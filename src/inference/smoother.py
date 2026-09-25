"""
Temporal Prediction Smoother for Vietnamese Sign Language Recognition (Phase 10).
Prevents flickering and transient jitter in live video inference.

Key Mechanisms:
1. Confidence Thresholding (filters low-confidence ambiguous transitions).
2. Majority Voting & Exponential Moving Average across a sliding history window.
3. Persistence Debounce (requires sign to be stable across consecutive windows).
4. Display Hold & Sentence History accumulator.
"""

import collections
import time
from typing import Dict, Any, Optional, List, Tuple


class TemporalSmoother:
    """
    Stabilizes and filters raw per-frame sign language predictions.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.45,
        window_size: int = 5,
        min_consistency_count: int = 2,
        hold_frames: int = 20,
        refractory_frames: int = 30,
    ):
        """
        Args:
            confidence_threshold: Minimum probability for a prediction to be considered.
            window_size: Number of recent inferences kept for voting (default 5).
            min_consistency_count: Minimum votes needed within window to confirm a sign (default 2).
            hold_frames: Number of video frames to hold confirmed prediction on screen.
            refractory_frames: Cooldown before the same gloss can be re-added to sentence history.
        """
        self.confidence_threshold = confidence_threshold
        self.window_size = window_size
        self.min_consistency_count = min_consistency_count
        self.hold_frames = hold_frames
        self.refractory_frames = refractory_frames

        # History queues
        self.prediction_window = collections.deque(maxlen=window_size)
        self.confidence_window = collections.deque(maxlen=window_size)

        # State tracking
        self.active_gloss: str = "..."
        self.active_confidence: float = 0.0
        self.hold_counter: int = 0
        self.is_confirmed: bool = False

        # Sentence history
        self.confirmed_history: List[str] = []
        self.last_confirmed_gloss: Optional[str] = None
        self.cooldown_counter: int = 0

    def reset(self):
        """Resets all smoother states and sentence history."""
        self.prediction_window.clear()
        self.confidence_window.clear()
        self.active_gloss = "..."
        self.active_confidence = 0.0
        self.hold_counter = 0
        self.is_confirmed = False
        self.confirmed_history.clear()
        self.last_confirmed_gloss = None
        self.cooldown_counter = 0

    def update(
        self,
        raw_prediction: Optional[Dict[str, Any]],
        hand_detected: bool = True,
        is_moving: bool = True,
    ) -> Dict[str, Any]:
        """
        Updates smoother with latest raw prediction from pipeline.

        Args:
            raw_prediction: Dict containing 'gloss', 'confidence', 'top5' (or None).
            hand_detected: True if user's hands are visible in frame.
            is_moving: True if hands exhibit sufficient kinematic movement for a dynamic sign.

        Returns:
            Dictionary with:
              - 'gloss': Current stable displayed gloss.
              - 'confidence': Smoothed confidence [0.0 - 1.0].
              - 'is_confirmed': True if candidate reached consistency criteria.
              - 'status': 'DETECTING', 'CONFIRMED', 'STATIC_HAND', or 'IDLE'.
              - 'sentence': List of confirmed glosses accumulated so far.
              - 'top5': Raw or averaged top-5 predictions.
        """
        # Decrement cooldown counters
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if self.hold_counter > 0:
            self.hold_counter -= 1
        elif not hand_detected:
            # If no hands detected and hold expired, clear active display
            self.active_gloss = "..."
            self.active_confidence = 0.0
            self.is_confirmed = False

        # If hand detected but completely stationary (holding a static pose like letter C)
        # Suppress dynamic word model to prevent false positive triggers
        if hand_detected and not is_moving and self.hold_counter == 0:
            self.prediction_window.clear()
            self.confidence_window.clear()
            self.active_gloss = "..."
            self.active_confidence = 0.0
            self.is_confirmed = False
            return self._build_state(raw_prediction, status_override="STATIC_HAND")

        # If no new prediction provided on this video frame, maintain held state
        if raw_prediction is None or not hand_detected:
            return self._build_state(raw_prediction)

        gloss = raw_prediction.get("gloss", "...")
        conf = raw_prediction.get("confidence", 0.0)

        # 1. Filter out low-confidence predictions
        if conf >= self.confidence_threshold:
            self.prediction_window.append(gloss)
            self.confidence_window.append(conf)
        else:
            self.prediction_window.append("...")
            self.confidence_window.append(0.0)

        # 2. Majority Voting across recent window
        valid_votes = [g for g in self.prediction_window if g != "..."]
        if not valid_votes:
            status = "IDLE" if self.hold_counter == 0 else "CONFIRMED"
            return self._build_state(raw_prediction, status_override=status)

        vote_counts = collections.Counter(valid_votes)
        candidate_gloss, count = vote_counts.most_common(1)[0]

        # Calculate average confidence for the winning candidate
        candidate_confs = [
            c for g, c in zip(self.prediction_window, self.confidence_window) if g == candidate_gloss
        ]
        avg_conf = sum(candidate_confs) / len(candidate_confs) if candidate_confs else 0.0

        # 3. Consistency Confirmation Check
        if count >= self.min_consistency_count and avg_conf >= self.confidence_threshold:
            self.active_gloss = candidate_gloss
            self.active_confidence = avg_conf
            self.hold_counter = self.hold_frames
            self.is_confirmed = True

            # Add to sentence history if not immediate duplicate
            if (candidate_gloss != self.last_confirmed_gloss) or (self.cooldown_counter == 0):
                self.confirmed_history.append(candidate_gloss)
                self.last_confirmed_gloss = candidate_gloss
                self.cooldown_counter = self.refractory_frames

            status = "CONFIRMED"
        else:
            status = "DETECTING" if self.hold_counter == 0 else "CONFIRMED"

        return self._build_state(raw_prediction, status_override=status)

    def _build_state(self, raw_prediction: Optional[Dict[str, Any]], status_override: Optional[str] = None) -> Dict[str, Any]:
        status = status_override or ("CONFIRMED" if self.is_confirmed else "IDLE")
        top5 = raw_prediction.get("top5", []) if raw_prediction else []

        return {
            "gloss": self.active_gloss,
            "confidence": round(self.active_confidence, 4),
            "is_confirmed": self.is_confirmed,
            "status": status,
            "sentence": list(self.confirmed_history),
            "top5": top5,
        }
