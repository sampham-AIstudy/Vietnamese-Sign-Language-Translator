# Kế hoạch 08 — Segmenter live (backlog 2b)

**ĐANG LÀM** (planner đang viết; các mục chưa điền coi như chưa có)

- Nhánh lập kế hoạch: `cloud/2026-09-29-viec-a-d` (cloud). Ngày: 2026-09-29.
- Nguồn: `docs/STATE.md` "Backlog còn lại" mục 2b; `docs/reviews/04-review.md` mục S3.5, S4, "Thiết kế (planner)" 8–9;
  `docs/plans/06-viec5-frontend.md` §3.8 (vì sao tách khỏi Việc 5).
- Quyết định người dùng liên quan (không hỏi lại): "Cắt đoạn nghỉ: giữ ở realtime, tham số lấy từ checkpoint; chế độ Ký từ
  gom trọn một ký hiệu rồi mới dự đoán." Model mặc định KHÔNG đổi (GATE riêng).

## 1. Mục tiêu và DoD

**Mục tiêu.**
1. (Review 04 mục 8) Trong `SignSegmenter`, tốc độ cổ tay của frame mới nhất được tính theo khoảng thời gian THẬT giữa
   frame đó và frame liền trước (`dt` từng frame), thay vì `fps` trung bình của cửa sổ `activity_window_s`. Khi frame cách
   đều, kết quả (hoạt động từng frame + sự kiện) phải GIỐNG HỆT cách cũ.
2. (Review 04 mục 9) Có chính sách được đăng ký trước cho ký hiệu có nhịp nghỉ giữa chừng (loại `qipedc_W03251B`: một ký
   hiệu bị cắt thành 2 đoạn và phát 2 `sign_result` cùng gloss), với ngưỡng chọn trên TRAIN, kiểm trên VAL, không chạm
   TEST; hoặc — nếu bằng chứng TRAIN/VAL không ủng hộ đổi hành vi — ghi Giới hạn trung thực.

**DoD phục vụ.**
- DoD 3 (Ký từ qua `/ws/live-stream`, đường `harmonized_v1` ứng viên) và DoD 6 (không có kết quả giả: không phát trùng
  gloss do lỗi cắt đoạn mà người dùng tưởng là hai từ).
- DoD 7 (test tương đương train↔realtime: mọi thay đổi ở bước tiền xử lý live phải có test tương đương — ở đây là
  tương đương với luật `hand_activity` lúc train và với segmenter cũ khi fps đều).
- DoD 9 (mục "Giới hạn" trung thực: ghi rõ phần chính sách còn lại chưa giải được).
- Gián tiếp: GATE đổi model mặc định Cấp 2 (backlog 5) sẽ dùng đường này; việc này KHÔNG đổi model mặc định.

## 2. Hiện trạng (HEAD của nhánh cloud khi lập: sau 34a527d)

