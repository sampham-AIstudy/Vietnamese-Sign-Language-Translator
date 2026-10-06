"""
Plan 15 AC-D: the desktop app level1_demo.py, on a real clip (hauuto training clip: this checks the code path, not
accuracy). No webcam is used: the window mode is for the user (U1).

D1 --help lists the options. D2 headless run on a_hau_A_001.mp4: exit 0, JSON keys of §3.5, every segment's prediction
equals Level1Classifier.classify run again on the same segment, two runs give the same tokens / segments.
D3 newest-frame slot fed with frames read from the real video through the app's reader. D4 a video whose frame rate
cannot be read -> exit code != 0 with a message, no default frame rate. D5 in paced mode classification runs off the
main loop (a deliberately slow classifier defined here -> more than one frame processed meanwhile).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import level1_demo as app_mod  # noqa: E402
from src.inference.level1_core import Level1Classifier  # noqa: E402

PY = sys.executable
CLIP = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "hau", "a_hau_A_001.mp4")
CKPT = os.path.join("checkpoints", "alphabet_best.pt")
_MISSING = [p for p in (CLIP, CKPT) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]
SKIP_REASON = "missing (gitignored data / checkpoint): " + ", ".join(_MISSING)
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

TOP_KEYS = ("generated_by", "config", "checkpoint", "source", "frame_size", "camera_props", "warmup", "stages",
            "counts", "tokens", "text", "warnings", "segments", "events", "expected", "note")
GEN_KEYS = ("command", "git_commit", "code_dirty", "utc", "python", "mediapipe", "cv2", "torch", "numpy", "cpu", "os")
SEG_KEYS = ("seq", "t_start_ms", "t_end_ms", "close_reason", "frames", "detected_frames", "prediction", "confidence",
            "accepted")
STAGES = ("capture_age", "mediapipe", "segmenter", "draw_landmarks", "hud", "display", "frame_total", "classify",
          "emit_to_token")
COUNT_KEYS = ("frames_read", "frames_processed", "frames_dropped", "processing_fps")


# plan 15 lần sửa 12 S1: automatic spaces (word gap, open palm gesture) are off by default. The tests written before
# lần sửa 12 pin the app with both on (their default then, and the app at the earlier commits they compare with), so
# args_for() turns both on first; a test's own --no-auto-space / --no-gesture-space comes later and wins (argparse
# BooleanOptionalAction: the last flag counts). args_new() parses exactly the given argv (the defaults of today).
LEGACY_DEFAULTS = ("--auto-space", "--gesture-space")


def args_for(*argv):
    return app_mod.build_parser().parse_args([*LEGACY_DEFAULTS, *argv])


def args_new(*argv):
    return app_mod.build_parser().parse_args(list(argv))


class TestHelpD1(unittest.TestCase):
    def test_d1_help(self):
        r = subprocess.run([PY, "level1_demo.py", "--help"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                           env=ENV, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        for opt in ("--source", "--headless", "--out-json", "--config", "--checkpoint", "--pace", "--expected",
                    "--display-mirror", "--font"):
            self.assertIn(opt, r.stdout)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHeadlessD2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_d2_")
        cls.out = os.path.join(cls.tmp, "d2.json")
        cls.proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, "--headless", "--out-json", cls.out],
                                  cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV, timeout=900)
        cls.report = None
        if cls.proc.returncode == 0:
            with open(cls.out, encoding="utf-8") as f:
                cls.report = json.load(f)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.app = app_mod.Level1App(args_for("--source", CLIP, "--headless"), keep_segments=True)
            cls.report2 = cls.app.run()
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_d2_exit_and_keys(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        r = self.report
        for k in TOP_KEYS:
            self.assertIn(k, r)
        for k in GEN_KEYS:
            self.assertIn(k, r["generated_by"])
        self.assertEqual(len(r["generated_by"]["git_commit"]), 40)
        self.assertIsInstance(r["generated_by"]["code_dirty"], bool)
        self.assertEqual(set(r["config"]["values"]) >= {"hold_ms", "still_speed"}, True)
        self.assertEqual(len(r["config"]["sha256"]), 64)
        self.assertEqual(r["checkpoint"]["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, CKPT)))
        self.assertEqual(r["checkpoint"]["path"], "checkpoints/alphabet_best.pt")
        self.assertEqual(r["config"]["path"], "configs/level1_realtime.json")
        self.assertEqual(r["source"], {"kind": "video", "id": CLIP.replace("\\", "/"), "mode": "headless",
                                       "fps_file": r["source"]["fps_file"]})
        self.assertGreater(r["source"]["fps_file"], 0)
        self.assertEqual(r["frame_size"], {"width": 640, "height": 480})
        self.assertIn("mediapipe_first_ms", r["warmup"])
        self.assertIn("classify_first_ms", r["warmup"])
        for s in STAGES:
            self.assertEqual(set(r["stages"][s]), {"n", "mean", "p50", "p95"})
        self.assertEqual(r["stages"]["mediapipe"]["n"], r["counts"]["frames_processed"])
        for k in COUNT_KEYS:
            self.assertIn(k, r["counts"])
        self.assertEqual(r["counts"]["frames_read"], r["counts"]["frames_processed"])
        self.assertEqual(r["counts"]["frames_dropped"], 0)
        self.assertGreaterEqual(len(r["segments"]), 1)
        for seg in r["segments"]:
            for k in SEG_KEYS:
                self.assertIn(k, seg)
        self.assertEqual(r["stages"]["classify"]["n"], len(r["segments"]))
        from src.inference.fingerspelling_compose import compose
        self.assertEqual(r["text"], compose(r["tokens"])["text"])

    def test_d2_prediction_equals_classify_again(self):
        clf = Level1Classifier.from_checkpoint(os.path.join(PROJECT_ROOT, CKPT))
        kept = {s.seq: s for s in self.app.kept_segments}
        self.assertEqual(sorted(kept), [s["seq"] for s in self.report2["segments"]])
        for seg in self.report2["segments"]:
            again = clf.classify(kept[seg["seq"]], 5)
            self.assertEqual(seg["status"], again["status"])
            self.assertEqual(seg["prediction"], again.get("prediction"))
            self.assertEqual(seg["confidence"], again.get("confidence"))
            self.assertEqual(seg["frames"], kept[seg["seq"]].n_frames)

    def test_d2_two_runs_identical(self):
        a, b = self.report, self.report2
        self.assertEqual(a["tokens"], b["tokens"])
        self.assertEqual(a["text"], b["text"])
        self.assertEqual(a["segments"], b["segments"])  # content timestamps only (i * 1000 / fps), no wall time
        self.assertEqual(a["counts"]["frames_processed"], b["counts"]["frames_processed"])


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestLatestFrameSlotD3(unittest.TestCase):
    def setUp(self):
        self.reader = app_mod.VideoFileReader(os.path.join(PROJECT_ROOT, CLIP))

    def tearDown(self):
        self.reader.release()

    def test_d3_newest_frame_and_dropped(self):
        slot = app_mod.LatestFrameSlot()
        frames = [self.reader.read() for _ in range(5)]
        for i, f in enumerate(frames[:3]):
            slot.put(f, float(i), float(i))
        seq, frame, _t, _ts = slot.get(timeout=0.1)
        self.assertEqual(seq, 3)
        self.assertIs(frame, frames[2])
        self.assertEqual(slot.dropped, 2)
        self.assertIsNone(slot.get(timeout=0.01))  # nothing newer
        slot.put(frames[3], 3.0, 3.0)
        self.assertEqual(slot.get(timeout=0.1)[0], 4)
        slot.put(frames[4], 4.0, 4.0)
        slot.close()
        self.assertEqual(slot.get(timeout=0.1)[0], 5)  # the last frame is still delivered after close
        self.assertIsNone(slot.get(timeout=0.01))
        self.assertEqual(slot.dropped, 2)

    def test_d3_slow_consumer_with_capture_thread(self):
        slot = app_mod.LatestFrameSlot()
        cap = app_mod.CaptureThread(self.reader, slot, paced=True, origin=time.perf_counter())
        cap.start()
        got = []
        while True:
            item = slot.get(timeout=0.5)
            if item is None:
                if slot.closed:
                    break
                continue
            got.append(item[0])
            time.sleep(0.12)  # slower than the file's frame rate
        cap.join()
        self.assertGreater(len(got), 1)
        self.assertEqual(got, sorted(set(got)))            # never an older (or the same) frame again
        self.assertEqual(got[-1], cap.frames_read)          # the newest frame is the last one delivered
        self.assertGreater(slot.dropped, 0)
        self.assertEqual(len(got) + slot.dropped, cap.frames_read)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHudOffscreen(unittest.TestCase):
    """Window drawing without a window: landmarks drawn on the processed (unmirrored) frame, mirror for display
    only, Vietnamese text panel stacked below the image and rebuilt only when its text changes."""

    def test_hud_compose_and_mirror(self):
        from src.inference.hand_live import HandLandmarkSession
        from src.inference.level1_core import load_level1_config
        values = load_level1_config(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"))["values"]
        reader = app_mod.VideoFileReader(os.path.join(PROJECT_ROOT, CLIP))
        session = HandLandmarkSession()
        try:
            frame = None
            for _ in range(20):
                frame = reader.read()
                lms, _hd, _sc = session.process(frame)
        finally:
            session.close()
            reader.release()
        self.assertIsNotNone(lms)
        drawn = frame.copy()
        app_mod.draw_landmarks(drawn, lms)
        self.assertFalse(np.array_equal(drawn, frame))
        mirrored = app_mod.display_view(drawn, True)
        self.assertTrue(np.array_equal(mirrored, drawn[:, ::-1]))
        self.assertIs(app_mod.display_view(drawn, False), drawn)
        hud = app_mod.Hud(app_mod.find_font(None, values["font_paths"]), values["hud_font_size"])
        big, small = ["Văn bản: mẹ cá"], ["Trạng thái: đang giữ yên"]
        out = hud.compose(mirrored, big, small, 0.0)
        h, w = mirrored.shape[:2]
        self.assertEqual(out.shape[1], w)
        self.assertGreater(out.shape[0], h)
        self.assertTrue(np.array_equal(out[:h], mirrored))  # the camera image is not covered
        panel = hud._panel
        hud.compose(mirrored, big, small, 0.5)
        self.assertIs(hud._panel, panel)                      # same text: cached panel reused
        hud.compose(mirrored, ["Văn bản: mẹ"], small, 0.0)
        self.assertIsNot(hud._panel, panel)

    def test_missing_font_stops(self):
        with self.assertRaises(app_mod.SourceError):
            app_mod.find_font(None, [os.path.join(PROJECT_ROOT, "_no_such_font_.ttf")])
        with self.assertRaises(app_mod.SourceError):
            app_mod.find_font(os.path.join(PROJECT_ROOT, "_no_such_font_.ttf"), [])


class TestDefaultPaths(unittest.TestCase):
    def test_defaults_found_from_another_directory(self):
        tmp = tempfile.mkdtemp(prefix="vslt_p15_cwd_")
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            for rel in (app_mod.DEFAULT_CONFIG, app_mod.DEFAULT_CHECKPOINT):
                full = app_mod.resolve_path(rel)
                self.assertEqual(os.path.normcase(os.path.abspath(full)),
                                 os.path.normcase(os.path.join(PROJECT_ROOT, rel)))
                self.assertEqual(app_mod.report_path(full), rel.replace(os.sep, "/"))
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmp, ignore_errors=True)


class _CaptureWithoutRate:
    """Capture object for D4 (defined in the test): opens, but its frame rate property is unreadable."""

    def __init__(self, value):
        self.value = value

    def isOpened(self):
        return True

    def get(self, prop):
        return self.value

    def release(self):
        pass


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestNoFrameRateD4(unittest.TestCase):
    def test_d4_reader_refuses_unknown_rate(self):
        for value in (0.0, -1.0, float("nan"), None):
            with self.subTest(value=value), self.assertRaises(app_mod.SourceError) as cm:
                app_mod.VideoFileReader(os.path.join(PROJECT_ROOT, CLIP),
                                        capture_factory=lambda p, v=value: _CaptureWithoutRate(v))
            self.assertIn("frame rate", str(cm.exception))

    def test_d4_cli_exit_code(self):
        tmp = tempfile.mkdtemp(prefix="vslt_p15_d4_")
        try:
            bad = os.path.join(tmp, "not_a_video.mp4")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("this file is not a video\n")
            out = os.path.join(tmp, "o.json")
            r = subprocess.run([PY, "level1_demo.py", "--source", bad, "--headless", "--out-json", out],
                               cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV, timeout=600)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("level1_demo:", r.stderr)
            self.assertFalse(os.path.exists(out))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class _SlowClassifier:
    """Deliberately slow classifier for D5 (defined in the test): wraps the real one, sleeps, and records how many
    frames the app processed while it was running and on which thread it ran."""

    def __init__(self, inner, delay_s):
        self.inner, self.delay_s = inner, delay_s
        self.min_detected_frames = inner.min_detected_frames
        self.app = None
        self.calls = []

    def warmup(self):
        return self.inner.warmup()

    def classify(self, segment, top_k):
        before = self.app.counts["frames_processed"]
        time.sleep(self.delay_s)
        after = self.app.counts["frames_processed"]
        self.calls.append({"thread": threading.current_thread(), "processed_meanwhile": after - before})
        return self.inner.classify(segment, top_k)


# clips with a hold segment well before the end (the first one is the D2 clip); the test uses the first whose run
# classifies a segment while frames are still coming
D5_CLIPS = (CLIP,
            os.path.join("data", "external", "hauuto_raw", "raw", "raw", "hau", "a_hau_A_002.mp4"),
            os.path.join("data", "external", "hauuto_raw", "raw", "raw", "hau", "b_hau_A_001.mp4"))


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestWorkerD5(unittest.TestCase):
    def test_d5_classify_not_on_main_loop(self):
        inner = Level1Classifier.from_checkpoint(os.path.join(PROJECT_ROOT, CKPT))
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            for clip in D5_CLIPS:
                if not os.path.exists(clip):
                    continue
                slow = _SlowClassifier(inner, 0.5)
                app = app_mod.Level1App(args_for("--source", clip, "--pace", "realtime", "--headless"),
                                        classifier=slow)
                slow.app = app
                report = app.run()
                self.assertEqual(report["source"]["mode"], "paced")
                self.assertTrue(slow.calls)
                for c in slow.calls:
                    self.assertIsNot(c["thread"], threading.main_thread())
                if any(c["processed_meanwhile"] > 1 for c in slow.calls):
                    return
            self.fail("no clip classified a segment while frames were still being processed")
        finally:
            os.chdir(cwd)


# ------------------------------------------------------------------------------------------------- AC-L (B5)
FRAME_STAGES = STAGES[:7]
SIGN_STAGES = STAGES[7:]
DRAWN_STAGES = ("draw_landmarks", "hud", "display")
TMP_PARENT = os.path.join(PROJECT_ROOT, "_work", "_plan15_tmp")


def _git_out(*args):
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout.strip()


class _WindowRecorder:
    """Stands in for the OpenCV window calls in the AC-L window-mode test (defined in the test; no window opens):
    records the images given to imshow; every other step of the frame path is the app's own."""

    def __init__(self):
        self.shown = []

    def imshow(self, name, image):
        self.shown.append(image.shape)

    @staticmethod
    def waitKey(delay):
        return -1

    @staticmethod
    def getWindowProperty(name, prop):
        return 1.0

    @staticmethod
    def namedWindow(*a, **k):
        return None

    @staticmethod
    def destroyAllWindows():
        return None


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestLatencyAcL(unittest.TestCase):
    """AC-L L1 / L2 / L3 (generation mechanism) on real runs of the app over the D2 clip: headless (the D2 command),
    paced headless (CLI), paced in window mode (window calls recorded, see _WindowRecorder)."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_l_", dir=TMP_PARENT)
        cls.runs = {}
        for name, extra in (("headless", ["--headless"]), ("paced", ["--pace", "realtime", "--headless"])):
            out = os.path.join(cls.tmp, name + ".json")
            proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, *extra, "--out-json", out],
                                  cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV, timeout=900)
            report = None
            if proc.returncode == 0:
                with open(out, encoding="utf-8") as f:
                    report = json.load(f)
            cls.runs[name] = (proc, report)
        cls.head = _git_out("rev-parse", "HEAD")
        cls.dirty = bool(_git_out("status", "--porcelain", "--", *app_mod.CODE_PATHS))
        rec = cls.recorder = _WindowRecorder()
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            from unittest import mock
            with mock.patch.multiple(app_mod.cv2, imshow=rec.imshow, waitKey=rec.waitKey,
                                     getWindowProperty=rec.getWindowProperty, namedWindow=rec.namedWindow,
                                     destroyAllWindows=rec.destroyAllWindows):
                cls.window_report = app_mod.Level1App(args_for("--source", CLIP, "--pace", "realtime")).run()
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def report(self, name):
        proc, report = self.runs[name]
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return report

    def check_stage_shape(self, r):
        self.assertEqual(tuple(r["stages"]), STAGES)  # 7 frame stages + 2 sign stages, nothing else
        for s in STAGES:
            st = r["stages"][s]
            self.assertEqual(set(st), {"n", "mean", "p50", "p95"})
            if st["n"] == 0:
                self.assertEqual((st["mean"], st["p50"], st["p95"]), (None, None, None))
            else:
                for k in ("mean", "p50", "p95"):
                    self.assertTrue(np.isfinite(st[k]) and st[k] >= 0, (s, k, st[k]))
                self.assertLessEqual(st["p50"], st["p95"])
        processed = r["counts"]["frames_processed"]
        self.assertGreater(processed, 0)
        self.assertEqual(r["stages"]["mediapipe"]["n"], processed)  # warm-up runs are not in the stages
        for s in ("capture_age", "segmenter", "frame_total"):
            self.assertEqual(r["stages"][s]["n"], processed, s)
        self.assertGreaterEqual(len(r["segments"]), 1)
        self.assertEqual(r["stages"]["classify"]["n"], len(r["segments"]))
        self.assertEqual(set(r["warmup"]), {"mediapipe_first_ms", "classify_first_ms"})
        for v in r["warmup"].values():
            self.assertIsInstance(v, float)
            self.assertGreater(v, 0.0)

    def test_l1_headless_d2_json(self):
        r = self.report("headless")
        self.check_stage_shape(r)
        self.assertEqual(r["source"]["mode"], "headless")
        for s in DRAWN_STAGES:  # nothing drawn or shown without a window
            self.assertEqual(r["stages"][s]["n"], 0, s)
        self.assertEqual(r["stages"]["emit_to_token"]["n"], len(r["segments"]))
        self.assertEqual(r["counts"]["dropped"], 0)
        self.assertEqual(r["counts"]["results_not_displayed"], 0)
        self.assertGreater(r["counts"]["capture_fps"], 0.0)

    def test_l1_l2_paced_json(self):
        r = self.report("paced")
        self.check_stage_shape(r)
        self.assertEqual(r["source"]["mode"], "paced")
        c = r["counts"]
        self.assertIn("dropped", c)
        self.assertIsInstance(c["dropped"], int)
        self.assertEqual(c["dropped"], c["frames_dropped"])
        self.assertEqual(c["frames_processed"] + c["dropped"], c["frames_read"])  # each frame read: processed or dropped
        self.assertEqual(c["frames_read"], self.report("headless")["counts"]["frames_read"])  # the whole file was read
        self.assertGreater(c["capture_fps"], 0.0)
        self.assertGreater(c["processing_fps"], 0.0)
        for s in DRAWN_STAGES:
            self.assertEqual(r["stages"][s]["n"], 0, s)
        self.assertEqual(r["stages"]["emit_to_token"]["n"], len(r["segments"]))

    def test_l1_window_mode_measures_every_stage(self):
        r = self.window_report
        self.check_stage_shape(r)
        self.assertEqual(r["source"]["mode"], "paced")
        processed = r["counts"]["frames_processed"]
        for s in FRAME_STAGES:
            self.assertEqual(r["stages"][s]["n"], processed, s)
        self.assertEqual(len(self.recorder.shown), processed)
        h = r["frame_size"]["height"]
        for shape in self.recorder.shown:
            self.assertGreater(shape[0], h)  # camera image + HUD panel below it
        self.assertEqual(r["stages"]["emit_to_token"]["n"] + r["counts"]["results_not_displayed"],
                         r["stages"]["classify"]["n"])
        self.assertEqual(r["counts"]["frames_processed"] + r["counts"]["dropped"], r["counts"]["frames_read"])

    def test_l3_generated_by_commit_and_dirty_flag(self):
        self.assertEqual(app_mod.CODE_PATHS, ("level1_demo.py", "src", "configs/level1_realtime.json"))
        for r in (self.report("headless"), self.report("paced"), self.window_report):
            g = r["generated_by"]
            self.assertEqual(g["git_commit"], self.head)
            self.assertIs(g["code_dirty"], self.dirty)


class TestHudStatsLines(unittest.TestCase):
    """The HUD shows a rolling p50 of every stage (last `rolling` values) + processed/s + dropped frames."""

    def test_rolling_p50_every_stage(self):
        from src.inference.level1_timing import StageTimes
        times = StageTimes(STAGES, rolling=3)
        for i, s in enumerate(STAGES[:-1]):  # emit_to_token left empty
            for v in (1000.0, 1000.0, 2.0 + i, 4.0 + i, 3.0 + i):  # the two first values leave the window
                times.add(s, v)
        starts = [0.0, 0.1, 0.2, 0.3, 0.4]
        lines = app_mod.hud_stats_lines(times, starts, rolling=3, dropped=7)
        self.assertEqual(len(lines), 2)
        text = "\n".join(lines)
        labels = dict(app_mod.HUD_STAGE_LABELS)
        self.assertEqual(set(labels), set(STAGES))
        for i, s in enumerate(STAGES[:-1]):
            self.assertIn(f"{labels[s]} {float(np.median([2.0 + i, 4.0 + i, 3.0 + i])):.1f}", text)
        self.assertIn(f"{labels['emit_to_token']} n/a", text)
        self.assertIn("processed/s 10.0", text)  # 2 intervals over the last 3 starts, 0.2 s
        self.assertIn("dropped 7", text)
        self.assertTrue(text.isascii())  # drawn with cv2.putText

    def test_panel_reserves_stats_lines(self):
        from src.inference.level1_core import load_level1_config
        values = load_level1_config(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"))["values"]
        hud = app_mod.Hud(app_mod.find_font(None, values["font_paths"]), values["hud_font_size"])
        view = np.zeros((48, 320, 3), dtype=np.uint8)
        one = hud.compose(view, ["Văn bản: bá"], ["x"], 0.0, ["a"])
        two = hud.compose(view, ["Văn bản: bá"], ["x"], 0.0, ["a", "b"])
        self.assertEqual(two.shape[0] - one.shape[0], hud.small_h)
        self.assertTrue(np.array_equal(two[:48], view))


class TestHudTextboxAcTD(unittest.TestCase):
    """Plan 15 Lần sửa 1 §5 AC-TD: HUD textbox rendering & key actions (offscreen, no GUI)."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import load_level1_config
        values = load_level1_config(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"))["values"]
        cls.font_path = app_mod.find_font(None, values["font_paths"])
        cls.font_size = values["hud_font_size"]
        cls.hud = app_mod.Hud(cls.font_path, cls.font_size)

    def test_td1_camera_image_not_covered(self):
        from src.inference.level1_textbox import textbox_view
        view = np.full((100, 320, 3), 123, dtype=np.uint8)
        tb_view = textbox_view(["b", "a"])
        out = self.hud.compose(view, tb_view, ["small line"], 0.5)
        self.assertEqual(out.shape[1], 320)
        self.assertGreater(out.shape[0], 100)
        self.assertTrue(np.array_equal(out[:100, :320], view))

    def test_td2_highlight_in_active_not_committed(self):
        from src.inference.level1_textbox import textbox_view
        tb_view = textbox_view(["m", "e", "dấu nặng", " ", "c", "a", "dấu sắc"])
        panel = self.hud._build(640, tb_view, [], 0)

        x0 = 8
        w_comm = int(round(self.hud.font.getlength("mẹ ")))
        x_comm_end = x0 + w_comm
        w_act = int(round(self.hud.font.getlength("cá")))
        x_act_end = x_comm_end + w_act

        y0 = 4
        y1 = y0 + self.hud.line_h

        comm_box = panel[y0:y1, x0:x_comm_end]
        has_hl_in_comm = np.any(np.all(comm_box == self.hud.HIGHLIGHT_BGR, axis=-1))
        self.assertFalse(has_hl_in_comm, "Highlight color found in committed region")

        act_box = panel[y0:y1, x_comm_end:x_act_end]
        has_hl_in_act = np.any(np.all(act_box == self.hud.HIGHLIGHT_BGR, axis=-1))
        self.assertTrue(has_hl_in_act, "Highlight color missing in active region")

    def test_td3_cursor_column_has_cursor_color(self):
        from src.inference.level1_textbox import textbox_view
        tb_view = textbox_view(["m", "e", "dấu nặng", " ", "c", "a", "dấu sắc"])
        panel = self.hud._build(640, tb_view, [], 0)

        x0 = 8
        x_cursor = x0 + int(round(self.hud.font.getlength("mẹ cá")))
        y0 = 4
        y1 = y0 + self.hud.line_h

        col_cursor = panel[y0:y1, x_cursor]
        has_cursor = np.any(np.all(col_cursor == self.hud.CURSOR_BGR, axis=-1))
        self.assertTrue(has_cursor, "Cursor color missing in cursor column")

    def test_td4_preview_muted_color_right_of_cursor(self):
        from src.inference.level1_textbox import textbox_view
        tb_view_no_prev = textbox_view(["c", "a", "dấu sắc"])
        panel_no_prev = self.hud._build(640, tb_view_no_prev, [], 0)

        x0 = 8
        x_cursor = x0 + int(round(self.hud.font.getlength("cá")))
        y0 = 4
        y1 = y0 + self.hud.line_h

        right_no_prev = panel_no_prev[y0:y1, x_cursor + 2:]
        self.assertFalse(np.any(np.all(right_no_prev == self.hud.PREVIEW_BGR, axis=-1)))

        tb_view_with_prev = textbox_view(
            ["c", "a", "dấu sắc"],
            rejected={"prediction": "dấu huyền", "confidence": 0.4},
        )
        panel_with_prev = self.hud._build(640, tb_view_with_prev, [], 0)

        right_with_prev = panel_with_prev[y0:y1, x_cursor + 2:]
        self.assertTrue(np.any(np.all(right_with_prev == self.hud.PREVIEW_BGR, axis=-1)))

    def test_td5_long_text_within_panel_and_ellipsis(self):
        from src.inference.level1_textbox import textbox_view
        tokens = ["b", "a", " "] * 39 + ["c", "a"]
        tb_view = textbox_view(tokens)

        panel_width = 640
        panel = self.hud._build(panel_width, tb_view, [], 0)

        disp_committed = self.hud._fit_committed(tb_view["committed"], tb_view["active"], panel_width - 24 - 8)
        self.assertIn("…", disp_committed)
        self.assertEqual(tb_view["active"], "ca")

        x0 = 8
        x_cursor = x0 + int(round(self.hud.font.getlength(disp_committed + tb_view["active"])))
        self.assertLess(x_cursor, panel_width)
        self.assertGreater(x_cursor, 0)

    def test_td6_caching(self):
        from src.inference.level1_textbox import textbox_view
        view = np.zeros((100, 320, 3), dtype=np.uint8)
        tb_view1 = textbox_view(["b", "a"])
        out1 = self.hud.compose(view, tb_view1, ["status: ok"], 0.0)
        p1 = self.hud._panel

        out2 = self.hud.compose(view, tb_view1, ["status: ok"], 0.5)
        self.assertIs(self.hud._panel, p1)

        tb_view2 = textbox_view(["b", "a", "dấu sắc"])
        out3 = self.hud.compose(view, tb_view2, ["status: ok"], 0.5)
        self.assertIsNot(self.hud._panel, p1)

    def test_td7_keys_1_to_5(self):
        app = app_mod.Level1App(args_for("--source", CLIP, "--headless"))
        self.assertEqual(app.speller.tokens, [])
        keys = [
            (ord("1"), "tone_1", "dấu sắc"),
            (ord("2"), "tone_2", "dấu huyền"),
            (ord("3"), "tone_3", "dấu hỏi"),
            (ord("4"), "tone_4", "dấu ngã"),
            (ord("5"), "tone_5", "dấu nặng"),
        ]
        for code, name, expected_token in keys:
            app._key(code)
            self.assertEqual(app.speller.tokens[-1], expected_token)
            ev = app.speller.events[-1]
            self.assertEqual(ev["source"], "key")
            self.assertEqual(ev["key"], name)
            self.assertEqual(ev["token"], expected_token)


# ------------------------------------------------------------------ plan 15 lần sửa 4 §3.1 / §5: AC-K3 (key n "chữ kế")
@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestNextKeyK3(unittest.TestCase):
    """AC-K3: Level1App._key(ord("n")) calls the re-arm function of the segmenter (rearm_mode motion_pose), logs a key
    event with source 'key' and adds no token."""

    def _app(self):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless"))
        finally:
            os.chdir(cwd)

    def test_k3_key_n_maps_to_next(self):
        self.assertEqual(app_mod.KEY_ACTIONS[ord("n")], "next")

    def test_k3_motion_pose_calls_force_rearm_no_token(self):
        app = self._app()
        calls = []
        app.segmenter.force_rearm = lambda ts: calls.append(ts)
        tokens_before, speller_events_before = list(app.speller.tokens), list(app.speller.events)
        app.last_ts = 1234.0
        app._key(ord("n"))
        self.assertEqual(calls, [1234.0])
        self.assertEqual(app.speller.tokens, tokens_before)
        self.assertEqual(app.speller.events, speller_events_before)
        self.assertEqual(app.events[-1], {"event": "key", "key": "next", "source": "key", "t_ms": 1234.0})

    def test_k3_hud_help_line_lists_n(self):
        app = self._app()
        _view, small, _progress, _stats = app._hud_lines()
        self.assertTrue(any("n chữ kế" in line for line in small), small)


# ------------------------------------------------------------------ plan 15 lần sửa 4 §3.4 / §5: AC-A1…A5 (classifier re-arm in the app)
def _config_with(tmp_dir, **values):
    """Copy of configs/level1_realtime.json with some values changed (written under _work/, removed by the test)."""
    with open(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"), encoding="utf-8") as f:
        raw = json.load(f)
    for k, v in values.items():
        raw[k] = dict(raw[k], value=v)
    path = os.path.join(tmp_dir, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    return path


BEFORE_D2_COMMIT = "12bd961"  # level1_demo.py before the classifier path (AC-A2 reference)


def before_d2_app_module():
    """level1_demo.py at BEFORE_D2_COMMIT loaded from `git show` into a temporary in-memory module (nothing written)."""
    import types
    r = subprocess.run(["git", "show", f"{BEFORE_D2_COMMIT}:level1_demo.py"], cwd=PROJECT_ROOT, capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {BEFORE_D2_COMMIT}:level1_demo.py failed: {r.stderr.strip()}")
    name = f"_level1_demo_ref_{BEFORE_D2_COMMIT}"
    mod = types.ModuleType(name)
    mod.__file__ = os.path.join(PROJECT_ROOT, "level1_demo.py")  # same ROOT as the real file
    sys.modules[name] = mod
    try:
        exec(compile(r.stdout, f"<git show {BEFORE_D2_COMMIT}:level1_demo.py>", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestClassifierModeA1A2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_a_", dir=TMP_PARENT)
        cls.cfg = _config_with(cls.tmp, rearm_mode="classifier")
        cls.out = os.path.join(cls.tmp, "a1.json")
        cls.proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, "--headless", "--config", cls.cfg,
                                   "--out-json", cls.out], cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV,
                                  timeout=900)
        cls.report = None
        if cls.proc.returncode == 0:
            with open(cls.out, encoding="utf-8") as f:
                cls.report = json.load(f)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.report2 = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", cls.cfg)).run()
            cls.motion_new = app_mod.Level1App(args_for("--source", CLIP, "--headless")).run()
            ref = before_d2_app_module()
            cls.motion_ref = ref.Level1App(ref.build_parser().parse_args(["--source", CLIP, "--headless"])).run()
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a1_classifier_headless(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        r = self.report
        self.assertEqual(r["rearm_mode"], "classifier")
        st = r["stages"]["window_classify"]
        self.assertEqual(set(st), {"n", "mean", "p50", "p95"})
        self.assertGreater(st["n"], 0)
        c = r["counts"]
        self.assertEqual(st["n"], c["window_results"])
        self.assertEqual(c["window_results"], c["window_jobs"])     # headless: every window classified
        self.assertEqual(c["window_dropped"], 0)
        self.assertEqual(r["stages"]["classify"]["n"], 0)          # segments are not classified
        self.assertEqual(c["segments_not_classified"], len(r["segments"]))
        self.assertEqual(c["label_emits"], len(r["labels"]))
        self.assertGreaterEqual(len(r["labels"]), 1)
        from src.inference.fingerspelling_compose import compose
        self.assertEqual(r["text"], compose(r["tokens"])["text"])
        model_tokens = [e for e in r["events"] if e.get("event") == "token" and e["source"] == "model"]
        self.assertEqual(len(model_tokens), len(r["labels"]))

    def test_a1_two_runs_identical(self):
        a, b = self.report, self.report2
        self.assertEqual(a["tokens"], b["tokens"])
        self.assertEqual(a["labels"], b["labels"])
        self.assertEqual(a["segments"], b["segments"])
        self.assertEqual(a["counts"]["window_jobs"], b["counts"]["window_jobs"])

    def test_a2_motion_pose_identical_to_before_d2(self):
        new, ref = self.motion_new, self.motion_ref
        self.assertEqual(new["rearm_mode"], "motion_pose")
        self.assertNotIn("window_classify", new["stages"])
        self.assertEqual(new["labels"], [])
        self.assertEqual(new["tokens"], ref["tokens"])
        self.assertEqual(new["segments"], ref["segments"])
        self.assertEqual(new["text"], ref["text"])
        self.assertGreaterEqual(len(new["segments"]), 1)


class _SlowWindowClassifier:
    """Deliberately slow classifier for AC-A3 (defined in the test): sleeps, records the thread and the frames the
    app processed meanwhile, returns a fixed 'ok' result (the decoder logic is AC-D, not this test)."""

    def __init__(self, inner, delay_s):
        self.inner, self.delay_s = inner, delay_s
        self.min_detected_frames = inner.min_detected_frames if inner is not None else 6
        self.app = None
        self.calls = []

    def warmup(self):
        return self.inner.warmup()

    def classify(self, segment, top_k):
        before = self.app.counts["frames_processed"] if self.app is not None else 0
        time.sleep(self.delay_s)
        after = self.app.counts["frames_processed"] if self.app is not None else 0
        self.calls.append({"thread": threading.current_thread(), "processed_meanwhile": after - before,
                           "t_emit": segment.t_emit_ms})
        return {"status": "ok", "prediction": "a", "confidence": 0.95}


class TestLatestWindowWorkerA3(unittest.TestCase):
    def test_a3_never_older_and_dropped_counted(self):
        from src.inference.level1_segmenter import SignSegment
        slow = _SlowWindowClassifier(None, 0.03)
        w = app_mod.LatestWindowWorker(slow, 5)
        w.start()
        returned, dropped_ids = [], []
        for k in range(40):
            seg = SignSegment(seq=k, raw_landmarks=np.zeros((1, 21, 3), np.float32), detected=np.ones(1, bool),
                              handedness=np.array(["Right"]), timestamps_ms=np.array([k * 5.0]), frame_width=640,
                              frame_height=480, t_start_ms=k * 5.0, t_end_ms=k * 5.0, t_emit_ms=k * 5.0,
                              close_reason="window")
            d = w.submit(k, k * 5.0, seg)
            if d is not None:
                dropped_ids.append(d)
            returned += w.poll()
            time.sleep(0.005)
        returned += w.finish()
        ids = [r[0] for r in returned]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(sorted(ids + dropped_ids), list(range(40)))  # every job: returned or dropped, never both
        self.assertEqual(w.dropped, len(dropped_ids))
        self.assertGreater(w.dropped, 0)
        self.assertEqual(w.submitted, 40)
        for c in slow.calls:
            self.assertIsNot(c["thread"], threading.main_thread())

    @unittest.skipUnless(not _MISSING, SKIP_REASON)
    def test_a3_paced_app_main_loop_keeps_running(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_a3_", dir=TMP_PARENT)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            inner = Level1Classifier.from_checkpoint(os.path.join(PROJECT_ROOT, CKPT))
            slow = _SlowWindowClassifier(inner, 0.3)
            app = app_mod.Level1App(args_for("--source", CLIP, "--pace", "realtime", "--headless", "--config",
                                             _config_with(tmp, rearm_mode="classifier")), classifier=slow)
            slow.app = app
            r = app.run()
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(r["source"]["mode"], "paced")
        c = r["counts"]
        self.assertTrue(slow.calls)
        for call in slow.calls:
            self.assertIsNot(call["thread"], threading.main_thread())
        t_emits = [call["t_emit"] for call in slow.calls]
        self.assertEqual(t_emits, sorted(t_emits))                 # never an older window after a newer one
        self.assertTrue(any(call["processed_meanwhile"] > 1 for call in slow.calls))
        self.assertGreater(c["window_dropped"], 0)
        self.assertEqual(c["window_results"] + c["window_dropped"], c["window_jobs"])
        self.assertEqual(c["window_results"], len(slow.calls))
        self.assertEqual(r["stages"]["window_classify"]["n"], c["window_results"])


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestNextKeyClassifierK3(unittest.TestCase):
    """AC-K3 in rearm_mode 'classifier': key n calls decoder.force_next (in timestamp order), not the segmenter."""

    def test_k3_classifier_calls_force_next_no_token(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_k3_", dir=TMP_PARENT)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            app = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config",
                                             _config_with(tmp, rearm_mode="classifier")))
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmp, ignore_errors=True)
        nexts, rearms = [], []
        app.decoder.force_next = lambda ts: nexts.append(ts)
        app.segmenter.force_rearm = lambda ts: rearms.append(ts)
        app.last_ts = 500.0
        app._key(ord("n"))
        self.assertEqual(nexts, [500.0])
        self.assertEqual(rearms, [])
        self.assertEqual(app.speller.tokens, [])
        self.assertEqual(app.events[-1], {"event": "key", "key": "next", "source": "key", "t_ms": 500.0})


DEMO_CONFIG = os.path.join("configs", "level1_demo_classifier.json")


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestDemoConfigW4(unittest.TestCase):
    """Plan 15 lần sửa 5 AC-W4: the demo command with the committed demo config (user decision (a)) runs in rearm_mode
    'classifier' on the D2 clip (a training clip: this checks the code path, not accuracy)."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_w4_", dir=TMP_PARENT)
        cls.out = os.path.join(cls.tmp, "w4.json")
        cls.proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                   "--out-json", cls.out], cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV,
                                  timeout=900)
        cls.report = None
        if cls.proc.returncode == 0:
            with open(cls.out, encoding="utf-8") as f:
                cls.report = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_w4_demo_config_runs_classifier_mode(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        r = self.report
        self.assertEqual(r["rearm_mode"], "classifier")
        self.assertEqual(r["config"]["path"], "configs/level1_demo_classifier.json")
        self.assertEqual(r["config"]["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, DEMO_CONFIG)))
        self.assertEqual(r["checkpoint"]["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, CKPT)))
        self.assertIn("window_classify", r["stages"])
        self.assertGreater(r["stages"]["window_classify"]["n"], 0)
        self.assertEqual(r["stages"]["classify"]["n"], 0)
        self.assertEqual(r["counts"]["label_emits"], len(r["labels"]))



# ------------------------------------------------------------------ plan 15 lần sửa 6 W1 / §7: AC-6b, AC-6c (--trace-windows)
BEFORE_REV6_COMMIT = "4f913a2"  # level1_demo.py before lần sửa 6 (AC-6a base)
TRACE_KEYS = ("ts_ms", "status", "top1", "conf", "top2", "conf2", "run_label", "run_ms", "last", "emitted")


def app_module_at(commit):
    """level1_demo.py at `commit` loaded from `git show` into a temporary in-memory module (nothing written)."""
    import types
    r = subprocess.run(["git", "show", f"{commit}:level1_demo.py"], cwd=PROJECT_ROOT, capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {commit}:level1_demo.py failed: {r.stderr.strip()}")
    name = f"_level1_demo_ref_{commit}"
    mod = types.ModuleType(name)
    mod.__file__ = os.path.join(PROJECT_ROOT, "level1_demo.py")
    sys.modules[name] = mod
    try:
        exec(compile(r.stdout, f"<git show {commit}:level1_demo.py>", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


def _key_tree(obj, depth=2):
    """Key set of a JSON report down to `depth` dict levels (the shape compared by AC-6b, not the values)."""
    if not isinstance(obj, dict) or depth == 0:
        return None
    return {k: _key_tree(v, depth - 1) for k, v in obj.items()}


def _without_rates(counts):
    return {k: v for k, v in counts.items() if k not in ("processing_fps", "capture_fps")}


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestTraceWindowsW1(unittest.TestCase):
    """AC-6b (trace off = the JSON of 4f913a2: same keys, same tokens/labels/segments in both re-arm modes) and AC-6c
    (trace on: one entry per window result with the §3.W1 keys, `emitted` = the labels, tokens unchanged; size limit).
    The D2 clip is a training clip: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_w1_", dir=TMP_PARENT)
        cls.out = os.path.join(cls.tmp, "trace.json")
        cls.proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                   "--trace-windows", "--out-json", cls.out], cwd=PROJECT_ROOT, capture_output=True,
                                  text=True, env=ENV, timeout=900)
        cls.cli = None
        if cls.proc.returncode == 0:
            with open(cls.out, encoding="utf-8") as f:
                cls.cli = json.load(f)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV6_COMMIT)
            cls.runs = {}
            for mode, extra in (("classifier", ["--config", DEMO_CONFIG]), ("motion_pose", [])):
                argv = ["--source", CLIP, "--headless", *extra]
                cls.runs[mode] = {
                    "ref": ref.Level1App(ref.build_parser().parse_args(argv)).run(),
                    "off": app_mod.Level1App(args_for(*argv)).run(),
                    "on": app_mod.Level1App(args_for(*argv, "--trace-windows")).run(),
                }
            from unittest import mock
            with mock.patch.object(app_mod, "TRACE_MAX_ENTRIES", 5):
                cls.small = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                                       "--trace-windows")).run()
            cls.paced = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--pace", "realtime", "--config",
                                                   DEMO_CONFIG, "--trace-windows")).run()
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_w1_help_lists_flag_default_off(self):
        self.assertIn("--trace-windows", app_mod.build_parser().format_help())
        self.assertFalse(args_for("--source", CLIP).trace_windows)
        self.assertTrue(args_for("--source", CLIP, "--trace-windows").trace_windows)

    def test_6b_trace_off_same_keys_and_tokens_as_before(self):
        for mode, r in self.runs.items():
            off, ref = r["off"], r["ref"]
            self.assertEqual(off["rearm_mode"], mode)
            self.assertNotIn("window_trace", off)
            self.assertEqual(list(off), list(ref), mode)                 # same top-level keys, same order
            self.assertEqual(_key_tree(off), _key_tree(ref), mode)       # and the same keys one level down
            for k in ("tokens", "text", "labels", "segments"):
                self.assertEqual(off[k], ref[k], (mode, k))
            self.assertEqual(_without_rates(off["counts"]), _without_rates(ref["counts"]), mode)

    def test_6c_trace_on_one_entry_per_window_result(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        for r in (self.cli, self.runs["classifier"]["on"], self.paced):
            wt = r["window_trace"]
            self.assertEqual(set(wt), {"max_entries", "n_windows", "truncated", "fields", "entries"})
            self.assertEqual(wt["max_entries"], 20000)
            self.assertFalse(wt["truncated"])
            self.assertEqual(tuple(wt["fields"]), TRACE_KEYS)
            self.assertGreater(r["counts"]["window_results"], 0)
            self.assertEqual(len(wt["entries"]), r["counts"]["window_results"])
            self.assertEqual(wt["n_windows"], r["counts"]["window_results"])
            ts = [e["ts_ms"] for e in wt["entries"]]
            self.assertEqual(ts, sorted(set(ts)))                        # timestamp order, one entry per window
            for e in wt["entries"]:
                self.assertEqual(tuple(e), TRACE_KEYS)
                self.assertEqual(e["status"], "ok")
                self.assertGreaterEqual(e["conf"], e["conf2"])
                self.assertGreaterEqual(e["run_ms"], 0.0)

    def test_6c_emitted_matches_labels(self):
        for r in (self.cli, self.runs["classifier"]["on"], self.paced):
            emitted = [e for e in r["window_trace"]["entries"] if e["emitted"] is not None]
            self.assertGreaterEqual(len(emitted), 1)
            self.assertEqual([e["emitted"] for e in emitted], [lab["seq"] for lab in r["labels"]])
            for e, lab in zip(emitted, r["labels"]):
                self.assertEqual((e["ts_ms"], e["top1"], e["conf"]),
                                 (lab["ts_ms"], lab["prediction"], lab["confidence"]))
                self.assertEqual(e["last"], lab["prediction"])
                self.assertEqual(e["run_label"], lab["prediction"])
                self.assertEqual(e["run_ms"], lab["ts_ms"] - lab["run_since_ms"])
                self.assertGreaterEqual(e["run_ms"], 300.0)              # cls_stable_ms of the demo config

    def test_6c_tokens_unchanged_by_trace(self):
        for mode, r in self.runs.items():
            for k in ("tokens", "text", "labels", "segments"):
                self.assertEqual(r["on"][k], r["off"][k], (mode, k))
            self.assertEqual(_without_rates(r["on"]["counts"]), _without_rates(r["off"]["counts"]), mode)
        self.assertEqual(self.cli["tokens"], self.runs["classifier"]["off"]["tokens"])
        mp = self.runs["motion_pose"]["on"]["window_trace"]            # motion_pose classifies no window
        self.assertEqual((mp["entries"], mp["n_windows"], mp["truncated"]), ([], 0, False))

    def test_6c_size_limit_truncated(self):
        wt, full = self.small["window_trace"], self.runs["classifier"]["on"]["window_trace"]
        self.assertGreater(full["n_windows"], 5)
        self.assertEqual(wt["max_entries"], 5)
        self.assertTrue(wt["truncated"])
        self.assertEqual(wt["n_windows"], self.small["counts"]["window_results"])
        self.assertEqual(wt["entries"], full["entries"][:5])             # the first entries are kept
        self.assertEqual(self.small["tokens"], self.runs["classifier"]["off"]["tokens"])

    def test_6c_no_landmarks_or_frames_in_trace(self):
        for e in self.runs["classifier"]["on"]["window_trace"]["entries"]:
            for v in e.values():
                self.assertTrue(v is None or isinstance(v, (str, int, float)), e)



# ------------------------------------------------------------------ plan 15 lần sửa 6 W2 / §7: AC-6d (HUD in rearm_mode classifier)
HUD_DECODER_RE = r"^\[classifier\] cửa sổ: (.+) (\d\.\d\d|—) \| giữ (\d+)/(\d+) \| cuối: (.+)$"


def _ok_result(label, conf, second="y", conf2=0.01):
    return {"status": "ok", "prediction": label, "confidence": conf,
            "candidates": [{"class": label, "confidence": conf}, {"class": second, "confidence": conf2}]}


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHudClassifierW2(unittest.TestCase):
    """AC-6d: rearm_mode classifier shows the decoder line `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<cls_stable_ms> |
    cuối: <last>` in place of the "Trạng thái" line, and no hold bar of the old segmenter; rearm_mode motion_pose draws a
    HUD image identical to the one of 4f913a2 (same synthetic state, same view)."""

    @classmethod
    def setUpClass(cls):
        import re
        cls.re = re.compile(HUD_DECODER_RE)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            from src.inference.level1_core import load_level1_config
            values = load_level1_config(os.path.join(PROJECT_ROOT, DEMO_CONFIG))["values"]
            cls.font, cls.size, cls.stable = app_mod.find_font(None, values["font_paths"]), values["hud_font_size"], \
                values["cls_stable_ms"]
            cls.ref_mod = app_module_at(BEFORE_REV6_COMMIT)
            cls.run_app = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                                     "--trace-windows"))
            cls.run_report = cls.run_app.run()
            cls.mp_new = app_mod.Level1App(args_for("--source", CLIP, "--headless"))
            cls.mp_new_fresh = app_mod.Level1App(args_for("--source", CLIP, "--headless"))
            cls.mp_new.run()
            ref_args = cls.ref_mod.build_parser().parse_args(["--source", CLIP, "--headless"])
            cls.mp_ref = cls.ref_mod.Level1App(ref_args)
            cls.mp_ref_fresh = cls.ref_mod.Level1App(ref_args)
            cls.mp_ref.run()
        finally:
            os.chdir(cwd)

    def _fresh_classifier_app(self):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", DEMO_CONFIG))
        finally:
            os.chdir(cwd)

    def _decoder_line(self, small):
        self.assertFalse(any(line.startswith("Trạng thái") for line in small), small)
        self.assertTrue(small[1].startswith("[classifier] "), small)   # in place of the "Trạng thái" line
        self.assertEqual(sum(1 for line in small if line.startswith("[classifier]")), 1)
        m = self.re.match(small[1])
        self.assertIsNotNone(m, small[1])
        return m.groups()

    def test_6d_line_after_real_run(self):
        app = self.run_app
        _view, small, progress, _stats = app._hud_lines()
        self.assertEqual(progress, 0.0)
        top1, conf, held, stable, last = self._decoder_line(small)
        w = self.run_report["window_trace"]["entries"][-1]
        self.assertEqual((top1, conf), (w["top1"], f"{w['conf']:.2f}"))
        self.assertEqual(int(held), round(w["run_ms"]) if w["run_label"] is not None else 0)
        self.assertEqual(int(stable), self.stable)
        self.assertEqual(last, app.decoder.last_label or "—")
        self.assertEqual(last, self.run_report["labels"][-1]["prediction"])

    def test_6d_line_follows_decoder_on_synthetic_windows(self):
        app = self._fresh_classifier_app()
        self.assertEqual(app._hud_lines()[1][1], f"[classifier] cửa sổ: — — | giữ 0/{self.stable} | cuối: —")
        lines = []
        for i, (label, conf) in enumerate([("b", 0.95)] * 12 + [("dấu hỏi", 0.6)] + [("c", 0.97)] * 3):
            app.timeline.append(["frame", 1000.0 + 33.0 * i, True, True, _ok_result(label, conf)])
            app._drain_timeline()
            lines.append(self._decoder_line(app._hud_lines()[1]))
        self.assertEqual(lines[0], ("b", "0.95", "0", str(self.stable), "—"))
        self.assertEqual(lines[8], ("b", "0.95", "264", str(self.stable), "—"))      # 8 x 33 ms < 300: not yet
        self.assertEqual(lines[10], ("b", "0.95", "330", str(self.stable), "b"))     # emitted at >= 300 ms
        self.assertEqual(lines[12], ("dấu hỏi", "0.60", "0", str(self.stable), "b"))  # below cls_conf: no run
        self.assertEqual(lines[15], ("c", "0.97", "66", str(self.stable), "b"))
        self.assertEqual([lab["prediction"] for lab in app.labels], ["b"])

    def test_6d_no_hold_bar_in_classifier_mode(self):
        from unittest import mock
        app = self._fresh_classifier_app()
        with mock.patch.object(app.segmenter, "status", return_value={"state": "holding", "hold_progress": 0.7}):
            view_c, small_c, progress_c, stats_c = app._hud_lines()
            mp_view, mp_small, mp_progress, _ = self.mp_new_fresh._hud_lines()
        self.assertEqual(progress_c, 0.0)
        self.assertEqual(len(small_c), len(mp_small))                  # same number of panel lines as motion_pose
        hud = app_mod.Hud(self.font, self.size)
        view = np.full((60, 640, 3), 90, dtype=np.uint8)
        out = hud.compose(view.copy(), view_c, small_c, progress_c, stats_c)
        green = np.all(out[60:63] == np.array([0, 200, 0], dtype=np.uint8), axis=-1)
        self.assertFalse(green.any())
        with mock.patch.object(self.mp_new_fresh.segmenter, "status",
                               return_value={"state": "holding", "hold_progress": 0.7}):
            self.assertEqual(self.mp_new_fresh._hud_lines()[2], 0.7)      # motion_pose keeps its bar

    def test_6d_paused_marked(self):
        app = self._fresh_classifier_app()
        app.paused = True
        line = app._hud_lines()[1][1]
        self.assertEqual(line, f"[classifier] cửa sổ: — — | giữ 0/{self.stable} | cuối: — | tạm dừng (p)")

    def test_6d_motion_pose_hud_image_identical_to_before(self):
        from unittest import mock
        view = np.full((120, 640, 3), 90, dtype=np.uint8)
        hold = {"state": "holding", "hold_progress": 0.6}
        states = [("fresh", self.mp_new_fresh, self.mp_ref_fresh, None, False),
                  ("after run", self.mp_new, self.mp_ref, None, False),
                  ("paused", self.mp_new, self.mp_ref, None, True),
                  ("holding", self.mp_new_fresh, self.mp_ref_fresh, hold, False)]
        for name, new, ref, status, paused in states:
            new.paused = ref.paused = paused
            try:
                with mock.patch.object(new.segmenter, "status", return_value=status) if status else _nullctx(), \
                        mock.patch.object(ref.segmenter, "status", return_value=status) if status else _nullctx():
                    nv, ns, np_, stats = new._hud_lines()
                    rv, rs, rp, _ = ref._hud_lines()
            finally:
                new.paused = ref.paused = False
            self.assertEqual((nv, ns, np_), (rv, rs, rp), name)
            img_new = app_mod.Hud(self.font, self.size).compose(view.copy(), nv, ns, np_, stats)
            img_ref = self.ref_mod.Hud(self.font, self.size).compose(view.copy(), rv, rs, rp, stats)
            self.assertTrue(np.array_equal(img_new, img_ref), name)


