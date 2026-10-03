# Kế hoạch 15 — Cấp 1 (đánh vần chữ cái VSL) realtime trên app desktop OpenCV, tự tách ký hiệu + ghép từ

TRẠNG THÁI: XONG (planner, 2026-10-03). Không có điểm "CẦN NGƯỜI DÙNG" để BẮT ĐẦU (xem §7).
Người lập: vslt-planner, HEAD 5140d8e, nhánh feat/vslt-complete. Kế hoạch 11/13/14 đang TẠM DỪNG — kế hoạch này không phụ thuộc
và không sửa file của chúng.

## 1. Mục tiêu + DoD phục vụ

**Mục tiêu.** Một app desktop (`level1_demo.py`, cửa sổ OpenCV) đọc webcam, tự tách từng ký hiệu chữ cái/dấu thanh khi người ký
đổi chữ (không bấm Ghi/Dừng), phân loại bằng checkpoint Cấp 1 đang dùng (`checkpoints/alphabet_best.pt`, KHÔNG đổi model),
ghép chữ + dấu thanh thành từ tiếng Việt và hiển thị trên khung hình, với chấm landmark vẽ trên ĐÚNG khung đã xử lý; đo độ trễ
từng chặng ra HUD + JSON. Logic dùng chung nằm trong "lõi Cấp 1" thuần (`src/inference/level1_*.py`) để web dùng lại sau.
Hạn: người dùng báo cáo thầy khoảng 6–8/10/2026 → MVP chạy được trước (B0–B3), đo/tài liệu sau.

**DoD phục vụ** (docs/prompts/autopilot.md §1): DoD 2 (Đánh vần: chuỗi landmark → chữ + confidence → ghép từ; ở đây là đường
desktop, đường web giữ nguyên), DoD 6 (không kết quả giả: token chỉ từ model hoặc phím người dùng có ghi nguồn, chữ ghép chỉ từ
`compose`), DoD 7 (test tương đương train ↔ realtime cho đường mới + guard không thêm vi phạm), một phần DoD 8 (đo độ trễ từng
chặng — LƯU Ý: DoD 8 đòi đo "qua WebSocket thật" cho web; số desktop KHÔNG thay thế số đó, ghi rõ trong tài liệu), một phần DoD 9
(mục Giới hạn §6.3).

## 2. Hiện trạng (bằng chứng file:dòng)

### 2.1 Model Cấp 1 nhận gì
- Checkpoint triển khai `checkpoints/alphabet_best.pt` (có trên đĩa). Nội dung theo `reports/alphabet_deploy_2026-09-27/provenance.json:7-56`:
  `model_type` bigru, `selected` [bigru, 120, "frame"], `epochs` 120, `classes` 34 lớp (29 chữ + 5 dấu thanh, `:57…`),
  `preprocessing` = {aspect_correct true, mirror_left_hand true, target_frames 30, normalization wrist_centered_palm_scale,
  extractor mp.solutions.hands, mediapipe_version 0.10.14, max_num_hands 1, model_complexity 1, resample "frame_index",
  wrist_trajectory false, min_detected_frames 3} (`:34-46`), `trained_on` {source hauuto, 4 signers, clips 636} (`:47-56`).
  Checkpoint này BẰNG HỆT state_dict của chạy nested primary, KHÁC chạy real_run (`provenance.json:375-379`:
  `nested_primary true`, `real_run false`).
- Kiến trúc: `VSLAlphabetBiGRU(input_dim=63, hidden_dim, num_layers, num_classes)` (`src/models/alphabet_temporal.py:12`), dựng
  từ `hparams` của checkpoint ở `backend/main.py:626-628`; đầu vào [B, 30, 63].
- Tiền xử lý dùng chung (một hàm cho train và live): `alphabet_clip_features` (`src/data/alphabet_preprocessing.py:270-304`):
  `canonicalize_hand_sequence` (bù tỉ lệ x,z × W/H; lật x nếu nhãn handedness đa số là "Left" trên khung KHÔNG lật gương;
  khung không tay = 0) `:171-212` → lỗi nếu số khung có tay < `min_detected_frames` `:289-290` → `resample_by_index` (30 khung
  chọn đều trên các khung CÓ tay, bỏ khoảng hở) `:254-257` → `normalize_hand_landmarks` (gốc cổ tay, chia độ dài cổ tay→MCP giữa)
  `:22-54` → [30, 63]. Script train dùng `canonicalize_hand_sequence` + `sequence_features_from_clip` (`scripts/train_alphabet_real.py:48-53`),
  tương đương nhánh frame_index (đã có test ở `tests/test_hand_live_equivalence.py:115-132`).
- Một mẫu train = TRỌN một clip một ký hiệu: `scripts/extract_hands_batch.py:23-63` — `mp.solutions.hands.Hands(static_image_mode=False,
  max_num_hands=1, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)` (`:37-38`), tracker MỚI mỗi clip,
  khung GỐC (không resize, không lật), BGR→RGB, tay đầu tiên + handedness đầu tiên (`:43-50`). Clip hauuto 640×480, 23.584 fps
  (`data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv:2-3`; số khung mỗi clip ở cột `num_frames`; ví dụ trong
  `reports/fingerspell_live_2026-09-29/hand_live_check.json:25,49,73…`). Video gốc tại `data/external/hauuto_raw/raw/raw/<signer>/`
  (640 mp4, `docs/plans/12-progress.md:111-112`), npz Kaggle tại `data/external/alphabet_hands_kaggle/alphabet_hands/`.
- Dấu thanh là 5 LỚP riêng ("dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng") của cùng model — ký hiệu có chuyển động
  (`src/inference/fingerspelling_compose.py:32-38`); bộ tách ký hiệu phải giữ được đoạn chuyển động của dấu thanh.
- Trình trích live có sẵn, bằng hệt train: `src/inference/hand_live.py:21-27` `LEVEL1_HANDS_KWARGS`, `HandLandmarkSession`
  (`reset()` = tracker mới, `process(frame_bgr)` → (float32[21,3] | None, "Left"/"Right"/"", score)) `:35-66`. Kwargs khớp
  `extract_hands_batch.py` được khóa bằng AST ở `tests/test_hand_landmarks_ws.py:89-96`; landmark live == offline BIT-identical
  trên 10 clip ở `tests/test_hand_live_equivalence.py:85-97`. Lệch đã biết: JPEG q90 vs PNG tới ~0.24, npz Kaggle (Linux) vs trích
  local tới ~0.23 (`hand_live_check.json:80-88`) → desktop KHÔNG nén JPEG nên tránh được lệch thứ nhất.

