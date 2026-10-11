# Kế hoạch 15 — LẦN SỬA 13g: chẩn đoán cử chỉ không nhận + khung xương lệch (VU2), xử lý DC1 trượt

> LẦN SỬA 13h (2026-10-11): xem docs/plans/15-lan-sua-13h.md — G-0..G-3 áp THEO TỪNG CỬ CHỈ (làm rõ "từng cử chỉ g" của §3.3 13g, số không đổi): space design_ok giữ design, backspace đi G-1/G-2, G-3 gộp; R0 review S1–S3 (kèm nghi lỗi skeleton gộp = 0)→S3a agy sửa decisions theo cử chỉ + counts k/5→S3b tái sinh D commit sạch→S3c đối chiếu U2→S6 config 13g chỉ khóa trong tuned_values (⊆ wave_*)→S6b GF 770 clip (trượt ⇒ DỪNG)→U3/S7 GT→S8 preset; số tới hạn chỉ lấy từ JSON sau APPROVE.

**CẦN NGƯỜI DÙNG** (chặn S3 trở đi, KHÔNG chặn S1/S2/S9): U1 quay 12 clip chẩn đoán + U2 chạy app 1 phút (§5); U3 quay 24 clip kiểm
(chỉ khi S6 có đổi ngưỡng); VU3 nhìn lại khung xương sau S5. Không đổi model chữ cái; preset chỉ đổi file cử chỉ ở S8 sau khi GF+GT đạt.

Phân công (quyết định người dùng 2026-10-11): Claude chỉ lập kế hoạch + review; mã do agy (`vslt-coder` cầu nối, Gemini effort ≥ high);
mỗi bước 1 commit + review TRƯỚC bước kế. Hiệu lực: THAY protocol thu clip của §3.4 `15-lan-sua-13.md` (ngưỡng GT1/GT2 giữ nguyên, lý do §3.5);
mọi tiêu chí khác của 13/13d/13f giữ nguyên.

## 1. Mục tiêu và DoD
- (1) Tìm ĐIỀU KIỆN nào làm cử chỉ cố ý không phát trên dữ liệu thật của người dùng; chỉ nới ngưỡng theo quy tắc đặt trước (§3.3), rồi
  bắt buộc GF1/GF2 (770 clip) + GT1/GT2 (clip riêng). (2) Đo nguồn lệch khung xương rồi sửa theo quy tắc đặt trước. (3) Chốt DC1 = Giới hạn.
- DoD phục vụ: demo Cấp 1 desktop dùng được (hạng mục 1 và 5 của kế hoạch 15 lần sửa 13), số liệu truy được (JSON + lệnh + commit).

## 2. Hiện trạng (đọc mã, không đoán)
- Preset LUÔN được chèn trước argv khi không `--headless`: `level1_demo.py:1810-1827` `DEFAULT_DEMO_ARGV` gồm `--smooth-landmarks`,
  `--gesture-space --gesture-backspace --gesture-config configs/level1_gestures.json`, `--min-detection-conf 0.55`. ⇒ Lệnh VU2 của người
  dùng chạy CÓ làm mượt landmark (dù không gõ cờ), conf 0.35 (argv sau thắng), và đường cử chỉ cũ KHÔNG thể bật lại bằng cách "bỏ
  --gesture-config" (preset luôn thêm). `--gesture-space/--gesture-backspace` là `BooleanOptionalAction` (`:1778`, `:1793`) ⇒ tắt được bằng `--no-…`.
