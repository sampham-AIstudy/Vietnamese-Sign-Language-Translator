"""
Why does the Level 2 model separate video sources? (step 1 + 2 of the (c) investigation)

Step 1: a source classifier (VSL-GH vs QIPEDC vs HCMUE) on summaries of the MODEL INPUT
        (VSLPreprocessingPipeline output as the unified model sees it: aspect-corrected, shoulder-centred,
        60 frames + joint/temporal masks). GroupKFold by recording (VSL-GH sentence video, QIPEDC recording
        group, HCMUE video). All features, then each feature group alone, then all-but-one group.
Step 2: raw per-source statistics of the stored keypoints (before preprocessing).

Usage: python scripts/source_diagnostics.py --out reports/source_diagnostics_2026-09-26 [--vslgh-n 1500]
"""
import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline  # noqa: E402

POSE, LH, RH = slice(0, 25), slice(25, 46), slice(46, 67)


def load_sources(vslgh_n, seed):
    rows = []
    seg = pd.read_csv("data/processed/vslgh_segments/segments.csv").sample(vslgh_n, random_state=seed)
    for r in seg.itertuples():
        rows.append({"source": "vslgh", "path": r.npz_path, "group": r.video_id.rsplit("_g", 1)[0],
                     "width": r.width, "height": r.height, "fps": 30.0, "label": r.label})
    rg = pd.read_csv("data/splits/recording_groups.csv")
    grp = dict(zip(rg.file_name.str.lower().str.replace(".mp4", "", regex=False), rg.recording_group))
    for p in sorted(glob.glob("data/processed/qipedc_kps/*.npz")):
        stem = os.path.splitext(os.path.basename(p))[0]
        rows.append({"source": "qipedc", "path": p, "group": grp.get(stem.lower(), stem), "width": 1280, "height": 720,
                     "fps": None, "label": None})
    man = "data/processed/hcmue_all_kps/manifest.csv"
    if not os.path.exists(man):
        man = "data/processed/hcmue_kps/manifest.csv"
    for m in csv.DictReader(open(man, encoding="utf-8")):
        rows.append({"source": "hcmue", "path": os.path.join(os.path.dirname(man), m["npz_file"]), "group": m["file_name"],
                     "width": int(m["width"]), "height": int(m["height"]), "fps": float(m["fps"]), "label": m["label"]})
    return rows


def features(seq, jm, tm):
    """Clip summary of the model input, by named group."""
    v = tm > 0.5
    s, j = seq[v], jm[v]
    f = {}
    f["time"] = np.array([v.mean()])
    f["presence"] = j.mean(0)                                             # 67 joint presence rates
    def stats(block, mask):
        x = np.where(mask[..., None] > 0.5, block, np.nan)
        return np.concatenate([np.nanmean(x, 0).ravel(), np.nanstd(x, 0).ravel()])
    f["pose_xy"] = stats(s[:, POSE, :2], j[:, POSE])
    f["pose_z"] = stats(s[:, POSE, 2:], j[:, POSE])
    hands = np.concatenate([s[:, LH], s[:, RH]], 1)
    hmask = np.concatenate([j[:, LH], j[:, RH]], 1)
    f["hand_xy"] = stats(hands[..., :2], hmask)
    f["hand_z"] = stats(hands[..., 2:], hmask)
    shape = []
    for sl in (LH, RH):                                                  # hand shape: wrist-centred, hand-size scaled
        h, m = s[:, sl], j[:, sl].min(1) > 0.5
        if m.sum() < 2:
            shape.append(np.full(63, np.nan)); continue
        h = h[m] - h[m][:, :1]
        size = np.linalg.norm(h[:, 9, :2], axis=-1, keepdims=True)[..., None] + 1e-6
        shape.append((h / size).mean(0).ravel())
    f["hand_shape"] = np.concatenate(shape)
    return {k: np.nan_to_num(np.asarray(x, np.float64), nan=0.0) for k, x in f.items()}


