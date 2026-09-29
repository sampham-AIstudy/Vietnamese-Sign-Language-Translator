# Phase 12: FastAPI + React — hợp đồng API (REST + WebSocket)
**Vietnamese Sign Language Translator (VSLT)** — cập nhật theo kế hoạch 04 (WS v2), 05 (`dropped_frames`) và 06 (Việc 5).

Tài liệu này mô tả hợp đồng; không chứa số đo hiệu năng nào. Nguồn sự thật là `backend/main.py` và các test hợp đồng
(`tests/test_ws_live_contract.py`, `tests/test_hand_landmarks_ws.py`, `tests/test_cors_origin_bind.py`,
`tests/test_fingerspelling_*.py`). `tests/test_frontend_contract.py` kiểm tài liệu này chứa mọi mã lỗi và lý do bỏ đoạn
mà code phát ra.

---

## 1. Cách chạy

- `start_fullstack.ps1`: backend `uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload --ws-max-size 1048576`,
  rồi frontend `npm run dev` (Vite, cổng 3000, `strictPort: true` — cổng bận thì Vite báo lỗi, không nhảy sang 3001).
- Backend chỉ nghe `127.0.0.1` (không mở ra mạng LAN). Vite cũng chỉ nghe localhost (không có khóa `host`).
- Trình duyệt mở `http://localhost:3000/`. Vite proxy `/api` → `http://127.0.0.1:8000` và `/ws` → `ws://127.0.0.1:8000`
  (`frontend/vite.config.js`), nên với trình duyệt mọi REST/WS đều cùng origin với trang. Frontend dựng URL WS bằng
  `wsUrl(window.location, path)` (`frontend/src/lib/ws.js`) → `ws://localhost:3000/ws/...`; không có cổng backend nào
  viết cứng trong `frontend/src`.
- Model Cấp 2 mặc định KHÔNG đổi (`VSL_MODEL_TYPE` không đặt → `stgcn`, đường `legacy`). Ứng viên GATE:
  `VSL_MODEL_TYPE=stgcn_h360` (đường `harmonized_v1`), chỉ đặt trong môi trường của tiến trình thử.
- Smoke test thủ công (TestClient, model thật): `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py`
  (chạy cả với `VSL_MODEL_TYPE=stgcn_h360`).

## 2. CORS, Origin của WebSocket

- Quyết định 2026-09-28: chỉ origin dev, không bao giờ `*` kèm credentials.
- `VSL_CORS_ORIGINS` (tùy chọn): danh sách origin chính xác, phân tách bằng dấu phẩy. Không đặt / rỗng → mặc định
  `http://localhost:3000`, `http://127.0.0.1:3000`. Phần tử `*`, rỗng, không bắt đầu bằng `http://`/`https://`, hoặc có
  `/` ở cuối → backend KHÔNG khởi động (lỗi lúc import, không lặng lẽ mở rộng).
- `CORSMiddleware`: `allow_origins` = danh sách trên, `allow_credentials=False`, `allow_methods=["GET","POST"]`,
  `allow_headers=["Content-Type"]`. Qua proxy Vite, CORS không tham gia; CORS chỉ có ý nghĩa khi trang origin khác gọi
  thẳng cổng 8000.
- WebSocket (`/ws/live-stream`, `/ws/hand-landmarks`): header `Origin` được kiểm TRƯỚC `accept()`:
  - không có `Origin` (client không phải trình duyệt: smoke test, script đo) → cho qua;
  - có `Origin` → phải khớp CHÍNH XÁC một origin được phép (so sánh phân biệt hoa thường; `null` bị từ chối);
  - bị từ chối → đóng mã **1008** (bắt tay trả 403), không gửi `session_info`, không nạp model.

## 3. REST

| Endpoint | Ý nghĩa |
|---|---|
| `GET /api/health` (= `/health`, `/api/status`) | 200 `status: "ok"` + model Cấp 2 (`model_type`, `pipeline`, `checkpoint`, `is_default_model`, ...); **503** `status: "model_unavailable"` khi model đã cấu hình không phục vụ được (thiếu file, sha256 sai, preprocessing không dùng được) — không bao giờ lặng lẽ đổi model. |
| `GET /model/info`, `GET /api/classes` | Thông tin/lớp của model Cấp 2; 503 như trên. |
| `GET /api/fingerspelling/status` | Cấp 1: `available`, `classes`, `num_classes`, `preprocessing`, `model_type`, `trained_on` (chỉ `{source, n_signers}` hoặc null), `data_provenance`, `message`. |
| `POST /api/fingerspelling/sequence` | Cấp 1: phân loại MỘT ký hiệu từ chuỗi landmark bàn tay (hợp đồng kế hoạch 03). |
| `POST /api/fingerspelling/compose` | Ghép token đã chấp nhận (chữ, dấu thanh, `" "`) thành chữ tiếng Việt: `{text, syllables, warnings, tone_style}`. |
| `POST /api/fingerspelling` | Endpoint ảnh cũ: luôn **409** (frontend không gọi nữa). |

