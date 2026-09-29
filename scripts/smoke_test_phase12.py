"""
Manual smoke test of the Phase 12 backend (FastAPI TestClient, real model of the running configuration):
REST /health + /model/info, WS /ws/live-stream protocol_version 2 (both live paths), WS /ws/hand-landmarks, Origin
check. Prints "PASSED" only when every assert passed.

Run with the default model and with the GATE candidate:
  PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py
  VSL_MODEL_TYPE=stgcn_h360 PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py

Inputs: a black 640x480 frame (protocol checks only), the first clip of scripts/live_clip_sample.select_train_clips
(seed 0, TRAIN split; 30 frames) and one frame of the hauuto clip a_hau_A_001.mp4 (training data of the Level 1
model; contract check only). No TEST/VAL clip is used.
"""

import base64
import collections
import json
import os
import sys
import time

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

import backend.main as api  # noqa: E402

# error codes of plan 04 §3.6
ERROR_CODES = {"message_too_large", "bad_message", "decode_failed", "unsupported_format", "frame_too_large",
               "frame_too_small", "bad_timestamp", "bad_config", "model_unavailable"}
LEGACY_KEYS = {"type", "pipeline", "gloss", "prediction", "confidence", "top5", "latency_ms", "fps", "status",
               "sentence", "is_confirmed", "translated_text", "oov_warning", "is_signing", "hand_detected",
               "buffer_fill", "buffer_capacity", "landmarks", "metrics"}
HAUUTO_CLIP = os.path.join(PROJECT_ROOT, "data", "external", "hauuto_raw", "raw", "raw", "hau", "a_hau_A_001.mp4")


def jpeg_data_url(frame, quality=75):
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    assert ok
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii"), buf.tobytes()


def receive_until_frame(ws, counts):
    """Messages until the frame_result (or error) of the frame just sent; sign_result / sign_discarded come first."""
    while True:
        m = ws.receive_json()
        counts[m["type"]] += 1
        if m["type"] in ("frame_result", "error"):
            return m


def check_frame_result(m, pipeline):
    assert m["type"] == "frame_result", m
    assert m["pipeline"] == pipeline, m
    if pipeline == "legacy":
        missing = LEGACY_KEYS - set(m)
        assert not missing, f"legacy frame_result misses {sorted(missing)}"
        assert m["status"] in ("IDLE", "DETECTING", "CONFIRMED"), m["status"]
    else:
        assert m["prediction"] is None and m["gloss"] is None and m["top5"] == [], m
        assert m["status"] in ("IDLE", "RECORDING", "WAIT_REST"), m["status"]


