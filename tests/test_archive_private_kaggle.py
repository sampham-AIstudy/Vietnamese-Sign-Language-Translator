"""scripts/archive_private_kaggle.py (docs/plans/05-thuc-thi-quyet-dinh-0928.md §3.3, AC9 cases 1-13): plan_files /
stage / upload / verify / restore with a fake Kaggle API (no network, no credentials).

Fixtures are small unit-test byte strings in a temp dir outside the repo (not report data): a fake step4_results.json
(2 untracked inputs), a fake provenance.json (deployed + 3 known.*) and a nested_predictions.csv. The "secret" strings of
case 6 are assembled at run time from harmless pieces; none is a real token."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
import archive_private_kaggle as P  # noqa: E402
import archive_step4_kaggle as A  # noqa: E402
from tests.test_archive_step4_kaggle import FakeApi as _StepFourFakeApi  # noqa: E402
from tests.test_archive_step4_kaggle import Obj  # noqa: E402

DATASET = "owner1/vslt-provenance-artifacts"
RESULTS_REAL = os.path.join(ROOT, "reports", "step4_2026-09-26", "step4_results.json")
PROVENANCE_REAL = os.path.join(ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")
S_SOURCE = "reports/step4_2026-09-26/step4_results.json#limitations_data.untracked_unarchived_inputs"
A_SOURCE = "reports/alphabet_deploy_2026-09-27/provenance.json#checkpoints."
REAL_RUN = "reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class FakeApi(_StepFourFakeApi):
    """The plan 02 fake API with this dataset ref; `list_error` makes dataset_list raise."""

    def __init__(self, list_error=False, **kw):
        kw.setdefault("create_result", Obj(status="ok", error=None, ref=DATASET, url="u"))
        super().__init__(**kw)
        self.list_error = list_error

    def dataset_list(self, **kw):
        self.calls.append(("dataset_list", kw))
        if self.list_error:
            raise RuntimeError("list failed (test)")
        visible = self.exists or self.created if self.listed is None else self.listed
        if self.list_private == "absent" or not visible:
            return [Obj(ref="owner1/other-dataset", is_private=True)]
        return [Obj(ref="owner1/other-dataset", is_private=False), Obj(ref=DATASET, is_private=self.list_private)]


S_FILES = [("reports/step4_x/runs/kernel.log", b"epoch 1 loss 0.5\n", "kernel log"),
           ("checkpoints/stgcn_unified_best.pt", b"ckpt-unified", "model of 4a")]
A_FILES = {"deployed": ("checkpoints/alphabet_best.pt", b"ckpt-deployed"),
           "known.nested_primary": ("reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt", b"np"),
           "known.nested_variants": ("reports/alphabet_nested_2026-09-25/variants/alphabet_nested_final.pt", b"nv"),
           "known.real_run": (REAL_RUN, b"ckpt-real-run")}
CSV = b"clip,pred\nc1,a\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.assertFalse(A.inside(self.d))
        self.src = os.path.join(self.d, "repo")
        self.s_entries = []
        for path, data, role in S_FILES:
            self.put(path, data)
            self.s_entries.append({"path": path, "sha256": sha(data), "role": role, "required": True})
        self.a_entries = {}
        for key, (path, data) in A_FILES.items():
            self.put(path, data)
            self.a_entries[key] = {"path": path, "exists": True, "sha256": sha(data), "size_bytes": len(data)}
        self.put(P.nested_predictions_path(), CSV)
        self.results = os.path.join(self.d, "step4_results.json")
        self.provenance = os.path.join(self.d, "provenance.json")
        self.write_json()
        self.staging = os.path.join(self.d, "staging", "vslt-provenance-artifacts")
        self.dl = os.path.join(self.d, "dl")
        self.manifest = os.path.join(self.d, "out", "kaggle_archive_manifest.json")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def put(self, rel, data, root=None):
        p = os.path.join(root or self.src, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def write_json(self, results=None, provenance=None):
        with open(self.results, "w", encoding="utf-8") as f:
            json.dump(results if results is not None else
                      {"limitations_data": {"untracked_unarchived_inputs": {"files": self.s_entries}}}, f)
        with open(self.provenance, "w", encoding="utf-8") as f:
            json.dump(provenance if provenance is not None else {"checkpoints": self.a_entries}, f)

    def code(self, fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except A.ArchiveError as e:
            return e.code

    def plan(self):
        return P.plan_files(self.results, self.provenance, src_root=self.src)

    def stage(self, staging=None):
        return self.code(P.stage, self.results, self.provenance, staging or self.staging, DATASET, src_root=self.src)

    def verify(self, api):
        return self.code(P.verify, self.staging, DATASET, self.dl, self.manifest, api, ["verify", "--x"],
                         self.results, self.provenance, src_root=self.src, poll_s=0, timeout_s=0,
                         sleep=lambda s: None)

    def created_api(self, **kw):
        api = FakeApi(staging=self.staging, **kw)
        api.created = True
        return api

    def assertNoStaging(self):
        self.assertFalse(os.path.exists(self.staging))
        parent = os.path.dirname(self.staging)
        self.assertEqual(os.listdir(parent) if os.path.isdir(parent) else [], [])


# ------------------------------------------------------------------------------------------------ plan_files (1-3)
class TestPlanFiles(Base):
    def test_01_fixture(self):
        files = self.plan()
        self.assertEqual(len(files), len(S_FILES) + len(A_FILES) + 1)
        self.assertEqual([f["archive_name"] for f in files], sorted(f["archive_name"] for f in files))
        by_path = {f["local_path"]: f for f in files}
        for f in files:
            self.assertEqual(set(f), {"group", "role", "local_path", "source", "archive_name", "expected_sha256",
                                      "expected_sha256_source", "licence_status", "licence_note"})
            self.assertEqual(f["archive_name"], f["local_path"].replace("/", "__"))
            self.assertEqual(os.path.normcase(f["source"]),
                             os.path.normcase(os.path.join(self.src, *f["local_path"].split("/"))))
        for path, data, role in S_FILES:
            f = by_path[path]
            self.assertEqual((f["group"], f["role"], f["expected_sha256"], f["expected_sha256_source"]),
                             ("step4_untracked_input", role, sha(data), S_SOURCE))
            self.assertEqual((f["licence_status"], f["licence_note"]), ("redistribution_not_stated", P.LICENCE_NOTE_S))
        for key, (path, data) in A_FILES.items():
            f = by_path[path]
            self.assertEqual((f["group"], f["role"], f["expected_sha256"], f["expected_sha256_source"]),
                             ("alphabet_provenance", key, sha(data), A_SOURCE + key))
            self.assertEqual((f["licence_status"], f["licence_note"]), ("unknown", P.LICENCE_NOTE_A))
        f = by_path[P.nested_predictions_path()]
        self.assertEqual((f["group"], f["role"], f["expected_sha256"], f["expected_sha256_source"]),
                         ("alphabet_provenance", "nested_predictions (V6)", None, None))
        self.assertEqual((f["licence_status"], f["licence_note"]), ("unknown", P.LICENCE_NOTE_A))
        self.assertIn("hauuto", P.LICENCE_NOTE_A)
        self.assertIn("QIPEDC", P.LICENCE_NOTE_S)

    def test_02_real_json(self):
        with open(RESULTS_REAL, encoding="utf-8") as f:
            s_list = json.load(f)["limitations_data"]["untracked_unarchived_inputs"]["files"]
        with open(PROVENANCE_REAL, encoding="utf-8") as f:
            ckpts = json.load(f)["checkpoints"]
        files = P.plan_files(RESULTS_REAL, PROVENANCE_REAL)
        self.assertEqual(len(files), len(s_list) + len(ckpts) + 1)
        expected_paths = {e["path"] for e in s_list} | {v["path"] for v in ckpts.values()} | \
            {P.nested_predictions_path()}
        self.assertEqual({f["local_path"] for f in files}, expected_paths)
        for p in (REAL_RUN, "reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt",
                  "reports/alphabet_nested_2026-09-25/variants/alphabet_nested_final.pt",
                  "reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv", "checkpoints/alphabet_best.pt"):
            self.assertIn(p, {f["local_path"] for f in files})
        self.assertEqual(P.nested_predictions_path(), "reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv")
        by_path = {f["local_path"]: f for f in files}
        for e in s_list:
            self.assertEqual(by_path[e["path"]]["expected_sha256"], e["sha256"])
            self.assertEqual(by_path[e["path"]]["group"], "step4_untracked_input")
        for key, v in ckpts.items():
            self.assertEqual(by_path[v["path"]]["expected_sha256"], v["sha256"])
            self.assertEqual(by_path[v["path"]]["role"], key)
        self.assertEqual(by_path[REAL_RUN]["expected_sha256"], ckpts["known.real_run"]["sha256"])

    def test_03_invalid_inputs_exit_2(self):
        cases = {}
        a = json.loads(json.dumps(self.a_entries))
        a["known.nested_primary"]["exists"] = False
        cases["exists_false"] = (None, {"checkpoints": a})
        a = json.loads(json.dumps(self.a_entries))
        del a["known.real_run"]["sha256"]
        cases["missing_sha256"] = (None, {"checkpoints": a})
        a = json.loads(json.dumps(self.a_entries))
        a["deployed"]["path"] = S_FILES[1][0]
        a["deployed"]["sha256"] = sha(S_FILES[1][1])
        cases["duplicate_between_groups"] = (None, {"checkpoints": a})
        for bad in ("C:/abs/x.pt", "/abs/x.pt", "reports/../x.pt", "../x.pt"):
            s = json.loads(json.dumps(self.s_entries))
            s[0]["path"] = bad
            cases[f"path {bad}"] = ({"limitations_data": {"untracked_unarchived_inputs": {"files": s}}}, None)
        cases["untracked_missing"] = ({"limitations_data": {}}, None)
        cases["untracked_empty"] = ({"limitations_data": {"untracked_unarchived_inputs": {"files": []}}}, None)
        cases["checkpoints_missing"] = (None, {})
        for name, (results, provenance) in cases.items():
            with self.subTest(case=name):
                self.write_json(results, provenance)
                self.assertEqual(self.code(self.plan), 2)
        self.write_json()
        self.assertEqual(self.code(P.plan_files, os.path.join(self.d, "nope.json"), self.provenance,
                                   src_root=self.src), 2)


# ------------------------------------------------------------------------------------------------ stage (4-7)
class TestStage(Base):
    def test_04_stage_success(self):
        self.assertEqual(self.stage(), 0)
        files = self.plan()
        self.assertEqual(sorted(os.listdir(self.staging)),
                         sorted([f["archive_name"] for f in files] + ["SHA256SUMS", "dataset-metadata.json"]))
        with open(os.path.join(self.staging, "dataset-metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIs(meta["isPrivate"], True)
        self.assertEqual(meta["id"], DATASET)
        self.assertEqual(meta["licenses"], [{"name": "unknown"}])
        self.assertEqual(meta["title"], "VSLT provenance evidence and untracked inputs")
        sums = A.parse_sums(os.path.join(self.staging, "SHA256SUMS"))
        self.assertEqual(set(sums), {f["archive_name"] for f in files})
        for n, h in sums.items():
            self.assertEqual(h, A.sha256_file(os.path.join(self.staging, n)))
        csv_name = P.nested_predictions_path().replace("/", "__")
        self.assertIsNotNone(sums.get(csv_name))
        self.assertEqual(sums[csv_name], sha(CSV))

    def test_05a_source_sha_mismatch_exit_3(self):
        self.a_entries["deployed"]["sha256"] = "0" * 64
        self.write_json()
        self.assertEqual(self.stage(), 3)
        self.assertNoStaging()

    def test_05b_missing_source_exit_2(self):
        os.remove(os.path.join(self.src, *P.nested_predictions_path().split("/")))
        self.assertEqual(self.stage(), 2)
        self.assertNoStaging()

    def test_05c_staging_inside_repo_exit_2(self):
        inside = os.path.join(ROOT, "_archive_private_test_staging_should_not_exist")
        self.assertEqual(self.stage(inside), 2)
        self.assertFalse(os.path.exists(inside))

    def test_05d_staging_exists_exit_2(self):
        os.makedirs(self.staging)
        self.assertEqual(self.stage(), 2)
        self.assertEqual(os.listdir(self.staging), [])
        self.assertEqual(os.listdir(os.path.dirname(self.staging)), ["vslt-provenance-artifacts"])

    def secrets(self):
        """(pattern name, text) built at run time; every text matches exactly the named pattern's regex."""
        return [("kaggle_token", "KGAT" + "_" + "abc123"),
                ("json_key", '{"username": "u", "' + "key" + '": "' + "0" * 8 + '"}'),
                ("kaggle_key_env", "KAGGLE" + "_KEY=" + "x"),
                ("api_key", "api" + "_key = " + "x"),
                ("token_assign", "auth" + "_token: " + "x"),
                ("github_token", "gh" + "p_" + "A" * 20),
                ("hf_token", "h" + "f_" + "B" * 20)]

    def test_06_secret_scan(self):
        self.assertEqual({n for n, _ in self.secrets()}, set(P.SECRET_PATTERNS))
        log_path, _, _ = S_FILES[0]
        for name, text in self.secrets():
            with self.subTest(pattern=name):
                data = ("step 1\n" + text + "\nstep 2\n").encode("utf-8")
                self.put(log_path, data)
                self.s_entries[0]["sha256"] = sha(data)
                self.write_json()
                err = io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    rc = P.main(["stage", "--results", self.results, "--provenance", self.provenance,
                                 "--staging", self.staging, "--dataset", DATASET], src_root=self.src)
                self.assertEqual(rc, 2)
                self.assertNoStaging()
                self.assertIn(log_path, err.getvalue())
                self.assertIn(name, err.getvalue())
                self.assertNotIn(text, err.getvalue())
        clean = b"epoch 1 loss 0.5\n"
        self.put(log_path, clean)
        self.s_entries[0]["sha256"] = sha(clean)
        pt_path, _ = A_FILES["deployed"]
        pt = b"\x80\x02" + b"KGAT_x" + b"\x00"                       # binary: not scanned
        self.put(pt_path, pt)
        self.a_entries["deployed"]["sha256"] = sha(pt)
        self.write_json()
        self.assertEqual(self.stage(), 0)

    def test_07_total_size_limit_exit_2(self):
        total = sum(os.path.getsize(f["source"]) for f in self.plan())
        with mock.patch.object(P, "MAX_TOTAL_BYTES", total - 1):
            self.assertEqual(self.stage(), 2)
        self.assertNoStaging()
        self.assertEqual(P.MAX_TOTAL_BYTES, 2 * 1024 ** 3)


