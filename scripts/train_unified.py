"""
Train the isolated-sign recogniser on the unified manifest (scripts/build_unified_manifest.py).

- Model/preprocessing identical to what the backend loads (STGCNModel, 67 joints, 60 frames),
  plus aspect correction; the checkpoint records label_map + preprocessing so VSLPredictor /
  RealtimePipeline reproduce the training input exactly (aspect_correct follows the checkpoint).
- Class-balanced sampling (weights 1/sqrt(class count)) so 1-2-sample classes are seen.
- Model selection on VAL only; TEST is evaluated once at the end and reported per source:
    qipedc -> unseen recording of a dictionary sign, vslgh -> unseen signer (S06).
Usage:
  python scripts/train_unified.py --data-root <dir with qipedc_kps/ and vslgh_segments/> \
      --out-dir <dir> [--epochs 120] [--batch-size 64] [--skip-missing] [--max-batches N]
"""
import argparse
import csv
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from src.data.collate import vsl_collate_fn  # noqa: E402
from src.data.vsl_dataset import VSLDataset, validate_split_guards  # noqa: E402
from src.models.stgcn_model import STGCNModel  # noqa: E402
from src.training.trainer import VSLTrainer  # noqa: E402

MODEL_CFG = dict(num_joints=67, in_channels=3, graph_strategy="spatial", channel_dims=[64, 64, 128],
                 dropout=0.25, temporal_kernel_size=9)  # must match src/inference/predictor.py
PREPROCESSING = dict(aspect_correct=True, target_len=60, vis_threshold=0.5, center_mode="mid_shoulder",
                     scale_mode="shoulder_width", temporal_mode="pad", extractor="CleanHolisticExtractor",
                     mediapipe_version="0.10.14", joints="pose25+lh21+rh21")


def set_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


