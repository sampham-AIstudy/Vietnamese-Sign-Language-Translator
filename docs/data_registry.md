# Vietnamese Sign Language Translator (VSLT) — Data Registry

This document serves as the single source of truth for all datasets integrated, canonicalized, or archived within the VSLT repository.

Last Updated: **2026-09-24** (audit round 3 corrections)

---

## 1. Current QIPEDC Isolated Dataset (Isolated VSLR)

- **Dataset**: QIPEDC Isolated Sign Language Corpus
- **Purpose**: Isolated sign language recognition (ISLR) across 50 core classes (Tier 1) and 489 extended classes (Tier 2).
- **Source**: Raw recordings from the QIPEDC Vietnamese Sign Language dictionary (`data (2)/Dataset/Videos/`).
- **Commit**: Local dataset integration (Phase 1, commit baseline `2026-09-12`).
- **License**: Educational / Academic research use (Ministry of Education & Training / QIPEDC project).
- **Samples**:
  - Total cataloged: 1,475 raw video clips across 489 gloss classes ($\ge 3$ video recordings per class).
  - Tier 1 (Core 50 classes): 158 videos (Train: 58, Val: 50, Test: 50).
  - Tier 2 (Extended 489 classes): 1,475 videos (Train: 497, Val: 489, Test: 489).
- **Signers**: ~8–10 signers (studio, uniform); **the same signers perform all three regional variants** — B/T/N labels denote the regional *sign variant* (burned into the video caption by the source), not the signer's region. No signer IDs (0/4,362); Deaf status unverified. (Audit round 3, `reports/audit_round3/PROVENANCE.md`.)
- **Duplicate recordings**: QIPEDC reuses one clip for several regions when the sign is identical (only the caption changes): 4,362 videos = 3,946 distinct recordings. `data/splits/recording_groups.csv` (scripts/build_recording_groups.py) maps each video to its recording; splits must keep a group together (`tier1_grouped_*` / `tier2_grouped_*`, enforced by `DuplicateRecordingLeakageError`). Only 101 glosses have ≥ 3 distinct recordings.
- **Views**: Frontal view only.
- **Feature Shape**: $[T, 67, 3]$ float32 keypoints with $[T, 67]$ visibility mask (25 upper-body pose + 21 left hand + 21 right hand; strict NO ZERO-FILL policy with NaNs and visibility=0.0).
- **Annotations**: Class-level gloss labels (`tier1_classes.txt`, split CSVs).
- **Splits**: Dialect-stratified video-disjoint splits:
  - ~~Train: Northern (`B`) / Val: Central (`T`) / Test: Southern (`N`)~~ — legacy; T/N copies of one recording ended up in val and test.
  - Active: recording-grouped folds `data/splits/folds/{tier1,tier2}_grouped_{train,val,test}.csv` (scripts/create_grouped_splits.py).
- **Known Limitations**:
  - Small sample count per class (~3 videos/class, 1 per dialect), limiting signer variance.
  - Isolated sign only; cannot be used for continuous sentence translation without synthetic chaining.
- **How to Regenerate**:
  ```powershell
  .\.venv\Scripts\python.exe scripts/build_recording_groups.py
  .\.venv\Scripts\python.exe scripts/create_grouped_splits.py --tier tier2
  .\.venv\Scripts\python.exe scripts/build_unified_manifest.py
  ```
- **Active / Archive Status**: **Active** (Production baseline for ST-GCN isolated recognition).

---

## 2. VSL-GH (Continuous VSL Sign Language Translation)

- **Dataset**: VSL-GH (Vietnamese Sign Language - Gloss & Hand)
- **Purpose**: Continuous Sign Language Recognition (CSLR) and Sign Language Translation (SLT) with full sentence temporal boundary modeling.
- **Source**: `https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git`
- **Commit**: `6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a`
- **License**: **MIT License** (Copyright (c) 2026 VSL-GH Dataset Authors).
- **Samples**:
  - Exactly 4,200 frontal video recordings (300 unique sentences $\times$ 14 repetitions across 6 signers).
  - Exactly 4,200 frontal keypoint sequences in `data/external/vsl_gh/keypoints_frontal/`.
  - 1,830 lateral (side-view) keypoint sequences exist upstream (not kept locally; re-clone upstream if needed).
- **Signers**: 6 independent signers (S01, S02, S03, S04, S05, S06).
- **Views**: Dual-camera (Frontal `_F` active in production; Lateral `_S` archived).
- **Feature Shape**:
  - Raw canonical keypoint files: $[T, 411]$ float32 (MediaPipe Holistic: 25 pose, 70 face, 21 left hand, 21 right hand $\times$ 3 coordinates).
  - Adapter-converted representation: $[T, 67, 3]$ float32 (Pose 25 + Left Hand 21 + Right Hand 21) or $[T, 67, 6]$ with velocity.
- **Annotations**:
  - Dense word-level gloss temporal boundaries (`HH:MM:SS.mmm` start and end times).
  - Vietnamese spoken natural language sentence translations.
  - Fully regenerated in `data/external/vsl_gh/dataset_canonical.json` (resolving audit issue where SENT151–SENT300 had empty gloss sequences in original JSON).
