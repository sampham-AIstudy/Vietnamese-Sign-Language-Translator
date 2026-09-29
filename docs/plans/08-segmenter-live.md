# Kế hoạch 08 — Segmenter live (backlog 2b)

**Trạng thái: XONG (chờ orchestrator)**

**Điểm dừng:** KHÔNG cần người dùng trước khi code. Có điểm dừng CÓ ĐIỀU KIỆN (§7), trong đó một nhánh của luật D9
("keep_0.5_needs_user") sẽ thành câu hỏi CẦN NGƯỜI DÙNG sau khi có số TRAIN/VAL.

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
    `"server"` = `time.perf_counter()` lúc NHẬN (nếu không tăng thì cộng 1e-6 s, `:1325-1326`). `t_s` đưa vào segmenter =
    giờ này trừ giờ frame đầu.
  - `:1232-1234` worker truyền `seq = dropped_frames + frame_seq + 1` (đếm frame bị ghi đè trong slot).
  - `:1296` `session_info.segmenter = dict(SEGMENTER_DEFAULT)`; `:1263` `frame_result.segment.max_sign_s`;
    `:1210` `sign_result.metrics.rest_hold_s`.
- Frontend (chỉ đọc, thuộc kế hoạch 06): `frontend/src/components/CameraCapture.jsx:114` `drawImage` (lúc chụp),
  `:117` `const now = nowMs()` (cho bộ đếm fps), `:126` `toDataURL` (mã hóa JPEG), `:127` `timestamp: nowMs()` — tức
  timestamp là lúc GỬI, SAU khi mã hóa JPEG, không phải lúc chụp. `nowMs()` = `performance.timeOrigin + performance.now()`
  (`frontend/src/lib/ws.js:16-17`), đơn điệu. `targetFps = 25` (`CameraCapture.jsx:17`).
  `frontend/src/lib/liveProtocol.js:10` hiện MỌI `sign_result` (không khử trùng), đúng quyết định 06 §3.8.

