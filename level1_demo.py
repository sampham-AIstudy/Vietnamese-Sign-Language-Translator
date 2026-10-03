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
  r repeat the last letter | c clear | p pause / resume segmentation | q or Esc quit.

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
from src.inference.level1_segmenter import Level1SignSegmenter, SignSegment, WordGap  # noqa: E402
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
KEY_ACTIONS = {8: "backspace", 32: "space", ord("a"): "accept", ord("r"): "repeat", ord("c"): "clear"}
KEY_QUIT = (ord("q"), 27)
KEY_PAUSE = ord("p")
STATE_LABELS = {"no_hand": "không thấy tay", "moving": "đang chuyển động", "holding": "đang giữ yên"}


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

    def __init__(self, font_path: str, font_size: int):
        from PIL import ImageFont
        self.font = ImageFont.truetype(font_path, font_size)
        self.small = ImageFont.truetype(font_path, max(1, int(font_size * 2 / 3)))
        self.line_h = int(font_size * 1.35)
        self.small_h = int(font_size * 0.95)
        self._key = None
        self._panel = None

    def _build(self, width: int, big: List[str], small: List[str], n_stats: int) -> np.ndarray:
        from PIL import Image, ImageDraw
        height = self.line_h * len(big) + self.small_h * (len(small) + n_stats) + 8  # + lines for the live stats
        img = Image.new("RGB", (width, height), (20, 20, 20))
        d = ImageDraw.Draw(img)
        y = 4
        for text in big:
            d.text((8, y), text, font=self.font, fill=(255, 255, 255))
            y += self.line_h
        for text in small:
            d.text((8, y), text, font=self.small, fill=(200, 220, 255))
            y += self.small_h
        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    def compose(self, view: np.ndarray, big: List[str], small: List[str], hold_progress: float,
                stats_lines: Sequence[str] = ()) -> np.ndarray:
        """Window image = the camera image with the text panel stacked BELOW it (the hand is never covered); a
        green bar on top of the panel shows the hold progress. The PIL panel (Vietnamese text) is cached; the live
        stats lines (ASCII, change every frame) are drawn with cv2.putText on the last lines of the panel."""
        w = view.shape[1]
        stats_lines = list(stats_lines)
        key = (w, tuple(big), tuple(small), len(stats_lines))
        if key != self._key:
            self._panel, self._key = self._build(w, big, small, len(stats_lines)), key
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
        self.times = StageTimes(FRAME_STAGES + SIGN_STAGES, self.values["hud_rolling_frames"])
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
                self.speller.word_gap(ev.seq, t_ms=ev.t_ms)

    def _drain_worker(self, results) -> None:
        for seg, result, classify_ms, error in results:
            if error is not None:
                raise error
            self._apply_result(seg, result, classify_ms)

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
            self._log("pause" if self.paused else "resume", t_ms=self.last_ts)
        elif k in KEY_ACTIONS:
            self.speller.key(KEY_ACTIONS[k], t_ms=self.last_ts)

    # -------------------------------------------------------------- one frame
    def _hud_lines(self):
        comp = self.speller.composed()
        big = ["Văn bản: " + (comp["text"] or "")]
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
        small = [last, "Trạng thái: " + state]
        for w in comp["warnings"][-2:]:
            small.append("Cảnh báo: " + w["code"])
        small.append("Backspace xóa | Space cách | a nhận | r lặp chữ | c xóa hết | p dừng | q thoát")
        dropped = self.slot.dropped if self.slot is not None else 0
        stats = hud_stats_lines(self.times, self.process_starts, self.values["hud_rolling_frames"], dropped)
        return big, small, st["hold_progress"], stats

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
        self.last_ts = ts_ms
        t2 = time.perf_counter()
        self.times.add("segmenter", (t2 - t1) * 1000.0)
        self.counts["frames_processed"] += 1
        if self.worker is not None:
            self._drain_worker(self.worker.poll())
        if not self.display:
            self.times.add("frame_total", (time.perf_counter() - t_cap) * 1000.0)
            return
        draw_landmarks(frame, landmarks)
        t3 = time.perf_counter()
        self.times.add("draw_landmarks", (t3 - t2) * 1000.0)
        view = display_view(frame, self.args.display_mirror)
        big, small, progress, stats = self._hud_lines()
        view = self.hud.compose(view, big, small, progress, stats)
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
            if self.last_ts is not None and not self.paused:
                self._on_events(self.segmenter.flush(self.last_ts))
            if self.worker is not None:
                self._drain_worker(self.worker.finish())
                self.worker = None
        finally:
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
        return {
            "generated_by": generated_by(self.argv),
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
            "events": self.events + self.speller.events,
            "expected": expected,
            "note": NOTE,
        }


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
