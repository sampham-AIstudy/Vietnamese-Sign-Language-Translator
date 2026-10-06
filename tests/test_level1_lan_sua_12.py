"""
Plan 15 lần sửa 12 (docs/plans/15-lan-sua-12.md): motion gate of the label decoder (G1), handedness lock (H1), configs.
Pure logic on controlled inputs (fixed hand shapes / fake classifiers); no data or checkpoint needed.
"""
import json
import os
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import scripts.level1_rearm_check as rc  # noqa: E402
from src.inference.level1_core import (HAND_LOCK_FRAMES, OPTIONAL_CONFIG_SPEC, HandednessLock,  # noqa: E402
                                       load_level1_config, validate_level1_config)
from src.inference.level1_segmenter import Level1LabelDecoder, MOTION_GATE_KEY  # noqa: E402
from tests.test_level1_segmenter import PARAMS, SPEED, hand_at  # noqa: E402

DEC = {"cls_window_ms": 200, "cls_conf": 0.9, "cls_stable_ms": 120, "hand_lost_ms": 300}
DT = 40.0
REV8 = os.path.join(PROJECT_ROOT, "configs", "level1_demo_classifier_rev8.json")
REV9 = os.path.join(PROJECT_ROOT, "configs", "level1_demo_classifier_rev9.json")


def ok(label, conf=0.95):
    return {"status": "ok", "prediction": label, "confidence": conf}


def run_decoder(decoder, frames):
    """frames: [(label, moving)] one hand frame each, DT apart -> [(frame_index, prediction)]."""
    out = []
    for i, (label, moving) in enumerate(frames):
        e = decoder.push(i * DT, True, ok(label), moving=moving)
        if e is not None:
            out.append((i, e.prediction))
    return out


