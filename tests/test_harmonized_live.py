"""
Plan 04 AC2: src/inference/harmonized_live.py (live harmonized_v1 path).

Fake extractor / predictor / MediaPipe graph are test doubles; landmark frames are fixtures generated in the
test (tests/test_sign_segmenter.py), not data. AC2-a also reads the real H-keepz-360 checkpoint when present.
"""
import importlib.util
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import mediapipe  # noqa: E402

import src.inference.harmonized_live as hl  # noqa: E402
from src.data.harmonized import HARMONIZED_DEFAULT  # noqa: E402
from src.data.landmark_extractor import CleanHolisticExtractor  # noqa: E402
from src.inference.sign_segmenter import Emit  # noqa: E402
from tests.test_sign_segmenter import REST_Y, build, sign_profile  # noqa: E402

H360_CKPT = os.path.join(PROJECT_ROOT, "reports", "step4_2026-09-26", "runs", "run_keepz_360", "stgcn_unified_best.pt")
PRE = {**HARMONIZED_DEFAULT, "process_height": 360, "trim": True, "hand_z": True,
       "extractor": "CleanHolisticExtractor", "mediapipe_version": mediapipe.__version__}


class FakeExtractor:
    """Returns the fixture frames in order; records the image shapes it was given."""

    def __init__(self, kps, vis, process_height=360):
        self.kps, self.vis, self.i, self.shapes, self.process_height = kps, vis, 0, [], process_height
        self.closed = False

    def _get_holistic(self):
        return self

    def extract_frame(self, frame_rgb):
        self.shapes.append(frame_rgb.shape)
        k, v = self.kps[self.i], self.vis[self.i]
        self.i += 1
        return k.copy(), v.copy()

    def close(self):
        self.closed = True


class FakePredictor:
    def __init__(self, n=10):
        self.class_names = [f"g{i}" for i in range(n)]
        self.num_classes, self.calls = n, []
        self.preprocessing, self.model_type, self.device = dict(PRE), "stgcn", "cpu"

    def predict(self, sequence, joint_mask=None, temporal_mask=None, top_k=5):
        self.calls.append((sequence, joint_mask, temporal_mask, top_k))
        conf = [0.5, 0.2, 0.1, 0.05, 0.04][:top_k]
        top = [{"gloss": self.class_names[i], "confidence": c} for i, c in enumerate(conf)]
        return {"gloss": top[0]["gloss"], "confidence": top[0]["confidence"], "top5": top, "latency_ms": 1.0}


def sign_stream(fps=30.0, dur=3.5):
    t = np.arange(int(round(dur * fps))) / fps
    k, v = build(t, lambda x: sign_profile(x, 1.0, 2.5))
    return t, k, v


def run_session(session, t, w=640, h=480):
    frame = np.zeros((h, w, 3), np.uint8)
    return [session.process(frame, float(x)) for x in t]


class TestLivePipelineFor(unittest.TestCase):
    def test_a_legacy_cases(self):
        spec = importlib.util.spec_from_file_location("train_unified_for_test",
                                                      os.path.join(PROJECT_ROOT, "scripts", "train_unified.py"))
        cwd = os.getcwd()
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        finally:
            os.chdir(cwd)
        for pre in (None, {}, mod.PREPROCESSING):
            with self.subTest(pre=pre):
                self.assertEqual(hl.live_pipeline_for(pre), "legacy")

    @unittest.skipUnless(os.path.exists(H360_CKPT), "H-keepz-360 checkpoint not on disk")
    def test_a_real_checkpoint_is_harmonized(self):
        import torch
        pre = torch.load(H360_CKPT, map_location="cpu", weights_only=False)["preprocessing"]
        self.assertEqual(hl.live_pipeline_for(pre), "harmonized_v1")

    def test_a_invalid_harmonized_raise(self):
        self.assertEqual(hl.live_pipeline_for(PRE), "harmonized_v1")
        bad = [{**PRE, "features": "harmonized_v2"}, {**PRE, "mediapipe_version": "0.10.9"}, {**PRE, "extractor": "X"},
               {k: v for k, v in PRE.items() if k != "rest_y"}, {**PRE, "process_height": 0},
               {**PRE, "process_height": True}, {**PRE, "target_len": 1},
               {k: v for k, v in PRE.items() if k != "process_height"}]
        for pre in bad:
            with self.subTest(pre={k: pre.get(k) for k in ("features", "mediapipe_version", "extractor",
                                                             "process_height", "target_len")}), \
                    self.assertRaises(ValueError):
                hl.live_pipeline_for(pre)


