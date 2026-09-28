# Kế hoạch 06 — Việc 5: nối frontend với backend (Đánh vần Cấp 1 + Ký từ WS v2)

- Nhánh: feat/vslt-complete | HEAD khi lập: 19d02bf | Ngày: 2026-09-29
- Backlog: docs/STATE.md "Backlog còn lại" mục 2; autopilot.md backlog gốc mục 3.
- **Không có điểm dừng CẦN NGƯỜI DÙNG trước khi code** (xem §7; chỉ có điểm dừng có điều kiện trong lúc làm).

## 1. Mục tiêu và DoD

**Mục tiêu.** Frontend React dùng được hai hợp đồng backend đã APPROVE: (a) chế độ "Đánh vần" gửi CHUỖI landmark bàn tay
tới `/api/fingerspelling/sequence` và ghép chữ bằng `/compose`; (b) chế độ "Ký từ" nói giao thức WS v2 của
`/ws/live-stream` qua proxy `/ws` của Vite. Đồng thời siết CORS/Origin/bind theo quyết định 2026-09-28, sửa smoke test
Phase 12, ghi hợp đồng vào `docs/phase12_api.md`, và lần đầu chạy backend + frontend cùng nhau có kiểm tự động (trình
duyệt thật, webcam giả nạp clip thật).

**DoD phục vụ.**
- DoD 1 (một phần): `start_fullstack.ps1` chạy cả hai, `/api/health` OK, không lỗi console — kiểm bằng script tự động.
  Phần "clone sạch theo README" KHÔNG thuộc việc này (backlog 7 gốc).
- DoD 2: webcam → chuỗi landmark → chữ + confidence → ghép từ; endpoint ảnh cũ 409 (frontend không gọi nữa).
- DoD 3: webcam → model mặc định (KHÔNG đổi) → top-k + confidence qua `/ws/live-stream`, cả đường `legacy` (mặc định) lẫn
  `harmonized_v1` (khi bật `VSL_MODEL_TYPE=stgcn_h360`, để GATE về sau dùng được UI — review 04 mục 12).
- DoD 6 (một phần): không có kết quả giả; bỏ nút "Test Frame" gửi ảnh 1×1. Nút chọn chế độ là Việc 6.
- DoD 7: contract test cho endpoint mới + test tương đương train↔live cho Cấp 1 + e2e trên clip thật + guard cơ bản
  cho `frontend/src` (Math.random, URL cứng).
- DoD 8: chỉ đảm bảo ĐO ĐƯỢC (có mốc thời gian client/server trong message), KHÔNG đo trong việc này.

## 2. Hiện trạng (HEAD 19d02bf)

### 2.1 Backend
- `backend/main.py:327-334`: `CORSMiddleware(allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
  allow_headers=["*"])` — đúng cái quyết định 2026-09-28 cấm.
- `backend/main.py:1297-1314`: `websocket_live_stream` gọi `websocket.accept()` ngay, KHÔNG kiểm header `Origin`.
- `backend/main.py:1519`: `uvicorn.run(..., host="0.0.0.0", ...)`; `start_fullstack.ps1:13`: `--host 0.0.0.0 --reload`.
- Cấp 1 (APPROVE ở kế hoạch 03): `GET /api/fingerspelling/status` (`:729`), `POST /api/fingerspelling/sequence` (`:760`),
  `POST /api/fingerspelling/compose` (`:800`), `POST /api/fingerspelling` → 409 (`:811`). Hợp đồng §3.2 kế hoạch 03:
  `landmarks` 1..`ALPHABET_MAX_FRAMES`(=300, `:551`) phần tử, mỗi phần tử `null`/`[]` hoặc 21×[x,y,z] hữu hạn |v| ≤ 10,
  không trùng hệt; `handedness`, `timestamps_ms?`, `frame_width/height`, `source_mirrored`, `top_k`; 413 (> 1 MiB),
  422 hai dạng body (`{"detail": str}` hoặc `{"detail": [{loc,msg,type}]}`), 503.
- Checkpoint Cấp 1 triển khai (`reports/alphabet_deploy_2026-09-27/provenance.json:27-45`): `bigru`, `target_frames` 30,
  `resample: "frame_index"`, `min_detected_frames` 3.
- Extractor lúc train Cấp 1: `scripts/extract_hands_batch.py:37-50` — `mp.solutions.hands.Hands(static_image_mode=False,
  max_num_hands=1, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)`, tracker MỚI cho mỗi
  clip, frame gốc (không resize), BGR→RGB, không lật; mediapipe 0.10.14. Không có tay → ghi 0 + `detected=False`.
  Dữ liệu train: `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` (hauuto 640×480 ≈ 23.6 fps, ≈ 75
  frame/clip; qipedc 1280×720) — trích trên Kaggle (Linux). Video gốc hauuto có cục bộ:
  `data/external/hauuto_raw/raw/raw/<signer>/<tên>.mp4`; video qipedc: `data/Dataset/Videos/D*.mp4`.
- **Backend CHƯA có đường nào trích landmark bàn tay Cấp 1 từ frame webcam.** `src/data/extract_landmarks.py:122`
  (`HandLandmarkExtractor`) dùng `min_detection_confidence=0.7`, không đặt `model_complexity`, trả đặc trưng 42 chiều đã
  chuẩn hóa — KHÁC extractor train, KHÔNG được dùng.
- WS v2 (kế hoạch 04 §3.6, `backend/main.py:1297+`): `session_info` → `frame_result` (legacy: có `gloss/prediction/
  confidence/top5/status IDLE|DETECTING|CONFIRMED/is_confirmed/buffer_fill/buffer_capacity`, `:1114-1143`; harmonized:
  không bao giờ mang dự đoán) → `sign_result` / `sign_discarded` (chỉ harmonized) → `error{code, detail, received_seq}`;
  1 MiB → 1009; `model_unavailable` → 1011. Helper dùng lại được: `_parse_ws_message` (`:890`, ném `bad_message`,
  `bad_config`, `bad_timestamp`, `message_too_large`), `_image_header` (`:945`), `_decode_frame(raw, min_height=None)`
  (`:965`), `_ws_error` (`:875`), `THREAD_POOL` (`:89`).
- `sign_result.segment.dropped_frames` theo hợp đồng mới của kế hoạch 05 (chỉ đếm frame hợp lệ bị ghi đè slot; docstring
  `:1308-1312`) và các thay đổi hợp đồng legacy (review 04 mục 11: message đầu là `session_info`, lỗi frame thành
  `error{code}`, bỏ khóa `frame`/`data`) CHƯA có trong `docs/phase12_api.md` (tài liệu còn `ws://localhost:8000`,
  `--host 0.0.0.0`, không có `session_info`).
- `scripts/smoke_test_phase12.py:74-102`: đọc `resp['gloss']` ở message đầu (nay là `session_info`) → `KeyError`;
  bước [4/5] chờ `status == "ERROR"` (nay là `error{code}`); dùng ảnh đen 640×480 và `data\Dataset\Videos\W00009N.mp4`.

### 2.2 Frontend
- `frontend/vite.config.js:5-14`: proxy `/api` → `http://127.0.0.1:8000` (changeOrigin) và `/ws` → `ws://127.0.0.1:8000`
  (`ws: true`); port 3000 cho `dev` và `preview`, KHÔNG `strictPort` (cổng bận thì Vite nhảy sang 3001 → Origin đổi).
  Proxy không đổi `Origin` của trình duyệt (`changeOrigin` chỉ đổi Host).
- `frontend/src/App.jsx:53-56`: tab `realtime` → `Phase12Pipeline`, `alphabet` → `Fingerspelling`, `dictionary`, `reports`.
  (Nút chọn chế độ đúng nghĩa DoD 6 là Việc 6; ở đây giữ các tab.)
