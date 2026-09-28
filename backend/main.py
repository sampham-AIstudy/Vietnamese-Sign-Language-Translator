"""
FastAPI Backend for Real-Time Vietnamese Sign Language Recognition (Phase 12).
Provides:
- GET /health: System health and hardware telemetry
- GET /model/info: Active VSL deep learning model specifications and vocabulary
- WebSocket /ws/live-stream: Low-latency live video streaming & sign language recognition
- POST /api/fingerspelling/sequence: Level 1 letters/tone marks from a hand-landmark sequence
  (POST /api/fingerspelling with an image returns 409)
- POST /api/fingerspelling/compose: Level 1 accepted tokens (letters, tone marks, spaces) -> Vietnamese text
- GET /api/fingerspelling/status: Level 1 model availability, preprocessing and training-data provenance
  (`trained_on` is null or only {"source", "n_signers"}; signer names are never returned)

Level 2 ("Ký từ") model and live path (plan 04):
- The default model is unchanged: VSL_MODEL_TYPE unset -> "stgcn" = checkpoints/stgcn_tier2_indomain.pt, served by
  the legacy live path (60-frame sliding window + smoother).
- Candidate H-keepz-360 (opt-in, for the GATE only):  VSL_MODEL_TYPE=stgcn_h360
  -> reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt (gitignored; archived in the private Kaggle
  dataset phmvnsm33/vslt-step4-artifacts). Its sha256 is checked before loading; a mismatch makes the model
  unavailable (/api/health 503, WebSocket error model_unavailable + close 1011), never a silent fallback.
- VSL_STGCN_CKPT=<path> overrides the checkpoint (no sha256 check, is_default_model=false).
- The live path is chosen by the checkpoint itself (src/inference/harmonized_live.live_pipeline_for):
  preprocessing.features == "harmonized_v1" -> harmonized path (frame resized to the checkpoint's process_height
  before MediaPipe, CleanHolisticExtractor, one whole sign collected by SignSegmenter, harmonize() with the
  checkpoint's preprocessing, top-5 in a `sign_result` message); no `features` -> legacy path.
- /ws/live-stream protocol_version 2: `session_info` first; limits WS_MAX_MESSAGE_BYTES / WS_MAX_FRAME_SIDE.
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
import io
import json
import math
import base64
import binascii
import asyncio
import collections
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Dict, Any, Optional, List, Tuple, Union

import cv2
import numpy as np
import torch
from pydantic import BaseModel, Field
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from src.inference.harmonized_live import (  # noqa: E402
    PIPELINE_HARMONIZED, PIPELINE_LEGACY, HarmonizedLiveSession, live_pipeline_for)
from src.inference.sign_segmenter import SEGMENTER_DEFAULT  # noqa: E402
from fastapi.staticfiles import StaticFiles
from fastapi import Query, UploadFile, File

# Global predictor singleton
GLOBAL_PREDICTOR: Optional[VSLPredictor] = None
DEFAULT_MODEL_TYPE = "stgcn"
MODEL_TYPE = os.getenv("VSL_MODEL_TYPE", DEFAULT_MODEL_TYPE)
# Level 2 ST-GCN variants selectable with VSL_MODEL_TYPE (other values go to VSLPredictor unchanged).
#   stgcn          default backend model (tier2, 487 classes), legacy live path
#   stgcn_unified  unified 876-class model (reports/unified_run_2026-09-25, seed 42). Opt-in for the Việc 6
#                  experiments only: it did not pass the Việc 3 gate (0% on HCMUE, 0/31 cross-source clips).
#                  Classes come from the checkpoint's label_map.
#   stgcn_h360     candidate H-keepz-360 (4c decision B), harmonized_v1 live path. Opt-in for the GATE only;
#                  sha256 from reports/step4_2026-09-26/REPORT.md §1.4, checked before loading.
STGCN_VARIANTS = {
    "stgcn": {"ckpt": "checkpoints/stgcn_tier2_indomain.pt", "classes": "configs/tier2_classes.txt", "sha256": None},
    "stgcn_unified": {"ckpt": "checkpoints/stgcn_unified_best.pt", "classes": None, "sha256": None},
    "stgcn_h360": {"ckpt": "reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt", "classes": None,
                   "sha256": "648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e"},
}
_STGCN_VARIANT = STGCN_VARIANTS.get(MODEL_TYPE, STGCN_VARIANTS["stgcn"])
PREDICTOR_MODEL_TYPE = "stgcn" if MODEL_TYPE in STGCN_VARIANTS else MODEL_TYPE
STGCN_CKPT = os.getenv("VSL_STGCN_CKPT", _STGCN_VARIANT["ckpt"])
# An explicit VSL_STGCN_CKPT is not a known artifact: no sha256 to check, and never the default model.
STGCN_CKPT_SHA256 = None if "VSL_STGCN_CKPT" in os.environ else _STGCN_VARIANT.get("sha256")
CLASSES_PATH = os.getenv("VSL_CLASSES_PATH", _STGCN_VARIANT["classes"])
IS_DEFAULT_MODEL = (MODEL_TYPE == DEFAULT_MODEL_TYPE and "VSL_STGCN_CKPT" not in os.environ)
LOADED_CKPT_SHA256: Optional[str] = None


class ModelUnavailable(RuntimeError):
    """The configured Level 2 model cannot be served (missing file, sha256 mismatch, unusable preprocessing...)."""


def _sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _short(text: Any, limit: int = 200) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def get_or_load_predictor() -> VSLPredictor:
    """Loads and caches VSLPredictor singleton instance.
    Raises ModelUnavailable when the variant's sha256 does not match (checked BEFORE the file is unpickled) or the
    checkpoint's preprocessing cannot be served by any live path; nothing is cached then (no silent fallback)."""
    global GLOBAL_PREDICTOR, LOADED_CKPT_SHA256
    if GLOBAL_PREDICTOR is None:
        sha = _sha256_file(STGCN_CKPT) if STGCN_CKPT and os.path.isfile(STGCN_CKPT) else None
        if STGCN_CKPT_SHA256 is not None and sha != STGCN_CKPT_SHA256:
            raise ModelUnavailable(
                f"checkpoint {os.path.basename(STGCN_CKPT)} for {MODEL_TYPE}: "
                + ("file not found" if sha is None else f"sha256 {sha[:12]}... != expected {STGCN_CKPT_SHA256[:12]}..."))
        logger.info(f"[FastAPI] Initializing VSLPredictor (model_type='{MODEL_TYPE}', ckpt='{STGCN_CKPT}', classes='{CLASSES_PATH}')...")
        predictor = VSLPredictor(
            model_type=PREDICTOR_MODEL_TYPE,
            stgcn_ckpt=STGCN_CKPT,
            classes_path=CLASSES_PATH,
            warmup=True,
        )
        try:
            pipeline = live_pipeline_for(getattr(predictor, "preprocessing", None))
        except ValueError as e:
            raise ModelUnavailable(f"checkpoint preprocessing not usable: {e}") from e
        GLOBAL_PREDICTOR, LOADED_CKPT_SHA256 = predictor, sha
        logger.info(f"[FastAPI] Predictor loaded successfully. Vocabulary: {GLOBAL_PREDICTOR.num_classes} classes. "
                    f"Live pipeline: {pipeline}.")
    return GLOBAL_PREDICTOR


