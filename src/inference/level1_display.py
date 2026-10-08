"""
Level 1 scaled display layout and rendering module (plan 15 lần sửa 13 U1).
Pure computation and rendering for adaptive OpenCV windows, preserving aspect ratio,
centering content with letterboxing/pillarboxing, and font-scalable HUD panel caching.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import inspect
import re
import numpy as np
import cv2


class DisplayLayout:
    """Calculated layout for fitting camera frame + HUD panel into a target window.

    Attributes:
        scale: Scaling factor applied to both camera frame and HUD panel.
        content_w: Scaled width of content (camera and panel).
        content_h: Total scaled height of content (camera height + panel height).
        x0: Horizontal offset of content from the left edge of the window.
        y0: Vertical offset of content from the top edge of the window.
        cam_rect: (x, y, w, h) bounding rectangle of the scaled camera frame.
        panel_rect: (x, y, w, h) bounding rectangle of the scaled HUD panel.
        win_w: Width of the window canvas.
        win_h: Height of the window canvas.
    """

    def __init__(
        self,
        scale: float,
        content_w: int,
        content_h: int,
        x0: int,
        y0: int,
        cam_rect: Tuple[int, int, int, int],
        panel_rect: Tuple[int, int, int, int],
        win_w: Optional[int] = None,
        win_h: Optional[int] = None,
    ):
        self.scale = float(scale)
        self.content_w = int(content_w)
        self.content_h = int(content_h)
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.cam_rect = tuple(cam_rect)
        self.panel_rect = tuple(panel_rect)
        self.win_w = int(win_w) if win_w is not None else int(content_w + 2 * x0)
        self.win_h = int(win_h) if win_h is not None else int(content_h + 2 * y0)

    def __iter__(self):
        """Allows unpacking as 7-tuple: scale, content_w, content_h, x0, y0, cam_rect, panel_rect."""
        return iter((
            self.scale,
            self.content_w,
            self.content_h,
            self.x0,
            self.y0,
            self.cam_rect,
            self.panel_rect,
        ))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DisplayLayout):
            return False
        return (
            abs(self.scale - other.scale) < 1e-9
            and self.content_w == other.content_w
            and self.content_h == other.content_h
            and self.x0 == other.x0
            and self.y0 == other.y0
            and self.cam_rect == other.cam_rect
            and self.panel_rect == other.panel_rect
        )

    def __repr__(self) -> str:
        return (
            f"DisplayLayout(scale={self.scale}, content_w={self.content_w}, "
            f"content_h={self.content_h}, x0={self.x0}, y0={self.y0}, "
            f"cam_rect={self.cam_rect}, panel_rect={self.panel_rect})"
        )


def fit_layout(
    cam_w: int,
    cam_h: int,
    panel_h: int,
    win_w: Any = None,
    win_h: Any = None,
) -> DisplayLayout:
    """Computes a centered, aspect-ratio-preserving layout inside an arbitrary window size.

    Natural content consists of camera image (cam_w x cam_h) vertically stacked with panel (cam_w x panel_h).
    Scale factor is min(win_w / cam_w, win_h / (cam_h + panel_h)).
    Scaled content is centered in the window with black bars on at most one pair of opposite edges.

    Invalid window coordinates (None, <= 0, (-1, -1, -1, -1), etc.) fallback to scale 1.0 (natural size).
    """
    if isinstance(win_w, (tuple, list)):
        if len(win_w) == 4:
            # OpenCV getWindowImageRect returns (x, y, width, height)
            _, _, w, h = win_w
        elif len(win_w) == 2:
            w, h = win_w
        else:
            w, h = None, None
    else:
        w, h = win_w, win_h

    natural_w = int(cam_w)
    natural_h = int(cam_h + panel_h)

    # Check for invalid window dimensions
    valid_window = True
    if w is None or h is None:
        valid_window = False
    else:
        try:
            w = int(w)
            h = int(h)
            if w <= 0 or h <= 0:
                valid_window = False
        except (TypeError, ValueError):
            valid_window = False

    if not valid_window:
        return DisplayLayout(
            scale=1.0,
            content_w=natural_w,
            content_h=natural_h,
            x0=0,
            y0=0,
            cam_rect=(0, 0, int(cam_w), int(cam_h)),
            panel_rect=(0, int(cam_h), int(cam_w), int(panel_h)),
            win_w=natural_w,
            win_h=natural_h,
        )

    scale_w = float(w) / float(natural_w)
    scale_h = float(h) / float(natural_h)
    scale = min(scale_w, scale_h)

    content_w = int(round(cam_w * scale))
    cam_scaled_h = int(round(cam_h * scale))
    panel_scaled_h = int(round(panel_h * scale))
    content_h = cam_scaled_h + panel_scaled_h

    x0 = (w - content_w) // 2
    y0 = (h - content_h) // 2

    cam_rect = (x0, y0, content_w, cam_scaled_h)
    panel_rect = (x0, y0 + cam_scaled_h, content_w, panel_scaled_h)

    return DisplayLayout(
        scale=scale,
        content_w=content_w,
        content_h=content_h,
        x0=x0,
        y0=y0,
        cam_rect=cam_rect,
        panel_rect=panel_rect,
        win_w=w,
        win_h=h,
    )


class ScalableHud:
    """Scalable HUD panel builder and cache.

    TrueType fonts are cached per font size in pixels (never recreated per frame).
    Panels are cached by (width, font_px, view_cache_key, small_tuple, n_stats).
    """

    BG_RGB = (20, 20, 20)
    BG_BGR = (20, 20, 20)
    TEXT_RGB = (255, 255, 255)
    TEXT_BGR = (255, 255, 255)
    HIGHLIGHT_RGB = (45, 75, 125)
    HIGHLIGHT_BGR = (125, 75, 45)
    CURSOR_RGB = (255, 215, 0)
    CURSOR_BGR = (0, 215, 255)
    PREVIEW_RGB = (130, 140, 150)
    PREVIEW_BGR = (150, 140, 130)
    HINT_RGB = (255, 215, 0)
    HINT_BGR = (0, 215, 255)
    HINT_PREFIX = "[Góc tay:"
    SMALL_RGB = (200, 220, 255)

    def __init__(self, font_path: str, base_font_size: int = 18):
        self.font_path = font_path
        self.base_font_size = int(base_font_size)
        self.font_size = int(base_font_size)
        self._font_cache: Dict[int, Tuple[Any, Any, int, int]] = {}
        self._panel: Optional[np.ndarray] = None
        self._key: Any = None
        self.build_count = 0
        self.last_font_size = int(base_font_size)

    def get_font_bundle(self, font_px: int) -> Tuple[Any, Any, int, int]:
        """Gets cached (font, small_font, line_h, small_h) for given font size in pixels."""
        font_px = max(1, int(round(font_px)))
        if font_px not in self._font_cache:
            from PIL import ImageFont

            font = ImageFont.truetype(self.font_path, font_px)
            small = ImageFont.truetype(self.font_path, max(1, int(font_px * 2 / 3)))
            line_h = int(font_px * 1.35)
            small_h = int(font_px * 0.95)
            self._font_cache[font_px] = (font, small, line_h, small_h)
        return self._font_cache[font_px]

    @staticmethod
    def _view_cache_key(v: Any) -> tuple:
        if not isinstance(v, dict):
            return tuple(v) if isinstance(v, (list, tuple)) else (v,)
        prev = v.get("preview")
        if prev is not None:
            prev_key = (
                prev.get("token"),
                prev.get("prediction"),
                prev.get("confidence"),
                prev.get("active_if_accepted"),
            )
        else:
            prev_key = None
        tc_key = tuple((tc.get("from"), tc.get("to")) for tc in v.get("tone_changes", []))
        warn_key = tuple(w.get("code") for w in v.get("warnings", []))
        return (
            v.get("committed"),
            v.get("active"),
            v.get("text"),
            v.get("cursor"),
            prev_key,
            tc_key,
            warn_key,
        )

    def _fit_committed(self, font: Any, committed: str, active: str, max_w: float) -> str:
        if not committed:
            return ""
        if font.getlength(committed + active) <= max_w:
            return committed
        words = re.findall(r"\S+\s*", committed)
        if not words:
            return "… "
        for i in range(1, len(words) + 1):
            rem = "".join(words[i:])
            cand = "… " + rem if rem else "… "
            if font.getlength(cand + active) <= max_w:
                return cand
        return "… "

    def _build_raw(
        self,
        width: int,
        font: Any,
        small_font: Any,
        line_h: int,
        small_h: int,
        scale: float,
        view: Any,
        small: Sequence[str],
        n_stats: int,
    ) -> np.ndarray:
        from PIL import Image, ImageDraw

        is_view_dict = isinstance(view, dict)
        num_big = 1 if is_view_dict else len(view)
        # Match natural height formula when scale == 1.0 (with round(8 * scale))
        height = line_h * num_big + small_h * (len(small) + n_stats) + int(round(8 * scale))
        img = Image.new("RGB", (width, height), self.BG_RGB)
        d = ImageDraw.Draw(img)
        y = int(round(4 * scale))

        if not is_view_dict:
            for text in view:
                d.text((int(round(8 * scale)), y), text, font=font, fill=self.TEXT_RGB)
                y += line_h
        else:
            committed = view.get("committed", "")
            active = view.get("active", "")
            preview = view.get("preview")

            x0 = int(round(8 * scale))
            max_cursor_w = max(width - int(round(24 * scale)) - x0, int(round(100 * scale)))
            disp_committed = self._fit_committed(font, committed, active, max_cursor_w)

            # 1. Committed text
            w_comm = font.getlength(disp_committed) if disp_committed else 0.0
            if disp_committed:
                d.text((x0, y), disp_committed, font=font, fill=self.TEXT_RGB)

            # 2. Active text with highlight background
            x_active = x0 + w_comm
            w_act = font.getlength(active) if active else 0.0
            if active and w_act > 0:
                rect_x0 = int(round(x_active))
                rect_x1 = int(round(x_active + w_act))
                d.rectangle([(rect_x0, y), (rect_x1, y + line_h - int(round(2 * scale)))], fill=self.HIGHLIGHT_RGB)
                d.text((rect_x0, y), active, font=font, fill=self.TEXT_RGB)

            # 3. Cursor line
            x_cursor = int(round(x_active + w_act))
            cur_w = max(1, int(round(2 * scale)))
            d.line(
                [(x_cursor, y + int(round(2 * scale))), (x_cursor, y + line_h - int(round(4 * scale)))],
                fill=self.CURSOR_RGB,
                width=cur_w,
            )

            # 4. Preview
            if preview is not None and (preview.get("token") is not None or preview.get("prediction") is not None):
                conf = preview.get("confidence")
                conf_str = f"{conf:.2f}" if conf is not None else ""
                active_if = preview.get("active_if_accepted", "")
                if active_if:
                    prev_label = f" {active_if} (a: nhận, {conf_str})"
                else:
                    prev_label = f" (a: nhận, {conf_str})"
                x_prev = x_cursor + int(round(4 * scale))
                d.text((x_prev, y), prev_label, font=font, fill=self.PREVIEW_RGB)

            y += line_h

        for text in small:
            d.text(
                (int(round(8 * scale)), y),
                text,
                font=small_font,
                fill=self.HINT_RGB if text.startswith(self.HINT_PREFIX) else self.SMALL_RGB,
            )
            y += small_h

        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    def build_panel(
        self,
        width: int,
        scale: float,
        view: Any,
        small: Sequence[str] = (),
        n_stats: int = 0,
    ) -> Tuple[np.ndarray, int]:
        """Builds or fetches cached panel image and small_h for the specified scale and content."""
        font_px = max(1, int(round(self.base_font_size * scale)))
        font, small_font, line_h, small_h = self.get_font_bundle(font_px)
        self.last_font_size = font_px

        key = (width, font_px, self._view_cache_key(view), tuple(small), int(n_stats))
        if key != self._key:
            self._panel = self._build_raw(
                width, font, small_font, line_h, small_h, scale, view, small, int(n_stats)
            )
            self._key = key
            self.build_count += 1
        return self._panel, small_h

    def panel_builder(self, view: Any, small: Sequence[str] = ()) -> "PanelBuilder":
        """Returns a PanelBuilder object holding the current view and small text."""
        return PanelBuilder(self, view, small)


class PanelBuilder:
    """Wrapper holding ScalableHud instance along with current view and hint lines."""

    def __init__(self, scalable_hud: ScalableHud, view: Any, small: Sequence[str] = ()):
        self.hud = scalable_hud
        self.view = view
        self.small = list(small)

    @property
    def font_size(self) -> int:
        return self.hud.base_font_size

    @property
    def base_font_size(self) -> int:
        return self.hud.base_font_size

    @property
    def build_count(self) -> int:
        return self.hud.build_count

    @property
    def last_font_size(self) -> int:
        return self.hud.last_font_size

    def build(self, width: int, scale: float = 1.0, n_stats: int = 0) -> Tuple[np.ndarray, int]:
        return self.hud.build_panel(width, scale, self.view, self.small, n_stats)

    def __call__(self, width: int, scale: float = 1.0, n_stats: int = 0) -> Tuple[np.ndarray, int]:
        return self.build(width, scale, n_stats)


def render_to_window(
    view_bgr: np.ndarray,
    panel_builder: Any,
    stats_lines: Sequence[str] = (),
    hold_progress: float = 0.0,
    layout: Optional[DisplayLayout] = None,
) -> np.ndarray:
    """Renders the camera view, scaled HUD panel, hold bar, and stats lines onto a window canvas.

    Args:
        view_bgr: Camera image in BGR format (already has landmarks drawn and display mirror applied).
        panel_builder: Panel builder callable, ScalableHud, PanelBuilder instance, or pre-rendered array.
        stats_lines: Sequence of ASCII status lines to draw via cv2.putText at the bottom of the panel.
        hold_progress: Progress of the hold gesture (0.0 to 1.0) shown as a green bar.
        layout: DisplayLayout geometry. If None, natural size layout is used.

    Returns:
        np.ndarray of shape (win_h, win_w, 3) in BGR format.
    """
    cam_h, cam_w = view_bgr.shape[:2]

    if layout is None:
        # Default natural layout
        layout = fit_layout(cam_w, cam_h, 200, None)

    scale = layout.scale
    cam_x, cam_y, cam_cw, cam_ch = layout.cam_rect
    pan_x, pan_y, pan_cw, pan_ch = layout.panel_rect
    win_w = layout.win_w
    win_h = layout.win_h

    # 1. Create black background canvas
    canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)

    # 2. Resize and place camera frame
    if (cam_w, cam_h) == (cam_cw, cam_ch):
        cam_resized = view_bgr
    else:
        cam_resized = cv2.resize(view_bgr, (cam_cw, cam_ch), interpolation=cv2.INTER_LINEAR)
    canvas[cam_y : cam_y + cam_ch, cam_x : cam_x + cam_cw] = cam_resized

    # 3. Build and place HUD panel
    panel_img = None
    small_h = None
    stats_lines = list(stats_lines)
    n_stats = len(stats_lines)

    if isinstance(panel_builder, np.ndarray):
        panel_img = panel_builder
    elif hasattr(panel_builder, "build") and callable(panel_builder.build):
        res = panel_builder.build(pan_cw, scale, n_stats)
        if isinstance(res, tuple):
            panel_img, small_h = res
        else:
            panel_img = res
    elif callable(panel_builder):
        sig = inspect.signature(panel_builder)
        n_params = len(sig.parameters)
        if n_params >= 3:
            res = panel_builder(pan_cw, scale, n_stats)
        elif n_params == 2:
            p2_name = list(sig.parameters.keys())[1].lower()
            if any(term in p2_name for term in ["font", "px"]):
                base_font = getattr(panel_builder, "font_size", getattr(panel_builder, "base_font_size", 18))
                res = panel_builder(pan_cw, max(1, int(round(base_font * scale))))
            else:
                try:
                    res = panel_builder(pan_cw, scale)
                except TypeError:
                    base_font = getattr(panel_builder, "font_size", getattr(panel_builder, "base_font_size", 18))
                    res = panel_builder(pan_cw, max(1, int(round(base_font * scale))))
        elif n_params == 1:
            res = panel_builder(pan_cw)
        else:
            res = panel_builder()

        if isinstance(res, tuple):
            panel_img, small_h = res
        else:
            panel_img = res

    if small_h is None:
        if hasattr(panel_builder, "small_h"):
            small_h = panel_builder.small_h
        else:
            base_font = getattr(panel_builder, "font_size", getattr(panel_builder, "base_font_size", 18))
            small_h = int(max(1, int(round(base_font * scale))) * 0.95)

    if panel_img is not None:
        ph = min(panel_img.shape[0], win_h - pan_y)
        pw = min(panel_img.shape[1], win_w - pan_x)
        canvas[pan_y : pan_y + ph, pan_x : pan_x + pw] = panel_img[:ph, :pw]
        actual_panel_h = panel_img.shape[0]
    else:
        actual_panel_h = pan_ch

    # 4. Draw hold progress bar
    if hold_progress > 0:
        bar_w = int(pan_cw * hold_progress)
        bar_h = max(1, int(round(3 * scale)))
        cv2.rectangle(canvas, (pan_x, pan_y), (pan_x + bar_w, pan_y + bar_h), (0, 200, 0), -1)

    # 5. Draw live stats lines
    font_scale = 0.45 * scale
    thickness = max(1, int(round(1 * scale)))
    x_stat = pan_x + int(round(8 * scale))
    panel_bottom = pan_y + actual_panel_h

    for i, line in enumerate(stats_lines):
        base = panel_bottom - int(round(10 * scale)) - (n_stats - 1 - i) * small_h
        cv2.putText(
            canvas,
            line,
            (x_stat, base),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (160, 255, 160),
            thickness,
            cv2.LINE_AA,
        )

    return canvas
