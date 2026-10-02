"""Build `gloss_vocab_canonical.txt` (CSLR gloss vocabulary) from VSL-GH `dataset_canonical.json` — plan 13.

The original generator of this file was never committed (plan 13 B0: `git log --all -S gloss_vocab_canonical` only finds
readers), so the token order is taken from the project's own `VSLGlossVocabulary.from_canonical_dataset`
(`<blank>`, `<unk>`, then the unique stripped glosses sorted by code point). Unlike `VSLGlossVocabulary.save()` (text mode
=> CRLF on Windows), this script writes UTF-8 bytes with one token + LF per line on every OS, so the file — and the
`gloss_vocab_hash` (first 16 hex of sha256 of the raw bytes) stored in `cslr_best.pt` by `train_cslr.py` — is identical
on Windows and on the Kaggle kernel.

Usage:
  python scripts/build_gloss_vocab_canonical.py --canonical data/external/vsl_gh/dataset_canonical.json --out <file>
Exit codes: 0 written; 2 bad input (canonical missing) or `--out` already exists (never overwritten);
3 a token contains a line break (cannot be written one per line).
Prints one JSON object: out, n_tokens, sha256, vocab_hash16, canonical_lf_sha256.
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


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build gloss_vocab_canonical.txt (LF) from dataset_canonical.json")
    ap.add_argument("--canonical", required=True, help="path to VSL-GH dataset_canonical.json")
    ap.add_argument("--out", required=True, help="output vocab file (must not exist)")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.canonical):
        print(f"ERROR: canonical file not found: {args.canonical}", file=sys.stderr)
        return 2
    if os.path.lexists(args.out):
        print(f"ERROR: refusing to overwrite existing file: {args.out}", file=sys.stderr)
        return 2

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
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
