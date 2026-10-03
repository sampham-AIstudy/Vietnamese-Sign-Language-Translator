# Kế hoạch 15 — LẦN SỬA 1 (phụ lục): dấu thanh + khung text kiểu bộ gõ

TRẠNG THÁI: XONG (planner, 2026-10-03). KHÔNG có điểm "CẦN NGƯỜI DÙNG" để bắt đầu (xem §7). Không đổi model mặc định.

Hiệu lực: phụ lục này có hiệu lực như nằm trong `docs/plans/15-level1-realtime-desktop.md` (orchestrator chèn dòng con trỏ vào file gốc).
Người lập: vslt-planner, HEAD d7d39d8, nhánh feat/vslt-complete. Căn cứ: quyết định người dùng 2026-10-03 10:30, 10:45, 15:40, 17:20
(STATE.md), phản hồi U1 + phát hiện orchestrator (STATE.md dòng 10-24), `docs/plans/15-progress.md` (B0–B5 xong).

## 0. Phần nào của file gốc bị thay

| File gốc | Thay bằng |
|---|---|
| §3.1 bảng file | THÊM: `src/inference/level1_textbox.py`, `tests/test_level1_textbox.py`, `tests/test_level1_segment_report.py`, `reports/level1_realtime_<D>/tone_evidence.json`, `reports/level1_realtime_<D>/segment_check_{before,after}.json` (+ `segment_check_paced.json` nếu làm A4). `scripts/level1_segment_report.py` (vốn có ở §3.1) được mở rộng. KHÔNG làm `scripts/level1_replay_clips.py` (B7 cũ bị cắt; `--summary` chuyển vào `scripts/level1_segment_report.py`). Danh sách "Không sửa" của §3.1 GIỮ NGUYÊN. |
| §3.3 bộ tách | THÊM tham số `tail_still_keep_ms` (§3.A.3). Còn lại giữ. |
| §3.4 phím + HUD | THÊM phím `1`–`5` = dấu sắc/huyền/hỏi/ngã/nặng (quy ước VNI), nguồn "key" (§3.B.3). Dòng "Văn bản:" của HUD thay bằng khung text (§3.B). |
| §3.6 hiệu chỉnh | THAY bằng §3.A.3 (giữ 2 quy tắc cũ still_speed/hold_ms; thêm quy tắc max_segment_ms, tail_still_keep_ms, điểm dừng tách dấu). |
| §3.7 replay 10 clip | CẮT khỏi 15 (backlog): không làm `replay_clips.json`, `replay_paced.json`, `equivalence_continuous.json`/AC-E2. Thay bằng `segment_check_*.json` (A3) + kiểm paced dấu thanh (A4, cắt được). |
| §4 bước B6a–B9 | THAY bằng bảng §4 dưới (T1, A1, T2, A2, A3, C1, A4, C2). B0–B5 đã xong, không làm lại. |
| §5 AC-R | THAY bằng AC-R' (§5). AC-E2 bỏ. AC0/AC1/AC-S/AC-C/AC-D/AC-E1/AC-E3/AC-G/AC-T/AC-L GIỮ, có bổ sung ở §5. |
| §6.3 Giới hạn | THÊM mục 7–9 (§6.2 dưới). |
| §6.4 việc người dùng | THÊM U1b (sau T2) và U2b (tùy chọn, sau A3). U2 giữ. |
| §7 điểm dừng | THÊM điểm dừng 1–3, 5 của §7 dưới; điểm dừng gốc giữ. |

## 1. Mục tiêu + DoD

**A. Dấu thanh.** Làm rõ bằng chứng vì sao dấu thanh (ký hiệu có chuyển động) lỗi; sửa phần tách đoạn có thể sửa mà KHÔNG đổi model
(tham số theo phân bố clip train, cắt đuôi giữ yên thừa, trần độ dài); nêu trung thực giới hạn của model.
**B. Khung text kiểu bộ gõ.** Thay dòng "Văn bản:" bằng khung soạn thảo: chữ đang gõ + con trỏ, âm tiết đang gõ tô sáng, từ trước cố
định, ký dấu mới thì dấu đổi ngay (đúng `compose()`), Backspace xóa token cuối, ứng viên bị từ chối hiện mờ; logic soạn văn bản là lõi
thuần (web dùng lại), phần vẽ tách riêng.

DoD phục vụ (autopilot.md §1): DoD 2 (Đánh vần → ghép từ, đường desktop), DoD 6 (không kết quả giả: chữ chỉ từ `compose`, token từ model
hoặc phím có ghi nguồn), DoD 7 (không thêm vi phạm guard; E1 vẫn bằng hệt), một phần DoD 9 (Giới hạn trung thực về dấu thanh).

## 2. Hiện trạng + bằng chứng về dấu thanh

### 2.1 Báo cáo đánh giá của checkpoint triển khai (nested primary)
Nguồn: `reports/alphabet_nested_2026-09-25/primary/nested_report.json` (checkpoint triển khai = chạy này, `provenance.json:375-379`).
- Chữ cái top-1 theo fold: 83.08 / 86.15 / 78.57 / 94.62 (mean 85.60, sd 6.77) — dòng 42-46, 76-80, 110-114, 144-148, 169-178.
- Dấu thanh top-1 theo fold (n = 30 mỗi fold): hau 50.0, khoi 46.67, tai 10.0, vy 56.67; mean 40.83, sd 20.97, ci95 [7.46, 74.20] —
  dòng 47-51, 81-85, 115-119, 149-153, 180-190.
