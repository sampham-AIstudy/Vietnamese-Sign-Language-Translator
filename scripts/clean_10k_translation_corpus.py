"""
Clean and filter the 10K parallel corpus:
1. Remove identical pairs (vi == vsl) ~23.42%.
2. Remove severe semantic mismatches / corruptions.
3. Repair known regex / tokenization bugs.
4. Normalize punctuation spacing.
Output: data/external/parallel_text/vie_vsl_10k_cleaned.jsonl
"""

import json
import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
raw_path = project_root / "data" / "external" / "parallel_text" / "vie_vsl_10k.jsonl"
clean_path = project_root / "data" / "external" / "parallel_text" / "vie_vsl_10k_cleaned.jsonl"

with open(raw_path, "r", encoding="utf-8") as f:
    raw_data = [json.loads(line) for line in f]

print(f"[CLEAN] Loaded {len(raw_data)} raw pairs from {raw_path}")

cleaned_pairs = []
stats = {
    "identical_removed": 0,
    "semantic_mismatch_removed": 0,
    "fixed_artifacts": 0,
    "retained": 0,
}

for item in raw_data:
    vsl = item["vsl"].strip()
    vi = item["vi"].strip()

    # 1. Check identical
    vi_norm = re.sub(r'[^\w\s]', '', vi.lower()).strip()
    vsl_norm = re.sub(r'[^\w\s]', '', vsl.lower()).strip()
    if not vi_norm or not vsl_norm:
        stats["identical_removed"] += 1
        continue
    if vi_norm == vsl_norm:
        stats["identical_removed"] += 1
        continue

    # 2. Known corrupted / severe misaligned IDs
    # e.g. PAR_10K_03005 is completely misaligned (money machine vs regret what you did)
    if item["id"] in ["PAR_10K_03005"]:
        stats["semantic_mismatch_removed"] += 1
        continue

    # Length ratio filter (length ratio between words should not exceed 3.5)
    len_vsl = len(vsl_norm.split())
    len_vi = len(vi_norm.split())
    if len_vsl < 1 or len_vi < 1:
        continue
    if len_vi / len_vsl > 3.5 or len_vsl / len_vi > 3.5:
        stats["semantic_mismatch_removed"] += 1
        continue

    # 3. Fix known regex and typographical corruptions
    original_vsl = vsl
    # Fix broken "l ; òng"
    vsl = re.sub(r'l\s*;\s*òng', 'lòng', vsl, flags=re.IGNORECASE)
    vi = re.sub(r'l\s*;\s*òng', 'lòng', vi, flags=re.IGNORECASE)

    # Fix broken "k = phong cách"
    vsl = re.sub(r'k\s*=\s*phong cách', 'phong cách', vsl, flags=re.IGNORECASE)
    vi = re.sub(r'k\s*=\s*phong cách', 'phong cách', vi, flags=re.IGNORECASE)

    # Fix "ở m ơn không" -> "ở đây không làm ơn"
    if "ở m ơn không" in vsl:
        vsl = vsl.replace("ở m ơn không", "ở đây làm ơn không")

    # Fix generic "m ơn" if isolated
    if re.search(r'\bm ơn\b', vsl, re.IGNORECASE):
        vsl = re.sub(r'\bm ơn\b', 'làm ơn', vsl, flags=re.IGNORECASE)

    if vsl != original_vsl:
        stats["fixed_artifacts"] += 1

    # Normalize excessive spaces
    vsl = re.sub(r'\s+', ' ', vsl).strip()
    vi = re.sub(r'\s+', ' ', vi).strip()

    cleaned_pairs.append({
        "id": item["id"],
        "vsl": vsl,
        "vi": vi,
    })

stats["retained"] = len(cleaned_pairs)

with open(clean_path, "w", encoding="utf-8") as f:
    for item in cleaned_pairs:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"[CLEAN] Finished cleaning:")
print(f"  - Identical pairs removed: {stats['identical_removed']}")
print(f"  - Severe misalignments removed: {stats['semantic_mismatch_removed']}")
print(f"  - Fixed corrupted artifacts: {stats['fixed_artifacts']}")
print(f"  - Cleaned pairs retained: {stats['retained']} ({stats['retained']/len(raw_data)*100:.2f}%)")
print(f"  - Saved to: {clean_path}")
