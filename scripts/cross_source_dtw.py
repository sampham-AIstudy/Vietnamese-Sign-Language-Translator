"""
Do VSL-GH and QIPEDC sign the same words the same way? Hands-only nearest-neighbour test with DTW
(step 3 of the source investigation). No body landmarks, no clip length: each clip is trimmed to its active
part (trim_rest_eval.active_span), resampled to 32 frames, and described per frame by the dominant (right)
hand wrist position relative to the shoulders + its wrist-centred hand shape, and the left wrist position.

Pool   : VSL-GH segments of training signers S01-S04 (up to --per-word per word, all VSL-GH words)
Queries: cross_source  QIPEDC clips of words that exist in VSL-GH (local keypoints)
         s06           reference: VSL-GH S06 segments of the same words (same source, unseen signer)
Reports the rank of the correct word (best DTW over its pool segments) and top-1/top-5 NN accuracy per set,
and per cross-source word the rank + nearest words, to list likely variant differences.
Usage: python scripts/cross_source_dtw.py --out <json>
"""
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
from trim_rest_eval import active_span  # noqa: E402

N = 32
REST_L = np.array([0.8, 2.2])  # left wrist when missing: hanging by the left hip (shoulder-width units)


def describe(path, aspect):
    d = np.load(path)
    k, v = d["keypoints"].astype(np.float32), d["visibility_mask"] > 0.5
    a, b = active_span(k, v)
    k, v = k[a:b].copy(), v[a:b]
    k[~v] = np.nan
    k[..., 0] *= aspect
    mid = np.nanmedian((k[:, 11, :2] + k[:, 12, :2]) / 2, 0)
    sw = np.nanmedian(np.linalg.norm(k[:, 11, :2] - k[:, 12, :2], axis=1))
    rh, lh = k[:, 46:67, :2], k[:, 25:46, :2]
    have = np.isfinite(rh[:, 0, 0])
    if have.sum() < 2:
        return None
    t = np.flatnonzero(have)
    rh = np.stack([np.stack([np.interp(np.arange(len(k)), t, rh[t, j, c]) for c in range(2)], -1) for j in range(21)], 1)
    wrist = (rh[:, 0] - mid) / sw
    size = np.linalg.norm(rh[:, 9] - rh[:, 0], axis=-1)[:, None, None] + 1e-6
    shape = ((rh - rh[:, :1]) / size)[:, 1:].reshape(len(k), -1) * 0.25
    lw = (lh[:, 0] - mid) / sw
    lw = np.where(np.isfinite(lw), lw, REST_L)
    f = np.concatenate([wrist * 2.0, lw, shape], 1)
    idx = np.linspace(0, len(f) - 1, N).round().astype(int)
    return f[idx].astype(np.float32)


def dtw(a, b, band=8):
    c = np.linalg.norm(a[:, None] - b[None], axis=-1)
    D = np.full((N + 1, N + 1), np.inf, np.float32); D[0, 0] = 0
    for i in range(1, N + 1):
        for j in range(max(1, i - band), min(N, i + band) + 1):
            D[i, j] = c[i - 1, j - 1] + min(D[i - 1, j], D[i - 1, j - 1], D[i, j - 1])
    return D[N, N]


def rank_queries(queries, pool):
    out = []
    for q in queries:
        best = defaultdict(lambda: np.inf)
        for p in pool:
            best[p["label"]] = min(best[p["label"]], dtw(q["f"], p["f"]))
        order = sorted(best, key=best.get)
        out.append({"id": q["id"], "label": q["label"], "rank": order.index(q["label"]) + 1 if q["label"] in best else None,
                    "nearest": order[:5]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-word", type=int, default=4)
    args = ap.parse_args()
    seg = pd.read_csv("data/processed/vslgh_segments/segments.csv")
    train = pd.read_csv("data/splits/unified/train.csv")
    test = pd.read_csv("data/splits/unified/test.csv")
    vwords = set(train.loc[train.source == "vslgh", "gloss_normalized"])
    pool_rows = (seg[seg.signer_id.isin(["S01", "S02", "S03", "S04"]) & seg.label.isin(vwords)]
                 .sample(frac=1, random_state=0).groupby("label").head(args.per_word))
    pool = [{"label": r.label, "f": describe(r.npz_path, r.width / r.height)} for r in pool_rows.itertuples()]
    pool = [p for p in pool if p["f"] is not None]
    cross = [{"id": r.video_id, "label": r.gloss_normalized,
              "f": describe(os.path.join("data/processed", r.npz_path), r.width / r.height)}
             for r in test.itertuples() if r.source == "qipedc" and r.gloss_normalized in vwords
             and os.path.exists(os.path.join("data/processed", r.npz_path))]
    words = {c["label"] for c in cross}
    s06_rows = seg[(seg.signer_id == "S06") & seg.label.isin(words)].groupby("label").head(3)
    s06 = [{"id": r.video_id, "label": r.label, "f": describe(r.npz_path, r.width / r.height)} for r in s06_rows.itertuples()]
    res = {"pool_segments": len(pool), "pool_words": len({p["label"] for p in pool})}
    for name, qs in (("cross_source", cross), ("s06_reference", s06)):
        qs = [q for q in qs if q["f"] is not None]
        r = rank_queries(qs, pool)
        ranks = np.array([x["rank"] for x in r])
        res[name] = {"n": len(r), "top1": round(100 * float(np.mean(ranks == 1)), 1), "top5": round(100 * float(np.mean(ranks <= 5)), 1),
                     "median_rank": float(np.median(ranks)), "per_query": r}
        print(name, {k: v for k, v in res[name].items() if k != "per_query"}, flush=True)
    json.dump(res, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    for x in sorted(res["cross_source"]["per_query"], key=lambda x: x["rank"]):
        print(f"  {x['label']:<14} rank {x['rank']:>4}  nearest {x['nearest'][:3]}")


if __name__ == "__main__":
    main()
