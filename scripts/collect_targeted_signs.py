"""
scripts/collect_targeted_signs.py
=============================================================================
Công cụ thu thập dữ liệu chuyên dụng đa góc nhìn cho các ký hiệu khó (ă, â, o, s, v.v.)
nhằm giải quyết triệt để hiện tượng tự che khuất trục sâu (axial occlusion / foreshortening)
khi giơ tay thẳng đối diện webcam.
=============================================================================
Cách sử dụng:
  .\\.venv\\Scripts\\python.exe scripts/collect_targeted_signs.py --signer user1 --symbols aw,aa,o,s
=============================================================================
"""
import argparse
import csv
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import cv2
import mediapipe as mp
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_core import foreshortening_ratio  # noqa: E402
from src.inference.level1_segmenter import aspect_points  # noqa: E402

SYMBOL_MAP = {
    "a": "a", "aw": "ă", "aa": "â", "b": "b", "c": "c", "d": "d", "dd": "đ",
    "e": "e", "ee": "ê", "g": "g", "h": "h", "i": "i", "k": "k", "l": "l",
    "m": "m", "n": "n", "o": "o", "oo": "ô", "ow": "ơ", "p": "p", "q": "q",
    "r": "r", "s": "s", "t": "t", "u": "u", "uw": "ư", "v": "v", "x": "x", "y": "y",
    "tone_s": "dấu sắc", "tone_f": "dấu huyền", "tone_r": "dấu hỏi", "tone_x": "dấu ngã", "tone_j": "dấu nặng",
    # Direct vietnamese names
    "ă": "ă", "â": "â", "đ": "đ", "ê": "ê", "ô": "ô", "ơ": "ơ", "ư": "ư",
}

ANGLE_PROMPTS = [
    ("straight", "1. GÓC THẲNG (Trực diện đối diện camera)"),
    ("tilted_down", "2. GÓC CHÚC XUỐNG (Nghiêng chúc đầu ngón tay ~20° - 30°)"),
    ("angled_side", "3. GÓC NGHIÊNG BÊN (Hơi xoay nghiêng lòng bàn tay 20° - 30°)"),
]

RECORD_FRAMES = 60  # ~2 seconds at 30 fps


def draw_hud(frame, text_lines, color=(0, 255, 0)):
    y = 30
    for line in text_lines:
        cv2.putText(frame, line, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1, cv2.LINE_AA)
        y += 28


