"""
Level 1 ("Đánh vần") core shared by the desktop app (level1_demo.py) and, later, the web path (plan 15 §3.4).

- load_level1_config(path): configs/level1_realtime.json -> validated parameters (no default value in code).
- Level1Classifier: loads the Level 1 checkpoint like backend/main.py get_or_load_alphabet_model and classifies a
  SignSegment through alphabet_clip_features (the preprocessing shared with training); the result has the keys and
  rounding of POST /api/fingerspelling/sequence plus a status.
- Level1Speller: accepts tokens (model result >= accept_confidence, or a key press), keeps the event order and
  composes the text with fingerspelling_compose.compose (never guesses letters; a letter is only replaced by its
  diacritic variant when the label decoder says so, on_label).
- enhance_low_light(frame_bgr): adaptive CLAHE on the L channel of a dark frame before hand detection (plan 15 lần sửa
  8 M2; the desktop demo's --auto-enhance only, never on the training / offline path).
- LandmarkSmoother: adaptive moving average of the hand points (plan 15 lần sửa 10 P2; the desktop demo's
  --smooth-landmarks only, never on the training / offline path).
- foreshortening_ratio(landmarks): projected / 3D length of the index finger (plan 15 lần sửa 10 P3; HUD angle hint).
- HandednessLock: locks the handedness label of a run to the majority of MediaPipe's own labels on the first hand frames
  (plan 15 lần sửa 12 H1; the desktop demo's --dominant-hand lock only).

No GUI, no thread, no camera.
"""
import hashlib
import json
import numbers
import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.data.alphabet_preprocessing import DEFAULT_ALPHABET_PREPROCESSING, alphabet_clip_features
from src.inference.fingerspelling_compose import SPACE, TONE_MARKS, compose, token_kind
from src.inference.level1_segmenter import DIACRITIC_FUSION, VARIANT_BASE, is_variant_of

# key -> (kind, check); kind: "number" | "int" | "bool" | "str" | "str_list" | "enum" (check = name in ENUMS)
CONFIG_SPEC = {
    "motion_window_ms": ("number", "positive"),
    "still_speed": ("number", "positive"),
    "move_over_still_ratio": ("number", "above_one"),
    "move_speed": ("number", "positive"),
    "hold_ms_design": ("number", "positive"),
    "hold_ms": ("number", "positive"),
    "tail_still_keep_ms": ("number", "positive"),
    "rearm_move_ms": ("number", "positive"),
    "pose_change_rules": ("bool", "bool"),
    "rearm_pose_dist": ("number", "positive"),
    "pose_over_jitter_ratio": ("number", "above_one"),
    "rearm_mode": ("enum", "rearm_mode"),
    "cls_window_ms": ("number", "positive"),
    "cls_conf": ("number", "unit_interval"),
    "cls_stable_ms": ("number", "positive"),
    "hand_lost_ms": ("number", "positive"),
    "word_gap_ms": ("number", "positive"),
    "max_segment_ms": ("number", "positive"),
    "min_sign_frames": ("int", "positive"),
    "accept_confidence": ("number", "unit_interval"),
    "top_k": ("int", "positive"),
    "camera_width": ("int", "positive"),
    "camera_height": ("int", "positive"),
    "camera_api": ("str", "camera_api"),
    "camera_buffersize": ("int", "positive"),
    "hud_font_size": ("int", "positive"),
    "hud_rolling_frames": ("int", "positive"),
    "font_paths": ("str_list", "non_empty"),
}
# keys a config may leave out (plan 15 lần sửa 7): checked like CONFIG_SPEC when present; an absent key means the
# behaviour without it (Level1LabelDecoder falls back to cls_conf / cls_stable_ms, no dropout debounce, no motion gate)
OPTIONAL_CONFIG_SPEC = {
    "cls_conf_tone": ("number", "unit_interval"),
    "cls_stable_ms_tone": ("number", "positive"),
    "dropout_tolerance_ms": ("number", "positive"),
    "cls_motion_gate": ("bool", "bool"),  # plan 15 lần sửa 12 G1
}
CAMERA_APIS = ("dshow", "msmf", "any")
REARM_MODES = ("motion_pose", "classifier")  # plan 15 lần sửa 4 §3.3: segmenter re-arm (motion / pose) or label decoder
ENUMS = {"rearm_mode": REARM_MODES}
CALIBRATED_PREFIX = "calibrated: "