### 2.1 Segmenter live tính tốc độ thế nào
- `src/inference/sign_segmenter.py`
  - `:34-43` `SEGMENTER_DEFAULT` (chỉ dùng cho live, KHÔNG có trong checkpoint): `onset_min_s 0.10`, `pre_roll_s 0.50`,
    `rest_hold_s 0.50`, `min_sign_s 0.30`, `max_sign_s 8.0`, `stream_gap_s 1.0`, `activity_window_s 1.0`,
    `max_buffer_frames 1024`. Docstring `:14-15` ghi rõ: giá trị thiết kế, CHƯA đo; chỉ chỉnh trên TRAIN/webcam người
    dùng, không bao giờ trên TEST.
  - `:44` `CHECKPOINT_KEYS = (rest_y, active_speed, pad_s, max_gap_s, mask_resting_hand)` — bắt buộc lấy từ
    `ckpt["preprocessing"]`, không có mặc định (`_check_params` `:71-103`). Ràng buộc `:97-102`: `pre_roll_s ≥ pad_s`,
    `rest_hold_s ≥ pad_s`, `rest_hold_s > max_gap_s`. Mọi tham số phải là số hữu hạn ≥ 0 (`:83-85`).
  - `:136-144` `_activity(aspect)`: lấy toàn bộ cửa sổ `_hist` (các frame trong `activity_window_s` gần nhất, `:208-212`),
    `fps = (n-1)/(t_cuối - t_đầu)` (fps TRUNG BÌNH của cửa sổ; `n == 1` → 30.0, lúc đó tốc độ luôn 0), rồi
    `hand_activity(_normalise(cửa sổ), fps, cfg)` và chỉ dùng phần tử CUỐI (`left[-1] or right[-1]`).
  - Phần tử cuối của `hand_activity` chỉ phụ thuộc cặp frame cuối: `speed[-1] = ‖wrist_n − wrist_{n-1}‖ · fps` khi cổ tay
    có mặt ở CẢ hai frame, ngược lại 0 (`src/data/harmonized.py:68-77`). Vậy lỗi nằm ở chỗ nhân với `fps` trung bình
    thay vì chia cho `dt` thật của cặp đó.
  - Thời gian: `validate_time` `:174-181` đòi `t_s` hữu hạn và TĂNG NGẶT, sai → `ValueError`, không đổi trạng thái (AC1-h
    kế hoạch 04). Khoảng trống `t − t_trước > stream_gap_s` → `Discard(stream_gap)` khi đang ghi và xóa cửa sổ + bộ đệm
    (`:196-205`).
  - Máy trạng thái `:217-272`: đoạn đóng khi không hoạt động liên tục `≥ rest_hold_s` (`:250`); `too_short` nếu
    `active_end − onset < min_sign_s` (`:251-252`); phần đuôi nghỉ giữ lại làm tiền cuộn cho ký hiệu sau (`:255-260`).
- `src/inference/harmonized_live.py`
  - `:94` `SignSegmenter(preprocessing, segmenter_cfg)` — `preprocessing` là dict của checkpoint; `segmenter_cfg`
    mặc định `SEGMENTER_DEFAULT` (`:87`).
  - `:108-115` `_harmonize_buffer`: `harmonize(kps, vis, W/H, fps=(n-1)/(t_n-t_1), cfg=preprocessing, timestamps_s=t-t0)`.
    `harmonize` resample theo THỜI GIAN, nhưng `active_span` / `mask_resting_hand` bên trong nó vẫn dùng `fps` trung bình
    của đoạn (hàm train, KHÔNG sửa trong việc này — xem §6).
  - `:139-146` `sign_result.segment` ghi `effective_fps`, `dropped_frames`, `active_start_s`, `active_end_s`.
- `backend/main.py` (chỉ đọc)
  - `:1183-1185` `_new_harmonized_session`: `HarmonizedLiveSession(predictor, predictor.preprocessing)` → segmenter
    dùng `SEGMENTER_DEFAULT` (import `:104`).
  - `:1302-1331` `_SessionClock`: nguồn giờ chốt ở frame đầu tiên: `"client"` = `timestamp` (ms) client gửi, tăng ngặt;
    `"server"` = `time.perf_counter()` lúc NHẬN (nếu không tăng thì cộng 1e-6 s). `t_s` đưa vào segmenter = giờ này
    trừ giờ frame đầu.
  - `:1232-1234` worker truyền `seq = dropped_frames + frame_seq + 1` (đếm frame bị ghi đè trong slot).
  - `:1296` `session_info.segmenter = dict(SEGMENTER_DEFAULT)`; `:1263` `frame_result.segment.max_sign_s`;
    `:1210` `sign_result.metrics.rest_hold_s`.
