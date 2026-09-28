# Kế hoạch 03: Việc 4, endpoint chuỗi landmark cho Cấp 1 "Đánh vần" (chỉ backend/)

> **Điểm dừng: KHÔNG có điểm dừng trước khi code, kể cả sau Lần sửa 2.**
>
> Review vòng 1 (`docs/reviews/03-review.md`) có mục "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH" gồm 5 câu hỏi:
> - chấp nhận V1–V6;
> - lưu trữ bằng chứng provenance;
> - `trained_on.signers` trong status;
> - CORS và giới hạn WebSocket;
> - `alphabet_real_best.pt`.
>
> Orchestrator chuyển các câu hỏi này cho người dùng. Chúng KHÔNG chặn Lần sửa 2, và việc này KHÔNG đụng tới chúng.
>
> Các ràng buộc giữ nguyên:
> - Không đổi model mặc định. Không sửa, thay hay chép checkpoint. Không đổi giá trị mặc định `VSL_ALPHABET_CKPT`.
> - Không đụng `frontend/`.
> - Không `git add -A` và không `git add .` (có 3 file bị xóa chưa commit của người dùng).
> - Không sửa CORS. Không thêm giới hạn cho WebSocket. Không đổi `trained_on.signers`.

Nhánh `feat/vslt-complete`.
- Lập kế hoạch lần đầu tại HEAD `09d4057` (2026-09-27); commit kế hoạch ở `f903980`.
- Lần sửa 1: ngày 2026-09-28, sau khi coder trả "CẦN PLANNER"; commit ở `9be36e4`.
- Lần sửa 2: ngày 2026-09-28, sau review vòng 1/3 kết luận CHANGES_REQUESTED, tại HEAD `9f4eb68`.

---

## 0'. Lần sửa 2 (sau review vòng 1, CHANGES_REQUESTED: FAIL mục 11)

Các commit đã có giữ nguyên. Không viết lại lịch sử. Mọi thay đổi đều là commit MỚI trên `9f4eb68`.

### 0'.1 Nguyên nhân gốc
**FAIL mục 11: `/sequence` trả 500 khi tọa độ là số hữu hạn nhưng rất lớn.**

Chuỗi lỗi:
1. Tọa độ 3e38 vẫn hữu hạn trong float32, nên qua được kiểm tra `isfinite` ở `backend/main.py:555-564`.
2. Phép nhân aspect ratio ở `src/data/alphabet_preprocessing.py:203` làm số này tràn thành inf.
3. Phép chia cho độ dài lòng bàn tay (`:53`) biến inf thành NaN.
4. Softmax ra NaN, và `JSONResponse` từ chối serialize NaN, nên server trả 500.

Nguyên nhân gốc nằm ở thiết kế, cả trong kế hoạch lẫn trong code:
- Kế hoạch §3.2 chỉ kiểm tra **đầu vào** (số hữu hạn), rồi coi mọi thứ phía sau là an toàn.
- Hợp đồng không có (a) cận giá trị cho tọa độ, và không có (b) bước kiểm tra **đầu ra trung gian**: đặc trưng và xác
  suất.
- Vì vậy hai tính chất mà hợp đồng hứa ("không bao giờ trả 500 cho input xấu", "không kết quả giả") phụ thuộc vào việc
  phép tính số học không tràn. Kế hoạch không kiểm chứng điều đó.
- Test quét AC1-j chỉ có `1e300`. Số này tràn ngay khi ép sang float32, nên bị chặn ở bước đầu. Test không có ca nào
  hữu hạn mà vẫn lớn, nên không lộ ra lỗi.

**Mức thấp: 422 ngữ nghĩa trả lại input của client mà không giới hạn độ dài.** Lý do G1 đưa ra ("không trả lại input")
chỉ được áp cho lỗi schema, chưa áp cho các thông điệp tự viết. Các chỗ đang lộ input:
- `backend/main.py:576`: `got {bad[:5]}`;
- `src/inference/fingerspelling_compose.py:60,119`: dùng `{token!r}`.