`POST /api/fingerspelling/sequence` — body:
`{"landmarks": [ [[x,y,z]×21] | null | [] ] (1..300 phần tử), "handedness": ["Left"|"Right"|""], "timestamps_ms": [số không
giảm]?, "frame_width", "frame_height", "source_mirrored": false, "top_k": 1..10}`. Mỗi khung có tay phải là 21 điểm số hữu
hạn, |v| ≤ 10, không trùng hệt; khung không tay gửi `null` (không bao giờ gửi khung toàn 0). Trả 200
`{prediction, prediction_kind, confidence, candidates:[{class, confidence, kind}], frames, detected_frames, model_type,
checkpoint}`; **413** body > 1 MiB; **422** hai dạng body `{"detail": "..."}` hoặc `{"detail": [{loc, msg, type}]}`;
**503** chưa có model Cấp 1. `confidence` là độ tin cậy của model, không phải độ chính xác.

## 4. WebSocket `/ws/live-stream` — "Ký từ" (Cấp 2), `protocol_version` 2

Giới hạn chung (hằng trong `backend/main.py`, áp cho cả hai đường): message ≤ 1 048 576 byte (UTF-8 của text hoặc độ dài
binary); chỉ JPEG/PNG (kiểm magic bytes, kích thước đọc từ header TRƯỚC khi giải mã); cạnh ảnh ≤ 1920. Lỗi của MỘT
message không đóng phiên, trừ `message_too_large` (đóng **1009**) và `model_unavailable` (đóng **1011**). `detail` ≤ 200 ký
tự và không lặp lại dữ liệu client gửi.

**Client → server**

| Message | Dạng |
|---|---|
| Frame (text) | `{"image": "data:image/jpeg;base64,..." \| base64, "timestamp": ms?, "config": {"confidence_threshold": 0..1}?}` |
| Frame (binary) | byte JPEG/PNG; không có timestamp (nguồn thời gian là server) |
| Điều khiển | `{"type": "control", "action": "reset"}` |

Đường `harmonized_v1`: nguồn timestamp của phiên cố định theo frame hợp lệ đầu tiên (client nếu có `timestamp`, ngược lại
server); frame của nguồn kia hoặc timestamp client không tăng ngặt → `bad_timestamp`. Frontend luôn gửi text JSON có
`timestamp = performance.timeOrigin + performance.now()` (đồng hồ đơn điệu).

**Server → client**

1. `session_info` — luôn là message ĐẦU TIÊN: `{"type":"session_info","protocol_version":2,"pipeline":"legacy"|"harmonized_v1",
   "model":{model_type, checkpoint, checkpoint_sha256, is_default, num_classes}, "preprocessing":{...}, "segmenter":{...}|null,
   "limits":{max_message_bytes, max_frame_side, min_frame_height|null}}`.
2. `frame_result` — một message cho mỗi frame được xử lý.
   - `legacy`: giữ mọi khóa cũ (`gloss`, `prediction`, `confidence`, `top5`, `latency_ms`, `fps`, `status` IDLE/DETECTING/
     CONFIRMED, `sentence`, `is_confirmed`, `translated_text`, `oov_warning`, `is_signing`, `hand_detected`, `buffer_fill`,
     `buffer_capacity`, `landmarks`, `metrics{client_timestamp, decode_ms, server_preprocess_ms, server_infer_ms,
     postprocess_ms, server_total_ms, server_fps, buffer_frames}`) + `type`, `pipeline`.
   - `harmonized_v1`: KHÔNG BAO GIỜ mang dự đoán (`prediction/gloss/confidence` null, `top5` rỗng); `status`
     IDLE/RECORDING/WAIT_REST, `segment{state, segment_id, recording_s, frames, max_sign_s}`, `frame_seq`, `received_seq`,
     `dropped_frames` (số frame hợp lệ bị ghi đè slot, cộng dồn cả phiên), `hand_detected`, `hand_active`, `landmarks`,
     `metrics{client_timestamp, timestamp_source, decode_ms, extract_ms, segment_ms, server_total_ms, server_fps}`.