# ------------------------------------------------------------------------------------------------ upload (8)
class TestUpload(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage(), 0)

    def test_08a_reuses_step4_upload(self):
        self.assertIs(P.upload, A.upload)
        api = FakeApi(staging=self.staging)
        with mock.patch.object(A, "upload", wraps=A.upload) as spy, contextlib.redirect_stdout(io.StringIO()):
            rc = P.main(["upload", "--staging", self.staging, "--dataset", DATASET], api=api)
        self.assertEqual(rc, 0)
        spy.assert_called_once_with(self.staging, DATASET, api)
        creates = [c for c in api.calls if c[0] == "dataset_create_new"]
        self.assertEqual(len(creates), 1)
        self.assertIs(creates[0][1]["public"], False)

    def test_08b_existing_slug_exit_5(self):
        api = FakeApi(staging=self.staging, exists=True)
        with contextlib.redirect_stderr(io.StringIO()):
            rc = P.main(["upload", "--staging", self.staging, "--dataset", DATASET], api=api)
        self.assertEqual(rc, 5)
        self.assertNotIn("dataset_create_new", api.names())

    def test_08c_metadata_not_private_exit_2(self):
        p = os.path.join(self.staging, "dataset-metadata.json")
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        m["isPrivate"] = False
        with open(p, "w", encoding="utf-8") as f:
            json.dump(m, f)
        api = FakeApi(staging=self.staging)
        with contextlib.redirect_stderr(io.StringIO()):
            rc = P.main(["upload", "--staging", self.staging, "--dataset", DATASET], api=api)
        self.assertEqual(rc, 2)
        self.assertNotIn("dataset_create_new", api.names())


