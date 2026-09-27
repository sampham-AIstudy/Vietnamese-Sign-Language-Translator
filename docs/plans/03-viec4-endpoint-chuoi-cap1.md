# Kế hoạch 03: Việc 4, endpoint chuỗi landmark cho Cấp 1 "Đánh vần" (chỉ backend/)

> **Điểm dừng: KHÔNG có điểm dừng lúc bắt đầu.** Có một **điểm dừng CÓ ĐIỀU KIỆN ở Bước 0**. Nếu checkpoint Cấp 1
> đang được nạp (`checkpoints/alphabet_best.pt`) KHÔNG trùng sha256 với checkpoint nào đã biết là train trên dữ liệu
> thật, hoặc không có `trained_on.source == "hauuto"`, thì ghi "CẦN NGƯỜI DÙNG" vào progress_log và dừng Bước 5.
> Lý do: nguồn gốc model mặc định không rõ, và muốn thay nó thì phải đổi model mặc định, việc này cần người dùng duyệt.
> Các bước khác không phụ thuộc Bước 0 thì vẫn làm tiếp.
> Việc này KHÔNG đổi model mặc định: không sửa/thay/chép checkpoint, không đổi giá trị mặc định `VSL_ALPHABET_CKPT`.
> Việc này KHÔNG đụng frontend/ (thuộc Việc 5). KHÔNG `git add -A` / `git add .`: thư mục làm việc có các file bị xóa
> chưa commit của người dùng (progress_log, mục "Ghi chú của người dùng" 3).

Nhánh `feat/vslt-complete`, lập kế hoạch tại HEAD `09d4057`, ngày 2026-09-27.

---

## 1. Mục tiêu và DoD

**Mục tiêu.** Backend đã có endpoint chuỗi landmark (commit `6dd0202`, làm trước quy trình 3 agent và chưa qua
vslt-reviewer). Việc này làm bốn thứ:
1. Kiểm chứng phần đã có.
2. Bổ sung phần còn thiếu để đạt DoD 2 phía backend: giới hạn kích thước request, ghép chữ thành từ có dấu thanh,
   nguồn gốc model trong status.
3. Viết test tương đương train và realtime cho **đúng checkpoint đang được nạp**.
4. Cho vslt-reviewer duyệt.

**DoD phục vụ.**
- DoD 2 (phía backend): endpoint nhận CHUỖI landmark → chữ cái + confidence; ghép chữ thành từ; endpoint ảnh cũ trả 409.
- DoD 6: không có kết quả giả. Không có model thì trả 503. Không ghép khi token không hợp lệ. Nguồn gốc model phải
  hiển thị.
- DoD 7: unit + contract + test tương đương train và realtime.
- Mục 11 (bảo mật) của reviewer: kiểm tra shape, kích thước và loại input; giới hạn kích thước body.

---

## 2. Hiện trạng: đối chiếu DoD 2 phía backend với code (HEAD `09d4057`)