3. `sign_result` (chỉ `harmonized_v1`) — gửi TRƯỚC `frame_result` của frame kích hoạt (cùng `frame_seq`):
   `{segment_id, frame_seq, prediction, gloss, confidence, top5:[{gloss, confidence}], end_reason:"rest",
   segment{start_s, end_s, duration_s, frames, effective_fps, dropped_frames, active_start_s, active_end_s},
   model{...}, metrics{harmonize_ms, infer_ms, finalize_ms, trigger_client_timestamp, rest_hold_s}}`.
   `segment.dropped_frames` (kế hoạch 05) = số frame HỢP LỆ bị ghi đè slot (worker bận) giữa frame đầu và frame cuối của
   ký hiệu; message lỗi, điều khiển, rỗng KHÔNG được đếm.
4. `sign_discarded` (chỉ `harmonized_v1`): `{segment_id, frame_seq, reason, segment{duration_s, frames}}`, `reason` ∈
   `too_short`, `too_long`, `stream_gap`, `frame_size_changed`, `no_hand_frames`, `reset`.
5. `error`: `{"type":"error","code","detail","received_seq"}`, `code` ∈ `message_too_large`, `bad_message`, `bad_config`,
   `bad_timestamp`, `decode_failed`, `unsupported_format`, `frame_too_large`, `frame_too_small`, `model_unavailable`.

Thay đổi so với giao thức cũ (review 04 mục 11): message đầu là `session_info` (không còn là dự đoán); frame lỗi trả
`error{code}` thay cho `status: "ERROR"`; bỏ khóa `frame`/`data`.

Frontend (`frontend/src/lib/liveProtocol.js`, `reduceLive`) xử lý theo `type`; `protocol_version` ≠ 2 → báo
`protocol_mismatch`; `message_too_large`/`model_unavailable` → dừng phiên; `type` lạ được đếm, không làm hỏng UI. Mỗi
`sign_result` được hiện đúng như server gửi (không gộp, không khử trùng), có nút "Xóa từ cuối".

## 5. WebSocket `/ws/hand-landmarks` — "Đánh vần" (Cấp 1), `protocol_version` 1

Server trích landmark bàn tay của từng frame webcam bằng đúng extractor lúc train Cấp 1 (`src/inference/hand_live.py`:
`mp.solutions.hands.Hands` với `static_image_mode=False, max_num_hands=1, model_complexity=1, min_detection_confidence=0.5,
min_tracking_confidence=0.5`, mediapipe 0.10.14; frame gốc không resize, không lật; tracker mới cho mỗi ký hiệu). Tương
đương với `scripts/extract_hands_batch.py::_extract_one` được kiểm bit-by-bit (`tests/test_hand_live_equivalence.py`).
Client ghép các `hand_frame` của MỘT ký hiệu và gọi `POST /api/fingerspelling/sequence` (§3); server không phân loại ở đây.

- Client → server: như `/ws/live-stream` (text JSON `{"image","timestamp"?}`, base64/data URL trần, binary JPEG/PNG,
  `{"type":"control","action":"reset"}`); `config` hợp lệ bị bỏ qua, sai → `bad_config`.
- Xử lý TUẦN TỰ: mỗi message xử lý xong mới nhận message sau; server không bỏ frame nào.
- Server → client:
  1. `session_info` (đầu tiên): `{"type":"session_info","endpoint":"hand-landmarks","protocol_version":1,
     "extractor":{"name":"mp.solutions.hands","mediapipe_version", ...tham số Hands}, "limits":{max_message_bytes,
     max_frame_side, max_frames_per_segment: 300}}`. Segment 0 bắt đầu với tracker mới.
  2. `reset_done`: `{"type":"reset_done","segment_id"}` — gửi SAU khi tracker mới đã tạo; `segment_id` +1 mỗi reset;
     `frame_seq` bắt đầu lại từ 0.
  3. `hand_frame`: `{"type":"hand_frame","segment_id","frame_seq","received_seq","client_timestamp"|null,"frame_width",
     "frame_height","landmarks":[[x,y,z]×21]|null,"handedness":"Left"|"Right"|"","handedness_score"|null,
     "metrics":{decode_ms, extract_ms, server_total_ms}}` — landmark float32 của MediaPipe đổi sang số JSON không làm tròn.
  4. `error`: như §4 (`message_too_large` → đóng 1009; không tạo được MediaPipe → `model_unavailable` + đóng 1011); frame
     lỗi không tăng `frame_seq` và không đi vào tracker.

