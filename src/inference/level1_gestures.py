"""
Level 1 deliberate gestures (plan 15 lần sửa 13 §3.2; user decision Q5 2026-10-08): the open palm (5 fingers spread) is
Space, a left / right wave of the flat hand is Backspace, and both fire only when the hand does them on purpose.

- load_gesture_config(path): configs/level1_gestures.json -> validated parameters (no default value in code; every key
  is {value, source "design", reason}; a missing / unknown key, a missing source or reason, a source other than
  "design" or a value out of its domain -> ValueError).
- palm_centre(points) / palm_len(points): mean of points 0, 5, 9, 13, 17 / |p9 - p0| in the image plane (x, y).
- DeliberateSpaceGesture: fires once when the open palm is held STILL (segmenter not "moving") for space_hold_ms,
  tolerating space_dropout_frames bad frames WITH the hand in a row; losing the hand cancels the hold at once.
- WaveBackspaceGesture: fires once when the palm centre makes wave_min_strokes horizontal strokes, each at least
  wave_min_amplitude x the median palm length, inside wave_window_ms, with a flat hand on wave_min_flat_fraction of the
  frames and a vertical amplitude at most wave_max_vertical_ratio x the horizontal one; then cooldown (no frame of it
  is buffered) and re-arm only when the flat hand ends.
- GestureEngine(values): both trackers on one frame; step() is the ONE path the desktop app and the measuring script
  call (level1_core.is_open_palm_space and level1_core.is_flat_hand_backspace with the config's thumb thresholds).

Pure computation: no clock, no GUI, no thread, no camera. Timestamps come from the caller.
"""
import hashlib
import json
import numbers
import os
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import numpy as np

from src.data.alphabet_preprocessing import MIDDLE_MCP_IDX, WRIST_IDX
from src.inference.level1_core import is_flat_hand_backspace, is_open_palm_space
from src.inference.level1_segmenter import aspect_points

# key -> kind: "number" (finite, > 0), "count" (integer >= 1), "fraction" (in (0, 1])
GESTURE_SPEC = {
    "space_hold_ms": "number",
    "space_dropout_frames": "count",
    "space_rearm_ms": "number",
    "wave_window_ms": "number",
    "wave_min_amplitude": "number",
    "wave_min_strokes": "count",
    "wave_max_vertical_ratio": "fraction",
    "wave_min_flat_fraction": "fraction",
    "wave_cooldown_ms": "number",
    "flat_thumb_min_ratio": "number",
    "flat_thumb_max_spread": "number",
    "gesture_flash_ms": "number",
    "legacy_flick_cooldown_ms": "number",
    "legacy_flick_window_ms": "number",
    "legacy_flick_min_dx": "number",
    "legacy_flick_min_speed": "number",
    "legacy_flick_palm_ratio": "number",
    "legacy_flick_dx_over_dy": "number",
    "legacy_flick_min_dt_s": "number",
}
ENTRY_FIELDS = frozenset({"value", "source", "reason"})
DESIGN_SOURCE = "design"
PALM_POINTS = (WRIST_IDX, 5, MIDDLE_MCP_IDX, 13, 17)  # wrist and the 4 long-finger MCPs


class WaveFrame(NamedTuple):
    """One hand frame of the wave buffer."""
    ts: float
    x: float      # palm centre
    y: float
    flat: bool    # is_flat_hand_backspace of the frame
    palm: float   # palm_len of the frame


# ---------------------------------------------------------------------------------------------------- config
def _check(name: str, kind: str, value: Any) -> Any:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name}: value must be a number, got {value!r}")
    if not np.isfinite(float(value)):
        raise ValueError(f"{name}: value must be finite, got {value!r}")
    if kind == "count":
        if not isinstance(value, numbers.Integral):
            raise ValueError(f"{name}: value must be an integer, got {value!r}")
        if not value >= 1:
            raise ValueError(f"{name}: value must be >= 1, got {value!r}")
        return int(value)
    if not value > 0:
        raise ValueError(f"{name}: value must be > 0, got {value!r}")
    if kind == "fraction" and not value <= 1:
        raise ValueError(f"{name}: value must be in (0, 1], got {value!r}")
    return value