class TestMotionGateDecoderG1(unittest.TestCase):
    def test_absent_or_false_gate_ignores_moving(self):
        frames = [("a", False)] * 6 + [("x", True)] * 6 + [("b", False)] * 6
        ref = run_decoder(Level1LabelDecoder(DEC), [(lab, False) for lab, _ in frames])
        for params in (DEC, {**DEC, MOTION_GATE_KEY: False}):
            with self.subTest(params=params):
                d = Level1LabelDecoder(params)
                self.assertFalse(d.motion_gate)
                self.assertEqual(run_decoder(d, frames), ref)
                self.assertEqual(d.n_gated, 0)
        self.assertEqual([lab for _, lab in ref], ["a", "x", "b"])

    def test_gate_drops_the_label_of_a_moving_hand(self):
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        got = run_decoder(d, [("a", False)] * 6 + [("x", True)] * 6 + [("b", False)] * 6)
        self.assertEqual([lab for _, lab in got], ["a", "b"])
        self.assertEqual(d.n_gated, 6)
        # a is emitted after cls_stable_ms on still frames (frame 3 = 120 ms after frame 0), b likewise after frame 12
        self.assertEqual([i for i, _ in got], [3, 15])

    def test_moving_frame_restarts_the_run(self):
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        # still a for 2 frames, one moving frame, still a again: the run starts again after the moving frame
        got = run_decoder(d, [("a", False)] * 2 + [("a", True)] + [("a", False)] * 5)
        self.assertEqual(got, [(6, "a")])

    def test_gate_never_emits_while_moving(self):
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        self.assertEqual(run_decoder(d, [("a", True)] * 30), [])

    def test_gate_with_dropout_debounce(self):
        # a moving frame is not a dropout: the debounce does not carry the run over it
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True, "dropout_tolerance_ms": 100.0})
        got = run_decoder(d, [("a", False)] * 2 + [("a", True)] + [("a", False)] * 3)
        self.assertEqual(got, [])

    def test_variant_of_the_last_label_is_not_gated(self):
        # a then the motion of â (diacritic variant of a): the motion is part of the sign, the variant replaces a
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        frames = [("a", False)] * 5 + [("â", True)] * 5
        out = []
        for i, (label, moving) in enumerate(frames):
            e = d.push(i * DT, True, ok(label), moving=moving)
            if e is not None:
                out.append((i, e.prediction, e.action))
        self.assertEqual(out, [(3, "a", "append"), (8, "â", "replace")])
        # without the base letter emitted just before, a moving variant is gated like any label
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        self.assertEqual(run_decoder(d, [("b", False)] * 5 + [("â", True)] * 10), [(3, "b")])

    def test_diacritic_fusion_variants_not_gated(self):
        from src.inference.level1_core import Level1Speller
        # e followed by circumflex motion predicted as â: not gated because â is in DIACRITIC_FUSION["e"]
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        sp = Level1Speller(0.5, unikey_mode=True)
        frames = [("e", False)] * 5 + [("â", True)] * 5
        out = []
        for i, (label, moving) in enumerate(frames):
            e = d.push(i * DT, True, ok(label), moving=moving)
            if e is not None:
                out.append((i, e.prediction, e.action))
                sp.on_label(i, e)
        self.assertEqual(out, [(3, "e", "append"), (8, "â", "append")])
        self.assertEqual(sp.text, "ê")

        # o followed by circumflex motion predicted as â: not gated
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        sp = Level1Speller(0.5, unikey_mode=True)
        frames = [("o", False)] * 5 + [("â", True)] * 5
        out = []
        for i, (label, moving) in enumerate(frames):
            e = d.push(i * DT, True, ok(label), moving=moving)
            if e is not None:
                out.append((i, e.prediction, e.action))
                sp.on_label(i, e)
        self.assertEqual(out, [(3, "o", "append"), (8, "â", "append")])
        self.assertEqual(sp.text, "ô")

        # u followed by hook motion predicted as ơ: not gated
        d = Level1LabelDecoder({**DEC, MOTION_GATE_KEY: True})
        sp = Level1Speller(0.5, unikey_mode=True)
        frames = [("u", False)] * 5 + [("ơ", True)] * 5
        out = []
        for i, (label, moving) in enumerate(frames):
            e = d.push(i * DT, True, ok(label), moving=moving)
            if e is not None:
                out.append((i, e.prediction, e.action))
                sp.on_label(i, e)
        self.assertEqual(out, [(3, "u", "append"), (8, "ơ", "append")])
        self.assertEqual(sp.text, "ư")

    def test_gate_must_be_bool(self):
        for bad in (1, 0, "true", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Level1LabelDecoder({**DEC, MOTION_GATE_KEY: bad})


class TestConfigG1(unittest.TestCase):
    def _raw(self, value):
        with open(REV8, encoding="utf-8") as f:
            raw = json.load(f)
        raw[MOTION_GATE_KEY] = {"value": value, "source": "design", "reason": "test"}
        return raw

    def test_optional_key(self):
        self.assertEqual(OPTIONAL_CONFIG_SPEC[MOTION_GATE_KEY], ("bool", "bool"))
        self.assertIs(validate_level1_config(self._raw(True))[MOTION_GATE_KEY], True)
        for bad in (1, "true"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_level1_config(self._raw(bad))

    def test_rev9_is_rev8_plus_the_gate(self):
        rev8 = load_level1_config(REV8)["values"]
        rev9 = load_level1_config(REV9)["values"]
        self.assertNotIn(MOTION_GATE_KEY, rev8)
        self.assertIs(rev9[MOTION_GATE_KEY], True)
        self.assertEqual({k: v for k, v in rev9.items() if k != MOTION_GATE_KEY}, rev8)
        self.assertEqual(rev9["rearm_mode"], "classifier")

    def test_default_config_unchanged(self):
        values = load_level1_config(os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json"))["values"]
        self.assertNotIn(MOTION_GATE_KEY, values)
        self.assertEqual(values["rearm_mode"], "motion_pose")


def _gate_chain():
    """Still hand (label a), hand moving down (label x), still hand at the new place (label b), DT apart; the fake
    classifier gives the label of the window's last frame."""
    frames, labels = [], []
    y = 0.3
    for _ in range(10):
        frames.append(hand_at(y))
        labels.append("a")
    for k in range(8):
        y = 0.3 + SPEED * (k + 1) * DT / 1000.0
        frames.append(hand_at(y))
        labels.append("x")
    for _ in range(10):
        frames.append(hand_at(y))
        labels.append("b")
    T = len(frames)
    sd = {"raw": np.stack(frames).astype(np.float32), "detected": np.ones(T, bool), "handedness": ["Left"] * T,
          "timestamps_ms": np.arange(T) * DT, "width": 640, "height": 480}
    return sd, labels


class TestDecodeChainG1(unittest.TestCase):
    """decode_chain (the D4 check) runs the segmenter beside the decoder exactly when cls_motion_gate is true."""

    def _run(self, gate):
        sd, labels = _gate_chain()
        ts_all = sd["timestamps_ms"]

        def classify(seg):
            i = int(np.where(np.abs(ts_all - seg.t_emit_ms) < 1e-6)[0][0])
            return ok(labels[i])
        params = {**PARAMS, **DEC}
        if gate is not None:
            params[MOTION_GATE_KEY] = gate
        return rc.decode_chain(sd, params, classify, 2)

    def test_without_gate_the_transition_is_emitted(self):
        for gate in (None, False):
            with self.subTest(gate=gate):
                dec = self._run(gate)
                self.assertEqual([lab for _, lab in dec["final"]], ["a", "x", "b"])
                self.assertEqual(dec["n_gated"], 0)

    def test_with_gate_only_the_still_signs(self):
        dec = self._run(True)
        self.assertEqual([lab for _, lab in dec["final"]], ["a", "b"])
        self.assertGreater(dec["n_gated"], 0)


class TestHandednessLockH1(unittest.TestCase):
    def test_majority_of_mediapipe_labels(self):
        for labels, expected in ((["Right"] * 10 + ["Left"] * 5, "Right"), (["Left"] * 8 + ["Right"] * 7, "Left")):
            with self.subTest(expected=expected):
                lock = HandednessLock()
                self.assertEqual([lock.update(x) for x in labels], labels)    # unchanged while counting
                self.assertTrue(lock.locked)
                self.assertEqual(lock.label, expected)
                self.assertEqual([lock.update(x) for x in ("Left", "Right", "")], [expected] * 3)

    def test_no_assumed_mapping(self):
        # a right hand on a mirroring camera: MediaPipe says 'Right'; the lock keeps 'Right' (never flips it to 'Left')
        lock = HandednessLock(3)
        for _ in range(3):
            lock.update("Right")
        self.assertEqual(lock.label, "Right")

    def test_other_labels_not_counted(self):
        lock = HandednessLock(3)
        self.assertEqual(lock.update(""), "")
        self.assertEqual(lock.n_votes, 0)
        self.assertFalse(lock.locked)

    def test_default_and_bad_lock_frames(self):
        self.assertEqual(HandednessLock().lock_frames, HAND_LOCK_FRAMES)
        self.assertEqual(HAND_LOCK_FRAMES % 2, 1)
        for bad in (0, -1, 1.5, True, "3"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                HandednessLock(bad)


if __name__ == "__main__":
    unittest.main()
