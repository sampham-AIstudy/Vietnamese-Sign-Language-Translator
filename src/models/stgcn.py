"""
Spatio-Temporal Graph Convolutional Block (ST-GCN)
Follows Yan et al. (AAAI 2018) with joint and temporal masking extensions.

Components:
  - SpatialGraphConv: Multi-partition spatial convolution with learnable edge importance weighting.
  - STGCNBlock: Spatial GCN + Temporal Conv + Mask Injection + Residual Connection.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class SpatialGraphConv(nn.Module):
    """
    Spatial Graph Convolution layer.
    Computes: X_out = sum_k ( (X_in * (A_k * M_k)) W_k )
    Where:
      - A_k: [V, V] normalized spatial partition adjacency
      - M_k: [V, V] learnable edge importance weight (initialized to 1.0)
      - W_k: 1x1 convolution projecting C_in -> C_out
    """
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_subsets: int = 3,
        num_nodes: int = 67,
    ):
        super().__init__()
        self.num_subsets = num_subsets
        self.num_nodes = num_nodes
        self.in_channels = in_channels
        self.out_channels = out_channels

        # 1x1 2D Conv for each partition: kernel=(1, 1) over [T, V]
        self.conv = nn.Conv2d(
            in_channels,
            out_channels * num_subsets,
            kernel_size=1,
            bias=True,
        )

        # Learnable edge importance weighting matrix M [K, V, V]
        self.edge_importance = nn.Parameter(torch.ones(num_subsets, num_nodes, num_nodes))

    def forward(self, x: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [B, C_in, T, V]
            A: Adjacency tensor of shape [K, V, V]
        Returns:
            out: Tensor of shape [B, C_out, T, V]
        """
        B, C_in, T, V = x.shape

        # Linear projection for all K subsets simultaneously: [B, K * C_out, T, V]
        x_proj = self.conv(x)
        # Reshape to [B, K, C_out, T, V]
        x_proj = x_proj.view(B, self.num_subsets, self.out_channels, T, V)

        # Apply learnable edge importance: A_eff = A * M  [K, V, V]
        A_eff = A * self.edge_importance

        # Multiply by adjacency for each partition k:
        # Einsum: b k c t v, k v w -> b c t w
        # Sum over subsets k and nodes v
        out = torch.einsum("bkctv,kvw->bctw", x_proj, A_eff)

        return out


class STGCNBlock(nn.Module):
    """
    Standard ST-GCN unit consisting of:
    1. Spatial Graph Convolution
    2. Batch Normalization & ReLU
    3. Joint Mask Multiplication (prevents missing joints from propagating noise)
    4. Temporal Convolution (TCN)
    5. Residual Connection
    """
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        A: torch.Tensor,  # [K, V, V]
        stride: int = 1,
        temporal_kernel_size: int = 9,
        dropout: float = 0.2,
    ):
        super().__init__()
        num_subsets, num_nodes, _ = A.shape
        self.register_buffer("A", A)
        self.stride = stride

        # 1. Spatial Graph Convolution
        self.gcn = SpatialGraphConv(
            in_channels=in_channels,
            out_channels=out_channels,
            num_subsets=num_subsets,
            num_nodes=num_nodes,
        )
        self.bn_gcn = nn.BatchNorm2d(out_channels)

        # 2. Temporal Convolution
        padding = (temporal_kernel_size - 1) // 2
        self.tcn = nn.Sequential(
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=(temporal_kernel_size, 1),
                padding=(padding, 0),
                stride=(stride, 1),
                bias=False,
            ),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout),
        )

        self.relu = nn.ReLU(inplace=True)

        # 3. Residual Connection
        if in_channels != out_channels or stride != 1:
            self.residual = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=(stride, 1),
                    bias=False,
                ),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.residual = nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        joint_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape [B, C_in, T, V]
            joint_mask: Optional binary tensor [B, T, V] (or [B, 1, T, V])
        Returns:
            out: Tensor of shape [B, C_out, T // stride, V]
        """
        res = self.residual(x)

        # Spatial Graph Convolution
        x_gcn = self.gcn(x, self.A)
        x_gcn = self.bn_gcn(x_gcn)
        x_gcn = self.relu(x_gcn)

        # Zero out missing joints to prevent noise propagation across graph edges
        if joint_mask is not None:
            if joint_mask.dim() == 3:
                mask = joint_mask.unsqueeze(1)  # [B, 1, T, V]
            else:
                mask = joint_mask
            x_gcn = x_gcn * mask

        # Temporal Convolution
        x_tcn = self.tcn(x_gcn)

        # Residual add + ReLU
        out = self.relu(x_tcn + res)

        # Re-apply mask after TCN if stride is 1 (if stride > 1, mask downsampling is handled by caller)
        if joint_mask is not None and self.stride == 1:
            out = out * mask

        return out
