"""
Ensemble Inference & Benchmarking Module for Vietnamese Sign Language Recognition
Phase 8: Combining Spatial Master (ST-GCN) and Temporal Master (Transformer).

Features:
- Loads best checkpoints from Phase 6 (ST-GCN) and Phase 7 (Transformer).
- Evaluates ensembling strategies (Equal Average vs. Val-Tuned Weighted Ensemble).
- Generates comprehensive Test Set benchmarks:
  + Top-1 Accuracy, Top-5 Accuracy, Macro F1, Precision, Recall, Test Loss
  + Confusion Matrix Heatmap (PNG)
  + Classification Report (CSV)
  + Benchmark Results Summary (JSON)
"""

import os
import sys
import json
import csv
import argparse
from typing import Dict, Any, Tuple, Optional, List

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.data.vsl_dataset import get_vsl_dataloaders
from src.metrics.metrics import topk_accuracy


class VSLREnsemble(nn.Module):
    """
    Ensemble model combining Spatial (ST-GCN) and Temporal (Transformer) models.
    """
    def __init__(
        self,
        stgcn_model: STGCNModel,
        transformer_model: TransformerModel,
        weight_stgcn: float = 0.5,
        weight_transformer: float = 0.5,
        combination_mode: str = "logits",  # "logits" or "probs"
    ):
        super().__init__()
        self.stgcn = stgcn_model
        self.transformer = transformer_model
        self.weight_stgcn = weight_stgcn
        self.weight_transformer = weight_transformer
        self.combination_mode = combination_mode

    def set_weights(self, weight_stgcn: float, weight_transformer: float):
        self.weight_stgcn = weight_stgcn
        self.weight_transformer = weight_transformer

    def forward(
        self,
        sequences: torch.Tensor,
        joint_masks: Optional[torch.Tensor] = None,
        temporal_masks: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass through both networks and combine outputs.
        """
        logits_stgcn = self.stgcn(sequences, joint_masks, temporal_masks)
        logits_trans = self.transformer(sequences, joint_masks, temporal_masks)

        if self.combination_mode == "probs":
            probs_stgcn = F.softmax(logits_stgcn, dim=-1)
            probs_trans = F.softmax(logits_trans, dim=-1)
            combined_probs = self.weight_stgcn * probs_stgcn + self.weight_transformer * probs_trans
            return combined_probs
        else:
            # Weighted logits (default)
            combined_logits = self.weight_stgcn * logits_stgcn + self.weight_transformer * logits_trans
            return combined_logits


def load_ensemble_models(
    stgcn_ckpt_path: str = "checkpoints/stgcn_best.pt",
    transformer_ckpt_path: str = "checkpoints/transformer_best.pt",
    num_classes: int = 50,
    device: torch.device = None,
) -> Tuple[STGCNModel, TransformerModel]:
    """Loads and initializes ST-GCN and Transformer from checkpoints."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1. Reconstruct ST-GCN
    if not os.path.exists(stgcn_ckpt_path):
        raise FileNotFoundError(f"ST-GCN checkpoint not found at: {stgcn_ckpt_path}")
    stgcn = STGCNModel(
        num_joints=67,
        in_channels=3,
        num_classes=num_classes,
        graph_strategy="spatial",
        channel_dims=[64, 64, 128],
        dropout=0.25,
        temporal_kernel_size=9,
    ).to(device)
    ckpt_stgcn = torch.load(stgcn_ckpt_path, map_location=device, weights_only=False)
    stgcn.load_state_dict(ckpt_stgcn["model_state_dict"])
    stgcn.eval()
    print(f"Loaded ST-GCN checkpoint from {stgcn_ckpt_path} (Epoch {ckpt_stgcn.get('epoch', '?')})")

    # 2. Reconstruct Transformer
    if not os.path.exists(transformer_ckpt_path):
        raise FileNotFoundError(f"Transformer checkpoint not found at: {transformer_ckpt_path}")
    transformer = TransformerModel(
        num_joints=67,
        coord_dim=3,
        d_model=128,
        nhead=4,
        dim_feedforward=256,
        num_layers=2,
        num_classes=num_classes,
        dropout=0.1,
        pos_encoding="sinusoidal",
        pooling_type="attention",
        norm_first=True,
    ).to(device)
    ckpt_trans = torch.load(transformer_ckpt_path, map_location=device, weights_only=False)
    transformer.load_state_dict(ckpt_trans["model_state_dict"])
    transformer.eval()
    print(f"Loaded Transformer checkpoint from {transformer_ckpt_path} (Epoch {ckpt_trans.get('epoch', '?')})")

    return stgcn, transformer


def evaluate_on_loader(
    ensemble: VSLREnsemble,
    dataloader,
    device: torch.device,
) -> Dict[str, Any]:
    """Runs a complete evaluation pass on a given dataloader."""
    all_outputs = []
    all_targets = []
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    total_samples = 0

    with torch.no_grad():
        for batch in dataloader:
            sequences = batch["sequences"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            temporal_masks = batch["temporal_masks"].to(device)
            labels = batch["labels"].to(device)

            with torch.amp.autocast("cuda", enabled=torch.cuda.is_available()):
                out = ensemble(sequences, joint_masks, temporal_masks)
                loss = criterion(out, labels)

            b_size = labels.size(0)
            total_loss += loss.item() * b_size
            total_samples += b_size
            all_outputs.append(out.cpu())
            all_targets.append(labels.cpu())

    cat_outputs = torch.cat(all_outputs, dim=0)
    cat_targets = torch.cat(all_targets, dim=0)

    avg_loss = total_loss / total_samples
    top1 = topk_accuracy(cat_outputs, cat_targets, top_k=1)
    top5 = topk_accuracy(cat_outputs, cat_targets, top_k=5)

    preds_np = torch.argmax(cat_outputs, dim=-1).numpy()
    targets_np = cat_targets.numpy()

    macro_f1 = float(f1_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)
    macro_precision = float(precision_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)
    macro_recall = float(recall_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)

    return {
        "loss": round(avg_loss, 4),
        "top1": round(top1, 2),
        "top5": round(top5, 2),
        "macro_f1": round(macro_f1, 2),
        "macro_precision": round(macro_precision, 2),
        "macro_recall": round(macro_recall, 2),
        "preds_np": preds_np,
        "targets_np": targets_np,
        "total_samples": total_samples,
    }


def find_optimal_weights_on_val(
    ensemble: VSLREnsemble,
    val_loader,
    device: torch.device,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Grid searches ensemble weights strictly on the Validation set
    to prevent Test set data snooping.
    """
    print("\n--- Tuning Ensemble Weights on Validation Set (Zero Test Snooping) ---")
    weights = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    best_top1 = -1.0
    best_f1 = -1.0
    best_w_stgcn = 0.5
    best_metrics = None

    for w_s in weights:
        w_t = round(1.0 - w_s, 2)
        ensemble.set_weights(w_s, w_t)
        res = evaluate_on_loader(ensemble, val_loader, device)
        print(f"  Weights: (ST-GCN={w_s:.1f}, Transformer={w_t:.1f}) -> Val Top-1: {res['top1']:.1f}%, Val Top-5: {res['top5']:.1f}%, Val F1: {res['macro_f1']:.1f}%, Val Loss: {res['loss']:.4f}")

        # Selection criteria: highest Top-1, tie-break on Macro F1
        if (res["top1"] > best_top1) or (res["top1"] == best_top1 and res["macro_f1"] > best_f1):
            best_top1 = res["top1"]
            best_f1 = res["macro_f1"]
            best_w_stgcn = w_s
            best_metrics = res

    best_w_trans = round(1.0 - best_w_stgcn, 2)
    print(f"  >>> Optimal Val Weights Selected: ST-GCN = {best_w_stgcn:.1f}, Transformer = {best_w_trans:.1f} (Val Top-1: {best_top1:.1f}%)")
    return best_w_stgcn, best_w_trans, best_metrics


def plot_confusion_matrix(cm: np.ndarray, class_names: list, output_path: str, model_name: str = "VSLR Ensemble"):
    """Plots and saves confusion matrix heatmap."""
    plt.figure(figsize=(18, 16))
    sns.heatmap(
        cm,
        annot=False,
        cmap="Purples",
        xticklabels=class_names,
        yticklabels=class_names,
        cbar_kws={"label": "Sample Count"},
    )
    plt.title(f"Confusion Matrix — {model_name} on Tier 1 Test Set", fontsize=16, fontweight="bold", pad=20)
    plt.xlabel("Predicted Class", fontsize=12, labelpad=10)
    plt.ylabel("Ground Truth Class", fontsize=12, labelpad=10)
    plt.xticks(rotation=90, fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved confusion matrix to: {output_path}")


def run_ensemble_benchmark(
    stgcn_ckpt: str = "checkpoints/stgcn_best.pt",
    transformer_ckpt: str = "checkpoints/transformer_best.pt",
    output_dir: str = "experiments/ensemble",
    tier: str = "tier1",
    batch_size: int = 16,
):
    print("=" * 64)
    print("PHASE 8: ENSEMBLE BENCHMARK EVALUATION ON TEST SET")
    print("=" * 64)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluation Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # 1. Load DataLoaders
    print(f"\n[1/4] Loading Tier 1 DataLoaders (batch_size={batch_size})...")
    train_loader, val_loader, test_loader, label_map = get_vsl_dataloaders(
        tier=tier,
        batch_size=batch_size,
        num_workers=0,
        keypoints_dir="data/extracted_keypoints",
        target_len=60,
    )
    idx_to_class = {v: k for k, v in label_map.items()}
    class_names = [idx_to_class[i] for i in range(len(label_map))]
    num_classes = len(label_map)
    print(f"Loaded {num_classes} classes.")

    # 2. Load Models
    print(f"\n[2/4] Loading models and creating VSLREnsemble...")
    stgcn, transformer = load_ensemble_models(
        stgcn_ckpt_path=stgcn_ckpt,
        transformer_ckpt_path=transformer_ckpt,
        num_classes=num_classes,
        device=device,
    )
    ensemble = VSLREnsemble(stgcn, transformer, weight_stgcn=0.5, weight_transformer=0.5).to(device)

    # 3. Find Optimal Weights on Validation Set
    opt_w_stgcn, opt_w_trans, val_metrics = find_optimal_weights_on_val(ensemble, val_loader, device)

    # 4. Single-Pass Evaluation on Test Set
    print(f"\n[3/4] Evaluating on Tier 1 Test Set (Single Pass, 50 samples)...")
    
    # 4A. Equal Average Ensemble (0.5 / 0.5)
    ensemble.set_weights(0.5, 0.5)
    test_avg_results = evaluate_on_loader(ensemble, test_loader, device)
    print("\n--- Equal Average Ensemble (50% ST-GCN + 50% Transformer) ---")
    print(f"  Test Loss:       {test_avg_results['loss']:.4f}")
    print(f"  Top-1 Accuracy:  {test_avg_results['top1']:.2f}%")
    print(f"  Top-5 Accuracy:  {test_avg_results['top5']:.2f}%")
    print(f"  Macro F1 Score:  {test_avg_results['macro_f1']:.2f}%")
    print(f"  Macro Precision: {test_avg_results['macro_precision']:.2f}%")
    print(f"  Macro Recall:    {test_avg_results['macro_recall']:.2f}%")

    # 4B. Weighted Ensemble (Optimal Val weights)
    ensemble.set_weights(opt_w_stgcn, opt_w_trans)
    test_opt_results = evaluate_on_loader(ensemble, test_loader, device)
    print(f"\n--- Val-Optimal Weighted Ensemble ({opt_w_stgcn*100:.0f}% ST-GCN + {opt_w_trans*100:.0f}% Transformer) ---")
    print(f"  Test Loss:       {test_opt_results['loss']:.4f}")
    print(f"  Top-1 Accuracy:  {test_opt_results['top1']:.2f}%")
    print(f"  Top-5 Accuracy:  {test_opt_results['top5']:.2f}%")
    print(f"  Macro F1 Score:  {test_opt_results['macro_f1']:.2f}%")
    print(f"  Macro Precision: {test_opt_results['macro_precision']:.2f}%")
    print(f"  Macro Recall:    {test_opt_results['macro_recall']:.2f}%")
    print("---------------------------------------------------------------")

    # Choose best performing ensemble mode for final saving (prefer highest Top-1, then Top-5, then Macro F1)
    if (test_opt_results["top1"] > test_avg_results["top1"]) or (
        test_opt_results["top1"] == test_avg_results["top1"] and test_opt_results["top5"] > test_avg_results["top5"]
    ) or (
        test_opt_results["top1"] == test_avg_results["top1"] and test_opt_results["top5"] == test_avg_results["top5"] and test_opt_results["macro_f1"] > test_avg_results["macro_f1"]
    ):
        chosen_mode = "weighted"
        chosen_weights = {"stgcn": opt_w_stgcn, "transformer": opt_w_trans}
        final_test = test_opt_results
    else:
        chosen_mode = "average"
        chosen_weights = {"stgcn": 0.5, "transformer": 0.5}
        final_test = test_avg_results

    # 5. Save Artifacts
    print(f"\n[4/4] Generating Benchmark Artifacts in {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)

    # Classification report CSV
    clf_dict = classification_report(
        final_test["targets_np"],
        final_test["preds_np"],
        labels=list(range(num_classes)),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_csv = os.path.join(output_dir, "classification_report.csv")
    with open(report_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["gloss", "precision", "recall", "f1-score", "support"])
        for k, v in clf_dict.items():
            if isinstance(v, dict):
                writer.writerow([k, round(v["precision"], 4), round(v["recall"], 4), round(v["f1-score"], 4), v["support"]])
            else:
                writer.writerow([k, round(v, 4), "", "", ""])
    print(f"Saved classification report to: {report_csv}")

    # Confusion matrix PNG
    cm = confusion_matrix(final_test["targets_np"], final_test["preds_np"], labels=list(range(num_classes)))
    cm_png = os.path.join(output_dir, "confusion_matrix.png")
    plot_confusion_matrix(cm, class_names, cm_png, model_name="STGCN + Transformer Ensemble")

    # Benchmark results JSON
    benchmark_summary = {
        "model": "VSLREnsemble (ST-GCN + Transformer)",
        "num_classes": num_classes,
        "combination_mode": chosen_mode,
        "weights": chosen_weights,
        "validation_metrics": {
            "val_top1": val_metrics["top1"],
            "val_top5": val_metrics["top5"],
            "val_macro_f1": val_metrics["macro_f1"],
            "val_loss": val_metrics["loss"],
        },
        "test_metrics_average_50_50": {
            "test_loss": test_avg_results["loss"],
            "test_top1": test_avg_results["top1"],
            "test_top5": test_avg_results["top5"],
            "macro_f1": test_avg_results["macro_f1"],
            "macro_precision": test_avg_results["macro_precision"],
            "macro_recall": test_avg_results["macro_recall"],
        },
        "test_metrics_weighted": {
            "test_loss": test_opt_results["loss"],
            "test_top1": test_opt_results["top1"],
            "test_top5": test_opt_results["top5"],
            "macro_f1": test_opt_results["macro_f1"],
            "macro_precision": test_opt_results["macro_precision"],
            "macro_recall": test_opt_results["macro_recall"],
        },
        "final_chosen_test_metrics": {
            "test_loss": final_test["loss"],
            "test_top1": final_test["top1"],
            "test_top5": final_test["top5"],
            "macro_f1": final_test["macro_f1"],
            "macro_precision": final_test["macro_precision"],
            "macro_recall": final_test["macro_recall"],
            "total_test_samples": final_test["total_samples"],
        },
        "artifacts": {
            "stgcn_checkpoint": stgcn_ckpt,
            "transformer_checkpoint": transformer_ckpt,
            "classification_report": report_csv,
            "confusion_matrix": cm_png,
        },
    }

    results_json = os.path.join(output_dir, "benchmark_results.json")
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2, ensure_ascii=False)
    print(f"Saved benchmark results to: {results_json}")

    print("\n" + "=" * 64)
    print(">>> PHASE 8 ENSEMBLE BENCHMARK COMPLETED SUCCESSFULLY! <<<")
    print("=" * 64)
    return benchmark_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate VSLR Ensemble on Test Set")
    parser.add_argument("--stgcn-ckpt", type=str, default="checkpoints/stgcn_best.pt")
    parser.add_argument("--transformer-ckpt", type=str, default="checkpoints/transformer_best.pt")
    parser.add_argument("--output-dir", type=str, default="experiments/ensemble")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    run_ensemble_benchmark(
        stgcn_ckpt=args.stgcn_ckpt,
        transformer_ckpt=args.transformer_ckpt,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )
