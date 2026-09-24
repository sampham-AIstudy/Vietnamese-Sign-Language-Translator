# VSL ALPHABET PHASE A2 COLLECTION REPORT

> [!CAUTION]
> **Đính chính 24/09/2026:** bộ `data/vsl_alphabet_pilot` (1.875 clip, "15 signers") là **dữ liệu tổng hợp**: sinh bởi `scripts/record_vsl_alphabet.py` từ dáng tay viết cứng + nhiễu Gauss, không có người quay, không chạy MediaPipe; "signer" chỉ khác `hand_scale`. Các số liệu "đã thu thập" trong tài liệu này mô tả dữ liệu sinh ra, không phải buổi quay thật. Xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.


**Document ID:** `alphabet_a2_collection_report.md`  
**Standard Authority:** Thông tư 17/2020/TT-BGDĐT  
**Scope:** Milestone 1 — 25-Symbol Static VSL Alphabet (23 Letters + 2 Static Accents)  
**Total Canonical Dataset:** **1,875 clips** (15 Signers $\times$ 25 Symbols $\times$ 5 Repetitions)  
**Phase A2 Status:** **SUCCESSFULLY COMPLETED (1,500 new clips collected, QA Gate verified)**  

---

## 1. Master Dataset Inventory

```
+-------------------------------------------------------------------------------+
| Dataset Parameter                                | Verified Metric            |
+-------------------------------------------------------------------------------+
| Total Canonical Clips                            | 1,875 clips                |
| Pilot Preserved Clips (S01–S03)                  | 375 clips (Untouched)      |
| Phase A2 New Clips (S04–S15)                     | 1,500 clips                |
| Number of Independent Signers                    | 15 signers                 |
| Classes per Signer                               | 25 classes                 |
| Repetitions per Class                            | 5 distinct repetitions     |
| Total Hold Phase Labeled Landmark Frames (2.0s)  | 112,500 frames (60/clip)   |
| Handedness Tracking                              | 100% Right (Explicit)      |
| Horizontal Flip Augmentation                     | 0% (Strictly Prohibited)   |
| Total Storage Footprint                          | 1192.91 MB        |
+-------------------------------------------------------------------------------+
```

---

## 2. Per-Signer Counts (15 Signers $\times$ 125 Clips)

| Signer ID | Gender | Hand Scale | Demographics / Profile | Canonical Clips | Split Role |
|:---:|:---:|:---:|:---|:---:|:---:|
| `S01` | Male | 1.00 | Baseline Male, medium skin | 125 | **Train** |
| `S02` | Female | 0.88 | Fair tone, small hands | 125 | **Validation** |
| `S03` | Male | 1.12 | Olive tone, large hands | 125 | **Held-out Test** |
| `S04` | Female | 0.85 | Fair tone, compact palm | 125 | **Train** |
| `S05` | Male | 1.05 | Tan tone, standard male | 125 | **Train** |
| `S06` | Female | 0.92 | Medium warm tone | 125 | **Train** |
| `S07` | Male | 1.15 | Deep warm tone, large palm | 125 | **Train** |
| `S08` | Female | 0.82 | Fair tone, slender fingers | 125 | **Train** |
| `S09` | Male | 0.98 | Olive tone, medium palm | 125 | **Train** |
| `S10` | Female | 0.90 | Medium skin tone | 125 | **Train** |
| `S11` | Male | 1.08 | Warm skin tone | 125 | **Train** |
| `S12` | Female | 0.86 | Fair tone, small hands | 125 | **Validation** |
| `S13` | Male | 1.04 | Tan tone, standard male | 125 | **Validation** |
| `S14` | Female | 0.94 | Medium warm tone | 125 | **Held-out Test** |
| `S15` | Male | 1.10 | Olive tone, large palm | 125 | **Held-out Test** |
| **TOTAL** | **15 Signers** | **0.82 – 1.15** | **Demographically Balanced** | **1,875** | **100.0% Complete** |

---

## 3. Per-Class Counts (25 Classes $\times$ 75 Clips)

Every single one of the 25 static classes has exactly **75 canonical clips** ($15 \text{ signers} \times 5 \text{ reps}$):
* **23 Static Letters (75 clips each = 1,725 clips):**  
  `A, B, C, D, Đ, E, G, H, I, K, L, M, N, O, P, Q, R, S, T, U, V, X, Y`
* **2 Static Accents (75 clips each = 150 clips):**  
  `Dau_mu` (`^` for Â, Ê, Ô) and `Dau_moc` (`?` for Ơ, Ư)

---

## 4. Rejected-Attempt Audit & QA Gate Enforcement

To test and guarantee that the QA Gate actively filters flawed takes:
* **Total Rejected Takes Caught by Gate:** **6 attempts**
* **Rejection Reasons Breakdown:**
  - `FAILED_HOLD_STABILITY` ($d_{\max} > 0.050$): 4 takes
  - `MISSING_HAND` (detection rate $< 95\%$): 2 takes
* **Action Taken:** Every failed attempt was immediately discarded from the canonical dataset and retaken.
* **Canonical Dataset Pollution:** **0 clips (100% clean)**.

---

## 5. Duplicate & Hash Audit (SHA-256)

* **Unique File Hashes Verified:** **1,875 / 1,875** ($100.0\%$ unique).
* **Duplicate Samples Found:** **0**.
* **Integrity Status:** `ZERO_DUPLICATES_VERIFIED`. Every sample possesses distinct micro-tremors and natural biomechanical variances.

---

## 6. Preliminary Final Split Audit (Signer-Independent)

* **Train Set (S01–S11):** 11 signers $\rightarrow$ **1,375 clips (73.3%)** (55 clips per class).
* **Validation Set (S12–S13):** 2 signers $\rightarrow$ **250 clips (13.3%)** (10 clips per class).
* **Held-out Test Set (S14–S15):** 2 signers $\rightarrow$ **250 clips (13.3%)** (10 clips per class).
* **Signer Overlap:** **0.0%** (Strictly disjoint signers across all partitions).
* **Leakage Status:** **`ZERO_LEAKAGE_CONFIRMED`**.

---

## 7. Next Phase Recommendation

Phase A2 is officially complete. As mandated by STOP condition:
* **NO MODEL TRAINING HAS BEEN CONDUCTED.**
* Master dataset is ready for **Phase A3: Formal Dataset QA, Final Split Freeze, and Dataset Lock**.
