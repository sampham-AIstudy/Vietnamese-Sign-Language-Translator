# Kế hoạch 04: nối harmonize() vào đường live cho chế độ "Ký từ" (Cấp 2)

**Điểm dừng:** KHÔNG có điểm dừng bắt buộc khi làm đúng kế hoạch. Model mặc định Cấp 2 KHÔNG đổi. Có 3 điểm dừng
CÓ ĐIỀU KIỆN (xem §7). Nếu gặp một trong số đó, coder ghi "CẦN NGƯỜI DÙNG" hoặc "CẦN PLANNER" và dừng.

- Nhánh: `feat/vslt-complete`. HEAD lúc lập kế hoạch: `9f4eb68`.
- Coder 04 chỉ chạy SAU khi kế hoạch 03 được APPROVE. Kế hoạch 03 có thể còn sửa `backend/main.py`, nên số dòng ở
  §2 có thể lệch. Khi đó coder tìm theo tên symbol, không theo số dòng.
- Căn cứ: quyết định của người dùng ngày 2026-09-27, mục 1, 3 và 4 (`docs/progress_log.md`, mục "Quyết định của người
  dùng tại điểm dừng 4c").

---

## 1. Mục tiêu và DoD

**Mục tiêu.**
- Thêm vào `/ws/live-stream` một đường tiền xử lý thứ hai, gọi là "harmonized_v1". Đường này:
  - hạ frame về chiều cao 360 TRƯỚC MediaPipe;
  - trích landmark bằng CÙNG extractor lúc train;
  - gom trọn MỘT ký hiệu (từ lúc bắt đầu chuyển động đến lúc tay nghỉ);
  - gọi `harmonize()` với đúng tham số `preprocessing` lưu trong checkpoint, tức là có giữ cắt đoạn nghỉ;
  - rồi mới dự đoán top-5 + confidence.
- Đường cũ ("legacy": cửa sổ trượt 60 frame + smoother) giữ nguyên cho model mặc định.
- Backend chọn đường nào là do checkpoint tự mô tả. Model mặc định không đổi. Ứng viên H-keepz-360 chỉ bật được bằng
  biến môi trường, để phục vụ GATE.

**DoD phục vụ.**
- DoD 3 (phía backend): chế độ Ký từ trả top-k + confidence qua `/ws/live-stream`. Đường mới dùng được với H-keepz-360,
  nhưng model mặc định vẫn là model cũ cho tới GATE.
- DoD 6: không có kết quả giả.
  - Không dự đoán khi đoạn không có tay.
  - Đoạn quá dài, quá ngắn hoặc bị đứt thì bỏ, có ghi lý do.
  - Bỏ số liệu độ trễ bịa. `backend/main.py` hiện tính `server_preprocess_ms = latency*0.4` và
    `server_infer_ms = latency*0.6`.
- DoD 7: test tương đương train–realtime (cùng một video qua hai đường cho ra cùng tensor), cộng unit test và contract
  test.
- DoD 8: chưa đo trong việc này. Thiết kế thêm trường thời gian thật vào message để việc đo sau này dùng được.
- Bảo mật WebSocket: giới hạn kích thước message; kiểm tra định dạng và kích thước ảnh TRƯỚC khi giải mã toàn bộ; kiểm
  tra `timestamp` và `config`.

---

## 2. Hiện trạng (HEAD `9f4eb68`)

### 2.1 Phía train (nguồn chân lý; KHÔNG được sửa)

**`src/data/landmark_extractor.py` — `CleanHolisticExtractor`**
- `:36-42`: tham số `process_height`.
- `:66-69`: nếu chiều cao frame khác `process_height` thì `cv2.resize(..., INTER_AREA)` trên ảnh RGB, giữ tỉ lệ, chiều
  rộng = `round(w*360/h)`.
- `:82`: ngưỡng visibility của pose là `> 0.1`.
- `extract_from_video` `:102-160`: đọc video bằng `cv2.VideoCapture`, chuyển BGR→RGB, rồi gọi `extract_frame`.
  `fps` lấy từ `CAP_PROP_FPS`.

**`scripts/extract_keypoints_batch.py`**
- `_extract_one` `:30-53`: tạo MỘT extractor mới cho mỗi video, với `process_height=meta["process_height"]`.
- npz lưu metadata gồm `fps`, `width`, `height` (kích thước GỐC, trước resize).
- Kernel trích 360 px (`kaggle/vsl-extract-qipedc360-s*/extract_qipedc360.py`) chạy trên Linux: py3.11,
  mediapipe 0.10.14, `opencv-python-headless==4.10.0.84`, `numpy<2`.

**`src/data/harmonized.py`**
- `HARMONIZED_DEFAULT` `:28-42`.
- `_normalise` `:45-65`: bù tỉ lệ khung hình, lấy tâm giữa hai vai, scale theo MEDIAN độ rộng vai của cả đoạn được
  đưa vào.
- `hand_activity` `:68-77`: tốc độ = `diff * fps`, tức là giả định frame cách đều.
- `active_span` `:80-88`.
- `harmonize` `:118-153`: nhận `timestamps_s` tùy chọn; `rng=None` nghĩa là không augmentation.
- `HarmonizedDataset.__getitem__` `:170-184`: `fps` lấy từ metadata npz; `aspect = width/height` lấy từ CSV.
- Theo REPORT §1.2, trong khoảng c65032a→57957da không có commit nào đổi file này. Run H-keepz-360 train ở commit
  `c65032a`.

**`scripts/train_unified.py`**
- `:176-181`: `preprocessing = {**HARMONIZED_DEFAULT, hand_z, process_height, trim, extractor, mediapipe_version}`.
- `:211`: `preprocessing` được lưu vào checkpoint.
- `--process-height` chỉ để GHI LẠI (`:140-141`). Việc resize thật sự xảy ra ở bước trích landmark.

**Checkpoint ứng viên:** `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt`
- Có trên đĩa, gitignored.
- sha256 `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e` (REPORT §1.4).
- Cấu hình theo REPORT §3.1: `process_height=360`, `trim=True`, `hand_z=True`, `target_len=32`.
- Bản lưu trữ: Kaggle dataset private `phmvnsm33/vslt-step4-artifacts`.

**Môi trường cục bộ**
- `.venv` có mediapipe `0.10.14` (`.venv/Lib/site-packages/mediapipe/__init__.py:26`).
- Video QIPEDC có sẵn cục bộ ở `data/Dataset/Videos/*.mp4` (ví dụ `D0001N.mp4`). Đây là dữ liệu của người dùng,
  untracked. Chỉ ĐỌC, không commit.
- `data/splits/unified/{train,val,test}.csv` có cột `width`, `height`, `file_name`.

### 2.2 Phía live hiện tại (legacy)

**`backend/main.py`**
- `:88-101`:
  - `MODEL_TYPE = VSL_MODEL_TYPE` (mặc định `"stgcn"`);
  - `STGCN_VARIANTS` có `stgcn` → `checkpoints/stgcn_tier2_indomain.pt` và `stgcn_unified`;
  - `VSL_STGCN_CKPT` ghi đè được đường dẫn.
  - **Lỗ hổng lệch train–live:** trỏ `VSL_STGCN_CKPT` tới một checkpoint harmonized thì model vẫn được nạp, nhưng
    input lại đi qua tiền xử lý legacy (60 frame, pad). Kết quả sai mà không có cảnh báo nào.
- `get_or_load_predictor` `:104-116`.
- `health` `:350-369`: nếu nạp model lỗi thì trả 500.
- `model_info` `:372-390`: ghi cứng `target_sequence_length: 60`.
- `_decode_frame` `:710-737`: gọi `cv2.imdecode` ngay, không kiểm tra định dạng hay kích thước trước.
- `_process_frame_worker` `:740-878`:
  - `:872-873` là số liệu bịa (`latency_ms * 0.4` / `* 0.6`).
  - `:815-834` dịch câu khi smoother xác nhận.
- `websocket_live_stream` `:881-1029`:
  - `receive_loop` `:921-955` không giới hạn kích thước message.
  - `:947` gọi `float(cfg["confidence_threshold"])` mà không kiểm tra, nên nhận cả NaN.
  - Kiểu "chỉ giữ frame mới nhất" (một slot duy nhất) làm rơi frame khi worker bận.
- `:1032-1034`: `uvicorn.run(...)` không đặt `ws_max_size`. Giá trị mặc định của uvicorn là 16 MiB.

**`src/inference/realtime_pipeline.py`** `:29-164`
- Dùng `RealtimeLandmarkExtractor`, không resize.
- `VSLPreprocessingPipeline(target_len=60, pad)`.
- Bỏ qua `preprocessing.features`.

**`src/inference/realtime_extractor.py`**
- `:96` đặt ngưỡng visibility của pose là `> 0.2`, KHÁC `CleanHolisticExtractor` (`> 0.1`). Đây là lệch có từ trước
  của đường legacy. Không sửa trong việc này (xem §6).

**Frontend** (chỉ để biết hợp đồng; KHÔNG sửa trong việc này)
- `frontend/src/components/RealtimeStream.jsx:283-295` gửi text JSON
  `{image: dataURL JPEG 0.75, timestamp: Date.now(), config}`.
- `:154` chỉ đọc message có `type === 'frame_result'`.
- `:156-186` đọc `metrics.*`.

**Test hiện có:** `tests/test_harmonized.py` (6 ca, fixture), `tests/test_realtime.py` (legacy).
`tests/test_ws_throughput.py` là script, không có test unittest. Chưa có test nào cho `/ws/live-stream`.

### 2.3 Còn thiếu
1. Đường live gọi `harmonize()` với process_height 360.
2. Bộ gom ký hiệu.
3. Chọn đường xử lý theo checkpoint.
4. Hợp đồng message cho trạng thái "đang ghi ký hiệu".
5. Giới hạn message WS.
6. Test tương đương trên video thật.
7. Số liệu thời gian thật.

---

## 3. Thiết kế

### 3.1 Nguyên tắc
- **Không sửa code của phía train.**
  - `git diff c65032a HEAD -- src/data/harmonized.py` phải rỗng trước và sau việc này. Không đổi file này; code mới
    chỉ IMPORT `harmonize`, `_normalise`, `hand_activity`, `active_span` từ đó.
  - `src/data/landmark_extractor.py`, `scripts/extract_keypoints_batch.py`, `scripts/train_unified.py` cũng không đổi.
- **Cùng extractor.** Đường mới dùng chính `CleanHolisticExtractor(process_height=ckpt["preprocessing"]["process_height"])`
  và gọi `extract_frame(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))`, giống hệt `extract_from_video`.
  - Không dùng `RealtimeLandmarkExtractor` cho đường mới.
  - Landmark cho lớp phủ skeleton dựng lại từ `coords` (pose 0–24, tay 25–45 và 46–66). Làm vậy thì không cần object
    `results` của MediaPipe, và không phải sửa extractor.
- **Tham số lấy từ checkpoint.** `harmonize(kps, vis, aspect, fps, cfg=ckpt["preprocessing"], timestamps_s=...)`.
  - Không bao giờ truyền `HARMONIZED_DEFAULT` hay hằng gõ tay.
  - `rng` luôn là `None`: live không có augmentation.
- **Hai đường cùng tồn tại.** Đường `legacy` giữ nguyên hành vi dự đoán; `realtime_pipeline.py`, `realtime_extractor.py`
  và `predictor.py` không đổi. Đường `harmonized_v1` là đường mới.

### 3.2 Chọn đường xử lý và chọn model

Hàm mới `live_pipeline_for(preprocessing: dict | None) -> "legacy" | "harmonized_v1"` đặt trong
`src/inference/harmonized_live.py`:

| Điều kiện | Kết quả |
|---|---|
| `preprocessing` rỗng hoặc None, hoặc không có khóa `features` (checkpoint cũ, `PREPROCESSING` của run baseline) | `"legacy"` |
| `features == "harmonized_v1"` | `"harmonized_v1"`, SAU khi kiểm tra đủ các điều kiện dưới |
| `features` là giá trị khác | `ValueError` → model không dùng được |

Với `harmonized_v1`, kiểm tra các điều kiện sau; sai một điều kiện là `ValueError`:
- `extractor == "CleanHolisticExtractor"`;
- `mediapipe_version == mediapipe.__version__`;
- `process_height` là None hoặc int trong khoảng 1..2160;
- `target_len` là int ≥ 2;
- có đủ các khóa `trim`, `hand_z`, `rest_y`, `active_speed`, `pad_s`, `max_gap_s`, `mask_resting_hand`.

**Chọn model trong `backend/main.py`:**
- `DEFAULT_MODEL_TYPE = "stgcn"`. Không đổi → vẫn là `checkpoints/stgcn_tier2_indomain.pt`, đường legacy.
- Thêm biến thể `"stgcn_h360"`:
  - `ckpt = "reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt"`;
  - `classes = None` (dùng `label_map` trong checkpoint);
  - `sha256 = "648a7825…c9b59e"` (đủ 64 ký tự, lấy từ REPORT §1.4).
- Bật bằng `VSL_MODEL_TYPE=stgcn_h360`.
- Khi nạp một biến thể có `sha256`: băm file trước. Nếu băm lệch thì từ chối nạp và coi là model không dùng được. Không
  có chuyện fallback im lặng về model khác.
- `VSL_STGCN_CKPT` vẫn ghi đè được. Khi đó không kiểm sha, `is_default=false`, và đường xử lý do `preprocessing` của
  checkpoint quyết định. Nhờ vậy lỗ hổng ở §2.2 được bịt.
- `IS_DEFAULT_MODEL = (MODEL_TYPE == DEFAULT_MODEL_TYPE and "VSL_STGCN_CKPT" not in os.environ)`.
- **Model không dùng được:**
  - `/api/health` trả **503** `{"status": "model_unavailable", "detail": <≤200 ký tự>}` thay vì 500.
  - WS gửi `error{code:"model_unavailable"}` rồi đóng với mã 1011.
- `/api/health` và `/model/info` THÊM các trường:
  - `pipeline`;
  - `checkpoint` (basename);
  - `checkpoint_sha256`;
  - `is_default_model`;
  - `target_sequence_length`: lấy từ `preprocessing` (harmonized là 32, legacy giữ 60);
  - `process_height`.
- Ghi cách bật ứng viên vào docstring đầu `backend/main.py`. README để cho việc tài liệu (DoD 9).

### 3.3 Luồng dữ liệu của đường harmonized_v1
```
client (640×480, JPEG 0.75, không lật gương) --WS text JSON {image, timestamp(ms)} hoặc binary--> receive_loop
  receive_loop: kiểm tra kích thước message (≤ WS_MAX_MESSAGE_BYTES), parse một lần, kiểm tra timestamp/config
    → slot "frame mới nhất" (giữ kiểu chỉ-frame-mới-nhất; đếm received_seq và số frame bị rơi)
worker (ThreadPool):
  kiểm tra định dạng (magic bytes JPEG/PNG) + đọc kích thước từ HEADER (không giải mã toàn bộ)
    → từ chối nếu cạnh > WS_MAX_FRAME_SIDE hoặc cao < process_height
  → cv2.imdecode → BGR → RGB → CleanHolisticExtractor(process_height=360).extract_frame   [resize 480×360 trước MediaPipe]
  → SignSegmenter.push(coords[67,3], vis[67], t_s, frame_wh)          # src/inference/sign_segmenter.py, thuần numpy
       độ hoạt động của frame = hand_activity(_normalise(cửa sổ ≤ activity_window_s), fps_cửa_sổ, cfg_ckpt)[-1]
       state: idle → recording → (nghỉ ≥ rest_hold_s) → PHÁT đoạn → idle
  → nếu phát: harmonize(buffer_kps, buffer_vis, aspect=W/H gốc, fps=(n-1)/(t_n-t_1),
                        cfg=ckpt.preprocessing, timestamps_s=t - t_0)
       → nếu jm[:, 25:67].sum() == 0 → sign_discarded(no_hand_frames), KHÔNG dự đoán
       → predictor.predict(seq[32,67,3], jm, tm, top_k=5) → sign_result
  → frame_result (trạng thái ghi, landmark lớp phủ, thời gian thật)
```

- `aspect` là W/H của frame GỐC. Khi train, `aspect` là width/height gốc trong CSV, cũng là kích thước trước resize.
- **Thời gian:** nguồn timestamp của phiên được chốt ở frame đầu tiên được chấp nhận.
  - Nếu frame đó có `timestamp` hợp lệ thì dùng `"client"`: đơn vị ms, số hữu hạn, TĂNG NGẶT so với frame trước.
  - Nếu không thì dùng `"server"`: `time.monotonic()` lúc nhận trong `receive_loop`.
  - Sau đó, một frame lệch nguồn (thiếu timestamp khi nguồn là client), hoặc có timestamp không tăng, bị từ chối với
    lỗi `bad_timestamp` và KHÔNG được thêm vào bộ đệm.
- Vì có kiểu chỉ-frame-mới-nhất, frame có thể không cách đều. `harmonize` vẫn resample theo THỜI GIAN. Riêng
  `hand_activity` dùng `fps` trung bình của đoạn (rủi ro ở §6).

### 3.4 `SignSegmenter`: bộ gom ký hiệu (module thuần, không import torch, cv2 hay mediapipe)

Tham số chia làm hai nhóm.

**Nhóm lấy từ checkpoint** (bắt buộc; không có giá trị mặc định trong segmenter): `rest_y`, `active_speed`, `pad_s`,
`max_gap_s`, `mask_resting_hand`.

**Nhóm chỉ dùng cho live** (KHÔNG có trong checkpoint): hằng `SEGMENTER_DEFAULT`.
- Đây là giá trị thiết kế ban đầu, CHƯA đo. Chỉ được chỉnh dựa trên clip TRAIN hoặc bộ webcam của người dùng
  (Bước 5), không bao giờ dựa trên TEST.
- Các giá trị:

| Tham số | Giá trị |
|---|---|
| `onset_min_s` | 0.10 |
| `pre_roll_s` | 0.50 |
| `rest_hold_s` | 0.50 |
| `min_sign_s` | 0.30 |
| `max_sign_s` | 8.0 |
| `stream_gap_s` | 1.0 |
| `activity_window_s` | 1.0 |
| `max_buffer_frames` | 1024 |

- Ràng buộc kiểm lúc khởi tạo (sai thì `ValueError`):
  - `pre_roll_s ≥ pad_s`;
  - `rest_hold_s ≥ pad_s`;
  - `rest_hold_s > max_gap_s`. Nhờ vậy một lần mất tay ngắn mà `harmonize` còn nội suy được sẽ không cắt đôi ký hiệu.

**Máy trạng thái:**

| Trạng thái | Điều kiện chuyển | Tác dụng |
|---|---|---|
| `idle` | frame hoạt động liên tục ≥ `onset_min_s` → `recording` | vòng đệm giữ `pre_roll_s` gần nhất; đoạn bắt đầu từ đầu vòng đệm |
| `recording` | không hoạt động liên tục ≥ `rest_hold_s` → PHÁT, về `idle` | nếu thời lượng hoạt động (frame hoạt động đầu → cuối) < `min_sign_s` thì bỏ, lý do `too_short` |
| `recording` | thời lượng > `max_sign_s` → bỏ, lý do `too_long`, sang `wait_rest` | không dự đoán |
| `recording` | khoảng cách timestamp > `stream_gap_s` → bỏ, lý do `stream_gap`, sang `idle` | không dự đoán |
| `recording` | kích thước frame (W,H) đổi → bỏ, lý do `frame_size_changed`, sang `idle` | không dự đoán |
| bất kỳ | client gửi `control/reset` → nếu đang ghi thì bỏ, lý do `reset`, sang `idle` | xóa bộ đệm |
| `wait_rest` | frame không hoạt động liên tục ≥ `rest_hold_s` → `idle` | chặn kích hoạt lại khi tay vẫn đang giơ |

- Đoạn được PHÁT gồm: vòng đệm tiền cuộn + các frame ghi được + phần nghỉ `rest_hold_s`.
  - `harmonize` tự cắt về khoảng hoạt động ± `pad_s` theo đúng luật lúc train. Segmenter chỉ lo đoạn chứa trọn khoảng
    hoạt động.
- Bộ đệm không bao giờ vượt `max_buffer_frames`. Nếu chạm trần khi đang ghi thì bỏ đoạn, lý do `too_long`.
- API:
  - `push(coords, vis, t_s, frame_wh) -> SegmenterEvent | None`;
  - `reset() -> SegmenterEvent | None`;
  - thuộc tính `state`, `segment_id`, `recording_s`, `n_frames`.
- Event có thể là `Emit(kps, vis, t, frame_wh, active_start_s, active_end_s)` hoặc `Discard(reason, duration_s, frames)`.

### 3.5 `HarmonizedLiveSession` (`src/inference/harmonized_live.py`)
- Khởi tạo: `HarmonizedLiveSession(predictor, preprocessing, segmenter_cfg=SEGMENTER_DEFAULT, extractor=None)`.
  - Tạo extractor `CleanHolisticExtractor(process_height=preprocessing["process_height"])`.
  - Gọi `_get_holistic()` để dựng graph trước, KHÔNG xử lý frame giả. Xử lý một frame giả sẽ đổi trạng thái tracker so
    với lúc train.
- `process(frame_bgr, t_s) -> dict` gồm:
  - `coords`, `vis`, `landmarks` (dạng lớp phủ);
  - `event`: `sign_result`, `sign_discarded` hoặc None;
  - các mốc thời gian đo bằng `time.perf_counter`: `extract_ms`, `segment_ms`, `harmonize_ms`, `infer_ms`.
- `finalize_clip()`: CHỈ dùng cho test tương đương. Nó gọi `harmonize` trên TOÀN BỘ frame đã nhận, bỏ qua segmenter,
  qua đúng hàm `_harmonize_buffer` mà đường phát đoạn dùng.
- `close()`.

### 3.6 Hợp đồng `/ws/live-stream` (protocol_version 2; chỉ THÊM, không bỏ trường cũ của legacy)

**Client → server**

| Message | Dạng |
|---|---|
| Frame (text) | `{"image": "data:image/jpeg;base64,..." \| base64, "timestamp": number(ms)?, "config": {"confidence_threshold": number}?}` |
| Frame (binary) | byte JPEG hoặc PNG; không có timestamp, nên nguồn timestamp là server |
| Điều khiển | `{"type": "control", "action": "reset"}` |

**Giới hạn** (hằng trong `backend/main.py`, áp cho CẢ HAI đường)
- `WS_MAX_MESSAGE_BYTES = 1_048_576`: đo trên byte UTF-8 của text hoặc độ dài binary. Vượt thì gửi
  `error{message_too_large}` rồi đóng 1009. Thêm `--ws-max-size 1048576` vào `start_fullstack.ps1` và
  `ws_max_size=...` vào `uvicorn.run` ở `__main__`.
- Chỉ nhận JPEG hoặc PNG, kiểm bằng magic bytes. Kích thước đọc từ header mà không giải mã toàn bộ: dùng PIL
  `Image.open(...).size` nếu `.venv` có Pillow; nếu không thì tự parse SOF (JPEG) hoặc IHDR (PNG). Không cài gói mới
  nếu không cần.
- `WS_MAX_FRAME_SIDE = 1920`: cạnh lớn hơn thì trả `frame_too_large`.
- Đường harmonized: frame có chiều cao < `process_height` thì trả `frame_too_small`. Không phóng to lên 360, vì lúc train
  chỉ có thu nhỏ từ 720.
- `confidence_threshold` phải là số hữu hạn trong [0, 1]. Sai thì trả `bad_config`, ngưỡng giữ nguyên. Ngưỡng này chỉ
  dùng ở legacy.
- Lỗi của MỘT message KHÔNG làm đóng phiên, trừ `message_too_large` và `model_unavailable`.
- `detail` dài ≤ 200 ký tự và KHÔNG lặp lại dữ liệu client gửi.

**Server → client**

1. `session_info`: gửi đầu tiên, cho cả hai đường:
   ```
   {"type":"session_info","protocol_version":2,"pipeline":"harmonized_v1"|"legacy",
    "model":{"model_type","checkpoint","checkpoint_sha256","is_default","num_classes"},
    "preprocessing":{"target_len","process_height","trim","hand_z","rest_y","active_speed","pad_s","max_gap_s"} | {"target_len":60},
    "segmenter": {…SEGMENTER_DEFAULT} | null,
    "limits":{"max_message_bytes","max_frame_side","min_frame_height"|null}}
   ```
2. `frame_result`: một message cho mỗi frame được xử lý.
   - **Legacy:** giữ nguyên mọi khóa cũ. `metrics` sửa thành số đo thật:
     - `server_infer_ms` = `prediction.latency_ms` nếu `is_new_prediction`, ngược lại là 0.0;
     - `server_preprocess_ms` = thời gian `pipeline.process_frame` − `server_infer_ms`;
     - THÊM `decode_ms`, `postprocess_ms`.
   - **Harmonized:**
     ```
     {"type":"frame_result","pipeline":"harmonized_v1","frame_seq","received_seq","dropped_frames",
      "prediction":null,"gloss":null,"confidence":null,"top5":[],
      "status":"IDLE"|"RECORDING"|"WAIT_REST",
      "segment":{"state":"idle"|"recording"|"wait_rest","segment_id":int|null,"recording_s":float|null,
                 "frames":int,"max_sign_s":float},
      "is_signing": state=="recording", "hand_detected", "hand_active",
      "landmarks":{"pose":[[x,y]…25],"left_hand":[…21]|[],"right_hand":[…21]|[]},
      "latency_ms","fps",
      "metrics":{"client_timestamp","timestamp_source":"client"|"server","decode_ms","extract_ms",
                 "segment_ms","server_total_ms","server_fps"}}
     ```
     `frame_result` của đường harmonized KHÔNG BAO GIỜ mang dự đoán. Dự đoán chỉ có trong `sign_result`.
3. `sign_result`: chỉ có ở đường harmonized. Gửi TRƯỚC `frame_result` của frame làm kích hoạt, và hai message có cùng
   `frame_seq`.
   ```
   {"type":"sign_result","segment_id","frame_seq","prediction","gloss","confidence",
    "top5":[{"gloss","confidence"}×min(5,num_classes), giảm dần],"end_reason":"rest",
    "segment":{"start_s","end_s","duration_s","frames","effective_fps","dropped_frames","active_start_s","active_end_s"},
    "model":{"model_type","checkpoint","is_default","pipeline"},
    "metrics":{"harmonize_ms","infer_ms","finalize_ms","trigger_client_timestamp","rest_hold_s"}}
   ```
   - Các mốc `*_s` là số giây tính từ frame đầu tiên của phiên.
   - Để đo DoD 8 về sau:
     - độ trễ phía máy = thời điểm client nhận `sign_result` − `trigger_client_timestamp` (cùng đồng hồ client);
     - độ trễ người dùng cảm nhận = độ trễ phía máy + `rest_hold_s`.
4. `sign_discarded`:
   `{"type":"sign_discarded","segment_id","frame_seq","reason":"too_short"|"too_long"|"stream_gap"|"frame_size_changed"|"no_hand_frames"|"reset","segment":{"duration_s","frames"}}`.
5. `error`:
   `{"type":"error","code":"message_too_large"|"bad_message"|"decode_failed"|"unsupported_format"|"frame_too_large"|"frame_too_small"|"bad_timestamp"|"bad_config"|"model_unavailable","detail","received_seq"}`.

Phần hiển thị ("đang ghi ký hiệu", thanh thời lượng so với `max_sign_s`, lý do bỏ đoạn) thuộc Việc 5/6. Việc này chỉ
cung cấp hợp đồng và test hợp đồng.

---

## 4. Chia việc (mỗi bước ≤ ~2 giờ; làm theo thứ tự)

Trước khi sửa symbol có sẵn, chạy GitNexus `impact` (upstream) và ghi output vào báo cáo. Các symbol:
`get_or_load_predictor`, `health`, `model_info`, `_decode_frame`, `_process_frame_worker`, `websocket_live_stream`.
Nếu risk là `UNKNOWN` thì xác nhận thêm bằng text search. Chạy `detect-changes --scope all` trước MỖI commit, ghi risk
vào commit message. `git add` theo từng đường dẫn.

**B0. Kiểm tra trước (≤ 0.5 giờ, không sửa code).** Làm AC0. Nếu có một mục FAIL thì dừng (§7).

**B1. `src/inference/sign_segmenter.py` + `tests/test_sign_segmenter.py` (≤ 2 giờ).**
- Máy trạng thái theo §3.4.
- Chỉ import thêm từ `src.data.harmonized`.
- Viết test AC1 trước.

**B2. `src/inference/harmonized_live.py` + `tests/test_harmonized_live.py` (≤ 2 giờ).** Phụ thuộc B1.
- `live_pipeline_for`, `HarmonizedLiveSession`, `_harmonize_buffer`, `overlay_landmarks(coords, vis)`.
- Test AC2 dùng extractor và predictor giả. Riêng AC2-b dùng `CleanHolisticExtractor` thật, chỉ thay `_get_holistic`
  bằng đồ giả.

**B3. Nối vào `backend/main.py` (≤ 2 giờ).** Phụ thuộc B2.
- Biến thể `stgcn_h360`, kiểm sha256, `IS_DEFAULT_MODEL`, health 503.
- Tách hàm parse và kiểm tra message ra khỏi `receive_loop`.
- `session_info`; worker riêng `_process_frame_worker_harmonized`.
- Sửa số liệu bịa ở legacy.
- Giới hạn kích thước.
- Sửa `start_fullstack.ps1` và `__main__` (`ws_max_size`). Trước khi sửa `start_fullstack.ps1`, chạy `git status` cho
  file này. Nếu file có thay đổi chưa commit của người dùng thì KHÔNG sửa, ghi lại để báo.

**B4. `tests/test_ws_live_contract.py` (≤ 2 giờ).** Phụ thuộc B3. Test AC3 và AC7 bằng `fastapi.testclient`,
predictor và extractor giả.

**B5. `tests/test_live_harmonized_equivalence.py` (≤ 2 giờ).** Phụ thuộc B2 và B3. Test AC4 và AC5 trên video thật,
MediaPipe thật, checkpoint H-keepz-360 thật.

**B6. `scripts/live_segment_check.py` + JSON (≤ 1.5 giờ).** Phụ thuộc B2. AC6.

**B7. Chốt (≤ 1 giờ).** AC8 (hồi quy), AC9 (quy trình, progress_log, review).

Commit gợi ý: B1, B2, B3+B4, B5, B6, B7. Commit nhỏ, message ghi rõ bước.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; coder KHÔNG được đổi)

