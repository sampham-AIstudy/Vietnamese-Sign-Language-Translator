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
# Lần sửa 1: history.json of the chosen / dictionary run is a required input (exit 2 when missing), so every fixture
# run gets this small trainer-format history (unit-test fixture, not report data).
FIT_HISTORY = [
    {"epoch": 1, "train_loss": 6.0, "train_top1": 1.0, "val_loss": 5.0, "val_top1": 10.0, "lr": 0.001, "time_sec": 4.0},
    {"epoch": 2, "train_loss": 5.0, "train_top1": 5.5, "val_loss": 4.0, "val_top1": 20.0, "lr": 0.001, "time_sec": 4.5},
    {"epoch": 3, "train_loss": 4.0, "train_top1": 9.25, "val_loss": 3.5, "val_top1": 20.0, "lr": 0.0005, "time_sec": 5.0},
    {"epoch": 4, "train_loss": 3.0, "train_top1": 12.0, "val_loss": 3.9, "val_top1": 15.0, "lr": 0.00025, "time_sec": 5.5},
]


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
        dump(FIT_HISTORY, os.path.join(p, "history.json"))
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


class TestProposal4c(unittest.TestCase):
    """AC5: PROPOSAL_4c.md <= 550 words, one recommendation, the user decides, limitations, and every number
    (decimal, %, k/n, integer >= 10) copied verbatim from REPORT.md. A missing file fails (no conditional skip)."""
    DIR = os.path.join(ROOT, "reports", "step4_2026-09-26")

    def setUp(self):
        with open(os.path.join(self.DIR, "PROPOSAL_4c.md"), encoding="utf-8") as f:
            self.prop = f.read()
        with open(os.path.join(self.DIR, "REPORT.md"), encoding="utf-8") as f:
            self.report = f.read()

    def test_length_and_single_recommendation(self):
        import re
        self.assertLessEqual(len(self.prop.split()), 550)
        recs = re.findall(r"Khuyến nghị: ([AB])\b", self.prop)
        self.assertEqual(len(recs), 1)
        self.assertIn("người dùng quyết định", self.prop)

    def test_limitations_section(self):
        lim = self.prop.split("## Giới hạn", 1)[1].split("\n## ", 1)[0]
        for item in ("Ít mẫu mỗi lớp", "nhãn người ký", "seed cho model từ điển", "CI rộng", "(Cấp 3)",
                     "KHÔNG được đánh giá trong Bước 4", "Bộ phân loại nguồn", "đầu vào hài hòa", "harmonize()",
                     "realtime"):
            self.assertIn(item, lim)
        self.assertIn("## Điều gì sẽ làm đổi khuyến nghị", self.prop)

    def test_every_number_is_in_report(self):
        import re
        tokens = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?%|\d+/\d+|\d+\.\d+|\d+)", self.prop)
        checked = 0
        for t in tokens:
            if not ("%" in t or "/" in t or "." in t or int(t) >= 10):
                continue
            checked += 1
            self.assertRegex(self.report, r"(?<![\d.])" + re.escape(t) + r"(?!\.?\d)", f"'{t}' not in REPORT.md")
        self.assertGreater(checked, 20)