- Theo LỚP (planner đếm tay từ `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv`, run=frame, 24 clip/lớp = 6/người;
  A1 PHẢI sinh lại bằng script và tự kiểm tổng theo fold khớp nested_report.json; số trong báo cáo chỉ lấy từ JSON của A1):
  dấu huyền 2/24, dấu nặng 18/24, dấu hỏi 8/24, dấu sắc 10/24, dấu ngã 11/24 (tổng 49/120, khớp mean 40.83). Trong 71 lỗi: khoảng 40 nhầm
  sang dấu khác, khoảng 31 nhầm sang chữ cái (a, l, i, ơ, ô, p, g…). Ví dụ: tai dấu hỏi 5/6 → "dấu huyền"; hau dấu sắc 4/6 → "a";
  khoi dấu huyền 4/6 → "dấu nặng".
- ⇒ Dấu thanh yếu NGAY Ở ĐÁNH GIÁ OFFLINE trên clip đã cắt sẵn (không liên quan tách đoạn realtime). Lỗi người dùng thấy trên webcam phần
  lớn là giới hạn MODEL/DỮ LIỆU (6 clip/dấu/người, 4 người); tách đoạn tốt nhất cũng chỉ đưa realtime về gần mức offline, không vượt.

### 2.2 Quỹ đạo cổ tay ĐÃ được thử cùng giao thức — không giúp dấu thanh
Nguồn: `reports/alphabet_nested_2026-09-25/variants/nested_report.json` (cùng giao thức nested LOSO, seed 42, 636 clip hauuto; biến thể
`frame_traj`/`time_traj` = `wrist_trajectory: True` → `features_with_wrist_trajectory`; `scripts/train_alphabet_nested.py:44-47`,
`src/data/alphabet_preprocessing.py:260-267,302-303`):

| biến thể | dấu thanh mean (sd) | chữ cái mean (sd) | dòng trong JSON |
|---|---|---|---|
| frame (= triển khai) | 40.83 (20.97) | 85.60 (6.77) | 160-190 |
| time | 38.33 (16.89) | 85.60 (6.22) | 335-360 |
| frame_traj | 36.67 (17.64) | 77.11 (5.71) | 510-535 |
| time_traj | 40.00 (15.63) | 76.34 (7.45) | 685-710 |

⇒ Thêm quỹ đạo cổ tay (cách đã cài) KHÔNG tăng dấu thanh và làm GIẢM chữ cái khoảng 8 điểm. Giả thuyết "model không thấy quỹ đạo nên lỗi
dấu" (STATE dòng 19-24) đúng một phần (model yếu dấu), nhưng phương án sửa bằng `features_with_wrist_trajectory` đã bị dữ liệu bác.

### 2.3 Video/landmark tone_* (train)
- `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` (cột num_frames, fps, detection_rate): ví dụ tone_s của hau 72–78 khung
  ở 21.2–30.4 fps; của tai 45–90 khung ở 26.5–29.0 fps; detection_rate 1.0 (dòng 128-133, 448-453). Mỗi clip = trọn MỘT ký hiệu,
  tay trong khung suốt clip (vài dòng đọc tay; phân bố đầy đủ do A1 sinh).
- CHƯA đo: đoạn đứng yên trước/sau/giữa nét dấu dài bao nhiêu, thời lượng chuyển động → A1 đo trên landmark npz (cùng hàm chuyển động của
  bộ tách), không cần đọc video.

### 2.4 Phiên webcam U1 (`_work/_plan15_u1/u1_2026-10-03_1650.json`; KHÔNG --expected ⇒ không phải độ chính xác; KHÔNG commit file này)
- counts (dòng 213-223): frames_read 11779, processed 9632, dropped 2146, processing_fps 24.92, capture_fps 30.47; 105 segment, 33 word_gap.
  Stages (dòng 157-211): mediapipe p50 28.5 ms, frame_total p50 52.6 ms, emit_to_token p50 73.4 ms.
- Segment: đa số 16–50 khung, close_reason chủ yếu `hold`. Một nhóm segment DÀI (ví dụ 97, 88, 108, 105, 99, 87, 76, 74, 67 khung; segment
  108 khung có t_end − t_start = 4000 ms = trần `max_segment_ms`) phần lớn ra "dấu ngã"/"d"/"g" confidence thấp và bị từ chối (dòng 229-320
  và tiếp). Segment ngắn dự đoán dấu (dấu sắc 33 khung 0.94; dấu ngã 45 khung 0.94; dấu nặng 18–36 khung) có lúc confidence cao — nhưng
  không biết người dùng đã ký gì.
- ⇒ Segment dài (gồm chuyển tiếp/chỉnh tay) là nhiễu; trần 4000 ms là giá trị THIẾT KẾ, chưa đối chiếu với thời lượng clip train → A2 đặt
  theo phân bố clip train. Muốn biết độ chính xác dấu trên webcam phải có phiên có `--expected` (U2b).

### 2.5 Mã liên quan
- `src/inference/level1_segmenter.py`: segment = từ đầu chuyển động (tái kích hoạt cắt bộ đệm về `_move_since`, `:259-263`) hoặc khung có tay
  đầu tiên (`:230-236`) tới khi đứng yên đủ `hold_ms` (`:267-276`); đuôi segment luôn chứa ~`hold_ms` khung đứng yên; `_trim` theo
  `max_segment_ms` (`:176-182`). Tham số bắt buộc `SEGMENTER_KEYS` (`:37-38`).
