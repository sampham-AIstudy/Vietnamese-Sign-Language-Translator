"""
Tests for scripts/level1_rearm_check.py (Plan 15 Lần sửa 3 — Step R0).

Covers AC-RC1, AC-RC2, AC-RC3, AC-RC4:
- AC-RC1: Trimming leading/trailing no-hand frames; clips with internal hand lost >= hand_lost_ms
          are excluded and counted; mismatched size/fps are excluded and counted.
- AC-RC2: Join interpolation: J=0 produces 0 frames; J>0 produces round(J*fps/1000) frames with
          exact linear interpolation of raw landmarks, handedness of preceding clip, source 'join'.
- AC-RC3: Majority assignment, garbage segments, order_ok, rates (one_rate, miss_rate, multi_rate,
          garbage_per_clip, hand_lost, covered one_rate) on a 3-clip synthetic example.
- AC-RC4: JSON structure contains generated_by, sha256 of configs, 'not accuracy' notice;
          missing --join-ms causes an argparse error (no default).
"""
import io
import json
import os
import unittest
from typing import Any, Dict, List

import numpy as np

from scripts.level1_rearm_check import (
    FILL_RULES,
    assign_segments_to_clips,
    build_concatenated_sequence,
    calculate_metrics,
    create_parser,
    interpolate_join,
    prepare_clip,
    run_rearm_check,
)


