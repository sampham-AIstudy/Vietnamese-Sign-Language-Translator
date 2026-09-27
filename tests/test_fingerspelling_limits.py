"""
Plan 03: request limits (AC1), retired image endpoint (AC2), response kind + status provenance (AC4),
concurrent model loading (AC6) and the OpenAPI contract (AC7) of the Level 1 endpoints in backend/main.py.

Fixture checkpoints are small random-weight models written to a temp dir (test fixtures, not data);
nothing here touches checkpoints/ or the deployed model.
"""
import inspect
import json
import math
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from build_alphabet_tasks import ALPHABET_CLASSES  # noqa: E402
from src.inference.fingerspelling_compose import token_kind  # noqa: E402
from src.models.alphabet_temporal import VSLAlphabetBiGRU  # noqa: E402

SEQ = "/api/fingerspelling/sequence"
COMPOSE = "/api/fingerspelling/compose"
STATUS = "/api/fingerspelling/status"
IMAGE = "/api/fingerspelling"
PROBE = "/api/__limit_probe__"
LIMIT = api.ALPHABET_MAX_BODY_BYTES
PREPROCESSING = {"aspect_correct": True, "mirror_left_hand": True, "target_frames": 30,
                 "resample": "frame_index", "wrist_trajectory": False, "min_detected_frames": 3}


