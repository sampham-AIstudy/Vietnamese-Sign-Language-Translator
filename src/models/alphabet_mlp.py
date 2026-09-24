"""
Static MLP Classifier for VSL Alphabet (Level 1).
Takes palm-scale normalized 21 hand landmarks (63 features) and predicts 25 VSL alphabet classes.
Ultra-lightweight (< 0.1M params) for real-time webcam inference (< 1ms).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional


class VSLAlphabetMLP(nn.Module):
    def __init__(
        self,
        input_dim: int = 63,
        num_classes: int = 25,
        hidden_dims: tuple = (128, 64),
        dropout: float = 0.2,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(dropout))
            prev_dim = h_dim

        self.backbone = nn.Sequential(*layers)
        self.classifier = nn.Linear(prev_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [batch_size, 63] or [batch_size, 21, 3].
        Returns:
            Logits of shape [batch_size, num_classes].
        """
        if x.dim() == 3:
            x = x.view(x.size(0), -1)
        h = self.backbone(x)
        logits = self.classifier(h)
        return logits

    @torch.no_grad()
    def predict_single(self, feature_vector: torch.Tensor) -> Dict[str, Any]:
        """
        Inference helper for a single sample.
        Args:
            feature_vector: Tensor of shape (63,) or (1, 63).
        Returns:
            Dict with class_idx, confidence, probabilities.
        """
        self.eval()
        if feature_vector.dim() == 1:
            feature_vector = feature_vector.unsqueeze(0)
        logits = self.forward(feature_vector)
        probs = F.softmax(logits, dim=-1)[0]
        conf, pred_idx = torch.max(probs, dim=-1)
        return {
            "class_idx": int(pred_idx.item()),
            "confidence": float(conf.item()),
            "probabilities": probs.cpu().numpy().tolist(),
        }
