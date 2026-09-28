# Review 04 — nối harmonize() vào đường live "Ký từ" (Cấp 2)

**TRẠNG THÁI: HOÀN TẤT — KẾT LUẬN: APPROVE** (không mục nào FAIL; còn việc theo sau không chặn, xem cuối file)

- Kế hoạch: `docs/plans/04-harmonize-duong-live.md`
- Phạm vi: 8bba04e → af6d384 (0f07585, 9c894da, 4c9e24c, 5627010, b1d447a, 2807a8a, af6d384).
  HEAD lúc kết thúc review là d329801 (d4a3856 + d329801 chỉ thêm tài liệu giao thức: CLAUDE.md, docs/STATE.md,
  docs/prompts/*; ngoài phạm vi; `git diff --stat af6d384 HEAD -- src backend scripts tests` rỗng).
- Môi trường: Windows / Git Bash, `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`.

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch / test thật | PASS (2 điểm yếu nhỏ) | Mỗi AC có test tương ứng, tôi đọc từng test: AC1 a–o = 15 test (`tests/test_sign_segmenter.py`), AC2 a–f + 2 = 10 test (`tests/test_harmonized_live.py`), AC3 a–i + AC7 a–e = 18 test (`tests/test_ws_live_contract.py`), AC4 (1)–(5) + AC5 + AC6 = 8 test (`tests/test_live_harmonized_equivalence.py`). Các assert thật sự kiểm điều AC nói (ví dụ AC3-f spy `cv2.imdecode` không được gọi; AC3-b `VSLPredictor` là MagicMock phải không được gọi; AC4-(2) wrapper quanh `holistic.process` thật; AC2-f thay `perf_counter` bằng dãy biết trước). AC0 tôi tự làm lại: diff c65032a rỗng, mediapipe 0.10.14 / cv2 5.0.0 / numpy 2.4.6, sha256 khớp, dict `preprocessing` đúng (`features=harmonized_v1, process_height=360, trim=True, hand_z=True, target_len=32, extractor=CleanHolisticExtractor, mediapipe_version=0.10.14`), 3 file " D" chưa staged. AC9: impact/detect-changes có trong message từng commit. **Điểm yếu:** (a) AC5 `test_ws_matches_in_process_session` không assert có ≥ 1 event — nếu cả hai bên đều 0 event thì PASS rỗng (`tests/test_live_harmonized_equivalence.py:276-277`); lần chạy của tôi có event thật (W03251B: 2 `sign_result`, D0120T: 1). (b) "checkpoint có `features` lạ → model không dùng được" chỉ được test ở mức `live_pipeline_for` (AC2-a), không có test backend (health 503 / WS 1011) cho ca này — tôi tự thử in-memory thì đúng (mục 11). |
| 2 | Tự chạy lại toàn bộ test | PASS | Lệnh AC8 đầy đủ (19 module) chạy tại `af6d384` (HEAD lúc bắt đầu; d4a3856 sau đó chỉ thêm tài liệu): `Ran 310 tests in 738.961s` / `OK` / EXIT=0, không có `(skipped=…)` → 0 skip; AC4/AC5/AC6 đều chạy. Khớp coder báo (310 OK, 0 skip). Output in từ test: `[AC4] max|d sequence| per clip` = 0.0 cả 8 clip; `[AC4] max|d confidence| over 8 clips x top-5: 0.0`; `[AC3-e] ... = 481261 bytes (limit 1048576)`; `[AC5] qipedc_W03251B ... WS events [('sign_result', None, 'thìa'), ('sign_result', None, 'thìa')]`, `qipedc_D0120T ... [('sign_result', None, 'phải không?')]`. Thêm: `scripts/smoke_test_phase10.py` PASS (module legacy + `__init__` lazy). **`scripts/smoke_test_phase12.py` HỎNG** ở bước [2/5]: `KeyError: 'gloss'` (message đầu là `session_info`) — script không thuộc AC8, xem S2. |
| 3 | Test cũ không bị sửa/skip/nới | PASS | `git diff --name-status 8bba04e af6d384 -- tests/` → chỉ 4 dòng `A` (test_harmonized_live, test_live_harmonized_equivalence, test_sign_segmenter, test_ws_live_contract). `git diff --stat 9f4eb68 af6d384 -- tests/test_harmonized.py tests/test_realtime.py` rỗng. Fixture segmenter "đổi" trước commit đầu (file mới ở 0f07585) — xem S3.5. |
| 4 | Nguồn gốc dữ liệu | PASS | Không train/đánh giá độ chính xác. AC4/AC5/AC6 dùng video QIPEDC thật (`data/Dataset/Videos`, chỉ đọc) + MediaPipe 0.10.14 thật + checkpoint thật (sha256 `648a7825…c9b59e`, tôi tự `sha256sum` khớp). Landmark sinh trong AC1/AC2/AC3 là fixture kiểm logic, ghi rõ trong docstring (`tests/test_sign_segmenter.py:1-8`), không dùng làm dữ liệu. Ảnh nhiễu `default_rng(0)` chỉ để đo kích thước message (`tests/test_ws_live_contract.py:345`). Không commit video/npz/frame: `git diff --name-only 8bba04e af6d384` chỉ có 1 file dữ liệu là `segment_check.json` (id + số, test `TestSegmentCheckJson` cấm khóa keypoints/landmarks/coords/visibility). |
| 5 | Rò rỉ | PASS (không áp dụng độ chính xác) | Mẫu chỉ từ `data/splits/unified/train.csv` (`scripts/live_clip_sample.py:16,27-29`), test_0 khẳng định `split == "train"` (`tests/test_live_harmonized_equivalence.py:161`). Không đo độ chính xác, không chạm TEST. |
| 6 | Chọn model bằng VAL / TEST một lần | PASS (không áp dụng) | Việc này không chọn model; model mặc định không đổi (AC3-a, tôi tự chạy). Ứng viên H-keepz-360 đã chọn ở việc trước; chỉ bật bằng `VSL_MODEL_TYPE=stgcn_h360`. Không có lần chạy TEST nào. |
| 7 | Số liệu truy được | PASS | `reports/live_word_2026-09-28/segment_check.json`: `generated_by.command` đầy đủ, `git_commit` = b1d447a (commit SAU amend, tổ tiên HEAD; sinh 03:39:17Z, giữa b1d447a 10:33 và 2807a8a 10:41 +07), `code_dirty=false`; giữa b1d447a và af6d384 không đổi src/scripts/backend. **Tôi chạy lại** `scripts/live_segment_check.py --n-clips 8 --seed 0 --out <thư mục tạm>` (EXIT 0): phần thân JSON (mọi clip, event, số thực) GIỐNG HỆT bản commit; chỉ khác `command`(đường out), `git_commit`, `generated_at_utc`. Số trong progress_log: 253→310 OK / 0 skip (tôi tái lập 310), AC6 7/8 và phiên bản cv2/numpy (từ JSON), AC4 0.0/0.0 (ghi rõ "in từ test, không phải JSON" — tái lập đúng ở mục 2). Khuyến nghị nhỏ: đưa số AC4 vào một JSON có lệnh + commit nếu sẽ trích ở GATE. |
| 8 | Cỡ mẫu / CI | PASS (có ghi chú) | AC4/AC5 là kiểm tương đương CODE (tất định, sai lệch 0.0) — n=8 đủ cho mục đích đó (§6). AC6 n=8: 7/8 chứa active_span offline; Wilson 95% ≈ [0.53, 0.98] — rộng, không được dùng như tỉ lệ thành công của segmenter. progress_log và JSON chỉ ghi số đếm, không suy ra tỉ lệ/khẳng định chung → không vi phạm. Khuyến nghị: nếu trích 7/8 ở GATE thì kèm CI và nói rõ là clip TRAIN, PNG, lock-step, phiên mới cho mỗi clip. |
| 9 | Nhất quán train–realtime | PASS (trong phạm vi AC4; giới hạn ghi ở mục 13) | **File train không đổi:** `git diff c65032a af6d384 -- src/data/harmonized.py src/data/landmark_extractor.py scripts/extract_keypoints_batch.py scripts/train_unified.py` → 0 dòng (tôi chạy); `git diff --stat 9f4eb68 af6d384 -- <10 file AC7-a>` → 0 dòng. **Cùng extractor:** `HarmonizedLiveSession.__init__` tạo `CleanHolisticExtractor(process_height=preprocessing["process_height"])` (`src/inference/harmonized_live.py:95-97`), `process` gọi `extract_frame(cv2.cvtColor(bgr, BGR2RGB))` (`:154`) — y hệt `extract_from_video` (`src/data/landmark_extractor.py`: cvtColor rồi `extract_frame`, resize INTER_AREA về 360 TRƯỚC `holistic.process`). **harmonize với cfg checkpoint:** `_harmonize_buffer` gọi `harmonize(kps, vis, W/H gốc, fps, cfg=self.preprocessing, timestamps_s=t-t0)`, không truyền rng (`:108-115`); checkpoint có `trim: true` (tôi in dict preprocessing) → cắt nghỉ được giữ. **Test tương đương trên clip thật đi qua bộ giải mã backend:** AC4 đọc video bằng `cv2.VideoCapture` → `cv2.imencode('.png')` → `backend.main._decode_frame(bytes, min_height=360)` (magic + header PIL + `cv2.imdecode`, cùng hàm worker WS dùng) → `session.process` → `finalize_clip()` (`tests/test_live_harmonized_equivalence.py:136-145`); so với `_extract_one` + `HarmonizedDataset[0]` (`:119-134`): landmark thô `array_equal(equal_nan=True)`, shape ảnh vào MediaPipe ghi bằng wrapper quanh `holistic.process` THẬT (360×640 ở cả 2 đường), mask `array_equal`, `max|Δseq| ≤ 1e-5`, top-5 cùng thứ tự `|Δconf| ≤ 1e-4`. Nhánh base64/dataURL + worker WS thật được phủ ở AC5 (WS ↔ session trong process). Mirror: frontend gửi frame không lật, đường mới không lật — khớp train. Kết quả tôi tự chạy: xem mục 2. |
| 10 | Không random/mock/số giả | PASS | `grep -n "latency_ms \* 0\|\* 0\.4\|\* 0\.6" backend/main.py` → rỗng (AC7-d test cũng kiểm). Legacy: `server_infer_ms` = `prediction.latency_ms` (đo bằng `perf_counter` trong `src/inference/predictor.py:274`) khi `is_new_prediction`, ngược lại 0.0; `server_preprocess_ms` = thời gian `pipeline.process_frame` − infer; thêm `decode_ms`, `postprocess_ms` (diff `backend/main.py` quanh `_process_frame_worker`). Harmonized: mọi `*_ms` từ `perf_counter` (AC2-f thay perf_counter bằng dãy biết trước). `grep random|mock|fake|dummy` trên 5 file mới/đổi của đường chính: chỉ `default_rng(seed)` chọn mẫu ở `scripts/live_clip_sample.py:31` (xem S3.2). Frontend không có `Math.random`. Không dự đoán khi đoạn không có tay (AC2-d: `predict` không được gọi). Ghi chú ngoài phạm vi: `reports/audit_round2/v1_latency_benchmark.json` (lịch sử) được tổng hợp từ số bịa 0.4/0.6 — nên đánh dấu vô hiệu. |
| 11 | Bảo mật | PASS (phạm vi kế hoạch) — tồn đọng ngoài phạm vi | `WS_MAX_MESSAGE_BYTES = 1_048_576`, đo trên byte UTF-8/độ dài binary, vượt → `error{message_too_large}` + đóng 1009 (`_parse_ws_message`; test AC3-e cả 2 đường, text+binary, và đúng biên = 1 MiB được nhận; JPEG nhiễu q95 640×480 < giới hạn). `uvicorn.run(..., ws_max_size=WS_MAX_MESSAGE_BYTES)` và `start_fullstack.ps1` thêm `--ws-max-size 1048576` (diff 1 dòng). Ảnh: magic JPEG/PNG → `PIL.Image.open(...).size` (chỉ header) → cạnh > 1920 `frame_too_large`, cao < 360 `frame_too_small` TRƯỚC `cv2.imdecode` (AC3-f dùng spy chứng minh `imdecode` không được gọi với PNG khai 4000×10), kiểm lại kích thước sau giải mã. `confidence_threshold` phải hữu hạn trong [0,1], bool bị từ chối (AC3-g gồm NaN/"abc"/2.0/-0.1/true). Timestamp hữu hạn, tăng ngặt, đúng nguồn (AC3-h). JSON đệ quy sâu → `RecursionError` bị bắt. `detail` ≤ 200 ký tự, không lặp base64 (AC3-f). Checkpoint `features` lạ / mediapipe lệch → 503 + WS 1011, không cache (tôi tự thử in-memory: `harmonized_v2` → 503 `model_unavailable`, WS `error` + close 1011, `GLOBAL_PREDICTOR` vẫn None) — NHƯNG không có test commit cho ca này ở mức backend (chỉ ở `live_pipeline_for`). Sha lệch → không unpickle (AC3-b: `VSLPredictor` là MagicMock phải không được gọi). Không lộ token (grep). **Tồn đọng không do kế hoạch này tạo ra:** `CORSMiddleware(allow_origins=["*"])` (`backend/main.py:328-329`) và WS không kiểm `Origin`, `start_fullstack.ps1` bind `0.0.0.0` — đã nằm trong danh sách chờ người dùng từ kế hoạch 03 ("CORS/WS (Việc 5)"). `detail` của 503 có thể chứa tên file/đường dẫn tương đối từ exception loader (lộ thông tin nhỏ). `/api/classes` vẫn trả 500 (không phải 503) khi model không dùng được. |
| 12 | So sánh công bằng / GATE | PASS (không áp dụng) | Không có so sánh model; không có tiêu chí GATE nào bị đổi. AC4/AC5 giữ nguyên ngưỡng kế hoạch (1e-5, 1e-4); AC6 không có ngưỡng như kế hoạch quy định; tham số segmenter = `SEGMENTER_DEFAULT` đúng bảng §3.4 (tôi đối chiếu JSON `generated_by.segmenter_default`). Model mặc định không đổi (AC3-a). |
| 13 | Kết luận vượt bằng chứng | PASS (không có câu vượt) — thiếu thí nghiệm liệt kê dưới | Tôi đọc dòng progress_log (af6d384) và message 7 commit: các khẳng định đều giới hạn đúng ("cùng máy (Windows)", "chưa so với landmark trích trên Kaggle", "tracker dùng chung cả phiên", "KHÔNG chỉnh tham số"). **Bỏ sót đáng ghi:** với `qipedc_W03251B` hệ quả thực tế là CÙNG gloss `thìa` được phát 2 lần (người dùng sẽ thấy từ lặp), top-5 overlap với `finalize_clip` chỉ 1 và 2, `|Δconf top-1|` = 0.4787 và 0.6391 (JSON) — progress_log chỉ nói "tách thành 2". **Thí nghiệm còn thiếu trước khi nói gì về chất lượng live:** (1) JPEG q0.75 thay PNG; (2) rơi frame thật (AC6 lock-step, `dropped_frames=0`); (3) nhiều ký hiệu trong MỘT phiên (AC6 tạo phiên mới mỗi clip → giới hạn "tracker dùng chung" chưa đo); (4) landmark Kaggle/Linux vs cục bộ (§6); (5) webcam người dùng (Bước 5); (6) ký hiệu có nhịp nghỉ giữa (loại W03251B) — tần suất trong từ điển; (7) độ trễ DoD 8. |

## Kiểm tra đặc biệt

### S1. Amend 2 commit (b1d447a, af6d384) — XONG
- `git reflog`: `98968e3` (10:32:46) → amend → `b1d447a` (10:33:05); `aeeb6a6` (11:03:48) → amend → `af6d384` (11:03:55).
- `git diff 98968e3 b1d447a` và `git diff aeeb6a6 af6d384`: RỖNG (tree giống hệt). Cha giữ nguyên (5627010, 2807a8a).
  Chỉ message đổi: dòng "detect-changes ... risk: none reported" sửa thành risk thật (CRITICAL cho b1d447a, LOW cho af6d384).
  → Không mất nội dung.
- JSON AC6 ghi `git_commit` = b1d447a (commit SAU amend, là tổ tiên HEAD) — amend xảy ra trước khi sinh JSON nên
  tham chiếu không bị treo (xem mục 7).
- Nhánh `feat/vslt-complete` không có upstream (`git log origin/feat/vslt-complete` → unknown revision) → chưa push,
  không ai khác có commit cũ. Đánh giá: vi phạm hình thức quy tắc "không viết lại lịch sử" (amend là viết lại), mức
  THẤP: không mất dữ liệu, không ảnh hưởng người khác, và mục đích là sửa message sai về risk (message cũ khai
  "none reported" trong khi GitNexus báo CRITICAL — sửa là đúng hướng). Khuyến nghị: lần sau dùng commit mới/ghi chú
  thay vì amend; ghi nhận trong progress_log. Không chặn APPROVE.

### S2. detect-changes CRITICAL — caller bị ảnh hưởng — XONG
- Phạm vi thật của 4c9e24c: `backend/main.py` +682/−127 (biến thể `stgcn_h360`, `get_or_load_predictor` kiểm sha
  TRƯỚC khi unpickle, `_active_model`, `health`/`model_info` 503 + trường mới, `_parse_ws_message`, `_image_header`,
  `_decode_frame` viết lại (ném `WsError`), `_process_frame_worker` (số liệu thật), `_process_frame_worker_harmonized`,
  `_session_info`, `_SessionClock`, `websocket_live_stream` viết lại), `start_fullstack.ps1` 1 dòng, test mới.
  CRITICAL là đúng về mặt đồ thị (điểm vào HTTP/WS dùng chung). b1d447a/2807a8a chỉ thêm test + script + JSON; CRITICAL
  ở đó do module test import `backend.main` — không đổi mã chạy (tôi xác nhận `git show --stat`).
- GitNexus `impact websocket_live_stream --direction upstream` → `risk: UNKNOWN`, 0 caller (route gọi qua HTTP/WS) —
  KHÔNG coi là an toàn; tôi xác nhận bằng text search (`grep -rln "live-stream|_decode_frame|get_or_load_predictor|/model/info|api/health"`).
- Ảnh hưởng tới caller KHI DÙNG MODEL MẶC ĐỊNH (đường legacy), cho tới Việc 5:
  | Caller | Hậu quả | Mức |
  |---|---|---|
  | `scripts/smoke_test_phase12.py` bước [2/5] | message đầu giờ là `session_info` → `resp['gloss']` KeyError → smoke test HỎNG (xem mục 2, tôi chạy lại) | Trung bình — script hồi quy thủ công bị gãy, không có trong AC8 |
  | `scripts/smoke_test_phase12.py` bước [4/5] | ảnh hỏng giờ trả `error{code}` (không có `status`) thay vì `frame_result{status:"ERROR"}` → `err_resp['status']` KeyError | như trên |
  | `frontend/src/components/RealtimeStream.jsx` | chỉ đọc `type === 'frame_result'` (`:154`) → `session_info`/`error` bị bỏ qua; `frame_result` legacy giữ đủ khóa cũ (AC7-b) → CHẠY. Mất: frame hỏng không còn hiện trạng thái ERROR (lỗi bị bỏ qua im lặng). `confidence_threshold` slider 0.4–0.95 (`:752-753`) hợp lệ; JPEG 640×480 q0.75 < 1 MiB. | Thấp |
  | `frontend/src/components/Phase12Pipeline.jsx` | chỉ cập nhật khi có `data.gloss`/`data.status` → `session_info`/`error` không có hai khóa đó → bỏ qua. Legacy chạy. | Thấp |
  | `frontend/src/App.jsx` (`/api/health`) | 500 → 503 khi model hỏng: `res.ok` false như cũ → "offline". Trường thêm vô hại. | Không |
  | `tests/test_ws_throughput.py` (script, 0 test) | đếm `session_info` như 1 response; không assert. | Không |
  | `reports/audit_round2/run_v1_latency.py`, `reports/audit_20260924/run_smoke_tests.py` (script lịch sử) | lệch 1 message do `session_info`; `run_v1_latency.py` từng tổng hợp `server_preprocess_ms/server_infer_ms` BỊA (0.4/0.6) vào `reports/audit_round2/v1_latency_benchmark.json` — số đó vô giá trị (không doc .md nào trích, tôi đã grep). | Thấp (ghi chú) |
  | Client gửi khóa `frame`/`data` thay vì `image` | trước được chấp nhận (`payload.get("image") or payload.get("frame") or payload.get("data")`), nay `bad_message`. Không caller nào trong repo dùng. | Thấp (đổi hợp đồng không ghi trong §3.6) |
- KHI BẬT `VSL_MODEL_TYPE=stgcn_h360` (chỉ phục vụ GATE): frontend không dùng được cho tới Việc 5 — `frame_result`
  không mang dự đoán, `metrics.server_preprocess_ms/server_infer_ms/buffer_frames` vắng (RealtimeStream hiện undefined),
  `sign_result` bị cả hai component bỏ qua; Phase12Pipeline còn ghi đè `gloss=null` ở mỗi frame. Đúng như §8 kế hoạch
  (hiển thị thuộc Việc 5/6), nhưng cần ghi rõ: KHÔNG thể GATE bằng UI trước Việc 5.

### S3. 5 giả định coder tự đặt — XONG
1. **Lazy `src/inference/__init__.py` (PEP 562)** — CHẤP NHẬN. Cần để AC1-o đúng (import `sign_segmenter` không kéo
   torch/cv2/mediapipe). `grep` toàn repo: không ai dùng `import src.inference as …` hay truy cập thuộc tính gói; chỉ
   `from src.inference.<module> import …`. Tôi chạy `from src.inference import VSLPredictor, RealtimePipeline,
   TemporalSmoother, VSLREnsemble` → OK (`src.inference.predictor`). Không đổi hành vi.
2. **Sampler có seed ở `scripts/live_clip_sample.py` (ngoài danh sách grep AC7-e)** — KHÔNG phải lách guard về bản
   chất, nhưng là giải một MÂU THUẪN trong kế hoạch mà không báo "CẦN PLANNER": AC4/AC6 BẮT BUỘC
   `np.random.default_rng(0).choice(n, 8, replace=False)` trong khi AC7-e cấm chữ `random` trong
   `scripts/live_segment_check.py`. Mục đích AC7-e (không có kết quả ngẫu nhiên/giả) được giữ: `random` chỉ dùng chọn
   mẫu cố định seed 0, không sinh số liệu; một định nghĩa mẫu dùng chung cho test và script (tốt hơn chép 2 lần).
   Khuyến nghị (thấp): planner sửa AC7-e thành "không có RNG ngoài `default_rng(seed)` chọn mẫu" và thêm
   `scripts/live_clip_sample.py` vào grep với ngoại lệ đó.
3. **`time.perf_counter` thay `time.monotonic` cho nguồn giờ server** — CHẤP NHẬN. Lý do đúng (trên Windows
   `time.monotonic` dùng GetTickCount64, độ phân giải ~15.6 ms, sẽ làm nhiều frame 30 fps trùng giờ → vi phạm tăng ngặt).
   perf_counter cũng đơn điệu; có ghi trong docstring `_SessionClock` (`backend/main.py`). Không ảnh hưởng đường client.
4. **Luật timestamp/message tự đặt** — CHẤP NHẬN, ghi chú:
   - Text không bắt đầu bằng `{` = base64/dataURL trần, nguồn giờ server (giữ tương thích cũ; test AC3-h server).
   - `bad_config` làm bỏ CẢ frame (không chỉ bỏ config) — chặt hơn chữ của §3.6, an toàn; frontend gửi ngưỡng hợp lệ.
   - Nguồn giờ bị chốt ngay khi frame qua bước parse, kể cả khi frame đó sau đó lỗi decode — lệch nhỏ với "frame đầu
     tiên được chấp nhận" ở §3.3; vô hại (cùng một client).
   - Giờ server không tăng → cộng 1e-6 s thay vì từ chối (không thể do client gây ra).
   - Khóa `frame`/`data` của payload cũ không còn được nhận (xem S2) — đổi hợp đồng legacy không có trong §3.6; không
     caller nào trong repo dùng.
5. **Fixture segmenter đổi (tay chỉ đung đưa khi giơ lên)** — KHÔNG phải nới tiêu chí, nhưng che một độ nhạy thiết kế.
   Tôi tự thử (chạy trong bộ nhớ, không sửa file): thay `build` bằng biến thể tay đung đưa CẢ khi nghỉ (biên độ 0.03)
   → 14/15 test AC1 vẫn PASS, chỉ `test_k_dropped_frames_still_one_emit` FAIL (0 event thay vì 1). Quét biên độ:
   tốc độ đỉnh tay nghỉ 0.00/0.31/0.47/0.63/0.79 sw/s → vẫn 1 Emit khi rơi frame; 0.94 sw/s (sát `active_speed`=1.0)
   → 0 Emit khi rơi frame, trong khi ở 30 fps đều vẫn 1 Emit và luật train offline vẫn coi là nghỉ. Nguyên nhân:
   `hand_activity` dùng `fps` TRUNG BÌNH của cửa sổ (theo đúng §3.3 kế hoạch) nên với mẫu giữ1-bỏ1/giữ1-bỏ2 tốc độ bị
   phóng đại tới ~1.2×. Đây là rủi ro §6 đã nêu ("Rơi frame và hand_activity"), không phải lỗi triển khai; fixture
   mới (tay nghỉ đứng yên) đúng định nghĩa "nghỉ" của luật train. Đề xuất (THIẾT KẾ, không chặn): thêm ca AC1-k có
   nhiễu tay nghỉ thực tế, hoặc tính tốc độ theo dt từng frame ở segmenter (không đụng `harmonize`).

### S4. AC6 7/8 — XONG
- Nguồn: JSON đã commit, tái lập được bit-for-bit (mục 7). 8 clip TRAIN, mỗi clip ≥ 1 event, 9 `sign_result`, 0 `sign_discarded`.
- 7/8 clip có đoạn phát chứa trọn active_span offline; top-1 live = top-1 `finalize_clip` ở 9/9 event;
  ở 7 clip bình thường top-5 overlap 4–5, `|Δconf top-1|` ≤ 0.0017.
- Clip ngoại lệ `qipedc_W03251B` (257 frame, active_span offline 0.968–7.074 s): tay nghỉ ~1.9 s giữa ký hiệu
  (active_end 3.136 → active_start 5.038) > `rest_hold_s`=0.5 → 2 `sign_result` đều `thìa`; top-5 overlap 1 và 2,
  `|Δconf top-1|` 0.4787 và 0.6391. Tức là với ký hiệu có nhịp nghỉ, live sẽ phát lặp từ và phân phối xác suất lệch xa
  đường train.
- Kết luận của coder (JSON `note`: "report only: no pass threshold; segmenter parameters not tuned"; progress_log:
  "n_contains_offline_span = 7/8 … ghi nhận, KHÔNG chỉnh tham số") KHÔNG vượt bằng chứng: không suy ra tỉ lệ, không
  khẳng định segmenter "đạt". Thiếu: CI (Wilson 95% ≈ [0.53, 0.98]) và hệ quả "lặp từ" (mục 13).
- AC6 là cận trên lạc quan: PNG không mất, lock-step (không rơi frame), phiên mới mỗi clip, đệm nghỉ bằng frame cuối
  lặp lại. Không được trích như chất lượng segmenter trên webcam.

## Kết luận

**APPROVE** — bảng 1–13 không có FAIL. Lệnh AC8 tôi tự chạy: 310 OK, 0 skip; AC6 tái lập bit-for-bit; file phía train
không đổi so với c65032a; model mặc định không đổi; đường harmonized dùng đúng extractor/360 px/`harmonize(cfg checkpoint)`
và được chứng minh tương đương trên 8 clip TRAIN thật qua bộ giải mã frame của backend.

Việc theo sau (KHÔNG chặn), xếp theo mức độ:

**Triển khai (coder, nhỏ):**
1. (Trung bình) `scripts/smoke_test_phase12.py` hỏng với model mặc định (`KeyError: 'gloss'` ở [2/5] do `session_info`;
   [4/5] còn đợi `status == "ERROR"` trong khi hợp đồng mới trả `error{code}`). Hậu quả của hợp đồng §3.6, coder đã
   liệt kê script là caller nhưng không sửa và không ghi vào progress_log. Sửa script (bỏ qua `session_info`, chấp
   nhận `error`) hoặc ghi rõ "hỏng tới Việc 5" trong progress_log.
2. (Thấp) AC5: thêm `assertGreaterEqual(len(ws_events), 1)` để test không PASS rỗng
   (`tests/test_live_harmonized_equivalence.py:276`).
3. (Thấp) Thêm test backend: checkpoint `features` lạ / `mediapipe_version` lệch → `/api/health` 503 + WS
   `error{model_unavailable}` + 1011, không cache (hành vi đúng — tôi đã thử — nhưng chưa có test).
4. (Thấp) `sign_result.segment.dropped_frames` tính theo `received_seq`, mà `received_seq` tăng cho CẢ message lỗi/
   control → con số gộp "rơi + bị từ chối + control". Đổi tên/ghi chú hoặc đếm riêng trước khi dùng cho DoD 8.
5. (Thấp) progress_log: bổ sung hệ quả W03251B (lặp gloss, top-5 overlap 1–2, |Δconf| 0.48/0.64) và CI cho 7/8.
6. (Thấp) `/api/classes` vẫn 500 khi model không dùng được (health/model_info đã 503); `detail` 503 có thể chứa tên
   file/đường dẫn tương đối từ exception.
7. (Quy trình, thấp) 2 lần `git commit --amend` cục bộ (98968e3→b1d447a, aeeb6a6→af6d384): tree giống hệt, chỉ sửa
   message risk cho đúng, nhánh chưa push → không mất gì; vẫn là viết lại lịch sử — lần sau thêm commit/ghi chú.

**Thiết kế (planner):**
8. Tốc độ tay trong segmenter dùng `fps` trung bình cửa sổ (theo §3.3) → khi rơi frame không đều tốc độ bị phóng đại
   (~1.2× với mẫu AC1-k); tay nghỉ rung 0.94 sw/s làm mất Emit (S3.5). Cân nhắc tính theo dt từng frame ở segmenter
   (không đổi `harmonize`) và thêm ca test có nhiễu tay nghỉ.
9. Ký hiệu có nhịp nghỉ > `rest_hold_s` bị tách và phát lặp từ (W03251B). Cần chính sách (gộp đoạn gần nhau, khử
   trùng gloss liên tiếp, hoặc chỉnh `rest_hold_s` — chỉ trên clip TRAIN/webcam người dùng).
10. AC7-e mâu thuẫn với AC4/AC6 (bắt buộc `default_rng`); sửa câu chữ AC7-e và đưa `scripts/live_clip_sample.py` vào
    grep với ngoại lệ `default_rng(seed)` chọn mẫu.
11. Hợp đồng legacy đã đổi (message đầu `session_info`; lỗi frame thành `error{code}`; bỏ khóa `frame`/`data`) — cần
    ghi vào `docs/phase12_api.md` (DoD 9) và xử lý ở Việc 5.
12. Không thể GATE H-keepz-360 qua UI trước Việc 5 (frontend bỏ qua `sign_result`; Phase12Pipeline ghi đè `gloss=null`).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
1. **Amend cục bộ 2 commit** (không mất nội dung, chưa push): chấp nhận như hiện trạng, hay yêu cầu ghi nhận vi phạm
   quy tắc "không viết lại lịch sử" vào progress_log? (Reviewer đề xuất: chấp nhận + ghi nhận.)
2. **`scripts/smoke_test_phase12.py` đang hỏng** với model mặc định: sửa ngay (việc nhỏ, trước Việc 5) hay để Việc 5?
3. **Ký hiệu có nhịp nghỉ bị phát 2 lần** (W03251B): chấp nhận cho tới việc chỉnh segmenter riêng, hay đưa khử trùng
   gloss vào Việc 5?
4. **CORS `allow_origins=["*"]` + WS không kiểm `Origin` + bind `0.0.0.0`** (tồn đọng từ trước, không do kế hoạch 04):
   vẫn chờ quyết định từ kế hoạch 03 cho Việc 5.
5. **`reports/audit_round2/v1_latency_benchmark.json`** (lịch sử) tổng hợp từ số độ trễ bịa 0.4/0.6 — đánh dấu vô hiệu
   (thêm ghi chú) hay để nguyên? Không tài liệu .md nào đang trích nó.