Frontend (`frontend/src/components/Fingerspelling.jsx`, `frontend/src/lib/fingerspelling.js`): Ghi → `reset` → chờ
`reset_done` → gửi frame JPEG chất lượng 0.9 (canvas không lật) ở 24 fps, tối đa 2 frame đang bay; Dừng → chờ frame đang
bay (≤ 2 s) → `buildSequenceBody` (chỉ segment hiện tại, theo `frame_seq`, khung không tay = `null`, `source_mirrored:
false`) → `/sequence` → ứng viên → người dùng Thêm → `/compose`; chữ hiển thị CHỈ lấy từ `text` của server.
(24 fps, 0.9, 2 là giá trị thiết kế, chưa đo.)

## 6. Trường để đo độ trễ (DoD 8 — chưa đo trong việc này)

- Ký từ (`harmonized_v1`): độ trễ phía máy = lúc client nhận `sign_result` − `metrics.trigger_client_timestamp` (cùng đồng
  hồ client; UI hiện `client_e2e_ms`); độ trễ người dùng cảm nhận = độ trễ phía máy + `rest_hold_s`. Legacy:
  `metrics.client_timestamp` của từng `frame_result`.
- Đánh vần: mốc client từ lúc bấm Dừng tới khi có phản hồi `/sequence` (UI hiện "phản hồi sau Dừng"), cộng `metrics`
  (`decode_ms`, `extract_ms`, `server_total_ms`) của từng `hand_frame`.

## 7. Giới hạn

- Ký hiệu có nhịp nghỉ giữa chừng có thể bị phát 2 lần thành hai `sign_result` (quan sát trên clip W03251B, n = 1; review
  04 mục 9). UI không khử trùng để không nuốt từ lặp thật; người dùng dùng "Xóa từ cuối". Xử lý thuộc kế hoạch riêng
  "segmenter live".
- Tham số segmenter (`SEGMENTER_DEFAULT`) chưa được chỉnh trên dữ liệu webcam; tốc độ theo dt từng frame (review 04 mục 8)
  chưa làm.
- Landmark Cấp 1 live được trích từ frame JPEG (chất lượng 0.9) do trình duyệt nén, trong khi lúc train trích từ frame giải
  mã mp4; ảnh hưởng đo được ở mục dưới.
- Origin check chỉ chặn trang web khác origin trong trình duyệt; nó không chặn client không phải trình duyệt (script tự
  viết không gửi `Origin`). Bảo vệ chính là bind `127.0.0.1`. Chưa giới hạn số kết nối WS đồng thời (mỗi kết nối
  `/ws/hand-landmarks` giữ một graph MediaPipe).
- `detail` của 503 có thể chứa tên file checkpoint (chỉ lộ trên máy cục bộ sau khi bind 127.0.0.1; backlog).
- Ký từ legacy dùng JPEG chất lượng 0.75 như trước; ảnh hưởng nén/rơi frame thật lên Cấp 2 chưa đo.

### Lệch nguồn landmark Cấp 1 đo được (AC6)

Nguồn: `reports/fingerspell_live_2026-09-29/hand_live_check.json` (`generated_by.git_commit`
`e58d02535fde94a36a1613798f1675509ae4f139`, `code_dirty: false`), mẫu 10 clip (8 hauuto + 2 qipedc). Chỉ ghi nhận, không
có ngưỡng.

- Đường live (PNG) so với `_extract_one` chạy trên cùng máy: bằng hệt ở cả 10 clip (sai lệch 0).
- (i) Landmark lúc train (npz trích trên Kaggle/Linux) so với trích lại trên máy này (Windows): KHÔNG bằng hệt. Cả 10 clip
  có sai lệch khác 0; 1 clip lệch cờ phát hiện tay (`hauuto_aw_khoi_A_003`, 88/90 frame khớp); sai lệch tọa độ lớn nhất
  0.2297654151916504 (đơn vị ảnh chuẩn hóa — cỡ cả bàn tay ở vài frame tracker bắt/nhả tay khác nhau).
- (ii) Frame JPEG chất lượng 90 (bộ nén cv2, không phải trình duyệt) so với PNG: 2 clip lệch cờ phát hiện tay
  (`hauuto_aw_khoi_A_003` 86/90, `qipedc_D0489` 87/93); sai lệch tọa độ lớn nhất 0.24034595489501953.
- Nhãn top-1 của `/sequence` trùng nhau giữa live PNG, live JPEG và npz Kaggle ở cả 10 clip — top-1 trùng trên 10 clip
  TRAIN, không chứng minh bền vững (hauuto là dữ liệu train của model Cấp 1; đây không phải độ chính xác).
