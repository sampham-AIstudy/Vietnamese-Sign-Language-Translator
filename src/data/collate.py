"""
Custom Collate Function for VSLR Batches:
Safely stacks sequences, joint presence masks, temporal masks, and labels.
Ensures zero mask corruption and validates tensor integrity.
"""

import torch
from typing import List, Dict, Any


def vsl_collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collates a list of sample dictionaries from VSLDataset into a batched dictionary.

    Args:
        batch: List of sample dicts containing:
            - 'sequence': [T, 67, 3] float tensor
            - 'joint_mask': [T, 67] float tensor
            - 'temporal_mask': [T] float tensor
            - 'label': scalar long tensor
            - 'video_id': int or str
            - 'gloss': str

    Returns:
        batched_dict containing:
            - 'sequences': [B, T, 67, 3] float32 tensor
            - 'joint_masks': [B, T, 67] float32 tensor
            - 'temporal_masks': [B, T] float32 tensor
            - 'labels': [B] long tensor
            - 'video_ids': List[str/int] of length B
            - 'glosses': List[str] of length B
    """
    sequences = torch.stack([item["sequence"] for item in batch], dim=0)
    joint_masks = torch.stack([item["joint_mask"] for item in batch], dim=0)
    temporal_masks = torch.stack([item["temporal_mask"] for item in batch], dim=0)
    labels = torch.stack([item["label"] for item in batch], dim=0)

    video_ids = [item["video_id"] for item in batch]
    glosses = [item["gloss"] for item in batch]

    # Integrity guard
    assert not torch.isnan(sequences).any(), "Collate integrity error: sequences contains NaN!"
    assert not torch.isinf(sequences).any(), "Collate integrity error: sequences contains Inf!"

    return {
        "sequences": sequences,
        "joint_masks": joint_masks,
        "temporal_masks": temporal_masks,
        "labels": labels,
        "video_ids": video_ids,
        "glosses": glosses,
    }
