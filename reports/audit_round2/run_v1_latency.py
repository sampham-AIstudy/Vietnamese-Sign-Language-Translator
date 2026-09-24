import os
import sys
import io
import time
import json
import glob
import cv2
import numpy as np
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from backend.main import app

print("=== STARTING V1: REAL END-TO-END WEBSOCKET LATENCY BENCHMARK ===")

client = TestClient(app)

# Load real video frames to stream
sample_vid_path = glob.glob('data/Dataset/Videos/*.mp4')[0]
cap = cv2.VideoCapture(sample_vid_path)
frames_bytes = []
for _ in range(60):
    ret, frame = cap.read()
    if not ret:
        break
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    frames_bytes.append(buf.tobytes())
cap.release()

print(f"Loaded {len(frames_bytes)} frames from {os.path.basename(sample_vid_path)}.")

# Measure WebSocket latency
rtt_latencies = []
server_preprocess_list = []
server_infer_list = []
server_total_list = []
network_serialize_list = []
received_responses = 0
total_sent = 100

with client.websocket_connect("/ws/live-stream") as ws:
    # Warmup 5 frames
    for i in range(5):
        ws.send_bytes(frames_bytes[i % len(frames_bytes)])
        _ = ws.receive_json()

    print(f"Streaming {total_sent} frames at ~30 FPS interval...")
    for i in range(total_sent):
        frame_data = frames_bytes[i % len(frames_bytes)]
        t_send = time.perf_counter()
        ws.send_bytes(frame_data)
        
        # In synchronous TestClient, send_bytes and receive_json are locked step
        resp = ws.receive_json()
        t_recv = time.perf_counter()
        
        rtt_ms = (t_recv - t_send) * 1000.0
        rtt_latencies.append(rtt_ms)
        received_responses += 1

        metrics = resp.get("metrics", {})
        s_total = float(resp.get("latency_ms", 0.0))
        s_prep = float(metrics.get("server_preprocess_ms", 0.0))
        s_infer = float(metrics.get("server_infer_ms", 0.0))
        net_overhead = max(0.0, rtt_ms - s_total)

        server_preprocess_list.append(s_prep)
        server_infer_list.append(s_infer)
        server_total_list.append(s_total)
        network_serialize_list.append(net_overhead)

def calc_stats(arr):
    return {
        "mean": round(float(np.mean(arr)), 2),
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
    }

v1_results = {
    "total_sent": total_sent,
    "received_responses": received_responses,
    "drop_rate_pct": round((total_sent - received_responses) / total_sent * 100.0, 2),
    "client_rtt_e2e_ms": calc_stats(rtt_latencies),
    "server_total_ms": calc_stats(server_total_list),
    "server_mediapipe_preprocess_ms": calc_stats(server_preprocess_list),
    "server_model_infer_ms": calc_stats(server_infer_list),
    "network_serialize_ms": calc_stats(network_serialize_list),
}

print("\n--- V1 BENCHMARK SUMMARY ---")
print(f"Total Sent: {total_sent}, Received: {received_responses}, Drops: {total_sent - received_responses}")
print(f"Client E2E RTT (ms):  Mean={v1_results['client_rtt_e2e_ms']['mean']}, p50={v1_results['client_rtt_e2e_ms']['p50']}, p95={v1_results['client_rtt_e2e_ms']['p95']}, p99={v1_results['client_rtt_e2e_ms']['p99']}")
print(f"Server Preprocess (ms): Mean={v1_results['server_mediapipe_preprocess_ms']['mean']}, p50={v1_results['server_mediapipe_preprocess_ms']['p50']}, p95={v1_results['server_mediapipe_preprocess_ms']['p95']}")
print(f"Server Inference (ms):  Mean={v1_results['server_model_infer_ms']['mean']}, p50={v1_results['server_model_infer_ms']['p50']}, p95={v1_results['server_model_infer_ms']['p95']}")
print(f"Network/Serialize (ms): Mean={v1_results['network_serialize_ms']['mean']}, p50={v1_results['network_serialize_ms']['p50']}, p95={v1_results['network_serialize_ms']['p95']}")

with open('reports/audit_round2/v1_latency_benchmark.json', 'w', encoding='utf-8') as f:
    json.dump(v1_results, f, indent=2, ensure_ascii=False)

print("V1 Benchmark saved to reports/audit_round2/v1_latency_benchmark.json.")
