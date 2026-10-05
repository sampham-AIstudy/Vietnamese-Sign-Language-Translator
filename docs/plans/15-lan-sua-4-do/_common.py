"""Planner measurements part 2 (plan 15 lần sửa 4): motion re-arm risk, combined decoder, single clips, QIPEDC held-out.
Run from repo root: PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze2.py
"""
import csv
import json
import os
import sys
from collections import Counter

import numpy as np
import torch

ROOT = os.getcwd()
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from src.inference.level1_core import Level1Classifier, load_level1_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter  # noqa: E402
from src.data.alphabet_preprocessing import alphabet_clip_features  # noqa: E402
import level1_rearm_check as rc  # noqa: E402

MANIFEST = "data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv"
cfg = dict(load_level1_config("configs/level1_realtime.json")["values"])
clf = Level1Classifier.from_checkpoint("checkpoints/alphabet_best.pt")
mdf, prep = clf.min_detected_frames, clf.preprocessing
out = {"note": "planner light measurement; hauuto = train clips of the deployed checkpoint (optimistic); qipedc = "
               "46 alphabet clips of one other signer, not in train; synthetic concatenation; not accuracy"}


def stream_motion(sd):
    seg = Level1SignSegmenter(cfg, mdf)
    M = []
    for i in range(len(sd["detected"])):
        lms = sd["raw"][i] if sd["detected"][i] else None
        seg.push(float(sd["timestamps_ms"][i]), lms, sd["handedness"][i] if lms is not None else "", sd["width"],
                 sd["height"])
        M.append(seg.motion if lms is not None else None)
    return M


def window_probs(sd, win_ms):
    T, ts = len(sd["detected"]), sd["timestamps_ms"]
    feats, idx = [], []
    for e in range(T):
        if not sd["detected"][e]:
            continue
        s = int(np.searchsorted(ts, ts[e] - win_ms + 1e-6))
        det = sd["detected"][s:e + 1]
        if det.sum() < mdf:
            continue
        feats.append(alphabet_clip_features(sd["raw"][s:e + 1], det, sd["handedness"][s:e + 1],
                                            sd["width"] / sd["height"], ts[s:e + 1], prep, clf.model_type))
        idx.append(e)
    P = np.full((T, len(clf.classes)), np.nan)
    if feats:
        with torch.no_grad():
            P[idx] = torch.softmax(clf.model(torch.from_numpy(np.stack(feats)).float()), -1).numpy()
    return P


def decode(P, ts, M, conf, stable_ms, need_still, det=None, lost_ms=300.0):
    """label-change decoder; need_still: also M_t <= still_speed during the stable run. Hand lost >= lost_ms
    resets `last` (same letter may be emitted again after the hand leaves)."""
    em, last, run_lab, run_since, last_hand = [], None, None, None, None
    for i in range(len(P)):
        if det is not None and not det[i]:
            if last_hand is not None and ts[i] - last_hand >= lost_ms:
                last, run_lab = None, None
            continue
        last_hand = ts[i]
        if np.isnan(P[i, 0]):
            continue
        k = int(np.argmax(P[i]))
        ok = P[i, k] >= conf and (not need_still or (M[i] is not None and M[i] <= cfg["still_speed"]))
        lab = k if ok else None
        if lab is None or lab != run_lab:
            run_lab, run_since = lab, ts[i]
        if lab is not None and ts[i] - run_since >= stable_ms and lab != last:
            em.append((i, lab))
            last = lab
    return em


def lev(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[-1]


def whole_label(c):
    ts = np.arange(len(c["detected"])) * 1000.0 / c["fps"]
    f = alphabet_clip_features(c["raw"], c["detected"], c["handedness"], c["width"] / c["height"], ts, prep,
                               clf.model_type)
    with torch.no_grad():
        p = torch.softmax(clf.model(torch.from_numpy(f).unsqueeze(0).float()), -1)[0]
    return int(torch.argmax(p)), float(p.max())


loaded = rc.load_and_prepare_manifest_clips(MANIFEST, mdf)
clips = loaded["clips"]
seqs_all = rc.build_candidate_sequences(clips)
ref = {c["sample_id"]: whole_label(c)[0] for c in clips}

