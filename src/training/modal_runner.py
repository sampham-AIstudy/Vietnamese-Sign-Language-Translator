"""
Modal Cloud Training and Dispatch Runner for VSLT (Vietnamese Sign Language Translator).

Enables training models (CSLR, Word-level, etc.) on Modal Serverless Cloud GPUs
instead of local laptop compute, avoiding VRAM limits and hardware constraints.

Features:
- Persistent cloud storage with modal.Volume for datasets and checkpoints.
- Dynamic GPU acceleration (T4, A10G, L4, or CPU fallback).
- Data synchronization between local machine and Modal Volume.
- Direct checkpoint and evaluation report download back to local repo.

Usage:
  # Check connection / GPU status on Modal:
  modal run src/training/modal_runner.py --task status

  # Sync dataset to Modal Cloud Volume:
  modal run src/training/modal_runner.py --task sync-data

  # Train CSLR model on Cloud GPU:
  modal run src/training/modal_runner.py --task train-cslr --epochs 40 --gpu T4

  # Download trained checkpoints back to local:
  modal run src/training/modal_runner.py --task download
"""

import os
import sys
import shutil
from pathlib import Path
import modal

# Setup project root
LOCAL_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Define Modal App and Persistent Storage Volume
app = modal.App("vslt-cloud")
volume = modal.Volume.from_name("vslt-data-volume", create_if_missing=True)

# Build Container Image with DL dependencies and mount local src code
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.10.0",
        "tqdm>=4.65.0",
    )
    .add_local_dir(LOCAL_PROJECT_ROOT / "src", remote_path="/root/src")
)

REMOTE_VOL_PATH = "/vol"


@app.function(image=image, volumes={REMOTE_VOL_PATH: volume}, timeout=120)
def check_cloud_environment():
    """Checks cloud runtime specs (CUDA, CPU, Volume status)."""
    import torch
    cuda_ok = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_ok else "No GPU (CPU Mode)"
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3) if cuda_ok else 0

    vol_contents = os.listdir(REMOTE_VOL_PATH) if os.path.exists(REMOTE_VOL_PATH) else []
    return {
        "status": "connected",
        "cuda_available": cuda_ok,
        "gpu_name": gpu_name,
        "vram_gb": round(vram_gb, 2),
        "torch_version": torch.__version__,
        "volume_path": REMOTE_VOL_PATH,
        "volume_entries": vol_contents,
    }


@app.function(image=image, volumes={REMOTE_VOL_PATH: volume}, timeout=3600 * 4)
def run_cslr_on_modal(
    epochs: int = 40,
    batch_size: int = 8,
    stage1_epochs: int = 10,
    stage1_lr: float = 1e-3,
    stage2_backbone_lr: float = 1e-4,
    stage2_head_lr: float = 5e-4,
    patience: int = 10,
    seed: int = 42,
):
    """Executes CSLR Training pipeline on Modal cloud container."""
    import sys
    if "/root" not in sys.path:
        sys.path.insert(0, "/root")

    import torch
    from src.training.train_cslr import train_cslr

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[Modal Cloud] Starting CSLR Training on device: {device}")
    if torch.cuda.is_available():
        print(f"[Modal Cloud] GPU: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB VRAM)")

    # Data paths inside the cloud container volume
    data_root = Path(REMOTE_VOL_PATH) / "data" / "external" / "vsl_gh"
    vocab_path = data_root / "gloss_vocab_canonical.txt"
    pretrained_backbone = Path(REMOTE_VOL_PATH) / "checkpoints" / "stgcn_best.pt"
    checkpoint_dir = Path(REMOTE_VOL_PATH) / "checkpoints"
    reports_dir = Path(REMOTE_VOL_PATH) / "reports"

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not data_root.exists():
        raise FileNotFoundError(
            f"Dataset not found at {data_root}. Please run 'modal run src/training/modal_runner.py --task sync-data' first!"
        )

    cfg = {
        "data_root": str(data_root),
        "vocab_path": str(vocab_path),
        "pretrained_backbone": str(pretrained_backbone) if pretrained_backbone.exists() else "",
        "checkpoint_dir": str(checkpoint_dir),
        "reports_dir": str(reports_dir),
        "batch_size": batch_size,
        "total_epochs": epochs,
        "stage1_epochs": stage1_epochs,
        "stage1_lr": stage1_lr,
        "stage2_backbone_lr": stage2_backbone_lr,
        "stage2_head_lr": stage2_head_lr,
        "hidden_size": 256,
        "num_gru_layers": 2,
        "dropout": 0.3,
        "early_stopping_patience": patience,
        "seed": seed,
    }

    print(f"[Modal Cloud] Configuration loaded: {cfg}")
    results = train_cslr(cfg, skip_smoke_test=False)

    # Commit volume changes to persist checkpoints and reports
    volume.commit()
    print("[Modal Cloud] Training complete! Volume state committed.")
    return results