# ------------------------------------------------------------------------------------------------ Lần sửa 1 (AC1 16-23)
class TestTrainingFit(unittest.TestCase):
    """AC1 case 16: fit diagnostics read verbatim from a trainer-format history."""

    def test_best_epoch_follows_trainer_rule(self):
        # epochs 2 and 3 tie on val_top1 (20.0); epoch 3 has the lower val_loss -> best 3
        f = R.training_fit(FIT_HISTORY, 795, 64)
        self.assertEqual(f["best_epoch"], 3)
        # same tie, the earlier epoch has the lower loss -> best 2
        h = [dict(e) for e in FIT_HISTORY]
        h[2]["val_loss"] = 4.2
        self.assertEqual(R.training_fit(h, 795, 64)["best_epoch"], 2)
        # full tie (val_top1 and val_loss) -> the earlier epoch
        h[2]["val_loss"] = 4.0
        self.assertEqual(R.training_fit(h, 795, 64)["best_epoch"], 2)

    def test_lr_drops_and_verbatim_values(self):
        f = R.training_fit(FIT_HISTORY, 795, 64)
        self.assertEqual(f["lr_drop_epochs"], [3, 4])
        self.assertEqual((f["lr_first"], f["lr_last"]), (0.001, 0.00025))
        self.assertEqual(f["train_top1_at_best"], 9.25)
        self.assertEqual(f["train_top1_last"], 12.0)
        self.assertEqual(f["train_loss_last"], 3.0)
        self.assertEqual((f["val_loss_first"], f["val_loss_min"], f["val_loss_last"]), (5.0, 3.5, 3.9))
        self.assertEqual(f["epochs_run"], 4)
        self.assertAlmostEqual(f["time_sec_total"], 19.0)
        self.assertAlmostEqual(f["time_sec_mean"], 4.75)

    def test_steps_with_uneven_batches(self):
        self.assertEqual(R.steps_per_epoch(795, 64), 13)
        self.assertEqual(R.steps_per_epoch(768, 64), 12)
        f = R.training_fit(FIT_HISTORY, 795, 64)
        self.assertEqual((f["steps_per_epoch"], f["total_steps"]), (13, 52))

    def test_missing_batch_size_is_none_not_error(self):
        self.assertIsNone(R.steps_per_epoch(795, None))
        f = R.training_fit(FIT_HISTORY, 795, None)
        self.assertIsNone(f["steps_per_epoch"])
        self.assertIsNone(f["total_steps"])

    def test_empty_history_is_exit_2(self):
        with self.assertRaises(R.ReportError) as cm:
            R.training_fit([], 795, 64)
        self.assertEqual(cm.exception.code, 2)


class TestBatchSizeFromCommand(unittest.TestCase):
    """AC1 case 17."""

    def test_batch_size(self):
        self.assertEqual(R.batch_size_from_command(
            "/usr/bin/python3 scripts/train_unified.py --data-root /tmp/r --batch-size 64 --seed 42"), 64)
        self.assertIsNone(R.batch_size_from_command("/usr/bin/python3 scripts/train_unified.py --data-root /tmp/r"))
        self.assertIsNone(R.batch_size_from_command(None))


class TestTrainCmdDiff(unittest.TestCase):
    """AC1 case 18."""
    A = ("/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_360 --out-dir /kaggle/working/run_keepz_360 "
         "--epochs 120 --batch-size 64 --patience 20 --seed 42 --features harmonized --hand-z keep")
    B = ("/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_360 --out-dir /kaggle/working/dict_keepz_360 "
         "--epochs 120 --batch-size 64 --patience 20 --seed 42 --features harmonized --hand-z keep --sources qipedc")
    EMPTY = {"only_a": {}, "only_b": {}, "different": {}}

    def test_only_ignored_flags_differ(self):
        self.assertEqual(R.train_cmd_diff(self.A, self.B), self.EMPTY)

    def test_extra_flag_reported(self):
        d = R.train_cmd_diff(self.A, self.B + " --process-height 360")
        self.assertEqual(d["only_b"], {"--process-height": "360"})
        self.assertEqual((d["only_a"], d["different"]), ({}, {}))
        d = R.train_cmd_diff(self.A + " --process-height 360", self.B)
        self.assertEqual(d["only_a"], {"--process-height": "360"})
        d = R.train_cmd_diff(self.A + " --no-trim", self.B)
        self.assertEqual(d["only_a"], {"--no-trim": True})

    def test_changed_value_reported(self):
        d = R.train_cmd_diff(self.A, self.B.replace("--epochs 120", "--epochs 60"))
        self.assertEqual(d["different"], {"--epochs": ["120", "60"]})
        self.assertEqual((d["only_a"], d["only_b"]), ({}, {}))


class TestInitOptions(unittest.TestCase):
    """AC1 case 19: argparse text (fixture) scanned for weight-initialisation options."""
    BASE = ('ap = argparse.ArgumentParser()\nap.add_argument("--data-root", required=True)\n'
            'ap.add_argument("--num-workers", type=int, default=2)\nap.add_argument("--out-dir", required=True)\n'
            'ap.add_argument("--no-trim", action="store_true", help="keep the whole clip (ablation)")\n')

    def scan(self, text):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "train_fixture.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            return R.init_options(p)
        finally:
            shutil.rmtree(d)

    def test_no_init_flag(self):
        self.assertEqual(self.scan(self.BASE), [])

    def test_init_flag_found(self):
        self.assertEqual(self.scan(self.BASE + 'ap.add_argument("--init-from", default=None, help="checkpoint (.pt)")\n'),
                         ["--init-from"])


