#!/usr/bin/env python
"""
Plan 15 Lần sửa 3 — Step R0: Re-arm check on concatenated train clips.

Concatenates train clips from hauuto (letters, tones, repetitions) to test the segmenter logic
under continuous signing without webcam or synthetic data.

Notice: train clips concatenated to test the segmenter logic; not accuracy, not a webcam session.

Step R3 (plan 15 lần sửa 3 §3.5, §4 #6, §5): --set NAME:KEY=JSON overrides one config key (e.g. on:pose_change_rules=true,
recorded in the report), the L chain also gets one_rate_covered (clips whose pair (previous clip, this clip) has
pose_distance(ref_prev, ref) >= rearm_pose_dist, ref = the R2 reference shape of the clip), --gates ON:OFF runs every
single clip (G6) and evaluates the pre-registered gates G1-G6; --write-rules-config CONFIG --rearm-json JSON switches
pose_change_rules to true only from a committed R3 JSON whose gates all passed.
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
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.inference.fingerspelling_compose import TONE_MARKS  # noqa: E402
from src.inference.level1_core import (  # noqa: E402
    Level1Classifier, class_kind, load_level1_config, validate_level1_config,
)
from src.inference.level1_segmenter import Level1SignSegmenter, SignSegment, pose_distance  # noqa: E402
from scripts import level1_segment_report as seg_report  # noqa: E402  (R2 reference shape, A2b commit helper)

KAGGLE_DIR = os.path.join(ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands")
DEFAULT_MANIFEST = os.path.join(KAGGLE_DIR, "manifest.csv")
DEFAULT_CKPT = os.path.join(ROOT, "checkpoints", "alphabet_best.pt")
DEFAULT_CONFIG = os.path.join(ROOT, "configs", "level1_realtime.json")
CODE_PATHS = ("scripts/level1_rearm_check.py", "src", "configs/level1_realtime.json")
NOTE = "train clips concatenated to test the segmenter logic; not accuracy, not a webcam session"
NOTE_VI = "chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác"
# pre-registered gates of plan 15 lần sửa 3 §5 R3 (never changed after seeing a result)
GATE_THRESHOLDS = {"G1_one_rate_covered_min": 0.90, "G2_multi_rate_max": 0.05, "G5_garbage_per_clip_max": 0.05,
                   "G6_single_drop_max": 0.02}
GATE_RULES = {
    "G1": "chain L, joins 0 and 300 ms: one_rate_covered >= 0.90 (gate config)",
    "G2": "chain L, every join: multi_rate <= 0.05",
    "G3": "every chain (L, T, O), every join: hand_lost == 0",
    "G4": "chain L, every join: order_ok",
    "G5": "chain L, joins 300 and 600 ms: garbage_per_clip <= 0.05",
    "G6": "single clips: single_segment_rate(gate) >= single_segment_rate(baseline) - 0.02, letters and tones",
}
GATE_JOINS = ("0", "300", "600")
TONES = tuple(TONE_MARKS.keys())


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


GIT_SPEC_PREFIX = "git:"
# keys added to the config after some commits, filled so that an older config reproduces its own behaviour:
# - tail_still_keep_ms == hold_ms keeps every buffered frame = behaviour before the key (plan 15 lần sửa 2 §2/§5);
# - pose_change_rules false = the segmenter without the pose rules (lần sửa 3 §3.2, AC-RA6); rearm_pose_dist and
#   pose_over_jitter_ratio are then never read by the segmenter, the values of DEFAULT_CONFIG only make the config valid;
# - rearm_mode 'motion_pose' = the segmenter path (lần sửa 4 §3.3); cls_* are then never read
FILL_RULES = {
    "tail_still_keep_ms": "= hold_ms of this config",
    "pose_change_rules": "= false (the pose rules did not exist at this commit)",
    "rearm_pose_dist": "= value in configs/level1_realtime.json on disk (not read while pose_change_rules is false)",
    "pose_over_jitter_ratio": "= value in configs/level1_realtime.json on disk (not read by the segmenter)",
    "rearm_mode": "= 'motion_pose' (the label decoder did not exist at this commit)",
    "cls_window_ms": "= value in configs/level1_realtime.json on disk (not read while rearm_mode is 'motion_pose')",
    "cls_conf": "= value in configs/level1_realtime.json on disk (not read while rearm_mode is 'motion_pose')",
    "cls_stable_ms": "= value in configs/level1_realtime.json on disk (not read while rearm_mode is 'motion_pose')",
}


def _git_bytes(*args) -> bytes:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def _fill_missing(raw: Dict[str, Any]) -> Dict[str, str]:
    """Fill the keys of FILL_RULES that a config read from an older commit lacks; returns {key: rule} of what was
    filled (recorded in the report)."""
    filled = {}
    if "tail_still_keep_ms" not in raw and isinstance(raw.get("hold_ms"), dict) and "value" in raw["hold_ms"]:
        raw["tail_still_keep_ms"] = {
            "value": raw["hold_ms"]["value"],
            "source": "design",
            "reason": "filled by scripts/level1_rearm_check.py: the key did not exist at this commit; "
                      "tail_still_keep_ms == hold_ms reproduces the behaviour before the key",
        }
        filled["tail_still_keep_ms"] = FILL_RULES["tail_still_keep_ms"]
    if "pose_change_rules" not in raw:
        reason = "filled by scripts/level1_rearm_check.py: the key did not exist at this commit"
        raw["pose_change_rules"] = {"value": False, "source": "design", "reason": reason}
        filled["pose_change_rules"] = FILL_RULES["pose_change_rules"]
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            disk = json.load(f)
        for key in ("rearm_pose_dist", "pose_over_jitter_ratio"):
            if key not in raw:
                raw[key] = {"value": disk[key]["value"], "source": "design", "reason": reason}
                filled[key] = FILL_RULES[key]
    if "rearm_mode" not in raw:  # plan 15 lần sửa 4 §3.3: keys of the label decoder
        reason = "filled by scripts/level1_rearm_check.py: the key did not exist at this commit"
        raw["rearm_mode"] = {"value": "motion_pose", "source": "design", "reason": reason}
        filled["rearm_mode"] = FILL_RULES["rearm_mode"]
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            disk = json.load(f)
        for key in ("cls_window_ms", "cls_conf", "cls_stable_ms"):
            if key not in raw:
                raw[key] = {"value": disk[key]["value"], "source": "design", "reason": reason}
                filled[key] = FILL_RULES[key]
    return filled


def resolve_config_spec(spec: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """NAME=PATH or NAME=git:REV:PATH -> (name, values, meta).

    - PATH: the file on disk; meta.git_commit = last commit of PATH when PATH is tracked and has no uncommitted
      change, else None (never an empty string) and meta.committed = False.
    - git:REV:PATH: the config read with `git show REV:PATH` (nothing written to disk); keys of FILL_RULES missing
      at REV are filled and listed in meta.filled; meta.git_commit = full hash of REV; sha256 of the git blob.
    """
    if "=" not in spec:
        raise ValueError(f"Config spec must be NAME=PATH or NAME={GIT_SPEC_PREFIX}REV:PATH, got {spec!r}")
    name, target = spec.split("=", 1)
    if target.startswith(GIT_SPEC_PREFIX):
        rev_path = target[len(GIT_SPEC_PREFIX):]
        if ":" not in rev_path:
            raise ValueError(f"Config spec {spec!r}: expected {GIT_SPEC_PREFIX}REV:PATH")
        rev, path = rev_path.split(":", 1)
        commit = _git_bytes("rev-parse", "--verify", f"{rev}^{{commit}}").decode("utf-8").strip()
        data = _git_bytes("show", f"{commit}:{path}")
        raw = json.loads(data.decode("utf-8"))
        filled = _fill_missing(raw)
        values = validate_level1_config(raw)
        meta = {"path": path, "source": f"git show {rev}:{path}", "sha256": hashlib.sha256(data).hexdigest(),
                "git_commit": commit, "committed": True, "filled": filled}
        return name, values, meta
    cfg = load_level1_config(target)
    tracked = _git("ls-files", "--error-unmatch", "--", target) is not None
    status = _git("status", "--porcelain", "--", target)
    commit = _git("log", "-1", "--format=%H", "--", target) if tracked and status == "" else None
    meta = {"path": rel(target), "sha256": cfg["sha256"], "git_commit": commit or None,
            "committed": bool(commit)}
    return name, cfg["values"], meta


def generated_by(argv: Sequence[str]) -> Dict[str, Any]:
    import torch
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    return {
        "command": " ".join(["python", "scripts/level1_rearm_check.py", *argv]),
        "git_commit": _git("rev-parse", "HEAD"),
        "code_dirty": None if status is None else bool(status),
        "code_paths": list(CODE_PATHS),
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cpu": platform.processor(),
        "os": platform.platform(),
    }


def prepare_clip(clip: Dict[str, Any], hand_lost_ms: float = 200.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Trim leading and trailing no-hand frames.
    Exclude clip if any internal gap of missing hand >= hand_lost_ms.
    Returns (prepared_clip, None) or (None, rejection_reason).
    """
    detected = np.asarray(clip["detected"], dtype=bool)
    idxs = np.where(detected)[0]
    if len(idxs) == 0:
        return None, "no_hand_frames"

    first_idx, last_idx = int(idxs[0]), int(idxs[-1])
    det_trimmed = detected[first_idx : last_idx + 1]
    fps = float(clip["fps"])

    # Check internal runs of missing hand
    last_hand_ts = 0.0
    for i, d in enumerate(det_trimmed):
        ts = i * 1000.0 / fps
        if d:
            last_hand_ts = ts
        else:
            if ts - last_hand_ts >= hand_lost_ms:
                return None, "internal_hand_lost"

    prepared = dict(clip)
    prepared["raw"] = np.asarray(clip["raw"][first_idx : last_idx + 1], dtype=np.float32)
    prepared["detected"] = det_trimmed
    prepared["handedness"] = list(clip["handedness"][first_idx : last_idx + 1])
    prepared["n_frames"] = len(det_trimmed)
    prepared["duration_ms"] = (len(det_trimmed) - 1) * 1000.0 / fps if len(det_trimmed) > 1 else 0.0
    return prepared, None


