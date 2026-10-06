#!/usr/bin/env python
"""
Plan 15 lần sửa 12 H1: handedness label fed to the Level 1 checkpoint vs the result, on the collected_targeted clips.

Every clip of data/collected_targeted/manifest.csv is classified whole (one SignSegment, as level1_demo.py's segments)
with four handedness inputs:
  auto           MediaPipe's label of each frame, as recorded (level1_demo.py --dominant-hand auto);
  fixed_Left     every hand frame 'Left'  (what --dominant-hand Right of lần sửa 10 P1 gave);
  fixed_Right    every hand frame 'Right' (what --dominant-hand Left of lần sửa 10 P1 gave);
  lock           HandednessLock over the recorded labels (level1_demo.py --dominant-hand lock of lần sửa 12).
The clips are part of the training data of the deployed checkpoint: this checks the handedness logic, it is not
accuracy and not a webcam session.

  python scripts/level1_dominant_hand_check.py --out reports/level1_realtime_2026-10-06/dominant_hand_check.json
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.inference.level1_core import HandednessLock, Level1Classifier  # noqa: E402
from src.inference.level1_segmenter import SignSegment  # noqa: E402

DEFAULT_MANIFEST = os.path.join(ROOT, "data", "collected_targeted", "manifest.csv")
DEFAULT_CKPT = os.path.join(ROOT, "checkpoints", "alphabet_best.pt")
CODE_PATHS = ("scripts/level1_dominant_hand_check.py", "src")
MODES = ("auto", "fixed_Left", "fixed_Right", "lock")
NOTE = ("collected_targeted clips are training data of the deployed checkpoint: checks the handedness logic; not "
        "accuracy, not a webcam session")


def _git(*args) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: str) -> str:
    r = os.path.relpath(os.path.abspath(path), ROOT)
    return (os.path.abspath(path) if r.startswith("..") else r).replace("\\", "/")


def labels_for(mode: str, recorded: np.ndarray, detected: np.ndarray) -> np.ndarray:
    """Handedness array fed to the classifier for one mode ('' where no hand)."""
    if mode == "auto":
        return np.where(detected, recorded, "")
    if mode in ("fixed_Left", "fixed_Right"):
        return np.where(detected, mode.split("_", 1)[1], "")
    lock = HandednessLock()
    return np.array([lock.update(str(x)) if d else "" for x, d in zip(recorded, detected)], dtype=object).astype(str)


def check(manifest_path: str, classifier) -> Dict[str, Any]:
    with open(manifest_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    base = os.path.dirname(manifest_path)
    clips: List[Dict[str, Any]] = []
    totals = {m: 0 for m in MODES}
    for r in rows:
        z = np.load(os.path.join(base, r["landmark_path"]), allow_pickle=False)
        raw = z["raw_landmarks"].astype(np.float32)
        det = z["detected_mask"].astype(bool)
        rec = z["handedness_label"].astype(str)
        ts = np.arange(len(det)) * 1000.0 / float(r["fps"])
        entry = {"sample_id": r["sample_id"], "symbol": r["symbol"],
                 "recorded_labels": dict(Counter(str(x) for x, d in zip(rec, det) if d)), "prediction": {}}
        for mode in MODES:
            seg = SignSegment(seq=1, raw_landmarks=raw, detected=det, handedness=labels_for(mode, rec, det),
                              timestamps_ms=ts, frame_width=int(r["width"]), frame_height=int(r["height"]),
                              t_start_ms=float(ts[0]), t_end_ms=float(ts[-1]), t_emit_ms=float(ts[-1]),
                              close_reason="end_of_stream")
            res = classifier.classify(seg, 1)
            pred = res.get("prediction") if res.get("status") == "ok" else None
            entry["prediction"][mode] = pred
            totals[mode] += int(pred == r["symbol"])
        clips.append(entry)
    majority = Counter(max(c["recorded_labels"], key=c["recorded_labels"].get) for c in clips if c["recorded_labels"])
    return {"n_clips": len(clips), "correct": totals,
            "rate": {m: (totals[m] / len(clips)) if clips else None for m in MODES},
            "clips_by_majority_recorded_label": dict(majority), "clips": clips}


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p.add_argument("--checkpoint", default=DEFAULT_CKPT)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    import mediapipe as mp
    import torch
    classifier = Level1Classifier.from_checkpoint(args.checkpoint)
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    report = {
        "generated_by": {"command": " ".join(["python", "scripts/level1_dominant_hand_check.py", *argv]),
                         "git_commit": _git("rev-parse", "HEAD"),
                         "code_dirty": None if status is None else bool(status),
                         "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                         "python": platform.python_version(), "torch": torch.__version__,
                         "mediapipe": mp.__version__, "numpy": np.__version__},
        "note": NOTE,
        "definitions": {"auto": "MediaPipe label of each frame as recorded by scripts/collect_targeted_signs.py",
                        "fixed_Left": "every hand frame labelled 'Left' (lần sửa 10: --dominant-hand Right)",
                        "fixed_Right": "every hand frame labelled 'Right' (lần sửa 10: --dominant-hand Left)",
                        "lock": "HandednessLock (src/inference/level1_core.py) over the recorded labels",
                        "correct": "top-1 of the whole clip == manifest symbol"},
        "manifest": {"path": rel(args.manifest), "sha256": sha256_file(args.manifest)},
        "checkpoint": {"path": rel(args.checkpoint), "sha256": sha256_file(args.checkpoint)},
        **check(args.manifest, classifier),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"correct": report["correct"], "n_clips": report["n_clips"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
