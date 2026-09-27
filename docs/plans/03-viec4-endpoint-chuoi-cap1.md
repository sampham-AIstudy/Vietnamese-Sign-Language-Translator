# Kế hoạch 03: Việc 4, endpoint chuỗi landmark cho Cấp 1 "Đánh vần" (chỉ backend/)

> **Điểm dừng: KHÔNG có điểm dừng trước khi code.** Tình trạng này không đổi sau Lần sửa 1.
> Bước 0 vẫn có một **điểm dừng CÓ ĐIỀU KIỆN**, nhưng tiêu chí đã sửa ở Lần sửa 1 (§0).
> - Nếu `provenance.json` sinh lại mà vẫn ra `verdict = UNKNOWN_PROVENANCE`, thì "CẦN NGƯỜI DÙNG" vẫn giữ nguyên, Bước 5
>   (AC5) vẫn bị chặn, và KHÔNG thay checkpoint.
> - Việc này KHÔNG đổi model mặc định: không sửa, không thay, không chép checkpoint, và không đổi giá trị mặc định của
>   `VSL_ALPHABET_CKPT`.
> - Việc này KHÔNG đụng `frontend/` (phần đó thuộc Việc 5).
> - KHÔNG dùng `git add -A` hay `git add .`, vì thư mục làm việc có file bị xóa chưa commit của người dùng.

Nhánh `feat/vslt-complete`. Lập kế hoạch lần đầu tại HEAD `09d4057` (2026-09-27). Kế hoạch đã commit ở `f903980`.
Lập lại (Lần sửa 1) ngày 2026-09-28, sau khi coder trả "CẦN PLANNER".

---

## 0. Lần sửa 1 (sau khi Bước 0 cho `UNKNOWN_PROVENANCE`; coder trả "CẦN PLANNER")

Các commit của coder GIỮ NGUYÊN: `f903980` (Bước 0), `7366274` (Bước 1–4), `1713f8d`. Không viết lại lịch sử. Mọi sửa
đổi đều là commit MỚI.

### 0.1 Nguyên nhân gốc
Tiêu chí danh tính ở Bước 0/AC0 của kế hoạch trước là "sha256 của FILE trùng một checkpoint đã biết VÀ
`trained_on.source == "hauuto"`". Đây là lỗi của kế hoạch. sha256 của file là một **đại diện** cho câu hỏi thật ("model
đang chạy có phải model train trên dữ liệu thật đã biết không"). Đại diện này hỏng ngay khi checkpoint được **đóng gói
lại**: file `.pt` là một dict pickle, nên chỉ cần thêm hoặc bớt một khóa metadata là mọi byte của file đổi, dù trọng số
và mọi thứ ảnh hưởng tới suy luận vẫn giữ nguyên. Kế hoạch trước không lường trường hợp này. Bằng chứng, trích từ
`reports/alphabet_deploy_2026-09-27/provenance.json` (script sinh ở HEAD `4fbc1a2`):
- sha256 của `checkpoints/alphabet_best.pt` (`a6311820…`) khác cả 3 checkpoint đã biết, nên `match = null`.
- `state_dict_equal`: `nested_primary = true`, `nested_variants = true`, `real_run = false`. Tức là mọi tensor bằng
  nhau theo `torch.equal`, cùng khóa, cùng shape, cùng dtype.
- Khóa của file triển khai lệch so với `nested_variants`: có thêm `licence_note`, `evaluation`, và thiếu
  `external_qipedc`, `loso4_val_top1`. Các trường `model_type`, `selected`, `epochs`, `preprocessing`, `trained_on`,
  `classes` đều trùng với `nested_variants`. Còn `nested_primary` chỉ có `classes`, `input_dim`, `model_type`,
  `num_classes`, `selected`, `state_dict`.
- `external_reproduction`: 46/46 argmax trên CPU trùng cột `pred` (run=external) của
  `primary/nested_predictions.csv`. Run gốc chạy trên cuda.

Kết luận: file triển khai là trọng số của model nested (bigru 120 frame, hauuto), đã đóng gói lại với metadata khác.
Ai đóng gói lại và vào lúc nào thì KHÔNG truy được, vì `checkpoints/` bị gitignore. Điểm này ghi vào §6. Nó không làm đổi
kế hoạch, vì các khóa thêm vào không được dùng ở đâu (AC4-f mới).

### 0.2 Tiêu chí mới cho Bước 0 (thay AC0 cũ; KHÔNG nới về bản chất)
`verdict = "real_data_known_checkpoint"` khi và chỉ khi TẤT CẢ V1–V6 đúng. Nếu có bất kỳ điều kiện nào sai hoặc không
tính được (ví dụ thiếu dữ liệu) thì `verdict = "UNKNOWN_PROVENANCE"`.
- **V1 (trọng số).** Gọi M là tập các checkpoint trong `{nested_primary, nested_variants}` có state_dict bằng
  bit-từng-bit với checkpoint triển khai: cùng danh sách khóa theo đúng thứ tự, và mọi tensor cùng shape, cùng dtype,
  `torch.equal`. Yêu cầu: M khác rỗng.
  `real_run` KHÔNG được tính vào M, vì AC5 dùng đường offline của `train_alphabet_nested.load`.
