"""
Plan 05 AC11: alphabet_real_best.pt is removed from the git index (not from history, not from disk), ignored, and kept in
the verified private Kaggle dataset recorded by the latest reports/private_archive_*/kaggle_archive_manifest.json.
Reads the real repository state; a missing manifest is a FAIL (no skip).
"""
import glob
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
import archive_private_kaggle as P  # noqa: E402
import archive_step4_kaggle as A  # noqa: E402

X = "reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt"
P5 = "b337aee"
ADDED_IN = "429b289"
RESULTS = os.path.join(ROOT, "reports", "step4_2026-09-26", "step4_results.json")
PROVENANCE = os.path.join(ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return r.returncode, r.stdout


def latest_manifest():
    found = sorted(glob.glob(os.path.join(ROOT, "reports", "private_archive_*", "kaggle_archive_manifest.json")))
    return found[-1] if found else None


class TestPrivateArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = latest_manifest()
        cls.m = None
        if cls.path:
            with open(cls.path, encoding="utf-8") as f:
                cls.m = json.load(f)

    def setUp(self):
        self.assertIsNotNone(self.m, "reports/private_archive_*/kaggle_archive_manifest.json missing")

    def test_a_not_tracked(self):
        rc, out = git("--literal-pathspecs", "ls-files", "-z", "--", X)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_b_ignored(self):
        rc, _ = git("check-ignore", "-q", "--", X)
        self.assertEqual(rc, 0)

    def test_c_in_private_manifest(self):
        with open(PROVENANCE, encoding="utf-8") as f:
            pinned = json.load(f)["checkpoints"]["known.real_run"]["sha256"]
        hits = [f for f in self.m["files"] if f["local_path"] == X]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["sha256"], pinned)
        self.assertIs(self.m["dataset"]["is_private"], True)
        self.assertEqual(self.m["dataset"]["is_private_sources"], {"dataset_list_mine": True, "dataset_metadata": True})

    def test_d_no_manifest_file_tracked(self):
        paths = [f["local_path"] for f in self.m["files"]]
        rc, out = git("--literal-pathspecs", "ls-files", "-z", "--", *paths)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "", out.split("\0"))

    def test_e_manifest_matches_plan(self):
        self.assertEqual({f["local_path"] for f in self.m["files"]},
                         {f["local_path"] for f in P.plan_files(RESULTS, PROVENANCE)})

    def test_f_file_on_disk_matches(self):
        p = os.path.join(ROOT, *X.split("/"))
        if os.path.isfile(p):
            self.assertEqual(A.sha256_file(p), [f for f in self.m["files"] if f["local_path"] == X][0]["sha256"])

    def test_g_gitignore(self):
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertIn("reports/**/*.pt", lines)
        self.assertIn("reports/**/*.npz", lines)
        rc, out = git("diff", P5, "HEAD", "--", ".gitignore")
        self.assertEqual(rc, 0)
        body = [ln for ln in out.splitlines() if not ln.startswith(("+++", "---"))]
        added = [ln for ln in body if ln.startswith("+")]
        self.assertEqual(len(added), 1, added)
        self.assertTrue(added[0].startswith("+#"), added)
        self.assertEqual([ln for ln in body if ln.startswith("-")], [])

    def test_h_history_not_rewritten(self):
        rc, _ = git("merge-base", "--is-ancestor", ADDED_IN, "HEAD")
        self.assertEqual(rc, 0)
        rc, out = git("log", "--format=%h %s", "--", X)
        self.assertEqual(rc, 0)
        self.assertTrue(any(line.startswith(ADDED_IN) for line in out.splitlines()), out)
        rc, deleted = git("log", "--diff-filter=D", "--format=%h", "--", X)
        self.assertEqual(rc, 0)
        self.assertTrue(deleted.strip(), "no commit removes X from the index")


if __name__ == "__main__":
    unittest.main()
