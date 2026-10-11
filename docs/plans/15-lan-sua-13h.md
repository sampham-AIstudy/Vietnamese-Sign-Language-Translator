# Kế hoạch 15 — LẦN SỬA 13h: luật R-G (G-0..G-3) áp THEO TỪNG CỬ CHỈ

Không có điểm dừng mới cần người dùng (U3/VU3 của 13g vẫn giữ). Kế hoạch gốc: `docs/plans/15-lan-sua-13g.md` (§3.3, §4, §6, §9).

## 1. Mục tiêu và DoD
Sửa cách cài G-0 ở S2/S3 của 13g: G-0..G-3 được tính và quyết định cho TỪNG cử chỉ g; `space` (G-0 đạt) giữ design, `backspace`
(G-0 trượt) đi tiếp G-1/G-2, rồi G-3 chạy trên bộ giá trị gộp. Phục vụ cùng mục DoD với 13g (VU2: cử chỉ nhận được trong app, GF/GT đạt).

## 2. Hiện trạng
- `reports/level1_realtime_2026-10-11/gesture_diag_D.json` (commit 84878b1, sinh ở 01e3809, `code_dirty false`, `--process-fps 15.5`):
  dòng 86-96 `gesture_ablation.g0 = {space: true, backspace: false}` nhưng `decisions.stop_offline_ok = true` CHUNG, `tuned_values = {}`
  (dòng 98-106) ⇒ script dừng cả hai cử chỉ. JSON KHÔNG ghi số clip k/5 theo từng giá trị lưới, nên giá trị tới hạn agy báo cho backspace
  (`wave_max_vertical_ratio` 0.6, `wave_min_flat_fraction` 0.80) KHÔNG truy vết được từ JSON ⇒ CHƯA được dùng.
- Ghi chú cho review S1–S3 (đang chạy song song): `skeleton.moving_{smooth,track,enh}` gộp có p50 = p90 = 0.0 với `count 12` (dòng 69-85),
  trong khi `per_clip` có giá trị khác 0 (vd `backspace_01` native smooth p90 ≈ 0.0297, track p90 ≈ 0.0369, dòng 431-440). Nghi lỗi gộp
  (đếm theo clip thay vì khung `moving`?) ⇒ `mediapipe_limit true` có thể là giả. Reviewer xác minh; nếu là lỗi thì sửa ở S3a (luật R-S giữ nguyên).

## 3. Thiết kế — làm rõ ý đồ, KHÔNG đổi quy tắc
Vì sao là làm rõ: §3.3 của 13g viết "R-G (cử chỉ), **từng cử chỉ g** (5 clip D)" và G-0 "design phát ở ≥ 4/5 clip **của g**"; lưới khóa
tách rời theo cử chỉ (`space_*` chỉ của space, `wave_*` chỉ của backspace); G-3 "mỗi g phát ≥ 4/5". Lý do của G-0 ghi trong ngoặc là "offline
đạt mà app không ⇒ lệch app/offline" — một mệnh đề về CỬ CHỈ đó. Áp G-0 chung cho cả hai là lỗi cài đặt. Không số nào trong bảng §3.3
(design, sàn, lưới, 4/5, chiều chặt) đổi; quy tắc chọn giá trị G-2 không đổi; không có giá trị nào được chọn dựa trên số liệu đã thấy.

Luật sau làm rõ (mỗi g ∈ {space, backspace}, trên CẢ hai biến thể native và `--process-fps`):
- G-0(g): design phát ≥ 4/5 clip của g ⇒ `status = design_ok`: g giữ design, không khóa nào của g vào `tuned_values`, KHÔNG dừng do script.
  Kiểm lệch app/offline (phần "app không" của lý do G-0) do orchestrator làm: đọc JSON/log U2 (§5 của 13g) — nếu app KHÔNG phát g ở U2 ⇒
  `stop_offline_ok` cho g ⇒ DỪNG, planner (như cũ). Nếu U2 cho thấy app phát g ⇒ không lệch, đi tiếp. (agy báo app U2 phát space 5 lần —
  orchestrator xác minh từ file U2, không từ lời agy.)
- G-1(g): chỉ khi G-0(g) trượt. Sàn phát < 4/5 ⇒ `status = stop_outside_config` ⇒ DỪNG, planner.
- G-2(g): chỉ khi G-1(g) đạt ⇒ `status = tuned`, mỗi khóa p của g: giá trị CHẶT nhất trên lưới thỏa ≥ 4/5, không chặt hơn design, lấy lỏng
  hơn giữa hai biến thể (đúng 13g).
- G-3 (gộp): bộ giá trị = design cho mọi khóa, thay bằng `tuned_values` của các g `tuned`; chạy lại trên D: mỗi g phát ≥ 4/5, 0 lần phát
  cử chỉ ngược, 0 lần phát trên 2 clip `spell`. Trượt ⇒ `stop_combined` ⇒ DỪNG, planner.

