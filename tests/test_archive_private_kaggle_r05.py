"""scripts/archive_private_kaggle.py after review 05 (docs/plans/09-don-dep-review05.md, AC3/AC4): `restore` checks every
`archive_name` against the name derived from `local_path` by the script that generated the manifest (before any
download or write), and `verify` records `code_dirty` / `code_dirty_files` in `generated_by`.

No network, no credentials: every P.main / P.restore / P.verify call below receives a fake Kaggle API
(tests.test_archive_private_kaggle.FakeApi or tests.test_archive_step4_kaggle.FakeApi). Fixtures are the small byte
strings of those two test modules, written to a temp dir outside the repo; the two committed manifests are only read.
Fixture modules are imported as modules (not their TestCase classes) so their tests are not collected twice."""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
import archive_private_kaggle as P  # noqa: E402
import archive_step4_kaggle as A  # noqa: E402
import tests.test_archive_private_kaggle as T0  # noqa: E402
import tests.test_archive_step4_kaggle as S4  # noqa: E402

PRIVATE_MANIFEST = os.path.join(ROOT, "reports", "private_archive_2026-09-28", "kaggle_archive_manifest.json")
STEP4_MANIFEST = os.path.join(ROOT, "reports", "step4_2026-09-26", "archive", "kaggle_archive_manifest.json")
REAL_RUN_BYTES = T0.A_FILES["known.real_run"][1]
DEPLOYED = T0.A_FILES["deployed"][0]
GIT_STATUS = ["git", "status", "--porcelain", "--", "scripts", "src", "tests", "backend"]
GENERATED_BY_KEYS = {"script", "command", "git_commit", "kaggle_version", "kagglesdk_version", "verified_at_utc",
                     "code_dirty", "code_dirty_files"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


def files_under(root):
    """Relative paths of every file below `root` ([] when `root` does not exist)."""
    return sorted(os.path.relpath(os.path.join(b, n), root) for b, _, ns in os.walk(root) for n in ns)


def run_restore(manifest, download_dir, api, root, only=None):
    """Exit code of P.restore with a fake API (ArchiveError -> its code); stdout swallowed."""
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return P.restore(manifest, download_dir, api, root=root, only=only)
        except A.ArchiveError as e:
            return e.code


# ------------------------------------------------------------------------------------------------ E1, E2
class TestExpectedArchiveName(unittest.TestCase):
    def test_e1_rules(self):
        self.assertEqual(P.SCRIPT, "scripts/archive_private_kaggle.py")
        self.assertEqual(P.STEP4_SCRIPT, "scripts/archive_step4_kaggle.py")
        for gen, local, want in ((P.SCRIPT, "a/b/c.pt", "a__b__c.pt"),
                                 (P.STEP4_SCRIPT, "reports/step4_x/runs/run_a/stgcn_unified_best.pt",
                                  "step4_x__runs__run_a__stgcn_unified_best.pt"),
                                 (P.STEP4_SCRIPT, "checkpoints/x.pt", "checkpoints__x.pt")):
            with self.subTest(generator=gen, local_path=local):
                self.assertEqual(P.expected_archive_name(gen, local), want)
        for gen in ("scripts/other.py", None, 123):
            with self.subTest(generator=gen):
                with self.assertRaises(A.ArchiveError) as cm:
                    P.expected_archive_name(gen, "a/b/c.pt")
                self.assertEqual(cm.exception.code, 2)

    def test_e2_committed_manifests(self):
        for path, script in ((PRIVATE_MANIFEST, P.SCRIPT), (STEP4_MANIFEST, P.STEP4_SCRIPT)):
            with self.subTest(manifest=os.path.relpath(path, ROOT)):
                m = load(path)
                self.assertEqual(m["generated_by"]["script"], script)
                self.assertGreater(len(m["files"]), 0)
                for f in m["files"]:
                    self.assertEqual(P.expected_archive_name(script, f["local_path"]), f["archive_name"],
                                     f["local_path"])
                self.assertNotIn("code_dirty", m["generated_by"])
        step4 = load(STEP4_MANIFEST)
        self.assertTrue(any(f["archive_name"] != f["local_path"].replace("/", "__") for f in step4["files"]))


# ------------------------------------------------------------------------------------------------ R1-R4 (own manifest)
class TestRestoreArchiveName(T0.Base):
    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.stage(), 0)
            self.assertEqual(self.verify(self.created_api()), 0)
        self.m = load(self.manifest)
        self.assertIn(T0.REAL_RUN, [f["local_path"] for f in self.m["files"]])
        self.assertIn(DEPLOYED, [f["local_path"] for f in self.m["files"]])

    def dirs(self, case):
        root, rdl = os.path.join(self.d, f"root_{case}"), os.path.join(self.d, f"rdl_{case}")
        self.assertFalse(os.path.exists(root))
        self.assertFalse(os.path.exists(rdl))
        return root, rdl

    def tampered(self, case, local_path, archive_name):
        """Copy of the verified manifest with `archive_name` of `local_path` replaced, written to its own file."""
        m = json.loads(json.dumps(self.m))
        hits = [f for f in m["files"] if f["local_path"] == local_path]
        self.assertEqual(len(hits), 1)
        hits[0]["archive_name"] = archive_name
        return dump(m, os.path.join(self.d, "manifests", f"{case}.json"))

    def add_to_staging(self, name, data):
        """The fake API downloads every staging file except dataset-metadata.json, so this file is 'on Kaggle'."""
        with open(os.path.join(self.staging, name), "wb") as f:
            f.write(data)

    def test_r1_bad_archive_name_exit_2_nothing_downloaded_or_written(self):
        for case in ("a", "b", "c"):
            with self.subTest(case=case):
                root, rdl = self.dirs(case)
                if case == "a":
                    self.add_to_staging("evil__copy.pt", REAL_RUN_BYTES)
                    name = "evil__copy.pt"
                elif case == "b":
                    self.put("evil_rel.bin", REAL_RUN_BYTES, root=rdl)
                    name = "../evil_rel.bin"
                else:
                    name = self.put("evil_abs.bin", REAL_RUN_BYTES, root=self.d)
                    self.assertTrue(os.path.isabs(name))
                manifest = self.tampered(f"r1{case}", T0.REAL_RUN, name)
                api = T0.FakeApi(staging=self.staging)
                self.assertEqual(run_restore(manifest, rdl, api, root), 2)
                self.assertEqual(api.calls, [])
                self.assertEqual(files_under(root), [])
                if case == "b":
                    self.assertEqual(os.listdir(rdl), ["evil_rel.bin"])
                else:
                    self.assertFalse(os.path.exists(rdl))

    def test_r2_checked_before_only_filter(self):
        self.add_to_staging("evil__copy.pt", T0.A_FILES["deployed"][1])
        manifest = self.tampered("r2", DEPLOYED, "evil__copy.pt")
        root, rdl = self.dirs("r2")
        api = T0.FakeApi(staging=self.staging)
        self.assertEqual(run_restore(manifest, rdl, api, root, only=[T0.REAL_RUN]), 2)
        self.assertEqual(api.calls, [])
        self.assertEqual(files_under(root), [])

    def test_r3_unsupported_or_missing_generator_exit_2(self):
        other = json.loads(json.dumps(self.m))
        other["generated_by"]["script"] = "scripts/other.py"
        missing = json.loads(json.dumps(self.m))
        del missing["generated_by"]
        for case, m in (("other_script", other), ("no_generated_by", missing)):
            with self.subTest(case=case):
                root, rdl = self.dirs(f"r3_{case}")
                api = T0.FakeApi(staging=self.staging)
                manifest = dump(m, os.path.join(self.d, "manifests", f"r3_{case}.json"))
                self.assertEqual(run_restore(manifest, rdl, api, root), 2)
                self.assertEqual(api.calls, [])
                self.assertEqual(files_under(root), [])

    def test_r4_cli_exit_2_message(self):
        self.add_to_staging("evil__copy.pt", REAL_RUN_BYTES)
        manifest = self.tampered("r4", T0.REAL_RUN, "evil__copy.pt")
        root, rdl = self.dirs("r4")
        api = T0.FakeApi(staging=self.staging)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = P.main(["restore", "--manifest", manifest, "--download-dir", rdl, "--root", root], api=api)
        self.assertEqual(rc, 2)
        self.assertTrue(err.getvalue().startswith("archive_private_kaggle:"), err.getvalue())
        self.assertIn(T0.REAL_RUN, err.getvalue())
        self.assertEqual(api.calls, [])
        self.assertEqual(files_under(root), [])

    def test_r5_manifest_without_code_dirty_restores(self):
        m = json.loads(json.dumps(self.m))
        self.assertIn("code_dirty", m["generated_by"])            # written by verify since plan 09
        m["generated_by"].pop("code_dirty", None)
        m["generated_by"].pop("code_dirty_files", None)
        manifest = dump(m, os.path.join(self.d, "manifests", "r5.json"))
        root, rdl = self.dirs("r5")
        self.assertEqual(run_restore(manifest, rdl, T0.FakeApi(staging=self.staging), root), 0)
        for f in m["files"]:
            self.assertEqual(A.sha256_file(os.path.join(root, *f["local_path"].split("/"))), f["sha256"])
        self.assertEqual(len(files_under(root)), len(m["files"]))


