"""
Bidirectional GRU Classifier with Temporal Self-Attention for Word-Level VSL (Level 2).
Inputs: (B, 60, 201) landmark sequence.
Outputs: Logits for num_classes Vietnamese glosses.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TemporalAttention(nn.Module):
    """Computes a learned weighted average over sequence time frames."""
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, rnn_out: torch.Tensor) -> torch.Tensor:
        # rnn_out shape: (B, T, hidden_dim)
        scores = self.attn(rnn_out)  # (B, T, 1)
        weights = F.softmax(scores, dim=1)  # (B, T, 1)
        context = torch.sum(rnn_out * weights, dim=1)  # (B, hidden_dim)
        return context


class BiGRUSequenceClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int = 201,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_classes: int = 50,
        dropout: float = 0.3,
        bidirectional: bool = True,
    ):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout / 2),
        )

        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        gru_out_dim = hidden_dim * 2 if bidirectional else hidden_dim
        self.attention = TemporalAttention(gru_out_dim)

        self.classifier = nn.Sequential(
            nn.Linear(gru_out_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, 60, 201)
        projected = self.input_proj(x)  # (B, 60, hidden_dim)
        rnn_out, _ = self.gru(projected)  # (B, 60, gru_out_dim)
        context = self.attention(rnn_out)  # (B, gru_out_dim)
        logits = self.classifier(context)  # (B, num_classes)
        return logits