class TestRearmCheckAcRC(unittest.TestCase):
    def test_rc1_trim_leading_trailing_no_hand(self):
        """AC-RC1: Trims leading and trailing no-hand frames."""
        raw = np.zeros((10, 21, 3), dtype=np.float32)
        # Frames 2..7 have hand
        detected = np.array([False, False, True, True, True, True, True, True, False, False], dtype=bool)
        for i in range(10):
            raw[i, :, :] = float(i)
        handedness = ["" if not detected[i] else "Right" for i in range(10)]
        clip = {
            "sample_id": "test_001",
            "symbol": "a",
            "kind": "letter",
            "signer_id": "s1",
            "raw": raw,
            "detected": detected,
            "handedness": handedness,
            "width": 640,
            "height": 480,
            "fps": 25.0,
        }
        res, reason = prepare_clip(clip, hand_lost_ms=200.0)
        self.assertIsNotNone(res)
        self.assertIsNone(reason)
        self.assertEqual(len(res["detected"]), 6)
        self.assertTrue(res["detected"][0])
        self.assertTrue(res["detected"][-1])
        self.assertEqual(float(res["raw"][0, 0, 0]), 2.0)
        self.assertEqual(float(res["raw"][-1, 0, 0]), 7.0)

    def test_rc1_internal_hand_lost_excluded_and_counted(self):
        """AC-RC1: Clip with internal hand lost >= hand_lost_ms is excluded with reason."""
        # 25 fps => 40 ms / frame.
        # Frames 0..1: hand; Frames 2..6: lost (5 frames * 40ms = 200ms >= 200ms); Frames 7..8: hand
        detected = np.array([True, True, False, False, False, False, False, True, True], dtype=bool)
        raw = np.zeros((9, 21, 3), dtype=np.float32)
        handedness = ["Right" if d else "" for d in detected]
        clip_bad = {
            "sample_id": "test_internal_lost",
            "symbol": "a",
            "kind": "letter",
            "signer_id": "s1",
            "raw": raw,
            "detected": detected,
            "handedness": handedness,
            "width": 640,
            "height": 480,
            "fps": 25.0,
        }
        res, reason = prepare_clip(clip_bad, hand_lost_ms=200.0)
        self.assertIsNone(res)
        self.assertEqual(reason, "internal_hand_lost")

        # Clip with short internal gap (2 frames * 40ms = 80ms < 200ms) should be accepted
        detected_good = np.array([True, True, False, False, True, True], dtype=bool)
        clip_good = dict(clip_bad, detected=detected_good, raw=np.zeros((6, 21, 3), dtype=np.float32),
                         handedness=["Right" if d else "" for d in detected_good])
        res_good, reason_good = prepare_clip(clip_good, hand_lost_ms=200.0)
        self.assertIsNotNone(res_good)
        self.assertIsNone(reason_good)

    def test_rc1_mismatched_size_or_fps_excluded_and_counted(self):
        """AC-RC1: Clips with mismatched size or fps are excluded when building sequence."""
        c1 = {
            "sample_id": "c1", "symbol": "a", "kind": "letter", "signer_id": "s1",
            "raw": np.zeros((5, 21, 3), dtype=np.float32),
            "detected": np.ones((5,), dtype=bool),
            "handedness": ["Right"] * 5, "width": 640, "height": 480, "fps": 25.0,
        }
        c2_bad_size = dict(c1, sample_id="c2", symbol="b", width=320, height=240)
        c3_bad_fps = dict(c1, sample_id="c3", symbol="c", fps=30.0)
        c4_ok = dict(c1, sample_id="c4", symbol="d")

        seq, stats = build_concatenated_sequence([c1, c2_bad_size, c3_bad_fps, c4_ok], join_ms=0.0)
        self.assertEqual(len(seq["kept_clips"]), 2)
        self.assertEqual([c["sample_id"] for c in seq["kept_clips"]], ["c1", "c4"])
        self.assertEqual(stats["excluded_mismatch"], 2)
        self.assertEqual(stats["mismatched_sample_ids"], ["c2", "c3"])

    def test_rc2_interpolate_join_zero(self):
        """AC-RC2: join_ms == 0 produces 0 interpolated frames."""
        raw_prev = np.ones((21, 3), dtype=np.float32)
        raw_next = np.ones((21, 3), dtype=np.float32) * 5.0
        join = interpolate_join(raw_prev, "Right", raw_next, fps=25.0, join_ms=0.0)
        self.assertEqual(len(join["raw"]), 0)
        self.assertEqual(len(join["detected"]), 0)
        self.assertEqual(len(join["handedness"]), 0)

    def test_rc2_interpolate_join_positive(self):
        """AC-RC2: join_ms > 0 produces round(J*fps/1000) linearly interpolated frames with source 'join'."""
        fps = 20.0
        join_ms = 300.0  # round(300 * 20 / 1000) = 6 frames
        raw_prev = np.ones((21, 3), dtype=np.float32) * 1.0
        raw_next = np.ones((21, 3), dtype=np.float32) * 8.0

        join = interpolate_join(raw_prev, "Left", raw_next, fps=fps, join_ms=join_ms)
        self.assertEqual(len(join["raw"]), 6)
        self.assertEqual(len(join["detected"]), 6)
        self.assertTrue(all(join["detected"]))
        self.assertEqual(join["handedness"], ["Left"] * 6)

        # Step = (8.0 - 1.0) / (6 + 1) = 1.0
        # Expected values: 2.0, 3.0, 4.0, 5.0, 6.0, 7.0
        expected = np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.0], dtype=np.float32)
        for k in range(6):
            np.testing.assert_allclose(join["raw"][k, 0, 0], expected[k], rtol=1e-5)
            np.testing.assert_allclose(join["raw"][k, 20, 2], expected[k], rtol=1e-5)

    def test_rc3_majority_assignment_garbage_and_metrics_on_3clips(self):
        """AC-RC3: majority assignment, garbage, order_ok, rates and covered rate on synthetic 3-clip sequence."""
        # 3 clips: clip 0, clip 1, clip 2
        # Let sequence have frame sources:
        # Frames 0..9 (10 frames): clip 0
        # Frames 10..15 (6 frames): "join"
        # Frames 16..25 (10 frames): clip 1
        # Frames 26..31 (6 frames): "join"
        # Frames 32..41 (10 frames): clip 2
        frame_sources = ([0] * 10) + (["join"] * 6) + ([1] * 10) + (["join"] * 6) + ([2] * 10)
        n_clips = 3

        # Segments defined by frame index ranges [start_idx, end_idx]:
        # seg1: frames 1..8 (8 frames of clip 0) -> clip 0
        # seg2: frames 9..14 (1 frame clip 0, 5 frames "join") -> "join" (GARBAGE)
        # seg3: frames 17..24 (8 frames of clip 1) -> clip 1
        # seg4: frames 33..40 (8 frames of clip 2) -> clip 2
        segments = [
            {"start_idx": 1, "end_idx": 8, "close_reason": "hold", "t_start_ms": 40.0, "t_end_ms": 320.0},
            {"start_idx": 9, "end_idx": 14, "close_reason": "hold", "t_start_ms": 360.0, "t_end_ms": 560.0},
            {"start_idx": 17, "end_idx": 24, "close_reason": "hold", "t_start_ms": 680.0, "t_end_ms": 960.0},
            {"start_idx": 33, "end_idx": 40, "close_reason": "hold", "t_start_ms": 1320.0, "t_end_ms": 1600.0},
        ]

        assigned = assign_segments_to_clips(segments, frame_sources, n_clips)
        self.assertEqual(len(assigned["garbage_segments"]), 1)
        self.assertEqual(assigned["garbage_segments"][0]["start_idx"], 9)
        self.assertEqual(len(assigned["clip_segments"][0]), 1)
        self.assertEqual(len(assigned["clip_segments"][1]), 1)
        self.assertEqual(len(assigned["clip_segments"][2]), 1)

        # Distances between consecutive clips:
        # clip 0 is always covered.
        # pair (0, 1): dist = 0.5 >= threshold 0.3 -> clip 1 covered
        # pair (1, 2): dist = 0.2 < threshold 0.3 -> clip 2 NOT covered
        clip_distances = [0.5, 0.2]  # dist(0, 1) and dist(1, 2)
        rearm_pose_dist = 0.3

        metrics = calculate_metrics(assigned, n_clips, clip_distances=clip_distances,
                                    rearm_pose_dist=rearm_pose_dist)
        self.assertEqual(metrics["n_clips"], 3)
        self.assertEqual(metrics["one_rate"], 1.0)
        self.assertEqual(metrics["miss_rate"], 0.0)
        self.assertEqual(metrics["multi_rate"], 0.0)
        self.assertAlmostEqual(metrics["garbage_per_clip"], 1.0 / 3.0)
        self.assertTrue(metrics["order_ok"])
        self.assertEqual(metrics["hand_lost"], 0)
        # Covered clips: clip 0 (always), clip 1 (dist >= 0.3) -> 2 covered clips, both have 1 segment
        self.assertEqual(metrics["n_clips_covered"], 2)
        self.assertEqual(metrics["one_rate_covered"], 1.0)

    def test_rc3_order_not_ok_and_multi_rate(self):
        """AC-RC3: order_ok is False when assigned clip indices decrease; multi_rate counts clips with >= 2 segs."""
        frame_sources = [0] * 5 + [1] * 5 + [2] * 5
        n_clips = 3
        # Segments in reverse order: clip 2 emitted first, then clip 0 (twice)
        segments = [
            {"start_idx": 11, "end_idx": 14, "close_reason": "hold", "t_start_ms": 440.0, "t_end_ms": 560.0},
            {"start_idx": 0, "end_idx": 2, "close_reason": "hold", "t_start_ms": 0.0, "t_end_ms": 80.0},
            {"start_idx": 3, "end_idx": 4, "close_reason": "hold", "t_start_ms": 120.0, "t_end_ms": 160.0},
        ]
        assigned = assign_segments_to_clips(segments, frame_sources, n_clips)
        metrics = calculate_metrics(assigned, n_clips)
        self.assertFalse(metrics["order_ok"])
        self.assertEqual(metrics["multi_rate"], 1.0 / 3.0)  # clip 0 has 2 segs
        self.assertEqual(metrics["miss_rate"], 1.0 / 3.0)   # clip 1 has 0 segs
        self.assertEqual(metrics["one_rate"], 1.0 / 3.0)    # clip 2 has 1 seg

    def test_rc4_argparse_requires_join_ms(self):
        """AC-RC4: Missing --join-ms causes an argparse error (no default)."""
        parser = create_parser()
        # Missing --join-ms
        with self.assertRaises(SystemExit):
            parser.parse_args(["--config", "current=configs/level1_realtime.json"])

        # Provided --join-ms succeeds
        args = parser.parse_args(["--config", "current=configs/level1_realtime.json", "--join-ms", "0,300,600"])
        self.assertEqual(args.join_ms, "0,300,600")

    def test_rc4_json_output_metadata(self):
        """AC-RC4: JSON output contains generated_by, sha256 of configs, and 'not accuracy' notice."""
        # Use synthetic runner with minimal mock
        res = run_rearm_check(
            config_specs=["current=configs/level1_realtime.json"],
            join_ms_list=[0.0],
            synthetic_only=True,
        )
        self.assertIn("generated_by", res)
        self.assertIn("git_commit", res["generated_by"])
        self.assertIn("configs", res)
        self.assertIn("current", res["configs"])
        self.assertIn("sha256", res["configs"]["current"])
        self.assertIn("note", res)
        self.assertIn("train clips concatenated to test the segmenter logic; not accuracy, not a webcam session",
                      res["note"])


