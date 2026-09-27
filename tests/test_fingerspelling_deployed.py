"""
Plan 03 AC5: train/realtime equivalence for the checkpoint the backend DEPLOYS (checkpoints/alphabet_best.pt).

Offline path: scripts/train_alphabet_nested.load (the training feature code of the nested run that produced
the deployed weights, see reports/alphabet_deploy_2026-09-27/provenance.json, verdict V1-V6) + the model
rebuilt from the checkpoint on CPU. Realtime path: POST /api/fingerspelling/sequence with the raw MediaPipe
landmarks of the same real clips. Both run on the same CPU; the comparison is about identical inputs, not
accuracy (hauuto clips were in training). Needs the gitignored real landmarks (hauuto licence unknown:
internal use only) and the gitignored checkpoint; skipped with the missing file named otherwise.
"""
import csv
import hashlib
import json
import os
import sys
import unittest

import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402

SEQ = "/api/fingerspelling/sequence"
DEPLOYED_CKPT = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
REAL_DATA = os.path.join(PROJECT_ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands")
MANIFEST = os.path.join(REAL_DATA, "manifest.csv")
PROVENANCE_JSON = os.path.join(PROJECT_ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")
PER_SIGNER = 15
MIRROR_CLIPS = 5
_MISSING = [p for p in (DEPLOYED_CKPT, MANIFEST, PROVENANCE_JSON) if not os.path.exists(p)]
SKIP_REASON = "missing file(s): " + ", ".join(os.path.relpath(p, PROJECT_ROOT) for p in _MISSING)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestDeployedCheckpointEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from train_alphabet_nested import load, preprocessing_for
        from train_alphabet_real import build

        cls.preprocessing_for = staticmethod(preprocessing_for)
        cls.ckpt = torch.load(DEPLOYED_CKPT, map_location="cpu", weights_only=False)
        with open(PROVENANCE_JSON, encoding="utf-8") as f:
            cls.provenance = json.load(f)
        cls.classes = list(cls.ckpt["classes"])
        cls.kind, cls.variant = cls.ckpt["model_type"], cls.ckpt["selected"][2]

        # offline model: rebuilt from the checkpoint, independent of the backend's loader
        cls.model = build(cls.kind, len(cls.classes))
        cls.model.load_state_dict(cls.ckpt["state_dict"])
        cls.model.eval()

        with open(MANIFEST, encoding="utf-8") as f:
            cls.manifest = {m["sample_id"]: m for m in csv.DictReader(f)}
        items = sorted(load(REAL_DATA, {}), key=lambda t: t["sample_id"])
        rng = np.random.default_rng(0)
        sample = [t for t in items if t["source"] == "qipedc"]
        for signer in sorted({t["signer"] for t in items if t["source"] == "hauuto"}):
            own = [t for t in items if t["signer"] == signer]
            sample += [own[i] for i in sorted(rng.choice(len(own), PER_SIGNER, replace=False))]
        cls.sample = sample

        key = cls.variant if cls.kind == "bigru" else "static"
        with torch.no_grad():
            probs = torch.softmax(cls.model(torch.from_numpy(np.stack([t[key] for t in sample]))), dim=-1).numpy()
        cls.offline = {t["sample_id"]: p for t, p in zip(sample, probs)}

        cls._saved = (api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta)
        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = DEPLOYED_CKPT, None, None
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started

    @classmethod
    def tearDownClass(cls):
        api.ALPHABET_CKPT = cls._saved[0]
        api._alphabet_model, api._alphabet_meta = None, None

    def body(self, sample_id, mirrored=False):
        m = self.manifest[sample_id]
        d = np.load(os.path.join(REAL_DATA, m["landmark_path"]))
        lms, det = d["raw_landmarks"].astype(np.float32), d["detected_mask"].astype(bool)
        labels = [str(h) for h in d["handedness_label"]]
        if mirrored:
            lms = lms.copy()
            lms[det, :, 0] = 1.0 - lms[det, :, 0]
            labels = [{"Left": "Right", "Right": "Left"}.get(h, h) for h in labels]
        body = {"landmarks": [f.tolist() if ok else None for f, ok in zip(lms, det)], "handedness": labels,
                "frame_width": int(m["width"]), "frame_height": int(m["height"]), "source_mirrored": mirrored}
        if self.ckpt["preprocessing"].get("resample") == "time":  # same fallback as load() without PTS
            body["timestamps_ms"] = (np.arange(len(det)) * 1000.0 / float(m["fps"])).tolist()
        return body

    def test_a_sha256_pinned_by_provenance(self):
        self.assertEqual(sha256_of(DEPLOYED_CKPT), self.provenance["checkpoints"]["deployed"]["sha256"])

    def test_provenance_verdict_is_real_data(self):
        self.assertEqual(self.provenance["verdict"], "real_data_known_checkpoint")
        self.assertTrue(all(self.provenance["verdict_checks"][f"V{i}"]["ok"] for i in range(1, 7)))

    def test_b_preprocessing_matches_training(self):
        self.assertEqual(self.preprocessing_for(self.variant), self.ckpt["preprocessing"])

    def test_d_sample(self):
        n_qipedc = sum(m["source"] == "qipedc" for m in self.manifest.values())
        signers = {t["signer"] for t in self.sample if t["source"] == "hauuto"}
        self.assertEqual(len(signers), 4)
        self.assertGreater(n_qipedc, 0)
        self.assertEqual(sum(t["source"] == "qipedc" for t in self.sample), n_qipedc)
        self.assertEqual(len(self.sample), n_qipedc + PER_SIGNER * len(signers))
        self.assertEqual(len({t["sample_id"] for t in self.sample}), len(self.sample))

    def test_e_h_backend_equals_offline(self):
        for t in self.sample:
            sid = t["sample_id"]
            p = self.offline[sid]
            top3 = [self.classes[i] for i in np.argsort(-p, kind="stable")[:3]]
            r = self.client.post(SEQ, json=self.body(sid))
            with self.subTest(sid):
                self.assertEqual(r.status_code, 200, r.text[:300])
                body = r.json()
                self.assertEqual(body["prediction"], self.classes[int(p.argmax())])
                self.assertLessEqual(abs(body["confidence"] - float(p.max())), 1e-4)
                self.assertEqual([c["class"] for c in body["candidates"][:3]], top3)
                self.assertIsNotNone(body["prediction_kind"])  # AC5-h
                self.assertTrue(all(c["kind"] is not None for c in body["candidates"]))

    def test_f_mirrored_source(self):
        for t in self.sample[:MIRROR_CLIPS]:
            sid = t["sample_id"]
            a = self.client.post(SEQ, json=self.body(sid)).json()
            r = self.client.post(SEQ, json=self.body(sid, mirrored=True))
            with self.subTest(sid):
                self.assertEqual(r.status_code, 200, r.text[:300])
                b = r.json()
                self.assertEqual(b["prediction"], a["prediction"])
                self.assertEqual(b["confidence"], a["confidence"])

    def test_backend_loaded_the_deployed_checkpoint(self):
        self.client.get("/api/fingerspelling/status")
        self.assertEqual(api.ALPHABET_CKPT, DEPLOYED_CKPT)
        self.assertEqual(api._alphabet_meta["checkpoint"], "alphabet_best.pt")
        self.assertEqual(api._alphabet_meta["classes"], self.classes)


if __name__ == "__main__":
    unittest.main()