Môi trường: `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`. Output thật của mọi lệnh phải có trong báo cáo của coder.
Test cần dữ liệu hay checkpoint thì dùng `skipUnless`. Trên máy này, các test đó PHẢI chạy: 0 skip.

**AC0. Kiểm tra trước (B0).**
- a. Không lệnh nào sau đây in ra gì:
  - `git diff c65032a HEAD -- src/data/harmonized.py`
  - `git diff c65032a HEAD -- src/data/landmark_extractor.py scripts/extract_keypoints_batch.py`

  Nếu lệnh thứ hai có output thì đối chiếu với commit đã clone trong log kernel trích 360 px. Nếu không có diff nào
  giải thích được thì dừng (§7).
- b. `mediapipe.__version__ == "0.10.14"` trong `.venv`. Ghi thêm phiên bản `cv2` và `numpy`.
- c. sha256 của checkpoint ứng viên bằng `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e`.
  `ckpt["preprocessing"]` có:
  - `features == "harmonized_v1"`, `process_height == 360`, `trim is True`, `hand_z is True`, `target_len == 32`;
  - `extractor == "CleanHolisticExtractor"`, `mediapipe_version == "0.10.14"`.

  In toàn bộ dict `preprocessing` vào báo cáo.
- d. `git status`: 3 file bị xóa của người dùng vẫn ở trạng thái " D", chưa staged.

