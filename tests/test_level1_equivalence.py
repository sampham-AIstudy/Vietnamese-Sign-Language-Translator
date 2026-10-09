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

E3: level1_demo.py and src/inference/level1_*.py never call Hands(...) or cv2.resize (see E4), and cv2.flip only inside
display_view (AST); the frame given to HandLandmarkSession.process is the very object returned by the reader
(spy; headless replay and --pace realtime).

E4 (plan 15-lan-sua-13a): the single exception is one cv2.resize(view_bgr, size, interpolation=...) of the DISPLAY
image in src/inference/level1_display.py::render_to_window (module level, after MediaPipe); _e4_violations also
forbids cv2 aliases / bare references / getattr(cv2, ...), cv2.warpAffine/warpPerspective/remap/pyrDown/pyrUp in every
E3 file, and any MediaPipe / landmark path in level1_display.py; render_to_window never modifies its input
(tests/test_level1_display.py).
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

# ngoại lệ E4 — 15-lan-sua-13a: the ONLY resize allowed in E3_FILES is this one call on the DISPLAY image
# (after MediaPipe, never the frame given to HandLandmarkSession.process); closed list, no other file / function / call.
E4_FILE = "src/inference/level1_display.py"
E4_FUNC = "render_to_window"
E4_RESIZE_CALLS = [("cv2.resize", "resize", E4_FUNC)]
E4_CV2_GEOMETRY = frozenset({"resize", "flip", "warpAffine", "warpPerspective", "remap", "pyrDown", "pyrUp"})
E4_CV2_FORBIDDEN_CALLS = frozenset({"warpAffine", "warpPerspective", "remap", "pyrDown", "pyrUp"})
E4_DISPLAY_IMPORT_ROOTS = frozenset({"__future__", "dataclasses", "typing", "math", "cv2", "numpy"})
E4_DISPLAY_FORBIDDEN_NAMES = frozenset({"HandLandmarkSession", "mediapipe", "Hands"})


def _is_cv2(node):
    return isinstance(node, ast.Name) and node.id == "cv2"


def _e4_violations(rel, source):
    """Plan 15-lan-sua-13a §3.2 items 1-4 for one file of E3_FILES (`rel`: project-relative, '/'): the E4 exception and
    the checks that compensate it. Pure (AST of `source` only); returns the violations, [] = valid."""
    tree = ast.parse(source, filename=rel)
    bad = []
    is_display = rel == E4_FILE

    # E3 + E4: the resize calls seen by _calls
    resizes = [c for c in _calls(tree) if c[1] == "resize"]
    expected = E4_RESIZE_CALLS if is_display else []
    if resizes != expected:
        bad.append(f"resize calls {resizes} != {expected}")

    # 1. render_to_window: never nested (any file); in the display file defined exactly once, at module level
    module_level = {id(n) for n in tree.body}
    defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == E4_FUNC]
    nested = [n.lineno for n in defs if id(n) not in module_level]
    if nested:
        bad.append(f"{E4_FUNC} defined inside a function/class at line(s) {nested}")
    if is_display:
        resize_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and (
            (isinstance(n.func, ast.Attribute) and n.func.attr == "resize")
            or (isinstance(n.func, ast.Name) and n.func.id == "resize"))]
        if len(defs) != 1 or nested:
            bad.append(f"{E4_FUNC} must be defined exactly once at module level, found {len(defs)} definition(s)")
        else:
            fn = defs[0]
            params = fn.args.posonlyargs + fn.args.args
            first = params[0].arg if params else None
            rebound = sorted(n.lineno for n in ast.walk(fn)
                             if isinstance(n, ast.Name) and n.id == first and isinstance(n.ctx, (ast.Store, ast.Del)))
            if rebound:
                bad.append(f"first parameter {first!r} of {E4_FUNC} rebound at line(s) {rebound}")
            for call in resize_nodes:
                where = f"resize at line {call.lineno}"
                if not (fn.lineno <= call.lineno and call.end_lineno <= fn.end_lineno):
                    bad.append(f"{where} outside {E4_FUNC} (lines {fn.lineno}-{fn.end_lineno})")
                # 2. resize(<first parameter>, <size>, interpolation=...) only
                if len(call.args) != 2:
                    bad.append(f"{where}: {len(call.args)} positional arguments, expected 2")
                if not (call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == first):
                    bad.append(f"{where}: first argument is not the parameter {first!r}")
                keywords = [k.arg for k in call.keywords]
                if not set(keywords) <= {"interpolation"}:
                    bad.append(f"{where}: keywords {keywords} not within ['interpolation']")

    # 3. no alias / indirect use of cv2 geometry functions
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and (n.module == "cv2" or n.module.startswith("cv2.")):
            bad.append(f"line {n.lineno}: from {n.module} import ...")
        elif isinstance(n, ast.Import):
            for a in n.names:
                if (a.name == "cv2" or a.name.startswith("cv2.")) and a.asname is not None:
                    bad.append(f"line {n.lineno}: import {a.name} as {a.asname}")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and n.args \
                and _is_cv2(n.args[0]):
            bad.append(f"line {n.lineno}: getattr(cv2, ...)")
        elif isinstance(n, ast.Attribute) and _is_cv2(n.value) and n.attr in E4_CV2_GEOMETRY:
            if id(n) not in called:
                bad.append(f"line {n.lineno}: bare reference cv2.{n.attr} (not called)")
            elif n.attr in E4_CV2_FORBIDDEN_CALLS:
                bad.append(f"line {n.lineno}: call cv2.{n.attr}")

    # 4. the display module only displays: no MediaPipe / landmark path
    if is_display:
        roots = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                roots.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                roots.add("." * n.level + (n.module or "").split(".")[0])
        if roots - E4_DISPLAY_IMPORT_ROOTS:
            extra = sorted(roots - E4_DISPLAY_IMPORT_ROOTS)
            bad.append(f"imports {extra} not within {sorted(E4_DISPLAY_IMPORT_ROOTS)}")
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "process":
                bad.append(f"line {n.lineno}: call .process(...)")
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "__import__":
                bad.append(f"line {n.lineno}: __import__(...)")
            name = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else None
            if name in E4_DISPLAY_FORBIDDEN_NAMES:
                bad.append(f"line {n.lineno}: name {name}")
    return bad


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
                resizes = [c for c in calls if c[1] == "resize"]
                self.assertEqual(resizes, E4_RESIZE_CALLS if rel == E4_FILE else [])  # ngoại lệ E4 — 15-lan-sua-13a
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