- **V2 (metadata ảnh hưởng suy luận).** Với MỌI K trong M, và với mọi trường trong `{model_type, classes, selected,
  hparams, input_dim, num_classes, epochs, preprocessing, trained_on}` mà K có: checkpoint triển khai cũng phải có
  trường đó, và giá trị phải bằng nhau. Riêng `classes` so cả thứ tự.
- **V3 (nguồn của preprocessing và trained_on).** Ít nhất một K trong M có CẢ `preprocessing` lẫn `trained_on`. Điều
  kiện này bảo đảm hai trường đó đến từ output của run, không phải chỉ được thêm vào lúc đóng gói lại.
- **V4.** `preprocessing` của checkpoint triển khai bằng `train_alphabet_nested.preprocessing_for(selected[2])`.
- **V5.** `trained_on.source == "hauuto"`.
- **V6 (tái lập dự đoán).** `external_reproduction` tính được (dữ liệu + CSV có mặt), và thỏa
  `n == clips_in_csv > 0` và `k == n`.
  Trước đây `external_reproduction` chỉ là thông tin. Từ Lần sửa 1 nó là điều kiện bắt buộc.

Lý do đây KHÔNG phải là nới tiêu chí:
- Điều mà tiêu chí cũ muốn bảo đảm là hành vi suy luận giống hệt một model đã biết, train trên dữ liệu thật.
  V1 + V2 + V4 kiểm trực tiếp đúng điều đó (trọng số bit-exact + mọi tham số suy luận), chứ không qua đại diện.
- V6 thêm một bằng chứng hành vi mà tiêu chí cũ không có.
- Tiêu chí mới CHẶT hơn tiêu chí cũ ở ba chỗ: không chấp nhận khớp với `real_run` (vì AC5 dùng đường nested), bắt buộc
  V4, và bắt buộc V6.
- Thứ duy nhất được phép khác là các khóa metadata KHÔNG dùng khi suy luận. Để bù cho điểm này:
  - `provenance.json` phải ghi `metadata_diff`: khóa chỉ có ở file triển khai, khóa chỉ có ở từng K, và kiểu giá trị
    của chúng. KHÔNG chép giá trị của `evaluation` / `licence_note`, vì các giá trị này không truy được nguồn, và chép
    vào sẽ có người lấy chúng làm số liệu.
  - AC4-f bắt buộc backend không đọc và không trả các khóa đó.
- Việc phát hiện đổi file về SAU vẫn giữ nguyên: AC5-a ghim sha256 của file triển khai vào `provenance.json`.
- Tiêu chí được sửa SAU khi đã thấy kết quả. Điều này được ghi công khai ở đây. Nó được chấp nhận vì hai lý do:
  (1) đây là tiêu chí danh tính, không phải GATE chất lượng hay độ chính xác;
  (2) mọi điều kiện đều chỉ về cùng hướng (khẳng định model này là model nested); không điều kiện nào thay đổi số liệu
  báo cáo hay lựa chọn model.

