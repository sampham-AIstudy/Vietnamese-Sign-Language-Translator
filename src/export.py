"""
Export Module: Converts PyTorch models to ONNX and TorchScript.
Provides optimized, dependency-free inference engines for production deployment.
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import torch
import numpy as np
from src.models.gru_classifier import BiGRUSequenceClassifier
from src.models.transformer_classifier import VSLTransformerClassifier
from src.models.alphabet_classifier import AlphabetMLP


def export_word_model(
    checkpoint_path: str = "experiments/word_model_bigru.pth",
    output_dir: str = "experiments",
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    model_type = checkpoint.get("model_type", "bigru")
    num_classes = checkpoint["num_classes"]
    idx_to_class = checkpoint["idx_to_class"]

    if model_type == "bigru":
        model = BiGRUSequenceClassifier(
            input_dim=201,
            hidden_dim=128,
            num_layers=2,
            num_classes=num_classes,
            bidirectional=True,
        )
    else:
        model = VSLTransformerClassifier(
            input_dim=201,
            d_model=128,
            nhead=4,
            num_layers=3,
            num_classes=num_classes,
        )

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dummy_input = torch.randn(1, 60, 201, dtype=torch.float32)

    # 1. Export TorchScript
    ts_path = os.path.join(output_dir, f"word_model_{model_type}.torchscript.pt")
    traced = torch.jit.trace(model, dummy_input)
    traced.save(ts_path)
    print(f"[Export] TorchScript model saved: {ts_path}")

    # 2. Export ONNX
    onnx_path = os.path.join(output_dir, f"word_model_{model_type}.onnx")
    try:
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            input_names=["sequence"],
            output_names=["logits"],
            dynamic_axes={"sequence": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=14,
            dynamo=False,
        )
        print(f"[Export] ONNX model saved: {onnx_path}")
    except Exception as e:
        print(f"[Warning] ONNX export failed with: {e}. TorchScript model is available at {ts_path}")

    # 3. Save class metadata
    meta_path = os.path.join(output_dir, f"word_model_{model_type}_classes.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(idx_to_class, f, ensure_ascii=False, indent=2)
    print(f"[Export] Class metadata saved: {meta_path}")


def export_alphabet_model(
    checkpoint_path: str = "experiments/alphabet_model.pth",
    output_dir: str = "experiments",
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    num_classes = checkpoint["num_classes"]
    class_to_idx = checkpoint["class_to_idx"]
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    model = AlphabetMLP(input_dim=42, num_classes=num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dummy_input = torch.randn(1, 42, dtype=torch.float32)

    # 1. Export TorchScript
    ts_path = os.path.join(output_dir, "alphabet_model.torchscript.pt")
    traced = torch.jit.trace(model, dummy_input)
    traced.save(ts_path)
    print(f"[Export] TorchScript model saved: {ts_path}")

    # 2. Export ONNX
    onnx_path = os.path.join(output_dir, "alphabet_model.onnx")
    try:
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            input_names=["keypoints"],
            output_names=["logits"],
            dynamic_axes={"keypoints": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=14,
            dynamo=False,
        )
        print(f"[Export] ONNX model saved: {onnx_path}")
    except Exception as e:
        print(f"[Warning] ONNX export failed with: {e}. TorchScript model is available at {ts_path}")

    # 3. Save class metadata
    meta_path = os.path.join(output_dir, "alphabet_model_classes.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(idx_to_class, f, ensure_ascii=False, indent=2)
    print(f"[Export] Class metadata saved: {meta_path}")


if __name__ == "__main__":
    if os.path.exists("experiments/word_model_bigru.pth"):
        export_word_model("experiments/word_model_bigru.pth")
    if os.path.exists("experiments/alphabet_model.pth"):
        export_alphabet_model("experiments/alphabet_model.pth")
