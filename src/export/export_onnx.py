"""
ONNX Model Export Script for Vietnamese Sign Language Recognition (Phase 13).
Exports PyTorch trained models (ST-GCN and Transformer) to standard ONNX format (opset 14),
applies constant folding, checks validity via onnx.checker, and validates numerical parity (<1e-4).
"""

import os
import sys
import argparse
import json
from typing import Tuple, List, Dict, Any

import torch
import numpy as np
import onnx
import onnxruntime as ort

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel


def load_classes(classes_path: str = "configs/tier1_classes.txt") -> List[str]:
    """Loads 50-class tier1 vocabulary."""
    with open(classes_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def export_stgcn_to_onnx(
    checkpoint_path: str = "checkpoints/stgcn_best.pt",
    output_path: str = "checkpoints/stgcn_best.onnx",
    classes_path: str = "configs/tier1_classes.txt",
    opset_version: int = 14,
    dynamic_batch: bool = True,
) -> Dict[str, Any]:
    """
    Exports ST-GCN model to ONNX.
    """
    print("=" * 64)
    print(f"[ONNX Export] Exporting ST-GCN Model from: {checkpoint_path}")
    print("=" * 64)

    classes = load_classes(classes_path)
    num_classes = len(classes)

    # 1. Initialize PyTorch model and load weights
    model = STGCNModel(
        num_joints=67,
        in_channels=3,
        num_classes=num_classes,
        channel_dims=[64, 64, 128],
        dropout=0.0,
    )
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict)
    model.eval()

    # 2. Prepare dummy inputs [B=1, T=60, V=67, C=3]
    dummy_seq = torch.randn(1, 60, 67, 3, dtype=torch.float32)
    dummy_jm = torch.ones(1, 60, 67, dtype=torch.float32)
    dummy_tm = torch.ones(1, 60, dtype=torch.float32)

    # Dynamic axes configuration
    dynamic_axes = {
        "sequence": {0: "batch_size"},
        "joint_mask": {0: "batch_size"},
        "temporal_mask": {0: "batch_size"},
        "logits": {0: "batch_size"},
    } if dynamic_batch else None

    # 3. Export to ONNX
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    torch.onnx.export(
        model,
        (dummy_seq, dummy_jm, dummy_tm),
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["sequence", "joint_mask", "temporal_mask"],
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
    )
    print(f"  -> Successfully exported ONNX model to: {output_path}")

    # 4. Verify with onnx.checker
    print("  -> Verifying ONNX model structure with onnx.checker...")
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print("  -> onnx.checker verification PASSED!")

    # 5. Verify numerical consistency between PyTorch and ONNX Runtime
    print("  -> Verifying numerical parity (< 1e-4 tolerance)...")
    sess = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    
    with torch.no_grad():
        py_logits = model(dummy_seq, dummy_jm, dummy_tm).numpy()

    onnx_inputs = {
        "sequence": dummy_seq.numpy(),
        "joint_mask": dummy_jm.numpy(),
        "temporal_mask": dummy_tm.numpy(),
    }
    onnx_logits = sess.run(["logits"], onnx_inputs)[0]

    max_abs_diff = float(np.max(np.abs(py_logits - onnx_logits)))
    mean_abs_diff = float(np.mean(np.abs(py_logits - onnx_logits)))
    print(f"  -> Max Abs Difference: {max_abs_diff:.7e}")
    print(f"  -> Mean Abs Difference: {mean_abs_diff:.7e}")
    assert max_abs_diff < 1e-4, f"Numerical divergence exceeded 1e-4: {max_abs_diff}"
    print("  -> Parity verification PASSED!")

    pt_size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
    onnx_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  -> File size: PyTorch {pt_size_mb:.2f} MB -> ONNX {onnx_size_mb:.2f} MB ({(1 - onnx_size_mb/pt_size_mb)*100:.1f}% reduction)")

    return {
        "model": "STGCNModel",
        "checkpoint_pt": checkpoint_path,
        "checkpoint_onnx": output_path,
        "pt_size_mb": round(pt_size_mb, 2),
        "onnx_size_mb": round(onnx_size_mb, 2),
        "max_abs_diff": max_abs_diff,
        "opset_version": opset_version,
    }