def run_smoke_test_phase12():
    print("=" * 64)
    print(f"PHASE 12 SMOKE TEST (VSL_MODEL_TYPE={os.environ.get('VSL_MODEL_TYPE', '<unset: default>')})")
    print("=" * 64)
    black = np.zeros((480, 640, 3), dtype=np.uint8)
    black_url, black_jpeg = jpeg_data_url(black)

    with TestClient(api.app) as client:
        print("\n[1/6] REST /health and /model/info")
        health = client.get("/health")
        assert health.status_code == 200, f"/health {health.status_code}: {health.text[:200]}"
        h = health.json()
        assert h["status"] == "ok" and h["model_loaded"] is True and h["num_classes"] > 0, h
        info = client.get("/model/info")
        assert info.status_code == 200, info.status_code
        i = info.json()
        assert i["num_classes"] == h["num_classes"] and len(i["classes"]) == i["num_classes"]
        print(f"  -> model_type={h['model_type']} num_classes={h['num_classes']} device={h['device']}")

        print("\n[2/6] /ws/live-stream: session_info + one base64 JPEG frame")
        with client.websocket_connect("/ws/live-stream") as ws:
            first = ws.receive_json()
            assert first["type"] == "session_info", first
            assert first["protocol_version"] == 2, first
            pipeline = first["pipeline"]
            assert pipeline in ("legacy", "harmonized_v1"), pipeline
            print(f"  -> session_info: pipeline={pipeline} model={first['model']['model_type']} "
                  f"is_default={first['model']['is_default']}")
            counts = collections.Counter()
            ws.send_json({"image": black_url, "timestamp": 1000.0})
            m = receive_until_frame(ws, counts)
            check_frame_result(m, pipeline)
            print(f"  -> frame_result: status={m['status']} latency_ms={m['latency_ms']}")

            print("\n[3/6] garbage text -> one error message, session stays open")
            ws.send_text("THIS_IS_NOT_VALID_IMAGE_DATA")
            err = ws.receive_json()
            assert err["type"] == "error", err
            assert err["code"] in ERROR_CODES, err
            print(f"  -> error code={err['code']} detail={err['detail']!r}")
            ws.send_json({"image": black_url, "timestamp": 2000.0})
            check_frame_result(receive_until_frame(ws, counts), pipeline)
            print("  -> next frame still answered")

        with client.websocket_connect("/ws/live-stream") as ws:
            assert ws.receive_json()["type"] == "session_info"
            ws.send_bytes(black_jpeg)
            check_frame_result(receive_until_frame(ws, collections.Counter()), pipeline)
            print("  -> binary JPEG frame answered (new session: binary frames carry no timestamp)")

        print("\n[4/6] /ws/live-stream: 30 frames of a real TRAIN clip")
        import live_clip_sample
        row = live_clip_sample.select_train_clips(1, 0)[0]
        cap = cv2.VideoCapture(row["video_path"])
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        counts = collections.Counter()
        sent = 0
        t0 = time.time()
        with client.websocket_connect("/ws/live-stream") as ws:
            assert ws.receive_json()["type"] == "session_info"
            while sent < 30:
                ok, frame = cap.read()
                if not ok:
                    break
                url, _ = jpeg_data_url(frame)
                ws.send_json({"image": url, "timestamp": sent * 1000.0 / fps})
                sent += 1
                m = receive_until_frame(ws, counts)
                if m["type"] == "frame_result":
                    check_frame_result(m, pipeline)
        cap.release()
        print(f"  -> clip {row['video_id']}: {sent} frames in {time.time() - t0:.2f}s; messages by type: "
              f"{dict(sorted(counts.items()))}")
        assert sent == 30, sent
        assert counts["error"] == 0, counts
        assert counts["frame_result"] == 30, counts

        print("\n[5/6] /ws/hand-landmarks: session_info -> reset_done -> hand_frame (real frame)")
        cap = cv2.VideoCapture(HAUUTO_CLIP)
        ok, frame = cap.read()
        cap.release()
        assert ok, f"cannot read {os.path.relpath(HAUUTO_CLIP, PROJECT_ROOT)}"
        with client.websocket_connect("/ws/hand-landmarks") as ws:
            si = ws.receive_json()
            assert si["type"] == "session_info" and si["endpoint"] == "hand-landmarks", si
            ws.send_json({"type": "control", "action": "reset"})
            rd = ws.receive_json()
            assert rd == {"type": "reset_done", "segment_id": 1}, rd
            ok, png = cv2.imencode(".png", frame)
            ws.send_json({"image": "data:image/png;base64," + base64.b64encode(png.tobytes()).decode("ascii"),
                          "timestamp": 0.0})
            hf = ws.receive_json()
            assert hf["type"] == "hand_frame" and hf["segment_id"] == 1 and hf["frame_seq"] == 0, hf
            n_points = len(hf["landmarks"]) if hf["landmarks"] else 0
            print(f"  -> extractor {si['extractor']['name']} {si['extractor']['mediapipe_version']}; "
                  f"hand_frame {hf['frame_width']}x{hf['frame_height']} points={n_points} "
                  f"handedness={hf['handedness']!r}")

        print("\n[6/6] foreign Origin is refused (1008) on both WebSockets")
        for path in ("/ws/live-stream", "/ws/hand-landmarks"):
            try:
                with client.websocket_connect(path, headers={"origin": "http://evil.example"}) as ws:
                    ws.receive_json()
                raise AssertionError(f"{path}: foreign Origin was accepted")
            except WebSocketDisconnect as e:
                assert e.code == 1008, e.code
            print(f"  -> {path}: close 1008")

    print("\n" + "=" * 64)
    print(">>> PHASE 12 SMOKE TEST PASSED <<<")
    print("=" * 64)


if __name__ == "__main__":
    run_smoke_test_phase12()
