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


def args_for(*argv):
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
        self.assertIn("--no-auto-space", app_mod.build_parser().format_help())
        self.assertFalse(args_for("--source", CLIP).no_auto_space)
        self.assertTrue(args_for("--source", CLIP, "--no-auto-space").no_auto_space)


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
        self.assertNotIn("auto_space", r)
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


if __name__ == "__main__":
    unittest.main()