def _active_model():
    """(predictor, live pipeline name) of the configured Level 2 model, or ModelUnavailable (any load failure)."""
    try:
        predictor = get_or_load_predictor()
        pipeline = live_pipeline_for(getattr(predictor, "preprocessing", None))
    except ModelUnavailable:
        raise
    except Exception as e:  # missing file, bad checkpoint, invalid preprocessing ...
        raise ModelUnavailable(f"{type(e).__name__}: {e}") from e
    return predictor, pipeline


def _model_fields(predictor, pipeline: str) -> Dict[str, Any]:
    """Fields added to /api/health and /model/info (plan 04 §3.2)."""
    pre = getattr(predictor, "preprocessing", None) or {}
    harmonized = pipeline == PIPELINE_HARMONIZED
    return {
        "pipeline": pipeline,
        "checkpoint": os.path.basename(STGCN_CKPT) if STGCN_CKPT else None,
        "checkpoint_sha256": LOADED_CKPT_SHA256,
        "is_default_model": IS_DEFAULT_MODEL,
        "target_sequence_length": int(pre["target_len"]) if harmonized else 60,
        "process_height": pre.get("process_height") if harmonized else None,
    }


def _model_unavailable_response(err: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"status": "model_unavailable", "detail": _short(err)})


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

# -------------------------------------------------------------
# Level 1 request limits (plan 03 §3.2). Applied ONLY to the two Level 1 JSON endpoints; every other
# path (including the retired POST /api/fingerspelling, which always answers 409) is untouched.
# -------------------------------------------------------------
ALPHABET_MAX_BODY_BYTES = 1_048_576
ALPHABET_SEQUENCE_ENDPOINT = "/api/fingerspelling/sequence"
ALPHABET_COMPOSE_ENDPOINT = "/api/fingerspelling/compose"
BODY_LIMITED_PATHS = frozenset({ALPHABET_SEQUENCE_ENDPOINT, ALPHABET_COMPOSE_ENDPOINT})


def _is_body_limited(path: str) -> bool:
    return path.rstrip("/") in BODY_LIMITED_PATHS


class PathBodyLimitMiddleware:
    """Pure ASGI middleware. On the limited paths it answers 413 BEFORE any JSON parsing when the body
    is larger than `max_bytes`: from Content-Length when the client declares it, otherwise while
    reading a chunked body. An accepted body (<= max_bytes) is buffered and replayed to the app."""

    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def _reject(self, scope, receive, send):
        response = JSONResponse(status_code=413,
                                content={"detail": f"Request body larger than {self.max_bytes} bytes"})
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _is_body_limited(scope["path"]):
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
                if declared is not None and declared > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body, replayed = b"".join(chunks), False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request, exc: RequestValidationError):
    """On the Level 1 JSON endpoints, 422 bodies carry loc/msg/type only: echoing the rejected input
    could hold NaN/Infinity (not valid JSON -> would become a 500) or up to 1 MiB of payload.
    Every other path keeps FastAPI's default handler."""
    if _is_body_limited(request.url.path):
        errors = [{"loc": list(e.get("loc", ())), "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))}
                  for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})
    return await request_validation_exception_handler(request, exc)


# Registered before CORS so that CORS stays the outermost layer (413s keep their CORS headers).
app.add_middleware(PathBodyLimitMiddleware, max_bytes=ALPHABET_MAX_BODY_BYTES)

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
    """Returns system status, device hardware, and predictor readiness.
    503 {"status": "model_unavailable", "detail"} when the configured Level 2 model cannot be served."""
    try:
        predictor, pipeline = _active_model()
    except ModelUnavailable as e:
        return _model_unavailable_response(e)
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
        **_model_fields(predictor, pipeline),
    }


