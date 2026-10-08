"""
Tests for the Level 1 scaled / fullscreen display (plan 15 lần sửa 13, step U1, AC-U1..AC-U3).
Module under test: src.inference.level1_display (layout + window render) and the scalable panel of level1_demo.Hud
(one source for the panel: the window render calls Hud.panel_builder, nothing of Hud is copied).

AC-U1 fit_layout: content inside the window for every window (x0, y0 >= 0, x0 + w <= win_w, y0 + h <= win_h), one pair
       of black bars, aspect kept; invalid windows give the natural size; (x, y, w, h) rects accepted.
AC-U2 render_to_window: shape (win_h, win_w, 3); EVERY pixel outside the content is 0 (top/bottom/left/right); camera
       area == cv2.resize(view); the panel fills exactly its slot (not cut, no overflow); a window of the natural size
       gives an image bit-identical to Hud.compose (layout None and the natural rect).
AC-U3 scale 2: panel font == round(font_size * 2); panel height == 2x natural (±2 px per line); the panel is not rebuilt
       when only the stats lines change; fonts are created once per pixel size.
"""
import itertools
import os
import subprocess
import sys
import types
import unittest
from unittest import mock

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import level1_demo as app_mod  # noqa: E402
import src.inference.level1_display as disp  # noqa: E402
from src.inference.level1_core import load_level1_config  # noqa: E402

CONFIG = os.path.join(PROJECT_ROOT, "configs", "level1_realtime.json")
HUD_BASE_COMMIT = "cad8cdc"  # plan 15 lần sửa 13 M0: level1_demo.Hud before U1 (reference for scale 1.0)
CAM_W, CAM_H = 640, 480

HINT = "[Góc tay: Hơi nghiêng tay 20°]"
VIEWS = (
    ["Dòng A", "Dòng B"],
    {"committed": "xin ", "active": "chào", "text": "xin chào"},
    {"committed": "một câu rất dài " * 8, "active": "từ", "text": "x",
     "preview": {"token": "a", "prediction": "a", "confidence": 0.93, "active_if_accepted": "tà"}},
    {"committed": "mẹ ", "active": "cá", "text": "mẹ cá",
     "preview": {"token": "b", "prediction": "b", "confidence": 0.5, "active_if_accepted": ""}},
    {"committed": "", "active": "", "text": ""},
)
SMALLS = ([], [HINT, "gợi ý"], ["x", "Trạng thái: chờ", "[classifier] cửa sổ", "dòng 4"])
STATS = ([], ["p50 1"], ["p50 1", "p50 2"], ["p50 1", "p50 2", "p50 3"])
HOLDS = (0.0, 0.3, 1.0)


def _font():
    values = load_level1_config(CONFIG)["values"]
    return app_mod.find_font(None, values["font_paths"]), values["hud_font_size"]


