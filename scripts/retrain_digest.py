"""Digests shared by the local machine and the Kaggle kernels of plan 13 (retrain missing checkpoints).

- `sha256_file(path)`: sha256 of the raw bytes (binary files: .npy/.npz/.pt, ...).
- `lf_sha256(path)`: sha256 after replacing every CRLF pair with LF, for text files that Python writes in text mode
  (CRLF on Windows, LF on Linux). A lone CR is kept: it is content, not a line ending.
- `dir_digest(directory, pattern="*", names=None)`: combined digest of the regular files directly inside `directory`
  (not recursive) = sha256 of the UTF-8 text made of one line `"<file name> <sha256>\n"` per file, sorted by name.
  With `names`, exactly those file names are used (missing -> FileNotFoundError).

CLI (prints one JSON object):
  python scripts/retrain_digest.py sha256 FILE
  python scripts/retrain_digest.py lf-sha256 FILE
  python scripts/retrain_digest.py dir DIR [--pattern GLOB]
Read-only: never writes a file.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from typing import Iterable, List, Optional, Tuple

CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def lf_sha256(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def digest_entries(entries: Iterable[Tuple[str, str]]) -> str:
    """sha256 of `"<name> <sha256>\\n"` lines sorted by name."""
    text = "".join(f"{name} {digest}\n" for name, digest in sorted(entries))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_names(names: List[str]) -> None:
    seen = set()
    for n in names:
        if not n or n != os.path.basename(n) or n in (".", "..") or "/" in n or "\\" in n:
            raise ValueError(f"not a plain file name: {n!r}")
        if n in seen:
            raise ValueError(f"duplicate file name: {n!r}")
        seen.add(n)


def dir_digest(directory: str, pattern: str = "*", names: Optional[Iterable[str]] = None) -> Tuple[str, int]:
    """Return (combined digest, number of files) for regular files directly inside `directory`."""
    if names is not None:
        names = list(names)
        _check_names(names)
        selected = []
        for n in names:
            full = os.path.join(directory, n)
            if not os.path.isfile(full):
                raise FileNotFoundError(full)
            selected.append(n)
    else:
        selected = [
            e.name for e in os.scandir(directory)
            if e.is_file(follow_symlinks=False) and fnmatch.fnmatchcase(e.name, pattern)
        ]
    entries = [(n, sha256_file(os.path.join(directory, n))) for n in selected]
    return digest_entries(entries), len(entries)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sha256")
    a.add_argument("path")
    b = sub.add_parser("lf-sha256")
    b.add_argument("path")
    c = sub.add_parser("dir")
    c.add_argument("path")
    c.add_argument("--pattern", default="*")
    args = ap.parse_args(argv)
    if args.cmd == "sha256":
        res = {"path": args.path, "sha256": sha256_file(args.path)}
    elif args.cmd == "lf-sha256":
        res = {"path": args.path, "lf_sha256": lf_sha256(args.path)}
    else:
        digest, n = dir_digest(args.path, pattern=args.pattern)
        res = {"path": args.path, "pattern": args.pattern, "n_files": n, "dir_digest": digest}
    print(json.dumps(res, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