**AC1. `tests/test_sign_segmenter.py`** (fixture landmark sinh trong test theo kiểu `tests/test_harmonized.py::clip`;
không phải dữ liệu). Mỗi ý là một test.
- a. 5 s chỉ có nghỉ (tay ở hông hoặc không thấy tay) → 0 event, state luôn là `idle`.
- b. Nghỉ 1 s, ký 1.5 s, nghỉ 1 s:
  - đúng 1 `Emit`;
  - `[t_đầu, t_cuối]` của đoạn phát CHỨA khoảng `active_span` do `harmonized.active_span` tính trên toàn fixture (đổi
    ra thời gian);
  - event xảy ra ở frame đầu tiên có (t − t_hoạt_động_cuối) ≥ `rest_hold_s`.
- c. Hai ký hiệu cách nhau khoảng nghỉ > `rest_hold_s` → 2 `Emit`, `segment_id` tăng dần.
- d. Tay giơ liên tục 10 s → `Discard(too_long)` tại thời điểm vượt `max_sign_s`, rồi state là `wait_rest`. Không có
  `Emit` nào khi tay còn giơ. Hạ tay ≥ `rest_hold_s` → `idle`.
- e. Hoạt động ngắn hơn `min_sign_s` → `Discard(too_short)`.
- f. Timestamp nhảy > `stream_gap_s` khi đang ghi → `Discard(stream_gap)`.
- g. Đổi (W,H) khi đang ghi → `Discard(frame_size_changed)`.
- h. Timestamp không tăng → `ValueError`, state và bộ đệm không đổi.
- i. Tham số lấy từ cfg của checkpoint: fixture có cổ tay đứng yên ở giữa hai ngưỡng `rest_y` (1.0 và 1.4) → kích
  hoạt với ngưỡng này, không kích hoạt với ngưỡng kia. Thiếu một khóa bắt buộc của nhóm checkpoint → `ValueError`.