### 2.2 Lúc train cắt đoạn nghỉ tính tốc độ thế nào (để so tính nhất quán)
- `HarmonizedDataset.__getitem__` (`src/data/harmonized.py:170-184`): `fps` = `metadata.fps` của npz (CAP_PROP_FPS lúc
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
  khoảng < 0.9 s (xem §3.3 — trần đăng ký 0.8 s).

### 2.5 Dữ liệu (gitignored) — có ở đâu
| Dữ liệu | Cloud (clone này) | Local (Windows) | Nguồn khôi phục (`docs/CLOUD.md` §3) |
|---|---|---|---|
| `data/splits/unified/{train,val,test}.csv` | CÓ (planner đã đọc) | CÓ | — |
| Checkpoint H-keepz-360 `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt` (sha `648a7825…c9b59e`) | KHÔNG | CÓ | dataset private `phmvnsm33/vslt-step4-artifacts` (`scripts/archive_private_kaggle.py restore`) |
| Keypoint QIPEDC 360 px (`qipedc_kps360/*.npz`, đúng đầu vào train H-keepz-360) | KHÔNG | chưa rõ (coder kiểm) | output kernel `phmvnsm33/vsl-extract-qipedc360-s{0,1,2}` (`kaggle kernels output … -p <tạm>`) |
| Video QIPEDC `data/Dataset/Videos/*.mp4` | KHÔNG | CÓ | dataset `aresusayhi/vsl-vietnamese-sign-languages` (chỉ dùng nội bộ) |

## 3. Thiết kế

### 3.1 Nguyên tắc (ràng buộc)
- KHÔNG sửa: `src/data/harmonized.py`, `src/data/landmark_extractor.py`, `scripts/train_unified.py`,
  `scripts/extract_keypoints_batch.py` (khóa bởi `TestAC7aUnchangedFiles`), `src/inference/harmonized_live.py` (không
  cần), `backend/main.py`, `frontend/**`, `docs/phase12_api.md`, `scripts/smoke_test_phase12.py`,
  `scripts/live_segment_check.py`, `docs/plans/06-*` — NGOẠI TRỪ bước B6, chỉ làm SAU khi kế hoạch 06 được APPROVE (§4).
- KHÔNG sửa/skip/nới test có sẵn. Test mới nằm ở FILE MỚI.
- Segmenter tiếp tục gọi `_normalise` và `hand_activity` của module train (tiền xử lý dùng chung, không chép công thức);
  chỉ đổi đối số `fps` truyền vào.
- Không đổi nhóm tham số checkpoint (`CHECKPOINT_KEYS`). Chỉ nhóm live `SEGMENTER_DEFAULT`: thêm `speed_min_dt_s`; có thể
  đổi `rest_hold_s` theo luật D9 (§3.3). Không đổi tham số nào khác.
- Không đổi model mặc định (`DEFAULT_MODEL_TYPE` vẫn `"stgcn"`, đường legacy).
- Không có RNG ở đâu trong việc này. Chuỗi con `random` không được xuất hiện trong `sign_segmenter.py`,
  `harmonized_live.py`, `live_segment_check.py` (AC7-e cũ) và trong script mới `scripts/segmenter_replay_eval.py`.

### 3.2 Mục 8 — tốc độ theo dt từng frame
Luồng (chỉ bước ② đổi):
```
backend _SessionClock → t_s (client ms/1000, hoặc perf_counter lúc nhận) → HarmonizedLiveSession.process
 → SignSegmenter.push(coords, vis, t_s, frame_wh, seq)
    ① validate_time: hữu hạn, tăng ngặt                                   (không đổi)
    ② _activity(aspect):
         kn, vn = _normalise(cửa sổ ≤ activity_window_s, aspect)          (không đổi)
         n ≥ 2: dt = t_n − t_{n−1};  fps_last = 1 / max(dt, speed_min_dt_s)
         n = 1: fps_last = 30.0   (tốc độ của frame đơn luôn 0 — như cũ)
         left, right = hand_activity(kn, vn, fps_last, cfg_ckpt);  return left[-1] or right[-1]
    ③ máy trạng thái                                                     (không đổi)
```
- Chỉ phần tử cuối được dùng, và nó chỉ phụ thuộc cặp (n−1, n) → đúng bằng `‖Δwrist‖/dt` của cặp cuối (cổ tay phải có
  mặt ở cả hai frame, như luật train). Các phần tử khác của mảng tính với fps không đúng nghĩa và bị bỏ — docstring
  `_activity` phải nói rõ để không ai dùng lại mảng đó. Docstring module (`:7-9`, "fps_window is its mean frame rate")
  sửa cho đúng.
- **`speed_min_dt_s = 0.010`** (tham số live MỚI trong `SEGMENTER_DEFAULT`): HẰNG THIẾT KẾ đăng ký trước, KHÔNG chỉnh theo
  dữ liệu. Mục đích: chặn tốc độ "nổ" khi hai frame gần như cùng thời điểm (server cộng 1e-6 s ở `backend/main.py:1325-1326`;
  client có thể gửi dồn khi timer bị trễ). 10 ms nhỏ hơn khoảng frame của mọi luồng ≤ 100 fps → với luồng đều ≤ 100 fps
  (gồm 25/30/60 fps trong test và 29.97 fps của QIPEDC) nó KHÔNG BAO GIỜ kích hoạt, nên tính tương đương giữ nguyên.
  Kiểm tham số: số hữu hạn ≥ 0 (vòng kiểm sẵn có `:83-85`) và thêm `speed_min_dt_s < stream_gap_s` → sai là `ValueError`.
- **Nguồn timestamp:** segmenter dùng `t_s` người gọi đưa, không tự lấy giờ. Ý nghĩa đúng nhất = thời điểm CHỤP frame.
  Hiện trạng: client đóng dấu lúc GỬI sau `toDataURL` (§2.1) → dt mang nhiễu thời gian mã hóa JPEG; nguồn `"server"`
  mang nhiễu mạng/hàng đợi. Việc này KHÔNG sửa backend. Bước B6 (sau khi 06 APPROVE) đổi client gửi `timestamp: now` với
  `now = nowMs()` đã lấy ngay sau `drawImage` (`CameraCapture.jsx:117`), trước `toDataURL`.
- **Frame rơi:** dt = khe thật → tốc độ = tốc độ trung bình trên khe (đúng với chuyển động đều; hết phóng đại 1.2×).
- **Khoảng trống:** `dt > stream_gap_s` → `Discard(stream_gap)` + xóa cửa sổ như cũ; `speed_min_dt_s ≤ dt ≤ stream_gap_s`
  → tốc độ trung bình trên khe (luật vị trí `y < rest_y` vẫn bắt được tay đang giơ).
- **Timestamp không đơn điệu / NaN:** `ValueError` như cũ (backend trả `bad_timestamp`), không đổi trạng thái — AC1-h cũ
  vẫn phủ.
- **Tương đương khi fps đều:** về toán `1/dt == (n−1)/(t_n − t_1)`; dấu phẩy động có thể lệch cỡ 1e-15 tương đối, boolean
  chỉ có thể đổi nếu tốc độ nằm sát `active_speed` trong cỡ đó. Hợp đồng (AC-D1, AC-D2 ở §5): dãy hoạt động từng frame + danh
  sách sự kiện GIỐNG HỆT trên mọi fixture và mọi clip TRAIN/VAL phát lại đều; một khác biệt bất kỳ → DỪNG, báo planner,
  không nới.
- **Cài đặt tham chiếu (chỉ cho test/đánh giá):** lớp `WindowMeanFpsSegmenter(SignSegmenter)` ghi đè `_activity` bằng
  NGUYÊN VĂN thân `sign_segmenter.py:136-144` tại commit gốc P8 của B0 (hash ghi trong docstring). Định nghĩa MỘT lần
  trong `scripts/segmenter_replay_eval.py`; test import từ đó (giống cách `scripts/live_clip_sample.py` được dùng chung).
  Vì vậy `_activity(self, aspect) -> bool` phải GIỮ tên và chữ ký (điểm ghi đè). Script chỉ import numpy + stdlib +
  `src.inference.sign_segmenter` ở mức module; torch/đọc CSV/npz nằm trong hàm (test fixture không cần torch).
- **Không đổi:** `_harmonize_buffer` (fps trung bình đoạn cho `harmonize`) — rủi ro còn lại ở §6.

### 3.3 Mục 9 — chính sách ký hiệu có nhịp nghỉ

| # | Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|---|
| P0 | Không đổi hành vi; ghi Giới hạn | Không rủi ro, không thêm độ trễ | Lặp từ vẫn xảy ra; mỗi nửa ký hiệu cho phân phối xa đường train (W03251B `|Δconf|` 0.48/0.64) | Nhánh mặc định nếu TRAIN không ủng hộ đổi |
| P1 | Tăng `rest_hold_s` (đóng đoạn cần nghỉ lâu hơn), chọn trên TRAIN theo luật D9, trần 0.8 s | 1 tham số có sẵn; không đổi hợp đồng WS/UI; nhịp nghỉ < `rest_hold_s` nằm TRONG đoạn nên đầu vào model giống clip train (`harmonize` chỉ cắt nghỉ đầu/cuối); đúng quyết định "gom trọn rồi mới dự đoán" | Mọi ký hiệu phát chậm thêm (r − 0.5) s; người dùng phải nghỉ ≥ r giữa hai từ; không cứu nhịp nghỉ > trần (W03251B ~1.9 s) | **CHỌN**, kèm P0 cho phần còn lại |
| P2 | Gộp hai đoạn nếu khoảng nghỉ < `merge_gap_s` (giữ đoạn chờ đoạn tiếp) | — | Muốn gộp mà không phát sớm thì phải chờ `merge_gap_s` sau MỖI ký hiệu → tương đương P1 với `rest_hold_s = merge_gap_s`, thêm trạng thái mới | Loại (trùng P1, phức tạp hơn) |
| P3 | Phát ngay; nếu đoạn kế bắt đầu trong `merge_gap_s` VÀ cùng top-1 thì dự đoán lại trên hợp hai đoạn, gửi `sign_result` có `replaces_segment_id` (UI thay từ cuối) | Không thêm độ trễ; xử lý được nhịp nghỉ dài | Dự đoán trên nửa ký hiệu trước (trái tinh thần "gom trọn"); đổi hợp đồng WS + reducer frontend (của 06) + tài liệu; nuốt lặp thật cùng từ; bằng chứng n = 1 | Không làm ở đây; thành câu hỏi người dùng nếu D9 rơi vào nhánh B |
| P4 | Khử lặp nhãn liền kề trong một khoảng thời gian (server hoặc UI) | Rẻ | Che hiện tượng, không sửa đầu vào model; nuốt lặp thật (06 §3.8 đã loại ở UI); vô dụng khi hai nửa khác top-1 | Loại |
| P5 | Phân biệt "dừng giữa" và "kết thúc" theo tư thế/vị trí tay | Có thể tách đúng hơn | Luật mới không có trong train; thêm ngưỡng chưa có dữ liệu | Loại (ngoài phạm vi) |

**Luật D9 — ĐĂNG KÝ TRƯỚC** (viết trước khi có bất kỳ số nào; coder không đổi; chỉ planner đổi kèm lý do):
- Dữ liệu CHỌN: TRAIN = `data/splits/unified/train.csv`, `source == "qipedc"`, có npz 360 px. Dữ liệu XÁC NHẬN: VAL
  (`val.csv`, cùng điều kiện). TEST không đọc (kể cả W03251N/W03251T).
- Phát lại mỗi clip: t = i/fps (`metadata.fps` của npz), `frame_wh = (width, height)` của CSV, tham số checkpoint,
  `SEGMENTER_DEFAULT` với `rest_hold_s = r`, segmenter MỚI (sau B1); đệm cuối như AC5/AC6: lặp frame cuối
  `ceil((r + 0.2)·fps)` lần, timestamp tiếp tục tăng đều. (Đệm là quy ước test, ghi rõ trong JSON.)
- Lưới G = {0.5, 0.6, 0.7, 0.8}. Trần 0.8 s vì (i) độ trễ thêm ≤ 0.3 s mỗi ký hiệu; (ii) fixture test có sẵn chỉ có
  ~0.9 s nghỉ cuối (§2.4), r ≥ 0.9 buộc sửa test cũ — không được phép.
- Định nghĩa: E(r, clip) = số `Emit`. split(r) = tỉ lệ clip có E ≥ 2. b(r) = số clip có E(0.5) ≥ 2 và E(r) = 1;
  c(r) = số clip có E(0.5) = 1 và E(r) ≠ 1. p(r) = P[X ≥ b(r)] với X ~ Binomial(b(r) + c(r), 0.5) (kiểm dấu một phía,
  tính chính xác; b + c = 0 → p = 1). N = số clip TRAIN có npz.
- Quyết định (script tính bằng CODE và ghi vào JSON, không ai gõ tay):
  1. N < 0.9 × số dòng TRAIN qipedc → `decision = "insufficient_data"` → DỪNG, CẦN PLANNER.
  2. Nhánh C: split_TRAIN(0.5) < 0.02 → giữ 0.5, `decision = "keep_0.5_rare"`.
  3. Nhánh A: ngược lại, r* = r NHỎ NHẤT trong {0.6, 0.7, 0.8} thỏa CẢ BA: b_TRAIN(r)/N ≥ 0.02; p_TRAIN(r) < 0.05;
     b_VAL(r) ≥ c_VAL(r) → `decision = "adopt"`, `rest_hold_s_selected = r*`.
  4. Nhánh B: ngược lại → giữ 0.5, `decision = "keep_0.5_needs_user"` → CẦN NGƯỜI DÙNG kèm số (xem §7).
- Lý do các ngưỡng (phán đoán của planner, ghi trước): 2% = lỗi gặp ở ≥ 1/50 từ trong từ điển mới đáng để MỌI người dùng
  chịu thêm tới 0.3 s độ trễ mỗi từ; kiểm dấu p < 0.05 chặn quyết định do nhiễu; điều kiện VAL chặn lựa chọn làm VAL xấu đi.
- W03251B chỉ là 1 trong N clip TRAIN, không có trọng số riêng, không phải tiêu chí.
- Sau quyết định (mọi nhánh), Giới hạn ghi: split_TRAIN(r_final), split_VAL(r_final) kèm Wilson 95%, và phân bố "nhịp nghỉ
  trong" (`inner_pause_max_s` = đoạn dài nhất các frame KHÔNG hoạt động nằm giữa frame hoạt động đầu và cuối, theo
  `hand_active` của segmenter trên luồng đều; không phụ thuộc r) theo các khoảng [0, 0.5), [0.5, 0.6), [0.6, 0.7),
  [0.7, 0.8), [0.8, 1.0), [1.0, 2.0), [2.0, ∞) s.

