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
- pose rules (plan 15 lần sửa 3 §3.2), only when pose_change_rules is true (false: the code above is the whole
  behaviour and rearm_pose_dist is never read): pose_distance(N_a, N_b) = mean over the 21 points of |N_a - N_b| (3D,
  hand lengths);
  1. anchor: when a 'hold' fires, anchor = mean N of the hand frames in [t_emit - motion_window_ms, t_emit]; cleared by
     any re-arm, reset() and a lost hand;
  2. pose re-arm (OR with the motion re-arm): while not armed and anchored, pose_since = first hand frame of the current
     run of hand frames with pose_distance(N_t, anchor) >= rearm_pose_dist (a frame below it ends the run); re-arm when
     ts - pose_since >= rearm_move_ms, the buffer is cut back to pose_since;
  3. stable hold: while the hold clock runs, hold_ref = N of the frame that started it; a frame with
     pose_distance(N_t, hold_ref) >= rearm_pose_dist restarts the hold clock there (armed or not), so a slow change of
     hand shape is not emitted half-way;
- a WordGap after the hand is lost for >= word_gap_ms, only when a sign was emitted since the previous WordGap;
- force_rearm(ts) (key "chữ kế", plan 15 lần sửa 4 §3.1): re-arm at once, buffer cut to ts, a running hold clock
  restarts at ts (a held letter can be emitted again without moving the hand).

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
from src.inference.fingerspelling_compose import TONE_MARKS

SEGMENTER_KEYS = ("motion_window_ms", "still_speed", "move_speed", "hold_ms", "rearm_move_ms", "hand_lost_ms",
                  "word_gap_ms", "max_segment_ms", "min_sign_frames", "tail_still_keep_ms", "pose_change_rules",
                  "rearm_pose_dist")
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


def pose_distance(n_a: np.ndarray, n_b: np.ndarray) -> float:
    """Distance between two normalised hand shapes N [21, 3]: mean over the 21 points of the 3D distance, in hand
    lengths (the shape term of frame_motion without the division by dt)."""
    diff = np.asarray(n_a, dtype=np.float64) - np.asarray(n_b, dtype=np.float64)
    return float(np.mean(np.linalg.norm(diff, axis=-1)))


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
        if not isinstance(self.p["pose_change_rules"], bool):
            raise ValueError("pose_change_rules must be a bool")
        dist = self.p["rearm_pose_dist"]
        if isinstance(dist, bool) or not isinstance(dist, (int, float, np.floating, np.integer)) \
                or not np.isfinite(dist) or not dist > 0:
            raise ValueError("rearm_pose_dist must be a finite number > 0")
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
        self._clear_pose_state()

    def _clear_pose_state(self) -> None:
        """Pose rules state (plan 15 lần sửa 3 §3.2); only filled when pose_change_rules is true."""
        self._anchor: Optional[np.ndarray] = None
        self._pose_since: Optional[float] = None
        self._hold_ref: Optional[np.ndarray] = None
        self._recent_n: Deque[Tuple[float, np.ndarray]] = deque()

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
        self._clear_pose_state()

    # ------------------------------------------------------------------ API
    def force_rearm(self, ts_ms: float) -> None:
        """Key "chữ kế" (plan 15 lần sửa 4 §3.1): re-arm now, so the sign held from ts_ms on is emitted again. Armed =
        True, the buffer keeps only the frames with ts >= ts_ms, a running hold clock restarts at ts_ms (the segment
        then holds only frames after the key), the pose anchor / pose run are cleared. Already armed: only the buffer
        and the hold clock are reset. No hand tracked: nothing changes. Emits nothing."""
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        if not self._tracking:
            return
        self._armed = True
        self._buf = [f for f in self._buf if f[3] >= ts]
        if self._still_since is not None:
            self._still_since = ts
            self._hold_ref = None  # rule 3: the hold reference is taken again from the next hand frame
        self._anchor = None
        self._pose_since = None
        self._hold_progress = 0.0

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
            rules = self.p["pose_change_rules"]
            if rules:  # hand shapes of the last motion_window_ms, for the anchor (rule 1)
                self._recent_n.append((ts, n))
                horizon = ts - self.p["motion_window_ms"]
                while self._recent_n and self._recent_n[0][0] < horizon:
                    self._recent_n.popleft()
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

            if rules:
                # rule 3: the hold clock only runs while the hand shape stays within rearm_pose_dist of where it began
                if self._still_since is None:
                    self._hold_ref = None
                elif self._still_since == ts or self._hold_ref is None:
                    self._hold_ref = n
                elif pose_distance(n, self._hold_ref) >= self.p["rearm_pose_dist"]:
                    self._still_since = ts
                    self._hold_ref = n
                # rule 2: run of hand frames far from the anchor
                if not self._armed and self._anchor is not None:
                    if pose_distance(n, self._anchor) >= self.p["rearm_pose_dist"]:
                        if self._pose_since is None:
                            self._pose_since = ts
                    else:
                        self._pose_since = None

            if (not self._armed and self._move_since is not None
                    and ts - self._move_since >= self.p["rearm_move_ms"]):
                self._armed = True
                start = self._move_since
                self._buf = [f for f in self._buf if f[3] >= start]
                self._anchor = None
                self._pose_since = None
            if (rules and not self._armed and self._pose_since is not None
                    and ts - self._pose_since >= self.p["rearm_move_ms"]):
                self._armed = True
                start = self._pose_since
                self._buf = [f for f in self._buf if f[3] >= start]
                self._anchor = None
                self._pose_since = None
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
                    if rules:  # rule 1: anchor = mean hand shape of [t_emit - motion_window_ms, t_emit]
                        self._anchor = np.mean(np.stack([m for _, m in self._recent_n]), axis=0)
                        self._pose_since = None
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


