"""
Phase 4B Comprehensive Evaluation Script
Compares:
1. Model A: Stage 1 only (Pretrained on Cleaned 10K only)
2. Model B: Stage 1 + Stage 2 (Cleaned 10K + VSL-GH Fine-Tuned)

Modes:
- Mode A: Oracle Ground-Truth Gloss -> Natural Vietnamese Text
- Mode B: CSLR Output (cslr_best.pt predictions on S06) -> Natural Vietnamese Text

Evaluation Sets:
- Subset 1: Held-Out Unseen Sentences on S06 (SENT271-SENT300, 30 samples) - 100% leak-free
- Subset 2: Full S06 Unseen Signer (SENT001-SENT300, 300 samples)
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.translation.text_normalizer import normalize_vsl_source, normalize_vietnamese_target
from src.translation.metrics import compute_translation_metrics


def run_inference(
    model: AutoModelForSeq2SeqLM,
    tokenizer: AutoTokenizer,
    sources: List[str],
    device: torch.device,
    batch_size: int = 16,
    num_beams: int = 4,
    max_length: int = 64,
) -> List[str]:
    """Runs beam search generation on list of source strings."""
    model.eval()
    predictions = []

    for i in range(0, len(sources), batch_size):
        batch_src = sources[i : i + batch_size]
        inputs = tokenizer(
            batch_src,
            max_length=128,
            padding=True,
            truncation=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                num_beams=num_beams,
                max_length=max_length,
                early_stopping=True,
            )

        batch_preds = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        for pred in batch_preds:
            predictions.append(normalize_vietnamese_target(pred))

    return predictions


def evaluate_model_on_data(
    model_path: Path,
    model_label: str,
    s06_samples: List[Dict[str, Any]],
    device: torch.device,
) -> Dict[str, Any]:
    print(f"\n[BENCHMARK] Evaluating: {model_label} from {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path)).to(device)

    # Prepare datasets
    # Split S06 into full (300) and held-out unseen sentences (SENT271-SENT300, 30 samples)
    held_out_samples = [s for s in s06_samples if s["sentence_id"] >= "SENT271"]
    print(f"  - Full S06 samples: {len(s06_samples)}")
    print(f"  - Held-out sentences (SENT271-SENT300): {len(held_out_samples)}")

    results = {"model_label": model_label, "model_path": str(model_path)}

    eval_splits = [
        ("held_out_unseen_sentences_30", held_out_samples),
        ("full_s06_unseen_signer_300", s06_samples),
    ]

    for split_key, split_samples in eval_splits:
        ref_targets = [normalize_vietnamese_target(s["translation"]) for s in split_samples]

        # Mode A: Oracle Gloss -> Text
        mode_a_sources = [normalize_vsl_source(s["ref_gloss_list"]) for s in split_samples]
        mode_a_preds = run_inference(model, tokenizer, mode_a_sources, device)
        mode_a_metrics = compute_translation_metrics(mode_a_preds, ref_targets)

        # Mode B: CSLR Predicted Gloss -> Text
        mode_b_sources = [normalize_vsl_source(s["pred_gloss_list"]) for s in split_samples]
        mode_b_preds = run_inference(model, tokenizer, mode_b_sources, device)
        mode_b_metrics = compute_translation_metrics(mode_b_preds, ref_targets)

        # Qualitative examples (first 5)
        qualitative = []
        for i in range(min(5, len(split_samples))):
            s = split_samples[i]
            qualitative.append({
                "sample_id": s["sample_id"],
                "sentence_id": s["sentence_id"],
                "ref_gloss": " ".join(s["ref_gloss_list"]),
                "pred_cslr_gloss": " ".join(s["pred_gloss_list"]),
                "ground_truth_target": ref_targets[i],
                "mode_a_output": mode_a_preds[i],
                "mode_b_output": mode_b_preds[i],
            })

        results[split_key] = {
            "num_samples": len(split_samples),
            "mode_a_oracle": mode_a_metrics,
            "mode_b_cslr": mode_b_metrics,
            "qualitative_examples": qualitative,
        }

        print(f"  [{split_key}] Mode A (Oracle) -> BLEU: {mode_a_metrics['bleu']} | ROUGE-L: {mode_a_metrics['rouge_l']} | EM: {mode_a_metrics['exact_match']}%")
        print(f"  [{split_key}] Mode B (CSLR)   -> BLEU: {mode_b_metrics['bleu']} | ROUGE-L: {mode_b_metrics['rouge_l']} | EM: {mode_b_metrics['exact_match']}%")

    return results


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[BENCHMARK] Device: {device}")

    # Load S06 CSLR predictions
    cslr_pred_path = project_root / "reports" / "cslr_s06_predictions.json"
    if not cslr_pred_path.exists():
        raise FileNotFoundError(f"CSLR predictions file not found: {cslr_pred_path}")

    with open(cslr_pred_path, "r", encoding="utf-8") as f:
        s06_samples = json.load(f)
    print(f"[BENCHMARK] Loaded {len(s06_samples)} S06 sample predictions")

    stage1_path = project_root / "checkpoints" / "vit5_stage1" / "best_model"
    stage2_path = project_root / "checkpoints" / "vit5_stage2" / "best_model"

    all_evaluations = {}

    if stage1_path.exists():
        all_evaluations["stage1_only"] = evaluate_model_on_data(
            stage1_path, "ViT5 (Stage 1 Only: Cleaned 10K)", s06_samples, device
        )
    else:
        print(f"[WARN] Stage 1 checkpoint not found at: {stage1_path}")

    if stage2_path.exists():
        all_evaluations["stage1_plus_stage2"] = evaluate_model_on_data(
            stage2_path, "ViT5 (Stage 1 + Stage 2: 10K + VSL-GH)", s06_samples, device
        )
    else:
        print(f"[WARN] Stage 2 checkpoint not found at: {stage2_path}")

    # Save JSON report
    rep_dir = project_root / "reports"
    rep_dir.mkdir(exist_ok=True)
    out_json = rep_dir / "translation_phase4b_benchmark.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_evaluations, f, indent=2, ensure_ascii=False)
    print(f"\n[BENCHMARK] Saved detailed JSON benchmark report to: {out_json}")


if __name__ == "__main__":
    main()
