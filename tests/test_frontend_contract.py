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


# ---------------------------------------------------------------------------------------------------------------
# AC12-t (plan 06, revision 2, 0B.1 / 0B.2): socket classification rules of scripts/e2e_fullstack.py.
# The module is loaded from its path; no browser, no server. Inputs have the shape e2e_browser.cjs records.
E2E_FULLSTACK = os.path.join(PROJECT_ROOT, "scripts", "e2e_fullstack.py")
HMR_URL = "ws://localhost:3000/?token=AAsU3M2Axbsn"
LIVE_URL = "ws://localhost:3000/ws/live-stream"
HAND_URL = "ws://localhost:3000/ws/hand-landmarks"


def _load_e2e_fullstack():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_plan06_e2e_fullstack", E2E_FULLSTACK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sock(url, protocol=None, count_by_type=None, closed=False, n_messages=None, first_type=None):
    cbt = dict(count_by_type or {})
    if n_messages is None:
        n_messages = sum(cbt.values())
    if first_type is None and cbt:
        first_type = next(iter(cbt))
    return {"url": url, "protocol": protocol, "count_by_type": cbt, "n_messages": n_messages, "closed": closed,
            "first_type": first_type}


def _hmr(url=HMR_URL, protocol="vite-hmr", count_by_type=None):
    return _sock(url, protocol, {"connected": 1} if count_by_type is None else count_by_type)


def _used(url=LIVE_URL):
    return _sock(url, None, {"session_info": 1, "frame_result": 40})


def _orphan(url=LIVE_URL, closed=True):
    return _sock(url, None, {}, closed=closed, n_messages=0)