def _check_value(key: str, value: Any) -> None:
    kind, check = CONFIG_SPEC[key] if key in CONFIG_SPEC else OPTIONAL_CONFIG_SPEC[key]
    if kind in ("number", "int"):
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise ValueError(f"config {key}: value must be a number, got {value!r}")
        if kind == "int" and not isinstance(value, numbers.Integral):
            raise ValueError(f"config {key}: value must be an integer, got {value!r}")
        if not value == value or value in (float("inf"), float("-inf")):
            raise ValueError(f"config {key}: value must be finite")
        if check == "positive" and not value > 0:
            raise ValueError(f"config {key}: value must be > 0, got {value!r}")
        if check == "above_one" and not value > 1:
            raise ValueError(f"config {key}: value must be > 1, got {value!r}")
        if check == "unit_interval" and not 0 < value <= 1:
            raise ValueError(f"config {key}: value must be in (0, 1], got {value!r}")
    elif kind == "bool":
        if not isinstance(value, bool):  # a real JSON true / false; 0 / 1 are refused
            raise ValueError(f"config {key}: value must be true or false, got {value!r}")
    elif kind == "str":
        if not isinstance(value, str):
            raise ValueError(f"config {key}: value must be a string, got {value!r}")
        if check == "camera_api" and value not in CAMERA_APIS:
            raise ValueError(f"config {key}: value must be one of {CAMERA_APIS}, got {value!r}")
    elif kind == "enum":
        if not isinstance(value, str) or value not in ENUMS[check]:
            raise ValueError(f"config {key}: value must be one of {ENUMS[check]}, got {value!r}")
    elif kind == "str_list":
        if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
            raise ValueError(f"config {key}: value must be a non-empty list of strings")


def _entry_value(key: str, entry: Any) -> Any:
    if not isinstance(entry, dict) or "value" not in entry:
        raise ValueError(f"config {key}: must be an object with value, source, reason")
    source, reason = entry.get("source"), entry.get("reason")
    if not isinstance(source, str) or not (source == "design" or (source.startswith(CALIBRATED_PREFIX)
                                                                   and len(source) > len(CALIBRATED_PREFIX))):
        raise ValueError(f"config {key}: source must be 'design' or '{CALIBRATED_PREFIX}<json>@<commit>'")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"config {key}: reason must be a non-empty string")
    _check_value(key, entry["value"])
    return entry["value"]


def validate_level1_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Raw config dict -> {key: value}. Raises ValueError on a missing key, a missing / empty source or reason,
    a wrong type, move_speed <= still_speed or word_gap_ms < hand_lost_ms. Keys starting with '_' are comments.
    The keys of OPTIONAL_CONFIG_SPEC are checked the same way when present and returned after the others."""
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in CONFIG_SPEC
                     and k not in OPTIONAL_CONFIG_SPEC)
    if unknown:
        raise ValueError(f"config: unknown keys {unknown}")
    values = {}
    for key in CONFIG_SPEC:
        if key not in raw:
            raise ValueError(f"config: missing key {key!r}")
        values[key] = _entry_value(key, raw[key])
    for key in OPTIONAL_CONFIG_SPEC:
        if key in raw:
            values[key] = _entry_value(key, raw[key])
    if not values["move_speed"] > values["still_speed"]:
        raise ValueError("config: move_speed must be > still_speed")
    if values["word_gap_ms"] < values["hand_lost_ms"]:
        raise ValueError("config: word_gap_ms must be >= hand_lost_ms")
    if not (0 < values["tail_still_keep_ms"] <= values["hold_ms"]):
        raise ValueError("config: tail_still_keep_ms must be > 0 and <= hold_ms")
    return values


def load_level1_config(path: str) -> Dict[str, Any]:
    """configs/level1_realtime.json -> {"values": {key: value}, "raw": parsed JSON, "path", "sha256"}."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"config {os.path.basename(path)}: not valid UTF-8 JSON ({e})") from None
    return {"values": validate_level1_config(raw), "raw": raw, "path": path,
            "sha256": hashlib.sha256(data).hexdigest()}


# ----------------------------------------------------------------------------------------------------------------------
# Classifier (plan 15 §3.4)
# ----------------------------------------------------------------------------------------------------------------------
def class_kind(name: str) -> Optional[str]:
    """'letter' | 'tone' for a Level 1 class name; None outside the Level 1 vocabulary (as backend class_kind)."""
    try:
        return token_kind(name)
    except ValueError:
        return None


