"""
Plan 03 AC0b: the verdict rule V1..V6 of scripts/alphabet_ckpt_provenance.py (pure function
`verdict_checks`), on tiny fixture checkpoints built in memory. No real checkpoint is read here,
except the last class, which checks the committed provenance.json (a report, not a checkpoint).
"""
import copy
import json
import os
import sys
import unittest

import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import alphabet_ckpt_provenance as prov  # noqa: E402
from train_alphabet_nested import preprocessing_for  # noqa: E402

REAL, UNKNOWN = prov.REAL_DATA_VERDICT, prov.UNKNOWN_VERDICT
CLASSES = ["a", "b", "dấu sắc"]
TRAINED_ON = {"source": "hauuto", "signers": ["s1", "s2"], "clips": 10}
GOOD_REPRO = {"k": 46, "n": 46, "clips_in_csv": 46}
PROVENANCE_JSON = os.path.join(PROJECT_ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")


def weights(offset=0.0):
    return {"gru.weight": torch.tensor([1.0, 2.0, 3.0]) + offset, "fc.bias": torch.tensor([0.5, -0.25])}


def fixtures():
    """(deployed, known) shaped like the real files: primary has no preprocessing/trained_on,
    variants has them plus run-only keys, real_run has other weights."""
    meta = {"model_type": "bigru", "classes": list(CLASSES), "num_classes": 3, "input_dim": 63,
            "selected": ["bigru", 120, "frame"]}
    primary = {**meta, "state_dict": weights()}
    variants = {**meta, "state_dict": weights(), "preprocessing": preprocessing_for("frame"),
                "hparams": {"hidden_dim": 64, "num_layers": 2}, "epochs": 120, "trained_on": dict(TRAINED_ON),
                "external_qipedc": {"x": 1}, "loso4_val_top1": 1.0}
    real_run = {"model_type": "bigru", "classes": list(CLASSES), "state_dict": weights(offset=1.0),
                "preprocessing": {"aspect_correct": True}, "trained_on": dict(TRAINED_ON)}
    deployed = {k: copy.deepcopy(v) for k, v in variants.items() if k not in ("external_qipedc", "loso4_val_top1")}
    return deployed, {"nested_primary": primary, "nested_variants": variants, "real_run": real_run}


def run(deployed, known, repro=GOOD_REPRO, sha256=None):
    return prov.verdict_checks(deployed, known, repro, preprocessing_for=preprocessing_for, sha256=sha256)


class TestVerdictRule(unittest.TestCase):
    def test_a_all_checks_hold(self):
        verdict, checks, M = run(*fixtures())
        self.assertEqual(verdict, REAL)
        self.assertEqual(M, ["nested_primary", "nested_variants"])
        self.assertEqual([f"V{i}" for i in range(1, 7)], [k for k in checks if k.startswith("V")])
        self.assertTrue(all(checks[f"V{i}"]["ok"] for i in range(1, 7)))

    def test_b_extra_untraceable_keys_are_listed_by_name_only(self):
        deployed, known = fixtures()
        deployed["evaluation"] = {"zz_inner_metric": 0.123456}
        deployed["licence_note"] = "SECRET-NOTE-VALUE"
        verdict, _, _ = run(deployed, known)
        self.assertEqual(verdict, REAL)
        diff = prov.metadata_diff(deployed, known)
        self.assertEqual(diff["nested_variants"]["only_in_deployed"], {"evaluation": "dict", "licence_note": "str"})
        self.assertEqual(diff["nested_variants"]["only_in_known"], {"external_qipedc": "dict", "loso4_val_top1": "float"})
        text = json.dumps(diff)
        self.assertNotIn("SECRET-NOTE-VALUE", text)
        self.assertNotIn("0.123456", text)
        self.assertNotIn("zz_inner_metric", text)

    def test_c_one_ulp_off_is_unknown(self):
        deployed, known = fixtures()
        w = deployed["state_dict"]["gru.weight"].clone()
        w[1] = torch.nextafter(w[1], torch.tensor(float("inf")))
        deployed["state_dict"]["gru.weight"] = w
        verdict, checks, M = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V1"]["ok"])
        self.assertEqual(M, [])

    def test_d_state_dict_key_order_differs(self):
        deployed, known = fixtures()
        deployed["state_dict"] = dict(reversed(list(deployed["state_dict"].items())))
        verdict, checks, _ = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V1"]["ok"])

    def test_e_classes_same_set_other_order(self):
        deployed, known = fixtures()
        deployed["classes"] = list(reversed(CLASSES))
        verdict, checks, _ = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V2"]["ok"])

    def test_f_preprocessing_differs_in_one_field(self):
        deployed, known = fixtures()
        deployed["preprocessing"] = {**deployed["preprocessing"], "target_frames": 31}
        verdict, checks, _ = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V2"]["ok"])
        self.assertFalse(checks["V4"]["ok"])

    def test_f_v4_alone(self):
        """Only V4 fails when no K carries preprocessing but the deployed one differs from preprocessing_for."""
        deployed, known = fixtures()
        deployed["preprocessing"] = {**deployed["preprocessing"], "target_frames": 31}
        known["nested_variants"]["preprocessing"] = dict(deployed["preprocessing"])
        verdict, checks, _ = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertTrue(checks["V2"]["ok"])
        self.assertFalse(checks["V4"]["ok"])

    def test_g_matches_only_real_run(self):
        deployed, known = fixtures()
        deployed["state_dict"] = copy.deepcopy(known["real_run"]["state_dict"])
        verdict, checks, M = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V1"]["ok"])
        self.assertEqual(M, [])
        self.assertTrue(checks["V1"]["detail"]["real_run_state_dict_equal_not_counted"])

    def test_h_no_K_in_M_has_preprocessing_and_trained_on(self):
        deployed, known = fixtures()
        known["nested_variants"]["state_dict"] = weights(offset=2.0)  # M = [nested_primary] only
        verdict, checks, M = run(deployed, known)
        self.assertEqual(M, ["nested_primary"])
        self.assertEqual(verdict, UNKNOWN)
        self.assertTrue(checks["V1"]["ok"])
        self.assertFalse(checks["V3"]["ok"])

    def test_i_other_source(self):
        deployed, known = fixtures()
        deployed["trained_on"] = {**TRAINED_ON, "source": "other"}
        verdict, checks, _ = run(deployed, known)
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V5"]["ok"])

    def test_j_reproduction_must_be_complete(self):
        for name, repro in (("k = n - 1", {"k": 45, "n": 46, "clips_in_csv": 46}),
                            ("null (missing data)", None),
                            ("k null", {"k": None, "n": None, "reason": "missing: x"}),
                            ("n = 0", {"k": 0, "n": 0, "clips_in_csv": 0}),
                            ("n < clips_in_csv", {"k": 40, "n": 40, "clips_in_csv": 46})):
            with self.subTest(name):
                verdict, checks, _ = run(*fixtures(), repro=repro)
                self.assertEqual(verdict, UNKNOWN)
                self.assertFalse(checks["V6"]["ok"])

    def test_k_identical_sha256_exempts_nothing(self):
        deployed, known = fixtures()
        sha = {"deployed": "f" * 64, "nested_primary": "0" * 64, "nested_variants": "f" * 64, "real_run": "1" * 64}
        verdict, checks, _ = run(deployed, known, repro={"k": 45, "n": 46, "clips_in_csv": 46}, sha256=sha)
        self.assertEqual(checks["sha256_match_information_only"], "nested_variants")
        self.assertEqual(verdict, UNKNOWN)
        self.assertFalse(checks["V6"]["ok"])

    def test_missing_deployed_or_known_is_unknown(self):
        _, known = fixtures()
        self.assertEqual(run(None, known)[0], UNKNOWN)
        deployed, _ = fixtures()
        self.assertEqual(run(deployed, {"nested_primary": None, "nested_variants": None, "real_run": None})[0],
                         UNKNOWN)

    def test_pure_no_disk_access(self):
        from unittest import mock
        with mock.patch("builtins.open", side_effect=AssertionError("disk read")), \
                mock.patch.object(prov.torch, "load", side_effect=AssertionError("torch.load")):
            verdict, _, _ = run(*fixtures())
        self.assertEqual(verdict, REAL)


@unittest.skipUnless(os.path.exists(PROVENANCE_JSON), f"missing file: {PROVENANCE_JSON}")
class TestCommittedProvenanceJson(unittest.TestCase):
    """The committed report follows AC0': six checks, verdict consistent with them, no untraceable values."""

    @classmethod
    def setUpClass(cls):
        with open(PROVENANCE_JSON, encoding="utf-8") as f:
            cls.raw = f.read()
        cls.data = json.loads(cls.raw)

    def test_six_checks_and_consistent_verdict(self):
        checks = self.data["verdict_checks"]
        self.assertEqual(sorted(checks), [f"V{i}" for i in range(1, 7)])
        all_ok = all(c["ok"] for c in checks.values())
        self.assertEqual(self.data["verdict"], REAL if all_ok else UNKNOWN)
        self.assertEqual(self.data["M"], checks["V1"]["detail"]["M"])
        self.assertEqual(self.data["match"], self.data["sha256_match"])

    def test_metadata_diff_has_names_and_types_only(self):
        for name, diff in self.data["metadata_diff"].items():
            if diff is None:
                continue
            for side in ("only_in_deployed", "only_in_known"):
                for key, type_name in diff[side].items():
                    self.assertIsInstance(type_name, str)
                    self.assertRegex(type_name, r"^[A-Za-z_]+$")
        self.assertNotIn("internal use only", self.raw)  # licence_note value
        self.assertNotIn("nested_loso", self.raw)  # evaluation value


if __name__ == "__main__":
    unittest.main()
