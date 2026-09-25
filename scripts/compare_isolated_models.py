"""
Level 2 gate: old backend model vs new unified model on clips NEITHER model has seen.

Sets (labels restricted to the intersection of both label spaces, compared after normalize_label):
  qipedc_fair : unified TEST QIPEDC rows whose recording group is not in the old model's train/val
                (data/splits/folds/tier2_indomain_{train,val}.csv) -> unseen recording for both
  s06_fair    : unified TEST VSL-GH rows (signer S06; the old model never saw VSL-GH)
  hcmue       : HCMUE crawl (tudienngonngukyhieu.com, other signers), external for both models
Each model gets its own preprocessing (aspect correction only if its checkpoint says so) through
VSLPreprocessingPipeline, i.e. the same path as VSLDataset. Sanity check: the new model's accuracy on
its full unified test must reproduce metrics.json (--new-metrics).
Reports Top-1/Top-5 with Wilson 95% CI and an exact McNemar test on the paired Top-1 outcomes.
HCMUE has no signer IDs; results are broken down by the page's region field (not a signer).

Usage: python scripts/compare_isolated_models.py --new-ckpt <run>/stgcn_unified_best.pt \
         --new-metrics <run>/metrics.json --data-root <dir with qipedc_kps/ vslgh_segments/> \
         [--hcmue-dir data/processed/hcmue_kps] --out <json>
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
from build_label_inventory import normalize_label  # noqa: E402
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline  # noqa: E402
from src.inference.predictor import VSLPredictor  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * (c - h), 2), round(100 * (c + h), 2)]


def mcnemar_exact(a, b):
    """Two-sided exact McNemar p-value for paired 0/1 outcomes."""
    from scipy.stats import binomtest
    n01 = int(np.sum((a == 0) & (b == 1)))
    n10 = int(np.sum((a == 1) & (b == 0)))
    if n01 + n10 == 0:
        return {"old_only": n10, "new_only": n01, "p": 1.0}
    return {"old_only": n10, "new_only": n01, "p": float(binomtest(n01, n01 + n10, 0.5).pvalue)}


class Model:
    def __init__(self, name, ckpt, classes_path=None):
        self.name = name
        self.pred = VSLPredictor(model_type="stgcn", stgcn_ckpt=ckpt, classes_path=classes_path, warmup=False)
        p = self.pred.preprocessing
        self.aspect = bool(p.get("aspect_correct", False))
        self.pipe = VSLPreprocessingPipeline(
            target_len=p.get("target_len", 60), vis_threshold=p.get("vis_threshold", 0.5),
            center_mode=p.get("center_mode", "mid_shoulder"), scale_mode=p.get("scale_mode", "shoulder_width"),
            temporal_mode=p.get("temporal_mode", "pad"))
        self.labels = {normalize_label(c) for c in self.pred.class_names}

    def run(self, npz_path, width, height):
        d = np.load(npz_path)
        ar = float(width) / float(height) if self.aspect else None
        seq, jm, tm = self.pipe(raw_keypoints=d["keypoints"].astype(np.float32),
                                visibility=d["visibility_mask"].astype(np.float32), aspect_ratio=ar)
        out = self.pred.predict(seq, joint_mask=jm, temporal_mask=tm, top_k=5)
        return normalize_label(out["gloss"]), [normalize_label(x["gloss"]) for x in out["top5"]]


def score(model, rows):
    t1, t5 = [], []
    for r in rows:
        g, top5 = model.run(r["npz"], r["width"], r["height"])
        t1.append(int(g == r["label"]))
        t5.append(int(r["label"] in top5))
    return np.array(t1), np.array(t5)


def summary(t1, t5):
    n = len(t1)
    return {"n": n, "top1": round(100 * t1.mean(), 2) if n else None, "top1_ci": wilson(int(t1.sum()), n),
            "top5": round(100 * t5.mean(), 2) if n else None, "top5_ci": wilson(int(t5.sum()), n)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-ckpt", required=True)
    ap.add_argument("--new-metrics")
    ap.add_argument("--new-classes", help="only for checkpoints without label_map (smoke tests)")
    ap.add_argument("--old-ckpt", default="checkpoints/stgcn_tier2_indomain.pt")
    ap.add_argument("--old-classes", default="configs/tier2_classes.txt")
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--manifest-dir", default="data/splits/unified")
    ap.add_argument("--hcmue-dir", default="data/processed/hcmue_kps")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    old, new = Model("old", args.old_ckpt, args.old_classes), Model("new", args.new_ckpt, args.new_classes)
    both = old.labels & new.labels
    groups = dict(pd.read_csv("data/splits/recording_groups.csv")[["file_name", "recording_group"]]
                  .assign(file_name=lambda d: d.file_name.str.lower()).values)
    old_seen = pd.concat([pd.read_csv(f"data/splits/folds/tier2_indomain_{s}.csv") for s in ("train", "val")])
    old_seen_groups = {groups.get(str(f).strip().lower()) for f in old_seen.file_name}

    test = pd.read_csv(os.path.join(args.manifest_dir, "test.csv"))
    def row(r):
        return {"id": r.video_id, "label": r.gloss_normalized, "npz": os.path.join(args.data_root, r.npz_path),
                "width": r.width, "height": r.height, "source": r.source}
    all_test = [row(r) for r in test.itertuples()]
    sets = {
        "qipedc_fair": [row(r) for r in test.itertuples() if r.source == "qipedc"
                        and r.recording_group not in old_seen_groups and r.gloss_normalized in both],
        "s06_fair": [row(r) for r in test.itertuples() if r.source == "vslgh" and r.gloss_normalized in both],
    }
    hcmue = []
    man = os.path.join(args.hcmue_dir, "manifest.csv")
    if os.path.exists(man):
        region = {r["VIDEO"]: r["REGION"] for r in csv.DictReader(open(os.path.join(args.hcmue_dir, "hcmue_overlap_labels.csv"), encoding="utf-8"))}
        for m in csv.DictReader(open(man, encoding="utf-8")):
            hcmue.append({"id": m["file_name"], "label": normalize_label(m["label"]),
                          "npz": os.path.join(args.hcmue_dir, m["npz_file"]),
                          "width": m["width"], "height": m["height"], "region": region.get(m["file_name"], "?")})
        sets["hcmue_fair"] = [r for r in hcmue if r["label"] in both]

    missing = {}
    for name in list(sets):
        missing[name] = sum(not os.path.exists(r["npz"]) for r in sets[name])
        sets[name] = [r for r in sets[name] if os.path.exists(r["npz"])]
    report = {"label_spaces": {"old": len(old.labels), "new": len(new.labels), "both": len(both)},
              "missing_npz": missing, "sets": {}}
    if args.new_metrics:  # sanity: our preprocessing path reproduces the training script's test score
        t1, _ = score(new, [r for r in all_test if os.path.exists(r["npz"])])
        ref = json.load(open(args.new_metrics, encoding="utf-8"))["test_overall"]["top1"]
        report["sanity_new_full_test"] = {"reproduced_top1": round(100 * t1.mean(), 2), "metrics_json_top1": round(ref, 2)}
        print("sanity:", report["sanity_new_full_test"], flush=True)
    for name, rows in sets.items():
        o1, o5 = score(old, rows)
        n1, n5 = score(new, rows)
        entry = {"old": summary(o1, o5), "new": summary(n1, n5), "mcnemar_top1": mcnemar_exact(o1, n1),
                 "labels": len({r["label"] for r in rows})}
        if name == "hcmue_fair":
            by = defaultdict(list)
            for i, r in enumerate(rows):
                by[r["region"]].append(i)
            entry["by_region_not_signer"] = {g: {"n": len(ix), "old_top1": round(100 * o1[ix].mean(), 1),
                                                 "new_top1": round(100 * n1[ix].mean(), 1)} for g, ix in sorted(by.items())}
        report["sets"][name] = entry
        print(name, json.dumps(entry, ensure_ascii=False), flush=True)
    if hcmue:  # new model on every HCMUE clip whose label it knows (not only the shared labels)
        rows = [r for r in hcmue if r["label"] in new.labels]
        n1, n5 = score(new, rows)
        report["hcmue_new_all_known_labels"] = summary(n1, n5)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(report, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
