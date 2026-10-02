"""
Pre-registered, ONE-TIME evaluation on the 30 test sentences of the VSL-GH sentence split v1 (plan 13 §3.12), and the
K3 reproduction protocol of the old audit (plan 13 §0.7, protocol `repro_v2`).

  python scripts/eval_sentsplit.py --prereg reports/retrain_<D>/preregistration.json --protocol sentsplit_v1 \
         --manifest reports/retrain_<D>/artifacts_manifest.json --manifest reports/retrain_<D>/vit5_manifest.json \
         --out reports/retrain_<D>/eval/test_eval.json
  python scripts/eval_sentsplit.py --recompute-from reports/retrain_<D>/eval/test_eval.json --out _work/<x>.json

Every parameter is READ from the preregistration (`evaluation_protocol` for sentsplit_v1, `evaluation_protocol_repro_v2`
for repro_v2) — nothing below is a tunable constant of the run. `protocol_template(name)` is the code form of plan 13
§3.12 / §0.7 that scripts/retrain_preregister.py (B5) copies into the preregistration; this script then refuses a
protocol whose algorithm fields it does not implement exactly (rng, interpolation, BLEU options, ...).

Preregistration keys read: `evaluation_protocol[_repro_v2]`, `sentence_split{path, sha256}`, `libs_local{sacrebleu,
numpy}` (must equal the running versions), `vocab{sha256}` (sentsplit_v1) / `vocab_full_reference{sha256}` (repro_v2),
`inputs` entries {path, sha256|lf_sha256} (matched to the protocol's FILE inputs by resolved path; the canonical json entry
is mandatory), `evaluation_output[_repro_v2]` (the only accepted --out) and `test_keypoints_digest[_repro_v2]` (sha256 of
the "<id>.npy <sha256>" lines of the selected test clips sorted by id). Model files are matched against the --manifest
entries by FULL relative path (`protocol.manifest_rel_paths`), never by base name (mid review 13, E1-E3).

sentsplit_v1 (§3.12): test set = S06 x T (select_vslgh_samples(..., "test", split)), exactly `expected_n` clips; CSLR
on CPU (model kwargs from the checkpoint config), greedy CTC decode; WER = compute_wer(pred glosses, RAW reference
glosses) with S/D/I (+ vocab-encoded WER and OOV for reference only); BLEU Mode A (oracle gloss -> ViT5) and Mode B
(CSLR -> ViT5) with sacrebleu BLEU(tokenize, smooth_method, lowercase); CI = PAIRED sentence bootstrap: one
numpy.random.RandomState(seed), the same `idx` per resample for WER (+ S/D/I rates), BLEU A, BLEU B and A - B;
percentiles with numpy's default (linear) interpolation. Point estimates use all clips.
repro_v2 (§0.7): the exact algorithm of reports/audit_round2/run_v2_cslr_bootstrap.py:29-133 (global
np.random.seed, BLEU bootstrap on the unseen sentences, then plain-Levenshtein WER bootstrap on all S06 clips continuing
the same RNG stream).

Once only: --out must be the registered `evaluation_output` and must not exist (exit 2); an exclusive run marker
`<evaluation_output>.started` is created (mode "x") after every input check and BEFORE the first test clip is read, so a
second run - into any path, even after a crash - is refused (exit 2); code must be clean (exit 2); the commit that added
the preregistration must be an ancestor of HEAD and the only commit touching it (exit 2). Inputs are checked BEFORE any test sample is loaded (exit 2/3); once predictions
exist they are printed to the log (PER_SAMPLE line) before metrics so an error afterwards loses nothing.
Exit codes: 0 ok; 2 refused (arguments, output exists, dirty code, preregistration not committed / not an ancestor,
library version or protocol mismatch, missing input); 3 data / digest mismatch (count, keypoints, sha256 vs
preregistration / manifests / checkpoint metadata, recompute differs).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPT = "scripts/eval_sentsplit.py"
PROTOCOLS = ("sentsplit_v1", "repro_v2")
OLD_RESULTS = "reports/audit_round2/v2_cslr_reliability.json"
CODE_PATHS = ("src", "scripts", "configs", "train.py")


class EvalError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------------------------------------------------
# Protocol (code form of plan 13 §3.12 / §0.7; copied into the preregistration by B5)
# ---------------------------------------------------------------------------------------------------------------------
def protocol_template(name):
    common_translation = {
        "source_normalizer": "src.translation.text_normalizer.normalize_vsl_source",
        "target_normalizer": "src.translation.text_normalizer.normalize_vietnamese_target",
        "tokenizer": {"max_length": 128, "padding": True, "truncation": True},
        "generate": {"num_beams": 4, "max_length": 64, "do_sample": False},
        "batching": "all sources of a mode in one batch",
        "decode": {"skip_special_tokens": True},
        "post_normalizer": "normalize_vietnamese_target",
        "device": "cpu",
        "fallback_stage1": False,
    }
    if name == "sentsplit_v1":
        return {
            "name": "sentsplit_v1",
            "plan_ref": "docs/plans/13-train-lai-checkpoint-thieu.md §3.12",
            "test_set": {"selection": "select_vslgh_samples(canonical, 'test', sentence_split)", "split": "test",
                         "expected_n": 30, "signers": ["S06"], "sentence_ids": "sentence_split.test_ids",
                         "missing_keypoints": "stop (never drop a clip)"},
            "inputs": {"canonical_json": "data/external/vsl_gh/dataset_canonical.json",
                       "keypoints_dir": "data/external/vsl_gh/keypoints_frontal",
                       "vocab": "data/external/vsl_gh/gloss_vocab_canonical.txt",
                       "cslr_checkpoint": "checkpoints/cslr_best.pt",
                       "vit5_model_dir": "checkpoints/vit5_stage2/best_model"},
            "manifest_rel_paths": {"cslr_checkpoint": "k2/cslr_best.pt", "vit5_model_dir": "vit5_stage2/best_model"},
            "cslr": {"dataset": {"conversion_mode": "semantic", "normalize": True}, "device": "cpu", "batch_size": 8,
                     "autocast": False, "decode": "ctc_greedy_decode + tokens_to_words",
                     "model": {"from_checkpoint_config": ["hidden_size", "num_gru_layers", "dropout"],
                               "fixed": {"num_joints": 67, "in_channels": 3, "channel_dims": [64, 64, 128],
                                         "temporal_downsample": 2}}},
            "wer": {"function": "src.metrics.cslr_metrics.compute_wer",
                    "references": "raw gloss_sequence of the clip (strip, drop empty) - NOT vocab-encoded",
                    "secondary": "wer_vocab_encoded (refs encoded with the vocab, as evaluate_cslr) - reference only"},
            "translation": dict(common_translation),
            "bleu": {"library": "sacrebleu", "class": "sacrebleu.metrics.BLEU", "tokenize": "13a",
                     "smooth_method": "exp", "lowercase": False},
            "bootstrap": {"rng": "numpy.random.RandomState", "seed": 42, "n_resamples": 1000, "paired": True,
                          "unit": "clip (= sentence: S06 has one clip per sentence)", "ci_level": 95,
                          "percentiles": [2.5, 97.5], "interpolation": "linear",
                          "statistics": ["wer", "sub_rate", "del_rate", "ins_rate", "bleu_mode_a", "bleu_mode_b",
                                         "delta_a_minus_b"]},
            "comparison_to_old": {"source": OLD_RESULTS,
                                  "keys": {"bleu_mode_a": "bleu_bootstrap_30_unseen.mode_a_oracle",
                                           "bleu_mode_b": "bleu_bootstrap_30_unseen.mode_b_cslr"},
                                  "rule": "descriptive only: is the old point estimate inside the new 95% CI"},
        }
    if name == "repro_v2":
        return {
            "name": "repro_v2",
            "plan_ref": "docs/plans/13-train-lai-checkpoint-thieu.md §0.7 (K3); algorithm of "
                        "reports/audit_round2/run_v2_cslr_bootstrap.py:29-133",
            "test_set": {"selection": "VSLGHContinuousDataset(split='test') without sentence split (all S06 clips)",
                         "split": "test", "expected_n": 300, "signers": ["S06"],
                         "unseen_rule": "sentence_id >= 'SENT271'", "expected_unseen": 30,
                         "missing_keypoints": "stop (never drop a clip)"},
            "inputs": {"canonical_json": "data/external/vsl_gh/dataset_canonical.json",
                       "keypoints_dir": "data/external/vsl_gh/keypoints_frontal",
                       "vocab": "_work/_plan13_tmp/k3/gloss_vocab_canonical.txt",
                       "cslr_checkpoint": "_work/_plan13_tmp/k3/cslr_best.pt",
                       "vit5_model_dir": "_work/_plan13_tmp/k3/vit5_stage2/best_model"},
            "manifest_rel_paths": {"cslr_checkpoint": "k3/cslr_best.pt", "vit5_model_dir": "k3/vit5_stage2/best_model"},
            "cslr": {"dataset": {"conversion_mode": "semantic", "normalize": True}, "device": "cpu", "batch_size": 8,
                     "autocast": False, "decode": "ctc_greedy_decode + tokens_to_words",
                     "model": {"from_checkpoint_config": ["hidden_size", "num_gru_layers", "dropout"],
                               "fixed": {"num_joints": 67, "in_channels": 3, "channel_dims": [64, 64, 128],
                                         "temporal_downsample": 2}}},
            "translation": dict(common_translation),
            "bleu": {"library": "sacrebleu", "function": "sacrebleu.corpus_bleu", "defaults": True},
            "bootstrap": {"rng": "numpy.random.seed (global)", "seed": 42, "n_resamples": 1000,
                          "order": "BLEU on unseen (A, B, A-B with one idx) then WER on all clips, same RNG stream",
                          "percentiles": [2.5, 97.5], "interpolation": "linear",
                          "wer_edit": "plain Levenshtein edit count on raw gloss lists"},
            "comparison_to_old": {"source": OLD_RESULTS,
                                  "keys": {"bleu_mode_a": "bleu_bootstrap_30_unseen.mode_a_oracle",
                                           "bleu_mode_b": "bleu_bootstrap_30_unseen.mode_b_cslr",
                                           "wer_300": "cslr_wer_bootstrap_300"},
                                  "rule": "descriptive only: is the old point estimate inside the new 95% CI"},
        }
    raise EvalError(2, f"unknown protocol {name!r}; expected one of {PROTOCOLS}")


PREREG_KEYS = {
    "sentsplit_v1": {"protocol": "evaluation_protocol", "output": "evaluation_output",
                     "kp_digest": "test_keypoints_digest"},
    "repro_v2": {"protocol": "evaluation_protocol_repro_v2", "output": "evaluation_output_repro_v2",
                 "kp_digest": "test_keypoints_digest_repro_v2"},
}
FILE_INPUTS = ("canonical_json", "vocab", "cslr_checkpoint")  # directories: keypoints -> kp digest, ViT5 -> manifests
REQUIRED_INPUT_ENTRIES = ("canonical_json",)


def run_marker_path(out_path):
    """Exclusive marker of the one evaluation run, next to the registered output."""
    p = Path(out_path)
    return p.with_name(p.name + ".started")


def same_path(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


SUPPORTED = {
    "sentsplit_v1": {("bootstrap", "rng"): "numpy.random.RandomState", ("bootstrap", "paired"): True,
                     ("bootstrap", "interpolation"): "linear", ("bleu", "library"): "sacrebleu",
                     ("bleu", "class"): "sacrebleu.metrics.BLEU", ("translation", "fallback_stage1"): False,
                     ("translation", "device"): "cpu", ("cslr", "device"): "cpu", ("cslr", "autocast"): False},
    "repro_v2": {("bootstrap", "rng"): "numpy.random.seed (global)", ("bootstrap", "interpolation"): "linear",
                 ("bleu", "function"): "sacrebleu.corpus_bleu", ("bleu", "defaults"): True,
                 ("translation", "fallback_stage1"): False, ("translation", "device"): "cpu",
                 ("cslr", "device"): "cpu", ("cslr", "autocast"): False},
}


def check_protocol(protocol, name):
    if not isinstance(protocol, dict) or protocol.get("name") != name:
        raise EvalError(2, f"preregistration protocol name {protocol.get('name') if isinstance(protocol, dict) else None!r} != {name!r}")
    for (sec, key), want in SUPPORTED[name].items():
        got = (protocol.get(sec) or {}).get(key)
        if got != want:
            raise EvalError(2, f"protocol {name}: {sec}.{key} = {got!r}; this script implements only {want!r}")
    b = protocol["bootstrap"]
    pct = b.get("percentiles")
    if not isinstance(pct, list) or len(pct) != 2 or not all(isinstance(x, (int, float)) for x in pct):
        raise EvalError(2, "protocol: bootstrap.percentiles must be a list of two numbers")
    for k in ("seed", "n_resamples"):
        if not isinstance(b.get(k), int) or isinstance(b.get(k), bool) or b[k] < 0:
            raise EvalError(2, f"protocol: bootstrap.{k} must be a non-negative integer")
    return protocol


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def lf_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def pkg_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:  # noqa: BLE001
        return None


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    return r.returncode, r.stdout.strip()


def git_state(prereg_path):
    """{head, code_dirty, dirty_lines, prereg_commit, prereg_is_ancestor} (patched in tests)."""
    rc, head = _git("rev-parse", "HEAD")
    if rc != 0:
        raise EvalError(2, "git rev-parse HEAD failed")
    rel = os.path.relpath(os.path.abspath(prereg_path), str(ROOT)).replace("\\", "/")
    rc, dirty = _git("status", "--porcelain", "--", *CODE_PATHS, rel)
    if rc != 0:
        raise EvalError(2, "git status failed")
    rc, log = _git("log", "--format=%H", "--", rel)
    commits = [c for c in log.splitlines() if c.strip()] if rc == 0 else []
    first = commits[-1] if commits else None
    is_anc = False
    if first:
        rc_a, _ = _git("merge-base", "--is-ancestor", first, "HEAD")
        is_anc = rc_a == 0
    return {"head": head, "code_dirty": bool(dirty.strip()), "dirty_lines": dirty.splitlines(),
            "prereg_commit": first, "prereg_n_commits": len(commits), "prereg_is_ancestor": is_anc}


def manifest_sha_index(paths):
    """{relative path: {sha256, ...}} from archive manifests (files[].rel_path/sha256) or SHA256SUMS files (archive
    names, "/" stored as "__"). Keys are FULL relative paths, never base names (mid review 13, E2)."""
    idx = {}
    for p in paths:
        p = resolve(p)
        if not p.is_file():
            raise EvalError(2, f"manifest not found: {p}")
        text = p.read_text(encoding="utf-8")
        entries = []
        try:
            m = json.loads(text)
            entries = [(f["rel_path"], f["sha256"]) for f in m["files"]]
        except (json.JSONDecodeError, KeyError, TypeError):
            for line in text.splitlines():
                h, sep, n = line.partition("  ")
                if sep and len(h) == 64:
                    entries.append((n, h))
        if not entries:
            raise EvalError(2, f"no file entries in manifest {p}")
        for rel, h in entries:
            key = rel.replace("\\", "/").replace("__", "/").strip("/")
            idx.setdefault(key, set()).add(h)
    return idx


def check_against_manifests(file_shas, idx):
    """Every model file's sha256 must appear in the manifests under the SAME full relative path
    ({"vit5_stage2/best_model/config.json": sha256, ...}); a stage 1 file put in place of stage 2 is refused."""
    bad = [rel for rel, h in sorted(file_shas.items()) if h not in idx.get(rel, set())]
    if bad:
        raise EvalError(3, f"sha256 not found in the given manifests: {bad}")


# ---------------------------------------------------------------------------------------------------------------------
# Metrics (pure; used by the run and by --recompute-from)
# ---------------------------------------------------------------------------------------------------------------------
def _bleu_scorer(protocol):
    from sacrebleu.metrics import BLEU
    b = protocol["bleu"]
    return BLEU(tokenize=b["tokenize"], smooth_method=b["smooth_method"], lowercase=b["lowercase"])


def _ci(values, protocol):
    import numpy as np
    lo, hi = np.percentile(np.asarray(values, dtype=float), protocol["bootstrap"]["percentiles"])
    return [float(lo), float(hi)]


def metrics_sentsplit_v1(per_sample, protocol):
    import numpy as np
    from src.metrics.cslr_metrics import compute_wer
    n = len(per_sample)
    hyps = [s["pred_gloss"] for s in per_sample]
    refs = [s["ref_gloss"] for s in per_sample]
    wer = compute_wer(hyps, refs)
    S = np.array([s["S"] for s in per_sample]); D = np.array([s["D"] for s in per_sample])
    I = np.array([s["I"] for s in per_sample]); N = np.array([len(s["ref_gloss"]) for s in per_sample])
    if int(S.sum()) != wer["substitutions"] or int(D.sum()) != wer["deletions"] or int(I.sum()) != wer["insertions"]:
        raise EvalError(3, "per-sample S/D/I do not add up to compute_wer")
    wer_enc = compute_wer(hyps, [s["ref_gloss_vocab_encoded"] for s in per_sample])
    n_oov = sum(s["n_ref_oov"] for s in per_sample)

    bleu = _bleu_scorer(protocol)
    refs_t = [s["reference"] for s in per_sample]
    hyp_a = [s["mode_a_output"] for s in per_sample]
    hyp_b = [s["mode_b_output"] for s in per_sample]
    score_a = bleu.corpus_score(hyp_a, [refs_t])
    score_b = bleu.corpus_score(hyp_b, [refs_t])
    signature = str(bleu.get_signature())

    bp = protocol["bootstrap"]
    rng = np.random.RandomState(bp["seed"])
    boot = {k: [] for k in ("wer", "sub_rate", "del_rate", "ins_rate", "bleu_mode_a", "bleu_mode_b", "delta_a_minus_b")}
    for _ in range(bp["n_resamples"]):
        idx = rng.choice(n, n, replace=True)
        nref = N[idx].sum()
        boot["wer"].append(float((S[idx].sum() + D[idx].sum() + I[idx].sum()) / nref * 100.0))
        boot["sub_rate"].append(float(S[idx].sum() / nref * 100.0))
        boot["del_rate"].append(float(D[idx].sum() / nref * 100.0))
        boot["ins_rate"].append(float(I[idx].sum() / nref * 100.0))
        r = [refs_t[i] for i in idx]
        a = bleu.corpus_score([hyp_a[i] for i in idx], [r]).score
        b = bleu.corpus_score([hyp_b[i] for i in idx], [r]).score
        boot["bleu_mode_a"].append(float(a))
        boot["bleu_mode_b"].append(float(b))
        boot["delta_a_minus_b"].append(float(a - b))
    ci = {k: _ci(v, protocol) for k, v in boot.items()}
    n_ref, edits = int(N.sum()), int(S.sum() + D.sum() + I.sum())
    delta = float(score_a.score - score_b.score)
    return {
        "n_clips": n,
        "wer": {"wer": wer["wer"], "wer_exact": edits / n_ref * 100.0 if n_ref else None,
                "S": wer["substitutions"], "D": wer["deletions"], "I": wer["insertions"],
                "sub_rate": wer["sub_rate"], "del_rate": wer["del_rate"], "ins_rate": wer["ins_rate"],
                "N_ref": wer["total_ref_words"], "N_hyp": wer["total_hyp_words"],
                "ci_95": ci["wer"], "ci_95_sub_rate": ci["sub_rate"], "ci_95_del_rate": ci["del_rate"],
                "ci_95_ins_rate": ci["ins_rate"]},
        "wer_vocab_encoded": {"wer": wer_enc["wer"], "S": wer_enc["substitutions"], "D": wer_enc["deletions"],
                              "I": wer_enc["insertions"], "note": "reference only (as evaluate_cslr; OOV refs -> <unk>)"},
        "oov": {"n_ref_tokens": n_ref, "n_ref_tokens_not_in_vocab": n_oov,
                "ratio": (n_oov / n_ref) if n_ref else None},
        "bleu_mode_a": {"score": float(score_a.score), "ci_95": ci["bleu_mode_a"], "signature": signature},
        "bleu_mode_b": {"score": float(score_b.score), "ci_95": ci["bleu_mode_b"], "signature": signature},
        "delta": {"score": delta, "ci_95": ci["delta_a_minus_b"],
                  "ci_contains_zero": bool(ci["delta_a_minus_b"][0] <= 0.0 <= ci["delta_a_minus_b"][1]),
                  "note": "descriptive; not a significance test"},
        "bootstrap": {"rng": bp["rng"], "seed": bp["seed"], "n_resamples": bp["n_resamples"], "paired": True,
                      "percentiles": bp["percentiles"]},
    }


def _plain_edit_distance(ref, hyp):
    """Exactly the DP of reports/audit_round2/run_v2_cslr_bootstrap.py:99-109."""
    import numpy as np
    dp = np.zeros((len(ref) + 1, len(hyp) + 1), dtype=int)
    for i in range(len(ref) + 1):
        dp[i][0] = i
    for j in range(len(hyp) + 1):
        dp[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return int(dp[len(ref)][len(hyp)])


def metrics_repro_v2(per_sample, protocol):
    """Re-implements run_v2_cslr_bootstrap.py:29-133 (global RNG, same draw order)."""
    import numpy as np
    import sacrebleu
    unseen = [s for s in per_sample if s["sentence_id"] >= "SENT271"]
    refs = [s["reference"] for s in unseen]
    hyp_a = [s["mode_a_output"] for s in unseen]
    hyp_b = [s["mode_b_output"] for s in unseen]
    base_a = sacrebleu.corpus_bleu(hyp_a, [refs]).score
    base_b = sacrebleu.corpus_bleu(hyp_b, [refs]).score
    bp = protocol["bootstrap"]
    np.random.seed(bp["seed"])
    boot_a, boot_b, boot_d = [], [], []
    n = len(unseen)
    for _ in range(bp["n_resamples"]):
        idx = np.random.choice(n, size=n, replace=True)
        b_refs = [refs[i] for i in idx]
        sa = sacrebleu.corpus_bleu([hyp_a[i] for i in idx], [b_refs]).score
        sb = sacrebleu.corpus_bleu([hyp_b[i] for i in idx], [b_refs]).score
        boot_a.append(sa); boot_b.append(sb); boot_d.append(sa - sb)
    edits = np.array([_plain_edit_distance(s["ref_gloss_raw"], s["pred_gloss"]) for s in per_sample])
    lens = np.array([len(s["ref_gloss_raw"]) for s in per_sample])
    base_wer = float(edits.sum() / lens.sum() * 100.0)
    boot_w = []
    m = len(per_sample)
    for _ in range(bp["n_resamples"]):
        idx = np.random.choice(m, size=m, replace=True)
        boot_w.append(float(edits[idx].sum() / lens[idx].sum() * 100.0))
    ci = lambda v: [float(x) for x in np.percentile(v, bp["percentiles"])]  # noqa: E731
    ci_d = ci(boot_d)
    out = {
        "n_clips": m, "n_unseen": n,
        "bleu_mode_a": {"score": float(base_a), "ci_95": ci(boot_a)},
        "bleu_mode_b": {"score": float(base_b), "ci_95": ci(boot_b)},
        "delta": {"score": float(base_a - base_b), "ci_95": ci_d, "ci_contains_zero": bool(ci_d[0] <= 0 <= ci_d[1])},
        "wer_300": {"score": base_wer, "ci_95": ci(boot_w)},
    }
    out["rounded_2"] = {k: {"score": round(v["score"], 2), "ci_95": [round(x, 2) for x in v["ci_95"]]}
                        for k, v in out.items() if isinstance(v, dict) and "score" in v}
    return out


def compute_metrics(per_sample, protocol):
    if protocol["name"] == "sentsplit_v1":
        return metrics_sentsplit_v1(per_sample, protocol)
    return metrics_repro_v2(per_sample, protocol)


def comparison_to_old(metrics, protocol):
    cfg = protocol["comparison_to_old"]
    path = resolve(cfg["source"])
    text = path.read_text(encoding="utf-8")
    old = json.loads(text)
    lines = text.splitlines()
    out = {"source": cfg["source"], "source_sha256": sha256_file(path), "rule": cfg["rule"], "items": {}}
    new_key = {"bleu_mode_a": "bleu_mode_a", "bleu_mode_b": "bleu_mode_b", "wer_300": "wer_300"}
    for name, dotted in cfg["keys"].items():
        node = old
        for part in dotted.split("."):
            node = node[part]
        leaf = dotted.split(".")[-1]
        line_no = next((i + 1 for i, ln in enumerate(lines) if f'"{leaf}"' in ln), None)
        new = metrics.get(new_key[name])
        lo, hi = new["ci_95"]
        out["items"][name] = {"old_point_estimate": node["point_estimate"], "old_ci_95": node["ci_95"],
                              "old_source": f"{cfg['source']}:{line_no}" if line_no else cfg["source"],
                              "new_score": new["score"], "new_ci_95": new["ci_95"],
                              "old_point_inside_new_ci": bool(lo <= node["point_estimate"] <= hi)}
    return out


LIMITATIONS_SENTSPLIT_V1 = [
    "The 30 test sentences SENT271..SENT300 were NOT chosen at random (they are the last 30 ids); they may differ "
    "systematically (topic, length) from the 270 others: these numbers do not represent 'any new sentence' (plan 13 R13).",
    "One signer (S06), 30 clips: confidence intervals are wide (plan 13 R7).",
    "The old numbers (comparison_to_old) come from OLD models with leakage: the old CSLR had learned all 300 sentences through "
    "S01-S04 (docs/cloud_reports/viec-A-D-2026-09-29.md:45-48), so the old Mode B is optimistic; the old ViT5 stage 1 "
    "may have contained these sentences (never measured). A lower new number does NOT mean the new model is worse.",
    "Bootstrap differs from the old one: the old WER was measured on 300 clips and not paired with BLEU; here WER and "
    "BLEU share the same resamples on 30 clips.",
    "'Unseen' for ViT5 stage 1 means 'unseen under the plan 13 §0.3 matching rule (L1/L2/near-duplicate)'; paraphrases "
    "may remain (plan 13 R15).",
    "Offline path (dataset preprocessing with normalize=True), not the realtime path (plan 13 R10).",
]
LIMITATIONS_REPRO_V2 = [
    "Reproduction check of the old recipe (i): the CSLR saw every sentence through S01-S04, so S06 is only an unseen "
    "SIGNER, not unseen sentences (docs/cloud_reports/viec-A-D-2026-09-29.md:45-48).",
    "The 30 'unseen' sentences are the last 30 ids, not a random sample; one signer.",
    "Descriptive only: no threshold, no action depends on these numbers (plan 13 §0.7).",
]


# ---------------------------------------------------------------------------------------------------------------------
# Heavy steps (patched in the unit tests)
# ---------------------------------------------------------------------------------------------------------------------
def load_cslr_checkpoint(path):
    import torch
    return torch.load(str(path), map_location="cpu", weights_only=False)


def cslr_predict(ckpt, vocab, dataset, protocol):
    """{sample_id: [predicted glosses]} on CPU, no autocast, greedy CTC decode."""
    import torch
    from torch.utils.data import DataLoader
    from src.data.vsl_gh_dataset import vslgh_collate_fn
    from src.metrics.cslr_metrics import ctc_greedy_decode, tokens_to_words
    from src.models.cslr_stgcn_bigru import STGCNBiGRU_CSLR
    mc = protocol["cslr"]["model"]
    cfg = ckpt["config"]
    kwargs = dict(mc["fixed"])
    kwargs.update({k: cfg[k] for k in mc["from_checkpoint_config"]})
    model = STGCNBiGRU_CSLR(num_classes=len(vocab), **kwargs)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    loader = DataLoader(dataset, batch_size=protocol["cslr"]["batch_size"], shuffle=False, num_workers=0,
                        collate_fn=vslgh_collate_fn)
    out = {}
    with torch.no_grad():
        for batch in loader:
            log_probs, out_lens = model(batch["features"], joint_masks=batch["joint_masks"],
                                        sequence_lengths=batch["lengths"])
            seqs = ctc_greedy_decode(log_probs, sequence_lengths=out_lens, blank_id=vocab.blank_id)
            for sid, words in zip(batch["sample_ids"], tokens_to_words(seqs, vocab)):
                out[sid] = list(words)
    return out


def vit5_generate(model_dir, sources, protocol):
    """One batch, beam search as registered; outputs post-normalised with normalize_vietnamese_target."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from src.translation.text_normalizer import normalize_vietnamese_target
    t = protocol["translation"]
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir))
    model.eval()
    inputs = tok(sources, return_tensors="pt", **t["tokenizer"])
    with torch.no_grad():
        outputs = model.generate(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], **t["generate"])
    raw = tok.batch_decode(outputs, **t["decode"])
    return [normalize_vietnamese_target(r) for r in raw]


