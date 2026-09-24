"""
Generates vsl_alphabet_cloud_training.ipynb (Level 1 fingerspelling) for Kaggle.

Protocol enforced by the generated notebook:
- Model + epoch selection uses VAL only; the decision is written to selection.json
  BEFORE the test set is touched. TEST is evaluated exactly once, in the last cell.
- Fixed seed, deterministic cuDNN.
- Checkpoints embed config, ordered class list and preprocessing parameters.

Usage:
  python scripts/generate_alphabet_notebook.py              # write the .ipynb
  python scripts/generate_alphabet_notebook.py --script > /tmp/nb.py
  ALPHA_SMOKE=1 ALPHA_OUT=/tmp/alpha_smoke python /tmp/nb.py   # local CPU smoke run (2 epochs, subsets)
"""

import json
import sys
from pathlib import Path

MARKDOWN_INTRO = """# VSL Alphabet (Level 1 - Fingerspelling) — Kaggle GPU training

**Data:** VSL Alphabet Pilot (1,875 clips, 15 signers, 25 classes), signer-disjoint split:
train = 10 signers, val = S02/S12, test = S03/S14/S15.

**Protocol**
1. Train Static MLP (63-d median hold frame) and Temporal BiGRU (30x63 sequence).
2. Pick best epoch per model and the winning model **on VAL only** -> `selection.json`.
3. Evaluate TEST **once** at the end: Top-1, Top-3, macro-F1, per-class F1, confusion matrix, per-signer accuracy.
4. Outputs in `/kaggle/working`: `alphabet_best.pt`, per-model checkpoints, epoch logs, metrics."""

CELL_ENV = r'''# 1. ENVIRONMENT
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # must precede CUDA init for determinism
import sys, json, time, random, shutil, zipfile, platform, copy
from pathlib import Path
import numpy as np
import torch

T_START = time.time()
IN_KAGGLE = Path("/kaggle/input").exists()
SMOKE = os.environ.get("ALPHA_SMOKE") == "1"
OUT_DIR = Path("/kaggle/working" if IN_KAGGLE else os.environ.get("ALPHA_OUT", "outputs_alphabet_local")).resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None

print(f"Kaggle={IN_KAGGLE} smoke={SMOKE} device={DEVICE} gpu={GPU_NAME}")
print(f"python={platform.python_version()} torch={torch.__version__} out={OUT_DIR}")'''

CELL_DATA = r'''# 2. LOCATE DATA + CODE (dataset zip, auto-extracted dataset, or local repo)
def locate_root() -> Path:
    here = Path(".").resolve()
    if (here / "data/vsl_alphabet_pilot/splits/train.csv").exists() and (here / "src/data/alphabet_dataset.py").exists():
        return here
    base = Path("/kaggle/input")
    zips = sorted(base.rglob("vsl_alphabet_cloud_data.zip")) if base.exists() else []
    if zips:
        work = Path("/tmp/vsl_alphabet")  # NOT /kaggle/working: keep data out of the kernel output
        if work.exists():
            shutil.rmtree(work)
        with zipfile.ZipFile(zips[0]) as zf:
            zf.extractall(work)
        print(f"Extracted {zips[0]} -> {work}")
        return work
    for hit in sorted(base.rglob("alphabet_dataset.py")) if base.exists() else []:
        root = hit.parents[2]
        if (root / "data/vsl_alphabet_pilot/splits/train.csv").exists():
            return root
    raise FileNotFoundError("vsl_alphabet_cloud_data not found (attach the Kaggle dataset)")

ROOT = locate_root()
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
CFG = yaml.safe_load(open("configs/alphabet_level1.yaml", encoding="utf-8"))
SEED = int(CFG["seed"])
SPLITS = CFG["data"]["splits_dir"]
CLASSES = [l.strip() for l in open(f"{SPLITS}/classes.txt", encoding="utf-8") if l.strip()]
assert len(CLASSES) == CFG["data"]["num_classes"] == 25, CLASSES

import csv
SPLIT_ROWS = {s: list(csv.DictReader(open(f"{SPLITS}/{s}.csv", encoding="utf-8"))) for s in ("train", "val", "test")}
SIGNER_OF = {r["sample_id"]: r["signer_id"] for rows in SPLIT_ROWS.values() for r in rows}
SIGNERS = {s: sorted({r["signer_id"] for r in rows}) for s, rows in SPLIT_ROWS.items()}
assert not (set(SIGNERS["train"]) & set(SIGNERS["val"])) and not (set(SIGNERS["train"]) & set(SIGNERS["test"]))
assert not (set(SIGNERS["val"]) & set(SIGNERS["test"]))
missing = [r["landmark_path"] for rows in SPLIT_ROWS.values() for r in rows if not Path(r["landmark_path"]).exists()]
assert not missing, f"{len(missing)} landmark files missing, e.g. {missing[:3]}"
print(f"root={ROOT}")
print({s: len(r) for s, r in SPLIT_ROWS.items()}, SIGNERS)'''