- `frontend/src/components/Phase12Pipeline.jsx:51-52`: `ws://${host}:8000/ws/live-stream` CỨNG (bỏ qua proxy);
  `onmessage` (`:65-93`) không xét `type`: bỏ qua `session_info`/`error`, ghi đè `gloss=null` mỗi `frame_result`
  harmonized, bỏ qua `sign_result`/`sign_discarded`; nút "Test Frame" (`:121-131,160-168`) gửi JPEG 1×1 — dữ liệu giả lập
  trong mã chính; `bufferCapacity={60}` cứng (`:201`).
- `frontend/src/components/CameraCapture.jsx`: webcam 640×480 lý tưởng, `toDataURL('image/jpeg', 0.75)` hoặc binary;
  frame KHÔNG lật (chỉ CSS `-scale-x-100` khi hiển thị, `:252,260`) — khớp train, giữ nguyên. `timestamp: Date.now()`
  (`:146`) — đồng hồ tường, có thể lùi khi hệ thống chỉnh giờ → `bad_timestamp`. Nhận `ws` qua prop `wsRef.current`.
- `frontend/src/components/PredictionDisplay.jsx:81` và `Navbar.jsx:71`: chữ cứng ":8000".
- `frontend/src/components/RealtimeStream.jsx`: KHÔNG được import ở đâu (mã chết); cũng nối cứng `ws://…:8000` (`:143`).
- `frontend/src/components/Fingerspelling.jsx:58-88`: tải MỘT ảnh lên `POST /api/fingerspelling` (nay 409 → `alert`);
  không có webcam, không gửi chuỗi; ghép chữ bằng cộng chuỗi thô (`:207`) thay vì `/compose`; "25 lớp" cứng (`:130`).
- Không có framework test frontend. Có `puppeteer-core` trong `devDependencies` (`frontend/package.json:26`, đã có trong
  `frontend/node_modules`) và tiền lệ `scripts/take_screenshots.cjs` chạy Edge
  (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) với `--use-fake-device-for-media-stream`.
  → Unit test JS dùng `node --test` (có sẵn trong Node), e2e dùng puppeteer-core: KHÔNG cần cài gói mới.

### 2.3 Còn thiếu (việc này làm)
1. Đường trích landmark bàn tay Cấp 1 từ webcam, nhất quán với extractor train.
2. `Fingerspelling.jsx` viết lại: webcam → ghi một ký hiệu → `/sequence` → top-k → chấp nhận token → `/compose`.
3. Client WS v2 cho "Ký từ" (xử lý theo `type`, cả hai pipeline), URL qua proxy `/ws`.
4. CORS danh sách origin dev, WS kiểm Origin, bind 127.0.0.1.
5. `smoke_test_phase12.py` cho WS v2; `docs/phase12_api.md` cập nhật.
6. Script e2e fullstack (Edge + webcam giả nạp clip thật) + kiểm console.
7. Quyết định review 04 mục 8–9 (§3.8).

## 3. Thiết kế

### 3.1 Quyết định: MediaPipe cho Cấp 1 chạy ở SERVER (Python), không ở trình duyệt
- Bất biến 1 của skill `vsl-landmark-consistency`: cùng extractor + cùng phiên bản ở train và live. Train Cấp 1 dùng
  `mp.solutions.hands` 0.10.14 (Python). MediaPipe JS (`@mediapipe/tasks-vision`, HandLandmarker) là model/phiên bản
  khác, cần tải model `.task` + WASM từ mạng (trái quy tắc "không tải từ mạng" nếu không có bản cục bộ), và KHÔNG thể có
  test tương đương bit-by-bit với landmark train.
- Chạy ở server: dùng đúng `mp.solutions.hands` với đúng tham số của `scripts/extract_hands_batch.py`, tracker mới cho mỗi
  ký hiệu (như "tracker mới cho mỗi clip" lúc trích). Tương đương kiểm được bằng test Python: cùng video → đường live ↔
  `_extract_one` phải ra landmark GIỐNG HỆT (AC5).
- Giá phải trả: frame đi qua WS (như chế độ Ký từ); có thêm độ trễ mạng/giải mã — ghi được vào metrics, không đo ở đây.
- Hợp đồng `/api/fingerspelling/sequence` (kế hoạch 03) GIỮ NGUYÊN: server trả landmark thô về client, client ghép chuỗi
  và gọi `/sequence`. Không thêm đường phân loại thứ hai.

### 3.2 Luồng dữ liệu chế độ "Đánh vần"
```
Fingerspelling.jsx
  GET /api/fingerspelling/status → available, classes, num_classes, preprocessing   (không available → khóa nút ghi, hiện message)
  WS  /ws/hand-landmarks (URL từ window.location qua proxy /ws) → session_info
  [Ghi]   → gửi {"type":"control","action":"reset"} → chờ reset_done(segment_id)
          → vòng chụp (FS_TARGET_FPS, canvas KHÔNG lật, JPEG chất lượng FS_JPEG_QUALITY) gửi {image, timestamp=nowMs()}
            tối đa FS_MAX_IN_FLIGHT frame chưa có hand_frame; vượt → bỏ chụp frame đó, đếm client_skipped
          → mỗi hand_frame(segment_id hiện tại) → lưu {landmarks|null, handedness, client_timestamp, frame_width, frame_height}
  [Dừng] hoặc đủ limits.max_frames_per_segment frame (lấy từ session_info, không cứng)
          → chờ hết frame đang bay (timeout 2 s; frame không về thì không có trong chuỗi, đếm vào client_skipped)
          → body = buildSequenceBody(frames, {topK: 5})   (hàm thuần, frontend/src/lib/fingerspelling.js)
          → POST /api/fingerspelling/sequence
              200 → hiện prediction, confidence, candidates (class, confidence, kind), frames, detected_frames
              413/422/503 → hiện detail (cả 2 dạng body), KHÔNG hiện kết quả nào
  Bộ ghép: tokens[] trong state. [Thêm] = thêm candidate người dùng chọn (mặc định top-1); [Dấu cách] = " ";
          [Xóa lùi], [Xóa hết]. Mỗi lần tokens đổi → POST /api/fingerspelling/compose {tokens}
          → hiện text + warnings. Chữ hiển thị CHỈ lấy từ `text` của server (không tự ghép trong JS).
```
`buildSequenceBody` (hợp đồng, test ở AC7):
- `landmarks[i]` = mảng 21×[x,y,z] đúng như server trả, hoặc `null` khi `hand_frame.landmarks == null`.
  KHÔNG bao giờ gửi khung toàn 0.
- `handedness[i]` = `hand_frame.handedness` ("" khi không có tay); `timestamps_ms[i]` = `client_timestamp` (ms, đồng hồ
  đơn điệu `performance.timeOrigin + performance.now()`, không giảm).
- `frame_width`/`frame_height` = của hand_frame; nếu kích thước đổi giữa chừng → không gửi, hiện lỗi "kích thước camera
  đổi" (không đoán).
- `source_mirrored: false` (frame không lật); `top_k`.
- Thứ tự theo `frame_seq`; chỉ lấy hand_frame có `segment_id` của lượt ghi hiện tại.

Hằng mới (ghi ở `frontend/src/lib/fingerspelling.js`, có chú thích "giá trị thiết kế, chưa đo"): `FS_TARGET_FPS = 24`
(gần fps hauuto trong manifest), `FS_JPEG_QUALITY = 0.9`, `FS_MAX_IN_FLIGHT = 2`. Không có tham số cắt ký hiệu tự động:
người dùng bấm Ghi/Dừng (tránh thêm luật cắt chưa có dữ liệu; §6).

UI hiển thị kèm kết quả: độ phân giải frame, số frame, số frame có tay, `client_skipped`, fps hiệu dụng của lượt ghi
(tính từ `client_timestamp`) — để người dùng thấy khi đầu vào lệch điều kiện train. `confidence` ghi là "độ tin cậy của
model", không ghi là "độ chính xác".