| Yêu cầu | Đã có? | Bằng chứng | Còn thiếu |
|---|---|---|---|
| Endpoint nhận chuỗi landmark | CÓ | `backend/main.py:483-512` `predict_fingerspelling_sequence`; request model `:398-410`; kiểm tra input `:413-456` | Không giới hạn kích thước body trước khi parse JSON (xem dưới) |
| Trả chữ cái + confidence + top-k | CÓ | `:498-512` (`prediction`, `confidence`, `candidates`, `frames`, `detected_frames`, `model_type`, `checkpoint`) | Không phân biệt chữ cái với dấu thanh trong response |
| Ảnh cũ → 409 | CÓ | `:515-527`; test `tests/test_fingerspelling_api.py:87-91` | Route vẫn khai `file: Optional[UploadFile] = File(None)` (`:516`), nên FastAPI parse TOÀN BỘ multipart (lưu tạm ra đĩa) rồi mới trả 409. Không giới hạn kích thước |
| Kiểm tra input → 422 | CÓ phần lớn | `:416-451`; test `:110-127` (10 ca) | Không có giới hạn byte của body. `List[...]` không có `max_length`, nên pydantic parse cả danh sách tùy ý dài rồi mới kiểm `T ≤ 300` (`:417`). `frame_width/height` không có cận trên. Không có test NaN/Infinity, không có test body không phải JSON |
| 503 khi không có model / checkpoint thiếu `preprocessing` | CÓ | `:364-395`, `:489-490`; test `:150-159` | Nạp lười không có khóa (`:368-395`), nên hai request đầu đồng thời có thể cùng `torch.load` |
| Tiền xử lý dùng chung train và realtime | CÓ | Backend gọi `src/data/alphabet_preprocessing.py:270-304` `alphabet_clip_features` theo dict `preprocessing` trong checkpoint. Script train model triển khai `scripts/train_alphabet_nested.py:51-73` cũng gọi đúng hàm đó | — |
| Test tương đương train và realtime | CÓ, nhưng SAI checkpoint | Fixture: `tests/test_fingerspelling_api.py:172-187` (so với `canonicalize_hand_sequence`+`sequence_features_from_clip`, preprocessing rút gọn `:59`). Dữ liệu thật: `:190-219` dùng `REAL_CKPT = reports/alphabet_real_run_2026-09-25/.../alphabet_real_best.pt` (`:34`) và đường offline `train_alphabet_real.load` | KHÔNG có test nào chạy **checkpoint đang triển khai** (`checkpoints/alphabet_best.pt`, theo handoff 2026-09-25 là "bigru 120 frame" từ nested run) qua đường offline của `train_alphabet_nested.load`. Chỉ so `prediction`, không so confidence (`:216`) |
| Ghép chữ thành từ | KHÔNG (backend) | Frontend `frontend/src/components/Fingerspelling.jsx:207` nối chuỗi tên lớp thô (`prev + prediction`). Nhãn dấu là `"dấu sắc"` … (`scripts/build_alphabet_tasks.py:27`), nên sẽ ra chữ "adấu sắc" thay vì "á" | Cần hàm ghép tiếng Việt (áp dấu thanh vào đúng nguyên âm) có test và endpoint không trạng thái (§3.3) |
| Nguồn gốc model hiển thị | KHÔNG | Status `:459-480` không trả `trained_on`. Checkpoint nested có `trained_on`, `selected`, `epochs` (`scripts/train_alphabet_nested.py:206-213`) | Trả `trained_on` và ghi chú giấy phép dữ liệu (`docs/data_registry.md:41-48`: hauuto, licence unknown, internal only) |
| Model Cấp 1 nào đang nạp, dữ liệu có hợp lệ không | CHƯA KIỂM CHỨNG | `ALPHABET_CKPT` mặc định `checkpoints/alphabet_best.pt` (`:357`), bị gitignore (`.gitignore:62`). Handoff `2026-09-25-gate0-level1-nested.md:43` ghi "deployed … bigru 120 frame" nhưng không có sha256. Tên file này trùng với tên mà pipeline tổng hợp cũ định sinh ra (`reports/audit_round2/AUDIT_ROUND2.md:119`; memory: `data/vsl_alphabet_pilot` là TỔNG HỢP, run Kaggle đã dừng trước khi upload) | Bước 0: sha256 + đọc khóa checkpoint + so với các checkpoint đã biết |

**Dữ liệu và model đã biết (không phải số liệu mới, chỉ để định hướng):**
- `reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt`: train trên hauuto (4 người thật, MediaPipe
  thật, GATE 0 PASS ở `reports/alphabet_real_run_2026-09-25/GATE0_integrity.md`), log `primary/nested.log:6`
  chọn `('bigru', 120, 'frame')`, train trên `cuda`. Giấy phép hauuto: **unknown**, chỉ dùng nội bộ.
- `reports/alphabet_nested_2026-09-25/variants/alphabet_nested_final.pt`: ứng viên thứ hai.
- `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`: model cũ hơn, đã commit công khai
  (`docs/data_registry.md:44`). Giữ hay gỡ là quyết định của người dùng; việc này không động vào.
- Dữ liệu thật cho test có trên máy: `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` (gitignored).

**Ghi chú về ranh giới:** CORS `allow_origins=["*"]` + `allow_credentials=True` (`backend/main.py:151-157`) là lỗi
có từ trước (mục 11 của reviewer). Việc 4 không sửa nó, vì đổi CORS trước khi nối proxy `/ws` ở Việc 5 có thể làm hỏng
frontend. Chuyển sang Việc 5 (§8).

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu (Cấp 1)
```
[Việc 5, frontend] webcam (KHÔNG lật gương) → MediaPipe Hands → cắt 1 ký hiệu (tay xuất hiện → dừng/biến mất, hoặc nút)
   → POST /api/fingerspelling/sequence {landmarks[T], handedness[T], timestamps_ms[T]?, frame_width, frame_height}
[backend] giới hạn body (413) → pydantic (422) → parse_fingerspelling_sequence (422)
   → alphabet_clip_features(..., preprocessing = checkpoint["preprocessing"])   ← CÙNG hàm với train_alphabet_nested.load
   → model → top-k {class, confidence} + prediction_kind
[Việc 5] người dùng chấp nhận/sửa token → danh sách token (chữ, dấu, " ")
   → POST /api/fingerspelling/compose {tokens} → {text, syllables, warnings}   ← hàm thuần, không trạng thái
```
Ranh giới với Việc 5. **Backend (Việc 4)** không giữ trạng thái. Nó phân loại MỘT ký hiệu mỗi request và ghép một danh
sách token thành chữ. **Frontend (Việc 5)** lo mọi thứ còn lại: MediaPipe phía client, cắt ký hiệu trong luồng, giữ danh
sách token, nút cách/xóa lùi/xóa hết, hiển thị cảnh báo, đọc to. Frontend phải gọi `/compose` và không tự ghép chuỗi.

