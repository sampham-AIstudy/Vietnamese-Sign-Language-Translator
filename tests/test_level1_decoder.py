"""
Plan 15 lần sửa 4 §3.2 / §3.3 / §5 AC-D1…D9: the classifier label decoder (Level1LabelDecoder), the sliding window
(WindowBuffer), VARIANT_BASE, the new config keys and Level1Speller.on_label.

The result streams and landmark sequences below are controlled synthetic data built in this test to check the logic
(dữ liệu tổng hợp có kiểm soát để kiểm logic, không phải dữ liệu thật); the decoder parameters are test-only values
(PARAMS), not configs/level1_realtime.json (except AC-D8, which loads the real config).
"""
import copy
import json
import os
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.fingerspelling_compose import LETTERS, compose  # noqa: E402
from src.inference.level1_core import Level1Speller, load_level1_config, validate_level1_config  # noqa: E402
from src.inference.level1_segmenter import (  # noqa: E402
    VARIANT_BASE, LabelEmit, Level1LabelDecoder, SignSegment, WindowBuffer)

CONFIG = os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")
CKPT = os.path.join(PROJECT_ROOT, "checkpoints", "alphabet_best.pt")
PARAMS = {"cls_window_ms": 1000, "cls_conf": 0.9, "cls_stable_ms": 300, "hand_lost_ms": 300}
DT = 40.0
W, H = 640, 480


def ok(label, conf=0.95):
    return {"status": "ok", "prediction": label, "confidence": conf}


def stream(spec, t0=0.0):
    """spec: list of (label | None for 'no hand', duration_ms[, conf]) -> frames [(ts, has_hand, result)] every DT ms;
    the label of a hand frame becomes an 'ok' result with that confidence (default 0.95)."""
    frames, t = [], t0
    for item in spec:
        label, dur = item[0], item[1]
        conf = item[2] if len(item) > 2 else 0.95
        end = t + dur
        while t < end - 1e-9:
            frames.append((t, label is not None, ok(label, conf) if label is not None else None))
            t += DT
    return frames, t


def decode(frames, dec=None, params=PARAMS):
    dec = dec or Level1LabelDecoder(params)
    out = []
    for ts, has_hand, result in frames:
        e = dec.push(ts, has_hand, result)
        if e is not None:
            out.append(e)
    return out