### 2.2 Đường Cấp 1 hiện có (web)
- `POST /api/fingerspelling/sequence` (`backend/main.py:797-834`): kiểm đầu vào `parse_fingerspelling_sequence` `:722-763`, đặc
  trưng `alphabet_clip_features(raw, detected, hand, W/H, ts, ckpt.preprocessing, model_type)` `:806-808`, softmax top-k, trả
  {prediction, prediction_kind, confidence (làm tròn 4), candidates, frames, detected_frames, model_type, checkpoint}.
  Nạp model: `get_or_load_alphabet_model` `:602-641` (đòi `classes` + `preprocessing` trong checkpoint).
- Ghép từ: `src/inference/fingerspelling_compose.py:118-147` `compose(tokens)` thuần (không torch/fastapi): token = tên lớp hoặc " ";
  dấu thanh áp cho cả âm tiết, đặt đúng nguyên âm (`:70-94`), cảnh báo `multiple_tones`/`tone_without_vowel`; API `/compose` `main.py:837-845`.
- Web: WS `/ws/hand-landmarks` (`main.py:1572-1699`) trả landmark từng khung; client gom một lượt Ghi/Dừng rồi POST /sequence
  (`frontend/src/lib/fingerspelling.js:34-62`); người dùng tự bấm chấp nhận token (`frontend/src/components/Fingerspelling.jsx:304-324,489-514`).
  KHÔNG có tách ký hiệu tự động, KHÔNG có ngưỡng confidence tự động. Độ trễ người dùng thấy (STATE 2026-10-03 10:45): vòng
  trình duyệt → JPEG → WS → MediaPipe server → về, chấm vẽ trên khung hiện tại bằng tọa độ khung cũ (chưa đo).
- `realtime_demo.py` là demo Cấp 2 (import `VSLPredictor`, `RealtimePipeline`: `realtime_demo.py:28-31`), thuộc phạm vi kế hoạch 11
  (TẠM DỪNG). `README.md:203` ghi `realtime_demo.py --webcam` nhưng `main()` chỉ có `--source`/`--video`
  (`docs/plans/11-sua-vi-pham-guard-dod7.md:106-107`).
- `src/inference/sign_segmenter.py` là bộ tách Cấp 2 (kế hoạch 08/11, TẠM DỪNG) — KHÔNG dùng lại, KHÔNG sửa.

### 2.3 Guard DoD 7
- `tests/test_backend_source_guard.py:46` `ENTRYPOINTS = ("backend/main.py", "realtime_demo.py")`; MAIN = `backend/**` + `src/**` + SERVING
  (`:799-806`). Luật D-binding/D-string áp cho MỌI file `src/**` (`:75,95-98`): tên chứa token `ms`, `fps`, `latency`, `p50`, `p95`…
  (`:139-141`) nhận số gõ tay → vi phạm; chuỗi "<số> ms|fps|%" → vi phạm (`:142-147`). Luật C (fake/mock/synthetic/simulat…, giá trị
  cố định gán vào `prediction`/`confidence`/`candidates`…) chỉ áp cho SERVING (`:127-137`).
- File mới ở GỐC repo (như `level1_demo.py`) KHÔNG nằm trong phạm vi guard chính; file guard thuộc danh sách sửa của kế hoạch 11
  (đang dừng) → kế hoạch 15 KHÔNG sửa nó, mà thêm guard riêng tái dùng `scan_source`/`serving_closure` (`:720-724,781-796`), §5 AC-G.
- Quy ước fps của kế hoạch 11: không `or 30.0`/fps mặc định gõ tay; khi chưa đo được (n < 2) hiển thị 0.0/"—"
  (`11-sua-vi-pham-guard-dod7.md:62`; STATE 2026-10-03 ghi chú F2).

### 2.4 Thiếu
1. Không có bộ tách ký hiệu Cấp 1 (mọi đường hiện tại là Ghi/Dừng thủ công).
2. Không có lõi Cấp 1 dùng chung ngoài backend (nạp model + phân loại nằm trong `backend/main.py`).
3. Không có app desktop Cấp 1, không có đo độ trễ từng chặng Cấp 1.
4. Số LOSO trong README (`README.md:51`: 75.1% ± 8.7) là của chạy `reports/alphabet_real_run_2026-09-25/` — KHÔNG phải checkpoint
   đang triển khai (nested primary). Số cho checkpoint triển khai phải lấy từ `reports/alphabet_nested_2026-09-25/primary/nested_report.json`.

## 3. Thiết kế

### 3.1 File (tất cả MỚI; không sửa file có sẵn)
| File | Vai trò |
|---|---|
| `configs/level1_realtime.json` | Mọi tham số tách ký hiệu / chấp nhận token / camera / hiển thị. Mỗi khóa = {`value`, `source` ("design" hoặc "calibrated: <JSON>@<commit>"), `reason`}. |
| `src/inference/level1_segmenter.py` | Bộ tách ký hiệu thuần numpy (không cv2/torch). |
| `src/inference/level1_core.py` | `load_level1_config`, `Level1Classifier` (nạp checkpoint + phân loại segment qua `alphabet_clip_features`), `Level1Speller` (chấp nhận token + `compose`). Không GUI, không thread. |
| `src/inference/level1_timing.py` | Bộ đo chặng + thống kê (n, mean, p50, p95) thuần. |
| `level1_demo.py` (gốc repo, cạnh `realtime_demo.py`) | App desktop: luồng camera, vòng xử lý, HUD, phím, chế độ headless/replay, ghi JSON. |
| `scripts/level1_segment_report.py` | Thống kê + hiệu chỉnh trên clip TRAIN (npz) → JSON (§3.6). |
| `scripts/level1_replay_clips.py` | Chạy app headless trên clip thật → JSON (§3.7); `--summary` sinh `SUMMARY.md` từ các JSON. |
| `tests/test_level1_segmenter.py`, `tests/test_level1_core.py`, `tests/test_level1_demo.py`, `tests/test_level1_equivalence.py`, `tests/test_level1_guard.py` | Test (§5). |
| `docs/level1_desktop.md` | Cách chạy, phím, kiến trúc, chặng đo, Giới hạn; số liệu chỉ trỏ tới JSON/SUMMARY sinh tự động. |
| `docs/plans/15-progress.md` | Tiến độ coder. |
| `reports/level1_realtime_<YYYY-MM-DD>/` | JSON + SUMMARY.md sinh bằng lệnh, tại commit sạch. |

