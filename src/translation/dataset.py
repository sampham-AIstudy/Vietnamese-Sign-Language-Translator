"""
Translation PyTorch Dataset implementations:
1. Clean10kDataset: Auxiliary pretraining dataset (7,140 cleaned pairs)
2. VSLGHTextDataset: Primary domain fine-tuning dataset (300 VSL-GH canonical sentences)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

import torch
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizer

from src.translation.text_normalizer import normalize_vsl_source, normalize_vietnamese_target


class Clean10kDataset(Dataset):
    """
    Dataset for Auxiliary Pretraining (Stage 1) on Cleaned 10K Parallel Text.
    """
    def __init__(
        self,
        jsonl_path: Union[str, Path] = "data/external/parallel_text/vie_vsl_10k_cleaned.jsonl",
        split: str = "train", # 'train' (90%) or 'val' (10%)
        val_ratio: float = 0.1,
        seed: int = 42,
    ):
        self.jsonl_path = Path(jsonl_path)
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            all_data = [json.loads(line) for line in f]

        # Deterministic train/val split
        import random
        rng = random.Random(seed)
        shuffled = list(all_data)
        rng.shuffle(shuffled)

        val_size = int(len(shuffled) * val_ratio)
        if split == "val":
            self.samples = shuffled[:val_size]
        else:
            self.samples = shuffled[val_size:]

        self.normalized_pairs: List[Tuple[str, str, str]] = []
        for item in self.samples:
            src_norm = normalize_vsl_source(item["vsl"])
            tgt_norm = normalize_vietnamese_target(item["vi"])
            self.normalized_pairs.append((item["id"], src_norm, tgt_norm))

    def __len__(self) -> int:
        return len(self.normalized_pairs)

    def __getitem__(self, idx: int) -> Dict[str, str]:
        item_id, src, tgt = self.normalized_pairs[idx]
        return {
            "id": item_id,
            "source": src,
            "target": tgt,
        }


class VSLGHTextDataset(Dataset):
    """
    Dataset for Primary Domain Fine-Tuning (Stage 2) on VSL-GH 300 canonical sentences.
    Split protocol:
      - 'train': SENT001..SENT240 (240 unique sentences, 80%)
      - 'val':   SENT241..SENT270 (30 unique sentences, 10%)
      - 'test':  SENT271..SENT300 (30 unique sentences, 10%) - strictly held out
      - 'all':   SENT001..SENT300 (300 unique sentences)
    """
    def __init__(
        self,
        canonical_json: Union[str, Path] = "data/external/vsl_gh/dataset_canonical.json",
        split: str = "train",  # 'train', 'val', 'test', 'all'
    ):
        self.canonical_json = Path(canonical_json)
        with open(self.canonical_json, "r", encoding="utf-8") as f:
            all_samples = json.load(f)

        # Collect unique sentences
        unique_sentences = {}
        for s in all_samples:
            sid = s["sentence_id"]
            if sid not in unique_sentences:
                unique_sentences[sid] = {
                    "sentence_id": sid,
                    "gloss_sequence": s.get("gloss_sequence", []),
                    "translation": s.get("translation", ""),
                }

        all_sids = sorted(list(unique_sentences.keys()))  # SENT001..SENT300

        if split == "train":
            target_sids = set(all_sids[:240])       # SENT001..SENT240 (240)
        elif split == "val":
            target_sids = set(all_sids[240:270])    # SENT241..SENT270 (30)
        elif split == "test":
            target_sids = set(all_sids[270:])       # SENT271..SENT300 (30)
        elif split == "all":
            target_sids = set(all_sids)             # 300
        else:
            raise ValueError(f"Unknown split: {split}")

        self.samples = []
        for sid in sorted(list(target_sids)):
            item = unique_sentences[sid]
            src_norm = normalize_vsl_source(item["gloss_sequence"])
            tgt_norm = normalize_vietnamese_target(item["translation"])
            self.samples.append({
                "id": sid,
                "sentence_id": sid,
                "source": src_norm,
                "target": tgt_norm,
                "raw_glosses": item["gloss_sequence"],
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def get_seq2seq_collate_fn(tokenizer: PreTrainedTokenizer, max_source_length: int = 128, max_target_length: int = 128):
    """
    Returns collate function that tokenizes and pads batches for Seq2Seq models (ViT5 / T5).
    """
    def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        sources = [item["source"] for item in batch]
        targets = [item["target"] for item in batch]

        model_inputs = tokenizer(
            sources,
            max_length=max_source_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        labels = tokenizer(
            targets,
            max_length=max_target_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )["input_ids"]

        # Replace padding token id's with -100 so loss ignores them
        labels[labels == tokenizer.pad_token_id] = -100
        model_inputs["labels"] = labels
        model_inputs["raw_sources"] = sources
        model_inputs["raw_targets"] = targets
        model_inputs["ids"] = [item["id"] for item in batch]

        return model_inputs

    return collate_fn
