# Review kế hoạch 03: Việc 4, endpoint chuỗi landmark Cấp 1 (vòng 1)

- Kế hoạch: `docs/plans/03-viec4-endpoint-chuoi-cap1.md` (bản gốc ở f903980, cùng §0 "Lần sửa 1" ở 9be36e4).
- Commit được review: 6dd0202 (làm trước quy trình 3 agent, chưa review lần nào), f903980, 7366274, 1713f8d, 9be36e4, 1a471cb,
  4145e51, 2038551, 9f4eb68. HEAD `9f4eb68`, nhánh `feat/vslt-complete`.
- Reviewer: vslt-reviewer, ngày 2026-09-28. Tôi tự đọc diff, tự chạy lại mọi lệnh, và không dựa vào phần tóm tắt của coder.
  Tôi không sửa file nào ngoài file này. Các lần chạy script provenance đều ghi ra thư mục tạm, không ghi đè JSON đã commit.
  `git status` trước và sau khi review giống nhau: chỉ có 3 file bị xóa (trạng thái " D") của người dùng, chưa staged.

**Kết luận: CHANGES_REQUESTED.** Có 1 FAIL ở mục 11. Đây là lỗi triển khai: `/sequence` trả **500** khi nhận landmark là số hữu hạn
nhưng rất lớn. Lỗi này vi phạm hợp đồng §3.2 của chính kế hoạch ("Không bao giờ trả 500 khi input xấu"). Mọi mục còn lại đạt.
Riêng việc sửa tiêu chí Bước 0 (Lần sửa 1), tôi đánh giá là **không nới về bản chất** (xem mục 12).

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS (có ghi chú) | Mỗi AC đều có test, và test kiểm đúng điều AC yêu cầu. **AC0'**: tôi chạy lại script (xem mục 7). **AC0b a–k**: `tests/test_alphabet_ckpt_provenance.py`. Mỗi ca assert đúng điều kiện V tương ứng là False. Ví dụ ca c: `torch.nextafter` → `V1.ok` False và `M == []`. Ca f tách riêng V2 và V4 (`test_f_v4_alone`). Ca k: sha256 trùng nhưng V6 sai → UNKNOWN. `test_pure_no_disk_access` patch `open` và `torch.load`. **AC1 a–j, AC2, AC4 a–h, AC6, AC7**: `tests/test_fingerspelling_limits.py`. Test 413 kiểm cả Content-Length lẫn chunked, và có test xác nhận request chunked không mang header content-length. Body đúng bằng giới hạn → 200. AC4-f duyệt đệ quy mọi khóa. AC6 dùng Barrier 8 thread với `torch.load` chậm 0.2 s, và kiểm `call_count == 1`. **AC3 a–f**: `tests/test_fingerspelling_compose.py`, gồm 26 ca bảng chép nguyên văn kế hoạch; token tổ hợp được kiểm là khác dạng dựng sẵn trước khi compose. **AC5 a–h**: `tests/test_fingerspelling_deployed.py` (xem mục 9). Ghi chú: (i) quét AC1-j có `1e300` (tràn float32 → inf → 422), nhưng không có số hữu hạn lớn như `3e38`, nên lọt lỗi ở mục 11. (ii) AC1-e tự nhận là payload "as long as floats can make it", nhưng dùng số mũ `e-05`. Tôi đo lại: payload của test là 483 132 byte; khi thay mọi tọa độ bằng `-1.2345678901234567e-300` thì là 514 632 byte. Vẫn nhỏ hơn 1 048 576, nên kết luận 1 MiB là đủ vẫn đúng. |
| 2 | Tự chạy lại test | PASS | Lệnh AC8 đầy đủ (14 module) ở HEAD 9f4eb68: **Ran 232 tests, OK**, 0 skip, 0 failure, 0 error. Theo module: provenance 16, preprocessing 6, aspect 3, api 11, compose 25, deployed 7, limits 32, realtime 3, report_step4 105, split_guards 6, translation_core 8, unified_split 4, vsl_system 6. Tổng 232, khớp với số coder báo (progress_log, 2038551). `TestRealClipEquivalence` và cả 7 test deployed đều chạy, không skip. **Lưu ý:** `tests.test_ws_throughput` có **0 test**. File này là script thủ công (`asyncio.run(stress_test())`) và cần server thật ở 127.0.0.1:8000. Xem mục 13. |
| 3 | Test không bị sửa/nới | PASS | `git diff 09d4057 HEAD -- tests/test_fingerspelling_api.py tests/test_alphabet_preprocessing.py`: 0 dòng. `git diff 1713f8d HEAD -- tests/test_fingerspelling_limits.py tests/test_fingerspelling_compose.py`: 0 dòng bị xóa. Số test tăng: limits 29 → 32, compose 21 → 25 (đếm `def test_` ở 1713f8d và ở HEAD). `git diff --stat 09d4057 HEAD -- tests/`: chỉ có dòng thêm. |
| 4 | Nguồn dữ liệu | PASS | Model triển khai có `trained_on` = hauuto, 4 người ký, 636 clip (provenance.json). Manifest thật `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` có 686 dòng (hauuto 640 = 4 × 160, qipedc 46), extractor `mp.solutions.hands`, MediaPipe 0.10.14. `docs/data_registry.md` §1b: người thật, MediaPipe thật (GATE0_integrity). Grep `pilot` trong `scripts/train_alphabet_nested.py`, `scripts/train_alphabet_real.py`, `backend/main.py`: 0 kết quả, nên KHÔNG dùng `data/vsl_alphabet_pilot`. Fixture checkpoint trong test là trọng số ngẫu nhiên có seed, và được ghi rõ là fixture, không phải dữ liệu. |
| 5 | Rò rỉ | PASS (không áp dụng) | Việc này không train và không đo độ chính xác. AC5 có dùng clip hauuto đã nằm trong tập train, nhưng chỉ để so đầu vào/đầu ra giữa hai đường; docstring của test ghi rõ "not accuracy". |
| 6 | VAL/TEST | PASS (không áp dụng) | Không chọn model mới, và không đổi model mặc định: `ALPHABET_CKPT` mặc định vẫn là `checkpoints/alphabet_best.pt`. File đó vẫn có mtime 2026-09-25 15:14, và sha256 bằng giá trị trong provenance (AC5-a pass). Model gốc được chọn bằng inner-VAL trong nested LOSO (`primary/nested.log`). |
| 7 | Số liệu truy được | PASS | Tôi chạy lệnh AC0' 2 lần, ghi ra thư mục tạm. Kết quả: verdict `real_data_known_checkpoint`, V1–V6 đều True, M = nested_primary + nested_variants, 46/46. Sau khi bỏ `generated_by`: lần 1 bằng lần 2, **và** bằng `reports/alphabet_deploy_2026-09-27/provenance.json` đã commit (True, True). JSON có `command` và `head` 9be36e4. Các số trong progress_log (V1–V6, 46/46, 232, 202, 152) khớp với JSON, khớp số test tôi đếm, và khớp phép cộng 202 + 16 + 7 + 4 + 3 = 232. Mã mới không chứa số liệu độ chính xác. `evaluation_report` chỉ là đường dẫn. |
| 8 | Cỡ mẫu | PASS (không áp dụng) | Không đưa số liệu mới vào API hay tài liệu. V6 là tỉ lệ khớp argmax (46/46), không phải accuracy; JSON ghi rõ điều này trong `note`. |
| 9 | Nhất quán train–realtime | PASS | `tests/test_fingerspelling_deployed.py` chạy trên **checkpoint triển khai** `checkpoints/alphabet_best.pt`, có sha256 ghim theo provenance. Dữ liệu thật: 46 clip qipedc + 15 clip × 4 người hauuto = 106 clip, chọn bằng `default_rng(0)` trên `sample_id` đã sort. 0 skip. Đường offline là `train_alphabet_nested.load` (đúng mã trích đặc trưng của run nested), cộng model dựng lại bằng `train_alphabet_real.build` trên CPU, độc lập với loader của backend. Test so `prediction`, độ lệch confidence ≤ 1e-4, top-3, và thêm 5 clip `source_mirrored`. Aspect ratio lấy từ width/height trong manifest, giống `load()`. Giới hạn của tính độc lập: cả hai đường cùng gọi `alphabet_clip_features`, nên test chứng minh backend = đường train, chứ không kiểm chính hàm đó. Điểm neo vào lúc train là V6: 46/46 argmax khớp với CSV của run cuda gốc khi chạy bằng mã hiện tại. `src/data/alphabet_preprocessing.py` và `scripts/train_alphabet_nested.py` không đổi kể từ d1c844f (git log). MediaPipe phía client (JS) chưa được kiểm; việc này thuộc Việc 5 (§6). |
| 10 | Mock / kết quả giả / hard-code | PASS | Grep các dòng thêm trong diff 4fbc1a2..HEAD của `backend/main.py`, `src/inference/fingerspelling_compose.py`, `scripts/alphabet_ckpt_provenance.py`: không có `random`, không có `mock`, không có số thập phân gõ tay. Khi không có model, `/sequence` trả 503 (có test). `/compose` là hàm thuần. Backend không đọc `evaluation` hay `licence_note`: grep `backend/main.py` chỉ thấy hằng `ALPHABET_DATA_PROVENANCE` và `evaluation_report` (là đường dẫn). Ghi chú (không chặn): input suy biến (21 điểm trùng nhau, nên palm = 0) vẫn trả 200 với confidence 0.8566. Đây không phải kết quả giả, nhưng là dự đoán trên dữ liệu không phải bàn tay. Xem mục CẦN PLANNER. |
| 11 | Bảo mật | **FAIL** | **Lỗi:** POST `/sequence` bằng checkpoint triển khai, 10 khung, mỗi khung 21 điểm dạng `[3e38*(i%2), -3e38*(i%3==0), 1.0]` → **500 Internal Server Error**. Với `raise_server_exceptions=True`, lỗi là `ValueError: Out of range float values are not JSON compliant`. Nguyên nhân: 3e38 hữu hạn trong float32 nên qua được kiểm isfinite (`backend/main.py:555-564`). Sau đó phép nhân aspect ratio (`src/data/alphabet_preprocessing.py:203`) tràn thành inf, và phép chia cho palm (`:53`) ra NaN. Softmax ra NaN, và JSONResponse từ chối NaN. Với 2e38 hay 1e38 thì trả 200. **Phần đạt:** 413 cho cả Content-Length lẫn chunked, và CHỈ trên 2 path. Tôi kiểm trực tiếp `PathBodyLimitMiddleware` với max 10 byte: scope websocket (cả `/ws/live-stream` lẫn `/api/fingerspelling/sequence`) và lifespan đi thẳng qua; `/api/translate` với 100 byte đi thẳng qua; `/compose` với 100 byte → 413. `/api/fingerspelling`: route không có tham số, OpenAPI không có requestBody, multipart 5 MB → 409, body thô 3 MB → 409. 422 lỗi schema chỉ có loc/msg/type; NaN nằm trong lỗi pydantic → 422, và body trả về không chứa NaN; các path khác giữ định dạng mặc định. Status không có `evaluation`/`licence_note` (AC4-f; tôi kiểm lại với checkpoint thật). Response 413 vẫn có header CORS (CORS là lớp ngoài cùng). **Ghi nhận thêm (mức thấp):** 422 ngữ nghĩa trả lại input của client mà không giới hạn độ dài. `handedness ... got {bad[:5]}` (`backend/main.py:576`) trả 400 070 byte khi gửi 2 nhãn, mỗi nhãn 400 KB. `unknown token` (`src/inference/fingerspelling_compose.py:119`) trả 900 040 byte. Chỉ phản chiếu input của chính client, không lộ dữ liệu của server, nhưng ngược với lý do đưa ra ở G1. **Có từ trước, ngoài phạm vi (§8, Việc 5):** CORS `allow_origins=["*"]` + `allow_credentials=True` (`backend/main.py:237-243`): request có `Origin: http://evil.example` nhận lại đúng origin đó kèm allow-credentials true. `/ws/live-stream` không giới hạn kích thước message ở tầng ứng dụng: frame 2 MiB vẫn được nhận và xử lý. Không lộ token hay kaggle.json. Không commit file .pt/.npz (`git diff --name-only 4fbc1a2 HEAD`). |
| 12 | So sánh công bằng / không nới GATE | PASS (có ghi chú) | Đánh giá Lần sửa 1: V1–V6 thay cho "sha256 của file trùng VÀ source = hauuto". **Không nới về bản chất**, vì bốn lý do. (a) Câu hỏi thật là: hành vi suy luận có đúng là của model đã biết, train trên dữ liệu thật hay không. V1 (state_dict bit-exact, cùng thứ tự khóa, cùng dtype), V2 (mọi trường ảnh hưởng suy luận) và V4 trả lời trực tiếp câu hỏi này. Tôi đối chiếu thì thấy backend chỉ đọc `classes`, `preprocessing`, `model_type`, `hparams`, `state_dict`, `trained_on`, và cả sáu trường đều nằm trong V1/V2. (b) Tiêu chí mới chặt hơn ở 3 chỗ: loại `real_run` khỏi M, bắt buộc V4, bắt buộc V6. (c) Chỗ được nới DUY NHẤT là danh tính theo byte của file: tiêu chí mới chấp nhận các khóa metadata không truy được nguồn (`evaluation`, `licence_note`). Chỗ này có bù: `metadata_diff` chỉ ghi tên khóa và kiểu (tôi kiểm: không lá nào của `evaluation` và không giá trị `licence_note` nào xuất hiện trong JSON); có AC4-f; có AC5-a ghim sha256. (d) Tiêu chí được sửa sau khi đã thấy kết quả, và việc này được ghi công khai (§0.2). Đây là tiêu chí danh tính, không phải GATE chất lượng, và không làm đổi số liệu hay lựa chọn model. Ghi chú: (1) Theo mtime, `checkpoints/alphabet_best.pt` (25/09 15:14) có SAU `primary` (14:32) nhưng TRƯỚC `variants/alphabet_nested_final.pt` (15:30). Vì vậy V3 chứng minh được "metadata BẰNG output của một run", chứ không chứng minh "được chép từ output đó". Kết luận về hành vi không đổi; mtime chỉ là bằng chứng yếu. (2) Mọi bằng chứng cho V1/V3/V6 (các file .pt ở primary và variants, và `primary/nested_predictions.csv`) đều bị gitignore và chỉ có trên máy này, nên máy khác không tái lập được verdict. Xem mục CẦN NGƯỜI DÙNG. |
| 13 | Kết luận vượt bằng chứng | PASS (có ghi chú) | Sản phẩm của coder không có kết luận sai. progress_log ghi đúng những gì JSON và test cho thấy, và docstring AC5 nói rõ "not accuracy". Có 3 câu mạnh hơn bằng chứng, cần ghi lại cho đúng (mức thấp). (i) Kế hoạch §0.3 G5 nói việc WebSocket đi thẳng qua "có bằng chứng từ `tests.test_ws_throughput`". Nhưng module này có **0 test tự động**, nên AC8 không chứng minh được gì cho WebSocket. Kết luận vẫn đúng, có điều bằng chứng là của reviewer: kiểm middleware trực tiếp (mục 11), và gọi `TestClient.websocket_connect("/ws/live-stream")` qua toàn bộ app → được accept; gửi 2 MiB → nhận `frame_result`. (ii) Docstring AC1-e ghi "as long as floats can make it", điều này không đúng (mục 1); kết luận < 1 MiB vẫn đúng. (iii) Message của 6dd0202 ghi "now also used by the training scripts", nhưng commit này không đụng script train nào; `train_alphabet_nested` bắt đầu dùng `alphabet_clip_features` từ d1c844f, 11 phút sau. Chỉ là mô tả lịch sử, không ảnh hưởng gì. |

