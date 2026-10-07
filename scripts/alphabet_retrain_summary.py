#!/usr/bin/env python
"""
Aggregated summary of one scripts/train_alphabet_real.py run (the output of kernel phmvnsm33/vsl-train-alphabet), for
reports/ (no per-clip row: hauuto per-clip files are never committed, docs/data_registry.md §1b).

Reads <run-dir>/alphabet_report.json, <run-dir>/loso_predictions.csv, <run-dir>/alphabet_best.pt and the kernel log
(git commit of the clone), writes:
  - LOSO top-1 of the winner and of both model kinds on whole clips (slices left out) and with slices (older definition);
  - per-class whole-clip LOSO accuracy and the confusion of the diacritic groups (d/đ, a/â/ă, e/ê, o/ô/ơ, u/ư), all
    signers and per signer (user1 = data/collected_targeted, the hauuto signers);
  - QIPEDC external test (whole clips and with slices);
  - sha256 of the checkpoint and of the inputs.
LOSO = leave-one-signer-out over the hauuto signers + user1; the final checkpoint is trained on all of them, so these
numbers describe the recipe, not the checkpoint on unseen data (QIPEDC is the only data the checkpoint never saw).

  python scripts/alphabet_retrain_summary.py --run-dir <kernel output>/alphabet_run --log <kernel output>/<kernel>.log \
      --out reports/alphabet_retrain_2026-10-06/retrain_summary.json
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# confusion groups: the diacritic groups, then p / q (user1 clips added in 8c53795)
DIACRITIC_GROUPS = (("d", "đ"), ("a", "â", "ă"), ("e", "ê"), ("o", "ô", "ơ"), ("u", "ư"), ("p", "q"))
FOCUS = ("d", "đ", "a", "â", "ă", "e", "ê", "o", "ô", "ơ", "u", "ư", "p", "q")


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


def kernel_commit(log_path: str) -> Optional[str]:
    """Commit printed by `git log --oneline -1` of the kernel's clone (first short hash after that command)."""
    with open(log_path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"git log --oneline -1.*?\\n\"\}.*?\"data\":\"([0-9a-f]{7,40}) ", text, re.S)
    return m.group(1) if m else None


def confusion(rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        per[r["true"]][0] += 1
        per[r["true"]][1] += int(r["true"] == r["pred"])
    groups = []
    for g in DIACRITIC_GROUPS:
        groups.append({"symbols": list(g), "confusion": {
            y: dict(Counter(r["pred"] if r["pred"] in g else "other" for r in rows if r["true"] == y)) for y in g}})
    n = len(rows)
    return {"n": n, "top1": (100.0 * sum(int(r["true"] == r["pred"]) for r in rows) / n) if n else None,
            "focus_per_class": {c: {"n": per[c][0], "correct": per[c][1],
                                    "top1": (100.0 * per[c][1] / per[c][0]) if per[c][0] else None}
                                for c in FOCUS if per[c][0]},
            "groups": groups}


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="aggregated summary of a train_alphabet_real.py run")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--kernel-version", default=None)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    with open(os.path.join(a.run_dir, "alphabet_report.json"), encoding="utf-8") as f:
        rep = json.load(f)
    with open(os.path.join(a.run_dir, "loso_predictions.csv"), encoding="utf-8") as f:
        preds = list(csv.DictReader(f))
    winner = rep["winner_by_loso"]
    rows = [r for r in preds if r["kind"] == winner]
    by_signer = {s: confusion([r for r in rows if r["test_signer"] == s])
                 for s in sorted({r["test_signer"] for r in rows})}
    ckpt = os.path.join(a.run_dir, "alphabet_best.pt")
    out = {
        "generated_by": {"command": " ".join(["python", "scripts/alphabet_retrain_summary.py", *argv]),
                         "git_commit": _git("rev-parse", "HEAD"),
                         "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},
        "kernel": {"id": "phmvnsm33/vsl-train-alphabet", "version": a.kernel_version,
                   "clone_commit": kernel_commit(a.log)},
        "note": ("LOSO over the hauuto signers + user1 (data/collected_targeted); the checkpoint is trained on all of "
                 "them, so LOSO describes the recipe; QIPEDC letters are the only data unseen by the checkpoint. "
                 "whole clips = compound slices left out of the test set (they are training items only)."),
        "checkpoint": {"file": "alphabet_best.pt", "sha256": sha256_file(ckpt)},
        "inputs_sha256": {n: sha256_file(os.path.join(a.run_dir, n))
                          for n in ("alphabet_report.json", "loso_predictions.csv")},
        "winner_by_loso": winner,
        "clips": rep.get("clips"), "n_slices": rep.get("n_slices"),
        "per_signer_items": rep.get("per_signer_clip_counts"),
        "loso_top1_whole_clips": rep.get("whole_clip_loso_summary"),
        "loso_top1_with_slices": rep.get("loso_summary"),
        "loso_whole_clips_winner": confusion(rows),
        "loso_whole_clips_winner_by_signer": by_signer,
        "external_qipedc_letters_whole_clips": rep.get("external_qipedc_letters_whole_clips"),
        "external_qipedc_letters_with_slices": rep.get("external_qipedc_letters"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"winner": winner, "whole": out["loso_top1_whole_clips"],
                      "d_dd": out["loso_whole_clips_winner"]["groups"][0]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
