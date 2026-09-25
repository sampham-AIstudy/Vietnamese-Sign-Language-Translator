"""
Aspect-ratio correction in the shared preprocessing path (training dataset + live camera).

MediaPipe normalises x by frame width and y by frame height, so one physical pose yields
different normalised shapes in a 16:9 dictionary clip, a 1:1 VSL-GH clip and a 4:3 webcam.
"""
import unittest

import numpy as np

from src.data.preprocessing.pipeline import VSLPreprocessingPipeline, correct_aspect


def _pose_in_pixels(rng):
    """A plausible upper body + two hands in pixel space: shoulders ~300 px apart."""
    pts = np.zeros((20, 67, 3), dtype=np.float32)
    base = np.array([640.0, 400.0, 0.0])
    for t in range(20):
        pts[t, :25] = base + rng.normal(0, 60, size=(25, 3)) * [1, 1, 0]
        pts[t, 11] = base + [-150, 0, 0]
        pts[t, 12] = base + [150, 0, 0]
        pts[t, 25:46] = base + [-120, -80, 0] + rng.normal(0, 25, size=(21, 3)) * [1, 1, 0] + [0, 0, 5 * t]
        pts[t, 46:67] = base + [120, -80, 0] + rng.normal(0, 25, size=(21, 3)) * [1, 1, 0]
    return pts


def _normalised(pixel_pts, width, height):
    """What MediaPipe would report for a frame of width x height (z on the x scale)."""
    out = pixel_pts.copy()
    out[..., 0] /= width
    out[..., 1] /= height
    out[..., 2] /= width
    return out


class TestAspectCorrection(unittest.TestCase):
    def setUp(self):
        self.pipeline = VSLPreprocessingPipeline(target_len=20)
        self.vis = np.ones((20, 67), dtype=np.float32)
        self.px = _pose_in_pixels(np.random.default_rng(0))

    def test_default_is_unchanged(self):
        kps = _normalised(self.px, 1280, 720)
        a = self.pipeline(kps, self.vis)
        b = self.pipeline(kps, self.vis, aspect_ratio=None)
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x, y)

    def test_same_pose_different_frames_match_after_correction(self):
        # Same physical pose, centred crop into two frames with different shapes.
        wide = _normalised(self.px, 1280, 720)
        square_px = self.px.copy()
        square_px[..., 0] -= (1280 - 720) / 2
        square = _normalised(square_px, 720, 720)

        raw_a = self.pipeline(wide, self.vis)[0]
        raw_b = self.pipeline(square, self.vis)[0]
        self.assertGreater(np.abs(raw_a - raw_b).max(), 1e-2, "uncorrected inputs should differ")

        fixed_a = self.pipeline(wide, self.vis, aspect_ratio=1280 / 720)[0]
        fixed_b = self.pipeline(square, self.vis, aspect_ratio=1.0)[0]
        np.testing.assert_allclose(fixed_a, fixed_b, atol=1e-4)

    def test_nan_preserved_and_bad_ratio_rejected(self):
        kps = _normalised(self.px, 1280, 720)
        kps[3, 30] = np.nan
        out = correct_aspect(kps, 16 / 9)
        self.assertTrue(np.isnan(out[3, 30]).all())
        self.assertAlmostEqual(float(out[0, 11, 0]), float(kps[0, 11, 0] * 16 / 9), places=5)
        self.assertEqual(float(out[0, 11, 1]), float(kps[0, 11, 1]))
        for bad in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                correct_aspect(kps, bad)


if __name__ == "__main__":
    unittest.main()
