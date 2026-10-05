"""Planner check (post hoc, NOT a new rule): P1/P2 if the 6 letters with a diacritic movement (â ê ô ă ơ ư) were left
out of P1, and how many letter pairs are base/diacritic twins. Run: PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze4.py"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from src.inference.level1_core import load_level1_config, Level1Classifier
import level1_segment_report as sr
cfg = dict(load_level1_config("configs/level1_realtime.json")["values"])
mdf = Level1Classifier.from_checkpoint("checkpoints/alphabet_best.pt").min_detected_frames
clips = [c for c in sr.load_train_clips("data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv", mdf)["clips"] if c["kind"] == "letter"]
prof = [sr.clip_pose_profile(c, cfg, mdf) for c in clips]
D = set("âêôăơư")
out = {}
for name, keep in (("all_letters", lambda p: True), ("without_diacritic_letters", lambda p: p["symbol"] not in D)):
    sub = [p for p in prof if keep(p)]
    cal = sr.pose_calibration(sub, 2.0)
    out[name] = {"rearm_pose_dist": cal["values"]["rearm_pose_dist"], "coverage": cal["p2"]["coverage"],
                 "n_pairs": cal["p2"]["n_pairs"]}
# coverage of ALL letter pairs (incl. diacritic letters) at the threshold computed without them
th = out["without_diacritic_letters"]["rearm_pose_dist"]
cal_all = sr.pose_calibration(prof, 2.0)
b = []
from collections import defaultdict
from src.inference.level1_segmenter import pose_distance
refs = defaultdict(dict)
for p in sorted(prof, key=lambda p: p["sample_id"]):
    if p["has_still"] and p["symbol"] not in refs[(p["signer_id"], p["session"])]:
        refs[(p["signer_id"], p["session"])][p["symbol"]] = p["ref"]
for d in refs.values():
    ks = sorted(d)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            b.append(pose_distance(d[ks[i]], d[ks[j]]))
out["coverage_all_pairs_at_threshold_without_diacritics"] = float(np.mean(np.asarray(b) >= th))
print(json.dumps(out, indent=1))
json.dump(out, open("docs/plans/15-lan-sua-4-do/measure4.json", "w"), indent=1)
