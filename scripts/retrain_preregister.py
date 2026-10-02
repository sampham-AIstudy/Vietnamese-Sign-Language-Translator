"""Plan 13 B5 (§3.3 + [LS1]) — preregistration of the retraining jobs, written BEFORE any Kaggle kernel is pushed.

  python scripts/retrain_preregister.py --date <YYYY-MM-DD> --plan-revision-commit <hash of plan revision 1> \
         --clean10k <cleaned 10k jsonl to measure> [--vocab-file <train-only vocab to cross-check>] \
         [--vocab-full-file <full vocab to cross-check>]
  -> reports/retrain_<YYYY-MM-DD>/preregistration.json (refuses to overwrite)

Every value is COMPUTED by code at generation time from the local data and the committed split file (never typed):
digests (sha256 / lf_sha256 / combined directory digests), sample counts of the three datasets with and without the
sentence split, the 10k pairs excluded by the §0.3 rule (ids + rule, never the text), the train-only vocabulary (bytes
built in memory with the same function as scripts/build_gloss_vocab_canonical.py), the leak checks (shared functions of
src/data/sentence_split.py), the digest of the S06 x T keypoint files (formula of scripts/eval_sentsplit.py; only file
hashes, nothing is fed to a model), library versions of the .venv, upstream commits of the local clones, and
`evaluation_protocol[_repro_v2]` = `eval_sentsplit.protocol_template(...)`. Reference counts (7140, 6426/714, 240/30,
3600/300/300, 372, 4200) are READ from their source files with file:line, then compared with the measured values of the
ORIGINAL data (no split): any difference, a leak check != 0, a CSLR val/test != 30, a vocab > the full vocab or a cross-check
file that differs -> exit 3 and no file is written.

The measurement functions (`measure_*`) and `compare` are shared with the Kaggle kernels (kaggle/vsl-retrain-*), which
re-measure on the rebuilt data and stop before training on any difference.

Exit codes: 0 written; 2 refused (output exists / wrong path, code dirty, plan revision commit not found or not an
ancestor of HEAD, split file not committed exactly once, missing input); 3 data mismatch (see above).
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
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

from retrain_digest import dir_digest, lf_sha256, sha256_file  # noqa: E402

SCRIPT = "scripts/retrain_preregister.py"
PLAN = "docs/plans/13-train-lai-checkpoint-thieu.md"
PLAN_REVISION_MARKER = "## 0. Lần sửa 1 (2026-10-02)"
SPLIT_REL = "configs/vslgh_sentence_split_v1.json"
CANONICAL_REL = "data/external/vsl_gh/dataset_canonical.json"
KEYPOINTS_REL = "data/external/vsl_gh/keypoints_frontal"
VOCAB_REL = "data/external/vsl_gh/gloss_vocab_canonical.txt"
RAW10K_REL = "data/external/parallel_text/vie_vsl_10k.jsonl"
CLEAN10K_REL = "data/external/parallel_text/vie_vsl_10k_cleaned.jsonl"
TIER1_CSV_REL = {"train": "data/splits/folds/tier1_grouped_train.csv",
                 "val": "data/splits/folds/tier1_grouped_val.csv",
                 "test": "data/splits/folds/tier1_grouped_test.csv"}
TIER1_CLASSES_REL = "data/splits/folds/tier1_grouped_classes.txt"
TIER1_NPZ_DIR_REL = "data/extracted_keypoints"
UPSTREAM = {"vsl_gh": "clone/Vietnamese-Sign-Language-Translation",
            "parallel_corpus": "clone/Parallel-Corpus-Vie-VSL"}
LIBS = ("torch", "transformers", "tokenizers", "sentencepiece", "safetensors", "sacrebleu", "numpy", "rouge_score")
K2_PIP_PINNED = ("transformers", "tokenizers", "sentencepiece", "safetensors")
CODE_PATHS = ("src", "scripts", "configs", "train.py", "evaluate_test.py", "kaggle")
OUT_RX = re.compile(r"^reports/retrain_(\d{4}-\d{2}-\d{2})/preregistration\.json$")
SPECIALS = ("<blank>", "<unk>")
EXCLUSION_RULES = ("L1", "L2", "near_dup")
EXPECTED_SPLIT_N = {"cslr_val": 30, "cslr_test": 30}

# Reference values of the ORIGINAL data (plan 13 §3.3 `reference_counts`): (file, how to find the line, regex or JSON key)
REFERENCE_SOURCES = {
    "cleaned_10k_records": ("reports/audit_20260924/inventory_summary.json", "json", "level_3.clean_10k_pairs"),
    "raw_10k_lines": ("reports/audit_20260924/inventory_summary.json", "json", "level_3.raw_10k_pairs"),
    "clean10k_default_train": ("reports/vit5_stage1_history.json", "json", "train_samples"),
    "clean10k_default_val": ("reports/vit5_stage1_history.json", "json", "val_samples"),
    "vslgh_text_default_train": ("reports/vit5_stage2_history.json", "json", "train_samples"),
    "vslgh_text_default_val": ("reports/vit5_stage2_history.json", "json", "val_samples"),
    "cslr_default_train": ("docs/data_registry.md", "regex", r"Signer-independent: Train \(S01\.\.S04, ([\d,]+) samples\)"),
    "cslr_default_val": ("docs/data_registry.md", "regex", r"Signer-independent: .*Val \(S05, ([\d,]+) samples\)"),
    "cslr_default_test": ("docs/data_registry.md", "regex", r"Signer-independent: .*Test \(S06, ([\d,]+) samples\)"),
    "vocab_full_n_tokens": ("docs/vsl_gh_dataset.md", "regex", r"gloss_vocab_canonical\.txt` \((\d+) tokens\)"),
    "canonical_n_samples": ("docs/vsl_gh_dataset.md", "regex", r"dataset_canonical\.json` \(([\d,]+) entries\)"),
    "keypoints_n_files": ("docs/vsl_gh_dataset.md", "regex", r"keypoints_frontal/\*\.npy` \(([\d,]+) files\)"),
}

# Epoch-selection rule of every job: (file, the one line that implements it) -> "file:line" computed at generation time
SELECTION_RULES = {
    "k1": ("src/training/trainer.py", 'if val_metrics["top1"] > self.best_val_top1 or ('),
    "cslr": ("src/training/train_cslr.py", 'if val_res["wer"] < best_val_wer:'),
    "vit5_stage1": ("scripts/train_translation_stage1.py", "if avg_val_loss < best_val_loss:"),
    "vit5_stage2": ("scripts/train_translation_stage2.py", "if avg_val_loss < best_val_loss:"),
}


class PreregError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
def rel(root, path):
    return os.path.relpath(os.path.abspath(str(path)), os.path.abspath(str(root))).replace("\\", "/")


def need_file(path, what):
    if not Path(path).is_file():
        raise PreregError(2, f"missing input {what}: {path}")
    return Path(path)


def need_dir(path, what):
    if not Path(path).is_dir():
        raise PreregError(2, f"missing input {what}: {path}")
    return Path(path)


def pkg_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:  # noqa: BLE001
        return None


def lines_of(path):
    return Path(path).read_text(encoding="utf-8").splitlines()


def line_ref(root, path, needle):
    """'path:N' of the ONE line of `path` containing `needle` (0 or > 1 lines -> exit 3)."""
    hits = [i + 1 for i, ln in enumerate(lines_of(need_file(Path(root) / path, path))) if needle in ln]
    if len(hits) != 1:
        raise PreregError(3, f"{path}: expected exactly 1 line containing {needle!r}, found {hits}")
    return f"{path}:{hits[0]}"


def vocab_bytes(tokens):
    return "".join(t + "\n" for t in tokens).encode("utf-8")


def _int(text):
    return int(text.replace(",", ""))


def read_reference(root, name):
    path, kind, key = REFERENCE_SOURCES[name]
    lines = lines_of(need_file(Path(root) / path, f"reference source {path}"))
    if kind == "json":
        value = json.loads("\n".join(lines))
        for part in key.split("."):
            value = value[part]
        leaf = key.split(".")[-1]
        hits = [i + 1 for i, ln in enumerate(lines) if f'"{leaf}"' in ln]
    else:
        rx = re.compile(key)
        found = [(i + 1, rx.search(ln)) for i, ln in enumerate(lines)]
        found = [(n, m) for n, m in found if m]
        if len(found) != 1:
            raise PreregError(3, f"reference {name}: {len(found)} lines of {path} match {key!r}")
        hits, value = [found[0][0]], _int(found[0][1].group(1))
    if len(hits) != 1:
        raise PreregError(3, f"reference {name}: key {key!r} found on {len(hits)} lines of {path}")
    return {"value": value, "source": f"{path}:{hits[0]}"}


# ---------------------------------------------------------------------------------------------------------------------
# measurements (shared with the kernels)
# ---------------------------------------------------------------------------------------------------------------------
def measure_split(root):
    from src.data.sentence_split import load_sentence_split
    p = need_file(Path(root) / SPLIT_REL, "sentence split")
    ss = load_sentence_split(p)
    return ss, {"path": SPLIT_REL, "sha256": ss.sha256,
                "sha256_rule": "sha256 of the file bytes with CRLF -> LF (src.data.sentence_split.split_file_sha256)",
                "version": ss.version, "seed": ss.seed, "python": ss.raw.get("python"),
                "test_ids": list(ss.test_ids), "val_ids": list(ss.val_ids), "n_train_sentences": len(ss.train_ids),
                "n_val_sentences": len(ss.val_ids), "n_test_sentences": len(ss.test_ids)}


def test_keypoints_digest(samples, keypoints_dir):
    """Formula of scripts/eval_sentsplit.py (sha256 of '<id>.npy <sha256>\\n' sorted by id). Missing file -> exit 3."""
    kp = Path(keypoints_dir)
    missing = [s["id"] for s in samples if not (kp / f"{s['id']}.npy").is_file()]
    if missing:
        raise PreregError(3, f"missing keypoints for {len(missing)} test clip(s): {missing[:5]}")
    text = "".join(f"{s['id']}.npy {sha256_file(str(kp / (s['id'] + '.npy')))}\n"
                   for s in sorted(samples, key=lambda x: x["id"]))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def measure_vslgh(root, ss):
    """Canonical VSL-GH: digests, CSLR / VSLGHText counts (with and without the split), vocab, leak checks."""
    import build_gloss_vocab_canonical as BV
    from src.data.sentence_split import (collect_glosses, sample_leak_report, select_vslgh_samples,
                                         vocab_leak_report)
    from src.data.vsl_gh_dataset import VSLGHContinuousDataset
    from src.translation.dataset import VSLGHTextDataset
    root = Path(root)
    canon_p = need_file(root / CANONICAL_REL, "canonical json")
    kp_dir = need_dir(root / KEYPOINTS_REL, "keypoints_frontal")
    with open(canon_p, "r", encoding="utf-8") as f:
        canonical = json.load(f)
    kp_digest, kp_n = dir_digest(str(kp_dir), pattern="*.npy")
    inputs = {
        "dataset_canonical_json": {"path": CANONICAL_REL, "lf_sha256": lf_sha256(str(canon_p)),
                                   "n_samples": len(canonical)},
        "keypoints_frontal": {"path": KEYPOINTS_REL, "pattern": "*.npy", "dir_digest": kp_digest, "n_files": kp_n,
                              "rule": "sha256 of '<name> <sha256>\\n' lines sorted by name (scripts/retrain_digest.py)"},
    }
    cont = {n: VSLGHContinuousDataset(canonical_json=str(canon_p), keypoints_dir=str(kp_dir), split=n,
                                      sentence_split=ss) for n in ("train", "val", "test")}
    cont_default = {n: VSLGHContinuousDataset(canonical_json=str(canon_p), keypoints_dir=str(kp_dir), split=n)
                    for n in ("train", "val", "test")}
    text = {n: VSLGHTextDataset(canonical_json=str(canon_p), split=n, sentence_split=ss) for n in ("train", "val", "test")}
    text_default = {n: VSLGHTextDataset(canonical_json=str(canon_p), split=n) for n in ("train", "val", "test")}
    counts = {"cslr": {n: len(d) for n, d in cont.items()}, "vslgh_text": {n: len(d) for n, d in text.items()}}
    counts_default = {"cslr": {n: len(d) for n, d in cont_default.items()},
                      "vslgh_text": {n: len(d) for n, d in text_default.items()}}

    # vocab: same function as scripts/build_gloss_vocab_canonical.py (bytes = token + LF per line)
    tokens, excluded, n_sel = BV.build_tokens_train_only(str(canon_p), str(root / SPLIT_REL), "train")
    full_tokens = BV.build_tokens(str(canon_p))
    vb, fb = vocab_bytes(tokens), vocab_bytes(full_tokens)
    excluded_set = set(excluded)
    V, T = set(ss.val_ids), set(ss.test_ids)
    in_val = collect_glosses(s for s in canonical if s.get("sentence_id") in V)
    in_test = collect_glosses(s for s in canonical if s.get("sentence_id") in T)
    only_val, only_test = sorted(excluded_set & in_val), sorted(excluded_set & in_test)
    other = sorted(excluded_set - in_val - in_test)
    test_sel = select_vslgh_samples(canonical, "test", ss)
    test_ref = [g.strip() for s in test_sel for g in (s.get("gloss_sequence") or []) if g.strip()]
    vocab_set = set(tokens)
    vocab = {"mode": "train_only", "path": VOCAB_REL, "n_tokens": len(tokens), "sha256": hashlib.sha256(vb).hexdigest(),
             "sha256_rule": "sha256 of the raw bytes (LF only; eval_sentsplit.py uses sha256_file)",
             "gloss_vocab_hash16": hashlib.sha256(vb).hexdigest()[:16],
             "built_with": "scripts/build_gloss_vocab_canonical.py --sentence-split " + SPLIT_REL + " --split train "
                           "(build_tokens_train_only)",
             "n_samples_selected": n_sel, "first_tokens": tokens[:2],
             "glosses_excluded": sorted(excluded), "glosses_only_in_val": only_val, "glosses_only_in_test": only_test,
             "glosses_excluded_other": other,
             "test_ref_tokens_total": len(test_ref),
             "test_ref_tokens_oov": sum(1 for g in test_ref if g not in vocab_set)}
    vocab_full = {"n_tokens": len(full_tokens), "sha256": hashlib.sha256(fb).hexdigest(),
                  "built_with": "scripts/build_gloss_vocab_canonical.py (no --sentence-split; build_tokens)",
                  "used_for": "K3 (recipe (i), plan 13 §0.7) only; never placed in data/external/vsl_gh/"}

    leak = {}
    rep = sample_leak_report(ss, cont["train"].samples, cont["val"].samples)
    leak["cslr"] = {k: v for k, v in rep.items() if k != "sentence_split_sha256"}
    v_rep = vocab_leak_report(tokens, collect_glosses(cont["train"].samples), specials=SPECIALS)
    leak["vocab"] = v_rep
    rep2 = sample_leak_report(ss, text["train"].samples, text["val"].samples)
    leak["vit5_stage2"] = {k: v for k, v in rep2.items() if k != "sentence_split_sha256"}
    t_sids = {s["sentence_id"] for s in cont["test"].samples}
    t_signers = {s.get("signer_id") for s in cont["test"].samples}
    test_viol = sorted(map(str, t_sids ^ T)) + sorted(map(str, t_signers - set(ss.signers("test"))))
    if [s["id"] for s in cont["test"].samples] != [s["id"] for s in test_sel]:
        test_viol.append("dataset test selection != select_vslgh_samples(canonical, 'test', split)")
    leak["cslr_test_selection"] = {"n_clips": len(cont["test"]), "signers": sorted(map(str, t_signers)),
                                   "violations": test_viol, "n_violations": len(test_viol)}
    digests = {"test_keypoints_digest": test_keypoints_digest(test_sel, kp_dir),
               "test_keypoints_digest_repro_v2": test_keypoints_digest(list(cont_default["test"].samples), kp_dir)}
    return {"inputs": inputs, "counts": counts, "counts_default": counts_default, "vocab": vocab,
            "vocab_full": vocab_full, "leak": leak, "digests": digests, "vocab_bytes": vb, "vocab_full_bytes": fb,
            "canonical": canonical}


def measure_parallel(root, clean10k_path, ss, canonical):
    """10k corpus: digests, Clean10kDataset counts (default and after the §0.3 exclusion), excluded ids, leak check."""
    from src.data.sentence_split import heldout_texts, text_leak_report
    from src.translation.dataset import Clean10kDataset
    root = Path(root)
    raw_p = need_file(root / RAW10K_REL, "raw 10k jsonl")
    cl_p = need_file(clean10k_path, "cleaned 10k jsonl")
    cl_bytes = cl_p.read_bytes()
    with open(cl_p, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    inputs = {
        "vie_vsl_10k_jsonl": {"path": RAW10K_REL, "lf_sha256": lf_sha256(str(raw_p)),
                              "n_lines": raw_p.read_bytes().count(b"\n")},
        "vie_vsl_10k_cleaned_jsonl": {"path": CLEAN10K_REL, "measured_from": rel(root, cl_p),
                                      "lf_sha256": lf_sha256(str(cl_p)), "n_records": len(records),
                                      "n_unique_ids": len({r.get("id") for r in records}),
                                      "n_lines": cl_bytes.count(b"\n")},
    }
    default = {n: len(Clean10kDataset(jsonl_path=str(cl_p), split=n)) for n in ("train", "val")}
    held = heldout_texts(canonical, ss.heldout_ids())
    ds = {n: Clean10kDataset(jsonl_path=str(cl_p), split=n, exclude_heldout=held) for n in ("train", "val")}
    items = [{"split": n, **e} for n in ("train", "val") for e in ds[n].excluded]
    bad = [e for e in items if e.get("rule") not in EXCLUSION_RULES or not e.get("sentence_ids")]
    if bad:
        raise PreregError(3, f"10k pairs excluded without a registered reason: {bad[:3]}")
    by_reason = {r: sum(1 for e in items if e["rule"] == r) for r in EXCLUSION_RULES}
    by_reason_side = dict(sorted(collections.Counter(f"{e['rule']}/{e['side']}" for e in items).items()))
    T, V = set(ss.test_ids), set(ss.val_ids)
    excluded = {"rule_ref": "§0.3", "rule": "plan 13 §0.3: L1 / L2 / near_dup (Jaccard >= 0.8 and word count diff <= 1), "
                                          "source OR target, vs every pair (all signers, repetitions) of T u V",
                "heldout_sentence_ids": list(held.sentence_ids),
                "n_train": len(ds["train"].excluded), "n_val": len(ds["val"].excluded), "by_reason": by_reason,
                "by_reason_side": by_reason_side, "ids": sorted(e["id"] for e in items),
                "n_matching_test_sentences": sum(1 for e in items if set(e["sentence_ids"]) & T),
                "n_matching_val_sentences": sum(1 for e in items if set(e["sentence_ids"]) & V),
                "items": items}
    rep = text_leak_report([*ds["train"].samples, *ds["val"].samples], held)
    leak = {"n_items": rep["n_items"], "matches": rep["matches"], "n_violations": rep["n_violations"]}
    return {"inputs": inputs, "counts": {"train": len(ds["train"]), "val": len(ds["val"])}, "counts_default": default,
            "excluded": excluded, "leak": leak}


def measure_tier1(root):
    """Tier 1 inputs of K1: the 3 CSV + classes (lf_sha256, rows) and the npz they reference (combined digest)."""
    root = Path(root)
    out, vids = {}, set()
    for name, p_rel in TIER1_CSV_REL.items():
        p = need_file(root / p_rel, f"tier1 {name} csv")
        with open(p, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        ids = [str(r["video_id"]).strip() for r in rows]
        vids.update(ids)
        out[f"tier1_grouped_{name}_csv"] = {"path": p_rel, "lf_sha256": lf_sha256(str(p)), "n_rows": len(rows),
                                            "n_classes_in_rows": len({r.get("gloss_normalized") for r in rows})}
    cp = need_file(root / TIER1_CLASSES_REL, "tier1 classes")
    classes = [ln.strip() for ln in lines_of(cp) if ln.strip()]
    out["tier1_grouped_classes_txt"] = {"path": TIER1_CLASSES_REL, "lf_sha256": lf_sha256(str(cp)),
                                        "n_classes": len(classes)}
    names = sorted(f"{v}.npz" for v in vids)
    try:
        digest, n = dir_digest(str(need_dir(root / TIER1_NPZ_DIR_REL, "tier1 npz dir")), names=names)
    except FileNotFoundError as exc:
        raise PreregError(2, f"missing tier1 npz: {exc}") from None
    out["tier1_npz"] = {"path": TIER1_NPZ_DIR_REL, "names": "<video_id>.npz of the 3 CSV", "dir_digest": digest,
                        "n_files": n}
    return out


def reference_counts(root):
    return {name: read_reference(root, name) for name in REFERENCE_SOURCES}


def measured_for_references(vs, par):
    return {
        "cleaned_10k_records": par["inputs"]["vie_vsl_10k_cleaned_jsonl"]["n_records"],
        "raw_10k_lines": par["inputs"]["vie_vsl_10k_jsonl"]["n_lines"],
        "clean10k_default_train": par["counts_default"]["train"], "clean10k_default_val": par["counts_default"]["val"],
        "vslgh_text_default_train": vs["counts_default"]["vslgh_text"]["train"],
        "vslgh_text_default_val": vs["counts_default"]["vslgh_text"]["val"],
        "cslr_default_train": vs["counts_default"]["cslr"]["train"],
        "cslr_default_val": vs["counts_default"]["cslr"]["val"],
        "cslr_default_test": vs["counts_default"]["cslr"]["test"],
        "vocab_full_n_tokens": vs["vocab_full"]["n_tokens"],
        "canonical_n_samples": vs["inputs"]["dataset_canonical_json"]["n_samples"],
        "keypoints_n_files": vs["inputs"]["keypoints_frontal"]["n_files"],
    }


def measure_k2(root, clean10k_path, ss=None, split_block=None, vocab_file=None):
    """Everything K2 compares, in the layout of the preregistration (sections of K2_COMPARE). Raises PreregError(3)
    on a leak (total != 0), a CSLR val/test != 30, VSLGHText sizes != split sizes, a train vocab larger than the full
    one or full - train != only_in_val u only_in_test. `vocab_file` (kernel): the vocab file actually built, whose
    bytes must equal the bytes built here."""
    root = Path(root)
    if ss is None:
        ss, split_block = measure_split(root)
    vs = measure_vslgh(root, ss)
    par = measure_parallel(root, clean10k_path, ss, vs["canonical"])
    counts = {"cslr": vs["counts"]["cslr"], "vslgh_text": vs["counts"]["vslgh_text"], "clean10k": par["counts"]}
    if counts["cslr"]["val"] != EXPECTED_SPLIT_N["cslr_val"] or counts["cslr"]["test"] != EXPECTED_SPLIT_N["cslr_test"]:
        raise PreregError(3, f"CSLR val/test {counts['cslr']['val']}/{counts['cslr']['test']} != 30/30 (§7.2-2)")
    if (counts["vslgh_text"]["train"], counts["vslgh_text"]["val"]) != (split_block["n_train_sentences"],
                                                                       split_block["n_val_sentences"]):
        raise PreregError(3, f"VSLGHText train/val {counts['vslgh_text']} != split sizes")
    voc = vs["vocab"]
    if voc["n_tokens"] > vs["vocab_full"]["n_tokens"]:
        raise PreregError(3, "train-only vocab larger than the full vocab")
    if voc["glosses_excluded_other"] or sorted(set(voc["glosses_only_in_val"]) | set(voc["glosses_only_in_test"]))             != voc["glosses_excluded"]:
        raise PreregError(3, f"full - train vocab != only_in_val u only_in_test: other={voc['glosses_excluded_other']}")
    leak = {"cslr": vs["leak"]["cslr"], "vocab": vs["leak"]["vocab"], "vit5_stage1": par["leak"],
            "vit5_stage2": vs["leak"]["vit5_stage2"], "cslr_test_selection": vs["leak"]["cslr_test_selection"]}
    leak["total"] = sum(v["n_violations"] for v in leak.values())
    leak["rule"] = ("shared functions of src/data/sentence_split.py (sample_leak_report, vocab_leak_report, "
                    "text_leak_report) on the very selections the training scripts use; total must be 0")
    if leak["total"] != 0:
        raise PreregError(3, f"leak_check total {leak['total']} != 0: "
                             f"{ {k: v['n_violations'] for k, v in leak.items() if isinstance(v, dict)} }")
    vb = vs["vocab_bytes"]
    vocab_entry = {"path": VOCAB_REL, "sha256": hashlib.sha256(vb).hexdigest(),
                   "lf_sha256": hashlib.sha256(vb.replace(b"\r\n", b"\n")).hexdigest(), "n_tokens": voc["n_tokens"],
                   "mode": "train_only", "measured_from": "bytes built by build_tokens_train_only"}
    if vocab_file is not None:
        got = need_file(vocab_file, "built vocab file").read_bytes()
        vocab_entry = {**vocab_entry, "sha256": hashlib.sha256(got).hexdigest(),
                       "lf_sha256": hashlib.sha256(got.replace(b"\r\n", b"\n")).hexdigest(),
                       "n_tokens": got.count(b"\n"), "measured_from": rel(root, vocab_file),
                       "identical_to_built_bytes": got == vb}
        if got != vb:
            raise PreregError(3, f"vocab file {vocab_file} differs from build_tokens_train_only bytes")
    return {"sentence_split": split_block,
            "inputs": {**vs["inputs"], **par["inputs"], "gloss_vocab_canonical_txt": vocab_entry},
            "vocab": voc, "vocab_full_reference": vs["vocab_full"], "counts_after_split": counts,
            "counts_default": {"cslr": vs["counts_default"]["cslr"], "vslgh_text": vs["counts_default"]["vslgh_text"],
                               "clean10k": par["counts_default"]},
            "clean10k_excluded": par["excluded"], "leak_check": leak,
            "test_keypoints_digest": vs["digests"]["test_keypoints_digest"],
            "test_keypoints_digest_repro_v2": vs["digests"]["test_keypoints_digest_repro_v2"],
            "_vs": vs, "_par": par}


# ---------------------------------------------------------------------------------------------------------------------
# comparison (kernels: measured on Kaggle vs this preregistration)
# ---------------------------------------------------------------------------------------------------------------------
K2_COMPARE = ("sentence_split.sha256", "inputs.dataset_canonical_json.lf_sha256", "inputs.dataset_canonical_json.n_samples",
              "inputs.keypoints_frontal.dir_digest", "inputs.keypoints_frontal.n_files",
              "inputs.vie_vsl_10k_jsonl.lf_sha256", "inputs.vie_vsl_10k_jsonl.n_lines",
              "inputs.vie_vsl_10k_cleaned_jsonl.lf_sha256", "inputs.vie_vsl_10k_cleaned_jsonl.n_records",
              "inputs.gloss_vocab_canonical_txt.sha256", "inputs.gloss_vocab_canonical_txt.n_tokens",
              "vocab.n_tokens", "vocab.sha256", "vocab.glosses_only_in_val", "vocab.glosses_only_in_test",
              "vocab.test_ref_tokens_total", "vocab.test_ref_tokens_oov", "vocab_full_reference.n_tokens",
              "vocab_full_reference.sha256", "counts_after_split", "counts_default", "clean10k_excluded.n_train",
              "clean10k_excluded.n_val", "clean10k_excluded.by_reason", "clean10k_excluded.ids",
              "leak_check.total", "test_keypoints_digest", "test_keypoints_digest_repro_v2")
K1_COMPARE = ("inputs.tier1_grouped_train_csv", "inputs.tier1_grouped_val_csv", "inputs.tier1_grouped_test_csv",
              "inputs.tier1_grouped_classes_txt", "inputs.tier1_npz.dir_digest", "inputs.tier1_npz.n_files")


def get_path(d, dotted):
    node = d
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def _leaves(prefix, node):
    if isinstance(node, dict) and node:
        for k in sorted(node):
            yield from _leaves(f"{prefix}.{k}", node[k])
    else:
        yield prefix, node


def compare(expected, measured, keys):
    """Rows {key, expected, measured, ok} for every leaf under `keys`; a key missing on either side is a mismatch."""
    rows = []
    for key in keys:
        try:
            exp = get_path(expected, key)
        except KeyError:
            rows.append({"key": key, "expected": "<missing>", "measured": None, "ok": False})
            continue
        for leaf, value in _leaves(key, exp):
            try:
                got = get_path(measured, leaf)
            except KeyError:
                got = "<missing>"
            rows.append({"key": leaf, "expected": value, "measured": got, "ok": got == value})
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------------------------------------------------
def _git(root, *args, text=True):
    r = subprocess.run(["git", *args], capture_output=True, cwd=str(root))
    out = r.stdout.decode("utf-8", "replace").strip() if text else r.stdout
    return r.returncode, out


def git_info(root, plan_revision_commit):
    """HEAD, dirty code, plan revision 1 commit (verified), split file commit (exactly 1, ancestor). Patched in tests."""
    rc, head = _git(root, "rev-parse", "HEAD")
    if rc != 0:
        raise PreregError(2, "git rev-parse HEAD failed")
    rc, dirty = _git(root, "status", "--porcelain", "--", *CODE_PATHS)
    if rc != 0:
        raise PreregError(2, "git status failed")
    rc, log = _git(root, "log", "--reverse", "--format=%H", "--", PLAN)
    first = None
    for c in log.splitlines():
        rc_s, content = _git(root, "show", f"{c}:{PLAN}")
        if rc_s == 0 and PLAN_REVISION_MARKER in content:
            first = c
            break
    if first is None:
        raise PreregError(2, f"no commit of {PLAN} contains {PLAN_REVISION_MARKER!r}")
    rc, given = _git(root, "rev-parse", "--verify", f"{plan_revision_commit}^{{commit}}")
    if rc != 0 or given != first:
        raise PreregError(2, f"--plan-revision-commit {plan_revision_commit} != first commit with the plan revision 1 "
                             f"marker ({first})")
    is_anc = _git(root, "merge-base", "--is-ancestor", first, "HEAD")[0] == 0
    if not is_anc:
        raise PreregError(2, f"plan revision 1 commit {first} is not an ancestor of HEAD")
    rc, slog = _git(root, "log", "--format=%H", "--", SPLIT_REL)
    scommits = [c for c in slog.splitlines() if c.strip()]
    if len(scommits) != 1:
        raise PreregError(2, f"{SPLIT_REL} must have exactly 1 commit (has {len(scommits)})")
    s_anc = _git(root, "merge-base", "--is-ancestor", scommits[0], "HEAD")[0] == 0
    rc, blob = _git(root, "show", f"{scommits[0]}:{SPLIT_REL}", text=False)
    from src.data.sentence_split import split_file_sha256
    return {"head": head, "code_dirty": bool(dirty.strip()), "code_dirty_files": dirty.splitlines(),
            "plan_revision": {"commit": first, "marker": PLAN_REVISION_MARKER, "file": PLAN,
                              "is_ancestor_of_head": is_anc},
            "split_commit": {"commit": scommits[0], "n_commits": len(scommits), "is_ancestor_of_head": s_anc,
                             "blob_sha256_lf": split_file_sha256(blob) if rc == 0 else None}}


def upstream_info(root):
    out = {}
    urls = {"vsl_gh": "https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git",
            "parallel_corpus": "https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git"}
    for name, d in UPSTREAM.items():
        p = Path(root) / d
        rc, head = _git(p, "rev-parse", "HEAD") if (p / ".git").exists() else (1, "")
        rc2, url = _git(p, "remote", "get-url", "origin") if rc == 0 else (1, "")
        if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", head or ""):
            raise PreregError(2, f"upstream clone {d} not found or has no commit (needed by K2 to rebuild the data)")
        out[name] = {"clone_dir": d, "url": url if rc2 == 0 and url else urls[name], "commit": head,
                     "source": f"git -C {d} rev-parse HEAD"}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# preregistration
# ---------------------------------------------------------------------------------------------------------------------
def jobs_block(root, date):
    out_k1 = "/kaggle/working/k1"
    split = SPLIT_REL
    sel = {k: line_ref(root, f, needle) for k, (f, needle) in SELECTION_RULES.items()}

    def cmd(argv):
        return {"argv": argv, "command": "python " + " ".join(shlex.quote(a) for a in argv)}

    return {
        "seed": 42,
        "k1": {
            "kernel": "phmvnsm33/vsl-retrain-stgcn-tier1", "dir": "kaggle/vsl-retrain-stgcn-tier1",
            "train": cmd(["train.py", "--config", "configs/experiments/stgcn.yaml", "--seed", "42"]),
            "test": cmd(["evaluate_test.py", "--config", "configs/experiments/stgcn.yaml", "--checkpoint",
                         "checkpoints/stgcn_best.pt", "--output-dir", f"{out_k1}/eval"]),
            "history_file": "experiments/stgcn/history.json", "checkpoint": "checkpoints/stgcn_best.pt",
            "selection": {"split": "val (tier1_grouped_val.csv)", "rule": "max val top-1, tie -> lower val loss",
                          "rule_ref": sel["k1"]},
            "test_policy": "Tier 1 test (tier1_grouped_test.csv) evaluated exactly once by evaluate_test.py, after "
                           "the sanity checks pass",
            "sanity": ["every loss in the history finite", "best epoch >= 1",
                       "val top-1 at the best epoch > 100 / number of classes (label_map)"],
            "watchdog_minutes": 45, "gpu_cap_hours": 0.75, "accelerator": "GPU",
        },
        "k2": {
            "kernel": "phmvnsm33/vsl-retrain-cslr-vit5", "dir": "kaggle/vsl-retrain-cslr-vit5",
            "modes": {"preflight": "CPU, no accelerator: rebuild the data, measure with scripts/retrain_preregister.py "
                                   "(measure_*), compare with this file, stop on any difference; no training, no test",
                      "train": "preflight again, then backbone sha256 == k1_outputs.json, LEAK CHECK, GPU0 CSLR | "
                               "GPU1 ViT5 s1 -> s2"},
            "data_prep": {
                "vsl_gh": cmd(["scripts/prepare_canonical_vsl_gh.py"]),
                "parallel_corpus": "scripts/prepare_canonical_translation.py loaded with importlib in a runner "
                                   "subprocess; PROJECT_ROOT/CORPUS_DIR/VSL_SRC/VIE_SRC/OUTPUT_DIR/OUTPUT_JSONL/"
                                   "REPORT_JSON reset into the clone (plan 13 §2.2); main() unchanged",
                "clean_10k": cmd(["scripts/clean_10k_translation_corpus.py"]),
                "vocab": cmd(["scripts/build_gloss_vocab_canonical.py", "--canonical", CANONICAL_REL, "--out",
                              VOCAB_REL, "--sentence-split", split, "--split", "train"]),
            },
            "backbone": {"path": "checkpoints/stgcn_best.pt", "from": "output of K1 (kernel source)",
                         "sha256_from": f"reports/retrain_{date}/k1_outputs.json (committed after K1, before K2-train)",
                         "k1_outputs_key": "stgcn_best_pt.sha256",
                         "rule": "missing or sha256 different -> stop before training (train_cslr.py would "
                                 "otherwise train from scratch silently)"},
            "cslr": {"train": cmd(["src/training/train_cslr.py", "--sentence-split", split]),
                     "gpu": "0", "selection": {"split": "val = S05 x val_ids (30 clips)", "rule": "min val WER, "
                                               "tie keeps the earlier epoch", "rule_ref": sel["cslr"]},
                     "test_policy": "NOT run in the kernel: exactly one 'TEST DEFERRED (sentence split v1)' line, 0 "
                                    "'PRIMARY TEST EVALUATION'; test = scripts/eval_sentsplit.py once, local, after B11",
                     "outputs": ["checkpoints/cslr_best.pt", "checkpoints/cslr_stage1_best.pt",
                                 "reports/cslr_used_ids.json", "reports/cslr_train_summary.json",
                                 "reports/cslr_training_history.json"],
                     "sanity": ["every loss finite", "best epoch >= 1", "best_val_wer < 100",
                                "'LEAK CHECK OK (cslr)' before the first epoch",
                                "backbone transferred ('[MODEL] Transferred'), never 'Training from scratch'"]},
            "vit5_stage1": {"train": cmd(["scripts/train_translation_stage1.py", "--sentence-split", split]),
                            "gpu": "1", "base_model": "VietAI/vit5-base",
                            "selection": {"split": "val 10% of the cleaned 10k after the §0.3 exclusion",
                                          "rule": "min val loss", "rule_ref": sel["vit5_stage1"]},
                            "test_policy": "no test in the kernel", "outputs": ["checkpoints/vit5_stage1/best_model",
                                                                               "reports/vit5_stage1_used_ids.json",
                                                                               "reports/vit5_stage1_history.json"],
                            "sanity": ["every loss finite", "'LEAK CHECK OK (vit5_stage1)' before the first epoch"]},
            "vit5_stage2": {"train": cmd(["scripts/train_translation_stage2.py", "--sentence-split", split,
                                          "--stage1-path", "checkpoints/vit5_stage1/best_model"]),
                            "gpu": "1", "after": "vit5_stage1",
                            "selection": {"split": "val = val_ids (30 sentences)", "rule": "min val loss",
                                          "rule_ref": sel["vit5_stage2"]},
                            "test_policy": "no test in the kernel; ViT5 runs on the 30 test sentences only once, in "
                                           "scripts/eval_sentsplit.py (Mode A / Mode B), local, after B11",
                            "outputs": ["checkpoints/vit5_stage2/best_model", "reports/vit5_stage2_used_ids.json",
                                        "reports/vit5_stage2_history.json"],
                            "sanity": ["every loss finite", "best epoch >= 1",
                                       "'LEAK CHECK OK (vit5_stage2)' before the first epoch",
                                       "non-empty translations for the inputs of tests/test_translation_core (B11)"]},
            "single_gpu": "CSLR then ViT5 sequentially (watchdog still applies)",
            "watchdog_minutes": 105, "gpu_cap_hours": 1.75, "accelerator": "preflight: none; train: GPU T4 x2",
        },
        "k3_optional": {
            "condition": "plan 13 §0.7: only after B13 (eval of (ii) done) AND GPU budget §3.7 AND the 5h quota gate",
            "mode": "repro_i (same K2 kernel): no --sentence-split, full vocab (vocab_full_reference), CSLR test S06 at "
                    "the end as the old recipe; outputs only under /kaggle/working/k3 -> _work/_plan13_tmp/k3/",
            "evaluation": "scripts/eval_sentsplit.py --protocol repro_v2 once (evaluation_output_repro_v2)",
            "watchdog_minutes": 105, "gpu_cap_hours": 1.75},
        "gpu_budget": {"weekly_limit_hours": 10, "plan_total_cap_hours": 2.5, "plan_total_cap_with_k3_hours": 4.25,
                       "rule": "before each GPU job: STATE week + used in plan 13 + cap of the job > 10 -> stop "
                               "(K3: record 'K3 hoan' instead)", "source": "plan 13 §3.7"},
        "rerun_policy": "no other seed / config; rerun only on an infrastructure error, at most once per job, same "
                        "config (plan 13 §3.6)",
    }


def build_preregistration(root, date, clean10k_path, plan_revision_commit, argv, vocab_file=None,
                          vocab_full_file=None, code_root=ROOT):
    """`root` = where the data is measured; `code_root` = the repository whose code / clones are referenced
    (selection-rule lines, upstream clones). Both are this repository in a real run."""
    root = Path(root)
    gi = git_info(root, plan_revision_commit)
    if gi["code_dirty"]:
        raise PreregError(2, f"code is dirty (git status --porcelain -- {' '.join(CODE_PATHS)}): {gi['code_dirty_files']}")
    ss, split_block = measure_split(root)
    if gi["split_commit"]["blob_sha256_lf"] != ss.sha256:
        raise PreregError(3, f"{SPLIT_REL} differs from its committed blob")
    if not gi["split_commit"]["is_ancestor_of_head"]:
        raise PreregError(2, f"the commit of {SPLIT_REL} is not an ancestor of HEAD")
    split_block["git_commit"] = gi["split_commit"]["commit"]

    m = measure_k2(root, clean10k_path, ss=ss, split_block=split_block)
    vs, par = m["_vs"], m["_par"]
    tier1 = measure_tier1(root)

    # cross-checks with the files generated earlier (B2 / B2c) -> byte-identical or exit 3
    cross = {}
    for what, fpath, data in (("vocab", vocab_file, vs["vocab_bytes"]), ("vocab_full", vocab_full_file,
                                                                        vs["vocab_full_bytes"])):
        if fpath:
            got = need_file(fpath, f"{what} cross-check file").read_bytes()
            if got != data:
                raise PreregError(3, f"{what}: {fpath} differs from the bytes built now")
            cross[what] = {"file": rel(root, fpath), "sha256": hashlib.sha256(got).hexdigest(), "identical": True}

    refs = reference_counts(root)
    measured = measured_for_references(vs, par)
    ref_rows = {k: {**refs[k], "measured": measured[k], "matches": refs[k]["value"] == measured[k]} for k in refs}
    bad_refs = {k: v for k, v in ref_rows.items() if not v["matches"]}
    if bad_refs:
        raise PreregError(3, f"measured counts of the ORIGINAL data differ from the references (§7.2-2): {bad_refs}")

    import eval_sentsplit as E
    inputs = dict(m["inputs"])
    if "vocab" in cross:
        inputs["gloss_vocab_canonical_txt"] = {**inputs["gloss_vocab_canonical_txt"],
                                               "cross_checked_with": cross["vocab"]["file"]}
    inputs.update(tier1)
    voc, counts, leak = m["vocab"], m["counts_after_split"], m["leak_check"]
    libs = {n: pkg_version(n) for n in LIBS}
    libs["python"] = platform.python_version()
    prereg = {
        "plan": PLAN,
        "generated_by": {"script": SCRIPT, "command": "python " + " ".join([SCRIPT, *map(shlex.quote, argv)]),
                         "git_commit": gi["head"], "code_dirty": gi["code_dirty"],
                         "code_dirty_files": gi["code_dirty_files"],
                         "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "python": platform.python_version(), "platform": platform.platform()},
        "date": date,
        "plan_revision": gi["plan_revision"],
        "sentence_split": split_block,
        "inputs": inputs,
        "cross_checks": cross,
        "reference_counts": ref_rows,
        "counts_default": m["counts_default"],
        "counts_after_split": counts,
        "clean10k_excluded": m["clean10k_excluded"],
        "leak_check": leak,
        "vocab": voc,
        "vocab_full_reference": m["vocab_full_reference"],
        "test_keypoints_digest": m["test_keypoints_digest"],
        "test_keypoints_digest_repro_v2": m["test_keypoints_digest_repro_v2"],
        "test_keypoints_digest_rule": "sha256 of '<id>.npy <sha256>\\n' lines of the test clips sorted by id "
                                      "(scripts/eval_sentsplit.py); sentsplit_v1 = S06 x test_ids, repro_v2 = all S06",
        "evaluation_output": f"reports/retrain_{date}/eval/test_eval.json",
        "evaluation_output_repro_v2": f"reports/retrain_{date}/k3_repro/test_eval_repro.json",
        "evaluation_protocol": E.protocol_template("sentsplit_v1"),
        "evaluation_protocol_repro_v2": E.protocol_template("repro_v2"),
        "libs_local": libs,
        "k2_pip_pinned": {n: libs[n] for n in K2_PIP_PINNED},
        "hf_base_model": {"name": "VietAI/vit5-base", "revision": None,
                          "policy": "not pinned; the HF snapshot sha is recorded in env.json at preflight and at "
                                    "train; if they differ it is recorded as a limitation (plan 13 R5)"},
        "upstream_sources": upstream_info(code_root),
        "jobs": jobs_block(code_root, date),
        "artifacts_planned": {
            "checkpoints/stgcn_best.pt": {"job": "k1", "dataset": "phmvnsm33/vslt-retrain-artifacts"},
            "checkpoints/cslr_best.pt": {"job": "k2", "dataset": "phmvnsm33/vslt-retrain-artifacts"},
            VOCAB_REL: {"job": "k2 (== bytes of vocab.sha256)", "dataset": "phmvnsm33/vslt-retrain-artifacts"},
            CLEAN10K_REL: {"job": "B3 (local) == K2 rebuild", "dataset": "phmvnsm33/vslt-retrain-artifacts"},
            "checkpoints/vit5_stage1/best_model": {"job": "k2", "dataset": "phmvnsm33/vslt-retrain-vit5"},
            "checkpoints/vit5_stage2/best_model": {"job": "k2", "dataset": "phmvnsm33/vslt-retrain-vit5"},
            "tier1_inputs": {"dataset": "phmvnsm33/vslt-retrain-inputs-tier1",
                             "manifest": f"reports/retrain_{date}/inputs_tier1_manifest.json"},
            "manifests": [f"reports/retrain_{date}/{n}_manifest.json" for n in ("inputs_tier1", "artifacts", "vit5")],
            "k1_outputs": f"reports/retrain_{date}/k1_outputs.json",
            "k3_optional": {"dir": "_work/_plan13_tmp/k3/", "dataset": "phmvnsm33/vslt-retrain-repro-i",
                            "manifest": f"reports/retrain_{date}/repro_i_manifest.json", "never_in": "checkpoints/"},
        },
    }
    # the protocol must read back exactly what eval_sentsplit.py implements
    E.check_protocol(prereg["evaluation_protocol"], "sentsplit_v1")
    E.check_protocol(prereg["evaluation_protocol_repro_v2"], "repro_v2")
    return prereg


def write_new(path, prereg):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(prereg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with open(path, "xb") as f:  # exclusive: never overwrite, even on a race
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="<D> of plan 13 (YYYY-MM-DD, the day of B5)")
    ap.add_argument("--plan-revision-commit", required=True, help="commit that added plan revision 1 (§0) to the plan")
    ap.add_argument("--clean10k", required=True, help="cleaned 10k jsonl to measure (B3 output)")
    ap.add_argument("--vocab-file", help="train-only vocab generated earlier (B2c): must be byte-identical")
    ap.add_argument("--vocab-full-file", help="full vocab generated earlier (B2): must be byte-identical")
    ap.add_argument("--out", help="default reports/retrain_<date>/preregistration.json (only this form is accepted)")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        dt.date.fromisoformat(args.date)
    except ValueError:
        ap.error(f"--date must be YYYY-MM-DD, got {args.date!r}")
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    root = Path(args.root)
    out_rel = args.out or f"reports/retrain_{args.date}/preregistration.json"
    out_rel = out_rel.replace("\\", "/")
    m = OUT_RX.match(out_rel)
    if not m or m.group(1) != args.date:
        print(f"retrain_preregister: --out must be reports/retrain_{args.date}/preregistration.json", file=sys.stderr)
        return 2
    out = root / out_rel
    if out.exists():
        print(f"retrain_preregister: refusing to overwrite {out}", file=sys.stderr)
        return 2
    clean = Path(args.clean10k)
    clean = clean if clean.is_absolute() else root / clean
    vf = [None if p is None else (Path(p) if Path(p).is_absolute() else root / p)
          for p in (args.vocab_file, args.vocab_full_file)]
    try:
        prereg = build_preregistration(root, args.date, clean, args.plan_revision_commit, _drop_root(argv),
                                       vocab_file=vf[0], vocab_full_file=vf[1])
        sha = write_new(out, prereg)
    except PreregError as e:
        print(f"retrain_preregister: {e}", file=sys.stderr)
        return e.code
    except FileExistsError:
        print(f"retrain_preregister: refusing to overwrite {out}", file=sys.stderr)
        return 2
    print(json.dumps({"out": out_rel, "sha256": sha, "git_commit": prereg["generated_by"]["git_commit"],
                      "leak_check_total": prereg["leak_check"]["total"],
                      "counts_after_split": prereg["counts_after_split"],
                      "clean10k_excluded": {k: prereg["clean10k_excluded"][k] for k in ("n_train", "n_val", "by_reason")},
                      "vocab": {k: prereg["vocab"][k] for k in ("n_tokens", "sha256")}}, ensure_ascii=False))
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
