"""
Level 1 nested leave-one-signer-out (unbiased model selection).

Outer loop: each hauuto signer is the test person once.
Inner loop: each of the 3 remaining signers is the validation person once (train on the other 2);
the config (model MLP/BiGRU x epochs [x feature variant]) with the best mean inner-val top-1 is
retrained on all 3 and tested once on the outer signer. The test signer never influences selection.
Training recipe (fit/evaluate/augment) is the one in scripts/train_alphabet_real.py.

Feature variants for the BiGRU (the MLP always uses the static median frame):
  frame      current: resample 30 frames uniformly over detected frames by index (gaps dropped)
  time       resample 30 points uniformly in real time (container PTS, fallback i/fps) between the
             first and last detected frame, linear interpolation across missing-hand gaps
  frame_traj frame + wrist trajectory in the (otherwise always-zero) wrist slot, in palm units
  time_traj  time + wrist trajectory
Runs: one nested run per --variants entry, plus (if more than one) a nested run where the variant
is part of the inner-selected config. The final external model is selected by plain LOSO over
all 4 signers, trained on all 4, and tested once on QIPEDC letters (per clip and per distinct recording).
Usage: python scripts/train_alphabet_nested.py --data-dir <alphabet_hands> --out-dir <dir>
       [--pts-json <signer_report.json>] [--recording-groups data/splits/recording_groups.csv]
       [--variants frame time frame_traj time_traj] [--epochs-grid 20 40 80 120]
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from itertools import product

import numpy as np
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_alphabet_tasks import ALPHABET_CLASSES  # noqa: E402
from src.data.alphabet_preprocessing import DEFAULT_ALPHABET_PREPROCESSING, alphabet_clip_features  # noqa: E402
from train_alphabet_real import PREPROCESSING, evaluate, fit  # noqa: E402


VARIANTS = {  # BiGRU feature variants -> preprocessing stored in the checkpoint
    "frame": {"resample": "frame_index", "wrist_trajectory": False},
    "time": {"resample": "time", "wrist_trajectory": False},
    "frame_traj": {"resample": "frame_index", "wrist_trajectory": True},
    "time_traj": {"resample": "time", "wrist_trajectory": True},
}


def preprocessing_for(variant):
    return {**PREPROCESSING, **DEFAULT_ALPHABET_PREPROCESSING, **VARIANTS[variant]}


def load(data_dir, pts):
    items = []
    with open(os.path.join(data_dir, "manifest.csv"), encoding="utf-8") as f:
        for m in csv.DictReader(f):
            d = np.load(os.path.join(data_dir, m["landmark_path"]))
            args = (d["raw_landmarks"], d["detected_mask"], d["handedness_label"], float(m["width"]) / float(m["height"]))
            if d["detected_mask"].sum() < 3:
                continue
            t_ms = pts.get(m["sample_id"])
            if t_ms is None or len(t_ms) != len(d["detected_mask"]):
                t_ms = np.arange(len(d["detected_mask"])) * 1000.0 / float(m["fps"])
            item = {"sample_id": m["sample_id"], "signer": m["signer_id"], "source": m["source"],
                    "label": ALPHABET_CLASSES.index(m["symbol"]), "symbol": m["symbol"],
                    "static": alphabet_clip_features(*args, preprocessing=PREPROCESSING, model_type="mlp")}
            for v in VARIANTS:
                item[v] = alphabet_clip_features(*args, timestamps_ms=np.asarray(t_ms),
                                                 preprocessing=preprocessing_for(v), model_type="bigru")
            items.append(item)
    return items


def view(items, variant):
    return [{**t, "seq": t[variant]} for t in items]


def score(cfg, train, val, device, seed):
    kind, epochs, variant = cfg
    model = fit(kind, view(train, variant), epochs, device, seed)
    return evaluate(model, kind, view(val, variant), device)


def select(configs, pool, device, seed, cache):
    """Leave-one-signer-out over `pool` signers; returns the config with best mean val top-1."""
    signers = sorted({t["signer"] for t in pool})
    table = {}
    for cfg in configs:
        accs = []
        for v in signers:
            key = (cfg, tuple(signers), v)
            if key not in cache:
                m, _ = score(cfg, [t for t in pool if t["signer"] != v], [t for t in pool if t["signer"] == v], device, seed)
                cache[key] = m["overall"]["top1"]
            accs.append(cache[key])
        table[cfg] = float(np.mean(accs))
    # ties -> fewer epochs, then list order (deterministic)
    best = max(configs, key=lambda c: (table[c], -c[1]))
    return best, table


def nested(name, configs, hauuto, device, seed, cache, log):
    signers = sorted({t["signer"] for t in hauuto})
    folds, preds = [], []
    for s in signers:
        pool = [t for t in hauuto if t["signer"] != s]
        best, table = select(configs, pool, device, seed, cache)
        m, p = score(best, pool, [t for t in hauuto if t["signer"] == s], device, seed)
        folds.append({"test_signer": s, "selected": {"model": best[0], "epochs": best[1], "variant": best[2]},
                      "inner_val_top1": {"|".join(map(str, c)): v for c, v in table.items()}, **m})
        preds += [{"run": name, "test_signer": s, "sample_id": a, "true": b, "pred": c} for a, b, c in p]
        log(f"[{name}] test={s} selected={best} inner_val={table[best]:.1f} -> top1={m['overall']['top1']:.1f} "
            f"letters={m['letters']['top1']:.1f} tones={m['tones']['top1']:.1f}")
    return folds, preds


def ci_t(values):
    from scipy import stats
    v = np.asarray(values, dtype=float)
    h = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
    return {"mean": float(v.mean()), "sd": float(v.std(ddof=1)), "ci95": [float(v.mean() - h), float(v.mean() + h)],
            "min": float(v.min()), "max": float(v.max()), "n_folds": len(v)}


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(100 * (c - h)), float(100 * (c + h))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pts-json")
    ap.add_argument("--recording-groups", default=os.path.join(ROOT, "data", "splits", "recording_groups.csv"))
    ap.add_argument("--variants", nargs="+", default=["frame"])
    ap.add_argument("--epochs-grid", nargs="+", type=int, default=[20, 40, 80, 120])
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logf = open(os.path.join(args.out_dir, "nested.log"), "w", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n"); logf.flush()

    pts = {}
    if args.pts_json:
        rep = json.load(open(args.pts_json, encoding="utf-8"))
        pts = {k: np.asarray(v) for k, v in rep.get("_pts_ms", {}).items()}
    t0 = time.time()
    items = load(args.data_dir, pts)
    hauuto = [t for t in items if t["source"] == "hauuto"]
    external = [t for t in items if t["source"] == "qipedc"]
    log(f"hauuto {len(hauuto)} clips, qipedc {len(external)}, real PTS for {sum(k in pts for k in (t['sample_id'] for t in items))} clips, "
        f"device {device}, epochs grid {args.epochs_grid}, variants {args.variants}")

    cache = {}
    runs, all_preds = {}, []
    def configs_for(variants):
        mlp = [("mlp", e, "frame") for e in args.epochs_grid]  # MLP ignores the sequence variant
        return mlp + [("bigru", e, v) for v, e in product(variants, args.epochs_grid)]
    plan = [(v, [v]) for v in args.variants]
    if len(args.variants) > 1:
        plan.append(("variant_selected", args.variants))
    for name, variants in plan:
        folds, preds = nested(name, configs_for(variants), hauuto, device, args.seed, cache, log)
        runs[name] = {"folds": folds, "summary": {part: ci_t([f[part]["top1"] for f in folds])
                                                  for part in ("overall", "letters", "tones")}}
        all_preds += preds

    # final model for the external test: plain LOSO selection over all 4 signers
    main_configs = configs_for(args.variants)
    best, table = select(main_configs, hauuto, device, args.seed, cache)
    final = fit(best[0], view(hauuto, best[2]), best[1], device, args.seed)
    ext, ext_preds = evaluate(final, best[0], view(external, best[2]), device)
    groups = {}
    with open(args.recording_groups, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            groups[os.path.splitext(r["file_name"])[0]] = r["recording_group"]
    seen, correct = set(), 0
    for sid, y, p in ext_preds:
        g = groups.get(sid.replace("qipedc_", ""), sid)
        if g not in seen:
            seen.add(g); correct += int(y == p)
    ext["per_recording"] = {"n": len(seen), "top1": 100 * correct / len(seen), "wilson95": wilson(correct, len(seen))}
    log(f"[external] selected={best} -> clips top1={ext['overall']['top1']:.1f} (n={ext['overall']['n']}), "
        f"recordings top1={ext['per_recording']['top1']:.1f} (n={len(seen)})")
    all_preds += [{"run": "external", "test_signer": "qipedc", "sample_id": a, "true": b, "pred": c} for a, b, c in ext_preds]

    report = {"protocol": "nested LOSO: outer test signer, inner leave-one-signer-out validation over the 3 others",
              "epochs_grid": args.epochs_grid, "variants": args.variants, "seed": args.seed,
              "clips": {"hauuto": len(hauuto), "qipedc": len(external)},
              "runs": runs, "external": {"selected": list(best), "loso4_val_top1": table[best], **ext},
              "minutes": (time.time() - t0) / 60}
    with open(os.path.join(args.out_dir, "nested_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "nested_predictions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "test_signer", "sample_id", "true", "pred"])
        w.writeheader(); w.writerows(all_preds)
    torch.save({"model_type": best[0], "state_dict": final.state_dict(), "classes": ALPHABET_CLASSES,
                "num_classes": len(ALPHABET_CLASSES), "input_dim": 63, "selected": list(best),
                "preprocessing": preprocessing_for(best[2]),
                "hparams": {"hidden_dim": 64, "num_layers": 2} if best[0] == "bigru" else {"hidden_dims": [128, 64]},
                "epochs": best[1], "loso4_val_top1": table[best],
                "trained_on": {"source": "hauuto", "signers": sorted({t["signer"] for t in hauuto}), "clips": len(hauuto)},
                "external_qipedc": ext},
               os.path.join(args.out_dir, "alphabet_nested_final.pt"))
    log(f"done in {report['minutes']:.1f} min")


if __name__ == "__main__":
    main()