### 3.2 Hợp đồng `POST /api/fingerspelling/sequence` (giữ nguyên các trường cũ, chỉ THÊM)
Input (JSON), giữ tương thích với `FingerspellingSequenceRequest` hiện có:
- `landmarks`: list độ dài 1..`ALPHABET_MAX_FRAMES` (=300, giữ nguyên). Mỗi phần tử là `null`, `[]`, hoặc đúng
  21 × [x, y, z] số hữu hạn. Dùng pydantic `Field(max_length=ALPHABET_MAX_FRAMES)` cho danh sách ngoài. Danh sách trong
  có `max_length` 21 và 3, để parse không phình ra.
- `handedness`: `null` hoặc list cùng độ dài T, giá trị trong {"Left","Right",""}. Bắt buộc có khi
  `mirror_left_hand` (như cũ).
- `timestamps_ms`: `null` hoặc T số hữu hạn không giảm. Bắt buộc có khi `resample == "time"` (như cũ).
- `frame_width`, `frame_height`: int trong 1..`ALPHABET_MAX_FRAME_SIDE` (hằng mới, = 8192).
- `source_mirrored`: bool (như cũ). `top_k`: 1..10 (như cũ).

Output 200: các trường cũ, cộng thêm:
- `prediction_kind`: `"letter"` | `"tone"` (của `prediction`).
- Mỗi phần tử `candidates` có thêm `kind`.
Không làm tròn thêm và không đổi `confidence` (vẫn `round(v, 4)`).

Mã lỗi:
- 413: body lớn hơn `ALPHABET_MAX_BODY_BYTES` (hằng mới, = 1_048_576), áp cho cả request có `Content-Length` lẫn
  request chunked. Body là JSON `{"detail": ...}`. Kiểm tra TRƯỚC khi parse JSON. Chỉ áp cho hai path
  `/api/fingerspelling/sequence` và `/api/fingerspelling/compose`. Không áp cho các path khác của app, và KHÔNG áp cho
  `/api/fingerspelling` (path này phải luôn trả 409).
  Cách làm (middleware ASGI giới hạn theo path, hoặc đọc body có chặn trong route) do coder chọn. Nếu đổi route sang
  `async`, suy luận vẫn phải chạy ngoài event loop (threadpool).
- 422: sai kiểu, sai shape, NaN/Infinity, body không phải JSON, vượt độ dài danh sách, `frame_*` ngoài khoảng, thiếu
  `handedness`/`timestamps_ms` khi model cần, ít hơn `min_detected_frames` khung có tay.
- 503: không có checkpoint hợp lệ (như cũ).
- Không bao giờ trả 500 cho input xấu.

Lý do chọn 1 MiB: payload hợp lệ lớn nhất gồm 300 khung × 63 số, mỗi số là float ở dạng repr dài nhất, cộng handedness
và timestamps. Test AC1-e dựng đúng payload này và chứng minh nó NHỎ HƠN giới hạn và trả 200. Không ước lượng tay.

### 3.3 Hợp đồng `POST /api/fingerspelling/compose` (mới) + module thuần
Module mới `src/inference/fingerspelling_compose.py` (không import torch/fastapi, dùng được ở mọi nơi):
- Hằng `LETTERS` (29) và `TONE_MARKS` (5 nhãn `"dấu sắc"`, `"dấu huyền"`, `"dấu hỏi"`, `"dấu ngã"`, `"dấu nặng"` →
  dấu kết hợp U+0301, U+0300, U+0309, U+0303, U+0323), `SPACE = " "`.
- `token_kind(token) -> "letter" | "tone" | "space"`: ném `ValueError` nếu token lạ.
- `compose(tokens) -> {"text": str (NFC), "syllables": [str], "warnings": [{"code", "token_index", "message"}]}`.

Quy tắc ghép (có tài liệu trong docstring và test ở AC3):
1. Âm tiết là chuỗi token nằm giữa hai `" "`. Chữ cái nối theo thứ tự. Dấu thanh áp cho CẢ âm tiết, bất kể nó đứng ở
   đâu trong âm tiết (thường ký sau chữ cuối, giống Telex).
