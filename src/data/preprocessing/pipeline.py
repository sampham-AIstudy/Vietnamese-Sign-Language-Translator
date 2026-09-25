"""
Master Preprocessing Pipeline for VSLR:
Integrates:
1. Missing landmark interpolation (missing.py)
2. Spatial translation and scale normalization (spatial.py)
3. Temporal resizing and mask generation (temporal.py)
"""

import numpy as np
from typing import Tuple, Dict, Any, Optional

from src.data.preprocessing.missing import handle_missing_landmarks
from src.data.preprocessing.spatial import SpatialNormalizer
from src.data.preprocessing.temporal import TemporalProcessor


def correct_aspect(keypoints: np.ndarray, aspect_ratio: float) -> np.ndarray:
    """Rescales MediaPipe x (and z, which MediaPipe expresses on the x scale) by width/height."""
    if not np.isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError(f"aspect_ratio must be a positive finite number, got {aspect_ratio}")
    out = np.array(keypoints, dtype=np.float32, copy=True)
    out[..., 0] *= aspect_ratio
    out[..., 2] *= aspect_ratio
    return out


class VSLPreprocessingPipeline:
    """
    End-to-end preprocessing pipeline for a single raw sign language sequence.
    """

    def __init__(
        self,
        target_len: int = 60,
        vis_threshold: float = 0.5,
        center_mode: str = "mid_shoulder",
        scale_mode: str = "shoulder_width",
        temporal_mode: str = "pad",
    ):
        self.vis_threshold = vis_threshold
        self.spatial_normalizer = SpatialNormalizer(
            center_mode=center_mode,
            scale_mode=scale_mode,
        )
        self.temporal_processor = TemporalProcessor(
            target_len=target_len,
            mode=temporal_mode,
        )

    def __call__(
        self,
        raw_keypoints: np.ndarray,
        visibility: np.ndarray,
        aspect_ratio: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Processes raw extracted keypoints into clean normalized tensors.

        Args:
            raw_keypoints: [T, 67, 3] float32 (may contain NaNs)
            visibility: [T, 67] float32
            aspect_ratio: source frame width / height. MediaPipe divides x by width and y by
                height, so the same hand looks narrower in a 16:9 clip than on a 4:3 webcam.
                When given, x and z are multiplied by it so all axes are in frame-height units.
                None keeps the legacy (uncorrected) behaviour that existing checkpoints expect.

        Returns:
            sequence: [target_len, 67, 3] float32 (normalized, zero NaNs/Infs)
            joint_mask: [target_len, 67] float32 ({0.0, 1.0})
            temporal_mask: [target_len] float32 ({0.0, 1.0})
        """
        if aspect_ratio is not None:
            raw_keypoints = correct_aspect(raw_keypoints, aspect_ratio)

        # Step 1: Missing landmark temporal interpolation & joint presence mask
        clean_kps, joint_mask = handle_missing_landmarks(
            raw_keypoints,
            visibility,
            vis_threshold=self.vis_threshold,
        )

        # Step 2: Robust spatial translation & scale normalization
        norm_kps = self.spatial_normalizer.normalize(
            clean_kps,
            joint_mask,
        )

        # Step 3: Temporal standardization & temporal mask generation
        final_kps, final_joint_mask, temporal_mask = self.temporal_processor.process(
            norm_kps,
            joint_mask,
        )

        return final_kps, final_joint_mask, temporal_mask
