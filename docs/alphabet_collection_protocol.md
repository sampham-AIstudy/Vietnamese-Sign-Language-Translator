# VSL Alphabet Data Collection Protocol

> [!NOTE]
> Giao thức này là đặc tả cho việc quay thật. Bộ `data/vsl_alphabet_pilot` từng được tạo "theo" giao thức này là **dữ liệu tổng hợp** (`scripts/record_vsl_alphabet.py`), không phải kết quả thu thập. Xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.


**Document Version:** 1.0.0  
**Authority:** Thông tư 17/2020/TT-BGDĐT (Bộ Giáo dục và Đào tạo)  
**Milestone:** Milestone 1 — 25 Static Classes (23 Letters + 2 Accents)  

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

## 2. 4-Phase Recording Execution Protocol

Each recording instance follows a strict 4-phase sequence:
1. **Phase 1: REST (Nghỉ)** — Hand rests on lap or lower frame boundary (0.5s – 1.0s).
2. **Phase 2: APPROACH (Đưa tay)** — Signer raises hand smoothly into the neutral signing box and forms the target posture (0.5s).
3. **Phase 3: HOLD (Giữ tĩnh)** — Hand is held completely stable for exactly **2.0 seconds** (~60 frames @ 30 FPS).
4. **Phase 4: RETURN (Hạ tay)** — Hand lowers back to resting position (0.5s).

---

## 3. Optical & Environmental Controls
* **Resolution:** Minimum 1080p ($1920 \times 1080$), fallback 720p.
* **Frame Rate:** 30 FPS constant.
* **Lighting:** Diffuse forward light $> 300\text{ lux}$ to avoid harsh shadows.
* **Chirality:** Right-handed default, tracked in metadata (`handedness`). **Zero horizontal flip augmentation permitted.**
* **Background:** High-contrast neutral studio background.

---

## 4. Landmark Extraction & Normalization
* **Tracker:** Google MediaPipe Hands (21 keypoints, $(x, y, z)$).
* **Storage Schema (`.npz`):**
  - `raw_landmarks`: `[T, 21, 3]` in normalized image coordinates $[0, 1]$.
  - `visibility`: `[T, 21]` detection confidence.
  - `wrist_centered`: Translation-invariant coordinates $\mathbf{p}_i - \mathbf{p}_0$.
  - `palm_scale_normalized`: Scale-invariant coordinates $(\mathbf{p}_i - \mathbf{p}_0) / (\|\mathbf{p}_9 - \mathbf{p}_0\|_2 + \epsilon)$.
  - `detected_mask`: `[T]` boolean validity mask.

---

## 5. Signer-Independent Split Strategy
* **Pilot Cohort:**
  - `S01` $\rightarrow$ Train candidate (125 clips)
  - `S02` $\rightarrow$ Validation candidate (125 clips)
  - `S03` $\rightarrow$ Test candidate (125 clips)
* **Zero Leakage:** Strictly disjoint signers across all sets.
