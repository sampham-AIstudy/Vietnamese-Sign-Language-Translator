"""VSL-GH sentence split v1 (plan 13, user decision Q1 = (ii), 2026-10-02 10:05) — ONE shared module for CSLR, ViT5,
the gloss vocabulary, the leak guard and the evaluation.

Split = sentence split x the existing signer split:
  - sentences: T (test) = SENT271..SENT300 (fixed, NOT random — the 30 sentences ViT5 stage 2 never saw, so BLEU stays
    comparable with the old 27.98 / 23.18); V (val) = sorted(random.Random(seed).sample(sorted(SENT001..SENT270), 30)),
    seed 42; Tr (train) = the other 240 sentences;
  - signers (the `split` field of `dataset_canonical.json`, unchanged): train S01-S04, val S05, test S06.
  CSLR train = S01-S04 x Tr, val = S05 x V, test = S06 x T. Everything else is unused.
The split file (`configs/vslgh_sentence_split_v1.json`) is the source of truth; the seed only documents its origin.

Held-out text matching (rule registered in plan 13 §0.3 = plan 07 §C1, `docs/plans/07-viec6-che-do.md:181-184`): a
(source, target) pair matches a held-out sentence when, on the source side (vs every source of that sentence) OR on the
target side (vs every target), it is
  L1 — equal after the training normalisers (`normalize_vsl_source` / `normalize_vietnamese_target`);
  L2 — equal after L1 + lower-case + dropping the characters .,!?;:"'()[]{}… + collapsing whitespace;
  near_dup — word-set Jaccard (after L2) >= 0.8 AND word-count difference <= 1.
Text normalisation is NOT re-implemented here: L1 is `src/translation/text_normalizer.py`.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

SPLIT_VERSION = "vslgh_sentence_split_v1"
SPLIT_NAMES = ("train", "val", "test")
N_SENTENCES = 300
N_TRAIN, N_VAL, N_TEST = 240, 30, 30
ALL_SENTENCE_IDS: Tuple[str, ...] = tuple(f"SENT{i:03d}" for i in range(1, N_SENTENCES + 1))
TEST_SENTENCE_IDS: Tuple[str, ...] = ALL_SENTENCE_IDS[N_SENTENCES - N_TEST:]  # SENT271..SENT300
VAL_POOL: Tuple[str, ...] = ALL_SENTENCE_IDS[: N_SENTENCES - N_TEST]  # SENT001..SENT270
SIGNER_SPLIT: Dict[str, Tuple[str, ...]] = {
    "train": ("S01", "S02", "S03", "S04"),
    "val": ("S05",),
    "test": ("S06",),
}
VAL_RULE = "sorted(random.Random(seed).sample(sorted(SENT001..SENT270), 30))"
TEST_RULE = "SENT271..SENT300 (fixed; the ViT5 stage-2 held-out sentences; NOT chosen at random)"

# L2 drops exactly these characters (plan 07 §C1 / plan 13 §0.3).
_L2_DROP = re.compile(r"[.,!?;:\"'()\[\]{}…]")
_WS = re.compile(r"\s+")
NEAR_DUP_JACCARD = (4, 5)  # >= 4/5 = 0.8, compared with integers (no float rounding at the boundary)
NEAR_DUP_MAX_WORD_DIFF = 1

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------------------------------------------------
# Split file
# ---------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SentenceSplit:
    version: str
    seed: int
    train_ids: Tuple[str, ...]
    val_ids: Tuple[str, ...]
    test_ids: Tuple[str, ...]
    signer_split: Mapping[str, Tuple[str, ...]]
    path: Optional[str] = None
    sha256: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def ids(self, split_name: str) -> FrozenSet[str]:
        if split_name not in SPLIT_NAMES:
            raise ValueError(f"unknown split name {split_name!r}; expected one of {SPLIT_NAMES}")
        return frozenset({"train": self.train_ids, "val": self.val_ids, "test": self.test_ids}[split_name])

    def signers(self, split_name: str) -> FrozenSet[str]:
        if split_name not in SPLIT_NAMES:
            raise ValueError(f"unknown split name {split_name!r}; expected one of {SPLIT_NAMES}")
        return frozenset(self.signer_split[split_name])

    def heldout_ids(self) -> Tuple[str, ...]:
        """Sentences that must never be trained on (T) or tuned on (V): T ∪ V, sorted."""
        return tuple(sorted(set(self.val_ids) | set(self.test_ids)))


def _id_list(d: Mapping[str, Any], key: str) -> List[str]:
    value = d.get(key)
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"split field {key!r} must be a list of sentence_id strings")
    if len(set(value)) != len(value):
        raise ValueError(f"split field {key!r} contains duplicate sentence_ids")
    return value


def validate_split_dict(d: Mapping[str, Any], path: Optional[str] = None, sha256: Optional[str] = None) -> SentenceSplit:
    """Validate a split dict (rules of plan 13 §0.3). Raises ValueError on any violation."""
    if not isinstance(d, Mapping):
        raise ValueError("split file must contain a JSON object")
    if d.get("version") != SPLIT_VERSION:
        raise ValueError(f"split version {d.get('version')!r} != {SPLIT_VERSION!r}")
    seed = d.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("split field 'seed' must be an integer")
    train, val, test = _id_list(d, "train_ids"), _id_list(d, "val_ids"), _id_list(d, "test_ids")
    s_tr, s_va, s_te = set(train), set(val), set(test)
    if s_tr & s_va or s_tr & s_te or s_va & s_te:
        raise ValueError(
            f"split sets overlap: train&val={sorted(s_tr & s_va)} train&test={sorted(s_tr & s_te)} val&test={sorted(s_va & s_te)}")
    union = s_tr | s_va | s_te
    if union != set(ALL_SENTENCE_IDS):
        raise ValueError(f"split must cover exactly SENT001..SENT300: missing={sorted(set(ALL_SENTENCE_IDS) - union)} "
                         f"unknown={sorted(union - set(ALL_SENTENCE_IDS))}")
    if (len(train), len(val), len(test)) != (N_TRAIN, N_VAL, N_TEST):
        raise ValueError(f"split sizes {len(train)}/{len(val)}/{len(test)} != {N_TRAIN}/{N_VAL}/{N_TEST}")
    if s_te != set(TEST_SENTENCE_IDS):
        raise ValueError("test sentences must be exactly SENT271..SENT300")
    if not s_va <= set(VAL_POOL):
        raise ValueError("val sentences must be a subset of SENT001..SENT270")
    signer_split = d.get("signer_split")
    expected_signers = {k: list(v) for k, v in SIGNER_SPLIT.items()}
    if signer_split != expected_signers:
        raise ValueError(f"signer_split {signer_split!r} != {expected_signers!r} (the existing signer split is kept)")
    return SentenceSplit(
        version=SPLIT_VERSION, seed=seed,
        train_ids=tuple(sorted(train)), val_ids=tuple(sorted(val)), test_ids=tuple(sorted(test)),
        signer_split={k: tuple(v) for k, v in SIGNER_SPLIT.items()},
        path=path, sha256=sha256, raw=dict(d),
    )


def split_file_sha256(data: bytes) -> str:
    """Identity of a split file: sha256 of its bytes with CRLF -> LF (the file is generated with LF only, so this is the
    sha256 of the generated bytes and of the git blob; it stays the same on a Windows `core.autocrlf=true` checkout)."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def load_sentence_split(path: PathLike) -> SentenceSplit:
    """Read + validate a split file; `sha256` = `split_file_sha256` of the file bytes."""
    data = Path(path).read_bytes()
    try:
        d = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"split file {path} is not valid UTF-8 JSON: {exc}") from exc
    return validate_split_dict(d, path=str(path), sha256=split_file_sha256(data))


