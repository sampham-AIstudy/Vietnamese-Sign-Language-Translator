# Kế hoạch 06 — tiến độ (coder; chặng 1: B0–B2; chặng 2: B3–B4; chặng 3: B5–B7; chặng 4: B8–B9)

- P6 = 797d0af (HEAD lúc coder bắt đầu B0, commit đã chứa kế hoạch 06)
- Bước đã xong: B0 (8e7b09b), B1 (4924502), B2 (ed5c4c9), B3 (e58d025 + 5fcf295), B4 (026f474), B5 (34a527d), B6 (0328c1b), B7 (commit "06: B7 — ...")
- Bước đang làm: **B8c ĐANG LÀM** (Lần sửa 3, §0C.5; commit kế hoạch 717aa3e). B8b-1 xong (302072c), B8b-2 xong (eb379fa);
  B8b-3 đã dừng §7-8 (1a4e182) — phần chạy chính thức chuyển sang B8c. Chưa ghi đè `reports/e2e_2026-09-29/*.json`.
- Bước còn lại: B8c-1 (test AC12-t mục 10) → B8c-2 (e2e_browser.cjs 3 trường thời gian + vai trò path +
  `tab_unmounted_socket_rule`) → B8c-3 (chạy chính thức 3 kịch bản, mỗi kịch bản đúng 1 lần) → B9b.

## B0 (P6 = 797d0af, 2026-09-29)

Commit mở file tiến độ: 050d337 (chỉ `docs/plans/06-progress.md`).

1. `git status --porcelain` → `../_plan06_tmp/b0_status_porcelain.txt` (66 dòng; 3 dòng ` D` của người dùng + untracked).
2. AC2 mốc, 25 module cũ (log `../_plan06_tmp/b0_ac2.log`):
   `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest <25 module của AC2, không có 4 module mới> -v`
   → `Ran 383 tests in 398.220s` / `OK`, 0 skip, 0 fail, 0 error.
   Theo module (`loadTestsFromName(...).countTestCases()`, `../_plan06_tmp/b0_counts.txt`):
   alphabet_preprocessing 6, aspect_correction 3, realtime 3, split_guards 6, translation_core 8, vsl_system 6,
   ws_throughput 0, fingerspelling_api 11, unified_split_integrity 4, report_step4 105, fingerspelling_limits 48,
   fingerspelling_compose 28, fingerspelling_deployed 9, alphabet_ckpt_provenance 16, harmonized 6, sign_segmenter 15,
   harmonized_live 10, ws_live_contract 18, live_harmonized_equivalence 9, archive_step4_kaggle 24, status_privacy 5,
   backend_model_unavailable 5, ws_dropped_frames 3, archive_private_kaggle 27, private_artifacts 8 — TỔNG 383.
   `git status --porcelain` sau khi chạy: giống hệt file trước (`diff` rỗng → in `SAME`).
3. `node --version` → `v25.9.0`. `cd frontend && npm ls --depth=0` (exit 0) → `../_plan06_tmp/b0_npm_ls.txt`
   (16 gói: @fontsource/dm-sans@5.3.0, @fontsource/epilogue@5.3.0, @types/react-dom@18.3.7, @types/react@18.3.31,
   @vitejs/plugin-react@4.7.0, autoprefixer@10.5.6, clsx@2.1.1, lucide-react@0.475.0, postcss@8.5.28,
   puppeteer-core@25.10.0, react-dom@18.3.1, react@18.3.1, tailwind-merge@3.6.0, tailwindcss@3.4.19,
   typescript@7.0.2, vite@6.4.3).
4. Edge: `ls -l "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"` → tồn tại (5001808 byte).
   → Điểm dừng §7-4 KHÔNG kích hoạt.
5. `.venv/Scripts/python -c "import mediapipe; print(mediapipe.__version__)"` → `0.10.14`.
6. GitNexus: `node .gitnexus/run.cjs analyze --index-only` (OK; cảnh báo FTS/BM25 build lỗi — chỉ ảnh hưởng tìm theo từ khóa).
   `impact <s> --direction upstream` (`../_plan06_tmp/b0_impact.txt`):
   - `websocket_live_stream`: risk UNKNOWN (0 caller resolve). Text search: route WS, gọi qua URL `/ws/live-stream` từ
     `frontend/src/components/{Phase12Pipeline,RealtimeStream}.jsx`, `scripts/smoke_test_phase12.py`, và tests
     `test_backend_model_unavailable`, `test_fingerspelling_limits`, `test_live_harmonized_equivalence`,
     `test_ws_live_contract`, `test_ws_throughput`.
   - `_parse_ws_message`: risk LOW (direct 1: `receive_loop` trong `websocket_live_stream`; 2 process).
   - `_decode_frame`: risk LOW (direct 2: `_process_frame_worker`, `_process_frame_worker_harmonized`/`run_harmonized`).
   - `health`: risk UNKNOWN (0 caller resolve). Text search `/api/health`: `frontend/src/App.jsx`,
     `tests/test_backend_model_unavailable.py`, `tests/test_ws_live_contract.py`. B0–B2 không sửa `health`.

## B1 — CORS / Origin / bind (§3.5, AC3)

- impact trước khi sửa: `websocket_live_stream` UNKNOWN (text search ở B0: route WS, gọi qua URL từ frontend, smoke,
  5 module test). CORS middleware, `uvicorn.run` là mã cấp module (không có symbol trong đồ thị) — text search:
  `grep -n "0\.0\.0\.0\|allow_origins\|Origin" backend/main.py` → chỉ `:330 allow_origins=["*"]` và `:1519 uvicorn.run(... "0.0.0.0" ...)`.
  Không test cũ nào kiểm header CORS/Origin (`grep -i "access-control\|origin" tests/*.py` chỉ ra chữ "origin" trong
  ngữ cảnh khác). TestClient không gửi header Origin → các test WS cũ đi nhánh "không có Origin → cho qua".
- Test viết trước: `tests/test_cors_origin_bind.py`. Chạy TRƯỚC khi sửa: `Ran 18 tests` `FAILED (failures=13, errors=12)`
  (errors: `parse_cors_origins`/`DEFAULT_DEV_ORIGINS`/`ws_origin_allowed` chưa có; failures: bind, CORS header, WS Origin).
  Trong B1 `WS_PATHS = ("/ws/live-stream",)`; phần `/ws/hand-landmarks` của AC3-d/e thêm ở B2 cùng endpoint.