### 0.3 Xem xét các giả định coder tự đặt
| # | Giả định (commit) | Quyết định | Điều kiện / yêu cầu |
|---|---|---|---|
| G1 | Handler 422 riêng cho `/sequence` và `/compose` (`backend/main.py:221-230`). Body lỗi chỉ có `loc/msg/type`, không trả lại `input` | **CHẤP NHẬN** | Lý do: handler mặc định trả lại `input`, nên khi input chứa NaN thì JSON không hợp lệ → 500 (vi phạm AC1-j), và có thể trả lại tới 1 MiB. Test đã có: `test_nan_inside_a_pydantic_error_is_still_422`, `test_other_paths_keep_default_422_format`. Hợp đồng §3.2 bổ sung: lỗi schema trên hai path này có dạng `{"detail": [{"loc","msg","type"}]}`; lỗi ngữ nghĩa (từ `parse_fingerspelling_sequence`/`compose`) có dạng `{"detail": str}`. Việc 5 phải xử lý cả hai dạng |
| G2 | Trường `compose_endpoint` trong status (`:607`, `:618`) | **CHẤP NHẬN** (chỉ thêm) | Ghi vào hợp đồng §3.4. Cần test MỚI (AC4-g) cho cả hai nhánh `available` true/false. Hiện chưa có test nào |
| G3 | `kind = null` cho lớp ngoài bộ từ Cấp 1 (`class_kind`, `:511-516`) | **CHẤP NHẬN** | Không được từ chối nạp checkpoint có lớp lạ (sẽ làm hỏng fixture `c0..c33` của `tests/test_fingerspelling_api.py`, file không được sửa). Hợp đồng §3.2: `kind`/`prediction_kind` ∈ {`"letter"`, `"tone"`, `null`}; `null` CHỈ khi tên lớp trong checkpoint không thuộc bộ từ Cấp 1. Cần test MỚI: fixture có lớp `c0..` → 200 và `kind is None` (AC4-h). Với checkpoint triển khai: KHÔNG được có `null` (AC5-h) |
| G4a | `multiple_tones`: một cảnh báo cho MỖI dấu trước dấu cuối | **CHẤP NHẬN** | Đúng AC3-b. Cần test số cảnh báo khi có 3 dấu (AC3-f) |
| G4b | "qu"/"gi": nếu bỏ "u"/"i" mà không còn nguyên âm nào thì không bỏ | **CHẤP NHẬN** | Nhất quán với ca `gì` ở AC3-a. Thêm ca `q u` → `qu`, và `q u dấu sắc` → `qú` (AC3-f) |
| G4c | Cụm nguyên âm = dãy nguyên âm liên tiếp ĐẦU TIÊN | **CHẤP NHẬN** | Như §3.3 |
| G4d | Token được chuẩn hóa NFC trước khi so khớp (dạng tổ hợp như `a` + U+0306 được nhận là `ă`); chữ hoa là token lạ → 422 | **CHẤP NHẬN** | Không đoán và không hạ chữ thường. Cần test (AC3-f) |
| G4e | `syllables` bỏ âm tiết rỗng; `text` giữ nguyên khoảng trắng | **CHẤP NHẬN** | Đúng AC3-b |
| G5 | `detect-changes` báo risk HIGH ở `7366274` (35 symbol, 7 luồng, đều thuộc Cấp 1) | **Ghi nhận, không chặn** | Middleware và exception handler đăng ký trên toàn app, nhưng chỉ tác động tới hai path. Reviewer phải kiểm cả 7 luồng: tất cả phải nằm trong Cấp 1. WebSocket (`scope["type"] != "http"`) và các path khác phải đi thẳng qua, có bằng chứng từ `tests.test_ws_throughput` + `test_other_paths_are_not_limited` trong AC8 |

### 0.4 Thay đổi so với kế hoạch trước
- §4: thêm các bước R1–R4.
- §5 có các thay đổi sau. Không bỏ tiêu chí nào, và không nới tiêu chí nào ngoài phần danh tính đã giải thích ở §0.2:
  - AC0 thay bằng AC0' (V1–V6).
  - Thêm AC0b (unit test cho quy tắc verdict).
  - Thêm AC3-f và AC4-f/g/h.
  - Thêm AC5-h.
  - AC8 thêm module `tests.test_alphabet_ckpt_provenance`.
  - AC9 thêm yêu cầu về progress_log.
- §3.2/§3.4: bổ sung hợp đồng cho G1–G3.
- §6: thêm rủi ro "đóng gói lại không truy được".

---

## 1. Mục tiêu và DoD

**Mục tiêu.** Backend đã có endpoint chuỗi landmark (commit `6dd0202`, làm trước quy trình 3 agent và chưa qua
vslt-reviewer). Việc này làm bốn thứ:
1. Kiểm chứng phần đã có.
2. Bổ sung phần còn thiếu để đạt DoD 2 phía backend: giới hạn kích thước request, ghép chữ thành từ có dấu thanh,
   nguồn gốc model trong status.
3. Viết test tương đương train/realtime cho **đúng checkpoint đang nạp**.
4. Đưa vslt-reviewer duyệt.

**DoD phục vụ.**
- DoD 2 (phía backend): endpoint nhận CHUỖI landmark → chữ cái + confidence; ghép chữ thành từ; endpoint ảnh cũ trả 409.
- DoD 6: không có kết quả giả. Không có model thì trả 503. Không ghép khi token không hợp lệ. Nguồn gốc model phải
  hiển thị.
- DoD 7: unit test + contract test + test tương đương train/realtime.
- Mục 11 của reviewer (bảo mật): kiểm tra shape, kích thước và loại input; giới hạn kích thước body.

---

## 2. Hiện trạng: đối chiếu DoD 2 phía backend với code (HEAD `09d4057`, trước khi coder làm)

