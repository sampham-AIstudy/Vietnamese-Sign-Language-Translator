# Kế hoạch 11 — Việc 5: sửa HẾT vi phạm có sẵn của guard DoD 7 backend (sửa code, KHÔNG nới guard)

TRẠNG THÁI: XONG (chờ orchestrator commit + giao coder)

**Điểm dừng: KHÔNG có điểm CẦN NGƯỜI DÙNG trước khi code** (quyết định `--source mock` đã có: 2026-10-02 16:15). Có điểm dừng
có điều kiện trong lúc làm (§7.1) và 2 việc CẦN PLANNER cho kế hoạch khác (§7.2: 08 và 13).

- Nhánh: `feat/vslt-complete` | HEAD khi lập: `f7717a9` | Ngày: 2026-10-03 | Planner chỉ đọc mã (không có Bash, không chạy lệnh).
- Mọi số dòng dưới đây đọc từ cây làm việc lúc HEAD `f7717a9` (các file này không có thay đổi chưa commit theo `git status` đầu phiên).
  Coder xác nhận lại ở B0 bằng lệnh (§4 B0); lệch dòng → dùng nội dung (snippet), không dùng số dòng.
- Danh sách vi phạm CHÍNH THỨC = finding `status: "known"` của `reports/guard_dod7_2026-09-29/guard_findings.json`
  (`generated_by.git_commit = 319ddcdb344572fa4d0878ae9922e60062f202a2`), chép ở `docs/plans/10-progress.md` mục
  "Danh sách vi phạm có sẵn (CHÍNH THỨC, AC5-e)": **9 finding, 8 nhóm** `(path, rule, qualname)`. Không có số nào trong kế hoạch
  này là số đo mô hình.

## 1. Mục tiêu và DoD

**Mục tiêu.** Sửa mã nguồn để guard tĩnh `tests/test_backend_source_guard.py` (kế hoạch 10) không còn báo 9 vi phạm có sẵn;
sổ `KNOWN_VIOLATIONS` co về rỗng (`{}`) bằng cách XÓA các mục đã thành `STALE` sau khi sửa mã; không thêm/nới luật, không thêm
khóa vào `ALLOWED`/`PLAN10_APPROVED_ALLOWED`, không thêm cơ chế ngoại lệ nào. Đồng thời thực hiện quyết định người dùng
2026-10-02 16:15: bộ sinh khung giả của `realtime_demo.py --source mock` chuyển thành fixture chỉ trong `tests/`;
`realtime_demo.py` không còn chế độ `mock`.

**DoD phục vụ.** DoD 7 (autopilot §1), vế "Có test guard FAIL nếu mã nguồn chính chứa Math.random / dữ liệu giả lập / số liệu
hard-code" — phần backend/Python: kế hoạch 10 §3.5 ý 4 quy định DoD 7 backend CHỈ PASS khi `KNOWN_VIOLATIONS` rỗng, có bằng chứng
JSON `summary.by_status.known = 0` kèm commit. DoD 6 ("không có kết quả giả ở bất kỳ chế độ nào") hưởng lợi trực tiếp: chế độ
nguồn khung tổng hợp bị gỡ khỏi điểm vào người dùng. Hạng mục review 10 ("Không random/mock/số giả").

