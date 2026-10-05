"""
Plan 15 AC-C (Level 1 core: src/inference/level1_core.py) and AC-T (src/inference/level1_timing.py).

C1 classify(segment) == POST /api/fingerspelling/sequence (prediction, prediction_kind, confidence, candidates, ...) on
   4 hauuto training clips fixed by sample_id (two code paths on the same input; not accuracy).
C2 checkpoint without classes / preprocessing -> ValueError. C3 fewer hand frames than min_detected_frames ->
   status too_few_frames, no token. C4-C7 speller (threshold, keys, text == compose(tokens), event order).
C8 load_level1_config: missing key / missing source or reason / move_speed <= still_speed / word_gap_ms < hand_lost_ms
-> ValueError; the real configs/level1_realtime.json loads.
AC-T summarize / StageTimes / rate_from_timestamps against numpy.
The speller inputs ("ok(pred, conf)") are classifier-shaped results built in the test to drive the speller logic.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_core import CONFIG_SPEC, load_level1_config, validate_level1_config  # noqa: E402

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")


def _real_raw():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestConfigC8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_cfg_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _write(self, raw, name="c.json"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        return p

    def test_real_config_loads(self):
        cfg = load_level1_config(CONFIG_PATH)
        self.assertEqual(set(cfg["values"]), set(CONFIG_SPEC))
        self.assertEqual(len(cfg["sha256"]), 64)
        self.assertGreater(cfg["values"]["move_speed"], cfg["values"]["still_speed"])
        self.assertGreaterEqual(cfg["values"]["word_gap_ms"], cfg["values"]["hand_lost_ms"])
        for k in CONFIG_SPEC:
            self.assertTrue(cfg["raw"][k]["reason"].strip())

    def test_missing_key(self):
        for key in CONFIG_SPEC:
            raw = _real_raw()
            del raw[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_level1_config(self._write(raw))

    def test_missing_source_or_reason(self):
        for field in ("source", "reason"):
            for key in ("hold_ms", "accept_confidence", "camera_api"):
                raw = _real_raw()
                del raw[key][field]
                with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                    validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["reason"] = "  "
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["source"] = "measured"
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw = _real_raw()
        raw["hold_ms"]["source"] = "calibrated: reports/x.json@abc123"
        self.assertEqual(validate_level1_config(raw)["hold_ms"], raw["hold_ms"]["value"])

    def test_move_not_above_still(self):
        raw = _real_raw()
        raw["move_speed"]["value"] = raw["still_speed"]["value"]
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_word_gap_below_hand_lost(self):
        raw = _real_raw()
        raw["word_gap_ms"]["value"] = raw["hand_lost_ms"]["value"] - 1
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_wrong_types(self):
        for key, bad in (("hold_ms", "400"), ("min_sign_frames", 2.5), ("accept_confidence", 1.5),
                         ("camera_api", "v4l"), ("font_paths", []), ("still_speed", True), ("top_k", 0)):
            raw = _real_raw()
            raw[key]["value"] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_level1_config(raw)
        raw = _real_raw()
        raw["unknown_key"] = copy.deepcopy(raw["hold_ms"])
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

    def test_not_json(self):
        p = os.path.join(self.tmp, "bad.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{not json")
        with self.assertRaises(ValueError):
            load_level1_config(p)

    def test_c8b_tail_still_keep_ms(self):
        # Missing tail_still_keep_ms -> ValueError
        raw = _real_raw()
        if "tail_still_keep_ms" in raw:
            del raw["tail_still_keep_ms"]
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

        # tail_still_keep_ms <= 0 -> ValueError
        raw = _real_raw()
        raw["tail_still_keep_ms"] = {"value": 0, "source": "design", "reason": "test"}
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw["tail_still_keep_ms"]["value"] = -10
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

        # tail_still_keep_ms > hold_ms -> ValueError
        raw = _real_raw()
        raw["hold_ms"] = {"value": 400, "source": "design", "reason": "test"}
        raw["tail_still_keep_ms"] = {"value": 450, "source": "design", "reason": "test"}
        with self.assertRaises(ValueError):
            validate_level1_config(raw)

        # Real config loads and has valid tail_still_keep_ms
        cfg = load_level1_config(CONFIG_PATH)
        self.assertIn("tail_still_keep_ms", cfg["values"])
        self.assertGreater(cfg["values"]["tail_still_keep_ms"], 0)
        self.assertLessEqual(cfg["values"]["tail_still_keep_ms"], cfg["values"]["hold_ms"])



# ----------------------------------------------------------------------------------------------------------------------
# B2: classifier (C1-C3), speller (C4-C7), timing (AC-T)
# ----------------------------------------------------------------------------------------------------------------------
import numpy as np  # noqa: E402

from src.inference.fingerspelling_compose import compose  # noqa: E402
from src.inference.level1_core import Level1Classifier, Level1Speller  # noqa: E402
from src.inference.level1_segmenter import SignSegment  # noqa: E402
from src.inference.level1_timing import StageTimes, rate_from_timestamps, summarize  # noqa: E402

for _p in (os.path.join(PROJECT_ROOT, "scripts"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import hand_live_check as H  # noqa: E402

# C1 sample, fixed by sample_id: hauuto training clips (equivalence of two code paths, not accuracy)
C1_SAMPLE_IDS = ("hauuto_a_hau_A_001", "hauuto_tone_f_hau_A_001", "hauuto_a_khoi_A_001", "hauuto_b_vy_A_001")
_C1_MISSING = [p for p in (H.MANIFEST, H.DEPLOYED_CKPT) if not os.path.exists(p)]


def segment_from_npz(npz, width, height, fps, seq=1):
    """SignSegment holding one whole training clip (as the app would emit it), timestamps i * 1000 / fps."""
    det = np.asarray(npz["detected_mask"], dtype=bool)
    ts = np.array([H.timestamp_ms(i, fps) for i in range(len(det))], dtype=np.float64)
    return SignSegment(seq=seq, raw_landmarks=np.asarray(npz["raw_landmarks"], dtype=np.float32).copy(),
                       detected=det.copy(), handedness=np.array(list(npz["handedness_label"])),
                       timestamps_ms=ts, frame_width=int(width), frame_height=int(height),
                       t_start_ms=float(ts[0]), t_end_ms=float(ts[-1]), t_emit_ms=float(ts[-1]),
                       close_reason="end_of_stream")


@unittest.skipUnless(not _C1_MISSING, "missing (gitignored data / checkpoint): " + ", ".join(_C1_MISSING))
class TestClassifierC1C3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import backend.main as api
        cls.api = api
        cls._saved = (api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta)
        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = H.DEPLOYED_CKPT, None, None
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started
        cls.clf = Level1Classifier.from_checkpoint(H.DEPLOYED_CKPT)
        rows = {r["sample_id"]: r for r in H.read_manifest()}
        cls.rows = [rows[s] for s in C1_SAMPLE_IDS]

    @classmethod
    def tearDownClass(cls):
        cls.api.ALPHABET_CKPT = cls._saved[0]
        cls.api._alphabet_model, cls.api._alphabet_meta = None, None

    def test_c1_classify_equals_sequence_endpoint(self):
        keys = ("prediction", "prediction_kind", "confidence", "candidates", "frames", "detected_frames",
                "model_type", "checkpoint")
        for row in self.rows:
            with self.subTest(sample_id=row["sample_id"]):
                npz = H.load_npz(os.path.join(H.KAGGLE_DIR, row["landmark_path"]))
                w, h, fps = int(row["width"]), int(row["height"]), float(row["fps"])
                body = H.body_from_npz(npz, w, h, fps)
                resp = self.client.post(H.SEQ_PATH, json=body)
                self.assertEqual(resp.status_code, 200, resp.text)
                api = resp.json()
                mine = self.clf.classify(segment_from_npz(npz, w, h, fps), body["top_k"])
                self.assertEqual(mine["status"], "ok")
                for k in keys:
                    self.assertEqual(mine[k], api[k], k)

    def test_c2_checkpoint_without_classes_or_preprocessing(self):
        import torch
        ckpt = torch.load(H.DEPLOYED_CKPT, map_location="cpu")
        tmp = tempfile.mkdtemp(prefix="vslt_p15_ckpt_")
        try:
            for key in ("classes", "preprocessing"):
                bad = {k: v for k, v in ckpt.items() if k != key}
                p = os.path.join(tmp, f"no_{key}.pt")
                torch.save(bad, p)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    Level1Classifier.from_checkpoint(p)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_c3_too_few_frames(self):
        row = self.rows[0]
        npz = H.load_npz(os.path.join(H.KAGGLE_DIR, row["landmark_path"]))
        seg = segment_from_npz(npz, int(row["width"]), int(row["height"]), float(row["fps"]))
        keep = np.flatnonzero(seg.detected)[: self.clf.min_detected_frames - 1]
        seg.detected = np.zeros_like(seg.detected)
        seg.detected[keep] = True
        seg.raw_landmarks[~seg.detected] = 0.0
        r = self.clf.classify(seg, 5)
        self.assertEqual(r["status"], "too_few_frames")
        self.assertNotIn("prediction", r)
        sp = Level1Speller(0.5)
        sp.on_result(1, r)
        self.assertEqual(sp.tokens, [])
        self.assertFalse(sp.key("accept"))  # no candidate to accept
        self.assertEqual(sp.tokens, [])

    def test_warmup_returns_duration(self):
        self.assertGreaterEqual(self.clf.warmup(), 0.0)


def ok(pred, conf):
    """A classifier result shaped like Level1Classifier.classify (built in the test to drive the speller)."""
    return {"status": "ok", "prediction": pred, "confidence": conf, "candidates": [{"class": pred}]}


class TestSpellerC4C7(unittest.TestCase):
    def test_c4_threshold_and_accept(self):
        sp = Level1Speller(0.6)
        d = sp.on_result(1, ok("b", 0.6))
        self.assertTrue(d[0]["accepted"])
        self.assertEqual(sp.tokens, ["b"])
        d = sp.on_result(2, ok("a", 0.5999))
        self.assertFalse(d[0]["accepted"])
        self.assertEqual(sp.tokens, ["b"])
        self.assertEqual(sp.rejected["prediction"], "a")
        self.assertTrue(sp.key("accept"))
        self.assertEqual(sp.tokens, ["b", "a"])
        self.assertFalse(sp.key("accept"))  # consumed
        sources = [(e["action"], e["token"], e["source"]) for e in sp.events]
        self.assertEqual(sources, [("add", "b", "model"), ("reject", "a", "model"), ("add", "a", "key")])

    def test_c5_keys(self):
        sp = Level1Speller(0.5)
        self.assertFalse(sp.key("backspace"))  # empty: no error
        self.assertFalse(sp.key("space"))      # nothing to separate yet
        self.assertFalse(sp.key("repeat"))
        sp.on_result(1, ok("o", 0.9))
        self.assertTrue(sp.key("repeat"))
        self.assertEqual(sp.tokens, ["o", "o"])
        self.assertTrue(sp.key("space"))
        self.assertFalse(sp.key("space"))      # no double space
        self.assertEqual(sp.tokens, ["o", "o", " "])
        self.assertFalse(sp.key("repeat"))     # last token is not a letter
        self.assertTrue(sp.key("backspace"))
        self.assertEqual(sp.tokens, ["o", "o"])
        sp.on_result(2, ok("dấu sắc", 0.9))
        self.assertFalse(sp.key("repeat"))     # a tone mark is not repeated
        self.assertTrue(sp.key("clear"))
        self.assertEqual(sp.tokens, [])
        self.assertTrue(all(e["source"] == "key" for e in sp.events if e.get("key")))
        with self.assertRaises(ValueError):
            sp.key("x")

    def test_ack_tone_keys(self):
        sp = Level1Speller(0.5)
        tones = ["tone_1", "tone_2", "tone_3", "tone_4", "tone_5"]
        expected_tones = ["dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng"]
        
        for i, name in enumerate(tones):
            self.assertTrue(sp.key(name))
            self.assertEqual(sp.tokens[-1], expected_tones[i])
            event = sp.events[-1]
            self.assertEqual(event["source"], "key")
            self.assertEqual(event["key"], name)
            self.assertEqual(sp.text, compose(sp.tokens)["text"])
            
        with self.assertRaises(ValueError):
            sp.key("tone_6")

    def test_c6_text_is_compose(self):
        for tokens, text in ((["b", "a", "dấu sắc"], "bá"), (["m", "e", "dấu nặng", " ", "c", "a", "dấu sắc"], "mẹ cá")):
            sp = Level1Speller(0.5)
            for i, t in enumerate(tokens):
                if t == " ":
                    sp.key("space")
                else:
                    sp.on_result(i + 1, ok(t, 0.9))
                self.assertEqual(sp.text, compose(sp.tokens)["text"])
            self.assertEqual(sp.tokens, tokens)
            self.assertEqual(sp.text, text)
            sp.key("backspace")
            self.assertEqual(sp.text, compose(sp.tokens)["text"])
            sp.key("clear")
            self.assertEqual(sp.text, compose([])["text"])

    def test_c7_word_gap_waits_for_pending_result(self):
        sp = Level1Speller(0.5)
        sp.segment_emitted(1)
        sp.on_result(1, ok("b", 0.9))
        sp.segment_emitted(2)          # k = 2, result not there yet
        sp.word_gap(3)                 # gap emitted after k
        self.assertEqual(sp.tokens, ["b"])
        sp.on_result(2, ok("a", 0.9))
        self.assertEqual(sp.tokens, ["b", "a", " "])
        # a gap with nothing pending applies at once; a second gap adds nothing
        sp.word_gap(4)
        self.assertEqual(sp.tokens, ["b", "a", " "])

    def test_c7_rejected_pending_then_gap(self):
        sp = Level1Speller(0.5)
        sp.segment_emitted(1)
        sp.word_gap(2)
        sp.on_result(1, ok("b", 0.1))  # rejected: the gap has nothing to separate
        self.assertEqual(sp.tokens, [])


class TestTimingAcT(unittest.TestCase):
    def test_summary_matches_numpy(self):
        values = [3.0, 1.5, 9.25, 4.0, 4.0, 12.0, 0.5]
        s = summarize(values)
        self.assertEqual(s["n"], len(values))
        self.assertEqual(s["mean"], float(np.mean(values)))
        self.assertEqual(s["p50"], float(np.percentile(values, 50)))
        self.assertEqual(s["p95"], float(np.percentile(values, 95)))

    def test_empty_is_null(self):
        self.assertEqual(summarize([]), {"n": 0, "mean": None, "p50": None, "p95": None})
        st = StageTimes(("a", "b"), 3)
        self.assertEqual(st.stats()["a"]["n"], 0)
        self.assertIsNone(st.rolling_p50("a"))

    def test_rate(self):
        self.assertEqual(rate_from_timestamps([]), 0.0)
        self.assertEqual(rate_from_timestamps([1.0]), 0.0)
        self.assertEqual(rate_from_timestamps([1.0, 1.0]), 0.0)
        self.assertEqual(rate_from_timestamps([0.0, 0.5, 1.0]), 2.0)

    def test_stage_times_rolling(self):
        st = StageTimes(("a",), 2)
        for v in (10.0, 1.0, 3.0):
            st.add("a", v)
        self.assertEqual(st.values("a"), [10.0, 1.0, 3.0])
        self.assertEqual(st.rolling_p50("a"), float(np.percentile([1.0, 3.0], 50)))
        self.assertEqual(st.stats()["a"]["n"], 3)
        with self.assertRaises(KeyError):
            st.add("zzz", 1.0)



# ----------------------------------------------------------------------------------------------------------------------
# Plan 15 lần sửa 7 T1: optional decoder keys cls_conf_tone / cls_stable_ms_tone (absent = the decoder falls back to
# cls_conf / cls_stable_ms; configs/level1_realtime.json does not get them and still loads exactly as before).
# ----------------------------------------------------------------------------------------------------------------------
T1_KEYS = {"cls_conf_tone": 0.78, "cls_stable_ms_tone": 200.0}


class TestOptionalToneKeysT1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vslt_p15_t1_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _with(self, **values):
        raw = _real_raw()
        for k, v in values.items():
            raw[k] = {"value": v, "source": "design", "reason": "test value (plan 15 lần sửa 7 T1)"}
        return raw

    def test_t1_optional_spec(self):
        from src.inference.level1_core import OPTIONAL_CONFIG_SPEC
        for k in T1_KEYS:
            self.assertIn(k, OPTIONAL_CONFIG_SPEC)
            self.assertNotIn(k, CONFIG_SPEC)                           # never a required key
        self.assertFalse(set(OPTIONAL_CONFIG_SPEC) & set(CONFIG_SPEC))

    def test_t1_default_config_unchanged(self):
        cfg = load_level1_config(CONFIG_PATH)
        self.assertEqual(set(cfg["values"]), set(CONFIG_SPEC))
        for k in T1_KEYS:
            self.assertNotIn(k, cfg["raw"])

    def test_t1_keys_accepted_and_returned(self):
        values = validate_level1_config(self._with(**T1_KEYS))
        for k, v in T1_KEYS.items():
            self.assertEqual(values[k], v)
        self.assertEqual(list(values)[:len(CONFIG_SPEC)], list(CONFIG_SPEC))
        values = validate_level1_config(self._with(cls_conf_tone=1.0))
        self.assertEqual(values["cls_conf_tone"], 1.0)
        self.assertNotIn("cls_stable_ms_tone", values)
        p = os.path.join(self.tmp, "t1.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self._with(**T1_KEYS), f, ensure_ascii=False)
        self.assertEqual(load_level1_config(p)["values"]["cls_stable_ms_tone"], 200.0)

    def test_t1_bad_values_rejected(self):
        for key, bad in (("cls_conf_tone", 0), ("cls_conf_tone", 1.01), ("cls_conf_tone", -0.2), ("cls_conf_tone", True),
                         ("cls_conf_tone", "0.78"), ("cls_conf_tone", float("nan")), ("cls_stable_ms_tone", 0),
                         ("cls_stable_ms_tone", -200), ("cls_stable_ms_tone", False),
                         ("cls_stable_ms_tone", float("inf"))):
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(ValueError):
                    validate_level1_config(self._with(**{key: bad}))
        for field in ("source", "reason"):
            raw = self._with(**T1_KEYS)
            del raw["cls_conf_tone"][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_level1_config(raw)
        raw = self._with(**T1_KEYS)
        raw["cls_stable_ms_tone"] = 200.0                                # a bare number, not {value, source, reason}
        with self.assertRaises(ValueError):
            validate_level1_config(raw)
        raw = self._with(cls_conf_tones=0.78)                            # misspelt key: still an unknown key
        with self.assertRaises(ValueError):
            validate_level1_config(raw)



class TestOptionalDropoutKeyT2(unittest.TestCase):
    """Plan 15 lần sửa 7 T2: optional key dropout_tolerance_ms (absent = no debounce, the decoder of D4)."""

    def _with(self, value):
        raw = _real_raw()
        raw["dropout_tolerance_ms"] = {"value": value, "source": "design", "reason": "test value (plan 15 lần sửa 7 T2)"}
        return raw

    def test_t2_optional_key(self):
        from src.inference.level1_core import OPTIONAL_CONFIG_SPEC
        self.assertIn("dropout_tolerance_ms", OPTIONAL_CONFIG_SPEC)
        self.assertNotIn("dropout_tolerance_ms", CONFIG_SPEC)
        self.assertNotIn("dropout_tolerance_ms", _real_raw())
        self.assertEqual(validate_level1_config(self._with(60))["dropout_tolerance_ms"], 60)
        self.assertNotIn("dropout_tolerance_ms", validate_level1_config(_real_raw()))

    def test_t2_bad_values_rejected(self):
        for bad in (0, -60, True, "60", float("nan"), None, [60]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_level1_config(self._with(bad))


# ------------------------------------------------------------------ plan 15 lần sửa 8 M2
class TestEnhanceLowLightM2(unittest.TestCase):
    """AC-8d at the function level (plan 15 lần sửa 8 §2 M2): enhance_low_light(frame_bgr, threshold, clip_limit) ->
    (frame, enhanced). Mean of the grayscale frame < threshold -> CLAHE (clipLimit = clip_limit, tileGridSize 8x8) on
    the L channel of LAB, back to BGR, a new array, enhanced True; mean >= threshold -> the very same frame object,
    enhanced False. The input frame is never modified. The frames are constant or ramp arrays built here to drive the
    function (no image data)."""

    @staticmethod
    def _flat(value, h=48, w=64):
        import numpy as np
        return np.full((h, w, 3), value, dtype=np.uint8)

    @staticmethod
    def _dark_ramp(lo=20, hi=40, h=480, w=640):
        import numpy as np
        x = np.tile(np.linspace(lo, hi, w).astype(np.uint8), (h, 1))
        return np.ascontiguousarray(np.dstack([x, x, x]))

    @staticmethod
    def _reference(frame, clip_limit):
        """The §2 M2 steps written out here: BGR -> LAB, CLAHE on L, merge, LAB -> BGR."""
        import cv2
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_ch = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8)).apply(l_ch)
        return cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)

    @staticmethod
    def _gray(frame):
        import cv2
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype("float64")

    def test_m2_dark_flat_frame_enhanced(self):
        import numpy as np
        from src.inference.level1_core import enhance_low_light
        frame = self._flat(30)
        before = frame.copy()
        out, enhanced = enhance_low_light(frame)
        self.assertIs(enhanced, True)
        self.assertIsNot(out, frame)
        self.assertEqual((out.shape, out.dtype), (frame.shape, frame.dtype))
        self.assertTrue(np.array_equal(frame, before))             # input not modified
        self.assertFalse(np.array_equal(out, frame))
        self.assertGreater(self._gray(out).mean(), self._gray(frame).mean())
        self.assertTrue(np.array_equal(out, self._reference(before, 2.0)))

    def test_m2_dark_ramp_contrast_raised(self):
        import numpy as np
        from src.inference.level1_core import enhance_low_light
        frame = self._dark_ramp()
        out, enhanced = enhance_low_light(frame)
        self.assertIs(enhanced, True)
        self.assertTrue(np.array_equal(out, self._reference(frame, 2.0)))
        self.assertGreater(self._gray(out).std(), self._gray(frame).std())
        out4, _ = enhance_low_light(frame, clip_limit=4.0)        # clip_limit is passed to CLAHE
        self.assertTrue(np.array_equal(out4, self._reference(frame, 4.0)))
        self.assertFalse(np.array_equal(out4, out))

    def test_m2_bright_frame_unchanged(self):
        import numpy as np
        from src.inference.level1_core import enhance_low_light
        frame = self._flat(150)
        before = frame.copy()
        out, enhanced = enhance_low_light(frame)
        self.assertIs(enhanced, False)
        self.assertIs(out, frame)                                  # the very object, no copy
        self.assertTrue(np.array_equal(frame, before))

    def test_m2_threshold_boundary_and_parameter(self):
        from src.inference.level1_core import enhance_low_light
        self.assertIs(enhance_low_light(self._flat(79))[1], True)    # mean 79 < 80
        self.assertIs(enhance_low_light(self._flat(80))[1], False)   # mean 80 >= 80
        self.assertIs(enhance_low_light(self._flat(100), threshold=120.0)[1], True)
        self.assertIs(enhance_low_light(self._flat(30), threshold=20.0)[1], False)

    def test_m2_rejects_non_bgr_uint8(self):
        import numpy as np
        from src.inference.level1_core import enhance_low_light
        with self.assertRaises(ValueError):
            enhance_low_light(np.full((48, 64), 30, dtype=np.uint8))
        with self.assertRaises(ValueError):
            enhance_low_light(np.full((48, 64, 3), 30.0, dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
