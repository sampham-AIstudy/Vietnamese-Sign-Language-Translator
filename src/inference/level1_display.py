"""
Level 1 desktop app: scaled / fullscreen window layout and render (plan 15 lần sửa 13, step U1).

Pure geometry + drawing, no window calls. The window content is the DISPLAY image (landmarks drawn, mirrored for
display; never the frame given to MediaPipe) with the HUD text panel stacked below it, scaled by one factor and
centred in the window (black bars on one pair of opposite edges only).

One source for the panel: the text panel is drawn by `level1_demo.Hud` (its `panel_builder` is the PanelBuilder of
`render_to_window`); this module only places it. The hold bar and the live stats lines are drawn by
`draw_panel_overlays`, used both by `Hud.compose` (natural size, scale 1.0) and by `render_to_window`.
"""
import dataclasses
from typing import Any, Callable, Optional, Sequence, Tuple

import cv2
import numpy as np

Rect = Tuple[int, int, int, int]  # (x, y, w, h) in window pixels

# PanelBuilder protocol (the only one): builder(width, height, scale, n_stats) -> (panel BGR uint8 of shape
# (height, width, 3), stats line step in px). `height` is the panel slot of the layout, `scale` the layout scale,
# `n_stats` the number of live stats lines whose rows the panel keeps free at its bottom.
PanelBuilder = Callable[[int, int, float, int], Tuple[np.ndarray, int]]

# Overlays at natural size (scale 1.0), the values Hud.compose always drew (plan 15 B3 / lần sửa 6): hold bar on the
# top edge of the panel, live stats lines (ASCII, cv2 Hershey font) on the reserved bottom rows of the panel.
HOLD_BAR_BGR = (0, 200, 0)
HOLD_BAR_HEIGHT = 3
STATS_BGR = (160, 255, 160)
STATS_FONT_SCALE = 0.45
STATS_THICKNESS = 1
STATS_X = 8
STATS_BOTTOM_MARGIN = 10


def scaled_px(value: int, scale: float) -> int:
    """A natural-size pixel distance at `scale`, rounded down (scale 1.0 gives `value` unchanged)."""
    return int(value * scale)


@dataclasses.dataclass(frozen=True)
class DisplayLayout:
    """Placement of the content (camera image + panel) in the window. Rects are (x, y, w, h) in window pixels; the
    camera rect is on top, the panel rect right below it, both of width `content_w`. Equality compares every field
    (window size included). Iteration yields the 7 fields of the plan signature (scale .. panel_rect)."""

    scale: float
    content_w: int
    content_h: int
    x0: int
    y0: int
    cam_rect: Rect
    panel_rect: Rect
    win_w: int
    win_h: int

    def __iter__(self):
        return iter((self.scale, self.content_w, self.content_h, self.x0, self.y0, self.cam_rect, self.panel_rect))


def _window_size(win_w: Any, win_h: Any) -> Optional[Tuple[int, int]]:
    """(w, h) of a valid window, else None. Accepts (w, h) as two numbers, a 2-sequence (w, h) or the 4-sequence
    (x, y, w, h) of cv2.getWindowImageRect; None, non-numbers and sizes <= 0 (e.g. (-1, -1, -1, -1)) are invalid."""
    if isinstance(win_w, (tuple, list)):
        if win_h is not None:
            return None
        if len(win_w) == 4:
            size = (win_w[2], win_w[3])
        elif len(win_w) == 2:
            size = (win_w[0], win_w[1])
        else:
            return None
    else:
        size = (win_w, win_h)
    try:
        w, h = int(size[0]), int(size[1])
    except (TypeError, ValueError, OverflowError):
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def _natural_layout(cam_w: int, cam_h: int, panel_h: int) -> DisplayLayout:
    return DisplayLayout(1.0, cam_w, cam_h + panel_h, 0, 0, (0, 0, cam_w, cam_h), (0, cam_h, cam_w, panel_h),
                         cam_w, cam_h + panel_h)


def _round_ratio(value: int, num: int, den: int) -> int:
    """round(value * num / den), halves up, in integers (no float error at exact window edges)."""
    return (2 * value * num + den) // (2 * den)


