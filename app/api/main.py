"""
FastAPI Backend for Vietnamese Sign Language (VSL) Recognition Service.
Exposes REST endpoints for:
1. Static alphabet recognition (42-dim normalized hand keypoints or image)
2. Word-level VSL sequence recognition (60-frame x 201-dim landmarks or mp4 video)
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import io
import json
import time
import base64
import tempfile
from collections import deque
import cv2
import numpy as np
import torch
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

from src.models.alphabet_classifier import AlphabetMLP
from src.models.gru_classifier import BiGRUSequenceClassifier
from src.models.transformer_classifier import VSLTransformerClassifier
from src.data.extract_landmarks import HolisticLandmarkExtractor, HandLandmarkExtractor

app = FastAPI(
    title="Vietnamese Sign Language (VSL) Recognition API",
    description="Dual-tier API for VSL Alphabet Fingerspelling and Word-Level SLR",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model caches
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ALPHABET_MODEL = None
ALPHABET_CLASSES: Dict[int, str] = {}
WORD_MODEL = None
WORD_CLASSES: Dict[int, str] = {}
HOLISTIC_EXTRACTOR = None
HAND_EXTRACTOR = None


class AlphabetKeypointsInput(BaseModel):
    keypoints: List[float]  # 42 floats


class WordSequenceInput(BaseModel):
    sequence: List[List[float]]  # 60 frames x 201 floats


def load_models_if_needed():
    global ALPHABET_MODEL, ALPHABET_CLASSES, WORD_MODEL, WORD_CLASSES, HOLISTIC_EXTRACTOR, HAND_EXTRACTOR

    # 1. Alphabet model
    alphabet_ckpt = "experiments/alphabet_model.pth"
    if ALPHABET_MODEL is None and os.path.isfile(alphabet_ckpt):
        ckpt = torch.load(alphabet_ckpt, map_location=DEVICE)
        num_cls = ckpt["num_classes"]
        ALPHABET_MODEL = AlphabetMLP(input_dim=42, num_classes=num_cls).to(DEVICE)
        ALPHABET_MODEL.load_state_dict(ckpt["model_state_dict"])
        ALPHABET_MODEL.eval()
        ALPHABET_CLASSES = {v: k for k, v in ckpt["class_to_idx"].items()}

    # 2. Word model
    word_ckpt = "experiments/word_model_bigru.pth"
    if not os.path.isfile(word_ckpt):
        word_ckpt = "experiments/word_model_transformer.pth"

    if WORD_MODEL is None and os.path.isfile(word_ckpt):
        ckpt = torch.load(word_ckpt, map_location=DEVICE)
        m_type = ckpt.get("model_type", "bigru")
        num_cls = ckpt["num_classes"]
        WORD_CLASSES = ckpt["idx_to_class"]
        # Ensure integer keys
        WORD_CLASSES = {int(k): v for k, v in WORD_CLASSES.items()}

        if m_type == "bigru":
            WORD_MODEL = BiGRUSequenceClassifier(
                input_dim=201, hidden_dim=128, num_layers=2, num_classes=num_cls
            ).to(DEVICE)
        else:
            WORD_MODEL = VSLTransformerClassifier(
                input_dim=201, d_model=128, nhead=4, num_layers=3, num_classes=num_cls
            ).to(DEVICE)

        WORD_MODEL.load_state_dict(ckpt["model_state_dict"])
        WORD_MODEL.eval()


@app.on_event("startup")
def startup_event():
    load_models_if_needed()


@app.get("/health")
def health_check():
    load_models_if_needed()
    return {
        "status": "online",
        "device": str(DEVICE),
        "alphabet_model_loaded": ALPHABET_MODEL is not None,
        "word_model_loaded": WORD_MODEL is not None,
        "num_alphabet_classes": len(ALPHABET_CLASSES),
        "num_word_classes": len(WORD_CLASSES),
    }


@app.get("/classes/alphabet")
def get_alphabet_classes():
    load_models_if_needed()
    return {"classes": ALPHABET_CLASSES}


@app.get("/classes/word")
def get_word_classes():
    load_models_if_needed()
    return {"classes": WORD_CLASSES}


@app.post("/predict/alphabet")
def predict_alphabet(data: AlphabetKeypointsInput):
    load_models_if_needed()
    if ALPHABET_MODEL is None:
        raise HTTPException(status_code=503, detail="Alphabet model not loaded. Train it first!")

    if len(data.keypoints) != 42:
        raise HTTPException(status_code=400, detail=f"Expected 42 keypoint coordinates, got {len(data.keypoints)}")

    inp = torch.tensor([data.keypoints], dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        logits = ALPHABET_MODEL(inp)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    top3_idx = np.argsort(probs)[-3:][::-1]
    top_class = ALPHABET_CLASSES.get(int(top3_idx[0]), f"Class_{top3_idx[0]}")
    confidence = float(probs[top3_idx[0]])

    candidates = [
        {"class": ALPHABET_CLASSES.get(int(idx), f"Class_{idx}"), "confidence": float(probs[idx])}
        for idx in top3_idx
    ]

    return {
        "prediction": top_class,
        "confidence": confidence,
        "candidates": candidates,
    }


@app.post("/predict/word")
def predict_word(data: WordSequenceInput):
    load_models_if_needed()
    if WORD_MODEL is None:
        raise HTTPException(status_code=503, detail="Word SLR model not loaded. Train it first!")

    seq = np.array(data.sequence, dtype=np.float32)
    if seq.shape != (60, 201):
        raise HTTPException(status_code=400, detail=f"Expected sequence shape (60, 201), got {seq.shape}")

    inp = torch.tensor([seq], dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        logits = WORD_MODEL(inp)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    top5_idx = np.argsort(probs)[-5:][::-1]
    top_class = WORD_CLASSES.get(int(top5_idx[0]), f"Class_{top5_idx[0]}")
    confidence = float(probs[top5_idx[0]])

    candidates = [
        {"gloss": WORD_CLASSES.get(int(idx), f"Class_{idx}"), "confidence": float(probs[idx])}
        for idx in top5_idx
    ]

    return {
        "prediction": top_class,
        "confidence": confidence,
        "candidates": candidates,
    }


@app.post("/predict/video")
async def predict_video(file: UploadFile = File(...)):
    """Uploads an MP4 video clip, extracts MediaPipe Holistic landmarks, and predicts the sign."""
    load_models_if_needed()
    if WORD_MODEL is None:
        raise HTTPException(status_code=503, detail="Word SLR model not loaded. Train it first!")

    global HOLISTIC_EXTRACTOR
    if HOLISTIC_EXTRACTOR is None:
        HOLISTIC_EXTRACTOR = HolisticLandmarkExtractor()

    # Save to temp file
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        sequence = HOLISTIC_EXTRACTOR.extract_from_video(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    inp = torch.tensor([sequence], dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        logits = WORD_MODEL(inp)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    top5_idx = np.argsort(probs)[-5:][::-1]
    top_class = WORD_CLASSES.get(int(top5_idx[0]), f"Class_{top5_idx[0]}")

    candidates = [
        {"gloss": WORD_CLASSES.get(int(idx), f"Class_{idx}"), "confidence": float(probs[idx])}
        for idx in top5_idx
    ]

    return {
        "prediction": top_class,
        "confidence": float(probs[top5_idx[0]]),
        "candidates": candidates,
        "sequence_frames": int(sequence.shape[0]),
    }


# ==============================================================================
# VSL DICTIONARY & EXPLORER ENDPOINTS
# ==============================================================================
VSL_LABEL_CACHE = None

def get_vsl_labels_df():
    global VSL_LABEL_CACHE
    if VSL_LABEL_CACHE is None:
        csv_path = "data (2)/Dataset/Labels/label.csv"
        if os.path.isfile(csv_path):
            VSL_LABEL_CACHE = pd.read_csv(csv_path)
    return VSL_LABEL_CACHE


@app.get("/dictionary")
def get_dictionary(q: Optional[str] = None, region: Optional[str] = None, limit: int = 50, offset: int = 0):
    df = get_vsl_labels_df()
    if df is None:
        return {"total": 0, "items": []}

    filtered = df.copy()
    if q:
        filtered = filtered[filtered["LABEL"].str.contains(q, case=False, na=False)]
    if region:
        # Filter by region code in video filename: B (North), T (Central), N (South)
        code = region.upper().strip()
        filtered = filtered[filtered["VIDEO"].str.contains(f"{code}.mp4", case=False, na=False)]

    total = len(filtered)
    items = filtered.iloc[offset : offset + limit].to_dict(orient="records")
    for item in items:
        vid = item.get("VIDEO", "")
        if "B.mp4" in vid:
            item["region"] = "Miền Bắc (North)"
        elif "T.mp4" in vid:
            item["region"] = "Miền Trung (Central)"
        elif "N.mp4" in vid:
            item["region"] = "Miền Nam (South)"
        else:
            item["region"] = "Chung"

    return {"total": total, "limit": limit, "offset": offset, "items": items}


# ==============================================================================
# REAL-TIME WEBSOCKET STREAMING & TELEMETRY
# ==============================================================================
@app.websocket("/ws/live-stream")
async def websocket_live_stream(websocket: WebSocket):
    """
    High-performance WebSocket endpoint for real-time video stream recognition.
    Receives base64/binary frames, runs MediaPipe Holistic extraction + BiGRU inference,
    and returns precise microsecond latency telemetry (preprocess_ms, infer_ms, total_ms).
    """
    await websocket.accept()
    load_models_if_needed()

    global HOLISTIC_EXTRACTOR
    if HOLISTIC_EXTRACTOR is None:
        HOLISTIC_EXTRACTOR = HolisticLandmarkExtractor(target_seq_len=60)

    # State per websocket connection
    buffer = deque()
    frame_counter = 0
    last_frame_time = time.perf_counter()
    server_fps = 0.0

    last_emitted_gloss = ""
    last_emitted_time = 0.0

    # Default parameters (client can override dynamically)
    window_sec = 2.0
    conf_threshold = 0.65
    debounce_sec = 1.2
    infer_interval = 5

    try:
        while True:
            raw_data = await websocket.receive_text()
            t0 = time.perf_counter()

            try:
                payload = json.loads(raw_data)
            except Exception:
                continue

            # Update client config if provided
            if "config" in payload:
                cfg = payload["config"]
                window_sec = float(cfg.get("window_sec", window_sec))
                conf_threshold = float(cfg.get("confidence_threshold", conf_threshold))
                debounce_sec = float(cfg.get("debounce_sec", debounce_sec))

            client_ts = payload.get("timestamp", 0)
            img_b64 = payload.get("image", "")
            if not img_b64:
                continue

            # Decode base64 image
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(img_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception:
                continue

            if frame_bgr is None:
                continue

            # Calculate FPS
            dt = t0 - last_frame_time
            if dt > 0:
                current_fps = 1.0 / dt
                server_fps = 0.9 * server_fps + 0.1 * current_fps if server_fps > 0 else current_fps
            last_frame_time = t0
            frame_counter += 1

            # 1. MediaPipe Holistic Landmark Extraction
            img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            holistic = HOLISTIC_EXTRACTOR._get_holistic()
            results = holistic.process(img_rgb)

            pose = np.zeros((25, 3), dtype=np.float32)
            raw_pose_list = []
            if results.pose_landmarks:
                for idx in range(min(25, len(results.pose_landmarks.landmark))):
                    lm = results.pose_landmarks.landmark[idx]
                    pose[idx] = [lm.x, lm.y, lm.z]
                    raw_pose_list.append([round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)])

            lh = np.zeros((21, 3), dtype=np.float32)
            raw_lh_list = []
            if results.left_hand_landmarks:
                for idx, lm in enumerate(results.left_hand_landmarks.landmark):
                    lh[idx] = [lm.x, lm.y, lm.z]
                    raw_lh_list.append([round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)])

            rh = np.zeros((21, 3), dtype=np.float32)
            raw_rh_list = []
            if results.right_hand_landmarks:
                for idx, lm in enumerate(results.right_hand_landmarks.landmark):
                    rh[idx] = [lm.x, lm.y, lm.z]
                    raw_rh_list.append([round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)])

            feature_201 = np.concatenate([pose.flatten(), lh.flatten(), rh.flatten()])
            t_preprocess = time.perf_counter()

            # 2. Maintain sliding window buffer
            now = time.time()
            buffer.append((now, feature_201))
            cutoff = now - window_sec
            while buffer and buffer[0][0] < cutoff:
                buffer.popleft()

            # 3. Model Inference (every infer_interval frames)
            pred_gloss = "..."
            pred_conf = 0.0
            top5_candidates = []
            is_confident = False
            should_emit_word = False
            ran_infer = False
            t_infer = t_preprocess

            if (
                WORD_MODEL is not None
                and WORD_CLASSES
                and frame_counter % infer_interval == 0
                and len(buffer) >= 12
            ):
                buf_duration = buffer[-1][0] - buffer[0][0]
                if buf_duration >= 0.8:
                    ran_infer = True
                    raw_seq = np.array([item[1] for item in buffer], dtype=np.float32)
                    resampled = HOLISTIC_EXTRACTOR.resample_sequence(raw_seq, target_len=60)

                    inp_t = torch.tensor(resampled, dtype=torch.float32).unsqueeze(0).to(DEVICE)
                    with torch.no_grad():
                        logits = WORD_MODEL(inp_t)
                        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

                    top_indices = np.argsort(probs)[-5:][::-1]
                    top1_idx = int(top_indices[0])
                    pred_gloss = WORD_CLASSES.get(top1_idx, "Unknown")
                    pred_conf = float(probs[top1_idx])

                    top5_candidates = [
                        {"gloss": WORD_CLASSES.get(int(idx), f"Class_{idx}"), "confidence": float(probs[idx])}
                        for idx in top_indices
                    ]

                    is_confident = pred_conf >= conf_threshold
                    if is_confident:
                        time_since = now - last_emitted_time
                        is_new = pred_gloss != last_emitted_gloss
                        if is_new or (time_since >= debounce_sec):
                            should_emit_word = True
                            last_emitted_gloss = pred_gloss
                            last_emitted_time = now

                    t_infer = time.perf_counter()

            t_end = time.perf_counter()

            # Build telemetry and prediction response packet
            response = {
                "type": "frame_result",
                "prediction": pred_gloss,
                "confidence": round(pred_conf, 4),
                "is_signing": is_confident,
                "should_append": should_emit_word,
                "top5": top5_candidates,
                "landmarks": {
                    "pose": raw_pose_list,
                    "left_hand": raw_lh_list,
                    "right_hand": raw_rh_list,
                },
                "metrics": {
                    "client_timestamp": client_ts,
                    "server_preprocess_ms": round((t_preprocess - t0) * 1000, 2),
                    "server_infer_ms": round((t_infer - t_preprocess) * 1000, 2) if ran_infer else 0.0,
                    "server_total_ms": round((t_end - t0) * 1000, 2),
                    "server_fps": round(server_fps, 1),
                    "buffer_frames": len(buffer),
                    "ran_infer": ran_infer,
                },
            }

            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
