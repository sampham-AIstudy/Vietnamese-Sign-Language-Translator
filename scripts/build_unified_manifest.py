"""
Unified, dialect-agnostic isolated-sign manifest + leakage-free splits across real sources.

Labels  : normalize_label() (regional variants merged). Kept only if they can be measured,
          i.e. have >= --min-units independent units and end with >= 1 train and >= 1 test sample.
Sources and what "independent" means:
  QIPEDC : recording groups (data/splits/recording_groups.csv). Re-captioned copies share a group
           and always land in the same split. Per label: 1 group -> test, 1 -> val if >= 3 groups,
           rest -> train (seeded).
  VSL-GH : signers. Upstream signer split: S01-S04 train, S05 val, S06 test (unseen signers).
Test therefore measures recognition of a recording (QIPEDC) or a person (VSL-GH) never seen in
training. npz_path is relative to a data root (resolved by the training script):
  qipedc_kps/<stem>.npz, vslgh_segments/<signer>/<segment>.npz

Output: data/splits/unified/{train,val,test}.csv, classes.txt, report.json
Usage : python scripts/build_unified_manifest.py [--min-units 2] [--seed 42]
"""
import argparse
import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_label_inventory import normalize_label  # noqa: E402

VSLGH_SPLIT = {"S01": "train", "S02": "train", "S03": "train", "S04": "train", "S05": "val", "S06": "test"}
FIELDS = ["video_id", "file_name", "source", "gloss_raw", "gloss_normalized", "dialect", "signer_id",
          "recording_group", "width", "height", "npz_path", "split"]


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-units", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "data", "splits", "unified"))
    args = ap.parse_args()
    rng = random.Random(args.seed)

    inventory = {r["file_name"]: r for r in read(os.path.join(ROOT, "results", "raw_dataset_inventory.csv"))}
    qipedc = defaultdict(lambda: defaultdict(list))  # label -> group -> rows
    for r in read(os.path.join(ROOT, "data", "splits", "recording_groups.csv")):
        inv = inventory[r["file_name"]]
        if inv.get("status", "VALID") != "VALID":
            continue
        label = normalize_label(r["gloss"])
        qipedc[label][r["recording_group"]].append({
            "video_id": f"qipedc_{os.path.splitext(r['file_name'])[0]}", "file_name": r["file_name"],
            "source": "qipedc", "gloss_raw": r["gloss"], "gloss_normalized": label,
            "dialect": r["dialect"] if r["dialect"] in ("B", "T", "N") else "Other", "signer_id": "",
            "recording_group": r["recording_group"], "width": inv["width"], "height": inv["height"],
            "npz_path": f"qipedc_kps/{os.path.splitext(r['file_name'])[0]}.npz",
        })

    vslgh = defaultdict(list)  # label -> rows
    for r in read(os.path.join(ROOT, "data", "processed", "vslgh_segments", "segments.csv")):
        rel = r["npz_path"].split("data/processed/", 1)[-1]
        vslgh[r["label"]].append({
            "video_id": f"vslgh_{r['video_id']}", "file_name": r["video_id"], "source": "vslgh",
            "gloss_raw": r["gloss_raw"], "gloss_normalized": r["label"], "dialect": "Other",
            "signer_id": r["signer_id"], "recording_group": f"vslgh_{r['signer_id']}",
            "width": r["width"], "height": r["height"], "npz_path": rel, "split": VSLGH_SPLIT[r["signer_id"]],
        })

    out = {"train": [], "val": [], "test": []}
    dropped = Counter()
    kept = []
    for label in sorted(set(qipedc) | set(vslgh)):
        units = len(qipedc.get(label, {})) + len({r["signer_id"] for r in vslgh.get(label, [])})
        if units < args.min_units:
            dropped[f"< {args.min_units} independent units"] += 1
            continue
        rows = [dict(r) for r in vslgh.get(label, [])]
        groups = sorted(qipedc.get(label, {}))
        rng.shuffle(groups)
        has_vslgh_test = any(r["split"] == "test" for r in rows)
        assign = {}
        if groups:
            if len(groups) >= 2 or not has_vslgh_test:
                assign[groups[0]] = "test"
            if len(groups) >= 3:
                assign[groups[1]] = "val"
        for g in groups:
            for r in qipedc[label][g]:
                rows.append(dict(r, split=assign.get(g, "train")))
        splits = Counter(r["split"] for r in rows)
        if not splits["train"] or not splits["test"]:
            dropped["no train/test sample after grouping"] += 1
            continue
        for r in rows:
            out[r["split"]].append(r)
        kept.append(label)

    os.makedirs(args.out_dir, exist_ok=True)
    for split, rows in out.items():
        with open(os.path.join(args.out_dir, f"{split}.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["video_id"]))
    with open(os.path.join(args.out_dir, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")

    # Leakage self-check: no recording group / VSL-GH signer-label pair on two sides.
    side = {}
    for split, rows in out.items():
        for r in rows:
            key = r["recording_group"] if r["source"] == "qipedc" else (r["signer_id"], r["gloss_normalized"])
            assert side.setdefault(key, split) == split, f"leak: {key} in {side[key]} and {split}"

    report = {
        "min_units": args.min_units, "seed": args.seed, "classes": len(kept), "dropped_labels": dict(dropped),
        "samples": {s: len(r) for s, r in out.items()},
        "samples_by_source": {s: dict(Counter(r["source"] for r in rows)) for s, rows in out.items()},
        "test_classes": len({r["gloss_normalized"] for r in out["test"]}),
        "val_classes": len({r["gloss_normalized"] for r in out["val"]}),
        "classes_by_source": dict(Counter("+".join(sorted({r["source"] for s in out.values() for r in s
                                                           if r["gloss_normalized"] == c})) for c in kept)),
        "train_samples_per_class": dict(sorted(Counter(Counter(r["gloss_normalized"] for r in out["train"]).values()).items())),
    }
    json.dump(report, open(os.path.join(args.out_dir, "report.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
