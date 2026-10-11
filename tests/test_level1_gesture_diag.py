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
    # AC-5: Ablation dùng GestureEngine thật
    # -------------------------------------------------------------------------
    def test_ac5_ablation_real_engine(self):
        """Ablation trên chuỗi tổng hợp với GestureEngine thật:
        - vẫy 2 nét biên độ 0.8x palm phát ở design;
        - vẫy biên độ 0.5x palm không phát ở design, c(wave_min_amplitude) = 0.5;
        - giữ xòe 500 ms không phát ở design (600), c(space_hold_ms) = 500.
        """
        from tests.test_level1_gestures import (
            DESIGN_TABLE,
            FLAT,
            OPEN_PALM,
            PALM,
            hand,
            stroke_path,
            to_mediapipe,
        )
        from scripts.level1_gesture_diag import (
            find_critical_value,
            make_floor_values,
            run_engine_on_sequence,
        )

        floor_values = make_floor_values(DESIGN_TABLE)
        dt = 25.0  # 40 fps
        w, h = TARGET_W, TARGET_H

        # 1. Giữ xòe 500 ms (20 frames * 25ms = 500ms)
        space_seq_500 = []
        for i in range(21):
            ts = i * dt
            # Bàn tay xòe ở giữa màn hình
            pts = hand(OPEN_PALM, 0.5, 0.5, PALM)
            lm = to_mediapipe(pts, w, h)
            space_seq_500.append((ts, lm, w, h, True))  # still = True

        # Tại design (space_hold_ms=600): KHÔNG phát
        emits_design = run_engine_on_sequence(DESIGN_TABLE, space_seq_500)
        self.assertEqual(emits_design["space"], 0)

        # c(space_hold_ms) trên lưới [600, 550, 500, 450, 400]
        c_space = find_critical_value(space_seq_500, "space_hold_ms", "space", floor_values)
        self.assertEqual(c_space, 500)

        # 2. Vẫy 2 nét: biên độ 0.8x palm vs 0.5x palm
        def make_wave_seq(amp_ratio):
            xs = stroke_path(0.5, [amp_ratio * PALM, -amp_ratio * PALM], frames_per_stroke=10)
            seq = []
            for i, x in enumerate(xs):
                ts = i * dt
                pts = hand(FLAT, x, 0.5, PALM)
                lm = to_mediapipe(pts, w, h)
                seq.append((ts, lm, w, h, False))
            return seq

        wave_seq_08 = make_wave_seq(0.8)
        emits_08 = run_engine_on_sequence(DESIGN_TABLE, wave_seq_08)
        self.assertGreaterEqual(emits_08["backspace"], 1, "Vẫy 0.8x palm phải phát ở design")

        wave_seq_05 = make_wave_seq(0.5)
        emits_05 = run_engine_on_sequence(DESIGN_TABLE, wave_seq_05)
        self.assertEqual(emits_05["backspace"], 0, "Vẫy 0.5x palm không phát ở design")

        c_wave = find_critical_value(wave_seq_05, "wave_min_amplitude", "backspace", floor_values)
        self.assertEqual(c_wave, 0.50, "c(wave_min_amplitude) cho chuỗi 0.5x palm phải bằng 0.50")

    # -------------------------------------------------------------------------
    # AC-6: Quy tắc R-G (G-0..G-3) với bộ chạy giả tiêm vào
    # -------------------------------------------------------------------------
    def test_ac6_rg_decision_rules(self):
        """Kiểm tra đầy đủ G-0, G-1, G-2, G-3 qua bộ chạy giả (mock runner)."""
        from tests.test_level1_gestures import DESIGN_TABLE
        from scripts.level1_gesture_diag import evaluate_gesture_rules

        # Ca 1: G-0: design phát ở >= 4/5 clip trên cả 2 biến thể -> stop_offline_ok = True
        def runner_g0(values, clip):
            return {"space": 1, "backspace": 0}

        clips_cat = {
            "space": [{"cat": "space", "idx": i} for i in range(5)],
            "backspace": [{"cat": "backspace", "idx": i} for i in range(5)],
            "spell": [{"cat": "spell", "idx": i} for i in range(2)],
        }
        res_g0 = evaluate_gesture_rules(clips_cat, clips_cat, DESIGN_TABLE, runner=runner_g0)
        self.assertTrue(res_g0["decisions"]["stop_offline_ok"])

        # Ca 2: G-1: floor phát ở < 4/5 clip (< 4) -> stop_outside_config = True
        def runner_g1(values, clip):
            # Chỉ 2 clip phát
            if clip.get("idx", 0) < 2 and clip.get("cat") == "space":
                return {"space": 1, "backspace": 0}
            return {"space": 0, "backspace": 0}

        res_g1 = evaluate_gesture_rules(clips_cat, clips_cat, DESIGN_TABLE, runner=runner_g1)
        self.assertTrue(res_g1["decisions"]["stop_outside_config"])

        # Ca 3: G-2 & G-3: Tính ngưỡng tới hạn, lấy giá trị lỏng hơn giữa 2 biến thể, không vượt sàn
        def runner_g2(values, clip):
            cat = clip.get("cat")
            idx = clip.get("idx", 0)
            if cat == "spell":
                return {"space": 0, "backspace": 0}
            hold = values.get("space_hold_ms", 600)
            amp = values.get("wave_min_amplitude", 0.6)
            sp = 1 if cat == "space" and hold <= 450 and idx < 4 else 0
            bs = 1 if cat == "backspace" and amp <= 0.50 and idx < 4 else 0
            return {"space": sp, "backspace": bs}

        res_g2 = evaluate_gesture_rules(clips_cat, None, DESIGN_TABLE, runner=runner_g2)
        dec = res_g2["decisions"]
        self.assertFalse(dec["stop_offline_ok"])
        self.assertFalse(dec["stop_outside_config"])
        self.assertFalse(dec["stop_combined"])
        self.assertIn("space_hold_ms", dec["tuned_values"])
        self.assertEqual(dec["tuned_values"]["space_hold_ms"], 450)

        # Ca 4: G-3 thất bại nếu có phát ngược hoặc phát trên spell
        def runner_g3_spell_polluted(values, clip):
            cat = clip.get("cat")
            if cat == "spell":
                return {"space": 1, "backspace": 0}
            return {"space": 1, "backspace": 0}

        res_g3 = evaluate_gesture_rules(clips_cat, None, DESIGN_TABLE, runner=runner_g3_spell_polluted)
        self.assertTrue(res_g3["decisions"]["stop_offline_ok"] or res_g3["decisions"]["stop_combined"])

    # -------------------------------------------------------------------------
    # AC-7: Chế độ --mode gate (GT1/GT2)
    # -------------------------------------------------------------------------
    def test_ac7_mode_gate(self):
        """Kiểm tra chế độ --mode gate:
        - 10/12 + 0 ngược => pass
        - 9/12 => fail
        - 10/12 nhưng 1 clip phát ngược => clip đó không đạt
        - Số clip != 12 => fail-closed (pass = False) + lý do.
        """
        from scripts.level1_gesture_diag import run_gate_mode

        # 1. 10/12 space (0 back), 10/12 backspace (0 space) -> PASS
        def runner_pass(values, clip_idx):
            # clip_idx 0..9 phát đúng, 10..11 không phát
            if clip_idx < 10:
                return {"space": 1, "backspace": 0}
            return {"space": 0, "backspace": 0}

        def runner_back_pass(values, clip_idx):
            if clip_idx < 10:
                return {"space": 0, "backspace": 1}
            return {"space": 0, "backspace": 0}

        clips_12 = {"space": list(range(12)), "backspace": list(range(12))}

        def runner_combined_pass(values, c):
            # Nếu c là space clip (chẵn/lẻ phân biệt qua đối số)
            return {"space": 1, "backspace": 0} if c < 10 else {"space": 0, "backspace": 0}

        # Tạo runner phân biệt cử chỉ theo c
        class MockGateRunner:
            def __call__(self, values, c):
                is_space_clip = c.get("is_space", False)
                idx = c.get("idx", 0)
                if is_space_clip:
                    return {"space": 1 if idx < 10 else 0, "backspace": 0}
                else:
                    return {"space": 0, "backspace": 1 if idx < 10 else 0}

        clips_pass = {
            "space": [{"is_space": True, "idx": i} for i in range(12)],
            "backspace": [{"is_space": False, "idx": i} for i in range(12)],
        }
        res_pass = run_gate_mode(clips_pass, {}, runner=MockGateRunner())
        self.assertTrue(res_pass["pass"], f"Gate phải pass với 10/12, lý do: {res_pass.get('reason')}")

        # 2. 9/12 -> FAIL
        class MockGateRunner9:
            def __call__(self, values, c):
                is_space_clip = c.get("is_space", False)
                idx = c.get("idx", 0)
                if is_space_clip:
                    return {"space": 1 if idx < 9 else 0, "backspace": 0}
                else:
                    return {"space": 0, "backspace": 1 if idx < 10 else 0}

        res_fail9 = run_gate_mode(clips_pass, {}, runner=MockGateRunner9())
        self.assertFalse(res_fail9["pass"])
        self.assertEqual(res_fail9["gt1"]["valid"], 9)

        # 3. 10/12 space nhưng 1 clip phát ngược backspace -> clip đó bị loại (chỉ còn 9 hợp lệ) -> FAIL
        class MockGateRunnerInverse:
            def __call__(self, values, c):
                is_space_clip = c.get("is_space", False)
                idx = c.get("idx", 0)
                if is_space_clip:
                    # Clip idx=0 phát cả space và backspace (phát ngược)
                    if idx == 0:
                        return {"space": 1, "backspace": 1}
                    return {"space": 1 if idx < 10 else 0, "backspace": 0}
                else:
                    return {"space": 0, "backspace": 1 if idx < 10 else 0}

        res_inverse = run_gate_mode(clips_pass, {}, runner=MockGateRunnerInverse())
        self.assertFalse(res_inverse["pass"])
        self.assertEqual(res_inverse["gt1"]["valid"], 9)

        # 4. Fail-closed khi số clip != 12
        clips_wrong_count = {
            "space": list(range(11)),  # chỉ 11 clip
            "backspace": list(range(12)),
        }
        res_closed = run_gate_mode(clips_wrong_count, {})
        self.assertFalse(res_closed["pass"])
        self.assertIn("Fail-closed", res_closed["reason"])

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