Không sửa: `backend/main.py`, `src/inference/hand_live.py`, `src/data/alphabet_preprocessing.py`, `src/inference/fingerspelling_compose.py`,
`realtime_demo.py`, `src/inference/sign_segmenter.py`, `tests/test_backend_source_guard.py`, `README.md`, checkpoint, mọi file trong danh
sách kế hoạch 11/13/14. Lõi chỉ IMPORT `HandLandmarkSession`, `alphabet_clip_features`, `compose`, `token_kind`, `VSLAlphabetBiGRU`/`VSLAlphabetMLP`.
Nếu coder thấy BUỘC phải sửa symbol có sẵn → dừng, chạy `impact` (upstream), ghi vào 15-progress, báo planner (không tự sửa).

### 3.2 Luồng dữ liệu (desktop, chế độ webcam)
```
[T-cap] luồng camera: cv2.VideoCapture(index, api) → read() liên tục → ô MỚI NHẤT (1 chỗ, ghi đè; đếm khung bị bỏ) + t_cap (perf_counter)
[T-main] vòng chính: lấy khung mới nhất (seq mới) → HandLandmarkSession.process(frame) [MediaPipe video mode, kwargs = train]
         → Level1SignSegmenter.push(t_cap_ms, lms|None, handedness, W, H) → sự kiện (SignSegment | WordGap)
         → vẽ chấm lên CHÍNH frame vừa xử lý → (tùy chọn lật gương hiển thị) → HUD chữ (PIL, font tiếng Việt) → imshow/waitKey(1)
         SignSegment → hàng đợi phân loại (không chờ)
[T-cls] 1 worker: Level1Classifier.classify(segment) → kết quả (giữ thứ tự seq) → hàng đợi kết quả
[T-main] mỗi vòng: rút kết quả + sự kiện theo ĐÚNG thứ tự seq → Level1Speller → compose(tokens) → HUD
```
- Khung luôn KHÔNG lật khi vào MediaPipe (quy ước train; skill vsl-landmark-consistency mục 4). Lật gương chỉ để hiển thị: vẽ chấm
  trước, lật ảnh sau, vẽ chữ HUD sau cùng.
- Không resize khung trước MediaPipe (hand_live.py docstring `:4-7`). Camera xin 640×480 qua config `camera_width/height` (lý do: khớp
  kích thước clip hauuto trong manifest); kích thước thật đọc từ khung, ghi vào JSON; bù tỉ lệ dùng W/H thật.
- MỘT `HandLandmarkSession` liên tục cho cả phiên (không reset mỗi ký hiệu, vì đầu ký hiệu chỉ biết sau). Lệch so với train: khung đầu
  của một ký hiệu có thể đi nhánh tracking thay vì detection — đo bằng AC-E2 (không khẳng định bằng hệt).
- `--source <video> --headless` (replay chính xác): xử lý MỌI khung theo thứ tự, timestamp = i × 1000 / fps đọc từ file (fps ≤ 0 /
  không đọc được → lỗi rõ ràng, KHÔNG fps mặc định), phân loại đồng bộ để kết quả tất định. `--pace realtime` (video): luồng camera đọc
  file theo nhịp fps của file và áp dụng y như webcam (lấy khung mới nhất, bỏ khung cũ) để đo độ trễ/khung bỏ khi không có webcam.
  Không dùng chữ "simulate/mock/fake/synthetic/placeholder" trong mã app/lõi (guard C), không gán hằng vào biến tên
  `confidence`/`prediction`/`candidates` (dùng `None` cho "chưa có").

### 3.3 Bộ tách ký hiệu (`Level1SignSegmenter`)
Tín hiệu chuyển động mỗi khung có tay (t) mà khung trước cũng có tay (t−1), dt = ts_t − ts_{t−1} > 0:
- P = landmark thô với x, z × (W/H) (cùng phép bù như `canonicalize_hand_sequence`); palm_t = ‖P_t[9,:2] − P_t[0,:2]‖.
- v_t (cổ tay) = ‖P_t[0,:2] − P_{t−1}[0,:2]‖ / mean(palm_t, palm_{t−1}) / dt_s; s_t (hình bàn tay) = trung bình 21 điểm ‖N_t − N_{t−1}‖ / dt_s,
  N = `normalize_hand_landmarks(P)`; m_t = max(v_t, s_t), đơn vị "độ dài bàn tay / giây" — không phụ thuộc fps, độ phân giải.
- M_t = trung vị m trong cửa sổ `motion_window_ms` gần nhất. Không có cặp khung có tay liên tiếp → M_t = None (KHÔNG gán số; không
  tính là đứng yên). Timestamp phải tăng ngặt; vi phạm → `ValueError`.
Máy trạng thái (tham số từ config; thời gian tính bằng ms theo timestamp, không theo số khung):
1. NO_HAND → khung có tay: mở bộ đệm mới, `armed = True`.
2. Mỗi khung khi đang theo dõi (có tay hoặc không) được thêm vào bộ đệm NGUYÊN VẸN (landmark thô, detected, handedness, ts, W, H).
   Bộ đệm giới hạn `max_segment_ms` (bỏ phần cũ nhất; không phát).
3. ĐỨNG YÊN: M_t ≤ `still_speed`; DI CHUYỂN: M_t ≥ `move_speed` (> `still_speed`, trễ chống rung).
4. Phát ký hiệu (lý do `hold`): `armed` và đứng yên liên tục ≥ `hold_ms` và số khung có tay trong bộ đệm ≥ max(`min_sign_frames`,
   checkpoint `min_detected_frames`) → phát `SignSegment(bộ đệm)`, `armed = False`, bộ đệm làm rỗng (vẫn ghi lăn).
