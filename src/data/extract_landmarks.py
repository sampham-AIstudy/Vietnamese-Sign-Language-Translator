"""
MediaPipe Landmark Extractor for Vietnamese Sign Language (VSL)
Extracts:
1. 201-dim sequences (T=60, D=201):
   - Upper body pose (landmarks 0..24, 25*3 = 75)
   - Left hand (21 landmarks * 3 = 63)
   - Right hand (21 landmarks * 3 = 63)
   Matches the preprocessed VSL dataset structure in `data (2)/Processed`.
2. 42-dim static hand keypoints (21 landmarks * 2 = 42):
   - Normalized relative to wrist (landmark 0)
   Matches `hand_data.csv` and Paper 2 (VSL Alphabet Recognition).
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class HolisticLandmarkExtractor:
    """Extracts 201-dim Holistic features from video frames or live camera feed."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        target_seq_len: int = 60,
    ):
        self.target_seq_len = target_seq_len
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._holistic = None

    def _get_holistic(self):
        if self._holistic is None:
            import mediapipe as mp
            self._holistic = mp.solutions.holistic.Holistic(
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                model_complexity=1,
            )
        return self._holistic

    def extract_frame_landmarks(self, frame_rgb: np.ndarray) -> np.ndarray:
        """
        Extract 201-dimensional feature vector for a single RGB frame:
        - 25 pose landmarks * 3 (x, y, z) = 75
        - 21 left hand landmarks * 3 (x, y, z) = 63
        - 21 right hand landmarks * 3 (x, y, z) = 63
        Total: 201 floats
        """
        holistic = self._get_holistic()
        results = holistic.process(frame_rgb)

        # 1. Pose landmarks (take first 25 upper body landmarks)
        pose = np.zeros((25, 3), dtype=np.float32)
        if results.pose_landmarks:
            for idx in range(min(25, len(results.pose_landmarks.landmark))):
                lm = results.pose_landmarks.landmark[idx]
                pose[idx] = [lm.x, lm.y, lm.z]

        # 2. Left hand landmarks (21 landmarks)
        lh = np.zeros((21, 3), dtype=np.float32)
        if results.left_hand_landmarks:
            for idx, lm in enumerate(results.left_hand_landmarks.landmark):
                lh[idx] = [lm.x, lm.y, lm.z]

        # 3. Right hand landmarks (21 landmarks)
        rh = np.zeros((21, 3), dtype=np.float32)
        if results.right_hand_landmarks:
            for idx, lm in enumerate(results.right_hand_landmarks.landmark):
                rh[idx] = [lm.x, lm.y, lm.z]

        # Concatenate into 201-dim 1D array
        features = np.concatenate([pose.flatten(), lh.flatten(), rh.flatten()])
        return features

    def resample_sequence(self, sequence: np.ndarray, target_len: int = 60) -> np.ndarray:
        """Resamples or interpolates a sequence (T, D) to target length (target_len, D)."""
        curr_len = len(sequence)
        if curr_len == 0:
            return np.zeros((target_len, 201), dtype=np.float32)
        if curr_len == target_len:
            return sequence

        indices = np.linspace(0, curr_len - 1, target_len)
        resampled = np.zeros((target_len, sequence.shape[1]), dtype=np.float32)
        for d in range(sequence.shape[1]):
            resampled[:, d] = np.interp(indices, np.arange(curr_len), sequence[:, d])
        return resampled

    def extract_from_video(self, video_path: str) -> np.ndarray:
        """
        Processes an entire video file and returns an array of shape (60, 201).
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video file: {video_path}")

        frame_features: List[np.ndarray] = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            feats = self.extract_frame_landmarks(frame_rgb)
            frame_features.append(feats)

        cap.release()

        if not frame_features:
            return np.zeros((self.target_seq_len, 201), dtype=np.float32)

        raw_sequence = np.array(frame_features, dtype=np.float32)
        return self.resample_sequence(raw_sequence, self.target_seq_len)

    def close(self):
        if self._holistic is not None:
            self._holistic.close()
            self._holistic = None


class HandLandmarkExtractor:
    """
    Extracts 42-dim normalized hand landmarks for static fingerspelling / alphabet.
    Matches the normalization in Paper 2:
    - 21 landmarks
    - Subtract wrist (landmark 0) -> wrist becomes (0, 0)
    - Scale by maximum Euclidean coordinate distance to achieve scale invariance
    """

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self._hands = None

    def _get_hands(self):
        if self._hands is None:
            import mediapipe as mp
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_num_hands,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
        return self._hands

    def extract_hand_landmarks(
        self, frame_rgb: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[object]]:
        """
        Returns:
            (normalized_landmarks_42, raw_hand_landmarks_object)
            normalized_landmarks_42: shape (42,), normalized relative to wrist
        """
        hands = self._get_hands()
        results = hands.process(frame_rgb)

        if not results.multi_hand_landmarks:
            return None, None

        # Take primary detected hand
        hand_landmarks = results.multi_hand_landmarks[0]
        coords = np.array(
            [[lm.x, lm.y] for lm in hand_landmarks.landmark], dtype=np.float32
        )  # (21, 2)

        # Normalize relative to wrist (index 0)
        wrist = coords[0].copy()
        norm_coords = coords - wrist  # wrist becomes (0.0, 0.0)

        # Scale normalization (max absolute value)
        max_val = np.max(np.abs(norm_coords))
        if max_val > 1e-6:
            norm_coords = norm_coords / max_val

        return norm_coords.flatten(), hand_landmarks

    def close(self):
        if self._hands is not None:
            self._hands.close()
            self._hands = None
