"""
Leakage-free recording-grouped splits (tier1, tier2): every member of a recording group (see
scripts/build_recording_groups.py) lands in the same split.

Classes = the classes of the legacy split family (--tier) that have >= 2 distinct recordings:
  tier2 -> the 487 tier2_indomain classes, tier1 -> the 50 tier1 classes.
Per class (seeded): 1 recording group -> test, 1 -> val if >= 3 groups, rest -> train.
Duplicates follow their group, so a re-captioned copy never crosses splits.

Output: data/splits/folds/<tier>_grouped_{train,val,test}.csv (+ <tier>_grouped_classes.txt)
Columns = results/raw_dataset_inventory.csv + dialect, recording_group, split.
Usage: python scripts/create_grouped_splits.py [--tier tier2|tier1] [--seed 42]
"""
import argparse
import csv
import os
import random
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INVENTORY = os.path.join(ROOT, "results", "raw_dataset_inventory.csv")
GROUPS = os.path.join(ROOT, "data", "splits", "recording_groups.csv")
LEGACY = {
    "tier2": os.path.join(ROOT, "data", "splits", "folds", "tier2_indomain_{}.csv"),
    "tier1": os.path.join(ROOT, "data", "splits", "tier1_{}.csv"),
}
OUT = os.path.join(ROOT, "data", "splits", "folds", "{tier}_grouped_{split}.csv")


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=sorted(LEGACY), default="tier2")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    inventory = {r["file_name"]: r for r in read(INVENTORY)}
    group_of = {r["file_name"]: r["recording_group"] for r in read(GROUPS)}
    dialect_of = {r["file_name"]: r["dialect"] for r in read(GROUPS)}

    # Class universe = classes of the legacy split family; membership by gloss_normalized of the inventory.
    classes = {r["gloss_normalized"] for s in ("train", "val", "test") for r in read(LEGACY[args.tier].format(s))}
    by_class = defaultdict(lambda: defaultdict(list))
    for fname, row in inventory.items():
        if row["gloss_normalized"] in classes and row.get("status", "VALID") == "VALID":
            by_class[row["gloss_normalized"]][group_of[fname]].append(fname)

    out = {"train": [], "val": [], "test": []}
    kept = []
    for cls in sorted(by_class):
        groups = sorted(by_class[cls])
        if len(groups) < 2:
            continue
        rng.shuffle(groups)
        assign = {groups[0]: "test"}
        if len(groups) >= 3:
            assign[groups[1]] = "val"
        for g in groups:
            split = assign.get(g, "train")
            for fname in sorted(by_class[cls][g]):
                row = dict(inventory[fname])
                d = dialect_of[fname]
                row.update({"dialect": d if d in "BTN" else "Other", "recording_group": g, "split": split})
                out[split].append(row)
        kept.append(cls)

    fields = list(next(iter(inventory.values())).keys()) + ["dialect", "recording_group", "split"]
    for split, rows in out.items():
        with open(OUT.format(tier=args.tier, split=split), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    with open(OUT.format(tier=args.tier, split="classes").replace(".csv", ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(kept)) + "\n")

    val_classes = {r["gloss_normalized"] for r in out["val"]}
    print(f"classes kept: {len(kept)} / {len(classes)} (dropped {len(classes) - len(kept)} with < 2 distinct recordings)")
    for split, rows in out.items():
        print(f"  {split}: {len(rows)} videos, {len({r['recording_group'] for r in rows})} recordings, "
              f"{len({r['gloss_normalized'] for r in rows})} classes")
    print(f"  val covers {len(val_classes)} classes (only those with >= 3 recordings)")


if __name__ == "__main__":
    main()