| Yêu cầu | Đã có? | Bằng chứng | Còn thiếu |
|---|---|---|---|
| Endpoint nhận chuỗi landmark | CÓ | `backend/main.py:483-512` `predict_fingerspelling_sequence`; request model `:398-410`; kiểm tra `:413-456` | Không giới hạn kích thước body trước khi parse JSON |
| Chữ cái + confidence + top-k | CÓ | `:498-512` | Không phân biệt chữ cái với dấu thanh |
| Ảnh cũ → 409 | CÓ | `:515-527`; test `tests/test_fingerspelling_api.py:87-91` | Route khai `file: Optional[UploadFile] = File(None)` (`:516`), nên FastAPI parse toàn bộ multipart rồi mới trả 409 |
| Kiểm tra input → 422 | CÓ phần lớn | `:416-451`; test `:110-127` | Không giới hạn số byte. Các list không có `max_length`. `frame_width/height` không có cận trên. Chưa có test NaN/Infinity và test body không phải JSON |
| 503 khi không có model | CÓ | `:364-395`, `:489-490`; test `:150-159` | Nạp model lười và không có khóa (`:368-395`) |
| Tiền xử lý dùng chung | CÓ | `src/data/alphabet_preprocessing.py:270-304` `alphabet_clip_features`; `scripts/train_alphabet_nested.py:51-73` | — |
| Test tương đương | CÓ, nhưng dùng SAI checkpoint | `tests/test_fingerspelling_api.py:172-219` dùng fixture và `REAL_CKPT = alphabet_real_best.pt` | Chưa có test cho checkpoint đang triển khai. Chưa so confidence |
| Ghép chữ thành từ | KHÔNG | `frontend/src/components/Fingerspelling.jsx:207` nối thẳng tên lớp thô | Cần hàm ghép + endpoint (§3.3) |
| Nguồn gốc model | KHÔNG | Status `:459-480` | `trained_on` + ghi chú giấy phép (`docs/data_registry.md:41-48`) |
| Model Cấp 1 đang nạp | CHƯA KIỂM CHỨNG | `ALPHABET_CKPT` (`:357`), gitignore (`.gitignore:62`) | Bước 0 |

Checkpoint đã biết:
- `reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt`: hauuto, GATE 0 PASS
  (`reports/alphabet_real_run_2026-09-25/GATE0_integrity.md`), `primary/nested.log:6` ghi `('bigru', 120, 'frame')`,
  train trên cuda.
- `.../variants/alphabet_nested_final.pt`.
- `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`: đã commit công khai; giữ hay xóa do người
  dùng quyết.

Dữ liệu thật có trên máy (gitignored): `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv`.

CORS `allow_origins=["*"]` + `allow_credentials=True` (`backend/main.py`, khối CORSMiddleware) là lỗi có từ trước, và
thuộc Việc 5 (§8).

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu (Cấp 1)
```
[Việc 5, frontend] webcam (KHÔNG lật gương) → MediaPipe Hands → cắt 1 ký hiệu (tay xuất hiện → dừng/biến mất, hoặc nút)
   → POST /api/fingerspelling/sequence {landmarks[T], handedness[T], timestamps_ms[T]?, frame_width, frame_height}
[backend] giới hạn body (413) → pydantic (422) → parse_fingerspelling_sequence (422)
   → alphabet_clip_features(..., preprocessing = checkpoint["preprocessing"])   ← CÙNG hàm với train_alphabet_nested.load
   → model → top-k {class, confidence, kind} + prediction_kind
[Việc 5] người dùng chấp nhận hoặc sửa token → danh sách token (chữ, dấu, " ")
   → POST /api/fingerspelling/compose {tokens} → {text, syllables, warnings, tone_style}   ← hàm thuần, không trạng thái
```
Phân chia giữa hai bên:
- **Backend (Việc 4)** không giữ trạng thái. Mỗi request phân loại MỘT ký hiệu, hoặc ghép một danh sách token.
- **Frontend (Việc 5)** lo phần còn lại:
  - chạy MediaPipe;
  - cắt từng ký hiệu;
  - giữ danh sách token;
  - các nút cách, xóa lùi, xóa hết;
  - hiển thị cảnh báo;
  - đọc to.

  Frontend phải gọi `/compose`, không tự ghép chuỗi.

### 3.2 Hợp đồng `POST /api/fingerspelling/sequence` (giữ nguyên các trường cũ, chỉ THÊM)
Input (JSON):
- `landmarks`: có 1..`ALPHABET_MAX_FRAMES` (=300) phần tử. Mỗi phần tử là `null`, `[]`, hoặc đúng 21 × [x, y, z]
  số hữu hạn. Có `max_length` ở cả 3 cấp.
- `handedness`: `null` hoặc T phần tử thuộc {"Left","Right",""}. Bắt buộc khi `mirror_left_hand`.
- `timestamps_ms`: `null` hoặc T số hữu hạn, không giảm. Bắt buộc khi `resample == "time"`.
- `frame_width`, `frame_height`: 1..`ALPHABET_MAX_FRAME_SIDE` (=8192).
- `source_mirrored`: bool.
- `top_k`: 1..10.

Output 200: các trường cũ, thêm:
- `prediction_kind`;
- mỗi `candidates[i]` có thêm `kind`.