Hợp đồng JSON (`decisions`, thay phần cử chỉ hiện có):
- `decisions.gestures.<g>` = `{"status": "design_ok"|"stop_outside_config"|"tuned", "counts": {...}, "tuned_values": {...}}`;
  `counts` ghi k (số clip phát / 5) cho design, sàn và MỖI giá trị lưới của MỖI khóa của g, theo từng biến thể — để mọi giá trị tới hạn truy
  vết được từ JSON.
- `decisions.tuned_values` = hợp các `tuned_values` theo g (chỉ khóa khác design); `decisions.stop_outside_config` = có g nào dừng G-1;
  `decisions.stop_combined` = G-3 trượt; `decisions.design_ok_gestures` = danh sách g đạt G-0 (để orchestrator đối chiếu U2).
  Khóa `stop_offline_ok` không còn do script đặt (luôn `false` hoặc bỏ; test chốt một trong hai, ghi trong docstring).
- `rules._note` thêm "G-0..G-3 theo từng cử chỉ — làm rõ ở 15-lan-sua-13h"; mọi số trong `rules` giữ y nguyên.

## 4. Chia việc (mỗi bước 1 commit `15: L13h-<mã> …` + review trước bước kế)
| Mã | Việc | Phụ thuộc | Giờ | Coder |
|---|---|---|---|---|
| R0 | Review S1–S3 của 13g APPROVE (gồm kết luận về `skeleton` gộp = 0). | — | — | reviewer |
| S3a | Sửa `scripts/level1_gesture_diag.py` theo §3 (+ sửa gộp `skeleton` nếu R0 xác nhận lỗi); test AC-13h-1..3 (+ AC-13h-4 nếu có). | R0 | 1,5 | vslt-coder (agy) |
| S3b | Tái sinh D tại commit sạch, CÙNG lệnh 13g S3 (cùng `--process-fps 15.5`, cùng clip), GHI ĐÈ `gesture_diag_D.json` (bản cũ còn ở 84878b1); commit JSON riêng; đọc `decisions`, rẽ nhánh. | S3a APPROVE | 0,3 | orchestrator/cầu nối |
| S3c | Orchestrator đối chiếu `design_ok_gestures` với U2 (§3, G-0). | S3b | 0,1 | orchestrator |
| S5 | (nếu `fix_draw_raw`) như 13g. | S3b | 1 | agy |
| S6 | Config 13g như §3.4 của 13g: CHỈ các khóa trong `decisions.tuned_values` của JSON S3b (kỳ vọng ⊆ `wave_*`); `reason` chứa `15-lan-sua-13g` và nhắc `15-lan-sua-13h` + đường JSON. | S3b/S3c | 1 | agy |
| S6b | GF1/GF2 trên 770 clip với config 13g (lệnh S6b của 13g). Trượt ⇒ DỪNG, KHÔNG chỉnh lần hai. | S6 | 0,5 | orchestrator/cầu nối |
| U3/VU3, S7 | Như 13g: người dùng quay T; GT1/GT2 bằng `--mode gate`. Trượt ⇒ DỪNG. | S5, S6b | — | người dùng / cầu nối |
| S8 | Preset trỏ config 13g (chỉ khi GF+GT đạt), AC-11 của 13g. | S7 | 0,5 | agy (+ orchestrator commit hộ) |
Nhánh DỪNG: G-1(backspace) trượt, G-3 trượt, U2 không khớp `design_ok`, `tuned_values` chứa khóa `space_*` (mâu thuẫn với `design_ok` của space), GF/GT trượt ⇒ báo planner.

Số liệu: giá trị tới hạn của backspace CHỈ lấy từ `decisions.gestures.backspace` của JSON S3b, sau khi S3a APPROVE và JSON sinh ở commit
sạch. Không dùng số agy báo trong hội thoại/commit message.

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; chỉ planner đổi kèm lý do)
Đổi so với 13g: AC-6 phần G-0 được thay bằng AC-13h-1..3 (lý do: AC-6 cũ chốt G-0 chung — sai ý đồ "từng cử chỉ g" của §3.3; các phần G-1,
G-2, G-3, đột biến `>= 4`→`>= 3` và bỏ kẹp sàn giữ nguyên). AC-10 vẫn đọc `gesture_diag_D.json` (bản S3b). AC khác của 13g giữ nguyên.
- AC-13h-1 (bộ chạy giả `fires(values, clip)`): space design 5/5, backspace design 0/5, sàn backspace 5/5 ⇒ `gestures.space.status ==
  "design_ok"`, không khóa `space_*` trong `tuned_values`; `gestures.backspace.status == "tuned"`, `tuned_values` ⊆ `wave_*` và đúng giá trị
  tính tay của bộ giả; script không dừng; `design_ok_gestures == ["space"]`.