- Sửa: `backend/main.py` (`DEFAULT_DEV_ORIGINS`, `parse_cors_origins`, `ALLOWED_ORIGINS`, `ws_origin_allowed`,
  `CORSMiddleware(allow_origins=list(ALLOWED_ORIGINS), allow_credentials=False, allow_methods=["GET","POST"],
  allow_headers=["Content-Type"])` ở đúng vị trí cũ (CORS vẫn ngoài cùng), `_ws_check_origin` + `WS_CLOSE_POLICY_VIOLATION
  = 1008` gọi TRƯỚC `accept()` trong `websocket_live_stream`, `uvicorn.run(host="127.0.0.1")`);
  `start_fullstack.ps1` chỉ `--host 0.0.0.0` → `--host 127.0.0.1`; `frontend/vite.config.js` `strictPort: true` cho
  `server` và `preview` (không khóa `host`). `node --check frontend/vite.config.js` → OK.
- Sau khi sửa: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_cors_origin_bind tests.test_ws_live_contract
  tests.test_fingerspelling_limits tests.test_fingerspelling_api tests.test_ws_dropped_frames tests.test_backend_model_unavailable
  tests.test_live_harmonized_equivalence tests.test_status_privacy -v` → `Ran 117 tests in 165.445s` `OK`, 0 skip
  (cors_origin_bind 18 mới; ws_live_contract 18, fingerspelling_limits 48, fingerspelling_api 11, ws_dropped_frames 3,
  backend_model_unavailable 5, live_harmonized_equivalence 9, status_privacy 5 = như B0).
- detect-changes --scope all (sau analyze --index-only): risk **medium**, 7 symbol (DEFAULT_DEV_ORIGINS, parse_cors_origins,
  ALLOWED_ORIGINS, ws_origin_allowed, WS_CLOSE_POLICY_VIOLATION, _ws_check_origin, websocket_live_stream), 4 process
  (đều bắt đầu từ websocket_live_stream).

## B2 — `src/inference/hand_live.py` + `WS /ws/hand-landmarks` (§3.3, AC4; phần hand-landmarks của AC3-d/e)

- impact: các symbol B2 đều MỚI (`HandLandmarkSession`, `LEVEL1_HANDS_KWARGS`, `extractor_info`, `_hand_session_info`,
  `_hand_frame_worker`, `websocket_hand_landmarks`); dùng lại không sửa `_parse_ws_message` (LOW), `_decode_frame` (LOW),
  `_ws_error`, `_ws_check_origin` (B1), `THREAD_POOL`. Trong `backend/main.py` chỉ thêm 1 dòng docstring module, 1 dòng
  import, và khối endpoint mới trước `if __name__`. `scripts/extract_hands_batch.py` KHÔNG sửa.
- Dữ liệu: `manifest.csv` có 686 dòng, cột `mediapipe_version` = {`0.10.14`} (1 giá trị) → §7-6 KHÔNG kích hoạt.
  `a_hau_A_001.mp4` có cục bộ (185716 byte).
- Test: `tests/test_hand_landmarks_ws.py` (AC4 a–g, 9 test, MediaPipe thật CPU); `tests/test_cors_origin_bind.py`
  thêm `/ws/hand-landmarks` vào AC3-d (HandLandmarkSession vá MagicMock, `assert_not_called`) và lớp AC3-e hand-landmarks
  (Origin localhost:3000, 127.0.0.1:3000, không Origin → `session_info`), 18 → 21 test.
  Test viết cùng lúc với code (không chạy trước khi có code). Kiểm đột biến thay cho bằng chứng "đỏ trước":
  `min_detection_confidence` 0.5→0.7 trong hand_live → `FAIL test_kwargs_equal_training_extractor` (1/9);
  bỏ `self.close()` trong `reset()` → `FAIL test_reset_segments_and_graphs` (1/9); file đã khôi phục (`cmp` OK).
- `.venv/Scripts/python -m unittest tests.test_hand_landmarks_ws tests.test_cors_origin_bind -v` → `Ran 30 tests in 2.006s` `OK`;
  in `a_hau_A_001: frame 0 (first detected by _extract_one), handedness Left`.
- AC2 (25 module cũ + 2 module mới đã có), log `../_plan06_tmp/b2_ac2.log`:
  `Ran 413 tests in 193.855s` `OK`, 0 skip (= 383 của B0 + cors_origin_bind 21 + hand_landmarks_ws 9).
  `git status --porcelain` trước/sau khi chạy: giống hệt (`SAME`).
- detect-changes --scope all (sau analyze --index-only): risk **HIGH** — theo luật ">15 symbol": 17 symbol, tất cả là
  symbol MỚI của B2 (backend: HAND_WS_PROTOCOL_VERSION, _hand_session_info, _hand_frame_worker, websocket_hand_landmarks,
  hàm lồng `unavailable`, biến cục bộ `session`) và test mới của kế hoạch này (tests/test_cors_origin_bind.py); không symbol
  cũ nào bị sửa (`websocket_live_stream` không nằm trong danh sách). 6 process, đều bắt đầu từ
  `websocket_hand_landmarks`/`_hand_frame_worker`.

## B3 — tương đương Cấp 1 train↔live (AC5) + báo cáo lệch nguồn (AC6)

- impact: không sửa symbol cũ nào; file mới `scripts/hand_live_check.py` (helper dùng chung: `select_clips`,
  `video_path_for`, `offline_extract` gọi `_extract_one` import nguyên văn, `live_hand_frames` qua TestClient WS,
  `body_from_hand_frames` = bản Python của buildSequenceBody §3.2, `body_from_npz`) và `tests/test_hand_live_equivalence.py`.
- Kích thước message: PNG data URL lớn nhất của 2 clip qipedc 1280×720 = 375494 byte (< 1048576) → gửi được qua text.
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_hand_live_equivalence -v` → `Ran 4 tests in 36.881s` `OK`
  (0 skip). **AC5-a bằng hệt trên cả 10 clip** (landmark `np.array_equal` float32, detected, nhãn, score) → §7-1 KHÔNG kích hoạt.
  Output in (d):
  `[AC5] hauuto candidates with local video: 640`;
  hauuto_a_tai_B_001 frames=45 detected=45; hauuto_aa_khoi_B_002 91/87; hauuto_aw_khoi_A_003 90/84; hauuto_ee_vy_A_002 90/90;
  hauuto_h_khoi_A_001 91/77; hauuto_oo_vy_A_003 91/91; hauuto_s_hau_B_002 74/74; hauuto_tone_x_khoi_B_002 90/86;
  qipedc_D0489 93/45; qipedc_D0490B 89/51.
