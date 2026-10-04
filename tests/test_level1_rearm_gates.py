"""
Plan 15 lần sửa 3 §3.5 / §4 #6 / §5 (R3): scripts/level1_rearm_check.py — covered one_rate, config overrides, G6 on
single clips, the pre-registered gates G1-G6 and the switch of pose_change_rules after the gates.

The landmark sequences / clips below are controlled sequences built in this test to check the logic; they are not real
data (chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ liệu thật). The real rearm_check_r3.json needs the
gitignored landmark data and is produced by the script, not here.
"""
import csv
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

import scripts.level1_rearm_check as rc  # noqa: E402
import scripts.level1_segment_report as sr  # noqa: E402
from tests.test_level1_rearm import DIR, PARAMS_RA, H, W, shape, stream_ra1, stream_ra2  # noqa: E402

CONFIG_REL = "configs/level1_realtime.json"


def metrics(one_cov=0.95, multi=0.0, hand_lost=0, order_ok=True, garbage=0.0):
    return {"one_rate_covered": one_cov, "one_rate": one_cov, "multi_rate": multi, "hand_lost": hand_lost,
            "order_ok": order_ok, "garbage_per_clip": garbage}


def passing_results():
    res = {}
    for cfg in ("on", "off"):
        res[cfg] = {chain: {j: metrics() for j in ("0", "300", "600")} for chain in ("L", "T", "O")}
    return res


def passing_single():
    return {"on": {"letter": {"rate": 0.95}, "tone": {"rate": 0.80}},
            "off": {"letter": {"rate": 0.96}, "tone": {"rate": 0.81}}}


class TestCoveredRate(unittest.TestCase):
    def test_script_uses_segmenter_pose_functions(self):
        """AC-RA9 (R3 side): the covered rate uses the segmenter's pose_distance and the R2 clip reference shape."""
        import src.inference.level1_segmenter as seg_mod
        self.assertIs(rc.pose_distance, seg_mod.pose_distance)
        self.assertIs(rc.seg_report.clip_pose_profile, sr.clip_pose_profile)

    def test_undefined_distance_is_not_covered(self):
        assigned = {"clip_segments": {0: [{}], 1: [{}], 2: []}, "garbage_segments": [],
                    "all_segments": [{"assigned_source": 0}, {"assigned_source": 1}]}
        m = rc.calculate_metrics(assigned, 3, clip_distances=[None, 0.9], rearm_pose_dist=0.3)
        self.assertEqual(m["n_clips_covered"], 2)       # clip 0 (always) + clip 2; clip 1 has no reference shape
        self.assertEqual(m["n_one_covered"], 1)
        self.assertEqual(m["one_rate_covered"], 0.5)