## Kiểm tra riêng

### Commit 6dd0202 (làm trước quy trình 3 agent)
- Nội dung:
  - thêm `/api/fingerspelling/sequence`, cùng `alphabet_clip_features` dùng chung;
  - endpoint ảnh trả 409;
  - từ chối nạp checkpoint thiếu `classes` hoặc `preprocessing`;
  - thêm biến môi trường `VSL_ALPHABET_CKPT`, giá trị mặc định **giữ nguyên** `checkpoints/alphabet_best.pt`.
- Các thiếu sót so với DoD. 7366274 đã sửa tất cả và có test:
  - không giới hạn kích thước body;
  - `File(None)` khiến FastAPI vẫn parse multipart;
  - các list không có `max_length`;
  - không có cận trên cho `frame_*`;
  - `np.asarray` chạy trên list lởm chởm.

  Lỗi "số hữu hạn lớn → 500" (mục 11) có từ 6dd0202 và vẫn còn.
- `TestRealClipEquivalence` (6dd0202) dùng model do chính backend nạp, với `REAL_CKPT`, không phải checkpoint triển khai. Kế hoạch đã
  ghi nhận điều này (§2), và AC5 đã bù. Test fixture `TestBackendOfflineEquivalence` dùng đường offline cũ
  (`canonicalize_hand_sequence` + `sequence_features_from_clip`), độc lập với `alphabet_clip_features`. Đây là điểm tốt.