**Tài liệu: hai câu nói quá bằng chứng.**
- §0.3 G5 lấy `tests.test_ws_throughput` làm bằng chứng. Module này có **0 test tự động**: nó là script thủ công và cần
  server thật chạy.
- Docstring của `largest_valid_payload` (`tests/test_fingerspelling_limits.py:77-80`) ghi "as long as floats can make
  it". Câu này không đúng: repr với số mũ `e-300` dài hơn. Kết luận "< 1 MiB" vẫn đúng theo đo của reviewer.

### 0'.2 Quyết định cho hai câu hỏi reviewer chuyển sang planner

**(a) Cận tọa độ + bàn tay suy biến: CÓ, cả hai.** Đây là THAY ĐỔI HỢP ĐỒNG (§3.2), có AC mới là AC12.
- **Cận:** mọi tọa độ thô (trước khi nhân aspect) phải thỏa `|x|, |y|, |z| ≤ ALPHABET_MAX_ABS_COORD = 10.0`. Nếu vi
  phạm → 422, thông điệp nêu chỉ số khung.
  - Lý do: MediaPipe trả x, y chuẩn hóa theo khung hình, còn z cùng thang với x. Giá trị thật nằm quanh [0, 1], và vượt ra
    ngoài một chút khi tay chạm mép khung. Cận 10 rộng gấp nhiều lần mức đó.
  - Cận này chặn cả lớp lỗi tràn số ngay ở biên. Với aspect ≤ 8192 thì |x · aspect| ≤ 81 920, nên không thể tràn
    float32.
  - Cận KHÔNG được làm mất dữ liệu thật. AC12-d buộc chạy toàn bộ khung có tay của manifest thật (686 clip) qua đúng
    hàm kiểm tra, và yêu cầu 0 vi phạm.
- **Bàn tay suy biến:** khung có tay mà 21 điểm TRÙNG HỆT nhau (`(arr == arr[0]).all()` trên float32 sau khi parse) → 422.
  Trường hợp này bao gồm khung toàn số 0.
  - Lý do 1: nó không bao giờ là output của MediaPipe. Khi không có tay, MediaPipe không trả điểm nào, và hợp đồng quy
    định gửi `null` hoặc `[]`.
  - Lý do 2: nó làm lệch train/realtime. Hiện nay backend coi khung toàn số 0 là "có tay" (`detected[t] = True`), trong
    khi dữ liệu train đánh dấu các khung đó là không có tay (`detected_mask = False`).
  - Lý do 3: hiện input này nhận 200 với confidence cao (reviewer đo được 0.8566). Đó là dự đoán trên dữ liệu không phải
    bàn tay, ngược với tinh thần DoD 6.
  - Chỉ dùng tiêu chí trùng HỆT, KHÔNG dùng ngưỡng gần 0, để không có nguy cơ loại nhầm bàn tay thật (AC12-d kiểm trên dữ
    liệu thật). Các input gần suy biến (có nhiễu rất nhỏ) vẫn nhận 200.
- **Giới hạn ghi rõ:** server không thể chứng minh landmark đến từ một bàn tay thật. Cả hai kiểm tra chỉ loại input vô
  nghĩa rõ ràng, không phải cơ chế chống giả mạo. `confidence` không phải bằng chứng rằng input là bàn tay.
- Không vỡ test cũ: tôi đã grep `tests/`. Mọi payload có 21 điểm giống nhau đều đang được kỳ vọng 422 (`test_fingerspelling_limits.py:245-248, 294-295, 305`).
  Các fixture được kỳ vọng 200 (`hand_clip`, `make_clip`, `largest_valid_payload`) có các điểm khác nhau, và tọa độ đều
  ≤ 10. Clip thật gửi `null` cho khung không có tay (`tests/test_fingerspelling_deployed.py:101`,
  `tests/test_fingerspelling_api.py:52`). Nếu vẫn có test cũ vỡ → DỪNG và báo planner. KHÔNG sửa test cũ.

