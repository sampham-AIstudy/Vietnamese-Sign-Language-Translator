"""
Offline Streaming Simulation for Level 3 CSLR (P1-2).
Evaluates full-clip (offline) vs chunk-based streaming on 30 unseen sentences of S06.
Metrics:
- WER (Word Error Rate)
- Latency (Full-clip vs Per-chunk vs Time-to-first-gloss)
- Degradation analysis
Output:
- reports/audit_round2/cslr_streaming_simulation.json
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translation.cslr_recognizer import CSLRRecognizer
from src.data.vsl_gh_dataset import convert_137_to_67
from src.metrics.cslr_metrics import compute_wer, ctc_greedy_decode, tokens_to_words


def stream_chunks(
    kps_67: np.ndarray,
    recognizer: CSLRRecognizer,
    chunk_size: int = 60,
    stride: int = 30,
) -> Tuple[List[str], List[float], float]:
    """
    Simulates streaming by sliding a window over the continuous keypoints.
    Accumulates decoded tokens with CTC deduplication across chunk boundaries.
    """
    T = kps_67.shape[0]
    all_pred_words = []
    chunk_latencies = []
    t_start = time.perf_counter()
    first_token_time = None

    last_emitted_token = None

    for start_idx in range(0, max(1, T - chunk_size // 2), stride):
        end_idx = min(start_idx + chunk_size, T)
        chunk = kps_67[start_idx:end_idx]  # [C_len, 67, 3]
        if len(chunk) < 15:
            continue

        c_start = time.perf_counter()
        # Run inference on chunk
        chunk_tensor = torch.from_numpy(chunk).float().unsqueeze(0).to(recognizer.device)
        lengths = torch.tensor([len(chunk)], dtype=torch.long, device=recognizer.device)

        with torch.no_grad():
            with torch.amp.autocast("cuda", enabled=(recognizer.device.type == "cuda")):
                log_probs, out_lens = recognizer.model(chunk_tensor, sequence_lengths=lengths)

        pred_tokens = ctc_greedy_decode(log_probs, sequence_lengths=out_lens, blank_id=recognizer.vocab.blank_id)[0]
        c_lat = (time.perf_counter() - c_start) * 1000.0
        chunk_latencies.append(c_lat)

        # Append new non-duplicate tokens
        for tok in pred_tokens:
            if tok != last_emitted_token and tok != recognizer.vocab.blank_id:
                word = recognizer.vocab.id_to_gloss.get(tok, f"ID_{tok}")
                all_pred_words.append(word)
                last_emitted_token = tok
                if first_token_time is None:
                    first_token_time = (time.perf_counter() - t_start) * 1000.0

    if first_token_time is None:
        first_token_time = sum(chunk_latencies)

    return all_pred_words, chunk_latencies, first_token_time


def main():
    print("=== STARTING P1-2: CSLR OFFLINE STREAMING SIMULATION ===")
    recognizer = CSLRRecognizer()
    print("CSLRRecognizer loaded successfully on", recognizer.device)

    # Load S06 unseen samples (SENT271 - SENT300)
    with open("reports/cslr_s06_predictions.json", encoding="utf-8") as f:
        s06_all = json.load(f)

    unseen_samples = [s for s in s06_all if s["sentence_id"] >= "SENT271"]
    print(f"Loaded {len(unseen_samples)} unseen sentence samples from S06.")

    kp_dir = Path("data/external/vsl_gh/keypoints_frontal")
    if not kp_dir.exists():
        print(f"Error: {kp_dir} does not exist!")
        return

    results = []
    offline_wers = []
    streaming_wers = []
    offline_lats = []
    chunk_lats = []
    ttft_lats = []

    for i, s in enumerate(unseen_samples, 1):
        sample_id = s["sample_id"]
        ref_glosses = s["ref_gloss_list"]
        npy_path = kp_dir / f"{sample_id}.npy"

        if not npy_path.exists():
            continue

        raw_kps = np.load(npy_path).astype(np.float32)  # [T, 411]
        kps_67 = convert_137_to_67(raw_kps, mode="semantic")  # [T, 67, 3]

        # 1. Offline Full-Clip
        t0 = time.perf_counter()
        off_res = recognizer.predict(kps_67)
        off_lat = (time.perf_counter() - t0) * 1000.0
        off_pred = off_res["gloss_list"]
        off_wer = float(compute_wer([off_pred], [ref_glosses])["wer"])

        # 2. Streaming Simulation (chunk=60, stride=30)
        stream_pred, c_lats, ttft = stream_chunks(kps_67, recognizer, chunk_size=60, stride=30)
        stream_wer = float(compute_wer([stream_pred], [ref_glosses])["wer"])

        offline_wers.append(off_wer)
        streaming_wers.append(stream_wer)
        offline_lats.append(off_lat)
        chunk_lats.extend(c_lats)
        ttft_lats.append(ttft)

        res_item = {
            "sample_id": sample_id,
            "sentence_id": s["sentence_id"],
            "num_frames": int(kps_67.shape[0]),
            "reference": ref_glosses,
            "offline_prediction": off_pred,
            "offline_wer": round(off_wer, 4),
            "offline_latency_ms": round(off_lat, 2),
            "streaming_prediction": stream_pred,
            "streaming_wer": round(stream_wer, 4),
            "avg_chunk_latency_ms": round(float(np.mean(c_lats)), 2) if c_lats else 0.0,
            "time_to_first_token_ms": round(ttft, 2),
        }
        results.append(res_item)

        if i % 10 == 0 or i == len(unseen_samples):
            print(f"[{i:2d}/{len(unseen_samples)}] {sample_id} ({kps_67.shape[0]} frames) | Offline WER: {off_wer*100:.1f}% | Stream WER: {stream_wer*100:.1f}%")

    avg_off_wer = float(np.mean(offline_wers))
    avg_stream_wer = float(np.mean(streaming_wers))
    delta_wer = avg_stream_wer - avg_off_wer

    summary = {
        "num_samples": len(results),
        "chunk_config": {"chunk_size_frames": 60, "stride_frames": 30, "chunk_sec": 2.0, "stride_sec": 1.0},
        "offline": {
            "mean_wer": round(avg_off_wer, 4),
            "mean_latency_ms": round(float(np.mean(offline_lats)), 2),
            "p95_latency_ms": round(float(np.percentile(offline_lats, 95)), 2),
        },
        "streaming": {
            "mean_wer": round(avg_stream_wer, 4),
            "mean_chunk_latency_ms": round(float(np.mean(chunk_lats)), 2),
            "mean_time_to_first_token_ms": round(float(np.mean(ttft_lats)), 2),
            "p95_chunk_latency_ms": round(float(np.percentile(chunk_lats, 95)), 2),
        },
        "degradation": {
            "wer_delta_absolute": round(delta_wer, 4),
            "wer_relative_increase_percent": round((delta_wer / max(avg_off_wer, 1e-5)) * 100, 2),
        },
        "samples": results,
    }

    out_file = Path("reports/audit_round2/cslr_streaming_simulation.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print("CSLR STREAMING SIMULATION RESULTS:")
    print(f"  Offline (Full-Clip) Mean WER : {avg_off_wer*100:.2f}% (Latency: {np.mean(offline_lats):.1f}ms)")
    print(f"  Streaming (Chunk=60) Mean WER: {avg_stream_wer*100:.2f}% (Chunk Latency: {np.mean(chunk_lats):.1f}ms, TTFT: {np.mean(ttft_lats):.1f}ms)")
    print(f"  Degradation (WER Delta)      : +{delta_wer*100:.2f}% (Relative increase: {summary['degradation']['wer_relative_increase_percent']}%)")
    print(f"  Saved detailed report to: {out_file}")
    print("=======================================================")


if __name__ == "__main__":
    main()
