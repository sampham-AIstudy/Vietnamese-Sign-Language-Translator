# VSL Alphabet Data Collection Protocol (Version 2.0.0 — Hardened)

> [!NOTE]
> Giao thức này là đặc tả cho việc quay thật. Bộ `data/vsl_alphabet_pilot` từng được tạo "theo" giao thức này là **dữ liệu tổng hợp** (`scripts/record_vsl_alphabet.py`), không phải kết quả thu thập. Xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.


**Document Version:** 2.0.0  
**Authority:** Thông tư 17/2020/TT-BGDĐT (Bộ Giáo dục và Đào tạo)  
**Scope:** Milestone 1 — 25 Static Classes (23 Letters + 2 Static Accents)  
**Status:** Hardened Specification for Multi-Signer Cohort  

---

## 1. Class Taxonomy (25 Static Symbols)

### 1.1 23 Static Letters
| No. | Symbol | Vietnamese Name | Physical Gesture Description (Thông tư 17) |
|:---:|:---:|:---|:---|
| 1 | `A` | Chữ A | Nắm tay, ngón cái áp sát cạnh ngoài ngón trỏ |
| 2 | `B` | Chữ B | Bàn tay mở, 4 ngón khép duỗi thẳng lên, ngón cái gập ngang lòng bàn tay |
| 3 | `C` | Chữ C | Bàn tay uốn cong hình chữ C hướng về phía trước |
| 4 | `D` | Chữ D | Ngón trỏ chỉ thẳng lên, các ngón còn lại chạm đầu ngón cái tạo vòng tròn |
| 5 | `Đ` | Chữ Đ | Tương tự chữ D với nét vạch ngang đặc trưng của VSL |
| 6 | `E` | Chữ E | Các ngón tay cong quặp lại, đầu ngón tay tì lên ngón cái |
| 7 | `G` | Chữ G | Ngón trỏ và ngón cái duỗi thẳng song song hướng ngang phía trước |
| 8 | `H` | Chữ H | Ngón trỏ và ngón giữa duỗi thẳng khép song song hướng ngang, ngón cái gập |
| 9 | `I` | Chữ I | Ngón út duỗi thẳng đứng, 3 ngón giữa gập, ngón cái giữ qua |
| 10 | `K` | Chữ K | Ngón trỏ hướng lên, ngón giữa hướng tới trước, ngón cái kẹp giữa |
| 11 | `L` | Chữ L | Hình chữ L: ngón cái hướng ngang, ngón trỏ hướng thẳng đứng |
| 12 | `M` | Chữ M | Nắm tay, 3 ngón (trỏ, giữa, áp út) phủ trùm lên ngón cái |
| 13 | `N` | Chữ N | Nắm tay, 2 ngón (trỏ, giữa) phủ trùm lên ngón cái |
| 14 | `O` | Chữ O | Các đầu ngón tay chạm đầu ngón cái tạo thành hình tròn chữ O |
| 15 | `P` | Chữ P | Hình chữ K nhưng chúc chúc đầu ngón xuống dưới |
| 16 | `Q` | Chữ Q | Hình chữ G nhưng chúc chúc đầu ngón xuống dưới |
| 17 | `R` | Chữ R | Ngón trỏ và ngón giữa bắt chéo vào nhau |
| 18 | `S` | Chữ S | Nắm tay, ngón cái vắt ngang qua mu 4 ngón tay đang nắm |
| 19 | `T` | Chữ T | Nắm tay, ngón cái luồn chen vào giữa ngón trỏ và ngón giữa |
| 20 | `U` | Chữ U | Ngón trỏ và ngón giữa duỗi thẳng khép sát hướng lên, ngón cái gập |
| 21 | `V` | Chữ V | Ngón trỏ và ngón giữa xòe hình chữ V (peace sign) |
| 22 | `X` | Chữ X | Ngón trỏ uốn cong hình móc câu, các ngón khác gập nắm |
| 23 | `Y` | Chữ Y | Ngón cái và ngón út xòe sang hai bên, 3 ngón giữa gập (shaka) |

