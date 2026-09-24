"""
Training script for VSL Alphabet (Level 1) - Signer Disjoint.
Supports both Static MLP and Temporal BiGRU models.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset

from src.data.alphabet_dataset import VSLAlphabetDataset, get_alphabet_dataloaders
from src.models.alphabet_mlp import VSLAlphabetMLP
from src.models.alphabet_temporal import VSLAlphabetBiGRU, VSLAlphabet1DCNN


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: str,
) -> Tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for batch in loader:
        features = batch["features"].to(device)
        labels = batch["label"].to(device)

        optimizer.zero_grad()
        logits = model(features)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * features.size(0)
        preds = torch.argmax(logits, dim=-1)
        correct += (preds == labels).sum().item()
        total += features.size(0)

    avg_loss = total_loss / max(total, 1)
    acc = correct / max(total, 1)
    return avg_loss, acc


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: str,
) -> Tuple[float, float, float]:
    model.eval()
    total_loss = 0.0
    top1_correct = 0
    top3_correct = 0
    total = 0

    for batch in loader:
        features = batch["features"].to(device)
        labels = batch["label"].to(device)

        logits = model(features)
        loss = criterion(logits, labels)

        total_loss += loss.item() * features.size(0)
        # Top-1
        preds = torch.argmax(logits, dim=-1)
        top1_correct += (preds == labels).sum().item()

        # Top-3
        _, top3_preds = torch.topk(logits, k=min(3, logits.size(-1)), dim=-1)
        for i in range(labels.size(0)):
            if labels[i] in top3_preds[i]:
                top3_correct += 1

        total += features.size(0)

    avg_loss = total_loss / max(total, 1)
    top1_acc = top1_correct / max(total, 1)
    top3_acc = top3_correct / max(total, 1)
    return avg_loss, top1_acc, top3_acc


def run_training(
    model_type: str = "mlp",
    epochs: int = 40,
    batch_size: int = 32,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    device_name: str = "auto",
    splits_dir: str = "data/vsl_alphabet_pilot/splits",
    save_path: str = "checkpoints/alphabet_best.pt",
    smoke_test_samples: Optional[int] = None,
) -> Dict[str, Any]:
    if device_name == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_name

    print(f"\n==================================================")
    print(f"Starting VSL Alphabet Training ({model_type.upper()})")
    print(f"Device: {device} | Epochs: {epochs} | Batch: {batch_size}")
    print(f"==================================================")

    data_mode = "sequence" if model_type in ("bigru", "cnn1d") else "static"
    train_loader, val_loader, test_loader, classes = get_alphabet_dataloaders(
        splits_dir=splits_dir,
        data_mode=data_mode,
        batch_size=batch_size,
    )

    if smoke_test_samples is not None:
        print(f"[SMOKE TEST MODE] Restricting datasets to {smoke_test_samples} samples.")
        train_loader = DataLoader(
            Subset(train_loader.dataset, range(min(smoke_test_samples, len(train_loader.dataset)))),
            batch_size=batch_size, shuffle=True
        )
        val_loader = DataLoader(
            Subset(val_loader.dataset, range(min(smoke_test_samples, len(val_loader.dataset)))),
            batch_size=batch_size, shuffle=False
        )
        test_loader = DataLoader(
            Subset(test_loader.dataset, range(min(smoke_test_samples, len(test_loader.dataset)))),
            batch_size=batch_size, shuffle=False
        )

    num_classes = len(classes)
    if model_type == "mlp":
        model = VSLAlphabetMLP(input_dim=63, num_classes=num_classes)
    elif model_type == "bigru":
        model = VSLAlphabetBiGRU(input_dim=63, hidden_dim=64, num_classes=num_classes)
    elif model_type == "cnn1d":
        model = VSLAlphabet1DCNN(input_dim=63, num_classes=num_classes)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    model.to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    best_val_acc = 0.0
    best_epoch = 0
    history = []

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_top1, val_top3 = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        record = {
            "epoch": epoch,
            "train_loss": round(tr_loss, 4),
            "train_acc": round(tr_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_top1": round(val_top1, 4),
            "val_top3": round(val_top3, 4),
            "elapsed_s": round(elapsed, 2),
        }
        history.append(record)

        if epoch % 5 == 0 or epoch == epochs or smoke_test_samples is not None:
            print(f"Epoch {epoch:2d}/{epochs:2d} [{elapsed:.1f}s] - Train Loss: {tr_loss:.4f} Acc: {tr_acc*100:.1f}% | Val Loss: {val_loss:.4f} Top1: {val_top1*100:.1f}% Top3: {val_top3*100:.1f}%")

        if val_top1 > best_val_acc and smoke_test_samples is None:
            best_val_acc = val_top1
            best_epoch = epoch
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            torch.save({
                "model_type": model_type,
                "num_classes": num_classes,
                "classes": classes,
                "state_dict": model.state_dict(),
                "best_val_acc": best_val_acc,
                "epoch": best_epoch,
                "input_dim": 63,
                "normalization": "palm_scale_wrist_centered",
            }, save_path)

    # Evaluate on Test set
    test_loss, test_top1, test_top3 = evaluate(model, test_loader, criterion, device)
    print(f"\n--- Final Test Evaluation (Signers S03, S14, S15 - Disjoint) ---")
    print(f"Test Top-1 Accuracy: {test_top1*100:.2f}% | Top-3 Accuracy: {test_top3*100:.2f}% (Loss: {test_loss:.4f})")

    return {
        "model_type": model_type,
        "best_epoch": best_epoch,
        "best_val_acc": best_val_acc,
        "test_top1": test_top1,
        "test_top3": test_top3,
        "history": history,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["mlp", "bigru", "cnn1d"], default="mlp")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--smoke-test", action="store_true", help="Run quick 2-epoch test on 30 samples")
    args = parser.parse_args()

    if args.smoke_test:
        run_training(model_type=args.model, epochs=2, batch_size=16, smoke_test_samples=30)
    else:
        run_training(model_type=args.model, epochs=args.epochs, batch_size=args.batch_size)
