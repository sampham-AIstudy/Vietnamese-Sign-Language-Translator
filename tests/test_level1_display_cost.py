"""
Tests for level1_display_cost (plan 15 lần sửa 13b U2d, AC-U5, gate DC1).
chuỗi tạo có kiểm soát để kiểm logic — không cần dữ liệu thật.
"""
import io
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts import level1_display_cost as cost_mod  # noqa: E402


def _run_summary(n, p50, p90, compose=None, rtw=0, hud=2.0, mediapipe=25.0, n_imshow=None):
    """Tóm tắt một lần đo (chuỗi tạo có kiểm soát để kiểm logic): mặc định mọi khung đi Hud.compose, imshow = khung."""
    compose = n - rtw if compose is None else compose
    return {
        "n_frames": n,
        "p50_ms": p50,
        "p90_ms": p90,
        "n_imshow": n if n_imshow is None else n_imshow,
        "path_counts": {"Hud.compose": compose, "render_to_window": rtw},
        "stage_p50_ms": {"hud": hud, "mediapipe": mediapipe},
    }


def _measured(frame_total, rtw=0, hud=None, mediapipe=None):
    """Kết quả `measure` tạo có kiểm soát (chuỗi tạo có kiểm soát để kiểm logic): imshow = khung, mọi khung đếm đường vẽ."""
    n = len(frame_total)
    return {
        "frame_total": list(frame_total),
        "hud": list(hud if hud is not None else [2.0] * n),
        "mediapipe": list(mediapipe if mediapipe is not None else [25.0] * n),
        "n_imshow": n,
        "path_counts": {"Hud.compose": n - rtw, "render_to_window": rtw},
    }


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
        # 13c TB-1 (fail-closed): p50 tự nhiên <= 0 hoặc không hữu hạn => ValueError, không trả 0.0 (0.0 sẽ làm gate pass)
        for bad in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(p50_natural=bad):
                with self.assertRaises(ValueError):
                    cost_mod.compute_ratio(bad, 12.0)

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

        # 13c TB-1: ratio không hợp lệ => không pass (fail-closed), có lý do
        for bad in (float("nan"), None):
            with self.subTest(ratio=bad):
                g_bad = cost_mod.dc1_gate(bad)
                self.assertEqual(g_bad["name"], "DC1")
                self.assertEqual(g_bad["threshold"], 1.25)
                self.assertIs(g_bad["pass"], False)
                self.assertTrue(g_bad["reason"])
        # ratio hợp lệ: không có lý do
        self.assertIsNone(cost_mod.dc1_gate(1.25)["reason"])
        self.assertIsNone(cost_mod.dc1_gate(1.30)["reason"])

    def test_build_report_keys_and_content(self):
        command = "python scripts/level1_display_cost.py --out reports/cost.json"
        commit = "1234567890abcdef"
        clip = "data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4"
        natural_summary = _run_summary(100, 10.0, 15.0, compose=97, rtw=3, hud=2.5, mediapipe=27.0)
        p1080_summary = _run_summary(100, 12.0, 18.0, compose=0, rtw=100, hud=6.0, mediapipe=28.0)
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
        # 13c TB-2: đường vẽ là số ĐẾM được, không còn chuỗi `path` hard-code
        self.assertNotIn("path", nat)
        self.assertEqual(nat["path_counts"], {"Hud.compose": 97, "render_to_window": 3})
        self.assertEqual(nat["n_imshow"], 100)
        self.assertEqual(nat["stage_p50_ms"], {"hud": 2.5, "mediapipe": 27.0})

        # Kiểm tra nội dung window_1080p
        w1080 = report["window_1080p"]
        self.assertEqual(w1080["n_frames"], 100)
        self.assertEqual(w1080["p50_ms"], 12.0)
        self.assertEqual(w1080["p90_ms"], 18.0)
        self.assertNotIn("path", w1080)
        self.assertEqual(w1080["path_counts"], {"Hud.compose": 0, "render_to_window": 100})
        self.assertEqual(w1080["n_imshow"], 100)
        self.assertEqual(w1080["stage_p50_ms"], {"hud": 6.0, "mediapipe": 28.0})

        # Kiểm tra ratio và gate
        self.assertAlmostEqual(report["ratio_p50"], 1.2)
        self.assertEqual(report["gate"]["name"], "DC1")
        self.assertEqual(report["gate"]["threshold"], 1.25)
        self.assertTrue(report["gate"]["pass"])

        # Note chứa cả 'imshow vá' và 'Hud.compose'
        self.assertIn("imshow vá", report["note"])
        self.assertIn("Hud.compose", report["note"])

        # 13c: khóa mới của AC-C1
        self.assertIsNone(report["gate"]["reason"])
        self.assertEqual(report["min_frames"], 10)
        self.assertIs(report["info"]["in_gate"], False)
        self.assertAlmostEqual(report["info"]["hud_p50_delta_ms"], 6.0 - 2.5)
        for phrase in ("imshow vá", "không cửa sổ thật", "không đo chi phí vẽ cửa sổ HĐH", "path_counts"):
            self.assertIn(phrase, report["note"])
        # note không còn khẳng định lần natural đi Hud.compose (TB-2)
        self.assertNotIn("đo đường Hud.compose", report["note"])
        self.assertNotIn("natural đo đường", report["note"].replace('"', ""))