class FakeGraph:
    def __init__(self):
        self.images = []

    def process(self, img):
        self.images.append(img.copy())
        return SimpleNamespace(pose_landmarks=None, left_hand_landmarks=None, right_hand_landmarks=None)


class TestSession(unittest.TestCase):
    def test_b_real_extractor_resizes_to_360_rgb(self):
        for (w, h), expected in (((640, 480), (360, 480, 3)), ((1280, 720), (360, 640, 3))):
            ext = CleanHolisticExtractor(process_height=360)
            graph = FakeGraph()
            with mock.patch.object(ext, "_get_holistic", return_value=graph):
                s = hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=ext)
                frame = np.zeros((h, w, 3), np.uint8)
                frame[:] = (255, 0, 0)                   # pure blue in BGR
                s.process(frame, 0.0)
            with self.subTest(size=(w, h)):
                self.assertEqual(graph.images[0].shape, expected)
                self.assertEqual(tuple(int(c) for c in graph.images[0][10, 10]), (0, 0, 255))

    def test_c_harmonize_gets_checkpoint_cfg_aspect_and_time(self):
        t, k, v = sign_stream()
        pred = FakePredictor()
        s = hl.HarmonizedLiveSession(pred, PRE, extractor=FakeExtractor(k, v))
        calls = []
        real = hl.harmonize

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return real(*args, **kwargs)

        with mock.patch.object(hl, "harmonize", side_effect=spy):
            outs = run_session(s, t)
        events = [o["event"] for o in outs if o["event"]]
        self.assertEqual([e["type"] for e in events], ["sign_result"])
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertTrue(kwargs["cfg"] is PRE or kwargs["cfg"] == PRE)
        self.assertEqual(kwargs["cfg"], PRE)
        self.assertEqual(args[2], 640 / 480)                        # aspect of the original frame
        ts = kwargs["timestamps_s"]
        self.assertEqual(ts[0], 0.0)
        self.assertTrue(np.all(np.diff(ts) > 0))
        self.assertIsNone(kwargs.get("rng"))
        self.assertEqual(len(args), 4)                               # (kps, vis, aspect, fps): rng never passed
        self.assertEqual(len(pred.calls), 1)
        top = events[0]["top5"]
        self.assertEqual([x["confidence"] for x in top], sorted([x["confidence"] for x in top], reverse=True))

    def test_d_no_hand_segment_discarded_without_predict(self):
        t = np.arange(60) / 30.0
        for kw in ({}, {"right_visible": False, "left_visible": False}):
            k, v = build(t, lambda _: REST_Y, **kw)
            pred = FakePredictor()
            s = hl.HarmonizedLiveSession(pred, PRE, extractor=FakeExtractor(k, v))
            forced = Emit(segment_id=1, kps=k[:40], vis=v[:40], t=t[:40], frame_wh=(640, 480),
                          active_start_s=float(t[5]), active_end_s=float(t[20]))
            outs = run_session(s, t[:39])
            with mock.patch.object(s.segmenter, "push", return_value=forced):
                last = s.process(np.zeros((480, 640, 3), np.uint8), float(t[39]))
            with self.subTest(**kw):
                self.assertTrue(all(o["event"] is None for o in outs))
                self.assertEqual(last["event"]["type"], "sign_discarded")
                self.assertEqual(last["event"]["reason"], "no_hand_frames")
                self.assertEqual(pred.calls, [])

    def test_e_overlay_landmarks(self):
        t, k, v = sign_stream()
        full = hl.overlay_landmarks(k[40], v[40])
        self.assertEqual(len(full["pose"]), 25)
        self.assertEqual(len(full["left_hand"]), 21)
        self.assertEqual(len(full["right_hand"]), 21)
        for pairs in full.values():
            for p in pairs:
                self.assertEqual(len(p), 2)
                self.assertEqual(p, [round(p[0], 4), round(p[1], 4)])
        kk, vv = k[40].copy(), v[40].copy()
        kk[25:46], vv[25:46] = np.nan, 0                              # left hand missing
        kk[:25] = np.nan                                              # no pose
        miss = hl.overlay_landmarks(kk, vv)
        self.assertEqual((miss["pose"], miss["left_hand"]), ([], []))
        self.assertEqual(len(miss["right_hand"]), 21)
        text = json.dumps(miss, allow_nan=False)                      # raises on NaN / Infinity
        self.assertNotIn("NaN", text)

    def test_f_timings_come_from_perf_counter(self):
        t, k, v = sign_stream()
        s = hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=FakeExtractor(k, v))
        # idle frame: perf_counter called 3 times (before/after extract, after segmenter)
        with mock.patch.object(hl, "perf_counter", side_effect=[1.0, 1.25, 1.5]):
            out = s.process(np.zeros((480, 640, 3), np.uint8), float(t[0]))
        self.assertEqual((out["extract_ms"], out["segment_ms"]), (250.0, 250.0))
        self.assertIsNone(out["harmonize_ms"])
        outs = run_session(s, t[1:])
        i_ev = next(i for i, o in enumerate(outs) if o["event"]) + 1
        s2 = hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=FakeExtractor(k, v))
        run_session(s2, t[:i_ev])
        seq = [2.0, 2.5, 2.625, 3.0, 3.125, 3.5]      # extract, segment, then harmonize / infer (exact binary values)
        with mock.patch.object(hl, "perf_counter", side_effect=seq):
            out = s2.process(np.zeros((480, 640, 3), np.uint8), float(t[i_ev]))
        self.assertEqual(out["event"]["type"], "sign_result")
        self.assertEqual(out["extract_ms"], 500.0)
        self.assertEqual(out["segment_ms"], 125.0)
        self.assertEqual(out["harmonize_ms"], 125.0)
        self.assertEqual(out["infer_ms"], 375.0)
        self.assertEqual(out["finalize_ms"], 500.0)
        self.assertEqual(out["event"]["metrics"]["infer_ms"], 375.0)

    def test_finalize_clip_uses_same_buffer_path(self):
        t, k, v = sign_stream()
        s = hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=FakeExtractor(k, v), record_clip=True)
        run_session(s, t)
        with mock.patch.object(s, "_harmonize_buffer", wraps=s._harmonize_buffer) as spy:
            out = s.finalize_clip()
        spy.assert_called_once()
        self.assertEqual(out["sequence"].shape, (PRE["target_len"], 67, 3))
        self.assertTrue(np.array_equal(out["keypoints"], k, equal_nan=True))
        with self.assertRaises(RuntimeError):
            hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=FakeExtractor(k, v)).finalize_clip()

    def test_bad_time_rejected_before_extraction(self):
        t, k, v = sign_stream()
        ext = FakeExtractor(k, v)
        s = hl.HarmonizedLiveSession(FakePredictor(), PRE, extractor=ext)
        s.process(np.zeros((480, 640, 3), np.uint8), 1.0)
        with self.assertRaises(ValueError):
            s.process(np.zeros((480, 640, 3), np.uint8), 1.0)
        self.assertEqual(ext.i, 1)


if __name__ == "__main__":
    unittest.main()