5. Tái kích hoạt (chống phát lặp khi giữ yên lâu): `armed = True` khi DI CHUYỂN liên tục ≥ `rearm_move_ms` (bộ đệm cắt về từ lúc bắt
   đầu di chuyển — giữ trọn chuyển động của dấu thanh) HOẶC mất tay ≥ `hand_lost_ms`.
6. Mất tay ≥ `hand_lost_ms`: nếu `armed` và đủ khung → phát (lý do `hand_lost`, cắt đuôi tại khung có tay cuối); về NO_HAND.
7. Mất tay ≥ `word_gap_ms` (config phải ≥ `hand_lost_ms`, kiểm khi nạp): phát MỘT `WordGap` (chỉ khi từ WordGap trước đã có ≥ 1 ký hiệu).
8. `flush(ts)` (hết video/thoát) = như mục 6 với lý do `end_of_stream`.
- Chữ lặp ("oo"): giữ yên KHÔNG phát lại; người ký nảy/dịch nhẹ tay (di chuyển ≥ `rearm_move_ms`) hoặc hạ tay rồi ký lại → phát lần 2.
  Ghi hướng dẫn trên HUD/tài liệu. Phím `r` = lặp chữ cái cuối (dự phòng thủ công, ghi `source: "key"`).
- `SignSegment` = {seq, raw_landmarks [T,21,3] float32 (0 khi không tay), detected [T] bool, handedness [T] str, timestamps_ms [T],
  frame_width, frame_height, t_start_ms, t_end_ms, t_emit_ms, close_reason ∈ {hold, hand_lost, end_of_stream}}; là BẢN SAO (không chia
  sẻ bộ nhớ với bộ đệm); đúng định dạng đầu vào `alphabet_clip_features`.
- Trạng thái cho HUD: `state` ∈ {no_hand, moving, holding}, `hold_progress` ∈ [0,1], `armed`.
- Thiết kế có chủ đích: chữ cái hiện SAU khi giữ yên `hold_ms` (độ trễ thiết kế, báo riêng với độ trễ xử lý).

### 3.4 Phân loại + chấp nhận token + ghép từ (`level1_core.py`)
- `load_level1_config(path)`: đọc JSON; thiếu khóa bắt buộc, thiếu `source`/`reason`, kiểu sai, `move_speed ≤ still_speed`,
  `word_gap_ms < hand_lost_ms` → `ValueError` (KHÔNG giá trị mặc định trong mã).
- `Level1Classifier.from_checkpoint(path)`: `torch.load` → đòi `classes`, `preprocessing` (thiếu → `ValueError`, như backend
  `main.py:603-605`); dựng model theo `model_type`/`hparams` y như `main.py:619-630`; `eval()`.
  `classify(segment, top_k)` → `alphabet_clip_features(raw, detected, handedness, W/H, ts, preprocessing, model_type)` → softmax → dict
  CÙNG khóa và cách làm tròn với `/sequence` (`prediction`, `prediction_kind`, `confidence`, `candidates`, `frames`, `detected_frames`,
  `model_type`, `checkpoint`) + `status: "ok"`. Ít khung (ValueError của `alphabet_clip_features`) → `{"status": "too_few_frames"}`;
  đặc trưng/xác suất không hữu hạn → `{"status": "invalid"}` — không token trong cả hai trường hợp.
- `Level1Speller(config)`: `on_result(seq, r)` → nhận token nếu `status == "ok"` và `confidence ≥ accept_confidence`, ngược lại lưu là
  `rejected` (HUD hiện mờ, KHÔNG thêm). `on_word_gap()` → thêm " " nếu token cuối tồn tại và không phải " ". Phím: `Backspace` xóa
  token cuối, `Space` thêm " ", `a` chấp nhận ứng viên bị từ chối gần nhất, `r` lặp chữ cái cuối, `c` xóa hết, `p` tạm dừng/tiếp tục
  tách, `q`/`Esc` thoát. Văn bản = `compose(tokens)["text"]` (không sửa/đoán chữ); `warnings` hiện trên HUD. Mọi thay đổi token ghi vào
  nhật ký sự kiện JSON kèm `source: "model" | "key"`.
- Thứ tự: Speller xử lý sự kiện đúng thứ tự phát; `WordGap` phát sau segment k chờ kết quả của k.

### 3.5 Độ trễ (đo, không ước đoán)
Chặng (ms, `time.perf_counter`): `capture_age` (t_cap → bắt đầu xử lý), `mediapipe`, `segmenter`, `draw_landmarks`, `hud`, `display`
(imshow + waitKey), `frame_total` (t_cap → sau imshow); theo ký hiệu: `classify` (đặc trưng + model), `emit_to_token` (t_emit → token
lên HUD). Đếm: khung đọc, khung xử lý, khung bỏ (bị ghi đè), fps xử lý (từ timestamp; n < 2 → 0.0). HUD: p50 lăn mỗi chặng + fps +
khung bỏ. JSON (khi thoát hoặc hết video): {generated_by: {command, git_commit, code_dirty, utc, python, mediapipe, cv2, torch, numpy,
cpu, os}, config (toàn bộ + sha256 file), checkpoint {path, sha256}, source {kind: webcam|video, id, mode: headless|paced|gui}, frame_size,
camera_props (giá trị đọc lại sau khi set), warmup {mediapipe_first_ms, classify_first_ms}, stages {tên: {n, mean, p50, p95}}, counts,
tokens, text, warnings, segments [{seq, t_start_ms, t_end_ms, close_reason, frames, detected_frames, prediction, confidence, accepted}],
events, expected (nếu có `--expected`), note}. Thống kê: n = 0 → mean/p50/p95 = null; phân vị theo `numpy.percentile` (linear).
Không đo được: trễ cảm biến/driver camera và màn hình — ghi trong `note` + tài liệu.
Tối ưu đã chọn (KHÔNG đổi tham số MediaPipe — `model_complexity` giữ 1 như train): luồng camera riêng + lấy khung mới nhất,
`CAP_PROP_BUFFERSIZE` = giá trị config (ghi giá trị đọc lại vào JSON), API camera chọn qua config `camera_api` ("dshow"/"msmf"/"any"),
phân loại ở worker, cache lớp chữ HUD (chỉ vẽ lại PIL khi nội dung đổi), warm-up khi khởi động.

