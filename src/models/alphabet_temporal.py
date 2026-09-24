"""
Temporal Sequence Classifier for VSL Alphabet (Level 1).
Supports 1D-CNN and BiGRU architectures on sequences of hand landmarks [B, T, 63].
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional


class VSLAlphabetBiGRU(nn.Module):
    def __init__(
        self,
        input_dim: int = 63,
        hidden_dim: int = 64,
        num_layers: int = 2,
        num_classes: int = 25,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [batch_size, seq_len, 63].
        Returns:
            Logits of shape [batch_size, num_classes].
        """
        # Linear projection
        h = F.relu(self.input_proj(x))
        # GRU
        out, _ = self.gru(h)  # [B, T, 2*H]
        # Attention pooling across time
        attn_weights = F.softmax(self.attention(out), dim=1)  # [B, T, 1]
        pooled = torch.sum(out * attn_weights, dim=1)  # [B, 2*H]
        pooled = self.dropout(pooled)
        logits = self.fc(pooled)
        return logits


class VSLAlphabet1DCNN(nn.Module):
    def __init__(
        self,
        input_dim: int = 63,
        num_classes: int = 25,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.conv1 = nn.Conv1d(input_dim, 64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [batch_size, seq_len, 63].
        Returns:
            Logits of shape [batch_size, num_classes].
        """
        # Conv1d expects [B, C, T]
        x = x.transpose(1, 2)
        h = F.relu(self.bn1(self.conv1(x)))
        h = F.relu(self.bn2(self.conv2(h)))
        pooled = self.pool(h).squeeze(-1)  # [B, 128]
        pooled = self.dropout(pooled)
        logits = self.fc(pooled)
        return logits