def raw_stats(rows):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        d = np.load(r["path"])
        k = d["keypoints"].astype(np.float32)
        vis = d["visibility_mask"].astype(np.float32) > 0.5
        a = acc[r["source"]]
        a["frames"].append(len(k))
        a["lh_present"].append(vis[:, LH].all(1).mean()); a["rh_present"].append(vis[:, RH].all(1).mean())
        a["no_hand"].append((~vis[:, LH].any(1) & ~vis[:, RH].any(1)).mean())
        a["pose_present"].append(vis[:, POSE].mean())
        a["joint_present"].append(vis.mean(0))
        kk = np.where(vis[..., None], k, np.nan)
        a["pose_z"].append(np.nanmedian(kk[:, POSE, 2])); a["hand_z_spread"].append(np.nanstd(kk[:, 25:, 2]))
        a["x_span"].append(np.nanpercentile(kk[..., 0], 95) - np.nanpercentile(kk[..., 0], 5))
        a["nan_where_missing"].append(bool(np.isnan(k[~vis]).all()) if (~vis).any() else True)
        a["dtype"].append(str(d["keypoints"].dtype))
        if r["fps"]:
            a["fps"].append(r["fps"])
        a["resolution"].append(f"{r['width']}x{r['height']}")
    out = {}
    for s, a in acc.items():
        jp = np.mean(a["joint_present"], 0)
        out[s] = {"clips": len(a["frames"]), "frames_median": float(np.median(a["frames"])),
                  "fps": sorted(set(round(x) for x in a["fps"])) if a["fps"] else "n/a",
                  "resolution": sorted(set(a["resolution"]))[:5], "dtype": sorted(set(a["dtype"])),
                  **{k: float(np.mean(a[k])) for k in ("lh_present", "rh_present", "no_hand", "pose_present",
                                                       "pose_z", "hand_z_spread", "x_span")},
                  "missing_stored_as_nan": float(np.mean(a["nan_where_missing"])),
                  "joints_never_present": [int(i) for i in np.flatnonzero(jp < 0.01)],
                  "joints_present_lt_50pct": [int(i) for i in np.flatnonzero(jp < 0.5)]}
    return out


def classify(X, y, groups, seed=0):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    pred = np.empty_like(y)
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.5, class_weight="balanced"))
        clf.fit(X[tr], y[tr]); pred[te] = clf.predict(X[te])
    labels = sorted(set(y))
    return {"balanced_accuracy": round(100 * balanced_accuracy_score(y, pred), 1),
            "confusion": {"labels": labels, "matrix": confusion_matrix(y, pred, labels=labels).tolist()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--vslgh-n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rows = load_sources(args.vslgh_n, args.seed)
    pipe = VSLPreprocessingPipeline(target_len=60)  # unified model settings (defaults) + aspect correction below
    feats, keep = [], []
    for r in rows:
        d = np.load(r["path"])
        seq, jm, tm = pipe(raw_keypoints=d["keypoints"].astype(np.float32),
                           visibility=d["visibility_mask"].astype(np.float32),
                           aspect_ratio=float(r["width"]) / float(r["height"]))
        feats.append(features(seq, jm, tm)); keep.append(r)
    y = np.array([r["source"] for r in keep]); g = np.array([r["group"] for r in keep])
    names = list(feats[0])
    block = {n: np.stack([f[n] for f in feats]) for n in names}
    res = {"n_by_source": {s: int((y == s).sum()) for s in sorted(set(y))}, "chance_balanced_accuracy": round(100 / len(set(y)), 1),
           "all_features": classify(np.hstack([block[n] for n in names]), y, g),
           "single_group": {n: classify(block[n], y, g)["balanced_accuracy"] for n in names},
           "all_but_group": {n: classify(np.hstack([block[m] for m in names if m != n]), y, g)["balanced_accuracy"] for n in names},
           "feature_dims": {n: int(block[n].shape[1]) for n in names}}
    two = y != "hcmue"
    res["vslgh_vs_qipedc_all"] = classify(np.hstack([block[n] for n in names])[two], y[two], g[two])["balanced_accuracy"]
    res["vslgh_vs_qipedc_single_group"] = {n: classify(block[n][two], y[two], g[two])["balanced_accuracy"] for n in names}
    res["raw_stats"] = raw_stats(keep)
    json.dump(res, open(os.path.join(args.out, "source_diagnostics.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "raw_stats"}, indent=1, ensure_ascii=False))
    print(json.dumps(res["raw_stats"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
