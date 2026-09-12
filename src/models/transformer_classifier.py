"""
Spatio-Temporal Transformer Encoder for Word-Level VSL Recognition.
Processes (B, 60, 201) keypoint sequences with self-attention across frames.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 120):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, d_model)
        return x + self.pe[:, :x.size(1)]


class VSLTransformerClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int = 201,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 3,
        dim_feedforward: int = 256,
        num_classes: int = 50,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.embedding = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.LayerNorm(d_model),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

        self.pos_encoder = PositionalEncoding(d_model=d_model, max_len=120)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Classification token / pooling layer
        self.norm = nn.LayerNorm(d_model)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, 60, 201)
        x_emb = self.embedding(x)  # (B, 60, d_model)
        x_pos = self.pos_encoder(x_emb)  # (B, 60, d_model)
        encoded = self.transformer_encoder(x_pos)  # (B, 60, d_model)

        # Global average pooling across time
        pooled = torch.mean(encoded, dim=1)  # (B, d_model)
        pooled = self.norm(pooled)
        logits = self.classifier(pooled)  # (B, num_classes)
        return logits