### 3.6 Hiệu chỉnh trên clip TRAIN (KHÔNG phải độ chính xác)
`scripts/level1_segment_report.py` đọc `manifest.csv` + npz, CHỈ source hauuto (= dữ liệu train của checkpoint), chạy
`Level1SignSegmenter` trên từng clip (timestamp i×1000/fps của manifest; `flush` ở cuối clip), ghi
`reports/level1_realtime_<D>/segmenter_train_clips.json`: phân phối M_t theo nhóm chữ / dấu thanh, đoạn đứng yên dài nhất mỗi clip,
số segment mỗi clip, close_reason, và nhãn model trên cửa sổ segment so với nhãn model trên TRỌN clip (đầu vào lúc train) — gọi là
"đồng thuận cửa sổ", KHÔNG phải độ chính xác.
Quy tắc hiệu chỉnh ĐẶT TRƯỚC (script tính, coder không gõ số):
- `still_speed` = phân vị 90 (qua các clip CHỮ CÁI) của trung vị M_t trong từng clip.
- `move_speed` = `still_speed` × `move_over_still_ratio` (design).
- `hold_ms` = min(`hold_ms_design`, phân vị 10 của "đoạn đứng yên dài nhất" qua các clip chữ cái).
- Các khóa còn lại (`motion_window_ms`, `rearm_move_ms`, `hand_lost_ms`, `word_gap_ms`, `max_segment_ms`, `accept_confidence`,
  `min_sign_frames`, `move_over_still_ratio`, `hold_ms_design`, camera/hiển thị) là giá trị THIẾT KẾ, `source: "design"`, kèm lý do;
  không gọi là số đo. Coder chọn giá trị thiết kế ban đầu ở B1 và ghi lý do; không chỉnh theo kết quả replay §3.7.
- `--write-config` ghi giá trị tính được vào config với `source: "calibrated: reports/level1_realtime_<D>/segmenter_train_clips.json@<commit>"`.
Luồng ghép có kiểm soát từ landmark THẬT (npz train): nối các clip cùng người ký, chèn khoảng không tay (None) dài cho trước giữa các
clip, để kiểm logic tách + ghép (đầu ra: số segment, chuỗi token so với nhãn model trên trọn từng clip). JSON ghi rõ: "ghép có kiểm soát
từ clip train; không phải ký liên tục thật".

### 3.7 Replay clip thật qua app (headless)
`scripts/level1_replay_clips.py` chọn CÙNG 10 clip của `scripts/hand_live_check.select_clips(rows, 8, 0)` (8 hauuto train + 2 qipedc đã dùng
ở AC5 kế hoạch 06 — quyết định người dùng 2026-10-01 19:22), chạy app headless (video thật → MediaPipe → tách → phân loại → ghép), ghi
`reports/level1_realtime_<D>/replay_clips.json` (mỗi clip: số segment, nhãn, confidence, close_reason, thống kê chặng); một lần
`--pace realtime` trên clip có nhiều khung nhất trong 10 clip → `replay_paced.json`; đo E2 (phiên liên tục qua 2 clip nối, xem AC-E2) →
`equivalence_continuous.json`; `--summary` → `SUMMARY.md` (bảng số sinh từ các JSON trên + JSON phiên webcam nếu có, kèm đường dẫn +
commit). JSON ghi chú bắt buộc: "hauuto = dữ liệu train; qipedc = clip test đã dùng ở kế hoạch 06; không phải độ chính xác; không dùng
để chỉnh tham số".

## 4. Chia việc (mỗi bước 1 commit `15: B<n> …`, test đỏ trước, chạy AC-G + AC1-ngắn trước mỗi commit)

Ước lượng giờ công coder (chưa gồm thời gian chạy test dài). Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`.
File tạm/log: `_work/_plan15/`. Commit bằng `git add <file cụ thể>` (không cuốn thay đổi chưa commit của người dùng); trước commit chạy
`node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLAUDE.md).

| Bước | Nội dung | Phụ thuộc | Giờ |
|---|---|---|---|
| **B0** | Mốc: ghi HEAD, sha256 checkpoint, `git status` (không đụng thay đổi của người dùng); chạy AC1-ngắn + AC1-đủ (31 module) → log `_work/_plan15/b0_*.log`, ghi số Ran/OK/FAIL/ERROR/skip từng test vào `docs/plans/15-progress.md`. Không sửa mã. | — | 0,5 |
| **B1** | `configs/level1_realtime.json` (giá trị thiết kế + lý do) + `src/inference/level1_segmenter.py` + `load_level1_config` (chốt một nơi, ghi trong 15-progress) + `tests/test_level1_segmenter.py` (AC-S, viết trước, đỏ) + `tests/test_level1_guard.py` (AC-G, danh sách file mới tăng dần). | B0 | 2 |
| **B2** | `src/inference/level1_core.py` (`Level1Classifier`, `Level1Speller`) + `src/inference/level1_timing.py` + `tests/test_level1_core.py` (AC-C, AC-T). | B1 | 1,5 |
| **B3 (MVP)** | `level1_demo.py`: luồng camera lấy khung mới nhất, vòng chính, vẽ chấm trên khung đã xử lý, HUD PIL (font tiếng Việt: `--font` hoặc tìm trong danh sách đường dẫn font Windows; không thấy → thoát với thông báo, không vẽ chữ hỏng), phím §3.4, worker phân loại, `--source`, `--headless`, `--out-json`, `--config`, `--checkpoint`, `--expected`, `--display-mirror`; JSON tối thiểu (tokens, text, segments, stages cơ bản) + `tests/test_level1_demo.py` (AC-D). Sau B3: orchestrator báo người dùng có thể chạy thử (U1). | B2 | 2 |
| **B4** | `tests/test_level1_equivalence.py` (AC-E1, AC-E3). Nếu E1 không bằng hệt → DỪNG (§7). | B3 | 1,5 |
| **B5** | Hoàn thiện đo độ trễ (§3.5): đủ chặng, warm-up tách riêng, HUD p50 lăn, `--pace realtime`, `camera_api`/`CAP_PROP_BUFFERSIZE`, cache HUD; test AC-L. | B3 | 1,5 |
| **B6a** | `scripts/level1_segment_report.py` (§3.6) + test nhỏ (chạy trên 2 npz, khóa JSON, quy tắc hiệu chỉnh tính đúng trên dãy số cho trước). | B1, B2 | 1,5 |
| **B6b** | Chạy R1 tại commit sạch → JSON; áp `--write-config` (commit config riêng, ghi giá trị cũ → mới trong 15-progress); chạy lại AC-S/AC-C. Kiểm điểm dừng AC-R1. | B6a | 0,5 |
| **B7** | `scripts/level1_replay_clips.py` (§3.7: replay 10 clip, paced, E2, `--summary`) + test nhỏ; chạy tại commit sạch → JSON + SUMMARY.md. | B4, B5, B6b | 1,5 |
| **B8** | `docs/level1_desktop.md` (cách chạy, phím, kiến trúc §3.2, chặng §3.5, hướng dẫn chữ lặp, Giới hạn §6.3, link JSON/SUMMARY; không gõ số đo); AC1-đủ cuối; ghi 15-progress + 1 dòng progress_log. | B7 | 1 |
| **B9** | Sau khi người dùng chạy U2: các JSON phiên webcam (app tự ghi vào `reports/level1_realtime_<D>/`) được commit, chạy lại `--summary`. Không chỉnh tham số theo phiên này. | B8, U2 | 0,5 |