- j. Vòng đệm tiền cuộn: đoạn phát bắt đầu ≤ onset − `pre_roll_s` (hoặc ở frame đầu dòng, nếu dòng ngắn hơn).
- k. Rơi frame: bỏ frame theo mẫu cố định (giữ 1 bỏ 1, rồi giữ 1 bỏ 2) → vẫn đúng 1 `Emit` chứa `active_span`.
- l. `reset()` khi đang ghi → `Discard(reset)`; khi `idle` → None.
- m. Chạy 60 s liên tục với tay giơ ở 60 fps → bộ đệm luôn ≤ `max_buffer_frames`.
- n. Ràng buộc §3.4 bị vi phạm (ví dụ `rest_hold_s ≤ max_gap_s`) → `ValueError`.
- o. Module không import `torch`, `cv2`, `mediapipe`. Kiểm bằng `sys.modules` sau khi import trong subprocess sạch.

**AC2. `tests/test_harmonized_live.py`**
- a. `live_pipeline_for`:
  - `None`, `{}`, `PREPROCESSING` của `scripts/train_unified.py` (không có `features`) → `"legacy"`;
  - `preprocessing` đọc từ checkpoint H-keepz-360 → `"harmonized_v1"`;
  - `features="harmonized_v2"`, `mediapipe_version="0.10.9"`, `extractor="X"`, thiếu `rest_y`, `process_height=0` →
    mỗi trường hợp ra `ValueError`.
