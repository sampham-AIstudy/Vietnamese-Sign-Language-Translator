"""
Plan 04 AC6: how the live SignSegmenter cuts real TRAIN clips, compared with the offline (training) rule.
A report, not a gate: there is no pass threshold, and the segmenter parameters are NOT tuned here.

For each clip of scripts/live_clip_sample.select_train_clips(n, seed) (the AC4 sample):
  - the clip is streamed through HarmonizedLiveSession (real MediaPipe, H-keepz-360 checkpoint, CPU), frames sent
    as lossless PNG through backend.main._decode_frame, t = i / CAP_PROP_FPS; then the last frame is sent again
    ceil((rest_hold_s + 0.2) * fps) times (TEST PADDING, as in AC5, so the segmenter sees hands at rest);
  - reference = finalize_clip() on the clip frames only (the training transform of the whole clip);
  - offline active span = harmonized.active_span on the whole clip (training rule), converted to seconds.
Per clip the JSON records the events (type, reason), whether an emitted segment contains the offline active span,
segment / span durations, and for each sign_result: top-1 equal to the reference or not, top-5 overlap and
|delta confidence| of the top-1. No landmark, frame or video is written.

Usage:
  PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py --n-clips 8 --seed 0 \
      --out reports/live_word_<YYYY-MM-DD>/segment_check.json
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path):
    import cv2
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    return frames, fps


def check_clip(row, predictor, pre, decode, session_cls):
    import cv2
    import numpy as np
    from src.data.harmonized import _normalise, active_span

    frames, fps = _read(row["video_path"])
    session = session_cls(predictor, pre, record_clip=True)
    events = []
    try:
        def send(frame, i):
            ok, buf = cv2.imencode(".png", frame)
            out = session.process(decode(buf.tobytes(), min_height=session.process_height), i / fps)
            if out["event"] is not None:
                events.append(out["event"])

        for i, frame in enumerate(frames):
            send(frame, i)
        ref = session.finalize_clip()                         # clip frames only, before the padding
        n_pad = int(math.ceil((session.segmenter.params["rest_hold_s"] + 0.2) * fps))
        for j in range(n_pad):
            send(frames[-1], len(frames) + j)
    finally:
        session.close()

    ref_pred = predictor.predict(ref["sequence"], ref["joint_mask"], ref["temporal_mask"], top_k=5)
    h, w = frames[0].shape[:2]
    kn, vn = _normalise(ref["keypoints"], ref["visibility_mask"], w / h)
    a, b = active_span(kn, vn, fps, pre)
    t = np.arange(len(frames)) / fps
    span = (float(t[a]), float(t[b - 1]))

    ev_out, contains = [], False
    ref_glosses = [x["gloss"] for x in ref_pred["top5"]]
    for e in events:
        rec = {"type": e["type"], "reason": e.get("reason"), "segment_id": e["segment_id"],
               "duration_s": e["segment"]["duration_s"], "frames": e["segment"]["frames"]}
        if e["type"] == "sign_result":
            seg = e["segment"]
            inside = seg["start_s"] <= span[0] and seg["end_s"] >= span[1]
            contains = contains or inside
            live_glosses = [x["gloss"] for x in e["top5"]]
            rec.update({"start_s": seg["start_s"], "end_s": seg["end_s"],
                        "active_start_s": seg["active_start_s"], "active_end_s": seg["active_end_s"],
                        "contains_offline_span": inside,
                        "live_top1": live_glosses[0], "finalize_top1": ref_glosses[0],
                        "top1_equal_finalize": live_glosses[0] == ref_glosses[0],
                        "top5_overlap": len(set(live_glosses) & set(ref_glosses)),
                        "abs_delta_top1_confidence": abs(e["top5"][0]["confidence"] - ref_pred["top5"][0]["confidence"])})
        ev_out.append(rec)
    return {"video_id": row["video_id"], "n_frames": len(frames), "n_padding_frames": n_pad, "fps": fps,
            "frame_wh": [w, h], "offline_active_span_s": list(span),
            "offline_active_span_duration_s": span[1] - span[0], "contains_offline_span": contains,
            "events": ev_out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-clips", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import cv2
    import mediapipe
    import numpy as np
    import torch
    import backend.main as api
    import live_clip_sample
    from src.inference.harmonized_live import HarmonizedLiveSession
    from src.inference.predictor import VSLPredictor
    from src.inference.sign_segmenter import SEGMENTER_DEFAULT

    ckpt_path = live_clip_sample.H360_CKPT
    sha = _sha256(ckpt_path)
    expected = api.STGCN_VARIANTS["stgcn_h360"]["sha256"]
    if sha != expected:
        raise SystemExit(f"checkpoint sha256 {sha} != expected {expected}")
    pre = torch.load(ckpt_path, map_location="cpu", weights_only=False)["preprocessing"]
    predictor = VSLPredictor(model_type="stgcn", stgcn_ckpt=ckpt_path, device="cpu")
    rows = live_clip_sample.select_train_clips(args.n_clips, args.seed)
    clips = []
    for row in rows:
        print(f"[live_segment_check] {row['video_id']}", flush=True)
        clips.append(check_clip(row, predictor, pre, api._decode_frame, HarmonizedLiveSession))

    report = {
        "generated_by": {
            "command": "PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py "
                       + " ".join(sys.argv[1:]),
            "git_commit": _git("rev-parse", "HEAD"),
            "code_dirty": bool(_git("status", "--porcelain", "--", "src", "scripts", "backend")),
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mediapipe": mediapipe.__version__, "cv2": cv2.__version__, "numpy": np.__version__,
            "checkpoint": os.path.relpath(ckpt_path, ROOT).replace("\\", "/"), "checkpoint_sha256": sha,
            "segmenter_default": SEGMENTER_DEFAULT,
            "sample": f"scripts/live_clip_sample.select_train_clips(n={args.n_clips}, seed={args.seed}) (TRAIN only)",
            "padding": "last frame repeated ceil((rest_hold_s + 0.2) * fps) times after each clip (test padding)",
            "note": "report only: no pass threshold; segmenter parameters not tuned; no landmark stored",
        },
        "n_clips": len(clips),
        "n_contains_offline_span": sum(c["contains_offline_span"] for c in clips),
        "clips": clips,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(f"[live_segment_check] wrote {args.out}: {report['n_contains_offline_span']}/{len(clips)} clips with an "
          f"emitted segment containing the offline active span")


if __name__ == "__main__":
    main()
