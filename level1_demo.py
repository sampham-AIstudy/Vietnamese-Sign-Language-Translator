"""
Level 1 ("Đánh vần") realtime desktop app (plan 15): webcam -> MediaPipe Hands (same extractor and keywords as
training) -> automatic sign segmentation -> Level 1 checkpoint -> tokens composed into Vietnamese text, shown in an
OpenCV window with the landmarks drawn on the very frame that was processed.

Run (from the project root, inside .venv):
  python level1_demo.py --source 0                         webcam 0 in a window
  python level1_demo.py --source 0 --display-mirror        same, shown like a mirror (processing is never mirrored)
  python level1_demo.py --source 0 --expected "ba" --out-json reports/level1_realtime_<D>/webcam_ba_1.json
  python level1_demo.py --source <video.mp4> --headless --out-json out.json      every frame, no window
  python level1_demo.py --source <video.mp4> --pace realtime [--headless]        read at the file's frame rate, newest
                                                                                 frame only (like a webcam)
  python level1_demo.py --source 0 --config configs/level1_demo_classifier.json --cls-window-ms <N> --no-auto-space
                                    window of N milliseconds for this run; no automatic space (Space key only)
  python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json \
                        --min-detection-conf 0.35 --auto-enhance
                                    MediaPipe hand detection threshold 0.35 for this run (edge-on hands); dark frames
                                    (mean gray level below the threshold) get CLAHE before MediaPipe, the window still
                                    shows the camera frame (plan 15 lần sửa 8; HUD line [MP: conf=... | CLAHE: ...])
  python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json \
                        --min-detection-conf 0.35 --auto-enhance --no-auto-space
                                    spaces only from the open palm gesture (or the Space key), plan 15 lần sửa 9
  python level1_demo.py --source 0 --smooth-landmarks
                                    hand points smoothed by LandmarkSmoother (adaptive moving average: strong while
                                    the hand is still, light while it moves) before the segmenter, the window, the
                                    gesture and the drawing (plan 15 lần sửa 10 P2; default off)
  python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev9.json \
                        --min-detection-conf 0.35 --auto-enhance --dominant-hand lock
                                    multi-sign spelling (plan 15 lần sửa 12): classifier re-arm with the motion gate (a
                                    label counts only while the hand is still), handedness locked to the majority of
                                    MediaPipe's own labels on the first hand frames (HUD line [Tay: khóa ...]); spaces
                                    from the Space key only
  --dominant-hand Right / Left (lần sửa 10 P1) are aliases of lock since lần sửa 12 H1: the fixed label they gave
  (Right -> 'Left') mirrored x on every frame of a camera whose driver mirrors the frames.
HUD angle hint (plan 15 lần sửa 10 P3, always on): index finger pointing at the camera (foreshortening_ratio < 0.3) on
  more than 3 consecutive hand frames -> yellow line [Góc tay: Hơi nghiêng tay 20°]; HUD only (JSON unchanged).
Keys (window): Backspace delete last token | Space add a space | a accept the last rejected candidate |
  r repeat the last letter | n next letter (re-arm: the letter held now is emitted again) | c clear |
  p pause / resume segmentation | f fullscreen | q or Esc quit.
Automatic spaces are off by default since plan 15 lần sửa 12 S1: --auto-space adds a space after the hand is away for
  word_gap_ms, --gesture-space turns the open palm gesture on; the Space key always adds one.
Gesture (plan 15 lần sửa 9, with --gesture-space): open palm (5 fingers spread, thumb out) held --space-hold-ms
  (default 250) = Space, once per gesture (change the hand shape or withdraw the hand before the next one); HUD line
  [Cử chỉ: Dấu cách <held>/<hold>] while held, [Ký hiệu: Dấu cách (Space)] right after. In rearm_mode classifier an
  open-palm frame reaches the window as a frame without hand (it is never classified as a letter).

Re-arm (config rearm_mode, written to the JSON as rearm_mode; plan 15 lần sửa 4 §3.4):
  motion_pose  every SignSegment of the segmenter is classified and gives one token (behaviour before lần sửa 4)
  classifier   at every hand frame the last cls_window_ms are classified (stage window_classify) and the label decoder
               emits a token when the window label changes; the segmenter still runs for the HUD state, hand_lost and
               word gaps, its segments are counted but not classified

Modes (written to the JSON as source.mode):
  gui      webcam (newest frame only, camera thread) or a video shown frame by frame; classification in a worker
  paced    video read by the camera thread at the file's frame rate, newest frame only; classification in a worker
  headless video, every frame in order, timestamps i * 1000 / fps, classification in the main loop (deterministic)

The app never writes video, frames or landmarks; the JSON holds tokens, events, timings and statistics only.
"""
import argparse
import collections
import datetime
import functools
import hashlib
import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.inference.hand_live import LEVEL1_HANDS_KWARGS, HandLandmarkSession  # noqa: E402
from src.inference.level1_display import (PanelBuilder, draw_panel_overlays, fit_layout,  # noqa: E402
                                          render_to_window, scaled_px)
from src.inference.level1_core import (CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID, GESTURE_BACKSPACE_DEFAULT,  # noqa: E402
                                       GESTURE_BACKSPACE_FLASH, LOW_LIGHT_THRESHOLD, BackspaceGestureTracker,
                                       HandednessLock, LandmarkSmoother, Level1Classifier, Level1Speller,
                                       enhance_low_light, foreshortening_ratio, is_flat_hand_backspace,
                                       is_open_palm_space, load_level1_config)
from src.inference.level1_segmenter import (Level1LabelDecoder, Level1SignSegmenter, SignSegment,  # noqa: E402
                                            WindowBuffer, WordGap, aspect_points)
from src.inference.level1_timing import (FRAME_STAGES, SIGN_STAGES, StageTimes,  # noqa: E402
                                         rate_from_timestamps)

DEFAULT_CONFIG = os.path.join("configs", "level1_realtime.json")      # relative to the repository root
DEFAULT_CHECKPOINT = os.path.join("checkpoints", "alphabet_best.pt")  # relative to the repository root
WINDOW_NAME = "VSLT Level 1 (f: toàn màn hình)"
EXIT_INPUT_ERROR = 2
CODE_PATHS = ("level1_demo.py", "src", "configs/level1_realtime.json")
NOTE = ("Durations are measured inside the app with time.perf_counter, from the moment a frame is received from "
        "the capture call to the end of each stage (frame_total ends after imshow + waitKey in a window, after the "
        "segmenter in headless mode). In headless mode nothing is drawn or shown, so draw_landmarks, hud and display "
        "have n = 0. emit_to_token runs from the moment a segment is emitted to the end of imshow of the first frame "
        "showing its result (headless: to the moment the result is applied); results that arrive after the last "
        "frame are never shown (counts.results_not_displayed). warmup = first MediaPipe graph run and first model "
        "run, measured apart and not included in stages. Camera sensor / driver delay and display delay are not "
        "measured. These desktop numbers do not replace the WebSocket end-to-end measurement required for the web "
        "app (DoD 8). A letter appears only after the designed hold time (config hold_ms), on top of the processing "
        "time.")
HUD_STAGE_LABELS = (("capture_age", "cap_age"), ("mediapipe", "mp"), ("segmenter", "seg"), ("draw_landmarks", "draw"),
                    ("hud", "hud"), ("display", "disp"), ("frame_total", "total"), ("classify", "classify"),
                    ("emit_to_token", "emit>token"))
KEY_ACTIONS = {
    8: "backspace",
    32: "space",
    ord("a"): "accept",
    ord("r"): "repeat",
    ord("c"): "clear",
    ord("1"): "tone_1",
    ord("2"): "tone_2",
    ord("3"): "tone_3",
    ord("4"): "tone_4",
    ord("5"): "tone_5",
    ord("n"): "next",
}
WINDOW_STAGES = ("window_classify",)  # rearm_mode 'classifier' only: one window classification per hand frame
# --auto-enhance only (plan 15 lần sửa 8 M3): enhance_low_light of every processed frame, before (not in) mediapipe
ENHANCE_STAGES = ("low_light_enhance",)
# --smooth-landmarks only (plan 15 lần sửa 10 P2): LandmarkSmoother.filter of every processed frame, after mediapipe
SMOOTH_STAGES = ("landmark_smooth",)
# --min-detection-conf default: the value of training and of the WebSocket path (LEVEL1_HANDS_KWARGS, not changed)
DEFAULT_MIN_DETECTION_CONF = LEVEL1_HANDS_KWARGS["min_detection_confidence"]
KEY_NEXT = "next"  # app action (segmenter / decoder re-arm), not a Level1Speller key
KEY_QUIT = (ord("q"), 27)
KEY_PAUSE = ord("p")
KEY_FULLSCREEN = ord("f")
STATE_LABELS = {"no_hand": "không thấy tay", "moving": "đang chuyển động", "holding": "đang giữ yên"}
# --trace-windows (plan 15 lần sửa 6 §3.W1): one entry per classified window, in the order the decoder applies them
TRACE_KEYS = ("ts_ms", "status", "top1", "conf", "top2", "conf2", "run_label", "run_ms", "last", "emitted")
TRACE_MAX_ENTRIES = 20000  # later windows are counted (n_windows) but not kept; truncated = true
# open palm gesture = Space (plan 15 lần sửa 9 §2 S2), in milliseconds of stream time. Hold and re-arm are design values
# of the plan (not measurements); the flash time of the HUD line is the coder's value. Written without the unit in the
# name: the source guard reads a metric-named binding (..._ms) set to a literal as a hand-typed performance number.
GESTURE_SPACE_HOLD = 250.0    # open palm held this long (armed) -> one space
GESTURE_SPACE_REARM = 150.0   # another hand shape held longer than this (or no hand) -> armed again
GESTURE_SPACE_FLASH = 600.0   # "[Ký hiệu: Dấu cách (Space)]" shown this long after the space
# --smooth-landmarks default (plan 15 lần sửa 10 P2): OFF. The plan writes default=True, but its AC-10d / §1 require the
# run without the new flags to be the app of before; smoothing changes the landmarks of every frame, so the segments and
# windows of the default run (pinned by the older tests against earlier commits) would change.
SMOOTH_LANDMARKS_DEFAULT = False
# angle hint (plan 15 lần sửa 10 P3, design values of the plan): foreshortening_ratio below FORESHORTEN_RATIO_MIN (index
# finger pointing at the camera) on more than FORESHORTEN_FRAMES consecutive hand frames -> HUD line ANGLE_HINT_LINE
FORESHORTEN_RATIO_MIN = 0.3
FORESHORTEN_FRAMES = 3
ANGLE_HINT_LINE = "[Góc tay: Hơi nghiêng tay 20°]"
# --dominant-hand (plan 15 lần sửa 12 H1, replaces the fixed labels of lần sửa 10 P1): 'auto' = MediaPipe's label of
# each frame; 'lock' = HandednessLock, the majority of MediaPipe's own labels on the first hand frames, for the rest of
# the run. Lần sửa 10 gave every frame a label chosen from the signer's hand (Right -> 'Left'), assuming the camera never
# mirrors; on a camera whose driver mirrors, MediaPipe labels a right hand 'Right', so the fixed 'Left' mirrored x on
# every frame (thumb and little finger swapped). Measured on the collected_targeted clips:
# reports/level1_realtime_2026-10-06/dominant_hand_check.json. Right / Left are kept as aliases of 'lock'.
DOMINANT_HAND_CHOICES = ("auto", "lock", "Right", "Left")
DOMINANT_HAND_ALIASES = ("Right", "Left")
HAND_LOCK_HUD = "[Tay: khóa {label}]"
HAND_LOCKING_HUD = "[Tay: đang khóa {n}/{total}]"
# automatic spaces (plan 15 lần sửa 12 S1): OFF by default. A short loss of the hand (word gap) and a relaxed open hand
# (gesture) both added spaces the signer did not want in the middle of a word; --auto-space / --gesture-space turn them on
AUTO_SPACE_DEFAULT = False
GESTURE_SPACE_DEFAULT = False