2. Nếu âm tiết có từ 2 dấu thanh trở lên thì dùng dấu CUỐI và thêm cảnh báo `multiple_tones`.
3. Nếu âm tiết không có nguyên âm thì không áp dấu, giữ nguyên các chữ, và thêm cảnh báo `tone_without_vowel`.
   Không tự sửa hay đoán chữ.
4. Chọn nguyên âm mang dấu. Nguyên âm gồm a ă â e ê i o ô ơ u ư y. Bỏ "u" trong "qu" đầu âm tiết. Bỏ "i" trong "gi"
   đầu âm tiết khi sau nó còn nguyên âm khác.
   Với cụm nguyên âm còn lại:
   (a) Cụm có nguyên âm mang mũ/móc (ă â ê ô ơ ư): đặt dấu vào nguyên âm mang mũ/móc CUỐI cùng. Ví dụ "ươ" đặt ở ơ.
   (b) Nếu không, và âm tiết có phụ âm cuối: đặt vào nguyên âm cuối của cụm.
   (c) Nếu không, cụm 3 nguyên âm: đặt vào nguyên âm giữa.
   (d) Nếu không, cụm 2 nguyên âm: đặt vào nguyên âm ĐẦU. Đây là **kiểu cũ**: hòa, thủy.
   (e) Cụm 1 nguyên âm: đặt vào nguyên âm đó.
   Kiểu đặt dấu cũ/mới là lựa chọn trình bày, không phải điểm dừng. Ghi `"tone_style": "traditional"` trong response
   để frontend/tài liệu nói rõ.
5. Kết quả chuẩn hóa NFC, chữ thường. Không viết hoa và không tự thêm khoảng trắng.

Endpoint:
- Input: `{"tokens": [str]}`, độ dài 0..`COMPOSE_MAX_TOKENS` (=200).
- Output 200: `compose(...)` + `"tone_style"`.
- Lỗi: 422 khi token lạ (thông báo nêu vị trí), khi vượt độ dài, hoặc khi sai kiểu. 413 khi body vượt giới hạn (§3.2).
- Endpoint KHÔNG cần model, nên vẫn chạy được khi checkpoint không có. Không gọi model, không sửa token.

Tính nhất quán nhãn: tập `LETTERS ∪ TONE_MARKS` phải BẰNG `scripts/build_alphabet_tasks.ALPHABET_CLASSES`. Nếu checkpoint
triển khai có mặt, tập này cũng phải bằng `classes` của nó (AC3-d). `prediction_kind`/`kind` ở §3.2 lấy từ `token_kind`.

### 3.4 Status có nguồn gốc model (`GET /api/fingerspelling/status`, chỉ THÊM trường)
- `trained_on`: lấy nguyên từ checkpoint (`None` nếu checkpoint không có khóa này).
- `data_provenance`: tra theo `trained_on.source` trong một hằng ở backend. Hằng này chỉ chứa sự thật đã ghi ở
  `docs/data_registry.md` §1b: hauuto → `{"licence": "unknown", "usage": "internal only", "registry": "docs/data_registry.md#1b"}`.
  Nguồn không có trong hằng, hoặc thiếu `trained_on` → `{"status": "unknown"}`.
- `evaluation_report`: đường dẫn `reports/alphabet_nested_2026-09-25/REPORT.md` (chỉ đường dẫn, KHÔNG chép số liệu
  vào API).
- KHÔNG từ chối nạp checkpoint thiếu `trained_on`. Từ chối như vậy là đổi hành vi của model mặc định, và nó sẽ làm hỏng
  các fixture test có sẵn. Test ở Bước 5 mới là chỗ kiểm chứng nguồn gốc.

### 3.5 Nạp model an toàn khi chạy đồng thời
`get_or_load_alphabet_model` dùng `threading.Lock` theo mẫu double-checked, để `torch.load` chạy đúng một lần. Hành vi
trả `(None, None)` khi lỗi giữ nguyên. Không cache lỗi vĩnh viễn: giữ như hiện tại, lần sau thử lại.

---

## 4. Chia việc (thứ tự và phụ thuộc)

Trước khi sửa bất kỳ hàm nào, chạy GitNexus `impact` (upstream) cho: `predict_fingerspelling_sequence`,
`parse_fingerspelling_sequence`, `FingerspellingSequenceRequest`, `get_or_load_alphabet_model`,
`get_fingerspelling_status`, `predict_fingerspelling`. Ghi risk vào commit message. Nếu risk là HIGH/CRITICAL thì cảnh
báo. Nếu là UNKNOWN thì xác nhận thêm bằng text search.