class TestE2eSocketRules(unittest.TestCase):
    """AC12-t: Vite HMR socket definition (0B.1) and React.StrictMode orphan rule (0B.2)."""

    URL_CHECKS = ("ws_no_8000_any_socket", "ws_app_urls_via_proxy", "vite_hmr_socket_rule")

    @classmethod
    def setUpClass(cls):
        cls.E = _load_e2e_fullstack()

    def _checks(self, sockets):
        res = self.E.classify_ws(sockets)
        self.assertEqual(set(res["checks"]), set(self.URL_CHECKS))
        return res, {k: v["pass"] for k, v in res["checks"].items()}

    # case 1
    def test_hmr_socket_excluded_and_all_url_checks_pass(self):
        res, ok = self._checks([_hmr(), _used()])
        self.assertEqual(ok, {k: True for k in self.URL_CHECKS})
        self.assertEqual(res["hmr_excluded"],
                         [{"url": HMR_URL, "protocol": "vite-hmr", "count_by_type": {"connected": 1}}])
        self.assertEqual([w["url"] for w in res["app"]], [LIVE_URL])

    # case 2
    def test_same_url_without_protocol_is_not_hmr(self):
        res, ok = self._checks([_hmr(protocol=None), _used()])
        self.assertEqual(res["hmr_excluded"], [])
        self.assertFalse(ok["ws_app_urls_via_proxy"])

    def test_other_protocol_is_not_hmr(self):
        res, ok = self._checks([_hmr(protocol="vite-hmr2"), _used()])
        self.assertEqual(res["hmr_excluded"], [])
        self.assertFalse(ok["ws_app_urls_via_proxy"])

    # case 3
    def test_vite_hmr_protocol_with_other_url_is_red(self):
        for url in ("ws://localhost:3000/?token=x&a=1", "ws://localhost:3000/foo?token=x", "ws://127.0.0.1:3000/?token=x",
                    "ws://localhost:3000/?token=", "ws://localhost:3000/?token=x\n", "wss://localhost:3000/?token=x",
                    "ws://localhost:3000/?token=x#f", "ws://localhost:3001/?token=x"):
            with self.subTest(url=url):
                res, ok = self._checks([_hmr(url=url), _used()])
                self.assertEqual(res["hmr_excluded"], [])
                self.assertFalse(ok["vite_hmr_socket_rule"])
                self.assertFalse(all(ok.values()))

    # case 4
    def test_port_8000_is_red_for_every_socket(self):
        res, ok = self._checks([_hmr(url="ws://localhost:8000/?token=x"), _used()])
        self.assertFalse(ok["ws_no_8000_any_socket"])
        res, ok = self._checks([_hmr(), _sock("ws://localhost:8000/ws/live-stream", None, {"session_info": 1})])
        self.assertFalse(ok["ws_no_8000_any_socket"])
        res, ok = self._checks([_hmr(), _used(), _orphan(url="ws://127.0.0.1:8000/ws/live-stream")])
        self.assertFalse(ok["ws_no_8000_any_socket"])

    # case 5
    def test_hmr_socket_with_other_message_type_is_red(self):
        for cbt in ({"connected": 1, "full-reload": 1}, {"update": 1}, {"connected": 1, "error": 1}):
            with self.subTest(count_by_type=cbt):
                res, ok = self._checks([_hmr(count_by_type=cbt), _used()])
                self.assertEqual(res["hmr_excluded"], [])
                self.assertFalse(ok["vite_hmr_socket_rule"])
        # a non-JSON message is not a JSON message with type "connected"
        res, ok = self._checks([_sock(HMR_URL, "vite-hmr", {"connected": 1}, n_messages=2), _used()])
        self.assertEqual(res["hmr_excluded"], [])
        self.assertFalse(ok["vite_hmr_socket_rule"])

    # case 6
    def test_two_hmr_sockets_are_red(self):
        res, ok = self._checks([_hmr(), _hmr(url="ws://localhost:3000/?token=bbbbbbbbbbbb"), _used()])
        self.assertFalse(ok["vite_hmr_socket_rule"])

    # case 7
    def test_only_hmr_socket_is_red(self):
        res, ok = self._checks([_hmr()])
        self.assertFalse(ok["ws_app_urls_via_proxy"])
        res, ok = self._checks([])
        self.assertFalse(ok["ws_app_urls_via_proxy"])

    # case 8
    def test_app_socket_outside_ws_prefix_is_red(self):
        res, ok = self._checks([_hmr(), _used(), _sock("ws://localhost:3000/api/x", None, {})])
        self.assertFalse(ok["ws_app_urls_via_proxy"])
        res, ok = self._checks([_hmr(), _sock("ws://127.0.0.1:3000/ws/live-stream", None, {"session_info": 1})])
        self.assertFalse(ok["ws_app_urls_via_proxy"])

    # case 9 — StrictMode orphans of one path
    def test_orphan_then_used_socket_is_green(self):
        res = self.E.strictmode_orphans([_orphan(), _used()])
        self.assertTrue(res["pass"], res)
        self.assertEqual(res["orphans"], [0])
        self.assertEqual([w["first_type"] for w in res["checked"]], ["session_info"])

    def test_single_used_socket_is_green(self):
        res = self.E.strictmode_orphans([_used(HAND_URL)])
        self.assertTrue(res["pass"], res)
        self.assertEqual(res["orphans"], [])

    def test_two_orphans_on_one_path_are_red(self):
        self.assertFalse(self.E.strictmode_orphans([_orphan(), _orphan(), _used()])["pass"])

    def test_zero_message_last_or_only_socket_is_red(self):
        self.assertFalse(self.E.strictmode_orphans([_orphan()])["pass"])
        self.assertFalse(self.E.strictmode_orphans([_used(), _orphan()])["pass"])
        self.assertFalse(self.E.strictmode_orphans([_orphan(), _orphan()])["pass"])

    def test_zero_message_socket_not_closed_is_red(self):
        self.assertFalse(self.E.strictmode_orphans([_orphan(closed=False), _used()])["pass"])

    def test_empty_path_is_red(self):
        self.assertFalse(self.E.strictmode_orphans([])["pass"])

    def test_socket_with_messages_is_never_an_orphan(self):
        # an earlier socket that received messages stays subject to the session_info check
        early = _sock(LIVE_URL, None, {"error": 1}, closed=True)
        res = self.E.strictmode_orphans([early, _used()])
        self.assertEqual(res["orphans"], [])
        self.assertEqual(len(res["checked"]), 2)
        self.assertEqual(res["checked"][0]["first_type"], "error")