def _git_out(*args) -> bytes:
    """git output; a missing commit (shallow clone) FAILS the caller, it is never skipped."""
    import subprocess
    from scripts.level1_rearm_check import ROOT
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


R1_KEYS = ("pose_change_rules", "rearm_pose_dist", "pose_over_jitter_ratio")  # config keys added by plan 15 R1
D1_KEYS = ("rearm_mode", "cls_window_ms", "cls_conf", "cls_stable_ms")  # config keys added by plan 15 lần sửa 4 D1


class TestConfigProvenanceA2a(unittest.TestCase):
    """A2a (b): configs.<name>.git_commit names the commit the config comes from; never an empty string
    (rearm_check_r0.json at 1acb4a5 had configs.before_a2.git_commit == "" for a config built from 3ebc7b9)."""

    BEFORE = "3ebc7b9"
    PATH = "configs/level1_realtime.json"

    def test_git_spec_records_full_commit_sha_and_fill(self):
        import hashlib
        from scripts.level1_rearm_check import resolve_config_spec
        name, values, meta = resolve_config_spec(f"before_a2=git:{self.BEFORE}:{self.PATH}")
        full = _git_out("rev-parse", "--verify", f"{self.BEFORE}^{{commit}}").decode().strip()
        self.assertEqual(name, "before_a2")
        self.assertEqual(len(full), 40)
        self.assertTrue(full.startswith(self.BEFORE))
        self.assertEqual(meta["git_commit"], full)
        self.assertTrue(meta["committed"])
        self.assertEqual(meta["path"], self.PATH)
        blob = _git_out("show", f"{full}:{self.PATH}")
        self.assertEqual(meta["sha256"], hashlib.sha256(blob).hexdigest())
        self.assertEqual(meta["filled"], {"tail_still_keep_ms": "= hold_ms of this config",
                                          **{k: FILL_RULES[k] for k in R1_KEYS + D1_KEYS}})
        self.assertEqual(values["tail_still_keep_ms"], values["hold_ms"])
        self.assertIs(values["pose_change_rules"], False)
        raw = json.loads(blob.decode("utf-8"))
        self.assertNotIn("tail_still_keep_ms", raw)
        for key, value in values.items():
            if key not in meta["filled"]:
                self.assertEqual(value, raw[key]["value"], key)

    def test_git_spec_without_missing_key_fills_nothing(self):
        from scripts.level1_rearm_check import resolve_config_spec
        from src.inference.level1_core import CONFIG_SPEC
        _, _, meta = resolve_config_spec(f"cur=git:HEAD:{self.PATH}")
        at_head = json.loads(_git_out("show", f"HEAD:{self.PATH}").decode("utf-8"))
        self.assertEqual(set(meta["filled"]), {k for k in CONFIG_SPEC if k not in at_head})
        self.assertEqual(meta["git_commit"], _git_out("rev-parse", "HEAD").decode().strip())

    def test_tracked_path_records_last_commit_when_clean(self):
        from scripts.level1_rearm_check import resolve_config_spec
        _, _, meta = resolve_config_spec(f"current={self.PATH}")
        dirty = _git_out("status", "--porcelain", "--", self.PATH).decode().strip()
        expected = None if dirty else _git_out("log", "-1", "--format=%H", "--", self.PATH).decode().strip()
        self.assertEqual(meta["git_commit"], expected)
        self.assertEqual(meta["committed"], expected is not None)

    def test_untracked_path_records_none_not_empty(self):
        import shutil
        import tempfile
        from scripts.level1_rearm_check import ROOT, resolve_config_spec
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="_tmp_rearm_a2a_") as d:  # inside the repo, untracked
            path = os.path.join(d, "config_copy.json")
            shutil.copyfile(os.path.join(ROOT, self.PATH), path)
            _, _, meta = resolve_config_spec(f"copy={path}")
        self.assertIsNone(meta["git_commit"])
        self.assertFalse(meta["committed"])

    def test_run_rearm_check_reports_git_spec_commit(self):
        res = run_rearm_check(
            config_specs=[f"current={self.PATH}", f"before_a2=git:{self.BEFORE}:{self.PATH}"],
            join_ms_list=[0.0],
            synthetic_only=True,
        )
        commit = res["configs"]["before_a2"]["git_commit"]
        self.assertTrue(commit and commit.startswith(self.BEFORE), commit)
        self.assertNotEqual(res["configs"]["current"]["git_commit"], "")

    def test_bad_specs_raise(self):
        from scripts.level1_rearm_check import resolve_config_spec
        for spec in ("no_equals_sign", "x=git:no_colon", "x=git:0000000:configs/level1_realtime.json"):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    resolve_config_spec(spec)