- Khung xương: `_process` (`level1_demo.py:1407-1470`): `session.process(frame_mp)` (`:1420`, `frame_mp` = ảnh CLAHE khi `--auto-enhance`,
  cùng hình học) → nếu làm mượt thì `landmarks = landmark_smoother.filter(...)` (`:1425-1426`) → `draw_landmarks(frame, landmarks)` (`:1467`)
  vẽ landmark ĐÃ LÀM MƯỢT lên đúng khung đã xử lý → `display_view` lật gương (`:453-455`) → `render_to_window` co giãn đều. Vì vẽ trên chính
  khung đưa vào MediaPipe nên KHÔNG có lệch thời gian giữa ảnh và landmark thô; nguồn lệch khả dĩ chỉ còn: (a) trễ của `LandmarkSmoother`
  (`src/inference/level1_core.py:707-753`, alpha 0.6 khi chậm / 0.9 khi nhanh), (b) sai số MediaPipe chế độ video (bám ROI khung trước;
  `src/inference/hand_live.py:24-30`: video mode, complexity 1, tracking 0.5) + ngưỡng detection 0.35, (c) CLAHE đổi kết quả MediaPipe.
  Chưa có số đo nào cho (a)/(b)/(c).
- Cử chỉ: `src/inference/level1_gestures.py` — `DeliberateSpaceGesture` (`:162`), `WaveBackspaceGesture` (`:229`), `GestureEngine.step`
  (`:340-380`, trả `is_palm`, `is_flat`); app gọi tại `level1_demo.py:1449-1451` với `still = segmenter.state != "moving"` và landmark ĐÃ làm mượt.
  G3 (`reports/level1_realtime_2026-10-08/gesture_false_trigger.json`) chỉ đo kích hoạt nhầm; độ nhạy chưa đo. `scripts/level1_gesture_check.py`
  CHƯA có chế độ `--positives` (argparse `:428-437`) ⇒ G5 cũ chưa chạy được.
- Phím: `KEY_ACTIONS` có 32 = space, 8 = backspace (`level1_demo.py:129-131`).
- DC1: 3 lần F4(a) ratio_p50 1.0391 / 1.6356 / 1.8550 (đọc từ `docs/plans/15-progress.md:1936-1942`; JSON ở `_work/_plan15_l13/l13f_f4_run{1,2,3}.json`, chưa commit).

## 3. Thiết kế

### 3.1 Lệnh demo TẠM (dùng ngay, không cần mã mới)
```
.venv\Scripts\python level1_demo.py --min-detection-conf 0.35 --auto-enhance --no-gesture-space --no-gesture-backspace
```
(preset vẫn thêm webcam 0, gương, rev9, khóa tay, làm mượt, Unikey). Dấu cách/xóa bằng phím SPACE / BACKSPACE trên cửa sổ. KHÔNG khuyên đường
cử chỉ cũ: không bật được qua preset và thăm dò cũ đã có kích hoạt nhầm (24/640, 8/640 — số của kế hoạch 13 §3.3). Không khuyên
`--no-smooth-landmarks` cho demo (đổi đầu vào bộ nhận dạng so với preset).

### 3.2 Script chẩn đoán `scripts/level1_gesture_diag.py` (mới; một đường ống, dùng cho D, T và khung xương)
Đầu vào: `--clips-dir DIR` có thư mục con `space/`, `backspace/`, `spell/` (mp4 bất kỳ, sắp theo tên; thư mục thiếu = 0 clip).
Đường ống mỗi clip = đường app (tái dùng hàm có sẵn, không chép logic):
1. Đọc khung bằng cv2; timestamp = `CAP_PROP_POS_MSEC` nếu tăng chặt và > 0 từ khung 2, ngược lại `i*1000/fps` (ghi nguồn timestamp vào JSON).
2. Cắt giữa về tỉ lệ 4:3 rồi `INTER_AREA` về `camera_width × camera_height` của `configs/level1_demo_classifier_rev9.json` (640×480); ảnh đã 640×480 giữ nguyên.
3. `--process-fps F` (tùy chọn): giữ khung khi `ts ≥ ts_giữ_trước + 1000/F` (mô phỏng app bỏ khung).
4. `enhance_low_light` (bật mặc định, `--no-auto-enhance` tắt) → `HandLandmarkSession(min_detection_confidence=0.35)` mới cho mỗi clip →
   `HandednessLock` như `--dominant-hand lock` → `LandmarkSmoother` (đường `smoothed`; đường `raw` báo cáo) → `Level1SignSegmenter` giá trị rev9
   (dựng như `scripts/level1_gesture_check.py` `run_clip`/`min_detected_frames_of`) → `still` → `GestureEngine(values).step`.