### 3.3 Hợp đồng `WS /ws/hand-landmarks` (mới, `protocol_version` 1)
Module thuần mới `src/inference/hand_live.py` (không import torch/fastapi):
- `LEVEL1_HANDS_KWARGS = {"static_image_mode": False, "max_num_hands": 1, "model_complexity": 1,
  "min_detection_confidence": 0.5, "min_tracking_confidence": 0.5}` — phải BẰNG các keyword trong lời gọi
  `Hands(...)` của `scripts/extract_hands_batch.py` (AC4-a đọc bằng `ast`, KHÔNG sửa file train).
- `class HandLandmarkSession`: `reset()` (đóng graph cũ, tạo `mp.solutions.hands.Hands(**LEVEL1_HANDS_KWARGS)` mới),
  `process(frame_bgr) -> (landmarks float32[21,3] | None, label: str, score: float | None)` — đúng chuyển đổi của
  `_extract_one`: `cv2.cvtColor(BGR2RGB)`, frame gốc không resize, `multi_hand_landmarks[0]`,
  `multi_handedness[0].classification[0]`; `close()`.

Endpoint `websocket_hand_landmarks` trong `backend/main.py`: kiểm Origin (§3.5) → accept → tạo session (lỗi →
`error{model_unavailable}` + 1011) → vòng nhận TUẦN TỰ (mỗi message xử lý xong mới nhận message sau; không có slot
"frame mới nhất", không bỏ frame ở server). Dùng lại `_parse_ws_message`, `_decode_frame(raw, min_height=None)`,
`_ws_error`, `THREAD_POOL`; không viết lại logic giải mã/kiểm kích thước.

Client → server: giống `/ws/live-stream` (text JSON `{"image", "timestamp"?}`, binary JPEG/PNG,
`{"type":"control","action":"reset"}`). `config` hợp lệ bị bỏ qua; `config` sai → `bad_config` (do parser dùng chung).

Server → client:
1. `session_info` (đầu tiên): `{"type":"session_info","endpoint":"hand-landmarks","protocol_version":1,
   "extractor":{"name":"mp.solutions.hands","mediapipe_version", ...LEVEL1_HANDS_KWARGS},
   "limits":{"max_message_bytes":WS_MAX_MESSAGE_BYTES,"max_frame_side":WS_MAX_FRAME_SIDE,
   "max_frames_per_segment":ALPHABET_MAX_FRAMES}}`.
2. `reset_done`: `{"type":"reset_done","segment_id":int}` — gửi SAU khi graph mới đã tạo; `segment_id` tăng 1 mỗi reset
   (bắt đầu 0 lúc mở phiên, graph ban đầu cũng mới).
3. `hand_frame`: `{"type":"hand_frame","segment_id","frame_seq"(0-based trong segment),"received_seq",
   "client_timestamp":number|null,"frame_width","frame_height","landmarks":[[x,y,z]×21]|null,
   "handedness":"Left"|"Right"|"","handedness_score":number|null,
   "metrics":{"decode_ms","extract_ms","server_total_ms"}}` (thời gian đo bằng `time.perf_counter`).
   `landmarks` là float32 của MediaPipe đổi sang float Python (không làm tròn), để JSON đi-về giữ nguyên giá trị.
4. `error`: `_ws_error` với mã ∈ {`message_too_large` (đóng 1009), `bad_message`, `bad_config`, `bad_timestamp`,
   `decode_failed`, `unsupported_format`, `frame_too_large`, `model_unavailable` (đóng 1011)}; lỗi một message không đóng
   phiên; frame lỗi KHÔNG tăng `frame_seq` và không đưa vào tracker.

### 3.4 Chế độ "Ký từ": client WS v2
- `frontend/src/lib/ws.js`: `wsUrl(location, path)` → `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`.
  Mọi WS trong `frontend/src` dùng hàm này; không còn chuỗi `:8000` nào trong `frontend/src`.
- `frontend/src/lib/liveProtocol.js`: reducer THUẦN `reduceLive(state, msg, nowMs)` (không React, test bằng `node --test`):
  - `session_info`: lưu `pipeline`, `protocol_version` (≠ 2 → `state.fatal = "protocol_mismatch"`), `model`
    (`model_type`, `is_default`), `segmenter.max_sign_s` (harmonized), `limits`.
  - `frame_result` legacy: cập nhật `gloss/confidence/top5/status/buffer_fill/buffer_capacity` (lấy từ message, bỏ số 60
    cứng), `landmarks`, `metrics`; thêm từ vào `words` khi `status` chuyển sang `CONFIRMED` với gloss mới (giữ hành vi cũ
    của `Phase12Pipeline.jsx:81-89`).
  - `frame_result` harmonized: chỉ cập nhật trạng thái ghi (`status` IDLE/RECORDING/WAIT_REST, `segment.recording_s`,
    `hand_detected`, `hand_active`), `landmarks`, `metrics`; KHÔNG động tới kết quả dự đoán đang hiện.
  - `sign_result`: `lastSign = {gloss, confidence, top5, segment, segment_id}`; thêm `gloss` vào `words` (KHÔNG khử trùng,
    §3.8); `lastSign.client_e2e_ms = nowMs - metrics.trigger_client_timestamp` khi trigger là số (để DoD 8 đo được).
  - `sign_discarded`: `lastDiscard = {reason, segment}`; UI đổi `reason` sang câu tiếng Việt.
  - `error`: `lastError = {code, detail}`; `message_too_large`/`model_unavailable` → `state.fatal = code`.
  - `type` lạ: tăng `state.unknownMessages`, không ném lỗi.
- `Phase12Pipeline.jsx`: dùng `wsUrl(window.location, '/ws/live-stream')` + `reduceLive`; hiện huy hiệu pipeline/model,
  "Đang ghi ký hiệu" + thanh `recording_s / max_sign_s` (harmonized), lý do bỏ đoạn, lỗi theo `code`; top-5 + confidence
  của `sign_result` (harmonized) hoặc `frame_result` (legacy); nút "Xóa từ cuối". Xóa nút "Test Frame" và chuỗi base64 1×1.
- `CameraCapture.jsx`: `timestamp = nowMs()` (`performance.timeOrigin + performance.now()`, đơn điệu, dùng chung với
  reducer); lấy socket qua ref/getter thay vì giá trị `wsRef.current` lúc render (tránh socket cũ sau khi nối lại).
- `PredictionDisplay.jsx`, `Navbar.jsx`: bỏ ":8000".
- `RealtimeStream.jsx` (mã chết): CHỈ thay dòng URL bằng `wsUrl(...)`. KHÔNG xóa file (xóa file là điểm dừng); ghi vào
  backlog "hỏi người dùng trước khi xóa RealtimeStream.jsx".

### 3.5 CORS, Origin của WS, bind
- `backend/main.py`: `DEFAULT_DEV_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")`;
  hàm thuần `parse_cors_origins(value: Optional[str]) -> Tuple[str, ...]`: `None`/rỗng → mặc định; tách theo dấu phẩy,
  bỏ khoảng trắng; phần tử `*`, rỗng, hoặc không bắt đầu bằng `http://`/`https://`, hoặc có dấu `/` ở cuối → `ValueError`.
  `ALLOWED_ORIGINS = parse_cors_origins(os.environ.get("VSL_CORS_ORIGINS"))` lúc import (sai → không khởi động được).
- `CORSMiddleware(allow_origins=list(ALLOWED_ORIGINS), allow_credentials=False, allow_methods=["GET", "POST"],
  allow_headers=["Content-Type"])`. Frontend không dùng cookie/credentials. Giữ thứ tự middleware (CORS ngoài cùng,
  `backend/main.py:324`).
- `ws_origin_allowed(origin: Optional[str]) -> bool`: không có header `Origin` → True (client không phải trình duyệt: smoke
  test, script đo; trình duyệt luôn gửi Origin); có → khớp CHÍNH XÁC một phần tử `ALLOWED_ORIGINS` (`"null"` bị từ chối).
  Cả `/ws/live-stream` và `/ws/hand-landmarks` gọi TRƯỚC `accept()`; bị từ chối → `await websocket.close(code=1008)`
  (bắt tay trả 403), log cảnh báo với origin cắt ngắn bằng `_short`, KHÔNG gửi `session_info`, KHÔNG nạp model.