# ---------------------------------------------------------------------------------------------------------------
# AC12-t item 10 (plan 06, revision 3, 0C.2): role of each app path fixed by the scenario + tab_unmounted_socket_rule.
# Inputs have the shape e2e_browser.cjs records (revision 3 adds created_t_s / closed_t_s per socket and click_t_s on
# the tab_alphabet step). Common marks of the fingerspell cases: tab clicked at T, record clicked at R, R > T.
T_CLICK = 2.0
R_RECORD = 5.0
OTHER_URL = "ws://localhost:3000/ws/other"
ALL_CHECKS = ("ws_no_8000_any_socket", "ws_app_urls_via_proxy", "vite_hmr_socket_rule", "strictmode_orphan_rule",
              "tab_unmounted_socket_rule")


def _ws(url, protocol=None, count_by_type=None, closed=True, created_t_s=1.0, closed_t_s=2.5, handshake_status=None,
        n_non_json=0, session_info=None, first_type=None, n_messages=None):
    cbt = dict(count_by_type or {})
    if n_messages is None:
        n_messages = sum(cbt.values()) + n_non_json
    if first_type is None and cbt:
        first_type = next(iter(cbt))
    if session_info is None and "session_info" in cbt:
        session_info = {"type": "session_info", "protocol_version": 2}
    return {"url": url, "protocol": protocol, "handshake_status": handshake_status, "closed": closed,
            "created_t_s": created_t_s, "closed_t_s": closed_t_s if closed else None, "n_messages": n_messages,
            "n_non_json": n_non_json, "first_type": first_type, "count_by_type": cbt, "session_info": session_info,
            "errors": [{"code": "x", "detail": ""}] * cbt.get("error", 0)}


def _hmr_ws():
    return _ws(HMR_URL, "vite-hmr", {"connected": 1}, closed=False, created_t_s=0.9, handshake_status=101)


def _fs_steps(tab=True, clicked=True, record=True):
    steps = [{"t_s": 0.8, "name": "goto"}]
    if tab:
        steps.append({"t_s": T_CLICK + 0.05, "name": "tab_alphabet", "clicked": clicked, "click_t_s": T_CLICK})
    steps.append({"t_s": 4.0, "name": "ready", "available": "true", "ws": "connected"})
    if record:
        steps.append({"t_s": R_RECORD, "name": "record_clicked"})
    steps += [{"t_s": 8.3, "name": "recording", "started": True}, {"t_s": 11.5, "name": "stop_clicked"},
              {"t_s": 12.0, "name": "done"}]
    return steps


def _word_steps():
    return [{"t_s": 0.8, "name": "goto"}, {"t_s": 2.3, "name": "ready", "connection": "connected"},
            {"t_s": 2.6, "name": "camera_started", "harmonized": False},
            {"t_s": 6.5, "name": "camera_stopped", "ran_s": 3.8, "loops": 1.01}, {"t_s": 9.0, "name": "done"}]


def _live_tab(i, **kw):
    """Socket i (0 or 1) of the StrictMode pair of the default tab: 0 messages, handshake not finished, created before T
    and closed in (T, R] (the shape of the 10a case)."""
    base = {"created_t_s": 1.0 + 0.1 * i, "closed_t_s": T_CLICK + 0.2 + 0.1 * i}
    base.update(kw)
    url = base.pop("url", LIVE_URL)
    return _ws(url, **base)


def _hand_orphan():
    return _ws(HAND_URL, None, {}, closed=True, created_t_s=T_CLICK + 0.3, closed_t_s=T_CLICK + 0.31)


def _hand_used():
    return _ws(HAND_URL, None, {"session_info": 1, "reset_done": 1, "hand_frame": 76}, closed=False,
               created_t_s=T_CLICK + 0.31, handshake_status=101)


def _case_10a():
    return [_hmr_ws(), _live_tab(0), _live_tab(1), _hand_orphan(), _hand_used()]