class TestPredOrigin(unittest.TestCase):
    """AC1 case 20: class origin of top-1 predictions, all / wrong only / base rate."""
    VSLGH_ONLY, WITH_Q = {"x", "y"}, {"a", "b"}
    PRED = ["a", "x", "b", "z", "y", "a"]
    TRUE = ["a", "a", "c", "b", "y", "b"]

    def test_all_and_wrong_only(self):
        o = R.pred_origin(self.PRED, self.TRUE, self.VSLGH_ONLY, self.WITH_Q)
        a, w = o["all"], o["wrong_only"]
        self.assertEqual([a[k]["k"] for k in ("vslgh_only_class", "class_with_qipedc_train", "class_without_train_data")],
                         [2, 3, 1])
        self.assertEqual(w["vslgh_only_class"]["n"], sum(p != t for p, t in zip(self.PRED, self.TRUE)))
        # the correct "a" (row 0) is in a class with QIPEDC training data but not in wrong_only
        self.assertEqual([w[k]["k"] for k in ("vslgh_only_class", "class_with_qipedc_train", "class_without_train_data")],
                         [1, 2, 1])
        self.assertEqual(o["correct_n"], 2)
        for blk in (a, w):
            ks = [blk[k]["k"] for k in ("vslgh_only_class", "class_with_qipedc_train", "class_without_train_data")]
            self.assertEqual(sum(ks), blk["vslgh_only_class"]["n"])

    def test_label_space_base_rate(self):
        r = R.label_space_base_rate(self.VSLGH_ONLY, ["a", "b", "c", "x", "y", "z"])
        self.assertEqual((r["k"], r["n"]), (2, 6))


class TestTrimConsequence(unittest.TestCase):
    """AC1 case 21: sentence built from run_config.trim of the chosen run and the VAL verdict."""
    ROWS = [{"trimmed": "K", "untrimmed": "Knotrim", "diff": -0.28, "credited": False}]

    def test_trimmed_not_credited(self):
        c = R.trim_consequence("K360", cfg("keep", 360, True), self.ROWS)
        self.assertTrue(c["chosen_trim"])
        self.assertFalse(c["credited"])
        for s in ("K360", "trim=true", "harmonize()", "không do luật đăng ký trước quyết định"):
            self.assertIn(s, c["sentence"])

    def test_not_trimmed(self):
        c = R.trim_consequence("K360", cfg("keep", 360, False), self.ROWS)
        self.assertFalse(c["chosen_trim"])
        self.assertIn("không cắt đoạn nghỉ", c["sentence"])
        self.assertNotIn("trim=true", c["sentence"])

    def test_name_not_hard_coded(self):
        c = R.trim_consequence("Other-run_x", cfg("keep", 360, True), self.ROWS)
        self.assertIn("Other-run_x", c["sentence"])
        self.assertNotIn("K360", c["sentence"])


class TestPreregHeaderTimes(unittest.TestCase):
    """AC1 case 22: header time written in PREREGISTRATION vs the time of the first commit containing it."""
    TEXT = "# Pre-registration\n\n1. rule\n\n## Added 2026-09-26 12:30, after the z choice\n\n2. rule\n"

    @staticmethod
    def commit(h, date, text):
        import datetime as dt
        return {"commit": h, "date": date, "unix": int(dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z").timestamp()),
                "text": text}

    def test_header_minus_commit(self):
        commits = [self.commit("ccc3333", "2026-09-26 13:00:00 +0700", self.TEXT),
                   self.commit("bbb2222", "2026-09-26 12:13:24 +0700", self.TEXT),
                   self.commit("aaa1111", "2026-09-26 10:58:44 +0700", "# Pre-registration\n\n1. rule\n")]
        out = R.prereg_header_times(self.TEXT, commits)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["header_time"], "2026-09-26 12:30")
        self.assertEqual(out[0]["commit"], "bbb2222")
        self.assertEqual(out[0]["commit_time"], "2026-09-26 12:13:24 +0700")
        self.assertEqual(out[0]["header_minus_commit_s"], 996)

    def test_no_header(self):
        self.assertEqual(R.prereg_header_times("# Pre-registration\n\n1. rule\n", []), [])

    def test_commit_not_found(self):
        out = R.prereg_header_times(self.TEXT, [self.commit("aaa1111", "2026-09-26 10:58:44 +0700", "# old\n")])
        self.assertEqual(out[0]["header_time"], "2026-09-26 12:30")
        self.assertIsNone(out[0]["commit"])
        self.assertIsNone(out[0]["commit_time"])
        self.assertIsNone(out[0]["header_minus_commit_s"])
        self.assertIsNone(R.prereg_header_times(self.TEXT, [])[0]["commit"])