def validate_gesture_config(raw: Any) -> Dict[str, Any]:
    """Raw config dict -> {key: value} in GESTURE_SPEC order. Keys starting with '_' are comments. Raises ValueError on a
    missing or unknown key, an entry that is not exactly {value, source, reason}, a source other than "design", an
    empty reason or a value out of its domain."""
    if not isinstance(raw, dict):
        raise ValueError("gesture config must be a JSON object")
    unknown = sorted(k for k in raw if not str(k).startswith("_") and k not in GESTURE_SPEC)
    if unknown:
        raise ValueError(f"gesture config: unknown keys {unknown}")
    values = {}
    for key, kind in GESTURE_SPEC.items():
        if key not in raw:
            raise ValueError(f"gesture config: missing key {key!r}")
        entry = raw[key]
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise ValueError(f"gesture config {key}: must be an object with exactly value, source, reason")
        if entry["source"] != DESIGN_SOURCE:
            raise ValueError(f"gesture config {key}: source must be {DESIGN_SOURCE!r}, got {entry['source']!r}")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ValueError(f"gesture config {key}: reason must be a non-empty string")
        values[key] = _check(f"gesture config {key}", kind, entry["value"])
    return values


def load_gesture_config(path: str) -> Dict[str, Any]:
    """configs/level1_gestures.json -> {"values": {key: value}, "raw": parsed JSON, "sha256", "path"}."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"gesture config {os.path.basename(path)}: not valid UTF-8 JSON ({e})") from None
    return {"values": validate_gesture_config(raw), "raw": raw, "sha256": hashlib.sha256(data).hexdigest(), "path": path}


def _need(values: Dict[str, Any], keys: Tuple[str, ...]) -> List[Any]:
    missing = [k for k in keys if k not in values]
    if missing:
        raise ValueError(f"gesture values: missing keys {missing}")
    return [values[k] for k in keys]


def _timestamp(ts_ms: float) -> float:
    ts = float(ts_ms)
    if not np.isfinite(ts):
        raise ValueError("timestamp must be finite")
    return ts


# ---------------------------------------------------------------------------------------------------- geometry
def palm_centre(points: np.ndarray) -> np.ndarray:
    """Mean of the wrist and the 4 long-finger MCPs (aspect-corrected points, level1_segmenter.aspect_points)."""
    p = np.asarray(points, dtype=np.float64)
    return np.mean(p[list(PALM_POINTS)], axis=0)


def palm_len(points: np.ndarray) -> float:
    """|p9 - p0| in the image plane (x, y): the hand-size unit of the wave amplitude."""
    p = np.asarray(points, dtype=np.float64)
    return float(np.linalg.norm(p[MIDDLE_MCP_IDX, :2] - p[WRIST_IDX, :2]))


def _hand_points(points: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """[21, 2] / [21, 3] finite points with a palm length > 0, else None (no usable hand)."""
    if points is None:
        return None
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] != 21 or p.shape[1] not in (2, 3) or not np.all(np.isfinite(p)):
        return None
    if not palm_len(p) > 0:
        return None
    return p


# ---------------------------------------------------------------------------------------------------- space
class DeliberateSpaceGesture:
    """Open palm held still -> Space. update(ts_ms, is_palm, has_hand, still) once per processed frame (still = the
    segmenter of the same frame is not "moving"); returns True exactly once per gesture:
      - armed: the hold starts at the first frame with the open palm AND still; a frame with the hand but not (open palm
        and still) is a bad frame: up to dropout_frames bad frames in a row keep the hold (its time keeps running),
        one more ends it; a frame without hand ends it at once (dropout_frames does not cover frames without hand,
        lần sửa 13d P1). A good frame with ts - start >= hold_ms -> True, disarmed;
      - disarmed: no space however long the open palm is held (no auto-repeat); re-armed by a frame without hand, or by
        another pose / a hand that is not still held for more than rearm_ms.
    held_ms = how long the open palm has been held while armed (0 otherwise; HUD)."""

    def __init__(self, hold_ms: float, dropout_frames: int, rearm_ms: float):
        self.hold_ms = float(_check("hold_ms", "number", hold_ms))
        self.dropout_frames = _check("dropout_frames", "count", dropout_frames)
        self.rearm_ms = float(_check("rearm_ms", "number", rearm_ms))
        self.n_emits = 0
        self.reset()

    @classmethod
    def from_values(cls, values: Dict[str, Any]) -> "DeliberateSpaceGesture":
        return cls(*_need(values, ("space_hold_ms", "space_dropout_frames", "space_rearm_ms")))

    def reset(self) -> None:
        """Armed, no hold. The emission counter is kept."""
        self.armed = True
        self.run_since: Optional[float] = None
        self.misses = 0
        self.other_since: Optional[float] = None
        self.last_ts: Optional[float] = None

    @property
    def held_ms(self) -> float:
        if self.armed and self.run_since is not None and self.last_ts is not None:
            return self.last_ts - self.run_since
        return 0.0

    def update(self, ts_ms: float, is_palm: bool, has_hand: bool, still: bool) -> bool:
        ts = _timestamp(ts_ms)
        self.last_ts = ts
        if not has_hand:
            self.armed, self.run_since, self.misses, self.other_since = True, None, 0, None
            return False
        if is_palm and still:
            self.other_since, self.misses = None, 0
            if not self.armed:
                return False
            if self.run_since is None:
                self.run_since = ts
            if ts - self.run_since >= self.hold_ms:
                self.armed, self.run_since = False, None
                self.n_emits += 1
                return True
            return False
        if self.armed:
            if self.run_since is not None:
                self.misses += 1
                if self.misses > self.dropout_frames:
                    self.run_since, self.misses = None, 0
            return False
        if self.other_since is None:
            self.other_since = ts
        if ts - self.other_since > self.rearm_ms:
            self.armed, self.other_since = True, None
        return False


# ---------------------------------------------------------------------------------------------------- backspace
class WaveBackspaceGesture:
    """Flat hand waved left / right -> Backspace. update(ts_ms, points_or_None, is_flat) once per processed frame
    (points = aspect-corrected hand points, None = no hand); returns True exactly once per wave:
      - buffer of the hand frames (ts, palm centre x, y, is_flat, palm length) of the last window_ms; a frame without
        hand clears it;
      - strokes by hysteresis on the x of the palm centre, threshold = min_amplitude x median palm length of the buffer:
        the first stroke when x has moved that far from its lowest / highest point, a new stroke each time x comes back
        that far from the extreme of the current stroke;
      - fires when strokes >= min_strokes AND, on the frames from the start of the first stroke to now, the flat
        fraction >= min_flat_fraction AND the vertical amplitude <= max_vertical_ratio x the horizontal one AND
        cooldown_ms has passed since the last backspace;
      - after firing: buffer cleared, cooldown, and nothing is buffered until the flat hand ends (a frame without hand,
        or a hand frame that is not flat after the cooldown);
      - no hand frame with ts - last backspace < cooldown_ms is ever buffered (lần sửa 13d P2): the buffer stays empty
        and strokes = 0 during the cooldown, so strokes are counted only from the first frame after it (a wave done
        inside the cooldown does not fire when it ends). A frame without hand still ends the flat hand at once.
    strokes = strokes counted on the current buffer (HUD)."""

    def __init__(self, window_ms: float, min_amplitude: float, min_strokes: int, max_vertical_ratio: float,
                 min_flat_fraction: float, cooldown_ms: float):
        self.window_ms = float(_check("window_ms", "number", window_ms))
        self.min_amplitude = float(_check("min_amplitude", "number", min_amplitude))
        self.min_strokes = _check("min_strokes", "count", min_strokes)
        self.max_vertical_ratio = float(_check("max_vertical_ratio", "fraction", max_vertical_ratio))
        self.min_flat_fraction = float(_check("min_flat_fraction", "fraction", min_flat_fraction))
        self.cooldown_ms = float(_check("cooldown_ms", "number", cooldown_ms))
        self.n_emits = 0
        self.reset()

    @classmethod
    def from_values(cls, values: Dict[str, Any]) -> "WaveBackspaceGesture":
        return cls(*_need(values, ("wave_window_ms", "wave_min_amplitude", "wave_min_strokes",
                                   "wave_max_vertical_ratio", "wave_min_flat_fraction", "wave_cooldown_ms")))

    def reset(self) -> None:
        """Empty buffer, no cooldown, armed. The emission counter is kept."""
        self.buffer: List[WaveFrame] = []
        self.last_emit_ts: Optional[float] = None
        self.need_release = False
        self.strokes = 0
        self.last_ts: Optional[float] = None

    def _count_strokes(self) -> Tuple[int, int]:
        """-> (number of strokes, buffer index where the first stroke starts)."""
        thr = self.min_amplitude * float(np.median([b.palm for b in self.buffer]))
        direction, n, start = 0, 0, 0
        lo = hi = ext = self.buffer[0].x
        lo_i = hi_i = 0
        for i, b in enumerate(self.buffer):
            x = b.x
            if direction == 0:
                if x <= lo:
                    lo, lo_i = x, i
                if x >= hi:
                    hi, hi_i = x, i
                if x - lo >= thr:
                    direction, n, ext, start = 1, 1, x, lo_i
                elif hi - x >= thr:
                    direction, n, ext, start = -1, 1, x, hi_i
            elif direction > 0:
                if x >= ext:
                    ext = x
                elif ext - x >= thr:
                    direction, n, ext = -1, n + 1, x
            else:
                if x <= ext:
                    ext = x
                elif x - ext >= thr:
                    direction, n, ext = 1, n + 1, x
        return n, start

    def update(self, ts_ms: float, points: Optional[np.ndarray], is_flat: bool) -> bool:
        ts = _timestamp(ts_ms)
        self.last_ts = ts
        p = _hand_points(points)
        if p is None:
            self.buffer.clear()
            self.need_release, self.strokes = False, 0
            return False
        flat = bool(is_flat)
        in_cooldown = self.last_emit_ts is not None and ts - self.last_emit_ts < self.cooldown_ms
        if self.need_release:
            if flat or in_cooldown:
                return False
            self.need_release = False
        if in_cooldown:  # plan 15 lần sửa 13d P2: a hand frame inside the cooldown is never buffered
            self.buffer.clear()
            self.strokes = 0
            return False
        c = palm_centre(p)
        self.buffer.append(WaveFrame(ts, float(c[0]), float(c[1]), flat, palm_len(p)))
        cutoff = ts - self.window_ms
        self.buffer = [b for b in self.buffer if b.ts >= cutoff]
        self.strokes, start = self._count_strokes()
        if self.strokes < self.min_strokes:
            return False
        span = self.buffer[start:]
        if sum(b.flat for b in span) < self.min_flat_fraction * len(span):
            return False
        xs = [b.x for b in span]
        ys = [b.y for b in span]
        if max(ys) - min(ys) > self.max_vertical_ratio * (max(xs) - min(xs)):
            return False
        self.last_emit_ts = ts
        self.n_emits += 1
        self.buffer.clear()
        self.need_release, self.strokes = True, 0
        return True


# ---------------------------------------------------------------------------------------------------- engine
class GestureEngine:
    """Both deliberate gestures on one frame. step(ts_ms, landmarks_or_None, width, height, still) with the raw
    MediaPipe hand landmarks [21, 3] of the frame (None = no hand) and still = the segmenter of the same frame is not
    "moving" -> {"space", "backspace", "is_palm", "is_flat"}. The points go through level1_segmenter.aspect_points
    (the correction shared with training); the poses are level1_core.is_open_palm_space and
    level1_core.is_flat_hand_backspace(points, flat_thumb_min_ratio, flat_thumb_max_spread). A [21, 3] frame with a NaN /
    inf value is no hand for both trackers (as None; lần sửa 13d THẤP-2); another shape, or a width / height that is not
    a finite number > 0 -> ValueError."""

    def __init__(self, values: Dict[str, Any]):
        thumb_min, thumb_spread = _need(values, ("flat_thumb_min_ratio", "flat_thumb_max_spread"))
        self.thumb_min = float(_check("flat_thumb_min_ratio", "number", thumb_min))
        self.thumb_spread = float(_check("flat_thumb_max_spread", "number", thumb_spread))
        self.space = DeliberateSpaceGesture.from_values(values)
        self.wave = WaveBackspaceGesture.from_values(values)

    def reset(self) -> None:
        self.space.reset()
        self.wave.reset()

    def step(self, ts_ms: float, landmarks: Optional[np.ndarray], width: int, height: int,
             still: bool) -> Dict[str, bool]:
        for name, size in (("width", width), ("height", height)):
            if isinstance(size, bool) or not isinstance(size, numbers.Real) or not np.isfinite(float(size)) \
                    or not size > 0:
                raise ValueError(f"{name} must be a finite number > 0, got {size!r}")
        raw = None
        if landmarks is not None:
            raw = np.asarray(landmarks, dtype=np.float64)
            if raw.shape != (21, 3):
                raise ValueError(f"landmarks must be [21, 3], got {raw.shape}")
            if not np.all(np.isfinite(raw)):
                raw = None  # lần sửa 13d (THẤP-2): a frame with NaN / inf is no hand for both trackers
        if raw is None:
            space = self.space.update(ts_ms, False, False, still)
            backspace = self.wave.update(ts_ms, None, False)
            return {"space": space, "backspace": backspace, "is_palm": False, "is_flat": False}
        points = aspect_points(raw, width, height)
        is_palm = bool(is_open_palm_space(points))
        is_flat = bool(is_flat_hand_backspace(points, self.thumb_min, self.thumb_spread))
        space = self.space.update(ts_ms, is_palm, True, still)
        backspace = self.wave.update(ts_ms, points, is_flat)
        return {"space": space, "backspace": backspace, "is_palm": is_palm, "is_flat": is_flat}
