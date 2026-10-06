#!/usr/bin/env python
"""
Level 1 checkpoints compared on whole clips through the app's inference path (Level1Classifier.classify of one
SignSegment per clip, MediaPipe handedness of each frame), aggregated per class (no per-clip row in the output).

Sets (each one a manifest.csv + npz of scripts/extract_hands_batch.py / scripts/collect_targeted_signs.py):
  --set NAME=MANIFEST[:SYMBOLS]   SYMBOLS = comma list of symbols to keep (default: every row); rows with source
                                  'hauuto' are always left out (they are training data of every checkpoint compared)
  --ckpt NAME=PATH                 one or more checkpoints
A set is only a fair test for a checkpoint that never trained on it: say which in --note (written to the JSON).

  python scripts/alphabet_ckpt_compare.py --ckpt old=<old.pt> --ckpt new=checkpoints/alphabet_best.pt \
      --set qipedc=data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv \
      --set user1_new=data/collected_targeted/manifest.csv:đ,ê,ô,ơ,ư --note "..." --out <json>
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.inference.level1_core import Level1Classifier  # noqa: E402
from src.inference.level1_segmenter import SignSegment  # noqa: E402

CODE_PATHS = ("scripts/alphabet_ckpt_compare.py", "src")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args) -> Optional[str]:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def rel(path: str) -> str:
    r = os.path.relpath(os.path.abspath(path), ROOT)
    return (os.path.abspath(path) if r.startswith("..") else r).replace("\\", "/")


def load_set(spec: str) -> Dict[str, Any]:
    name, target = spec.split("=", 1)
    symbols = None
    if ":" in target and not os.path.exists(target):
        target, sym = target.rsplit(":", 1)
        symbols = set(sym.split(","))
    base = os.path.dirname(target)
    with open(target, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["source"] != "hauuto" and (symbols is None or r["symbol"] in symbols)]
    clips = []
    for r in rows:
        z = np.load(os.path.join(base, r["landmark_path"]), allow_pickle=False)
        det = z["detected_mask"].astype(bool)
        ts = np.arange(len(det)) * 1000.0 / float(r["fps"])
        clips.append((r["symbol"], SignSegment(
            seq=1, raw_landmarks=z["raw_landmarks"].astype(np.float32), detected=det,
            handedness=np.where(det, z["handedness_label"].astype(str), ""), timestamps_ms=ts,
            frame_width=int(r["width"]), frame_height=int(r["height"]), t_start_ms=float(ts[0]),
            t_end_ms=float(ts[-1]), t_emit_ms=float(ts[-1]), close_reason="end_of_stream")))
    return {"name": name, "manifest": rel(target), "manifest_sha256": sha256_file(target),
            "symbols": sorted(symbols) if symbols else None, "clips": clips}


def score(clf: Level1Classifier, clips) -> Dict[str, Any]:
    per = defaultdict(Counter)
    for sym, seg in clips:
        r = clf.classify(seg, 1)
        per[sym][r.get("prediction") if r.get("status") == "ok" else None] += 1
    n = sum(sum(c.values()) for c in per.values())
    correct = sum(per[s][s] for s in per)
    return {"n": n, "correct": correct, "top1": (100.0 * correct / n) if n else None,
            "per_class": {s: {"n": sum(c.values()), "correct": c[s], "predicted": dict(c)} for s, c in sorted(per.items())}}


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="compare Level 1 checkpoints on whole clips")
    p.add_argument("--ckpt", action="append", required=True)
    p.add_argument("--set", dest="sets", action="append", required=True)
    p.add_argument("--note", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    sets = [load_set(s) for s in a.sets]
    status = _git("status", "--porcelain", "--", *CODE_PATHS)
    out = {"generated_by": {"command": " ".join(["python", "scripts/alphabet_ckpt_compare.py", *argv]),
                            "git_commit": _git("rev-parse", "HEAD"),
                            "code_dirty": None if status is None else bool(status),
                            "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},
           "note": a.note, "checkpoints": {}, "sets": {s["name"]: {k: s[k] for k in ("manifest", "manifest_sha256",
                                                                                     "symbols")} for s in sets},
           "results": {}}
    for spec in a.ckpt:
        name, path = spec.split("=", 1)
        clf = Level1Classifier.from_checkpoint(path)
        out["checkpoints"][name] = {"path": rel(path), "sha256": sha256_file(path), "n_classes": len(clf.classes)}
        out["results"][name] = {s["name"]: score(clf, s["clips"]) for s in sets}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({c: {s: (r["correct"], r["n"]) for s, r in v.items()} for c, v in out["results"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