- Commit code B3: e58d025. Sau đó (code sạch: `git status --porcelain -- src scripts backend tests frontend` rỗng) chạy AC6:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0 --out reports/fingerspell_live_2026-09-29/hand_live_check.json`
  → `wrote ...: 10 clips; live_png == local offline (detected): 10/10`; `generated_by.git_commit` = e58d025…, `code_dirty: false`.
  Chạy lại lần 2 ra `../_plan06_tmp/hlc_run2.json`: phần thân (bỏ `generated_by`) giống hệt lần 1 (`body identical: True`).
  Tóm tắt (đọc từ JSON, chỉ ghi nhận, không có ngưỡng): live_png vs offline cục bộ: detected_equal 10/10, max_abs_diff 0.0 cả 10;
  jpeg90 vs png: detected_agree < n_frames ở 2 clip (aw_khoi_A_003 86/90, qipedc_D0489 87/93), max_abs_diff_both lớn nhất 0.2403
  (aw_khoi_A_003); Kaggle npz vs offline cục bộ: n_frames_equal 10/10, detected_agree < n_frames ở 1 clip (aw_khoi_A_003 88/90),
  max_abs_diff_both lớn nhất 0.2298 (aw_khoi_A_003); sequence_top1 live_png = live_jpeg90 = kaggle_npz ở cả 10 clip.

## B4 — thư viện JS thuần + `node --test` + guard + test chéo ngôn ngữ (AC7, AC8)

- File mới: `frontend/src/lib/ws.js` (`wsUrl`, `nowMs`), `frontend/src/lib/liveProtocol.js` (`initialLiveState`,
  `reduceLive`, `undoLastWord`, `discardReasonText`), `frontend/src/lib/fingerspelling.js` (FS_TARGET_FPS 24,
  FS_JPEG_QUALITY 0.9, FS_MAX_IN_FLIGHT 2 — "giá trị thiết kế, chưa đo"; `buildSequenceBody` ném `SequenceBodyError`
  code ∈ {empty, too_many_frames, frame_size_changed, bad_timestamps}; `recordingStats`, `errorDetailText`);
  `frontend/tests/{ws,liveProtocol,fingerspelling}.test.mjs`, `frontend/tests/build_body_cli.mjs`;
  `tests/test_frontend_contract.py`. `frontend/package.json`: CHỈ thêm `scripts.test`. `package-lock.json` không đổi.
  Chưa component nào import lib (B5/B6).
- **Lệch với kế hoạch (cần planner):** lệnh `node --test tests/` của bảng B4/AC2 KHÔNG chạy được với Node v25.9.0:
  `cd frontend && node --test tests/` → `✖ tests ... MODULE_NOT_FOUND` (Node ≥ 22 coi đối số là glob/đường dẫn file, không
  duyệt thư mục). Đã dùng `"test": "node --test tests/*.test.mjs"` (Node tự mở glob; chạy được cả cmd.exe lẫn sh).
  `cd frontend && npm test` → `tests 26, pass 26, fail 0` (ws 4, liveProtocol 12, fingerspelling 10);
  `node --test` (không đối số, mẫu mặc định) cũng ra 26/26.
- `tests.test_frontend_contract` (6 test): TestGuardSelfCheck 3 OK; TestHandLiveCheckReport OK; TestCrossLanguageBody OK
  (in `[AC7-d] hauuto_a_tai_B_001: frames=45 with_hand=45`; body JS == body Python từ npz offline, POST 200, response bằng
  hệt); **TestFrontendSourceGuard.test_no_violation FAIL (đỏ có chủ đích, test viết trước cho B5/B6)** — 14 vi phạm:
  Fingerspelling.jsx:69 ('/api/fingerspelling'), :130 (25 lớp); Navbar.jsx:71 (:8000); Phase12Pipeline.jsx:8, :52 (×2), :98 (×2),
  :129 (base64 /9j/), :201 (bufferCapacity={60}); PredictionDisplay.jsx:81 (:8000); RealtimeStream.jsx:143 (:8000, ws://), :203 (:8000).
  **Mâu thuẫn cần planner:** `RealtimeStream.jsx:203` có ":8000" trong câu báo lỗi (không phải dòng URL), nhưng AC1 chỉ cho
  sửa "dòng URL + 1 dòng import" của file này → AC8 và AC1 không thể cùng đạt nếu không nới một trong hai.
- AC2 (25 module cũ + 4 mới), log `../_plan06_tmp/b4_ac2.log`: `Ran 423 tests in 281.254s` `FAILED (failures=1)` — lỗi duy
  nhất là TestFrontendSourceGuard ở trên; 0 error, 0 skip. 423 = 383 + cors_origin_bind 21 + hand_landmarks_ws 9 +
  hand_live_equivalence 4 + frontend_contract 6. `git status --porcelain` trước/sau: giống hệt (`SAME`).

## B5 — UI "Ký từ" (§3.4)

- impact upstream (GitNexus, trước khi sửa): `Phase12Pipeline`, `CameraCapture`, `PredictionDisplay`, `Navbar` đều risk
  **CRITICAL** (processes_affected 18–21) — nhưng caller thật chỉ là d=1 `App.jsx` (Phase12Pipeline, Navbar) hoặc
  `Phase12Pipeline.jsx` (CameraCapture, PredictionDisplay); các nút d=3 là hàm Python (`src/training/train_cslr.py`,
  `scripts/evaluate_cslr_s06.py`, `clone/...`) do phân giải tên sai ngôn ngữ (name-fallback), không phải phụ thuộc thật.
  `App.jsx` render `<Phase12Pipeline />` không prop → đổi prop của CameraCapture/PredictionDisplay chỉ ảnh hưởng Phase12Pipeline.
  RealtimeStream.jsx không import CameraCapture/PredictionDisplay.
- Sửa:
  - `Phase12Pipeline.jsx` viết lại: `wsUrl(window.location, '/ws/live-stream')` + `useReducer` bọc `reduceLive`; huy hiệu
    `live-pipeline`/`live-model`; `live-recording` (harmonized, `recording_s / max_sign_s`); `live-discard` (lý do tiếng Việt);
    `live-error` (theo `code`); top-5/confidence từ `sign_result` (harmonized) hoặc `frame_result` (legacy); nút "Xóa từ cuối";
    bỏ nút "Test Frame" và chuỗi base64 1×1; `bufferCapacity` lấy từ message; hiện `client_e2e_ms` của sign_result.
  - `CameraCapture.jsx`: nhận `getSocket()` (đọc mỗi tick, không giữ socket cũ); `timestamp = nowMs()`; bỏ chế độ binary
    (mọi frame là JSON có timestamp — phiên harmonized không được trộn frame có/không timestamp); `camera-start`/`camera-stop`;
    chất lượng JPEG giữ 0.75 như cũ (prop `jpegQuality`).
  - `PredictionDisplay.jsx`: bỏ ":8000", bỏ mặc định 60; trạng thái RECORDING/WAIT_REST; `live-connection`, `live-status`,
    `live-gloss`, `live-confidence` (`data-value`), `live-top5` (+ `live-top5-item` `data-gloss`), `live-words`, `live-undo`.
  - `Navbar.jsx`: ':8000' → 'Online'. `RealtimeStream.jsx`: đúng 3 dòng (import `wsUrl as buildWsUrl`, dòng URL, chuỗi báo lỗi bỏ
    ":8000") — `git diff --numstat` → `3 2`.
- `cd frontend && npm run build` → `✓ 1597 modules transformed`, `✓ built in 1.79s` (exit 0). `package-lock.json` không đổi.
- `cd frontend && npm test` (Node v25.9.0) → `tests 26, pass 26, fail 0`; `git ls-files "tests/*.test.mjs"` = 3 file, cả 3
  file đều có test trong output (ws 4, liveProtocol 12, fingerspelling 10).
- Guard AC8: **đỏ có chủ đích, còn 2 vi phạm** (14 → 2), chỉ trong `Fingerspelling.jsx` (:69 '/api/fingerspelling', :130 '25 lớp')
  — đúng mốc §0.3 sau B5.
- AC2 (25 cũ + 4 mới), log `../_plan06_tmp/b5_ac2.log`: `Ran 423 tests in 217.217s` `FAILED (failures=1)` — failure duy nhất là
  `TestFrontendSourceGuard.test_no_violation` (2 vi phạm trên); 0 error, 0 skip.
  `git status --porcelain` trước/sau KHÁC nhưng không do test: trong lúc chạy có người khác sửa `CLAUDE.md` và thêm
  `docs/CLOUD.md`, `scripts/cloud_setup.sh` (thay đổi của người dùng/orchestrator — coder KHÔNG đụng, KHÔNG commit).
- Chưa kiểm UI bằng trình duyệt (việc của B8).

## B6 — UI "Đánh vần" (§3.2)

- impact upstream `Fingerspelling`: risk CRITICAL theo GitNexus (19 process) — caller thật chỉ d=1 `App.jsx`
  (`<Fingerspelling />` không prop); d=3 là hàm Python do name-fallback sai ngôn ngữ (như B5).
- `Fingerspelling.jsx` viết lại (từ bản nháp `../_plan06_tmp/Fingerspelling.jsx` + 3 sửa: `sessionInfoRef` khai báo trước
  `connectWs`; bỏ điều kiện thừa; không gọi `/compose` khi danh sách token rỗng — chữ hiện rỗng):
  GET `/api/fingerspelling/status` (không available → khóa Ghi, hiện message); WS `wsUrl(window.location, '/ws/hand-landmarks')`
  → `session_info` (lấy `limits.max_frames_per_segment`); [Ghi] bật camera → gửi `control/reset` → chờ `reset_done` → chụp
  FS_TARGET_FPS, canvas KHÔNG lật, JPEG FS_JPEG_QUALITY, `timestamp = nowMs()`, tối đa FS_MAX_IN_FLIGHT frame đang bay (vượt →
  `client_skipped`); đủ `max_frames_per_segment` frame → tự dừng; [Dừng] → chờ frame đang bay tối đa 2 s → `buildSequenceBody`
  (chỉ segment hiện tại) → POST `/sequence` → prediction, confidence ("độ tin cậy của mô hình"), candidates (class, confidence,
  kind); lỗi 413/422/503 hiện `detail` (cả 2 dạng) và KHÔNG hiện kết quả. Hiện độ phân giải, số frame, số frame có tay,
  client_skipped, fps hiệu dụng, thời gian từ Dừng tới phản hồi (mốc DoD 8, không đo ở đây). Bộ ghép: tokens trong state,
  Thêm (ứng viên đang chọn, mặc định top-1) / Dấu cách / Xóa lùi / Xóa hết; mỗi lần đổi → POST `/compose`, chữ hiện CHỈ lấy
  từ `text` của server + `warnings`. Đủ 15 `data-testid` fs-*. Không còn gọi endpoint ảnh cũ, không còn "25 lớp".
- `cd frontend && npm run build` → `✓ 1598 modules transformed`, `✓ built in 1.30s`. `package-lock.json` không đổi.
- `cd frontend && npm test` (Node v25.9.0) → `tests 26, pass 26, fail 0` (3 file = `git ls-files "tests/*.test.mjs"`).
- Guard AC8: **0 vi phạm** (14 → 2 → 0) — `tests.test_frontend_contract` `Ran 6` `OK`.
- AC2 (25 cũ + 4 mới), log `../_plan06_tmp/b6_ac2.log`: `Ran 423 tests in 224.958s` `OK`, 0 skip, 0 failure, 0 error;
  `git status --porcelain` trước/sau giống hệt (`SAME`).
- Chưa kiểm UI bằng trình duyệt (B8).

## B7 — smoke test WS v2 (AC10) + `docs/phase12_api.md` (AC11)

- impact: `scripts/smoke_test_phase12.py` là script thủ công (không có caller trong code/test; text search: chỉ tài liệu).
  Không sửa symbol nào của backend/src.
- `scripts/smoke_test_phase12.py` viết lại cho WS v2: [1/6] REST /health + /model/info; [2/6] message đầu `session_info`
  (`protocol_version == 2`, pipeline ∈ {legacy, harmonized_v1}), frame_result theo pipeline (legacy: đủ khóa cũ; harmonized:
  `prediction is None`); [3/6] text rác → 1 message `error` với `code` thuộc bảng §3.6 kế hoạch 04 (in mã thật), frame tiếp
  vẫn được trả lời; frame binary ở phiên mới; [4/6] 30 frame của clip TRAIN đầu tiên của `live_clip_sample.select_train_clips(1, 0)`
  (thay cho W00009N.mp4 cũ — không chạm TEST/VAL), đếm message theo `type`, 0 `error`; [5/6] `/ws/hand-landmarks`
  session_info → reset_done → hand_frame trên frame đầu của `a_hau_A_001.mp4`; [6/6] Origin lạ → 1008 ở cả hai WS.
- AC10, chạy 2 lần (log `../_plan06_tmp/b7_smoke_default.log`, `../_plan06_tmp/b7_smoke_h360.log`), cả hai exit 0 và in
  `>>> PHASE 12 SMOKE TEST PASSED <<<`:
  - Mặc định: `model_type=stgcn num_classes=487 device=cuda`; `session_info: pipeline=legacy model=stgcn is_default=True`;
    text rác → `error code=decode_failed detail='image is not valid base64'`; clip `qipedc_W03292N`: 30 frame,
    `messages by type: {'frame_result': 30}`; hand_frame `640x480 points=21 handedness='Left'`; 1008 ở cả hai WS.
  - `VSL_MODEL_TYPE=stgcn_h360`: `model_type=stgcn num_classes=876`; `session_info: pipeline=harmonized_v1 model=stgcn_h360
    is_default=False`; text rác → `error code=bad_timestamp detail='this session uses client timestamps; the frame has none'`
    (phiên đã cố định nguồn timestamp client; text trần = frame không timestamp); clip `qipedc_W03292N`: 30 frame,
    `{'frame_result': 30}` (0 sign_result/sign_discarded trong 30 frame — chỉ ghi nhận, AC12 là nơi kiểm sự kiện);
    hand_frame 640x480 21 điểm; 1008 ở cả hai WS.
- `docs/phase12_api.md` viết lại: cách chạy (127.0.0.1, proxy /api /ws, strictPort), CORS/Origin/`VSL_CORS_ORIGINS`, REST,
  `/ws/live-stream` v2 đầy đủ (+ `dropped_frames` kế hoạch 05, thay đổi legacy review 04 mục 11), `/ws/hand-landmarks`,
  trường đo DoD 8, mục "Giới hạn" + tiểu mục AC6 (số lấy nguyên văn từ JSON e58d025: Kaggle↔cục bộ 1 clip lệch cờ,
  max 0.2297654151916504; JPEG q90↔PNG 2 clip lệch cờ, max 0.24034595489501953; top-1 trùng 10 clip TRAIN, không chứng
  minh bền vững). Không số đo hiệu năng nào.
- `tests/test_frontend_contract.py` thêm `TestPhase12ApiDoc` (6 test): mã lỗi trích bằng regex từ `_ws_error("…"`/`WsError("…"`
  (9 mã), lý do bỏ đoạn trích từ `_discard(...)` của sign_segmenter + `"reason": "…"` (6 lý do), type message, thuật ngữ,
  mục Giới hạn, và mọi số thập phân trong đoạn AC6 phải có trong JSON (+ đường dẫn JSON và `git_commit`). 6 → 12 test, OK.
- AC2 (25 cũ + 4 mới), log `../_plan06_tmp/b7_ac2.log`: **`Ran 429 tests in 224.030s` `OK`**, 0 failure, 0 error, 0 skip
  (429 = 383 + cors 21 + hand_landmarks_ws 9 + hand_live_equivalence 4 + frontend_contract 12); `git status --porcelain`
  trước/sau giống hệt.
- `cd frontend && npm test` (Node v25.9.0) → `tests 26, pass 26, fail 0` (3 file).

## B8 — e2e fullstack (AC12) — chạy xong, 1 mệnh đề CẦN PLANNER

- Commit script: 7e38118 (`scripts/make_fake_webcam_y4m.py`, `scripts/e2e_browser.cjs`, `scripts/e2e_fullstack.py`; 3 file mới,
  không sửa symbol cũ). detect-changes --scope staged: risk CRITICAL theo đồ thị (105 symbol mới; 41 process "bị ảnh hưởng"
  do trùng tên `ROOT`/`main` với file khác — không symbol cũ nào đổi). Guard backend + frontend contract: `Ran 36` `OK`
  (script mới không nằm trong phạm vi SERVING của guard DoD 7: không được import từ backend, không được start_fullstack.ps1 gọi).
- Clip: Đánh vần `a_hau_A_001.mp4` (hauuto_a_hau_A_001, 75 frame, 23.584 fps, 640×480). Ký từ: `qipedc_D0120T`
  (TRAIN, 113 frame, 29.97 fps, 1280×720) — **giả định của coder**: "clip đầu tiên (thứ tự của hàm) của mẫu
  live_clip_sample.py (seed 0, TRAIN), KHÁC W03251B" = phần tử đầu của `select_train_clips()` mặc định (n=8, seed 0) sau khi bỏ
  `qipedc_W03251B` (phần tử đầu là W03251B; thứ 2 là D0120T). (B7 smoke dùng `select_train_clips(1, 0)` → W03292N.)
- y4m ở `%TEMP%\vslt_e2e\` (ngoài repo; script từ chối đường ra trong repo).
- Chạy thử trên code chưa commit (ra `../_plan06_tmp/b8_dev_*.json`): cả 3 kịch bản đạt mọi kiểm tra AC12 TRỪ
  `ws_urls_all_via_proxy_no_8000`: trang dev có thêm socket HMR của Vite `ws://localhost:3000/?token=…`
  (`Sec-WebSocket-Protocol: vite-hmr`) — không bắt đầu bằng `ws://localhost:3000/ws/` → **CẦN PLANNER** (xem dưới).
- **Chạy chính thức** tại HEAD 15200d9 (`git status --porcelain -- backend src frontend scripts tests` rỗng; JSON ghi
  `git_commit` 15200d9…, `code_dirty: false`), commit JSON e3d0df8. Log: `../_plan06_tmp/b8_run_{fingerspell,word_default,word_h360}.log`.
  Chung: node v25.9.0, `Edg/146.0.3856.72`, mediapipe 0.10.14; health 200 `status ok` sau 7.1 / 8.7 / 8.7 s, trang 3000 200 sau
  7.2 / 8.7 / 8.7 s; 0 console error, 0 pageerror, 0 requestfailed, 0 HTTP ≥ 400; 0 request tới `/api/fingerspelling`;
  sau khi dừng cổng 8000/3000 rảnh, 0 tiến trình còn sống (cây: powershell, uvicorn, 3 python, cmd, 2 node, esbuild).
  - `reports/e2e_2026-09-29/fingerspell_default.json`: 19/20 kiểm tra đạt. status available true (bigru, 34 lớp); WS
    hand-landmarks: session_info → reset_done → 76 hand_frame; 1 POST /sequence 200, body 76/76/76 frame, 76 khung không null,
    0 khung 21 điểm trùng, max |v| trong JSON, timestamps không giảm, source_mirrored false; `fs-prediction` "a" == response;
    `fs-confidence` data-value "0.9688", chữ "96.9%" == kỳ vọng; fs-add → POST /compose 200 tokens ["a"], `fs-composed` "a" ==
    text. `info_not_accuracy`: clip hauuto_a_hau_A_001 nhãn "a", prediction "a", confidence 0.9688 (clip TRAIN, không phải độ
    chính xác).
  - `reports/e2e_2026-09-29/word_default.json`: 17/18. session_info v2 `legacy` (stgcn, is_default true); 44 frame_result;
    0 error; `live-pipeline` "legacy"; sau camera-stop + 2 s im lặng, `live-top5` == top5 của frame_result cuối.
  - `reports/e2e_2026-09-29/word_stgcn_h360.json`: 20/21. session_info v2 `harmonized_v1` (is_default false); 72 frame_result,
    mọi prediction null; status RECORDING 45 / IDLE 27; `live-recording` hiện 1 lần; 1 sign_result (0 sign_discarded) trong
    1.01 vòng clip → §7-2 KHÔNG kích hoạt; `live-gloss` + `live-top5` == sign_result cuối; 0 error.
  - **Kiểm tra đỏ duy nhất ở cả 3: `ws_urls_all_via_proxy_no_8000`.** Danh sách URL WS mỗi lần gồm socket HMR của Vite dev
    `ws://localhost:3000/?token=…` (`Sec-WebSocket-Protocol: vite-hmr`, do `start_fullstack.ps1` chạy `npm run dev`), không bắt đầu
    bằng `ws://localhost:3000/ws/`. Mọi socket của app (`/ws/live-stream`, `/ws/hand-landmarks`) đều qua proxy, 0 URL chứa `:8000`.
    (Socket app thứ 2 cùng path đóng trước khi có message = React.StrictMode mount 2 lần ở dev.)
    → **CẦN PLANNER**: AC12 viết "Mọi URL WS" — coder KHÔNG tự loại socket HMR khỏi kiểm tra, KHÔNG tắt HMR trong
    vite.config.js (ngoài thiết kế §3.5). Lựa chọn cho planner: (a) loại socket có protocol `vite-hmr` khỏi mệnh đề;
    (b) tắt HMR/ws của Vite dev (`server.hmr`/`server.ws`) — đổi trải nghiệm dev; (c) chạy e2e trên `vite preview` (không có
    HMR) — lệch với "chạy start_fullstack.ps1".

## B9 — kiểm tra đóng việc (CHẠY TRƯỚC; CHƯA đóng vì AC12 chờ planner)

- AC2 hợp đồng (29 module), HEAD 0e506c3, log `../_plan06_tmp/b9_ac2.log`: **`Ran 429 tests in 272.291s` `OK`**, 0 skip,
  0 failure, 0 error (= B0 383 + cors_origin_bind 21 + hand_landmarks_ws 9 + hand_live_equivalence 4 + frontend_contract 12;
  25 module cũ không đổi số so với B0).
- AC2 mở rộng (31 module = 29 + test_archive_private_kaggle_r05 14 + test_backend_source_guard 24), log
  `../_plan06_tmp/b9_ac2_31.log`: **`Ran 467 tests in 248.873s` `OK`**, 0 skip (bằng mốc sau merge 467).
  Guard DoD 7 backend xanh: script B8 không thuộc SERVING (không import từ backend, start_fullstack.ps1 không gọi scripts/*.py).
- `git status --porcelain` trước / sau cả hai lần chạy: giống hệt (`SAME`).
- `git diff 797d0af HEAD -- tests/`: chỉ file mới (numstat cột xóa = 0 ở cả 6 file A); không file test cũ nào bị sửa.
- `cd frontend && npm test` (node v25.9.0): `tests 26, pass 26, fail 0`; `git ls-files "tests/*.test.mjs"` = 3 file, chạy
  riêng từng file: ws 4, liveProtocol 12, fingerspelling 10 (tổng 26, cả 3 file đều chạy).
- `npm run build`: exit 0 (`✓ built in 2.51s`). `npm ls --depth=0` giống hệt file B0 (bỏ dòng đầu chứa đường dẫn):
  `NPM_LS_SAME`. `git diff 797d0af HEAD -- frontend/package-lock.json` rỗng; `frontend/package.json` +2/−1 (thêm `"test"`,
  dấu phẩy dòng `preview`).
- AC1 — `git diff --name-status 797d0af HEAD`: 56 dòng. Tách nguồn:
  - Do merge bbfdff3 (`git diff --name-status bbfdff3^1 bbfdff3`, 14 file): README.md (M), docs/cloud_reports/viec-A-D-2026-09-29.md,
    docs/plans/{07-viec6-che-do,08-segmenter-live,09-don-dep-review05,09-progress,10-guard-dod7,10-progress}.md,
    docs/reviews/{09-review,10-review}.md, reports/guard_dod7_2026-09-29/guard_findings.json, scripts/archive_private_kaggle.py (M),
    tests/test_archive_private_kaggle_r05.py, tests/test_backend_source_guard.py.
  - Do commit orchestrator/cloud trên nhánh chính (không phải merge, không phải coder 06): docs/STATE.md, docs/usage_ledger.csv
    (các commit `state:` 2f5d3f2 be0aac0 353c46d 49a9f22 bae0eaf f3a7371 4e98c48 8e1c85a + facffea + 8628948);
    docs/progress_log.md (chỉ 2f5d3f2 `state:`, 0 dòng xóa); CLAUDE.md, docs/CLOUD.md, scripts/cloud_setup.sh (8628948 "chore: cloud
    handoff", 296b12e, f62dd45 "cloud: ..."); docs/cloud_reports/ (merge). docs/plans/06-viec5-frontend.md: chỉ facffea (planner).
    Lưu ý: CLAUDE.md, docs/CLOUD.md, scripts/cloud_setup.sh KHÔNG nằm trong danh sách merge orchestrator nêu — chúng đến từ 8628948/
    296b12e/f62dd45 trên first-parent.
  - Do coder 06 (`git log --name-only --grep "^(WIP )?06:"` trừ facffea): backend/main.py, src/inference/hand_live.py (A),
    start_fullstack.ps1 (chỉ `--host 0.0.0.0` → `127.0.0.1`), frontend/vite.config.js, frontend/package.json, 6 component
    (RealtimeStream.jsx: đúng 3 dòng — import, URL, chuỗi báo lỗi), frontend/src/lib/{ws,liveProtocol,fingerspelling}.js (A),
    frontend/tests/{ws,liveProtocol,fingerspelling}.test.mjs + build_body_cli.mjs (A), scripts/smoke_test_phase12.py (M),
    scripts/{hand_live_check,make_fake_webcam_y4m,e2e_fullstack}.py + scripts/e2e_browser.cjs (A), tests/{test_cors_origin_bind,
    test_hand_landmarks_ws,test_hand_live_equivalence,test_frontend_contract}.py (A), reports/fingerspell_live_2026-09-29/
    hand_live_check.json + reports/e2e_2026-09-29/{fingerspell_default,word_default,word_stgcn_h360}.json (A), docs/phase12_api.md (M),
    docs/plans/06-progress.md (A) — tất cả nằm trong danh sách AC1. frontend/index.html không đổi; package-lock không đổi;
    không file bị xóa; không .pt/.npz/.mp4/.y4m/.png/.jpg/.log nào được thêm; 3 file ` D` của người dùng vẫn chưa staged.

## B8b — Lần sửa 2 (0B.5 bước 1–3): luật socket HMR Vite + mồ côi StrictMode, chạy lại 3 kịch bản

### B8b-1 — test AC12-t trước (commit 302072c)
- `tests/test_frontend_contract.py` thêm lớp `TestE2eSocketRules` (16 test; nạp `scripts/e2e_fullstack.py` theo đường dẫn bằng
  `importlib.util.spec_from_file_location`, không mở trình duyệt/server, không skip). Đủ 9 ca của AC12-t, thêm vài ca âm:
  URL HMR sai (`?token=x&a=1`, `/foo?token=x`, `127.0.0.1`, token rỗng, xuống dòng cuối, `wss://`, `#f`, cổng 3001),
  protocol khác `vite-hmr`, message không phải JSON trên socket HMR, `:8000` trên socket mồ côi, socket app `127.0.0.1:3000`,
  path rỗng, socket có message không bao giờ là mồ côi.
- Chạy trước khi có hàm: `Ran 16 tests` `FAILED (errors=26)` — 26/26 là `AttributeError` (`classify_ws`/`strictmode_orphans`
  chưa có). Log `../_plan06_tmp/b8b1_red.log`. detect-changes --scope staged: risk critical theo đồ thị (25 symbol mới trong
  file test; 36 process "bị ảnh hưởng" do trùng tên) — không symbol cũ nào đổi.

### B8b-2 — hàm thuần + 4 kiểm mới trong `scripts/e2e_fullstack.py`
- impact `evaluate` (`-f scripts/e2e_fullstack.py`, `../_plan06_tmp/b8b2_impact_evaluate.txt`): risk **CRITICAL** theo đồ thị
  (direct 1 = `main` của chính script; độ sâu 3: 14 do trùng tên `main` với các script khác; 23 process). Text search: caller
  duy nhất là `main()` của `scripts/e2e_fullstack.py` (script chạy tay; test chỉ gọi hàm thuần mới). Symbol mới:
  `classify_ws`, `strictmode_orphans`, `app_ws_by_path`, `ws_classification`, `_hmr_rule_failures`, `_ws_brief`.
- Cài đặt: `VITE_HMR_URL_RE = ^ws://localhost:3000/\?token=[A-Za-z0-9_-]+$` (`fullmatch`), protocol đúng `vite-hmr`, mọi message
  là JSON `type == "connected"` (`count_by_type` chỉ có `connected` và `n_messages == tổng count_by_type`), ≤ 1 socket HMR.
  `ws_urls_all_via_proxy_no_8000` bị thay bằng `ws_no_8000_any_socket` (mọi socket), `ws_app_urls_via_proxy` (≥ 1 socket không
  phải HMR, tất cả bắt đầu `ws://localhost:3000/ws/`), `vite_hmr_socket_rule`; thêm `strictmode_orphan_rule` áp cho MỌI path
  của socket app (đúng chữ "với mỗi path app" của AC12). `hand_ws_session_info` và `live_ws_first_message_session_info_v2`
  dùng `strictmode_orphans`: mọi socket không phải mồ côi phải có message đầu `session_info`. JSON thêm khóa
  `ws_classification{vite_hmr_excluded[{url, protocol, count_by_type}], strictmode_orphans_by_path}`.
  `scripts/e2e_browser.cjs` không sửa (đã có `protocol`, `count_by_type`, `closed`, `n_messages`, `first_type`).
- AC12-t: `Ran 16 tests` `OK`.
- AC2 31 module (log `../_plan06_tmp/b8b2_ac2_31.log`): **`Ran 483 tests in 273.728s` `OK`**, 0 failure, 0 error, 0 skip.
  Theo module (`../_plan06_tmp/b8b2_counts.txt`): 25 module cũ = 383 (bằng B0); 4 module của 06 = cors_origin_bind 21 +
  hand_landmarks_ws 9 + hand_live_equivalence 4 + frontend_contract 28 = 62 (= B7 46 + 16 test AC12-t); 2 module merge =
  archive_private_kaggle_r05 14 + backend_source_guard 24 = 38 (bằng review cloud). `git status --porcelain` trước/sau: SAME.
- detect-changes --scope staged (`../_plan06_tmp/b8b2_detect.txt`): risk medium (1 file; symbol cũ đổi: `evaluate`, `main`,
  `_find_forbidden` (chỉ do dòng lân cận), `checks`; 2 process `Main → Fps_fraction`, `Main → Is_inside_repo` của chính script).
  Index GitNexus ở f702b1a nên symbol mới chưa được thấy trong kết quả này.

### B8b-3 — DỪNG theo §7-8: CẦN PLANNER (`strictmode_orphan_rule` đỏ ở kịch bản Đánh vần)
- Trước lượt chính thức, chạy THỬ cả 3 kịch bản tại HEAD sạch eb379fa (`git status --porcelain -- backend src frontend
  scripts tests` rỗng), đầu ra NGOÀI repo (`../_plan06_tmp/b8b3_trial_*.json`, log `../_plan06_tmp/b8b3_trial_*.log`); mỗi JSON
  có `generated_by.git_commit` eb379fa…, `code_dirty: false`. `reports/e2e_2026-09-29/*.json` KHÔNG bị ghi đè, không commit JSON.
  - `fingerspell`: **exit 1, `checks 22/23 pass; FAILED: ['strictmode_orphan_rule']`**.
  - `word` mặc định: exit 0, 21/21, `all_checks_pass: true` (HMR loại 1: `ws://localhost:3000/?token=5tA751TjzxVE`,
    `vite-hmr`, `{connected: 1}`; mồ côi `/ws/live-stream`: 1; ran_loops 1.01).
  - `word --model-type stgcn_h360`: exit 0, 24/24, `all_checks_pass: true` (HMR loại 1; mồ côi `/ws/live-stream`: 1;
    ran_loops 1.026; 1 sign_result).
- Chi tiết đỏ (nguyên văn JSON Đánh vần): `strictmode_orphan_rule.detail` = `/ws/live-stream: {n_sockets: 2, orphans: [0],
  violations: ["socket 1: 0 messages and it is the last socket of the path"]}`, `/ws/hand-landmarks: {n_sockets: 2,
  orphans: [0], violations: []}`. Các socket: HMR (101, 1 msg `connected`); `/ws/live-stream` ×2 (`handshake_status: null`,
  `closed: true`, 0 message); `/ws/hand-landmarks` ×2 (mồ côi 0 message đã đóng; socket dùng 101, session_info → reset_done →
  76 hand_frame). Mọi kiểm URL mới xanh (`ws_no_8000_any_socket`, `ws_app_urls_via_proxy`, `vite_hmr_socket_rule`),
  `hand_ws_session_info` xanh.
- Nguyên nhân (đọc code, không suy từ số): `frontend/src/App.jsx:9` tab mặc định là `'realtime'` → `Phase12Pipeline` mount
  (StrictMode: mount → unmount → mount = 2 socket `/ws/live-stream`); kịch bản Đánh vần của `e2e_browser.cjs` bấm tab "Bảng Chữ
  Cái" ngay sau `goto` (step `tab_alphabet` t=2.21 s) → `Phase12Pipeline` unmount, socket thứ 2 đóng trước khi bắt tay xong.
  Như vậy path `/ws/live-stream` của kịch bản Đánh vần KHÔNG phải trường hợp "mỗi component chỉ mount 1 lần trong kịch bản"
  mà 0B.2 giả định: component bị gỡ do chuyển tab, không có socket "được dùng". 3 JSON e3d0df8 cũng có đúng 2 socket này
  (planner ghi "socket đầu của mỗi path … 0 message" nhưng ở Đánh vần cả 2 socket `/ws/live-stream` đều 0 message).
- Coder KHÔNG sửa luật, KHÔNG đổi luồng trình duyệt, KHÔNG đổi clip/`App.jsx` (App.jsx thuộc danh sách "KHÔNG đổi" của AC1).
  Cài đặt hiện tại áp `strictmode_orphan_rule` cho MỌI path socket app đúng chữ AC12 ("với mỗi path app").
- Câu hỏi cho planner (chọn một, hoặc khác): (a) luật mồ côi chỉ áp cho path mà kịch bản kiểm `session_info`
  (Đánh vần: `/ws/hand-landmarks`; Ký từ: `/ws/live-stream`) — path còn lại cần luật riêng; (b) thêm loại "socket của component
  bị gỡ do chuyển tab": path KHÔNG được kịch bản dùng, ≤ 2 socket (cặp StrictMode), tất cả 0 message, `closed: true`, tạo trước
  lúc bấm tab — vẫn chịu `:8000` và `/ws/`; (c) giữ nguyên chữ → AC12 Đánh vần không đạt được với luồng hiện tại (tab mặc định
  không đổi được vì `App.jsx` bị khóa).

## B8c — Lần sửa 3 (§0C.5): vai trò path theo kịch bản + `tab_unmounted_socket_rule`, chạy chính thức 3 kịch bản

### B8c-1 — test AC12-t mục 10 trước (commit 85ef325, `WIP 06:`)
- `tests/test_frontend_contract.py` thêm lớp `TestE2eScenarioRoles` (30 test; chỉ thêm dòng cuối file).
  `git diff eb379fa HEAD -- tests/test_frontend_contract.py | grep -c '^-[^-]'` → `0` (16 test cũ không sửa).
  Ca: bảng vai trò là hằng (+ kịch bản lạ → ValueError); 10a (dạng lượt thử), 10a biến thể socket 0 đóng trước T, 10b, 10c;
  âm `tab_unmounted_socket_rule` (3 socket; `closed: false`; `closed_t_s` null; `closed_t_s > R` (+ dương `= R`);
  `created_t_s` = T / > T / null; thiếu `tab_alphabet`; `clicked: false`; thiếu `record_clicked`; `{error:1}`,
  `{session_info:1, frame_result:1}`, `{session_info:2}`, `{frame_result:1}`; `n_non_json: 1`; protocol 3; `first_type`
  khác session_info; handshake 403; path lạ `/ws/other`; `word` + `/ws/hand-landmarks`); âm `strictmode_orphan_rule`
  (word 2 socket 0 message; fingerspell hand 2 socket 0 message; fingerspell vắng `/ws/hand-landmarks`); âm URL trên path
  `tab_unmounted` (`:8000`, `127.0.0.1:3000`); 2 dạng `word` xanh; nối dây `evaluate` và `ws_classification`.
  Mỗi ca assert đủ 5 kiểm (3 kiểm URL + 2 luật path): đúng kiểm ghi bị đỏ, còn lại xanh.
- Chạy trước khi có hàm (log `../_plan06_tmp/b8c1_red.log`): `Ran 46 tests` `FAILED (failures=1, errors=35)` — 16 cũ OK;
  mọi ca mới đỏ (AttributeError `scenario_ws_roles`/`SCENARIO_WS_ROLES`; FAIL duy nhất là `test_evaluate_uses_the_role_rules`
  tái hiện đúng lỗi lượt thử: `/ws/live-stream` "socket 1: 0 messages and it is the last socket of the path").
- impact (index tại 8a2f5a2, `../_plan06_tmp/b8c2_impact*.txt`): `evaluate` (`-f scripts/e2e_fullstack.py`) CRITICAL theo đồ
  thị — d1 = `main` của chính script, d3 = 13 nút do trùng tên `main`; `strictmode_orphans` CRITICAL (d1 = 2), `app_ws_by_path`
  CRITICAL (d1 = 3), `ws_classification` CRITICAL (d1 = 1), `newWs` (JS) CRITICAL (d1 = 1) — đều do trùng tên ở độ sâu 3.
  Text search (`grep -rn` trong scripts tests backend src frontend/src): caller thật chỉ trong `scripts/e2e_fullstack.py`
  (`evaluate`←`main`; `strictmode_orphans`←`evaluate`,`ws_classification`, test; `app_ws_by_path`←`evaluate`,
  `ws_classification`, `main`; `ws_classification`←`main`), `newWs`←handler `webSocketCreated` của `e2e_browser.cjs`.
- detect-changes --scope staged: "no indexed symbols overlap those hunks" (chỉ code mới cuối file test).
