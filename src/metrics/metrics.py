"""
Classification Metrics for Vietnamese Sign Language Recognition (VSLR)
- Top-1 Accuracy
- Top-5 Accuracy
- Macro F1 Score (via scikit-learn)
- MetricTracker for epoch aggregation
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from sklearn.metrics import f1_score, precision_score, recall_score


def topk_accuracy(logits: torch.Tensor, targets: torch.Tensor, top_k: int = 1) -> float:
    """
    Computes top-k classification accuracy as a percentage [0.0, 100.0].
    """
    if logits.numel() == 0 or targets.numel() == 0:
        return 0.0

    batch_size = targets.size(0)
    k = min(top_k, logits.size(1))
    _, pred = logits.topk(k, dim=1, largest=True, sorted=True)
    pred = pred.t()  # [k, B]
    correct = pred.eq(targets.view(1, -1).expand_as(pred))
    correct_k = correct[:k].reshape(-1).float().sum(0, keepdim=True).item()
    return (correct_k / batch_size) * 100.0


def compute_metrics(
    all_logits: torch.Tensor,
    all_targets: torch.Tensor,
) -> Dict[str, float]:
    """
    Computes Top-1, Top-5, and Macro F1 on full prediction tensors.
    """
    if all_logits.dim() != 2 or all_targets.dim() != 1:
        raise ValueError("all_logits must be 2D [N, C] and all_targets must be 1D [N].")

    top1 = topk_accuracy(all_logits, all_targets, top_k=1)
    top5 = topk_accuracy(all_logits, all_targets, top_k=5)

    preds = torch.argmax(all_logits, dim=-1).cpu().numpy()
    targets = all_targets.cpu().numpy()

    macro_f1 = float(f1_score(targets, preds, average="macro", zero_division=0) * 100.0)

    return {
        "top1": round(top1, 2),
        "top5": round(top5, 2),
        "macro_f1": round(macro_f1, 2),
    }


class MetricTracker:
    """
    Accumulates batch loss, logits, and targets across an evaluation or training split.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_loss = 0.0
        self.total_samples = 0
        self.all_logits: List[torch.Tensor] = []
        self.all_targets: List[torch.Tensor] = []

    def update(self, loss: float, logits: torch.Tensor, targets: torch.Tensor):
        batch_size = targets.size(0)
        self.total_loss += float(loss) * batch_size
        self.total_samples += batch_size
        self.all_logits.append(logits.detach().cpu())
        self.all_targets.append(targets.detach().cpu())

    def compute(self) -> Dict[str, float]:
        if self.total_samples == 0:
            return {"loss": 0.0, "top1": 0.0, "top5": 0.0, "macro_f1": 0.0}

        avg_loss = self.total_loss / self.total_samples
        cat_logits = torch.cat(self.all_logits, dim=0)
        cat_targets = torch.cat(self.all_targets, dim=0)

        metrics = compute_metrics(cat_logits, cat_targets)
        metrics["loss"] = round(avg_loss, 4)
        return metrics
