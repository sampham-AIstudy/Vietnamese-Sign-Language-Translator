"""
Audit round 3 — Tier 2 in-domain test: re-run the round-2 V4 evaluation (same checkpoint,
preprocessing and split as reports/audit_round2/run_v4_generalization.py) and flag every
test clip whose recording also appears (near-identical video) in the train split.

Near-duplicate test: 5 mid-body grayscale frames (20/35/50/65/80% of the clip, 26x32),
mean |diff| < 3.0 on a 0-255 scale. Distinct recordings of the same word score ~14-16.

Output: reports/audit_round3/r3_tier2_leakage.json (+ per-sample CSV)
"""
import csv
import json
import os
import sys
from collections import defaultdict

import cv2
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from src.inference.predictor import VSLPredictor  # noqa: E402
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline  # noqa: E402

VIDEOS = "data/Dataset/Videos"
DUP_THRESHOLD = 3.0
OUT = "reports/audit_round3"


def signature(fname):
    cap = cv2.VideoCapture(os.path.join(VIDEOS, fname))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for p in (0.2, 0.35, 0.5, 0.65, 0.8):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * p))
        ok, f = cap.read()
        g = cv2.cvtColor(cv2.resize(f[40:680, 380:900], (26, 32)), cv2.COLOR_BGR2GRAY)
        frames.append(g.astype(np.float32))
    cap.release()
    return np.stack(frames)


def dialect_of(fname):
    return fname[-5] if fname[-5] in "BTN" else "Other"


train = pd.read_csv("data/splits/folds/tier2_indomain_train.csv")
test = pd.read_csv("data/splits/folds/tier2_indomain_test.csv")
train_by_gloss = defaultdict(list)
for _, r in train.iterrows():
    train_by_gloss[str(r["gloss_normalized"]).strip()].append(str(r["file_name"]).strip())

sig_cache = {}
def sig(f):
    if f not in sig_cache:
        sig_cache[f] = signature(f)
    return sig_cache[f]

predictor = VSLPredictor(model_type="stgcn", stgcn_ckpt="checkpoints/stgcn_tier2_indomain.pt",
                         classes_path="configs/tier2_classes.txt", warmup=True)
pre = VSLPreprocessingPipeline(target_len=60, vis_threshold=0.5, center_mode="mid_shoulder",
                               scale_mode="shoulder_width", temporal_mode="pad")

rows = []
for _, r in test.iterrows():
    kp = os.path.join("data", "extracted_keypoints", f"{r['video_id']}.npz")
    if not os.path.exists(kp):
        continue
    gloss, fname = str(r["gloss_normalized"]).strip(), str(r["file_name"]).strip()
    d = np.load(kp)
    seq, jm, tm = pre(d["keypoints"], d["visibility_mask"])
    pred = predictor.predict(seq, joint_mask=jm, temporal_mask=tm, top_k=5)
    diffs = [(float(np.mean(np.abs(sig(fname) - sig(t)))), t) for t in train_by_gloss[gloss]]
    best = min(diffs) if diffs else (float("inf"), "")
    rows.append({
        "video_id": r["video_id"], "file_name": fname, "dialect": dialect_of(fname), "gloss": gloss,
        "top1": int(pred["gloss"] == gloss), "top5": int(gloss in [x["gloss"] for x in pred["top5"]]),
        "closest_train_clip": best[1], "closest_train_diff": round(best[0], 3),
        "dup_in_train": int(best[0] < DUP_THRESHOLD),
    })

df = pd.DataFrame(rows)
rng = np.random.default_rng(42)

def ci(x, n_boot=1000):
    x = np.asarray(x)
    if len(x) == 0:
        return None
    b = [x[rng.integers(0, len(x), len(x))].mean() * 100 for _ in range(n_boot)]
    return [round(float(x.mean() * 100), 2), round(float(np.percentile(b, 2.5)), 2), round(float(np.percentile(b, 97.5)), 2)]

res = {
    "n": len(df), "dup_threshold": DUP_THRESHOLD,
    "overall": {"top1": ci(df.top1), "top5": ci(df.top5), "dup_rate": round(float(df.dup_in_train.mean()), 4)},
    "by_dialect": {d: {"n": int((df.dialect == d).sum()), "top1": ci(df[df.dialect == d].top1),
                       "dup_rate": round(float(df[df.dialect == d].dup_in_train.mean()), 4)} for d in ("B", "T", "N")},
    "by_dup": {k: {"n": int((df.dup_in_train == v).sum()), "top1": ci(df[df.dup_in_train == v].top1),
                   "top5": ci(df[df.dup_in_train == v].top5)} for k, v in (("dup_in_train", 1), ("clean", 0))},
    "by_dialect_and_dup": {f"{d}_{k}": {"n": int(((df.dialect == d) & (df.dup_in_train == v)).sum()),
                                        "top1": ci(df[(df.dialect == d) & (df.dup_in_train == v)].top1)}
                           for d in ("B", "T", "N") for k, v in (("dup", 1), ("clean", 0))},
    "format": "[point %, CI2.5, CI97.5] bootstrap 1000, seed 42",
}
os.makedirs(OUT, exist_ok=True)
df.to_csv(f"{OUT}/r3_tier2_leakage_per_sample.csv", index=False, encoding="utf-8")
json.dump(res, open(f"{OUT}/r3_tier2_leakage.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(res, indent=2, ensure_ascii=False))
