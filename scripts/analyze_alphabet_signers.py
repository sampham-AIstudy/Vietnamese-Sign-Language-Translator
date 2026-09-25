"""
Per-signer capture diagnostics for Level 1 (why does one hauuto signer score lower?).

Reads the extract_hands_batch.py output (manifest.csv + npz) and, if --raw-dir is given, the
original mp4 files to read real frame timestamps (container PTS via OpenCV).
Per signer: handedness / mirroring, fps (header vs PTS), duration, missing-hand frames
(edges vs interior gaps), camera-angle proxies (in-plane hand roll, palm facing, hand size,
position in frame) and wrist travel for tone marks.
Usage: python scripts/analyze_alphabet_signers.py --data-dir <alphabet_hands> [--raw-dir <hauuto raw/raw>]
       --out <json>
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from src.data.alphabet_preprocessing import canonicalize_hand_sequence  # noqa: E402


def read_pts_ms(path):
    import cv2
    cap = cv2.VideoCapture(path)
    pts = []
    while cap.grab():
        pts.append(cap.get(cv2.CAP_PROP_POS_MSEC))
    cap.release()
    return np.asarray(pts, dtype=np.float64)


def raw_path(raw_dir, sample_id, signer):
    return os.path.join(raw_dir, signer.replace("hauuto_", ""), sample_id.replace("hauuto_", "") + ".mp4")


def clip_stats(m, d, raw_dir):
    det = d["detected_mask"].astype(bool)
    labels = [str(x) for x, k in zip(d["handedness_label"], det) if k]
    lms, det, mirrored = canonicalize_hand_sequence(d["raw_landmarks"], det, d["handedness_label"],
                                                    aspect_ratio=float(m["width"]) / float(m["height"]))
    T = len(det)
    idx = np.flatnonzero(det)
    s = {"sample_id": m["sample_id"], "signer": m["signer_id"], "symbol": m["symbol"], "frames": T, "fps_header": float(m["fps"]),
         "detection_rate": float(det.mean()), "mirrored": bool(mirrored)}
    if labels:
        major = max(set(labels), key=labels.count)
        s["handedness_minority_frac"] = 1 - labels.count(major) / len(labels)
        s["handedness_score"] = float(np.mean(d["handedness_score"][det]))
    if len(idx):
        s["missing_edges"] = int(idx[0] + (T - 1 - idx[-1]))
        s["missing_interior"] = int((idx[-1] - idx[0] + 1) - len(idx))
        s["max_gap"] = int(np.max(np.diff(idx)) - 1) if len(idx) > 1 else 0
        f = lms[det]
        v = f[:, 9, :2] - f[:, 0, :2]  # wrist -> middle MCP (image plane)
        s["roll_deg"] = float(np.degrees(np.median(np.arctan2(v[:, 0], -v[:, 1]))))
        s["hand_size"] = float(np.median(np.linalg.norm(v, axis=1)))
        n = np.cross(f[:, 5] - f[:, 0], f[:, 17] - f[:, 0])  # palm normal
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        s["palm_facing_deg"] = float(np.degrees(np.median(np.arccos(np.clip(np.abs(n[:, 2]), 0, 1)))))
        s["wrist_y"] = float(np.median(f[:, 0, 1]))
        w = f[:, 0, :2] / max(s["hand_size"], 1e-6)
        s["wrist_travel_palms"] = float(np.linalg.norm(w.max(0) - w.min(0)))
    if raw_dir:
        p = raw_path(raw_dir, m["sample_id"], m["signer_id"])
        if os.path.exists(p):
            pts = read_pts_ms(p)
            dt = np.diff(pts)
            dt = dt[dt > 0]
            s["pts_frames"] = int(len(pts))
            s["_pts"] = pts.round(3).tolist()
            s["duration_s"] = float((pts[-1] - pts[0]) / 1000) if len(pts) > 1 else 0.0
            if len(dt):
                s["fps_pts"] = float(1000 / np.median(dt))
                s["dt_cv"] = float(np.std(dt) / np.mean(dt))  # 0 = constant frame rate
                s["dt_max_ms"] = float(dt.max())
    return s


def summarize(rows):
    keys = ["frames", "fps_header", "fps_pts", "duration_s", "dt_cv", "dt_max_ms", "detection_rate",
            "missing_edges", "missing_interior", "max_gap", "handedness_minority_frac", "handedness_score",
            "roll_deg", "palm_facing_deg", "hand_size", "wrist_y"]
    out = {"clips": len(rows), "mirrored_frac": float(np.mean([r["mirrored"] for r in rows]))}
    for k in keys:
        v = [r[k] for r in rows if k in r]
        if v:
            out[k] = {"median": float(np.median(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))}
    out["clips_with_interior_gap"] = int(sum(r.get("missing_interior", 0) > 0 for r in rows))
    out["clips_vfr_dt_cv_gt_0.1"] = int(sum(r.get("dt_cv", 0) > 0.1 for r in rows))
    tone = [r["wrist_travel_palms"] for r in rows if r["symbol"].startswith("dấu") and "wrist_travel_palms" in r]
    if tone:
        out["tone_wrist_travel_palms_median"] = float(np.median(tone))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--raw-dir")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    by = defaultdict(list)
    with open(os.path.join(args.data_dir, "manifest.csv"), encoding="utf-8") as f:
        for m in csv.DictReader(f):
            if m["source"] != "hauuto":
                continue
            d = np.load(os.path.join(args.data_dir, m["landmark_path"]))
            by[m["signer_id"]].append(clip_stats(m, d, args.raw_dir))
    pts = {m_id: r.pop("_pts") for rows in by.values() for r in rows if "_pts" in r
           for m_id in [r["sample_id"]]}
    report = {s: summarize(r) for s, r in sorted(by.items())}
    report["_pts_ms"] = pts
    report["_per_clip"] = {s: r for s, r in sorted(by.items())}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    for s, r in report.items():
        if s.startswith("_"):
            continue
        brief = {k: (v["median"] if isinstance(v, dict) else v) for k, v in r.items()}
        print(s, json.dumps(brief, ensure_ascii=False))


if __name__ == "__main__":
    main()
