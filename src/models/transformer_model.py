"""
Transformer / Temporal Attention Architecture for Vietnamese Sign Language Recognition (VSLR)
Designed for Phase 7 of the VSLR Benchmark.

Architecture Highlights:
1. Input Projection:
   - Flattens 67 landmarks x 3 coordinates (201 dimensions) per frame.
   - Applies Linear projection to `d_model` followed by LayerNorm, GELU, and Dropout.
2. Positional Encoding:
   - Supports Sinusoidal Positional Encoding (default) or Learnable Positional Embedding.
   - Injects temporal ordering information across sequence length T=60.
3. Transformer Encoder:
   - PyTorch native nn.TransformerEncoder with nn.TransformerEncoderLayer (Pre-LN).
   - Utilizes `src_key_padding_mask` to strictly ignore padding frames (temporal_mask == 0).
4. Masked Temporal Pooling:
   - Supports Masked Attention Pooling (default) or Masked Mean Pooling.
   - Guarantees zero contribution from padded/invalid temporal frames.
5. Classifier Head:
   - Dropout -> Linear(d_model, num_classes).
6. Resource Efficiency:
   - Compact parameter footprint (~306K params), fully optimized for NVIDIA RTX 3050 4GB GPU.
"""

import math
from typing import Optional, Literal
import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    """
    Sinusoidal Positional Encoding for temporal sequences.
    PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # Shape: [1, max_len, d_model]

        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [B, T, d_model]
        Returns:
            Tensor of shape [B, T, d_model] with positional encoding added.
        """
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class LearnablePositionalEncoding(nn.Module):
    """
    Learnable Positional Embedding across sequence length T.
    """
    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        self.pe = nn.Parameter(torch.zeros(1, max_len, d_model))
        nn.init.trunc_normal_(self.pe, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class MaskedTemporalAttention(nn.Module):
    """
    Computes masked attention weights across temporal frames.
    Padded frames (temporal_mask == 0) are excluded via large negative masking before Softmax.
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
            # Mask out invalid frames (-1e4 is safe for fp16 in AMP)
            mask = temporal_mask.unsqueeze(-1).bool()  # [B, T, 1]
            scores = scores.masked_fill(~mask, -1e4)

        weights = F.softmax(scores, dim=1)  # [B, T, 1]
        # Safeguard against degenerate all-masked sequences
        weights = torch.nan_to_num(weights, nan=0.0)

        pooled = torch.sum(x * weights, dim=1)  # [B, D]
        return pooled


class MaskedMeanPooling(nn.Module):
    """
    Computes mean over valid temporal frames using temporal_mask.
    """
    def forward(self, x: torch.Tensor, temporal_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        if temporal_mask is not None:
            t_mask = temporal_mask.unsqueeze(-1)  # [B, T, 1]
            denom = t_mask.sum(dim=1).clamp(min=1e-8)
            return (x * t_mask).sum(dim=1) / denom
        return x.mean(dim=1)


class TransformerModel(nn.Module):
    """
    Transformer Encoder Sequence Classifier for Vietnamese Sign Language Recognition.

    Pipeline:
    1. Spatial Joint Masking & Flattening: [B, T, V, C] -> [B, T, V*C]
    2. Linear Projection + LayerNorm + GELU: [B, T, 201] -> [B, T, d_model]
    3. Positional Encoding: Sinusoidal or Learnable
    4. Transformer Encoder (L layers with Multi-Head Self-Attention & Pre-LN):
       - Masks out padded frames using src_key_padding_mask
    5. Masked Temporal Pooling (Attention or Mean): [B, T, d_model] -> [B, d_model]
    6. Classification Head: [B, d_model] -> [B, num_classes]
    """
    def __init__(
        self,
        num_joints: int = 67,
        coord_dim: int = 3,
        d_model: int = 128,
        nhead: int = 4,
        dim_feedforward: int = 256,
        num_layers: int = 2,
        num_classes: int = 50,
        dropout: float = 0.1,
        pos_encoding: Literal["sinusoidal", "learnable", "none"] = "sinusoidal",
        pooling_type: Literal["attention", "mean"] = "attention",
        norm_first: bool = True,
        max_len: int = 500,
    ):
        super().__init__()
        self.num_joints = num_joints
        self.coord_dim = coord_dim
        self.input_dim = num_joints * coord_dim
        self.d_model = d_model
        self.nhead = nhead
        self.dim_feedforward = dim_feedforward
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.pooling_type = pooling_type
        self.pos_encoding_type = pos_encoding

        # 1. Spatial Projection: [B, T, 201] -> [B, T, d_model]
        self.spatial_proj = nn.Sequential(
            nn.Linear(self.input_dim, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # 2. Positional Encoding
        if pos_encoding == "sinusoidal":
            self.pos_encoder = PositionalEncoding(d_model=d_model, max_len=max_len, dropout=dropout)
        elif pos_encoding == "learnable":
            self.pos_encoder = LearnablePositionalEncoding(d_model=d_model, max_len=max_len, dropout=dropout)
        elif pos_encoding == "none":
            self.pos_encoder = nn.Dropout(dropout)
        else:
            raise ValueError(f"Unsupported pos_encoding: '{pos_encoding}'. Choose from ['sinusoidal', 'learnable', 'none'].")

        # 3. Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=norm_first,
        )
        final_norm = nn.LayerNorm(d_model) if norm_first else None
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer=encoder_layer,
            num_layers=num_layers,
            norm=final_norm,
            enable_nested_tensor=False,
        )

        # 4. Masked Temporal Pooling
        if pooling_type == "attention":
            self.pooler = MaskedTemporalAttention(in_features=d_model, hidden_dim=d_model // 2)
        elif pooling_type == "mean":
            self.pooler = MaskedMeanPooling()
        else:
            raise ValueError(f"Unsupported pooling_type: '{pooling_type}'. Choose 'attention' or 'mean'.")

        # 5. Classifier Head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes),
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
            joint_masks: [B, T, V] optional binary mask for joints
            temporal_masks: [B, T] binary mask where 1.0 = valid frame, 0.0 = padded frame
        Returns:
            logits: [B, num_classes]
        """
        B, T = sequences.shape[0], sequences.shape[1]

        # 1. Spatial Flattening and Joint Masking
        if sequences.dim() == 4:
            if joint_masks is not None:
                sequences = sequences * joint_masks.unsqueeze(-1)
            x = sequences.contiguous().view(B, T, -1)  # [B, T, 201]
        else:
            x = sequences

        # 2. Input Embedding & Projection: [B, T, 201] -> [B, T, d_model]
        x = self.spatial_proj(x)

        # 3. Positional Encoding
        x = self.pos_encoder(x)

        # 4. Transformer Encoder with Key Padding Mask
        # PyTorch Transformer convention: True = position to IGNORE (padding)
        src_key_padding_mask = None
        if temporal_masks is not None:
            src_key_padding_mask = (temporal_masks == 0).bool()  # [B, T]

        encoded = self.transformer_encoder(x, src_key_padding_mask=src_key_padding_mask)  # [B, T, d_model]

        # 5. Masked Temporal Pooling: [B, T, d_model] -> [B, d_model]
        pooled = self.pooler(encoded, temporal_mask=temporal_masks)

        # 6. Classification Head: [B, d_model] -> [B, num_classes]
        logits = self.classifier(pooled)
        return logits