class Level1Classifier:
    """Level 1 checkpoint + the shared preprocessing. classify() returns the keys and rounding of
    POST /api/fingerspelling/sequence plus status 'ok'; 'too_few_frames' / 'invalid' carry no prediction."""

    def __init__(self, model, classes: List[str], preprocessing: Dict[str, Any], model_type: str,
                 checkpoint_path: str):
        self.model = model
        self.classes = list(classes)
        self.preprocessing = dict(preprocessing)
        self.model_type = model_type
        self.checkpoint_path = checkpoint_path
        self.checkpoint = os.path.basename(checkpoint_path)
        self.min_detected_frames = int({**DEFAULT_ALPHABET_PREPROCESSING, **self.preprocessing}["min_detected_frames"])

    @classmethod
    def from_checkpoint(cls, path: str) -> "Level1Classifier":
        """Same loading as backend/main.py get_or_load_alphabet_model: `classes` and `preprocessing` are required
        (ValueError otherwise), model built from model_type / hparams, eval()."""
        import torch
        ckpt = torch.load(path, map_location="cpu")
        if not isinstance(ckpt, dict) or "classes" not in ckpt or "preprocessing" not in ckpt:
            raise ValueError(f"{os.path.basename(path)}: checkpoint must carry 'classes' and 'preprocessing'")
        classes, preprocessing = list(ckpt["classes"]), dict(ckpt["preprocessing"])
        model_type = ckpt.get("model_type", "bigru")
        hparams = ckpt.get("hparams", {})
        if model_type == "mlp":
            from src.models.alphabet_mlp import VSLAlphabetMLP
            model = VSLAlphabetMLP(input_dim=63, num_classes=len(classes),
                                   hidden_dims=tuple(hparams.get("hidden_dims", (128, 64))))
        else:
            from src.models.alphabet_temporal import VSLAlphabetBiGRU
            model = VSLAlphabetBiGRU(input_dim=63, hidden_dim=hparams.get("hidden_dim", 64),
                                     num_layers=hparams.get("num_layers", 2), num_classes=len(classes))
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        return cls(model, classes, preprocessing, model_type, path)

    def features(self, segment) -> np.ndarray:
        """alphabet_clip_features of a SignSegment (raises ValueError with too few hand frames)."""
        return alphabet_clip_features(segment.raw_landmarks, segment.detected, segment.handedness,
                                      segment.frame_width / segment.frame_height, segment.timestamps_ms,
                                      self.preprocessing, self.model_type)

    def warmup(self) -> float:
        """One forward pass on an all-zero input of the model's shape (result discarded); returns its duration in
        ms (first-call cost, reported apart from the per-sign timings)."""
        import time
        import torch
        n = int({**DEFAULT_ALPHABET_PREPROCESSING, **self.preprocessing}["target_frames"])
        shape = (1, 63) if self.model_type == "mlp" else (1, n, 63)
        t0 = time.perf_counter()
        with torch.no_grad():
            self.model(torch.zeros(shape, dtype=torch.float32))
        return (time.perf_counter() - t0) * 1000.0

    def classify(self, segment, top_k: int) -> Dict[str, Any]:
        import torch
        base = {"frames": segment.n_frames, "detected_frames": segment.n_detected,
                "model_type": self.model_type, "checkpoint": self.checkpoint}
        if segment.n_detected < self.min_detected_frames:
            return {"status": "too_few_frames", **base}
        feats = self.features(segment)
        if not np.isfinite(feats).all():
            return {"status": "invalid", "reason_detail": "non-finite features", **base}
        with torch.no_grad():
            probs = torch.softmax(self.model(torch.from_numpy(feats).unsqueeze(0)), dim=-1)[0]
        if not bool(torch.isfinite(probs).all()):
            return {"status": "invalid", "reason_detail": "non-finite probabilities", **base}
        topk = torch.topk(probs, k=min(int(top_k), len(self.classes)))
        candidates = [{"class": self.classes[i], "confidence": round(v, 4), "kind": class_kind(self.classes[i])}
                      for v, i in zip(topk.values.tolist(), topk.indices.tolist())]
        return {"status": "ok", "prediction": candidates[0]["class"], "prediction_kind": candidates[0]["kind"],
                "confidence": candidates[0]["confidence"], "candidates": candidates, **base}


# ----------------------------------------------------------------------------------------------------------------------
# Speller (plan 15 §3.4)
# ----------------------------------------------------------------------------------------------------------------------
KEY_NAMES = ("backspace", "space", "accept", "repeat", "clear", "tone_1", "tone_2", "tone_3", "tone_4", "tone_5")
DIACRITIC_FUSION = {
    # Base letter -> {trigger signs -> target accented vowel}
    "a": {"â": "â", "ô": "â", "ê": "â", "ă": "ă"},
    "o": {"â": "ô", "ô": "ô", "ê": "ô", "ơ": "ơ", "ư": "ơ"},
    "e": {"â": "ê", "ô": "ê", "ê": "ê"},
    "u": {"ơ": "ư", "ư": "ư"},
    "d": {"đ": "đ"},
}