**(b) Test tự động cho WebSocket và lifespan: CÓ** (AC14). Test gọi ASGI trực tiếp trên `PathBodyLimitMiddleware` với
`max_bytes` nhỏ và một app giả để ghi lại lời gọi. Cách này giống thực nghiệm của reviewer. Test không mở WebSocket thật
tới `/ws/live-stream`, vì làm vậy phải nạp model Cấp 2. Test này thay vai trò mà G5 đã gán nhầm cho
`tests.test_ws_throughput`.

**Mã lỗi khi model trả xác suất không hữu hạn:** 503, không phải 422. Nếu đặc trưng hữu hạn mà xác suất không hữu hạn thì
lỗi nằm ở model, không phải ở input. Body là JSON hợp lệ, không chứa NaN, và server ghi log lỗi (AC11-b).

### 0'.3 Thay đổi so với Lần sửa 1
- §0.3: sửa hàng G5.
- §3.2: thêm các mục sau vào hợp đồng:
  - cận tọa độ;
  - quy tắc bàn tay suy biến;
  - kiểm tra đặc trưng và xác suất hữu hạn;
  - cắt ngắn phần input trả lại trong thông điệp lỗi.
- §4: thêm các bước R5–R9.
- §5: thêm AC11–AC15. AC8 thêm một ngoại lệ đã nêu rõ cho docstring (AC15-a). Không bỏ hay nới tiêu chí nào.
- §6: thêm giới hạn "server không chứng minh được input là bàn tay".

---

## 0. Lần sửa 1 (sau khi Bước 0 cho `UNKNOWN_PROVENANCE`; coder trả "CẦN PLANNER")

Commit của coder giữ nguyên: `f903980`, `7366274`, `1713f8d`.

### 0.1 Nguyên nhân gốc
Tiêu chí danh tính cũ ở Bước 0 là: sha256 của FILE trùng một checkpoint đã biết, VÀ `trained_on.source == "hauuto"`.
Đây là lỗi của kế hoạch. sha256 của file chỉ là một đại diện cho câu hỏi thật. Đại diện này hỏng ngay khi checkpoint được
đóng gói lại (thêm hoặc bớt khóa metadata làm đổi byte), dù trọng số và các trường ảnh hưởng suy luận vẫn giữ nguyên.

Bằng chứng (`reports/alphabet_deploy_2026-09-27/provenance.json`, sinh tại HEAD `4fbc1a2`):
- sha256 của file triển khai khác cả 3 checkpoint đã biết;
- `state_dict_equal` là true với nested_primary và nested_variants;
- file triển khai có thêm khóa `licence_note` và `evaluation`;
- tái lập 46/46.

Ai đóng gói lại và vào lúc nào thì không truy được (xem §6).

### 0.2 Tiêu chí mới cho Bước 0: V1–V6, KHÔNG nới về bản chất
`verdict = "real_data_known_checkpoint"` khi và chỉ khi TẤT CẢ các điều kiện sau đúng. Nếu có điều kiện sai hoặc không
tính được → `UNKNOWN_PROVENANCE`.
- **V1:** tập M ≠ ∅. M gồm các checkpoint trong {nested_primary, nested_variants} có state_dict bằng bit-từng-bit với file
  triển khai (cùng thứ tự khóa, cùng shape, cùng dtype, `torch.equal`). `real_run` không tính.
- **V2:** với mọi K ∈ M và mọi trường trong `{model_type, classes, selected, hparams, input_dim, num_classes, epochs,
  preprocessing, trained_on}` mà K có, file triển khai phải có trường đó với giá trị bằng nhau. `classes` so cả thứ tự.
- **V3:** có ít nhất một K ∈ M có CẢ `preprocessing` lẫn `trained_on`.
- **V4:** `preprocessing == preprocessing_for(selected[2])`.
- **V5:** `trained_on.source == "hauuto"`.
- **V6:** `external_reproduction` tính được, `n == clips_in_csv > 0` và `k == n`.

Vì sao không phải là nới tiêu chí:
- V1, V2 và V4 kiểm trực tiếp hành vi suy luận.
- Tiêu chí mới chặt hơn ở 3 chỗ: loại `real_run`, bắt buộc V4, bắt buộc V6.
- Chỉ các khóa không dùng khi suy luận được phép khác. Bù lại có ba ràng buộc:
  - `metadata_diff` chỉ ghi tên và kiểu của khóa, không ghi giá trị;
  - AC4-f;
  - AC5-a ghim sha256 của file.
