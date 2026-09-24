"""
PyTorch Dataset for VSL Alphabet (Level 1) Pilot Dataset.
Supports:
- 'static' mode: extracts representative keyframe / median (63,) features for Static MLP.
- 'sequence' mode: extracts resampled sequence (30, 63) features for 1D-CNN / BiGRU.
- Jitter & scale augmentation for robust training.
"""

import os
import csv
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple, Any

from src.data.alphabet_preprocessing import (
    extract_static_features,
    extract_sequence_features,
    normalize_hand_landmarks,
)


class VSLAlphabetDataset(Dataset):
    def __init__(
        self,
        split_csv: str,
        classes_path: str = "data/vsl_alphabet_pilot/splits/classes.txt",
        data_mode: str = "static",  # 'static' or 'sequence'
        target_seq_len: int = 30,
        augment: bool = False,
        jitter_std: float = 0.005,
        scale_range: Tuple[float, float] = (0.95, 1.05),
    ):
        if not os.path.exists(split_csv):
            raise FileNotFoundError(f"Split CSV not found: {split_csv}")
        if not os.path.exists(classes_path):
            raise FileNotFoundError(f"Classes file not found: {classes_path}")

        self.split_csv = split_csv
        self.data_mode = data_mode
        self.target_seq_len = target_seq_len
        self.augment = augment
        self.jitter_std = jitter_std
        self.scale_range = scale_range

        # Load class map
        with open(classes_path, "r", encoding="utf-8") as f:
            self.classes = [line.strip() for line in f if line.strip()]
        self.class_to_idx = {cls: i for i, cls in enumerate(self.classes)}

        # Load samples
        with open(split_csv, "r", encoding="utf-8") as f:
            self.samples = list(csv.DictReader(f))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        row = self.samples[idx]
        landmark_path = row["landmark_path"]
        hold_start = int(row.get("hold_start_frame", 30))
        hold_end = int(row.get("hold_end_frame", 90))
        symbol = row["symbol"]
        label = self.class_to_idx[symbol]

        # Load .npz
        if not os.path.exists(landmark_path):
            # Try relative path fallback
            alt_path = os.path.join(os.path.dirname(self.split_csv), "..", "..", landmark_path)
            if os.path.exists(alt_path):
                landmark_path = alt_path
            else:
                raise FileNotFoundError(f"Landmark file not found: {landmark_path}")

        data = np.load(landmark_path)
        # Use raw_landmarks (105, 21, 3) through our shared preprocessing
        raw_seq = data["raw_landmarks"]

        if self.data_mode == "static":
            features = extract_static_features(
                raw_seq,
                hold_start=hold_start,
                hold_end=hold_end,
                strategy="median",
            )  # (63,)
            if self.augment:
                # Add slight noise & scaling
                scale = np.random.uniform(self.scale_range[0], self.scale_range[1])
                noise = np.random.normal(0, self.jitter_std, size=features.shape).astype(np.float32)
                # Keep wrist (indices 0..2) at zero
                noise[0:3] = 0.0
                features = (features * scale + noise).astype(np.float32)
        elif self.data_mode == "sequence":
            features = extract_sequence_features(
                raw_seq,
                target_frames=self.target_seq_len,
                hold_start=hold_start,
                hold_end=hold_end,
            )  # (T, 63)
            if self.augment:
                scale = np.random.uniform(self.scale_range[0], self.scale_range[1])
                noise = np.random.normal(0, self.jitter_std, size=features.shape).astype(np.float32)
                noise[:, 0:3] = 0.0
                features = (features * scale + noise).astype(np.float32)
        else:
            raise ValueError(f"Unknown data_mode: {self.data_mode}")

        return {
            "features": torch.tensor(features, dtype=torch.float32),
            "label": torch.tensor(label, dtype=torch.long),
            "symbol": symbol,
            "sample_id": row["sample_id"],
        }


def get_alphabet_dataloaders(
    splits_dir: str = "data/vsl_alphabet_pilot/splits",
    data_mode: str = "static",
    batch_size: int = 32,
    num_workers: int = 0,
    target_seq_len: int = 30,
) -> Tuple[DataLoader, DataLoader, DataLoader, List[str]]:
    """Helper to create Train, Val, and Test dataloaders for Alphabet pilot."""
    train_csv = os.path.join(splits_dir, "train.csv")
    val_csv = os.path.join(splits_dir, "val.csv")
    test_csv = os.path.join(splits_dir, "test.csv")
    classes_path = os.path.join(splits_dir, "classes.txt")

    train_ds = VSLAlphabetDataset(
        train_csv, classes_path=classes_path, data_mode=data_mode,
        target_seq_len=target_seq_len, augment=True
    )
    val_ds = VSLAlphabetDataset(
        val_csv, classes_path=classes_path, data_mode=data_mode,
        target_seq_len=target_seq_len, augment=False
    )
    test_ds = VSLAlphabetDataset(
        test_csv, classes_path=classes_path, data_mode=data_mode,
        target_seq_len=target_seq_len, augment=False
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, test_loader, train_ds.classes