### 3.4 Script đánh giá `scripts/segmenter_replay_eval.py` (MỚI)
- CLI: `--mode {dt,rest}` `--kps-dir <thư mục npz 360>` `--ckpt <H-keepz-360 .pt>` `--splits train,val` `--out <json>`.
  - Chỉ nhận split `train`, `val`; `test` hoặc giá trị khác → thoát với mã ≠ 0 trước khi đọc dữ liệu. Mã nguồn không chứa
    chuỗi `test.csv`.
  - sha256 checkpoint phải = `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e`, sai → thoát lỗi. Đọc
    `ckpt["preprocessing"]` và chỉ lấy `CHECKPOINT_KEYS` (không gõ tay giá trị nào). Không chạy model.
  - npz của dòng CSV = `<kps-dir>/<basename(npz_path)>`; thiếu → đếm và ghi `video_id` vào `missing_ids`.
  - Chỉ clip `source == "qipedc"` (clip từ điển: nghỉ → ký → nghỉ, một từ mỗi clip). Không dùng VSL-GH (đoạn cắt từ câu
    liên tục, không có nghỉ đầu/cuối — segmenter không thiết kế cho loại đó).
- Mode `dt` (bằng chứng mục 8), chạy với `SEGMENTER_DEFAULT` của commit đang chạy (trước B4 → `rest_hold_s` 0.5). Mỗi
  clip × 2 cài đặt {`new` = `SignSegmenter`, `ref` = `WindowMeanFpsSegmenter`} × các luồng:
  - `U`: đều, t = i/fps;
  - `D`: mẫu rơi cố định `[giữ, bỏ, giữ, bỏ, bỏ]` lặp lại từ frame 0 (như AC1-k) trên frame của clip; đệm cuối giữ đủ, đều;
  - `J2`, `J5`, `J10`: t_i + s_i·a/1000 với a ∈ {2, 5, 10} ms, s_i = +1 nếu i chẵn, −1 nếu i lẻ, áp cho MỌI frame kể cả
    đệm — mẫu nhiễu GIẢ ĐỊNH, xác định, KHÔNG phải số đo thật (luôn tăng ngặt vì a < 500/fps ms).
  - Ghi mỗi clip: `uniform_identical` (new vs ref trên U: dãy `hand_active` từng frame, dãy `state`, và danh sách sự kiện
    gồm type, reason, segment_id, `t`, `active_start_s`, `active_end_s` — so bằng `==`/`array_equal`); chữ ký sự kiện
    (danh sách (type, reason)) của từng (impl, luồng); `agree_<luồng>_<impl>` = chữ ký luồng đó == chữ ký U cùng impl.
  - Tổng hợp theo split: `n`, `n_uniform_identical`, `n_agree_D_new`, `n_agree_D_ref`, `n_agree_J{2,5,10}_{new,ref}`.