**Bước 0: Nguồn gốc checkpoint đang nạp (≤ 1 giờ, không phụ thuộc bước nào).**
- Viết script mới `scripts/alphabet_ckpt_provenance.py`. Script ghi `reports/alphabet_deploy_2026-09-27/provenance.json`
  gồm các mục sau:
  - `generated_by`: lệnh, HEAD commit, thời điểm.
  - sha256 và kích thước của `checkpoints/alphabet_best.pt` và của 3 checkpoint đã biết ở §2.
  - Các khóa của mỗi checkpoint.
  - `model_type`, `selected`, `epochs`, `preprocessing`, `trained_on`, `classes` (danh sách).
  - `match`: tên checkpoint đã biết trùng sha256, hoặc `null`.
  - `verdict` ∈ {`"real_data_known_checkpoint"`, `"UNKNOWN_PROVENANCE"`}.
  - Mục thông tin `external_reproduction`: chạy checkpoint đang nạp trên CPU với 46 clip QIPEDC qua đường offline, so
    với `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv` (run="external"), rồi ghi `k/n`. Nếu thiếu
    dữ liệu/CSV thì ghi `null` + lý do. Mục này CHỈ là thông tin, vì run gốc train trên cuda.
  - JSON KHÔNG chứa landmark hay mã clip riêng lẻ.
- Nếu `verdict == "UNKNOWN_PROVENANCE"` hoặc `trained_on.source != "hauuto"`: ghi "CẦN NGƯỜI DÙNG" vào progress_log,
  bỏ qua Bước 5, và làm tiếp các bước còn lại. KHÔNG thay checkpoint.

**Bước 1: Giới hạn input + 409 không đọc body (≤ 2 giờ).**
- Thêm hằng `ALPHABET_MAX_BODY_BYTES`, `ALPHABET_MAX_FRAME_SIDE`. Thêm giới hạn 413 theo path (§3.2).
- Thêm `max_length` cho các list trong pydantic và cận cho `frame_width/height`.
- Route `/api/fingerspelling` bỏ tham số `file`, nên không còn đọc body. Nội dung 409 giữ nguyên.
- Test: AC1, AC2 (file test MỚI `tests/test_fingerspelling_limits.py`).

**Bước 2: Module ghép chữ (≤ 2 giờ, không phụ thuộc bước nào).**
- `src/inference/fingerspelling_compose.py` + `tests/test_fingerspelling_compose.py` (AC3-a..c, e).

**Bước 3: Endpoint `/compose`, `prediction_kind`, status có nguồn gốc (≤ 1.5 giờ, phụ thuộc Bước 1 và 2).**
- Test: AC3-d, AC4, AC7 (thêm vào `tests/test_fingerspelling_compose.py` / `tests/test_fingerspelling_limits.py`).

**Bước 4: Khóa khi nạp model (≤ 0.5 giờ, phụ thuộc Bước 3 vì cùng vùng code).** Test AC6.

**Bước 5: Test tương đương cho checkpoint đang triển khai (≤ 1.5 giờ, phụ thuộc Bước 0 = verdict hợp lệ).**
- File MỚI `tests/test_fingerspelling_deployed.py` (AC5).

**Bước 6: Kiểm tra cuối, commit, review (≤ 1 giờ).**
- Cập nhật docstring đầu `backend/main.py:1-9` (thêm `/compose`).
- Chạy toàn bộ bộ test (AC8). Chạy `node .gitnexus/run.cjs detect-changes --scope all --repo .` trước MỖI commit.
- Mỗi commit chỉ `git add` từng đường dẫn cụ thể.
- Ghi 1 dòng vào progress_log. Chạy vslt-reviewer với kế hoạch này và danh sách commit.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng, coder KHÔNG được đổi)

Môi trường chạy: `.venv/Scripts/python`, đặt `PYTHONIOENCODING=utf-8`. Ghi output thật của mọi lệnh vào báo cáo của
coder.

**AC0: Nguồn gốc (Bước 0).**
- Lệnh: `.venv/Scripts/python scripts/alphabet_ckpt_provenance.py --out reports/alphabet_deploy_2026-09-27/provenance.json`.
- File phải có đủ các trường ở Bước 0.
- `verdict` do script tính từ sha256 và `trained_on`. Không gõ tay.
- Chạy lại lần hai thì JSON giống hệt, ngoại trừ `generated_by`.
- Nếu `verdict != "real_data_known_checkpoint"` thì phải có dòng progress_log với "CẦN NGƯỜI DÙNG", và AC5 được ghi
  "BLOCKED (điểm dừng)". AC5 không được tính là PASS.

**AC1: Giới hạn input** (`tests/test_fingerspelling_limits.py`). Mỗi ý là ít nhất một test:
- a. Body lớn hơn `ALPHABET_MAX_BODY_BYTES` gửi tới `/api/fingerspelling/sequence` có `Content-Length` → 413.
- b. Như (a) nhưng gửi chunked (TestClient `content=` là generator, không có `Content-Length`) → 413.
- c. (a) và (b) cho `/api/fingerspelling/compose` → 413.
- d. Các path khác không bị giới hạn này: gửi body lớn hơn giới hạn tới một path KHÔNG tồn tại
  (`POST /api/__limit_probe__`) → 404, không phải 413. Không dùng route thật nào có nạp model.
