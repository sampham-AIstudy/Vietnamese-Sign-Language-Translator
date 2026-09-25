"""
Contract + equivalence tests for the Level 1 fingerspelling endpoints (backend/main.py).

Contract: POST /api/fingerspelling (image) -> 409; POST /api/fingerspelling/sequence validates its
payload (422), handles mirrored input, answers 503 without a checkpoint.
Equivalence: the endpoint returns the same prediction/confidence as the offline training path
(canonicalize_hand_sequence + sequence_features_from_clip, as in scripts/train_alphabet_real.py).
The real-data test runs only when the (gitignored) hauuto landmarks are present locally.
"""
import csv
import os
import sys
import tempfile
import unittest

import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from src.data.alphabet_preprocessing import (  # noqa: E402
    canonicalize_hand_sequence, sequence_features_from_clip)
from src.models.alphabet_temporal import VSLAlphabetBiGRU  # noqa: E402

CLASSES = [f"c{i}" for i in range(34)]
SEQ = "/api/fingerspelling/sequence"
REAL_DATA = os.path.join(PROJECT_ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands")
REAL_CKPT = os.path.join(PROJECT_ROOT, "reports", "alphabet_real_run_2026-09-25", "alphabet_run", "alphabet_real_best.pt")


def make_clip(T=40, seed=0, hand="Left", missing=(3, 17, 18)):
    """Deterministic hand-like landmark clip (a test fixture, not data)."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.3, 0.7, size=(21, 3)).astype(np.float32)
    base[:, 2] = rng.normal(0, 0.05, 21)
    drift = np.linspace(0, 0.1, T, dtype=np.float32)[:, None, None]
    lms = base[None] + drift + rng.normal(0, 0.005, size=(T, 21, 3)).astype(np.float32)
    det = np.ones(T, dtype=bool)
    det[list(missing)] = False
    lms[~det] = 0.0
    labels = np.array([hand if d else "" for d in det])
    return lms, det, labels


def payload(lms, det, labels, width=640, height=480, **kw):
    body = {"landmarks": [f.tolist() if d else None for f, d in zip(lms, det)],
            "handedness": labels.tolist(), "frame_width": width, "frame_height": height}
    body.update(kw)
    return body


class _ApiCase(unittest.TestCase):
    preprocessing = {"aspect_correct": True, "mirror_left_hand": True, "target_frames": 30}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        torch.manual_seed(0)
        cls.model = VSLAlphabetBiGRU(input_dim=63, hidden_dim=64, num_layers=2, num_classes=len(CLASSES)).eval()
        cls.ckpt = os.path.join(cls.tmp.name, "alphabet_test.pt")
        torch.save({"model_type": "bigru", "state_dict": cls.model.state_dict(), "classes": CLASSES,
                    "num_classes": len(CLASSES), "preprocessing": cls.preprocessing,
                    "hparams": {"hidden_dim": 64, "num_layers": 2}}, cls.ckpt)
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


class TestFingerspellingContract(_ApiCase):
    def test_image_endpoint_returns_409(self):
        r = self.client.post("/api/fingerspelling", files={"file": ("a.jpg", b"\xff\xd8\xff", "image/jpeg")})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"]["use"], SEQ)
        self.assertEqual(self.client.post("/api/fingerspelling").status_code, 409)

    def test_status_describes_sequence_contract(self):
        body = self.client.get("/api/fingerspelling/status").json()
        self.assertTrue(body["available"])
        self.assertEqual((body["model_type"], body["endpoint"], body["input"]), ("bigru", SEQ, "landmark_sequence"))
        self.assertEqual(body["classes"], CLASSES)
        self.assertTrue(body["preprocessing"]["mirror_left_hand"])

    def test_valid_sequence_response_shape(self):
        r = self.client.post(SEQ, json=payload(*make_clip(), top_k=5))
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(len(body["candidates"]), 5)
        confs = [c["confidence"] for c in body["candidates"]]
        self.assertEqual(confs, sorted(confs, reverse=True))
        self.assertEqual(body["prediction"], body["candidates"][0]["class"])
        self.assertEqual((body["frames"], body["detected_frames"]), (40, 37))

    def test_validation_errors_are_422(self):
        lms, det, labels = make_clip()
        good = payload(lms, det, labels)
        cases = {
            "bad frame shape": {**good, "landmarks": [[[0.1, 0.2]] * 21] + good["landmarks"][1:]},
            "handedness length": {**good, "handedness": good["handedness"][:-1]},
            "handedness value": {**good, "handedness": ["left"] * 40},
            "handedness missing": {k: v for k, v in good.items() if k != "handedness"},
            "too few hands": {**good, "landmarks": [None] * 38 + good["landmarks"][:2]},
            "timestamps decreasing": {**good, "timestamps_ms": list(range(40, 0, -1))},
            "timestamps length": {**good, "timestamps_ms": [0.0, 33.0]},
            "zero width": {**good, "frame_width": 0},
            "too many frames": {**good, "landmarks": [None] * 301, "handedness": [""] * 301},
            "top_k": {**good, "top_k": 0},
        }
        for name, body in cases.items():
            with self.subTest(name):
                self.assertEqual(self.client.post(SEQ, json=body).status_code, 422)

    def test_mirrored_source_equals_unmirrored(self):
        lms, det, labels = make_clip(hand="Left")
        mirrored = lms.copy()
        mirrored[det, :, 0] = 1.0 - mirrored[det, :, 0]
        swapped = np.array([{"Left": "Right", "Right": "Left"}.get(h, h) for h in labels])
        a = self.client.post(SEQ, json=payload(lms, det, labels)).json()
        b = self.client.post(SEQ, json=payload(mirrored, det, swapped, source_mirrored=True)).json()
        self.assertEqual(a["candidates"], b["candidates"])

    def test_left_and_right_hand_give_same_answer(self):
        """A right hand (MediaPipe 'Left' on unmirrored frames) and its mirror image signed with the
        other hand must map to the same canonical input."""
        lms, det, labels = make_clip(hand="Left")
        other = lms.copy()
        other[det, :, 0] = 1.0 - other[det, :, 0]
        other_labels = np.array(["Right" if d else "" for d in det])
        a = self.client.post(SEQ, json=payload(lms, det, labels)).json()
        b = self.client.post(SEQ, json=payload(other, det, other_labels)).json()
        self.assertEqual(a["prediction"], b["prediction"])
        self.assertAlmostEqual(a["confidence"], b["confidence"], places=3)

    def test_missing_checkpoint_returns_503(self):
        self._use(os.path.join(self.tmp.name, "does_not_exist.pt"))
        self.assertEqual(self.client.post(SEQ, json=payload(*make_clip())).status_code, 503)
        self.assertFalse(self.client.get("/api/fingerspelling/status").json()["available"])

    def test_checkpoint_without_preprocessing_is_refused(self):
        bad = os.path.join(self.tmp.name, "no_prep.pt")
        torch.save({"model_type": "bigru", "state_dict": self.model.state_dict(), "classes": CLASSES}, bad)
        self._use(bad)
        self.assertEqual(self.client.post(SEQ, json=payload(*make_clip())).status_code, 503)


class TestTimeResampleContract(_ApiCase):
    preprocessing = {"aspect_correct": True, "mirror_left_hand": True, "target_frames": 30, "resample": "time"}

    def test_time_model_requires_timestamps(self):
        lms, det, labels = make_clip()
        self.assertEqual(self.client.post(SEQ, json=payload(lms, det, labels)).status_code, 422)
        ts = (np.arange(40) * 33.3).tolist()
        self.assertEqual(self.client.post(SEQ, json=payload(lms, det, labels, timestamps_ms=ts)).status_code, 200)


class TestBackendOfflineEquivalence(_ApiCase):
    def _offline(self, lms, det, labels, aspect):
        c_lms, c_det, _ = canonicalize_hand_sequence(lms, det, labels, aspect_ratio=aspect)
        feats = sequence_features_from_clip(c_lms, c_det, 30)
        with torch.no_grad():
            probs = torch.softmax(self.model(torch.from_numpy(feats)[None]), -1)[0]
        return int(probs.argmax()), float(probs.max())

    def test_fixture_clips_match_offline_path(self):
        for seed, hand, (w, h) in [(0, "Left", (640, 480)), (1, "Right", (1280, 720)), (2, "Left", (480, 480))]:
            lms, det, labels = make_clip(seed=seed, hand=hand)
            idx, conf = self._offline(lms, det, labels, w / h)
            body = self.client.post(SEQ, json=payload(lms, det, labels, width=w, height=h)).json()
            with self.subTest(seed=seed):
                self.assertEqual(body["prediction"], CLASSES[idx])
                self.assertAlmostEqual(body["confidence"], conf, places=4)


@unittest.skipUnless(os.path.exists(os.path.join(REAL_DATA, "manifest.csv")) and os.path.exists(REAL_CKPT),
                     "hauuto landmarks not present locally (gitignored, licence unknown)")
class TestRealClipEquivalence(unittest.TestCase):
    """Real clips through the backend vs scripts/train_alphabet_real.py load() + evaluate()."""

    def test_real_clips_match_training_evaluation(self):
        from train_alphabet_real import evaluate, load

        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = REAL_CKPT, None, None
        try:
            client = TestClient(api.app)
            model, meta = api.get_or_load_alphabet_model()
            items = load(REAL_DATA)
            rng = np.random.default_rng(0)
            items = [items[i] for i in rng.choice(len(items), 40, replace=False)]
            _, offline = evaluate(model, meta["model_type"], items, torch.device("cpu"))
            offline = {sid: pred for sid, _, pred in offline}
            manifest = {m["sample_id"]: m for m in csv.DictReader(open(os.path.join(REAL_DATA, "manifest.csv"), encoding="utf-8"))}
            for t in items:
                m = manifest[t["sample_id"]]
                d = np.load(os.path.join(REAL_DATA, m["landmark_path"]))
                body = payload(d["raw_landmarks"], d["detected_mask"].astype(bool), d["handedness_label"],
                               width=int(m["width"]), height=int(m["height"]))
                r = client.post(SEQ, json=body)
                with self.subTest(t["sample_id"]):
                    self.assertEqual(r.status_code, 200, r.text)
                    self.assertEqual(r.json()["prediction"], offline[t["sample_id"]])
        finally:
            api.ALPHABET_CKPT = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
            api._alphabet_model, api._alphabet_meta = None, None


if __name__ == "__main__":
    unittest.main()