def interpolate_join(
    raw_prev: np.ndarray,
    handedness_prev: str,
    raw_next: np.ndarray,
    fps: float,
    join_ms: float,
) -> Dict[str, Any]:
    """
    Linearly interpolate raw landmarks between raw_prev and raw_next for join_ms duration.
    join_ms <= 0 yields 0 frames.
    join_ms > 0 yields round(join_ms * fps / 1000) frames with handedness of preceding clip.
    """
    n_join = int(round(join_ms * fps / 1000.0))
    if n_join <= 0:
        return {
            "raw": np.zeros((0, 21, 3), dtype=np.float32),
            "detected": np.zeros((0,), dtype=bool),
            "handedness": [],
        }

    raw_join = np.zeros((n_join, 21, 3), dtype=np.float32)
    prev_f = raw_prev.astype(np.float32)
    next_f = raw_next.astype(np.float32)
    for k in range(1, n_join + 1):
        alpha = float(k) / float(n_join + 1)
        raw_join[k - 1] = (1.0 - alpha) * prev_f + alpha * next_f

    return {
        "raw": raw_join,
        "detected": np.ones((n_join,), dtype=bool),
        "handedness": [str(handedness_prev)] * n_join,
    }


def build_concatenated_sequence(
    clips: Sequence[Dict[str, Any]],
    join_ms: float,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Concatenate a list of candidate clips into a single continuous stream.
    Clips must match size and fps of the first clip; mismatches are excluded and counted.
    """
    if not clips:
        return {"raw": np.zeros((0, 21, 3), dtype=np.float32), "detected": np.zeros((0,), dtype=bool),
                "handedness": [], "timestamps_ms": np.zeros((0,), dtype=np.float64), "frame_sources": [],
                "kept_clips": [], "fps": 0.0, "width": 0, "height": 0}, {"excluded_mismatch": 0, "mismatched_sample_ids": []}

    ref_fps = float(clips[0]["fps"])
    ref_size = (int(clips[0]["width"]), int(clips[0]["height"]))

    kept: List[Dict[str, Any]] = [clips[0]]
    mismatched: List[str] = []

    for c in clips[1:]:
        if (int(c["width"]), int(c["height"])) == ref_size and abs(float(c["fps"]) - ref_fps) <= 1e-4:
            kept.append(c)
        else:
            mismatched.append(c.get("sample_id", "unknown"))

    raw_blocks: List[np.ndarray] = []
    det_blocks: List[np.ndarray] = []
    hand_blocks: List[str] = []
    source_blocks: List[Any] = []

    for i, c in enumerate(kept):
        if i > 0 and join_ms > 0:
            join = interpolate_join(
                kept[i - 1]["raw"][-1],
                kept[i - 1]["handedness"][-1],
                c["raw"][0],
                fps=ref_fps,
                join_ms=join_ms,
            )
            n_join = len(join["detected"])
            if n_join > 0:
                raw_blocks.append(join["raw"])
                det_blocks.append(join["detected"])
                hand_blocks.extend(join["handedness"])
                source_blocks.extend(["join"] * n_join)

        n_c = len(c["detected"])
        raw_blocks.append(c["raw"])
        det_blocks.append(c["detected"])
        hand_blocks.extend(c["handedness"])
        source_blocks.extend([i] * n_c)

    raw_all = np.concatenate(raw_blocks, axis=0) if raw_blocks else np.zeros((0, 21, 3), dtype=np.float32)
    det_all = np.concatenate(det_blocks, axis=0) if det_blocks else np.zeros((0,), dtype=bool)
    n_total = len(det_all)
    ts_all = np.array([idx * 1000.0 / ref_fps for idx in range(n_total)], dtype=np.float64)

    seq_data = {
        "raw": raw_all,
        "detected": det_all,
        "handedness": hand_blocks,
        "timestamps_ms": ts_all,
        "frame_sources": source_blocks,
        "kept_clips": kept,
        "fps": ref_fps,
        "width": ref_size[0],
        "height": ref_size[1],
    }
    stats = {
        "excluded_mismatch": len(mismatched),
        "mismatched_sample_ids": mismatched,
    }
    return seq_data, stats


def assign_segments_to_clips(
    segments: Sequence[Dict[str, Any]],
    frame_sources: Sequence[Any],
    n_clips: int,
) -> Dict[str, Any]:
    """
    Assign emitted segments to clip indices or mark as garbage.
    Each frame in segment is mapped to its source ('join' or integer clip index).
    Majority wins; ties broken by earlier first appearance in the segment.
    Majority 'join' -> garbage segment.
    """
    clip_segments: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(n_clips)}
    garbage_segments: List[Dict[str, Any]] = []

    assigned_all: List[Dict[str, Any]] = []
    for seg in segments:
        s_idx = int(seg["start_idx"])
        e_idx = int(seg["end_idx"])
        seg_sources = frame_sources[s_idx : e_idx + 1]
        if not seg_sources:
            continue

        # Count frequencies and track first appearance order
        counts: Counter = Counter(seg_sources)
        first_seen: Dict[Any, int] = {}
        for pos, src in enumerate(seg_sources):
            if src not in first_seen:
                first_seen[src] = pos

        # Majority with tie-break by earlier appearance
        best_source = sorted(counts.keys(), key=lambda src: (-counts[src], first_seen[src]))[0]

        seg_with_source = dict(seg, assigned_source=best_source)
        assigned_all.append(seg_with_source)
        if best_source == "join":
            garbage_segments.append(seg_with_source)
        else:
            clip_idx = int(best_source)
            if 0 <= clip_idx < n_clips:
                clip_segments[clip_idx].append(seg_with_source)
            else:
                garbage_segments.append(seg_with_source)

    return {
        "clip_segments": clip_segments,
        "garbage_segments": garbage_segments,
        "all_segments": assigned_all,
    }


def calculate_metrics(
    assigned: Dict[str, Any],
    n_clips: int,
    clip_distances: Optional[Sequence[float]] = None,
    rearm_pose_dist: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute one_rate, miss_rate, multi_rate, garbage_per_clip, order_ok, hand_lost,
    and covered one_rate.
    """
    if n_clips <= 0:
        return {
            "n_clips": 0, "total_segments": 0, "close_reason": {},
            "one_rate": 0.0, "miss_rate": 0.0, "multi_rate": 0.0,
            "garbage_per_clip": 0.0, "order_ok": True, "hand_lost": 0,
            "one_rate_covered": None, "n_clips_covered": 0, "n_one_covered": 0,
        }

    clip_segments = assigned["clip_segments"]
    garbage_segments = assigned["garbage_segments"]
    all_segments = assigned["all_segments"]

    reasons = Counter(seg.get("close_reason", "unknown") for seg in all_segments)
    hand_lost_count = sum(1 for seg in all_segments if seg.get("close_reason") == "hand_lost")

    n_one = sum(1 for i in range(n_clips) if len(clip_segments[i]) == 1)
    n_miss = sum(1 for i in range(n_clips) if len(clip_segments[i]) == 0)
    n_multi = sum(1 for i in range(n_clips) if len(clip_segments[i]) >= 2)

    one_rate = float(n_one) / float(n_clips)
    miss_rate = float(n_miss) / float(n_clips)
    multi_rate = float(n_multi) / float(n_clips)
    garbage_per_clip = float(len(garbage_segments)) / float(n_clips)

    # Check order_ok: sequence of clip assignments for non-garbage segments in emitted order
    valid_assigned_clips = [
        int(seg["assigned_source"])
        for seg in all_segments
        if seg.get("assigned_source") != "join"
    ]

    order_ok = True
    for a, b in zip(valid_assigned_clips, valid_assigned_clips[1:]):
        if b < a:
            order_ok = False
            break

    # Covered one_rate (a pair without a reference shape, distance None, is not covered)
    one_rate_covered = None
    n_covered = 0
    n_one_covered = 0
    if clip_distances is not None and rearm_pose_dist is not None:
        covered_indices = [0]  # First clip is always covered
        for i, dist in enumerate(clip_distances, start=1):
            if dist is not None and dist >= rearm_pose_dist:
                covered_indices.append(i)
        n_covered = len(covered_indices)
        if n_covered > 0:
            n_one_covered = sum(1 for idx in covered_indices if len(clip_segments[idx]) == 1)
            one_rate_covered = float(n_one_covered) / float(n_covered)

    return {
        "n_clips": n_clips,
        "total_segments": len(all_segments),
        "close_reason": dict(reasons),
        "one_rate": one_rate,
        "miss_rate": miss_rate,
        "multi_rate": multi_rate,
        "garbage_per_clip": garbage_per_clip,
        "order_ok": order_ok,
        "hand_lost": hand_lost_count,
        "one_rate_covered": one_rate_covered,
        "n_clips_covered": n_covered,
        "n_one_covered": n_one_covered,
    }


def parse_override(spec: str) -> Tuple[str, str, Any]:
    """'NAME:KEY=JSON' -> (name, key, value); the value is JSON (true / false / a number)."""
    if ":" not in spec or "=" not in spec.split(":", 1)[1]:
        raise ValueError(f"override must be NAME:KEY=JSON, got {spec!r}")
    name, rest = spec.split(":", 1)
    key, raw = rest.split("=", 1)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"override {spec!r}: value is not JSON") from None
    return name, key, value


