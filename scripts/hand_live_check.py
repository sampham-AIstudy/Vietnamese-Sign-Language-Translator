"""
Plan 06 AC6 (and shared helpers of tests/test_hand_live_equivalence.py, AC5): Level 1 live hand landmarks
(WS /ws/hand-landmarks) versus the training extractor, on real clips.

Sample (same as AC5): np.random.default_rng(seed) picks --n-clips hauuto clips of manifest.csv whose video exists
locally (data/external/hauuto_raw/raw/raw/<signer>/<name>.mp4), plus the first 2 qipedc clips (by sample_id) with
data/Dataset/Videos/<id>.mp4. hauuto clips are TRAINING data of the deployed Level 1 model: this is a report on
input drift, not accuracy. No pass threshold for the JPEG and Kaggle comparisons. No landmark is written.

Per clip:
- live_png_vs_local_offline: live path (frames as lossless PNG data URLs) vs _extract_one on this machine.
- live_jpeg90_vs_live_png: frames sent as JPEG quality 90 (the frontend's FS_JPEG_QUALITY; cv2 encoder, not the
  browser's) vs PNG.
- kaggle_npz_vs_local_offline: the landmarks the model was trained on (extracted on Kaggle, Linux) vs this machine.
- sequence_top1: POST /api/fingerspelling/sequence prediction (deployed checkpoint, sha256 checked) of each body.

Usage:
  PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0 \
      --out reports/fingerspell_live_<YYYY-MM-DD>/hand_live_check.json
"""
import argparse
import base64
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (ROOT, os.path.join(ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

KAGGLE_DIR = os.path.join(ROOT, "data", "external", "alphabet_hands_kaggle", "alphabet_hands")
MANIFEST = os.path.join(KAGGLE_DIR, "manifest.csv")
HAUUTO_VIDEO_DIR = os.path.join(ROOT, "data", "external", "hauuto_raw", "raw", "raw")
QIPEDC_VIDEO_DIR = os.path.join(ROOT, "data", "Dataset", "Videos")
EXTRACT_SCRIPT = os.path.join(ROOT, "scripts", "extract_hands_batch.py")
DEPLOYED_CKPT = os.path.join(ROOT, "checkpoints", "alphabet_best.pt")
PROVENANCE_JSON = os.path.join(ROOT, "reports", "alphabet_deploy_2026-09-27", "provenance.json")
WS_PATH = "/ws/hand-landmarks"
SEQ_PATH = "/api/fingerspelling/sequence"
N_QIPEDC = 2
TOP_K = 5
JPEG_QUALITY = 90
NOTE = "report only; hauuto clips are training data of the deployed Level 1 model; not accuracy"


# ---------------------------------------------------------------- sample
def read_manifest(path=MANIFEST):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def video_path_for(row):
    """Local video of a manifest row (the path may not exist). hauuto: sample_id 'hauuto_<name>',
    signer_id 'hauuto_<signer>' -> HAUUTO_VIDEO_DIR/<signer>/<name>.mp4; qipedc: 'qipedc_<id>' ->
    QIPEDC_VIDEO_DIR/<id>.mp4."""
    sid, source = row["sample_id"], row["source"]
    if source == "hauuto":
        signer = row["signer_id"][len("hauuto_"):] if row["signer_id"].startswith("hauuto_") else row["signer_id"]
        name = sid[len("hauuto_"):] if sid.startswith("hauuto_") else sid
        return os.path.join(HAUUTO_VIDEO_DIR, signer, name + ".mp4")
    if source == "qipedc":
        name = sid[len("qipedc_"):] if sid.startswith("qipedc_") else sid
        return os.path.join(QIPEDC_VIDEO_DIR, name + ".mp4")
    raise ValueError(f"unknown source {source!r}")


def hauuto_candidates(rows):
    """hauuto rows with a local video, sorted by sample_id."""
    return sorted((r for r in rows if r["source"] == "hauuto" and os.path.isfile(video_path_for(r))),
                  key=lambda r: r["sample_id"])


def select_clips(rows, n_hauuto, seed, n_qipedc=N_QIPEDC):
    """AC5/AC6 sample: rng(seed) picks n_hauuto of hauuto_candidates (indices sorted) + the first n_qipedc qipedc
    rows (by sample_id) with a local video."""
    cands = hauuto_candidates(rows)
    if len(cands) < n_hauuto:
        raise ValueError(f"only {len(cands)} hauuto clips with a local video (need {n_hauuto})")
    rng = np.random.default_rng(seed)
    picked = [cands[i] for i in sorted(rng.choice(len(cands), n_hauuto, replace=False))]
    qipedc = [r for r in sorted(rows, key=lambda r: r["sample_id"])
              if r["source"] == "qipedc" and os.path.isfile(video_path_for(r))][:n_qipedc]
    return picked + qipedc


# ---------------------------------------------------------------- offline (training extractor)
def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_hands_batch", EXTRACT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def offline_extract(row, tmpdir, extract_module=None):
    """scripts/extract_hands_batch.py::_extract_one (imported, unchanged) on the local video -> npz contents."""
    mod = extract_module or load_extract_module()
    task_row = {"video_path": video_path_for(row), **{k: row[k] for k in ("sample_id", "symbol", "signer_id",
                                                                           "source")}}
    out = os.path.join(tmpdir, row["sample_id"] + ".npz")
    path, status = mod._extract_one((task_row, out))
    if status != "ok":
        raise RuntimeError(f"_extract_one {row['sample_id']}: {status}")
    return load_npz(path)


def load_npz(path):
    with np.load(path) as z:
        return {"raw_landmarks": np.asarray(z["raw_landmarks"], dtype=np.float32),
                "detected_mask": np.asarray(z["detected_mask"], dtype=bool),
                "handedness_label": [str(h) for h in z["handedness_label"]],
                "handedness_score": np.asarray(z["handedness_score"], dtype=np.float32),
                "metadata": json.loads(str(z["metadata"]))}


# ---------------------------------------------------------------- live (WS /ws/hand-landmarks)
def read_video(path):
    """All frames (BGR, as cv2.VideoCapture decodes them) + fps with _extract_one's fallback."""
    import cv2
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {os.path.basename(path)}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    return frames, float(fps)


def encode_data_url(frame, fmt="png"):
    import cv2
    if fmt == "png":
        ok, buf = cv2.imencode(".png", frame)
        mime = "image/png"
    elif fmt == "jpeg90":
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        mime = "image/jpeg"
    else:
        raise ValueError(fmt)
    if not ok:
        raise RuntimeError("encode failed")
    return f"data:{mime};base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def timestamp_ms(i, fps):
    return i * 1000.0 / fps


def live_hand_frames(client, frames, fps, fmt="png"):
    """One recorded sign through WS /ws/hand-landmarks: session_info, one reset (fresh tracker, like a new clip),
    then every frame as a text data URL with timestamp i * 1000 / fps. Returns the hand_frame messages."""
    out = []
    with client.websocket_connect(WS_PATH) as ws:
        first = ws.receive_json()
        if first.get("type") != "session_info":
            raise RuntimeError(f"expected session_info, got {first.get('type')!r}")
        ws.send_json({"type": "control", "action": "reset"})
        done = ws.receive_json()
        if done.get("type") != "reset_done":
            raise RuntimeError(f"expected reset_done, got {done.get('type')!r}")
        for i, frame in enumerate(frames):
            ws.send_json({"image": encode_data_url(frame, fmt), "timestamp": timestamp_ms(i, fps)})
            m = ws.receive_json()
            if m.get("type") != "hand_frame":
                raise RuntimeError(f"frame {i}: expected hand_frame, got {m.get('type')!r} {m.get('code')!r}")
            out.append(m)
    return out


def live_arrays(hand_frames):
    """hand_frame list -> (landmarks float32 [T,21,3] zeros without hand, detected [T], labels, scores float32)."""
    T = len(hand_frames)
    lms = np.zeros((T, 21, 3), dtype=np.float32)
    det = np.zeros(T, dtype=bool)
    labels, scores = [], np.zeros(T, dtype=np.float32)
    for t, m in enumerate(hand_frames):
        if m["landmarks"] is not None:
            lms[t], det[t] = np.asarray(m["landmarks"], dtype=np.float32), True
            scores[t] = np.float32(m["handedness_score"])
        labels.append(m["handedness"])
    return lms, det, labels, scores


# ---------------------------------------------------------------- /sequence bodies
def body_from_hand_frames(hand_frames, top_k=TOP_K):
    """Plan 06 §3.2 buildSequenceBody (Python mirror; the frontend's is frontend/src/lib/fingerspelling.js):
    frames of the last segment, ordered by frame_seq; null without a hand (never an all-zero frame);
    timestamps_ms = client_timestamp; frame size must be constant; source_mirrored false."""
    if not hand_frames:
        raise ValueError("empty")
    seg = hand_frames[-1]["segment_id"]
    frames = sorted((m for m in hand_frames if m["segment_id"] == seg), key=lambda m: m["frame_seq"])
    sizes = {(m["frame_width"], m["frame_height"]) for m in frames}
    if len(sizes) != 1:
        raise ValueError("frame_size_changed")
    (w, h), = sizes
    return {"landmarks": [m["landmarks"] for m in frames],
            "handedness": [m["handedness"] for m in frames],
            "timestamps_ms": [m["client_timestamp"] for m in frames],
            "frame_width": w, "frame_height": h, "source_mirrored": False, "top_k": top_k}


def body_from_npz(npz, width, height, fps, top_k=TOP_K):
    """Body from extracted landmarks, as tests/test_fingerspelling_deployed.body (+ timestamps_ms i * 1000 / fps
    and top_k)."""
    lms, det = npz["raw_landmarks"], npz["detected_mask"]
    return {"landmarks": [f.tolist() if ok else None for f, ok in zip(lms, det)],
            "handedness": list(npz["handedness_label"]),
            "timestamps_ms": [timestamp_ms(i, fps) for i in range(len(det))],
            "frame_width": int(width), "frame_height": int(height), "source_mirrored": False, "top_k": top_k}


# ---------------------------------------------------------------- comparisons
def _max_abs_both(a_lms, a_det, b_lms, b_det):
    both = a_det & b_det
    if not both.any():
        return None
    return float(np.abs(a_lms[both].astype(np.float64) - b_lms[both].astype(np.float64)).max())


def compare(a, b):
    """a, b = (lms, det, ...) -> {n_frames_equal, detected_agree (frames with equal detection flag over the common
    length), detected_equal, max_abs_diff_both (frames detected in both; null if none)}."""
    n = min(len(a[1]), len(b[1]))
    return {"n_frames_equal": len(a[1]) == len(b[1]),
            "detected_agree": int((a[1][:n] == b[1][:n]).sum()),
            "detected_equal": bool(len(a[1]) == len(b[1]) and np.array_equal(a[1], b[1])),
            "max_abs_diff_both": _max_abs_both(a[0][:n], a[1][:n], b[0][:n], b[1][:n])}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def deployed_sha256():
    with open(PROVENANCE_JSON, encoding="utf-8") as f:
        return json.load(f)["checkpoints"]["deployed"]["sha256"]


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def top1(client, body):
    r = client.post(SEQ_PATH, json=body)
    return r.json()["prediction"] if r.status_code == 200 else f"HTTP {r.status_code}"


def check_clip(row, client, extract_module, tmpdir):
    frames, fps = read_video(video_path_for(row))
    off = offline_extract(row, tmpdir, extract_module)
    off_t = (off["raw_landmarks"], off["detected_mask"])
    png = live_hand_frames(client, frames, fps, "png")
    jpg = live_hand_frames(client, frames, fps, "jpeg90")
    png_a, jpg_a = live_arrays(png), live_arrays(jpg)
    kag = load_npz(os.path.join(KAGGLE_DIR, row["landmark_path"]))
    kag_t = (kag["raw_landmarks"], kag["detected_mask"])
    c_png = compare(png_a, off_t)
    c_jpg = compare(jpg_a, png_a)
    c_kag = compare(kag_t, off_t)
    return {
        "sample_id": row["sample_id"],
        "source": row["source"],
        "n_frames": len(frames),
        "n_detected_local_offline": int(off["detected_mask"].sum()),
        "live_png_vs_local_offline": {"detected_equal": c_png["detected_equal"],
                                      "max_abs_diff": c_png["max_abs_diff_both"]},
        "live_jpeg90_vs_live_png": {"detected_agree": c_jpg["detected_agree"],
                                    "max_abs_diff_both": c_jpg["max_abs_diff_both"]},
        "kaggle_npz_vs_local_offline": {"n_frames_equal": c_kag["n_frames_equal"],
                                        "detected_agree": c_kag["detected_agree"],
                                        "max_abs_diff_both": c_kag["max_abs_diff_both"]},
        "sequence_top1": {"live_png": top1(client, body_from_hand_frames(png)),
                          "live_jpeg90": top1(client, body_from_hand_frames(jpg)),
                          "kaggle_npz": top1(client, body_from_npz(kag, row["width"], row["height"],
                                                                   float(row["fps"])))},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n-clips", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import cv2
    import mediapipe
    from fastapi.testclient import TestClient
    import backend.main as api

    sha = sha256_of(DEPLOYED_CKPT)
    if sha != deployed_sha256():
        raise SystemExit(f"checkpoint sha256 {sha} != provenance.json")
    api.ALPHABET_CKPT, api._alphabet_model, api._alphabet_meta = DEPLOYED_CKPT, None, None
    client = TestClient(api.app)  # no `with`: the Level 2 model is not loaded
    rows = select_clips(read_manifest(), args.n_clips, args.seed)
    extract_module = load_extract_module()
    clips = []
    with tempfile.TemporaryDirectory(prefix="vslt_hand_live_check_") as tmpdir:
        for row in rows:
            print(f"[hand_live_check] {row['sample_id']}", flush=True)
            clips.append(check_clip(row, client, extract_module, tmpdir))

    report = {
        "generated_by": {
            "command": "PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/hand_live_check.py "
                       + " ".join(sys.argv[1:]),
            "git_commit": _git("rev-parse", "HEAD"),
            "code_dirty": bool(_git("status", "--porcelain", "--", "src", "scripts", "backend", "tests",
                                    "frontend")),
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mediapipe": mediapipe.__version__, "cv2": cv2.__version__, "numpy": np.__version__,
            "checkpoint": os.path.relpath(DEPLOYED_CKPT, ROOT).replace("\\", "/"), "checkpoint_sha256": sha,
        },
        "note": NOTE,
        "sample": (f"np.random.default_rng({args.seed}) picks {args.n_clips} hauuto clips of manifest.csv with a local "
                   f"video + the first {N_QIPEDC} qipedc clips (by sample_id) with a local video"),
        "definitions": {
            "detected_agree": "frames (over the common length) whose hand-detected flag is equal",
            "max_abs_diff": "max |a - b| of raw landmark coordinates over frames with a hand in both (null if none)",
            "jpeg90": f"cv2.imencode JPEG quality {JPEG_QUALITY} (not the browser encoder)",
            "sequence_top1": f"prediction of POST {SEQ_PATH} (deployed checkpoint); 'HTTP <code>' when not 200",
        },
        "n_clips": len(clips),
        "clips": clips,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(f"[hand_live_check] wrote {args.out}: {len(clips)} clips; live_png == local offline (detected): "
          f"{sum(c['live_png_vs_local_offline']['detected_equal'] for c in clips)}/{len(clips)}")


if __name__ == "__main__":
    main()
