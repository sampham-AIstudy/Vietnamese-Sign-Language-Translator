"""
Level 1 ("Đánh vần") core shared by the desktop app (level1_demo.py) and, later, the web path (plan 15 §3.4).

- load_level1_config(path): configs/level1_realtime.json -> validated parameters (no default value in code).
- Level1Classifier: loads the Level 1 checkpoint like backend/main.py get_or_load_alphabet_model and classifies a
  SignSegment through alphabet_clip_features (the preprocessing shared with training); the result has the keys and
  rounding of POST /api/fingerspelling/sequence plus a status.
- Level1Speller: accepts tokens (model result >= accept_confidence, or a key press), keeps the event order and
  composes the text with fingerspelling_compose.compose (never guesses letters; a letter is only replaced by its
  diacritic variant when the label decoder says so, on_label).

No GUI, no thread, no camera.
"""
import hashlib
import json
import numbers
import os
from typing import Any, Dict, List, Optional

import numpy as np

from src.data.alphabet_preprocessing import DEFAULT_ALPHABET_PREPROCESSING, alphabet_clip_features
from src.inference.fingerspelling_compose import SPACE, compose, token_kind
from src.inference.level1_segmenter import VARIANT_BASE

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
CAMERA_APIS = ("dshow", "msmf", "any")
REARM_MODES = ("motion_pose", "classifier")  # plan 15 lần sửa 4 §3.3: segmenter re-arm (motion / pose) or label decoder
ENUMS = {"rearm_mode": REARM_MODES}
CALIBRATED_PREFIX = "calibrated: "


def _check_value(key: str, value: Any) -> None:
    kind, check = CONFIG_SPEC[key]
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


def validate_level1_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Raw config dict -> {key: value}. Raises ValueError on a missing key, a missing / empty source or reason,
    a wrong type, move_speed <= still_speed or word_gap_ms < hand_lost_ms. Keys starting with '_' are comments."""
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in CONFIG_SPEC)
    if unknown:
        raise ValueError(f"config: unknown keys {unknown}")
    values = {}
    for key in CONFIG_SPEC:
        if key not in raw:
            raise ValueError(f"config: missing key {key!r}")
        entry = raw[key]
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(f"config {key}: must be an object with value, source, reason")
        source, reason = entry.get("source"), entry.get("reason")
        if not isinstance(source, str) or not (source == "design" or (source.startswith(CALIBRATED_PREFIX)
                                                                       and len(source) > len(CALIBRATED_PREFIX))):
            raise ValueError(f"config {key}: source must be 'design' or '{CALIBRATED_PREFIX}<json>@<commit>'")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"config {key}: reason must be a non-empty string")
        _check_value(key, entry["value"])
        values[key] = entry["value"]
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


class Level1Speller:
    """Token list + event log. Events of the segmenter are applied in emission order: a WordGap emitted after
    segment k waits for k's result. Text = compose(tokens)["text"]; letters are never edited or guessed.

    - result with status 'ok' and confidence >= accept_confidence -> token added (source 'model');
      otherwise kept as the latest rejected candidate (not added);
    - word gap -> ' ' when the last token exists and is not ' ' (source 'model', reason 'word_gap');
    - keys (source 'key'): backspace = remove the last token (nothing on an empty list); space = ' ' with the same
      rule as a word gap; accept = add the latest rejected candidate that has a prediction; repeat = add the last
      token again when it is a letter; clear = remove every token."""

    def __init__(self, accept_confidence: float):
        self.accept_confidence = float(accept_confidence)
        self.tokens: List[str] = []
        self.events: List[Dict[str, Any]] = []
        self.rejected: Optional[Dict[str, Any]] = None
        self._queue: List[tuple] = []          # ("segment", seq) | ("gap", seq), emission order
        self._results: Dict[int, Dict[str, Any]] = {}
        self._result_t: Dict[int, Optional[float]] = {}

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
            if self.tokens and self.tokens[-1] != SPACE:
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
