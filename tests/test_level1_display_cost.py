"""
Tests for level1_display_cost (plan 15 lần sửa 13b U2d, AC-U5, gate DC1).
chuỗi tạo có kiểm soát để kiểm logic — không cần dữ liệu thật.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts import level1_display_cost as cost_mod  # noqa: E402


class TestPureFunctions(unittest.TestCase):
    """Kiểm tra các hàm thuần túy tính toán percentile, tỷ lệ, gate và tạo báo cáo."""

    def test_percentile_linear(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(cost_mod.percentile(values, 50), 30.0)
        self.assertAlmostEqual(cost_mod.percentile(values, 90), float(np.percentile(values, 90)))

    def test_summarize_frame_total(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        summary = cost_mod.summarize_frame_total(values)
        self.assertIn("n", summary)
        self.assertIn("p50", summary)
        self.assertIn("p90", summary)
        self.assertEqual(summary["n"], 5)
        self.assertAlmostEqual(summary["p50"], 30.0)
        self.assertAlmostEqual(summary["p90"], float(np.percentile(values, 90)))

        # Rỗng
        empty_summary = cost_mod.summarize_frame_total([])
        self.assertEqual(empty_summary["n"], 0)
        self.assertEqual(empty_summary["p50"], 0.0)
        self.assertEqual(empty_summary["p90"], 0.0)

    def test_compute_ratio(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        self.assertAlmostEqual(cost_mod.compute_ratio(10.0, 12.0), 1.2)
        self.assertAlmostEqual(cost_mod.compute_ratio(10.0, 12.5), 1.25)
        self.assertAlmostEqual(cost_mod.compute_ratio(10.0, 15.0), 1.5)
        self.assertEqual(cost_mod.compute_ratio(0.0, 12.0), 0.0)

    def test_dc1_gate_boundary(self):
        # Biên theo đặc tả: ratio 1.25 => pass, 1.2501 => fail
        g_pass = cost_mod.dc1_gate(1.25)
        self.assertEqual(g_pass["name"], "DC1")
        self.assertEqual(g_pass["threshold"], 1.25)
        self.assertTrue(g_pass["pass"])

        g_fail = cost_mod.dc1_gate(1.2501)
        self.assertEqual(g_fail["name"], "DC1")
        self.assertEqual(g_fail["threshold"], 1.25)
        self.assertFalse(g_fail["pass"])

        g_below = cost_mod.dc1_gate(1.10)
        self.assertTrue(g_below["pass"])

        g_above = cost_mod.dc1_gate(1.30)
        self.assertFalse(g_above["pass"])

    def test_build_report_keys_and_content(self):
        command = "python scripts/level1_display_cost.py --out reports/cost.json"
        commit = "1234567890abcdef"
        clip = "data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4"
        natural_summary = {"n": 100, "p50": 10.0, "p90": 15.0}
        p1080_summary = {"n": 100, "p50": 12.0, "p90": 18.0}
        py_ver = "3.10.12"
        cv2_ver = "4.10.0"

        report = cost_mod.build_report(command, commit, clip, natural_summary, p1080_summary, py_ver, cv2_ver)

        expected_keys = {
            "command",
            "commit",
            "code_dirty",
            "clip",
            "natural",
            "window_1080p",
            "ratio_p50",
            "gate",
            "note",
            "python",
            "cv2",
        }
        self.assertTrue(expected_keys.issubset(set(report.keys())))
        self.assertEqual(report["command"], command)
        self.assertEqual(report["commit"], commit)
        self.assertFalse(report["code_dirty"])
        self.assertEqual(report["clip"], clip)
        self.assertEqual(report["python"], py_ver)
        self.assertEqual(report["cv2"], cv2_ver)

        # Kiểm tra nội dung natural
        nat = report["natural"]
        self.assertEqual(nat["n_frames"], 100)
        self.assertEqual(nat["p50_ms"], 10.0)
        self.assertEqual(nat["p90_ms"], 15.0)
        self.assertEqual(nat["path"], "Hud.compose (đường cũ, không qua render_to_window)")

        # Kiểm tra nội dung window_1080p
        w1080 = report["window_1080p"]
        self.assertEqual(w1080["n_frames"], 100)
        self.assertEqual(w1080["p50_ms"], 12.0)
        self.assertEqual(w1080["p90_ms"], 18.0)
        self.assertEqual(w1080["path"], "render_to_window")

        # Kiểm tra ratio và gate
        self.assertAlmostEqual(report["ratio_p50"], 1.2)
        self.assertEqual(report["gate"]["name"], "DC1")
        self.assertEqual(report["gate"]["threshold"], 1.25)
        self.assertTrue(report["gate"]["pass"])

        # Note chứa cả 'imshow vá' và 'Hud.compose'
        self.assertIn("imshow vá", report["note"])
        self.assertIn("Hud.compose", report["note"])


class TestRecorderLogic(unittest.TestCase):
    """Kiểm logic bộ ghi recorder không cần video thật."""

    def test_recorder_natural_and_scaled(self):
        # Tự nhiên
        rec_nat = cost_mod._DisplayCostRecorder("natural")
        self.assertEqual(rec_nat.waitKey(), -1)
        self.assertEqual(rec_nat.getWindowProperty("VSLT", 0), 1.0)
        # Ban đầu chưa có imshow/resize
        self.assertEqual(rec_nat.getWindowImageRect("VSLT"), (0, 0, 640, 643))
        # Khi app gọi resizeWindow khung đầu
        rec_nat.resizeWindow("VSLT", 640, 643)
        self.assertEqual(rec_nat.getWindowImageRect("VSLT"), (0, 0, 640, 643))
        # Khi app imshow
        fake_img = np.zeros((643, 640, 3), dtype=np.uint8)
        rec_nat.imshow("VSLT", fake_img)
        self.assertEqual(rec_nat.getWindowImageRect("VSLT"), (0, 0, 640, 643))

        # Cửa sổ 1080p
        rec_1080 = cost_mod._DisplayCostRecorder((0, 0, 1920, 1080))
        self.assertEqual(rec_1080.getWindowImageRect("VSLT"), (0, 0, 1920, 1080))


class TestDisplayCostCli(unittest.TestCase):
    """Kiểm tra CLI tạo file JSON khi vá hàm measure bằng chuỗi tổng hợp."""

    def test_cli_writes_json_when_measure_patched(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        fake_natural_series = [10.0, 10.5, 11.0, 11.5, 12.0]  # p50 = 11.0
        fake_1080_series = [12.0, 12.5, 13.0, 13.5, 14.0]     # p50 = 13.0, ratio = 13.0 / 11.0 = 1.1818 <= 1.25

        def fake_measure(rect, clip=cost_mod.CLIP):
            if rect == "natural":
                return list(fake_natural_series)
            return list(fake_1080_series)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "reports", "display_cost.json")
            with mock.patch("scripts.level1_display_cost.measure", side_effect=fake_measure):
                stdout_buf = io.StringIO()
                with mock.patch("sys.stdout", stdout_buf):
                    ret = cost_mod.main(["--out", out_file])

                self.assertEqual(ret, 0)
                self.assertTrue(os.path.exists(out_file))

                out_str = stdout_buf.getvalue()
                self.assertIn("DC1 pass=True", out_str)
                self.assertIn("ratio=", out_str)

                with open(out_file, encoding="utf-8") as f:
                    data = json.load(f)

                self.assertIn("command", data)
                self.assertIn("commit", data)
                self.assertIn("code_dirty", data)
                self.assertEqual(data["natural"]["n_frames"], len(fake_natural_series))
                self.assertEqual(data["window_1080p"]["n_frames"], len(fake_1080_series))
                self.assertTrue(data["gate"]["pass"])
                self.assertIn("imshow vá", data["note"])
                self.assertIn("Hud.compose", data["note"])

    def test_cli_exit_zero_even_when_gate_fails(self):
        # chuỗi tạo có kiểm soát để kiểm logic (ratio vượt ngưỡng 1.25)
        fake_natural_series = [10.0]
        fake_1080_series = [20.0]  # ratio = 2.0 > 1.25 => FAIL

        def fake_measure(rect, clip=cost_mod.CLIP):
            if rect == "natural":
                return list(fake_natural_series)
            return list(fake_1080_series)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "display_cost_fail.json")
            with mock.patch("scripts.level1_display_cost.measure", side_effect=fake_measure):
                stdout_buf = io.StringIO()
                with mock.patch("sys.stdout", stdout_buf):
                    ret = cost_mod.main(["--out", out_file])

                self.assertEqual(ret, 0)
                self.assertTrue(os.path.exists(out_file))

                out_str = stdout_buf.getvalue()
                self.assertIn("DC1 pass=False", out_str)
                self.assertIn("ratio=", out_str)

                with open(out_file, encoding="utf-8") as f:
                    data = json.load(f)

                self.assertFalse(data["gate"]["pass"])
