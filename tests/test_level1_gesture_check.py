"""
Plan 15 lần sửa 13 §3.2 mục 5, §3.3, §9 AC-G7 (+ the "script import" part of AC-G6; lần sửa 13d; review G2c notes):
scripts/level1_gesture_check.py.

AC-G7 the script on fake manifests (tmp) counts right: clips with >= 1 space / backspace per path (raw, smoothed) and per
      gesture kind (deliberate = GestureEngine, legacy = the old trackers), multi_emit, per source / per class; the
      rates and pass recomputed here from the counts of the JSON match `rates` / `gates` / `pass`; --verify finds a
      tampered report; a missing source (manifest absent, no row of a source, an npz absent) is an error (exit 2, no JSON).
      Gate thresholds are those set before the measurement (§3.3): GF1 backspace <= 0.005, GF2 space <= 0.010, both paths.
AC-G6 (script part) the script uses GestureEngine of src.inference.level1_gestures (the class the app uses).
Review G2c: GestureEngine.step gets still = segmenter.state != "moving" read AFTER segmenter.push of the SAME frame, the
      real width / height also on frames without hand; path smoothed = the LandmarkSmoother output given to both the
      segmenter and the engine; path raw = the npz landmarks.

Every clip below is a chuỗi tạo có kiểm soát để kiểm logic (controlled sequence built to check the logic): hand shapes are
the templates of tests/test_level1_gestures.py (checked there against the real pose predicates); they are not data and no
number here is a measurement.
"""
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts import level1_gesture_check as gc  # noqa: E402
from src.inference import level1_gestures  # noqa: E402
from src.inference.level1_core import LandmarkSmoother  # noqa: E402
from src.inference.level1_gestures import load_gesture_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter  # noqa: E402
from tests.test_level1_gestures import CURLED, FLAT, OPEN_PALM, PALM, hand, stroke_path, to_mediapipe  # noqa: E402

GESTURE_CONFIG = os.path.join(PROJECT_ROOT, "configs", "level1_gestures.json")
SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "level1_gesture_check.py")
W, H, FPS = 640, 480, 25.0
FIELDS = ["detection_rate", "extractor", "fps", "height", "landmark_path", "mediapipe_version", "num_frames",
          "sample_id", "signer_id", "source", "symbol", "width"]


# ------------------------------------------------------------------------------------------- controlled clips
def _pose_frames(template, n, cx=0.6, cy=0.5):
    return [hand(template, cx, cy) for _ in range(n)]


def _wave_frames():
    """Flat hand: still, then 2 horizontal strokes of 2 x (wave_min_amplitude x palm length), then still."""
    amp = 2.0 * load_gesture_config(GESTURE_CONFIG)["values"]["wave_min_amplitude"] * PALM
    xs = stroke_path(0.5, [amp, -amp], frames_per_stroke=6, still_before=6, still_after=10)
    return [hand(FLAT, x, 0.5) for x in xs]


CLIPS = {
    # sample_id: (source, symbol, frames (aspect points or None = no hand))
    # open palm held still 2 s -> one deliberate space
    "h_space": ("hauuto", "a", _pose_frames(OPEN_PALM, 50)),
    # open palm 1.2 s, one frame without hand, open palm 1.2 s -> two deliberate spaces (multi_emit)
    "h_space_twice": ("hauuto", "b", _pose_frames(OPEN_PALM, 30) + [None] + _pose_frames(OPEN_PALM, 30)),
    # no hand at all -> nothing
    "h_nohand": ("hauuto", "a", [None] * 20),
    # flat hand waved left / right -> one deliberate backspace
    "q_wave": ("qipedc", "c", _wave_frames()),
    # open palm 0.44 s then curled: legacy space (250 ms) fires, deliberate (600 ms held still) does not
    "q_short_palm": ("qipedc", "d", _pose_frames(OPEN_PALM, 12) + _pose_frames(CURLED, 15)),
    # curled hand held still -> nothing
    "u_curled": ("user1", "e", _pose_frames(CURLED, 40)),
}


