# BLOCKER REPORT — VSLR Project

**CURRENT PHASE:** Phase 0 — Full Audit / Baseline  
**PHASE STATUS:** BLOCKED  
**TIMESTAMP:** 2026-09-12 12:56:00  

---

### BLOCKER TYPE:
- `dataset_missing`
- `mapping_unknown`
- `leakage`
- `cuda`

---

### EVIDENCE:

1. **Target Dataset Missing**:
   - The master prompt specifies a target dataset: *472 glosses, [T, 76, 3] shape, `processed/`, `processed_augmented/`, `raw/`, `keypoints_splited/`, `frame_splited/`*.
   - A recursive scan across all directories on `C:\` (`C:\Users\Admin`, `Downloads`, `Documents`, `Desktop`, `Python Advanced`) confirmed that no such dataset, directory names, or files exist.
   - The actual dataset on disk is `data (2)/`:
     - `data (2)/Dataset/Videos/`: 4,362 MP4 files.
     - `data (2)/Dataset/Labels/label.csv`: 4,362 video entries mapping to 3,315 unique glosses.
     - `data (2)/Processed/`: 184,295 `.npz` files of shape `(60, 201)`.
   - No file in the repository or filesystem has shape `[T, 76, 3]`.

2. **76-joint Semantic Mapping Unknown**:
   - The repository code (`src/data/extract_landmarks.py`, `src/models/stgcn.py`) exclusively implements **67 joints** ($201$ dimensions = $25$ pose + $21$ left hand + $21$ right hand $\times 3$).
   - Nowhere in the codebase, configs, papers in `reference/`, or filesystem is a 76-joint mapping defined.
   - Master Prompt Rule 0 & Rule 3 explicitly prohibit: *"giả định 76 joints = 33 pose + 21 left hand + 21 right hand + face nếu không có bằng chứng"* and *"Nếu thiếu bằng chứng, phải đánh dấu BLOCKED"*.

3. **Critical Data Leakage in Current Preprocessed Dataset**:
   - `data (2)/Processed/` contains 184,295 `.npz` files derived from only 4,362 raw videos.
   - For example, gloss `địa chỉ` has only 3 raw videos (`D0001B.mp4`, `D0001N.mp4`, `D0001T.mp4`), but has 98 samples in `train/`, 12 in `val/`, and 13 in `test/`.
   - Direct cosine similarity between `train/địa chỉ/0.npz` and `val/địa chỉ/1.npz` is **0.9937**; between `train/địa chỉ/0.npz` and `test/địa chỉ/4.npz` is **0.9943**.
   - 654 sample pairs between `val` and `train` have cosine similarity $> 0.99$.
   - Slicing and temporal windowing/augmentation were executed **before** splitting, contaminating the validation and test sets.

4. **CUDA Environment**:
   - Physical hardware: NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM), Driver 566.36, CUDA 12.7.
   - Active Python virtualenv (`.\.venv\Scripts\python.exe`) has PyTorch installed as `2.14.0+cpu`.
   - `torch.cuda.is_available()` returns `False`.

---

### WHY IT BLOCKS:

1. Under Rule 1 (Phase Gating) & Rule 9 (Stop on Blocker):
   - *"Nếu gặp bất kỳ điều nào sau đây, phải dừng ngay: dataset không tồn tại như kỳ vọng; không xác định được 76-joint mapping; có leakage nghiêm trọng; CUDA cần cho phase nhưng không available."*
2. Phase 1 cannot integrate a 472-gloss `[T,76,3]` dataset because that dataset does not exist on disk.
3. Phase 1 cannot construct a 76-joint skeleton topology because the joint semantic mapping is unknown and unverified.
4. Continuing on the existing `data (2)/Processed` splits would violate Rule 4 (No Data Leakage) and produce invalid benchmark numbers.

---

### WHAT WAS TRIED:

1. Searched all local filesystem paths, user directories, Downloads, Desktop, Documents for `472`, `Cropped`, `keypoints_splited`, `frame_splited`, `processed_augmented`.
2. Inspected git log, commit history, and branches for any previous commits or references to 76 joints or 472 classes.
3. Grepped all repository `.py`, `.yaml`, `.json`, `.md` files for `76` and `472`.
4. Extracted text and searched both reference PDFs (`reference/12 25068...pdf` and `reference/24065...pdf`) for keyword matches.
5. Inspected `data (2)/Processed` `.npz` files and calculated pairwise cross-split MSE and cosine similarity, demonstrating empirical proof of data leakage.
6. Checked `nvidia-smi` and `torch.cuda.is_available()`.

---

### MINIMAL INFO NEEDED FROM USER:

1. **Dataset Location & Target Scope**:
   - Is there an external path or download link for the "VSL 472 glosses / [T,76,3] Cropped" dataset?
   - OR is the intended goal to use the **existing 4,362 raw videos (`data (2)/Dataset/Videos`)** and re-extract landmarks cleanly from scratch with an agreed landmark schema?
2. **Joint Topology / Dimensionality**:
   - If the 472-gloss dataset exists elsewhere, what is the exact 76-joint index layout?
   - If using the existing 4,362 videos, do we adopt MediaPipe Holistic 67 joints ($25$ pose + $21$ LH + $21$ RH $= 201$ dims) or a specified 76-joint schema (e.g., $33$ pose + $21$ LH + $21$ RH + $1$ nose/face)?
3. **PyTorch CUDA Acceleration**:
   - Confirmation to install CUDA-enabled PyTorch (`torch` with `cu121` or `cu124`) into `.venv` so subsequent training and evaluation phases can use the RTX 3050 GPU.

---

### PROPOSED OPTIONS:

* **Option 1 (Provide External Dataset)**:
  User provides the exact path or archive for the *VSL 472 glosses [T,76,3]* dataset and its joint specification. We integrate it in Phase 1.
* **Option 2 (Build Clean Pipeline on Existing VSL Dataset)**:
  Use the existing raw dataset (`data (2)/Dataset/Videos`, 4,362 videos across 3,315 glosses or a selected benchmark subset such as top 40 / 50 / 100 glosses):
  - Extract landmarks cleanly using MediaPipe Holistic without zero-padding.
  - Formulate a strict **source-video-disjoint split** (train / val / test) directly from the raw 4,362 videos to eliminate all data leakage.
  - Augment only the training split.
* **Option 3 (Hybrid / User-specified Subset)**:
  Filter the existing 4,362 videos to glosses with multiple dialect recordings (e.g. B, T, N) to ensure sufficient support per class for statistical validity on RTX 3050.

---

### RECOMMENDED NEXT ACTION:

Pause autonomous execution at Phase 0. Await user clarification regarding the 472-gloss dataset location and 76-joint specification, or authorization to proceed with Option 2 on the existing raw video corpus with strict video-disjoint partitioning.