- `src/inference/level1_core.py`: `validate_level1_config` (`:76`, từ chối khóa lạ), `Level1Speller` (`:210-332`, `KEY_NAMES` `:207`),
  `composed()` = `compose(tokens)` (`:231-236`).
- `level1_demo.py`: `KEY_ACTIONS` (`:68`; phím `1`–`5` còn trống), `Hud` (`:293-337`, panel PIL dưới ảnh camera, cache theo nội dung),
  `_hud_lines` (`:522-541`, dòng "Văn bản:" + "Cảnh báo: <code>").
- `src/inference/fingerspelling_compose.py:118-147` `compose(tokens)` → {text, syllables, warnings}; dấu sau thay dấu trước kèm cảnh báo
  `multiple_tones` (`:103-106`); không nguyên âm → `tone_without_vowel` (`:109-112`); khoảng trắng giữ nguyên.
- Thiếu: `scripts/level1_segment_report.py` (B6a chưa làm); không có lõi khung text; không có phím dấu.

## 3. Thiết kế

### 3.A Dấu thanh

#### 3.A.1 Quyết định
- **A(a) LÀM** (không đổi model): hiệu chỉnh tách đoạn theo phân bố clip TRAIN + cắt đuôi giữ yên thừa + trần độ dài; kiểm bằng
  segment_check trên clip train (headless, tất định) và (tùy chọn) paced.
- **A(b) KHÔNG LÀM** trong 15: bằng chứng §2.2 (cùng giao thức nested LOSO, cùng dữ liệu) cho thấy `features_with_wrist_trajectory` không
  tăng dấu thanh (36.67 / 40.00 so với 40.83) và giảm chữ cái (77.11 / 76.34 so với 85.60). Train lại trên Kaggle với đặc trưng đó sẽ tốn
  GPU + một GATE đổi model mặc định mà bằng chứng sẵn có dự báo là không lợi. Không đăng ký GATE, không có điểm dừng đổi model.
  Nếu người dùng VẪN muốn thử hướng model khác (vd thêm dữ liệu dấu, tăng cường dữ liệu, kiến trúc khác) → kế hoạch RIÊNG sau báo cáo,
  có GATE đăng ký trước (cùng giao thức nested LOSO, cùng 636 clip, so `runs.*.summary.tones` và `letters`), là điểm CẦN NGƯỜI DÙNG của
  kế hoạch đó — không thuộc phụ lục này. Ước lượng để người dùng cân nhắc: thời gian máy không phải nút thắt (primary ghi `minutes`
  19.81, `nested_report.json:222`); chi phí chính là lập kế hoạch + đăng ký GATE + review (cỡ 1 ngày công agent) trong khi hạn mức tuần
  còn ~20% đến 8/10 và hạn báo cáo 6–8/10 ⇒ không kịp an toàn trước báo cáo.
- **Dự phòng cho demo:** phím dấu `1`–`5` trong khung text (§3.B.3): khi model không nhận đúng dấu, người trình bày gõ dấu, chữ đổi dấu
  ngay; nguồn "key" được ghi JSON và nêu trong Giới hạn. Không ẩn, không gọi là nhận dạng.
- Không làm (đã cân nhắc, bác): (i) chặn lớp theo mức chuyển động (chỉ cho dấu khi có chuyển động) — luật hậu xử lý mới, không kiểm được
  mà không rò rỉ (checkpoint triển khai đã train trên cả 4 người; kiểm trên clip train là lạc quan) → backlog; (ii) đổi cách lấy mẫu
  (`resample`) — phá tương đương train (E1); (iii) thêm khung giữ yên trước nét dấu (pre-roll) — khung trước nét dấu trên live là hình
  bàn tay của CHỮ TRƯỚC, khác clip train.

#### 3.A.2 Luồng (không đổi kiến trúc)
`Level1SignSegmenter` (thêm `tail_still_keep_ms`) → `SignSegment` → `Level1Classifier.classify` (KHÔNG đổi) → `Level1Speller`.
Tiền xử lý dùng chung: `alphabet_clip_features` (không đổi); chuyển động: `frame_motion` + trung vị cửa sổ của bộ tách (script A1 PHẢI
gọi lại đúng hàm/lớp này, không viết lại công thức).

#### 3.A.3 Hiệu chỉnh + quy tắc ĐẶT TRƯỚC (thay §3.6 gốc)
Script `scripts/level1_segment_report.py` (A1), đầu vào: `manifest.csv` + npz hauuto (= dữ liệu train của checkpoint), `nested_predictions.csv`
+ 2 `nested_report.json`, tùy chọn `--u1-json`. Timestamp clip = i × 1000 / fps của manifest.

Hồ sơ chuyển động mỗi clip (M_t = chuỗi `segmenter.motion` sau mỗi push, tạo bằng chính `Level1SignSegmenter` hoặc một hàm public tách
ra từ nó; tự kiểm bằng test: hai cách cho cùng chuỗi):
- `duration_ms` = ts cuối − ts đầu; `first_move_ms`/`last_move_ms` = ts khung đầu/cuối có M_t ≥ move_speed (không có → clip "no_motion",
  đếm riêng, không gán số);
- `leading_still_ms` = first_move − ts đầu; `trailing_still_ms` = ts cuối − last_move; `moving_ms` = last_move − first_move;
- `longest_still_ms` = đoạn liên tục dài nhất có M_t ≤ still_speed (cả clip); `longest_internal_still_ms` = như trên nhưng chỉ trong
  (first_move, last_move).
Thống kê theo nhóm (chữ cái / dấu thanh / từng dấu): n, p5, p10, p50, p90, p95 (`numpy.percentile` linear).

