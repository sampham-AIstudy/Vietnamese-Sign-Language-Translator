# PHASE 1 REPORT — Dataset Integration & 67-Joint Landmark Mapping

**Project:** Vietnamese Sign Language Recognition (VSLR)  
**Phase:** 1 — Dataset Integration + Landmark Mapping  
**Date:** 2026-09-12  
**Engineer:** Senior Computer Vision + Deep Learning Engineer  
**Status:** **PASS**  

---

## 1. Objective

Integrate the canonical raw VSL video corpus (`data (2)/Dataset/Videos/`) into an audit-safe, leakage-safe pipeline.
- Implement the approved **Two-Tier Benchmark strategy** (Tier 1: Core 50 classes; Tier 2: Extended 489 classes).
- Generate strict video-disjoint Train / Val / Test splits to eliminate all data leakage.
- Implement a clean MediaPipe Holistic 67-joint feature extractor with **STRICT NO ZERO-FILL** (visibility masks and NaNs for missing data).
- Implement temporal sequence handling (`SequenceGenerator`).
- Validate pipeline execution on sample classes (Dry Run) and automated leakage checking with 100% verified test passes.

---

## 2. What Was Done

1. **Environment Confirmation**:
   - PyTorch `2.6.0+cu124` active in `.venv`.
   - NVIDIA GeForce RTX 3050 Laptop GPU confirmed active (`CUDA Available: True`, `cuDNN 90100`).
2. **Video-Level Split Execution (`scripts/create_video_splits.py`)**:
   - Processed all 489 glosses possessing $\ge 3$ video recordings (total 1,475 videos).
   - Applied dialect stratification: Northern (`B`) $\to$ Train, Central (`T`) $\to$ Val, Southern (`N`) $\to$ Test. Extra recordings ($>3$) assigned to Train.
   - Partitioned Tier 2: 489 classes (Train: 497, Val: 489, Test: 489).
   - Curated Tier 1: 50 classes representing high-frequency communication vocabulary (Train: 58, Val: 50, Test: 50).
   - Saved `configs/tier1_classes.txt` and all split CSVs to `data/splits/`.
3. **Clean Landmark Extractor (`src/data/landmark_extractor.py`)**:
   - Implemented `CleanHolisticExtractor` for 67 joints ($25$ upper pose + $21$ LH + $21$ RH).
   - **Enforced Strict Rule: NO ZERO-FILL**: Missing joints retain $(x,y,z) = \text{NaN}$ and explicit visibility mask $= 0.0$.
   - Output structured format: `keypoints` $[T, 67, 3]$, `visibility_mask` $[T, 67]$, and `keypoints_4d` $[T, 67, 4]$.
4. **Sequence Generator (`src/data/sequence_generator.py`)**:
   - Implemented padding/cropping with boolean frame presence masks.
   - Implemented sliding window chunking and uniform temporal resampling.
5. **Dry Run Extraction (`scripts/dry_run_extraction.py`)**:
   - Executed extraction on 12 raw videos across 3 representative Tier 1 classes (`thương yêu`, `anh em`, `bông hoa`) across Train, Val, and Test splits.
   - Verified zero crashes, exact output shapes `[T, 67, 3]`, visibility masks `[T, 67]`, and successful `.npz` storage and reloading.
6. **Automated Leakage Audit (`scripts/check_data_leakage.py`)**:
   - Ran formal leakage checks across all generated splits:
     - Video ID overlap: **0**
     - Filename overlap: **0**
     - File hash duplicate overlap: **0**
     - Class coverage: **100% synchronized (50 classes for Tier 1, 489 classes for Tier 2)**.

---

## 3. Files Created / Changed

| File | Purpose |
| :--- | :--- |
| `configs/tier1_classes.txt` | Approved 50 Core vocabulary classes |
| `configs/vsl_config.yaml` | Master YAML configuration replacing old hardcoded settings |
| `scripts/create_video_splits.py` | Video-disjoint split generator script |
| `scripts/check_data_leakage.py` | Automated split leakage auditor |
| `src/data/landmark_extractor.py` | MediaPipe 67-joint extractor without zero-fill |
| `src/data/sequence_generator.py` | Sequence padding, masking, and window generator |
| `scripts/dry_run_extraction.py` | Phase 1 extraction verification script |
| `data/splits/tier1_train.csv` | Tier 1 training split (58 videos, 50 classes) |
| `data/splits/tier1_val.csv` | Tier 1 validation split (50 videos, 50 classes) |
| `data/splits/tier1_test.csv` | Tier 1 test split (50 videos, 50 classes) |
| `data/splits/tier1_50_all.csv` | Full Tier 1 metadata (158 videos) |
| `data/splits/tier2_train.csv` | Tier 2 training split (497 videos, 489 classes) |
| `data/splits/tier2_val.csv` | Tier 2 validation split (489 videos, 489 classes) |
| `data/splits/tier2_test.csv` | Tier 2 test split (489 videos, 489 classes) |
| `data/splits/tier2_489_all.csv` | Full Tier 2 metadata (1,475 videos) |
| `data/dry_run_extracted/` | Sample extracted `.npz` files for 3 classes across splits |

---

## 4. Evidence & Validation Results

### 4.1 Dry Run Verification Output
```
All 12 dry-run extractions completed with 100% SUCCESS.
Shapes verified: keypoints=(T, 67, 3), visibility_mask=(T, 67)
Missing landmarks verified: NaN with visibility=0.0 (NO ZERO-FILL)
SequenceGenerator test: Successfully resized to (60, 67, 3) with valid frame masks
Reload verification: 100% PASS
```

### 4.2 Leakage Checker Verification Output
```
FINAL AUDIT VERDICT: ZERO DATA LEAKAGE CONFIRMED ACROSS ALL TIERS.
Train & Val overlap: 0
Train & Test overlap: 0
Val & Test overlap: 0
File Hash overlap: 0
Tier 1: 50 classes strictly synchronized
Tier 2: 489 classes strictly synchronized
```

---

## 5. Acceptance Criteria Checklist

- [x] PyTorch CUDA operational on RTX 3050 Laptop GPU (`torch.cuda.is_available() = True`).
- [x] Strict video-disjoint split created for 489 classes and 50 classes.
- [x] Tier 1 class list saved to `configs/tier1_classes.txt`.
- [x] MediaPipe 67-joint extractor implemented with NO zero-fill.
- [x] `SequenceGenerator` implemented.
- [x] Dry run completed on sample classes with verified output shapes and reloadability.
- [x] Data leakage check passed with 0% overlap.
- [x] `configs/vsl_config.yaml` created.
- [x] `phase_state.json` updated.

---

## 6. Status & Next Phase Readiness

* **Phase 1 Status:** **PASS**
* **Next Phase:** **Phase 2 — Data Split & Preprocessing Pipeline** (Spatial/temporal normalization, interpolation for missing landmarks, dataset feature generation).
* **Next Action:** Ready to proceed to Phase 2 upon user command.