- Bind: `start_fullstack.ps1` `--host 127.0.0.1`; `uvicorn.run(host="127.0.0.1", ...)` trong `backend/main.py`;
  `frontend/vite.config.js` thêm `strictPort: true` cho `server` và `preview`, KHÔNG đặt `host: true`/`0.0.0.0`.
- Qua proxy Vite, trình duyệt thấy `/api` và `/ws` là cùng origin → CORS không tham gia; backend vẫn thấy
  `Origin: http://localhost:3000` ở bắt tay WS nên Origin check vẫn có hiệu lực. CORS chỉ còn ý nghĩa khi một trang
  origin khác gọi thẳng :8000.

### 3.6 Smoke test Phase 12 và tài liệu
- `scripts/smoke_test_phase12.py` (sửa, vẫn là script thủ công dùng `TestClient`): message đầu phải là `session_info`
  (`protocol_version == 2`, `pipeline` ∈ {legacy, harmonized_v1}); các bước sau phân nhánh theo `pipeline`
  (legacy: `frame_result` đủ khóa cũ; harmonized: `frame_result` có `prediction is None`); text rác → một message
  `type == "error"` với `code` thuộc bảng mã §3.6 kế hoạch 04 (in ra mã thật); video thật 30 frame: đếm message theo
  `type`, 0 `error`; thêm bước `/ws/hand-landmarks` (session_info → reset_done → hand_frame trên 1 frame video hauuto
  thật); thêm bước Origin lạ bị từ chối. In "PASSED" chỉ khi mọi assert qua.
- `docs/phase12_api.md` (viết lại phần giao thức): cách chạy (127.0.0.1, proxy `/api` `/ws`, `strictPort`), chính sách
  CORS/Origin/`VSL_CORS_ORIGINS`; REST (health 200/503, fingerspelling status/sequence/compose/409, 413/422/503); WS
  `/ws/live-stream` v2 đầy đủ (chép bảng §3.6 kế hoạch 04 + nghĩa `dropped_frames` của kế hoạch 05 + thay đổi legacy ở
  review 04 mục 11); WS `/ws/hand-landmarks` (§3.3); các trường để đo DoD 8 (Ký từ: `trigger_client_timestamp`; Đánh vần:
  mốc client từ lúc bấm Dừng tới khi có phản hồi `/sequence` + `metrics` của hand_frame). Không ghi số đo nào.

