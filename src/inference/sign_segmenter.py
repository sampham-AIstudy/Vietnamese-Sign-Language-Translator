"""
Sign segmenter for the live "Ký từ" path (plan 04 §3.4). Pure numpy: no torch, cv2 or mediapipe.

It collects ONE whole sign from a stream of 67-joint landmark frames (onset of motion -> hands at rest) and emits
the buffered frames; `harmonize()` then trims them to the active span +- pad_s with exactly the training rule.

Per-frame activity uses the training functions themselves (src/data/harmonized.py, not modified):
    active(frame) = any(hand_activity(_normalise(window), fps_window, cfg_ckpt))[-1]
where `window` holds the frames of the last `activity_window_s` seconds and `fps_window` is its mean frame rate.

Two groups of parameters:
- from the checkpoint's `preprocessing` (required, no defaults here): rest_y, active_speed, pad_s, max_gap_s,
  mask_resting_hand;
- live only (not in the checkpoint): SEGMENTER_DEFAULT. These are initial DESIGN values, NOT measured. Tune them only
  on TRAIN clips or on the user's own webcam set (Bước 5), never on TEST.

State machine:
  idle      --active continuously >= onset_min_s-->               recording (segment starts at the pre-roll ring)
  recording --inactive continuously >= rest_hold_s-->             Emit (or Discard too_short) -> idle
  recording --duration > max_sign_s or buffer full-->             Discard too_long -> wait_rest
  recording --timestamp gap > stream_gap_s-->                     Discard stream_gap -> idle
  recording --frame (W, H) changed-->                             Discard frame_size_changed -> idle
  any       --reset()-->                                          Discard reset if recording -> idle
  wait_rest --inactive continuously >= rest_hold_s-->             idle
"""
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple, Union

import numpy as np

from src.data.harmonized import _normalise, hand_activity

SEGMENTER_DEFAULT: Dict[str, Any] = {
    "onset_min_s": 0.10,
    "pre_roll_s": 0.50,
    "rest_hold_s": 0.50,
    "min_sign_s": 0.30,
    "max_sign_s": 8.0,
    "stream_gap_s": 1.0,
    "activity_window_s": 1.0,
    "max_buffer_frames": 1024,
}
CHECKPOINT_KEYS = ("rest_y", "active_speed", "pad_s", "max_gap_s", "mask_resting_hand")
DISCARD_REASONS = ("too_short", "too_long", "stream_gap", "frame_size_changed", "no_hand_frames", "reset")


@dataclass(frozen=True)
class Emit:
    segment_id: int
    kps: np.ndarray            # [n, 67, 3] raw MediaPipe coords (NaN = missing)
    vis: np.ndarray            # [n, 67]
    t: np.ndarray              # [n] seconds (caller's clock), strictly increasing
    frame_wh: Tuple[int, int]
    active_start_s: float      # first frame of the onset run
    active_end_s: float        # last active frame
    seqs: Optional[Tuple[int, ...]] = None   # caller's frame sequence numbers, when given to push()


@dataclass(frozen=True)
class Discard:
    segment_id: int
    reason: str
    duration_s: float          # time span of the discarded buffer
    frames: int


SegmenterEvent = Union[Emit, Discard]


def _check_params(preprocessing: Mapping[str, Any], params: Optional[Mapping[str, Any]]):
    if not isinstance(preprocessing, Mapping):
        raise ValueError("preprocessing must be a mapping (the checkpoint's preprocessing dict)")
    missing = [k for k in CHECKPOINT_KEYS if k not in preprocessing]
    if missing:
        raise ValueError(f"preprocessing is missing required key(s) {missing}")
    p = dict(SEGMENTER_DEFAULT)
    if params is not None:
        unknown = sorted(set(params) - set(SEGMENTER_DEFAULT))
        if unknown:
            raise ValueError(f"unknown segmenter parameter(s) {unknown}")
        p.update(params)
    for k, v in p.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0:
            raise ValueError(f"segmenter parameter {k} must be a finite number >= 0, got {v!r}")
    if not isinstance(p["max_buffer_frames"], int) or p["max_buffer_frames"] < 2:
        raise ValueError("max_buffer_frames must be an int >= 2")
    for k in ("rest_hold_s", "max_sign_s", "stream_gap_s", "activity_window_s"):
        if p[k] <= 0:
            raise ValueError(f"{k} must be > 0")
    cfg = {k: preprocessing[k] for k in CHECKPOINT_KEYS}
    for k in ("rest_y", "active_speed", "pad_s", "max_gap_s"):
        v = cfg[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v):
            raise ValueError(f"preprocessing[{k!r}] must be a finite number, got {v!r}")
    # plan 04 §3.4 constraints
    if not p["pre_roll_s"] >= cfg["pad_s"]:
        raise ValueError("pre_roll_s must be >= pad_s")
    if not p["rest_hold_s"] >= cfg["pad_s"]:
        raise ValueError("rest_hold_s must be >= pad_s")
    if not p["rest_hold_s"] > cfg["max_gap_s"]:
        raise ValueError("rest_hold_s must be > max_gap_s (a hand gap harmonize() bridges must not split a sign)")
    return cfg, p