- Tiêu chí được sửa sau khi đã thấy kết quả, và kế hoạch ghi công khai điều này. Đây là tiêu chí danh tính, không phải
  GATE chất lượng.

Reviewer vòng 1 đánh giá: không nới về bản chất (mục 12).

### 0.3 Xem xét giả định của coder
| # | Giả định | Quyết định | Điều kiện |
|---|---|---|---|
| G1 | Handler 422 riêng cho `/sequence` và `/compose`, chỉ trả `loc/msg/type` | CHẤP NHẬN | Nếu dùng handler mặc định, NaN sẽ bị trả lại → 500. Hợp đồng §3.2 ghi hai dạng body 422. Lần sửa 2 mở rộng nguyên tắc "không trả lại input dài" sang thông điệp ngữ nghĩa (AC13) |
| G2 | Trường `compose_endpoint` trong status | CHẤP NHẬN | AC4-g |
| G3 | `kind = null` cho lớp ngoài bộ từ | CHẤP NHẬN | AC4-h; checkpoint triển khai không được có null (AC5-h) |
| G4a–e | Chi tiết luật compose | CHẤP NHẬN | AC3-f |
| G5 | `detect-changes` risk HIGH ở `7366274`: 7 luồng, đều thuộc Cấp 1 | Ghi nhận, không chặn | **(Sửa ở Lần sửa 2.)** Câu trước đây ghi "có bằng chứng từ `tests.test_ws_throughput`" là SAI: module này có 0 test tự động, và AC8 không chứng minh được gì về WebSocket. Bằng chứng hiện có là thực nghiệm của reviewer (`docs/reviews/03-review.md` mục 11 và mục 13). Bằng chứng tự động là AC14 (thêm ở Lần sửa 2). Các path HTTP khác đi thẳng qua middleware, có test `test_other_paths_are_not_limited` |

---

## 1. Mục tiêu và DoD

**Mục tiêu.** Backend đã có endpoint chuỗi landmark (`6dd0202`). Việc này kiểm chứng phần đã có, bổ sung phần còn thiếu,
viết test tương đương cho đúng checkpoint đang nạp, và đưa qua vslt-reviewer.

**DoD phục vụ.**
- DoD 2 (phía backend).
- DoD 6: không có kết quả giả.
- DoD 7: unit test + contract test + test tương đương.
- Mục 11 của reviewer: input được kiểm tra.

---

## 2. Hiện trạng (HEAD `09d4057`, trước khi coder làm)

Bảng đối chiếu chi tiết nằm ở bản `f903980` của file này. Tóm tắt những gì đã có từ `6dd0202`:
- endpoint `/sequence`;
- endpoint ảnh trả 409;
- 422 và 503;
- `alphabet_clip_features` dùng chung cho train và realtime.

Những gì còn thiếu:
- giới hạn kích thước request;
- ghép chữ thành từ;
- nguồn gốc model;
- khóa khi nạp model;
- test tương đương cho checkpoint đang triển khai;
- danh tính của checkpoint đang nạp.

Tất cả đã xử lý ở `7366274` … `9f4eb68`, trừ các lỗi review vòng 1 nêu ở §0'.

CORS và WebSocket không giới hạn kích thước message là lỗi có từ trước. Phần này ngoài phạm vi (§8) và đang chờ người
dùng.

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu (Cấp 1)
```
[Việc 5, frontend] webcam (KHÔNG lật gương) → MediaPipe Hands → cắt 1 ký hiệu
   → POST /api/fingerspelling/sequence {landmarks[T] (null khi không có tay), handedness[T], timestamps_ms[T]?, frame_width, frame_height}
[backend] giới hạn body (413) → pydantic (422) → parse_fingerspelling_sequence (422: shape, hữu hạn, |v| ≤ 10, không suy biến)
   → alphabet_clip_features(..., preprocessing = checkpoint["preprocessing"])  → đặc trưng hữu hạn? (không → 422)
   → model → xác suất hữu hạn? (không → 503) → top-k {class, confidence, kind} + prediction_kind
[Việc 5] danh sách token → POST /api/fingerspelling/compose {tokens} → {text, syllables, warnings, tone_style}
```
Backend không giữ trạng thái. Frontend (Việc 5) lo: MediaPipe, cắt ký hiệu, giữ danh sách token, UI, và gọi `/compose`.

