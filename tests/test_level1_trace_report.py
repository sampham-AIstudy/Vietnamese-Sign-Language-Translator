"""
Plan 15 lần sửa 6 W3 / §7 AC-6e: scripts/level1_trace_report.py on synthetic traces built for each hypothesis.

The traces are made the way the app makes them: every window result goes through the real Level1LabelDecoder and the
entry is written by the app's own Level1App._window_entry (no model, no video: synthetic window results, so this tests
the classification logic of the report, not the model).

Tests:
- one synthetic session per hypothesis M1, M2, M3, M4 (and M4 found from the closing label without --expected) is
  classified with that hypothesis as the main cause (> 50 % of the transition time), with the expected window counts;
- M0: a motion_pose run is M0 without window analysis;
- segment boundaries: decoder reset (hand withdrawn), end of trace, windows before the first emission;
- --hold-ms, window time capped at hand_lost_ms, truncated trace flagged, missing window_trace refused;
- deterministic: the CLI run twice gives the same bytes (stdout and --out-json).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import level1_demo as app_mod  # noqa: E402
from scripts import level1_trace_report as rep  # noqa: E402
from src.inference.level1_segmenter import Level1LabelDecoder  # noqa: E402

PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
TMP_PARENT = os.path.join(PROJECT_ROOT, "_work", "_plan15_tmp")
PARAMS = {"cls_window_ms": 1000, "cls_conf": 0.9, "cls_stable_ms": 300, "hand_lost_ms": 300}
STEP = 33.0
T0 = 1000.0


def win(top1, conf, top2="y", conf2=0.01):
    return (top1, conf, top2, conf2)


def run(label, conf, n, top2="y", conf2=0.01):
    return [win(label, conf, top2, conf2)] * n


def make_trace(frames, rearm_mode="classifier"):
    """frames: window results (top1, conf, top2, conf2) or None (frame without a hand), one every STEP ms."""
    dec = Level1LabelDecoder(PARAMS)
    fake_app = types.SimpleNamespace(decoder=dec)
    entries, labels = [], []
    for i, f in enumerate(frames):
        ts = T0 + STEP * i
        if f is None:
            dec.push(ts, False, None)
            continue
        top1, conf, top2, conf2 = f
        result = {"status": "ok", "prediction": top1, "confidence": conf,
                  "candidates": [{"class": top1, "confidence": conf}, {"class": top2, "confidence": conf2}]}
        emit = dec.push(ts, True, result)
        entries.append(app_mod.Level1App._window_entry(fake_app, ts, result, emit))
        if emit is not None:
            labels.append({"seq": emit.seq, "ts_ms": emit.ts_ms, "prediction": emit.prediction,
                           "run_since_ms": emit.run_since_ms})
    return {"rearm_mode": rearm_mode,
            "config": {"values": {k: {"value": v, "source": "design"} for k, v in PARAMS.items()}},
            "labels": labels,
            "window_trace": {"max_entries": app_mod.TRACE_MAX_ENTRIES, "n_windows": len(entries), "truncated": False,
                             "fields": list(app_mod.TRACE_KEYS), "entries": entries}}


# old sign 'a' held 70 windows (emitted at 330 ms; hold = 2000 ms from the start of its run => windows 0..60), then the
# transition (60 windows), then the new sign 'b' held 20 windows (emitted 330 ms after its run starts)
HOLD_A = run("a", 0.95, 70)
NEW_B = run("b", 0.95, 20)
TRANSITIONS = {
    "M1": run("c", 0.5, 60, top2="e", conf2=0.3),                                   # below cls_conf, not the pair
    "M2": run("a", 0.95, 60),                                                        # old sign, confident
    "M3": (run("c", 0.95, 3) + run("e", 0.95, 3)) * 10,                              # confident, runs of 99 ms
    "M4": (run("a", 0.55, 1, top2="b", conf2=0.4) + run("b", 0.5, 1, top2="a", conf2=0.45)) * 30,  # split a/b
}


class TestTraceReportW3(unittest.TestCase):
    def analyse(self, frames, expected="a,b", **kw):
        return rep.analyse(make_trace(frames), rep.parse_expected(expected), **kw)

    def test_6e_each_hypothesis_is_main_cause(self):
        for code, middle in TRANSITIONS.items():
            res = self.analyse(HOLD_A + middle + NEW_B)
            self.assertEqual(res["main_cause"], code, (code, res["totals"]))
            self.assertEqual(len(res["segments"]), 2, code)        # a -> b, then after b to the end
            s = res["segments"][0]
            self.assertEqual((s["old"], s["new"], s["end_reason"], s["closing_label"], s["reached_new"]),
                             ("a", "b", "emit", "b", True), code)
            c = s["counts"]
            self.assertEqual(c["hold"]["windows"], 50, code)       # windows 11..60 (emission at window 10)
            self.assertEqual(c["stable"]["windows"], 10, code)     # 'b' run before its emission (330 ms)
            self.assertEqual(c["M2"]["windows"], (9 if code != "M2" else 69), code)  # 'a' windows 61..69 after hold
            if code != "M2":
                self.assertEqual(c[code]["windows"], 60, code)
            self.assertGreater(res["shares"][code], 0.5)
            self.assertAlmostEqual(sum(res["shares"].values()), 1.0, places=9)
            last = res["segments"][1]
            self.assertEqual((last["old"], last["new"], last["end_reason"]), ("b", None, "end"))
            self.assertEqual(last["transition_ms"], 0.0)            # 'b' still held at the end: all hold

    def test_6e_m4_without_expected_uses_closing_label(self):
        res = self.analyse(HOLD_A + TRANSITIONS["M4"] + NEW_B, expected=None)
        self.assertEqual(res["segments"][0]["new"], "b")
        self.assertEqual(res["main_cause"], "M4")
        res_other = self.analyse(HOLD_A + TRANSITIONS["M4"] + NEW_B, expected="a,c")  # another pair: not M4
        self.assertEqual(res_other["segments"][0]["new"], "c")
        self.assertEqual(res_other["segments"][0]["counts"]["M4"]["windows"], 0)
        self.assertEqual(res_other["main_cause"], "M1")

    def test_6e_m0_motion_pose(self):
        res = rep.analyse(make_trace(HOLD_A + NEW_B, rearm_mode="motion_pose"), None)
        self.assertTrue(res["m0"])
        self.assertEqual(res["main_cause"], "M0")
        text = rep.render(res, "x.json")
        self.assertIn("Nguyên nhân chính: M0", text)
        r = make_trace(HOLD_A, rearm_mode="motion_pose")
        del r["window_trace"]                                        # M0 does not need a trace
        self.assertEqual(rep.analyse(r, None)["main_cause"], "M0")

    def test_6e_reset_and_onset(self):
        # 'a' stuck after the hold (M2), hand withdrawn 16 frames (528 ms >= hand_lost_ms), then 'b' signed again
        frames = HOLD_A + TRANSITIONS["M2"] + [None] * 16 + NEW_B
        res = self.analyse(frames)
        s0 = res["segments"][0]
        self.assertEqual((s0["old"], s0["new"], s0["end_reason"], s0["closing_label"], s0["reached_new"]),
                         ("a", "b", "reset", None, False))
        self.assertEqual(s0["counts"]["M2"]["windows"], 69)
        self.assertEqual(s0["counts"]["stable"]["windows"], 0)
        self.assertEqual(res["main_cause"], "M2")
        self.assertEqual(len(res["segments"]), 2)                    # the 'b' run after the reset is onset
        self.assertEqual(res["segments"][1]["old"], "b")
        n_seg = sum(sum(c["windows"] for c in s["counts"].values()) for s in res["segments"])
        self.assertEqual(n_seg, len(make_trace(frames)["window_trace"]["entries"]) - 11 - 11)  # 2 onsets of 11

    def test_6e_expected_alignment_after_reset(self):
        # a -> b emitted, 'b' withdrawn and signed again (emitted again): both 'b' segments move towards 'c'
        frames = HOLD_A + NEW_B + [None] * 16 + NEW_B
        res = self.analyse(frames, expected="a,b,c")
        self.assertEqual([(s["old"], s["new"], s["end_reason"]) for s in res["segments"]],
                         [("a", "b", "emit"), ("b", "c", "reset"), ("b", "c", "end")])
        res = self.analyse(frames, expected="a,b")                   # after the last expected sign: no new
        self.assertEqual([s["new"] for s in res["segments"]], ["b", None, None])

    def test_6e_hold_ms(self):
        res = self.analyse(HOLD_A + TRANSITIONS["M2"] + NEW_B, hold_ms=0.0)
        c = res["segments"][0]["counts"]
        self.assertEqual((c["hold"]["windows"], c["M2"]["windows"]), (0, 119))  # every 'a' window after its emission

    def test_6e_window_time_capped(self):
        entries = make_trace(HOLD_A[:3] + [None] * 16 + HOLD_A[:2])["window_trace"]["entries"]
        times = rep.window_times(entries, 300.0)
        self.assertEqual(len(times), 5)
        self.assertAlmostEqual(times[0], STEP)
        self.assertEqual(times[2], 300.0)                            # 17 x 33 ms gap capped at hand_lost_ms
        self.assertAlmostEqual(times[4], STEP)                       # last entry: median interval

    def test_6e_truncated_flag_and_missing_trace(self):
        r = make_trace(HOLD_A + TRANSITIONS["M2"] + NEW_B)
        r["window_trace"]["truncated"] = True
        r["window_trace"]["n_windows"] = 999
        res = rep.analyse(r, None)
        self.assertTrue(res["truncated"])
        self.assertIn("TRACE BỊ CẮT", rep.render(res, "x.json"))
        del r["window_trace"]
        with self.assertRaises(ValueError):
            rep.analyse(r, None)

    def test_6e_cli_deterministic(self):
        os.makedirs(TMP_PARENT, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="vslt_p15_w3_", dir=TMP_PARENT)
        try:
            trace = os.path.join(tmp, "trace.json")
            with open(trace, "w", encoding="utf-8") as f:
                json.dump(make_trace(HOLD_A + TRANSITIONS["M3"] + NEW_B), f, ensure_ascii=False)
            outs = []
            for k in (1, 2):
                out = os.path.join(tmp, f"res{k}.json")
                p = subprocess.run([PY, os.path.join("scripts", "level1_trace_report.py"), "--trace", trace,
                                    "--expected", "a,b", "--out-json", out], cwd=PROJECT_ROOT, capture_output=True,
                                   env=ENV)
                self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
                with open(out, "rb") as f:
                    outs.append((p.stdout, f.read()))
            self.assertEqual(outs[0], outs[1])
            text = outs[0][0].decode("utf-8")
            self.assertIn("Nguyên nhân chính (§5: một mã > 50% thời gian chuyển): M3", text)
            data = json.loads(outs[0][1].decode("utf-8"))
            self.assertEqual(data["main_cause"], "M3")
            del_trace = os.path.join(tmp, "notrace.json")
            r = make_trace(HOLD_A)
            del r["window_trace"]
            with open(del_trace, "w", encoding="utf-8") as f:
                json.dump(r, f)
            p = subprocess.run([PY, os.path.join("scripts", "level1_trace_report.py"), "--trace", del_trace],
                               cwd=PROJECT_ROOT, capture_output=True, env=ENV)
            self.assertEqual(p.returncode, 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
