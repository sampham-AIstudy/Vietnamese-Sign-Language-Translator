"""
Real-Time Landmark Extractor for Vietnamese Sign Language Recognition (Phase 10).
Extracts 67 landmarks (Pose Upper Body 0..24, Left Hand 25..45, Right Hand 46..66)
from webcam or video stream frames using MediaPipe Holistic.

Design Principles:
- Strictly conforms to Phase 0.5/Phase 1 67-joint schema.
- Missing landmarks are marked with np.nan and visibility = 0.0 (NO ZERO-FILL).
- Provides optional skeletal overlay visualization for OpenCV GUI preview.
"""

import os
import contextlib
import cv2
import numpy as np
import mediapipe as mp
from typing import Tuple, Dict, Any, Optional


@contextlib.contextmanager
def _suppress_c_stderr():
    """Temporarily suppresses C-level stderr output to eliminate MediaPipe/TFLite C++ warnings."""
    try:
        null_fd = os.open(os.devnull, os.O_RDWR)
        save_stderr = os.dup(2)
        os.dup2(null_fd, 2)
        os.close(null_fd)
        yield
    except Exception:
        yield
    finally:
        try:
            os.dup2(save_stderr, 2)
            os.close(save_stderr)
        except Exception:
            pass


class RealtimeLandmarkExtractor:
    """
    High-performance single-frame landmark extractor powered by MediaPipe Holistic.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity

        self.mp_holistic = mp.solutions.holistic
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        with _suppress_c_stderr():
            self.holistic = self.mp_holistic.Holistic(
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                model_complexity=self.model_complexity,
                static_image_mode=False,
            )
            # Warm up subgraphs (pose, face, hands) to compile delegates inside suppression context
            dummy = np.zeros((256, 256, 3), dtype=np.uint8)
            self.holistic.process(dummy)

    def extract(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Any]:
        """
        Extracts 67 landmarks from an OpenCV BGR frame.

        Args:
            frame_bgr: NumPy array [H, W, 3] in BGR color space.

        Returns:
            coords: [67, 3] float32 array (x, y, z). Missing joints are np.nan.
            visibility: [67] float32 array (1.0 = present, 0.0 = missing).
            results: Raw MediaPipe Holistic results object (for visualization).
        """
        # MediaPipe expects RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        results = self.holistic.process(frame_rgb)
        frame_rgb.flags.writeable = True

        coords = np.full((67, 3), np.nan, dtype=np.float32)
        visibility = np.zeros(67, dtype=np.float32)

        # 1. Pose Upper Body (0..24)
        if results.pose_landmarks:
            for idx in range(min(25, len(results.pose_landmarks.landmark))):
                lm = results.pose_landmarks.landmark[idx]
                coords[idx] = [lm.x, lm.y, lm.z]
                vis = getattr(lm, "visibility", 1.0)
                visibility[idx] = 1.0 if vis > 0.2 else 0.0

        # 2. Left Hand (local 0..20 -> global 25..45)
        if results.left_hand_landmarks:
            for idx, lm in enumerate(results.left_hand_landmarks.landmark):
                if idx < 21:
                    global_idx = 25 + idx
                    coords[global_idx] = [lm.x, lm.y, lm.z]
                    visibility[global_idx] = 1.0

        # 3. Right Hand (local 0..20 -> global 46..66)
        if results.right_hand_landmarks:
            for idx, lm in enumerate(results.right_hand_landmarks.landmark):
                if idx < 21:
                    global_idx = 46 + idx
                    coords[global_idx] = [lm.x, lm.y, lm.z]
                    visibility[global_idx] = 1.0

        return coords, visibility, results

    def draw_landmarks(self, frame_bgr: np.ndarray, results: Any) -> np.ndarray:
        """
        Renders elegant skeleton keypoint and bone connections onto the frame.
        """
        if results is None:
            return frame_bgr

        annotated = frame_bgr.copy()

        # Pose connections (upper body only)
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated,
                results.pose_landmarks,
                self.mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
            )

        # Left Hand
        if results.left_hand_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated,
                results.left_hand_landmarks,
                self.mp_holistic.HAND_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=3),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(121, 44, 250), thickness=2, circle_radius=2),
            )

        # Right Hand
        if results.right_hand_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated,
                results.right_hand_landmarks,
                self.mp_holistic.HAND_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=3),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2),
            )

        return annotated

    def close(self):
        """Releases underlying MediaPipe graph resources."""
        if self.holistic is not None:
            self.holistic.close()
            self.holistic = None