### 3.7 Kiểm tự động fullstack + e2e trên clip thật
- `scripts/make_fake_webcam_y4m.py --video <mp4> --out <y4m> [--max-frames N]`: đọc video bằng cv2, ghi Y4M 4:2:0 cùng
  kích thước (cắt 1 px nếu lẻ) và cùng fps (`F<num>:<den>`). File ra ở thư mục tạm NGOÀI repo (vd. `%TEMP%\vslt_e2e\`);
  không commit video/frame.
- `scripts/e2e_browser.cjs` (puppeteer-core + Edge; đường dẫn trình duyệt từ `VSL_E2E_BROWSER`, mặc định đường Edge của
  `take_screenshots.cjs`): cờ `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream
  --use-file-for-fake-video-capture=<y4m>`; mở `http://localhost:3000/`; ghi lại: console `error`, `pageerror`,
  `requestfailed`, HTTP ≥ 400, URL WS (CDP `Network.webSocketCreated`), `type` của mọi message WS nhận (CDP
  `Network.webSocketFrameReceived`), body + status của mọi `POST /api/fingerspelling/sequence|compose`.
  Chọn phần tử bằng `data-testid` (thêm vào component; danh sách ở B5/B6). In JSON ra file `--out`.
- `scripts/e2e_fullstack.py --scenario fingerspell|word [--model-type stgcn_h360] --video <mp4> --out <json>`:
  1. chạy `powershell -NoProfile -ExecutionPolicy Bypass -File start_fullstack.ps1` (env thêm `VSL_MODEL_TYPE` nếu có;
     `-ExecutionPolicy Bypass` chỉ cho tiến trình này, KHÔNG đổi policy hệ thống);
  2. chờ `GET http://127.0.0.1:8000/api/health` 200 và `http://localhost:3000/` 200 (timeout 180 s, ghi thời gian chờ);
  3. tạo y4m, chạy `node scripts/e2e_browser.cjs`;
  4. dừng cây tiến trình (`taskkill /T /F /PID`), kiểm cổng 8000/3000 đã rảnh;
  5. ghi JSON: `generated_by{command, git_commit, code_dirty}`, phiên bản node/Edge/mediapipe, clip id (không đường dẫn
     tuyệt đối, không landmark), kết quả kịch bản, danh sách lỗi console (nguyên văn, cắt 300 ký tự).
- Clip: Đánh vần — `data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4` (640×480, cỡ webcam; clip TRAIN của model Cấp
  1 → chỉ kiểm chạy được, KHÔNG phải độ chính xác). Ký từ — clip đầu tiên (thứ tự của hàm) của mẫu
  `scripts/live_clip_sample.py` (seed 0, split TRAIN), KHÁC `qipedc_W03251B`. KHÔNG dùng clip TEST/VAL nào.

### 3.8 Quyết định review 04 mục 8–9: TÁCH khỏi Việc 5
- **Mục 8 (tốc độ theo dt từng frame) và mục 9 (ký hiệu có nhịp nghỉ bị phát lặp, W03251B): KHÔNG làm trong kế hoạch này.**
  Tách thành kế hoạch riêng "segmenter live", đặt ngay sau Việc 5 trong backlog; phần chỉnh tham số chờ dữ liệu webcam
  của Bước 5.
- Lý do:
  1. Cả hai đổi hành vi cắt đoạn của đường harmonized (đoạn nào được dự đoán), tức đổi đầu vào model; cần test tương đương
     và bằng chứng riêng. Gộp vào việc nối UI sẽ trộn hai loại rủi ro trong một review.
  2. Chính sách cho mục 9 (gộp đoạn gần nhau / khử trùng gloss liên tiếp / đổi `rest_hold_s`) hiện chỉ có 1 clip bằng chứng
     (W03251B, n = 1). Kế hoạch 04 §3.4 cấm chỉnh tham số trên TEST; dữ liệu hợp lệ là clip TRAIN (nhiều clip) và webcam
     người dùng (Bước 5). Khử trùng gloss ở UI sẽ nuốt mất từ lặp thật mà người ký chủ ý.
  3. Mục 8 cần fixture tay nghỉ có nhiễu + mô phỏng rơi frame thật; với WebSocket thật (việc này bật được) mới đo được
     mẫu rơi frame thực tế — nên làm SAU khi UI chạy.
  4. Đường mặc định (legacy) không dùng `SignSegmenter`; UI của việc này vẫn đúng hợp đồng khi segmenter đổi về sau.
- Trong Việc 5: UI hiện TỪNG `sign_result` như server gửi (không khử trùng, không gộp), có nút "Xóa từ cuối"; `sign_discarded`
  hiện lý do. Như vậy hiện tượng lặp nhìn thấy được, không bị che. Ghi giới hạn này vào `docs/phase12_api.md`.

### 3.9 Ngoài phạm vi (ghi rõ để reviewer không tính là thiếu)
- Nút chọn chế độ, Ký câu (Việc 6); từ điển SQLite; proxy `/videos` `/raw_videos` cho tab Từ điển; đổi model mặc định
  (GATE); đo độ trễ DoD 8; clone sạch; số liệu cứng trong `Reports.jsx` (DoD 9).
- `detail` 503 có thể chứa tên file (review 04 mục 6 / review 05): KHÔNG sửa ở đây — sửa sẽ đổi body mà test cũ đang
  kiểm, và sau khi bind 127.0.0.1 phạm vi lộ chỉ còn máy cục bộ. Đưa vào backlog 8.

## 4. Chia việc

Quy ước chung cho mọi bước:
- `P6` = HEAD lúc coder bắt đầu B0 (commit đã chứa kế hoạch này; ghi hash vào `docs/plans/06-progress.md`).
- Trước khi sửa một symbol: GitNexus `impact <symbol> --direction upstream`; `risk: UNKNOWN` → xác nhận bằng text search.
  Trước MỖI commit: `detect-changes --scope all`; ghi risk thật vào commit message. KHÔNG `git commit --amend`, không
  `git add -A`/`git add .` (3 file ` D` của người dùng + nhiều file untracked).
- Viết test trước (hoặc cùng lúc) với code. Mỗi bước kết thúc bằng 1 commit và 1 đoạn trong `docs/plans/06-progress.md`
  (lệnh đã chạy + output thật rút gọn + hash).
- Thư mục tạm ngoài repo: `../_plan06_tmp/`.

| Bước | Nội dung | Phụ thuộc | Ước lượng |
|---|---|---|---|
| **B0** | Mốc: chạy lệnh AC2 (chỉ 25 module cũ) tại `P6`, lưu output + `git status --porcelain` vào `../_plan06_tmp/b0_*.txt`; ghi `node --version`, `npm ls --depth=0` (lưu file), Edge có tồn tại ở đường mặc định không, `mediapipe.__version__`; `impact` cho `websocket_live_stream`, `_parse_ws_message`, `_decode_frame`, `health`. Tạo `docs/plans/06-progress.md`. Commit. | — | 0.5 giờ |
| **B1** | CORS/Origin/bind (§3.5): test `tests/test_cors_origin_bind.py` (AC3) trước → sửa `backend/main.py`, `start_fullstack.ps1`, `frontend/vite.config.js`. Chạy AC3 + `tests.test_ws_live_contract tests.test_fingerspelling_limits tests.test_fingerspelling_api tests.test_ws_dropped_frames`. Commit. | B0 | 1.5 giờ |
| **B2** | `src/inference/hand_live.py` + endpoint `/ws/hand-landmarks` (§3.3): test `tests/test_hand_landmarks_ws.py` (AC4) trước. Commit. | B1 (dùng `ws_origin_allowed`) | 2 giờ |
| **B3** | Tương đương Cấp 1 train↔live: `tests/test_hand_live_equivalence.py` (AC5) + `scripts/hand_live_check.py` và JSON (AC6). Nếu AC5-a không bằng hệt → DỪNG, báo planner (§7). Commit. | B2 | 2 giờ |
| **B4** | Thư viện JS thuần `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` + `frontend/tests/*.test.mjs` (`node --test`) + `frontend/tests/build_body_cli.mjs`; thêm script `"test": "node --test tests/"` vào `frontend/package.json`; Python `tests/test_frontend_contract.py` (AC7-d, AC8). Commit. | B2 (định dạng hand_frame) | 2 giờ |
| **B5** | UI "Ký từ" (§3.4): `Phase12Pipeline.jsx`, `CameraCapture.jsx`, `PredictionDisplay.jsx`, `Navbar.jsx`, dòng URL của `RealtimeStream.jsx`; `data-testid`: `live-connection`, `live-pipeline`, `live-model`, `live-status`, `live-recording`, `live-gloss`, `live-confidence`, `live-top5`, `live-discard`, `live-error`, `live-words`, `live-undo`, `camera-start`, `camera-stop`. `npm run build` (AC9). Commit. | B4 | 2 giờ |
| **B6** | UI "Đánh vần" (§3.2): viết lại `Fingerspelling.jsx`; `data-testid`: `fs-status`, `fs-ws`, `fs-record`, `fs-stop`, `fs-frames`, `fs-prediction`, `fs-confidence`, `fs-candidates`, `fs-error`, `fs-add`, `fs-space`, `fs-backspace`, `fs-clear`, `fs-composed`, `fs-warnings`. `npm run build`. Commit. | B4 | 2 giờ |
| **B7** | `scripts/smoke_test_phase12.py` (AC10) chạy với model mặc định VÀ `VSL_MODEL_TYPE=stgcn_h360`; viết lại `docs/phase12_api.md` (AC11, test thêm vào `tests/test_frontend_contract.py`). Commit. | B2, B5 | 1.5 giờ |
| **B8** | E2E: `scripts/make_fake_webcam_y4m.py`, `scripts/e2e_browser.cjs`, `scripts/e2e_fullstack.py`; chạy 3 kịch bản AC12 (Đánh vần mặc định, Ký từ mặc định, Ký từ `stgcn_h360`) tại HEAD sạch; commit script + 3 JSON. | B5, B6, B7 | 2 giờ |
| **B9** | Đóng: chạy AC2 đầy đủ + `node --test` + build; so `git status --porcelain` với B0; THÊM 1 dòng progress_log (AC13), ghi backlog đề xuất (kế hoạch "segmenter live"; hỏi người dùng trước khi xóa `RealtimeStream.jsx`; `detail` 503). Commit. Orchestrator gọi vslt-reviewer. | B0–B8 | 0.5 giờ |

Tổng ước lượng ≈ 16 giờ, GPU 0 giờ, không Kaggle, không cài gói.

**Chặng giao gợi ý:** chặng 1 = B0–B2 (backend: CORS/Origin/bind + endpoint mới); chặng 2 = B3–B4 (tương đương + thư
viện JS); chặng 3 = B5–B7 (UI hai chế độ + smoke + tài liệu); chặng 4 = B8–B9 (e2e fullstack + đóng việc).

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG được đổi; chỉ planner đổi và phải ghi lý do)

Mọi lệnh Python chạy qua `.venv/Scripts/python` với `PYTHONIOENCODING=utf-8`, từ thư mục gốc repo. "Mới" = file/lớp test do kế
hoạch này thêm. Test mới không cần mạng, không ghi file trong repo (chỉ thư mục tạm), và KHÔNG skip trên máy này (được
`skipUnless` cho clone sạch, lý do nêu rõ file thiếu).

**AC1 — Phạm vi thay đổi.** `git diff --name-status P6 HEAD` chỉ chứa:
- `backend/main.py` (M); `src/inference/hand_live.py` (A); `start_fullstack.ps1` (M, chỉ tham số `--host`);
- `frontend/vite.config.js` (M); `frontend/package.json` (M, CHỈ thêm khóa `scripts.test`); `frontend/index.html` (M, chỉ
  nếu cần để hết lỗi console ở AC12, ghi lý do);
- `frontend/src/components/{Phase12Pipeline,CameraCapture,PredictionDisplay,Navbar,Fingerspelling}.jsx` (M);
  `frontend/src/components/RealtimeStream.jsx` (M, chỉ dòng URL + 1 dòng import);
  `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` (A); `frontend/tests/*.mjs` (A);
- `scripts/smoke_test_phase12.py` (M); `scripts/{hand_live_check,make_fake_webcam_y4m,e2e_fullstack}.py`,
  `scripts/e2e_browser.cjs` (A);
- `tests/{test_cors_origin_bind,test_hand_landmarks_ws,test_hand_live_equivalence,test_frontend_contract}.py` (A);
- `reports/fingerspell_live_<YYYY-MM-DD>/hand_live_check.json`, `reports/e2e_<YYYY-MM-DD>/*.json` (A);
- `docs/phase12_api.md` (M); `docs/progress_log.md` (M, chỉ thêm); `docs/plans/06-progress.md` (A/M);
  `docs/plans/06-viec5-frontend.md` (chỉ planner).

KHÔNG đổi: `frontend/package-lock.json`, `frontend/src/App.jsx`, `Dictionary.jsx`, `Reports.jsx`, `scripts/extract_hands_batch.py`,
`src/data/**`, `src/inference/{harmonized_live,sign_segmenter,predictor}.py`, `configs/`, `checkpoints/`, `data/`, mọi test
đã có, `docs/reviews/*`. Không xóa file nào. 3 file data của người dùng vẫn ` D` chưa staged. Không file `.pt/.npz/.mp4/.y4m/
.png/.jpg/.log` nào được thêm vào git; `frontend/dist` và `node_modules` không vào git.