class SignSegmenter:
    """push(coords[67,3], vis[67], t_s, frame_wh) -> Emit | Discard | None. See the module docstring."""

    def __init__(self, preprocessing: Mapping[str, Any], params: Optional[Mapping[str, Any]] = None):
        self.cfg, self.params = _check_params(preprocessing, params)
        self.state = "idle"
        self.segment_id: Optional[int] = None
        self.hand_active = False
        self._next_id = 1
        self._last_t: Optional[float] = None
        self._frame_wh: Optional[Tuple[int, int]] = None
        self._hist: deque = deque()   # (coords, vis, t) for the activity window
        self._buf: deque = deque()    # (coords, vis, t, active, seq): pre-roll ring / recorded segment
        self._run_start: Optional[float] = None
        self._onset_t: Optional[float] = None
        self._last_active_t: Optional[float] = None
        self._inactive_since: Optional[float] = None

    # ---------------------------------------------------------------- properties
    @property
    def n_frames(self) -> int:
        return len(self._buf)

    @property
    def recording_s(self) -> Optional[float]:
        if self.state != "recording" or self._onset_t is None or self._last_t is None:
            return None
        return float(self._last_t - self._onset_t)

    # ---------------------------------------------------------------- internals
    def _activity(self, aspect: float) -> bool:
        k = np.stack([h[0] for h in self._hist])
        v = np.stack([h[1] for h in self._hist])
        t0, t1 = self._hist[0][2], self._hist[-1][2]
        n = len(self._hist)
        fps = (n - 1) / (t1 - t0) if n >= 2 and t1 > t0 else 30.0   # n == 1: speed is 0 whatever fps is
        kn, vn = _normalise(k, v, aspect)
        left, right = hand_activity(kn, vn, fps, self.cfg)
        return bool(left[-1] or right[-1])

    def _trim_ring(self, ref_t: float):
        pre = self.params["pre_roll_s"]
        while len(self._buf) >= 2 and self._buf[1][2] <= ref_t - pre:
            self._buf.popleft()
        while len(self._buf) > self.params["max_buffer_frames"]:
            self._buf.popleft()

    def _discard(self, reason: str) -> Discard:
        ts = [r[2] for r in self._buf]
        dur = float(ts[-1] - ts[0]) if len(ts) >= 2 else 0.0
        return Discard(segment_id=self.segment_id, reason=reason, duration_s=dur, frames=len(self._buf))

    def _emit(self) -> Emit:
        recs = list(self._buf)
        seqs = [r[4] for r in recs]
        return Emit(segment_id=self.segment_id,
                    kps=np.stack([r[0] for r in recs]).astype(np.float32),
                    vis=np.stack([r[1] for r in recs]).astype(np.float32),
                    t=np.array([r[2] for r in recs], dtype=np.float64),
                    frame_wh=self._frame_wh,
                    active_start_s=float(self._onset_t), active_end_s=float(self._last_active_t),
                    seqs=None if any(s is None for s in seqs) else tuple(int(s) for s in seqs))

    def _to_idle(self):
        self.state = "idle"
        self._run_start = self._onset_t = self._last_active_t = self._inactive_since = None

    # ---------------------------------------------------------------- API
    def validate_time(self, t_s: float) -> float:
        """ValueError unless t_s is finite and strictly after the last pushed frame. Changes nothing."""
        t = float(t_s)
        if not np.isfinite(t):
            raise ValueError("t_s must be finite")
        if self._last_t is not None and not t > self._last_t:
            raise ValueError(f"timestamps must be strictly increasing ({t} <= {self._last_t})")
        return t

    def push(self, coords, vis, t_s: float, frame_wh, seq: Optional[int] = None) -> Optional[SegmenterEvent]:
        # --- validate everything before touching any state
        t = self.validate_time(t_s)
        c = np.asarray(coords, dtype=np.float32)
        v = np.asarray(vis, dtype=np.float32)
        if c.shape != (67, 3) or v.shape != (67,):
            raise ValueError(f"expected coords [67,3] and vis [67], got {c.shape} and {v.shape}")
        wh = (int(frame_wh[0]), int(frame_wh[1]))
        if wh[0] <= 0 or wh[1] <= 0:
            raise ValueError(f"frame_wh must be positive, got {wh}")

        p = self.params
        event: Optional[SegmenterEvent] = None
        gap = self._last_t is not None and t - self._last_t > p["stream_gap_s"]
        resized = self._frame_wh is not None and wh != self._frame_wh
        if gap or resized:
            if self.state == "recording":
                event = self._discard("stream_gap" if gap else "frame_size_changed")
                self._to_idle()
            # time or geometry discontinuity: nothing before it may be mixed with what follows
            self._hist.clear()
            self._buf.clear()
            self._run_start = self._inactive_since = None
        self._last_t, self._frame_wh = t, wh

        self._hist.append((c, v, t))
        while self._hist and self._hist[0][2] < t - p["activity_window_s"]:
            self._hist.popleft()
        while len(self._hist) > p["max_buffer_frames"]:
            self._hist.popleft()
        active = self._activity(wh[0] / wh[1])
        self.hand_active = active
        rec = (c, v, t, active, seq)

        if self.state == "idle":
            self._buf.append(rec)
            self._run_start = (self._run_start if self._run_start is not None else t) if active else None
            if active and t - self._run_start >= p["onset_min_s"]:
                self.state = "recording"
                self.segment_id = self._next_id
                self._next_id += 1
                self._onset_t, self._last_active_t = self._run_start, t
                self._trim_ring(self._onset_t)
            else:
                self._trim_ring(self._run_start if self._run_start is not None else t)
            return event

        if self.state == "recording":
            if len(self._buf) >= p["max_buffer_frames"]:
                event = self._discard("too_long")
                self._buf.clear()
                self._to_idle()
                self.state = "wait_rest"
                self._inactive_since = None if active else t
                self._buf.append(rec)
                return event
            self._buf.append(rec)
            if active:
                self._last_active_t = t
            if t - self._onset_t > p["max_sign_s"]:
                event = self._discard("too_long")
                self._buf.clear()
                self._to_idle()
                self.state = "wait_rest"
                self._inactive_since = None if active else t
                self._buf.append(rec)
                return event
            if not active and t - self._last_active_t >= p["rest_hold_s"]:
                if self._last_active_t - self._onset_t < p["min_sign_s"]:
                    event = self._discard("too_short")
                else:
                    event = self._emit()
                last_active = self._last_active_t
                tail = [r for r in self._buf if r[2] > last_active]   # rest frames only: pre-roll for the next sign
                self._buf.clear()
                self._buf.extend(tail)
                self._to_idle()
                self._trim_ring(t)
            return event

        # wait_rest: block re-triggering while the hand stays up
        self._buf.append(rec)
        if active:
            self._inactive_since = None
        elif self._inactive_since is None:
            self._inactive_since = t
        if self._inactive_since is not None and t - self._inactive_since >= p["rest_hold_s"]:
            self._to_idle()
        self._trim_ring(t)
        return event

    def reset(self) -> Optional[Discard]:
        """Client reset: drop the current recording (Discard reset) and clear every buffer; timestamps keep
        their order requirement (the session clock is not reset)."""
        event = self._discard("reset") if self.state == "recording" else None
        self._hist.clear()
        self._buf.clear()
        self._frame_wh = None
        self.hand_active = False
        self._to_idle()
        return event