class TestDecoderD1D5(unittest.TestCase):
    def test_d1_a_then_b(self):
        frames, _ = stream([("a", 500), ("b", 500)])
        em = decode(frames)
        self.assertEqual([e.prediction for e in em], ["a", "b"])
        self.assertEqual([e.action for e in em], ["append", "append"])
        for e, first in zip(em, (0.0, 520.0)):
            self.assertEqual(e.run_since_ms, first)
            self.assertGreaterEqual(e.ts_ms, first + PARAMS["cls_stable_ms"])
            self.assertLessEqual(e.ts_ms, first + PARAMS["cls_stable_ms"] + DT)  # at most one frame late
            self.assertEqual(e.confidence, 0.95)
            self.assertEqual(e.result, ok(e.prediction))
        self.assertEqual([e.seq for e in em], [1, 2])

    def test_d2_low_conf_or_short_run_no_emit(self):
        self.assertEqual(decode(stream([("a", 2000, 0.85)])[0]), [])
        frames, _ = stream([("a", 200), ("b", 500)])
        self.assertEqual([e.prediction for e in decode(frames)], ["b"])
        # alternating every frame: no run reaches cls_stable_ms
        alt = [(k * DT, True, ok("a" if k % 2 else "b")) for k in range(50)]
        self.assertEqual(decode(alt), [])
        # a low-confidence frame breaks the run
        frames, _ = stream([("a", 200), ("a", 40, 0.5), ("a", 200)])
        self.assertEqual(decode(frames), [])
        # a status other than 'ok' breaks the run too
        frames = [(k * DT, True, ok("a") if k != 5 else {"status": "invalid"}) for k in range(20)]
        self.assertEqual([e.ts_ms for e in decode(frames)], [6 * DT + 320.0])

    def test_d2_missing_result_does_not_break_the_run(self):
        """result None on a hand frame (window too short / job dropped) = no result for that frame: skipped."""
        frames = [(k * DT, True, ok("a") if k % 3 else None) for k in range(12)]
        em = decode(frames)
        self.assertEqual(len(em), 1)
        self.assertEqual(em[0].run_since_ms, 1 * DT)

    def test_d3_long_hold_once(self):
        self.assertEqual(len(decode(stream([("a", 5000)])[0])), 1)

    def test_d4_hand_lost_allows_repeat(self):
        frames, _ = stream([("a", 1000), (None, 400), ("a", 1000)])
        self.assertEqual([e.prediction for e in decode(frames)], ["a", "a"])
        frames, _ = stream([("a", 1000), (None, 200), ("a", 1000)])
        self.assertEqual([e.prediction for e in decode(frames)], ["a"])
        # exactly hand_lost_ms without a hand counts as lost
        frames, _ = stream([("a", 1000), (None, 320), ("a", 1000)])
        self.assertEqual(len(decode(frames)), 2)

    def test_d5_force_next_emits_again(self):
        frames, t = stream([("a", 1000)])
        dec = Level1LabelDecoder(PARAMS)
        em = decode(frames, dec)
        dec.force_next(t - DT)
        more, _ = stream([("a", 1000)], t0=t)
        em += decode(more, dec)
        self.assertEqual([e.prediction for e in em], ["a", "a"])
        self.assertEqual([e.action for e in em], ["append", "append"])

    def test_timestamps_strictly_increasing(self):
        dec = Level1LabelDecoder(PARAMS)
        dec.push(10.0, True, ok("a"))
        with self.assertRaises(ValueError):
            dec.push(10.0, True, ok("a"))
        with self.assertRaises(ValueError):
            dec.push(float("nan"), True, ok("a"))

    def test_parameters_checked(self):
        for key in PARAMS:
            with self.subTest(missing=key):
                with self.assertRaises(ValueError):
                    Level1LabelDecoder({k: v for k, v in PARAMS.items() if k != key})
        for key, bad in (("cls_window_ms", 0), ("cls_stable_ms", -1), ("cls_conf", 0.0), ("cls_conf", 1.5),
                         ("hand_lost_ms", 0), ("cls_conf", True)):
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(ValueError):
                    Level1LabelDecoder({**PARAMS, key: bad})


class TestVariantD6(unittest.TestCase):
    def test_d6_base_then_variant_replaces(self):
        em = decode(stream([("a", 500), ("â", 500)])[0])
        self.assertEqual([(e.prediction, e.action) for e in em], [("a", "append"), ("â", "replace")])

    def test_d6_other_orders_append(self):
        for spec, want in (([("â", 500), ("a", 500)], [("â", "append"), ("a", "append")]),
                           ([("a", 500), ("b", 500)], [("a", "append"), ("b", "append")]),
                           ([("a", 500), (None, 400), ("â", 500)], [("a", "append"), ("â", "append")])):
            with self.subTest(spec=spec):
                self.assertEqual([(e.prediction, e.action) for e in decode(stream(spec)[0])], want)
        # after force_next the variant is a new letter
        frames, t = stream([("a", 500)])
        dec = Level1LabelDecoder(PARAMS)
        em = decode(frames, dec)
        dec.force_next(t - DT)
        em += decode(stream([("â", 500)], t0=t)[0], dec)
        self.assertEqual([e.action for e in em], ["append", "append"])

    def test_d6_every_pair_replaces(self):
        for variant, base in VARIANT_BASE.items():
            with self.subTest(variant=variant):
                em = decode(stream([(base, 500), (variant, 500)])[0])
                self.assertEqual([(e.prediction, e.action) for e in em], [(base, "append"), (variant, "replace")])

    def test_d6_table_is_the_language_fact(self):
        self.assertEqual(VARIANT_BASE, {"ă": "a", "â": "a", "ê": "e", "ô": "o", "ơ": "o", "ư": "u", "đ": "d"})
        if os.path.exists(CKPT):
            import torch
            classes = list(torch.load(CKPT, map_location="cpu")["classes"])
        else:
            classes = list(LETTERS)
        for k, v in VARIANT_BASE.items():
            self.assertIn(k, classes)
            self.assertIn(v, classes)