5. Phiên tham chiếu cho khung xương trên CÙNG khung: `HandLandmarkSession(static_image_mode=True, min_detection_confidence=0.35)` (phát hiện
   lại từng khung, không bám ROI) và phiên video không CLAHE.
Nhận phiên MediaPipe qua tham số `session_factory` (test tiêm phiên giả, không cần MediaPipe/dữ liệu).

**Khung xương** (khung có cả hai landmark): `dev(a,b) = mean_j ‖a_j − b_j‖ / palm_len(a_raw)` trên `aspect_points` (pixel 640×480).
`smooth = dev(smoothed, raw)`, `track = dev(raw_video, static)`, `enh = dev(raw CLAHE, raw không CLAHE)`; p50/p90 trên mọi khung và trên khung
`moving`; tỉ lệ khung có tay của từng phiên. Ảnh overlay (raw xanh lá, smoothed đỏ = cái app đang vẽ, static xanh dương) 6 khung/clip
(3 khung `smooth` lớn nhất, 3 khung `track` lớn nhất) ghi vào `_work/l13g/overlay/` — CÓ MẶT người dùng, KHÔNG commit.

**Cử chỉ — ablation chỉ qua `GestureEngine`** (không viết lại điều kiện): với mỗi clip, chạy lại engine trên chuỗi khung đã tính (landmark +
still) với bộ giá trị khác nhau:
- `design` = `configs/level1_gestures.json`; `floor` = mọi khóa chỉnh được đặt ở giá trị sàn §3.3 (lỏng nhất cho phép);
- giá trị tới hạn cô lập `c_i(p)` = giá trị CHẶT nhất trên lưới của khóa p mà clip còn phát, các khóa chỉnh được khác ở `floor`.
- Báo cáo thêm (không quyết định): tỉ lệ khung có tay, `is_palm`, `is_flat`, `still` trên khung có tay; số nét tối đa trong cửa sổ; số lần
  phát cử chỉ ngược (space trong clip backspace và ngược lại); kết quả `raw` vs `smoothed`.

Chế độ `--mode gate` (cho T): đếm GT1/GT2 (§3.5) với `--gesture-config` cho trước, đường `smoothed`, fail-closed khi số clip mỗi cử chỉ ≠ 12.

JSON: `generated_by` (argv, commit, `code_dirty`), sha256 hai config + rev9, nguồn timestamp, biến thể (native / process-fps), `skeleton`,
`gestures.per_clip`, `rules` (hằng của script, chú thích "đặt trước ở 15-lan-sua-13g §3.3"), `decisions`. Đường dẫn tương đối, không chứa ảnh.

### 3.3 Quy tắc quyết định (ĐẶT TRƯỚC khi có dữ liệu; mã hóa thành hằng trong script; coder và orchestrator không đổi)
**R-S (khung xương)**, gộp mọi clip D, khung `moving`:
- R-S1: `p90(smooth) > p90(track)` ⇒ `fix_draw_raw = true` (vẽ landmark thô, đường nhận dạng giữ landmark mượt — S5).
- R-S2: `p90(enh) > p90(track)` ⇒ `suggest_no_auto_enhance = true` (chỉ ghi chú lệnh demo, không đổi mã).
- Không cái nào ⇒ `mediapipe_limit = true` ⇒ ghi Giới hạn R2 + overlay cho người dùng xem.
Lý do: `track` = độ bất đồng giữa hai chế độ MediaPipe trên cùng khung ≈ độ bất định nội tại; phần do đường ống thêm vào lớn hơn nó mới đáng sửa.