**AC2 — Không hồi quy.** Lệnh (25 module của kế hoạch 05 + 4 module mới):
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract -v`
- 0 failure, 0 error, 0 skip. Số test = số B0 (25 module) + số test mới; báo theo module, trước → sau.
- `git diff P6 HEAD -- tests/` với mọi file test đã có ở `P6`: 0 dòng `-`.
- `git status --porcelain` trước và sau khi chạy giống hệt.
- `cd frontend && node --test tests/` → 0 fail; báo số test.

**AC3 — CORS / Origin / bind (`tests/test_cors_origin_bind.py`).**
- a. `parse_cors_origins`: `None`→`DEFAULT_DEV_ORIGINS`; `""`→`DEFAULT_DEV_ORIGINS`; `" http://a:1 , https://b "`→
  `("http://a:1", "https://b")`; mỗi giá trị sau → `ValueError`: `"*"`, `"http://a,*"`, `"http://a,"`, `"ftp://x"`,
  `"http://a/"`, `"null"`.
- b. `api.DEFAULT_DEV_ORIGINS == ("http://localhost:3000", "http://127.0.0.1:3000")`; khi test chạy không có
  `VSL_CORS_ORIGINS` thì `api.ALLOWED_ORIGINS == api.DEFAULT_DEV_ORIGINS`. Trong `api.app.user_middleware` có đúng một
  `CORSMiddleware` với `allow_origins == list(DEFAULT_DEV_ORIGINS)`, `allow_credentials is False`, và `"*"` không nằm trong
  `allow_origins`, `allow_methods`, `allow_headers`.
- c. HTTP (`POST /api/fingerspelling/compose {"tokens": ["a"]}`, không cần model):
  - `Origin: http://localhost:3000` → 200, `access-control-allow-origin == "http://localhost:3000"`, KHÔNG có header
    `access-control-allow-credentials`;
  - `Origin: http://evil.example` → không có header `access-control-allow-origin`;
  - preflight `OPTIONS` với `Origin: http://evil.example` + `Access-Control-Request-Method: POST` → không có
    `access-control-allow-origin` và mã khác 2xx; với `Origin: http://127.0.0.1:3000` → 200 và ACAO bằng origin đó;
  - không response nào trong test có ACAO `*`.
- d. WS: với mỗi path ∈ {`/ws/live-stream`, `/ws/hand-landmarks`} và mỗi origin ∈ {`http://evil.example`, `null`,
  `http://localhost:3001`, `http://localhost:3000.evil.example`, `HTTP://LOCALHOST:3000`}: `websocket_connect(path,
  headers={"origin": ...})` ném `WebSocketDisconnect` với `code == 1008`; `backend.main._active_model` và
  `HandLandmarkSession` (vá bằng `MagicMock`) KHÔNG được gọi.
- e. Origin hợp lệ vẫn qua: `/ws/hand-landmarks` với `Origin: http://localhost:3000` → message đầu `type == "session_info"`;
  `/ws/live-stream` với `Origin: http://localhost:3000` và `_active_model` vá để ném `ModelUnavailable` → nhận
  `error{code: "model_unavailable"}` rồi đóng 1011 (chứng minh đã qua kiểm Origin mà không nạp model thật); không có header
  Origin → như Origin hợp lệ.
- f. `ws_origin_allowed`: `None`→True; `"http://localhost:3000"`→True; `"http://127.0.0.1:3000"`→True; `""`→False; `"null"`→False.
- g. Bind (kiểm văn bản): `start_fullstack.ps1` chứa `--host 127.0.0.1` và không chứa `0.0.0.0`; `backend/main.py` không chứa
  `0.0.0.0` và lời gọi `uvicorn.run(` có `host="127.0.0.1"`; `frontend/vite.config.js` có `strictPort: true` trong cả
  `server` và `preview`, không có khóa `host`.

**AC4 — Hợp đồng `/ws/hand-landmarks` (`tests/test_hand_landmarks_ws.py`, MediaPipe thật, CPU).**
- a. `LEVEL1_HANDS_KWARGS` bằng hệt dict keyword của lời gọi `Hands(...)` DUY NHẤT trong `scripts/extract_hands_batch.py`
  (đọc bằng `ast.literal_eval` từng keyword). Subprocess `import src.inference.hand_live, sys; print('torch' in
  sys.modules, 'fastapi' in sys.modules)` in `False False`.
- b. `session_info` là message đầu, đủ khóa §3.3; `extractor.mediapipe_version == mediapipe.__version__` và bằng giá trị
  DUY NHẤT của cột `mediapipe_version` trong `manifest.csv` (đọc từ file, không gõ tay);
  `limits.max_frames_per_segment == api.ALPHABET_MAX_FRAMES`.
- c. Reset: `segment_id` ban đầu 0; mỗi `control/reset` → `reset_done` với `segment_id` +1; `frame_seq` bắt đầu lại từ 0.
  Spy constructor `mp.solutions.hands.Hands`: số lần gọi = 1 + số reset; graph cũ được `close()` đúng 1 lần mỗi reset.
- d. Frame thật: frame của `a_hau_A_001.mp4` có tay (chỉ số lấy từ kết quả `_extract_one` trong test, không gõ tay) →
  `landmarks` 21×3 số, |v| ≤ 10, `handedness` ∈ {Left, Right}, `0 < handedness_score ≤ 1`; frame đen 640×480 →
  `landmarks is None`, `handedness == ""`, `handedness_score is None`.
- e. Lỗi (phiên KHÔNG đóng, frame hợp lệ tiếp theo vẫn nhận `hand_frame` và lỗi không làm tăng `frame_seq`):
  text rác → `type == "error"`, `code` ∈ {bad_message, decode_failed, unsupported_format}; PNG header khai 4000×10 →
  `frame_too_large` và `cv2.imdecode` KHÔNG được gọi (spy); `timestamp: "x"` → `bad_timestamp`. Message > 1 MiB →
  `message_too_large` rồi đóng 1009. `detail` ≤ 200 ký tự và không chứa chuỗi base64 đã gửi.
- f. Tuần tự, không bỏ frame: gửi liên tiếp 5 frame rồi mới đọc → đúng 5 `hand_frame`, `frame_seq` 0..4, `received_seq`
  tăng ngặt, `client_timestamp` bằng hệt timestamp đã gửi; frame binary → `client_timestamp is None`.
- g. `Hands(...)` ném lỗi khi khởi tạo (vá) → `error{model_unavailable}` + đóng 1011.

**AC5 — Tương đương train↔live Cấp 1 (`tests/test_hand_live_equivalence.py`).**
- Mẫu: `np.random.default_rng(0)` chọn 8 clip hauuto trong `manifest.csv` có video cục bộ (hàm ánh xạ `sample_id` →
  `data/external/hauuto_raw/raw/raw/<signer>/<tên>.mp4` dùng chung với `scripts/hand_live_check.py`; test assert tìm thấy
  ≥ 8) + 2 clip qipedc đầu tiên (theo `sample_id`) có `data/Dataset/Videos/<id>.mp4`.
- Offline = `_extract_one` của `scripts/extract_hands_batch.py` (import, không sửa) chạy vào thư mục tạm, CÙNG máy.
  Live = đọc cùng video bằng `cv2.VideoCapture` → PNG → WS text data-URL, `timestamp = i * 1000 / fps` → một `reset` đầu
  clip → dãy `hand_frame`.
- a. Mỗi clip: số frame bằng nhau; `detected` `array_equal`; landmark các frame có tay `np.array_equal` sau khi ép float32;
  nhãn handedness bằng nhau; score bằng nhau (float32).
