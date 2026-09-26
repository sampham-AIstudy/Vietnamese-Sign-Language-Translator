"""scripts/report_step4.py: pre-registered selection rules, trimming / 4c guards, top-k alignment, McNemar, Wilson,
kernel-log parsing, provenance, deterministic output, exit codes (docs/plans/01-buoc4-hoan-tat-4a-4c.md, AC1).

Fixtures below are small synthetic unit-test inputs built in a temp dir (not report data)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import report_step4 as R  # noqa: E402

PREREG = os.path.join(ROOT, "reports", "step4_2026-09-26", "PREREGISTRATION.md")


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def cfg(hand_z="keep", ph=None, trim=None, sources="all", seed=42):
    rc = {"features": "harmonized", "hand_z": hand_z, "sources": sources, "process_height": ph}
    if trim is not None:
        rc["trim"] = trim
    return R.effective_config(rc, seed)


# ------------------------------------------------------------------------------------------------ selection rules
class TestChooseZ(unittest.TestCase):
    def test_keep_wins_by_at_least_half_point(self):
        z = R.choose_z({"K": (46.0, cfg("keep")), "D": (45.4, cfg("drop"))})
        self.assertEqual(z["chosen"], "K")
        self.assertAlmostEqual(z["diff"], 0.6)

    def test_keep_wins_by_less_than_half_point_goes_to_drop(self):
        z = R.choose_z({"K": (46.0, cfg("keep")), "D": (45.51, cfg("drop"))})
        self.assertEqual(z["chosen"], "D")
        self.assertAlmostEqual(z["diff"], 0.49)

    def test_drop_better_goes_to_drop(self):
        self.assertEqual(R.choose_z({"K": (44.0, cfg("keep")), "D": (45.0, cfg("drop"))})["chosen"], "D")

    def test_exactly_half_point_goes_to_keep(self):
        self.assertEqual(R.choose_z({"K": (46.5, cfg("keep")), "D": (46.0, cfg("drop"))})["chosen"], "K")

    def test_variant_identified_by_run_config_not_name(self):
        # names say the opposite of run_config: the rule must follow run_config.hand_z
        z = R.choose_z({"H-dropz": (46.0, cfg("keep")), "H-keepz": (45.8, cfg("drop"))})
        self.assertEqual(z["chosen"], "H-keepz")
        self.assertEqual(z["simple"], "H-keepz")
        z = R.choose_z({"run_a": (47.0, cfg("keep")), "run_b": (45.8, cfg("drop"))})
        self.assertEqual(z["chosen"], "run_a")

    def test_candidate_without_val_by_source_is_skipped(self):
        z = R.choose_z({"base": (None, R.effective_config(None, 42)), "K": (46.0, cfg("keep")), "D": (43.0, cfg("drop"))})
        self.assertEqual(z["chosen"], "K")

    def test_balanced_val_none_without_val_by_source(self):
        self.assertIsNone(R.balanced_val({"val_best": {"epoch": 1}}))
        self.assertIsNone(R.balanced_val({"val_by_source": {"qipedc": {"top1": 10.0}}}))
        self.assertEqual(R.balanced_val({"val_by_source": {"vslgh": {"top1": 75.0}, "qipedc": {"top1": 17.0}}}), 46.0)


class TestChooseResolution(unittest.TestCase):
    def test_360_adopted_at_half_point_or_more(self):
        r = R.choose_resolution("K", 46.0, cfg("keep"), {"K360": (46.5, cfg("keep", 360, True))})
        self.assertTrue(r["adopted"])
        self.assertEqual(r["chosen"], "K360")

    def test_360_not_adopted_below_half_point(self):
        r = R.choose_resolution("K", 46.0, cfg("keep"), {"K360": (46.4, cfg("keep", 360, True))})
        self.assertFalse(r["adopted"])
        self.assertEqual(r["chosen"], "K")

    def test_360_with_other_hand_z_is_exit_3(self):
        with self.assertRaises(R.ReportError) as cm:
            R.choose_resolution("K", 46.0, cfg("keep"), {"D360": (50.0, cfg("drop", 360, True))})
        self.assertEqual(cm.exception.code, 3)

    def test_missing_trim_key_means_trimmed(self):
        self.assertTrue(R.effective_config({"hand_z": "keep"}, 42)["trim"])


class TestSelectAux(unittest.TestCase):
    def test_aux_with_highest_val_is_never_chosen(self):
        meta = {"baseline": {"role": "baseline", "bal": None, "cfg": R.effective_config(None, 42)},
                "K": {"role": "candidate_native", "bal": 46.0, "cfg": cfg("keep")},
                "D": {"role": "candidate_native", "bal": 43.0, "cfg": cfg("drop")},
                "K360": {"role": "candidate_360", "bal": 46.2, "cfg": cfg("keep", 360, True)},
                "K43": {"role": "aux", "bal": 60.0, "cfg": cfg("keep", seed=43)},
                "Knotrim": {"role": "aux", "bal": 59.0, "cfg": cfg("keep", trim=False)}}
        self.assertEqual(R.select(meta)["chosen"], "K")


class TestTrimming(unittest.TestCase):
    def runs(self, bal_trim, bal_notrim):
        return {"K": (bal_trim, cfg("keep")), "K43": (50.0, cfg("keep", seed=43)),
                "K360": (48.0, cfg("keep", 360, True)), "Knotrim": (bal_notrim, cfg("keep", trim=False))}

    def test_paired_by_run_config_and_credited(self):
        v = R.trimming_verdict(self.runs(46.5, 46.0))
        self.assertEqual([(x["trimmed"], x["untrimmed"], x["credited"]) for x in v], [("K", "Knotrim", True)])

    def test_not_credited_below_half_point(self):
        v = R.trimming_verdict(self.runs(46.4, 46.0))
        self.assertFalse(v[0]["credited"])

    def test_no_pair_is_exit_3(self):
        with self.assertRaises(R.ReportError) as cm:
            R.trimming_verdict({"K360": (48.0, cfg("keep", 360, True)), "Knotrim": (46.0, cfg("keep", trim=False))})
        self.assertEqual(cm.exception.code, 3)


class TestPickDictRun(unittest.TestCase):
    def test_matching_config(self):
        d = {"dict": cfg("keep", None, None, "qipedc"), "dict360": cfg("keep", 360, True, "qipedc")}
        self.assertEqual(R.pick_dict_run(cfg("keep", 360, True), d), "dict360")
        self.assertEqual(R.pick_dict_run(cfg("keep"), d), "dict")

    def test_no_match_is_exit_3_without_fallback(self):
        d = {"dict": cfg("keep", None, None, "qipedc"), "dict360": cfg("keep", 360, True, "qipedc")}
        with self.assertRaises(R.ReportError) as cm:
            R.pick_dict_run(cfg("drop"), d)
        self.assertEqual(cm.exception.code, 3)
        self.assertIn("4c không có run từ điển khớp", str(cm.exception))


# ------------------------------------------------------------------------------------------------ statistics
class TestStats(unittest.TestCase):
    def test_mcnemar(self):
        from scipy.stats import binomtest
        self.assertEqual(R.mcnemar_exact([1, 0], [1, 0]), (0, 0, 1.0))
        n10, n01, p = R.mcnemar_exact([1] * 5 + [0] * 3, [0] * 5 + [0] * 3)
        self.assertEqual((n10, n01), (5, 0))
        self.assertEqual(p, binomtest(5, 5, 0.5).pvalue)
        a, b = [1, 1, 0, 1, 0, 0, 1], [0, 1, 1, 0, 0, 1, 0]
        n10, n01, p = R.mcnemar_exact(a, b)
        m10, m01, q = R.mcnemar_exact(b, a)
        self.assertEqual((n10, n01), (m01, m10))
        self.assertAlmostEqual(p, q)

    def test_wilson_bounds(self):
        for k, n in ((0, 7), (7, 7), (0, 1), (1, 1), (0, 1000), (1000, 1000)):
            r = R.rate(k, n)
            self.assertGreaterEqual(r["ci_low"], 0.0)
            self.assertLessEqual(r["ci_high"], 100.0)
            self.assertLessEqual(r["ci_low"], r["pct"])
            self.assertGreaterEqual(r["ci_high"], r["pct"])
        self.assertIsNone(R.rate(0, 0)["pct"])

    def test_k_from_pct(self):
        self.assertEqual(R.k_from_pct(58.4, 202), 118)
        self.assertEqual(R.k_from_pct(0.0, 26), 0)
        self.assertEqual(R.k_from_exact_pct(17.142857142857142, 105), 18)
        self.assertIsNone(R.k_from_exact_pct(17.2, 105))


class TestTopkAlign(unittest.TestCase):
    def setUp(self):
        self.classes = ["a", "b", "c"]
        self.test = pd.DataFrame({"video_id": ["v1", "v2", "v3", "v4"], "gloss_normalized": ["a", "b", "c", "a"],
                                  "source": ["qipedc"] * 4})

    def test_intersection_row_by_row(self):
        # run A: v3, v1, v2 (v4 missing); run B: v2, v4, v1 (v3 missing) -> compared on v1, v2
        la = np.array([[0, 0, 9], [9, 1, 0], [1, 0, 2]], np.float16)   # v3 right, v1 right, v2 wrong (c > a > b)
        lb = np.array([[0, 5, 1], [1, 9, 0], [0, 9, 1]], np.float16)   # v2 right, v4 wrong, v1 wrong
        ra, xa, ta = R.align_logits(["v3", "v1", "v2"], [2, 0, 1], la, self.classes, self.test)
        rb, xb, tb = R.align_logits(["v2", "v4", "v1"], [1, 0, 0], lb, self.classes, self.test)
        self.assertEqual(list(ra.video_id), ["v1", "v2", "v3"])
        self.assertEqual(list(rb.video_id), ["v1", "v2", "v4"])
        ha, hb = R.topk_hits(xa, ta, (1, 2)), R.topk_hits(xb, tb, (1, 2))
        ia, ib, common = R.align(ra, rb)
        self.assertEqual(common, ["v1", "v2"])
        self.assertEqual(list(ha[1][ia]), [True, False])
        self.assertEqual(list(hb[1][ib]), [False, True])
        self.assertEqual(list(ha[2][ia]), [True, False])   # v2 in A: c 2, a 1, b 0 -> b is third
        self.assertEqual(R.mcnemar_exact(ha[1][ia], hb[1][ib])[:2], (1, 1))

    def test_wrong_label_order_asserts(self):
        with self.assertRaises(AssertionError):
            R.align_logits(["v1", "v2"], [1, 0], np.zeros((2, 3), np.float16), self.classes, self.test)

    def test_tie_check(self):
        L = np.array([[1, 1, 0], [2, 0, 0]], np.float16)
        tc = R.tie_check(L, [1, 0], (1,))
        self.assertEqual((tc["1"]["used"], tc["1"]["pessimistic"], tc["1"]["optimistic"]), (1, 1, 2))


# ------------------------------------------------------------------------------------------------ provenance
KERNEL_LOG = [
    {"stream_name": "stdout", "time": 0.7, "data": "$ git clone -q --depth 1 -b fix/audit-round2 https://github.com/x/Vietnamese-Sign-Language-Translator.git /tmp/vslt\n"},
    {"stream_name": "stdout", "time": 2.2, "data": "$ cd /tmp/vslt && git log --oneline -1\n"},
    {"stream_name": "stdout", "time": 2.3, "data": "c8a7bdf feat(level2): something\n"},
    {"stream_name": "stdout", "time": 80.2, "data": "$ [GPU 0] /usr/bin/python3 scripts/train_unified.py --data-root /tmp/r --out-dir /kaggle/working/run_keepz --epochs 120 --seed 42 --features harmonized --hand-z keep\n"},
    {"stream_name": "stdout", "time": 80.3, "data": "$ [GPU 1] /usr/bin/python3 scripts/train_unified.py --data-root /tmp/r --out-dir /kaggle/working/run_keepz_seed43 --epochs 120 --seed 43 --features harmonized\n"},
    {"stream_name": "stdout", "time": 4224.6, "data": "--- run_keepz exit 0 ---\n"},
    {"stream_name": "stdout", "time": 4224.7, "data": "total 70.4 min; failed: []\n"},
    {"stream_name": "stderr", "time": 4229.1, "data": "[NbConvertApp] Writing 292898 bytes to __results__.html\n"},
]


class TestProvenance(unittest.TestCase):
    def test_parse_kernel_log(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "k.log")
            dump(KERNEL_LOG, p)
            k = R.parse_kernel_log(p)
        finally:
            shutil.rmtree(d)
        self.assertEqual(k["repo_commit"], "c8a7bdf")
        self.assertEqual(k["branch"], "fix/audit-round2")
        self.assertEqual(sorted(k["runs"]), ["run_keepz", "run_keepz_seed43"])
        self.assertEqual(k["runs"]["run_keepz"]["seed"], 42)
        self.assertEqual(k["runs"]["run_keepz_seed43"]["seed"], 43)
        self.assertEqual(k["runs"]["run_keepz"]["exit"], 0)
        self.assertIsNone(k["runs"]["run_keepz_seed43"]["exit"])
        self.assertTrue(k["runs"]["run_keepz"]["command"].startswith("/usr/bin/python3 scripts/train_unified.py"))
        self.assertEqual(k["duration_s"], 4229.1)
        self.assertEqual(k["reported_total_min"], 70.4)

    def test_json_without_provenance(self):
        self.assertEqual(R.json_provenance({"balanced": {}}), (None, None))
        self.assertEqual(R.json_provenance({"command": "python x", "git_commit": "abc"}), ("python x", "abc"))

    def test_compare_legacy(self):
        old = {"a": 1, "b": {"c": 2, "d": [1, 2]}}
        same = R.compare_legacy(old, {"a": 1, "b": {"c": 2, "d": [1, 2]}, "command": "x", "git_commit": "y"})
        self.assertTrue(same["same"])
        self.assertEqual(same["only_in_new"], ["command", "git_commit"])
        diff = R.compare_legacy(old, {"a": 1, "b": {"c": 3}})
        self.assertFalse(diff["same"])
        self.assertEqual(diff["different_fields"], ["b.c"])
        self.assertEqual(diff["only_in_old"], ["b.d"])


# ------------------------------------------------------------------------------------------------ end-to-end fixture
CLASSES = ["a", "b", "c", "d", "e"]


def _rows(spec, split):
    return pd.DataFrame([{"video_id": v, "source": s, "gloss_normalized": g, "signer_id": sg, "recording_group": rg,
                          "split": split} for v, s, g, sg, rg in spec])


def make_fixture(d, dict_runs=("dict", "dict360"), bad_label_run=None):
    import torch
    man = os.path.join(d, "manifest")
    os.makedirs(man)
    _rows([("t1", "vslgh", "a", "S01", None), ("t2", "vslgh", "b", "S01", None), ("t3", "vslgh", "c", "S01", None),
           ("t4", "qipedc", "c", None, "RG1"), ("t5", "qipedc", "d", None, "RG2"), ("t6", "qipedc", "e", None, "RG3")],
          "train").to_csv(os.path.join(man, "train.csv"), index=False)
    _rows([("v1", "vslgh", "a", "S05", None), ("v2", "qipedc", "d", None, "RG2v")], "val").to_csv(os.path.join(man, "val.csv"), index=False)
    test = [("s1", "vslgh", "a", "S06", None), ("s2", "vslgh", "b", "S06", None), ("s3", "vslgh", "c", "S06", None),
            ("q1", "qipedc", "c", None, "RG1t"), ("q2", "qipedc", "d", None, "RG2t"), ("q3", "qipedc", "e", None, "RG3t")]
    _rows(test, "test").to_csv(os.path.join(man, "test.csv"), index=False)
    rng = np.random.default_rng(0)

    def run(name, rc, seed, bal=None, classes=CLASSES, qonly=False):
        p = os.path.join(d, name).replace("\\", "/")
        os.makedirs(p)
        m = {"val_best": {"epoch": 3, "top1": 50.0}, "train_samples_per_class_hist": {"1": len(classes)},
             "test_overall": {"n": 6, "top1": 50.0, "top5": 100.0}}
        if bal is not None:
            m["val_by_source"] = {"qipedc": {"n": 10, "top1": bal[1]}} if qonly else \
                {"vslgh": {"n": 10, "top1": bal[0]}, "qipedc": {"n": 10, "top1": bal[1]}}
        if rc is not None:
            m["run_config"] = rc
        dump(m, os.path.join(p, "metrics.json"))
        torch.save({"label_map": {c: i for i, c in enumerate(classes)}, "seed": seed, "run_config": rc,
                    "preprocessing": {"joints": "arms", "hand_z": True, "trim": True, "target_len": 32}},
                   os.path.join(p, "stgcn_unified_best.pt"))
        rows = [t for t in test if t[2] in classes and (not qonly or t[1] == "qipedc")][::-1]
        labels = [classes.index(t[2]) for t in rows]
        if name == bad_label_run:
            labels = labels[1:] + labels[:1]
        np.savez_compressed(os.path.join(p, "test_logits.npz"), video_ids=np.array([t[0] for t in rows]),
                            labels=np.array(labels), logits=rng.normal(size=(len(rows), len(classes))).astype(np.float16))
        return p

    hz = lambda z, ph=None, trim=None, src="all": {k: v for k, v in {"features": "harmonized", "hand_z": z, "sources": src,
                                                                      "process_height": ph, "trim": trim}.items()
                                                  if k != "trim" or trim is not None}
    p = {"baseline": run("baseline", None, 42), "base43": run("base43", None, 43),
         "keep": run("keep", hz("keep"), 42, (70.0, 20.0)), "drop": run("drop", hz("drop"), 42, (69.0, 19.0)),
         "k360": run("k360", hz("keep", 360, True), 42, (72.0, 20.0)),
         "k43": run("k43", hz("keep"), 43, (90.0, 90.0)), "notrim": run("notrim", hz("keep", None, False), 42, (70.0, 19.0))}
    if "dict" in dict_runs:
        p["dict"] = run("dict", hz("keep", src="qipedc"), 42, (0, 5.0), ["c", "d", "e"], True)
    if "dict360" in dict_runs:
        p["dict360"] = run("dict360", hz("keep", 360, True, "qipedc"), 42, (0, 6.0), ["c", "d", "e"], True)
    s4a = {"shared_classes": 1, "command": f"python scripts/shortcut_85.py --ckpt {p['baseline']}/stgcn_unified_best.pt --out x",
           "git_commit": "abc1234",
           "balanced": {"n_by_source": {"qipedc": 1, "vslgh": 1}, "chance": 50.0, "all": 60.0, "single_group": {"time": 55.0}},
           "cross_source_current_model": {"classes_kept": 1, "excluded_different_sign": [],
                                          "qipedc_test_only": {"n": 1, "classes": 1, "top1": 0.0, "top1_ci": [0.0, 79.35], "top5": 100.0}}}
    dump(s4a, os.path.join(d, "s4a.json"))
    s4b = {"shared_classes": 1, "features": "harmonized", "hand_z": "keep", "qipedc_kps_dir": "qipedc_kps",
           "balanced": {"n_by_source": {"qipedc": 1, "vslgh": 1}, "chance": 50.0, "all": 55.0, "single_group": {"time": 50.0}}}
    dump(s4b, os.path.join(d, "s4b.json"))
    return p


def argv_for(d, p, out=True, dict_runs=("dict", "dict360")):
    a = ["--baseline", p["baseline"], "--runs", f"K={p['keep']}", f"D={p['drop']}", "--run-360", f"K360={p['k360']}",
         "--aux-runs", f"K43={p['k43']}", f"Knotrim={p['notrim']}", f"base43={p['base43']}",
         "--manifest-dir", os.path.join(d, "manifest"), "--shortcut-4a", os.path.join(d, "s4a.json"),
         "--shortcut-4b", os.path.join(d, "s4b.json"), "--prereg", PREREG, "--segments", ""]
    if "dict" in dict_runs:
        a += ["--dict-run", p["dict"]]
    if "dict360" in dict_runs:
        a += ["--dict-run-360", p["dict360"]]
    if out:
        a += ["--out", os.path.join(d, "out", "REPORT.md"), "--json-out", os.path.join(d, "out", "step4_results.json")]
    return a


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp().replace("\\", "/")
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.d, ignore_errors=True)

    def build(self, argv):
        return R.build(R.parse_args(argv), argv)

    def test_selection_does_not_depend_on_test_logits(self):
        p = make_fixture(self.d)
        argv = argv_for(self.d, p)
        r1 = self.build(argv)
        for name in ("keep", "drop", "k360", "k43", "notrim"):
            f = os.path.join(p[name], "test_logits.npz")
            z = dict(np.load(f))
            z["logits"] = -z["logits"]
            np.savez_compressed(f, **z)
        r2 = self.build(argv)
        self.assertNotEqual(r1["4b"]["test_groups"], r2["4b"]["test_groups"])
        self.assertEqual(r1["4b"]["selection"], r2["4b"]["selection"])
        self.assertEqual(r1["4b"]["trimming"]["val"], r2["4b"]["trimming"]["val"])
        self.assertEqual(r1["4b"]["selection"]["chosen"], "K360")
        self.assertEqual(r1["4c"]["dict_run_used"], "dict360")

    def test_render_is_deterministic(self):
        p = make_fixture(self.d)
        argv = argv_for(self.d, p)
        r1, r2 = self.build(argv), self.build(argv)
        self.assertEqual(R.render(r1), R.render(r1))
        self.assertEqual(R.render(r1), R.render(r2))
        self.assertEqual(R.to_json(r1), R.to_json(r2))

    def test_report_marks_missing_provenance(self):
        p = make_fixture(self.d)
        text = R.render(self.build(argv_for(self.d, p)))
        self.assertIn(f"| `{R.rel(os.path.join(self.d, 's4b.json'))}` | {R.MISSING} | {R.MISSING} |", text)
        self.assertIn("dict — không khớp cách hài hòa đã chọn", text)

    def test_unreported_dict_run_has_no_numbers(self):
        p = make_fixture(self.d)
        res = self.build(argv_for(self.d, p))
        self.assertEqual(res["4c"]["dict_run_used"], "dict360")
        self.assertNotIn("dict", [r["run"] for r in res["4b"]["selection"]["table"]])
        self.assertNotIn("dict", res["4b"]["test_groups"]["tie_check"])
        self.assertEqual([d["run"] for d in res["4c"]["dict_runs_not_reported"]], ["dict"])

    def test_main_writes_both_files_on_success(self):
        p = make_fixture(self.d)
        self.assertEqual(R.main(argv_for(self.d, p)), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.d, "out", "REPORT.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.d, "out", "step4_results.json")))

    def assertNoOutput(self):
        self.assertFalse(os.path.exists(os.path.join(self.d, "out", "REPORT.md")))
        self.assertFalse(os.path.exists(os.path.join(self.d, "out", "step4_results.json")))

    def test_missing_input_exit_2_writes_nothing(self):
        p = make_fixture(self.d)
        os.remove(os.path.join(p["drop"], "test_logits.npz"))
        self.assertEqual(R.main(argv_for(self.d, p)), 2)
        self.assertNoOutput()

    def test_no_matching_dict_run_exit_3_writes_nothing(self):
        p = make_fixture(self.d, dict_runs=("dict",))
        self.assertEqual(R.main(argv_for(self.d, p, dict_runs=("dict",))), 3)
        self.assertNoOutput()

    def test_label_order_exit_1_writes_nothing(self):
        p = make_fixture(self.d, bad_label_run="drop")
        self.assertEqual(R.main(argv_for(self.d, p)), 1)
        self.assertNoOutput()

    def test_bad_arguments_exit_2_writes_nothing(self):
        p = make_fixture(self.d)
        argv = argv_for(self.d, p)
        argv = argv[:argv.index("--json-out")]
        with self.assertRaises(SystemExit) as cm:
            R.main(argv)
        self.assertEqual(cm.exception.code, 2)
        self.assertNoOutput()


if __name__ == "__main__":
    unittest.main()