- AC-13h-2: cả hai design ≥ 4/5 ⇒ cả hai `design_ok`, `tuned_values == {}`, không cờ dừng; backspace design 0/5 và sàn 3/5 ⇒
  `stop_outside_config true`, `gestures.backspace.tuned_values == {}`, space vẫn `design_ok`; G-1/G-2 KHÔNG chạy cho g đã `design_ok`
  (bộ giả đếm lời gọi).
- AC-13h-3: G-3 gọi `fires` với bộ gộp (space = design, backspace = tuned) cùng lúc; bộ giả phát ngược hoặc phát trên `spell` ⇒
  `stop_combined true`. `counts` có đủ mục cho design, sàn, mọi giá trị lưới, hai biến thể; `rules` từng số khớp §3.3 của 13g.
- AC-13h-4 (chỉ nếu R0 xác nhận lỗi gộp skeleton): dữ liệu tổng hợp có độ lệch khác 0 ở khung `moving` ⇒ `skeleton.moving_*` p90 > 0 và
  bằng `numpy.percentile` trên đúng tập khung đó; đột biến khôi phục cách gộp cũ ⇒ test đỏ.
- Lệnh: `PY=.venv/Scripts/python`; `$PY -m unittest tests.test_level1_gesture_diag -v` xanh; `$PY -m unittest discover -s tests` không có
  FAILED/ERROR mới so với HEAD trước bước (so danh sách tên); `tests.test_level1_guard` xanh; không dùng skip.
- S3b: JSON có `code_dirty false`, `generated_by.commit` = commit S3a; lệnh khớp 13g S3. Review đột biến: áp G-0 chung lại ⇒ AC-13h-1 đỏ.
- AC-G4 của 13g (GF1 ≤ 0.005, GF2 ≤ 0.010 trên `raw` và `smoothed`; GT1, GT2 ≥ 10/12) giữ nguyên, trượt ⇒ DỪNG.

## 5b. Phạm vi file
```scope
scripts/level1_gesture_diag.py
tests/test_level1_gesture_diag.py
reports/level1_realtime_2026-10-11/
configs/level1_gestures_13g.json
src/inference/level1_gestures.py
tests/test_level1_gestures_13g.py
level1_demo.py
tests/test_level1_demo_draw_raw.py
tests/test_level1_demo.py
docs/plans/15-progress.md
docs/plans/15-lan-sua-13g.md
docs/STATE.md
```
Giới hạn theo bước như §7 của 13g (`level1_demo.py` chỉ S5/S8; `tests/test_level1_demo.py` chỉ dòng 3788 ở S8; loader chỉ S6;
`docs/plans/15-lan-sua-13g.md` chỉ dòng con trỏ, do orchestrator).
Độ khó: S (S3a S); vùng nhạy cảm: có (tham số cử chỉ, đánh giá GF/GT, landmark nếu sửa gộp skeleton).

## 6. Rủi ro dữ liệu/ML
- D (5 clip/cử chỉ, 1 người) là tập chỉnh; tái sinh S3b trên CÙNG D với CÙNG lệnh — không thêm clip, không đổi F, không chạy lại để chọn lần.
- Space giữ design là lựa chọn bảo thủ (không nới); GF/GT vẫn kiểm cả hai cử chỉ với config 13g.
- Nếu `skeleton` gộp đúng là lỗi thì quyết định R-S của 13g (`mediapipe_limit`) đổi theo dữ liệu tái sinh — đó là sửa lỗi đo, luật R-S không đổi.
- Lệch train–realtime, n = 12, 1 người ký: như §8 của 13g.

## 7. Điểm dừng
- Không đổi model/preset mặc định trước S8 (sau GF+GT đạt). Không đụng thay đổi chưa commit của người dùng (`README.md`, `data/…`).
- DỪNG báo planner: R0 không APPROVE; G-1/G-3 trượt; U2 không khớp; GF/GT trượt; agy chạm file ngoài phạm vi.
- CẦN NGƯỜI DÙNG: chỉ U3/VU3 (đã có ở 13g). Nếu reviewer/orchestrator cho rằng §3 là ĐỔI quy tắc chứ không phải làm rõ ⇒ dừng và hỏi người dùng.

`> LẦN SỬA 13h (2026-10-11): xem docs/plans/15-lan-sua-13h.md — G-0..G-3 áp THEO TỪNG CỬ CHỈ (làm rõ "từng cử chỉ g" của §3.3 13g, số không đổi): space design_ok giữ design, backspace đi G-1/G-2, G-3 gộp; R0 review S1–S3 (kèm nghi lỗi skeleton gộp = 0)→S3a agy sửa decisions theo cử chỉ + counts k/5→S3b tái sinh D commit sạch→S3c đối chiếu U2→S6 config 13g chỉ khóa trong tuned_values (⊆ wave_*)→S6b GF 770 clip (trượt ⇒ DỪNG)→U3/S7 GT→S8 preset; số tới hạn chỉ lấy từ JSON sau APPROVE.`
