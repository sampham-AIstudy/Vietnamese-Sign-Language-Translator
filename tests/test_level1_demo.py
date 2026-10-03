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


if __name__ == "__main__":
    unittest.main()
