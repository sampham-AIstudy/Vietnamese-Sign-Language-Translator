"""
Evaluation Module for VSL Models (Alphabet and Word-Level).
Computes:
- Top-1 and Top-5 Accuracy
- Classification Report (Precision, Recall, F1-score)
- Confusion Matrix visualization saved to `experiments/`
- Analysis of most frequently confused pairs of signs
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from typing import Dict, List, Tuple

from src.models.gru_classifier import BiGRUSequenceClassifier
from src.models.transformer_classifier import VSLTransformerClassifier
from src.data.dataset import VSLSequenceDataset
from torch.utils.data import DataLoader


def evaluate_word_model(
    checkpoint_path: str = "experiments/word_model_bigru.pth",
    processed_dir: str = "data/Processed",
    output_img: str = "experiments/confusion_matrix_word.png",
    batch_size: int = 32,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not os.path.isfile(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device)
    model_type = checkpoint.get("model_type", "bigru")
    num_classes = checkpoint["num_classes"]
    idx_to_class = checkpoint["idx_to_class"]
    selected_classes = [idx_to_class[i] for i in range(num_classes)]

    if model_type == "bigru":
        model = BiGRUSequenceClassifier(
            input_dim=201,
            hidden_dim=128,
            num_layers=2,
            num_classes=num_classes,
            bidirectional=True,
        )
    else:
        model = VSLTransformerClassifier(
            input_dim=201,
            d_model=128,
            nhead=4,
            num_layers=3,
            num_classes=num_classes,
        )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    test_ds = VSLSequenceDataset(
        split_dir=os.path.join(processed_dir, "test"),
        label_map_path=os.path.join(processed_dir, "label_map.json"),
        selected_classes=selected_classes,
        augment=False,
    )
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    all_preds = []
    all_targets = []
    all_probs = []

    print(f"[Info] Evaluating on {len(test_ds)} test samples...")
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            probs = torch.softmax(out, dim=1)
            preds = out.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(y.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)

    # Calculate Top-1 and Top-5
    top1 = accuracy_score(all_targets, all_preds)
    top5_correct = 0
    for i in range(len(all_targets)):
        top5_indices = np.argsort(all_probs[i])[-5:]
        if all_targets[i] in top5_indices:
            top5_correct += 1
    top5 = top5_correct / len(all_targets)

    print("\n" + "=" * 60)
    print(f"EVALUATION SUMMARY: {model_type.upper()}")
    print("=" * 60)
    print(f"Test Top-1 Accuracy: {top1 * 100:.2f}%")
    print(f"Test Top-5 Accuracy: {top5 * 100:.2f}%")
    print("=" * 60)

    # Classification report
    target_names = [idx_to_class[i] for i in range(num_classes)]
    print("\nDetailed Classification Report:")
    print(classification_report(all_targets, all_preds, target_names=target_names, zero_division=0))

    # Confusion matrix
    cm = confusion_matrix(all_targets, all_preds)

    # Find top confused pairs
    confused_pairs = []
    for i in range(num_classes):
        for j in range(num_classes):
            if i != j and cm[i, j] > 0:
                confused_pairs.append((target_names[i], target_names[j], cm[i, j]))

    confused_pairs.sort(key=lambda x: x[2], reverse=True)
    if confused_pairs:
        print("\nTop Confused Sign Pairs:")
        for true_label, pred_label, count in confused_pairs[:10]:
            print(f"  True: '{true_label}' --> Predicted: '{pred_label}' ({count} times)")

    # Plot confusion matrix
    plt.figure(figsize=(max(12, num_classes // 2), max(10, num_classes // 2)))
    sns.heatmap(
        cm,
        annot=num_classes <= 30,
        fmt="d",
        cmap="Blues",
        xticklabels=target_names,
        yticklabels=target_names,
    )
    plt.title(f"VSL Confusion Matrix ({model_type.upper()}) - Top-1: {top1*100:.1f}%")
    plt.xlabel("Predicted Class")
    plt.ylabel("True Class")
    plt.xticks(rotation=90, fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()
    plt.savefig(output_img, dpi=300)
    plt.close()
    print(f"\n[Info] Confusion matrix plot saved to: {output_img}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, default="experiments/word_model_bigru.pth")
    parser.add_argument("--output", type=str, default="experiments/confusion_matrix_word.png")
    args = parser.parse_args()
    evaluate_word_model(checkpoint_path=args.checkpoint, output_img=args.output)