Tổng: **~14 giờ công** (MVP B0–B3 ≈ 6 giờ). Nếu ngân sách cạn, thứ tự cắt (từ cuối lên): B9 → B8 rút gọn (chỉ cách chạy + Giới
hạn) → B6a/B6b (giữ giá trị thiết kế, ghi rõ "chưa hiệu chỉnh" trong Giới hạn). KHÔNG cắt B4 (DoD 7) và B5 (yêu cầu đo của người dùng).
Review: vslt-reviewer sau B4 (giữa, chỉ AC-S/C/D/E/G) nếu ngân sách cho phép, và sau B8 (cuối).
Backlog ghi lại (không làm trong 15): `README.md:203` `--webcam` → `--source 0` + dòng hướng dẫn `level1_demo.py` (README thuộc kế hoạch
14/việc 8); thêm `level1_demo.py` vào `ENTRYPOINTS` của guard chính khi kế hoạch 11 tiếp tục (thắt chặt, không nới); web dùng lại lõi
(MediaPipe JS chỉ kèm test tương đương — quyết định 10:45).

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

**AC0 — Phạm vi.** `git diff --name-only <B0>..HEAD` giới hạn ở commit `^(WIP )?15:` chỉ gồm file trong §3.1. `sha256(checkpoints/alphabet_best.pt)`
trước = sau = `a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2`. `backend/main.py` không đổi (model mặc định
`ALPHABET_CKPT` giữ nguyên). Không commit video, frame, landmark của người dùng.

**AC1 — Hồi quy.**
- AC1-ngắn (mỗi bước): `python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_fingerspelling_api
  tests.test_fingerspelling_compose tests.test_fingerspelling_limits tests.test_fingerspelling_deployed tests.test_hand_landmarks_ws
  tests.test_hand_live_equivalence tests.test_alphabet_ckpt_provenance tests.test_status_privacy tests.test_backend_source_guard
  tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_equivalence tests.test_level1_guard -v`
  (module chưa tồn tại ở bước sớm thì bỏ khỏi lệnh, ghi rõ) → mọi test có ở B0 cùng trạng thái như B0; test mới OK, 0 skip
  (dữ liệu/checkpoint có trên máy).
- AC1-đủ (B0 và B8): lệnh 31 module nguyên văn `docs/plans/06-viec5-frontend.md:1028` + 5 module `tests.test_level1_*` → từng test
  cùng trạng thái như B0 (lỗi có sẵn ghi ở STATE: setUpClass `test_translation_core` thiếu ViT5, skip `stgcn_best.pt`), module mới OK.
- `tests.test_hand_landmarks_ws ... test_reset_segments_and_graphs` đã biết chập chờn (STATE): nếu FAIL, chạy riêng 3 lần, ghi 3 log;
  không sửa/skip test đó.

