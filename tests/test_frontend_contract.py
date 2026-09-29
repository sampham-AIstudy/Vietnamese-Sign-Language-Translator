"""
Plan 06 frontend contract checks (Python side).

- AC8: source guard over frontend/src/**/*.{js,jsx} (no Math.random, no backend port / literal ws:// URL, no fake
  1x1 JPEG frame, no call of the retired image endpoint, no hard-coded buffer size / class count). The guard function
  is self-tested with in-memory violating samples.
- AC7-d: cross-language check: the live hand_frame messages of one real hauuto clip (WS /ws/hand-landmarks, as in
  AC5) go through the frontend's buildSequenceBody (node frontend/tests/build_body_cli.mjs); the body must equal
  the Python body built from the offline _extract_one landmarks, and POST /api/fingerspelling/sequence -> 200.
- AC6: reports/fingerspell_live_*/hand_live_check.json carries no landmark array and has generated_by.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FRONTEND_SRC = os.path.join(PROJECT_ROOT, "frontend", "src")
BUILD_BODY_CLI = os.path.join(PROJECT_ROOT, "frontend", "tests", "build_body_cli.mjs")

# (rule name, compiled pattern)
GUARD_RULES = [
    ("Math.random", re.compile(r"Math\.random")),
    ("backend port :8000", re.compile(r":8000")),
    ("literal ws:// or wss:// URL", re.compile(r"wss?://")),
    ("fake base64 JPEG frame", re.compile(r"data:image/jpeg;base64,/9j/")),
    ("retired image endpoint '/api/fingerspelling'", re.compile(r"/api/fingerspelling['\"`]")),
    ("hard-coded bufferCapacity={60}", re.compile(r"bufferCapacity=\{60\}")),
    ("hard-coded '25 lớp'", re.compile(r"25 lớp")),
]


def guard_violations(text, name="<memory>"):
    """[(name, line_no, rule)] for every guard rule matched in `text`."""
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        for rule, rx in GUARD_RULES:
            if rx.search(line):
                out.append((name, no, rule))
    return out


def frontend_source_files():
    files = []
    for ext in ("js", "jsx"):
        files += glob.glob(os.path.join(FRONTEND_SRC, "**", f"*.{ext}"), recursive=True)
    return sorted(files)


class TestGuardSelfCheck(unittest.TestCase):
    """AC8: the guard reports each violating sample (strings in memory, not files)."""

    SAMPLES = {
        "Math.random": "const conf = Math.random();",
        "backend port :8000": "fetch(`http://${host}:8000/api/health`)",
        "literal ws:// or wss:// URL": "new WebSocket('ws://localhost/ws/live-stream')",
        "fake base64 JPEG frame": "const f = 'data:image/jpeg;base64,/9j/4AAQSkZJRg';",
        "retired image endpoint '/api/fingerspelling'": "await fetch('/api/fingerspelling', {method: 'POST'})",
        "hard-coded bufferCapacity={60}": "<PredictionDisplay bufferCapacity={60} />",
        "hard-coded '25 lớp'": "<span>25 lớp</span>",
    }

    def test_each_rule_fires(self):
        self.assertEqual(set(self.SAMPLES), {r for r, _ in GUARD_RULES})
        for rule, text in self.SAMPLES.items():
            with self.subTest(rule):
                self.assertIn(rule, [v[2] for v in guard_violations(text)])

    def test_wss_and_double_quote_variants(self):
        self.assertTrue(guard_violations('const u = "wss://x/ws";'))
        self.assertTrue(guard_violations('fetch("/api/fingerspelling")'))
        self.assertTrue(guard_violations("fetch(`/api/fingerspelling`)"))

    def test_allowed_code(self):
        ok = "\n".join([
            "const url = wsUrl(window.location, '/ws/live-stream');",
            "fetch('/api/fingerspelling/sequence', {method: 'POST'});",
            "fetch('/api/fingerspelling/compose');",
            "fetch('/api/fingerspelling/status');",
            "const s = `${scheme}://${location.host}${p}`;",
            "<PredictionDisplay bufferCapacity={state.bufferCapacity} />",
        ])
        self.assertEqual(guard_violations(ok), [])


class TestFrontendSourceGuard(unittest.TestCase):
    """AC8 on the real tree frontend/src/**/*.{js,jsx}."""

    def test_no_violation(self):
        files = frontend_source_files()
        self.assertTrue(files, "no frontend source file found")
        found = []
        for path in files:
            with open(path, encoding="utf-8") as f:
                found += guard_violations(f.read(), os.path.relpath(path, PROJECT_ROOT).replace("\\", "/"))
        self.assertEqual(found, [], "\n" + "\n".join(f"{n}:{no}: {rule}" for n, no, rule in found))


class TestHandLiveCheckReport(unittest.TestCase):
    """AC6: no landmark array in the report; provenance present."""

    BANNED = {"landmarks", "raw_landmarks", "coords"}

    def _keys(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from self._keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from self._keys(v)

    def test_reports(self):
        paths = sorted(glob.glob(os.path.join(PROJECT_ROOT, "reports", "fingerspell_live_*", "hand_live_check.json")))
        self.assertTrue(paths, "no reports/fingerspell_live_*/hand_live_check.json")
        for path in paths:
            with open(path, encoding="utf-8") as f:
                rep = json.load(f)
            with self.subTest(os.path.relpath(path, PROJECT_ROOT)):
                self.assertEqual(set(self._keys(rep)) & self.BANNED, set())
                g = rep["generated_by"]
                self.assertTrue(g["command"].startswith("PYTHONIOENCODING=utf-8 .venv/Scripts/python "
                                                        "scripts/hand_live_check.py"))
                self.assertRegex(g["git_commit"], r"^[0-9a-f]{40}$")
                self.assertIs(g["code_dirty"], False)
                self.assertIn("not accuracy", rep["note"])
                for c in rep["clips"]:
                    self.assertTrue(set(c) >= {"sample_id", "source", "n_frames", "live_png_vs_local_offline",
                                                "live_jpeg90_vs_live_png", "kaggle_npz_vs_local_offline",
                                                "sequence_top1"}, sorted(c))
                self.assertNotRegex(json.dumps(rep), r"[A-Za-z]:\\\\|/Users/|\\\\Users\\\\")


API_DOC = os.path.join(PROJECT_ROOT, "docs", "phase12_api.md")
AC6_JSON_REL = "reports/fingerspell_live_2026-09-29/hand_live_check.json"
AC6_HEADING = "### Lệch nguồn landmark Cấp 1 đo được (AC6)"


def _read_rel(rel):
    with open(os.path.join(PROJECT_ROOT, rel), encoding="utf-8") as f:
        return f.read()


def emitted_error_codes():
    """Error codes emitted by backend/main.py (_ws_error("...") / WsError("...")), extracted from the code."""
    return set(re.findall(r'(?:_ws_error|WsError)\(\s*"([a-z_]+)"', _read_rel("backend/main.py")))


def discard_reasons():
    """sign_discarded reasons: every literal passed to _discard(...) in sign_segmenter.py and every literal
    "reason": "..." of a sign_discarded built in harmonized_live.py / backend/main.py."""
    reasons = set()
    for call in re.findall(r"_discard\(([^)]*)\)", _read_rel("src/inference/sign_segmenter.py")):
        reasons |= set(re.findall(r'"([a-z_]+)"', call))
    for rel in ("src/inference/harmonized_live.py", "backend/main.py"):
        reasons |= set(re.findall(r'"reason":\s*"([a-z_]+)"', _read_rel(rel)))
    return reasons


def _section(text, heading):
    start = text.index(heading)
    nxt = re.search(r"^#{1,3} ", text[start + len(heading):], flags=re.M)
    return text[start: start + len(heading) + (nxt.start() if nxt else len(text))]


class TestPhase12ApiDoc(unittest.TestCase):
    """AC11: docs/phase12_api.md covers what the code emits (codes/reasons extracted from the code, not typed)."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _read_rel("docs/phase12_api.md")

    def test_no_stale_bind_or_url(self):
        self.assertNotIn("0.0.0.0", self.doc)
        self.assertNotIn("ws://localhost:8000", self.doc)

    def test_every_error_code(self):
        codes = emitted_error_codes()
        self.assertGreaterEqual(len(codes), 9, codes)
        for code in sorted(codes):
            with self.subTest(code):
                self.assertIn(f"`{code}`", self.doc)

    def test_every_discard_reason(self):
        reasons = discard_reasons()
        self.assertGreaterEqual(len(reasons), 6, reasons)
        for reason in sorted(reasons):
            with self.subTest(reason):
                self.assertIn(f"`{reason}`", self.doc)

    def test_message_types_and_terms(self):
        for term in ("session_info", "frame_result", "sign_result", "sign_discarded", "error", "reset_done",
                     "hand_frame", "VSL_CORS_ORIGINS", "1008", "1009", "1011", "dropped_frames",
                     "trigger_client_timestamp", "/ws/hand-landmarks"):
            with self.subTest(term):
                self.assertIn(term, self.doc)

    def test_limits_section(self):
        lim = _section(self.doc, "## 7. Giới hạn")
        for term in ("W03251B", "segmenter", "JPEG", "Origin", "không phải trình duyệt"):
            with self.subTest(term):
                self.assertIn(term, lim)

    def test_ac6_paragraph_numbers_come_from_the_json(self):
        with open(os.path.join(PROJECT_ROOT, AC6_JSON_REL), encoding="utf-8") as f:
            rep = json.load(f)
        para = _section(self.doc, AC6_HEADING)
        self.assertIn(AC6_JSON_REL, para)
        self.assertIn(rep["generated_by"]["git_commit"], para)
        self.assertIn("không chứng minh bền vững", para)
        floats = set()

        def walk(o):
            if isinstance(o, float):
                floats.add(o)
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(rep)
        decimals = re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", para)
        self.assertTrue(decimals, "no decimal number in the AC6 paragraph")
        for d in decimals:
            with self.subTest(d):
                self.assertIn(float(d), floats)
        # the maxima quoted are the maxima of the JSON
        clips = rep["clips"]
        self.assertIn(repr(max(c["kaggle_npz_vs_local_offline"]["max_abs_diff_both"] for c in clips)), para)
        self.assertIn(repr(max(c["live_jpeg90_vs_live_png"]["max_abs_diff_both"] for c in clips)), para)


