#!/usr/bin/env python
"""
Plan 15 (lần sửa 1) §3.A.3 — evidence about the tone marks + segmenter calibration rules on the TRAIN clips (A1).

Writes ONE JSON (default: reports/level1_realtime_<D>/tone_evidence.json) with:

- nested_per_class: per tone class, per outer fold (= test signer) and in total, the out-of-fold predictions of the
  deployed run (reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv, run "frame"): n, correct, top1,
  predicted_as {label: count}, errors to another tone / to a letter. Self-check: the tone top-1 recomputed per fold
  must equal runs.frame.folds[i].tones.top1 of the primary nested_report.json (|diff| <= 1e-9) and their mean must equal
  summary.tones.mean; otherwise the script stops WITHOUT writing (plan stop point 3).
- variants_summary: tones / letters mean and sd of the 4 variants of reports/alphabet_nested_2026-09-25/variants
  (read from the JSON, with its path + sha256).
- train_profiles: motion profile of every hauuto clip of the manifest with >= min_detected_frames hand frames (the
  training data of the deployed checkpoint), statistics per group (letters / tones / each tone).
  M_t = Level1SignSegmenter.motion read after each push (the segmenter itself is run; no formula is rewritten here).
- calibration: rules 1-6 of §3.A.3 with their inputs; rule 6 = the pre-registered stop point.
- u1 (only with --u1-json): aggregate numbers of a webcam session JSON (never copied), with its sha256.

Timestamps of a clip = i * 1000 / fps of the manifest. This is NOT accuracy: train data / out-of-fold predictions.
--write-config is not part of this step (plan step A2).

Step R2 (plan 15 lần sửa 3 §3.4), separate JSON: --pose-evidence --out reports/level1_realtime_<D>/pose_evidence.json
computes rules P1 (rearm_pose_dist = pose_over_jitter_ratio x p95 over letter clips of the hand-shape jitter in the
longest still run) and P2 (coverage of the letter pairs per signer / session, pre-registered stop below 0.80);
--write-pose-config <config> --pose-evidence-json <json> writes only rearm_pose_dist (commit of the JSON read with git).

Step A3 (lần sửa 1 §3.A.4, lần sửa 2 §5): --segment-check --config <PATH | git:REV:PATH> --label <name> --out
reports/level1_realtime_<D>/segment_check_<name>.json runs the segmenter (rearm_mode 'motion_pose', pose rules off) on
every hauuto train clip and classifies with Level1Classifier (single_segment, window_agrees per letter / tone group);
--keep-rule BEFORE AFTER applies the pre-registered keep rule + AC-R1 to two such JSON files (exit 5 = stop).

Step C1: --summary --out reports/level1_realtime_<D>/SUMMARY.md writes the tables of tone_evidence (--evidence-json),
segment_check_{before,after}.json, decoder rearm_check_*.json, the demo config and webcam_*.json of that folder; the
same inputs give the same bytes (AC-R'4).
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import platform
import itertools
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.inference.fingerspelling_compose import TONE_MARKS  # noqa: E402
from src.inference.level1_core import class_kind, load_level1_config, validate_level1_config  # noqa: E402
from src.data.alphabet_preprocessing import normalize_hand_landmarks  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter, aspect_points, pose_distance  # noqa: E402

KAGGLE_DIR = os.path.join(ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands")
MANIFEST = os.path.join(KAGGLE_DIR, "manifest.csv")
NESTED_DIR = os.path.join(ROOT, "reports", "alphabet_nested_2026-09-25")
PRIMARY_REPORT = os.path.join(NESTED_DIR, "primary", "nested_report.json")
PRIMARY_PREDICTIONS = os.path.join(NESTED_DIR, "primary", "nested_predictions.csv")
VARIANTS_REPORT = os.path.join(NESTED_DIR, "variants", "nested_report.json")
DEPLOYED_CKPT = os.path.join(ROOT, "checkpoints", "alphabet_best.pt")
CONFIG = os.path.join(ROOT, "configs", "level1_realtime.json")

DEPLOYED_RUN = "frame"
VARIANTS = ("frame", "time", "frame_traj", "time_traj")
TONES = tuple(TONE_MARKS.keys())
PERCENTILES = (5, 10, 50, 90, 95)
FOLD_TOLERANCE = 1e-9
PROFILE_METRICS = ("duration_ms", "leading_still_ms", "trailing_still_ms", "moving_ms", "longest_still_ms",
                   "longest_internal_still_ms", "median_motion")
CODE_PATHS = ("scripts/level1_segment_report.py", "src", "configs/level1_realtime.json")
NOTE = "train data / out-of-fold predictions; not webcam accuracy"
DEFINITIONS = {
    "M_t": "Level1SignSegmenter.motion read after each push of the clip (every frame, None without a value); on a "
           "frame without a hand the segmenter keeps its last value and its still / moving state (it only updates "
           "them on hand frames), the profile uses the value as the segmenter holds it",
    "timestamps": "i * 1000 / fps of the manifest, ms",
    "duration_ms": "ts of the last frame - ts of the first frame",
    "first_move_ms / last_move_ms": "ts of the first / last frame with M_t >= move_speed; none -> clip 'no_motion' "
                                    "(counted apart, no number given)",
    "leading_still_ms": "first_move_ms - ts of the first frame",
    "trailing_still_ms": "ts of the last frame - last_move_ms",
    "moving_ms": "last_move_ms - first_move_ms",
    "longest_still_ms": "longest run of consecutive frames with M_t <= still_speed (ts of its last frame - ts of its "
                        "first frame, as the segmenter's hold timer); 0.0 when the clip has no such frame",
    "longest_internal_still_ms": "as longest_still_ms, only frames with first_move_ms < ts < last_move_ms; "
                                 "no_motion clips excluded",
    "median_motion": "median of the M_t values of the clip that are not None; None (excluded) when there is none",
    "percentiles": "numpy.percentile, linear interpolation",
}


# ---------------------------------------------------------------------------------------------------------- helpers
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: str) -> str:
    r = os.path.relpath(os.path.abspath(path), ROOT)
    return (os.path.abspath(path) if r.startswith("..") else r).replace("\\", "/")


def _git(*args) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def generated_by(argv: Sequence[str]) -> Dict[str, Any]:
    import torch
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    return {"command": " ".join(["python", "scripts/level1_segment_report.py", *argv]),
            "git_commit": _git("rev-parse", "HEAD"),
            "code_dirty": None if status is None else bool(status),
            "code_paths": list(CODE_PATHS),
            "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
            "cpu": platform.processor(), "os": platform.platform()}


def percentile_stats(values: Sequence[float]) -> Dict[str, Any]:
    """{n, p5, p10, p50, p90, p95} with numpy.percentile (linear); percentiles None when n == 0."""
    v = np.asarray([float(x) for x in values], dtype=np.float64)
    out: Dict[str, Any] = {"n": int(v.size)}
    for q in PERCENTILES:
        out[f"p{q}"] = float(np.percentile(v, q)) if v.size else None
    return out


def _pct(values: Sequence[float], q: float, what: str) -> float:
    if len(values) == 0:
        raise ValueError(f"no value for {what}")
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


# ---------------------------------------------------------------------------------------- nested evidence (R'2)
def read_predictions(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _class_block(rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    n = len(rows)
    correct = sum(1 for r in rows if r["pred"] == r["true"])
    wrong = [r["pred"] for r in rows if r["pred"] != r["true"]]
    return {"n": n, "correct": correct, "top1": (100.0 * correct / n) if n else None,
            "predicted_as": dict(sorted(Counter(r["pred"] for r in rows).items(), key=lambda kv: (-kv[1], kv[0]))),
            "errors_to_tone": sum(1 for p in wrong if class_kind(p) == "tone"),
            "errors_to_letter": sum(1 for p in wrong if class_kind(p) == "letter"),
            "errors_to_other": sum(1 for p in wrong if class_kind(p) not in ("tone", "letter"))}


def _group_top1(rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    n = len(rows)
    correct = sum(1 for r in rows if r["pred"] == r["true"])
    return {"n": n, "correct": correct, "top1": (100.0 * correct / n) if n else None}


def nested_per_class(pred_rows: Sequence[Dict[str, str]], report: Dict[str, Any],
                     run: str = DEPLOYED_RUN) -> Dict[str, Any]:
    """Per tone class / fold counts from the out-of-fold predictions + self-check against nested_report.json."""
    rows = [r for r in pred_rows if r["run"] == run]
    folds_report = report["runs"][run]["folds"]
    folds, diffs = [], []
    for fold in folds_report:
        signer = fold["test_signer"]
        frows = [r for r in rows if r["test_signer"] == signer]
        tone_rows = [r for r in frows if class_kind(r["true"]) == "tone"]
        letter_rows = [r for r in frows if class_kind(r["true"]) == "letter"]
        tones = _group_top1(tone_rows)
        letters = _group_top1(letter_rows)
        tones["report_top1"] = fold["tones"]["top1"]
        letters["report_top1"] = fold["letters"]["top1"]
        if tones["top1"] is None:
            diffs.append(float("inf"))
        else:
            diffs.append(abs(tones["top1"] - fold["tones"]["top1"]))
        folds.append({"test_signer": signer, "tones": tones, "letters": letters,
                      "per_class": {t: _class_block([r for r in tone_rows if r["true"] == t]) for t in TONES}})
    all_tone_rows = [r for r in rows if class_kind(r["true"]) == "tone"]
    fold_top1 = [f["tones"]["top1"] for f in folds]
    mean_recomputed = float(np.mean(fold_top1)) if fold_top1 and None not in fold_top1 else None
    mean_report = report["runs"][run]["summary"]["tones"]["mean"]
    mean_diff = abs(mean_recomputed - mean_report) if mean_recomputed is not None else float("inf")
    max_diff = max(diffs) if diffs else float("inf")
    used = {f["test_signer"] for f in folds_report}
    return {
        "source_run": run,
        "folds": folds,
        "total": {"tones": _group_top1(all_tone_rows),
                  "per_class": {t: _class_block([r for r in all_tone_rows if r["true"] == t]) for t in TONES}},
        "check": {"fold_tones_top1_max_abs_diff": max_diff, "tones_mean_recomputed": mean_recomputed,
                  "tones_mean_report": mean_report, "tones_mean_abs_diff": mean_diff, "tolerance": FOLD_TOLERANCE,
                  "rows_outside_report_folds": sum(1 for r in rows if r["test_signer"] not in used),
                  "matches": bool(max_diff <= FOLD_TOLERANCE and mean_diff <= FOLD_TOLERANCE)},
    }


def variants_summary(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    out = {"path": rel(path), "sha256": sha256_file(path), "protocol": rep.get("protocol"), "seed": rep.get("seed"),
           "clips": rep.get("clips"), "variants": {}}
    for v in VARIANTS:
        s = rep["runs"][v]["summary"]
        out["variants"][v] = {g: {"mean": s[g]["mean"], "sd": s[g]["sd"], "n_folds": s[g].get("n_folds")}
                              for g in ("tones", "letters")}
    return out


# ------------------------------------------------------------------------------------------ motion profiles
def clip_timestamps(n_frames: int, fps: float) -> np.ndarray:
    return np.array([i * 1000.0 / fps for i in range(n_frames)], dtype=np.float64)


def motion_series(raw_landmarks: np.ndarray, detected: np.ndarray, handedness: Sequence[str], width: int,
                  height: int, timestamps_ms: Sequence[float], params: Dict[str, Any],
                  min_detected_frames: int) -> List[Optional[float]]:
    """M_t of a clip = Level1SignSegmenter.motion after each push (one fresh segmenter per clip)."""
    seg = Level1SignSegmenter(params, min_detected_frames)
    out: List[Optional[float]] = []
    for i, ts in enumerate(timestamps_ms):
        lms = raw_landmarks[i] if bool(detected[i]) else None
        seg.push(float(ts), lms, str(handedness[i]) if bool(detected[i]) else "", int(width), int(height))
        out.append(None if seg.motion is None else float(seg.motion))
    return out


def longest_still_run(ts: Sequence[float], flags: Sequence[bool]) -> Optional[Tuple[int, int]]:
    """(first, last) frame index of the run whose duration _longest_run returns (the first run reaching it); None
    when no flag is set."""
    best, best_run, start = -1.0, None, None
    for i, ok in enumerate(flags):
        if ok:
            if start is None:
                start = i
            d = float(ts[i]) - float(ts[start])
            if d > best:
                best, best_run = d, (start, i)
        else:
            start = None
    return best_run


def _longest_run(ts: Sequence[float], flags: Sequence[bool]) -> float:
    best, start = 0.0, None
    for i, ok in enumerate(flags):
        if ok:
            if start is None:
                start = i
            best = max(best, float(ts[i]) - float(ts[start]))
        else:
            start = None
    return best


def motion_profile(timestamps_ms: Sequence[float], motion: Sequence[Optional[float]], still_speed: float,
                   move_speed: float) -> Dict[str, Any]:
    """Profile of one clip (DEFINITIONS). no_motion clips carry None for the move-based fields."""
    ts = [float(t) for t in timestamps_ms]
    if len(ts) != len(motion) or not ts:
        raise ValueError("timestamps and motion must have the same non-zero length")
    values = [m for m in motion if m is not None]
    still = [m is not None and m <= still_speed for m in motion]
    moving = [i for i, m in enumerate(motion) if m is not None and m >= move_speed]
    prof: Dict[str, Any] = {
        "duration_ms": ts[-1] - ts[0],
        "median_motion": float(np.median(values)) if values else None,
        "longest_still_ms": _longest_run(ts, still),
        "no_motion": not moving,
        "has_still": any(still),
    }
    if not moving:
        prof.update({"first_move_ms": None, "last_move_ms": None, "leading_still_ms": None,
                     "trailing_still_ms": None, "moving_ms": None, "longest_internal_still_ms": None})
        return prof
    first, last = ts[moving[0]], ts[moving[-1]]
    internal = [s and first < t < last for s, t in zip(still, ts)]
    prof.update({"first_move_ms": first, "last_move_ms": last, "leading_still_ms": first - ts[0],
                 "trailing_still_ms": ts[-1] - last, "moving_ms": last - first,
                 "longest_internal_still_ms": _longest_run(ts, internal)})
    return prof


# ------------------------------------------------------------------------------------------- calibration
def calibrate(clips: Sequence[Dict[str, Any]], design: Dict[str, Any]) -> Dict[str, Any]:
    """Rules 1-6 of plan 15 lần sửa 1 §3.A.3, in that order.

    clips: [{"kind": "letter" | "tone", "symbol", "timestamps_ms", "motion"}]; design: {"move_over_still_ratio",
    "hold_ms_design"}. Returns {"values", "inputs", "rule6", "profiles"} (profiles computed with the rule 1 values)."""
    letters = [c for c in clips if c["kind"] == "letter"]
    tones = [c for c in clips if c["kind"] == "tone"]
    # rule 1
    letter_medians = []
    for c in letters:
        vals = [m for m in c["motion"] if m is not None]
        if vals:
            letter_medians.append(float(np.median(vals)))
    still_speed = _pct(letter_medians, 90, "still_speed (letter clips with a motion value)")
    ratio = float(design["move_over_still_ratio"])
    move_speed = still_speed * ratio
    # rule 2
    profiles = [motion_profile(c["timestamps_ms"], c["motion"], still_speed, move_speed) for c in clips]
    for c, p in zip(clips, profiles):
        p["kind"], p["symbol"] = c["kind"], c["symbol"]
    letter_p = [p for p in profiles if p["kind"] == "letter"]
    tone_p = [p for p in profiles if p["kind"] == "tone"]
    moving_p = [p for p in profiles if not p["no_motion"]]
    tone_moving_p = [p for p in tone_p if not p["no_motion"]]
    # rule 3
    p10_longest_still = _pct([p["longest_still_ms"] for p in letter_p], 10, "hold_ms (letter clips)")
    hold_ms = min(float(design["hold_ms_design"]), p10_longest_still)
    # rule 4
    p95_duration = _pct([p["duration_ms"] for p in profiles], 95, "max_segment_ms (all clips)")
    max_segment_ms = int(math.ceil(p95_duration))
    # rule 5
    if moving_p:
        p50_trailing = _pct([p["trailing_still_ms"] for p in moving_p], 50, "tail_still_keep_ms (clips with motion)")
        tail_still_keep_ms = min(hold_ms, p50_trailing)
    else:
        p50_trailing = None
        tail_still_keep_ms = hold_ms
    # rule 6 (pre-registered stop point)
    if tone_moving_p:
        p90_internal = _pct([p["longest_internal_still_ms"] for p in tone_moving_p], 90,
                            "rule 6 (tone clips with motion)")
        triggered = bool(p90_internal >= hold_ms)
    else:
        p90_internal = None
        triggered = False
    return {
        "values": {"still_speed": still_speed, "move_speed": move_speed, "hold_ms": hold_ms,
                   "max_segment_ms": max_segment_ms, "tail_still_keep_ms": tail_still_keep_ms},
        "inputs": {
            "rule1_still_speed": {"p90_of_letter_clip_median_motion": still_speed,
                                  "n_letter_clips_with_value": len(letter_medians),
                                  "n_letter_clips_without_value": len(letters) - len(letter_medians)},
            "rule1_move_speed": {"still_speed": still_speed, "move_over_still_ratio": ratio},
            "rule3_hold_ms": {"hold_ms_design": float(design["hold_ms_design"]),
                              "p10_letter_longest_still_ms": p10_longest_still, "n_letter_clips": len(letter_p),
                              "n_letter_clips_without_still_frame": sum(1 for p in letter_p if not p["has_still"])},
            "rule4_max_segment_ms": {"p95_duration_ms_all_clips": p95_duration, "n_clips": len(profiles)},
            "rule5_tail_still_keep_ms": {"hold_ms": hold_ms, "p50_trailing_still_ms_clips_with_motion": p50_trailing,
                                         "n_clips_with_motion": len(moving_p),
                                         "n_no_motion": len(profiles) - len(moving_p)},
        },
        "rule6": {"p90_tone_longest_internal_still_ms": p90_internal, "hold_ms": hold_ms,
                  "n_tone_clips_with_motion": len(tone_moving_p),
                  "n_tone_clips_no_motion": len(tone_p) - len(tone_moving_p), "triggered": triggered,
                  "meaning": "triggered = at least 10% of the tone clips hold still >= hold_ms between their first "
                             "and last motion (the segmenter would cut them in two) -> coder stops, planner decides"},
        "profiles": profiles,
    }


def group_stats(profiles: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Statistics per group: letters, tones, each tone."""
    groups = {"letters": [p for p in profiles if p["kind"] == "letter"],
              "tones": [p for p in profiles if p["kind"] == "tone"]}
    for t in TONES:
        groups[t] = [p for p in profiles if p["symbol"] == t]
    out = {}
    for name, ps in groups.items():
        block: Dict[str, Any] = {"n_clips": len(ps), "n_no_motion": sum(1 for p in ps if p["no_motion"]),
                                 "n_without_still_frame": sum(1 for p in ps if not p["has_still"])}
        for m in PROFILE_METRICS:
            block[m] = percentile_stats([p[m] for p in ps if p[m] is not None])
        out[name] = block
    return out