# ------------------------------------------------------------------ plan 15 lần sửa 4 §5 D3: AC-C1…C5 (--decoder)
# The streams, manifests and classifier results below are controlled synthetic data built in this test (dữ liệu tổng
# hợp có kiểm soát để kiểm logic, không phải dữ liệu thật); the fake classifiers are functions defined here.
import csv  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
from unittest import mock  # noqa: E402

import scripts.level1_rearm_check as rc  # noqa: E402
import scripts.level1_segment_report as sr  # noqa: E402

DEC_PARAMS = {"cls_window_ms": 200, "cls_conf": 0.9, "cls_stable_ms": 120, "hand_lost_ms": 300}
DT_C = 40.0


def _chain(blocks):
    """blocks: list of (source, n_frames, label_or_None_for_no_hand) -> seq_data with frame_sources and the label of
    every frame (the fake classifier reads the label of the window's last frame)."""
    srcs, labels, det = [], [], []
    for src, n, lab in blocks:
        srcs += [src] * n
        labels += [lab] * n
        det += [lab is not None] * n
    T = len(srcs)
    sd = {"raw": np.full((T, 21, 3), 0.5, np.float32), "detected": np.array(det, bool),
          "handedness": ["Right" if d else "" for d in det], "timestamps_ms": np.arange(T) * DT_C,
          "frame_sources": srcs, "width": 640, "height": 480, "fps": 25.0}
    return sd, labels


def _fake_classify(labels, ts_all):
    def classify(seg):
        i = int(np.where(np.abs(ts_all - seg.t_emit_ms) < 1e-6)[0][0])
        lab = labels[i]
        conf = 0.5 if lab == "low" else 0.95
        return {"status": "ok", "prediction": lab, "confidence": conf}
    return classify


class TestDecoderMetricsC1C2(unittest.TestCase):
    def _run(self, blocks, expected):
        sd, labels = _chain(blocks)
        dec = rc.decode_chain(sd, DEC_PARAMS, _fake_classify(labels, sd["timestamps_ms"]), 2)
        return dec, rc.strict_chain_metrics(dec["final"], sd["frame_sources"], expected)

    def test_c1_c2_join_and_wrong_label_are_garbage(self):
        dec, m = self._run([(0, 30, "a"), ("join", 10, "x"), (1, 30, "z"), (2, 30, "c")], ["a", "b", "c"])
        self.assertEqual([lab for _, lab in dec["final"]], ["a", "x", "z", "c"])
        self.assertEqual((m["n_clips"], m["n_one"], m["n_miss"], m["n_multi"], m["n_garbage"]), (3, 2, 1, 0, 2))
        self.assertTrue(m["order_ok"])
        self.assertEqual(m["edit_distance"], 2)          # [a, x, z, c] vs [a, b, c]
        tot = rc._sum_strict([m])
        self.assertAlmostEqual(tot["one_rate"], 2 / 3)
        self.assertAlmostEqual(tot["miss_rate"], 1 / 3)
        self.assertAlmostEqual(tot["garbage_per_clip"], 2 / 3)
        self.assertAlmostEqual(tot["token_error_rate"], 2 / 3)
        self.assertEqual(dec["n_append_after_lost"], 0)

    def test_c1_multi_needs_a_lost_hand_and_is_counted(self):
        dec, m = self._run([(0, 30, "a"), (1, 20, "b"), (1, 10, None), (1, 20, "b"), (2, 30, "c")],
                           ["a", "b", "c"])
        self.assertEqual([lab for _, lab in dec["final"]], ["a", "b", "b", "c"])
        self.assertEqual((m["n_one"], m["n_multi"], m["n_garbage"]), (2, 1, 0))
        self.assertEqual(dec["n_append_after_lost"], 1)  # G3 counts this emission
        self.assertEqual(rc._sum_strict([dict(m, hand_lost=dec["n_append_after_lost"])], ("hand_lost",))["hand_lost"], 1)

    def test_c1_replace_moves_the_last_emission(self):
        dec, m = self._run([(0, 10, "a"), (0, 20, "â"), (1, 30, "b")], ["â", "b"])
        self.assertEqual([lab for _, lab in dec["final"]], ["â", "b"])
        self.assertEqual(dec["n_replace"], 1)
        self.assertEqual([e["action"] for e in dec["emits"]], ["append", "replace", "append"])
        self.assertEqual((m["n_one"], m["n_garbage"]), (2, 0))

    def test_c1_low_confidence_and_order(self):
        dec, m = self._run([(0, 30, "a"), (1, 30, "low"), (2, 30, "c")], ["a", "b", "c"])
        self.assertEqual((m["n_one"], m["n_miss"], m["n_garbage"]), (2, 1, 0))
        m2 = rc.strict_chain_metrics([(35, "b"), (5, "a")], ["0"] * 0 + [0] * 30 + [1] * 30, ["a", "b"])
        self.assertFalse(m2["order_ok"])

    def test_decoder_gates(self):
        res = {"on": {c: {j: {"one_rate": 0.95, "multi_rate": 0.0, "hand_lost": 0, "order_ok": True,
                              "garbage_per_clip": 0.0} for j in ("0", "300", "600")} for c in ("L", "T", "O")}}
        single = {"on": {"letter": {"rate": 0.95}, "tone": {"rate": 0.80}},
                  "off": {"letter": {"rate": 0.96}, "tone": {"rate": 0.81}}}
        g = rc.evaluate_decoder_gates(res, single, "on", "off")
        self.assertTrue(g["all_pass"])
        self.assertIsNone(g["stop_point"])
        tone_bad = {"on": single["on"], "off": {"letter": {"rate": 0.96}, "tone": {"rate": 0.90}}}
        g = rc.evaluate_decoder_gates(res, tone_bad, "on", "off")
        self.assertEqual(g["failed"], ["G6"])
        self.assertTrue(g["only_g6_tone_failed"])
        self.assertIn("§7 item 2", g["stop_point"])
        res["on"]["L"]["300"]["garbage_per_clip"] = 0.06
        g = rc.evaluate_decoder_gates(res, single, "on", "off")
        self.assertEqual(g["failed"], ["G5"])
        self.assertFalse(g["only_g6_tone_failed"])
        self.assertIn("§7 item 1", g["stop_point"])
        res["on"]["L"]["300"]["garbage_per_clip"] = 0.05   # boundary inclusive
        res["on"]["L"]["0"]["one_rate"] = 0.90
        self.assertTrue(rc.evaluate_decoder_gates(res, single, "on", "off")["all_pass"])
        del res["on"]["L"]["600"]
        self.assertFalse(rc.evaluate_decoder_gates(res, single, "on", "off")["all_pass"])


