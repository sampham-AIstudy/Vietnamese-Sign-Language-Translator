"""
Evaluation and Benchmarking Script for VSLR Baseline Model on Test Set.
- Loads best checkpoint from training (selected strictly on validation set).
- Evaluates exclusively on Tier 1 Test Set (100% video-disjoint cross-dialect evaluation).
- Calculates:
  + Top-1 Accuracy
  + Top-5 Accuracy
  + Macro F1, Precision, Recall
  + Per-Class Classification Report (saved as CSV)
  + Confusion Matrix (saved as high-res PNG)
  + Training Curves from history.json (saved as PNG)
  + Final Benchmark Summary (saved as JSON)
"""

import os
import sys
import json
import csv
import yaml
import argparse
import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.baseline_bigru import BaselineBiGRU
from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.data.vsl_dataset import get_vsl_dataloaders
from src.metrics.metrics import topk_accuracy


def plot_training_curves(history_path: str, output_path: str):
    """Plots Loss and Top-1 Accuracy curves across epochs."""
    if not os.path.exists(history_path):
        print(f"Warning: History file {history_path} not found. Skipping curve plotting.")
        return

    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    epochs = [h["epoch"] for h in history]
    train_loss = [h["train_loss"] for h in history]
    val_loss = [h["val_loss"] for h in history]
    train_top1 = [h["train_top1"] for h in history]
    val_top1 = [h["val_top1"] for h in history]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Loss Curve
    axes[0].plot(epochs, train_loss, label="Train Loss", color="#1f77b4", linewidth=2)
    axes[0].plot(epochs, val_loss, label="Val Loss", color="#ff7f0e", linewidth=2)
    axes[0].set_title("Training & Validation Loss", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Epoch", fontsize=12)
    axes[0].set_ylabel("CrossEntropy Loss", fontsize=12)
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(fontsize=11)

    # Top-1 Accuracy Curve
    axes[1].plot(epochs, train_top1, label="Train Top-1", color="#2ca02c", linewidth=2)
    axes[1].plot(epochs, val_top1, label="Val Top-1", color="#d62728", linewidth=2)
    axes[1].set_title("Training & Validation Top-1 Accuracy (%)", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Epoch", fontsize=12)
    axes[1].set_ylabel("Accuracy (%)", fontsize=12)
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(fontsize=11)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved training curves to: {output_path}")


def plot_confusion_matrix(cm: np.ndarray, class_names: list, output_path: str, model_name: str = "Baseline BiGRU"):
    """Plots and saves confusion matrix heatmap."""
    plt.figure(figsize=(18, 16))
    sns.heatmap(
        cm,
        annot=False,
        cmap="Blues",
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


def build_model(model_cfg: dict, num_classes: int):
    """Builds model instance from configuration dict."""
    model_name = model_cfg.get("name", "BaselineBiGRU")
    if model_name == "TransformerModel":
        return TransformerModel(
            num_joints=model_cfg.get("num_joints", 67),
            coord_dim=model_cfg.get("coord_dim", 3),
            d_model=model_cfg.get("d_model", 128),
            nhead=model_cfg.get("nhead", 4),
            dim_feedforward=model_cfg.get("dim_feedforward", 256),
            num_layers=model_cfg.get("num_layers", 2),
            num_classes=num_classes,
            dropout=model_cfg.get("dropout", 0.1),
            pos_encoding=model_cfg.get("pos_encoding", "sinusoidal"),
            pooling_type=model_cfg.get("pooling_type", "attention"),
            norm_first=model_cfg.get("norm_first", True),
        )
    elif model_name == "STGCNModel":
        return STGCNModel(
            num_joints=model_cfg.get("num_joints", 67),
            in_channels=model_cfg.get("in_channels", 3),
            num_classes=num_classes,
            graph_strategy=model_cfg.get("graph_strategy", "spatial"),
            channel_dims=model_cfg.get("channel_dims", [64, 64, 128]),
            dropout=model_cfg.get("dropout", 0.25),
            temporal_kernel_size=model_cfg.get("temporal_kernel_size", 9),
        )
    else:
        return BaselineBiGRU(
            num_joints=model_cfg.get("num_joints", 67),
            coord_dim=model_cfg.get("coord_dim", 3),
            hidden_dim=model_cfg.get("hidden_dim", 128),
            num_layers=model_cfg.get("num_layers", 2),
            num_classes=num_classes,
            dropout=model_cfg.get("dropout", 0.3),
            bidirectional=model_cfg.get("bidirectional", True),
            pooling_type=model_cfg.get("pooling_type", "attention"),
        )


def evaluate_model(
    config_path: str = "configs/experiments/baseline_bigru.yaml",
    checkpoint_path: str = None,
    history_path: str = None,
    output_dir: str = None,
    tier: str = None,
    batch_size: int = None,
):
    print("=" * 64)
    print("BENCHMARK EVALUATION ON TEST SET")
    print("=" * 64)

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    model_cfg = config.get("model", {"name": "BaselineBiGRU"})
    data_cfg = config.get("data", {})
    out_cfg = config.get("output", {})

    tier = tier or data_cfg.get("tier", "tier1")
    batch_size = batch_size or config.get("training", {}).get("batch_size", 16)
    checkpoint_path = checkpoint_path or out_cfg.get("checkpoint_file", "checkpoints/baseline_bigru.pt")
    history_path = history_path or out_cfg.get("history_file", "experiments/baseline/history.json")
    output_dir = output_dir or out_cfg.get("experiment_dir", "experiments/baseline")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Model Name:        {model_cfg.get('name')}")
    print(f"Config:            {config_path}")
    print(f"Checkpoint:        {checkpoint_path}")
    print(f"Output Directory:  {output_dir}")
    print(f"Evaluation Device: {device}")

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    # 1. Load DataLoaders
    print(f"\n[1/4] Loading {tier} DataLoaders...")
    train_loader, val_loader, test_loader, label_map = get_vsl_dataloaders(
        tier=tier,
        batch_size=batch_size,
        num_workers=0,
        keypoints_dir=data_cfg.get("keypoints_dir", "data/extracted_keypoints"),
        target_len=data_cfg.get("sequence_length", 60),
    )
    idx_to_class = {v: k for k, v in label_map.items()}
    class_names = [idx_to_class[i] for i in range(len(label_map))]
    num_classes = len(label_map)

    # 2. Reconstruct Model and Load Checkpoint
    print(f"\n[2/4] Loading Best Checkpoint from {checkpoint_path}...")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    
    model = build_model(model_cfg, num_classes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    best_epoch = checkpoint.get("epoch", "unknown")
    best_val_top1 = checkpoint.get("val_top1", 0.0)
    best_val_loss = checkpoint.get("val_loss", 0.0)
    print(f"Loaded model from Epoch {best_epoch} (Best Val Top-1: {best_val_top1:.2f}%, Val Loss: {best_val_loss:.4f})")

    # 3. Evaluate on Test Set
    print(f"\n[3/4] Evaluating on {tier} Test Set ({len(test_loader.dataset)} samples)...")
    all_logits = []
    all_targets = []
    criterion = torch.nn.CrossEntropyLoss()
    total_test_loss = 0.0
    total_test_samples = 0

    with torch.no_grad():
        for batch in test_loader:
            sequences = batch["sequences"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            temporal_masks = batch["temporal_masks"].to(device)
            labels = batch["labels"].to(device)

            with torch.amp.autocast("cuda", enabled=torch.cuda.is_available()):
                logits = model(sequences, joint_masks, temporal_masks)
                loss = criterion(logits, labels)

            b_size = labels.size(0)
            total_test_loss += loss.item() * b_size
            total_test_samples += b_size
            all_logits.append(logits.cpu())
            all_targets.append(labels.cpu())

    cat_logits = torch.cat(all_logits, dim=0)
    cat_targets = torch.cat(all_targets, dim=0)

    test_loss = total_test_loss / total_test_samples
    test_top1 = topk_accuracy(cat_logits, cat_targets, top_k=1)
    test_top5 = topk_accuracy(cat_logits, cat_targets, top_k=5)

    preds_np = torch.argmax(cat_logits, dim=-1).numpy()
    targets_np = cat_targets.numpy()

    macro_f1 = float(f1_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)
    macro_precision = float(precision_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)
    macro_recall = float(recall_score(targets_np, preds_np, average="macro", zero_division=0) * 100.0)

    print("\n--- FINAL TEST SET BENCHMARK RESULTS ---")
    print(f"  Model:               {model_cfg.get('name')}")
    print(f"  Test Loss:           {test_loss:.4f}")
    print(f"  Top-1 Accuracy:      {test_top1:.2f}%")
    print(f"  Top-5 Accuracy:      {test_top5:.2f}%")
    print(f"  Macro F1 Score:      {macro_f1:.2f}%")
    print(f"  Macro Precision:     {macro_precision:.2f}%")
    print(f"  Macro Recall:        {macro_recall:.2f}%")
    print("----------------------------------------")

    # 4. Save Artifacts
    print(f"\n[4/4] Generating Reports and Visualizations in {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)

    # A. Classification Report CSV
    clf_dict = classification_report(
        targets_np,
        preds_np,
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

    # B. Confusion Matrix PNG
    cm = confusion_matrix(targets_np, preds_np, labels=list(range(num_classes)))
    cm_png = os.path.join(output_dir, "confusion_matrix.png")
    plot_confusion_matrix(cm, class_names, cm_png, model_name=model_cfg.get("name", "BaselineBiGRU"))

    # C. Training Curves PNG
    curves_png = os.path.join(output_dir, "training_curve.png")
    plot_training_curves(history_path, curves_png)

    # D. Final Benchmark Results JSON
    results_summary = {
        "model": model_cfg.get("name", "BaselineBiGRU"),
        "num_classes": num_classes,
        "best_epoch": int(best_epoch),
        "validation_metrics": {
            "val_loss": round(float(best_val_loss), 4),
            "val_top1": round(float(best_val_top1), 2),
        },
        "test_metrics": {
            "test_loss": round(float(test_loss), 4),
            "test_top1": round(float(test_top1), 2),
            "test_top5": round(float(test_top5), 2),
            "macro_f1": round(float(macro_f1), 2),
            "macro_precision": round(float(macro_precision), 2),
            "macro_recall": round(float(macro_recall), 2),
            "total_test_samples": total_test_samples,
        },
        "artifacts": {
            "checkpoint": checkpoint_path,
            "classification_report": report_csv,
            "confusion_matrix": cm_png,
            "training_curve": curves_png,
        },
    }
    results_json = os.path.join(output_dir, "benchmark_results.json")
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    print(f"Saved benchmark results to: {results_json}")

    print("\n" + "=" * 64)
    print("BENCHMARK EVALUATION COMPLETE.")
    print("=" * 64)
    return results_summary


def evaluate_baseline(**kwargs):
    """Backward compatibility wrapper."""
    return evaluate_model(config_path="configs/experiments/baseline_bigru.yaml", **kwargs)


def main():
    parser = argparse.ArgumentParser(description="Evaluate VSLR Model on Test Set")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/experiments/baseline_bigru.yaml",
        help="Path to YAML experiment configuration file",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Path to model checkpoint (overrides config)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Path to output directory (overrides config)",
    )
    args = parser.parse_args()
    evaluate_model(
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
