"""
Plan 05 AC6 (f2, f4): a Level 2 checkpoint whose preprocessing cannot be served by any live path (unknown
`features`, other `mediapipe_version`) makes /api/health, /model/info and /api/classes answer 503 model_unavailable
and the WebSocket send error{model_unavailable} + close 1011; nothing is cached (every request loads again).
/api/classes also answers 503 (not 500) for any other load failure, and keeps {total, classes} on success.

No real checkpoint is loaded: VSLPredictor is a MagicMock returning tests.test_harmonized_live.FakePredictor.
"""
import os
import sys
import unittest
from unittest import mock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from tests.test_harmonized_live import PRE, FakePredictor  # noqa: E402

WS = "/ws/live-stream"


def predictor_with(preprocessing):
    p = FakePredictor()
    p.preprocessing = dict(preprocessing)
    return p


class _Case(unittest.TestCase):
    def patched(self, loader):
        patches = [mock.patch.object(api, "GLOBAL_PREDICTOR", None),
                   mock.patch.object(api, "STGCN_CKPT_SHA256", None),
                   mock.patch.object(api, "VSLPredictor", loader)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return TestClient(api.app, raise_server_exceptions=False)  # no `with`: lifespan is not started

    def assert_unavailable(self, r):
        self.assertEqual(r.status_code, 503, r.text)
        body = r.json()
        self.assertEqual(body["status"], "model_unavailable")
        self.assertLessEqual(len(body["detail"]), 200)


class TestUnservablePreprocessing(_Case):
    """AC6 a–e, for each of the two unservable preprocessing variants."""

    VARIANTS = {"features_unknown": {**PRE, "features": "harmonized_v9"},
                "mediapipe_mismatch": {**PRE, "mediapipe_version": "0.0.0-test"}}

    def _run(self, name):
        loader = mock.MagicMock(side_effect=lambda *a, **kw: predictor_with(self.VARIANTS[name]))
        client = self.patched(loader)
        self.assert_unavailable(client.get("/api/health"))                       # a
        self.assertEqual(client.get("/model/info").status_code, 503)             # b
        self.assert_unavailable(client.get("/api/classes"))                      # c
        with client.websocket_connect(WS) as ws:                                 # d
            m = ws.receive_json()
            self.assertEqual((m["type"], m["code"]), ("error", "model_unavailable"), m)
            closing = ws.receive()
            self.assertEqual((closing["type"], closing["code"]), ("websocket.close", 1011))
        self.assertIsNone(api.GLOBAL_PREDICTOR)                                  # e
        self.assertEqual(loader.call_count, 4)

    def test_features_unknown(self):
        self._run("features_unknown")

    def test_mediapipe_version_mismatch(self):
        self._run("mediapipe_mismatch")


class TestClassesLoadError(_Case):
    """AC6 f."""

    def test_file_not_found_is_503(self):
        loader = mock.MagicMock(side_effect=FileNotFoundError("checkpoint missing (test fixture)"))
        client = self.patched(loader)
        self.assert_unavailable(client.get("/api/classes"))
        self.assertIsNone(api.GLOBAL_PREDICTOR)


class TestClassesSuccess(_Case):
    """AC6 g: harmonized and legacy ({}) preprocessing."""

    def _ok(self, preprocessing):
        predictor = predictor_with(preprocessing)
        client = self.patched(mock.MagicMock(return_value=predictor))
        r = client.get("/api/classes")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(set(body), {"total", "classes"})
        self.assertEqual(body["total"], predictor.num_classes)
        self.assertEqual(body["classes"], predictor.class_names)

    def test_harmonized(self):
        self._ok(PRE)

    def test_legacy_empty_preprocessing(self):
        self._ok({})


if __name__ == "__main__":
    unittest.main()