CELL_HELPERS = r'''# 3. SEED, LOADERS, MODELS, METRICS
from torch.utils.data import DataLoader, Subset
import torch.nn as nn
from sklearn.metrics import f1_score, confusion_matrix
from src.data.alphabet_dataset import VSLAlphabetDataset
from src.models.alphabet_mlp import VSLAlphabetMLP
from src.models.alphabet_temporal import VSLAlphabetBiGRU

def set_seed(seed: int):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)

def make_loader(split: str, data_mode: str, train: bool) -> DataLoader:
    d = CFG["data"]
    ds = VSLAlphabetDataset(
        f"{SPLITS}/{split}.csv", classes_path=f"{SPLITS}/classes.txt", data_mode=data_mode,
        target_seq_len=d["target_seq_len"], augment=train,
        jitter_std=d["augment"]["jitter_std"], scale_range=tuple(d["augment"]["scale_range"]),
    )
    assert ds.classes == CLASSES
    if SMOKE:
        ds = Subset(ds, list(range(0, len(ds), max(1, len(ds) // 60))))
    g = torch.Generator(); g.manual_seed(SEED)
    return DataLoader(ds, batch_size=CFG["train"]["batch_size"], shuffle=train,
                      generator=g if train else None, num_workers=0)

def build_model(name: str) -> nn.Module:
    m = CFG["models"][name]
    if name == "mlp":
        return VSLAlphabetMLP(input_dim=63, num_classes=len(CLASSES),
                              hidden_dims=tuple(m["hidden_dims"]), dropout=m["dropout"])
    return VSLAlphabetBiGRU(input_dim=63, hidden_dim=m["hidden_dim"], num_layers=m["num_layers"],
                            num_classes=len(CLASSES), dropout=m["dropout"])

# backend/main.py rebuilds models with these exact constructors — fail fast if the config drifts.
assert tuple(CFG["models"]["mlp"]["hidden_dims"]) == (128, 64)
assert CFG["models"]["bigru"]["hidden_dim"] == 64 and CFG["models"]["bigru"]["num_layers"] == 2

@torch.no_grad()
def predict(model, loader, criterion=None):
    model.eval()
    ys, probs, ids, loss_sum = [], [], [], 0.0
    for b in loader:
        x, y = b["features"].to(DEVICE), b["label"].to(DEVICE)
        logits = model(x)
        if criterion is not None:
            loss_sum += criterion(logits, y).item() * y.size(0)
        probs.append(torch.softmax(logits, -1).cpu().numpy()); ys.append(y.cpu().numpy()); ids += list(b["sample_id"])
    y, p = np.concatenate(ys), np.concatenate(probs)
    return y, p, ids, loss_sum / max(len(y), 1)

def summarize(y, p) -> dict:
    pred = p.argmax(1)
    top3 = np.argsort(-p, 1)[:, :3]
    return {
        "top1": float((pred == y).mean()),
        "top3": float(np.mean([t in row for t, row in zip(y, top3)])),
        "macro_f1": float(f1_score(y, pred, labels=list(range(len(CLASSES))), average="macro", zero_division=0)),
        "n": int(len(y)),
    }'''

