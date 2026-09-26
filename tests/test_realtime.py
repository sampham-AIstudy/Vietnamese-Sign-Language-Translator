"""
Unit test for real-time VSL video inference pipeline (RealtimePipeline).
Tests frame buffering, MediaPipe integration, and buffer management without any legacy dependencies.
"""

import sys
import os
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.realtime_pipeline import RealtimePipeline


class MockPredictor:
    """Mock predictor to isolate pipeline testing from checkpoint availability."""
    def __init__(self):
        self.predict_called = False

    def predict(self, sequence, joint_mask=None, temporal_mask=None, top_k=5):
        self.predict_called = True
        return {
            "gloss": "Xin chào",
            "confidence": 0.85,
            "top5": [("Xin chào", 0.85), ("Cảm ơn", 0.10)],
            "latency_ms": 12.5,
        }


class TestRealtimePipeline(unittest.TestCase):
    def setUp(self):
        self.mock_predictor = MockPredictor()
        self.pipeline = RealtimePipeline(
            predictor=self.mock_predictor,
            target_len=60,
            min_frames=5,
            infer_interval=2,
        )

    def tearDown(self):
        self.pipeline.close()

    def test_pipeline_initialization(self):
        self.assertEqual(self.pipeline.target_len, 60)
        self.assertEqual(self.pipeline.min_frames, 5)
        self.assertEqual(self.pipeline.infer_interval, 2)
        self.assertEqual(len(self.pipeline.kps_buffer), 0)
        self.assertEqual(len(self.pipeline.vis_buffer), 0)

    def test_process_frame_buffering(self):
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        output = self.pipeline.process_frame(dummy_frame)

        self.assertIn("prediction", output)
        self.assertIn("is_new_prediction", output)
        self.assertIn("buffer_fill", output)
        self.assertIn("buffer_capacity", output)
        self.assertIn("hand_detected", output)

        self.assertEqual(output["buffer_fill"], 1)
        self.assertEqual(output["buffer_capacity"], 60)
        self.assertIsInstance(output["hand_detected"], bool)

    def test_clear_buffer(self):
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.pipeline.process_frame(dummy_frame)
        self.assertEqual(len(self.pipeline.kps_buffer), 1)

        self.pipeline.clear_buffer()
        self.assertEqual(len(self.pipeline.kps_buffer), 0)
        self.assertEqual(len(self.pipeline.vis_buffer), 0)
        self.assertEqual(self.pipeline.frame_count, 0)
        self.assertIsNone(self.pipeline.last_prediction)


if __name__ == "__main__":
    unittest.main()