_NODE = shutil.which("node")


@unittest.skipUnless(_NODE, "node not found on PATH (needed for the cross-language check)")
class TestCrossLanguageBody(unittest.TestCase):
    """AC7-d."""

    @classmethod
    def setUpClass(cls):
        import hand_live_check as H
        missing = [p for p in (H.MANIFEST, H.DEPLOYED_CKPT, H.PROVENANCE_JSON) if not os.path.exists(p)]
        if missing:
            raise unittest.SkipTest("missing (gitignored data / checkpoint; clean clone): "
                                    + ", ".join(os.path.relpath(p, PROJECT_ROOT) for p in missing))
        from fastapi.testclient import TestClient
        import backend.main as api

        cls.H, cls.api = H, api
        cls.row = H.select_clips(H.read_manifest(), 8, 0)[0]
        cls._saved = (api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta)
        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = H.DEPLOYED_CKPT, None, None
        cls.client = TestClient(api.app)
        cls.tmp = tempfile.mkdtemp(prefix="vslt_ac7d_")
        frames, fps = H.read_video(H.video_path_for(cls.row))
        cls.hand_frames = H.live_hand_frames(cls.client, frames, fps, "png")
        cls.offline = H.offline_extract(cls.row, cls.tmp)

    @classmethod
    def tearDownClass(cls):
        cls.api.ALPHABET_CKPT = cls._saved[0]
        cls.api._alphabet_model, cls.api._alphabet_meta = None, None
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_js_body_equals_python_offline_body(self):
        H = self.H
        self.assertEqual(H.sha256_of(H.DEPLOYED_CKPT), H.deployed_sha256())
        in_path, out_path = os.path.join(self.tmp, "in.json"), os.path.join(self.tmp, "out.json")
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump({"hand_frames": self.hand_frames, "segment_id": self.hand_frames[-1]["segment_id"],
                       "max_frames": self.api.ALPHABET_MAX_FRAMES, "top_k": H.TOP_K}, f)
        run = subprocess.run([_NODE, BUILD_BODY_CLI, in_path, out_path], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        with open(out_path, encoding="utf-8") as f:
            body_js = json.load(f)
        meta = self.offline["metadata"]
        body_py = H.body_from_npz(self.offline, meta["width"], meta["height"], meta["fps"])
        print(f"\n[AC7-d] {self.row['sample_id']}: frames={len(body_js['landmarks'])} "
              f"with_hand={sum(f is not None for f in body_js['landmarks'])}")
        self.assertEqual(body_js, body_py)
        r = self.client.post(H.SEQ_PATH, json=body_js)
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertEqual(r.json(), self.client.post(H.SEQ_PATH, json=body_py).json())


if __name__ == "__main__":
    unittest.main()