- Frontend (chỉ đọc, thuộc kế hoạch 06): `frontend/src/components/CameraCapture.jsx:114` `drawImage` (lúc chụp),
  `:126` `toDataURL` (mã hóa JPEG), `:127` `timestamp: nowMs()` — tức timestamp là lúc GỬI, SAU khi mã hóa JPEG, không
  phải lúc chụp. `nowMs()` = `performance.timeOrigin + performance.now()` (`frontend/src/lib/ws.js:16-17`), đơn điệu.
  `targetFps = 25` (`CameraCapture.jsx:17`). `frontend/src/lib/liveProtocol.js:10` hiện MỌI `sign_result` (không khử
  trùng), đúng quyết định 06 §3.8.

### 2.2 Lúc train cắt đoạn nghỉ tính tốc độ thế nào (để so tính nhất quán)
- `HarmonizedDataset.__getitem__` (`src/data/harmonized.py:170-180`): `fps` = `metadata.fps` của npz (CAP_PROP_FPS lúc
  trích; mặc định 30), `timestamps_s=None` → `t = arange(T)/fps` (frame CÁCH ĐỀU, mọi frame giải mã được).
- `harmonize` (`:118-153`) → `active_span(k, v, fps, cfg)` (`:80-88`) → `hand_activity` (`:68-77`):
  `speed = ‖Δwrist‖ · fps` giữa HAI FRAME LIỀN KỀ có cổ tay → tức là `‖Δwrist‖ / dt` với `dt = 1/fps` của video.
  Hoạt động = có tay và (`y < rest_y` hoặc `speed > active_speed`). `pad = round(pad_s·fps)` frame.
- Kết luận: luật train = tốc độ theo dt của từng cặp frame liền kề, ở đó mọi dt bằng nhau. Segmenter live hiện nhân với
  fps trung bình cửa sổ — trùng với luật train khi frame đều, lệch khi rơi frame (review 04 S3.5: mẫu giữ1-bỏ1/giữ1-bỏ2
  phóng đại tốc độ tới ~1.2× ở khe 3 frame; tay nghỉ đung đưa 0.94 sw/s làm mất `Emit`). Tính theo dt thật của cặp cuối
  là cách tổng quát hóa ĐÚNG luật train cho frame không đều.
- `scripts/trim_rest_eval.py` KHÔNG phải luật train (là chẩn đoán bước 4a, luật riêng theo thân người, `PAD = 3`
  frame); không dùng trong việc này.
- Tham số lấy từ checkpoint: `rest_y`, `active_speed`, `pad_s`, `max_gap_s`, `mask_resting_hand` (bằng
  `HARMONIZED_DEFAULT` `:28-42` khi train H-keepz-360, ghi trong `ckpt["preprocessing"]`, `scripts/train_unified.py:176-181`,
  `:211`). Việc này KHÔNG đổi nhóm tham số này và KHÔNG đổi `src/data/harmonized.py` (test `TestAC7aUnchangedFiles`
  trong `tests/test_ws_live_contract.py:511-` khóa file này).

### 2.3 Bằng chứng về ký hiệu có nhịp nghỉ (W03251B)
- `reports/live_word_2026-09-28/segment_check.json` (lệnh + commit `b1d447a`, `code_dirty=false`, sinh bởi
  `scripts/live_segment_check.py --n-clips 8 --seed 0`): `qipedc_W03251B` 257 frame, 29.97 fps, 1280×720;
  `offline_active_span_s` [0.9676, 7.0737]; 2 `sign_result` đều `thìa`: đoạn 1 `active_start_s 1.0677 → active_end_s 3.1365`,
  đoạn 2 `5.0384 → 6.9736`; `top5_overlap` 1 và 2; `abs_delta_top1_confidence` 0.4787 và 0.6391; `contains_offline_span`
  false. 7 clip còn lại mỗi clip đúng 1 `sign_result`, `n_contains_offline_span = 7` / 8.
  (Khoảng nghỉ giữa hai đoạn theo chính JSON: 5.0384 − 3.1365 ≈ 1.90 s, lớn hơn `rest_hold_s = 0.5` gần 4 lần.)
