"""
PyTorch Dataset and DataLoader for Clean VSLR Sequences:
- Lazy loads extracted 67-joint landmarks from .npz files.
- Automatically handles on-demand extraction with caching if .npz does not exist yet.
- Applies clean preprocessing pipeline:
    1. Visibility-aware temporal interpolation (no zero-fill).
    2. Robust spatial translation and scale normalization.
    3. Temporal length standardization and frame masking.
- Returns clean tensors:
    sequences [60, 67, 3], joint_masks [60, 67], temporal_masks [60], labels (long).
"""

import os
import re
import json
import csv
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import collections
from typing import Dict, List, Optional, Tuple, Any, Set

from src.data.preprocessing.pipeline import VSLPreprocessingPipeline
from src.data.collate import vsl_collate_fn
from src.data.landmark_extractor import CleanHolisticExtractor, save_landmarks_npz
from src.data.augment import KeypointAugmenter


class SplitIntegrityError(Exception):
    """Base exception for dataset split integrity violations."""
    pass


class VideoLeakageError(SplitIntegrityError):
    """Raised when the same video appears across multiple splits (leakage)."""
    pass


class DialectConfoundedError(SplitIntegrityError):
    """Raised when dialect distribution is confounded across splits."""
    pass


class ClassCountMismatchError(SplitIntegrityError):
    """Raised when the number of classes in splits does not match expected count."""
    pass


class DuplicateRecordingLeakageError(SplitIntegrityError):
    """Raised when one physical recording (QIPEDC re-captions a clip per region) spans splits."""
    pass


# Built by scripts/build_recording_groups.py; see reports/audit_round3/PROVENANCE.md.
DEFAULT_RECORDING_GROUPS_CSV = os.path.join("data", "splits", "recording_groups.csv")


