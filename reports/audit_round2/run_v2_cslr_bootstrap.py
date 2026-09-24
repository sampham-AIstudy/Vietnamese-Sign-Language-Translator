import os
import sys
import io
import json
import time
from pathlib import Path
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translation.text_normalizer import normalize_vsl_source, normalize_vietnamese_target
from src.translation.metrics import compute_translation_metrics

print("=== STARTING V2: LEVEL 3 EVALUATION RELIABILITY & BOOTSTRAP CI ===")

# 1. Load S06 samples
with open('reports/cslr_s06_predictions.json', encoding='utf-8') as f:
    s06_samples = json.load(f)

# Count sentence breakdown
total_samples = len(s06_samples)
unseen_samples = [s for s in s06_samples if s["sentence_id"] >= "SENT271"]
seen_samples = [s for s in s06_samples if s["sentence_id"] < "SENT271"]

print(f"Total S06 test clips: {total_samples}")
print(f"  - Unseen sentences (SENT271-SENT300): {len(unseen_samples)} ({len(unseen_samples)/total_samples*100:.1f}%)")
print(f"  - Seen sentences in train (SENT001-SENT270): {len(seen_samples)} ({len(seen_samples)/total_samples*100:.1f}%)")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_path = Path("checkpoints/vit5_stage2/best_model")
tokenizer = AutoTokenizer.from_pretrained(str(model_path))
model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path)).to(device)
model.eval()

# Generate predictions for 30 unseen sentences
unseen_refs = [normalize_vietnamese_target(s["translation"]) for s in unseen_samples]
mode_a_srcs = [normalize_vsl_source(s["ref_gloss_list"]) for s in unseen_samples]
mode_b_srcs = [normalize_vsl_source(s["pred_gloss_list"]) for s in unseen_samples]

def batch_generate(sources):
    preds = []
    inputs = tokenizer(sources, max_length=128, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], num_beams=4, max_length=64)
    raw = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return [normalize_vietnamese_target(r) for r in raw]

mode_a_preds = batch_generate(mode_a_srcs)
mode_b_preds = batch_generate(mode_b_srcs)

# Base metrics
base_a = compute_translation_metrics(mode_a_preds, unseen_refs)
base_b = compute_translation_metrics(mode_b_preds, unseen_refs)
print(f"30 Unseen Sentences Base BLEU: Mode A (Oracle) = {base_a['bleu']:.2f}, Mode B (CSLR) = {base_b['bleu']:.2f}")

# 2. Bootstrap 95% CI for BLEU on 30 unseen sentences (N=1000)
import sacrebleu

np.random.seed(42)
N_BOOTSTRAP = 1000
boot_a_bleu = []
boot_b_bleu = []
boot_diff_bleu = []

n = len(unseen_samples)
for _ in range(N_BOOTSTRAP):
    idx = np.random.choice(n, size=n, replace=True)
    b_refs = [unseen_refs[i] for i in idx]
    b_preds_a = [mode_a_preds[i] for i in idx]
    b_preds_b = [mode_b_preds[i] for i in idx]

    score_a = sacrebleu.corpus_bleu(b_preds_a, [b_refs]).score
    score_b = sacrebleu.corpus_bleu(b_preds_b, [b_refs]).score
    boot_a_bleu.append(score_a)
    boot_b_bleu.append(score_b)
    boot_diff_bleu.append(score_a - score_b)

ci_a = (np.percentile(boot_a_bleu, 2.5), np.percentile(boot_a_bleu, 97.5))
ci_b = (np.percentile(boot_b_bleu, 2.5), np.percentile(boot_b_bleu, 97.5))
ci_diff = (np.percentile(boot_diff_bleu, 2.5), np.percentile(boot_diff_bleu, 97.5))

print(f"Mode A (Oracle) BLEU 95% CI: [{ci_a[0]:.2f}, {ci_a[1]:.2f}]")
print(f"Mode B (CSLR)   BLEU 95% CI: [{ci_b[0]:.2f}, {ci_b[1]:.2f}]")
print(f"Delta (Mode A - Mode B) BLEU 95% CI: [{ci_diff[0]:.2f}, {ci_diff[1]:.2f}]")