class TestRevision1EndToEnd(unittest.TestCase):
    """AC1 case 23 + the Lần sửa 1 CLI contract (history.json inputs, new JSON keys, 4c scope section)."""

    def setUp(self):
        self.d = tempfile.mkdtemp().replace("\\", "/")
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.d, ignore_errors=True)

    def build(self, argv):
        return R.build(R.parse_args(argv), argv)

    def test_augmentation_line_not_repeated(self):
        p = make_fixture(self.d)
        text = R.render(self.build(argv_for(self.d, p)))
        self.assertNotIn("Augmentation: Augmentation", text)
        self.assertEqual(sum(l.startswith("- Augmentation (training only):") for l in text.splitlines()), 1)

    def test_new_json_keys_and_scope_section(self):
        p = make_fixture(self.d)
        res = self.build(argv_for(self.d, p))
        fs = res["4c"]["fit_and_scope"]
        self.assertEqual(fs["dict"]["best_epoch"], 3)
        self.assertEqual(fs["unified"]["train_top1_last"], 12.0)
        self.assertIsNone(fs["dict"]["batch_size"])          # no kernel log in the fixture -> no command
        self.assertEqual(fs["init_options"], [])
        self.assertFalse(fs["dict_command_uses_init"])
        self.assertTrue(fs["scope_limited"])
        eb = res["4c"]["exploratory"]["b_unified_top1_class_origin"]
        for key in ("qipedc_test_all", "qipedc_test_common", "s06_contrast"):
            self.assertIn("wrong_only", eb[key])
            self.assertIn("vslgh_only_class", eb[key])     # old keys kept
        self.assertIn("label_space_base_rate", eb)
        self.assertIn("consequence", res["4b"]["trimming"])
        self.assertIn("preregistration_header_times", res["limitations_data"])
        self.assertIn("train_top1_measurement", res["limitations_data"])
        aug = res["4b"]["harmonisation_config"]["augmentation"]
        self.assertIsNotNone(aug)
        self.assertFalse(aug.startswith("Augmentation"))
        roles = {i["role"] for i in res["inputs"]}
        self.assertIn("history.json K360", roles)
        self.assertIn("history.json dict360", roles)
        text = R.render(res)
        i_scope = text.index("Phạm vi so sánh và mức khớp train")
        self.assertLess(text.index("McNemar chính xác top-1"), i_scope)
        self.assertLess(i_scope, text.index("Phân tích thăm dò"))
        self.assertIn("không phải độ chính xác sạch trên tập train", text)
        self.assertIn("(iv) ", text)

    def test_missing_history_of_chosen_run_exit_2_writes_nothing(self):
        p = make_fixture(self.d)
        os.remove(os.path.join(p["k360"], "history.json"))
        self.assertEqual(R.main(argv_for(self.d, p)), 2)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out", "REPORT.md")))
        self.assertFalse(os.path.exists(os.path.join(self.d, "out", "step4_results.json")))

    def test_missing_history_of_dict_run_used_exit_2(self):
        p = make_fixture(self.d)
        os.remove(os.path.join(p["dict360"], "history.json"))
        self.assertEqual(R.main(argv_for(self.d, p)), 2)

    def test_missing_history_of_other_run_is_null(self):
        p = make_fixture(self.d)
        os.remove(os.path.join(p["drop"], "history.json"))
        res = self.build(argv_for(self.d, p))
        self.assertNotIn("history.json D", {i["role"] for i in res["inputs"]})
        self.assertIsNone(res["provenance"]["runs"]["D"]["history_json"])
        self.assertEqual(res["provenance"]["runs"]["K"]["history_json"], R.rel(os.path.join(p["keep"], "history.json")))
        self.assertIsNotNone(res["4c"]["fit_and_scope"]["dict"])


if __name__ == "__main__":
    unittest.main()