def hand_clip(T=40, seed=0, hand="Right"):
    """Deterministic hand-like landmark clip (fixture): [T,21,3], all frames detected."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.3, 0.7, size=(21, 3))
    base[:, 2] = rng.normal(0, 0.05, 21)
    drift = np.linspace(0, 0.1, T)[:, None, None]
    lms = base[None] + drift + rng.normal(0, 0.005, size=(T, 21, 3))
    return lms, [hand] * T


def body_for(lms, labels, width=640, height=480, **kw):
    body = {"landmarks": [f.tolist() for f in lms], "handedness": list(labels),
            "frame_width": width, "frame_height": height}
    body.update(kw)
    return body


def long_float(x):
    """The first float >= x whose repr has exactly 17 significant digits and an exponent."""
    v = float(x)
    for _ in range(10000):
        r = repr(v)
        if "e" in r and len(r.split("e")[0].lstrip("-").replace(".", "").lstrip("0")) == 17:
            return v
        v = math.nextafter(v, math.inf)
    raise AssertionError(f"no 17-digit float near {x}")


def is_long_float(v):
    r = repr(v)
    return isinstance(v, float) and "e" in r and len(r.split("e")[0].lstrip("-").replace(".", "").lstrip("0")) == 17


def largest_valid_payload():
    """AC1-e: T=300, every frame 21x3, handedness + timestamps, every coordinate a float whose repr
    has 17 significant digits and an exponent (x, y ~ (1.3..1.8)e-5, z ~ -(1.0..1.2)e-5: a leading
    digit 1 makes 17-digit reprs common) so the JSON is as long as floats can make it, while the palm
    length stays > 0."""
    T = api.ALPHABET_MAX_FRAMES
    lms, _ = hand_clip(T=T, seed=7)
    lms[..., :2] = (1.0 + lms[..., :2]) * 1e-5
    lms[..., 2] = -(1.0 + np.abs(lms[..., 2])) * 1e-5
    coords = [[[long_float(v) for v in point] for point in frame] for frame in lms]
    ts = [long_float((1.0 + t * 0.003) * 1e-5) for t in range(T)]  # increasing, 17 digits + exponent
    return {"landmarks": coords, "handedness": ["Right"] * T, "timestamps_ms": ts,
            "frame_width": api.ALPHABET_MAX_FRAME_SIDE, "frame_height": api.ALPHABET_MAX_FRAME_SIDE,
            "source_mirrored": False, "top_k": 10}


def save_fixture(path, trained_on=None, classes=ALPHABET_CLASSES):
    torch.manual_seed(0)
    model = VSLAlphabetBiGRU(input_dim=63, hidden_dim=64, num_layers=2, num_classes=len(classes)).eval()
    ckpt = {"model_type": "bigru", "state_dict": model.state_dict(), "classes": list(classes),
            "num_classes": len(classes), "preprocessing": PREPROCESSING,
            "hparams": {"hidden_dim": 64, "num_layers": 2}}
    if trained_on is not None:
        ckpt["trained_on"] = trained_on
    torch.save(ckpt, path)
    return path


class _Case(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ckpt = save_fixture(os.path.join(cls.tmp.name, "fixture_no_trained_on.pt"))
        cls.ckpt_hauuto = save_fixture(os.path.join(cls.tmp.name, "fixture_hauuto.pt"),
                                       trained_on={"source": "hauuto", "signers": ["s1"], "clips": 1})
        cls.ckpt_other = save_fixture(os.path.join(cls.tmp.name, "fixture_other.pt"),
                                      trained_on={"source": "somewhere_else"})
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started

    @classmethod
    def tearDownClass(cls):
        cls._use(None)
        cls.tmp.cleanup()

    @staticmethod
    def _use(path):
        api.ALPHABET_CKPT = path or os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
        api._alphabet_model, api._alphabet_meta = None, None

    def setUp(self):
        self._use(self.ckpt)

    def post_raw(self, path, text, content_type="application/json"):
        return self.client.post(path, content=text.encode("utf-8") if isinstance(text, str) else text,
                                headers={"content-type": content_type})


def chunks_of(data, size=65536):
    def gen():
        for i in range(0, len(data), size):
            yield data[i:i + size]
    return gen()


class TestBodyLimit(_Case):
    """AC1-a..d: 413 before parsing, with and without Content-Length, only on the two Level 1 paths."""

    def test_constants(self):
        self.assertEqual(api.ALPHABET_MAX_BODY_BYTES, 1_048_576)
        self.assertEqual(api.ALPHABET_MAX_FRAME_SIDE, 8192)
        self.assertEqual(api.ALPHABET_MAX_FRAMES, 300)

    def _oversized(self, path):
        head = b'{"tokens": []}' if path == COMPOSE else b'{"landmarks": [null]}'
        return head + b" " * (LIMIT + 1 - len(head))  # valid JSON, one byte over the limit

    def test_chunked_request_has_no_content_length(self):
        req = self.client.build_request("POST", SEQ, content=chunks_of(b"x" * 10))
        self.assertNotIn("content-length", req.headers)
        self.assertEqual(req.headers.get("transfer-encoding"), "chunked")

    def test_oversized_with_content_length_is_413(self):  # AC1-a, AC1-c
        for path in (SEQ, COMPOSE):
            with self.subTest(path=path):
                body = self._oversized(path)
                self.assertEqual(len(body), LIMIT + 1)
                r = self.post_raw(path, body)
                self.assertEqual(r.status_code, 413, r.text)
                self.assertIn("detail", r.json())

    def test_oversized_chunked_is_413(self):  # AC1-b, AC1-c
        for path in (SEQ, COMPOSE):
            with self.subTest(path=path):
                r = self.client.post(path, content=chunks_of(self._oversized(path)),
                                     headers={"content-type": "application/json"})
                self.assertEqual(r.status_code, 413, r.text)
                self.assertIn("detail", r.json())

    def test_body_at_the_limit_is_accepted(self):
        head = b'{"tokens": ["a"]}'
        body = head + b" " * (LIMIT - len(head))
        self.assertEqual(len(body), LIMIT)
        self.assertEqual(self.post_raw(COMPOSE, body).status_code, 200)
        r = self.client.post(COMPOSE, content=chunks_of(body), headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["text"], "a")

    def test_other_paths_are_not_limited(self):  # AC1-d
        body = b"x" * (LIMIT + 1)
        self.assertEqual(self.post_raw(PROBE, body).status_code, 404)
        self.assertEqual(self.client.post(PROBE, content=chunks_of(body)).status_code, 404)

    def test_other_paths_keep_default_422_format(self):
        """The Level 1 422 handler is scoped: /api/translate (validation fails before any model load)
        still gets FastAPI's default body, which echoes `input`."""
        r = self.client.post("/api/translate", json={})
        self.assertEqual(r.status_code, 422)
        self.assertIn("input", r.json()["detail"][0])
        r = self.client.post(SEQ, json={})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(set(r.json()["detail"][0]), {"loc", "msg", "type"})


