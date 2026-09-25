# VSL-GH Continuous Dataset Adapter Documentation

This document describes the design, architecture, landmark mapping, temporal conversions, vocabulary management, and evaluation integrity of the **VSL-GH Continuous Dataset Adapter** implemented in `src/data/vsl_gh_dataset.py`.

---

## 1. Dataset Origin & Provenance

- **Dataset**: VSL-GH (Vietnamese Sign Language - Gloss & Hand)
- **Source Repository**: `https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git`
- **Commit**: `6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a`
- **License**: MIT License (Copyright (c) 2026 VSL-GH Dataset Authors)
- **Primary Domain**: Continuous Sign Language Recognition (CSLR) and Sign Language Translation (SLT).
- **Environment**: Green-screen studio recording, dual-camera (Frontal and Lateral/Side view).
- **Canonical Storage Location**:
  - Frontal keypoints: `data/external/vsl_gh/keypoints_frontal/*.npy` (4,200 files)
  - Annotations: `data/external/vsl_gh/annotations/*.txt` (4,206 files)
  - Metadata: `data/external/vsl_gh/dataset_canonical.json` (4,200 entries)
  - Vocabularies: `data/external/vsl_gh/gloss_vocab_canonical.txt` (372 tokens)

---

## 2. Landmark Layout & 137 $\to$ 67 Conversion

### 2.1 Upstream VSL-GH Landmark Scheme
Raw keypoint files store MediaPipe Holistic features of shape $[T, 411]$ (`float32`), representing 137 landmarks $\times$ 3 coordinates $(x, y, z)$:
- **Pose**: 25 landmarks (dims 0..74)
  `POSE_LANDMARKS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28]`
  *(Note: VSL-GH skipped MediaPipe 9, 10 [mouth corners] and 21, 22 [thumbs], but retained 25..28 [knees, ankles]).*
- **Face**: 70 landmarks (dims 75..284) from MediaPipe FaceMesh (including lip contour).
- **Left Hand**: 21 landmarks (dims 285..347), standard MediaPipe Hands 0..20.
- **Right Hand**: 21 landmarks (dims 348..410), standard MediaPipe Hands 0..20.

### 2.2 Target Project 67-Joint Scheme (QIPEDC / CleanHolistic)
The project's anatomical ST-GCN graph (`src/models/graph.py`) defines 67 joints:
- Joints 0..24: Upper-body pose (MediaPipe Pose 0..24)
- Joints 25..45: Left hand (MediaPipe Hands 0..20)
- Joints 46..66: Right hand (MediaPipe Hands 0..20)

### 2.3 Explicit Landmark Mapping Table
The adapter implements `convert_137_to_67(keypoints, mode)` supporting two deterministic modes:

| Target Joint Index | Anatomical Name | Direct Mode Source | Semantic Mode Source |
| :--- | :--- | :--- | :--- |
| **0** | Nose | VSL-GH Pose [0] (MP 0) | VSL-GH Pose [0] (MP 0) |
| **1..8** | Eyes & Ears | VSL-GH Pose [1..8] (MP 1..8) | VSL-GH Pose [1..8] (MP 1..8) |
| **9** | Mouth Left | VSL-GH Pose [9] (MP 11)* | VSL-GH Face [0] (FaceMesh 61) |
| **10** | Mouth Right | VSL-GH Pose [10] (MP 12)* | VSL-GH Face [10] (FaceMesh 291) |
| **11, 12** | Shoulders (L, R) | VSL-GH Pose [11, 12] (MP 13, 14)*| VSL-GH Pose [9, 10] (MP 11, 12) |
| **13, 14** | Elbows (L, R) | VSL-GH Pose [13, 14] (MP 15, 16)*| VSL-GH Pose [11, 12] (MP 13, 14) |
| **15, 16** | Wrists (L, R) | VSL-GH Pose [15, 16] (MP 17, 18)*| VSL-GH Pose [13, 14] (MP 15, 16) |
| **17, 18** | Pinkies (L, R) | VSL-GH Pose [17, 18] (MP 19, 20)*| VSL-GH Pose [15, 16] (MP 17, 18) |
| **19, 20** | Indices (L, R) | VSL-GH Pose [19, 20] (MP 23, 24)*| VSL-GH Pose [17, 18] (MP 19, 20) |
| **21, 22** | Thumbs (L, R) | VSL-GH Pose [21, 22] (MP 25, 26)*| Left Hand [4] & Right Hand [4] |
| **23, 24** | Hips (L, R) | VSL-GH Pose [23, 24] (MP 27, 28)*| VSL-GH Pose [19, 20] (MP 23, 24) |
| **25..45** | Left Hand (21) | VSL-GH Left Hand (dims 285..348) | VSL-GH Left Hand (dims 285..348) |
| **46..66** | Right Hand (21)| VSL-GH Right Hand (dims 348..411)| VSL-GH Right Hand (dims 348..411)|

*Recommendation*: `mode="direct"` extracts VSL-GH's native 25 pose landmarks $[0..24]$ without altering joint dynamics. `mode="semantic"` provides strict anatomical alignment with the pre-existing QIPEDC spatial adjacency graph. Both modes are unit-tested and verified.

