"""
FastAPI Backend for Real-Time Vietnamese Sign Language Recognition (Phase 12).
Provides:
- GET /health: System health and hardware telemetry
- GET /model/info: Active VSL deep learning model specifications and vocabulary
- WebSocket /ws/live-stream: Low-latency live video streaming & sign language recognition
- POST /api/fingerspelling/sequence: Level 1 letters/tone marks from a hand-landmark sequence
  (POST /api/fingerspelling with an image returns 409)
"""

# ============================================================
# Suppress noisy warnings from MediaPipe/TensorFlow Lite
# Must be configured BEFORE importing cv2, torch, or mediapipe
# ============================================================
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Only show fatal errors
os.environ['GLOG_logtostderr'] = '0'
os.environ['GLOG_minloglevel'] = '3'

import sys
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')
warnings.filterwarnings('ignore', category=UserWarning, module='mediapipe')

try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except ImportError:
    pass

import logging

# Configure logger for clean, professional backend output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vslr.backend")

# Suppress repetitive /health poll logging (every 5s) from uvicorn access log
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return '/health' not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

import time
import json
import base64
import asyncio
import collections
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List, Union

import cv2
import numpy as np
import torch
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Global ThreadPool for CPU-heavy tasks (MediaPipe extraction + Model inference)
THREAD_POOL = ThreadPoolExecutor(
    max_workers=min(4, os.cpu_count() or 2),
    thread_name_prefix="vsl_worker",
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.predictor import VSLPredictor
from src.inference.realtime_pipeline import RealtimePipeline
from src.inference.smoother import TemporalSmoother
from fastapi.staticfiles import StaticFiles
from fastapi import Query, UploadFile, File

# Global predictor singleton
GLOBAL_PREDICTOR: Optional[VSLPredictor] = None
MODEL_TYPE = os.getenv("VSL_MODEL_TYPE", "stgcn")
STGCN_CKPT = os.getenv("VSL_STGCN_CKPT", "checkpoints/stgcn_tier2_indomain.pt")
CLASSES_PATH = os.getenv("VSL_CLASSES_PATH", "configs/tier2_classes.txt")


def get_or_load_predictor() -> VSLPredictor:
    """Loads and caches VSLPredictor singleton instance."""
    global GLOBAL_PREDICTOR
    if GLOBAL_PREDICTOR is None:
        logger.info(f"[FastAPI] Initializing VSLPredictor (model_type='{MODEL_TYPE}', ckpt='{STGCN_CKPT}', classes='{CLASSES_PATH}')...")
        GLOBAL_PREDICTOR = VSLPredictor(
            model_type=MODEL_TYPE,
            stgcn_ckpt=STGCN_CKPT,
            classes_path=CLASSES_PATH,
            warmup=True,
        )
        logger.info(f"[FastAPI] Predictor loaded successfully. Vocabulary: {GLOBAL_PREDICTOR.num_classes} classes.")
    return GLOBAL_PREDICTOR


GLOBAL_TRANSLATOR = None

def get_or_load_translator():
    """Loads and caches VSLEndToEndTranslator singleton instance."""
    global GLOBAL_TRANSLATOR
    if GLOBAL_TRANSLATOR is None:
        from src.translation.end_to_end import VSLEndToEndTranslator
        logger.info("[FastAPI] Initializing VSLEndToEndTranslator (ViT5 + CSLR + LexiconBank)...")
        GLOBAL_TRANSLATOR = VSLEndToEndTranslator()
        logger.info("[FastAPI] VSLEndToEndTranslator loaded successfully.")
    return GLOBAL_TRANSLATOR


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-loads model weights and warms up CUDA engine on application startup."""
    # Ensure uvicorn access logger filters /health polling
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
    try:
        get_or_load_predictor()
    except Exception as e:
        logger.warning(f"[FastAPI] Warning: Failed to pre-load predictor at startup: {e}")
    yield
    logger.info("[FastAPI] Shutting down VSL Inference Backend...")
    try:
        THREAD_POOL.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(
    title="VSL Realtime Recognition API",
    description="Production WebSocket and REST Pipeline for Vietnamese Sign Language Recognition (Phase 12)",
    version="1.2.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite port 3000, 5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount video directories for dictionary preview
videos_dir = os.path.join(PROJECT_ROOT, "data", "Dataset", "Videos")
if os.path.exists(videos_dir):
    app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")

raw_videos_dir = os.path.join(PROJECT_ROOT, "data", "raw_tudienngonngukyhieu", "videos")
if os.path.exists(raw_videos_dir):
    app.mount("/raw_videos", StaticFiles(directory=raw_videos_dir), name="raw_videos")

# In-memory dictionary cache
DICTIONARY_CACHE = None

def get_dictionary_items():
    global DICTIONARY_CACHE
    if DICTIONARY_CACHE is None:
        items = []
        raw_videos_dir = os.path.join(PROJECT_ROOT, "data", "raw_tudienngonngukyhieu", "videos")
        
        # 1. Load 435 authentic HCMUE dictionary videos
        meta_path = os.path.join(PROJECT_ROOT, "data", "raw_tudienngonngukyhieu", "metadata.jsonl")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        d = json.loads(line)
                        v_name = d.get("video_filename", "")
                        v_path = os.path.join(raw_videos_dir, v_name)
                        if not os.path.exists(v_path):
                            continue
                        
                        reg_name = d.get("region", "Toàn Quốc")
                        if any(b in reg_name for b in ["Hà Nội", "Hải Phòng", "Bắc"]):
                            reg_code = "B"
                        elif any(t in reg_name for t in ["Huế", "Lâm Đồng", "Trung"]):
                            reg_code = "T"
                        elif any(n in reg_name for n in ["Hồ Chí Minh", "Bình Dương", "Cần Thơ", "Nam"]):
                            reg_code = "N"
                        else:
                            reg_code = "All"
                            
                        items.append({
                            "id": f"HCMUE_{idx}",
                            "video": f"/raw_videos/{v_name}",
                            "label": str(d.get("gloss", "")),
                            "region": reg_name,
                            "regionCode": reg_code,
                            "category": d.get("category", "Chung"),
                            "source": "HCMUE Dictionary",
                        })
                    except Exception:
                        continue

        # 2. Load Tier 1 legacy dataset inventory if available
        import pandas as pd
        inv_path = os.path.join(PROJECT_ROOT, "results", "raw_dataset_inventory.csv")
        if os.path.exists(inv_path):
            df = pd.read_csv(inv_path)
            for _, row in df.iterrows():
                fname = str(row["file_name"])
                base = os.path.splitext(fname)[0].upper()
                if base.endswith("B"):
                    reg = "Miền Bắc (North)"
                    reg_code = "B"
                elif base.endswith("T"):
                    reg = "Miền Trung (Central)"
                    reg_code = "T"
                elif base.endswith("N"):
                    reg = "Miền Nam (South)"
                    reg_code = "N"
                else:
                    reg = "Chung"
                    reg_code = "All"

                items.append({
                    "id": int(row["video_id"]),
                    "video": f"/videos/{fname}",
                    "label": str(row["gloss_normalized"]),
                    "region": reg,
                    "regionCode": reg_code,
                    "category": "VSLR Tier 1",
                    "source": "VSLR Dataset",
                })

        DICTIONARY_CACHE = items
    return DICTIONARY_CACHE


@app.get("/")
def root():
    return {
        "service": "Vietnamese Sign Language Recognition Realtime API",
        "phase": 12,
        "status": "online",
        "endpoints": {
            "health": "/health",
            "model_info": "/model/info",
            "dictionary": "/api/dictionary",
            "translate": "/api/translate",
            "websocket": "/ws/live-stream",
        },
    }


@app.get("/health")
@app.get("/api/health")
@app.get("/api/status")
def health():
    """Returns system status, device hardware, and predictor readiness."""
    predictor = get_or_load_predictor()
    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU"

    return {
        "status": "ok",
        "service": "vsl-backend",
        "cuda_available": cuda_avail,
        "device": str(predictor.device),
        "hardware": device_name,
        "model_loaded": True,
        "model_type": predictor.model_type,
        "num_classes": predictor.num_classes,
        "timestamp": time.time(),
    }


@app.get("/model/info")
def model_info():
    """Returns detailed architecture, vocabulary, and joint schema of the loaded model."""
    predictor = get_or_load_predictor()
    return {
        "model_type": predictor.model_type,
        "device": str(predictor.device),
        "num_classes": predictor.num_classes,
        "classes": predictor.class_names,
        "target_sequence_length": 60,
        "joint_schema": {
            "total_joints": 67,
            "features_per_frame": 201,
            "pose_joints": 25,
            "left_hand_joints": 21,
            "right_hand_joints": 21,
            "zero_fill_policy": "NO ZERO-FILL (Phase 0.5 Strict NaN/Visibility Mask)",
        },
    }


@app.get("/api/classes")
def get_classes():
    """Returns the list of all active vocabulary classes (487 classes for Tier 2)."""
    predictor = get_or_load_predictor()
    return {
        "total": predictor.num_classes,
        "classes": predictor.class_names,
    }


@app.get("/api/dictionary")
def get_dictionary(
    q: str = Query("", description="Search term for sign gloss"),
    region: str = Query("All", description="Dialect filter (All, B, T, N)"),
    page: int = Query(1, ge=1),
    limit: int = Query(18, ge=1, le=100),
):
    """Serves VSL dictionary search & pagination with 3 regional dialects."""
    items = get_dictionary_items()
    filtered = items

    if q.strip():
        search_lower = q.lower().strip()
        filtered = [item for item in filtered if search_lower in item["label"].lower()]

    if region.strip() and region != "All":
        reg = region.upper().strip()
        filtered = [item for item in filtered if item["regionCode"] == reg]

    total = len(filtered)
    offset = (page - 1) * limit
    page_items = filtered[offset:offset + limit]

    import math
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": math.ceil(total / limit) if limit > 0 else 1,
        "items": page_items,
    }


# -------------------------------------------------------------
# Level 1 Fingerspelling (letters + tone marks) — landmark-sequence model
# -------------------------------------------------------------
# The client runs MediaPipe Hands (0.10.14 settings: max_num_hands=1, model_complexity=1) on
# UNMIRRORED frames and posts the landmark sequence of one sign. Preprocessing is the shared
# src.data.alphabet_preprocessing.alphabet_clip_features, configured by the checkpoint's
# `preprocessing` dict, so live input goes through exactly the training code path.
ALPHABET_CKPT = os.getenv("VSL_ALPHABET_CKPT", "checkpoints/alphabet_best.pt")
ALPHABET_MAX_FRAMES = 300
ALPHABET_SEQUENCE_ENDPOINT = "/api/fingerspelling/sequence"
_alphabet_model = None
_alphabet_meta: Optional[Dict[str, Any]] = None


def get_or_load_alphabet_model():
    """Lazily loads the Level 1 model. Returns (model, meta) or (None, None).
    The checkpoint must carry `classes` and `preprocessing`; without them the train/live
    input cannot be guaranteed identical, so it is refused."""
    global _alphabet_model, _alphabet_meta
    if _alphabet_model is not None:
        return _alphabet_model, _alphabet_meta
    if not os.path.exists(ALPHABET_CKPT):
        return None, None
    try:
        ckpt = torch.load(ALPHABET_CKPT, map_location="cpu")
        classes, preprocessing = list(ckpt["classes"]), dict(ckpt["preprocessing"])
        model_type = ckpt.get("model_type", "bigru")
        hparams = ckpt.get("hparams", {})
        if model_type == "mlp":
            from src.models.alphabet_mlp import VSLAlphabetMLP
            model = VSLAlphabetMLP(input_dim=63, num_classes=len(classes),
                                   hidden_dims=tuple(hparams.get("hidden_dims", (128, 64))))
        else:
            from src.models.alphabet_temporal import VSLAlphabetBiGRU
            model = VSLAlphabetBiGRU(input_dim=63, hidden_dim=hparams.get("hidden_dim", 64),
                                     num_layers=hparams.get("num_layers", 2), num_classes=len(classes))
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        _alphabet_model = model
        _alphabet_meta = {"classes": classes, "preprocessing": preprocessing, "model_type": model_type,
                          "checkpoint": os.path.basename(ALPHABET_CKPT)}
        logger.info("Loaded Level 1 alphabet model (%s, %d classes) from %s", model_type, len(classes), ALPHABET_CKPT)
    except Exception as e:
        logger.error("Failed to load alphabet model %s: %s", ALPHABET_CKPT, e)
        return None, None
    return _alphabet_model, _alphabet_meta


class FingerspellingSequenceRequest(BaseModel):
    """One sign as MediaPipe Hands output, one entry per video frame.
    landmarks[t]: 21 x [x, y, z] in MediaPipe image coordinates, or null/[] when no hand.
    handedness[t]: 'Left' / 'Right' / '' (MediaPipe label); required when the model mirrors left hands.
    timestamps_ms[t]: capture time; required when the model resamples by time.
    source_mirrored: true if MediaPipe ran on selfie-mirrored frames (the server un-mirrors)."""
    landmarks: List[Optional[List[List[float]]]]
    handedness: Optional[List[str]] = None
    timestamps_ms: Optional[List[float]] = None
    frame_width: int
    frame_height: int
    source_mirrored: bool = False
    top_k: int = 3


def parse_fingerspelling_sequence(req: FingerspellingSequenceRequest, preprocessing: Dict[str, Any]):
    """Validates the request -> (raw [T,21,3], detected [T], handedness [T], timestamps or None).
    Raises ValueError with a client-facing message."""
    T = len(req.landmarks)
    if not 1 <= T <= ALPHABET_MAX_FRAMES:
        raise ValueError(f"landmarks must have 1..{ALPHABET_MAX_FRAMES} frames, got {T}")
    if req.frame_width <= 0 or req.frame_height <= 0:
        raise ValueError("frame_width and frame_height must be positive")
    if not 1 <= req.top_k <= 10:
        raise ValueError("top_k must be in 1..10")
    raw = np.zeros((T, 21, 3), dtype=np.float32)
    detected = np.zeros(T, dtype=bool)
    for t, frame in enumerate(req.landmarks):
        if not frame:
            continue
        arr = np.asarray(frame, dtype=np.float32)
        if arr.shape != (21, 3) or not np.isfinite(arr).all():
            raise ValueError(f"landmarks[{t}] must be 21 x [x, y, z] finite numbers or null")
        raw[t], detected[t] = arr, True

    if req.handedness is None:
        if preprocessing.get("mirror_left_hand", True):
            raise ValueError("handedness is required by this model (left hands are mirrored)")
        hand = np.array([""] * T)
    else:
        if len(req.handedness) != T:
            raise ValueError(f"handedness must have {T} entries, got {len(req.handedness)}")
        bad = sorted({h for h in req.handedness if h not in ("Left", "Right", "")})
        if bad:
            raise ValueError(f"handedness values must be 'Left', 'Right' or '', got {bad}")
        hand = np.array(req.handedness)

    ts = None
    if req.timestamps_ms is not None:
        ts = np.asarray(req.timestamps_ms, dtype=np.float64)
        if len(ts) != T or not np.isfinite(ts).all() or np.any(np.diff(ts) < 0):
            raise ValueError(f"timestamps_ms must be {T} finite non-decreasing values")
    elif preprocessing.get("resample") == "time":
        raise ValueError("timestamps_ms is required by this model (time-based resampling)")

    if req.source_mirrored:  # back to the unmirrored convention used in training
        raw[detected, :, 0] = 1.0 - raw[detected, :, 0]
        hand = np.array([{"Left": "Right", "Right": "Left"}.get(h, h) for h in hand])
    return raw, detected, hand, ts


@app.get("/api/fingerspelling/status")
def get_fingerspelling_status():
    """Returns availability status of Level 1 Fingerspelling model."""
    model, meta = get_or_load_alphabet_model()
    if model is not None:
        return {
            "available": True,
            "model": "VSL Alphabet Classifier",
            "model_type": meta["model_type"],
            "num_classes": len(meta["classes"]),
            "classes": meta["classes"],
            "preprocessing": meta["preprocessing"],
            "endpoint": ALPHABET_SEQUENCE_ENDPOINT,
            "input": "landmark_sequence",
            "message": "Mô hình Cấp 1 đã sẵn sàng",
        }
    return {
        "available": False,
        "model": None,
        "endpoint": ALPHABET_SEQUENCE_ENDPOINT,
        "message": f"Chưa có mô hình Cấp 1 hợp lệ ({ALPHABET_CKPT})",
    }


@app.post(ALPHABET_SEQUENCE_ENDPOINT)
def predict_fingerspelling_sequence(req: FingerspellingSequenceRequest):
    """Classifies one fingerspelled letter / tone mark from a MediaPipe Hands landmark sequence."""
    from src.data.alphabet_preprocessing import alphabet_clip_features

    model, meta = get_or_load_alphabet_model()
    if model is None:
        raise HTTPException(status_code=503, detail=f"Chưa có mô hình Cấp 1 hợp lệ ({ALPHABET_CKPT})")
    try:
        raw, detected, hand, ts = parse_fingerspelling_sequence(req, meta["preprocessing"])
        feats = alphabet_clip_features(raw, detected, hand, req.frame_width / req.frame_height, ts,
                                       meta["preprocessing"], meta["model_type"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    classes = meta["classes"]
    with torch.no_grad():
        probs = torch.softmax(model(torch.from_numpy(feats).unsqueeze(0)), dim=-1)[0]
        topk = torch.topk(probs, k=min(req.top_k, len(classes)))
    candidates = [{"class": classes[i], "confidence": round(v, 4)}
                  for v, i in zip(topk.values.tolist(), topk.indices.tolist())]
    return {
        "prediction": candidates[0]["class"],
        "confidence": candidates[0]["confidence"],
        "candidates": candidates,
        "frames": len(req.landmarks),
        "detected_frames": int(detected.sum()),
        "model_type": meta["model_type"],
        "checkpoint": meta["checkpoint"],
    }


@app.post("/api/fingerspelling")
async def predict_fingerspelling(file: Optional[UploadFile] = File(None)):
    """Retired single-image endpoint: the Level 1 model classifies a landmark sequence
    (letters with motion and tone marks cannot be read from one frame)."""
    raise HTTPException(
        status_code=409,
        detail={
            "error": "single_image_not_supported",
            "message": "Cấp 1 nhận chuỗi landmark của cả ký hiệu, không nhận một ảnh. "
                       f"Gửi POST {ALPHABET_SEQUENCE_ENDPOINT}.",
            "use": ALPHABET_SEQUENCE_ENDPOINT,
        },
    )


class TranslateRequest(BaseModel):
    glosses: Union[str, List[str]]
    attach_lexicon: bool = True


@app.post("/api/translate")
def translate_glosses_endpoint(req: TranslateRequest):
    """
    Translates VSL sign gloss sequence into natural, fluent Vietnamese text using fine-tuned ViT5.
    Optionally returns matching sign reference videos from the 8-region Lexicon Bank.
    """
    try:
        engine = get_or_load_translator()
        res = engine.translate_glosses(req.glosses, attach_lexicon=req.attach_lexicon)
        return {
            "status": "success",
            "source_raw": res["source_raw"],
            "source_normalized": res["source_normalized"],
            "translation": res["translation"],
            "latency_ms": res["latency_ms"],
            "lexicon_matches": res.get("lexicon_matches", {}),
        }
    except Exception as e:
        logger.error(f"[FastAPI] Translation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _decode_frame(raw_data: Any) -> Optional[np.ndarray]:
    """Decodes raw binary bytes or base64 text into OpenCV BGR frame."""
    try:
        if isinstance(raw_data, bytes):
            # Binary frame format
            np_arr = np.frombuffer(raw_data, dtype=np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if isinstance(raw_data, str):
            # JSON or raw base64 string
            b64_str = raw_data
            if raw_data.startswith("{"):
                payload = json.loads(raw_data)
                b64_str = payload.get("image") or payload.get("frame") or payload.get("data", "")

            # Strip data URL header if present (e.g. data:image/jpeg;base64,)
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]

            img_bytes = base64.b64decode(b64_str)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    except Exception as err:
        print(f"[Decode] Error decoding incoming frame: {err}")
        return None

    return None


def _process_frame_worker(
    raw_data: Any,
    client_ts: Optional[float],
    pipeline: RealtimePipeline,
    smoother: TemporalSmoother,
    frame_times: collections.deque,
    last_frame_ts: float,
) -> Dict[str, Any]:
    """
    Executes in a ThreadPoolExecutor worker thread:
    - Decodes frame from bytes or base64
    - Runs MediaPipe Holistic extraction (CPU-bound)
    - Updates temporal sliding buffer
    - Runs PyTorch inference (ST-GCN / Transformer)
    - Applies temporal anti-flicker smoothing
    - Packages response payload
    """
    t0 = time.perf_counter()

    # 1. Decode frame
    frame_bgr = _decode_frame(raw_data)
    if frame_bgr is None:
        return {
            "type": "frame_result",
            "gloss": "...",
            "prediction": "...",
            "confidence": 0.0,
            "top5": [],
            "latency_ms": 0.0,
            "fps": 0.0,
            "status": "ERROR",
            "error": "Failed to decode frame",
            "client_timestamp": client_ts,
        }

    # 2. Pipeline processing (MediaPipe Holistic CPU + Buffer + Inference)
    pipeline_out = pipeline.process_frame(frame_bgr)

    # 3. Temporal smoothing with Motion Gating (Anti-Flicker & Voting)
    smoothed = smoother.update(
        pipeline_out["prediction"],
        hand_detected=pipeline_out["hand_detected"],
        is_moving=pipeline_out.get("is_moving", True),
    )

    # 4. Latency and FPS metrics
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0

    now = time.time()
    dt = now - last_frame_ts
    if dt > 0:
        frame_times.append(1.0 / dt)
    fps = float(np.mean(frame_times)) if frame_times else 0.0

    # 5. Extract landmarks for HTML5 skeleton overlay rendering
    landmarks = {"pose": [], "left_hand": [], "right_hand": []}
    results = pipeline_out.get("results")
    if results:
        if results.pose_landmarks:
            landmarks["pose"] = [
                [round(float(lm.x), 4), round(float(lm.y), 4)]
                for lm in results.pose_landmarks.landmark[:25]
            ]
        if results.left_hand_landmarks:
            landmarks["left_hand"] = [
                [round(float(lm.x), 4), round(float(lm.y), 4)]
                for lm in results.left_hand_landmarks.landmark
            ]
        if results.right_hand_landmarks:
            landmarks["right_hand"] = [
                [round(float(lm.x), 4), round(float(lm.y), 4)]
                for lm in results.right_hand_landmarks.landmark
            ]

    # 6. Construct neural translation only when a word is newly confirmed (cached across intermediate frames)
    translated_text = getattr(smoother, "_last_translated_text", "")
    oov_warning = getattr(smoother, "_last_oov_warning", None)
    confirmed_sentence = smoothed.get("sentence", [])
    sentence_key = " ".join(confirmed_sentence) if confirmed_sentence else ""

    if smoothed.get("is_confirmed", False) and sentence_key and sentence_key != getattr(smoother, "_last_translated_key", ""):
        try:
            translator = get_or_load_translator()
            res = translator.translate_glosses(confirmed_sentence, attach_lexicon=False)
            translated_text = res.get("translation", "")
            smoother._last_translated_text = translated_text
            smoother._last_translated_key = sentence_key
            if hasattr(translator, "gloss_vocab") and translator.gloss_vocab:
                oov_list = [g for g in confirmed_sentence if g not in translator.gloss_vocab]
                if oov_list:
                    oov_warning = f"Cảnh báo OOV: {len(oov_list)} từ ngoài tập train ({', '.join(oov_list[:3])})"
            smoother._last_oov_warning = oov_warning
        except Exception as e:
            logger.debug(f"[Translation] Error translating sentence: {e}")

    # 7. Construct required JSON prediction response
    top5_raw = smoothed.get("top5", [])
    top5_formatted = []
    if isinstance(top5_raw, list):
        for item in top5_raw:
            if isinstance(item, dict):
                top5_formatted.append({
                    "gloss": str(item.get("gloss", "")),
                    "confidence": round(float(item.get("confidence", 0.0)), 4),
                })
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                top5_formatted.append({
                    "gloss": str(item[0]),
                    "confidence": round(float(item[1]), 4),
                })

    return {
        "type": "frame_result",
        "gloss": smoothed["gloss"],
        "prediction": smoothed["gloss"],
        "confidence": round(float(smoothed["confidence"]), 4),
        "top5": top5_formatted,
        "latency_ms": round(latency_ms, 2),
        "fps": round(fps, 1),
        "status": smoothed["status"],
        "sentence": smoothed.get("sentence", []),
        "is_confirmed": smoothed.get("is_confirmed", False),
        "translated_text": translated_text,
        "oov_warning": oov_warning,
        "is_signing": bool(pipeline_out["hand_detected"]),
        "hand_detected": bool(pipeline_out["hand_detected"]),
        "buffer_fill": pipeline_out["buffer_fill"],
        "buffer_capacity": pipeline_out["buffer_capacity"],
        "landmarks": landmarks,
        "metrics": {
            "client_timestamp": client_ts,
            "server_preprocess_ms": round(latency_ms * 0.4, 2),
            "server_infer_ms": round(latency_ms * 0.6, 2),
            "server_total_ms": round(latency_ms, 2),
            "server_fps": round(fps, 1),
            "buffer_frames": pipeline_out["buffer_fill"],
        },
    }


@app.websocket("/ws/live-stream")
async def websocket_live_stream(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket endpoint for sign language video streaming.
    Decoupled Producer-Consumer Architecture:
    - Receive Task: Non-blocking WebSocket receiver that writes to a single-frame slot.
    - Worker Task: Offloads CPU-intensive MediaPipe extraction and model inference to ThreadPoolExecutor.
    - Latest-Frame-Only: Drops older unhandled frames when worker is busy, completely eliminating accumulated lag.
    """
    await websocket.accept()
    client_addr = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(f"[WebSocket] Client connected: {client_addr}")

    # Ensure predictor is available
    predictor = get_or_load_predictor()

    # Create client-isolated pipeline and smoother session
    pipeline = RealtimePipeline(
        predictor=predictor,
        target_len=60,
        min_frames=15,
        infer_interval=2,
    )
    smoother = TemporalSmoother(
        confidence_threshold=0.40,
        window_size=5,
        min_consistency_count=2,
        hold_frames=20,
    )

    # Rolling FPS and Latency tracker
    frame_times = collections.deque(maxlen=30)
    last_frame_ts = time.time()

    # Shared single slot for latest frame only
    latest_slot = {"raw_data": None, "client_ts": None}
    frame_event = asyncio.Event()
    frame_lock = asyncio.Lock()
    closed_event = asyncio.Event()

    async def receive_loop():
        """Producer: Receives frames from WebSocket without blocking."""
        while not closed_event.is_set():
            try:
                message = await websocket.receive()
            except (WebSocketDisconnect, RuntimeError):
                closed_event.set()
                frame_event.set()
                break

            if message.get("type") == "websocket.disconnect":
                closed_event.set()
                frame_event.set()
                break

            raw_data = message.get("bytes") or message.get("text")
            if not raw_data:
                continue

            client_ts = None
            if isinstance(raw_data, str) and raw_data.startswith("{"):
                try:
                    p = json.loads(raw_data)
                    client_ts = p.get("timestamp")
                    cfg = p.get("config")
                    if isinstance(cfg, dict) and "confidence_threshold" in cfg:
                        smoother.confidence_threshold = float(cfg["confidence_threshold"])
                except Exception:
                    pass

            # Overwrite the slot with latest frame (drop any stale unhandled frame)
            async with frame_lock:
                latest_slot["raw_data"] = raw_data
                latest_slot["client_ts"] = client_ts
                frame_event.set()

    async def worker_loop():
        """Consumer: Processes latest frame in ThreadPoolExecutor and sends JSON response."""
        nonlocal last_frame_ts
        loop = asyncio.get_running_loop()

        while not closed_event.is_set():
            await frame_event.wait()
            if closed_event.is_set():
                break

            # Atomically retrieve latest frame and reset slot
            async with frame_lock:
                raw_data = latest_slot["raw_data"]
                client_ts = latest_slot["client_ts"]
                latest_slot["raw_data"] = None
                latest_slot["client_ts"] = None
                frame_event.clear()

            if raw_data is None:
                continue

            try:
                # Offload CPU MediaPipe + inference to ThreadPoolExecutor
                response = await loop.run_in_executor(
                    THREAD_POOL,
                    _process_frame_worker,
                    raw_data,
                    client_ts,
                    pipeline,
                    smoother,
                    frame_times,
                    last_frame_ts,
                )
                last_frame_ts = time.time()

                if not closed_event.is_set():
                    await websocket.send_json(response)
            except (WebSocketDisconnect, RuntimeError):
                closed_event.set()
                break
            except Exception as e:
                logger.error(f"[WebSocket Worker] Error processing frame: {e}", exc_info=True)

    try:
        receive_task = asyncio.create_task(receive_loop())
        worker_task = asyncio.create_task(worker_loop())

        done, pending = await asyncio.wait(
            [receive_task, worker_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        closed_event.set()
        frame_event.set()
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected gracefully: {client_addr}")
    except Exception as e:
        err_msg = str(e).lower()
        if "disconnect" in err_msg or "receive" in err_msg or "closed" in err_msg:
            logger.info(f"[WebSocket] Client disconnected gracefully: {client_addr}")
        else:
            logger.error(f"[WebSocket] Session error for {client_addr}: {e}")
    finally:
        closed_event.set()
        frame_event.set()
        pipeline.close()
        logger.info(f"[WebSocket] Session cleaned up gracefully for {client_addr}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
