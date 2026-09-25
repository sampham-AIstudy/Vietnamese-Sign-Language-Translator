"""
Continuous Sign Language Recognition (CSLR) Baseline Architecture: ST-GCN + BiGRU

Architecture:
1. Spatial Backbone:
   - Anatomical 67-joint VSLGraph topology with spatial configuration partitioning.
   - Batch normalization on input coordinates [B, C*V, T].
   - Stacked ST-GCN blocks (channels: 64 -> 64 -> 128).
   - Can load pretrained weights from isolated VSLR ST-GCN (checkpoints/stgcn_best.pt).
2. Spatial Masked Pooling:
   - Collapses 67 joints via masked average: [B, 128, T, 67] -> [B, 128, T].
3. Optional Temporal Downsampler:
   - 1D Temporal Convolution (stride 1 or stride 2).
4. Temporal Sequence Encoder:
   - Bidirectional GRU (2 layers, hidden dimension 256 -> 512 total output).
   - Dropout 0.3 for sequence regularization.
5. Linear CTC Projection Head:
   - Linear(512, num_classes) projecting to CTC vocabulary (including blank=0).
   - Outputs log-probabilities [T_out, B, num_classes] for PyTorch nn.CTCLoss.
"""

import os
from typing import Optional, List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.models.graph import VSLGraph
from src.models.stgcn import STGCNBlock