# ----------------------------------------------------------------------------------------------------------------------
# Classifier re-arm (plan 15 lần sửa 4 §3.2): sliding window + label-change decoder
# ----------------------------------------------------------------------------------------------------------------------
# diacritic letter -> its base letter (a fact of the Vietnamese alphabet, locked by a test): a letter with a diacritic is
# signed as the hand shape of the base letter plus a motion, so a window sees the base letter first
VARIANT_BASE = {"ă": "a", "â": "a", "ê": "e", "ô": "o", "ơ": "o", "ư": "u", "đ": "d"}

DIACRITIC_FUSION = {
    # Base letter -> {trigger signs -> target accented vowel}
    "a": {"â": "â", "ô": "â", "ê": "â", "ă": "ă"},
    "o": {"â": "ô", "ô": "ô", "ê": "ô", "ơ": "ơ", "ư": "ơ"},
    "e": {"â": "ê", "ô": "ê", "ê": "ê"},
    "u": {"ơ": "ư", "ư": "ư"},
    "d": {"đ": "đ"},
}


def is_variant_of(prediction: Optional[str], last: Optional[str]) -> bool:
    """True when prediction is a diacritic variant of last (direct base letter or via diacritic fusion)."""
    if not prediction or not last:
        return False
    if VARIANT_BASE.get(prediction) == last:
        return True
    if last in DIACRITIC_FUSION and prediction in DIACRITIC_FUSION[last]:
        return True
    return False


DECODER_KEYS = ("cls_window_ms", "cls_conf", "cls_stable_ms", "hand_lost_ms")
# optional (plan 15 lần sửa 7 T1): threshold / stable time of the 5 tone marks; an absent key = cls_conf / cls_stable_ms
DECODER_TONE_KEYS = {"cls_conf_tone": "cls_conf", "cls_stable_ms_tone": "cls_stable_ms"}
TONE_LABELS = tuple(TONE_MARKS)
DROPOUT_KEY = "dropout_tolerance_ms"  # optional (plan 15 lần sửa 7 T2): one-frame dropout debounce; absent = off
MOTION_GATE_KEY = "cls_motion_gate"  # optional (plan 15 lần sửa 12 G1): labels only while the hand is still; absent = off
LABEL_ACTIONS = ("append", "replace")
WINDOW_CLOSE_REASON = "window"