def load_train_clips(manifest_path: str, min_detected_frames: int) -> Dict[str, Any]:
    """hauuto rows of the manifest -> clips with >= min_detected_frames hand frames (+ the excluded ids)."""
    with open(manifest_path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source"] == "hauuto"]
    base = os.path.dirname(manifest_path)
    clips, excluded = [], []
    for r in sorted(rows, key=lambda r: r["sample_id"]):
        with np.load(os.path.join(base, r["landmark_path"])) as z:
            raw = np.asarray(z["raw_landmarks"], dtype=np.float32)
            det = np.asarray(z["detected_mask"], dtype=bool)
            hand = [str(h) for h in z["handedness_label"]]
        kind = class_kind(r["symbol"])
        if kind is None:
            raise ValueError(f"{r['sample_id']}: symbol {r['symbol']!r} outside the Level 1 vocabulary")
        n_det = int(det.sum())
        if n_det < min_detected_frames:
            excluded.append({"sample_id": r["sample_id"], "detected_frames": n_det, "frames": int(det.size)})
            continue
        clips.append({"sample_id": r["sample_id"], "symbol": r["symbol"], "kind": kind, "signer_id": r["signer_id"],
                      "raw": raw, "detected": det, "handedness": hand, "width": int(r["width"]),
                      "height": int(r["height"]), "fps": float(r["fps"])})
    return {"n_manifest_hauuto": len(rows), "clips": clips, "excluded": excluded}


# ------------------------------------------------------------------------------------- pose evidence (step R2)
POSE_NOTE = "train data of the deployed checkpoint; not accuracy"
POSE_COVERAGE_STOP = 0.80  # plan 15 lần sửa 3 §3.4 P2: pre-registered stop point (coverage below it -> stop)
POSE_REASON = ("calibrated on the train clips of the deployed checkpoint: pose_over_jitter_ratio times the "
               "ninety-fifth percentile, over the letter clips, of the hand-shape jitter in the longest still run of "
               "each clip (ninety-fifth percentile of the pose distance to the mean shape of that run)")
POSE_DEFINITIONS = {
    "N_t": "hand shape of a hand frame: normalize_hand_landmarks(aspect_points(raw, W, H)), computed exactly as "
           "Level1SignSegmenter.push does (hand_shape)",
    "pose_distance": "src.inference.level1_segmenter.pose_distance: mean over the 21 points of the 3D distance between "
                     "two N, in hand lengths",
    "still run": "the longest run of consecutive frames with M_t <= still_speed of the config (M_t as in "
                 "DEFINITIONS of tone_evidence: Level1SignSegmenter.motion after each push; the same run as "
                 "longest_still_ms, the first one when tied); only its hand frames are used",
    "ref": "mean N over the hand frames of the still run of a clip",
    "jitter_clip": "p95 over the hand frames of the still run of pose_distance(N_t, ref)",
    "P1": "rearm_pose_dist = pose_over_jitter_ratio x p95 over the letter clips with a still frame of jitter_clip; "
          "letter clips without a still frame are counted apart and left out",
    "P2": "per (signer, session) and per pair of different letter classes: ref of the clip with the smallest "
          "sample_id of each class, between = pose_distance(ref_a, ref_b); coverage = share of the pairs with "
          "between >= rearm_pose_dist; stop (no config written) when coverage < 0.80",
    "session": "the session letter of sample_id (hauuto_<symbol>_<signer>_<session>_<nnn>)",
    "percentiles": "numpy.percentile, linear interpolation",
}


def hand_shape(raw: np.ndarray, width: int, height: int) -> np.ndarray:
    """N of one hand frame with the same functions and dtypes as Level1SignSegmenter.push."""
    p = aspect_points(raw, width, height)
    return normalize_hand_landmarks(p.astype(np.float32)).astype(np.float64)


def _session(sample_id: str) -> str:
    return sample_id.rsplit("_", 2)[1]


def clip_pose_profile(clip: Dict[str, Any], params: Dict[str, Any], min_detected_frames: int) -> Dict[str, Any]:
    """Still run, ref and jitter_clip of one clip (POSE_DEFINITIONS)."""
    ts = clip_timestamps(len(clip["detected"]), clip["fps"])
    motion = motion_series(clip["raw"], clip["detected"], clip["handedness"], clip["width"], clip["height"], ts,
                           params, min_detected_frames)
    flags = [m is not None and m <= params["still_speed"] for m in motion]
    run = longest_still_run(ts, flags)
    out = {"sample_id": clip["sample_id"], "symbol": clip["symbol"], "kind": clip["kind"],
           "signer_id": clip["signer_id"], "session": _session(clip["sample_id"]), "has_still": False,
           "run_ms": None, "run_hand_frames": 0, "jitter_clip": None, "ref": None}
    if run is None:
        return out
    idx = [i for i in range(run[0], run[1] + 1) if bool(clip["detected"][i])]
    if not idx:
        return out
    shapes = [hand_shape(clip["raw"][i], clip["width"], clip["height"]) for i in idx]
    ref = np.mean(np.stack(shapes), axis=0)
    dists = [pose_distance(n, ref) for n in shapes]
    out.update({"has_still": True, "run_ms": [float(ts[run[0]]), float(ts[run[1]])], "run_hand_frames": len(idx),
                "jitter_clip": float(np.percentile(np.asarray(dists, dtype=np.float64), 95)), "ref": ref})
    return out


def pose_calibration(profiles: Sequence[Dict[str, Any]], ratio: float) -> Dict[str, Any]:
    """Rules P1 and P2 of plan 15 lần sửa 3 §3.4 on clip profiles (clip_pose_profile)."""
    letters = [p for p in profiles if p["kind"] == "letter"]
    with_still = [p for p in letters if p["has_still"]]
    jitters = [p["jitter_clip"] for p in with_still]
    p95_jitter = _pct(jitters, 95, "rearm_pose_dist (letter clips with a still frame)")
    rearm_pose_dist = float(ratio) * p95_jitter
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in letters:
        groups[(p["signer_id"], p["session"])].append(p)
    pairs, without_ref = [], []
    for (signer, session), ps in sorted(groups.items()):
        first: Dict[str, Dict[str, Any]] = {}
        for p in ps:
            if p["symbol"] not in first or p["sample_id"] < first[p["symbol"]]["sample_id"]:
                first[p["symbol"]] = p
        for sym in sorted(first):
            if not first[sym]["has_still"]:
                without_ref.append({"signer_id": signer, "session": session, "symbol": sym})
        refs = {sym: p for sym, p in first.items() if p["has_still"]}
        for a, b in itertools.combinations(sorted(refs), 2):
            pairs.append({"signer_id": signer, "session": session, "a": a, "b": b,
                          "sample_ids": [refs[a]["sample_id"], refs[b]["sample_id"]],
                          "between": pose_distance(refs[a]["ref"], refs[b]["ref"])})
    if not pairs:
        raise ValueError("no letter pair with a reference shape (P2)")
    below = [p for p in pairs if p["between"] < rearm_pose_dist]
    coverage = 1.0 - len(below) / len(pairs)
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in below:
        grouped[(p["a"], p["b"])].append(p)
    pairs_below = [{"pair": [a, b], "n_signers": len({p["signer_id"] for p in ps}),
                    "signers": sorted({p["signer_id"] for p in ps}), "n_sessions": len(ps),
                    "between": sorted(p["between"] for p in ps)}
                   for (a, b), ps in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    return {
        "values": {"rearm_pose_dist": rearm_pose_dist},
        "inputs": {"pose_over_jitter_ratio": float(ratio), "p95_letter_jitter_clip": p95_jitter,
                   "n_letter_clips": len(letters), "n_letter_clips_with_still": len(with_still),
                   "letter_clips_without_still": sorted(p["sample_id"] for p in letters if not p["has_still"])},
        "p1": {"jitter_clip": percentile_stats(jitters),
               "jitter_clip_by_symbol": {sym: percentile_stats([p["jitter_clip"] for p in with_still
                                                                if p["symbol"] == sym])
                                         for sym in sorted({p["symbol"] for p in with_still})}},
        "p2": {"n_pairs": len(pairs), "n_pairs_below": len(below), "coverage": coverage,
               "between": percentile_stats([p["between"] for p in pairs]),
               "classes_without_ref": without_ref, "pairs_below": pairs_below,
               "stop_rule": {"threshold": POSE_COVERAGE_STOP, "triggered": bool(coverage < POSE_COVERAGE_STOP)}},
    }


def pose_report(argv: Sequence[str], config_path: str, manifest_path: str, loaded: Dict[str, Any],
                min_detected_frames: int) -> Dict[str, Any]:
    """pose_evidence.json content (AC-RP3) from clips loaded with load_train_clips."""
    cfg = load_level1_config(config_path)
    params = cfg["values"]
    profiles = [clip_pose_profile(c, params, min_detected_frames) for c in loaded["clips"]]
    cal = pose_calibration(profiles, params["pose_over_jitter_ratio"])
    return {
        "generated_by": generated_by(argv),
        "note": POSE_NOTE,
        "definitions": POSE_DEFINITIONS,
        "manifest": {"path": rel(manifest_path), "sha256": sha256_file(manifest_path)},
        "config": {"path": rel(config_path), "sha256": cfg["sha256"], "still_speed": params["still_speed"],
                   "pose_over_jitter_ratio": params["pose_over_jitter_ratio"],
                   "rearm_pose_dist_before": params["rearm_pose_dist"]},
        "train_clips": {"n_manifest_hauuto": loaded["n_manifest_hauuto"], "n_clips": len(loaded["clips"]),
                        "excluded_min_detected_frames": loaded["excluded"],
                        "min_detected_frames": int(min_detected_frames)},
        "calibration": cal,
    }


def write_pose_config(config_path: str, evidence_path: str) -> Dict[str, Any]:
    """Write rearm_pose_dist of a committed pose_evidence.json into the config (only that key; value, source with the
    commit read by committed_evidence_ref, POSE_REASON). RuntimeError (config untouched) when the evidence is not
    committed / dirty or when its P2 stop rule fired."""
    full = os.path.abspath(evidence_path if os.path.isabs(evidence_path) else os.path.join(ROOT, evidence_path))
    with open(full, encoding="utf-8") as f:
        evidence = json.load(f)
    cal = evidence["calibration"]
    if cal["p2"]["stop_rule"]["triggered"]:
        raise RuntimeError(f"P2 stop rule fired (coverage {cal['p2']['coverage']} < "
                           f"{cal['p2']['stop_rule']['threshold']}): rearm_pose_dist is not written")
    rel_evidence, commit = committed_evidence_ref(full)
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    old = dict(cfg["rearm_pose_dist"])
    cfg["rearm_pose_dist"] = {"value": cal["values"]["rearm_pose_dist"],
                              "source": f"calibrated: {rel_evidence}@{commit}", "reason": POSE_REASON}
    validate_level1_config(cfg)
    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"rearm_pose_dist": {"old": old, "new": cfg["rearm_pose_dist"]}}


# ------------------------------------------------------------------------------------------------- U1 session
def u1_summary(path: str) -> Dict[str, Any]:
    """Aggregate numbers of a level1_demo.py session JSON (never copied)."""
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    segs = s.get("segments") or []
    cap_raw = (s.get("config") or {}).get("values", {}).get("max_segment_ms")
    cap = cap_raw.get("value") if isinstance(cap_raw, dict) else cap_raw
    counts = s.get("counts") or {}
    proc_fps = counts.get("processing_fps")
    interval = (1000.0 / proc_fps) if proc_fps else None
    durations = [float(g["t_end_ms"]) - float(g["t_start_ms"]) for g in segs]
    preds = [g.get("prediction") for g in segs]
    kinds = Counter("none" if p is None else (class_kind(p) or "other") for p in preds)
    at_cap = None
    if cap is not None and interval is not None:
        at_cap = sum(1 for d in durations if d >= float(cap) - interval)
    accepted = sum(1 for g in segs if g.get("accepted"))
    return {
        "path": rel(path), "sha256": sha256_file(path), "copied": False,
        "expected": s.get("expected"),
        "session_git_commit": (s.get("generated_by") or {}).get("git_commit"),
        "session_code_dirty": (s.get("generated_by") or {}).get("code_dirty"),
        "n_segments": len(segs),
        "frames": percentile_stats([g["frames"] for g in segs]),
        "detected_frames": percentile_stats([g["detected_frames"] for g in segs]),
        "duration_ms": percentile_stats(durations),
        "duration_ms_max": max(durations) if durations else None,
        "close_reason": dict(Counter(g.get("close_reason") for g in segs)),
        "status": dict(Counter(g.get("status") for g in segs)),
        "prediction_kind": dict(kinds),
        "prediction": dict(sorted(Counter(p for p in preds if p is not None).items(),
                                  key=lambda kv: (-kv[1], kv[0]))),
        "accepted": accepted, "accepted_rate": (accepted / len(segs)) if segs else None,
        "session_max_segment_ms": cap, "session_processing_fps": proc_fps,
        "n_segments_at_cap": at_cap,
        "at_cap_definition": "duration_ms >= session max_segment_ms - 1000 / session processing_fps (one processed "
                             "frame interval short of the cap or longer: the buffer was cut by max_segment_ms)",
        "word_gaps": sum(1 for e in (s.get("events") or []) if e.get("reason") == "word_gap"),
        "note": "webcam session without --expected is not accuracy; aggregate only, the file stays in _work/",
    }


# ------------------------------------------------------------------------------------- segment check (step A3)
SEGMENT_CHECK_NOTE = "train data of the deployed checkpoint; window agreement is not accuracy"
SEGMENT_CHECK_CODE_PATHS = ("scripts/level1_segment_report.py", "scripts/level1_rearm_check.py", "src",
                            "configs/level1_realtime.json")
SEGMENT_CHECK_DEFINITIONS = {
    "clips": "every hauuto row of the manifest (training data of the deployed checkpoint), none excluded; clips with "
             "fewer hand frames than the checkpoint min_detected_frames are kept and flagged (the segmenter cannot "
             "emit for them)",
    "run": "one fresh Level1SignSegmenter per clip, every frame pushed with ts = i * 1000 / fps of the manifest, "
           "flush 1 ms after the last frame (as AC-S18 and G6 of scripts/level1_rearm_check.py); headless, "
           "deterministic",
    "n_segments": "number of SignSegment events of the clip",
    "single_segment": "exactly one SignSegment",
    "window_agrees": "exactly one SignSegment AND its Level1Classifier.classify prediction == the prediction for the "
                     "whole clip (the input of the model at training time); no prediction is never an agreement",
    "rates": "single_segment / n and window_agrees / n per group; None when n == 0",
}
KEEP_LETTER_TOLERANCE = 0.02  # plan 15 lần sửa 1 §3.A.4 (pre-registered): letters may lose at most 2 points
AC_R1_MIN_SINGLE = 0.9  # plan 15 §5 AC-R1 (kept by lần sửa 1 §3.A.4): single-segment rate with the config SAU
KEEP_RULE_TEXT = ("plan 15 lần sửa 1 §3.A.4: keep the config SAU when, for the TONE group, single_segment_rate and "
                  "window_agreement_rate of SAU >= TRUOC, AND for the LETTER group both rates of SAU >= TRUOC - 0.02; "
                  "otherwise STOP (no other value is tried). AC-R1: single_segment_rate of SAU < 0.9 for letters or "
                  "tones -> STOP")
KEEP_METRICS = ("single_segment_rate", "window_agreement_rate")


def segment_check_config(spec: str, label: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """PATH or git:REV:PATH -> (values, meta) with the keys an older commit lacks filled so that the config reproduces
    its own behaviour (scripts/level1_rearm_check.py FILL_RULES: tail_still_keep_ms = hold_ms, pose rules off,
    rearm_mode 'motion_pose'). ValueError unless rearm_mode is 'motion_pose' and pose_change_rules is false: the
    check measures the segmenter path of plan 15 A2 (lần sửa 4 §4 row 6+)."""
    from scripts.level1_rearm_check import resolve_config_spec  # lazy: level1_rearm_check imports this module
    _, values, meta = resolve_config_spec(f"{label}={spec}")
    if values["rearm_mode"] != "motion_pose":
        raise ValueError(f"segment check needs rearm_mode 'motion_pose', config {spec} has {values['rearm_mode']!r}")
    if values["pose_change_rules"]:
        raise ValueError(f"segment check compares the A2 calibration with the pose rules off; {spec} turns them on")
    meta.setdefault("filled", {})
    return values, meta


def clip_segment_check(clip: Dict[str, Any], params: Dict[str, Any], min_detected_frames: int,
                       classify) -> Dict[str, Any]:
    """One train clip: segmenter run (SEGMENT_CHECK_DEFINITIONS.run) + labels. classify(segment) -> classify dict
    (prediction read only when status == 'ok')."""
    from scripts.level1_rearm_check import whole_clip_segment
    from src.inference.level1_segmenter import SignSegment

    def label(segment) -> Optional[str]:
        r = classify(segment)
        return r.get("prediction") if r.get("status") == "ok" else None

    ts = clip_timestamps(len(clip["detected"]), clip["fps"])
    seg = Level1SignSegmenter(params, min_detected_frames)
    events: List[Any] = []
    for i, t in enumerate(ts):
        det = bool(clip["detected"][i])
        events += seg.push(float(t), clip["raw"][i] if det else None, clip["handedness"][i] if det else "",
                           clip["width"], clip["height"])
    events += seg.flush(float(ts[-1]) + 1.0)
    segments = [e for e in events if isinstance(e, SignSegment)]
    whole = label(whole_clip_segment(clip))
    preds = [label(s) for s in segments]
    single = len(segments) == 1
    return {"sample_id": clip["sample_id"], "symbol": clip["symbol"], "kind": clip["kind"],
            "signer_id": clip.get("signer_id"), "frames": int(len(clip["detected"])),
            "detected_frames": int(np.asarray(clip["detected"], dtype=bool).sum()),
            "below_min_detected_frames": bool(int(np.asarray(clip["detected"], dtype=bool).sum()) < min_detected_frames),
            "n_segments": len(segments), "close_reasons": [s.close_reason for s in segments],
            "segment_frames": [int(s.n_frames) for s in segments], "segment_predictions": preds,
            "whole_clip_prediction": whole, "single_segment": single,
            "window_agrees": bool(single and whole is not None and preds[0] == whole)}


def segment_check_groups(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts and rates per group: letters, tones, each tone."""
    groups = {"letters": [r for r in rows if r["kind"] == "letter"], "tones": [r for r in rows if r["kind"] == "tone"]}
    for t in TONES:
        groups[t] = [r for r in rows if r["symbol"] == t]
    out = {}
    for name, rs in groups.items():
        n = len(rs)
        single = sum(1 for r in rs if r["single_segment"])
        agree = sum(1 for r in rs if r["window_agrees"])
        nseg = Counter("2+" if r["n_segments"] >= 2 else str(r["n_segments"]) for r in rs)
        reasons = Counter(c for r in rs for c in r["close_reasons"])
        out[name] = {"n": n, "single_segment": single, "single_segment_rate": (single / n) if n else None,
                     "window_agrees": agree, "window_agreement_rate": (agree / n) if n else None,
                     "n_segments": {k: nseg[k] for k in ("0", "1", "2+") if nseg[k]},
                     "close_reason": dict(sorted(reasons.items())),
                     "n_below_min_detected_frames": sum(1 for r in rs if r["below_min_detected_frames"])}
    return out


def segment_check_report(argv: Sequence[str], spec: str, label: str, manifest_path: str) -> Dict[str, Any]:
    from src.inference.level1_core import Level1Classifier
    values, meta = segment_check_config(spec, label)
    clf = Level1Classifier.from_checkpoint(DEPLOYED_CKPT)
    min_det = clf.min_detected_frames
    loaded = load_train_clips(manifest_path, 0)  # every hauuto clip (none excluded), flagged below min_det
    top_k = int(values["top_k"])
    rows = [clip_segment_check(c, values, min_det, lambda s: clf.classify(s, top_k)) for c in loaded["clips"]]
    gb = generated_by(argv)
    status = _git("status", "--porcelain", "--", *SEGMENT_CHECK_CODE_PATHS)
    gb.update({"code_dirty": None if status is None else bool(status), "code_paths": list(SEGMENT_CHECK_CODE_PATHS)})
    return {
        "generated_by": gb,
        "mode": "segment_check",
        "label": label,
        "note": SEGMENT_CHECK_NOTE,
        "plan": "docs/plans/15-lan-sua-1.md §3.A.4 + docs/plans/15-lan-sua-2.md §5 (step A3)",
        "config": {"spec": spec, **meta},
        "rearm_mode": values["rearm_mode"],
        "pose_change_rules": values["pose_change_rules"],
        "segmenter_values": {k: values[k] for k in ("motion_window_ms", "still_speed", "move_speed", "hold_ms",
                                                    "tail_still_keep_ms", "rearm_move_ms", "hand_lost_ms",
                                                    "word_gap_ms", "max_segment_ms", "min_sign_frames")},
        "inputs": {"manifest": {"path": rel(manifest_path), "sha256": sha256_file(manifest_path)},
                   "checkpoint": {"path": rel(DEPLOYED_CKPT), "sha256": sha256_file(DEPLOYED_CKPT),
                                  "min_detected_frames": min_det}},
        "clip_counts": {"n_manifest_hauuto": loaded["n_manifest_hauuto"], "n_clips": len(rows),
                        "n_letter_clips": sum(1 for r in rows if r["kind"] == "letter"),
                        "n_tone_clips": sum(1 for r in rows if r["kind"] == "tone"),
                        "n_below_min_detected_frames": sum(1 for r in rows if r["below_min_detected_frames"])},
        "definitions": SEGMENT_CHECK_DEFINITIONS,
        "groups": segment_check_groups(rows),
        "clips": rows,
    }


def keep_rule(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-registered keep rule of plan 15 lần sửa 1 §3.A.4 + AC-R1 on two segment_check reports (numbers read from
    the JSON). ValueError when the clip sets differ (AC-R'3) or a rate is missing."""
    ids_b = [c["sample_id"] for c in before.get("clips", [])]
    ids_a = [c["sample_id"] for c in after.get("clips", [])]
    if ids_b != ids_a:
        raise ValueError("segment_check reports cover different clips (plan 15 AC-R'3 needs the same set)")
    vals: Dict[str, Dict[str, Any]] = {}
    keep = True
    for group, tol in (("tones", 0.0), ("letters", KEEP_LETTER_TOLERANCE)):
        vals[group] = {}
        for m in KEEP_METRICS:
            b = before["groups"][group].get(m)
            a = after["groups"][group].get(m)
            if b is None or a is None:
                raise ValueError(f"segment_check {group}.{m} missing")
            ok = bool(a >= b - tol)
            vals[group][m] = {"before": b, "after": a, "pass": ok}
            keep = keep and ok
    r1 = {g: after["groups"][g]["single_segment_rate"] for g in ("letters", "tones")}
    r1_pass = all(v >= AC_R1_MIN_SINGLE for v in r1.values())
    return {"rule": KEEP_RULE_TEXT, "values": vals, "keep": keep,
            "ac_r1": {"min": AC_R1_MIN_SINGLE, "after_single_segment_rate": r1, "pass": r1_pass},
            "stop": not (keep and r1_pass)}


# --------------------------------------------------------------------------------------------- summary (step C1)
DEMO_CONFIG = os.path.join(ROOT, "configs", "level1_demo_classifier.json")
SUMMARY_GROUPS = ("letters", "tones") + TONES


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _source(path: str) -> str:
    """`path` @ first 7 characters of the last commit of the file ('uncommitted' when untracked or changed), sha256."""
    r = rel(path)
    tracked = _git("ls-files", "--error-unmatch", "--", r) is not None
    clean = _git("status", "--porcelain", "--", r) == ""
    commit = _git("log", "-1", "--format=%H", "--", r) if tracked and clean else None
    return f"`{r}` @ {commit[:7] if commit else 'uncommitted'}, sha256 `{sha256_file(path)[:16]}…`"


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_summary(out_path: str, evidence_path: Optional[str] = None, demo_config: str = DEMO_CONFIG) -> str:
    """SUMMARY.md of reports/level1_realtime_<D>/ (plan 15 lần sửa 1 §4 C1, AC-R'4): every number is read by code from
    the JSON named in its section; no clock, no HEAD commit, so the same inputs give the same bytes."""
    out_dir = os.path.dirname(os.path.abspath(out_path))
    evidence_path = evidence_path or DEFAULT_EVIDENCE
    ev_full = evidence_path if os.path.isabs(evidence_path) else os.path.join(ROOT, evidence_path)
    L: List[str] = [
        f"# Level 1 realtime — SUMMARY (`{rel(out_dir)}`)",
        "",
        f"Generated by `python scripts/level1_segment_report.py --summary --out {rel(out_path)}` — do not edit by hand. "
        "Every number below is read by code from the JSON named in its section (path @ commit of that file, sha256). "
        "Train clips are the training data of the deployed checkpoint: the checks on them test logic, they are not "
        "accuracy and not a webcam session.",
        "",
    ]

    # 1. offline model
    L += ["## 1. Offline model (out-of-fold, nested LOSO)", ""]
    ev = _load_json(ev_full)
    if ev is None:
        L += [f"Missing `{rel(ev_full)}`.", ""]
    else:
        L += [f"Source: {_source(ev_full)}. Note: {ev.get('note')}.", ""]
        tot = ev["nested_per_class"]["total"]
        L += ["| Tone mark | n | correct | top-1 (%) |", "|---|---|---|---|"]
        for t in TONES:
            c = tot["per_class"].get(t, {})
            L.append(f"| {t} | {_fmt(c.get('n'))} | {_fmt(c.get('correct'))} | {_fmt(c.get('top1'))} |")
        L.append(f"| all tones | {_fmt(tot['tones']['n'])} | {_fmt(tot['tones']['correct'])} | "
                 f"{_fmt(tot['tones']['top1'])} |")
        L += ["", "Variants (mean ± sd over the 4 outer folds, %; deployed run = `frame`):", "",
              "| Variant | letters mean | letters sd | tones mean | tones sd |", "|---|---|---|---|---|"]
        for v, blk in ev["variants_summary"]["variants"].items():
            L.append(f"| {v} | {_fmt(blk['letters']['mean'])} | {_fmt(blk['letters']['sd'])} | "
                     f"{_fmt(blk['tones']['mean'])} | {_fmt(blk['tones']['sd'])} |")
        L.append("")

    # 2. segment check (A3)
    L += ["## 2. Segmenter check on train clips (step A3, `rearm_mode` motion_pose)", ""]
    paths = {k: os.path.join(out_dir, f"segment_check_{k}.json") for k in ("before", "after")}
    sc = {k: _load_json(p) for k, p in paths.items()}
    if sc["before"] is None or sc["after"] is None:
        L += ["No `segment_check_before.json` / `segment_check_after.json` in this folder.", ""]
    else:
        for k in ("before", "after"):
            cfg = sc[k]["config"]
            filled = ", ".join(sorted(cfg.get("filled") or {})) or "none"
            L.append(f"- {k}: {_source(paths[k])}; config `{cfg.get('path')}` @ {str(cfg.get('git_commit'))[:7]}, "
                     f"keys filled: {filled}")
        L += ["", "| Group | n | single TRƯỚC | single SAU | agreement TRƯỚC | agreement SAU |",
              "|---|---|---|---|---|---|"]
        for g in SUMMARY_GROUPS:
            b, a = sc["before"]["groups"].get(g), sc["after"]["groups"].get(g)
            if b is None or a is None:
                continue
            L.append(f"| {g} | {a['n']} | {_fmt(b['single_segment_rate'])} | {_fmt(a['single_segment_rate'])} | "
                     f"{_fmt(b['window_agreement_rate'])} | {_fmt(a['window_agreement_rate'])} |")
        kr = keep_rule(sc["before"], sc["after"])
        r1 = kr["ac_r1"]["after_single_segment_rate"]
        L += ["", f"Keep rule: {kr['rule']}.", "",
              f"Result: keep **{_fmt(kr['keep'])}**; AC-R1 (single SAU ≥ {kr['ac_r1']['min']}: letters "
              f"{_fmt(r1['letters'])}, tones {_fmt(r1['tones'])}) **{'pass' if kr['ac_r1']['pass'] else 'FAIL'}**; "
              f"stop **{_fmt(kr['stop'])}**.", ""]

    # 3. demo re-arm mode (D4) + demo config
    L += ["## 3. Demo re-arm mode (label decoder, gates of step D4)", ""]
    d4s = []
    for name in sorted(os.listdir(out_dir)):
        if name.startswith("rearm_check_") and name.endswith(".json"):
            rep = _load_json(os.path.join(out_dir, name))
            if rep and rep.get("mode") == "decoder" and isinstance(rep.get("gates"), dict):
                d4s.append((name, rep))
    if not d4s:
        L += ["No decoder `rearm_check_*.json` in this folder.", ""]
    for name, rep in d4s:
        gates = rep["gates"]
        L += [f"Source: {_source(os.path.join(out_dir, name))}; gate config `{gates['gate_config']}` vs baseline "
              f"`{gates['baseline_config']}`. Note: {rep.get('note')}.", "",
              "| Gate | values | pass |", "|---|---|---|"]
        for gname, g in gates["gates"].items():
            vals = "; ".join(f"{k}: " + (", ".join(f"{kk} {_fmt(vv)}" for kk, vv in v.items()) if isinstance(v, dict)
                                          else _fmt(v)) for k, v in g["values"].items())
            L.append(f"| {gname} | {vals} | {_fmt(g['pass'])} |")
        L += ["", f"All gates pass: {_fmt(gates['all_pass'])}; failed: {', '.join(gates.get('failed') or []) or '—'}.", ""]
        q = rep.get("qipedc_g7") or {}
        if q.get("configs"):
            L += [f"G7 QIPEDC (report only, {q.get('n_clips')} clips): " + "; ".join(
                f"{k} ({c['rearm_mode']}) whole-clip label emitted {_fmt(c['whole_label_emitted_rate'])}, "
                f"symbol emitted {_fmt(c['symbol_emitted_rate'])}" for k, c in sorted(q["configs"].items())) + ".", ""]
    demo = _load_json(demo_config)
    if demo is not None:
        dec = demo.get("_user_decision") or {}
        L += [f"Demo config: {_source(demo_config)}; `rearm_mode` = {demo['rearm_mode']['value']}; user decision "
              f"{dec.get('choice')} ({dec.get('decided')}), gate failed: {dec.get('gate_failed')}, evidence "
              f"`{dec.get('evidence')}`.", ""]

    # 4. webcam sessions
    L += ["## 4. Webcam sessions (`webcam_*.json`, one signer, not an evaluation)", ""]
    cams = sorted(n for n in os.listdir(out_dir) if n.startswith("webcam_") and n.endswith(".json"))
    if not cams:
        L += ["None in this folder (user steps U2 / U2b not run).", ""]
    else:
        L += ["| File | expected | text | matches | rearm_mode | segments | labels | processing fps |",
              "|---|---|---|---|---|---|---|---|"]
        for n in cams:
            w = _load_json(os.path.join(out_dir, n))
            exp = w.get("expected") or {}
            L.append(f"| {_source(os.path.join(out_dir, n))} | {_fmt(exp.get('text'))} | {_fmt(w.get('text'))} | "
                     f"{_fmt(exp.get('matches_text'))} | {_fmt(w.get('rearm_mode'))} | {len(w.get('segments') or [])} | "
                     f"{len(w.get('labels') or [])} | {_fmt((w.get('counts') or {}).get('processing_fps'))} |")
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


# ------------------------------------------------------------------------------------------------------- main
def build_report(argv: Sequence[str], config_path: str, u1_json: Optional[str]) -> Dict[str, Any]:
    from src.inference.level1_core import Level1Classifier
    with open(PRIMARY_REPORT, encoding="utf-8") as f:
        primary = json.load(f)
    nested = nested_per_class(read_predictions(PRIMARY_PREDICTIONS), primary)
    if not nested["check"]["matches"]:
        raise SystemExit(f"STOP (plan stop point 3): out-of-fold CSV does not match nested_report.json: "
                         f"{json.dumps(nested['check'])}")
    cfg = load_level1_config(config_path)
    params = cfg["values"]
    min_det = Level1Classifier.from_checkpoint(DEPLOYED_CKPT).min_detected_frames
    loaded = load_train_clips(MANIFEST, min_det)
    clips = []
    for c in loaded["clips"]:
        ts = clip_timestamps(len(c["detected"]), c["fps"])
        clips.append({"sample_id": c["sample_id"], "kind": c["kind"], "symbol": c["symbol"], "timestamps_ms": ts,
                      "motion": motion_series(c["raw"], c["detected"], c["handedness"], c["width"], c["height"],
                                              ts, params, min_det)})
    cal = calibrate(clips, params)
    profiles = cal.pop("profiles")
    report = {
        "generated_by": generated_by(argv),
        "note": NOTE,
        "plan": "docs/plans/15-lan-sua-1.md §3.A.3 (step A1)",
        "inputs": {
            "manifest": {"path": rel(MANIFEST), "sha256": sha256_file(MANIFEST)},
            "primary_report": {"path": rel(PRIMARY_REPORT), "sha256": sha256_file(PRIMARY_REPORT)},
            "primary_predictions": {"path": rel(PRIMARY_PREDICTIONS), "sha256": sha256_file(PRIMARY_PREDICTIONS)},
            "variants_report": {"path": rel(VARIANTS_REPORT), "sha256": sha256_file(VARIANTS_REPORT)},
            "config": {"path": rel(config_path), "sha256": cfg["sha256"]},
            "checkpoint": {"path": rel(DEPLOYED_CKPT), "sha256": sha256_file(DEPLOYED_CKPT),
                           "min_detected_frames": min_det},
        },
        "nested_per_class": nested,
        "variants_summary": variants_summary(VARIANTS_REPORT),
        "train_profiles": {
            "source": "hauuto clips of the manifest (training data of the deployed checkpoint)",
            "n_manifest_hauuto": loaded["n_manifest_hauuto"], "n_clips": len(clips),
            "n_letter_clips": sum(1 for c in clips if c["kind"] == "letter"),
            "n_tone_clips": sum(1 for c in clips if c["kind"] == "tone"),
            "excluded_below_min_detected_frames": loaded["excluded"],
            "motion_params": {k: params[k] for k in ("motion_window_ms", "hand_lost_ms")},
            "motion_params_note": "M_t depends only on motion_window_ms and hand_lost_ms (design values of the "
                                  "config); still_speed / move_speed are those of calibration rule 1",
            "thresholds": {"still_speed": cal["values"]["still_speed"], "move_speed": cal["values"]["move_speed"]},
            "definitions": DEFINITIONS,
            "groups": group_stats(profiles),
        },
        "calibration": {"rules": "plan 15 lần sửa 1 §3.A.3 rules 1-6 (pre-registered)",
                        "design_inputs": {"move_over_still_ratio": params["move_over_still_ratio"],
                                          "hold_ms_design": params["hold_ms_design"]},
                        "config_values_before": {k: params[k] for k in ("still_speed", "move_speed", "hold_ms",
                                                                        "max_segment_ms")},
                        **cal},
    }
    if u1_json:
        report["u1"] = u1_summary(u1_json)
    return report


CALIBRATED_KEYS = ("still_speed", "move_speed", "hold_ms", "max_segment_ms", "tail_still_keep_ms")
DEFAULT_EVIDENCE = "reports/level1_realtime_2026-10-03/tone_evidence.json"
# reason written with each calibrated key (plan 15 lần sửa 2 §6.1, AC-W2): the rule of calibrate(), no measured number
CALIBRATION_REASONS = {
    "still_speed": "calibrated on the train clips of the deployed checkpoint: the ninetieth percentile, over the letter "
                   "clips, of the per-clip median of the segmenter motion signal M_t",
    "move_speed": "calibrated: still_speed multiplied by move_over_still_ratio (design), so moving is a fixed multiple "
                  "of the still threshold (hysteresis)",
    "hold_ms": "calibrated on the train clips of the deployed checkpoint: the smaller of hold_ms_design and the tenth "
               "percentile, over the letter clips, of the longest still run of each clip",
    "max_segment_ms": "calibrated on the train clips of the deployed checkpoint: the ninety-fifth percentile, over all "
                      "clips, of the clip duration, rounded up to a whole millisecond",
    "tail_still_keep_ms": "calibrated on the train clips of the deployed checkpoint: the smaller of hold_ms and the "
                          "median, over the clips with motion, of the still time after the last motion",
}


def committed_evidence_ref(evidence_path: str) -> Tuple[str, str]:
    """(repo-relative path, abbreviated commit) of an evidence JSON that is committed and has no uncommitted change.
    RuntimeError otherwise: the commit is always read from git, never typed by hand and never taken from the JSON's
    generated_by (that is the commit of the code, not of the JSON) — plan 15 lần sửa 2 AC-W1. Shared by write_config
    and the pose calibration of step R2."""
    full = os.path.abspath(evidence_path if os.path.isabs(evidence_path) else os.path.join(ROOT, evidence_path))
    rel_path = rel(full)
    if _git("ls-files", "--error-unmatch", "--", rel_path) is None:
        raise RuntimeError(f"evidence {rel_path} is not tracked by git: commit it before writing the config")
    status = _git("status", "--porcelain", "--", rel_path)
    if status is None or status != "":
        raise RuntimeError(f"evidence {rel_path} has uncommitted changes: commit it before writing the config")
    full_commit = _git("log", "-1", "--format=%H", "--", rel_path)
    if not full_commit:
        raise RuntimeError(f"evidence {rel_path} is in no commit: commit it before writing the config")
    short = _git("rev-parse", "--short=7", full_commit)
    if not short:
        raise RuntimeError(f"cannot abbreviate commit {full_commit}")
    return rel_path, short


def write_config(config_path: str, evidence_path: str = DEFAULT_EVIDENCE) -> Dict[str, Any]:
    full_evidence = os.path.abspath(evidence_path if os.path.isabs(evidence_path) else os.path.join(ROOT, evidence_path))
    if not os.path.exists(full_evidence):
        raise FileNotFoundError(f"evidence JSON not found: {full_evidence}")
    with open(full_evidence, "r", encoding="utf-8") as f:
        evidence = json.load(f)
    if "calibration" not in evidence or "values" not in evidence["calibration"]:
        raise ValueError(f"evidence JSON {evidence_path} missing calibration.values")
    cal_values = evidence["calibration"]["values"]

    missing_cal = [k for k in CALIBRATED_KEYS if k not in cal_values]
    if missing_cal:
        raise ValueError(f"calibration.values missing keys: {missing_cal}")

    rel_evidence, commit = committed_evidence_ref(full_evidence)
    source_str = f"calibrated: {rel_evidence}@{commit}"

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    changes = {}
    for k in CALIBRATED_KEYS:
        if k not in cfg:
            raise KeyError(f"target config {config_path} missing key {k!r}")
        old_val = cfg[k]["value"]
        old_source = cfg[k]["source"]
        old_reason = cfg[k]["reason"]
        new_val = cal_values[k]
        cfg[k]["value"] = new_val
        cfg[k]["source"] = source_str
        cfg[k]["reason"] = CALIBRATION_REASONS[k]
        changes[k] = {
            "old_value": old_val,
            "new_value": new_val,
            "old_source": old_source,
            "new_source": source_str,
            "old_reason": old_reason,
            "new_reason": CALIBRATION_REASONS[k],
        }

    validate_level1_config(cfg)

    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return changes


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=None, help="output JSON (reports/level1_realtime_<D>/tone_evidence.json)")
    ap.add_argument("--config", default=CONFIG, help="Level 1 config (default %(default)s)")
    ap.add_argument("--write-config", default=None, help="write calibrated parameters to config file")
    ap.add_argument("--evidence-json", default=DEFAULT_EVIDENCE, help="path to tone evidence JSON (default %(default)s)")
    ap.add_argument("--u1-json", default=None, help="optional webcam session JSON of level1_demo.py (aggregated)")
    ap.add_argument("--pose-evidence", action="store_true",
                    help="step R2: write the pose evidence JSON (rules P1, P2) to --out instead of tone_evidence")
    ap.add_argument("--write-pose-config", default=None,
                    help="step R2: write rearm_pose_dist of --pose-evidence-json into this config")
    ap.add_argument("--pose-evidence-json", default=None,
                    help="committed pose_evidence.json read by --write-pose-config (required with it)")
    ap.add_argument("--segment-check", action="store_true",
                    help="step A3: run the segmenter on every train clip with --config (PATH or git:REV:PATH) and "
                         "write segment_check JSON to --out")
    ap.add_argument("--label", default=None, help="name of the config in the segment check (e.g. before, after)")
    ap.add_argument("--manifest", default=MANIFEST, help="manifest of the train clips (default %(default)s)")
    ap.add_argument("--keep-rule", nargs=2, metavar=("BEFORE", "AFTER"), default=None,
                    help="step A3: apply the pre-registered keep rule to two segment_check JSON files")
    ap.add_argument("--summary", action="store_true",
                    help="step C1: write SUMMARY.md (--out) from the JSON files of its folder + --evidence-json")
    args = ap.parse_args(argv)

    if args.summary:
        if not args.out:
            ap.error("--out is required with --summary")
        text = build_summary(args.out, args.evidence_json)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"wrote {rel(args.out)}")
        return 0
    if args.keep_rule:
        reports = []
        for path in args.keep_rule:
            with open(path, encoding="utf-8") as f:
                reports.append(json.load(f))
        res = keep_rule(*reports)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print("keep rule:", "KEEP" if res["keep"] else "FAIL", "| AC-R1:", "pass" if res["ac_r1"]["pass"] else "FAIL",
              "| STOP" if res["stop"] else "")
        return 5 if res["stop"] else 0
    if args.segment_check:
        if not args.out or not args.label:
            ap.error("--out and --label are required with --segment-check")
        report = segment_check_report(argv, args.config, args.label, args.manifest)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        g = report["groups"]
        print(f"wrote {rel(args.out)}: clips={report['clip_counts']['n_clips']} "
              f"code_dirty={report['generated_by']['code_dirty']}")
        for name in ("letters", "tones"):
            print(f"  {name}: n={g[name]['n']} single_segment_rate={g[name]['single_segment_rate']} "
                  f"window_agreement_rate={g[name]['window_agreement_rate']}")
        return 0

    if args.write_pose_config:
        if not args.pose_evidence_json:
            ap.error("--pose-evidence-json is required with --write-pose-config")
        change = write_pose_config(args.write_pose_config, args.pose_evidence_json)["rearm_pose_dist"]
        print(f"wrote rearm_pose_dist into {rel(args.write_pose_config)}: {change['old']['value']} "
              f"({change['old']['source']}) -> {change['new']['value']} ({change['new']['source']})")
        return 0
    if args.pose_evidence:
        if not args.out:
            ap.error("--out is required with --pose-evidence")
        from src.inference.level1_core import Level1Classifier
        min_det = Level1Classifier.from_checkpoint(DEPLOYED_CKPT).min_detected_frames
        report = pose_report(argv, args.config, MANIFEST, load_train_clips(MANIFEST, min_det), min_det)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        cal = report["calibration"]
        print(f"wrote {rel(args.out)}: rearm_pose_dist {cal['values']['rearm_pose_dist']}, P2 coverage "
              f"{cal['p2']['coverage']} ({cal['p2']['n_pairs']} pairs), stop {cal['p2']['stop_rule']['triggered']}")
        return 2 if cal["p2"]["stop_rule"]["triggered"] else 0

    if args.write_config:
        changes = write_config(args.write_config, args.evidence_json)
        print(f"wrote calibrated config {rel(args.write_config)}")
        print("changes:")
        for k, v in changes.items():
            print(f"  {k}: {v['old_value']} ({v['old_source']}) -> {v['new_value']} ({v['new_source']})")
        return 0

    if not args.out:
        ap.error("--out is required when --write-config is not given")
    report = build_report(argv, args.config, args.u1_json)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    cal = report["calibration"]
    print(f"wrote {rel(args.out)}: clips={report['train_profiles']['n_clips']} "
          f"code_dirty={report['generated_by']['code_dirty']}")
    print("calibration values:", json.dumps(cal["values"], ensure_ascii=False))
    print("rule6:", json.dumps(cal["rule6"], ensure_ascii=False))
    if cal["rule6"]["triggered"]:
        print("STOP: rule 6 triggered (plan 15 lần sửa 1 §3.A.3 / §7 stop point 1)")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
