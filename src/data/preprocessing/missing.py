"""
Missing Landmark Imputation & Mask Generation for VSLR:
- Strictly handles missing landmarks without naive zero-filling before masking.
- Uses linear temporal interpolation for gaps between valid frames.
- Forward-fills leading missing frames and backward-fills trailing missing frames.
- If a joint is permanently absent throughout the video (e.g. inactive hand),
  it is safely anchored and explicitly marked as joint_mask = 0.0.
"""

import numpy as np
from typing import Tuple


def handle_missing_landmarks(
    keypoints: np.ndarray,
    visibility: np.ndarray,
    vis_threshold: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Interpolates missing landmarks and generates an explicit validity mask.

    Args:
        keypoints: np.ndarray of shape [T, V, C] (e.g. [T, 67, 3]), may contain NaNs.
        visibility: np.ndarray of shape [T, V] (1.0 = detected, 0.0 = undetected).
        vis_threshold: Threshold above which a landmark is considered detected.

    Returns:
        clean_keypoints: np.ndarray of shape [T, V, C], guaranteed no NaNs or Infs.
        joint_mask: np.ndarray of shape [T, V], float32 (1.0 = valid/interpolated, 0.0 = permanently missing).
    """
    T, V, C = keypoints.shape
    clean_kps = keypoints.copy()
    joint_mask = np.zeros((T, V), dtype=np.float32)

    # Pose wrist anchors for fallback: Joint 15 (Pose Left Wrist), Joint 16 (Pose Right Wrist)
    POSE_LW_IDX = 15
    POSE_RW_IDX = 16

    for v in range(V):
        # A frame is valid if visibility > threshold and coordinates are not NaN
        valid_indices = np.where(
            (visibility[:, v] > vis_threshold) & (~np.isnan(clean_kps[:, v, 0]))
        )[0]

        if len(valid_indices) == 0:
            # Joint is permanently missing across entire video sequence
            joint_mask[:, v] = 0.0

            # Safe physical anchor instead of arbitrary zero:
            # If joint belongs to left hand (25..45), anchor to pose left wrist if available
            if 25 <= v <= 45 and not np.isnan(clean_kps[:, POSE_LW_IDX, 0]).all():
                for c in range(C):
                    clean_kps[:, v, c] = np.nan_to_num(clean_kps[:, POSE_LW_IDX, c], nan=0.0)
            # If joint belongs to right hand (46..66), anchor to pose right wrist if available
            elif 46 <= v <= 66 and not np.isnan(clean_kps[:, POSE_RW_IDX, 0]).all():
                for c in range(C):
                    clean_kps[:, v, c] = np.nan_to_num(clean_kps[:, POSE_RW_IDX, c], nan=0.0)
            else:
                clean_kps[:, v, :] = 0.0
            continue

        # Joint has at least one valid detection
        joint_mask[:, v] = 1.0
        first_valid = valid_indices[0]
        last_valid = valid_indices[-1]

        # 1. Forward-fill leading missing frames (0 to first_valid - 1)
        if first_valid > 0:
            for c in range(C):
                clean_kps[:first_valid, v, c] = clean_kps[first_valid, v, c]

        # 2. Backward-fill trailing missing frames (last_valid + 1 to T - 1)
        if last_valid < T - 1:
            for c in range(C):
                clean_kps[last_valid + 1 :, v, c] = clean_kps[last_valid, v, c]

        # 3. Linear interpolation for intermediate gaps
        if len(valid_indices) > 1:
            time_steps = np.arange(T)
            for c in range(C):
                valid_coords = clean_kps[valid_indices, v, c]
                clean_kps[:, v, c] = np.interp(
                    time_steps,
                    valid_indices,
                    valid_coords,
                )

    # Final guard: guarantee no remaining NaNs or Infs
    clean_kps = np.nan_to_num(clean_kps, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    return clean_kps, joint_mask
