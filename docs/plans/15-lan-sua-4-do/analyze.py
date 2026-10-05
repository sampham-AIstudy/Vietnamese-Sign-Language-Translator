"""Planner measurements for plan 15 lần sửa 4 (NOT committed code; outputs a JSON summary for the plan).

Train clips of the deployed checkpoint (hauuto) => optimistic for anything involving the classifier; logic check only.
Run from repo root:  PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze.py
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import torch

ROOT = os.getcwd()
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from src.inference.level1_core import Level1Classifier, load_level1_config  # noqa: E402
from src.inference.level1_segmenter import Level1SignSegmenter, pose_distance  # noqa: E402
from src.data.alphabet_preprocessing import alphabet_clip_features  # noqa: E402
import level1_rearm_check as rc  # noqa: E402
import level1_segment_report as sr  # noqa: E402

MANIFEST = "data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv"
CKPT = "checkpoints/alphabet_best.pt"
OUT = "docs/plans/15-lan-sua-4-do/measure.json"


def pct(v, qs=(5, 10, 50, 90, 95)):
    a = np.asarray([x for x in v if x is not None], dtype=np.float64)
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), **{f"p{q}": float(np.percentile(a, q)) for q in qs}}


cfg = dict(load_level1_config("configs/level1_realtime.json")["values"])
clf = Level1Classifier.from_checkpoint(CKPT)
mdf = clf.min_detected_frames
prep = clf.preprocessing
out = {"note": "planner light measurement on TRAIN clips of the deployed checkpoint (hauuto); concatenated streams "
               "are synthetic; not accuracy", "config_sha_note": "configs/level1_realtime.json at HEAD"}

# ---------------------------------------------------------------- 1. motion during a synthetic letter->letter join
loaded = rc.load_and_prepare_manifest_clips(MANIFEST, mdf)
clips = loaded["clips"]
seqs = rc.build_candidate_sequences(clips)["L"]
join_motion = {}
for join in (300, 600):
    vals_med, vals_max = [], []
    for s in seqs:
        sd, _ = rc.build_concatenated_sequence(s["clips"], join)
        seg = Level1SignSegmenter(cfg, mdf)
        src = sd["frame_sources"]
        cur = []
        for i in range(len(src)):
            seg.push(float(sd["timestamps_ms"][i]), sd["raw"][i], sd["handedness"][i], sd["width"], sd["height"])
            if src[i] == "join":
                cur.append(seg.motion)
            elif cur:
                c = [x for x in cur if x is not None]
                if c:
                    vals_med.append(float(np.median(c)))
                    vals_max.append(float(np.max(c)))
                cur = []
    join_motion[str(join)] = {
        "median_M_in_join": pct(vals_med), "max_M_in_join": pct(vals_max),
        "share_joins_max_ge_move_speed": float(np.mean(np.asarray(vals_max) >= cfg["move_speed"])),
        "share_joins_max_le_still_speed": float(np.mean(np.asarray(vals_max) <= cfg["still_speed"])),
        "n_joins": len(vals_max)}
out["join_motion"] = {"still_speed": cfg["still_speed"], "move_speed": cfg["move_speed"], **join_motion}

# within-clip motion of letter clips (the real, recorded movement)
mot_all, mot_max = [], []
for c in clips:
    if c["kind"] != "letter":
        continue
    ts = sr.clip_timestamps(len(c["detected"]), c["fps"])
    m = sr.motion_series(c["raw"], c["detected"], c["handedness"], c["width"], c["height"], ts, cfg, mdf)
    mm = [x for x in m if x is not None]
    if mm:
        mot_max.append(max(mm))
        mot_all.extend(mm)
out["letter_clip_motion"] = {"M_t_all_frames": pct(mot_all), "M_t_max_per_clip": pct(mot_max)}

# ---------------------------------------------------------------- 2. pose separability (why P2 fails)
pc = [sr.clip_pose_profile(c, cfg, mdf) for c in sr.load_train_clips(MANIFEST, mdf)["clips"] if c["kind"] == "letter"]
jit_by_sym = defaultdict(list)
for p in pc:
    if p["has_still"]:
        jit_by_sym[p["symbol"]].append(p["jitter_clip"])
out["pose"] = {"jitter_clip_median_by_symbol": {k: float(np.median(v)) for k, v in sorted(jit_by_sym.items())},
               "jitter_clip_all": pct([p["jitter_clip"] for p in pc if p["has_still"]])}
# nearest other letter per (session, letter) vs that clip's own jitter
refs = defaultdict(dict)
for p in sorted(pc, key=lambda p: p["sample_id"]):
    if p["has_still"] and p["symbol"] not in refs[(p["signer_id"], p["session"])]:
        refs[(p["signer_id"], p["session"])][p["symbol"]] = p
ratio, nn = [], []
for key, d in refs.items():
    for a, pa in d.items():
        dmin = min(pose_distance(pa["ref"], pb["ref"]) for b, pb in d.items() if b != a)
        nn.append(dmin)
        ratio.append(dmin / max(pa["jitter_clip"], 1e-9))
out["pose"]["nearest_other_letter_dist"] = pct(nn)
out["pose"]["nearest_over_own_jitter"] = pct(ratio)
out["pose"]["share_nearest_over_own_jitter_ge_2"] = float(np.mean(np.asarray(ratio) >= 2.0))

# ---------------------------------------------------------------- 3. classifier cost
seg_dummy = clips[0]
x = torch.zeros((1, 30, 63))
with torch.no_grad():
    for _ in range(5):
        clf.model(x)
    t = []
    for _ in range(200):
        t0 = time.perf_counter()
        clf.model(x)
        t.append((time.perf_counter() - t0) * 1000)
feat_t = []
for _ in range(200):
    c = seg_dummy
    n = min(24, len(c["detected"]))
    t0 = time.perf_counter()
    alphabet_clip_features(c["raw"][:n], c["detected"][:n], c["handedness"][:n], c["width"] / c["height"],
                           sr.clip_timestamps(n, c["fps"]), prep, clf.model_type)
    feat_t.append((time.perf_counter() - t0) * 1000)
push_t = []
seg = Level1SignSegmenter(cfg, mdf)
ts0 = sr.clip_timestamps(len(seg_dummy["detected"]), seg_dummy["fps"])
for i in range(len(ts0)):
    t0 = time.perf_counter()
    seg.push(float(ts0[i]), seg_dummy["raw"][i], seg_dummy["handedness"][i], seg_dummy["width"], seg_dummy["height"])
    push_t.append((time.perf_counter() - t0) * 1000)
out["cost_ms_this_cloud_cpu"] = {"model_forward_1x30x63": pct(t, (50, 95)), "features_24_frames": pct(feat_t, (50, 95)),
                                 "segmenter_push": pct(push_t, (50, 95)), "torch_threads": torch.get_num_threads()}


# ---------------------------------------------------------------- 4. sliding-window classifier on concatenated L
def window_probs(sd, win_ms, stride):
    """probs [T, C] (nan rows where not evaluated / too few frames) for windows ending at each frame."""
    T = len(sd["detected"])
    ts = sd["timestamps_ms"]
    feats, idx = [], []
    for e in range(0, T, stride):
        s = int(np.searchsorted(ts, ts[e] - win_ms + 1e-6))
        det = sd["detected"][s:e + 1]
        if det.sum() < mdf:
            continue
        f = alphabet_clip_features(sd["raw"][s:e + 1], det, sd["handedness"][s:e + 1], sd["width"] / sd["height"],
                                   ts[s:e + 1], prep, clf.model_type)
        feats.append(f)
        idx.append(e)
    P = np.full((T, len(clf.classes)), np.nan)
    if feats:
        with torch.no_grad():
            pr = torch.softmax(clf.model(torch.from_numpy(np.stack(feats)).float()), dim=-1).numpy()
        P[idx] = pr
    return P


def decode(P, ts, conf, stable_ms):
    """emit label when argmax==L with p>=conf continuously for >= stable_ms and L != last emitted."""
    emitted, last, run_lab, run_since = [], None, None, None
    for i in range(len(P)):
        if np.isnan(P[i, 0]):
            continue
        k = int(np.argmax(P[i]))
        ok = P[i, k] >= conf
        lab = k if ok else None
        if lab is None or lab != run_lab:
            run_lab, run_since = lab, ts[i]
        if lab is not None and ts[i] - run_since >= stable_ms and lab != last:
            emitted.append((i, lab))
            last = lab
    return emitted


def whole_clip_label(c):
    ts = sr.clip_timestamps(len(c["detected"]), c["fps"])
    f = alphabet_clip_features(c["raw"], c["detected"], c["handedness"], c["width"] / c["height"], ts, prep,
                               clf.model_type)
    with torch.no_grad():
        return int(torch.argmax(clf.model(torch.from_numpy(f).unsqueeze(0).float())))


ref_label = {c["sample_id"]: whole_clip_label(c) for s in seqs for c in s["clips"]}
truth_ok = np.mean([clf.classes[ref_label[c["sample_id"]]] == c["symbol"] for s in seqs for c in s["clips"]])
out["whole_clip_train_agreement_with_symbol"] = float(truth_ok)


def lev(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[-1]


grid = []
for join in (0, 300):
    built = [rc.build_concatenated_sequence(s["clips"], join)[0] for s in seqs]
    for win in (600, 1000, 1500):
        Ps = [window_probs(sd, win, 1) for sd in built]
        for conf in (0.6, 0.8, 0.9):
            for stable in (200, 400):
                n_clip = n_one = n_garb = 0
                ed, ref_len = 0, 0
                for s, sd, P in zip(seqs, built, Ps):
                    em = decode(P, sd["timestamps_ms"], conf, stable)
                    src = sd["frame_sources"]
                    exp = [ref_label[c["sample_id"]] for c in sd["kept_clips"]]
                    # collapse consecutive equal expected labels (label-change decoder cannot repeat)
                    exp_c = [l for i, l in enumerate(exp) if i == 0 or l != exp[i - 1]]
                    got = [lab for _, lab in em]
                    ed += lev(got, exp_c)
                    ref_len += len(exp_c)
                    per_clip = Counter()
                    for i, lab in em:
                        si = src[i]
                        if si == "join" or lab != ref_label[sd["kept_clips"][si]["sample_id"]]:
                            # emitted while frames of clip si (or join) are the latest: label wrong for that clip
                            # -> may still be the previous letter carried over; count as garbage
                            n_garb += 1
                        else:
                            per_clip[si] += 1
                    n_clip += len(sd["kept_clips"])
                    n_one += sum(1 for i in range(len(sd["kept_clips"])) if per_clip[i] == 1)
                grid.append({"join_ms": join, "window_ms": win, "conf": conf, "stable_ms": stable,
                             "one_rate": n_one / n_clip, "garbage_per_clip": n_garb / n_clip,
                             "token_error_rate": ed / ref_len, "n_clips": n_clip})
out["sliding_window_L"] = grid

# baseline: current segmenter (pose rules off) on the same streams, label of emitted segments
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "sliding_window_L"}, ensure_ascii=False, indent=1))
for g in sorted(grid, key=lambda g: g["token_error_rate"])[:12]:
    print(g)