def main():
    parser = argparse.ArgumentParser(description="Targeted Multi-Angle Sign Collector")
    parser.add_argument("--signer", default="user_live", help="Tên hoặc mã người ký (vd: user1)")
    parser.add_argument("--symbols", default="aw,aa,o,s", help="Danh sách ký hiệu cần thu thập (phân cách bằng dấu phẩy)")
    parser.add_argument("--reps-per-angle", type=int, default=2, help="Số lần lặp lại cho mỗi góc độ (mặc định 2)")
    parser.add_argument("--source", type=int, default=0, help="Webcam device index (mặc định 0)")
    parser.add_argument("--out-dir", default="data/collected_targeted", help="Thư mục lưu dữ liệu")
    args = parser.parse_args()

    symbols_raw = [s.strip() for s in args.symbols.split(",") if s.strip()]
    symbols = []
    for s in symbols_raw:
        canonical = SYMBOL_MAP.get(s, s)
        symbols.append((s, canonical))

    out_dir = os.path.abspath(args.out_dir)
    signer_dir = os.path.join(out_dir, args.signer)
    os.makedirs(signer_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, "manifest.csv")

    cap = cv2.VideoCapture(args.source, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"Lỗi: Không thể mở webcam {args.source}")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils

    print("\n" + "=" * 60)
    print(" BỘ THU THẬP DỮ LIỆU ĐA GÓC ĐỘ (TARGETED MULTI-ANGLE COLLECTOR)")
    print("=" * 60)
    print(f" Người ký  : {args.signer}")
    print(f" Ký hiệu   : {', '.join(canon for _, canon in symbols)}")
    print(f" Thư mục   : {signer_dir}")
    print(" Hướng dẫn : Bấm SPACE để bắt đầu ghi, 's' để bỏ qua, 'q' để thoát")
    print("=" * 60 + "\n")

    manifest_rows = []
    # Load existing manifest if present
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest_rows = list(csv.DictReader(f))

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.35,
        min_tracking_confidence=0.5
    ) as hands:

        for sym_code, sym_name in symbols:
            for angle_tag, angle_desc in ANGLE_PROMPTS:
                for rep in range(1, args.reps_per_angle + 1):
                    sample_id = f"{args.signer}_{sym_code}_{angle_tag}_rep{rep}"
                    npz_file = os.path.join(signer_dir, f"{sample_id}.npz")
                    mp4_file = os.path.join(signer_dir, f"{sample_id}.mp4")

                    # Wait for user trigger
                    triggered = False
                    skip = False
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break

                        h, w = frame.shape[:2]
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        res = hands.process(rgb)

                        ratio_str = "—"
                        angle_hint = "Chua thay tay"
                        has_hand = False
                        if res.multi_hand_landmarks:
                            has_hand = True
                            lm_list = [[p.x, p.y, p.z] for p in res.multi_hand_landmarks[0].landmark]
                            r = foreshortening_ratio(aspect_points(np.array(lm_list), w, h))
                            ratio_str = f"{r:.2f}"
                            if r < 0.35:
                                angle_hint = "Tay dang chuc/thang truc dien (Foreshortened)"
                            elif r < 0.70:
                                angle_hint = "Tay nghieng vua phai (~30 deg)"
                            else:
                                angle_hint = "Tay thang phang tren mat camera"
                            mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)

                        hud_lines = [
                            f"[KY HIEU]: {sym_name.upper()} ({sym_code}) | Mau {rep}/{args.reps_per_angle}",
                            f"[YEU CAU]: {angle_desc}",
                            f"[Goc tay]: Do dai chieu: {ratio_str} ({angle_hint})",
                            "[HUONG DAN]: Bam [SPACE] de dem nguoc ghi mau | [S] bo qua | [Q] thoat",
                        ]
                        draw_hud(frame, hud_lines, (0, 255, 255) if has_hand else (0, 0, 255))
                        cv2.imshow("Targeted Sign Collector", frame)

                        k = cv2.waitKey(1) & 0xFF
                        if k in (ord("q"), 27):
                            cap.release()
                            cv2.destroyAllWindows()
                            print("\nĐã kết thúc thu thập.")
                            return 0
                        elif k == ord("s"):
                            skip = True
                            break
                        elif k == ord(" "):
                            triggered = True
                            break

                    if skip or not triggered:
                        continue

                    # Countdown 2 seconds
                    t_start = time.time()
                    while time.time() - t_start < 2.0:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        rem = 2.0 - (time.time() - t_start)
                        hud_lines = [
                            f"CHUAN BI GIU TAY: {sym_name.upper()}",
                            f"{angle_desc}",
                            f"BAT DAU TRONG: {rem:.1f} giay...",
                        ]
                        draw_hud(frame, hud_lines, (0, 165, 255))
                        cv2.imshow("Targeted Sign Collector", frame)
                        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                            cap.release()
                            cv2.destroyAllWindows()
                            return 0

                    # Recording phase
                    recorded_lms = []
                    recorded_det = []
                    recorded_lab = []
                    recorded_score = []
                    recorded_frames = []

                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(mp4_file, fourcc, 30.0, (w, h))

                    for frame_idx in range(RECORD_FRAMES):
                        ret, frame = cap.read()
                        if not ret:
                            break

                        writer.write(frame)
                        recorded_frames.append(frame.copy())

                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        res = hands.process(rgb)

                        if res.multi_hand_landmarks:
                            recorded_lms.append([[p.x, p.y, p.z] for p in res.multi_hand_landmarks[0].landmark])
                            c = res.multi_handedness[0].classification[0]
                            recorded_det.append(True)
                            recorded_lab.append(c.label)
                            recorded_score.append(c.score)
                            mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp_hands.HAND_CONNECTIONS)
                        else:
                            recorded_lms.append([[0.0, 0.0, 0.0]] * 21)
                            recorded_det.append(False)
                            recorded_lab.append("")
                            recorded_score.append(0.0)

                        progress_pct = int((frame_idx + 1) / RECORD_FRAMES * 100)
                        hud_lines = [
                            f"[DANG GHI]: {sym_name.upper()} ({progress_pct}%)",
                            f"Giu yen tay theo goc: {angle_tag}",
                        ]
                        draw_hud(frame, hud_lines, (0, 0, 255))
                        cv2.imshow("Targeted Sign Collector", frame)
                        cv2.waitKey(1)

                    writer.release()

                    # Save NPZ
                    det_rate = float(np.mean(recorded_det)) if recorded_det else 0.0
                    meta = {
                        "sample_id": sample_id,
                        "symbol": sym_name,
                        "signer_id": args.signer,
                        "source": "collected_targeted",
                        "num_frames": len(recorded_lms),
                        "fps": 30.0,
                        "width": w,
                        "height": h,
                        "detection_rate": det_rate,
                        "mediapipe_version": mp.__version__,
                        "extractor": "mp.solutions.hands",
                        "angle_tag": angle_tag,
                    }

                    np.savez_compressed(
                        npz_file,
                        raw_landmarks=np.asarray(recorded_lms, dtype=np.float32),
                        detected_mask=np.asarray(recorded_det, dtype=bool),
                        handedness_label=np.asarray(recorded_lab),
                        handedness_score=np.asarray(recorded_score, dtype=np.float32),
                        metadata=json.dumps(meta),
                    )

                    # Update manifest
                    rel_npz = os.path.relpath(npz_file, out_dir).replace("\\", "/")
                    manifest_rows.append({
                        "sample_id": sample_id,
                        "symbol": sym_name,
                        "signer_id": args.signer,
                        "source": "collected_targeted",
                        "landmark_path": rel_npz,
                        "num_frames": len(recorded_lms),
                        "fps": 30.0,
                        "width": w,
                        "height": h,
                        "detection_rate": det_rate,
                        "mediapipe_version": mp.__version__,
                        "extractor": "mp.solutions.hands",
                    })

                    # Write manifest
                    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
                        fieldnames = ["sample_id", "symbol", "signer_id", "source", "landmark_path",
                                      "num_frames", "fps", "width", "height", "detection_rate",
                                      "mediapipe_version", "extractor"]
                        writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
                        writer_csv.writeheader()
                        writer_csv.writerows(manifest_rows)

                    print(f" -> [THÀNH CÔNG] Đã lưu mẫu {sample_id} (Detection rate: {det_rate*100:.1f}%)")

    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "=" * 60)
    print(f" HOÀN TẤT THU THẬP: Tổng cộng {len(manifest_rows)} mẫu trong {manifest_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
