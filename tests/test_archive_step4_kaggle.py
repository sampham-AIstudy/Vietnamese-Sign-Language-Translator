"""scripts/archive_step4_kaggle.py (docs/plans/02-don-dep-sau-4c.md, AC1 cases 1-13): stage / upload / verify with a
fake Kaggle API (no network, no credentials).

Fixtures are small unit-test byte strings in a temp dir (not report data): a fake step4_results.json with 2 runs."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import archive_step4_kaggle as A  # noqa: E402

DATASET = "owner1/vslt-step4-artifacts"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class HttpError(Exception):
    """Mimics requests.HTTPError (the attribute read by the script is response.status_code)."""

    def __init__(self, code):
        super().__init__(f"{code} Client Error")
        self.response = Obj(status_code=code)


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeApi:
    """Records calls. `exists` controls dataset_status before creation; after create the status is `status_after`."""

    def __init__(self, staging=None, exists=False, create_result=None, status_after="ready", list_private=True,
                 meta_info=None, remote_override=None, pages=1, download_tamper=None, absent_code=404, listed=None):
        self.calls = []
        self.absent_code, self.listed = absent_code, listed
        self.staging, self.exists, self.created = staging, exists, False
        self.create_result = create_result or Obj(status="ok", error=None, ref=DATASET, url="u")
        self.status_after, self.list_private = status_after, list_private
        self.meta_info = {"isPrivate": True} if meta_info is None else meta_info
        self.remote_override, self.pages, self.download_tamper = remote_override, pages, download_tamper

    def dataset_status(self, dataset):
        self.calls.append(("dataset_status", dataset))
        if self.exists or self.created:
            return self.status_after if self.created else "ready"
        raise HttpError(self.absent_code)

    def dataset_create_new(self, **kw):
        self.calls.append(("dataset_create_new", kw))
        self.created = True
        return self.create_result

    def dataset_list(self, **kw):
        self.calls.append(("dataset_list", kw))
        visible = self.exists or self.created if self.listed is None else self.listed
        if self.list_private == "absent" or not visible:
            return [Obj(ref="owner1/other-dataset", is_private=True)]
        return [Obj(ref="owner1/other-dataset", is_private=False), Obj(ref=DATASET, is_private=self.list_private)]

    def dataset_metadata(self, dataset, path):
        self.calls.append(("dataset_metadata", dataset))
        p = os.path.join(path, "dataset-metadata.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"id": dataset, "info": self.meta_info}, f)
        return p

    def _remote(self):
        if self.remote_override is not None:
            return dict(self.remote_override)
        return {n: os.path.getsize(os.path.join(self.staging, n)) for n in os.listdir(self.staging)
                if n != "dataset-metadata.json"}

    def dataset_list_files(self, dataset, page_token=None, page_size=20):
        self.calls.append(("dataset_list_files", page_token))
        items = sorted(self._remote().items())
        chunks = [items[i::self.pages] for i in range(self.pages)]
        i = 0 if page_token is None else int(page_token)
        nxt = str(i + 1) if i + 1 < self.pages else None
        return Obj(files=[Obj(name=n, total_bytes=s) for n, s in chunks[i]], next_page_token=nxt, error_message=None)

    def dataset_download_files(self, dataset, path=None, unzip=False, **kw):
        self.calls.append(("dataset_download_files", path, unzip))
        for n in os.listdir(self.staging):
            if n != "dataset-metadata.json":
                shutil.copy2(os.path.join(self.staging, n), os.path.join(path, n))
        if self.download_tamper:
            with open(os.path.join(path, self.download_tamper), "ab") as f:
                f.write(b"x")

    def names(self):
        return [c[0] for c in self.calls]


class Base(unittest.TestCase):
    RUNS = {"R-a": "reports/step4_x/runs/run_a", "R-b": "reports/unified_y/run"}

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.src = os.path.join(self.d, "repo")
        runs = {}
        for i, (name, rd) in enumerate(self.RUNS.items()):
            p = os.path.join(self.src, *rd.split("/"))
            os.makedirs(p)
            ck, lg = f"ckpt-{i}".encode(), f"logits-{i}".encode()
            with open(os.path.join(p, "stgcn_unified_best.pt"), "wb") as f:
                f.write(ck)
            with open(os.path.join(p, "test_logits.npz"), "wb") as f:
                f.write(lg)
            runs[name] = {"dir": rd, "sha256_ckpt": sha(ck), "sha256_test_logits": sha(lg)}
        self.results = os.path.join(self.d, "step4_results.json")
        self.write_results(runs)
        self.runs = runs
        self.staging = os.path.join(self.d, "staging", "vslt-step4-artifacts")
        self.dl = os.path.join(self.d, "dl")
        self.manifest = os.path.join(self.d, "out", "kaggle_archive_manifest.json")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write_results(self, runs):
        with open(self.results, "w", encoding="utf-8") as f:
            json.dump({"provenance": {"runs": runs}}, f)

    def code(self, fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except A.ArchiveError as e:
            return e.code

    def stage(self, staging=None):
        return self.code(A.stage, self.results, staging or self.staging, DATASET, src_root=self.src)

    def upload(self, api):
        return self.code(A.upload, self.staging, DATASET, api)

    def verify(self, api):
        return self.code(A.verify, self.staging, DATASET, self.dl, self.manifest, api, ["verify", "--x"], self.results,
                         src_root=self.src, poll_s=0, timeout_s=0, sleep=lambda s: None)

    def created_api(self, **kw):
        api = FakeApi(staging=self.staging, **kw)
        api.created = True
        return api


# ------------------------------------------------------------------------------------------------ stage (1-3)
class TestStage(Base):
    def test_01_stage_success_deterministic(self):
        self.assertEqual(self.stage(), 0)
        names = sorted(os.listdir(self.staging))
        data = ["step4_x__runs__run_a__stgcn_unified_best.pt", "step4_x__runs__run_a__test_logits.npz",
                "unified_y__run__stgcn_unified_best.pt", "unified_y__run__test_logits.npz"]
        self.assertEqual(names, sorted(data + ["SHA256SUMS", "dataset-metadata.json"]))
        with open(os.path.join(self.staging, "SHA256SUMS"), "rb") as f:
            sums1 = f.read()
        lines = sums1.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 4)
        for line in lines:
            h, n = line.split("  ")
            with open(os.path.join(self.staging, n), "rb") as f:
                self.assertEqual(h, hashlib.sha256(f.read()).hexdigest())
        with open(os.path.join(self.staging, "dataset-metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIs(meta["isPrivate"], True)
        self.assertEqual(meta["id"], DATASET)
        self.assertEqual(meta["licenses"], [{"name": "unknown"}])
        second = os.path.join(self.d, "staging2", "vslt-step4-artifacts")
        self.assertEqual(self.stage(second), 0)
        self.assertEqual(sorted(os.listdir(second)), names)
        with open(os.path.join(second, "SHA256SUMS"), "rb") as f:
            self.assertEqual(f.read(), sums1)

    def test_02_source_sha_mismatch_exit_3_no_staging(self):
        self.runs["R-a"]["sha256_ckpt"] = "0" * 64
        self.write_results(self.runs)
        self.assertEqual(self.stage(), 3)
        self.assertFalse(os.path.exists(self.staging))
        parent = os.path.dirname(self.staging)
        self.assertEqual(os.listdir(parent) if os.path.isdir(parent) else [], [])

    def test_03a_staging_inside_repo_exit_2(self):
        inside = os.path.join(A.ROOT, "_archive_test_staging_should_not_exist")
        self.assertEqual(self.stage(inside), 2)
        self.assertFalse(os.path.exists(inside))

    def test_03b_missing_source_exit_2(self):
        os.remove(os.path.join(self.src, "reports", "unified_y", "run", "test_logits.npz"))
        self.assertEqual(self.stage(), 2)
        self.assertFalse(os.path.exists(self.staging))


# ------------------------------------------------------------------------------------------------ upload (4-8)
class TestUpload(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage(), 0)

    def test_04_create_called_once_private(self):
        api = FakeApi(staging=self.staging)
        self.assertEqual(self.upload(api), 0)
        creates = [c for c in api.calls if c[0] == "dataset_create_new"]
        self.assertEqual(len(creates), 1)
        kw = creates[0][1]
        self.assertIs(kw["public"], False)
        self.assertEqual(kw["dir_mode"], "skip")
        self.assertEqual(kw["folder"], self.staging)

    def test_05_existing_slug_exit_5_no_create(self):
        api = FakeApi(staging=self.staging, exists=True)
        self.assertEqual(self.upload(api), 5)
        self.assertNotIn("dataset_create_new", api.names())

    def test_05b_status_403_and_not_listed_creates(self):
        # kaggle 2.2.4 answers 403 for a slug absent from the caller's account; dataset_list(mine) confirms absence
        api = FakeApi(staging=self.staging, absent_code=403)
        self.assertEqual(self.upload(api), 0)
        self.assertEqual(api.names().count("dataset_create_new"), 1)

    def test_05c_status_403_but_listed_exit_5_no_create(self):
        api = FakeApi(staging=self.staging, absent_code=403, listed=True)
        self.assertEqual(self.upload(api), 5)
        self.assertNotIn("dataset_create_new", api.names())

    def test_05d_status_other_http_error_exit_6_no_create(self):
        api = FakeApi(staging=self.staging, absent_code=401)
        self.assertEqual(self.upload(api), 6)
        self.assertNotIn("dataset_create_new", api.names())

    def set_meta(self, **kw):
        p = os.path.join(self.staging, "dataset-metadata.json")
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        m.update(kw)
        for k in [k for k, v in kw.items() if v is Ellipsis]:
            del m[k]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(m, f)

    def test_06_metadata_not_private_exit_2(self):
        for value in (Ellipsis, False, "true"):
            with self.subTest(isPrivate=value):
                self.set_meta(isPrivate=value)
                api = FakeApi(staging=self.staging)
                self.assertEqual(self.upload(api), 2)
                self.assertNotIn("dataset_create_new", api.names())

    def test_07a_modified_staging_file_exit_3(self):
        with open(os.path.join(self.staging, "unified_y__run__test_logits.npz"), "ab") as f:
            f.write(b"!")
        api = FakeApi(staging=self.staging)
        self.assertEqual(self.upload(api), 3)
        self.assertNotIn("dataset_create_new", api.names())

    def test_07b_extra_staging_file_exit_3(self):
        with open(os.path.join(self.staging, "extra.bin"), "wb") as f:
            f.write(b"extra")
        api = FakeApi(staging=self.staging)
        self.assertEqual(self.upload(api), 3)
        self.assertNotIn("dataset_create_new", api.names())

    def test_08_api_error_status_exit_6(self):
        api = FakeApi(staging=self.staging, create_result=Obj(status="error", error="title in use"))
        self.assertEqual(self.upload(api), 6)


# ------------------------------------------------------------------------------------------------ verify (9-12)
class TestVerify(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.stage(), 0)

    def assertNoManifest(self):
        self.assertFalse(os.path.exists(self.manifest))

    def test_09a_list_not_private_exit_4(self):
        self.assertEqual(self.verify(self.created_api(list_private=False)), 4)
        self.assertNoManifest()

    def test_09b_metadata_not_private_or_missing_exit_4(self):
        for info in ({"isPrivate": False}, {"title": "x"}):
            with self.subTest(info=info):
                self.assertEqual(self.verify(self.created_api(meta_info=info)), 4)
                self.assertNoManifest()

    def test_09c_dataset_not_in_list_exit_4(self):
        self.assertEqual(self.verify(self.created_api(list_private="absent")), 4)
        self.assertNoManifest()

    def remote(self):
        return {n: os.path.getsize(os.path.join(self.staging, n)) for n in os.listdir(self.staging)
                if n != "dataset-metadata.json"}

    def test_10a_remote_file_missing_exit_3(self):
        r = self.remote()
        del r["unified_y__run__stgcn_unified_best.pt"]
        self.assertEqual(self.verify(self.created_api(remote_override=r)), 3)
        self.assertNoManifest()

    def test_10b_remote_size_differs_exit_3(self):
        r = self.remote()
        r["unified_y__run__stgcn_unified_best.pt"] += 1
        self.assertEqual(self.verify(self.created_api(remote_override=r)), 3)
        self.assertNoManifest()

    def test_10c_two_pages_merged(self):
        api = self.created_api(pages=2)
        self.assertEqual(self.verify(api), 0)
        self.assertEqual([c[1] for c in api.calls if c[0] == "dataset_list_files"], [None, "1"])

    def test_11_downloaded_sha_differs_exit_3(self):
        api = self.created_api(download_tamper="step4_x__runs__run_a__test_logits.npz")
        self.assertEqual(self.verify(api), 3)
        self.assertNoManifest()

    def test_11b_not_ready_before_timeout_exit_6(self):
        self.assertEqual(self.verify(self.created_api(status_after="pending")), 6)
        self.assertNoManifest()

    def test_12_success_manifest_keys(self):
        self.assertEqual(self.verify(self.created_api()), 0)
        with open(self.manifest, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(set(m), {"generated_by", "dataset", "files", "sha256sums_file", "verified"})
        self.assertEqual(set(m["generated_by"]), {"script", "command", "git_commit", "kaggle_version",
                                                  "kagglesdk_version", "verified_at_utc"})
        self.assertEqual(set(m["dataset"]), {"ref", "url", "title", "license", "is_private", "is_private_sources",
                                             "status", "total_bytes"})
        self.assertEqual(set(m["dataset"]["is_private_sources"]), {"dataset_list_mine", "dataset_metadata"})
        self.assertEqual(set(m["sha256sums_file"]), {"archive_name", "sha256"})
        self.assertEqual(set(m["verified"]), {"file_list_matches", "downloaded_sha256_all_match", "n_files"})
        for f in m["files"]:
            self.assertEqual(set(f), {"run", "run_dir", "kind", "local_path", "archive_name", "size_bytes", "sha256",
                                      "sha256_after_download"})
            self.assertEqual(f["sha256"], f["sha256_after_download"])
            key = "sha256_ckpt" if f["kind"] == "checkpoint" else "sha256_test_logits"
            self.assertEqual(f["sha256"], self.runs[f["run"]][key])
        self.assertIs(m["dataset"]["is_private"], True)
        self.assertIs(m["dataset"]["is_private_sources"]["dataset_list_mine"], True)
        self.assertIs(m["dataset"]["is_private_sources"]["dataset_metadata"], True)
        self.assertEqual(m["dataset"]["status"], "ready")
        self.assertEqual(m["dataset"]["ref"], DATASET)
        self.assertEqual(m["verified"]["n_files"], 2 * len(self.runs))
        self.assertEqual(len(m["files"]), 2 * len(self.runs))
        self.assertTrue(m["verified"]["file_list_matches"])
        self.assertTrue(m["verified"]["downloaded_sha256_all_match"])
        self.assertTrue(m["generated_by"]["command"].startswith("python scripts/archive_step4_kaggle.py verify"))


# ------------------------------------------------------------------------------------------------ source guard (13)
class TestSourceGuard(unittest.TestCase):
    def test_13_forbidden_calls_absent(self):
        with open(os.path.join(ROOT, "scripts", "archive_step4_kaggle.py"), encoding="utf-8") as f:
            src = f.read()
        for bad in ("public=True", '"--public"', "dataset_metadata_update", "dataset_delete", "dataset_create_version",
                    "metadata --update"):
            self.assertNotIn(bad, src, bad)
        self.assertIn("public=False", src)


if __name__ == "__main__":
    unittest.main()