# Source mimicking the current render_to_window of level1_display.py (the one valid E4 case) and the closed list of
# invalid sources of AC-E4c (plan 15-lan-sua-13a §5): (case, rel, source); every one must give violations.
_E4_HEAD = ("import dataclasses\nfrom typing import Any, Callable, Optional, Sequence, Tuple\n\nimport cv2\n"
            "import numpy as np\n\n\n")
_E4_FIT = ("def fit_layout(cam_w, cam_h, panel_h, win_w=None, win_h=None):\n"
           "    natural_h = cam_h + panel_h\n"
           "    return (cam_w, natural_h)\n\n\n")
_E4_RENDER = ("def render_to_window(view_bgr, panel_builder, stats_lines, hold_progress, layout):\n"
              "    canvas = np.zeros((layout.win_h, layout.win_w, 3), dtype=np.uint8)\n"
              "    content = canvas[layout.y0:layout.y0 + layout.content_h, layout.x0:layout.x0 + layout.content_w]\n"
              "    cam_h = layout.cam_rect[3]\n"
              "    width = layout.content_w\n"
              "    if view_bgr.shape[:2] == (cam_h, width):\n"
              "        content[:cam_h] = view_bgr\n"
              "    else:\n"
              "        content[:cam_h] = cv2.resize(view_bgr, (width, cam_h), interpolation=cv2.INTER_LINEAR)\n"
              "    return canvas\n")
_E4_VALID = _E4_HEAD + _E4_FIT + _E4_RENDER
_E4_RESIZE_LINE = "content[:cam_h] = cv2.resize(view_bgr, (width, cam_h), interpolation=cv2.INTER_LINEAR)"


def _e4_replace(old, new, source=_E4_VALID):
    assert source.count(old) == 1, old
    return source.replace(old, new)


