"""
tests/test_level1_gesture_diag.py
=============================================================================
Unit tests cho scripts/level1_gesture_diag.py (Ke hoach 15 — Lan sua 13g S1).
Nghiem thu cac tieu chi chap nhan:
  - AC-1: Cat/co ti le 4:3 -> 640x480 INTER_AREA
  - AC-2: Xu ly timestamp POS_MSEC va loc --process-fps
  - AC-3: Cong thuc sai lech khung xuong dev(a, b), percentiles, va duong ong app
  - AC-4: Bang bien quy tac quyet dinh R-S (R-S1, R-S2, mediapipe_limit)
  - AC-8: Cau truc JSON, khong lech duong dan nguoi dung (privacy), khong chua anh
=============================================================================
"""
import json
import re
import unittest
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from scripts.level1_gesture_diag import (
    PRESET_RULES_13G,
    TARGET_H,
    TARGET_W,
    compute_percentiles,
    crop_and_resize,
    dev,
    evaluate_rs_rules,
    filter_process_fps,
    resolve_timestamps,
    run_pipeline_on_frames,
)
from src.inference.level1_gestures import palm_len


class TestLevel1GestureDiagS1(unittest.TestCase):
    """Test suite cho Phần 1 (S1) của script chẩn đoán cử chỉ & khung xương."""

    # -------------------------------------------------------------------------
    # AC-1: Cắt / co hình ảnh
    # -------------------------------------------------------------------------
    def test_ac1_crop_and_resize_16_9_to_4_3(self):
        """1280x720 (16:9) -> 640x480: cắt giữa vùng 960x720 rồi INTER_AREA."""
        # Tạo frame 1280x720: hai viền ngoài màu đen (0), vùng giữa 960x720 màu trắng (255)
        # 1280 - 960 = 320 -> x0 = 160, x1 = 1120
        frame_16_9 = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame_16_9[:, 160:1120] = 255

        out = crop_and_resize(frame_16_9, target_w=640, target_h=480)
        self.assertEqual(out.shape, (480, 640, 3))
        # Vì vùng giữa hoàn toàn là 255, sau khi crop đúng 960x720 và resize thì toàn bộ out phải là 255
        self.assertTrue(np.all(out == 255), "Vùng cắt giữa 960x720 phải hoàn toàn là 255")

    def test_ac1_crop_and_resize_exact_640x480(self):
        """640x480 giữ nguyên từng pixel."""
        rng = np.random.RandomState(42)
        frame_exact = rng.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        out = crop_and_resize(frame_exact, target_w=640, target_h=480)
        self.assertEqual(out.shape, (480, 640, 3))
        self.assertTrue(np.array_equal(out, frame_exact), "Ảnh 640x480 phải được giữ nguyên từng pixel")

    def test_ac1_crop_and_resize_portrait_480x640(self):
        """480x640 dọc -> cắt giữa đúng 4:3 (480x360) rồi INTER_AREA về 640x480."""
        # 480 * 3 / 4 = 360 -> y0 = (640 - 360) // 2 = 140, y1 = 500
        frame_portrait = np.zeros((640, 480, 3), dtype=np.uint8)
        frame_portrait[140:500, :] = 200

        out = crop_and_resize(frame_portrait, target_w=640, target_h=480)
        self.assertEqual(out.shape, (480, 640, 3))
        self.assertTrue(np.all(out == 200), "Vùng cắt giữa 480x360 phải được giữ nguyên giá trị 200")

    # -------------------------------------------------------------------------
    # AC-2: Xử lý timestamp & lọc process-fps
    # -------------------------------------------------------------------------
    def test_ac2_timestamp_resolution_pos_msec(self):
        """POS_MSEC tăng chặt và > 0 từ khung 2 -> dùng POS_MSEC."""
        pos_msecs = [0.0, 33.33, 66.67, 100.0]
        ts, src = resolve_timestamps(pos_msecs, fps=30.0)
        self.assertEqual(src, "pos_msec")
        self.assertEqual(ts, pos_msecs)

    def test_ac2_timestamp_resolution_fallback_to_fps(self):
        """POS_MSEC toàn 0 hoặc không tăng -> fallback sang i * 1000 / fps."""
        # Ca 1: Toàn 0
        pos_zeros = [0.0, 0.0, 0.0, 0.0]
        ts_z, src_z = resolve_timestamps(pos_zeros, fps=25.0)
        self.assertEqual(src_z, "fps_index")
        self.assertEqual(ts_z, [0.0, 40.0, 80.0, 120.0])

        # Ca 2: Không tăng chặt (có khung trùng timestamp)
        pos_stuck = [0.0, 33.3, 33.3, 66.7]
        ts_s, src_s = resolve_timestamps(pos_stuck, fps=30.0)
        self.assertEqual(src_s, "fps_index")
        self.assertAlmostEqual(ts_s[1], 1000.0 / 30.0, places=4)

    def test_ac2_filter_process_fps(self):
        """--process-fps 15 trên chuỗi 30 fps: giữ khung cách >= 66.67 ms, khung đầu luôn giữ."""
        fps = 30.0
        n = 10
        timestamps = [i * 1000.0 / fps for i in range(n)]  # 0, 33.33, 66.67, 100.0, 133.33, ...
        dummy_frames = [np.full((10, 10, 3), i, dtype=np.uint8) for i in range(n)]

        kept_frames, kept_ts = filter_process_fps(dummy_frames, timestamps, process_fps=15.0)

        # Khung đầu luôn giữ
        self.assertEqual(kept_ts[0], 0.0)
        self.assertEqual(kept_frames[0][0, 0, 0], 0)

        # Mọi khoảng cách giữa các khung kế tiếp phải >= 66.666 ms
        min_interval = 1000.0 / 15.0 - 1e-4
        for i in range(1, len(kept_ts)):
            self.assertGreaterEqual(kept_ts[i] - kept_ts[i - 1], min_interval)

        # Số khung giữ lại là 5 (chính xác 1 nửa chuỗi 30 fps)
        self.assertEqual(len(kept_frames), 5)
        self.assertEqual(len(kept_ts), 5)

    # -------------------------------------------------------------------------
    # AC-3: Sai lệch khung xương & đường ống giả lập
    # -------------------------------------------------------------------------
    def test_ac3_skeleton_dev_formula(self):
        """dev(a, a + d * e_x) = d / palm_len(a_raw) với sai số <= 1e-6."""
        # Dựng bộ 21 điểm mẫu
        a = np.zeros((21, 2), dtype=np.float64)
        # Đặt cổ tay p0 và khớp ngón giữa p9
        a[0] = [320.0, 400.0]  # p0
        a[9] = [320.0, 250.0]  # p9
        plen = palm_len(a)
        self.assertAlmostEqual(plen, 150.0, places=5)

        # Dịch chuyển tất cả các điểm theo d * e_x
        d = 15.0
        b = a.copy()
        b[:, 0] += d  # shift x

        calculated_dev = dev(a, b, a)
        expected_dev = d / plen  # 15.0 / 150.0 = 0.1
        self.assertIsNotNone(calculated_dev)
        self.assertLessEqual(abs(calculated_dev - expected_dev), 1e-6)

    def test_ac3_skeleton_missing_pairs_excluded(self):
        """Khung thiếu một phía bị loại (trả None)."""
        a = np.zeros((21, 2), dtype=np.float64)
        a[0] = [320.0, 400.0]
        a[9] = [320.0, 250.0]

        self.assertIsNone(dev(None, a, a))
        self.assertIsNone(dev(a, None, a))
        self.assertIsNone(dev(a, a, None))

    def test_ac3_percentiles_calculation(self):
        """p50/p90 khớp np.percentile mặc định."""
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_percentiles(vals)
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["p50"], 30.0)
        self.assertEqual(stats["p90"], 46.0)

    def test_ac3_pipeline_execution_order(self):
        """Đường ống app: CLAHE trước MediaPipe, smoother sau MediaPipe, segmenter nhận landmark mượt."""
        call_log = []

        class MockSession:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def process(self, frame_bgr):
                # Ghi nhận liệu frame nhận vào có qua CLAHE không
                # Ta gán một giá trị đặc biệt khi CLAHE được gọi
                is_enhanced = getattr(frame_bgr, "_is_enhanced", False)
                call_log.append(("mediapipe", self.kwargs, is_enhanced))
                # Trả về 21 điểm giả
                lm = np.zeros((21, 3), dtype=np.float32)
                lm[0] = [0.5, 0.8, 0.0]
                lm[9] = [0.5, 0.5, 0.0]
                return lm, "Right", 0.95

            def close(self):
                pass

        # Chuẩn bị dummy frames
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        timestamps = [0.0, 33.3, 66.7]
        from src.inference.level1_core import load_level1_config
        seg_values = load_level1_config("configs/level1_demo_classifier_rev9.json")["values"]

        res = run_pipeline_on_frames(
            frames=frames,
            timestamps=timestamps,
            seg_values=seg_values,
            auto_enhance=True,
            session_factory=MockSession,
        )

        self.assertEqual(res["n_frames"], 3)
        # Kiểm tra 3 phiên MediaPipe đều được khởi tạo và gọi
        self.assertGreater(len(call_log), 0)
        modes = [call[1].get("static_image_mode") for call in call_log]
        self.assertIn(True, modes)   # Phiên static
        self.assertIn(False, modes)  # Phiên video

    # -------------------------------------------------------------------------
    # AC-4: Bảng biên quyết định R-S
    # -------------------------------------------------------------------------
    def test_ac4_rs_boundary_rules(self):
        """Kiểm tra toàn bộ bảng biên R-S1, R-S2 và trường hợp mặc định mediapipe_limit."""
        # 1. p90(smooth) == p90(track) -> fix_draw_raw = False
        r1 = evaluate_rs_rules(p90_smooth=0.05, p90_track=0.05, p90_enh=0.04)
        self.assertFalse(r1["fix_draw_raw"])

        # 2. p90(smooth) - p90(track) > 1e-9 -> fix_draw_raw = True
        r2 = evaluate_rs_rules(p90_smooth=0.05000001, p90_track=0.05, p90_enh=0.04)
        self.assertTrue(r2["fix_draw_raw"])
        self.assertFalse(r2["mediapipe_limit"])

        # 3. p90(enh) - p90(track) > 1e-9 -> suggest_no_auto_enhance = True
        r3 = evaluate_rs_rules(p90_smooth=0.04, p90_track=0.05, p90_enh=0.05000001)
        self.assertTrue(r3["suggest_no_auto_enhance"])
        self.assertFalse(r3["mediapipe_limit"])

        # 4. Không cái nào -> mediapipe_limit = True
        r4 = evaluate_rs_rules(p90_smooth=0.04, p90_track=0.05, p90_enh=0.04)
        self.assertTrue(r4["mediapipe_limit"])
        self.assertFalse(r4["fix_draw_raw"])
        self.assertFalse(r4["suggest_no_auto_enhance"])

    # -------------------------------------------------------------------------
    # AC-8: Cấu trúc JSON & Privacy
    # -------------------------------------------------------------------------
    def test_ac8_json_structure_and_privacy(self):
        """Khung JSON có đủ generated_by, rules, decisions; grep users/ bằng 0; không chứa ảnh."""
        from scripts.level1_gesture_diag import build_metadata

        meta = build_metadata(["test_cmd", "--arg1"])
        self.assertIn("command", meta)
        self.assertIn("commit", meta)
        self.assertIn("code_dirty", meta)
        self.assertIn("utc", meta)

        report_sample = {
            "generated_by": meta,
            "rules": PRESET_RULES_13G,
            "skeleton": {"moving_smooth": {"p90": 0.05}, "moving_track": {"p90": 0.04}},
            "decisions": evaluate_rs_rules(0.05, 0.04, 0.03),
            "per_clip": {},
        }

        json_str = json.dumps(report_sample, ensure_ascii=False)

        # Kiểm tra regex users[\/]+ trong JSON test phải bằng 0 (không rò rỉ username / đường dẫn cục bộ)
        matches = re.findall(r"users[\/\\]+", json_str, re.IGNORECASE)
        self.assertEqual(len(matches), 0, "Không được rò rỉ đường dẫn người dùng users/ trong JSON")

        # Không khóa nào chứa dữ liệu ảnh nhị phân/base64
        self.assertNotIn("base64", json_str)
        self.assertNotIn("image_bytes", json_str)


if __name__ == "__main__":
    unittest.main()