- b. Resize thật trước MediaPipe: dùng `CleanHolisticExtractor` thật, thay `_get_holistic` bằng graph giả ghi lại shape
  ảnh nhận được.
  - Frame 640×480 → graph nhận (360, 480, 3).
  - Frame 1280×720 → (360, 640, 3).
  - Ảnh graph nhận ở dạng RGB: kiểm bằng frame một màu BGR (255,0,0) → pixel nhận được là (0,0,255).
- c. Dùng spy trên `harmonize`:
  - `cfg` được truyền `==` `preprocessing` của phiên (và là chính object đó hoặc bản sao bằng nó);
  - `aspect == 640/480`;
  - `timestamps_s[0] == 0`, và dãy này tăng ngặt;
  - `rng` là None hoặc không được truyền.
- d. Đoạn chỉ có tay nghỉ hoặc không có tay (jm tay toàn 0) → `sign_discarded(no_hand_frames)`, `predict` KHÔNG được gọi.
- e. `overlay_landmarks`:
  - đúng định dạng legacy: pose 25 cặp [x, y] làm tròn 4 chữ số; tay đủ 21 cặp hoặc `[]`;
  - khi tay thiếu thì `[]`;
  - không có NaN trong JSON.
- f. Các mốc thời gian trong kết quả lấy từ `time.perf_counter`: patch perf_counter trả dãy số biết trước, thì các
  trường `*_ms` phải bằng đúng giá trị suy ra.

