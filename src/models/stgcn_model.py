"""
Complete ST-GCN Network for Vietnamese Sign Language Recognition
Features:
- Anatomical 67-joint graph topology (VSLGraph) with spatial configuration partitioning.
- Dynamic edge importance weighting.
- Full joint and temporal mask integration.
- Hardware-efficient for NVIDIA RTX 3050 4GB GPU.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Dict, Any

from src.models.graph import VSLGraph
from src.models.stgcn import STGCNBlock


class STGCNModel(nn.Module):
    """
    Spatio-Temporal Graph Convolutional Network for VSLR.
    Input:
      - sequences: [B, T, V, C]
      - joint_masks: [B, T, V]
      - temporal_masks: [B, T]
    Output:
      - logits: [B, num_classes]
    """
    def __init__(
        self,
        num_joints: int = 67,
        in_channels: int = 3,
        num_classes: int = 50,
        graph_strategy: str = "spatial",
        channel_dims: Optional[List[int]] = None,
        dropout: float = 0.25,
        temporal_kernel_size: int = 9,
    ):
        super().__init__()
        self.num_joints = num_joints
        self.in_channels = in_channels
        self.num_classes = num_classes

        # 1. Graph Topology and Adjacency Matrix [K, V, V]
        self.graph = VSLGraph(strategy=graph_strategy)
        A = self.graph.get_adjacency()  # [3, 67, 67]
        self.register_buffer("A", A)

        # 2. Input Data Batch Normalization: [B, C*V, T]
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)

        # 3. Stacked ST-GCN Blocks
        # Default compact architecture: 64 -> 64 -> 128
        if channel_dims is None:
            channel_dims = [64, 64, 128]

        self.blocks = nn.ModuleList()
        current_in = in_channels

        for i, c_out in enumerate(channel_dims):
            # Apply stride 2 on the transition to higher channels (e.g. block 3) if sequence is long
            stride = 1
            block = STGCNBlock(
                in_channels=current_in,
                out_channels=c_out,
                A=A,
                stride=stride,
                temporal_kernel_size=temporal_kernel_size,
                dropout=dropout,
            )
            self.blocks.append(block)
            current_in = c_out

        final_channels = channel_dims[-1]

        # 4. Classifier Head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(final_channels, num_classes),
        )

    def forward(
        self,
        sequences: torch.Tensor,
        joint_masks: Optional[torch.Tensor] = None,
        temporal_masks: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            sequences: [B, T, V, C]
            joint_masks: [B, T, V]
            temporal_masks: [B, T]
        Returns:
            logits: [B, num_classes]
        """
        B, T, V, C = sequences.shape

        # Initial joint mask application
        if joint_masks is not None:
            sequences = sequences * joint_masks.unsqueeze(-1)

        # Data normalization: permute to [B, C*V, T]
        x_norm = sequences.permute(0, 3, 2, 1).contiguous().view(B, C * V, T)
        x_norm = self.data_bn(x_norm)

        # Reshape to [B, C, T, V] for ST-GCN
        x = x_norm.view(B, C, V, T).permute(0, 1, 3, 2).contiguous()  # [B, C, T, V]

        # Forward through ST-GCN Blocks
        for block in self.blocks:
            x = block(x, joint_mask=joint_masks)  # [B, C_curr, T, V]

        # --- Masked Global Pooling ---
        # 1. Masked Spatial Pooling over V: [B, C, T, V] -> [B, C, T]
        if joint_masks is not None:
            # joint_masks shape: [B, T, V] -> unsqueeze to [B, 1, T, V]
            jm = joint_masks.unsqueeze(1)
            spatial_denom = jm.sum(dim=-1).clamp(min=1e-6)  # [B, 1, T]
            x_spat = (x * jm).sum(dim=-1) / spatial_denom    # [B, C, T]
        else:
            x_spat = x.mean(dim=-1)  # [B, C, T]

        # 2. Masked Temporal Pooling over T: [B, C, T] -> [B, C]
        if temporal_masks is not None:
            # temporal_masks shape: [B, T] -> unsqueeze to [B, 1, T]
            tm = temporal_masks.unsqueeze(1)
            temp_denom = tm.sum(dim=-1).clamp(min=1e-6)  # [B, 1]
            x_pool = (x_spat * tm).sum(dim=-1) / temp_denom  # [B, C]
        else:
            x_pool = x_spat.mean(dim=-1)  # [B, C]

        # 3. Classifier Projection: [B, C] -> [B, num_classes]
        logits = self.classifier(x_pool)

        return logits
