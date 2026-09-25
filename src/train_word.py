"""
Training Script for Word-Level Isolated VSL Recognition (Level 2).
Trains BiGRU or Transformer model on 60-frame x 201-dim MediaPipe Holistic landmark sequences.
Dataset source: `data (2)/Processed`.
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict

from src.data.dataset import create_word_dataloaders, get_top_classes
from src.models.gru_classifier import BiGRUSequenceClassifier
from src.models.transformer_classifier import VSLTransformerClassifier


def compute_top_k_accuracy(outputs: torch.Tensor, targets: torch.Tensor, k: int = 5) -> float:
    """Computes Top-K Accuracy."""
    with torch.no_grad():
        batch_size = targets.size(0)
        actual_k = min(k, outputs.size(1))
        _, pred = outputs.topk(actual_k, 1, True, True)
        pred = pred.t()
        correct = pred.eq(targets.view(1, -1).expand_as(pred))
        correct_k = correct[:actual_k].reshape(-1).float().sum(0, keepdim=True)
        return (correct_k.item() / batch_size)


def train_word_model(
    model_type: str = "bigru",
    top_k_classes: int = 40,
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 1e-3,
    processed_dir: str = "data/Processed",
    save_path: str = None,
):
    os.makedirs("experiments", exist_ok=True)
    if save_path is None:
        save_path = f"experiments/word_model_{model_type}.pth"

    print(f"===========================================================")
    print(f"Starting VSL Word-Level SLR Training | Model: {model_type.upper()}")
    print(f"Selecting Top {top_k_classes} most frequent VSL glosses...")
    print(f"===========================================================")

    train_loader, val_loader, test_loader, idx_to_class = create_word_dataloaders(
        processed_dir=processed_dir,
        top_k=top_k_classes,
        batch_size=batch_size,
    )
    num_classes = len(idx_to_class)
    class_to_idx = {c: i for i, c in idx_to_class.items()}
    print(f"[Info] Training with {num_classes} classes.")
    print(f"  Train batches: {len(train_loader)} | Val batches: {len(val_loader)} | Test batches: {len(test_loader)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Info] Training Device: {device}")

    # Initialize model
    if model_type.lower() == "bigru":
        model = BiGRUSequenceClassifier(
            input_dim=201,
            hidden_dim=128,
            num_layers=2,
            num_classes=num_classes,
            dropout=0.3,
            bidirectional=True,
        ).to(device)
    elif model_type.lower() == "transformer":
        model = VSLTransformerClassifier(
            input_dim=201,
            d_model=128,
            nhead=4,
            num_layers=3,
            dim_feedforward=256,
            num_classes=num_classes,
            dropout=0.2,
        ).to(device)
    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_val_top1 = 0.0
    best_val_top5 = 0.0

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()

            train_loss += loss.item() * len(y)
            pred = out.argmax(dim=1)
            train_correct += (pred == y).sum().item()
            train_total += len(y)

        scheduler.step()
        train_acc = train_correct / train_total

        # Validation
        model.eval()
        val_loss, val_top1_correct, val_total = 0.0, 0, 0
        val_top5_sum = 0.0
        val_batches = 0

        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                out = model(x)
                loss = criterion(out, y)

                val_loss += loss.item() * len(y)
                pred = out.argmax(dim=1)
                val_top1_correct += (pred == y).sum().item()
                val_total += len(y)

                top5 = compute_top_k_accuracy(out, y, k=5)
                val_top5_sum += top5
                val_batches += 1

        val_top1 = val_top1_correct / val_total
        val_top5 = val_top5_sum / max(1, val_batches)

        # Checkpoint if best top-1
        if val_top1 > best_val_top1:
            best_val_top1 = val_top1
            best_val_top5 = val_top5
            torch.save({
                "model_type": model_type,
                "model_state_dict": model.state_dict(),
                "class_to_idx": class_to_idx,
                "idx_to_class": idx_to_class,
                "input_dim": 201,
                "num_classes": num_classes,
                "val_top1": val_top1,
                "val_top5": val_top5,
            }, save_path)

        if epoch % 2 == 0 or epoch == epochs:
            print(
                f"Epoch [{epoch:02d}/{epochs}] "
                f"Train Loss: {train_loss/train_total:.4f} | Train Acc: {train_acc*100:.2f}% | "
                f"Val Top-1: {val_top1*100:.2f}% | Val Top-5: {val_top5*100:.2f}%"
            )

    print(f"\n[Done] Best Val Top-1: {best_val_top1*100:.2f}% | Top-5: {best_val_top5*100:.2f}%")
    print(f"[Info] Checkpoint saved to {save_path}")

    # Test evaluation
    checkpoint = torch.load(save_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    test_top1_correct, test_total = 0, 0
    test_top5_sum, test_batches = 0.0, 0

    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            pred = out.argmax(dim=1)
            test_top1_correct += (pred == y).sum().item()
            test_total += len(y)
            test_top5_sum += compute_top_k_accuracy(out, y, k=5)
            test_batches += 1

    test_top1 = test_top1_correct / max(1, test_total)
    test_top5 = test_top5_sum / max(1, test_batches)

    print(f"\n================ Final Test Set Evaluation ================")
    print(f"Model: {model_type.upper()} on {num_classes} VSL Classes")
    print(f"Test Top-1 Accuracy: {test_top1 * 100:.2f}%")
    print(f"Test Top-5 Accuracy: {test_top5 * 100:.2f}%")
    print(f"===========================================================\n")

    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train VSL Word Recognition Model")
    parser.add_argument("--model", type=str, default="bigru", choices=["bigru", "transformer"])
    parser.add_argument("--top_k", type=int, default=40, help="Number of top classes to train on")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train_word_model(
        model_type=args.model,
        top_k_classes=args.top_k,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