**AC3. `tests/test_ws_live_contract.py`** (TestClient; predictor và extractor giả; không cần MediaPipe hay checkpoint thật).
- a. Chạy subprocess với env không có `VSL_MODEL_TYPE` hay `VSL_STGCN_CKPT`, in các hằng của `backend.main`:
  - `MODEL_TYPE == "stgcn"`;
  - `STGCN_CKPT == "checkpoints/stgcn_tier2_indomain.pt"`;
  - `IS_DEFAULT_MODEL is True`.

  Với `VSL_MODEL_TYPE=stgcn_h360`: `STGCN_CKPT` trỏ tới `run_keepz_360/stgcn_unified_best.pt`, `IS_DEFAULT_MODEL is False`.
- b. Fixture checkpoint bị sha lệch cho biến thể có sha:
  - `/api/health` trả 503, `status == "model_unavailable"`;
  - WS nhận `error{model_unavailable}` rồi bị đóng với mã 1011;
  - KHÔNG có `frame_result` nào mang dự đoán.
- c. Message đầu tiên của mỗi phiên là `session_info`, có đủ khóa ở §3.6. Với fixture harmonized, `pipeline` là
  `"harmonized_v1"`; với fixture legacy là `"legacy"`.
- d. Dòng frame giả làm segmenter đi idle → recording → phát:
  - đúng 1 `sign_result`;
  - `top5` có 5 phần tử giảm dần, `confidence` nằm trong [0, 1];
  - `sign_result` đến TRƯỚC `frame_result` có cùng `frame_seq`;
  - mọi `frame_result` của đường harmonized có `prediction is None` và `top5 == []`;
  - `status` và `segment.state` đi đúng thứ tự.
- e. Giới hạn kích thước, cho CẢ HAI đường:
  - message dài `WS_MAX_MESSAGE_BYTES + 1` (text, và binary) → `error{message_too_large}` rồi đóng 1009;
  - message dài đúng `WS_MAX_MESSAGE_BYTES` mà hợp lệ về dạng thì không bị lỗi kích thước.
  - Chứng minh giới hạn đủ rộng: tạo một ảnh 640×480 nhiễu ngẫu nhiên, mã hóa JPEG chất lượng 95, bọc thành dataURL
    trong JSON. Test in kích thước thật; kích thước phải < giới hạn, và frame đó được nhận.
  - Nhiễu sinh bằng `default_rng(0)`, chỉ trong test.
- f. Mỗi loại lỗi sau cho đúng `error.code`, và phiên VẪN xử lý được frame hợp lệ gửi ngay sau đó:
  - JSON hỏng → `bad_message`;
  - thiếu `image` → `bad_message`;
  - base64 hỏng → `decode_failed`;
  - GIF hoặc byte rác → `unsupported_format`;
  - PNG có header khai 4000×10 → `frame_too_large`, và `cv2.imdecode` KHÔNG được gọi (kiểm bằng spy);
  - frame 320×240 ở đường harmonized → `frame_too_small`;
  - `detail` không chứa chuỗi base64 đã gửi.
- g. `config.confidence_threshold` là NaN, `"abc"` hoặc 2.0 → `bad_config`, ngưỡng của smoother không đổi. Giá trị
  0.5 → ngưỡng được cập nhật.
- h. Timestamp:
  - giảm, bằng frame trước, NaN hoặc chuỗi → `bad_timestamp`, frame không vào bộ đệm (`segment.frames` không tăng);
  - phiên có nguồn client mà nhận binary frame → `bad_timestamp`;
  - `metrics.timestamp_source` đúng với nguồn đã chốt.
- i. `{"type":"control","action":"reset"}` khi đang ghi → `sign_discarded{reason:"reset"}`. Action lạ → `bad_message`.

**AC4. Tương đương train–realtime trên video thật** (`tests/test_live_harmonized_equivalence.py::TestTransformEquivalence`).
- Mẫu:
  - chỉ lấy các dòng `source == "qipedc"` trong `data/splits/unified/train.csv` có `data/Dataset/Videos/<file_name>` trên đĩa;
  - sắp theo `video_id`;
  - lấy 8 dòng bằng `np.random.default_rng(0).choice(n, 8, replace=False)`;
  - in danh sách `video_id` ra.
  - Chỉ dùng TRAIN, và không đo độ chính xác.