**Thêm (bắt buộc theo review merge cloud, `docs/reviews/cloud-2026-09-29-review.md` §5 và §7 điều kiện 4: "Trước khi code 08 và 11:
planner xử lý K1 + P2"):**
- K1: thêm test MÁY kiểm "sổ chỉ co lại": mọi khóa `KNOWN_VIOLATIONS`/`ALLOWED` phải có trong JSON mốc đã commit và count không lớn hơn.
- P2: AC "không sửa test cũ" của kế hoạch này có NGOẠI LỆ CÓ TÊN, đúng một vùng: được xóa mục trong khối `KNOWN_VIOLATIONS` của
  `tests/test_backend_source_guard.py`; cấm mọi thay đổi khác ở phần có sẵn của file (§5 AC2).

**Không thuộc việc này:** 16 khóa `ALLOWED` (DTG đã duyệt ở kế hoạch 10 — giữ nguyên); import lười trong `src/inference/ensemble.py`
để đưa `augment.py` ra khỏi bao đóng (kế hoạch 10 đề xuất "tùy chọn" — không làm, vì sẽ làm 8 khóa ALLOWED thành STALE và cần
sửa `ALLOWED`, ngoài yêu cầu); docstring `/api/classes` "(487 classes for Tier 2)" trong `backend/main.py` (không phải finding
của guard; không đụng `backend/main.py`); guard thứ hai cho `scripts/` đo/báo cáo (backlog); các quan sát ở §2.6.

## 2. Hiện trạng (đã đọc mã tại HEAD f7717a9)

### 2.1 Guard và sổ đăng ký
- `tests/test_backend_source_guard.py:46` `ENTRYPOINTS = ("backend/main.py", "realtime_demo.py")`; `:158-168`
  `PLAN10_APPROVED_ALLOWED` (16 khóa); `:174-207` `ALLOWED` (16 khóa, tổng count 36); `:209-210` comment "This registry may only
  SHRINK"; `:211-235` `KNOWN_VIOLATIONS` (8 khóa, tổng count 9).
- `:1188-1212` `TestBackendSourceGuard`: `test_a_tree_matches_registry` (unregistered/changed/stale đều rỗng), `test_b_registry_shape`,
  `test_c_summary_line` (in `[DoD7-guard] known=<n> allowed=<m>`).
- `:1215-1271` `TestRegistryComparator`: `_registered_key()` (`:1235-1238`) dùng `KNOWN_VIOLATIONS or ALLOWED` → khi KNOWN rỗng vẫn
  chạy bằng khóa ALLOWED đầu tiên (ALLOWED không rỗng) → không đỏ (K2 của review 10 không xảy ra ở kế hoạch này).
- Hệ quả cơ chế: sửa mã làm 1 nhóm KNOWN về 0 finding → `stale` → `test_a_tree_matches_registry` FAIL cho tới khi xóa mục đó khỏi
  sổ. Vì vậy mỗi bước sửa mã PHẢI xóa đúng mục KNOWN tương ứng trong CÙNG commit (không có commit nào để guard đỏ).
- Thiếu (K1): không có test so sổ với JSON mốc `reports/guard_dod7_2026-09-29/guard_findings.json`; tăng count trong sổ cùng lúc
  thêm vi phạm thì test vẫn xanh. Thiếu: không có test khẳng định `KNOWN_VIOLATIONS == {}` (DoD 7 backend).

### 2.2 Từng vi phạm (9 finding, 8 nhóm) — vị trí tại HEAD, mã đã đọc

| # | file:dòng | Luật | qualname | Mã tại HEAD | Bản chất |
|---|---|---|---|---|---|
| V1 | `realtime_demo.py:52` | C-result | `RealtimeHUD._locate_vietnamese_font` | `candidates = [ "C:/Windows/Fonts/segoeui.ttf", … ]` (`:52-58`), duyệt `:59-61`, `return "arial.ttf"` `:62` | Tên biến `candidates` ∈ `RESULT_KEYS` (`tests/test_backend_source_guard.py:134-135`); thực chất là danh sách đường dẫn font, không phải kết quả nhận dạng. |
| V2, V3 | `realtime_demo.py:266`, `:267` | C-string ×2 | `RealtimeDemo._open_stream` | `elif self.source == "mock":` / `print("Using Synthetic Mock Video Stream for Smoke Test...")`; `cap = None` `:268` | Chế độ nguồn giả trong điểm vào người dùng. |
| V4 | `realtime_demo.py:294` | C-string | `RealtimeDemo.run` | `if self.source == "mock":` → `frame = np.zeros((720, 1280, 3), dtype=np.uint8)`; `cv2.circle(frame, (640, 360), 80, (60, 60, 60), -1)` (`:294-297`) | Bộ sinh khung tổng hợp (khung đen + hình tròn xám) chạy qua pipeline thật → HUD hiển thị dự đoán trên khung giả. |
| V5 | `realtime_demo.py:330` | D-binding | `RealtimeDemo.run` | `avg_fps = 1.0 / (sum(fps_tracker) / len(fps_tracker)) if fps_tracker else 30.0` | FPS 30 gõ tay (nhánh không tới được vì `:329` vừa `append`), nhưng còn lỗi ẩn: `dt` đo bằng `time.time()` (`:290`, `:328`) có thể = 0 → `ZeroDivisionError` khi trung bình = 0. Giá trị hiển thị ở HUD `:140` (`f"{fps:.1f} FPS | …"`) và log headless `:379`. |
| V6 | `realtime_demo.py:395` | C-string | `main` | `help="Webcam device index ('0', '1') or video path ('path.mp4') or 'mock'"` | Quảng cáo chế độ mock. |
| V7 | `src/data/landmark_extractor.py:121` | D-binding | `CleanHolisticExtractor.extract_from_video` | `fps = cap.get(cv2.CAP_PROP_FPS) or 25.0`; trả `"fps": float(fps)` `:157` | Bịa fps 25 khi video không có metadata frame rate. |
| V8 | `src/data/vsl_gh_dataset.py:31` | D-string | `<module>` | Chuỗi `"""…"""` cấp module `:31-70` (đứng sau import `:15-25`, không phải docstring; docstring thật `:1-13`), chứa `"Hand landmark ordering is 100% identical between VSL-GH and current project (LH: 21, RH: 21)."` (`:58`) | Câu mô tả có "100%" (khớp D-string (i)); là mô tả ánh xạ, không phải số đo. |
| V9 | `src/inference/sign_segmenter.py:141` | D-binding | `SignSegmenter._activity` | `fps = (n - 1) / (t1 - t0) if n >= 2 and t1 > t0 else 30.0   # n == 1: speed is 0 whatever fps is` | 30.0 gõ tay; chỉ dùng khi cửa sổ có 1 frame (`validate_time` `:174-181` buộc timestamp tăng ngặt ⇒ `n ≥ 2` kéo theo `t1 > t0`). Với T = 1, `hand_activity` (`src/data/harmonized.py:68-77`) có `speed[1:]` rỗng ⇒ `speed ≡ 0` với MỌI fps ⇒ giá trị 30.0 không ảnh hưởng kết quả. |

### 2.3 Caller / người dùng của mã bị sửa (Grep của planner; coder phải chạy `impact` GitNexus — §3.6)
- `RealtimeDemo`: `run_core.py:116-119` (`--webcam` → `RealtimeDemo(source=str(args.webcam))`) và `:121-125` (`--video`) — không
  truyền `"mock"`. `RealtimeHUD`: `scripts/generate_slide_images.py:19`, `:35`, `:55-60` (gọi `draw_hud(..., fps=28.5, ...)`).
  Không test nào import `realtime_demo` (Grep `RealtimeDemo|RealtimeHUD|realtime_demo` trong `tests/`: chỉ chuỗi trong
  `tests/test_backend_source_guard.py`). Tài liệu nhắc `realtime_demo.py`: `README.md:150,203,206`, `docs/phase10_realtime.md`
  (`:147-163`, `:176` "verified on video stream and mock stream" — tài liệu lịch sử phase 10), không tài liệu nào hướng dẫn `--source mock`.
- `CleanHolisticExtractor.extract_from_video`: `scripts/extract_keypoints_batch.py:41,46` (ghi `fps=float(res["fps"])` vào metadata
  npz — đường TRÍCH DỮ LIỆU TRAIN), `src/data/vsl_dataset.py:322,331` (auto-extract, ghi metadata), `src/translation/end_to_end.py:195`
  (không dùng `fps`), `reports/audit_20260924/run_smoke_tests.py:37` (script lịch sử). Người đọc `fps` của npz:
  `src/data/harmonized.py:175-177` (`HarmonizedDataset.__getitem__`: `.get("fps") or 30.0`) → `harmonize` `:129`
  (`fps if fps and fps > 0 else 30.0`); `scripts/shortcut_85.py:76` (`or 30.0`); `scripts/source_diagnostics.py:97` (`if r["fps"]`).
  Tiền lệ cùng ý nghĩa trên đường phục vụ: `src/inference/harmonized_live.py:113`
  `fps = (n - 1) / ts[-1] if n >= 2 and ts[-1] > 0 else 0.0` rồi `harmonize(...)` tự áp mặc định — tức là "0.0 = chưa đo được,
  module tiền xử lý chung quyết định".
- `SignSegmenter._activity`: gọi từ `push` (`:213`); test hiện có `tests/test_sign_segmenter.py`; kế hoạch 08 (CHƯA bắt đầu — không
  có `docs/plans/08-progress.md`) sẽ viết lại hàm này (§3.2 của 08: `n = 1: fps_last = 30.0`, `docs/plans/08-segmenter-live.md:152`)
  và dùng `_activity` làm điểm ghi đè cho `WindowMeanFpsSegmenter` (`:178-181`).
- `src/data/vsl_gh_dataset.py`: kế hoạch 13 [LS1] được sửa file này (thêm tham số `sentence_split`, `docs/plans/13-train-lai-checkpoint-thieu.md:527-528`;
  đã làm ở B2b). Thay đổi của kế hoạch 11 ở file này chỉ là chữ trong một chuỗi không được dùng (§3.4).

### 2.4 Ràng buộc song song (kế hoạch 13 đang chạy)
- File của 13 (KHÔNG đụng): `kaggle/vsl-retrain-*`, `scripts/retrain_*`, `scripts/eval_sentsplit.py`, `scripts/archive_retrain_kaggle.py`,
  `tests/test_retrain_tools.py`, `tests/test_sentence_split_guard.py`, `src/data/sentence_split.py`, `reports/retrain_*`,
  `docs/plans/13-progress.md`. **Không vi phạm nào trong 9 nằm ở các file này** → không có vi phạm nào phải xếp sau khi 13 đóng.
- Kernel K2 đang chạy dùng commit ghim `28a126e` (clone tại commit ghim) → commit của kế hoạch 11 trên nhánh không đổi mã kernel đang chạy.
- Kế hoạch 13 còn bước đánh giá local (B11) đòi `code_dirty = false` → coder 11 không được để thay đổi chưa commit trong `src/`,
  `backend/`, `tests/`, `realtime_demo.py` giữa các bước (mỗi bước kết thúc bằng commit).
- Kế hoạch 11 KHÔNG sửa `backend/main.py` (0 finding ở file này) → không xung đột "2 coder cùng sửa backend/main.py".

### 2.5 Mốc test hiện có (từ `docs/plans/13-progress.md`, không phải số đo mới)
- Lệnh AC2-06 31 module (`docs/plans/06-viec5-frontend.md:1028`): lần ghi gần nhất `Ran 518`, `FAILED (failures=1, errors=1, skipped=1)`
  tại `ea12b44` (`13-progress.md:399-410`): ERROR `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu ViT5);
  1 skip `stgcn_best.pt not found`; failure chập chờn `tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs`
  (`[1, 1, 1, 0] != [1, 1, 1, 1]`, PASS khi chạy riêng). Checkpoint stgcn_best / CSLR / ViT5 chưa đặt vào `checkpoints/` (13 B11).
  Mốc chính thức của kế hoạch 11 do coder chạy lại ở B0 (§4), không dùng số trên làm mốc.
- Guard: `[DoD7-guard] known=9 allowed=36`; dòng `[scope] serving=45 main=56` (13-progress `:326`).

### 2.6 Quan sát ngoài phạm vi (ghi để orchestrator xếp backlog; KHÔNG sửa ở đây)
- `README.md:203` và docstring `realtime_demo.py:8` hướng dẫn `realtime_demo.py --webcam 0/1`, nhưng `main()` (`:393-400`) không có
  đối số `--webcam` (chỉ `--source`, `--video`) → lệnh README sẽ lỗi argparse. Thuộc việc 8 (README, clone sạch).
- `scripts/generate_slide_images.py:60` vẽ HUD với `fps=28.5` gõ tay (ảnh slide); ngoài phạm vi guard (scripts trình bày, kế hoạch 10 §2.4).
- `realtime_demo.py:331` hiển thị `latency 0.0ms` khi chưa có dự đoán (sentinel, không phải finding).

## 3. Thiết kế cách sửa

### 3.0 Nguyên tắc (áp cho mọi bước)
1. **Guard là trọng tài, không bị sửa.** Trong `tests/test_backend_source_guard.py` chỉ được: (a) XÓA mục trong khối
   `KNOWN_VIOLATIONS` khi nhóm đó đã về 0 finding; (b) THÊM lớp test/hàm phụ mới ngay trước `if __name__ == "__main__":`.
   Không đổi luật, regex, `SENTINELS`, `UNIT_FACTORS`, `RESULT_KEYS`, `METRIC_TOKENS`, `FAKE_TOKENS`, `ENTRYPOINTS`, `MIN_SERVING`,
   `NOT_SERVING`, `SCRIPTS_REALTIME`, `ALLOWED`, `PLAN10_APPROVED_ALLOWED`, hàm quét, test có sẵn.
2. **Sửa nguyên nhân, không né luật.** CẤM: đổi tên biến chứa token METRIC/FAKE mà giá trị vẫn là số gõ tay (ví dụ `fps` → `rate`
   giữ `30.0`); chuyển số/chuỗi sang file ngoài MAIN/SERVING (ví dụ sang `scripts/` hay `configs/`) để guard không thấy; chuyển chuỗi
   chứa số đo thành comment; thêm import động để thoát bao đóng; thêm khóa ALLOWED; comment ngoại lệ tại chỗ. NGOẠI LỆ CÓ TÊN DUY NHẤT
   về "đưa ra ngoài phạm vi": bộ sinh khung giả → fixture trong `tests/` (quyết định người dùng 2026-10-02 16:15).
3. **Không tạo finding mới.** Sau mỗi sửa, guard phải cho `unregistered = []`, `changed = []`, `stale = []`. Có finding mới → viết lại
   cách sửa; không đăng ký (§7.1 điểm 3).
4. **Hành vi**: chỉ đổi những gì liệt kê ở §3.7; mọi thứ khác bằng hệt.
5. **Một bước = một commit**, commit chứa: mã sửa + test mới + xóa mục KNOWN tương ứng + cập nhật `docs/plans/11-progress.md`.
   Không commit nào để `tests.test_backend_source_guard` đỏ.

### 3.1 `realtime_demo.py` (V1–V6: 6 finding, 5 nhóm)
**(a) Gỡ chế độ mock (V2, V3, V4, V6).**
- `RealtimeDemo._open_stream` (`:260-278`): xóa nhánh `elif self.source == "mock": … cap = None` (`:266-268`). Hệ quả: `source="mock"`
  đi vào nhánh đường dẫn video → `FileNotFoundError("Video file not found: mock")` khi không có file tên `mock` (như mọi đường dẫn sai).
  `cap` không còn là `None`; điều kiện `cap is not None` ở `:275` và `:386` được giữ hoặc rút gọn (không bắt buộc).
- `RealtimeDemo.run` (`:280-390`): xóa nhánh `if self.source == "mock": …` (`:294-297`); mọi nguồn đều `ret, frame = cap.read()`,
  giữ `if not ret: print("End of video stream reached."); break`.
- `main` (`:395`): help `--source` = `"Webcam device index ('0', '1') or video path ('path.mp4')"`.
- Không thêm tham số mới vào `RealtimeDemo.__init__` (chữ ký giữ nguyên: `source, model_type, headless, max_frames, draw_skeleton`).
- **Fixture** (thay cho `--source mock`): file test MỚI `tests/test_realtime_demo_source.py` định nghĩa lớp `SyntheticFrameSource(n_frames)`
  với giao diện tối thiểu của `cv2.VideoCapture`: `isOpened() -> True`, `read() -> (True, frame)` cho `n_frames` lần đầu rồi
  `(False, None)`, `release()` (ghi cờ đã gọi). `frame` sinh ĐÚNG như mã cũ `:296-297`: `np.zeros((720, 1280, 3), dtype=np.uint8)`
  + `cv2.circle(frame, (640, 360), 80, (60, 60, 60), -1)`. Docstring ghi "test fixture moved from realtime_demo.py --source mock
  (user decision 2026-10-02 16:15); never imported outside tests/". Test chạy `RealtimeDemo.run()` bằng cách thay `_open_stream` của
  instance (`mock.patch.object`) để trả fixture. Fixture KHÔNG được import từ `src/`, `backend/`, `scripts/`, `realtime_demo.py`.
- Test dựng `RealtimeDemo` mà KHÔNG nạp checkpoint/ViT5/MediaPipe: thay `realtime_demo.VSLPredictor`, `realtime_demo.RealtimeLandmarkExtractor`,
  `realtime_demo.RealtimePipeline` bằng đối tượng giả trong test, và chặn `from src.translation.translator import VSLTranslator`
  (`:250`) bằng `mock.patch.dict(sys.modules, …)` hoặc tương đương; có spy chứng minh lớp thật không được dựng. (Mock chỉ trong
  `tests/`, ngoài phạm vi guard — đúng thiết kế kế hoạch 10 §3.1.)

**(b) FPS hiển thị (V5).**
- Thêm 2 hàm thuần cấp module trong `realtime_demo.py`:
  - `mean_fps(frame_times_s) -> float`: rỗng, hoặc trung bình không hữu hạn, hoặc trung bình ≤ 0 → `0.0` (nghĩa: "chưa đo được");
    ngược lại `1.0 / mean`.
  - `format_fps(fps) -> str`: `fps` hữu hạn và `> 0` → `f"{fps:.1f} FPS"`; ngược lại `"-- FPS"` (ASCII — log headless in ra console
    Windows, tránh lỗi mã hóa).
- `run`: `t_start = time.perf_counter()`, `dt = time.perf_counter() - t_start` (thay `time.time()` ở `:290`, `:328`; `t_prev` `:284`
  không dùng → xóa); `avg_fps = mean_fps(fps_tracker)`.
- `RealtimeHUD.draw_hud` `:140`: `f"{format_fps(fps)} | {latency_ms:.1f}ms"`; log headless `:379`: thay `{avg_fps:.1f} FPS` bằng
  `{format_fps(avg_fps)}`.
- Không có số gõ tay mới (`0.0` thuộc `SENTINELS` của guard; không dùng số nào khác).

**(c) V1.** Đổi tên biến cục bộ `candidates` → `font_paths` (`:52`, `:59`). Lý do (không phải né luật): trong dự án `candidates` là
khóa KẾT QUẢ nhận dạng (`RESULT_KEYS`); biến này là danh sách đường dẫn font → tên mới mô tả đúng nội dung; hành vi y hệt. Đây là
hướng sửa kế hoạch 10 đã nêu cho nhóm này ("đổi tên biến"), không phải ALLOWED.

### 3.2 `src/data/landmark_extractor.py` (V7)
- `CleanHolisticExtractor.extract_from_video` `:121`: `fps = float(cap.get(cv2.CAP_PROP_FPS))`; nếu `not fps > 0` (0, âm, NaN) →
  `fps = 0.0`. Docstring mục trả về `'fps'`: "frame rate stored in the container; 0.0 = unknown (no metadata) — harmonize() applies
  its own default". Không đặt 25 hay số nào khác.
- Mặc định khi thiếu fps chỉ còn ở MỘT chỗ: module tiền xử lý chung `src/data/harmonized.py` (`:129`, `:175-177`, đã là ALLOWED của
  kế hoạch 10), cùng quy ước với `src/inference/harmonized_live.py:113`.
- Hệ quả hành vi (duy nhất): video KHÔNG có metadata fps → npz metadata `fps = 0.0` thay vì `25.0` → khi train, `harmonize` dùng
  `30.0` thay vì `25.0` cho clip đó. Chỉ ảnh hưởng lần TRÍCH LẠI sau này; npz đã có không đổi; đường live dùng timestamp thật, không
  dùng hàm này. B0 đếm số video như vậy trong dữ liệu local (§7.1 điểm 2).
- Không đổi `__init__`, `_get_holistic`, `extract_frame`, `save_landmarks_npz`, `scripts/extract_keypoints_batch.py`.

### 3.3 `src/inference/sign_segmenter.py` (V9)
- `SignSegmenter._activity` `:141`: `fps = (n - 1) / (t1 - t0) if n >= 2 and t1 > t0 else 0.0` kèm comment "one frame: no rate is
  measured; hand_activity's speed term is empty, so the result does not depend on fps". Không đổi dòng nào khác.
- Chứng minh không đổi hành vi: n = 1 → `hand_activity` với T = 1: `speed = np.zeros(1)`, `both = present[1:] & present[:-1]` rỗng →
  `speed` giữ 0 với mọi fps → kết quả độc lập fps. n ≥ 2 → nhánh tính không đổi. Kiểm bằng test tương đương (§5 AC4).
- Phối hợp kế hoạch 08: `08-segmenter-live.md:152` ghi `n = 1: fps_last = 30.0` — sau kế hoạch 11 câu đó sẽ tạo finding D-binding mới
  (sổ KNOWN đã rỗng, `TestKnownEmpty` cấm đăng ký) → CẦN PLANNER 08 sửa thành cùng quy ước `0.0` (§7.2, không phải người dùng).
- Không chạy cùng lúc với coder 08 B1 (cùng hàm). Nếu tới bước này mà 08 B1 đã commit: đọc lại hàm tại HEAD, áp CÙNG nguyên tắc
  (không số gõ tay ở nhánh 1 frame), chạy lại impact, ghi vào 11-progress; test tương đương AC4 so với mã tại commit cha của bước này.

### 3.4 `src/data/vsl_gh_dataset.py` (V8)
- Đổi DUY NHẤT dòng `:58` trong chuỗi khối `:31-70`:
  `Hand landmark ordering is 100% identical between VSL-GH and current project (LH: 21, RH: 21).` →
  `Hand landmark ordering is the same in VSL-GH and the current project (MediaPipe Hands 0..20 for each hand; LH: 21, RH: 21).`
- Giữ dạng chuỗi (không chuyển thành comment — thay đổi nhỏ nhất, file này kế hoạch 13 đã sửa). Câu mới không có `%`, không có
  "số + ms/fps", không có từ khóa số liệu (D-string (i)–(iii)). Lý do: "100%" là cách nói tuyệt đối, không phải phép đo; câu mới
  nói đúng sự kiện mà bảng ánh xạ ngay trong chuỗi mô tả (`:41-42`, `:55-56`).
- Không đổi mã; `git diff` của file = đúng 1 dòng `-`, 1 dòng `+`.

### 3.5 Guard: co sổ, K1, DoD 7
- Mỗi bước sửa xóa đúng các mục KNOWN của nhóm đã về 0 (bảng §4). Cuối cùng `KNOWN_VIOLATIONS = {}`; giữ comment `:209-210`, được
  thêm 1 dòng comment "emptied by plan 11 (all pre-existing violations fixed in code)". Không đổi count của mục còn lại (chỉ xóa cả mục).
- **K1 — lớp mới `TestRegistryBaseline`** (B1), chỉ thư viện chuẩn (giữ `TestImportLight`):
  - hằng `BASELINE_REPORT = "reports/guard_dod7_2026-09-29/guard_findings.json"`,
    `BASELINE_COMMIT = "319ddcdb344572fa4d0878ae9922e60062f202a2"`;
  - hàm thuần `baseline_counts(report: dict) -> dict[str, dict[tuple, int]]` (gom `findings` theo `status` rồi `(path, rule, qualname)`)
    và `registry_excess(registry: dict, base: dict) -> list[str]` (khóa không có trong mốc → `"NEW <key>"`; count > mốc →
    `"GREW <key>: mốc N, sổ M"`);
  - `test_a_baseline_provenance`: file tồn tại, `generated_by.git_commit == BASELINE_COMMIT`, `generated_by.code_dirty is False`,
    `summary.by_status.unregistered == 0`;
  - `test_b_known_within_baseline`: `registry_excess(KNOWN_VIOLATIONS, base["known"]) == []`;
  - `test_c_allowed_within_baseline`: `registry_excess(ALLOWED, base["allowed"]) == []`;
  - `test_d_excess_detects_growth` (tự kiểm trong bộ nhớ): sổ có khóa mới → ≥ 1 dòng `NEW`; sổ có count +1 → ≥ 1 dòng `GREW`;
    sổ = mốc → `[]`; sổ rỗng → `[]`.
  Muốn nới sổ sau này phải sửa cả JSON mốc đã commit hoặc hằng `BASELINE_COMMIT` → lộ rõ khi review (đúng đề xuất review cloud §5).
- **DoD 7 — lớp mới `TestKnownEmpty`** (B5, cùng commit xóa mục KNOWN cuối): `test_known_violations_empty`:
  `assertEqual(KNOWN_VIOLATIONS, {}, "DoD 7 backend: vi phạm phải được SỬA trong mã, không đăng ký (kế hoạch 11)")`.
- Không test mới nào dùng `skip*`/`expectedFailure`.

### 3.6 Impact GitNexus (BẮT BUỘC trước khi sửa symbol — CLAUDE.md)
Lệnh: `node .gitnexus/run.cjs impact "<symbol>" --direction upstream --repo .` (chưa có `.gitnexus/run.cjs` → bootstrap theo CLAUDE.md,
hoặc `npx --yes gitnexus@1.6.12 impact …` như kế hoạch 10). Index cũ (lastCommit khác HEAD và `git diff --stat <lastCommit> HEAD --
src backend realtime_demo.py` khác rỗng) → `node .gitnexus/run.cjs analyze --index-only` trước. Ghi caller + `risk` vào 11-progress.
HIGH/CRITICAL → ghi CẢNH BÁO trong 11-progress và commit message (CRITICAL → §7.1 điểm 6). `UNKNOWN`/caller rỗng → KHÔNG coi là
an toàn: xác nhận bằng Grep (các caller planner đã thấy ở §2.3) và ghi kết quả.

| Bước | Symbol (impact upstream) | File |
|---|---|---|
| B1 | `compare_registry`, `registry_totals` (chỉ đọc — lớp mới gọi lại; không sửa) | `tests/test_backend_source_guard.py` |
| B2 | `SignSegmenter._activity` (và `SignSegmenter.push` để thấy luồng) | `src/inference/sign_segmenter.py` |
| B3 | `CleanHolisticExtractor.extract_from_video` | `src/data/landmark_extractor.py` |
| B4 | không có symbol (chuỗi cấp module); `context` cho file `src/data/vsl_gh_dataset.py` để ghi người import | `src/data/vsl_gh_dataset.py` |
| B5 | `RealtimeHUD._locate_vietnamese_font`, `RealtimeHUD.draw_hud`, `RealtimeDemo._open_stream`, `RealtimeDemo.run`, `main` (của `realtime_demo.py` — tên `main` trùng nhiều file: dùng `--file realtime_demo.py` hoặc `context` để chọn đúng) | `realtime_demo.py` |

Trước MỖI commit: `node .gitnexus/run.cjs detect-changes --scope all --repo .`; `partial: true`/`truncated: true` → chạy lại; ghi `risk`
vào commit message.

### 3.7 Hợp đồng hành vi sau sửa (danh sách ĐẦY ĐỦ thay đổi quan sát được)

| Chỗ | Trước (HEAD f7717a9) | Sau |
|---|---|---|
| `realtime_demo.py --source mock` | khung tổng hợp chạy qua pipeline thật | `FileNotFoundError: Video file not found: mock` (như đường dẫn sai) |
| `realtime_demo.py --help` | nhắc `'mock'` | không nhắc |
| FPS trên HUD / log headless khi chưa đo được (trung bình dt ≤ 0) | `ZeroDivisionError` (nhánh `30.0` không tới được) | `-- FPS` |
| FPS bình thường | `1 / mean(dt)` với `time.time()`, `"%.1f FPS"` | `1 / mean(dt)` với `time.perf_counter()`, cùng định dạng |
| `extract_from_video` khi container không có fps | `fps = 25.0` | `fps = 0.0` (harmonize áp mặc định của nó) |
| `SignSegmenter` | — | bằng hệt (sự kiện + `hand_active` từng frame) |
| `vsl_gh_dataset` | — | bằng hệt (chỉ đổi chữ trong chuỗi không dùng) |

Không đổi: `backend/` (API, WS, CORS), frontend, model mặc định, checkpoint, tham số tiền xử lý/segmenter, `run_core.py`,
`scripts/`, chữ ký `RealtimeDemo.__init__`/`RealtimeHUD.draw_hud`.

Module tiền xử lý chung: kế hoạch không chép công thức tiền xử lý nào; test tương đương (AC4, AC5) gọi thẳng `_normalise`,
`hand_activity`, `harmonize` của `src/data/harmonized.py`.

## 4. Chia việc

Quy ước: `$PY` = `.venv/Scripts/python` (local Windows) hoặc `.venv/bin/python` (cloud); mọi lệnh Python kèm `PYTHONIOENCODING=utf-8`.
`P11` = HEAD lúc bắt đầu B0 (ghi hash đầy đủ vào 11-progress). Log/file tạm: `_work/_plan11_tmp/` (KHÔNG commit). Tiến độ:
`docs/plans/11-progress.md`, cập nhật sau MỖI bước bằng output thật (chép dòng tổng kết, không gõ số tay). Commit message bắt đầu
`11:` (bước) hoặc `WIP 11:` (chỉ tiến độ), có dòng `detect-changes: risk=<…>` và dòng `[DoD7-guard] known=<n> allowed=<m>` chép
từ output test. Không amend/rebase/force-push. Commit bằng `git commit -- <paths>` (chỉ file của bước; không cuốn file coder 13 đã stage).

**Mẫu mỗi bước sửa (B2–B5) — "test đỏ trước":**
1. `impact` các symbol của bước (§3.6) → ghi 11-progress.
2. Viết test mới của bước; chạy → các ca hành vi MỚI phải FAIL/ERROR trên mã cũ (log `_work/_plan11_tmp/<bước>_red_tests.txt`);
   ca tương đương (characterization) phải PASS trên mã cũ (trừ ngoại lệ ghi ở AC6 R3).
3. Xóa mục KNOWN của bước TRƯỚC khi sửa mã; chạy `tests.test_backend_source_guard` → FAIL với `unregistered` đúng các finding của
   nhóm đó và không gì khác (log `<bước>_red_guard.txt`) — đây là bằng chứng guard bắt đúng vi phạm.
4. Sửa mã theo §3; chạy lại guard (OK, 0 skip) + test mới + test liên quan (cột "Test liên quan") → OK; log `<bước>_green.txt`.
5. `detect-changes`; commit.

| Bước | Nội dung | Mục KNOWN xóa | Test mới / liên quan | Phụ thuộc | Ước lượng |
|---|---|---|---|---|---|
| **B0** | Mốc. (1) `git rev-parse HEAD` → P11; `git status --porcelain` → `b0_status.txt`; `git diff --stat HEAD -- realtime_demo.py src/data/landmark_extractor.py src/data/vsl_gh_dataset.py src/inference/sign_segmenter.py tests/test_backend_source_guard.py` → rỗng (khác rỗng → §7.1 điểm 5). (2) Đối chiếu dòng §2.2 với mã (ghi lệch nếu có). (3) `$PY -m tests.test_backend_source_guard --report _work/_plan11_tmp/b0_guard.json` → kiểm `by_status` (`known`, `allowed`, `unregistered`) và tập khóa known == 8 khóa §2.2 với count như sổ (khác → §7.1 điểm 1). (4) Lệnh AC7 phần "31 module" → `b0_ac2_31.log`; liệt kê id test không-ok (FAIL/ERROR/skip) → `b0_nonok.txt`; `$PY -m unittest tests.data.test_vsl_gh_dataset -v` → `b0_vslgh.log`. (5) Đếm video thiếu fps (ghi chú B0 dưới bảng) → `b0_fps_metadata.json`. (6) `sha256sum` (hoặc `certutil -hashfile`) danh sách file trong `checkpoints/` → `b0_ckpt.txt`. (7) Kiểm index GitNexus (lastCommit) → analyze nếu cũ. (8) Tạo `docs/plans/11-progress.md`; commit `WIP 11: B0 mốc`. | — | — | — | 1 giờ |
| **B1** | K1 (§3.5): thêm `baseline_counts`, `registry_excess`, lớp `TestRegistryBaseline` (4 test) vào cuối `tests/test_backend_source_guard.py` (trước `if __name__`). Không đổi dòng nào có sẵn. Chạy module 2 lần → OK cả hai. "Đỏ trước": `test_d_excess_detects_growth` chính là đột biến (khóa mới, count +1); thêm bằng chứng tay: chạy `registry_excess` trên bản sao trong bộ nhớ của `KNOWN_VIOLATIONS` với 1 count +1 → in dòng `GREW` (log `b1_red.txt`, không commit mã thử). | — | `tests.test_backend_source_guard` | B0 | 1.5 giờ |
| **B2** | V9 `sign_segmenter.py` (§3.3). Không làm nếu coder 08 đang sửa file này (§7.1 điểm 5). | `('src/inference/sign_segmenter.py', 'D-binding', 'SignSegmenter._activity')` | MỚI `tests/test_guard_dod7_fixes.py::TestSegmenterSingleFrame` (AC4); liên quan `tests.test_sign_segmenter`, `tests.test_harmonized_live`, `tests.test_ws_live_contract` | B1 | 1 giờ |
| **B3** | V7 `landmark_extractor.py` (§3.2). Chỉ làm nếu điều kiện B0(5) thỏa (§7.1 điểm 2). | `('src/data/landmark_extractor.py', 'D-binding', 'CleanHolisticExtractor.extract_from_video')` | MỚI `tests/test_guard_dod7_fixes.py::TestExtractorFps`, `::TestHarmonizeUnknownFps` (AC5); liên quan `tests.test_harmonized`, `tests.test_live_harmonized_equivalence`, `tests.test_aspect_correction` | B1 | 1 giờ |
| **B4** | V8 `vsl_gh_dataset.py` (§3.4). Trước khi sửa: `git status --porcelain -- src/data/vsl_gh_dataset.py` rỗng. | `('src/data/vsl_gh_dataset.py', 'D-string', '<module>')` | không test mới (guard là test; thay đổi là chữ); liên quan `tests.data.test_vsl_gh_dataset` (so `b0_vslgh.log`), `tests.test_sentence_split_guard` (chỉ CHẠY, không sửa) | B1 | 0.5 giờ |
| **B5** | V1–V6 `realtime_demo.py` (§3.1) + fixture + `TestKnownEmpty` (§3.5). Sau bước này `KNOWN_VIOLATIONS = {}`. | 5 mục `realtime_demo.py` (`C-result _locate_vietnamese_font`, `C-string _open_stream`, `C-string run`, `C-string main`, `D-binding run`) | MỚI `tests/test_realtime_demo_source.py` (AC6), `TestKnownEmpty` trong guard; liên quan `tests.test_realtime` | B2, B3, B4 | 2 giờ |
| **B6** | Đóng. (1) Trên cây sạch với `git status --porcelain -- backend src tests realtime_demo.py start_fullstack.ps1` rỗng (nếu coder 13 đang để dở file trong các đường này → chờ, không commit hộ): `$PY -m tests.test_backend_source_guard --report reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json`; chạy lại ra `_work/_plan11_tmp/b6_rerun.json`, so thân (bỏ `generated_by`) → giống hệt. (2) Lệnh AC7 đầy đủ (33 module) → `b6_ac2_33.log`; so với B0 theo AC7; log so sánh `b6_compare.txt`. (3) Kiểm AC1, AC2, AC8 bằng lệnh §5; chép output vào 11-progress. (4) `detect-changes`; commit `11: B6 — báo cáo guard known=0 + hồi quy` (JSON + 11-progress). Orchestrator gọi vslt-reviewer. KHÔNG sửa `docs/STATE.md`/`docs/progress_log.md`. | — | toàn bộ AC | B5 | 1 giờ |

Tổng: **7 bước, ~8 giờ công** (chưa kể thời gian chạy bộ AC2: theo `13-progress.md` từ ~4 tới ~19 phút mỗi lần). Thứ tự B2/B3/B4
đổi được cho nhau; B5 cuối (mang `TestKnownEmpty`). Mỗi bước tự đứng được: bị ngắt giữa bước → `git status` cho thấy file dở; khôi
phục bằng cách đọc 11-progress (bước cuối đã commit) và làm lại bước dở từ ý 1.

**Ghi chú B0(5) — đếm video thiếu fps (chỉ đọc header, không đọc khung, không mở nhãn).** Coder viết script tạm
`_work/_plan11_tmp/count_fps_metadata.py` (KHÔNG commit), duyệt mọi file `*.mp4|*.avi|*.mov|*.webm|*.mkv` dưới `data/` (bỏ qua thư mục
không tồn tại, ghi tên), với mỗi file `cv2.VideoCapture(p).get(cv2.CAP_PROP_FPS)` rồi `release()`; ghi JSON
`{generated_by{command, git_commit, generated_at_utc}, dirs{<thư mục cấp 2 dưới data/>: {n_videos, n_fps_missing, n_open_failed, examples(≤5 tên file)}}}`
với `n_fps_missing` = số file mở được nhưng giá trị không `> 0` (0, âm, NaN); `n_open_failed` đếm riêng. Số liệu chỉ lấy từ JSON này.

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG đổi; chỉ planner đổi, ghi lý do)

**AC1 — Phạm vi file.** Gọi C11 = tập commit `git log --format=%H P11..HEAD -E --grep="^(WIP )?11:"`. Hợp các file trong
`git show --name-status --format= <c>` với c ∈ C11 ⊆ {`M realtime_demo.py`, `M src/inference/sign_segmenter.py`,
`M src/data/landmark_extractor.py`, `M src/data/vsl_gh_dataset.py`, `M tests/test_backend_source_guard.py`,
`A tests/test_realtime_demo_source.py`, `A tests/test_guard_dod7_fixes.py`, `A reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json`,
`A|M docs/plans/11-progress.md`}. Không commit nào của C11 chạm: `backend/`, `frontend/`, `scripts/`, `kaggle/`, `configs/`,
`run_core.py`, `README.md`, `docs/STATE.md`, `docs/progress_log.md`, `docs/reviews/*`, file của kế hoạch 13 (§2.4), `checkpoints/`,
`data/`; không file `.pt/.npz/.npy/.mp4/.log/.png`. 3 dòng ` D` của người dùng còn nguyên, chưa staged. Mọi commit của coder 11 có
tiền tố `11:`/`WIP 11:`.

**AC2 — Không nới guard, không sửa test cũ (P2: ngoại lệ có tên).**
- (a) `git show P11:tests/test_backend_source_guard.py` và bản HEAD: phần từ dòng 1 tới hết dòng NGAY TRƯỚC `KNOWN_VIOLATIONS = {`
  giống hệt từng byte (lệnh: script `_work/_plan11_tmp/ac2_prefix.py` so 2 chuỗi, in `PREFIX_IDENTICAL True`); phần từ dòng sau dấu
  `}` đóng khối KNOWN tới dòng `if __name__ == "__main__":` ở P11 xuất hiện NGUYÊN VẸN, liền mạch trong bản HEAD (cùng script, in
  `BODY_PRESERVED True`); khối `if __name__ …` tới cuối file giống hệt.
- (b) `git diff P11 HEAD -- tests/test_backend_source_guard.py`: mọi dòng `-` (trừ `---`) nằm trong khối KNOWN tại P11 (`:211-235`
  theo HEAD f7717a9); dòng `+` chỉ là `KNOWN_VIOLATIONS = {}` (+ ≤ 2 dòng comment) và các lớp/hàm mới của §3.5.
- (c) `git diff P11 HEAD -- tests/ ':(exclude)tests/test_backend_source_guard.py'` chỉ có file mới (`new file mode`), 0 dòng `-` (trừ `---`).
- (d) `git grep -n -E "skip|expectedFailure" -- tests/test_realtime_demo_source.py tests/test_guard_dod7_fixes.py` → 0 dòng; các lớp
  mới trong guard không dùng skip.
- (e) `git grep -n -i -E "guard *: *allow|noqa.*guard" -- src backend realtime_demo.py` → 0 dòng.

**AC3 — Guard xanh, 0 vi phạm (DoD 7 backend).**
- `$PY -m unittest tests.test_backend_source_guard -v` chạy 2 lần: cả hai `OK`, 0 skip, 0 failure, 0 error; số test = số ở B0 + 5
  (4 của `TestRegistryBaseline` + 1 của `TestKnownEmpty`); có dòng in `[DoD7-guard] known=0 allowed=<m>` với `<m>` = tổng count
  `ALLOWED` (không đổi so với B0); `test_known_violations_empty ... ok`.
- Báo cáo B6 `reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json`: `generated_by.code_dirty == false`; `generated_by.git_commit`
  là tổ tiên của HEAD và `git diff <git_commit> HEAD -- backend src tests realtime_demo.py start_fullstack.ps1` rỗng;
  `summary.by_status.known == 0`, `summary.by_status.unregistered == 0`, `summary.by_status.allowed == <m>`.
  Tập `(path, rule, qualname) → count` của finding `allowed` == tập đó trong `b0_guard.json` (ALLOWED không đổi).
  `scope.serving_files` và `scope.main_files` == của `b0_guard.json`; nếu khác, mọi khác biệt phải do commit KHÔNG thuộc C11
  (chứng minh bằng `git log --format="%h %s" P11..HEAD -- <file>`).
- Chạy báo cáo 2 lần, thân (bỏ `generated_by`) giống hệt. Không có đường dẫn tuyệt đối trong file (đã có `TestReportMode`).

**AC4 — V9: SignSegmenter bằng hệt (`tests/test_guard_dod7_fixes.py::TestSegmenterSingleFrame`, không cần dữ liệu).**
- (a) Với cửa sổ T = 1 dựng trong test (≥ 3 ca: tay giơ cao trên `rest_y`; tay hạ thấp; không có tay), `hand_activity(*_normalise(k, v,
  aspect), fps, cfg)` cho kết quả GIỐNG HỆT (`np.array_equal`) với `fps ∈ {0.0, 30.0, 1000.0}` — dùng hàm thật của `src/data/harmonized.py`.
- (b) Một luồng frame dựng trong test (seed cố định: `np.random.default_rng(0)` trong test; khoảng cách frame KHÔNG đều; có ≥ 1 khoảng
  hở > `stream_gap_s` để `_hist` bị xóa → nhánh n = 1 xảy ra giữa luồng; có 1 lần `reset()`; có ≥ 1 `Emit`) đẩy qua `SignSegmenter`
  và qua lớp con CỤC BỘ TRONG TEST có `_activity` là bản chép NGUYÊN VĂN mã P11 (`:136-144`, gồm `else 30.0`): dãy `hand_active`
  từng frame, `state` từng frame, và dãy sự kiện (kiểu, `segment_id`, `reason`, `frames`, `kps`/`vis`/`t` bằng hệt) GIỐNG HỆT.
  Test assert nhánh n = 1 thật sự được chạy ≥ 2 lần (đếm bằng spy trong lớp con).
- (c) `tests.test_sign_segmenter`, `tests.test_harmonized_live`, `tests.test_ws_live_contract`: từng test cùng trạng thái như B0.
- (d) Bằng chứng đỏ trước: `b2_red_guard.txt` có đúng 1 dòng `unregistered` `src/inference/sign_segmenter.py:<dòng>: D-binding
  [SignSegmenter._activity]` và không finding nào khác.

**AC5 — V7: fps của extractor (`TestExtractorFps`, `TestHarmonizeUnknownFps`, không cần dữ liệu, không chạy MediaPipe).**
- (a) Thay `src.data.landmark_extractor.cv2.VideoCapture` bằng lớp giả trong test (mở được, `CAP_PROP_FPS` trả giá trị cho trước,
  `read()` trả `(False, None)` ngay; file video là file rỗng tạo trong thư mục tạm để qua `os.path.exists`): giá trị
  `0.0`, `-1.0`, `NaN` → `result["fps"] == 0.0`; `29.97`, `25.0`, `30.0` → đúng giá trị đó (`assertEqual`); `extract_frame` không
  được gọi (spy). Ca `0.0` FAIL trên mã P11 (trả 25.0) — log `b3_red_tests.txt`.
- (b) `harmonize(kps, vis, aspect, 0.0, cfg)` và `harmonize(kps, vis, aspect, 30.0, cfg)` (kps/vis dựng trong test, `cfg` =
  `HARMONIZED_DEFAULT`, có `trim` và `mask_resting_hand` như mặc định) cho 3 mảng GIỐNG HỆT → "0.0 = để module tiền xử lý chung quyết
  định" là đúng với mã hiện tại (characterization; PASS cả trước và sau).
- (c) `tests.test_harmonized`, `tests.test_live_harmonized_equivalence`, `tests.test_aspect_correction`: cùng trạng thái như B0.
- (d) `b0_fps_metadata.json` tồn tại, có `generated_by`, và điều kiện §7.1 điểm 2 đã được xét (ghi kết quả vào 11-progress).
- (e) Bằng chứng đỏ trước guard: `b3_red_guard.txt` đúng 1 finding `unregistered` của nhóm này.

**AC6 — V1–V6 + fixture mock (`tests/test_realtime_demo_source.py`, không cần checkpoint/dữ liệu/webcam, chạy < 30 s).**
- R1: `RealtimeDemo(source="mock", headless=True)` (phụ thuộc nặng đã thay, §3.1) — `_open_stream()` ném `FileNotFoundError`
  (cwd = thư mục tạm không có file `mock`). FAIL trên mã P11.
- R2: `main()` với argv `["realtime_demo.py", "--help"]` → `SystemExit` mã 0; stdout không chứa `mock` (không phân biệt hoa thường).
  FAIL trên mã P11.
- R3: `run()` với `_open_stream` trả `SyntheticFrameSource(5)`, headless, `max_frames=None`: `process_frame` của pipeline giả được gọi
  ĐÚNG 5 lần, mỗi khung shape `(720, 1280, 3)`, dtype `uint8`, `frame[360, 640]` == `(60, 60, 60)` và `frame[0, 0]` == `(0, 0, 0)`;
  `release()` của nguồn và `close()` của pipeline được gọi; lớp thật `VSLPredictor`/`VSLTranslator`/`RealtimeLandmarkExtractor` KHÔNG
  được dựng (spy). Trên mã P11 ca này có thể PASS hoặc ERROR `ZeroDivisionError` (pipeline giả trả ngay → `dt` theo `time.time()` có
  thể bằng 0, chính là lỗi V5) — ghi kết quả thực tế vào log đỏ, không bắt buộc chiều nào; sau sửa phải PASS.
- R4: như R3 với `max_frames=2` → đúng 2 lần `process_frame`.
- R5: `mean_fps([]) == 0.0`; `mean_fps([0.0, 0.0]) == 0.0`; `mean_fps([float("nan")]) == 0.0`;
  `mean_fps([0.02, 0.04])` ≈ `1 / 0.03` (`assertAlmostEqual`, places=9). ERROR trên P11 (chưa có hàm).
- R6: `format_fps(0.0) == format_fps(-1.0) == format_fps(float("nan")) == "-- FPS"`; `format_fps(29.96) == "30.0 FPS"`;
  `RealtimeHUD().draw_hud(np.zeros((720, 1280, 3), np.uint8), {}, {}, "X", fps=0.0, latency_ms=0.0)` trả ndarray cùng shape và
  gọi `format_fps` với `0.0` (spy qua `mock.patch.object(realtime_demo, "format_fps", wraps=…)`). ERROR trên P11.
- R7: `inspect.signature(RealtimeDemo.__init__)` có đúng các tham số `self, source, model_type, headless, max_frames, draw_skeleton`
  với mặc định như P11; `inspect.signature(RealtimeHUD.draw_hud)` không đổi so với P11 (so bằng chuỗi ghi trong test).
- R8: `git grep -n "SyntheticFrameSource" -- . ':(exclude)tests/'` → 0 dòng; `git grep -n -i "mock" -- realtime_demo.py` → 0 dòng.
- `git diff P11 HEAD -- run_core.py scripts/` rỗng.

**AC7 — Hồi quy = mốc.**
Lệnh B0 (31 module, nguyên văn `docs/plans/06-viec5-frontend.md:1028`, thay `.venv/Scripts/python` bằng `$PY` nếu cloud):
`PYTHONIOENCODING=utf-8 $PY -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_archive_private_kaggle_r05 tests.test_backend_source_guard -v`
Lệnh B6 (33 module) = lệnh trên + `tests.test_realtime_demo_source tests.test_guard_dod7_fixes`.
- So theo module (đếm ok/FAIL/ERROR/skip): 30 module cũ (trừ guard) GIỐNG HỆT B0; `tests.test_backend_source_guard` = B0 + 5 test, tất
  cả ok; 2 module mới: tất cả ok, 0 skip.
- Tập id test không-ok ở B6 ⊆ tập ở B0 (`b0_nonok.txt`). Các mục không-ok có sẵn được chấp nhận CHỈ khi có ở B0: ERROR `setUpClass
  (tests.test_translation_core.TestVSLTranslationCore)` (thiếu ViT5), skip `stgcn_best.pt not found`.
- Luật test chập chờn có sẵn (`13-progress.md:399-410`): nếu `tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs`
  FAIL ở B6 với ĐÚNG thông điệp `[1, 1, 1, 0] != [1, 1, 1, 1]` → chạy `$PY -m unittest tests.test_hand_landmarks_ws -v` riêng 3 lần,
  phải OK cả 3 → ghi "chập chờn có sẵn, không do 11" kèm 3 log; khác thông điệp hoặc không OK đủ 3 lần → AC7 FAIL. Không sửa/skip test đó.
- Nếu `checkpoints/` khác `b0_ckpt.txt` (kế hoạch 13 B11 đặt checkpoint giữa chừng): test trước ERROR/skip nay chạy phải ok; nếu
  FAIL → DỪNG, báo (§7.1 điểm 4) — không tính là đạt.
- `tests.data.test_vsl_gh_dataset` (ngoài 31 module, file bị sửa ở B4): từng test cùng trạng thái như `b0_vslgh.log`.
- `git status --porcelain` trước/sau mỗi lần chạy bộ test giống hệt.

**AC8 — Quy trình.**
- 11-progress có output `impact` (risk, caller) cho mọi symbol §3.6 TRƯỚC commit sửa symbol đó; HIGH/CRITICAL có dòng CẢNH BÁO.
- Mọi commit C11 có dòng `detect-changes: risk=…` trong message; không `--amend`, rebase, force-push.
- Mỗi commit C11 (trừ `WIP 11: B0`) có trong 11-progress dòng output `$PY -m unittest tests.test_backend_source_guard` = `OK` tại commit
  đó (không commit nào để guard đỏ); dòng `[DoD7-guard] known=` giảm đơn điệu qua các bước: B0/B1 = 9, sau B2 = 8, sau B3 = 7, sau B4 = 6,
  sau B5 = 0 (nếu B2–B4 đổi thứ tự thì dãy tương ứng, vẫn giảm đúng count của nhóm đã sửa).
- Có các log "đỏ trước" của B2–B5 (`<bước>_red_tests.txt`, `<bước>_red_guard.txt`) và đường dẫn ghi trong 11-progress.

**AC9 — Bằng chứng và báo cáo.** 11-progress chứa: P11; tóm tắt B0 (Ran/failures/errors/skipped + id không-ok, chép từ log);
`b0_guard.json` summary; `b0_fps_metadata.json` tóm tắt (chép từ JSON); từng bước: impact, log đỏ, log xanh, commit; bảng so sánh AC7
theo module; đường dẫn + `git_commit` của báo cáo B6. Câu kết luận DoD 7 backend chỉ được viết dạng "guard: known = 0 (theo
`reports/guard_dod7_<D>/guard_findings.json`, commit <hash>)" kèm giới hạn §6 R6 (known = 0 là điều kiện cần, không đủ).

## 6. Rủi ro dữ liệu / ML và kỹ thuật

- **R1 — Lệch train↔realtime do V7.** Đổi `25.0 → 0.0` chỉ đổi metadata npz của video THIẾU fps khi trích LẠI (harmonize dùng 30.0 thay
  25.0). Npz đã có (Kaggle, `data/processed`) không đổi; đường live (`harmonized_live`, `sign_segmenter`) dùng timestamp thật, không
  dùng hàm này ⇒ không lệch train↔realtime hiện hành. Giảm thiểu: B0 đếm số video thiếu fps; > 0 → DỪNG (§7.1-2).
  Đọc header video TEST chỉ để đếm metadata (không xem nhãn, không chạy model) — không phải "đo trên TEST".
- **R2 — V9 đổi hành vi segmenter.** Đã chứng minh độc lập fps khi T = 1; AC4 kiểm bằng hệt so với bản chép mã cũ trên luồng có
  nhánh n = 1. Rủi ro còn: kế hoạch 08 viết lại hàm và đưa lại `30.0` → guard đỏ ⇒ cần Lần sửa 08 (§7.2).
- **R3 — "Né luật" thay vì sửa.** V1 (đổi tên) và V8 (đổi câu) là sửa ngữ nghĩa có lý do (§3.1c, §3.4); §3.0 ý 2 liệt kê cách né bị
  cấm; reviewer kiểm bằng diff (mỗi sửa ≤ vài dòng). Không dùng ALLOWED, không chuyển mã ra ngoài phạm vi (trừ fixture theo quyết
  định người dùng).
- **R4 — Song song với kế hoạch 13.** (a) Kernel K2 dùng commit ghim → không ảnh hưởng. (b) `code_dirty` của bước đánh giá 13 B11:
  mọi bước 11 kết thúc bằng commit; không để file dở. (c) `vsl_gh_dataset.py` là file 13 đã sửa: B4 chỉ đổi 1 dòng chữ, kiểm
  `git status` trước. (d) Câu chữ AC0(e) của 13 ("không file tracked cũ nào bị sửa trừ …", `13-train-lai-checkpoint-thieu.md:519-525`)
  nếu đọc theo `git diff <mốc B0 của 13> HEAD` sẽ thấy file của 11 → cần planner 13 giới hạn theo commit `^(WIP )?13:` (§7.2).
  (e) Commit bằng `git commit -- <paths>` để không cuốn file coder 13 đã stage (tiền lệ sự cố modal_runner, STATE).
- **R5 — Test chập chờn có sẵn** `test_reset_segments_and_graphs`: luật xử lý cố định ở AC7, không sửa/skip.
- **R6 — Giới hạn guard (K3 review 10).** `known = 0` chỉ là điều kiện cần của DoD 7: guard không giải import động, không quét
  `scripts/` đo/báo cáo (ví dụ `scripts/generate_slide_images.py:60` `fps=28.5`), không hiểu ngữ nghĩa. Báo cáo cuối phải ghi rõ.
- **R7 — Test realtime_demo nạp nặng.** Import `realtime_demo` kéo `cv2`, `PIL`, `torch` (qua `src.inference.predictor`) — có trong
  `.venv`; test phải thay lớp nặng để không nạp checkpoint/ViT5/MediaPipe (AC6 R3 spy). Nếu sau 13 B11 có checkpoint thật, test vẫn
  không được nạp (spy bảo đảm).
- **R8 — Mã hóa console Windows.** Chuỗi FPS mới là ASCII (`-- FPS`).
- **Dữ liệu/ML khác:** không train, không đánh giá model, không split mới, không đụng TEST cho số liệu → rò rỉ/cỡ mẫu/CI: N/A. Nguồn
  gốc: JSON guard (có `generated_by`) và JSON đếm fps (có `generated_by`), không gõ số tay.

## 7. Điểm dừng

**Không có điểm CẦN NGƯỜI DÙNG trước khi code.** Lý do: quyết định gỡ `--source mock` đã có (2026-10-02 16:15); không đổi model mặc
định; không xóa file nào (chỉ sửa; fixture là file test mới); không đổi API backend công khai (không đụng `backend/`); không chạm
thay đổi chưa commit của người dùng (3 file ` D` trong `data/`); không hành động không hoàn tác (mọi thay đổi là commit thường).

### 7.1 Điểm dừng có điều kiện (coder DỪNG, ghi 11-progress, báo orchestrator)
1. B0: `b0_guard.json` có `unregistered > 0`, hoặc tập khóa/count `known` khác 8 nhóm/9 finding của §2.2 → CẦN PLANNER (kế hoạch lập
   trên sổ cũ).
2. B0(5): `n_fps_missing > 0` hoặc `n_open_failed > 0` ở bất kỳ thư mục dữ liệu nào → KHÔNG làm B3, CẦN PLANNER (planner xét có giữ
   cách sửa §3.2 không; nếu thay đổi làm đổi dữ liệu train khi trích lại thì có thể thành câu hỏi người dùng). B2, B4 vẫn làm được;
   B5 làm được nhưng `TestKnownEmpty` chỉ thêm khi KNOWN thật sự rỗng.
3. Một cách sửa ở §3 vẫn sinh finding mới (`unregistered`) mà không viết lại được trong khuôn §3.0 → CẦN PLANNER (không ALLOWED, không
   đổi tên né luật).
4. Test cũ đổi trạng thái so với B0 ngoài luật AC7 (kể cả test mới chạy được do checkpoint vừa đặt mà FAIL) → dừng, báo.
5. `git status --porcelain` cho thấy thay đổi chưa commit của người khác ở file sắp sửa (`src/inference/sign_segmenter.py`,
   `src/data/vsl_gh_dataset.py`, `realtime_demo.py`, `src/data/landmark_extractor.py`, `tests/test_backend_source_guard.py`), hoặc
   coder 08 đang làm B1 → chờ/đổi thứ tự bước; không sửa đè, không commit hộ.
6. `impact` trả CRITICAL cho symbol sắp sửa → dừng, CẦN PLANNER (HIGH: ghi cảnh báo, làm tiếp nếu mọi caller đã được liệt kê và test).

### 7.2 Việc CẦN PLANNER cho kế hoạch khác (không chặn kế hoạch 11; orchestrator xếp)
- **Kế hoạch 08 (Lần sửa, trước khi code 08):** §3.2 dòng `n = 1: fps_last = 30.0` (`08-segmenter-live.md:152`) → dùng quy ước `0.0`
  như §3.3 ở đây (sau 11, guard có `TestKnownEmpty` nên 08 không thể đăng ký finding); AC-T của 08 thêm `tests.test_archive_private_kaggle_r05`
  (P1), `tests.test_backend_source_guard`, `tests.test_realtime_demo_source`, `tests.test_guard_dod7_fixes`;
  P2 cho 08 không còn cần ngoại lệ sửa sổ KNOWN (sổ đã rỗng) — thay bằng "guard xanh, không thêm khóa KNOWN/ALLOWED".
- **Kế hoạch 13:** câu chữ AC0(e)/AC1 so `git diff <mốc B0 của 13> HEAD` → giới hạn theo commit `^(WIP )?13:` (tiền lệ kế hoạch 06
  Lần sửa 2), để commit của 11 không làm AC của 13 đỏ giả.
- **Kế hoạch 07 (P3 review cloud):** tiêu chí "guard xanh, không thêm khóa KNOWN/ALLOWED" nay được máy kiểm bởi `TestKnownEmpty` +
  `TestRegistryBaseline`.
- Backlog (orchestrator): `README.md:203`/`realtime_demo.py:8` hướng dẫn `--webcam` không tồn tại (việc 8); `generate_slide_images.py:60`
  `fps=28.5` (guard scripts, backlog).
