"""
Plan 06 AC5: Level 1 train <-> live equivalence on real clips, same machine.

Offline = scripts/extract_hands_batch.py::_extract_one (imported, unchanged) run into a temporary directory.
Live = the same video read with cv2.VideoCapture -> PNG (lossless) -> WS /ws/hand-landmarks text data URL,
timestamp i * 1000 / fps, one reset at the start of the clip.
Sample: scripts/hand_live_check.select_clips(n_hauuto=8, seed=0) (8 hauuto clips with a local video, rng(0)) + the
first 2 qipedc clips with a local video. hauuto clips are training data of the deployed Level 1 model: this checks
identical inputs, not accuracy.

(a) landmarks must be BIT-identical (plan 06 §7-1: otherwise stop and report, no tolerance).
"""
import os
import sys
import tempfile
import shutil
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hand_live_check as H  # noqa: E402

N_HAUUTO, SEED = 8, 0
_MISSING = [p for p in (H.MANIFEST, H.HAUUTO_VIDEO_DIR, H.QIPEDC_VIDEO_DIR, H.DEPLOYED_CKPT, H.PROVENANCE_JSON)
            if not os.path.exists(p)]
SKIP_REASON = "missing (gitignored data / checkpoint; clean clone): " + ", ".join(
    os.path.relpath(p, PROJECT_ROOT) for p in _MISSING)


@unittest.skipUnless(not _MISSING, SKIP_REASON)
class TestHandLiveEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from fastapi.testclient import TestClient
        import backend.main as api
        from train_alphabet_real import build

        cls.api = api
        cls.rows_all = H.read_manifest()
        cls.n_candidates = len(H.hauuto_candidates(cls.rows_all))
        cls.rows = H.select_clips(cls.rows_all, N_HAUUTO, SEED)
        cls.ckpt_sha = H.sha256_of(H.DEPLOYED_CKPT)
        cls.ckpt = torch.load(H.DEPLOYED_CKPT, map_location="cpu", weights_only=False)
        cls.model = build(cls.ckpt["model_type"], len(cls.ckpt["classes"]))
        cls.model.load_state_dict(cls.ckpt["state_dict"])
        cls.model.eval()

        cls._saved = (api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta)
        api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = H.DEPLOYED_CKPT, None, None
        cls.client = TestClient(api.app)  # no `with`: lifespan (Level 2 predictor) is not started

        cls.tmp = tempfile.mkdtemp(prefix="vslt_ac5_")
        extract = H.load_extract_module()
        cls.results = []
        for row in cls.rows:
            frames, fps = H.read_video(H.video_path_for(row))
            off = H.offline_extract(row, cls.tmp, extract)
            live = H.live_hand_frames(cls.client, frames, fps, "png")
            cls.results.append({"row": row, "fps": fps, "n_video_frames": len(frames), "off": off, "live": live})

    @classmethod
    def tearDownClass(cls):
        cls.api.ALPHABET_CKPT = cls._saved[0]
        cls.api._alphabet_model, cls.api._alphabet_meta = None, None
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_0_sample(self):
        self.assertGreaterEqual(self.n_candidates, N_HAUUTO)
        sources = [r["source"] for r in self.rows]
        self.assertEqual(sources, ["hauuto"] * N_HAUUTO + ["qipedc"] * H.N_QIPEDC)
        self.assertEqual(len({r["sample_id"] for r in self.rows}), len(self.rows))
        # (d) printed from the run, not typed
        print(f"\n[AC5] hauuto candidates with local video: {self.n_candidates}")
        for res in self.results:
            off = res["off"]
            print(f"[AC5] {res['row']['sample_id']}: frames={len(off['detected_mask'])} "
                  f"detected={int(off['detected_mask'].sum())}")

    def test_a_landmarks_bit_identical(self):
        for res in self.results:
            sid, off, live = res["row"]["sample_id"], res["off"], res["live"]
            lms, det, labels, scores = H.live_arrays(live)
            with self.subTest(sid):
                self.assertEqual(len(live), len(off["detected_mask"]))
                self.assertEqual(len(live), res["n_video_frames"])
                self.assertEqual([m["frame_seq"] for m in live], list(range(len(live))))
                self.assertTrue(np.array_equal(det, off["detected_mask"]))
                self.assertTrue(np.array_equal(lms[det], off["raw_landmarks"][det]))
                self.assertEqual(labels, off["handedness_label"])
                self.assertTrue(np.array_equal(scores[det], off["handedness_score"][det]))
                self.assertTrue(all(m["handedness_score"] is None for m in live if m["landmarks"] is None))

    def test_b_bodies_and_responses_identical(self):
        self.assertEqual(self.ckpt_sha, H.deployed_sha256())
        for res in self.results:
            sid, off = res["row"]["sample_id"], res["off"]
            meta = off["metadata"]
            body_live = H.body_from_hand_frames(res["live"])
            body_off = H.body_from_npz(off, meta["width"], meta["height"], meta["fps"])
            with self.subTest(sid):
                self.assertEqual(body_live, body_off)
                r_live = self.client.post(H.SEQ_PATH, json=body_live)
                r_off = self.client.post(H.SEQ_PATH, json=body_off)
                self.assertEqual(r_live.status_code, r_off.status_code)
                self.assertEqual(r_live.status_code, 200, r_live.text[:300])
                self.assertEqual(r_live.json(), r_off.json())
                self.assertEqual(r_live.json()["checkpoint"], "alphabet_best.pt")

    def test_c_offline_model_equals_live_prediction(self):
        import torch
        from src.data.alphabet_preprocessing import alphabet_clip_features

        classes, pre, kind = list(self.ckpt["classes"]), dict(self.ckpt["preprocessing"]), self.ckpt["model_type"]
        for res in self.results:
            sid, off = res["row"]["sample_id"], res["off"]
            meta = off["metadata"]
            ts = np.asarray([H.timestamp_ms(i, meta["fps"]) for i in range(len(off["detected_mask"]))])
            feats = alphabet_clip_features(off["raw_landmarks"], off["detected_mask"],
                                           np.array(off["handedness_label"]), meta["width"] / meta["height"], ts,
                                           pre, kind)
            with torch.no_grad():
                p = torch.softmax(self.model(torch.from_numpy(feats).unsqueeze(0)), dim=-1)[0].numpy()
            live = self.client.post(H.SEQ_PATH, json=H.body_from_hand_frames(res["live"])).json()
            with self.subTest(sid):
                self.assertEqual(live["prediction"], classes[int(p.argmax())])
                self.assertLessEqual(abs(live["confidence"] - float(p.max())), 1e-4)


if __name__ == "__main__":
    unittest.main()
