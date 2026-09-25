"""
Automated Test Suite for VSL Translation Core Engine
Tests:
1. VSLTranslator (ViT5) single sentence & batch translation
2. Text normalization and edge case robustness
3. CSLRRecognizer loading and landmark inference
4. VSLEndToEndTranslator unified pipeline and Lexicon Bank integration
"""

import unittest
from pathlib import Path
import numpy as np
import torch

from src.translation.text_normalizer import normalize_vsl_source, normalize_vietnamese_target
from src.translation.translator import VSLTranslator
from src.translation.cslr_recognizer import CSLRRecognizer
from src.translation.end_to_end import VSLEndToEndTranslator


class TestVSLTranslationCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[SETUP] Initializing Core Models for Testing...")
        # Use CPU or CUDA depending on availability
        cls.device = "cuda" if torch.cuda.is_available() else "cpu"
        cls.translator = VSLTranslator(device=cls.device, num_beams=2, max_length=32)
        cls.cslr = CSLRRecognizer(device=cls.device)
        cls.end_to_end = VSLEndToEndTranslator(device=cls.device)

    def test_text_normalizer(self):
        # Test lowercasing, hyphens, and whitespace
        src = normalize_vsl_source(["TÔI", "ĐĂNG-KÝ", "KHÁM", "BỆNH"])
        self.assertEqual(src, "tôi đăng ký khám bệnh")

        # Test empty input
        self.assertEqual(normalize_vsl_source(""), "")
        self.assertEqual(normalize_vsl_source([]), "")

        # Test punctuation spacing on target
        tgt = normalize_vietnamese_target("tôi đi học . ")
        self.assertEqual(tgt, "tôi đi học.")

    def test_vit5_single_translation(self):
        res = self.translator.translate(["BẠN", "TÊN", "GÌ"])
        self.assertIn("translation", res)
        self.assertGreater(len(res["translation"]), 0)
        self.assertTrue(res["latency_ms"] > 0)
        print(f"  [TEST] 'BẠN TÊN GÌ' -> '{res['translation']}' ({res['latency_ms']} ms)")

    def test_vit5_batch_translation(self):
        inputs = [
            ["TÔI", "HỌC", "SINH"],
            ["BÂY GIỜ", "MẤY", "GIỜ"],
            ["CẢM ƠN", "BẠN"],
        ]
        results = self.translator.translate_batch(inputs, batch_size=2)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertGreater(len(r["translation"]), 0)
            print(f"  [TEST BATCH] {r['source_normalized']} -> '{r['translation']}'")

    def test_vit5_edge_cases(self):
        # Empty string
        res_empty = self.translator.translate("")
        self.assertEqual(res_empty["translation"], "")

        # Single word
        res_word = self.translator.translate("CẢM-ƠN")
        self.assertGreater(len(res_word["translation"]), 0)

    def test_cslr_recognizer(self):
        # Dummy sequence: 30 frames of 67 joints
        dummy_kps = np.random.randn(30, 67, 3).astype(np.float32) * 0.1
        res = self.cslr.predict(dummy_kps)
        self.assertIn("gloss_list", res)
        self.assertIn("gloss_str", res)
        self.assertEqual(res["num_frames"], 30)
        self.assertGreater(res["latency_ms"], 0)
        print(f"  [TEST CSLR] Dummy 30 frames -> {res['gloss_list']} ({res['latency_ms']} ms)")

    def test_end_to_end_translator_glosses(self):
        res = self.end_to_end.translate_glosses(["HÔM NAY", "TRỜI", "MƯA", "TO"], attach_lexicon=True)
        self.assertGreater(len(res["translation"]), 0)
        self.assertIn("lexicon_matches", res)
        print(f"  [TEST E2E Gloss] Translation: '{res['translation']}', Lexicon matches: {list(res['lexicon_matches'].keys())}")

    def test_end_to_end_translator_keypoints(self):
        # Test with dummy keypoints array [40, 67, 3]
        dummy_kps = np.random.randn(40, 67, 3).astype(np.float32) * 0.05
        res = self.end_to_end.translate_keypoints(dummy_kps)
        self.assertIn("predicted_gloss_list", res)
        self.assertIn("translation", res)
        self.assertIn("total_latency_ms", res)
        print(f"  [TEST E2E Kps] Total latency: {res['total_latency_ms']} ms, Translation: '{res['translation']}'")

    def test_lexicon_lookup(self):
        matches = self.end_to_end.lookup_lexicon(query="mưa")
        self.assertIsInstance(matches, list)
        self.assertGreater(len(matches), 0)
        print(f"  [TEST Lexicon] Found {len(matches)} sign videos matching 'mưa'")


if __name__ == "__main__":
    unittest.main()
