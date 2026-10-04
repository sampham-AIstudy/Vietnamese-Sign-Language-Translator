"""
Plan 15 lần sửa 3 §3.4 / §5 (R2): pose evidence (rules P1, P2) and --write-pose-config — AC-RP1 … AC-RP4.

The clips below are controlled landmark sequences built in this test to check the calibration logic; they are not real
data (chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ liệu thật). Expected values are computed with the
by-hand formulas of tests/test_level1_rearm.py (normalized_by_hand / pose_distance_by_hand), not with the functions
under test. The real pose_evidence.json needs the gitignored landmark data and is produced by the script, not here.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import scripts.level1_segment_report as sr  # noqa: E402
import src.inference.level1_segmenter as seg_mod  # noqa: E402
from tests.test_level1_rearm import (  # noqa: E402
    DIR, H, PARAMS_RA, W, normalized_by_hand, pose_distance_by_hand, shape,
)

DT = 40.0
FPS = 1000.0 / DT
PARAMS = {**PARAMS_RA, "pose_change_rules": False}
MIN_DET = 3
JIT = 0.01  # shape jitter of the still clips: consecutive frames 2 * JIT apart -> shape speed 0.5 <= still 1.0


def still_clip(sample_id, symbol, signer, base, n=20, kind="letter"):
    """Hand at shape `base` (pose distance from A along DIR) with an alternating +/- JIT shape jitter along another
    direction: M_t <= still_speed from frame 1 on (frame 0 has no motion value), so the still run is frames 1..n-1."""
    other = np.roll(DIR, 3, axis=0)
    other[0] = 0.0
    other[9] = 0.0
    raws = []
    for k in range(n):
        base_raw = shape(base).astype(np.float64)
        jit = shape(JIT if k % 2 else -JIT, direction=other).astype(np.float64) - shape(0.0).astype(np.float64)
        raws.append((base_raw + jit).astype(np.float32))
    return {"sample_id": sample_id, "symbol": symbol, "kind": kind, "signer_id": signer, "raw": np.stack(raws),
            "detected": np.ones(n, dtype=bool), "handedness": ["Left"] * n, "width": W, "height": H, "fps": FPS}


def moving_clip(sample_id, symbol, signer, n=20):
    """Wrist moving fast the whole clip (M_t >= move_speed): no still frame."""
    raws = [shape(0.0, wrist_y=0.6 * k * DT / 1000.0) for k in range(n)]
    return {"sample_id": sample_id, "symbol": symbol, "kind": "letter", "signer_id": signer, "raw": np.stack(raws),
            "detected": np.ones(n, dtype=bool), "handedness": ["Left"] * n, "width": W, "height": H, "fps": FPS}


def expected_profile(clip):
    """Run = frames 1..n-1 (see still_clip); ref = mean N; jitter = p95 of the distances to ref (by hand)."""
    ns = [normalized_by_hand(lm) for lm in clip["raw"][1:]]
    ref = np.mean(ns, axis=0)
    d = [float(np.mean(np.linalg.norm(n - ref, axis=-1))) for n in ns]
    return ref, float(np.percentile(d, 95))


class TestSharedFunctionsRA9(unittest.TestCase):
    """AC-RA9 (script side): the script uses the segmenter's pose_distance and computes N as the segmenter does."""

    def test_script_uses_segmenter_pose_distance(self):
        self.assertIs(sr.pose_distance, seg_mod.pose_distance)

    def test_hand_shape_equals_segmenter_n(self):
        seg = seg_mod.Level1SignSegmenter(PARAMS, MIN_DET)
        for k, lm in enumerate([shape(0.0), shape(0.3), shape(-0.2)]):
            seg.push(k * DT, lm, "Left", W, H)
            self.assertTrue(np.array_equal(sr.hand_shape(lm, W, H), seg._prev[1]))
            self.assertEqual(sr.hand_shape(lm, W, H).dtype, seg._prev[1].dtype)

    def test_longest_still_run_matches_longest_run(self):
        rng = np.random.default_rng(7)
        for _ in range(200):
            n = int(rng.integers(1, 30))
            ts = np.cumsum(rng.uniform(10.0, 60.0, size=n))
            flags = list(rng.random(n) < 0.6)
            run = sr.longest_still_run(ts, flags)
            if not any(flags):
                self.assertIsNone(run)
                continue
            i0, i1 = run
            self.assertTrue(all(flags[i0:i1 + 1]))
            self.assertEqual(float(ts[i1]) - float(ts[i0]), sr._longest_run(ts, flags))


