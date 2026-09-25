"""
Cut VSL-GH continuous sentences into isolated-sign segments using the dataset's own per-gloss
time boundaries, in the project's 67-joint format (same as CleanHolisticExtractor output).

- Conversion: convert_137_to_67(mode="semantic") (see docs/audit/LANDMARK_MAPPING_REPORT.md; "direct" mislabels joints).
- Missing landmarks: VSL-GH stores zeros -> NaN + visibility 0 (project convention, no zero-fill).
- Frame geometry: 1080x1080 (width/height recorded so aspect correction can be applied).
- Skips the two annotations this project wrote by hand (scripts/prepare_canonical_vsl_gh.py):
  their boundaries are estimates, not upstream labels.

Output:
  data/processed/vslgh_segments/<signer>/<sample_id>_gNN.npz   keypoints float16 [T,67,3], visibility_mask [T,67]
  data/processed/vslgh_segments/segments.csv                   one row per segment
Usage:  python scripts/export_vslgh_segments.py [--pad 3] [--min-frames 4]
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from src.data.vsl_gh_dataset import convert_137_to_67  # noqa: E402
from build_label_inventory import normalize_label  # noqa: E402

VSLGH = os.path.join(ROOT, "data", "external", "vsl_gh")
OUT = os.path.join(ROOT, "data", "processed", "vslgh_segments")
HAND_WRITTEN = {"SENT236_S01_R03_F", "SENT285_S04_R03_F"}


def to_seconds(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad", type=int, default=3, help="context frames added on each side")
    ap.add_argument("--min-frames", type=int, default=4)
    args = ap.parse_args()

    samples = json.load(open(os.path.join(VSLGH, "dataset_canonical.json"), encoding="utf-8"))
    rows, skipped = [], {"hand_written": 0, "too_short": 0}
    for s in samples:
        if s["id"] in HAND_WRITTEN:
            skipped["hand_written"] += len(s.get("glosses_detail", []))
            continue
        raw = np.load(os.path.join(VSLGH, s["keypoint_file"])).astype(np.float32)
        kps = convert_137_to_67(raw, mode="semantic")
        present = np.abs(kps).sum(axis=-1) > 0
        kps[~present] = np.nan
        vis = present.astype(np.float32)
        fps, T = float(s.get("fps", 30)), len(kps)
        width, height = (int(v) for v in s.get("resolution", "1080x1080").split("x"))
        for k, g in enumerate(s.get("glosses_detail", [])):
            a = max(0, int(round(to_seconds(g["start_time"]) * fps)) - args.pad)
            b = min(T, int(round(to_seconds(g["end_time"]) * fps)) + args.pad)
            if b - a < args.min_frames:
                skipped["too_short"] += 1
                continue
            seg_id = f"{s['id']}_g{k:02d}"
            path = os.path.join(OUT, s["signer_id"], f"{seg_id}.npz")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            np.savez_compressed(path, keypoints=kps[a:b].astype(np.float16), visibility_mask=vis[a:b],
                                metadata=json.dumps({"source": "vslgh", "sample_id": s["id"], "gloss": g["gloss"],
                                                     "start_frame": a, "end_frame": b, "width": width, "height": height},
                                                    ensure_ascii=False))
            rows.append({
                "video_id": seg_id, "source": "vslgh", "signer_id": s["signer_id"], "sentence_id": s["sentence_id"],
                "repetition": s["repetition"], "gloss_raw": g["gloss"], "label": normalize_label(g["gloss"]),
                "start_frame": a, "end_frame": b, "num_frames": b - a, "width": width, "height": height,
                "npz_path": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                "upstream_split": s.get("split", ""),
            })
    with open(os.path.join(OUT, "segments.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} segments from {len(samples)} sentences; skipped {skipped}")
    print(f"labels: {len({r['label'] for r in rows})}, signers: {sorted({r['signer_id'] for r in rows})}")
    lens = sorted(r["num_frames"] for r in rows)
    print(f"segment length (frames): min {lens[0]}, median {lens[len(lens) // 2]}, max {lens[-1]}")


if __name__ == "__main__":
    main()
