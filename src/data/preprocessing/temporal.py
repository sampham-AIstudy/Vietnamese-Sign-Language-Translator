"""
Temporal Resizing & Masking for VSLR Skeleton Sequences:
- Resizes variable length sequence [T, 67, 3] to fixed target length (e.g. 60 frames).
- Resizes joint_mask [T, 67] using nearest-neighbor indexing to strictly preserve binary {0, 1} values.
- Generates temporal_mask [target_len] (1.0 = valid frame, 0.0 = padded frame).
"""

import numpy as np
from typing import Tuple


class TemporalProcessor:
    """
    Standardizes sequence length across variable video durations.
    """

    def __init__(self, target_len: int = 60, mode: str = "pad"):
        """
        Args:
            target_len: Target sequence length (default: 60 frames).
            mode: "pad" (pads with zeros and masks) or "interpolate" (stretches short sequences).
        """
        self.target_len = target_len
        self.mode = mode

    def process(
        self,
        keypoints: np.ndarray,
        joint_mask: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Resizes keypoints and masks to [target_len].

        Args:
            keypoints: [T, 67, 3] float32
            joint_mask: [T, 67] float32

        Returns:
            resized_kps: [target_len, 67, 3] float32
            resized_joint_mask: [target_len, 67] float32 (values in {0.0, 1.0})
            temporal_mask: [target_len] float32 (1.0 = valid frame, 0.0 = padding)
        """
        T, V, C = keypoints.shape
        L = self.target_len

        # Case 1: Exact length match
        if T == L:
            return (
                keypoints.copy().astype(np.float32),
                joint_mask.copy().astype(np.float32),
                np.ones(L, dtype=np.float32),
            )

        # Case 2: Sequence longer than target_len -> Uniform temporal sampling
        if T > L:
            indices = np.linspace(0, T - 1, L).astype(int)
            resized_kps = keypoints[indices].astype(np.float32)
            # Nearest-neighbor ensures joint_mask remains exactly {0.0, 1.0}
            resized_joint_mask = joint_mask[indices].astype(np.float32)
            temporal_mask = np.ones(L, dtype=np.float32)
            return resized_kps, resized_joint_mask, temporal_mask

        # Case 3: Sequence shorter than target_len (T < L)
        if self.mode == "interpolate":
            # Linear interpolation for keypoints, nearest neighbor for joint mask
            src_t = np.arange(T)
            target_t = np.linspace(0, T - 1, L)
            resized_kps = np.zeros((L, V, C), dtype=np.float32)
            for v in range(V):
                for c in range(C):
                    resized_kps[:, v, c] = np.interp(target_t, src_t, keypoints[:, v, c])

            nn_indices = np.round(target_t).astype(int)
            resized_joint_mask = joint_mask[nn_indices].astype(np.float32)
            temporal_mask = np.ones(L, dtype=np.float32)
            return resized_kps, resized_joint_mask, temporal_mask
        else:
            # Default "pad" mode: Pad with zeros and mark temporal_mask
            padded_kps = np.zeros((L, V, C), dtype=np.float32)
            padded_joint_mask = np.zeros((L, V), dtype=np.float32)
            temporal_mask = np.zeros(L, dtype=np.float32)

            padded_kps[:T] = keypoints
            padded_joint_mask[:T] = joint_mask
            temporal_mask[:T] = 1.0

            return padded_kps, padded_joint_mask, temporal_mask