class TestPoseRulesRP1(unittest.TestCase):
    """AC-RP1: P1 / P2 on controlled clips match the by-hand values; a clip without a still frame is counted apart."""

    def test_rp1_clip_profile(self):
        clip = still_clip("hauuto_b_s1_A_001", "b", "s1", 0.3)
        prof = sr.clip_pose_profile(clip, PARAMS, MIN_DET)
        ref, jitter = expected_profile(clip)
        self.assertTrue(prof["has_still"])
        self.assertEqual(prof["run_hand_frames"], 19)
        self.assertEqual(prof["session"], "A")
        self.assertTrue(np.allclose(prof["ref"], ref, atol=1e-6))
        self.assertAlmostEqual(prof["jitter_clip"], jitter, places=6)
        self.assertGreater(jitter, 0.0)
        moving = sr.clip_pose_profile(moving_clip("hauuto_c_s1_A_001", "c", "s1"), PARAMS, MIN_DET)
        self.assertFalse(moving["has_still"])
        self.assertIsNone(moving["jitter_clip"])

    def test_rp1_p1_p2_values(self):
        # signer s1: classes a (0.0), b (0.3), c (no still frame: moving); signer s2: a (0.0), b (0.01), d (0.6);
        # a second, later clip of a for s1 (not the smallest sample_id: not used by P2); one tone clip (not a letter)
        clips = [still_clip("hauuto_a_s1_A_001", "a", "s1", 0.0), still_clip("hauuto_a_s1_A_002", "a", "s1", 0.9),
                 still_clip("hauuto_b_s1_A_001", "b", "s1", 0.3), moving_clip("hauuto_c_s1_A_001", "c", "s1"),
                 still_clip("hauuto_a_s2_A_001", "a", "s2", 0.0), still_clip("hauuto_b_s2_A_001", "b", "s2", 0.01),
                 still_clip("hauuto_d_s2_A_001", "d", "s2", 0.6),
                 still_clip("hauuto_tone_s_s1_A_001", "dấu sắc", "s1", 0.4, kind="tone")]
        ratio = 2.0
        profiles = [sr.clip_pose_profile(c, PARAMS, MIN_DET) for c in clips]
        ev = sr.pose_calibration(profiles, ratio)
        letters = [c for c in clips if c["kind"] == "letter" and c["symbol"] != "c"]
        jitters = [expected_profile(c)[1] for c in letters]
        expected_dist = ratio * float(np.percentile(jitters, 95))
        self.assertAlmostEqual(ev["values"]["rearm_pose_dist"], expected_dist, places=6)
        self.assertEqual(ev["inputs"]["n_letter_clips"], 7)
        self.assertEqual(ev["inputs"]["n_letter_clips_with_still"], 6)
        self.assertEqual(ev["inputs"]["letter_clips_without_still"], ["hauuto_c_s1_A_001"])
        # P2 pairs: s1/A: (a, b) [c has no ref]; s2/A: (a, b), (a, d), (b, d)
        refs = {(c["signer_id"], c["symbol"]): expected_profile(c)[0] for c in letters
                if c["sample_id"] != "hauuto_a_s1_A_002"}
        pairs = [("s1", "a", "b"), ("s2", "a", "b"), ("s2", "a", "d"), ("s2", "b", "d")]
        between = {p: float(np.mean(np.linalg.norm(refs[(p[0], p[1])] - refs[(p[0], p[2])], axis=-1))) for p in pairs}
        self.assertEqual(ev["p2"]["n_pairs"], 4)
        below = sorted(p for p in pairs if between[p] < expected_dist)
        self.assertAlmostEqual(ev["p2"]["coverage"], 1.0 - len(below) / 4.0, places=12)
        self.assertEqual(ev["p2"]["classes_without_ref"], [{"signer_id": "s1", "session": "A", "symbol": "c"}])
        got_below = {(tuple(b["pair"])): b for b in ev["p2"]["pairs_below"]}
        exp_below = {}
        for s, a, b in below:
            exp_below.setdefault((a, b), set()).add(s)
        self.assertEqual(set(got_below), set(exp_below))
        for k, signers in exp_below.items():
            self.assertEqual(got_below[k]["n_signers"], len(signers))
            self.assertEqual(got_below[k]["signers"], sorted(signers))
        # the (a, b) pair of s2 is 0.01 apart, below 2 x the jitter (about 0.01): below the threshold by construction
        self.assertIn(("a", "b"), got_below)
        self.assertEqual(ev["p2"]["stop_rule"]["threshold"], 0.80)
        self.assertEqual(ev["p2"]["stop_rule"]["triggered"], ev["p2"]["coverage"] < 0.80)

    def test_rp1_no_letter_with_still_frame_raises(self):
        profiles = [sr.clip_pose_profile(moving_clip("hauuto_c_s1_A_001", "c", "s1"), PARAMS, MIN_DET)]
        with self.assertRaises(ValueError):
            sr.pose_calibration(profiles, 2.0)