class SourceError(Exception):
    """Input problem reported to the user (exit code EXIT_INPUT_ERROR)."""


# ---------------------------------------------------------------------------------------------------------- sources
def video_fps(cap) -> float:
    """Frame rate stored in the video; SourceError when it cannot be read (no default frame rate)."""
    value = cap.get(cv2.CAP_PROP_FPS)
    try:
        rate = float(value)
    except (TypeError, ValueError):
        rate = float("nan")
    if not np.isfinite(rate) or rate <= 0:
        raise SourceError(f"cannot read the frame rate of the video (CAP_PROP_FPS = {value!r}); "
                          "no default frame rate is used")
    return rate


class VideoFileReader:
    """Frames of a video file in order (BGR, exactly as cv2.VideoCapture decodes them)."""
    kind = "video"

    def __init__(self, path: str, capture_factory=cv2.VideoCapture):
        if not os.path.isfile(path):
            raise SourceError(f"video not found: {path}")
        self.path = path
        self.cap = capture_factory(path)
        if not self.cap.isOpened():
            raise SourceError(f"cannot open video: {path}")
        self.fps = video_fps(self.cap)
        self.props = None

    def read(self) -> Optional[np.ndarray]:
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self) -> None:
        self.cap.release()


class CameraReader:
    """Webcam opened with the backend and size of the config; the values read back are kept in .props."""
    kind = "webcam"
    APIS = {"dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF, "any": cv2.CAP_ANY}

    def __init__(self, index: int, values: Dict[str, Any]):
        self.index = index
        self.cap = cv2.VideoCapture(index, self.APIS[values["camera_api"]])
        if not self.cap.isOpened():
            raise SourceError(f"cannot open webcam {index} (camera_api {values['camera_api']!r})")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, values["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, values["camera_height"])
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, values["camera_buffersize"])
        self.fps = None
        self.props = {"camera_api": values["camera_api"], "backend": self.cap.getBackendName(),
                      "width": self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                      "height": self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                      "fps_reported": self.cap.get(cv2.CAP_PROP_FPS),
                      "buffersize": self.cap.get(cv2.CAP_PROP_BUFFERSIZE),
                      "requested": {"width": values["camera_width"], "height": values["camera_height"],
                                    "buffersize": values["camera_buffersize"]}}

    def read(self) -> Optional[np.ndarray]:
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self) -> None:
        self.cap.release()


class LatestFrameSlot:
    """One slot holding the newest captured frame. put() overwrites an unread frame (counted in .dropped);
    get() returns the newest frame and empties the slot, so a frame older than one already returned is never
    returned."""

    def __init__(self):
        self._cond = threading.Condition()
        self._item = None
        self.put_count = 0
        self.dropped = 0
        self.closed = False

    def put(self, frame: np.ndarray, t_cap: float, ts_ms: float) -> None:
        with self._cond:
            if self._item is not None:
                self.dropped += 1
            self.put_count += 1
            self._item = (self.put_count, frame, t_cap, ts_ms)
            self._cond.notify_all()

    def close(self) -> None:
        with self._cond:
            self.closed = True
            self._cond.notify_all()

    def get(self, timeout: float):
        """(seq, frame, t_cap, ts_ms) of the newest unread frame, or None after `timeout` seconds / when closed
        and empty."""
        with self._cond:
            self._cond.wait_for(lambda: self._item is not None or self.closed, timeout)
            item, self._item = self._item, None
            return item


class CaptureThread(threading.Thread):
    """Reads the source as fast as it delivers (webcam) or at the file's frame rate (paced video) and puts every
    frame into the slot. Timestamps: webcam = capture time; video = i * 1000 / fps of the file."""

    def __init__(self, reader, slot: LatestFrameSlot, paced: bool, origin: float):
        super().__init__(daemon=True)
        self.reader, self.slot, self.paced, self.origin = reader, slot, paced, origin
        self.frames_read = 0
        self.read_times: List[float] = []  # perf_counter (s) of every frame read, for counts.capture_fps
        self.error: Optional[BaseException] = None
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            start = time.perf_counter()
            while not self._stop_event.is_set():
                if self.paced:
                    wait = start + self.frames_read / self.reader.fps - time.perf_counter()
                    if wait > 0:
                        time.sleep(wait)
                frame = self.reader.read()
                if frame is None:
                    break
                t_cap = time.perf_counter()
                self.read_times.append(t_cap)
                if self.reader.fps is None:
                    ts_ms = (t_cap - self.origin) * 1000.0
                else:
                    ts_ms = self.frames_read * 1000.0 / self.reader.fps
                self.frames_read += 1
                self.slot.put(frame, t_cap, ts_ms)
        except BaseException as e:  # reported by the main loop
            self.error = e
        finally:
            self.slot.close()


class ClassifyWorker(threading.Thread):
    """Classifies SignSegments off the main loop, in submission order."""

    def __init__(self, classifier, top_k: int):
        super().__init__(daemon=True)
        self.classifier, self.top_k = classifier, top_k
        self._in: "queue.Queue" = queue.Queue()
        self._out: "queue.Queue" = queue.Queue()

    def submit(self, seg: SignSegment) -> None:
        self._in.put(seg)

    def run(self) -> None:
        while True:
            seg = self._in.get()
            if seg is None:
                return
            t0 = time.perf_counter()
            try:
                result = self.classifier.classify(seg, self.top_k)
                self._out.put((seg, result, (time.perf_counter() - t0) * 1000.0, None))
            except BaseException as e:  # re-raised in the main loop
                self._out.put((seg, None, None, e))

    def poll(self) -> List:
        out = []
        while True:
            try:
                out.append(self._out.get_nowait())
            except queue.Empty:
                return out

    def finish(self) -> List:
        self._in.put(None)
        self.join()
        return self.poll()