class Level1Speller:
    """Token list + event log. Events of the segmenter are applied in emission order: a WordGap emitted after
    segment k waits for k's result. Text = compose(tokens)["text"]; letters are never edited or guessed.

    - result with status 'ok' and confidence >= accept_confidence -> token added (source 'model');
      otherwise kept as the latest rejected candidate (not added);
    - word gap -> ' ' when the last token exists and is not ' ' (source 'model', reason 'word_gap');
    - keys (source 'key'): backspace = remove the last token (nothing on an empty list); space = ' ' with the same
      rule as a word gap; accept = add the latest rejected candidate that has a prediction; repeat = add the last
      token again when it is a letter; clear = remove every token."""

    def __init__(self, accept_confidence: float, unikey_mode: bool = False):
        self.accept_confidence = float(accept_confidence)
        self.unikey_mode = bool(unikey_mode)
        self.tokens: List[str] = []
        self.events: List[Dict[str, Any]] = []
        self.rejected: Optional[Dict[str, Any]] = None
        self._queue: List[tuple] = []          # ("segment", seq) | ("gap", seq), emission order
        self._results: Dict[int, Dict[str, Any]] = {}
        self._result_t: Dict[int, Optional[float]] = {}

    @staticmethod
    def _is_tone(tok: str) -> bool:
        return tok in TONE_MARKS

    def _find_tone_in_active_syllable(self) -> Optional[Tuple[int, str]]:
        """Returns (index, tone_token) of the tone mark in the active syllable (after last SPACE), or None."""
        k = 0
        for i in range(len(self.tokens) - 1, -1, -1):
            if self.tokens[i] == SPACE:
                k = i + 1
                break
        for i in range(len(self.tokens) - 1, k - 1, -1):
            if self._is_tone(self.tokens[i]):
                return i, self.tokens[i]
        return None

    # ---------------------------------------------------------------- text
    @property
    def view(self) -> Dict[str, Any]:
        from src.inference.level1_textbox import textbox_view
        return textbox_view(self.tokens, self.rejected)

    def composed(self) -> Dict[str, Any]:
        return compose(self.tokens)

    @property
    def text(self) -> str:
        return self.composed()["text"]

    def _log(self, action: str, token: Optional[str], source: str, t_ms: Optional[float], **extra) -> None:
        self.events.append({"event": "token", "action": action, "token": token, "source": source, "t_ms": t_ms,
                            "tokens_after": len(self.tokens), **extra})

    # ---------------------------------------------------------------- model side
    def segment_emitted(self, seq: int) -> None:
        self._queue.append(("segment", seq))

    def word_gap(self, seq: int, t_ms: Optional[float] = None) -> List[Dict[str, Any]]:
        self._queue.append(("gap", seq))
        self._result_t[seq] = t_ms
        return self._drain()

    def on_result(self, seq: int, result: Dict[str, Any], t_ms: Optional[float] = None) -> List[Dict[str, Any]]:
        """Result of segment `seq` (registered or not). Returns the decisions applied now, in order:
        [{seq, accepted, status, prediction, confidence}]."""
        if ("segment", seq) not in self._queue:
            self._queue.append(("segment", seq))
        self._results[seq] = result
        self._result_t[seq] = t_ms
        return self._drain()

    def _drain(self) -> List[Dict[str, Any]]:
        decisions = []
        while self._queue:
            kind, seq = self._queue[0]
            if kind == "gap":
                self._queue.pop(0)
                self.on_word_gap(self._result_t.pop(seq, None))
                continue
            if seq not in self._results:
                break
            self._queue.pop(0)
            decisions.append(self._apply(seq, self._results.pop(seq), self._result_t.pop(seq, None)))
        return decisions

    def _apply(self, seq: int, r: Dict[str, Any], t_ms: Optional[float]) -> Dict[str, Any]:
        status = r.get("status")
        prediction = r.get("prediction") if status == "ok" else None
        conf = r.get("confidence") if status == "ok" else None
        accepted = status == "ok" and conf is not None and conf >= self.accept_confidence
        if accepted:
            if self.unikey_mode and self._is_tone(prediction) and self._find_tone_in_active_syllable() is not None:
                idx, old_tone = self._find_tone_in_active_syllable()
                self.tokens[idx] = prediction
                self._log("replace", prediction, "model", t_ms, seq=seq, confidence=conf, replaced=old_tone)
            elif self.unikey_mode and self.tokens and self.tokens[-1] in DIACRITIC_FUSION and prediction in DIACRITIC_FUSION[self.tokens[-1]]:
                old = self.tokens[-1]
                target = DIACRITIC_FUSION[old][prediction]
                self.tokens[-1] = target
                self._log("replace", target, "model", t_ms, seq=seq, confidence=conf, replaced=old)
            else:
                self.tokens.append(prediction)
                self._log("add", prediction, "model", t_ms, seq=seq, confidence=conf)
        else:
            self.rejected = {"seq": seq, "status": status, "prediction": prediction, "confidence": conf}
            self._log("reject", prediction, "model", t_ms, seq=seq, confidence=conf, status=status)
        return {"seq": seq, "accepted": accepted, "status": status, "prediction": prediction, "confidence": conf}

    def on_label(self, seq: int, emit) -> Dict[str, Any]:
        """Label emitted by Level1LabelDecoder (rearm_mode 'classifier', plan 15 lần sửa 4 §3.4), applied at once
        (no segment queue: the decoder emits in timestamp order). Accepted with the same rule as on_result
        (confidence >= accept_confidence). action 'append' = token added; 'replace' = the last token is replaced
        when it is the base letter of the label (VARIANT_BASE), otherwise the label is added."""
        prediction, conf, t_ms = emit.prediction, emit.confidence, emit.ts_ms
        accepted = conf is not None and conf >= self.accept_confidence
        action = None
        if not accepted:
            self.rejected = {"seq": seq, "status": "ok", "prediction": prediction, "confidence": conf}
            self._log("reject", prediction, "model", t_ms, seq=seq, confidence=conf, status="ok")
        elif emit.action == "replace" and self.tokens and self.tokens[-1] == VARIANT_BASE.get(prediction):
            old = self.tokens[-1]
            self.tokens[-1] = prediction
            action = "replace"
            self._log("replace", prediction, "model", t_ms, seq=seq, confidence=conf, replaced=old)
        elif self.unikey_mode and self.tokens and self.tokens[-1] in DIACRITIC_FUSION and prediction in DIACRITIC_FUSION[self.tokens[-1]]:
            old = self.tokens[-1]
            target = DIACRITIC_FUSION[old][prediction]
            self.tokens[-1] = target
            action = "replace"
            self._log("replace", target, "model", t_ms, seq=seq, confidence=conf, replaced=old)
        elif self.unikey_mode and self._is_tone(prediction) and self._find_tone_in_active_syllable() is not None:
            idx, old_tone = self._find_tone_in_active_syllable()
            self.tokens[idx] = prediction
            action = "replace"
            self._log("replace", prediction, "model", t_ms, seq=seq, confidence=conf, replaced=old_tone)
        else:
            self.tokens.append(prediction)
            action = "add"
            self._log("add", prediction, "model", t_ms, seq=seq, confidence=conf)
        return {"seq": seq, "accepted": accepted, "status": "ok", "prediction": prediction, "confidence": conf,
                "action": action}

    def on_word_gap(self, t_ms: Optional[float] = None) -> bool:
        if self.tokens and self.tokens[-1] != SPACE:
            self.tokens.append(SPACE)
            self._log("add", SPACE, "model", t_ms, reason="word_gap")
            return True
        return False

    # ---------------------------------------------------------------- keys
    def key(self, name: str, t_ms: Optional[float] = None) -> bool:
        """Applies a key action (KEY_NAMES); returns True when the tokens changed."""
        if name not in KEY_NAMES:
            raise ValueError(f"unknown key action {name!r}")
        if name == "backspace":
            if not self.tokens:
                return False
            tok = self.tokens.pop()
            self._log("remove", tok, "key", t_ms, key=name)
            return True
        if name == "space":
            if not self.tokens:
                return False
            if self.unikey_mode:
                self.tokens.append(SPACE)
                self._log("add", SPACE, "key", t_ms, key=name)
                return True
            if self.tokens[-1] != SPACE:
                self.tokens.append(SPACE)
                self._log("add", SPACE, "key", t_ms, key=name)
                return True
            return False
        if name == "accept":
            r = self.rejected
            if r is None or r["prediction"] is None:
                return False
            self.tokens.append(r["prediction"])
            self.rejected = None
            self._log("add", r["prediction"], "key", t_ms, key=name, seq=r["seq"], confidence=r["confidence"])
            return True
        if name == "repeat":
            if not self.tokens or token_kind(self.tokens[-1]) != "letter":
                return False
            self.tokens.append(self.tokens[-1])
            self._log("add", self.tokens[-1], "key", t_ms, key=name)
            return True
        if name.startswith("tone_"):
            tone_map = {
                "tone_1": "dấu sắc",
                "tone_2": "dấu huyền",
                "tone_3": "dấu hỏi",
                "tone_4": "dấu ngã",
                "tone_5": "dấu nặng"
            }
            tone = tone_map[name]
            if self.unikey_mode and self._find_tone_in_active_syllable() is not None:
                idx, old_tone = self._find_tone_in_active_syllable()
                self.tokens[idx] = tone
                self._log("replace", tone, "key", t_ms, key=name, replaced=old_tone)
            else:
                self.tokens.append(tone)
                self._log("add", tone, "key", t_ms, key=name)
            return True
        # clear
        if not self.tokens and self.rejected is None:
            return False
        n = len(self.tokens)
        self.tokens.clear()
        self.rejected = None
        self._log("clear", None, "key", t_ms, key=name, removed=n)
        return True