@app.function(image=image, volumes={REMOTE_VOL_PATH: volume}, timeout=3600)
def write_file_to_volume(relative_path: str, data_bytes: bytes):
    """Helper to stream files directly into Modal Volume."""
    target_path = Path(REMOTE_VOL_PATH) / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(data_bytes)
    return str(target_path)


@app.function(image=image, volumes={REMOTE_VOL_PATH: volume}, timeout=300)
def read_file_from_volume(relative_path: str) -> bytes:
    """Helper to read artifact bytes from Modal Volume."""
    target_path = Path(REMOTE_VOL_PATH) / relative_path
    if not target_path.exists():
        raise FileNotFoundError(f"File {relative_path} does not exist in Modal Volume.")
    with open(target_path, "rb") as f:
        return f.read()


@app.function(image=image, volumes={REMOTE_VOL_PATH: volume}, timeout=300)
def list_volume_files(subfolder: str = "") -> list:
    """Lists files in the Modal Volume."""
    base = Path(REMOTE_VOL_PATH) / subfolder
    if not base.exists():
        return []
    res = []
    for root, _, files in os.walk(base):
        for file in files:
            p = Path(root) / file
            res.append(str(p.relative_to(REMOTE_VOL_PATH)))
    return res


@app.local_entrypoint()
def main(
    task: str = "status",
    epochs: int = 40,
    batch_size: int = 8,
    gpu: str = "T4",
):
    print(f"===========================================================")
    print(f" VSLT Modal Cloud Dispatcher | Task: {task.upper()}")
    print(f"===========================================================")

    if task == "status":
        print("[Info] Querying Modal cloud container status...")
        info = check_cloud_environment.remote()
        for k, v in info.items():
            print(f"  {k}: {v}")

    elif task == "sync-data":
        print("[Info] Synchronizing essential VSLT data & pretrained backbones to Modal Volume...")
        local_vsl_gh = LOCAL_PROJECT_ROOT / "data" / "external" / "vsl_gh"
        local_stgcn = LOCAL_PROJECT_ROOT / "checkpoints" / "stgcn_best.pt"

        # 1. Sync metadata and vocab files
        files_to_sync = [
            local_vsl_gh / "gloss_vocab_canonical.txt",
            local_vsl_gh / "dataset_canonical.json",
            local_stgcn,
        ]

        # 2. Sync splits
        splits_dir = local_vsl_gh / "splits"
        if splits_dir.exists():
            for sp in splits_dir.glob("*.json"):
                files_to_sync.append(sp)

        # 3. Sync keypoints (sample batch or full)
        kp_dir = local_vsl_gh / "keypoints_frontal"
        if kp_dir.exists():
            for kp in kp_dir.glob("*.npy"):
                files_to_sync.append(kp)

        print(f"[Info] Found {len(files_to_sync)} files to upload to Modal Volume...")
        uploaded = 0
        for f in files_to_sync:
            if not f.exists():
                continue
            rel = f.relative_to(LOCAL_PROJECT_ROOT)
            with open(f, "rb") as fh:
                write_file_to_volume.remote(str(rel).replace("\\", "/"), fh.read())
            uploaded += 1
            if uploaded % 50 == 0 or uploaded == len(files_to_sync):
                print(f"  Uploaded {uploaded}/{len(files_to_sync)} files...")

        volume.commit()
        print("[Success] Data synchronization to Modal Volume completed successfully!")

    elif task == "train-cslr":
        print(f"[Info] Dispatching CSLR training job to Modal Cloud (epochs={epochs}, batch_size={batch_size})...")
        print(f"[Note] If using GPU ({gpu}), ensure your Modal billing method is configured.")
        # Configure GPU execution dynamically
        runner = run_cslr_on_modal
        if gpu:
            runner = runner.pip_install().set_options(gpu=gpu)
        results = runner.remote(
            epochs=epochs,
            batch_size=batch_size,
        )
        print(f"[Success] CSLR Training finished on Modal Cloud! Results: {results}")

    elif task == "download":
        print("[Info] Checking artifacts available in Modal Volume...")
        files = list_volume_files.remote()
        print(f"[Info] Files in volume: {files}")
        checkpoints_to_fetch = [f for f in files if f.startswith("checkpoints/") or f.startswith("reports/")]
        for rel in checkpoints_to_fetch:
            print(f"  Downloading {rel}...")
            content = read_file_from_volume.remote(rel)
            local_dest = LOCAL_PROJECT_ROOT / rel
            local_dest.parent.mkdir(parents=True, exist_ok=True)
            with open(local_dest, "wb") as fh:
                fh.write(content)
        print("[Success] Download complete! Checkpoints and reports are synced to local repository.")

    else:
        print(f"[Error] Unknown task: {task}. Choose from: status, sync-data, train-cslr, download")