# ------------------------------------------------------------------------------------------------ R6, R7 (step-4 manifest)
class TestRestoreStep4Manifest(S4.Base):
    def setUp(self):
        super().setUp()
        self.assertFalse(A.inside(self.d))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.stage(), 0)
            self.assertEqual(self.verify(self.created_api()), 0)
        self.m = load(self.manifest)
        self.root = os.path.join(self.d, "restore_root")
        self.rdl = os.path.join(self.d, "restore_dl")

    def test_r6_step4_manifest_restores(self):
        self.assertEqual(self.m["generated_by"]["script"], P.STEP4_SCRIPT)
        self.assertTrue(any(f["archive_name"] != f["local_path"].replace("/", "__") for f in self.m["files"]))
        self.assertEqual(run_restore(self.manifest, self.rdl, S4.FakeApi(staging=self.staging), self.root), 0)
        self.assertGreater(len(self.m["files"]), 0)
        for f in self.m["files"]:
            p = os.path.join(self.root, *f["local_path"].split("/"))
            self.assertTrue(os.path.isfile(p), f["local_path"])
            self.assertEqual(A.sha256_file(p), f["sha256"])
        self.assertEqual(len(files_under(self.root)), len(self.m["files"]))

    def test_r7_step4_manifest_with_replace_rule_name_exit_2(self):
        m = json.loads(json.dumps(self.m))
        f = next(f for f in m["files"] if f["archive_name"] != f["local_path"].replace("/", "__"))
        f["archive_name"] = f["local_path"].replace("/", "__")
        manifest = dump(m, os.path.join(self.d, "manifests", "r7.json"))
        api = S4.FakeApi(staging=self.staging)
        self.assertEqual(run_restore(manifest, self.rdl, api, self.root), 2)
        self.assertEqual(api.calls, [])
        self.assertEqual(files_under(self.root), [])


