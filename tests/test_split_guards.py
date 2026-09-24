"""
Unit tests for Dataset Split Guards (P0-2).
Tests:
1. Recording-grouped splits pass all guards; legacy in-domain splits trip the duplicate-recording guard.
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
    DuplicateRecordingLeakageError,
    DEFAULT_RECORDING_GROUPS_CSV,
)


class TestSplitGuards(unittest.TestCase):

    def test_grouped_splits_pass(self):
        """The recording-grouped folds (tier1: 50, tier2: 487 classes) pass every guard incl. duplicates."""
        if not os.path.exists(DEFAULT_RECORDING_GROUPS_CSV):
            self.skipTest("recording_groups.csv not found (run scripts/build_recording_groups.py).")
        for tier, n_classes in (("tier1", 50), ("tier2", 487)):
            paths = [f"data/splits/folds/{tier}_grouped_{s}.csv" for s in ("train", "val", "test")]
            if not all(os.path.exists(p) for p in paths):
                self.skipTest(f"{tier} grouped fold CSVs not found.")
            stats = validate_split_guards(*paths, expected_num_classes=n_classes)
            self.assertEqual(stats["status"], "PASS")
            self.assertEqual(stats["duplicate_recording_check"], "PASS")
            self.assertEqual(stats["num_classes"], n_classes)
            self.assertGreater(stats["val_samples"], 0)
            self.assertGreater(stats["test_samples"], 0)

    def test_legacy_indomain_splits_leak_duplicate_recordings(self):
        """tier2_indomain_* put re-captioned copies of one clip in train and test (audit round 3)."""
        paths = [f"data/splits/folds/tier2_indomain_{s}.csv" for s in ("train", "val", "test")]
        if not os.path.exists(DEFAULT_RECORDING_GROUPS_CSV) or not all(os.path.exists(p) for p in paths):
            self.skipTest("recording_groups.csv or legacy in-domain folds not found.")
        with self.assertRaises(DuplicateRecordingLeakageError):
            validate_split_guards(*paths, expected_num_classes=487)
        stats = validate_split_guards(*paths, expected_num_classes=487, allow_duplicate_recordings=True)
        self.assertEqual(stats["duplicate_recording_check"], "DISABLED (legacy reproduction only)")

    def test_duplicate_recording_guard_triggers(self):
        """Two file names mapped to one recording group in different splits raise, even with distinct IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fields = ["video_id", "file_name", "gloss_normalized", "dialect"]
            rows = {
                "train": [{"video_id": "1", "file_name": "W1T.mp4", "gloss_normalized": "ai", "dialect": "T"},
                          {"video_id": "3", "file_name": "W2B.mp4", "gloss_normalized": "bạn", "dialect": "B"}],
                "val": [{"video_id": "4", "file_name": "W2N.mp4", "gloss_normalized": "bạn", "dialect": "N"}],
                "test": [{"video_id": "2", "file_name": "W1N.mp4", "gloss_normalized": "ai", "dialect": "N"}],
            }
            paths = {}
            for split, split_rows in rows.items():
                paths[split] = os.path.join(tmpdir, f"{split}.csv")
                with open(paths[split], "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(split_rows)
            groups = os.path.join(tmpdir, "recording_groups.csv")
            with open(groups, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["file_name", "recording_group"])
                writer.writeheader()
                writer.writerows([{"file_name": "W1T.mp4", "recording_group": "RG1"},
                                  {"file_name": "W1N.mp4", "recording_group": "RG1"},
                                  {"file_name": "W2B.mp4", "recording_group": "RG2"},
                                  {"file_name": "W2N.mp4", "recording_group": "RG3"}])
            args = (paths["train"], paths["val"], paths["test"])
            with self.assertRaises(DuplicateRecordingLeakageError):
                validate_split_guards(*args, recording_groups_csv=groups)
            stats = validate_split_guards(*args, recording_groups_csv=os.path.join(tmpdir, "missing.csv"))
            self.assertTrue(stats["duplicate_recording_check"].startswith("SKIPPED"))

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
