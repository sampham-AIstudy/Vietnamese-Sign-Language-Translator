import os
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=== STARTING V3: LEVEL 2 VOCABULARY TO VIT5 BRIDGE AUDIT ===")

# 1. Load Tier 2 classes (487 classes)
with open('configs/tier2_classes.txt', encoding='utf-8') as f:
    tier2_classes = [l.strip().lower() for l in f if l.strip()]

print(f"Total Tier 2 classes: {len(tier2_classes)}")

# 2. Load Cleaned 10K vocab
clean_10k = [json.loads(l) for l in open('data/external/parallel_text/vie_vsl_10k_cleaned.jsonl', encoding='utf-8') if l.strip()]
clean_10k_tokens = set()
for item in clean_10k:
    for tok in item.get('vsl', '').lower().split():
        clean_10k_tokens.add(tok)

# 3. Load VSL-GH canonical vocab
with open('data/external/vsl_gh/gloss_vocab_canonical.txt', encoding='utf-8') as f:
    vsl_gh_tokens = set(l.strip().lower().replace('-', ' ') for l in f if l.strip())

combined_training_vocab = clean_10k_tokens.union(vsl_gh_tokens)

# Map 487 classes to vocab
# A class can be a single word (e.g. 'đi') or compound (e.g. 'địa chỉ', 'mùa xuân', 'anh dũng')
in_10k_exact = 0
in_vslgh_exact = 0
in_combined_exact = 0
token_level_oov_count = 0
total_tokens_in_tier2 = 0

tier2_oov_classes = []
tier2_covered_classes = []

for c in tier2_classes:
    tokens = c.split()
    total_tokens_in_tier2 += len(tokens)
    
    # Check if all tokens of the class are known
    all_in_10k = all(tok in clean_10k_tokens for tok in tokens)
    all_in_vslgh = all(tok in vsl_gh_tokens or c in vsl_gh_tokens for tok in tokens)
    all_in_comb = all(tok in combined_training_vocab for tok in tokens)

    if all_in_10k: in_10k_exact += 1
    if all_in_vslgh: in_vslgh_exact += 1
    if all_in_comb:
        in_combined_exact += 1
        tier2_covered_classes.append(c)
    else:
        tier2_oov_classes.append(c)

    for tok in tokens:
        if tok not in combined_training_vocab:
            token_level_oov_count += 1

pct_covered = (in_combined_exact / len(tier2_classes)) * 100.0
pct_oov_tokens = (token_level_oov_count / total_tokens_in_tier2) * 100.0

print(f"\n--- VOCABULARY OVERLAP METRICS ---")
print(f"Tier 2 classes covered in Cleaned 10K (exact tokens): {in_10k_exact} / {len(tier2_classes)} ({in_10k_exact/len(tier2_classes)*100:.2f}%)")
print(f"Tier 2 classes covered in VSL-GH: {in_vslgh_exact} / {len(tier2_classes)} ({in_vslgh_exact/len(tier2_classes)*100:.2f}%)")
print(f"Tier 2 classes covered in Combined Training Vocab: {in_combined_exact} / {len(tier2_classes)} ({pct_covered:.2f}%)")
print(f"Token-level OOV Rate: {token_level_oov_count} / {total_tokens_in_tier2} ({pct_oov_tokens:.2f}%)")
print(f"Sample OOV Classes (total {len(tier2_oov_classes)}): {tier2_oov_classes[:10]}")

# 4. Code Trace
# (a) realtime_demo.py:
# Lines 318-326:
# current_history = smoothed.get("sentence", [])
# if self.translator and current_history and current_history != self.last_translated_history:
#     t_res = self.translator.translate(current_history)
# (b) backend/main.py:
# WebSocket /ws/live-stream does NOT call translator at all! It only returns "sentence": smoothed.get("sentence", []).
# ViT5 is ONLY called via REST POST /api/translate.

# 5. Run ViT5 on 10 realistic Tier 2 sign gloss phrases (3-5 words each)
from src.translation.translator import VSLTranslator
translator = VSLTranslator(model_path="checkpoints/vit5_stage2/best_model")

test_phrases = [
    # 1. Câu chào hỏi / giới thiệu
    "tôi chào bạn",
    # 2. Câu hỏi tên
    "bạn tên gì",
    # 3. Câu sức khỏe
    "tôi khám bệnh muốn",
    # 4. Câu gia đình
    "nhà tôi ba mẹ có",
    # 5. Câu chỉ địa điểm
    "địa chỉ trường học ở đâu",
    # 6. Câu sở thích
    "tôi xem phim thích",
    # 7. Câu thời gian
    "ngày mai đi học sẽ",
    # 8. Câu cảm ơn
    "tôi cảm ơn bác sĩ nhiều",
    # 9. Câu chứa từ OOV/hiếm trong 10k
    "cảnh sát giao thông bắt xe",
    # 10. Câu ghép từ Tier 2
    "bạn giúp đỡ tôi được không",
]

test_results = []
print("\n--- TESTING VIT5 TRANSLATION ON 10 TIER 2 PHRASES ---")
for p in test_phrases:
    res = translator.translate(p)
    out_txt = res["translation"]
    lat = res["latency_ms"]
    test_results.append({
        "input_gloss": p,
        "translation": out_txt,
        "latency_ms": round(lat, 2),
    })
    print(f"  Input:  '{p}'")
    print(f"  Output: '{out_txt}' ({lat:.1f}ms)\n")

v3_results = {
    "tier2_total_classes": len(tier2_classes),
    "classes_covered_in_combined": in_combined_exact,
    "coverage_pct": round(pct_covered, 2),
    "total_tokens": total_tokens_in_tier2,
    "oov_tokens_count": token_level_oov_count,
    "token_oov_pct": round(pct_oov_tokens, 2),
    "oov_classes_sample": tier2_oov_classes[:15],
    "code_trace": {
        "realtime_demo_py": "Accumulates confirmed isolated words in smoothed.get('sentence', []), calls translator.translate(current_history) on new word.",
        "backend_ws": "Returns confirmed words array in 'sentence' field, DOES NOT call ViT5 inside WebSocket loop. ViT5 is separate on REST POST /api/translate."
    },
    "test_phrases_evaluation": test_results,
}

with open('reports/audit_round2/v3_vocab_bridge.json', 'w', encoding='utf-8') as f:
    json.dump(v3_results, f, indent=2, ensure_ascii=False)

print("V3 completed and saved to reports/audit_round2/v3_vocab_bridge.json.")