_E4_BAD_CASES = [
    ("1 resize in fit_layout", "src/inference/level1_display.py",
     _e4_replace("    natural_h = cam_h + panel_h\n",
                 "    natural_h = cam_h + panel_h\n    _ = cv2.resize(np.zeros((2, 2, 3), np.uint8), (1, 1))\n")),
    ("2 two resizes in render_to_window", "src/inference/level1_display.py",
     _e4_replace("    return canvas\n", "    small = cv2.resize(view_bgr, (2, 2))\n    return canvas\n")),
    ("3 valid render_to_window in another file", "src/inference/level1_core.py", _E4_VALID),
    ("4 from cv2 import resize as r", "src/inference/level1_display.py",
     _e4_replace("import cv2\n", "import cv2\nfrom cv2 import resize as r\n")),
    ("5 import cv2 as c", "src/inference/level1_display.py",
     _e4_replace("import cv2\n", "import cv2\nimport cv2 as c\n")),
    ("6 f = cv2.resize", "src/inference/level1_display.py",
     _e4_replace("    return canvas\n", "    f = cv2.resize\n    return canvas\n")),
    ("7 getattr(cv2, 'resize')", "src/inference/level1_display.py",
     _e4_replace("    return canvas\n", "    g = getattr(cv2, \"resize\")\n    return canvas\n")),
    ("8 render_to_window nested in another function", "src/inference/level1_display.py",
     _E4_HEAD + _E4_FIT + "def outer():\n" + "".join("    " + ln + "\n" for ln in _E4_RENDER.splitlines())
     + "    return render_to_window\n"),
    ("8b nested render_to_window next to the module-level one", "src/inference/level1_display.py",
     _E4_VALID + "\n\nclass Window:\n    def render_to_window(self, frame):\n        return frame\n"),
    ("9 first argument is not the first parameter", "src/inference/level1_display.py",
     _e4_replace(_E4_RESIZE_LINE, "frame = view_bgr[::1]\n        content[:cam_h] = cv2.resize(frame, (width, cam_h), "
                                  "interpolation=cv2.INTER_LINEAR)")),
    ("9b first parameter rebound before the resize", "src/inference/level1_display.py",
     _e4_replace(_E4_RESIZE_LINE, "view_bgr = view_bgr[::2, ::2]\n        " + _E4_RESIZE_LINE)),
    ("10 keyword dst=", "src/inference/level1_display.py",
     _e4_replace(_E4_RESIZE_LINE, "cv2.resize(view_bgr, (width, cam_h), dst=content[:cam_h], "
                                  "interpolation=cv2.INTER_LINEAR)")),
    ("10b **kwargs", "src/inference/level1_display.py",
     _e4_replace("interpolation=cv2.INTER_LINEAR)", "**{\"interpolation\": cv2.INTER_LINEAR})")),
    ("10c three positional arguments", "src/inference/level1_display.py",
     _e4_replace("(width, cam_h), interpolation", "(width, cam_h), None, interpolation")),
    ("11 cv2.warpAffine in level1_display.py", "src/inference/level1_display.py",
     _e4_replace("    return canvas\n", "    w = cv2.warpAffine(view_bgr, np.eye(2, 3), (2, 2))\n    return canvas\n")),
    ("11b cv2.warpAffine in another file", "src/inference/level1_core.py",
     "import cv2\nimport numpy as np\n\n\ndef f(frame):\n    return cv2.warpAffine(frame, np.eye(2, 3), (2, 2))\n"),
    ("11c cv2.pyrDown in level1_demo.py", "level1_demo.py",
     "import cv2\n\n\ndef f(frame):\n    return cv2.pyrDown(frame)\n"),
    ("12 import mediapipe", "src/inference/level1_display.py",
     _e4_replace("import numpy as np\n", "import numpy as np\nimport mediapipe\n")),
    ("12b from src.inference.hand_live import HandLandmarkSession", "src/inference/level1_display.py",
     _e4_replace("import numpy as np\n",
                 "import numpy as np\nfrom src.inference.hand_live import HandLandmarkSession\n")),
    ("13 session.process(x)", "src/inference/level1_display.py",
     _e4_replace("    return canvas\n", "    session.process(view_bgr)\n    return canvas\n")),
]


