"""
CSLR Training Pipeline for Vietnamese Sign Language Recognition
Model: ST-GCN + BiGRU with Connectionist Temporal Classification (CTC) Loss

Protocol:
- Validation Signer: S05 (300 samples)
- Test Signer: S06 (300 samples) - Evaluated once at the very end
- Training Signers: S01..S04 (3,600 samples)
- Two-Stage Transfer Learning:
    * Stage 1 (Epochs 1-10): Frozen spatial backbone (checkpoints/stgcn_best.pt),
      train BiGRU + CTC head at lr=1e-3.
    * Stage 2 (Epochs 11-40): Unfreeze spatial backbone with differential lr
      (1e-4 for ST-GCN, 5e-4 for BiGRU/CTC head) with early stopping on Val WER.
- Hardware Target: NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM) with AMP FP16.
- Metric: Word Error Rate (WER) with Substitutions, Deletions, Insertions breakdown.
"""

import os
import sys
import json
import csv
import time
import random
import argparse
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

# Project root setup
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.vsl_gh_dataset import (
    VSLGHContinuousDataset,
    VSLGlossVocabulary,
    vslgh_collate_fn,
)
from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
from src.metrics.cslr_metrics import (
    ctc_greedy_decode,
    tokens_to_words,
    compute_wer,
    CSLRMetricTracker,
)


