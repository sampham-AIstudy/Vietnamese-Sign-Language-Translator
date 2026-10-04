"""
Plan 15 AC-R'1 (a-c): Tests for scripts/level1_segment_report.py.

Tests:
- R'1 (a): out-of-fold predictions from nested_predictions.csv recomputed per fold and in total
  match primary nested_report.json runs.frame.folds[i].tones.top1 (|diff| <= 1e-9) and
  summary.tones.mean.
- R'1 (b): motion profile on 2 fixed hauuto npz clips matches the exact Level1SignSegmenter.motion
  series obtained by pushing frame-by-frame.
- R'1 (c): rules 1-6 calculated correctly on controlled/synthetic series, including the 'no_motion'
  branch and the rule 6 triggered stop point.
"""
import csv
import json
import os
import shutil
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.level1_segment_report import (  # noqa: E402
    CONFIG, MANIFEST, PRIMARY_PREDICTIONS, PRIMARY_REPORT, TONES, VARIANTS_REPORT,
    calibrate, clip_timestamps, main, motion_profile, motion_series,
    nested_per_class, read_predictions, u1_summary, variants_summary,
)
from src.inference.level1_core import load_level1_config, validate_level1_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter  # noqa: E402


class TestNestedPerClass(unittest.TestCase):
    """AC-R'1 (a): out-of-fold tone metrics match nested_report.json."""

    def test_r_prime_1a_fold_top1_and_mean_match_report(self):
        self.assertTrue(os.path.exists(PRIMARY_REPORT), f"Missing {PRIMARY_REPORT}")
        self.assertTrue(os.path.exists(PRIMARY_PREDICTIONS), f"Missing {PRIMARY_PREDICTIONS}")

        with open(PRIMARY_REPORT, encoding="utf-8") as f:
            primary = json.load(f)
        pred_rows = read_predictions(PRIMARY_PREDICTIONS)

        res = nested_per_class(pred_rows, primary, run="frame")

        self.assertTrue(res["check"]["matches"])
        self.assertLessEqual(res["check"]["fold_tones_top1_max_abs_diff"], 1e-9)
        self.assertLessEqual(res["check"]["tones_mean_abs_diff"], 1e-9)
        self.assertEqual(res["check"]["rows_outside_report_folds"], 0)

        # 4 folds corresponding to the 4 test signers
        self.assertEqual(len(res["folds"]), 4)
        for fold in res["folds"]:
            signer = fold["test_signer"]
            tones = fold["tones"]
            self.assertIsNotNone(tones["top1"])
            self.assertAlmostEqual(tones["top1"], tones["report_top1"], delta=1e-9,
                                   msg=f"Fold {signer} tones top-1 mismatch")

    def test_r_prime_1a_per_class_counts(self):
        with open(PRIMARY_REPORT, encoding="utf-8") as f:
            primary = json.load(f)
        pred_rows = read_predictions(PRIMARY_PREDICTIONS)
        res = nested_per_class(pred_rows, primary, run="frame")

        total = res["total"]
        # n = 120 tone clips in total (24 per tone, 6 per signer)
        self.assertEqual(total["tones"]["n"], 120)
        self.assertEqual(total["tones"]["correct"], 49)

        per_class = total["per_class"]
        for t in TONES:
            self.assertIn(t, per_class)
            self.assertEqual(per_class[t]["n"], 24)

        # Plan 15 §2.1 expected counts:
        # huyền 2/24, nặng 18/24, hỏi 8/24, sắc 10/24, ngã 11/24
        self.assertEqual(per_class["dấu huyền"]["correct"], 2)
        self.assertEqual(per_class["dấu nặng"]["correct"], 18)
        self.assertEqual(per_class["dấu hỏi"]["correct"], 8)
        self.assertEqual(per_class["dấu sắc"]["correct"], 10)
        self.assertEqual(per_class["dấu ngã"]["correct"], 11)


