"""Planner measurements part 3 (plan 15 lần sửa 4): option 3 = segmenter hold emission kept, re-arm by classifier
label change on a sliding window (simulated by setting the segmenter's private state; analysis only, not product code).
Run: PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze3.py
"""
import csv, json, os, sys
from collections import Counter
import numpy as np, torch
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from src.inference.level1_core import Level1Classifier, load_level1_config
from src.inference.level1_segmenter import Level1SignSegmenter, SignSegment
import level1_rearm_check as rc
exec(open("docs/plans/15-lan-sua-4-do/analyze2.py").read().split("# ---------------- A.")[0].split("loaded = rc.")[0]
     .split("MANIFEST = ")[1].join(["MANIFEST = ", ""]) if False else "")
MANIFEST = "data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv"
cfg = dict(load_level1_config("configs/level1_realtime.json")["values"])
clf = Level1Classifier.from_checkpoint("checkpoints/alphabet_best.pt")
mdf, prep = clf.min_detected_frames, clf.preprocessing
from src.data.alphabet_preprocessing import alphabet_clip_features

def probs_at(sd, e, win):
    ts = sd["timestamps_ms"]; s = int(np.searchsorted(ts, ts[e] - win + 1e-6)); det = sd["detected"][s:e+1]
    if det.sum() < mdf: return None
    f = alphabet_clip_features(sd["raw"][s:e+1], det, sd["handedness"][s:e+1], sd["width"]/sd["height"], ts[s:e+1], prep, clf.model_type)
    with torch.no_grad(): return torch.softmax(clf.model(torch.from_numpy(f).unsqueeze(0).float()), -1)[0].numpy()

def seg_label(seg):
    r = clf.classify(seg, 1); return clf.classes.index(r["prediction"]) if r["status"] == "ok" else None

def run(sd, win, conf, stable, cut_back, use_cls=True):
    seg = Level1SignSegmenter(cfg, mdf); ts = sd["timestamps_ms"]; ev = []
    last_lab = None; run_lab = None; run_since = None; rearms = 0
    for i in range(len(sd["detected"])):
        has = bool(sd["detected"][i])
        out = seg.push(float(ts[i]), sd["raw"][i] if has else None, sd["handedness"][i] if has else "", sd["width"], sd["height"])
        for e in out:
            if isinstance(e, SignSegment):
                lab = seg_label(e); ev.append((i, lab)); last_lab = lab
        if not seg._tracking: last_lab = None; run_lab = None
        if use_cls and has and not seg._armed:
            p = probs_at(sd, i, win)
            lab = int(np.argmax(p)) if p is not None and p.max() >= conf else None
            if lab is None or lab != run_lab: run_lab, run_since = lab, ts[i]
            if lab is not None and lab != last_lab and ts[i] - run_since >= stable:
                seg._armed = True; start = run_since - cut_back
                seg._buf = [f for f in seg._buf if f[3] >= start]; rearms += 1; run_lab = None
        elif seg._armed: run_lab = None
    for e in seg.flush(float(ts[-1]) + 1000.0 / sd["fps"]):
        if isinstance(e, SignSegment): ev.append((len(ts) - 1, seg_label(e)))
    return ev

def lev(a, b):
    d = list(range(len(b)+1))
    for i in range(1, len(a)+1):
        prev, d[0] = d[0], i
        for j in range(1, len(b)+1):
            cur = min(d[j]+1, d[j-1]+1, prev + (a[i-1] != b[j-1])); prev, d[j] = d[j], cur
    return d[-1]

loaded = rc.load_and_prepare_manifest_clips(MANIFEST, mdf); clips = loaded["clips"]
L = rc.build_candidate_sequences(clips)["L"]
def whole(c):
    sd = {**c, "timestamps_ms": np.arange(len(c["detected"]))*1000.0/c["fps"]}
    p = probs_at(sd, len(c["detected"])-1, 1e9); return int(np.argmax(p))
ref = {c["sample_id"]: whole(c) for c in clips}
res = []
for (win, conf, stable, cut_back, use_cls) in [(1000,0.9,300,0,False),(1000,0.9,300,0,True),(1000,0.9,300,300,True),(1000,0.8,300,0,True),(1500,0.9,300,0,True)]:
    row = {"win": win, "conf": conf, "stable": stable, "cut_back": cut_back, "classifier_rearm": use_cls}
    for j in (0, 300, 600):
        n=one=garb=ed=rl=0
        for s in L:
            sd, _ = rc.build_concatenated_sequence(s["clips"], j)
            ev = run(sd, win, conf, stable, cut_back, use_cls)
            exp = [ref[c["sample_id"]] for c in sd["kept_clips"]]
            ed += lev([l for _, l in ev], exp); rl += len(exp)
            per = Counter()
            for i, lab in ev:
                si = sd["frame_sources"][i]
                # attribute to the clip whose frames end the segment (emission frame); join or wrong label = garbage
                if si == "join" or lab != exp[si]: garb += 1
                else: per[si] += 1
            n += len(exp); one += sum(per[k]==1 for k in range(len(exp)))
        row[f"L{j}"] = {"one_rate": round(one/n,4), "garbage_per_clip": round(garb/n,4), "token_error_rate": round(ed/rl,4)}
    for kind in ("letter","tone"):
        cnt = Counter()
        for c in clips:
            if c["kind"] != kind: continue
            sd = {**c, "timestamps_ms": np.arange(len(c["detected"]))*1000.0/c["fps"]}
            ev = run(sd, win, conf, stable, cut_back, use_cls)
            cnt["n"] += 1; cnt["one"] += len(ev)==1; cnt["multi"] += len(ev)>=2
        row[f"single_{kind}"] = {k: (v if k=="n" else round(v/cnt["n"],4)) for k,v in cnt.items()}
    print(json.dumps(row), flush=True); res.append(row)
json.dump(res, open("docs/plans/15-lan-sua-4-do/measure3.json","w"), indent=1)
