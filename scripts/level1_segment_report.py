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
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
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

from src.inference.fingerspelling_compose import TONE_MARKS  # noqa: E402
from src.inference.level1_core import class_kind, load_level1_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter  # noqa: E402

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
    p50_trailing = _pct([p["trailing_still_ms"] for p in moving_p], 50, "tail_still_keep_ms (clips with motion)")
    tail_still_keep_ms = min(hold_ms, p50_trailing)
    # rule 6 (pre-registered stop point)
    p90_internal = _pct([p["longest_internal_still_ms"] for p in tone_moving_p], 90,
                        "rule 6 (tone clips with motion)")
    triggered = bool(p90_internal >= hold_ms)
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


# ------------------------------------------------------------------------------------------------- U1 session
def u1_summary(path: str) -> Dict[str, Any]:
    """Aggregate numbers of a level1_demo.py session JSON (never copied)."""
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    segs = s.get("segments") or []
    cap = (s.get("config") or {}).get("values", {}).get("max_segment_ms")
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="output JSON (reports/level1_realtime_<D>/tone_evidence.json)")
    ap.add_argument("--config", default=CONFIG, help="Level 1 config (default %(default)s)")
    ap.add_argument("--u1-json", default=None, help="optional webcam session JSON of level1_demo.py (aggregated)")
    args = ap.parse_args(argv)
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