- Mode `rest` (luật D9): per clip E(r) cho mọi r ∈ G, lý do mọi `Discard`, `inner_pause_max_s`; tổng hợp theo split:
  split(r) + Wilson 95%, b(r), c(r), p(r), histogram nhịp nghỉ; cuối cùng `decision`, `rest_hold_s_selected`.
- Header `generated_by`: `command`, `git_commit`, `code_dirty` (`git status --porcelain -- src scripts backend`),
  `generated_at_utc`, phiên bản numpy/python, `checkpoint` (đường tương đối) + `checkpoint_sha256`, `preprocessing`
  (CHECKPOINT_KEYS), `segmenter_params`, `kps_dir` (tên thư mục, không đường tuyệt đối), `n_npz_files` + sha256 của danh
  sách "tên:kích thước" đã sắp xếp, `splits_used`, `grid`, `drop_pattern`, `jitter_ms`, `padding`, `note` ("TRAIN chọn, VAL
  xác nhận, TEST không đọc; mẫu rơi/jitter là mô phỏng xác định, không phải số đo").
- JSON KHÔNG chứa landmark: không có khóa `keypoints`, `landmarks`, `coords`, `visibility`; không đường dẫn tuyệt đối.

### 3.5 Áp quyết định
- Nhánh A: đổi DUY NHẤT `SEGMENTER_DEFAULT["rest_hold_s"]` → r*; docstring ghi nguồn (đường JSON + "luật D9 kế hoạch 08").
  Ràng buộc `_check_params` vẫn thỏa (r* ≥ `pad_s` 0.1, r* > `max_gap_s` 0.25).
- Nhánh B/C: không đổi code; chỉ ghi Giới hạn (progress_log; `docs/phase12_api.md` ở B6).
- Mọi nhánh: sinh lại báo cáo AC6 chuẩn `reports/live_word_<YYYY-MM-DD>/segment_check.json` bằng code cuối (LOCAL), để
  `TestSegmentCheckJson` kiểm bản mới nhất (bản 2026-09-28 giữ nguyên, không xóa).

### 3.6 Hợp đồng API
- WS `/ws/live-stream` protocol_version 2: KHÔNG đổi dạng message, KHÔNG thêm mã lỗi, KHÔNG thêm lý do `sign_discarded`
  (`DISCARD_REASONS` không đổi → `frontend/src/lib/liveProtocol.js:152-160` không phải sửa).
- Thay đổi quan sát được: `session_info.segmenter` có thêm khóa `speed_min_dt_s` (bổ sung, hợp lệ theo 04 §3.6 "chỉ THÊM";
  `liveProtocol.js:64` chỉ đọc `max_sign_s`); nếu nhánh A, `session_info.segmenter.rest_hold_s` và
  `sign_result.metrics.rest_hold_s` = r*.
- Lỗi thời gian vẫn là `bad_timestamp` (không tăng ngặt / NaN / lệch nguồn), không đổi.
- `SignSegmenter.push/reset/validate_time` giữ chữ ký; `Emit`/`Discard` giữ trường.
- `docs/phase12_api.md` (B6, sau 06 APPROVE): ghi `timestamp` = lúc chụp (ms, đồng hồ performance), tốc độ theo dt từng
  frame, giá trị `rest_hold_s`, Giới hạn nhịp nghỉ (số lấy từ JSON D9, kèm đường dẫn).

### 3.7 Module tiền xử lý dùng chung
- Segmenter vẫn gọi `src.data.harmonized._normalise` và `hand_activity` (không chép công thức); `harmonize` và
  `HarmonizedLiveSession._harmonize_buffer` không đổi. Tương đương được chứng minh bởi test mới AC-D1/AC-D2 (fixture + clip
  TRAIN/VAL thật) và test cũ AC4/AC5 (video thật, bộ giải mã backend) phải vẫn PASS.

## 4. Chia việc

`$PY` = `.venv/Scripts/python` (local Windows) hoặc `.venv/bin/python` (cloud). Mọi lệnh Python kèm `PYTHONIOENCODING=utf-8`.
Coder ghi tiến độ vào `docs/plans/08-progress.md` sau MỖI bước (output thật của lệnh, không tóm tắt số bằng tay).

| Bước | Nội dung | Chạy ở đâu / dữ liệu | Phụ thuộc | Ước lượng |
|---|---|---|---|---|
| **B0** | Kiểm tra trước: ghi commit gốc **P8** = HEAD; `git status --porcelain` (lưu lại); chạy lệnh AC-T (§5) → số test/failure/skip theo module làm MỐC (trên cloud: ghi rõ test nào skip vì thiếu dữ liệu, failure có chủ đích nào đang có, ví dụ `TestFrontendSourceGuard` khi 06 chưa xong B6); GitNexus `impact --direction upstream` cho `SignSegmenter`, `_activity`, `_check_params`, `SEGMENTER_DEFAULT` (ghi caller + risk; `UNKNOWN` → xác nhận bằng text search); in dòng CSV của `qipedc_W03251B` (train.csv) — CHỈ đọc id/split, không mở dữ liệu TEST. | cloud hoặc local; không cần dữ liệu | — | 0.5 giờ |
| **B1** | Mục 8. (a) Viết `scripts/segmenter_replay_eval.py` phần lõi: `WindowMeanFpsSegmenter` (nguyên văn `:136-144` tại P8) + hàm `replay(seg, times, kps, vis, frame_wh)` trả (events, hand_active từng frame, state từng frame). (b) Viết `tests/test_segmenter_dt.py` (AC-D1, AC-D3) TRƯỚC, chạy → các ca hành vi mới phải FAIL trên code cũ (ghi output). (c) Sửa `src/inference/sign_segmenter.py`: `_activity` theo §3.2, thêm `speed_min_dt_s: 0.010` vào `SEGMENTER_DEFAULT`, ràng buộc `speed_min_dt_s < stream_gap_s`, docstring. (d) Chạy AC-T; commit (detect-changes, risk trong message). | cloud OK (chỉ fixture) | B0 | 2 giờ |
| **B2** | Bằng chứng mục 8 trên clip thật. Khôi phục dữ liệu vào thư mục gitignored (không commit): checkpoint (`scripts/archive_private_kaggle.py restore`), npz 360 (3 output kernel → `data/processed/qipedc_kps360/`). Hoàn thiện mode `dt`; chạy lệnh AC-D4 → `reports/segmenter_live_<YYYY-MM-DD>/dt_replay_eval.json`. Thêm vào `tests/test_segmenter_dt.py`: `TestDtReplayJson` (AC-D2, AC-D4, AC-D5) + `TestTrainNpzReplaySubset` (`skipUnless` dữ liệu). Commit script + JSON + test. | cloud nếu tải được từ Kaggle; nếu không → local | B1 | 2 giờ |
| **B3** | Mục 9, luật D9. Mode `rest`; chạy lệnh AC-R1 → `reports/segmenter_live_<YYYY-MM-DD>/rest_policy_eval.json`; `TestRestPolicyJson` (AC-R1..R4). Commit. Nếu `decision == "insufficient_data"` → DỪNG (§7). Nếu `keep_0.5_needs_user` → ghi CẦN NGƯỜI DÙNG vào 08-progress kèm số, làm tiếp B4 (không đổi code). | như B2 | B2 | 1.5 giờ |
| **B4** | Áp quyết định (§3.5). Nhánh A: đổi DUY NHẤT `rest_hold_s`; thêm `TestDefaultsMatchDecision` (AC-A). Nhánh B/C: chỉ thêm `TestDefaultsMatchDecision` (khẳng định 0.5). Chạy AC-T; commit. | cloud OK | B3 | 1 giờ |
| **B5a** | Hồi quy video thật cho mục 8 (AC-V1): chạy `live_segment_check.py` ở một commit có code dt MỚI và `rest_hold_s` = 0.5 (sau B1, trước B4 nếu nhánh A — nếu B4 đã commit thì dùng `git worktree add ../_plan08_b5a <commit B3>`, xong thì `git worktree remove`; KHÔNG checkout lùi nhánh chính). Test `TestSegmentCheckDtRegression`. Commit JSON + test. | LOCAL (video + Windows + checkpoint) | B1 | 1.5 giờ |
| **B5b** | Báo cáo AC6 chuẩn với code cuối (AC-V2) → `reports/live_word_<YYYY-MM-DD>/segment_check.json`; khôi phục npz 360 ở local nếu chưa có (như B2) để `TestTrainNpzReplaySubset` không skip; chạy AC-T đầy đủ LOCAL (0 skip); AC-V3. Commit JSON. | LOCAL | B4, B5a | 1.5 giờ |
| **B6** | **CHỈ SAU KHI KẾ HOẠCH 06 APPROVE.** (a) `frontend/src/components/CameraCapture.jsx`: gửi `timestamp: now` (biến `now` ở `:117`, lấy sau `drawImage`, trước `toDataURL`) thay cho `nowMs()` thứ hai — ≤ 3 dòng đổi. (b) Test nguồn (AC-B6). (c) `docs/phase12_api.md`: mục segmenter (timestamp lúc chụp, tốc độ theo dt, `rest_hold_s`, `speed_min_dt_s`, Giới hạn nhịp nghỉ với số từ JSON D9). (d) `cd frontend && npm test` + build; e2e kịch bản word của 06 chạy lại (LOCAL, Edge). Commit. | cloud cho (a)–(c); e2e LOCAL | 06 APPROVE, B4 | 1.5 giờ |
| **B7** | Đóng: so `git status --porcelain` với B0; THÊM 1 dòng `docs/progress_log.md` (AC-P); cập nhật 08-progress; orchestrator gọi vslt-reviewer. Nếu 06 chưa APPROVE khi tới đây: review 08 phần B0–B5b, B6 ghi vào backlog "08-B6 (chặn GATE)". | bất kỳ | B5b (+B6 nếu làm được) | 0.5 giờ |

**Phụ thuộc với kế hoạch 06 (đang làm ở local).**
- 06 không sửa `src/inference/sign_segmenter.py` (06 §"KHÔNG đổi", dòng 391) → B0–B5 không đụng file của 06, làm song song
  được trên nhánh riêng.
- Merge các commit code của 08 (B1, B4) vào `feat/vslt-complete` CHỈ SAU khi 06 APPROVE: B1/B4 đổi hành vi segmenter với
  timestamp thật (e2e B8 của 06 dùng webcam giả + timer thật), nếu merge sớm thì bằng chứng e2e của 06 không còn ứng với
  code 06 được review.
- B6 sửa file của 06 (`CameraCapture.jsx`, `docs/phase12_api.md`) → chỉ sau khi 06 APPROVE. Không sửa `backend/main.py`
  ở bất kỳ bước nào.

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG được đổi; chỉ planner đổi, kèm lý do)