@app.get("/model/info")
def model_info():
    """Returns detailed architecture, vocabulary, and joint schema of the loaded model (503 when unavailable)."""
    try:
        predictor, pipeline = _active_model()
    except ModelUnavailable as e:
        return _model_unavailable_response(e)
    return {
        "model_type": predictor.model_type,
        "device": str(predictor.device),
        "num_classes": predictor.num_classes,
        "classes": predictor.class_names,
        **_model_fields(predictor, pipeline),
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
    """Returns the list of all active vocabulary classes (487 classes for Tier 2).
    503 {"status": "model_unavailable", "detail"} when the configured Level 2 model cannot be served."""
    try:
        predictor, _ = _active_model()
    except ModelUnavailable as e:
        return _model_unavailable_response(e)
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
# The server is stateless: it classifies ONE sign per request (/sequence) and composes a list of
# accepted tokens into text (/compose). Body size limit: PathBodyLimitMiddleware above.
from src.inference.fingerspelling_compose import TONE_STYLE, compose, short_repr, token_kind  # noqa: E402

ALPHABET_CKPT = os.getenv("VSL_ALPHABET_CKPT", "checkpoints/alphabet_best.pt")
ALPHABET_MAX_FRAMES = 300
ALPHABET_MAX_FRAME_SIDE = 8192
ALPHABET_MAX_ABS_COORD = 10.0  # bound on every raw landmark coordinate (plan 03 Lần sửa 2, AC12)
COMPOSE_MAX_TOKENS = 200
# Only facts recorded in docs/data_registry.md §1b; any other / missing source -> {"status": "unknown"}.
ALPHABET_DATA_PROVENANCE = {
    "hauuto": {"licence": "unknown", "usage": "internal only", "registry": "docs/data_registry.md#1b"},
}
ALPHABET_EVALUATION_REPORT = "reports/alphabet_nested_2026-09-25/REPORT.md"
_alphabet_model = None
_alphabet_meta: Optional[Dict[str, Any]] = None
_alphabet_lock = threading.Lock()


def get_or_load_alphabet_model():
    """Lazily loads the Level 1 model. Returns (model, meta) or (None, None).
    The checkpoint must carry `classes` and `preprocessing`; without them the train/live
    input cannot be guaranteed identical, so it is refused.
    Double-checked lock: concurrent first requests run torch.load once. A failed load is not
    cached (the next call tries again)."""
    global _alphabet_model, _alphabet_meta
    if _alphabet_model is not None:
        return _alphabet_model, _alphabet_meta
    with _alphabet_lock:
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
            # meta first: a lock-free reader that sees the model must also see its meta
            _alphabet_meta = {"classes": classes, "preprocessing": preprocessing, "model_type": model_type,
                              "checkpoint": os.path.basename(ALPHABET_CKPT),
                              "trained_on": ckpt.get("trained_on")}
            _alphabet_model = model
            logger.info("Loaded Level 1 alphabet model (%s, %d classes) from %s",
                        model_type, len(classes), ALPHABET_CKPT)
        except Exception as e:
            logger.error("Failed to load alphabet model %s: %s", ALPHABET_CKPT, e)
            return None, None
        return _alphabet_model, _alphabet_meta


def alphabet_data_provenance(trained_on: Any) -> Dict[str, Any]:
    """Licence/usage of the training data, looked up by trained_on.source in ALPHABET_DATA_PROVENANCE."""
    source = trained_on.get("source") if isinstance(trained_on, dict) else None
    if isinstance(source, str) and source in ALPHABET_DATA_PROVENANCE:
        return dict(ALPHABET_DATA_PROVENANCE[source])
    return {"status": "unknown"}


def public_trained_on(trained_on: Any) -> Optional[Dict[str, Any]]:
    """Public view of a checkpoint's `trained_on`: only the data source and the number of distinct signers.

    Never copies any other key (signer names, clip counts, ...). Returns None when nothing public is left."""
    if not isinstance(trained_on, dict):
        return None
    out: Dict[str, Any] = {}
    source = trained_on.get("source")
    if isinstance(source, str):
        out["source"] = source
    signers = trained_on.get("signers")
    if isinstance(signers, (list, tuple)) and all(isinstance(x, str) for x in signers):
        out["n_signers"] = len(set(signers))
    return out or None


def class_kind(name: str) -> Optional[str]:
    """'letter' | 'tone' for a Level 1 class name; None for a class outside the Level 1 vocabulary."""
    try:
        return token_kind(name)
    except ValueError:
        return None


_Point = Annotated[List[float], Field(max_length=3)]
_Frame = Annotated[List[_Point], Field(max_length=21)]


class FingerspellingSequenceRequest(BaseModel):
    """One sign as MediaPipe Hands output, one entry per video frame.
    landmarks[t]: 21 x [x, y, z] in MediaPipe image coordinates, or null/[] when no hand.
    handedness[t]: 'Left' / 'Right' / '' (MediaPipe label); required when the model mirrors left hands.
    timestamps_ms[t]: capture time; required when the model resamples by time.
    source_mirrored: true if MediaPipe ran on selfie-mirrored frames (the server un-mirrors)."""
    landmarks: List[Optional[_Frame]] = Field(max_length=ALPHABET_MAX_FRAMES)
    handedness: Optional[List[str]] = Field(None, max_length=ALPHABET_MAX_FRAMES)
    timestamps_ms: Optional[List[float]] = Field(None, max_length=ALPHABET_MAX_FRAMES)
    frame_width: int = Field(ge=1, le=ALPHABET_MAX_FRAME_SIDE)
    frame_height: int = Field(ge=1, le=ALPHABET_MAX_FRAME_SIDE)
    source_mirrored: bool = False
    top_k: int = Field(3, ge=1, le=10)


class FingerspellingComposeRequest(BaseModel):
    """Accepted Level 1 tokens in signing order: class names (letters, 'dấu …') and ' ' between words."""
    tokens: List[str] = Field(max_length=COMPOSE_MAX_TOKENS)


def validate_hand_frame(frame, t: int) -> np.ndarray:
    """One frame that claims a hand -> float32 [21, 3] (the backend's exact parsing).
    Raises ValueError (client message naming frame t) unless it is 21 x [x, y, z] finite numbers with
    |v| <= ALPHABET_MAX_ABS_COORD (MediaPipe image coordinates lie around [0, 1]; the bound also keeps
    x * aspect far from float32 overflow) and the 21 points are not all identical (never a MediaPipe
    output; a frame without a hand is sent as null / [])."""
    bad_frame = f"landmarks[{t}] must be 21 x [x, y, z] finite numbers or null"
    if len(frame) != 21 or any(len(p) != 3 for p in frame):
        raise ValueError(bad_frame)
    with np.errstate(over="ignore"):  # |v| > float32 max becomes inf and is rejected below
        arr = np.asarray(frame, dtype=np.float32)
    if not np.isfinite(arr).all():
        raise ValueError(bad_frame)
    if float(np.abs(arr).max()) > ALPHABET_MAX_ABS_COORD:
        raise ValueError(f"landmarks[{t}]: coordinates must satisfy |x|, |y|, |z| <= {ALPHABET_MAX_ABS_COORD} "
                         "(MediaPipe image coordinates)")
    if (arr == arr[0]).all():
        raise ValueError(f"landmarks[{t}]: all 21 points are identical, which is not a hand; "
                         "send null (or []) for a frame without a hand")
    return arr


def parse_fingerspelling_sequence(req: FingerspellingSequenceRequest, preprocessing: Dict[str, Any]):
    """Validates the request -> (raw [T,21,3], detected [T], handedness [T], timestamps or None).
    Raises ValueError with a client-facing message (client input quoted with short_repr only)."""
    T = len(req.landmarks)
    if not 1 <= T <= ALPHABET_MAX_FRAMES:
        raise ValueError(f"landmarks must have 1..{ALPHABET_MAX_FRAMES} frames, got {T}")
    if not (1 <= req.frame_width <= ALPHABET_MAX_FRAME_SIDE and 1 <= req.frame_height <= ALPHABET_MAX_FRAME_SIDE):
        raise ValueError(f"frame_width and frame_height must be in 1..{ALPHABET_MAX_FRAME_SIDE}")
    if not 1 <= req.top_k <= 10:
        raise ValueError("top_k must be in 1..10")
    raw = np.zeros((T, 21, 3), dtype=np.float32)
    detected = np.zeros(T, dtype=bool)
    for t, frame in enumerate(req.landmarks):
        if not frame:
            continue
        raw[t], detected[t] = validate_hand_frame(frame, t), True

    if req.handedness is None:
        if preprocessing.get("mirror_left_hand", True):
            raise ValueError("handedness is required by this model (left hands are mirrored)")
        hand = np.array([""] * T)
    else:
        if len(req.handedness) != T:
            raise ValueError(f"handedness must have {T} entries, got {len(req.handedness)}")
        bad = sorted({h for h in req.handedness if h not in ("Left", "Right", "")})
        if bad:
            raise ValueError("handedness values must be 'Left', 'Right' or '', got "
                             + ", ".join(short_repr(h) for h in bad[:5]))
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
    """Returns availability status of Level 1 Fingerspelling model, with the provenance of its
    training data (`trained_on` = public_trained_on(checkpoint trained_on): null or only {"source", "n_signers"},
    never signer names; licence/usage from docs/data_registry.md)."""
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
            "compose_endpoint": ALPHABET_COMPOSE_ENDPOINT,
            "input": "landmark_sequence",
            "trained_on": public_trained_on(meta["trained_on"]),
            "data_provenance": alphabet_data_provenance(meta["trained_on"]),
            "evaluation_report": ALPHABET_EVALUATION_REPORT,
            "message": "Mô hình Cấp 1 đã sẵn sàng",
        }
    return {
        "available": False,
        "model": None,
        "endpoint": ALPHABET_SEQUENCE_ENDPOINT,
        "compose_endpoint": ALPHABET_COMPOSE_ENDPOINT,
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
    if not np.isfinite(feats).all():  # input-derived features: the client's landmarks are at fault
        raise HTTPException(status_code=422, detail="landmarks give non-finite model features")

    classes = meta["classes"]
    with torch.no_grad():
        probs = torch.softmax(model(torch.from_numpy(feats).unsqueeze(0)), dim=-1)[0]
    if not bool(torch.isfinite(probs).all()):  # finite features, non-finite output: the model is at fault
        logger.error("Level 1 model %s returned non-finite probabilities for finite features", ALPHABET_CKPT)
        raise HTTPException(status_code=503,
                            detail="Đầu ra mô hình Cấp 1 không hợp lệ (xác suất không hữu hạn) / "
                                   "Level 1 model output is invalid (non-finite probabilities)")
    topk = torch.topk(probs, k=min(req.top_k, len(classes)))
    candidates = [{"class": classes[i], "confidence": round(v, 4), "kind": class_kind(classes[i])}
                  for v, i in zip(topk.values.tolist(), topk.indices.tolist())]
    return {
        "prediction": candidates[0]["class"],
        "prediction_kind": candidates[0]["kind"],
        "confidence": candidates[0]["confidence"],
        "candidates": candidates,
        "frames": len(req.landmarks),
        "detected_frames": int(detected.sum()),
        "model_type": meta["model_type"],
        "checkpoint": meta["checkpoint"],
    }


@app.post(ALPHABET_COMPOSE_ENDPOINT)
def compose_fingerspelling(req: FingerspellingComposeRequest):
    """Composes accepted Level 1 tokens into Vietnamese text (tone mark placed on the right vowel).
    Stateless and needs no model; never changes or guesses tokens (src/inference/fingerspelling_compose.py)."""
    try:
        out = compose(req.tokens)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {**out, "tone_style": TONE_STYLE}


@app.post("/api/fingerspelling")
async def predict_fingerspelling():
    """Retired single-image endpoint: the Level 1 model classifies a landmark sequence
    (letters with motion and tone marks cannot be read from one frame).
    Takes no parameters, so the request body is never read or parsed."""
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


# -------------------------------------------------------------
# /ws/live-stream, protocol_version 2 (plan 04 §3.6). The limits below apply to BOTH live paths.
# -------------------------------------------------------------
WS_PROTOCOL_VERSION = 2
WS_MAX_MESSAGE_BYTES = 1_048_576      # UTF-8 bytes of a text message / length of a binary message
WS_MAX_FRAME_SIDE = 1920              # largest accepted image side (read from the header before decoding)
WS_CLOSE_MESSAGE_TOO_LARGE = 1009
WS_CLOSE_MODEL_UNAVAILABLE = 1011
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class WsError(Exception):
    """One rejected client message -> {"type": "error", "code", "detail"}; `fatal` also closes the session.
    `detail` never repeats client data."""

    def __init__(self, code: str, detail: str, fatal: bool = False):
        super().__init__(detail)
        self.code, self.detail, self.fatal = code, _short(detail), fatal


def _ws_error(code: str, detail: str, received_seq: Optional[int] = None) -> Dict[str, Any]:
    return {"type": "error", "code": code, "detail": _short(detail), "received_seq": received_seq}


def _finite_number(v: Any) -> Optional[float]:
    """float(v) for a finite int/float that is not a bool, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        f = float(v)
    except (OverflowError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _parse_ws_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """ASGI `websocket.receive` message -> {"kind": "empty"} | {"kind": "control", "action": "reset"} |
    {"kind": "frame", "image": str|bytes, "timestamp": float|None, "threshold": float|None}.
    Raises WsError (message_too_large [fatal], bad_message, bad_config, bad_timestamp)."""
    text, data = message.get("text"), message.get("bytes")
    if data is not None:
        size = len(data)
    elif text is not None:
        size = len(text.encode("utf-8"))
    else:
        return {"kind": "empty"}
    if size > WS_MAX_MESSAGE_BYTES:
        raise WsError("message_too_large", f"message of {size} bytes exceeds {WS_MAX_MESSAGE_BYTES} bytes", fatal=True)
    if data is not None:
        if not data:
            return {"kind": "empty"}
        return {"kind": "frame", "image": bytes(data), "timestamp": None, "threshold": None}
    if not text.strip():
        return {"kind": "empty"}
    if not text.lstrip().startswith("{"):
        # bare base64 / data URL text (accepted since the first protocol version); no timestamp
        return {"kind": "frame", "image": text, "timestamp": None, "threshold": None}
    try:
        payload = json.loads(text)
    except (ValueError, RecursionError):
        raise WsError("bad_message", "message is not valid JSON")
    if not isinstance(payload, dict):
        raise WsError("bad_message", "JSON message must be an object")
    kind = payload.get("type", "frame")
    if kind == "control":
        if payload.get("action") == "reset":
            return {"kind": "control", "action": "reset"}
        raise WsError("bad_message", "unknown control action (supported: reset)")
    if kind != "frame":
        raise WsError("bad_message", "unknown message type (supported: frame, control)")
    image = payload.get("image")
    if not isinstance(image, str) or not image:
        raise WsError("bad_message", "frame message needs 'image' (base64 or data URL string)")
    threshold = None
    cfg = payload.get("config")
    if cfg is not None:
        if not isinstance(cfg, dict):
            raise WsError("bad_config", "config must be an object")
        if "confidence_threshold" in cfg:
            threshold = _finite_number(cfg["confidence_threshold"])
            if threshold is None or not 0.0 <= threshold <= 1.0:
                raise WsError("bad_config", "config.confidence_threshold must be a finite number in [0, 1]")
    ts = payload.get("timestamp")
    if ts is not None:
        ts = _finite_number(ts)
        if ts is None:
            raise WsError("bad_timestamp", "timestamp must be a finite number (milliseconds)")
    return {"kind": "frame", "image": image, "timestamp": ts, "threshold": threshold}


def _image_header(data: bytes) -> Tuple[str, int, int]:
    """(format, width, height) from the JPEG/PNG header only (PIL reads the header lazily; nothing is decoded).
    Raises WsError unsupported_format / frame_too_large / decode_failed."""
    if data.startswith(_JPEG_MAGIC):
        fmt = "JPEG"
    elif data.startswith(_PNG_MAGIC):
        fmt = "PNG"
    else:
        raise WsError("unsupported_format", "only JPEG and PNG frames are accepted")
    from PIL import Image
    try:
        with Image.open(io.BytesIO(data), formats=[fmt]) as im:
            width, height = im.size
    except Image.DecompressionBombError:
        raise WsError("frame_too_large", f"image header declares more pixels than allowed (max side {WS_MAX_FRAME_SIDE})")
    except Exception:
        raise WsError("decode_failed", f"cannot read the {fmt} header")
    return fmt, int(width), int(height)


def _decode_frame(raw_data: Any, min_height: Optional[int] = None) -> np.ndarray:
    """Base64 / data-URL text or binary bytes -> OpenCV BGR frame.
    Format (magic bytes) and size (header) are checked BEFORE cv2.imdecode: sides > WS_MAX_FRAME_SIDE ->
    frame_too_large; height < min_height (harmonized path: the checkpoint's process_height; frames are only ever
    shrunk to it, as in training) -> frame_too_small. Raises WsError."""
    if isinstance(raw_data, str):
        s = raw_data.strip()
        if s.startswith("data:"):
            _, sep, s = s.partition(",")
            if not sep:
                raise WsError("decode_failed", "data URL without a comma")
        try:
            data = base64.b64decode(s, validate=True)
        except (binascii.Error, ValueError):
            raise WsError("decode_failed", "image is not valid base64")
    elif isinstance(raw_data, (bytes, bytearray)):
        data = bytes(raw_data)
    else:
        raise WsError("bad_message", "image must be base64 text or a binary message")
    _, width, height = _image_header(data)
    if max(width, height) > WS_MAX_FRAME_SIDE:
        raise WsError("frame_too_large", f"frame {width}x{height} exceeds the max side {WS_MAX_FRAME_SIDE}")
    if min_height and height < min_height:
        raise WsError("frame_too_small", f"frame height {height} < {min_height} required by the model")
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None or frame.ndim != 3:
        raise WsError("decode_failed", "image could not be decoded")
    fh, fw = frame.shape[:2]
    if max(fw, fh) > WS_MAX_FRAME_SIDE:
        raise WsError("frame_too_large", f"frame {fw}x{fh} exceeds the max side {WS_MAX_FRAME_SIDE}")
    if min_height and fh < min_height:
        raise WsError("frame_too_small", f"frame height {fh} < {min_height} required by the model")
    return frame


def _process_frame_worker(
    raw_data: Any,
    client_ts: Optional[float],
    pipeline: RealtimePipeline,
    smoother: TemporalSmoother,
    frame_times: collections.deque,
    last_frame_ts: float,
    received_seq: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Legacy live path, executed in a ThreadPoolExecutor worker thread:
    - Decodes frame from bytes or base64 (header checked first; errors -> an `error` message)
    - Runs MediaPipe Holistic extraction (CPU-bound)
    - Updates temporal sliding buffer
    - Runs PyTorch inference (ST-GCN / Transformer)
    - Applies temporal anti-flicker smoothing
    - Packages response payload. Timings are measured (time.perf_counter); server_infer_ms is the model's own
      latency for a new prediction (0.0 otherwise).
    """
    t0 = time.perf_counter()

    # 1. Decode frame
    try:
        frame_bgr = _decode_frame(raw_data)
    except WsError as e:
        return _ws_error(e.code, e.detail, received_seq)
    t_decoded = time.perf_counter()

    # 2. Pipeline processing (MediaPipe Holistic CPU + Buffer + Inference)
    pipeline_out = pipeline.process_frame(frame_bgr)
    t_pipeline = time.perf_counter()

    # 3. Temporal smoothing with Motion Gating (Anti-Flicker & Voting)
    smoothed = smoother.update(
        pipeline_out["prediction"],
        hand_detected=pipeline_out["hand_detected"],
        is_moving=pipeline_out.get("is_moving", True),
    )

    # 4. Latency and FPS metrics
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    decode_ms = (t_decoded - t0) * 1000.0
    pipeline_ms = (t_pipeline - t_decoded) * 1000.0
    postprocess_ms = (t1 - t_pipeline) * 1000.0
    prediction = pipeline_out.get("prediction")
    infer_ms = 0.0
    if pipeline_out.get("is_new_prediction") and isinstance(prediction, dict):
        infer_ms = float(prediction.get("latency_ms", 0.0))
    preprocess_ms = max(0.0, pipeline_ms - infer_ms)

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
        "pipeline": PIPELINE_LEGACY,
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
            "decode_ms": round(decode_ms, 2),
            "server_preprocess_ms": round(preprocess_ms, 2),
            "server_infer_ms": round(infer_ms, 2),
            "postprocess_ms": round(postprocess_ms, 2),
            "server_total_ms": round(latency_ms, 2),
            "server_fps": round(fps, 1),
            "buffer_frames": pipeline_out["buffer_fill"],
        },
    }


