# Cấp 1 — kernel version 6 (+12 clip `p`, `q` của user1): so sánh checkpoint cũ / v5 / v6 — 2026-10-07

Mọi số dưới đây đọc từ các JSON trong thư mục này (mỗi file ghi lệnh + commit). Không có số nào gõ tay.

| File | Sinh tại | Nội dung |
|---|---|---|
| `retrain_summary_v5.json`, `retrain_summary_v6.json` | `3d35182`, output kernel `phmvnsm33/vsl-train-alphabet` v5 (clone `36e6dc0`) / v6 (clone `8c53795`) | LOSO trên clip nguyên, nhầm lẫn theo nhóm (thêm `p`/`q`), theo người, QIPEDC |
| `ckpt_compare.json` | `3d35182`, `code_dirty: false` | 3 checkpoint trên clip nguyên qua `Level1Classifier` |
| `rearm_check_gate_{old,v5,v6}.json` | `3d35182` (code decoder của `3510c3a`: cổng chuyển động miễn cả cặp `DIACRITIC_FUSION`) | cổng G1–G6, rev8 = off, rev9 = on |

Checkpoint: cũ `756eaf3f…`, v5 `9c9e8960…`, v6 `160e0c68…` (output kernel version 6; không commit — `checkpoints/` bị
gitignore; tải: `kaggle kernels output phmvnsm33/vsl-train-alphabet -p <thư mục>`).

## 0. Dữ liệu (Bước 0, `vsl-data-integrity`)

`data/collected_targeted/manifest.csv` @ `8c53795`: 78 dòng = 13 ký hiệu × 6 (`â ă d i o s đ ê ô ơ ư p q`). 12 clip mới `p`, `q`
(user1, 3 góc × 2): 60 khung, detection 0.967–1.000, 0 NaN, nhãn tay `Right`, 0 hash trùng với 66 clip cũ, cùng
`scripts/collect_targeted_signs.py` (webcam → `mp.solutions.hands` 0.10.14 → `np.savez_compressed`; script không đổi từ `fd5ceea`).
`p`, `q` không nằm trong `COMPOUND_DIACRITICS` (không cắt lát); script train không đổi từ v5 (`36e6dc0`).

## 1. LOSO trên clip nguyên (bỏ ra 1 người ký mỗi fold) — mô tả công thức train, không phải checkpoint cuối

| | v5 | v6 |
|---|---|---|
| BiGRU (mean ± std, 5 fold) | 70.80 ± 9.04 | 74.14 ± 8.59 |
| fold hauuto_hau / khoi / tai / vy (cùng clip test ở cả hai) | 72.5 / 78.1 / 60.3 / 82.5 | 75.0 / 81.9 / 63.5 / 85.0 |
| fold user1 (66 → 78 clip test) | 60.6 | 65.4 |
| `p` / `q` (đúng / n) | 9/16 / 12/14 | 21/22 / 17/20 |
| `p`/`q` nhầm lẫn | `p`: 9 p, 1 q, 6 khác; `q`: 12 q, 2 khác | `p`: 21 p, 1 khác; `q`: 17 q, 1 p, 2 khác |
| `p` của hauuto_khoi / hauuto_tai | 0/4 / 1/4 | 3/4 / 4/4 |
| `đ` / `ơ` / `ư` | 28/30 / 23/30 / 22/30 | 29/30 / 25/30 / 22/30 |
| `d` | 21/22 | 22/22 |
| `â` / `ê` / `ô` | 16/30 / 13/30 / 15/30 | 16/30 / 16/30 / 15/30 |
| fold user1: `đ`, `ơ`, `ư` | 5, 6, 0 /6 | 5, 6, 0 /6 |

- Bốn fold hauuto có cùng tập clip test ở v5 và v6 và đều tăng; `p` của hauuto tăng rõ nhờ `p` của user1. Mỗi số là 1 lần train
  (1 seed); chưa đo độ dao động giữa các seed.
- Không hồi quy `đ`, `ơ`, `ư` trên LOSO; `ư` của user1 vẫn 0/6 khi user1 bị bỏ ra (như v5).

## 2. Dữ liệu chưa thấy và kiểm hồi quy trên clip user1

| | cũ | v5 | v6 |
|---|---|---|---|
| QIPEDC 46 clip (không model nào thấy) top-1 | 24/46 | 25/46 | **23/46** |
| QIPEDC top-3 (từ `retrain_summary`) | — | 73.9 | 65.2 |
| 12 clip `p`/`q` user1 | 10/12 (chưa thấy) | 11/12 (chưa thấy) | 12/12 (đã train) |
| 18 clip `đ`/`ơ`/`ư` user1 | 13/18 (chưa thấy) | 18/18 (đã train) | **17/18** (đã train: 1 `ơ` → `o`) |

