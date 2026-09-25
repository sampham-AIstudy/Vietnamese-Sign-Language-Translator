"""scripts/train_unified.assert_split_integrity: hard FAIL on QIPEDC recording leakage or VSL-GH signer leakage."""
import csv
import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
_cwd = os.getcwd()
import train_unified  # noqa: E402  (module chdirs to the project root)
os.chdir(_cwd)

MANIFEST = os.path.join(PROJECT_ROOT, "data", "splits", "unified")
FIELDS = ["video_id", "source", "signer_id", "recording_group"]


class TestUnifiedSplitIntegrity(unittest.TestCase):
    def _write(self, rows_by_split):
        tmp = tempfile.mkdtemp()
        paths = {}
        for split, rows in rows_by_split.items():
            paths[split] = os.path.join(tmp, f"{split}.csv")
            with open(paths[split], "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
        return paths

    def test_committed_unified_manifest_passes(self):
        paths = {s: os.path.join(MANIFEST, f"{s}.csv") for s in ("train", "val", "test")}
        report = train_unified.assert_split_integrity(paths)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["vslgh_signers"]["S06"], ["test"])

    def test_recording_group_in_two_splits_fails(self):
        paths = self._write({
            "train": [{"video_id": "q1", "source": "qipedc", "signer_id": "", "recording_group": "RG1"}],
            "val": [],
            "test": [{"video_id": "q2", "source": "qipedc", "signer_id": "", "recording_group": "RG1"}]})
        with self.assertRaisesRegex(RuntimeError, "recording groups in more than one split"):
            train_unified.assert_split_integrity(paths)

    def test_missing_recording_group_fails(self):
        paths = self._write({"train": [{"video_id": "q1", "source": "qipedc", "signer_id": "", "recording_group": ""}],
                             "val": [], "test": []})
        with self.assertRaisesRegex(RuntimeError, "no recording_group"):
            train_unified.assert_split_integrity(paths)

    def test_s06_in_train_fails(self):
        paths = self._write({"train": [{"video_id": "v1", "source": "vslgh", "signer_id": "S06", "recording_group": ""}],
                             "val": [], "test": []})
        with self.assertRaisesRegex(RuntimeError, "held-out VSL-GH signer"):
            train_unified.assert_split_integrity(paths)


if __name__ == "__main__":
    unittest.main()