- **Splits**:
  - Signer-independent: Train (S01..S04, 3,600 samples), Val (S05, 300 samples), Test (S06, 300 samples).
  - Leave-One-Signer-Out (LOSO): 6 folds (`dataset_loso_s01.json` to `dataset_loso_s06.json`).
- **Known Limitations**:
  - Controlled green-screen studio environment (high landmark clarity, lower visual noise than wild conditions).
  - 2 original annotation files had missing entries in upstream commit (`SENT236_S01_R03_F` and `SENT285_S04_R03_F`). **Their annotations are hand-written by this project** in `scripts/prepare_canonical_vsl_gh.py` (glosses copied from sister repetitions, boundaries estimated from `.npy` length) — not upstream labels; both are in train.
- **How to Regenerate**:
  ```powershell
  .\.venv\Scripts\python.exe scripts/prepare_canonical_vsl_gh.py
  ```
- **Active / Archive Status**: **Active** (`data/external/vsl_gh/`); side-view keypoints not kept (available upstream).

---

## 3. Parallel-Corpus-Vie-VSL (Text Translation Corpus)

- **Dataset**: Parallel Corpus Vie-VSL 10k
- **Purpose**: Translation module training / fine-tuning (Gloss-to-Text translation; e.g., BART-Pho / ViT5).
- **Source**: `https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git`
- **Commit**: `f57558c3fa79ced8a961cba825157c573fd4c74d`
- **License**: Open access for research and educational purposes.
- **Samples**:
  - Source lines: 10,000 paired lines (`VSL10k.txt` & `Vie10k.txt`).
  - Canonical deduplicated pairs: 9,405 unique aligned pairs in `data/external/parallel_text/vie_vsl_10k.jsonl`.
  - Duplicate pairs removed: 595 pairs.
- **Signers**: N/A (Textual parallel corpus).
- **Views**: N/A.
- **Feature Shape**: Textual JSONL: `{"id": "...", "vsl": "...", "vi": "..."}`.
  - VSL vocabulary: 3,764 unique tokens.
  - Vietnamese vocabulary: 3,774 unique tokens.
- **Annotations**: Aligned VSL gloss token sequences $\leftrightarrow$ Natural spoken Vietnamese sentences.
- **Splits**: Monolithic 9,405 corpus; downstream split strategy: 8,405 train / 500 val / 500 test (or 90/5/5 split).
- **Known Limitations**:
  - High duplicate rate (595 exact duplicates among 10k lines).
  - `Corpus-Vie-VSL-10K.xlsx` diverges from the text files on 2,295 lines (punctuation and minor phrasing variations).
  - Construction method is not documented upstream (neither "rule-generated" nor "translated by Deaf signers" is verified). 9,404/9,405 canonical pairs match upstream verbatim (audit round 3).
- **How to Regenerate**:
  ```powershell
  .\.venv\Scripts\python.exe scripts/prepare_canonical_translation.py
  ```
- **Active / Archive Status**: **Active** (`data/external/parallel_text/vie_vsl_10k.jsonl`); Lexicon available upstream (`VSL-Lexicon.rar` in the upstream repo).

---

## 4. Multi-VSL_WACV_2025 Reference Dataset

- **Dataset**: Multi-VSL WACV 2025
- **Purpose**: Academic benchmark reference for multi-view sign language recognition, vocabulary taxonomy (1,000 classes), and cross-model comparison.
- **Source**: `https://github.com/Etdihatthoc/Multi-VSL_WACV_2025.git`
- **Commit**: `943eed8954f761e02e76b17b8b2322bb5243615c`
- **License**: Unspecified in repository / academic paper citation.
- **Samples**:
  - Upstream catalog: >84,000 multi-view RGB videos across 1,000 glosses and 30 signers (hosted externally on Google Drive).
  - Retained in repository: 13 split CSVs for 1,000 glosses, 12 CSVs for 400 glosses, 13 CSVs for 200 glosses.
- **Signers**: 30 native signers.
- **Views**: 3 camera views (Frontal, Left 45°, Right 45°).
- **Feature Shape**: RGB video frames ($224 \times 224$ or original resolution).
- **Annotations**: Video URL / file paths and class gloss labels (subsets of 200, 400, and 1,000 classes).
- **Splits**: Official train / val / test CSV splits provided in `data/label_1_1000/`, `data/label_1_400/`, `data/label_1_200/`.
- **Known Limitations**:
  - Raw video data (>84,000 videos) is hosted on Google Drive and is neither checked in nor imported into the active VSLT pipeline.
  - Video models require heavy 3D-CNN / Vision Transformer infrastructure (I3D, SlowFast, VideoMAE) incompatible with edge MediaPipe skeleton inference.
- **How to Regenerate**: not kept locally (only split CSVs were ever available; the public Drive link holds ~50 demo videos). Re-clone upstream if needed.
- **Active / Archive Status**: **Reference Only** (Configs and split labels retained; 11.94 GB checkpoints and 795 MB demo videos deleted).