Quy tắc (script tính; coder KHÔNG gõ số; thứ tự tính như sau):
1. `still_speed` = p90 (qua clip CHỮ CÁI) của trung vị M_t từng clip (giữ §3.6). `move_speed` = still_speed × `move_over_still_ratio`.
2. Hồ sơ chuyển động tính lại với still/move của bước 1.
3. `hold_ms` = min(`hold_ms_design`, p10 qua clip CHỮ CÁI của `longest_still_ms`) (giữ §3.6).
4. `max_segment_ms` = ceil(p95 qua MỌI clip hauuto của `duration_ms`) (MỚI; thay giá trị thiết kế 4000).
5. `tail_still_keep_ms` = min(`hold_ms`, p50 qua MỌI clip có chuyển động của `trailing_still_ms`) (MỚI).
6. **Điểm dừng tách dấu (đặt trước):** nếu p90 qua clip DẤU THANH của `longest_internal_still_ms` ≥ `hold_ms` (tức ≥ 10% clip dấu bị cắt
   đôi giữa nét) → coder DỪNG, ghi 15-progress, báo planner. Không tự đổi quy tắc.
`--write-config` ghi 5 giá trị (still_speed, move_speed, hold_ms, max_segment_ms, tail_still_keep_ms) với
`source: "calibrated: reports/level1_realtime_<D>/tone_evidence.json@<commit>"`; khóa khác giữ `design`.

Hành vi `tail_still_keep_ms` (bộ tách): khi phát lý do `hold`, segment chỉ giữ các khung có ts ≤ `_still_since + tail_still_keep_ms`
(khung sau đó vẫn tính vào hold, chỉ không đưa vào segment). `tail_still_keep_ms == hold_ms` ⇒ hành vi giống hệt hiện tại (test khóa).
Lý do `hand_lost`/`end_of_stream` không đổi. Kiểm khi nạp config: 0 < tail_still_keep_ms ≤ hold_ms, ngược lại `ValueError`.

#### 3.A.4 Kiểm (không phải độ chính xác)
- `segment_check` (A3, headless, tất định, chạy bộ tách trên npz train như §3.6 gốc; phân loại bằng `Level1Classifier`): với config
  TRƯỚC (bản `configs/level1_realtime.json` tại commit 3ebc7b9, ghi ra `_work/_plan15/config_before.json` bằng `git show`) và SAU (sau
  `--write-config`), trên MỌI clip hauuto: số segment, close_reason, `single_segment` (đúng 1 segment), `window_agrees` (đúng 1 segment VÀ
  nhãn segment == nhãn trọn clip). Tổng hợp theo chữ cái / dấu thanh / từng dấu. JSON ghi: "train data of the deployed checkpoint; window
  agreement is not accuracy".
  (Config TRƯỚC không có khóa `tail_still_keep_ms` ⇒ script điền `tail_still_keep_ms = hold_ms` của chính config đó — tương đương hành vi
  cũ theo AC-S14 — và ghi rõ việc điền vào JSON.)
- Quy tắc giữ config SAU (đặt trước, trên số headless tất định): giữ nếu với nhóm DẤU THANH cả `single_segment_rate` và
  `window_agreement_rate` của SAU ≥ TRƯỚC, VÀ với nhóm CHỮ CÁI cả hai tỉ lệ SAU ≥ TRƯỚC − 0,02 (dung sai đặt trước: không đánh đổi chữ cái
  quá 2 điểm để lấy dấu). Không đạt → DỪNG, báo planner (không thử giá trị khác). Vẫn giữ AC-R1 gốc: tỉ lệ đúng-1-segment (chữ cái, dấu
  thanh tính riêng) < 0,9 với config SAU → DỪNG.
- A4 (tùy chọn, cắt được): cùng phép kiểm nhưng chạy app `--pace realtime --headless` trên video gốc của 120 clip dấu thanh (bỏ khung như
  webcam) → `segment_check_paced.json` có processing_fps/dropped mỗi clip — để báo cáo ảnh hưởng "fps thấp", KHÔNG dùng để chọn tham số.

### 3.B Khung text kiểu bộ gõ

#### 3.B.1 Lõi thuần `src/inference/level1_textbox.py` (không cv2/PIL/torch/thread; chỉ import `compose`, `token_kind`, `SPACE`, `TONE_MARKS`)
`textbox_view(tokens: Sequence[str], rejected: Optional[dict] = None) -> dict`:
- `committed` = `compose(tokens[:k])["text"]` với k = chỉ số sau SPACE cuối (không có SPACE → k = 0, committed ""); `active` =
  `compose(tokens[k:])["text"]`; `text` = `compose(tokens)["text"]`; bất biến `committed + active == text`.
- `cursor` = len(text) (con trỏ luôn ở cuối — bộ gõ chỉ thêm/xóa ở cuối).
- `active_tokens` = tokens[k:]; `active_tone` = tên dấu đang có hiệu lực trong âm tiết đang gõ (dấu CUỐI) hoặc None;
  `tone_changes` = danh sách {from, to} cho các dấu bị thay trong âm tiết đang gõ (từ cảnh báo `multiple_tones` của compose ứng với chỉ số
  trong `active_tokens`) — hiển thị là THÔNG TIN "đổi dấu", không phải cảnh báo.
- `warnings` = cảnh báo `tone_without_vowel` (toàn văn bản) — hiện là cảnh báo; `multiple_tones` ở âm tiết ĐÃ cố định không hiện.
- `preview` = nếu `rejected` có `prediction` (không None): {token, confidence, active_if_accepted = compose(tokens[k:] + [token])["text"]
  (nếu token là SPACE thì "")}; ngược lại None. Không bao giờ đưa preview vào `text`.