**AC-S — Bộ tách (dữ liệu điều khiển tạo TRONG test, docstring ghi "chuỗi landmark tạo có kiểm soát để kiểm logic, không phải dữ
liệu thật"; tham số lấy từ một config test riêng trong test, không từ file config thật).** Mỗi ca là một test:
S1 tay xuất hiện, di chuyển, rồi đứng yên ≥ hold → đúng 1 segment `hold`, t_start = khung có tay đầu tiên, t_emit = khung đầu tiên đạt
đủ hold; S2 giữ yên thêm nhiều lần hold → vẫn 1; S3 giữ → di chuyển ≥ rearm → giữ → đúng 2 (chữ lặp); S4 di chuyển < rearm giữa hai lần
giữ → 1; S5 chuyển động rồi mất tay ≥ hand_lost (chưa từng đứng yên) → 1 segment `hand_lost`, đuôi cắt tại khung có tay cuối;
S6 mất tay ≥ word_gap → đúng 1 `WordGap` sau segment, mất tay tiếp → không thêm; tay biến mất khi chưa có segment nào → 0 WordGap;
S7 rung nhỏ dưới still → tính là đứng yên; S8 khoảng cách timestamp KHÔNG đều (cùng chuyển động theo thời gian, hai nhịp khung khác nhau)
→ cùng số segment và t_emit lệch ≤ một khoảng khung; S9 bộ đệm dài hơn max_segment → segment chỉ chứa phần cuối ≤ max_segment;
S10 một khung có tay duy nhất → M = None, không chia 0; timestamp bằng hoặc giảm → ValueError; S11 nội dung segment == đúng các khung đã
push (array_equal landmark, detected, handedness, ts) và là bản sao (sửa segment không đổi bộ đệm); S12 ít khung có tay hơn min → không
phát; S13 `flush` → `end_of_stream`.

**AC-C — Lõi.** C1: trên ≥ 3 npz hauuto (chọn cố định theo sample_id, ghi trong test), body dựng từ npz như `hand_live_check.body_from_npz`
→ `Level1Classifier.classify(segment)` và `POST /api/fingerspelling/sequence` (TestClient, checkpoint triển khai) có `prediction`,
`prediction_kind`, `confidence`, `candidates` BẰNG NHAU (==). C2 checkpoint thiếu `classes`/`preprocessing` → ValueError. C3 < min khung
→ `too_few_frames`, không token. C4 ngưỡng: confidence == accept_confidence → nhận; nhỏ hơn → rejected; `a` nhận lại đúng ứng viên đó.
C5 Backspace/Space/c/r đúng như §3.4, Backspace trên rỗng không lỗi. C6 sau mọi thao tác `text == compose(tokens)["text"]`; ví dụ token
["b","a","dấu sắc"] → "bá", ["m","e","dấu nặng"," ","c","a","dấu sắc"] → "mẹ cá". C7 WordGap phát sau segment k chưa có kết quả →
" " nằm SAU token của k. C8 `load_level1_config`: thiếu khóa / thiếu source/reason / move ≤ still / word_gap < hand_lost → ValueError.
**AC-T — Thống kê:** dãy cho trước → n, mean, p50, p95 == `numpy` tương ứng; n = 0 → null; fps n < 2 → 0.0.

**AC-D — App.** D1 `python level1_demo.py --help` liệt kê `--source --headless --out-json --config --checkpoint --pace --expected
--display-mirror --font`. D2 `python level1_demo.py --source data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4 --headless --out-json
_work/_plan15/d2.json` exit 0; JSON có đủ khóa §3.5; mỗi segment trong JSON có prediction == `Level1Classifier.classify` chạy lại trên
cùng segment; chạy 2 lần → `tokens`, `segments` (bỏ thời gian) giống hệt. D3 lớp ô khung mới nhất (test bằng nguồn khung đọc từ video thật
qua đúng lớp đọc của app, không webcam): consumer chậm → nhận khung có seq mới nhất, `dropped` = số khung bị ghi đè, không bao giờ trả khung
cũ hơn khung đã trả. D4 video không đọc được fps → thoát mã ≠ 0 với thông báo, không fps mặc định. D5 vòng xử lý không gọi
`classify` trên luồng chính ở chế độ GUI/paced (test: classifier chậm có chủ đích, định nghĩa TRONG test → số khung xử lý trong thời gian
đó > 1).

**AC-E — Tương đương train ↔ realtime.**
E1 (B4, bắt buộc, BẰNG HỆT): 10 clip của `hand_live_check.select_clips(rows, 8, 0)`: đọc video bằng bộ đọc của app (replay headless),
`HandLandmarkSession` mới cho mỗi clip → landmark/detected/handedness/score `array_equal` với `_extract_one` (chạy vào thư mục tạm);
segment = trọn clip → đặc trưng `array_equal` với `alphabet_clip_features` trên kết quả offline; `classify` == phản hồi `/sequence`
cho `hand_live_check.body_from_npz(offline)` (prediction, confidence, candidates). Không bằng hệt → DỪNG, không thêm dung sai.
E2 (B7, ĐO, không khẳng định): phiên liên tục (không reset) qua clip A rồi clip B (cùng người ký, 3 cặp cố định trong 10 clip) → JSON
`equivalence_continuous.json`: số khung detected khác nhau, max |Δ| landmark của B so với offline B, nhãn trọn-clip B hai cách.
Test chỉ kiểm hàm chạy trên 1 cặp và trả đủ khóa.
E3: `level1_demo.py` và `src/inference/level1_*.py` không gọi `Hands(` / `cv2.resize` / `cv2.flip` trước `process` (kiểm AST: `Hands(`
và `cv2.resize` không xuất hiện; `cv2.flip` chỉ trong hàm hiển thị); frame đưa vào `process` là đúng đối tượng đã đọc (test spy).

**AC-G — Guard DoD 7.** G1 `python -m unittest tests.test_backend_source_guard -v` OK, KNOWN/ALLOWED không đổi (file không sửa).
G2 `tests/test_level1_guard.py`: `serving_closure(PROJECT_ROOT, ("level1_demo.py",))` + `scripts/level1_*.py` không nằm trong closure;
quét closure với `ALL_RULES` bằng `scan_source` → 0 finding ở file mới của 15; finding ở file khác trong closure chỉ được là khóa đã có
trong `ALLOWED` của guard chính với cùng số đếm (0 khóa KNOWN). G3 tự kiểm: chèn `latency_ms = 12.5` vào bản sao chuỗi `level1_core.py`
→ `scan_source` báo D-binding (guard thật sự đọc file).

**AC-L — Độ trễ.** L1 JSON của D2 và `replay_paced.json` có `stages` cho đủ 7 chặng khung + 2 chặng ký hiệu, mỗi chặng {n, mean, p50, p95};
`mediapipe.n` = số khung xử lý; `warmup` tách riêng. L2 `replay_paced.json`: `counts.dropped` có mặt, `source.mode == "paced"`. L3 mọi JSON
trong `reports/level1_realtime_<D>/` có `generated_by.git_commit` = commit tại lúc sinh và `code_dirty == false`.

**AC-R — Báo cáo.** R1 `segmenter_train_clips.json` phủ MỌI clip hauuto trong manifest có ≥ `min_detected_frames` khung có tay (số
in từ lần chạy, không gõ); có `note` "train data; not accuracy". **Điểm dừng đặt trước:** nếu tỉ lệ clip (chữ cái, hoặc dấu thanh, tính
riêng) cho ĐÚNG 1 segment < 0,9 sau khi áp config hiệu chỉnh → coder DỪNG, báo planner (không tự chỉnh tham số ngoài quy tắc §3.6).
R2 `replay_clips.json` có 10 clip với khóa §3.7. R3 `SUMMARY.md` sinh lại bằng `--summary` → giống hệt byte (tất định); mọi số trong
`docs/level1_desktop.md` đều chỉ là đường dẫn tới JSON/SUMMARY (kiểm: không có chuỗi khớp `\d+(\.\d+)?\s*(ms|%|fps)` trong file doc).

## 6. Rủi ro dữ liệu/ML, giới hạn trung thực, việc người dùng

### 6.1 Rủi ro
- **Lệch cửa sổ train ↔ live (lớn nhất).** Train = trọn clip một ký hiệu (~2–4 s, tay trong khung suốt clip); live = đoạn từ lúc bắt đầu
  di chuyển tới khi giữ yên `hold_ms`. Đo bằng "đồng thuận cửa sổ" ở R1 (trên train, không phải độ chính xác); nếu thấp → cân nhắc ở
  lần sửa kế hoạch (vd thêm khung giữ yên), KHÔNG train lại trong 15.
- **Nhịp khung.** `resample: frame_index` giả định khung cách đều; khi bỏ khung (latest-frame) khoảng cách không đều → méo thời gian
  của dấu thanh. Ghi fps xử lý + khung bỏ vào JSON; không đổi được cách resample nếu không train lại.
- **Tracker liên tục** khác tracker mới mỗi clip (E2 đo).
- **Rò rỉ / chọn tham số:** hiệu chỉnh CHỈ trên hauuto train; 2 clip qipedc (test) chỉ để replay, không chỉnh theo; phiên webcam của người
  dùng không dùng để chỉnh (nếu sau này cần chỉnh theo dữ liệu người dùng → lần sửa kế hoạch, số trên dữ liệu đó ghi "đã dùng để chỉnh").
- **Cỡ mẫu:** 4 người ký, cùng điều kiện quay; số replay 10 clip và vài phiên webcam là minh họa, không phải đánh giá.
- **Nguồn gốc/giấy phép:** hauuto licence unknown, internal only (`backend/main.py:593-595`, docs/data_registry.md §1b) — không phát
  hành clip/landmark; báo cáo cho thầy là dùng nội bộ.
- **Kỹ thuật:** Windows camera API khác nhau về độ trễ/bộ đệm (đo bằng `camera_api`); PIL vẽ chữ mỗi khung tốn thời gian (đo chặng `hud`,
  có cache); MediaPipe `model_complexity=1` không được hạ để nhanh hơn (lệch train).

### 6.2 Không làm trong 15
Không train lại, không đổi checkpoint/model mặc định, không sửa web/backend, không làm MediaPipe JS, không sửa README (backlog §4).

### 6.3 Giới hạn trung thực cho báo cáo (đưa vào `docs/level1_desktop.md`)
1. Model Cấp 1 train trên 4 người ký (hauuto), một bộ dữ liệu, giấy phép chưa rõ (nội bộ).
2. Số LOSO là đánh giá OFFLINE theo clip đã cắt sẵn; checkpoint triển khai = nested primary → trích số từ
   `reports/alphabet_nested_2026-09-25/primary/nested_report.json`; số 75.1% ± 8.7 ở README thuộc chạy khác (real_run), không dùng cho
   checkpoint này (`provenance.json:375-379`). Dấu thanh yếu hơn chữ cái (số theo phần trong cùng JSON).
3. Độ chính xác trên webcam CHƯA đo (trừ khi có phiên U2; khi có thì là thử nghiệm vài từ, một người, không phải đánh giá).
4. Tham số tách ký hiệu: thiết kế + hiệu chỉnh trên clip TRAIN; replay hauuto là dữ liệu train (kiểm đường chạy, không phải độ chính xác).
5. Độ trễ đo trong app (từ lúc nhận khung tới lúc hiển thị) trên MỘT máy (cấu hình trong JSON); không gồm trễ camera/màn hình; không thay
   số DoD 8 (WebSocket) của web. Độ trễ chữ hiện ra gồm `hold_ms` thiết kế.
6. Chữ lặp cần nảy tay/hạ tay; phím tay (`a`, `r`, Backspace, Space) được ghi nguồn "key" trong JSON.

### 6.4 Việc người dùng (không chặn demo)
- **U1 (sau B3, ~10 phút):** `python level1_demo.py --source 0` (thêm `--display-mirror` nếu muốn như gương). Ký lần lượt vài chữ
  (a, b, c, o, dấu sắc) rồi 2 từ "ba", "cá"; nhận xét: chấm có bám tay không, chữ có tự tách không, có phát lặp khi giữ yên không.
  Báo lại bằng lời; không cần gửi file.
- **U2 (sau B5, ~15 phút), để có số độ trễ/thử nghiệm webcam:** 4 từ × 3 lần, mỗi lần một lệnh
  `python level1_demo.py --source 0 --expected "<từ>" --out-json reports/level1_realtime_<D>/webcam_<từ-không-dấu>_<n>.json`,
  từ = "ba", "cá", "mẹ", "xoong" (có chữ lặp "oo"; nảy tay giữa hai chữ o). Ký xong nhấn `q`. JSON chỉ chứa token, sự kiện, thời gian
  và thống kê; app KHÔNG ghi video/khung/landmark của người dùng.
- **U3 (chỉ khi U1 cho thấy tách sai nhiều):** báo orchestrator → planner lập lần sửa (có thể thêm cờ ghi landmark ra `_work/`, ngoài
  repo, để người dùng quay ~2 phút ký tự do phục vụ chỉnh tham số). Coder không tự chỉnh theo cảm nhận.

## 7. Điểm dừng

Không có điểm dừng bắt buộc khi BẮT ĐẦU: không đổi model mặc định (checkpoint triển khai giữ nguyên, AC0), không cần dữ liệu người dùng
để có demo (U1–U3 không chặn), không đụng thay đổi chưa commit của người dùng (chỉ file MỚI; coder dùng `git add <file cụ thể>`), không
hành động không hoàn tác, không xóa file.

Điểm dừng có điều kiện (coder dừng, ghi 15-progress, báo orchestrator → planner):
1. AC-E1 không bằng hệt (lệch extractor/tiền xử lý) — có thể là vấn đề dữ liệu mới → báo người dùng theo autopilot §5.
2. AC-R1: tỉ lệ đúng-1-segment < 0,9 (chữ cái hoặc dấu thanh) sau hiệu chỉnh.
3. Cần sửa file/symbol có sẵn (§3.1), cần cài gói mới (Pillow/opencv đã có trong `.venv` vì `realtime_demo.py` dùng; nếu thiếu → dừng),
   hoặc không có font tiếng Việt trên máy.
4. Test cũ đổi trạng thái so với B0 mà không phải test chập chờn đã biết.
5. Thiếu dữ liệu cục bộ (video hauuto/qipedc, manifest, checkpoint) làm test mới skip — không được coi là PASS.
