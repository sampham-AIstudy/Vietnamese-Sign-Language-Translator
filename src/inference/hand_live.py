"""
Level 1 ("Đánh vần") live hand-landmark extraction for WS /ws/hand-landmarks (plan 06 §3.3).

The Level 1 model was trained on landmarks from scripts/extract_hands_batch.py::_extract_one:
mp.solutions.hands.Hands with the keywords below (mediapipe 0.10.14), a NEW tracker per clip, the ORIGINAL frame
(no resize, no mirror), BGR -> RGB, the first detected hand and its first handedness classification.
HandLandmarkSession reproduces exactly that per recorded sign: reset() = new tracker (like a new clip),
process(frame_bgr) = one frame of the clip. The equivalence with _extract_one is tested bit-for-bit
(tests/test_hand_landmarks_ws.py AC4-a, tests/test_hand_live_equivalence.py AC5).

Pure module: imports cv2 / mediapipe / numpy only (no torch, no fastapi).
"""
from typing import Any, Dict, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

EXTRACTOR_NAME = "mp.solutions.hands"
# Must equal the keywords of the Hands(...) call in scripts/extract_hands_batch.py (read with ast in AC4-a).
LEVEL1_HANDS_KWARGS: Dict[str, Any] = {
    "static_image_mode": False,
    "max_num_hands": 1,
    "model_complexity": 1,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
}


def extractor_info() -> Dict[str, Any]:
    """Extractor description sent in the session_info of /ws/hand-landmarks."""
    return {"name": EXTRACTOR_NAME, "mediapipe_version": mp.__version__, **LEVEL1_HANDS_KWARGS}


class HandLandmarkSession:
    """One MediaPipe Hands graph in video mode; reset() starts a new tracker (one per recorded sign).
    Not thread-safe: a session must be used by one caller at a time."""

    def __init__(self):
        self._hands = None
        self.reset()

    def reset(self) -> None:
        """Closes the current graph (if any) and creates a new one (fresh tracker)."""
        self.close()
        # attribute looked up at call time (tests spy on mp.solutions.hands.Hands)
        self._hands = mp.solutions.hands.Hands(**LEVEL1_HANDS_KWARGS)

    def process(self, frame_bgr: np.ndarray) -> Tuple[Optional[np.ndarray], str, Optional[float]]:
        """(landmarks float32[21, 3] | None, handedness label ("Left"/"Right", "" without hand), score | None).
        Same conversion as _extract_one: cv2.cvtColor(BGR2RGB) of the original frame, multi_hand_landmarks[0],
        multi_handedness[0].classification[0]."""
        if self._hands is None:
            raise RuntimeError("HandLandmarkSession is closed")
        res = self._hands.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        if res.multi_hand_landmarks:
            landmarks = np.asarray([[p.x, p.y, p.z] for p in res.multi_hand_landmarks[0].landmark], dtype=np.float32)
            c = res.multi_handedness[0].classification[0]
            return landmarks, str(c.label), float(c.score)
        return None, "", None

    def close(self) -> None:
        """Closes the graph once; further calls do nothing."""
        hands, self._hands = self._hands, None
        if hands is not None:
            hands.close()