### 3.2 Hợp đồng `POST /api/fingerspelling/sequence`
**Input.**
- `landmarks`: 1..300 phần tử. Mỗi phần tử là:
  - `null` hoặc `[]` khi không có tay; hoặc
  - đúng 21 × [x, y, z], các số hữu hạn, **|v| ≤ `ALPHABET_MAX_ABS_COORD` (=10.0)** (Lần sửa 2), và **21 điểm không
    được trùng hệt nhau** (Lần sửa 2). Khung toàn số 0 KHÔNG được dùng để biểu thị "không có tay".
- `handedness`: T phần tử thuộc {"Left","Right",""}.
- `timestamps_ms`: T số hữu hạn, không giảm.
- `frame_width`, `frame_height`: 1..8192.
- `source_mirrored`: bool.
- `top_k`: 1..10.

**Output 200.** Các trường cũ, cộng thêm:
- `prediction_kind`;
- `candidates[i].kind`, giá trị ∈ {"letter","tone",null}. Chỉ trả `null` cho lớp nằm ngoài bộ từ Cấp 1.

**Mã lỗi.**
- **413**: body > 1_048_576 byte. Áp cho cả Content-Length và chunked. Chỉ áp cho 2 path.
- **422**:
  - Lỗi schema có dạng `{"detail":[{loc,msg,type}]}`.
  - Lỗi ngữ nghĩa có dạng `{"detail": str}`. **Phần input của client được trích lại trong thông điệp chỉ gồm tối đa 40 ký
    tự repr, cắt đuôi bằng "…"** (Lần sửa 2).
  - Các ca 422 của Lần sửa 2:
    - tọa độ vượt cận;
    - khung suy biến;
    - **đặc trưng sau `alphabet_clip_features` có giá trị không hữu hạn**.
- **503**:
  - không có checkpoint hợp lệ;
  - **model trả xác suất không hữu hạn** (Lần sửa 2; body không có NaN; server ghi log lỗi).
- Không bao giờ trả 500 cho input xấu.

### 3.3 `POST /api/fingerspelling/compose` + module thuần
Giữ như Lần sửa 1: các quy tắc 1–5, `tone_style: "traditional"`, tối đa 200 token.

Lần sửa 2 thêm: thông điệp `ValueError` của `token_kind` và `compose` chỉ trích tối đa 40 ký tự repr của token. Vị trí
`tokens[i]` vẫn giữ nguyên.

### 3.4 Status
Giữ như Lần sửa 1:
- `trained_on`;
- `data_provenance`;
- `evaluation_report`;
- `compose_endpoint`;
- không đọc các khóa `evaluation` và `licence_note`.

Việc có đổi `trained_on.signers` hay không là câu hỏi cho người dùng. Lần sửa này không đụng.

### 3.5 Nạp model
Giữ như cũ: có khóa, và nạp lại khi lỗi.

---

## 4. Chia việc

Đã làm: Bước 0–6 và R1–R4 (`f903980` … `9f4eb68`). Việc còn lại là Lần sửa 2.

Trước khi sửa, chạy GitNexus `impact` (upstream) cho các symbol: `parse_fingerspelling_sequence`,
`predict_fingerspelling_sequence`, `token_kind`, `compose`, `PathBodyLimitMiddleware`. Với kết quả UNKNOWN, xác nhận lại
bằng text search. Chạy `detect-changes --scope all` trước MỖI commit, và ghi risk vào commit message.

**R5 (bắt buộc, ≤ 1 giờ): kiểm tra đặc trưng và xác suất hữu hạn.**
- Trong `predict_fingerspelling_sequence`:
  - đặc trưng không hữu hạn → 422;
  - xác suất không hữu hạn → 503 và ghi log.
