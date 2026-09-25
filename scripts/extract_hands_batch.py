"""
Batch MediaPipe Hands extraction for Level 1 (fingerspelling letters + tone marks).

Matches the backend's hand pipeline (mediapipe.solutions.hands, max_num_hands=1,
model_complexity=1, mediapipe 0.10.14). Video mode with a fresh tracker per clip.
Output format is the one src/data/alphabet_dataset.py reads:
  raw_landmarks [T,21,3] float32 (MediaPipe image coords, zeros where no hand),
  detected_mask [T], handedness_label [T] ('Left'/'Right'/''), handedness_score [T],
  metadata JSON (sample_id, symbol, signer_id, source, width, height, fps, mediapipe_version).

Input CSV columns: video_path, sample_id, symbol, signer_id, source
Usage: python scripts/extract_hands_batch.py --tasks-csv tasks.csv --out-dir <dir> [--workers N]
Writes <out-dir>/<signer_id>/<sample_id>.npz and <out-dir>/manifest.csv.
"""
import argparse
import csv
import json
import os
import time
from multiprocessing import Pool


def _extract_one(task):
    import cv2
    import mediapipe as mp
    import numpy as np

    row, out_path = task
    if os.path.exists(out_path):
        return out_path, "skip"
    cap = cv2.VideoCapture(row["video_path"])
    if not cap.isOpened():
        return out_path, "error: cannot open"
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    lms, det, lab, score = [], [], [], []
    with mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, model_complexity=1,
                                  min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if res.multi_hand_landmarks:
                lms.append([[p.x, p.y, p.z] for p in res.multi_hand_landmarks[0].landmark])
                c = res.multi_handedness[0].classification[0]
                det.append(True); lab.append(c.label); score.append(c.score)
            else:
                lms.append([[0.0, 0.0, 0.0]] * 21)
                det.append(False); lab.append(""); score.append(0.0)
    cap.release()
    if not lms:
        return out_path, "error: no frames"
    meta = {k: row[k] for k in ("sample_id", "symbol", "signer_id", "source")}
    meta.update(num_frames=len(lms), fps=float(fps), width=width, height=height,
                detection_rate=float(np.mean(det)), mediapipe_version=mp.__version__, extractor="mp.solutions.hands")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp.npz"
    np.savez_compressed(tmp, raw_landmarks=np.asarray(lms, dtype=np.float32), detected_mask=np.asarray(det),
                        handedness_label=np.asarray(lab), handedness_score=np.asarray(score, dtype=np.float32),
                        metadata=json.dumps(meta, ensure_ascii=False))
    os.replace(tmp, out_path)
    return out_path, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks-csv", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    with open(args.tasks_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tasks = [(r, os.path.join(args.out_dir, r["signer_id"], f"{r['sample_id']}.npz")) for r in rows]
    print(f"{len(tasks)} clips, {args.workers} workers", flush=True)
    t0, errors = time.time(), []
    with Pool(args.workers, maxtasksperchild=50) as pool:
        for i, (path, status) in enumerate(pool.imap_unordered(_extract_one, tasks, chunksize=4), 1):
            if status.startswith("error"):
                errors.append((path, status))
            if i % 100 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} {(time.time() - t0) / 60:.1f} min", flush=True)

    import numpy as np
    manifest = []
    for r, path in tasks:
        if os.path.exists(path):
            m = json.loads(str(np.load(path)["metadata"]))
            m["landmark_path"] = os.path.relpath(path, args.out_dir).replace(os.sep, "/")
            manifest.append(m)
    with open(os.path.join(args.out_dir, "manifest.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for m in manifest for k in m}))
        w.writeheader()
        w.writerows(manifest)
    print(f"done: {len(manifest)} npz, {len(errors)} errors {errors[:10]}", flush=True)


if __name__ == "__main__":
    main()