class STGCNBiGRU_CSLR(nn.Module):
    """
    ST-GCN + BiGRU model for Continuous Sign Language Recognition (CSLR) trained with CTC loss.
    
    Args:
        num_joints: Number of skeletal joints (default: 67).
        in_channels: Landmark coordinate dimensions (default: 3 for x, y, z).
        num_classes: Size of vocabulary including CTC blank (0) and UNK (1). Default: 372.
        graph_strategy: Adjacency partitioning strategy ("spatial").
        channel_dims: Channels for ST-GCN blocks (default: [64, 64, 128]).
        temporal_downsample: Temporal stride / downsampling factor (1 or 2). Default: 2.
        hidden_size: Hidden dimension per GRU direction (default: 256).
        num_gru_layers: Number of stacked BiGRU layers (default: 2).
        dropout: Dropout rate across GCN, GRU, and classifier (default: 0.3).
        pretrained_path: Optional path to pretrained isolated ST-GCN checkpoint.
    """
    def __init__(
        self,
        num_joints: int = 67,
        in_channels: int = 3,
        num_classes: int = 372,
        graph_strategy: str = "spatial",
        channel_dims: Optional[List[int]] = None,
        temporal_downsample: int = 2,
        hidden_size: int = 256,
        num_gru_layers: int = 2,
        dropout: float = 0.3,
        pretrained_path: Optional[str] = None,
    ):
        super().__init__()
        self.num_joints = num_joints
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.temporal_downsample_factor = temporal_downsample

        if channel_dims is None:
            channel_dims = [64, 64, 128]

        # 1. Graph Topology and Normalized Adjacency [3, 67, 67]
        self.graph = VSLGraph(strategy=graph_strategy)
        A = self.graph.get_adjacency()
        self.register_buffer("A", A)

        # 2. Input Data Batch Normalization: [B, C*V, T]
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)

        # 3. Stacked Spatial-Temporal GCN Blocks (stride=1 to preserve exact pretraining weights)
        self.blocks = nn.ModuleList()
        current_in = in_channels
        for c_out in channel_dims:
            block = STGCNBlock(
                in_channels=current_in,
                out_channels=c_out,
                A=A,
                stride=1,
                temporal_kernel_size=9,
                dropout=dropout,
            )
            self.blocks.append(block)
            current_in = c_out

        final_spatial_dim = channel_dims[-1]

        # 4. Optional Temporal Downsampler
        if self.temporal_downsample_factor == 2:
            self.temporal_downsample = nn.Sequential(
                nn.Conv1d(
                    final_spatial_dim,
                    final_spatial_dim,
                    kernel_size=3,
                    stride=2,
                    padding=1,
                    bias=False,
                ),
                nn.BatchNorm1d(final_spatial_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
            )
        elif self.temporal_downsample_factor == 1:
            self.temporal_downsample = nn.Identity()
        else:
            raise ValueError(f"temporal_downsample must be 1 or 2, got {temporal_downsample}")

        # 5. Temporal Sequence Encoder: Bidirectional GRU
        self.gru_dropout = nn.Dropout(dropout)
        self.bigru = nn.GRU(
            input_size=final_spatial_dim,
            hidden_size=hidden_size,
            num_layers=num_gru_layers,
            dropout=dropout if num_gru_layers > 1 else 0.0,
            bidirectional=True,
            batch_first=True,
        )

        # 6. CTC Linear Head: [2 * hidden_size] -> num_classes
        gru_out_dim = hidden_size * 2
        self.head_dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(gru_out_dim, num_classes)

        # 7. Optional Pretrained Weight Loading
        if pretrained_path is not None:
            self.load_pretrained_spatial_backbone(pretrained_path)

    def forward(
        self,
        sequences: torch.Tensor,
        joint_masks: Optional[torch.Tensor] = None,
        sequence_lengths: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for CSLR.
        
        Args:
            sequences: [B, T, V, C] landmark tensor.
            joint_masks: Optional [B, T, V] binary mask.
            sequence_lengths: Optional [B] tensor of original frame counts.
            
        Returns:
            log_probs: [T_out, B, num_classes] tensor of log-probabilities for nn.CTCLoss.
            out_lengths: [B] tensor of output frame counts after temporal downsampling.
        """
        B, T, V, C = sequences.shape

        # Initial joint mask application
        if joint_masks is not None:
            sequences = sequences * joint_masks.unsqueeze(-1)

        # Permute to [B, C*V, T] for data_bn
        x_norm = sequences.permute(0, 3, 2, 1).contiguous().view(B, C * V, T)
        x_norm = self.data_bn(x_norm)

        # Reshape to [B, C, T, V] for ST-GCN
        x = x_norm.view(B, C, V, T).permute(0, 1, 3, 2).contiguous()

        # Pass through ST-GCN blocks: output [B, 128, T, V]
        for block in self.blocks:
            x = block(x, joint_mask=joint_masks)

        # Masked spatial pooling over V: [B, 128, T, V] -> [B, 128, T]
        if joint_masks is not None:
            jm = joint_masks.unsqueeze(1)  # [B, 1, T, V]
            denom = jm.sum(dim=-1).clamp(min=1e-6)  # [B, 1, T]
            x_spat = (x * jm).sum(dim=-1) / denom  # [B, 128, T]
        else:
            x_spat = x.mean(dim=-1)  # [B, 128, T]

        # Temporal downsampling: [B, 128, T] -> [B, 128, T_out]
        x_down = self.temporal_downsample(x_spat)
        B_curr, C_curr, T_out = x_down.shape

        # Compute output sequence lengths
        if sequence_lengths is not None:
            if self.temporal_downsample_factor == 2:
                # Conv1d(k=3, s=2, p=1): L_out = (L_in + 1) // 2
                out_lengths = (sequence_lengths + 1) // 2
            else:
                out_lengths = sequence_lengths.clone()
        else:
            out_lengths = torch.full((B,), T_out, dtype=torch.long, device=sequences.device)

        # Permute to [B, T_out, C_curr] for BiGRU
        x_gru = x_down.permute(0, 2, 1).contiguous()
        x_gru = self.gru_dropout(x_gru)

        # Pack sequence for efficient and correct recurrent computation
        if sequence_lengths is not None and sequences.device.type != "mps":
            out_lens_cpu = out_lengths.cpu().to(torch.int64)
            # Ensure lengths are positive
            out_lens_cpu = torch.clamp(out_lens_cpu, min=1)
            packed_x = nn.utils.rnn.pack_padded_sequence(
                x_gru, out_lens_cpu, batch_first=True, enforce_sorted=False
            )
            packed_out, _ = self.bigru(packed_x)
            gru_out, _ = nn.utils.rnn.pad_packed_sequence(
                packed_out, batch_first=True, total_length=T_out
            )
        else:
            gru_out, _ = self.bigru(x_gru)

        # Classifier head: [B, T_out, 2*hidden_size] -> [B, T_out, num_classes]
        gru_out = self.head_dropout(gru_out)
        logits = self.fc(gru_out)

        # PyTorch nn.CTCLoss expects [T_out, B, num_classes] log-probabilities
        log_probs = F.log_softmax(logits, dim=-1).permute(1, 0, 2).contiguous()

        return log_probs, out_lengths

    def load_pretrained_spatial_backbone(
        self,
        checkpoint_path: str,
        freeze: bool = False,
    ) -> Dict[str, Any]:
        """
        Loads pretrained weights from the isolated sign ST-GCN checkpoint.
        Transfers: data_bn and blocks.0..2.
        Skips: isolated classifier head.
        
        Args:
            checkpoint_path: Path to .pt checkpoint file.
            freeze: If True, freezes the spatial backbone weights (requires_grad=False).
            
        Returns:
            Dict summarizing loaded keys, skipped keys, and parameter count.
        """
        if not os.path.isfile(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        ckpt = torch.load(checkpoint_path, map_location="cpu")
        state_dict = ckpt.get("model_state_dict", ckpt)

        model_dict = self.state_dict()
        transferred_keys = []
        skipped_keys = []
        transferred_params = 0

        for k, v in state_dict.items():
            if (k.startswith("data_bn.") or k.startswith("blocks.")) and k in model_dict:
                if model_dict[k].shape == v.shape:
                    model_dict[k].copy_(v)
                    transferred_keys.append(k)
                    transferred_params += v.numel()
                else:
                    skipped_keys.append(f"{k} (shape mismatch: {model_dict[k].shape} vs {v.shape})")
            else:
                skipped_keys.append(k)

        if freeze:
            for name, param in self.named_parameters():
                if name.startswith("data_bn.") or name.startswith("blocks."):
                    param.requires_grad = False

        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)

        return {
            "checkpoint_path": checkpoint_path,
            "transferred_keys_count": len(transferred_keys),
            "skipped_keys_count": len(skipped_keys),
            "transferred_params": transferred_params,
            "total_params": total_params,
            "trainable_params": trainable_params,
            "backbone_frozen": freeze,
        }