- 6dd0202 không đụng `frontend/`. Trong phạm vi kế hoạch 03, `git diff 09d4057 HEAD -- frontend/` rỗng.

### detect-changes HIGH (7366274, 9be36e4): phạm vi
- Lệnh `node .gitnexus/run.cjs detect-changes --scope compare --base-ref 4fbc1a2`: 13 file (tính cả 3 CSV bị xóa của người dùng),
  17 luồng, risk critical (do số symbol). Mọi luồng mà CLI in ra đều là `Compose_fingerspelling -> ...` hoặc `Main -> ...` của
  `scripts/alphabet_ckpt_provenance.py`.
- `impact` upstream:
  - `PathBodyLimitMiddleware`, `_validation_error_handler`: **UNKNOWN**, vì chúng được đăng ký qua `app.add_middleware` và decorator,
    nên đồ thị không có cạnh gọi tới chúng.
  - `get_or_load_alphabet_model`: LOW (2 caller trực tiếp).
  - `class_kind`, `verdict_checks`, `external_reproduction`: LOW.
- Xác minh các UNKNOWN bằng text search trên toàn repo (trừ `clone/` và `docs/`):
  - `_is_body_limited` chỉ được gọi ở `backend/main.py:184` (middleware) và `:226` (handler);
  - `verdict_checks` chỉ có trong script và test;
  - `get_or_load_alphabet_model` chỉ có ở `backend/main.py:597, 628` và trong test.