- Test: AC11.

**R6 (≤ 1.5 giờ): cận tọa độ + khung suy biến.**
- Làm trong `parse_fingerspelling_sequence`.
- Thêm hằng `ALPHABET_MAX_ABS_COORD`.
- Test: AC12. Trong đó AC12-d chạy trên dữ liệu thật.

**R7 (≤ 0.5 giờ): cắt ngắn input trả lại.**
- Viết một hàm tiện ích dùng chung, ví dụ `short_repr(v, limit=40)` trong `src/inference/fingerspelling_compose.py`, và
  import vào backend.
- Áp dụng ở `backend/main.py:576` và `src/inference/fingerspelling_compose.py:60,119`.
- Test: AC13.

**R8 (≤ 0.5 giờ): test ASGI cho middleware.** Test: AC14.

**R9 (≤ 1 giờ): tài liệu và chốt.**
- AC15.
- AC8.
- progress_log: THÊM một dòng mới (AC9), ghi cả phần sửa G5.
- Chạy lại vslt-reviewer (vòng 2).

Test mới được đặt như sau:
- AC11, AC12-a..c, AC13-b, AC14 → `tests/test_fingerspelling_limits.py`;
- AC13-a, c, d → `tests/test_fingerspelling_compose.py`;
- AC11-c (bản chạy với checkpoint triển khai) và AC12-d → `tests/test_fingerspelling_deployed.py`.

Chỉ THÊM test, trừ ngoại lệ docstring ở AC15-a.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; coder KHÔNG được đổi)

Môi trường: `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`. Ghi output thật của mọi lệnh.

**AC0'** (V1–V6), **AC0b** (a–k), **AC1** (a–j), **AC2**, **AC3** (a–f), **AC4** (a–h), **AC5** (a–h + verdict),
**AC6**, **AC7**: GIỮ NGUYÊN như Lần sửa 1 (bản `9be36e4` của file này). Các test hiện có của những AC này phải tiếp
tục pass mà không bị sửa.

**AC11 (Lần sửa 2, bắt buộc): đặc trưng và xác suất hữu hạn.**
- a. Dùng `mock.patch` để `src.data.alphabet_preprocessing.alphabet_clip_features` trả về một mảng đúng shape nhưng có
  NaN; chạy lại với inf. Kỳ vọng: `/sequence` → 422, body là JSON hợp lệ và không có chuỗi `NaN`/`Infinity`. Test này
  kiểm tra riêng bước kiểm hữu hạn, độc lập với cận tọa độ.
- b. Fixture checkpoint có một trọng số là NaN. Với input hợp lệ, `/sequence` → 503, body là JSON hợp lệ, không có
  `NaN`, và `detail` nói rõ đầu ra model không hợp lệ.
- c. Payload của reviewer: 10 khung, mỗi khung 21 điểm `[3e38*(i%2), -3e38*(i%3==0), 1.0]`. Kỳ vọng 422, chạy với
  fixture checkpoint (luôn chạy). Chạy thêm một lần với checkpoint triển khai trong `tests/test_fingerspelling_deployed.py`
  (skipUnless; trên máy này bắt buộc chạy).
- d. `frame_width=8192`, `frame_height=1`, tọa độ `1e35` → 422.
- e. Một hàm quét MỚI; không sửa `test_no_500_on_bad_input`. Kỳ vọng:
  - các ca `3e38`, `-3e38`, `3.4e38`, `1e35` với 8192:1, và `10.000001` → đều 422;
  - ca tọa độ dưới chuẩn (`1e-45`, các điểm khác nhau) → mã ∈ {200, 422};
  - KHÔNG ca nào trả 500.

**AC12 (Lần sửa 2, thay đổi hợp đồng): cận tọa độ + khung suy biến.**
- a. `api.ALPHABET_MAX_ABS_COORD == 10.0`.
- b. Cận có tính cả dấu bằng:
  - một điểm có x = 10.0 (các điểm khác khác nhau) → 200;
  - x = 10.000001 → 422; tương tự cho y và z, và cho giá trị âm;
  - thông điệp nêu chỉ số khung.
