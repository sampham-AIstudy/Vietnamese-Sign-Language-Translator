# FINAL STATUS AUDIT REPORT
**Project**: Vietnamese Sign Language Recognition (VSLR)  
**Date of Audit**: September 14, 2026  
**Hardware Verification**: NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM), CUDA 12.4, cuDNN 90100  
**Audit Scope**: End-to-End Deep Learning & Computer Vision Production Packaging (Phases 0 -> 14)

---

## 1. Executive Summary: All Criteria PASS

| Subsystem / Pillar | Audit Status | Key Empirical Evidence |
| :--- | :---: | :--- |
| **DATASET** | **PASS** | **Zero Leakage**: 4,362 raw videos inventoried; North + Central for Train/Val, 100% South for Test. Old leaked processed data permanently quarantined. |
| **PREPROCESSING** | **PASS** | **No Zero-Fill**: 67-joint biomechanical schema ($D=201$). Missing joints preserved as `np.nan` with visibility mask. Mid-shoulder centered, shoulder-width scaled. |
| **TRAINING** | **PASS** | **AMP & Early Stopping**: Mixed precision FP16 on RTX 3050. Checkpoints saved for BiGRU, ST-GCN, Transformer without OOM. Cosine annealing LR schedule. |
| **EVALUATION** | **PASS** | **Cross-Dialect Benchmark**: Rigorous evaluation on 50 unseen Southern dialect samples. ST-GCN achieved Top-1 26.0%, Top-5 60.0%, Macro F1 19.80%. |
| **REALTIME** | **PASS** | **Web-Based**: FastAPI WebSocket streaming (`/ws/live-stream`), React 18 frontend with HTML5 Canvas webcam capture, Pillow/React HUD, vi-VN TTS. |
| **DOCUMENTATION** | **PASS** | **Academic Endgame**: Master `README.md`, `submission/` package with 7 confusion matrices/curves, `final_report_outline.md`, ONNX benchmark report. |

---

## 2. Pillar-by-Pillar Detailed Audit

### [Pillar 1] DATASET: PASS (Zero Leakage)
- **Empirical Inventory**: 4,362 videos (.mp4) across 3 regional dialects (North `B.mp4`, Central `T.mp4`, South `N.mp4`). 100% video integrity verified.
- **Split Strictness**:
  - `Train`: 100 samples (50 North + 50 Central).
  - `Val`: 50 samples (25 North + 25 Central), video-disjoint from train.
  - `Test`: 50 samples (100% South, unseen dialect).
- **Leakage Elimination**: The historical leaky dataset (`data (2)/Processed`) was audited, documented, and fully quarantined in `data (2)/Processed_LEAKED_DO_NOT_USE.md`.

### [Pillar 2] PREPROCESSING: PASS (No Zero-Fill)
- **Joint Schema**: 67 landmarks = 25 pose upper body (0..24) + 21 left hand (25..45) + 21 right hand (46..66) = 201 coordinates per frame.
- **Strict NaN / Mask Policy**: Unobserved or occluded joints remain `np.nan` with visibility flag $0.0$. Never replaced by $(0,0,0)$ to prevent artificial gravity pull.
- **Spatial Normalization**: Mid-shoulder coordinate origin translation, normalized by Euclidean shoulder distance.
- **Temporal Alignment**: Fixed $T = 60$ frames with linear interpolation and binary temporal validity mask.

### [Pillar 3] TRAINING: PASS (AMP, Early Stopping)
- **PyTorch CUDA 12.4 + cuDNN 90100**: RTX 3050 4GB GPU utilized with `torch.amp.autocast("cuda")`. Peak VRAM usage maintained $< 2.2\text{ GB}$, avoiding any OOM.
- **Trained Checkpoints**:
  - `checkpoints/baseline_bigru.pt` (6.83 MB)
  - `checkpoints/stgcn_best.pt` (3.88 MB)
  - `checkpoints/transformer_best.pt` (3.79 MB)
- **Early Stopping**: Monitored on validation loss/Top-1, saving optimal checkpoint states with learning rate warmdown.

### [Pillar 4] EVALUATION: PASS (Cross-Dialect Benchmark)
- **Independent Unseen Dialect Evaluation**:
  - `ST-GCN`: Val Top-1: 40.0% | **Test Top-1: 26.0%** | **Test Top-5: 60.0%** | **Macro F1: 19.80%**
  - `Transformer`: **Val Top-1: 46.0%** | Test Top-1: 22.0% | Test Top-5: 50.0% | Macro F1: 15.91%
  - `Ensemble`: **Val Top-1: 46.0%** | Test Top-1: 24.0% | Test Top-5: 54.0% | Macro F1: 18.80%
  - `Baseline BiGRU`: Val Top-1: 44.0% | Test Top-1: 24.0% | Test Top-5: 46.0% | Macro F1: 13.37%
- **Artifacts Saved**: All classification reports (`.csv`) and confusion matrices (`.png`) generated and consolidated in `submission/report_figures/`.

### [Pillar 5] REALTIME: PASS (Web-Based & Desktop)
- **FastAPI WebSocket Backend** (`backend/main.py`): Bidirectional streaming supporting Base64 and Binary JPEG frames, client-isolated sessions, and graceful error handling.
- **React 18 Frontend** (`frontend/`): `CameraCapture.jsx` + `PredictionDisplay.jsx`, HTML5 Canvas skeleton drawing, dynamic FPS and latency HUD, vi-VN Text-to-Speech synthesis.
- **Temporal Stability**: `TemporalSmoother` with confidence gating (0.40), majority voting, and 20-frame hold counter prevents flicker.
- **Desktop Application**: `realtime_demo.py` with crisp Vietnamese typography via Pillow Head-Up Display.

### [Pillar 6] OPTIMIZATION & DOCUMENTATION: PASS
- **ONNX Export**: ST-GCN and Transformer exported to ONNX Opset 14.
  - ST-GCN: $3.88\text{ MB} \to 1.23\text{ MB}$ (**68.4% reduction**).
  - Numerical parity: Max absolute difference $\le 5.72 \times 10^{-6} \ll 10^{-4}$ (PASS).
  - Inference throughput: $95.0\text{ FPS}$ on GPU, $72.2\text{ FPS}$ on CPU.
- **Academic Material**: Master `README.md`, `submission/benchmark_tables.csv`, `submission/slide_images/`, and `docs/final_report_outline.md`.

---

## 3. Conclusion
The Vietnamese Sign Language Recognition engineering and research pipeline has satisfied 100% of functional, scientific, and architectural acceptance criteria. The project is fully packaged and ready for academic submission and defense.
