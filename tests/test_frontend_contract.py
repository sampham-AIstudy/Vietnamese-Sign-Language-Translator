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
