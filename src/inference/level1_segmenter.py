"""
Level 1 ("Đánh vần") sign segmenter for continuous fingerspelling (plan 15 §3.3).

The Level 1 model was trained on ONE whole clip per letter / tone mark. On a live stream the signer moves from one
letter to the next without pressing anything; this segmenter cuts the stream into such clips:

- motion per frame (only when this frame and the previous pushed frame both have a hand, dt > 0):
  P = raw MediaPipe landmarks with x, z multiplied by W/H (the aspect correction of canonicalize_hand_sequence),
  palm_t = |P_t[9,:2] - P_t[0,:2]|,
  v_t = |P_t[0,:2] - P_{t-1}[0,:2]| / mean(palm_t, palm_{t-1}) / dt_s       (wrist speed),
  s_t = mean over the 21 points of |N_t - N_{t-1}| / dt_s, N = normalize_hand_landmarks(P)   (hand-shape speed),
  m_t = max(v_t, s_t), in hand-lengths per second (independent of fps and resolution);
- M_t = median of the m values of the last `motion_window_ms`; None when there is no such value (never a number
  invented for "no measurement", and None is not "still");
- still: M_t <= still_speed; moving: M_t >= move_speed (> still_speed, hysteresis: in between the previous state is
  kept); the still / moving classification is only updated on frames with a hand;
- emit a SignSegment when armed and still for >= hold_ms with enough hand frames (reason "hold"; the segment keeps the
  buffered frames with ts <= t_emit - (hold_ms - tail_still_keep_ms), t_emit = timestamp of the emitting frame, so
  tail_still_keep_ms == hold_ms keeps every buffered frame), when the hand is
  lost for >= hand_lost_ms (reason "hand_lost", tail cut at the last hand frame) or on flush() ("end_of_stream");
- re-arm after moving continuously for >= rearm_move_ms (the buffer is cut back to the start of that motion, so the
  whole motion of a tone mark is kept) or after the hand was lost;
- a WordGap after the hand is lost for >= word_gap_ms, only when a sign was emitted since the previous WordGap.

All durations are in milliseconds of the pushed timestamps (not frame counts). Parameters come from the caller
(configs/level1_realtime.json via level1_core.load_level1_config); there is no default value in this module.

Pure computation: numpy + normalize_hand_landmarks (the Level 1 normalisation shared with training); no cv2, no
GUI, no thread. Not thread-safe.
"""
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from src.data.alphabet_preprocessing import EPS, MIDDLE_MCP_IDX, WRIST_IDX, normalize_hand_landmarks

SEGMENTER_KEYS = ("motion_window_ms", "still_speed", "move_speed", "hold_ms", "rearm_move_ms", "hand_lost_ms",
                  "word_gap_ms", "max_segment_ms", "min_sign_frames", "tail_still_keep_ms")
CLOSE_REASONS = ("hold", "hand_lost", "end_of_stream")
STATES = ("no_hand", "moving", "holding")


@dataclass
class SignSegment:
    """One sign cut from the stream; arrays are copies (never shared with the segmenter's buffer). The fields are
    the inputs of alphabet_clip_features(raw_landmarks, detected, handedness, frame_width / frame_height,
    timestamps_ms, ...)."""
    seq: int
    raw_landmarks: np.ndarray   # [T, 21, 3] float32, zeros where no hand
    detected: np.ndarray        # [T] bool
    handedness: np.ndarray      # [T] str ('Left' / 'Right' / '')
    timestamps_ms: np.ndarray   # [T] float64
    frame_width: int
    frame_height: int
    t_start_ms: float
    t_end_ms: float
    t_emit_ms: float
    close_reason: str

    @property
    def n_frames(self) -> int:
        return int(len(self.detected))

    @property
    def n_detected(self) -> int:
        return int(np.count_nonzero(self.detected))


@dataclass
class WordGap:
    """The hand was away long enough to end the current word."""
    seq: int
    t_ms: float


Event = Union[SignSegment, WordGap]


def aspect_points(landmarks: np.ndarray, width: int, height: int) -> np.ndarray:
    """Raw MediaPipe landmarks [21, 3] -> x and z multiplied by width / height (same correction as
    canonicalize_hand_sequence), float64."""
    p = np.asarray(landmarks, dtype=np.float64).copy()
    ratio = float(width) / float(height)
    p[:, 0] *= ratio
    p[:, 2] *= ratio
    return p


