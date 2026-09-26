"""
Batch 67-joint landmark extraction for cloud runs (Kaggle/Colab), resumable and shardable.

Uses the backend's own CleanHolisticExtractor (MediaPipe Holistic). Run it under the same
mediapipe version as the backend (0.10.14) so training and live-camera landmarks match.
A fresh Holistic instance is created per video: the tracker (static_image_mode=False) would
otherwise carry the previous clip's hand positions into the first frames of the next one.

Output per video: <out-dir>/<stem>.npz  (keypoints [T,67,3] float32 NaN=missing,
visibility_mask [T,67], metadata JSON incl. width/height for aspect correction).
Finally writes <out-dir>/manifest.csv built from the npz metadata.

Usage:
  python scripts/extract_keypoints_batch.py --videos-dir <dir> --labels-csv <label.csv> \
      --source qipedc --out-dir <dir> [--workers N] [--shard 0/1] [--limit N]
  labels CSV needs columns VIDEO (file name) and LABEL (gloss), like QIPEDC's label.csv.
"""
import argparse
import csv
import json
import os
import sys
import time
from multiprocessing import Pool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def _extract_one(task):
    import numpy as np
    import mediapipe as mp
    from src.data.landmark_extractor import CleanHolisticExtractor

    video_path, out_path, meta = task
    if os.path.exists(out_path):
        return out_path, "skip", 0.0
    t0 = time.time()
    extractor = CleanHolisticExtractor(process_height=meta.get("process_height"))
    try:
        res = extractor.extract_from_video(video_path)
    except Exception as e:  # unreadable video: record and continue
        return out_path, f"error: {type(e).__name__}: {e}", 0.0
    finally:
        extractor.close()
    meta = dict(meta, num_frames=int(res["num_frames"]), fps=float(res["fps"]), width=int(res["width"]),
                height=int(res["height"]), mediapipe_version=mp.__version__, extractor="CleanHolisticExtractor")
    tmp = out_path + ".tmp.npz"
    np.savez_compressed(tmp, keypoints=res["keypoints"].astype(np.float32),
                        visibility_mask=res["visibility_mask"].astype(np.float32),
                        metadata=json.dumps(meta, ensure_ascii=False))
    os.replace(tmp, out_path)
    return out_path, "ok", time.time() - t0


def write_manifest(out_dir):
    import numpy as np
    rows = []
    for name in sorted(os.listdir(out_dir)):
        if not name.endswith(".npz") or name.endswith(".tmp.npz"):
            continue
        m = json.loads(str(np.load(os.path.join(out_dir, name))["metadata"]))
        m["npz_file"] = name
        rows.append(m)
    if rows:
        fields = sorted({k for r in rows for k in r})
        with open(os.path.join(out_dir, "manifest.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos-dir", required=True)
    ap.add_argument("--labels-csv", required=True)
    ap.add_argument("--source", required=True, help="e.g. qipedc, hcmue")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--shard", default="0/1", help="i/n: process every n-th video starting at i")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--process-height", type=int, default=None,
                    help="resize frames to this height before MediaPipe (e.g. 360 to match VSL-GH)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    with open(args.labels_csv, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)]
    i, n = (int(x) for x in args.shard.split("/"))
    rows = [r for k, r in enumerate(sorted(rows, key=lambda r: r["VIDEO"])) if k % n == i]
    if args.limit:
        rows = rows[: args.limit]
    tasks = []
    for r in rows:
        video = r["VIDEO"].strip()
        path = os.path.join(args.videos_dir, video)
        if not os.path.exists(path):
            print(f"missing video: {video}", flush=True)
            continue
        stem = os.path.splitext(video)[0]
        tasks.append((path, os.path.join(args.out_dir, f"{stem}.npz"),
                      {"source": args.source, "file_name": video, "label": r["LABEL"].strip(),
                       "process_height": args.process_height}))

    print(f"{len(tasks)} videos, {args.workers} workers, shard {args.shard}", flush=True)
    t0, done, errors = time.time(), 0, []
    with Pool(args.workers, maxtasksperchild=50) as pool:
        for out_path, status, secs in pool.imap_unordered(_extract_one, tasks, chunksize=4):
            done += 1
            if status.startswith("error"):
                errors.append((out_path, status))
            if done % 100 == 0 or done == len(tasks):
                rate = done / max(time.time() - t0, 1e-6)
                print(f"  {done}/{len(tasks)}  {rate:.2f} videos/s  eta {(len(tasks) - done) / max(rate, 1e-6) / 60:.1f} min",
                      flush=True)
    n_rows = write_manifest(args.out_dir)
    print(f"done in {(time.time() - t0) / 60:.1f} min; manifest rows {n_rows}; errors {len(errors)}", flush=True)
    for e in errors[:20]:
        print("  ", e)


if __name__ == "__main__":
    main()
