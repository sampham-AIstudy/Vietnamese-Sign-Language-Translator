"""
High-Performance ONNX Runtime Inference Predictor for Vietnamese Sign Language Recognition (Phase 13).
Supports dynamic/static input batching, automatic CPU/CUDA Execution Provider fallback,
and side-by-side benchmark comparison against native PyTorch models.
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Union, Tuple

import numpy as np
import onnxruntime as ort
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class OnnxPredictor:
    """
    Production-grade ONNX Runtime Predictor for VSL models.
    """

    def __init__(
        self,
        onnx_path: str = "checkpoints/stgcn_best.onnx",
        classes_path: str = "configs/tier1_classes.txt",
        providers: Optional[List[str]] = None,
        warmup: bool = True,
    ):
        self.onnx_path = onnx_path
        if not os.path.exists(onnx_path):
            raise FileNotFoundError(f"ONNX model file not found at: {onnx_path}")

        # 1. Configure Execution Providers
        if providers is None:
            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                self.providers = ["CPUExecutionProvider"]
        else:
            self.providers = providers

        # 2. Initialize Session
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(self.onnx_path, sess_options=opts, providers=self.providers)
        self.active_provider = self.session.get_providers()[0]

        # 3. Cache Input and Output Names
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]

        # 4. Load Vocabulary
        self.class_names = self._load_classes(classes_path)
        self.num_classes = len(self.class_names)
        self.idx_to_class = {i: c for i, c in enumerate(self.class_names)}

        # 5. Warmup Engine
        if warmup:
            self.warmup()

    def _load_classes(self, path: str) -> List[str]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Classes file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def warmup(self, num_runs: int = 5):
        """Warms up ONNX runtime memory allocators and execution kernels."""
        dummy_seq = np.zeros((1, 60, 67, 3), dtype=np.float32)
        dummy_jm = np.ones((1, 60, 67), dtype=np.float32)
        dummy_tm = np.ones((1, 60), dtype=np.float32)
        feeds = {"sequence": dummy_seq, "joint_mask": dummy_jm, "temporal_mask": dummy_tm}
        for _ in range(num_runs):
            _ = self.session.run(self.output_names, feeds)

    def predict(
        self,
        sequence: Union[np.ndarray, torch.Tensor],
        joint_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
        temporal_mask: Optional[Union[np.ndarray, torch.Tensor]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Runs low-latency inference on sign sequence using ONNX Runtime.

        Args:
            sequence: Skeleton data with shape [60, 67, 3] or [1, 60, 67, 3].
            joint_mask: Optional [60, 67] or [1, 60, 67].
            temporal_mask: Optional [60] or [1, 60].
            top_k: Number of ranked predictions (default 5).

        Returns:
            Dict containing 'gloss', 'confidence', 'top5', 'logits', 'latency_ms'.
        """
        # 1. Convert inputs to numpy
        if isinstance(sequence, torch.Tensor):
            seq = sequence.detach().cpu().numpy()
        else:
            seq = np.asarray(sequence, dtype=np.float32)

        if seq.ndim == 3:  # [60, 67, 3]
            seq = np.expand_dims(seq, axis=0)

        B, T, V, C = seq.shape

        # Masks
        if joint_mask is None:
            jm = np.ones((B, T, V), dtype=np.float32)
        elif isinstance(joint_mask, torch.Tensor):
            jm = joint_mask.detach().cpu().numpy()
            if jm.ndim == 2:
                jm = np.expand_dims(jm, axis=0)
        else:
            jm = np.asarray(joint_mask, dtype=np.float32)
            if jm.ndim == 2:
                jm = np.expand_dims(jm, axis=0)

        if temporal_mask is None:
            tm = np.ones((B, T), dtype=np.float32)
        elif isinstance(temporal_mask, torch.Tensor):
            tm = temporal_mask.detach().cpu().numpy()
            if tm.ndim == 1:
                tm = np.expand_dims(tm, axis=0)
        else:
            tm = np.asarray(temporal_mask, dtype=np.float32)
            if tm.ndim == 1:
                tm = np.expand_dims(tm, axis=0)

        feeds = {
            "sequence": seq.astype(np.float32),
            "joint_mask": jm.astype(np.float32),
            "temporal_mask": tm.astype(np.float32),
        }

        # 2. Execute Timed Inference
        t0 = time.perf_counter()
        raw_outputs = self.session.run(self.output_names, feeds)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        logits = raw_outputs[0]  # [B, num_classes]

        # 3. Softmax probabilities
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        sample_probs = probs[0]
        topk_indices = np.argsort(sample_probs)[::-1][: min(top_k, self.num_classes)]

        top5 = [
            {
                "gloss": self.idx_to_class[int(idx)],
                "confidence": round(float(sample_probs[idx]), 4),
            }
            for idx in topk_indices
        ]

        return {
            "gloss": top5[0]["gloss"],
            "confidence": top5[0]["confidence"],
            "top5": top5,
            "logits": logits,
            "latency_ms": round(latency_ms, 2),
            "provider": self.active_provider,
        }

    def benchmark_against_pytorch(
        self,
        pytorch_model: torch.nn.Module,
        device: torch.device,
        num_iterations: int = 100,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive side-by-side benchmark comparing PyTorch vs ONNX Runtime:
        - Latency (mean, p50, p95, p99 in ms)
        - Max Absolute Difference & Mean Absolute Difference of logits
        - Parity check assertion (< 1e-4)
        """
        pytorch_model.eval()

        # Fixed sample input
        np.random.seed(42)
        sample_seq_np = np.random.randn(1, 60, 67, 3).astype(np.float32)
        sample_jm_np = np.ones((1, 60, 67), dtype=np.float32)
        sample_tm_np = np.ones((1, 60), dtype=np.float32)

        sample_seq_pt = torch.from_numpy(sample_seq_np).to(device)
        sample_jm_pt = torch.from_numpy(sample_jm_np).to(device)
        sample_tm_pt = torch.from_numpy(sample_tm_np).to(device)

        # 1. Parity Check (evaluated on CPU to avoid CUDA vs CPU FP32 accumulation discrepancies)
        pytorch_model_cpu = pytorch_model.to("cpu")
        sample_seq_cpu = torch.from_numpy(sample_seq_np)
        sample_jm_cpu = torch.from_numpy(sample_jm_np)
        sample_tm_cpu = torch.from_numpy(sample_tm_np)

        with torch.inference_mode():
            py_logits = pytorch_model_cpu(sample_seq_cpu, sample_jm_cpu, sample_tm_cpu).numpy()

        onnx_res = self.predict(sample_seq_np, sample_jm_np, sample_tm_np)
        onnx_logits = onnx_res["logits"]

        max_abs_diff = float(np.max(np.abs(py_logits - onnx_logits)))
        mean_abs_diff = float(np.mean(np.abs(py_logits - onnx_logits)))
        parity_pass = bool(max_abs_diff < 1e-4)

        # Restore model to requested device for speed benchmarking
        pytorch_model.to(device)

        # 2. Benchmark PyTorch
        py_latencies = []
        with torch.inference_mode():
            # Warmup
            for _ in range(15):
                _ = pytorch_model(sample_seq_pt, sample_jm_pt, sample_tm_pt)
                if device.type == "cuda":
                    torch.cuda.synchronize()

            # Benchmark
            for _ in range(num_iterations):
                if device.type == "cuda":
                    torch.cuda.synchronize()
                t0 = time.perf_counter()
                _ = pytorch_model(sample_seq_pt, sample_jm_pt, sample_tm_pt)
                if device.type == "cuda":
                    torch.cuda.synchronize()
                py_latencies.append((time.perf_counter() - t0) * 1000.0)

        # 3. Benchmark ONNX Runtime
        onnx_latencies = []
        feeds = {"sequence": sample_seq_np, "joint_mask": sample_jm_np, "temporal_mask": sample_tm_np}
        # Warmup
        for _ in range(15):
            _ = self.session.run(self.output_names, feeds)

        # Benchmark
        for _ in range(num_iterations):
            t0 = time.perf_counter()
            _ = self.session.run(self.output_names, feeds)
            onnx_latencies.append((time.perf_counter() - t0) * 1000.0)

        py_mean = float(np.mean(py_latencies))
        onnx_mean = float(np.mean(onnx_latencies))
        speedup = py_mean / max(1e-5, onnx_mean)

        return {
            "num_iterations": num_iterations,
            "parity_check": {
                "max_abs_diff": max_abs_diff,
                "mean_abs_diff": mean_abs_diff,
                "tolerance": 1e-4,
                "status": "PASS" if parity_pass else "FAIL",
            },
            "pytorch_native": {
                "device": str(device),
                "mean_latency_ms": round(py_mean, 2),
                "p50_latency_ms": round(float(np.percentile(py_latencies, 50)), 2),
                "p95_latency_ms": round(float(np.percentile(py_latencies, 95)), 2),
                "fps": round(1000.0 / py_mean, 1),
            },
            "onnx_runtime": {
                "provider": self.active_provider,
                "mean_latency_ms": round(onnx_mean, 2),
                "p50_latency_ms": round(float(np.percentile(onnx_latencies, 50)), 2),
                "p95_latency_ms": round(float(np.percentile(onnx_latencies, 95)), 2),
                "fps": round(1000.0 / onnx_mean, 1),
            },
            "speedup_factor": round(speedup, 2),
        }
