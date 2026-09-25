"""
prepare_canonical_translation.py
--------------------------------
Extracts, aligns, normalizes, and deduplicates the parallel Vie-VSL 10k corpus:
1. Aligns VSL10k.txt and Vie10k.txt line by line.
2. Applies Unicode NFC normalization.
3. Normalizes punctuation & whitespace while preserving word order.
4. Identifies and removes duplicate pairs.
5. Writes canonical output to data/external/parallel_text/vie_vsl_10k.jsonl.
6. Writes validation report to reports/translation_corpus_validation.json.
"""

import sys
import io
import json
import unicodedata
import re
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path("C:/Users/Admin/Python Advanced/Deep Learning - CV/Project")
CORPUS_DIR   = PROJECT_ROOT / "clone" / "Parallel-Corpus-Vie-VSL"
OUTPUT_DIR   = PROJECT_ROOT / "data" / "external" / "parallel_text"
REPORTS_DIR  = PROJECT_ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

VSL_SRC = CORPUS_DIR / "VSL10k.txt"
VIE_SRC = CORPUS_DIR / "Vie10k.txt"
OUTPUT_JSONL = OUTPUT_DIR / "vie_vsl_10k.jsonl"
REPORT_JSON  = REPORTS_DIR / "translation_corpus_validation.json"


def normalize_text(text: str) -> str:
    # Remove BOM and zero-width characters
    text = text.replace('\ufeff', '').replace('\u200b', '')
    # Unicode NFC normalization
    text = unicodedata.normalize('NFC', text)
    # Normalize punctuation characters
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = text.replace('…', '...').replace('–', '-').replace('—', '-')
    # Normalize spaces: multiple spaces into single space
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    return text.strip()


def main():
    print("=" * 70)
    print("STEP 1: Reading parallel corpus text files")
    print("=" * 70)

    with open(VSL_SRC, "r", encoding="utf-8") as f:
        vsl_lines = f.read().splitlines()

    with open(VIE_SRC, "r", encoding="utf-8") as f:
        vie_lines = f.read().splitlines()

    orig_count = len(vsl_lines)
    assert len(vie_lines) == orig_count, f"Line count mismatch: VSL={len(vsl_lines)} vs VIE={len(vie_lines)}"
    print(f"Loaded {orig_count} parallel lines from source files.")

    print("\n" + "=" * 70)
    print("STEP 2: Normalization and Deduplication")
    print("=" * 70)

    seen_pairs = set()
    canonical_entries = []
    duplicate_count = 0
    vsl_vocab = Counter = set()
    vi_vocab = set()

    for idx, (raw_vsl, raw_vi) in enumerate(zip(vsl_lines, vie_lines), start=1):
        clean_vsl = normalize_text(raw_vsl)
        clean_vi  = normalize_text(raw_vi)

        pair_key = (clean_vsl.lower(), clean_vi.lower())
        if pair_key in seen_pairs:
            duplicate_count += 1
            continue

        seen_pairs.add(pair_key)
        item_id = f"PAR_10K_{len(canonical_entries) + 1:05d}"
        canonical_entries.append({
            "id": item_id,
            "vsl": clean_vsl,
            "vi": clean_vi
        })

        for tok in clean_vsl.split():
            vsl_vocab.add(tok)
        for tok in clean_vi.split():
            vi_vocab.add(tok)

    final_count = len(canonical_entries)
    print(f"Original pairs:  {orig_count}")
    print(f"Duplicate pairs: {duplicate_count}")
    print(f"Final pairs:     {final_count}")
    print(f"VSL vocabulary size: {len(vsl_vocab)} unique tokens")
    print(f"Vie vocabulary size: {len(vi_vocab)} unique tokens")

    print("\n" + "=" * 70)
    print("STEP 3: Writing JSONL and validation report")
    print("=" * 70)

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for entry in canonical_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Canonical dataset saved to: {OUTPUT_JSONL}")

    report = {
        "status": "PASS",
        "dataset": "Vie-VSL Parallel Text 10k",
        "source_files": [
            str(VSL_SRC.relative_to(PROJECT_ROOT)),
            str(VIE_SRC.relative_to(PROJECT_ROOT))
        ],
        "original_pairs_count": orig_count,
        "duplicate_pairs_count": duplicate_count,
        "final_canonical_pairs_count": final_count,
        "vsl_unique_tokens": len(vsl_vocab),
        "vie_unique_tokens": len(vi_vocab),
        "unicode_normalization": "NFC",
        "schema": {
            "id": "PAR_10K_XXXXX",
            "vsl": "Sign language gloss / token order",
            "vi": "Spoken Vietnamese natural sentence"
        },
        "sample_head": canonical_entries[:3],
        "sample_tail": canonical_entries[-3:]
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Validation report saved to: {REPORT_JSON}")
    print("\nCANONICAL TRANSLATION CORPUS GENERATION COMPLETE!")


if __name__ == "__main__":
    main()