- `p`/`q` của user1 đã được checkpoint cũ và v5 nhận phần lớn trước khi có dữ liệu (10/12, 11/12 trên clip chưa thấy).
- QIPEDC: v6 kém v5 2 clip (N ≈ 1–3 clip/lớp ⇒ chưa kết luận được), nhưng top-3 giảm liên tục qua v4 → v5 → v6 (84.8 → 73.9 → 65.2):
  dấu hiệu model chuyên biệt dần vào user1 / hauuto.
- v6 sai 1 clip `ơ` của user1 (đọc thành `o`) dù đã train trên nó.

## 3. Cổng G1–G6 (decoder `classifier` trên chuỗi ghép clip train — kiểm logic, không phải webcam)

Cả 3 checkpoint đo lại trên CÙNG code (`3d35182`, decoder của `3510c3a`), nên số của checkpoint cũ / v5 ở đây khác nhẹ bản
2026-10-06 (code decoder trước `3510c3a`). Cổng đăng ký trước, không đổi.

| | cũ | v5 | v6 |
|---|---|---|---|
| G1 one_rate L, rev9 (0 / 300; ≥ 0.90) | 0.922 / 0.922 đạt | 0.896 / 0.902 trượt | 0.896 / 0.902 trượt |
| G5 rác L, rev9 (300 / 600; ≤ 0.05) | 0.109 / 0.124 trượt | 0.124 / 0.124 trượt | 0.098 / 0.135 trượt |
| G6 clip đơn: chữ (rev9 / rev8) | 0.959 / 0.957 | 0.952 / 0.944 | 0.946 / 0.940 |
| G6 clip đơn: dấu thanh (rev9 / rev8) | 0.625 / 0.575 | 0.542 / 0.550 | 0.508 / 0.500 |
| chuỗi T rev9 (300): one_rate / rác | 0.971 / 0.229 | 0.929 / 0.286 | 0.929 / 0.314 |
| G2, G3, G4 | đạt | đạt | đạt |
| gate trượt | G5 | G1, G5 | G1, G5 |

Chữ bị mất trên chuỗi L (rev9, cộng 3 join): `p` cũ 0, v5 0, v6 3; `q` 0 / 0 / 0; `đ` 0 / 0 / 0; `ơ` 3 / 2 / 3; `ư` 3 / 6 / 6;
`ê` 6 / 7 / 13 (v6: thừa `e` 12). `dấu sắc` thừa: 11 / 14 / 13.

- Phép đo này chấm nhãn của decoder, KHÔNG áp `DIACRITIC_FUSION` của speller: một clip `ê` ra `e` rồi dấu mũ (`â`) — đúng thiết kế
  Unikey mà người dùng xác nhận — vẫn bị tính là mất `ê` + thừa. Số `ê`/`ô` ở đây vì vậy bi quan so với app (giới hạn đã biết của
  phép đo; định nghĩa không đổi sau khi thấy kết quả).
- Dấu thanh: tỉ lệ clip đơn ra đúng một lần giảm dần qua các bản (0.625 → 0.542 → 0.508); LOSO dấu thanh (định nghĩa cũ, dấu thanh
  không bị cắt lát) không cho thấy xu hướng rõ: v4 44.2, v6 40.0, v5 34.2 (std 11–16; `retrain_summary*.json`).

## 4. Kết luận

- `p`/`q`: v6 nhận tốt trên LOSO (21/22, 17/20; `p` của hauuto tăng) và không hồi quy `đ` (LOSO 29/30, chuỗi L 0 lần mất).
- Hồi quy cần theo dõi: 1 clip `ơ` của user1 thành `o`; `ê` mất nhiều hơn trên chuỗi decoder; dấu thanh clip đơn và QIPEDC top-3
  giảm. Không checkpoint nào qua G1–G6; v6 không tốt hơn v5 ở G1, ngang ở G5.
- Không thay checkpoint mặc định dựa trên các số này; quyết định thuộc người dùng, nên thử webcam so v5 và v6.

## 5. Test (cloud, checkpoint v6, code `3d35182`)

15 module `tests/test_level1_*.py`: Ran 431, 2 FAIL, skip 7 (6 equivalence thiếu video QIPEDC, 1 u1_summary thiếu file webcam
local). 2 FAIL đều ở `tests.test_level1_guard` (G2, G3): `src/inference/level1_core.py:549 GESTURE_BACKSPACE_WINDOW_MS = 250.0`
(commit `7a267c7`, cử chỉ backspace) bị luật D-binding coi là số đo gõ tay; không liên quan tới checkpoint. Cách sửa theo quy ước
sẵn có: đặt tên không có hậu tố đơn vị như `GESTURE_SPACE_HOLD` trong `level1_demo.py` — chưa sửa (ngoài phạm vi việc train).