class TestPoseReportRP3(unittest.TestCase):
    """AC-RP3: the pose evidence JSON carries generated_by (code_dirty), sha256 of manifest + config, definitions,
    coverage, the pairs below the threshold and the 'not accuracy' sentence."""

    def test_rp3_report_keys(self):
        tmp = tempfile.mkdtemp(prefix="vslt_rp3_")
        try:
            manifest = os.path.join(tmp, "manifest.csv")
            with open(manifest, "w", encoding="utf-8") as f:
                f.write("sample_id\n")
            clips = [still_clip("hauuto_a_s1_A_001", "a", "s1", 0.0), still_clip("hauuto_b_s1_A_001", "b", "s1", 0.3)]
            rep = sr.pose_report(["--pose-evidence", "--out", "x.json"], sr.CONFIG, manifest,
                                 {"n_manifest_hauuto": 2, "clips": clips, "excluded": []}, MIN_DET)
            self.assertEqual(rep["note"], "train data of the deployed checkpoint; not accuracy")
            for k in ("command", "git_commit", "code_dirty", "code_paths"):
                self.assertIn(k, rep["generated_by"])
            self.assertIn(rep["generated_by"]["code_dirty"], (True, False))
            self.assertEqual(len(rep["manifest"]["sha256"]), 64)
            self.assertEqual(len(rep["config"]["sha256"]), 64)
            self.assertIn("pose_over_jitter_ratio", rep["config"])
            for k in ("coverage", "n_pairs", "pairs_below", "between", "stop_rule"):
                self.assertIn(k, rep["calibration"]["p2"])
            self.assertIn("jitter_clip", rep["calibration"]["p1"])
            self.assertIn("rearm_pose_dist", rep["calibration"]["values"])
            self.assertIn("P1", rep["definitions"])
            self.assertEqual(rep["train_clips"]["n_clips"], 2)
            json.dumps(rep)  # serialisable: no numpy array left
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestWritePoseConfigRP2(unittest.TestCase):
    """AC-RP2: --write-pose-config refuses an uncommitted / dirty evidence (config unchanged byte for byte); on
    success only rearm_pose_dist changes (value, source with the commit read through the A2b helper, reason without a
    digit). AC-RP4: the A2b helper is reused, not copied."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=PROJECT_ROOT, prefix="_tmp_rp2_")  # inside the repo, untracked
        self.cfg = os.path.join(self.tmp, "config.json")
        shutil.copyfile(sr.CONFIG, self.cfg)
        with open(self.cfg, "rb") as f:
            self.cfg_bytes = f.read()
        self.ev = os.path.join(self.tmp, "pose_evidence.json")
        self._write_ev(0.123456, False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_ev(self, value, triggered):
        with open(self.ev, "w", encoding="utf-8") as f:
            json.dump({"calibration": {"values": {"rearm_pose_dist": value},
                                       "p2": {"coverage": 0.9, "stop_rule": {"threshold": 0.80,
                                                                             "triggered": triggered}}}}, f)

    def _unchanged(self):
        with open(self.cfg, "rb") as f:
            self.assertEqual(f.read(), self.cfg_bytes)

    def test_rp2_uncommitted_evidence(self):
        with self.assertRaises(RuntimeError):
            sr.write_pose_config(self.cfg, self.ev)
        self._unchanged()

    def test_rp2_dirty_evidence(self):
        real_git = sr._git

        def git_dirty(*args):
            if args[:1] == ("ls-files",):
                return "tracked"
            if args[:1] == ("status",):
                return " M x"
            return real_git(*args)
        with mock.patch.object(sr, "_git", side_effect=git_dirty):
            with self.assertRaises(RuntimeError):
                sr.write_pose_config(self.cfg, self.ev)
        self._unchanged()

    def test_rp2_p2_stop_refuses(self):
        self._write_ev(0.123456, True)
        with mock.patch.object(sr, "committed_evidence_ref", return_value=("reports/x/pose_evidence.json", "abc1234")):
            with self.assertRaises(RuntimeError):
                sr.write_pose_config(self.cfg, self.ev)
        self._unchanged()

    def test_rp2_success_only_rearm_pose_dist(self):
        with open(self.cfg, encoding="utf-8") as f:
            before = json.load(f)
        with mock.patch.object(sr, "committed_evidence_ref",
                               return_value=("reports/x/pose_evidence.json", "abc1234")) as helper:
            sr.write_pose_config(self.cfg, self.ev)
        helper.assert_called_once()
        self.assertEqual(os.path.abspath(helper.call_args[0][0]), os.path.abspath(self.ev))
        with open(self.cfg, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual(list(after), list(before))
        entry = after["rearm_pose_dist"]
        self.assertEqual(entry["value"], 0.123456)
        self.assertEqual(entry["source"], "calibrated: reports/x/pose_evidence.json@abc1234")
        self.assertEqual(entry["reason"], sr.POSE_REASON)
        self.assertIsNone(re.search(r"\d", entry["reason"]))
        for k in before:
            if k != "rearm_pose_dist":
                self.assertEqual(json.dumps(after[k], ensure_ascii=False), json.dumps(before[k], ensure_ascii=False), k)
        sr.validate_level1_config(after)


if __name__ == "__main__":
    unittest.main()