- e. Payload HỢP LỆ lớn nhất có thể: T=300, mọi khung đủ 21×3, có đủ handedness và timestamps. Mỗi tọa độ là một float
  Python mà `repr` có đúng 17 chữ số có nghĩa và có số mũ, ví dụ `0.5 + k·1.2345678901234567e-07`. Như vậy độ dài
  chuỗi JSON đạt mức tối đa của float, và bàn tay vẫn có kích thước lòng bàn tay khác 0. Test kiểm
  `len(json.dumps(body).encode()) < ALPHABET_MAX_BODY_BYTES` VÀ POST trả 200.
- f. Body chứa `NaN` và body chứa `Infinity` trong landmarks → 422. Test gửi chuỗi JSON thô, không để client lọc.
- g. Body không phải JSON (`content=b"abc"`, `text/plain`) → 422.
- h. `frame_width = ALPHABET_MAX_FRAME_SIDE + 1` → 422. `frame_height = ALPHABET_MAX_FRAME_SIDE` → 200.
- i. Một khung có 22 điểm, và một điểm có 4 tọa độ → 422.
- j. Không ca nào trong AC1 trả 500.

**AC2: 409** (`tests/test_fingerspelling_limits.py`).
- `inspect.signature(api.predict_fingerspelling).parameters` rỗng.
- Upload multipart 5 MB tới `/api/fingerspelling` → 409 với `detail.use == "/api/fingerspelling/sequence"`.
- POST rỗng → 409. Test cũ `test_image_endpoint_returns_409` vẫn pass và không bị sửa.

**AC3: Ghép chữ** (`tests/test_fingerspelling_compose.py`).
- a. Bảng ca bắt buộc cho `compose`. Token viết bằng tên lớp, `␣` là `" "`. Kết quả so theo NFC:
  `v i ê t dấu nặng ␣ n a m` → `việt nam`;
  `n g ư ơ i dấu huyền` → `người`;
  `h o a dấu huyền` → `hòa`;
  `t h u y dấu hỏi` → `thủy`;
  `t o a n dấu sắc` → `toán`;
  `h o a n g dấu huyền` → `hoàng`;
  `t u â n dấu sắc` → `tuấn`;
  `q u a dấu hỏi` → `quả`;
  `q u y dấu sắc` → `quý`;
  `q u ô c dấu sắc` → `quốc`;
  `g i a dấu huyền` → `già`;
  `g i dấu huyền` → `gì`;
  `g i ê n g dấu sắc` → `giếng`;
  `n g o a i dấu huyền` → `ngoài`;
  `k h u y u dấu hỏi` → `khuỷu`;
  `c ư a dấu hỏi` → `cửa`;
  `c ư u dấu huyền` → `cừu`;
  `m u ô n dấu sắc` → `muốn`;
  `k h u y ê n dấu sắc` → `khuyến`;
  `x o ă n dấu sắc` → `xoắn`;
  `t h u ơ dấu hỏi` → `thuở`;
  `c u a dấu hỏi` → `của`;
  `y dấu sắc` → `ý`;
  `đ a dấu ngã` → `đã`;
  `t o dấu sắc a n` (dấu đứng giữa) → `toán`;
  `m e` (không dấu) → `me`.
- b. Cảnh báo:
  - `b dấu sắc` → text `b`, cảnh báo `tone_without_vowel` với đúng `token_index`.
  - `a dấu sắc dấu huyền` → `à` + cảnh báo `multiple_tones`.
  - `[]` → `""`, không cảnh báo.
  - `["a", " ", " ", "b"]`: `text` giữ đúng hai khoảng trắng. Không chuẩn hóa khoảng trắng.
- c. `compose(["x1"])` ném `ValueError`. Output luôn là NFC (`unicodedata.is_normalized("NFC", text)`).
- d. `set(LETTERS) | set(TONE_MARKS) == set(ALPHABET_CLASSES)` (import từ `scripts/build_alphabet_tasks`). Nếu
  `checkpoints/alphabet_best.pt` có mặt thì tập này cũng bằng `classes` của nó (dùng skipUnless riêng cho phần checkpoint).
- e. Endpoint: token lạ → 422, thông báo có vị trí; 201 token → 422; 200 token → 200; khi KHÔNG có checkpoint
  (`api.ALPHABET_CKPT` trỏ tới file không tồn tại) `/compose` vẫn trả 200; response có `"tone_style": "traditional"`.