def materialise(manifest_dir, data_root, out_dir, skip_missing):
    """Copy split CSVs with absolute npz_path; optionally drop rows whose npz is absent (smoke tests)."""
    paths, missing = {}, Counter()
    for split in ("train", "val", "test"):
        with open(os.path.join(manifest_dir, f"{split}.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        kept = []
        for r in rows:
            r["npz_path"] = os.path.join(data_root, r["npz_path"])
            if not os.path.exists(r["npz_path"]):
                missing[split] += 1
                if skip_missing:
                    continue
                raise FileNotFoundError(f"{split}: {r['npz_path']} (use --skip-missing only for smoke tests)")
            kept.append(r)
        paths[split] = os.path.join(out_dir, f"{split}_resolved.csv")
        with open(paths[split], "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(kept)
    return paths, dict(missing)


VSLGH_TEST_ONLY = {"S06"}  # held out for the Level 2 -> Level 3 end-to-end evaluation


def assert_split_integrity(paths):
    """Hard FAIL (no silent skip) unless: every QIPEDC row has a recording_group and each group sits in
    exactly one split; VSL-GH signers are disjoint across splits and S06 appears in test only."""
    group_splits, signer_splits, problems = defaultdict(set), defaultdict(set), []
    for split, path in paths.items():
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["source"] == "qipedc":
                    if not r["recording_group"].strip():
                        problems.append(f"{split}: {r['video_id']} has no recording_group")
                    group_splits[r["recording_group"]].add(split)
                elif r["source"] == "vslgh":
                    signer_splits[r["signer_id"]].add(split)
    crossing = {g: sorted(s) for g, s in group_splits.items() if len(s) > 1}
    if crossing:
        problems.append(f"{len(crossing)} QIPEDC recording groups in more than one split, e.g. {list(crossing.items())[:5]}")
    shared = {s: sorted(v) for s, v in signer_splits.items() if len(v) > 1}
    if shared:
        problems.append(f"VSL-GH signers in more than one split: {shared}")
    leaked = {s: sorted(v) for s, v in signer_splits.items() if s in VSLGH_TEST_ONLY and v != {"test"}}
    if leaked:
        problems.append(f"held-out VSL-GH signer outside test: {leaked}")
    if problems:
        raise RuntimeError("split integrity FAIL: " + " | ".join(problems))
    return {"status": "PASS", "qipedc_recording_groups": len(group_splits),
            "vslgh_signers": {s: sorted(v) for s, v in sorted(signer_splits.items())}}


@torch.no_grad()
def predict_all(model, loader, device):
    model.eval()
    logits_all, labels_all = [], []
    for b in loader:
        with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
            out = model(sequences=b["sequences"].to(device), joint_masks=b["joint_masks"].to(device),
                        temporal_masks=b["temporal_masks"].to(device))
        logits_all.append(out.float().cpu()); labels_all.append(b["labels"])
    return torch.cat(logits_all).numpy(), torch.cat(labels_all).numpy()


def summarise(logits, labels, n_classes):
    from sklearn.metrics import f1_score
    pred = logits.argmax(1)
    top5 = np.argsort(-logits, 1)[:, :5]
    present = sorted(set(labels.tolist()))
    return {"n": int(len(labels)), "top1": float((pred == labels).mean() * 100),
            "top5": float(np.mean([l in t for l, t in zip(labels, top5)]) * 100),
            "macro_f1_present_classes": float(f1_score(labels, pred, labels=present, average="macro", zero_division=0) * 100)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest-dir", default="data/splits/unified")
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-missing", action="store_true")
    ap.add_argument("--max-batches", type=int, default=None)
    args = ap.parse_args()
    set_seed(args.seed)
    os.makedirs(args.out_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    classes = [l.strip() for l in open(os.path.join(args.manifest_dir, "classes.txt"), encoding="utf-8") if l.strip()]
    label_map = {c: i for i, c in enumerate(classes)}
    paths, missing = materialise(args.manifest_dir, args.data_root, args.out_dir, args.skip_missing)
    guard = validate_split_guards(paths["train"], paths["val"], paths["test"])
    print("split guards:", guard["status"], "| duplicate-recording check:", guard["duplicate_recording_check"], "| missing npz:", missing)
    if str(guard["duplicate_recording_check"]).startswith("SKIPPED"):
        raise RuntimeError("split integrity FAIL: duplicate-recording check was skipped (recording_groups.csv missing)")
    integrity = assert_split_integrity(paths)
    print("split integrity:", json.dumps(integrity), flush=True)

    common = dict(label_map=label_map, target_len=60, auto_extract=False, aspect_correct=True)
    train_ds = VSLDataset(paths["train"], augment=True, **common)
    val_ds = VSLDataset(paths["val"], **common)
    test_ds = VSLDataset(paths["test"], **common)
    counts = Counter(r["gloss_normalized"] for r in train_ds.samples)
    weights = [1.0 / math.sqrt(counts[r["gloss_normalized"]]) for r in train_ds.samples]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True,
                                    generator=torch.Generator().manual_seed(args.seed))
    dl = dict(batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=vsl_collate_fn,
              pin_memory=device.type == "cuda")
    train_loader = DataLoader(train_ds, sampler=sampler, **dl)
    val_loader = DataLoader(val_ds, shuffle=False, **dl)
    test_loader = DataLoader(test_ds, shuffle=False, **dl)
    print(f"classes {len(classes)} | train {len(train_ds)} val {len(val_ds)} test {len(test_ds)} | device {device}")

    model = STGCNModel(num_classes=len(classes), **MODEL_CFG)
    ckpt_path = os.path.join(args.out_dir, "stgcn_unified_best.pt")
    trainer = VSLTrainer(model, train_loader, val_loader, lr=args.lr, patience=args.patience, device=device,
                         checkpoint_path=ckpt_path, history_path=os.path.join(args.out_dir, "history.json"),
                         max_batches=args.max_batches)
    summary = trainer.fit(epochs=args.epochs, verbose=True)

    # Final checkpoint: best weights + everything inference needs to reproduce training input.
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    ckpt.pop("optimizer_state_dict", None)
    ckpt.update({"label_map": label_map, "num_classes": len(classes), "preprocessing": PREPROCESSING,
                 "model_config": MODEL_CFG, "manifest_report": json.load(open(os.path.join(args.manifest_dir, "report.json"), encoding="utf-8")),
                 "seed": args.seed})
    torch.save(ckpt, ckpt_path)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)

    # TEST — once, after selection on VAL.
    logits, labels = predict_all(model, test_loader, device)
    rows = test_ds.samples
    src = np.array([r["source"] for r in rows])
    cls_has_vslgh = {r["gloss_normalized"] for r in train_ds.samples if r["source"] == "vslgh"}
    grp = np.array(["vslgh_class" if r["gloss_normalized"] in cls_has_vslgh else "qipedc_only_class" for r in rows])
    metrics = {"val_best": {"epoch": summary["best_epoch"], "top1": summary["best_val_top1"]},
               "test_overall": summarise(logits, labels, len(classes)),
               "test_by_source": {s: summarise(logits[src == s], labels[src == s], len(classes)) for s in sorted(set(src))},
               "test_by_class_group": {g: summarise(logits[grp == g], labels[grp == g], len(classes)) for g in sorted(set(grp))},
               "train_samples_per_class_hist": dict(sorted(Counter(counts.values()).items())),
               "missing_npz": missing, "split_integrity": integrity, "smoke": bool(args.skip_missing or args.max_batches)}
    pred = logits.argmax(1)
    # raw test logits so reports (groups, Top-5, CIs, model comparisons) are recomputed from files
    np.savez_compressed(os.path.join(args.out_dir, "test_logits.npz"), logits=logits.astype(np.float16),
                        labels=labels, video_ids=np.array([r["video_id"] for r in rows]))
    with open(os.path.join(args.out_dir, "test_predictions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["video_id", "source", "signer_id", "true", "pred", "confidence", "correct", "top5"])
        prob = torch.softmax(torch.tensor(logits), 1).numpy()
        for r, t, p, pr, lg in zip(rows, labels, pred, prob, logits):
            top5 = "|".join(classes[i] for i in np.argsort(-lg)[:5])
            w.writerow([r["video_id"], r["source"], r.get("signer_id", ""), classes[t], classes[p], f"{pr[p]:.4f}",
                        int(t == p), top5])
    per_class = defaultdict(lambda: [0, 0])
    for t, p in zip(labels, pred):
        per_class[classes[t]][0] += int(t == p); per_class[classes[t]][1] += 1
    with open(os.path.join(args.out_dir, "test_per_class.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["label", "train_samples", "test_samples", "test_correct", "test_acc"])
        for c, (ok, n) in sorted(per_class.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
            w.writerow([c, counts.get(c, 0), n, ok, f"{ok / n:.3f}"])
    json.dump(metrics, open(os.path.join(args.out_dir, "metrics.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