# ------------------------------------------------------------------------------------------------ verify (9-10)
class TestVerify(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage(), 0)

    def assertNoManifest(self):
        self.assertFalse(os.path.exists(self.manifest))
        self.assertFalse(os.path.exists(self.manifest + ".tmp"))

    def test_09_success_manifest(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.verify(self.created_api()), 0)
        with open(self.manifest, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(set(m), {"generated_by", "dataset", "files", "sha256sums_file", "verified"})
        self.assertIs(m["dataset"]["is_private"], True)
        self.assertEqual(m["dataset"]["is_private_sources"], {"dataset_list_mine": True, "dataset_metadata": True})
        self.assertEqual(m["dataset"]["ref"], DATASET)
        self.assertEqual(m["dataset"]["status"], "ready")
        files = self.plan()
        self.assertEqual(m["verified"]["n_files"], len(files))
        self.assertEqual(len(m["files"]), len(files))
        self.assertTrue(m["verified"]["file_list_matches"])
        self.assertTrue(m["verified"]["downloaded_sha256_all_match"])
        for f in m["files"]:
            self.assertEqual(set(f), {"group", "role", "local_path", "archive_name", "size_bytes", "sha256",
                                      "sha256_after_download", "expected_sha256_source", "licence_status",
                                      "licence_note"})
            self.assertEqual(f["sha256_after_download"], f["sha256"])
            with open(os.path.join(self.src, *f["local_path"].split("/")), "rb") as fh:
                self.assertEqual(f["sha256"], sha(fh.read()))
        self.assertEqual(m["generated_by"]["script"], "scripts/archive_private_kaggle.py")
        self.assertTrue(m["generated_by"]["command"].startswith("python scripts/archive_private_kaggle.py verify"))

    def test_10a_not_private_exit_4(self):
        for name, api in (("list_not_private", self.created_api(list_private=False)),
                          ("metadata_not_private", self.created_api(meta_info={"isPrivate": False})),
                          ("list_error", self.created_api(list_error=True))):
            with self.subTest(case=name):
                self.assertEqual(self.verify(api), 4)
                self.assertNoManifest()

    def test_10b_remote_list_differs_exit_3(self):
        r = {n: os.path.getsize(os.path.join(self.staging, n)) for n in os.listdir(self.staging)
             if n != "dataset-metadata.json"}
        del r["checkpoints__alphabet_best.pt"]
        self.assertEqual(self.verify(self.created_api(remote_override=r)), 3)
        self.assertNoManifest()

    def test_10c_download_tampered_exit_3(self):
        self.assertEqual(self.verify(self.created_api(download_tamper="checkpoints__alphabet_best.pt")), 3)
        self.assertNoManifest()

    def test_10d_not_ready_exit_6(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.verify(self.created_api(status_after="pending")), 6)
        self.assertNoManifest()

    def test_10e_manifest_inside_repo_must_use_dated_path(self):
        bad = os.path.join(ROOT, "reports", "private_archive_test_should_not_exist", "kaggle_archive_manifest.json")
        api = self.created_api()
        rc = self.code(P.verify, self.staging, DATASET, self.dl, bad, api, ["verify"], self.results,
                       self.provenance, src_root=self.src, poll_s=0, timeout_s=0, sleep=lambda s: None)
        self.assertEqual(rc, 2)
        self.assertEqual(api.calls, [])
        self.assertFalse(os.path.exists(os.path.dirname(bad)))


# ------------------------------------------------------------------------------------------------ restore (11)
class TestRestore(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage(), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.verify(self.created_api()), 0)
        with open(self.manifest, encoding="utf-8") as f:
            self.m = json.load(f)
        self.root = os.path.join(self.d, "restore_root")
        self.rdl = os.path.join(self.d, "restore_dl")

    def restore(self, api=None, root="default", only=None, download_dir=None):
        api = api or FakeApi(staging=self.staging)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = self.code(P.restore, self.manifest, download_dir or self.rdl, api,
                           root=self.root if root == "default" else root, only=only)
        return rc, out.getvalue()

    def snapshot(self):
        out = {}
        for base, _, names in os.walk(self.root):
            for n in names:
                p = os.path.join(base, n)
                with open(p, "rb") as f:
                    out[os.path.relpath(p, self.root)] = (f.read(), os.stat(p).st_mtime_ns)
        return out

    def test_11a_writes_missing_files(self):
        rc, _ = self.restore()
        self.assertEqual(rc, 0)
        for f in self.m["files"]:
            p = os.path.join(self.root, *f["local_path"].split("/"))
            self.assertEqual(A.sha256_file(p), f["sha256"])
        self.assertEqual(len(self.snapshot()), len(self.m["files"]))

    def test_11b_existing_same_sha_untouched(self):
        self.assertEqual(self.restore()[0], 0)
        before = self.snapshot()
        rc, out = self.restore()
        self.assertEqual(rc, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(out.count("đã có"), len(self.m["files"]))

    def test_11c_existing_other_sha_exit_3_nothing_written(self):
        self.put(REAL_RUN, b"something else", root=self.root)
        rc, _ = self.restore()
        self.assertEqual(rc, 3)
        self.assertEqual(list(self.snapshot()), [os.path.join(*REAL_RUN.split("/"))])
        with open(os.path.join(self.root, *REAL_RUN.split("/")), "rb") as f:
            self.assertEqual(f.read(), b"something else")

    def test_11d_downloaded_tampered_exit_3_nothing_written(self):
        rc, _ = self.restore(api=FakeApi(staging=self.staging, download_tamper="checkpoints__alphabet_best.pt"))
        self.assertEqual(rc, 3)
        self.assertEqual(self.snapshot(), {})

    def test_11e_only(self):
        rc, _ = self.restore(only=[REAL_RUN])
        self.assertEqual(rc, 0)
        self.assertEqual(list(self.snapshot()), [os.path.join(*REAL_RUN.split("/"))])
        rc, _ = self.restore(only=["checkpoints/not_in_manifest.pt"])
        self.assertEqual(rc, 2)

    def test_11f_paths_inside_repo_exit_2(self):
        inside = os.path.join(ROOT, "_archive_private_test_should_not_exist")
        self.assertEqual(self.restore(download_dir=inside)[0], 2)
        self.assertEqual(self.restore(root=inside)[0], 2)
        self.assertFalse(os.path.exists(inside))


# ------------------------------------------------------------------------------------------------ guards (12-13)
class TestSourceGuard(unittest.TestCase):
    def test_12_forbidden_calls_absent(self):
        with open(os.path.join(ROOT, "scripts", "archive_private_kaggle.py"), encoding="utf-8") as f:
            src = f.read()
        for bad in ("public=True", '"--public"', "dataset_metadata_update", "dataset_delete", "dataset_create_version",
                    "metadata --update"):
            self.assertNotIn(bad, src, bad)

    def test_13_step4_script_unchanged(self):
        import subprocess
        r = subprocess.run(["git", "diff", "--name-only", "b337aee", "--", "scripts/archive_step4_kaggle.py"],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