**AC4: Response và status.**
- `/sequence` với fixture checkpoint trả `prediction_kind`. Mỗi candidate có `kind`, và `kind == token_kind(class)`.
  Fixture phải dùng `classes = ALPHABET_CLASSES` để `kind` có nghĩa.
- Fixture checkpoint KHÔNG có `trained_on` → status có `trained_on is None` và `data_provenance == {"status": "unknown"}`.
- Fixture CÓ `trained_on.source == "hauuto"` → `data_provenance.licence == "unknown"`.
- Status có `evaluation_report` là đường dẫn tồn tại trong repo.
- Mọi test cũ của `test_status_describes_sequence_contract` vẫn pass.

**AC5: Tương đương train và realtime cho checkpoint ĐANG TRIỂN KHAI** (`tests/test_fingerspelling_deployed.py`).
- `skipUnless` checkpoint + `manifest.csv` có mặt. Trên máy này **phải chạy, 0 skip**. Lý do skip phải nêu rõ tên file
  thiếu.
- a. Đọc checkpoint `checkpoints/alphabet_best.pt`. Có sha256 bằng `provenance.json` → `checkpoints.deployed.sha256`.
  Nếu lệch thì FAIL, vì checkpoint đã bị đổi sau Bước 0.
- b. `train_alphabet_nested.preprocessing_for(ckpt["selected"][2]) == ckpt["preprocessing"]`.
- c. Đường offline: `train_alphabet_nested.load(REAL_DATA, {})` lấy đặc trưng của variant `selected[2]`, rồi forward
  model trên CPU → softmax. Nếu `resample == "time"` thì request gửi `timestamps_ms = arange(T)*1000/fps` từ manifest,
  đúng như `load()` dùng khi không có PTS.
- d. Mẫu: TẤT CẢ clip `source == "qipedc"` + 15 clip mỗi người hauuto, chọn bằng `np.random.default_rng(0)`, theo thứ
  tự `sample_id` đã sort.
- e. Với mỗi clip: POST landmarks thô + handedness + width/height từ manifest tới `/sequence` → 200; `prediction` BẰNG
  argmax offline; `abs(confidence - p_offline) <= 1e-4`; `candidates[:3]` có cùng thứ tự lớp với top-3 offline.
- f. Thêm một ca `source_mirrored=True`: lật x và đổi nhãn tay của 5 clip thật → cùng `prediction`/`confidence`.
- g. KHÔNG sửa `TestRealClipEquivalence` cũ. Test đó vẫn chạy với `REAL_CKPT` của nó.

**AC6: Khóa khi nạp.** 8 thread gọi `get_or_load_alphabet_model()` đồng thời với fixture checkpoint. `torch.load` được
gọi đúng 1 lần (đếm bằng `unittest.mock.patch` bọc hàm thật). Cả 8 lần gọi nhận cùng một object model.

**AC7: Hợp đồng OpenAPI.** `GET /openapi.json` có:
- path `/api/fingerspelling/sequence` (POST), `/api/fingerspelling/compose` (POST), `/api/fingerspelling/status` (GET),
  `/api/fingerspelling` (POST).
- schema request của `/sequence` có đủ `landmarks`, `handedness`, `timestamps_ms`, `frame_width`, `frame_height`,
  `source_mirrored`, `top_k`, và `landmarks` có `maxItems` 300.
- schema request của `/compose` có `tokens` với `maxItems` 200.

