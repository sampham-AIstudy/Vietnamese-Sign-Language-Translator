"""
Shared Preprocessing and Feature Extraction for VSL Alphabet (Level 1).
Provides:
1. normalize_hand_landmarks: Wrist-centered, palm-scale normalized 21 landmarks.
2. extract_static_features: Stable keyframe/median aggregation for Static MLP (63 dims).
3. extract_sequence_features: Resampled temporal sequence for 1D-CNN / BiGRU (T, 63).
4. Realtime single-frame preprocessing matching offline training pipeline exactly.
"""

import numpy as np
import torch
from typing import Optional, Tuple, Union, Dict, Any

# Landmark Indices for MediaPipe Hand
WRIST_IDX = 0
INDEX_MCP_IDX = 5
MIDDLE_MCP_IDX = 9
PINKY_MCP_IDX = 17
EPS = 1e-6


def normalize_hand_landmarks(landmarks: np.ndarray) -> np.ndarray:
    """
    Normalizes 21 3D hand landmarks to be translation- and scale-invariant.
    
    Args:
        landmarks: Array of shape (21, 3) or (..., 21, 3).
    Returns:
        Normalized array of the same shape, with wrist at (0, 0, 0)
        and scaled such that palm length (wrist to middle MCP) is 1.0.
    """
    landmarks = np.asarray(landmarks, dtype=np.float32)
    # Check if empty/all zeros
    if np.all(landmarks == 0):
        return np.zeros_like(landmarks)

    # Wrist position
    wrist = landmarks[..., WRIST_IDX:WRIST_IDX + 1, :]  # (..., 1, 3)
    centered = landmarks - wrist

    # Middle finger MCP position relative to wrist
    middle_mcp = centered[..., MIDDLE_MCP_IDX:MIDDLE_MCP_IDX + 1, :]
    palm_scale = np.linalg.norm(middle_mcp, axis=-1, keepdims=True)  # (..., 1, 1)

    # Fallback to index MCP or overall max norm if palm_scale is degenerate
    if np.any(palm_scale < EPS):
        index_mcp = centered[..., INDEX_MCP_IDX:INDEX_MCP_IDX + 1, :]
        palm_scale = np.linalg.norm(index_mcp, axis=-1, keepdims=True)
        if np.any(palm_scale < EPS):
            max_norm = np.max(np.linalg.norm(centered, axis=-1, keepdims=True), axis=-2, keepdims=True)
            palm_scale = np.where(max_norm < EPS, 1.0, max_norm)

    normalized = centered / np.clip(palm_scale, EPS, None)
    return normalized


def is_valid_frame(frame_landmarks: np.ndarray) -> bool:
    """Check if hand frame has valid detected keypoints (not all zeros or NaNs)."""
    if frame_landmarks is None or np.isnan(frame_landmarks).any():
        return False
    return not np.all(frame_landmarks == 0)


def extract_static_features(
    sequence: np.ndarray,
    hold_start: int = 30,
    hold_end: int = 90,
    strategy: str = "median",
) -> np.ndarray:
    """
    Extracts a single representative 63-dimensional feature vector for Static MLP.

    Args:
        sequence: Array of shape (T, 21, 3).
        hold_start: Starting frame index of stable hold segment.
        hold_end: Ending frame index of stable hold segment.
        strategy: 'median', 'mean', or 'center_frame'.
    Returns:
        Flattened 1D array of shape (63,) with normalized coordinates.
    """
    T = sequence.shape[0]
    start = max(0, min(hold_start, T - 1))
    end = max(start + 1, min(hold_end, T))

    hold_segment = sequence[start:end]  # (N, 21, 3)

    # Filter out empty/untracked frames in the hold window
    valid_mask = [is_valid_frame(f) for f in hold_segment]
    if any(valid_mask):
        valid_frames = hold_segment[valid_mask]
    else:
        # Fallback to all valid frames in sequence
        all_valid = [is_valid_frame(f) for f in sequence]
        valid_frames = sequence[all_valid] if any(all_valid) else sequence

    if len(valid_frames) == 0:
        return np.zeros(63, dtype=np.float32)

    if strategy == "median":
        rep_frame = np.median(valid_frames, axis=0)  # (21, 3)
    elif strategy == "mean":
        rep_frame = np.mean(valid_frames, axis=0)
    elif strategy == "center_frame":
        mid_idx = len(valid_frames) // 2
        rep_frame = valid_frames[mid_idx]
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    norm_frame = normalize_hand_landmarks(rep_frame)
    return norm_frame.reshape(-1).astype(np.float32)  # (63,)