- b. Body `/sequence` dựng từ live (theo §3.2) == body dựng từ npz offline (theo cách của
  `tests/test_fingerspelling_deployed.body`, thêm `timestamps_ms` như nhau) — so dict JSON bằng hệt. POST cả hai với
  checkpoint triển khai (`checkpoints/alphabet_best.pt`, sha256 phải bằng `provenance.json`) → JSON response bằng hệt.
- c. Model offline dựng từ checkpoint (như `TestDeployedCheckpointEquivalence`) trên `alphabet_clip_features` của npz
  offline → top-1 bằng `prediction` của live, `|Δconfidence| ≤ 1e-4`.
- d. Test in mỗi clip: `sample_id`, số frame, số frame có tay (từ output, không gõ tay). Không có câu nào về độ chính xác.
- Nếu (a) KHÔNG bằng hệt: DỪNG, báo planner (không nới sang dung sai).

**AC6 — Báo cáo lệch nguồn (`scripts/hand_live_check.py`).** Lệnh:
`.venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0 --out reports/fingerspell_live_<YYYY-MM-DD>/hand_live_check.json`
(cùng mẫu AC5). JSON có `generated_by{command, git_commit, code_dirty: false}`, `note` ("report only; hauuto clips are
training data of the deployed Level 1 model; not accuracy"), và mỗi clip: `sample_id`, `source`, `n_frames`;
`live_png_vs_local_offline{detected_equal, max_abs_diff}`; `live_jpeg90_vs_live_png{detected_agree, max_abs_diff_both}`;
`kaggle_npz_vs_local_offline{n_frames_equal, detected_agree, max_abs_diff_both}`;
`sequence_top1{live_png, live_jpeg90, kaggle_npz}`. KHÔNG có mảng landmark trong JSON (test trong
`tests/test_frontend_contract.py` cấm các khóa `landmarks`/`raw_landmarks`/`coords`). Không có ngưỡng pass cho hai so sánh
JPEG và Kaggle — chỉ ghi nhận. Reviewer chạy lại → phần thân giống hệt, trừ `generated_by`/thời gian.

**AC7 — Thư viện JS (`frontend/tests/*.test.mjs`, `node --test`).**
- a. `wsUrl({protocol: 'http:', host: 'localhost:3000'}, '/ws/live-stream') === 'ws://localhost:3000/ws/live-stream'`;
  `https:` → `wss://`; giữ nguyên port của host.
- b. `reduceLive` với message mẫu viết theo lược đồ §3.6 kế hoạch 04 (mẫu giao thức, không phải dữ liệu):
  session_info v2 legacy và harmonized; `protocol_version: 3` → `fatal === 'protocol_mismatch'`; legacy CONFIRMED
  chuyển trạng thái thêm 1 từ, CONFIRMED lặp cùng gloss không thêm; `buffer_capacity` lấy từ message; `frame_result`
  harmonized KHÔNG đổi `lastSign`; hai `sign_result` liên tiếp cùng gloss → `words` có CẢ HAI; `client_e2e_ms ===
  nowMs - trigger_client_timestamp`; `sign_discarded` lưu `reason`; `error message_too_large` → `fatal`; type lạ →
  `unknownMessages` +1; state đầu vào được `deepFreeze` và không bị sửa.
- c. `buildSequenceBody`: frame không tay → `null` (không bao giờ khung toàn 0); sắp theo `frame_seq` khi đầu vào lộn
  xộn; bỏ frame khác `segment_id`; kích thước đổi → lỗi `frame_size_changed`; quá `max_frames_per_segment` → lỗi; rỗng →
  lỗi; `source_mirrored === false`; `timestamps_ms` không giảm.
- d. (Python, `tests/test_frontend_contract.py`) Chéo ngôn ngữ: lấy dãy `hand_frame` live của 1 clip hauuto (tạo trong
  test như AC5) → ghi JSON tạm → `node frontend/tests/build_body_cli.mjs <in> <out>` → body bằng hệt body Python dựng
  từ npz offline (AC5-b), rồi POST → 200. `skipUnless(shutil.which("node"))`; trên máy này không skip.

**AC8 — Guard mã nguồn frontend (`tests/test_frontend_contract.py`).** Duyệt mọi file `frontend/src/**/*.{js,jsx}`:
không chứa `Math.random`; không chứa `:8000`; không có literal `ws://`/`wss://`; không có `data:image/jpeg;base64,/9j/`;
không có chuỗi `'/api/fingerspelling'` đứng riêng (endpoint ảnh cũ; regex khớp dấu nháy đóng ngay sau `fingerspelling`);
không có `bufferCapacity={60}` và `25 lớp`. Test tự kiểm: đưa từng mẫu vi phạm (chuỗi trong bộ nhớ) vào hàm guard → hàm
báo lỗi.

**AC9 — Build, không thêm gói.** `cd frontend && npm run build` exit 0 (build vào `frontend/dist`, đã bị ignore);
`npm ls --depth=0` giống hệt file B0; `git diff P6 HEAD -- frontend/package-lock.json` rỗng; diff `frontend/package.json`
chỉ thêm `"test"`.

**AC10 — Smoke test Phase 12.** `.venv/Scripts/python scripts/smoke_test_phase12.py` exit 0 và in dòng PASSED, chạy 2
lần: model mặc định và `VSL_MODEL_TYPE=stgcn_h360`. Output (cả mã lỗi thật của bước text rác và số message theo `type`)
chép vào `06-progress.md`.

**AC11 — `docs/phase12_api.md` (`tests/test_frontend_contract.py`).**
- Không chứa `0.0.0.0` và `ws://localhost:8000`.
- Chứa MỌI mã lỗi mà `backend/main.py` phát ra (test tự trích bằng regex từ `_ws_error("…"`/`WsError("…"`, không gõ tay),
  mọi `reason` của `sign_discarded` (trích từ `src/inference/sign_segmenter.py`/`backend/main.py`), mọi `type` message của
  cả hai WS (`session_info`, `frame_result`, `sign_result`, `sign_discarded`, `error`, `reset_done`, `hand_frame`),
  `VSL_CORS_ORIGINS`, `1008`, `1009`, `1011`, `dropped_frames`, `trigger_client_timestamp`, `/ws/hand-landmarks`.
- Có mục "Giới hạn" nêu: ký hiệu có nhịp nghỉ có thể bị phát 2 lần (W03251B), segmenter chưa chỉnh tham số, landmark
  Cấp 1 live dùng JPEG (ảnh hưởng ghi ở AC6), Origin check không chặn client không phải trình duyệt.

**AC12 — E2E fullstack trên clip thật (`scripts/e2e_fullstack.py`).** 3 lần chạy tại HEAD sạch
(`git status --porcelain -- backend src frontend scripts tests` rỗng), mỗi lần 1 JSON trong `reports/e2e_<YYYY-MM-DD>/`:
`fingerspell_default.json`, `word_default.json`, `word_stgcn_h360.json`. Chung cho cả 3:
- `/api/health` 200 (`status == "ok"`) và trang 3000 200 trong 180 s; ghi `model_type`, `is_default` từ health.
- 0 console `error`, 0 `pageerror`, 0 `requestfailed`, 0 HTTP ≥ 400 (lỗi nguyên văn được liệt kê nếu có).
- Mọi URL WS bắt đầu bằng `ws://localhost:3000/ws/`; không URL nào chứa `:8000`. Không request nào tới
  `POST /api/fingerspelling` (endpoint ảnh cũ).
- Sau khi dừng: cổng 8000 và 3000 rảnh; không còn tiến trình con.
- **Đánh vần** (`a_hau_A_001.mp4`): status `available: true`; WS hand-landmarks nhận `session_info`; ≥ 1
  `POST /sequence` 200; MỌI body gửi đi: `len(landmarks) == len(handedness) == len(timestamps_ms) ≤ 300`, ≥ 3 khung
  không null, không khung nào có 21 điểm trùng hệt, mọi |v| ≤ 10, `timestamps_ms` không giảm, `source_mirrored == false`;
  text `fs-prediction` == `prediction` của response cuối; `fs-confidence` hiển thị đúng `confidence` đó; bấm `fs-add` →
  `POST /compose` 200 và `fs-composed` == `text` của response. Ghi `prediction` và nhãn clip vào JSON dưới khóa
  `info_not_accuracy`.
- **Ký từ mặc định (legacy)**: message WS đầu là `session_info` với `protocol_version == 2`, `pipeline == "legacy"`;
  ≥ 30 `frame_result`; 0 message `error`; `live-pipeline` hiện "legacy"; sau `camera-stop`, danh sách `live-top5` ==
  `top5` của `frame_result` cuối cùng nhận được.
- **Ký từ `VSL_MODEL_TYPE=stgcn_h360`**: `pipeline == "harmonized_v1"`; mọi `frame_result.prediction is null`; thấy ≥ 1
  `frame_result.status == "RECORDING"` và `live-recording` hiện ra ít nhất một lần; ≥ 1 `sign_result` hoặc
  `sign_discarded` trong tối đa 3 vòng lặp clip; nếu có `sign_result`: `live-gloss` == `gloss` và `live-top5` == `top5`
  của nó; 0 message `error`. Nếu 0 sự kiện: DỪNG, báo planner (KHÔNG chỉnh segmenter hay tham số).
- JSON có `generated_by{command, git_commit, code_dirty: false}`; không chứa đường dẫn tuyệt đối, landmark, hay ảnh.

**AC13 — Quy trình.** Mỗi commit có output `impact`/`detect-changes` (risk thật) trong message; không amend; 3 file ` D`
của người dùng vẫn chưa staged; `docs/plans/06-progress.md` có output thật cho từng bước; `docs/progress_log.md` THÊM 1
dòng (không sửa dòng cũ) nêu: commit, số test trước → sau, 3 JSON e2e, quyết định §3.8, các việc theo sau đề xuất.
Kết luận vslt-reviewer = APPROVE.

## 6. Rủi ro dữ liệu/ML

**Lệch train–realtime, Cấp 1 (quan trọng nhất).**
- Cùng extractor + tham số + tracker mới mỗi lượt ghi được chứng minh bằng AC4-a/AC5 (PNG, cùng máy). Những gì AC5 KHÔNG
  chứng minh (chỉ ghi nhận ở AC6 hoặc chưa đo):
  - **Nén JPEG** (client gửi JPEG `FS_JPEG_QUALITY`) so với frame giải mã từ mp4 lúc train: AC6 ghi `live_jpeg90_vs_live_png`.
  - **Nền tảng:** landmark train trích trên Kaggle (Linux), live chạy Windows: AC6 ghi `kaggle_npz_vs_local_offline`.
  - **Tốc độ khung:** train hauuto ≈ 23.6 fps, mọi frame; live phụ thuộc webcam và `FS_MAX_IN_FLIGHT`. Với
    `resample: "frame_index"`, ít frame hơn → lấy mẫu thời gian khác. UI hiện fps hiệu dụng và `client_skipped`; chưa đo
    ảnh hưởng lên nhãn.
  - **Cắt ký hiệu thủ công:** người dùng bấm Ghi/Dừng nên đầu/cuối có thể chứa đoạn đưa tay lên/hạ tay, khác cách cắt clip
    train (chưa kiểm chứng clip hauuto được cắt thế nào). Không thêm luật cắt tự động khi chưa có dữ liệu webcam (Bước 5).
  - **Độ phân giải:** webcam có thể trả khác 640×480; tỉ lệ khung được bù qua `frame_width/height` (kế hoạch 03), nhưng
    độ nhạy MediaPipe theo độ phân giải chưa đo. UI hiện độ phân giải.
- Lật gương: frame không lật ở cả hai phía, `source_mirrored: false`; giữ đúng bất biến 4 của skill.

**Lệch train–realtime, Cấp 2.** Không đổi gì ở đường live (kế hoạch 04 giữ nguyên). Các thí nghiệm còn thiếu của review 04
mục 13 (JPEG q0.75, rơi frame thật, nhiều ký hiệu một phiên, webcam người dùng) vẫn thiếu; e2e của việc này KHÔNG phải
đánh giá chất lượng và không được trích như vậy.

**Rò rỉ / TEST.** Không train, không chọn model. E2E và AC5 chỉ dùng clip TRAIN (hauuto là dữ liệu train của model Cấp 1;
clip Ký từ lấy từ split TRAIN); KHÔNG chạm clip TEST/VAL (TEST chỉ chạy một lần, để dành cho GATE).

**Cỡ mẫu.** AC5 10 clip là kiểm tương đương CODE (tất định), không phải tỉ lệ. E2E 1 clip/kịch bản chỉ chứng minh "chạy
được". `prediction` trong JSON e2e ghi dưới khóa `info_not_accuracy`; không suy ra độ chính xác từ đó.

**Nguồn gốc / giấy phép.** hauuto: giấy phép unknown, chỉ dùng nội bộ (`docs/data_registry.md` 1b); mã người ký trong id
clip giữ nguyên theo quyết định (a) 2026-09-28; y4m/video/frame KHÔNG vào git; JSON không chứa landmark. QIPEDC video
chỉ đọc.

**Bảo mật.** Origin check chỉ chặn trang web khác origin trong trình duyệt, không chặn client tự viết; bảo vệ chính là bind
127.0.0.1. Endpoint mới mở thêm bề mặt: mỗi kết nối giữ 1 graph MediaPipe và xử lý tuần tự; chưa có giới hạn số kết nối
(giống `/ws/live-stream` hiện tại) — chấp nhận vì chỉ nghe cục bộ; ghi vào `docs/phase12_api.md` mục Giới hạn nếu coder
thấy cần. `VSL_CORS_ORIGINS` sai → backend không khởi động (fail-fast, không lặng lẽ mở rộng).

**Trung thực UI (DoD 6).** Mọi chữ/từ/câu hiển thị lấy từ response server; khi model không sẵn sàng thì khóa chức năng và
nói rõ; không còn frame giả lập; `confidence` ghi là độ tin cậy của model.

## 7. Điểm dừng

**Không có điểm dừng CẦN NGƯỜI DÙNG trước khi code.** Lý do:
- CORS/Origin/bind đã có quyết định (2026-09-28): chỉ origin dev, không `*` kèm credentials.
- Model mặc định KHÔNG đổi; `VSL_MODEL_TYPE=stgcn_h360` chỉ đặt trong môi trường của tiến trình e2e/smoke.
- Không cần dữ liệu mới từ người dùng (dùng video cục bộ đã có; webcam thật là Bước 5).
- Không đụng thay đổi chưa commit của người dùng; không xóa file (`RealtimeStream.jsx` giữ lại, hỏi sau); không có hành
  động không hoàn tác được; không cài gói; không Kaggle.

**Điểm dừng có điều kiện trong lúc làm (coder DỪNG, báo planner/orchestrator; KHÔNG tự nới tiêu chí):**
1. AC5-a không bằng hệt (landmark live ≠ `_extract_one` trên cùng máy) → báo planner.
2. AC12 kịch bản `stgcn_h360` có 0 `sign_result`/`sign_discarded` → báo planner (không chỉnh segmenter/tham số).
3. Một test đã có bị vỡ do CORS/Origin/bind hoặc endpoint mới → báo planner (không sửa test cũ).
4. Cần cài gói npm/pip, cần tải trình duyệt/model từ mạng, hoặc Edge không có ở máy → báo orchestrator (hỏi người dùng).
5. Cần xóa file, hoặc đổi policy hệ thống (ExecutionPolicy toàn máy) để chạy `start_fullstack.ps1` → hỏi người dùng.
6. Phát hiện vấn đề dữ liệu mới (ví dụ `manifest.csv` có nhiều `mediapipe_version`, video hauuto không khớp npz) → báo
   planner (điểm dừng "vấn đề dữ liệu mới" của autopilot mục 5).
