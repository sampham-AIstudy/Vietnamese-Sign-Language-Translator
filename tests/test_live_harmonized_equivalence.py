"""
Plan 04 AC4 + AC5: the live harmonized_v1 path reproduces the TRAINING input on real QIPEDC TRAIN videos.

AC4 (TestTransformEquivalence), per clip of scripts/live_clip_sample.select_train_clips(8, seed 0):
  training path = scripts/extract_keypoints_batch._extract_one (process_height 360) -> HarmonizedDataset[0]
  live path     = cv2.VideoCapture -> lossless PNG -> backend.main._decode_frame (header checks) ->
                  HarmonizedLiveSession.process(frame, i / CAP_PROP_FPS) -> finalize_clip()
  (1) raw keypoints / visibility identical, (2) MediaPipe got 360-px-high images on both paths,
  (3) joint / temporal masks identical, (4) max |d sequence| <= 1e-5, (5) same top-5 order, |d conf| <= 1e-4.
AC5 (TestWebSocketEndToEnd), first 2 clips: the same frames through /ws/live-stream (VSL_MODEL_TYPE=stgcn_h360,
  lock-step, PNG data URLs) and through an in-process HarmonizedLiveSession give the same events and top-5.

Needs the local (gitignored / user) data: H-keepz-360 checkpoint, data/Dataset/Videos, unified train split.
Only TRAIN clips are used and no accuracy is measured. No landmark / frame is written outside a temp dir.
"""
import base64
import csv
import importlib
import json
import math
import os
import sys
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import live_clip_sample  # noqa: E402
from src.data.landmark_extractor import CleanHolisticExtractor  # noqa: E402

AVAILABLE = live_clip_sample.available()
REASON = "needs the H-keepz-360 checkpoint, data/Dataset/Videos and data/splits/unified/train.csv"


class MediaPipeInputRecorder:
    """Wraps the REAL holistic.process of every CleanHolisticExtractor graph to record the image shapes
    (the real function is still called)."""

    def __init__(self):
        self.shapes = []
        self._orig = CleanHolisticExtractor._get_holistic
        recorder = self

        def wrapped(extractor):
            graph = recorder._orig(extractor)
            if not getattr(graph, "_vslt_recorded", False):
                real = graph.process

                def process(image):
                    recorder.shapes.append(tuple(image.shape))
                    return real(image)
                graph.process = process
                graph._vslt_recorded = True
            return graph
        self.patch = mock.patch.object(CleanHolisticExtractor, "_get_holistic", wrapped)

    def __enter__(self):
        self.shapes = []
        self.patch.start()
        return self

    def __exit__(self, *exc):
        self.patch.stop()


