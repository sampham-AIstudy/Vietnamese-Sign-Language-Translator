"""src/data/harmonized.py: shapes, masks, no NaN, dropped joints, pose z, resting-hand masking, determinism."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.data.harmonized import KEEP, harmonize  # noqa: E402


def clip(T=90, rest_frames=20, seed=0):
    """Fixture (not data): shoulders at y=0.4, right hand raised in the middle, left hand resting at the hip."""
    rng = np.random.default_rng(seed)
    k = np.full((T, 67, 3), np.nan, np.float32)
    vis = np.zeros((T, 67), np.float32)
    k[:, :25] = rng.uniform(0.3, 0.7, (25, 3)); vis[:, :25] = 1   # static body
    k[:, 11, :2], k[:, 12, :2] = [0.6, 0.4], [0.4, 0.4]   # shoulder width 0.2
    k[:, 23, :2], k[:, 24, :2] = [0.58, 0.7], [0.42, 0.7]
    hand = rng.normal(0, 0.01, (21, 3)).astype(np.float32)
    t = np.arange(T)
    up = np.clip(np.minimum(t - rest_frames, T - rest_frames - t) / 10.0, 0, 1)   # smooth raise and lower
    for i in range(T):
        x = 0.4 + 0.03 * np.sin(2 * np.pi * i / T)
        k[i, 46:67] = hand + [x, 0.75 - 0.3 * up[i], 0.0]                  # right hand: hip -> raised -> hip
        k[i, 25:46] = hand + [0.6, 0.75, 0.0]                              # left hand always resting
    vis[:, 25:67] = 1
    return k, vis


class TestHarmonized(unittest.TestCase):
    def test_shapes_masks_and_dropped_joints(self):
        k, v = clip()
        seq, jm, tm = harmonize(k, v, 16 / 9, 30, {"target_len": 32})
        self.assertEqual((seq.shape, jm.shape, tm.shape), ((32, 67, 3), (32, 67), (32,)))
        self.assertTrue(np.isfinite(seq).all())
        self.assertEqual(jm[:, ~KEEP].sum(), 0)          # face, pose hand points, hips masked
        self.assertEqual(np.abs(seq[:, :25, 2]).sum(), 0)  # pose z dropped
        self.assertEqual(np.abs(seq[jm == 0]).sum(), 0)

    def test_rest_trimmed_and_resting_hand_masked(self):
        k, v = clip()
        seq, jm, _ = harmonize(k, v, 1.0, 30)
        self.assertGreater(jm[:, 46].mean(), 0.9)          # right hand kept over the (trimmed) sign
        self.assertEqual(jm[:, 25].sum(), 0)               # left hand resting at the hip -> absent
        self.assertGreater((seq[jm[:, 46] > 0, 46, 1] < 1.2).mean(), 0.6)  # raised part + fast ramps + 0.1 s pad

    def test_hand_z_drop_and_determinism(self):
        k, v = clip()
        a = harmonize(k, v, 1.0, 30)[0]
        self.assertTrue(np.array_equal(a, harmonize(k, v, 1.0, 30)[0]))
        self.assertEqual(np.abs(harmonize(k, v, 1.0, 30, {"hand_z": False})[0][..., 2]).sum(), 0)

    def test_time_resampling_ignores_frame_rate(self):
        k, v = clip(T=90)
        a, ja, _ = harmonize(k, v, 1.0, 30)
        b, jb, _ = harmonize(k[::2], v[::2], 1.0, 15)        # same motion at half the frame rate
        self.assertGreaterEqual((ja == jb).mean(), 0.9)     # masks agree except at the span edges
        both = (ja > 0) & (jb > 0)
        self.assertLess(np.abs(a - b)[both].max(), 0.25)  # fast ramp (4.5 shoulder widths/s), sub-frame grid shift

    def test_augmentation_keeps_masks_valid(self):
        k, v = clip()
        seq, jm, _ = harmonize(k, v, 1.0, 30, rng=np.random.default_rng(1))
        self.assertTrue(np.isfinite(seq).all())
        self.assertEqual(np.abs(seq[jm == 0]).sum(), 0)


if __name__ == "__main__":
    unittest.main()