- Token lạ → `ValueError` (từ compose). Không sửa/đoán chữ; không viết luật dấu mới (mọi chữ có dấu chỉ ra từ `compose`).
`Level1Speller` thêm property `view` = `textbox_view(self.tokens, self.rejected)` (không đổi logic token hiện có).

#### 3.B.2 Vẽ (trong `level1_demo.py`, tách khỏi lõi)
`Hud` nhận `view` (dict trên) thay cho dòng "Văn bản:"; vẽ bằng PIL trên panel DƯỚI ảnh camera (giữ: không che tay):
- `committed` màu thường; `active` có nền tô sáng (hình chữ nhật sau đúng phần chữ, đo bằng `font.getlength`/`getbbox`); con trỏ = vạch
  dọc ngay sau `active` (không nhấp nháy — tránh vẽ lại PIL mỗi khung); `preview.active_if_accepted` vẽ MỜ sau con trỏ kèm
  "(a: nhận, <confidence>)"; `tone_changes` cuối → dòng nhỏ "đổi dấu: sắc → huyền"; `warnings` → dòng "Cảnh báo".
- Văn bản dài hơn panel: bỏ bớt ÂM TIẾT ĐÃ CỐ ĐỊNH ở đầu (thêm "…") cho tới khi con trỏ nằm trong panel; âm tiết đang gõ luôn hiện đủ.
- Cache panel theo (width, view, các dòng nhỏ) như hiện có; dòng số đo vẫn cv2.putText.
- Font: giữ cơ chế `find_font` (font tiếng Việt; không thấy → dừng có thông báo).
- Màu/kích thước là giá trị vẽ gõ trong mã hiển thị (không phải số đo; không đặt tên biến chứa token ms/fps/latency để không chạm luật D).

#### 3.B.3 Phím
- Giữ: Backspace (xóa token cuối — văn bản cập nhật theo compose: xóa dấu thay thế thì dấu trước có hiệu lực lại; xóa SPACE thì âm tiết
  trước thành âm tiết đang gõ), Space, `a`, `r`, `c`, `p`, `q`/Esc.
- THÊM `1`–`5` (VNI): `1` dấu sắc, `2` dấu huyền, `3` dấu hỏi, `4` dấu ngã, `5` dấu nặng → `Level1Speller.key("tone_1".."tone_5")`
  thêm token dấu với `source: "key"`, ghi `key` trong nhật ký sự kiện. Dòng hướng dẫn HUD cập nhật.
- Không thêm: copy/lưu file, TTS, web (quyết định 17:20).

## 3b. Phạm vi file (máy đọc được — hook git của agy chặn commit ngoài danh sách này)
_Thêm bởi orchestrator 2026-10-03 từ danh sách file CÓ SẴN trong §2.5 và §4; không đổi thiết kế/tiêu chí. Planner có thể chỉnh ở lần sửa sau._
Độ khó: L; vùng nhạy cảm: có (bộ tách đoạn, tiền xử lý dùng chung train–realtime) → coder dùng opus/high cho A1–A3, gemini/high cho T1–T2, C1.
```scope
src/inference/level1_textbox.py
src/inference/level1_core.py
src/inference/level1_segmenter.py
level1_demo.py
configs/level1_realtime.json
scripts/level1_segment_report.py
scripts/level1_replay_clips.py
tests/test_level1_*.py
docs/level1_desktop.md
docs/progress_log.md
reports/level1_realtime_*
```

## 4. Chia việc (mỗi bước 1 commit `15: <mã> …`; bước sinh JSON có thêm 1 commit báo cáo, sinh tại commit code sạch)

