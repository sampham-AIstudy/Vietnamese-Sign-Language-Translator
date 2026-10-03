"""
Level 1 ("Đánh vần") core shared by the desktop app (level1_demo.py) and, later, the web path (plan 15 §3.4).

- load_level1_config(path): configs/level1_realtime.json -> validated parameters (no default value in code).

No GUI, no thread, no camera.
"""
import hashlib
import json
import numbers
import os
from typing import Any, Dict

# key -> (kind, check); kind: "number" | "int" | "str" | "str_list"
CONFIG_SPEC = {
    "motion_window_ms": ("number", "positive"),
    "still_speed": ("number", "positive"),
    "move_over_still_ratio": ("number", "above_one"),
    "move_speed": ("number", "positive"),
    "hold_ms_design": ("number", "positive"),
    "hold_ms": ("number", "positive"),
    "rearm_move_ms": ("number", "positive"),
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
    elif kind == "str":
        if not isinstance(value, str):
            raise ValueError(f"config {key}: value must be a string, got {value!r}")
        if check == "camera_api" and value not in CAMERA_APIS:
            raise ValueError(f"config {key}: value must be one of {CAMERA_APIS}, got {value!r}")
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