Giá trị của `kind` ∈ {`"letter"`, `"tone"`, `null`}. `null` CHỈ xuất hiện khi tên lớp trong checkpoint không thuộc bộ
từ Cấp 1 (G3). `confidence` vẫn là `round(v, 4)`.

Mã lỗi:
- **413**: body > `ALPHABET_MAX_BODY_BYTES` (=1_048_576).
  - Áp cho cả request có `Content-Length` lẫn request chunked, và kiểm TRƯỚC khi parse.
  - CHỈ áp cho `/api/fingerspelling/sequence` và `/api/fingerspelling/compose`.
  - `/api/fingerspelling` luôn trả 409.
- **422**:
  - lỗi schema: `{"detail": [{"loc","msg","type"}]}`, không trả lại `input` (G1);
  - lỗi ngữ nghĩa: `{"detail": str}`.
  - Các trường hợp gây 422: sai kiểu/shape, NaN/Infinity, body không phải JSON, vượt độ dài, `frame_*` ngoài khoảng,
    thiếu `handedness`/`timestamps_ms` khi model cần, ít hơn `min_detected_frames` khung có tay.
- **503**: không có checkpoint hợp lệ.
- Không bao giờ trả 500 khi input xấu.

Lý do chọn 1 MiB: test AC1-e dựng payload hợp lệ lớn nhất và chứng minh nó nhỏ hơn giới hạn và vẫn trả 200.

### 3.3 Hợp đồng `POST /api/fingerspelling/compose` + module thuần
Module `src/inference/fingerspelling_compose.py` không import torch hay fastapi. Nó có:
- các hằng `LETTERS` (29), `TONE_MARKS` (5 dấu → dấu kết hợp U+0301, U+0300, U+0309, U+0303, U+0323), `SPACE = " "`;
- `token_kind(token)`: trả `"letter" | "tone" | "space"`; token lạ thì ném `ValueError`. Token được chuẩn hóa NFC
  trước khi so khớp; không hạ chữ thường (G4d);
- `compose(tokens)`: trả `{"text": NFC, "syllables": [...], "warnings": [{"code","token_index","message"}]}`.

Quy tắc ghép:
1. Âm tiết là phần giữa hai `" "`. Dấu thanh áp cho cả âm tiết, bất kể nó đứng ở vị trí nào trong âm tiết.
2. Âm tiết có từ 2 dấu trở lên: dùng dấu CUỐI. Mỗi dấu đứng trước sinh một cảnh báo `multiple_tones` (G4a).
3. Âm tiết không có nguyên âm: không áp dấu, và sinh cảnh báo `tone_without_vowel`. Không sửa hay đoán chữ.
4. Tập nguyên âm: a ă â e ê i o ô ơ u ư y.
   - Bỏ "u" của "qu" ở đầu âm tiết.
   - Bỏ "i" của "gi" ở đầu âm tiết khi phía sau còn nguyên âm khác.
   - Nếu bỏ đi mà không còn nguyên âm nào thì không bỏ (G4b).

   Trên dãy nguyên âm liên tiếp ĐẦU TIÊN (G4c), chọn nguyên âm mang dấu theo thứ tự ưu tiên:
   (a) nếu có nguyên âm mang mũ/móc, lấy nguyên âm mang mũ/móc CUỐI;
   (b) nếu không, và có phụ âm cuối, lấy nguyên âm cuối của cụm;
   (c) nếu không, và cụm có 3 nguyên âm, lấy nguyên âm giữa;
   (d) nếu không, và cụm có 2 nguyên âm, lấy nguyên âm ĐẦU (kiểu cũ);
   (e) cụm 1 nguyên âm thì lấy nguyên âm đó.

   Response ghi `"tone_style": "traditional"`.
5. Output ở dạng NFC, chữ thường, giữ nguyên khoảng trắng. `syllables` bỏ các âm tiết rỗng (G4e).

Endpoint:
- Input: `{"tokens": [str]}`, có 0..`COMPOSE_MAX_TOKENS` (=200) phần tử.
- 200: kết quả `compose(...)` kèm `tone_style`.
- 422: token lạ (thông báo nêu vị trí), vượt độ dài, sai kiểu.
- 413: body quá lớn.
- Không cần model.

Tập `LETTERS ∪ TONE_MARKS` phải BẰNG `ALPHABET_CLASSES`, và bằng `classes` của checkpoint triển khai.

### 3.4 Status (`GET /api/fingerspelling/status`, chỉ THÊM)
- `trained_on`: lấy nguyên từ checkpoint, hoặc `null`.
- `data_provenance`: hằng tra theo `trained_on.source`. Với hauuto là
  `{"licence": "unknown", "usage": "internal only", "registry": "docs/data_registry.md#1b"}`. Các trường hợp khác trả
  `{"status": "unknown"}`.
