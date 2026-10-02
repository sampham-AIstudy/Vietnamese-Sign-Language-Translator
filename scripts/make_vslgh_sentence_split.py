"""Generate the VSL-GH sentence split file (plan 13 §0.3, user decision Q1 = (ii), 2026-10-02 10:05).

  python scripts/make_vslgh_sentence_split.py --canonical data/external/vsl_gh/dataset_canonical.json \
      --seed 42 --out configs/vslgh_sentence_split_v1.json

T = SENT271..SENT300 (fixed, not random); V = sorted(random.Random(seed).sample(sorted(SENT001..SENT270), 30));
Tr = the remaining 240. Before writing, the canonical data are checked (signer <-> split = S01-S04 train, S05 val,
S06 test; sentence ids exactly SENT001..SENT300). Output: UTF-8 JSON, LF only (same bytes on every OS), never
overwritten. The logic lives in `src/data/sentence_split.py` (shared with CSLR / ViT5 / vocab / guard / eval).

Exit codes: 0 written; 2 canonical missing or `--out` already exists; 3 canonical layout check failed.
Prints one JSON object: out, sha256, seed, python, n_train/n_val/n_test, val_ids, canonical_lf_sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (ROOT, os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from retrain_digest import lf_sha256  # noqa: E402
from src.data.sentence_split import load_sentence_split, make_split_dict, split_file_bytes  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate configs/vslgh_sentence_split_v1.json")
    ap.add_argument("--canonical", required=True, help="path to VSL-GH dataset_canonical.json")
    ap.add_argument("--seed", type=int, required=True, help="seed for the 30 val sentences (plan 13: 42)")
    ap.add_argument("--out", required=True, help="output split file (must not exist)")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.canonical):
        print(f"ERROR: canonical file not found: {args.canonical}", file=sys.stderr)
        return 2
    if os.path.lexists(args.out):
        print(f"ERROR: refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2
    with open(args.canonical, "r", encoding="utf-8") as f:
        samples = json.load(f)
    try:
        d = make_split_dict(samples, seed=args.seed)
    except ValueError as exc:
        print(f"ERROR: canonical layout check failed: {exc}", file=sys.stderr)
        return 3
    data = split_file_bytes(d)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    try:
        with open(args.out, "xb") as f:  # exclusive create: never overwrite, even on a race
            f.write(data)
    except FileExistsError:
        print(f"ERROR: refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2

    loaded = load_sentence_split(args.out)  # re-validate what is on disk
    print(json.dumps({
        "out": args.out,
        "sha256": hashlib.sha256(data).hexdigest(),
        "seed": loaded.seed,
        "python": d["python"],
        "n_train": len(loaded.train_ids),
        "n_val": len(loaded.val_ids),
        "n_test": len(loaded.test_ids),
        "val_ids": list(loaded.val_ids),
        "canonical_lf_sha256": lf_sha256(args.canonical),
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
