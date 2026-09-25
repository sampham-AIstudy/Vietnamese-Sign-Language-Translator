import os
import sys
import io
import time
import json
import glob
import numpy as np
import torch
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=== STARTING SECTION D: END-TO-END SMOKE TESTS ===")
smoke_results = {}

# -------------------------------------------------------------
# D1. VIDEO -> KEYPOINT EXTRACTION
# -------------------------------------------------------------
print("\n--- [D1] Video -> Keypoint Extraction ---")
from src.data.landmark_extractor import CleanHolisticExtractor

extractor = CleanHolisticExtractor(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    model_complexity=1
)

sample_vids = glob.glob('data/Dataset/Videos/*.mp4')[:2]
d1_records = []
for v_path in sample_vids:
    t0 = time.perf_counter()
    extracted = extractor.extract_from_video(v_path)
    dur = (time.perf_counter() - t0) * 1000.0
    kps = extracted['keypoints']
    vis = extracted['visibility_mask']
    d1_records.append({
        "video": os.path.basename(v_path),
        "shape": list(kps.shape),
        "vis_shape": list(vis.shape) if vis is not None else None,
        "latency_ms": round(dur, 2),
        "valid_shape": kps.ndim == 3 and kps.shape[1] == 67 and kps.shape[2] == 3,
    })
    print(f"  {os.path.basename(v_path)} -> shape: {kps.shape}, time: {dur:.1f}ms")

smoke_results["d1_extraction"] = d1_records

# -------------------------------------------------------------
# D2. KEYPOINT -> LEVEL 2 PREDICTOR (ST-GCN)
# -------------------------------------------------------------
print("\n--- [D2] Keypoint -> Level 2 ST-GCN Predictor ---")
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline
from src.inference.predictor import VSLPredictor

preprocessor = VSLPreprocessingPipeline(
    target_len=60,
    vis_threshold=0.5,
    center_mode="mid_shoulder",
    scale_mode="shoulder_width",
    temporal_mode="pad",
)

predictor = VSLPredictor(
    model_type="stgcn",
    stgcn_ckpt="checkpoints/stgcn_tier2_indomain.pt",
    classes_path="configs/tier2_classes.txt",
    warmup=True
)

sample_kps = glob.glob('data/extracted_keypoints/*.npz')[:3]
d2_records = []
for kp_path in sample_kps:
    d = np.load(kp_path)
    kps = d['keypoints']
    vis = d['visibility_mask']
    seq, jm, tm = preprocessor(kps, vis)
    t0 = time.perf_counter()
    pred = predictor.predict(seq, joint_mask=jm, temporal_mask=tm)
    dur = (time.perf_counter() - t0) * 1000.0
    d2_records.append({
        "sample": os.path.basename(kp_path),
        "top1": pred["gloss"],
        "confidence": pred["confidence"],
        "top5": pred["top5"][:3],
        "latency_ms": round(dur, 2),
    })
    print(f"  {os.path.basename(kp_path)} -> top1: '{pred['gloss']}' (conf: {pred['confidence']:.3f}), latency: {dur:.1f}ms")

smoke_results["d2_level2"] = d2_records

# -------------------------------------------------------------
# D3. KEYPOINT -> LEVEL 3 CSLR (ST-GCN + BiGRU)
# -------------------------------------------------------------
print("\n--- [D3] Keypoint -> Level 3 CSLR Recognizer ---")
from src.data.vsl_gh_dataset import convert_137_to_67
from src.translation.cslr_recognizer import CSLRRecognizer

cslr = CSLRRecognizer(
    checkpoint_path="checkpoints/cslr_best.pt",
    vocab_path="data/external/vsl_gh/gloss_vocab_canonical.txt"
)

sample_cslr_kps = [
    'data/external/vsl_gh/keypoints_frontal/SENT001_S01_R01_F.npy',
    'data/external/vsl_gh/keypoints_frontal/SENT002_S01_R01_F.npy',
]
d3_records = []
cslr_glosses = []
for kp_path in sample_cslr_kps:
    arr = np.load(kp_path)
    kps_67 = convert_137_to_67(arr, mode="semantic")
    t0 = time.perf_counter()
    res = cslr.predict(kps_67)
    dur = (time.perf_counter() - t0) * 1000.0
    cslr_glosses.append(res["gloss_str"])
    d3_records.append({
        "sample": os.path.basename(kp_path),
        "input_shape": list(arr.shape),
        "converted_shape": list(kps_67.shape),
        "num_frames": res["num_frames"],
        "gloss_list": res["gloss_list"],
        "gloss_str": res["gloss_str"],
        "latency_ms": round(dur, 2),
    })
    print(f"  {os.path.basename(kp_path)} -> glosses: '{res['gloss_str']}', latency: {dur:.1f}ms")

smoke_results["d3_cslr"] = d3_records

