"""
Comprehensive Unit Test Suite for VSLR Modern Deep Learning Architecture:
- Tests STGCNModel & TransformerModel forward passes with masks
- Tests KeypointAugmenter on 67-joint sequences
- Tests PreprocessingPipeline (Spatial + Temporal Normalization)
- Tests TemporalSmoother (Confidence gating, Voting, Anti-flicker)
- Tests VSLPredictor inference engine
"""

import sys
import os
import unittest
import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.data.augment import KeypointAugmenter
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline
from src.inference.smoother import TemporalSmoother
from src.inference.predictor import VSLPredictor


class TestVSLSystem(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def test_stgcn_forward_pass(self):
        """Tests ST-GCN model shape, mask integration, and zero NaNs."""
        model = STGCNModel(num_joints=67, in_channels=3, num_classes=50)
        model.eval()

        batch_size = 2
        seq = torch.randn(batch_size, 60, 67, 3)
        jmask = torch.ones(batch_size, 60, 67)
        tmask = torch.ones(batch_size, 60)

        with torch.no_grad():
            out = model(seq, joint_masks=jmask, temporal_masks=tmask)

        self.assertEqual(out.shape, (batch_size, 50))
        self.assertFalse(torch.isnan(out).any())
        self.assertFalse(torch.isinf(out).any())

    def test_transformer_forward_pass(self):
        """Tests Transformer model shape and key padding mask integration."""
        model = TransformerModel(num_joints=67, coord_dim=3, num_classes=50)
        model.eval()

        batch_size = 2
        seq = torch.randn(batch_size, 60, 67, 3)
        tmask = torch.ones(batch_size, 60)
        tmask[:, 45:] = 0.0  # Padded trailing frames

        with torch.no_grad():
            out = model(seq, temporal_masks=tmask)

        self.assertEqual(out.shape, (batch_size, 50))
        self.assertFalse(torch.isnan(out).any())
        self.assertFalse(torch.isinf(out).any())

    def test_keypoint_augmenter(self):
        """Tests KeypointAugmenter spatial and temporal transformations."""
        augmenter = KeypointAugmenter()
        seq = np.random.randn(60, 67, 3).astype(np.float32)
        jmask = np.ones((60, 67), dtype=np.float32)

        aug_seq, aug_mask = augmenter.augment_vsl_sequence(seq, jmask)
        self.assertEqual(aug_seq.shape, (60, 67, 3))
        self.assertEqual(aug_mask.shape, (60, 67))
        self.assertFalse(np.isnan(aug_seq).any())
        self.assertFalse(np.isinf(aug_seq).any())

    def test_preprocessing_pipeline(self):
        """Tests end-to-end normalization on sequence with missing frames."""
        pipeline = VSLPreprocessingPipeline(target_len=60)
        raw_kps = np.random.randn(85, 67, 3).astype(np.float32)
        vis = np.ones((85, 67), dtype=np.float32)

        # Inject some NaNs into raw keypoints
        raw_kps[10:15, 25:40, :] = np.nan
        vis[10:15, 25:40] = 0.0

        final_kps, final_jmask, tmask = pipeline(raw_kps, vis)
        self.assertEqual(final_kps.shape, (60, 67, 3))
        self.assertEqual(final_jmask.shape, (60, 67))
        self.assertEqual(tmask.shape, (60,))
        self.assertFalse(np.isnan(final_kps).any())
        self.assertFalse(np.isinf(final_kps).any())

    def test_temporal_smoother(self):
        """Tests anti-flicker temporal smoothing with confidence gating."""
        smoother = TemporalSmoother(
            confidence_threshold=0.50,
            window_size=5,
            min_consistency_count=2,
            hold_frames=10,
        )

        # 1. Low confidence prediction -> should remain IDLE
        low_pred = {"gloss": "Xin chào", "confidence": 0.30, "top5": []}
        state1 = smoother.update(low_pred, hand_detected=True)
        self.assertEqual(state1["status"], "IDLE")

        # 2. Consistent high confidence prediction -> should confirm
        high_pred = {"gloss": "Xin chào", "confidence": 0.90, "top5": []}
        for _ in range(5):
            state2 = smoother.update(high_pred, hand_detected=True)
        self.assertEqual(state2["gloss"], "Xin chào")
        self.assertTrue(state2["is_confirmed"])

    def test_vsl_predictor_smoke(self):
        """Tests loading trained ST-GCN weights and performing single prediction."""
        if not os.path.exists("checkpoints/stgcn_best.pt"):
            self.skipTest("Checkpoint checkpoints/stgcn_best.pt not found")

        predictor = VSLPredictor(model_type="stgcn", device="cpu")
        dummy_seq = np.random.randn(60, 67, 3).astype(np.float32)

        pred = predictor.predict(dummy_seq)
        self.assertIn("gloss", pred)
        self.assertIn("confidence", pred)
        self.assertIn("top5", pred)
        self.assertIn("latency_ms", pred)
        self.assertGreaterEqual(pred["confidence"], 0.0)
        self.assertLessEqual(pred["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
