"""
Plan 04 AC3 + AC7: /ws/live-stream contract (protocol_version 2) with fake predictor / extractor / legacy pipeline.
No MediaPipe graph and no real checkpoint are needed. Landmark frames are fixtures generated in the test
(tests/test_sign_segmenter.py); the only pixels are blank frames and one seeded-noise JPEG (AC3-e).
"""
import base64
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest import mock

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
import src.inference.harmonized_live as hl  # noqa: E402
from src.inference.smoother import TemporalSmoother  # noqa: E402
from tests.test_harmonized_live import PRE, FakePredictor  # noqa: E402
from tests.test_sign_segmenter import REST_Y, build, sign_profile  # noqa: E402

WS = "/ws/live-stream"
SESSION_INFO_KEYS = {"type", "protocol_version", "pipeline", "model", "preprocessing", "segmenter", "limits"}
LEGACY_KEYS = {"type", "gloss", "prediction", "confidence", "top5", "latency_ms", "fps", "status", "sentence",
               "is_confirmed", "translated_text", "oov_warning", "is_signing", "hand_detected", "buffer_fill",
               "buffer_capacity", "landmarks", "metrics"}
LEGACY_METRIC_KEYS = {"client_timestamp", "server_preprocess_ms", "server_infer_ms", "server_total_ms", "server_fps",
                      "buffer_frames"}


def png_bytes(w=640, h=480):
    ok, buf = cv2.imencode(".png", np.zeros((h, w, 3), np.uint8))
    assert ok
    return buf.tobytes()


def data_url(data, mime="image/png"):
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


PNG_640 = png_bytes()
URL_640 = data_url(PNG_640)


def png_header_only(w, h):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IEND", b"")


class LoopExtractor:
    """Fixture frames in order (last frame repeated when exhausted); counts calls."""

    def __init__(self, kps, vis):
        self.kps, self.vis, self.i, self.process_height = kps, vis, 0, 360

    def _get_holistic(self):
        return self

    def extract_frame(self, rgb):
        j = min(self.i, len(self.kps) - 1)
        self.i += 1
        return self.kps[j].copy(), self.vis[j].copy()

    def close(self):
        pass


class FakeRealtimePipeline:
    """Legacy RealtimePipeline double: prediction latency 7.0 ms; is_new_prediction settable."""
    is_new = True

    def __init__(self, predictor=None, target_len=60, min_frames=15, infer_interval=2, **kw):
        self.n = 0

    def process_frame(self, frame_bgr):
        self.n += 1
        pred = {"gloss": "g0", "confidence": 0.3, "top5": [{"gloss": "g0", "confidence": 0.3}], "latency_ms": 7.0}
        return {"prediction": pred, "is_new_prediction": FakeRealtimePipeline.is_new, "results": None,
                "buffer_fill": self.n, "buffer_capacity": 60, "hand_detected": True, "is_moving": True}

    def clear_buffer(self):
        self.n = 0

    def close(self):
        pass


class RecordingSmoother(TemporalSmoother):
    instances = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        RecordingSmoother.instances.append(self)


class _FakeTranslator:
    gloss_vocab = None

    def translate_glosses(self, glosses, attach_lexicon=False):
        return {"translation": ""}


def sign_frames(dur=3.5):
    t = np.arange(int(round(dur * 30))) / 30.0
    k, v = build(t, lambda x: sign_profile(x, 1.0, 2.5))
    return t, k, v