# ---------------------------------------------------------------------------------------------- low light (lần sửa 8)
# plan 15 lần sửa 8 §2 M2: design values of the plan (mean gray level of the frame, CLAHE clip limit and tile grid)
LOW_LIGHT_THRESHOLD = 80.0
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)


def enhance_low_light(frame_bgr: np.ndarray, threshold: float = LOW_LIGHT_THRESHOLD,
                      clip_limit: float = CLAHE_CLIP_LIMIT) -> Tuple[np.ndarray, bool]:
    """(frame, enhanced). Mean of the grayscale frame < threshold: BGR -> LAB, CLAHE (clipLimit clip_limit, tile grid
    CLAHE_TILE_GRID) on the L channel, LAB -> BGR -> (new uint8 frame, True). Otherwise (frame_bgr itself, False).
    frame_bgr (uint8, H x W x 3, BGR) is never modified."""
    if not (isinstance(frame_bgr, np.ndarray) and frame_bgr.dtype == np.uint8 and frame_bgr.ndim == 3
            and frame_bgr.shape[2] == 3):
        raise ValueError("enhance_low_light needs a uint8 BGR frame of shape (H, W, 3)")
    if float(np.mean(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY))) >= threshold:
        return frame_bgr, False
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    l_ch = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=CLAHE_TILE_GRID).apply(l_ch)
    return cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR), True