def _rand_hand(rng):
    return rng.uniform(0.2, 0.8, size=(21, 3)).astype(np.float32)


class TestWindowBufferD7(unittest.TestCase):
    MIN = 4

    def _frames(self, n=40, gap=(10, 13), seed=0):
        """n frames every DT ms; frames in [gap[0], gap[1]) have no hand."""
        rng = np.random.default_rng(seed)
        out = []
        for k in range(n):
            has = not (gap[0] <= k < gap[1])
            out.append((k * DT, _rand_hand(rng) if has else None, "Right" if has else ""))
        return out

    def test_d7_segment_is_exactly_the_window(self):
        frames = self._frames()
        wb = WindowBuffer(PARAMS["cls_window_ms"], self.MIN)
        for i, (ts, lm, hd) in enumerate(frames):
            wb.push(ts, lm, hd, W, H)
            seg = wb.segment(ts)
            inside = [f for f in frames[:i + 1] if f[0] >= ts - PARAMS["cls_window_ms"] + 1e-6]
            n_hand = sum(1 for f in inside if f[1] is not None)
            if n_hand < self.MIN:
                self.assertIsNone(seg, i)
                continue
            self.assertIsInstance(seg, SignSegment)
            want_raw = np.stack([f[1] if f[1] is not None else np.zeros((21, 3), np.float32) for f in inside])
            self.assertTrue(np.array_equal(seg.raw_landmarks, want_raw), i)
            self.assertEqual(seg.raw_landmarks.dtype, np.float32)
            self.assertTrue(np.array_equal(seg.detected, np.array([f[1] is not None for f in inside])), i)
            self.assertTrue(np.array_equal(seg.handedness, np.array([f[2] for f in inside])), i)
            self.assertTrue(np.array_equal(seg.timestamps_ms, np.array([f[0] for f in inside])), i)
            self.assertEqual((seg.frame_width, seg.frame_height), (W, H))
            self.assertEqual((seg.t_start_ms, seg.t_end_ms, seg.t_emit_ms), (inside[0][0], inside[-1][0], ts))
            self.assertEqual(seg.close_reason, "window")

    def test_d7_segment_is_a_copy(self):
        frames = self._frames(n=20, gap=(0, 0))
        wb = WindowBuffer(PARAMS["cls_window_ms"], self.MIN)
        pushed = []
        for ts, lm, hd in frames:
            pushed.append(lm.copy())
            wb.push(ts, lm, hd, W, H)
            lm[:] = -1.0  # the caller reuses its array: the buffer kept its own copy
        a = wb.segment(frames[-1][0])
        a.raw_landmarks[:] = 7.0
        a.detected[:] = False
        b = wb.segment(frames[-1][0])
        self.assertTrue(np.array_equal(b.raw_landmarks, np.stack(pushed)))
        self.assertTrue(b.detected.all())

    def test_d7_too_few_hand_frames_none_and_size_change(self):
        wb = WindowBuffer(PARAMS["cls_window_ms"], self.MIN)
        rng = np.random.default_rng(1)
        for k in range(3):
            wb.push(k * DT, _rand_hand(rng), "Right", W, H)
        self.assertIsNone(wb.segment(2 * DT))
        wb.push(3 * DT, _rand_hand(rng), "Right", W, H)
        self.assertIsNotNone(wb.segment(3 * DT))
        wb.push(4 * DT, _rand_hand(rng), "Right", 320, 240)  # camera size changed: the window starts again
        self.assertIsNone(wb.segment(4 * DT))
        with self.assertRaises(ValueError):
            wb.push(4 * DT, _rand_hand(rng), "Right", 320, 240)  # timestamps must increase

    @unittest.skipUnless(os.path.exists(CKPT), "missing (gitignored checkpoint): checkpoints/alphabet_best.pt")
    def test_d7_classify_window_equals_hand_built_segment(self):
        from src.inference.level1_core import Level1Classifier
        clf = Level1Classifier.from_checkpoint(CKPT)
        frames = self._frames(n=60, gap=(20, 24), seed=3)
        wb = WindowBuffer(PARAMS["cls_window_ms"], clf.min_detected_frames)
        n_checked = 0
        for i, (ts, lm, hd) in enumerate(frames):
            wb.push(ts, lm, hd, W, H)
            seg = wb.segment(ts)
            if seg is None or i % 7:
                continue
            inside = [f for f in frames[:i + 1] if f[0] >= ts - PARAMS["cls_window_ms"] + 1e-6]
            hand = SignSegment(
                seq=99, raw_landmarks=np.stack([f[1] if f[1] is not None else np.zeros((21, 3), np.float32)
                                                for f in inside]).astype(np.float32),
                detected=np.array([f[1] is not None for f in inside]),
                handedness=np.array([f[2] for f in inside], dtype=object).astype(str),
                timestamps_ms=np.array([f[0] for f in inside], dtype=np.float64), frame_width=W, frame_height=H,
                t_start_ms=inside[0][0], t_end_ms=inside[-1][0], t_emit_ms=ts, close_reason="hold")
            self.assertEqual(clf.classify(seg, 5), clf.classify(hand, 5), i)
            n_checked += 1
        self.assertGreater(n_checked, 3)


