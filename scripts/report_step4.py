"""
Step 4a-4c final report, generated only from files: run dirs (metrics.json + test_logits.npz + stgcn_unified_best.pt
with label_map/seed/run_config), the 4a/4b source-classifier JSONs, the Kaggle kernel logs and the unified manifest.
Rules: reports/step4_2026-09-26/PREREGISTRATION.md (selection on VAL only; TEST logits are only re-read).

Usage (see docs/plans/01-buoc4-hoan-tat-4a-4c.md, step 5):
  python scripts/report_step4.py --baseline <dir> --runs H-keepz=<dir> H-dropz=<dir> [--run-360 NAME=<dir>]
         [--aux-runs NAME=<dir> ...] [--dict-run <dir>] [--dict-run-360 <dir>]
         [--shortcut-4a <json>] [--shortcut-4b <json> ...] [--shortcut-legacy-compare OLD=NEW ...]
         [--kernel-logs <log> ...] [--review-file <md>] --out REPORT.md --json-out step4_results.json

Selection (pre-registered, VAL only): the z variant among --runs (the simpler one, hand z dropped, identified by
run_config.hand_z == "drop", unless another beats it by >= 0.5 balanced-VAL point); then --run-360 replaces it only
if >= 0.5 point better and its run_config equals the chosen one except process_height. --aux-runs are reported but
never selected. 4c uses the dictionary run whose run_config equals the chosen one except `sources` (no fallback).

Exit codes: 0 ok; 2 missing input / bad arguments; 3 configuration mismatch; 1 label-order assertion.
Nothing is written unless the exit code is 0. Output is deterministic (no timestamps, fixed key order).
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)
from report_unified import group_rows, wilson  # noqa: E402

DIFFERENT_SIGN = {"xem", "kết quả", "yếu", "thường xuyên"}
THRESHOLD = 0.5  # balanced-VAL points (PREREGISTRATION.md)
# Keys absent from run_config of runs trained before the --no-trim flag existed (commit 9b0ade1): that flag only
# added an option whose default keeps trimming on (git diff c8a7bdf c65032a -- src/data/harmonized.py
# scripts/train_unified.py), so those runs trimmed.
LEGACY_CONFIG_DEFAULTS = {"trim": True}
SHORTCUT_DEFAULT_CKPT = "checkpoints/stgcn_unified_best.pt"  # scripts/shortcut_85.py --ckpt default
DEFAULT_4B_DIR = "reports/step4_2026-09-26/4b"
MISSING = "KHÔNG CÓ"
GROUPS = ("vslgh_unseen_signer", "qipedc_only_class", "total", "cross_source")
GROUP_NAMES = {"vslgh_unseen_signer": "S06 (người ký chưa thấy)",
               "qipedc_only_class": "QIPEDC-only (≥ 2 bản quay)",
               "total": "Tổng",
               "cross_source": "Chéo nguồn (lớp chung − 4 từ)"}
ROLE_NAMES = {"baseline": "baseline", "candidate_native": "ứng viên (gốc)", "candidate_360": "ứng viên (360 px)",
              "aux": "phụ (không phải ứng viên)", "dict": "từ điển (4c)"}


class ReportError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------------------------------------------
# pure functions (tested in tests/test_report_step4.py)
# ---------------------------------------------------------------------------------------------------------------
def rate(k, n):
    """Proportion in percent with Wilson 95% CI, clamped to [0, 100]."""
    k, n = int(k), int(n)
    if n == 0:
        return {"k": 0, "n": 0, "pct": None, "ci_low": None, "ci_high": None}
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "pct": 100.0 * k / n,
            "ci_low": float(min(max(lo, 0.0), 100.0)), "ci_high": float(min(max(hi, 0.0), 100.0))}


def rate_of(hits):
    hits = np.asarray(hits, bool)
    return rate(int(hits.sum()), len(hits))


def k_from_pct(pct, n, decimals=1):
    """The unique k whose rounded percentage equals pct (as written by shortcut_85.py / train_unified.py), else None."""
    if pct is None or not n:
        return None
    ks = [k for k in range(n + 1) if round(100 * np.float64(k / n), decimals) == pct]
    return ks[0] if len(ks) == 1 else None


def k_from_exact_pct(pct, n):
    """metrics.json stores unrounded percentages: k = pct * n / 100 must be an integer."""
    if pct is None or not n:
        return None
    k = pct * n / 100.0
    return int(round(k)) if abs(k - round(k)) < 1e-6 else None


def balanced_val(metrics):
    """(VAL top-1 on VSL-GH + VAL top-1 on QIPEDC) / 2 from metrics.json -> val_by_source, unrounded."""
    vb = metrics.get("val_by_source") or {}
    if any(s not in vb or vb[s].get("top1") is None for s in ("vslgh", "qipedc")):
        return None
    return (vb["vslgh"]["top1"] + vb["qipedc"]["top1"]) / 2


def effective_config(run_config, seed):
    """run_config (+ defaults for keys added later) + the checkpoint seed; {} + seed when the run predates run_config."""
    cfg = {} if run_config is None else {**LEGACY_CONFIG_DEFAULTS, **run_config}
    cfg["seed"] = seed
    return cfg


def same_except(a, b, keys):
    keys = set(keys)
    return {k: v for k, v in a.items() if k not in keys} == {k: v for k, v in b.items() if k not in keys}


def choose_z(cands):
    """cands {name: (balanced_val | None, cfg)}. The simpler variant (cfg hand_z == "drop") unless the best other
    candidate beats it by >= THRESHOLD. Candidates without balanced VAL are not candidates."""
    valid = {k: v for k, v in cands.items() if v[0] is not None}
    if not valid:
        raise ReportError(3, "không có ứng viên gốc nào có val_by_source")
    drops = sorted(k for k, (_, c) in valid.items() if c.get("hand_z") == "drop")
    if len(drops) > 1:
        raise ReportError(3, f"nhiều hơn một ứng viên bỏ hand z: {drops}")
    others = {k: v for k, v in valid.items() if k not in drops}
    best = max(sorted(others), key=lambda k: others[k][0]) if others else None
    if not drops:
        return {"chosen": best, "simple": None, "best_other": best, "diff": None}
    if best is None:
        return {"chosen": drops[0], "simple": drops[0], "best_other": None, "diff": None}
    diff = others[best][0] - valid[drops[0]][0]
    return {"chosen": best if diff >= THRESHOLD else drops[0], "simple": drops[0], "best_other": best, "diff": diff}


def choose_resolution(chosen, bal_chosen, cfg_chosen, r360):
    """r360 {name: (balanced_val, cfg)}: adopted only if >= THRESHOLD better; its cfg must equal the chosen one in
    every key except process_height (else exit 3)."""
    if not r360:
        return {"chosen": chosen, "run_360": None, "compared_with": chosen, "diff": None, "adopted": False}
    if len(r360) > 1:
        raise ReportError(3, f"nhiều hơn một run 360: {sorted(r360)}")
    name, (bal, cfg) = next(iter(r360.items()))
    if not same_except(cfg, cfg_chosen, {"process_height"}) or cfg.get("process_height") == cfg_chosen.get("process_height"):
        raise ReportError(3, f"run_config của {name} ({cfg}) không trùng {chosen} ({cfg_chosen}) ngoài process_height")
    if bal is None or bal_chosen is None:
        raise ReportError(3, f"thiếu val_by_source cho {name} hoặc {chosen}")
    diff = bal - bal_chosen
    adopted = diff >= THRESHOLD
    return {"chosen": name if adopted else chosen, "run_360": name, "compared_with": chosen, "diff": diff,
            "adopted": adopted}


def trimming_verdict(runs):
    """runs {name: (balanced_val, cfg)}: each trim == False run is paired with the one run whose cfg is equal except
    trim; credited if bal(trimmed) - bal(untrimmed) >= THRESHOLD. No unique partner -> exit 3."""
    out = []
    for name, (bal, cfg) in runs.items():
        if cfg.get("trim") is not False:
            continue
        partners = [p for p, (_, c) in runs.items() if p != name and c.get("trim") is True and same_except(c, cfg, {"trim"})]
        if len(partners) != 1:
            raise ReportError(3, f"ablation cắt nghỉ {name}: {len(partners)} run trùng run_config (trừ trim): {partners}")
        p = partners[0]
        if bal is None or runs[p][0] is None:
            raise ReportError(3, f"ablation cắt nghỉ {name}/{p}: thiếu val_by_source")
        diff = runs[p][0] - bal
        out.append({"trimmed": p, "untrimmed": name, "diff": diff, "credited": diff >= THRESHOLD})
    return out


def seed_pairs(cfgs):
    """cfgs {name: cfg}: pairs (lower seed, higher seed) of runs identical except seed."""
    names = list(cfgs)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ca, cb = cfgs[a], cfgs[b]
            if ca.get("seed") != cb.get("seed") and same_except(ca, cb, {"seed"}):
                out.append((a, b) if (ca.get("seed") or 0) <= (cb.get("seed") or 0) else (b, a))
    return out


def pick_dict_run(chosen_cfg, dict_runs):
    """dict_runs {name: cfg}: the one dictionary (sources == qipedc) run whose cfg equals the chosen one except
    sources/seed. None or several -> exit 3 (no fallback)."""
    match = [n for n, c in dict_runs.items()
             if c.get("sources") == "qipedc" and same_except(c, chosen_cfg, {"sources", "seed"})]
    if len(match) != 1:
        raise ReportError(3, f"4c không có run từ điển khớp cách hài hòa đã chọn (chosen {chosen_cfg}; "
                             f"dict runs {dict_runs}; khớp: {match})")
    return match[0]


def topk_hits(logits, true_idx, ks=(1, 5, 10)):
    """{k: bool array}; ranks by stable sort (ties -> lower class index first)."""
    order = np.argsort(-np.asarray(logits, np.float64), axis=1, kind="stable")
    pos = (order == np.asarray(true_idx)[:, None]).argmax(1)
    return {k: pos < k for k in ks}


def tie_check(logits, true_idx, ks=(1, 5, 10)):
    """Logits are stored as float16, so the true class can tie with others. Per k: hits with the stable ranking used
    here, and the pessimistic / optimistic counts (ties ranked after / before the true class)."""
    L = np.asarray(logits, np.float64)
    t = L[np.arange(len(L)), np.asarray(true_idx)]
    gt = (L > t[:, None]).sum(1)
    eq = (L == t[:, None]).sum(1) - 1
    used = topk_hits(L, true_idx, ks)
    return {str(k): {"used": int(used[k].sum()), "pessimistic": int(((gt + eq) < k).sum()),
                     "optimistic": int((gt < k).sum()), "n": int(len(L))} for k in ks}


def top1_pred(logits):
    return np.argsort(-np.asarray(logits, np.float64), axis=1, kind="stable")[:, 0]


def align_logits(video_ids, labels, logits, classes, test):
    """Manifest rows present in the logits file, in manifest order; asserts that the stored label of each row is its
    class in the checkpoint label order."""
    order = {v: i for i, v in enumerate(video_ids)}
    rows = test[test.video_id.isin(order)].reset_index(drop=True)
    idx = np.array([order[v] for v in rows.video_id], dtype=int)
    lab = np.asarray(labels)[idx].astype(int)
    assert all(classes[l] == g for l, g in zip(lab, rows.gloss_normalized)), "label order mismatch"
    return rows, np.asarray(logits, np.float32)[idx], lab


def align(rows_a, rows_b):
    """Indices into rows_a / rows_b of their common video_ids (sorted)."""
    common = sorted(set(rows_a.video_id) & set(rows_b.video_id))
    return (pd.Index(rows_a.video_id).get_indexer(common), pd.Index(rows_b.video_id).get_indexer(common), common)


def mcnemar_exact(a_hits, b_hits):
    """n10 = a right & b wrong, n01 = the reverse; two-sided exact binomial p (1.0 when no discordant pair)."""
    from scipy.stats import binomtest
    a, b = np.asarray(a_hits, bool), np.asarray(b_hits, bool)
    n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
    p = 1.0 if n10 + n01 == 0 else float(binomtest(n10, n10 + n01, 0.5).pvalue)
    return n10, n01, p


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_CMD = re.compile(r"^\$ (?:\[GPU (\d+)\] )?(\S*python3?\S* scripts/train_unified\.py .*)$")
_EXIT = re.compile(r"^--- (\S+) exit (-?\d+) ---$")
_EXIT_SEED = re.compile(r"^--- seed \d+ exit (-?\d+); tail of (\S+)/train\.log ---$")
_TOTAL = re.compile(r"^total ([\d.]+) min")


def parse_kernel_log(path):
    """Kaggle kernel log (JSON array of {stream_name, time, data}) -> repo commit, branch, per out-dir command/seed/exit,
    duration (time of the last entry)."""
    entries = read_json(path)
    out = {"path": path, "repo_commit": None, "branch": None, "runs": {}, "duration_s": None, "reported_total_min": None}
    for i, e in enumerate(entries):
        line = e["data"].strip()
        m = re.search(r"git clone .*?-b (\S+) \S*Vietnamese-Sign-Language-Translator", line)
        if m and out["branch"] is None:
            out["branch"] = m.group(1)
        if line.startswith("$ cd /tmp/vslt && git log --oneline -1") and i + 1 < len(entries):
            out["repo_commit"] = entries[i + 1]["data"].split()[0]
        m = _CMD.match(line)
        if m:
            cmd = m.group(2)
            toks = shlex.split(cmd)
            od = toks[toks.index("--out-dir") + 1] if "--out-dir" in toks else None
            seed = int(toks[toks.index("--seed") + 1]) if "--seed" in toks else None
            if od:
                out["runs"][os.path.basename(od.rstrip("/"))] = {"command": cmd, "seed": seed, "exit": None}
        m = _EXIT.match(line) or _EXIT_SEED.match(line)
        if m:
            code, od = (m.group(2), m.group(1)) if m.re is _EXIT else (m.group(1), m.group(2))
            name = os.path.basename(od.rstrip("/"))
            if name in out["runs"]:
                out["runs"][name]["exit"] = int(code)
        m = _TOTAL.match(line)
        if m:
            out["reported_total_min"] = float(m.group(1))
    if entries:
        out["duration_s"] = float(entries[-1]["time"])
    return out


def json_provenance(j):
    return j.get("command"), j.get("git_commit")


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def compare_legacy(old, new):
    """Old JSON (no provenance) vs its re-run: fields with different values, fields missing in the re-run, fields only
    in the re-run. Same = no differing value and nothing missing."""
    fo, fn = _flatten(old), _flatten(new)
    diff = sorted(k for k in fo if k in fn and fo[k] != fn[k])
    only_old = sorted(k for k in fo if k not in fn)
    only_new = sorted(k for k in fn if k not in fo)
    return {"same": not diff and not only_old, "different_fields": diff, "only_in_old": only_old, "only_in_new": only_new,
            "values": {k: {"old": fo[k], "new": fn[k]} for k in diff}}


# ---------------------------------------------------------------------------------------------------------------
# file helpers
# ---------------------------------------------------------------------------------------------------------------
def sha256(path, _cache={}):
    st = os.stat(path)
    key = (os.path.abspath(path), st.st_mtime_ns, st.st_size)
    if key not in _cache:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _cache[key] = h.hexdigest()
    return _cache[key]


def rel(path):
    p = os.path.normpath(path)
    try:
        r = os.path.relpath(p, ROOT)
        p = r if not r.startswith("..") else p
    except ValueError:
        pass
    return p.replace("\\", "/")


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    return r.stdout.strip() if r.returncode == 0 else None


def git_commit_info(commit):
    s = git("log", "-1", "--format=%h|%ct|%ad|%s", "--date=iso", commit) if commit else None
    if not s:
        return None
    h, ct, ad, subj = s.split("|", 3)
    return {"commit": h, "unix": int(ct), "date": ad, "subject": subj}


def git_added(path):
    s = git("log", "--diff-filter=A", "-1", "--format=%h|%ct|%ad|%s", "--date=iso", "--", rel(path))
    if not s:
        return None
    h, ct, ad, subj = s.split("|", 3)
    return {"commit": h, "unix": int(ct), "date": ad, "subject": subj}


class Inputs:
    def __init__(self):
        self.items = {}

    def add(self, path, role):
        p = rel(path)
        if not os.path.isfile(path):
            raise ReportError(2, f"thiếu file đầu vào: {p} ({role})")
        self.items.setdefault(p, {"path": p, "sha256": sha256(path), "roles": []})
        if role not in self.items[p]["roles"]:
            self.items[p]["roles"].append(role)
        return path

    def as_list(self):
        return [{"path": v["path"], "sha256": v["sha256"], "role": "; ".join(v["roles"])} for _, v in sorted(self.items.items())]


def load_json(path, inputs, role):
    inputs.add(path, role)
    return read_json(path)


def load_ckpt_meta(path):
    import torch
    ck = torch.load(path, map_location="cpu", weights_only=False)
    lm = ck["label_map"]
    return {"classes": [c for c, _ in sorted(lm.items(), key=lambda kv: kv[1])], "seed": ck.get("seed"),
            "run_config": ck.get("run_config"), "preprocessing": ck.get("preprocessing")}


def _named(items, flag):
    out = {}
    for s in items:
        if "=" not in s:
            raise ReportError(2, f"{flag}: cần NAME=DIR, nhận '{s}'")
        k, v = s.split("=", 1)
        out[k] = v
    return out


# ---------------------------------------------------------------------------------------------------------------
# build the results dict
# ---------------------------------------------------------------------------------------------------------------
def _cfg_for_json(cfg):
    return {k: cfg[k] for k in cfg}


def _val_rates(metrics):
    vb = metrics.get("val_by_source") or {}
    out = {}
    for s in ("vslgh", "qipedc"):
        if s in vb:
            n = int(vb[s]["n"])
            k = k_from_exact_pct(vb[s]["top1"], n)
            out[s] = rate(k, n) if k is not None else {"k": None, "n": n, "pct": vb[s]["top1"], "ci_low": None, "ci_high": None}
    return out


def _hist_summary(metrics):
    h = {int(k): int(v) for k, v in (metrics.get("train_samples_per_class_hist") or {}).items()}
    return {"classes_with_train_data": sum(h.values()), "train_clips": sum(k * v for k, v in h.items()),
            "classes_le_2_clips": sum(v for k, v in h.items() if k <= 2),
            "hist": {str(k): v for k, v in sorted(h.items())}}


def select(meta):
    """Pre-registered selection on VAL only. meta {name: {"role", "bal", "cfg"}}; aux/baseline/dict never selected."""
    native = {n: (m["bal"], m["cfg"]) for n, m in meta.items() if m["role"] == "candidate_native"}
    z = choose_z(native)
    r360 = {n: (m["bal"], m["cfg"]) for n, m in meta.items() if m["role"] == "candidate_360"}
    res = choose_resolution(z["chosen"], meta[z["chosen"]]["bal"], meta[z["chosen"]]["cfg"], r360)
    return {"z": z, "resolution": res, "chosen": res["chosen"]}


def build(args, argv):
    inputs = Inputs()
    man_dir = args.manifest_dir
    test = pd.read_csv(inputs.add(os.path.join(man_dir, "test.csv"), "manifest test"))
    train = pd.read_csv(inputs.add(os.path.join(man_dir, "train.csv"), "manifest train"))
    val = pd.read_csv(inputs.add(os.path.join(man_dir, "val.csv"), "manifest val"))
    man = pd.concat([train, val, test])
    shared = {c for c, s in man.groupby("gloss_normalized").source.apply(set).items() if {"vslgh", "qipedc"} <= s}

    specs = [("baseline", args.baseline, "baseline")]
    specs += [(k, v, "candidate_native") for k, v in _named(args.runs, "--runs").items()]
    if args.run_360:
        specs += [(k, v, "candidate_360") for k, v in _named([args.run_360], "--run-360").items()]
    specs += [(k, v, "aux") for k, v in _named(args.aux_runs, "--aux-runs").items()]
    for d in (args.dict_run, args.dict_run_360):
        if d:
            specs.append((os.path.basename(os.path.normpath(d)), d, "dict"))
    names = [s[0] for s in specs]
    if len(set(names)) != len(names):
        raise ReportError(2, f"tên run trùng nhau: {names}")

    # every input must exist before anything is computed
    for name, d, _ in specs:
        for f in ("metrics.json", "test_logits.npz", "stgcn_unified_best.pt"):
            inputs.add(os.path.join(d, f), f"{f} {name}")
    kernels = [parse_kernel_log(inputs.add(p, "kernel log")) for p in args.kernel_logs]
    s4a = load_json(args.shortcut_4a, inputs, "4a source classifier + cross-source (provenance)")
    s4b_paths = args.shortcut_4b if args.shortcut_4b is not None else sorted(
        os.path.join(DEFAULT_4B_DIR, f) for f in os.listdir(DEFAULT_4B_DIR) if f.startswith("shortcut_85_harmonized"))
    s4b = [(p, load_json(p, inputs, "4b source classifier")) for p in s4b_paths]
    legacy = []
    for pair in args.shortcut_legacy_compare:
        if "=" not in pair:
            raise ReportError(2, f"--shortcut-legacy-compare: cần OLD=NEW, nhận '{pair}'")
        o, n = pair.split("=", 1)
        legacy.append((o, n, load_json(o, inputs, "JSON cũ (không provenance)"), load_json(n, inputs, "JSON chạy lại")))
    review = read_text(inputs.add(args.review_file, "review")) if args.review_file else None
    inputs.add(args.prereg, "preregistration")

    # ---- per-run metadata (VAL, config, seed) ----
    meta = {}
    for name, d, role in specs:
        m = load_json(os.path.join(d, "metrics.json"), inputs, f"metrics.json {name}")
        ck = load_ckpt_meta(os.path.join(d, "stgcn_unified_best.pt"))
        if m.get("run_config") is not None and ck["run_config"] is not None and m["run_config"] != ck["run_config"]:
            raise ReportError(3, f"{name}: run_config của metrics.json và checkpoint khác nhau")
        meta[name] = {"dir": d, "role": role, "metrics": m, "ckpt": ck, "bal": balanced_val(m),
                      "cfg": effective_config(m.get("run_config", ck["run_config"]), ck["seed"])}

    sel = select(meta)
    chosen = sel["chosen"]
    # 4c: only the dictionary run matching the chosen harmonisation is reported (PREREGISTRATION.md line 23);
    # the other one is named, never given numbers.
    dict_names = [n for n in meta if meta[n]["role"] == "dict"]
    used_dict = pick_dict_run(meta[chosen]["cfg"], {n: meta[n]["cfg"] for n in dict_names}) if dict_names else None
    hidden = set(dict_names) - {used_dict}
    q_val_n = sorted({int(meta[n]["metrics"]["val_by_source"]["qipedc"]["n"]) for n in meta
                      if meta[n]["role"] in ("candidate_native", "candidate_360") and meta[n]["bal"] is not None})
    if len(q_val_n) != 1:
        raise ReportError(3, f"số clip QIPEDC VAL khác nhau giữa các ứng viên: {q_val_n}")
    one_clip = 100.0 / (2 * q_val_n[0])
    non_dict = [n for n in meta if meta[n]["role"] != "dict"]
    trimming = trimming_verdict({n: (meta[n]["bal"], meta[n]["cfg"]) for n in non_dict if meta[n]["cfg"].get("trim") is not None})
    pairs = seed_pairs({n: meta[n]["cfg"] for n in non_dict})

    val_table = []
    for n in non_dict + [x for x in dict_names if x not in hidden]:
        m = meta[n]
        val_table.append({"run": n, "role": m["role"], "candidate": m["role"] in ("candidate_native", "candidate_360"),
                          "val_by_source": _val_rates(m["metrics"]), "balanced_val": m["bal"],
                          "best_epoch": m["metrics"].get("val_best", {}).get("epoch"),
                          "val_best_top1_overall": m["metrics"].get("val_best", {}).get("top1")})

    def near(diff):
        return None if diff is None else abs(diff - THRESHOLD) < one_clip

    seed_val = [{"a": a, "b": b, "seed_a": meta[a]["cfg"]["seed"], "seed_b": meta[b]["cfg"]["seed"],
                 "diff_b_minus_a": meta[b]["bal"] - meta[a]["bal"]} for a, b in pairs
                if meta[a]["bal"] is not None and meta[b]["bal"] is not None]
    selection = {"rule": "balanced VAL = (VAL top-1 VSL-GH S05 + VAL top-1 QIPEDC) / 2; chênh < 0.5 điểm -> biến thể "
                         "đơn giản (bỏ hand z; độ phân giải gốc). Chỉ dùng VAL.",
                 "threshold": THRESHOLD, "n_qipedc_val": q_val_n[0], "one_qipedc_val_clip_points": one_clip,
                 "table": val_table,
                 "z": {**sel["z"], "near_threshold": near(sel["z"]["diff"])},
                 "resolution": {**sel["resolution"], "near_threshold": near(sel["resolution"]["diff"])},
                 "chosen": chosen, "chosen_run_config": _cfg_for_json(meta[chosen]["cfg"]),
                 "seed_spread_balanced_val": seed_val}
    for t in trimming:
        t["near_threshold"] = near(t["diff"])

    # ---- TEST (logits only re-read) ----
    masks_all, dropped = group_rows(test, train)
    masks_all = dict(masks_all)
    masks_all["cross_source"] = ((test.source == "qipedc") & test.gloss_normalized.isin(shared - DIFFERENT_SIGN)).values
    loaded = {}
    for name in meta:
        d = np.load(os.path.join(meta[name]["dir"], "test_logits.npz"))
        rows, logits, true = align_logits(d["video_ids"], d["labels"], d["logits"], meta[name]["ckpt"]["classes"], test)
        loaded[name] = {"rows": rows, "logits": logits, "true": true, "hits": topk_hits(logits, true),
                        "pred": top1_pred(logits)}
    ties = {}
    for name in meta:
        tc = tie_check(loaded[name]["logits"], loaded[name]["true"])
        to = meta[name]["metrics"].get("test_overall") or {}
        for k in ("1", "5"):
            pct = to.get(f"top{k}")
            tc[k]["metrics_json_fp32"] = k_from_exact_pct(pct, to.get("n")) if pct is not None else None
        if name not in hidden:
            ties[name] = tc
    test_groups = {}
    group_hits = {}
    for name in non_dict:
        L = loaded[name]
        present = test.video_id.isin(L["rows"].video_id).values
        test_groups[name] = {}
        group_hits[name] = {}
        for g in GROUPS:
            mk = masks_all[g][present]
            test_groups[name][g] = {"top1": rate_of(L["hits"][1][mk]), "top5": rate_of(L["hits"][5][mk])}
            group_hits[name][g] = (L["rows"].video_id.values[mk], L["hits"][1][mk])
    seed_spread = []
    for a, b in pairs:
        row = {"a": a, "b": b, "seed_a": meta[a]["cfg"]["seed"], "seed_b": meta[b]["cfg"]["seed"], "groups": {}}
        for g in GROUPS:
            row["groups"][g] = {}
            for k in ("top1", "top5"):
                ra, rb = test_groups[a][g][k], test_groups[b][g][k]
                row["groups"][g][k] = {"a": ra, "b": rb, "diff_points": None if ra["pct"] is None else rb["pct"] - ra["pct"],
                                       "diff_k": rb["k"] - ra["k"]}
        seed_spread.append(row)

    def paired(a, b):
        out = {}
        for g in GROUPS:
            va, ha = group_hits[a][g]
            vb_, hb = group_hits[b][g]
            ia = pd.Index(va).get_indexer(sorted(set(va) & set(vb_)))
            ib = pd.Index(vb_).get_indexer(sorted(set(va) & set(vb_)))
            n10, n01, p = mcnemar_exact(ha[ia], hb[ib])
            out[g] = {"a": test_groups[a][g]["top1"], "b": test_groups[b][g]["top1"], "n_common": len(ia),
                      "diff_points": (None if test_groups[a][g]["top1"]["pct"] is None
                                      else test_groups[a][g]["top1"]["pct"] - test_groups[b][g]["top1"]["pct"]),
                      "diff_k": test_groups[a][g]["top1"]["k"] - test_groups[b][g]["top1"]["k"],
                      "mcnemar_top1": {"n10_a_only": n10, "n01_b_only": n01, "p": p}}
        return out

    trim_test = [{"trimmed": t["trimmed"], "untrimmed": t["untrimmed"], "groups": paired(t["trimmed"], t["untrimmed"])}
                 for t in trimming]
    base_name = "baseline"
    vs_baseline = {"chosen": chosen, "baseline": base_name, "groups": paired(chosen, base_name),
                   "chosen_process_height": meta[chosen]["cfg"].get("process_height"),
                   "ablation_process_heights": sorted({str(meta[t["trimmed"]]["cfg"].get("process_height")) for t in trimming})}

    # ---- source classifier on harmonised input ----
    src_cls = []
    for p, j in s4b:
        cmd, com = json_provenance(j)
        src_cls.append({"path": rel(p), "command": cmd, "git_commit": com, "hand_z": j.get("hand_z"),
                        "qipedc_kps_dir": j.get("qipedc_kps_dir"), "features": j.get("features"),
                        "n_by_source": j["balanced"]["n_by_source"], "all": j["balanced"]["all"],
                        "single_group": j["balanced"]["single_group"]})

    # ---- harmonisation config (from the chosen checkpoint + src/data/harmonized.py) ----
    import src.data.harmonized as H
    prep = meta[chosen]["ckpt"]["preprocessing"] or {}
    doc = H.__doc__ or ""
    aug = re.search(r"Augmentation \(training only\):[^\n]*", doc)
    bullets = {k: re.search(rf"- {k}:(.*?)(?=\n- |\nAugmentation|\Z)", doc, re.S) for k in ("joints", "coordinates", "time")}
    harm = {"source": f"checkpoint {rel(os.path.join(meta[chosen]['dir'], 'stgcn_unified_best.pt'))} -> preprocessing; "
                      "src/data/harmonized.py (HARMONIZED_DEFAULT, docstring)",
            "preprocessing_of_chosen": prep,
            "differs_from_HARMONIZED_DEFAULT": {k: {"default": H.HARMONIZED_DEFAULT.get(k), "chosen": prep.get(k)}
                                                for k in sorted(set(H.HARMONIZED_DEFAULT) | set(prep))
                                                if k in H.HARMONIZED_DEFAULT and prep.get(k) != H.HARMONIZED_DEFAULT.get(k)},
            "doc": {k: " ".join(v.group(1).split()) if v else None for k, v in bullets.items()},
            "augmentation": aug.group(0) if aug else None,
            "tta": "không (TEST đánh giá một lần, không TTA: scripts/train_unified.py predict_all một lượt)"}

    # ---- 4a ----
    cur_ckpt = SHORTCUT_DEFAULT_CKPT
    cmd4a, com4a = json_provenance(s4a)
    if cmd4a and "--ckpt" in shlex.split(cmd4a):
        t = shlex.split(cmd4a)
        cur_ckpt = t[t.index("--ckpt") + 1]
    inputs.add(cur_ckpt, "model hiện tại của 4a (chỉ sha256)")
    base_ckpt = os.path.join(meta[base_name]["dir"], "stgcn_unified_best.pt")
    c = s4a.get("cross_source_current_model")
    cross4a = None
    if c:
        cross4a = {"classes_kept": c["classes_kept"], "excluded_different_sign": c["excluded_different_sign"]}
        for s in ("qipedc_test_only", "qipedc_val_test", "s06_reference"):
            e = c.get(s)
            if not e:
                continue
            k1, k5 = k_from_pct(e["top1"], e["n"]), k_from_pct(e["top5"], e["n"])
            cross4a[s] = {"n": e["n"], "classes": e.get("classes"), "json_top1": e["top1"], "json_top1_ci": e.get("top1_ci"),
                          "json_top5": e["top5"], "top1": rate(k1, e["n"]) if k1 is not None else None,
                          "top5": rate(k5, e["n"]) if k5 is not None else None}
    same_ckpt = sha256(cur_ckpt) == sha256(base_ckpt)
    check_vs_baseline = None
    if cross4a and cross4a.get("qipedc_test_only", {}).get("top1") and same_ckpt:
        b = test_groups[base_name]["cross_source"]
        a1, a5 = cross4a["qipedc_test_only"]["top1"], cross4a["qipedc_test_only"]["top5"]
        check_vs_baseline = {"same": (a1["k"], a1["n"], a5 and a5["k"]) == (b["top1"]["k"], b["top1"]["n"], b["top5"]["k"]),
                             "json": [a1["k"], a1["n"], a5 and a5["k"]], "baseline_logits": [b["top1"]["k"], b["top1"]["n"], b["top5"]["k"]]}
    s4a_out = {"path": rel(args.shortcut_4a), "command": cmd4a, "git_commit": com4a,
               "shared_classes": s4a["shared_classes"], "balanced": s4a["balanced"], "cross_source_current_model": cross4a,
               "current_model_ckpt": {"path": rel(cur_ckpt), "sha256": sha256(cur_ckpt)},
               "baseline_ckpt": {"path": rel(base_ckpt), "sha256": sha256(base_ckpt)}, "same_checkpoint": same_ckpt,
               "cross_source_vs_baseline_logits": check_vs_baseline}

    # ---- 4c ----
    c4 = None
    if dict_names:
        used = used_dict
        D, U = loaded[used], loaded[chosen]
        uq = U["rows"].source.values == "qipedc"
        uq_idx = np.where(uq)[0]
        di, ui_q, common = align(D["rows"], U["rows"].iloc[uq_idx])
        ui = uq_idx[ui_q]
        main_tab = {"dict": {k: rate_of(D["hits"][k][di]) for k in (1, 5, 10)},
                    "unified": {k: rate_of(U["hits"][k][ui]) for k in (1, 5, 10)}}
        n10, n01, p = mcnemar_exact(D["hits"][1][di], U["hits"][1][ui])
        d_cls, u_cls = meta[used]["ckpt"]["classes"], meta[chosen]["ckpt"]["classes"]
        u_pos = {c: i for i, c in enumerate(u_cls)}
        cols = [u_pos[c] for c in d_cls if c in u_pos]
        missing_cls = [c for c in d_cls if c not in u_pos]
        restricted = None
        if not missing_cls:
            r_hits = topk_hits(U["logits"][ui][:, cols], D["true"][di])
            rn10, rn01, rp = mcnemar_exact(D["hits"][1][di], r_hits[1])
            restricted = {"unified_restricted": {k: rate_of(r_hits[k]) for k in (1, 5, 10)},
                          "mcnemar_top1": {"n10_dict_only": rn10, "n01_unified_only": rn01, "p": rp}}
        tr_v = set(train.loc[train.source == "vslgh", "gloss_normalized"])
        tr_q = set(train.loc[train.source == "qipedc", "gloss_normalized"])
        pred_cls = np.array([u_cls[i] for i in U["pred"]])

        def pred_split(mask):
            pc = pred_cls[mask]
            n = len(pc)
            return {"vslgh_only_class": rate(sum((c in tr_v) and (c not in tr_q) for c in pc), n),
                    "class_with_qipedc_train": rate(sum(c in tr_q for c in pc), n),
                    "class_without_train_data": rate(sum((c not in tr_v) and (c not in tr_q) for c in pc), n)}
        common_mask = np.zeros(len(U["rows"]), bool)
        common_mask[ui] = True
        explo_b = {"qipedc_test_all": pred_split(uq), "qipedc_test_common": pred_split(common_mask),
                   "s06_contrast": pred_split(U["rows"].source.values == "vslgh"),
                   "n_classes_vslgh_only": len(tr_v - tr_q), "n_classes_with_qipedc_train": len(tr_q & set(u_cls))}
        c4 = {"dict_run_used": used, "dict_run_config": _cfg_for_json(meta[used]["cfg"]),
              "unified_run": chosen, "unified_run_config": _cfg_for_json(meta[chosen]["cfg"]),
              "dict_runs_not_reported": [{"run": n, "reason": "không khớp cách hài hòa đã chọn; không báo theo "
                                          "PREREGISTRATION.md dòng 23"} for n in dict_names if n != used],
              "sample_size": {"dict": {"classes": len(d_cls), **_hist_summary(meta[used]["metrics"])},
                              "unified": {"classes": len(u_cls), **_hist_summary(meta[chosen]["metrics"])},
                              "common_test_clips": len(common),
                              "dict_test_rows": int(len(D["rows"])), "unified_qipedc_test_rows": int(uq.sum())},
              "main": {"top": {m: {str(k): v for k, v in t.items()} for m, t in main_tab.items()},
                       "mcnemar_top1": {"n10_dict_only": n10, "n01_unified_only": n01, "p": p},
                       "registered": True},
              "exploratory": {"registered": False,
                              "a_unified_restricted_to_dict_labels": (
                                  None if restricted is None else
                                  {"top": {str(k): v for k, v in restricted["unified_restricted"].items()},
                                   "mcnemar_top1": restricted["mcnemar_top1"]}),
                              "a_missing_dict_classes_in_unified": missing_cls,
                              "b_unified_top1_class_origin": explo_b}}

    # ---- provenance ----
    kernel_runs = {}
    for kl in kernels:
        for od, r in kl["runs"].items():
            if od in kernel_runs:
                raise ReportError(3, f"out-dir {od} xuất hiện trong nhiều log kernel ({kernel_runs[od][0]}, {kl['path']})")
            kernel_runs[od] = (kl["path"], r, kl["repo_commit"], kl["branch"])
    prov_runs = {}
    for name in meta:
        d = meta[name]["dir"]
        base = os.path.basename(os.path.normpath(d))
        k = kernel_runs.get(base)
        added = git_added(os.path.join(d, "metrics.json"))
        prov_runs[name] = {"dir": rel(d), "role": meta[name]["role"],
                           "kernel_log": rel(k[0]) if k else None, "repo_commit": k[2] if k else None,
                           "branch": k[3] if k else None, "command": k[1]["command"] if k else None,
                           "seed_log": k[1]["seed"] if k else None, "exit": k[1]["exit"] if k else None,
                           "seed_ckpt": meta[name]["ckpt"]["seed"],
                           "run_config": meta[name]["metrics"].get("run_config"),
                           "effective_config": _cfg_for_json(meta[name]["cfg"]),
                           "sha256_test_logits": sha256(os.path.join(d, "test_logits.npz")),
                           "sha256_ckpt": sha256(os.path.join(d, "stgcn_unified_best.pt")),
                           "results_committed": added}
    prov_kernels = []
    for kl in kernels:
        info = git_commit_info(kl["repo_commit"])
        prov_kernels.append({"path": rel(kl["path"]), "repo_commit": kl["repo_commit"], "branch": kl["branch"],
                             "repo_commit_is_ancestor_of_HEAD": (
                                 None if not kl["repo_commit"] else
                                 subprocess.run(["git", "merge-base", "--is-ancestor", kl["repo_commit"], "HEAD"],
                                                cwd=ROOT, capture_output=True).returncode == 0),
                             "repo_commit_date": info["date"] if info else None,
                             "runs": sorted(kl["runs"]), "duration_s": kl["duration_s"],
                             "reported_total_min": kl["reported_total_min"]})
    ordered = sorted([k for k in prov_kernels if k["repo_commit"]],
                     key=lambda k: (git_commit_info(k["repo_commit"]) or {"unix": 0})["unix"])
    chain = [k["repo_commit"] for k in ordered] + ["HEAD"]
    code_diffs = []
    for a, b in zip(chain, chain[1:]):
        ns = git("diff", "--numstat", a, b, "--", "src/data/harmonized.py", "scripts/train_unified.py",
                 "scripts/shortcut_85.py", "scripts/source_diagnostics.py")
        code_diffs.append({"from": a, "to": b if b != "HEAD" else f"HEAD ({git('rev-parse', '--short', 'HEAD')})",
                           "numstat": ns.splitlines() if ns else []})
    prov_jsons = []
    for p in [args.shortcut_4a] + list(s4b_paths):
        j = read_json(p)
        cmd, com = json_provenance(j)
        prov_jsons.append({"path": rel(p), "command": cmd, "git_commit": com})
    legacy_out = []
    for o, n, jo, jn in legacy:
        cmd, com = json_provenance(jo)
        cmp_ = compare_legacy(jo, jn)
        legacy_out.append({"old": rel(o), "new": rel(n), "old_command": cmd, "old_git_commit": com,
                           "old_added_in": git_added(o), "new_command": jn.get("command"),
                           "new_git_commit": jn.get("git_commit"), **cmp_})
    prereg_log = git("log", "--format=%h|%ct|%ad|%s", "--date=iso", "--", rel(args.prereg)) or ""
    prereg = [dict(zip(("commit", "unix", "date", "subject"), l.split("|", 3))) for l in prereg_log.splitlines()]
    for p in prereg:
        p["unix"] = int(p["unix"])
    last_prereg = max((p["unix"] for p in prereg), default=None)
    for name, pr in prov_runs.items():
        rc = pr["results_committed"]
        pr["results_committed_after_last_prereg_commit"] = (None if rc is None or last_prereg is None
                                                            else rc["unix"] > last_prereg)

    # ---- limitations data ----
    backend_src = os.path.join(ROOT, "backend", "main.py")
    backend = {"model_type_default": None, "ckpt": None, "sha256": None, "same_as_4a_model": None}
    if os.path.isfile(backend_src):
        txt = read_text(backend_src)
        m = re.search(r'os\.getenv\("VSL_MODEL_TYPE",\s*"([^"]+)"\)', txt)
        if m:
            backend["model_type_default"] = m.group(1)
            m2 = re.search(r'"%s":\s*\{"ckpt":\s*"([^"]+)"' % re.escape(m.group(1)), txt)
            if m2:
                backend["ckpt"] = m2.group(1)
                if os.path.isfile(m2.group(1)):
                    inputs.add(m2.group(1), "checkpoint mặc định của backend (chỉ sha256)")
                    backend["sha256"] = sha256(m2.group(1))
                    backend["same_as_4a_model"] = backend["sha256"] == sha256(cur_ckpt)
    live_files = []
    for base in ("backend", os.path.join("src", "inference")):
        for dp, _, fs in os.walk(os.path.join(ROOT, base)):
            live_files += [os.path.join(dp, f) for f in fs if f.endswith(".py")]
    live_uses = sorted(rel(f) for f in live_files if "harmonize" in read_text(f))
    s06_overlap = None
    if args.segments and os.path.isfile(args.segments):
        seg = pd.read_csv(inputs.add(args.segments, "VSL-GH segments (chồng lấn câu S06)"))
        seen = set(seg[seg.signer_id.isin(set(train.signer_id.dropna()))].sentence_id)
        s6 = seg[seg.signer_id == "S06"]
        s06_overlap = rate(int(s6.sentence_id.isin(seen).sum()), len(s6))
    q_rows = man[man.source == "qipedc"]
    limits = {"test_group_n_chosen": {g: test_groups[chosen][g]["top1"]["n"] for g in GROUPS},
              "cross_source_ci_chosen": test_groups[chosen]["cross_source"]["top1"],
              "qipedc_only_excluded_lt2_recordings": dropped,
              "hist_unified_chosen": _hist_summary(meta[chosen]["metrics"]),
              "hist_dict_used": _hist_summary(meta[c4["dict_run_used"]]["metrics"]) if c4 else None,
              "seeds_same_config": {n: sum(same_except(meta[x]["cfg"], meta[n]["cfg"], {"seed"}) for x in meta)
                                    for n in ([chosen] + ([c4["dict_run_used"]] if c4 else []))},
              "qipedc_rows_with_signer_id": rate(int(q_rows.signer_id.notna().sum()), len(q_rows)),
              "manifest_sources": sorted(man.source.unique().tolist()),
              "s06_segments_from_sentences_seen_in_train": s06_overlap,
              "live_path_files_calling_harmonize": live_uses,
              "chosen_process_height": meta[chosen]["cfg"].get("process_height"),
              "backend_default_model": backend,
              "preregistration_commits": prereg,
              "epoch_selection": "epoch tốt nhất của mỗi run chọn theo VAL top-1 tổng (VSL-GH chiếm "
                                 f"{int((val.source == 'vslgh').sum())}/{len(val)} clip VAL), còn biến thể chọn theo balanced VAL"}

    head = git("rev-parse", "--short", "HEAD")
    dirty = git("status", "--porcelain", "--", "scripts", "src", "tests")
    return {"generated_by": {"script": "scripts/report_step4.py",
                             "command": "python scripts/report_step4.py " + " ".join(shlex.quote(a) for a in argv),
                             "git_commit": head, "code_dirty": bool(dirty),
                             "code_dirty_files": dirty.splitlines() if dirty else []},
            "inputs": inputs.as_list(),
            "provenance": {"runs": prov_runs, "jsons": prov_jsons, "legacy_compare": legacy_out,
                           "kernels": prov_kernels,
                           "kernels_total_duration_s": sum(k["duration_s"] or 0 for k in prov_kernels),
                           "kernel_code_diffs": code_diffs,
                           "config_note": "run_config thiếu khóa trim (run trước commit 9b0ade1) được hiểu là trim=True"},
            "4a": s4a_out,
            "4b": {"selection": selection, "trimming": {"val": trimming, "test": trim_test, "vs_baseline": vs_baseline},
                   "test_groups": {"runs": test_groups, "qipedc_only_excluded_lt2_recordings": dropped,
                                   "tie_check": ties},
                   "seed_spread": {"balanced_val": seed_val, "test": seed_spread},
                   "source_classifier": src_cls, "harmonisation_config": harm},
            "4c": c4,
            "limitations_data": limits,
            "review": review}


# ---------------------------------------------------------------------------------------------------------------
# render (only from the results dict)
# ---------------------------------------------------------------------------------------------------------------
def fr(r):
    if r is None:
        return MISSING
    if r["pct"] is None:
        return "n=0"
    if r["k"] is None:
        return f"{r['pct']:.1f}% (n={r['n']})"
    return f"{r['pct']:.1f}% ({r['k']}/{r['n']}) [{r['ci_low']:.1f}, {r['ci_high']:.1f}]"


def fv(x, d=2, sign=False):
    if x is None:
        return MISSING
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def na(x):
    return MISSING if x is None or x == "" else str(x)


def yn(b):
    return MISSING if b is None else ("CÓ" if b else "KHÔNG")


def render(res):
    g, pv, s4a, b, c4, lim = res["generated_by"], res["provenance"], res["4a"], res["4b"], res["4c"], res["limitations_data"]
    sel = b["selection"]
    o = ["# Báo cáo Bước 4a–4c (sinh bởi scripts/report_step4.py)", "",
         f"- Lệnh: `{g['command']}`", f"- HEAD: `{g['git_commit']}`; code_dirty (scripts/, src/, tests/): "
         f"{str(g['code_dirty']).lower()}", "- Luật chọn đăng ký trước: `reports/step4_2026-09-26/PREREGISTRATION.md`. "
         "Chọn chỉ bằng VAL; TEST chỉ đọc lại `test_logits.npz` đã sinh một lần trong kernel; không TTA.",
         "- Mọi số trong báo cáo này có trong `step4_results.json` (cùng dict) hoặc trong JSON đầu vào.", ""]

    # 1. provenance
    o += ["## 1. Provenance", "", "### 1.1 Run", "",
          "| Run | Vai trò | Thư mục | Log kernel | Repo commit (log) | Nhánh | Seed (log / ckpt) | Exit | Kết quả commit (metrics.json) | Sau lần sửa PREREG cuối |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in pv["runs"].items():
        rc = r["results_committed"]
        o.append(f"| {n} | {ROLE_NAMES[r['role']]} | `{r['dir']}` | {na(r['kernel_log'])} | {na(r['repo_commit'])} | "
                 f"{na(r['branch'])} | {na(r['seed_log'])} / {na(r['seed_ckpt'])} | {na(r['exit'])} | "
                 f"{MISSING if rc is None else rc['commit'] + ' ' + rc['date']} | {yn(r['results_committed_after_last_prereg_commit'])} |")
    o += ["", "| Run | Lệnh train (từ log kernel) | run_config (metrics.json) | sha256 test_logits.npz | sha256 stgcn_unified_best.pt |",
          "|---|---|---|---|---|"]
    for n, r in pv["runs"].items():
        o.append(f"| {n} | {('`' + r['command'] + '`') if r['command'] else MISSING} | "
                 f"{MISSING if r['run_config'] is None else '`' + json.dumps(r['run_config'], ensure_ascii=False) + '`'} | "
                 f"`{r['sha256_test_logits']}` | `{r['sha256_ckpt']}` |")
    o += ["", f"Ghi chú cấu hình: {pv['config_note']} (thêm cờ `--no-trim` với mặc định giữ cắt nghỉ; xem diff mã bên dưới).", "",
          "### 1.2 Kernel", "", "| Log | Repo commit | Ngày commit | Nhánh clone | Tổ tiên của HEAD | Run | Thời lượng (s, trường time cuối) | Tổng tự báo (phút) |",
          "|---|---|---|---|---|---|---|---|"]
    for k in pv["kernels"]:
        o.append(f"| `{k['path']}` | {na(k['repo_commit'])} | {na(k['repo_commit_date'])} | {na(k['branch'])} | "
                 f"{yn(k['repo_commit_is_ancestor_of_HEAD'])} | {', '.join(k['runs'])} | {fv(k['duration_s'], 1)} | "
                 f"{fv(k['reported_total_min'], 1)} |")
    o += ["", f"Tổng thời lượng các kernel: {fv(pv['kernels_total_duration_s'], 1)} s "
              f"({fv(pv['kernels_total_duration_s'] / 3600, 2)} giờ).", "",
          "Diff mã giữa các commit kernel (`git diff --numstat`, src/data/harmonized.py, scripts/train_unified.py, "
          "scripts/shortcut_85.py, scripts/source_diagnostics.py):", ""]
    for d in pv["kernel_code_diffs"]:
        o.append(f"- {d['from']} → {d['to']}: " + ("; ".join(f"`{x}`" for x in d["numstat"]) if d["numstat"] else "không đổi"))
    o += ["", "### 1.3 JSON bộ phân loại nguồn", "", "| JSON | command | git_commit |", "|---|---|---|"]
    for j in pv["jsons"]:
        o.append(f"| `{j['path']}` | {('`' + j['command'] + '`') if j['command'] else MISSING} | {na(j['git_commit'])} |")
    if pv["legacy_compare"]:
        o += ["", "So khớp JSON cũ (không provenance) với bản chạy lại:", "",
              "| JSON cũ | commit thêm file | command / git_commit bản cũ | Bản chạy lại | chạy lại trùng | Trường khác | Trường chỉ có ở bản chạy lại |",
              "|---|---|---|---|---|---|---|"]
        for L in pv["legacy_compare"]:
            ad = L["old_added_in"]
            o.append(f"| `{L['old']}` | {MISSING if ad is None else ad['commit'] + ' ' + ad['date']} | "
                     f"{na(L['old_command'])} / {na(L['old_git_commit'])} | `{L['new']}` ({na(L['new_git_commit'])}) | "
                     f"{yn(L['same'])} | {', '.join(L['different_fields'] + L['only_in_old']) or '—'} | "
                     f"{', '.join(L['only_in_new']) or '—'} |")
        o.append("\nBản cũ không ghi `--ckpt`/`--seed`; bản chạy lại dùng mặc định của scripts/shortcut_85.py "
                 f"(`--ckpt {SHORTCUT_DEFAULT_CKPT}`, `--seed 0`) — giả định là bản cũ cũng vậy.")
    o += ["", "### 1.4 File đầu vào (sha256)", "", "| File | Vai trò | sha256 |", "|---|---|---|"]
    o += [f"| `{i['path']}` | {i['role']} | `{i['sha256']}` |" for i in res["inputs"]]

    # 2. 4a
    bal4a = s4a["balanced"]
    o += ["", "## 2. Bước 4a — kiểm tra lối tắt trên các lớp có ở cả hai nguồn", "",
          f"Nguồn số: `{s4a['path']}` (command: {('`' + s4a['command'] + '`') if s4a['command'] else MISSING}; "
          f"git_commit: {na(s4a['git_commit'])}).", "",
          f"Lớp chung: {s4a['shared_classes']}; tập cân bằng {json.dumps(bal4a['n_by_source'], ensure_ascii=False)}; "
          f"ngẫu nhiên {bal4a['chance']}%.", "", "| Đặc trưng | Bộ phân loại nguồn (balanced acc., %) |", "|---|---|",
          f"| all | **{bal4a['all']}** |"]
    o += [f"| chỉ {k} | {v} |" for k, v in bal4a["single_group"].items()]
    cm = s4a["cross_source_current_model"]
    o += ["", f"Model hiện tại = `{s4a['current_model_ckpt']['path']}` (sha256 `{s4a['current_model_ckpt']['sha256']}`); "
              f"baseline trong báo cáo = `{s4a['baseline_ckpt']['path']}` (sha256 `{s4a['baseline_ckpt']['sha256']}`): "
              f"cùng checkpoint: {yn(s4a['same_checkpoint'])}."]
    if cm:
        o += ["", f"Đánh giá chéo nguồn của model hiện tại trên {cm['classes_kept']} lớp chung (loại vì ký khác: "
                  f"{', '.join(cm['excluded_different_sign'])}); k suy ra duy nhất từ % làm tròn và n trong JSON:", "",
              "| Tập | n | Top-1 | Top-5 |", "|---|---|---|---|"]
        for s, lab in (("qipedc_test_only", "QIPEDC TEST (clip chưa thấy)"), ("qipedc_val_test", "QIPEDC VAL+TEST"),
                       ("s06_reference", "S06 cùng lớp (tham chiếu cùng nguồn)")):
            if s in cm:
                e = cm[s]
                o.append(f"| {lab} | {e['n']} | {fr(e['top1']) if e['top1'] else str(e['json_top1']) + '%'} | "
                         f"{fr(e['top5']) if e['top5'] else str(e['json_top5']) + '%'} |")
        chk = s4a["cross_source_vs_baseline_logits"]
        if chk:
            o.append(f"\nKiểm tra chéo với logits TEST của baseline (cùng checkpoint), cột chéo nguồn mục 3.3: "
                     f"trùng: {yn(chk['same'])} (JSON k1/n/k5 = {chk['json']}; logits = {chk['baseline_logits']}).")

    # 3. 4b
    o += ["", "## 3. Bước 4b — đầu vào hài hòa, train lại", "", "### 3.1 Cấu hình hài hòa (sinh từ mã)", "",
          f"Nguồn: {b['harmonisation_config']['source']}.", ""]
    hc = b["harmonisation_config"]
    p = hc["preprocessing_of_chosen"]
    o += [f"- Khớp giữ / bỏ, ngón cái 21/22: `{p.get('joints')}` — {na(hc['doc'].get('joints'))}",
          f"- Tọa độ: {na(hc['doc'].get('coordinates'))}",
          f"- pose z: {'giữ' if p.get('pose_z') else 'bỏ'} (`pose_z={p.get('pose_z')}`); hand z: "
          f"{'giữ' if p.get('hand_z') else 'bỏ'} (`hand_z={p.get('hand_z')}`)",
          f"- Cắt đoạn nghỉ: `trim={p.get('trim')}`, `rest_y={p.get('rest_y')}`, `active_speed={p.get('active_speed')}`, "
          f"`pad_s={p.get('pad_s')}`, `mask_resting_hand={p.get('mask_resting_hand')}`",
          f"- Resample theo thời gian: {na(hc['doc'].get('time'))} `target_len={p.get('target_len')}`, `max_gap_s={p.get('max_gap_s')}`",
          f"- Độ phân giải trích xuất: `process_height={p.get('process_height')}`; extractor `{p.get('extractor')}` "
          f"MediaPipe `{p.get('mediapipe_version')}`",
          f"- Augmentation: {na(hc['augmentation'])}",
          f"- TTA: {hc['tta']}",
          f"- Khác `HARMONIZED_DEFAULT`: `{json.dumps(hc['differs_from_HARMONIZED_DEFAULT'], ensure_ascii=False)}`"]

    o += ["", "### 3.2 Chọn trên VAL (balanced VAL = trung bình VAL top-1 VSL-GH S05 và QIPEDC)", "",
          "| Run | Vai trò | VAL VSL-GH top-1 | VAL QIPEDC top-1 | Balanced VAL | Epoch tốt nhất (VAL tổng) |",
          "|---|---|---|---|---|---|"]
    for r in sel["table"]:
        vb = r["val_by_source"]
        o.append(f"| {r['run']} | {ROLE_NAMES[r['role']]} | "
                 f"{fr(vb.get('vslgh')) if 'vslgh' in vb else 'n/a'} | {fr(vb.get('qipedc')) if 'qipedc' in vb else 'n/a'} | "
                 f"{('**' + fv(r['balanced_val']) + '**') if r['balanced_val'] is not None else 'n/a (không có val_by_source)'} | "
                 f"{na(r['best_epoch'])} |")
    z, rz = sel["z"], sel["resolution"]
    o += ["", f"Giá trị balanced VAL của 1 clip QIPEDC VAL = 100/(2·{sel['n_qipedc_val']}) = "
              f"{fv(sel['one_qipedc_val_clip_points'], 3)} điểm; ngưỡng {sel['threshold']} điểm. "
              "Cờ \"sát ngưỡng\" khi |chênh − 0.5| < giá trị đó.", ""]
    if z["diff"] is not None:
        o.append(f"- Chọn z (độ phân giải gốc): {z['best_other']} − {z['simple']} = {fv(z['diff'], sign=True)} điểm → "
                 f"**{z['chosen']}**{' (SÁT NGƯỠNG)' if z['near_threshold'] else ''}.")
    else:
        o.append(f"- Chọn z: chỉ một ứng viên hợp lệ → **{z['chosen']}**.")
    if rz["run_360"]:
        o.append(f"- 360 px: {rz['run_360']} − {rz['compared_with']} = {fv(rz['diff'], sign=True)} điểm → "
                 f"{'chọn 360 px' if rz['adopted'] else 'giữ độ phân giải gốc'}{' (SÁT NGƯỠNG)' if rz['near_threshold'] else ''}.")
    for s in sel["seed_spread_balanced_val"]:
        o.append(f"- Tham khảo, KHÔNG dùng để chọn: chênh balanced VAL seed {s['seed_a']} → {s['seed_b']} "
                 f"({s['a']} → {s['b']}) = {fv(s['diff_b_minus_a'], sign=True)} điểm.")
    o += ["", f"**Run được chọn theo luật: {sel['chosen']}** (`{json.dumps(sel['chosen_run_config'], ensure_ascii=False)}`)."]

    tg = b["test_groups"]["runs"]
    o += ["", "### 3.3 TEST — 4 nhóm (top-1 và top-5: % (k/n) [Wilson 95%])", "",
          "| Run | Nhóm | Top-1 | Top-5 |", "|---|---|---|---|"]
    for n, gr in tg.items():
        tag = " (không phải ứng viên)" if pv["runs"][n]["role"] == "aux" else ""
        for gname in GROUPS:
            o.append(f"| {n}{tag} | {GROUP_NAMES[gname]} | {fr(gr[gname]['top1'])} | {fr(gr[gname]['top5'])} |")
    o.append(f"\nClip QIPEDC-only bị loại vì lớp có < 2 bản quay: {b['test_groups']['qipedc_only_excluded_lt2_recordings']}.")
    o += ["", "Kiểm tra hòa điểm: `test_logits.npz` lưu float16 nên lớp đúng có thể hòa điểm với lớp khác. Báo cáo dùng "
              "sắp xếp ổn định (hòa → lớp có chỉ số nhỏ hơn đứng trước). Số clip đúng trên toàn TEST của mỗi run: k dùng "
              "[bi quan – lạc quan] / n, và k từ `metrics.json → test_overall` (tính trong kernel trên logits float32):", "",
          "| Run | Top-1: dùng [bi quan – lạc quan] | Top-1 metrics.json | Top-5: dùng [bi quan – lạc quan] | Top-5 metrics.json | Top-10: dùng [bi quan – lạc quan] |",
          "|---|---|---|---|---|---|"]
    for n, tc in b["test_groups"]["tie_check"].items():
        cells = []
        for k in ("1", "5", "10"):
            cells.append(f"{tc[k]['used']} [{tc[k]['pessimistic']} – {tc[k]['optimistic']}] / {tc[k]['n']}")
            if k != "10":
                cells.append(na(tc[k].get("metrics_json_fp32")))
        o.append(f"| {n} | " + " | ".join(cells) + " |")

    tr = b["trimming"]
    o += ["", "### 3.4 Kết luận cắt đoạn nghỉ", ""]
    for t in tr["val"]:
        o.append(f"(i) Luật VAL (PREREGISTRATION phần bổ sung): {t['trimmed']} (cắt) − {t['untrimmed']} (không cắt) = "
                 f"{fv(t['diff'], sign=True)} điểm balanced VAL → cắt đoạn nghỉ "
                 f"{'ĐƯỢC công nhận' if t['credited'] else 'KHÔNG được công nhận'} (ngưỡng 0.5)"
                 f"{' (SÁT NGƯỠNG)' if t['near_threshold'] else ''}.")
    for t in tr["test"]:
        o += ["", f"(ii) TEST cả hai run ({t['trimmed']} cắt vs {t['untrimmed']} không cắt; McNemar chính xác top-1 "
                  "chỉ để mô tả, không đăng ký trước):", "",
              "| Nhóm | Cắt: top-1 | Không cắt: top-1 | Chênh (điểm / clip) | McNemar n10 / n01 / p |", "|---|---|---|---|---|"]
        for gname, e in t["groups"].items():
            mc = e["mcnemar_top1"]
            o.append(f"| {GROUP_NAMES[gname]} | {fr(e['a'])} | {fr(e['b'])} | {fv(e['diff_points'], 1, True)} / "
                     f"{e['diff_k']:+d} | {mc['n10_a_only']} / {mc['n01_b_only']} / {mc['p']:.3g} |")
    vb_ = tr["vs_baseline"]
    o += ["", f"(iii) Run được chọn ({vb_['chosen']}, process_height={vb_['chosen_process_height']}) vs baseline cũ "
              "(đầu vào cũ, không cắt nghỉ) trên cùng nhóm — khác nhau đồng thời ở hài hòa, cắt nghỉ"
              f"{' và độ phân giải' if vb_['chosen_process_height'] else ''}, nên chênh lệch KHÔNG quy riêng cho cắt nghỉ:", "",
          "| Nhóm | Được chọn: top-1 | Baseline: top-1 | Chênh (điểm / clip) | McNemar n10 / n01 / p |", "|---|---|---|---|---|"]
    for gname, e in vb_["groups"].items():
        mc = e["mcnemar_top1"]
        o.append(f"| {GROUP_NAMES[gname]} | {fr(e['a'])} | {fr(e['b'])} | {fv(e['diff_points'], 1, True)} / {e['diff_k']:+d} | "
                 f"{mc['n10_a_only']} / {mc['n01_b_only']} / {mc['p']:.3g} |")
    heights = ", ".join("gốc" if h == "None" else f"{h} px" for h in vb_["ablation_process_heights"])
    if tr["val"]:
        credited = all(t["credited"] for t in tr["val"])
        o += ["", f"**Kết luận:** ablation cắt nghỉ chạy ở độ phân giải {heights}. Theo luật VAL đăng ký trước, cắt đoạn "
                  f"nghỉ {'được' if credited else 'KHÔNG được'} công nhận là có ích; bảng (ii) chỉ để mô tả. "
                  "So sánh (iii) với baseline cũ đo tác động gộp của cả gói hài hòa, không riêng cắt nghỉ."]

    o += ["", "### 3.5 Dao động seed", "",
          "Chênh = seed sau − seed trước; theo điểm % và theo số clip đúng (k). Không dùng để chọn.", "",
          "| Cặp | Nhóm | Top-1: seed trước → sau | Chênh top-1 (điểm / clip) | Top-5: seed trước → sau | Chênh top-5 (điểm / clip) |",
          "|---|---|---|---|---|---|"]
    for s in b["seed_spread"]["test"]:
        for gname, e in s["groups"].items():
            t1, t5 = e["top1"], e["top5"]
            o.append(f"| {s['a']} (seed {s['seed_a']}) → {s['b']} (seed {s['seed_b']}) | {GROUP_NAMES[gname]} | "
                     f"{fr(t1['a'])} → {fr(t1['b'])} | {fv(t1['diff_points'], 1, True)} / {t1['diff_k']:+d} | "
                     f"{fr(t5['a'])} → {fr(t5['b'])} | {fv(t5['diff_points'], 1, True)} / {t5['diff_k']:+d} |")

    sc = b["source_classifier"]
    if sc:
        keys = list(sc[0]["single_group"])
        o += ["", "### 3.6 Bộ phân loại nguồn trên đầu vào hài hòa (tập cân bằng của 4a)", "",
              "| JSON | hand z | keypoint QIPEDC | git_commit | all | " + " | ".join(keys) + " |",
              "|---" * (5 + len(keys)) + "|"]
        for s in sc:
            o.append(f"| `{s['path']}` | {s['hand_z']} | {s['qipedc_kps_dir']} | {na(s['git_commit'])} | {s['all']} | "
                     + " | ".join(str(s["single_group"].get(k)) for k in keys) + " |")

    # 4. 4c
    o += ["", "## 4. Bước 4c — model từ điển (chỉ QIPEDC) vs model gộp được chọn, cùng clip QIPEDC TEST", ""]
    if c4 is None:
        o.append(f"{MISSING}: không có run từ điển trong lệnh.")
    else:
        ss = c4["sample_size"]
        o += [f"- Run từ điển dùng: **{c4['dict_run_used']}** (`{json.dumps(c4['dict_run_config'], ensure_ascii=False)}`); "
              f"model gộp: **{c4['unified_run']}** (`{json.dumps(c4['unified_run_config'], ensure_ascii=False)}`). "
              "Cấu hình trùng mọi khóa trừ `sources`."]
        for d in c4["dict_runs_not_reported"]:
            o.append(f"- Run từ điển còn lại: {d['run']} — {d['reason']} (không in số).")
        o += ["", "| Model | Số lớp | Lớp có dữ liệu train | Clip train | Lớp có ≤ 2 clip train | Hist (clip/lớp: số lớp) |",
              "|---|---|---|---|---|---|"]
        for key, lab in (("dict", "từ điển"), ("unified", "gộp")):
            h = ss[key]
            o.append(f"| {lab} | {h['classes']} | {h['classes_with_train_data']} | {h['train_clips']} | {h['classes_le_2_clips']} | "
                     f"`{json.dumps(h['hist'])}` |")
        o += ["", f"Clip chung (QIPEDC TEST có lớp thuộc cả hai không gian nhãn): {ss['common_test_clips']} "
                  f"(dòng TEST của model từ điển {ss['dict_test_rows']}; dòng QIPEDC TEST của model gộp {ss['unified_qipedc_test_rows']}).", "",
              "**Kết quả chính (đã đăng ký trước)** — % (k/n) [Wilson 95%]:", "",
              "| Model | Top-1 | Top-5 | Top-10 |", "|---|---|---|---|"]
        for key, lab in (("dict", f"từ điển ({c4['dict_run_used']})"), ("unified", f"gộp ({c4['unified_run']})")):
            t = c4["main"]["top"][key]
            o.append(f"| {lab} | {fr(t['1'])} | {fr(t['5'])} | {fr(t['10'])} |")
        mc = c4["main"]["mcnemar_top1"]
        o += ["", f"McNemar chính xác top-1: từ điển đúng & gộp sai n10 = {mc['n10_dict_only']}, ngược lại n01 = "
                  f"{mc['n01_unified_only']}, p = {mc['p']:.3g}.", "",
              "**Phân tích thăm dò — không đăng ký trước, không dùng để chọn:**", ""]
        ex = c4["exploratory"]
        a = ex["a_unified_restricted_to_dict_labels"]
        if a:
            t = a["top"]
            o += ["(a) Model gộp với logits giới hạn về đúng không gian nhãn của model từ điển, cùng clip:", "",
                  "| Model | Top-1 | Top-5 | Top-10 |", "|---|---|---|---|",
                  f"| gộp, giới hạn nhãn | {fr(t['1'])} | {fr(t['5'])} | {fr(t['10'])} |",
                  "", f"McNemar top-1 (từ điển vs gộp giới hạn): n10 = {a['mcnemar_top1']['n10_dict_only']}, n01 = "
                      f"{a['mcnemar_top1']['n01_unified_only']}, p = {a['mcnemar_top1']['p']:.3g}.", ""]
        else:
            o.append(f"(a) {MISSING}: lớp của model từ điển không có trong model gộp: {ex['a_missing_dict_classes_in_unified']}.")
        eb = ex["b_unified_top1_class_origin"]
        o += [f"(b) Dự đoán top-1 của model gộp rơi vào lớp chỉ-VSL-GH ({eb['n_classes_vslgh_only']} lớp có train VSL-GH, "
              f"không có train QIPEDC) vs lớp có train QIPEDC ({eb['n_classes_with_qipedc_train']} lớp):", "",
              "| Tập clip | Lớp chỉ-VSL-GH | Lớp có QIPEDC | Lớp không có train |", "|---|---|---|---|"]
        for key, lab in (("qipedc_test_all", "mọi clip QIPEDC TEST"), ("qipedc_test_common", "clip chung của 4c"),
                         ("s06_contrast", "S06 (đối chứng)")):
            e = eb[key]
            o.append(f"| {lab} | {fr(e['vslgh_only_class'])} | {fr(e['class_with_qipedc_train'])} | {fr(e['class_without_train_data'])} |")
        o.append("\nChỉ là chỉ báo cho giả thuyết \"model gộp học phân biệt nguồn\", không phải kiểm định.")

    # 5. limitations
    L = lim
    bd = L["backend_default_model"]
    o += ["", "## 5. Giới hạn", "",
          "- Cỡ mẫu TEST của run được chọn: " + "; ".join(f"{GROUP_NAMES[k]} n={v}" for k, v in L["test_group_n_chosen"].items())
          + f". Chéo nguồn: {fr(L['cross_source_ci_chosen'])} — CI rất rộng. Clip QIPEDC-only bị loại vì < 2 bản quay: "
            f"{L['qipedc_only_excluded_lt2_recordings']}.",
          "- Wilson CI giả định các clip độc lập; clip cùng lớp / cùng bản quay / cùng người ký tương quan nên CI thật rộng hơn.",
          f"- Ít mẫu mỗi lớp: model gộp {L['hist_unified_chosen']['classes_le_2_clips']} lớp có ≤ 2 clip train"
          + (f"; model từ điển {L['hist_dict_used']['classes_le_2_clips']}/{L['hist_dict_used']['classes_with_train_data']} lớp "
             f"có ≤ 2 clip train ({L['hist_dict_used']['train_clips']} clip train)." if L["hist_dict_used"] else "."),
          "- Số seed cùng cấu hình: " + "; ".join(f"{k}: {v}" for k, v in L["seeds_same_config"].items())
          + " (1 = một seed duy nhất; so sánh 360 px và 4c dựa trên một seed).",
          f"- QIPEDC không có nhãn người ký: dòng QIPEDC có signer_id {fr(L['qipedc_rows_with_signer_id'])}; không split được theo người ký.",
          "- S06 đo người ký mới, không đo câu mới: "
          + (f"đoạn S06 đến từ câu mà người ký train cũng ký: {fr(L['s06_segments_from_sentences_seen_in_train'])}."
             if L["s06_segments_from_sentences_seen_in_train"] else f"{MISSING} (thiếu segments.csv)."),
          "- Đường live chưa dùng `harmonize()`: file trong backend/ và src/inference/ gọi harmonize: "
          + (", ".join(L["live_path_files_calling_harmonize"]) or "không có") + ".",
          f"- Độ phân giải của run được chọn: process_height={L['chosen_process_height']}. "
          + ("Nếu giữ lựa chọn này, đường realtime (webcam 640×480) phải giảm về cùng chiều cao trước MediaPipe và có test "
             "tương đương train–realtime — việc SAU khi người dùng duyệt (PREREGISTRATION dòng 11–12)."
             if L["chosen_process_height"] else "Độ phân giải gốc; đường realtime không cần đổi độ phân giải."),
          "- Phần bổ sung của PREREGISTRATION viết sau khi đã biết kết quả chọn z; commit của PREREGISTRATION: "
          + "; ".join(f"{p['commit']} {p['date']}" for p in L["preregistration_commits"])
          + " (so với cột \"Sau lần sửa PREREG cuối\" ở mục 1.1).",
          f"- Nguồn trong manifest: {', '.join(L['manifest_sources'])} — HCMUE không dùng để train hay đo.",
          f"- Model mặc định của backend: VSL_MODEL_TYPE mặc định `{na(bd['model_type_default'])}` → `{na(bd['ckpt'])}` "
          f"(sha256 {na(bd['sha256'])}); trùng model được kiểm ở 4a: {yn(bd['same_as_4a_model'])}.",
          f"- Chọn epoch: {L['epoch_selection']}.",
          "- `git_commit` trong JSON của scripts/shortcut_85.py chỉ là HEAD, không ghi trạng thái bẩn của mã.",
          "- Logits, checkpoint và log kernel bị gitignore: clone sạch không tái tạo được báo cáo; sha256 ở mục 1.4 là bằng chứng thay thế."]

    o += ["", "## 6. Review", ""]
    o.append(res["review"].rstrip() if res["review"] else "Chưa có kết quả vslt-reviewer (sinh lại với `--review-file`).")
    return "\n".join(o) + "\n"


def to_json(res):
    def clean(x):
        if isinstance(x, dict):
            return {str(k): clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [clean(v) for v in x]
        if isinstance(x, np.generic):
            return x.item()
        return x
    return json.dumps(clean(res), ensure_ascii=False, indent=2) + "\n"


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="NAME=DIR, native-resolution z variants (candidates)")
    ap.add_argument("--run-360", help="NAME=DIR, chosen z variant at 360 px (candidate vs the native choice)")
    ap.add_argument("--aux-runs", nargs="*", default=[], help="NAME=DIR, reported only, never selected")
    ap.add_argument("--dict-run", help="dictionary-word model, native resolution")
    ap.add_argument("--dict-run-360", help="dictionary-word model, 360 px")
    ap.add_argument("--manifest-dir", default="data/splits/unified")
    ap.add_argument("--shortcut-4a", default="reports/step4_2026-09-26/4a/shortcut_85.json")
    ap.add_argument("--shortcut-4b", nargs="+", default=None, help="default: every shortcut_85_harmonized* in 4b/")
    ap.add_argument("--shortcut-legacy-compare", nargs="*", default=[], help="OLD=NEW JSON pairs")
    ap.add_argument("--kernel-logs", nargs="*", default=[])
    ap.add_argument("--review-file")
    ap.add_argument("--prereg", default="reports/step4_2026-09-26/PREREGISTRATION.md")
    ap.add_argument("--segments", default="data/processed/vslgh_segments/segments.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    if args.out and not args.json_out:
        ap.error("--json-out là bắt buộc khi có --out")
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    os.chdir(ROOT)
    try:
        res = build(args, argv)
        text = render(res)
        js = to_json(res)
    except ReportError as e:
        print(f"report_step4: {e}", file=sys.stderr)
        return e.code
    except AssertionError as e:
        print(f"report_step4: assertion failed: {e}", file=sys.stderr)
        return 1
    for path, content in ((args.out, text), (args.json_out, js)):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    print(f"wrote {rel(args.out)} and {rel(args.json_out)}; chosen: {res['4b']['selection']['chosen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