class TestOverrides(unittest.TestCase):
    def test_parse_and_apply(self):
        self.assertEqual(rc.parse_override("on:pose_change_rules=true"), ("on", "pose_change_rules", True))
        self.assertEqual(rc.parse_override("off:rearm_pose_dist=0.25"), ("off", "rearm_pose_dist", 0.25))
        name, values, meta = rc.resolve_config_spec(f"on={CONFIG_REL}")
        new = rc.apply_overrides(values, {"pose_change_rules": True})
        self.assertIs(new["pose_change_rules"], True)
        self.assertIsNot(new, values)
        for spec in ("no_colon=true", "on:pose_change_rules", "on:pose_change_rules=notjson"):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                rc.parse_override(spec)
        for bad in ({"pose_change_rules": 1}, {"rearm_pose_dist": 0}, {"unknown_key": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rc.apply_overrides(values, bad)


class TestGates(unittest.TestCase):
    """G1..G6 of plan 15 lần sửa 3 §5 R3, thresholds fixed in the script (pre-registered)."""

    def test_all_pass(self):
        g = rc.evaluate_gates(passing_results(), passing_single(), "on", "off")
        self.assertEqual(sorted(g["gates"]), ["G1", "G2", "G3", "G4", "G5", "G6"])
        self.assertTrue(all(v["pass"] for v in g["gates"].values()))
        self.assertTrue(g["all_pass"])
        self.assertEqual(g["thresholds"], {"G1_one_rate_covered_min": 0.90, "G2_multi_rate_max": 0.05,
                                           "G5_garbage_per_clip_max": 0.05, "G6_single_drop_max": 0.02})

    def test_boundaries_inclusive(self):
        res = passing_results()
        res["on"]["L"]["0"]["one_rate_covered"] = 0.90
        res["on"]["L"]["600"]["multi_rate"] = 0.05
        res["on"]["L"]["300"]["garbage_per_clip"] = 0.05
        self.assertTrue(rc.evaluate_gates(res, passing_single(), "on", "off")["all_pass"])

    def test_each_gate_fails(self):
        cases = {
            "G1": lambda r, s: r["on"]["L"]["300"].__setitem__("one_rate_covered", 0.89),
            "G2": lambda r, s: r["on"]["L"]["600"].__setitem__("multi_rate", 0.06),
            "G3": lambda r, s: r["on"]["O"]["0"].__setitem__("hand_lost", 1),
            "G4": lambda r, s: r["on"]["L"]["0"].__setitem__("order_ok", False),
            "G5": lambda r, s: r["on"]["L"]["600"].__setitem__("garbage_per_clip", 0.06),
            "G6": lambda r, s: s["on"]["tone"].__setitem__("rate", 0.75),
        }
        for gate, mutate in cases.items():
            with self.subTest(gate=gate):
                res, single = passing_results(), passing_single()
                mutate(res, single)
                g = rc.evaluate_gates(res, single, "on", "off")
                self.assertFalse(g["gates"][gate]["pass"])
                self.assertFalse(g["all_pass"])
                self.assertEqual([k for k, v in g["gates"].items() if not v["pass"]], [gate])

    def test_off_config_and_report_only_values_do_not_gate(self):
        res = passing_results()
        res["off"]["L"]["0"]["one_rate_covered"] = 0.1          # the off config is never gated (except as G6 base)
        res["on"]["L"]["600"]["one_rate_covered"] = 0.1         # G1 at join 600 is report only
        res["on"]["T"]["0"]["multi_rate"] = 0.9                 # chain T: only G3 applies
        self.assertTrue(rc.evaluate_gates(res, passing_single(), "on", "off")["all_pass"])

    def test_missing_join_fails(self):
        res = passing_results()
        del res["on"]["L"]["300"]
        g = rc.evaluate_gates(res, passing_single(), "on", "off")
        self.assertFalse(g["gates"]["G1"]["pass"])
        self.assertFalse(g["gates"]["G5"]["pass"])


class TestSingleClipG6(unittest.TestCase):
    def _clip(self, frames, symbol, kind):
        lm = [f[1] for f in frames]
        return {"sample_id": f"hauuto_{symbol}_s1_A_001", "symbol": symbol, "kind": kind, "signer_id": "s1",
                "raw": np.stack(lm), "detected": np.ones(len(lm), dtype=bool), "handedness": ["Left"] * len(lm),
                "width": W, "height": H, "fps": 25.0}

    def test_single_clip_rates(self):
        clips = [self._clip(stream_ra2(), "a", "letter"), self._clip(stream_ra1(), "b", "letter"),
                 self._clip(stream_ra2(), "dấu sắc", "tone")]
        on = rc.single_clip_rates(clips, {**PARAMS_RA, "pose_change_rules": True}, 3)
        off = rc.single_clip_rates(clips, {**PARAMS_RA, "pose_change_rules": False}, 3)
        self.assertEqual(off["letter"], {"n": 2, "single": 2, "rate": 1.0})
        self.assertEqual(on["letter"], {"n": 2, "single": 1, "rate": 0.5})   # the A -> B clip gives 2 segments
        self.assertEqual(on["tone"], {"n": 1, "single": 1, "rate": 1.0})


def _write_npz(path, raws):
    raws = np.stack(raws).astype(np.float32)
    np.savez(path, raw_landmarks=raws, detected_mask=np.ones(len(raws), dtype=bool),
             handedness_label=np.array(["Left"] * len(raws)))


def still_raws(dist, n=40):
    """Shape at `dist` from A held still with a tiny alternating jitter (far below still_speed)."""
    other = np.roll(DIR, 3, axis=0)
    other[0] = 0.0
    other[9] = 0.0
    base = shape(dist).astype(np.float64)
    zero = shape(0.0).astype(np.float64)
    return [(base + shape(0.005 if k % 2 else -0.005, direction=other).astype(np.float64) - zero).astype(np.float32)
            for k in range(n)]


class TestEndToEndSynthetic(unittest.TestCase):
    """run_rearm_check on a synthetic manifest (one signer, one session): with the real config values, the pose
    rules on (rearm_pose_dist overridden for these synthetic shapes) give one segment per letter clip; off: the
    concatenated letters after the first are missed (the U1b failure)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vslt_r3_")
        rows = []
        clips = [("a", 0.0, "001"), ("b", 0.3, "001"), ("c", 0.6, "001"), ("d", 0.9, "001"), ("o", 1.2, "001"),
                 ("o", 1.2, "002"), ("dấu sắc", 1.5, "001")]
        for sym, dist, num in clips:
            sid = f"hauuto_{'tone_s' if sym == 'dấu sắc' else sym}_s1_A_{num}"
            _write_npz(os.path.join(self.tmp, f"{sid}.npz"), still_raws(dist))
            rows.append({"sample_id": sid, "source": "hauuto", "symbol": sym, "signer_id": "s1",
                         "landmark_path": f"{sid}.npz", "width": W, "height": H, "fps": 25.0})
        self.manifest = os.path.join(self.tmp, "manifest.csv")
        with open(self.manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_end_to_end(self):
        rep = rc.run_rearm_check(
            config_specs=[f"off={CONFIG_REL}", f"on={CONFIG_REL}"], join_ms_list=[0.0, 300.0, 600.0],
            manifest_path=self.manifest, checkpoint_path=None, min_detected_frames=3,
            overrides=["on:pose_change_rules=true", "on:rearm_pose_dist=0.15", "off:rearm_pose_dist=0.15"],
            gates=("on", "off"), argv=["--test"])
        self.assertEqual(rep["note"], rc.NOTE)
        self.assertEqual(rep["note_vi"], "chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác")
        self.assertEqual(rep["configs"]["on"]["overrides"], {"pose_change_rules": True, "rearm_pose_dist": 0.15})
        self.assertIsNone(rep["checkpoint"])
        on_l0, off_l0 = rep["results"]["on"]["L"]["0"], rep["results"]["off"]["L"]["0"]
        self.assertEqual(on_l0["n_clips"], 5)
        self.assertEqual(on_l0["one_rate"], 1.0)
        self.assertEqual(on_l0["one_rate_covered"], 1.0)
        self.assertEqual(on_l0["n_clips_covered"], 5)
        self.assertLess(off_l0["one_rate"], on_l0["one_rate"])
        self.assertIsNone(on_l0["label_agrees"])
        self.assertEqual(sorted(rep["gates"]["gates"]), ["G1", "G2", "G3", "G4", "G5", "G6"])
        self.assertIn("letter", rep["single_clip"]["on"])
        json.dumps(rep)


class TestWriteRulesConfig(unittest.TestCase):
    """pose_change_rules -> true only from a committed, clean R3 JSON whose gates all passed; only that key changes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=PROJECT_ROOT, prefix="_tmp_r3_")  # inside the repo, untracked
        self.cfg = os.path.join(self.tmp, "config.json")
        shutil.copyfile(os.path.join(PROJECT_ROOT, CONFIG_REL), self.cfg)
        with open(self.cfg, "rb") as f:
            self.cfg_bytes = f.read()
        self.js = os.path.join(self.tmp, "rearm_check_r3.json")
        self._write(True, False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, all_pass, dirty):
        with open(self.js, "w", encoding="utf-8") as f:
            json.dump({"generated_by": {"git_commit": "f" * 40, "code_dirty": dirty},
                       "gates": {"all_pass": all_pass, "gate_config": "on", "baseline_config": "off"}}, f)

    def _unchanged(self):
        with open(self.cfg, "rb") as f:
            self.assertEqual(f.read(), self.cfg_bytes)

    def test_uncommitted_json_refused(self):
        with self.assertRaises(RuntimeError):
            rc.write_rules_config(self.cfg, self.js)
        self._unchanged()

    def test_failed_gates_or_dirty_code_refused(self):
        for all_pass, dirty in ((False, False), (True, True)):
            with self.subTest(all_pass=all_pass, dirty=dirty):
                self._write(all_pass, dirty)
                with mock.patch.object(sr, "committed_evidence_ref", return_value=("reports/x/r3.json", "abc1234")):
                    with self.assertRaises(RuntimeError):
                        rc.write_rules_config(self.cfg, self.js)
                self._unchanged()

    def test_success_only_pose_change_rules(self):
        with open(self.cfg, encoding="utf-8") as f:
            before = json.load(f)
        with mock.patch.object(sr, "committed_evidence_ref", return_value=("reports/x/r3.json", "abc1234")) as h:
            rc.write_rules_config(self.cfg, self.js)
        h.assert_called_once()
        with open(self.cfg, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual(list(after), list(before))
        self.assertIs(after["pose_change_rules"]["value"], True)
        self.assertEqual(after["pose_change_rules"]["source"], "design")
        self.assertIn("reports/x/r3.json@abc1234", after["pose_change_rules"]["reason"])
        for k in before:
            if k != "pose_change_rules":
                self.assertEqual(json.dumps(after[k], ensure_ascii=False), json.dumps(before[k], ensure_ascii=False), k)
        sr.validate_level1_config(after)
        self.assertIsNone(re.search(r"\bfake\b|\bmock\b", after["pose_change_rules"]["reason"]))


if __name__ == "__main__":
    unittest.main()
