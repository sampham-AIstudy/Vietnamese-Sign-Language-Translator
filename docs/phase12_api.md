# Phase 12: FastAPI + React Production Pipeline Documentation
**Vietnamese Sign Language Recognition (VSLR) — Web-Based Realtime Interface**

---

## 1. System Overview

Phase 12 delivers a web-based, real-time sign language recognition interface powered by:
- **Backend**: FastAPI with native WebSocket streaming (`backend/main.py`), utilizing PyTorch GPU inference (`VSLPredictor`) and MediaPipe Holistic (`RealtimePipeline`).
- **Frontend**: React 18 + Vite + Tailwind CSS (`frontend/`), featuring modular webcam capture (`CameraCapture.jsx`), HTML5 skeleton overlay, and live telemetry HUD (`PredictionDisplay.jsx`).

```
[Webcam (Client Browser)]
          │
          │ 1. Capture frame (Canvas 640x480 @ 25 FPS)
          │ 2. Compress JPEG (Base64 / Binary)
          ▼
   WebSocket Stream (ws://localhost:8000/ws/live-stream)
          │
          ▼
   [FastAPI Backend (backend/main.py)]
          │
          ├─► MediaPipe Holistic Extractor (67 landmarks: Pose + LH + RH)
          ├─► Temporal Sliding Window (60 frames buffer)
          ├─► Phase 2/3 Spatial Normalization (Mid-shoulder centering)
          ├─► VSLPredictor (ST-GCN / Ensemble CUDA Inference)
          └─► TemporalSmoother (Anti-flicker, Voting & Confirmation)
          │
          ▼
   WebSocket JSON Response (gloss, confidence, top5, latency_ms, fps, status)
          │
          ▼
[React Frontend HUD (PredictionDisplay.jsx)]
```

---

## 2. REST API Specification

### `GET /health`
Returns system status, CUDA GPU availability, and model readiness.

- **URL**: `http://localhost:8000/health`
- **Method**: `GET`
- **Response Format** (`200 OK`):
```json
{
  "status": "ok",
  "service": "vsl-backend",
  "cuda_available": true,
  "device": "cuda",
  "hardware": "NVIDIA GeForce RTX 3050 Laptop GPU",
  "model_loaded": true,
  "model_type": "stgcn",
  "num_classes": 50,
  "timestamp": 1789355410.33
}
```

### `GET /model/info`
Returns active model architecture, vocabulary classes, and landmark schema.

- **URL**: `http://localhost:8000/model/info`
- **Method**: `GET`
- **Response Format** (`200 OK`):
```json
{
  "model_type": "stgcn",
  "device": "cuda",
  "num_classes": 50,
  "classes": ["an_toan", "bao_ve", "benh_vien", "cam_on", "..."],
  "target_sequence_length": 60,
  "joint_schema": {
    "total_joints": 67,
    "features_per_frame": 201,
    "pose_joints": 25,
    "left_hand_joints": 21,
    "right_hand_joints": 21,
    "zero_fill_policy": "NO ZERO-FILL (Phase 0.5 Strict NaN/Visibility Mask)"
  }
}
```

---

## 3. WebSocket Realtime Streaming Protocol

### Connection Endpoint
```
ws://localhost:8000/ws/live-stream
```

### A. Client-to-Server Frame Transmission
The backend accepts two formats for maximum flexibility and performance:

#### Format 1: Base64 Encoded JSON (Default)
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
  "timestamp": 1789355412000,
  "config": {
    "confidence_threshold": 0.45
  }
}
```

#### Format 2: Binary Frame (Raw JPEG Bytes / ArrayBuffer / Blob)
Clients can directly transmit raw binary JPEG bytes through WebSocket binary frames to eliminate Base64 encoding overhead:
```javascript
canvas.toBlob((blob) => {
  if (ws.readyState === WebSocket.OPEN) ws.send(blob);
}, 'image/jpeg', 0.75);
```

---

### B. Server-to-Client Prediction Response Schema
Conforms strictly to Phase 12 requirements:

```json
{
  "type": "frame_result",
  "gloss": "cảm ơn",
  "confidence": 0.8842,
  "top5": [
    {"gloss": "cảm ơn", "confidence": 0.8842},
    {"gloss": "xin chào", "confidence": 0.0614},
    {"gloss": "tạm biệt", "confidence": 0.0215},
    {"gloss": "xin lỗi", "confidence": 0.0180},
    {"gloss": "giúp đỡ", "confidence": 0.0149}
  ],
  "latency_ms": 14.85,
  "fps": 28.6,
  "status": "CONFIRMED",
  "sentence": ["xin chào", "cảm ơn"],
  "is_confirmed": true,
  "is_signing": true,
  "hand_detected": true,
  "buffer_fill": 48,
  "buffer_capacity": 60,
  "landmarks": {
    "pose": [[0.51, 0.32], [0.49, 0.35]],
    "left_hand": [[0.45, 0.62], [0.44, 0.64]],
    "right_hand": [[0.58, 0.61], [0.60, 0.63]]
  }
}
```

### Recognition Status States (`status`):
- `IDLE`: User is resting, hands not engaged in signing, or confidence below detection threshold.
- `DETECTING`: Sign movement initiated; model is accumulating votes across sliding window buffer.
- `CONFIRMED`: Sign has passed temporal consistency threshold (held stable across consecutive windows); added to sentence accumulator.

---

## 4. How to Run & Verify

### Step 1: Start FastAPI Backend
From project root:
```powershell
.\.venv\Scripts\uvicorn.exe backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI docs available at: `http://localhost:8000/docs`

### Step 2: Start React Frontend
From project root:
```powershell
cd frontend
npm run dev
```
Web application opens at: `http://localhost:3000` (or `http://localhost:5173`)

### Step 3: Run Automated Smoke Test
To verify full REST endpoints, WebSocket Base64 and Binary transmission, error handling, and multi-frame sign video streaming:
```powershell
.\.venv\Scripts\python.exe scripts/smoke_test_phase12.py
```
Expected output:
```
================================================================
>>> PHASE 12 SMOKE TEST PASSED COMPLETELY! <<<
================================================================
```