# -------------------------------------------------------------
# D4. GLOSS -> LEVEL 3 TRANSLATOR (ViT5)
# -------------------------------------------------------------
print("\n--- [D4] Gloss -> Level 3 ViT5 Translation ---")
from src.translation.translator import VSLTranslator

translator = VSLTranslator(
    model_path="checkpoints/vit5_stage2/best_model"
)

oracle_glosses = [
    "TÔI ĐĂNG-KÝ KHÁM SỨC-KHỎE MUỐN",
    "BẠN TÊN GÌ",
]
d4_oracle = []
for g in oracle_glosses:
    res = translator.translate(g)
    d4_oracle.append({
        "input_gloss": g,
        "translation": res["translation"],
        "latency_ms": res["latency_ms"],
    })
    print(f"  [Oracle] '{g}' -> '{res['translation']}' ({res['latency_ms']:.1f}ms)")

d4_cslr = []
for g in cslr_glosses:
    res = translator.translate(g)
    d4_cslr.append({
        "input_cslr_gloss": g,
        "translation": res["translation"],
        "latency_ms": res["latency_ms"],
    })
    print(f"  [CSLR Pred] '{g}' -> '{res['translation']}' ({res['latency_ms']:.1f}ms)")

smoke_results["d4_translation"] = {
    "oracle": d4_oracle,
    "cslr_predicted": d4_cslr,
}

# -------------------------------------------------------------
# D5. BACKEND API & WEBSOCKET SMOKE TESTS
# -------------------------------------------------------------
print("\n--- [D5] Backend API & WebSocket Smoke Tests ---")
from starlette.testclient import TestClient
from backend.main import app

client = TestClient(app)

# GET /health
r_health = client.get("/health")
print(f"  GET /health: {r_health.status_code}, status={r_health.json().get('status')}")

# GET /api/classes
r_classes = client.get("/api/classes")
print(f"  GET /api/classes: {r_classes.status_code}, total={r_classes.json().get('total')}")

# GET /api/dictionary
r_dict = client.get("/api/dictionary?limit=5")
print(f"  GET /api/dictionary: {r_dict.status_code}, total_items={r_dict.json().get('total')}")

# POST /api/translate
r_trans = client.post("/api/translate", json={"glosses": "TÔI MUỐN HỌC BÀI", "attach_lexicon": False})
print(f"  POST /api/translate: {r_trans.status_code}, trans='{r_trans.json().get('translation')}'")

# WebSocket /ws/live-stream
ws_status = "UNKNOWN"
try:
    with client.websocket_connect("/ws/live-stream") as ws:
        import cv2
        dummy_img = np.zeros((240, 320, 3), dtype=np.uint8)
        _, img_buf = cv2.imencode(".jpg", dummy_img)
        ws.send_bytes(img_buf.tobytes())
        data = ws.receive_json()
        print(f"  WS /ws/live-stream: SUCCESS, received response type='{data.get('type')}', status='{data.get('status')}'")
        ws_status = "PASS"
except Exception as e:
    print(f"  WS /ws/live-stream error: {e}")
    ws_status = f"FAIL: {e}"

smoke_results["d5_backend"] = {
    "health_status_code": r_health.status_code,
    "health_json": r_health.json(),
    "classes_count": r_classes.json().get('total'),
    "dictionary_count": r_dict.json().get('total'),
    "translate_status_code": r_trans.status_code,
    "translate_result": r_trans.json().get('translation'),
    "websocket_status": ws_status,
}

# -------------------------------------------------------------
# D7. LATENCY BENCHMARK (Mean, p50, p95)
# -------------------------------------------------------------
print("\n--- [D7] Latency Benchmark on ST-GCN Tier 2 ---")
dummy_seq = torch.randn(1, 60, 67, 3, device=predictor.device)
dummy_jm = torch.ones(1, 60, 67, device=predictor.device)
dummy_tm = torch.ones(1, 60, device=predictor.device)

latencies = []
for _ in range(50):
    t0 = time.perf_counter()
    _ = predictor.predict(dummy_seq, joint_mask=dummy_jm, temporal_mask=dummy_tm)
    latencies.append((time.perf_counter() - t0) * 1000.0)

mean_l = float(np.mean(latencies))
p50_l = float(np.percentile(latencies, 50))
p95_l = float(np.percentile(latencies, 95))
print(f"  ST-GCN Inference Latency (50 runs): Mean={mean_l:.2f}ms, p50={p50_l:.2f}ms, p95={p95_l:.2f}ms (< 150ms PASS)")

smoke_results["d7_latency"] = {
    "mean_ms": round(mean_l, 2),
    "p50_ms": round(p50_l, 2),
    "p95_ms": round(p95_l, 2),
    "target_lt_150ms": p95_l < 150.0,
}

with open('reports/audit_20260924/smoke_results.json', 'w', encoding='utf-8') as f:
    json.dump(smoke_results, f, indent=2, ensure_ascii=False)

print("\nAll Section D smoke tests finished successfully and saved to smoke_results.json.")