class TestE2eScenarioRoles(unittest.TestCase):
    """AC12-t item 10: role of each app path (fixed per scenario, 0C.2), strictmode_orphan_rule on the `used` path only,
    and tab_unmounted_socket_rule on every other path."""

    @classmethod
    def setUpClass(cls):
        cls.E = _load_e2e_fullstack()

    def _run(self, scenario, sockets, steps):
        cls_ = self.E.classify_ws(sockets)
        roles = self.E.scenario_ws_roles(self.E.app_ws_by_path(sockets), scenario, steps)
        self.assertEqual(set(roles["checks"]), {"strictmode_orphan_rule", "tab_unmounted_socket_rule"})
        ok = {k: v["pass"] for k, v in {**cls_["checks"], **roles["checks"]}.items()}
        self.assertEqual(set(ok), set(ALL_CHECKS))
        return roles, ok

    def _assert_only_red(self, ok, *red):
        self.assertEqual(ok, {k: (k not in red) for k in ALL_CHECKS})

    # --- the table of 0C.2 is a constant of the script, not inferred from the observations
    def test_role_table_is_the_constant_of_0C2(self):
        self.assertEqual(self.E.SCENARIO_WS_ROLES["fingerspell"]["used"], "/ws/hand-landmarks")
        self.assertEqual(self.E.SCENARIO_WS_ROLES["fingerspell"]["tab_unmounted"], "/ws/live-stream")
        self.assertEqual(self.E.SCENARIO_WS_ROLES["word"]["used"], "/ws/live-stream")
        self.assertIsNone(self.E.SCENARIO_WS_ROLES["word"]["tab_unmounted"])
        self.assertEqual(set(self.E.SCENARIO_WS_ROLES), {"fingerspell", "word"})
        with self.assertRaises(ValueError):
            self.E.scenario_ws_roles({}, "sentence", [])

    # --- 10a / 10b / 10c (positive)
    def test_10a_trial_shape_is_green(self):
        roles, ok = self._run("fingerspell", _case_10a(), _fs_steps())
        self._assert_only_red(ok)
        self.assertEqual(roles["role_by_path"], {"/ws/hand-landmarks": "used", "/ws/live-stream": "tab_unmounted"})
        self.assertEqual(roles["tab_unmounted_by_path"], {"/ws/live-stream": 2})

    def test_10a_first_socket_closed_before_the_click_is_green(self):
        # real StrictMode order: socket 0 is closed by the StrictMode unmount, before the tab click
        s = _case_10a()
        s[1] = _live_tab(0, closed_t_s=1.05)
        roles, ok = self._run("fingerspell", s, _fs_steps())
        self._assert_only_red(ok)

    def test_10b_one_valid_session_info_is_green(self):
        s = _case_10a()
        s[2] = _live_tab(1, count_by_type={"session_info": 1}, first_type="session_info", handshake_status=101)
        self.assertEqual(s[2]["session_info"]["protocol_version"], 2)
        roles, ok = self._run("fingerspell", s, _fs_steps())
        self._assert_only_red(ok)

    def test_10c_no_live_stream_socket_is_green(self):
        roles, ok = self._run("fingerspell", [_hmr_ws(), _hand_orphan(), _hand_used()], _fs_steps())
        self._assert_only_red(ok)
        self.assertEqual(roles["role_by_path"]["/ws/hand-landmarks"], "used")
        self.assertEqual(roles["tab_unmounted_by_path"], {"/ws/live-stream": 0})

    # --- negative: tab_unmounted_socket_rule red, one factor changed from 10a
    def _tab_red(self, sockets, steps=None, scenario="fingerspell"):
        roles, ok = self._run(scenario, sockets, _fs_steps() if steps is None else steps)
        self._assert_only_red(ok, "tab_unmounted_socket_rule")
        return roles

    def test_three_live_stream_sockets_are_red(self):
        s = _case_10a()
        s.insert(3, _live_tab(1, created_t_s=1.2, closed_t_s=T_CLICK + 0.4))
        self._tab_red(s)

    def test_live_socket_not_closed_is_red(self):
        s = _case_10a()
        s[2] = dict(s[2], closed=False)
        self._tab_red(s)

    def test_live_socket_closed_t_s_null_is_red(self):
        s = _case_10a()
        s[2] = dict(s[2], closed_t_s=None)
        self._tab_red(s)

    def test_live_socket_closed_after_record_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, closed_t_s=R_RECORD + 0.001)
        self._tab_red(s)

    def test_live_socket_closed_at_record_is_green(self):
        s = _case_10a()
        s[2] = _live_tab(1, closed_t_s=R_RECORD)
        roles, ok = self._run("fingerspell", s, _fs_steps())
        self._assert_only_red(ok)

    def test_live_socket_created_at_or_after_click_is_red(self):
        for created in (T_CLICK, T_CLICK + 0.001, T_CLICK + 1.0):
            with self.subTest(created_t_s=created):
                s = _case_10a()
                s[2] = _live_tab(1, created_t_s=created)
                self._tab_red(s)

    def test_live_socket_created_t_s_missing_is_red(self):
        s = _case_10a()
        s[2] = dict(s[2], created_t_s=None)
        self._tab_red(s)

    def test_missing_tab_alphabet_step_is_red(self):
        self._tab_red(_case_10a(), _fs_steps(tab=False))

    def test_tab_not_clicked_is_red(self):
        self._tab_red(_case_10a(), _fs_steps(clicked=False))

    def test_missing_record_clicked_step_is_red(self):
        self._tab_red(_case_10a(), _fs_steps(record=False))

    def test_live_socket_messages_other_than_one_session_info_are_red(self):
        # from 10b (handshake 101, messages received): only the messages change
        for cbt in ({"error": 1}, {"session_info": 1, "frame_result": 1}, {"session_info": 2}, {"frame_result": 1}):
            with self.subTest(count_by_type=cbt):
                s = _case_10a()
                s[2] = _live_tab(1, count_by_type=cbt, handshake_status=101)
                self._tab_red(s)

    def test_live_socket_non_json_message_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, n_non_json=1)
        self.assertEqual(s[2]["n_messages"], 1)
        self._tab_red(s)

    def test_live_socket_session_info_protocol_3_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, count_by_type={"session_info": 1}, handshake_status=101,
                         session_info={"type": "session_info", "protocol_version": 3})
        self._tab_red(s)

    def test_live_socket_session_info_not_first_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, count_by_type={"session_info": 1}, handshake_status=101, first_type="error")
        self._tab_red(s)

    def test_live_socket_handshake_403_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, handshake_status=403)
        self._tab_red(s)

    def test_unknown_app_path_in_fingerspell_is_red(self):
        s = _case_10a() + [_ws(OTHER_URL, None, {}, created_t_s=1.0, closed_t_s=T_CLICK + 0.2)]
        roles = self._tab_red(s)
        self.assertEqual(roles["role_by_path"]["/ws/other"], "other")

    def test_word_with_hand_landmarks_socket_is_red(self):
        s = [_hmr_ws(), _ws(LIVE_URL, None, {}, created_t_s=1.0, closed_t_s=1.05),
             _ws(LIVE_URL, None, {"session_info": 1, "frame_result": 44}, closed=False, created_t_s=1.05,
                 handshake_status=101),
             _ws(HAND_URL, None, {}, created_t_s=1.0, closed_t_s=T_CLICK + 0.2)]
        roles = self._tab_red(s, _word_steps(), scenario="word")
        self.assertEqual(roles["role_by_path"], {"/ws/live-stream": "used", "/ws/hand-landmarks": "other"})

    # --- negative: strictmode_orphan_rule red (the old rule is not swallowed by the new one)
    def test_word_used_path_without_socket_receiving_messages_is_red(self):
        s = [_hmr_ws(), _live_tab(0), _live_tab(1)]
        roles, ok = self._run("word", s, _word_steps())
        self._assert_only_red(ok, "strictmode_orphan_rule")

    def test_fingerspell_hand_path_with_two_zero_message_sockets_is_red(self):
        s = [_hmr_ws(), _live_tab(0), _live_tab(1), _hand_orphan(),
             _ws(HAND_URL, None, {}, created_t_s=T_CLICK + 0.31, closed_t_s=T_CLICK + 0.5)]
        roles, ok = self._run("fingerspell", s, _fs_steps())
        self._assert_only_red(ok, "strictmode_orphan_rule")

    def test_fingerspell_used_path_absent_is_red(self):
        roles, ok = self._run("fingerspell", [_hmr_ws(), _live_tab(0), _live_tab(1)], _fs_steps())
        self._assert_only_red(ok, "strictmode_orphan_rule")
        self.assertEqual(roles["role_by_path"], {"/ws/hand-landmarks": "used", "/ws/live-stream": "tab_unmounted"})

    # --- negative: the URL checks still apply to the tab_unmounted path
    def test_port_8000_on_tab_unmounted_path_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, url="ws://localhost:8000/ws/live-stream")
        roles, ok = self._run("fingerspell", s, _fs_steps())
        # a :8000 socket is not the HMR socket and does not start with ws://localhost:3000/ws/, so by the unchanged
        # definitions of 0B.1 ws_app_urls_via_proxy is red as well; the two path rules stay green
        self._assert_only_red(ok, "ws_no_8000_any_socket", "ws_app_urls_via_proxy")

    def test_127_0_0_1_on_tab_unmounted_path_is_red(self):
        s = _case_10a()
        s[2] = _live_tab(1, url="ws://127.0.0.1:3000/ws/live-stream")
        roles, ok = self._run("fingerspell", s, _fs_steps())
        self._assert_only_red(ok, "ws_app_urls_via_proxy")

    # --- the two word scenarios in the trial shape
    def test_word_trial_shapes_are_green(self):
        for used_cbt in ({"session_info": 1, "frame_result": 44},
                         {"session_info": 1, "frame_result": 72, "sign_result": 1}):
            with self.subTest(count_by_type=used_cbt):
                s = [_hmr_ws(), _ws(LIVE_URL, None, {}, created_t_s=1.0, closed_t_s=1.05),
                     _ws(LIVE_URL, None, used_cbt, closed=False, created_t_s=1.05, handshake_status=101)]
                roles, ok = self._run("word", s, _word_steps())
                self._assert_only_red(ok)
                self.assertEqual(roles["role_by_path"], {"/ws/live-stream": "used"})
                self.assertEqual(roles["tab_unmounted_by_path"], {})

    # --- wiring: evaluate() puts both checks in `checks`, ws_classification() writes role_by_path
    def _obs(self, sockets, steps, scenario):
        return {"scenario": scenario, "steps": steps, "ws": sockets, "console_errors": [], "page_errors": [],
                "request_failed": [], "http_errors": [], "requests_old_image_endpoint": [], "fatal_error": None,
                "fingerspelling_status": None, "sequence_posts": [], "compose_posts": [], "dom": {}}

    def _evaluate(self, scenario, sockets, steps):
        import types
        args = types.SimpleNamespace(scenario=scenario, model_type=None, max_loops=3)
        ready = {"health_status": 200, "health": {"status": "ok"}, "health_wait_s": 1.0, "page_status": 200,
                 "page_wait_s": 1.0}
        stop = {"ports_listening_after_stop": {"8000": False, "3000": False}, "processes_alive_after_stop": []}
        return self.E.evaluate(args, self._obs(sockets, steps, scenario), ready, stop, {})

    def test_evaluate_uses_the_role_rules(self):
        checks = self._evaluate("fingerspell", _case_10a(), _fs_steps())
        self.assertTrue(checks["strictmode_orphan_rule"]["pass"], checks["strictmode_orphan_rule"])
        self.assertTrue(checks["tab_unmounted_socket_rule"]["pass"], checks["tab_unmounted_socket_rule"])
        checks = self._evaluate("fingerspell", _case_10a(), _fs_steps(record=False))
        self.assertFalse(checks["tab_unmounted_socket_rule"]["pass"])
        s = [_hmr_ws(), _ws(LIVE_URL, None, {}, created_t_s=1.0, closed_t_s=1.05),
             _ws(LIVE_URL, None, {"session_info": 1, "frame_result": 44}, closed=False, created_t_s=1.05,
                 handshake_status=101)]
        checks = self._evaluate("word", s, _word_steps())
        self.assertTrue(checks["strictmode_orphan_rule"]["pass"])
        self.assertTrue(checks["tab_unmounted_socket_rule"]["pass"])
        checks = self._evaluate("word", s + [_ws(HAND_URL, None, {})], _word_steps())
        self.assertFalse(checks["tab_unmounted_socket_rule"]["pass"])

    def test_ws_classification_has_roles(self):
        wc = self.E.ws_classification(self._obs(_case_10a(), _fs_steps(), "fingerspell"), "fingerspell")
        self.assertEqual(wc["role_by_path"], {"/ws/hand-landmarks": "used", "/ws/live-stream": "tab_unmounted"})
        self.assertEqual(wc["tab_unmounted_by_path"], {"/ws/live-stream": 2})
        self.assertEqual(wc["strictmode_orphans_by_path"], {"/ws/hand-landmarks": 1})
        self.assertEqual(len(wc["vite_hmr_excluded"]), 1)


if __name__ == "__main__":
    unittest.main()