**R-G (cử chỉ)**, từng cử chỉ g (5 clip D), tính trên CẢ biến thể native và biến thể `--process-fps` (F = số khung xử lý / thời lượng đọc
từ JSON U2; thiếu U2 ⇒ chỉ native, ghi rõ):
- Khóa chỉnh được, sàn và lưới (chiều "chặt"):
  | khóa | design | sàn (lỏng nhất) | lưới | chặt hơn khi |
  |---|---|---|---|---|
  | `space_hold_ms` | 600 | 400 (> `cls_stable_ms` 300 của rev9) | 400..600 bước 50 | lớn hơn |
  | `space_dropout_frames` | 1 | 3 | 1..3 | nhỏ hơn |
  | `wave_window_ms` | 1500 | 2500 | 1500..2500 bước 250 | nhỏ hơn |
  | `wave_min_amplitude` | 0.6 | 0.35 (= `legacy_flick_palm_ratio`) | 0.35..0.6 bước 0.05 | lớn hơn |
  | `wave_max_vertical_ratio` | 0.5 | 1.0 (ngang ≥ dọc) | 0.5..1.0 bước 0.1 | nhỏ hơn |
  | `wave_min_flat_fraction` | 0.9 | 0.6 (đa số khung phẳng) | 0.6..0.9 bước 0.05 | lớn hơn |
  KHÔNG chỉnh: `wave_min_strokes` (=2, định nghĩa "vẫy" theo Q5), `space_rearm_ms`, `wave_cooldown_ms`, `flat_thumb_*`, `gesture_flash_ms`,
  `legacy_*`, ngưỡng `is_open_palm_space`, ngưỡng chuyển động segmenter rev9.
- G-0: `design` phát ở ≥ 4/5 clip của g trên CẢ hai biến thể ⇒ `stop_offline_ok` (offline đạt mà app không ⇒ lệch app/offline) ⇒ DỪNG, planner.
- G-1: `floor` phát ở < 4/5 clip ⇒ `stop_outside_config` (tác nhân nằm ngoài khóa chỉnh được: bàn tay xòe/phẳng không nhận, `still` không
  đạt, mất tay, < 2 nét) ⇒ DỪNG, planner (thiết kế lại; số liệu báo cáo nêu điều kiện nào).
- G-2: với mỗi khóa p của g: giá trị mới = giá trị CHẶT nhất trên lưới thỏa ≥ 4/5 clip (`c_i(p)` cho phép), không bao giờ chặt hơn design;
  lấy giá trị LỎNG hơn giữa hai biến thể.
- G-3: chạy lại với bộ giá trị mới (mọi khóa cùng lúc) trên D: mỗi g phát ≥ 4/5, 0 lần phát cử chỉ ngược trên mọi clip, 0 lần phát gì trên
  2 clip `spell`. Không đạt ⇒ `stop_combined` ⇒ DỪNG, planner. Đạt ⇒ `decisions.tuned_values` (chỉ các khóa khác design).
- G-4 (sau S6, bắt buộc): GF1/GF2 của §3.3 kế hoạch 13 trên 770 clip với config mới (ngưỡng giữ nguyên) và GT1/GT2 (§3.5) trên T. Trượt ⇒
  DỪNG; KHÔNG chỉnh lần hai (D đã là tập chỉnh; T đã dùng sẽ thành tập chỉnh).

### 3.4 Sửa
- S5 (nếu `fix_draw_raw`): trong `_process` giữ `landmarks_raw` ngay sau `session.process`/khóa tay; `draw_landmarks(frame, landmarks_raw)`.
  Mọi thứ khác (segmenter, cửa sổ, cử chỉ, JSON, chặng thời gian) dùng landmark như cũ. Không cờ mới.
- S6 (nếu `tuned_values`): file MỚI `configs/level1_gestures_13g.json` = bản sao `level1_gestures.json`, khóa trong `tuned_values` mang giá trị
  đó với `"source": "tuned_13g"`, `reason` nêu quy tắc G-2 + đường JSON D; loader `validate_gesture_config` chấp nhận `source ∈ {"design",
  "tuned_13g"}`, `tuned_13g` bắt buộc `reason` chứa `15-lan-sua-13g`; nguồn khác vẫn ValueError. File cũ không đổi (`level1_core` vẫn đọc nó).
