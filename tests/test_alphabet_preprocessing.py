"""
Unit tests for VSL Alphabet Preprocessing Equivalence and Invariance.
"""

import unittest
import numpy as np

from src.data.alphabet_preprocessing import (
    normalize_hand_landmarks,
    extract_static_features,
    extract_sequence_features,
    preprocess_realtime_frame,
    WRIST_IDX,
    MIDDLE_MCP_IDX,
)


class TestAlphabetPreprocessing(unittest.TestCase):

    def setUp(self):
        # Create a synthetic hand with 21 landmarks
        np.random.seed(42)
        self.hand_base = np.random.randn(21, 3).astype(np.float32) * 0.1
        # Ensure wrist and middle MCP have distinct positions
        self.hand_base[WRIST_IDX] = [0.5, 0.5, 0.0]
        self.hand_base[MIDDLE_MCP_IDX] = [0.5, 0.3, 0.0]  # distance = 0.2

    def test_wrist_at_origin_and_unit_palm(self):
        norm = normalize_hand_landmarks(self.hand_base)
        # Wrist should be at origin
        np.testing.assert_allclose(norm[WRIST_IDX], [0.0, 0.0, 0.0], atol=1e-5)
        # Distance from wrist to middle MCP should be 1.0
        palm_dist = np.linalg.norm(norm[MIDDLE_MCP_IDX] - norm[WRIST_IDX])
        self.assertAlmostEqual(palm_dist, 1.0, places=5)

    def test_translation_invariance(self):
        norm_orig = normalize_hand_landmarks(self.hand_base)
        # Shift hand by large offset
        shifted = self.hand_base + np.array([12.5, -45.0, 8.2], dtype=np.float32)
        norm_shifted = normalize_hand_landmarks(shifted)
        np.testing.assert_allclose(norm_shifted, norm_orig, atol=1e-4)

    def test_scale_invariance(self):
        norm_orig = normalize_hand_landmarks(self.hand_base)
        # Scale hand by factor of 3.5
        scaled = (self.hand_base - self.hand_base[WRIST_IDX]) * 3.5 + self.hand_base[WRIST_IDX]
        norm_scaled = normalize_hand_landmarks(scaled)
        np.testing.assert_allclose(norm_scaled, norm_orig, atol=1e-4)

    def test_extract_static_features_shape(self):
        seq = np.tile(self.hand_base[np.newaxis, :, :], (105, 1, 1))
        features = extract_static_features(seq, hold_start=30, hold_end=90, strategy="median")
        self.assertEqual(features.shape, (63,))
        self.assertEqual(features.dtype, np.float32)
        # Check wrist is origin in flattened representation
        np.testing.assert_allclose(features[0:3], [0.0, 0.0, 0.0], atol=1e-5)

    def test_extract_sequence_features_shape(self):
        seq = np.tile(self.hand_base[np.newaxis, :, :], (105, 1, 1))
        features = extract_sequence_features(seq, target_frames=30, hold_start=30, hold_end=90)
        self.assertEqual(features.shape, (30, 63))
        self.assertEqual(features.dtype, np.float32)

    def test_realtime_preprocessing_equivalence(self):
        live_frame = self.hand_base.copy()
        live_out = preprocess_realtime_frame(live_frame)
        offline_out = normalize_hand_landmarks(live_frame).reshape(-1)
        np.testing.assert_allclose(live_out, offline_out, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