CELL_TRAIN_FN = r'''# 4. TRAINING LOOP (selection on VAL only; test loader is never built here)
def train_model(name: str) -> dict:
    set_seed(SEED)
    mc, tc = CFG["models"][name], CFG["train"]
    epochs = 2 if SMOKE else int(mc["epochs"])
    tr_loader, va_loader = make_loader("train", mc["data_mode"], True), make_loader("val", mc["data_mode"], False)
    model = build_model(name).to(DEVICE)
    crit = nn.CrossEntropyLoss(label_smoothing=tc["label_smoothing"])
    opt = torch.optim.AdamW(model.parameters(), lr=float(mc["lr"]), weight_decay=float(tc["weight_decay"]))
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=float(tc["eta_min"]))
    best, best_state, history, t0 = None, None, [], time.time()
    for ep in range(1, epochs + 1):
        te = time.time(); model.train(); tl, tc_, tn = 0.0, 0, 0
        for b in tr_loader:
            x, y = b["features"].to(DEVICE), b["label"].to(DEVICE)
            opt.zero_grad(); logits = model(x); loss = crit(logits, y); loss.backward(); opt.step()
            tl += loss.item() * y.size(0); tc_ += (logits.argmax(-1) == y).sum().item(); tn += y.size(0)
        sched.step()
        vy, vp, _, vloss = predict(model, va_loader, crit)
        vm = summarize(vy, vp)
        rec = {"epoch": ep, "train_loss": tl / tn, "train_acc": tc_ / tn, "val_loss": vloss,
               "val_top1": vm["top1"], "val_top3": vm["top3"], "val_macro_f1": vm["macro_f1"],
               "lr": opt.param_groups[0]["lr"], "epoch_s": time.time() - te}
        history.append(rec)
        print(f"[{name}] ep {ep:02d}/{epochs} train_loss={rec['train_loss']:.4f} train_acc={rec['train_acc']:.3f} "
              f"val_loss={vloss:.4f} val_top1={vm['top1']:.3f} val_f1={vm['macro_f1']:.3f}")
        key = (vm["top1"], vm["macro_f1"])
        if best is None or key > (best["val_top1"], best["val_macro_f1"]):
            best = {"epoch": ep, "val_top1": vm["top1"], "val_top3": vm["top3"], "val_macro_f1": vm["macro_f1"], "val_loss": vloss}
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    d = CFG["data"]
    ckpt = {
        "model_type": name,
        "num_classes": len(CLASSES),
        "classes": list(CLASSES),                      # index order == label ids
        "class_to_idx": {c: i for i, c in enumerate(CLASSES)},
        "state_dict": best_state,
        "input_dim": 63,
        "normalization": d["normalization"],
        "model_hparams": dict(mc),
        "preprocessing": {
            "data_mode": mc["data_mode"],
            "landmarks": "MediaPipe Hands 21x(x,y,z), npz key raw_landmarks",
            "normalization": d["normalization"], "wrist_idx": 0, "scale_ref_idx": 9,
            "static_strategy": d["static_strategy"], "target_seq_len": int(d["target_seq_len"]),
            "hold_window": "split CSV hold_start_frame/hold_end_frame",
            "hold_start_default": int(d["default_hold_start"]), "hold_end_default": int(d["default_hold_end"]),
        },
        "config": CFG,
        "seed": SEED,
        "epoch": best["epoch"],
        "best_val_acc": best["val_top1"],
        "best_val_macro_f1": best["val_macro_f1"],
        "signers": SIGNERS,
        "torch_version": str(torch.__version__),  # TorchVersion is rejected by torch.load(weights_only=True)
        "smoke": SMOKE,
    }
    path = OUT_DIR / f"alphabet_{name}_best.pt"
    torch.save(ckpt, path)
    with open(OUT_DIR / f"train_log_{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(history[0])); w.writeheader(); w.writerows(history)
    res = {"model": name, "best": best, "epochs": epochs, "train_time_s": time.time() - t0, "ckpt": str(path)}
    print(f"[{name}] best epoch {best['epoch']} val_top1={best['val_top1']:.4f} val_f1={best['val_macro_f1']:.4f} "
          f"({res['train_time_s']:.0f}s)")
    return res'''

CELL_MLP = r'''# 5. STATIC MLP
RESULTS = {"mlp": train_model("mlp")}'''

CELL_BIGRU = r'''# 6. TEMPORAL BIGRU
RESULTS["bigru"] = train_model("bigru")'''

CELL_SELECT = r'''# 7. SELECT WINNER ON VAL ONLY (frozen to disk before any test evaluation)
def sel_key(n):
    b = RESULTS[n]["best"]
    return (b["val_top1"], b["val_macro_f1"], 1 if n == "mlp" else 0)  # final tie-break: MLP (backend-compatible)

WINNER = max(RESULTS, key=sel_key)
SELECTION = {
    "winner": WINNER, "criterion": [CFG["selection_metric"], *CFG["tie_breakers"]],
    "val": {n: r["best"] for n, r in RESULTS.items()}, "decided_before_test": True,
}
json.dump(SELECTION, open(OUT_DIR / "selection.json", "w", encoding="utf-8"), indent=2)
shutil.copy(RESULTS[WINNER]["ckpt"], OUT_DIR / "alphabet_best.pt")
print(json.dumps(SELECTION, indent=2))'''

