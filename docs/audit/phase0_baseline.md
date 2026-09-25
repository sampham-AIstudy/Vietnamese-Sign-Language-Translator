# PHASE 0 — Full Audit / Baseline Report: Vietnamese Sign Language Recognition (VSLR)

**Project:** Vietnamese Sign Language Translator (VSLR)  
**Corpus / Repo:** `sampham-AIstudy/Vietnamese-Sign-Language-Translator`  
**Working Directory:** `C:\Users\Admin\Python Advanced\Deep Learning - CV\Project`  
**Audit Date:** 2026-09-12  
**Auditor:** Senior CV + DL + MLOps Engineer  

---

## 1. Executive Summary & Status

* **Status:** `BLOCKED`
* **Blocker Severity:** HIGH (Dataset specification mismatch, missing 76-joint mapping, severe data leakage in existing preprocessed splits, and CPU-only PyTorch build).
* **Rule Compliance:** Audit performed strictly on real code, logs, and data. Zero functional code modified. Zero assumptions made.

---

## 2. Environment & Hardware Audit

| Component | Detected Specification | Note / Evidence |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 (64-bit) | PowerShell shell |
| **CPU / System RAM** | AMD/Intel 64-bit | Host system |
| **Physical GPU** | **NVIDIA GeForce RTX 3050 Laptop GPU** | `nvidia-smi`: Driver 566.36, CUDA 12.7, VRAM: 4096 MiB (4GB) |
| **Active Python** | Python 3.11.9 (`.\.venv\Scripts\python.exe`) | Virtual environment active in project root |
| **PyTorch Version** | **`2.14.0+cpu`** | **CRITICAL: PyTorch is CPU-only!** `torch.cuda.is_available()` returns `False` |
| **Key Packages** | `mediapipe==0.10.x`, `opencv-python`, `fastapi`, `uvicorn`, `streamlit`, `onnx`, `onnxruntime`, `pypdf` | Installed in `.venv` |

---

## 3. Current Repository Architecture

```
Project/
├── .venv/                         # Virtual environment (Python 3.11.9, torch CPU)
├── configs/
│   ├── alphabet_config.yaml       # Config for Level 1 static alphabet
│   └── word_config.yaml           # Config for Level 2 word recognition (top 40 classes)
├── data/                          # Level 1: Static Fingerspelling Alphabet
│   ├── hand_data.csv              # 1,196 samples x 43 cols (42 coords + label)
│   ├── alphabet_landmarks_full.csv# 2,068 samples x 43 cols (42 coords + label)
│   ├── asl_alphabet_train/        # ASL image dataset (29 classes, 87,000 jpgs)
│   └── asl_alphabet_test/         # ASL image test set
├── data (2)/                      # Level 2: Word-Level Dynamic VSL
│   ├── Dataset/
│   │   ├── Videos/                # 4,362 raw MP4 video clips
│   │   └── Labels/label.csv       # 4,362 rows (ID, VIDEO, LABEL), 3,315 unique glosses
│   └── Processed/                 # 184,295 .npz sequence files
│       ├── label_map.json         # 3,315 class mapping to [0..3314]
│       ├── train/                 # 145,019 .npz files across 3,315 subdirs
│       ├── val/                   # 17,980 .npz files across 3,315 subdirs
│       └── test/                  # 21,296 .npz files across 3,315 subdirs
├── experiments/                   # Checkpoints & artifacts
│   ├── alphabet_model.pth / onnx / torchscript.pt
│   ├── word_model_bigru.pth / onnx / torchscript.pt (trained on top 40 classes)
│   ├── word_model_bigru_classes.json (40 classes)
│   └── confusion_matrix_word.png
├── src/
│   ├── data/
│   │   ├── extract_landmarks.py   # MediaPipe Holistic (201-dim) & Hands (42-dim)
│   │   ├── dataset.py             # PyTorch Dataset/DataLoader (VSLSequenceDataset)
│   │   └── augment.py             # Jitter, rotate, time warp
│   ├── models/
│   │   ├── alphabet_classifier.py # AlphabetMLP (input 42, hidden [256, 128, 64], out 29)
│   │   ├── gru_classifier.py      # BiGRUSequenceClassifier (input 201, hidden 128, out 40)
│   │   ├── transformer_classifier.py # VSLTransformerClassifier (input 201, d_model 128)
│   │   └── stgcn.py               # STGCNClassifier (num_nodes=67, in_channels=3)
│   ├── inference/
│   │   └── realtime_processor.py  # WebRTC sliding window inference buffer
│   ├── train_alphabet.py
│   ├── train_word.py
│   ├── evaluate.py
│   └── export.py
├── app/
│   ├── api/main.py                # FastAPI REST + WebSocket (/ws/live-stream)
│   └── ui/app.py                  # Streamlit UI
├── backend/                       # Node.js Express server (proxy + dictionary API)
├── frontend/                      # React 18 + Vite + Tailwind CSS frontend
├── reference/                     # 2 HUST research papers (2025 Alphabet, 2026 VSL Review)
├── requirements.txt
├── README.md
└── start_fullstack.ps1
```

