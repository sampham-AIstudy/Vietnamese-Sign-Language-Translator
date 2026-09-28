"""
Plan 05 AC3: GET /api/fingerspelling/status exposes only the data source and the number of signers of the Level 1
checkpoint (`trained_on` -> {"source", "n_signers"}), never the signer names or other trained_on keys.

Fixture checkpoints are small seeded-weight models written to a temp dir (test fixtures, not data). The deployed
checkpoint case reads checkpoints/alphabet_best.pt read-only; expected values are derived from the checkpoint itself.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient  # noqa: E402

import backend.main as api  # noqa: E402
from tests.test_fingerspelling_limits import save_fixture  # noqa: E402

STATUS = "/api/fingerspelling/status"
DEPLOYED = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
PROVENANCE = os.path.join(PROJECT_ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")
FIXTURE_SIGNERS = ["signer_alpha", "signer_beta"]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _all_strings(obj):
    """Every dict key and every string value, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _all_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _all_strings(v)
    elif isinstance(obj, str):
        yield obj


class _StatusCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started

    @classmethod
    def tearDownClass(cls):
        cls._use(None)
        cls.tmp.cleanup()

    @staticmethod
    def _use(path):
        api.ALPHABET_CKPT = path or DEPLOYED
        api._alphabet_model, api._alphabet_meta = None, None

    def assert_no_names(self, response, names):
        body = response.json()
        for name in names:
            self.assertNotIn(name, response.text)
            for s in _all_strings(body):
                self.assertNotIn(name, s)


class TestPublicTrainedOn(unittest.TestCase):
    """AC3-a: pure function table."""

    def test_table(self):
        cases = [
            (None, None),
            ("x", None),
            ({}, None),
            ({"clips": 5}, None),
            ({"source": "hauuto"}, {"source": "hauuto"}),
            ({"source": "hauuto", "signers": ["a", "b", "a"], "clips": 7}, {"source": "hauuto", "n_signers": 2}),
            ({"signers": ["a"]}, {"n_signers": 1}),
            ({"source": 3, "signers": "ab"}, None),
            ({"source": "x", "signers": ["a", 1]}, {"source": "x"}),
            ({"source": "x", "signers": []}, {"source": "x", "n_signers": 0}),
        ]
        for given, expected in cases:
            with self.subTest(given=given):
                self.assertEqual(api.public_trained_on(given), expected)

    def test_tuple_signers(self):
        self.assertEqual(api.public_trained_on({"source": "s", "signers": ("a", "b")}), {"source": "s", "n_signers": 2})

    def test_does_not_mutate_input(self):
        given = {"source": "hauuto", "signers": ["a", "b"], "clips": 3}
        snapshot = json.loads(json.dumps(given))
        api.public_trained_on(given)
        self.assertEqual(given, snapshot)


class TestStatusFixture(_StatusCase):
    """AC3-b: fixture checkpoint with signer names."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ckpt = save_fixture(os.path.join(cls.tmp.name, "fixture_named_signers.pt"),
                                trained_on={"source": "hauuto", "signers": list(FIXTURE_SIGNERS), "clips": 636})

    def setUp(self):
        self._use(self.ckpt)

    def test_status_only_source_and_count(self):
        r = self.client.get(STATUS)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body["available"])
        self.assertEqual(body["trained_on"], {"source": "hauuto", "n_signers": 2})
        self.assertNotIn('"clips"', r.text)
        self.assert_no_names(r, FIXTURE_SIGNERS)
        self.assertEqual(body["data_provenance"], {"licence": "unknown", "usage": "internal only",
                                                   "registry": "docs/data_registry.md#1b"})


@unittest.skipUnless(os.path.isfile(DEPLOYED), f"deployed checkpoint missing: {DEPLOYED}")
class TestStatusDeployed(_StatusCase):
    """AC3-c: the deployed checkpoint (sha256 pinned by provenance.json)."""

    def setUp(self):
        self._use(DEPLOYED)

    def test_deployed_checkpoint(self):
        with open(PROVENANCE, encoding="utf-8") as f:
            pinned = json.load(f)["checkpoints"]["deployed"]["sha256"]
        self.assertEqual(_sha256(DEPLOYED), pinned, "checkpoints/alphabet_best.pt differs from provenance.json")
        trained_on = torch.load(DEPLOYED, map_location="cpu", weights_only=False)["trained_on"]
        signers = trained_on["signers"]
        self.assertTrue(signers)
        r = self.client.get(STATUS)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["trained_on"], {"source": trained_on["source"], "n_signers": len(set(signers))})
        self.assert_no_names(r, [str(s) for s in signers])


if __name__ == "__main__":
    unittest.main()