# ------------------------------------------------------------------------------------------ open palm (lần sửa 9)
# plan 15 lần sửa 9 §2 S1: (tip, pip, mcp) of the 4 long fingers (index, middle, ring, little finger)
LONG_FINGERS = ((8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17))
# criterion 2 (design value of the plan): thumb tip to little finger MCP > THUMB_SPREAD_RATIO x wrist to middle MCP
THUMB_SPREAD_RATIO = 1.1
# criterion 3 (coder's value, the plan only says "not too small"): adjacent fingertips farther apart than
# FINGER_SPREAD_MIN x their MCPs. Fingers side by side keep their tips about as far apart as their knuckles (ratio
# near 1, a little more where two fingers differ in length); fingers spread apart fan out (ratio well above 1).
FINGER_SPREAD_MIN = 1.2


def is_open_palm_space(landmarks: Optional[np.ndarray]) -> bool:
    """True when the hand is the open palm of the space gesture (plan 15 lần sửa 9 §2 S1): all 5 fingers spread.
    landmarks: the 21 MediaPipe hand points [21, 3] (or [21, 2]) in coordinates with the same scale on every axis
    (pixels, or MediaPipe output with x and z multiplied by width / height as level1_segmenter.aspect_points does);
    only distances between points of the same hand are compared, so position, size, rotation and mirroring do not
    matter.
      1. the 4 long fingers are straight: for (tip, pip, mcp) dist(tip, wrist) > dist(pip, wrist) and
         dist(tip, mcp) > dist(pip, mcp);
      2. the thumb is spread away from the palm and straight: dist(4, 17) > THUMB_SPREAD_RATIO x dist(9, 0) and
         dist(4, 0) > dist(3, 0) (b: 4 straight fingers, thumb folded across the palm);
      3. the fingers are apart: dist(8, 12), dist(12, 16), dist(16, 20) > FINGER_SPREAD_MIN x dist of their MCPs
         (5-9, 9-13, 13-17).
    None, a shape other than [21, 2] / [21, 3], a non-finite value or a degenerate hand (wrist on the middle MCP) ->
    False. Pure computation."""
    if landmarks is None:
        return False
    p = np.asarray(landmarks, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] != 21 or p.shape[1] not in (2, 3) or not np.all(np.isfinite(p)):
        return False

    def dist(i: int, j: int) -> float:
        return float(np.linalg.norm(p[i] - p[j]))

    palm = dist(9, 0)
    if not palm > 0:
        return False
    for tip, pip, mcp in LONG_FINGERS:
        if not (dist(tip, 0) > dist(pip, 0) and dist(tip, mcp) > dist(pip, mcp)):
            return False
    if not (dist(4, 17) > THUMB_SPREAD_RATIO * palm and dist(4, 0) > dist(3, 0)):
        return False
    for (tip_a, _pa, mcp_a), (tip_b, _pb, mcp_b) in zip(LONG_FINGERS, LONG_FINGERS[1:]):
        if not dist(tip_a, tip_b) > FINGER_SPREAD_MIN * dist(mcp_a, mcp_b):
            return False
    return True


# ---------------------------------------------------------------------------- flat hand flick -> Backspace
GESTURE_BACKSPACE_COOLDOWN = 400.0   # ms cooldown after backspace before another flick can trigger
GESTURE_BACKSPACE_WINDOW = 250.0     # sliding history window for measuring the flick
GESTURE_BACKSPACE_MIN_DX = 0.05      # minimum horizontal displacement across the window
GESTURE_BACKSPACE_MIN_SPEED = 0.30   # minimum horizontal speed in screen units/s
GESTURE_BACKSPACE_FLASH = 600.0      # ms to flash HUD banner
GESTURE_BACKSPACE_DEFAULT = False    # off by default in parser (on in default webcam preset)


def is_flat_hand_backspace(landmarks: Optional[np.ndarray], thumb_min_ratio: float = 0.5,
                           thumb_max_spread: float = 1.05) -> bool:
    """True when the hand is the flat hand pose for the backspace gesture: all 5 fingers straight,
    held together (not spread wide like the space gesture).
    landmarks: the 21 MediaPipe hand points [21, 3] (or [21, 2]) in aspect-corrected coordinates.
      1. the 4 long fingers are straight: for (tip, pip, mcp) dist(tip, wrist) > dist(pip, wrist)
         and dist(tip, mcp) > dist(pip, mcp);
      2. the thumb is straight: dist(4, wrist) > dist(3, wrist) and extended (dist(4, wrist) > thumb_min_ratio * palm);
      3. thumb is not spread wide away as in open palm (dist(4, 17) <= thumb_max_spread * palm);
      4. not the open-palm space gesture: not is_open_palm_space(landmarks).
    thumb_min_ratio / thumb_max_spread: flat_thumb_min_ratio / flat_thumb_max_spread of configs/level1_gestures.json
    (plan 15 lần sửa 13 §3.2, passed by level1_gestures.GestureEngine); the defaults are the values of commit 7a267c7,
    so a call with the landmarks only behaves as before.
    None, non-finite values or degenerate hands return False. Pure computation."""
    if landmarks is None:
        return False
    p = np.asarray(landmarks, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] != 21 or p.shape[1] not in (2, 3) or not np.all(np.isfinite(p)):
        return False

    def dist(i: int, j: int) -> float:
        return float(np.linalg.norm(p[i] - p[j]))

    palm = dist(9, 0)
    if not palm > 0:
        return False
    for tip, pip, mcp in LONG_FINGERS:
        if not (dist(tip, 0) > dist(pip, 0) and dist(tip, mcp) > dist(pip, mcp)):
            return False
    if not (dist(4, 0) > dist(3, 0) and dist(4, 0) > thumb_min_ratio * palm):
        return False
    if dist(4, 17) > thumb_max_spread * palm:
        return False
    if is_open_palm_space(landmarks):
        return False
    return True