- Hành vi runtime đã kiểm bằng thực nghiệm (mục 11):
  - middleware chỉ chặn 2 path;
  - WebSocket, lifespan và các path khác đi thẳng qua;
  - handler 422 chỉ đổi định dạng trên 2 path (`test_other_paths_keep_default_422_format`).

  Kết luận: phạm vi đúng như coder báo, chỉ gồm Cấp 1 và script provenance.

### Hai sai sót quy trình coder tự báo
- 1a471cb: commit message ghi "5 files", trong khi output thật của `detect-changes` là 4 file.
- 4145e51: commit message không ghi risk.
- Mức độ: **thấp**, không chặn. Không có mã nào bị ảnh hưởng, và cả hai đã được ghi công khai trong progress_log (dòng Lần sửa 1). Risk
  thật của 4145e51 (chỉ thêm test, 0 luồng) phù hợp với diff: thêm 84 dòng, xóa 0 dòng.

### Khác
- AC9:
  - 3 file của người dùng vẫn ở trạng thái " D", chưa staged;
  - diff không có file `.pt` hay `.npz`;
  - progress_log được THÊM dòng mới, dòng cũ không bị sửa.
- Status trả `trained_on.signers` (hauuto_hau, hauuto_khoi, ...). Đây là tên người ký, lấy từ đường dẫn của một dataset chưa rõ giấy
  phép. Xem mục CẦN NGƯỜI DÙNG.