Chuỗi timestamp tổng hợp (fixture) CHỈ dùng trong test đơn vị để kiểm logic thời gian; KHÔNG dùng làm số liệu đánh giá.
Số liệu đánh giá chỉ đến từ các JSON ở AC-D4, AC-R1, AC-V1, AC-V2 (có lệnh + commit).

**AC-0 (B0).** 08-progress có: P8, output `git status --porcelain`, output lệnh AC-T (số test, failure, skip + lý do theo
module), output `impact` 4 symbol, dòng CSV `qipedc_W03251B` với `split = train`.

**AC-D1 — Tương đương khi fps đều (fixture)** `tests/test_segmenter_dt.py::TestUniformEquivalence`.
- Kịch bản: mọi timeline mà AC1 (`tests/test_sign_segmenter.py`) dựng (chỉ nghỉ; 1 ký hiệu 1.0–2.5 s trong 3.5 s; 2 ký hiệu;
  tay giơ 10 s trong 12 s; ký quá ngắn; không thấy tay) + 1 kịch bản tay nghỉ đung đưa (x = 0.4 + 0.03·sin(2πt) cả khi nghỉ
  lẫn khi giơ — biến thể review 04 S3.5), ở fps ∈ {25, 30, 60}, t = i/fps; với tham số mặc định, `{"max_buffer_frames": 64}`
  và `{"rest_hold_s": 0.8}`. Dùng hàm dựng fixture import từ `tests.test_sign_segmenter` (không chép).
- Kỳ vọng: `SignSegmenter` (mới) và `WindowMeanFpsSegmenter` (tham chiếu) cho: dãy `hand_active` từng frame bằng nhau; dãy
  `state` bằng nhau; danh sách sự kiện bằng nhau — `Emit`: `segment_id`, `kps` (`array_equal(equal_nan=True)`), `vis`, `t`
  (`array_equal`), `frame_wh`, `active_start_s`, `active_end_s`, `seqs`; `Discard`: `segment_id`, `reason`, `duration_s`,
  `frames`. 0 khác biệt. Khác biệt bất kỳ → DỪNG, CẦN PLANNER (không nới, không đổi fixture).

**AC-D2 — Tương đương khi fps đều (clip TRAIN/VAL thật).** Trong `dt_replay_eval.json`: `n_uniform_identical == n` cho
TRAIN và cho VAL. `TestTrainNpzReplaySubset` (`skipUnless` npz + checkpoint): tính lại trên 20 clip TRAIN đầu tiên theo
`video_id` đã sắp xếp → `uniform_identical` đúng cho cả 20, và chữ ký sự kiện U/D của 20 clip == giá trị trong JSON (tái lập).