class TestConfigD8(unittest.TestCase):
    def _raw(self):
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)

    def test_d8_real_config_loads(self):
        v = load_level1_config(CONFIG)["values"]
        self.assertEqual(v["rearm_mode"], "motion_pose")
        self.assertEqual((v["cls_window_ms"], v["cls_conf"], v["cls_stable_ms"]), (1000, 0.9, 300))
        raw = self._raw()
        for key in ("rearm_mode", "cls_window_ms", "cls_conf", "cls_stable_ms"):
            self.assertEqual(raw[key]["source"], "design", key)
        for key in ("cls_window_ms", "cls_conf", "cls_stable_ms"):
            self.assertIn("not an independent calibration", raw[key]["reason"], key)

    def test_d8_missing_key(self):
        for key in ("rearm_mode", "cls_window_ms", "cls_conf", "cls_stable_ms"):
            raw = self._raw()
            del raw[key]
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    validate_level1_config(raw)

    def test_d8_types_and_ranges(self):
        bad = (("rearm_mode", "pose"), ("rearm_mode", ""), ("rearm_mode", 1), ("rearm_mode", None),
               ("cls_window_ms", 0), ("cls_window_ms", -5), ("cls_window_ms", "1000"), ("cls_stable_ms", 0),
               ("cls_stable_ms", True), ("cls_conf", 0), ("cls_conf", 1.01), ("cls_conf", -0.1), ("cls_conf", True),
               ("cls_window_ms", float("nan")))
        for key, value in bad:
            raw = self._raw()
            raw[key] = dict(raw[key], value=value)
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    validate_level1_config(raw)
        for key, value in (("rearm_mode", "classifier"), ("cls_conf", 1.0), ("cls_conf", 0.5)):
            raw = self._raw()
            raw[key] = dict(raw[key], value=value)
            self.assertEqual(validate_level1_config(raw)[key], value)


def _emit(seq, label, action, ts=0.0, conf=0.95):
    return LabelEmit(seq=seq, ts_ms=ts, prediction=label, confidence=conf, action=action, run_since_ms=ts - 300.0,
                     result=ok(label, conf))


