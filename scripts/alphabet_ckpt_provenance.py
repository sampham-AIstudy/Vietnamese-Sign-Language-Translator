"""
Provenance of the Level 1 checkpoint the backend loads (plan 03, Bước 0).

Writes a JSON with, for the deployed checkpoint (default checkpoints/alphabet_best.pt) and the
three checkpoints known to be trained on real hauuto data:
  path, exists, sha256, size_bytes, keys, model_type, selected, epochs, preprocessing, trained_on, classes
plus
  match    name of the known checkpoint with the same sha256 as the deployed one, or null
  verdict  "real_data_known_checkpoint" iff match is not null AND deployed trained_on.source == "hauuto",
           else "UNKNOWN_PROVENANCE"  (rule fixed by the plan; nothing else feeds it)
  state_dict_equal   information only (NOT used by the verdict): for each known checkpoint, whether it
                     has the same state_dict keys and every tensor is torch.equal to the deployed one
  external_reproduction  information only: the deployed model on CPU, offline path of
                     scripts/train_alphabet_nested.load, over the QIPEDC clips; k = clips whose argmax
                     equals the `pred` of run="external" in primary/nested_predictions.csv (the original
                     run trained on cuda). null + reason when the data or the CSV is missing.
The JSON holds counts only: no landmarks, no per-clip ids. Running twice gives the same JSON
except `generated_by`.
Usage: python scripts/alphabet_ckpt_provenance.py --out reports/alphabet_deploy_2026-09-27/provenance.json
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

DEPLOYED = "checkpoints/alphabet_best.pt"
KNOWN = {  # plan 03 §2: checkpoints known to be trained on real (hauuto) data
    "nested_primary": "reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt",
    "nested_variants": "reports/alphabet_nested_2026-09-25/variants/alphabet_nested_final.pt",
    "real_run": "reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt",
}
REAL_DATA = "data/external/alphabet_hands_kaggle/alphabet_hands"
NESTED_PREDICTIONS = "reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv"
FIELDS = ("model_type", "selected", "epochs", "preprocessing", "trained_on", "classes")
REAL_DATA_VERDICT, UNKNOWN_VERDICT = "real_data_known_checkpoint", "UNKNOWN_PROVENANCE"


def _abs(rel):
    return os.path.join(ROOT, *rel.split("/"))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_ckpt(rel):
    return torch.load(_abs(rel), map_location="cpu", weights_only=False)


def describe(rel):
    entry = {"path": rel, "exists": os.path.exists(_abs(rel))}
    if not entry["exists"]:
        return entry, None
    ckpt = load_ckpt(rel)
    entry.update({"sha256": sha256_of(_abs(rel)), "size_bytes": os.path.getsize(_abs(rel)),
                  "keys": sorted(ckpt.keys())})
    for k in FIELDS:
        v = ckpt.get(k)
        entry[k] = list(v) if isinstance(v, tuple) else v
    return entry, ckpt


def verdict_for(deployed, known):
    """match = known name with the deployed sha256; verdict per the plan's fixed rule."""
    sha = deployed.get("sha256")
    match = next((name for name, e in known.items() if sha is not None and e.get("sha256") == sha), None)
    source = (deployed.get("trained_on") or {}).get("source")
    ok = match is not None and source == "hauuto"
    return match, (REAL_DATA_VERDICT if ok else UNKNOWN_VERDICT)


def state_dict_equal(a, b):
    sa, sb = a["state_dict"], b["state_dict"]
    return list(sa.keys()) == list(sb.keys()) and all(
        sa[k].shape == sb[k].shape and sa[k].dtype == sb[k].dtype and torch.equal(sa[k], sb[k]) for k in sa)


def external_reproduction(ckpt):
    """Deployed model on CPU through train_alphabet_nested.load vs the original run's CSV."""
    manifest = _abs(REAL_DATA + "/manifest.csv")
    missing = [p for p in (manifest, _abs(NESTED_PREDICTIONS)) if not os.path.exists(p)]
    if missing:
        return {"k": None, "n": None, "reason": "missing: " + ", ".join(os.path.relpath(p, ROOT) for p in missing)}
    from train_alphabet_nested import load
    from train_alphabet_real import build

    with open(_abs(NESTED_PREDICTIONS), encoding="utf-8") as f:
        original = {r["sample_id"]: r["pred"] for r in csv.DictReader(f) if r["run"] == "external"}
    kind, variant = ckpt["model_type"], ckpt["selected"][2]
    classes = list(ckpt["classes"])
    model = build(kind, len(classes))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    items = [t for t in load(_abs(REAL_DATA), {}) if t["source"] == "qipedc"]
    key = variant if kind == "bigru" else "static"
    with torch.no_grad():
        logits = model(torch.from_numpy(np.stack([t[key] for t in items]))).numpy()
    preds = [classes[i] for i in logits.argmax(1)]
    both = [(t["sample_id"], p) for t, p in zip(items, preds) if t["sample_id"] in original]
    k = sum(original[sid] == p for sid, p in both)
    return {"k": int(k), "n": len(both), "clips_offline": len(items), "clips_in_csv": len(original),
            "device": "cpu", "original_device": "cuda (primary/nested.log)", "variant": variant,
            "compared_with": NESTED_PREDICTIONS + " (run=external, column pred)",
            "note": "information only: agreement of argmax with the original run, not accuracy"}


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_report(deployed_rel=DEPLOYED):
    deployed, dep_ckpt = describe(deployed_rel)
    known, known_ckpts = {}, {}
    for name, rel in KNOWN.items():
        known[name], known_ckpts[name] = describe(rel)
    match, verdict = verdict_for(deployed, known)
    report = {
        "checkpoints": {"deployed": deployed, **{f"known.{n}": e for n, e in known.items()}},
        "match": match,
        "verdict": verdict,
        "verdict_rule": (f"'{REAL_DATA_VERDICT}' iff the deployed sha256 equals a known checkpoint's sha256 "
                         f"AND deployed trained_on.source == 'hauuto'; otherwise '{UNKNOWN_VERDICT}'"),
        "state_dict_equal": {
            "note": "information only, not used by verdict: same keys and torch.equal on every tensor",
            **{n: (state_dict_equal(dep_ckpt, c) if dep_ckpt is not None and c is not None else None)
               for n, c in known_ckpts.items()}},
    }
    if dep_ckpt is None:
        report["external_reproduction"] = {"k": None, "n": None, "reason": f"missing: {deployed_rel}"}
    else:
        report["external_reproduction"] = external_reproduction(dep_ckpt)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", required=True)
    ap.add_argument("--deployed", default=DEPLOYED)
    args = ap.parse_args()
    report = {"generated_by": {
        "command": " ".join(["python", "scripts/alphabet_ckpt_provenance.py"] + sys.argv[1:]),
        "head": git_head(),
        "utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}}
    report.update(build_report(args.deployed))
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"verdict={report['verdict']} match={report['match']} "
          f"state_dict_equal={ {k: v for k, v in report['state_dict_equal'].items() if k != 'note'} } "
          f"external_reproduction={report['external_reproduction'].get('k')}/{report['external_reproduction'].get('n')} "
          f"-> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