**AC-D3 — Ngữ nghĩa dt từng frame (fixture)** `tests/test_segmenter_dt.py::TestPerFrameDt`, mỗi ý một test:
- a. Cặp cuối quyết định: cửa sổ có các frame đầu cách nhau 0.2 s, cặp cuối cách 1/30 s; cổ tay phải dưới `rest_y` (chỉ tốc
  độ quyết định); dịch chuyển cặp cuối sao cho Δ·30 = 1.2 sw/s → mới: `hand_active` True, tham chiếu: False; Δ·30 = 0.8 →
  mới: False.
- b. Rơi frame với vận tốc đều 1.1 sw/s (dưới `rest_y`), mẫu `[giữ, bỏ, giữ, bỏ, bỏ]` → mới: `hand_active` True ở MỌI frame
  từ frame thứ 2; tham chiếu: không phải mọi frame (ghi lại dãy).
- c. `speed_min_dt_s`: hai frame cách 1e-6 s, dịch chuyển 0.002 sw (dưới `rest_y`) → mới với mặc định: False; với
  `{"speed_min_dt_s": 0}`: True.
- d. Kiểm tham số: `speed_min_dt_s` = NaN, −0.01, `"x"`, `True`, `1.0` (= `stream_gap_s`) → `ValueError`; `0` được nhận.
  `SEGMENTER_DEFAULT["speed_min_dt_s"] == 0.010`.
- e. Kịch bản review 04 S3.5: fixture AC1-k (1 ký hiệu 1.0–2.5 s trong 3.5 s, 30 fps, mẫu rơi `[giữ, bỏ, giữ, bỏ, bỏ]`) nhưng
  tay phải đung đưa x = 0.4 + 0.03·sin(2πt) CẢ khi nghỉ → mới: đúng 1 `Emit`, `[t[0], t[-1]]` chứa `active_span` offline
  (tính như AC1-k trên luồng đầy đủ 30 fps). In số sự kiện của tham chiếu (không assert tham chiếu).
- f. Khoảng trống 0.6 s (< `stream_gap_s`) khi tay nghỉ đứng yên → không có frame hoạt động giả, không sự kiện.
- g. `scripts/segmenter_replay_eval.py` không chứa chuỗi con `random`, không chứa `test.csv`; `--splits test` và
  `--splits train,test` → thoát mã ≠ 0 (chạy subprocess, không cần dữ liệu).
- Test cũ AC1 a–o (gồm AC1-h timestamp không tăng, AC1-o không import torch/cv2/mediapipe) và AC7-e vẫn PASS không sửa.

**AC-D4 — JSON bằng chứng mục 8 (B2).** Lệnh:
`PYTHONIOENCODING=utf-8 $PY scripts/segmenter_replay_eval.py --mode dt --kps-dir data/processed/qipedc_kps360 --ckpt reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt --splits train,val --out reports/segmenter_live_<YYYY-MM-DD>/dt_replay_eval.json`
`TestDtReplayJson` kiểm: file tồn tại; `generated_by` đủ khóa §3.4; `code_dirty == false`; `git_commit` là tổ tiên HEAD;
`checkpoint_sha256` đúng; `splits_used == ["train", "val"]`; không `video_id` nào thuộc `test.csv` (test đọc CỘT id của
test.csv chỉ để kiểm rò rỉ); không khóa cấm; mỗi split `n_available ≥ 0.9 × n_rows` (sai → DỪNG, CẦN PLANNER).

**AC-D5 — Không kém hơn khi rơi frame (đăng ký trước, TRAIN).** `n_agree_D_new ≥ n_agree_D_ref` trên TRAIN. FAIL → DỪNG,
CẦN PLANNER (không chỉnh `speed_min_dt_s`, không đổi mẫu rơi). Số VAL và J2/J5/J10: CHỈ BÁO CÁO. Bắt buộc về lời: nếu với
bất kỳ a có `n_agree_Ja_new < n_agree_Ja_ref` trên TRAIN, progress_log và (ở B6) `docs/phase12_api.md` phải ghi "tốc độ theo
dt nhạy với nhiễu timestamp; timestamp phải là thời điểm chụp (B6)" kèm số từ JSON.

**AC-R1 — JSON luật D9 (B3).** Lệnh:
`PYTHONIOENCODING=utf-8 $PY scripts/segmenter_replay_eval.py --mode rest --kps-dir data/processed/qipedc_kps360 --ckpt reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt --splits train,val --out reports/segmenter_live_<YYYY-MM-DD>/rest_policy_eval.json`
`TestRestPolicyJson` kiểm như AC-D4 (header, sạch, tổ tiên, sha, splits, không id TEST, không khóa cấm), thêm:
`grid == [0.5, 0.6, 0.7, 0.8]`; `decision` ∈ {`adopt`, `keep_0.5_rare`, `keep_0.5_needs_user`, `insufficient_data`}.
- **AC-R2:** test tính LẠI (cài đặt độc lập trong test, `math.comb` cho nhị thức, Wilson tự viết) split(r), b(r), c(r), p(r)
  và quyết định theo đúng chữ §3.3 từ các dòng E(r) per clip trong JSON → bằng `decision` và `rest_hold_s_selected` của JSON.
- **AC-R3:** E(0.5, clip) trong `rest_policy_eval.json` == số `Emit` của luồng U/new trong `dt_replay_eval.json` cho mọi clip
  chung, khi `git diff <commit dt> <commit rest> -- src/inference/sign_segmenter.py` rỗng (cùng code segmenter).
- **AC-R4:** histogram nhịp nghỉ có đủ 7 khoảng và tổng = N mỗi split.

**AC-A — Mặc định khớp quyết định (B4)** `TestDefaultsMatchDecision`: đọc `rest_policy_eval.json` mới nhất; `adopt` →
`SEGMENTER_DEFAULT["rest_hold_s"] == rest_hold_s_selected`; ngược lại `== 0.5`. Mọi khóa khác của `SEGMENTER_DEFAULT` bằng
giá trị ở §2.1 + `speed_min_dt_s: 0.010` (không đổi gì khác). `CHECKPOINT_KEYS` không đổi.