def validate_split_guards(
    train_csv: str,
    val_csv: str,
    test_csv: str,
    expected_num_classes: Optional[int] = None,
    allow_cross_dialect_benchmark: bool = False,
    recording_groups_csv: Optional[str] = DEFAULT_RECORDING_GROUPS_CSV,
    allow_duplicate_recordings: bool = False,
) -> Dict[str, Any]:
    """
    Validates dataset split integrity across train, val, and test CSVs.

    Guards:
    1. Video Leakage Guard:
       Ensures no video_id or video file name appears in more than one split.
    1b. Duplicate Recording Guard:
       If `recording_groups_csv` exists, ensures no recording group (the same clip saved
       under several file names) spans splits. `allow_duplicate_recordings=True` exists only
       to reproduce legacy numbers; results obtained that way are not valid benchmarks.
    2. Dialect Confounding Guard:
       For standard in-domain splits, ensures train is not 100% single dialect
       when multiple dialects exist across the overall dataset.
    3. Class Count Guard:
       Ensures number of unique classes in train matches expected_num_classes (if provided)
       and that test/val do not have unrepresented classes outside train.

    Returns:
        Dict with validation statistics (video_counts, dialect_counts, class_counts).
    Raises:
        VideoLeakageError, DialectConfoundedError, ClassCountMismatchError, FileNotFoundError
    """
    for p in [train_csv, val_csv, test_csv]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Split file does not exist: {p}")

    def read_split(path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    train_rows = read_split(train_csv)
    val_rows = read_split(val_csv)
    test_rows = read_split(test_csv)

    # 1. Video Leakage Guard
    def get_video_keys(rows: List[Dict[str, Any]]) -> Set[str]:
        keys = set()
        for r in rows:
            vid = r.get("video_id") or r.get("file_name") or r.get("file_path")
            if vid:
                keys.add(str(vid).strip().lower())
        return keys

    train_vids = get_video_keys(train_rows)
    val_vids = get_video_keys(val_rows)
    test_vids = get_video_keys(test_rows)

    leak_train_val = train_vids & val_vids
    leak_train_test = train_vids & test_vids
    leak_val_test = val_vids & test_vids

    if leak_train_val or leak_train_test or leak_val_test:
        all_leaks = leak_train_val | leak_train_test | leak_val_test
        raise VideoLeakageError(
            f"Split integrity violation: Found {len(all_leaks)} leaked videos across splits! "
            f"(train-val: {len(leak_train_val)}, train-test: {len(leak_train_test)}, val-test: {len(leak_val_test)})"
        )

    # 1b. Duplicate Recording Guard
    duplicate_check = "SKIPPED (no recording_groups file)"
    if allow_duplicate_recordings:
        duplicate_check = "DISABLED (legacy reproduction only)"
    elif recording_groups_csv and os.path.exists(recording_groups_csv):
        with open(recording_groups_csv, "r", encoding="utf-8-sig") as f:
            group_of = {r["file_name"].strip().lower(): r["recording_group"] for r in csv.DictReader(f)}
        split_of_group: Dict[str, str] = {}
        crossing: Set[str] = set()
        for split_name, rows in (("train", train_rows), ("val", val_rows), ("test", test_rows)):
            for r in rows:
                fname = os.path.basename(str(r.get("file_name") or r.get("file_path") or "")).strip().lower()
                group = group_of.get(fname)
                if group is not None and split_of_group.setdefault(group, split_name) != split_name:
                    crossing.add(group)
        if crossing:
            raise DuplicateRecordingLeakageError(
                f"Split integrity violation: {len(crossing)} recordings appear in more than one split under "
                f"different file names (e.g. {sorted(crossing)[:3]}). Use data/splits/folds/tier2_grouped_*.csv "
                f"(scripts/create_grouped_splits.py)."
            )
        duplicate_check = "PASS"

    # 2. Dialect Confounding Guard
    def get_dialects(rows: List[Dict[str, Any]]) -> collections.Counter:
        counts = collections.Counter()
        for r in rows:
            d = r.get("dialect") or r.get("possible_region_or_dialect") or "unknown"
            if isinstance(d, str) and d.strip():
                code = d.strip()[0].upper()
                if code in ("B", "N", "T"):
                    counts[code] += 1
                else:
                    counts[d.strip()] += 1
            else:
                counts["unknown"] += 1
        return counts

    train_dialects = get_dialects(train_rows)
    val_dialects = get_dialects(val_rows)
    test_dialects = get_dialects(test_rows)

    total_dialects = set(train_dialects.keys()) | set(val_dialects.keys()) | set(test_dialects.keys())
    known_dialects = {d for d in total_dialects if d in ("B", "N", "T")}

    if not allow_cross_dialect_benchmark and len(known_dialects) > 1:
        # Check if train is 100% single dialect while other dialects exist in val or test
        train_known = {d: count for d, count in train_dialects.items() if d in known_dialects}
        if len(train_known) == 1 and len(known_dialects) > 1:
            dominant = list(train_known.keys())[0]
            raise DialectConfoundedError(
                f"Split integrity violation: Train split is confounded with 100% dialect '{dominant}' "
                f"while dataset contains dialects {known_dialects}. "
                f"Use recording-grouped splits (tier2_grouped_*.csv) to prevent single-dialect bias."
            )

    # 3. Class Count Guard
    train_classes = set(r["gloss_normalized"] for r in train_rows if "gloss_normalized" in r)
    val_classes = set(r["gloss_normalized"] for r in val_rows if "gloss_normalized" in r)
    test_classes = set(r["gloss_normalized"] for r in test_rows if "gloss_normalized" in r)

    if expected_num_classes is not None:
        if len(train_classes) != expected_num_classes:
            raise ClassCountMismatchError(
                f"Class count mismatch: expected {expected_num_classes} classes, but train split has {len(train_classes)} classes."
            )

    # Check for unseen classes in test/val
    unseen_val = val_classes - train_classes
    unseen_test = test_classes - train_classes
    if unseen_val or unseen_test:
        raise ClassCountMismatchError(
            f"Split integrity violation: Unseen classes detected! Val has {len(unseen_val)} unseen classes, "
            f"Test has {len(unseen_test)} unseen classes not present in train."
        )

    return {
        "status": "PASS",
        "train_samples": len(train_rows),
        "val_samples": len(val_rows),
        "test_samples": len(test_rows),
        "num_classes": len(train_classes),
        "train_dialects": dict(train_dialects),
        "val_dialects": dict(val_dialects),
        "test_dialects": dict(test_dialects),
        "duplicate_recording_check": duplicate_check,
    }


class VSLDataset(Dataset):
    """
    Standard PyTorch Dataset for isolated Vietnamese Sign Language Recognition.
    """

    def __init__(
        self,
        split_csv: str,
        keypoints_dir: str = "data/extracted_keypoints",
        label_map: Optional[Dict[str, int]] = None,
        pipeline: Optional[VSLPreprocessingPipeline] = None,
        target_len: int = 60,
        auto_extract: bool = True,
        augment: bool = False,
        epoch_multiplier: int = 1,
    ):
        """
        Args:
            split_csv: Path to split CSV (e.g. data/splits/tier1_train.csv).
            keypoints_dir: Root directory for pre-extracted .npz landmark files.
            label_map: Dict mapping gloss string to integer label.
            pipeline: Instance of VSLPreprocessingPipeline.
            target_len: Target sequence length (default 60 frames).
            auto_extract: If True, extracts and caches landmarks from raw video if .npz is missing.
            augment: If True, applies on-the-fly keypoint and temporal augmentation.
            epoch_multiplier: Multiplies virtual dataset length for diverse augmented batches.
        """
        if not os.path.exists(split_csv):
            raise FileNotFoundError(f"Split CSV not found: {split_csv}")

        with open(split_csv, "r", encoding="utf-8-sig") as f:
            self.samples: List[Dict[str, Any]] = list(csv.DictReader(f))

        self.keypoints_dir = keypoints_dir
        self.target_len = target_len
        self.auto_extract = auto_extract
        self.augment = augment
        self.epoch_multiplier = max(1, int(epoch_multiplier)) if augment else 1
        self.augmenter = KeypointAugmenter() if augment else None

        # Establish deterministic label mapping
        if label_map is not None:
            self.label_map = label_map
        else:
            unique_classes = sorted(list(set(row["gloss_normalized"] for row in self.samples)))
            self.label_map = {cls_name: i for i, cls_name in enumerate(unique_classes)}

        self.idx_to_label = {v: k for k, v in self.label_map.items()}

        # Master preprocessing pipeline
        self.pipeline = pipeline or VSLPreprocessingPipeline(target_len=target_len)

        # Lazy extractor instance for auto_extract
        self._extractor: Optional[CleanHolisticExtractor] = None

    def _get_extractor(self) -> CleanHolisticExtractor:
        if self._extractor is None:
            self._extractor = CleanHolisticExtractor()
        return self._extractor

    def __len__(self) -> int:
        return len(self.samples) * self.epoch_multiplier

    def _locate_or_extract_npz(self, row: Dict[str, Any]) -> str:
        """Finds existing .npz file or extracts from raw video and caches it."""
        video_id = row["video_id"]
        gloss = row["gloss_normalized"]
        split = row.get("split", "unknown")
        raw_video_path = row.get("file_path", "")
        if not os.path.exists(raw_video_path):
            fallback = os.path.join("data", "Dataset", "Videos", row.get("file_name", ""))
            if os.path.exists(fallback):
                raw_video_path = fallback

        # Sanitize gloss name for Windows filesystem compatibility (e.g. replace '?' with '_')
        safe_gloss = re.sub(r'[<>:"/\\|?*]', '_', gloss).strip()

        # 1. Check hierarchical path: keypoints_dir/split/safe_gloss/{video_id}.npz
        p1 = os.path.join(self.keypoints_dir, split, safe_gloss, f"{video_id}.npz")
        if os.path.exists(p1):
            return p1

        # Also check other subdirs in keypoints_dir if split was remapped
        for s in ["train", "val", "test"]:
            alt_p = os.path.join(self.keypoints_dir, s, safe_gloss, f"{video_id}.npz")
            if os.path.exists(alt_p):
                return alt_p

        # 2. Check flat path: keypoints_dir/{video_id}.npz
        p2 = os.path.join(self.keypoints_dir, f"{video_id}.npz")
        if os.path.exists(p2):
            return p2

        # 3. Check dry-run directory fallback: data/dry_run_extracted/split/safe_gloss/{video_id}.npz
        p3 = os.path.join("data", "dry_run_extracted", split, safe_gloss, f"{video_id}.npz")
        if os.path.exists(p3):
            return p3

        # 4. Auto-extract from raw video if enabled
        if self.auto_extract and os.path.exists(raw_video_path):
            extractor = self._get_extractor()
            result = extractor.extract_from_video(raw_video_path)
            kps = result["keypoints"]
            vis = result["visibility_mask"]
            metadata = {
                "video_id": int(video_id),
                "file_name": row["file_name"],
                "gloss": gloss,
                "split": split,
                "num_frames": int(result["num_frames"]),
                "fps": float(result["fps"]),
            }
            save_landmarks_npz(p1, kps, vis, metadata)
            return p1

        raise FileNotFoundError(
            f"Landmark .npz not found for video_id {video_id} ({raw_video_path}) and auto_extract is False."
        )

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample_idx = idx % len(self.samples)
        row = self.samples[sample_idx]
        gloss = row["gloss_normalized"]
        label_idx = self.label_map[gloss]
        video_id = row["video_id"]

        npz_path = self._locate_or_extract_npz(row)
        npz_data = np.load(npz_path)

        raw_keypoints = npz_data["keypoints"].astype(np.float32)  # [T, 67, 3]
        visibility_mask = npz_data["visibility_mask"].astype(np.float32)  # [T, 67]

        # Apply robust preprocessing pipeline
        final_kps, final_joint_mask, temporal_mask = self.pipeline(
            raw_keypoints=raw_keypoints,
            visibility=visibility_mask,
        )

        # Apply active data augmentation if enabled for training
        if self.augment and self.augmenter is not None:
            final_kps, final_joint_mask = self.augmenter.augment_vsl_sequence(
                final_kps, final_joint_mask
            )

        return {
            "sequence": torch.tensor(final_kps, dtype=torch.float32),  # [60, 67, 3]
            "joint_mask": torch.tensor(final_joint_mask, dtype=torch.float32),  # [60, 67]
            "temporal_mask": torch.tensor(temporal_mask, dtype=torch.float32),  # [60]
            "label": torch.tensor(label_idx, dtype=torch.long),
            "video_id": video_id,
            "gloss": gloss,
            "split": row.get("split", "unknown"),
        }


def get_vsl_dataloaders(
    tier: str = "tier1",
    batch_size: int = 32,
    num_workers: int = 0,
    keypoints_dir: str = "data/extracted_keypoints",
    target_len: int = 60,
    pin_memory: Optional[bool] = None,
    augment_train: bool = True,
    epoch_multiplier: int = 5,
    train_csv: Optional[str] = None,
    val_csv: Optional[str] = None,
    test_csv: Optional[str] = None,
    validate_guards: bool = True,
    expected_num_classes: Optional[int] = None,
) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[str, int]]:
    """
    Creates Train, Val, and Test DataLoaders for the specified tier.
    """
    if pin_memory is None:
        pin_memory = torch.cuda.is_available()

    if train_csv is None or val_csv is None or test_csv is None:
        if tier == "tier2":
            # Default to recording-grouped folds (487 classes). The older tier2_indomain_* folds put
            # re-captioned copies of one clip in train and test (reports/audit_round3/PROVENANCE.md).
            train_csv = os.path.join("data", "splits", "folds", "tier2_grouped_train.csv")
            val_csv = os.path.join("data", "splits", "folds", "tier2_grouped_val.csv")
            test_csv = os.path.join("data", "splits", "folds", "tier2_grouped_test.csv")
            if expected_num_classes is None:
                expected_num_classes = 487
        else:
            splits_dir = os.path.join("data", "splits", "folds")
            train_csv = os.path.join(splits_dir, f"{tier}_grouped_train.csv")
            val_csv = os.path.join(splits_dir, f"{tier}_grouped_val.csv")
            test_csv = os.path.join(splits_dir, f"{tier}_grouped_test.csv")
            if tier == "tier1" and expected_num_classes is None:
                expected_num_classes = 50

    if validate_guards:
        validate_split_guards(
            train_csv=train_csv,
            val_csv=val_csv,
            test_csv=test_csv,
            expected_num_classes=expected_num_classes,
        )

    # Load shared label mapping from train split
    with open(train_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        unique_classes = sorted(list(set(row["gloss_normalized"] for row in reader)))
    label_map = {cls_name: i for i, cls_name in enumerate(unique_classes)}

    train_ds = VSLDataset(
        split_csv=train_csv,
        keypoints_dir=keypoints_dir,
        label_map=label_map,
        target_len=target_len,
        augment=augment_train,
        epoch_multiplier=epoch_multiplier,
    )
    val_ds = VSLDataset(
        split_csv=val_csv,
        keypoints_dir=keypoints_dir,
        label_map=label_map,
        target_len=target_len,
        augment=False,
    )
    test_ds = VSLDataset(
        split_csv=test_csv,
        keypoints_dir=keypoints_dir,
        label_map=label_map,
        target_len=target_len,
        augment=False,
    )

    persistent = (num_workers > 0)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        collate_fn=vsl_collate_fn,
        pin_memory=pin_memory,
        persistent_workers=persistent,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=vsl_collate_fn,
        pin_memory=pin_memory,
        persistent_workers=persistent,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=vsl_collate_fn,
        pin_memory=pin_memory,
        persistent_workers=persistent,
    )

    return train_loader, val_loader, test_loader, label_map
