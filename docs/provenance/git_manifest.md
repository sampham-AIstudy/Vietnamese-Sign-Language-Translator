# Git Repositories Manifest & Retention Recommendation

This document records the exact Git metadata of all external cloned repositories, quantifies the disk space occupied by `.git` metadata, and provides explicit recommendations on repository retention.

Recorded Date: **2026-09-21**

---

## 1. Upstream Git Repositories Metadata

| Attribute | Multi-VSL_WACV_2025 | Parallel-Corpus-Vie-VSL | Vietnamese-Sign-Language-Translation |
| :--- | :--- | :--- | :--- |
| **Repository Directory** | `clone/Multi-VSL_WACV_2025` | `clone/Parallel-Corpus-Vie-VSL` | `clone/Vietnamese-Sign-Language-Translation` |
| **Remote URL** | `https://github.com/Etdihatthoc/Multi-VSL_WACV_2025.git` | `https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git` | `https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git` |
| **Commit (HEAD)** | `943eed8954f761e02e76b17b8b2322bb5243615c` | `f57558c3fa79ced8a961cba825157c573fd4c74d` | `6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a` |
| **Active Branch** | `main` | `main` | `main` |
| **Date Cloned / Added**| 2026-09-18 | 2026-09-18 | 2026-09-18 |
| **License** | Unspecified / Academic paper | Research / Educational only | MIT License |
| **Citation** | WACV 2025 Multi-view SLR | BichDiep Parallel Vie-VSL | VSL-GH Dataset (2026) |

---

## 2. Measured Disk Space Analysis of `.git` Directories

| Repository `.git` Path | Size (Bytes) | Size (MB) | File Count |
| :--- | :--- | :--- | :--- |
| `clone/Multi-VSL_WACV_2025/.git` | 4,970,006 bytes | 4.74 MB | 28 files |
| `clone/Parallel-Corpus-Vie-VSL/.git` | 16,935,241 bytes | 16.15 MB | 28 files |
| `clone/Vietnamese-Sign-Language-Translation/.git` | 920,792,204 bytes | 878.14 MB | 28 files |
| **Total `.git` Storage** | **942,697,451 bytes** | **899.03 MB (~0.88 GB)** | **84 files** |

---

## 3. Analysis & Recommendation

### Can `.git` directories be safely removed in the future?
1. **Reproducibility**: All three upstream remotes and their commit hashes are immutable git refs on GitHub. Any repository can be re-cloned on demand:
   ```bash
   git clone https://github.com/Etdihatthoc/Multi-VSL_WACV_2025.git
   git clone https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git
   git clone https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git
   ```
2. **Canonical Extraction Complete**: All active assets needed for training and inference have been extracted into canonical locations:
   - `data/external/vsl_gh/`
   - `data/external/parallel_text/`
   - `docs/provenance/archive/`
3. **Space Savings**:
   - Deleting `.git` inside the three clone directories would reclaim **~899 MB** of disk space (principally ~878 MB from VSL-GH's git history which tracks earlier keypoint commits).

### Current Execution Decision:
- In strict adherence to Rule 10, **`.git` directories are NOT removed during this cleanup run**.
- Retaining `.git` preserves local verification capability and git tracking during the initial review of the canonical data preparation.
- Once the canonical data adapter and pipelines are approved, removing `.git` from `clone/` or replacing `clone/` with an archived artifact can reclaim the ~899 MB without loss of information.
