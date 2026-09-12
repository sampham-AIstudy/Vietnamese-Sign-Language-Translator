"""
Real-time VSL Video Processor for streamlit-webrtc.
Extracts 201-dim MediaPipe Holistic landmarks, maintains sliding window buffer,
resamples to (60, 201), and runs continuous inference with confidence filtering and debounce.
"""

import time
import threading
from collections import deque
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np
import torch

try:
    import av
except ImportError:
    av = None

import mediapipe as mp

try:
    from streamlit_webrtc import VideoProcessorBase
except ImportError:
    # Fallback if imported before streamlit_webrtc is loaded
    class VideoProcessorBase:
        pass

from src.data.extract_landmarks import HolisticLandmarkExtractor


class VSLRealtimeVideoProcessor(VideoProcessorBase):
    """
    Thread-safe WebRTC Video Processor for real-time Vietnamese Sign Language recognition.
    """

    def __init__(
        self,
        model: Optional[torch.nn.Module] = None,
        idx_to_class: Optional[Dict[int, str]] = None,
        device: Optional[torch.device] = None,
        window_sec: float = 2.0,
        infer_interval_frames: int = 6,
        confidence_threshold: float = 0.65,
        debounce_sec: float = 1.2,
    ):
        super().__init__()
        self.model = model
        self.idx_to_class = idx_to_class or {}
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.window_sec = window_sec
        self.infer_interval_frames = infer_interval_frames
        self.confidence_threshold = confidence_threshold
        self.debounce_sec = debounce_sec

        # Feature extractor
        self.extractor = HolisticLandmarkExtractor(target_seq_len=60)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_holistic = mp.solutions.holistic
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Buffer: stores (timestamp, 201-dim array)
        self.buffer = deque()
        self.frame_count = 0
        self.fps = 0.0
        self.last_frame_time = time.time()

        # Thread synchronization
        self.lock = threading.Lock()

        # Shared state for Streamlit UI
        self.latest_prediction: str = "..."
        self.latest_confidence: float = 0.0
        self.top5_predictions: List[Tuple[str, float]] = []
        self.sentence_tokens: List[str] = []
        self.is_signing: bool = False

        # Debounce tracking
        self.last_emitted_gloss: str = ""
        self.last_emitted_time: float = 0.0

    def update_config(self, threshold: float, debounce: float, window: float):
        """Update runtime parameters thread-safely."""
        with self.lock:
            self.confidence_threshold = threshold
            self.debounce_sec = debounce
            self.window_sec = window

    def clear_sentence(self):
        """Clear the accumulated sentence."""
        with self.lock:
            self.sentence_tokens.clear()
            self.last_emitted_gloss = ""

    def pop_last_word(self):
        """Delete the last recognized word from sentence."""
        with self.lock:
            if self.sentence_tokens:
                self.sentence_tokens.pop()

    def get_state(self) -> Dict[str, Any]:
        """Snapshot current state for Streamlit UI rendering."""
        with self.lock:
            return {
                "latest_prediction": self.latest_prediction,
                "latest_confidence": self.latest_confidence,
                "top5": list(self.top5_predictions),
                "sentence_tokens": list(self.sentence_tokens),
                "sentence_text": " ".join(self.sentence_tokens),
                "is_signing": self.is_signing,
                "fps": self.fps,
                "buffer_len": len(self.buffer),
            }

    def _draw_hud(self, img_bgr: np.ndarray, pred_gloss: str, conf: float, is_active: bool):
        """Draw aesthetic status header on the video frame."""
        h, w, _ = img_bgr.shape
        # Top banner background
        overlay = img_bgr.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, img_bgr, 0.25, 0, img_bgr)

        # Status text
        status_color = (0, 255, 127) if is_active else (200, 200, 200)
        status_text = f"VSL Live: {pred_gloss} ({conf*100:.1f}%)" if is_active else "VSL Live: Dang lang nghe..."
        cv2.putText(
            img_bgr,
            status_text,
            (15, 33),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            status_color,
            2,
            cv2.LINE_AA,
        )

        # FPS indicator
        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(
            img_bgr,
            fps_text,
            (w - 120, 33),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def process_bgr_frame(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes a single BGR video frame:
        - Calculates FPS
        - Extracts 201-dim MediaPipe Holistic landmarks
        - Maintains time-based sliding window buffer
        - Draws skeletal overlay
        - Periodically infers sign gloss with confidence and debounce filtering
        - Draws HUD overlay
        Returns:
            annotated_img_bgr (np.ndarray): Annotated video frame with landmarks and HUD
            state (dict): Current recognition state
        """
        now = time.time()
        # Calculate instantaneous FPS
        dt = now - self.last_frame_time
        if dt > 0:
            current_fps = 1.0 / dt
            self.fps = 0.9 * self.fps + 0.1 * current_fps if self.fps > 0 else current_fps
        self.last_frame_time = now
        self.frame_count += 1

        annotated_img = img_bgr.copy()
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 1. Process MediaPipe Holistic
        holistic = self.extractor._get_holistic()
        results = holistic.process(img_rgb)

        # 2. Extract 201-dim landmark vector
        pose = np.zeros((25, 3), dtype=np.float32)
        if results.pose_landmarks:
            for idx in range(min(25, len(results.pose_landmarks.landmark))):
                lm = results.pose_landmarks.landmark[idx]
                pose[idx] = [lm.x, lm.y, lm.z]

        lh = np.zeros((21, 3), dtype=np.float32)
        if results.left_hand_landmarks:
            for idx, lm in enumerate(results.left_hand_landmarks.landmark):
                lh[idx] = [lm.x, lm.y, lm.z]

        rh = np.zeros((21, 3), dtype=np.float32)
        if results.right_hand_landmarks:
            for idx, lm in enumerate(results.right_hand_landmarks.landmark):
                rh[idx] = [lm.x, lm.y, lm.z]

        feature_201 = np.concatenate([pose.flatten(), lh.flatten(), rh.flatten()])

        # 3. Maintain sliding window buffer
        self.buffer.append((now, feature_201))
        cutoff_time = now - self.window_sec
        while self.buffer and self.buffer[0][0] < cutoff_time:
            self.buffer.popleft()

        # 4. Draw skeletal landmarks on frame
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated_img,
                results.pose_landmarks,
                self.mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
            )
        if results.left_hand_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated_img,
                results.left_hand_landmarks,
                self.mp_holistic.HAND_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                connection_drawing_spec=self.mp_drawing_styles.get_default_hand_connections_style(),
            )
        if results.right_hand_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated_img,
                results.right_hand_landmarks,
                self.mp_holistic.HAND_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                connection_drawing_spec=self.mp_drawing_styles.get_default_hand_connections_style(),
            )

        # 5. Periodic inference
        if (
            self.model is not None
            and self.idx_to_class
            and self.frame_count % self.infer_interval_frames == 0
            and len(self.buffer) >= 12
        ):
            buf_duration = self.buffer[-1][0] - self.buffer[0][0]
            if buf_duration >= 0.8:
                raw_seq = np.array([item[1] for item in self.buffer], dtype=np.float32)
                resampled = self.extractor.resample_sequence(raw_seq, target_len=60)

                inp_t = torch.tensor(resampled, dtype=torch.float32).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    logits = self.model(inp_t)
                    probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

                top_indices = np.argsort(probs)[-5:][::-1]
                top1_idx = int(top_indices[0])
                pred_gloss = self.idx_to_class.get(top1_idx, "Unknown")
                pred_conf = float(probs[top1_idx])

                top5 = [
                    (self.idx_to_class.get(int(idx), f"Class {idx}"), float(probs[idx]))
                    for idx in top_indices
                ]

                is_confident = pred_conf >= self.confidence_threshold
                with self.lock:
                    self.latest_prediction = pred_gloss
                    self.latest_confidence = pred_conf
                    self.top5_predictions = top5
                    self.is_signing = is_confident

                    if is_confident:
                        time_since_last = now - self.last_emitted_time
                        is_new_word = pred_gloss != self.last_emitted_gloss
                        if is_new_word or (time_since_last >= self.debounce_sec):
                            self.sentence_tokens.append(pred_gloss)
                            self.last_emitted_gloss = pred_gloss
                            self.last_emitted_time = now

        # 6. Overlay HUD
        with self.lock:
            cur_pred = self.latest_prediction
            cur_conf = self.latest_confidence
            cur_active = self.is_signing

        self._draw_hud(annotated_img, cur_pred, cur_conf, cur_active)
        return annotated_img, self.get_state()

    def recv(self, frame: Any) -> Any:
        """
        WebRTC frame receive callback. Runs on background media worker thread.
        Never calls Streamlit API directly.
        """
        img_bgr = frame.to_ndarray(format="bgr24")
        annotated_img, _ = self.process_bgr_frame(img_bgr)
        if av is not None:
            return av.VideoFrame.from_ndarray(annotated_img, format="bgr24")
        return annotated_img
