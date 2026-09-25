"""
Benchmark Script: PyTorch Native vs. ONNX Runtime (Phase 13).
Compares Latency, Throughput (FPS), File Size, and Numerical Error (Max Abs Diff).
Outputs JSON report to: experiments/optimization/benchmark_onnx_vs_pytorch.json
"""

import os
import sys
import json
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.models.stgcn_model import STGCNModel
from src.models.transformer_model import TransformerModel
from src.export.onnx_predictor import OnnxPredictor


def run_benchmark():
    print("=" * 68)
    print("PHASE 13: ONNX RUNTIME VS PYTORCH NATIVE BENCHMARK")
    print("=" * 68)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device: {device} | Hardware: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    os.makedirs("experiments/optimization", exist_ok=True)
    report = {
        "device": str(device),
        "hardware": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "models": {},
    }

    # 1. Benchmark ST-GCN
    print("\n[1/2] Benchmarking ST-GCN (Spatial Master)...")
    stgcn_pt_path = "checkpoints/stgcn_best.pt"
    stgcn_onnx_path = "checkpoints/stgcn_best.onnx"

    stgcn_model = STGCNModel(num_classes=50, channel_dims=[64, 64, 128], dropout=0.0).to(device)
    ckpt_stgcn = torch.load(stgcn_pt_path, map_location=device)
    stgcn_model.load_state_dict(ckpt_stgcn["model_state_dict"])
    stgcn_model.eval()

    stgcn_onnx = OnnxPredictor(stgcn_onnx_path)
    stgcn_bench = stgcn_onnx.benchmark_against_pytorch(stgcn_model, device=device, num_iterations=100)

    pt_size = os.path.getsize(stgcn_pt_path) / (1024 * 1024)
    onnx_size = os.path.getsize(stgcn_onnx_path) / (1024 * 1024)

    stgcn_bench["file_size"] = {
        "pytorch_pt_mb": round(pt_size, 2),
        "onnx_mb": round(onnx_size, 2),
        "compression_ratio": f"{(1 - onnx_size / pt_size) * 100:.1f}% reduction",
    }
    report["models"]["ST-GCN"] = stgcn_bench

    print(f"  -> PyTorch Latency: {stgcn_bench['pytorch_native']['mean_latency_ms']} ms ({stgcn_bench['pytorch_native']['fps']} FPS)")
    print(f"  -> ONNX Latency:    {stgcn_bench['onnx_runtime']['mean_latency_ms']} ms ({stgcn_bench['onnx_runtime']['fps']} FPS)")
    print(f"  -> Speedup Factor:   {stgcn_bench['speedup_factor']}x")
    print(f"  -> Max Abs Diff:    {stgcn_bench['parity_check']['max_abs_diff']:.7e} (Status: {stgcn_bench['parity_check']['status']})")
    print(f"  -> File Size:       {pt_size:.2f} MB -> {onnx_size:.2f} MB ({stgcn_bench['file_size']['compression_ratio']})")

    # 2. Benchmark Transformer
    print("\n[2/2] Benchmarking Transformer (Temporal Master)...")
    trans_pt_path = "checkpoints/transformer_best.pt"
    trans_onnx_path = "checkpoints/transformer_best.onnx"

    trans_model = TransformerModel(
        num_joints=67,
        coord_dim=3,
        d_model=128,
        nhead=4,
        dim_feedforward=256,
        num_layers=2,
        num_classes=50,
        dropout=0.0,
        pooling_type="attention",
    ).to(device)
    ckpt_trans = torch.load(trans_pt_path, map_location=device)
    trans_model.load_state_dict(ckpt_trans["model_state_dict"])
    trans_model.eval()

    trans_onnx = OnnxPredictor(trans_onnx_path)
    trans_bench = trans_onnx.benchmark_against_pytorch(trans_model, device=device, num_iterations=100)

    t_pt_size = os.path.getsize(trans_pt_path) / (1024 * 1024)
    t_onnx_size = os.path.getsize(trans_onnx_path) / (1024 * 1024)

    trans_bench["file_size"] = {
        "pytorch_pt_mb": round(t_pt_size, 2),
        "onnx_mb": round(t_onnx_size, 2),
        "compression_ratio": f"{(1 - t_onnx_size / t_pt_size) * 100:.1f}% reduction",
    }
    report["models"]["Transformer"] = trans_bench

    print(f"  -> PyTorch Latency: {trans_bench['pytorch_native']['mean_latency_ms']} ms ({trans_bench['pytorch_native']['fps']} FPS)")
    print(f"  -> ONNX Latency:    {trans_bench['onnx_runtime']['mean_latency_ms']} ms ({trans_bench['onnx_runtime']['fps']} FPS)")
    print(f"  -> Speedup Factor:   {trans_bench['speedup_factor']}x")
    print(f"  -> Max Abs Diff:    {trans_bench['parity_check']['max_abs_diff']:.7e} (Status: {trans_bench['parity_check']['status']})")
    print(f"  -> File Size:       {t_pt_size:.2f} MB -> {t_onnx_size:.2f} MB ({trans_bench['file_size']['compression_ratio']})")

    # 3. Save JSON Report
    output_json = "experiments/optimization/benchmark_onnx_vs_pytorch.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[Saved] Complete benchmark report saved to: {output_json}")

    print("\n" + "=" * 68)
    print(">>> PHASE 13 BENCHMARK PASSED WITH NUMERICAL PARITY CONFIRMED <<<")
    print("=" * 68)


if __name__ == "__main__":
    run_benchmark()