class TestSpellerOnLabelD9(unittest.TestCase):
    def test_d9_replace_base_letter(self):
        sp = Level1Speller(0.5)
        sp.on_label(1, _emit(1, "b", "append", 100.0))
        sp.on_label(2, _emit(2, "a", "append", 600.0))
        self.assertEqual(sp.tokens, ["b", "a"])
        d = sp.on_label(3, _emit(3, "â", "replace", 1100.0))
        self.assertEqual(sp.tokens, ["b", "â"])
        self.assertEqual(sp.text, compose(sp.tokens)["text"])
        self.assertEqual(sp.text, compose(["b", "â"])["text"])
        ev = sp.events[-1]
        self.assertEqual((ev["event"], ev["action"], ev["token"], ev["source"]), ("token", "replace", "â", "model"))
        self.assertEqual(ev["replaced"], "a")
        self.assertEqual(ev["t_ms"], 1100.0)
        self.assertTrue(d["accepted"])
        self.assertEqual(sp.events[0]["action"], "add")
        self.assertEqual(sp.events[0]["source"], "model")

    def test_d9_replace_when_last_is_not_the_base_appends(self):
        sp = Level1Speller(0.5)
        sp.on_label(1, _emit(1, "b", "append"))
        sp.on_label(2, _emit(2, "â", "replace"))
        self.assertEqual(sp.tokens, ["b", "â"])
        self.assertEqual(sp.events[-1]["action"], "add")
        sp2 = Level1Speller(0.5)
        sp2.on_label(1, _emit(1, "â", "replace"))  # empty token list
        self.assertEqual(sp2.tokens, ["â"])
        sp3 = Level1Speller(0.5)
        sp3.on_label(1, _emit(1, "a", "append"))
        sp3.on_word_gap()
        sp3.on_label(2, _emit(2, "â", "replace"))  # last token is the space
        self.assertEqual(sp3.tokens, ["a", " ", "â"])

    def test_d9_low_confidence_rejected(self):
        sp = Level1Speller(0.97)
        d = sp.on_label(1, _emit(1, "a", "append", conf=0.95))
        self.assertFalse(d["accepted"])
        self.assertEqual(sp.tokens, [])
        self.assertEqual(sp.rejected["prediction"], "a")
        self.assertEqual(sp.events[-1]["action"], "reject")



# ----------------------------------------------------------------------------------------------------------------------
# Plan 15 lần sửa 7 T1: AC-7b (own threshold and stable time for the 5 tone marks) and AC-7d (without the new keys the
# decoder is the decoder of D4 exactly). Streams are controlled synthetic data to check the logic, not accuracy.
# ----------------------------------------------------------------------------------------------------------------------
import subprocess  # noqa: E402
import types  # noqa: E402

TONE_LABELS = ("dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng")
PARAMS_T1 = {**PARAMS, "cls_conf_tone": 0.78, "cls_stable_ms_tone": 200}
BEFORE_REV7_COMMIT = "5e08fbd"  # src/inference/level1_segmenter.py of D4 / lần sửa 6 (before lần sửa 7)


