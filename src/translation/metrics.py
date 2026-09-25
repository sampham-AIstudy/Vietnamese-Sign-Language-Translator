"""
Translation Metrics Calculation Module
Computes:
- SacreBLEU / BLEU (BLEU-1, BLEU-2, BLEU-3, BLEU-4)
- ROUGE-1, ROUGE-2, ROUGE-L (via rouge_score)
- Exact Match (EM)
- Word Error Rate (WER)
"""

from typing import List, Dict, Any, Tuple
import sacrebleu
from rouge_score import rouge_scorer
import numpy as np


def compute_translation_metrics(
    hypotheses: List[str],
    references: List[str],
) -> Dict[str, float]:
    """
    Computes standard MT metrics between hypothesis list and reference list.
    Both should be lists of strings of the same length.
    """
    assert len(hypotheses) == len(references), f"Length mismatch: {len(hypotheses)} vs {len(references)}"

    if not hypotheses:
        return {
            "bleu": 0.0,
            "bleu_1": 0.0,
            "bleu_2": 0.0,
            "bleu_3": 0.0,
            "bleu_4": 0.0,
            "rouge_1": 0.0,
            "rouge_2": 0.0,
            "rouge_l": 0.0,
            "exact_match": 0.0,
        }

    # 1. SacreBLEU calculation
    # sacrebleu expects references as list of lists: [[ref1, ref2, ...]]
    bleu_res = sacrebleu.corpus_bleu(hypotheses, [references])
    bleu_score = bleu_res.score
    bleu_precisions = bleu_res.precisions  # [p1, p2, p3, p4]

    # 2. ROUGE calculation
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)
    r1_list = []
    r2_list = []
    rl_list = []

    exact_matches = 0
    for hyp, ref in zip(hypotheses, references):
        hyp_clean = hyp.strip()
        ref_clean = ref.strip()
        if hyp_clean.lower() == ref_clean.lower():
            exact_matches += 1

        scores = scorer.score(ref_clean, hyp_clean)
        r1_list.append(scores["rouge1"].fmeasure)
        r2_list.append(scores["rouge2"].fmeasure)
        rl_list.append(scores["rougeL"].fmeasure)

    r1_mean = float(np.mean(r1_list)) * 100.0 if r1_list else 0.0
    r2_mean = float(np.mean(r2_list)) * 100.0 if r2_list else 0.0
    rl_mean = float(np.mean(rl_list)) * 100.0 if rl_list else 0.0
    em_rate = (exact_matches / len(hypotheses)) * 100.0 if hypotheses else 0.0

    return {
        "bleu": round(bleu_score, 2),
        "bleu_1": round(bleu_precisions[0], 2) if len(bleu_precisions) > 0 else 0.0,
        "bleu_2": round(bleu_precisions[1], 2) if len(bleu_precisions) > 1 else 0.0,
        "bleu_3": round(bleu_precisions[2], 2) if len(bleu_precisions) > 2 else 0.0,
        "bleu_4": round(bleu_precisions[3], 2) if len(bleu_precisions) > 3 else 0.0,
        "rouge_1": round(r1_mean, 2),
        "rouge_2": round(r2_mean, 2),
        "rouge_l": round(rl_mean, 2),
        "exact_match": round(em_rate, 2),
    }
