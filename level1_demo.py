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
Keys (window): Backspace delete last token | Space add a space | a accept the last rejected candidate |
  r repeat the last letter | n next letter (re-arm: the letter held now is emitted again) | c clear |
  p pause / resume segmentation | q or Esc quit.

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
import datetime
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
from typing import Any, Dict, List, Optional, Sequence

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.inference.hand_live import HandLandmarkSession  # noqa: E402
from src.inference.level1_core import Level1Classifier, Level1Speller, load_level1_config  # noqa: E402
from src.inference.level1_segmenter import (Level1LabelDecoder, Level1SignSegmenter, SignSegment,  # noqa: E402
                                            WindowBuffer, WordGap)
from src.inference.level1_timing import (FRAME_STAGES, SIGN_STAGES, StageTimes,  # noqa: E402
                                         rate_from_timestamps)

DEFAULT_CONFIG = os.path.join("configs", "level1_realtime.json")      # relative to the repository root
DEFAULT_CHECKPOINT = os.path.join("checkpoints", "alphabet_best.pt")  # relative to the repository root
WINDOW_NAME = "VSLT Level 1"
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
KEY_NEXT = "next"  # app action (segmenter / decoder re-arm), not a Level1Speller key
KEY_QUIT = (ord("q"), 27)
KEY_PAUSE = ord("p")
STATE_LABELS = {"no_hand": "không thấy tay", "moving": "đang chuyển động", "holding": "đang giữ yên"}
# --trace-windows (plan 15 lần sửa 6 §3.W1): one entry per classified window, in the order the decoder applies them
TRACE_KEYS = ("ts_ms", "status", "top1", "conf", "top2", "conf2", "run_label", "run_ms", "last", "emitted")
TRACE_MAX_ENTRIES = 20000  # later windows are counted (n_windows) but not kept; truncated = true


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
    when its text changes (cache)."""

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

    def __init__(self, font_path: str, font_size: int):
        from PIL import ImageFont
        self.font = ImageFont.truetype(font_path, font_size)
        self.small = ImageFont.truetype(font_path, max(1, int(font_size * 2 / 3)))
        self.line_h = int(font_size * 1.35)
        self.small_h = int(font_size * 0.95)
        self._key = None
        self._panel = None

    def _fit_committed(self, committed: str, active: str, max_w: float) -> str:
        """Drops committed syllables from the start (prepending '…') until cursor fits in max_w."""
        if not committed:
            return ""
        if self.font.getlength(committed + active) <= max_w:
            return committed
        import re
        words = re.findall(r"\S+\s*", committed)
        if not words:
            return "… "
        for i in range(1, len(words) + 1):
            rem = "".join(words[i:])
            cand = "… " + rem if rem else "… "
            if self.font.getlength(cand + active) <= max_w:
                return cand
        return "… "

    def _build(self, width: int, view: Any, small: List[str], n_stats: int) -> np.ndarray:
        from PIL import Image, ImageDraw
        is_view_dict = isinstance(view, dict)
        num_big = 1 if is_view_dict else len(view)
        height = self.line_h * num_big + self.small_h * (len(small) + n_stats) + 8  # + lines for the live stats
        img = Image.new("RGB", (width, height), self.BG_RGB)
        d = ImageDraw.Draw(img)
        y = 4

        if not is_view_dict:
            for text in view:
                d.text((8, y), text, font=self.font, fill=self.TEXT_RGB)
                y += self.line_h
        else:
            committed = view.get("committed", "")
            active = view.get("active", "")
            preview = view.get("preview")

            x0 = 8
            max_cursor_w = max(width - 24 - x0, 100)
            disp_committed = self._fit_committed(committed, active, max_cursor_w)

            # 1. Committed text
            w_comm = self.font.getlength(disp_committed) if disp_committed else 0.0
            if disp_committed:
                d.text((x0, y), disp_committed, font=self.font, fill=self.TEXT_RGB)

            # 2. Active text with highlight background
            x_active = x0 + w_comm
            w_act = self.font.getlength(active) if active else 0.0
            if active and w_act > 0:
                rect_x0 = int(round(x_active))
                rect_x1 = int(round(x_active + w_act))
                d.rectangle([(rect_x0, y), (rect_x1, y + self.line_h - 2)], fill=self.HIGHLIGHT_RGB)
                d.text((rect_x0, y), active, font=self.font, fill=self.TEXT_RGB)

            # 3. Cursor
            x_cursor = int(round(x_active + w_act))
            d.line([(x_cursor, y + 2), (x_cursor, y + self.line_h - 4)], fill=self.CURSOR_RGB, width=2)

            # 4. Preview
            if preview is not None and (preview.get("token") is not None or preview.get("prediction") is not None):
                conf = preview.get("confidence")
                conf_str = f"{conf:.2f}" if conf is not None else ""
                active_if = preview.get("active_if_accepted", "")
                if active_if:
                    prev_label = f" {active_if} (a: nhận, {conf_str})"
                else:
                    prev_label = f" (a: nhận, {conf_str})"
                x_prev = x_cursor + 4
                d.text((x_prev, y), prev_label, font=self.font, fill=self.PREVIEW_RGB)

            y += self.line_h

        for text in small:
            d.text((8, y), text, font=self.small, fill=(200, 220, 255))
            y += self.small_h
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
        y = view.shape[0]
        if hold_progress > 0:
            cv2.rectangle(out, (0, y), (int(w * hold_progress), y + 3), (0, 200, 0), -1)
        for i, line in enumerate(stats_lines):
            base = out.shape[0] - 10 - (len(stats_lines) - 1 - i) * self.small_h
            cv2.putText(out, line, (8, base), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 255, 160), 1, cv2.LINE_AA)
        return out


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


# ---------------------------------------------------------------------------------------------------------- app
class Level1App:
    """One run of the app. `classifier` / `session_factory` can be given (tests); keep_segments keeps the emitted
    SignSegments in memory (tests only; never written)."""

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
        self.speller = Level1Speller(self.values["accept_confidence"])
        self.rearm_mode = self.values["rearm_mode"]
        self.classifier_mode = self.rearm_mode == "classifier"
        stages = FRAME_STAGES + SIGN_STAGES + (WINDOW_STAGES if self.classifier_mode else ())
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
    def _window_frame(self, ts_ms: float, landmarks, handedness: str, w: int, h: int) -> None:
        """Window of this frame -> classification (headless: now; otherwise newest-job worker) -> timeline."""
        self.window.push(ts_ms, landmarks, handedness, w, h)
        entry = ["frame", ts_ms, landmarks is not None, True, None]
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
            kind, ts_ms, has_hand, _resolved, payload = self.timeline.pop(0)
            if kind == "gap":
                self.speller.word_gap(payload, t_ms=ts_ms)
            elif kind == "next":
                self.decoder.force_next(ts_ms)
            elif kind == "reset":
                self.decoder.reset()
            else:
                emit = self.decoder.push(ts_ms, has_hand, payload)
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
                if self.classifier_mode:
                    self.window.reset()
                    self.timeline.append(["reset", self.last_ts, False, True, None])
                    self._drain_timeline()
            self._log("pause" if self.paused else "resume", t_ms=self.last_ts)
        elif k in KEY_ACTIONS and KEY_ACTIONS[k] == KEY_NEXT:
            self._next_key()
        elif k in KEY_ACTIONS:
            self.speller.key(KEY_ACTIONS[k], t_ms=self.last_ts)

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
        how long its label has held against cls_stable_ms (0 when the window is below cls_conf), last emitted label."""
        w = self.last_window
        top1 = w["top1"] if w is not None and w["top1"] is not None else "—"
        conf = f"{w['conf']:.2f}" if w is not None and w["conf"] is not None else "—"
        held = w["run_ms"] if w is not None and w["run_label"] is not None else 0.0
        last = self.decoder.last_label if self.decoder.last_label is not None else "—"
        line = (f"[classifier] cửa sổ: {top1} {conf} | giữ {held:.0f}/{self.values['cls_stable_ms']:.0f} | "
                f"cuối: {last}")
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
        landmarks, handedness, _score = session.process(frame)
        t1 = time.perf_counter()
        self.times.add("mediapipe", (t1 - t0) * 1000.0)
        if not self.paused:
            self._on_events(self.segmenter.push(ts_ms, landmarks, handedness, w, h))
        t2 = time.perf_counter()
        self.times.add("segmenter", (t2 - t1) * 1000.0)
        if self.classifier_mode and not self.paused:  # a word gap of this frame is a no-hand frame: order unaffected
            self._window_frame(ts_ms, landmarks, handedness, w, h)
            t2 = time.perf_counter()
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
        view = self.hud.compose(view, tb_view, small, progress, stats)
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
                cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
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
        if self.config_overrides:  # only with --cls-window-ms: otherwise the report keeps its keys (AC-6b)
            report["config"]["overrides"] = dict(self.config_overrides)
        if self.trace_windows:  # without the flag the report keeps exactly its keys of before (lần sửa 6 AC-6b)
            report["window_trace"] = {"max_entries": TRACE_MAX_ENTRIES, "n_windows": self.window_trace_n,
                                      "truncated": self.window_trace_n > len(self.window_trace),
                                      "fields": list(TRACE_KEYS), "entries": list(self.window_trace)}
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VSLT Level 1 (fingerspelling) realtime desktop app (plan 15).")
    p.add_argument("--source", required=True, help="webcam index (e.g. 0) or a video file")
    p.add_argument("--headless", action="store_true", help="no window (video sources only)")
    p.add_argument("--out-json", default=None, help="write the run report (JSON) to this path")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="parameter file (default %(default)s)")
    p.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT, help="Level 1 checkpoint (default %(default)s)")
    p.add_argument("--pace", choices=("all", "realtime"), default="all",
                   help="video: 'all' = every frame in order; 'realtime' = read at the file's frame rate and process "
                        "only the newest frame, like a webcam")
    p.add_argument("--expected", default=None, help="text the signer intends to spell (written to the JSON)")
    p.add_argument("--display-mirror", action="store_true", help="show the image mirrored (display only)")
    p.add_argument("--font", default=None, help="TrueType font with Vietnamese glyphs for the HUD")
    p.add_argument("--trace-windows", action="store_true",
                   help="rearm_mode classifier: write every window result and the decoder state (window_trace) to "
                        f"the JSON, at most {TRACE_MAX_ENTRIES} entries; no landmark or frame (default off)")
    p.add_argument("--cls-window-ms", type=positive_ms, default=None,
                   help="rearm_mode classifier: length of the sliding window in milliseconds for this run, in place "
                        "of cls_window_ms of the config (the file is not changed; written to the JSON as "
                        "config.overrides)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
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