class BackspaceGestureTracker:
    """Flat hand + horizontal flick/swipe -> Backspace.
    update(ts_ms, landmarks, is_flat, has_hand) returns True exactly once per deliberate flick:
      - keeps a sliding history of (ts_ms, x, y, is_flat, palm) over window_ms (250 ms);
      - triggers Backspace when:
        1. flat hand was present in the recent window;
        2. hand underwent a rapid horizontal movement (dx >= min_dx, vx >= min_speed, dx > 1.1 * dy);
        3. tracker is not in cooldown (cooldown_ms = 400 ms).
    Pure computation, no clock."""

    def __init__(self, cooldown_ms: float = GESTURE_BACKSPACE_COOLDOWN,
                 window_ms: float = GESTURE_BACKSPACE_WINDOW,
                 min_dx: float = GESTURE_BACKSPACE_MIN_DX,
                 min_speed: float = GESTURE_BACKSPACE_MIN_SPEED):
        self.cooldown_ms = float(cooldown_ms)
        self.window_ms = float(window_ms)
        self.min_dx = float(min_dx)
        self.min_speed = float(min_speed)
        self.n_emits = 0
        self.last_emit_ts: Optional[float] = None
        self.last_ts: Optional[float] = None
        self.history: List[Tuple[float, float, float, bool, float]] = []

    def reset(self) -> None:
        self.history.clear()
        self.last_emit_ts = None
        self.last_ts = None

    def is_ready(self, ts_ms: Optional[float]) -> bool:
        """True when the flat hand pose is held and ready to flick (not in cooldown)."""
        if ts_ms is None:
            return False
        if self.last_emit_ts is not None and (ts_ms - self.last_emit_ts) < self.cooldown_ms:
            return False
        return any(h[3] for h in self.history)

    def update(self, ts_ms: float, landmarks: Optional[np.ndarray], is_flat: bool,
               has_hand: bool = True) -> bool:
        ts = float(ts_ms)
        if not np.isfinite(ts):
            raise ValueError("timestamp must be finite")
        self.last_ts = ts
        if not has_hand or landmarks is None:
            self.history.clear()
            return False
        p = np.asarray(landmarks, dtype=np.float64)
        ref_pt = (p[0, :2] + p[9, :2] + p[12, :2]) / 3.0
        palm = float(np.linalg.norm(p[9, :2] - p[0, :2]))
        self.history.append((ts, float(ref_pt[0]), float(ref_pt[1]), bool(is_flat), palm))
        cutoff = ts - self.window_ms
        self.history = [h for h in self.history if h[0] >= cutoff]

        if self.last_emit_ts is not None and (ts - self.last_emit_ts) < self.cooldown_ms:
            return False
        if not any(h[3] for h in self.history):
            return False
        if len(self.history) < 2:
            return False
        dt = (self.history[-1][0] - self.history[0][0]) / 1000.0
        if dt < 0.04:
            return False
        xs = [h[1] for h in self.history]
        ys = [h[2] for h in self.history]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        vx = dx / dt
        avg_palm = np.mean([h[4] for h in self.history])
        is_flick = ((dx >= self.min_dx or (avg_palm > 0 and dx / avg_palm >= 0.35))
                    and vx >= self.min_speed
                    and dx > 1.1 * dy)
        if is_flick:
            self.last_emit_ts = ts
            self.n_emits += 1
            self.history.clear()
            return True
        return False