- S8 (chỉ khi G-4 đạt): `DEFAULT_DEMO_ARGV` trỏ `configs/level1_gestures_13g.json`.

### 3.5 Sửa protocol G5 (§3.4 kế hoạch 13) — trước khi có bất kỳ clip cử chỉ nào, nên không phải chỉnh sau khi thấy kết quả
Giữ: 12 clip/cử chỉ, GT1 ≥ 10/12 clip `space` có ≥ 1 space và 0 backspace, GT2 ≥ 10/12 clip `backspace` có ≥ 1 backspace và 0 space, đường
`smoothed`. Đổi: quay bằng Windows Camera, đánh giá bằng `level1_gesture_diag.py --mode gate` (đường ống y app: conf 0.35, CLAHE, video mode,
khóa tay, làm mượt, `--process-fps` như S3). Lý do: collector cũ cố định 2 s và ghi mp4 với fps danh nghĩa 30 (`collect_targeted_signs.py:51,214`)
⇒ timestamp có thể sai, mà mọi ngưỡng cử chỉ tính bằng ms; npz của collector không qua CLAHE/conf 0.35 như app.

## 4. Chia việc (mỗi bước 1 commit `15: L13g-<mã> …` + review trước bước kế)
| Mã | Việc | Phụ thuộc | Giờ | Coder |
|---|---|---|---|---|
| S9 | Commit 3 JSON DC1 làm bằng chứng TRƯỢT: chép `_work/_plan15_l13/l13f_f4_run{1,2,3}.json` → `reports/level1_realtime_2026-10-10/display_cost_fail_run{1,2,3}.json` (không sửa nội dung); progress ghi Giới hạn §6. | — | 0,2 | cầu nối/orchestrator |
| S1 | Script phần 1: đọc video, timestamp, cắt/co, process-fps, đường ống app (session_factory tiêm được), khung xương + overlay + R-S, khung JSON. Test tổng hợp AC-1..AC-4. | — | 2 | agy |
| S2 | Script phần 2: ablation cử chỉ, R-G (G-0..G-3), `--mode gate`. Test AC-5..AC-8. | S1 APPROVE | 2 | agy |
| U1/U2 | NGƯỜI DÙNG §5 (song song S1/S2). | — | 15 phút | người dùng |
| S3 | Chạy D: `PY scripts/level1_gesture_diag.py --clips-dir data/collected_gestures/13g_D --process-fps F --out reports/level1_realtime_2026-10-11/gesture_diag_D.json` tại commit sạch; commit JSON riêng. Đọc `decisions`, rẽ nhánh. | S2, U1, U2 | 0,3 | cầu nối |
| S5 | (nếu `fix_draw_raw`) vẽ landmark thô + test AC-9. | S3 | 1 | agy |
| S6 | (nếu `tuned_values`) config 13g + loader + test AC-10. | S3 | 1 | agy |
| S6b | G3 với config 13g: `PY scripts/level1_gesture_check.py --gesture-config configs/level1_gestures_13g.json --out reports/level1_realtime_2026-10-11/gesture_false_trigger_13g.json`; GF1/GF2. | S6 | 0,5 | cầu nối |
| U3/VU3 | NGƯỜI DÙNG quay T (§5) sau S5/S6b; nhìn khung xương (VU3). | S5, S6b | 15 phút | người dùng |
| S7 | `PY scripts/level1_gesture_diag.py --mode gate --clips-dir data/collected_gestures/13g_T --gesture-config configs/level1_gestures_13g.json --process-fps F --out reports/level1_realtime_2026-10-11/gesture_sensitivity_13g.json`; GT1/GT2. | U3 | 0,3 | cầu nối |
| S8 | (GF+GT đạt) preset trỏ config 13g + AC-11. | S7 | 0,5 | agy (+ orchestrator commit hộ, §8) |
Nhánh DỪNG (G-0/G-1/G-3/G-4 trượt) ⇒ báo planner; demo dùng lệnh §3.1.