class TestLargestValidPayload(_Case):
    def test_largest_valid_payload_fits_and_returns_200(self):  # AC1-e
        body = largest_valid_payload()
        flat = [v for frame in body["landmarks"] for point in frame for v in point] + body["timestamps_ms"]
        self.assertEqual(len(body["landmarks"]), 300)
        self.assertTrue(all(len(f) == 21 and all(len(p) == 3 for p in f) for f in body["landmarks"]))
        self.assertTrue(all(is_long_float(v) for v in flat))
        self.assertEqual(body["timestamps_ms"], sorted(body["timestamps_ms"]))
        lms = np.asarray(body["landmarks"], dtype=np.float32)
        palm = np.linalg.norm(lms[:, 9] - lms[:, 0], axis=-1)
        self.assertTrue((palm > 0).all())
        encoded = json.dumps(body).encode()
        self.assertLess(len(encoded), LIMIT)
        r = self.post_raw(SEQ, encoded)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["detected_frames"], 300)


class TestInputValidation(_Case):
    """AC1-f..j. Every case is checked for its exact code, and none may be 500."""

    SENTINEL = 0.123456789

    def _raw_with(self, token, where="landmarks"):
        lms, labels = hand_clip()
        body = body_for(lms, labels)
        if where == "landmarks":
            body["landmarks"][5][3][0] = self.SENTINEL
        else:
            body["timestamps_ms"] = [float(t) for t in range(40)]
            body["timestamps_ms"][7] = self.SENTINEL
        text = json.dumps(body)
        self.assertEqual(text.count(repr(self.SENTINEL)), 1)
        return text.replace(repr(self.SENTINEL), token)

    def test_nan_and_infinity_are_422(self):  # AC1-f
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            for where in ("landmarks", "timestamps_ms"):
                with self.subTest(token=token, where=where):
                    r = self.post_raw(SEQ, self._raw_with(token, where))
                    self.assertEqual(r.status_code, 422, r.text)

    def test_nan_inside_a_pydantic_error_is_still_422(self):
        """The rejected input is not echoed back (it would hold NaN, which is not valid JSON)."""
        lms, labels = hand_clip()
        good = body_for(lms, labels)
        bad_frame = [[0.5, 0.5, self.SENTINEL]] * 22  # 22 points -> pydantic error on a list holding NaN
        cases = {
            "22 points + NaN": {**good, "landmarks": [bad_frame] + good["landmarks"][1:]},
            "301 frames + NaN": {**good, "landmarks": [[[0.5, 0.5, self.SENTINEL]] * 21] * 301,
                                 "handedness": ["Right"] * 301},
            "frame_width NaN": {**good, "frame_width": self.SENTINEL},
        }
        for name, body in cases.items():
            with self.subTest(name):
                text = json.dumps(body).replace(repr(self.SENTINEL), "NaN")
                self.assertIn("NaN", text)
                r = self.post_raw(SEQ, text)
                self.assertEqual(r.status_code, 422, r.text)
                self.assertNotIn("NaN", r.text)
        r = self.post_raw(COMPOSE, '{"tokens": [NaN, "a"]}')
        self.assertEqual(r.status_code, 422, r.text)

    def test_not_json_is_422(self):  # AC1-g
        self.assertEqual(self.post_raw(SEQ, b"abc", content_type="text/plain").status_code, 422)
        self.assertEqual(self.post_raw(SEQ, b"abc").status_code, 422)
        self.assertEqual(self.post_raw(COMPOSE, b"abc", content_type="text/plain").status_code, 422)
        self.assertEqual(self.post_raw(SEQ, b'{"landmarks": [').status_code, 422)
        self.assertEqual(self.post_raw(SEQ, b"[]").status_code, 422)

    def test_frame_side_bounds(self):  # AC1-h
        lms, labels = hand_clip()
        side = api.ALPHABET_MAX_FRAME_SIDE
        self.assertEqual(self.client.post(SEQ, json=body_for(lms, labels, width=side + 1)).status_code, 422)
        self.assertEqual(self.client.post(SEQ, json=body_for(lms, labels, height=side + 1)).status_code, 422)
        r = self.client.post(SEQ, json=body_for(lms, labels, height=side))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.post(SEQ, json=body_for(lms, labels, width=side)).status_code, 200)

    def test_frame_shape(self):  # AC1-i
        lms, labels = hand_clip()
        good = body_for(lms, labels)
        extra_point = [good["landmarks"][0] + [[0.5, 0.5, 0.0]]] + good["landmarks"][1:]
        four_coords = [[good["landmarks"][0][0] + [0.0]] + good["landmarks"][0][1:]] + good["landmarks"][1:]
        ragged = [[good["landmarks"][0][0][:2]] + good["landmarks"][0][1:]] + good["landmarks"][1:]
        for name, landmarks in (("22 points", extra_point), ("4 coordinates", four_coords), ("2 coordinates", ragged)):
            with self.subTest(name):
                r = self.client.post(SEQ, json={**good, "landmarks": landmarks})
                self.assertEqual(r.status_code, 422, r.text)

    def test_no_500_on_bad_input(self):  # AC1-j (sweep of odd payloads)
        lms, labels = hand_clip()
        good = body_for(lms, labels)
        payloads = [
            b"", b"null", b"0", b'"x"', b"{}", b'{"landmarks": null}', b'{"landmarks": "abc"}',
            json.dumps({**good, "landmarks": [[["a", "b", "c"]] * 21] * 3}).encode(),
            json.dumps({**good, "landmarks": [[[[0.1]]] * 21] * 3}).encode(),
            json.dumps({**good, "handedness": ["x" * 1000] * 40}).encode(),
            json.dumps({**good, "handedness": [1] * 40}).encode(),
            json.dumps({**good, "timestamps_ms": ["a"] * 40}).encode(),
            json.dumps({**good, "top_k": 11}).encode(),
            json.dumps({**good, "frame_width": -1}).encode(),
            json.dumps({**good, "frame_width": 1.5}).encode(),
            json.dumps({**good, "source_mirrored": "maybe"}).encode(),
            json.dumps({**good, "landmarks": []}).encode(),
            json.dumps({**good, "landmarks": [[]] * 40}).encode(),
            json.dumps({**good, "landmarks": [[[1e300, 1e300, 1e300]] * 21] * 40}).encode(),
        ]
        for i, raw in enumerate(payloads):
            with self.subTest(i=i, payload=raw[:60]):
                r = self.post_raw(SEQ, raw)
                self.assertEqual(r.status_code, 422, r.text[:300])
        for raw in (b"", b"null", b'{"tokens": "a"}', b'{"tokens": [["a"]]}', b'{"tokens": [null]}'):
            with self.subTest(compose=raw):
                self.assertEqual(self.post_raw(COMPOSE, raw).status_code, 422)