def resolve_sentence_split(obj: Union[SentenceSplit, PathLike]) -> SentenceSplit:
    """Accept a loaded `SentenceSplit` or a path to a split file."""
    if isinstance(obj, SentenceSplit):
        return obj
    if isinstance(obj, (str, Path)):
        return load_sentence_split(obj)
    raise TypeError(f"sentence_split must be a SentenceSplit or a path, got {type(obj).__name__}")


def check_canonical_layout(samples: Sequence[Mapping[str, Any]]) -> None:
    """The canonical VSL-GH layout this split relies on: signer <-> `split` exactly as SIGNER_SPLIT and the sentence ids
    exactly SENT001..SENT300. Raises ValueError otherwise."""
    expected = {sig: name for name, sigs in SIGNER_SPLIT.items() for sig in sigs}
    bad = []
    for s in samples:
        signer, s_split = s.get("signer_id"), s.get("split")
        if expected.get(signer) != s_split:
            bad.append((s.get("id"), signer, s_split))
    if bad:
        raise ValueError(f"{len(bad)} sample(s) break the signer split {SIGNER_SPLIT}, e.g. {bad[:3]}")
    sids = {s.get("sentence_id") for s in samples}
    if sids != set(ALL_SENTENCE_IDS):
        raise ValueError(f"canonical sentence ids must be exactly SENT001..SENT300: "
                         f"missing={sorted(set(ALL_SENTENCE_IDS) - sids)[:5]} unknown={sorted(map(str, sids - set(ALL_SENTENCE_IDS)))[:5]}")


