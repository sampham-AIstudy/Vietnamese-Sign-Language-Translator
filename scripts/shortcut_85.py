"""
Step 4a — is the 100% source separation a shortcut (framing, clip length) or just two different vocabularies?

1. Classes present in both VSL-GH and QIPEDC (unified manifest, all splits).
2. Balanced set: per class, one QIPEDC clip per distinct recording group (k groups) and k VSL-GH segments from
   k different sentence recordings. Source classifier (VSL-GH vs QIPEDC) with GroupKFold by recording, per
   feature group — same features as scripts/source_diagnostics.py (model input of the unified model).
   Near 100% with the SAME words on both sides → the shortcut is real.
3. Cross-source accuracy of the current unified model on these classes minus the words signed differently
   (xem, kết quả, yếu, thường xuyên): QIPEDC clips it never trained on (val + test; val only picked the epoch),
   with S06 segments of the same classes as the same-source reference.
Usage: python scripts/shortcut_85.py --ckpt checkpoints/stgcn_unified_best.pt --out <dir> [--features legacy|harmonized ...]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from source_diagnostics import classify, features  # noqa: E402
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline  # noqa: E402

DIFFERENT_SIGN = {"xem", "kết quả", "yếu", "thường xuyên"}


def shared_classes(man):
    by = man.groupby("gloss_normalized").source.apply(set)
    return sorted(c for c, s in by.items() if {"vslgh", "qipedc"} <= s)


def balanced_rows(man, classes, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for c in classes:
        q = man[(man.source == "qipedc") & (man.gloss_normalized == c)].drop_duplicates("recording_group")
        v = man[(man.source == "vslgh") & (man.gloss_normalized == c)].copy()
        v["rec"] = v.video_id.str.rsplit("_g", n=1).str[0]
        v = v.drop_duplicates("rec")
        k = min(len(q), len(v))
        for r in q.sample(k, random_state=int(rng.integers(1e9))).itertuples():
            rows.append({"source": "qipedc", "label": c, "group": r.recording_group, "npz": r.npz_path, "w": r.width, "h": r.height})
        for r in v.sample(k, random_state=int(rng.integers(1e9))).itertuples():
            rows.append({"source": "vslgh", "label": c, "group": r.rec, "npz": r.npz_path, "w": r.width, "h": r.height})
    return rows


def feature_blocks(rows, featurize):
    feats = [featurize(r) for r in rows]
    return {n: np.stack([f[n] for f in feats]) for n in feats[0]}


def legacy_featurize(r):
    d = np.load(os.path.join("data/processed", r["npz"]))
    seq, jm, tm = PIPE(raw_keypoints=d["keypoints"].astype(np.float32), visibility=d["visibility_mask"].astype(np.float32),
                       aspect_ratio=float(r["w"]) / float(r["h"]))
    return features(seq, jm, tm)


PIPE = VSLPreprocessingPipeline(target_len=60)


def harmonized_featurizer(hand_z, kps_dir):
    """Features of the step 4b harmonised input (src/data/harmonized.py) for the same balanced rows."""
    from src.data.harmonized import harmonize

    def featurize(r):
        npz = r["npz"] if not r["npz"].startswith("qipedc_kps/") else r["npz"].replace("qipedc_kps/", kps_dir + "/", 1)
        d = np.load(os.path.join("data/processed", npz))
        fps = float(json.loads(str(d["metadata"])).get("fps") or 30.0) if "metadata" in d.files else 30.0
        seq, jm, tm = harmonize(d["keypoints"], d["visibility_mask"], float(r["w"]) / float(r["h"]), fps,
                                {"hand_z": hand_z})
        return features(seq, jm, tm)
    return featurize


def source_classifier(rows, featurize):
    y = np.array([r["source"] for r in rows]); g = np.array([r["group"] for r in rows])
    block = feature_blocks(rows, featurize)
    names = list(block)
    return {"n_by_source": {s: int((y == s).sum()) for s in sorted(set(y))}, "chance": 50.0,
            "all": classify(np.hstack([block[n] for n in names]), y, g)["balanced_accuracy"],
            "single_group": {n: classify(block[n], y, g)["balanced_accuracy"] for n in names}}


def cross_source_eval(ckpt, man, classes):
    from compare_isolated_models import Model, wilson
    from build_label_inventory import normalize_label
    model = Model("unified", ckpt)
    keep = [c for c in classes if c not in DIFFERENT_SIGN]
    sets = {"qipedc_val_test": man[(man.source == "qipedc") & man.split.isin(["val", "test"]) & man.gloss_normalized.isin(keep)],
            "qipedc_test_only": man[(man.source == "qipedc") & (man.split == "test") & man.gloss_normalized.isin(keep)],
            "s06_reference": man[(man.source == "vslgh") & (man.split == "test") & man.gloss_normalized.isin(keep)]}
    out = {"classes_kept": len(keep), "excluded_different_sign": sorted(DIFFERENT_SIGN & set(classes))}
    for name, df in sets.items():
        t1, t5 = [], []
        for r in df.itertuples():
            g, top5 = model.run(os.path.join("data/processed", r.npz_path), r.width, r.height)
            t1.append(g == r.gloss_normalized); t5.append(r.gloss_normalized in top5)
        n = len(t1)
        out[name] = {"n": n, "classes": int(df.gloss_normalized.nunique()), "top1": round(100 * np.mean(t1), 1) if n else None,
                     "top1_ci": wilson(int(sum(t1)), n) if n else None, "top5": round(100 * np.mean(t5), 1) if n else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="checkpoints/stgcn_unified_best.pt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-eval", action="store_true")
    ap.add_argument("--features", choices=["legacy", "harmonized"], default="legacy")
    ap.add_argument("--hand-z", choices=["keep", "drop"], default="keep")
    ap.add_argument("--qipedc-kps-dir", default="qipedc_kps", help="e.g. qipedc_kps360 for the 360 px extraction")
    args = ap.parse_args()
    man = pd.concat([pd.read_csv(f"data/splits/unified/{s}.csv") for s in ("train", "val", "test")])
    classes = shared_classes(man)
    rows = balanced_rows(man, classes, args.seed)
    featurize = (legacy_featurize if args.features == "legacy"
                 else harmonized_featurizer(args.hand_z == "keep", args.qipedc_kps_dir))
    res = {"shared_classes": len(classes), "features": args.features, "hand_z": args.hand_z,
           "qipedc_kps_dir": args.qipedc_kps_dir, "balanced": source_classifier(rows, featurize)}
    print("source classifier on shared classes:", json.dumps(res["balanced"], ensure_ascii=False), flush=True)
    if not args.skip_eval:
        res["cross_source_current_model"] = cross_source_eval(args.ckpt, man, classes)
        print("cross-source:", json.dumps(res["cross_source_current_model"], ensure_ascii=False), flush=True)
    os.makedirs(args.out, exist_ok=True)
    name = "shortcut_85.json" if args.features == "legacy" else f"shortcut_85_harmonized_{args.hand_z}z_{args.qipedc_kps_dir}.json"
    json.dump(res, open(os.path.join(args.out, name), "w", encoding="utf-8"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