**AC-V1 — Hồi quy video thật cho mục 8 (B5a, LOCAL).** Lệnh:
`PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py --n-clips 8 --seed 0 --out reports/segmenter_live_<YYYY-MM-DD>/segment_check_dt.json`
`TestSegmentCheckDtRegression` (`skipUnless` file tồn tại): `generated_by.mediapipe`, `cv2`, `numpy`, `checkpoint_sha256`
bằng bản `reports/live_word_2026-09-28/segment_check.json`; `segmenter_default` bằng bản cũ cộng DUY NHẤT khóa
`speed_min_dt_s`; `code_dirty == false`; `clips` và `n_contains_offline_span` BẰNG HỆT bản 2026-09-28 (so `==` trên JSON đã
parse). Phiên bản khác → không so được → DỪNG, CẦN PLANNER (không nới). (Đường dẫn ngoài `live_word_*` nên không đổi file mà
`TestSegmentCheckJson` đọc.)

**AC-V2 — Báo cáo AC6 với code cuối (B5b, LOCAL).** Lệnh:
`PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py --n-clips 8 --seed 0 --out reports/live_word_<YYYY-MM-DD>/segment_check.json`
`TestSegmentCheckJson` (có sẵn) PASS trên file này. Báo cáo (không ngưỡng): sự kiện từng clip, riêng `qipedc_W03251B` (số
`sign_result`, gloss) — số lấy từ JSON.

**AC-V3 (LOCAL).** `tests.test_live_harmonized_equivalence` (AC4, AC5, `TestWebSocketEventsNotEmpty`) PASS, 0 skip.

**AC-T — Không hồi quy.** Lệnh (danh sách AC2 của kế hoạch 06 + module mới):
`PYTHONIOENCODING=utf-8 $PY -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_segmenter_dt -v`
(Nếu AC2 của 06 được planner 06 đổi danh sách: dùng danh sách cuối của 06 + `tests.test_segmenter_dt`; nếu B6 thêm test
Python thì thêm module đó.)
- Mốc trung gian (B1–B4, cloud được): 0 error; failure chỉ được là failure đã có ở mốc B0 (cùng tên test), không thêm; skip
  chỉ ở test cần dữ liệu, ghi lý do từng skip.
- Đóng việc (B5b, LOCAL): 0 failure, 0 error, 0 skip — ngoại lệ DUY NHẤT: failure có chủ đích của 06 còn tồn tại ở mốc B0 nếu
  06 chưa đóng (ghi tên), không thêm failure nào.
- `git diff P8 HEAD -- tests/` với mọi file test đã có ở P8: 0 dòng `-`.
- Trước B6: `git diff P8 HEAD -- src/data scripts/train_unified.py scripts/extract_keypoints_batch.py src/inference/harmonized_live.py backend frontend docs/phase12_api.md scripts/smoke_test_phase12.py scripts/live_segment_check.py` → rỗng.
  Sau B6: chỉ thêm `frontend/src/components/CameraCapture.jsx` (≤ 3 dòng đổi), `docs/phase12_api.md`, test mới của B6.
- `git status --porcelain` trước/sau khi chạy test giống hệt.

**AC-B6 (chỉ sau 06 APPROVE).**
- Test nguồn (Python `tests/test_capture_timestamp.py` hoặc Node `frontend/tests/*.test.mjs`): trong thân `grabAndSendFrame`
  của `CameraCapture.jsx`, vị trí `drawImage(` < vị trí lấy giờ dùng làm `timestamp` < vị trí `toDataURL(`; message gửi dùng
  đúng biến đó; không còn `timestamp: nowMs()`.
- `cd frontend && npm test` 0 fail (số file test == `git ls-files "frontend/tests/*.test.mjs"`); `npm run build` OK.
- e2e kịch bản word của 06 chạy lại (LOCAL): ≥ 1 `sign_result`/`sign_discarded`, 0 message `error`; JSON mới có
  `generated_by`.
- `docs/phase12_api.md` có mục segmenter như §3.6, số lấy từ JSON (kèm đường dẫn).

**AC-P — Quy trình.**
- `impact` (upstream) trước khi sửa mỗi symbol có sẵn (`SignSegmenter._activity`, `_check_params`, `SEGMENTER_DEFAULT`,
  `grabAndSendFrame` ở B6); HIGH/CRITICAL phải ghi cảnh báo trong 08-progress. `detect-changes --scope all` trước MỖI commit,
  risk ghi trong commit message; không `--amend` commit đã có.
- Không `.pt/.npz/.mp4`/landmark/frame nào vào git; `reports/segmenter_live_*/` chỉ chứa JSON; `data/processed/qipedc_kps360/`
  không vào git.
- `docs/progress_log.md`: THÊM đúng 1 dòng (không sửa dòng cũ): ngày | việc | kế hoạch 08 | commit | test trước → sau |
  `decision` D9 + split_TRAIN/VAL (từ JSON) | kết luận review | việc tiếp theo.
- 3 file dữ liệu bị xóa của người dùng vẫn " D" chưa staged (local). Không xóa file nào.
- Review `docs/reviews/08-review.md` kết luận APPROVE.

## 6. Rủi ro dữ liệu/ML

- **Lệch train–realtime còn lại (không sửa ở đây).**
  - `_harmonize_buffer` → `harmonize` dùng fps TRUNG BÌNH của đoạn cho `active_span`, `pad` và `mask_resting_hand`. Khi rơi
    frame, cắt nghỉ + che tay nghỉ bên trong `harmonize` vẫn theo fps trung bình. Không sửa vì đó là hàm train (sửa = đổi
    dữ liệu train → phải train lại/GATE). `sign_result.segment.effective_fps`, `dropped_frames` đã có để đo. Đề xuất việc
    sau (không thuộc 08): resample đoạn về lưới đều trước `harmonize`, có test tương đương riêng.
  - Chuẩn hóa theo cửa sổ 1 s (median độ rộng vai của cửa sổ) khác cả clip lúc train — có từ kế hoạch 04, không đổi.
  - fps cao hơn train (webcam 60 fps): nhiễu landmark giữa hai frame liền kề → tốc độ nhiễu lớn gấp đôi so với 30 fps ở CẢ
    cách cũ lẫn mới (không do việc này). Ghi Giới hạn; chỉ đo được bằng bộ webcam Bước 5.
- **Nhiễu timestamp.** Tốc độ theo dt từng frame nhạy với nhiễu thời gian hơn fps trung bình. Timestamp client hiện là lúc
  GỬI (sau mã hóa JPEG) → B6. Phiên nguồn `"server"` (client không gửi timestamp) nhiễu hơn — ghi vào `docs/phase12_api.md`.
  Mẫu J2/J5/J10 là giả định, KHÔNG phải số đo jitter thật; jitter thật chỉ đo được qua WebSocket thật (DoD 8 / Bước 5).
