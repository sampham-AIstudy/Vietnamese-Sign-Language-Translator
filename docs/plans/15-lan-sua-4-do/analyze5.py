"""Planner measurement part 5: option 1 decoder + variant-replace rule (a->ă/â, e->ê, o->ô/ơ, u->ư, d->đ: a new stable
label that is the diacritic variant of the last emitted label, within the same hand run, REPLACES it), and where the
extra emissions in single clips come from. Run: PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze5.py"""
import json
from collections import Counter
exec(open("docs/plans/15-lan-sua-4-do/_common.py").read())
VAR = {"ă": "a", "â": "a", "ê": "e", "ô": "o", "ơ": "o", "ư": "u", "đ": "d"}
C = clf.classes

def decode_r(P, ts, conf, stable, det, replace, lost_ms=300.0):
    em, last, run_lab, run_since, last_hand = [], None, None, None, None
    for i in range(len(P)):
        if not det[i]:
            if last_hand is not None and ts[i] - last_hand >= lost_ms:
                last, run_lab = None, None
            continue
        last_hand = ts[i]
        if np.isnan(P[i, 0]):
            continue
        k = int(np.argmax(P[i])); lab = k if P[i, k] >= conf else None
        if lab is None or lab != run_lab:
            run_lab, run_since = lab, ts[i]
        if lab is not None and ts[i] - run_since >= stable and lab != last:
            if replace and em and last is not None and VAR.get(C[lab]) == C[last]:
                em[-1] = (i, lab)  # replace base letter by its diacritic variant
            else:
                em.append((i, lab))
            last = lab
    return em

loaded = rc.load_and_prepare_manifest_clips(MANIFEST, mdf); clips = loaded["clips"]
L = rc.build_candidate_sequences(clips)["L"]
ref = {}
for c in clips:
    sd = {**c, "timestamps_ms": np.arange(len(c["detected"])) * 1000.0 / c["fps"]}
    ref[c["sample_id"]] = int(np.argmax(window_probs(sd, 1e9)[len(c["detected"]) - 1])) if True else None
res = {}
for win, conf, stable in [(1000, 0.9, 300), (1000, 0.8, 300), (1500, 0.9, 300)]:
    for replace in (False, True):
        row = {}
        for j in (0, 300, 600):
            n = one = garb = 0
            for s in L:
                sd, _ = rc.build_concatenated_sequence(s["clips"], j)
                em = decode_r(window_probs(sd, win), sd["timestamps_ms"], conf, stable, sd["detected"], replace)
                exp = [ref[c["sample_id"]] for c in sd["kept_clips"]]
                per = Counter()
                for i, lab in em:
                    si = sd["frame_sources"][i]
                    if si == "join" or lab != exp[si]: garb += 1
                    else: per[si] += 1
                n += len(exp); one += sum(per[k] == 1 for k in range(len(exp)))
            row[f"L{j}"] = {"one_rate": round(one / n, 4), "garbage_per_clip": round(garb / n, 4)}
        extra = Counter()
        for kind in ("letter", "tone"):
            cnt = Counter()
            for c in clips:
                if c["kind"] != kind: continue
                sd = {**c, "timestamps_ms": np.arange(len(c["detected"])) * 1000.0 / c["fps"]}
                em = decode_r(window_probs(sd, win), sd["timestamps_ms"], conf, stable, sd["detected"], replace)
                cnt["n"] += 1; cnt["one"] += len(em) == 1; cnt["multi"] += len(em) >= 2; cnt["zero"] += len(em) == 0
                if len(em) >= 2:
                    extra[f"{C[em[0][1]]}->{C[em[-1][1]]} ({c['symbol']})"] += 1
            row[f"single_{kind}"] = {k: (v if k == "n" else round(v / cnt["n"], 4)) for k, v in cnt.items()}
        row["top_multi_patterns"] = extra.most_common(15)
        key = f"w{win}_c{conf}_s{stable}_replace{int(replace)}"
        res[key] = row
        print(key, json.dumps(row, ensure_ascii=False), flush=True)
json.dump(res, open("docs/plans/15-lan-sua-4-do/measure5.json", "w"), ensure_ascii=False, indent=1)
