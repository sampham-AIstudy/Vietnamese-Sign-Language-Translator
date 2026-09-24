"""
Unit tests for Dataset Split Guards (P0-2).
Tests:
1. Balanced in-domain splits pass all guards (video leakage, dialect confounding, class count).
2. Confounded single-dialect split triggers DialectConfoundedError.
3. Video ID overlap between splits triggers VideoLeakageError.
4. Class count mismatch or unseen classes trigger ClassCountMismatchError.
"""

import os
import csv
import unittest
import tempfile
from src.data.vsl_dataset import (
    validate_split_guards,
    VideoLeakageError,
    DialectConfoundedError,
    ClassCountMismatchError,
)


class TestSplitGuards(unittest.TestCase):

    def test_balanced_tier2_indomain_splits_pass(self):
        """Verify that the official tier2 in-domain folds pass all integrity guards."""
        train_csv = "data/splits/folds/tier2_indomain_train.csv"
        val_csv = "data/splits/folds/tier2_indomain_val.csv"
        test_csv = "data/splits/folds/tier2_indomain_test.csv"

        if not (os.path.exists(train_csv) and os.path.exists(val_csv) and os.path.exists(test_csv)):
            self.skipTest("In-domain fold CSV files not found.")

        stats = validate_split_guards(
            train_csv=train_csv,
            val_csv=val_csv,
            test_csv=test_csv,
            expected_num_classes=487,
        )
        self.assertEqual(stats["status"], "PASS")
        self.assertEqual(stats["num_classes"], 487)
        self.assertGreater(stats["train_samples"], 0)
        self.assertGreater(stats["val_samples"], 0)
        self.assertGreater(stats["test_samples"], 0)

    def test_video_leakage_guard_triggers(self):
        """Verify VideoLeakageError is raised when identical video IDs exist in train and test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            train_path = os.path.join(tmpdir, "train.csv")
            val_path = os.path.join(tmpdir, "val.csv")
            test_path = os.path.join(tmpdir, "test.csv")

            fields = ["video_id", "gloss_normalized", "dialect"]
            with open(train_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_001", "gloss_normalized": "XIN_CHAO", "dialect": "B"})
                writer.writerow({"video_id": "vid_002", "gloss_normalized": "CAM_ON", "dialect": "N"})

            with open(val_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_003", "gloss_normalized": "XIN_CHAO", "dialect": "T"})

            # Test LEAKS video 001!
            with open(test_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_001", "gloss_normalized": "XIN_CHAO", "dialect": "B"})

            with self.assertRaises(VideoLeakageError) as ctx:
                validate_split_guards(train_path, val_path, test_path)
            self.assertIn("leaked videos", str(ctx.exception).lower())

    def test_dialect_confounding_guard_triggers(self):
        """Verify DialectConfoundedError is raised when train is 100% single dialect while test has other dialects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            train_path = os.path.join(tmpdir, "train.csv")
            val_path = os.path.join(tmpdir, "val.csv")
            test_path = os.path.join(tmpdir, "test.csv")

            fields = ["video_id", "gloss_normalized", "dialect"]
            # Train is 100% North (B)
            with open(train_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_001", "gloss_normalized": "XIN_CHAO", "dialect": "B"})
                writer.writerow({"video_id": "vid_002", "gloss_normalized": "CAM_ON", "dialect": "B"})

            with open(val_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_003", "gloss_normalized": "XIN_CHAO", "dialect": "B"})

            # Test has South (N) and Central (T)
            with open(test_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_004", "gloss_normalized": "XIN_CHAO", "dialect": "N"})
                writer.writerow({"video_id": "vid_005", "gloss_normalized": "CAM_ON", "dialect": "T"})

            with self.assertRaises(DialectConfoundedError) as ctx:
                validate_split_guards(train_path, val_path, test_path)
            self.assertIn("confounded with 100% dialect", str(ctx.exception).lower())

    def test_class_count_mismatch_guard_triggers(self):
        """Verify ClassCountMismatchError is raised when expected class count does not match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            train_path = os.path.join(tmpdir, "train.csv")
            val_path = os.path.join(tmpdir, "val.csv")
            test_path = os.path.join(tmpdir, "test.csv")

            fields = ["video_id", "gloss_normalized", "dialect"]
            with open(train_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_001", "gloss_normalized": "A", "dialect": "B"})
                writer.writerow({"video_id": "vid_002", "gloss_normalized": "B", "dialect": "N"})

            with open(val_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_003", "gloss_normalized": "A", "dialect": "B"})

            with open(test_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"video_id": "vid_004", "gloss_normalized": "B", "dialect": "N"})

            # Expect 10 classes, but train only has 2
            with self.assertRaises(ClassCountMismatchError) as ctx:
                validate_split_guards(train_path, val_path, test_path, expected_num_classes=10)
            self.assertIn("class count mismatch", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
