"""
Side-by-side landmark rendering of the same word in VSL-GH (segment) and QIPEDC (dictionary clip), to check
whether the two sources sign it the same way (step 3 of the source investigation).

Per word: <out>/<word>.png  row 1 VSL-GH skeleton, row 2 QIPEDC skeleton (frames with a hand), row 3 QIPEDC video
          <out>/<word>.mp4  VSL-GH | QIPEDC skeletons animated side by side (both resampled to the same length)
Skeletons: aspect-corrected, centred on mid-shoulder, scaled by shoulder width; right hand red, left hand blue.
Usage: python scripts/render_cross_source.py --words "hỏi" "giấy" ... --out <dir>
"""
import argparse
import os
import sys

import cv2
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
ARMS = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24)]
HAND = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
S = 240  # tile size


def load(path, aspect):
    d = np.load(path)
    k = d["keypoints"].astype(np.float32)
    v = d["visibility_mask"].astype(np.float32) > 0.5
    k[~v] = np.nan
    k[..., 0] *= aspect
    mid = np.nanmean((k[:, 11, :2] + k[:, 12, :2]) / 2, 0)
    sw = np.nanmedian(np.linalg.norm(k[:, 11, :2] - k[:, 12, :2], axis=1))
    return (k[..., :2] - mid) / sw, v


def draw(pts, title):
    img = np.full((S, S, 3), 255, np.uint8)
    P = lambda i: pts[i] * (S / 5.0) + np.array([S / 2, S * 0.35])  # 5 shoulder widths across
    def line(a, b, col, w):
        pa, pb = P(a), P(b)
        if np.isfinite(pa).all() and np.isfinite(pb).all():
            cv2.line(img, tuple(int(x) for x in pa), tuple(int(x) for x in pb), col, w, cv2.LINE_AA)
    for a, b in ARMS:
        line(a, b, (150, 150, 150), 2)
    for off, col in ((46, (40, 40, 220)), (25, (220, 90, 40))):  # right hand red, left hand blue (BGR)
        for a, b in HAND:
            line(off + a, off + b, col, 1)
    cv2.putText(img, title, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    return img


def pick(v, n):
    idx = np.flatnonzero(v[:, 25:].any(1))
    idx = idx if len(idx) >= n else np.arange(len(v))
    return idx[np.linspace(0, len(idx) - 1, n).round().astype(int)]


def video_frames(fname, idx):
    cap = cv2.VideoCapture(os.path.join("data", "Dataset", "Videos", fname))
    out = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        f = cv2.resize(f, (S * 16 // 9, S))[:, (S * 16 // 9 - S) // 2:][:, :S] if ok else np.zeros((S, S, 3), np.uint8)
        out.append(f)
    cap.release()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    seg = pd.read_csv("data/processed/vslgh_segments/segments.csv")
    test = pd.read_csv("data/splits/unified/test.csv")
    for w in args.words:
        s = seg[(seg.label == w) & (seg.signer_id == "S01")].sort_values("video_id")
        q = test[(test.source == "qipedc") & (test.gloss_normalized == w)]
        q = q[[os.path.exists(os.path.join("data/processed", p)) for p in q.npz_path]]
        if s.empty or q.empty:
            print("skip", w); continue
        s, q = s.iloc[len(s) // 2], q.iloc[0]
        a, av = load(s.npz_path, s.width / s.height)
        b, bv = load(os.path.join("data/processed", q.npz_path), q.width / q.height)
        ia, ib = pick(av, args.n), pick(bv, args.n)
        rows = [np.hstack([draw(a[i], f"VSL-GH {s.video_id[-16:]} f{i}") for i in ia]),
                np.hstack([draw(b[i], f"QIPEDC {q.file_name} f{i}") for i in ib]),
                np.hstack(video_frames(q.file_name, ib))]
        safe = w.replace(" ", "_")
        cv2.imencode(".png", np.vstack(rows))[1].tofile(os.path.join(args.out, f"{safe}.png"))
        n = 48
        fa, fb = np.linspace(0, len(a) - 1, n).round().astype(int), np.linspace(0, len(b) - 1, n).round().astype(int)
        vw = cv2.VideoWriter(os.path.join(args.out, f"{safe}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 12, (2 * S, S))
        for i, j in zip(fa, fb):
            vw.write(np.hstack([draw(a[i], f"VSL-GH {w}"), draw(b[j], f"QIPEDC {w}")]))
        vw.release()
        print("ok", w, s.video_id, q.file_name, len(a), len(b))


if __name__ == "__main__":
    main()
