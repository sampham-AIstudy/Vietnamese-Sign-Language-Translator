"""
Sequence Generator & Temporal Utilities for VSLR:
Handles variable sequence lengths, temporal masking, sliding windows, and uniform sampling.
Preserves strict temporal ordering and outputs explicit valid-frame masks.
"""

import numpy as np
from typing import Tuple, List, Optional, Dict, Any


class SequenceGenerator:
    """
    Utilities for managing temporal sequences of skeleton keypoints [T, V, C].
    """

    def __init__(
        self,
        default_target_len: int = 60,
        pad_mode: str = "zero",  # "zero" or "edge"
    ):
        self.default_target_len = default_target_len
        self.pad_mode = pad_mode

    @staticmethod
    def pad_or_crop_sequence(
        keypoints: np.ndarray,
        visibility_mask: np.ndarray,
        target_len: int = 60,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Pads or crops a sequence [T, V, C] and visibility [T, V] to fixed target_len.
        Generates temporal frame_mask [target_len] where 1.0 = valid frame, 0.0 = padded frame.

        Returns:
            padded_keypoints: [target_len, V, C]
            padded_vis_mask: [target_len, V]
            frame_mask: [target_len] (temporal presence mask)
        """
        T, V, C = keypoints.shape
        if T == target_len:
            frame_mask = np.ones(target_len, dtype=np.float32)
            return keypoints.copy(), visibility_mask.copy(), frame_mask

        if T > target_len:
            # Crop to target_len (uniform temporal subsampling)
            indices = np.linspace(0, T - 1, target_len).astype(int)
            sub_kps = keypoints[indices]
            sub_vis = visibility_mask[indices]
            frame_mask = np.ones(target_len, dtype=np.float32)
            return sub_kps, sub_vis, frame_mask

        # T < target_len -> Pad
        padded_kps = np.zeros((target_len, V, C), dtype=np.float32)
        padded_vis = np.zeros((target_len, V), dtype=np.float32)
        frame_mask = np.zeros(target_len, dtype=np.float32)

        padded_kps[:T] = keypoints
        padded_vis[:T] = visibility_mask
        frame_mask[:T] = 1.0

        return padded_kps, padded_vis, frame_mask

    @staticmethod
    def generate_sliding_windows(
        keypoints: np.ndarray,
        visibility_mask: np.ndarray,
        window_size: int = 60,
        stride: int = 30,
        min_frames: int = 20,
    ) -> List[Dict[str, np.ndarray]]:
        """
        Slices a long keypoint sequence into overlapping temporal windows.
        Returns list of window dicts:
            [{'keypoints': [window_size, V, C], 'visibility_mask': [window_size, V], 'frame_mask': [window_size]}]
        """
        T, V, C = keypoints.shape
        if T < min_frames:
            return []

        if T <= window_size:
            # Single padded window
            pk, pv, fm = SequenceGenerator.pad_or_crop_sequence(keypoints, visibility_mask, window_size)
            return [{"keypoints": pk, "visibility_mask": pv, "frame_mask": fm}]

        windows = []
        start = 0
        while start + window_size <= T:
            w_kps = keypoints[start : start + window_size]
            w_vis = visibility_mask[start : start + window_size]
            fm = np.ones(window_size, dtype=np.float32)
            windows.append({"keypoints": w_kps, "visibility_mask": w_vis, "frame_mask": fm})
            start += stride

        # If remainder frames > min_frames, add trailing window
        if start < T and (T - start) >= min_frames:
            w_kps = keypoints[T - window_size : T]
            w_vis = visibility_mask[T - window_size : T]
            fm = np.ones(window_size, dtype=np.float32)
            windows.append({"keypoints": w_kps, "visibility_mask": w_vis, "frame_mask": fm})

        return windows

    @staticmethod
    def uniform_resample(
        keypoints: np.ndarray,
        visibility_mask: np.ndarray,
        target_len: int = 60,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Linearly interpolates sequence to exactly target_len along temporal axis.
        """
        T, V, C = keypoints.shape
        if T == target_len:
            return keypoints.copy(), visibility_mask.copy()

        src_indices = np.arange(T)
        target_indices = np.linspace(0, T - 1, target_len)

        # Handle NaNs: replace nan with 0 for interp, interpolate mask separately
        nan_mask = np.isnan(keypoints)
        clean_kps = np.nan_to_num(keypoints, nan=0.0)

        resampled_kps = np.zeros((target_len, V, C), dtype=np.float32)
        resampled_vis = np.zeros((target_len, V), dtype=np.float32)

        for v in range(V):
            for c in range(C):
                resampled_kps[:, v, c] = np.interp(target_indices, src_indices, clean_kps[:, v, c])
            resampled_vis[:, v] = np.interp(target_indices, src_indices, visibility_mask[:, v])

        # Restore NaNs where visibility is 0
        resampled_kps[resampled_vis < 0.1] = np.nan

        return resampled_kps, resampled_vis