def fit_layout(cam_w: int, cam_h: int, panel_h: int, win_w: Any = None, win_h: Any = None) -> DisplayLayout:
    """Content = camera image (cam_w x cam_h) with the panel (cam_w x panel_h) below it, scaled by
    scale = min(win_w / cam_w, win_h / (cam_h + panel_h)) and centred in the window.

    Rounding: the scale is kept as an exact ratio; the content width and the TOTAL content height are each rounded
    once (so they never exceed the window), the camera height is rounded down and the panel gets the rest, so
    camera + panel == content height and x0, y0 >= 0, x0 + content_w <= win_w, y0 + content_h <= win_h always.
    Invalid window (see _window_size) => scale 1.0 at the natural size (the old window, Hud.compose)."""
    cam_w, cam_h, panel_h = int(cam_w), int(cam_h), int(panel_h)
    if cam_w <= 0 or cam_h <= 0 or panel_h < 0:
        raise ValueError(f"fit_layout: camera size must be > 0 and panel height >= 0, got {cam_w}x{cam_h}, {panel_h}")
    natural_h = cam_h + panel_h
    size = _window_size(win_w, win_h)
    if size is None:
        return _natural_layout(cam_w, cam_h, panel_h)
    w, h = size
    # scale = num / den: limited by the width when w / cam_w <= h / natural_h
    num, den = (w, cam_w) if w * natural_h <= h * cam_w else (h, natural_h)
    content_w = min(w, max(1, _round_ratio(cam_w, num, den)))
    content_h = min(h, max(1, _round_ratio(natural_h, num, den)))
    cam_sh = min(content_h, max(1, cam_h * num // den))
    panel_sh = content_h - cam_sh
    x0 = (w - content_w) // 2
    y0 = (h - content_h) // 2
    return DisplayLayout(num / den, content_w, content_h, x0, y0, (x0, y0, content_w, cam_sh),
                         (x0, y0 + cam_sh, content_w, panel_sh), w, h)


def draw_panel_overlays(content: np.ndarray, panel_top: int, hold_progress: float, stats_lines: Sequence[str],
                        stats_step: int, scale: float = 1.0) -> None:
    """Draws, in place on `content` (camera image + panel, nothing else), the hold bar on the top edge of the panel
    and the live stats lines on the bottom rows of the panel, every distance scaled by `scale`. Drawing is clipped
    to `content`, so nothing reaches the black bars of the window."""
    w = content.shape[1]
    if hold_progress > 0:
        cv2.rectangle(content, (0, panel_top), (int(w * hold_progress), panel_top + scaled_px(HOLD_BAR_HEIGHT, scale)),
                      HOLD_BAR_BGR, -1)
    n = len(stats_lines)
    x = scaled_px(STATS_X, scale)
    thickness = max(STATS_THICKNESS, int(round(STATS_THICKNESS * scale)))
    for i, line in enumerate(stats_lines):
        base = content.shape[0] - scaled_px(STATS_BOTTOM_MARGIN, scale) - (n - 1 - i) * stats_step
        cv2.putText(content, line, (x, base), cv2.FONT_HERSHEY_SIMPLEX, STATS_FONT_SCALE * scale, STATS_BGR,
                    thickness, cv2.LINE_AA)


def render_to_window(view_bgr: np.ndarray, panel_builder: PanelBuilder, stats_lines: Sequence[str],
                     hold_progress: float, layout: DisplayLayout) -> np.ndarray:
    """Window image (layout.win_h, layout.win_w, 3): black, with the display image resized (cv2.INTER_LINEAR) into
    layout.cam_rect, the panel built by `panel_builder` at the exact size of layout.panel_rect (text drawn at the
    scaled font size, not an enlarged image), then the hold bar and stats lines. Pixels outside the content stay 0.
    A layout of the natural size gives the image of Hud.compose (same inputs).

    Raises ValueError only when `panel_builder` breaks its protocol (panel not of the slot size)."""
    stats_lines = list(stats_lines)
    canvas = np.zeros((layout.win_h, layout.win_w, 3), dtype=np.uint8)
    content = canvas[layout.y0:layout.y0 + layout.content_h, layout.x0:layout.x0 + layout.content_w]
    cam_h = layout.cam_rect[3]
    panel_h = layout.panel_rect[3]
    width = layout.content_w
    if view_bgr.shape[:2] == (cam_h, width):
        content[:cam_h] = view_bgr
    else:
        content[:cam_h] = cv2.resize(view_bgr, (width, cam_h), interpolation=cv2.INTER_LINEAR)
    if panel_h > 0:
        panel, stats_step = panel_builder(width, panel_h, layout.scale, len(stats_lines))
        if panel.shape != (panel_h, width, 3):
            raise ValueError(f"panel_builder returned shape {panel.shape}, layout slot is {(panel_h, width, 3)}")
        content[cam_h:] = panel
        draw_panel_overlays(content, cam_h, hold_progress, stats_lines, stats_step, layout.scale)
    return canvas
