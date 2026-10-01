"""scripts/check_restored_data.py (plan 12, AC1): read-only checker of restored local data.

Every fixture lives in a fresh temp dir used as `--root` (a fake project tree with `_work/` and `reports/`); the only
real-repo file read is the committed spec `docs/recovery/expected_local_data.json` (contract test at the end, read-only).
The small videos are written with cv2.VideoWriter only to exercise the frame counter; they are not data."""
import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
import check_restored_data as C  # noqa: E402

SCRIPT = os.path.join(ROOT, "scripts", "check_restored_data.py")
SPEC_REPO = os.path.join(ROOT, "docs", "recovery", "expected_local_data.json")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def listing(root):
    out = set()
    for d, _, files in os.walk(root):
        for f in files:
            out.add(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"))
    return out


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode, **({} if isinstance(data, bytes) else {"encoding": "utf-8", "newline": ""})) as f:
        f.write(data)


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make_video(path, n_frames, w=64, h=48, fps=10.0):
    import cv2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    assert vw.isOpened()
    for i in range(n_frames):
        vw.write(np.full((h, w, 3), (i * 30) % 256, np.uint8))
    vw.release()


class Fixture(unittest.TestCase):
    """Fake root: payload files, references (manifest json, csv) and a spec covering each item type."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="vslt_chk_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        r = self.root
        os.makedirs(os.path.join(r, "_work"))
        self.good = b"checkpoint-bytes"
        write(os.path.join(r, "ck", "a.pt"), self.good)
        write(os.path.join(r, "refs", "manifest.json"),
              json.dumps({"files": [{"local_path": "ck/a.pt", "sha256": sha256_bytes(self.good)}]}))
        write(os.path.join(r, "refs", "facts.json"),
              json.dumps({"n": 3, "clip": {"video_facts": {"frames": 5, "fps": 10.0, "width": 64, "height": 48}}}))
        for i in range(3):
            write(os.path.join(r, "cnt", f"s{i % 2}", f"x{i}.bin"), b"x")
        # videos + reference csvs
        make_video(os.path.join(r, "vid", "v1.mp4"), 5)
        make_video(os.path.join(r, "vid", "v2.mp4"), 7)
        write_csv(os.path.join(r, "refs", "groups.csv"), ["file_name", "num_frames"], [["v1.mp4", 5], ["v2.mp4", 7]])
        write_csv(os.path.join(r, "refs", "wh.csv"), ["file_name", "source", "width", "height"],
                  [["v1.mp4", "q", 64, 48], ["v2.mp4", "q", 64, 48], ["zz.mp4", "other", 1, 1]])
        # csv ids
        write_csv(os.path.join(r, "refs", "pred.csv"), ["sample_id", "pred"], [["id1", "a"], ["id2", "b"]])
        write_csv(os.path.join(r, "man", "manifest.csv"), ["sample_id", "symbol"], [["id1", "a"], ["id2", "b"], ["id3", "c"]])
        write(os.path.join(r, "opaque", "model.bin"), b"no-hash")
        self.spec = {"version": 1, "items": [
            {"id": "sha_ok", "group": "a", "type": "sha256", "required": True, "dir": "ck", "file": "a.pt",
             "expected_from": [{"manifest": "refs/manifest.json", "local_path": "ck/a.pt"}], "expect_source": "refs/manifest.json:1"},
            {"id": "cnt", "group": "b", "type": "count", "required": True, "dir": "cnt", "glob": "*/*.bin",
             "expect": {"json": "refs/facts.json", "key": "n"}, "expect_groups": {"value": 2, "source": "t:1"},
             "expect_source": "refs/facts.json:1"},
            {"id": "vid", "group": "c", "type": "video_frames", "required": True, "dir": "vid", "glob": "*.mp4",
             "refs": [{"csv": "refs/groups.csv", "file_col": "file_name", "frames_col": "num_frames"},
                      {"csv": "refs/wh.csv", "file_col": "file_name", "width_col": "width", "height_col": "height",
                       "filter": {"source": "q"}}],
             "min_files_from_ref": "refs/groups.csv",
             "facts": [{"file": "v1.mp4", "expect": {"json": "refs/facts.json", "key": "clip.video_facts"}}],
             "expect_source": "refs/groups.csv:1"},
            {"id": "ids", "group": "b", "type": "csv_ids", "required": True, "dir": "man", "file": "manifest.csv",
             "id_col": "sample_id", "ref": {"csv": "refs/pred.csv", "id_col": "sample_id"},
             "expect_ref_rows": {"value": 2, "source": "t:2"}, "expect_source": "refs/pred.csv:1"},
            {"id": "opaque", "group": "a", "type": "exists_only", "required": False, "dir": "opaque", "file": "model.bin",
             "expect_source": "t:3"},
        ]}
        self.spec_path = os.path.join(r, "spec.json")
        self.save_spec()

    def save_spec(self):
        write(self.spec_path, json.dumps(self.spec))

    def run_main(self, *extra, out="_work/out.json"):
        argv = ["--root", self.root, "--spec", self.spec_path]
        if out is not None:
            argv += ["--out", os.path.join(self.root, out)]
        argv += list(extra)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = C.main(argv)
            except SystemExit as e:
                code = e.code
        return code

    def result(self, out="_work/out.json"):
        with open(os.path.join(self.root, out), encoding="utf-8") as f:
            return json.load(f)

    def item(self, rid, out="_work/out.json"):
        return {i["id"]: i for i in self.result(out)["items"]}[rid]


class TestItems(Fixture):
    def test_all_ok_exit0(self):
        self.assertEqual(self.run_main(), 0)
        res = self.result()
        self.assertEqual({i["id"]: i["status"] for i in res["items"]},
                         {"sha_ok": "ok", "cnt": "ok", "vid": "ok", "ids": "ok", "opaque": "unverifiable"})
        for k in ("command", "git_commit", "code_dirty"):
            self.assertIn(k, res["generated_by"])

    def test_sha_mismatch(self):
        write(os.path.join(self.root, "ck", "a.pt"), b"other-bytes")
        self.assertEqual(self.run_main("--only", "sha_ok"), 3)
        it = self.item("sha_ok")
        self.assertEqual(it["status"], "mismatch")
        self.assertEqual(it["sha256"], sha256_bytes(b"other-bytes"))
        self.assertEqual(it["expected_sha256"], sha256_bytes(self.good))

    def test_sha_missing_file(self):
        os.remove(os.path.join(self.root, "ck", "a.pt"))
        self.assertEqual(self.run_main("--only", "sha_ok"), 3)
        self.assertEqual(self.item("sha_ok")["status"], "missing")

    def test_glob_count_and_groups(self):
        self.assertEqual(self.run_main("--only", "cnt"), 0)
        it = self.item("cnt")
        self.assertEqual((it["count"], it["expected"], it["groups"], it["expected_groups"]), (3, 3, 2, 2))
        write(os.path.join(self.root, "cnt", "s2", "x9.bin"), b"x")
        self.assertEqual(self.run_main("--only", "cnt"), 3)
        it = self.item("cnt")
        self.assertEqual((it["status"], it["count"], it["groups"]), ("mismatch", 4, 3))

    def test_count_missing_dir(self):
        shutil.rmtree(os.path.join(self.root, "cnt"))
        self.assertEqual(self.run_main("--only", "cnt"), 3)
        self.assertEqual(self.item("cnt")["status"], "missing")

    def test_video_frames_ok_values(self):
        self.assertEqual(self.run_main("--only", "vid"), 0)
        it = self.item("vid")
        self.assertEqual((it["n_files"], it["n_ref_files"], it["n_missing_files"], it["n_frame_mismatch"],
                          it["n_size_mismatch"], it["n_size_checked"]), (2, 2, 0, 0, 0, 2))
        self.assertEqual(it["facts"][0]["status"], "ok")
        self.assertEqual(it["facts"][0]["actual"], {"frames": 5, "fps": 10.0, "width": 64, "height": 48})

    def test_video_frames_mismatch(self):
        write_csv(os.path.join(self.root, "refs", "groups.csv"), ["file_name", "num_frames"], [["v1.mp4", 5], ["v2.mp4", 8]])
        self.assertEqual(self.run_main("--only", "vid"), 3)
        it = self.item("vid")
        self.assertEqual((it["status"], it["n_frame_mismatch"]), ("mismatch", 1))
        self.assertEqual(it["frame_mismatch_examples"][0], {"file": "v2.mp4", "expected": 8, "actual": 7})

    def test_video_size_and_facts_mismatch(self):
        write(os.path.join(self.root, "refs", "facts.json"),
              json.dumps({"n": 3, "clip": {"video_facts": {"frames": 6, "fps": 10.0, "width": 64, "height": 48}}}))
        write_csv(os.path.join(self.root, "refs", "wh.csv"), ["file_name", "source", "width", "height"],
                  [["v1.mp4", "q", 64, 48], ["v2.mp4", "q", 1280, 720]])
        self.assertEqual(self.run_main("--only", "vid"), 3)
        it = self.item("vid")
        self.assertEqual((it["status"], it["n_size_mismatch"], it["facts"][0]["status"]), ("mismatch", 1, "mismatch"))

    def test_video_facts_only_item(self):
        self.spec["items"].append({"id": "facts_only", "group": "b", "type": "video_frames", "required": True,
                                   "dir": "vid", "facts": [{"file": "v1.mp4", "expect": {"json": "refs/facts.json",
                                                                                          "key": "clip.video_facts"}}],
                                   "expect_source": "refs/facts.json:1"})
        self.save_spec()
        self.assertEqual(self.run_main("--only", "facts_only"), 0)
        self.assertEqual(self.item("facts_only")["facts"][0]["status"], "ok")
        os.remove(os.path.join(self.root, "vid", "v1.mp4"))
        self.assertEqual(self.run_main("--only", "facts_only"), 3)
        self.assertEqual(self.item("facts_only")["status"], "missing")

    def test_video_facts_file_in_subdir(self):
        # like the committed spec b1_hauuto_facts: fact file "<signer>/<clip>.mp4", no glob given
        make_video(os.path.join(self.root, "sub", "s1", "c1.mp4"), 5)
        self.spec["items"].append({"id": "facts_sub", "group": "b", "type": "video_frames", "required": True,
                                   "dir": "sub", "facts": [{"file": "s1/c1.mp4", "expect": {"json": "refs/facts.json",
                                                                                             "key": "clip.video_facts"}}],
                                   "expect_source": "refs/facts.json:1"})
        self.save_spec()
        self.assertEqual(self.run_main("--only", "facts_sub"), 0)
        it = self.item("facts_sub")
        self.assertEqual((it["status"], it["facts"][0]["status"]), ("ok", "ok"))
        self.assertEqual(it["facts"][0]["actual"], {"frames": 5, "fps": 10.0, "width": 64, "height": 48})
        os.remove(os.path.join(self.root, "sub", "s1", "c1.mp4"))
        self.assertEqual(self.run_main("--only", "facts_sub"), 3)
        self.assertEqual(self.item("facts_sub")["status"], "missing")

    def test_video_missing_file(self):
        os.remove(os.path.join(self.root, "vid", "v2.mp4"))
        self.assertEqual(self.run_main("--only", "vid"), 3)
        it = self.item("vid")
        self.assertEqual((it["status"], it["n_missing_files"]), ("missing", 1))

    def test_csv_ids_missing(self):
        write_csv(os.path.join(self.root, "man", "manifest.csv"), ["sample_id", "symbol"], [["id1", "a"]])
        self.assertEqual(self.run_main("--only", "ids"), 3)
        it = self.item("ids")
        self.assertEqual((it["status"], it["n_ref_ids"], it["n_missing_ids"]), ("missing", 2, 1))
        self.assertEqual(it["missing_id_examples"], ["id2"])

    def test_csv_ids_ref_rows_changed(self):
        write_csv(os.path.join(self.root, "refs", "pred.csv"), ["sample_id", "pred"], [["id1", "a"]])
        self.assertEqual(self.run_main("--only", "ids"), 3)
        self.assertEqual(self.item("ids")["status"], "mismatch")

    def test_unverifiable_and_missing_optional(self):
        self.assertEqual(self.run_main("--only", "opaque"), 0)
        it = self.item("opaque")
        self.assertEqual((it["status"], it["verified"]), ("unverifiable", "no_reference_hash"))
        os.remove(os.path.join(self.root, "opaque", "model.bin"))
        self.assertEqual(self.run_main("--only", "opaque"), 0)  # required: false -> missing does not fail
        self.assertEqual(self.item("opaque")["status"], "missing")

    def test_private_names_redacted_outside_work(self):
        self.spec["items"][2]["private_names"] = True
        self.save_spec()
        os.remove(os.path.join(self.root, "vid", "v2.mp4"))
        out = "reports/data_recovery_2026-10-01/inv.json"
        self.assertEqual(self.run_main("--only", "vid", out=out), 3)
        it = self.item("vid", out)
        self.assertEqual(it["n_missing_files"], 1)
        self.assertNotIn("v2.mp4", json.dumps(self.result(out)))
        self.assertTrue(it["examples_redacted"])
        self.assertEqual(self.run_main("--only", "vid"), 3)
        self.assertEqual(self.item("vid")["missing_file_examples"], ["v2.mp4"])

    def test_dir_override_inside_work(self):
        shutil.copytree(os.path.join(self.root, "ck"), os.path.join(self.root, "_work", "stage"))
        shutil.rmtree(os.path.join(self.root, "ck"))
        self.assertEqual(self.run_main("--only", "sha_ok"), 3)
        self.assertEqual(self.run_main("--only", "sha_ok", "--dir-override", "sha_ok=_work/stage"), 0)
        it = self.item("sha_ok")
        self.assertEqual((it["status"], it["dir"], it["dir_overridden"]), ("ok", "_work/stage", True))


class TestExitCodesAndScope(Fixture):
    def test_exit3_subprocess(self):
        os.remove(os.path.join(self.root, "ck", "a.pt"))
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "--spec", self.spec_path,
                            "--out", os.path.join(self.root, "_work", "o.json")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 3, p.stderr)
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "--spec", self.spec_path,
                            "--out", os.path.join(self.root, "_work", "o.json"), "--only", "cnt"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_exit2_bad_args(self):
        before = listing(self.root)
        self.assertEqual(self.run_main(out=None), 2)                       # --out missing
        self.assertEqual(self.run_main("--only", "nope"), 2)               # unknown item
        self.assertEqual(self.run_main("--dir-override", "nope=_work"), 2)
        self.assertEqual(self.run_main("--dir-override", "sha_ok"), 2)     # malformed
        self.spec["items"][0]["type"] = "weird"
        self.save_spec()
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(listing(self.root) - before, set())

    def test_spec_item_without_expect_source_rejected(self):
        del self.spec["items"][1]["expect_source"]
        self.save_spec()
        self.assertEqual(self.run_main(), 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "_work", "out.json")))

    def test_out_outside_scope_rejected(self):
        before = listing(self.root)
        for bad in ("out.json", "reports/other/out.json", "ck/out.json", "_work/../ck/out.json"):
            self.assertEqual(self.run_main(out=bad), 2, bad)
        outside = os.path.join(tempfile.gettempdir(), "vslt_chk_outside.json")
        self.assertEqual(self.run_main(out=os.path.relpath(outside, self.root)), 2)
        self.assertFalse(os.path.exists(outside))
        self.assertEqual(listing(self.root), before)

    def test_out_allowed_reports_dir(self):
        self.assertEqual(self.run_main(out="reports/data_recovery_2026-10-01/inventory_after.json"), 0)

    def test_dir_override_outside_work_rejected(self):
        before = listing(self.root)
        self.assertEqual(self.run_main("--dir-override", "sha_ok=ck"), 2)
        self.assertEqual(self.run_main("--dir-override", "sha_ok=_work/../ck"), 2)
        self.assertEqual(self.run_main("--dir-override", f"sha_ok={tempfile.gettempdir()}"), 2)
        self.assertEqual(listing(self.root), before)

    def test_writes_only_out(self):
        before = listing(self.root)
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(listing(self.root) - before, {"_work/out.json"})
        self.assertEqual(before - listing(self.root), set())


class TestCommittedSpec(unittest.TestCase):
    """Contract on docs/recovery/expected_local_data.json (read-only): valid, every item has a file:line source,
    every reference resolves in the repo, plan-12 items are all present."""

    def test_spec_valid_and_references_resolve(self):
        with open(SPEC_REPO, encoding="utf-8") as f:
            spec = json.load(f)
        items = C.validate_spec(spec)
        ids = {i["id"] for i in items}
        for prefix in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "b1", "b2", "b3", "b4", "c1", "c2"):
            self.assertTrue(any(i.split("_")[0] == prefix for i in ids), prefix)
        for it in items:
            self.assertRegex(it["expect_source"], r"\S+:\d+|git blob")
        for it in items:
            C.resolve_expectations(ROOT, it)  # raises if a reference file/key is missing
        req = {i["id"]: i["required"] for i in items}
        for i, r in req.items():
            if i.split("_")[0] in ("a4", "a5", "a6", "a7"):
                self.assertFalse(r, i)  # §8.1: no archived copy, cannot be required


if __name__ == "__main__":
    unittest.main()
