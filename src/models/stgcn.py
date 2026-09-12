"""
Lightweight Spatial-Temporal Graph Convolutional Network (ST-GCN) module for VSL skeleton sequences.
Models joint topology (bones between hand/body landmarks) alongside temporal dynamics.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class GraphConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.fc = nn.Linear(in_channels, out_channels)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        # x: (B, T, V, C)
        # adj: (V, V)
        # Spatial convolution via normalized adjacency multiplication
        support = self.fc(x)  # (B, T, V, out_channels)
        out = torch.einsum("vw,btwc->btvc", adj, support)
        return out


class STGCNBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, dropout: float = 0.2):
        super().__init__()
        self.gcn = GraphConv(in_channels, out_channels)
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=(9, 1), padding=(4, 0), stride=(stride, 1)),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout),
        )
        self.relu = nn.ReLU(inplace=True)
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.residual = nn.Identity()

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T, V)
        res = self.residual(x)
        # Permute for GCN: (B, T, V, C)
        x_perm = x.permute(0, 2, 3, 1)
        x_gcn = self.gcn(x_perm, adj)
        # Permute back for TCN: (B, C, T, V)
        x_gcn = x_gcn.permute(0, 3, 1, 2)
        x_tcn = self.tcn(x_gcn)
        return self.relu(x_tcn + res)


class STGCNClassifier(nn.Module):
    def __init__(self, num_nodes: int = 67, in_channels: int = 3, num_classes: int = 50):
        super().__init__()
        self.num_nodes = num_nodes
        # Default adjacency matrix: self-connections + uniform normalized
        adj = torch.eye(num_nodes) + 0.1 * torch.ones(num_nodes, num_nodes)
        row_sum = adj.sum(dim=1, keepdim=True)
        self.register_buffer("adj", adj / row_sum)

        self.block1 = STGCNBlock(in_channels, 64)
        self.block2 = STGCNBlock(64, 128, stride=2)
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(128, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x input can be (B, 60, 201) -> reshape to (B, 3, 60, 67)
        B, T, D = x.shape
        x = x.view(B, T, self.num_nodes, 3).permute(0, 3, 1, 2)  # (B, C, T, V)
        out = self.block1(x, self.adj)
        out = self.block2(out, self.adj)
        logits = self.classifier(out)
        return logits
