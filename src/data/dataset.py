"""
PyTorch Datasets and DataLoaders for Vietnamese Sign Language (VSL):
1. VSLSequenceDataset:
   Loads (60, 201) sequence arrays (.npz) from `data (2)/Processed/{split}`.
   Supports filtering top-K glosses for fast, high-accuracy training.
2. AlphabetLandmarkDataset:
   Loads 42-dim normalized hand keypoints for fingerspelling alphabet letters.
"""

import os
import json
import glob
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Optional, Tuple, Union
from src.data.augment import KeypointAugmenter


class VSLSequenceDataset(Dataset):
    """
    Dataset for Word-level Isolated VSL Recognition.
    Loads pre-extracted (60, 201) keypoint sequences from `.npz` files.
    """

    def __init__(
        self,
        split_dir: str,
        label_map_path: str,
        selected_classes: Optional[List[str]] = None,
        max_samples_per_class: Optional[int] = None,
        augment: bool = False,
    ):
        """
        Args:
            split_dir: Path to split directory, e.g. 'data (2)/Processed/train'
            label_map_path: Path to 'label_map.json'
            selected_classes: Optional list of class names to filter (e.g. top 30-50 words).
            max_samples_per_class: Limit samples per class (useful for quick debugging).
            augment: Whether to apply keypoint augmentation.
        """
        self.split_dir = split_dir
        self.augment = augment
        self.augmenter = KeypointAugmenter() if augment else None

        with open(label_map_path, "r", encoding="utf-8") as f:
            full_label_map = json.load(f)

        # Class selection
        if selected_classes is not None:
            self.classes = sorted(selected_classes)
        else:
            # Discover existing class folders in split_dir
            existing_dirs = [
                d for d in os.listdir(split_dir)
                if os.path.isdir(os.path.join(split_dir, d))
            ]
            self.classes = sorted(existing_dirs)

        # Build contiguous label index [0..N-1]
        self.class_to_idx = {cls_name: i for i, cls_name in enumerate(self.classes)}
        self.idx_to_class = {i: cls_name for cls_name, i in self.class_to_idx.items()}

        # Gather sample file paths
        self.samples: List[Tuple[str, int]] = []
        for cls_name in self.classes:
            class_folder = os.path.join(split_dir, cls_name)
            if not os.path.isdir(class_folder):
                continue
            npz_files = glob.glob(os.path.join(class_folder, "*.npz"))
            if max_samples_per_class:
                npz_files = npz_files[:max_samples_per_class]
            cls_idx = self.class_to_idx[cls_name]
            for file_path in npz_files:
                self.samples.append((file_path, cls_idx))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        file_path, label_idx = self.samples[idx]
        data = np.load(file_path)
        sequence = data["sequence"].astype(np.float32)  # shape (60, 201)

        # Apply augmentation if enabled
        if self.augment and self.augmenter:
            sequence = self.augmenter.augment_sequence(sequence)

        sequence_tensor = torch.tensor(sequence, dtype=torch.float32)
        label_tensor = torch.tensor(label_idx, dtype=torch.long)
        return sequence_tensor, label_tensor


class AlphabetLandmarkDataset(Dataset):
    """
    Dataset for Static Fingerspelling / Alphabet Recognition (Level 1).
    Loads 42-dim normalized hand landmarks.
    """

    def __init__(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        class_to_idx: Dict[str, int],
        augment: bool = False,
    ):
        self.features = features.astype(np.float32)
        self.labels = labels
        self.class_to_idx = class_to_idx
        self.idx_to_class = {i: c for c, i in class_to_idx.items()}
        self.augment = augment
        self.augmenter = KeypointAugmenter() if augment else None

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        feat = self.features[idx].copy()
        if self.augment and self.augmenter:
            feat = self.augmenter.augment_static(feat)

        x = torch.tensor(feat, dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        return x, y


def get_top_classes(
    processed_dir: str, top_k: int = 50, min_samples_per_class: int = 20
) -> List[str]:
    """
    Finds top-K classes with the most training samples in `processed_dir/train`.
    Ensures balanced and sufficient data for robust model training.
    """
    train_dir = os.path.join(processed_dir, "train")
    class_counts = []
    for cls_name in os.listdir(train_dir):
        cls_path = os.path.join(train_dir, cls_name)
        if os.path.isdir(cls_path):
            count = len(glob.glob(os.path.join(cls_path, "*.npz")))
            if count >= min_samples_per_class:
                class_counts.append((cls_name, count))

    # Sort descending by sample count
    class_counts.sort(key=lambda x: x[1], reverse=True)
    top_classes = [c[0] for c in class_counts[:top_k]]
    return top_classes


def create_word_dataloaders(
    processed_dir: str,
    top_k: int = 50,
    batch_size: int = 32,
    num_workers: int = 0,
    selected_classes: Optional[List[str]] = None,
) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[int, str]]:
    """
    Creates train, val, and test DataLoaders for word-level sequence classification.
    """
    label_map_path = os.path.join(processed_dir, "label_map.json")

    if selected_classes is None:
        selected_classes = get_top_classes(processed_dir, top_k=top_k)

    train_ds = VSLSequenceDataset(
        split_dir=os.path.join(processed_dir, "train"),
        label_map_path=label_map_path,
        selected_classes=selected_classes,
        augment=True,
    )
    val_ds = VSLSequenceDataset(
        split_dir=os.path.join(processed_dir, "val"),
        label_map_path=label_map_path,
        selected_classes=selected_classes,
        augment=False,
    )
    test_ds = VSLSequenceDataset(
        split_dir=os.path.join(processed_dir, "test"),
        label_map_path=label_map_path,
        selected_classes=selected_classes,
        augment=False,
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, test_loader, train_ds.idx_to_class