- `evaluation_report`: chỉ đường dẫn tới báo cáo.
- `compose_endpoint`: có ở cả hai nhánh `available` true/false (G2).
- Backend KHÔNG đọc và KHÔNG trả các khóa `evaluation` hay `licence_note` của checkpoint (§0.2).
- Không từ chối nạp checkpoint thiếu `trained_on`.

### 3.5 Nạp model an toàn khi chạy đồng thời
Dùng `threading.Lock` theo kiểu double-checked. Khi lỗi thì trả `(None, None)`, và lần gọi sau thử nạp lại.

---

## 4. Chia việc

Các bước 0–4 và 6 (trừ review) ĐÃ LÀM ở `f903980`, `7366274`, `1713f8d`. Nội dung gốc của các bước này giữ ở cuối mục
để truy vết. Việc còn lại:

**R1: Sửa quy tắc verdict + sinh lại provenance (≤ 1.5 giờ).**
- Trong `scripts/alphabet_ckpt_provenance.py`, thay `verdict_for` bằng một hàm THUẦN. Hàm này nhận các dict đã nạp và
  kết quả tái lập, không đọc đĩa, và trả `(verdict, checks)`. `checks` có `V1`…`V6`, mỗi mục là `{"ok": bool,
  "detail": ...}`.
- JSON ghi thêm các mục sau:
  - `verdict_checks`;
  - `M` (tên các K thỏa V1);
  - `sha256_match` (giữ tên cũ `match` với cùng nghĩa, để tương thích);
  - `metadata_diff`: chỉ ghi tên khóa + tên kiểu giá trị, KHÔNG ghi giá trị;
  - `verdict_rule`: câu mô tả V1–V6.
- `external_reproduction` bỏ nhãn "information only", vì đã thành V6.
- Unit test cho hàm verdict: `tests/test_alphabet_ckpt_provenance.py` (AC0b).
- Sinh lại JSON 2 lần (AC0').

**R2: Test còn thiếu cho G2, G3, G4 và cho khóa metadata không truy được (≤ 1 giờ).**
- Chỉ THÊM test (AC3-f, AC4-f/g/h) vào `tests/test_fingerspelling_limits.py` / `tests/test_fingerspelling_compose.py`.
- Không sửa và không xóa test đã có.
- Chỉ sửa code nếu test mới lộ ra lỗi.

**R3: Bước 5 = AC5 (≤ 1.5 giờ). CHỈ làm khi AC0' ra `real_data_known_checkpoint`.**
- `tests/test_fingerspelling_deployed.py`.

**R4: Chốt (≤ 1 giờ).**
- Chạy AC8.
- Chạy `detect-changes --scope all` trước MỖI commit.
- `git add` theo từng đường dẫn.
- progress_log (AC9).
- vslt-reviewer.

Trước khi sửa symbol nào, phải chạy GitNexus `impact` (upstream). Riêng R1: chạy cho `verdict_for` và `build_report`.

*(Truy vết, đã làm)*
- Bước 0: `scripts/alphabet_ckpt_provenance.py` + `provenance.json`.
- Bước 1: giới hạn 413/422 + 409 không đọc body.
- Bước 2: module compose.
- Bước 3: `/compose`, `prediction_kind`, status có nguồn gốc.
- Bước 4: khóa khi nạp.
- Bước 6: docstring + test + commit.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; coder KHÔNG được đổi)

Môi trường: `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`. Output thật của mọi lệnh phải ghi vào báo cáo của coder.

**AC0' (Lần sửa 1, thay AC0): Nguồn gốc.**
- Lệnh: `.venv/Scripts/python scripts/alphabet_ckpt_provenance.py --out reports/alphabet_deploy_2026-09-27/provenance.json`.
- `verdict` phải do script tính theo V1–V6 (§0.2). `verdict_checks` có đủ 6 mục.
- Chạy 2 lần: JSON giống hệt nhau, trừ `generated_by`.
- `metadata_diff` không chứa giá trị của `evaluation` hay `licence_note`.
- Nếu `verdict == "real_data_known_checkpoint"`: làm R3, và dòng progress_log mới ghi rõ "CẦN NGƯỜI DÙNG của dòng
  2026-09-28 trước được gỡ theo Lần sửa 1 (tiêu chí V1–V6)".
- Nếu không: giữ "CẦN NGƯỜI DÙNG", AC5 = "BLOCKED (điểm dừng)", KHÔNG tính là PASS, và KHÔNG thay checkpoint.