@dataclass
class LabelEmit:
    """One label emitted by Level1LabelDecoder. action 'append' = a new letter; 'replace' = the variant of the label
    emitted just before (VARIANT_BASE) replaces it. result = the classify() dict of the frame that emitted."""
    seq: int
    ts_ms: float
    prediction: str
    confidence: float
    action: str
    run_since_ms: float
    result: Dict[str, Any]


def _positive_number(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)) \
            or not np.isfinite(value) or not value > 0:
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")


class WindowBuffer:
    """Frames of the last window_ms (plan 15 lần sửa 4 §3.2). push() every frame (with or without a hand, timestamps
    strictly increasing); segment(t) = SignSegment copy of the frames with ts >= t - window_ms + 1e-6 (the tolerance
    of the planner's measure, docs/plans/15-lan-sua-4-do/analyze2.py window_probs)
    (no-hand frames inside the window included, nothing trimmed: the classifier input is formed exactly like a
    segment, alphabet_clip_features is unchanged), close_reason 'window'; None with < min_detected_frames hand frames.
    A change of frame size starts the window again (the frames cannot form one clip)."""

    def __init__(self, window_ms: float, min_detected_frames: int):
        _positive_number("window_ms", window_ms)
        self.window_ms = float(window_ms)
        self.min_frames = int(min_detected_frames)
        self._seq = 0
        self._last_ts: Optional[float] = None
        self.reset()

    def reset(self) -> None:
        self._buf: Deque[Tuple[np.ndarray, bool, str, float, int, int]] = deque()
        self._size: Optional[Tuple[int, int]] = None

    def _horizon(self, ts: float) -> float:
        """Oldest timestamp inside the window ending at ts."""
        return ts - self.window_ms + 1e-6

    def push(self, ts_ms: float, landmarks: Optional[np.ndarray], handedness: str, width: int, height: int) -> None:
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        if self._last_ts is not None and ts <= self._last_ts:
            raise ValueError(f"timestamps must increase strictly ({ts} after {self._last_ts})")
        if not (int(width) > 0 and int(height) > 0):
            raise ValueError("frame size must be positive")
        self._last_ts = ts
        size = (int(width), int(height))
        if self._size != size:
            self._buf.clear()
        self._size = size
        if landmarks is None:
            self._buf.append((np.zeros((21, 3), dtype=np.float32), False, "", ts, size[0], size[1]))
        else:
            raw = np.asarray(landmarks, dtype=np.float32).reshape(21, 3).copy()
            self._buf.append((raw, True, str(handedness), ts, size[0], size[1]))
        horizon = self._horizon(ts)
        while self._buf and self._buf[0][3] < horizon:
            self._buf.popleft()

    def segment(self, ts_ms: float) -> Optional[SignSegment]:
        horizon = self._horizon(float(ts_ms))
        frames = [f for f in self._buf if horizon <= f[3] <= float(ts_ms)]
        if sum(1 for f in frames if f[1]) < self.min_frames:
            return None
        self._seq += 1
        return SignSegment(
            seq=self._seq,
            raw_landmarks=np.stack([f[0] for f in frames]).astype(np.float32, copy=True),
            detected=np.array([f[1] for f in frames], dtype=bool),
            handedness=np.array([f[2] for f in frames], dtype=object).astype(str),
            timestamps_ms=np.array([f[3] for f in frames], dtype=np.float64),
            frame_width=int(frames[0][4]), frame_height=int(frames[0][5]),
            t_start_ms=float(frames[0][3]), t_end_ms=float(frames[-1][3]), t_emit_ms=float(ts_ms),
            close_reason=WINDOW_CLOSE_REASON)