def apply_overrides(values: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Copy of the config values with the overrides, re-validated by validate_level1_config (unknown key, wrong type
    or range -> ValueError)."""
    new = dict(values)
    new.update(overrides)
    raw = {k: {"value": v, "source": "design", "reason": "override"} for k, v in new.items()}
    validate_level1_config(raw)
    return new


def single_clip_rates(clips: Sequence[Dict[str, Any]], params: Dict[str, Any],
                      min_detected_frames: int) -> Dict[str, Dict[str, Any]]:
    """G6: one fresh segmenter per clip (every frame pushed, flush 1 ms after the last frame as AC-S18); share of the
    clips with exactly one SignSegment, per kind (letter / tone)."""
    out: Dict[str, Dict[str, Any]] = {}
    for kind in ("letter", "tone"):
        n = single = 0
        for clip in (c for c in clips if c["kind"] == kind):
            ts = seg_report.clip_timestamps(len(clip["detected"]), clip["fps"])
            seg = Level1SignSegmenter(params, min_detected_frames)
            evs = []
            for i, t in enumerate(ts):
                det = bool(clip["detected"][i])
                evs += seg.push(float(t), clip["raw"][i] if det else None, clip["handedness"][i] if det else "",
                                clip["width"], clip["height"])
            evs += seg.flush(float(ts[-1]) + 1.0)
            n += 1
            single += int(sum(1 for e in evs if isinstance(e, SignSegment)) == 1)
        out[kind] = {"n": n, "single": single, "rate": (single / n) if n else None}
    return out


def evaluate_gates(results: Dict[str, Any], single: Dict[str, Any], gate_cfg: str, base_cfg: str) -> Dict[str, Any]:
    """Gates G1-G6 (GATE_RULES) on the results of the gate config; G6 against the baseline config. A missing join or
    value fails its gate."""
    th = GATE_THRESHOLDS
    res = results.get(gate_cfg, {})

    def val(chain, join, key):
        return (res.get(chain) or {}).get(join, {}).get(key)

    gates: Dict[str, Dict[str, Any]] = {}
    g1 = {j: val("L", j, "one_rate_covered") for j in ("0", "300")}
    gates["G1"] = {"values": g1, "pass": all(v is not None and v >= th["G1_one_rate_covered_min"] for v in g1.values())}
    g2 = {j: val("L", j, "multi_rate") for j in GATE_JOINS}
    gates["G2"] = {"values": g2, "pass": all(v is not None and v <= th["G2_multi_rate_max"] for v in g2.values())}
    g3 = {f"{c}/{j}": val(c, j, "hand_lost") for c in ("L", "T", "O") for j in GATE_JOINS}
    gates["G3"] = {"values": g3, "pass": all(v == 0 for v in g3.values())}
    g4 = {j: val("L", j, "order_ok") for j in GATE_JOINS}
    gates["G4"] = {"values": g4, "pass": all(v is True for v in g4.values())}
    g5 = {j: val("L", j, "garbage_per_clip") for j in ("300", "600")}
    gates["G5"] = {"values": g5, "pass": all(v is not None and v <= th["G5_garbage_per_clip_max"] for v in g5.values())}
    g6, ok6 = {}, True
    for kind in ("letter", "tone"):
        on = ((single.get(gate_cfg) or {}).get(kind) or {}).get("rate")
        off = ((single.get(base_cfg) or {}).get(kind) or {}).get("rate")
        g6[kind] = {"gate": on, "baseline": off}
        ok6 = ok6 and on is not None and off is not None and on >= off - th["G6_single_drop_max"]
    gates["G6"] = {"values": g6, "pass": bool(ok6)}
    for k in gates:
        gates[k] = {"rule": GATE_RULES[k], **gates[k]}
    return {"gate_config": gate_cfg, "baseline_config": base_cfg, "thresholds": dict(th), "gates": gates,
            "all_pass": all(g["pass"] for g in gates.values())}


def whole_clip_segment(clip: Dict[str, Any]) -> SignSegment:
    """The whole (untrimmed) train clip as one SignSegment: the input of the model at training time."""
    ts = seg_report.clip_timestamps(len(clip["detected"]), clip["fps"])
    return SignSegment(seq=0, raw_landmarks=np.asarray(clip["raw"], dtype=np.float32),
                       detected=np.asarray(clip["detected"], dtype=bool),
                       handedness=np.asarray(clip["handedness"], dtype=object).astype(str),
                       timestamps_ms=np.asarray(ts, dtype=np.float64), frame_width=int(clip["width"]),
                       frame_height=int(clip["height"]), t_start_ms=float(ts[0]), t_end_ms=float(ts[-1]),
                       t_emit_ms=float(ts[-1]), close_reason="end_of_stream")


def write_rules_config(config_path: str, rearm_json: str) -> Dict[str, Any]:
    """pose_change_rules -> true (source 'design', reason naming the R3 JSON and its commit), only when the R3 JSON
    is committed and clean (A2b helper), was generated from clean code and all its gates passed; only this key
    changes. RuntimeError otherwise (config untouched)."""
    with open(rearm_json, encoding="utf-8") as f:
        rep = json.load(f)
    gates = rep.get("gates") or {}
    if gates.get("all_pass") is not True:
        raise RuntimeError(f"{rearm_json}: gates G1-G6 did not all pass; pose_change_rules stays false")
    if (rep.get("generated_by") or {}).get("code_dirty") is not False:
        raise RuntimeError(f"{rearm_json}: generated with uncommitted code (code_dirty not false)")
    rel_json, commit = seg_report.committed_evidence_ref(rearm_json)
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    old = dict(cfg["pose_change_rules"])
    cfg["pose_change_rules"] = {
        "value": True, "source": "design",
        "reason": f"pose re-arm rules on: gates G1-G6 of plan 15 lần sửa 3 section 5 (step R3) passed for config "
                  f"'{gates.get('gate_config')}' in {rel_json}@{commit} ({NOTE})"}
    validate_level1_config(cfg)
    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"pose_change_rules": {"old": old, "new": cfg["pose_change_rules"]}}


# ----------------------------------------------------------------------------------------------------------------------
# Step D3 (plan 15 lần sửa 4 §4 #4, §5 D3, §5.1): --decoder — the label decoder of rearm_mode 'classifier'
# ----------------------------------------------------------------------------------------------------------------------
EXPLORATORY_PARAMS_NOTE = ("tham số D chọn sau thăm dò planner trên cùng chuỗi L — gate là kiểm logic (cls_window_ms, cls_conf, "
                           "cls_stable_ms chosen after the planner's exploratory measure on the same L chains; the gates "
                           "check logic, not an independent result)")
# pre-registered gates of plan 15 lần sửa 4 §5.1 (thresholds of lần sửa 3 §5 kept; never changed after a result)
DECODER_GATE_RULES = {
    "G1": "chain L, joins 0 and 300 ms: one_rate >= 0.90 (gate config; full one_rate, 'covered' dropped)",
    "G2": "chain L, every join: multi_rate <= 0.05",
    "G3": "every chain (L, T, O), every join: emissions that needed a lost hand == 0",
    "G4": "chain L, every join: order_ok",
    "G5": "chain L, joins 300 and 600 ms: garbage_per_clip <= 0.05 (strict garbage, definitions.garbage)",
    "G6": "single clips: one_rate(gate) >= one_rate(baseline) - 0.02, letters and tones",
}
DECODER_DEFINITIONS = {
    "segment": "classifier config: one 'append' emission of Level1LabelDecoder; a 'replace' emission is not a new "
               "segment (counted in n_replace): it moves the last emission to its frame and label, as "
               "docs/plans/15-lan-sua-4-do/analyze5.py decode_r; motion_pose config: one SignSegment",
    "clip_of_emission": "the source clip of the frame that emitted (classifier) / of the frame at t_emit (motion_pose, "
                        "strict block); a frame of an interpolated join has source 'join'",
    "expected_label": "model label of the whole untrimmed train clip (the training input)",
    "garbage": "strict (C2): an emission at a 'join' frame OR whose label != expected label of the clip of the "
               "emission; stricter than R0, which counted segments made mostly of join frames",
    "one_rate": "share of clips with exactly one non-garbage emission (no 'covered' filter)",
    "hand_lost": "classifier config: 'append' emissions after a run of >= hand_lost_ms without a hand since the "
                 "previous emission (an emission that needed the hand to be withdrawn)",
    "token_error_rate": "Levenshtein distance between the emitted labels and the expected labels (consecutive equal "
                        "expected labels collapsed: the decoder never repeats a label without a lost hand) / number of "
                        "expected labels",
    "single_clip": "every hauuto clip with >= min_detected_frames hand frames, untrimmed; classifier: one fresh window "
                   "+ decoder per clip, rate = share with exactly one emission; motion_pose: one fresh segmenter, flush "
                   "1 ms after the last frame, rate = share with exactly one SignSegment (as R3)",
    "qipedc_g7": "report only: 46 QIPEDC alphabet clips (one signer, not in train); share of clips where the config emits "
                 "the model label of the whole clip (classifier: any emission; motion_pose: any classified SignSegment)",
}


def decode_chain(seq_data: Dict[str, Any], params: Dict[str, Any], classify, min_detected_frames: int) -> Dict[str, Any]:
    """WindowBuffer + Level1LabelDecoder over a stream, exactly as level1_demo.py headless in rearm_mode 'classifier'
    (one window classification per hand frame, decoder fed in frame order). classify(segment) -> result dict of
    Level1Classifier.classify. Returns final emissions [(frame_index, label)] (a 'replace' moves the last one), the
    raw emissions, n_replace, n_append_after_lost, n_windows. With cls_motion_gate true (plan 15 lần sửa 12 G1) a
    Level1SignSegmenter runs on the same frames, as in the app, and its state 'moving' is passed to the decoder;
    n_gated = hand frames ended by the gate (0 without the gate)."""
    from src.inference.level1_segmenter import Level1LabelDecoder, WindowBuffer
    window = WindowBuffer(params["cls_window_ms"], min_detected_frames)
    decoder = Level1LabelDecoder(params)
    motion = Level1SignSegmenter(params, min_detected_frames) if decoder.motion_gate else None
    ts_all, det, raw, hand = seq_data["timestamps_ms"], seq_data["detected"], seq_data["raw"], seq_data["handedness"]
    final: List[Tuple[int, str]] = []
    raw_emits: List[Dict[str, Any]] = []
    n_replace = n_lost = n_windows = 0
    last_hand: Optional[float] = None
    lost_since_emit = False
    for i in range(len(det)):
        ts = float(ts_all[i])
        has = bool(det[i])
        window.push(ts, raw[i] if has else None, str(hand[i]) if has else "", seq_data["width"], seq_data["height"])
        moving = False
        if motion is not None:
            motion.push(ts, raw[i] if has else None, str(hand[i]) if has else "", seq_data["width"],
                        seq_data["height"])
            moving = motion.state == "moving"
        result = None
        if has:
            last_hand = ts
            seg = window.segment(ts)
            if seg is not None:
                n_windows += 1
                result = classify(seg)
        elif last_hand is not None and ts - last_hand >= params["hand_lost_ms"]:
            lost_since_emit = True
        emit = decoder.push(ts, has, result, moving=moving)
        if emit is None:
            continue
        raw_emits.append({"index": i, "label": emit.prediction, "action": emit.action,
                          "confidence": emit.confidence})
        if emit.action == "replace" and final:
            final[-1] = (i, emit.prediction)
            n_replace += 1
        else:
            final.append((i, emit.prediction))
            n_lost += int(lost_since_emit)
        lost_since_emit = False
    return {"final": final, "emits": raw_emits, "n_replace": n_replace, "n_append_after_lost": n_lost,
            "n_windows": n_windows, "n_gated": decoder.n_gated}


def levenshtein(a: Sequence[Any], b: Sequence[Any]) -> int:
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[-1]


def strict_chain_metrics(emissions: Sequence[Tuple[int, Optional[str]]], frame_sources: Sequence[Any],
                         expected: Sequence[Optional[str]]) -> Dict[str, Any]:
    """Metrics of plan 15 lần sửa 4 §5.1 for one chain: emissions [(frame_index, label)] in order, expected label per
    clip. Garbage = emission at a 'join' frame or label != expected label of its clip (definitions.garbage)."""
    n = len(expected)
    per = Counter()
    order: List[int] = []
    n_garbage = 0
    for idx, label in emissions:
        src = frame_sources[idx]
        if src == "join" or label is None or label != expected[int(src)]:
            n_garbage += 1
            continue
        per[int(src)] += 1
        order.append(int(src))
    exp_c = [lab for k, lab in enumerate(expected) if k == 0 or lab != expected[k - 1]]
    return {
        "n_clips": n,
        "n_emissions": len(emissions),
        "n_one": sum(1 for k in range(n) if per[k] == 1),
        "n_miss": sum(1 for k in range(n) if per[k] == 0),
        "n_multi": sum(1 for k in range(n) if per[k] >= 2),
        "n_garbage": n_garbage,
        "order_ok": all(b >= a for a, b in zip(order, order[1:])),
        "edit_distance": levenshtein([lab for _, lab in emissions], exp_c),
        "n_expected_collapsed": len(exp_c),
    }


def _sum_strict(per_seq: Sequence[Dict[str, Any]], extra_keys: Sequence[str] = ()) -> Dict[str, Any]:
    tot = Counter()
    for m in per_seq:
        for k in ("n_clips", "n_emissions", "n_one", "n_miss", "n_multi", "n_garbage", "edit_distance",
                  "n_expected_collapsed", *extra_keys):
            tot[k] += m.get(k, 0)
    n = tot["n_clips"]
    out = {k: int(v) for k, v in tot.items()}
    out.update({
        "one_rate": tot["n_one"] / n if n else 0.0,
        "miss_rate": tot["n_miss"] / n if n else 0.0,
        "multi_rate": tot["n_multi"] / n if n else 0.0,
        "garbage_per_clip": tot["n_garbage"] / n if n else 0.0,
        "order_ok": all(m["order_ok"] for m in per_seq),
        "token_error_rate": (tot["edit_distance"] / tot["n_expected_collapsed"]) if tot["n_expected_collapsed"] else None,
    })
    return out


def evaluate_decoder_gates(results: Dict[str, Any], single: Dict[str, Any], gate_cfg: str,
                           base_cfg: str) -> Dict[str, Any]:
    """Gates of plan 15 lần sửa 4 §5.1 on the results of the gate config (classifier), G6 against the baseline. A
    missing join or value fails its gate."""
    th = GATE_THRESHOLDS
    res = results.get(gate_cfg, {})

    def val(chain, join, key):
        return (res.get(chain) or {}).get(join, {}).get(key)

    gates: Dict[str, Dict[str, Any]] = {}
    g1 = {j: val("L", j, "one_rate") for j in ("0", "300")}
    gates["G1"] = {"values": g1, "pass": all(v is not None and v >= th["G1_one_rate_covered_min"] for v in g1.values())}
    g2 = {j: val("L", j, "multi_rate") for j in GATE_JOINS}
    gates["G2"] = {"values": g2, "pass": all(v is not None and v <= th["G2_multi_rate_max"] for v in g2.values())}
    g3 = {f"{c}/{j}": val(c, j, "hand_lost") for c in ("L", "T", "O") for j in GATE_JOINS}
    gates["G3"] = {"values": g3, "pass": all(v == 0 for v in g3.values())}
    g4 = {j: val("L", j, "order_ok") for j in GATE_JOINS}
    gates["G4"] = {"values": g4, "pass": all(v is True for v in g4.values())}
    g5 = {j: val("L", j, "garbage_per_clip") for j in ("300", "600")}
    gates["G5"] = {"values": g5, "pass": all(v is not None and v <= th["G5_garbage_per_clip_max"] for v in g5.values())}
    g6, ok6 = {}, True
    for kind in ("letter", "tone"):
        on = ((single.get(gate_cfg) or {}).get(kind) or {}).get("rate")
        off = ((single.get(base_cfg) or {}).get(kind) or {}).get("rate")
        g6[kind] = {"gate": on, "baseline": off, "pass": on is not None and off is not None
                    and on >= off - th["G6_single_drop_max"]}
        ok6 = ok6 and g6[kind]["pass"]
    gates["G6"] = {"values": g6, "pass": bool(ok6)}
    for k in gates:
        gates[k] = {"rule": DECODER_GATE_RULES[k], **gates[k]}
    failed = [k for k, g in gates.items() if not g["pass"]]
    only_g6_tone = failed == ["G6"] and g6["letter"]["pass"] and not g6["tone"]["pass"]
    return {"gate_config": gate_cfg, "baseline_config": base_cfg, "thresholds": dict(th), "gates": gates,
            "all_pass": not failed, "failed": failed, "only_g6_tone_failed": only_g6_tone,
            "stop_point": (None if not failed else
                           "lần sửa 4 §7 item 2: only G6 tones failed -> STOP, the user chooses (a) or (b)" if only_g6_tone
                           else "lần sửa 4 §7 item 1: a gate failed -> STOP, config keeps rearm_mode 'motion_pose'")}


def single_clip_rates_decoder(clips: Sequence[Dict[str, Any]], params: Dict[str, Any], classify,
                              min_detected_frames: int, whole_label: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """G6 for a classifier config: one fresh window + decoder per untrimmed clip; rate = share with exactly one
    emission (no label check, as the segmenter rate); one_and_label = exactly one emission with the whole-clip label
    (report only)."""
    out: Dict[str, Dict[str, Any]] = {}
    for kind in ("letter", "tone"):
        n = single = labelled = zero = multi = 0
        for clip in (c for c in clips if c["kind"] == kind):
            sd = {"raw": clip["raw"], "detected": clip["detected"], "handedness": clip["handedness"],
                  "timestamps_ms": seg_report.clip_timestamps(len(clip["detected"]), clip["fps"]),
                  "width": clip["width"], "height": clip["height"]}
            fin = decode_chain(sd, params, classify, min_detected_frames)["final"]
            n += 1
            single += int(len(fin) == 1)
            zero += int(len(fin) == 0)
            multi += int(len(fin) >= 2)
            labelled += int(len(fin) == 1 and fin[0][1] == whole_label[clip["sample_id"]])
        out[kind] = {"n": n, "single": single, "rate": (single / n) if n else None, "zero": zero, "multi": multi,
                     "one_and_label_rate": (labelled / n) if n else None}
    return out


def load_qipedc_clips(manifest_path: str, min_detected_frames: int) -> Dict[str, Any]:
    """QIPEDC rows of the manifest (G7, report only): clips with >= min_detected_frames hand frames."""
    with open(manifest_path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source"] == "qipedc"]
    base = os.path.dirname(manifest_path)
    clips, too_few = [], []
    for r in sorted(rows, key=lambda r: r["sample_id"]):
        with np.load(os.path.join(base, r["landmark_path"])) as z:
            det = np.asarray(z["detected_mask"], dtype=bool)
            clip = {"sample_id": r["sample_id"], "symbol": r["symbol"], "kind": class_kind(r["symbol"]),
                    "raw": np.asarray(z["raw_landmarks"], dtype=np.float32), "detected": det,
                    "handedness": [str(h) for h in z["handedness_label"]], "width": int(r["width"]),
                    "height": int(r["height"]), "fps": float(r["fps"])}
        if int(det.sum()) < min_detected_frames:
            too_few.append(r["sample_id"])
        else:
            clips.append(clip)
    return {"n_manifest": len(rows), "clips": clips, "too_few_frames": too_few}


def qipedc_report(manifest_path: str, configs: Dict[str, Dict[str, Any]], classifier,
                  min_detected_frames: int) -> Dict[str, Any]:
    """G7 (report only, plan 15 lần sửa 4 §5.1): per config, share of QIPEDC clips (untrimmed) where the config emits
    the model label of the whole clip, and where it emits the manifest symbol."""
    q = load_qipedc_clips(manifest_path, min_detected_frames)
    out: Dict[str, Any] = {"n_manifest": q["n_manifest"], "n_clips": len(q["clips"]),
                           "too_few_frames": q["too_few_frames"], "definition": DECODER_DEFINITIONS["qipedc_g7"],
                           "note": "report only, not a gate: one signer, detection rate about 0.5; the planner saw half "
                                   "of this measure (the bare decoder) before choosing the parameters",
                           "configs": {}}
    for name, p in configs.items():
        top_k = int(p["top_k"])
        n_whole_ok = n_symbol = n_whole_is_symbol = n_emits = 0
        for clip in q["clips"]:
            whole_seg = whole_clip_segment(clip)
            r = classifier.classify(whole_seg, top_k)
            wl = r.get("prediction") if r.get("status") == "ok" else None
            n_whole_is_symbol += int(wl == clip["symbol"])
            ts = seg_report.clip_timestamps(len(clip["detected"]), clip["fps"])
            if p["rearm_mode"] == "classifier":
                sd = {"raw": clip["raw"], "detected": clip["detected"], "handedness": clip["handedness"],
                      "timestamps_ms": ts, "width": clip["width"], "height": clip["height"]}
                labels = [lab for _, lab in decode_chain(sd, p, lambda sg: classifier.classify(sg, top_k),
                                                         min_detected_frames)["final"]]
            else:
                seg = Level1SignSegmenter(p, min_detected_frames)
                evs = []
                for i, t in enumerate(ts):
                    det = bool(clip["detected"][i])
                    evs += seg.push(float(t), clip["raw"][i] if det else None,
                                    clip["handedness"][i] if det else "", clip["width"], clip["height"])
                evs += seg.flush(float(ts[-1]) + 1.0)
                labels = []
                for e in evs:
                    if isinstance(e, SignSegment):
                        rr = classifier.classify(e, top_k)
                        labels.append(rr.get("prediction") if rr.get("status") == "ok" else None)
            n_emits += len(labels)
            n_whole_ok += int(wl is not None and wl in labels)
            n_symbol += int(clip["symbol"] in labels)
        n = len(q["clips"])
        out["configs"][name] = {"rearm_mode": p["rearm_mode"], "n_emissions": n_emits,
                                "whole_label_emitted": n_whole_ok, "whole_label_emitted_rate": (n_whole_ok / n) if n else None,
                                "symbol_emitted": n_symbol, "symbol_emitted_rate": (n_symbol / n) if n else None,
                                "whole_label_is_symbol": n_whole_is_symbol}
    return out


def write_mode_config(config_path: str, rearm_json: str) -> Dict[str, Any]:
    """rearm_mode -> 'classifier' (source 'design', reason naming the D4 JSON and its commit), only when the D4 JSON
    is committed and clean (helper committed_evidence_ref), is a --decoder report generated from clean code, its gate
    config is a classifier config and all its gates passed; only this key changes. RuntimeError otherwise (config
    untouched)."""
    with open(rearm_json, encoding="utf-8") as f:
        rep = json.load(f)
    gates = rep.get("gates") or {}
    if rep.get("mode") != "decoder":
        raise RuntimeError(f"{rearm_json}: not a --decoder report (step D4)")
    if gates.get("all_pass") is not True:
        raise RuntimeError(f"{rearm_json}: gates G1-G6 did not all pass; rearm_mode stays 'motion_pose'")
    if (rep.get("generated_by") or {}).get("code_dirty") is not False:
        raise RuntimeError(f"{rearm_json}: generated with uncommitted code (code_dirty not false)")
    gate_cfg = gates.get("gate_config")
    if (rep.get("rearm_modes") or {}).get(gate_cfg) != "classifier":
        raise RuntimeError(f"{rearm_json}: gate config {gate_cfg!r} is not rearm_mode 'classifier'")
    rel_json, commit = seg_report.committed_evidence_ref(rearm_json)
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    old = dict(cfg["rearm_mode"])
    cfg["rearm_mode"] = {
        "value": "classifier", "source": "design",
        "reason": f"label decoder on: gates G1-G6 of plan 15 lần sửa 4 section 5.1 (step D4) passed for config "
                  f"'{gate_cfg}' in {rel_json}@{commit} ({NOTE}; decoder parameters chosen after an exploratory "
                  f"measure on the same chains)"}
    validate_level1_config(cfg)
    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"rearm_mode": {"old": old, "new": cfg["rearm_mode"]}}


# the user's decision after step D4 (plan 15 lần sửa 4 §7 item 2, choice (a), recorded in docs/plans/15-progress.md D4);
# written into the demo config by write_demo_config (plan 15 lần sửa 5 §3.1), never typed into a config by hand
DEMO_DECISION = {"choice": "(a) classifier", "decided": "2026-10-05", "recorded_in": "docs/plans/15-progress.md (D4)",
                 "plans": "docs/plans/15-lan-sua-4.md §7 item 2; docs/plans/15-lan-sua-5.md"}


def write_demo_config(out_path: str, rearm_json: str) -> Dict[str, Any]:
    """Demo config (plan 15 lần sửa 5 §3.1): the base config with rearm_mode 'classifier' + the markers _about and
    _user_decision, only when the D4 JSON is committed and clean, is a --decoder report from clean code, exactly G6
    tones failed (lần sửa 4 §7 item 2: gates.failed == ['G6'], letters passed, tones failed) and its gate config is the
    base config as it is now (same sha256, committed and clean) with the single override rearm_mode 'classifier'. The
    base config is never written; RuntimeError otherwise (out_path not written)."""
    with open(rearm_json, encoding="utf-8") as f:
        rep = json.load(f)
    gates = rep.get("gates") or {}
    if rep.get("mode") != "decoder":
        raise RuntimeError(f"{rearm_json}: not a --decoder report (step D4)")
    if (rep.get("generated_by") or {}).get("code_dirty") is not False:
        raise RuntimeError(f"{rearm_json}: generated with uncommitted code (code_dirty not false)")
    if gates.get("all_pass") is True:
        raise RuntimeError(f"{rearm_json}: gates G1-G6 all passed; switch the default config with --write-mode-config")
    g6 = ((gates.get("gates") or {}).get("G6") or {}).get("values") or {}
    letter, tone = g6.get("letter") or {}, g6.get("tone") or {}
    if gates.get("failed") != ["G6"] or gates.get("only_g6_tone_failed") is not True \
            or letter.get("pass") is not True or tone.get("pass") is not False:
        raise RuntimeError(f"{rearm_json}: not the case of lần sửa 4 §7 item 2 (only G6 tones failed): "
                           f"failed {gates.get('failed')!r}")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               for v in (tone.get("gate"), tone.get("baseline"), letter.get("gate"), letter.get("baseline"))):
        raise RuntimeError(f"{rearm_json}: G6 values missing")
    gate_cfg = gates.get("gate_config")
    if (rep.get("rearm_modes") or {}).get(gate_cfg) != "classifier":
        raise RuntimeError(f"{rearm_json}: gate config {gate_cfg!r} is not rearm_mode 'classifier'")
    measured = (rep.get("configs") or {}).get(gate_cfg) or {}
    if measured.get("overrides") != {"rearm_mode": "classifier"}:
        raise RuntimeError(f"{rearm_json}: gate config {gate_cfg!r} must be the base config with the single override "
                           f"rearm_mode 'classifier', got {measured.get('overrides')!r}")
    base_path = measured.get("path")
    if not isinstance(base_path, str) or not base_path:
        raise RuntimeError(f"{rearm_json}: gate config {gate_cfg!r} has no path")
    base_full = os.path.abspath(base_path if os.path.isabs(base_path) else os.path.join(ROOT, base_path))
    out_full = os.path.abspath(out_path)
    if os.path.realpath(out_full) == os.path.realpath(base_full):
        raise RuntimeError(f"{out_path}: is the base config itself; the demo config must be another file")
    rel_json, commit = seg_report.committed_evidence_ref(rearm_json)
    rel_base, base_commit = seg_report.committed_evidence_ref(base_full)
    base_sha = sha256_file(base_full)
    if base_sha != measured.get("sha256"):
        raise RuntimeError(f"{rel_base}: sha256 {base_sha} is not the config measured in {rel_json}@{commit} "
                           f"({measured.get('sha256')}); run step D4 again for this config")
    with open(base_full, encoding="utf-8") as f:
        base = json.load(f)
    evidence = f"{rel_json}@{commit}"
    drop = (gates.get("thresholds") or {}).get("G6_single_drop_max", GATE_THRESHOLDS["G6_single_drop_max"])
    rule = f"on >= off - {drop}"
    decision = {**DEMO_DECISION, "gate_failed": "G6 tone",
                "g6_tone": {"on": tone.get("gate"), "off": tone.get("baseline"), "rule": rule},
                "g6_letter": {"on": letter.get("gate"), "off": letter.get("baseline")},
                "evidence": evidence,
                "note": f"not a gate pass: gate G6 tones failed; tones: keys 1-5; gates checked on {NOTE}"}
    about = (f"Demo config (plan 15 lần sửa 5): generated by scripts/level1_rearm_check.py --write-demo-config from "
             f"{rel_base} (sha256 {base_sha}, commit {base_commit}) = config '{gate_cfg}' measured in {evidence}; only "
             f"rearm_mode differs (+ _user_decision); do not edit by hand; the default config stays motion_pose. "
             f"Read by level1_demo.py --config like the default config.")
    new_mode = {
        "value": "classifier", "source": "design",
        "reason": f"user decision {DEMO_DECISION['choice']} {DEMO_DECISION['decided']} after step D4: classifier "
                  f"re-arm enabled for the demo although gate G6 tones FAILED (on {tone.get('gate'):.4f} vs off "
                  f"{tone.get('baseline'):.4f}, rule {rule}) in {evidence}; not a gate pass; tones: keys 1-5"}
    demo: Dict[str, Any] = {"_about": about, "_user_decision": decision}
    for k, v in base.items():
        if k != "_about":
            demo[k] = new_mode if k == "rearm_mode" else v
    validate_level1_config(demo)
    with open(out_full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(demo, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"out": seg_report.rel(out_full), "rearm_mode": {"old": base["rearm_mode"], "new": new_mode},
            "base": {"path": rel_base, "sha256": base_sha, "commit": base_commit}}


# plan 15 lần sửa 7 §2 (T1-T3), user decision "File config mới" (2026-10-05): the values of lần sửa 7 go into a NEW
# demo config written by write_rev7_config (the demo config of lần sửa 5 stays as it is, its test AC-W3 pins it); never
# typed into a config by hand. key -> (value, reason); the optional decoder keys are inserted after cls_stable_ms.
REV7_DEMO_CONFIG = os.path.join("configs", "level1_demo_classifier_rev7.json")
REV7_BASE_CONFIG = os.path.join("configs", "level1_demo_classifier.json")
REV7_DECISION = {"choice": "File config mới", "decided": "2026-10-05",
                 "recorded_in": "docs/plans/15-progress.md (lần sửa 7)", "plans": "docs/plans/15-lan-sua-7.md §2",
                 "note": "values chosen by the planner after the U3 webcam session (trace not committed); not checked "
                         "on committed evidence, not a gate"}
REV7_VALUES = {
    "cls_window_ms": (
        700.0, "plan 15 lần sửa 7 T2: shorter sliding window so the previous sign leaves the window sooner when the "
               "signer changes sign without lowering the hand; value chosen by the planner after the U3 webcam session "
               "(trace not committed); not an independent calibration"),
    "cls_conf_tone": (
        0.78, "plan 15 lần sửa 7 T1: own minimum top-1 probability of a window for the 5 tone marks (moving signs "
              "whose windows seldom reached cls_conf in the U3 webcam session); value chosen by the planner from that "
              "session (trace not committed); not an independent calibration; letters keep cls_conf"),
    "cls_stable_ms_tone": (
        200.0, "plan 15 lần sửa 7 T1: stable time of the 5 tone marks before they are emitted; value chosen by the "
               "planner after the U3 webcam session; not an independent calibration; letters keep cls_stable_ms"),
    "dropout_tolerance_ms": (
        60.0, "plan 15 lần sửa 7 T2: one-frame dropout debounce of the label decoder (a single window below its "
              "threshold does not restart a run when the next window comes back to the same label within this time); "
              "about one webcam frame; design"),
    "word_gap_ms": (
        2500.0, "plan 15 lần sửa 7 T3: only a clear rest of the hand ends a word, so a short loss of the hand does not "
                "insert a space; value chosen by the planner; must be >= hand_lost_ms; level1_demo.py --no-auto-space "
                "turns the automatic space off"),
}


def write_rev7_config(out_path: str, base_path: str = REV7_BASE_CONFIG) -> Dict[str, Any]:
    """Demo config of plan 15 lần sửa 7 (user decision "File config mới"): the base demo config (committed and clean,
    rearm_mode 'classifier') with the values of REV7_VALUES (keys already in the base are replaced in place, the others
    inserted after cls_stable_ms) + the markers _about and _rev7_decision; every other key unchanged, no clock, so the
    same base gives the same bytes. The base is never written; RuntimeError otherwise (out_path not written)."""
    base_full = os.path.abspath(base_path if os.path.isabs(base_path) else os.path.join(ROOT, base_path))
    out_full = os.path.abspath(out_path)
    if os.path.realpath(out_full) == os.path.realpath(base_full):
        raise RuntimeError(f"{out_path}: is the base config itself; the lần sửa 7 config must be another file")
    rel_base, base_commit = seg_report.committed_evidence_ref(base_full)
    base_sha = sha256_file(base_full)
    with open(base_full, encoding="utf-8") as f:
        base = json.load(f)
    if validate_level1_config(base)["rearm_mode"] != "classifier":
        raise RuntimeError(f"{rel_base}: rearm_mode is not 'classifier' (the base must be the demo config)")
    about = (f"Demo config (plan 15 lần sửa 7): generated by scripts/level1_rearm_check.py --write-rev7-config from "
             f"{rel_base} (sha256 {base_sha}, commit {base_commit}) = that demo config with the values of "
             f"docs/plans/15-lan-sua-7.md §2 ({', '.join(REV7_VALUES)}) + _rev7_decision; do not edit by hand; "
             f"{rel_base} and the default config are unchanged. Read by level1_demo.py --config like the other "
             f"configs.")
    entries = {k: {"value": v, "source": "design", "reason": reason} for k, (v, reason) in REV7_VALUES.items()}
    new: Dict[str, Any] = {"_about": about, "_rev7_decision": dict(REV7_DECISION)}
    for k, v in base.items():
        if k == "_about":
            continue
        new[k] = entries[k] if k in entries else v
        if k == "cls_stable_ms":
            for extra in (e for e in entries if e not in base):
                new[extra] = entries[extra]
    for extra in (e for e in entries if e not in new):
        new[extra] = entries[extra]
    validate_level1_config(new)
    with open(out_full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"out": seg_report.rel(out_full), "base": {"path": rel_base, "sha256": base_sha, "commit": base_commit},
            "changed": {k: {"old": base.get(k), "new": entries[k]} for k in entries}}


def run_segmenter_on_stream(
    seq_data: Dict[str, Any],
    params: Dict[str, Any],
    min_detected_frames: int,
) -> List[Dict[str, Any]]:
    """
    Push each frame of concatenated stream into Level1SignSegmenter, flush at the end.
    Returns list of segment dicts with start_idx, end_idx, close_reason, t_start_ms, t_end_ms.
    """
    raw_all = seq_data["raw"]
    det_all = seq_data["detected"]
    hand_all = seq_data["handedness"]
    ts_all = seq_data["timestamps_ms"]
    width = seq_data["width"]
    height = seq_data["height"]
    n_frames = len(det_all)

    seg = Level1SignSegmenter(params, min_detected_frames)
    events = []

    for idx in range(n_frames):
        ts = float(ts_all[idx])
        lms = raw_all[idx] if bool(det_all[idx]) else None
        h = str(hand_all[idx]) if bool(det_all[idx]) else ""
        ev = seg.push(ts, lms, h, width, height)
        if ev:
            events.extend(ev)

    if n_frames > 0:
        dt = 1000.0 / float(seq_data["fps"]) if seq_data["fps"] > 0 else 40.0
        flush_ts = float(ts_all[-1]) + dt
        ev = seg.flush(flush_ts)
        if ev:
            events.extend(ev)

    out_segments: List[Dict[str, Any]] = []
    for ev in events:
        if isinstance(ev, SignSegment):
            # Map t_start_ms and t_end_ms to frame indices
            # Find frames in stream where ts_all falls within [t_start_ms - 1e-3, t_end_ms + 1e-3]
            in_range = np.where((ts_all >= ev.t_start_ms - 1e-3) & (ts_all <= ev.t_end_ms + 1e-3))[0]
            start_idx = int(in_range[0]) if len(in_range) > 0 else 0
            end_idx = int(in_range[-1]) if len(in_range) > 0 else 0
            out_segments.append({
                "start_idx": start_idx,
                "end_idx": end_idx,
                "t_start_ms": float(ev.t_start_ms),
                "t_end_ms": float(ev.t_end_ms),
                "t_emit_ms": float(ev.t_emit_ms),
                "close_reason": str(ev.close_reason),
                "frames": int(ev.n_frames),
                "detected_frames": int(ev.n_detected),
                "raw_segment": ev,
            })

    return out_segments


def load_and_prepare_manifest_clips(
    manifest_path: str,
    min_detected_frames: int,
    hand_lost_ms: float = 200.0,
) -> Dict[str, Any]:
    """
    Read hauuto clips from manifest, filter by min_detected_frames,
    then prepare_clip (trim no-hand, exclude internal hand lost).
    """
    with open(manifest_path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source"] == "hauuto"]

    base = os.path.dirname(manifest_path)
    prepared_clips: List[Dict[str, Any]] = []
    excluded_min_det: List[str] = []
    excluded_internal_lost: List[str] = []
    excluded_no_hand: List[str] = []

    for r in sorted(rows, key=lambda r: r["sample_id"]):
        npz_path = os.path.join(base, r["landmark_path"])
        with np.load(npz_path) as z:
            raw = np.asarray(z["raw_landmarks"], dtype=np.float32)
            det = np.asarray(z["detected_mask"], dtype=bool)
            hand = [str(h) for h in z["handedness_label"]]

        kind = class_kind(r["symbol"])
        if kind is None:
            continue

        n_det = int(det.sum())
        if n_det < min_detected_frames:
            excluded_min_det.append(r["sample_id"])
            continue

        raw_clip = {
            "sample_id": r["sample_id"], "symbol": r["symbol"], "kind": kind,
            "signer_id": r["signer_id"], "raw": raw, "detected": det,
            "handedness": hand, "width": int(r["width"]), "height": int(r["height"]),
            "fps": float(r["fps"]),
        }

        prep, reason = prepare_clip(raw_clip, hand_lost_ms=hand_lost_ms)
        if prep is None:
            if reason == "internal_hand_lost":
                excluded_internal_lost.append(r["sample_id"])
            else:
                excluded_no_hand.append(r["sample_id"])
        else:
            prepared_clips.append(prep)

    return {
        "n_manifest_hauuto": len(rows),
        "clips": prepared_clips,
        "excluded": {
            "min_detected_frames": len(excluded_min_det),
            "internal_hand_lost": len(excluded_internal_lost),
            "no_hand_frames": len(excluded_no_hand),
            "internal_hand_lost_sample_ids": excluded_internal_lost,
            "min_detected_frames_sample_ids": excluded_min_det,
            "no_hand_frames_sample_ids": excluded_no_hand,
        },
    }


def build_candidate_sequences(
    clips: Sequence[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group prepared clips into candidate sequences:
    - 'L' (letters): per (signer, session), all letter classes sorted by symbol, 1 clip per class (smallest sample_id)
    - 'T' (tone pairs): per (signer, session) x tone, [clip 'a', clip tone]
    - 'O' (repetition pairs): per (signer, session), for 'o' and 'e' if >= 2 clips: [clip 1, clip 2]
    """
    by_signer_session = defaultdict(list)
    for c in clips:
        signer = c["signer_id"]
        session = c["sample_id"].rsplit("_", 2)[1]
        by_signer_session[(signer, session)].append(c)

    sequences: Dict[str, List[Dict[str, Any]]] = {"L": [], "T": [], "O": []}

    for (signer, session), clist in sorted(by_signer_session.items()):
        # 1. L sequences: letter classes sorted by symbol
        letters = [c for c in clist if c["kind"] == "letter"]
        best_per_sym = {}
        for c in letters:
            sym = c["symbol"]
            if sym not in best_per_sym or c["sample_id"] < best_per_sym[sym]["sample_id"]:
                best_per_sym[sym] = c
        sorted_syms = sorted(best_per_sym.keys())
        l_clips = [best_per_sym[s] for s in sorted_syms]
        if l_clips:
            sequences["L"].append({
                "seq_id": f"L_{signer}_{session}",
                "signer_id": signer,
                "session": session,
                "type": "L",
                "clips": l_clips,
            })

        # 2. T sequences: [clip 'a', clip tone]
        clip_a = best_per_sym.get("a")
        if clip_a is not None:
            tones = [c for c in clist if c["kind"] == "tone"]
            best_per_tone = {}
            for c in tones:
                sym = c["symbol"]
                if sym not in best_per_tone or c["sample_id"] < best_per_tone[sym]["sample_id"]:
                    best_per_tone[sym] = c
            for t_sym in sorted(best_per_tone.keys()):
                sequences["T"].append({
                    "seq_id": f"T_{signer}_{session}_{t_sym}",
                    "signer_id": signer,
                    "session": session,
                    "type": "T",
                    "clips": [clip_a, best_per_tone[t_sym]],
                })

        # 3. O sequences: repeated 'o' and 'e'
        for rep_sym in ("o", "e"):
            reps = [c for c in clist if c["symbol"] == rep_sym]
            reps_sorted = sorted(reps, key=lambda c: c["sample_id"])
            if len(reps_sorted) >= 2:
                sequences["O"].append({
                    "seq_id": f"O_{signer}_{session}_{rep_sym}",
                    "signer_id": signer,
                    "session": session,
                    "type": "O",
                    "clips": [reps_sorted[0], reps_sorted[1]],
                })

    return sequences


def run_rearm_check(
    config_specs: Sequence[str],
    join_ms_list: Sequence[float],
    manifest_path: str = DEFAULT_MANIFEST,
    checkpoint_path: Optional[str] = DEFAULT_CKPT,
    argv: Optional[Sequence[str]] = None,
    synthetic_only: bool = False,
    min_detected_frames: Optional[int] = None,
    overrides: Sequence[str] = (),
    gates: Optional[Tuple[str, str]] = None,
    decoder: bool = False,
    classifier=None,
) -> Dict[str, Any]:
    """
    Main evaluation routine running the segmenter across configs and join_ms. checkpoint_path None: no label check
    (label_agrees None) and min_detected_frames must be given; with a checkpoint min_detected_frames comes from it.
    decoder (step D3, plan 15 lần sửa 4): a config with rearm_mode 'classifier' runs the window classifier + label
    decoder (metrics of §5.1, strict garbage), a motion_pose config runs the segmenter as before plus the strict
    block; gates are those of §5.1; G7 (QIPEDC) is reported. The checkpoint is required (no silent skip).
    classifier: an object with classify(segment, top_k) and min_detected_frames used instead of the checkpoint
    (tests).
    """
    # Parse config specifications NAME=PATH
    configs_meta = {}
    loaded_configs = {}
    for spec in config_specs:
        name, values, meta = resolve_config_spec(spec)
        configs_meta[name] = meta
        loaded_configs[name] = values
    by_name: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for spec in overrides:
        name, key, value = parse_override(spec)
        if name not in loaded_configs:
            raise ValueError(f"override {spec!r}: no config named {name!r}")
        by_name[name][key] = value
    for name, ov in by_name.items():
        loaded_configs[name] = apply_overrides(loaded_configs[name], ov)
        configs_meta[name]["overrides"] = dict(ov)
    if gates is not None and not all(g in loaded_configs for g in gates):
        raise ValueError(f"--gates {gates}: unknown config name")

    if synthetic_only:
        return {
            "generated_by": generated_by(argv or []),
            "note": NOTE,
            "note_vi": NOTE_VI,
            "configs": configs_meta,
            "join_ms": list(join_ms_list),
            "results": {},
        }

    if decoder and classifier is None:
        if checkpoint_path is None:
            raise ValueError("--decoder needs the Level 1 checkpoint (the decoder classifies a sliding window); "
                             "none given")
        if not os.path.isfile(checkpoint_path):
            raise FileNotFoundError(f"--decoder needs the Level 1 checkpoint; not found: {checkpoint_path}")
    if classifier is None and checkpoint_path is not None:
        classifier = Level1Classifier.from_checkpoint(checkpoint_path)
    if classifier is not None:
        if min_detected_frames is not None and int(min_detected_frames) != classifier.min_detected_frames:
            raise ValueError("min_detected_frames differs from the checkpoint's")
        min_det = classifier.min_detected_frames
    elif min_detected_frames is None:
        raise ValueError("without a checkpoint min_detected_frames must be given")
    else:
        min_det = int(min_detected_frames)

    # Determine hand_lost_ms from the first config
    first_cfg = list(loaded_configs.values())[0]
    hand_lost_ms = float(first_cfg.get("hand_lost_ms", 200.0))

    manifest_data = load_and_prepare_manifest_clips(manifest_path, min_det, hand_lost_ms=hand_lost_ms)
    candidate_seqs = build_candidate_sequences(manifest_data["clips"])
    # untrimmed clips (the training input / the R2 reference shapes), same min_detected_frames filter
    whole = {c["sample_id"]: c for c in seg_report.load_train_clips(manifest_path, min_det)["clips"]}
    whole_label: Dict[str, Optional[str]] = {}
    refs: Dict[Tuple[str, str], Optional[np.ndarray]] = {}

    def ref_of(cfg_name: str, sample_id: str) -> Optional[np.ndarray]:
        if (cfg_name, sample_id) not in refs:
            prof = seg_report.clip_pose_profile(whole[sample_id], loaded_configs[cfg_name], min_det)
            refs[(cfg_name, sample_id)] = prof["ref"]
        return refs[(cfg_name, sample_id)]

    def label(segment: SignSegment, top_k: int) -> Optional[str]:
        r = classifier.classify(segment, top_k)
        return r.get("prediction") if r.get("status") == "ok" else None

    def wlabel(sample_id: str, top_k: int) -> Optional[str]:
        if sample_id not in whole_label:
            whole_label[sample_id] = label(whole_clip_segment(whole[sample_id]), top_k)
        return whole_label[sample_id]

    def run_decoder_chains(cfg_name: str, params: Dict[str, Any], seq_type: str, j_ms: float) -> Dict[str, Any]:
        top_k = int(params["top_k"])
        per_seq, details = [], []
        for seq in candidate_seqs[seq_type]:
            seq_stream, _ = build_concatenated_sequence(seq["clips"], join_ms=j_ms)
            kept_ids = [c["sample_id"] for c in seq_stream["kept_clips"]]
            if not kept_ids:
                continue
            expected = [wlabel(sid, top_k) for sid in kept_ids]
            dec = decode_chain(seq_stream, params, lambda sg: classifier.classify(sg, top_k), min_det)
            m = strict_chain_metrics(dec["final"], seq_stream["frame_sources"], expected)
            m.update({"n_replace": dec["n_replace"], "hand_lost": dec["n_append_after_lost"],
                      "n_windows": dec["n_windows"]})
            per_seq.append(m)
            details.append({"seq_id": seq["seq_id"], "sample_ids": kept_ids, "expected": expected,
                            "emitted": [lab for _, lab in dec["final"]], "metrics": m})
        out = _sum_strict(per_seq, ("n_replace", "hand_lost", "n_windows"))
        out.update({"n_sequences": len(candidate_seqs[seq_type]), "label_agrees": None,
                    "label_agrees_note": "not applicable: an emission counts for a clip only when its label equals "
                                         "the whole-clip label (definitions.garbage)",
                    "sequences": details})
        return out

    def strict_for_segments(segs: Sequence[Dict[str, Any]], seq_stream: Dict[str, Any], kept_ids: Sequence[str],
                            top_k: int) -> Dict[str, Any]:
        """Strict metrics (§5.1) of a motion_pose run, for comparison (report only)."""
        ts_all = seq_stream["timestamps_ms"]
        ems = []
        for sg in segs:
            hit = np.where(np.abs(ts_all - sg["t_emit_ms"]) <= 1e-6)[0]
            idx = int(hit[0]) if len(hit) else int(sg["end_idx"])
            ems.append((idx, label(sg["raw_segment"], top_k)))
        return strict_chain_metrics(ems, seq_stream["frame_sources"], [wlabel(sid, top_k) for sid in kept_ids])

    results: Dict[str, Any] = {}

    for cfg_name, params in loaded_configs.items():
        results[cfg_name] = {}
        for seq_type in ("L", "T", "O"):
            results[cfg_name][seq_type] = {}
            for j_ms in join_ms_list:
                j_key = str(int(j_ms)) if float(j_ms).is_integer() else str(j_ms)
                if decoder and params["rearm_mode"] == "classifier":
                    results[cfg_name][seq_type][j_key] = run_decoder_chains(cfg_name, params, seq_type, j_ms)
                    continue
                strict_seqs = []

                total_clips = 0
                total_segs = 0
                total_garbage = 0
                reasons_all: Counter = Counter()
                total_hand_lost = 0
                total_one = 0
                total_miss = 0
                total_multi = 0
                total_covered = 0
                total_one_covered = 0
                n_label_eval = 0
                n_label_agree = 0
                all_order_ok = True
                seq_details = []

                for seq in candidate_seqs[seq_type]:
                    seq_stream, build_stats = build_concatenated_sequence(seq["clips"], join_ms=j_ms)
                    n_kept = len(seq_stream["kept_clips"])
                    if n_kept == 0:
                        continue

                    segs = run_segmenter_on_stream(seq_stream, params, min_det)
                    assigned = assign_segments_to_clips(segs, seq_stream["frame_sources"], n_kept)
                    kept_ids = [c["sample_id"] for c in seq_stream["kept_clips"]]
                    distances = None
                    if seq_type == "L":
                        kept_refs = [ref_of(cfg_name, sid) for sid in kept_ids]
                        distances = [pose_distance(a, b) if a is not None and b is not None else None
                                     for a, b in zip(kept_refs, kept_refs[1:])]
                    metrics = calculate_metrics(assigned, n_kept, clip_distances=distances,
                                                rearm_pose_dist=params["rearm_pose_dist"] if distances is not None
                                                else None)
                    if seq_type == "L":
                        total_covered += metrics["n_clips_covered"]
                        total_one_covered += metrics["n_one_covered"]
                    if classifier is not None:
                        for c_idx, sid in enumerate(kept_ids):
                            if len(assigned["clip_segments"][c_idx]) != 1:
                                continue
                            if sid not in whole_label:
                                whole_label[sid] = label(whole_clip_segment(whole[sid]), int(params["top_k"]))
                            seg_label = label(assigned["clip_segments"][c_idx][0]["raw_segment"], int(params["top_k"]))
                            n_label_eval += 1
                            n_label_agree += int(seg_label is not None and seg_label == whole_label[sid])

                    total_clips += metrics["n_clips"]
                    total_segs += metrics["total_segments"]
                    total_garbage += len(assigned["garbage_segments"])
                    reasons_all.update(metrics["close_reason"])
                    total_hand_lost += metrics["hand_lost"]
                    if not metrics["order_ok"]:
                        all_order_ok = False

                    n_one_s = sum(1 for c_idx in range(n_kept) if len(assigned["clip_segments"][c_idx]) == 1)
                    n_miss_s = sum(1 for c_idx in range(n_kept) if len(assigned["clip_segments"][c_idx]) == 0)
                    n_multi_s = sum(1 for c_idx in range(n_kept) if len(assigned["clip_segments"][c_idx]) >= 2)
                    total_one += n_one_s
                    total_miss += n_miss_s
                    total_multi += n_multi_s
                    if decoder:
                        strict_seqs.append(strict_for_segments(segs, seq_stream, kept_ids, int(params["top_k"])))

                    seq_details.append({
                        "seq_id": seq["seq_id"],
                        "n_clips": n_kept,
                        "sample_ids": kept_ids,
                        "pair_distances": distances,
                        "metrics": metrics,
                    })

                one_rate = (float(total_one) / float(total_clips)) if total_clips > 0 else 0.0
                miss_rate = (float(total_miss) / float(total_clips)) if total_clips > 0 else 0.0
                multi_rate = (float(total_multi) / float(total_clips)) if total_clips > 0 else 0.0
                garbage_per_clip = (float(total_garbage) / float(total_clips)) if total_clips > 0 else 0.0

                results[cfg_name][seq_type][j_key] = {
                    "n_sequences": len(candidate_seqs[seq_type]),
                    "n_clips": total_clips,
                    "total_segments": total_segs,
                    "close_reason": dict(reasons_all),
                    "one_rate": one_rate,
                    "miss_rate": miss_rate,
                    "multi_rate": multi_rate,
                    "garbage_per_clip": garbage_per_clip,
                    "order_ok": all_order_ok,
                    "hand_lost": total_hand_lost,
                    "one_rate_covered": (float(total_one_covered) / float(total_covered)) if total_covered else None,
                    "n_clips_covered": total_covered,
                    "label_agrees": ({"n_one_segment_clips": n_label_eval, "n_agree": n_label_agree,
                                      "rate": (n_label_agree / n_label_eval) if n_label_eval else None,
                                      "definition": "clips with exactly one segment: model label of the segment == "
                                                    "model label of the whole untrimmed clip (report only, not a "
                                                    "gate, not accuracy)"}
                                     if classifier is not None else None),
                    "sequences": seq_details,
                }
                if decoder:
                    results[cfg_name][seq_type][j_key]["strict"] = {
                        **_sum_strict(strict_seqs),
                        "note": "the §5.1 strict metrics of this motion_pose run (emission = the frame at t_emit), "
                                "for comparison with a classifier config; report only"}

    report = {
        "generated_by": generated_by(argv or []),
        "note": NOTE,
        "note_vi": NOTE_VI,
        "manifest": {"path": rel(manifest_path), "sha256": sha256_file(manifest_path)},
        "checkpoint": ({"path": rel(checkpoint_path), "sha256": sha256_file(checkpoint_path)}
                       if checkpoint_path is not None else None),
        "min_detected_frames": min_det,
        "manifest_summary": {
            "n_manifest_hauuto": manifest_data["n_manifest_hauuto"],
            "n_prepared_clips": len(manifest_data["clips"]),
            "excluded": manifest_data["excluded"],
        },
        "configs": configs_meta,
        "join_ms": list(join_ms_list),
        "results": results,
    }
    if decoder:
        report["mode"] = "decoder"
        report["rearm_modes"] = {n: p["rearm_mode"] for n, p in loaded_configs.items()}
        report["definitions"] = DECODER_DEFINITIONS
        report["exploratory_params_note"] = EXPLORATORY_PARAMS_NOTE
        report["decoder_params"] = {n: {k: p[k] for k in ("cls_window_ms", "cls_conf", "cls_stable_ms", "hand_lost_ms")}
                                    for n, p in loaded_configs.items() if p["rearm_mode"] == "classifier"}
        report["qipedc_g7"] = qipedc_report(manifest_path, loaded_configs, classifier, min_det)
    if gates is not None and decoder:
        gate_cfg, base_cfg = gates
        single = {}
        for n in (gate_cfg, base_cfg):
            p = loaded_configs[n]
            if p["rearm_mode"] == "classifier":
                top_k = int(p["top_k"])
                wl = {sid: wlabel(sid, top_k) for sid in whole}
                single[n] = single_clip_rates_decoder(list(whole.values()), p,
                                                      lambda sg, k=top_k: classifier.classify(sg, k), min_det, wl)
            else:
                single[n] = single_clip_rates(list(whole.values()), p, min_det)
        report["single_clip"] = {**single, "definition": DECODER_DEFINITIONS["single_clip"]}
        report["gates"] = evaluate_decoder_gates(results, single, gate_cfg, base_cfg)
    elif gates is not None:
        gate_cfg, base_cfg = gates
        single = {n: single_clip_rates(list(whole.values()), loaded_configs[n], min_det) for n in (gate_cfg, base_cfg)}
        report["single_clip"] = {**single, "definition": "every hauuto clip with >= min_detected_frames hand frames, "
                                                         "untrimmed, one fresh segmenter, flush 1 ms after the last "
                                                         "frame; rate = share with exactly one SignSegment"}
        report["gates"] = evaluate_gates(results, single, gate_cfg, base_cfg)
    return report


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan 15 Step R0: Re-arm check on concatenated train clips."
    )
    parser.add_argument(
        "--config",
        dest="configs",
        action="append",
        required=True,
        help="Config specification in the format NAME=PATH (e.g. current=configs/level1_realtime.json). May be specified multiple times.",
    )
    parser.add_argument(
        "--join-ms",
        dest="join_ms",
        required=True,
        help="Comma-separated join durations in milliseconds (e.g. '0,300,600'). Required, no default.",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default=None,
        help="Path to output JSON report.",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest",
        default=DEFAULT_MANIFEST,
        help="Path to manifest.csv",
    )
    parser.add_argument(
        "--checkpoint",
        dest="checkpoint",
        default=DEFAULT_CKPT,
        help="Path to alphabet checkpoint",
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="NAME:KEY=JSON override of one config key (e.g. on:pose_change_rules=true); recorded in the report.",
    )
    parser.add_argument(
        "--decoder",
        dest="decoder",
        action="store_true",
        help="step D3/D4 (plan 15 lần sửa 4): configs with rearm_mode 'classifier' run the window classifier + label "
             "decoder; gates of §5.1; G7 QIPEDC reported. Needs the checkpoint.",
    )
    parser.add_argument(
        "--gates",
        dest="gates",
        default=None,
        help="GATE:BASELINE config names (e.g. on:off): run G6 on single clips and evaluate gates G1-G6 (step R3).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if "--write-mode-config" in argv:
        wp = argparse.ArgumentParser(description="Step D4: rearm_mode -> 'classifier' from a committed D4 JSON.")
        wp.add_argument("--write-mode-config", required=True, help="config to update")
        wp.add_argument("--rearm-json", required=True, help="committed --decoder rearm_check JSON with gates (step D4)")
        wargs = wp.parse_args(argv)
        change = write_mode_config(wargs.write_mode_config, wargs.rearm_json)["rearm_mode"]
        print(f"rearm_mode: {change['old']['value']} -> {change['new']['value']} ({change['new']['reason']})")
        return 0
    if "--write-demo-config" in argv:
        wp = argparse.ArgumentParser(description="Plan 15 lần sửa 5: demo config with rearm_mode 'classifier' (user "
                                                 "decision (a)) from a committed D4 JSON in which only G6 tones failed.")
        wp.add_argument("--write-demo-config", required=True, help="demo config to write (never the base config)")
        wp.add_argument("--rearm-json", required=True, help="committed --decoder rearm_check JSON with gates (step D4)")
        wargs = wp.parse_args(argv)
        res = write_demo_config(wargs.write_demo_config, wargs.rearm_json)
        print(f"demo config {res['out']} (sha256 {sha256_file(wargs.write_demo_config)}): rearm_mode "
              f"{res['rearm_mode']['old']['value']} -> {res['rearm_mode']['new']['value']}; base {res['base']['path']} "
              f"(sha256 {res['base']['sha256']}, commit {res['base']['commit']}) unchanged")
        return 0
    if "--write-rev7-config" in argv:
        wp = argparse.ArgumentParser(description="Plan 15 lần sửa 7: new demo config = the committed demo config of "
                                                 "lần sửa 5 + the values of lần sửa 7 §2 (user decision 'File config "
                                                 "mới').")
        wp.add_argument("--write-rev7-config", required=True,
                        help=f"config to write (never the base), normally {REV7_DEMO_CONFIG}")
        wp.add_argument("--base", default=REV7_BASE_CONFIG, help="committed demo config (default %(default)s)")
        wargs = wp.parse_args(argv)
        res = write_rev7_config(wargs.write_rev7_config, wargs.base)
        changes = ", ".join(f"{k} {(c['old'] or {}).get('value', '-')} -> {c['new']['value']}"
                            for k, c in res["changed"].items())
        base = res["base"]
        print(f"lần sửa 7 config {res['out']} (sha256 {sha256_file(wargs.write_rev7_config)}): {changes}; "
              f"base {base['path']} (sha256 {base['sha256']}, commit {base['commit']}) unchanged")
        return 0
    if "--write-rules-config" in argv:
        wp = argparse.ArgumentParser(description="Step R3: pose_change_rules -> true from a committed R3 JSON.")
        wp.add_argument("--write-rules-config", required=True, help="config to update")
        wp.add_argument("--rearm-json", required=True, help="committed rearm_check JSON with gates (step R3)")
        wargs = wp.parse_args(argv)
        change = write_rules_config(wargs.write_rules_config, wargs.rearm_json)["pose_change_rules"]
        print(f"pose_change_rules: {change['old']['value']} -> {change['new']['value']} ({change['new']['reason']})")
        return 0
    parser = create_parser()
    args = parser.parse_args(argv)
    gates = None
    if args.gates:
        if ":" not in args.gates:
            parser.error("--gates must be GATE:BASELINE")
        gates = tuple(args.gates.split(":", 1))

    try:
        join_ms_list = [float(x.strip()) for x in args.join_ms.split(",") if x.strip()]
    except ValueError as e:
        parser.error(f"Invalid --join-ms values: {args.join_ms!r} ({e})")

    try:
        report = run_rearm_check(
            config_specs=args.configs,
            join_ms_list=join_ms_list,
            manifest_path=args.manifest,
            checkpoint_path=args.checkpoint,
            argv=argv,
            overrides=args.overrides,
            gates=gates,
            decoder=args.decoder,
        )
    except (ValueError, FileNotFoundError) as e:
        if not args.decoder:
            raise
        print(f"level1_rearm_check: {e}", file=sys.stderr)
        return 2

    if args.out:
        out_path = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Report written to: {out_path}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if "gates" in report:
        failed = [k for k, g in report["gates"]["gates"].items() if not g["pass"]]
        print("gates G1-G6: " + ("ALL PASS" if not failed else "FAILED " + ", ".join(failed)))
        if report["gates"].get("stop_point"):
            print("stop: " + report["gates"]["stop_point"])
        return 0 if not failed else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
