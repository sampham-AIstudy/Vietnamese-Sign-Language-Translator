"""
Tests for Level 1 scaled and fullscreen display layout and rendering (plan 15 lần sửa 13 U1, AC-U1..AC-U3).
Module under test: src.inference.level1_display.
"""
import os
import sys
import unittest
import numpy as np
import cv2

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.level1_display import (
    DisplayLayout,
    fit_layout,
    render_to_window,
    ScalableHud,
    PanelBuilder,
)
from src.inference.level1_core import load_level1_config
from level1_demo import Hud, find_font


class TestFitLayoutAcU1(unittest.TestCase):
    """AC-U1 fit_layout geometry tests."""

    def test_u1_scale_two(self):
        # cam 640x480, panel 200, window 1280x1360 => scale 2.0
        layout = fit_layout(640, 480, 200, 1280, 1360)
        self.assertEqual(layout.scale, 2.0)
        self.assertEqual(layout.content_w, 1280)
        self.assertEqual(layout.content_h, 1360)
        self.assertEqual(layout.x0, 0)
        self.assertEqual(layout.y0, 0)
        self.assertEqual(layout.cam_rect, (0, 0, 1280, 960))
        self.assertEqual(layout.panel_rect, (0, 960, 1280, 400))

    def test_u1_scale_1080p(self):
        # cam 640x480, panel 200, window 1920x1080
        layout = fit_layout(640, 480, 200, 1920, 1080)
        self.assertAlmostEqual(layout.content_h, 1080, delta=1)
        expected_x0 = (1920 - layout.content_w) // 2
        self.assertAlmostEqual(layout.x0, expected_x0, delta=1)
        self.assertEqual(layout.y0, 0)
        self.assertTrue(layout.x0 > 0)

    def test_u1_tall_window(self):
        # cam 640x480, panel 200, window 600x2000 => content_w == 600, centered vertically
        layout = fit_layout(640, 480, 200, 600, 2000)
        self.assertEqual(layout.content_w, 600)
        self.assertEqual(layout.x0, 0)
        self.assertTrue(layout.y0 > 0)
        self.assertEqual(layout.y0, (2000 - layout.content_h) // 2)

    def test_u1_invalid_windows(self):
        # (-1, -1, -1, -1), (0, 0), None => scale 1, natural size
        for inv in [(-1, -1, -1, -1), (0, 0), None, (-1, -1), (0, 0, 0, 0)]:
            layout = fit_layout(640, 480, 200, inv)
            self.assertEqual(layout.scale, 1.0)
            self.assertEqual(layout.content_w, 640)
            self.assertEqual(layout.content_h, 680)
            self.assertEqual(layout.x0, 0)
            self.assertEqual(layout.y0, 0)
            self.assertEqual(layout.cam_rect, (0, 0, 640, 480))
            self.assertEqual(layout.panel_rect, (0, 480, 640, 200))

    def test_u1_grid_scan(self):
        # Grid 200..4000 step 175 in both dims
        cam_w, cam_h, panel_h = 640, 480, 200
        orig_ratio = cam_w / (cam_h + panel_h)

        for w in range(200, 4001, 175):
            for h in range(200, 4001, 175):
                layout = fit_layout(cam_w, cam_h, panel_h, w, h)
                self.assertLessEqual(layout.content_w, w)
                self.assertLessEqual(layout.content_h, h)
                touch_w = abs(layout.content_w - w) <= 1
                touch_h = abs(layout.content_h - h) <= 1
                self.assertTrue(
                    touch_w or touch_h,
                    f"Not touching any edge: w={w}, h={h}, cw={layout.content_w}, ch={layout.content_h}",
                )
                actual_ratio = layout.content_w / layout.content_h
                diff = abs(actual_ratio / orig_ratio - 1.0)
                self.assertLessEqual(
                    diff,
                    0.01,
                    f"Ratio deviation {diff*100:.2f}% > 1% at w={w}, h={h}",
                )

    def test_u1_unpacking(self):
        layout = fit_layout(640, 480, 200, 1280, 1360)
        scale, cw, ch, x0, y0, cr, pr = layout
        self.assertEqual(scale, 2.0)
        self.assertEqual(cw, 1280)
        self.assertEqual(ch, 1360)
        self.assertEqual(x0, 0)
        self.assertEqual(y0, 0)
        self.assertEqual(cr, (0, 0, 1280, 960))
        self.assertEqual(pr, (0, 960, 1280, 400))


class TestRenderToWindowAcU2(unittest.TestCase):
    """AC-U2 render_to_window tests."""

    @classmethod
    def setUpClass(cls):
        cfg = load_level1_config("configs/level1_realtime.json")
        cls.font_path = find_font(None, cfg["values"]["font_paths"])
        cls.font_size = cfg["values"]["hud_font_size"]
        cls.hud = Hud(cls.font_path, cls.font_size)
        cls.scalable_hud = ScalableHud(cls.font_path, cls.font_size)

    def test_u2_shape_and_padding(self):
        # 1920x1080 window with 640x480 cam and natural panel height
        view = np.ones((480, 640, 3), dtype=np.uint8) * 128
        tb_view = {"committed": "xin ", "active": "chào", "text": "xin chào"}
        small = ["Dòng gợi ý 1", "[Góc tay: Hơi nghiêng tay 20°]"]
        stats = ["p50 (ms) mp 15.0", "p50 (ms) sign 30.0 | dropped 0"]
        progress = 0.5

        # Get natural panel height
        _, panel_h = self.scalable_hud.build_panel(640, 1.0, tb_view, small, len(stats))
        layout = fit_layout(640, 480, self.scalable_hud._panel.shape[0], 1920, 1080)

        builder = self.scalable_hud.panel_builder(tb_view, small)
        out = render_to_window(view, builder, stats, progress, layout)

        self.assertEqual(out.shape, (1080, 1920, 3))

        # Check outside content is completely 0 (black bars)
        x0 = layout.x0
        cw = layout.content_w
        if x0 > 0:
            self.assertEqual(np.count_nonzero(out[:, :x0]), 0)
            self.assertEqual(np.count_nonzero(out[:, x0 + cw :]), 0)

    def test_u2_camera_area_resized(self):
        view = np.arange(480 * 640 * 3, dtype=np.uint8).reshape((480, 640, 3))
        tb_view = {"committed": "a", "active": "b", "text": "ab"}
        layout = fit_layout(640, 480, 200, 1920, 1080)
        builder = self.scalable_hud.panel_builder(tb_view, [])

        out = render_to_window(view, builder, [], 0.0, layout)

        cam_x, cam_y, cam_w, cam_h = layout.cam_rect
        cam_sub = out[cam_y : cam_y + cam_h, cam_x : cam_x + cam_w]
        expected_cam = cv2.resize(view, (cam_w, cam_h), interpolation=cv2.INTER_LINEAR)
        self.assertTrue(np.array_equal(cam_sub, expected_cam))

    def test_u2_natural_equals_hud_compose(self):
        view = np.ones((480, 640, 3), dtype=np.uint8) * 100
        tb_view = {"committed": "xin ", "active": "chào", "text": "xin chào"}
        small = ["Dòng 1", "Dòng 2"]
        stats = ["p50 (ms) 12.3", "p50 (ms) 45.6"]
        progress = 0.65

        # Direct Hud compose
        expected = self.hud.compose(view, tb_view, small, progress, stats)
        panel_h = self.hud._panel.shape[0]

        # Natural layout render_to_window
        layout = fit_layout(640, 480, panel_h, None)
        builder = self.scalable_hud.panel_builder(tb_view, small)
        out = render_to_window(view, builder, stats, progress, layout)

        self.assertEqual(out.shape, expected.shape)
        self.assertTrue(
            np.array_equal(out, expected),
            "render_to_window at natural size must be bit-identical to Hud.compose",
        )


class TestScalableHudAcU3(unittest.TestCase):
    """AC-U3 ScalableHud and caching tests."""

    @classmethod
    def setUpClass(cls):
        cfg = load_level1_config("configs/level1_realtime.json")
        cls.font_path = find_font(None, cfg["values"]["font_paths"])
        cls.font_size = cfg["values"]["hud_font_size"]

    def test_u3_scale_two_font_and_height(self):
        hud = ScalableHud(self.font_path, self.font_size)
        tb_view = {"committed": "xin ", "active": "chào"}
        small = ["Gợi ý"]
        stats = ["stats 1", "stats 2"]

        # Build at scale 1.0
        p1, small_h1 = hud.build_panel(640, 1.0, tb_view, small, len(stats))
        h1 = p1.shape[0]

        # Build at scale 2.0
        p2, small_h2 = hud.build_panel(1280, 2.0, tb_view, small, len(stats))
        h2 = p2.shape[0]

        # Font size at scale 2
        self.assertEqual(hud.last_font_size, round(self.font_size * 2))

        # Panel height should be approximately 2x (within +/- 2px per line)
        # Total lines = 1 (big) + 1 (small) + 2 (stats) = 4 lines
        total_lines = 1 + len(small) + len(stats)
        self.assertAlmostEqual(h2, 2 * h1, delta=2 * total_lines + 8)

    def test_u3_caching_stats_lines(self):
        hud = ScalableHud(self.font_path, self.font_size)
        tb_view = {"committed": "a", "active": "b"}
        small = ["hint"]

        # 1st build
        self.assertEqual(hud.build_count, 0)
        builder = hud.panel_builder(tb_view, small)

        layout = fit_layout(640, 480, 200, 1280, 1360)
        view = np.zeros((480, 640, 3), dtype=np.uint8)

        render_to_window(view, builder, ["stat frame 1", "line 2"], 0.0, layout)
        self.assertEqual(hud.build_count, 1)

        # 2nd call: only stats_lines content changed, count of stats is the same (2)
        render_to_window(view, builder, ["stat frame 2 with new values", "line 2 updated"], 0.1, layout)
        self.assertEqual(hud.build_count, 1, "Panel must not be rebuilt when only stats lines change")

        # 3rd call: view changed => should rebuild
        tb_view_new = {"committed": "a", "active": "c"}
        builder_new = hud.panel_builder(tb_view_new, small)
        render_to_window(view, builder_new, ["stat frame 3", "line 2"], 0.2, layout)
        self.assertEqual(hud.build_count, 2, "Panel must be rebuilt when text/view changes")


if __name__ == "__main__":
    unittest.main()
