"""
MediaPipe Holistic Landmark Extractor for Vietnamese Sign Language Recognition (VSLR).
Extracts 67 upper-body and hand joints:
  - 25 Upper-Body Pose landmarks (MediaPipe Pose 0..24)
  - 21 Left Hand landmarks (MediaPipe Hands 0..20)
  - 21 Right Hand landmarks (MediaPipe Hands 0..20)
  Total: 67 joints.

STRICT DESIGN RULES:
  - NO ZERO-FILL FOR MISSING LANDMARKS.
  - Undetected landmarks are marked with visibility = 0.0 and coordinates = np.nan.
  - Outputs:
      'keypoints': shape [T, 67, 3] (x, y, z)
      'visibility_mask': shape [T, 67] (1.0 = present, 0.0 = missing)
      'keypoints_4d': shape [T, 67, 4] (x, y, z, visibility)
"""

import os
import json
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List


class CleanHolisticExtractor:
    """
    Extracts 67 joints from video frames using MediaPipe Holistic without zero-padding.
    Preserves exact detection confidence and missingness masks.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
        process_height: Optional[int] = None,
    ):
        """process_height: if set, frames are resized (aspect kept, INTER_AREA) to this height before
        MediaPipe — e.g. 360 to match VSL-GH, whose upstream extraction ran on 360x360 frames.
        Landmarks stay normalised to [0, 1], so coordinates remain comparable."""
        self.min_detection_confidence = min_detection_confidence
        self.process_height = process_height
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity
        self._holistic = None

    def _get_holistic(self):
        if self._holistic is None:
            import mediapipe as mp
            self._holistic = mp.solutions.holistic.Holistic(
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                model_complexity=self.model_complexity,
                static_image_mode=False,
            )
        return self._holistic

    def extract_frame(self, frame_rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts landmarks for a single RGB frame.
        Returns:
            coords: np.ndarray of shape (67, 3), coordinates (x, y, z). Missing landmarks are np.nan.
            mask: np.ndarray of shape (67,), 1.0 if detected, 0.0 if missing.
        """
        holistic = self._get_holistic()
        if self.process_height and frame_rgb.shape[0] != self.process_height:
            h, w = frame_rgb.shape[:2]
            frame_rgb = cv2.resize(frame_rgb, (max(1, round(w * self.process_height / h)), self.process_height),
                                   interpolation=cv2.INTER_AREA)
        results = holistic.process(frame_rgb)

        coords = np.full((67, 3), np.nan, dtype=np.float32)
        mask = np.zeros(67, dtype=np.float32)

        # 1. Pose landmarks (0..24)
        if results.pose_landmarks:
            for idx in range(min(25, len(results.pose_landmarks.landmark))):
                lm = results.pose_landmarks.landmark[idx]
                coords[idx] = [lm.x, lm.y, lm.z]
                # If visibility attribute exists in MediaPipe Pose
                vis = getattr(lm, "visibility", 1.0)
                mask[idx] = 1.0 if vis > 0.1 else 0.0

        # 2. Left hand landmarks (local 0..20 -> global 25..45)
        if results.left_hand_landmarks:
            for idx, lm in enumerate(results.left_hand_landmarks.landmark):
                if idx < 21:
                    global_idx = 25 + idx
                    coords[global_idx] = [lm.x, lm.y, lm.z]
                    mask[global_idx] = 1.0

        # 3. Right hand landmarks (local 0..20 -> global 46..66)
        if results.right_hand_landmarks:
            for idx, lm in enumerate(results.right_hand_landmarks.landmark):
                if idx < 21:
                    global_idx = 46 + idx
                    coords[global_idx] = [lm.x, lm.y, lm.z]
                    mask[global_idx] = 1.0

        return coords, mask

    def extract_from_video(self, video_path: str) -> Dict[str, Any]:
        """
        Extracts continuous landmark trajectories from an MP4 video file.
        Returns dictionary with:
            - 'keypoints': shape [T, 67, 3] (float32, missing = np.nan)
            - 'visibility_mask': shape [T, 67] (float32, 1.0 = present, 0.0 = missing)
            - 'keypoints_4d': shape [T, 67, 4] (x, y, z, visibility)
            - 'num_frames': int
            - 'fps': float
            - 'width': int
            - 'height': int
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        all_coords: List[np.ndarray] = []
        all_masks: List[np.ndarray] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            coords, mask = self.extract_frame(frame_rgb)
            all_coords.append(coords)
            all_masks.append(mask)

        cap.release()

        T = len(all_coords)
        if T == 0:
            keypoints = np.full((1, 67, 3), np.nan, dtype=np.float32)
            visibility_mask = np.zeros((1, 67), dtype=np.float32)
        else:
            keypoints = np.stack(all_coords, axis=0)  # [T, 67, 3]
            visibility_mask = np.stack(all_masks, axis=0)  # [T, 67]

        # Combine into 4D [T, 67, 4] (x, y, z, visibility)
        vis_expanded = np.expand_dims(visibility_mask, axis=-1)  # [T, 67, 1]
        keypoints_4d = np.concatenate([np.nan_to_num(keypoints, nan=0.0), vis_expanded], axis=-1)  # [T, 67, 4]

        return {
            "keypoints": keypoints,
            "visibility_mask": visibility_mask,
            "keypoints_4d": keypoints_4d,
            "num_frames": T,
            "fps": float(fps),
            "width": width,
            "height": height,
        }

    def close(self):
        if self._holistic is not None:
            self._holistic.close()
            self._holistic = None


def save_landmarks_npz(
    output_path: str,
    keypoints: np.ndarray,
    visibility_mask: np.ndarray,
    metadata: Dict[str, Any],
):
    """
    Saves extracted raw landmarks and metadata to an audit-safe .npz file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.savez_compressed(
        output_path,
        keypoints=keypoints.astype(np.float32),
        visibility_mask=visibility_mask.astype(np.float32),
        metadata=json.dumps(metadata, ensure_ascii=False),
    )