## 5. Việc NGƯỜI DÙNG (hướng dẫn quay, tiếng Việt)
Chung: Windows Camera, chế độ Video, đặt máy/đèn như lúc demo, ngồi như lúc ký; nếu Cài đặt cho chọn 480p 4:3 thì chọn. Mỗi clip là MỘT lần
làm: bắt đầu ghi khi tay ĐANG HẠ ngoài khung → đưa tay lên làm cử chỉ y như khi dùng app → hạ tay ra khỏi khung → dừng ghi (~3–5 giây).
Sau khi quay, chuyển file từ `Pictures\Camera Roll` vào đúng thư mục con.
- **U1 (12 clip, ~8 phút)** → `data\collected_gestures\13g_D\`
  - `space\` 5 clip: xòe đủ 5 ngón, ngón cái dang ra, giữ yên như bạn vẫn làm để thêm dấu cách.
  - `backspace\` 5 clip: bàn tay phẳng, vẫy ngang như bạn vẫn làm để xóa.
  - `spell\` 2 clip (~10 giây): đánh vần thường một từ 5–6 chữ cái, KHÔNG làm cử chỉ.
- **U2 (~1 phút)**: chạy `.venv\Scripts\python level1_demo.py --min-detection-conf 0.35 --auto-enhance --out-json _work/l13g/u2_app.json`,
  làm 3 lần dấu cách + 3 lần vẫy xóa, bấm q. (Cho số khung xử lý/giây thật và bộ đếm cử chỉ của app.)
- **U3 (24 clip, chỉ khi S6 đổi ngưỡng; quay SAU khi được báo)** → `data\collected_gestures\13g_T\space\` 12 clip, `…\backspace\` 12 clip,
  cùng cách như U1 (không xem kết quả D trước khi quay). **VU3**: chạy lệnh §3.1 sau S5, cho biết khung xương còn lệch không.
Clip có mặt người dùng: không commit (đã bị `*.mp4` gốc chặn); orchestrator chép `G:\My Drive\VSLT\` + SHA256SUMS như user1.

## 6. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)
Lệnh test: `PY=.venv/Scripts/python`. Mọi test mới chỉ dùng dữ liệu tổng hợp/phiên giả: KHÔNG dùng `@unittest.skipUnless`/`skipIf`/`skip`
(tránh agy-guard SKIP_ADDED, backlog 0c — không cần miễn trừ).
- AC-1 (S1) cắt/co: 1280×720 → 640×480 lấy vùng giữa 960×720; 640×480 giữ nguyên từng pixel; 480×640 dọc → cắt giữa đúng 4:3.
- AC-2 (S1) timestamp: POS_MSEC tăng chặt ⇒ dùng nó; POS_MSEC toàn 0 hoặc không tăng ⇒ `i*1000/fps`, JSON ghi nguồn; `--process-fps 15`
  trên chuỗi 30 fps giữ khung cách ≥ 66.67 ms, khung đầu luôn giữ.
- AC-3 (S1) khung xương: `dev(a, a + d·e_x)` = `d / palm_len` (sai ≤ 1e-6); khung thiếu một phía bị loại và đếm; p50/p90 = `numpy.percentile`
  mặc định; phiên giả xác nhận đường ống gọi CLAHE trước MediaPipe, làm mượt sau MediaPipe, segmenter nhận landmark mượt (như app).
- AC-4 (S1) R-S: bảng biên: `p90(smooth) == p90(track)` ⇒ `fix_draw_raw false`; lớn hơn 1e-9 ⇒ true; tương tự R-S2; không cái nào ⇒
  `mediapipe_limit true`.
- AC-5 (S2) ablation dùng `GestureEngine` thật: chuỗi tổng hợp (vá `is_flat_hand_backspace`/`is_open_palm_space` trong module
  `level1_gestures` nếu cần, hoặc dùng bộ dựng bàn tay của `tests/test_level1_gestures.py`) — vẫy 2 nét biên độ 0.8×palm phát ở design;
  biên độ 0.5×palm không phát ở design, `c(wave_min_amplitude)` = 0.5 hoặc 0.45 tùy lưới (test ghi đúng giá trị tính tay); giữ xòe 500 ms
  không phát ở design, `c(space_hold_ms)` = 500.
- AC-6 (S2) R-G với bộ chạy giả (hàm `fires(values, clip)` tiêm vào): G-0, G-1, G-2 (đúng ≥ 4/5, không chặt hơn design, lấy lỏng hơn của
  hai biến thể, không vượt sàn), G-3 (phát ngược hoặc phát trên `spell` ⇒ `stop_combined`). Hằng `rules` trong JSON khớp bảng §3.3 từng số.
- AC-7 (S2) `--mode gate`: 10/12 + 0 ngược ⇒ pass; 9/12 ⇒ fail; 10/12 nhưng 1 clip phát ngược ở clip đếm đạt ⇒ clip đó không đạt;
  số clip ≠ 12 ⇒ `pass false` + lý do.
- AC-8 (S1+S2) JSON: có `generated_by.commit`, `code_dirty`, sha256 config; `grep -ciE 'users[\\/]+'` trên JSON test ⇒ 0; không khóa nào chứa ảnh.
- AC-9 (S5) test mới: app với phiên giả + `--smooth-landmarks`, vá `level1_demo.draw_landmarks` để bắt đối số: đối số == landmark thô của khung
  đó (khác landmark mượt), và `segmenter.push`/`GestureEngine` vẫn nhận landmark mượt; không làm mượt ⇒ như cũ. Đột biến: hoàn `:1467` về
  `landmarks` ⇒ test mới đỏ (log `_work/l13g/s5_mut.log`).
- AC-10 (S6) loader: `tuned_13g` + reason chứa `15-lan-sua-13g` ⇒ nạp; reason thiếu ⇒ ValueError; source khác ⇒ ValueError; config cũ nạp như
  trước; mọi khóa của config 13g = design trừ khóa trong `decisions.tuned_values` của `gesture_diag_D.json` (test đọc JSON đã commit, so từng số).
- AC-G4 (S6b, S7): GF1 ≤ 0.005, GF2 ≤ 0.010 trên `raw` và `smoothed` (JSON `pass true`, `code_dirty false`); GT1 ≥ 10/12, GT2 ≥ 10/12.
  Trượt ⇒ DỪNG, không chạy lại để chọn lần.
- AC-11 (S8): `DEFAULT_DEMO_ARGV` chứa `configs/level1_gestures_13g.json`; ngoại lệ test DUY NHẤT: hằng `GESTURE_CONFIG` ở
  `tests/test_level1_demo.py:3788` đổi sang đường mới (1 dòng), không sửa dòng test nào khác.
- Mọi bước có mã: `$PY -m unittest tests.test_level1_gesture_diag -v` (và file test của bước) xanh; bộ đầy đủ `$PY -m unittest discover -s tests`
  không có FAILED/ERROR mới so với HEAD trước bước (so danh sách tên); `tests.test_level1_guard` xanh.
- Review (Claude) đọc đủ diff + test; chạy ≥ 2 đột biến ở S2 (đổi `>= 4` thành `>= 3`; bỏ kẹp sàn) ⇒ test đỏ.

## 7. Phạm vi file
```scope
scripts/level1_gesture_diag.py
tests/test_level1_gesture_diag.py
level1_demo.py
tests/test_level1_demo_draw_raw.py
tests/test_level1_demo.py
src/inference/level1_gestures.py
tests/test_level1_gestures_13g.py
configs/level1_gestures_13g.json
reports/level1_realtime_2026-10-11/
reports/level1_realtime_2026-10-10/display_cost_fail_run*.json
docs/plans/15-progress.md
docs/STATE.md
```
`level1_demo.py` chỉ ở S5 (dòng vẽ) và S8 (preset); `tests/test_level1_demo.py` chỉ dòng 3788 ở S8; `src/inference/level1_gestures.py` chỉ loader ở S6.
Độ khó: M (S1 M, S2 M, S5 S, S6 S, S8 S); vùng nhạy cảm: có (landmark/đường ống app, tham số cử chỉ, đánh giá GF/GT).

## 8. Rủi ro dữ liệu/ML
- Tập chỉnh D (5 clip/cử chỉ, 1 người) nhỏ: quy tắc 4/5 + sàn chặn nới quá; GF/GT bắt buộc sau đó; T quay SAU khi config 13g đã commit.
- Lệch train–realtime: D/T đi qua đường ống app (conf 0.35, CLAHE, video mode, làm mượt) nhưng camera Windows Camera ≠ dshow 640×480 (cắt/co
  khác sensor) ⇒ ghi Giới hạn; U2 cho fps thật của app.
- n = 12/cử chỉ là kiểm khói, khoảng tin cậy rộng; chỉ 1 người ký ⇒ không suy rộng.
- `track` (static vs video) không phải nhãn đúng; R-S chỉ so tương đối.
- agy-guard 0c: tránh bằng test không cần dữ liệu (không decorator bỏ qua). Nếu agy-guard vẫn chặn sửa `tests/test_level1_demo.py` ở S8: orchestrator
  kiểm diff (đúng 1 dòng 3788) rồi commit hộ như T2.
- DC1: ratio nhạy tải máy/thứ tự lượt (quan sát, chưa chứng minh). KHÔNG đo lại theo phương pháp mới trong 13g (đổi phương pháp sau khi thấy
  kết quả = dời cột gôn). Giới hạn R2 (`docs/level1_desktop.md`, bước R2 cũ): "DC1 (ngưỡng 1.25 đặt trước) trượt 2/3 lần ở bố cục 13f —
  số trong `reports/level1_realtime_2026-10-10/display_cost_fail_run{1,2,3}.json`; chặng mediapipe lượt 1080p cao hơn lượt natural trong cùng lần
  đo nên ratio lẫn tải máy; VU2 người dùng chấp nhận cửa sổ." Muốn gate mới (vd lượt xen kẽ, trung vị K cặp, chỉ chặng hud) ⇒ kế hoạch mới,
  đặt trước, và DC1 cũ vẫn ghi TRƯỢT.

## 9. Điểm dừng
- CẦN NGƯỜI DÙNG: U1+U2 trước S3; U3+VU3 sau S5/S6b.
- Đổi hành vi mặc định (preset cử chỉ) chỉ ở S8 sau GF1/GF2/GT1/GT2 đạt; không đổi model chữ cái.
- DỪNG báo planner: `stop_offline_ok` / `stop_outside_config` / `stop_combined`; GF/GT trượt; test cũ đỏ; agy chạm file ngoài phạm vi.
- Không đụng thay đổi chưa commit của người dùng (`README.md`, `data/…` đang M/D trong `git status`).

`> LẦN SỬA 13g (2026-10-11): xem docs/plans/15-lan-sua-13g.md — VU2: chẩn đoán cử chỉ không nhận (người dùng quay 12 clip D + chạy app 1 phút; script level1_gesture_diag.py ablation qua GestureEngine, quy tắc nới ngưỡng G-0..G-3 đặt trước, sàn cố định) và khung xương lệch (đo smooth/track/CLAHE, R-S ⇒ vẽ landmark thô); S9→S1→S2 (agy)→S3 (cầu nối)→S5/S6 (agy)→S6b GF→U3 T 24 clip→S7 GT→S8 preset; DC1 = Giới hạn (3 JSON trượt commit làm bằng chứng); demo tạm: --no-gesture-space --no-gesture-backspace + phím SPACE/BACKSPACE.`