**AC8: Hồi quy và toàn vẹn test.**
- Lệnh: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed -v`.
- Kỳ vọng: 0 failure, 0 error. Báo số test và số skip thật, kèm lý do từng skip.
- `tests.test_fingerspelling_api`: số test trước và sau bằng nhau, và `TestRealClipEquivalence` KHÔNG skip trên máy này.
- `git diff 09d4057 HEAD -- tests/test_fingerspelling_api.py tests/test_alphabet_preprocessing.py` phải RỖNG.
  Test mới chỉ nằm ở file mới.
- Grep mã mới trong `backend/main.py` và `src/inference/fingerspelling_compose.py` không thấy `random`, không thấy số
  liệu độ chính xác gõ tay.

**AC9: Quy trình.**
- Có output `impact` cho 6 symbol ở §4. Có output `detect-changes --scope all` cho mỗi commit (ghi vào commit message).
- `git status` sau commit cuối: 3 file bị xóa của người dùng vẫn ở trạng thái " D", chưa staged.
- Không commit `.pt`, `.npz`, landmark, file per-clip.
- Có dòng progress_log. Có review `docs/reviews/03-review.md` với kết luận APPROVE.

---

## 6. Rủi ro dữ liệu / ML

- **Nguồn gốc model mặc định chưa được kiểm chứng.** Tên `alphabet_best.pt` trùng với tên của pipeline tổng hợp cũ
  (memory: `data/vsl_alphabet_pilot` là TỔNG HỢP, không được train hay đánh giá trên nó). Bước 0 + AC5-a xử lý rủi ro
  này. Khi chưa có kết luận của Bước 0, không được nói "model Cấp 1 train trên dữ liệu thật".
- **Giấy phép.** hauuto có licence unknown, chỉ dùng nội bộ. Status phải nói điều đó (AC4). Không commit landmark hay
  CSV dự đoán theo clip. `nested_predictions.csv` đã bị gitignore (`.gitignore:72`), và `provenance.json` chỉ chứa số
  đếm. Vấn đề `alphabet_real_best.pt` đã công khai: đã ghi ở data_registry. Việc này không xử lý vấn đề đó.
- **Lệch train và realtime (lớn nhất, nằm NGOÀI backend).** Dữ liệu train được trích bằng Python
  `mp.solutions.hands` 0.10.14 (`max_num_hands=1, model_complexity=1`). Nếu Việc 5 chạy MediaPipe JS (tasks-vision) ở
  trình duyệt thì model và phiên bản đều khác, nên landmark có thể lệch dù test backend pass.
  Backend chỉ giúp được một việc: status đã trả `preprocessing.extractor` và `mediapipe_version` để client đối chiếu.
  Kế hoạch Việc 5 phải quyết định chỗ chạy MediaPipe, và phải có test tương đương client so với trích offline. Test đó
  cần clip webcam thật, nên dính điểm dừng "dữ liệu người dùng quay" (Bước 5 backlog).
- **Cắt ký hiệu.** Train dùng CẢ clip khoảng 3 s (`REPORT.md` bảng capture). Live cắt theo tay xuất hiện/biến mất, nên
  độ dài và phần đệm có thể khác train. Resample theo index giảm bớt ảnh hưởng này nhưng không loại hết. Việc 5 phải ghi
  rõ quy tắc cắt.
- **Cỡ mẫu.** 4 người ký. Dấu thanh có CI [7.5, 74.2] (`reports/alphabet_nested_2026-09-25/REPORT.md:14`), và GATE 0
  kết luận số liệu dấu thanh "không dùng được làm kết quả". Việc này KHÔNG đưa số liệu nào vào API. `prediction_kind`
  chỉ để UI (Việc 5) cảnh báo riêng cho dấu.
- **Tương đương số học.** Model gốc train trên cuda, còn backend chạy CPU. Vì vậy AC5 so backend với offline trên CÙNG
  CPU. So với CSV do run gốc ghi chỉ là thông tin (Bước 0), không phải tiêu chí pass/fail.
- **Rò rỉ.** Không có. Việc này không train và không đánh giá accuracy. AC5 dùng clip hauuto đã có trong train, và chỉ
  để kiểm tra tính đồng nhất đầu vào, không để đo độ chính xác.

---

## 7. Điểm dừng
- Đổi model mặc định: KHÔNG. Không chạm checkpoint, không đổi `ALPHABET_CKPT`.
- Cần dữ liệu người dùng: KHÔNG, với phạm vi này.
- Đụng thay đổi chưa commit của người dùng: KHÔNG. Chỉ `git add` từng đường dẫn cụ thể (AC9).
- Hành động không hoàn tác: KHÔNG.
- Vấn đề dữ liệu mới: CÓ ĐIỀU KIỆN. Nếu Bước 0 ra `UNKNOWN_PROVENANCE` hoặc nguồn khác hauuto → "CẦN NGƯỜI DÙNG",
  và chặn Bước 5/AC5.

## 8. Ngoài phạm vi (chuyển cho kế hoạch sau, ghi để không bị quên)
- Việc 5:
  - thay `Fingerspelling.jsx` (còn gọi endpoint ảnh ở `:69`, nối tên lớp thô ở `:207`, ghi cứng "25 lớp" ở `:130`);
  - cắt ký hiệu phía client;
  - chọn chỗ chạy MediaPipe và làm test tương đương client;
  - thu hẹp CORS (`backend/main.py:151-157`) sau khi dùng proxy `/api` + `/ws` của Vite.
- DoD 8 yêu cầu đo độ trễ "qua WebSocket thật" cho cả Đánh vần, nhưng Cấp 1 dùng REST. Kế hoạch đo hiệu năng phải ghi
  rõ cách đo cho Cấp 1 (REST round-trip) và báo điểm lệch này cho người dùng. Chưa phải điểm dừng.
- Kiểu đặt dấu (cũ hay mới): việc này chọn kiểu cũ và ghi trong response. Nếu người dùng muốn kiểu mới thì đó là một
  thay đổi nhỏ có test.