- c. Khung suy biến:
  - khung có 21 điểm `[0.5, 0.5, 0.0]` → 422;
  - khung toàn 0 → 422, và thông điệp nhắc dùng `null`;
  - khung có 20 điểm trùng nhau và 1 điểm khác → KHÔNG bị luật này chặn (200).
- d. Dữ liệu thật (skipUnless manifest; trên máy này bắt buộc chạy, 0 skip):
  - duyệt mọi clip trong `manifest.csv` (cả hauuto lẫn qipedc) và mọi khung có `detected_mask` true;
  - gọi đúng hàm kiểm tra mà backend dùng (đưa phần kiểm tra khung ra thành một hàm module-level để test gọi được);
  - kỳ vọng: số khung vi phạm cận = 0, và số khung suy biến = 0;
  - test in ra số clip và số khung đã kiểm (lấy từ output, không gõ tay).
- e. Toàn bộ test cũ vẫn pass mà không bị sửa. Riêng AC5 (106 clip thật) vẫn cho kết quả giống hệt.

**AC13 (Lần sửa 2, mức thấp): không trả lại input dài.**
- a. `/compose` với một token dài 500 KB → 422, `len(r.content) ≤ 1024`, thông điệp vẫn chứa `tokens[0]`.
- b. `/sequence` với 2 nhãn `handedness`, mỗi nhãn 400 KB (và T tương ứng) → 422, `len(r.content) ≤ 1024`.
- c. Unit test: `token_kind("x" * 500_000)` ném `ValueError` với thông điệp ≤ 200 ký tự.
- d. Token ngắn, ví dụ `"x1"`: thông điệp vẫn chứa nguyên `'x1'`. Các test cũ về thông điệp có vị trí vẫn pass.

**AC14 (Lần sửa 2): middleware để WebSocket, lifespan và các path khác đi thẳng qua.**
Test gọi ASGI trực tiếp trên `PathBodyLimitMiddleware(inner, max_bytes=10)`, với `inner` là app giả ghi lại
`(scope, receive)` và gửi 200.
- a. `scope["type"] == "websocket"` với path `/ws/live-stream`, và với path `/api/fingerspelling/sequence`:
  - `inner` được gọi đúng 1 lần, nhận ĐÚNG object `receive` gốc (so bằng `is`);
  - middleware không tự gửi message nào.
- b. `scope["type"] == "lifespan"`: kết quả giống (a).
- c. HTTP `POST /api/translate` với body 100 byte: `inner` được gọi và đọc được đủ 100 byte.
- d. HTTP `POST /api/fingerspelling/compose` với body 11 byte (chunked, không có Content-Length): nhận 413, và `inner`
  KHÔNG được gọi.
- e. `api.app.user_middleware` chứa `PathBodyLimitMiddleware` với `max_bytes == ALPHABET_MAX_BODY_BYTES`.

**AC15 (Lần sửa 2): tài liệu.**
- a. Sửa docstring của `largest_valid_payload` (`tests/test_fingerspelling_limits.py:77-80`): bỏ câu "as long as
  floats can make it". Thay bằng mô tả đúng: mỗi tọa độ có 17 chữ số có nghĩa và có số mũ; đây KHÔNG phải repr dài
  nhất có thể có; xem AC15-b.
  **Đây là ngoại lệ duy nhất được phép sửa dòng cũ trong `tests/`.** Chỉ đổi docstring, không đổi dòng code nào của
  test. Reviewer kiểm bằng `git diff 9f4eb68 HEAD -- tests/`: mọi dòng bị xóa phải nằm trong docstring này.
- b. Test MỚI chỉ đo kích thước (không POST): payload có T=300, mọi số là `-1.2345678901234567e-300`, kèm handedness và
  timestamps cùng dạng. Kỳ vọng `len(json.dumps(...).encode()) < ALPHABET_MAX_BODY_BYTES`. Như vậy bằng chứng cho giới
  hạn 1 MiB không còn phụ thuộc vào docstring.
