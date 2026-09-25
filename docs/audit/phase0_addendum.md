# PHASE 0 ADDENDUM — Pivot to Clean Raw Video Pipeline

**Project:** Vietnamese Sign Language Recognition (VSLR)  
**Date:** 2026-09-12  
**Auditor:** Senior Computer Vision + Deep Learning Engineer  
**Status:** Phase 0 BLOCKED -> Transitioning to Phase 0.5 (Scope Freeze + Environment Fix + Raw Dataset Feasibility)  

---

## 1. Context & Why Phase 0 Was BLOCKED

During the initial baseline audit of Phase 0, four critical blockers were discovered:
1. **Target Dataset Missing (`dataset_missing`)**:
   The prompt envisioned a target dataset of *472 glosses with shape [T, 76, 3] and directories `processed/`, `processed_augmented/`, `raw/`, `keypoints_splited/`, `frame_splited/`*. An exhaustive filesystem scan across drive `C:\` confirmed that this dataset does **not exist** anywhere on the user's machine or repository.
2. **76-joint Semantic Mapping Undefined (`mapping_unknown`)**:
   No code, configuration, or reference paper in the repository defines a 76-joint layout. The existing codebase exclusively implements a **67-joint** representation (201 dimensions = 25 upper-body pose + 21 left hand + 21 right hand $\times$ 3 coordinates). Global Rule 0 & Rule 3 strictly prohibit inventing or assuming a 76-joint schema without concrete evidence.
3. **Severe Data Leakage in Existing Preprocessed Dataset (`leakage`)**:
   `data (2)/Processed/` contains 184,295 `.npz` sequence files, yet the entire raw video corpus in `data (2)/Dataset/Videos/` contains only 4,362 videos. Analysis demonstrated that temporal sliding-window slicing and augmentations were applied **before** splitting. Augmented and sliced variants of the exact same video performances were scattered across `train/`, `val/`, and `test/`, yielding cross-split cosine similarities exceeding $0.99$. The 100% validation accuracy recorded in `word_model_bigru.pth` is a direct consequence of this leakage.
4. **CPU-only PyTorch Build (`cuda`)**:
   While the host machine contains a dedicated NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM, Driver 566.36, CUDA 12.7), PyTorch inside `.\.venv` was installed as CPU-only (`2.14.0+cpu`), preventing GPU acceleration.

---

## 2. Core Decisions & Pivot Strategy

To ensure scientific integrity, academic reproducibility, and leakage-safe benchmarks:

1. **Abandon Fictitious 472-Gloss / 76-Joint Assumptions**:
   - We will NOT synthesize or fabricate a 472-class dataset.
   - We will NOT guess a 76-joint schema.
   - We freeze the joint representation to the verified **67-joint MediaPipe Holistic schema** (25 pose + 21 LH + 21 RH = 201 features).

2. **Quarantine `data (2)/Processed`**:
   - The existing 184,295 `.npz` files in `data (2)/Processed` are formally quarantined and marked as `LEAKED / INVALID FOR BENCHMARK`.
   - They will never be used for training, validation, or testing in any benchmark phase.
   - They are retained solely for historical debugging / reference.

3. **Pivot to Clean Raw Video Pipeline**:
   - All future training and evaluation pipelines must derive directly from the canonical **4,362 raw MP4 videos** located in `data (2)/Dataset/Videos/` and their annotations in `data (2)/Dataset/Labels/label.csv`.
   - Feature extraction will be performed cleanly from raw videos without zero-padding for missing landmarks.

4. **Source-Video-Disjoint Partitioning**:
   - A raw video file is defined as an atomic `source_id`.
   - All frames, sequences, windows, and augmentations derived from a given `source_id` must strictly reside in a single split (`train`, `val`, or `test`).
   - Augmentation will be applied strictly post-split and exclusively to the `train` split.

5. **Establish Phase 0.5**:
   - Current phase transitions to **Phase 0.5: Scope Freeze + Environment Fix + Raw Dataset Feasibility**.
   - Model training remains strictly forbidden until the raw dataset scope is audited and frozen.

---

## 3. Remaining Risks & Mitigation

| Risk | Impact | Mitigation Plan |
| :--- | :--- | :--- |
| **Imbalance / Low Video Count per Gloss** | Out of 3,315 glosses, many may have only 1–3 videos, making standard closed-set supervised classification statistically weak or intractable. | Conduct complete class feasibility audit (Step 5); propose filtered subsets (e.g. top-N or $\ge k$ samples/class) with sufficient support per class. |
| **No Ground-Truth Signer ID** | Cannot perform strict signer-independent evaluation without signer labels. | Enforce strict source-video-disjoint splits. Note dialect/region (North, Central, South) as a proxy grouping if applicable, and explicitly document this limitation in academic reports. |
| **VRAM Constraint (RTX 3050 4GB)** | Large models or excessive batch sizes will trigger Out-Of-Memory (OOM) errors. | Fix PyTorch CUDA runtime, profile memory, adopt lightweight architectures (BiGRU, compact ST-GCN, small Transformer), and use Mixed Precision (AMP). |
| **MediaPipe Landmark Extraction Overhead** | Re-extracting landmarks from 4,362 raw videos requires computation. | Profile extraction throughput, log missing rate, cache canonical raw landmarks once per video in an auditable, non-augmented format. |

---