def _hud_module_at(commit):
    """level1_demo.py at `commit` loaded from `git show` into an in-memory module (nothing written)."""
    r = subprocess.run(["git", "show", f"{commit}:level1_demo.py"], cwd=PROJECT_ROOT, capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(f"git show {commit}:level1_demo.py failed: {r.stderr.strip()}")
    name = f"_level1_demo_display_ref_{commit}"
    mod = types.ModuleType(name)
    mod.__file__ = os.path.join(PROJECT_ROOT, "level1_demo.py")
    sys.modules[name] = mod
    try:
        exec(compile(r.stdout, f"<git show {commit}:level1_demo.py>", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


def _outside_mask(layout):
    """True on every window pixel outside the content rectangle."""
    m = np.ones((layout.win_h, layout.win_w), dtype=bool)
    m[layout.y0:layout.y0 + layout.content_h, layout.x0:layout.x0 + layout.content_w] = False
    return m


def _view(seed, h=CAM_H, w=CAM_W):
    """Camera image with no zero pixel (so black bars can be told apart from the content)."""
    return np.random.default_rng(seed).integers(1, 255, (h, w, 3), dtype=np.uint8)


def _render(hud, view, text_or_view, small, stats, hold, win):
    """The window path of the app: natural panel height -> fit_layout -> render_to_window(Hud.panel_builder)."""
    ph = hud.panel_height(text_or_view, small, len(stats))
    layout = disp.fit_layout(view.shape[1], view.shape[0], ph, *win)
    return disp.render_to_window(view, hud.panel_builder(text_or_view, small), stats, hold, layout), layout


# ------------------------------------------------------------------------------------------------------------ AC-U1
class TestFitLayoutAcU1(unittest.TestCase):
    """AC-U1 fit_layout geometry."""

    def assertInside(self, L, w, h, msg=""):
        self.assertGreaterEqual(L.x0, 0, msg)
        self.assertGreaterEqual(L.y0, 0, msg)
        self.assertLessEqual(L.x0 + L.content_w, w, msg)
        self.assertLessEqual(L.y0 + L.content_h, h, msg)
        self.assertEqual((L.win_w, L.win_h), (w, h), msg)
        # camera and panel stacked inside the content, full content width
        cx, cy, cw, ch = L.cam_rect
        px, py, pw, ph = L.panel_rect
        self.assertEqual((cx, cy, cw), (L.x0, L.y0, L.content_w), msg)
        self.assertEqual((px, py, pw), (L.x0, L.y0 + ch, L.content_w), msg)
        self.assertEqual(ch + ph, L.content_h, msg)
        self.assertGreaterEqual(ch, 1, msg)
        self.assertGreaterEqual(ph, 0, msg)

    def test_u1_scale_two(self):
        L = disp.fit_layout(640, 480, 200, 1280, 1360)
        self.assertEqual(L.scale, 2.0)
        self.assertEqual((L.content_w, L.content_h, L.x0, L.y0), (1280, 1360, 0, 0))
        self.assertEqual(L.cam_rect, (0, 0, 1280, 960))
        self.assertEqual(L.panel_rect, (0, 960, 1280, 400))

    def test_u1_scale_1080p(self):
        L = disp.fit_layout(640, 480, 200, 1920, 1080)
        self.assertAlmostEqual(L.content_h, 1080, delta=1)
        self.assertAlmostEqual(L.x0, (1920 - L.content_w) // 2, delta=1)
        self.assertEqual(L.y0, 0)
        self.assertGreater(L.x0, 0)
        self.assertInside(L, 1920, 1080)

    def test_u1_tall_window(self):
        L = disp.fit_layout(640, 480, 200, 600, 2000)
        self.assertEqual(L.content_w, 600)
        self.assertEqual(L.x0, 0)
        self.assertGreater(L.y0, 0)
        self.assertEqual(L.y0, (2000 - L.content_h) // 2)
        self.assertInside(L, 600, 2000)

    def test_u1_invalid_windows(self):
        natural = disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 200), 640, 680)
        for inv in [((-1, -1, -1, -1),), ((0, 0),), (None,), (None, None), ((0, 0, 0, 0),), ((-1, -1),), ((1920,),),
                    ((1, 2, 3),), (0, 1080), (1920, 0), (1920, -5), (-1, -1), ("abc", 1080), (float("nan"), 1080),
                    ((10, 20, 0, 1080),), ((10, 20, 1920, -1),), (1920, None)]:
            with self.subTest(win=inv):
                L = disp.fit_layout(640, 480, 200, *inv)
                self.assertEqual(L, natural)
                self.assertEqual(L.scale, 1.0)

    def test_u1_rect_four_tuple_is_x_y_w_h(self):
        ref = disp.fit_layout(640, 480, 200, 1920, 1080)
        self.assertEqual(disp.fit_layout(640, 480, 200, (10, 20, 1920, 1080)), ref)
        self.assertEqual(disp.fit_layout(640, 480, 200, [0, 0, 1920, 1080]), ref)
        self.assertEqual(disp.fit_layout(640, 480, 200, (1920, 1080)), ref)
        self.assertNotEqual(disp.fit_layout(640, 480, 200, (1920, 1080, 10, 20)), ref)

    def test_u1_layout_equality_compares_every_field(self):
        a = disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 200), 640, 680)
        self.assertEqual(a, disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 200), 640, 680))
        self.assertNotEqual(a, disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 200), 641, 680))
        self.assertNotEqual(a, disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 200), 640, 681))
        self.assertNotEqual(a, disp.DisplayLayout(1.0, 640, 680, 0, 0, (0, 0, 640, 480), (0, 480, 640, 201), 640, 680))

    def test_u1_unpacking(self):
        L = disp.fit_layout(640, 480, 200, 1280, 1360)
        scale, cw, ch, x0, y0, cr, pr = L
        self.assertEqual((scale, cw, ch, x0, y0), (2.0, 1280, 1360, 0, 0))
        self.assertEqual(cr, (0, 0, 1280, 960))
        self.assertEqual(pr, (0, 960, 1280, 400))

    def test_u1_grid_scan(self):
        """Plan grid 200..4000 step 175 in both dimensions (cam 640x480, panel 200)."""
        cam_w, cam_h, panel_h = 640, 480, 200
        ratio = cam_w / (cam_h + panel_h)
        for w in range(200, 4001, 175):
            for h in range(200, 4001, 175):
                L = disp.fit_layout(cam_w, cam_h, panel_h, w, h)
                msg = f"w={w} h={h} {L}"
                self.assertInside(L, w, h, msg)
                touch_w = abs(L.content_w - w) <= 1
                touch_h = abs(L.content_h - h) <= 1
                self.assertTrue(touch_w or touch_h, msg)
                self.assertEqual(L.x0, (w - L.content_w) // 2, msg)  # centred: bars only on one opposite pair
                self.assertEqual(L.y0, (h - L.content_h) // 2, msg)
                self.assertTrue(L.x0 == 0 or L.y0 == 0, msg)
                self.assertLessEqual(abs((L.content_w / L.content_h) / ratio - 1.0), 0.01, msg)

    def test_u1_wide_grid_inside_window(self):
        """The cases found by the bridge probe (camera sizes x panel heights x windows): never outside the window."""
        self.assertInside(disp.fit_layout(640, 480, 96, 394, 333), 394, 333)
        for (cam_w, cam_h) in [(640, 480), (1280, 720), (320, 240)]:
            for panel_h in range(40, 400, 7):
                for w in range(150, 4001, 61):
                    for h in range(150, 4001, 61):
                        L = disp.fit_layout(cam_w, cam_h, panel_h, w, h)
                        if (L.x0 < 0 or L.y0 < 0 or L.x0 + L.content_w > w or L.y0 + L.content_h > h
                                or L.cam_rect[3] + L.panel_rect[3] != L.content_h):
                            self.fail(f"outside window: cam {cam_w}x{cam_h} panel {panel_h} win {w}x{h} {L}")

    def test_u1_tiny_windows_valid(self):
        for (w, h) in [(1, 1), (1, 4000), (4000, 1), (2, 3), (7, 5)]:
            L = disp.fit_layout(640, 480, 200, w, h)
            self.assertInside(L, w, h, f"{w}x{h} {L}")
            self.assertGreaterEqual(L.content_w, 1)
            self.assertGreaterEqual(L.content_h, 1)


# ------------------------------------------------------------------------------------------------------------ AC-U2
class TestRenderToWindowAcU2(unittest.TestCase):
    """AC-U2 render_to_window."""

    @classmethod
    def setUpClass(cls):
        cls.font_path, cls.font_size = _font()

    def hud(self):
        return app_mod.Hud(self.font_path, self.font_size)

    def test_u2_shape_and_every_outside_pixel_zero(self):
        view = _view(1)
        stats = ["p50 (ms) mp 15.0 | a very long stats line that is wider than the camera image " * 3,
                 "p50 (ms) sign 30.0 | dropped 0"]
        for win in [(1920, 1080), (1280, 1360), (1000, 3000), (3840, 2160), (800, 600), (2560, 1080), (394, 333),
                    (600, 2000), (333, 1500), (1500, 333)]:
            for tv, hold in [(VIEWS[1], 1.0), (VIEWS[2], 0.5), (VIEWS[0], 0.0)]:
                with self.subTest(win=win, view=type(tv).__name__, hold=hold):
                    out, L = _render(self.hud(), view, tv, [HINT, "gợi ý"], stats, hold, win)
                    self.assertEqual(out.shape, (win[1], win[0], 3))
                    self.assertEqual(int(np.count_nonzero(out[_outside_mask(L)])), 0)
                    # bars on top/bottom and left/right explicitly
                    self.assertEqual(int(np.count_nonzero(out[:L.y0])), 0)
                    self.assertEqual(int(np.count_nonzero(out[L.y0 + L.content_h:])), 0)
                    self.assertEqual(int(np.count_nonzero(out[:, :L.x0])), 0)
                    self.assertEqual(int(np.count_nonzero(out[:, L.x0 + L.content_w:])), 0)

    def test_u2_camera_area_resized(self):
        view = np.arange(CAM_H * CAM_W * 3, dtype=np.uint64).astype(np.uint8).reshape((CAM_H, CAM_W, 3))
        for win in [(1920, 1080), (1280, 1360), (600, 2000), (3840, 2160)]:
            with self.subTest(win=win):
                out, L = _render(self.hud(), view, VIEWS[1], [], [], 0.0, win)
                x, y, w, h = L.cam_rect
                expected = cv2.resize(view, (w, h), interpolation=cv2.INTER_LINEAR)
                self.assertTrue(np.array_equal(out[y:y + h, x:x + w], expected))

    def test_u2_panel_fills_its_slot_not_cut(self):
        """The panel is built at the slot size: the slot of the window equals the panel built for it (no hold bar, stats
        rows reserved but empty), and the text rows of the panel end inside the slot."""
        view = _view(2)
        for win in [(1920, 1080), (1280, 1360), (1000, 3000), (3840, 2160), (800, 600), (394, 333), (2560, 1440)]:
            for tv, small, n_stats in [(VIEWS[1], [HINT, "gợi ý"], 2), (VIEWS[0], SMALLS[2], 3), (VIEWS[3], [], 0)]:
                with self.subTest(win=win, small=len(small), n_stats=n_stats):
                    hud = self.hud()
                    out, L = _render(hud, view, tv, small, [""] * n_stats, 0.0, win)
                    x, y, w, h = L.panel_rect
                    self.assertLessEqual(y + h, win[1])
                    ref = app_mod.Hud(self.font_path, self.font_size)._build(w, tv, small, n_stats, L.scale, h)
                    self.assertEqual(ref.shape, (h, w, 3))
                    self.assertTrue(np.array_equal(out[y:y + h, x:x + w], ref))
                    line_h, small_h = hud.line_steps(L.scale)
                    num_big = 1 if isinstance(tv, dict) else len(tv)
                    rows_end = int(hud.PAD_TOP * L.scale) + line_h * num_big + small_h * (len(small) + n_stats)
                    self.assertLessEqual(rows_end, h)

    def test_u2_text_rows_fit_slot_on_grid(self):
        hud = self.hud()
        for tv, small, n_stats in itertools.product(VIEWS[:2], SMALLS, range(4)):
            ph = hud.panel_height(tv, small, n_stats)
            num_big = 1 if isinstance(tv, dict) else len(tv)
            for w in range(200, 4001, 175):
                for h in range(200, 4001, 175):
                    L = disp.fit_layout(CAM_W, CAM_H, ph, w, h)
                    line_h, small_h = hud.line_steps(L.scale)
                    rows_end = int(hud.PAD_TOP * L.scale) + line_h * num_big + small_h * (len(small) + n_stats)
                    if rows_end > L.panel_rect[3]:
                        self.fail(f"panel rows cut: win {w}x{h} ph {ph} rows_end {rows_end} slot {L.panel_rect[3]}")

    def test_u2_never_raises_on_rounding_edge_windows(self):
        """Windows where rounding the camera and the panel separately exceeds the window (the 7ae0040 crash, e.g.
        panel 96 in 394x333): the render has the window shape and nothing outside the content."""
        view = _view(3)
        cases = [(96, 394, 333)]
        for ph in range(40, 400, 7):
            for w in range(150, 4001, 61):
                for h in range(150, 4001, 61):
                    s = min(w / CAM_W, h / (CAM_H + ph))
                    if round(CAM_W * s) > w or round(CAM_H * s) + round(ph * s) > h:
                        cases.append((ph, w, h))
        self.assertGreater(len(cases), 20)

        def solid_panel(width, height, scale, n_stats):  # protocol-conforming panel: bright, fills its slot
            return np.full((height, width, 3), 200, np.uint8), max(1, int(14 * scale))

        for ph, w, h in cases[:40]:
            with self.subTest(ph=ph, w=w, h=h):
                L = disp.fit_layout(CAM_W, CAM_H, ph, w, h)
                out = disp.render_to_window(view, solid_panel, ["t", "u"], 1.0, L)
                self.assertEqual(out.shape, (h, w, 3))
                self.assertEqual(int(np.count_nonzero(out[_outside_mask(L)])), 0)
                self.assertTrue((out[L.panel_rect[1] + L.panel_rect[3] - 1, L.x0] != 0).any())  # panel bottom row drawn
        # real Hud panels at the same kind of windows
        hud = self.hud()
        for tv, small, n_stats in [(VIEWS[1], [HINT, "gợi ý"], 2), (VIEWS[0], SMALLS[2], 3)]:
            for _, w, h in cases[:8]:
                L = disp.fit_layout(CAM_W, CAM_H, hud.panel_height(tv, small, n_stats), w, h)
                out = disp.render_to_window(view, hud.panel_builder(tv, small), ["t"] * n_stats, 0.5, L)
                self.assertEqual(out.shape, (h, w, 3))
                self.assertEqual(int(np.count_nonzero(out[_outside_mask(L)])), 0)

    def test_u2_natural_equals_hud_compose(self):
        """Window == natural size: bit-identical to Hud.compose for layout None and for the natural rect, on list / dict
        views, preview, hint line, 0-3 stats lines, hold 0 / 0.3 / 1."""
        n = 0
        for i, (tv, small, stats, hold) in enumerate(itertools.product(VIEWS, SMALLS, STATS, HOLDS)):
            view = _view(100 + i)
            expected = self.hud().compose(view.copy(), tv, small, hold, stats)
            ph = expected.shape[0] - CAM_H
            for win in [(None,), ((0, 0, CAM_W, CAM_H + ph),), ((37, 52, CAM_W, CAM_H + ph),), (CAM_W, CAM_H + ph)]:
                hud = self.hud()
                self.assertEqual(hud.panel_height(tv, small, len(stats)), ph)
                layout = disp.fit_layout(CAM_W, CAM_H, ph, *win)
                self.assertEqual(layout.scale, 1.0)
                out = disp.render_to_window(view.copy(), hud.panel_builder(tv, small), stats, hold, layout)
                n += 1
                if out.shape != expected.shape or not np.array_equal(out, expected):
                    self.fail(f"differs from Hud.compose: view={tv!r} small={small} stats={stats} hold={hold} "
                              f"win={win}")
        self.assertEqual(n, len(VIEWS) * len(SMALLS) * len(STATS) * len(HOLDS) * 4)

    def test_u2_hud_scale_one_identical_to_m0_hud(self):
        """The refactored Hud (scale parameter) draws exactly what the Hud of the M0 commit drew."""
        ref_mod = _hud_module_at(HUD_BASE_COMMIT)
        for i, (tv, small, stats, hold) in enumerate(itertools.product(VIEWS, SMALLS, STATS, HOLDS)):
            view = _view(500 + i)
            new = self.hud().compose(view.copy(), tv, small, hold, stats)
            ref = ref_mod.Hud(self.font_path, self.font_size).compose(view.copy(), tv, small, hold, stats)
            if new.shape != ref.shape or not np.array_equal(new, ref):
                self.fail(f"Hud.compose differs from {HUD_BASE_COMMIT}: view={tv!r} small={small} stats={stats}")
        for width in (640, 300, 1280):
            for tv in VIEWS:
                new = self.hud()._build(width, tv, [HINT], 2)
                ref = ref_mod.Hud(self.font_path, self.font_size)._build(width, tv, [HINT], 2)
                self.assertTrue(np.array_equal(new, ref), (width, tv))

    def test_u2_builder_protocol_shape_checked(self):
        view = _view(4)
        L = disp.fit_layout(CAM_W, CAM_H, 100, 1280, 1000)
        bad = (lambda width, height, scale, n: (np.zeros((height + 3, width, 3), np.uint8), 1))
        with self.assertRaises(ValueError):
            disp.render_to_window(view, bad, [], 0.0, L)


# ------------------------------------------------------------------------------------------------------------ AC-U3
class TestScaledPanelAcU3(unittest.TestCase):
    """AC-U3 scaled panel: font size, height, caches."""

    @classmethod
    def setUpClass(cls):
        cls.font_path, cls.font_size = _font()

    def test_u3_scale_two_font_and_height(self):
        for tv, small, stats in [(VIEWS[1], [HINT], ["s1", "s2"]), (VIEWS[0], SMALLS[2], ["s1", "s2", "s3"]),
                                 (VIEWS[2], [], [])]:
            with self.subTest(view=type(tv).__name__, small=len(small), stats=len(stats)):
                hud = app_mod.Hud(self.font_path, self.font_size)
                h1 = hud.compose(_view(7), tv, small, 0.0, stats).shape[0] - CAM_H
                self.assertEqual(hud.panel_height(tv, small, len(stats)), h1)
                with mock.patch.object(hud, "_build", wraps=hud._build) as build:
                    out, L = _render(hud, _view(7), tv, small, stats, 0.0, (2 * CAM_W, 2 * (CAM_H + h1)))
                self.assertEqual(L.scale, 2.0)
                self.assertEqual(build.call_count, 1)
                self.assertEqual(hud.font_px(L.scale), round(self.font_size * 2))
                font, small_font = hud._fonts_at(L.scale)
                self.assertEqual(font.size, round(self.font_size * 2))
                self.assertEqual(small_font.size, max(1, int(round(self.font_size * 2) * 2 / 3)))
                n_lines = (1 if isinstance(tv, dict) else len(tv)) + len(small) + len(stats)
                h2 = L.panel_rect[3]
                self.assertLessEqual(abs(h2 - 2 * h1), 2 * n_lines)  # contract: ±2 px per line
                self.assertLessEqual(abs(hud.panel_height(tv, small, len(stats), 2.0) - 2 * h1), 2 * n_lines)

    def test_u3_no_rebuild_when_only_stats_change(self):
        hud = app_mod.Hud(self.font_path, self.font_size)
        view = _view(8)
        with mock.patch.object(hud, "_build", wraps=hud._build) as build:
            _render(hud, view, VIEWS[1], [HINT], ["stat frame 1", "line 2"], 0.0, (1920, 1080))
            self.assertEqual(build.call_count, 1)
            _render(hud, view, VIEWS[1], [HINT], ["stat frame 2 new values", "line 2 updated"], 0.4, (1920, 1080))
            _render(hud, view, VIEWS[1], [HINT], ["stat frame 3", "x"], 1.0, (1920, 1080))
            self.assertEqual(build.call_count, 1, "panel rebuilt although only the stats lines changed")
            _render(hud, view, {"committed": "xin ", "active": "chà", "text": "xin chà"}, [HINT], ["a", "b"], 0.0,
                    (1920, 1080))
            self.assertEqual(build.call_count, 2, "panel not rebuilt when the text changed")
            _render(hud, view, {"committed": "xin ", "active": "chà", "text": "xin chà"}, [HINT], ["a", "b"], 0.0,
                    (1280, 1360))
            self.assertEqual(build.call_count, 3, "panel not rebuilt when the window size changed")

    def test_u3_fonts_created_once_per_pixel_size(self):
        from PIL import ImageFont
        hud = app_mod.Hud(self.font_path, self.font_size)
        view = _view(9)
        with mock.patch.object(ImageFont, "truetype", wraps=ImageFont.truetype) as tt:
            _render(hud, view, VIEWS[1], [HINT], ["a"], 0.0, (1920, 1080))
            first = tt.call_count
            self.assertEqual(first, 2)  # main + small font at the new pixel size
            for k in range(5):
                _render(hud, view, {"committed": f"câu {k} ", "active": "từ", "text": "x"}, [HINT], ["a"], 0.0,
                        (1920, 1080))
            self.assertEqual(tt.call_count, first)
            _render(hud, view, VIEWS[1], [HINT], ["a"], 0.0, (CAM_W, CAM_H + hud.panel_height(VIEWS[1], [HINT], 1)))
            self.assertEqual(tt.call_count, first)  # scale 1.0 uses the fonts made by __init__


# ------------------------------------------------------------------------------------------------------- E4 item 5
class TestRenderToWindowInputUnchanged(unittest.TestCase):
    """Plan 15-lan-sua-13a §3.2 item 5 (exception E4, dynamic part): render_to_window never modifies the display image
    it is given and returns a new image (no shared memory), on the copy branch (natural layout) and on the resize
    branch (1920x1080 window)."""

    @classmethod
    def setUpClass(cls):
        cls.font_path, cls.font_size = _font()

    def _check(self, layout, resized, builder, stats, hold, seed):
        view = _view(seed)
        before = view.copy()
        out = disp.render_to_window(view, builder, stats, hold, layout)
        self.assertTrue(np.array_equal(view, before))
        self.assertFalse(np.shares_memory(out, view))
        self.assertEqual(out.shape, (layout.win_h, layout.win_w, 3))
        x, y, w, h = layout.cam_rect
        self.assertEqual((w, h) != (view.shape[1], view.shape[0]), resized)  # the branch under test is taken
        expected = cv2.resize(before, (w, h), interpolation=cv2.INTER_LINEAR) if resized else before
        self.assertTrue(np.array_equal(out[y:y + h, x:x + w], expected))
        # a read-only view: any write into the input would raise
        ro = before.copy()
        ro.flags.writeable = False
        out_ro = disp.render_to_window(ro, builder, stats, hold, layout)
        self.assertTrue(np.array_equal(out_ro, out))
        self.assertTrue(np.array_equal(ro, before))

    def test_e4_input_unchanged_copy_and_resize_branch(self):
        hud = app_mod.Hud(self.font_path, self.font_size)

        def solid_panel(width, height, scale, n_stats):
            return np.full((height, width, 3), 200, np.uint8), max(1, int(14 * scale))

        for tv, small, stats, hold in [(VIEWS[1], [HINT, "gợi ý"], ["p50 1", "p50 2"], 0.3), (VIEWS[0], [], [], 1.0),
                                       (VIEWS[2], SMALLS[2], ["p50 1"], 0.0)]:
            ph = hud.panel_height(tv, small, len(stats))
            for win, resized in [((None,), False), ((CAM_W, CAM_H + ph), False), ((1920, 1080), True)]:
                layout = disp.fit_layout(CAM_W, CAM_H, ph, *win)
                for bname, builder in [("hud", hud.panel_builder(tv, small)), ("solid", solid_panel)]:
                    with self.subTest(view=type(tv).__name__, win=win, builder=bname):
                        self._check(layout, resized, builder, stats, hold, 900 + len(stats))



# ------------------------------------------------------------------------------------------------------------ AC-U7
class TestU2OverlaysScaled(unittest.TestCase):
    """AC-U7 (U2a, TB-1): scaled hold bar and live stats lines in render_to_window."""

    CAM_W, CAM_H = 640, 480
    PANEL_H = 200
    BG = (40, 40, 40)
    WINDOWS = ((1920, 1080), (1280, 1360))

    def setUp(self):
        self.view = np.full((self.CAM_H, self.CAM_W, 3), 90, dtype=np.uint8)

    def _panel_builder(self, w: int, h: int, scale: float, n_stats: int):
        panel = np.full((h, w, 3), self.BG, dtype=np.uint8)
        return panel, disp.scaled_px(18, scale)

    def test_u7_h1_hold_full_scaled(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                s = L.scale
                px, py, cw, _ = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]
                canvas = disp.render_to_window(self.view, self._panel_builder, [], 1.0, L)
                bar = canvas[py : py + disp.scaled_px(3, s), px : px + cw]
                self.assertTrue(np.all(bar == disp.HOLD_BAR_BGR))

    def test_u7_h2_hold_half_scaled(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                s = L.scale
                px, py, cw, _ = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]
                canvas = disp.render_to_window(self.view, self._panel_builder, [], 0.5, L)
                bar = canvas[py : py + disp.scaled_px(3, s), px : px + int(cw * 0.5)]
                self.assertTrue(np.all(bar == disp.HOLD_BAR_BGR))
                rest = canvas[py, px + int(cw * 0.5) + 2 : px + cw]
                has_bar = np.any(np.all(rest == disp.HOLD_BAR_BGR, axis=-1))
                self.assertFalse(has_bar)

    def test_u7_h3_hold_height_exact_scaled(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                s = L.scale
                px, py, cw, _ = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]
                canvas = disp.render_to_window(self.view, self._panel_builder, [], 1.0, L)
                row = canvas[py + disp.scaled_px(3, s) + 1, px : px + cw]
                has_bar = np.any(np.all(row == disp.HOLD_BAR_BGR, axis=-1))
                self.assertFalse(has_bar)

    def test_u7_h4_hold_zero_no_bar(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                canvas = disp.render_to_window(self.view, self._panel_builder, [], 0.0, L)
                has_bar = np.any(np.all(canvas == disp.HOLD_BAR_BGR, axis=-1))
                self.assertFalse(has_bar)

    def test_u7_s1_stats_bottom_half_and_color(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                px, py, cw, ph = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]
                canvas = disp.render_to_window(self.view, self._panel_builder, ["fps 30.0 | hud 1.2ms"], 0.0, L)
                panel_region = canvas[py : py + ph, px : px + cw]
                diff = np.any(panel_region != self.BG, axis=-1)
                d_rows, _ = np.where(diff)
                self.assertGreater(len(d_rows), 0)
                self.assertTrue(np.all(d_rows + py >= py + ph // 2))
                d_pixels = panel_region[diff]
                channel_diff = np.abs(d_pixels.astype(np.int32) - np.array(disp.STATS_BGR, dtype=np.int32))
                max_channel_diff = np.max(channel_diff, axis=1)
                self.assertTrue(np.any(max_channel_diff <= 8))

    def test_u7_s2_stats_empty_no_diff(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                px, py, cw, ph = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]
                canvas = disp.render_to_window(self.view, self._panel_builder, [], 0.0, L)
                panel_region = canvas[py : py + ph, px : px + cw]
                diff = np.any(panel_region != self.BG, axis=-1)
                self.assertEqual(int(np.count_nonzero(diff)), 0)

    def test_u7_s3_stats_font_height_scaled(self):
        stats = ["fps 30.0 | hud 1.2ms"]

        L_nat = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H)
        px_nat, py_nat, cw_nat, ph_nat = L_nat.panel_rect[0], L_nat.panel_rect[1], L_nat.content_w, L_nat.panel_rect[3]
        out_nat = disp.render_to_window(self.view, self._panel_builder, stats, 0.0, L_nat)
        panel_nat = out_nat[py_nat : py_nat + ph_nat, px_nat : px_nat + cw_nat]
        diff_nat = np.any(panel_nat != self.BG, axis=-1)
        rows_nat = np.where(diff_nat)[0]
        span_nat = int(rows_nat.max() - rows_nat.min() + 1)

        L_2 = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, 1280, 1360)
        px_2, py_2, cw_2, ph_2 = L_2.panel_rect[0], L_2.panel_rect[1], L_2.content_w, L_2.panel_rect[3]
        out_2 = disp.render_to_window(self.view, self._panel_builder, stats, 0.0, L_2)
        panel_2 = out_2[py_2 : py_2 + ph_2, px_2 : px_2 + cw_2]
        diff_2 = np.any(panel_2 != self.BG, axis=-1)
        rows_2 = np.where(diff_2)[0]
        span_2 = int(rows_2.max() - rows_2.min() + 1)

        ratio = span_2 / span_nat
        self.assertGreaterEqual(ratio, 1.6)
        self.assertLessEqual(ratio, 2.4)

    def test_u7_s4_outside_pixels_zero(self):
        for W, H in self.WINDOWS:
            with self.subTest(win=(W, H)):
                L = disp.fit_layout(self.CAM_W, self.CAM_H, self.PANEL_H, W, H)
                canvas = disp.render_to_window(self.view, self._panel_builder, ["fps 30.0 | hud 1.2ms"], 1.0, L)
                self.assertEqual(int(np.count_nonzero(canvas[_outside_mask(L)])), 0)


if __name__ == "__main__":
    unittest.main()