class TestBuildReportValidityC1(unittest.TestCase):
    """13c TB-1: điều kiện hợp lệ dữ liệu áp TRƯỚC gate DC1, fail-closed (chuỗi tạo có kiểm soát để kiểm logic)."""

    def _report(self, natural, p1080):
        return cost_mod.build_report("python scripts/level1_display_cost.py --out x.json", "abc", "clip.mp4",
                                     natural, p1080, "3.10", "4.10")

    def assert_invalid(self, report, ratio_none):
        self.assertIs(report["gate"]["pass"], False)
        self.assertIsInstance(report["gate"]["reason"], str)
        self.assertTrue(report["gate"]["reason"].strip())
        self.assertEqual(report["gate"]["name"], "DC1")
        self.assertEqual(report["gate"]["threshold"], 1.25)
        if ratio_none:
            self.assertIsNone(report["ratio_p50"])

    def test_min_frames_constant(self):
        self.assertEqual(cost_mod.MIN_FRAMES, 10)

    def test_natural_empty(self):
        rep = self._report(_run_summary(0, 0.0, 0.0), _run_summary(50, 12.0, 14.0))
        self.assert_invalid(rep, ratio_none=True)

    def test_1080_empty(self):
        rep = self._report(_run_summary(50, 10.0, 12.0), _run_summary(0, 0.0, 0.0))
        self.assert_invalid(rep, ratio_none=True)

    def test_both_empty(self):
        rep = self._report(_run_summary(0, 0.0, 0.0), _run_summary(0, 0.0, 0.0))
        self.assert_invalid(rep, ratio_none=True)

    def test_empty_series_through_summarize(self):
        # đúng chuỗi mà main dùng: measure trả rỗng => summarize_run => build_report không pass
        nat = cost_mod.summarize_run(_measured([]))
        p1080 = cost_mod.summarize_run(_measured([500.0] * 20, rtw=20))
        rep = self._report(nat, p1080)
        self.assert_invalid(rep, ratio_none=True)

    def test_below_min_frames(self):
        rep = self._report(_run_summary(9, 10.0, 12.0), _run_summary(50, 11.0, 13.0))
        self.assert_invalid(rep, ratio_none=False)
        rep = self._report(_run_summary(50, 10.0, 12.0), _run_summary(9, 11.0, 13.0))
        self.assert_invalid(rep, ratio_none=False)

    def test_path_counts_sum_differs_from_n_imshow(self):
        bad = _run_summary(20, 10.0, 12.0, compose=18, rtw=1)  # 19 != n_imshow 20
        rep = self._report(bad, _run_summary(20, 11.0, 13.0))
        self.assert_invalid(rep, ratio_none=False)
        rep = self._report(_run_summary(20, 10.0, 12.0), bad)
        self.assert_invalid(rep, ratio_none=False)

    def test_n_imshow_differs_from_n_frames(self):
        bad = _run_summary(20, 10.0, 12.0, compose=21, rtw=0, n_imshow=21)  # path_counts == n_imshow, != n_frames
        rep = self._report(bad, _run_summary(20, 11.0, 13.0))
        self.assert_invalid(rep, ratio_none=False)
        rep = self._report(_run_summary(20, 10.0, 12.0), bad)
        self.assert_invalid(rep, ratio_none=False)

    def test_missing_counts_is_invalid(self):
        # thiếu n_imshow / path_counts (lược đồ cũ của U2d) => không pass
        rep = self._report({"n": 100, "p50": 10.0, "p90": 15.0}, {"n": 100, "p50": 12.0, "p90": 18.0})
        self.assert_invalid(rep, ratio_none=False)

    def test_non_finite_p50(self):
        rep = self._report(_run_summary(20, float("nan"), 12.0), _run_summary(20, 11.0, 13.0))
        self.assert_invalid(rep, ratio_none=True)
        rep = self._report(_run_summary(20, 10.0, 12.0), _run_summary(20, float("inf"), 13.0))
        self.assert_invalid(rep, ratio_none=True)

    def test_valid_min_frames_pass(self):
        rep = self._report(_run_summary(10, 10.0, 12.0), _run_summary(10, 12.0, 13.0, rtw=10))
        self.assertAlmostEqual(rep["ratio_p50"], 1.2)
        self.assertIs(rep["gate"]["pass"], True)
        self.assertIsNone(rep["gate"]["reason"])

    def test_valid_ratio_above_threshold_fails_without_reason(self):
        rep = self._report(_run_summary(10, 10.0, 12.0), _run_summary(10, 13.0, 14.0, rtw=10))
        self.assertAlmostEqual(rep["ratio_p50"], 1.3)
        self.assertIs(rep["gate"]["pass"], False)
        self.assertIsNone(rep["gate"]["reason"])

    def test_hud_delta_none_when_stage_missing(self):
        nat = _run_summary(10, 10.0, 12.0, hud=None)
        rep = self._report(nat, _run_summary(10, 12.0, 13.0, rtw=10, hud=6.0))
        self.assertIsNone(rep["info"]["hud_p50_delta_ms"])
        self.assertIs(rep["info"]["in_gate"], False)
        self.assertIs(rep["gate"]["pass"], True)  # số thông tin không vào gate

    def test_summarize_run(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        m = _measured([10.0, 20.0, 30.0, 40.0, 50.0], rtw=2, hud=[1.0, 2.0, 3.0, 4.0, 5.0],
                      mediapipe=[20.0, 21.0, 22.0, 23.0, 24.0])
        s = cost_mod.summarize_run(m)
        self.assertEqual(s["n_frames"], 5)
        self.assertAlmostEqual(s["p50_ms"], 30.0)
        self.assertAlmostEqual(s["p90_ms"], float(np.percentile([10.0, 20.0, 30.0, 40.0, 50.0], 90)))
        self.assertEqual(s["n_imshow"], 5)
        self.assertEqual(s["path_counts"], {"Hud.compose": 3, "render_to_window": 2})
        self.assertEqual(s["stage_p50_ms"], {"hud": 3.0, "mediapipe": 22.0})
        empty = cost_mod.summarize_run(_measured([]))
        self.assertEqual(empty["stage_p50_ms"], {"hud": None, "mediapipe": None})
        self.assertEqual(empty["n_frames"], 0)


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

    def test_recorder_rect_fixed_when_panel_height_changes(self):
        # 13c THẤP-7. Giống cửa sổ thật: sau lần resizeWindow đầu, rect cố định ở cỡ đó; app KHÔNG resize lại khi panel đổi
        # cao. Nên khi panel tự nhiên đổi 640x643 -> 640x663 (hiện thêm dòng gợi ý), rect vẫn 640x643 => cỡ tự nhiên mới
        # khác rect => app đi render_to_window (co nội dung vào rect), không phải Hud.compose. Đây là lý do lần "natural"
        # có thể có khung đi render_to_window, và vì sao JSON ĐẾM path_counts thay vì ghi nhãn cố định.
        from src.inference.level1_display import fit_layout

        rec = cost_mod._DisplayCostRecorder("natural")
        rec.resizeWindow("VSLT", 640, 643)
        rec.imshow("VSLT", np.zeros((643, 640, 3), dtype=np.uint8))
        rect = rec.getWindowImageRect("VSLT")
        self.assertEqual(rect, (0, 0, 640, 643))
        # cỡ tự nhiên cũ (480 + 163) khớp rect => Hud.compose; cỡ tự nhiên mới (480 + 183) không khớp => render_to_window
        self.assertEqual(fit_layout(640, 480, 163, rect), fit_layout(640, 480, 163))
        self.assertNotEqual(fit_layout(640, 480, 183, rect), fit_layout(640, 480, 183))
        # ảnh render_to_window có đúng cỡ rect => imshow (643, 640) => rect vẫn cố định
        layout = fit_layout(640, 480, 183, rect)
        self.assertEqual((layout.win_h, layout.win_w), (643, 640))
        rec.imshow("VSLT", np.zeros((layout.win_h, layout.win_w, 3), dtype=np.uint8))
        self.assertEqual(rec.getWindowImageRect("VSLT"), (0, 0, 640, 643))
        self.assertNotEqual(rec.getWindowImageRect("VSLT"), (0, 0, 640, 663))


class _FakeTimes:
    """StageTimes giả: giữ mọi giá trị theo chặng (chuỗi tạo có kiểm soát để kiểm logic)."""

    def __init__(self):
        self._all = {"frame_total": [], "hud": [], "mediapipe": []}

    def add(self, stage, value):
        self._all[stage].append(float(value))

    def values(self, stage):
        return list(self._all[stage])


def _make_fake_app_module():
    """Module app giả cho measure(): run() gọi Hud.compose 3 lần rồi render_to_window 2 lần (đổi đường giữa chừng), mỗi
    lần imshow đúng ảnh nhận được, và ghi frame_total/hud/mediapipe. Hàm cv2 gốc của module giả ném lỗi nếu không bị vá."""
    log = {"returned": [], "shown": [], "parse_args": [], "times": {"frame_total": [], "hud": [], "mediapipe": []}}

    def _unpatched(*a, **k):
        raise AssertionError("cv2 của module app giả không được vá")

    fake_cv2 = types.SimpleNamespace(imshow=_unpatched, waitKey=_unpatched, getWindowProperty=_unpatched,
                                     namedWindow=_unpatched, destroyAllWindows=_unpatched,
                                     resizeWindow=_unpatched, getWindowImageRect=_unpatched)

    class Hud:
        def compose(self, view, tag):
            img = np.full((7, 5, 3), tag, dtype=np.uint8)
            log["returned"].append(img)
            return img

    def render_to_window(view, tag):
        img = np.full((9, 16, 3), tag, dtype=np.uint8)
        log["returned"].append(img)
        return img

    module = types.SimpleNamespace(Hud=Hud, render_to_window=render_to_window, cv2=fake_cv2)

    class _Parser:
        def parse_args(self, argv):
            log["parse_args"].append(list(argv))
            return types.SimpleNamespace(argv=list(argv))

    class Level1App:
        def __init__(self, args):
            self.args = args
            self.times = _FakeTimes()
            self.hud = Hud()

        def run(self):
            view = np.zeros((3, 3, 3), dtype=np.uint8)
            for i in range(5):
                img = self.hud.compose(view, i) if i < 3 else module.render_to_window(view, i)
                module.cv2.imshow("VSLT", img)
                log["shown"].append(img)
                for stage, base in (("mediapipe", 20.0), ("hud", 2.0), ("frame_total", 30.0)):
                    v = base + i
                    self.times.add(stage, v)
                    log["times"][stage].append(v)

    module.Level1App = Level1App
    module.build_parser = lambda: _Parser()
    return module, log


class TestMeasureCountsC1(unittest.TestCase):
    """13c TB-2 / THẤP-7: measure() đếm đường vẽ bằng cách bọc hàm gốc (hàm gốc vẫn chạy, kết quả đi tiếp tới imshow)."""

    def test_measure_counts_paths_with_switch(self):
        module, log = _make_fake_app_module()
        orig_compose = module.Hud.compose
        orig_rtw = module.render_to_window
        orig_imshow = module.cv2.imshow
        cwd = os.getcwd()

        res = cost_mod.measure("natural", "clips/x.mp4", app_module=module)

        self.assertEqual(res["path_counts"], {"Hud.compose": 3, "render_to_window": 2})
        self.assertEqual(res["n_imshow"], 5)
        self.assertEqual(len(log["returned"]), 5)
        for got, ret in zip(log["shown"], log["returned"]):
            self.assertIs(got, ret)  # đúng đối tượng hàm gốc trả về, không sao chép/thay
        self.assertEqual(res["frame_total"], log["times"]["frame_total"])
        self.assertEqual(res["hud"], log["times"]["hud"])
        self.assertEqual(res["mediapipe"], log["times"]["mediapipe"])
        self.assertEqual(log["parse_args"], [["--source", "clips/x.mp4", "--pace", "realtime"]])
        # vá được gỡ sau khi đo; cwd được trả lại
        self.assertIs(module.Hud.compose, orig_compose)
        self.assertIs(module.render_to_window, orig_rtw)
        self.assertIs(module.cv2.imshow, orig_imshow)
        self.assertEqual(os.getcwd(), cwd)

    def test_measure_counts_are_per_call(self):
        module, _log = _make_fake_app_module()
        first = cost_mod.measure((0, 0, 1920, 1080), "a.mp4", app_module=module)
        second = cost_mod.measure((0, 0, 1920, 1080), "a.mp4", app_module=module)
        self.assertEqual(first["path_counts"], {"Hud.compose": 3, "render_to_window": 2})
        self.assertEqual(second["path_counts"], {"Hud.compose": 3, "render_to_window": 2})
        self.assertEqual(second["n_imshow"], 5)


class TestDisplayCostCli(unittest.TestCase):
    """Kiểm tra CLI tạo file JSON khi vá hàm measure bằng chuỗi tổng hợp."""

    def setUp(self):
        # 13c THẤP-4: main kiểm clip tồn tại TRƯỚC khi đo. measure bị vá nên clip không được đọc; clip mặc định trỏ tới
        # một file có sẵn của repo để test CLI không cần dữ liệu D2 (ca thiếu clip có test riêng, truyền --clip tường minh).
        patcher = mock.patch.object(cost_mod, "CLIP", "scripts/level1_display_cost.py")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cli_writes_json_when_measure_patched(self):
        # chuỗi tạo có kiểm soát để kiểm logic
        fake_natural_series = [10.0 + 0.5 * i for i in range(10)]  # n = 10 = MIN_FRAMES, p50 = 12.25
        fake_1080_series = [12.0 + 0.5 * i for i in range(10)]     # p50 = 14.25, ratio = 14.25 / 12.25 = 1.163 <= 1.25

        def fake_measure(rect, clip=cost_mod.CLIP):
            if rect == "natural":
                return _measured(fake_natural_series)
            return _measured(fake_1080_series, rtw=len(fake_1080_series))

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

    def _run_main(self, argv, fake_measure):
        calls = []

        def recording_measure(rect, clip=None):
            calls.append((rect, clip))
            return fake_measure(rect, clip)

        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        with mock.patch("scripts.level1_display_cost.measure", side_effect=recording_measure):
            with mock.patch("sys.stdout", stdout_buf), mock.patch("sys.stderr", stderr_buf):
                ret = cost_mod.main(argv)
        return ret, calls, stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_cli_exit_one_when_gate_fails(self):
        # chuỗi tạo có kiểm soát để kiểm logic (ratio vượt ngưỡng 1.25, dữ liệu hợp lệ) - 13c THẤP-5: mã thoát 1
        fake_natural_series = [10.0] * 10
        fake_1080_series = [20.0] * 10  # ratio = 2.0 > 1.25 => FAIL

        def fake_measure(rect, clip=None):
            if rect == "natural":
                return _measured(fake_natural_series)
            return _measured(fake_1080_series, rtw=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "display_cost_fail.json")
            ret, calls, out_str, _err = self._run_main(["--out", out_file], fake_measure)

            self.assertEqual(ret, 1)
            self.assertEqual(len(calls), 2)
            self.assertTrue(os.path.exists(out_file))
            self.assertIn("DC1 pass=False", out_str)
            self.assertIn("ratio=", out_str)

            with open(out_file, encoding="utf-8") as f:
                data = json.load(f)

            self.assertFalse(data["gate"]["pass"])
            self.assertIsNone(data["gate"]["reason"])
            self.assertAlmostEqual(data["ratio_p50"], 2.0)

    def test_cli_exit_three_when_data_invalid(self):
        # chuỗi tạo có kiểm soát để kiểm logic: lần natural không có khung => dữ liệu không hợp lệ, vẫn ghi JSON, mã 3
        def fake_measure(rect, clip=None):
            if rect == "natural":
                return _measured([])
            return _measured([12.0] * 10, rtw=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "display_cost_invalid.json")
            ret, _calls, out_str, _err = self._run_main(["--out", out_file], fake_measure)

            self.assertEqual(ret, 3)
            self.assertTrue(os.path.exists(out_file))
            self.assertIn("DC1 pass=False", out_str)
            with open(out_file, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIs(data["gate"]["pass"], False)
            self.assertTrue(data["gate"]["reason"])
            self.assertIsNone(data["ratio_p50"])
            self.assertEqual(data["natural"]["n_frames"], 0)

    def test_cli_exit_two_when_clip_missing(self):
        def fake_measure(rect, clip=None):
            raise AssertionError("measure không được gọi khi thiếu clip")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "display_cost_noclip.json")
            missing = os.path.join(tmpdir, "khong_co.mp4")
            ret, calls, _out, err = self._run_main(["--out", out_file, "--clip", missing], fake_measure)

            self.assertEqual(ret, 2)
            self.assertEqual(calls, [])
            self.assertFalse(os.path.exists(out_file))
            self.assertTrue(err.strip())

    def test_cli_relative_clip_resolved_from_caller_cwd(self):
        # 13c THẤP-4: --clip tương đối hiểu theo cwd của người gọi (abspath trước mọi chdir)
        def fake_measure(rect, clip=None):
            return _measured([10.0] * 10, rtw=0 if rect == "natural" else 10)

        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "clips"))
            with open(os.path.join(tmpdir, "clips", "x.mp4"), "wb") as f:
                f.write(b"")
            out_file = os.path.join(tmpdir, "out.json")
            try:
                os.chdir(tmpdir)
                expected = os.path.abspath(os.path.join(os.getcwd(), "clips", "x.mp4"))
                ret, calls, _out, _err = self._run_main(["--out", out_file, "--clip", "clips/x.mp4"], fake_measure)
            finally:
                os.chdir(cwd)

            self.assertEqual(ret, 0)
            self.assertEqual([c for _r, c in calls], [expected, expected])
            self.assertEqual(calls[0][0], "natural")
            self.assertEqual(calls[1][0], (0, 0, 1920, 1080))
            with open(out_file, encoding="utf-8") as f:
                data = json.load(f)
            # clip nằm ngoài ROOT => ghi abspath
            self.assertEqual(data["clip"], expected)

    def test_cli_clip_inside_root_is_relative_and_no_root_in_json(self):
        # 13c THẤP-6: clip trong ROOT => relpath posix; JSON và command không chứa ROOT (dạng \ lẫn /)
        def fake_measure(rect, clip=None):
            return _measured([10.0] * 10, rtw=0 if rect == "natural" else 10)

        clip_abs = os.path.join(PROJECT_ROOT, "scripts", "level1_display_cost.py")
        root_forms = {PROJECT_ROOT, PROJECT_ROOT.replace("\\", "/"), PROJECT_ROOT.replace("/", "\\"),
                      json.dumps(PROJECT_ROOT)[1:-1]}
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "out.json")
            ret, calls, _out, _err = self._run_main(["--out", out_file, "--clip", clip_abs], fake_measure)

            self.assertEqual(ret, 0)
            self.assertEqual(os.path.normcase(calls[0][1]), os.path.normcase(os.path.abspath(clip_abs)))
            with open(out_file, encoding="utf-8") as f:
                text = f.read()
            data = json.loads(text)
            self.assertEqual(data["clip"], "scripts/level1_display_cost.py")
            self.assertIn("scripts/level1_display_cost.py", data["command"])
            self.assertIn("--clip", data["command"])
            for form in root_forms:
                for hay in (text.lower(), data["command"].lower()):
                    self.assertNotIn(form.lower(), hay)

    def test_command_interpreter_label(self):
        # trình thông dịch trong ROOT => relpath posix; ngoài ROOT => basename (không lộ đường dẫn tuyệt đối)
        inside = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
        with mock.patch.object(sys, "executable", inside):
            self.assertEqual(cost_mod.build_command(["--out", "x.json"]),
                             ".venv/Scripts/python.exe scripts/level1_display_cost.py --out x.json")
        outside = os.path.join(os.path.dirname(PROJECT_ROOT) + "_khac", "py", "python.exe")
        with mock.patch.object(sys, "executable", outside):
            cmd = cost_mod.build_command(["--out", "x.json"])
        self.assertEqual(cmd, "python.exe scripts/level1_display_cost.py --out x.json")
        # đối số là đường dẫn tuyệt đối trong ROOT => relpath posix
        with mock.patch.object(sys, "executable", inside):
            cmd = cost_mod.build_command(["--clip", os.path.join(PROJECT_ROOT, "data", "a.mp4")])
        self.assertEqual(cmd, ".venv/Scripts/python.exe scripts/level1_display_cost.py --clip data/a.mp4")
