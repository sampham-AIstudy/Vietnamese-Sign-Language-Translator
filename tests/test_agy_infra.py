"""Hạ tầng agy: guard nhận nhánh làm việc theo danh sách cho phép; cổng hạn mức bỏ qua bucket {"disabled": true}.

Không gọi agy thật: subprocess / pm.pick / sổ đo đều được mock.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import agy_guard as guard  # noqa: E402
import agy_usage as usage  # noqa: E402

CLOUD = "cloud/2026-10-04-level1-rearm"
FEAT = "feat/vslt-complete"


def _usage_json(claude_week_frac=0.0, gemini_5h=1.0, gemini_week=1.0, claude_5h_disabled=True):
    """Cùng cấu trúc với `agy -p /usage --output-format json` thật (8/10: bucket 5h nhóm Claude/GPT là {"disabled": true})."""
    c5 = {"id": "3p-5h", "name": "Five Hour Limit Remaining", "window": "5h", "remaining_fraction": 1}
    if claude_5h_disabled:
        c5["disabled"] = True
    else:
        c5["reset_time"] = "2026-10-08T15:00:00Z"
    return json.dumps({"status": "SUCCESS", "command": {"name": "usage", "data": {"groups": [
        {"name": "Gemini Models", "buckets": [
            {"id": "gemini-weekly", "window": "weekly", "remaining_fraction": gemini_week, "reset_time": "2026-10-15T07:07:31Z"},
            {"id": "gemini-5h", "window": "5h", "remaining_fraction": gemini_5h, "reset_time": "2026-10-08T12:07:31Z"}]},
        {"name": "Claude and GPT models", "buckets": [
            {"id": "3p-weekly", "window": "weekly", "remaining_fraction": claude_week_frac, "reset_time": "2026-10-10T14:46:37Z"},
            c5]},
    ]}}})


def _run_ok(stdout):
    return subprocess.CompletedProcess(args=["agy"], returncode=0, stdout=stdout, stderr="")


# ----------------------------------------------------------------------------- guard: nhánh

class TestGuardBranches(unittest.TestCase):
    def test_default_allowed_contains_working_branches_not_main(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGY_ALLOWED_BRANCHES", None)
            al = guard.allowed_branches()
        self.assertIn(FEAT, al)
        self.assertIn(CLOUD, al)
        self.assertNotIn("main", al)
        self.assertNotIn("master", al)

    def test_env_override_comma_separated(self):
        al = guard.allowed_branches({"AGY_ALLOWED_BRANCHES": " feat/x , fix/y ,"})
        self.assertEqual(al, ["feat/x", "fix/y"])

    def test_env_cannot_allow_main_or_wildcard(self):
        al = guard.allowed_branches({"AGY_ALLOWED_BRANCHES": "main,master,*,feat/*,feat/ok,?x"})
        self.assertEqual(al, ["feat/ok"])

    def test_env_empty_falls_back_to_default(self):
        self.assertEqual(guard.allowed_branches({"AGY_ALLOWED_BRANCHES": "  "}), list(guard.DEFAULT_ALLOWED_BRANCHES))

    def test_branch_problem(self):
        al = [FEAT, CLOUD]
        self.assertIsNone(guard.branch_problem(CLOUD, al))
        self.assertIsNone(guard.branch_problem(FEAT, al))
        msg = guard.branch_problem("main", al)
        self.assertIsNotNone(msg)
        self.assertIn(FEAT, msg)
        self.assertIn(CLOUD, msg)
        self.assertIsNotNone(guard.branch_problem("feature/other", al))
        self.assertIsNotNone(guard.branch_problem("", al))  # detached HEAD
        self.assertIsNotNone(guard.branch_problem("main", ["main"]))  # main không bao giờ được phép
        self.assertIsNone(guard.branch_problem(CLOUD, al, snap_branch=CLOUD))
        self.assertIsNotNone(guard.branch_problem(FEAT, al, snap_branch=CLOUD))  # đổi nhánh giữa chừng

    def _check(self, br, env=None, snap_branch=None):
        snap = {"scope": ["scripts/x.py"], "protected": [], "branch": snap_branch}
        fake_git = lambda *a, **k: (br + "\n") if a[:2] == ("branch", "--show-current") else ""
        with mock.patch.object(guard, "git", side_effect=fake_git), \
                mock.patch.object(guard, "diff_files", return_value=[]), \
                mock.patch.dict(os.environ, env or {}, clear=False):
            if env is None:
                os.environ.pop("AGY_ALLOWED_BRANCHES", None)
            return guard.check_diff(["--cached"], snap)

    def test_check_diff_accepts_cloud_branch(self):
        block, _ = self._check(CLOUD)
        self.assertEqual(block, [])

    def test_check_diff_accepts_feat_branch(self):
        block, _ = self._check(FEAT)
        self.assertEqual(block, [])

    def test_check_diff_blocks_main_and_lists_allowed(self):
        block, _ = self._check("main")
        self.assertEqual(len(block), 1)
        self.assertIn("main", block[0])
        self.assertIn(FEAT, block[0])
        self.assertIn(CLOUD, block[0])

    def test_check_diff_env_override(self):
        self.assertEqual(self._check("fix/z", env={"AGY_ALLOWED_BRANCHES": "fix/z"})[0], [])
        self.assertEqual(len(self._check(CLOUD, env={"AGY_ALLOWED_BRANCHES": "fix/z"})[0]), 1)

    def test_check_diff_blocks_branch_switch_after_snapshot(self):
        self.assertEqual(len(self._check(FEAT, snap_branch=CLOUD)[0]), 1)
        self.assertEqual(self._check(CLOUD, snap_branch=CLOUD)[0], [])

    def test_old_snapshot_without_branch_file_loads(self):
        d = tempfile.mkdtemp(dir=_work_dir())
        for n, s in {"protected.txt": "a\n", "scope.txt": "b/\n", "base": "abc", "hashes.json": "{}", "porcelain.json": "{}"}.items():
            with open(os.path.join(d, n), "w", encoding="utf-8") as f:
                f.write(s)
        snap = guard.load(d)
        self.assertIsNone(snap["branch"])
        with open(os.path.join(d, "branch"), "w", encoding="utf-8") as f:
            f.write(CLOUD + "\n")
        self.assertEqual(guard.load(d)["branch"], CLOUD)


def _work_dir():
    p = os.path.join(ROOT, "_work", "test_agy_infra")
    os.makedirs(p, exist_ok=True)
    return p


def tearDownModule():
    def _writable(func, path, _exc):  # object của git là read-only trên Windows
        try:
            os.chmod(path, 0o700)
            func(path)
        except OSError:
            pass
    shutil.rmtree(os.path.join(ROOT, "_work", "test_agy_infra"), onerror=_writable)  # chỉ thư mục tạm do test này tạo


class TestGuardEndToEnd(unittest.TestCase):
    """Chạy guard thật (snapshot + range) trong một repo git tạm, không dùng agy."""

    def _git(self, repo, *a):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(["git", "-c", "core.hooksPath=", *a], cwd=repo, check=True, capture_output=True, env=env)

    def _run(self, branch, env_allowed=None):
        repo = tempfile.mkdtemp(dir=_work_dir())
        self._git(repo, "init", "-q", "-b", branch)
        with open(os.path.join(repo, "plan.md"), "w", encoding="utf-8") as f:
            f.write("```scope\nsrc/\n```\n")
        self._git(repo, "add", "plan.md")
        self._git(repo, "commit", "-q", "-m", "init")
        env = dict(os.environ)
        env.pop("AGY_ALLOWED_BRANCHES", None)
        if env_allowed is not None:
            env["AGY_ALLOWED_BRANCHES"] = env_allowed
        script = os.path.join(ROOT, "scripts", "agy_guard.py")
        snap = os.path.join(repo, ".snap")
        subprocess.run([sys.executable, script, "snapshot", "plan.md", snap], cwd=repo, check=True, capture_output=True, env=env)
        os.makedirs(os.path.join(repo, "src"))
        with open(os.path.join(repo, "src", "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        self._git(repo, "add", "src/a.py")
        self._git(repo, "commit", "-q", "-m", "work")
        return subprocess.run([sys.executable, script, "range", snap], cwd=repo, capture_output=True, env=env,
                              text=True, encoding="utf-8", errors="replace")

    def test_range_clean_on_cloud_branch(self):
        r = self._run(CLOUD)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

    def test_range_blocks_on_main(self):
        r = self._run("main")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("main", r.stderr)
        self.assertIn(CLOUD, r.stderr)

    def test_range_env_override(self):
        self.assertEqual(self._run("fix/z", env_allowed="fix/z").returncode, 0)
        self.assertEqual(self._run("fix/z").returncode, 1)


# ----------------------------------------------------------------------------- usage: bucket disabled

class TestUsageFetch(unittest.TestCase):
    def _fetch(self, stdout):
        with mock.patch.object(usage.subprocess, "run", return_value=_run_ok(stdout)), \
                contextlib.redirect_stderr(io.StringIO()):
            return usage.fetch()

    def test_disabled_bucket_no_exception_and_group_unusable(self):
        u = self._fetch(_usage_json())
        self.assertIsNotNone(u)
        c = u["claude"]
        self.assertTrue(c["disabled"])
        self.assertEqual(c["five_used"], 100.0)
        self.assertEqual(c["week_used"], 100.0)
        self.assertIsNone(c["five_reset"])
        self.assertEqual(c["week_reset"], "2026-10-10T14:46:37Z")

    def test_gemini_group_read_correctly_next_to_disabled(self):
        u = self._fetch(_usage_json(gemini_5h=0.75, gemini_week=0.41))
        g = u["gemini"]
        self.assertFalse(g["disabled"])
        self.assertEqual(g["five_used"], 25.0)
        self.assertEqual(g["week_used"], 59.0)
        self.assertEqual(g["five_reset"], "2026-10-08T12:07:31Z")
        self.assertEqual(g["week_reset"], "2026-10-15T07:07:31Z")

    def test_disabled_group_forced_unusable_even_if_week_left(self):
        c = self._fetch(_usage_json(claude_week_frac=0.5))["claude"]
        self.assertTrue(c["disabled"])
        self.assertEqual((c["five_used"], c["week_used"]), (100.0, 100.0))

    def test_no_disabled_bucket_unchanged(self):
        c = self._fetch(_usage_json(claude_week_frac=0.5, claude_5h_disabled=False))["claude"]
        self.assertFalse(c["disabled"])
        self.assertEqual(c["five_used"], 0.0)
        self.assertEqual(c["week_used"], 50.0)
        self.assertEqual(c["five_reset"], "2026-10-08T15:00:00Z")

    def test_bucket_missing_fields_is_unusable_not_crash(self):
        d = json.loads(_usage_json(claude_5h_disabled=False))
        del d["command"]["data"]["groups"][1]["buckets"][1]["reset_time"]
        u = self._fetch(json.dumps(d))
        self.assertTrue(u["claude"]["disabled"])
        self.assertFalse(u["gemini"]["disabled"])


class TestUsageGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_work_dir())
        self.patches = [
            mock.patch.object(usage, "BEFORE", os.path.join(self.tmp, "before.json")),
            mock.patch.object(usage, "LEDGER", os.path.join(self.tmp, "ledger.csv")),
            mock.patch.object(usage, "read_ledger", return_value=[]),
            mock.patch.object(usage.pm, "pick", side_effect=lambda fam, eff: (f"{fam}-model-{eff}", eff)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def _choose(self, stdout, pref="gemini", effort="high", steps=1):
        out = io.StringIO()
        with mock.patch.object(usage.subprocess, "run", return_value=_run_ok(stdout)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = usage.cmd_choose(pref, effort, steps, "docs/plans/x.md")
        return rc, out.getvalue()

    def test_choose_gemini_high_when_claude_disabled(self):
        rc, out = self._choose(_usage_json())
        self.assertEqual(rc, 0, out)
        self.assertIn("MODEL=gemini-model-high", out)
        self.assertIn("EFFORT=high", out)
        self.assertIn("GROUP=gemini", out)

    def test_choose_skips_disabled_group_even_if_preferred(self):
        rc, out = self._choose(_usage_json(claude_week_frac=1.0), pref="opus")
        self.assertEqual(rc, 0, out)
        self.assertIn("GROUP=gemini", out)
        self.assertIn("EFFORT=high", out)
        before = json.load(open(usage.BEFORE, encoding="utf-8"))
        self.assertEqual(before["group"], "gemini")
        self.assertTrue(before["usage"]["claude"]["disabled"])

    def test_choose_wait_without_crash_when_nothing_fits(self):
        rc, out = self._choose(_usage_json(gemini_5h=0.05))
        self.assertEqual(rc, 20, out)
        self.assertIn("WAIT", out)

    def test_status_with_disabled_group(self):
        out = io.StringIO()
        with mock.patch.object(usage.subprocess, "run", return_value=_run_ok(_usage_json())), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = usage.cmd_status()
        self.assertEqual(rc, 0)
        self.assertIn("disabled", out.getvalue())
        self.assertIn("gemini", out.getvalue())

    def test_record_after_choose_with_disabled_group(self):
        self.assertEqual(self._choose(_usage_json())[0], 0)
        out = io.StringIO()
        with mock.patch.object(usage.subprocess, "run", return_value=_run_ok(_usage_json(gemini_5h=0.9, gemini_week=0.99))), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = usage.cmd_record(1, "")
        self.assertEqual(rc, 0)
        rows = open(usage.LEDGER, encoding="utf-8").read().splitlines()
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1].split(",")[1] == "gemini")
        self.assertIn(",10.0,1.0,ok", rows[1])

    def test_record_old_before_file_without_disabled_key(self):
        old = {"gemini": {"five_used": 0.0, "five_reset": "2026-10-08T12:07:31Z", "week_used": 0.0, "week_reset": "2026-10-15T07:07:31Z"}}
        with open(usage.BEFORE, "w", encoding="utf-8") as f:
            json.dump({"usage": old, "group": "gemini", "model": "m", "effort": "high", "plan": "p"}, f)
        with mock.patch.object(usage.subprocess, "run", return_value=_run_ok(_usage_json(gemini_5h=0.9, gemini_week=0.99))), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(usage.cmd_record(1, ""), 0)
        self.assertIn(",10.0,1.0,ok", open(usage.LEDGER, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
