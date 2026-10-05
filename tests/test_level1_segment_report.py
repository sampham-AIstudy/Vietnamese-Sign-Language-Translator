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



# ------------------------------------------------------------------------------ plan 15 step A3 (--segment-check)
BEFORE_CONFIG_COMMIT = "3ebc7b9"  # configs/level1_realtime.json before the A2 calibration (plan 15 lần sửa 2 §5)
A3_CLIP_IDS = ("hauuto_a_hau_A_001", "hauuto_tone_s_hau_A_001", "hauuto_b_khoi_A_001")
A3_REPORT_DIR = "reports/level1_realtime_2026-10-05"


def _temp_manifest(tmp_dir, sample_ids):
    """Manifest with only the given hauuto rows (landmark_path made absolute, the npz files are not copied)."""
    with open(MANIFEST, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = {r["sample_id"]: r for r in reader}
    base = os.path.dirname(MANIFEST)
    out = os.path.join(tmp_dir, "manifest.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in sample_ids:
            r = dict(rows[sid])
            r["landmark_path"] = os.path.join(base, r["landmark_path"])
            w.writerow(r)
    return out


def _check_row(sample_id, kind, symbol, n_segments, agrees, close_reasons=None, below=False):
    return {"sample_id": sample_id, "kind": kind, "symbol": symbol, "n_segments": n_segments,
            "close_reasons": close_reasons if close_reasons is not None else ["hold"] * n_segments,
            "single_segment": n_segments == 1, "window_agrees": agrees, "below_min_detected_frames": below}


class TestSegmentCheckA3(unittest.TestCase):
    """plan 15 lần sửa 1 §3.A.4 + lần sửa 2 §5 (step A3): segment_check on the train clips, config TRƯỚC (3ebc7b9,
    tail_still_keep_ms filled = hold_ms) / SAU (b0620a9), keep rule. Real hauuto npz for the segmenter; the
    classifier is a stub defined in the test except in the CLI test (deployed checkpoint, 3 clips)."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(dir=PROJECT_ROOT, prefix="_tmp_a3_")  # inside the repo, untracked

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a3_config_before_is_3ebc7b9_with_tail_filled(self):
        import hashlib
        from scripts.level1_segment_report import segment_check_config
        values, meta = segment_check_config(f"git:{BEFORE_CONFIG_COMMIT}:configs/level1_realtime.json", "before")
        data = _git_text("show", f"{BEFORE_CONFIG_COMMIT}:configs/level1_realtime.json")
        raw = json.loads(data)
        self.assertNotIn("tail_still_keep_ms", raw)
        self.assertEqual(values["tail_still_keep_ms"], raw["hold_ms"]["value"])
        self.assertEqual(meta["filled"]["tail_still_keep_ms"], "= hold_ms of this config")
        self.assertTrue(meta["git_commit"].startswith(BEFORE_CONFIG_COMMIT))
        self.assertEqual(meta["sha256"], hashlib.sha256(data.encode("utf-8")).hexdigest())
        self.assertEqual(values["rearm_mode"], "motion_pose")
        self.assertIs(values["pose_change_rules"], False)
        for k in ("still_speed", "move_speed", "hold_ms", "max_segment_ms", "rearm_move_ms", "hand_lost_ms"):
            self.assertEqual(values[k], raw[k]["value"], k)

    def test_a3_config_after_is_b0620a9(self):
        from scripts.level1_segment_report import segment_check_config
        values, meta = segment_check_config(f"git:{A2_CONFIG_COMMIT}:configs/level1_realtime.json", "after")
        raw = json.loads(_git_text("show", f"{A2_CONFIG_COMMIT}:configs/level1_realtime.json"))
        for k in CAL_KEYS:
            self.assertEqual(json.dumps(values[k]), json.dumps(raw[k]["value"]), k)
        self.assertNotIn("tail_still_keep_ms", meta["filled"])  # the key exists at b0620a9
        self.assertTrue(meta["git_commit"].startswith(A2_CONFIG_COMMIT))
        self.assertEqual(values["rearm_mode"], "motion_pose")
        self.assertIs(values["pose_change_rules"], False)

    def test_a3_classifier_config_refused(self):
        from scripts.level1_segment_report import segment_check_config
        with self.assertRaises(ValueError):
            segment_check_config("configs/level1_demo_classifier.json", "demo")

    def test_a3_clip_check_matches_segmenter_and_agreement_rule(self):
        from scripts.level1_segment_report import clip_segment_check, load_train_clips, segment_check_config
        from src.inference.level1_segmenter import SignSegment
        values, _ = segment_check_config(f"git:{A2_CONFIG_COMMIT}:configs/level1_realtime.json", "after")
        clips = load_train_clips(_temp_manifest(self.tmp, A3_CLIP_IDS), 0)["clips"]
        self.assertEqual([c["sample_id"] for c in clips], sorted(A3_CLIP_IDS))
        min_det = 10

        def by_frames(segment):  # label = frame count: agrees only when the segment has the frames of the clip
            return {"status": "ok", "prediction": str(segment.n_frames)}

        for clip in clips:
            ts = clip_timestamps(len(clip["detected"]), clip["fps"])
            seg = Level1SignSegmenter(values, min_det)
            evs = []
            for i, t in enumerate(ts):
                det = bool(clip["detected"][i])
                evs += seg.push(float(t), clip["raw"][i] if det else None, clip["handedness"][i] if det else "",
                                clip["width"], clip["height"])
            evs += seg.flush(float(ts[-1]) + 1.0)
            segs = [e for e in evs if isinstance(e, SignSegment)]

            row = clip_segment_check(clip, values, min_det, lambda s: {"status": "ok", "prediction": "a"})
            self.assertEqual(row["n_segments"], len(segs), clip["sample_id"])
            self.assertEqual(row["close_reasons"], [s.close_reason for s in segs])
            self.assertEqual(row["single_segment"], len(segs) == 1)
            self.assertEqual(row["window_agrees"], len(segs) == 1)  # constant label: agreement == single
            self.assertEqual(row["whole_clip_prediction"], "a")

            row2 = clip_segment_check(clip, values, min_det, by_frames)
            self.assertEqual(row2["whole_clip_prediction"], str(len(clip["detected"])))
            self.assertEqual(row2["window_agrees"],
                             len(segs) == 1 and segs[0].n_frames == len(clip["detected"]), clip["sample_id"])

            row3 = clip_segment_check(clip, values, min_det, lambda s: {"status": "too_few_frames"})
            self.assertIsNone(row3["whole_clip_prediction"])
            self.assertFalse(row3["window_agrees"])  # no label is never an agreement

    def test_a3_groups_and_rates(self):
        from scripts.level1_segment_report import segment_check_groups
        rows = [_check_row("l1", "letter", "a", 1, True), _check_row("l2", "letter", "b", 1, False),
                _check_row("l3", "letter", "c", 2, False), _check_row("l4", "letter", "d", 0, False, below=True),
                _check_row("t1", "tone", "dấu sắc", 1, True), _check_row("t2", "tone", "dấu sắc", 2, False,
                                                                          ["hold", "end_of_stream"])]
        g = segment_check_groups(rows)
        self.assertEqual(g["letters"]["n"], 4)
        self.assertEqual(g["letters"]["single_segment"], 2)
        self.assertAlmostEqual(g["letters"]["single_segment_rate"], 0.5)
        self.assertEqual(g["letters"]["window_agrees"], 1)
        self.assertAlmostEqual(g["letters"]["window_agreement_rate"], 0.25)
        self.assertEqual(g["letters"]["n_segments"], {"0": 1, "1": 2, "2+": 1})
        self.assertEqual(g["letters"]["n_below_min_detected_frames"], 1)
        self.assertEqual(g["tones"]["n"], 2)
        self.assertAlmostEqual(g["tones"]["single_segment_rate"], 0.5)
        self.assertEqual(g["tones"]["close_reason"], {"end_of_stream": 1, "hold": 2})
        self.assertEqual(g["dấu sắc"]["n"], 2)
        self.assertEqual(g["dấu huyền"]["n"], 0)
        self.assertIsNone(g["dấu huyền"]["single_segment_rate"])
        self.assertIsNone(g["dấu huyền"]["window_agreement_rate"])

    def _report(self, letters, tones, ids=("l", "t")):
        def group(rates):
            return {"single_segment_rate": rates[0], "window_agreement_rate": rates[1]}
        return {"mode": "segment_check", "groups": {"letters": group(letters), "tones": group(tones)},
                "clips": [{"sample_id": i} for i in ids]}

    def test_a3_keep_rule(self):
        from scripts.level1_segment_report import keep_rule
        before = self._report((0.90, 0.80), (0.95, 0.40))
        ok = keep_rule(before, self._report((0.95, 0.79), (0.95, 0.45)))
        self.assertTrue(ok["keep"])
        self.assertTrue(ok["ac_r1"]["pass"])
        self.assertFalse(ok["stop"])
        self.assertEqual(ok["values"]["tones"]["single_segment_rate"], {"before": 0.95, "after": 0.95, "pass": True})
        tone_drop = keep_rule(before, self._report((0.95, 0.80), (0.94, 0.45)))
        self.assertFalse(tone_drop["keep"])
        self.assertTrue(tone_drop["stop"])
        letter_drop = keep_rule(before, self._report((0.95, 0.76), (0.95, 0.45)))
        self.assertFalse(letter_drop["keep"])
        self.assertFalse(letter_drop["values"]["letters"]["window_agreement_rate"]["pass"])
        r1 = keep_rule(self._report((0.85, 0.80), (0.95, 0.40)), self._report((0.89, 0.80), (0.95, 0.45)))
        self.assertTrue(r1["keep"])
        self.assertFalse(r1["ac_r1"]["pass"])  # AC-R1: single-segment rate below 0.9 with the config SAU
        self.assertTrue(r1["stop"])
        with self.assertRaises(ValueError):  # R'3: same clip set
            keep_rule(before, self._report((0.95, 0.80), (0.95, 0.45), ids=("l",)))
        missing = self._report((0.95, 0.80), (0.95, 0.45))
        missing["groups"]["tones"]["window_agreement_rate"] = None
        with self.assertRaises(ValueError):
            keep_rule(before, missing)

    def test_a3_cli_writes_report(self):
        out = os.path.join(self.tmp, "segment_check_after.json")
        manifest = _temp_manifest(self.tmp, A3_CLIP_IDS)
        ret = main(["--segment-check", "--config", f"git:{A2_CONFIG_COMMIT}:configs/level1_realtime.json",
                    "--label", "after", "--manifest", manifest, "--out", out])
        self.assertEqual(ret, 0)
        with open(out, encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["mode"], "segment_check")
        self.assertEqual(rep["label"], "after")
        self.assertIn("window agreement is not accuracy", rep["note"])
        self.assertEqual(len(rep["config"]["sha256"]), 64)
        self.assertTrue(rep["config"]["git_commit"].startswith(A2_CONFIG_COMMIT))
        self.assertEqual(rep["rearm_mode"], "motion_pose")
        self.assertIn(rep["generated_by"]["code_dirty"], (True, False))
        self.assertIn("scripts/level1_rearm_check.py", rep["generated_by"]["code_paths"])
        self.assertEqual([c["sample_id"] for c in rep["clips"]], sorted(A3_CLIP_IDS))
        self.assertEqual(rep["clip_counts"]["n_manifest_hauuto"], 3)
        self.assertEqual(rep["groups"]["letters"]["n"], 2)
        self.assertEqual(rep["groups"]["tones"]["n"], 1)
        for c in rep["clips"]:
            self.assertIsNotNone(c["whole_clip_prediction"])
            self.assertEqual(len(c["segment_predictions"]), c["n_segments"])
        # keep rule CLI on the same report twice: identical -> keep
        self.assertEqual(main(["--keep-rule", out, out]), 0)


if __name__ == "__main__":
    unittest.main()