- Đường train: đúng code đã sinh dữ liệu train.
  - `scripts/extract_keypoints_batch._extract_one((video, tmp/<stem>.npz, {"process_height": 360, "source": "qipedc", "file_name", "label"}))`;
  - sau đó `HarmonizedDataset(<csv tạm có npz_path, width, height, gloss_normalized, video_id>, label_map của checkpoint, cfg=ckpt["preprocessing"], augment=False)[0]`.
- Đường realtime:
  - đọc cùng video bằng `cv2.VideoCapture`;
  - mã hóa mỗi frame BGR bằng `cv2.imencode(".png")` (không mất dữ liệu) và đưa qua `backend.main._decode_frame` cùng
    bước kiểm tra header của AC3;
  - `HarmonizedLiveSession.process(frame, t_s=i/fps)`, trong đó `fps` là `CAP_PROP_FPS`;
  - cuối cùng `finalize_clip()`.
- Kỳ vọng, cho TỪNG clip:
  - (1) `keypoints` và `visibility_mask` thô của hai đường giống hệt: `np.array_equal(..., equal_nan=True)`.
  - (2) Ảnh MediaPipe nhận ở cả hai đường có chiều cao 360. Kiểm bằng wrapper ghi shape, bọc `holistic.process` thật
    và vẫn gọi hàm thật.
  - (3) `joint_mask` và `temporal_mask` giống hệt (`array_equal`).
  - (4) `max|Δsequence| ≤ 1e-5`. Không đòi giống từng bit, vì fps của đường live ước lượng từ timestamp, còn đường train
    dùng `CAP_PROP_FPS`.
  - (5) Qua `VSLPredictor(model_type="stgcn", stgcn_ckpt=<H-keepz-360>, device="cpu")`:
    - top-5 gloss của hai đường cùng thứ tự;
    - `|Δconfidence| ≤ 1e-4` cho cả 5 phần tử.
- Nếu (1) sai (MediaPipe không tất định giữa hai instance trên cùng máy): KHÔNG được nới. Dừng, "CẦN PLANNER" (§7).

**AC5. WS end-to-end trên video thật** (`TestWebSocketEndToEnd`, 2 clip đầu của mẫu AC4).
- Set `VSL_MODEL_TYPE=stgcn_h360`, reload `backend.main`, rồi mở phiên bằng TestClient.
- Gửi theo nhịp khóa bước (chờ `frame_result` rồi mới gửi frame kế tiếp, nên không rơi frame):
  - mỗi frame là text JSON `{"image": dataURL PNG, "timestamp": i*1000/fps}`;
  - sau frame cuối, gửi lại frame cuối thêm `ceil((rest_hold_s + 0.2) * fps)` lần với timestamp tiếp tục tăng. Đây là
    đệm nghỉ trong test, và được ghi rõ là đệm.
- Cùng dãy frame và timestamp đó cho chạy trong process qua một `HarmonizedLiveSession` mới, dùng chung predictor.
- Kỳ vọng:
  - loại và số lượng event của hai bên trùng nhau;
  - mỗi `sign_result` của WS có `top5` trùng bên trong process (cùng thứ tự, `|Δconf| ≤ 1e-4`);
  - các trường đúng §3.6.
- Nếu clip ra `sign_discarded` thay vì `sign_result`, test vẫn PASS khi hai bên trùng nhau. Coder ghi lý do vào báo cáo.

**AC6. Kiểm tra segmenter trên clip thật (báo cáo, không đặt ngưỡng).**
- Lệnh:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py --n-clips 8 --seed 0 --out reports/live_word_<YYYY-MM-DD>/segment_check.json`
- Mẫu: đúng cách chọn của AC4.
- Mỗi clip được stream qua `HarmonizedLiveSession` có segmenter, với phần đệm nghỉ như AC5.
- JSON ghi, cho mỗi clip:
  - `video_id`;
  - danh sách event (loại, lý do);
  - `contains_offline_span` (bool);
  - thời lượng đoạn và thời lượng `active_span` offline;
  - top-1 của đường live so với `finalize_clip()` (trùng hay không), độ giao top-5, `|Δconf|` của top-1.
- Header `generated_by` ghi:
  - lệnh, `git_commit`, `code_dirty` (của `src/`, `scripts/`, `backend/`);
  - phiên bản mediapipe, cv2, numpy;
  - sha256 của checkpoint;
  - `SEGMENTER_DEFAULT`.
- JSON KHÔNG chứa landmark.
- Không có ngưỡng pass. Mọi số trong báo cáo phải lấy từ JSON này.
- Test `TestSegmentCheckJson` kiểm:
  - file tồn tại;
  - có 8 mục;
  - `code_dirty == false`;
  - `git_commit` là tổ tiên của HEAD;
  - mỗi clip có ≥ 1 event (không clip nào bị bỏ qua im lặng).
- Nếu có clip `contains_offline_span == false`: ghi vào báo cáo và progress_log. KHÔNG chỉnh tham số segmenter trong
  việc này. Chỉnh tham số là một việc riêng, và chỉ dựa trên clip TRAIN.

**AC7. Legacy không đổi hành vi dự đoán; số liệu thật.**
- a. `git diff 9f4eb68 HEAD` phải rỗng cho:
  - `src/inference/realtime_pipeline.py`, `src/inference/realtime_extractor.py`, `src/inference/predictor.py`,
    `src/inference/smoother.py`;
  - `src/data/harmonized.py`, `src/data/landmark_extractor.py`;
  - `scripts/train_unified.py`, `scripts/extract_keypoints_batch.py`;
  - `tests/test_harmonized.py`, `tests/test_realtime.py`.
- b. `frame_result` của legacy chứa mọi khóa cũ: `type`, `gloss`, `prediction`, `confidence`, `top5`, `latency_ms`,
  `fps`, `status`, `sentence`, `is_confirmed`, `translated_text`, `oov_warning`, `is_signing`, `hand_detected`,
  `buffer_fill`, `buffer_capacity`, `landmarks`, `metrics`, và trong `metrics` có `client_timestamp`,
  `server_preprocess_ms`, `server_infer_ms`, `server_total_ms`, `server_fps`, `buffer_frames`.
- c. Pipeline giả trả `prediction.latency_ms = 7.0` và `is_new_prediction = True` →
  `metrics.server_infer_ms == 7.0`. Khi `is_new_prediction = False` → `0.0`.
- d. Trong `backend/main.py`, grep `latency_ms \* 0\.[0-9]` không ra kết quả.
- e. Grep các file mới (`src/inference/sign_segmenter.py`, `src/inference/harmonized_live.py`,
  `scripts/live_segment_check.py`) không thấy `random` và không thấy số liệu độ chính xác gõ tay.

**AC8. Hồi quy.**
- Lệnh:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence -v`
- Kỳ vọng:
  - 0 failure, 0 error;
  - báo số test trước → sau và số skip thật, kèm lý do từng skip;
  - AC4, AC5, AC6 không được skip trên máy này.
