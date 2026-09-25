"""
Real-Time Vietnamese Sign Language Recognition Demo (Phase 10).
Live webcam and video stream inference with MediaPipe Holistic,
Temporal Buffer Preprocessing, and Anti-Flicker Temporal Smoothing.

Usage:
  python realtime_demo.py                       # Live Webcam (device 0)
  python realtime_demo.py --webcam 1            # External Webcam (device 1)
  python realtime_demo.py --video "path.mp4"    # Test Video File
  python realtime_demo.py --headless --max-frames 90   # Automated Smoke Test
"""

import os
import sys
import time
import argparse
import collections
from typing import Optional, Tuple, List

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.predictor import VSLPredictor
from src.inference.realtime_extractor import RealtimeLandmarkExtractor
from src.inference.realtime_pipeline import RealtimePipeline
from src.inference.smoother import TemporalSmoother


class RealtimeHUD:
    """
    Renders a modern, semi-transparent Head-Up Display (HUD) with
    crisp Vietnamese typography via Pillow onto OpenCV video frames.
    """

    def __init__(self, font_size_large: int = 34, font_size_small: int = 18):
        self.font_path = self._locate_vietnamese_font()
        try:
            self.font_large = ImageFont.truetype(self.font_path, font_size_large)
            self.font_medium = ImageFont.truetype(self.font_path, font_size_small + 4)
            self.font_small = ImageFont.truetype(self.font_path, font_size_small)
        except Exception:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def _locate_vietnamese_font(self) -> str:
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return "arial.ttf"

    def draw_hud(
        self,
        frame: np.ndarray,
        smoothed_state: dict,
        pipeline_info: dict,
        model_name: str,
        fps: float,
        latency_ms: float,
        show_sidebar: bool = True,
        translated_sentence: str = "",
    ) -> np.ndarray:
        """
        Renders HUD overlay onto frame.
        """
        H, W, _ = frame.shape
        overlay = frame.copy()

        # 1. Top Header Bar (dark translucent)
        cv2.rectangle(overlay, (0, 0), (W, 64), (20, 24, 30), -1)

        # 2. Left Sidebar (for top-5 and buffer info)
        sidebar_w = 320
        if show_sidebar:
            cv2.rectangle(overlay, (0, 64), (sidebar_w, H - 40), (20, 24, 30), -1)

        # 3. Bottom Control Hint Bar
        cv2.rectangle(overlay, (0, H - 36), (W, H), (15, 18, 22), -1)

        # 4. Central Subtitle Pill (for primary recognized sign)
        active_gloss = smoothed_state.get("gloss", "...")
        conf = smoothed_state.get("confidence", 0.0)
        status = smoothed_state.get("status", "IDLE")

        pill_w, pill_h = 580, 84
        pill_x1 = (W - pill_w) // 2
        pill_y1 = H - 132
        pill_x2 = pill_x1 + pill_w
        pill_y2 = pill_y1 + pill_h

        # Pill background color based on status
        if status == "CONFIRMED":
            pill_color = (18, 55, 22)  # Dark green
            border_color = (46, 204, 113)  # Bright emerald
        elif status == "DETECTING":
            pill_color = (20, 45, 55)  # Dark amber
            border_color = (241, 196, 15)  # Gold
        elif status == "STATIC_HAND":
            pill_color = (20, 35, 55)  # Dark blue
            border_color = (52, 152, 219)  # Sky blue
        else:
            pill_color = (30, 32, 38)  # Slate
            border_color = (127, 140, 141)

        cv2.rectangle(overlay, (pill_x1, pill_y1), (pill_x2, pill_y2), pill_color, -1)
        cv2.rectangle(overlay, (pill_x1, pill_y1), (pill_x2, pill_y2), border_color, 2)

        # Blend overlays with transparency
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

        # Render Crisp Vietnamese Typography via Pillow
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # A. Header Text
        draw.text((16, 14), "VSLR Real-Time Translator", font=self.font_medium, fill=(255, 255, 255))
        draw.text((360, 18), f"Model: {model_name}", font=self.font_small, fill=(200, 220, 255))

        # Status badge color
        status_colors = {
            "CONFIRMED": (46, 204, 113),
            "DETECTING": (241, 196, 15),
            "STATIC_HAND": (52, 152, 219),
            "IDLE": (189, 195, 199),
        }
        badge_col = status_colors.get(status, (200, 200, 200))
        draw.text((W - 320, 16), f"● {status}", font=self.font_medium, fill=badge_col)
        draw.text((W - 160, 18), f"{fps:.1f} FPS | {latency_ms:.1f}ms", font=self.font_small, fill=(220, 220, 220))

        # B. Central Subtitle Text (Main Gloss + ViT5 Sentence Translation)
        if active_gloss != "...":
            display_text = f"Ký hiệu: {active_gloss} ({conf*100:.1f}%)"
            draw.text((pill_x1 + 20, pill_y1 + 10), display_text, font=self.font_large, fill=(255, 255, 255))
        elif status == "STATIC_HAND":
            draw.text((pill_x1 + 20, pill_y1 + 14), "Bàn tay tĩnh (Đang giữ tư thế, chờ cử chỉ động...)", font=self.font_medium, fill=(130, 210, 255))
        else:
            draw.text((pill_x1 + 20, pill_y1 + 14), "Đang chờ cử chỉ ký hiệu...", font=self.font_medium, fill=(180, 180, 180))

        if translated_sentence:
            draw.text((pill_x1 + 20, pill_y1 + 50), f"Dịch ViT5: {translated_sentence}", font=self.font_medium, fill=(46, 204, 113))

        # C. Left Sidebar Content
        if show_sidebar:
            buf_fill = pipeline_info.get("buffer_fill", 0)
            buf_cap = pipeline_info.get("buffer_capacity", 60)
            draw.text((16, 78), f"Buffer: {buf_fill}/{buf_cap} frames", font=self.font_small, fill=(220, 220, 220))

            # Progress Bar
            bar_w = 280
            bar_fill = int((buf_fill / max(1, buf_cap)) * bar_w)
            # Draw empty bar background
            # (Pillow rectangle)
            draw.rectangle([16, 106, 16 + bar_w, 116], fill=(50, 50, 50))
            draw.rectangle([16, 106, 16 + bar_fill, 116], fill=(52, 152, 219))

            # Top-5 Predictions
            draw.text((16, 136), "Top-5 Dự đoán:", font=self.font_medium, fill=(241, 196, 15))
            top5_items = smoothed_state.get("top5", [])
            for i, item in enumerate(top5_items[:5]):
                g_name = item.get("gloss", "")
                g_prob = item.get("confidence", 0.0)
                y_pos = 172 + i * 44

                # Candidate item text
                draw.text((16, y_pos), f"{i+1}. {g_name[:18]}", font=self.font_small, fill=(240, 240, 240))
                draw.text((250, y_pos), f"{g_prob*100:.1f}%", font=self.font_small, fill=(180, 220, 240))

                # Mini progress bar for probability
                prob_bar_fill = int(g_prob * bar_w)
                draw.rectangle([16, y_pos + 26, 16 + bar_w, y_pos + 30], fill=(40, 40, 40))
                draw.rectangle([16, y_pos + 26, 16 + prob_bar_fill, y_pos + 30], fill=(46, 204, 113) if i == 0 else (100, 100, 100))

            # Sentence History
            history_list = smoothed_state.get("sentence", [])
            draw.text((16, H - 150), "Lịch sử câu đã dịch:", font=self.font_medium, fill=(241, 196, 15))
            recent_words = " ".join(history_list[-4:]) if history_list else "(chưa có)"
            draw.text((16, H - 118), f"{recent_words[:35]}", font=self.font_small, fill=(220, 220, 220))

        # D. Bottom Control Hints
        controls_str = "[Q] Thoát  |  [C] Xóa Buffer  |  [M] Đổi Model  |  [D] Bật/Tắt Khớp Xương  |  [H] Bật/Tắt HUD"
        draw.text((16, H - 28), controls_str, font=self.font_small, fill=(160, 160, 160))

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


