"""
scripts/level1_gesture_diag.py
=============================================================================
Script chan doan cu chi khong nhan + khung xuong lech (Ke hoach 15 — Lan sua 13g)
Phan 1 (S1): Doc video, timestamp, cat/co 4:3, process-fps, duong ong app
             (session_factory tiem duoc), do khung xuong, quy tac R-S, khung JSON.
Phan 2 (S2): Ablation cu chi qua GestureEngine, quy tac R-G, --mode gate.
=============================================================================
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.hand_live import HandLandmarkSession  # noqa: E402
from src.inference.level1_core import (  # noqa: E402
    HandednessLock,
    LandmarkSmoother,
    enhance_low_light,
    is_flat_hand_backspace,
    is_open_palm_space,
    load_level1_config,
)
from src.inference.level1_gestures import (  # noqa: E402
    GestureEngine,
    load_gesture_config,
    palm_len,
)
from src.inference.level1_segmenter import Level1SignSegmenter, aspect_points  # noqa: E402

ADJUSTABLE_KEYS = {
    "space": ["space_hold_ms", "space_dropout_frames"],
    "backspace": [
        "wave_window_ms",
        "wave_min_amplitude",
        "wave_max_vertical_ratio",
        "wave_min_flat_fraction",
    ],
}

GRIDS = {
    "space_hold_ms": {
        "design": 600,
        "floor": 400,
        "values": [600, 550, 500, 450, 400],
        "direction": "larger_is_stricter",
    },
    "space_dropout_frames": {
        "design": 1,
        "floor": 3,
        "values": [1, 2, 3],
        "direction": "smaller_is_stricter",
    },
    "wave_window_ms": {
        "design": 1500,
        "floor": 2500,
        "values": [1500, 1750, 2000, 2250, 2500],
        "direction": "smaller_is_stricter",
    },
    "wave_min_amplitude": {
        "design": 0.6,
        "floor": 0.35,
        "values": [0.60, 0.55, 0.50, 0.45, 0.40, 0.35],
        "direction": "larger_is_stricter",
    },
    "wave_max_vertical_ratio": {
        "design": 0.5,
        "floor": 1.0,
        "values": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "direction": "smaller_is_stricter",
    },
    "wave_min_flat_fraction": {
        "design": 0.9,
        "floor": 0.6,
        "values": [0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60],
        "direction": "larger_is_stricter",
    },
}

# Hằng số quy tắc đặt trước theo Kế hoạch 15 — Lần sửa 13g §3.3
PRESET_RULES_13G: Dict[str, Any] = {
    "_note": "Đặt trước ở 15-lan-sua-13g §3.3, coder và orchestrator không đổi",
    "skeleton": {
        "rs1_formula": "p90(smooth) > p90(track) => fix_draw_raw = True",
        "rs2_formula": "p90(enh) > p90(track) => suggest_no_auto_enhance = True",
        "default": "Không cái nào => mediapipe_limit = True",
    },
    "gestures": {
        "pass_fraction": 0.8,  # >= 4/5 clip
        "grid": {
            "space_hold_ms": {"design": 600, "floor": 400, "step": 50, "direction": "larger_is_stricter"},
            "space_dropout_frames": {"design": 1, "floor": 3, "step": 1, "direction": "smaller_is_stricter"},
            "wave_window_ms": {"design": 1500, "floor": 2500, "step": 250, "direction": "smaller_is_stricter"},
            "wave_min_amplitude": {"design": 0.6, "floor": 0.35, "step": 0.05, "direction": "larger_is_stricter"},
            "wave_max_vertical_ratio": {"design": 0.5, "floor": 1.0, "step": 0.1, "direction": "smaller_is_stricter"},
            "wave_min_flat_fraction": {"design": 0.9, "floor": 0.6, "step": 0.05, "direction": "larger_is_stricter"},
        },
    },
}

TARGET_W = 640
TARGET_H = 480


# =============================================================================
# 1. TIEN XU LY HINH ANH & KHUNG HINH (AC-1)
# =============================================================================
def crop_and_resize(frame: np.ndarray, target_w: int = TARGET_W, target_h: int = TARGET_H) -> np.ndarray:
    """AC-1: Cắt giữa về tỉ lệ 4:3 rồi INTER_AREA về target_w x target_h (640x480).
    Ảnh đã 640x480 giữ nguyên từng pixel."""
    h, w = frame.shape[:2]
    if w == target_w and h == target_h:
        return frame

    target_aspect = 4.0 / 3.0
    current_aspect = float(w) / float(h)

    # Nếu chiều rộng quá lớn (vd: 16:9 1280x720) -> cắt giữa chiều ngang
    if current_aspect > target_aspect:
        crop_w = int(round(h * target_aspect))
        x0 = (w - crop_w) // 2
        cropped = frame[:, x0 : x0 + crop_w]
    # Nếu chiều cao quá lớn (vd: 480x640 dọc) -> cắt giữa chiều dọc
    elif current_aspect < target_aspect:
        crop_h = int(round(w / target_aspect))
        y0 = (h - crop_h) // 2
        cropped = frame[y0 : y0 + crop_h, :]
    else:
        cropped = frame

    if cropped.shape[1] == target_w and cropped.shape[0] == target_h:
        return cropped
    return cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)


# =============================================================================
# 2. XU LY TIMESTAMP & PROCESS-FPS (AC-2)
# =============================================================================
def resolve_timestamps(pos_msec_list: Sequence[float], fps: float) -> Tuple[List[float], str]:
    """AC-2: Xác định chuỗi timestamp từ POS_MSEC hoặc số thứ tự khung."""
    n = len(pos_msec_list)
    if n == 0:
        return [], "none"

    # Kiểm tra POS_MSEC có tăng chặt và > 0 từ khung 2 không
    strictly_increasing = True
    if n >= 2 and pos_msec_list[1] <= 0:
        strictly_increasing = False
    else:
        for i in range(1, n):
            if pos_msec_list[i] <= pos_msec_list[i - 1]:
                strictly_increasing = False
                break

    if strictly_increasing and (n == 1 or pos_msec_list[1] > 0):
        return [float(t) for t in pos_msec_list], "pos_msec"

    effective_fps = fps if fps > 0 else 30.0
    computed = [float(i * 1000.0 / effective_fps) for i in range(n)]
    return computed, "fps_index"


def filter_process_fps(
    frames: Sequence[np.ndarray], timestamps: Sequence[float], process_fps: Optional[float]
) -> Tuple[List[np.ndarray], List[float]]:
    """AC-2: Lọc khung theo --process-fps F (giữ khi ts >= ts_giữ_trước + 1000/F).
    Khung đầu luôn giữ."""
    if process_fps is None or process_fps <= 0 or len(frames) == 0:
        return list(frames), list(timestamps)

    interval_ms = 1000.0 / float(process_fps)
    kept_frames = [frames[0]]
    kept_ts = [timestamps[0]]
    last_kept_ts = timestamps[0]

    for i in range(1, len(frames)):
        t = timestamps[i]
        if t >= last_kept_ts + interval_ms:
            kept_frames.append(frames[i])
            kept_ts.append(t)
            last_kept_ts = t

    return kept_frames, kept_ts


# =============================================================================
# 3. DO KHUNG XUONG & QUY TAC R-S (AC-3, AC-4)
# =============================================================================
def dev(a: Optional[np.ndarray], b: Optional[np.ndarray], a_raw: Optional[np.ndarray]) -> Optional[float]:
    """AC-3: dev(a,b) = mean_j ‖a_j − b_j‖ / palm_len(a_raw) tren aspect_points (pixel 640x480)."""
    if a is None or b is None or a_raw is None:
        return None
    plen = palm_len(a_raw)
    if plen <= 1e-9:
        return None
    diff = np.asarray(a, dtype=np.float64)[:, :2] - np.asarray(b, dtype=np.float64)[:, :2]
    d_j = np.linalg.norm(diff, axis=1)
    return float(np.mean(d_j) / plen)


def compute_percentiles(values: Sequence[float]) -> Dict[str, Optional[float]]:
    """Tính p50, p90 theo numpy.percentile mặc định."""
    if not values:
        return {"p50": None, "p90": None, "count": 0}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "count": int(len(arr)),
    }


def evaluate_rs_rules(
    p90_smooth: Optional[float], p90_track: Optional[float], p90_enh: Optional[float]
) -> Dict[str, bool]:
    """AC-4: Bảng biên R-S1, R-S2:
    - R-S1: p90(smooth) > p90(track) + 1e-9 => fix_draw_raw = True
    - R-S2: p90(enh) > p90(track) + 1e-9 => suggest_no_auto_enhance = True
    - Không cái nào => mediapipe_limit = True
    """
    if p90_smooth is None or p90_track is None or p90_enh is None:
        return {"fix_draw_raw": False, "suggest_no_auto_enhance": False, "mediapipe_limit": True}

    fix_draw_raw = (p90_smooth - p90_track) > 1e-9
    suggest_no_auto_enhance = (p90_enh - p90_track) > 1e-9
    mediapipe_limit = not (fix_draw_raw or suggest_no_auto_enhance)

    return {
        "fix_draw_raw": fix_draw_raw,
        "suggest_no_auto_enhance": suggest_no_auto_enhance,
        "mediapipe_limit": mediapipe_limit,
    }


# =============================================================================
# 4. DUONG ONG XU LY CLIP (SESSION_FACTORY TIEM DUOC)
# =============================================================================
def read_clip_frames(clip_path: str) -> Tuple[List[np.ndarray], List[float], str]:
    """Doc toan bo khung va timestamp tu file video."""
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        raise RuntimeError(f"Khong the mo file video: {clip_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    raw_frames = []
    pos_msecs = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ts = cap.get(cv2.CAP_PROP_POS_MSEC)
        raw_frames.append(crop_and_resize(frame))
        pos_msecs.append(float(ts))

    cap.release()
    timestamps, ts_source = resolve_timestamps(pos_msecs, fps)
    return raw_frames, timestamps, ts_source


def run_pipeline_on_frames(
    frames: List[np.ndarray],
    timestamps: List[float],
    seg_values: Dict[str, Any],
    auto_enhance: bool = True,
    session_factory: Optional[Callable[..., Any]] = None,
    save_overlays: bool = False,
    overlay_out_dir: Optional[str] = None,
    clip_id: str = "clip",
) -> Dict[str, Any]:
    """Chạy đường ống phân tích khung xương và cử chỉ trên danh sách khung."""
    n_frames = len(frames)
    if n_frames == 0:
        return {
            "n_frames": 0,
            "skeleton": {"smooth": [], "track": [], "enh": []},
            "states": [],
            "landmarks_raw": [],
            "landmarks_smooth": [],
            "hand_rate": {"video": 0.0, "static": 0.0, "no_clahe": 0.0},
        }

    factory = session_factory if session_factory is not None else HandLandmarkSession

    # Ba phiên MediaPipe độc lập trên cùng khung:
    # 1. Phiên chính (app): video mode, conf 0.35
    session_app = factory(min_detection_confidence=0.35, static_image_mode=False)
    # 2. Phiên tham chiếu static: static_image_mode=True, conf 0.35
    session_static = factory(min_detection_confidence=0.35, static_image_mode=True)
    # 3. Phiên video không CLAHE: conf 0.35, static_image_mode=False
    session_no_clahe = factory(min_detection_confidence=0.35, static_image_mode=False)

    smoother = LandmarkSmoother()
    hand_lock = HandednessLock()
    segmenter = Level1SignSegmenter(seg_values, min_detected_frames=5)

    w, h = TARGET_W, TARGET_H

    dev_smooth_all: List[float] = []
    dev_track_all: List[float] = []
    dev_enh_all: List[float] = []

    dev_smooth_moving: List[float] = []
    dev_track_moving: List[float] = []
    dev_enh_moving: List[float] = []

    has_hand_app = 0
    has_hand_static = 0
    has_hand_no_clahe = 0

    frame_details = []
    frames_seq_smooth: List[Tuple[float, Optional[np.ndarray], int, int, bool]] = []
    frames_seq_raw: List[Tuple[float, Optional[np.ndarray], int, int, bool]] = []

    n_palm = 0
    n_flat = 0
    n_still_hand = 0

    for i in range(n_frames):
        frame = frames[i]
        ts = timestamps[i]

        # Đường CLAHE
        if auto_enhance:
            frame_enhanced, _ = enhance_low_light(frame)
        else:
            frame_enhanced = frame

        # 1. Phiên app
        lm_raw, handedness, _ = session_app.process(frame_enhanced)
        if lm_raw is not None:
            has_hand_app += 1
            handedness = hand_lock.update(handedness)
        lm_smooth = smoother.filter(ts, lm_raw)

        # 2. Phiên static (chạy trên frame CLAHE như app)
        lm_static, _, _ = session_static.process(frame_enhanced)
        if lm_static is not None:
            has_hand_static += 1

        # 3. Phiên không CLAHE (chạy trên frame gốc)
        lm_no_clahe, _, _ = session_no_clahe.process(frame)
        if lm_no_clahe is not None:
            has_hand_no_clahe += 1

        # Cập nhật segmenter
        segmenter.push(ts, lm_smooth, handedness, w, h)
        is_moving = segmenter.state == "moving"
        still = not is_moving

        # Lưu chuỗi cho GestureEngine
        frames_seq_smooth.append((ts, lm_smooth, w, h, still))
        frames_seq_raw.append((ts, lm_raw, w, h, still))

        # Tính độ lệch khung xương trên aspect_points
        pts_raw = aspect_points(lm_raw, w, h) if lm_raw is not None else None
        pts_smooth = aspect_points(lm_smooth, w, h) if lm_smooth is not None else None
        pts_static = aspect_points(lm_static, w, h) if lm_static is not None else None
        pts_no_clahe = aspect_points(lm_no_clahe, w, h) if lm_no_clahe is not None else None

        if pts_smooth is not None:
            if is_open_palm_space(pts_smooth):
                n_palm += 1
            if is_flat_hand_backspace(pts_smooth):
                n_flat += 1
            if still:
                n_still_hand += 1

        d_smooth = dev(pts_smooth, pts_raw, pts_raw)
        d_track = dev(pts_raw, pts_static, pts_raw)
        d_enh = dev(pts_raw, pts_no_clahe, pts_raw)

        if d_smooth is not None:
            dev_smooth_all.append(d_smooth)
            if is_moving:
                dev_smooth_moving.append(d_smooth)

        if d_track is not None:
            dev_track_all.append(d_track)
            if is_moving:
                dev_track_moving.append(d_track)

        if d_enh is not None:
            dev_enh_all.append(d_enh)
            if is_moving:
                dev_enh_moving.append(d_enh)

        frame_details.append({
            "idx": i,
            "ts": ts,
            "is_moving": is_moving,
            "d_smooth": d_smooth,
            "d_track": d_track,
            "d_enh": d_enh,
            "pts_raw": pts_raw,
            "pts_smooth": pts_smooth,
            "pts_static": pts_static,
            "frame": frame if save_overlays else None,
        })

    # Đóng các session nếu có method close
    for s in (session_app, session_static, session_no_clahe):
        if hasattr(s, "close"):
            s.close()

    # Lưu ảnh overlay nếu được yêu cầu (6 khung/clip: 3 smooth lớn nhất, 3 track lớn nhất)
    if save_overlays and overlay_out_dir:
        os.makedirs(overlay_out_dir, exist_ok=True)
        # 3 khung smooth lớn nhất
        valid_smooth = [f for f in frame_details if f["d_smooth"] is not None]
        valid_smooth.sort(key=lambda x: x["d_smooth"], reverse=True)
        top_smooth = valid_smooth[:3]

        # 3 khung track lớn nhất
        valid_track = [f for f in frame_details if f["d_track"] is not None]
        valid_track.sort(key=lambda x: x["d_track"], reverse=True)
        top_track = valid_track[:3]

        for rank, item in enumerate(top_smooth):
            _save_overlay_frame(item, overlay_out_dir, f"{clip_id}_smooth_top{rank+1}")
        for rank, item in enumerate(top_track):
            _save_overlay_frame(item, overlay_out_dir, f"{clip_id}_track_top{rank+1}")

    return {
        "n_frames": n_frames,
        "dev_smooth_all": dev_smooth_all,
        "dev_track_all": dev_track_all,
        "dev_enh_all": dev_enh_all,
        "dev_smooth_moving": dev_smooth_moving,
        "dev_track_moving": dev_track_moving,
        "dev_enh_moving": dev_enh_moving,
        "hand_rate": {
            "app_video": float(has_hand_app / n_frames),
            "static": float(has_hand_static / n_frames),
            "no_clahe": float(has_hand_no_clahe / n_frames),
        },
        "frames_seq_smooth": frames_seq_smooth,
        "frames_seq_raw": frames_seq_raw,
        "pose_rates_on_hand": {
            "palm": float(n_palm / has_hand_app) if has_hand_app > 0 else 0.0,
            "flat": float(n_flat / has_hand_app) if has_hand_app > 0 else 0.0,
            "still": float(n_still_hand / has_hand_app) if has_hand_app > 0 else 0.0,
        },
    }


def _save_overlay_frame(item: Dict[str, Any], out_dir: str, prefix: str) -> None:
    """Vẽ overlay: raw xanh lá, smoothed đỏ, static xanh dương."""
    frame = item.get("frame")
    if frame is None:
        return
    vis = frame.copy()
    pts_raw = item.get("pts_raw")
    pts_smooth = item.get("pts_smooth")
    pts_static = item.get("pts_static")

    if pts_raw is not None:
        for p in pts_raw:
            cv2.circle(vis, (int(round(p[0])), int(round(p[1]))), 3, (0, 255, 0), -1)
    if pts_smooth is not None:
        for p in pts_smooth:
            cv2.circle(vis, (int(round(p[0])), int(round(p[1]))), 3, (0, 0, 255), -1)
    if pts_static is not None:
        for p in pts_static:
            cv2.circle(vis, (int(round(p[0])), int(round(p[1]))), 3, (255, 0, 0), -1)

    cv2.imwrite(os.path.join(out_dir, f"{prefix}.jpg"), vis)


# =============================================================================
# 5. KHUNG METADATA & BUILD JSON (AC-8)
# =============================================================================
def git_commit_hash() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def is_git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--", "scripts/", "src/", "level1_demo.py"],
            stderr=subprocess.DEVNULL,
        )
        return len(out.strip()) > 0
    except Exception:
        return False


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_metadata(argv: Sequence[str]) -> Dict[str, Any]:
    return {
        "command": " ".join(argv),
        "commit": git_commit_hash(),
        "code_dirty": is_git_dirty(),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def find_clips(clips_dir: str) -> Dict[str, List[str]]:
    """Tìm tất cả clip mp4 trong space/, backspace/, spell/ sắp xếp theo tên."""
    categories = ["space", "backspace", "spell"]
    found: Dict[str, List[str]] = {cat: [] for cat in categories}
    if not os.path.isdir(clips_dir):
        return found

    for cat in categories:
        sub = os.path.join(clips_dir, cat)
        if os.path.isdir(sub):
            files = [
                os.path.join(sub, f)
                for f in sorted(os.listdir(sub))
                if f.lower().endswith(".mp4")
            ]
            found[cat] = files
    return found


# =============================================================================
# 6. ABLATION CU CHI & QUY TAC QUYET DINH R-G (AC-5, AC-6, AC-7)
# =============================================================================
def make_floor_values(design_values: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo bộ cấu hình floor (lỏng nhất cho phép theo §3.3)."""
    vals = dict(design_values)
    for k, info in GRIDS.items():
        vals[k] = info["floor"]
    return vals