- **Frame trùng.** Nếu timer gửi nhanh hơn camera (camera tối ~15 fps, `targetFps` 25), cùng một frame video có thể được gửi
  2 lần: dịch chuyển ≈ 0 rồi frame kế dịch chuyển gấp đôi trong một dt → tốc độ frame kế bị phóng đại tới ~2× (cách cũ làm
  nhòe hiện tượng này qua fps trung bình). Không xử lý ở đây; ghi Giới hạn; hướng xử lý sau: chụp theo
  `requestVideoFrameCallback` (thuộc frontend, kế hoạch riêng).
- **Phát lại npz ≠ live.** npz 360 được trích trên Kaggle Linux, extractor mới cho MỖI clip (như train), không có tracker
  xuyên phiên, không nén JPEG, không rơi frame thật → số E(r) là cận LẠC QUAN cho live. Landmark Linux có thể lệch Windows
  (`docs/CLOUD.md` §4) → kết quả W03251B trên npz có thể khác JSON 2026-09-28 (Windows); không dùng so sánh đó làm tiêu chí.
- **Đích thay thế "1 clip = 1 từ ⇒ 1 Emit".** Clip từ điển có thể minh họa ký hiệu 2 lần; khi đó 2 Emit không hẳn sai. Việc
  này không xem video/frame (không lưu frame) nên không phân biệt được; ghi Giới hạn.
- **Chi phí của P1 chưa đo.** Khoảng nghỉ giữa hai từ của người dùng thật chưa có dữ liệu (Bước 5). Trần 0.8 s giới hạn rủi
  ro gộp nhầm hai từ; UI/tài liệu phải nói "hạ tay ≥ r giây giữa hai từ". Sau Bước 5: đánh giá lại trên bộ webcam (không
  phải TEST) bằng kế hoạch riêng, đăng ký trước.
- **Cỡ mẫu.** Planner đếm tại thời điểm lập (grep `,qipedc,`): train.csv 795 dòng, val.csv 105 dòng — chỉ để lên kế hoạch;
  N thật lấy từ JSON. VAL nhỏ → điều kiện VAL chỉ là chặn "không xấu đi", công suất thấp. Ba giá trị r cùng kiểm p < 0.05 →
  lạm phát nhẹ do so sánh bội; chấp nhận vì luật chọn r nhỏ nhất + điều kiện hiệu ứng ≥ 2% + điều kiện VAL. Mọi tỉ lệ kèm
  Wilson 95%.
- **Rò rỉ.** Không train, không đo độ chính xác, không chạy model trong đánh giá. TEST không được đọc (script từ chối
  `test`; test kiểm không có id TEST trong JSON). W03251N/W03251T (TEST, cùng gloss `thìa`) không chạm. Chọn trên TRAIN, xác
  nhận trên VAL.
- **Nguồn gốc / giấy phép.** npz QIPEDC là output kernel private của tài khoản người dùng; video QIPEDC chỉ dùng nội bộ; JSON
  chỉ ghi `video_id` + số; không commit npz/landmark/frame.
- **Checkpoint.** Chỉ đọc `preprocessing` (sha kiểm trước); không dùng trọng số trong đánh giá D9/dt.
- **Đệm test.** Lặp frame cuối: nếu clip kết thúc khi tay còn giơ, đệm giữ tay giơ → có thể `too_long`/không phát (như AC6);
  ghi trong JSON, không đổi quy ước.

## 7. Điểm dừng

- **Đổi model mặc định:** KHÔNG. `DEFAULT_MODEL_TYPE` vẫn `"stgcn"` (đường legacy, không dùng `SignSegmenter`).
- **Cần dữ liệu người dùng cung cấp:** KHÔNG. Dùng artifact private đã có (checkpoint, npz 360 của tài khoản `phmvnsm33`) và
  video đã có ở local. Bộ webcam Bước 5 không cần cho việc này.
- **Đụng thay đổi chưa commit của người dùng:** KHÔNG. 3 file " D" và các file untracked không đụng; npz tải về đặt trong
  thư mục gitignored.
- **Hành động không hoàn tác:** KHÔNG (không xóa file; `git worktree` ở B5a là tạm, gỡ được; không lệnh Kaggle ghi/xóa, chỉ
  tải output về).
- **Phụ thuộc kế hoạch 06:** B6 và việc merge code 08 vào `feat/vslt-complete` chỉ SAU khi 06 APPROVE (§4). Không sửa
  `backend/main.py` ở bất kỳ bước nào.
- **Điểm dừng CÓ ĐIỀU KIỆN:**
  1. AC-D1 hoặc AC-D2 có khác biệt (tương đương khi fps đều bị vỡ) → CẦN PLANNER. Không nới, không đổi fixture.
  2. AC-D5 FAIL (cách mới kém hơn cách cũ khi rơi frame trên TRAIN) → CẦN PLANNER.
  3. `n_available < 0.9 × n_rows` ở một split, hoặc `decision == "insufficient_data"` → CẦN PLANNER.
  4. `decision == "keep_0.5_needs_user"` → **CẦN NGƯỜI DÙNG** (không chặn B4–B7; coder làm tiếp với `rest_hold_s = 0.5`).
     Câu hỏi gửi kèm số từ `rest_policy_eval.json`: "Với trần 0.8 s, tỉ lệ clip TRAIN vẫn bị tách là X% (Wilson 95% […]).
     Chọn: (a) chấp nhận và ghi Giới hạn; (b) cho phép `rest_hold_s` > 0.8 s — độ trễ mỗi từ lớn hơn và phải sửa timeline
     fixture của test cũ (cần người dùng cho phép sửa test); (c) làm phương án P3 'phát rồi sửa lại' — đổi hợp đồng WS và UI
     (kế hoạch riêng)."
  5. Một test có sẵn FAIL sau B1 hoặc B4 → CẦN PLANNER (không sửa test, không đổi tham số để né).
  6. AC-V1: phiên bản mediapipe/cv2/numpy/sha khác bản 2026-09-28, hoặc `clips` khác → CẦN PLANNER.
  7. Không tải được npz 360/checkpoint ở cả cloud lẫn local (quyền Kaggle) → CẦN NGƯỜI DÙNG (quyền truy cập dữ liệu).
  8. `impact` báo HIGH/CRITICAL → ghi cảnh báo vào 08-progress; không tự bỏ qua, tiếp tục chỉ khi thay đổi đúng phạm vi §3.

**Tóm tắt nơi chạy:** cloud làm được B0, B1, B4, và B2–B3 nếu tải được dữ liệu Kaggle; LOCAL bắt buộc cho B5a, B5b (video,
Windows, 0 skip) và e2e của B6.