### 1.2 2 Static Accents
| No. | Symbol | Accent Name | Target Vowels | Description |
|:---:|:---:|:---|:---|:---|
| 24 | `Dau_mu` | Dấu mũ (`^`) | `Â`, `Ê`, `Ô` | Ngón trỏ và ngón giữa tạo hình chữ V ngược |
| 25 | `Dau_moc` | Dấu móc / râu (`?`) | `Ơ`, `Ư` | Ngón trỏ uốn cong thành hình móc râu |

---

## 2. Hardened Camera Control Protocols

The recording tool enforces hardware-level controls via OpenCV VideoCapture properties:
1. **Exposure Control:** Attempts programmatic lock via `CAP_PROP_AUTO_EXPOSURE = 0.25` (DirectShow manual) or `1.0`. If driver returns `-1.0` (unsupported register), logs graceful fallback and prompts fixed studio diffuse lighting.
2. **White Balance Control:** Attempts lock via `CAP_PROP_AUTO_WB = 0.0`. Gracefully falls back if unsupported.
3. **Autofocus Control:** Attempts lock via `CAP_PROP_AUTOFOCUS = 0.0` to eliminate focus hunting during approach phase.
4. **Telemetry Logging:** Every clip metadata records `actual_resolution` and `actual_fps`.

---

## 3. Real-Time Hold Stability Gate

During the 2.0-second HOLD phase (Frames 30 to 89 at 30 FPS):
* **Wrist Displacement Metric:**
  $$d(t) = \|\mathbf{p}_0(t) - \mathbf{p}_0(t_{\text{hold\_start}})\|_2$$
* **Configured Threshold:** $\tau_{\text{stability}} = 0.050$ (normalized image coordinate units).
* **Live HUD Feedback:**
  - Real-time stability gauge on screen: Green if $d(t) \le 0.050$, Red if $d(t) > 0.050$.
* **Automatic Retake Mandate:**
  - If $d_{\text{max}} > 0.050$ or hand detection rate $< 95\%$, the sample is automatically rejected.
  - The recording session automatically prompts the signer to retake the current repetition.

---

## 4. Handedness & Chirality Enforcement
* Default: Right hand (`handedness: "Right"`).
* If recording a left-handed signer, `--handedness Left` must be explicitly declared.
* **Prohibition:** Horizontal flip augmentation is strictly prohibited in all pipelines to preserve asymmetrical handshapes (`D`, `Đ`, `G`, `H`, `L`, `P`, `Q`).

---

## 5. Hardened Quality Gate Thresholds (QA v2)

| Quality Gate Parameter | v1.0.0 Threshold | v2.0.0 Hardened Threshold | Rejection Action |
|:---|:---:|:---:|:---|
| **Hold Detection Rate** | $\ge 85\%$ | **$\ge 95\%$** | Reject sample (`MISSING_HAND`) |
| **Max Wrist Displacement** | Not monitored | **$\le 0.050$** | Reject sample (`FAILED_HOLD_STABILITY`) |
| **Max Landmark Jitter** | Not monitored | **$\le 0.015$** | Reject sample (`EXCESSIVE_JITTER`) |
| **Hold Duration Window** | $[1.80\text{s}, 2.50\text{s}]$ | **$[1.90\text{s}, 2.15\text{s}]$** | Reject sample (`INVALID_HOLD_DURATION`) |
| **Video Codec Integrity** | Readable | Readable & Frame Count $\ge 75$ | Reject sample (`CODEC_FAILURE`) |

---

## 6. Signer-Independent Split Strategy
* **Strict Disjointness:** Zero signer overlap across splits.
* **Verified Pilot Partition (S01–S03):**
  - Train Candidate: `S01` (125 clips)
  - Validation Candidate: `S02` (125 clips)
  - Held-out Test Candidate: `S03` (125 clips)
  - *Status:* Đã kiểm chứng thực tế không trùng lặp (0.0% overlap).
* **Planned Final Partition for Full 15-Signer Cohort (S01–S15):**
  - Train Set: `S01`–`S11` (11 signers $\times$ 25 classes $\times$ 5 reps = 1,375 clips)
  - Validation Set: `S12`–`S13` (2 signers $\times$ 25 classes $\times$ 5 reps = 250 clips)
  - Held-out Test Set: `S14`–`S15` (2 signers $\times$ 25 classes $\times$ 5 reps = 250 clips)
  - *Status:* Thiết kế phân vùng dự kiến (chỉ được kiểm chứng sau khi hoàn tất thu thập Phase A2).