def make_split_dict(samples: Sequence[Mapping[str, Any]], seed: int = 42,
                    python_version: Optional[str] = None) -> Dict[str, Any]:
    """Build the split dict from the canonical samples (checked with `check_canonical_layout`)."""
    check_canonical_layout(samples)
    val = sorted(random.Random(seed).sample(sorted(VAL_POOL), N_VAL))
    test = list(TEST_SENTENCE_IDS)
    train = sorted(set(ALL_SENTENCE_IDS) - set(val) - set(test))
    d = {
        "version": SPLIT_VERSION,
        "seed": seed,
        "python": python_version if python_version is not None else platform.python_version(),
        "val_rule": VAL_RULE,
        "test_rule": TEST_RULE,
        "signer_split": {k: list(v) for k, v in SIGNER_SPLIT.items()},
        "usage": {
            "cslr": {"train": "signer_split.train x train_ids", "val": "signer_split.val x val_ids",
                     "test": "signer_split.test x test_ids (evaluated once, plan 13 §3.12)"},
            "vit5_stage2": {"train": "train_ids", "val": "val_ids", "test": "test_ids (evaluated once)"},
            "vit5_stage1": "10k pairs matching any sentence of val_ids or test_ids (L1/L2/near_dup) removed from train and val",
            "gloss_vocab": "glosses of the CSLR train samples only",
        },
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "train_ids": train,
        "val_ids": val,
        "test_ids": test,
    }
    validate_split_dict(d)
    return d


