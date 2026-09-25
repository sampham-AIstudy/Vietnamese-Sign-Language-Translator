# External Repositories Provenance Manifest

This manifest documents the provenance, commit hashes, license terms, integration date, and lifecycle status of external repositories integrated into the **Vietnamese Sign Language Translator (VSLT)** project.

Date of integration: **2026-09-21**

---

## 1. Multi-VSL_WACV_2025

- **Repository**: `Multi-VSL_WACV_2025`
- **Remote URL**: `https://github.com/Etdihatthoc/Multi-VSL_WACV_2025.git`
- **Commit**: `943eed8954f761e02e76b17b8b2322bb5243615c`
- **Branch**: `main`
- **Original Clone Path**: `clone/Multi-VSL_WACV_2025`
- **Original Size**: 12.7735 GB (13,715,472,930 bytes across 1,221 files)
- **License / Citation Information**:
  - *License*: Unspecified in repository (no dedicated `LICENSE` file provided).
  - *Citation*: WACV 2025 Paper: *"Multi-view Sign Language Recognition"*. Dataset spanning 1,000 glosses and 30 signers (>84,000 multi-view videos).
- **Assets Retained**:
  - `configs/` (57 model/training YAML configs)
  - `data/label_1_1000/` (13 annotation/label CSV split files)
  - `data/label_1_400/` (12 annotation/label CSV split files)
  - `data/label_1_200/` (13 annotation/label CSV split files)
  - `dataset/`, `inference_config/`, `modelling/`, `tools/`, `trainer/`, `utils/`
  - `main.py`, `README.md`, `requirements.txt`, `.gitignore`, `.git`
- **Assets Archived**: None
- **Assets Deleted**:
  - `data/Check point/` (11.9401 GB, 53 untracked checkpoint files; not tracked by git, available via upstream Google Drive)
  - `data/video data/` (0.7946 GB, 1,000 untracked/ignored demo MP4 videos; not tracked by git, ignored via `.gitignore` `*.mp4`)
- **Integration Role**: Academic reference for multi-view architectures, vocabulary definitions, and experimental benchmarks. Not imported into production inference or ST-GCN pipeline.

---

## 2. Parallel-Corpus-Vie-VSL

- **Repository**: `Parallel-Corpus-Vie-VSL`
- **Remote URL**: `https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git`
- **Commit**: `f57558c3fa79ced8a961cba825157c573fd4c74d`
- **Branch**: `main`
- **Original Clone Path**: `clone/Parallel-Corpus-Vie-VSL`
- **Original Size**: 0.0342 GB (36,734,875 bytes across 37 files)
- **License / Citation Information**:
  - *License*: Open access for research and educational purposes only (*"This dataset is intended for research and educational purposes only. Always cite this repository when using the data in your work."*). No formal SPDX license file.
  - *Citation*: BichDiep, *Parallel-Corpus-Vie-VSL* (GitHub repository).
- **Assets Retained**:
  - `VSL10k.txt` (10,000 parallel VSL sentences)
  - `Vie10k.txt` (10,000 parallel Vietnamese sentences)
  - `Vie-Traveling.xlsx` (domain-specific traveling corpus)
  - `Vie10k_phantich.txt` & `VSL10k_phantich.txt` (syntactic/morphological analysis)
  - `Corpus-Vie-VSL-10K.xlsx` (retained in clone: 2,295 textual/punctuation discrepancies detected compared to text files, preventing deletion)
  - `README.md`, `.git`
- **Assets Archived**:
  - `VSL-Lexicon.rar` (3,211,262 bytes) -> copied to `docs/provenance/archive/VSL-Lexicon.rar` (contains ~7,000-word VSL lexical resource)
- **Assets Deleted**:
  - `Parallel Corpus Vie-VSL.rar` (8,405,920 bytes) — deleted after 100% SHA256 verification confirmed it was an exact duplicate container of unpacked files.
- **Integration Role**: Ground-truth parallel text corpus for Gloss-to-Text translation; canonical JSONL extracted to `data/external/parallel_text/vie_vsl_10k.jsonl`.

---

## 3. Vietnamese-Sign-Language-Translation (VSL-GH)

- **Repository**: `Vietnamese-Sign-Language-Translation`
- **Remote URL**: `https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git`
- **Commit**: `6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a`
- **Branch**: `main`
- **Original Clone Path**: `clone/Vietnamese-Sign-Language-Translation`
- **Original Size**: 1.8696 GB (2,007,475,939 bytes across 10,416 files)
- **License / Citation Information**:
  - *License*: **MIT License** (Copyright (c) 2026 VSL-GH Dataset Authors)
  - *Citation*: VSL-GH: Vietnamese Sign Language Dataset (dual-camera frontal/lateral, 6 signers, 300 sentences, temporal gloss boundaries)
- **Assets Retained**:
  - Cloned repository source code: `source/`, `scripts/`, `eval_*.sh`, `start_*.sh`, `LICENSE`, `README.md`
  - Cloned data files: `data/dataset.json`, `data/dataset_stats.json`, `data/gloss_vocab.txt`, `data/trans_vocab.txt`, `data/splits/`, `data/annotations/`, `data/keypoints/`
  - Canonical External Data Layer created at `data/external/vsl_gh/`:
    - `keypoints_frontal/` (4,200 frontal `.npy` files)
    - `annotations/` (4,200 annotation files)
    - `splits/` (`train.txt`, `val.txt`, `test.txt`, `dataset_loso_s01.json` ... `dataset_loso_s06.json`)
    - `dataset_canonical.json` (regenerated metadata curing incomplete gloss sequences for SENT151–SENT300)
    - `gloss_vocab.txt`, `trans_vocab.txt`, `dataset_stats.json`
- **Assets Archived**:
  - Lateral (side-view) keypoints (1,830 `.npy` files) -> copied to `docs/provenance/archive/vsl_gh_side_view/`
- **Assets Deleted**: None (all source files in clone preserved)
- **Integration Role**: Continuous VSL sign language recognition and translation dataset (MediaPipe Holistic 137 landmarks / 411 dimensions, convertible to 67-joint [T, 67, 3] layout).