def export_transformer_to_onnx(
    checkpoint_path: str = "checkpoints/transformer_best.pt",
    output_path: str = "checkpoints/transformer_best.onnx",
    classes_path: str = "configs/tier1_classes.txt",
    opset_version: int = 14,
    dynamic_batch: bool = True,
) -> Dict[str, Any]:
    """
    Exports Transformer model to ONNX.
    """
    print("\n" + "=" * 64)
    print(f"[ONNX Export] Exporting Transformer Model from: {checkpoint_path}")
    print("=" * 64)

    classes = load_classes(classes_path)
    num_classes = len(classes)

    model = TransformerModel(
        num_joints=67,
        coord_dim=3,
        d_model=128,
        nhead=4,
        dim_feedforward=256,
        num_layers=2,
        num_classes=num_classes,
        dropout=0.0,
        pos_encoding="sinusoidal",
        pooling_type="attention",
        norm_first=True,
    )
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict)
    model.eval()

    dummy_seq = torch.randn(1, 60, 67, 3, dtype=torch.float32)
    dummy_jm = torch.ones(1, 60, 67, dtype=torch.float32)
    dummy_tm = torch.ones(1, 60, dtype=torch.float32)

    dynamic_axes = {
        "sequence": {0: "batch_size"},
        "joint_mask": {0: "batch_size"},
        "temporal_mask": {0: "batch_size"},
        "logits": {0: "batch_size"},
    } if dynamic_batch else None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    torch.onnx.export(
        model,
        (dummy_seq, dummy_jm, dummy_tm),
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["sequence", "joint_mask", "temporal_mask"],
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
    )
    print(f"  -> Successfully exported ONNX model to: {output_path}")

    print("  -> Verifying ONNX model structure with onnx.checker...")
    onnx_model = onnx.load(output_path)
    onnx.checker.check_model(onnx_model)
    print("  -> onnx.checker verification PASSED!")

    print("  -> Verifying numerical parity (< 1e-4 tolerance)...")
    sess = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    with torch.no_grad():
        py_logits = model(dummy_seq, dummy_jm, dummy_tm).numpy()

    onnx_inputs = {
        "sequence": dummy_seq.numpy(),
        "joint_mask": dummy_jm.numpy(),
        "temporal_mask": dummy_tm.numpy(),
    }
    onnx_logits = sess.run(["logits"], onnx_inputs)[0]

    max_abs_diff = float(np.max(np.abs(py_logits - onnx_logits)))
    mean_abs_diff = float(np.mean(np.abs(py_logits - onnx_logits)))
    print(f"  -> Max Abs Difference: {max_abs_diff:.7e}")
    print(f"  -> Mean Abs Difference: {mean_abs_diff:.7e}")
    assert max_abs_diff < 1e-4, f"Numerical divergence exceeded 1e-4: {max_abs_diff}"
    print("  -> Parity verification PASSED!")

    pt_size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
    onnx_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  -> File size: PyTorch {pt_size_mb:.2f} MB -> ONNX {onnx_size_mb:.2f} MB ({(1 - onnx_size_mb/pt_size_mb)*100:.1f}% reduction)")

    return {
        "model": "TransformerModel",
        "checkpoint_pt": checkpoint_path,
        "checkpoint_onnx": output_path,
        "pt_size_mb": round(pt_size_mb, 2),
        "onnx_size_mb": round(onnx_size_mb, 2),
        "max_abs_diff": max_abs_diff,
        "opset_version": opset_version,
    }


def main():
    parser = argparse.ArgumentParser(description="Export VSL Models to ONNX format.")
    parser.add_argument("--model", type=str, default="all", choices=["stgcn", "transformer", "all"], help="Model to export")
    parser.add_argument("--opset", type=int, default=14, help="ONNX Opset version (default: 14)")
    args = parser.parse_args()

    results = {}
    if args.model in ["stgcn", "all"]:
        results["stgcn"] = export_stgcn_to_onnx(opset_version=args.opset)
    if args.model in ["transformer", "all"]:
        results["transformer"] = export_transformer_to_onnx(opset_version=args.opset)

    print("\n" + "=" * 64)
    print(">>> ONNX EXPORT COMPLETED FOR ALL REQUESTED MODELS <<<")
    print("=" * 64)


if __name__ == "__main__":
    main()
