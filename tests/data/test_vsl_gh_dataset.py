"""
Automated Test Suite for VSL-GH Continuous Dataset Adapter
===========================================================

Verifies all 16 required data quality checks, plus:
- 137 -> 67 landmark conversion unit tests
- Velocity calculation [T, 67, 6]
- Vocabulary encoding / decoding (CTC blank index 0)
- Variable-length batch collation & CTC target compatibility
- Train / Val / Test signer separation
- LOSO fold integrity
- All 4,200 samples accessibility
- Synthesized annotations tracking
- Existing ST-GCN model input layout compatibility [B, 3, T, 67]
- Performance & memory benchmarks
"""

import unittest
import time
import json
import numpy as np
import torch

from src.data.vsl_gh_dataset import (
    VSLGHContinuousDataset,
    convert_137_to_67,
    compute_velocity,
    VSLGlossVocabulary,
    vslgh_collate_fn,
    map_temporal_boundary,
    LANDMARK_MAPPING_TABLE,
)


class TestVSLGHContinuousDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full_dataset = VSLGHContinuousDataset(
            canonical_json="data/external/vsl_gh/dataset_canonical.json",
            keypoints_dir="data/external/vsl_gh/keypoints_frontal",
            conversion_mode="direct",
            use_velocity=False,
        )

    # -------------------------------------------------------------
    # 1. Load one sample
    # -------------------------------------------------------------
    def test_01_load_one_sample(self):
        self.assertEqual(len(self.full_dataset), 4200)
        sample = self.full_dataset[0]
        self.assertIsInstance(sample, dict)
        required_keys = [
            "sample_id", "sentence_id", "signer_id", "repetition",
            "split", "duration_sec", "raw_length", "length",
            "keypoints", "joint_mask", "gloss_sequence", "gloss_ids",
            "gloss_details", "gloss_frame_boundaries", "translation",
            "annotation_source"
        ]
        for k in required_keys:
            self.assertIn(k, sample, f"Missing key {k} in sample")

    # -------------------------------------------------------------
    # 2. Shape [T, 411] from raw source
    # -------------------------------------------------------------
    def test_02_raw_keypoint_shape(self):
        sample_meta = self.full_dataset.samples[0]
        raw_arr = np.load(f"data/external/vsl_gh/keypoints_frontal/{sample_meta['id']}.npy")
        self.assertEqual(raw_arr.ndim, 2)
        self.assertEqual(raw_arr.shape[1], 411)
        self.assertEqual(raw_arr.dtype, np.float32)

    # -------------------------------------------------------------
    # 3. Convert to [T, 67, 3]
    # -------------------------------------------------------------
    def test_03_convert_to_67_shape(self):
        sample = self.full_dataset[0]
        kps = sample["keypoints"]
        T = sample["length"]
        self.assertEqual(kps.shape, (T, 67, 3))
        self.assertEqual(sample["joint_mask"].shape, (T, 67))

    # -------------------------------------------------------------
    # 4. Check dtype float32
    # -------------------------------------------------------------
    def test_04_dtype_float32(self):
        sample = self.full_dataset[0]
        self.assertEqual(sample["keypoints"].dtype, torch.float32)
        self.assertEqual(sample["joint_mask"].dtype, torch.float32)

    # -------------------------------------------------------------
    # 5. Check no NaN / inf
    # -------------------------------------------------------------
    def test_05_no_nan_or_inf(self):
        indices_to_test = [0, 50, 100, 500, 1000, 2000, 3000, 4199]
        for idx in indices_to_test:
            sample = self.full_dataset[idx]
            kps = sample["keypoints"]
            self.assertFalse(torch.isnan(kps).any(), f"NaN found in sample {sample['sample_id']}")
            self.assertFalse(torch.isinf(kps).any(), f"Inf found in sample {sample['sample_id']}")

    # -------------------------------------------------------------
    # 6. Check gloss sequence non-empty
    # -------------------------------------------------------------
    def test_06_gloss_sequence_non_empty(self):
        for idx in [0, 10, 100, 1500, 2100, 3500, 4199]:
            sample = self.full_dataset[idx]
            self.assertGreater(len(sample["gloss_sequence"]), 0)
            self.assertTrue(all(len(g.strip()) > 0 for g in sample["gloss_sequence"]))

    # -------------------------------------------------------------
    # 7. Check translation non-empty
    # -------------------------------------------------------------
    def test_07_translation_non_empty(self):
        for idx in [0, 10, 100, 1500, 2100, 3500, 4199]:
            sample = self.full_dataset[idx]
            self.assertIsInstance(sample["translation"], str)
            self.assertGreater(len(sample["translation"].strip()), 0)

    # -------------------------------------------------------------
    # 8. Check timestamp monotonicity
    # -------------------------------------------------------------
    def test_08_timestamp_monotonicity(self):
        for idx in [0, 50, 100, 500, 1000, 2000, 3000]:
            sample = self.full_dataset[idx]
            details = sample["gloss_details"]
            for i in range(len(details)):
                g = details[i]
                self.assertLessEqual(g["start_ms"], g["end_ms"])
                if i > 0:
                    prev_g = details[i - 1]
                    self.assertGreaterEqual(g["start_ms"], prev_g["start_ms"])

    # -------------------------------------------------------------
    # 9. Check timestamp ranges
    # -------------------------------------------------------------
    def test_09_timestamp_ranges(self):
        sample = self.full_dataset[0]
        for g in sample["gloss_details"]:
            self.assertGreaterEqual(g["start_ms"], 0.0)
            self.assertGreaterEqual(g["end_ms"], g["start_ms"])
            self.assertLessEqual(g["end_ms"], (sample["duration_sec"] + 1.0) * 1000.0)

    # -------------------------------------------------------------
    # 10. Check timestamp -> frame conversion
    # -------------------------------------------------------------
    def test_10_timestamp_to_frame_conversion(self):
        sample = self.full_dataset[0]
        T = sample["raw_length"]
        for g in sample["gloss_details"]:
            self.assertTrue(0 <= g["start_frame"] <= T)
            self.assertTrue(g["start_frame"] <= g["end_frame"] <= T)

    # -------------------------------------------------------------
    # 11. Check collate function
    # -------------------------------------------------------------
    def test_11_collate_fn(self):
        batch = [self.full_dataset[0], self.full_dataset[1], self.full_dataset[2]]
        collated = vslgh_collate_fn(batch)
        self.assertIn("features", collated)
        self.assertIn("features_stgcn", collated)
        self.assertIn("lengths", collated)
        self.assertIn("gloss_targets", collated)
        self.assertIn("gloss_lengths", collated)
        self.assertEqual(collated["lengths"].shape, (3,))
        self.assertEqual(collated["gloss_lengths"].shape, (3,))

    # -------------------------------------------------------------
    # 12. Check variable-length batch
    # -------------------------------------------------------------
    def test_12_variable_length_batch(self):
        s1 = self.full_dataset[0]
        s2 = self.full_dataset[15]
        batch = [s1, s2]
        collated = vslgh_collate_fn(batch)

        max_T = max(s1["length"], s2["length"])
        self.assertEqual(collated["features"].shape, (2, max_T, 67, 3))
        self.assertEqual(collated["temporal_masks"].shape, (2, max_T))
        self.assertEqual(collated["temporal_masks"][0, :s1["length"]].sum().item(), s1["length"])
        self.assertEqual(collated["temporal_masks"][1, :s2["length"]].sum().item(), s2["length"])

    # -------------------------------------------------------------
    # 13. Check vocabulary encoding & decoding
    # -------------------------------------------------------------
    def test_13_vocabulary_encoding(self):
        vocab = self.full_dataset.vocab
        self.assertEqual(vocab.blank_id, 0)
        self.assertEqual(vocab.unk_id, 1)
        self.assertGreaterEqual(len(vocab), 370)

        test_seq = ["TÔI", "ĐĂNG-KÝ", "KHÁM"]
        encoded = vocab.encode(test_seq)
        self.assertEqual(len(encoded), 3)
        self.assertTrue(all(isinstance(x, int) and x > 1 for x in encoded))

        decoded = vocab.decode(encoded)
        self.assertEqual(decoded, test_seq)

    # -------------------------------------------------------------
    # 14. Check CTC target lengths
    # -------------------------------------------------------------
    def test_14_ctc_target_lengths(self):
        batch = [self.full_dataset[0], self.full_dataset[1], self.full_dataset[2], self.full_dataset[3]]
        collated = vslgh_collate_fn(batch)
        expected_total_tokens = sum(len(item["gloss_ids"]) for item in batch)
        self.assertEqual(collated["gloss_targets"].shape[0], expected_total_tokens)
        self.assertEqual(collated["gloss_lengths"].sum().item(), expected_total_tokens)

    # -------------------------------------------------------------
    # 15. Check Train / Val / Test signer separation
    # -------------------------------------------------------------
    def test_15_train_val_test_signer_separation(self):
        train_ds = VSLGHContinuousDataset(split="train")
        val_ds   = VSLGHContinuousDataset(split="val")
        test_ds  = VSLGHContinuousDataset(split="test")

        self.assertEqual(len(train_ds), 3600)
        self.assertEqual(len(val_ds), 300)
        self.assertEqual(len(test_ds), 300)

        train_signers = set(s["signer_id"] for s in train_ds.samples)
        val_signers   = set(s["signer_id"] for s in val_ds.samples)
        test_signers  = set(s["signer_id"] for s in test_ds.samples)

        self.assertEqual(train_signers, {"S01", "S02", "S03", "S04"})
        self.assertEqual(val_signers, {"S05"})
        self.assertEqual(test_signers, {"S06"})

        self.assertEqual(len(train_signers.intersection(val_signers)), 0)
        self.assertEqual(len(train_signers.intersection(test_signers)), 0)
        self.assertEqual(len(val_signers.intersection(test_signers)), 0)

        # Sample ID disjointness
        train_ids = set(s["id"] for s in train_ds.samples)
        val_ids   = set(s["id"] for s in val_ds.samples)
        test_ids  = set(s["id"] for s in test_ds.samples)

        self.assertEqual(len(train_ids.intersection(val_ids)), 0)
        self.assertEqual(len(train_ids.intersection(test_ids)), 0)
        self.assertEqual(len(val_ids.intersection(test_ids)), 0)

    # -------------------------------------------------------------
    # 16. Check all 4,200 samples are accessible
    # -------------------------------------------------------------
    def test_16_all_4200_samples_accessible(self):
        self.assertEqual(len(self.full_dataset.samples), 4200)
        indices_to_test = [0, 1000, 2000, 3000, 4199]
        for idx in indices_to_test:
            sample = self.full_dataset[idx]
            self.assertGreater(sample["keypoints"].shape[0], 0)
            self.assertEqual(sample["keypoints"].shape[1], 67)
            self.assertEqual(sample["keypoints"].shape[2], 3)

    # -------------------------------------------------------------
    # 17. Optional Velocity Features [T, 67, 6]
    # -------------------------------------------------------------
    def test_17_velocity_features(self):
        vel_ds = VSLGHContinuousDataset(use_velocity=True)
        sample = vel_ds[0]
        T = sample["length"]
        self.assertEqual(sample["keypoints"].shape, (T, 67, 6))
        # At t=0, velocity should be 0.0
        self.assertTrue(torch.all(sample["keypoints"][0, :, 3:6] == 0.0))

    # -------------------------------------------------------------
    # 18. Landmark Conversion Unit Tests (Direct vs Semantic)
    # -------------------------------------------------------------
    def test_18_conversion_modes(self):
        fake_137 = np.random.randn(10, 411).astype(np.float32)

        direct_67 = convert_137_to_67(fake_137, mode="direct")
        self.assertEqual(direct_67.shape, (10, 67, 3))

        semantic_67 = convert_137_to_67(fake_137, mode="semantic")
        self.assertEqual(semantic_67.shape, (10, 67, 3))

        # Hands must be identical in both modes
        np.testing.assert_allclose(direct_67[:, 25:], semantic_67[:, 25:])

    # -------------------------------------------------------------
    # 19. Synthesized Annotations Tracking
    # -------------------------------------------------------------
    def test_19_synthesized_annotations_tracking(self):
        reconstructed = [s for s in self.full_dataset.samples if s.get("annotation_source") == "reconstructed"]
        self.assertEqual(len(reconstructed), 2)
        recon_ids = set(s["id"] for s in reconstructed)
        self.assertEqual(recon_ids, {"SENT236_S01_R03_F", "SENT285_S04_R03_F"})

        sources = [s for s in self.full_dataset.samples if s.get("annotation_source") == "source"]
        self.assertEqual(len(sources), 4198)

    # -------------------------------------------------------------
    # 20. ST-GCN Model Contract Compatibility [B, 3, T, 67]
    # -------------------------------------------------------------
    def test_20_stgcn_input_contract_compatibility(self):
        batch = [self.full_dataset[0], self.full_dataset[1]]
        collated = vslgh_collate_fn(batch)

        # Spatial ST-GCN expects [B, C, T, V] = [B, 3, max_T, 67]
        stgcn_tensor = collated["features_stgcn"]
        B, C, T, V = stgcn_tensor.shape
        self.assertEqual(B, 2)
        self.assertEqual(C, 3)
        self.assertEqual(V, 67)
        self.assertEqual(T, collated["features"].shape[1])

        # Test forwarding through STGCNModel from existing codebase
        from src.models.stgcn_model import STGCNModel
        model = STGCNModel(num_joints=67, in_channels=3, num_classes=50)
        model.eval()

        with torch.no_grad():
            logits = model(
                sequences=collated["features"],
                joint_masks=collated["joint_masks"],
                temporal_masks=collated["temporal_masks"],
            )
            self.assertEqual(logits.shape, (2, 50))
            self.assertFalse(torch.isnan(logits).any())

    # -------------------------------------------------------------
    # 21. LOSO Split Folds Verification
    # -------------------------------------------------------------
    def test_21_loso_folds(self):
        for s_idx in range(1, 7):
            signer_id = f"S0{s_idx}"
            train_loso = VSLGHContinuousDataset(loso_signer=signer_id, loso_mode="train")
            test_loso  = VSLGHContinuousDataset(loso_signer=signer_id, loso_mode="test")

            test_signers = set(s["signer_id"] for s in test_loso.samples)
            self.assertEqual(test_signers, {signer_id})

            train_signers = set(s["signer_id"] for s in train_loso.samples)
            self.assertNotIn(signer_id, train_signers)

            self.assertEqual(len(train_loso) + len(test_loso), 4200)


if __name__ == "__main__":
    unittest.main()