---

## 3. Optional Velocity Features

When initialized with `use_velocity=True`:
$$\mathbf{v}[t] = \begin{cases} \mathbf{0}, & t = 0 \\ \mathbf{x}[t] - \mathbf{x}[t-1], & t \ge 1 \end{cases}$$
The returned keypoint tensor has shape $[T, 67, 6]$ where channels 0..2 are $(x, y, z)$ and channels 3..5 are $(v_x, v_y, v_z)$.
Default: `use_velocity=False` (shape $[T, 67, 3]$).

---

## 4. Temporal Annotations & Frame Conversion

VSL-GH ground-truth annotations provide millisecond timestamps in `HH:MM:SS.mmm` format:
```
Gloss       00:00:00.010    00:00:00.860    TÔI
Gloss       00:00:00.860    00:00:01.430    HẸN
Translation 00:00:00.000    00:00:03.000    Tôi có phải chờ lâu không?
```

The adapter converts each boundary using sample-specific FPS:
$$\text{start\_ms} = H \times 3.6\times 10^6 + M \times 6\times 10^4 + S \times 10^3 + ms$$
$$\text{start\_frame} = \text{clip}\left(\text{round}\left(\frac{\text{start\_ms} \times \text{fps}}{1000}\right), 0, T\right)$$
$$\text{end\_frame} = \text{clip}\left(\text{round}\left(\frac{\text{end\_ms} \times \text{fps}}{1000}\right), \text{start\_frame}, T\right)$$

---

## 5. Gloss Vocabulary Management

Vocabulary is managed by `VSLGlossVocabulary`:
- **Explicit Blank Index**: `0` (`<blank>` reserved for CTC decoding).
- **Explicit Unknown Index**: `1` (`<unk>`).
- **Target Vocabulary**: Indices `2..371` (370 unique target glosses sorted alphabetically).
- **Unknown Handling**: Explicit policy (`handle_unknown='unk'` or `'error'`). Unseen tokens are never silently mapped to 0 or padding.

---

## 6. Translation Target

Vietnamese spoken translations are preserved as un-tokenized, UTF-8 NFC normalized strings (`sample["translation"]`). Tokenization is decoupled from vision feature loading, allowing seamless integration with downstream translation tokenizers (e.g. ViT5, PhoBERT).

---

## 7. Variable-Length Collation & CTC Target Format

`vslgh_collate_fn()` stacks variable-length batches:
- `features`: $[B, \max(T), 67, C]$ (`float32`, zero-padded)
- `features_stgcn`: $[B, C, \max(T), 67]$ (`float32`, permuted for ST-GCN spatial convolution)
- `joint_masks`: $[B, \max(T), 67]$ (`float32`, 1.0 for detected joints, 0.0 for missing/padded)
- `temporal_masks`: $[B, \max(T)]$ (`float32`, 1.0 for valid frames, 0.0 for padded frames)
- `lengths`: $[B]$ (`int64`, actual frame lengths $T_i$)
- `gloss_targets`: 1D concatenated tensor $[ \sum \text{gloss\_lengths} ]$ (`int64`, for standard PyTorch `nn.CTCLoss`)
- `gloss_targets_padded`: 2D padded tensor $[B, \max(\text{gloss\_length})]$ (`int64`)
- `gloss_lengths`: $[B]$ (`int64`, gloss token counts)
- `sample_ids`, `translations`, `annotation_sources`: Python lists of length $B$

---

## 8. Split & Signer Partitioning

### 8.1 Signer-Independent Splits
- **Train Split**: Signers S01, S02, S03, S04 $\times$ 3 repetitions = **3,600 samples**.
- **Val Split**: Signer S05 $\times$ 1 repetition = **300 samples** (unseen signer).
- **Test Split**: Signer S06 $\times$ 1 repetition = **300 samples** (unseen signer).
- **Disjointness**: 0 sample overlap, 0 signer overlap across train/val/test.

### 8.2 Leave-One-Signer-Out (LOSO) Folds
All 6 official LOSO folds (`dataset_loso_s01.json` through `dataset_loso_s06.json`) are supported via `loso_signer='S0X'` and `loso_mode='train'|'test'`.

---

## 9. Reconstructed Annotations Audit

Two samples were omitted from the upstream git commit `5325b43`:
1. `SENT236_S01_R03_F`
2. `SENT285_S04_R03_F`

Both samples are explicitly tagged:
```json
"annotation_source": "reconstructed"
```
All other 4,198 samples are tagged:
```json
"annotation_source": "source"
```
The adapter preserves this field in every `__getitem__` output and collated batch dictionary to prevent silent equivalence with original ground-truth annotations during benchmarking.

---

## 10. Known Limitations

1. **Missing Landmark Storage in Source**: Upstream MediaPipe extraction stored undetected joints as exact zeros $(0, 0, 0)$ instead of explicit NaNs. The adapter reconstructs visibility masks via $(|x| + |y| + |z|) > 10^{-6}$.
2. **Nominal FPS vs Video Duration**: In some recordings, video recording ran 0.5–1.0s beyond the final gloss gesture. Clamping frame indices to $[0, T]$ guarantees boundaries never exceed tensor bounds.