---

## 4. Current Dataset Audit vs. Target Specification

### 4.1 Target Specification Mentioned in Master Prompt
* 472 glosses
* Folders: `processed/`, `processed_augmented/`, `raw/`, `keypoints_splited/`, `frame_splited/`
* Keypoint shape: `[T, 76, 3]` (76 joints)

### 4.2 Reality Found in Codebase and Filesystem
1. **Dataset Root & Structure**:
   - The directory on disk is named `data (2)/`, containing `Dataset/Videos/`, `Dataset/Labels/label.csv`, and `Processed/`.
   - No folder named `keypoints_splited`, `frame_splited`, or `processed_augmented` exists anywhere on the machine (recursively searched `C:\` and user directories).
   - No dataset with **472 glosses** exists.
2. **Actual Class Counts**:
   - `data (2)/Dataset/Labels/label.csv`: Contains **4,362 rows** and **3,315 unique glosses**.
   - `data (2)/Processed/label_map.json`: Contains **3,315 classes**.
   - Current training scripts (`word_config.yaml`, `src/train_word.py`) filter down to `top_k: 40` classes due to hardware constraints.
3. **Actual Tensor Shape & Dimensions**:
   - Shape in all existing `.npz` files: **`(60, 201)`** of type `float64`.
   - Feature structure: $201 = 67 \times 3$, broken down into:
     - Upper body pose: landmarks $0..24$ ($25 \times 3 = 75$ coords).
     - Left hand: 21 landmarks ($21 \times 3 = 63$ coords).
     - Right hand: 21 landmarks ($21 \times 3 = 63$ coords).
     - Total: $25 + 21 + 21 = 67$ joints, each with $(x, y, z)$.
   - **Zero files with shape `[T, 76, 3]` exist** in the repository or filesystem.
4. **76-joint Semantic Mapping**:
   - In existing code and configs, **76 joints are nowhere mentioned or defined**.
   - In `src/models/stgcn.py`, the code uses `num_nodes: int = 67`.
   - Without empirical ground truth or mapping metadata, assigning semantics to 76 joints is strictly prohibited by Rule 0 and Rule 3.

---

## 5. Critical Finding: Severe Data Leakage in Current Preprocessed Split

### 5.1 Evidence
1. **Source Video Discrepancy**:
   - `data (2)/Dataset/Videos/` contains **4,362 video files** total.
   - For any given gloss (e.g., `địa chỉ`), there are only **3 raw videos** (`D0001B.mp4`, `D0001N.mp4`, `D0001T.mp4`).
   - However, `data (2)/Processed/` contains **184,295 `.npz` files** across all classes!
   - For `địa chỉ`, there are **123 `.npz` files** (98 in `train/`, 12 in `val/`, 13 in `test/`).
2. **Leakage Verification via Direct Empirical Analysis**:
   - Comparing random samples of class `địa chỉ` across splits using `scikit-learn` / `numpy`:
     - $\text{MSE}(\text{train\_0.npz}, \text{val\_1.npz}) = 0.001986$
     - $\text{Cosine Similarity}(\text{train\_0.npz}, \text{val\_1.npz}) = \mathbf{0.99369}$
     - $\text{Cosine Similarity}(\text{train\_0.npz}, \text{test\_4.npz}) = \mathbf{0.99430}$
     - **654 pairs** between `val` and `train` have cosine similarity $> 0.99$.
3. **Mechanism of Leakage**:
   - Multi-crop / temporal sliding-window / data augmentation was applied **prior to splitting**.
   - The resulting slices were shuffled and randomly partitioned into `train/`, `val/`, and `test/`.
   - Near-duplicate temporal slices and augmented copies of the exact same video recording exist simultaneously in both training and test sets.
4. **Consequence on Benchmark**:
   - In `experiments/word_model_bigru.pth`, the recorded validation accuracy is $\mathbf{100.0\%}$ (`val_top1: 1.0`, `val_top5: 1.0`).
   - This 100% accuracy is an illusion caused by dataset contamination and data leakage.

---

## 6. Signer & Source Metadata Audit

* `data (2)/Dataset/Labels/label.csv`:
  * Columns: `ID`, `VIDEO`, `LABEL`.
  * No explicit `signer_id` column exists.
  * Filename conventions encode dialect/region:
    * Suffix `B`: Northern dialect (Miền Bắc).
    * Suffix `T`: Central dialect (Miền Trung).
    * Suffix `N`: Southern dialect (Miền Nam).
    * Prefix `D`: Dialogue / phrases.
    * Prefix `W`: Isolated words.
* **Signer-disjoint split is currently IMPOSSIBLE** without external signer annotations.
* **Source-video-disjoint split is MANDATORY and FEASIBLE**: All frames / keypoints derived from video `D0001B.mp4` must strictly reside within only ONE split (e.g. `train`).

---

## 7. Current Models & Inference Pipeline Audit

### 7.1 Word-Level Model (`src/models/gru_classifier.py`)
* Input: `(B, 60, 201)`
* Output: `(B, 40)` (or `num_classes`)
* Architecture: Linear projection (201 -> 128) -> LayerNorm -> ReLU -> Dropout -> BiGRU (2 layers, hidden=128) -> `TemporalAttention` -> Classifier MLP (256 -> 128 -> num_classes).
* Missing landmarks handling: **Hardcoded zeros** in `extract_landmarks.py` when detection fails (`pose = np.zeros(...)`, `lh = np.zeros(...)`, `rh = np.zeros(...)`). Violates Rule 0.

### 7.2 ST-GCN Model (`src/models/stgcn.py`)
* Input: `(B, 60, 201)` reshaped to `(B, 3, 60, 67)`
* Adjacency Matrix: Dummy uniform matrix (`adj = torch.eye(67) + 0.1 * torch.ones(67, 67)`). It does **NOT** reflect actual anatomical joint connections.

### 7.3 Active Checkpoint in Inference
* `experiments/word_model_bigru.pth` (40 classes, BiGRU, 201 input dimensions, trained on contaminated split).
* Loaded by `app/api/main.py` at startup and used for REST `/predict/word`, `/predict/video`, and `/ws/live-stream`.

---

## 8. Technical Debt & Critical Bugs

1. **Bug 1 (Data Leakage)**: `data (2)/Processed/` contains augmented/sliding-window copies of the same raw videos partitioned across train/val/test splits.
2. **Bug 2 (Zero-fill for Missing Landmarks)**: `src/data/extract_landmarks.py` fills undetected hands and pose with zeros, preventing the model from distinguishing real coordinate $(0,0,0)$ from missing data.
3. **Bug 3 (Forced Resampling to 60 Frames)**: `resample_sequence(..., 60)` distorts natural signing velocity and temporal dynamics.
4. **Bug 4 (Dummy ST-GCN Graph)**: `stgcn.py` uses an unnormalized, fully-connected dummy graph rather than anatomical skeleton topology.
5. **Bug 5 (Arbitrary Top-40 Truncation)**: Dataset loader arbitrarily truncates vocabulary to top 40 classes without a formalized benchmark protocol.
6. **Bug 6 (CPU-only PyTorch)**: PyTorch in `.venv` does not leverage the host's NVIDIA RTX 3050 GPU.

---

## 9. Exact Files Needing Modification in Subsequent Phases

* `configs/vsl_config.yaml` (New configuration standard)
* `src/data/extract_landmarks.py` (Remove zero-filling, add confidence/visibility masks)
* `src/data/dataset.py` (Fix split loader, eliminate data leakage, support variable sequence length & masks)
* `src/data/preprocessing/` (New modular preprocessing: spatial, temporal, missing, features)
* `src/models/stgcn.py` (Implement true anatomical graph topology)
* `src/train_word.py` (Support reproducible training, AMP, proper metrics Top-1, Top-5, Macro F1)
* `app/api/main.py` (Update inference pipeline to match validated model and preprocessing)

---

## 10. Recommended Target Architecture

```
Raw Videos (4,362 clips) or Raw Canonical Keypoints
   │
   ▼
Video-Disjoint Split (Train / Val / Test based strictly on Video ID & Dialect)
   │
   ├── Train Split ──────► Train-only Augmentation (Jitter, Time Warp, Scale)
   ├── Val Split ────────► Clean Canonical (No Augmentation)
   └── Test Split ───────► Clean Canonical (No Augmentation)
   │
   ▼
Visibility & Confidence Aware Preprocessing
   - No zero-padding for missing hands
   - Interpolation + Missingness Mask
   - Centering & Scale Normalization relative to shoulder/torso
   │
   ▼
PyTorch Dataset / DataLoader with Collate & Mask
   - Inputs: [B, T, V, C] + [B, T, V] mask
   │
   ▼
Model Family Benchmark (same split, same protocol):
   1. Spatial-Temporal BiGRU Baseline
   2. ST-GCN (true anatomical skeleton adjacency)
   3. Spatial-Temporal Transformer
```

---

## 11. Phase 0 Status & Blockers

### STATUS: `BLOCKED`

### BLOCKERS:
1. **`dataset_missing`**: The target dataset described as *472 glosses with shape [T,76,3] and directories `processed/`, `processed_augmented/`, `keypoints_splited/`* does not exist in the filesystem or repository. The actual dataset available is `data (2)` with 3,315 classes, 4,362 videos, and 184,295 `.npz` sequences of shape `(60, 201)`.
2. **`mapping_unknown`**: The 76-joint semantic mapping is not defined in any file, config, or paper in the repository. The current code exclusively implements a 67-joint feature vector (25 pose + 21 left hand + 21 right hand = 67 x 3 = 201). Assumption of 76 joints is strictly prohibited by Rule 0.
3. **`leakage`**: Severe data leakage is present in the current `data (2)/Processed/` split, where multi-crop / augmented slices from the same raw videos exist across `train`, `val`, and `test` splits (cosine similarity $> 0.99$).
4. **`cuda_environment`**: PyTorch build is currently CPU-only (`2.14.0+cpu`). Training or benchmarking on GPU requires a CUDA-enabled PyTorch build.

---
