# Huấn luyện lại Cấp 1 (BiGRU 34 lớp) với clip `đ ê ô ơ ư` của user1 — 2026-10-06

Mọi số dưới đây đọc từ 3 JSON trong thư mục này (mỗi file ghi lệnh + commit). Không có số nào gõ tay.

| File | Sinh tại | Nội dung |
|---|---|---|
| `retrain_summary.json` | `f0fb9b4`, từ output kernel `phmvnsm33/vsl-train-alphabet` version 4 (clone `d3a79a2`) | LOSO trên clip nguyên, nhầm lẫn nhóm dấu, QIPEDC |
| `ckpt_compare.json` | `f0fb9b4`, `code_dirty: false` | checkpoint cũ vs mới trên clip nguyên qua `Level1Classifier` |
| `rearm_check_gate_retrain.json` | `f0fb9b4`, `code_dirty: false`, checkpoint mới | cổng G1–G6 (rev8 = off, rev9 = on) trên chuỗi ghép clip train |
| so sánh: `reports/level1_realtime_2026-10-06/rearm_check_gate_v2.json` | `551e1b2`, checkpoint cũ | cùng lệnh, checkpoint cũ |

Checkpoint: cũ `756eaf3f…` (output kernel trước lần này), mới `9e4a99c8…` (output version 4; KHÔNG commit — `checkpoints/` bị
gitignore; tải: `kaggle kernels output phmvnsm33/vsl-train-alphabet -p <thư mục>`).

## 0. Dữ liệu (Bước 0, `vsl-data-integrity`)

- `data/collected_targeted/` (`d49fae2`): 66 clip = 11 ký hiệu × 6 (3 góc × 2 lần), signer `user1`, ghi bằng
  `scripts/collect_targeted_signs.py` (webcam `cv2.VideoCapture` → `mp.solutions.hands` 0.10.14 → `np.savez_compressed`; không có
  sinh tổng hợp). 30 clip mới: `đ ê ô ơ ư`, detection 1.0, nhãn tay `Right`, 0 clip trùng hash.
- Clip tĩnh: chuyển động giữa các khung của `đ ơ ư` user1 nhỏ hơn hẳn các lớp khác (máy thu "giữ tay" 60 khung sau đếm ngược).
- Hình tay trung bình (`normalize_hand_landmarks`, đo thăm dò trong phiên, không lưu JSON nên không chép số): ở hauuto khoảng cách
  `d`–`đ` giữa hai lớp ngang khoảng cách trong một lớp (`đ` của hauuto chỉ khác `d` ở chuyển động); ở user1 `đ` khác `d` một chút và
  `ơ` khác `o` rõ rệt ngay cả khi tay đứng yên.
- Cắt lát `COMPOUND_DIACRITICS` (nay có `đ`): mọi clip `â ă ê ô ơ ư đ` ≥ 40 khung cho thêm lát đầu (nhãn chữ gốc) và lát cuối
  (nhãn chữ có dấu): 210 + 209 lát. Lát chỉ dùng để TRAIN; từ `34b63a3` LOSO và QIPEDC được chấm thêm trên clip nguyên.

## 1. LOSO (bỏ ra 1 người ký mỗi fold; 4 người hauuto + user1) — công thức train, không phải checkpoint cuối

- Clip nguyên: BiGRU **71.46 ± 9.36** (thắng), MLP 64.52 ± 8.27. Định nghĩa cũ (lẫn lát cắt): BiGRU 64.33 ± 12.84.
  Lần train trước (định nghĩa cũ, chưa cắt `đ`, user1 36 clip): 69.11 ± 6.64 — KHÔNG so trực tiếp được (tập test khác).
- `d` vs `đ` (clip nguyên, BiGRU): `d` 21/22 (1 → `đ`); `đ` **20/30** (8 → `d`, 2 khác).
  Theo người: `đ` của `hauuto_vy` 1/6 và của `user1` 1/6 khi người đó bị bỏ ra (cách ký `đ` khác nhau giữa người).
- Nguyên âm có dấu (đúng / n): `â` 15/30, `ă` 28/30, `ê` 14/30, `ô` 18/30, `ơ` 19/30, `ư` 25/30.
- Fold `user1` (model không có clip nào của user1): 57.6; `ê` 0/6, `ô` 0/6, `ơ` 1/6, `đ` 1/6 — cách ký của user1 khác hauuto, nên dữ
  liệu của chính user1 là cần thiết.

## 2. Dữ liệu chưa thấy

- QIPEDC (46 clip chữ cái, không model nào thấy): cũ 24/46, mới **25/46** (chênh 1 clip; N ≈ 1–3 clip/lớp ⇒ không kết luận được).
  `d` 1 clip: cũ → `đ`, mới đúng; `đ` 1 clip: cũ đúng, mới → `ô`.
- 30 clip mới của user1 với checkpoint CŨ (chưa thấy): 13/30 — `đ` 5/6, `ư` 6/6, `ơ` 2/6, `ê` 0/6 (→ `â`), `ô` 0/6 (→ `â`/`a`).
  Checkpoint mới 30/30 trên chính các clip nó đã train — không phải phép test.

## 3. Cổng G1–G6 (decoder `classifier` trên chuỗi ghép clip train — kiểm logic, không phải webcam)

| | cũ, rev9 | mới, rev9 | cũ, rev8 | mới, rev8 |
|---|---|---|---|---|
| G1 one_rate L (0 / 300) | 0.922 / 0.922 đạt | **0.870 / 0.870 trượt** | 0.933 / 0.933 | 0.886 / 0.886 |
| G5 rác L (300 / 600) | 0.104 / 0.119 trượt | 0.093 / 0.083 trượt | 0.124 / 0.135 | 0.109 / 0.083 |
| rác chuỗi T (300) | 0.229 | 0.286 | 0.243 | 0.314 |
| G6 clip đơn chữ / dấu | 0.961 / 0.625 | 0.930 / 0.583 | 0.957 / 0.575 | 0.917 / 0.575 |