## Việc phải sửa (CHANGES_REQUESTED), xếp theo mức độ

1. **[Triển khai, TRUNG BÌNH, bắt buộc]** `/sequence` trả 500 khi tọa độ là số hữu hạn nhưng lớn. Lỗi này vi phạm §3.2 và AC1-j.
   - Cách sửa tối thiểu, không đổi hợp đồng: sau `alphabet_clip_features`, nếu đặc trưng có giá trị không hữu hạn thì trả 422. Có thể
     kiểm thêm `probs` hữu hạn.
   - Thêm test, chỉ THÊM, vào `tests/test_fingerspelling_limits.py`:
     - tọa độ `3e38` → 422;
     - `frame_width=8192`, `frame_height=1`, tọa độ `1e35` → 422;
     - không ca nào ra 500.
2. **[Triển khai, THẤP]** Giới hạn độ dài phần input được trả lại trong 422 ngữ nghĩa, ví dụ cắt repr còn tối đa 40 ký tự. Chỗ cần sửa:
   `backend/main.py:576` và `src/inference/fingerspelling_compose.py:60,119`. Kèm test: khi token hoặc nhãn tay dài 500 KB, body 422
   phải có độ dài bị chặn.
3. **[Tài liệu, THẤP]** Sửa câu G5 trong kế hoạch và progress_log: `tests.test_ws_throughput` không có test tự động. Cần ghi bằng chứng
   thay thế (của review này), hoặc thêm một test tự động (xem mục CẦN PLANNER).