# ------------------------------------------------------------------------------------------------ C1-C4 code_status
class FakeRun:
    """Stands in for subprocess.run: records (args, kwargs); returns a CompletedProcess or raises `exc`."""

    def __init__(self, returncode=0, stdout="", exc=None):
        self.returncode, self.stdout, self.exc, self.calls = returncode, stdout, exc, []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return subprocess.CompletedProcess(args[0], self.returncode, stdout=self.stdout, stderr="")


class TestCodeStatus(unittest.TestCase):
    def test_c1_clean_and_arguments(self):
        fake = FakeRun(returncode=0, stdout="")
        r = P.code_status(run=fake)
        self.assertIs(r[0], False)
        self.assertEqual(r[1], [])
        self.assertEqual(len(fake.calls), 1)
        args, kwargs = fake.calls[0]
        self.assertEqual(args[0], GIT_STATUS)
        self.assertEqual(os.path.normcase(kwargs["cwd"]), os.path.normcase(ROOT))
        self.assertIn("timeout", kwargs)

    def test_c2_dirty_lines_kept_verbatim(self):
        r = P.code_status(run=FakeRun(returncode=0, stdout=" M scripts/a.py\n?? tests/b.py\n\n"))
        self.assertEqual(r, (True, [" M scripts/a.py", "?? tests/b.py"]))
        self.assertIs(r[0], True)

    def test_c3_unknown_is_none_never_false(self):
        for case, fake in (("returncode_128", FakeRun(returncode=128, stdout="")),
                           ("FileNotFoundError", FakeRun(exc=FileNotFoundError("git"))),
                           ("TimeoutExpired", FakeRun(exc=subprocess.TimeoutExpired(GIT_STATUS, 60))),
                           ("OSError", FakeRun(exc=OSError("exec failed")))):
            with self.subTest(case=case):
                r = P.code_status(run=fake)
                self.assertIsNone(r[0])
                self.assertIsNone(r[1])

    def test_c4_real_git_consistent(self):
        r = P.code_status()
        self.assertIsInstance(r[0], bool)
        g = subprocess.run(GIT_STATUS, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(g.returncode, 0, g.stderr)
        lines = [ln for ln in g.stdout.splitlines() if ln.strip()]
        self.assertEqual(r, (bool(lines), lines))


# ------------------------------------------------------------------------------------------------ C5 verify writes it
class TestVerifyCodeDirty(T0.Base):
    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.stage(), 0)

    def test_c5_manifest_generated_by(self):
        for v in ((True, [" M scripts/x.py"]), (False, []), (None, None)):
            with self.subTest(code_status=v):
                if os.path.exists(self.manifest):
                    os.remove(self.manifest)
                with mock.patch.object(P, "code_status", return_value=v), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.verify(self.created_api()), 0)
                with open(self.manifest, encoding="utf-8") as f:
                    text = f.read()
                m = json.loads(text)
                self.assertIs(m["generated_by"]["code_dirty"], v[0])
                self.assertEqual(m["generated_by"]["code_dirty_files"], v[1])
                self.assertEqual(set(m["generated_by"]), GENERATED_BY_KEYS)
                self.assertEqual(set(m), {"generated_by", "dataset", "files", "sha256sums_file", "verified"})
                if v == (None, None):
                    self.assertIn('"code_dirty": null', text)


if __name__ == "__main__":
    unittest.main()
