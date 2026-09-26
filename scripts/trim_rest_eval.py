"""
Does the dictionary clip structure (rest -> sign -> rest) explain the cross-source failure? No retraining:
the unified model is run on each clip as stored and on the clip trimmed to its active part
(frames with a hand raised above the lower 40% of the torso, +/- 3 frames like the VSL-GH segment export).

Sets: cross_source  QIPEDC test clips of words that have VSL-GH training data (the 0/31 group, local ones)
      qipedc_test   QIPEDC test clips available locally
      hcmue         HCMUE clips whose word is in the model's classes
      s06           control: VSL-GH S06 segments (already cut to the sign; trimming should change little)
Usage: python scripts/trim_rest_eval.py --ckpt <stgcn_unified_best.pt> --out <json>
"""
import argparse
import csv
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)
from compare_isolated_models import Model, wilson  # noqa: E402  (chdirs to ROOT)
from build_label_inventory import normalize_label  # noqa: E402

PAD = 3


def active_span(k, v):
    """First..last frame where a hand is present and its wrist is above the lower 40% of the torso."""
    with np.errstate(invalid="ignore"):
        sh = np.nanmean(np.where(v[:, [11, 12], None], k[:, [11, 12], :2], np.nan), 1)[:, 1]
        hp = np.nanmean(np.where(v[:, [23, 24], None], k[:, [23, 24], :2], np.nan), 1)[:, 1]
    thr = np.nanmedian(sh) + 0.6 * (np.nanmedian(hp) - np.nanmedian(sh))
    act = np.zeros(len(k), bool)
    for w, sl in ((25, slice(25, 46)), (46, slice(46, 67))):
        act |= v[:, sl].any(1) & (k[:, w, 1] < thr)
    idx = np.flatnonzero(act)
    if len(idx) < 4 or not np.isfinite(thr):
        return 0, len(k)
    return max(0, idx[0] - PAD), min(len(k), idx[-1] + PAD + 1)


def run(model, rows):
    res = {"full": [], "trimmed": [], "kept_fraction": []}
    for r in rows:
        d = np.load(r["npz"])
        k, v = d["keypoints"].astype(np.float32), d["visibility_mask"].astype(np.float32)
        a, b = active_span(k, v > 0.5)
        res["kept_fraction"].append((b - a) / len(k))
        for key, (kk, vv) in (("full", (k, v)), ("trimmed", (k[a:b], v[a:b]))):
            seq, jm, tm = model.pipe(raw_keypoints=kk, visibility=vv,
                                     aspect_ratio=r["width"] / r["height"] if model.aspect else None)
            out = model.pred.predict(seq, joint_mask=jm, temporal_mask=tm, top_k=5)
            top5 = [normalize_label(x["gloss"]) for x in out["top5"]]
            res[key].append((int(normalize_label(out["gloss"]) == r["label"]), int(r["label"] in top5)))
    summary = {"n": len(rows), "kept_fraction_median": float(np.median(res["kept_fraction"]))}
    for key in ("full", "trimmed"):
        t = np.array(res[key])
        summary[key] = {"top1": round(100 * t[:, 0].mean(), 1), "top1_ci": wilson(int(t[:, 0].sum()), len(t)),
                        "top5": round(100 * t[:, 1].mean(), 1)}
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    model = Model("new", args.ckpt)
    test = pd.read_csv("data/splits/unified/test.csv")
    train = pd.read_csv("data/splits/unified/train.csv")
    vcls = set(train.loc[train.source == "vslgh", "gloss_normalized"])
    row = lambda r: {"label": r.gloss_normalized, "npz": os.path.join("data/processed", r.npz_path),
                     "width": float(r.width), "height": float(r.height)}
    q = [row(r) for r in test.itertuples() if r.source == "qipedc" and os.path.exists(os.path.join("data/processed", r.npz_path))]
    sets = {"cross_source": [x for x in q if x["label"] in vcls], "qipedc_test": q,
            "s06": [row(r) for r in test.itertuples() if r.source == "vslgh"][:400]}
    man = "data/processed/hcmue_all_kps/manifest.csv"
    man = man if os.path.exists(man) else "data/processed/hcmue_kps/manifest.csv"
    sets["hcmue"] = [{"label": normalize_label(m["label"]), "npz": os.path.join(os.path.dirname(man), m["npz_file"]),
                      "width": float(m["width"]), "height": float(m["height"])}
                     for m in csv.DictReader(open(man, encoding="utf-8")) if normalize_label(m["label"]) in model.labels]
    out = {name: run(model, rows) for name, rows in sets.items()}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
