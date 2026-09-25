"""
Spatial Normalization for VSLR Skeleton Sequences:
- Provides Translation & Scale Invariance.
- Centers coordinates relative to mid-shoulder (fallback to individual shoulder, mid-hip, nose).
- Scales coordinates relative to sequence-level shoulder width (fallback to torso height, bbox, or 1.0).
- Guarantees strictly NO NaN or Inf in the normalized output.
"""

import numpy as np
from typing import Tuple, Optional


class SpatialNormalizer:
    """
    Normalizes 67-joint skeleton sequences for translation and scale invariance.
    """

    # Anatomical index anchors in the 67-joint schema
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24

    def __init__(
        self,
        center_mode: str = "mid_shoulder",  # "mid_shoulder", "mid_hip", "nose"
        scale_mode: str = "shoulder_width",  # "shoulder_width", "torso_height", "bbox"
        eps: float = 1e-5,
    ):
        self.center_mode = center_mode
        self.scale_mode = scale_mode
        self.eps = eps

    def get_frame_center(
        self,
        frame_kps: np.ndarray,
        frame_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Determines the translation center anchor for a single frame [67, 3].
        Returns [3] translation vector.
        """
        ls_valid = frame_mask[self.LEFT_SHOULDER] > 0.5
        rs_valid = frame_mask[self.RIGHT_SHOULDER] > 0.5

        if ls_valid and rs_valid:
            # Primary: Mid-shoulder center
            return 0.5 * (frame_kps[self.LEFT_SHOULDER] + frame_kps[self.RIGHT_SHOULDER])
        elif ls_valid:
            # Fallback 1a: Left shoulder
            return frame_kps[self.LEFT_SHOULDER].copy()
        elif rs_valid:
            # Fallback 1b: Right shoulder
            return frame_kps[self.RIGHT_SHOULDER].copy()

        # Fallback 2: Mid-hip or individual hip
        lh_valid = frame_mask[self.LEFT_HIP] > 0.5
        rh_valid = frame_mask[self.RIGHT_HIP] > 0.5
        if lh_valid and rh_valid:
            return 0.5 * (frame_kps[self.LEFT_HIP] + frame_kps[self.RIGHT_HIP])
        elif lh_valid:
            return frame_kps[self.LEFT_HIP].copy()
        elif rh_valid:
            return frame_kps[self.RIGHT_HIP].copy()

        # Fallback 3: Nose
        if frame_mask[self.NOSE] > 0.5:
            return frame_kps[self.NOSE].copy()

        # Fallback 4: Mean of all valid joints in frame
        valid_idx = np.where(frame_mask > 0.5)[0]
        if len(valid_idx) > 0:
            return np.mean(frame_kps[valid_idx], axis=0)

        # Extreme Fallback 5: No valid joints -> origin (0, 0, 0)
        return np.zeros(3, dtype=np.float32)

    def compute_sequence_scale(
        self,
        keypoints: np.ndarray,
        joint_mask: np.ndarray,
    ) -> float:
        """
        Computes a stable, sequence-level scale factor based on median anatomical distance.
        Sequence-level scale avoids per-frame jitter and preserves relative motion velocity.
        """
        T = keypoints.shape[0]
        ls_idx = self.LEFT_SHOULDER
        rs_idx = self.RIGHT_SHOULDER
        lh_idx = self.LEFT_HIP
        rh_idx = self.RIGHT_HIP

        # 1. Primary: Shoulder width $\|\mathbf{p}_{11} - \mathbf{p}_{12}\|_2$
        both_shoulders = (joint_mask[:, ls_idx] > 0.5) & (joint_mask[:, rs_idx] > 0.5)
        if np.any(both_shoulders):
            diffs = keypoints[both_shoulders, ls_idx] - keypoints[both_shoulders, rs_idx]
            dists = np.linalg.norm(diffs, axis=-1)
            med_dist = float(np.median(dists))
            if med_dist > self.eps:
                return med_dist

        # 2. Fallback 1: Torso height (Mid-shoulder to Mid-hip)
        torso_valid = (
            (joint_mask[:, ls_idx] > 0.5)
            & (joint_mask[:, rs_idx] > 0.5)
            & (joint_mask[:, lh_idx] > 0.5)
            & (joint_mask[:, rh_idx] > 0.5)
        )
        if np.any(torso_valid):
            mid_shoulders = 0.5 * (keypoints[torso_valid, ls_idx] + keypoints[torso_valid, rs_idx])
            mid_hips = 0.5 * (keypoints[torso_valid, lh_idx] + keypoints[torso_valid, rh_idx])
            t_dists = np.linalg.norm(mid_shoulders - mid_hips, axis=-1)
            med_torso = float(np.median(t_dists))
            if med_torso > self.eps:
                return med_torso

        # 3. Fallback 2: Bounding box span across valid joints
        valid_coords = keypoints[joint_mask > 0.5]
        if len(valid_coords) > 0:
            min_pt = np.min(valid_coords, axis=0)
            max_pt = np.max(valid_coords, axis=0)
            diag = float(np.linalg.norm(max_pt - min_pt))
            if diag > self.eps:
                return diag * 0.5

        # 4. Fallback 3: Unit scale (no scaling)
        return 1.0

    def normalize(
        self,
        keypoints: np.ndarray,
        joint_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Applies robust translation and scale normalization to [T, 67, 3].

        Returns:
            norm_kps: [T, 67, 3] float32, guaranteed zero NaNs and zero Infs.
        """
        T, V, C = keypoints.shape
        norm_kps = np.zeros_like(keypoints, dtype=np.float32)

        # 1. Translation: Center each frame around mid-shoulder
        for t in range(T):
            center = self.get_frame_center(keypoints[t], joint_mask[t])
            norm_kps[t] = keypoints[t] - center

        # 2. Scale: Divide by sequence-level anatomical scale
        scale = self.compute_sequence_scale(norm_kps, joint_mask)
        norm_kps = norm_kps / scale

        # 3. If a joint was permanently missing (mask == 0), ensure it stays exactly 0.0
        norm_kps[joint_mask == 0.0] = 0.0

        # 4. Final safety guard against NaNs/Infs
        norm_kps = np.nan_to_num(norm_kps, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        return norm_kps
