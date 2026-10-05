"""
Plan 15 lần sửa 6 W0: .gitattributes forces LF for the files whose sha256 is checked by tests (configs/*.json,
reports/**/*.json, reports/**/*.md, docs/**/*.md), so that those tests also pass on Windows with the Git default
core.autocrlf=true (lần sửa 6 §1 E9).

Tests:
- the four rules are in .gitattributes, each with `text eol=lf`;
- `git check-attr text eol` gives text=set, eol=lf for every tracked file under the four patterns (and the sha256-pinned
  files are among them);
- `git ls-files --eol`: none of these files is CRLF in the index (i/crlf) or in the working tree (w/crlf);
- a checkout with core.autocrlf=true (the Windows default, simulated in a temporary work tree with a temporary index,
  the repository's own index and work tree are not touched) writes the pinned files with LF only, byte-identical to the
  blob in HEAD.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

GITATTRIBUTES = os.path.join(PROJECT_ROOT, ".gitattributes")
PATTERNS = ("configs/*.json", "reports/**/*.json", "reports/**/*.md", "docs/**/*.md")
# files whose sha256 is checked by the Level 1 tests (lần sửa 6 §1 E9)
PINNED = ("configs/level1_realtime.json", "configs/level1_demo_classifier.json",
          "reports/level1_realtime_2026-10-05/SUMMARY.md",
          "reports/level1_realtime_2026-10-05/segment_check_before.json",
          "reports/level1_realtime_2026-10-05/segment_check_after.json")
TMP_PARENT = os.path.join(PROJECT_ROOT, "_work", "_plan15_tmp")


def git(*args, env=None):
    r = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, env=env)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def tracked(patterns):
    """Tracked files matching the gitattributes-style patterns (pathspec glob magic: `**/` also matches no directory)."""
    out = git("ls-files", "-z", "--", *[f":(glob){p}" for p in patterns])
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


class TestGitattributesW0(unittest.TestCase):
    def test_w0_rules_present(self):
        self.assertTrue(os.path.isfile(GITATTRIBUTES), ".gitattributes missing")
        with open(GITATTRIBUTES, encoding="utf-8") as f:
            rules = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pattern, *attrs = line.split()
                    rules[pattern] = attrs
        for p in PATTERNS:
            self.assertIn(p, rules, f"no rule for {p}")
            self.assertIn("text", rules[p], p)
            self.assertIn("eol=lf", rules[p], p)

    def test_w0_check_attr_lf_for_every_tracked_file(self):
        files = tracked(PATTERNS)
        for p in PINNED:
            self.assertIn(p, files)
        out = git("check-attr", "-z", "text", "eol", "--", *files).decode("utf-8").split("\0")
        attrs = {}
        for i in range(0, len(out) - 2, 3):
            attrs.setdefault(out[i], {})[out[i + 1]] = out[i + 2]
        bad = {f: attrs.get(f) for f in files if attrs.get(f) != {"text": "set", "eol": "lf"}}
        self.assertEqual(bad, {})

    def test_w0_ls_files_eol_no_crlf(self):
        files = tracked(PATTERNS)
        out = git("ls-files", "--eol", "--", *files).decode("utf-8").splitlines()
        self.assertEqual(len(out), len(files))
        crlf = [line for line in out if "w/crlf" in line.split("\t")[0] or "i/crlf" in line.split("\t")[0]]
        self.assertEqual(crlf, [])
        for line in out:
            self.assertIn("attr/text eol=lf", line, line)

    def test_w0_windows_autocrlf_checkout_keeps_lf(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_w0_", dir=TMP_PARENT)
        try:
            work = os.path.join(tmp, "wt")
            os.makedirs(work)
            env = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
            # global attributes file = this repo's .gitattributes (patterns relative to the top level), so the
            # simulation uses the rules being tested whether or not they are committed yet
            git("-c", "core.autocrlf=true", "-c", f"core.attributesFile={GITATTRIBUTES}", f"--work-tree={work}",
                "checkout", "HEAD", "--", *PINNED, env=env)
            for p in PINNED:
                with open(os.path.join(work, p), "rb") as f:
                    data = f.read()
                self.assertFalse(b"\r\n" in data, f"{p}: CRLF written with core.autocrlf=true")
                self.assertTrue(data == git("cat-file", "blob", f"HEAD:{p}"), f"{p}: differs from the blob in HEAD")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
