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
                                          **{k: FILL_RULES[k] for k in R1_KEYS}})
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


if __name__ == "__main__":
    unittest.main()
