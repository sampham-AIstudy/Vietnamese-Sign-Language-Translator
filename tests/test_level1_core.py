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


if __name__ == "__main__":
    unittest.main()