class TestEquivalenceE4Display(unittest.TestCase):
    """Exception E4 (plan 15-lan-sua-13a §3.2): one cv2.resize of the DISPLAY image in render_to_window, plus the
    static checks that compensate it (items 1-4), on synthetic sources (AC-E4c) and on every file of E3_FILES."""

    def test_e4_file_is_scanned(self):
        self.assertIn(E4_FILE, E3_FILES)
        self.assertEqual(E4_RESIZE_CALLS, [("cv2.resize", "resize", "render_to_window")])

    def test_e4_valid_source_passes(self):
        self.assertEqual(_e4_violations(E4_FILE, _E4_VALID), [])
        # the valid source is what E3 sees in the real file: exactly the E4 resize
        self.assertEqual([c for c in _calls(ast.parse(_E4_VALID)) if c[1] == "resize"], E4_RESIZE_CALLS)

    def test_e4_bad_sources_flagged(self):
        self.assertEqual(len({name for name, _, _ in _E4_BAD_CASES}), len(_E4_BAD_CASES))
        for name, rel, source in _E4_BAD_CASES:
            with self.subTest(name):
                ast.parse(source)  # the case is valid Python: it is the check that must refuse it
                self.assertNotEqual(_e4_violations(rel, source), [])

    def test_e4_real_files(self):
        for rel in E3_FILES:
            with open(os.path.join(PROJECT_ROOT, rel), encoding="utf-8") as fh:
                source = fh.read()
            with self.subTest(rel):
                self.assertEqual(_e4_violations(rel, source), [])


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


class _WindowCallsU6b:
    """The OpenCV window calls of the window mode, recorded (no window opens). The window image rect is
    (0, 0, 1920, 1080), so every frame shown goes through render_to_window (the E4 display resize)."""

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
    def getWindowImageRect(name):
        return (0, 0, 1920, 1080)

    @staticmethod
    def namedWindow(*a, **k):
        return None

    @staticmethod
    def resizeWindow(*a, **k):
        return None

    @staticmethod
    def destroyAllWindows():
        return None


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestEquivalenceU6bWindow(unittest.TestCase):
    """AC-U6b (plan 15-lan-sua-13a §3.2 item 6, step U2 / 13b U2b): the app in WINDOW mode with a 1920x1080 window
    (recorded window calls, _WindowCallsU6b), on the clip of TestEquivalenceE3Spy with RecordingSession + SpyReader:
    every frame given to HandLandmarkSession.process IS the object returned by the reader (all of them in order in
    the replay window mode; in reading order, never a copy, with --pace realtime), and the images shown are
    (1080, 1920, 3), i.e. the display resize path ran in the same run."""

    @classmethod
    def setUpClass(cls):
        from src.inference.level1_core import Level1Classifier
        cls.clf = Level1Classifier.from_checkpoint(H.DEPLOYED_CKPT)
        cls.video = H.video_path_for(H.select_clips(H.read_manifest(), N_HAUUTO, SEED)[0])

    def run_window(self, extra):
        from unittest import mock
        rec = _WindowCallsU6b()
        cwd = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            with mock.patch.multiple(app_mod.cv2, imshow=rec.imshow, waitKey=rec.waitKey,
                                     getWindowProperty=rec.getWindowProperty,
                                     getWindowImageRect=rec.getWindowImageRect, namedWindow=rec.namedWindow,
                                     resizeWindow=rec.resizeWindow, destroyAllWindows=rec.destroyAllWindows):
                app, report, session = run_app(self.video, self.clf, extra)
        finally:
            os.chdir(cwd)
        return rec, app, report, session

    def assert_scaled_display(self, rec, report):
        self.assertEqual(len(rec.shown), report["counts"]["frames_processed"])
        self.assertIn((1080, 1920, 3), rec.shown)
        self.assertTrue(all(shape == (1080, 1920, 3) for shape in rec.shown), set(rec.shown))

    def test_u6b_window_frame_is_object_read(self):
        rec, app, report, session = self.run_window(())
        read = app.spy_reader.frames_out
        self.assertEqual(report["source"]["mode"], "gui")
        self.assertGreater(len(read), 0)
        self.assertEqual(len(session.frames_in), len(read))
        self.assertTrue(all(a is b for a, b in zip(session.frames_in, read)))
        self.assert_scaled_display(rec, report)

    def test_u6b_window_paced_frame_is_object_read(self):
        rec, app, report, session = self.run_window(("--pace", "realtime"))
        read = app.spy_reader.frames_out
        self.assertEqual(report["source"]["mode"], "paced")
        self.assertGreater(len(session.frames_in), 0)
        pos = [next((i for i, r in enumerate(read) if r is f), -1) for f in session.frames_in]
        self.assertNotIn(-1, pos)
        self.assertEqual(pos, sorted(set(pos)))
        self.assert_scaled_display(rec, report)


if __name__ == "__main__":
    unittest.main()