class TestMotionProfiles(unittest.TestCase):
    """AC-R'1 (b): motion series matches Level1SignSegmenter.motion frame-by-frame."""

    def test_r_prime_1b_motion_series_matches_segmenter_push(self):
        cfg = load_level1_config(CONFIG)
        params = cfg["values"]
        min_det = 10
        base = os.path.dirname(MANIFEST)

        # Select 2 fixed npz files from manifest: 1 letter clip, 1 tone clip
        clip_paths = [
            ("hauuto_a_hau_A_001", "hauuto_hau/hauuto_a_hau_A_001.npz"),
            ("hauuto_tone_s_hau_A_001", "hauuto_hau/hauuto_tone_s_hau_A_001.npz"),
        ]

        with open(MANIFEST, encoding="utf-8") as f:
            manifest_rows = {r["sample_id"]: r for r in csv.DictReader(f)}

        for sample_id, rel_path in clip_paths:
            self.assertIn(sample_id, manifest_rows)
            r = manifest_rows[sample_id]
            npz_path = os.path.join(base, rel_path)
            self.assertTrue(os.path.exists(npz_path), f"Missing npz {npz_path}")

            with np.load(npz_path) as z:
                raw = np.asarray(z["raw_landmarks"], dtype=np.float32)
                det = np.asarray(z["detected_mask"], dtype=bool)
                hand = [str(h) for h in z["handedness_label"]]

            w, h, fps = int(r["width"]), int(r["height"]), float(r["fps"])
            ts = clip_timestamps(len(det), fps)

            # Method 1: motion_series function
            series_from_func = motion_series(raw, det, hand, w, h, ts, params, min_det)

            # Method 2: push frame-by-frame on a fresh segmenter
            seg = Level1SignSegmenter(params, min_det)
            series_from_push = []
            for i, t in enumerate(ts):
                lms = raw[i] if bool(det[i]) else None
                seg.push(float(t), lms, str(hand[i]) if bool(det[i]) else "", w, h)
                series_from_push.append(None if seg.motion is None else float(seg.motion))

            self.assertEqual(len(series_from_func), len(series_from_push))
            self.assertEqual(series_from_func, series_from_push,
                             f"motion_series mismatch on clip {sample_id}")

            # Verify motion_profile produces valid dict
            prof = motion_profile(ts, series_from_func, still_speed=params["still_speed"],
                                  move_speed=params["move_speed"])
            self.assertIn("duration_ms", prof)
            self.assertIn("longest_still_ms", prof)
            self.assertIn("no_motion", prof)
            self.assertAlmostEqual(prof["duration_ms"], ts[-1] - ts[0], delta=1e-5)


