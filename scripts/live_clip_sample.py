"""
The TRAIN clips used to compare the training and live harmonized_v1 paths (plan 04 AC4 / AC5 / AC6).

Rows of data/splits/unified/train.csv with source == "qipedc" whose video data/Dataset/Videos/<file_name> is on
disk, sorted by video_id, then `n` rows picked with np.random.default_rng(seed).choice(len, n, replace=False)
(a fixed, seeded selection; the order of the picks is kept). TRAIN only: the comparison measures code
equivalence, never accuracy.
"""
import csv
import os
from typing import Dict, List

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRAIN_CSV = os.path.join(ROOT, "data", "splits", "unified", "train.csv")
VIDEOS_DIR = os.path.join(ROOT, "data", "Dataset", "Videos")
H360_CKPT = os.path.join(ROOT, "reports", "step4_2026-09-26", "runs", "run_keepz_360", "stgcn_unified_best.pt")


def available() -> bool:
    return os.path.isfile(TRAIN_CSV) and os.path.isdir(VIDEOS_DIR) and os.path.isfile(H360_CKPT)


def select_train_clips(n: int = 8, seed: int = 0, train_csv: str = TRAIN_CSV,
                       videos_dir: str = VIDEOS_DIR) -> List[Dict[str, str]]:
    with open(train_csv, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)
                if r["source"] == "qipedc" and os.path.isfile(os.path.join(videos_dir, r["file_name"]))]
    rows.sort(key=lambda r: r["video_id"])
    picks = np.random.default_rng(seed).choice(len(rows), n, replace=False)
    return [dict(rows[int(i)], video_path=os.path.join(videos_dir, rows[int(i)]["file_name"])) for i in picks]