def _nullctx():
    import contextlib
    return contextlib.nullcontext()


# ------------------------------------------------------------------ plan 15 lần sửa 7 T2: --cls-window-ms
def _config_plus(tmp_dir, base, name, **values):
    """Copy of the config `base` with keys set or added ({value, source 'design', reason}), written under _work/ and
    removed by the test."""
    with open(os.path.join(PROJECT_ROOT, base), encoding="utf-8") as f:
        raw = json.load(f)
    for k, v in values.items():
        raw[k] = {"value": v, "source": "design", "reason": "test value (plan 15 lần sửa 7)"}
    path = os.path.join(tmp_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    return path


class TestClsWindowArgT2(unittest.TestCase):
    def test_t2_help_and_parsing(self):
        self.assertIn("--cls-window-ms", app_mod.build_parser().format_help())
        self.assertIsNone(args_for("--source", CLIP).cls_window_ms)
        self.assertEqual(args_for("--source", CLIP, "--cls-window-ms", "700").cls_window_ms, 700.0)
        self.assertEqual(args_for("--source", CLIP, "--cls-window-ms", "650.5").cls_window_ms, 650.5)
        import contextlib
        import io
        for bad in ("0", "-5", "abc", "nan", "inf", ""):
            with self.subTest(bad=bad), self.assertRaises(SystemExit), \
                    contextlib.redirect_stderr(io.StringIO()):
                args_for("--source", CLIP, "--cls-window-ms", bad)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestClsWindowFlagT2(unittest.TestCase):
    """--cls-window-ms N = the same run as a config whose cls_window_ms is N (the config file is not changed; the JSON
    records the override). The D2 clip is a training clip: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_t2_", dir=TMP_PARENT)
        cls.cfg700 = _config_plus(cls.tmp, DEMO_CONFIG, "w700.json", cls_window_ms=700.0)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.app_flag = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                                      "--cls-window-ms", "700"),
                                             argv=["--source", CLIP, "--headless", "--config", DEMO_CONFIG,
                                                   "--cls-window-ms", "700"])
            cls.flag = cls.app_flag.run()
            cls.cfg = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", cls.cfg700)).run()
            cls.plain = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", DEMO_CONFIG)).run()
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_t2_flag_equals_config_value(self):
        self.assertEqual(self.app_flag.window.window_ms, 700.0)
        self.assertEqual(self.app_flag.values["cls_window_ms"], 700.0)
        for k in ("tokens", "text", "labels", "segments"):
            self.assertEqual(self.flag[k], self.cfg[k], k)
        self.assertEqual(_without_rates(self.flag["counts"]), _without_rates(self.cfg["counts"]))
        self.assertGreater(self.flag["counts"]["window_results"], 0)

    def test_t2_report_records_the_override(self):
        c = self.flag["config"]
        self.assertEqual(c["overrides"], {"cls_window_ms": 700.0})
        self.assertEqual(c["path"], "configs/level1_demo_classifier.json")
        self.assertEqual(c["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, DEMO_CONFIG)))
        with open(os.path.join(PROJECT_ROOT, DEMO_CONFIG), encoding="utf-8") as f:
            self.assertEqual(c["values"], json.load(f))                  # the file as it is, not changed
        self.assertEqual(c["values"]["cls_window_ms"]["value"], 1000)
        self.assertNotIn("overrides", self.plain["config"])              # no flag: the report keeps its keys
        self.assertNotIn("overrides", self.cfg["config"])
        self.assertIn("--cls-window-ms", self.flag["generated_by"]["command"])

    def test_t2_flag_needs_classifier_mode(self):
        import contextlib
        import io
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            with self.assertRaises(app_mod.SourceError):
                app_mod.Level1App(args_for("--source", CLIP, "--headless", "--cls-window-ms", "700"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = app_mod.main(["--source", CLIP, "--headless", "--cls-window-ms", "700"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, app_mod.EXIT_INPUT_ERROR)
        self.assertIn("--cls-window-ms", err.getvalue())


# ------------------------------------------------------------------ plan 15 lần sửa 7 T3: AC-7c (--no-auto-space)
class TestNoAutoSpaceArgT3(unittest.TestCase):
    def test_t3_help_and_default(self):
        # lần sửa 12 S1: --auto-space / --no-auto-space (BooleanOptionalAction), default off
        text = app_mod.build_parser().format_help()
        self.assertIn("--no-auto-space", text)
        self.assertIn("--auto-space", text)
        self.assertFalse(args_new("--source", CLIP).auto_space)
        self.assertTrue(args_new("--source", CLIP, "--auto-space").auto_space)
        self.assertFalse(args_for("--source", CLIP, "--no-auto-space").auto_space)


from src.inference.hand_live import HandLandmarkSession  # noqa: E402


class _HandAwaySession(HandLandmarkSession):
    """The real MediaPipe session; after the first AWAY_FROM frames of a stream every frame is reported without a hand,
    as when the signer lowers the hand (the frames before carry the real landmarks)."""
    AWAY_FROM = 40

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n = 0

    def process(self, frame_bgr):
        out = super().process(frame_bgr)
        self.n += 1
        return out if self.n <= self.AWAY_FROM else (None, "", None)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestNoAutoSpaceT3(unittest.TestCase):
    """AC-7c: with --no-auto-space a hand away for longer than word_gap_ms adds no space to the text (the word gap is
    still detected and counted); the Space key still adds one. Without the flag the space is added as before. The D2
    clip is a training clip: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import load_level1_config
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.word_gap_ms = {}
            cls.runs = {}
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", DEMO_CONFIG])):
                cfg = extra[1] if extra else app_mod.DEFAULT_CONFIG
                cls.word_gap_ms[mode] = load_level1_config(os.path.join(PROJECT_ROOT, cfg))["values"]["word_gap_ms"]
                for flag in (False, True):
                    argv = ["--source", CLIP, "--headless", *extra] + (["--no-auto-space"] if flag else [])
                    app = app_mod.Level1App(args_for(*argv), session_factory=_HandAwaySession)
                    cls.runs[(mode, flag)] = (app, app.run())
        finally:
            os.chdir(cwd)

    def test_7c_hand_away_longer_than_word_gap(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                _app, r = self.runs[(mode, False)]
                gaps = [e for e in r["events"] if e.get("event") == "word_gap"]
                self.assertEqual(len(gaps), 1)
                self.assertEqual(r["counts"]["word_gaps"], 1)
                last_hand = max(s["t_end_ms"] for s in r["segments"])          # hand_lost segment: last hand frame
                self.assertGreaterEqual(gaps[0]["t_ms"] - last_hand, self.word_gap_ms[mode])
                self.assertGreaterEqual(len([t for t in r["tokens"] if t != " "]), 1)

    def test_7c_without_flag_space_added(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[(mode, False)][1]
                self.assertEqual(r["tokens"][-1], " ")
                self.assertTrue(r["text"].endswith(" "))
                self.assertNotIn("auto_space", r)

    def test_7c_with_flag_no_space(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                off, on = self.runs[(mode, False)][1], self.runs[(mode, True)][1]
                self.assertNotIn(" ", on["tokens"])
                self.assertNotIn(" ", on["text"])
                self.assertEqual(on["tokens"], [t for t in off["tokens"] if t != " "])
                self.assertEqual(on["counts"]["word_gaps"], off["counts"]["word_gaps"])   # still detected
                self.assertEqual(on["labels"], off["labels"])
                self.assertEqual(on["segments"], off["segments"])
                gaps = [e for e in on["events"] if e.get("event") == "word_gap"]
                self.assertEqual(len(gaps), 1)
                self.assertIs(gaps[0]["auto_space"], False)
                self.assertIs(on["auto_space"], False)
                spaces = [e for e in on["events"] if e.get("token") == " "]
                self.assertEqual(spaces, [])

    def test_7c_space_key_still_works(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                app, r = self.runs[(mode, True)]
                n = len(app.speller.tokens)
                app._key(32)                                                  # Space key
                self.assertEqual(app.speller.tokens[n:], [" "])

    def test_7c_word_gap_event_unit(self):
        """A WordGap of the segmenter, pushed through the app in both re-arm modes."""
        from src.inference.level1_segmenter import WordGap
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", DEMO_CONFIG])):
                for flag in (False, True):
                    with self.subTest(mode=mode, flag=flag):
                        argv = ["--source", CLIP, "--headless", *extra] + (["--no-auto-space"] if flag else [])
                        app = app_mod.Level1App(args_for(*argv))
                        app.speller.key("tone_1", t_ms=100.0)                    # one token before the gap
                        app._on_events([WordGap(seq=1, t_ms=2000.0)])
                        self.assertEqual(app.speller.tokens, ["dấu sắc"] if flag else ["dấu sắc", " "])
                        self.assertEqual(app.counts["word_gaps"], 1)
        finally:
            os.chdir(cwd)


# ------------------------------------------------------------------ plan 15 lần sửa 7 T4: HUD line for a held tone mark
HUD_TONE_RE = r"^\[classifier\] cửa sổ: (.+) (\d\.\d\d|—) \| giữ (\d+)/(\d+) \(tone\) \| cuối: (.+)$"


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHudToneT4(unittest.TestCase):
    """T4: while the decoder holds a run of a tone mark the line shows the stable time used for tone marks and
    `(tone)`: `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<stable_tone> (tone) | cuối: <last>`; a letter run or no
    run keeps the line of lần sửa 6 (HUD_DECODER_RE)."""

    @classmethod
    def setUpClass(cls):
        import re
        cls.re_tone, cls.re_letter = re.compile(HUD_TONE_RE), re.compile(HUD_DECODER_RE)
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_t4_", dir=TMP_PARENT)
        cls.cfg_tone = _config_plus(cls.tmp, DEMO_CONFIG, "tone.json", cls_conf_tone=0.78, cls_stable_ms_tone=200.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _app(self, config):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", config))
        finally:
            os.chdir(cwd)

    def _feed(self, app, windows, t0=1000.0, dt=33.0):
        lines = []
        for i, (label, conf) in enumerate(windows):
            app.timeline.append(["frame", t0 + dt * i, True, True, _ok_result(label, conf)])
            app._drain_timeline()
            lines.append(app._hud_lines()[1][1])
        return lines

    def test_t4_tone_line_with_tone_keys(self):
        app = self._app(self.cfg_tone)
        lines = self._feed(app, [("dấu huyền", 0.80)] * 9 + [("b", 0.95)] * 12)
        m = [self.re_tone.match(x) for x in lines[:9]]
        self.assertTrue(all(m), lines[:9])
        self.assertEqual(m[0].groups(), ("dấu huyền", "0.80", "0", "200", "—"))
        self.assertEqual(m[6].groups(), ("dấu huyền", "0.80", "198", "200", "—"))     # 6 x 33 ms < 200: not yet
        self.assertEqual(m[7].groups(), ("dấu huyền", "0.80", "231", "200", "dấu huyền"))
        for x in lines[9:]:                                                           # a letter run: line of lần sửa 6
            self.assertIsNone(self.re_tone.match(x), x)
            self.assertIsNotNone(self.re_letter.match(x), x)
        self.assertEqual(self.re_letter.match(lines[19]).groups(), ("b", "0.95", "330", "300", "b"))
        self.assertEqual([lab["prediction"] for lab in app.labels], ["dấu huyền", "b"])

    def test_t4_tone_below_its_threshold_no_tone_mark(self):
        app = self._app(self.cfg_tone)
        line = self._feed(app, [("dấu hỏi", 0.70)])[0]
        self.assertEqual(line, "[classifier] cửa sổ: dấu hỏi 0.70 | giữ 0/300 | cuối: —")

    def test_t4_tone_line_without_tone_keys(self):
        app = self._app(DEMO_CONFIG)                                  # stable time of a tone = cls_stable_ms
        lines = self._feed(app, [("dấu ngã", 0.95)] * 3)
        self.assertEqual(lines[2], "[classifier] cửa sổ: dấu ngã 0.95 | giữ 66/300 (tone) | cuối: —")

    def test_t4_tone_line_paused(self):
        app = self._app(self.cfg_tone)
        self._feed(app, [("dấu sắc", 0.80)] * 3)
        app.paused = True
        self.assertEqual(app._hud_lines()[1][1],
                         "[classifier] cửa sổ: dấu sắc 0.80 | giữ 66/200 (tone) | cuối: — | tạm dừng (p)")


class TestDesktopDocT4(unittest.TestCase):
    def test_t4_doc_lists_new_flags_and_keys(self):
        import re
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        for text in ("--cls-window-ms", "--no-auto-space", "(tone)", "cls_conf_tone", "cls_stable_ms_tone",
                     "dropout_tolerance_ms", "config.overrides"):
            self.assertIn(text, doc, text)
        self.assertIsNone(re.search(r"\d+(\.\d+)?\s*(ms|%|fps)", doc))   # no measured number (as AC-R'4 / C1)


# ------------------------------------------------------------------ plan 15 lần sửa 7, user decision "File config mới"
REV7_CONFIG = os.path.join("configs", "level1_demo_classifier_rev7.json")


def _feed_windows(app, windows, t0=1000.0, dt=33.0):
    """Window results pushed through the app's timeline (as TestHudToneT4); returns the [classifier] HUD lines."""
    lines = []
    for i, (label, conf) in enumerate(windows):
        app.timeline.append(["frame", t0 + dt * i, True, True, _ok_result(label, conf)])
        app._drain_timeline()
        lines.append(app._hud_lines()[1][1])
    return lines


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestRev7DemoConfig(unittest.TestCase):
    """The demo command of lần sửa 7, `--config configs/level1_demo_classifier_rev7.json` (written by
    scripts/level1_rearm_check.py --write-rev7-config), runs rearm_mode classifier with the values of lần sửa 7 §2
    (window, thresholds of the tone marks, one-frame dropout debounce, word gap) without any flag. The D2 clip is a
    training clip: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import load_level1_config
        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_r7_", dir=TMP_PARENT)
        cls.out = os.path.join(cls.tmp, "r7.json")
        cls.proc = subprocess.run([PY, "level1_demo.py", "--source", CLIP, "--headless", "--config", REV7_CONFIG,
                                   "--out-json", cls.out], cwd=PROJECT_ROOT, capture_output=True, text=True, env=ENV,
                                  timeout=900)
        cls.report = None
        if cls.proc.returncode == 0:
            with open(cls.out, encoding="utf-8") as f:
                cls.report = json.load(f)
        cls.cfg = load_level1_config(os.path.join(PROJECT_ROOT, REV7_CONFIG))["values"]
        cls.base = load_level1_config(os.path.join(PROJECT_ROOT, DEMO_CONFIG))["values"]
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.away = {}
            for name, cfg in (("base", DEMO_CONFIG), ("rev7", REV7_CONFIG)):
                app = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", cfg),
                                        session_factory=_HandAwaySession)
                cls.away[name] = (app, app.run())
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _app(self, config=REV7_CONFIG):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless", "--config", config))
        finally:
            os.chdir(cwd)

    def test_r7_demo_command_runs_classifier_mode(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        r = self.report
        self.assertEqual(r["rearm_mode"], "classifier")
        self.assertEqual(r["config"]["path"], "configs/level1_demo_classifier_rev7.json")
        self.assertEqual(r["config"]["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, REV7_CONFIG)))
        self.assertNotIn("overrides", r["config"])                       # the values come from the file, no flag
        self.assertIs(r["auto_space"], False)   # lần sửa 12 S1: no automatic space by default (key written when off)
        self.assertEqual(r["checkpoint"]["sha256"], app_mod.sha256_file(os.path.join(PROJECT_ROOT, CKPT)))
        self.assertGreater(r["stages"]["window_classify"]["n"], 0)
        self.assertEqual(r["stages"]["classify"]["n"], 0)
        self.assertEqual(r["counts"]["label_emits"], len(r["labels"]))

    def test_r7_values_reach_the_app(self):
        app = self._app()
        self.assertEqual(app.rearm_mode, "classifier")
        self.assertEqual(app.window.window_ms, 700.0)
        self.assertEqual(app.decoder.thresholds("dấu huyền"), (0.78, 200.0))
        self.assertEqual(app.decoder.thresholds("a"), (self.base["cls_conf"], self.base["cls_stable_ms"]))
        self.assertEqual(app.decoder.dropout_tolerance_ms, 60.0)
        self.assertEqual(app.segmenter.p["word_gap_ms"], 2500.0)

    def test_r7_tone_mark_at_its_threshold(self):
        app = self._app()
        lines = _feed_windows(app, [("dấu huyền", 0.80)] * 8)
        self.assertEqual(lines[6], "[classifier] cửa sổ: dấu huyền 0.80 | giữ 198/200 (tone) | cuối: —")
        self.assertEqual(lines[7], "[classifier] cửa sổ: dấu huyền 0.80 | giữ 231/200 (tone) | cuối: dấu huyền")
        self.assertEqual([lab["prediction"] for lab in app.labels], ["dấu huyền"])
        letter = self._app()
        _feed_windows(letter, [("b", 0.80)] * 20)                         # a letter keeps cls_conf
        self.assertEqual(letter.labels, [])

    def test_r7_one_frame_dropout_kept(self):
        stream = [("b", 0.95)] * 5 + [("b", 0.50)] + [("b", 0.95)] * 5   # one window below cls_conf inside the run
        on, off = self._app(), self._app(DEMO_CONFIG)
        _feed_windows(on, stream)
        _feed_windows(off, stream)
        self.assertEqual([(lab["prediction"], lab["ts_ms"], lab["run_since_ms"]) for lab in on.labels],
                         [("b", 1330.0, 1000.0)])
        self.assertEqual(off.labels, [])                                  # lần sửa 5 config: the run restarts

    def test_r7_word_gap(self):
        app_b, rb = self.away["base"]
        app, r = self.away["rev7"]
        last_hand = app.segmenter._last_hand_ts                           # last frame with a hand, then hand away
        self.assertEqual(app_b.segmenter._last_hand_ts, last_hand)
        away = app.last_ts - last_hand                                    # hand away until the end of the clip
        self.assertGreaterEqual(away, self.base["word_gap_ms"])
        self.assertLess(away, self.cfg["word_gap_ms"])
        gaps_b = [e["t_ms"] for e in rb["events"] if e.get("event") == "word_gap"]
        self.assertEqual(len(gaps_b), 1)
        self.assertGreaterEqual(gaps_b[0] - last_hand, self.base["word_gap_ms"])
        self.assertEqual(rb["tokens"][-1], " ")                           # lần sửa 5 config: a space
        self.assertEqual(r["counts"]["word_gaps"], 0)                     # lần sửa 7 config: not yet a word gap
        self.assertNotIn(" ", r["tokens"])


class TestRev7DesktopDoc(unittest.TestCase):
    def test_r7_doc_demo_command(self):
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        for text in ("--config configs/level1_demo_classifier_rev7.json", "--write-rev7-config",
                     "--config configs/level1_demo_classifier.json"):
            self.assertIn(text, doc, text)


# ------------------------------------------------------------------ plan 15 lần sửa 8 (Tầng 1, demo app only)
class _SpyHandsM1:
    """Wraps mp.solutions.hands.Hands: records the keywords of every graph and counts its close() (graphs stay real)."""

    def __init__(self, real):
        self.real = real
        self.graphs = []   # [{"kwargs", "closes"}]

    def __call__(self, **kwargs):
        graph = self.real(**kwargs)
        record = {"kwargs": dict(kwargs), "closes": 0}
        orig_close = graph.close

        def close():
            record["closes"] += 1
            return orig_close()
        graph.close = close
        self.graphs.append(record)
        return graph


def _spy_hands():
    """(patcher, spy): mp.solutions.hands.Hands replaced by a recording wrapper of the real class while patched."""
    from unittest import mock
    import mediapipe as mp
    spy = _SpyHandsM1(mp.solutions.hands.Hands)
    return mock.patch.object(mp.solutions.hands, "Hands", side_effect=spy), spy


class TestHandSessionKwargsM1(unittest.TestCase):
    """AC-8b / AC-8c at the session level (plan 15 lần sửa 8 §2 M1): HandLandmarkSession() builds MediaPipe Hands with
    exactly LEVEL1_HANDS_KWARGS (min_detection_confidence 0.5, the keywords of training); a keyword of
    LEVEL1_HANDS_KWARGS given to the session replaces that value for its graphs only (reset() included); the module
    constant and the extractor description of /ws/hand-landmarks are unchanged."""

    def test_m1_default_is_level1_hands_kwargs(self):
        from src.inference import hand_live
        before = dict(hand_live.LEVEL1_HANDS_KWARGS)
        patcher, spy = _spy_hands()
        with patcher:
            s = hand_live.HandLandmarkSession()
            s.close()
        self.assertEqual(len(spy.graphs), 1)
        self.assertEqual(spy.graphs[0]["kwargs"], hand_live.LEVEL1_HANDS_KWARGS)
        self.assertEqual(spy.graphs[0]["kwargs"]["min_detection_confidence"], 0.5)
        self.assertEqual(s.kwargs, hand_live.LEVEL1_HANDS_KWARGS)
        self.assertIsNot(s.kwargs, hand_live.LEVEL1_HANDS_KWARGS)   # a copy: the session never edits the constant
        self.assertEqual(hand_live.LEVEL1_HANDS_KWARGS, before)

    def test_m1_override_min_detection_confidence(self):
        from src.inference import hand_live
        before = dict(hand_live.LEVEL1_HANDS_KWARGS)
        expected = {**before, "min_detection_confidence": 0.35}
        patcher, spy = _spy_hands()
        with patcher:
            s = hand_live.HandLandmarkSession(min_detection_confidence=0.35)
            self.assertEqual(s.kwargs, expected)
            s.reset()                                   # a new tracker keeps the session's keywords
            s.close()
        self.assertEqual([g["kwargs"] for g in spy.graphs], [expected, expected])
        self.assertEqual([g["closes"] for g in spy.graphs], [1, 1])
        self.assertEqual(hand_live.LEVEL1_HANDS_KWARGS, before)
        self.assertEqual(hand_live.LEVEL1_HANDS_KWARGS["min_detection_confidence"], 0.5)
        self.assertEqual(hand_live.extractor_info()["min_detection_confidence"], 0.5)

    def test_m1_none_means_default(self):
        from src.inference import hand_live
        patcher, spy = _spy_hands()
        with patcher:
            hand_live.HandLandmarkSession(min_detection_confidence=None).close()
        self.assertEqual(spy.graphs[0]["kwargs"], hand_live.LEVEL1_HANDS_KWARGS)

    def test_m1_unknown_keyword_rejected(self):
        from src.inference import hand_live
        patcher, spy = _spy_hands()
        with patcher:
            with self.assertRaises(TypeError):
                hand_live.HandLandmarkSession(min_detect_confidence=0.35)
        self.assertEqual(spy.graphs, [])            # no graph is built for a wrong keyword

    def test_m1_subclass_without_arguments(self):
        # the sessions of the tests (RecordingSession of AC-E, _HandAwaySession) call super().__init__() bare
        from src.inference import hand_live
        s = _HandAwaySession()
        try:
            self.assertEqual(s.kwargs, hand_live.LEVEL1_HANDS_KWARGS)
        finally:
            s.close()


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHandSessionClipM1(unittest.TestCase):
    """AC-8b on the D2 clip (a training clip: this checks the code path, not accuracy): a session given
    min_detection_confidence=0.5 explicitly returns, frame by frame, exactly what HandLandmarkSession() returns
    (landmarks bit-identical, same handedness and score); a session at 0.35 runs over the same frames."""

    @staticmethod
    def _run(session):
        reader = app_mod.VideoFileReader(os.path.join(PROJECT_ROOT, CLIP))
        out = []
        try:
            while True:
                frame = reader.read()
                if frame is None:
                    break
                out.append(session.process(frame))
        finally:
            session.close()
            reader.release()
        return out

    def test_m1_explicit_default_is_bit_identical(self):
        from src.inference.hand_live import HandLandmarkSession
        ref = self._run(HandLandmarkSession())
        same = self._run(HandLandmarkSession(min_detection_confidence=0.5))
        low = self._run(HandLandmarkSession(min_detection_confidence=0.35))
        self.assertGreater(len(ref), 0)
        self.assertEqual(len(same), len(ref))
        self.assertEqual(len(low), len(ref))
        self.assertGreater(sum(o[0] is not None for o in ref), 0)
        for (l_ref, h_ref, s_ref), (l_same, h_same, s_same) in zip(ref, same):
            self.assertEqual(l_ref is None, l_same is None)
            if l_ref is not None:
                self.assertTrue(np.array_equal(l_ref, l_same))
            self.assertEqual((h_ref, s_ref), (h_same, s_same))
        for lms, hand, score in low:
            if lms is not None:
                self.assertEqual((lms.shape, lms.dtype), ((21, 3), np.float32))
                self.assertIn(hand, ("Left", "Right"))
                self.assertIsInstance(score, float)


# ------------------------------------------------------------------ plan 15 lần sửa 8 M3 (CLI flags, HUD, camera, doc)
BEFORE_REV8_COMMIT = "1af1926"   # docs/plans/15-lan-sua-8.md committed; level1_demo.py as lần sửa 7 left it
# a hauuto clip whose every frame has a mean gray level above the low-light threshold (checked in the test); the D2
# clip is the opposite (every frame below it)
BRIGHT_CLIP = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "khoi", "a_khoi_A_001.mp4")
_MISSING_M3 = [p for p in (CLIP, CKPT, BRIGHT_CLIP) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]
SKIP_REASON_M3 = "missing (gitignored data / checkpoint): " + ", ".join(_MISSING_M3)
REV8_COMMAND = ("python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json "
                "--min-detection-conf 0.35 --auto-enhance")
HUD_MP_RE = r"^\[MP: conf=(\d\.\d\d) \| CLAHE: (on|off)\]$"


def _mean_gray(frame):
    import cv2
    return float(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))


class _FrameRecordingSession(HandLandmarkSession):
    """The real HandLandmarkSession (default keywords); keeps every frame object given to process()."""
    instances = []

    def __init__(self):
        self.frames_in = []
        super().__init__()
        _FrameRecordingSession.instances.append(self)

    def process(self, frame_bgr):
        self.frames_in.append(frame_bgr)
        return super().process(frame_bgr)


class _SpyReaderM3:
    """Wraps the app's reader; keeps every frame object it returns."""

    def __init__(self, reader):
        self._reader = reader
        self.frames_out = []

    def __getattr__(self, name):
        return getattr(self._reader, name)

    def read(self):
        frame = self._reader.read()
        if frame is not None:
            self.frames_out.append(frame)
        return frame


class _SpyAppM3(app_mod.Level1App):
    def _open_reader(self):
        self.spy_reader = _SpyReaderM3(super()._open_reader())
        return self.spy_reader


def _run_recorded(argv):
    """(app, report, stream session) of one app run with a fresh _FrameRecordingSession (index 0 = warm-up)."""
    _FrameRecordingSession.instances = []
    app = _SpyAppM3(args_for(*argv), argv=list(argv), session_factory=_FrameRecordingSession)
    report = app.run()
    sessions = list(_FrameRecordingSession.instances)
    assert len(sessions) == 2, len(sessions)
    return app, report, sessions[1]


class TestDetectionArgsM3(unittest.TestCase):
    """§2 M3: --min-detection-conf (default = min_detection_confidence of LEVEL1_HANDS_KWARGS, 0.5; a finite number in
    (0, 1]) and --auto-enhance (default off)."""

    def test_m3_defaults(self):
        from src.inference.hand_live import LEVEL1_HANDS_KWARGS
        a = args_for("--source", "0")
        self.assertEqual(a.min_detection_conf, 0.5)
        self.assertEqual(a.min_detection_conf, LEVEL1_HANDS_KWARGS["min_detection_confidence"])
        self.assertIs(a.auto_enhance, False)

    def test_m3_values(self):
        a = args_for("--source", "0", "--min-detection-conf", "0.35", "--auto-enhance")
        self.assertEqual(a.min_detection_conf, 0.35)
        self.assertIs(a.auto_enhance, True)
        self.assertEqual(args_for("--source", "0", "--min-detection-conf", "1").min_detection_conf, 1.0)

    def test_m3_rejects_values_outside_unit_interval(self):
        import contextlib
        import io
        for bad in ("0", "-0.1", "1.5", "nan", "inf", "abc"):
            with self.subTest(bad), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    args_for("--source", "0", "--min-detection-conf", bad)

    def test_m3_help_lists_flags(self):
        text = app_mod.build_parser().format_help()
        for opt in ("--min-detection-conf", "--auto-enhance"):
            self.assertIn(opt, text)


@unittest.skipUnless(not _MISSING_M3, SKIP_REASON_M3)
class TestMinDetectionConfM3(unittest.TestCase):
    """AC-8c / AC-8b in the app (MediaPipe Hands spied, graphs stay real): --min-detection-conf 0.35 builds the warm-up
    and the stream graphs with 0.35 and the JSON records it (hand_detection); without the flag, or with 0.5 given,
    every graph has exactly LEVEL1_HANDS_KWARGS and the run equals the app of lần sửa 7 (1af1926): same JSON keys,
    tokens, labels, segments, counts. The D2 clip is a training clip: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV8_COMMIT)
            base = ["--source", CLIP, "--headless"]
            cls.graphs, cls.reports = {}, {}
            for name, extra in (("low", ["--min-detection-conf", "0.35"]), ("default", []),
                                ("explicit", ["--min-detection-conf", "0.5"])):
                patcher, spy = _spy_hands()
                with patcher:
                    cls.reports[name] = app_mod.Level1App(args_for(*base, *extra), argv=base + extra).run()
                cls.graphs[name] = spy.graphs
            patcher, spy = _spy_hands()
            with patcher:
                cls.reports["ref"] = ref.Level1App(ref.build_parser().parse_args(base)).run()
            cls.graphs["ref"] = spy.graphs
        finally:
            os.chdir(cwd)

    def test_m3_low_conf_reaches_every_graph(self):
        from src.inference.hand_live import LEVEL1_HANDS_KWARGS
        expected = {**LEVEL1_HANDS_KWARGS, "min_detection_confidence": 0.35}
        graphs = self.graphs["low"]
        self.assertEqual(len(graphs), 2)                         # warm-up + stream
        self.assertEqual([g["kwargs"] for g in graphs], [expected, expected])
        self.assertEqual([g["closes"] for g in graphs], [1, 1])
        r = self.reports["low"]
        self.assertEqual(r["hand_detection"], {"min_detection_confidence": 0.35, "auto_enhance": False})
        self.assertIn("--min-detection-conf", r["generated_by"]["command"])
        self.assertEqual(r["config"]["sha256"],
                         app_mod.sha256_file(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")))
        self.assertGreater(r["counts"]["frames_processed"], 0)

    def test_m3_default_graphs_use_level1_hands_kwargs(self):
        from src.inference.hand_live import LEVEL1_HANDS_KWARGS
        for name in ("default", "explicit", "ref"):
            graphs = self.graphs[name]
            with self.subTest(name):
                self.assertEqual(len(graphs), 2)
                self.assertTrue(all(g["kwargs"] == LEVEL1_HANDS_KWARGS for g in graphs))

    def test_m3_default_run_equals_rev7_app(self):
        ref = self.reports["ref"]
        for name in ("default", "explicit"):
            r = self.reports[name]
            with self.subTest(name):
                self.assertNotIn("hand_detection", r)
                self.assertEqual(_key_tree(r), _key_tree(ref))
                for k in ("tokens", "text", "labels", "segments", "rearm_mode"):
                    self.assertEqual(r[k], ref[k], k)
                self.assertEqual(_without_rates(r["counts"]), _without_rates(ref["counts"]))
                self.assertEqual(tuple(r["stages"]), STAGES)


@unittest.skipUnless(not _MISSING_M3, SKIP_REASON_M3)
class TestAutoEnhanceM3(unittest.TestCase):
    """AC-8d in the app: with --auto-enhance a frame whose mean gray level is below the threshold reaches MediaPipe as
    enhance_low_light(frame) (a new array), any other frame as the very object read; the frame drawn and shown stays
    the camera frame; the JSON counts the enhanced frames and times the step (stage low_light_enhance). Without the
    flag nothing changes. The D2 clip is dark (every frame below the threshold), the khoi clip bright (every frame
    above). Training clips: this checks the code path, not accuracy."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.dark = _run_recorded(["--source", CLIP, "--headless", "--auto-enhance"])
            cls.bright = _run_recorded(["--source", BRIGHT_CLIP, "--headless", "--auto-enhance"])
            cls.plain = _run_recorded(["--source", CLIP, "--headless"])
        finally:
            os.chdir(cwd)

    def test_m3_clips_are_dark_and_bright(self):
        from src.inference.level1_core import LOW_LIGHT_THRESHOLD
        self.assertTrue(all(_mean_gray(f) < LOW_LIGHT_THRESHOLD for f in self.dark[0].spy_reader.frames_out))
        self.assertTrue(all(_mean_gray(f) >= LOW_LIGHT_THRESHOLD for f in self.bright[0].spy_reader.frames_out))

    def test_m3_dark_frames_enhanced_before_mediapipe(self):
        from src.inference.level1_core import CLAHE_CLIP_LIMIT, LOW_LIGHT_THRESHOLD, enhance_low_light
        app, report, session = self.dark
        read = app.spy_reader.frames_out
        self.assertGreater(len(read), 0)
        self.assertEqual(len(session.frames_in), len(read))
        for f_in, f_read in zip(session.frames_in, read):
            expected, enhanced = enhance_low_light(f_read)
            self.assertIs(enhanced, True)
            self.assertIsNot(f_in, f_read)
            self.assertTrue(np.array_equal(f_in, expected))
        n = report["counts"]["frames_processed"]
        self.assertEqual(report["hand_detection"], {
            "min_detection_confidence": 0.5, "auto_enhance": True, "frames_enhanced": n,
            "low_light_threshold": LOW_LIGHT_THRESHOLD, "clahe_clip_limit": CLAHE_CLIP_LIMIT,
            "clahe_tile_grid": [8, 8]})
        self.assertEqual(tuple(report["stages"]), STAGES + ("low_light_enhance",))
        self.assertEqual(report["stages"]["low_light_enhance"]["n"], n)
        self.assertEqual(report["stages"]["mediapipe"]["n"], n)

    def test_m3_bright_frames_untouched(self):
        app, report, session = self.bright
        read = app.spy_reader.frames_out
        self.assertGreater(len(read), 0)
        self.assertEqual(len(session.frames_in), len(read))
        self.assertTrue(all(a is b for a, b in zip(session.frames_in, read)))
        self.assertEqual(report["hand_detection"]["frames_enhanced"], 0)
        self.assertEqual(report["stages"]["low_light_enhance"]["n"], report["counts"]["frames_processed"])

    def test_m3_no_flag_frame_is_object_read(self):
        app, report, session = self.plain
        read = app.spy_reader.frames_out
        self.assertTrue(all(a is b for a, b in zip(session.frames_in, read)))
        self.assertNotIn("hand_detection", report)
        self.assertEqual(tuple(report["stages"]), STAGES)

    def test_m3_window_shows_camera_frame(self):
        # window mode, OpenCV window calls recorded (_WindowRecorder): landmarks are drawn on the frame read, never on
        # the enhanced copy given to MediaPipe
        from unittest import mock
        rec = _WindowRecorder()
        drawn = []
        real_draw = app_mod.draw_landmarks

        def draw(frame, landmarks):
            drawn.append(frame)
            return real_draw(frame, landmarks)
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            with mock.patch.multiple(app_mod.cv2, imshow=rec.imshow, waitKey=rec.waitKey,
                                     getWindowProperty=rec.getWindowProperty, namedWindow=rec.namedWindow,
                                     destroyAllWindows=rec.destroyAllWindows), \
                    mock.patch.object(app_mod, "draw_landmarks", side_effect=draw):
                app, report, session = _run_recorded(["--source", CLIP, "--auto-enhance"])
        finally:
            os.chdir(cwd)
        read = app.spy_reader.frames_out
        self.assertEqual(report["source"]["mode"], "gui")
        self.assertGreater(len(read), 0)
        self.assertEqual(len(drawn), len(read))
        self.assertTrue(all(a is b for a, b in zip(drawn, read)))
        self.assertTrue(all(a is not b for a, b in zip(session.frames_in, read)))
        self.assertEqual(len(rec.shown), len(read))


@unittest.skipUnless(not _MISSING_M3, SKIP_REASON_M3)
class TestRev8CommandM3(unittest.TestCase):
    """The demo command of the plan (§2 M3) on the D2 clip in place of the webcam, through main(): exit 0, classifier
    mode of the lần sửa 7 config, MediaPipe at 0.35, every (dark) frame enhanced. Training clip: code path only."""

    def test_m3_plan_command_headless(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_m3_", dir=TMP_PARENT)
        try:
            out = os.path.join(tmp, "rev8.json")
            argv = REV8_COMMAND.split()[2:]
            self.assertEqual(argv[:2], ["--source", "0"])
            argv = ["--source", CLIP, "--headless"] + [a for a in argv[2:] if a != "--display-mirror"]
            proc = subprocess.run([PY, "level1_demo.py", *argv, "--out-json", out], cwd=PROJECT_ROOT,
                                  capture_output=True, text=True, env=ENV, timeout=900)
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            with open(out, encoding="utf-8") as f:
                r = json.load(f)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(r["rearm_mode"], "classifier")
        self.assertEqual(r["config"]["path"], "configs/level1_demo_classifier_rev7.json")
        hd = r["hand_detection"]
        self.assertEqual((hd["min_detection_confidence"], hd["auto_enhance"]), (0.35, True))
        self.assertEqual(hd["frames_enhanced"], r["counts"]["frames_processed"])
        self.assertGreater(r["counts"]["window_results"], 0)


@unittest.skipUnless(not _MISSING_M3, SKIP_REASON_M3)
class TestDetectionHudM3(unittest.TestCase):
    """HUD line "[MP: conf=<x.xx> | CLAHE: on|off]" right under the state / decoder line, only when MediaPipe or the
    frame differ from the default (--min-detection-conf other than 0.5 or --auto-enhance); without them the HUD lines
    are those of the app of lần sửa 7."""

    @staticmethod
    def _small(module, *extra):
        argv = ["--source", CLIP, "--headless", *extra]
        app = module.Level1App(module.build_parser().parse_args(argv))
        return app._hud_lines()[1]

    def test_m3_hud_line_only_when_not_default(self):
        import re
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV8_COMMIT)
            for cfg in ("configs/level1_realtime.json", "configs/level1_demo_classifier_rev7.json"):
                with self.subTest(cfg):
                    plain = self._small(app_mod, "--config", cfg)
                    self.assertEqual(plain, self._small(ref, "--config", cfg))
                    self.assertEqual(self._small(app_mod, "--config", cfg, "--min-detection-conf", "0.5"), plain)
                    self.assertFalse(any(re.match(HUD_MP_RE, s) for s in plain))
                    for extra, line in ((("--min-detection-conf", "0.35"), "[MP: conf=0.35 | CLAHE: off]"),
                                        (("--auto-enhance",), "[MP: conf=0.50 | CLAHE: on]"),
                                        (("--min-detection-conf", "0.35", "--auto-enhance"),
                                         "[MP: conf=0.35 | CLAHE: on]")):
                        small = self._small(app_mod, "--config", cfg, *extra)
                        self.assertRegex(line, HUD_MP_RE)
                        self.assertEqual(small, plain[:2] + [line] + plain[2:], extra)
        finally:
            os.chdir(cwd)


class TestCameraDshowM3(unittest.TestCase):
    """AC-8e (the part a test can check without the user's webcam): every committed config keeps camera_api "dshow",
    and the webcam reader opens the camera with cv2.CAP_DSHOW and the config's size and buffer (OpenCV capture
    replaced by a recorder defined here; no camera is opened)."""

    CONFIGS = ("configs/level1_realtime.json", "configs/level1_demo_classifier.json",
               "configs/level1_demo_classifier_rev7.json")

    def test_m3_configs_keep_dshow(self):
        for cfg in self.CONFIGS:
            with open(os.path.join(PROJECT_ROOT, cfg), encoding="utf-8") as f:
                with self.subTest(cfg):
                    self.assertEqual(json.load(f)["camera_api"]["value"], "dshow")

    def test_m3_camera_reader_opens_dshow(self):
        import cv2
        from unittest import mock
        from src.inference.level1_core import load_level1_config
        values = load_level1_config(os.path.join(PROJECT_ROOT, "configs", "level1_demo_classifier_rev7.json"))["values"]
        calls, sets = [], []

        class _Capture:
            def __init__(self, index, api):
                calls.append((index, api))
                self.props = {}

            def isOpened(self):
                return True

            def set(self, prop, value):
                sets.append((prop, value))
                self.props[prop] = value
                return True

            def get(self, prop):
                return float(self.props.get(prop, 0))

            def getBackendName(self):
                return "DSHOW"

            def release(self):
                return None

        with mock.patch.object(app_mod.cv2, "VideoCapture", _Capture):
            reader = app_mod.CameraReader(0, values)
        self.assertEqual(calls, [(0, cv2.CAP_DSHOW)])
        self.assertEqual(sets, [(cv2.CAP_PROP_FRAME_WIDTH, values["camera_width"]),
                                (cv2.CAP_PROP_FRAME_HEIGHT, values["camera_height"]),
                                (cv2.CAP_PROP_BUFFERSIZE, values["camera_buffersize"])])
        self.assertEqual(reader.props["camera_api"], "dshow")


class TestDesktopDocM3(unittest.TestCase):
    def test_m3_doc_lists_command_flags_and_json(self):
        import re
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        for text in (REV8_COMMAND, "--min-detection-conf", "--auto-enhance", "[MP: conf=0.35 | CLAHE: on]",
                     "hand_detection", "frames_enhanced", "low_light_enhance", "dshow"):
            self.assertIn(text, doc, text)
        self.assertIsNone(re.search(r"\d+(\.\d+)?\s*(ms|%|fps)", doc))   # no measured number (as AC-R'4 / C1)


# ------------------------------------------------------------------ plan 15 lần sửa 9 S2 (open palm gesture = Space)
BEFORE_REV9_COMMIT = "03d17b8"   # docs/plans/15-lan-sua-9.md committed; level1_demo.py as lần sửa 8 left it
# a hauuto training clip whose signer raises an OPEN PALM (5 fingers spread, thumb out) before forming the letter b
# (frames looked at by eye; is_open_palm_space is True on the first hand frames and False on the held b)
PALM_CLIP = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "khoi", "b_khoi_A_001.mp4")
_MISSING_S2 = [p for p in (CLIP, CKPT, PALM_CLIP) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]
SKIP_REASON_S2 = "missing (gitignored data / checkpoint): " + ", ".join(_MISSING_S2)
GESTURE_LINE_RE = r"^\[Cử chỉ: Dấu cách (\d+)/(\d+)\]$"
GESTURE_FLASH_LINE = "[Ký hiệu: Dấu cách (Space)]"


def _palm_steps(tracker, start, stop, step, is_space=True, has_hand=True):
    """tracker.update at start, start + step, ... < stop; returns the timestamps at which it returned True."""
    out = []
    t = start
    while t < stop:
        if tracker.update(t, is_space, has_hand=has_hand):
            out.append(t)
        t += step
    return out


class TestSpaceGestureTrackerS2(unittest.TestCase):
    """§2 S2: SpaceGestureTracker(hold_ms) -> update(ts_ms, is_space[, has_hand]) is True exactly once when the open
    palm has been held hold_ms (armed); then disarmed: no second space while the palm is held; re-armed by another
    hand shape held more than rearm_ms (150) or by a frame without hand. Timestamps / flags are driven here."""

    def test_s2_hold_200_no_space(self):
        tr = app_mod.SpaceGestureTracker()
        self.assertEqual(tr.hold_ms, 250.0)
        self.assertEqual(_palm_steps(tr, 0.0, 201.0, 20.0), [])                      # 0 .. 200 ms

    def test_s2_hold_260_one_space(self):
        tr = app_mod.SpaceGestureTracker()
        self.assertEqual(_palm_steps(tr, 0.0, 261.0, 20.0), [260.0])                 # 260 - 0 >= 250
        tr2 = app_mod.SpaceGestureTracker()
        self.assertEqual(_palm_steps(tr2, 0.0, 261.0, 10.0), [250.0])                # exactly 250 counts
        self.assertEqual(tr.n_emits, 1)

    def test_s2_hold_on_to_1000_no_second_space(self):
        tr = app_mod.SpaceGestureTracker()
        self.assertEqual(_palm_steps(tr, 0.0, 1001.0, 20.0), [260.0])
        self.assertFalse(tr.armed)

    def test_s2_other_pose_then_palm_again(self):
        tr = app_mod.SpaceGestureTracker()
        self.assertEqual(_palm_steps(tr, 0.0, 1001.0, 20.0), [260.0])
        self.assertEqual(_palm_steps(tr, 1020.0, 1221.0, 20.0, is_space=False), [])  # other shape for 200 ms
        self.assertTrue(tr.armed)
        self.assertEqual(_palm_steps(tr, 1240.0, 1601.0, 20.0), [1500.0])            # second space
        self.assertEqual(tr.n_emits, 2)

    def test_s2_short_other_pose_does_not_rearm(self):
        tr = app_mod.SpaceGestureTracker()
        _palm_steps(tr, 0.0, 301.0, 20.0)
        self.assertEqual(_palm_steps(tr, 320.0, 461.0, 20.0, is_space=False), [])    # 140 ms: not > 150
        self.assertFalse(tr.armed)
        self.assertEqual(_palm_steps(tr, 480.0, 1201.0, 20.0), [])                   # flicker: no second space
        _palm_steps(tr, 1220.0, 1381.0, 20.0, is_space=False)                        # 160 ms: > 150
        self.assertTrue(tr.armed)

    def test_s2_hand_lost_rearms(self):
        tr = app_mod.SpaceGestureTracker()
        _palm_steps(tr, 0.0, 301.0, 20.0)
        self.assertFalse(tr.armed)
        self.assertFalse(tr.update(320.0, False, has_hand=False))                    # one frame without hand
        self.assertTrue(tr.armed)
        self.assertEqual(_palm_steps(tr, 340.0, 701.0, 20.0), [600.0])

    def test_s2_interrupted_hold_restarts(self):
        tr = app_mod.SpaceGestureTracker()
        self.assertEqual(_palm_steps(tr, 0.0, 201.0, 20.0), [])
        self.assertFalse(tr.update(220.0, False))                                   # one other frame
        self.assertEqual(_palm_steps(tr, 240.0, 481.0, 20.0), [])                    # 240 .. 480: 240 < 250
        self.assertEqual(_palm_steps(tr, 500.0, 521.0, 20.0), [500.0])

    def test_s2_held_ms_and_hold_parameter(self):
        tr = app_mod.SpaceGestureTracker(hold_ms=400.0)
        self.assertEqual(tr.held_ms, 0.0)
        self.assertEqual(_palm_steps(tr, 0.0, 381.0, 20.0), [])
        self.assertEqual(tr.held_ms, 380.0)
        self.assertEqual(_palm_steps(tr, 400.0, 401.0, 20.0), [400.0])
        self.assertEqual(tr.held_ms, 0.0)                                            # disarmed: no hold shown
        for bad in (0.0, -5.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                app_mod.SpaceGestureTracker(hold_ms=bad)
        with self.assertRaises(ValueError):
            tr.update(float("nan"), True)

    def test_s2_reset(self):
        tr = app_mod.SpaceGestureTracker()
        _palm_steps(tr, 0.0, 301.0, 20.0)
        tr.reset()
        self.assertTrue(tr.armed)
        self.assertEqual(tr.held_ms, 0.0)
        self.assertEqual(tr.n_emits, 1)                                              # emissions are kept


class _LandmarkRecordingSession(HandLandmarkSession):
    """The real HandLandmarkSession (default keywords); keeps (landmarks, width, height) of every frame processed."""
    instances = []

    def __init__(self):
        self.seen = []
        super().__init__()
        _LandmarkRecordingSession.instances.append(self)

    def process(self, frame_bgr):
        out = super().process(frame_bgr)
        h, w = frame_bgr.shape[:2]
        self.seen.append((out[0], w, h))
        return out


def _expected_gesture_spaces(flags, ts, hold_ms=250.0):
    """Timestamps of the spaces of the §2 S2 rule, written out here for an open palm that is held only once per clip:
    first frame of a run of open-palm frames whose distance to the run start is >= hold_ms (one per run)."""
    out, start = [], None
    for f, t in zip(flags, ts):
        if not f:
            start = None
            continue
        if start is None:
            start = t
        if start != "done" and t - start >= hold_ms:
            out.append(t)
            start = "done"
    return out


@unittest.skipUnless(not _MISSING_S2, SKIP_REASON_S2)
class TestGestureSpaceAppS2(unittest.TestCase):
    """§2 S2 in Level1App on real clips (training clips: this checks the code path, not accuracy). PALM_CLIP starts
    with an open palm held longer than 250 ms, then the letter b: one gesture space, at the frame the rule gives, and
    the held b gives none. In rearm_mode classifier the open-palm frames reach the window as frames without hand (no
    window classified at them). CLIP has no open-palm frame: the report is that of the app at 03d17b8."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import is_open_palm_space
        from src.inference.level1_segmenter import aspect_points
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.ref = app_module_at(BEFORE_REV9_COMMIT)
            cls.runs = {}
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", REV7_CONFIG])):
                argv = ["--source", PALM_CLIP, "--headless", *extra, "--trace-windows"]
                _LandmarkRecordingSession.instances = []
                app = app_mod.Level1App(args_for(*argv), session_factory=_LandmarkRecordingSession)
                report = app.run()
                seen = _LandmarkRecordingSession.instances[1].seen                   # [0] = warm-up graph
                seeded = app_mod.Level1App(args_for(*argv))
                seeded.speller.key("tone_1", t_ms=0.0)                               # a token typed before the clip
                cls.runs[mode] = {"app": app, "report": report, "seen": seen, "seeded": seeded.run()}
                a = ["--source", CLIP, "--headless", *extra]                            # no open palm in CLIP
                cls.runs["clip_" + mode] = {"new": app_mod.Level1App(args_for(*a)).run(),
                                            "ref": cls.ref.Level1App(cls.ref.build_parser().parse_args(a)).run()}
            for mode in ("motion_pose", "classifier"):
                r = cls.runs[mode]
                fps = r["report"]["source"]["fps_file"]
                r["ts"] = [i * 1000.0 / fps for i in range(len(r["seen"]))]
                r["flags"] = [lm is not None and is_open_palm_space(aspect_points(lm, w, h)) for lm, w, h in r["seen"]]
        finally:
            os.chdir(cwd)

    def test_s2_clip_has_open_palm_then_letter(self):
        for mode in ("motion_pose", "classifier"):
            flags = self.runs[mode]["flags"]
            self.assertGreaterEqual(sum(flags), 8)                                    # > 250 ms at the clip rate
            self.assertFalse(any(flags[len(flags) // 2:]), mode)                      # the held b: never

    def test_s2_one_gesture_space_at_the_rule_frame(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[mode]
                events = [e for e in r["report"]["events"] if e.get("event") == "gesture_space"]
                expected = _expected_gesture_spaces(r["flags"], r["ts"])
                self.assertEqual(len(expected), 1)
                self.assertEqual([e["t_ms"] for e in events], expected)
                self.assertIs(events[0]["added"], False)                              # no token before: nothing to cut
                self.assertEqual(r["app"].space_tracker.n_emits, 1)

    def test_s2_space_added_after_a_token(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[mode]
                s = r["seeded"]
                t_gesture = _expected_gesture_spaces(r["flags"], r["ts"])[0]
                self.assertEqual(s["tokens"][:2], ["dấu sắc", " "])
                spaces = [e for e in s["events"] if e.get("event") == "token" and e.get("token") == " "]
                self.assertEqual(spaces[0]["t_ms"], t_gesture)
                self.assertEqual((spaces[0]["source"], spaces[0]["key"]), ("key", "space"))
                g = [e for e in s["events"] if e.get("event") == "gesture_space"]
                self.assertEqual([(e["t_ms"], e["added"]) for e in g], [(t_gesture, True)])

    def test_s2_classifier_no_window_at_open_palm_frames(self):
        r = self.runs["classifier"]
        palm_ts = {t for f, t in zip(r["flags"], r["ts"]) if f}
        entries = r["report"]["window_trace"]["entries"]
        self.assertGreater(len(entries), 0)
        self.assertFalse(palm_ts & {e["ts_ms"] for e in entries})
        hand_frames = sum(1 for lm, _w, _h in r["seen"] if lm is not None)
        self.assertLessEqual(r["report"]["counts"]["window_jobs"], hand_frames - len(palm_ts))

    def test_s2_motion_pose_segmenter_unchanged(self):
        """motion_pose: the segmenter still gets every hand frame (the plan changes only the window path)."""
        new, ref = self.runs["motion_pose"]["report"], None
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = self.ref.Level1App(self.ref.build_parser().parse_args(["--source", PALM_CLIP, "--headless"])).run()
        finally:
            os.chdir(cwd)
        self.assertEqual(new["segments"], ref["segments"])
        self.assertEqual(new["tokens"], ref["tokens"])                               # the space found no token

    def test_s2_no_open_palm_same_report_as_before(self):
        for mode in ("clip_motion_pose", "clip_classifier"):
            with self.subTest(mode=mode):
                new, ref = self.runs[mode]["new"], self.runs[mode]["ref"]
                self.assertEqual(list(new), list(ref))
                self.assertEqual(_key_tree(new), _key_tree(ref))
                for k in ("tokens", "text", "labels", "segments", "events"):
                    self.assertEqual(new[k], ref[k], (mode, k))
                self.assertEqual(_without_rates(new["counts"]), _without_rates(ref["counts"]), mode)
                self.assertFalse([e for e in new["events"] if e.get("event") == "gesture_space"])


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestGestureSpaceHudS2(unittest.TestCase):
    """HUD of §2 S2: while the open palm is held (armed) the line "[Cử chỉ: Dấu cách <held ms>/<hold ms>]" comes right
    after the state / decoder line; once the space is emitted "[Ký hiệu: Dấu cách (Space)]" is shown for
    GESTURE_SPACE_FLASH ms of stream time; otherwise no gesture line (HUD as before). Gesture steps driven here."""

    def _app(self, *extra):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless", *extra))
        finally:
            os.chdir(cwd)

    def test_s2_hud_progress_then_flash(self):
        import re
        for extra in ([], ["--config", REV7_CONFIG]):
            with self.subTest(extra=extra):
                app = self._app(*extra)
                app.speller.key("tone_1", t_ms=0.0)
                plain = app._hud_lines()[1]
                for t in (100.0, 160.0, 220.0):
                    app._gesture_step(t, True, True)
                small = app._hud_lines()[1]
                m = re.match(GESTURE_LINE_RE, small[2])
                self.assertIsNotNone(m, small)
                self.assertEqual((int(m.group(1)), int(m.group(2))), (120, 250))
                self.assertEqual(small[:2] + small[3:], plain)
                app._gesture_step(350.0, True, True)                                 # 250 ms held: space
                self.assertEqual(app.speller.tokens, ["dấu sắc", " "])
                small = app._hud_lines()[1]
                self.assertEqual(small[2], GESTURE_FLASH_LINE)
                end = 350.0 + app_mod.GESTURE_SPACE_FLASH
                app._gesture_step(end - 1.0, True, True)                             # still held, disarmed
                self.assertEqual(app._hud_lines()[1][2], GESTURE_FLASH_LINE)
                app._gesture_step(end, True, True)
                after = app._hud_lines()[1]
                self.assertFalse(any(GESTURE_FLASH_LINE == s or re.match(GESTURE_LINE_RE, s) for s in after))

    def test_s2_events_and_gesture_space_through_timeline(self):
        """classifier: the space waits behind a frame whose window result is not in yet (timestamp order)."""
        app = self._app("--config", REV7_CONFIG)
        app.speller.key("tone_1", t_ms=0.0)
        app.timeline.append(["frame", 50.0, True, False, None])                       # result not in yet
        for t in (100.0, 200.0, 350.0):
            app._gesture_step(t, True, True)
        self.assertEqual(app.speller.tokens, ["dấu sắc"])
        self.assertEqual([e[0] for e in app.timeline], ["frame", "space"])
        app.timeline[0][3] = True                                                     # the result comes in
        app._drain_timeline()
        self.assertEqual(app.speller.tokens, ["dấu sắc", " "])
        self.assertEqual([e for e in app.events if e["event"] == "gesture_space"],
                         [{"event": "gesture_space", "t_ms": 350.0, "added": True}])

    def test_s2_pause_resets_tracker(self):
        app = self._app()
        for t in (0.0, 100.0, 200.0):
            app._gesture_step(t, True, True)
        app._key(app_mod.KEY_PAUSE)
        self.assertEqual(app.space_tracker.held_ms, 0.0)
        app._key(app_mod.KEY_PAUSE)
        app._gesture_step(240.0, True, True)                                          # hold starts again
        self.assertEqual(app.speller.tokens, [])
        self.assertEqual(app.space_tracker.n_emits, 0)


# ------------------------------------------------------------------ plan 15 lần sửa 9 S3 (CLI flags, JSON, doc)
REV9_COMMAND = ("python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json "
                "--min-detection-conf 0.35 --auto-enhance --no-auto-space")
GESTURE_JSON_KEYS = ("enabled", "hold_ms", "rearm_ms", "flash_ms", "palm_frames", "emits", "spaces_added")


class TestGestureSpaceArgsS3(unittest.TestCase):
    """§2 S3: --gesture-space / --no-gesture-space (default on) and --space-hold-ms (default 250, a finite number > 0)."""

    def test_s3_help_and_defaults(self):
        text = app_mod.build_parser().format_help()
        for flag in ("--gesture-space", "--no-gesture-space", "--space-hold-ms"):
            self.assertIn(flag, text)
        a = args_for("--source", CLIP)
        self.assertIs(a.gesture_space, True)
        self.assertEqual(a.space_hold_ms, 250.0)
        self.assertEqual(a.space_hold_ms, app_mod.GESTURE_SPACE_HOLD)
        self.assertIs(args_for("--source", CLIP, "--no-gesture-space").gesture_space, False)
        self.assertIs(args_for("--source", CLIP, "--no-gesture-space", "--gesture-space").gesture_space, True)
        self.assertEqual(args_for("--source", CLIP, "--space-hold-ms", "400").space_hold_ms, 400.0)

    def test_s3_bad_hold_rejected(self):
        import contextlib
        import io
        for bad in ("0", "-5", "abc", "nan", "inf"):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    args_for("--source", CLIP, "--space-hold-ms", bad)


@unittest.skipUnless(not _MISSING_S2, SKIP_REASON_S2)
class TestGestureSpaceFlagsS3(unittest.TestCase):
    """AC-9c / AC-9d with the flags on real clips (training clips: code path, not accuracy). --no-gesture-space: the
    report (keys, tokens, labels, segments, events, counts) and the HUD lines are those of the app at 03d17b8, also on
    the clip with an open palm. With the gesture on, the JSON has `gesture_space` (§2 S3) when an open-palm frame was
    seen or --space-hold-ms is not the default; otherwise (no open palm, default hold) the report keeps its keys."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import is_open_palm_space
        from src.inference.level1_segmenter import aspect_points
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.ref = app_module_at(BEFORE_REV9_COMMIT)
            cls.runs = {}
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", REV7_CONFIG])):
                base = ["--source", PALM_CLIP, "--headless", *extra]
                ref_app = cls.ref.Level1App(cls.ref.build_parser().parse_args(base))
                off_app = app_mod.Level1App(args_for(*base, "--no-gesture-space"))
                cls.runs[mode] = {"ref": ref_app.run(), "off": off_app.run(), "ref_app": ref_app, "off_app": off_app}
                for hold in ("400", "500"):
                    cls.runs[mode][hold] = app_mod.Level1App(args_for(*base, "--space-hold-ms", hold)).run()
                _LandmarkRecordingSession.instances = []
                cls.runs[mode]["on"] = app_mod.Level1App(args_for(*base),
                                                         session_factory=_LandmarkRecordingSession).run()
                seen = _LandmarkRecordingSession.instances[1].seen
                fps = cls.runs[mode]["on"]["source"]["fps_file"]
                cls.runs[mode]["ts"] = [i * 1000.0 / fps for i in range(len(seen))]
                cls.runs[mode]["flags"] = [lm is not None and is_open_palm_space(aspect_points(lm, w, h))
                                           for lm, w, h in seen]
            plain = ["--source", CLIP, "--headless"]
            cls.clip_hold = app_mod.Level1App(args_for(*plain, "--space-hold-ms", "400")).run()
            cls.clip_ref = cls.ref.Level1App(cls.ref.build_parser().parse_args(plain)).run()
        finally:
            os.chdir(cwd)

    def _same_as_ref(self, new, ref, label):
        self.assertEqual(list(new), list(ref), label)
        self.assertEqual(_key_tree(new), _key_tree(ref), label)
        for k in ("tokens", "text", "labels", "segments", "events", "warnings"):
            self.assertEqual(new[k], ref[k], (label, k))
        self.assertEqual(_without_rates(new["counts"]), _without_rates(ref["counts"]), label)

    def test_9d_no_gesture_space_same_as_before(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[mode]
                self._same_as_ref(r["off"], r["ref"], mode)
                self.assertNotIn("gesture_space", r["off"])
                self.assertEqual(r["off_app"]._hud_lines()[1], r["ref_app"]._hud_lines()[1])
                self.assertEqual(r["off_app"].space_tracker.n_emits, 0)

    def test_9c_json_block_with_gesture_on(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[mode]
                on = r["on"]
                self.assertEqual(list(on), list(r["ref"]) + ["gesture_space"])
                g = on["gesture_space"]
                self.assertEqual(tuple(g), GESTURE_JSON_KEYS)
                self.assertEqual((g["enabled"], g["hold_ms"], g["rearm_ms"], g["flash_ms"]),
                                 (True, 250.0, 150.0, app_mod.GESTURE_SPACE_FLASH))
                self.assertEqual(g["palm_frames"], sum(r["flags"]))
                self.assertEqual((g["emits"], g["spaces_added"]), (1, 0))             # no token before the palm
                events = [e for e in on["events"] if e.get("event") == "gesture_space"]
                self.assertEqual([e["t_ms"] for e in events], _expected_gesture_spaces(r["flags"], r["ts"]))

    def test_9c_space_hold_ms(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[mode]
                for hold in ("400", "500"):
                    g = r[hold]["gesture_space"]
                    expected = _expected_gesture_spaces(r["flags"], r["ts"], hold_ms=float(hold))
                    events = [e["t_ms"] for e in r[hold]["events"] if e.get("event") == "gesture_space"]
                    self.assertEqual(events, expected, hold)
                    self.assertEqual((g["hold_ms"], g["emits"]), (float(hold), len(expected)))
                self.assertEqual(len(_expected_gesture_spaces(r["flags"], r["ts"], hold_ms=400.0)), 1)
                self.assertEqual(_expected_gesture_spaces(r["flags"], r["ts"], hold_ms=500.0), [])  # palm < 500

    def test_9c_hold_recorded_without_open_palm(self):
        r, ref = self.clip_hold, self.clip_ref
        self.assertEqual(r["gesture_space"], {"enabled": True, "hold_ms": 400.0, "rearm_ms": 150.0,
                                              "flash_ms": app_mod.GESTURE_SPACE_FLASH, "palm_frames": 0, "emits": 0,
                                              "spaces_added": 0})
        for k in ("tokens", "labels", "segments", "events"):
            self.assertEqual(r[k], ref[k], k)


@unittest.skipUnless(not _MISSING_S2, SKIP_REASON_S2)
class TestRev9CommandS3(unittest.TestCase):
    """The suggested command of §2 S3 (gesture space + --no-auto-space) through main() on PALM_CLIP in place of the
    webcam, headless: exit 0, classifier mode, no automatic space, the JSON has gesture_space. Training clip: code path."""

    def test_s3_plan_command_headless(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_s3_", dir=TMP_PARENT)
        try:
            out = os.path.join(tmp, "rev9.json")
            argv = REV9_COMMAND.split()[2:]
            self.assertEqual(argv[:2], ["--source", "0"])
            argv = ["--source", PALM_CLIP, "--headless"] + [a for a in argv[2:] if a != "--display-mirror"]
            argv.append("--gesture-space")   # lần sửa 12 S1: the gesture is off by default since
            proc = subprocess.run([PY, "level1_demo.py", *argv, "--out-json", out], cwd=PROJECT_ROOT,
                                  capture_output=True, text=True, env=ENV, timeout=900)
            self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
            with open(out, encoding="utf-8") as f:
                r = json.load(f)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(r["rearm_mode"], "classifier")
        self.assertIs(r["auto_space"], False)
        self.assertEqual((r["gesture_space"]["enabled"], r["gesture_space"]["emits"]), (True, 1))
        self.assertGreater(r["gesture_space"]["palm_frames"], 0)


class TestDesktopDocS3(unittest.TestCase):
    def test_s3_doc_gesture_and_command(self):
        import re
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        for text in (REV9_COMMAND, "--gesture-space", "--no-gesture-space", "--space-hold-ms", "Xòe 5 ngón",
                     "[Cử chỉ: Dấu cách", GESTURE_FLASH_LINE, "gesture_space", "palm_frames", "spaces_added"):
            self.assertIn(text, doc, text)
        self.assertIsNone(re.search(r"\d+(\.\d+)?\s*(ms|%|fps)", doc))   # no measured number (as AC-R'4 / C1)



# ------------------------------------------------------------------ plan 15 lần sửa 10 P2 (landmark smoothing in the app)
BEFORE_REV10_COMMIT = "8e6d6fb"  # docs/plans/15-lan-sua-10.md committed; level1_demo.py as lần sửa 9 left it
SMOOTH_JSON_KEYS = ("enabled", "alpha_static", "alpha_dynamic", "speed_threshold", "frames_static", "frames_dynamic")


def _spy_inputs(app):
    """Records (ts, landmarks copy | None, handedness) of every segmenter.push and window.push call of `app`."""
    rec = {"segmenter": [], "window": []}

    def wrap(obj, name):
        orig = obj.push

        def push(ts_ms, landmarks, handedness, w, h):
            rec[name].append((ts_ms, None if landmarks is None else np.array(landmarks, copy=True), handedness))
            return orig(ts_ms, landmarks, handedness, w, h)
        obj.push = push
    wrap(app.segmenter, "segmenter")
    if app.window is not None:
        wrap(app.window, "window")
    return rec


def _run_spied(argv):
    """(report, app, raw [(landmarks, w, h, handedness)] of the stream session, spied inputs) of one headless run."""
    _LandmarkHandRecordingSession.instances = []
    app = app_mod.Level1App(args_for(*argv), session_factory=_LandmarkHandRecordingSession)
    rec = _spy_inputs(app)
    report = app.run()
    return report, app, _LandmarkHandRecordingSession.instances[1].seen, rec        # [0] = warm-up graph


class _LandmarkHandRecordingSession(HandLandmarkSession):
    """The real HandLandmarkSession (default keywords); keeps (landmarks, width, height, handedness) of every frame."""
    instances = []

    def __init__(self):
        self.seen = []
        super().__init__()
        _LandmarkHandRecordingSession.instances.append(self)

    def process(self, frame_bgr):
        out = super().process(frame_bgr)
        h, w = frame_bgr.shape[:2]
        self.seen.append((out[0], w, h, out[1]))
        return out


class TestSmoothLandmarksArgsP2(unittest.TestCase):
    """§2 P2: --smooth-landmarks / --no-smooth-landmarks (BooleanOptionalAction). Default OFF: the plan writes
    default=True, but AC-10d and §1 require the run without the new flags to be the app of before (old tests compare the
    default run with the app at earlier commits segment by segment); see 15-progress lần sửa 10."""

    def test_p2_flags_and_default(self):
        text = app_mod.build_parser().format_help()
        for flag in ("--smooth-landmarks", "--no-smooth-landmarks"):
            self.assertIn(flag, text)
        self.assertIs(args_for("--source", CLIP).smooth_landmarks, False)
        self.assertIs(args_for("--source", CLIP, "--smooth-landmarks").smooth_landmarks, True)
        self.assertIs(args_for("--source", CLIP, "--smooth-landmarks", "--no-smooth-landmarks").smooth_landmarks, False)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestSmoothLandmarksAppP2(unittest.TestCase):
    """§2 P2 / AC-10c / AC-10d in Level1App on the D2 clip (training clip: code path, not accuracy). With
    --smooth-landmarks the segmenter (and in rearm_mode classifier the window) gets LandmarkSmoother.filter of the
    session's landmarks, recomputed here from the recorded raw landmarks; the frame-to-frame z jitter is lower than raw;
    the JSON has landmark_smoothing. Without the flag the inputs are the raw landmarks and the report is that of the app
    at 8e6d6fb."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV10_COMMIT)
            cls.runs = {}
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", REV7_CONFIG])):
                base = ["--source", CLIP, "--headless", *extra]
                on = _run_spied(base + ["--smooth-landmarks"])
                off = _run_spied(base)
                cls.runs[mode] = {"on": on, "off": off,
                                  "ref": ref.Level1App(ref.build_parser().parse_args(base)).run()}
        finally:
            os.chdir(cwd)

    @staticmethod
    def _expected(report, raw):
        from src.inference.level1_core import LandmarkSmoother
        sm = LandmarkSmoother()
        fps = report["source"]["fps_file"]
        return [sm.filter(i * 1000.0 / fps, lm) for i, (lm, _w, _h, _hd) in enumerate(raw)]

    def _assert_same_landmarks(self, got, expected, label):
        self.assertEqual(len(got), len(expected), label)
        for (_ts, lm, _hd), exp in zip(got, expected):
            if exp is None:
                self.assertIsNone(lm, label)
            else:
                np.testing.assert_array_equal(lm, exp, err_msg=label)

    def test_p2_segmenter_and_window_get_smoothed_landmarks(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                report, _app, raw, rec = self.runs[mode]["on"]
                expected = self._expected(report, raw)
                self.assertGreater(sum(e is not None for e in expected), 0)
                self._assert_same_landmarks(rec["segmenter"], expected, "segmenter")
                if mode == "classifier":
                    self._assert_same_landmarks(rec["window"], expected, "window")    # no open palm in this clip
                moved = [not np.allclose(e, lm) for e, (lm, _w, _h, _hd) in zip(expected, raw) if e is not None]
                self.assertTrue(any(moved))                                   # the smoother did change landmarks

    def test_p2_z_jitter_lower_than_raw(self):
        report, _app, raw, rec = self.runs["motion_pose"]["on"]
        pairs_raw, pairs_sm = [], []
        for (a, *_r1), (b, *_r2), (_t1, sa, _h1), (_t2, sb, _h2) in zip(raw, raw[1:], rec["segmenter"],
                                                                          rec["segmenter"][1:]):
            if a is not None and b is not None:
                pairs_raw.append(b[:, 2] - a[:, 2])
                pairs_sm.append(sb[:, 2] - sa[:, 2])
        self.assertGreater(len(pairs_raw), 10)
        self.assertLess(float(np.std(pairs_sm)), float(np.std(pairs_raw)))

    def test_p2_json_block_and_stage(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                report, app, raw, _rec = self.runs[mode]["on"]
                b = report["landmark_smoothing"]
                self.assertEqual(tuple(b), SMOOTH_JSON_KEYS)
                self.assertEqual((b["enabled"], b["alpha_static"], b["alpha_dynamic"], b["speed_threshold"]),
                                 (True, 0.6, 0.9, 0.15))
                hands = [lm is not None for lm, _w, _h, _hd in raw]
                runs = sum(1 for i, h in enumerate(hands) if h and (i == 0 or not hands[i - 1]))
                self.assertEqual(b["frames_static"] + b["frames_dynamic"], sum(hands) - runs)
                self.assertIn("landmark_smooth", report["stages"])
                self.assertEqual(report["stages"]["landmark_smooth"]["n"], len(raw))
                self.assertEqual(list(report)[-1], "landmark_smoothing")

    def test_p2_default_raw_landmarks_and_report_as_before(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                report, _app, raw, rec = self.runs[mode]["off"]
                ref = self.runs[mode]["ref"]
                self._assert_same_landmarks(rec["segmenter"], [lm for lm, _w, _h, _hd in raw], "segmenter")
                self.assertNotIn("landmark_smoothing", report)
                self.assertEqual(list(report), list(ref))
                self.assertEqual(_key_tree(report), _key_tree(ref))
                self.assertEqual(tuple(report["stages"]), tuple(ref["stages"]))
                for k in ("tokens", "text", "labels", "segments", "events", "warnings"):
                    self.assertEqual(report[k], ref[k], (mode, k))
                self.assertEqual(_without_rates(report["counts"]), _without_rates(ref["counts"]))


# ------------------------------------------------------------------ plan 15 lần sửa 10 P3 (angle hint on the HUD)
ANGLE_CLIP = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "hau", "aa_hau_A_001.mp4")
_MISSING_P3 = [p for p in (CLIP, CKPT, ANGLE_CLIP) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]
SKIP_REASON_P3 = "missing (gitignored data / checkpoint): " + ", ".join(_MISSING_P3)
ANGLE_HINT_LINE = "[Góc tay: Hơi nghiêng tay 20°]"


def _tilted_image_hand(degrees):
    """SchematicHand open palm with the index finger straight up (tests/test_level1_core.py) leaning toward the camera
    by `degrees` (foreshortening_ratio = cos of the tilt), in MediaPipe image coordinates of a 640 x 480 frame (x / 640,
    y / 480, z on the x scale). Drives the rule, not data."""
    import math
    from tests.test_level1_core import SchematicHand
    b = math.radians(degrees)
    rot = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(b), -math.sin(b)], [0.0, math.sin(b), math.cos(b)]])
    hand = SchematicHand.build({**SchematicHand.SPREAD, "index": 0.0}, SchematicHand.THUMB_OPEN) @ rot.T
    return (hand / np.array([640.0, 480.0, 640.0]) + np.array([0.5, 0.6, 0.0])).astype(np.float32)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestAngleHintP3(unittest.TestCase):
    """§2 P3: the HUD line "[Góc tay: Hơi nghiêng tay 20°]" while the hand has had foreshortening_ratio < 0.3 (index
    pointing at the camera) for more than 3 consecutive hand frames; another frame (ratio >= 0.3, or no hand) ends it.
    Frames driven through Level1App._angle_step with SchematicHand shapes (rule check, not data)."""

    def _app(self, *extra):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            return app_mod.Level1App(args_for("--source", CLIP, "--headless", *extra))
        finally:
            os.chdir(cwd)

    def test_p3_constants_of_the_plan(self):
        self.assertEqual((app_mod.FORESHORTEN_RATIO_MIN, app_mod.FORESHORTEN_FRAMES), (0.3, 3))

    def test_p3_hint_after_more_than_three_frames(self):
        from src.inference.level1_core import foreshortening_ratio
        from src.inference.level1_segmenter import aspect_points
        steep, flat = _tilted_image_hand(80.0), _tilted_image_hand(0.0)
        self.assertLess(foreshortening_ratio(aspect_points(steep, 640, 480)), 0.3)
        self.assertGreater(foreshortening_ratio(aspect_points(flat, 640, 480)), 0.3)
        for extra in ([], ["--config", REV7_CONFIG]):
            with self.subTest(extra=extra):
                app = self._app(*extra)
                plain = app._hud_lines()[1]
                for _ in range(3):
                    app._angle_step(steep, 640, 480)
                    self.assertEqual(app._hud_lines()[1], plain)               # 3 frames: not yet
                app._angle_step(steep, 640, 480)                               # 4th frame: hint
                small = app._hud_lines()[1]
                self.assertEqual(small.count(ANGLE_HINT_LINE), 1)
                self.assertEqual(small[:2], plain[:2])
                self.assertEqual([s for s in small if s != ANGLE_HINT_LINE], plain)
                app._angle_step(flat, 640, 480)                                # finger tilted: gone
                self.assertEqual(app._hud_lines()[1], plain)
                for _ in range(4):
                    app._angle_step(steep, 640, 480)
                app._angle_step(None, 640, 480)                                # hand lost: gone
                self.assertEqual(app._hud_lines()[1], plain)

    def test_p3_hint_line_drawn_in_yellow(self):
        values = self._app().values
        hud = app_mod.Hud(app_mod.find_font(None, values["font_paths"]), values["hud_font_size"])
        view = np.zeros((120, 640, 3), dtype=np.uint8)
        yellow = np.array(app_mod.Hud.HINT_BGR)

        def n_yellow(small):
            out = hud.compose(view, ["Văn bản:"], small, 0.0)
            return int(np.sum(np.all(out[view.shape[0]:] == yellow, axis=-1)))
        self.assertEqual(n_yellow(["Trạng thái: đang giữ yên"]), 0)
        self.assertGreater(n_yellow(["Trạng thái: đang giữ yên", ANGLE_HINT_LINE]), 0)
        self.assertEqual(tuple(app_mod.Hud.HINT_BGR), tuple(reversed(app_mod.Hud.HINT_RGB)))


@unittest.skipUnless(not _MISSING_P3, SKIP_REASON_P3)
class TestAngleHintClipP3(unittest.TestCase):
    """§2 P3 on real clips (training clips: code path, not accuracy). ANGLE_CLIP (â, the thumb and fingertips toward the
    camera) has runs of frames with foreshortening_ratio < 0.3: the hint state after each frame equals the rule
    recomputed here from the recorded landmarks, and is on for some frames; the D2 clip (a) never shows it. The hint
    is on the HUD only: the report of the D2 clip is that of the app at 8e6d6fb."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV10_COMMIT)
            cls.runs = {}
            for name, clip in (("angle", ANGLE_CLIP), ("plain", CLIP)):
                argv = ["--source", clip, "--headless"]
                _LandmarkHandRecordingSession.instances = []
                app = app_mod.Level1App(args_for(*argv), session_factory=_LandmarkHandRecordingSession)
                states = []
                orig = app._process

                def process(session, frame, t_cap, ts_ms, _orig=orig, _app=app, _states=states):
                    _orig(session, frame, t_cap, ts_ms)
                    _states.append(ANGLE_HINT_LINE in _app._hud_lines()[1])
                app._process = process
                report = app.run()
                cls.runs[name] = {"report": report, "states": states,
                                  "seen": _LandmarkHandRecordingSession.instances[1].seen,
                                  "ref": ref.Level1App(ref.build_parser().parse_args(argv)).run()}
        finally:
            os.chdir(cwd)

    @staticmethod
    def _rule(seen):
        from src.inference.level1_core import foreshortening_ratio
        from src.inference.level1_segmenter import aspect_points
        out, run = [], 0
        for lm, w, h, _hd in seen:
            run = run + 1 if lm is not None and foreshortening_ratio(aspect_points(lm, w, h)) < 0.3 else 0
            out.append(run > 3)
        return out

    def test_p3_hint_follows_rule_on_real_clips(self):
        for name in ("angle", "plain"):
            with self.subTest(name=name):
                r = self.runs[name]
                self.assertEqual(r["states"], self._rule(r["seen"]))
        self.assertGreater(sum(self.runs["angle"]["states"]), 0)
        self.assertEqual(sum(self.runs["plain"]["states"]), 0)

    def test_p3_report_unchanged(self):
        r, ref = self.runs["plain"]["report"], self.runs["plain"]["ref"]
        self.assertEqual(list(r), list(ref))
        self.assertEqual(_key_tree(r), _key_tree(ref))
        for k in ("tokens", "text", "labels", "segments", "events", "warnings"):
            self.assertEqual(r[k], ref[k], k)
        self.assertEqual(_without_rates(r["counts"]), _without_rates(ref["counts"]))



REV10_SMOOTH_COMMAND = ("python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json "
                        "--min-detection-conf 0.35 --auto-enhance --smooth-landmarks")


class TestDesktopDocP3(unittest.TestCase):
    def test_p3_doc_section_10(self):
        import re
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        self.assertIn("## 10.", doc)
        for text in (REV10_SMOOTH_COMMAND, "collinear", "--smooth-landmarks", "LandmarkSmoother", "landmark_smoothing",
                     "landmark_smooth", "foreshortening_ratio", ANGLE_HINT_LINE, "--min-detection-conf 0.35",
                     "--auto-enhance"):
            self.assertIn(text, doc, text)
        self.assertIsNone(re.search(r"\d+(\.\d+)?\s*(ms|%|fps)", doc))   # no measured number (as AC-R'4 / C1)



# ------------------------------------------------------------------ plan 15 lần sửa 10 P1 -> lần sửa 12 H1 (hand lock)
FLIP_CLIP = os.path.join("data", "external", "hauuto_raw", "raw", "raw", "khoi", "aa_khoi_A_001.mp4")
_MISSING_P1 = [p for p in (CLIP, CKPT, FLIP_CLIP) if not os.path.exists(os.path.join(PROJECT_ROOT, p))]
SKIP_REASON_P1 = "missing (gitignored data / checkpoint): " + ", ".join(_MISSING_P1)


class TestDominantHandArgsP1(unittest.TestCase):
    """lần sửa 12 H1: --dominant-hand {auto, lock, Right, Left}, default auto. lock = HandednessLock (majority of
    MediaPipe's own labels on the first hand frames); Right / Left (lần sửa 10 P1) are aliases of lock: the fixed label
    they gave (Right -> 'Left') mirrored every frame of a camera whose driver mirrors (dominant_hand_check.json)."""

    def test_p1_choices_default_aliases(self):
        text = app_mod.build_parser().format_help()
        self.assertIn("--dominant-hand", text)
        self.assertEqual(args_for("--source", CLIP).dominant_hand, "auto")
        for v in ("lock", "Right", "Left", "auto"):
            self.assertEqual(args_for("--source", CLIP, "--dominant-hand", v).dominant_hand, v)
        self.assertEqual(app_mod.DOMINANT_HAND_ALIASES, ("Right", "Left"))
        self.assertFalse(hasattr(app_mod, "DOMINANT_HAND_LABELS"))   # no assumed hand -> label mapping any more

    def test_p1_bad_value_rejected(self):
        import contextlib
        import io
        for bad in ("right", "both", "", "LOCK"):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    args_for("--source", CLIP, "--dominant-hand", bad)


@unittest.skipUnless(not _MISSING_P1, SKIP_REASON_P1)
class TestDominantHandP1(unittest.TestCase):
    """On FLIP_CLIP (â of signer khoi; training clip: code path, not accuracy), whose MediaPipe labels switch between
    Left and Right. --dominant-hand lock: the first HAND_LOCK_FRAMES hand frames keep MediaPipe's label and are counted,
    every later hand frame reaching the segmenter and the window has the majority label; landmarks untouched; JSON
    dominant_hand, HUD line. Right / Left: the same run as lock (requested recorded). auto (default): the session's
    labels pass unchanged and the report is that of the app at 8e6d6fb."""

    @classmethod
    def setUpClass(cls):
        import contextlib
        import io
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            ref = app_module_at(BEFORE_REV10_COMMIT)
            cls.runs = {}
            for mode, extra in (("motion_pose", []), ("classifier", ["--config", REV7_CONFIG])):
                base = ["--source", FLIP_CLIP, "--headless", *extra]
                for hand in ("lock", "Right", "Left", "auto"):
                    flags = [] if hand == "auto" else ["--dominant-hand", hand]
                    _LandmarkHandRecordingSession.instances = []
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        app = app_mod.Level1App(args_for(*base, *flags),
                                                session_factory=_LandmarkHandRecordingSession, keep_segments=True)
                    rec = _spy_inputs(app)
                    report = app.run()
                    cls.runs[(mode, hand)] = {"report": report, "app": app, "rec": rec, "stderr": err.getvalue(),
                                              "seen": _LandmarkHandRecordingSession.instances[1].seen}
                cls.runs[(mode, "ref")] = ref.Level1App(ref.build_parser().parse_args(base)).run()
        finally:
            os.chdir(cwd)

    @staticmethod
    def _mp_labels(run):
        return [hd for lm, _w, _h, hd in run["seen"] if lm is not None]

    def test_p1_clip_labels_switch(self):
        labels = self._mp_labels(self.runs[("motion_pose", "auto")])
        self.assertIn("Left", labels)
        self.assertIn("Right", labels)
        self.assertGreater(sum(a != b for a, b in zip(labels, labels[1:])), 0)

    def test_p1_locked_label_is_mediapipe_majority(self):
        from src.inference.level1_core import HAND_LOCK_FRAMES
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[(mode, "lock")]
                mp_labels = self._mp_labels(r)
                first = mp_labels[:HAND_LOCK_FRAMES]
                majority = max(("Left", "Right"), key=first.count)
                self.assertEqual(r["app"].hand_lock.label, majority)
                for name in ("segmenter", "window") if mode == "classifier" else ("segmenter",):
                    got = [hd for _ts, lm, hd in r["rec"][name] if lm is not None]
                    self.assertGreater(len(got), HAND_LOCK_FRAMES)
                    self.assertEqual(got[:HAND_LOCK_FRAMES], first, name)            # counted, unchanged
                    self.assertEqual(set(got[HAND_LOCK_FRAMES:]), {majority}, name)  # locked
                raw = [lm for lm, _w, _h, _hd in r["seen"]]
                seg_lm = [lm for _ts, lm, _hd in r["rec"]["segmenter"]]
                self.assertEqual([lm is None for lm in raw], [lm is None for lm in seg_lm])  # landmarks untouched
                for a, b in zip(raw, seg_lm):
                    if a is not None:
                        np.testing.assert_array_equal(a, b)

    def test_p1_segments_canonicalize_one_way(self):
        """Every segment that starts after the lock carries the locked label only, so it canonicalizes one way: mirrored
        exactly when MediaPipe's majority label is 'Left' (as the training clips recorded on the same camera)."""
        from src.data.alphabet_preprocessing import canonicalize_hand_sequence
        from src.inference.level1_core import HAND_LOCK_FRAMES
        r = self.runs[("motion_pose", "lock")]
        label = r["app"].hand_lock.label
        lock_ts = [ts for ts, lm, _hd in r["rec"]["segmenter"] if lm is not None][HAND_LOCK_FRAMES - 1]
        segs = [seg for seg in r["app"].kept_segments if seg.t_start_ms > lock_ts]
        self.assertGreater(len(segs), 0)
        for seg in segs:
            self.assertEqual(set(seg.handedness[seg.detected]), {label})
            flag = canonicalize_hand_sequence(seg.raw_landmarks, seg.detected, seg.handedness)[2]
            self.assertIs(flag, label == "Left")

    def test_p1_aliases_run_as_lock(self):
        for mode in ("motion_pose", "classifier"):
            lock = self.runs[(mode, "lock")]["report"]
            for hand in ("Right", "Left"):
                with self.subTest(mode=mode, hand=hand):
                    r = self.runs[(mode, hand)]
                    self.assertIn("now means --dominant-hand lock", r["stderr"])
                    rep = r["report"]
                    self.assertEqual(rep["dominant_hand"], {**lock["dominant_hand"], "requested": hand})
                    for k in ("tokens", "text", "labels", "segments", "warnings"):
                        self.assertEqual(rep[k], lock[k], (mode, hand, k))
            self.assertEqual(self.runs[(mode, "lock")]["stderr"], "")

    def test_p1_json_and_hud(self):
        from src.inference.level1_core import HAND_LOCK_FRAMES
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[(mode, "lock")]
                lock = r["app"].hand_lock
                first = self._mp_labels(r)[:HAND_LOCK_FRAMES]
                self.assertEqual(r["report"]["dominant_hand"],
                                 {"mode": "lock", "requested": "lock", "label": lock.label,
                                  "lock_frames": HAND_LOCK_FRAMES,
                                  "votes": {"Left": first.count("Left"), "Right": first.count("Right")}})
                small = r["app"]._hud_lines()[1]
                line = app_mod.HAND_LOCK_HUD.format(label=lock.label)
                self.assertEqual(small.count(line), 1)
                self.assertEqual(small[:2], [s for s in small if s != line][:2])
                small = self.runs[(mode, "auto")]["app"]._hud_lines()[1]
                self.assertFalse([s for s in small if s.startswith("[Tay:")])

    def test_p1_hud_while_counting(self):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            app = app_mod.Level1App(args_for("--source", CLIP, "--headless", "--dominant-hand", "lock"))
        finally:
            os.chdir(cwd)
        self.assertEqual(app._hand_line(), app_mod.HAND_LOCKING_HUD.format(n=0, total=app.hand_lock.lock_frames))
        app.hand_lock.update("Right")
        self.assertEqual(app._hand_line(), app_mod.HAND_LOCKING_HUD.format(n=1, total=app.hand_lock.lock_frames))

    def test_p1_auto_is_the_app_before(self):
        for mode in ("motion_pose", "classifier"):
            with self.subTest(mode=mode):
                r = self.runs[(mode, "auto")]
                report, ref = r["report"], self.runs[(mode, "ref")]
                got = [hd for _ts, lm, hd in r["rec"]["segmenter"] if lm is not None]
                self.assertEqual(got, [hd for lm, _w, _h, hd in r["seen"] if lm is not None])
                self.assertNotIn("dominant_hand", report)
                self.assertEqual(list(report), list(ref))
                self.assertEqual(_key_tree(report), _key_tree(ref))
                for k in ("tokens", "text", "labels", "segments", "events", "warnings"):
                    self.assertEqual(report[k], ref[k], (mode, k))
                self.assertEqual(_without_rates(report["counts"]), _without_rates(ref["counts"]))


REV10_COMMAND = ("python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json "
                 "--min-detection-conf 0.35 --auto-enhance --dominant-hand Right")
REV12_COMMAND = ("python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev9.json "
                 "--min-detection-conf 0.35 --auto-enhance --dominant-hand lock")


class TestDesktopDocP1(unittest.TestCase):
    def test_p1_doc_dominant_hand(self):
        import re
        with open(os.path.join(PROJECT_ROOT, "docs", "level1_desktop.md"), encoding="utf-8") as f:
            doc = f.read()
        section = doc[doc.index("## 10."):doc.index("## 11.")]
        for text in (REV10_COMMAND, "dominant_hand", "canonicalize_hand_sequence", "bí danh của", "mục 11"):
            self.assertIn(text, section, text)
        section = doc[doc.index("## 11."):]
        for text in (REV12_COMMAND, "--dominant-hand lock", "HandednessLock", "dominant_hand_check.json",
                     "[Tay: khóa Right]", "--auto-space", "--gesture-space", "cls_motion_gate", "frames_gated",
                     "chờ tay yên", "rearm_check_gate.json"):
            self.assertIn(text, section, text)
        self.assertIn(REV12_COMMAND, doc[:doc.index("## 2.")])                 # the command of section 1
        self.assertIsNone(re.search(r"\d+(\.\d+)?\s*(ms|%|fps)", doc))   # no measured number (as AC-R'4 / C1)


# ------------------------------------------------------------------ plan 15 lần sửa 12 S1 / G1 (defaults, motion gate)
REV8_DEMO_CONFIG = os.path.join("configs", "level1_demo_classifier_rev8.json")
REV9_DEMO_CONFIG = os.path.join("configs", "level1_demo_classifier_rev9.json")


class TestDefaultsArgsS1(unittest.TestCase):
    def test_s1_automatic_spaces_off_by_default(self):
        a = args_new("--source", CLIP)
        self.assertIs(a.auto_space, False)
        self.assertIs(a.gesture_space, False)
        self.assertIs(app_mod.AUTO_SPACE_DEFAULT, False)
        self.assertIs(app_mod.GESTURE_SPACE_DEFAULT, False)
        self.assertIs(args_new("--source", CLIP, "--gesture-space").gesture_space, True)
        self.assertIs(args_new("--source", CLIP, "--auto-space").auto_space, True)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestDefaultsS1G1(unittest.TestCase):
    """Runs with the defaults of today (args_new) on CLIP (training clip: code path, not accuracy) with the hand away
    after _HandAwaySession.AWAY_FROM frames: the word gap is detected and logged (configs whose word_gap_ms fits in the
    clip: the default one and DEMO_CONFIG, as TestNoAutoSpaceT3), no space token, JSON auto_space false, no gesture
    block. rev9 (motion gate): counts.frames_gated > 0; rev8: no frames_gated key."""

    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            cls.runs = {}
            for name, extra in (("motion_pose", []), ("classifier", ["--config", DEMO_CONFIG]),
                                ("rev8", ["--config", REV8_DEMO_CONFIG]), ("rev9", ["--config", REV9_DEMO_CONFIG])):
                app = app_mod.Level1App(args_new("--source", CLIP, "--headless", *extra),
                                        session_factory=_HandAwaySession)
                cls.runs[name] = (app, app.run())
        finally:
            os.chdir(cwd)

    def test_s1_no_automatic_space(self):
        for name, (app, r) in self.runs.items():
            with self.subTest(name=name):
                self.assertFalse(app.gesture_space)
                gaps = [e for e in r["events"] if e.get("event") == "word_gap"]
                if name in ("motion_pose", "classifier"):
                    self.assertEqual(r["counts"]["word_gaps"], 1)
                    self.assertEqual(len(gaps), 1)
                self.assertEqual(len(gaps), r["counts"]["word_gaps"])
                self.assertTrue(all(g["auto_space"] is False for g in gaps))
                self.assertNotIn(" ", r["tokens"])
                self.assertIs(r["auto_space"], False)
                self.assertNotIn("gesture_space", r)

    def test_g1_frames_gated_only_with_the_gate(self):
        self.assertNotIn("frames_gated", self.runs["motion_pose"][1]["counts"])
        self.assertNotIn("frames_gated", self.runs["rev8"][1]["counts"])
        app, r = self.runs["rev9"]
        self.assertTrue(app.decoder.motion_gate)
        self.assertGreater(r["counts"]["frames_gated"], 0)
        self.assertEqual(r["counts"]["frames_gated"], app.decoder.n_gated)

    def test_g1_gate_never_emits_on_a_moving_frame(self):
        """Every label of the rev9 run was emitted on a frame where the segmenter was not 'moving'."""
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            app = app_mod.Level1App(args_new("--source", CLIP, "--headless", "--config", REV9_DEMO_CONFIG))
            states = {}
            orig = app.segmenter.push

            def push(ts_ms, *a, **k):
                out = orig(ts_ms, *a, **k)
                states[ts_ms] = app.segmenter.state
                return out
            app.segmenter.push = push
            r = app.run()
        finally:
            os.chdir(cwd)
        self.assertGreater(len(r["labels"]), 0)
        for lab in r["labels"]:
            self.assertNotEqual(states[lab["ts_ms"]], "moving", lab)

    def test_g1_decoder_line_while_gated(self):
        app, _r = self.runs["rev9"]
        app.last_window = None
        app.segmenter._last_has_hand, app.segmenter._still_since = True, None   # state 'moving'
        self.assertTrue(app._decoder_line().endswith("| chờ tay yên"))
        app.segmenter._still_since = 0.0                                         # state 'holding'
        self.assertNotIn("chờ tay yên", app._decoder_line())
        self.assertNotIn("chờ tay yên", self.runs["rev8"][0]._decoder_line())


if __name__ == "__main__":
    unittest.main()

