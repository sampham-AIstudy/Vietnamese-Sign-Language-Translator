"""
Task list for Level 1 extraction (scripts/extract_hands_batch.py).

Sources (real recordings only):
  hauuto  : Kaggle hauuto/vietnamese-sign-language-alphabet, raw/raw/<signer>/<code>_<signer>_<A|B>_<n>.mp4
            4 signers x 34 classes (29 Vietnamese letters + 5 tone marks), codes in Telex.
  qipedc  : QIPEDC dictionary videos whose label is a single letter (independent signers) —
            used only as an external test set.
Usage:
  python scripts/build_alphabet_tasks.py --hauuto-raw <dir> --qipedc-labels <label.csv> \
      --qipedc-videos <dir> --out tasks.csv
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_label_inventory import normalize_label  # noqa: E402

TELEX_TO_LABEL = {
    "a": "a", "aw": "ă", "aa": "â", "b": "b", "c": "c", "d": "d", "dd": "đ", "e": "e", "ee": "ê",
    "g": "g", "h": "h", "i": "i", "k": "k", "l": "l", "m": "m", "n": "n", "o": "o", "oo": "ô",
    "ow": "ơ", "p": "p", "q": "q", "r": "r", "s": "s", "t": "t", "u": "u", "uw": "ư", "v": "v",
    "x": "x", "y": "y",
    "tone_s": "dấu sắc", "tone_f": "dấu huyền", "tone_r": "dấu hỏi", "tone_x": "dấu ngã", "tone_j": "dấu nặng",
}
ALPHABET_CLASSES = list(TELEX_TO_LABEL.values())  # 29 letters + 5 tone marks, fixed order
LETTERS = set(ALPHABET_CLASSES[:29])
PATTERN = re.compile(r"^(?P<code>.+)_(?P<signer>[a-z]+)_(?P<session>[AB])_(?P<n>\d+)\.mp4$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hauuto-raw", required=True)
    ap.add_argument("--qipedc-labels")
    ap.add_argument("--qipedc-videos")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows, unknown = [], []
    for signer in sorted(os.listdir(args.hauuto_raw)):
        d = os.path.join(args.hauuto_raw, signer)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            m = PATTERN.match(name)
            if not m:
                continue
            if m["code"] not in TELEX_TO_LABEL:
                unknown.append(name)
                continue
            rows.append({"video_path": os.path.join(d, name), "sample_id": f"hauuto_{os.path.splitext(name)[0]}",
                         "symbol": TELEX_TO_LABEL[m["code"]], "signer_id": f"hauuto_{m['signer']}",
                         "source": "hauuto", "session": m["session"]})
    if args.qipedc_labels:
        with open(args.qipedc_labels, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                label = normalize_label(r["LABEL"])
                path = os.path.join(args.qipedc_videos, r["VIDEO"].strip())
                if label in LETTERS and os.path.exists(path):
                    rows.append({"video_path": path, "sample_id": f"qipedc_{os.path.splitext(r['VIDEO'].strip())[0]}",
                                 "symbol": label, "signer_id": "qipedc", "source": "qipedc", "session": ""})
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["video_path", "sample_id", "symbol", "signer_id", "source", "session"])
        w.writeheader()
        w.writerows(rows)
    by_src = {}
    for r in rows:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    print(f"{len(rows)} tasks {by_src}; classes {len({r['symbol'] for r in rows})}; unknown codes: {unknown[:10]}")


if __name__ == "__main__":
    main()