class TestCalibrationRules(unittest.TestCase):
    """AC-R'1 (c): rules 1-6 calculated correctly on controlled/synthetic series."""

    def test_r_prime_1c_calibration_synthetic_clean(self):
        # Controlled timestamps: 10 frames spaced by 100 ms (0, 100, ..., 900)
        ts = [float(i * 100) for i in range(10)]
        design = {"move_over_still_ratio": 2.0, "hold_ms_design": 400.0}

        # 3 letter clips, 2 tone clips
        # Letters have steady motion = 0.5 (median = 0.5)
        # still_speed = p90([0.5, 0.5, 0.5]) = 0.5, move_speed = 1.0
        # All letter frames have motion <= 0.5 -> longest_still_ms = 900 ms -> hold_ms = min(400.0, 900.0) = 400.0 ms.
        clips = [
            {"kind": "letter", "symbol": "a", "timestamps_ms": ts,
             "motion": [0.5] * 10},
            {"kind": "letter", "symbol": "b", "timestamps_ms": ts,
             "motion": [0.5] * 10},
            {"kind": "letter", "symbol": "c", "timestamps_ms": ts,
             "motion": [0.5] * 10},
            # Tone 1: starts moving at frame 2 (ts=200), stops at frame 5 (ts=500)
            # motion at frames 2, 5 >= move_speed (2.0 >= 1.0)
            # internal frames 3, 4: motion <= still_speed (longest internal still = 100 ms)
            {"kind": "tone", "symbol": "dấu sắc", "timestamps_ms": ts,
             "motion": [0.5, 0.5, 2.0, 0.5, 0.5, 2.0, 0.5, 0.5, 0.5, 0.5]},
            # Tone 2: motion 2.0 at frame 2, 2.0 at frame 6, internal still = 200 ms
            {"kind": "tone", "symbol": "dấu huyền", "timestamps_ms": ts,
             "motion": [0.5, 0.5, 2.0, 0.5, 0.5, 0.5, 2.0, 0.5, 0.5, 0.5]},
        ]

        cal = calibrate(clips, design)
        vals = cal["values"]

        self.assertAlmostEqual(vals["still_speed"], 0.5)
        self.assertAlmostEqual(vals["move_speed"], 1.0)

        # hold_ms should be min(400.0, p10 of letter clips longest_still_ms) = 400.0
        self.assertEqual(vals["hold_ms"], 400.0)

        # max_segment_ms is ceil(p95(duration_ms)) = ceil(900.0) = 900
        self.assertEqual(vals["max_segment_ms"], 900)

        # rule 6 should not be triggered here (internal still <= 200 ms < 400 ms)
        self.assertFalse(cal["rule6"]["triggered"])

    def test_r_prime_1c_calibration_no_motion(self):
        ts = [float(i * 100) for i in range(5)]
        design = {"move_over_still_ratio": 2.0, "hold_ms_design": 400.0}

        # Letter and tone clips with a mix of moving and no_motion clips
        clips = [
            {"kind": "letter", "symbol": "a", "timestamps_ms": ts, "motion": [1.0, 4.0, 4.0, 1.0, 1.0]},
            {"kind": "letter", "symbol": "b", "timestamps_ms": ts, "motion": [0.5] * 5},
            {"kind": "tone", "symbol": "dấu sắc", "timestamps_ms": ts, "motion": [0.5] * 5},
            {"kind": "tone", "symbol": "dấu huyền", "timestamps_ms": ts, "motion": [1.0, 4.0, 4.0, 1.0, 1.0]},
        ]

        cal = calibrate(clips, design)
        # Verify no crash, no_motion handled cleanly
        self.assertEqual(cal["rule6"]["n_tone_clips_no_motion"], 1)
        self.assertEqual(cal["rule6"]["n_tone_clips_with_motion"], 1)

    def test_r_prime_1c_calibration_rule6_triggered(self):
        # Tone clip with internal still >= hold_ms
        # ts: 0, 100, 200, 300, 400, 500, 600, 700, 800, 900 (step 100ms)
        ts = [float(i * 100) for i in range(10)]
        design = {"move_over_still_ratio": 2.0, "hold_ms_design": 250.0}

        # Letters have no still frames (all moving) or short still run (100 ms)
        # hold_ms = min(250.0, p10_still)
        clips = [
            {"kind": "letter", "symbol": "a", "timestamps_ms": ts, "motion": [1.0] * 10},
            {"kind": "letter", "symbol": "b", "timestamps_ms": ts, "motion": [1.0] * 10},
            # Tone clip: first move at ts=100 (6.0), last move at ts=800 (6.0).
            # From ts=200 to ts=700 (500 ms run): motion 1.0 <= still_speed (internal still = 500 ms)
            {"kind": "tone", "symbol": "dấu sắc", "timestamps_ms": ts,
             "motion": [1.0, 6.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 6.0, 1.0]},
        ]

        cal = calibrate(clips, design)
        # internal still of tone = 500 ms >= hold_ms (<= 250 ms) -> triggered!
        self.assertTrue(cal["rule6"]["triggered"])


