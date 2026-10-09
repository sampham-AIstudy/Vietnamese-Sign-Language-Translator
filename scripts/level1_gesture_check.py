#!/usr/bin/env python
"""
Plan 15 lần sửa 13 §3.2 mục 5, §3.3, §9 AC-G7 (step G3; lần sửa 13d): false triggers of the deliberate gestures on
single-sign clips.

Every single-sign landmark clip on this machine is a NEGATIVE for both gestures (nobody does Space / Backspace in them):
  - hauuto  : rows source == "hauuto" of data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv
  - qipedc  : rows source == "qipedc" of the same manifest
  - user1   : every row of data/collected_targeted/manifest.csv
A source that is missing (manifest absent, no row, an npz absent) is an input error (exit 2), never skipped.

Each clip runs ALONE through the frame path of the desktop app (level1_demo.py Level1App._process with the webcam preset
DEFAULT_DEMO_ARGV): timestamps i * 1000 / fps of the manifest (as scripts/level1_rearm_check.py), every frame processed
(no frame dropping), the landmarks of a frame = raw_landmarks where detected_mask (else no hand), then
  - path "raw"      : the landmarks as they are;
  - path "smoothed" : the landmarks through LandmarkSmoother() (the app's --smooth-landmarks of the preset; a frame
                      without hand resets it);
and on each path, with a fresh Level1SignSegmenter (values of configs/level1_demo_classifier_rev9.json = the preset
config; min_detected_frames of the checkpoint, as the app):
  segmenter.push(ts, landmarks, handedness, w, h), then
  - "deliberate": GestureEngine(values of configs/level1_gestures.json + overrides {}).step(ts, landmarks, w, h,
                  still=segmenter.state != "moving") -- the SAME frame's segmenter state, the real w / h also without hand
                  (the one path the app calls, src.inference.level1_gestures.GestureEngine);
  - "legacy"    : the old trackers of the app without --gesture-config (SpaceGestureTracker(--space-hold-ms default) on
                  is_open_palm_space, BackspaceGestureTracker() on is_flat_hand_backspace), report only.
A clip counts for a gesture when it fires it at least once; multi_emit = clips firing it at least twice (report only,
lần sửa 13d §3).

Gates (set BEFORE the measurement in docs/plans/15-lan-sua-13.md §3.3; this script may not move them): on BOTH paths, all
sources pooled, deliberate gestures:
  GF1 rate of clips with >= 1 backspace <= 0.005;   GF2 rate of clips with >= 1 space <= 0.010.
Per source / per class / legacy: report only. A gate that fails = STOP (no parameter change after seeing the result).

These are TRAINING clips of real signers (4 hauuto signers + QIPEDC dictionary + user1): a logic check of the gestures on
real signs, not a webcam rate. Landmarks were extracted with MediaPipe min_detection_confidence 0.5 (hauuto / QIPEDC) and
0.35 (user1, scripts/collect_targeted_signs.py), not the preset's 0.55.

Exit codes: 0 every gate passes, 1 a gate fails (the JSON is written), 2 input error, 3 --verify found an inconsistency.

  python scripts/level1_gesture_check.py --out reports/level1_realtime_2026-10-08/gesture_false_trigger.json
  python scripts/level1_gesture_check.py --verify reports/level1_realtime_2026-10-08/gesture_false_trigger.json
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
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from level1_demo import GESTURE_SPACE_HOLD, GESTURE_SPACE_REARM, SpaceGestureTracker  # noqa: E402
from src.inference.level1_core import (BackspaceGestureTracker, LandmarkSmoother, Level1Classifier,  # noqa: E402
                                       is_flat_hand_backspace, is_open_palm_space, load_level1_config)
from src.inference.level1_gestures import GestureEngine, load_gesture_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter, aspect_points  # noqa: E402

KAGGLE_MANIFEST = os.path.join("data", "external", "alphabet_hands_kaggle", "alphabet_hands", "manifest.csv")
USER1_MANIFEST = os.path.join("data", "collected_targeted", "manifest.csv")
GESTURE_CONFIG = os.path.join("configs", "level1_gestures.json")
SEGMENTER_CONFIG = os.path.join("configs", "level1_demo_classifier_rev9.json")  # config of DEFAULT_DEMO_ARGV
CHECKPOINT = os.path.join("checkpoints", "alphabet_best.pt")
DEFAULT_OUT = os.path.join("reports", "level1_realtime_2026-10-08", "gesture_false_trigger.json")
CODE_PATHS = ("scripts/level1_gesture_check.py", "src", "level1_demo.py", "configs/level1_gestures.json",
              "configs/level1_demo_classifier_rev9.json")

SOURCES = ("hauuto", "qipedc", "user1")
PATHS = ("raw", "smoothed")
KINDS = ("deliberate", "legacy")
GESTURES = ("space", "backspace")
# gates of docs/plans/15-lan-sua-13.md §3.3 (set before the measurement; never changed after seeing a result)
GATE_SET_IN = "đặt trước ở 15-lan-sua-13 §3.3"
GATES = OrderedDict([
    ("GF1", {"gesture": "backspace", "max_rate": 0.005, "kind": "deliberate", "paths": list(PATHS)}),
    ("GF2", {"gesture": "space", "max_rate": 0.010, "kind": "deliberate", "paths": list(PATHS)}),
])
NOTE = ("clip một ký hiệu THẬT (clip train: 4 người hauuto + QIPEDC + user1) = âm tính cho cả hai cử chỉ; kiểm logic cử chỉ "
        "trên ký hiệu thật, KHÔNG phải tỉ lệ webcam; mỗi clip chạy riêng, mọi khung (không bỏ khung như webcam)")
LIMITS = [
    "landmark trích bằng MediaPipe min_detection_confidence 0.5 (hauuto, QIPEDC) và 0.35 (user1, "
    "scripts/collect_targeted_signs.py), preset dùng 0.55",
    "clip đã dùng để train model chữ (hauuto, user1) nhưng KHÔNG dùng để chỉnh tham số cử chỉ (giá trị thiết kế đặt trước); "
    "nếu GF trượt và tham số bị chỉnh lại thì các clip này thành dữ liệu chỉnh (15-lan-sua-13 §11)",
    "theo nguồn / lớp và đường legacy chỉ báo cáo (QIPEDC quá ít clip cho ngưỡng riêng)",
]
EXIT_OK, EXIT_GATE_FAIL, EXIT_INPUT_ERROR, EXIT_INCONSISTENT = 0, 1, 2, 3


class InputError(Exception):
    """Missing source / file / config: exit 2."""


# ------------------------------------------------------------------------------------------------------ helpers
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve(path: str) -> str:
    """A relative path that does not exist from the current directory is taken from the repository root."""
    if os.path.isabs(path) or os.path.exists(path):
        return os.path.abspath(path)
    return os.path.join(ROOT, path)


def rel(path: str) -> str:
    r = os.path.relpath(os.path.abspath(path), ROOT)
    return (os.path.abspath(path) if r.startswith("..") else r).replace("\\", "/")


def _git(*args) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def file_commit(path: str) -> Optional[str]:
    """Last commit of a tracked file without uncommitted change, else None."""
    r = rel(path)
    if _git("ls-files", "--error-unmatch", "--", r) is None:
        return None
    if _git("status", "--porcelain", "--", r) != "":
        return None
    return _git("log", "-1", "--format=%H", "--", r) or None


def generated_by(argv: Sequence[str]) -> Dict[str, Any]:
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    return {
        "command": " ".join(["python", "scripts/level1_gesture_check.py", *argv]),
        "git_commit": _git("rev-parse", "HEAD"),
        "code_dirty": None if status is None else bool(status),
        "code_paths": list(CODE_PATHS),
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "os": platform.platform(),
    }


# ------------------------------------------------------------------------------------------------------ clips
def _read_rows(manifest: str) -> List[Dict[str, str]]:
    if not os.path.isfile(manifest):
        raise InputError(f"manifest not found: {manifest}")
    with open(manifest, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def list_clips(kaggle_manifest: str, user1_manifest: str) -> List[Dict[str, Any]]:
    """Every clip of the 3 sources, in manifest order: {source, sample_id, symbol, signer_id, npz, fps, width, height}.
    A missing manifest, a source without row or a missing npz -> InputError (no silent skip)."""
    kaggle_rows = _read_rows(kaggle_manifest)
    user1_rows = _read_rows(user1_manifest)
    per_source = {
        "hauuto": (kaggle_manifest, [r for r in kaggle_rows if r.get("source") == "hauuto"]),
        "qipedc": (kaggle_manifest, [r for r in kaggle_rows if r.get("source") == "qipedc"]),
        "user1": (user1_manifest, user1_rows),
    }
    clips = []
    for source in SOURCES:
        manifest, rows = per_source[source]
        if not rows:
            raise InputError(f"source {source!r}: no clip in {manifest}")
        base = os.path.dirname(manifest)
        for r in rows:
            npz = os.path.join(base, r["landmark_path"])
            if not os.path.isfile(npz):
                raise InputError(f"source {source!r}: landmark file not found: {npz}")
            fps, width, height = float(r["fps"]), int(r["width"]), int(r["height"])
            if not (np.isfinite(fps) and fps > 0 and width > 0 and height > 0):
                raise InputError(f"{r['sample_id']}: fps / width / height must be > 0")
            clips.append({"source": source, "sample_id": r["sample_id"], "symbol": r["symbol"],
                          "signer_id": r.get("signer_id", ""), "npz": npz, "fps": fps, "width": width,
                          "height": height})
    return clips


def load_frames(npz: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    with np.load(npz) as z:
        raw = np.asarray(z["raw_landmarks"], dtype=np.float32)
        det = np.asarray(z["detected_mask"], dtype=bool)
        hand = [str(h) for h in z["handedness_label"]]
    if raw.ndim != 3 or raw.shape[1:] != (21, 3) or len(det) != len(raw) or len(hand) != len(raw):
        raise InputError(f"{npz}: raw_landmarks [T, 21, 3], detected_mask [T], handedness_label [T] expected")
    return raw, det, hand


# ------------------------------------------------------------------------------------------------------ one clip
def _new_counts() -> Dict[str, int]:
    return {"space": 0, "backspace": 0}


def run_clip(clip: Dict[str, Any], seg_values: Dict[str, Any], gesture_values: Dict[str, Any],
             min_detected_frames: int, space_hold_ms: float = GESTURE_SPACE_HOLD,
             space_rearm_ms: float = GESTURE_SPACE_REARM) -> Dict[str, Any]:
    """One clip on both paths -> {path: {"emits": {kind: {space, backspace}}, "frames": {...}}} (emission counts)."""
    raw, det, hand = load_frames(clip["npz"])
    w, h, fps = clip["width"], clip["height"], clip["fps"]
    nonfinite = int(np.sum(det & ~np.all(np.isfinite(raw.reshape(len(raw), -1)), axis=1))) if len(raw) else 0
    out = {}
    for path in PATHS:
        segmenter = Level1SignSegmenter(seg_values, min_detected_frames)
        smoother = LandmarkSmoother() if path == "smoothed" else None
        engine = GestureEngine(gesture_values)
        old_space = SpaceGestureTracker(space_hold_ms, space_rearm_ms)
        old_back = BackspaceGestureTracker()
        emits = {kind: _new_counts() for kind in KINDS}
        frames = {"n_frames": int(len(raw)), "hand_frames": 0, "palm_frames": 0, "flat_frames": 0,
                  "nonfinite_hand_frames": nonfinite}
        for i in range(len(raw)):
            ts = i * 1000.0 / fps
            landmarks = raw[i] if det[i] and np.all(np.isfinite(raw[i])) else None
            handedness = hand[i] if landmarks is not None else ""
            if smoother is not None:  # the app: a frame without hand resets the smoother
                landmarks = smoother.filter(ts, landmarks)
            segmenter.push(ts, landmarks, handedness, w, h)
            # deliberate: the app's _gesture_engine_step, still of the SAME frame (after segmenter.push)
            res = engine.step(ts, landmarks, w, h, still=segmenter.state != "moving")
            emits["deliberate"]["space"] += int(res["space"])
            emits["deliberate"]["backspace"] += int(res["backspace"])
            frames["palm_frames"] += int(res["is_palm"])
            frames["flat_frames"] += int(res["is_flat"])
            # legacy: the app without --gesture-config (_gesture_step, _gesture_backspace_step)
            has_hand = landmarks is not None
            frames["hand_frames"] += int(has_hand)
            points = aspect_points(landmarks, w, h) if has_hand else None
            is_space = has_hand and bool(is_open_palm_space(points))
            is_flat = has_hand and bool(is_flat_hand_backspace(points))
            emits["legacy"]["space"] += int(old_space.update(ts, is_space, has_hand=has_hand))
            emits["legacy"]["backspace"] += int(old_back.update(ts, points, is_flat, has_hand=has_hand))
        out[path] = {"emits": emits, "frames": frames}
    return out


# ------------------------------------------------------------------------------------------------------ report
def _empty_block() -> Dict[str, Any]:
    return {path: {kind: {"n_clips": 0, "space_clips": 0, "backspace_clips": 0, "space_multi_emit": 0,
                          "backspace_multi_emit": 0, "space_emits": 0, "backspace_emits": 0}
                   for kind in KINDS} for path in PATHS}


def _add(block: Dict[str, Any], result: Dict[str, Any]) -> None:
    for path in PATHS:
        for kind in KINDS:
            b, e = block[path][kind], result[path]["emits"][kind]
            b["n_clips"] += 1
            for g in GESTURES:
                b[f"{g}_clips"] += int(e[g] >= 1)
                b[f"{g}_multi_emit"] += int(e[g] >= 2)
                b[f"{g}_emits"] += e[g]


def rate(clips_with: int, n_clips: int) -> float:
    return clips_with / n_clips


def compute_rates(counts: Dict[str, Any]) -> Dict[str, Any]:
    """counts (pooled) -> {path: {kind: {space, backspace}}} = clips with >= 1 emission / clips."""
    return {path: {kind: {g: rate(counts[path][kind][f"{g}_clips"], counts[path][kind]["n_clips"]) for g in GESTURES}
                   for kind in KINDS} for path in PATHS}


def evaluate_gates(rates: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    out = OrderedDict()
    for name, g in GATES.items():
        per_path = OrderedDict()
        for path in g["paths"]:
            r = rates[path][g["kind"]][g["gesture"]]
            per_path[path] = {"rate": r, "pass": bool(r <= g["max_rate"])}
        out[name] = {"gesture": g["gesture"], "kind": g["kind"], "max_rate": g["max_rate"], "set_in": GATE_SET_IN,
                     "rule": f"rate of clips with >= 1 {g['gesture']} (all sources pooled) <= {g['max_rate']} on "
                             + " and ".join(g["paths"]),
                     "paths": per_path, "pass": all(p["pass"] for p in per_path.values())}
    return out, all(v["pass"] for v in out.values())


def build_report(clips: Sequence[Dict[str, Any]], results: Sequence[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    counts = _empty_block()
    per_source = OrderedDict((s, _empty_block()) for s in SOURCES)
    per_class: Dict[str, Any] = OrderedDict()
    fired = {path: {kind: {g: [] for g in GESTURES} for kind in KINDS} for path in PATHS}
    frames = {path: {"n_frames": 0, "hand_frames": 0, "palm_frames": 0, "flat_frames": 0, "nonfinite_hand_frames": 0}
              for path in PATHS}
    sources = OrderedDict((s, {"n_clips": 0, "clips_without_hand": 0, "signers": OrderedDict()}) for s in SOURCES)
    for clip, res in zip(clips, results):
        _add(counts, res)
        _add(per_source[clip["source"]], res)
        _add(per_class.setdefault(clip["symbol"], _empty_block()), res)
        src = sources[clip["source"]]
        src["n_clips"] += 1
        src["clips_without_hand"] += int(res["raw"]["frames"]["hand_frames"] == 0)
        src["signers"][clip["signer_id"]] = src["signers"].get(clip["signer_id"], 0) + 1
        for path in PATHS:
            for k in frames[path]:
                frames[path][k] += res[path]["frames"][k]
            for kind in KINDS:
                for g in GESTURES:
                    n = res[path]["emits"][kind][g]
                    if n >= 1:
                        fired[path][kind][g].append({"sample_id": clip["sample_id"], "source": clip["source"],
                                                     "symbol": clip["symbol"], "emits": n})
    rates = compute_rates(counts)
    gates, passed = evaluate_gates(rates)
    report = OrderedDict()
    report["plan"] = "docs/plans/15-lan-sua-13.md §3.2 mục 5, §3.3, §9 AC-G7; docs/plans/15-lan-sua-13d.md (P1, P2, NaN)"
    report["note"] = NOTE
    report["limits"] = list(LIMITS)
    report.update(meta)
    report["n_clips"] = len(clips)
    report["sources"] = sources
    report["counts"] = counts
    report["rates"] = rates
    report["gates"] = gates
    report["pass"] = passed
    report["per_source"] = per_source
    report["per_class"] = per_class
    report["frames"] = frames
    report["fired_clips"] = fired
    return report


def check_report(report: Dict[str, Any]) -> List[str]:
    """Recompute rates, gates and pass from the counts of a report (and the per-source sums) -> list of problems."""
    problems = []
    counts = report["counts"]
    n = report["n_clips"]
    if sum(s["n_clips"] for s in report["sources"].values()) != n:
        problems.append("sources n_clips do not sum to n_clips")
    for source in SOURCES:
        if source not in report["sources"] or report["sources"][source]["n_clips"] < 1:
            problems.append(f"source {source} missing")
    for path in PATHS:
        for kind in KINDS:
            c = counts[path][kind]
            if c["n_clips"] != n:
                problems.append(f"counts.{path}.{kind}.n_clips != n_clips")
            for key in c:
                total = sum(report["per_source"][s][path][kind][key] for s in report["per_source"])
                if total != c[key]:
                    problems.append(f"per_source {path}.{kind}.{key} sums to {total}, counts {c[key]}")
            for g in GESTURES:
                if len(report["fired_clips"][path][kind][g]) != c[f"{g}_clips"]:
                    problems.append(f"fired_clips {path}.{kind}.{g} != counts")
                if report["rates"][path][kind][g] != c[f"{g}_clips"] / c["n_clips"]:
                    problems.append(f"rates.{path}.{kind}.{g} != {g}_clips / n_clips")
    for name, g in GATES.items():
        got = report["gates"].get(name)
        if got is None or got["max_rate"] != g["max_rate"]:
            problems.append(f"gate {name} missing or its threshold changed")
            continue
        for path in g["paths"]:
            r = counts[path][g["kind"]][f"{g['gesture']}_clips"] / counts[path][g["kind"]]["n_clips"]
            if got["paths"][path]["rate"] != r or got["paths"][path]["pass"] != (r <= g["max_rate"]):
                problems.append(f"gate {name} {path} does not match the counts")
    expected_pass = all(
        counts[p][g["kind"]][f"{g['gesture']}_clips"] / counts[p][g["kind"]]["n_clips"] <= g["max_rate"]
        for g in GATES.values() for p in g["paths"])
    if report["pass"] != expected_pass:
        problems.append("pass does not match the gates recomputed from the counts")
    return problems


# ------------------------------------------------------------------------------------------------------ main
def min_detected_frames_of(args) -> Tuple[int, Dict[str, Any]]:
    if args.min_detected_frames is not None:
        return int(args.min_detected_frames), {"value": int(args.min_detected_frames), "from": "--min-detected-frames"}
    ckpt = resolve(args.checkpoint)
    if not os.path.isfile(ckpt):
        raise InputError(f"checkpoint not found: {args.checkpoint}")
    value = Level1Classifier.from_checkpoint(ckpt).min_detected_frames  # as the app (Level1App.segmenter)
    return int(value), {"value": int(value), "from": "checkpoint preprocessing (as level1_demo.Level1App)",
                        "checkpoint": rel(ckpt), "checkpoint_sha256": sha256_file(ckpt)}


def run(args, argv: Sequence[str]) -> Dict[str, Any]:
    gesture_path, seg_path = resolve(args.gesture_config), resolve(args.segmenter_config)
    for p, label in ((gesture_path, "gesture config"), (seg_path, "segmenter config")):
        if not os.path.isfile(p):
            raise InputError(f"{label} not found: {p}")
    try:
        gesture_cfg = load_gesture_config(gesture_path)
        seg_cfg = load_level1_config(seg_path)
    except ValueError as e:
        raise InputError(str(e)) from None
    overrides: Dict[str, Any] = {}  # the preset has no --space-hold-ms: effective values = values + overrides
    gesture_values = {**gesture_cfg["values"], **overrides}
    clips = list_clips(resolve(args.kaggle_manifest), resolve(args.user1_manifest))
    min_det, min_det_meta = min_detected_frames_of(args)
    results = [run_clip(c, seg_cfg["values"], gesture_values, min_det) for c in clips]
    smoother = LandmarkSmoother()
    meta = OrderedDict()
    meta["generated_by"] = generated_by(argv)
    meta["gesture_config"] = {"path": rel(gesture_path), "sha256": gesture_cfg["sha256"],
                              "git_commit": file_commit(gesture_path), "values": gesture_cfg["values"],
                              "overrides": overrides, "effective": "values + overrides (as level1_demo gestures)"}
    meta["segmenter_config"] = {"path": rel(seg_path), "sha256": seg_cfg["sha256"], "git_commit": file_commit(seg_path),
                                "note": "config of the webcam preset (level1_demo.DEFAULT_DEMO_ARGV)"}
    meta["min_detected_frames"] = min_det_meta
    meta["landmark_smoother"] = {"alpha_static": smoother.alpha_static, "alpha_dynamic": smoother.alpha_dynamic,
                                 "speed_threshold": smoother.speed_threshold,
                                 "note": "LandmarkSmoother() as the app's --smooth-landmarks (path smoothed only)"}
    meta["legacy"] = {"space": {"tracker": "level1_demo.SpaceGestureTracker", "hold_ms": GESTURE_SPACE_HOLD,
                                "rearm_ms": GESTURE_SPACE_REARM},
                      "backspace": {"tracker": "level1_core.BackspaceGestureTracker()"},
                      "note": "the app without --gesture-config; report only (review A3.2 probe 24/640, 8/640 had no JSON)"}
    meta["manifests"] = {
        "kaggle": {"path": rel(resolve(args.kaggle_manifest)), "sha256": sha256_file(resolve(args.kaggle_manifest))},
        "user1": {"path": rel(resolve(args.user1_manifest)), "sha256": sha256_file(resolve(args.user1_manifest))},
    }
    meta["timestamps"] = "i * 1000 / fps of the manifest; every frame processed (headless, no frame dropping)"
    return build_report(clips, results, meta)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kaggle-manifest", default=KAGGLE_MANIFEST, help="hauuto + qipedc clips")
    p.add_argument("--user1-manifest", default=USER1_MANIFEST, help="user1 clips")
    p.add_argument("--gesture-config", default=GESTURE_CONFIG)
    p.add_argument("--segmenter-config", default=SEGMENTER_CONFIG)
    p.add_argument("--checkpoint", default=CHECKPOINT, help="min_detected_frames of the segmenter, as the app")
    p.add_argument("--min-detected-frames", type=int, default=None, help="instead of reading the checkpoint")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--verify", metavar="REPORT", default=None,
                   help="recompute rates / gates / pass of an existing report from its counts (exit 0 or 3)")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    if args.verify is not None:
        try:
            with open(resolve(args.verify), encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, ValueError) as e:
            print(f"level1_gesture_check: {e}", file=sys.stderr)
            return EXIT_INPUT_ERROR
        problems = check_report(report)
        for p in problems:
            print(f"INCONSISTENT: {p}")
        print(f"verify {args.verify}: {'OK' if not problems else 'INCONSISTENT'}; pass={report['pass']}")
        return EXIT_INCONSISTENT if problems else EXIT_OK
    try:
        report = run(args, argv)
    except InputError as e:
        print(f"level1_gesture_check: {e}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for name, g in report["gates"].items():
        print(f"{name} ({g['gesture']} <= {g['max_rate']}): "
              + ", ".join(f"{p} {v['rate']:.6f} {'PASS' if v['pass'] else 'FAIL'}" for p, v in g["paths"].items()))
    print(f"n_clips {report['n_clips']} " + " ".join(f"{s}={v['n_clips']}" for s, v in report["sources"].items()))
    print(f"pass={report['pass']} -> {rel(out)}")
    return EXIT_OK if report["pass"] else EXIT_GATE_FAIL


if __name__ == "__main__":
    sys.exit(main())
