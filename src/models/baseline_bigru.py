"""
Baseline BiGRU Sequence Classifier with Joint & Temporal Masking
Designed for Vietnamese Sign Language Recognition (VSLR) Clean Benchmark.

Inputs:
  - sequences: Tensor of shape [B, T, V, C] or [B, T, V*C]
  - joint_masks: Optional Tensor of shape [B, T, V]
  - temporal_masks: Optional Tensor of shape [B, T]
Outputs:
  - logits: Tensor of shape [B, num_classes]
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Any


class MaskedTemporalAttention(nn.Module):
    """
    Computes masked attention weights across time frames.
    Invalid/padded frames (temporal_mask == 0) are excluded from the softmax.
    """
    def __init__(self, in_features: int, hidden_dim: Optional[int] = None):
        super().__init__()
        attn_dim = hidden_dim or (in_features // 2)
        self.score_net = nn.Sequential(
            nn.Linear(in_features, attn_dim),
            nn.Tanh(),
            nn.Linear(attn_dim, 1),
        )

    def forward(self, x: torch.Tensor, temporal_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [B, T, D]
            temporal_mask: Binary mask [B, T] where 1.0 indicates a valid frame.
        Returns:
            pooled: Tensor of shape [B, D]
        """
        scores = self.score_net(x)  # [B, T, 1]

        if temporal_mask is not None:
            # Mask out invalid frames (safe for float16 Half in AMP)
            mask = temporal_mask.unsqueeze(-1).bool()  # [B, T, 1]
            scores = scores.masked_fill(~mask, -1e4)

        weights = F.softmax(scores, dim=1)  # [B, T, 1]
        # Safeguard against all-masked frames (degenerate edge cases)
        weights = torch.nan_to_num(weights, nan=0.0)

        pooled = torch.sum(x * weights, dim=1)  # [B, D]
        return pooled


class BaselineBiGRU(nn.Module):
    """
    Baseline VSLR Classifier:
    1. Spatial Joint Masking & Projection: [B, T, 67, 3] -> [B, T, hidden_dim]
    2. Bidirectional GRU: [B, T, hidden_dim] -> [B, T, hidden_dim * 2]
    3. Masked Temporal Pooling: [B, T, hidden_dim * 2] -> [B, hidden_dim * 2]
    4. Classifier Head: [B, hidden_dim * 2] -> [B, num_classes]
    """
    def __init__(
        self,
        num_joints: int = 67,
        coord_dim: int = 3,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_classes: int = 50,
        dropout: float = 0.3,
        bidirectional: bool = True,
        pooling_type: str = "attention",  # "attention" or "mean"
    ):
        super().__init__()
        self.num_joints = num_joints
        self.coord_dim = coord_dim
        self.input_dim = num_joints * coord_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.bidirectional = bidirectional
        self.pooling_type = pooling_type

        # 1. Spatial Embedding
        self.spatial_proj = nn.Sequential(
            nn.Linear(self.input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout / 2.0),
        )

        # 2. Temporal Modeling (BiGRU)
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        gru_out_dim = hidden_dim * 2 if bidirectional else hidden_dim

        # 3. Masked Temporal Pooling
        if pooling_type == "attention":
            self.pooler = MaskedTemporalAttention(gru_out_dim)
        elif pooling_type == "mean":
            self.pooler = None
        else:
            raise ValueError(f"Unsupported pooling_type: {pooling_type}. Choose 'attention' or 'mean'.")

        # 4. Classifier Head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(gru_out_dim, num_classes),
        )

    def forward(
        self,
        sequences: torch.Tensor,
        joint_masks: Optional[torch.Tensor] = None,
        temporal_masks: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            sequences: [B, T, V, C] or [B, T, V*C]
            joint_masks: [B, T, V]
            temporal_masks: [B, T]
        Returns:
            logits: [B, num_classes]
        """
        B, T = sequences.shape[0], sequences.shape[1]

        # Apply joint masking if provided and sequences are 4D
        if sequences.dim() == 4:
            if joint_masks is not None:
                sequences = sequences * joint_masks.unsqueeze(-1)
            x = sequences.contiguous().view(B, T, -1)  # [B, T, 201]
        else:
            x = sequences

        # Spatial projection
        x = self.spatial_proj(x)  # [B, T, hidden_dim]

        # Temporal modeling
        rnn_out, _ = self.gru(x)  # [B, T, gru_out_dim]

        # Masked temporal pooling
        if self.pooling_type == "attention":
            context = self.pooler(rnn_out, temporal_mask=temporal_masks)
        else:  # Masked mean pooling
            if temporal_masks is not None:
                t_mask = temporal_masks.unsqueeze(-1)  # [B, T, 1]
                denom = t_mask.sum(dim=1).clamp(min=1e-8)
                context = (rnn_out * t_mask).sum(dim=1) / denom
            else:
                context = rnn_out.mean(dim=1)

        # Classification logits
        logits = self.classifier(context)  # [B, num_classes]
        return logits
