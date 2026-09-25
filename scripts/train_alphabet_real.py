"""
Level 1 (29 Vietnamese letters + 5 tone marks) on real recordings.

Data  : <data-dir>/manifest.csv + npz from scripts/extract_hands_batch.py
        (hauuto: 4 signers; qipedc: dictionary letter clips, external test only).
Feats : canonicalize_hand_sequence (aspect correction + left->right mirroring) then
        BiGRU  -> sequence_features_from_clip [30, 63] (handles dynamic tone marks)
        MLP    -> median palm-normalised frame [63] (static baseline)
Eval  : leave-one-signer-out over the 4 hauuto signers (unseen person each fold), reported
        overall / letters / tone marks; the model type is chosen on the LOSO mean only.
        The final model (all 4 signers) is then tested ONCE on QIPEDC letters (unseen signers,
        unseen camera). Checkpoint stores classes + preprocessing for the backend.
Usage : python scripts/train_alphabet_real.py --data-dir <alphabet_hands> --out-dir <dir> [--epochs 80]
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_alphabet_tasks import ALPHABET_CLASSES  # noqa: E402
from src.data.alphabet_preprocessing import (  # noqa: E402
    canonicalize_hand_sequence, normalize_hand_landmarks, sequence_features_from_clip)
from src.models.alphabet_mlp import VSLAlphabetMLP  # noqa: E402
from src.models.alphabet_temporal import VSLAlphabetBiGRU  # noqa: E402

SEQ_LEN = 30
TONES = {c for c in ALPHABET_CLASSES if c.startswith("dấu")}
PREPROCESSING = {"aspect_correct": True, "mirror_left_hand": True, "target_frames": SEQ_LEN,
                 "normalization": "wrist_centered_palm_scale", "extractor": "mp.solutions.hands",
                 "mediapipe_version": "0.10.14", "max_num_hands": 1, "model_complexity": 1}


def load(data_dir):
    items = []
    with open(os.path.join(data_dir, "manifest.csv"), encoding="utf-8") as f:
        for m in csv.DictReader(f):
            d = np.load(os.path.join(data_dir, m["landmark_path"]))
            lms, det, mirrored = canonicalize_hand_sequence(
                d["raw_landmarks"], d["detected_mask"], d["handedness_label"],
                aspect_ratio=float(m["width"]) / float(m["height"]))
            if det.sum() < 3:
                continue
            seq = sequence_features_from_clip(lms, det, SEQ_LEN)
            static = normalize_hand_landmarks(np.median(lms[det], axis=0)).reshape(-1).astype(np.float32)
            items.append({"sample_id": m["sample_id"], "signer": m["signer_id"], "source": m["source"],
                          "label": ALPHABET_CLASSES.index(m["symbol"]), "symbol": m["symbol"],
                          "seq": seq, "static": static, "mirrored": mirrored, "det_rate": float(det.mean())})
    return items


def augment(x, rng):
    """Small rotation (z axis), scale and jitter on palm-normalised coordinates."""
    shape = x.shape
    pts = x.reshape(*shape[:-1], 21, 3) if shape[-1] == 63 else x
    th = rng.uniform(-0.25, 0.25)
    rot = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]], dtype=np.float32)
    pts = pts @ rot.T * rng.uniform(0.9, 1.1) + rng.normal(0, 0.02, size=pts.shape).astype(np.float32)
    return pts.reshape(shape).astype(np.float32)


def build(kind, n_classes):
    return (VSLAlphabetBiGRU(input_dim=63, hidden_dim=64, num_layers=2, num_classes=n_classes)
            if kind == "bigru" else VSLAlphabetMLP(input_dim=63, num_classes=n_classes))


def fit(kind, train, epochs, device, seed):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    key = "seq" if kind == "bigru" else "static"
    model = build(kind, len(ALPHABET_CLASSES)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=1e-5)
    X = np.stack([t[key] for t in train]); Y = np.array([t["label"] for t in train])
    for _ in range(epochs):
        model.train()
        for b in np.array_split(rng.permutation(len(X)), max(1, len(X) // 32)):
            xb = torch.tensor(np.stack([augment(x, rng) for x in X[b]]), device=device)
            loss = F.cross_entropy(model(xb), torch.tensor(Y[b], device=device), label_smoothing=0.05)
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()
    return model


@torch.no_grad()
def evaluate(model, kind, items, device):
    from sklearn.metrics import f1_score
    key = "seq" if kind == "bigru" else "static"
    model.eval()
    logits = model(torch.tensor(np.stack([t[key] for t in items]), device=device)).float().cpu().numpy()
    y = np.array([t["label"] for t in items]); p = logits.argmax(1)
    top3 = np.argsort(-logits, 1)[:, :3]
    def part(mask):
        if not mask.any():
            return None
        return {"n": int(mask.sum()), "top1": float((p[mask] == y[mask]).mean() * 100),
                "top3": float(np.mean([a in b for a, b in zip(y[mask], top3[mask])]) * 100)}
    is_tone = np.array([ALPHABET_CLASSES[l] in TONES for l in y])
    present = sorted(set(y.tolist()))
    return ({"overall": part(np.ones_like(y, bool)), "letters": part(~is_tone), "tones": part(is_tone),
             "macro_f1": float(f1_score(y, p, labels=present, average="macro", zero_division=0) * 100)},
            [(t["sample_id"], ALPHABET_CLASSES[a], ALPHABET_CLASSES[b]) for t, a, b in zip(items, y, p)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    items = load(args.data_dir)
    hauuto = [t for t in items if t["source"] == "hauuto"]
    external = [t for t in items if t["source"] == "qipedc"]
    signers = sorted({t["signer"] for t in hauuto})
    print(f"hauuto {len(hauuto)} clips / signers {signers} | qipedc letters {len(external)} | "
          f"mirrored clips {sum(t['mirrored'] for t in items)} | classes {len(ALPHABET_CLASSES)}", flush=True)

    loso = defaultdict(list)
    for kind in ("bigru", "mlp"):
        for s in signers:
            model = fit(kind, [t for t in hauuto if t["signer"] != s], args.epochs, device, args.seed)
            m, _ = evaluate(model, kind, [t for t in hauuto if t["signer"] == s], device)
            loso[kind].append({"test_signer": s, **m})
            fmt = lambda part: f"{m[part]['top1']:.1f}" if m[part] else "n/a"
            print(f"[LOSO {kind}] test={s} top1={fmt('overall')} letters={fmt('letters')} tones={fmt('tones')}", flush=True)

    def mean(kind, part):
        v = [f[part]["top1"] for f in loso[kind] if f[part]]
        return {"mean": float(np.mean(v)), "std": float(np.std(v))}
    summary = {k: {p: mean(k, p) for p in ("overall", "letters", "tones")} for k in loso}
    winner = max(summary, key=lambda k: summary[k]["overall"]["mean"])  # chosen on LOSO only

    final = fit(winner, hauuto, args.epochs, device, args.seed)
    ext, ext_preds = evaluate(final, winner, external, device) if external else (None, [])
    ckpt = {"model_type": winner, "state_dict": final.state_dict(), "classes": ALPHABET_CLASSES,
            "num_classes": len(ALPHABET_CLASSES), "input_dim": 63, "preprocessing": PREPROCESSING,
            "hparams": {"hidden_dim": 64, "num_layers": 2} if winner == "bigru" else {"hidden_dims": [128, 64]},
            "loso_summary": summary, "trained_on": {"source": "hauuto", "signers": signers, "clips": len(hauuto)}}
    torch.save(ckpt, os.path.join(args.out_dir, "alphabet_real_best.pt"))
    with open(os.path.join(args.out_dir, "external_test_predictions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["sample_id", "true", "pred"]); w.writerows(ext_preds)
    report = {"loso_folds": loso, "loso_summary": summary, "winner_by_loso": winner,
              "external_qipedc_letters": ext, "clips": {"hauuto": len(hauuto), "qipedc": len(external)},
              "per_signer_clip_counts": dict(Counter(t["signer"] for t in items))}
    json.dump(report, open(os.path.join(args.out_dir, "alphabet_report.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"loso_summary": summary, "winner": winner, "external": ext}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