class _WsCase(unittest.TestCase):
    pipeline_kind = "harmonized"

    def setUp(self):
        self.predictor = FakePredictor()
        if self.pipeline_kind == "legacy":
            self.predictor.preprocessing = {}
        self.t, self.k, self.v = sign_frames()
        self.extractor = LoopExtractor(self.k, self.v)
        RecordingSmoother.instances = []
        FakeRealtimePipeline.is_new = True
        patches = [
            mock.patch.object(api, "GLOBAL_PREDICTOR", self.predictor),
            mock.patch.object(api, "LOADED_CKPT_SHA256", None),
            mock.patch.object(api, "_new_harmonized_session",
                              lambda pred: hl.HarmonizedLiveSession(pred, pred.preprocessing, extractor=self.extractor)),
            mock.patch.object(api, "RealtimePipeline", FakeRealtimePipeline),
            mock.patch.object(api, "TemporalSmoother", RecordingSmoother),
            mock.patch.object(api, "get_or_load_translator", lambda: _FakeTranslator()),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(api.app)   # no `with`: the lifespan (real model load) is not started
        self.ts = 0

    def connect(self):
        ws = self.client.websocket_connect(WS)
        conn = ws.__enter__()
        self.addCleanup(lambda: ws.__exit__(None, None, None))
        info = conn.receive_json()
        self.assertEqual(info["type"], "session_info")
        return conn, info

    def next_ts(self):
        self.ts += 1
        return self.ts * 1000.0 / 30.0

    def send_frame(self, ws, image=URL_640, ts="auto", **extra):
        body = {"image": image, **extra}
        if ts == "auto":
            body["timestamp"] = self.next_ts()
        elif ts is not None:
            body["timestamp"] = ts
        ws.send_text(json.dumps(body))

    def until_frame_result(self, ws):
        """Messages up to and including the next frame_result or error."""
        out = []
        while True:
            m = ws.receive_json()
            out.append(m)
            if m["type"] in ("frame_result", "error"):
                return out

    def expect_error(self, ws, code):
        m = ws.receive_json()
        self.assertEqual((m["type"], m["code"]), ("error", code), m)
        self.assertLessEqual(len(m["detail"]), 200)
        return m

    def expect_close(self, ws, code):
        m = ws.receive()
        self.assertEqual(m["type"], "websocket.close", m)
        self.assertEqual(m["code"], code)


class TestAC3aDefaults(unittest.TestCase):
    def _consts(self, extra_env):
        env = {k: v for k, v in os.environ.items() if k not in ("VSL_MODEL_TYPE", "VSL_STGCN_CKPT")}
        env.update(extra_env)
        env["PYTHONIOENCODING"] = "utf-8"
        code = ("import json, backend.main as m; print('CONSTS=' + json.dumps({'MODEL_TYPE': m.MODEL_TYPE, "
                "'STGCN_CKPT': m.STGCN_CKPT, 'IS_DEFAULT_MODEL': m.IS_DEFAULT_MODEL, "
                "'SHA': m.STGCN_CKPT_SHA256, 'DEFAULT': m.DEFAULT_MODEL_TYPE}))")
        out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, env=env, capture_output=True,
                             text=True, encoding="utf-8", timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        line = [x for x in out.stdout.splitlines() if x.startswith("CONSTS=")][-1]
        return json.loads(line[len("CONSTS="):])

    def test_a_default_is_unchanged(self):
        c = self._consts({})
        self.assertEqual(c["MODEL_TYPE"], "stgcn")
        self.assertEqual(c["DEFAULT"], "stgcn")
        self.assertEqual(c["STGCN_CKPT"], "checkpoints/stgcn_tier2_indomain.pt")
        self.assertIs(c["IS_DEFAULT_MODEL"], True)

    def test_a_candidate_opt_in(self):
        c = self._consts({"VSL_MODEL_TYPE": "stgcn_h360"})
        self.assertTrue(c["STGCN_CKPT"].replace("\\", "/").endswith("run_keepz_360/stgcn_unified_best.pt"))
        self.assertIs(c["IS_DEFAULT_MODEL"], False)
        self.assertEqual(c["SHA"], "648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e")


class TestAC3bShaMismatch(unittest.TestCase):
    def test_b_sha_mismatch_is_unavailable(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fake_ckpt = os.path.join(tmp.name, "stgcn_unified_best.pt")
        with open(fake_ckpt, "wb") as f:
            f.write(b"not the H-keepz-360 checkpoint (test fixture)")
        loader = mock.MagicMock(side_effect=AssertionError("VSLPredictor must not be built on a sha mismatch"))
        with mock.patch.object(api, "GLOBAL_PREDICTOR", None), mock.patch.object(api, "STGCN_CKPT", fake_ckpt), \
                mock.patch.object(api, "STGCN_CKPT_SHA256", api.STGCN_VARIANTS["stgcn_h360"]["sha256"]), \
                mock.patch.object(api, "VSLPredictor", loader):
            client = TestClient(api.app)
            r = client.get("/api/health")
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.json()["status"], "model_unavailable")
            self.assertLessEqual(len(r.json()["detail"]), 200)
            self.assertEqual(client.get("/model/info").status_code, 503)
            with client.websocket_connect(WS) as ws:
                m = ws.receive_json()
                self.assertEqual((m["type"], m["code"]), ("error", "model_unavailable"))
                closing = ws.receive()
                self.assertEqual((closing["type"], closing["code"]), ("websocket.close", 1011))
            loader.assert_not_called()
            self.assertIsNone(api.GLOBAL_PREDICTOR)


class TestAC3cSessionInfo(_WsCase):
    def test_c_session_info_both_paths(self):
        for kind, expected in (("harmonized", "harmonized_v1"), ("legacy", "legacy")):
            self.predictor.preprocessing = dict(PRE) if kind == "harmonized" else {}
            ws, info = self.connect()
            with self.subTest(kind=kind):
                self.assertEqual(set(info), SESSION_INFO_KEYS)
                self.assertEqual(info["protocol_version"], 2)
                self.assertEqual(info["pipeline"], expected)
                self.assertEqual(set(info["model"]), {"model_type", "checkpoint", "checkpoint_sha256", "is_default",
                                                      "num_classes"})
                self.assertEqual(set(info["limits"]), {"max_message_bytes", "max_frame_side", "min_frame_height"})
                self.assertEqual(info["limits"]["max_message_bytes"], api.WS_MAX_MESSAGE_BYTES)
                if kind == "harmonized":
                    self.assertEqual(set(info["preprocessing"]), {"target_len", "process_height", "trim", "hand_z",
                                                                  "rest_y", "active_speed", "pad_s", "max_gap_s"})
                    self.assertEqual(info["preprocessing"]["process_height"], 360)
                    self.assertEqual(info["segmenter"], api.SEGMENTER_DEFAULT)
                    self.assertEqual(info["limits"]["min_frame_height"], 360)
                else:
                    self.assertEqual(info["preprocessing"], {"target_len": 60})
                    self.assertIsNone(info["segmenter"])
                    self.assertIsNone(info["limits"]["min_frame_height"])


class TestAC3dSignFlow(_WsCase):
    def test_d_one_sign_result_before_its_frame_result(self):
        ws, _ = self.connect()
        messages = []
        for _ in range(len(self.t)):
            self.send_frame(ws)
            messages += self.until_frame_result(ws)
        frames = [m for m in messages if m["type"] == "frame_result"]
        signs = [m for m in messages if m["type"] == "sign_result"]
        self.assertEqual(len(frames), len(self.t))
        self.assertEqual([m["type"] for m in messages if m["type"] not in ("frame_result",)], ["sign_result"])
        s = signs[0]
        self.assertEqual(len(s["top5"]), 5)
        confs = [x["confidence"] for x in s["top5"]]
        self.assertEqual(confs, sorted(confs, reverse=True))
        self.assertTrue(all(0.0 <= c <= 1.0 for c in confs))
        self.assertTrue(0.0 <= s["confidence"] <= 1.0)
        i = messages.index(s)
        self.assertEqual(messages[i + 1]["type"], "frame_result")
        self.assertEqual(messages[i + 1]["frame_seq"], s["frame_seq"])
        self.assertEqual(set(s), {"type", "segment_id", "frame_seq", "prediction", "gloss", "confidence", "top5",
                                  "end_reason", "segment", "model", "metrics"})
        self.assertEqual(set(s["segment"]), {"start_s", "end_s", "duration_s", "frames", "effective_fps",
                                             "dropped_frames", "active_start_s", "active_end_s"})
        self.assertEqual(set(s["metrics"]), {"harmonize_ms", "infer_ms", "finalize_ms", "trigger_client_timestamp",
                                             "rest_hold_s"})
        self.assertEqual(s["model"]["pipeline"], "harmonized_v1")
        self.assertEqual(s["end_reason"], "rest")
        for f in frames:
            self.assertIsNone(f["prediction"])
            self.assertEqual(f["top5"], [])
            self.assertEqual(f["status"], f["segment"]["state"].upper())
            self.assertEqual(f["is_signing"], f["segment"]["state"] == "recording")
        states = [f["segment"]["state"] for f in frames]
        compressed = [x for j, x in enumerate(states) if j == 0 or states[j - 1] != x]
        self.assertEqual(compressed, ["idle", "recording", "idle"])
        self.assertEqual([f["frame_seq"] for f in frames], list(range(1, len(frames) + 1)))
        self.assertEqual(s["metrics"]["trigger_client_timestamp"], frames[s["frame_seq"] - 1]["metrics"]["client_timestamp"])


class TestAC3eLimits(_WsCase):
    def _too_large(self, kind, binary):
        self.predictor.preprocessing = dict(PRE) if kind == "harmonized" else {}
        ws, _ = self.connect()
        n = api.WS_MAX_MESSAGE_BYTES + 1
        if binary:
            ws.send_bytes(b"\0" * n)
        else:
            prefix, suffix = '{"image": "', '"}'
            ws.send_text(prefix + "A" * (n - len(prefix) - len(suffix)) + suffix)
        self.expect_error(ws, "message_too_large")
        self.expect_close(ws, 1009)

    def test_e_over_limit_closes_1009(self):
        for kind in ("harmonized", "legacy"):
            for binary in (False, True):
                with self.subTest(kind=kind, binary=binary):
                    self._too_large(kind, binary)

    def test_e_exact_limit_accepted(self):
        for kind in ("harmonized", "legacy"):
            self.predictor.preprocessing = dict(PRE) if kind == "harmonized" else {}
            ws, _ = self.connect()
            head = json.dumps({"image": URL_640, "timestamp": self.next_ts(), "pad": ""})
            text = head[:-2] + "x" * (api.WS_MAX_MESSAGE_BYTES - len(head.encode("utf-8"))) + head[-2:]
            self.assertEqual(len(text.encode("utf-8")), api.WS_MAX_MESSAGE_BYTES)
            ws.send_text(text)
            got = self.until_frame_result(ws)
            with self.subTest(kind=kind, message="text"):
                self.assertEqual(got[-1]["type"], "frame_result", got[-1])
            ws2, _ = self.connect()                                  # binary: server-time session
            ws2.send_bytes(PNG_640 + b"\0" * (api.WS_MAX_MESSAGE_BYTES - len(PNG_640)))
            got = self.until_frame_result(ws2)
            with self.subTest(kind=kind, message="binary"):
                self.assertEqual(got[-1]["type"], "frame_result", got[-1])

    def test_e_noisy_jpeg95_fits(self):
        noise = np.random.default_rng(0).integers(0, 256, (480, 640, 3), dtype=np.uint8)   # test-only noise
        ok, buf = cv2.imencode(".jpg", noise, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self.assertTrue(ok)
        body = json.dumps({"image": data_url(buf.tobytes(), "image/jpeg"), "timestamp": self.next_ts()})
        size = len(body.encode("utf-8"))
        print(f"\n[AC3-e] 640x480 noise JPEG q95 dataURL JSON = {size} bytes (limit {api.WS_MAX_MESSAGE_BYTES})")
        self.assertLess(size, api.WS_MAX_MESSAGE_BYTES)
        for kind in ("harmonized", "legacy"):
            self.predictor.preprocessing = dict(PRE) if kind == "harmonized" else {}
            ws, _ = self.connect()
            ws.send_text(body)
            with self.subTest(kind=kind):
                self.assertEqual(self.until_frame_result(ws)[-1]["type"], "frame_result")


class TestAC3fErrors(_WsCase):
    def _cases(self):
        gif = base64.b64encode(b"GIF89a" + b"\0" * 64).decode()
        garbage = base64.b64encode(bytes(range(256))).decode()
        return [
            ("bad_message", lambda ws: ws.send_text('{"image": "abc", ')),
            ("bad_message", lambda ws: ws.send_text(json.dumps({"timestamp": self.next_ts()}))),
            ("decode_failed", lambda ws: self.send_frame(ws, "data:image/png;base64,@@@not-base64@@@")),
            ("unsupported_format", lambda ws: self.send_frame(ws, "data:image/gif;base64," + gif)),
            ("unsupported_format", lambda ws: self.send_frame(ws, garbage)),
            ("frame_too_large", lambda ws: self.send_frame(ws, data_url(png_header_only(4000, 10)))),
        ]

    def _run(self, kind):
        self.predictor.preprocessing = dict(PRE) if kind == "harmonized" else {}
        ws, _ = self.connect()
        cases = self._cases()
        if kind == "harmonized":
            cases.append(("frame_too_small", lambda ws: self.send_frame(ws, data_url(png_bytes(320, 240)))))
        for code, send in cases:
            with self.subTest(kind=kind, code=code):
                spy = mock.patch.object(api.cv2, "imdecode", wraps=cv2.imdecode)
                with spy as imdecode:
                    send(ws)
                    err = self.expect_error(ws, code)
                    if code == "frame_too_large":
                        imdecode.assert_not_called()
                self.assertNotIn("base64,", err["detail"])
                self.assertNotIn("not-base64", err["detail"])
                self.assertIsInstance(err["received_seq"], int)
                self.send_frame(ws)                              # the session still serves a valid frame
                self.assertEqual(self.until_frame_result(ws)[-1]["type"], "frame_result")

    def test_f_errors_harmonized(self):
        self._run("harmonized")

    def test_f_errors_legacy(self):
        self._run("legacy")


class TestAC3gConfig(_WsCase):
    pipeline_kind = "legacy"

    def test_g_confidence_threshold(self):
        ws, _ = self.connect()
        smoother = RecordingSmoother.instances[-1]
        before = smoother.confidence_threshold
        for bad in ("NaN", '"abc"', "2.0", "-0.1", "true"):
            ws.send_text('{"image": "%s", "timestamp": %f, "config": {"confidence_threshold": %s}}'
                         % (URL_640, self.next_ts(), bad))
            with self.subTest(value=bad):
                self.expect_error(ws, "bad_config")
                self.assertEqual(smoother.confidence_threshold, before)
        self.send_frame(ws, config={"confidence_threshold": 0.5})
        self.assertEqual(self.until_frame_result(ws)[-1]["type"], "frame_result")
        self.assertEqual(smoother.confidence_threshold, 0.5)


class TestAC3hTimestamps(_WsCase):
    def test_h_client_source(self):
        ws, _ = self.connect()
        frames = []
        for _ in range(3):
            self.send_frame(ws)
            frames.append(self.until_frame_result(ws)[-1])
        self.assertEqual([f["segment"]["frames"] for f in frames], [1, 2, 3])
        self.assertTrue(all(f["metrics"]["timestamp_source"] == "client" for f in frames))
        last = self.ts * 1000.0 / 30.0
        for bad in (f"{last - 5}", f"{last}", "NaN", '"abc"'):
            ws.send_text('{"image": "%s", "timestamp": %s}' % (URL_640, bad))
            with self.subTest(timestamp=bad):
                self.expect_error(ws, "bad_timestamp")
        ws.send_bytes(PNG_640)                                  # binary frame has no timestamp
        self.expect_error(ws, "bad_timestamp")
        self.send_frame(ws, ts=None)                            # text frame without timestamp
        self.expect_error(ws, "bad_timestamp")
        self.send_frame(ws)
        f = self.until_frame_result(ws)[-1]
        self.assertEqual(f["segment"]["frames"], 4)             # none of the rejected frames entered the buffer
        self.assertEqual(self.extractor.i, 4)

    def test_h_server_source(self):
        ws, _ = self.connect()
        ws.send_bytes(PNG_640)
        f = self.until_frame_result(ws)[-1]
        self.assertEqual(f["metrics"]["timestamp_source"], "server")
        self.assertIsNone(f["metrics"]["client_timestamp"])
        self.send_frame(ws)                                     # a client timestamp in a server-time session
        self.expect_error(ws, "bad_timestamp")
        ws.send_text(URL_640)                                   # bare data URL text: no timestamp -> accepted
        f = self.until_frame_result(ws)[-1]
        self.assertEqual((f["type"], f["segment"]["frames"]), ("frame_result", 2))


class TestAC3iControl(_WsCase):
    def test_i_reset_while_recording(self):
        ws, _ = self.connect()
        for _ in range(len(self.t)):
            self.send_frame(ws)
            f = self.until_frame_result(ws)[-1]
            if f["segment"]["state"] == "recording":
                break
        self.assertEqual(f["segment"]["state"], "recording")
        ws.send_text(json.dumps({"type": "control", "action": "reset"}))
        m = ws.receive_json()
        self.assertEqual((m["type"], m["reason"]), ("sign_discarded", "reset"))
        self.assertEqual(set(m), {"type", "segment_id", "frame_seq", "reason", "segment"})
        self.assertEqual(set(m["segment"]), {"duration_s", "frames"})
        ws.send_text(json.dumps({"type": "control", "action": "explode"}))
        self.expect_error(ws, "bad_message")
        self.send_frame(ws)
        f = self.until_frame_result(ws)[-1]
        self.assertEqual(f["segment"]["state"], "idle")


class TestAC7Legacy(_WsCase):
    pipeline_kind = "legacy"

    def test_b_c_legacy_keys_and_real_timings(self):
        ws, _ = self.connect()
        for is_new, expected in ((True, 7.0), (False, 0.0)):
            FakeRealtimePipeline.is_new = is_new
            self.send_frame(ws)
            f = self.until_frame_result(ws)[-1]
            with self.subTest(is_new=is_new):
                self.assertEqual(f["type"], "frame_result")
                self.assertTrue(LEGACY_KEYS <= set(f), LEGACY_KEYS - set(f))
                self.assertTrue(LEGACY_METRIC_KEYS <= set(f["metrics"]))
                self.assertEqual(f["metrics"]["server_infer_ms"], expected)
                self.assertIn("decode_ms", f["metrics"])
                self.assertIn("postprocess_ms", f["metrics"])
                self.assertGreaterEqual(f["metrics"]["server_preprocess_ms"], 0.0)

    def test_d_no_fabricated_split(self):
        with open(os.path.join(PROJECT_ROOT, "backend", "main.py"), encoding="utf-8") as fh:
            self.assertIsNone(re.search(r"latency_ms \* 0\.[0-9]", fh.read()))


class TestAC7aUnchangedFiles(unittest.TestCase):
    FILES = ["src/inference/realtime_pipeline.py", "src/inference/realtime_extractor.py", "src/inference/predictor.py",
             "src/inference/smoother.py", "src/data/harmonized.py", "src/data/landmark_extractor.py",
             "scripts/train_unified.py", "scripts/extract_keypoints_batch.py", "tests/test_harmonized.py",
             "tests/test_realtime.py"]

    @unittest.skipUnless(os.path.isdir(os.path.join(PROJECT_ROOT, ".git")), "not a git checkout")
    def test_a_no_diff_since_plan_base(self):
        out = subprocess.run(["git", "diff", "--stat", "9f4eb68", "--", *self.FILES], cwd=PROJECT_ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "")
        out = subprocess.run(["git", "diff", "--stat", "c65032a", "--", "src/data/harmonized.py"],
                             cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
