# DATA SPLIT & LEAKAGE PREVENTION POLICY
**Vietnamese Sign Language Recognition (VSLR)**  
**Status:** FROZEN  
**Date:** 2026-09-12  
**Policy Owner:** Senior CV + DL Engineer  

---

## 1. Fundamental Principle: Zero Data Leakage

In scientific benchmarking of Sign Language Recognition (SLR), data leakage between splits produces deceptive, ungeneralizable metric inflation. To guarantee rigorous academic validity, the following split hierarchy and leakage prevention protocols are strictly enforced.

---

## 2. Core Partitioning Hierarchy

```
                      RAW VIDEO CORPUS (4,362 MP4s)
                                    │
                                    ▼
                     ATOMIC UNIT: source_video_id
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
           TRAIN SPLIT          VAL SPLIT           TEST SPLIT
         (source-disjoint)   (source-disjoint)   (source-disjoint)
                │                   │                   │
                ▼                   ▼                   ▼
         AUGMENTATION         NO AUGMENTATION     NO AUGMENTATION
          APPLIED             ALLOWED             ALLOWED
     (Post-split only)       (Canonical only)    (Canonical only)
```

### Rule 2.1: Atomic Source Identity
* Every single original MP4 file in `data (2)/Dataset/Videos/` represents a unique, atomic `source_video_id` (e.g. `D0001B`, `W00123T`).
* **Inviolable constraint**: All sub-sequences, sliding windows, frame subsamplings, and augmented variants derived from video $S_i$ must strictly and exclusively reside within the exact same partition:
  $$\text{Split}(S_i) \in \{\text{Train}, \text{Val}, \text{Test}\}$$
  $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$

### Rule 2.2: Signer & Dialect Considerations
1. **Signer Identity**:
   - The current dataset (`data (2)/Dataset/Labels/label.csv`) contains no explicit signer ID column.
   - If reliable external signer annotations are discovered, **signer-disjoint** partitioning takes immediate precedence.
   - In the absence of confirmed signer metadata, **source-video-disjoint** partitioning is the mandatory baseline, and the limitation must be transparently documented in publications.
2. **Regional Dialect**:
   - Dialect codes (`B` = Northern, `T` = Central, `N` = Southern) are treated as demographic/phonetic metadata.
   - For classes possessing multiple regional dialect videos, stratified sampling across dialects should be maintained across splits so that each split reflects balanced dialectal representation.

---

## 3. Augmentation Lifecycle Rules

### Rule 3.1: Post-Split Augmentation Only
* Augmentation must NEVER be executed prior to the train/val/test split.
* Pre-generating and saving augmented datasets that are subsequently randomly split is strictly banned (this was the root cause of the `data (2)/Processed` contamination).

### Rule 3.2: Train Split Exclusivity
* Validation and Test splits must consist **exclusively of clean, canonical, un-augmented sequences**.
* Offline or online keypoint augmentations (spatial rotation, scale jitter, temporal stretching, limb dropout) are applied **only to the training split during training**.
* Testing on augmented data is strictly prohibited as it distorts real-world camera accuracy metrics.

---

## 4. Leakage Verification Criteria (Automated Guardrail)

Prior to entering Phase 5 (Baseline Modeling), an automated script `scripts/check_data_leakage.py` must run and verify:

1. **Exact Filename Check**:
   $$\text{files}(\text{train}) \cap \text{files}(\text{val}) \cap \text{files}(\text{test}) = \emptyset$$
2. **Source ID Check**:
   $$\text{source\_id}(\text{train}) \cap \text{source\_id}(\text{val}) \cap \text{source\_id}(\text{test}) = \emptyset$$
3. **Cross-Split Hash & Cosine Similarity Check**:
   - Calculate pair-wise cosine similarity across all validation/test sequences against training sequences.
   - If any pair exhibits cosine similarity $> 0.99$, execution is halted (`BLOCKED`) for manual audit.

---

## 5. Split Ratio Guidelines for Closed-Set Benchmark

Depending on the final chosen vocabulary scope:
* For classes with $\ge 3$ video recordings:
  - Default allocation: **60% Train / 20% Val / 20% Test** (e.g. for 3 videos per gloss: 1 Train, 1 Val, 1 Test; or 5 videos: 3 Train, 1 Val, 1 Test).
  - Minimum requirement per class: At least 1 video in Train, 1 in Val, 1 in Test.
  - Classes with fewer than 3 video recordings cannot be included in an independent train/val/test closed-set split without synthetic data leaks.