def make_isolated_values(floor_values: Dict[str, Any], key: str, val: Any) -> Dict[str, Any]:
    """Tạo bộ cấu hình cô lập: khóa key mang giá trị val, các khóa khác ở floor."""
    vals = dict(floor_values)
    vals[key] = val
    return vals


def run_engine_on_sequence(
    values: Dict[str, Any],
    frames_seq: Sequence[Tuple[float, Optional[np.ndarray], int, int, bool]],
) -> Dict[str, Any]:
    """Chạy GestureEngine trên chuỗi khung đã tính trước."""
    engine = GestureEngine(values)
    emits_space = 0
    emits_backspace = 0
    max_strokes = 0
    for ts, lm, w, h, still in frames_seq:
        res = engine.step(ts, lm, w, h, still=still)
        if res["space"]:
            emits_space += 1
        if res["backspace"]:
            emits_backspace += 1
        if hasattr(engine, "wave") and hasattr(engine.wave, "strokes"):
            if engine.wave.strokes > max_strokes:
                max_strokes = engine.wave.strokes
    return {
        "space": emits_space,
        "backspace": emits_backspace,
        "max_strokes": max_strokes,
    }


def find_critical_value(
    clip_seq: Any,
    key: str,
    gesture_name: str,
    floor_values: Dict[str, Any],
    runner: Optional[Callable[..., Any]] = None,
) -> Optional[Any]:
    """Tìm giá trị tới hạn cô lập c_i(p): giá trị CHẶT nhất trên lưới mà clip còn phát."""
    grid_vals = GRIDS[key]["values"]  # Đã sắp xếp từ CHẶT nhất đến LỎNG nhất
    for v in grid_vals:
        test_values = make_isolated_values(floor_values, key, v)
        if runner is not None:
            emits = runner(test_values, clip_seq)
        else:
            emits = run_engine_on_sequence(test_values, clip_seq)
        if emits.get(gesture_name, 0) >= 1:
            return v  # Vì duyệt từ chặt đến lỏng nên giá trị đầu tiên phát là giá trị chặt nhất
    return None