class TestImageEndpoint409(_Case):
    """AC2: the retired image endpoint never reads its body."""

    def test_signature_has_no_parameters(self):
        self.assertEqual(len(inspect.signature(api.predict_fingerspelling).parameters), 0)

    def test_5mb_multipart_is_409(self):
        r = self.client.post(IMAGE, files={"file": ("big.jpg", b"\xff" * (5 * 1024 * 1024), "image/jpeg")})
        self.assertEqual(r.status_code, 409, r.text[:200])
        self.assertEqual(r.json()["detail"]["use"], SEQ)

    def test_empty_post_is_409(self):
        r = self.client.post(IMAGE)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["use"], SEQ)


class TestResponseKindAndStatus(_Case):
    """AC4."""

    def test_prediction_kind_and_candidate_kind(self):
        lms, labels = hand_clip()
        r = self.client.post(SEQ, json=body_for(lms, labels, top_k=10))
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertIn(body["prediction_kind"], ("letter", "tone"))
        self.assertEqual(body["prediction_kind"], token_kind(body["prediction"]))
        self.assertEqual(len(body["candidates"]), 10)
        for c in body["candidates"]:
            self.assertEqual(c["kind"], token_kind(c["class"]))

    def test_status_without_trained_on(self):
        body = self.client.get(STATUS).json()
        self.assertTrue(body["available"])
        self.assertIsNone(body["trained_on"])
        self.assertEqual(body["data_provenance"], {"status": "unknown"})

    def test_status_with_hauuto(self):
        self._use(self.ckpt_hauuto)
        body = self.client.get(STATUS).json()
        self.assertEqual(body["trained_on"]["source"], "hauuto")
        self.assertEqual(body["data_provenance"]["licence"], "unknown")
        self.assertEqual(body["data_provenance"]["usage"], "internal only")

    def test_status_with_unregistered_source(self):
        self._use(self.ckpt_other)
        body = self.client.get(STATUS).json()
        self.assertEqual(body["trained_on"], {"source": "somewhere_else"})
        self.assertEqual(body["data_provenance"], {"status": "unknown"})

    def test_evaluation_report_exists_in_repo(self):
        body = self.client.get(STATUS).json()
        path = body["evaluation_report"]
        self.assertFalse(os.path.isabs(path))
        self.assertTrue(os.path.isfile(os.path.join(PROJECT_ROOT, *path.split("/"))), path)

    def test_status_keeps_old_fields(self):
        body = self.client.get(STATUS).json()
        for key in ("available", "model", "model_type", "num_classes", "classes", "preprocessing",
                    "endpoint", "input", "message"):
            self.assertIn(key, body)
        self.assertEqual(body["classes"], ALPHABET_CLASSES)