def split_file_bytes(d: Mapping[str, Any]) -> bytes:
    """Canonical on-disk form: UTF-8, indent 2, LF only, trailing newline (identical on Windows and Linux)."""
    return (json.dumps(d, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------------------------------------------------
# Sample selection
# ---------------------------------------------------------------------------------------------------------------------

def select_vslgh_samples(samples: Sequence[Mapping[str, Any]], split_name: str,
                         sentence_split: Union[SentenceSplit, PathLike]) -> List[Mapping[str, Any]]:
    """Samples of `split_name` = (signers of that split) x (sentences of that split), original order kept.

    Every sample must agree with the signer split (signer <-> `split` field); a mislabelled sample raises ValueError
    instead of being silently kept or dropped."""
    ss = resolve_sentence_split(sentence_split)
    if split_name not in SPLIT_NAMES:
        raise ValueError(f"unknown split name {split_name!r}; expected one of {SPLIT_NAMES}")
    signer_to_split = {sig: name for name in SPLIT_NAMES for sig in ss.signers(name)}
    sids = ss.ids(split_name)
    out = []
    for s in samples:
        signer, s_split = s.get("signer_id"), s.get("split")
        if signer_to_split.get(signer) != s_split:
            raise ValueError(f"sample {s.get('id')!r}: signer {signer!r} with split {s_split!r} breaks the signer split")
        if s_split == split_name and s.get("sentence_id") in sids:
            out.append(s)
    return out


def collect_glosses(samples: Iterable[Mapping[str, Any]]) -> set:
    """Unique stripped non-empty glosses (same rule as `VSLGlossVocabulary.from_canonical_dataset`)."""
    out = set()
    for s in samples:
        for g in s.get("gloss_sequence", []) or []:
            g_clean = g.strip()
            if g_clean:
                out.add(g_clean)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Held-out text matching (ViT5 stage 1, 10k corpus)
# ---------------------------------------------------------------------------------------------------------------------

def _normalizers():
    from src.translation.text_normalizer import normalize_vietnamese_target, normalize_vsl_source
    return normalize_vsl_source, normalize_vietnamese_target


def l2_text(l1: str) -> str:
    """L2 of an (already L1-normalised) text: lower-case, drop .,!?;:"'()[]{}…, collapse whitespace."""
    return _WS.sub(" ", _L2_DROP.sub("", l1.lower())).strip()


def _words(l2: str) -> List[str]:
    return l2.split()


@dataclass
class _Side:
    l1: Dict[str, set] = field(default_factory=dict)
    l2: Dict[str, set] = field(default_factory=dict)
    words: set = field(default_factory=set)  # {(word set, n words, sentence_id)}

    def add(self, l1: str, sid: str) -> None:
        if not l1:
            return
        self.l1.setdefault(l1, set()).add(sid)
        l2 = l2_text(l1)
        if not l2:
            return
        self.l2.setdefault(l2, set()).add(sid)
        w = _words(l2)
        self.words.add((frozenset(w), len(w), sid))


@dataclass
class HeldoutTexts:
    sentence_ids: Tuple[str, ...]
    source: _Side
    target: _Side


def heldout_texts(canonical_samples: Sequence[Mapping[str, Any]], ids: Iterable[str]) -> HeldoutTexts:
    """Every (source, target) text of the given sentences, over ALL signers and repetitions of the canonical data."""
    norm_src, norm_tgt = _normalizers()
    wanted = sorted(set(ids))
    present = {s.get("sentence_id") for s in canonical_samples}
    missing = [sid for sid in wanted if sid not in present]
    if missing:
        raise ValueError(f"held-out sentence ids not found in the canonical data: {missing[:5]}")
    wanted_set = set(wanted)
    src, tgt = _Side(), _Side()
    for s in canonical_samples:
        sid = s.get("sentence_id")
        if sid not in wanted_set:
            continue
        src.add(norm_src(s.get("gloss_sequence", []) or []), sid)
        tgt.add(norm_tgt(s.get("translation", "") or ""), sid)
    return HeldoutTexts(sentence_ids=tuple(wanted), source=src, target=tgt)


def _near_dup_ids(l2: str, side: _Side) -> List[str]:
    w = _words(l2)
    if not w:
        return []
    ws, n = set(w), len(w)
    num, den = NEAR_DUP_JACCARD
    hits = set()
    for hs, hn, sid in side.words:
        if abs(hn - n) > NEAR_DUP_MAX_WORD_DIFF:
            continue
        inter = len(ws & hs)
        union = len(ws | hs)
        if union and den * inter >= num * union:
            hits.add(sid)
    return sorted(hits)


def match_heldout(src: Any, tgt: str, heldout: HeldoutTexts) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """(True, reason) if the pair matches a held-out sentence, else (False, None).

    `src` / `tgt` may be raw or already normalised (the normalisers are idempotent). Rules are tried in the order
    L1, L2, near_dup and, within a rule, source before target; the first hit is reported:
    reason = {"rule": "L1"|"L2"|"near_dup", "side": "source"|"target", "sentence_ids": [...]}."""
    norm_src, norm_tgt = _normalizers()
    l1 = {"source": norm_src(src if src is not None else ""), "target": norm_tgt(tgt if tgt is not None else "")}
    sides = {"source": heldout.source, "target": heldout.target}
    for side in ("source", "target"):
        hit = sides[side].l1.get(l1[side]) if l1[side] else None
        if hit:
            return True, {"rule": "L1", "side": side, "sentence_ids": sorted(hit)}
    l2 = {k: l2_text(v) for k, v in l1.items()}
    for side in ("source", "target"):
        hit = sides[side].l2.get(l2[side]) if l2[side] else None
        if hit:
            return True, {"rule": "L2", "side": side, "sentence_ids": sorted(hit)}
    for side in ("source", "target"):
        hit = _near_dup_ids(l2[side], sides[side])
        if hit:
            return True, {"rule": "near_dup", "side": side, "sentence_ids": hit}
    return False, None


# ---------------------------------------------------------------------------------------------------------------------
# Leak checks (plan 13 §3.4e/§3.4f: "LEAK CHECK OK" before any training epoch; run on the very data about to be used)
# ---------------------------------------------------------------------------------------------------------------------

_SAMPLE_LEAK_KEYS = ("train_in_test", "train_in_val", "train_outside_train", "val_in_test", "val_outside_val",
                     "train_signers_outside", "val_signers_outside")


def sample_leak_report(sentence_split: Union[SentenceSplit, PathLike], train_samples: Iterable[Mapping[str, Any]],
                       val_samples: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Sentence (and, when the samples carry `signer_id`, signer) leakage of a train / val selection.

    Violations: a train sentence in T or V or outside Tr; a val sentence in T or outside V; a train signer outside the
    train signers; a val signer outside the val signers. `n_violations` = number of offending ids (0 = clean)."""
    ss = resolve_sentence_split(sentence_split)
    T, V, Tr = set(ss.test_ids), set(ss.val_ids), set(ss.train_ids)
    train_samples, val_samples = list(train_samples), list(val_samples)
    tr = {s.get("sentence_id") for s in train_samples}
    va = {s.get("sentence_id") for s in val_samples}
    tr_sig = {s.get("signer_id") for s in train_samples if "signer_id" in s}
    va_sig = {s.get("signer_id") for s in val_samples if "signer_id" in s}
    rep: Dict[str, Any] = {
        "sentence_split_sha256": ss.sha256,
        "n_train_samples": len(train_samples), "n_val_samples": len(val_samples),
        "n_train_sentences": len(tr), "n_val_sentences": len(va),
        "train_in_test": sorted(map(str, tr & T)), "train_in_val": sorted(map(str, tr & V)),
        "train_outside_train": sorted(map(str, tr - Tr)),
        "val_in_test": sorted(map(str, va & T)), "val_outside_val": sorted(map(str, va - V)),
        "train_signers_outside": sorted(map(str, tr_sig - set(ss.signers("train")))),
        "val_signers_outside": sorted(map(str, va_sig - set(ss.signers("val")))),
    }
    rep["n_violations"] = sum(len(rep[k]) for k in _SAMPLE_LEAK_KEYS)
    return rep


def text_leak_report(items: Iterable[Mapping[str, Any]], heldout: HeldoutTexts) -> Dict[str, Any]:
    """10k pairs (`id`, `vsl`, `vi`) that still match a held-out sentence (L1/L2/near_dup). 0 = clean."""
    hits = []
    n = 0
    for it in items:
        n += 1
        hit, reason = match_heldout(it.get("vsl"), it.get("vi"), heldout)
        if hit:
            hits.append({"id": it.get("id"), **reason})
    return {"n_items": n, "heldout_sentence_ids": list(heldout.sentence_ids), "matches": hits,
            "n_violations": len(hits)}


def vocab_leak_report(vocab_tokens: Sequence[str], allowed_glosses: Iterable[str],
                      specials: Sequence[str] = ("<blank>", "<unk>")) -> Dict[str, Any]:
    """The label space must be exactly specials + the glosses of the train selection (plan 13 §0.4)."""
    tokens = list(vocab_tokens)
    allowed = set(allowed_glosses)
    extra = sorted(t for t in tokens if t not in allowed and t not in specials)
    missing = sorted(allowed - set(tokens))
    return {"n_tokens": len(tokens), "n_allowed": len(allowed), "tokens_not_from_train": extra,
            "train_glosses_missing": missing, "n_violations": len(extra) + len(missing)}


def assert_no_leak(report: Mapping[str, Any], what: str) -> str:
    """Return the "LEAK CHECK OK (<what>): ..." line, or raise RuntimeError("LEAK CHECK FAILED ...")."""
    n = report.get("n_violations")
    if n != 0:
        details = {k: v for k, v in report.items() if isinstance(v, list) and v}
        raise RuntimeError(f"LEAK CHECK FAILED ({what}): {n} violation(s): {json.dumps(details, ensure_ascii=False)[:2000]}")
    counts = {k: v for k, v in report.items() if k.startswith("n_") and k != "n_violations"}
    return f"LEAK CHECK OK ({what}): " + ", ".join(f"{k}={v}" for k, v in counts.items())