CELL_TEST = r'''# 8. FINAL TEST — evaluated ONCE, after selection.json was written
assert (OUT_DIR / "selection.json").exists()
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report

TEST = {}
for name in ("mlp", "bigru"):
    ck = torch.load(RESULTS[name]["ckpt"], map_location=DEVICE, weights_only=True)
    model = build_model(name).to(DEVICE); model.load_state_dict(ck["state_dict"])
    y, p, ids, _ = predict(model, make_loader("test", CFG["models"][name]["data_mode"], False))
    pred = p.argmax(1)
    m = summarize(y, p)
    rep = classification_report(y, pred, labels=list(range(len(CLASSES))), target_names=CLASSES,
                                output_dict=True, zero_division=0)
    m["per_class_f1"] = {c: float(rep[c]["f1-score"]) for c in CLASSES}
    signers = np.array([SIGNER_OF[i] for i in ids])
    m["per_signer_top1"] = {str(s): float((pred[signers == s] == y[signers == s]).mean()) for s in sorted(set(signers))}
    cm = confusion_matrix(y, pred, labels=list(range(len(CLASSES))))
    m["confusion_matrix"] = cm.tolist()
    off = [(int(cm[i, j]), CLASSES[i], CLASSES[j]) for i in range(len(CLASSES)) for j in range(len(CLASSES)) if i != j and cm[i, j] > 0]
    m["top_confusions"] = [{"true": t, "pred": pr, "count": c} for c, t, pr in sorted(off, reverse=True)[:10]]
    TEST[name] = m

    with open(OUT_DIR / f"test_predictions_{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["sample_id", "signer_id", "true", "pred", "confidence"])
        for i, t, pr, conf in zip(ids, y, pred, p.max(1)):
            w.writerow([i, SIGNER_OF[i], CLASSES[t], CLASSES[pr], f"{conf:.6f}"])
    with open(OUT_DIR / f"confusion_matrix_{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["true\\pred", *CLASSES])
        for c, row in zip(CLASSES, cm): w.writerow([c, *row])
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.imshow(cm, cmap="Blues"); ax.set_xticks(range(len(CLASSES)), CLASSES, rotation=90); ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(f"{name} — test (signers {', '.join(SIGNERS['test'])})")
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            if cm[i, j]: ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=6, color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(OUT_DIR / f"confusion_matrix_{name}.png", dpi=120); plt.close(fig)
    print(f"[TEST {name}] top1={m['top1']:.4f} top3={m['top3']:.4f} macro_f1={m['macro_f1']:.4f} per_signer={m['per_signer_top1']}")

METRICS = {
    "selection": SELECTION, "test": TEST, "val": SELECTION["val"],
    "train_time_s": {n: r["train_time_s"] for n, r in RESULTS.items()},
    "total_runtime_s": time.time() - T_START, "device": DEVICE, "gpu": GPU_NAME,
    "torch": str(torch.__version__), "seed": SEED, "smoke": SMOKE, "classes": CLASSES, "signers": SIGNERS,
}
json.dump(METRICS, open(OUT_DIR / "metrics.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"winner={WINNER} total_runtime={METRICS['total_runtime_s']:.0f}s -> {OUT_DIR}")'''

CELLS = [("markdown", MARKDOWN_INTRO), ("code", CELL_ENV), ("code", CELL_DATA), ("code", CELL_HELPERS),
         ("code", CELL_TRAIN_FN), ("code", CELL_MLP), ("code", CELL_BIGRU), ("code", CELL_SELECT), ("code", CELL_TEST)]


def _cell(kind: str, src: str) -> dict:
    lines = src.splitlines(keepends=True)
    if kind == "markdown":
        return {"cell_type": "markdown", "metadata": {}, "source": lines}
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines}


def build_notebook() -> dict:
    return {
        "cells": [_cell(k, s) for k, s in CELLS],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }


def as_script() -> str:
    """All code cells joined, for a local smoke run without Jupyter."""
    return "\n\n".join(s for k, s in CELLS if k == "code")


if __name__ == "__main__":
    if "--script" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        print(as_script())
    else:
        out_path = Path("vsl_alphabet_cloud_training.ipynb")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(build_notebook(), f, indent=1, ensure_ascii=False)
        print(f"Generated {out_path} ({out_path.stat().st_size} bytes)")