class TestConcurrentLoad(_Case):
    """AC6: 8 threads, one torch.load, one model object."""

    def test_eight_threads_load_once(self):
        real_load = torch.load
        barrier = threading.Barrier(8)

        def slow_load(*args, **kwargs):
            threading.Event().wait(0.2)  # widen the race window
            return real_load(*args, **kwargs)

        results, errors = [None] * 8, []

        def worker(i):
            try:
                barrier.wait()
                results[i] = api.get_or_load_alphabet_model()
            except Exception as e:  # pragma: no cover - reported below
                errors.append(e)

        with mock.patch.object(api.torch, "load", side_effect=slow_load) as spy:
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(30)
        self.assertEqual(errors, [])
        self.assertEqual(spy.call_count, 1)
        models = {id(r[0]) for r in results}
        self.assertEqual(len(models), 1)
        self.assertIsNotNone(results[0][0])
        self.assertTrue(all(r[1] is results[0][1] for r in results))

    def test_failed_load_is_retried(self):
        missing = os.path.join(self.tmp.name, "later.pt")
        self._use(missing)
        self.assertEqual(api.get_or_load_alphabet_model(), (None, None))
        save_fixture(missing)
        model, meta = api.get_or_load_alphabet_model()
        self.assertIsNotNone(model)


class TestOpenApiContract(_Case):
    """AC7."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = cls.client.get("/openapi.json").json()

    def _request_schema(self, path):
        ref = self.spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        return self.spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]

    def test_paths(self):
        paths = self.spec["paths"]
        self.assertIn("post", paths[SEQ])
        self.assertIn("post", paths[COMPOSE])
        self.assertIn("get", paths[STATUS])
        self.assertIn("post", paths[IMAGE])

    def test_sequence_request_schema(self):
        props = self._request_schema(SEQ)["properties"]
        for key in ("landmarks", "handedness", "timestamps_ms", "frame_width", "frame_height",
                    "source_mirrored", "top_k"):
            self.assertIn(key, props)
        self.assertEqual(props["landmarks"]["maxItems"], 300)
        self.assertEqual(props["frame_width"]["maximum"], api.ALPHABET_MAX_FRAME_SIDE)

    def test_compose_request_schema(self):
        props = self._request_schema(COMPOSE)["properties"]
        self.assertEqual(props["tokens"]["maxItems"], 200)

    def test_image_endpoint_has_no_request_body(self):
        self.assertNotIn("requestBody", self.spec["paths"][IMAGE]["post"])


if __name__ == "__main__":
    unittest.main()
