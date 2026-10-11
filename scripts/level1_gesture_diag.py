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
    load_level1_config,
)
from src.inference.level1_gestures import (  # noqa: E402
    GestureEngine,
    load_gesture_config,
    palm_len,
)
from src.inference.level1_segmenter import Level1SignSegmenter, aspect_points  # noqa: E402

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

        # Tính độ lệch khung xương trên aspect_points
        pts_raw = aspect_points(lm_raw, w, h) if lm_raw is not None else None
        pts_smooth = aspect_points(lm_smooth, w, h) if lm_smooth is not None else None
        pts_static = aspect_points(lm_static, w, h) if lm_static is not None else None
        pts_no_clahe = aspect_points(lm_no_clahe, w, h) if lm_no_clahe is not None else None

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

            clip_entry: Dict[str, Any] = {
                "file": clip_name,
                "n_frames": res_native["n_frames"],
                "ts_source": ts_source,
                "native": {
                    "hand_rate": res_native["hand_rate"],
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
                clip_entry["process_fps"] = {
                    "fps_target": float(process_fps),
                    "n_frames": res_pfps["n_frames"],
                    "hand_rate": res_pfps["hand_rate"],
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
        "decisions": rs_decisions,
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

