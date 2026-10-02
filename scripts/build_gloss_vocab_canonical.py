"""Build `gloss_vocab_canonical.txt` (CSLR gloss vocabulary) from VSL-GH `dataset_canonical.json` — plan 13.

The original generator of this file was never committed (plan 13 B0: `git log --all -S gloss_vocab_canonical` only finds
readers), so the token order is taken from the project's own `VSLGlossVocabulary.from_canonical_dataset`
(`<blank>`, `<unk>`, then the unique stripped glosses sorted by code point). Unlike `VSLGlossVocabulary.save()` (text mode
=> CRLF on Windows), this script writes UTF-8 bytes with one token + LF per line on every OS, so the file — and the
`gloss_vocab_hash` (first 16 hex of sha256 of the raw bytes) stored in `cslr_best.pt` by `train_cslr.py` — is identical
on Windows and on the Kaggle kernel.

Usage:
  python scripts/build_gloss_vocab_canonical.py --canonical data/external/vsl_gh/dataset_canonical.json --out <file>
  python scripts/build_gloss_vocab_canonical.py --canonical ... --out <file>       --sentence-split configs/vslgh_sentence_split_v1.json --split train          (plan 13 LS1, train-only vocabulary)
Exit codes: 0 written; 2 bad input (canonical missing, invalid split file / signer layout, `--sentence-split` and `--split`
not given together) or `--out` already exists (never overwritten); 3 a token contains a line break.
Prints one JSON object: out, n_tokens, sha256, vocab_hash16, canonical_lf_sha256 (+ with `--sentence-split`: split,
sentence_split, sentence_split_sha256, n_samples_selected, glosses_excluded = glosses of the full file not in the selection).
Without `--sentence-split` the output file and the JSON are exactly as before (plan 13 B2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (ROOT, os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from retrain_digest import lf_sha256  # noqa: E402


def build_tokens(canonical_path: str) -> List[str]:
    from src.data.vsl_gh_dataset import VSLGlossVocabulary

    vocab = VSLGlossVocabulary.from_canonical_dataset(canonical_path)
    return [vocab.id_to_gloss[i] for i in range(len(vocab))]


def build_tokens_train_only(canonical_path: str, sentence_split_path: str, split: str = "train"):
    """Vocabulary of the CSLR samples of `split` under the sentence split (plan 13 §0.4): same token order as
    `VSLGlossVocabulary` (<blank>, <unk>, sorted glosses). Returns (tokens, glosses_excluded, n_samples_selected)."""
    import json as _json

    from src.data.sentence_split import collect_glosses, load_sentence_split, select_vslgh_samples
    from src.data.vsl_gh_dataset import VSLGlossVocabulary

    with open(canonical_path, "r", encoding="utf-8") as f:
        samples = _json.load(f)
    selected = select_vslgh_samples(samples, split, load_sentence_split(sentence_split_path))
    vocab = VSLGlossVocabulary(tokens=list(collect_glosses(selected)))
    tokens = [vocab.id_to_gloss[i] for i in range(len(vocab))]
    excluded = sorted(collect_glosses(samples) - set(tokens))
    return tokens, excluded, len(selected)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build gloss_vocab_canonical.txt (LF) from dataset_canonical.json")
    ap.add_argument("--canonical", required=True, help="path to VSL-GH dataset_canonical.json")
    ap.add_argument("--out", required=True, help="output vocab file (must not exist)")
    ap.add_argument("--sentence-split", default=None, help="plan 13: sentence split file; vocab from --split samples only")
    ap.add_argument("--split", default=None, choices=["train"], help="plan 13: which CSLR split feeds the vocab (train)")
    args = ap.parse_args(argv)
    if (args.sentence_split is None) != (args.split is None):
        print("ERROR: --sentence-split and --split must be given together", file=sys.stderr)
        return 2

    if not os.path.isfile(args.canonical):
        print(f"ERROR: canonical file not found: {args.canonical}", file=sys.stderr)
        return 2
    if os.path.lexists(args.out):
        print(f"ERROR: refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2

    extra = {}
    if args.sentence_split is not None:
        from src.data.sentence_split import load_sentence_split

        try:
            ss = load_sentence_split(args.sentence_split)
            tokens, excluded, n_selected = build_tokens_train_only(args.canonical, args.sentence_split, args.split)
        except (OSError, ValueError) as exc:
            print(f"ERROR: sentence split: {exc}", file=sys.stderr)
            return 2
        extra = {"split": args.split, "sentence_split": args.sentence_split, "sentence_split_sha256": ss.sha256,
                 "n_samples_selected": n_selected, "glosses_excluded": excluded}
    else:
        tokens = build_tokens(args.canonical)
    bad = [t for t in tokens if "\n" in t or "\r" in t]
    if bad:
        print(f"ERROR: {len(bad)} token(s) contain a line break, e.g. {bad[0]!r}", file=sys.stderr)
        return 3
    data = "".join(t + "\n" for t in tokens).encode("utf-8")

    parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(parent, exist_ok=True)
    try:
        with open(args.out, "xb") as f:  # exclusive create: never overwrite, even on a race
            f.write(data)
    except FileExistsError:
        print(f"ERROR: refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2

    digest = hashlib.sha256(data).hexdigest()
    print(json.dumps({
        "out": args.out,
        "n_tokens": len(tokens),
        "sha256": digest,
        "vocab_hash16": digest[:16],
        "canonical_lf_sha256": lf_sha256(args.canonical),
        **extra,
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