- Split của clip (planner kiểm tại thời điểm lập): `data/splits/unified/train.csv:672`
  `qipedc_W03251B,…,thìa,…,RG02924,…,train` → **TRAIN**. Cùng gloss `thìa` có `qipedc_W03251N` và `qipedc_W03251T` ở
  `data/splits/unified/test.csv:611-612` (**TEST**, nhóm RG02925) → tuyệt đối KHÔNG xem/đo hai clip này.
- n = 1: không suy ra tần suất. Review 04 mục 13(6) yêu cầu đo "tần suất trong từ điển" — chưa có số nào.

### 2.4 Test hiện có phụ thuộc hành vi segmenter (phải vẫn PASS, KHÔNG sửa)
- `tests/test_sign_segmenter.py` (AC1 a–o kế hoạch 04): fixture 30/60 fps; tham chiếu `SEGMENTER_DEFAULT["rest_hold_s"]`
  động nhưng timeline cố định — ví dụ fixture 3.5 s ký 1.0–2.5 s chỉ còn ~0.97 s nghỉ cuối (test_b, test_j), test_k
  (rơi frame) frame cuối giữ lại ở 3.4 s (~0.9 s nghỉ), test_c khoảng nghỉ giữa hai ký hiệu ~1.6 s, test_d hạ tay 1.47 s.
- `tests/test_ws_live_contract.py` (`sign_frames(dur=3.5)` `:116-119`, cùng timeline), `tests/test_harmonized_live.py`
  (`:68-69`, cùng timeline), `tests/test_ws_dropped_frames.py`; `tests/test_ws_live_contract.py:260`
  `info["segmenter"] == api.SEGMENTER_DEFAULT` (so với chính dict → thêm khóa mới vẫn PASS);
  `:497-508` (AC7-e) cấm chuỗi con `random` và số độ chính xác gõ tay trong `sign_segmenter.py`, `harmonized_live.py`,
  `live_segment_check.py`.
- `tests/test_live_harmonized_equivalence.py` AC4/AC5 (video thật, LOCAL), `TestSegmentCheckJson` (`:295-329`) đọc file
  MỚI NHẤT `reports/live_word_*/segment_check.json` (8 clip, mỗi clip ≥ 1 event, `code_dirty=false`, commit là tổ tiên HEAD).
- Hệ quả: nếu đổi `rest_hold_s` mặc định, giá trị mới phải giữ mọi test trên PASS mà không sửa fixture; trần thực tế
  khoảng < 0.9 s (xem §3.2 — trần đăng ký 0.8 s).

### 2.5 Dữ liệu (gitignored) — có ở đâu
| Dữ liệu | Cloud (clone này) | Local (Windows) | Nguồn khôi phục (`docs/CLOUD.md` §3) |
|---|---|---|---|
| `data/splits/unified/{train,val,test}.csv` | CÓ (planner đã đọc) | CÓ | — |
| Checkpoint H-keepz-360 `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt` (sha `648a7825…c9b59e`) | KHÔNG | CÓ | dataset private `phmvnsm33/vslt-step4-artifacts` (`scripts/archive_private_kaggle.py restore`) |
| Keypoint QIPEDC 360 px (`qipedc_kps360/*.npz`, đúng đầu vào train H-keepz-360) | KHÔNG | chưa rõ (coder kiểm) | output kernel `phmvnsm33/vsl-extract-qipedc360-s{0,1,2}` (`kaggle kernels output … -p <tạm>`) |
| Video QIPEDC `data/Dataset/Videos/*.mp4` | KHÔNG | CÓ | dataset `aresusayhi/vsl-vietnamese-sign-languages` (chỉ dùng nội bộ) |

## 3. Thiết kế
(đang viết)

## 4. Chia việc
(chưa điền)

## 5. Tiêu chí chấp nhận (hợp đồng)
(chưa điền)

## 6. Rủi ro dữ liệu/ML
(chưa điền)

## 7. Điểm dừng
(chưa điền)
