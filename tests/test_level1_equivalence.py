"""
Plan 15 AC-E: Level 1 train <-> desktop realtime equivalence (B4).

E1 (BIT-identical, no tolerance; plan 15 §7-1 otherwise stop): the 10 clips of
scripts/hand_live_check.select_clips(rows, 8, 0) (8 hauuto clips with a local video + the first 2 qipedc clips).
Per clip the app itself is run (level1_demo.Level1App, --headless replay: VideoFileReader, every frame in order,
a new HandLandmarkSession per clip); the session's outputs are recorded by a subclass that only calls the real
HandLandmarkSession.process and keeps what it returns.
Offline = scripts/extract_hands_batch.py::_extract_one (imported, unchanged) into a temporary directory.
  - landmarks / detected / handedness / score: array_equal with the offline npz;
  - segment = the whole clip -> Level1Classifier.features == alphabet_clip_features on the offline result;
  - Level1Classifier.classify == POST /api/fingerspelling/sequence for hand_live_check.body_from_npz(offline)
    (prediction, confidence, candidates).
hauuto clips are training data of the deployed Level 1 model: this checks identical inputs, not accuracy.

E3: level1_demo.py and src/inference/level1_*.py never call Hands(...) or cv2.resize, and cv2.flip only inside
display_view (AST); the frame given to HandLandmarkSession.process is the very object returned by the reader
(spy; headless replay and --pace realtime).
"""
import ast
import glob
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hand_live_check as H  # noqa: E402
import level1_demo as app_mod  # noqa: E402
from src.inference.hand_live import HandLandmarkSession  # noqa: E402