def is_looser_or_equal(cand: Any, crit: Any, key: str) -> bool:
    """Kiểm tra cand có lỏng hơn hoặc bằng mốc tới hạn crit không."""
    if crit is None:
        return False
    direction = GRIDS[key]["direction"]
    if direction == "larger_is_stricter":
        return cand <= crit + 1e-9
    else:
        return cand >= crit - 1e-9


def pick_looser(key: str, v1: Any, v2: Any) -> Any:
    """Lấy giá trị LỎNG hơn giữa hai giá trị."""
    if v1 is None:
        return v2
    if v2 is None:
        return v1
    direction = GRIDS[key]["direction"]
    if direction == "larger_is_stricter":
        return min(v1, v2)
    else:
        return max(v1, v2)


def strictest_grid_satisfying(
    key: str, critical_values: Sequence[Any], fraction: float = 0.8
) -> Optional[Any]:
    """Tìm giá trị CHẶT nhất trên lưới thỏa mãn >= pass_fraction số clip."""
    total = len(critical_values)
    needed = int(np.ceil(total * fraction))
    grid_vals = GRIDS[key]["values"]  # Duyệt từ chặt nhất đến lỏng nhất
    for cand in grid_vals:
        count = sum(1 for c in critical_values if is_looser_or_equal(cand, c, key))
        if count >= needed:
            return cand
    return None