def read_frames(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    return frames, fps


def png(frame):
    ok, buf = cv2.imencode(".png", frame)
    assert ok
    return buf.tobytes()


def rest_padding(n_frames, fps, rest_hold_s):
    """TEST PADDING (not data): the last frame is sent again ceil((rest_hold_s + 0.2) * fps) times so that the
    segmenter sees the hands at rest after the clip ends (plan AC5)."""
    return int(math.ceil((rest_hold_s + 0.2) * fps))


@unittest.skipUnless(AVAILABLE, REASON)
class TestTransformEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from extract_keypoints_batch import _extract_one
        from backend.main import _decode_frame
        from src.data.harmonized import HarmonizedDataset
        from src.inference.harmonized_live import HarmonizedLiveSession
        from src.inference.predictor import VSLPredictor

        cls.ckpt = torch.load(live_clip_sample.H360_CKPT, map_location="cpu", weights_only=False)
        cls.pre = cls.ckpt["preprocessing"]
        cls.predictor = VSLPredictor(model_type="stgcn", stgcn_ckpt=live_clip_sample.H360_CKPT, device="cpu")
        cls.rows = live_clip_sample.select_train_clips(8, 0)
        print("\n[AC4] sample video_id:", [r["video_id"] for r in cls.rows])
        cls.tmp = tempfile.TemporaryDirectory()
        cls.results = []
        for r in cls.rows:
            stem = os.path.splitext(r["file_name"])[0]
            npz = os.path.join(cls.tmp.name, f"{stem}.npz")
            with MediaPipeInputRecorder() as rec_train:
                path, status, _ = _extract_one((r["video_path"], npz, {"process_height": 360, "source": "qipedc",
                                                                       "file_name": r["file_name"],
                                                                       "label": r["gloss_raw"]}))
            assert status == "ok", status
            csv_path = os.path.join(cls.tmp.name, f"{stem}.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["npz_path", "width", "height", "gloss_normalized", "video_id"])
                w.writeheader()
                w.writerow({"npz_path": npz, "width": r["width"], "height": r["height"],
                            "gloss_normalized": r["gloss_normalized"], "video_id": r["video_id"]})
            item = HarmonizedDataset(csv_path, cls.ckpt["label_map"], cfg=cls.pre, augment=False)[0]
            d = np.load(npz)
            train = {"keypoints": d["keypoints"], "visibility_mask": d["visibility_mask"],
                     "sequence": item["sequence"].numpy(), "joint_mask": item["joint_mask"].numpy(),
                     "temporal_mask": item["temporal_mask"].numpy()}

            frames, fps = read_frames(r["video_path"])
            with MediaPipeInputRecorder() as rec_live:
                session = HarmonizedLiveSession(cls.predictor, cls.pre, record_clip=True)
                try:
                    for i, frame in enumerate(frames):
                        decoded = _decode_frame(png(frame), min_height=session.process_height)
                        session.process(decoded, i / fps)
                    live = session.finalize_clip()
                finally:
                    session.close()
            cls.results.append({"row": r, "train": train, "live": live, "n_frames": len(frames),
                                "frame_wh": (frames[0].shape[1], frames[0].shape[0]),
                                "train_shapes": rec_train.shapes, "live_shapes": rec_live.shapes,
                                "pred_train": cls.predictor.predict(train["sequence"], train["joint_mask"],
                                                                    train["temporal_mask"], top_k=5),
                                "pred_live": cls.predictor.predict(live["sequence"], live["joint_mask"],
                                                                   live["temporal_mask"], top_k=5)})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_0_sample(self):
        self.assertEqual(len(self.results), 8)
        for res in self.results:
            self.assertEqual(res["row"]["split"], "train")
            self.assertEqual(res["frame_wh"], (int(res["row"]["width"]), int(res["row"]["height"])))

    def test_1_raw_landmarks_identical(self):
        for res in self.results:
            with self.subTest(video_id=res["row"]["video_id"]):
                self.assertTrue(np.array_equal(res["train"]["keypoints"], res["live"]["keypoints"], equal_nan=True))
                self.assertTrue(np.array_equal(res["train"]["visibility_mask"], res["live"]["visibility_mask"]))

    def test_2_mediapipe_input_height_360(self):
        for res in self.results:
            with self.subTest(video_id=res["row"]["video_id"]):
                for shapes in (res["train_shapes"], res["live_shapes"]):
                    self.assertEqual(len(shapes), res["n_frames"])
                    self.assertEqual({s[0] for s in shapes}, {360})
                    self.assertEqual({s[1] for s in shapes}, {640})

    def test_3_masks_identical(self):
        for res in self.results:
            with self.subTest(video_id=res["row"]["video_id"]):
                self.assertTrue(np.array_equal(res["train"]["joint_mask"], res["live"]["joint_mask"]))
                self.assertTrue(np.array_equal(res["train"]["temporal_mask"], res["live"]["temporal_mask"]))

    def test_4_sequence_close(self):
        worst = []
        for res in self.results:
            d = float(np.abs(res["train"]["sequence"] - res["live"]["sequence"]).max())
            worst.append((res["row"]["video_id"], d))
            with self.subTest(video_id=res["row"]["video_id"]):
                self.assertLessEqual(d, 1e-5)
        print("\n[AC4] max|d sequence| per clip:", worst)

    def test_5_same_top5(self):
        worst = 0.0
        for res in self.results:
            a, b = res["pred_train"]["top5"], res["pred_live"]["top5"]
            with self.subTest(video_id=res["row"]["video_id"]):
                self.assertEqual([x["gloss"] for x in a], [x["gloss"] for x in b])
                for x, y in zip(a, b):
                    worst = max(worst, abs(x["confidence"] - y["confidence"]))
                    self.assertLessEqual(abs(x["confidence"] - y["confidence"]), 1e-4)
        print(f"\n[AC4] max|d confidence| over 8 clips x top-5: {worst}")


@unittest.skipUnless(AVAILABLE, REASON)
class TestWebSocketEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import backend.main as api
        cls.api = api
        cls._env = {k: os.environ.get(k) for k in ("VSL_MODEL_TYPE", "VSL_STGCN_CKPT")}
        os.environ["VSL_MODEL_TYPE"] = "stgcn_h360"
        os.environ.pop("VSL_STGCN_CKPT", None)
        importlib.reload(api)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        importlib.reload(cls.api)       # back to the default model constants for the other test modules

    def _stream(self, row):
        frames, fps = read_frames(row["video_path"])
        rest_hold = self.api.SEGMENTER_DEFAULT["rest_hold_s"]
        seq = frames + [frames[-1]] * rest_padding(len(frames), fps, rest_hold)
        return [(png(f), i * 1000.0 / fps) for i, f in enumerate(seq)], len(frames)

    def test_ws_matches_in_process_session(self):
        from fastapi.testclient import TestClient
        from src.inference.harmonized_live import HarmonizedLiveSession
        api = self.api
        self.assertEqual(api.MODEL_TYPE, "stgcn_h360")
        self.assertFalse(api.IS_DEFAULT_MODEL)
        client = TestClient(api.app)
        for row in live_clip_sample.select_train_clips(8, 0)[:2]:
            stream, n_clip = self._stream(row)
            ws_events, frame_results = [], 0
            with client.websocket_connect("/ws/live-stream") as ws:
                info = ws.receive_json()
                self.assertEqual((info["type"], info["pipeline"]), ("session_info", "harmonized_v1"))
                self.assertEqual(info["model"]["checkpoint_sha256"], api.STGCN_VARIANTS["stgcn_h360"]["sha256"])
                for data, ts in stream:
                    ws.send_text(json.dumps({"image": "data:image/png;base64," + base64.b64encode(data).decode(),
                                             "timestamp": ts}))
                    while True:
                        m = ws.receive_json()
                        self.assertNotEqual(m["type"], "error", m)
                        if m["type"] == "frame_result":
                            frame_results += 1
                            self.assertIsNone(m["prediction"])
                            self.assertEqual(m["dropped_frames"], 0)
                            break
                        ws_events.append(m)
            self.assertEqual(frame_results, len(stream))

            predictor = api.GLOBAL_PREDICTOR
            session = HarmonizedLiveSession(predictor, predictor.preprocessing)
            local_events = []
            try:
                t0 = stream[0][1]
                for k, (data, ts) in enumerate(stream, start=1):
                    frame = api._decode_frame(data, min_height=session.process_height)
                    out = session.process(frame, (ts - t0) / 1000.0, seq=k)
                    if out["event"] is not None:
                        local_events.append(out["event"])
            finally:
                session.close()

            summary = [(e["type"], e.get("reason"), e.get("gloss")) for e in ws_events]
            print(f"\n[AC5] {row['video_id']}: {n_clip} frames + {len(stream) - n_clip} padding frames (test "
                  f"padding: last frame repeated) -> WS events {summary}")
            with self.subTest(video_id=row["video_id"]):
                self.assertEqual([(e["type"], e.get("reason")) for e in ws_events],
                                 [(e["type"], e.get("reason")) for e in local_events])
                for w, l in zip(ws_events, local_events):
                    self.assertEqual(w["segment_id"], l["segment_id"])
                    if w["type"] == "sign_result":
                        self.assertEqual(set(w), {"type", "segment_id", "frame_seq", "prediction", "gloss",
                                                  "confidence", "top5", "end_reason", "segment", "model", "metrics"})
                        self.assertEqual([x["gloss"] for x in w["top5"]], [x["gloss"] for x in l["top5"]])
                        for x, y in zip(w["top5"], l["top5"]):
                            self.assertLessEqual(abs(x["confidence"] - y["confidence"]), 1e-4)
                        self.assertEqual(len(w["top5"]), min(5, predictor.num_classes))
                        self.assertEqual(w["model"], {"model_type": "stgcn_h360", "checkpoint": "stgcn_unified_best.pt",
                                                      "is_default": False, "pipeline": "harmonized_v1"})
                        self.assertEqual(w["segment"]["dropped_frames"], 0)
                        self.assertIsNotNone(w["metrics"]["trigger_client_timestamp"])
                    else:
                        self.assertEqual(set(w), {"type", "segment_id", "frame_seq", "reason", "segment"})


class TestSegmentCheckJson(unittest.TestCase):
    """Plan 04 AC6: the committed report of scripts/live_segment_check.py (latest reports/live_word_*/)."""

    @classmethod
    def setUpClass(cls):
        import glob
        found = sorted(glob.glob(os.path.join(PROJECT_ROOT, "reports", "live_word_*", "segment_check.json")))
        cls.path = found[-1] if found else None

    def test_exists_and_complete(self):
        self.assertIsNotNone(self.path, "reports/live_word_*/segment_check.json missing")
        with open(self.path, encoding="utf-8") as f:
            report = json.load(f)
        gen = report["generated_by"]
        self.assertIs(gen["code_dirty"], False)
        self.assertEqual(gen["checkpoint_sha256"], "648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e")
        for key in ("command", "git_commit", "mediapipe", "cv2", "numpy", "segmenter_default"):
            self.assertIn(key, gen)
        import subprocess
        anc = subprocess.run(["git", "merge-base", "--is-ancestor", gen["git_commit"], "HEAD"], cwd=PROJECT_ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(anc.returncode, 0, f"{gen['git_commit']} is not an ancestor of HEAD")
        self.assertEqual(len(report["clips"]), 8)
        self.assertEqual(report["n_clips"], 8)
        if AVAILABLE:
            self.assertEqual([c["video_id"] for c in report["clips"]],
                             [r["video_id"] for r in live_clip_sample.select_train_clips(8, 0)])
        for clip in report["clips"]:
            with self.subTest(video_id=clip["video_id"]):
                self.assertGreaterEqual(len(clip["events"]), 1)
                self.assertIsInstance(clip["contains_offline_span"], bool)
        self.assertEqual(report["n_contains_offline_span"], sum(c["contains_offline_span"] for c in report["clips"]))
        text = json.dumps(report)
        for banned in ("keypoints", "landmarks", "coords", "visibility"):
            self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