Quy ước giữ nguyên §4 gốc: lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`; file tạm `_work/_plan15/`; `git commit -- <đường dẫn
cụ thể>`; trước sửa symbol có sẵn chạy `node .gitnexus/run.cjs impact "<symbol>" --direction upstream --repo .` (ghi vào 15-progress; CRITICAL
do trùng tên → kiểm bằng text search như B5); trước commit `detect-changes --scope all`; test đỏ trước; AC-G + AC1-ngắn trước mỗi commit.

Thứ tự XEN KẼ (T = khung text, A = dấu thanh, C = đóng), ưu tiên cái giúp demo nhất trước:

| # | Bước | Nội dung | Phụ thuộc | Giờ |
|---|---|---|---|---|
| 1 | **T1** | `src/inference/level1_textbox.py` + `tests/test_level1_textbox.py` (AC-TB1…TB8, viết trước, đỏ) + `Level1Speller.view` + phím `tone_1..5` trong `Level1Speller.key`/`KEY_NAMES` + test AC-K; thêm file vào `tests/test_level1_guard.py`. | B5 | 1,5 |
| 2 | **A1** | `scripts/level1_segment_report.py` (§3.A.3: bằng chứng nested theo lớp + variants, hồ sơ chuyển động clip train, quy tắc 1–6, `--u1-json` tổng hợp) + `tests/test_level1_segment_report.py` (AC-R'1 a–c). Chạy tại commit sạch → `reports/level1_realtime_<D>/tone_evidence.json` (commit riêng). Quy tắc 6 kích hoạt → DỪNG. | B5 | 2 |
| 3 | **T2** | Vẽ khung text trong `Hud` (§3.B.2) + map phím `1`–`5` trong `KEY_ACTIONS` + dòng hướng dẫn + test không GUI (AC-TD1…TD7). Sau T2 orchestrator báo người dùng có thể thử (U1b). | T1 | 1,5 |
| 4 | **A2** | `tail_still_keep_ms` trong bộ tách + `SEGMENTER_KEYS` + `validate_level1_config` + khóa trong config (thiết kế = hold_ms) + test AC-S14/S15, AC-C8b, AC-R'1 d; rồi `--write-config` → commit config hiệu chỉnh riêng, ghi giá trị cũ → mới vào 15-progress. Sửa DUY NHẤT được phép ở test cũ của 15: thêm khóa `tail_still_keep_ms` = `hold_ms` vào config test (không đổi assertion nào). | A1 | 1 |
| 5 | **A3** | `--segment-check` trong script A1 + test; chạy TRƯỚC/SAU tại commit sạch → `segment_check_before.json`, `segment_check_after.json`; áp quy tắc giữ §3.A.4 (kết luận + 4 tỉ lệ đọc từ JSON vào 15-progress); chạy lại AC-S/AC-C/AC-E1. | A2 | 1 |
| 6 | **C1** | `docs/level1_desktop.md` NGẮN (cách chạy, phím gồm `1`–`5`, khung text, Giới hạn §6.3 gốc + §6.2 dưới, link JSON; không gõ số đo) + `--summary` → `reports/level1_realtime_<D>/SUMMARY.md` (bảng sinh tự động từ tone_evidence/segment_check/webcam JSON nếu có) + AC1-đủ cuối + 1 dòng progress_log. | A3, T2 | 1 |
| 7 | **A4** (tùy chọn) | `--segment-check-paced`: chạy app `--pace realtime --headless` trên video 120 clip dấu → `segment_check_paced.json` (báo cáo, không chọn tham số). | A3 | 0,75 (+ máy chạy) |
| 8 | **C2** | Sau U2/U2b: commit JSON webcam, chạy lại `--summary`. Không chỉnh tham số theo các phiên này. | C1, U2 | 0,5 |

Tổng ≈ 9,25 giờ công (bắt buộc 1–6 ≈ 8 giờ). Bản demo có khung text + phím dấu sau bước 3 (≈ 5 giờ).
**Thứ tự cắt nếu thiếu ngân sách** (cắt trước → sau): A4 → C2 (JSON webcam vẫn nằm trong reports/, chưa tóm tắt) → phần `--summary` của C1
(giữ tài liệu ngắn + Giới hạn) → A3 + A2 (khi đó KHÔNG `--write-config`, config giữ `design`, Giới hạn ghi "chưa hiệu chỉnh"). KHÔNG cắt:
T1, T2 (tính năng người dùng chọn), A1 (nguồn JSON cho số dấu thanh trong báo cáo).
Review: vslt-reviewer một lần sau C1 (toàn bộ 15 + phụ lục) nếu ngân sách cho phép; tối thiểu reviewer chạy AC-TB/TD/K, AC-R', AC-G, AC-E1.

## 5. Tiêu chí chấp nhận (hợp đồng; coder KHÔNG đổi; chỉ planner đổi kèm lý do)

GIỮ từ file gốc: AC0 (mở rộng danh sách file theo §0; sha256 checkpoint không đổi; `backend/main.py`, `realtime_demo.py`, `README.md`,
`tests/test_backend_source_guard.py`, `src/inference/fingerspelling_compose.py`, `src/data/alphabet_preprocessing.py`, `hand_live.py` không đổi;
không commit `_work/_plan15_u1/*`), AC1 (AC1-ngắn = 16 module của B5 + `tests.test_level1_textbox tests.test_level1_segment_report`),
AC-S S1–S13, AC-C C1–C8, AC-D, AC-E1 (BẰNG HỆT — chạy lại sau A2), AC-E3, AC-G (G2 thêm `level1_textbox.py`), AC-T, AC-L.

**AC-TB — lõi khung text** (`tests/test_level1_textbox.py`; không GUI):
- TB1 bất biến: bảng cố định + 2000 chuỗi token ngẫu nhiên (`random.Random(0)`, độ dài 0–12, lấy từ LETTERS + 5 dấu + SPACE) →
  `committed + active == text == compose(tokens)["text"]`, `cursor == len(text)`.
- TB2 ["b","a","dấu sắc"] → active "bá"; thêm "dấu huyền" → active "bà", `active_tone == "dấu huyền"`, `tone_changes == [{"from":
  "dấu sắc", "to": "dấu huyền"}]`, `warnings == []`; Backspace (qua `Level1Speller.key("backspace")`) → active "bá", `tone_changes == []`.
- TB3 ["m","e","dấu nặng"," ","c","a"] → committed "mẹ ", active "ca"; thêm "dấu sắc" → text "mẹ cá".
- TB4 token cuối là SPACE → active "", committed == text; Backspace → âm tiết trước thành active.
- TB5 preview: rejected {prediction "dấu huyền", confidence 0.4} trên ["c","a","dấu sắc"] → preview.active_if_accepted "cà", `text` vẫn
  "cá"; rejected None hoặc prediction None → preview None.
- TB6 ["b","dấu sắc"] → `warnings` có `tone_without_vowel`; `multiple_tones` ở âm tiết đã cố định không có trong `warnings`/`tone_changes`.
- TB7 token lạ → ValueError.
- TB8 thuần: AST của `level1_textbox.py` không import cv2/PIL/torch/threading; chỉ import stdlib + `src.inference.fingerspelling_compose`.
**AC-K — phím dấu:** `key("tone_1".."tone_5")` thêm đúng dấu sắc/huyền/hỏi/ngã/nặng theo thứ tự, sự kiện `source == "key"`, `key` ghi tên;
tên phím lạ → ValueError (giữ); C6 (`text == compose(tokens)["text"]`) vẫn đúng sau mọi chuỗi phím.
**AC-TD — vẽ (không GUI, ảnh offscreen; font tìm như app; không thấy font → test FAIL, không skip — §7 gốc mục 5):**
- TD1 phần ảnh camera của ảnh ghép == ảnh vào (`array_equal`) — không che tay.
- TD2 có pixel màu tô sáng trong hộp bao phần `active`; không có trong hộp bao phần `committed`.
- TD3 cột con trỏ (x tính bằng `font.getlength` của phần chữ hiển thị trước con trỏ) có pixel màu con trỏ.
- TD4 có preview → có pixel màu mờ bên phải con trỏ; không preview → không có.
- TD5 văn bản dài (vd 40 âm tiết) → con trỏ nằm trong panel; âm tiết đang gõ hiện đủ; có "…".
- TD6 cùng view hai lần → panel không dựng lại (cache); view đổi → dựng lại.
- TD7 mã phím `ord("1")`…`ord("5")` qua `Level1App._key` → token dấu tương ứng trong speller (app tạo như các test D hiện có, không webcam).
**AC-S bổ sung:** S14 `tail_still_keep_ms == hold_ms` → segment `array_equal` với hành vi hiện tại trên các ca S1/S3; S15
`tail_still_keep_ms < hold_ms` → khung cuối của segment `hold` có ts ≤ `_still_since + tail_still_keep_ms`, t_emit không đổi.
**AC-C8b:** config thiếu `tail_still_keep_ms`, ≤ 0 hoặc > hold_ms → ValueError; `configs/level1_realtime.json` thật nạp được.
**AC-R' — báo cáo (thay AC-R gốc):**
- R'1 (test, `tests/test_level1_segment_report.py`): (a) đếm theo lớp từ `nested_predictions.csv` tính lại top-1 dấu thanh theo fold ==
  `runs.frame.folds[i].tones.top1` của primary `nested_report.json` (sai số ≤ 1e-9) và trung bình 4 fold == `summary.tones.mean`;
  (b) hồ sơ chuyển động trên 2 npz cố định dùng đúng chuỗi `segmenter.motion` lấy từ push từng khung; (c) quy tắc 1–6 tính đúng trên dãy
  số cho trước trong test (kể cả nhánh "no_motion" và quy tắc 6 kích hoạt); (d) `--write-config` chỉ đổi 5 khóa, `source` đúng mẫu.
- R'2 `tone_evidence.json` có: `nested_per_class` (5 dấu: n, correct, top1, predicted_as{nhãn: số}, theo fold và tổng), `variants_summary`
  (4 biến thể: tones/letters mean, sd, đọc từ variants JSON, kèm đường dẫn + sha256), `train_profiles` (phủ MỌI clip hauuto trong manifest có
  ≥ `min_detected_frames` khung có tay — số clip in từ lần chạy; thống kê theo chữ cái / dấu thanh / từng dấu), `calibration` (giá trị +
  đầu vào quy tắc 1–6), `u1` (nếu có `--u1-json`: chỉ số tổng hợp — số segment, phân bố frames/duration, close_reason, dự đoán theo loại,
  tỉ lệ accepted, số segment chạm trần; sha256 file nguồn; KHÔNG chép file), `note` "train data / out-of-fold predictions; not webcam
  accuracy", `generated_by.git_commit` + `code_dirty == false`.
- R'3 `segment_check_before.json`, `segment_check_after.json` (+ `segment_check_paced.json` nếu làm A4) có khóa §3.A.4, config sha256,
  cùng tập clip; kết luận quy tắc giữ ghi trong 15-progress kèm 4 tỉ lệ đọc từ JSON.
- R'4 `SUMMARY.md` sinh lại bằng `--summary` giống hệt byte; `docs/level1_desktop.md` không có chuỗi khớp `\d+(\.\d+)?\s*(ms|%|fps)`
  (giữ R3 gốc).

Lệnh kiểm chính:
- `python -m unittest tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core
  tests.test_level1_demo tests.test_level1_guard -v` → OK, 0 skip.
- AC1-ngắn (16 module của B5 + 2 module mới) → mọi test có ở B5 cùng trạng thái (test chập chờn đã biết xử lý như §5 AC1 gốc).
- `python -m unittest tests.test_level1_equivalence -v` OK sau A2 (E1 bằng hệt).
- G1 `python -m unittest tests.test_backend_source_guard -v` → OK, "known=9 allowed=36" như B5.
- Sinh JSON (commit sạch): `python scripts/level1_segment_report.py --out reports/level1_realtime_<D>/tone_evidence.json --u1-json
  _work/_plan15_u1/u1_2026-10-03_1650.json`; `... --write-config configs/level1_realtime.json`; `git show 3ebc7b9:configs/level1_realtime.json
  > _work/_plan15/config_before.json`; `... --segment-check --config _work/_plan15/config_before.json --label before --out
  reports/level1_realtime_<D>/segment_check_before.json` (tương tự `--label after` với config thật). Tên cờ chính xác coder chốt và ghi vào
  15-progress; nội dung JSON theo R'2/R'3.

## 6. Rủi ro dữ liệu/ML + Giới hạn

### 6.1 Rủi ro
- **Dấu thanh là giới hạn model:** offline 40.83% (sd 20.97, ci95 rộng; n = 6 clip/dấu/người) — sửa tách đoạn không nâng quá mức này;
  báo cáo phải nói rõ. Không trình bày phím `1`–`5` như nhận dạng.
- **Hiệu chỉnh trên dữ liệu train:** checkpoint triển khai đã train trên cả 4 người ⇒ `window_agreement` trên clip train lạc quan; chỉ
  dùng để so TRƯỚC/SAU cùng điều kiện, không phải độ chính xác. Số dấu thanh cho báo cáo lấy từ out-of-fold (`nested_predictions.csv`).
- **Rò rỉ khi chọn tham số:** chỉ hauuto train; không dùng 2 clip qipedc test, không dùng phiên U1/U2/U2b để chỉnh. U1 chỉ là chỉ số
  tổng hợp mô tả.
- **Lệch train–realtime còn lại:** live segment bắt đầu ở đầu chuyển động (clip train có thể có đoạn giữ yên đầu — A1 đo
  `leading_still_ms`, không bù vì khung trước đó là chữ trước); bỏ khung khi xử lý chậm (U1: processing_fps 24.92 so với capture 30.47)
  làm khung không cách đều khi `resample: frame_index` — A4 đo, không sửa (sửa = đổi tiền xử lý = phá E1).
- **Tracker liên tục** (E2 cũ) không đo trong 15 nữa → ghi Giới hạn.
- **Cỡ mẫu:** 24 clip/dấu out-of-fold; tỉ lệ theo lớp có sai số lớn — báo kèm n.
- **Nguồn gốc:** hauuto licence unknown, internal only; JSON U1 là dữ liệu phiên của người dùng (không có ảnh/landmark) — chỉ commit
  chỉ số tổng hợp + sha256, file gốc ở `_work/`.

### 6.2 Giới hạn bổ sung (đưa vào `docs/level1_desktop.md`, sau §6.3 gốc)
7. Dấu thanh: top-1 offline thấp hơn nhiều so với chữ cái; theo lớp và theo người ký trong `tone_evidence.json` (nguồn out-of-fold). Biến thể
   có quỹ đạo cổ tay đã thử cùng giao thức, không tốt hơn (`reports/alphabet_nested_2026-09-25/variants/nested_report.json`).
8. Phím `1`–`5` cho phép người dùng gõ dấu khi model nhận sai; token này có `source: "key"` trong JSON; không tính là nhận dạng.
9. Tham số tách hiệu chỉnh trên clip train (quy tắc đặt trước); không đo tracker liên tục qua nhiều ký hiệu; độ chính xác webcam chỉ có
   nếu có phiên `--expected` (U2/U2b), một người, vài từ — không phải đánh giá.

### 6.3 Việc người dùng (không chặn)
- **U1b (sau T2, ~5 phút):** `.venv\Scripts\python level1_demo.py --source 0 --display-mirror`; ký "ba" rồi dấu sắc, rồi dấu huyền
  (hoặc nhấn `1` rồi `2`) → xem chữ đổi bá → bà; thử Backspace; nhận xét khung text (dễ đọc, có che tay không). Báo bằng lời.
- **U2 (giữ, sau A3):** như §6.4 gốc (ba/cá/mẹ/xoong × 3, `--expected`, `--out-json reports/level1_realtime_<D>/webcam_<từ>_<n>.json`),
  CHỈ khi code sạch. Không dùng phím `1`–`5` trong U2 (để số đo là của model; nếu lỡ dùng, JSON vẫn ghi `source: "key"`).
- **U2b (tùy chọn, ~5 phút, sau A3):** thử dấu riêng bằng 5 từ một âm tiết "bá", "bà", "bả", "bã", "bạ", mỗi từ 2 lần:
  `--expected "bá" --out-json reports/level1_realtime_<D>/webcam_tone_s_<n>.json` (tương tự f/r/x/j). Không dùng phím `1`–`5`.
  Thử nghiệm một người, không phải đánh giá.

## 7. Điểm dừng

Không có điểm dừng bắt buộc khi BẮT ĐẦU: không đổi model mặc định (A(b) không làm; checkpoint giữ nguyên, AC0), không cần dữ liệu người dùng
để làm (U1b/U2/U2b không chặn), không đụng thay đổi chưa commit của người dùng (README.md và 3 file ` D` — dùng `git commit -- <file>`),
không hành động không hoàn tác, không xóa file, không train, không dùng GPU Kaggle.

Điểm dừng có điều kiện (coder dừng, ghi 15-progress, báo orchestrator → planner):
1. Quy tắc 6 §3.A.3 kích hoạt (nét dấu có đoạn đứng yên giữa chừng ≥ hold_ms ở ≥ 10% clip dấu).
2. Quy tắc giữ config §3.A.4 không đạt, hoặc AC-R1 gốc (đúng-1-segment < 0,9, chữ cái hoặc dấu thanh) với config SAU.
3. R'1(a) không khớp (CSV out-of-fold không khớp nested_report.json) — nghi vấn nguồn gốc số → báo người dùng theo autopilot §5.
4. AC-E1 không còn bằng hệt sau A2; test cũ đổi trạng thái so với B5 (trừ test chập chờn đã biết `test_reset_segments_and_graphs`).
5. Cần sửa file ngoài danh sách §0/§3.1 gốc (vd `fingerspelling_compose.py` để lấy vị trí âm tiết) — KHÔNG sửa; lõi khung text phải dựng
   từ `compose()` gọi trên từng phần token.
6. Người dùng (không phải agent) muốn train lại model dấu → kế hoạch riêng có GATE, CẦN NGƯỜI DÙNG (ngoài phụ lục này).