def extract_sequence_features(
    sequence: np.ndarray,
    target_frames: int = 30,
    hold_start: int = 30,
    hold_end: int = 90,
) -> np.ndarray:
    """
    Extracts resampled normalized sequence for 1D-CNN or BiGRU.

    Args:
        sequence: Array of shape (T, 21, 3).
        target_frames: Number of output frames (default 30).
        hold_start: Hold start frame.
        hold_end: Hold end frame.
    Returns:
        Array of shape (target_frames, 63).
    """
    T = sequence.shape[0]
    start = max(0, min(hold_start, T - 1))
    end = max(start + 1, min(hold_end, T))
    segment = sequence[start:end]

    valid_mask = [is_valid_frame(f) for f in segment]
    if any(valid_mask):
        valid_frames = segment[valid_mask]
    else:
        all_valid = [is_valid_frame(f) for f in sequence]
        valid_frames = sequence[all_valid] if any(all_valid) else segment

    N = len(valid_frames)
    if N == 0:
        return np.zeros((target_frames, 63), dtype=np.float32)

    # Uniform resampling to target_frames
    indices = np.linspace(0, N - 1, target_frames).round().astype(int)
    sampled = valid_frames[indices]  # (target_frames, 21, 3)

    norm_sampled = normalize_hand_landmarks(sampled)  # (target_frames, 21, 3)
    return norm_sampled.reshape(target_frames, -1).astype(np.float32)


def preprocess_realtime_frame(landmarks_21x3: np.ndarray) -> np.ndarray:
    """
    Processes a single frame of 21 (x, y, z) landmarks from live webcam MediaPipe.

    Args:
        landmarks_21x3: Array or list of shape (21, 3).
    Returns:
        Normalized feature vector of shape (63,).
    """
    arr = np.asarray(landmarks_21x3, dtype=np.float32).reshape(21, 3)
    norm = normalize_hand_landmarks(arr)
    return norm.reshape(-1).astype(np.float32)


# ---------------------------------------------------------------------------
# Real-data Level 1 features (shared by training and the live camera path)
# ---------------------------------------------------------------------------
def canonicalize_hand_sequence(
    raw_landmarks: np.ndarray,
    detected_mask: Optional[np.ndarray] = None,
    handedness_labels: Optional[np.ndarray] = None,
    aspect_ratio: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, bool]:
    """
    Makes one clip's hand landmarks comparable across cameras and signers.

    1. Aspect correction: MediaPipe divides x by frame width and y by height; x (and z, which
       MediaPipe expresses on the x scale) are multiplied by width/height so a 4:3 webcam and a
       16:9 dictionary clip give the same hand shape.
    2. Handedness: if the majority label over detected frames is 'Left', x is mirrored, so a
       left-handed signer produces the same features as a right-handed one. MediaPipe assumes a
       mirrored (selfie) image, so on the unmirrored frames the backend receives a right hand is
       labelled 'Left' and gets mirrored; a left hand is labelled 'Right' and is not. Both end in
       the same canonical form as long as training and inference use unmirrored frames.

    Args:
        raw_landmarks: [T, 21, 3] MediaPipe image coordinates (zeros where no hand).
        detected_mask: [T] bool; derived from non-zero frames when None.
        handedness_labels: [T] 'Left'/'Right'/'' per frame (MediaPipe labels on unmirrored frames).
        aspect_ratio: frame width / height, or None to skip.
    Returns:
        (landmarks [T,21,3] float32, detected [T] bool, mirrored flag)
    """
    lms = np.array(raw_landmarks, dtype=np.float32, copy=True)
    if detected_mask is None:
        detected = np.array([is_valid_frame(f) for f in lms], dtype=bool)
    else:
        detected = np.asarray(detected_mask, dtype=bool).copy()
    if aspect_ratio is not None:
        lms[..., 0] *= aspect_ratio
        lms[..., 2] *= aspect_ratio
    mirrored = False
    if handedness_labels is not None and detected.any():
        labels = [str(l) for l, d in zip(handedness_labels, detected) if d]
        mirrored = labels.count("Left") > labels.count("Right")
    if mirrored:
        lms[..., 0] = -lms[..., 0]
    lms[~detected] = 0.0
    return lms, detected, mirrored


def sequence_features_from_clip(
    landmarks: np.ndarray,
    detected: np.ndarray,
    target_frames: int = 30,
) -> np.ndarray:
    """
    [T,21,3] canonical landmarks -> [target_frames, 63] palm-normalised features, resampled
    uniformly over the frames where a hand was detected (whole clip; no hold window needed).
    """
    frames = landmarks[detected]
    if len(frames) == 0:
        return np.zeros((target_frames, 63), dtype=np.float32)
    idx = np.linspace(0, len(frames) - 1, target_frames).round().astype(int)
    return normalize_hand_landmarks(frames[idx]).reshape(target_frames, -1).astype(np.float32)
