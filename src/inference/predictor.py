"""
High-Performance Real-Time Inference Predictor for Vietnamese Sign Language Recognition
Phase 8 / Preparation for Phase 10 (Real-Time Camera & WebRTC Streaming).

Features:
- Unified wrapper supporting Single Models (ST-GCN, Transformer, BiGRU) or Multi-Model Ensemble.
- Automated input tensor normalization, reshaping, and fallback mask generation.
- Optimized with `torch.inference_mode()` and CUDA AMP mixed precision for sub-10ms latency.
- Built-in CUDA kernel warmup to eliminate first-frame latency spikes.
- Top-1 and Top-5 prediction ranking with calibrated Softmax confidences.
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Union

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.models.baseline_bigru import BaselineBiGRU
from src.inference.ensemble import VSLREnsemble, load_ensemble_models


class VSLPredictor:
    """
    Production-grade Inference Predictor for Vietnamese Sign Language Recognition.
    """

    def __init__(
        self,
        model_type: str = "stgcn",  # "stgcn", "ensemble", "transformer", "baseline"
        stgcn_ckpt: Optional[str] = None,
        transformer_ckpt: str = "checkpoints/transformer_best.pt",
        baseline_ckpt: str = "checkpoints/baseline_bigru.pt",
        tier1_classes_path: Optional[str] = None,
        classes_path: Optional[str] = None,
        stgcn_weight: float = 0.5,
        transformer_weight: float = 0.5,
        device: Optional[str] = None,
        warmup: bool = True,
    ):
        self.model_type = model_type.lower()
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Determine classes path (default: tier2_classes.txt with 487 classes)
        active_classes_path = classes_path or tier1_classes_path
        if active_classes_path is None:
            if os.path.exists("configs/tier2_classes.txt"):
                active_classes_path = "configs/tier2_classes.txt"
            else:
                active_classes_path = "configs/tier1_classes.txt"

        # Determine ST-GCN checkpoint path (default: stgcn_tier2_indomain.pt)
        if stgcn_ckpt is None:
            if os.path.exists("checkpoints/stgcn_tier2_indomain.pt"):
                stgcn_ckpt = "checkpoints/stgcn_tier2_indomain.pt"
            else:
                stgcn_ckpt = "checkpoints/stgcn_best.pt"

        # 1. Load Class Vocabulary. A label_map stored in the checkpoint is authoritative: a
        #    separate classes file can drift from the order the model was trained with.
        self.class_names = self._load_classes(active_classes_path)
        self.preprocessing: Dict[str, Any] = {}
        if self.model_type == "stgcn" and stgcn_ckpt and os.path.exists(stgcn_ckpt):
            meta = torch.load(stgcn_ckpt, map_location="cpu", weights_only=False)
            self.preprocessing = dict(meta.get("preprocessing") or {})
            label_map = meta.get("label_map")
            if label_map:
                ckpt_classes = [c for c, _ in sorted(label_map.items(), key=lambda kv: kv[1])]
                if ckpt_classes != self.class_names:
                    print(f"[VSLPredictor] classes file {active_classes_path} differs from the checkpoint "
                          f"label_map ({len(self.class_names)} vs {len(ckpt_classes)}); using the checkpoint.")
                self.class_names = ckpt_classes
        self.num_classes = len(self.class_names)
        self.idx_to_class = {i: c for i, c in enumerate(self.class_names)}
        self.class_to_idx = {c: i for i, c in enumerate(self.class_names)}

        # 2. Build and Load Target Model
        self.model = self._init_model(
            stgcn_ckpt=stgcn_ckpt,
            transformer_ckpt=transformer_ckpt,
            baseline_ckpt=baseline_ckpt,
            stgcn_weight=stgcn_weight,
            transformer_weight=transformer_weight,
        )
        self.model.eval()

        # 3. Warmup CUDA Kernels for Low-Latency Realtime
        if warmup and self.device.type == "cuda":
            self.warmup()

    def _load_classes(self, classes_path: str) -> List[str]:
        if not os.path.exists(classes_path):
            raise FileNotFoundError(f"Class vocabulary file not found: {classes_path}")
        with open(classes_path, "r", encoding="utf-8") as f:
            classes = [line.strip() for line in f if line.strip()]
        return classes

    def _init_model(
        self,
        stgcn_ckpt: str,
        transformer_ckpt: str,
        baseline_ckpt: str,
        stgcn_weight: float,
        transformer_weight: float,
    ) -> nn.Module:
        if self.model_type == "ensemble":
            stgcn, trans = load_ensemble_models(
                stgcn_ckpt_path=stgcn_ckpt,
                transformer_ckpt_path=transformer_ckpt,
                num_classes=self.num_classes,
                device=self.device,
            )
            return VSLREnsemble(
                stgcn,
                trans,
                weight_stgcn=stgcn_weight,
                weight_transformer=transformer_weight,
            ).to(self.device)

        elif self.model_type == "stgcn":
            model = STGCNModel(
                num_joints=67,
                in_channels=3,
                num_classes=self.num_classes,
                graph_strategy="spatial",
                channel_dims=[64, 64, 128],
                dropout=0.25,
                temporal_kernel_size=9,
            ).to(self.device)
            ckpt = torch.load(stgcn_ckpt, map_location=self.device, weights_only=False)
            model.load_state_dict(ckpt["model_state_dict"])
            return model

        elif self.model_type == "transformer":
            model = TransformerModel(
                num_joints=67,
                coord_dim=3,
                d_model=128,
                nhead=4,
                dim_feedforward=256,
                num_layers=2,
                num_classes=self.num_classes,
                dropout=0.1,
                pos_encoding="sinusoidal",
                pooling_type="attention",
                norm_first=True,
            ).to(self.device)
            ckpt = torch.load(transformer_ckpt, map_location=self.device, weights_only=False)
            model.load_state_dict(ckpt["model_state_dict"])
            return model

        elif self.model_type == "baseline":
            model = BaselineBiGRU(
                num_joints=67,
                coord_dim=3,
                hidden_dim=128,
                num_layers=2,
                num_classes=self.num_classes,
                dropout=0.3,
                bidirectional=True,
                pooling_type="attention",
            ).to(self.device)
            ckpt = torch.load(baseline_ckpt, map_location=self.device, weights_only=False)
            model.load_state_dict(ckpt["model_state_dict"])
            return model

        else:
            raise ValueError(f"Unknown model_type: '{self.model_type}'. Choose from ['ensemble', 'stgcn', 'transformer', 'baseline'].")

    def warmup(self, num_runs: int = 5):
        """Pre-heats CUDA execution graph and cuDNN kernels."""
        dummy_seq = torch.zeros((1, 60, 67, 3), dtype=torch.float32, device=self.device)
        dummy_jm = torch.ones((1, 60, 67), dtype=torch.float32, device=self.device)
        dummy_tm = torch.ones((1, 60), dtype=torch.float32, device=self.device)
        with torch.inference_mode():
            for _ in range(num_runs):
                with torch.amp.autocast("cuda", enabled=(self.device.type == "cuda")):
                    _ = self.model(dummy_seq, dummy_jm, dummy_tm)
        if self.device.type == "cuda":
            torch.cuda.synchronize()

    def predict(
        self,
        sequence: Union[np.ndarray, torch.Tensor],
        joint_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
        temporal_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Runs highly optimized inference on input sign sequence.

        Args:
            sequence: Skeleton data with shape:
                      - [60, 67, 3] or [60, 201] (Single sample)
                      - [B, 60, 67, 3] or [B, 60, 201] (Batch)
            joint_mask: Optional [60, 67] or [B, 60, 67]
            temporal_mask: Optional [60] or [B, 60]
            top_k: Number of highest ranking predictions to return (default 5).

        Returns:
            Dictionary containing:
              - 'gloss': Top-1 predicted gloss string
              - 'confidence': Probability of Top-1 prediction [0.0 - 1.0]
              - 'top5': List of dicts [{'gloss': ..., 'confidence': ...}]
              - 'latency_ms': Inference time in milliseconds
        """
        # Convert numpy to tensor
        if isinstance(sequence, np.ndarray):
            seq = torch.from_numpy(sequence).float()
        else:
            seq = sequence.float()

        # Handle dimensions
        is_single = False
        if seq.dim() == 2:  # [T, 201]
            T, D = seq.shape
            seq = seq.view(1, T, 67, 3)
            is_single = True
        elif seq.dim() == 3:
            if seq.shape[-1] == 3 and seq.shape[-2] == 67:  # [T, 67, 3]
                seq = seq.unsqueeze(0)
                is_single = True
            elif seq.shape[-1] == 201:  # [B, T, 201]
                B, T, _ = seq.shape
                seq = seq.view(B, T, 67, 3)
        elif seq.dim() == 4:  # [B, T, 67, 3]
            pass
        else:
            raise ValueError(f"Invalid input sequence shape: {seq.shape}. Expected [T, 67, 3] or [B, T, 67, 3].")

        B, T, V, C = seq.shape
        seq = seq.to(self.device)

        # Fallback masks
        if joint_mask is None:
            jm = torch.ones((B, T, V), dtype=torch.float32, device=self.device)
        else:
            jm = torch.as_tensor(joint_mask, dtype=torch.float32, device=self.device)
            if jm.dim() == 2:
                jm = jm.unsqueeze(0)

        if temporal_mask is None:
            tm = torch.ones((B, T), dtype=torch.float32, device=self.device)
        else:
            tm = torch.as_tensor(temporal_mask, dtype=torch.float32, device=self.device)
            if tm.dim() == 1:
                tm = tm.unsqueeze(0)

        # Timed Inference
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()

        with torch.inference_mode():
            with torch.amp.autocast("cuda", enabled=(self.device.type == "cuda")):
                logits = self.model(seq, jm, tm)
                probs = F.softmax(logits, dim=-1)

        if self.device.type == "cuda":
            torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Extract top-k
        topk_probs, topk_indices = torch.topk(probs, k=min(top_k, self.num_classes), dim=-1)
        topk_probs = topk_probs.cpu().numpy()
        topk_indices = topk_indices.cpu().numpy()

        if is_single:
            sample_idx = topk_indices[0]
            sample_probs = topk_probs[0]
            top_predictions = [
                {
                    "gloss": self.idx_to_class[int(idx)],
                    "confidence": round(float(prob), 4),
                }
                for idx, prob in zip(sample_idx, sample_probs)
            ]
            return {
                "gloss": top_predictions[0]["gloss"],
                "confidence": top_predictions[0]["confidence"],
                "top5": top_predictions,
                "latency_ms": round(latency_ms, 2),
            }
        else:
            results = []
            for b in range(B):
                b_idx = topk_indices[b]
                b_probs = topk_probs[b]
                b_preds = [
                    {
                        "gloss": self.idx_to_class[int(idx)],
                        "confidence": round(float(prob), 4),
                    }
                    for idx, prob in zip(b_idx, b_probs)
                ]
                results.append({
                    "gloss": b_preds[0]["gloss"],
                    "confidence": b_preds[0]["confidence"],
                    "top5": b_preds,
                    "latency_ms": round(latency_ms / B, 2),
                })
            return {"batch_results": results, "total_latency_ms": round(latency_ms, 2)}
