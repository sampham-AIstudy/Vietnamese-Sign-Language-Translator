"""
Plan 06 AC3: CORS allow-list, Origin check of the WebSockets, loopback bind (decision 2026-09-28: dev origins only,
never "*" with credentials).

No model is loaded: `_active_model` is replaced by a MagicMock (it must not even be called for a rejected Origin),
and the Level 1 hand-landmark session is replaced by a MagicMock for the rejected-Origin cases (the
accepted-Origin cases of /ws/hand-landmarks use the real MediaPipe Hands session).
"""
import os
import re
import sys
import unittest
from unittest import mock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

import backend.main as api  # noqa: E402

WS_PATHS = ("/ws/live-stream", "/ws/hand-landmarks")
BAD_ORIGINS = ("http://evil.example", "null", "http://localhost:3001", "http://localhost:3000.evil.example",
               "HTTP://LOCALHOST:3000")
GOOD_ORIGIN = "http://localhost:3000"
COMPOSE = "/api/fingerspelling/compose"


def _read(rel):
    with open(os.path.join(PROJECT_ROOT, rel), encoding="utf-8") as f:
        return f.read()


class TestParseCorsOrigins(unittest.TestCase):
    """AC3-a."""

    def test_default_when_unset_or_empty(self):
        self.assertEqual(api.parse_cors_origins(None), api.DEFAULT_DEV_ORIGINS)
        self.assertEqual(api.parse_cors_origins(""), api.DEFAULT_DEV_ORIGINS)

    def test_split_and_strip(self):
        self.assertEqual(api.parse_cors_origins(" http://a:1 , https://b "), ("http://a:1", "https://b"))

    def test_rejected_values(self):
        for value in ("*", "http://a,*", "http://a,", "ftp://x", "http://a/", "null"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    api.parse_cors_origins(value)


class TestCorsMiddlewareConfig(unittest.TestCase):
    """AC3-b."""

    def test_default_dev_origins(self):
        self.assertEqual(api.DEFAULT_DEV_ORIGINS, ("http://localhost:3000", "http://127.0.0.1:3000"))

    def test_allowed_origins_from_env(self):
        self.assertEqual(api.ALLOWED_ORIGINS, api.parse_cors_origins(os.environ.get("VSL_CORS_ORIGINS")))
        if "VSL_CORS_ORIGINS" not in os.environ:
            self.assertEqual(api.ALLOWED_ORIGINS, api.DEFAULT_DEV_ORIGINS)

    def test_single_cors_middleware_without_wildcards(self):
        cors = [m for m in api.app.user_middleware if m.cls is CORSMiddleware]
        self.assertEqual(len(cors), 1)
        kw = cors[0].kwargs
        self.assertEqual(kw["allow_origins"], list(api.DEFAULT_DEV_ORIGINS))
        self.assertIs(kw["allow_credentials"], False)
        for key in ("allow_origins", "allow_methods", "allow_headers"):
            with self.subTest(key=key):
                self.assertNotIn("*", kw.get(key, []))
        self.assertNotIn("allow_origin_regex", kw)


class TestCorsHttp(unittest.TestCase):
    """AC3-c: POST /api/fingerspelling/compose needs no model."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)  # no `with`: lifespan (model preload) is not started

    def setUp(self):
        self.responses = []

    def tearDown(self):
        for r in self.responses:
            self.assertNotEqual(r.headers.get("access-control-allow-origin"), "*")

    def _post(self, origin):
        r = self.client.post(COMPOSE, json={"tokens": ["a"]}, headers={"Origin": origin})
        self.responses.append(r)
        return r

    def _preflight(self, origin):
        r = self.client.options(COMPOSE, headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        self.responses.append(r)
        return r

    def test_allowed_origin(self):
        r = self._post("http://localhost:3000")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertNotIn("access-control-allow-credentials", r.headers)

    def test_foreign_origin_has_no_acao(self):
        r = self._post("http://evil.example")
        self.assertNotIn("access-control-allow-origin", r.headers)

    def test_preflight_foreign_origin_rejected(self):
        r = self._preflight("http://evil.example")
        self.assertNotIn("access-control-allow-origin", r.headers)
        self.assertFalse(200 <= r.status_code < 300, r.status_code)

    def test_preflight_allowed_origin(self):
        r = self._preflight("http://127.0.0.1:3000")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://127.0.0.1:3000")

    def test_no_wildcard_acao_anywhere(self):
        for origin in ("http://localhost:3000", "http://evil.example", "null", "http://127.0.0.1:3000"):
            self._post(origin)
            self._preflight(origin)
        self.assertTrue(self.responses)


class TestWsOriginAllowed(unittest.TestCase):
    """AC3-f."""

    def test_values(self):
        self.assertIs(api.ws_origin_allowed(None), True)
        self.assertIs(api.ws_origin_allowed("http://localhost:3000"), True)
        self.assertIs(api.ws_origin_allowed("http://127.0.0.1:3000"), True)
        self.assertIs(api.ws_origin_allowed(""), False)
        self.assertIs(api.ws_origin_allowed("null"), False)


class _WsCase(unittest.TestCase):
    def setUp(self):
        self.active_model = mock.MagicMock(side_effect=api.ModelUnavailable("test fixture: no model"))
        patches = [mock.patch.object(api, "_active_model", self.active_model)]
        self.hand_session = mock.MagicMock()
        patches.append(mock.patch.object(api, "HandLandmarkSession", self.hand_session))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(api.app)


class TestWsOriginRejected(_WsCase):
    """AC3-d: a foreign Origin is refused BEFORE accept (close 1008 -> handshake 403); nothing is loaded."""

    def test_rejected_origins(self):
        for path in WS_PATHS:
            for origin in BAD_ORIGINS:
                with self.subTest(path=path, origin=origin):
                    with self.assertRaises(WebSocketDisconnect) as cm:
                        with self.client.websocket_connect(path, headers={"origin": origin}) as ws:
                            ws.receive_json()
                    self.assertEqual(cm.exception.code, 1008)
        self.active_model.assert_not_called()
        self.hand_session.assert_not_called()


class TestWsOriginAccepted(_WsCase):
    """AC3-e: allowed Origin, or no Origin header (non-browser client), gets through the check."""

    def _live_stream_unavailable(self, headers):
        with self.client.websocket_connect("/ws/live-stream", headers=headers) as ws:
            m = ws.receive_json()
            self.assertEqual((m["type"], m["code"]), ("error", "model_unavailable"), m)
            closing = ws.receive()
            self.assertEqual((closing["type"], closing["code"]), ("websocket.close", 1011))

    def test_live_stream_allowed_origin(self):
        self._live_stream_unavailable({"origin": GOOD_ORIGIN})
        self.assertEqual(self.active_model.call_count, 1)

    def test_live_stream_no_origin(self):
        self._live_stream_unavailable({})
        self.assertEqual(self.active_model.call_count, 1)


class TestWsOriginAcceptedHandLandmarks(unittest.TestCase):
    """AC3-e for /ws/hand-landmarks, with the real MediaPipe Hands session (no Level 2 model involved)."""

    def setUp(self):
        self.client = TestClient(api.app)

    def _session_info(self, headers):
        with self.client.websocket_connect("/ws/hand-landmarks", headers=headers) as ws:
            m = ws.receive_json()
            self.assertEqual(m["type"], "session_info", m)

    def test_allowed_origin(self):
        self._session_info({"origin": GOOD_ORIGIN})

    def test_allowed_origin_127(self):
        self._session_info({"origin": "http://127.0.0.1:3000"})

    def test_no_origin(self):
        self._session_info({})


class TestBindLoopback(unittest.TestCase):
    """AC3-g (text checks)."""

    def test_start_fullstack(self):
        text = _read("start_fullstack.ps1")
        self.assertIn("--host 127.0.0.1", text)
        self.assertNotIn("0.0.0.0", text)

    def test_backend_main(self):
        text = _read("backend/main.py")
        self.assertNotIn("0.0.0.0", text)
        calls = re.findall(r"uvicorn\.run\((.*?)\)\s*$", text, flags=re.S | re.M)
        self.assertTrue(calls, "uvicorn.run( not found")
        for call in calls:
            self.assertIn('host="127.0.0.1"', call)

    def test_vite_config(self):
        text = _read("frontend/vite.config.js")
        for block in ("server", "preview"):
            with self.subTest(block=block):
                m = re.search(block + r"\s*:\s*\{(.*?)\}", text, flags=re.S)
                self.assertIsNotNone(m, block)
                self.assertRegex(m.group(1), r"strictPort\s*:\s*true")
        self.assertNotRegex(text, r"(^|[\s{,])host\s*:")


if __name__ == "__main__":
    unittest.main()