class LatestWindowWorker(threading.Thread):
    """Window classifications off the main loop, keeping only the newest job (plan 15 lần sửa 4 §3.4): submit()
    replaces a job that has not started yet (that job is dropped: returned to the caller and counted in .dropped), so
    a result older than one already returned never comes back. Results: (job_id, ts_ms, result, classify_ms, error)."""

    def __init__(self, classifier, top_k: int):
        super().__init__(daemon=True)
        self.classifier, self.top_k = classifier, top_k
        self._cond = threading.Condition()
        self._job = None
        self._closed = False
        self._out: "queue.Queue" = queue.Queue()
        self.submitted = 0
        self.dropped = 0

    def submit(self, job_id: int, ts_ms: float, seg: SignSegment) -> Optional[int]:
        """Queues the job; returns the id of the job it replaced (dropped) or None."""
        with self._cond:
            dropped = None
            if self._job is not None:
                dropped = self._job[0]
                self.dropped += 1
            self.submitted += 1
            self._job = (job_id, ts_ms, seg)
            self._cond.notify_all()
            return dropped

    def run(self) -> None:
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._job is not None or self._closed)
                if self._job is None:
                    return
                job, self._job = self._job, None
            job_id, ts_ms, seg = job
            t0 = time.perf_counter()
            try:
                result = self.classifier.classify(seg, self.top_k)
                self._out.put((job_id, ts_ms, result, (time.perf_counter() - t0) * 1000.0, None))
            except BaseException as e:  # re-raised in the main loop
                self._out.put((job_id, ts_ms, None, None, e))

    def poll(self) -> List:
        out = []
        while True:
            try:
                out.append(self._out.get_nowait())
            except queue.Empty:
                return out

    def finish(self) -> List:
        """Runs the job still queued, stops, returns the remaining results."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()
        self.join()
        return self.poll()


# ---------------------------------------------------------------------------------------------------------- drawing
def _hand_connections():
    import mediapipe as mp
    return sorted(tuple(c) for c in mp.solutions.hands.HAND_CONNECTIONS)


HAND_CONNECTIONS = _hand_connections()


def draw_landmarks(frame: np.ndarray, landmarks: Optional[np.ndarray]) -> None:
    """Draws the 21 points on `frame` (the frame that was processed, unmirrored, in place)."""
    if landmarks is None:
        return
    h, w = frame.shape[:2]
    pts = [(int(round(float(x) * w)), int(round(float(y) * h))) for x, y, _ in landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2, cv2.LINE_AA)
    for p in pts:
        cv2.circle(frame, p, 4, (0, 0, 255), -1, cv2.LINE_AA)


def display_view(frame: np.ndarray, mirror: bool) -> np.ndarray:
    """Image shown in the window: mirrored only for display (after the landmarks were drawn)."""
    return cv2.flip(frame, 1) if mirror else frame


def find_font(explicit: Optional[str], candidates: List[str]) -> str:
    if explicit:
        if not os.path.isfile(explicit):
            raise SourceError(f"font not found: {explicit}")
        return explicit
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise SourceError("no TrueType font with Vietnamese glyphs found (config font_paths); pass --font <file.ttf>")


class Hud:
    """Text panel drawn with PIL (Vietnamese glyphs), shown below the camera image. The panel image is rebuilt only
    when its text changes (cache).

    Display scale (plan 15 lần sửa 13 U1): the panel can also be built at a scale (`panel_builder`, used by
    src.inference.level1_display.render_to_window for a resized / fullscreen window): the font is the font size x
    scale in pixels (fonts cached per pixel size, never rebuilt per frame), every distance below is its natural value
    x scale, rounded down. Scale 1.0 draws exactly the natural panel."""

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
    HINT_RGB = (255, 215, 0)  # small lines starting with HINT_PREFIX (angle hint, lần sửa 10 P3): yellow
    HINT_BGR = (0, 215, 255)
    HINT_PREFIX = "[Góc tay:"
    SMALL_RGB = (200, 220, 255)
    # Panel geometry at natural size (scale 1.0), the values the HUD has always used (B3, text box lần sửa 6):
    LINE_RATIO = 1.35        # main line step = font px x 1.35
    SMALL_LINE_RATIO = 0.95  # small line step = font px x 0.95 (small font = 2/3 of the font, _small_px)
    PAD_X = 8                # text inset from the left edge
    PAD_TOP = 4              # padding above the first line
    PAD_BOTTOM = 4           # padding below the last line
    CURSOR_MARGIN = 24       # room kept free right of the cursor when old words are dropped (_fit_committed)
    MIN_CURSOR_W = 100       # the committed text keeps at least this width
    HIGHLIGHT_INSET = 2      # active-syllable highlight stops this far above the next line
    CURSOR_INSET_TOP = 2     # cursor line: inset from the top of the line
    CURSOR_INSET_BOTTOM = 4  # cursor line: inset from the bottom of the line
    CURSOR_WIDTH = 2
    PREVIEW_GAP = 4          # gap between the cursor and the preview label

    def __init__(self, font_path: str, font_size: int):
        from PIL import ImageFont
        self.font_path = font_path
        self.font_size = font_size
        self.font = ImageFont.truetype(font_path, font_size)
        self.small = ImageFont.truetype(font_path, self._small_px(font_size))
        self.line_h = int(font_size * self.LINE_RATIO)
        self.small_h = int(font_size * self.SMALL_LINE_RATIO)
        self._key = None
        self._panel = None
        self._fonts = collections.OrderedDict([(font_size, (self.font, self.small))])  # font px -> (font, small font)
        self._scaled_key = None
        self._scaled_panel = None

    @staticmethod
    def _small_px(font_px: int) -> int:
        return max(1, int(font_px * 2 / 3))

    def font_px(self, scale: float = 1.0) -> int:
        """Main font size in pixels at `scale` (round(font size x scale); the font size itself at scale 1.0)."""
        return max(1, int(round(self.font_size * scale)))

    def _fonts_at(self, scale: float) -> Tuple[Any, Any]:
        """(main font, small font) at `scale`; created once per pixel size."""
        px = self.font_px(scale)
        if px in self._fonts:
            self._fonts.move_to_end(px)
            return self._fonts[px]
        from PIL import ImageFont
        pair = (ImageFont.truetype(self.font_path, px),
                ImageFont.truetype(self.font_path, self._small_px(px)))
        self._fonts[px] = pair
        while len(self._fonts) > 8:
            self._fonts.popitem(last=False)
        return pair

    def line_steps(self, scale: float = 1.0) -> Tuple[int, int]:
        """(main line step, small line step) in px at `scale`: the natural steps x scale, rounded down."""
        return scaled_px(self.line_h, scale), scaled_px(self.small_h, scale)

    def panel_height(self, text_or_view: Any, small: Sequence[str], n_stats: int, scale: float = 1.0) -> int:
        """Height of the panel built by _build for this text (rows of the live stats lines included), without
        building it; at scale 1.0 = the height of the panel under the camera image in compose."""
        line_h, small_h = self.line_steps(scale)
        num_big = 1 if isinstance(text_or_view, dict) else len(text_or_view)
        return (line_h * num_big + small_h * (len(small) + n_stats)
                + scaled_px(self.PAD_TOP, scale) + scaled_px(self.PAD_BOTTOM, scale))

    def _fit_committed(self, committed: str, active: str, max_w: float, font: Any = None) -> str:
        """Drops committed syllables from the start (prepending '…') until cursor fits in max_w."""
        font = self.font if font is None else font
        if not committed:
            return ""
        if font.getlength(committed + active) <= max_w:
            return committed
        import re
        words = re.findall(r"\S+\s*", committed)
        if not words:
            return "… "
        for i in range(1, len(words) + 1):
            rem = "".join(words[i:])
            cand = "… " + rem if rem else "… "
            if font.getlength(cand + active) <= max_w:
                return cand
        return "… "

    def _build(self, width: int, view: Any, small: List[str], n_stats: int, scale: float = 1.0,
               height: Optional[int] = None) -> np.ndarray:
        """Panel image (BGR) of `width` px; `height` defaults to panel_height (the rows of the live stats lines are
        kept free at the bottom). `scale` != 1.0: scaled font and distances (window layout slot as `height`)."""
        from PIL import Image, ImageDraw
        font, small_font = self._fonts_at(scale)
        line_h, small_h = self.line_steps(scale)

        def px(value):
            return scaled_px(value, scale)

        is_view_dict = isinstance(view, dict)
        if height is None:
            height = self.panel_height(view, small, n_stats, scale)
        img = Image.new("RGB", (width, height), self.BG_RGB)
        d = ImageDraw.Draw(img)
        y = px(self.PAD_TOP)

        if not is_view_dict:
            for text in view:
                d.text((px(self.PAD_X), y), text, font=font, fill=self.TEXT_RGB)
                y += line_h
        else:
            committed = view.get("committed", "")
            active = view.get("active", "")
            preview = view.get("preview")

            x0 = px(self.PAD_X)
            max_cursor_w = max(width - px(self.CURSOR_MARGIN) - x0, px(self.MIN_CURSOR_W))
            disp_committed = self._fit_committed(committed, active, max_cursor_w, font)

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
                d.rectangle([(rect_x0, y), (rect_x1, y + line_h - px(self.HIGHLIGHT_INSET))], fill=self.HIGHLIGHT_RGB)
                d.text((rect_x0, y), active, font=font, fill=self.TEXT_RGB)

            # 3. Cursor
            x_cursor = int(round(x_active + w_act))
            d.line([(x_cursor, y + px(self.CURSOR_INSET_TOP)), (x_cursor, y + line_h - px(self.CURSOR_INSET_BOTTOM))],
                   fill=self.CURSOR_RGB, width=max(1, px(self.CURSOR_WIDTH)))

            # 4. Preview
            if preview is not None and (preview.get("token") is not None or preview.get("prediction") is not None):
                conf = preview.get("confidence")
                conf_str = f"{conf:.2f}" if conf is not None else ""
                active_if = preview.get("active_if_accepted", "")
                if active_if:
                    prev_label = f" {active_if} (a: nhận, {conf_str})"
                else:
                    prev_label = f" (a: nhận, {conf_str})"
                x_prev = x_cursor + px(self.PREVIEW_GAP)
                d.text((x_prev, y), prev_label, font=font, fill=self.PREVIEW_RGB)

            y += line_h

        for text in small:
            d.text((px(self.PAD_X), y), text, font=small_font,
                   fill=self.HINT_RGB if text.startswith(self.HINT_PREFIX) else self.SMALL_RGB)
            y += small_h
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _view_cache_key(v: Any) -> tuple:
        if not isinstance(v, dict):
            return tuple(v)
        prev = v.get("preview")
        if prev is not None:
            prev_key = (prev.get("token"), prev.get("prediction"), prev.get("confidence"), prev.get("active_if_accepted"))
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

    def compose(self, view: np.ndarray, text_or_view: Any, small: List[str], hold_progress: float,
                stats_lines: Sequence[str] = ()) -> np.ndarray:
        """Window image = the camera image with the text panel stacked BELOW it (the hand is never covered); a
        green bar on top of the panel shows the hold progress. The PIL panel (Vietnamese text) is cached; the live
        stats lines (ASCII, change every frame) are drawn with cv2.putText on the last lines of the panel."""
        w = view.shape[1]
        stats_lines = list(stats_lines)
        key = (w, self._view_cache_key(text_or_view), tuple(small), len(stats_lines))
        if key != self._key:
            self._panel, self._key = self._build(w, text_or_view, small, len(stats_lines)), key
        out = np.vstack([view, self._panel])
        draw_panel_overlays(out, view.shape[0], hold_progress, stats_lines, self.small_h)
        return out

    def panel_builder(self, text_or_view: Any, small: Sequence[str]) -> PanelBuilder:
        """PanelBuilder of render_to_window for this text: builder(width, height, scale, n_stats) -> (panel of exactly
        height x width, stats line step). The panel is cached by (width, height, scale, font px, text, small lines,
        n_stats): changing only the stats lines (drawn later by render_to_window) does not rebuild it."""
        small = list(small)
        view_key = self._view_cache_key(text_or_view)

        def build(width: int, height: int, scale: float, n_stats: int) -> Tuple[np.ndarray, int]:
            key = (width, height, scale, self.font_px(scale), view_key, tuple(small), n_stats)
            if key != self._scaled_key:
                self._scaled_panel = self._build(width, text_or_view, small, n_stats, scale, height)
                self._scaled_key = key
            return self._scaled_panel, self.line_steps(scale)[1]

        return build


def hud_stats_lines(times: StageTimes, process_starts: Sequence[float], rolling: int, dropped: int) -> List[str]:
    """Live stats shown on the HUD: rolling p50 (last `rolling` values, ms) of every frame stage and of both sign
    stages, frames processed per second over the last `rolling` frames, frames dropped so far. 'n/a' = nothing
    measured yet."""
    def p50(stage):
        v = times.rolling_p50(stage)
        return "n/a" if v is None else f"{v:.1f}"
    labels = dict(HUD_STAGE_LABELS)
    frame = " | ".join(f"{labels[s]} {p50(s)}" for s in FRAME_STAGES)
    sign = " | ".join(f"{labels[s]} {p50(s)}" for s in SIGN_STAGES)
    rate = rate_from_timestamps(list(process_starts)[-int(rolling):])
    return ["p50 (ms) " + frame, f"p50 (ms) {sign} | processed/s {rate:.1f} | dropped {int(dropped)}"]


# ---------------------------------------------------------------------------------------------------------- report
def resolve_path(path: str) -> str:
    """A relative path that does not exist from the current directory is taken from the repository root (so the
    app also starts from another directory)."""
    if os.path.isabs(path) or os.path.exists(path):
        return path
    return os.path.join(ROOT, path)


def report_path(path: str) -> str:
    """Path written to the JSON: relative to the repository root when inside it, '/' separators."""
    full = os.path.abspath(path)
    try:
        rel = os.path.relpath(full, ROOT)
    except ValueError:  # another drive
        return full.replace("\\", "/")
    return (full if rel.startswith("..") else rel).replace("\\", "/")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def generated_by(argv: List[str]) -> Dict[str, Any]:
    import mediapipe as mp
    import torch
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    return {"command": " ".join(["python", "level1_demo.py", *argv]),
            "git_commit": _git("rev-parse", "HEAD"),
            "code_dirty": None if status is None else bool(status),
            "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "python": platform.python_version(), "mediapipe": mp.__version__, "cv2": cv2.__version__,
            "torch": torch.__version__, "numpy": np.__version__,
            "cpu": platform.processor(), "os": platform.platform()}


# ------------------------------------------------------------------------------------------------- open palm = Space
def _finite_positive(name: str, value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}") from None
    if not np.isfinite(v) or not v > 0:
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")
    return v


class SpaceGestureTracker:
    """Open palm gesture -> Space (plan 15 lần sửa 9 §2 S2). update(ts_ms, is_space, has_hand) once per processed frame
    (is_space = is_open_palm_space of the frame's hand) returns True exactly once per gesture:
      - armed and open palm: the hold runs from the first open-palm frame; ts - start >= hold_ms -> True, disarmed;
      - disarmed: no space however long the open palm is held (no auto-repeat);
      - another hand shape: the hold stops; held longer than rearm_ms -> armed again; a frame without hand -> armed
        again at once (withdraw the hand, or change the hand shape, before the next space).
    held_ms = how long the open palm has been held while armed (0 otherwise; HUD). Pure computation, no clock."""

    def __init__(self, hold_ms: float = GESTURE_SPACE_HOLD, rearm_ms: float = GESTURE_SPACE_REARM):
        self.hold_ms = _finite_positive("hold_ms", hold_ms)
        self.rearm_ms = _finite_positive("rearm_ms", rearm_ms)
        self.n_emits = 0
        self.reset()

    def reset(self) -> None:
        """Armed, no hold, no other shape running (tracking paused). The emission counter is kept."""
        self.armed = True
        self.run_since: Optional[float] = None    # first frame of the open palm being held (armed)
        self.other_since: Optional[float] = None  # first frame of the other hand shape being held
        self.last_ts: Optional[float] = None

    @property
    def held_ms(self) -> float:
        if self.armed and self.run_since is not None and self.last_ts is not None:
            return self.last_ts - self.run_since
        return 0.0

    def update(self, ts_ms: float, is_space: bool, has_hand: bool = True) -> bool:
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        self.last_ts = ts
        if is_space and has_hand:
            self.other_since = None
            if not self.armed:
                return False
            if self.run_since is None:
                self.run_since = ts
            if ts - self.run_since >= self.hold_ms:
                self.armed, self.run_since = False, None
                self.n_emits += 1
                return True
            return False
        self.run_since = None
        if not has_hand:
            self.armed, self.other_since = True, None
            return False
        if self.other_since is None:
            self.other_since = ts
        if ts - self.other_since > self.rearm_ms:
            self.armed = True
        return False


# ---------------------------------------------------------------------------------------------------------- app
class Level1App:
    """One run of the app. `classifier` / `session_factory` can be given (tests); keep_segments keeps the emitted
    SignSegments in memory (tests only; never written). The default session factory builds HandLandmarkSession with
    --min-detection-conf; a factory given by a test is used as it is."""

    def __init__(self, args: argparse.Namespace, argv: Optional[List[str]] = None, classifier=None,
                 session_factory=HandLandmarkSession, keep_segments: bool = False):
        self.args = args
        self.argv = list(argv) if argv is not None else []
        self.config_path = resolve_path(args.config)
        self.checkpoint_path = resolve_path(args.checkpoint)
        if not os.path.isfile(self.config_path):
            raise SourceError(f"config not found: {args.config}")
        self.cfg = load_level1_config(self.config_path)
        self.values = self.cfg["values"]
        # command-line values that replace config values for this run (plan 15 lần sửa 7 T2), written to the JSON as
        # config.overrides; the config file is not changed
        self.config_overrides: Dict[str, Any] = {}
        if getattr(args, "cls_window_ms", None) is not None:
            if self.values["rearm_mode"] != "classifier":
                raise SourceError("--cls-window-ms needs a config with rearm_mode 'classifier' "
                                  "(e.g. --config configs/level1_demo_classifier.json)")
            self.config_overrides["cls_window_ms"] = float(args.cls_window_ms)
        if self.config_overrides:
            self.values = {**self.values, **self.config_overrides}
        if not os.path.isfile(self.checkpoint_path):
            raise SourceError(f"checkpoint not found: {args.checkpoint}")
        self.checkpoint_sha256 = sha256_file(self.checkpoint_path)
        self.classifier = classifier or Level1Classifier.from_checkpoint(self.checkpoint_path)
        # plan 15 lần sửa 8 M3: hand detection of this run (--min-detection-conf, --auto-enhance); with the defaults
        # every MediaPipe graph has exactly LEVEL1_HANDS_KWARGS and every frame reaches MediaPipe unchanged
        self.min_detection_conf = float(getattr(args, "min_detection_conf", DEFAULT_MIN_DETECTION_CONF))
        self.auto_enhance = bool(getattr(args, "auto_enhance", False))
        self.detection_custom = self.auto_enhance or self.min_detection_conf != DEFAULT_MIN_DETECTION_CONF
        self.frames_enhanced = 0
        if session_factory is HandLandmarkSession:
            session_factory = functools.partial(HandLandmarkSession, min_detection_confidence=self.min_detection_conf)
        self.session_factory = session_factory
        self.keep_segments = keep_segments
        self.kept_segments: List[SignSegment] = []
        self.webcam = args.source.isdigit()
        if self.webcam and args.headless:
            raise SourceError("--headless needs a video file as --source (the webcam has no end)")
        if self.webcam:
            self.mode = "gui"
        elif args.pace == "realtime":
            self.mode = "paced"
        else:
            self.mode = "headless" if args.headless else "gui"
        self.display = not args.headless
        self.latest_only = self.webcam or self.mode == "paced"
        self.sync_classify = self.mode == "headless"
        self.hud = None
        if self.display:
            self.hud = Hud(find_font(args.font, self.values["font_paths"]), self.values["hud_font_size"])
        self.segmenter = Level1SignSegmenter(self.values, self.classifier.min_detected_frames)
        self.unikey_mode = bool(getattr(args, "unikey_mode", True))
        self.speller = Level1Speller(self.values["accept_confidence"], unikey_mode=self.unikey_mode)
        self.rearm_mode = self.values["rearm_mode"]
        self.classifier_mode = self.rearm_mode == "classifier"
        # plan 15 lần sửa 10 P2: --smooth-landmarks -> the landmarks of every frame go through the smoother before the
        # segmenter, the window, the gesture and the drawing
        self.smooth_landmarks = bool(getattr(args, "smooth_landmarks", False))
        self.landmark_smoother = LandmarkSmoother()
        stages = (FRAME_STAGES + SIGN_STAGES + (WINDOW_STAGES if self.classifier_mode else ())
                  + (ENHANCE_STAGES if self.auto_enhance else ()) + (SMOOTH_STAGES if self.smooth_landmarks else ()))
        self.times = StageTimes(stages, self.values["hud_rolling_frames"])
        self.window: Optional[WindowBuffer] = None
        self.decoder: Optional[Level1LabelDecoder] = None
        if self.classifier_mode:
            self.window = WindowBuffer(self.values["cls_window_ms"], self.classifier.min_detected_frames)
            self.decoder = Level1LabelDecoder(self.values)
        # classifier mode: frames / word gaps / key n in timestamp order, applied once each frame's window result is in
        # [kind, ts, has_hand, resolved, result] (kind 'frame' | 'gap' | 'next'; a gap carries its seq in `result`)
        self.timeline: List[List[Any]] = []
        self.pending_jobs: Dict[int, List[Any]] = {}
        self.labels: List[Dict[str, Any]] = []
        self.window_counts = {"window_jobs": 0, "window_results": 0, "window_dropped": 0, "label_emits": 0,
                              "label_replace": 0, "segments_not_classified": 0}
        # --auto-space (plan 15 lần sửa 7 T3 --no-auto-space; off by default since lần sửa 12 S1)
        self.auto_space = bool(getattr(args, "auto_space", AUTO_SPACE_DEFAULT))
        # open palm = Space (plan 15 lần sửa 9 S2; --gesture-space, off by default since lần sửa 12 S1)
        self.gesture_space = bool(getattr(args, "gesture_space", GESTURE_SPACE_DEFAULT))
        self.space_tracker = SpaceGestureTracker(getattr(args, "space_hold_ms", GESTURE_SPACE_HOLD))
        self.gesture_flash_ts: Optional[float] = None  # stream time of the last gesture space (HUD flash)
        # flat hand flick = Backspace (--gesture-backspace, on by default)
        self.gesture_backspace = bool(getattr(args, "gesture_backspace", GESTURE_BACKSPACE_DEFAULT))
        self.backspace_tracker = BackspaceGestureTracker()
        self.gesture_backspace_flash_ts: Optional[float] = None  # stream time of the last gesture backspace (HUD flash)
        self.gesture_counts = {"palm_frames": 0, "spaces_added": 0, "flat_frames": 0, "backspaces_added": 0}
        self.foreshortened_run = 0  # consecutive hand frames with foreshortening_ratio < FORESHORTEN_RATIO_MIN (P3)
        # lần sửa 12 H1: 'auto' -> MediaPipe's label of each frame (no lock); 'lock' (or its aliases Right / Left) ->
        # the majority of MediaPipe's own labels on the first hand frames, for the rest of the run
        self.dominant_hand_requested = getattr(args, "dominant_hand", "auto")
        self.dominant_hand = ("lock" if self.dominant_hand_requested in DOMINANT_HAND_ALIASES
                              else self.dominant_hand_requested)
        self.hand_lock: Optional[HandednessLock] = HandednessLock() if self.dominant_hand == "lock" else None
        if self.dominant_hand_requested in DOMINANT_HAND_ALIASES:
            print(f"level1_demo: --dominant-hand {self.dominant_hand_requested} now means --dominant-hand lock (the "
                  "label is taken from MediaPipe on this camera, never assumed)", file=sys.stderr)
        self.trace_windows = bool(getattr(args, "trace_windows", False))
        self.window_trace: List[Dict[str, Any]] = []
        self.window_trace_n = 0
        self.last_window: Optional[Dict[str, Any]] = None  # newest window entry (HUD decoder line, lần sửa 6 W2)
        self.segments: Dict[int, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.t_emit_perf: Dict[int, float] = {}
        self.pending_display: List[int] = []
        self.process_starts: List[float] = []
        self.read_times: List[float] = []
        self.counts = {"frames_read": 0, "frames_processed": 0, "frames_dropped": 0, "segments": 0, "word_gaps": 0}
        self.frame_size = None
        self.paused = False
        self.quit = False
        self.last_ts: Optional[float] = None
        self.last_result: Optional[Dict[str, Any]] = None
        self.worker: Optional[ClassifyWorker] = None
        self.window_worker: Optional[LatestWindowWorker] = None
        self.slot: Optional[LatestFrameSlot] = None
        self.warmup = {}
        self.window_sized = False  # the resizable window was set to the natural size (first image shown)
        self.fullscreen = bool(getattr(args, "fullscreen", False))

    # -------------------------------------------------------------- events
    def _log(self, kind: str, **fields) -> None:
        self.events.append({"event": kind, **fields})

    def _apply_result(self, seg: SignSegment, result: Dict[str, Any], classify_ms: float) -> None:
        self.times.add("classify", classify_ms)
        decision = self.speller.on_result(seg.seq, result, t_ms=seg.t_emit_ms)
        info = self.segments[seg.seq]
        info.update({"status": result["status"], "prediction": result.get("prediction"),
                     "confidence": result.get("confidence")})
        for d in decision:
            if d["seq"] in self.segments:
                self.segments[d["seq"]]["accepted"] = d["accepted"]
        self.last_result = {"seq": seg.seq, **result, "accepted": info.get("accepted")}
        if self.display:
            self.pending_display.append(seg.seq)
        else:
            self.times.add("emit_to_token", (time.perf_counter() - self.t_emit_perf[seg.seq]) * 1000.0)

    def _on_events(self, events) -> None:
        for ev in events:
            if isinstance(ev, SignSegment):
                self.counts["segments"] += 1
                self.t_emit_perf[ev.seq] = time.perf_counter()
                self.segments[ev.seq] = {"seq": ev.seq, "t_start_ms": ev.t_start_ms, "t_end_ms": ev.t_end_ms,
                                         "t_emit_ms": ev.t_emit_ms, "close_reason": ev.close_reason,
                                         "frames": ev.n_frames, "detected_frames": ev.n_detected,
                                         "status": None, "prediction": None, "confidence": None, "accepted": None}
                self._log("segment", seq=ev.seq, t_ms=ev.t_emit_ms, close_reason=ev.close_reason)
                if self.keep_segments:
                    self.kept_segments.append(ev)
                if self.classifier_mode:  # tokens come from the label decoder; the segment is only counted
                    self.window_counts["segments_not_classified"] += 1
                    continue
                self.speller.segment_emitted(ev.seq)
                if self.sync_classify:
                    t0 = time.perf_counter()
                    result = self.classifier.classify(ev, self.values["top_k"])
                    self._apply_result(ev, result, (time.perf_counter() - t0) * 1000.0)
                else:
                    self.worker.submit(ev)
            elif isinstance(ev, WordGap):
                self.counts["word_gaps"] += 1
                if not self.auto_space:  # --no-auto-space: the gap is detected and logged, no space token
                    self._log("word_gap", seq=ev.seq, t_ms=ev.t_ms, auto_space=False)
                    continue
                self._log("word_gap", seq=ev.seq, t_ms=ev.t_ms)
                if self.classifier_mode:  # after the labels of the frames before it
                    self.timeline.append(["gap", ev.t_ms, False, True, ev.seq])
                    self._drain_timeline()
                else:
                    self.speller.word_gap(ev.seq, t_ms=ev.t_ms)

    def _drain_worker(self, results) -> None:
        for seg, result, classify_ms, error in results:
            if error is not None:
                raise error
            self._apply_result(seg, result, classify_ms)

    # -------------------------------------------------------------- classifier re-arm (plan 15 lần sửa 4 §3.4)
    def _window_frame(self, ts_ms: float, landmarks, handedness: str, w: int, h: int, moving: bool = False) -> None:
        """Window of this frame -> classification (headless: now; otherwise newest-job worker) -> timeline. moving =
        segmenter state 'moving' of this frame, read by the decoder only with cls_motion_gate (lần sửa 12 G1)."""
        self.window.push(ts_ms, landmarks, handedness, w, h)
        entry = ["frame", ts_ms, landmarks is not None, True, None, bool(moving)]
        self.timeline.append(entry)
        if landmarks is not None:
            seg = self.window.segment(ts_ms)
            if seg is not None:
                self.window_counts["window_jobs"] += 1
                if self.sync_classify:
                    t0 = time.perf_counter()
                    entry[4] = self.classifier.classify(seg, self.values["top_k"])
                    self.times.add("window_classify", (time.perf_counter() - t0) * 1000.0)
                    self.window_counts["window_results"] += 1
                else:
                    job_id = self.window_counts["window_jobs"]
                    entry[3] = False
                    self.pending_jobs[job_id] = entry
                    dropped = self.window_worker.submit(job_id, ts_ms, seg)
                    if dropped is not None:  # its frame has no result: None for the decoder
                        self.pending_jobs.pop(dropped)[3] = True
                        self.window_counts["window_dropped"] += 1
        self._drain_timeline()

    def _window_results(self, results) -> None:
        for job_id, _ts, result, classify_ms, error in results:
            if error is not None:
                raise error
            self.times.add("window_classify", classify_ms)
            self.window_counts["window_results"] += 1
            entry = self.pending_jobs.pop(job_id)
            entry[3], entry[4] = True, result
        self._drain_timeline()

    def _drain_timeline(self) -> None:
        """Applies the timeline from its start while its head is resolved (timestamp order is kept)."""
        while self.timeline and self.timeline[0][3]:
            entry = self.timeline.pop(0)
            kind, ts_ms, has_hand, _resolved, payload = entry[:5]
            moving = entry[5] if len(entry) > 5 else False  # frame entries only (lần sửa 12 G1)
            if kind == "gap":
                self.speller.word_gap(payload, t_ms=ts_ms)
            elif kind == "space":
                self._apply_gesture_space(ts_ms)
            elif kind == "backspace":
                self._apply_gesture_backspace(ts_ms)
            elif kind == "next":
                self.decoder.force_next(ts_ms)
            elif kind == "reset":
                self.decoder.reset()
            else:
                emit = self.decoder.push(ts_ms, has_hand, payload, moving=moving)
                if payload is not None:
                    self.last_window = self._window_entry(ts_ms, payload, emit)
                    if self.trace_windows:
                        self._trace_window(self.last_window)
                if emit is not None:
                    self._apply_label(emit)

    def _window_entry(self, ts_ms: float, result: Dict[str, Any], emit) -> Dict[str, Any]:
        """Window result + decoder state right after the decoder applied it (plan 15 lần sửa 6 §3.W1): top1/conf and
        top2/conf2 of the window (whatever cls_conf), run_label / run_ms = the label run after this window (run_ms =
        ts - start of the run; the run restarts at a window below cls_conf or with another label), last = last emitted
        label after this window, emitted = seq of the label emitted at this window (None otherwise). Reads the decoder,
        never changes it."""
        cands = result.get("candidates") or []
        second = cands[1] if len(cands) > 1 else {}
        run_since = self.decoder._run_since
        return {"ts_ms": float(ts_ms), "status": result.get("status"), "top1": result.get("prediction"),
                "conf": result.get("confidence"), "top2": second.get("class"), "conf2": second.get("confidence"),
                "run_label": self.decoder._run_label,
                "run_ms": float(ts_ms) - run_since if run_since is not None else 0.0,
                "last": self.decoder.last_label, "emitted": emit.seq if emit is not None else None}

    def _trace_window(self, entry: Dict[str, Any]) -> None:
        self.window_trace_n += 1
        if len(self.window_trace) < TRACE_MAX_ENTRIES:
            self.window_trace.append(entry)

    def _apply_label(self, emit) -> None:
        d = self.speller.on_label(emit.seq, emit)
        self.window_counts["label_emits"] += 1
        if d["action"] == "replace":
            self.window_counts["label_replace"] += 1
        self.labels.append({"seq": emit.seq, "ts_ms": emit.ts_ms, "run_since_ms": emit.run_since_ms,
                            "prediction": emit.prediction, "confidence": emit.confidence, "action": emit.action,
                            "accepted": d["accepted"], "applied": d["action"]})
        self._log("label", seq=emit.seq, t_ms=emit.ts_ms, prediction=emit.prediction, action=emit.action)
        self.last_result = {"seq": emit.seq, **emit.result, "accepted": d["accepted"]}

    def _key(self, code: int) -> None:
        if code < 0:
            return
        k = code & 0xFF
        if k in KEY_QUIT:
            self.quit = True
        elif k == KEY_PAUSE:
            self.paused = not self.paused
            if self.paused:
                self.segmenter.reset()
                self.space_tracker.reset()
                self.backspace_tracker.reset()
                if self.classifier_mode:
                    self.window.reset()
                    self.timeline.append(["reset", self.last_ts, False, True, None])
                    self._drain_timeline()
            self._log("pause" if self.paused else "resume", t_ms=self.last_ts)
        elif k == KEY_FULLSCREEN:
            self.fullscreen = not self.fullscreen
            prop = cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL
            try:
                cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, prop)
            except (cv2.error, AttributeError):
                pass
            if self.fullscreen:
                self.window_sized = False
            self._log("fullscreen", on=self.fullscreen)
        elif k in KEY_ACTIONS and KEY_ACTIONS[k] == KEY_NEXT:
            self._next_key()
        elif k in KEY_ACTIONS:
            self.speller.key(KEY_ACTIONS[k], t_ms=self.last_ts)

    # -------------------------------------------------------------- open palm = Space (plan 15 lần sửa 9 §2 S2)
    def _gesture_step(self, ts_ms: float, is_space: bool, has_hand: bool) -> None:
        """One frame of the gesture: tracker update; a space of the tracker goes to the speller as the Space key, in
        rearm_mode classifier through the timeline (after the labels of the frames before it, like a word gap)."""
        self.gesture_counts["palm_frames"] += int(bool(is_space and has_hand))
        if not self.space_tracker.update(ts_ms, is_space, has_hand=has_hand):
            return
        if self.classifier_mode:
            self.timeline.append(["space", ts_ms, False, True, None])
            self._drain_timeline()
        else:
            self._apply_gesture_space(ts_ms)

    def _apply_gesture_space(self, ts_ms: float) -> None:
        added = self.speller.key("space", t_ms=ts_ms)
        self.gesture_counts["spaces_added"] += int(added)
        self.gesture_flash_ts = ts_ms
        self._log("gesture_space", t_ms=ts_ms, added=added)

    # -------------------------------------------------------------- flat hand flick = Backspace
    def _gesture_backspace_step(self, ts_ms: float, landmarks, is_flat: bool, has_hand: bool) -> None:
        """One frame of the backspace gesture: tracker update; a flick of the flat hand goes to the speller
        as the Backspace key, in rearm_mode classifier through the timeline (after the labels before it)."""
        self.gesture_counts["flat_frames"] += int(bool(is_flat and has_hand))
        if not self.backspace_tracker.update(ts_ms, landmarks, is_flat, has_hand=has_hand):
            return
        if self.classifier_mode:
            self.timeline.append(["backspace", ts_ms, False, True, None])
            self._drain_timeline()
        else:
            self._apply_gesture_backspace(ts_ms)

    def _apply_gesture_backspace(self, ts_ms: float) -> None:
        changed = self.speller.key("backspace", t_ms=ts_ms)
        if self.classifier_mode and self.decoder is not None:
            self.decoder.reset()
        self.gesture_counts["backspaces_added"] += int(changed)
        self.gesture_backspace_flash_ts = ts_ms
        self._log("gesture_backspace", t_ms=ts_ms, changed=changed)

    def _gesture_line(self) -> Optional[str]:
        """HUD: backspace flash / space flash / open palm progress / flat hand ready hint; else None."""
        if (self.gesture_backspace_flash_ts is not None and self.last_ts is not None
                and self.last_ts - self.gesture_backspace_flash_ts < GESTURE_BACKSPACE_FLASH):
            return "[Ký hiệu: Xóa (Backspace)]"
        if (self.gesture_flash_ts is not None and self.space_tracker.last_ts is not None
                and self.space_tracker.last_ts - self.gesture_flash_ts < GESTURE_SPACE_FLASH):
            return "[Ký hiệu: Dấu cách (Space)]"
        tr = self.space_tracker
        if tr.armed and tr.run_since is not None:
            return f"[Cử chỉ: Dấu cách {tr.held_ms:.0f}/{tr.hold_ms:.0f}]"
        if self.gesture_backspace and self.backspace_tracker.is_ready(self.last_ts):
            return "[Cử chỉ: Phẩy tay để xóa]"
        return None

    # -------------------------------------------------------------- angle hint (plan 15 lần sửa 10 §2 P3)
    def _angle_step(self, landmarks, w: int, h: int) -> None:
        """One frame: a hand whose index finger points at the camera (foreshortening_ratio < FORESHORTEN_RATIO_MIN)
        lengthens the run; any other frame (ratio at or above it, or no hand) ends it. HUD only."""
        if landmarks is not None and foreshortening_ratio(aspect_points(landmarks, w, h)) < FORESHORTEN_RATIO_MIN:
            self.foreshortened_run += 1
        else:
            self.foreshortened_run = 0

    def _hand_line(self) -> str:
        """HUD line of --dominant-hand lock: the locked label, or the votes counted so far."""
        lock = self.hand_lock
        if lock.locked:
            return HAND_LOCK_HUD.format(label=lock.label)
        return HAND_LOCKING_HUD.format(n=lock.n_votes, total=lock.lock_frames)

    def _next_key(self) -> None:
        """Key n "chữ kế" (plan 15 lần sửa 4 §3.1): re-arm the segmenter at the last frame so the sign held now is
        emitted again; no token is created here (tokens still come only from the model or the token keys)."""
        if self.last_ts is not None:
            if self.classifier_mode:  # in timestamp order, after the frames already seen
                self.timeline.append(["next", self.last_ts, False, True, None])
                self._drain_timeline()
            else:
                self.segmenter.force_rearm(self.last_ts)
        self._log("key", key=KEY_NEXT, source="key", t_ms=self.last_ts)

    # -------------------------------------------------------------- one frame
    def _decoder_line(self) -> str:
        """rearm_mode classifier (plan 15 lần sửa 6 §3.W2): newest window (top-1 and its confidence, whatever cls_conf),
        how long its label has held against cls_stable_ms (0 when the window is below cls_conf), last emitted label.
        While the run is a tone mark the stable time of tone marks is shown, followed by "(tone)" (lần sửa 7 T4)."""
        w = self.last_window
        top1 = w["top1"] if w is not None and w["top1"] is not None else "—"
        conf = f"{w['conf']:.2f}" if w is not None and w["conf"] is not None else "—"
        held = w["run_ms"] if w is not None and w["run_label"] is not None else 0.0
        last = self.decoder.last_label if self.decoder.last_label is not None else "—"
        run = w["run_label"] if w is not None else None
        tone = self.decoder.is_tone(run)
        stable = f"{self.decoder.thresholds(run)[1]:.0f} (tone)" if tone else f"{self.values['cls_stable_ms']:.0f}"
        line = f"[classifier] cửa sổ: {top1} {conf} | giữ {held:.0f}/{stable} | cuối: {last}"
        if self.decoder.motion_gate and not self.paused and self.segmenter.state == "moving":  # lần sửa 12 G1
            line += " | chờ tay yên"
        return line + " | tạm dừng (p)" if self.paused else line

    def _hud_lines(self):
        tb_view = self.speller.view
        st = self.segmenter.status()
        state = "tạm dừng (p)" if self.paused else STATE_LABELS[st["state"]]
        r = self.last_result
        if r is None:
            last = "Ký hiệu: —"
        elif r["status"] != "ok":
            last = f"Ký hiệu #{r['seq']}: không đủ khung có tay ({r['status']})"
        else:
            mark = "nhận" if r.get("accepted") else "chưa nhận (a: nhận)"
            last = f"Ký hiệu #{r['seq']}: {r['prediction']}  {r['confidence']:.2f}  {mark}"
        # classifier: the decoder line replaces the segmenter state (the segmenter does not decide the letters there)
        small = [last, self._decoder_line() if self.classifier_mode else "Trạng thái: " + state]
        if self.detection_custom:  # lần sửa 8: only when MediaPipe or its input differ from the default
            small.append(f"[MP: conf={self.min_detection_conf:.2f} | CLAHE: {'on' if self.auto_enhance else 'off'}]")
        if self.hand_lock is not None:  # lần sửa 12 H1: only with --dominant-hand lock (or Right / Left)
            small.append(self._hand_line())
        gesture = self._gesture_line() if self.gesture_space else None
        if gesture is not None:  # lần sửa 9: only while the open palm is held / right after its space
            small.append(gesture)
        if self.foreshortened_run > FORESHORTEN_FRAMES:  # lần sửa 10 P3: index pointing at the camera
            small.append(ANGLE_HINT_LINE)
        tc_list = tb_view.get("tone_changes", [])
        if tc_list:
            last_tc = tc_list[-1]
            f_tone = last_tc["from"].replace("dấu ", "")
            t_tone = last_tc["to"].replace("dấu ", "")
            small.append(f"đổi dấu: {f_tone} → {t_tone}")
        for w in tb_view.get("warnings", []):
            small.append("Cảnh báo: " + w["code"])
        small.append("1-5 dấu | Backspace xóa | Space cách | a nhận | r lặp chữ | n chữ kế | c xóa hết | p dừng | q thoát")
        dropped = self.slot.dropped if self.slot is not None else 0
        stats = hud_stats_lines(self.times, self.process_starts, self.values["hud_rolling_frames"], dropped)
        progress = 0.0 if self.classifier_mode else st["hold_progress"]  # no hold bar of the segmenter in classifier
        return tb_view, small, progress, stats

    def _process(self, session, frame: np.ndarray, t_cap: float, ts_ms: float) -> None:
        t0 = time.perf_counter()
        self.process_starts.append(t0)
        self.times.add("capture_age", (t0 - t_cap) * 1000.0)
        h, w = frame.shape[:2]
        if self.frame_size is None:
            self.frame_size = {"width": int(w), "height": int(h)}
        frame_mp, t_mp = frame, t0  # what MediaPipe gets; `frame` (the camera frame) is the one drawn and shown
        if self.auto_enhance:
            frame_mp, enhanced = enhance_low_light(frame)
            self.frames_enhanced += int(enhanced)
            t_mp = time.perf_counter()
            self.times.add("low_light_enhance", (t_mp - t0) * 1000.0)
        landmarks, handedness, _score = session.process(frame_mp)
        if self.hand_lock is not None and landmarks is not None:  # lần sửa 12 H1: --dominant-hand lock
            handedness = self.hand_lock.update(handedness)
        t1 = time.perf_counter()
        self.times.add("mediapipe", (t1 - t_mp) * 1000.0)
        if self.smooth_landmarks:  # lần sửa 10 P2: a frame without hand resets the smoother
            landmarks = self.landmark_smoother.filter(ts_ms, landmarks)
            t_smooth = time.perf_counter()
            self.times.add("landmark_smooth", (t_smooth - t1) * 1000.0)
            t1 = t_smooth
        gesture_sp = self.gesture_space and not self.paused
        gesture_bs = self.gesture_backspace and not self.paused
        # open palm check (lần sửa 9): timed inside the segmenter stage (no new stage: the report keeps its stages)
        is_space = gesture_sp and landmarks is not None and is_open_palm_space(aspect_points(landmarks, w, h))
        # flat hand check: 5 straight fingers held together (not spread like space)
        is_flat = gesture_bs and landmarks is not None and is_flat_hand_backspace(aspect_points(landmarks, w, h))
        # angle hint (lần sửa 10 P3): timed inside the segmenter stage like the open palm check
        self._angle_step(landmarks, w, h)
        if not self.paused:
            self._on_events(self.segmenter.push(ts_ms, landmarks, handedness, w, h))
        t2 = time.perf_counter()
        self.times.add("segmenter", (t2 - t1) * 1000.0)
        if self.classifier_mode and not self.paused:  # a word gap of this frame is a no-hand frame: order unaffected
            # open palm gesture frames are not letters: they reach the window as frames without hand
            self._window_frame(ts_ms, None if is_space else landmarks, handedness, w, h,
                               moving=self.segmenter.state == "moving")
            t2 = time.perf_counter()
        if gesture_sp:
            self._gesture_step(ts_ms, is_space, landmarks is not None)
        if gesture_bs:
            self._gesture_backspace_step(ts_ms, aspect_points(landmarks, w, h) if landmarks is not None else None,
                                        is_flat, landmarks is not None)
        self.last_ts = ts_ms
        self.counts["frames_processed"] += 1
        if self.worker is not None:
            self._drain_worker(self.worker.poll())
        if self.window_worker is not None:
            self._window_results(self.window_worker.poll())
        if not self.display:
            self.times.add("frame_total", (time.perf_counter() - t_cap) * 1000.0)
            return
        draw_landmarks(frame, landmarks)
        t3 = time.perf_counter()
        self.times.add("draw_landmarks", (t3 - t2) * 1000.0)
        view = display_view(frame, self.args.display_mirror)
        tb_view, small, progress, stats = self._hud_lines()
        view = self._window_image(view, tb_view, small, progress, stats)
        t4 = time.perf_counter()
        self.times.add("hud", (t4 - t3) * 1000.0)
        cv2.imshow(WINDOW_NAME, view)
        code = cv2.waitKey(1)
        t5 = time.perf_counter()
        self.times.add("display", (t5 - t4) * 1000.0)
        self.times.add("frame_total", (t5 - t_cap) * 1000.0)
        for seq in self.pending_display:
            self.times.add("emit_to_token", (t5 - self.t_emit_perf[seq]) * 1000.0)
        self.pending_display = []
        self._key(code)
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            self.quit = True

    def _window_image(self, view: np.ndarray, text_or_view: Any, small: List[str], hold_progress: float,
                      stats_lines: List[str]) -> np.ndarray:
        """Image shown in the resizable window (plan 15 lần sửa 13 §2.2, 13b U2b), from the DISPLAY image only
        (landmarks drawn, mirrored; never the frame given to MediaPipe). The first image shown resizes the window once
        to the natural size (camera image + panel). The window image rect is read every frame: no usable size
        (cv2.error, no getWindowImageRect, invalid rect) or the natural size => Hud.compose (the image of the old
        fixed window); any other size => the content scaled into it (render_to_window, same text and overlays)."""
        h, w = view.shape[:2]
        panel_h = self.hud.panel_height(text_or_view, small, len(stats_lines))
        if not self.fullscreen and not self.window_sized:
            self.window_sized = True
            try:
                cv2.resizeWindow(WINDOW_NAME, w, h + panel_h)
            except (cv2.error, AttributeError):
                pass
        try:
            rect = cv2.getWindowImageRect(WINDOW_NAME)
        except (cv2.error, AttributeError):
            rect = None
        layout = fit_layout(w, h, panel_h, rect)
        if layout == fit_layout(w, h, panel_h):
            return self.hud.compose(view, text_or_view, small, hold_progress, stats_lines)
        return render_to_window(view, self.hud.panel_builder(text_or_view, small), stats_lines, hold_progress, layout)

    # -------------------------------------------------------------- run
    def _open_reader(self):
        if self.webcam:
            return CameraReader(int(self.args.source), self.values)
        return VideoFileReader(self.args.source)

    def _warmup(self, reader) -> None:
        """First MediaPipe graph run and first model run measured apart (a separate session: the session used for
        the stream is not touched)."""
        if reader.props is not None:
            w, h = int(reader.props["width"]), int(reader.props["height"])
        else:
            w, h = int(reader.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(reader.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        blank = np.zeros((max(h, 1), max(w, 1), 3), dtype=np.uint8)
        t0 = time.perf_counter()
        s = self.session_factory()
        try:
            s.process(blank)
        finally:
            s.close()
        mp_first = (time.perf_counter() - t0) * 1000.0
        self.warmup = {"mediapipe_first_ms": mp_first, "classify_first_ms": self.classifier.warmup()}

    def run(self) -> Dict[str, Any]:
        reader = self._open_reader()
        session = None
        capture = None
        try:
            self._warmup(reader)
            session = self.session_factory()
            if not self.sync_classify:
                self.worker = ClassifyWorker(self.classifier, self.values["top_k"])
                self.worker.start()
                if self.classifier_mode:
                    self.window_worker = LatestWindowWorker(self.classifier, self.values["top_k"])
                    self.window_worker.start()
            if self.display:
                cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)  # resizable: content scaled to the window (U2b)
                if self.fullscreen:
                    try:
                        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    except (cv2.error, AttributeError):
                        pass
            origin = time.perf_counter()
            if self.latest_only:
                slot = self.slot = LatestFrameSlot()
                capture = CaptureThread(reader, slot, paced=self.mode == "paced", origin=origin)
                capture.start()
                while not self.quit:
                    item = slot.get(timeout=0.05)
                    if item is None:
                        if slot.closed:
                            break
                        if self.display:
                            self._key(cv2.waitKey(1))
                        continue
                    _seq, frame, t_cap, ts_ms = item
                    self._process(session, frame, t_cap, ts_ms)
                capture.stop()
                capture.join()
                if capture.error is not None:
                    raise capture.error
                self.counts["frames_read"] = capture.frames_read
                if self.webcam and capture.frames_read == 0:
                    raise SourceError(f"webcam {self.args.source} delivered no frame (try another index or "
                                      "camera_api in the config)")
                self.counts["frames_dropped"] = slot.dropped
                self.read_times = capture.read_times
            else:
                i = 0
                while not self.quit:
                    frame = reader.read()
                    if frame is None:
                        break
                    t_cap = time.perf_counter()
                    self.read_times.append(t_cap)
                    self._process(session, frame, t_cap, i * 1000.0 / reader.fps)
                    i += 1
                self.counts["frames_read"] = i
            if self.window_worker is not None:  # the window results come before the end of the stream
                self._window_results(self.window_worker.finish())
                self.window_worker = None
            if self.last_ts is not None and not self.paused:
                self._on_events(self.segmenter.flush(self.last_ts))
            if self.worker is not None:
                self._drain_worker(self.worker.finish())
                self.worker = None
        finally:
            if self.window_worker is not None:
                self.window_worker.finish()
            if self.worker is not None:
                self.worker.finish()
            if capture is not None and capture.is_alive():
                capture.stop()
                capture.join()
            if session is not None:
                session.close()
            reader.release()
            if self.display:
                cv2.destroyAllWindows()
        return self.report(reader)

    def report(self, reader) -> Dict[str, Any]:
        comp = self.speller.composed()
        expected = None
        if self.args.expected is not None:
            exp = unicodedata.normalize("NFC", self.args.expected)
            expected = {"text": exp, "matches_text": exp == comp["text"]}
        source = {"kind": reader.kind, "id": self.args.source.replace("\\", "/"), "mode": self.mode}
        if reader.fps is not None:
            source["fps_file"] = reader.fps
        counts = dict(self.counts)
        counts["dropped"] = counts["frames_dropped"]  # same count under the name of plan 15 AC-L L2
        counts["processing_fps"] = rate_from_timestamps(self.process_starts)
        counts["capture_fps"] = rate_from_timestamps(self.read_times)
        counts["results_not_displayed"] = len(self.pending_display)
        if self.classifier_mode:
            counts.update(self.window_counts)
            if self.decoder.motion_gate:  # lần sửa 12 G1: only with cls_motion_gate (otherwise the counts of before)
                counts["frames_gated"] = self.decoder.n_gated
        report = {
            "generated_by": generated_by(self.argv),
            "rearm_mode": self.rearm_mode,
            "config": {"path": report_path(self.config_path), "sha256": self.cfg["sha256"],
                       "values": self.cfg["raw"]},
            "checkpoint": {"path": report_path(self.checkpoint_path), "sha256": self.checkpoint_sha256},
            "source": source,
            "frame_size": self.frame_size,
            "camera_props": reader.props,
            "warmup": self.warmup,
            "stages": self.times.stats(),
            "counts": counts,
            "tokens": list(self.speller.tokens),
            "text": comp["text"],
            "warnings": comp["warnings"],
            "segments": [self.segments[k] for k in sorted(self.segments)],
            "labels": list(self.labels),
            "events": self.events + self.speller.events,
            "expected": expected,
            "note": NOTE,
        }
        if not self.auto_space:  # only with --no-auto-space (same reason)
            report["auto_space"] = False
        if self.config_overrides:  # only with --cls-window-ms: otherwise the report keeps its keys (AC-6b)
            report["config"]["overrides"] = dict(self.config_overrides)
        if self.detection_custom:  # only with --min-detection-conf other than the default or --auto-enhance
            detection = {"min_detection_confidence": self.min_detection_conf, "auto_enhance": self.auto_enhance}
            if self.auto_enhance:
                detection.update({"frames_enhanced": self.frames_enhanced, "low_light_threshold": LOW_LIGHT_THRESHOLD,
                                  "clahe_clip_limit": CLAHE_CLIP_LIMIT, "clahe_tile_grid": list(CLAHE_TILE_GRID)})
            report["hand_detection"] = detection
        if self.trace_windows:  # without the flag the report keeps exactly its keys of before (lần sửa 6 AC-6b)
            report["window_trace"] = {"max_entries": TRACE_MAX_ENTRIES, "n_windows": self.window_trace_n,
                                      "truncated": self.window_trace_n > len(self.window_trace),
                                      "fields": list(TRACE_KEYS), "entries": list(self.window_trace)}
        if self.hand_lock is not None:  # lần sửa 12 H1: only with --dominant-hand lock (or Right / Left)
            lock = self.hand_lock
            report["dominant_hand"] = {"mode": self.dominant_hand, "requested": self.dominant_hand_requested,
                                       "label": lock.label, "lock_frames": lock.lock_frames, "votes": dict(lock.votes)}
        if self.smooth_landmarks:  # lần sửa 10 P2: only with --smooth-landmarks
            sm = self.landmark_smoother
            report["landmark_smoothing"] = {"enabled": True, "alpha_static": sm.alpha_static,
                                            "alpha_dynamic": sm.alpha_dynamic, "speed_threshold": sm.speed_threshold,
                                            "frames_static": sm.n_static, "frames_dynamic": sm.n_dynamic}
        # lần sửa 9 S3: gesture on and (an open-palm frame seen or --space-hold-ms not the default); a run without open
        # palm at the default hold, or with --no-gesture-space, keeps exactly the keys of before
        tr = self.space_tracker
        if self.gesture_space and (self.gesture_counts["palm_frames"] > 0 or tr.hold_ms != GESTURE_SPACE_HOLD):
            report["gesture_space"] = {"enabled": True, "hold_ms": tr.hold_ms, "rearm_ms": tr.rearm_ms,
                                       "flash_ms": GESTURE_SPACE_FLASH,
                                       "palm_frames": self.gesture_counts["palm_frames"], "emits": tr.n_emits,
                                       "spaces_added": self.gesture_counts["spaces_added"]}
        if self.gesture_backspace and (self.gesture_counts["flat_frames"] > 0 or self.backspace_tracker.n_emits > 0):
            report["gesture_backspace"] = {"enabled": True,
                                           "cooldown_ms": self.backspace_tracker.cooldown_ms,
                                           "window_ms": self.backspace_tracker.window_ms,
                                           "flash_ms": GESTURE_BACKSPACE_FLASH,
                                           "flat_frames": self.gesture_counts["flat_frames"],
                                           "emits": self.backspace_tracker.n_emits,
                                           "backspaces_added": self.gesture_counts["backspaces_added"]}
        return report


def positive_ms(text: str) -> float:
    """argparse type of a duration in milliseconds: a finite number > 0."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not np.isfinite(value) or not value > 0:
        raise argparse.ArgumentTypeError(f"must be a finite number > 0, got {text!r}")
    return value


def detection_conf(text: str) -> float:
    """argparse type of --min-detection-conf: a finite number in (0, 1]."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not np.isfinite(value) or not 0.0 < value <= 1.0:
        raise argparse.ArgumentTypeError(f"must be a number in (0, 1], got {text!r}")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VSLT Level 1 (fingerspelling) realtime desktop app (plan 15).")
    p.add_argument("--source", default="0", help="webcam index (e.g. 0) or a video file (default %(default)s)")
    p.add_argument("--headless", action="store_true", help="no window (video sources only)")
    p.add_argument("--out-json", default=None, help="write the run report (JSON) to this path")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="parameter file (default %(default)s)")
    p.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT, help="Level 1 checkpoint (default %(default)s)")
    p.add_argument("--pace", choices=("all", "realtime"), default="all",
                   help="video: 'all' = every frame in order; 'realtime' = read at the file's frame rate and process "
                        "only the newest frame, like a webcam")
    p.add_argument("--expected", default=None, help="text the signer intends to spell (written to the JSON)")
    p.add_argument("--display-mirror", action=argparse.BooleanOptionalAction, default=False,
                   help="show the image mirrored (display only)")
    p.add_argument("--fullscreen", action="store_true", default=False,
                   help="open window in fullscreen mode")
    p.add_argument("--font", default=None, help="TrueType font with Vietnamese glyphs for the HUD")
    p.add_argument("--trace-windows", action="store_true",
                   help="rearm_mode classifier: write every window result and the decoder state (window_trace) to "
                        f"the JSON, at most {TRACE_MAX_ENTRIES} entries; no landmark or frame (default off)")
    p.add_argument("--cls-window-ms", type=positive_ms, default=None,
                   help="rearm_mode classifier: length of the sliding window in milliseconds for this run, in place "
                        "of cls_window_ms of the config (the file is not changed; written to the JSON as "
                        "config.overrides)")
    p.add_argument("--auto-space", action=argparse.BooleanOptionalAction, default=AUTO_SPACE_DEFAULT,
                   help="add a space when the hand is away for word_gap_ms; --no-auto-space (default): the word gap is "
                        "still detected and written to the JSON, spaces come from the Space key (and --gesture-space)")
    p.add_argument("--min-detection-conf", type=detection_conf, default=DEFAULT_MIN_DETECTION_CONF,
                   help="MediaPipe min_detection_confidence (default %(default)s; try 0.35 for edge-on hands); "
                        "written to the JSON as hand_detection when not the default")
    p.add_argument("--auto-enhance", action="store_true",
                   help="Enable adaptive CLAHE enhancement for low-light frames before hand detection (mean gray "
                        f"level below {LOW_LIGHT_THRESHOLD:g}; the window still shows the camera frame; default off)")
    p.add_argument("--gesture-space", action=argparse.BooleanOptionalAction, default=GESTURE_SPACE_DEFAULT,
                   help="open palm (5 fingers spread, thumb out) held --space-hold-ms adds one space; change the hand "
                        "shape or withdraw the hand before the next one (written to the JSON as gesture_space; "
                        "default off: a relaxed open hand is easily taken for the gesture)")
    p.add_argument("--space-hold-ms", type=positive_ms, default=GESTURE_SPACE_HOLD,
                   help="hold time in milliseconds of the open palm before its space (default %(default)s)")
    p.add_argument("--gesture-backspace", action=argparse.BooleanOptionalAction, default=GESTURE_BACKSPACE_DEFAULT,
                   help="flat hand (5 fingers straight together) flick/swipe triggers Backspace (default on)")
    p.add_argument("--dominant-hand", choices=list(DOMINANT_HAND_CHOICES), default="auto",
                   help="'lock': the handedness label of every hand frame is the majority of MediaPipe's own labels on "
                        f"the first {HandednessLock().lock_frames} hand frames (no Left/Right flip inside a window, no "
                        "assumption about camera mirroring; HUD [Tay: khóa ...], JSON dominant_hand); 'Right' / 'Left' "
                        "are aliases of 'lock'; 'auto' keeps MediaPipe's label of each frame (default: auto)")
    p.add_argument("--smooth-landmarks", action=argparse.BooleanOptionalAction, default=SMOOTH_LANDMARKS_DEFAULT,
                   help="Enable adaptive landmark smoothing to suppress depth jitter: the landmarks of every frame go "
                        "through LandmarkSmoother before the segmenter, the window, the gesture and the drawing "
                        "(written to the JSON as landmark_smoothing; default off: the app as before)")
    p.add_argument("--unikey-mode", action=argparse.BooleanOptionalAction, default=True,
                   help="Unikey-style text editing: in-place tone replacement, consecutive spaces allowed, "
                        "clean backspace (default on)")
    return p


DEFAULT_DEMO_ARGV = [
    "--source", "0",
    "--display-mirror",
    "--config", "configs/level1_demo_classifier_rev9.json",
    "--min-detection-conf", "0.55",
    "--dominant-hand", "lock",
    "--smooth-landmarks",
    "--unikey-mode",
    "--gesture-space",
    "--gesture-backspace",
]


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--headless" not in argv and "-h" not in argv and "--help" not in argv:
        argv = [*DEFAULT_DEMO_ARGV, *argv]
    args = build_parser().parse_args(argv)
    try:
        report = Level1App(args, argv=argv).run()
    except SourceError as e:
        print(f"level1_demo: {e}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if args.out_json:
        out_dir = os.path.dirname(os.path.abspath(args.out_json))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"text: {report['text']!r}  tokens: {report['tokens']}  segments: {len(report['segments'])}  "
          f"mode: {report['source']['mode']}")
    if args.out_json:
        print(f"report: {args.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
