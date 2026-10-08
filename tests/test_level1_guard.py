"""
Plan 15 AC-G: DoD 7 source guard for the new Level 1 desktop files, reusing the rules of
tests/test_backend_source_guard.py (that file is not modified; plan 11 owns it).

G1 = tests.test_backend_source_guard itself (run it separately; KNOWN/ALLOWED unchanged).
G2 = the static import closure of the plan 15 entry points, scanned with ALL rules: 0 findings in the files of
     plan 15; a finding in another file of the closure must be a key of the main guard's ALLOWED with the same count
     (no KNOWN_VIOLATIONS key); scripts/level1_*.py are not in the closure.
G3 = self-check: the scanner really reads the plan 15 sources (an inserted hand-typed latency is reported).

PLAN15_FILES grows step by step (B1: segmenter + core; B2: + timing; B3: + level1_demo.py as the entry point).
"""
import collections
import glob
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_backend_source_guard import (  # noqa: E402
    ALL_RULES, ALLOWED, KNOWN_VIOLATIONS, _read, finding_key, scan_source, serving_closure)

PLAN15_FILES = (
    "level1_demo.py",
    "src/inference/level1_segmenter.py",
    "src/inference/level1_core.py",
    "src/inference/level1_timing.py",
    "src/inference/level1_textbox.py",
    "src/inference/level1_display.py",
)
ENTRYPOINTS_15 = ("level1_demo.py",)


class TestLevel1Guard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = serving_closure(PROJECT_ROOT, ENTRYPOINTS_15)
        cls.findings = []
        for rel in cls.closure:
            cls.findings += scan_source(_read(os.path.join(PROJECT_ROOT, rel)), rel, ALL_RULES)

    def test_g2_closure_contains_plan15_files_and_shared_modules(self):
        for f in PLAN15_FILES:
            self.assertIn(f, self.closure)
        for f in ("src/data/alphabet_preprocessing.py", "src/inference/hand_live.py",
                  "src/inference/fingerspelling_compose.py", "src/models/alphabet_temporal.py"):
            self.assertIn(f, self.closure)
        scripts = {os.path.relpath(p, PROJECT_ROOT).replace(os.sep, "/")
                   for p in glob.glob(os.path.join(PROJECT_ROOT, "scripts", "level1_*.py"))}
        self.assertFalse(scripts & set(self.closure))

    def test_g2_no_finding_in_plan15_files(self):
        own = [f for f in self.findings if f.path in PLAN15_FILES]
        self.assertEqual(own, [], "\n".join(f"{f.path}:{f.line} {f.rule} {f.snippet}" for f in own))

    def test_g2_other_closure_files_only_allowed(self):
        other = collections.Counter(finding_key(f) for f in self.findings if f.path not in PLAN15_FILES)
        for key, count in other.items():
            self.assertNotIn(key, KNOWN_VIOLATIONS, key)
            self.assertIn(key, ALLOWED, key)
            self.assertEqual(ALLOWED[key][0], count, key)

    def test_g3_scanner_reads_the_real_file(self):
        rel = "src/inference/level1_core.py"
        text = _read(os.path.join(PROJECT_ROOT, rel))
        self.assertEqual(scan_source(text, rel, ALL_RULES), [])
        probe = text + "\nlatency_ms = 12.5\n"
        rules = [f.rule for f in scan_source(probe, rel, ALL_RULES)]
        self.assertIn("D-binding", rules)


if __name__ == "__main__":
    unittest.main()