def _new_harmonized_session(predictor) -> HarmonizedLiveSession:
    """One HarmonizedLiveSession per WebSocket client (own CleanHolisticExtractor / MediaPipe graph)."""
    return HarmonizedLiveSession(predictor, predictor.preprocessing)


def _round_ms(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(float(v), 3)


def _harmonized_event_message(ev: Dict[str, Any], frame_seq: int, trigger_client_ts: Optional[float]) -> Dict[str, Any]:
    """Session event -> `sign_result` / `sign_discarded` message (plan 04 §3.6)."""
    if ev["type"] == "sign_result":
        m = ev["metrics"]
        return {
            "type": "sign_result",
            "segment_id": ev["segment_id"],
            "frame_seq": frame_seq,
            "prediction": ev["prediction"],
            "gloss": ev["gloss"],
            "confidence": ev["confidence"],
            "top5": ev["top5"],
            "end_reason": ev["end_reason"],
            "segment": ev["segment"],
            "model": {"model_type": MODEL_TYPE, "checkpoint": os.path.basename(STGCN_CKPT) if STGCN_CKPT else None,
                      "is_default": IS_DEFAULT_MODEL, "pipeline": PIPELINE_HARMONIZED},
            "metrics": {"harmonize_ms": _round_ms(m["harmonize_ms"]), "infer_ms": _round_ms(m["infer_ms"]),
                        "finalize_ms": _round_ms(m["finalize_ms"]), "trigger_client_timestamp": trigger_client_ts,
                        "rest_hold_s": m["rest_hold_s"]},
        }
    return {"type": "sign_discarded", "segment_id": ev["segment_id"], "frame_seq": frame_seq,
            "reason": ev["reason"], "segment": {"duration_s": ev["segment"]["duration_s"],
                                                "frames": ev["segment"]["frames"]}}


def _process_frame_worker_harmonized(item: Dict[str, Any], session: HarmonizedLiveSession,
                                     stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """harmonized_v1 live path, executed in a worker thread: decode (header checked, height >= process_height)
    -> session.process -> [sign_result | sign_discarded] + frame_result, or [error].
    frame_result never carries a prediction; predictions only come in sign_result, sent BEFORE the frame_result of
    the frame that triggered it (same frame_seq)."""
    t0 = time.perf_counter()
    try:
        frame_bgr = _decode_frame(item["image"], min_height=session.process_height)
    except WsError as e:
        return [_ws_error(e.code, e.detail, item["received_seq"])]
    t1 = time.perf_counter()
    try:
        out = session.process(frame_bgr, item["t_s"], seq=item["received_seq"])
    except ValueError as e:
        return [_ws_error("bad_timestamp", f"frame time rejected: {e}", item["received_seq"])]
    stats["frame_seq"] += 1
    frame_seq = stats["frame_seq"]
    done = time.perf_counter()
    if stats["last_done"] is not None and done > stats["last_done"]:
        stats["rates"].append(1.0 / (done - stats["last_done"]))
    stats["last_done"] = done
    fps = float(np.mean(stats["rates"])) if stats["rates"] else 0.0

    messages: List[Dict[str, Any]] = []
    if out["event"] is not None:
        messages.append(_harmonized_event_message(out["event"], frame_seq, item["client_ts"]))
    state = out["state"]
    total_ms = (time.perf_counter() - t0) * 1000.0
    messages.append({
        "type": "frame_result",
        "pipeline": PIPELINE_HARMONIZED,
        "frame_seq": frame_seq,
        "received_seq": item["received_seq"],
        "dropped_frames": item.get("dropped_frames", 0),
        "prediction": None,
        "gloss": None,
        "confidence": None,
        "top5": [],
        "status": state.upper(),
        "segment": {"state": state, "segment_id": out["segment_id"] if state == "recording" else None,
                    "recording_s": out["recording_s"], "frames": out["n_frames"],
                    "max_sign_s": session.segmenter.params["max_sign_s"]},
        "is_signing": state == "recording",
        "hand_detected": out["hand_detected"],
        "hand_active": out["hand_active"],
        "landmarks": out["landmarks"],
        "latency_ms": round(total_ms, 2),
        "fps": round(fps, 1),
        "metrics": {
            "client_timestamp": item["client_ts"],
            "timestamp_source": item["timestamp_source"],
            "decode_ms": _round_ms((t1 - t0) * 1000.0),
            "extract_ms": _round_ms(out["extract_ms"]),
            "segment_ms": _round_ms(out["segment_ms"]),
            "server_total_ms": round(total_ms, 2),
            "server_fps": round(fps, 1),
        },
    })
    return messages


def _session_info(predictor, pipeline: str) -> Dict[str, Any]:
    pre = getattr(predictor, "preprocessing", None) or {}
    harmonized = pipeline == PIPELINE_HARMONIZED
    return {
        "type": "session_info",
        "protocol_version": WS_PROTOCOL_VERSION,
        "pipeline": pipeline,
        "model": {"model_type": MODEL_TYPE, "checkpoint": os.path.basename(STGCN_CKPT) if STGCN_CKPT else None,
                  "checkpoint_sha256": LOADED_CKPT_SHA256, "is_default": IS_DEFAULT_MODEL,
                  "num_classes": int(predictor.num_classes)},
        "preprocessing": ({k: pre[k] for k in ("target_len", "process_height", "trim", "hand_z", "rest_y",
                                               "active_speed", "pad_s", "max_gap_s")}
                          if harmonized else {"target_len": 60}),
        "segmenter": dict(SEGMENTER_DEFAULT) if harmonized else None,
        "limits": {"max_message_bytes": WS_MAX_MESSAGE_BYTES, "max_frame_side": WS_MAX_FRAME_SIDE,
                   "min_frame_height": pre.get("process_height") if harmonized else None},
    }


class _SessionClock:
    """Timestamp source of a harmonized session, fixed by the first accepted frame: "client" (its `timestamp`, ms,
    strictly increasing) or "server" (time.perf_counter at receive; perf_counter rather than time.monotonic because
    the latter ticks every ~16 ms on Windows). A frame from the other source, or a non-increasing client timestamp,
    raises WsError bad_timestamp and changes nothing."""

    def __init__(self):
        self.source: Optional[str] = None
        self.first: Optional[float] = None
        self.last: Optional[float] = None

    def stamp(self, client_ts_ms: Optional[float]) -> float:
        source = self.source or ("client" if client_ts_ms is not None else "server")
        if source == "client":
            if client_ts_ms is None:
                raise WsError("bad_timestamp", "this session uses client timestamps; the frame has none")
            if self.last is not None and not client_ts_ms > self.last:
                raise WsError("bad_timestamp", "timestamp must increase strictly")
            value, scale = client_ts_ms, 1000.0
        else:
            if client_ts_ms is not None:
                raise WsError("bad_timestamp", "this session uses server time; the frame carries a timestamp")
            value, scale = time.perf_counter(), 1.0
            if self.last is not None and value <= self.last:
                value = self.last + 1e-6
        self.source = source
        if self.first is None:
            self.first = value
        self.last = value
        return (value - self.first) / scale


@app.websocket("/ws/live-stream")
async def websocket_live_stream(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket endpoint for sign language video streaming (protocol_version 2).
    - First message: `session_info` (pipeline, model, preprocessing, segmenter, limits).
    - Receive Task: parses/validates each message (size, JSON, config, timestamp) and writes frames to a
      single-frame slot (latest-frame-only: a frame not yet taken by the worker is dropped and counted).
    - Worker Task: offloads decoding + MediaPipe + inference to the ThreadPoolExecutor.
      legacy path: one `frame_result` per frame (sliding window + smoother), unchanged prediction behaviour.
      harmonized_v1 path: `frame_result` per frame (no prediction) + `sign_result` / `sign_discarded` per sign.
    - Errors: `error{code}`; only message_too_large (close 1009) and model_unavailable (close 1011) end the session.
    """
    await websocket.accept()
    client_addr = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(f"[WebSocket] Client connected: {client_addr}")
    loop = asyncio.get_running_loop()

    # Model of this session (no silent fallback when it cannot be served)
    try:
        predictor, live_pipeline = _active_model()
        session = pipeline = smoother = None
        if live_pipeline == PIPELINE_HARMONIZED:
            session = await loop.run_in_executor(THREAD_POOL, _new_harmonized_session, predictor)
        else:
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
    except Exception as e:
        logger.error(f"[WebSocket] Model unavailable for {client_addr}: {e}")
        try:
            await websocket.send_json(_ws_error("model_unavailable", str(e)))
            await websocket.close(code=WS_CLOSE_MODEL_UNAVAILABLE)
        except Exception:
            pass
        return

    # Rolling FPS and Latency tracker (legacy) / harmonized worker stats
    frame_times = collections.deque(maxlen=30)
    last_frame_ts = time.time()
    stats = {"frame_seq": 0, "last_done": None, "rates": collections.deque(maxlen=30)}
    counters = {"received": 0, "dropped": 0}
    clock = _SessionClock()
    session_lock = threading.Lock()   # the worker thread and close() never use the MediaPipe graph together

    # Shared single slot for latest frame only (+ pending reset)
    latest_slot: Dict[str, Any] = {"item": None, "reset": False}
    frame_event = asyncio.Event()
    frame_lock = asyncio.Lock()
    send_lock = asyncio.Lock()
    closed_event = asyncio.Event()

    async def send(message: Dict[str, Any]):
        async with send_lock:
            if not closed_event.is_set():
                await websocket.send_json(message)

    def run_harmonized(item):
        with session_lock:
            return _process_frame_worker_harmonized(item, session, stats)

    def reset_harmonized():
        with session_lock:
            return session.reset()

    async def receive_loop():
        """Producer: receives, validates and slots frames without blocking."""
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
            if message.get("text") is None and message.get("bytes") is None:
                continue

            counters["received"] += 1
            seq = counters["received"]
            try:
                parsed = _parse_ws_message(message)
                if parsed["kind"] == "empty":
                    continue
                if parsed["kind"] == "control":
                    async with frame_lock:
                        latest_slot["reset"] = True
                        frame_event.set()
                    continue
                t_s = clock.stamp(parsed["timestamp"]) if session is not None else None
            except WsError as e:
                await send(_ws_error(e.code, e.detail, seq))
                if e.fatal:
                    async with send_lock:
                        closed_event.set()
                        frame_event.set()
                        await websocket.close(code=WS_CLOSE_MESSAGE_TOO_LARGE)
                    break
                continue

            if smoother is not None and parsed["threshold"] is not None:
                smoother.confidence_threshold = parsed["threshold"]
            item = {"image": parsed["image"], "client_ts": parsed["timestamp"], "t_s": t_s, "received_seq": seq,
                    "timestamp_source": clock.source}
            # Overwrite the slot with latest frame (drop any stale unhandled frame)
            async with frame_lock:
                if latest_slot["item"] is not None:
                    counters["dropped"] += 1
                latest_slot["item"] = item
                frame_event.set()

    async def worker_loop():
        """Consumer: processes the latest frame in the ThreadPoolExecutor and sends the JSON response(s)."""
        nonlocal last_frame_ts

        while not closed_event.is_set():
            await frame_event.wait()
            if closed_event.is_set():
                break

            # Atomically retrieve latest frame / pending reset and reset slot
            async with frame_lock:
                item, do_reset = latest_slot["item"], latest_slot["reset"]
                latest_slot["item"], latest_slot["reset"] = None, False
                dropped = counters["dropped"]
                frame_event.clear()

            try:
                if do_reset:
                    if session is not None:
                        ev = await loop.run_in_executor(THREAD_POOL, reset_harmonized)
                        if ev is not None:
                            await send(_harmonized_event_message(ev, stats["frame_seq"], None))
                    else:
                        pipeline.clear_buffer()
                        smoother.reset()
                if item is None:
                    continue
                if session is not None:
                    item["dropped_frames"] = dropped
                    responses = await loop.run_in_executor(THREAD_POOL, run_harmonized, item)
                else:
                    # Offload CPU MediaPipe + inference to ThreadPoolExecutor
                    responses = [await loop.run_in_executor(
                        THREAD_POOL,
                        _process_frame_worker,
                        item["image"],
                        item["client_ts"],
                        pipeline,
                        smoother,
                        frame_times,
                        last_frame_ts,
                        item["received_seq"],
                    )]
                    last_frame_ts = time.time()
                for response in responses:
                    await send(response)
            except (WebSocketDisconnect, RuntimeError):
                closed_event.set()
                break
            except Exception as e:
                logger.error(f"[WebSocket Worker] Error processing frame: {e}", exc_info=True)

    try:
        await send(_session_info(predictor, live_pipeline))
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
        if pipeline is not None:
            pipeline.close()
        if session is not None:
            def _close_session():
                with session_lock:
                    session.close()
            await loop.run_in_executor(THREAD_POOL, _close_session)
        logger.info(f"[WebSocket] Session cleaned up gracefully for {client_addr}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, ws_max_size=WS_MAX_MESSAGE_BYTES)
