"""
Plan 06 §3.7: turn a real video into a Y4M file for the browser's fake webcam
(Edge/Chromium `--use-file-for-fake-video-capture=<file.y4m>`, which plays the file in a loop).

    .venv/Scripts/python scripts/make_fake_webcam_y4m.py --video <mp4> --out <y4m> [--max-frames N]

- Frames are read with cv2 (BGR), cropped to an even width/height (1 px off the right/bottom edge when odd; 4:2:0
  needs even sizes), converted with cv2.COLOR_BGR2YUV_I420 and written as `C420jpeg`.
- Same size (after the crop) and same frame rate as the video: `F<num>:<den>` is the video fps as a fraction.
- The output must be OUTSIDE the repository (the file holds video frames; plan 06 AC1 forbids committing them):
  an output path inside the repository is refused.
Prints one JSON line with the facts of the written file (frames, width, height, fps fraction); no frame data.
"""
import argparse
import json
import os
import sys
from fractions import Fraction

import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def fps_fraction(fps: float) -> Fraction:
    """Video fps -> exact small fraction (29.97002997 -> 30000/1001; 23.584 -> 2948/125)."""
    if not fps or fps <= 0:
        raise ValueError(f"video reports no usable fps: {fps!r}")
    return Fraction(fps).limit_denominator(1001)


def is_inside_repo(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(ROOT)
    return p == root or p.startswith(root + os.sep)


def write_y4m(video: str, out: str, max_frames: int = 0) -> dict:
    if is_inside_repo(out):
        raise ValueError("the y4m output must be outside the repository (video frames are never committed)")
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {os.path.basename(video)}")
    fps = fps_fraction(cap.get(cv2.CAP_PROP_FPS))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    n = 0
    width = height = None
    src_w = src_h = None
    try:
        with open(out, "wb") as f:
            while True:
                if max_frames and n >= max_frames:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                h, w = frame.shape[:2]
                if width is None:
                    src_w, src_h = w, h
                    width, height = w - (w % 2), h - (h % 2)
                    if width <= 0 or height <= 0:
                        raise ValueError(f"frame too small: {w}x{h}")
                    f.write(f"YUV4MPEG2 W{width} H{height} F{fps.numerator}:{fps.denominator} Ip A1:1 C420jpeg\n"
                            .encode("ascii"))
                elif (w, h) != (src_w, src_h):
                    raise ValueError(f"frame size changed inside the video: {src_w}x{src_h} -> {w}x{h}")
                yuv = cv2.cvtColor(frame[:height, :width], cv2.COLOR_BGR2YUV_I420)
                f.write(b"FRAME\n")
                f.write(yuv.tobytes())
                n += 1
    finally:
        cap.release()
    if n == 0:
        if os.path.exists(out):
            os.remove(out)
        raise ValueError("no frame could be read from the video")
    return {"frames": n, "width": width, "height": height, "source_width": src_w, "source_height": src_h,
            "fps_num": fps.numerator, "fps_den": fps.denominator, "fps": float(fps),
            "bytes": os.path.getsize(out)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, help="y4m path OUTSIDE the repository")
    ap.add_argument("--max-frames", type=int, default=0, help="0 = every frame")
    args = ap.parse_args(argv)
    info = write_y4m(args.video, args.out, args.max_frames)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
