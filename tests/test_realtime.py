"""
Unit test for real-time VSL video processor logic and pipeline.
"""

import sys
import os
import unittest
import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.gru_classifier import BiGRUSequenceClassifier
from src.inference.realtime_processor import VSLRealtimeVideoProcessor


class TestRealtimeProcessor(unittest.TestCase):
    def setUp(self):
        self.classes = {0: "Cảm ơn", 1: "Xin chào", 2: "Tạm biệt"}
        self.model = BiGRUSequenceClassifier(
            input_dim=201, hidden_dim=64, num_layers=1, num_classes=3
        )
        self.model.eval()
        self.processor = VSLRealtimeVideoProcessor(
            model=self.model,
            idx_to_class=self.classes,
            device=torch.device("cpu"),
            window_sec=2.0,
            confidence_threshold=0.5,
            debounce_sec=1.0,
        )

    def test_state_initialization(self):
        state = self.processor.get_state()
        self.assertEqual(state["latest_prediction"], "...")
        self.assertEqual(state["latest_confidence"], 0.0)
        self.assertEqual(state["sentence_text"], "")

    def test_update_config(self):
        self.processor.update_config(threshold=0.8, debounce=1.5, window=2.5)
        self.assertEqual(self.processor.confidence_threshold, 0.8)
        self.assertEqual(self.processor.debounce_sec, 1.5)
        self.assertEqual(self.processor.window_sec, 2.5)

    def test_sentence_management(self):
        with self.processor.lock:
            self.processor.sentence_tokens.extend(["Xin chào", "Cảm ơn"])

        state = self.processor.get_state()
        self.assertEqual(state["sentence_text"], "Xin chào Cảm ơn")

        self.processor.pop_last_word()
        state = self.processor.get_state()
        self.assertEqual(state["sentence_text"], "Xin chào")

        self.processor.clear_sentence()
        state = self.processor.get_state()
        self.assertEqual(state["sentence_text"], "")

    def test_process_bgr_frame(self):
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        annotated_frame, state = self.processor.process_bgr_frame(dummy_frame)
        self.assertEqual(annotated_frame.shape, (480, 640, 3))
        self.assertIn("latest_prediction", state)
        self.assertIn("sentence_tokens", state)


if __name__ == "__main__":
    unittest.main()