N_HAUUTO, SEED = 8, 0
TOP_K = H.TOP_K
COMPARED_KEYS = ("prediction", "confidence", "candidates")
TMP_PARENT = os.path.join(PROJECT_ROOT, "_work", "_plan15_tmp")
_MISSING = [os.path.relpath(p, PROJECT_ROOT) for p in
            (H.MANIFEST, H.HAUUTO_VIDEO_DIR, H.QIPEDC_VIDEO_DIR, H.DEPLOYED_CKPT,
             os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"))
            if not os.path.exists(p)]
SKIP_REASON = "missing (gitignored data / checkpoint; clean clone): " + ", ".join(_MISSING)


class RecordingSession(HandLandmarkSession):
    """The real HandLandmarkSession; process() is unchanged, its input frame and output are recorded."""
    instances = []

    def __init__(self):
        self.frames_in = []
        self.outputs = []
        super().__init__()
        RecordingSession.instances.append(self)

    def process(self, frame_bgr):
        out = super().process(frame_bgr)
        self.frames_in.append(frame_bgr)
        self.outputs.append(out)
        return out


class SpyReader:
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


class SpyApp(app_mod.Level1App):
    """Level1App whose reader (the app's own VideoFileReader) is wrapped by SpyReader."""

    def _open_reader(self):
        self.spy_reader = SpyReader(super()._open_reader())
        return self.spy_reader


def run_app(video, classifier, extra=("--headless",)):
    """One app run on a video with a fresh RecordingSession; returns (app, report, stream session)."""
    argv = ["--source", video, *extra]
    args = app_mod.build_parser().parse_args(argv)
    RecordingSession.instances = []
    app = SpyApp(args, argv=argv, classifier=classifier, session_factory=RecordingSession)
    report = app.run()
    sessions = list(RecordingSession.instances)
    # the first session is the warm-up (one blank frame), the second one processes the stream
    assert len(sessions) == 2, len(sessions)
    assert len(sessions[0].outputs) == 1, len(sessions[0].outputs)
    return app, report, sessions[1]


def segment_from_outputs(outputs, width, height, fps):
    """SignSegment holding the whole clip as seen by the app (zeros / '' where no hand), timestamps
    i * 1000 / fps."""
    from src.inference.level1_segmenter import SignSegment
    n = len(outputs)
    raw = np.zeros((n, 21, 3), dtype=np.float32)
    det = np.zeros(n, dtype=bool)
    for i, (lms, _hand, _score) in enumerate(outputs):
        if lms is not None:
            raw[i] = lms
            det[i] = True
    ts = np.array([H.timestamp_ms(i, fps) for i in range(n)], dtype=np.float64)
    return SignSegment(seq=1, raw_landmarks=raw, detected=det, handedness=np.array([o[1] for o in outputs]),
                       timestamps_ms=ts, frame_width=int(width), frame_height=int(height),
                       t_start_ms=float(ts[0]), t_end_ms=float(ts[-1]), t_emit_ms=float(ts[-1]),
                       close_reason="end_of_stream")


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestEquivalenceE1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import backend.main as api
        from src.inference.level1_core import Level1Classifier

        cls.api = api
        cls._saved = (api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta)
        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = H.DEPLOYED_CKPT, None, None
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started
        cls.clf = Level1Classifier.from_checkpoint(H.DEPLOYED_CKPT)
        cls.rows = H.select_clips(H.read_manifest(), N_HAUUTO, SEED)

        os.makedirs(TMP_PARENT, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_e1_", dir=TMP_PARENT)
        extract = H.load_extract_module()
        cls.results = []
        for row in cls.rows:
            video = H.video_path_for(row)
            off = H.offline_extract(row, cls.tmp, extract)
            app, report, session = run_app(video, cls.clf)
            cls.results.append({"row": row, "off": off, "outputs": session.outputs,
                                "fps": app.spy_reader.fps, "frame_size": report["frame_size"],
                                "n_read": len(app.spy_reader.frames_out),
                                "frames_processed": report["counts"]["frames_processed"],
                                "same_objects": len(session.frames_in) == len(app.spy_reader.frames_out) and all(
                                    a is b for a, b in zip(session.frames_in, app.spy_reader.frames_out))})
            del app, session

    @classmethod
    def tearDownClass(cls):
        cls.api.ALPHABET_CKPT = cls._saved[0]
        cls.api._alphabet_model, cls.api._alphabet_meta = None, None
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_0_sample(self):
        self.assertEqual(len(self.rows), N_HAUUTO + H.N_QIPEDC)
        self.assertEqual([r["source"] for r in self.rows], ["hauuto"] * N_HAUUTO + ["qipedc"] * H.N_QIPEDC)
        self.assertEqual(len({r["sample_id"] for r in self.rows}), len(self.rows))
        for res in self.results:  # printed from the run, not typed
            print(f"\n[E1] {res['row']['sample_id']}: frames={len(res['outputs'])} "
                  f"detected={sum(o[0] is not None for o in res['outputs'])} fps={res['fps']}", end="")
        print()

    def test_e1a_landmarks_identical(self):
        for res in self.results:
            off, outs = res["off"], res["outputs"]
            meta = off["metadata"]
            with self.subTest(res["row"]["sample_id"]):
                n = len(off["detected_mask"])
                self.assertEqual(len(outs), n)
                self.assertEqual(res["n_read"], n)
                self.assertEqual(res["frames_processed"], n)
                self.assertTrue(res["same_objects"])
                self.assertEqual(res["fps"], meta["fps"])
                self.assertEqual(res["frame_size"], {"width": meta["width"], "height": meta["height"]})
                det = np.array([o[0] is not None for o in outs])
                self.assertTrue(np.array_equal(det, off["detected_mask"]))
                lms = np.zeros((n, 21, 3), dtype=np.float32)
                for i, o in enumerate(outs):
                    if o[0] is not None:
                        self.assertEqual(o[0].dtype, np.float32)
                        self.assertEqual(o[0].shape, (21, 3))
                        lms[i] = o[0]
                self.assertTrue(np.array_equal(lms, off["raw_landmarks"]))
                self.assertEqual([o[1] for o in outs], off["handedness_label"])
                scores = np.array([0.0 if o[2] is None else o[2] for o in outs], dtype=np.float32)
                self.assertTrue(np.array_equal(scores, off["handedness_score"]))
                self.assertTrue(all(o[2] is None for o in outs if o[0] is None))

    def test_e1b_features_identical(self):
        from src.data.alphabet_preprocessing import alphabet_clip_features
        for res in self.results:
            off = res["off"]
            meta = off["metadata"]
            seg = segment_from_outputs(res["outputs"], res["frame_size"]["width"], res["frame_size"]["height"],
                                       res["fps"])
            ts = np.asarray([H.timestamp_ms(i, meta["fps"]) for i in range(len(off["detected_mask"]))])
            ref = alphabet_clip_features(off["raw_landmarks"], off["detected_mask"],
                                         np.array(off["handedness_label"]), meta["width"] / meta["height"], ts,
                                         self.clf.preprocessing, self.clf.model_type)
            with self.subTest(res["row"]["sample_id"]):
                self.assertTrue(np.array_equal(seg.timestamps_ms, ts))
                mine = self.clf.features(seg)
                self.assertEqual(mine.shape, ref.shape)
                self.assertEqual(mine.dtype, ref.dtype)
                self.assertTrue(np.array_equal(mine, ref))

    def test_e1c_classify_equals_sequence_endpoint(self):
        for res in self.results:
            off = res["off"]
            meta = off["metadata"]
            body = H.body_from_npz(off, meta["width"], meta["height"], meta["fps"])
            seg = segment_from_outputs(res["outputs"], res["frame_size"]["width"], res["frame_size"]["height"],
                                       res["fps"])
            with self.subTest(res["row"]["sample_id"]):
                r = self.client.post(H.SEQ_PATH, json=body)
                self.assertEqual(r.status_code, 200, r.text[:300])
                api = r.json()
                self.assertEqual(api["checkpoint"], "alphabet_best.pt")
                mine = self.clf.classify(seg, body["top_k"])
                self.assertEqual(mine["status"], "ok")
                for k in COMPARED_KEYS:
                    self.assertEqual(mine[k], api[k], k)
                print(f"\n[E1] {res['row']['sample_id']}: classify == /sequence "
                      f"({mine['prediction']!r}, {mine['confidence']})", end="")
        print()


def _calls(tree):
    """(call name, enclosing function name or None) for every call in the module."""
    out = []

    def visit(node, func):
        for child in ast.iter_child_nodes(node):
            f = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
            if isinstance(child, ast.Call):
                fn = child.func
                if isinstance(fn, ast.Attribute):
                    base = fn.value.id if isinstance(fn.value, ast.Name) else None
                    out.append(((base + "." if base else "") + fn.attr, fn.attr, func))
                elif isinstance(fn, ast.Name):
                    out.append((fn.id, fn.id, func))
            visit(child, f)

    visit(tree, None)
    return out


E3_FILES = ["level1_demo.py"] + sorted(
    os.path.relpath(p, PROJECT_ROOT).replace(os.sep, "/")
    for p in glob.glob(os.path.join(PROJECT_ROOT, "src", "inference", "level1_*.py")))


class TestEquivalenceE3Static(unittest.TestCase):
    def test_files(self):
        for f in ("level1_demo.py", "src/inference/level1_core.py", "src/inference/level1_segmenter.py",
                  "src/inference/level1_timing.py"):
            self.assertIn(f, E3_FILES)

    def test_e3_no_hands_resize_flip_outside_display(self):
        for rel in E3_FILES:
            with open(os.path.join(PROJECT_ROOT, rel), encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=rel)
            calls = _calls(tree)
            with self.subTest(rel):
                self.assertEqual([c for c in calls if c[1] == "Hands"], [])
                self.assertEqual([c for c in calls if c[1] == "resize"], [])
                flips = [c for c in calls if c[1] == "flip"]
                self.assertTrue(all(c[0] == "cv2.flip" and c[2] == "display_view" for c in flips), flips)
                if rel == "level1_demo.py":
                    self.assertEqual(len(flips), 1)

    def test_e3_ast_helper_sees_calls(self):
        # self-check: the walker reports a nested Hands(...) / cv2.resize / cv2.flip with its function
        tree = ast.parse("import cv2\ndef f(x):\n    h = mp.solutions.hands.Hands()\n    return cv2.resize(x, (1, 1))\n"
                         "def display_view(x):\n    return cv2.flip(x, 1)\n")
        calls = _calls(tree)
        self.assertIn(("Hands", "f"), [(c[1], c[2]) for c in calls])
        self.assertIn(("cv2.resize", "resize", "f"), calls)
        self.assertIn(("cv2.flip", "flip", "display_view"), calls)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestEquivalenceE3Spy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import Level1Classifier
        cls.clf = Level1Classifier.from_checkpoint(H.DEPLOYED_CKPT)
        cls.video = H.video_path_for(H.select_clips(H.read_manifest(), N_HAUUTO, SEED)[0])

    def test_e3_headless_frame_is_object_read(self):
        app, report, session = run_app(self.video, self.clf, ("--headless",))
        read = app.spy_reader.frames_out
        self.assertGreater(len(read), 0)
        self.assertEqual(len(session.frames_in), len(read))
        self.assertTrue(all(a is b for a, b in zip(session.frames_in, read)))
        self.assertEqual(report["source"]["mode"], "headless")

    def test_e3_paced_frame_is_object_read(self):
        app, report, session = run_app(self.video, self.clf, ("--headless", "--pace", "realtime"))
        read = app.spy_reader.frames_out
        self.assertEqual(report["source"]["mode"], "paced")
        self.assertGreater(len(session.frames_in), 0)
        # newest frame only: every processed frame is one of the read objects, in reading order, never a copy
        pos = [next((i for i, r in enumerate(read) if r is f), -1) for f in session.frames_in]
        self.assertNotIn(-1, pos)
        self.assertEqual(pos, sorted(set(pos)))


if __name__ == "__main__":
    unittest.main()
