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

# ---------------- A. motion re-arm with a lower separate threshold X: joins reached vs repeats inside held letters
rearm_ms = cfg["rearm_move_ms"]


def longest_above(ts, M, X, lo=0, hi=None):
    best, since = 0.0, None
    for i in range(lo, len(M) if hi is None else hi):
        if M[i] is not None and M[i] >= X:
            since = ts[i] if since is None else since
            best = max(best, ts[i] - since)
        else:
            since = None
    return best


motion_rearm = {}
L = seqs_all["L"]
streams = {j: [rc.build_concatenated_sequence(s["clips"], j)[0] for s in L] for j in (0, 300, 600)}
Ms = {j: [stream_motion(sd) for sd in streams[j]] for j in streams}
single_M = []
for c in clips:
    if c["kind"] != "letter":
        continue
    sd = {"raw": c["raw"], "detected": c["detected"], "handedness": c["handedness"],
          "timestamps_ms": np.arange(len(c["detected"])) * 1000.0 / c["fps"], "width": c["width"],
          "height": c["height"]}
    single_M.append((sd["timestamps_ms"], stream_motion(sd)))
for X in (1.0, 1.5, 2.0, cfg["still_speed"], cfg["move_speed"]):
    r = {}
    for j in (300, 600):
        hit = tot = 0
        for sd, M in zip(streams[j], Ms[j]):
            src = sd["frame_sources"]
            i = 0
            while i < len(src):
                if src[i] == "join":
                    k = i
                    while k < len(src) and src[k] == "join":
                        k += 1
                    # window: join frames + up to 300 ms of the next clip start
                    hi = min(len(src), k + int(round(0.3 * sd["fps"])))
                    tot += 1
                    hit += longest_above(sd["timestamps_ms"], M, X, i, hi) >= rearm_ms
                    i = k
                else:
                    i += 1
        r[f"join{j}_share_rearmed"] = hit / tot
    # repeat risk: inside one letter clip, after its first 400 ms, a run M >= X of >= rearm_move_ms
    rep = [longest_above(ts, M, X, int(np.searchsorted(ts, 400.0))) >= rearm_ms for ts, M in single_M]
    r["letter_clips_share_with_run_after_400ms"] = float(np.mean(rep))
    motion_rearm[f"X={X:.4g}"] = r
out["motion_rearm_lower_threshold"] = {"rearm_move_ms": rearm_ms, "n_letter_clips": len(single_M), **motion_rearm}

# ---------------- B. decoders on L (join 0/300/600), single clips (multi), T and O sequences
grid = []
settings = [(1000, 0.8, 300), (1000, 0.9, 300), (1000, 0.8, 400), (1500, 0.9, 300)]
cache = {}
for j in (0, 300, 600):
    for win in sorted({s[0] for s in settings}):
        cache[(j, win)] = [window_probs(sd, win) for sd in streams[j]]
for win, conf, stable in settings:
    for need_still in (False, True):
        row = {"window_ms": win, "conf": conf, "stable_ms": stable, "need_still": need_still}
        for j in (0, 300, 600):
            n_clip = n_one = n_garb = ed = rl = 0
            for sd, M, P in zip(streams[j], Ms[j], cache[(j, win)]):
                em = decode(P, sd["timestamps_ms"], M, conf, stable, need_still)
                exp = [ref[c["sample_id"]] for c in sd["kept_clips"]]
                exp_c = [l for i, l in enumerate(exp) if i == 0 or l != exp[i - 1]]
                ed += lev([lab for _, lab in em], exp_c)
                rl += len(exp_c)
                per = Counter()
                for i, lab in em:
                    si = sd["frame_sources"][i]
                    if si == "join" or lab != exp[si]:
                        n_garb += 1
                    else:
                        per[si] += 1
                n_clip += len(exp)
                n_one += sum(per[i] == 1 for i in range(len(exp)))
            row[f"L{j}"] = {"one_rate": round(n_one / n_clip, 4), "garbage_per_clip": round(n_garb / n_clip, 4),
                            "token_error_rate": round(ed / rl, 4)}
        # single clips: number of emissions per clip (all hauuto, letters and tones)
        multi = Counter()
        for kind in ("letter", "tone"):
            n = m0 = m2 = ok1 = 0
            for c in clips:
                if c["kind"] != kind:
                    continue
                sd = {"raw": c["raw"], "detected": c["detected"], "handedness": c["handedness"],
                      "timestamps_ms": np.arange(len(c["detected"])) * 1000.0 / c["fps"], "width": c["width"],
                      "height": c["height"]}
                key = ("single", c["sample_id"], win)
                if key not in cache:
                    cache[key] = (window_probs(sd, win), stream_motion(sd))
                P, M = cache[key]
                em = decode(P, sd["timestamps_ms"], M, conf, stable, need_still)
                n += 1
                m0 += len(em) == 0
                m2 += len(em) >= 2
                ok1 += len(em) == 1 and em[0][1] == ref[c["sample_id"]]
            row[f"single_{kind}"] = {"n": n, "zero": round(m0 / n, 4), "multi": round(m2 / n, 4),
                                     "one_and_same_label": round(ok1 / n, 4)}
        grid.append(row)
        print(json.dumps(row, ensure_ascii=False))
out["decoders"] = grid

# ---------------- C. QIPEDC held-out (other signer): whole clip vs sliding window on single clips
rows = [r for r in csv.DictReader(open(MANIFEST, encoding="utf-8")) if r["source"] == "qipedc"]
base = os.path.dirname(MANIFEST)
q = {"n": 0, "whole_correct": 0, "too_few": 0}
qdec = Counter()
for r in rows:
    with np.load(os.path.join(base, r["landmark_path"])) as z:
        c = {"raw": np.asarray(z["raw_landmarks"], np.float32), "detected": np.asarray(z["detected_mask"], bool),
             "handedness": [str(h) for h in z["handedness_label"]], "width": int(r["width"]),
             "height": int(r["height"]), "fps": float(r["fps"])}
    if c["detected"].sum() < mdf:
        q["too_few"] += 1
        continue
    q["n"] += 1
    lab, _ = whole_label(c)
    q["whole_correct"] += clf.classes[lab] == r["symbol"]
    sd = {**c, "timestamps_ms": np.arange(len(c["detected"])) * 1000.0 / c["fps"]}
    for win, conf, stable in settings:
        P, M = window_probs(sd, win), stream_motion(sd)
        for need_still in (False, True):
            em = decode(P, sd["timestamps_ms"], M, conf, stable, need_still, det=sd["detected"])
            k = f"w{win}_c{conf}_s{stable}_still{int(need_still)}"
            qdec[k + "_emits"] += len(em)
            qdec[k + "_has_correct"] += any(clf.classes[l] == r["symbol"] for _, l in em)
            qdec[k + "_whole_label_emitted"] += any(l == lab for _, l in em)
out["qipedc"] = {**q, "decoder_counts": dict(qdec)}
print(json.dumps(out["qipedc"], ensure_ascii=False, indent=1))
print(json.dumps(out["motion_rearm_lower_threshold"], indent=1))
with open("docs/plans/15-lan-sua-4-do/measure2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