- c. Dòng progress_log MỚI ghi rõ: `tests.test_ws_throughput` có 0 test tự động; bằng chứng WebSocket đi thẳng qua là
  AC14 cùng thực nghiệm của reviewer; câu G5 trong kế hoạch đã sửa ở Lần sửa 2.

**AC8: hồi quy.**
- Chạy cùng lệnh 14 module như Lần sửa 1. Kỳ vọng 0 failure, 0 error.
- Báo số test theo từng module và số skip (kèm lý do). Ghi rõ `tests.test_ws_throughput` = 0 test.
- `git diff 09d4057 HEAD -- tests/test_fingerspelling_api.py tests/test_alphabet_preprocessing.py` phải RỖNG.
- `git diff 9f4eb68 HEAD -- tests/`: chỉ có dòng THÊM. Ngoại lệ duy nhất là docstring ở AC15-a.

**AC9: quy trình.**
- Có output `impact` và `detect-changes --scope all` cho mỗi commit.
- 3 file của người dùng vẫn ở trạng thái " D", chưa staged.
- Không có file `.pt` hay `.npz` trong diff.
- progress_log: THÊM một dòng mới, không sửa dòng cũ.
- `docs/reviews/03-review.md` (vòng 2) kết luận APPROVE.

---

## 6. Rủi ro dữ liệu / ML
- **Nguồn gốc model:** AC0' đạt (V1–V6), reviewer đã kiểm lại.
  - Mọi bằng chứng cho V1/V3/V6 đều bị gitignore và chỉ có trên máy này. Có lưu trữ chúng hay không là câu hỏi cho
    người dùng.
- **Đóng gói lại mà không truy được:** hai khóa `licence_note` và `evaluation` không được dùng làm số liệu ở bất kỳ đâu.
  Ghi điểm này vào mục "Giới hạn" (DoD 9).
- **Giấy phép hauuto:** unknown, chỉ dùng nội bộ. Status trả tên người ký; đây là câu hỏi cho người dùng.
- **Server không chứng minh được input là bàn tay** (Lần sửa 2).
  - Cận tọa độ và luật khung suy biến chỉ loại input vô nghĩa rõ ràng.
  - Input gần suy biến, hoặc tọa độ bịa nhưng hợp lý, vẫn nhận 200.
  - `confidence` không được trình bày như bằng chứng. Ghi vào mục "Giới hạn".
- **Lệch train/realtime (ngoài backend):** dữ liệu train được trích bằng MediaPipe Python, còn client (Việc 5) có thể
  dùng MediaPipe JS. Việc 5 phải có test tương đương cho client.
  - Lần sửa 2 còn xóa một lệch nhỏ: trước đây khung toàn 0 được coi là "có tay", nay bị 422.
- **Cỡ mẫu:** 4 người ký. Dấu thanh có CI rộng. Không đưa số liệu nào vào API.
- **Rò rỉ:** không có. Việc này không train và không đo độ chính xác.

## 7. Điểm dừng
- Lần sửa 2 không có điểm dừng.
- Nếu R6 làm vỡ một test cũ, hoặc AC12-d thấy vi phạm trên dữ liệu thật → DỪNG và báo planner. Khi đó KHÔNG được nới cận
  hay đổi luật ngay tại chỗ.
- Các câu hỏi CẦN NGƯỜI DÙNG của review vòng 1 không chặn việc này.

## 8. Ngoài phạm vi
- Việc 5:
  - `Fingerspelling.jsx`;
  - cắt ký hiệu;
  - MediaPipe phía client và test tương đương cho client;
  - xử lý hai dạng body 422;
  - gửi `null` cho khung không có tay.
- Chờ người dùng quyết định (review vòng 1):
  - CORS;
  - giới hạn kích thước message WebSocket;
  - `trained_on.signers`;
  - lưu trữ bằng chứng provenance;
  - `alphabet_real_best.pt`.
- DoD 8: Cấp 1 dùng REST, không dùng WebSocket.
- Kiểu đặt dấu: dùng kiểu cũ.
