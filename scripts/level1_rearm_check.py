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
#   pose_over_jitter_ratio are then never read by the segmenter, the values of DEFAULT_CONFIG only make the config valid
FILL_RULES = {
    "tail_still_keep_ms": "= hold_ms of this config",
    "pose_change_rules": "= false (the pose rules did not exist at this commit)",
    "rearm_pose_dist": "= value in configs/level1_realtime.json on disk (not read while pose_change_rules is false)",
    "pose_over_jitter_ratio": "= value in configs/level1_realtime.json on disk (not read by the segmenter)",
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
) -> Dict[str, Any]:
    """
    Main evaluation routine running the segmenter across configs and join_ms. checkpoint_path None: no label check
    (label_agrees None) and min_detected_frames must be given; with a checkpoint min_detected_frames comes from it.
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

    classifier = Level1Classifier.from_checkpoint(checkpoint_path) if checkpoint_path is not None else None
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

    results: Dict[str, Any] = {}

    for cfg_name, params in loaded_configs.items():
        results[cfg_name] = {}
        for seq_type in ("L", "T", "O"):
            results[cfg_name][seq_type] = {}
            for j_ms in join_ms_list:
                j_key = str(int(j_ms)) if float(j_ms).is_integer() else str(j_ms)

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
    if gates is not None:
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
        "--gates",
        dest="gates",
        default=None,
        help="GATE:BASELINE config names (e.g. on:off): run G6 on single clips and evaluate gates G1-G6 (step R3).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
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

    report = run_rearm_check(
        config_specs=args.configs,
        join_ms_list=join_ms_list,
        manifest_path=args.manifest,
        checkpoint_path=args.checkpoint,
        argv=argv,
        overrides=args.overrides,
        gates=gates,
    )

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
        return 0 if not failed else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