- Nếu kế hoạch 03 đã đổi danh sách test của nó thì dùng danh sách AC8 cuối cùng của 03, cộng 5 module ở cuối lệnh trên.

**AC9. Quy trình.**
- Có output `impact` cho mọi symbol có sẵn bị sửa.
- Mỗi commit có `detect-changes --scope all`, và risk được ghi vào commit message.
- Không commit `.pt`, `.npz`, video, frame, landmark. Thư mục `reports/live_word_*/` chỉ chứa JSON.
- 3 file bị xóa của người dùng vẫn ở trạng thái " D".
- THÊM một dòng vào `docs/progress_log.md`: ngày | việc | kế hoạch | commit | kết luận review | việc tiếp theo, kèm
  dòng mô tả test (trước → sau) và kết quả AC6 (lấy từ JSON).
- Review `docs/reviews/04-review.md` kết luận APPROVE.

---

## 6. Rủi ro dữ liệu / ML

- **Lệch nền tảng.** AC4 chứng minh CODE hai đường giống nhau trên CÙNG máy (Windows, cv2 và numpy trong `.venv`).
  Nó KHÔNG chứng minh landmark trích trên Kaggle giống landmark trích cục bộ, vì Kaggle chạy Linux với
  `opencv-python-headless 4.10.0.84`, `numpy<2`, và bộ giải mã video có thể khác.
  - Việc tiếp theo nên có (không thuộc DoD của việc này): tải vài npz 360 px từ output kernel trích xuất (chỉ đọc) rồi so
    với bản trích cục bộ của cùng video. Báo cả chênh lệch lẫn tác động lên top-5. Không đặt ngưỡng trước khi có số.
- **Rơi frame và `hand_activity`.** Luật hoạt động lúc train tính tốc độ = `diff * fps`, vì frame lúc train cách đều.
  - Ở live, frame không cách đều do kiểu chỉ-frame-mới-nhất. Việc này dùng `fps` trung bình của đoạn, nên tốc độ ở từng
    frame có thể lệch.
  - `sign_result.segment` ghi `effective_fps` và `dropped_frames` để đo sau.
  - Không sửa `harmonize` để xử lý chuyện này, vì sửa sẽ đổi dữ liệu train.
- **Scale theo vai.** `_normalise` dùng median độ rộng vai trên đoạn được đưa vào. Đoạn live (tiền cuộn + ký + nghỉ)
  khác cả clip lúc train, nên tensor chỉ gần giống. Vì vậy AC4 so trên toàn clip (`finalize_clip`), còn phần cắt đoạn
  được báo riêng ở AC6.
- **Trạng thái tracker.** Lúc train, mỗi clip có một Holistic mới. Ở live, một Holistic dùng cho cả phiên, qua nhiều ký
  hiệu. Không reset tracker giữa các ký hiệu (reset tốn thời gian khởi tạo). Đây là giới hạn cần ghi lại.
- **Khác miền dữ liệu, không phải lệch pipeline.** Webcam 640×480 JPEG 0.75 khác mp4 QIPEDC 1280×720 (ánh sáng, khoảng
  cách, nén). AC4 dùng PNG để cô lập code. Tác động của JPEG và webcam chỉ đo được bằng bộ webcam Bước 5, là dữ liệu
  người dùng quay.
- **Tham số segmenter chưa đo.** Các giá trị ở §3.4 là giá trị thiết kế. Không được chỉnh theo TEST, và không được
  báo như số liệu.
- **Đường legacy có lệch sẵn (không sửa ở đây).**
  - `RealtimeLandmarkExtractor` dùng ngưỡng visibility pose 0.2, còn `CleanHolisticExtractor` dùng 0.1.
  - Legacy dùng cửa sổ trượt thay cho gom trọn ký hiệu.
  - Ghi cả hai vào tài liệu cho GATE. Sửa đường legacy là đổi hành vi của model mặc định, nên thuộc GATE.
- **Rò rỉ.** Không có: không train, không đo độ chính xác. AC4 và AC6 chỉ dùng clip TRAIN để so hai đường, không dùng
  TEST.
- **Cỡ mẫu.** 8 clip đủ để kiểm tính tương đương của code. Chúng không nói gì về độ chính xác live.
- **Nguồn gốc và giấy phép.** Video QIPEDC là dữ liệu cục bộ của người dùng, chỉ đọc. JSON chỉ ghi `video_id` và số,
  không ghi landmark hay frame.
- **Checkpoint ứng viên nằm ngoài git.** Biến thể `stgcn_h360` kiểm sha256 lúc nạp. Nếu file bị thay thì backend từ
  chối nạp, không chạy nhầm model khác.

---

## 7. Điểm dừng

- **Đổi model mặc định: KHÔNG.**
  - `DEFAULT_MODEL_TYPE` vẫn là `"stgcn"` → `checkpoints/stgcn_tier2_indomain.pt`, đường legacy (AC3-a).
  - Đổi mặc định sang H-keepz-360 là GATE riêng: DỪNG, kèm bảng so sánh model cũ và H-keepz-360 trên cùng tập test sạch.
- **Cần dữ liệu từ người dùng: KHÔNG.** Chỉ dùng video QIPEDC đã có trên đĩa. Bộ webcam là Bước 5.
- **Đụng thay đổi chưa commit của người dùng: KHÔNG.** `data/Dataset/` chỉ đọc. Nếu `start_fullstack.ps1` có thay đổi
  chưa commit thì không sửa file đó (B3).
- **Hành động không hoàn tác: KHÔNG.** Không xóa file, không lệnh Kaggle, không train.
- **Điểm dừng CÓ ĐIỀU KIỆN:**
  1. AC0-a có diff không giải thích được: code train hoặc trích xuất đã đổi so với lúc train H-keepz-360. Đây là vấn đề
     nguồn gốc dữ liệu → "CẦN NGƯỜI DÙNG".
  2. AC0-c: sha256 hoặc `preprocessing` của checkpoint không khớp → "CẦN NGƯỜI DÙNG". Không lấy checkpoint khác thay vào.
  3. AC4-(1) sai vì MediaPipe không tất định → "CẦN PLANNER". Không nới tiêu chí.

## 8. Ngoài phạm vi
- Mọi thay đổi frontend (Việc 5/6):
  - hiển thị trạng thái ghi, `sign_result`, lý do bỏ đoạn;
  - proxy `/ws`;
  - xin độ phân giải có chiều cao ≥ 360;
  - nút reset.
- Đo độ trễ DoD 8 (Việc 7), dùng các trường ở §3.6.
- Chỉnh tham số segmenter.
- Sửa các lệch có sẵn của đường legacy.
- GATE đổi model mặc định.
- Fine-tune model từ điển (mục (ii) cuối backlog).