## CẦN PLANNER (thiết kế; không chặn APPROVE nếu đã sửa việc 1–2)
- **Cận cho tọa độ và bàn tay suy biến.** Có nên đặt cận cho giá trị tọa độ không, ví dụ |x|, |y|, |z| ≤ 10, vì MediaPipe chuẩn hóa về
  khoảng [0, 1]? Có nên trả 422 cho bàn tay suy biến (palm ≈ 0) không? Hiện các input này nhận 200 với confidence cao. Đây là thay đổi
  hợp đồng, nên cần AC mới.
- **Test tự động cho WebSocket/lifespan.** Cần một test tự động chứng minh WebSocket và lifespan đi thẳng qua `PathBodyLimitMiddleware`,
  ví dụ gọi ASGI trực tiếp như reviewer đã làm. Test này thay cho vai trò mà G5 gán nhầm cho `tests.test_ws_throughput`.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
1. **Chấp nhận tiêu chí danh tính V1–V6 (Lần sửa 1).**
   - Tiêu chí này được sửa sau khi đã thấy kết quả. Reviewer đánh giá là không nới về bản chất (mục 12).
   - Tuy vậy, file triển khai đã bị đóng gói lại, và không rõ ai làm hay làm lúc nào. Theo mtime, file được tạo lúc 2026-09-25 15:14:
     10 phút trước commit 6dd0202, và trước file variants.
   - Nếu người dùng nhận ra đây là thao tác của mình trong phiên đó, xin ghi lại một câu vào progress_log.
2. **Lưu trữ bằng chứng provenance.**
   - Ba file `reports/alphabet_nested_2026-09-25/primary/alphabet_nested_final.pt`, `.../variants/alphabet_nested_final.pt` và
     `primary/nested_predictions.csv` đều bị gitignore và chỉ có trên máy này.
   - Nếu mất chúng thì không tính lại được V1/V3/V6, và verdict sẽ thành UNKNOWN.
   - Có nên đưa chúng vào dataset Kaggle private, như đã làm ở kế hoạch 02? Giấy phép hauuto chưa rõ, nên chỉ được để private.
3. **API công khai trả `trained_on.signers`.** Status hiện trả tên người ký của hauuto (giấy phép chưa rõ). Giữ nguyên, hay chỉ trả
   `source` và số lượng?
4. **CORS mở toàn bộ kèm credentials, và WebSocket không giới hạn kích thước message.**
   - Cả hai có từ trước, và kế hoạch để sang Việc 5.
   - Xin xác nhận thứ tự ưu tiên: mục 11 của reviewer sẽ FAIL với mọi cấu hình production còn giữ hai điểm này.
5. **(Có từ trước) `alphabet_real_best.pt` đã được commit công khai.** Vẫn chờ người dùng quyết định (A3).
