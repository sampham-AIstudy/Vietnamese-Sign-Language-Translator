"""
Real-Time Preprocessing & Inference Pipeline for Vietnamese Sign Language Recognition (Phase 10).
Bridges live camera video streams with trained deep neural network models.

Components:
1. Temporal Sliding Window Buffer (deque of length 60).
2. Phase 2 Preprocessing Pipeline (Spatial Normalization, Scale Centering, Missing Limbs Handling).
3. VSLPredictor Engine (ST-GCN / Transformer / Ensemble).
"""

import os
import sys
import collections
from typing import Dict, Any, Optional, Tuple

import cv2
import numpy as np
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.realtime_extractor import RealtimeLandmarkExtractor
from src.inference.predictor import VSLPredictor
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline


class RealtimePipeline:
    """
    End-to-end real-time inference manager:
    Camera Frame -> MediaPipe Extraction -> Temporal Buffer -> Normalization -> VSLPredictor
    """

    def __init__(
        self,
        predictor: Optional[VSLPredictor] = None,
        extractor: Optional[RealtimeLandmarkExtractor] = None,
        target_len: int = 60,
        min_frames: int = 20,
        infer_interval: int = 3,
        model_type: str = "stgcn",
        aspect_correct: Optional[bool] = None,
    ):
        """
        Args:
            predictor: Pre-initialized VSLPredictor instance.
            extractor: Pre-initialized RealtimeLandmarkExtractor instance.
            target_len: Target sequence length (fixed to 60 for trained models).
            min_frames: Minimum buffered frames before starting inference.
            infer_interval: Run inference every N frames (stride).
            model_type: Default model type if predictor is not supplied.
            aspect_correct: Rescale landmarks by the camera frame's width/height. None = follow the
                checkpoint (`preprocessing.aspect_correct`), so the live input matches training.
        """
        self.target_len = target_len
        self.min_frames = min_frames
        self.infer_interval = infer_interval

        # Extractor and Predictor
        self.extractor = extractor or RealtimeLandmarkExtractor()
        self.predictor = predictor or VSLPredictor(model_type=model_type)
        if aspect_correct is None:
            aspect_correct = bool(getattr(self.predictor, "preprocessing", {}).get("aspect_correct", False))
        self.aspect_correct = aspect_correct
        self.aspect_ratio: Optional[float] = None

        # Preprocessing pipeline adhering strictly to Phase 2/3/4 standards
        self.preprocessor = VSLPreprocessingPipeline(
            target_len=target_len,
            vis_threshold=0.5,
            center_mode="mid_shoulder",
            scale_mode="shoulder_width",
            temporal_mode="pad",
        )

        # Sliding window temporal buffers
        self.kps_buffer = collections.deque(maxlen=target_len)
        self.vis_buffer = collections.deque(maxlen=target_len)
        self.frame_count = 0
        self.last_prediction: Optional[Dict[str, Any]] = None

    def clear_buffer(self):
        """Resets sliding window buffer."""
        self.kps_buffer.clear()
        self.vis_buffer.clear()
        self.frame_count = 0
        self.last_prediction = None

    def process_frame(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Processes a single live camera frame through the full pipeline.

        Args:
            frame_bgr: BGR video frame from OpenCV.

        Returns:
            Dictionary with:
              - 'prediction': Latest VSLPredictor output dict (or None).
              - 'is_new_prediction': Boolean flag if prediction ran on this frame.
              - 'results': Raw MediaPipe results object for landmark rendering.
              - 'buffer_fill': Number of frames in buffer (0..60).
              - 'buffer_capacity': 60.
              - 'hand_detected': True if either hand is visible.
        """
        self.frame_count += 1
        if self.aspect_correct and frame_bgr is not None and frame_bgr.ndim >= 2 and frame_bgr.shape[0] > 0:
            self.aspect_ratio = frame_bgr.shape[1] / frame_bgr.shape[0]

        # 1. Landmark Extraction
        coords, vis, results = self.extractor.extract(frame_bgr)
        self.kps_buffer.append(coords)
        self.vis_buffer.append(vis)

        # Check hand presence (Left Hand: 25..45, Right Hand: 46..66)
        hand_detected = bool(np.any(vis[25:67] > 0.5))

        # Motion Energy calculation over recent hand frames to separate static poses from dynamic gestures
        motion_energy = 0.0
        is_moving = False
        if len(self.kps_buffer) >= 6 and hand_detected:
            recent_kps = np.array(list(self.kps_buffer)[-6:], dtype=np.float32)  # [6, 67, 3]
            hand_pts = recent_kps[:, 25:67, :2]  # [6, 42, 2]
            hand_clean = np.nan_to_num(hand_pts, nan=0.0)
            diffs = np.diff(hand_clean, axis=0)  # [5, 42, 2]
            motion_energy = float(np.mean(np.linalg.norm(diffs, axis=-1)))
            is_moving = bool(motion_energy >= 0.0035)

        buffer_fill = len(self.kps_buffer)
        is_new_prediction = False

        # 2. Trigger Inference if buffer has sufficient history and interval aligns
        if buffer_fill >= self.min_frames and (self.frame_count % self.infer_interval == 0):
            raw_kps = np.array(self.kps_buffer, dtype=np.float32)  # [T_curr, 67, 3]
            raw_vis = np.array(self.vis_buffer, dtype=np.float32)  # [T_curr, 67]

            # Step A: Apply full Phase 2 preprocessing
            seq, jm, tm = self.preprocessor(
                raw_kps, raw_vis, aspect_ratio=self.aspect_ratio if self.aspect_correct else None
            )

            # Step B: Model inference
            self.last_prediction = self.predictor.predict(
                sequence=seq,
                joint_mask=jm,
                temporal_mask=tm,
                top_k=5,
            )
            is_new_prediction = True

        return {
            "prediction": self.last_prediction,
            "is_new_prediction": is_new_prediction,
            "results": results,
            "buffer_fill": buffer_fill,
            "buffer_capacity": self.target_len,
            "hand_detected": hand_detected,
            "is_moving": is_moving,
            "motion_energy": motion_energy,
        }

    def close(self):
        """Releases underlying resources."""
        self.extractor.close()
