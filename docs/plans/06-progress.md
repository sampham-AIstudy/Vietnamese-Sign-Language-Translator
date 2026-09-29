# Kế hoạch 06 — tiến độ (coder; chặng 1: B0–B2; chặng 2: B3–B4; chặng 3: B5–B7)

- P6 = 797d0af (HEAD lúc coder bắt đầu B0, commit đã chứa kế hoạch 06)
- Bước đã xong: B0 (8e7b09b), B1 (4924502), B2 (ed5c4c9), B3 (e58d025 + 5fcf295), B4 (026f474)
- Bước đang làm: B5 (chặng 3 = B5–B7, theo Lần sửa 1 của kế hoạch, facffea)
- Bước còn lại: B5, B6, B7 (chặng 3); B8–B9 (chặng 4)

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