**AC0b (mới): Unit test quy tắc verdict** (`tests/test_alphabet_ckpt_provenance.py`).
- Chỉ dùng fixture checkpoint nhỏ tạo trong test (tensor vài phần tử). Không đọc checkpoint thật.
- Mỗi ca là một test:
  - a. Trọng số bit-exact + metadata suy luận trùng + K có `preprocessing`/`trained_on` + V4, V5 + tái lập `k == n > 0`
    → `real_data_known_checkpoint`.
  - b. Như (a), nhưng file triển khai có thêm khóa `evaluation` và `licence_note` → vẫn real. `metadata_diff` liệt kê
    đúng tên khóa, và không chứa giá trị.
  - c. Một tensor lệch 1 ULP (`torch.nextafter`) → UNKNOWN, và `V1.ok == False`.
  - d. Thứ tự khóa của state_dict khác → UNKNOWN.
  - e. `classes` cùng tập nhưng khác thứ tự → UNKNOWN (V2).
  - f. `preprocessing` khác ở một trường (ví dụ `target_frames`) → UNKNOWN (V2 hoặc V4).
  - g. Chỉ khớp với `real_run` → UNKNOWN (V1).
  - h. Trong M không có K nào có cả `preprocessing` và `trained_on` → UNKNOWN (V3).
  - i. `trained_on.source = "other"` → UNKNOWN (V5).
  - j. Tái lập `k = n - 1` → UNKNOWN. Tái lập `null` (thiếu dữ liệu) → UNKNOWN. `n = 0` → UNKNOWN (V6).
  - k. sha256 trùng hệt nhưng V6 sai → UNKNOWN. Trùng sha256 không được miễn điều kiện nào.

**AC1: Giới hạn input.** Giữ nguyên như kế hoạch trước (ý a–j). Đã có test trong `tests/test_fingerspelling_limits.py`.

**AC2: 409.** Giữ nguyên.

**AC3: Ghép chữ.**
- a–e giữ nguyên như kế hoạch trước (bảng 26 ca, cảnh báo, NFC, tập nhãn, endpoint).
- **f (mới, G4):**
  - `a dấu sắc dấu huyền dấu hỏi` → `ả` + ĐÚNG 2 cảnh báo `multiple_tones`, với `token_index` 1 và 2.
  - `q u` → `qu`; `q u dấu sắc` → `qú`.
  - token dạng tổ hợp `"ă"` được nhận là `ă`, nên `["ă", "dấu sắc"]` → `ắ`.
  - token `"A"` → `compose` ném `ValueError`, và endpoint trả 422.

**AC4: Response và status.**
- a–e giữ nguyên (kind, trained_on null/hauuto/nguồn lạ, evaluation_report, trường cũ).
- **f (mới):** fixture checkpoint có thêm `"evaluation": {"top1": 0.5}` và `"licence_note": "x"`. Kiểm:
  - Body của status và của `/sequence` không có khóa `evaluation` hay `licence_note` ở bất kỳ cấp nào (duyệt đệ quy).
  - Không chứa chuỗi `"licence_note"`.
- **g (mới, G2):** `compose_endpoint == "/api/fingerspelling/compose"` khi `available` true, và cả khi checkpoint không
  tồn tại (`available` false).
- **h (mới, G3):** fixture có `classes = ["c0", …]` → `/sequence` trả 200. `prediction_kind is None`, và mọi
  `candidates[i]["kind"] is None`.

**AC5: Tương đương train/realtime cho checkpoint ĐANG TRIỂN KHAI** (`tests/test_fingerspelling_deployed.py`).
- Ý a–g giữ nguyên:
  - a. sha256 của `checkpoints/alphabet_best.pt` bằng `provenance.json` → `checkpoints.deployed.sha256`. Nếu lệch thì
    FAIL; đây là cơ chế phát hiện đổi file về sau.
  - b. `preprocessing_for(selected[2]) == ckpt["preprocessing"]`.
  - c. Đường offline là `train_alphabet_nested.load`, chạy trên CPU.
  - d. Mẫu: mọi clip qipedc, cộng 15 clip mỗi người hauuto, chọn bằng `default_rng(0)` trên danh sách `sample_id` đã sort.
  - e. Cùng `prediction`; `|Δconfidence| ≤ 1e-4`; cùng top-3.
  - f. `source_mirrored=True` cho 5 clip.
  - g. Không sửa `TestRealClipEquivalence`.
- **h (mới, G3):** với mọi clip của AC5, `prediction_kind` và mọi `kind` đều ≠ `None`.
- Test thêm: `provenance.json` → `verdict == "real_data_known_checkpoint"` (test đọc JSON đã commit).
- skipUnless checkpoint + manifest. Trên máy này phải chạy, 0 skip.

**AC6: Khóa khi nạp.** Giữ nguyên.

**AC7: OpenAPI.** Giữ nguyên.