# ---------------------------------------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------------------------------------
def _load_json(path, what):
    p = resolve(path)
    if not p.is_file():
        raise EvalError(2, f"{what} not found: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_versions(prereg):
    libs = prereg.get("libs_local") or {}
    for name in ("sacrebleu", "numpy"):
        want, got = libs.get(name), pkg_version(name)
        if want is None or want != got:
            raise EvalError(2, f"{name} version {got!r} != preregistration libs_local.{name} {want!r}")


def check_prereg_inputs(prereg, protocol):
    """Check every preregistration `inputs` entry that names one of the protocol's FILE inputs (matched by resolved path,
    not by string). Never silent: a matched entry without a digest, or no entry for a required input
    (REQUIRED_INPUT_ENTRIES), is exit 3. Returns the paths checked."""
    entries = prereg.get("inputs") or {}
    items = list(entries.values()) if isinstance(entries, dict) else list(entries)
    wanted = {k: resolve(protocol["inputs"][k]) for k in FILE_INPUTS}
    checked = []
    for e in items:
        if not isinstance(e, dict) or not e.get("path"):
            continue
        p = resolve(e["path"])
        keys = [k for k, w in wanted.items() if same_path(p, w)]
        if not keys:
            continue
        if not p.is_file():
            raise EvalError(3, f"preregistered input {keys[0]} not found: {p}")
        if "lf_sha256" not in e and "sha256" not in e:
            raise EvalError(3, f"preregistration inputs entry for {keys[0]} ({e['path']}) has no lf_sha256 / sha256")
        if "lf_sha256" in e and lf_sha256(p) != e["lf_sha256"]:
            raise EvalError(3, f"lf_sha256 of {e['path']} ({keys[0]}) != preregistration")
        if "sha256" in e and sha256_file(p) != e["sha256"]:
            raise EvalError(3, f"sha256 of {e['path']} ({keys[0]}) != preregistration")
        checked += [(k, e["path"]) for k in keys]
    missing = [k for k in REQUIRED_INPUT_ENTRIES if k not in {c[0] for c in checked}]
    if missing:
        raise EvalError(3, f"preregistration inputs has no checkable entry for {missing} "
                           f"(path must resolve to {[str(wanted[k]) for k in missing]})")
    return [c[1] for c in checked]


def run(args, argv):
    name = args.protocol
    prereg_path = resolve(args.prereg)
    out_path = resolve(args.out)
    if out_path.exists():
        raise EvalError(2, f"output already exists (evaluation runs once): {out_path}")
    prereg = _load_json(prereg_path, "preregistration")
    pkeys = PREREG_KEYS[name]
    protocol = check_protocol(prereg.get(pkeys["protocol"]), name)
    registered_out = prereg.get(pkeys["output"])
    if not isinstance(registered_out, str) or not registered_out:
        raise EvalError(2, f"preregistration has no {pkeys['output']} (the one accepted --out)")
    registered_out = resolve(registered_out)
    if run_marker_path(registered_out).exists():
        raise EvalError(2, f"run marker exists, the evaluation already started once: {run_marker_path(registered_out)}")
    registered_kp = prereg.get(pkeys["kp_digest"])
    if not isinstance(registered_kp, str) or len(registered_kp) != 64:
        raise EvalError(3, f"preregistration has no {pkeys['kp_digest']} (64 hex)")
    rel_paths = protocol.get("manifest_rel_paths")
    if (not isinstance(rel_paths, dict) or not all(isinstance(rel_paths.get(k), str) and rel_paths[k]
                                                   for k in ("cslr_checkpoint", "vit5_model_dir"))):
        raise EvalError(2, "protocol has no manifest_rel_paths{cslr_checkpoint, vit5_model_dir}")
    gs = git_state(prereg_path)
    if gs["code_dirty"]:
        raise EvalError(2, f"code is dirty (git status --porcelain -- {' '.join(CODE_PATHS)} <prereg>): {gs['dirty_lines']}")
    if not gs["prereg_commit"] or not gs["prereg_is_ancestor"]:
        raise EvalError(2, "the commit that added the preregistration is not an ancestor of HEAD")
    if gs["prereg_n_commits"] != 1:
        raise EvalError(2, f"the preregistration was changed after it was committed ({gs['prereg_n_commits']} commits)")
    check_versions(prereg)

    from src.data.sentence_split import load_sentence_split, select_vslgh_samples
    from src.data.vsl_gh_dataset import VSLGHContinuousDataset, VSLGlossVocabulary
    inp = {k: resolve(v) for k, v in protocol["inputs"].items()}
    for k, p in inp.items():
        if not p.exists():
            raise EvalError(2, f"missing input {k}: {p}")
    split_info = prereg.get("sentence_split") or {}
    split = load_sentence_split(resolve(split_info.get("path", "")))
    if split.sha256 != split_info.get("sha256"):
        raise EvalError(3, f"sentence split sha256 {split.sha256} != preregistration {split_info.get('sha256')}")
    vocab_key = "vocab" if name == "sentsplit_v1" else "vocab_full_reference"
    vocab_sha = sha256_file(inp["vocab"])
    if vocab_sha != (prereg.get(vocab_key) or {}).get("sha256"):
        raise EvalError(3, f"vocab sha256 {vocab_sha} != preregistration {vocab_key}.sha256")
    checked_inputs = check_prereg_inputs(prereg, protocol)
    model_dir = inp["vit5_model_dir"]
    model_files = sorted(str(p.relative_to(model_dir)).replace("\\", "/") for p in model_dir.rglob("*") if p.is_file())
    if not model_files:
        raise EvalError(2, f"empty ViT5 model dir {model_dir}")
    file_shas = {"cslr_best.pt": sha256_file(inp["cslr_checkpoint"]),
                 "gloss_vocab_canonical.txt": vocab_sha}
    vit5_shas = {rel: sha256_file(model_dir / rel) for rel in model_files}
    vit5_prefix = rel_paths["vit5_model_dir"].replace("\\", "/").strip("/")
    check_against_manifests({rel_paths["cslr_checkpoint"].replace("\\", "/").strip("/"): file_shas["cslr_best.pt"],
                             **{f"{vit5_prefix}/{rel}": h for rel, h in vit5_shas.items()}},
                            manifest_sha_index(args.manifest))
    ckpt = load_cslr_checkpoint(inp["cslr_checkpoint"])
    if ckpt.get("gloss_vocab_hash") != vocab_sha[:16]:
        raise EvalError(3, f"checkpoint gloss_vocab_hash {ckpt.get('gloss_vocab_hash')!r} != vocab {vocab_sha[:16]}")
    if name == "sentsplit_v1" and (ckpt.get("config") or {}).get("sentence_split_sha256") != split.sha256:
        raise EvalError(3, "checkpoint config.sentence_split_sha256 != sentence split file")
    vocab = VSLGlossVocabulary.from_file(str(inp["vocab"]))

    # ---- test selection (checked before any clip is read) ----
    with open(inp["canonical_json"], encoding="utf-8") as f:
        canonical = json.load(f)
    ts = protocol["test_set"]
    ds_kwargs = dict(canonical_json=inp["canonical_json"], keypoints_dir=inp["keypoints_dir"], split="test",
                     vocabulary=vocab, **protocol["cslr"]["dataset"])
    if name == "sentsplit_v1":
        selected = select_vslgh_samples(canonical, "test", split)
        dataset = VSLGHContinuousDataset(sentence_split=split, **ds_kwargs)
        if {s["sentence_id"] for s in selected} != set(split.test_ids):
            raise EvalError(3, "test clips do not cover exactly the test sentences of the split")
    else:
        dataset = VSLGHContinuousDataset(**ds_kwargs)
        selected = list(dataset.samples)
        n_unseen = sum(1 for s in selected if s["sentence_id"] >= "SENT271")
        if n_unseen != ts["expected_unseen"]:
            raise EvalError(3, f"{n_unseen} unseen clips != expected {ts['expected_unseen']}")
    if [s["id"] for s in dataset.samples] != [s["id"] for s in selected]:
        raise EvalError(3, "dataset selection differs from the registered selection")
    if len(selected) != ts["expected_n"]:
        raise EvalError(3, f"{len(selected)} test clips != expected {ts['expected_n']}")
    if {s.get("signer_id") for s in selected} != set(ts["signers"]):
        raise EvalError(3, f"test signers {sorted({s.get('signer_id') for s in selected})} != {ts['signers']}")
    missing = [s["id"] for s in selected if not (inp["keypoints_dir"] / f"{s['id']}.npy").is_file()]
    if missing:
        raise EvalError(3, f"missing keypoints for {len(missing)} test clip(s) (never dropped): {missing[:5]}")
    kp_digest = hashlib.sha256("".join(f"{s['id']}.npy {sha256_file(inp['keypoints_dir'] / (s['id'] + '.npy'))}\n"
                                       for s in sorted(selected, key=lambda x: x["id"])).encode("utf-8")).hexdigest()

    if kp_digest != registered_kp:
        raise EvalError(3, f"test keypoints digest {kp_digest} != preregistration {pkeys['kp_digest']} {registered_kp}")
    if not same_path(out_path, registered_out):
        raise EvalError(2, f"--out {out_path} is not the registered {pkeys['output']} {registered_out}")

    # ---- the one evaluation: exclusive marker first, then the first test clip is read ----
    marker = run_marker_path(registered_out)
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(marker, "x", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"protocol": name, "git_commit": gs["head"], "out": str(out_path),
                                "command": f"python {SCRIPT} " + " ".join(shlex.quote(a) for a in argv),
                                "started_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                               ensure_ascii=False) + "\n")
    except FileExistsError:
        raise EvalError(2, f"run marker exists, the evaluation already started once: {marker}") from None
    print(f"EVAL RUN protocol={name} n_clips={len(selected)} head={gs['head']} marker={marker}", flush=True)
    from src.metrics.cslr_metrics import levenshtein_distance
    from src.translation.text_normalizer import normalize_vietnamese_target, normalize_vsl_source
    preds = cslr_predict(ckpt, vocab, dataset, protocol)
    rows = []
    for s in selected:
        raw = list(s.get("gloss_sequence", []) or [])
        ref = [g.strip() for g in raw if g.strip()]
        pred = preds[s["id"]]
        _, S, D, I = levenshtein_distance(ref, pred)
        enc = [vocab.id_to_gloss[i] for i in vocab.encode(raw)]
        rows.append({"sample_id": s["id"], "sentence_id": s["sentence_id"], "signer_id": s.get("signer_id"),
                     "ref_gloss_raw": raw, "ref_gloss": ref, "pred_gloss": pred, "S": S, "D": D, "I": I,
                     "ref_gloss_vocab_encoded": enc, "n_ref_oov": sum(1 for g in ref if g not in vocab.gloss_to_id),
                     "mode_a_source": normalize_vsl_source(raw), "mode_b_source": normalize_vsl_source(pred),
                     "reference": normalize_vietnamese_target(s.get("translation", "") or "")})
    tr_rows = rows if name == "sentsplit_v1" else [r for r in rows if r["sentence_id"] >= "SENT271"]
    out_a = vit5_generate(model_dir, [r["mode_a_source"] for r in tr_rows], protocol)
    out_b = vit5_generate(model_dir, [r["mode_b_source"] for r in tr_rows], protocol)
    for r, a, b in zip(tr_rows, out_a, out_b):
        r["mode_a_output"], r["mode_b_output"] = a, b
    print("PER_SAMPLE " + json.dumps(rows, ensure_ascii=False), flush=True)

    metrics = compute_metrics(rows, protocol)
    import numpy
    import sacrebleu
    import torch
    import transformers
    result = {
        "generated_by": {"script": SCRIPT, "command": f"python {SCRIPT} " + " ".join(shlex.quote(a) for a in argv),
                         "git_commit": gs["head"], "code_dirty": gs["code_dirty"],
                         "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "python": platform.python_version(), "torch": torch.__version__,
                         "transformers": transformers.__version__, "sacrebleu": sacrebleu.__version__,
                         "numpy": numpy.__version__, "device": "cpu"},
        "inputs": {"preregistration": str(args.prereg), "preregistration_sha256": lf_sha256(prereg_path),
                   "preregistration_commit": gs["prereg_commit"],
                   "sentence_split": split_info.get("path"), "sentence_split_sha256": split.sha256,
                   "canonical_json_lf_sha256": lf_sha256(inp["canonical_json"]),
                   "test_keypoints_digest": kp_digest, "vocab_sha256": vocab_sha,
                   "cslr_checkpoint_sha256": file_shas["cslr_best.pt"],
                   "vit5_model_files_sha256": vit5_shas, "manifests": list(args.manifest),
                   "manifest_rel_paths": rel_paths, "run_marker": str(marker),
                   "preregistration_inputs_checked": checked_inputs},
        "protocol": protocol,
        "per_sample": rows,
        "metrics": metrics,
        "comparison_to_old": comparison_to_old(metrics, protocol),
        "limitations": LIMITATIONS_SENTSPLIT_V1 if name == "sentsplit_v1" else LIMITATIONS_REPRO_V2,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"EVAL DONE -> {out_path}", flush=True)
    return 0


def recompute(src, out):
    data = _load_json(src, "evaluation JSON")
    out_path = resolve(out)
    if out_path.exists():
        raise EvalError(2, f"output already exists: {out_path}")
    protocol = data["protocol"]
    check_protocol(protocol, protocol.get("name"))
    metrics = compute_metrics(data["per_sample"], protocol)
    identical = json.loads(json.dumps(metrics)) == data["metrics"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"recomputed_from": str(src), "identical": identical, "metrics": metrics},
                           ensure_ascii=False, indent=2) + "\n")
    print(f"RECOMPUTE identical={identical} -> {out_path}")
    return 0 if identical else 3


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prereg")
    ap.add_argument("--protocol", choices=PROTOCOLS)
    ap.add_argument("--manifest", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--recompute-from")
    args = ap.parse_args(argv)
    if args.recompute_from is None:
        if not args.prereg or not args.protocol or not args.manifest:
            ap.error("--prereg, --protocol and at least one --manifest are required (or use --recompute-from)")
    elif args.prereg or args.protocol or args.manifest:
        ap.error("--recompute-from takes only --out")
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        if args.recompute_from:
            return recompute(args.recompute_from, args.out)
        return run(args, argv)
    except EvalError as e:
        print(f"eval_sentsplit: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
