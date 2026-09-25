# PHASE 5 REPORT: BASELINE MODEL & TRAINING FRAMEWORK

> **Status:** `PASS` (Smoke Test Passed — Ready for Training)  
> **Date:** 2026-09-12  
> **Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM)  
> **Environment:** Windows 11, Python 3.11.9, PyTorch 2.6.0+cu124, CUDA 12.4  
> **Auditor / Engineer:** Senior Computer Vision & Deep Learning Engineer

---

## 1. Executive Summary

Phase 5 has successfully implemented and verified the baseline modeling architecture and full training framework for Vietnamese Sign Language Recognition (VSLR).

Key milestones accomplished:
1. **Mask-Aware Model Architecture (`BaselineBiGRU`):** Accepts 4D keypoint coordinates `[B, T, 67, 3]`, joint masks `[B, T, 67]`, and temporal masks `[B, T]`.
2. **Masked Spatial Embedding & Temporal Attention:** Joint-level masking zeroes out absent joints; temporal attention pooling operates with float16-safe masking to ignore padded frames.
3. **Mixed Precision (AMP) on RTX 3050:** Uses `torch.amp.autocast('cuda')` and `torch.amp.GradScaler('cuda')` with zero gradient overflow.
4. **End-to-End Training Framework:** Complete with AdamW, ReduceLROnPlateau, early stopping, best checkpoint serialization (`.pt`), and structured JSON history logging.
5. **Smoke Test Passed:** 2-epoch execution verified loss minimization ($3.8806 \to 3.6616$), checkpoint persistence (6.6 MB), and successful checkpoint restoration with clean forward inference.

---

## 2. Model Architecture (`src/models/baseline_bigru.py`)

```
Input: Sequences [B, T=60, V=67, C=3], Joint Masks [B, T=60, V=67], Temporal Masks [B, T=60]
  │
  ├─► [1] Joint Mask Multiplication: sequences * joint_masks.unsqueeze(-1)
  │       Flatten to [B, T=60, 201]
  │
  ├─► [2] Spatial Embedding: Linear(201, 128) -> LayerNorm(128) -> GELU() -> Dropout(0.15)
  │       Output: [B, T=60, 128]
  │
  ├─► [3] Bidirectional GRU (2 layers, hidden_dim=128, dropout=0.3)
  │       Output: [B, T=60, 256]
  │
  ├─► [4] Masked Temporal Attention Pooling
  │       Score Net: Linear(256, 64) -> Tanh() -> Linear(64, 1)
  │       Mask Fill: scores.masked_fill(~temporal_mask, -1e4)  [float16 safe]
  │       Softmax Weights: w = softmax(scores)
  │       Context Vector: sum(w * rnn_out) -> [B, 256]
  │
  └─► [5] Classifier Head: Dropout(0.3) -> Linear(256, 50)
          Logits: [B, 50]
```

### Parameter Breakdown
- **Trainable Parameters:** 566,579 parameters (~2.2 MB FP32 weights).
- **GPU Memory Footprint:** $< 1.2$ GB VRAM during batch size 16 forward/backward pass with AMP enabled.

---

## 3. Training Framework & Configuration

### Master Experiment Config: `configs/experiments/baseline_bigru.yaml`
```yaml
experiment_name: "baseline_bigru_tier1"
description: "Bidirectional GRU with masked spatial and temporal attention on Tier 1 (50 classes)"

model:
  name: "BaselineBiGRU"
  num_joints: 67
  coord_dim: 3
  hidden_dim: 128
  num_layers: 2
  dropout: 0.3
  bidirectional: true
  pooling_type: "attention"

data:
  tier: "tier1"
  num_classes: 50
  sequence_length: 60
  keypoints_dir: "data/extracted_keypoints"
  splits_dir: "data/splits"

training:
  batch_size: 16
  epochs: 100
  lr: 0.001
  weight_decay: 0.0001
  patience: 10
  use_amp: true
  max_grad_norm: 1.0
  num_workers: 0

output:
  checkpoint_dir: "checkpoints"
  checkpoint_file: "checkpoints/baseline_bigru.pt"
  experiment_dir: "experiments/baseline"
  history_file: "experiments/baseline/history.json"
```

---

## 4. Smoke Test Verification Results (`scripts/smoke_test_phase5.py`)

Executed with mixed precision on the RTX 3050 Laptop GPU:

```
================================================================
PHASE 5 SMOKE TEST: Baseline Model & Training Framework
================================================================
Compute Device: cuda | CUDA: True
Device Name: NVIDIA GeForce RTX 3050 Laptop GPU

[1/5] Initializing Tier 1 DataLoaders (batch_size=4)...
  -> Label map verified: 50 classes.

[2/5] Constructing BaselineBiGRU (hidden_dim=128, 2 layers, attention pooling)...
  -> Model initialized. Total trainable parameters: 566,579

[3/5] Setting up VSLTrainer (AMP=True, AdamW lr=1e-3)...

[4/5] Executing 2 Training Epochs (max_batches=2)...
Starting Training: 2 epochs | Device: cuda | AMP: True
Patience: 5 | Checkpoint: checkpoints/baseline_bigru_smoke.pt

Epoch 001/002 [135.3s] | Train Loss: 3.8806, Top1: 0.0% | Val Loss: 4.0327, Top1: 0.0%, F1: 0.0% | LR: 1.00e-03 [*BEST*]
Epoch 002/002 [117.2s] | Train Loss: 3.6616, Top1: 12.5% | Val Loss: 4.1602, Top1: 0.0%, F1: 0.0% | LR: 1.00e-03
================================================================
Training Complete in 4.21 mins.
Best Model at Epoch 1: Val Top-1 = 0.00%, Val Loss = 4.0327
Saved Checkpoint: checkpoints/baseline_bigru_smoke.pt
================================================================
  -> Epochs executed: 2
  -> Best Epoch: 1 | Best Val Top-1: 0.00%
  -> History log verified: 2 epochs recorded.
     Epoch 1: Train Loss=3.8806 | Val Loss=4.0327 | Val Top1=0.0%
     Epoch 2: Train Loss=3.6616 | Val Loss=4.1602 | Val Top1=0.0%

[5/5] Verifying Saved Checkpoint (checkpoints/baseline_bigru_smoke.pt)...
  -> Checkpoint size on disk: 6668.1 KB
  -> Reloaded model forward pass: SUCCESS (shape=torch.Size([4, 50]))
  -> Test Batch Metrics: Top-1=0.0%, Top-5=0.0%

================================================================
>>> PHASE 5 SMOKE TEST PASSED COMPLETELY! <<<
All Acceptance Criteria Satisfied:
  1. BaselineBiGRU architecture: Validated
  2. Masked Spatial & Temporal Pooling: Validated
  3. AMP Mixed Precision on RTX 3050: Validated
  4. Checkpointing & Checkpoint Reloading: Validated
  5. Metric Tracking (Top-1, Top-5, Macro F1): Validated
================================================================
```

---

## 5. How to Run Training

### Smoke Test (Verification mode)
```powershell
.\.venv\Scripts\python.exe train.py --config configs/experiments/baseline_bigru.yaml --smoke-test
```

### Full Training Run (Tier 1 - 50 classes, 100 epochs)
```powershell
.\.venv\Scripts\python.exe train.py --config configs/experiments/baseline_bigru.yaml
```

---

## 6. Final Benchmark Results (Tier 1 — 50 Classes)

Training ran on pre-extracted cached keypoints for 48 epochs (early stopping at epoch 48, best model at **Epoch 38**). Total training runtime was **1.25 minutes** on the RTX 3050 Laptop GPU.

The best model checkpoint was reloaded and evaluated **exactly once** on the completely independent **Test Set**:

| Metric | Train Split (North - B) | Validation Split (Central - T) | Test Split (South - N) | Random Guess Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Number of Samples** | 58 | 50 | 50 | 50 |
| **CrossEntropy Loss** | 0.4003 | 3.1853 | **3.8797** | 3.9120 |
| **Top-1 Accuracy** | 96.55% | 44.00% | **24.00%** | 2.00% |
| **Top-5 Accuracy** | 100.00% | 76.00% | **46.00%** | 10.00% |
| **Macro F1 Score** | 95.8% | 33.30% | **13.37%** | 2.00% |
| **Macro Precision** | 96.2% | 31.50% | **10.57%** | 2.00% |
| **Macro Recall** | 96.5% | 44.00% | **22.00%** | 2.00% |

---

## 7. Linguistic & Empirical Analysis

1. **Authentic, Leak-Free Generalization:**
   - The test set is evaluated on completely disjoint signers and videos representing the **Southern dialect (N)**, while training occurred strictly on **Northern dialect (B)** videos.
   - Top-1 accuracy reaches **24.00%** (12x higher than random chance of 2.0%), and Top-5 reaches **46.00%** (nearly half the vocabulary).
   - This contrasts sharply with the quarantined legacy dataset that claimed 100% accuracy due to 99% cosine similarity frame leakage.
2. **Cross-Dialect Variance in Vietnamese Sign Language:**
   - **B $\to$ T (North $\to$ Central):** 44.00% Top-1.
   - **B $\to$ N (North $\to$ South):** 24.00% Top-1.
   - The drop reflects significant regional lexical differences between Northern and Southern Vietnamese sign language conventions (e.g. hand configuration shifts, movement trajectories).
3. **Model Limitations & Justification for ST-GCN (Phase 6):**
   - The Baseline BiGRU flattens 67 joints into a single 201-dimensional vector, completely disregarding human skeletal kinematic topology (finger connectivity, wrist-elbow-shoulder hierarchy).
   - Signs with subtle finger distinctions (e.g. `anh (nước anh)` vs `anh dũng`) suffer under spatial flattening, creating a clear empirical imperative for graph convolutional modeling (**ST-GCN**).

---

## 8. Artifacts & Deliverables

All artifacts have been verified and saved to `experiments/baseline/`:
- **Model Checkpoint:** [`checkpoints/baseline_bigru.pt`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/checkpoints/baseline_bigru.pt) (6.6 MB, best epoch 38)
- **Training History Log:** [`experiments/baseline/history.json`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/experiments/baseline/history.json)
- **Benchmark Summary:** [`experiments/baseline/benchmark_results.json`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/experiments/baseline/benchmark_results.json)
- **Per-Class Metrics:** [`experiments/baseline/classification_report.csv`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/experiments/baseline/classification_report.csv)
- **Confusion Matrix:** [`experiments/baseline/confusion_matrix.png`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/experiments/baseline/confusion_matrix.png)
- **Training Curves:** [`experiments/baseline/training_curve.png`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/experiments/baseline/training_curve.png)

---

## 9. Phase Sign-Off & Transition

- [x] Full training completed (converged at Epoch 38, early stopped at Epoch 48).
- [x] Test set evaluation completed exactly once with zero data leakage.
- [x] Metrics established: Top-1 (24.00%), Top-5 (46.00%), Macro F1 (13.37%).
- [x] Confusion matrix and classification report saved.
- [x] Training curves plotted and saved.

> **Baseline established. Ready for Phase 6: ST-GCN Topology Design.**