**AC8: Hồi quy.**
- Lệnh: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance -v`.
- Kết quả: 0 failure, 0 error. Báo số test và số skip thật, kèm lý do từng skip.
- Nếu AC0' ra UNKNOWN: chạy lệnh trên nhưng không có `tests.test_fingerspelling_deployed`, và ghi rõ điều này.
- `git diff 09d4057 HEAD -- tests/test_fingerspelling_api.py tests/test_alphabet_preprocessing.py` phải RỖNG.
- `git diff 1713f8d HEAD -- tests/test_fingerspelling_limits.py tests/test_fingerspelling_compose.py` chỉ có dòng THÊM.
- Grep mã mới không thấy `random` và không thấy số liệu độ chính xác gõ tay.

**AC9: Quy trình.**
- Có output `impact` cho mọi symbol bị sửa. Mỗi commit có `detect-changes --scope all`, ghi risk vào commit message.
- `git status`: 3 file bị xóa của người dùng vẫn ở trạng thái " D", chưa staged.
- Không commit `.pt`, `.npz`, landmark, hay file per-clip.
- **progress_log:** THÊM một dòng mới cho Lần sửa 1, không sửa dòng 2026-09-28 cũ. Dòng mới ghi:
  - commit;
  - verdict mới cùng 6 kết quả V1–V6 (lấy từ JSON);
  - trạng thái "CẦN NGƯỜI DÙNG" được gỡ hay còn giữ, kèm lý do;
  - số test trước → sau.
- Review `docs/reviews/03-review.md` kết luận APPROVE.

---

## 6. Rủi ro dữ liệu / ML

- **Nguồn gốc model mặc định.** AC0' giải quyết rủi ro này bằng V1–V6. Chỉ khi AC0' đạt mới được nói "model Cấp 1 là
  model nested train trên hauuto (dữ liệu thật)".
- **Đóng gói lại không truy được (mới).** `checkpoints/alphabet_best.pt` có hai khóa `licence_note` và `evaluation`.
  Không run nào sinh ra chúng, và không biết ai thêm hay thêm lúc nào.
  - Các giá trị này KHÔNG được dùng làm số liệu ở bất kỳ đâu: README, EVALUATION, API, báo cáo.
  - Số liệu Cấp 1 chỉ lấy từ `reports/alphabet_nested_2026-09-25/primary/nested_report.json` + `REPORT.md`.
  - Ghi điểm này vào mục "Giới hạn" của báo cáo cuối (DoD 9).
- **Giấy phép.** hauuto: unknown, chỉ dùng nội bộ. `provenance.json` chỉ chứa số đếm và tên khóa.
- **Lệch train/realtime (ngoài backend).** Dữ liệu train được trích bằng `mp.solutions.hands` 0.10.14 (Python). Nếu
  Việc 5 chạy MediaPipe JS thì landmark có thể lệch. Việc 5 phải xử lý và phải có test tương đương cho client (cần
  clip webcam thật).
- **Cắt ký hiệu.** Lúc train, mỗi mẫu là cả clip dài khoảng 3 s. Lúc live, ký hiệu được cắt theo tay xuất hiện/biến
  mất. Việc 5 phải ghi rõ quy tắc cắt.
- **Cỡ mẫu.** Chỉ có 4 người ký. Dấu thanh có CI [7.5, 74.2]. Không đưa số liệu nào vào API.
- **Tương đương số học.** Model train trên cuda, backend chạy CPU. AC5 so với đường offline chạy trên cùng CPU. V6 so
  argmax với CSV của run cuda, và đã quan sát được 46/46. Nếu sau này cần sinh lại mà ra k < n, verdict sẽ thành
  UNKNOWN; khi đó dừng lại, KHÔNG nới V6.
- **Rò rỉ.** Không có, vì không train và không đo accuracy.

---

## 7. Điểm dừng
- Đổi model mặc định: KHÔNG.
- Cần dữ liệu từ người dùng: KHÔNG.
- Đụng thay đổi chưa commit của người dùng: KHÔNG.
- Hành động không hoàn tác: KHÔNG.
- Vấn đề dữ liệu mới: CÓ ĐIỀU KIỆN. Nếu AC0' vẫn ra UNKNOWN → "CẦN NGƯỜI DÙNG", chặn R3/AC5. Việc đóng gói lại không
  truy được KHÔNG phải điểm dừng: nó không đổi kế hoạch hay model, và chỉ cần ghi vào mục "Giới hạn".

## 8. Ngoài phạm vi
- Việc 5:
  - `Fingerspelling.jsx` (`:69` gọi endpoint ảnh, `:207` nối tên lớp thô, `:130` ghi cứng "25 lớp");
  - cắt ký hiệu phía client;
  - chọn nơi chạy MediaPipe và viết test tương đương cho client;
  - thu hẹp CORS;
  - xử lý cả hai dạng body của lỗi 422 (G1).
- DoD 8 ghi đo độ trễ "qua WebSocket" cho cả chế độ Đánh vần, nhưng Cấp 1 dùng REST. Việc đo hiệu năng phải ghi rõ
  điểm lệch này và báo người dùng.
- Kiểu đặt dấu: hiện là kiểu cũ. Đổi sang kiểu mới là một thay đổi nhỏ, có test.