# Statistical significance check: does the 95% CI of Delta include 0?
is_sig_diff = not (ci_diff[0] <= 0 <= ci_diff[1])
print(f"Is Delta statistically significant (p < 0.05)?: {is_sig_diff} (Zero included: {ci_diff[0] <= 0 <= ci_diff[1]})")

# 3. Bootstrap 95% CI for CSLR WER on 300 test samples
# Calculate per-sample edits
def levenshtein_distance(ref_tokens, hyp_tokens):
    dp = np.zeros((len(ref_tokens) + 1, len(hyp_tokens) + 1), dtype=int)
    for i in range(len(ref_tokens) + 1): dp[i][0] = i
    for j in range(len(hyp_tokens) + 1): dp[0][j] = j
    for i in range(1, len(ref_tokens) + 1):
        for j in range(1, len(hyp_tokens) + 1):
            if ref_tokens[i-1] == hyp_tokens[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[len(ref_tokens)][len(hyp_tokens)]

sample_edits = []
sample_ref_lens = []
for s in s06_samples:
    r_toks = s["ref_gloss_list"]
    p_toks = s["pred_gloss_list"]
    ed = levenshtein_distance(r_toks, p_toks)
    sample_edits.append(ed)
    sample_ref_lens.append(len(r_toks))

sample_edits = np.array(sample_edits)
sample_ref_lens = np.array(sample_ref_lens)
base_wer = (sample_edits.sum() / sample_ref_lens.sum()) * 100.0
print(f"\nCSLR Base WER on S06: {base_wer:.2f}% (Reported in cslr_test_results.json: 32.80%)")

boot_wer = []
M = len(s06_samples)
for _ in range(N_BOOTSTRAP):
    idx = np.random.choice(M, size=M, replace=True)
    b_wer = (sample_edits[idx].sum() / sample_ref_lens[idx].sum()) * 100.0
    boot_wer.append(b_wer)

ci_wer = (np.percentile(boot_wer, 2.5), np.percentile(boot_wer, 97.5))
print(f"CSLR WER 95% CI: [{ci_wer[0]:.2f}%, {ci_wer[1]:.2f}%]")

v2_results = {
    "sample_counts": {
        "total_test_samples": total_samples,
        "unseen_sentences_count": len(unseen_samples),
        "seen_sentences_in_train_count": len(seen_samples),
        "seen_overlap_ratio": round(len(seen_samples) / total_samples * 100.0, 2),
        "num_signers": 6,
    },
    "bleu_bootstrap_30_unseen": {
        "mode_a_oracle": {"point_estimate": round(base_a['bleu'], 2), "ci_95": [round(ci_a[0], 2), round(ci_a[1], 2)]},
        "mode_b_cslr": {"point_estimate": round(base_b['bleu'], 2), "ci_95": [round(ci_b[0], 2), round(ci_b[1], 2)]},
        "delta_mode_a_minus_b": {
            "point_estimate": round(base_a['bleu'] - base_b['bleu'], 2),
            "ci_95": [round(ci_diff[0], 2), round(ci_diff[1], 2)],
            "is_statistically_significant": is_sig_diff,
        }
    },
    "cslr_wer_bootstrap_300": {
        "point_estimate": round(base_wer, 2),
        "ci_95": [round(ci_wer[0], 2), round(ci_wer[1], 2)],
    },
    "conclusion": (
        "Khoảng tin cậy delta giữa Mode A và Mode B "
        + ("KHÔNG bao gồm 0, chứng minh chênh lệch có ý nghĩa thống kê (p < 0.05)." if is_sig_diff else "BAO GỒM 0, chứng minh chênh lệch giữa Oracle và CSLR trên 30 câu unseen chưa có ý nghĩa thống kê rõ rệt do cỡ mẫu N=30 nhỏ.")
    )
}

with open('reports/audit_round2/v2_cslr_reliability.json', 'w', encoding='utf-8') as f:
    json.dump(v2_results, f, indent=2, ensure_ascii=False)

print("\nV2 completed and saved to reports/audit_round2/v2_cslr_reliability.json.")
