"""
Training Script for Fingerspelling / Alphabet Model (Level 1).
Extracts or loads 42-dim MediaPipe hand landmarks from `data/asl_alphabet_train`.
Trains `AlphabetMLP`, validates performance, and saves checkpoint to `experiments/alphabet_model.pth`.
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import glob
import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Tuple, Dict
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import classification_report, accuracy_score

from src.models.alphabet_classifier import AlphabetMLP
from src.data.dataset import AlphabetLandmarkDataset
from src.data.extract_landmarks import HandLandmarkExtractor


def extract_or_load_dataset(
    dataset_csv_path: str = "data/alphabet_landmarks_full.csv",
    train_img_dir: str = "data/asl_alphabet_train",
    samples_per_class: int = 80,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """
    Loads pre-extracted 42-dim hand landmarks CSV or extracts them from image folders.
    """
    if os.path.isfile(dataset_csv_path):
        print(f"[Info] Loading cached alphabet landmarks from {dataset_csv_path}...")
        df = pd.read_csv(dataset_csv_path)
        labels_str = df["label"].values
        features = df.drop(columns=["label"]).values.astype(np.float32)

        unique_classes = sorted(list(set(labels_str)))
        class_to_idx = {c: i for i, c in enumerate(unique_classes)}
        labels = np.array([class_to_idx[c] for c in labels_str], dtype=np.int64)
        return features, labels, class_to_idx

    print(f"[Info] Extracting landmarks from {train_img_dir} ({samples_per_class} samples/class)...")
    extractor = HandLandmarkExtractor(max_num_hands=1)
    features_list = []
    labels_list = []

    class_names = sorted(os.listdir(train_img_dir))
    class_names = [d for d in class_names if os.path.isdir(os.path.join(train_img_dir, d))]

    for cls_name in class_names:
        cls_folder = os.path.join(train_img_dir, cls_name)
        img_files = glob.glob(os.path.join(cls_folder, "*.jpg")) + glob.glob(os.path.join(cls_folder, "*.png"))
        img_files = img_files[:samples_per_class]

        valid_count = 0
        for img_path in img_files:
            img = cv2.imread(img_path)
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            norm_landmarks, _ = extractor.extract_hand_landmarks(img_rgb)
            if norm_landmarks is not None:
                features_list.append(norm_landmarks)
                labels_list.append(cls_name)
                valid_count += 1

        print(f"  Class {cls_name:8s}: {valid_count} valid hand landmarks extracted")

    extractor.close()

    features = np.array(features_list, dtype=np.float32)
    unique_classes = sorted(list(set(labels_list)))
    class_to_idx = {c: i for i, c in enumerate(unique_classes)}
    labels = np.array([class_to_idx[c] for c in labels_list], dtype=np.int64)

    # Save to CSV for future fast runs
    df_save = pd.DataFrame(features)
    df_save["label"] = labels_list
    os.makedirs(os.path.dirname(dataset_csv_path) or ".", exist_ok=True)
    df_save.to_csv(dataset_csv_path, index=False)
    print(f"[Info] Saved {len(df_save)} samples to {dataset_csv_path}")

    return features, labels, class_to_idx


def train_alphabet_model(
    epochs: int = 35,
    batch_size: int = 32,
    lr: float = 1e-3,
    save_path: str = "experiments/alphabet_model.pth",
):
    os.makedirs("experiments", exist_ok=True)
    features, labels, class_to_idx = extract_or_load_dataset()
    num_classes = len(class_to_idx)
    print(f"[Info] Dataset: {len(features)} samples across {num_classes} classes.")

    dataset = AlphabetLandmarkDataset(features, labels, class_to_idx, augment=True)
    val_size = int(len(dataset) * 0.15)
    test_size = int(len(dataset) * 0.15)
    train_size = len(dataset) - val_size - test_size

    generator = torch.Generator().manual_seed(42)
    train_ds, val_ds, test_ds = random_split(dataset, [train_size, val_size, test_size], generator=generator)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Info] Training on device: {device}")

    model = AlphabetMLP(input_dim=42, num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)

    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(y)
            pred = out.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += len(y)

        train_acc = correct / total

        # Validation
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                out = model(x)
                pred = out.argmax(dim=1)
                val_correct += (pred == y).sum().item()
                val_total += len(y)

        val_acc = val_correct / val_total
        scheduler.step(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "model_state_dict": model.state_dict(),
                "class_to_idx": class_to_idx,
                "input_dim": 42,
                "num_classes": num_classes,
                "val_acc": val_acc
            }, save_path)

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs}] Loss: {total_loss/total:.4f} | Train Acc: {train_acc*100:.2f}% | Val Acc: {val_acc*100:.2f}%")

    print(f"[Done] Best Val Accuracy: {best_val_acc*100:.2f}%. Model saved to {save_path}")

    # Evaluate on test set
    checkpoint = torch.load(save_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for x, y in test_loader:
            x = x.to(device)
            out = model(x)
            preds = out.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(y.numpy())

    test_acc = accuracy_score(all_targets, all_preds)
    print(f"\n================ Test Results (Fingerspelling) ================")
    print(f"Test Accuracy: {test_acc * 100:.2f}%")
    target_names = [k for k, v in sorted(class_to_idx.items(), key=lambda item: item[1])]
    print(classification_report(all_targets, all_preds, target_names=target_names, zero_division=0))


if __name__ == "__main__":
    train_alphabet_model()