VALUES_C = {"a": 0.1, "b": 0.3, "c": 0.5, "o": 0.7, "dấu sắc": 0.9}


class _FakeClassifier:
    """Defined in the test: the label is the symbol whose constant landmark value is nearest to the last hand frame of
    the segment; confidence 0.95."""
    min_detected_frames = 3

    def __init__(self):
        self.calls = 0

    def classify(self, segment, top_k):
        self.calls += 1
        last = segment.raw_landmarks[np.where(segment.detected)[0][-1]]
        v = float(last.mean())
        lab = min(VALUES_C, key=lambda s: abs(VALUES_C[s] - v))
        return {"status": "ok", "prediction": lab, "confidence": 0.95}


class TestDecoderRunC3C4(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vslt_d3_")
        rows = []
        for sym, num in (("a", "001"), ("b", "001"), ("c", "001"), ("o", "001"), ("o", "002"), ("dấu sắc", "001")):
            sid = f"hauuto_{'tone_s' if sym == 'dấu sắc' else sym}_s1_A_{num}"
            raws = np.full((40, 21, 3), VALUES_C[sym], np.float32)
            np.savez(os.path.join(self.tmp, f"{sid}.npz"), raw_landmarks=raws, detected_mask=np.ones(40, bool),
                     handedness_label=np.array(["Left"] * 40))
            rows.append({"sample_id": sid, "source": "hauuto", "symbol": sym, "signer_id": "s1",
                         "landmark_path": f"{sid}.npz", "width": 640, "height": 480, "fps": 25.0})
        self.manifest = os.path.join(self.tmp, "manifest.csv")
        with open(self.manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_c3_decoder_without_checkpoint_fails_clearly(self):
        cfg = "configs/level1_realtime.json"
        with self.assertRaises(ValueError) as cm:
            rc.run_rearm_check([f"off={cfg}"], [0.0], manifest_path=self.manifest, checkpoint_path=None,
                               min_detected_frames=3, decoder=True)
        self.assertIn("checkpoint", str(cm.exception))
        missing = os.path.join(self.tmp, "no_such.pt")
        with self.assertRaises(FileNotFoundError) as cm:
            rc.run_rearm_check([f"off={cfg}"], [0.0], manifest_path=self.manifest, checkpoint_path=missing,
                               decoder=True)
        self.assertIn("checkpoint", str(cm.exception))
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = rc.main(["--decoder", "--config", f"off={cfg}", "--join-ms", "0", "--manifest", self.manifest,
                            "--checkpoint", missing])
        self.assertEqual(code, 2)
        self.assertIn("checkpoint", err.getvalue())

    def test_c4_json_keys_and_run(self):
        fake = _FakeClassifier()
        rep = rc.run_rearm_check(
            config_specs=["off=configs/level1_realtime.json", "on=configs/level1_realtime.json"],
            join_ms_list=[0.0, 300.0, 600.0], manifest_path=self.manifest, checkpoint_path=None,
            overrides=['on:rearm_mode="classifier"'], gates=("on", "off"), decoder=True, classifier=fake,
            argv=["--test"])
        self.assertIsInstance(rep["generated_by"]["code_dirty"], bool)
        self.assertEqual(len(rep["configs"]["on"]["sha256"]), 64)
        self.assertIn("train clips concatenated", rep["note"])
        self.assertIn("not accuracy", rep["note"])
        self.assertEqual(rep["note_vi"], "chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác")
        self.assertIn("tham số D chọn sau thăm dò planner trên cùng chuỗi L — gate là kiểm logic",
                      rep["exploratory_params_note"])
        for k in ("segment", "garbage", "one_rate", "hand_lost", "single_clip", "qipedc_g7"):
            self.assertIn(k, rep["definitions"])
        self.assertEqual(rep["mode"], "decoder")
        self.assertEqual(rep["rearm_modes"], {"off": "motion_pose", "on": "classifier"})
        self.assertEqual(rep["configs"]["on"]["overrides"], {"rearm_mode": "classifier"})
        on_l0 = rep["results"]["on"]["L"]["0"]
        self.assertEqual(on_l0["n_clips"], 4)                 # a, b, c, o
        self.assertEqual(on_l0["one_rate"], 1.0)              # constant shapes: one label per clip
        self.assertEqual(on_l0["garbage_per_clip"], 0.0)
        self.assertEqual(on_l0["hand_lost"], 0)
        self.assertIn("strict", rep["results"]["off"]["L"]["0"])
        self.assertEqual(sorted(rep["gates"]["gates"]), ["G1", "G2", "G3", "G4", "G5", "G6"])
        self.assertIn("tone", rep["single_clip"]["on"])
        self.assertEqual(rep["single_clip"]["on"]["letter"]["rate"], 1.0)
        self.assertEqual(rep["qipedc_g7"]["n_clips"], 0)
        self.assertIn("on", rep["decoder_params"])
        self.assertGreater(fake.calls, 0)
        json.dumps(rep)


class TestWriteModeConfigC5(unittest.TestCase):
    """rearm_mode -> 'classifier' only from a committed, clean --decoder JSON whose gates all passed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=rc.ROOT, prefix="_tmp_d3_")  # inside the repo, untracked
        self.cfg = os.path.join(self.tmp, "config.json")
        shutil.copyfile(os.path.join(rc.ROOT, "configs", "level1_realtime.json"), self.cfg)
        with open(self.cfg, "rb") as f:
            self.cfg_bytes = f.read()
        self.js = os.path.join(self.tmp, "rearm_check_d4.json")
        self._write()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, all_pass=True, dirty=False, mode="decoder", gate_mode="classifier"):
        with open(self.js, "w", encoding="utf-8") as f:
            json.dump({"mode": mode, "generated_by": {"git_commit": "f" * 40, "code_dirty": dirty},
                       "rearm_modes": {"on": gate_mode, "off": "motion_pose"},
                       "gates": {"all_pass": all_pass, "gate_config": "on", "baseline_config": "off"}}, f)

    def _unchanged(self):
        with open(self.cfg, "rb") as f:
            self.assertEqual(f.read(), self.cfg_bytes)

    def test_c5_uncommitted_json_refused(self):
        with self.assertRaises(RuntimeError):
            rc.write_mode_config(self.cfg, self.js)
        self._unchanged()

    def test_c5_bad_reports_refused(self):
        for kw in ({"all_pass": False}, {"dirty": True}, {"mode": None}, {"gate_mode": "motion_pose"}):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                self._write(**kw)
                with mock.patch.object(sr, "committed_evidence_ref", return_value=("reports/x/d4.json", "abc1234")):
                    with self.assertRaises(RuntimeError):
                        rc.write_mode_config(self.cfg, self.js)
                self._unchanged()

    def test_c5_success_only_rearm_mode(self):
        with open(self.cfg, encoding="utf-8") as f:
            before = json.load(f)
        with mock.patch.object(sr, "committed_evidence_ref", return_value=("reports/x/d4.json", "abc1234")) as h:
            rc.write_mode_config(self.cfg, self.js)
        h.assert_called_once()
        with open(self.cfg, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual(list(after), list(before))
        self.assertEqual(after["rearm_mode"]["value"], "classifier")
        self.assertEqual(after["rearm_mode"]["source"], "design")
        self.assertIn("reports/x/d4.json@abc1234", after["rearm_mode"]["reason"])
        for k in before:
            if k != "rearm_mode":
                self.assertEqual(json.dumps(after[k], ensure_ascii=False), json.dumps(before[k], ensure_ascii=False), k)
        sr.validate_level1_config(after)
        self.assertIsNone(re.search(r"\bfake\b|\bmock\b", after["rearm_mode"]["reason"]))


# ----------------------------------------------------------------------------------------------------------------------
# Plan 15 lần sửa 5 (S1): --write-demo-config — AC-W1 (refusals), AC-W2 (success). The D4 JSON here is synthetic (G6 tone
# numbers 0.7123 / 0.8456 on purpose different from the real ones, so the test proves they are read from the JSON).
# ----------------------------------------------------------------------------------------------------------------------
DEMO_EXTRA_KEYS = ("rearm_mode", "_about", "_user_decision")


class TestWriteDemoConfigW1W2(unittest.TestCase):
    """configs/level1_demo_classifier.json only from a committed, clean --decoder JSON in which exactly G6 tones failed
    (lần sửa 4 §7 item 2, user decision (a)) and whose gate config is the current base config + rearm_mode classifier."""

    JSON_REF = ("reports/x/d4.json", "abc1234")
    BASE_COMMIT = "def5678"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=rc.ROOT, prefix="_tmp_s1_")  # inside the repo, untracked
        self.cfg = os.path.join(self.tmp, "config.json")
        shutil.copyfile(os.path.join(rc.ROOT, "configs", "level1_realtime.json"), self.cfg)
        with open(self.cfg, "rb") as f:
            self.cfg_bytes = f.read()
        self.cfg_rel = os.path.relpath(self.cfg, rc.ROOT).replace(os.sep, "/")
        self.js = os.path.join(self.tmp, "rearm_check_d4.json")
        self.out = os.path.join(self.tmp, "demo.json")
        self._write()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, all_pass=False, failed=("G6",), only_tone=True, letter_pass=True, tone_pass=False, dirty=False,
               mode="decoder", gate_mode="classifier", overrides=None, sha=None):
        g6 = {"letter": {"gate": 0.9512, "baseline": 0.8834, "pass": letter_pass},
              "tone": {"gate": 0.7123, "baseline": 0.8456, "pass": tone_pass}}
        rep = {"mode": mode, "generated_by": {"git_commit": "f" * 40, "code_dirty": dirty},
               "rearm_modes": {"on": gate_mode, "off": "motion_pose"},
               "configs": {"on": {"path": self.cfg_rel, "sha256": sha or rc.sha256_file(self.cfg), "committed": True,
                                  "overrides": {"rearm_mode": "classifier"} if overrides is None else overrides},
                           "off": {"path": self.cfg_rel, "sha256": rc.sha256_file(self.cfg), "committed": True}},
               "gates": {"all_pass": all_pass, "failed": list(failed), "only_g6_tone_failed": only_tone,
                         "gate_config": "on", "baseline_config": "off", "thresholds": {"G6_single_drop_max": 0.02},
                         "gates": {"G6": {"values": g6, "pass": letter_pass and tone_pass}}}}
        with open(self.js, "w", encoding="utf-8") as f:
            json.dump(rep, f)

    def _ref(self, path):
        full = os.path.abspath(path)
        if full == os.path.abspath(self.js):
            return self.JSON_REF
        if full == os.path.abspath(self.cfg):
            return self.cfg_rel, self.BASE_COMMIT
        raise AssertionError(f"unexpected committed_evidence_ref({path!r})")

    def _base_unchanged(self):
        with open(self.cfg, "rb") as f:
            self.assertEqual(f.read(), self.cfg_bytes)

    # --- AC-W1 -------------------------------------------------------------------------------------------------------
    def test_w1_uncommitted_json_refused(self):
        with self.assertRaises(RuntimeError):
            rc.write_demo_config(self.out, self.js)
        self.assertFalse(os.path.exists(self.out))
        self._base_unchanged()

    def test_w1_bad_reports_refused(self):
        cases = {
            "all_pass true (use --write-mode-config)": {"all_pass": True, "failed": (), "only_tone": False,
                                                       "tone_pass": True},
            "another gate failed": {"failed": ("G1", "G6"), "only_tone": False},
            "G6 letters failed": {"letter_pass": False, "only_tone": False},
            "G6 letters failed, flag still true": {"letter_pass": False},
            "G6 tones passed, flag still true": {"tone_pass": True},
            "code_dirty true": {"dirty": True},
            "not a --decoder report": {"mode": None},
            "gate config not classifier": {"gate_mode": "motion_pose"},
            "overrides other than rearm_mode": {"overrides": {"rearm_mode": "classifier", "cls_conf": 0.8}},
            "no override": {"overrides": {}},
            "base sha256 differs from the JSON": {"sha": "0" * 64},
        }
        for name, kw in cases.items():
            with self.subTest(case=name):
                self._write(**kw)
                with mock.patch.object(sr, "committed_evidence_ref", side_effect=self._ref):
                    with self.assertRaises(RuntimeError):
                        rc.write_demo_config(self.out, self.js)
                self.assertFalse(os.path.exists(self.out))
                self._base_unchanged()

    def test_w1_out_is_base_config_refused(self):
        with mock.patch.object(sr, "committed_evidence_ref", side_effect=self._ref):
            with self.assertRaises(RuntimeError):
                rc.write_demo_config(self.cfg, self.js)
        self._base_unchanged()

    def test_w1_dirty_base_config_refused(self):
        def ref(path):
            if os.path.abspath(path) == os.path.abspath(self.cfg):
                raise RuntimeError("evidence has uncommitted changes")
            return self._ref(path)
        with mock.patch.object(sr, "committed_evidence_ref", side_effect=ref):
            with self.assertRaises(RuntimeError):
                rc.write_demo_config(self.out, self.js)
        self.assertFalse(os.path.exists(self.out))
        self._base_unchanged()

    def test_w1_existing_out_untouched_on_refusal(self):
        with open(self.out, "wb") as f:
            f.write(b"{\"old\": true}\n")
        self._write(dirty=True)
        with mock.patch.object(sr, "committed_evidence_ref", side_effect=self._ref):
            with self.assertRaises(RuntimeError):
                rc.write_demo_config(self.out, self.js)
        with open(self.out, "rb") as f:
            self.assertEqual(f.read(), b"{\"old\": true}\n")
        self._base_unchanged()

    # --- AC-W2 -------------------------------------------------------------------------------------------------------
    def test_w2_success_only_rearm_mode_and_markers(self):
        with open(self.cfg, encoding="utf-8") as f:
            base = json.load(f)
        with mock.patch.object(sr, "committed_evidence_ref", side_effect=self._ref):
            res = rc.write_demo_config(self.out, self.js)
        self._base_unchanged()
        loaded = rc.load_level1_config(self.out)
        self.assertEqual(loaded["values"]["rearm_mode"], "classifier")
        demo = loaded["raw"]
        self.assertEqual(list(demo), ["_about", "_user_decision"] + [k for k in base if k != "_about"])
        for k in base:
            if k not in DEMO_EXTRA_KEYS:
                self.assertEqual(json.dumps(demo[k], ensure_ascii=False, sort_keys=True),
                                 json.dumps(base[k], ensure_ascii=False, sort_keys=True), k)
        rm = demo["rearm_mode"]
        self.assertEqual(rm["value"], "classifier")
        self.assertEqual(rm["source"], "design")
        for part in ("user decision (a)", "2026-10-05", "G6", "FAILED", "reports/x/d4.json@abc1234", "0.7123", "0.8456",
                     "0.02", "keys 1-5", "not a gate pass"):
            self.assertIn(part, rm["reason"])
        self.assertIsNone(re.search(r"\bfake\b|\bmock\b", rm["reason"]))
        ud = demo["_user_decision"]
        self.assertEqual(ud["choice"], "(a) classifier")
        self.assertEqual(ud["decided"], "2026-10-05")
        self.assertEqual(ud["recorded_in"], "docs/plans/15-progress.md (D4)")
        self.assertIn("docs/plans/15-lan-sua-5.md", ud["plans"])
        self.assertEqual(ud["gate_failed"], "G6 tone")
        self.assertEqual(ud["g6_tone"]["on"], 0.7123)
        self.assertEqual(ud["g6_tone"]["off"], 0.8456)
        self.assertIn("0.02", ud["g6_tone"]["rule"])
        self.assertEqual(ud["g6_letter"], {"on": 0.9512, "off": 0.8834})
        self.assertEqual(ud["evidence"], "reports/x/d4.json@abc1234")
        self.assertIn("not a gate pass", ud["note"])
        about = demo["_about"]
        sha = rc.sha256_file(self.cfg)
        for part in (self.cfg_rel, sha, self.BASE_COMMIT, "reports/x/d4.json@abc1234", "--write-demo-config",
                     "do not edit by hand", "motion_pose"):
            self.assertIn(part, about)
        self.assertEqual(res["base"], {"path": self.cfg_rel, "sha256": sha, "commit": self.BASE_COMMIT})
        self.assertEqual(res["rearm_mode"]["old"]["value"], "motion_pose")
        self.assertEqual(res["rearm_mode"]["new"], rm)

    def test_w2_cli(self):
        with mock.patch.object(sr, "committed_evidence_ref", side_effect=self._ref):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                code = rc.main(["--write-demo-config", self.out, "--rearm-json", self.js])
        self.assertEqual(code, 0)
        self.assertEqual(rc.load_level1_config(self.out)["values"]["rearm_mode"], "classifier")
        self.assertIn(rc.sha256_file(self.out), out.getvalue())
        self._base_unchanged()


# ----------------------------------------------------------------------------------------------------------------------
# Plan 15 lần sửa 5 (S2): AC-W3 — the real configs/level1_demo_classifier.json (generated by --write-demo-config at a
# clean commit) is tracked by git and is exactly the D4 'on' config: the default config + rearm_mode 'classifier'.
# If configs/level1_realtime.json changes later this test fails on purpose: run step D4 again, then the S2 command.
# ----------------------------------------------------------------------------------------------------------------------
import subprocess  # noqa: E402

DEMO_CONFIG_REL = "configs/level1_demo_classifier.json"
MAIN_CONFIG_REL = "configs/level1_realtime.json"


class TestDemoConfigFileW3(unittest.TestCase):
    def test_w3_demo_config_is_the_measured_d4_config(self):
        demo_path = os.path.join(rc.ROOT, DEMO_CONFIG_REL)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", DEMO_CONFIG_REL], cwd=rc.ROOT,
                                 capture_output=True, text=True)
        self.assertEqual(tracked.returncode, 0, f"{DEMO_CONFIG_REL} is not tracked by git")
        demo = rc.load_level1_config(demo_path)
        main = rc.load_level1_config(os.path.join(rc.ROOT, MAIN_CONFIG_REL))
        self.assertEqual(demo["values"]["rearm_mode"], "classifier")
        self.assertEqual(main["values"]["rearm_mode"], "motion_pose")      # the default config is not switched
        raw_d, raw_m = demo["raw"], main["raw"]
        self.assertEqual([k for k in raw_d if k not in DEMO_EXTRA_KEYS], [k for k in raw_m if k not in DEMO_EXTRA_KEYS])
        for k in raw_m:
            if k not in DEMO_EXTRA_KEYS:
                self.assertEqual(json.dumps(raw_d[k], ensure_ascii=False, sort_keys=True),
                                 json.dumps(raw_m[k], ensure_ascii=False, sort_keys=True), k)
        ud = raw_d["_user_decision"]
        ev_rel, ev_commit = ud["evidence"].rsplit("@", 1)
        self.assertEqual(sr.committed_evidence_ref(os.path.join(rc.ROOT, ev_rel)), (ev_rel, ev_commit))
        with open(os.path.join(rc.ROOT, ev_rel), encoding="utf-8") as f:
            rep = json.load(f)
        gates = rep["gates"]
        self.assertEqual(rep["mode"], "decoder")
        self.assertIs(rep["generated_by"]["code_dirty"], False)
        self.assertEqual(gates["failed"], ["G6"])
        self.assertIs(gates["only_g6_tone_failed"], True)
        measured = rep["configs"][gates["gate_config"]]
        self.assertEqual(measured["path"], MAIN_CONFIG_REL)
        self.assertEqual(measured["sha256"], main["sha256"])
        self.assertEqual(measured["overrides"], {"rearm_mode": "classifier"})
        g6 = gates["gates"]["G6"]["values"]
        self.assertEqual(ud["g6_tone"]["on"], g6["tone"]["gate"])
        self.assertEqual(ud["g6_tone"]["off"], g6["tone"]["baseline"])
        self.assertEqual(ud["g6_letter"], {"on": g6["letter"]["gate"], "off": g6["letter"]["baseline"]})
        self.assertEqual({k: ud[k] for k in rc.DEMO_DECISION}, rc.DEMO_DECISION)
        self.assertEqual(ud["gate_failed"], "G6 tone")
        self.assertIn(main["sha256"], raw_d["_about"])
        self.assertIn(ud["evidence"], raw_d["_about"])
        self.assertEqual(raw_d["rearm_mode"]["source"], "design")
        self.assertIn("user decision (a)", raw_d["rearm_mode"]["reason"])
        self.assertIn(ud["evidence"], raw_d["rearm_mode"]["reason"])


if __name__ == "__main__":
    unittest.main()
