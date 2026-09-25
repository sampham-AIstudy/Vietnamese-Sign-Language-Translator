"""
Generates high-resolution demonstration frames and HUD overlays for presentation slides (Phase 14).
Saves output PNGs to: submission/slide_images/
"""

import os
import sys
import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.inference.predictor import VSLPredictor
from src.inference.realtime_extractor import RealtimeLandmarkExtractor
from src.inference.realtime_pipeline import RealtimePipeline
from src.inference.smoother import TemporalSmoother
from realtime_demo import RealtimeHUD


def generate_slide_images():
    print("Generating Presentation Slide Images...")
    os.makedirs("submission/slide_images", exist_ok=True)

    sample_video = r"data\Dataset\Videos\W00009N.mp4"
    if not os.path.exists(sample_video):
        print(f"Warning: sample video {sample_video} not found.")
        return

    predictor = VSLPredictor(model_type="stgcn", warmup=True)
    extractor = RealtimeLandmarkExtractor()
    pipeline = RealtimePipeline(predictor=predictor, extractor=extractor, target_len=60, infer_interval=2)
    smoother = TemporalSmoother(confidence_threshold=0.35, window_size=5, min_consistency_count=2)
    hud = RealtimeHUD()

    cap = cv2.VideoCapture(sample_video)
    frame_idx = 0
    saved_frames = 0

    while frame_idx < 45 and saved_frames < 3:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        info = pipeline.process_frame(frame)
        smoothed = smoother.update(info["prediction"], hand_detected=info["hand_detected"])

        if frame_idx in [15, 30, 42]:
            # Render skeleton on frame
            frame_annotated = extractor.draw_landmarks(frame, info["results"])

            # Render HUD
            hud_frame = hud.draw_hud(
                frame=frame_annotated,
                smoothed_state=smoothed,
                pipeline_info=info,
                model_name="ST-GCN (Spatial Master)",
                fps=28.5,
                latency_ms=10.5,
                show_sidebar=True,
            )

            out_name = f"submission/slide_images/demo_hud_slide_{saved_frames + 1}.png"
            cv2.imwrite(out_name, hud_frame)
            print(f"  -> Saved: {out_name}")
            saved_frames += 1

    cap.release()
    pipeline.close()
    print("Slide images successfully generated in submission/slide_images/")


if __name__ == "__main__":
    generate_slide_images()

