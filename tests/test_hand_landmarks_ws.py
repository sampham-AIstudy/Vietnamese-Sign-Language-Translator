"""
Plan 06 AC4: contract of WS /ws/hand-landmarks (protocol_version 1) with the REAL MediaPipe Hands graph (CPU).

Real input: frames of the hauuto clip a_hau_A_001.mp4 (training data of the deployed Level 1 model; used here only to
check the message contract, not accuracy). The frame index with a hand is taken from the output of
scripts/extract_hands_batch.py::_extract_one run in a temporary directory in this test. Other pixels: an all-black
frame (no hand) and a PNG header declaring 4000x10 (never decoded).
"""
import ast
import base64
import csv
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest import mock

import cv2
import mediapipe as mp
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from src.inference import hand_live  # noqa: E402

WS = "/ws/hand-landmarks"
EXTRACT_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "extract_hands_batch.py")
MANIFEST = os.path.join(PROJECT_ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands", "manifest.csv")
CLIP = os.path.join(PROJECT_ROOT, "data", "external", "hauuto_raw", "raw", "raw", "hau", "a_hau_A_001.mp4")
SESSION_INFO_KEYS = {"type", "endpoint", "protocol_version", "extractor", "limits"}
HAND_FRAME_KEYS = {"type", "segment_id", "frame_seq", "received_seq", "client_timestamp", "frame_width",
                   "frame_height", "landmarks", "handedness", "handedness_score", "metrics"}


def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_hands_batch", EXTRACT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def png_bytes(frame):
    ok, buf = cv2.imencode(".png", frame)
    assert ok
    return buf.tobytes()


def data_url(data, mime="image/png"):
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def png_header_only(w, h):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IEND", b"")


BLACK_PNG = png_bytes(np.zeros((480, 640, 3), np.uint8))
BLACK_URL = data_url(BLACK_PNG)


def _hands_calls_in_extractor():
    with open(EXTRACT_SCRIPT, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name == "Hands":
                calls.append(node)
    return calls


class TestExtractorSettings(unittest.TestCase):
    """AC4-a."""

    def test_kwargs_equal_training_extractor(self):
        calls = _hands_calls_in_extractor()
        self.assertEqual(len(calls), 1, "expected exactly one Hands(...) call in extract_hands_batch.py")
        self.assertEqual(calls[0].args, [])
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in calls[0].keywords}
        self.assertEqual(hand_live.LEVEL1_HANDS_KWARGS, kwargs)
        for k, v in kwargs.items():
            self.assertIs(type(hand_live.LEVEL1_HANDS_KWARGS[k]), type(v), k)

    def test_module_is_pure(self):
        out = subprocess.run(
            [sys.executable, "-c",
             "import src.inference.hand_live, sys; print('torch' in sys.modules, 'fastapi' in sys.modules)"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertEqual(out.stdout.strip().splitlines()[-1], "False False")


class _WsCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)  # no `with`: lifespan (Level 2 preload) is not started

    def connect(self):
        return self.client.websocket_connect(WS)


class TestSessionInfo(_WsCase):
    """AC4-b."""

    @unittest.skipUnless(os.path.isfile(MANIFEST), "Level 1 manifest.csv missing (gitignored data; clean clone)")
    def test_session_info(self):
        with open(MANIFEST, encoding="utf-8") as f:
            versions = {row["mediapipe_version"] for row in csv.DictReader(f)}
        self.assertEqual(len(versions), 1, versions)
        with self.connect() as ws:
            m = ws.receive_json()
        self.assertEqual(m["type"], "session_info", m)
        self.assertEqual(set(m), SESSION_INFO_KEYS)
        self.assertEqual(m["endpoint"], "hand-landmarks")
        self.assertEqual(m["protocol_version"], 1)
        ex = m["extractor"]
        self.assertEqual(ex["name"], "mp.solutions.hands")
        self.assertEqual(ex["mediapipe_version"], mp.__version__)
        self.assertEqual(ex["mediapipe_version"], next(iter(versions)))
        self.assertEqual({k: ex[k] for k in hand_live.LEVEL1_HANDS_KWARGS}, hand_live.LEVEL1_HANDS_KWARGS)
        self.assertEqual(set(ex), {"name", "mediapipe_version"} | set(hand_live.LEVEL1_HANDS_KWARGS))
        self.assertEqual(m["limits"], {"max_message_bytes": api.WS_MAX_MESSAGE_BYTES,
                                       "max_frame_side": api.WS_MAX_FRAME_SIDE,
                                       "max_frames_per_segment": api.ALPHABET_MAX_FRAMES})


class _SpyHands:
    """Wraps mp.solutions.hands.Hands: records kwargs and counts close() per graph (graphs stay real)."""

    def __init__(self):
        self.real = mp.solutions.hands.Hands
        self.graphs = []   # [(kwargs, graph, closes)]

    def __call__(self, **kwargs):
        graph = self.real(**kwargs)
        record = {"kwargs": kwargs, "closes": 0}
        orig_close = graph.close

        def close():
            record["closes"] += 1
            return orig_close()
        graph.close = close
        self.graphs.append(record)
        return graph


class TestReset(_WsCase):
    """AC4-c."""

    def test_reset_segments_and_graphs(self):
        spy = _SpyHands()
        with mock.patch.object(mp.solutions.hands, "Hands", side_effect=spy) as ctor:
            with self.connect() as ws:
                self.assertEqual(ws.receive_json()["type"], "session_info")
                self.assertEqual(ctor.call_count, 1)
                ws.send_json({"image": BLACK_URL, "timestamp": 1.0})
                m = ws.receive_json()
                self.assertEqual((m["type"], m["segment_id"], m["frame_seq"]), ("hand_frame", 0, 0), m)
                ws.send_json({"image": BLACK_URL, "timestamp": 2.0})
                self.assertEqual(ws.receive_json()["frame_seq"], 1)
                for n_reset in (1, 2, 3):
                    ws.send_json({"type": "control", "action": "reset"})
                    m = ws.receive_json()
                    self.assertEqual(m, {"type": "reset_done", "segment_id": n_reset})
                    self.assertEqual(ctor.call_count, 1 + n_reset)
                    # every previous graph closed exactly once, the new one still open
                    self.assertEqual([g["closes"] for g in spy.graphs], [1] * n_reset + [0])
                    ws.send_json({"image": BLACK_URL, "timestamp": 10.0 + n_reset})
                    m = ws.receive_json()
                    self.assertEqual((m["type"], m["segment_id"], m["frame_seq"]), ("hand_frame", n_reset, 0), m)
        self.assertEqual(ctor.call_count, 4)
        self.assertEqual([g["closes"] for g in spy.graphs], [1, 1, 1, 1])   # last graph closed with the session
        for g in spy.graphs:
            self.assertEqual(g["kwargs"], hand_live.LEVEL1_HANDS_KWARGS)


@unittest.skipUnless(os.path.isfile(CLIP), "hauuto clip a_hau_A_001.mp4 missing (gitignored data; clean clone)")
class TestRealFrame(_WsCase):
    """AC4-d."""

    @classmethod
    def setUpClass(cls):
        extract = load_extract_module()
        cls.tmp = tempfile.mkdtemp(prefix="vslt_ac4_")
        out = os.path.join(cls.tmp, "a_hau_A_001.npz")
        row = {"video_path": CLIP, "sample_id": "hauuto_a_hau_A_001", "symbol": "a", "signer_id": "hauuto_hau",
               "source": "hauuto"}
        path, status = extract._extract_one((row, out))
        assert status == "ok", status
        with np.load(path) as z:
            detected = np.asarray(z["detected_mask"], dtype=bool)
        idx = np.flatnonzero(detected)
        assert idx.size > 0, "no detected frame in the clip according to _extract_one"
        cls.index = int(idx[0])
        cap = cv2.VideoCapture(CLIP)
        frame = None
        for _ in range(cls.index + 1):
            ok, frame = cap.read()
            assert ok
        cap.release()
        cls.frame = frame

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_hand_and_no_hand(self):
        with self.connect() as ws:
            self.assertEqual(ws.receive_json()["type"], "session_info")
            ws.send_json({"image": data_url(png_bytes(self.frame)), "timestamp": 0.0})
            m = ws.receive_json()
            ws.send_json({"type": "control", "action": "reset"})
            self.assertEqual(ws.receive_json()["type"], "reset_done")
            ws.send_json({"image": BLACK_URL, "timestamp": 1.0})
            black = ws.receive_json()
        print(f"\n  a_hau_A_001: frame {self.index} (first detected by _extract_one), handedness {m.get('handedness')}")
        self.assertEqual(m["type"], "hand_frame", m)
        self.assertEqual(set(m), HAND_FRAME_KEYS)
        self.assertEqual((m["frame_width"], m["frame_height"]), (self.frame.shape[1], self.frame.shape[0]))
        lms = m["landmarks"]
        self.assertIsNotNone(lms)
        self.assertEqual(len(lms), 21)
        for p in lms:
            self.assertEqual(len(p), 3)
            for v in p:
                self.assertIsInstance(v, float)
                self.assertTrue(np.isfinite(v) and abs(v) <= 10, v)
        self.assertIn(m["handedness"], {"Left", "Right"})
        self.assertTrue(0 < m["handedness_score"] <= 1, m["handedness_score"])
        self.assertEqual(set(m["metrics"]), {"decode_ms", "extract_ms", "server_total_ms"})
        self.assertEqual(black["type"], "hand_frame", black)
        self.assertIsNone(black["landmarks"])
        self.assertEqual(black["handedness"], "")
        self.assertIsNone(black["handedness_score"])
        self.assertEqual((black["frame_width"], black["frame_height"]), (640, 480))


class TestErrors(_WsCase):
    """AC4-e: per-message errors keep the session open and do not advance frame_seq; > 1 MiB closes with 1009."""

    def assert_error(self, m, codes, sent=None):
        self.assertEqual(m["type"], "error", m)
        self.assertIn(m["code"], codes, m)
        self.assertLessEqual(len(m["detail"]), 200)
        if sent:
            self.assertNotIn(sent, m["detail"])
            self.assertNotIn(sent[:64], m["detail"])

    def next_frame_ok(self, ws, expected_seq, ts):
        ws.send_json({"image": BLACK_URL, "timestamp": ts})
        m = ws.receive_json()
        self.assertEqual((m["type"], m["frame_seq"]), ("hand_frame", expected_seq), m)

    def test_errors_keep_session(self):
        header_4000 = base64.b64encode(png_header_only(4000, 10)).decode("ascii")
        with self.connect() as ws:
            self.assertEqual(ws.receive_json()["type"], "session_info")
            self.next_frame_ok(ws, 0, 1.0)
            for garbage in ("this is not a frame !!!", "{not json", "@@@@"):
                ws.send_text(garbage)
                self.assert_error(ws.receive_json(), {"bad_message", "decode_failed", "unsupported_format"},
                                  garbage)
            self.next_frame_ok(ws, 1, 2.0)
            with mock.patch.object(api.cv2, "imdecode", wraps=cv2.imdecode) as imdecode:
                ws.send_json({"image": "data:image/png;base64," + header_4000, "timestamp": 3.0})
                self.assert_error(ws.receive_json(), {"frame_too_large"}, header_4000)
                self.assertEqual(imdecode.call_count, 0)
                self.next_frame_ok(ws, 2, 4.0)
                self.assertEqual(imdecode.call_count, 1)
            ws.send_json({"image": BLACK_URL, "timestamp": "x"})
            self.assert_error(ws.receive_json(), {"bad_timestamp"}, BLACK_URL[len("data:image/png;base64,"):])
            self.next_frame_ok(ws, 3, 5.0)

    def test_message_too_large_closes_1009(self):
        big = "data:image/png;base64," + "A" * (api.WS_MAX_MESSAGE_BYTES + 1)
        with self.connect() as ws:
            self.assertEqual(ws.receive_json()["type"], "session_info")
            ws.send_text(big)
            m = ws.receive_json()
            self.assert_error(m, {"message_too_large"}, "A" * 64)
            closing = ws.receive()
            self.assertEqual((closing["type"], closing["code"]), ("websocket.close", 1009))


class TestSequential(_WsCase):
    """AC4-f: frames are handled in order, none dropped; client timestamps are echoed unchanged."""

    def test_five_frames_then_binary(self):
        stamps = [1000.0, 1041.5, 1083.25, 1125, 1166.875]
        with self.connect() as ws:
            self.assertEqual(ws.receive_json()["type"], "session_info")
            for ts in stamps:
                ws.send_json({"image": BLACK_URL, "timestamp": ts})
            got = [ws.receive_json() for _ in stamps]
            ws.send_bytes(BLACK_PNG)
            binary = ws.receive_json()
        self.assertEqual([m["type"] for m in got], ["hand_frame"] * 5)
        self.assertEqual([m["frame_seq"] for m in got], [0, 1, 2, 3, 4])
        seqs = [m["received_seq"] for m in got]
        self.assertTrue(all(b > a for a, b in zip(seqs, seqs[1:])), seqs)
        self.assertEqual([m["client_timestamp"] for m in got], stamps)
        self.assertEqual((binary["type"], binary["frame_seq"]), ("hand_frame", 5), binary)
        self.assertIsNone(binary["client_timestamp"])
        self.assertGreater(binary["received_seq"], seqs[-1])


class TestUnavailable(_WsCase):
    """AC4-g."""

    def test_hands_init_failure(self):
        with mock.patch.object(mp.solutions.hands, "Hands", side_effect=RuntimeError("graph init failed (test)")):
            with self.connect() as ws:
                m = ws.receive_json()
                self.assertEqual((m["type"], m["code"]), ("error", "model_unavailable"), m)
                self.assertLessEqual(len(m["detail"]), 200)
                closing = ws.receive()
                self.assertEqual((closing["type"], closing["code"]), ("websocket.close", 1011))


if __name__ == "__main__":
    unittest.main()
