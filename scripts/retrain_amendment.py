"""Plan 13 B9d (§0B.3 "path P", §0B.9) — public amendment of the K2 preregistration after the v3 smoke-test failure.

  python scripts/retrain_amendment.py --date <YYYY-MM-DD>
  -> reports/retrain_<YYYY-MM-DD>/preregistration_amendment_ls2.json (refuses to overwrite)

The amendment changes EXACTLY ONE key of reports/retrain_<D>/preregistration.json (which is never written):
`jobs.k2.cslr.train.argv` := registered argv + ["--skip-smoke-test"]. Every value is COMPUTED or COPIED by code at
generation time (never typed):
- the registered argv, read from the committed preregistration (exactly 1 commit, ancestor of HEAD, no local change);
- the decision of the smoke diagnosis (reports/retrain_<D>/k2_ls2_smoke_diag/smoke_diag.json, B9b): only "R1" or
  "R2-PASS" open path P; its reasons are copied from `decision_rule.reasons`;
- `expected_backbone_transfer{transferred_keys_count, transferred_params}` from the diagnosis D4-i (`D4.transfer_info`),
  cross-checked with `D4.key_analysis` (the R0 rule of §0B.3 must not hold);
- path + commit + sha256 of the committed blob (+ LF-normalised sha256 of the working copy) of smoke_diag.json and of
  the v3 CSLR log (reports/retrain_<D>/k2_train_v3/logs/cslr.log);
- the "unchanged" list: preregistration keys that the amendment does NOT touch (§3.6 sanity, epoch selection, test policy,
  §3.12 protocol, backbone rule, watchdog, GPU cap/budget, rerun policy), each with the sha256 of its canonical JSON;
- `flag_ref`: the one line of src/training/train_cslr.py that defines the existing `--skip-smoke-test` flag.

Exit codes: 0 written; 2 refused (output exists / wrong path, code or inputs dirty, missing input, an input file not
committed exactly once / not an ancestor of HEAD / committed blob != working copy); 3 the evidence does not open path P
(decision not in {R1, R2-PASS}, decision fields disagree, D4-ii fidelity false, diagnosis inputs not ok or its code dirty,
R0 condition on D4-i, registered argv missing or already containing the flag).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (str(ROOT), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from retrain_digest import lf_sha256  # noqa: E402

SCRIPT = "scripts/retrain_amendment.py"
PLAN = "docs/plans/13-train-lai-checkpoint-thieu.md"
REASON_REF = "docs/plans/13 §0B.3"
AMENDMENT_ID = "ls2"
KEY = "jobs.k2.cslr.train.argv"
FLAG = "--skip-smoke-test"
FLAG_FILE = "src/training/train_cslr.py"
CODE_PATHS = ("src", "scripts", "configs", "train.py", "evaluate_test.py", "kaggle")
PATH_P = {"R1": "R1", "R2-PASS": "R2"}  # decision of the diagnosis -> decision_rule of the amendment
UNCHANGED = (
    ("jobs.k2.cslr.sanity", "§3.6 sanity checks of the CSLR job (finite losses, best epoch >= 1, best_val_wer < 100, "
                            "LEAK CHECK before the first epoch, backbone transferred)"),
    ("jobs.k2.cslr.selection", "epoch selection rule (min val WER on the val split)"),
    ("jobs.k2.cslr.test_policy", "test protocol: no test in the kernel, one deferred local evaluation (§3.12)"),
    ("evaluation_protocol", "§3.12 evaluation protocol"),
    ("jobs.k2.backbone", "backbone file + sha256 rule (K1 output)"),
    ("jobs.k2.watchdog_minutes", "watchdog"),
    ("jobs.k2.gpu_cap_hours", "GPU cap of K2"),
    ("jobs.gpu_budget", "GPU budget of plan 13"),
    ("jobs.rerun_policy", "rerun policy"),
)


class AmendError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def input_rels(date):
    base = f"reports/retrain_{date}"
    return {"preregistration": f"{base}/preregistration.json",
            "smoke_diag": f"{base}/k2_ls2_smoke_diag/smoke_diag.json",
            "cslr_log": f"{base}/k2_train_v3/logs/cslr.log"}


def output_rel(date):
    return f"reports/retrain_{date}/preregistration_amendment_{AMENDMENT_ID}.json"


def canonical_sha256(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def get_key(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    return cur


# ---------------------------------------------------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------------------------------------------------
def _git(root, *args, text=True):
    r = subprocess.run(["git", *args], capture_output=True, cwd=str(root))
    out = r.stdout.decode("utf-8", "replace").strip() if text else r.stdout
    return r.returncode, out


def git_info(root, rels):
    """HEAD, dirty code/inputs, and for each input file: its commits, last commit, ancestry, sha256 of the committed
    blob. Patched in tests."""
    rc, head = _git(root, "rev-parse", "HEAD")
    if rc != 0:
        raise AmendError(2, "git rev-parse HEAD failed")
    rc, dirty = _git(root, "status", "--porcelain", "--", *CODE_PATHS, *rels)
    if rc != 0:
        raise AmendError(2, "git status failed")
    files = {}
    for rel in rels:
        _, log = _git(root, "log", "--format=%H", "--", rel)
        commits = [c for c in log.splitlines() if c.strip()]
        last = commits[0] if commits else None
        is_anc, blob_sha = False, None
        if last:
            is_anc = _git(root, "merge-base", "--is-ancestor", last, "HEAD")[0] == 0
            rc_b, blob = _git(root, "show", f"{last}:{rel}", text=False)
            blob_sha = hashlib.sha256(blob).hexdigest() if rc_b == 0 else None
        files[rel] = {"commits": commits, "n_commits": len(commits), "commit": last,
                      "is_ancestor_of_head": is_anc, "blob_sha256": blob_sha}
    return {"head": head, "code_dirty": bool(dirty.strip()), "code_dirty_files": dirty.splitlines(), "files": files}


# ---------------------------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------------------------
def committed_file(root, gi, rel):
    """Git record of one input: exactly 1 commit, ancestor of HEAD, committed blob == LF-normalised working copy."""
    f = gi["files"].get(rel) or {}
    if f.get("n_commits") != 1 or not f.get("commit"):
        raise AmendError(2, f"{rel} must be committed exactly once (has {f.get('n_commits')} commits: {f.get('commits')})")
    if not f.get("is_ancestor_of_head"):
        raise AmendError(2, f"{rel}: commit {f['commit']} is not an ancestor of HEAD")
    lf = lf_sha256(str(Path(root) / rel))
    if f.get("blob_sha256") != lf:
        raise AmendError(2, f"{rel}: committed blob sha256 {f.get('blob_sha256')} != working copy (LF) {lf}")
    return {"path": rel, "commit": f["commit"], "sha256": f["blob_sha256"], "lf_sha256": lf}


def _pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def check_diag(diag):
    """Decision of the diagnosis -> (decision, decision_rule, reasons, expected_backbone_transfer). Exit 3 otherwise."""
    dec = diag.get("decision")
    if dec not in PATH_P:
        raise AmendError(3, f"smoke_diag decision {dec!r} does not open path P (needs one of {sorted(PATH_P)})")
    rule = diag.get("decision_rule") or {}
    if rule.get("decision") != dec:
        raise AmendError(3, f"smoke_diag decision {dec!r} != decision_rule.decision {rule.get('decision')!r}")
    if rule.get("stop"):
        raise AmendError(3, f"smoke_diag decision_rule.stop is set: {rule.get('stop')!r}")
    if diag.get("inputs_ok") is not True:
        raise AmendError(3, "smoke_diag inputs_ok is not true")
    gb = diag.get("generated_by") or {}
    if gb.get("code_dirty") is not False:
        raise AmendError(3, f"smoke_diag generated_by.code_dirty is {gb.get('code_dirty')!r}")
    if (diag.get("fidelity") or {}).get("fidelity_ok") is not True:
        raise AmendError(3, "smoke_diag D4-ii fidelity_ok is not true (D4/D5 invalid)")
    d4 = diag.get("D4") or {}
    ti, ka = d4.get("transfer_info"), d4.get("key_analysis")
    if not isinstance(ti, dict) or not isinstance(ka, dict):
        raise AmendError(3, "smoke_diag D4.transfer_info / D4.key_analysis missing")
    n_keys, n_params = ti.get("transferred_keys_count"), ti.get("transferred_params")
    if not _pos_int(n_keys) or not _pos_int(n_params):
        raise AmendError(3, f"R0: transferred_keys_count={n_keys!r}, transferred_params={n_params!r}")
    if ka.get("n_shape_mismatch_keys") != 0:
        raise AmendError(3, f"R0: {ka.get('n_shape_mismatch_keys')!r} shape-mismatch keys")
    if ka.get("n_prefix_keys_in_both") != n_keys or ka.get("n_transferred_keys", n_keys) != n_keys:
        raise AmendError(3, f"R0: transferred keys {n_keys} != data_bn.*/blocks.* keys in both models "
                            f"{ka.get('n_prefix_keys_in_both')!r} (key_analysis n_transferred_keys "
                            f"{ka.get('n_transferred_keys')!r})")
    reasons = rule.get("reasons") or []
    return dec, PATH_P[dec], list(reasons), {
        "transferred_keys_count": n_keys, "transferred_params": n_params,
        "source": "smoke_diag.json D4.transfer_info (D4-i), cross-checked with D4.key_analysis",
        "kernel_check": "exactly one '[MODEL] Transferred N' line in the CSLR log with N == transferred_params"}


def flag_ref(root):
    path = Path(root) / FLAG_FILE
    if not path.is_file():
        raise AmendError(2, f"missing input {FLAG_FILE}")
    needle = f'"{FLAG}"'
    hits = [i + 1 for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines())
            if "add_argument(" in ln and needle in ln]
    if len(hits) != 1:
        raise AmendError(3, f"{FLAG_FILE}: expected exactly 1 add_argument line with {needle}, found {hits}")
    return f"{FLAG_FILE}:{hits[0]}"


# ---------------------------------------------------------------------------------------------------------------------
# amendment
# ---------------------------------------------------------------------------------------------------------------------
def build_amendment(root, date, argv):
    root = Path(root)
    rels = input_rels(date)
    for rel in rels.values():
        if not (root / rel).is_file():
            raise AmendError(2, f"missing input {rel}")
    gi = git_info(root, list(rels.values()))
    if gi["code_dirty"]:
        raise AmendError(2, f"code or inputs dirty (git status --porcelain): {gi['code_dirty_files']}")
    pre = committed_file(root, gi, rels["preregistration"])
    diag_ev = committed_file(root, gi, rels["smoke_diag"])
    log_ev = committed_file(root, gi, rels["cslr_log"])
    prereg = json.loads((root / rels["preregistration"]).read_text(encoding="utf-8"))
    diag = json.loads((root / rels["smoke_diag"]).read_text(encoding="utf-8"))
    decision, rule, reasons, transfer = check_diag(diag)
    try:
        registered = get_key(prereg, KEY)
    except KeyError:
        raise AmendError(3, f"preregistration has no {KEY}") from None
    if not isinstance(registered, list) or not registered or not all(isinstance(a, str) for a in registered):
        raise AmendError(3, f"preregistration {KEY} is not a non-empty list of strings: {registered!r}")
    if FLAG in registered:
        raise AmendError(3, f"preregistration {KEY} already contains {FLAG}")
    unchanged = []
    for key, what in UNCHANGED:
        try:
            value = get_key(prereg, key)
        except KeyError:
            raise AmendError(3, f"preregistration has no {key} (listed as unchanged)") from None
        unchanged.append({"key": key, "what": what, "sha256": canonical_sha256(value)})
    diag_gb = diag.get("generated_by") or {}
    return {
        "plan": PLAN,
        "amendment": AMENDMENT_ID,
        "reason_ref": REASON_REF,
        "generated_by": {"script": SCRIPT, "command": "python " + " ".join([SCRIPT, *map(shlex.quote, argv)]),
                         "git_commit": gi["head"], "code_dirty": gi["code_dirty"],
                         "code_dirty_files": gi["code_dirty_files"],
                         "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "python": platform.python_version(), "platform": platform.platform()},
        "date": date,
        "amends": {**pre, "note": "preregistration.json is not modified; this file is applied on top of it"},
        "whitelist": {KEY: [FLAG]},
        "changes": {KEY: [*registered, FLAG]},
        "changes_detail": {KEY: {"registered": list(registered), "added": [FLAG]}},
        "flag_ref": flag_ref(root),
        "decision": decision,
        "decision_rule": rule,
        "decision_reasons": reasons,
        "evidence": {
            "smoke_diag": {**diag_ev, "decision": decision, "diag_git_commit": diag_gb.get("git_commit")},
            "k2_train_v3_cslr_log": log_ev,
        },
        "expected_backbone_transfer": transfer,
        "unchanged": unchanged,
        "unchanged_rule": "every preregistration key other than the whitelisted one is unchanged; the listed keys are "
                          "the ones §0B.3 names explicitly (sha256 = canonical JSON of the registered value)",
    }


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with open(path, "xb") as f:  # exclusive: never overwrite, even on a race
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True, help="YYYY-MM-DD of reports/retrain_<date>/")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        dt.date.fromisoformat(args.date)
    except ValueError:
        ap.error(f"--date must be YYYY-MM-DD, got {args.date!r}")
    return args


def _drop_root(argv):
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "--root":
            skip = True
            continue
        if a.startswith("--root="):
            continue
        out.append(a)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    root = Path(args.root)
    out_rel = output_rel(args.date)
    if not re.fullmatch(r"reports/retrain_\d{4}-\d{2}-\d{2}/preregistration_amendment_ls2\.json", out_rel):
        print(f"retrain_amendment: bad output path {out_rel}", file=sys.stderr)
        return 2
    out = root / out_rel
    if out.exists():
        print(f"retrain_amendment: refusing to overwrite {out}", file=sys.stderr)
        return 2
    try:
        am = build_amendment(root, args.date, _drop_root(argv))
        sha = write_new(out, am)
    except AmendError as e:
        print(f"retrain_amendment: {e}", file=sys.stderr)
        return e.code
    except FileExistsError:
        print(f"retrain_amendment: refusing to overwrite {out}", file=sys.stderr)
        return 2
    print(json.dumps({"out": out_rel, "sha256": sha, "git_commit": am["generated_by"]["git_commit"],
                      "decision": am["decision"], "decision_rule": am["decision_rule"], "changes": am["changes"],
                      "expected_backbone_transfer": {k: am["expected_backbone_transfer"][k]
                                                     for k in ("transferred_keys_count", "transferred_params")}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