def _write_npz(path, frames):
    raw = np.zeros((len(frames), 21, 3), dtype=np.float32)
    det = np.zeros(len(frames), dtype=bool)
    for i, p in enumerate(frames):
        if p is not None:
            raw[i] = to_mediapipe(p, W, H)
            det[i] = True
    np.savez_compressed(path, raw_landmarks=raw, detected_mask=det,
                        handedness_label=np.asarray(["Right" if d else "" for d in det]),
                        handedness_score=np.ones(len(frames), dtype=np.float32), metadata=json.dumps({}))


def write_fixture(root, clips=CLIPS, drop_source=None, drop_npz=None, no_user1_manifest=False):
    """tmp layout: kaggle/manifest.csv (hauuto + qipedc), user1/manifest.csv; returns the two manifest paths."""
    kaggle_dir, user1_dir = os.path.join(root, "kaggle"), os.path.join(root, "user1")
    rows = {"kaggle": [], "user1": []}
    for sid, (source, symbol, frames) in clips.items():
        if source == drop_source:
            continue
        group = "user1" if source == "user1" else "kaggle"
        base = user1_dir if group == "user1" else kaggle_dir
        rel_npz = f"{source}/{sid}.npz"
        os.makedirs(os.path.join(base, source), exist_ok=True)
        if sid != drop_npz:
            _write_npz(os.path.join(base, rel_npz), frames)
        rows[group].append({
            "detection_rate": "1.0", "extractor": "mp.solutions.hands", "fps": str(FPS), "height": str(H),
            "landmark_path": rel_npz, "mediapipe_version": "0.10.14", "num_frames": str(len(frames)),
            "sample_id": sid, "signer_id": "user1" if source == "user1" else source, "symbol": symbol,
            "source": "collected_targeted" if source == "user1" else source, "width": str(W)})
    paths = {}
    for group, base in (("kaggle", kaggle_dir), ("user1", user1_dir)):
        os.makedirs(base, exist_ok=True)
        paths[group] = os.path.join(base, "manifest.csv")
        if group == "user1" and no_user1_manifest:
            continue
        with open(paths[group], "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows[group])
    return paths["kaggle"], paths["user1"]


def run_main(kaggle, user1, out):
    argv = ["--kaggle-manifest", kaggle, "--user1-manifest", user1, "--min-detected-frames", "3", "--out", out]
    return gc.main(argv)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="g3_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = os.path.join(self.tmp, "out", "report.json")


# ------------------------------------------------------------------------------------------- AC-G6 (script part)
class TestScriptUsesTheAppEngine(unittest.TestCase):
    def test_engine_is_the_one_of_level1_gestures(self):
        self.assertIs(gc.GestureEngine, level1_gestures.GestureEngine)
        with open(SCRIPT, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("from src.inference.level1_gestures import GestureEngine", text)

    def test_segmenter_config_is_the_preset_config(self):
        import level1_demo
        argv = level1_demo.DEFAULT_DEMO_ARGV
        self.assertEqual(argv[argv.index("--config") + 1].replace("/", os.sep), gc.SEGMENTER_CONFIG)
        self.assertEqual(argv[argv.index("--gesture-config") + 1].replace("/", os.sep), gc.GESTURE_CONFIG)
        self.assertIn("--smooth-landmarks", argv)


# ------------------------------------------------------------------------------------------- gates (§3.3)
class TestGatesSetBefore(unittest.TestCase):
    def test_thresholds_of_the_plan(self):
        """15-lan-sua-13 §3.3: GF1 backspace <= 0.005, GF2 space <= 0.010, deliberate, on raw AND smoothed."""
        self.assertEqual(list(gc.GATES), ["GF1", "GF2"])
        self.assertEqual((gc.GATES["GF1"]["gesture"], gc.GATES["GF1"]["max_rate"]), ("backspace", 0.005))
        self.assertEqual((gc.GATES["GF2"]["gesture"], gc.GATES["GF2"]["max_rate"]), ("space", 0.010))
        for g in gc.GATES.values():
            self.assertEqual(g["kind"], "deliberate")
            self.assertEqual(sorted(g["paths"]), ["raw", "smoothed"])
        self.assertIn("15-lan-sua-13 §3.3", gc.GATE_SET_IN)

    def _rates(self, space, backspace, path_fail=None):
        r = {p: {k: {"space": 0.0, "backspace": 0.0} for k in gc.KINDS} for p in gc.PATHS}
        for p in gc.PATHS:
            if path_fail in (None, p):
                r[p]["deliberate"] = {"space": space, "backspace": backspace}
        return r

    def test_boundary_is_inclusive(self):
        gates, ok = gc.evaluate_gates(self._rates(0.010, 0.005))
        self.assertTrue(ok)
        self.assertTrue(gates["GF1"]["pass"] and gates["GF2"]["pass"])

    def test_one_path_over_fails(self):
        for path in gc.PATHS:
            gates, ok = gc.evaluate_gates(self._rates(0.0, 0.0051, path_fail=path))
            self.assertFalse(ok)
            self.assertFalse(gates["GF1"]["paths"][path]["pass"])
            self.assertTrue(gates["GF2"]["pass"])
            gates, ok = gc.evaluate_gates(self._rates(0.0101, 0.0, path_fail=path))
            self.assertFalse(ok)
            self.assertFalse(gates["GF2"]["pass"])

    def test_legacy_is_not_gated(self):
        r = self._rates(0.0, 0.0)
        for p in gc.PATHS:
            r[p]["legacy"] = {"space": 1.0, "backspace": 1.0}
        self.assertTrue(gc.evaluate_gates(r)[1])


# ------------------------------------------------------------------------------------------- AC-G7 counts
class TestCountsOnFakeManifests(_Tmp):
    @classmethod
    def setUpClass(cls):
        cls.ctmp = tempfile.mkdtemp(prefix="g3c_")
        kaggle, user1 = write_fixture(cls.ctmp)
        cls.out_path = os.path.join(cls.ctmp, "report.json")
        cls.code = run_main(kaggle, user1, cls.out_path)
        with open(cls.out_path, encoding="utf-8") as f:
            cls.report = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ctmp, ignore_errors=True)

    def test_exit_code_and_sources(self):
        self.assertEqual(self.code, gc.EXIT_GATE_FAIL)  # 2/6 space, 1/6 backspace: far over the gates
        self.assertFalse(self.report["pass"])
        self.assertEqual(self.report["n_clips"], 6)
        self.assertEqual({s: v["n_clips"] for s, v in self.report["sources"].items()},
                         {"hauuto": 3, "qipedc": 2, "user1": 1})
        self.assertEqual(self.report["sources"]["hauuto"]["clips_without_hand"], 1)

    def test_deliberate_counts_on_both_paths(self):
        for path in gc.PATHS:
            c = self.report["counts"][path]["deliberate"]
            self.assertEqual(c["n_clips"], 6, path)
            self.assertEqual((c["space_clips"], c["space_multi_emit"], c["space_emits"]), (2, 1, 3), path)
            self.assertEqual((c["backspace_clips"], c["backspace_multi_emit"], c["backspace_emits"]), (1, 0, 1), path)
            fired = self.report["fired_clips"][path]["deliberate"]
            self.assertEqual(sorted(f["sample_id"] for f in fired["space"]), ["h_space", "h_space_twice"], path)
            self.assertEqual([f["sample_id"] for f in fired["backspace"]], ["q_wave"], path)

    def test_legacy_counts(self):
        """The old trackers of the app: the 0.44 s open palm fires the 250 ms space; the deliberate one does not."""
        for path in gc.PATHS:
            fired = self.report["fired_clips"][path]["legacy"]
            self.assertEqual(sorted(f["sample_id"] for f in fired["space"]), ["h_space", "h_space_twice", "q_short_palm"])
            self.assertNotIn("u_curled", [f["sample_id"] for f in fired["backspace"]])
            self.assertNotIn("h_nohand", [f["sample_id"] for f in fired["backspace"]])

    def test_per_source_and_per_class(self):
        for path in gc.PATHS:
            ps = self.report["per_source"]
            self.assertEqual(ps["hauuto"][path]["deliberate"]["space_clips"], 2)
            self.assertEqual(ps["qipedc"][path]["deliberate"]["space_clips"], 0)
            self.assertEqual(ps["qipedc"][path]["deliberate"]["backspace_clips"], 1)
            self.assertEqual(ps["user1"][path]["deliberate"]["space_clips"] + ps["user1"][path]["deliberate"]
                             ["backspace_clips"], 0)
            pc = self.report["per_class"]
            self.assertEqual(sorted(pc), ["a", "b", "c", "d", "e"])
            self.assertEqual(pc["a"][path]["deliberate"]["n_clips"], 2)
            self.assertEqual(pc["a"][path]["deliberate"]["space_clips"], 1)
            self.assertEqual(pc["c"][path]["deliberate"]["backspace_clips"], 1)

    def test_rates_and_pass_recomputed_from_the_counts(self):
        """Independent arithmetic on the JSON: rate = clips with >= 1 / n_clips; gate thresholds of §3.3."""
        thresholds = {"GF1": ("backspace", 0.005), "GF2": ("space", 0.010)}
        all_pass = True
        for path in ("raw", "smoothed"):
            for kind in ("deliberate", "legacy"):
                c = self.report["counts"][path][kind]
                for g in ("space", "backspace"):
                    self.assertEqual(self.report["rates"][path][kind][g], c[f"{g}_clips"] / c["n_clips"])
            for name, (g, thr) in thresholds.items():
                c = self.report["counts"][path]["deliberate"]
                r = c[f"{g}_clips"] / c["n_clips"]
                self.assertEqual(self.report["gates"][name]["paths"][path]["rate"], r)
                self.assertEqual(self.report["gates"][name]["paths"][path]["pass"], r <= thr)
                all_pass = all_pass and r <= thr
        self.assertEqual(self.report["pass"], all_pass)
        self.assertEqual(gc.check_report(self.report), [])

    def test_report_records_configs_and_command(self):
        cfg = self.report["gesture_config"]
        with open(GESTURE_CONFIG, "rb") as f:
            self.assertEqual(cfg["sha256"], hashlib.sha256(f.read()).hexdigest())
        self.assertEqual(cfg["values"], load_gesture_config(GESTURE_CONFIG)["values"])
        self.assertEqual(cfg["overrides"], {})
        gb = self.report["generated_by"]
        self.assertTrue(gb["command"].startswith("python scripts/level1_gesture_check.py "))
        self.assertIn("scripts/level1_gesture_check.py", gb["code_paths"])
        self.assertIn(gb["code_dirty"], (True, False))
        self.assertTrue(self.report["segmenter_config"]["path"].endswith("level1_demo_classifier_rev9.json"))
        self.assertEqual(self.report["min_detected_frames"]["value"], 3)

    def test_verify_mode(self):
        path = os.path.join(self.tmp, "r.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.report, f)
        self.assertEqual(gc.main(["--verify", path]), gc.EXIT_OK)
        tampers = [
            lambda r: r["rates"]["raw"]["deliberate"].__setitem__("space", 0.0),
            lambda r: r.__setitem__("pass", True),
            lambda r: r["gates"]["GF1"].__setitem__("max_rate", 0.5),
            lambda r: r["gates"]["GF2"]["paths"]["smoothed"].__setitem__("pass", True),
            lambda r: r["counts"]["smoothed"]["deliberate"].__setitem__("backspace_clips", 0),
        ]
        for i, tamper in enumerate(tampers):
            bad = json.loads(json.dumps(self.report))
            tamper(bad)
            bad_path = os.path.join(self.tmp, f"bad{i}.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                json.dump(bad, f)
            self.assertEqual(gc.main(["--verify", bad_path]), gc.EXIT_INCONSISTENT, i)


class TestPassingFixture(_Tmp):
    def test_negatives_only_pass(self):
        """Only clips without gesture: 0 clip fires -> exit 0, pass True."""
        clips = {k: v for k, v in CLIPS.items() if k in ("h_nohand", "q_short_palm", "u_curled")}
        kaggle, user1 = write_fixture(self.tmp, clips=clips)
        self.assertEqual(run_main(kaggle, user1, self.out), gc.EXIT_OK)
        with open(self.out, encoding="utf-8") as f:
            report = json.load(f)
        self.assertTrue(report["pass"])
        self.assertEqual(gc.check_report(report), [])


# ------------------------------------------------------------------------------------------- missing source
class TestMissingSourceIsAnError(_Tmp):
    def _expect_input_error(self, **kw):
        kaggle, user1 = write_fixture(self.tmp, **kw)
        self.assertEqual(run_main(kaggle, user1, self.out), gc.EXIT_INPUT_ERROR)
        self.assertFalse(os.path.exists(self.out))

    def test_no_qipedc_row(self):
        self._expect_input_error(drop_source="qipedc")

    def test_no_hauuto_row(self):
        self._expect_input_error(drop_source="hauuto")

    def test_no_user1_row(self):
        self._expect_input_error(drop_source="user1")

    def test_user1_manifest_absent(self):
        self._expect_input_error(no_user1_manifest=True)

    def test_npz_absent(self):
        self._expect_input_error(drop_npz="q_wave")

    def test_kaggle_manifest_absent(self):
        _, user1 = write_fixture(self.tmp)
        self.assertEqual(run_main(os.path.join(self.tmp, "nope.csv"), user1, self.out), gc.EXIT_INPUT_ERROR)


# ------------------------------------------------------------------------------------------- same path as the app
class TestFramePathLikeTheApp(_Tmp):
    """GestureEngine.step gets still of the SAME frame (after segmenter.push), the real w / h, and the same landmarks as
    the segmenter; path smoothed = LandmarkSmoother output, path raw = the npz landmarks."""

    def _record(self, sample_id):
        source, symbol, frames = CLIPS[sample_id]
        kaggle, _ = write_fixture(self.tmp)
        npz = os.path.join(os.path.dirname(kaggle), source, f"{sample_id}.npz")
        clip = {"source": source, "sample_id": sample_id, "symbol": symbol, "signer_id": source, "npz": npz,
                "fps": FPS, "width": W, "height": H}
        pushes, steps = [], []
        real_push, real_step = Level1SignSegmenter.push, level1_gestures.GestureEngine.step

        def push(seg, ts, landmarks, handedness, w, h):
            ev = real_push(seg, ts, landmarks, handedness, w, h)
            pushes.append((ts, None if landmarks is None else np.array(landmarks), seg.state, w, h))
            return ev

        def step(eng, ts, landmarks, w, h, still):
            steps.append((ts, None if landmarks is None else np.array(landmarks), still, w, h))
            return real_step(eng, ts, landmarks, w, h, still)

        with mock.patch.object(Level1SignSegmenter, "push", push), \
                mock.patch.object(level1_gestures.GestureEngine, "step", step):
            gc.run_clip(clip, gc.load_level1_config(os.path.join(PROJECT_ROOT, gc.SEGMENTER_CONFIG))["values"],
                        load_gesture_config(GESTURE_CONFIG)["values"], 3)
        with np.load(npz) as z:
            raw = z["raw_landmarks"]
            det = z["detected_mask"]
        return pushes, steps, raw, det

    def _check_pairs(self, pushes, steps):
        self.assertEqual(len(pushes), len(steps))
        for (ts_p, lm_p, state, w_p, h_p), (ts_s, lm_s, still, w_s, h_s) in zip(pushes, steps):
            self.assertEqual(ts_p, ts_s)
            self.assertEqual(still, state != "moving", ts_s)  # state read after the push of the same frame
            self.assertEqual((w_s, h_s), (W, H))
            self.assertEqual((w_p, h_p), (W, H))
            if lm_p is None:
                self.assertIsNone(lm_s)
            else:
                np.testing.assert_array_equal(lm_p, lm_s)

    def test_wave_clip_still_and_landmarks(self):
        pushes, steps, raw, det = self._record("q_wave")
        n = len(raw)
        self.assertEqual(len(steps), 2 * n)  # raw path then smoothed path
        self._check_pairs(pushes, steps)
        self.assertEqual({s[2] for s in steps}, {True, False})  # the wave makes the segmenter "moving"
        # raw path: the npz landmarks; smoothed path: LandmarkSmoother() of them
        smoother = LandmarkSmoother()
        for i in range(n):
            np.testing.assert_array_equal(steps[i][1], raw[i])
            np.testing.assert_array_equal(steps[n + i][1], smoother.filter(i * 1000.0 / FPS, raw[i]))
        self.assertFalse(all(np.array_equal(steps[i][1], steps[n + i][1]) for i in range(n)))

    def test_frames_without_hand_keep_the_real_size(self):
        pushes, steps, raw, det = self._record("h_space_twice")
        self._check_pairs(pushes, steps)
        none_steps = [s for s in steps if s[1] is None]
        self.assertEqual(len(none_steps), 2 * int((~det).sum()))
        self.assertTrue(all((s[3], s[4]) == (W, H) for s in none_steps))


if __name__ == "__main__":
    unittest.main()