class TestVariantsAndU1(unittest.TestCase):
    """Tests for variants summary and U1 aggregation."""

    def test_variants_summary_reads_file(self):
        self.assertTrue(os.path.exists(VARIANTS_REPORT), f"Missing {VARIANTS_REPORT}")
        res = variants_summary(VARIANTS_REPORT)

        self.assertIn("path", res)
        self.assertIn("sha256", res)
        self.assertEqual(len(res["sha256"]), 64)
        self.assertIn("variants", res)
        for v in ("frame", "time", "frame_traj", "time_traj"):
            self.assertIn(v, res["variants"])
            self.assertIn("tones", res["variants"][v])
            self.assertIn("letters", res["variants"][v])
            self.assertIn("mean", res["variants"][v]["tones"])
            self.assertIn("sd", res["variants"][v]["tones"])

    def test_u1_summary(self):
        u1_path = os.path.join(PROJECT_ROOT, "_work", "_plan15_u1", "u1_2026-10-03_1650.json")
        if not os.path.exists(u1_path):
            self.skipTest(f"U1 file {u1_path} not found")

        res = u1_summary(u1_path)
        self.assertFalse(res["copied"])
        self.assertEqual(len(res["sha256"]), 64)
        self.assertEqual(res["n_segments"], 105)
        self.assertIn("duration_ms", res)
        self.assertIn("close_reason", res)
        self.assertIn("accepted", res)
        self.assertIn("session_max_segment_ms", res)
        self.assertIsNotNone(res["n_segments_at_cap"])


