"""
Provenance of the Level 1 checkpoint the backend loads (plan 03, Bước 0; rule from Lần sửa 1, AC0').

Writes a JSON with, for the deployed checkpoint (default checkpoints/alphabet_best.pt) and the
three checkpoints known to be trained on real hauuto data:
  path, exists, sha256, size_bytes, keys, model_type, selected, epochs, preprocessing, trained_on, classes
plus
  verdict         "real_data_known_checkpoint" iff ALL of V1..V6 hold, else "UNKNOWN_PROVENANCE"
  verdict_checks  V1..V6, each {"ok": bool, "detail": ...} (computed by the pure function `verdict_checks`)
    V1 weights: M = the checkpoints among {nested_primary, nested_variants} whose state_dict is bit-exact
       (same key order, shape, dtype, torch.equal) with the deployed one; M must be non-empty.
       real_run is never part of M.
    V2 for every K in M and every inference field K has (model_type, classes, selected, hparams, input_dim,
       num_classes, epochs, preprocessing, trained_on): the deployed checkpoint has it with an equal value
       (classes compared in order).
    V3 at least one K in M has both preprocessing and trained_on (they come from a run's output).
    V4 deployed preprocessing == train_alphabet_nested.preprocessing_for(selected[2]).
    V5 deployed trained_on.source == "hauuto".
    V6 external_reproduction computed, n == clips_in_csv > 0 and k == n: the deployed model on CPU,
       offline path of scripts/train_alphabet_nested.load, over the QIPEDC clips; k = clips whose argmax
       equals `pred` of run="external" in primary/nested_predictions.csv (the original run used cuda).
  M               names of the known checkpoints satisfying V1
  sha256_match / match   name of the known checkpoint with the same file sha256, or null (information only:
                  a sha256 match exempts no check)
  state_dict_equal       per known checkpoint, bit-exact state_dict (information; V1 uses the nested ones)
  metadata_diff   per known checkpoint: key names only in the deployed file / only in K, with the TYPE
                  name of their values. Values are never copied (e.g. `evaluation`, `licence_note`).
The JSON holds counts, key names and checkpoint metadata only: no landmarks, no per-clip ids.
Running twice gives the same JSON except `generated_by`.
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
NESTED = ("nested_primary", "nested_variants")  # V1 candidates (AC5 uses the nested offline path)
REAL_DATA = "data/external/alphabet_hands_kaggle/alphabet_hands"
NESTED_PREDICTIONS = "reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv"
FIELDS = ("model_type", "selected", "epochs", "preprocessing", "trained_on", "classes")
INFERENCE_FIELDS = ("model_type", "classes", "selected", "hparams", "input_dim", "num_classes", "epochs",
                    "preprocessing", "trained_on")
REAL_DATA_VERDICT, UNKNOWN_VERDICT = "real_data_known_checkpoint", "UNKNOWN_PROVENANCE"
VERDICT_RULE = (
    f"'{REAL_DATA_VERDICT}' iff ALL of: V1 M = {{K in nested_primary, nested_variants: state_dict bit-exact "
    "(same key order, shape, dtype, torch.equal)}} is non-empty (real_run excluded); V2 for every K in M, every "
    f"field of {list(INFERENCE_FIELDS)} present in K is present and equal in the deployed checkpoint (classes in "
    "order); V3 some K in M has both preprocessing and trained_on; V4 deployed preprocessing == "
    "train_alphabet_nested.preprocessing_for(selected[2]); V5 deployed trained_on.source == 'hauuto'; V6 "
    "external_reproduction computed with n == clips_in_csv > 0 and k == n. Otherwise (any check false or not "
    f"computable) '{UNKNOWN_VERDICT}'. A sha256 match exempts no check.")


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


# ---------------------------------------------------------------------------
# Pure verdict logic (no disk access): unit-tested in tests/test_alphabet_ckpt_provenance.py
# ---------------------------------------------------------------------------
def state_dict_equal(a, b):
    """Bit-exact: same key order, and every tensor with the same shape, dtype and torch.equal."""
    sa, sb = (a or {}).get("state_dict"), (b or {}).get("state_dict")
    if sa is None or sb is None or list(sa.keys()) != list(sb.keys()):
        return False
    return all(sa[k].shape == sb[k].shape and sa[k].dtype == sb[k].dtype and torch.equal(sa[k], sb[k]) for k in sa)


def _norm(v):
    """tuples -> lists (recursively) so a value round-tripped through torch.save compares equal."""
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def metadata_diff(deployed, known):
    """Key names only in the deployed checkpoint / only in each K, with the type name of the value."""
    out = {}
    for name, ck in known.items():
        if ck is None:
            out[name] = None
            continue
        out[name] = {"only_in_deployed": {k: type(deployed[k]).__name__ for k in sorted(set(deployed) - set(ck))},
                     "only_in_known": {k: type(ck[k]).__name__ for k in sorted(set(ck) - set(deployed))}}
    return out


def verdict_checks(deployed, known, reproduction, preprocessing_for=None, sha256=None):
    """Pure. deployed: loaded checkpoint dict (or None); known: {name: loaded dict or None};
    reproduction: the external_reproduction dict (or None); preprocessing_for: variant -> preprocessing
    (default: scripts/train_alphabet_nested.preprocessing_for); sha256: optional {"deployed": sha, name: sha},
    reported as information only.
    Returns (verdict, checks, M)."""
    if preprocessing_for is None:
        from train_alphabet_nested import preprocessing_for
    deployed = deployed or {}
    checks = {}

    M = [n for n in NESTED if known.get(n) is not None and state_dict_equal(deployed, known[n])]
    checks["V1"] = {"ok": bool(M), "detail": {
        "M": M, "compared": [n for n in NESTED if known.get(n) is not None],
        "real_run_state_dict_equal_not_counted": (state_dict_equal(deployed, known["real_run"])
                                                  if known.get("real_run") is not None else None)}}

    mismatches = []
    for n in M:
        for f in INFERENCE_FIELDS:
            if f not in known[n]:
                continue
            if f not in deployed:
                mismatches.append({"K": n, "field": f, "reason": "missing in deployed"})
            elif _norm(deployed[f]) != _norm(known[n][f]):
                mismatches.append({"K": n, "field": f, "reason": "differs"})
    checks["V2"] = {"ok": bool(M) and not mismatches,
                    "detail": {"mismatches": mismatches} if M else "not computable: M is empty"}

    with_both = [n for n in M if "preprocessing" in known[n] and "trained_on" in known[n]]
    checks["V3"] = {"ok": bool(with_both), "detail": {"K_with_preprocessing_and_trained_on": with_both}}

    selected = deployed.get("selected")
    try:
        variant = selected[2]
        expected = preprocessing_for(variant)
        ok4 = _norm(deployed.get("preprocessing")) == _norm(expected)
        detail4 = {"variant": variant, "equal": ok4}
    except (TypeError, IndexError, KeyError) as e:
        ok4, detail4 = False, f"not computable: {type(e).__name__}"
    checks["V4"] = {"ok": ok4, "detail": detail4}

    trained_on = deployed.get("trained_on")
    source = trained_on.get("source") if isinstance(trained_on, dict) else None
    checks["V5"] = {"ok": source == "hauuto", "detail": {"trained_on.source": source}}

    r = reproduction or {}
    k, n, in_csv = r.get("k"), r.get("n"), r.get("clips_in_csv")
    ok6 = all(isinstance(x, int) for x in (k, n, in_csv)) and n == in_csv and n > 0 and k == n
    checks["V6"] = {"ok": ok6, "detail": {"k": k, "n": n, "clips_in_csv": in_csv}
                    if reproduction else "not computable: no external_reproduction"}

    if sha256 is not None:
        checks["sha256_match_information_only"] = next(
            (name for name in known if sha256.get(name) is not None and sha256.get(name) == sha256.get("deployed")),
            None)
    verdict = REAL_DATA_VERDICT if all(checks[f"V{i}"]["ok"] for i in range(1, 7)) else UNKNOWN_VERDICT
    return verdict, checks, M


def external_reproduction(ckpt):
    """Deployed model on CPU through train_alphabet_nested.load vs the original run's CSV (V6)."""
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
            "note": "V6: agreement of argmax with the original run (not accuracy)"}


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
    if dep_ckpt is None:
        reproduction = {"k": None, "n": None, "reason": f"missing: {deployed_rel}"}
    else:
        reproduction = external_reproduction(dep_ckpt)
    sha = {"deployed": deployed.get("sha256"), **{n: e.get("sha256") for n, e in known.items()}}
    verdict, checks, M = verdict_checks(dep_ckpt, known_ckpts, reproduction if reproduction.get("k") is not None
                                        else None, sha256=sha)
    match = checks.pop("sha256_match_information_only")
    return {
        "checkpoints": {"deployed": deployed, **{f"known.{n}": e for n, e in known.items()}},
        "verdict": verdict,
        "verdict_checks": checks,
        "M": M,
        "sha256_match": match,
        "match": match,
        "verdict_rule": VERDICT_RULE,
        "state_dict_equal": {
            "note": "bit-exact state_dict per known checkpoint; V1 counts only the nested ones",
            **{n: (state_dict_equal(dep_ckpt, c) if dep_ckpt is not None and c is not None else None)
               for n, c in known_ckpts.items()}},
        "metadata_diff": metadata_diff(dep_ckpt, known_ckpts) if dep_ckpt is not None else None,
        "external_reproduction": reproduction,
    }


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
    checks = {k: v["ok"] for k, v in report["verdict_checks"].items()}
    print(f"verdict={report['verdict']} checks={checks} M={report['M']} sha256_match={report['sha256_match']} "
          f"external_reproduction={report['external_reproduction'].get('k')}/{report['external_reproduction'].get('n')} "
          f"-> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
