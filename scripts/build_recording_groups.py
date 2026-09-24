"""
Group QIPEDC videos that are the SAME recording under different regional captions.

QIPEDC reuses one clip for several regional variants when the sign is identical (only the
burned-in "Kí hiệu Miền …" caption changes). Splitting such clips across train/test leaks
the test answer (reports/audit_round3/PROVENANCE.md). This script assigns every video a
`recording_group`; all members of a group must land in the same split.

Signature: 5 grayscale body crops (20/35/50/65/80% of the clip, 26x32). Two videos of the
same gloss are the same recording if mean |diff| < 3.0 (0-255). Distinct recordings of one
word measure ~14-16, identical re-captioned clips ~0.3.

Output: data/splits/recording_groups.csv
  file_name, gloss, dialect, num_frames, recording_group, group_size, min_diff_to_group
Usage:
  python scripts/build_recording_groups.py [--workers 4]
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIDEOS = os.path.join(ROOT, "data", "Dataset", "Videos")
LABELS = os.path.join(ROOT, "data", "Dataset", "Labels", "label.csv")
OUT = os.path.join(ROOT, "data", "splits", "recording_groups.csv")
DUP_THRESHOLD = 3.0


def signature(fname):
    cap = cv2.VideoCapture(os.path.join(VIDEOS, fname))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for p in (0.2, 0.35, 0.5, 0.65, 0.8):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * p))
        ok, f = cap.read()
        if not ok:
            cap.release()
            return fname, n, None
        g = cv2.cvtColor(cv2.resize(f[40:680, 380:900], (26, 32)), cv2.COLOR_BGR2GRAY)
        frames.append(g.astype(np.float32))
    cap.release()
    return fname, n, np.stack(frames)


def dialect_of(fname):
    stem = os.path.splitext(fname)[0]
    return stem[-1] if stem[-1] in "BTN" else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    with open(LABELS, encoding="utf-8-sig") as f:
        rows = [(r["VIDEO"].strip(), r["LABEL"].strip()) for r in csv.DictReader(f)]
    by_gloss = defaultdict(list)
    for fname, gloss in rows:
        by_gloss[gloss].append(fname)

    sigs, nframes = {}, {}
    with ProcessPoolExecutor(args.workers) as ex:
        for i, (fname, n, s) in enumerate(ex.map(signature, [r[0] for r in rows], chunksize=16), 1):
            sigs[fname], nframes[fname] = s, n
            if i % 500 == 0:
                print(f"  signatures {i}/{len(rows)}", flush=True)

    out_rows, gid = [], 0
    for gloss, files in sorted(by_gloss.items()):
        parent = {f: f for f in files}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        best = {f: float("inf") for f in files}
        for i, a in enumerate(files):
            for b in files[i + 1:]:
                if sigs[a] is None or sigs[b] is None:
                    continue
                d = float(np.mean(np.abs(sigs[a] - sigs[b])))
                if d < DUP_THRESHOLD:
                    parent[find(a)] = find(b)
                    best[a], best[b] = min(best[a], d), min(best[b], d)
        groups = defaultdict(list)
        for f in files:
            groups[find(f)].append(f)
        for members in sorted(groups.values(), key=lambda m: sorted(m)[0]):
            gid += 1
            for f in sorted(members):
                out_rows.append({
                    "file_name": f, "gloss": gloss, "dialect": dialect_of(f), "num_frames": nframes[f],
                    "recording_group": f"RG{gid:05d}", "group_size": len(members),
                    "min_diff_to_group": "" if best[f] == float("inf") else round(best[f], 3),
                })

    unreadable = [f for f, s in sigs.items() if s is None]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    n_groups = len({r["recording_group"] for r in out_rows})
    print(f"{len(out_rows)} videos -> {n_groups} distinct recordings ({len(out_rows) - n_groups} duplicates); "
          f"unreadable: {unreadable}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
