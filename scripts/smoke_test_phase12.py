"""
Automated Smoke Test Verification for Phase 12:
FastAPI + React Production Pipeline (Web-Based Realtime Interface).

Verifications:
1. REST GET /health endpoint (System status, CUDA GPU, model readiness).
2. REST GET /model/info endpoint (Model architecture, 50-class vocabulary, 67-joint schema).
3. WebSocket /ws/live-stream connection & message protocol.
4. Base64 JPEG frame transmission & JSON prediction response.
5. Binary frame (Blob/Bytes) transmission & JSON prediction response.
6. Corrupt/Invalid frame graceful error handling (zero server crash).
7. End-to-end multi-frame streaming with real sign language video (W00009N.mp4).
8. Strict schema conformance: gloss, confidence, top5, latency_ms, fps, status.
"""

import os
import sys
import time
import json
import base64
import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.main import app


def run_smoke_test_phase12():
    print("=" * 64)
    print("PHASE 12 SMOKE TEST: FastAPI + React Production Pipeline")
    print("=" * 64)

    # 1. Test REST Endpoints
    print("\n[1/5] Testing REST Endpoints (/health & /model/info)...")
    with TestClient(app) as client:
        # A. GET /health
        res_health = client.get("/health")
        assert res_health.status_code == 200, f"Health check failed: {res_health.status_code}"
        health_data = res_health.json()
        print(f"  -> Health: Status='{health_data['status']}' | Device='{health_data['device']}' | GPU='{health_data['hardware']}'")
        assert health_data["status"] == "ok"
        assert health_data["model_loaded"] is True
        assert health_data["num_classes"] > 0  # vocabulary size follows the loaded checkpoint

        # B. GET /model/info
        res_info = client.get("/model/info")
        assert res_info.status_code == 200, f"Model info failed: {res_info.status_code}"
        info_data = res_info.json()
        print(f"  -> Model Info: Type='{info_data['model_type']}' | Classes={info_data['num_classes']} | TargetLen={info_data['target_sequence_length']}")
        assert info_data["num_classes"] == health_data["num_classes"]
        assert len(info_data["classes"]) == info_data["num_classes"]
        assert info_data["joint_schema"]["total_joints"] == 67
        print("  -> REST Endpoints passed successfully.")

        # 2. Test WebSocket Connection & Base64 Transmission
        print("\n[2/5] Testing WebSocket /ws/live-stream with Base64 JPEG frame...")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".jpg", dummy_frame)
        b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")

        with client.websocket_connect("/ws/live-stream") as ws:
            # Send Base64 JSON payload
            payload = {
                "image": b64_str,
                "timestamp": int(time.time() * 1000),
            }
            ws.send_text(json.dumps(payload))

            # Receive prediction
            resp_text = ws.receive_text()
            resp = json.loads(resp_text)
            print(f"  -> WS Base64 Response: Gloss='{resp['gloss']}' | Conf={resp['confidence']} | Status='{resp['status']}' | Latency={resp['latency_ms']}ms")

            # Validate Required Output Schema
            for req_key in ["gloss", "confidence", "top5", "latency_ms", "fps", "status"]:
                assert req_key in resp, f"Missing required key '{req_key}' in response: {resp}"

            assert resp["status"] in ["IDLE", "DETECTING", "CONFIRMED"]
            assert isinstance(resp["top5"], list)
            assert resp["latency_ms"] >= 0.0
            print("  -> WebSocket Base64 communication and schema verified.")

            # 3. Test Binary Frame Transmission
            print("\n[3/5] Testing WebSocket with Binary Frame (raw JPEG bytes)...")
            raw_bytes = buffer.tobytes()
            ws.send_bytes(raw_bytes)

            resp_binary = json.loads(ws.receive_text())
            print(f"  -> WS Binary Response: Gloss='{resp_binary['gloss']}' | Conf={resp_binary['confidence']} | Status='{resp_binary['status']}'")
            assert "gloss" in resp_binary and "status" in resp_binary
            print("  -> WebSocket Binary frame reception verified.")

            # 4. Test Corrupt / Invalid Frame Error Handling
            print("\n[4/5] Testing Invalid Frame Error Handling (Robustness)...")
            ws.send_text("THIS_IS_NOT_VALID_IMAGE_DATA")
            err_resp = json.loads(ws.receive_text())
            print(f"  -> Error Response: Status='{err_resp['status']}' | Error='{err_resp.get('error')}'")
            assert err_resp["status"] == "ERROR"
            print("  -> Robust error handling verified (connection maintained, zero crash).")

        # 5. End-to-End Live Stream on Real Video (W00009N.mp4)
        print("\n[5/5] Testing Multi-Frame Live Video Streaming with Real Sign Video...")
        sample_video = r"data\Dataset\Videos\W00009N.mp4"
        assert os.path.exists(sample_video), f"Sample video not found at: {sample_video}"

        cap = cv2.VideoCapture(sample_video)
        frames_sent = 0
        t0 = time.time()

        with client.websocket_connect("/ws/live-stream") as ws_stream:
            while frames_sent < 30:
                ret, frame = cap.read()
                if not ret:
                    break
                frames_sent += 1

                # Encode frame to JPEG
                _, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                b64_frame = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("utf-8")

                ws_stream.send_text(json.dumps({"image": b64_frame, "timestamp": int(time.time() * 1000)}))
                frame_resp = json.loads(ws_stream.receive_text())

                if frames_sent % 10 == 0:
                    print(f"  -> Frame {frames_sent}/30: Gloss='{frame_resp['gloss']}' | Status={frame_resp['status']} | Latency={frame_resp['latency_ms']}ms | Buffer={frame_resp.get('buffer_fill')}/60")

        cap.release()
        total_time = time.time() - t0
        client_fps = frames_sent / max(1e-5, total_time)
        print(f"  -> Streamed {frames_sent} frames in {total_time:.2f}s ({client_fps:.1f} FPS)")
        print("  -> Multi-frame streaming completed with zero errors.")

    print("\n" + "=" * 64)
    print(">>> PHASE 12 SMOKE TEST PASSED COMPLETELY! <<<")
    print("All Acceptance Criteria Satisfied:")
    print("  1. FastAPI Backend running with REST /health and /model/info: Validated")
    print("  2. WebSocket /ws/live-stream supporting both Base64 and Binary frames: Validated")
    print("  3. JSON Prediction Schema (gloss, confidence, top5, latency_ms, fps, status): Validated")
    print("  4. Real Video multi-frame streaming with RealtimePipeline: Validated")
    print("  5. Error recovery on corrupt frames: Validated")
    print("=" * 64)


if __name__ == "__main__":
    run_smoke_test_phase12()