# ---------------------------------------------------------------------------- landmark smoothing (lần sửa 10)
class LandmarkSmoother:
    """Adaptive exponential moving average of the 21 MediaPipe hand points (plan 15 lần sửa 10 §2 P2), to damp the jitter
    of a hand held still (mostly z: a 2D camera has no depth sensor) without lagging behind a hand that moves.
    filter(ts_ms, landmarks) once per processed frame: out = alpha * landmarks + (1 - alpha) * previous output, with
      alpha = alpha_static  (strong smoothing) when the hand moves slower than speed_threshold,
      alpha = alpha_dynamic (close to 1, follows the hand) otherwise, or when the time step is not > 0.
    Speed = distance in x, y between the palm centre (mean of the 21 points) of the new frame and that of the previous
    output, divided by the time step, in MediaPipe image units per second (coder's reading of the plan: x, y only, since z
    is the noisy axis; the centre averages the 21 points' jitter). The first frame, and the first frame after
    landmarks None or reset(), is returned unchanged. n_static / n_dynamic count the frames smoothed with each weight.
    Pure computation, no clock; the input array is never modified."""

    def __init__(self, alpha_static: float = 0.6, alpha_dynamic: float = 0.9, speed_threshold: float = 0.15):
        for name, value in (("alpha_static", alpha_static), ("alpha_dynamic", alpha_dynamic)):
            if not (isinstance(value, numbers.Real) and np.isfinite(value) and 0.0 < value <= 1.0):
                raise ValueError(f"{name} must be a number in (0, 1], got {value!r}")
        if not (isinstance(speed_threshold, numbers.Real) and np.isfinite(speed_threshold) and speed_threshold > 0):
            raise ValueError(f"speed_threshold must be a finite number > 0, got {speed_threshold!r}")
        self.alpha_static = float(alpha_static)
        self.alpha_dynamic = float(alpha_dynamic)
        self.speed_threshold = float(speed_threshold)
        self.n_static = 0
        self.n_dynamic = 0
        self.reset()

    def reset(self) -> None:
        self._prev: Optional[np.ndarray] = None
        self._prev_ts: Optional[float] = None

    def filter(self, ts_ms: float, landmarks: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """landmarks [21, 3] (or None) at stream time ts_ms -> smoothed float32[21, 3] (None resets, returns None)."""
        if landmarks is None:
            self.reset()
            return None
        p = np.asarray(landmarks, dtype=np.float64)
        if p.shape != (21, 3) or not np.all(np.isfinite(p)):
            raise ValueError(f"landmarks must be a finite array of shape (21, 3), got shape {p.shape}")
        if self._prev is None:
            out = p.copy()
        else:
            dt = (float(ts_ms) - self._prev_ts) / 1000.0
            static = dt > 0 and float(np.linalg.norm(p[:, :2].mean(axis=0) - self._prev[:, :2].mean(axis=0))) / dt \
                < self.speed_threshold
            self.n_static += int(static)
            self.n_dynamic += int(not static)
            alpha = self.alpha_static if static else self.alpha_dynamic
            out = alpha * p + (1.0 - alpha) * self._prev
        self._prev, self._prev_ts = out, float(ts_ms)
        return out.astype(np.float32)


# ------------------------------------------------------------------------------ foreshortening (lần sửa 10 P3)
def foreshortening_ratio(landmarks: Optional[np.ndarray]) -> float:
    """dist_2d(8, 5) / dist_3d(8, 5): projected length of the index finger (tip 8 to MCP 5, x and y) over its 3D length
    (x, y, z), in [0, 1] (plan 15 lần sửa 10 §2 P3). 1 = index finger in the image plane; near 0 = index finger pointing
    straight at the camera, where a 2D camera sees its joints on one line of sight and the depth estimate jitters.
    landmarks: [21, 3] with the same scale on every axis (MediaPipe output through level1_segmenter.aspect_points).
    None, a shape other than [21, 3], a non-finite value or a tip on its MCP -> 1.0 (nothing measured, no hint)."""
    if landmarks is None:
        return 1.0
    p = np.asarray(landmarks, dtype=np.float64)
    if p.shape != (21, 3) or not np.all(np.isfinite(p)):
        return 1.0
    v = p[8] - p[5]
    d3 = float(np.linalg.norm(v))
    if not d3 > 0:
        return 1.0
    return min(1.0, float(np.linalg.norm(v[:2])) / d3)


# ---------------------------------------------------------------------------- handedness lock (lần sửa 12 H1)
HAND_LABELS = ("Left", "Right")
HAND_LOCK_FRAMES = 15  # design value: about half a second of webcam frames; odd, so two labels never tie


class HandednessLock:
    """One handedness label for the whole run, taken from MediaPipe itself (plan 15 lần sửa 12 H1). update(label) once
    per hand frame with MediaPipe's label of that frame: the first lock_frames 'Left' / 'Right' labels are counted and
    returned unchanged; from then on the majority of them is returned for every frame (label, locked). No mapping from
    "the signer's hand" to a label is assumed: which label a right hand gets depends on whether the camera driver
    mirrors the frames, and the lock keeps whatever MediaPipe gives on this camera, as the training clips did (their
    labels came from MediaPipe on the camera's frames). A label outside HAND_LABELS is returned unchanged and not
    counted. Pure computation."""

    def __init__(self, lock_frames: int = HAND_LOCK_FRAMES):
        if isinstance(lock_frames, bool) or not isinstance(lock_frames, numbers.Integral) or lock_frames < 1:
            raise ValueError(f"lock_frames must be an integer >= 1, got {lock_frames!r}")
        self.lock_frames = int(lock_frames)
        self.votes = {k: 0 for k in HAND_LABELS}
        self.label: Optional[str] = None

    @property
    def locked(self) -> bool:
        return self.label is not None

    @property
    def n_votes(self) -> int:
        return sum(self.votes.values())

    def update(self, label: str) -> str:
        if self.label is not None:
            return self.label
        if label not in HAND_LABELS:
            return label
        self.votes[label] += 1
        if self.n_votes >= self.lock_frames:
            # strict majority; a tie (even lock_frames) keeps the label of this frame
            left, right = self.votes["Left"], self.votes["Right"]
            self.label = "Left" if left > right else "Right" if right > left else label
        return label