def frame_motion(prev_p: np.ndarray, prev_n: np.ndarray, cur_p: np.ndarray, cur_n: np.ndarray, dt_s: float) -> float:
    """m_t = max(wrist speed, hand-shape speed) in hand-lengths per second (module docstring)."""
    palm_prev = float(np.linalg.norm(prev_p[MIDDLE_MCP_IDX, :2] - prev_p[WRIST_IDX, :2]))
    palm_cur = float(np.linalg.norm(cur_p[MIDDLE_MCP_IDX, :2] - cur_p[WRIST_IDX, :2]))
    palm = max((palm_prev + palm_cur) / 2.0, EPS)
    wrist = float(np.linalg.norm(cur_p[WRIST_IDX, :2] - prev_p[WRIST_IDX, :2])) / palm / dt_s
    shape = float(np.mean(np.linalg.norm(cur_n - prev_n, axis=-1))) / dt_s
    return max(wrist, shape)


class Level1SignSegmenter:
    """Push one frame at a time; push() / flush() return the events (SignSegment / WordGap) in emission order."""

    def __init__(self, params: Dict[str, Any], min_detected_frames: int):
        missing = [k for k in SEGMENTER_KEYS if k not in params]
        if missing:
            raise ValueError(f"segmenter parameters missing: {missing}")
        self.p = {k: params[k] for k in SEGMENTER_KEYS}
        if not self.p["move_speed"] > self.p["still_speed"]:
            raise ValueError("move_speed must be > still_speed")
        if self.p["word_gap_ms"] < self.p["hand_lost_ms"]:
            raise ValueError("word_gap_ms must be >= hand_lost_ms")
        if not (0 < self.p["tail_still_keep_ms"] <= self.p["hold_ms"]):
            raise ValueError("tail_still_keep_ms must be > 0 and <= hold_ms")
        self.min_frames = max(int(self.p["min_sign_frames"]), int(min_detected_frames))
        self._seq = 0
        self._word_has_sign = False
        self._last_ts: Optional[float] = None
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        """Drops the buffer and the motion history (used when tracking is paused). The event counter and the
        'word has a sign' flag are kept."""
        self._tracking = False
        self._buf: List[Tuple[np.ndarray, bool, str, float, int, int]] = []
        self._hist: Deque[Tuple[float, float]] = deque()
        self._prev: Optional[Tuple[np.ndarray, np.ndarray, float]] = None  # (P, N, ts) of the previous hand frame
        self._armed = False
        self._still_since: Optional[float] = None
        self._move_since: Optional[float] = None
        self._last_hand_ts: Optional[float] = None
        self._last_has_hand = False
        self._size: Optional[Tuple[int, int]] = None
        self.motion: Optional[float] = None
        self._hold_progress = 0.0

    @property
    def state(self) -> str:
        if not self._last_has_hand:
            return "no_hand"
        return "holding" if self._still_since is not None else "moving"

    @property
    def armed(self) -> bool:
        return self._armed

    @property
    def hold_progress(self) -> float:
        return self._hold_progress

    def status(self) -> Dict[str, Any]:
        """HUD state: {state, hold_progress in [0, 1], armed, motion (M_t or None)}."""
        return {"state": self.state, "hold_progress": self._hold_progress, "armed": self._armed,
                "motion": self.motion}

    # ------------------------------------------------------------------ helpers
    def _n_detected(self, frames: Sequence) -> int:
        return sum(1 for f in frames if f[1])

    def _make_segment(self, frames: Sequence, t_emit: float, reason: str) -> Optional[SignSegment]:
        """Segment of `frames` without leading / trailing no-hand frames; None when too few hand frames."""
        idx = [i for i, f in enumerate(frames) if f[1]]
        if len(idx) < self.min_frames:
            return None
        frames = frames[idx[0]:idx[-1] + 1]
        self._seq += 1
        seg = SignSegment(
            seq=self._seq,
            raw_landmarks=np.stack([f[0] for f in frames]).astype(np.float32, copy=True),
            detected=np.array([f[1] for f in frames], dtype=bool),
            handedness=np.array([f[2] for f in frames], dtype=object).astype(str),
            timestamps_ms=np.array([f[3] for f in frames], dtype=np.float64),
            frame_width=int(frames[0][4]), frame_height=int(frames[0][5]),
            t_start_ms=float(frames[0][3]), t_end_ms=float(frames[-1][3]), t_emit_ms=float(t_emit),
            close_reason=reason)
        self._word_has_sign = True
        return seg

    def _trim(self, ts: float) -> None:
        horizon = ts - self.p["max_segment_ms"]
        k = 0
        while k < len(self._buf) and self._buf[k][3] < horizon:
            k += 1
        if k:
            del self._buf[:k]

    def _motion_now(self, ts: float) -> Optional[float]:
        horizon = ts - self.p["motion_window_ms"]
        while self._hist and self._hist[0][0] <= horizon:
            self._hist.popleft()
        if not self._hist:
            return None
        return float(np.median([m for _, m in self._hist]))

    def _close_lost(self, t_emit: float, reason: str, events: List[Event]) -> None:
        """Hand lost / end of stream: emit the armed buffer (cut at the last hand frame), back to no_hand."""
        if self._tracking and self._armed:
            seg = self._make_segment(self._buf, t_emit, reason)
            if seg is not None:
                events.append(seg)
        self._tracking = False
        self._buf = []
        self._hist.clear()
        self._prev = None
        self._armed = False
        self._still_since = None
        self._move_since = None
        self._hold_progress = 0.0
        self.motion = None

    # ------------------------------------------------------------------ API
    def push(self, ts_ms: float, landmarks: Optional[np.ndarray], handedness: str, width: int,
             height: int) -> List[Event]:
        """One frame: timestamp (ms, strictly increasing), raw landmarks float [21, 3] or None, MediaPipe
        handedness label ('' without hand), frame size. Returns the events emitted by this frame."""
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        if self._last_ts is not None and ts <= self._last_ts:
            raise ValueError(f"timestamps must increase strictly ({ts} after {self._last_ts})")
        if not (int(width) > 0 and int(height) > 0):
            raise ValueError("frame size must be positive")
        self._last_ts = ts
        events: List[Event] = []
        has_hand = landmarks is not None
        size = (int(width), int(height))
        if self._tracking and self._size != size:  # camera size changed: the buffer cannot form one clip
            self._close_lost(ts, "hand_lost", events)
        self._size = size

        if has_hand:
            raw = np.asarray(landmarks, dtype=np.float32).reshape(21, 3).copy()
            if not self._tracking:
                self._tracking = True
                self._buf = []
                self._armed = True
                self._still_since = None
                self._move_since = None
            self._buf.append((raw, True, str(handedness), ts, size[0], size[1]))
            self._last_hand_ts = ts
            self._last_has_hand = True
            p = aspect_points(raw, *size)
            n = normalize_hand_landmarks(p.astype(np.float32)).astype(np.float64)
            if self._prev is not None:
                self._hist.append((ts, frame_motion(self._prev[0], self._prev[1], p, n,
                                                    (ts - self._prev[2]) / 1000.0)))
            self._prev = (p, n, ts)
            self.motion = self._motion_now(ts)
            if self.motion is None:
                self._still_since = None
                self._move_since = None
            elif self.motion <= self.p["still_speed"]:
                if self._still_since is None:
                    self._still_since = ts
                self._move_since = None
            elif self.motion >= self.p["move_speed"]:
                if self._move_since is None:
                    self._move_since = ts
                self._still_since = None
            # in between: hysteresis, both timers kept

            if (not self._armed and self._move_since is not None
                    and ts - self._move_since >= self.p["rearm_move_ms"]):
                self._armed = True
                start = self._move_since
                self._buf = [f for f in self._buf if f[3] >= start]
            self._trim(ts)

            self._hold_progress = 0.0
            if self._armed and self._still_since is not None:
                held = ts - self._still_since
                self._hold_progress = min(1.0, held / self.p["hold_ms"])
                if held >= self.p["hold_ms"] and self._n_detected(self._buf) >= self.min_frames:
                    if self.p["tail_still_keep_ms"] >= self.p["hold_ms"]:
                        buf_for_seg = self._buf  # no filtering: identical to the behaviour before the key
                    else:
                        cutoff = ts - (self.p["hold_ms"] - self.p["tail_still_keep_ms"])
                        buf_for_seg = [f for f in self._buf if f[3] <= cutoff + 1e-6]
                    seg = self._make_segment(buf_for_seg, ts, "hold")
                    if seg is not None:
                        events.append(seg)
                    self._armed = False
                    self._buf = []
                    self._hold_progress = 0.0
        else:
            self._last_has_hand = False
            self._prev = None  # the next hand frame has no consecutive pair
            if self._tracking:
                self._buf.append((np.zeros((21, 3), dtype=np.float32), False, "", ts, size[0], size[1]))
                self._trim(ts)
                if self._last_hand_ts is not None and ts - self._last_hand_ts >= self.p["hand_lost_ms"]:
                    self._close_lost(ts, "hand_lost", events)
            self._hold_progress = 0.0 if not self._tracking else self._hold_progress

        if (not has_hand and self._word_has_sign and self._last_hand_ts is not None
                and ts - self._last_hand_ts >= self.p["word_gap_ms"]):
            self._seq += 1
            events.append(WordGap(seq=self._seq, t_ms=ts))
            self._word_has_sign = False
        return events

    def flush(self, ts_ms: float) -> List[Event]:
        """End of the stream / quit: like a lost hand with close_reason 'end_of_stream'."""
        ts = float(ts_ms)
        if self._last_ts is not None and ts < self._last_ts:
            raise ValueError(f"flush timestamp {ts} is before the last frame {self._last_ts}")
        events: List[Event] = []
        self._close_lost(ts, "end_of_stream", events)
        self._last_has_hand = False
        return events