class Level1LabelDecoder:
    """Label-change decoder over the per-frame window classification (plan 15 lần sửa 4 §3.2, rules fixed before the
    D4 measurement, same as the decoder of docs/plans/15-lan-sua-4-do/analyze5.py):

    1. frame label = result['prediction'] when result['status'] == 'ok' and result['confidence'] >= cls_conf, else
       None; a label different from the running one (or None) starts a new run at this frame. A hand frame with
       result None (window too short, or its job dropped by the worker) has no result and leaves the run as it is.
    2. emit when the label is not None, ts - run_since >= cls_stable_ms and label != last emitted label; then
       last = label.
       Tone marks (plan 15 lần sửa 7 T1): a prediction among the 5 tone marks uses cls_conf_tone in rule 1 and
       cls_stable_ms_tone in rule 2 (thresholds(label)); each key is optional and falls back to cls_conf /
       cls_stable_ms, so without them the decoder is the decoder of D4 exactly.
    3. replace: when VARIANT_BASE[label] == last (and a label was emitted before), action 'replace', else 'append'.
    4. no hand for >= hand_lost_ms: last = None and the run is cleared (withdraw the hand and sign again = the same
       letter may come again); force_next(ts) (key n): last = None.
    5. timestamps strictly increasing (ValueError otherwise).
    6. one-frame dropout debounce (plan 15 lần sửa 7 T2), only when dropout_tolerance_ms is given (absent = off, the
       decoder of D4): a hand frame with a result whose label is None (rule 1) while a run is going on does not end
       the run at once; the next hand frame with a result decides: its label is the run label and it comes at most
       dropout_tolerance_ms after the dropped frame -> the run goes on from its start (the dropped frame counts as a
       frame without result); otherwise the run restarts at the dropped frame exactly as without the debounce. No-hand
       frames and hand frames without result in between do not decide (rule 1, rule 4 still apply).
    7. motion gate (plan 15 lần sửa 12 G1), only when cls_motion_gate is true (absent / false = off, the decoder above
       exactly): a hand frame pushed with moving=True (the caller passes Level1SignSegmenter.state == 'moving' of the
       same frame: the hand moves or changes shape, M_t >= move_speed with the segmenter's hysteresis, or no motion
       measured yet) ends the run at once, whatever its result (no dropout debounce: a motion is not a dropout), and
       emits nothing; so a label is emitted only after it held cls_stable_ms on frames where the hand was still. The
       window itself is unchanged (a tone mark's stroke stays in the window after the hand stops). Exception: a frame
       whose prediction is the diacritic variant of the label emitted last (VARIANT_BASE[prediction] == last, the
       'replace' case of rule 3) is not gated: the motion of â, ă, ê, ô, ơ, ư, đ right after their base letter is part
       of the sign, not a transition. n_gated counts the frames ended by the gate.
    Parameters come from the caller (config); no default value here. Pure computation, not thread-safe."""

    def __init__(self, params: Dict[str, Any]):
        missing = [k for k in DECODER_KEYS if k not in params]
        if missing:
            raise ValueError(f"decoder parameters missing: {missing}")
        self.p = {k: params[k] for k in DECODER_KEYS}
        for k in ("cls_window_ms", "cls_stable_ms", "hand_lost_ms"):
            _positive_number(k, self.p[k])
        conf = self.p["cls_conf"]
        _positive_number("cls_conf", conf)
        if not conf <= 1:
            raise ValueError(f"cls_conf must be in (0, 1], got {conf!r}")
        self.p_tone = {}  # the letter key each optional tone key replaces -> value used for tone marks
        for key, base in DECODER_TONE_KEYS.items():
            value = params[key] if key in params else self.p[base]
            _positive_number(key, value)
            self.p_tone[base] = value
        if not self.p_tone["cls_conf"] <= 1:
            raise ValueError(f"cls_conf_tone must be in (0, 1], got {self.p_tone['cls_conf']!r}")
        if DROPOUT_KEY in params:
            _positive_number(DROPOUT_KEY, params[DROPOUT_KEY])
        self.dropout_tolerance_ms = float(params[DROPOUT_KEY]) if DROPOUT_KEY in params else 0.0
        gate = params.get(MOTION_GATE_KEY, False)
        if not isinstance(gate, bool):
            raise ValueError(f"{MOTION_GATE_KEY} must be true or false, got {gate!r}")
        self.motion_gate = gate
        self.n_gated = 0
        self._seq = 0
        self._n_emitted = 0
        self._last_ts: Optional[float] = None
        self.reset()

    def reset(self) -> None:
        """Clears the last label, the run and the hand clock (tracking paused). The emission counter is kept."""
        self._last: Optional[str] = None
        self._run_label: Optional[str] = None
        self._run_since: Optional[float] = None
        self._last_hand_ts: Optional[float] = None
        self._drop_ts: Optional[float] = None  # rule 6: timestamp of the dropped frame waiting for the next result

    @property
    def last_label(self) -> Optional[str]:
        return self._last

    @staticmethod
    def is_tone(label: Optional[str]) -> bool:
        return label in TONE_LABELS

    def thresholds(self, label: Optional[str]) -> Tuple[float, float]:
        """(minimum confidence, stable time in ms) applied to a window predicting `label` (rules 1 and 2)."""
        p = self.p_tone if self.is_tone(label) else self.p
        return p["cls_conf"], p["cls_stable_ms"]

    def force_next(self, ts_ms: float) -> None:
        """Key n "chữ kế": the label held now may be emitted again."""
        if not np.isfinite(float(ts_ms)):
            raise ValueError("timestamp must be finite")
        self._last = None

    def push(self, ts_ms: float, has_hand: bool, result: Optional[Dict[str, Any]],
             moving: bool = False) -> Optional[LabelEmit]:
        """One frame (rules 1-7); moving is read only when cls_motion_gate is true."""
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        if self._last_ts is not None and ts <= self._last_ts:
            raise ValueError(f"timestamps must increase strictly ({ts} after {self._last_ts})")
        self._last_ts = ts
        if not has_hand:
            if self._last_hand_ts is not None and ts - self._last_hand_ts >= self.p["hand_lost_ms"]:
                self._last = None
                self._run_label = None
                self._drop_ts = None
            return None
        self._last_hand_ts = ts
        pred = result.get("prediction") if result is not None else None
        variant_of_last = is_variant_of(pred, self._last)
        if self.motion_gate and moving and not variant_of_last:  # rule 7: a moving hand is a transition, not a letter
            self._run_label, self._run_since, self._drop_ts = None, ts, None
            self.n_gated += 1
            return None
        if result is None:
            return None
        conf = result.get("confidence")
        min_conf, stable_ms = self.thresholds(result.get("prediction"))
        label = result.get("prediction") if (result.get("status") == "ok" and conf is not None
                                             and conf >= min_conf) else None
        if self._drop_ts is not None:  # rule 6: this frame decides about the dropped one
            drop_ts, self._drop_ts = self._drop_ts, None
            if not (label is not None and label == self._run_label and ts - drop_ts <= self.dropout_tolerance_ms):
                self._run_label, self._run_since = None, drop_ts  # as if the run had restarted at the dropped frame
        elif label is None and self._run_label is not None and self.dropout_tolerance_ms > 0:
            self._drop_ts = ts
            return None
        if label is None or label != self._run_label:
            self._run_label, self._run_since = label, ts
        if label is None or ts - self._run_since < stable_ms or label == self._last:
            return None
        replace = self._n_emitted > 0 and self._last is not None and VARIANT_BASE.get(label) == self._last
        self._last = label
        self._seq += 1
        self._n_emitted += 1
        return LabelEmit(seq=self._seq, ts_ms=ts, prediction=label, confidence=float(conf),
                         action="replace" if replace else "append", run_since_ms=float(self._run_since),
                         result=result)
