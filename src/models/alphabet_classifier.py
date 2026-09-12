"""
Alphabet Classifier Model (Fingerspelling - Level 1)
Neural network for 42-dimensional normalized MediaPipe hand keypoints (21 landmarks x 2).
Based on Paper 2: "Vietnamese Sign Language Alphabet Recognition Using Deep Learning and Mediapipe Methods"
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class AlphabetMLP(nn.Module):
    def __init__(self, input_dim: int = 42, num_classes: int = 29, hidden_dims: list = None, dropout: float = 0.25):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 128, 64]

        layers = []
        in_d = input_dim
        for h_d in hidden_dims:
            layers.extend([
                nn.Linear(in_d, h_d),
                nn.BatchNorm1d(h_d),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout)
            ])
            in_d = h_d

        self.feature_extractor = nn.Sequential(*layers)
        self.classifier = nn.Linear(in_d, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, 42)
        features = self.feature_extractor(x)
        logits = self.classifier(features)
        return logits