def segmenter_module_at(commit):
    """src/inference/level1_segmenter.py at `commit`, loaded from `git show` into an in-memory module (nothing written)."""
    r = subprocess.run(["git", "show", f"{commit}:src/inference/level1_segmenter.py"], cwd=PROJECT_ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {commit}:src/inference/level1_segmenter.py failed: {r.stderr.strip()}")
    mod = types.ModuleType(f"_level1_segmenter_ref_{commit}")
    exec(compile(r.stdout, f"<git show {commit}:level1_segmenter.py>", "exec"), mod.__dict__)
    return mod


def random_stream(rng, n=400):
    """Hand frames every 20-60 ms with letters, tone marks, low confidences, other statuses, missing results and
    no-hand runs (some longer than hand_lost_ms)."""
    labels = ["a", "â", "b", "o", "ơ", *TONE_LABELS]
    frames, t, k = [], 0.0, 0
    while k < n:
        run = int(rng.integers(1, 26))
        kind = rng.random()
        label = labels[int(rng.integers(len(labels)))]
        conf = float(rng.choice([0.5, 0.77, 0.78, 0.8, 0.85, 0.89, 0.9, 0.95, 1.0]))  # one level per run
        for _ in range(run):
            t += float(rng.integers(20, 61))
            if kind < 0.1:
                frames.append((t, False, None))
            elif kind < 0.15:
                frames.append((t, True, None))
            elif kind < 0.2:
                frames.append((t, True, {"status": "too_few_frames"}))
            else:
                dip = rng.random() < 0.08                                # a single frame below every threshold
                frames.append((t, True, ok(label, 0.5 if dip else conf)))
            k += 1
    return frames


def emits(em):
    return [(e.seq, e.ts_ms, e.prediction, e.confidence, e.action, e.run_since_ms) for e in em]


class TestToneThresholdsT1(unittest.TestCase):
    def test_7b_tone_at_080_emitted_after_200_ms(self):
        for tone in TONE_LABELS:
            with self.subTest(tone=tone):
                em = decode(stream([(tone, 1000, 0.80)])[0], params=PARAMS_T1)
                self.assertEqual([(e.prediction, e.action) for e in em], [(tone, "append")])
                self.assertEqual(em[0].run_since_ms, 0.0)
                self.assertEqual(em[0].ts_ms - em[0].run_since_ms, 200.0)  # frames every 40 ms: exactly 200 ms
                self.assertEqual(em[0].confidence, 0.80)

    def test_7b_letter_at_080_rejected_letter_at_092_after_300_ms(self):
        self.assertEqual(decode(stream([("b", 2000, 0.80)])[0], params=PARAMS_T1), [])
        em = decode(stream([("b", 1000, 0.92)])[0], params=PARAMS_T1)
        self.assertEqual([e.prediction for e in em], ["b"])
        self.assertGreaterEqual(em[0].ts_ms - em[0].run_since_ms, 300.0)
        self.assertLessEqual(em[0].ts_ms - em[0].run_since_ms, 300.0 + DT)
        # a letter held 280 ms (>= the tone stable time, < cls_stable_ms) is not emitted
        self.assertEqual(decode(stream([("b", 280, 0.95), (None, 40)])[0], params=PARAMS_T1), [])

    def test_7b_tone_below_its_threshold_or_too_short(self):
        self.assertEqual(decode(stream([("dấu huyền", 2000, 0.77)])[0], params=PARAMS_T1), [])
        self.assertEqual(decode(stream([("dấu huyền", 160, 0.80), ("b", 200, 0.95)])[0], params=PARAMS_T1), [])

    def test_7b_letters_and_tones_in_one_stream(self):
        frames, _ = stream([("a", 500), ("dấu sắc", 400, 0.80), ("b", 500, 0.92), ("dấu nặng", 400, 0.79)])
        em = decode(frames, params=PARAMS_T1)
        self.assertEqual([e.prediction for e in em], ["a", "dấu sắc", "b", "dấu nặng"])
        stable = [e.ts_ms - e.run_since_ms for e in em]
        self.assertEqual(stable, [320.0, 200.0, 320.0, 200.0])

    def test_7b_thresholds_per_label(self):
        dec = Level1LabelDecoder(PARAMS_T1)
        for tone in TONE_LABELS:
            self.assertEqual(dec.thresholds(tone), (0.78, 200))
            self.assertTrue(dec.is_tone(tone))
        for letter in ("a", "â", "đ", "y"):
            self.assertEqual(dec.thresholds(letter), (0.9, 300))
            self.assertFalse(dec.is_tone(letter))
        old = Level1LabelDecoder(PARAMS)
        self.assertEqual(old.thresholds("dấu sắc"), (0.9, 300))       # fallback to cls_conf / cls_stable_ms
        self.assertEqual(old.p, PARAMS)                                  # no new key added to the parameters

    def test_7b_one_key_without_the_other(self):
        em = decode(stream([("dấu ngã", 1000, 0.80)])[0], params={**PARAMS, "cls_conf_tone": 0.78})
        self.assertEqual([e.ts_ms - e.run_since_ms for e in em], [320.0])    # stable time falls back to 300
        em = decode(stream([("dấu ngã", 1000, 0.95)])[0], params={**PARAMS, "cls_stable_ms_tone": 200})
        self.assertEqual([e.ts_ms - e.run_since_ms for e in em], [200.0])    # threshold falls back to 0.9
        self.assertEqual(decode(stream([("dấu ngã", 1000, 0.80)])[0], params={**PARAMS, "cls_stable_ms_tone": 200}),
                         [])

    def test_7b_new_parameters_checked(self):
        for key, bad in (("cls_conf_tone", 0.0), ("cls_conf_tone", 1.5), ("cls_conf_tone", True),
                         ("cls_conf_tone", float("nan")), ("cls_conf_tone", "0.8"), ("cls_stable_ms_tone", 0),
                         ("cls_stable_ms_tone", -1), ("cls_stable_ms_tone", None)):
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(ValueError):
                    Level1LabelDecoder({**PARAMS, key: bad})
        self.assertEqual(Level1LabelDecoder({**PARAMS, "cls_conf_tone": 1.0}).thresholds("dấu hỏi"), (1.0, 300))

    def test_7d_without_new_keys_same_as_d4_decoder(self):
        ref = segmenter_module_at(BEFORE_REV7_COMMIT)
        rng = np.random.default_rng(7)
        n_emits = 0
        for i in range(30):
            frames = random_stream(rng)
            new, old = Level1LabelDecoder(PARAMS), ref.Level1LabelDecoder(PARAMS)
            em_new, em_old = [], []
            for j, (ts, has_hand, result) in enumerate(frames):
                if j % 97 == 96:                                         # key n now and then, on both
                    new.force_next(ts - 1.0)
                    old.force_next(ts - 1.0)
                e = new.push(ts, has_hand, result)
                if e is not None:
                    em_new.append(e)
                e = old.push(ts, has_hand, result)
                if e is not None:
                    em_old.append(e)
                self.assertEqual((new._run_label, new._run_since, new.last_label),
                                 (old._run_label, old._run_since, old.last_label), (i, j))
            self.assertEqual(emits(em_new), emits(em_old), i)
            self.assertEqual([e.result for e in em_new], [e.result for e in em_old], i)
            n_emits += len(em_new)
        self.assertGreater(n_emits, 50)
        # same keys given explicitly with the letter values = the D4 decoder as well
        frames = random_stream(np.random.default_rng(8))
        same = {**PARAMS, "cls_conf_tone": PARAMS["cls_conf"], "cls_stable_ms_tone": PARAMS["cls_stable_ms"]}
        self.assertEqual(emits(decode(frames, params=same)), emits(decode(frames, dec=ref.Level1LabelDecoder(PARAMS))))

    def test_7d_tone_keys_change_only_tone_runs(self):
        """With the T1 keys, a stream without tone marks gives the emissions of the D4 decoder."""
        ref = segmenter_module_at(BEFORE_REV7_COMMIT)
        rng = np.random.default_rng(9)
        for i in range(10):
            frames = [(ts, h, r) for ts, h, r in random_stream(rng)
                      if not (r is not None and r.get("prediction") in TONE_LABELS)]
            self.assertEqual(emits(decode(frames, params=PARAMS_T1)),
                             emits(decode(frames, dec=ref.Level1LabelDecoder(PARAMS))), i)


if __name__ == "__main__":
    unittest.main()