def evaluate_gesture_rules(
    clips_native: Dict[str, List[Any]],
    clips_pfps: Optional[Dict[str, List[Any]]],
    design_values: Dict[str, Any],
    runner: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Thực thi đầy đủ thuật toán nới ngưỡng R-G (G-0..G-3) theo §3.3."""
    floor_values = make_floor_values(design_values)
    gestures = ["space", "backspace"]

    decisions: Dict[str, Any] = {
        "stop_offline_ok": False,
        "stop_outside_config": False,
        "stop_combined": False,
        "tuned_values": {},
    }

    def _get_emits(values: Dict[str, Any], clip_seq: Any) -> Dict[str, int]:
        if runner is not None:
            return runner(values, clip_seq)
        return run_engine_on_sequence(values, clip_seq)

    # 1. Kiểm tra G-0: design phát ở >= 4/5 clip trên CẢ hai biến thể
    g0_results: Dict[str, bool] = {}
    for g in gestures:
        native_clips = clips_native.get(g, [])
        nat_count = sum(1 for c in native_clips if _get_emits(design_values, c).get(g, 0) >= 1)
        nat_ok = nat_count >= int(np.ceil(len(native_clips) * 0.8)) if native_clips else False

        pfps_ok = True
        if clips_pfps and clips_pfps.get(g):
            pfps_clips = clips_pfps[g]
            pfps_count = sum(1 for c in pfps_clips if _get_emits(design_values, c).get(g, 0) >= 1)
            pfps_ok = pfps_count >= int(np.ceil(len(pfps_clips) * 0.8))

        g0_results[g] = bool(nat_ok and pfps_ok)

    if any(g0_results.values()):
        decisions["stop_offline_ok"] = True
        return {"g0": g0_results, "decisions": decisions}

    # 2. Kiểm tra G-1: floor phát ở < 4/5 clip
    g1_results: Dict[str, bool] = {}
    for g in gestures:
        native_clips = clips_native.get(g, [])
        nat_count = sum(1 for c in native_clips if _get_emits(floor_values, c).get(g, 0) >= 1)
        nat_ok = nat_count >= int(np.ceil(len(native_clips) * 0.8)) if native_clips else False

        pfps_ok = True
        if clips_pfps and clips_pfps.get(g):
            pfps_clips = clips_pfps[g]
            pfps_count = sum(1 for c in pfps_clips if _get_emits(floor_values, c).get(g, 0) >= 1)
            pfps_ok = pfps_count >= int(np.ceil(len(pfps_clips) * 0.8))

        g1_results[g] = not (nat_ok and pfps_ok)

    if any(g1_results.values()):
        decisions["stop_outside_config"] = True
        return {"g0": g0_results, "g1": g1_results, "decisions": decisions}

    # 3. G-2: Tối ưu từng khóa cô lập
    g2_tuned: Dict[str, Any] = {}
    ablation_details: Dict[str, Any] = {}

    for g in gestures:
        keys = ADJUSTABLE_KEYS[g]
        native_clips = clips_native.get(g, [])
        pfps_clips = (clips_pfps.get(g, []) if clips_pfps else [])

        for p in keys:
            crits_nat = [find_critical_value(c, p, g, floor_values, runner) for c in native_clips]
            v_nat = strictest_grid_satisfying(p, crits_nat, 0.8)

            if pfps_clips:
                crits_pfps = [find_critical_value(c, p, g, floor_values, runner) for c in pfps_clips]
                v_pfps = strictest_grid_satisfying(p, crits_pfps, 0.8)
                v_final = pick_looser(p, v_nat, v_pfps)
            else:
                crits_pfps = []
                v_pfps = None
                v_final = v_nat

            g2_tuned[p] = v_final
            ablation_details[p] = {
                "crits_native": crits_nat,
                "crits_process_fps": crits_pfps,
                "v_native": v_nat,
                "v_process_fps": v_pfps,
                "v_final": v_final,
            }

    # 4. G-3: Chạy lại với bộ giá trị mới kết hợp trên D
    combined_values = dict(design_values)
    combined_values.update(g2_tuned)

    space_clips = clips_native.get("space", [])
    back_clips = clips_native.get("backspace", [])
    spell_clips = clips_native.get("spell", [])

    space_emits = [_get_emits(combined_values, c) for c in space_clips]
    back_emits = [_get_emits(combined_values, c) for c in back_clips]
    spell_emits = [_get_emits(combined_values, c) for c in spell_clips]

    # Điều kiện G-3:
    # - mỗi g phát >= 4/5
    space_pass = sum(1 for e in space_emits if e.get("space", 0) >= 1) >= int(np.ceil(len(space_clips) * 0.8))
    back_pass = sum(1 for e in back_emits if e.get("backspace", 0) >= 1) >= int(np.ceil(len(back_clips) * 0.8))

    # - 0 lần phát cử chỉ ngược
    space_inverse_0 = all(e.get("backspace", 0) == 0 for e in space_emits)
    back_inverse_0 = all(e.get("space", 0) == 0 for e in back_emits)

    # - 0 lần phát trên spell
    spell_clean = all(e.get("space", 0) == 0 and e.get("backspace", 0) == 0 for e in spell_emits)

    g3_ok = bool(space_pass and back_pass and space_inverse_0 and back_inverse_0 and spell_clean)

    if not g3_ok:
        decisions["stop_combined"] = True
    else:
        decisions["tuned_values"] = {
            k: v for k, v in combined_values.items() if v != design_values.get(k)
        }

    return {
        "g0": g0_results,
        "g1": g1_results,
        "g2_ablation": ablation_details,
        "g3_checks": {
            "space_pass": space_pass,
            "backspace_pass": back_pass,
            "space_inverse_zero": space_inverse_0,
            "backspace_inverse_zero": back_inverse_0,
            "spell_clean": spell_clean,
        },
        "decisions": decisions,
    }


def run_gate_mode(
    clips_by_cat: Dict[str, List[Any]],
    gesture_values: Dict[str, Any],
    runner: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """AC-7: Chế độ --mode gate kiểm tra GT1/GT2 trên tập kiểm thử T (fail-closed khi số clip != 12)."""
    space_clips = clips_by_cat.get("space", [])
    back_clips = clips_by_cat.get("backspace", [])

    if len(space_clips) != 12 or len(back_clips) != 12:
        return {
            "pass": False,
            "reason": f"Fail-closed: Số clip mỗi cử chỉ phải bằng 12 (thực tế: space={len(space_clips)}, backspace={len(back_clips)})",
            "gt1": {"valid": 0, "total": len(space_clips), "pass": False},
            "gt2": {"valid": 0, "total": len(back_clips), "pass": False},
        }

    def _get_emits(c: Any) -> Dict[str, int]:
        if runner is not None:
            return runner(gesture_values, c)
        return run_engine_on_sequence(gesture_values, c)

    # GT1: >= 10/12 clip space có >= 1 space và 0 backspace
    gt1_valid = 0
    for c in space_clips:
        e = _get_emits(c)
        if e.get("space", 0) >= 1 and e.get("backspace", 0) == 0:
            gt1_valid += 1

    # GT2: >= 10/12 clip backspace có >= 1 backspace và 0 space
    gt2_valid = 0
    for c in back_clips:
        e = _get_emits(c)
        if e.get("backspace", 0) >= 1 and e.get("space", 0) == 0:
            gt2_valid += 1

    gt1_pass = gt1_valid >= 10
    gt2_pass = gt2_valid >= 10
    pass_all = bool(gt1_pass and gt2_pass)

    return {
        "pass": pass_all,
        "gt1": {"valid": gt1_valid, "total": 12, "pass": gt1_pass},
        "gt2": {"valid": gt2_valid, "total": 12, "pass": gt2_pass},
        "reason": "OK" if pass_all else f"Chưa đạt ngưỡng (GT1: {gt1_valid}/12, GT2: {gt2_valid}/12)",
    }


def run_diag(
    clips_dir: str,
    seg_config_path: str = "configs/level1_demo_classifier_rev9.json",
    gesture_config_path: str = "configs/level1_gestures.json",
    process_fps: Optional[float] = None,
    auto_enhance: bool = True,
    overlay_dir: Optional[str] = "_work/l13g/overlay",
    session_factory: Optional[Callable[..., Any]] = None,
    argv: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Chạy chẩn đoán toàn bộ clip D/T và trả về cấu trúc JSON báo cáo."""
    seg_cfg = load_level1_config(seg_config_path)
    seg_values = seg_cfg["values"]
    gesture_cfg = load_gesture_config(gesture_config_path)

    clips_by_cat = find_clips(clips_dir)
    total_clips_count = sum(len(c) for c in clips_by_cat.values())

    all_smooth_moving: List[float] = []
    all_track_moving: List[float] = []
    all_enh_moving: List[float] = []

    per_clip_results: Dict[str, Any] = {}
    clips_seq_native: Dict[str, List[Any]] = {"space": [], "backspace": [], "spell": []}
    clips_seq_pfps: Dict[str, List[Any]] = {"space": [], "backspace": [], "spell": []}

    for cat, paths in clips_by_cat.items():
        per_clip_results[cat] = []
        for p in paths:
            clip_name = os.path.basename(p)
            clip_id = f"{cat}_{os.path.splitext(clip_name)[0]}"
            frames, timestamps, ts_source = read_clip_frames(p)

            # Biến thể native
            res_native = run_pipeline_on_frames(
                frames,
                timestamps,
                seg_values,
                auto_enhance=auto_enhance,
                session_factory=session_factory,
                save_overlays=True,
                overlay_out_dir=overlay_dir,
                clip_id=clip_id,
            )

            all_smooth_moving.extend(res_native["dev_smooth_moving"])
            all_track_moving.extend(res_native["dev_track_moving"])
            all_enh_moving.extend(res_native["dev_enh_moving"])

            clips_seq_native[cat].append(res_native["frames_seq_smooth"])

            clip_entry: Dict[str, Any] = {
                "file": clip_name,
                "n_frames": res_native["n_frames"],
                "ts_source": ts_source,
                "native": {
                    "hand_rate": res_native["hand_rate"],
                    "pose_rates_on_hand": res_native.get("pose_rates_on_hand"),
                    "smooth": compute_percentiles(res_native["dev_smooth_all"]),
                    "track": compute_percentiles(res_native["dev_track_all"]),
                    "enh": compute_percentiles(res_native["dev_enh_all"]),
                },
            }

            # Biến thể process-fps (nếu có yêu cầu)
            if process_fps is not None and process_fps > 0:
                filtered_frames, filtered_ts = filter_process_fps(frames, timestamps, process_fps)
                res_pfps = run_pipeline_on_frames(
                    filtered_frames,
                    filtered_ts,
                    seg_values,
                    auto_enhance=auto_enhance,
                    session_factory=session_factory,
                    save_overlays=False,
                )
                clips_seq_pfps[cat].append(res_pfps["frames_seq_smooth"])
                clip_entry["process_fps"] = {
                    "fps_target": float(process_fps),
                    "n_frames": res_pfps["n_frames"],
                    "hand_rate": res_pfps["hand_rate"],
                    "pose_rates_on_hand": res_pfps.get("pose_rates_on_hand"),
                    "smooth": compute_percentiles(res_pfps["dev_smooth_all"]),
                    "track": compute_percentiles(res_pfps["dev_track_all"]),
                    "enh": compute_percentiles(res_pfps["dev_enh_all"]),
                }

            per_clip_results[cat].append(clip_entry)

    # Thống kê tổng hợp khung xương trên khung moving
    skeleton_stats = {
        "moving_smooth": compute_percentiles(all_smooth_moving),
        "moving_track": compute_percentiles(all_track_moving),
        "moving_enh": compute_percentiles(all_enh_moving),
    }

    p90_s = skeleton_stats["moving_smooth"]["p90"]
    p90_t = skeleton_stats["moving_track"]["p90"]
    p90_e = skeleton_stats["moving_enh"]["p90"]

    rs_decisions = evaluate_rs_rules(p90_s, p90_t, p90_e)

    # Chạy ablation cử chỉ R-G (G-0..G-3)
    has_pfps = process_fps is not None and process_fps > 0
    rg_eval = evaluate_gesture_rules(
        clips_native=clips_seq_native,
        clips_pfps=clips_seq_pfps if has_pfps else None,
        design_values=gesture_cfg["values"],
    )

    combined_decisions = {**rs_decisions, **rg_eval["decisions"]}

    report = {
        "generated_by": build_metadata(argv if argv is not None else sys.argv),
        "configs": {
            "segmenter": {"path": seg_config_path, "sha256": sha256_file(seg_config_path)},
            "gestures": {"path": gesture_config_path, "sha256": sha256_file(gesture_config_path)},
        },
        "clips_dir": clips_dir,
        "total_clips": total_clips_count,
        "rules": PRESET_RULES_13G,
        "skeleton": skeleton_stats,
        "gesture_ablation": rg_eval,
        "decisions": combined_decisions,
        "per_clip": per_clip_results,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="VSLT Level 1 Gesture Diagnostic & Gate Runner")
    parser.add_argument("--clips-dir", default="data/collected_gestures/13g_D", help="Thu muc chua clip D/T")
    parser.add_argument("--process-fps", type=float, default=None, help="Mo phong app bo khung voi FPS muc tieu")
    parser.add_argument("--no-auto-enhance", action="store_true", default=False, help="Tat auto CLAHE")
    parser.add_argument("--gesture-config", default="configs/level1_gestures.json", help="File config cu chi")
    parser.add_argument("--segmenter-config", default="configs/level1_demo_classifier_rev9.json", help="File config rev9")
    parser.add_argument("--overlay-dir", default="_work/l13g/overlay", help="Thu muc luu anh overlay khung xuong")
    parser.add_argument("--out", default=None, help="Duong dan file JSON ket qua")
    parser.add_argument("--mode", default="diag", choices=["diag", "gate"], help="Che do chay: diag (D) hoac gate (T)")
    args = parser.parse_args()

    if args.mode == "gate":
        # Mode gate cho tập kiểm thử T
        gesture_cfg = load_gesture_config(args.gesture_config)
        clips_by_cat = find_clips(args.clips_dir)
        seg_cfg = load_level1_config(args.segmenter_config)

        # Chạy pipeline để lấy chuỗi smoothed frames cho mỗi clip
        clips_seq: Dict[str, List[Any]] = {"space": [], "backspace": []}
        for cat in ("space", "backspace"):
            for p in clips_by_cat.get(cat, []):
                frames, timestamps, _ = read_clip_frames(p)
                if args.process_fps is not None and args.process_fps > 0:
                    frames, timestamps = filter_process_fps(frames, timestamps, args.process_fps)
                res = run_pipeline_on_frames(
                    frames, timestamps, seg_cfg["values"], auto_enhance=not args.no_auto_enhance
                )
                clips_seq[cat].append(res["frames_seq_smooth"])

        gate_res = run_gate_mode(clips_seq, gesture_cfg["values"])
        report = {
            "generated_by": build_metadata(sys.argv),
            "mode": "gate",
            "clips_dir": args.clips_dir,
            "gesture_config": {"path": args.gesture_config, "sha256": sha256_file(args.gesture_config)},
            "gate_result": gate_res,
        }
    else:
        report = run_diag(
            clips_dir=args.clips_dir,
            seg_config_path=args.segmenter_config,
            gesture_config_path=args.gesture_config,
            process_fps=args.process_fps,
            auto_enhance=not args.no_auto_enhance,
            overlay_dir=args.overlay_dir,
            argv=sys.argv,
        )

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"-> [DA LUU] Báo cáo JSON: {args.out}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())