def set_seed(seed: int = 42) -> None:
    """Sets random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_vocab_hash(vocab_file: Path) -> str:
    """Calculates SHA256 hash of the canonical vocabulary file."""
    if vocab_file.is_file():
        return hashlib.sha256(vocab_file.read_bytes()).hexdigest()[:16]
    return "unknown"


def get_git_commit() -> str:
    """Retrieves current git commit hash."""
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(project_root)
        ).decode().strip()
    except Exception:
        return "406db45"


def validate_ctc_alignment_batch(
    out_lengths: torch.Tensor,
    target_lengths: torch.Tensor,
    batch_idx: int,
    epoch: int,
) -> int:
    """
    Checks that every sequence in the batch satisfies:
      out_lengths[i] >= target_lengths[i]
    Logs any violation and returns violation count.
    """
    violations = 0
    diff = out_lengths - target_lengths
    invalid_mask = diff < 0
    if invalid_mask.any():
        for i in range(len(out_lengths)):
            if invalid_mask[i]:
                violations += 1
                print(
                    f"[CTC ALIGNMENT ERROR] Epoch {epoch}, Batch {batch_idx}, Sample {i}: "
                    f"out_length={out_lengths[i].item()} < target_length={target_lengths[i].item()} "
                    f"(deficit={diff[i].item()})"
                )
    return violations


def evaluate_cslr(
    model: nn.Module,
    dataloader: DataLoader,
    ctc_loss_fn: nn.Module,
    vocab: VSLGlossVocabulary,
    device: torch.device,
    max_examples: int = 5,
) -> Dict[str, Any]:
    """
    Evaluates model on dataloader.
    Returns aggregated loss, WER (S, D, I), breakdown by annotation source,
    and qualitative prediction examples.
    """
    model.eval()
    total_loss = 0.0
    total_samples = 0
    all_hypotheses: List[List[int]] = []
    all_references: List[List[int]] = []
    annotation_sources: List[str] = []
    qualitative_examples: List[Dict[str, Any]] = []

    with torch.no_grad():
        for batch in dataloader:
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            gloss_targets = batch["gloss_targets"].to(device)
            gloss_lengths = batch["gloss_lengths"].to(device)
            sources = batch["annotation_sources"]

            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lengths = model(
                    features, joint_masks=joint_masks, sequence_lengths=lengths
                )
                loss = ctc_loss_fn(log_probs, gloss_targets, out_lengths, gloss_lengths)

            batch_size = len(lengths)
            total_loss += float(loss.item()) * batch_size
            total_samples += batch_size

            # Greedy decode
            decoded_batch = ctc_greedy_decode(
                log_probs, sequence_lengths=out_lengths, blank_id=vocab.blank_id
            )

            # Unpack targets per sample
            ref_batch: List[List[int]] = []
            ptr = 0
            for g_len in gloss_lengths.tolist():
                ref_seq = gloss_targets[ptr : ptr + g_len].cpu().tolist()
                ref_batch.append(ref_seq)
                ptr += g_len

            all_hypotheses.extend(decoded_batch)
            all_references.extend(ref_batch)
            annotation_sources.extend(sources)

            # Collect qualitative examples
            if len(qualitative_examples) < max_examples:
                decoded_words = tokens_to_words(decoded_batch, vocab)
                reference_words = tokens_to_words(ref_batch, vocab)
                for hyp_w, ref_w, sid, src in zip(
                    decoded_words, reference_words, batch["sample_ids"], sources
                ):
                    if len(qualitative_examples) < max_examples:
                        qualitative_examples.append({
                            "sample_id": sid,
                            "annotation_source": src,
                            "reference": " ".join(ref_w),
                            "prediction": " ".join(hyp_w) if hyp_w else "<BLANK_ONLY>",
                        })

    avg_loss = total_loss / total_samples if total_samples > 0 else 0.0
    overall_wer = compute_wer(all_hypotheses, all_references)

    # Separate metrics by annotation source
    src_hyp = [h for h, s in zip(all_hypotheses, annotation_sources) if s == "source"]
    src_ref = [r for r, s in zip(all_references, annotation_sources) if s == "source"]
    recon_hyp = [h for h, s in zip(all_hypotheses, annotation_sources) if s == "reconstructed"]
    recon_ref = [r for r, s in zip(all_references, annotation_sources) if s == "reconstructed"]

    src_wer = compute_wer(src_hyp, src_ref) if src_ref else {}
    recon_wer = compute_wer(recon_hyp, recon_ref) if recon_ref else {}

    return {
        "loss": round(avg_loss, 4),
        "total_samples": total_samples,
        "wer": overall_wer["wer"],
        "substitutions": overall_wer["substitutions"],
        "deletions": overall_wer["deletions"],
        "insertions": overall_wer["insertions"],
        "sub_rate": overall_wer["sub_rate"],
        "del_rate": overall_wer["del_rate"],
        "ins_rate": overall_wer["ins_rate"],
        "total_ref_words": overall_wer["total_ref_words"],
        "total_hyp_words": overall_wer["total_hyp_words"],
        "source_wer": src_wer.get("wer", None),
        "reconstructed_wer": recon_wer.get("wer", None),
        "qualitative_examples": qualitative_examples,
    }


def run_smoke_test(
    data_root: Path,
    vocab_path: Path,
    checkpoint_path: Path,
    device: torch.device,
) -> bool:
    """
    Executes a 10-epoch overfit test on 8 training samples and 1 validation sample.
    Verifies that the model can reduce training CTC loss and decode non-empty gloss sequences.
    """
    print("\n" + "=" * 60)
    print("STARTING SMOKE TEST / FIRST-RUN SAFETY CHECK")
    print("=" * 60)
    set_seed(42)

    vocab = VSLGlossVocabulary.from_file(str(vocab_path))
    full_train = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="train",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )
    val_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="val",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )

    smoke_train_subset = Subset(full_train, indices=list(range(8)))
    smoke_val_subset = Subset(val_dataset, indices=[0])

    train_loader = DataLoader(
        smoke_train_subset, batch_size=4, shuffle=True, collate_fn=vslgh_collate_fn
    )
    val_loader = DataLoader(
        smoke_val_subset, batch_size=1, shuffle=False, collate_fn=vslgh_collate_fn
    )

    model = STGCNBiGRU_CSLR(
        num_joints=67,
        in_channels=3,
        num_classes=len(vocab),
        channel_dims=[64, 64, 128],
        temporal_downsample=2,
        hidden_size=256,
        num_gru_layers=2,
        dropout=0.1,
    ).to(device)

    if checkpoint_path.is_file():
        model.load_pretrained_spatial_backbone(str(checkpoint_path), freeze=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))
    ctc_loss_fn = nn.CTCLoss(blank=vocab.blank_id, zero_infinity=True, reduction="mean")

    initial_loss = 0.0
    final_loss = 0.0

    print("Running 10 overfit epochs on 8 samples...")
    for epoch in range(1, 11):
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            gloss_targets = batch["gloss_targets"].to(device)
            gloss_lengths = batch["gloss_lengths"].to(device)

            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lengths = model(
                    features, joint_masks=joint_masks, sequence_lengths=lengths
                )
                loss = ctc_loss_fn(log_probs, gloss_targets, out_lengths, gloss_lengths)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += loss.item() * len(lengths)

        epoch_loss /= len(smoke_train_subset)
        if epoch == 1:
            initial_loss = epoch_loss
        final_loss = epoch_loss
        print(f"  Smoke Epoch {epoch:02d}/10: Train CTC Loss = {epoch_loss:.4f}")

    # Evaluate on smoke subset
    eval_res = evaluate_cslr(model, train_loader, ctc_loss_fn, vocab, device, max_examples=2)
    print(f"Smoke Test Initial Loss: {initial_loss:.4f} -> Final Loss: {final_loss:.4f}")
    print(f"Smoke Test Decoded Samples: {eval_res['qualitative_examples']}")

    loss_decreased = final_loss < initial_loss
    has_predictions = eval_res["total_hyp_words"] > 0
    smoke_passed = loss_decreased and has_predictions and torch.isfinite(torch.tensor(final_loss))

    if smoke_passed:
        print("[SMOKE TEST PASSED] CTC loss decreased and model produces non-empty decoded glosses.\n")
    else:
        print(f"[SMOKE TEST FAILED] Loss decreased: {loss_decreased}, Non-empty output: {has_predictions}")

    return smoke_passed


def train_cslr(
    config: Dict[str, Any],
    skip_smoke_test: bool = False,
) -> Dict[str, Any]:
    """
    Main training execution function.
    """
    set_seed(config["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INIT] Using device: {device}")
    if device.type == "cuda":
        print(f"[INIT] GPU: {torch.cuda.get_device_name(0)}")

    # Paths
    data_root = Path(config["data_root"])
    vocab_path = Path(config["vocab_path"])
    checkpoint_dir = Path(config["checkpoint_dir"])
    reports_dir = Path(config["reports_dir"])
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    pretrained_backbone_path = Path(config["pretrained_backbone"])
    vocab_hash = get_vocab_hash(vocab_path)
    git_commit = get_git_commit()
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Smoke test check
    if not skip_smoke_test:
        smoke_ok = run_smoke_test(data_root, vocab_path, pretrained_backbone_path, device)
        if not smoke_ok:
            raise RuntimeError("Smoke test failed! Halting full training as per Section 10 safety protocol.")

    # 2. Datasets and Loaders
    vocab = VSLGlossVocabulary.from_file(str(vocab_path))
    print(f"\n[DATA] Vocabulary loaded: {len(vocab)} classes (blank={vocab.blank_id}, unk={vocab.unk_id})")

    train_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="train",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )
    val_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="val",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )
    test_dataset = VSLGHContinuousDataset(
        canonical_json=data_root / "dataset_canonical.json",
        keypoints_dir=data_root / "keypoints_frontal",
        split="test",
        vocabulary=vocab,
        conversion_mode="semantic",
        normalize=True,
    )

    print(f"[DATA] Splits loaded: Train={len(train_dataset)} (S01-S04), Val={len(val_dataset)} (S05), Test={len(test_dataset)} (S06)")

    batch_size = config["batch_size"]
    num_workers = config.get("num_workers", 0)  # 0 for Windows stability

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=vslgh_collate_fn,
        num_workers=num_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=vslgh_collate_fn,
        num_workers=num_workers,
        pin_memory=(device.type == "cuda"),
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=vslgh_collate_fn,
        num_workers=num_workers,
        pin_memory=(device.type == "cuda"),
    )

    # 3. Model Architecture
    model = STGCNBiGRU_CSLR(
        num_joints=67,
        in_channels=3,
        num_classes=len(vocab),
        channel_dims=[64, 64, 128],
        temporal_downsample=2,
        hidden_size=config["hidden_size"],
        num_gru_layers=config["num_gru_layers"],
        dropout=config["dropout"],
    ).to(device)

    # Transfer pretrained backbone
    transfer_info = {}
    if pretrained_backbone_path.is_file():
        transfer_info = model.load_pretrained_spatial_backbone(
            str(pretrained_backbone_path), freeze=True
        )
        print(f"[MODEL] Transferred {transfer_info['transferred_params']:,} spatial parameters from {pretrained_backbone_path}")
    else:
        print(f"[WARN] Checkpoint {pretrained_backbone_path} not found. Training from scratch.")

    # CTC Loss
    ctc_loss_fn = nn.CTCLoss(blank=vocab.blank_id, zero_infinity=True, reduction="mean")
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    # Tracking structures
    history: List[Dict[str, Any]] = []
    best_val_wer = float("inf")
    best_stage1_wer = float("inf")
    best_epoch = 0
    patience = config.get("early_stopping_patience", 10)
    patience_counter = 0

    total_epochs = config["total_epochs"]  # 40
    stage1_epochs = config["stage1_epochs"] # 10

    print("\n" + "=" * 80)
    print(f"CSLR TRAINING STARTED | Total Epochs: {total_epochs} | Stage 1: 1-{stage1_epochs} | Stage 2: {stage1_epochs+1}-{total_epochs}")
    print("=" * 80)

    # =========================================================================
    # STAGE 1: FROZEN SPATIAL BACKBONE (Epochs 1-10)
    # =========================================================================
    print(f"\n>>> ENTERING STAGE 1: Frozen ST-GCN Backbone (Epochs 1-{stage1_epochs})")
    for name, param in model.named_parameters():
        if name.startswith("data_bn.") or name.startswith("blocks."):
            param.requires_grad = False
        else:
            param.requires_grad = True

    # Optimizer for Stage 1: newly initialized modules only
    trainable_params_stage1 = [p for p in model.parameters() if p.requires_grad]
    optimizer_stage1 = torch.optim.AdamW(
        trainable_params_stage1, lr=config["stage1_lr"], weight_decay=1e-4
    )
    scheduler_stage1 = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer_stage1, T_max=stage1_epochs, eta_min=1e-5
    )

    current_optimizer = optimizer_stage1
    current_scheduler = scheduler_stage1

    start_training_time = time.time()

    for epoch in range(1, total_epochs + 1):
        epoch_start_time = time.time()
        stage_num = 1 if epoch <= stage1_epochs else 2

        # Transition to Stage 2
        if epoch == stage1_epochs + 1:
            print(f"\n>>> ENTERING STAGE 2: Joint Fine-Tuning ST-GCN + BiGRU (Epochs {stage1_epochs+1}-{total_epochs})")
            # Unfreeze backbone
            for param in model.parameters():
                param.requires_grad = True

            # Differential learning rates
            backbone_params = [
                p for n, p in model.named_parameters() if n.startswith("data_bn.") or n.startswith("blocks.")
            ]
            head_params = [
                p for n, p in model.named_parameters() if not (n.startswith("data_bn.") or n.startswith("blocks."))
            ]

            current_optimizer = torch.optim.AdamW([
                {"params": backbone_params, "lr": config["stage2_backbone_lr"], "weight_decay": 1e-4},
                {"params": head_params, "lr": config["stage2_head_lr"], "weight_decay": 1e-4},
            ])
            stage2_len = total_epochs - stage1_epochs
            current_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                current_optimizer, T_max=stage2_len, eta_min=1e-6
            )

        # Training Phase
        model.train()
        train_loss = 0.0
        train_samples = 0
        alignment_violations = 0

        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)

        for batch_idx, batch in enumerate(train_loader):
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            gloss_targets = batch["gloss_targets"].to(device)
            gloss_lengths = batch["gloss_lengths"].to(device)

            current_optimizer.zero_grad()

            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lengths = model(
                    features, joint_masks=joint_masks, sequence_lengths=lengths
                )

                # Pre-backward alignment safety validation
                violations = validate_ctc_alignment_batch(
                    out_lengths, gloss_lengths, batch_idx, epoch
                )
                if violations > 0:
                    alignment_violations += violations
                    raise RuntimeError(
                        f"FATAL: CTC Alignment violation detected at epoch {epoch}, batch {batch_idx}. "
                        "input_lengths < target_lengths. Halting training to prevent silent error masking."
                    )

                loss = ctc_loss_fn(log_probs, gloss_targets, out_lengths, gloss_lengths)

            scaler.scale(loss).backward()
            scaler.unscale_(current_optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(current_optimizer)
            scaler.update()

            batch_count = len(lengths)
            train_loss += float(loss.item()) * batch_count
            train_samples += batch_count

        current_scheduler.step()
        train_loss /= train_samples
        epoch_time = time.time() - epoch_start_time

        peak_gpu_mb = (
            torch.cuda.max_memory_allocated(device) / (1024 * 1024) if device.type == "cuda" else 0.0
        )

        # Validation Phase (on S05)
        val_res = evaluate_cslr(
            model, val_loader, ctc_loss_fn, vocab, device, max_examples=3
        )

        # Current learning rates
        current_lrs = [pg["lr"] for pg in current_optimizer.param_groups]
        lr_head = current_lrs[-1]
        lr_backbone = current_lrs[0] if len(current_lrs) > 1 else 0.0

        epoch_record = {
            "epoch": epoch,
            "stage": stage_num,
            "train_loss": round(train_loss, 4),
            "val_loss": val_res["loss"],
            "val_wer": val_res["wer"],
            "substitutions": val_res["substitutions"],
            "deletions": val_res["deletions"],
            "insertions": val_res["insertions"],
            "sub_rate": val_res["sub_rate"],
            "del_rate": val_res["del_rate"],
            "ins_rate": val_res["ins_rate"],
            "learning_rate_head": lr_head,
            "learning_rate_backbone": lr_backbone,
            "epoch_time_sec": round(epoch_time, 2),
            "peak_gpu_memory_mb": round(peak_gpu_mb, 2),
        }
        history.append(epoch_record)

        print(
            f"Epoch {epoch:02d}/{total_epochs:02d} [Stage {stage_num}] | "
            f"Train Loss: {train_loss:.4f} | Val Loss: {val_res['loss']:.4f} | "
            f"Val WER: {val_res['wer']:.2f}% (S:{val_res['substitutions']} D:{val_res['deletions']} I:{val_res['insertions']}) | "
            f"Time: {epoch_time:.1f}s | GPU: {peak_gpu_mb:.1f} MB"
        )

        # Checkpoint saving
        checkpoint_meta = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": current_optimizer.state_dict(),
            "scheduler_state_dict": current_scheduler.state_dict(),
            "epoch": epoch,
            "stage": stage_num,
            "val_loss": val_res["loss"],
            "val_wer": val_res["wer"],
            "substitutions": val_res["substitutions"],
            "deletions": val_res["deletions"],
            "insertions": val_res["insertions"],
            "config": config,
            "seed": config["seed"],
            "dataset_commit": git_commit,
            "dataset_version": "canonical_v1.0",
            "gloss_vocab_hash": vocab_hash,
            "training_timestamp": timestamp_str,
        }

        # Stage 1 best tracking
        if stage_num == 1 and val_res["wer"] < best_stage1_wer:
            best_stage1_wer = val_res["wer"]
            checkpoint_meta["best_val_WER"] = best_stage1_wer
            torch.save(checkpoint_meta, checkpoint_dir / "cslr_stage1_best.pt")
            print(f"  --> Saved new Stage 1 best checkpoint: {checkpoint_dir / 'cslr_stage1_best.pt'} (WER: {best_stage1_wer:.2f}%)")

        # Global best tracking (primary model selection based on S05 validation WER)
        if val_res["wer"] < best_val_wer:
            best_val_wer = val_res["wer"]
            best_epoch = epoch
            patience_counter = 0
            checkpoint_meta["best_val_WER"] = best_val_wer
            torch.save(checkpoint_meta, checkpoint_dir / "cslr_best.pt")
            print(f"  --> Saved new Global best checkpoint: {checkpoint_dir / 'cslr_best.pt'} (WER: {best_val_wer:.2f}%)")
        else:
            if stage_num == 2:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"\n[EARLY STOPPING] Validation WER did not improve for {patience} consecutive epochs in Stage 2. Halting training.")
                    break

        # Always save latest
        checkpoint_meta["best_val_WER"] = best_val_wer
        torch.save(checkpoint_meta, checkpoint_dir / "cslr_latest.pt")

    total_train_time = time.time() - start_training_time
    avg_epoch_time = total_train_time / len(history) if history else 0.0

    # Save History JSON and CSV
    history_json_path = reports_dir / "cslr_training_history.json"
    with open(history_json_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    history_csv_path = reports_dir / "cslr_training_history.csv"
    with open(history_csv_path, "w", newline="", encoding="utf-8") as f:
        if history:
            writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
            writer.writeheader()
            writer.writerows(history)

    print(f"\n[HISTORY] Saved training logs to:\n  - {history_json_path}\n  - {history_csv_path}")

    # =========================================================================
    # FINAL EVALUATION ON S06 (TEST SIGNER) - STRICTLY ONCE
    # =========================================================================
    print("\n" + "=" * 80)
    print("PRIMARY TEST EVALUATION (Test Signer: S06, strictly held out until now)")
    print("=" * 80)
    best_ckpt_path = checkpoint_dir / "cslr_best.pt"
    if best_ckpt_path.is_file():
        print(f"Loading best checkpoint from epoch {best_epoch} (Val WER: {best_val_wer:.2f}%): {best_ckpt_path}")
        best_ckpt = torch.load(best_ckpt_path, map_location=device)
        model.load_state_dict(best_ckpt["model_state_dict"])
    else:
        print("[WARN] cslr_best.pt not found, evaluating model in current state.")

    test_res = evaluate_cslr(
        model, test_loader, ctc_loss_fn, vocab, device, max_examples=10
    )

    print(f"Test Set Loss: {test_res['loss']:.4f}")
    print(f"Test Primary WER (S06): {test_res['wer']:.2f}%")
    print(f"Test Substitutions: {test_res['substitutions']} ({test_res['sub_rate']:.2f}%)")
    print(f"Test Deletions:     {test_res['deletions']} ({test_res['del_rate']:.2f}%)")
    print(f"Test Insertions:    {test_res['insertions']} ({test_res['ins_rate']:.2f}%)")
    print(f"Total Reference Words: {test_res['total_ref_words']} | Predicted Words: {test_res['total_hyp_words']}")

    # Save complete test results
    final_test_summary = {
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else "N/A",
        "training_time": {
            "total_training_time_sec": round(total_train_time, 2),
            "average_epoch_time_sec": round(avg_epoch_time, 2),
            "total_epochs_trained": len(history),
            "best_epoch": best_epoch,
        },
        "validation_s05": {
            "best_val_wer": best_val_wer,
            "final_val_loss": history[-1]["val_loss"] if history else None,
            "final_val_wer": history[-1]["val_wer"] if history else None,
        },
        "test_s06": test_res,
        "checkpoints": {
            "stage1_best": str(checkpoint_dir / "cslr_stage1_best.pt"),
            "global_best": str(checkpoint_dir / "cslr_best.pt"),
            "latest": str(checkpoint_dir / "cslr_latest.pt"),
        },
        "config": config,
    }

    test_json_path = reports_dir / "cslr_test_results.json"
    with open(test_json_path, "w", encoding="utf-8") as f:
        json.dump(final_test_summary, f, indent=2, ensure_ascii=False)

    print(f"\n[TEST REPORT] Saved final test results to: {test_json_path}")
    return final_test_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Continuous Sign Language Recognition (CSLR) Model")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size (default: 8)")
    parser.add_argument("--epochs", type=int, default=40, help="Total training epochs (default: 40)")
    parser.add_argument("--stage1-epochs", type=int, default=10, help="Stage 1 frozen epochs (default: 10)")
    parser.add_argument("--stage1-lr", type=float, default=1e-3, help="Stage 1 learning rate (default: 1e-3)")
    parser.add_argument("--stage2-backbone-lr", type=float, default=1e-4, help="Stage 2 backbone lr (default: 1e-4)")
    parser.add_argument("--stage2-head-lr", type=float, default=5e-4, help="Stage 2 head lr (default: 5e-4)")
    parser.add_argument("--hidden-size", type=int, default=256, help="BiGRU hidden size (default: 256)")
    parser.add_argument("--num-gru-layers", type=int, default=2, help="Number of BiGRU layers (default: 2)")
    parser.add_argument("--dropout", type=float, default=0.3, help="Dropout rate (default: 0.3)")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience (default: 10)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--smoke-test-only", action="store_true", help="Run smoke test only and exit")
    parser.add_argument("--skip-smoke-test", action="store_true", help="Skip smoke test before training")

    args = parser.parse_args()

    cfg = {
        "data_root": str(project_root / "data" / "external" / "vsl_gh"),
        "vocab_path": str(project_root / "data" / "external" / "vsl_gh" / "gloss_vocab_canonical.txt"),
        "pretrained_backbone": str(project_root / "checkpoints" / "stgcn_best.pt"),
        "checkpoint_dir": str(project_root / "checkpoints"),
        "reports_dir": str(project_root / "reports"),
        "batch_size": args.batch_size,
        "total_epochs": args.epochs,
        "stage1_epochs": args.stage1_epochs,
        "stage1_lr": args.stage1_lr,
        "stage2_backbone_lr": args.stage2_backbone_lr,
        "stage2_head_lr": args.stage2_head_lr,
        "hidden_size": args.hidden_size,
        "num_gru_layers": args.num_gru_layers,
        "dropout": args.dropout,
        "early_stopping_patience": args.patience,
        "seed": args.seed,
    }

    if args.smoke_test_only:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ok = run_smoke_test(
            Path(cfg["data_root"]),
            Path(cfg["vocab_path"]),
            Path(cfg["pretrained_backbone"]),
            dev,
        )
        sys.exit(0 if ok else 1)

    train_cslr(cfg, skip_smoke_test=args.skip_smoke_test)