class TestWriteConfig(unittest.TestCase):
    """AC-R'1 (d): --write-config only updates 5 keys, source matches pattern."""

    def test_r_prime_1d_write_config(self):
        evidence_path = os.path.join(PROJECT_ROOT, "reports", "level1_realtime_2026-10-03", "tone_evidence.json")
        self.assertTrue(os.path.exists(evidence_path), f"Missing {evidence_path}")
        with open(evidence_path, encoding="utf-8") as f:
            evidence = json.load(f)
        cal_values = evidence["calibration"]["values"]

        tmp_dir = os.path.join(PROJECT_ROOT, "_work", "_plan15_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_cfg = os.path.join(tmp_dir, "test_write_config.json")
        shutil.copyfile(CONFIG, tmp_cfg)

        try:
            ret = main(["--write-config", tmp_cfg, "--evidence-json", evidence_path])
            self.assertEqual(ret, 0)

            with open(tmp_cfg, encoding="utf-8") as f:
                updated = json.load(f)
            with open(CONFIG, encoding="utf-8") as f:
                original = json.load(f)

            cal_keys = {"still_speed", "move_speed", "hold_ms", "max_segment_ms", "tail_still_keep_ms"}
            # Check the 5 calibrated keys
            for k in cal_keys:
                self.assertIn(k, updated)
                self.assertEqual(updated[k]["value"], cal_values[k])
                self.assertTrue(
                    updated[k]["source"].startswith("calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@"),
                    f"Unexpected source for {k}: {updated[k]['source']}",
                )
                self.assertEqual(updated[k]["reason"], original[k]["reason"])

            # Check all other keys are unchanged
            other_keys = set(original.keys()) - cal_keys
            for k in other_keys:
                self.assertEqual(updated[k], original[k], f"Key {k} was unexpectedly modified")

            # Validate the updated config
            val = validate_level1_config(updated)
            for k in cal_keys:
                self.assertEqual(val[k], cal_values[k])
        finally:
            if os.path.exists(tmp_cfg):
                os.remove(tmp_cfg)


EVIDENCE_REL = "reports/level1_realtime_2026-10-03/tone_evidence.json"
CAL_KEYS = ("still_speed", "move_speed", "hold_ms", "max_segment_ms", "tail_still_keep_ms")
A2_CONFIG_COMMIT = "b0620a9"  # `15: A2 config hiệu chỉnh` (plan 15 lần sửa 2 AC-W3)


def _git_text(*args):
    """git output; a missing commit (shallow clone) FAILS the caller, it is never skipped."""
    import subprocess
    r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


class TestWriteConfigA2b(unittest.TestCase):
    """plan 15 lần sửa 2 §4 AC-W1..W3 (step A2b): no hand-typed commit, rule reasons, values of b0620a9. Uses temporary
    config / evidence copies; configs/level1_realtime.json is never written by these tests."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(dir=PROJECT_ROOT, prefix="_tmp_a2b_")  # inside the repo, untracked
        self.cfg = os.path.join(self.tmp, "config.json")
        shutil.copyfile(CONFIG, self.cfg)
        with open(self.cfg, "rb") as f:
            self.cfg_bytes = f.read()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cfg_unchanged(self):
        with open(self.cfg, "rb") as f:
            self.assertEqual(f.read(), self.cfg_bytes, "config must not be written when write_config fails")

    def test_w1_uncommitted_evidence_raises_and_keeps_config(self):
        from scripts.level1_segment_report import write_config
        ev = os.path.join(self.tmp, "tone_evidence.json")
        shutil.copyfile(os.path.join(PROJECT_ROOT, EVIDENCE_REL), ev)  # untracked copy, has generated_by.git_commit
        with open(ev, encoding="utf-8") as f:
            self.assertTrue(json.load(f)["generated_by"]["git_commit"])  # a fallback would have something to use
        with self.assertRaises(RuntimeError):
            write_config(self.cfg, ev)
        self._cfg_unchanged()

    def test_w1_dirty_evidence_raises_and_keeps_config(self):
        from unittest import mock
        import scripts.level1_segment_report as sr
        real_git = sr._git

        def git_dirty(*args):
            if args[:1] == ("status",):
                return f" M {EVIDENCE_REL}"
            return real_git(*args)
        with mock.patch.object(sr, "_git", side_effect=git_dirty):
            with self.assertRaises(RuntimeError):
                sr.write_config(self.cfg, EVIDENCE_REL)
        self._cfg_unchanged()

    def test_w1_no_hand_typed_commit_in_scripts(self):
        for root, _, files in os.walk(os.path.join(PROJECT_ROOT, "scripts")):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                        self.assertNotIn("1ca53f3", f.read(), name)

    def test_w2_rule_reasons_and_other_keys_byte_identical(self):
        import re
        from scripts.level1_segment_report import CALIBRATION_REASONS, write_config
        with open(self.cfg, encoding="utf-8") as f:
            before = json.load(f)
        write_config(self.cfg, EVIDENCE_REL)
        with open(self.cfg, encoding="utf-8") as f:
            after = json.load(f)
        old_design = json.loads(_git_text("show", f"{A2_CONFIG_COMMIT}:configs/level1_realtime.json"))
        self.assertEqual(set(CALIBRATION_REASONS), set(CAL_KEYS))
        for k in CAL_KEYS:
            reason = after[k]["reason"]
            self.assertEqual(reason, CALIBRATION_REASONS[k], k)
            self.assertIsNone(re.search(r"\d", reason), f"{k}: reason must not contain a digit: {reason!r}")
            self.assertNotEqual(reason, old_design[k]["reason"], f"{k}: the old design reason must be gone")
        self.assertEqual(list(after), list(before))
        for k in before:
            if k not in CAL_KEYS:
                self.assertEqual(json.dumps(after[k], ensure_ascii=False), json.dumps(before[k], ensure_ascii=False), k)

    def test_w3_values_and_source_equal_b0620a9(self):
        from scripts.level1_segment_report import write_config
        write_config(self.cfg, EVIDENCE_REL)
        with open(self.cfg, encoding="utf-8") as f:
            after = json.load(f)
        a2 = json.loads(_git_text("show", f"{A2_CONFIG_COMMIT}:configs/level1_realtime.json"))
        full = _git_text("log", "-1", "--format=%H", "--", EVIDENCE_REL).strip()
        short = _git_text("rev-parse", "--short=7", full).strip()
        for k in CAL_KEYS:
            self.assertEqual(json.dumps(after[k]["value"]), json.dumps(a2[k]["value"]), k)
            self.assertEqual(after[k]["source"], f"calibrated: {EVIDENCE_REL}@{short}", k)
            self.assertEqual(after[k]["source"], a2[k]["source"], k)


if __name__ == "__main__":
    unittest.main()