G2, G3, G4 đạt ở mọi cột. Chữ bị mất trên chuỗi L (cộng 3 join, rev9): cũ `â` 9, `ê` 6, `s` 6, `đ` 0; mới **`đ` 18**, `â` 9, **`ư` 9**,
`ê` 6, `d` 6; chữ thừa: mới `u` 12, `a` 9, `e` 6.

Giải thích đơn giản nhất (chưa kiểm bằng thí nghiệm riêng): lát đầu gán nhãn `d` cho 40% đầu mỗi clip `đ`, mà ở hauuto hình tay `đ`
≈ `d`; cửa sổ trượt của decoder lúc ký `đ` vì vậy được đọc là `d` và `đ` không bao giờ thành. Phân loại nguyên clip không bị ảnh
hưởng theo cách này, chế độ realtime thì có.

## 4. Kết luận và đề xuất

- Checkpoint mới học được cách ký `ê ô ơ đ` của user1 (fold user1 cho thấy model không có dữ liệu user1 thì không nhận được), nhưng
  trên phép kiểm decoder nó xấu hơn checkpoint cũ ở G1 (mất `đ`, `ư`). KHÔNG thay checkpoint mặc định dựa trên các số này; cần
  phiên webcam so hai checkpoint (`--checkpoint`) với rev9.
- Thí nghiệm đề xuất để tách nguyên nhân: train lại cùng dữ liệu nhưng KHÔNG cắt lát `đ` (và thử không cắt `ư`), rồi chạy lại
  mục 1–3. Nếu `đ` trên chuỗi L trở lại và LOSO `d`/`đ` không xấu đi ⇒ bỏ `"đ": "d"` khỏi `COMPOUND_DIACRITICS`.
- `tests/test_fingerspelling_deployed.py` lỗi sẵn (`KeyError: 'selected'`): checkpoint train từ kernel không có metadata
  provenance mà test này đòi (checkpoint cũ cũng vậy).

Test Level 1 với checkpoint mới (cloud): 15 module `tests/test_level1_*.py` Ran 425, OK, skip 7 (6 equivalence thiếu video QIPEDC,
1 u1_summary thiếu file webcam local).

## 5. Kernel version 5 — không cắt lát `đ` và `ư` (quyết định của người dùng 2026-10-06)

Mã `36e6dc0` (`COMPOUND_DIACRITICS` bỏ `đ`, `ư`; `â ă ê ô ơ` vẫn cắt), cùng 66 clip user1. Checkpoint `9c9e8960…`. Số đọc từ
`v5/retrain_summary.json`, `v5/ckpt_compare.json` (`36e6dc0`, sạch), `v5/rearm_check_gate_v5.json` (`36e6dc0`, sạch).

| | cũ `756eaf3f` | v4 `9e4a99c8` (cắt `đ ư`) | v5 `9c9e8960` (không cắt `đ ư`) |
|---|---|---|---|
| LOSO clip nguyên BiGRU (mean ± std) | — | 71.46 ± 9.36 | 70.80 ± 9.04 |
| LOSO `đ` (đúng / n; → `d`) | — | 20/30 (8) | **28/30 (0)** |
| LOSO `d` | — | 21/22 | 21/22 |
| LOSO `ư` / `ơ` | — | 25/30 / 19/30 | 22/30 / 23/30 |
| fold user1: `đ`, `ư`, `ơ`, `ê`, `ô` | — | 1, 6, 1, 0, 0 /6 | 5, 0, 6, 0, 0 /6 |
| QIPEDC 46 clip (top-1 / top-3) | 24/46 | 25/46 (84.8) | 25/46 (73.9) |
| G1 one_rate L, rev9 (0 / 300) | 0.922 / 0.922 | 0.870 / 0.870 | 0.896 / 0.902 |
| G5 rác L, rev9 (300 / 600) | 0.104 / 0.119 | 0.093 / 0.083 | 0.124 / 0.124 |
| `đ` mất trên chuỗi L (3 join) | 0 | 18 | **0** |
| chuỗi T one_rate / rác (300) | 0.971 / 0.229 | 0.971 / 0.286 | 0.929 / 0.286 |
| gate trượt | G5 | G1, G5 | G1, G5 |

- Bỏ cắt lát `đ` đúng như giả thuyết ở mục 3: `đ` không còn bị đọc thành `d` (LOSO và chuỗi decoder).
- Đổi lại: `ư` của user1 không còn được nhận khi fold user1 bị bỏ ra (0/6, v4 6/6); rác dấu thanh trên chuỗi L tăng (`dấu sắc` thừa
  14 lần); G5 xấu hơn v4. Không checkpoint nào qua G1–G6 (cả checkpoint cũ cũng trượt G5).
- `ê`/`ô` → `â`: người dùng xác nhận đây là thiết kế (dấu mũ chung, `DIACRITIC_FUSION` ghép `e` + `â` → `ê`, `o` + `â` → `ô` khi chữ gốc
  đã ra trước). Các số `ê`/`ô` ở trên vẫn tính `â` là sai (định nghĩa không đổi sau khi thấy kết quả).
- Theo yêu cầu người dùng, v5 là checkpoint mới (output kernel version 5). Đây là quyết định của người dùng, không phải gate pass;
  cần phiên webcam để xác nhận.

Test Level 1 với v5 (cloud): 15 module, Ran 425, OK, skip 7 (như mục 4).