class RealtimeDemo:
    """
    Main Real-time Application Controller.
    """

    def __init__(
        self,
        source: str = "0",
        model_type: str = "stgcn",
        headless: bool = False,
        max_frames: Optional[int] = None,
        draw_skeleton: bool = True,
    ):
        self.source = source
        self.model_type = model_type
        self.headless = headless
        self.max_frames = max_frames
        self.draw_skeleton = draw_skeleton
        self.show_sidebar = True

        print("=" * 64)
        print("INITIALIZING VIETNAMESE SIGN LANGUAGE REALTIME PIPELINE")
        print("=" * 64)

        # 1. Initialize Predictor
        print(f"Loading VSLPredictor (model_type='{model_type}')...")
        self.predictor = VSLPredictor(model_type=model_type)

        # 2. Initialize Pipeline & Extractor
        print("Loading MediaPipe Holistic RealtimeLandmarkExtractor...")
        self.extractor = RealtimeLandmarkExtractor()
        self.pipeline = RealtimePipeline(
            predictor=self.predictor,
            extractor=self.extractor,
            target_len=60,
            infer_interval=3,
        )

        # 3. Initialize Temporal Smoother
        self.smoother = TemporalSmoother(
            confidence_threshold=0.45,
            window_size=5,
            min_consistency_count=2,
            hold_frames=24,
        )

        # 4. Initialize HUD renderer
        self.hud = RealtimeHUD()

        # 5. Initialize ViT5 Translation Engine
        self.translator = None
        try:
            from src.translation.translator import VSLTranslator
            print("Loading ViT5 Translation Engine (Gloss -> Natural Vietnamese)...")
            self.translator = VSLTranslator()
            print("ViT5 Translation Engine loaded successfully.")
        except Exception as e:
            print(f"[Warning] Could not load ViT5 Translator: {e}")

        self.translated_sentence = ""
        self.last_translated_history = []

    def _open_stream(self) -> cv2.VideoCapture:
        # Determine source
        if self.source.isdigit():
            src = int(self.source)
            print(f"Opening Live Webcam Device Index: {src}...")
            cap = cv2.VideoCapture(src)
        elif self.source == "mock":
            print("Using Synthetic Mock Video Stream for Smoke Test...")
            cap = None
        else:
            if not os.path.exists(self.source):
                raise FileNotFoundError(f"Video file not found: {self.source}")
            print(f"Opening Video Stream from: {self.source}...")
            cap = cv2.VideoCapture(self.source)

        if cap is not None and not cap.isOpened():
            raise IOError(f"Could not open video capture stream: {self.source}")

        return cap

    def run(self):
        cap = self._open_stream()
        frame_idx = 0
        fps_tracker = collections.deque(maxlen=30)
        t_prev = time.time()

        print("\nStarting Real-time Loop. Press 'q' in GUI to quit.\n")

        try:
            while True:
                t_start = time.time()
                frame_idx += 1

                # Frame acquisition
                if self.source == "mock":
                    # Synthetic 720p frame
                    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.circle(frame, (640, 360), 80, (60, 60, 60), -1)
                else:
                    ret, frame = cap.read()
                    if not ret:
                        print("End of video stream reached.")
                        break

                # 1. Pipeline Processing
                info = self.pipeline.process_frame(frame)
                raw_pred = info["prediction"]
                hand_detected = info["hand_detected"]
                results = info["results"]

                # 2. Temporal Smoothing with Motion Gating
                smoothed = self.smoother.update(
                    raw_pred,
                    hand_detected=hand_detected,
                    is_moving=info.get("is_moving", True),
                )

                # ViT5 Sentence Translation
                current_history = smoothed.get("sentence", [])
                if self.translator and current_history and current_history != self.last_translated_history:
                    self.last_translated_history = list(current_history)
                    try:
                        t_res = self.translator.translate(current_history)
                        self.translated_sentence = t_res.get("translation", "")
                    except Exception:
                        pass

                # FPS Calculation
                dt = time.time() - t_start
                fps_tracker.append(dt)
                avg_fps = 1.0 / (sum(fps_tracker) / len(fps_tracker)) if fps_tracker else 30.0
                latency = raw_pred.get("latency_ms", 0.0) if raw_pred else 0.0

                # 3. Visualization
                if not self.headless:
                    display_frame = frame.copy()
                    if self.draw_skeleton:
                        display_frame = self.extractor.draw_landmarks(display_frame, results)

                    # Render HUD
                    display_frame = self.hud.draw_hud(
                        frame=display_frame,
                        smoothed_state=smoothed,
                        pipeline_info=info,
                        model_name=self.model_type.upper(),
                        fps=avg_fps,
                        latency_ms=latency,
                        show_sidebar=self.show_sidebar,
                        translated_sentence=self.translated_sentence,
                    )

                    cv2.imshow("VSLR Real-Time Demo (Phase 10)", display_frame)

                    # Handle User Input
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        print("User initiated exit via 'q'.")
                        break
                    elif key == ord("c"):
                        self.pipeline.clear_buffer()
                        self.smoother.reset()
                        self.translated_sentence = ""
                        self.last_translated_history = []
                        print("Cleared temporal buffer and sentence history.")
                    elif key == ord("d"):
                        self.draw_skeleton = not self.draw_skeleton
                        print(f"Skeleton visualization: {self.draw_skeleton}")
                    elif key == ord("h"):
                        self.show_sidebar = not self.show_sidebar
                        print(f"Sidebar HUD: {self.show_sidebar}")
                    elif key == ord("m"):
                        # Cycle model: stgcn -> ensemble -> transformer
                        next_models = {"stgcn": "ensemble", "ensemble": "transformer", "transformer": "stgcn"}
                        self.model_type = next_models[self.model_type]
                        print(f"Switching active model to: {self.model_type.upper()}...")
                        self.pipeline.predictor = VSLPredictor(model_type=self.model_type)
                else:
                    # Headless log every 30 frames
                    if frame_idx % 30 == 0 or frame_idx == 1:
                        print(f"Frame {frame_idx:04d} | Buffer: {info['buffer_fill']}/60 | Active: {smoothed['gloss']} ({smoothed['confidence']*100:.1f}%) | {avg_fps:.1f} FPS")

                if self.max_frames and frame_idx >= self.max_frames:
                    print(f"Reached max_frames threshold ({self.max_frames}). Gracefully stopping.")
                    break

        finally:
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()
            self.pipeline.close()
            print("Video capture and MediaPipe pipeline closed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Vietnamese Sign Language Recognition Demo")
    parser.add_argument("--source", type=str, default="0", help="Webcam device index ('0', '1') or video path ('path.mp4') or 'mock'")
    parser.add_argument("--video", type=str, default=None, help="Shorthand for --source <path.mp4>")
    parser.add_argument("--model", type=str, default="stgcn", choices=["stgcn", "ensemble", "transformer"], help="Model architecture")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode without opening GUI window (for tests)")
    parser.add_argument("--max-frames", type=int, default=None, help="Terminate after N frames")
    args = parser.parse_args()

    source = args.video if args.video else args.source
    demo = RealtimeDemo(
        source=source,
        model_type=args.model,
        headless=args.headless,
        max_frames=args.max_frames,
    )
    demo.run()


if __name__ == "__main__":
    main()
