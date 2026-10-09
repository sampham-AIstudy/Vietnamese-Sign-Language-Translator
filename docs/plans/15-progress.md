# Kế hoạch 15 — tiến độ coder

Kế hoạch: `docs/plans/15-level1-realtime-desktop.md`. Chặng giao: MVP B0–B3. Nhánh `feat/vslt-complete`, mốc HEAD `6c4f5e0`.
Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`. Log tạm: `_work/_plan15/` (không commit).

## Trạng thái
- 2026-10-09 U2a xong (commit `15: L13-U2a test TB-1 overlay co giãn (AC-U7/U7m)`), TB-1 test AC-U7 đạt, đột biến m9–m12 đỏ (AC-U7m). Reviewer U2a: APPROVE (`docs/reviews/15-l13-u2a-review.md`).
- 2026-10-09 U2b xong (commit `15: L13-U2b nối cửa sổ co giãn (AC-U4/U4b/U6b)`, vslt-coder-claude). Reviewer U2b: APPROVE (`e165990`).
- 2026-10-09 U2c xong (commit `15: L13-U2c phím f, --fullscreen, --[no-]display-mirror, LRU font (AC-U6/U8)`).
- 2026-10-09 U2d xong (commit `15: L13-U2d script đo chi phí hiển thị (AC-U5, DC1)`). Script `scripts/level1_display_cost.py` + test `tests/test_level1_display_cost.py` đạt (AC-U5, gate DC1).
- ĐANG LÀM: không.
- Xong: B0 (4e4d9e3), B1 (966ea4b), B2 (58b31ce), B3 (WIP 75e3116 + commit `15: B3`), B4 (commit `15: B4`), B5 (3ebc7b9), T1 (92fce21), A1 (commit code 72167b9 + commit báo cáo 1ca53f3), T2 (ec19b1d; code ở ad7c126), A2 (6067611 + config commit `15: A2 config hiệu chỉnh`), R0 (code `a3970a6` + báo cáo `reports/level1_realtime_2026-10-04/rearm_check_r0.json`). A2a (code ở WIP `dddfde8` + commit `15: A2a` trên nhánh cloud; CHỜ LOCAL: AC-S18 trên clip thật + sinh lại rearm_check_r0.json bằng lệnh ở mục A2a). R1 (commit `15: R1` trên nhánh cloud; CHỜ LOCAL: AC-S18 + S18b trên clip thật). A2b (`71fc664` mã + `4b5d736` config; AC-W3 đạt).
  Lần sửa 13: M0 (5a32cff; ghi chép sửa ở commit U1), U1 (commit `15: L13-U1`), U1a (commit `acdcf63`), U2a (`cf5e2cc`), U2b (`b0cbcf1`), U2c, U2d.
- Còn lại (lần sửa 13): X1, G1..G3, K1..K2, V1, D1, V2, D2, D3, R1, R2, G5.

## B0 — mốc (2026-10-03)
- HEAD lúc bắt đầu: `6c4f5e0` (đã push). Không sửa mã ở B0.
- `sha256(checkpoints/alphabet_best.pt)` = `a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2` (= AC0).
- `git status --short` lúc mốc: ` M README.md`, 3 dòng ` D` của người dùng (`data (2)/Dataset/Labels/label.csv`,
  `data/alphabet_landmarks_full.csv`, `data/hand_data.csv`) + nhiều file untracked (lưu ở `_work/_plan15/b0_git_status.txt`).
  Không đụng; mọi commit của 15 dùng `git commit -- <đường dẫn cụ thể>`.
- AC1-đủ (31 module, lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1028`) → `_work/_plan15/b0_full.log`:
  `Ran 522 tests in 999.611s` — `FAILED (failures=1, errors=1, skipped=1)`.
  - ERROR: `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` — có sẵn (thiếu ViT5, STATE); 8 test của module không chạy
    (loader đếm 530 test = 522 + 8).
  - skip: `test_vsl_system` "Checkpoint checkpoints/stgcn_best.pt not found" — có sẵn (STATE).
  - FAIL: `tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs` (`[1, 1, 1, 0] != [1, 1, 1, 1]`) — test chập chờn
    đã biết (STATE). Chạy riêng 3 lần (`_work/_plan15/b0_flaky_reset_{1,2,3}.log`): FAIL / OK / FAIL. Không sửa/skip.
  - Mọi test khác OK. Số test theo module (loader, `_work/_plan15/b0_counts.txt`): alphabet_preprocessing 6, aspect_correction 3,
    realtime 3, split_guards 6, translation_core 8 (ERROR setUpClass), vsl_system 6 (1 skip), ws_throughput 0, fingerspelling_api 11,
    unified_split_integrity 4, report_step4 105, fingerspelling_limits 48, fingerspelling_compose 28, fingerspelling_deployed 9,
    alphabet_ckpt_provenance 16, harmonized 6, sign_segmenter 15, harmonized_live 10, ws_live_contract 18,
    live_harmonized_equivalence 9, archive_step4_kaggle 24, status_privacy 5, backend_model_unavailable 5, ws_dropped_frames 3,
    archive_private_kaggle 27, private_artifacts 8, cors_origin_bind 21, hand_landmarks_ws 9 (1 FAIL chập chờn),
    hand_live_equivalence 4, frontend_contract 71, archive_private_kaggle_r05 14, backend_source_guard 28.
- AC1-ngắn (11 module có sẵn; 5 module `tests.test_level1_*` chưa tồn tại ở B0 → bỏ khỏi lệnh) → `_work/_plan15/b0_short.log`:
  `Ran 167 tests in 236.586s` — `OK` (lần này test_reset_segments_and_graphs OK).

## B1 — config + bộ tách + load_level1_config
- File: `configs/level1_realtime.json` (20 khóa, mọi khóa `source: "design"` + lý do), `src/inference/level1_segmenter.py`
  (`Level1SignSegmenter`, `SignSegment`, `WordGap`), `src/inference/level1_core.py` (chỉ `load_level1_config`/`validate_level1_config`),
  `tests/test_level1_segmenter.py` (AC-S S1–S13 + kiểm tham số + trạng thái HUD: 18 test), `tests/test_level1_core.py` (C8: 7 test),
  `tests/test_level1_guard.py` (AC-G G2/G3 trên file của 15 hiện có: 4 test).
- Test viết trước: lần chạy đầu 17/18 OK, 1 FAIL do CHÍNH test tính sai (S5: 760 − 560 = 200 đã đạt hand_lost 200 → khung 19, không phải 20);
  sửa kỳ vọng của test mới (không phải test cũ), mã không đổi.
- AC1-ngắn (11 module cũ + test_level1_segmenter/core/guard; demo/equivalence chưa có) → `_work/_plan15/b1_short.log`:
  `Ran 196 tests in 218.618s` — `FAILED (failures=1)`: chỉ `test_reset_segments_and_graphs` (chập chờn đã biết). Mọi test level1 OK
  (29), guard chính OK. Chạy riêng test chập chờn: 8 lần với file của 15 (`b1_flaky_reset_1..8.log`): FAIL,FAIL,FAIL,OK,OK,OK,FAIL,OK;
  3 lần khi tạm cất file của 15 vào `_work/_plan15_tmp/stash` (`b1_flaky_stashed_1..3.log`): OK,FAIL,OK → chập chờn độc lập với 15
  (race: assert đếm close ngay sau khi thoát `with ws`, phía server đóng graph bất đồng bộ). Không sửa/skip.
- G1: `python -m tests.test_backend_source_guard` → `Ran 28 tests` `OK`, "[DoD7-guard] known=9 allowed=36", "[scope] serving=45 main=59"
  (main gồm 3 file src mới của 15, không finding mới).

## B2 — Level1Classifier + Level1Speller + level1_timing
- File: `src/inference/level1_core.py` (+ `class_kind`, `Level1Classifier` {from_checkpoint, features, warmup, classify},
  `Level1Speller` {segment_emitted, word_gap, on_result, on_word_gap, key, composed/text}), `src/inference/level1_timing.py`
  (`summarize`, `rate_from_timestamps`, `StageTimes`, tên chặng FRAME_STAGES/SIGN_STAGES), `tests/test_level1_core.py` (+ C1 trên 4 clip
  hauuto cố định theo sample_id, C2, C3, warmup, C4–C7, AC-T), `tests/test_level1_guard.py` (+ level1_timing.py).
- C1 BẰNG HỆT: `classify` == phản hồi `/api/fingerspelling/sequence` (TestClient, checkpoint triển khai) ở các khóa prediction,
  prediction_kind, confidence, candidates, frames, detected_frames, model_type, checkpoint trên hauuto_a_hau_A_001,
  hauuto_tone_f_hau_A_001, hauuto_a_khoi_A_001, hauuto_b_vy_A_001.
- `python -m unittest tests.test_level1_core tests.test_level1_guard tests.test_level1_segmenter` → `Ran 42 tests` `OK`.
- AC1-ngắn → `_work/_plan15/b2_short.log`: `Ran 209 tests in 245.428s` — `OK` (test chập chờn OK lần này). G1 guard chính:
  `Ran 28 tests` `OK`, "[DoD7-guard] known=9 allowed=36", "[scope] serving=45 main=59".

## B3 — level1_demo.py (MVP)
- File: `level1_demo.py` (gốc repo), `tests/test_level1_demo.py`, `tests/test_level1_guard.py` (điểm vào = level1_demo.py; closure gồm
  hand_live, alphabet_preprocessing, fingerspelling_compose, alphabet_temporal…: 0 finding ở file của 15, file khác 0 finding).
- App: `CameraReader` (camera_api/size/buffersize từ config, giá trị đọc lại vào JSON `camera_props`), `VideoFileReader` (fps từ file;
  không đọc được → `SourceError`, thoát mã 2, KHÔNG fps mặc định), `LatestFrameSlot` + `CaptureThread` (webcam / `--pace realtime`: chỉ
  khung mới nhất, đếm khung bị ghi đè), `ClassifyWorker` (phân loại ngoài vòng chính, theo thứ tự), một `HandLandmarkSession` liên tục,
  chấm vẽ trên CHÍNH khung đã xử lý (chưa lật), lật gương chỉ trong `display_view`, HUD PIL (font tiếng Việt: `--font` hoặc
  config `font_paths`; không thấy → thoát với thông báo) đặt DƯỚI ảnh camera (không che tay), panel PIL cache theo nội dung, dòng số đo
  sống vẽ bằng cv2.putText (ASCII). Phím §3.4. JSON đủ khóa §3.5 (generated_by, config+sha256, checkpoint, source, frame_size,
  camera_props, warmup, stages 7+2 chặng {n, mean, p50, p95}, counts, tokens, text, warnings, segments, events, expected, note).
  `code_dirty` = `git status --porcelain -- level1_demo.py src configs/level1_realtime.json` (không tính thay đổi của người dùng ở
  README/data). Đường dẫn config/checkpoint mặc định tìm theo gốc repo nếu chạy từ thư mục khác.
- Chế độ: `gui` (webcam, hoặc video hiển thị từng khung), `paced` (`--pace realtime`), `headless` (video, mọi khung, phân loại đồng bộ).
  `--headless` với webcam → lỗi rõ ràng.
- Kiểm không webcam: `python -m unittest tests.test_level1_demo tests.test_level1_guard` → `Ran 16 tests` `OK` (D1 help; D2 headless
  a_hau_A_001.mp4 exit 0 + khóa JSON + prediction == classify chạy lại + 2 lần giống hệt; D3 ô khung mới nhất với khung video thật
  qua đúng lớp đọc của app (đồng bộ + luồng chụp nhịp file); D4 fps không đọc được → SourceError, file không phải video → exit ≠ 0;
  D5 `--pace realtime` với bộ phân loại chậm định nghĩa trong test → classify chạy ở luồng khác luồng chính và > 1 khung được xử lý
  trong lúc đó; HUD vẽ offscreen: ảnh camera không bị che, panel cache; thiếu font → SourceError; đường dẫn mặc định từ thư mục khác).
- Chạy cửa sổ thật 1 lần trên video (`--source <a_hau_A_001.mp4> --pace realtime --display-mirror --out-json _work/...`): exit 0, cửa sổ
  mở/tự đóng hết clip, token 'a' (đây là clip TRAIN; chỉ kiểm đường chạy, không phải độ chính xác; JSON nằm trong _work, không phải báo cáo).
  Quan sát định tính (không phải số báo cáo): chặng MediaPipe chiếm phần lớn thời gian mỗi khung và dao động mạnh giữa các lần chạy trên
  máy này; HUD ban đầu rebuild PIL mỗi khung (dòng số đo đổi liên tục) → đã tách dòng số đo ra cv2.putText. Đo chính thức: B5/B7.
- AC1-ngắn (16 module, thiếu test_level1_equivalence vì B4 chưa làm) → `_work/_plan15/b3_short2.log`: `Ran 221 tests in 312.548s` —
  `FAILED (failures=1)`: chỉ `test_reset_segments_and_graphs` (chập chờn đã biết); chạy riêng 3 lần (`b3_flaky_reset_{1,2,3}.log`):
  OK, OK, FAIL. Bản trước sửa nhỏ (`b3_short.log`): `Ran 220 tests` `OK`. G1: `Ran 28 tests` `OK`, "known=9 allowed=36", "serving=45 main=59".
- AC0: `git diff --name-only 6c4f5e0..HEAD` = 10 file, đều trong §3.1; sha256 checkpoint không đổi (a6311820…08a2); backend/main.py,
  README.md, realtime_demo.py, tests/test_backend_source_guard.py không đổi.

## B4 — test tương đương AC-E1 / AC-E3
- File: `tests/test_level1_equivalence.py` (9 test). Không sửa file mã nào; không symbol có sẵn nào bị sửa.
- E1 (BẰNG HỆT, không dung sai): 10 clip `hand_live_check.select_clips(read_manifest(), 8, 0)` (8 hauuto + 2 qipedc). Mỗi clip chạy CHÍNH
  app (`Level1App` headless, `VideoFileReader`, mọi khung, `HandLandmarkSession` mới mỗi clip; lớp con `RecordingSession` chỉ gọi
  `process` thật và ghi kết quả; reader được bọc spy) so với `_extract_one` (import nguyên vẹn) chạy vào thư mục tạm
  `_work/_plan15_tmp/vslt_p15_e1_*` (xóa ở tearDown). Khóa so: số khung, detected, landmark (float32 [21,3], `array_equal` cả mảng),
  handedness, score (float32), fps đọc từ file == metadata fps, frame_size; segment = trọn clip → `Level1Classifier.features`
  `array_equal` `alphabet_clip_features` trên kết quả offline (+ timestamps bằng hệt); `classify` == `/sequence`
  (`body_from_npz(offline)`) ở prediction, confidence, candidates. KẾT QUẢ: cả 10 clip BẰNG HỆT (log `_work/_plan15/b4_equiv.log`;
  in từ lần chạy: số khung/detected/fps và prediction mỗi clip).
- E3: AST trên `level1_demo.py` + `src/inference/level1_*.py`: không gọi `Hands(`/`resize`; `cv2.flip` chỉ trong `display_view` (đúng 1);
  tự kiểm bộ duyệt AST. Spy: khung đưa vào `process` `is` đối tượng reader trả về — headless (mọi khung, đúng thứ tự) và
  `--pace realtime --headless` (mỗi khung xử lý là một đối tượng đã đọc, thứ tự tăng, không bản sao).
- `python -m unittest tests.test_level1_equivalence -v` → `Ran 9 tests in 172.519s` `OK`.
- AC1-ngắn đủ 16 module → `_work/_plan15/b4_short.log`: `Ran 230 tests in 464.261s` — `OK` (0 skip; test chập chờn OK lần này).
  G1 trong đó: "[DoD7-guard] known=9 allowed=36", "[scope] serving=45 main=59"; tests.test_level1_guard OK.
- Giả định: thư mục tạm của test nằm dưới `_work/_plan15_tmp/` (quy tắc file tạm của orchestrator), không dùng %TEMP%.

## B5 — đo độ trễ đầy đủ + AC-L (2026-10-03, mốc c845b06)
- Đã có từ B3 (kiểm lại, không làm lại): 7+2 chặng, warm-up tách riêng (session MediaPipe riêng + `classifier.warmup()`, không vào
  `stages`), `--pace realtime`, `camera_api`/`CAP_PROP_BUFFERSIZE` từ config (giá trị đọc lại vào `camera_props`), cache panel PIL.
- Thêm ở B5 (`level1_demo.py`): HUD p50 lăn cho ĐỦ 9 chặng (`hud_stats_lines`, 2 dòng ASCII cv2.putText; trước chỉ mediapipe +
  frame_total) + processed/s + dropped; `Hud.compose(..., stats_lines)` nhận nhiều dòng, cache khóa theo số dòng;
  `counts.dropped` (= `frames_dropped`, tên theo AC-L L2; giữ `frames_dropped` vì test D2 cũ dùng), `counts.capture_fps` (từ thời điểm
  đọc khung, cùng `rate_from_timestamps`), `counts.results_not_displayed` (kết quả về sau khung cuối ở chế độ cửa sổ → không có
  emit_to_token); NOTE ghi rõ headless không vẽ/hiển thị nên draw_landmarks/hud/display n = 0.
- Impact (CLI, upstream) trước khi sửa: `_hud_lines`, `_process`, `report`, `_build` báo CRITICAL (74–124 "direct") và `compose`
  ambiguous — do TRÙNG TÊN với hàm khác trong repo (process run_harmonized/measure_and_compare không liên quan); `CaptureThread` UNKNOWN.
  Kiểm bằng text search: người gọi thật chỉ là `level1_demo.py` và `tests/test_level1_{demo,equivalence,guard}.py` (đều của 15).
- Test mới (thêm class, không sửa test cũ) trong `tests/test_level1_demo.py`: `TestLatencyAcL` (L1 trên JSON lệnh D2 headless;
  L1+L2 trên JSON `--pace realtime --headless` qua CLI: `counts.dropped`, mode paced, processed + dropped == read == số khung file;
  chế độ cửa sổ paced với các hàm cửa sổ OpenCV thay bằng bộ ghi trong test → đủ 7 chặng khung n == frames_processed,
  emit_to_token.n + results_not_displayed == classify.n; L3 cơ chế: `generated_by.git_commit` == HEAD, `code_dirty` == git status
  của CODE_PATHS), `TestHudStatsLines` (p50 lăn đúng cửa sổ, n/a khi rỗng, ASCII; panel thêm đúng 1 dòng / dòng stats).
  Thư mục tạm dưới `_work/_plan15_tmp/`. L3 trên `reports/level1_realtime_<D>/` để B7 (thư mục chưa có).
- `python -m unittest tests.test_level1_demo tests.test_level1_guard -v` → `_work/_plan15/b5_demo.log`: `Ran 22 tests in 46.941s` `OK`.
- AC1-ngắn đủ 16 module → `_work/_plan15/b5_short.log`: `Ran 236 tests in 216.419s` — `OK` (230 của B4 + 6 mới; 0 skip; test chập
  chờn OK lần này). G1 trong đó: "[DoD7-guard] known=9 allowed=36", "[scope] serving=45 main=59"; tests.test_level1_guard OK.

- Đo thử tại commit sạch 3ebc7b9 (code_dirty false; KHÔNG phải báo cáo, JSON trong `_work/`, không commit; số chính thức: B7):
  `python level1_demo.py --source data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4 --pace realtime --headless --out-json
  _work/_plan15/b5_paced_headless.json` và cùng lệnh không `--headless` (cửa sổ thật, tự đóng) → `_work/_plan15/b5_paced_gui.json`.
  Máy: cpu "Intel64 Family 6 Model 186 Stepping 2, GenuineIntel", Windows-10-10.0.26200, mediapipe 0.10.14, torch 2.6.0+cu124;
  nguồn: clip TRAIN hauuto 640×480, fps file 23.584, 75 khung. Số đọc từ JSON (in bằng script đọc JSON):
  headless-paced: processed 48 / read 75, dropped 27, processing_fps 14.94, capture_fps 23.91; p50 mediapipe 63.6, frame_total 87.4,
  capture_age 21.7 (ms); warmup mediapipe_first 173.0, classify_first 28.8.
  cửa sổ-paced: processed 36 / read 75, dropped 39, processing_fps 11.08; p50 mediapipe 69.9, hud 6.6 (p95 40.9 = lúc panel PIL vẽ lại),
  display 2.5, frame_total 102.2 (p95 154.8); classify 29.7, emit_to_token 127.0 (n = 1).
  Nhận xét cho planner (không phải điểm dừng): trên máy này MediaPipe (model_complexity 1, giữ như train) chậm hơn nhịp khung clip →
  khoảng một nửa số khung bị bỏ ở chế độ realtime → khung không cách đều khi vào `resample: frame_index` (rủi ro §6.1 "Nhịp khung")
  là có thật; độ chính xác chưa đo.

## Việc người dùng — U1 (sau B3, ~10 phút; không chặn)
Từ gốc repo, trong .venv: `.venv\Scripts\python level1_demo.py --source 0 --display-mirror`
(thêm `--out-json _work/u1_webcam.json` nếu muốn xem JSON; không commit). Ký lần lượt vài chữ (a, b, c, o, dấu sắc) rồi 2 từ "ba", "cá"
(giữ yên mỗi chữ cho tới khi thanh xanh đầy; hạ tay ~1 giây để kết thúc từ; chữ lặp "oo" cần nảy tay hoặc nhấn `r`). Nhận xét: chấm có
bám tay không, chữ có tự tách không, có phát lặp khi giữ yên không, độ trễ cảm nhận. Nếu webcam không mở: thử `--source 1`, hoặc đổi
`camera_api` trong configs/level1_realtime.json sang "msmf"/"any" (ghi lại).

## Việc người dùng — U2 (sau B5, ~15 phút; không chặn)
Từ gốc repo, trong .venv, KHI KHÔNG có thay đổi chưa commit ở level1_demo.py / src / configs/level1_realtime.json (để code_dirty = false,
AC-L L3). 4 từ × 3 lần, mỗi lần một lệnh (n = 1, 2, 3; ký xong nhấn `q`):
`.venv\Scripts\python level1_demo.py --source 0 --display-mirror --expected "ba" --out-json reports/level1_realtime_<D>/webcam_ba_<n>.json`
tương tự `--expected "cá"` → `webcam_ca_<n>.json`, `"mẹ"` → `webcam_me_<n>.json`, `"xoong"` → `webcam_xoong_<n>.json` (nảy tay giữa
hai chữ o, hoặc nhấn `r`). `<D>` = ngày chạy dạng YYYY-MM-DD (orchestrator thống nhất với thư mục B7). JSON chỉ chứa token, sự kiện, thời
gian, thống kê; không có video/khung/landmark. Không dùng các phiên này để chỉnh tham số.

## Quyết định / giả định của coder
- `load_level1_config` chốt ở `src/inference/level1_core.py` (đúng bảng §3.1); kiểm thêm khóa lạ, kiểu, `source` ∈ {design, "calibrated: …"}.
- Bộ tách import `normalize_hand_landmarks` từ `src/data/alphabet_preprocessing.py` (một nơi cho chuẩn hóa, skill mục 6); bản thân
  module không dùng cv2/torch nhưng import này kéo theo torch (alphabet_preprocessing import torch ở đầu file).
- Bộ tách: phân loại đứng yên/di chuyển chỉ cập nhật trên khung CÓ tay; khung mất tay ngắn (< hand_lost_ms) không cắt chuỗi đứng yên.
  Đổi kích thước khung giữa chừng → đóng bộ đệm như mất tay. Segment bỏ khung không tay ở đầu/cuối.
- Speller: Space dùng cùng luật với WordGap (không thêm " " khi rỗng hoặc token cuối đã là " "); `r` chỉ lặp khi token cuối là CHỮ CÁI;
  space tự động do WordGap ghi `source: "model"` + `reason: "word_gap"` (không phải phím). Kết quả `too_few_frames`/`invalid` lưu là
  rejected không có prediction → `a` không nhận được gì.
- Classifier: `too_few_frames` xét bằng số khung có tay < `min_detected_frames` của checkpoint (gộp DEFAULT_ALPHABET_PREPROCESSING như
  alphabet_clip_features) TRƯỚC khi gọi alphabet_clip_features; ValueError khác vẫn ném ra.
- Giá trị thiết kế trong `configs/level1_realtime.json` (B1) — `source: "design"`, lý do ghi trong file; chưa hiệu chỉnh (B6b ngoài chặng này).

## Nhật ký detect-changes
(ghi trước mỗi commit)
- B0 (trước commit `15: B0`): `node .gitnexus/run.cjs analyze --index-only` rồi `detect-changes --scope all` → "Changes: 4 files,
  1 symbols, Affected processes: 192, Risk level: critical". 4 file = thay đổi CHƯA COMMIT CỦA NGƯỜI DÙNG (` M README.md` + 3 ` D`),
  không phải của 15; symbol đổi duy nhất "Section → README.md". File mới của 15 là untracked nên detect-changes không thấy.
  Commit B0 chỉ gồm `docs/plans/15-progress.md`.
- B1 (trước commit `15: B1`): analyze --index-only (exit 0) rồi detect-changes → "Changes: 4 files, 1 symbols, Affected processes: 164,
  Risk level: critical" — vẫn chỉ là 4 thay đổi chưa commit của người dùng (README + 3 ` D`); file mới của 15 untracked (không symbol có sẵn
  nào bị sửa, nên không cần impact).
- B2 (trước commit `15: B2`): analyze (exit 0) rồi detect-changes → "Changes: 7 files, 10 symbols, Affected processes: 176, Risk level:
  critical". Symbol đổi: Section → README.md (người dùng) + symbol MỚI của 15: class_kind, Level1Classifier, Level1Speller
  (level1_core.py), segment_from_npz, TestClassifierC1C3, ok, TestSpellerC4C7, TestTimingAcT (tests/test_level1_core.py). Không symbol có
  sẵn ngoài 15 bị sửa.
- B3-WIP (trước commit `WIP 15: B3`): analyze (exit 0) rồi detect-changes → "Changes: 5 files, 2 symbols, Affected processes: 176,
  Risk level: critical"; symbol đổi: Section → README.md (người dùng), TestLevel1Guard (tests/test_level1_guard.py, của 15).
  level1_demo.py + tests/test_level1_demo.py là file mới (untracked) nên chưa hiện.
- B3 (trước commit `15: B3`): analyze (exit 0) rồi detect-changes → "Changes: 6 files, 4 symbols, Affected processes: 164, Risk level:
  critical"; symbol đổi: Section → README.md (người dùng), Level1App (level1_demo.py), TestHeadlessD2 + TestDefaultPaths
  (tests/test_level1_demo.py) — đều của 15. Không symbol có sẵn ngoài 15 bị sửa.
- B4 (trước commit `15: B4`): analyze --index-only (exit 0) rồi detect-changes → "Changes: 5 files, 3 symbols, Affected processes: 174,
  Risk level: critical"; symbol đổi: Section → README.md (người dùng), 2 Section của docs/plans/15-progress.md. File test mới untracked
  nên chưa hiện. Không symbol có sẵn nào bị sửa (không cần impact).
- B5 (trước commit `15: B5`): analyze --index-only (exit 0) rồi detect-changes → "Changes: 7 files, 15 symbols, Affected processes: 176,
  Risk level: critical"; symbol đổi: Section → README.md (người dùng), 3 Section của 15-progress.md, HUD_STAGE_LABELS / CaptureThread /
  Hud / Level1App (level1_demo.py), FRAME_STAGES / SIGN_STAGES / DRAWN_STAGES / TMP_PARENT / _WindowRecorder / TestLatencyAcL /
  TestHudStatsLines (tests/test_level1_demo.py) — đều của 15. Process "affected" (run_harmonized, measure_and_compare…) là trùng tên,
  không phải người gọi thật (xem mục B5 impact).
- B5-progress (trước commit `15: B5 tiến độ`): analyze --index-only (exit 0) rồi detect-changes → "Changes: 5 files, 5 symbols, Affected
  processes: 174, Risk level: critical"; symbol đổi: Section → README.md (người dùng) + 4 Section của 15-progress.md. Chỉ tài liệu.
- A1-code (trước commit `15: A1 — scripts/level1_segment_report.py + test AC-R'1`): analyze --index-only (exit 0) rồi detect-changes → "Changes: 6 files, 5 symbols, Affected processes: 175, Risk level: critical". Symbol đổi: Section README.md (người dùng) + 4 Section của 15-progress.md. Commit code `72167b9`.
- A1-báo cáo: sinh `reports/level1_realtime_2026-10-03/tone_evidence.json` tại commit sạch `72167b9`. Chạy analyze --index-only và detect-changes trước commit báo cáo.
- T2 (trước commit `15: T2`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 4 files, 1 symbols, Affected processes: 170, Risk level: critical". Symbol đổi: Section ? → README.md (người dùng). Index sạch, không có partial/truncated.
- A2-code (trước commit `15: A2 — tail_still_keep_ms + --write-config + test`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 11 files, 7 symbols, Affected processes: 174, Risk level: critical". Symbol đổi: Section ? → README.md (người dùng) + symbol của A2: CALIBRATED_KEYS, DEFAULT_EVIDENCE (scripts/level1_segment_report.py), Level1SignSegmenter (src/inference/level1_segmenter.py), TestConfigC8 (tests/test_level1_core.py), TestWriteConfig (tests/test_level1_segment_report.py), TestSegmenter (tests/test_level1_segmenter.py). Index sạch, không có partial/truncated.
- A2-config (trước commit `15: A2 config hiệu chỉnh`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 5 files, 1 symbols, Affected processes: 174, Risk level: critical". Symbol đổi: Section ? → README.md (người dùng). Index sạch, không có partial/truncated.
- R0-code (trước commit `15: R0 — scripts/level1_rearm_check.py + test AC-RC1..RC4`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 5 files, 3 symbols, Affected processes: 0, Risk level: low". Symbol đổi: Section ? → README.md (người dùng) + Section 15-progress.md. File mới untracked. Index sạch, không có partial/truncated. Commit code `a3970a6`.
- R0-báo cáo: sinh `reports/level1_realtime_2026-10-04/rearm_check_r0.json` tại commit mã sạch `a3970a6` (`code_dirty: false`).
- A2a (cloud, trước commit `15: A2a`): `npx -y gitnexus@latest analyze` (đầu phiên) rồi `node .gitnexus/run.cjs analyze --index-only` (exit 0) và `detect-changes --scope all --repo .` → "Changes: 3 files, 21 symbols, Affected processes: 8, Risk level: high"; không có cờ partial/truncated. Symbol đổi: các Section của 15-progress.md + `scripts/level1_rearm_check.py` (GIT_SPEC_PREFIX, FILL_RULES, _git_bytes, _fill_missing, resolve_config_spec, load_and_prepare_manifest_clips, run_rearm_check) + `tests/test_level1_rearm_check.py` (TestConfigProvenanceA2a, _git_out). 8 luồng bị ảnh hưởng đều là `main` của scripts/level1_rearm_check.py. Risk HIGH = chỉ trong script R0 (không có người gọi ngoài script + test). Không có thay đổi chưa commit của người dùng trên cloud.
- R1 (cloud, trước commit `15: R1`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 6 files, 20 symbols, Affected processes: 8, Risk level: high"; không có cờ partial/truncated. Symbol đổi: SEGMENTER_KEYS, pose_distance (mới), Level1SignSegmenter (__init__, reset, _clear_pose_state (mới), _close_lost, push), CONFIG_SPEC, _check_value, FILL_RULES, _fill_missing, TestConfigProvenanceA2a + test của nó, file test mới tests/test_level1_rearm.py. 8 luồng bị ảnh hưởng: `main`/`run_segmenter_on_stream` của scripts/level1_rearm_check.py và `main` → `_check_value` (load config) — đều thuộc kế hoạch 15.
- A2b-code (cloud, trước commit `15: A2b — write_config …`): `analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 2 files, 17 symbols, Affected processes: 2, Risk level: medium"; không có cờ partial/truncated. Symbol đổi: `scripts/level1_segment_report.py` (CALIBRATION_REASONS, committed_evidence_ref (mới), write_config) + `tests/test_level1_segment_report.py` (TestWriteConfigA2b + helper). 2 luồng: `main` → `write_config` của script.
- R2-code (cloud, trước commit `15: R2 — code`): `analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 1 files, 15 symbols, Affected processes: 14, Risk level: high"; không có cờ partial/truncated. Symbol đổi: chỉ `scripts/level1_segment_report.py` (longest_still_run, POSE_*, hand_shape, _session, clip_pose_profile, pose_calibration, pose_report, write_pose_config, main); file test mới untracked chưa hiện. 14 luồng đều là `main` của script → hàm mới / bộ tách (chỉ GỌI). Impact `main`: LOW lower-bound (người gọi: điểm vào CLI + test).
- R3-code (cloud, trước commit `15: R3 — code`): `analyze --index-only` (exit 0) rồi `detect-changes --scope all --repo .` → "Changes: 1 files, 22 symbols, Affected processes: 9, Risk level: high"; không có cờ partial/truncated. Symbol đổi: chỉ `scripts/level1_rearm_check.py` (NOTE_VI, GATE_*, calculate_metrics, parse_override, apply_overrides, single_clip_rates, evaluate_gates, whole_clip_segment, write_rules_config, run_rearm_check, create_parser, main …); file test mới untracked chưa hiện. 9 luồng đều là `main` của script. Impact trước sửa (upstream): calculate_metrics / run_rearm_check / create_parser LOW (exact, chỉ trong script), main LOW lower-bound (CLI).

## T1 — textbox logic + tone keys
- File: `src/inference/level1_textbox.py`, `tests/test_level1_textbox.py`, `src/inference/level1_core.py` (`Level1Speller.view`, `KEY_NAMES`, `key`), `tests/test_level1_core.py` (AC-K), `tests/test_level1_guard.py` (`PLAN15_FILES`).
- AC-TB: Viết trước test, sau đó code (AC-TB1..8 OK).
- AC-K: Phím `tone_1`..`tone_5` thêm đúng dấu và giữ đúng text.
- G2/G3: `test_level1_guard` chạy thành công; thêm `level1_textbox.py` vào `PLAN15_FILES`, không có finding mới ở code của 15.
- AC1-ngắn (16 module của B5 + `tests.test_level1_textbox`) → `_work/_plan15/t1_short.log`: `Ran 245 tests in 108.524s` — `OK`, 0 skip (orchestrator chạy lại độc lập, 3/10 ~22:30). [Sửa dòng cũ của coder agy ghi "Ran 78": 78 chỉ là 6 module level 1, không phải AC1-ngắn.]
- detect-changes trước commit (agy ghi): `Changes: 9 files, 6 symbols`. Impact `Level1Speller` do coder KHÔNG ghi trước khi sửa; orchestrator chạy bổ sung sau: `risk UNKNOWN`, 0 caller trong đồ thị → kiểm bằng text search: người gọi thật chỉ `level1_demo.py` + `tests/test_level1_*.py`, đều nằm trong 245 test OK ở trên (các kết quả khác của `.view(` là PyTorch).
- Commit `92fce21` trên nhánh `feat/vslt-complete` (có trên origin lúc orchestrator kiểm). Coder agy KHÔNG được push; dòng "Đã push" cũ của agy đã bỏ.

## A1 — bằng chứng dấu thanh + hiệu chỉnh tách đoạn (scripts/level1_segment_report.py + AC-R'1)
- File: `scripts/level1_segment_report.py`, `tests/test_level1_segment_report.py`.
- Impact trước khi sửa: `u1_summary` và `calibrate` (risk UNKNOWN, symbol mới; kiểm bằng text search: chỉ gọi nội bộ trong script và test của nó).
- Bổ sung/sửa nhỏ trong script: xử lý cấu trúc `config.values` dạng dict `{value, source, reason}` trong `u1_summary`; xử lý an toàn danh sách rỗng cho `moving_p` và `tone_moving_p` trong `calibrate`.
- Test `tests/test_level1_segment_report.py` (8 test):
  - R'1a: `nested_per_class` kiểm lại out-of-fold `nested_predictions.csv` khớp `nested_report.json` từng fold (|diff| <= 1e-9) và mean khớp 40.83% (sai số <= 1e-9); đếm đúng 120 clip dấu (49 đúng: huyền 2, nặng 18, hỏi 8, sắc 10, ngã 11).
  - R'1b: `motion_series` trên 2 clip npz cố định (`hauuto_a_hau_A_001` và `hauuto_tone_s_hau_A_001`) khớp từng phần tử với chuỗi `seg.motion` khi push từng khung vào `Level1SignSegmenter`.
  - R'1c: `calibrate` tính đúng quy tắc 1–6 trên số kiểm soát; kiểm nhánh `no_motion` và nhánh quy tắc 6 `triggered == True`.
  - `variants_summary` và `u1_summary`: đọc đúng cấu trúc, sha256 64 hex, tổng hợp 105 segment của U1.
- Kết quả test:
  - `python -m unittest tests.test_level1_segment_report -v` → `Ran 8 tests` `OK`.
  - `python -m unittest tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_guard -v` → `Ran 77 tests in 26.202s` `OK`, 0 skip.
  - AC1-ngắn (18 module): `Ran 253 tests in 99.857s` `OK`, 0 skip. E1 bằng hệt cả 10 clip; guard DoD7 known=9, allowed=36.
- Commit code: `72167b9` (`15: A1 — scripts/level1_segment_report.py + test AC-R'1`).
- Báo cáo `reports/level1_realtime_2026-10-03/tone_evidence.json` (sinh tại commit sạch `72167b9`):
  - Lệnh: `python scripts/level1_segment_report.py --out reports/level1_realtime_2026-10-03/tone_evidence.json --u1-json _work/_plan15_u1/u1_2026-10-03_1650.json`
  - git_commit: `72167b9057baf00928f63c481e822aba9fd27fd2`, code_dirty: False, clips=636.
  - Giá trị hiệu chỉnh: still_speed: 2.5306, move_speed: 5.0612, hold_ms: 400.0, max_segment_ms: 3543, tail_still_keep_ms: 400.0.
  - Quy tắc 6 (điểm dừng tách dấu): p90_tone_longest_internal_still_ms = 359.22 ms < hold_ms = 400.0 ms -> triggered: false (KHÔNG kích hoạt điểm dừng).
- Commit báo cáo: `reports/level1_realtime_2026-10-03/tone_evidence.json` + `docs/plans/15-progress.md`.

## T2 — vẽ khung text trong Hud + map phím 1–5 (KEY_ACTIONS) + test AC-TD1..TD7
- File: `level1_demo.py`, `tests/test_level1_demo.py`.
- Tiếp tục và hoàn thiện từ commit WIP `ad7c126` (khung text trong Hud + phím 1–5).
- Impact GitNexus (upstream):
  - `Hud`: risk `UNKNOWN`, direct 0, processes_affected 0. Text search xác nhận: chỉ dùng trong `level1_demo.py:543` và `tests/test_level1_demo.py` (đều của 15).
  - `KEY_ACTIONS`: risk `UNKNOWN`, direct 0, processes_affected 0. Text search xác nhận: chỉ dùng nội bộ trong `level1_demo.py:623-624` (`Level1App._key`).
  - `_hud_lines`: risk `CRITICAL` (direct 57, processes_affected 22, modules_affected 8 — do trùng tên / false positives cross-process). Text search xác nhận: private method của `Level1App`, chỉ gọi trong `level1_demo.py:678`.
  - `Level1App`: risk `UNKNOWN`, direct 0, processes_affected 0. Text search xác nhận: chỉ dùng trong `level1_demo.py`, `tests/test_level1_demo.py`, `tests/test_level1_equivalence.py`.
- Bảng đối chiếu AC-TD1…TD7 ↔ tên test trong `tests/test_level1_demo.py`:
  | Tiêu chí | Mô tả | Tên test trong `tests/test_level1_demo.py` | Kết quả |
  |---|---|---|---|
  | AC-TD1 | Ảnh camera không bị che (array_equal phần camera) | `TestHudTextboxAcTD.test_td1_camera_image_not_covered` | OK |
  | AC-TD2 | Nền tô sáng trong active, không có trong committed | `TestHudTextboxAcTD.test_td2_highlight_in_active_not_committed` | OK |
  | AC-TD3 | Cột con trỏ có màu con trỏ | `TestHudTextboxAcTD.test_td3_cursor_column_has_cursor_color` | OK |
  | AC-TD4 | Màu mờ preview khi có preview, không có khi không preview | `TestHudTextboxAcTD.test_td4_preview_muted_color_right_of_cursor` | OK |
  | AC-TD5 | Văn bản dài (40 âm tiết) con trỏ nằm trong panel, có "…" | `TestHudTextboxAcTD.test_td5_long_text_within_panel_and_ellipsis` | OK |
  | AC-TD6 | Cache panel khi cùng view, dựng lại khi view đổi | `TestHudTextboxAcTD.test_td6_caching` | OK |
  | AC-TD7 | Phím `ord("1")`..`ord("5")` qua `_key` thêm đúng dấu sắc/huyền/hỏi/ngã/nặng (`source == "key"`) | `TestHudTextboxAcTD.test_td7_keys_1_to_5` | OK |
  - Cơ chế font: `setUpClass` gọi `find_font`, không tìm thấy sẽ fail với `SourceError` chứ không skip (0 skip).
- Kết quả test thực tế:
  - 6 module Level 1 (`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_guard -v`):
    `Ran 84 tests in 59.471s` — `OK`, 0 skip, 0 fail (log: `_work/_plan15/t2_level1_suite.log`).
  - Guard chính (`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_backend_source_guard -v`):
    `Ran 28 tests in 4.543s` — `OK`, `[DoD7-guard] known=9 allowed=36`, `[scope] serving=45 main=60` (log: `_work/_plan15/t2_guard.log`).
  - AC1-ngắn 18 module (`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_fingerspelling_api tests.test_fingerspelling_compose tests.test_fingerspelling_limits tests.test_fingerspelling_deployed tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_alphabet_ckpt_provenance tests.test_status_privacy tests.test_backend_source_guard tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_equivalence tests.test_level1_guard tests.test_level1_textbox tests.test_level1_segment_report -v`):
    `Ran 260 tests in 268.320s` — `OK`, 0 skip, 0 fail (log: `_work/_plan15/t2_short.log`). E1 bằng hệt cả 10 clip.

## A2 — tail_still_keep_ms + validate_level1_config + --write-config
- File: `src/inference/level1_segmenter.py`, `src/inference/level1_core.py`, `configs/level1_realtime.json`, `scripts/level1_segment_report.py`, `tests/test_level1_segmenter.py`, `tests/test_level1_core.py`, `tests/test_level1_segment_report.py`.
- GitNexus Impact trước khi sửa:
  - `Level1SignSegmenter`: risk `UNKNOWN`, direct 0, processes_affected 0. Text search xác nhận: chỉ dùng trong `level1_demo.py`, `scripts/level1_segment_report.py`, `tests/test_level1_segment_report.py`, `tests/test_level1_segmenter.py`, `tests/test_level1_equivalence.py` (đều thuộc plan 15).
  - `SEGMENTER_KEYS`: risk `UNKNOWN`, direct 0, processes_affected 0. Text search xác nhận: chỉ dùng nội bộ trong `src/inference/level1_segmenter.py`.
  - `validate_level1_config`: risk `CRITICAL` (direct 1: `load_level1_config`, processes_affected 74 qua call graph tới main). Text search xác nhận: chỉ gọi trong `load_level1_config` (`src/inference/level1_core.py`), `scripts/level1_segment_report.py` và `tests/test_level1_core.py`.
  - `load_level1_config`: risk `CRITICAL` (direct 2: `Level1App.__init__` trong `level1_demo.py`, `build_report` trong `scripts/level1_segment_report.py`, processes_affected 74). Text search xác nhận: người gọi thật chỉ nằm trong plan 15 (`level1_demo.py`, `scripts/level1_segment_report.py`, `tests/test_level1_core.py`, `tests/test_level1_demo.py`, `tests/test_level1_segment_report.py`).
  - `CONFIG_SPEC`: risk `UNKNOWN`, direct 0. Text search xác nhận: chỉ dùng trong `src/inference/level1_core.py` và `tests/test_level1_core.py`.
  - `main` của `scripts/level1_segment_report.py`: risk `UNKNOWN`, direct 0. Text search xác nhận: điểm vào CLI và `tests/test_level1_segment_report.py`.
- Viết test trước (TDD đỏ):
  - `test_parameter_checks` (AC-S): kiểm `tail_still_keep_ms` <= 0 và > hold_ms; `test_s14_tail_still_keep_ms_equal_hold_ms` (AC-S14) và `test_s15_tail_still_keep_ms_less_than_hold_ms` (AC-S15).
  - `test_c8b_tail_still_keep_ms` (AC-C8b): thiếu khóa, <= 0 hoặc > hold_ms -> ValueError; config thật nạp được.
  - `test_r_prime_1d_write_config` (AC-R'1 d): `--write-config` chỉ đổi 5 khóa, nguồn khớp mẫu.
  - Chạy lần đầu khi chưa code: `FAILED (failures=3, errors=1)` (AC-S, AC-C8b, AC-R'1 d đều đỏ đúng kỳ vọng).
- Triển khai code:
  - `src/inference/level1_segmenter.py`: thêm `tail_still_keep_ms` vào `SEGMENTER_KEYS`; kiểm `0 < tail_still_keep_ms <= hold_ms` trong `__init__`; khi đóng segment vì lý do `hold`, lọc buffer chỉ giữ các khung có `ts <= _still_since + tail_still_keep_ms + 1e-6` (`t_emit` giữ nguyên `ts`, `hand_lost`/`end_of_stream` không đổi; `tail_still_keep_ms == hold_ms` cho kết quả giống hệt).
  - `src/inference/level1_core.py`: thêm `"tail_still_keep_ms": ("number", "positive")` vào `CONFIG_SPEC`; kiểm `0 < tail_still_keep_ms <= hold_ms` trong `validate_level1_config`.
  - `configs/level1_realtime.json`: thêm khóa `"tail_still_keep_ms"` với `value: 400`, `source: "design"`, lý do tiếng Anh.
  - `scripts/level1_segment_report.py`: thêm cờ `--write-config <path>` và hàm `write_config(config_path, evidence_path)`; đọc 5 giá trị từ `calibration.values` của `reports/level1_realtime_2026-10-03/tone_evidence.json` đã commit (`1ca53f3`), gán `source = "calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3"`, giữ nguyên các khóa khác và reason; validate trước khi ghi.
- Kết quả test kiểm chứng Commit 1:
  - 3 test module trực tiếp (`python -m unittest tests.test_level1_segmenter tests.test_level1_core tests.test_level1_segment_report -v`): `Ran 51 tests in 4.988s` — `OK`, 0 fail.
  - 6 module Level 1 (`tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_guard -v`): `Ran 88 tests in 54.499s` — `OK`, 0 fail, 0 skip.
  - AC-E1 tương đương (`tests.test_level1_equivalence -v`): `Ran 9 tests in 77.906s` — `OK`, cả 10 clip BẰNG HỆT (bit-identical).
  - Guard chính (`tests.test_backend_source_guard -v`): `Ran 28 tests in 4.470s` — `OK`, `[DoD7-guard] known=9 allowed=36`, `[scope] serving=45 main=60`.
  - AC1-ngắn 18 module: `Ran 264 tests in 270.856s` — `OK`, 0 fail, 0 errors, 0 skip (log: `_work/_plan15/a2_short_1.log`). Test chập chờn `test_reset_segments_and_graphs` pass.
- Bảng giá trị cấu hình cũ -> mới (in tự động bằng code từ `6067611:configs/level1_realtime.json` và `configs/level1_realtime.json`):
  | Khóa | Giá trị cũ (thiết kế) | Nguồn cũ | Giá trị mới (hiệu chỉnh) | Nguồn mới |
  |---|---|---|---|---|
  | `still_speed` | `1.0` | `design` | `2.5306153884920786` | `calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` |
  | `move_speed` | `2.0` | `design` | `5.061230776984157` | `calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` |
  | `hold_ms` | `400` | `design` | `400.0` | `calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` |
  | `max_segment_ms` | `4000` | `design` | `3543` | `calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` |
  | `tail_still_keep_ms` | `400` | `design` | `400.0` | `calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` |
- Kết quả test kiểm chứng sau hiệu chỉnh config (bước 6):
  - 6 module Level 1 (`tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_guard -v`): `Ran 88 tests in 54.093s` — `OK`, 0 fail, 0 skip (log: `_work/_plan15/a2_level1_suite.log`).
  - AC-E1 tương đương (`tests.test_level1_equivalence -v`): `Ran 9 tests in 79.116s` — `OK`, cả 10 clip BẰNG HỆT (bit-identical, log: `_work/_plan15/a2_equiv.log`).
  - Guard chính (`tests.test_backend_source_guard -v`): `Ran 28 tests in 4.236s` — `OK`, `[DoD7-guard] known=9 allowed=36`, `[scope] serving=45 main=60` (log: `_work/_plan15/a2_guard.log`).
  - AC1-ngắn 18 module: `Ran 264 tests in 225.786s` — `OK`, 0 fail, 0 errors, 0 skip (log: `_work/_plan15/a2_short_2.log`).

## R0 — ghép chuỗi train clip kiểm re-arm (scripts/level1_rearm_check.py + AC-RC1..RC4)
- File: `scripts/level1_rearm_check.py`, `tests/test_level1_rearm_check.py`.
- TDD viết test trước: `tests/test_level1_rearm_check.py` (9 test) bao phủ AC-RC1..RC4.
  - RC1: bỏ khung không tay đầu/cuối; clip mất tay bên trong >= hand_lost_ms (200ms) bị loại (đoán và đếm đúng 9 clip hauuto); kích thước/fps lệch bị loại và đếm.
  - RC2: `join_ms == 0` không có khung chèn; `join_ms > 0` đúng `round(J * fps / 1000)` khung nội suy tuyến tính landmark thô, nguồn `join`, handedness của clip trước.
  - RC3: gán đa số nguồn, segment rác (đa số `join`), `order_ok`, các tỉ lệ (`one_rate`, `miss_rate`, `multi_rate`, `garbage_per_clip`, `hand_lost`, `one_rate_covered`) trên chuỗi tổng hợp 3 clip.
  - RC4: `--join-ms` là bắt buộc (không mặc định); JSON đầy đủ `generated_by`, `sha256` config, và câu thông báo `"train clips concatenated to test the segmenter logic; not accuracy, not a webcam session"`.
- Kết quả test kiểm thử mã R0:
  - Unit test mới: `python -m unittest tests/test_level1_rearm_check.py -v` → `Ran 9 tests in 0.181s` — `OK`.
  - 7 module Level 1: `Ran 97 tests in 60.547s` — `OK`, 0 fail, 0 skip.
  - Guard chính (`tests.test_backend_source_guard -v`): `Ran 28 tests in 4.419s` — `OK`, `known=9 allowed=36`, `serving=45 main=60`.
  - AC1-ngắn 19 module (`tests.test_alphabet_preprocessing` .. `tests.test_level1_rearm_check`): `Ran 273 tests in 293.031s` — `OK`, 0 fail, 0 errors, 0 skip. AC-E1 bit-identical cả 10 clips.
- Commit code: `a3970a6` (`15: R0 — scripts/level1_rearm_check.py + test AC-RC1..RC4`).
- Báo cáo `reports/level1_realtime_2026-10-04/rearm_check_r0.json` (sinh tại commit sạch `a3970a6`):
  - Lệnh: `python scripts/level1_rearm_check.py --config current=configs/level1_realtime.json --config before_a2=_work/_plan15/config_before.json --join-ms 0,300,600 --out reports/level1_realtime_2026-10-04/rearm_check_r0.json`
  - `git_commit`: `a3970a682cd77e5ed3d65265f85f03d9abc52f9f`, `code_dirty`: `False`.
  - Số liệu đọc trực tiếp từ JSON:
    | Config | Chuỗi | Join (ms) | n_clips | one_rate | miss_rate | multi_rate | garbage/clip | hand_lost | order_ok |
    |---|---|---|---|---|---|---|---|---|---|
    | `current` | L | 0 | 193 | 0.3109 | 0.6684 | 0.0207 | 0.0000 | 0 | True |
    | `current` | L | 300 | 193 | 0.3731 | 0.6010 | 0.0259 | 0.0000 | 0 | True |
    | `current` | L | 600 | 193 | 0.3109 | 0.6632 | 0.0259 | 0.0104 | 0 | True |
    | `current` | T | 0 | 70 | 0.7714 | 0.2286 | 0.0000 | 0.0000 | 0 | True |
    | `current` | T | 300 | 70 | 0.8000 | 0.2000 | 0.0000 | 0.0000 | 0 | True |
    | `current` | T | 600 | 70 | 0.7429 | 0.2571 | 0.0000 | 0.0000 | 0 | True |
    | `current` | O | 0 | 25 | 0.6400 | 0.3600 | 0.0000 | 0.0000 | 0 | True |
    | `current` | O | 300 | 25 | 0.6400 | 0.3600 | 0.0000 | 0.0000 | 0 | True |
    | `current` | O | 600 | 25 | 0.6400 | 0.3600 | 0.0000 | 0.0000 | 0 | True |
    | `before_a2` | L | 0 | 193 | 0.4145 | 0.5699 | 0.0155 | 0.0000 | 0 | True |
    | `before_a2` | L | 300 | 193 | 0.6632 | 0.3005 | 0.0363 | 0.0000 | 0 | True |
    | `before_a2` | L | 600 | 193 | 0.4819 | 0.4922 | 0.0259 | 0.0104 | 0 | True |
    | `before_a2` | T | 0 | 70 | 0.8857 | 0.1000 | 0.0143 | 0.0000 | 0 | True |
    | `before_a2` | T | 300 | 70 | 0.8714 | 0.0429 | 0.0857 | 0.0000 | 0 | True |
    | `before_a2` | T | 600 | 70 | 0.8857 | 0.1000 | 0.0143 | 0.0000 | 0 | True |
    | `before_a2` | O | 0 | 25 | 0.6800 | 0.3200 | 0.0000 | 0.0000 | 0 | True |
    | `before_a2` | O | 300 | 25 | 0.6800 | 0.3200 | 0.0000 | 0.0000 | 0 | True |
    | `before_a2` | O | 600 | 25 | 0.6800 | 0.3200 | 0.0000 | 0.0000 | 0 | True |
    _(Bảng trên SINH LẠI bằng code từ JSON ở A2a, cloud 2026-10-04, làm tròn 4 chữ số; thay bảng gõ tay cũ của 1acb4a5 có 4 chỗ sai: chuỗi T `n_clips` ghi 35 ở cả 6 dòng — JSON là 70; `current` L join 600 `garbage/clip` ghi 0.0000 — JSON 0.0104; `before_a2` L join 600 `garbage/clip` ghi 0.0000 — JSON 0.0104 (chỗ này prompt cloud không nêu, phát hiện khi sinh lại); `before_a2` L join 0 `miss_rate` ghi kèm "(57.00%)" — JSON 0.5699… = 56.99%. Các số khác của bảng cũ khớp JSON.)_
  - **Áp dụng luật R0 (§5):**
    - Điều kiện bác bỏ: `config 'current', chuỗi L, join 0 VÀ 300 đều có one_rate >= 0.90` -> giả thuyết sai.
    - Kết quả đo: join 0 có `one_rate = 0.3109 < 0.90`, join 300 có `one_rate = 0.3731 < 0.90`.
    - Kết luận luật R0: Giả thuyết ĐÚNG (bộ tách hiện tại bị kẹt chuyển chữ cái liên tiếp, miss tới 60–67% do thiếu re-arm tư thế). KHÔNG BỊ BÁC BỎ, ĐI TIẾP sang các bước tiếp theo.
  - **Số đếm cặp hold -> segment liền nhau của U1 (§2.2):**
    - Lệnh: `python -c "import json;e=json.load(open('_work/_plan15_u1/u1_2026-10-03_1650.json',encoding='utf-8'))['events'];print(sum(1 for a,b in zip(e,e[1:]) if a.get('close_reason')=='hold' and b['event']=='segment'))"`
    - Kết quả: `64` cặp.


  - **(c) Clip bị loại vì `min_detected_frames` (ghi bổ sung ở A2a, cloud 2026-10-04):** script R0 (`load_and_prepare_manifest_clips`) loại clip có số
    khung có tay < `min_detected_frames` của checkpoint TRƯỚC khi cắt đầu/cuối — bộ lọc này KHÔNG có trong §3.5 của 15-lan-sua-3 (lệch đặc tả,
    ghi nhận). Lý do giữ: (1) cùng bộ lọc với A1 (`scripts/level1_segment_report.py` `load_train_clips(manifest, min_detected_frames)`; AC-R1 / R'2
    "MỌI clip hauuto có ≥ `min_detected_frames` khung có tay"); (2) clip như vậy không thể tạo segment riêng (min_frames của bộ tách =
    max(`min_sign_frames`, `min_detected_frames`)) và `alphabet_clip_features` từ chối nó ⇒ luôn là "miss" không liên quan tới re-arm.
    Số đếm từ JSON `manifest_summary`: n_manifest_hauuto 640, n_prepared_clips 628, excluded `min_detected_frames` 4, `internal_hand_lost` 8
    (liệt kê id), `no_hand_frames` 0. JSON cũ không liệt kê id của 4 clip min_detected_frames → A2a thêm `min_detected_frames_sample_ids` và
    `no_hand_frames_sample_ids` vào `excluded` (có hiệu lực từ lần sinh lại). Ghi chú: dòng RC1 ở trên ghi "đếm đúng 9 clip hauuto" — JSON R0
    ghi `internal_hand_lost` = 8 (+ 4 min_detected_frames = 12 clip bị loại).

## A2a — hoàn tất luật cắt đuôi (15-lan-sua-2 §2, §4, §7) — phiên cloud 2026-10-04, nhánh `cloud/2026-10-04-level1-rearm`
- Mã A2a KHÔNG viết lại: nằm ở WIP `dddfde8` (`src/inference/level1_segmenter.py` +8/−3: `tail_still_keep_ms >= hold_ms` ⇒ không lọc
  (`buf_for_seg = self._buf`), ngược lại `cutoff = ts − (hold_ms − tail_still_keep_ms)`, lọc `ts ≤ cutoff + 1e-6`; docstring mô-đun;
  `tests/test_level1_segmenter.py` +218: AC-S16, AC-S17, AC-S18). Đã đọc `git show dddfde8`: khớp 15-lan-sua-2 §2 và §4.
- Môi trường cloud: Linux, Python 3.11.15, mediapipe 0.10.14, torch 2.6.0+cpu (`.venv` → `/opt/vslt-venv`). **KHÔNG có dữ liệu gitignored**:
  biến `KAGGLE_KEY` của environment cloud là chuỗi giữ chỗ của docs/CLOUD.md (không phải key) ⇒ không khôi phục được `manifest.csv`/npz,
  `checkpoints/alphabet_best.pt`, `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv`, video hauuto. Mọi test cần dữ liệu
  ERROR/FAIL/skip vì thiếu file — KHÔNG coi là pass (liệt kê ở dưới).
- **Đỏ tại 6067611 (cloud):** worktree tạm tại `6067611` + `tests/test_level1_segmenter.py` của HEAD →
  `Ran 23 tests — FAILED (failures=3, errors=1)`: FAIL `test_s16…` (grid `dt_33_47`), FAIL `test_s16…` (grid `fps_23.584`), FAIL `test_s17…`
  (grid `fps_23.584`); ERROR `test_s18…` = `FileNotFoundError …/manifest.csv` (thiếu dữ liệu — KHÔNG phải bằng chứng đỏ của S18; bằng chứng
  đỏ S18 là log local của orchestrator `_work/_bridge_verify/red_6067611.log`, failures=4, theo STATE.md). Log cloud: `_work/_cloud/red_6067611.log`.
- **Xanh ở HEAD (cloud):** `python -m unittest tests.test_level1_segmenter -v` → `Ran 23 tests — FAILED (errors=1)`: s16, s17 ok; lỗi duy nhất
  là `test_s18…` ERROR thiếu manifest. ⇒ **S18 (636+ clip thật, bằng hệt 4a55bf0) CHƯA kiểm được trên cloud — local PHẢI chạy lại**
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_segmenter -v` trước khi coi A2a là xong.
- **Impact (GitNexus qua `npx -y gitnexus@latest analyze`, rồi `node .gitnexus/run.cjs impact <symbol> --direction upstream --repo .`):**
  - `Level1SignSegmenter` (class): risk LOW (exact), direct 3 = IMPORTS từ `level1_demo.py`, `scripts/level1_rearm_check.py`,
    `scripts/level1_segment_report.py`; processes 0.
  - `Level1SignSegmenter.push` (method sửa ở A2a): **risk HIGH** (epistemic `lower-bound`: 16 call site bị bỏ vì không xác định kiểu receiver),
    direct 3 (`run_segmenter_on_stream`, `motion_series`, `Level1App._process`), processes_affected 4 (`main` của `scripts/level1_segment_report.py`,
    `level1_demo.py`, `scripts/level1_rearm_check.py`; `run_segmenter_on_stream`). CẢNH BÁO HIGH ghi nhận: mọi người gọi trong đồ thị là file của
    kế hoạch 15; text search `.push(` (ngoài `.venv`) thêm `src/inference/harmonized_live.py:157` và `tests/test_sign_segmenter.py` — đó là
    `push` của bộ tách Cấp 2 (`sign_segmenter`, lớp khác), không bị ảnh hưởng. Hành vi chỉ khác khi `tail_still_keep_ms < hold_ms`; config hiện
    hành có tail == hold == 400.0 ⇒ không đổi segment (AC-S18 khóa — chờ local).
  - `run_rearm_check`, `load_and_prepare_manifest_clips` (sửa (b)/(c) dưới): risk LOW (exact), direct 1, chỉ trong `scripts/level1_rearm_check.py`
    (+ `tests/test_level1_rearm_check.py` theo text search).
- **(a)** bảng R0 trong mục R0 ở trên được SINH LẠI từ JSON (4 chỗ sai của 1acb4a5 ghi ngay dưới bảng).
- **(b) `configs.before_a2.git_commit = ""`:** nguyên nhân: config TRƯỚC là file chưa track `_work/_plan15/config_before.json` ⇒
  `git log -1 --format=%H -- <file>` ra chuỗi rỗng. Tái hiện bằng script cũ (a3970a6 nạp từ `git show`, config 3ebc7b9 điền tail = hold, file
  chưa track) → `configs.before_a2.git_commit = ''` (`_work/_cloud/a2a_b_red.log`). Sửa trong `scripts/level1_rearm_check.py`:
  - hàm mới `resolve_config_spec`: `NAME=git:REV:PATH` đọc config bằng `git show REV:PATH` (không ghi file), điền khóa thiếu theo `FILL_RULES`
    (`tail_still_keep_ms = hold_ms` của chính config, ghi vào `configs.<name>.filled`), `git_commit` = hash đầy đủ của REV (lấy bằng git, không
    gõ), sha256 của blob git; `NAME=PATH`: `git_commit` = commit cuối của PATH chỉ khi PATH được track VÀ không có thay đổi chưa commit, ngược lại
    `None` (không bao giờ chuỗi rỗng) + `committed: false`.
  - `excluded` thêm `min_detected_frames_sample_ids`, `no_hand_frames_sample_ids` (mục (c)).
  - Test thêm (chỉ THÊM, không sửa test cũ) `tests/test_level1_rearm_check.py::TestConfigProvenanceA2a` (6 test): git spec → hash đầy đủ bắt
    đầu bằng 3ebc7b9, sha256 blob, `filled`, các giá trị khác bằng config gốc; HEAD spec không điền gì; path tracked sạch → commit cuối; path
    chưa track trong repo → `None`; `run_rearm_check` ghi đúng commit; spec sai → ValueError. Kết quả: `Ran 15 tests — OK`.
  - Lệnh sinh lại R0 (thay `--config before_a2=_work/_plan15/config_before.json`):
    `python scripts/level1_rearm_check.py --config current=configs/level1_realtime.json --config before_a2=git:3ebc7b9:configs/level1_realtime.json --join-ms 0,300,600 --out reports/level1_realtime_2026-10-04/rearm_check_r0.json`
    **CHƯA chạy được trên cloud (thiếu manifest/npz/checkpoint) ⇒ JSON R0 CHƯA sinh lại; số R0 cũ/mới: chưa có số mới.** Local chạy lệnh trên
    tại commit A2a sạch (sau commit này, TRƯỚC commit R1 — khi R1 thêm khóa config, config 3ebc7b9 thiếu thêm khóa tư thế) rồi so số với bảng R0.
- Test (cloud, không dữ liệu): 7 module Level 1 trước sửa (HEAD 3e6a15e) → `Ran 100 — FAILED (failures=1, errors=4, skipped=19)`; toàn bộ 5
  lỗi + 19 skip là do thiếu file gitignored (manifest.csv, nested_predictions.csv, checkpoint, video hauuto, file U1). Guard chính
  `tests.test_backend_source_guard` → `Ran 28 — OK`, `[DoD7-guard] known=9 allowed=36`; `tests.test_level1_guard` → `Ran 4 — OK`.

## R1 — luật re-arm theo tư thế (15-lan-sua-3 §3.2, §4 #3, §5 AC-RA1…RA11) — phiên cloud 2026-10-04
- File: `src/inference/level1_segmenter.py` (`pose_distance` public; `SEGMENTER_KEYS` + `pose_change_rules`, `rearm_pose_dist`; kiểm kiểu
  trong `__init__`; trạng thái `_anchor`, `_pose_since`, `_hold_ref`, `_recent_n` xóa ở `reset()`/`_close_lost`; luật 1–3 trong `push`; docstring),
  `src/inference/level1_core.py` (kind `"bool"` trong `_check_value` — chỉ nhận true/false thật; `CONFIG_SPEC` + `pose_change_rules` bool,
  `rearm_pose_dist` > 0, `pose_over_jitter_ratio` > 1), `configs/level1_realtime.json` (3 khóa mới, `source: design`: `pose_change_rules` false,
  `rearm_pose_dist` 1.0 GIỮ CHỖ — reason ghi "không đọc khi luật tắt, thay bằng P1 ở R2", `pose_over_jitter_ratio` 2.0; reason `rearm_move_ms`
  cập nhật chữ: bằng chứng liên tục cho cả re-arm chuyển động và tư thế; sinh bằng `json.dump(indent=2, ensure_ascii=False)` như `write_config`,
  các khóa khác giữ từng byte), `scripts/level1_rearm_check.py` (`FILL_RULES` điền thêm 3 khóa R1 cho config git cũ), test.
- **Impact trước sửa** (GitNexus, upstream): `SEGMENTER_KEYS` UNKNOWN (0 caller; text search: chỉ dùng trong `level1_segmenter.py`);
  `CONFIG_SPEC` UNKNOWN (text search: `level1_core.py` + `tests/test_level1_core.py`); `Level1SignSegmenter.__init__` UNKNOWN lower-bound (text search
  `Level1SignSegmenter(`: `level1_demo.py:544`, `scripts/level1_rearm_check.py`, `scripts/level1_segment_report.py`, tests của 15);
  `_check_value` LOW (direct: `validate_level1_config`); `validate_level1_config` LOW (direct: `load_level1_config`, `resolve_config_spec`,
  `write_config`); `reset` LOW (direct: `__init__`, `level1_demo.py` `_key`); **`_close_lost` HIGH** (direct: `flush`, `push` cùng lớp; 4 process
  qua các script/demo của 15); `push` HIGH lower-bound (xem mục A2a). Cảnh báo HIGH ghi nhận: mọi người gọi đều là file kế hoạch 15; luật tắt
  ⇒ không đọc `rearm_pose_dist`, không gọi `pose_distance` (AC-RA9 kiểm bằng mock: 0 lần gọi).
- **Test viết TRƯỚC (đỏ)** `tests/test_level1_rearm.py` (16 test) chạy trên mã trước R1 (HEAD b545ce7): `Ran 16 — FAILED (failures=14 (tính cả
  subTest), errors=6)`: RA1 và RA4 FAIL `['hold'] != ['hold', 'hold']` (tái hiện lỗi U1b: chỉ 1 segment khi đổi hình dạng tay không rút tay);
  RA7 ×3 ERROR (không có `_anchor`/`_pose_since`); RA9 ×2 ERROR (không có `pose_distance`); RA10 FAIL/ERROR (khóa mới chưa có, segmenter nhận
  tham số sai). RA2, RA3, RA5, RA6, RA8, RA11 + test kiểm chuỗi OK ngay trên mã cũ (đúng kỳ vọng: là tính chất "không được phá"). Log
  `_work/_cloud/r1_red.log`.
- **Xanh sau R1:** `python -m unittest tests.test_level1_rearm -v` → `Ran 16 — OK` (`_work/_cloud/r1_green.log`).
- Chuỗi test (tổng hợp có kiểm soát, docstring ghi rõ): hình dạng A/B giữ cổ tay và MCP giữa cố định ⇒ N tuyến tính, `pose_distance` biết trước;
  mọi khoảng cách trong assert tính bằng công thức viết tay trong test (không dùng hàm được kiểm). Params test riêng `PARAMS_RA`
  (motion_window 120 ms = trung vị 3 giá trị m; rearm_pose_dist 0.15). RA1: chuyển A→B 200 ms, tốc độ hình dạng 1.5 (giữa still 1.0 và move 2.0,
  test assert < move); segment 2 bắt đầu đúng khung đầu có d ≥ ngưỡng. RA4: chuyển 2 s, tốc độ 0.5 ≤ still, vượt ngưỡng sau 320 ms < hold 400
  (test assert cả hai). RA6: luật tắt ⇒ sự kiện bằng hệt giữa rearm_pose_dist 0.15 và 7.5 VÀ bằng hệt bộ tách của commit A2a (`b545ce7`, nạp
  bằng `git show`) trên 7 luồng RA + 4 luồng S16/S17 (2 lưới × tail = hold, hold/2). RA8: khung phát lệch 0.9×ngưỡng, sau đó tay dừng ở phía
  ngược 0.3×ngưỡng ⇒ neo 1 khung sẽ cách 1.2×ngưỡng (re-arm), neo trung bình cửa sổ 4 khung cách 0.525×ngưỡng (không) — test assert cả hai.
  RA11: `status()` đúng 4 khóa cũ, cùng giá trị với property, và bằng hệt `status()` của bộ tách A2a khi luật tắt.
- **Ngoại lệ test cũ (đúng §4 lần sửa 3):** `tests/test_level1_segmenter.py` PARAMS thêm `pose_change_rules: False, rearm_pose_dist: 0.2,
  pose_over_jitter_ratio: 2.0`; bộ dựng config AC-S18 (`s18_configs`) ép `pose_change_rules = False` cho (a) và điền 3 khóa cho (b) (3ebc7b9) —
  không đổi assertion. THÊM test `test_s18b_rearm_pose_dist_unused_when_rules_off` (§0 lần sửa 3: hai giá trị rearm_pose_dist ⇒ bằng hệt trên
  mọi clip hauuto) — cần dữ liệu, CHƯA chạy được trên cloud.
- **LỆCH cần reviewer xem (test A2a do chính phiên cloud viết ở b545ce7, chưa review):** 3 test `TestConfigProvenanceA2a` đỏ sau R1 vì config
  3ebc7b9 thiếu thêm 3 khóa R1 (không nạp được) và test ghim tập khóa điền = {tail_still_keep_ms}. Sửa: (1) mã — `FILL_RULES` điền
  `pose_change_rules = false` (luật chưa tồn tại ở commit đó ⇒ hành vi trước luật, AC-RA6) và `rearm_pose_dist`, `pose_over_jitter_ratio` lấy
  từ `configs/level1_realtime.json` trên đĩa (không được bộ tách đọc khi luật tắt), ghi vào `configs.<name>.filled`; (2) test — 2 assertion đổi:
  `filled` mong đợi thêm đúng 3 khóa R1 (`R1_KEYS`), vòng so giá trị bỏ qua đúng các khóa có trong `filled` (thay vì chỉ tail); test HEAD đổi
  từ `filled == {}` thành `set(filled) == các khóa CONFIG_SPEC thiếu ở HEAD` (test cũ đỏ ở MỌI lần thêm khóa config trước commit). Không nới:
  mọi khóa không điền vẫn so bằng hệt với blob git. Nếu reviewer không chấp nhận ⇒ hoàn tác 2 assertion, CẦN PLANNER.
- Quyết định nhỏ (không có trong đặc tả, ghi để review): (a) neo đặt mỗi khi luật hold kích hoạt (armed → False), kể cả khi `_make_segment`
  trả None sau cắt đuôi — để luôn có đường re-arm theo tư thế; (b) khung không tay (mất tay ngắn < hand_lost_ms) KHÔNG xóa `_pose_since`
  (đối xứng với `_move_since`: chỉ khung có tay cập nhật); (c) thứ tự trong một khung: phân loại still/move → luật 3 → theo dõi luật 2 →
  re-arm chuyển động → re-arm tư thế → `_trim` → kiểm phát hold; (d) KHÔNG thêm khóa tùy chọn `rearm` vào `status()` (giữ đúng 4 khóa);
  (e) cửa sổ neo đóng hai đầu [t_emit − motion_window_ms, t_emit] (khác cửa sổ chuyển động mở đầu trái) theo đúng chữ §3.2.
- Môi trường: venv cloud thiếu `seaborn` (có trong requirements.txt, thiếu trong `scripts/cloud_setup.sh`) ⇒ 6 module AC1 (backend) lỗi import;
  đã `pip install "seaborn>=0.12.0"` vào `.venv` (0.13.2), chạy lại mốc.
- **AC1-ngắn (19 module + tests.test_level1_rearm)**, so với mốc chạy cùng máy tại worktree sạch `b545ce7` (`_work/_cloud/ac1_base_b545ce7.log`):
  mốc `Ran 282 — FAILED (failures=1, errors=4, skipped=43)`; R1 `Ran 299 — FAILED (failures=1, errors=5, skipped=43)`. So từng test: KHÁC duy nhất
  là 16 test RA mới (ok) và `test_s18b…` mới (ERROR thiếu manifest). 1 FAIL + 4 ERROR + 43 skip còn lại GIỐNG mốc, đều do thiếu file gitignored
  (manifest/npz, checkpoint, video hauuto, nested_predictions.csv, file U1) — KHÔNG phải pass. `test_hand_landmarks_ws` (chập chờn) ok.
  Guard chính `known=9 allowed=36`, `tests.test_level1_guard` OK.
- CHỜ LOCAL (cần dữ liệu): AC-S18 + S18b trên clip thật (luật tắt bằng hệt 4a55bf0), AC-E1, AC-C1, AC-D, AC-R'1a/b.

## A2b — write_config: bỏ dự phòng commit gõ tay, reason theo quy tắc (15-lan-sua-2 §4 AC-W1…W3, §6, §7 #4b) — phiên cloud 2026-10-04
- Impact `write_config`: risk LOW (exact), direct 1 (`main` của `scripts/level1_segment_report.py`); text search: chỉ `main` + `tests/test_level1_segment_report.py`.
- Mã (`scripts/level1_segment_report.py`): hàm mới `committed_evidence_ref(evidence_path)` → (đường dẫn tương đối, commit rút gọn bằng
  `git rev-parse --short=7` của `git log -1 --format=%H -- <evidence>`); evidence chưa track / có thay đổi chưa commit / không có commit →
  `RuntimeError` TRƯỚC khi mở config (config không bị ghi). Bỏ dự phòng `generated_by.git_commit` và chuỗi gõ tay (grep `1ca53f3` trong
  `scripts/*.py` = 0). `write_config` ghi `reason` của 5 khóa = `CALIBRATION_REASONS[k]` (chuỗi cố định mô tả quy tắc của `calibrate()`, không
  chữ số); `changes` trả thêm `old_reason`/`new_reason`. Helper này sẽ được `--write-pose-config` (R2) dùng lại.
- Test viết TRƯỚC (`tests/test_level1_segment_report.py::TestWriteConfigA2b`, 5 test, dùng config/evidence tạm trong thư mục tạm chưa track của
  repo; không ghi config thật): W1 evidence chưa commit (bản sao có `generated_by.git_commit`) → RuntimeError + config giữ từng byte; W1 evidence
  bẩn (mock `git status` trả ` M …`) → RuntimeError + config giữ từng byte; W1 không còn `1ca53f3` trong `scripts/*.py`; W2 reason == hằng của
  script, không có chữ số, khác reason thiết kế ở b0620a9, thứ tự khóa giữ, khóa khác bằng hệt (so `json.dumps` từng khóa); W3 value 5 khóa
  bằng hệt `git show b0620a9:configs/level1_realtime.json` (so `json.dumps`, giữ kiểu int/float) và source == `calibrated: <evidence>@<short>`
  (short lấy bằng git trong test) == source ở b0620a9.
  - ĐỎ trên mã trước A2b (4c8c210): `Ran 6 — FAILED (failures=3, errors=1)`: W1 ×3 FAIL "RuntimeError not raised"/thấy `1ca53f3`, W2 ERROR
    (chưa có `CALIBRATION_REASONS`), W3 ok (đúng kỳ vọng: value không được đổi). Log `_work/_cloud/a2b_red.log`.
  - XANH sau mã: 5/5 ok (`_work/_cloud/a2b_green_code.log`).
- **Đỏ TẠM (đã biết trước, do thiết kế 2 commit của 15-lan-sua-2 §7 #4b):** test cũ A2 `TestWriteConfig.test_r_prime_1d_write_config` khẳng định
  `reason` sau ghi == `reason` của config thật trên đĩa. Ở commit mã A2b, config thật còn reason thiết kế cũ còn `write_config` ghi reason quy
  tắc (AC-W2) ⇒ FAIL tạm. Test KHÔNG sửa; nó xanh lại sau commit config sinh lại (bước dưới), vì khi đó config thật mang đúng reason quy tắc.
- Level 1 (8 module) ở commit mã: `Ran 128 — FAILED (failures=2, errors=5, skipped=19)` = 6 lỗi/19 skip thiếu dữ liệu như R1 + `test_r_prime_1d` đỏ tạm.
  Guard chính `known=9 allowed=36` OK.
- **A2b config (sinh lại tại commit mã sạch `71fc664`, `git status --porcelain -- scripts src configs` rỗng):**
  `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_segment_report.py --write-config configs/level1_realtime.json` (log
  `_work/_cloud/a2b_write_config.log`). **AC-W3 ĐẠT:** value 5 khóa bằng hệt `git show b0620a9:configs/level1_realtime.json` (so `json.dumps`:
  still_speed, move_speed, hold_ms 400.0 float, max_segment_ms 3543 int, tail_still_keep_ms 400.0 float); `source` không đổi
  (`calibrated: reports/level1_realtime_2026-10-03/tone_evidence.json@1ca53f3` — commit lấy bằng git); thứ tự khóa giữ; mọi khóa khác (kể cả 3
  khóa R1) bằng hệt từng byte; `git diff --stat` = 5 dòng reason. Bảng reason cũ → mới (in bằng code từ hai file):
  | Khóa | reason cũ (thiết kế, từ config trước A2b) | reason mới (quy tắc, `CALIBRATION_REASONS`) |
  |---|---|---|
  | `still_speed` | hand-lengths per second; a held letter only shows tracker jitter (a small fraction of the palm per frame); to be replaced by the train-clip calibration rule of plan 15 section 3.6 (B6b) | calibrated on the train clips of the deployed checkpoint: the ninetieth percentile, over the letter clips, of the per-clip median of the segmenter motion signal M_t |
  | `move_speed` | still_speed x move_over_still_ratio (plan 15 section 3.6) | calibrated: still_speed multiplied by move_over_still_ratio (design), so moving is a fixed multiple of the still threshold (hysteresis) |
  | `hold_ms` | = hold_ms_design until the calibration rule min(hold_ms_design, p10 of the longest still run per train clip) is applied (B6b) | calibrated on the train clips of the deployed checkpoint: the smaller of hold_ms_design and the tenth percentile, over the letter clips, of the longest still run of each clip |
  | `max_segment_ms` | a training clip is one whole sign of a few seconds; older frames are dropped from the buffer so a segment never spans much more than one sign | calibrated on the train clips of the deployed checkpoint: the ninety-fifth percentile, over all clips, of the clip duration, rounded up to a whole millisecond |
  | `tail_still_keep_ms` | = hold_ms until the calibration rule min(hold_ms, p50 of trailing_still_ms over moving train clips) is applied (plan 15 section 3.A.3) | calibrated on the train clips of the deployed checkpoint: the smaller of hold_ms and the median, over the clips with motion, of the still time after the last motion |
- Sau commit config: AC1-ngắn (19 module + test_level1_rearm) `Ran 304 — FAILED (failures=1, errors=5, skipped=43)`; so từng test với mốc
  b545ce7: khác duy nhất là test mới (16 RA ok, 5 W ok, S18b ERROR thiếu manifest); `test_r_prime_1d_write_config` XANH lại (đỏ tạm đã hết).
  Lỗi/skip còn lại giống mốc, đều do thiếu dữ liệu gitignored.
- detect-changes trước commit config (chạy khi chỉ config đổi, trước khi viết dòng này): "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (JSON config không có symbol mã). [Sửa ở commit R2: bản ghi trước ghi nhầm "Changes: 2 files".]

## R2 — hiệu chỉnh rearm_pose_dist (15-lan-sua-3 §3.4 P1/P2, §4 #5, §5 AC-RP1…RP4) — phiên cloud 2026-10-04: MÃ XONG, CHƯA CHẠY
- Mã (`scripts/level1_segment_report.py`, cùng script A1/A2b): `hand_shape` (N đúng như `push`: `normalize_hand_landmarks(aspect_points(raw).astype(float32)).astype(float64)`),
  `longest_still_run` (chỉ số của đúng đoạn mà `_longest_run` đo; đoạn đầu tiên khi bằng nhau), `clip_pose_profile` (M_t = `motion_series` của A1 →
  đoạn đứng yên dài nhất với `still_speed` của config → `ref` = trung bình N các khung có tay của đoạn, `jitter_clip` = p95 `pose_distance(N_t, ref)`),
  `pose_calibration` (P1: `rearm_pose_dist = pose_over_jitter_ratio × p95` qua clip chữ cái có khung đứng yên; clip không có → đếm + liệt kê, bỏ;
  P2: mỗi (người ký, phiên), mỗi cặp lớp chữ cái khác nhau, ref của clip sample_id nhỏ nhất; `coverage`; danh sách cặp dưới ngưỡng gộp theo cặp nhãn
  kèm số người ký; lớp có clip đầu không có đoạn đứng yên → `classes_without_ref`; luật dừng `coverage < 0.80`), `pose_report` (JSON: `generated_by`,
  `note` "train data of the deployed checkpoint; not accuracy", `definitions`, sha256 manifest + config, `calibration`), `write_pose_config`
  (chỉ ghi `rearm_pose_dist`: value + `source: calibrated: <evidence>@<commit>` lấy qua `committed_evidence_ref` của A2b + `POSE_REASON` không chữ số;
  evidence chưa commit/bẩn → RuntimeError trước khi mở config; P2 đã kích hoạt → RuntimeError, không ghi). CLI: `--pose-evidence --out <json>`
  (thoát mã 2 nếu P2 kích hoạt), `--write-pose-config <config> --pose-evidence-json <json>`. `pose_distance` của script LÀ hàm của bộ tách (`is`).
- Test viết TRƯỚC `tests/test_level1_pose_evidence.py` (11 test; clip tổng hợp có kiểm soát; giá trị mong đợi tính bằng công thức viết tay của
  `tests/test_level1_rearm.py`): ĐỎ trên mã trước R2: `Ran 11 — FAILED (errors=11)` (hàm chưa có; `_work/_cloud/r2_red.log`). Sửa 1 lỗi dựng dữ liệu
  trong chính test mới (chưa commit): cặp (a, b) của s2 đặt cách 0.05 không nằm dưới ngưỡng ≈ 2 × jitter ≈ 0.02 như chú thích nói → đổi thành 0.01.
  XANH: `Ran 11 — OK` (`_work/_cloud/r2_green.log`): RA9 phía script (`is`, `hand_shape` == N trong bộ tách, `longest_still_run` khớp `_longest_run`
  trên 200 dãy ngẫu nhiên), RP1 (hồ sơ clip, P1, P2, clip không đứng yên, không có clip chữ cái đứng yên → ValueError), RP2 (chưa commit / bẩn /
  P2 kích hoạt → RuntimeError + config giữ từng byte; thành công → chỉ `rearm_pose_dist` đổi, helper A2b được gọi đúng 1 lần), RP3 (khóa JSON).
  RP4: 5 test A2b (AC-W1…W3) + `test_r_prime_1d` vẫn xanh, không sửa.
- Level 1 (9 module, gồm test_level1_rearm + test_level1_pose_evidence): `Ran 139 — FAILED (failures=1, errors=5, skipped=19)` = đúng các lỗi/skip thiếu
  dữ liệu đã có từ R1 (không thêm). Guard chính `known=9 allowed=36` OK.
- **BỊ CHẶN (thiếu dữ liệu):** thử `python scripts/level1_segment_report.py --pose-evidence --out _work/_cloud/pose_try.json` →
  `FileNotFoundError …/checkpoints/alphabet_best.pt` (cần checkpoint cho `min_detected_frames` + manifest/npz). KHÔNG có `pose_evidence.json`, KHÔNG có
  số P1/P2, `rearm_pose_dist` trong config vẫn là giá trị giữ chỗ của R1, `pose_change_rules` vẫn false. Việc local (theo thứ tự, mỗi bước tại commit sạch):
  1. `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/level1_segment_report.py --pose-evidence --out reports/level1_realtime_<D>/pose_evidence.json`
     → kiểm `generated_by.code_dirty == false` → commit JSON (`15: R2 — pose_evidence.json`). Mã thoát 2 / `stop_rule.triggered` ⇒ P2 coverage < 0.80 ⇒ DỪNG, báo planner.
  2. `… --write-pose-config configs/level1_realtime.json --pose-evidence-json reports/level1_realtime_<D>/pose_evidence.json` → `git diff` chỉ khối
     `rearm_pose_dist` → chạy lại test Level 1 → commit (`15: R2 config`).

## R3 — kiểm gate G1–G6 trên chuỗi ghép (15-lan-sua-3 §3.5, §4 #6, §5 R3) — phiên cloud 2026-10-04: MÃ XONG, CHƯA CHẠY
- Mã (`scripts/level1_rearm_check.py`): `--set NAME:KEY=JSON` (ghi đè 1 khóa config, kiểm lại bằng `validate_level1_config`, ghi vào
  `configs.<name>.overrides`) — dùng để tạo config `on` = config R2 đã commit + `pose_change_rules=true` thay cho bản sao trong `_work/` của §4 #6
  (LỆCH nhỏ, có lợi cho nguồn gốc: `git_commit` của config vẫn ghi được); chuỗi L có thêm `one_rate_covered`/`n_clips_covered` (cặp (clip trước,
  clip này) có `pose_distance(ref_trước, ref) >= rearm_pose_dist` của chính config đó; `ref` = hình dạng tham chiếu của R2 (`clip_pose_profile`)
  tính trên clip CHƯA cắt — cùng đường dữ liệu với P2; cặp thiếu ref ⇒ không tính là covered); `label_agrees` (chỉ khi có checkpoint: clip có
  đúng 1 segment, nhãn model của segment == nhãn model của trọn clip chưa cắt; báo cáo, không gate); `--gates GATE:BASELINE` chạy G6
  (`single_clip_rates`: mọi clip hauuto có ≥ `min_detected_frames` khung có tay, chưa cắt, bộ tách mới mỗi clip, flush ts cuối + 1 ms như AC-S18;
  LỆCH nhỏ so với AC-S18: AC-S18 lấy mọi clip với min_frames = min_sign_frames, ở đây dùng bộ lọc + `min_detected_frames` của checkpoint như AC-R1)
  và đánh giá G1–G6 với ngưỡng ĐẶT TRƯỚC hằng trong script (`GATE_THRESHOLDS`: 0.90 / 0.05 / 0.05 / 0.02; thiếu join hoặc giá trị ⇒ gate trượt);
  JSON thêm `note_vi` "chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác", `single_clip`, `gates`; thoát mã 3 khi có gate trượt.
  `--write-rules-config CONFIG --rearm-json JSON`: đặt `pose_change_rules = true` (source design, reason ghi `<json>@<commit>`) CHỈ khi JSON đã
  commit và sạch (helper A2b `committed_evidence_ref`), `generated_by.code_dirty` false và `gates.all_pass` true; chỉ khóa đó đổi.
  `checkpoint_path=None` + `min_detected_frames` cho phép chạy không checkpoint (khi đó `label_agrees` None) — dùng cho test tổng hợp.
- Test viết TRƯỚC `tests/test_level1_rearm_gates.py` (13 test): ĐỎ trên mã trước R3: `Ran 12 — FAILED (errors=18 tính cả subTest)`
  (`_work/_cloud/r3_red.log`; test thứ 13 RA9 phía R3 thêm ngay sau, cũng đỏ vì chưa import). XANH: cùng `tests.test_level1_rearm_check` →
  `Ran 28 — OK` (`_work/_cloud/r3_green.log`): covered với khoảng cách None; override (parse, kiểm kiểu, khóa lạ); G1–G6 đạt / biên bao gồm
  (0.90, 0.05) / từng gate trượt riêng / config off và giá trị chỉ-báo-cáo không bị gate / thiếu join ⇒ trượt; G6 trên clip tổng hợp (A→B: tắt 1
  segment, bật 2); chạy đầu-cuối trên manifest + npz TỔNG HỢP (1 người ký, chuỗi L 5 clip) với config thật + `rearm_pose_dist` ghi đè cho hình dạng
  tổng hợp: bật ⇒ L/join 0 `one_rate` 1.0, tắt thấp hơn; `write_rules_config` (chưa commit / gate trượt / code bẩn ⇒ RuntimeError, config giữ từng
  byte; thành công ⇒ chỉ `pose_change_rules` đổi). Test RC1–RC4 + A2a cũ không sửa, vẫn xanh.
- Level 1 (10 module): `Ran 152 — FAILED (failures=1, errors=5, skipped=19)` = đúng các lỗi/skip thiếu dữ liệu đã có (không thêm). Guard chính
  `known=9 allowed=36` OK.
- **Ghi nhận cho planner (TỔNG HỢP, không phải số liệu, không dùng để chỉnh gì):** trên manifest tổng hợp của test, mối ghép 600 ms (15 khung nội
  suy chậm, tốc độ hình dạng < still_speed) cho phần lớn segment đa số khung "join" (rác theo luật gán): luật 3 chỉ khởi động lại đồng hồ hold khi
  lệch ≥ `rearm_pose_dist` so với `hold_ref`, nên hold có thể bắt đầu giữa mối ghép khi quãng còn lại < ngưỡng; segment bắt đầu từ `_pose_since`
  (giữa mối ghép). Đã trace từng khung: hành vi đúng chữ §3.2, không phải lỗi cài đặt. Hệ quả có thể: G5 (join 600) trượt trên dữ liệu thật — nếu
  vậy là điểm DỪNG của R3, báo planner, không nới gate.
- **BỊ CHẶN (thiếu dữ liệu):** thử chạy lệnh R3 → `FileNotFoundError …/checkpoints/alphabet_best.pt`. KHÔNG có `rearm_check_r3.json`, KHÔNG có số
  G1–G6, `pose_change_rules` vẫn false. Việc local (SAU khi xong R2 config; mỗi bước tại commit sạch):
  1. `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/level1_rearm_check.py --config off=configs/level1_realtime.json --config on=configs/level1_realtime.json --set on:pose_change_rules=true --gates on:off --join-ms 0,300,600 --out reports/level1_realtime_<D>/rearm_check_r3.json`
     → mã thoát 0 = G1–G6 đạt, 3 = có gate trượt ⇒ DỪNG, ghi số từ JSON, báo planner (không nới gate) → commit JSON (`15: R3 — rearm_check_r3.json`).
  2. Chỉ khi đạt: `… scripts/level1_rearm_check.py --write-rules-config configs/level1_realtime.json --rearm-json reports/level1_realtime_<D>/rearm_check_r3.json`
     → `git diff` chỉ khối `pose_change_rules` → chạy lại test Level 1 + AC-E1 → commit (`15: R3 config`) → báo người dùng U1c.

## Phiên cloud 2026-10-05 — chạy trên dữ liệu thật (nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc nhận `4ad3e8c`)
- Môi trường: Kaggle CLI 2.2.4 dùng `KAGGLE_API_TOKEN` (chạy được: `kaggle datasets list --mine` liệt kê 3 dataset private); cài `seaborn` vào `.venv`.
  GitNexus 1.6.12 qua `npx -y gitnexus@latest analyze` + `detect-changes --scope all --repo .`.
- Dữ liệu khôi phục (gitignored, KHÔNG commit): kernel output `phmvnsm33/vsl-extract-alphabet` → `data/external/alphabet_hands_kaggle/alphabet_hands/`
  (686 npz + manifest.csv + tasks.csv); `archive_private_kaggle.py restore` cả 2 manifest (provenance: 13 file, step4: 18 file) — sha256
  `checkpoints/alphabet_best.pt` = `a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2` (khớp); `hauuto/vietnamese-sign-language-alphabet`
  → `data/external/hauuto_raw/raw/raw/` (640 mp4); 46 video QIPEDC chữ cái (theo manifest) từ `aresusayhi/vsl-vietnamese-sign-languages` → `data/Dataset/Videos/`.
- Kiểm A2a + R1 trên dữ liệu tại `4ad3e8c`: 11 module (7 Level 1 + rearm, pose_evidence, rearm_gates, equivalence) → `Ran 161 — OK (skipped=7)`;
  AC-S18 + S18b (mọi clip hauuto) XANH; `tests.test_level1_equivalence` riêng → `Ran 9 — OK` (AC-E1 + E3, video trích trên Linux, so trên cùng máy).
  Skip còn lại: `test_u1_summary` (file U1 local `_work/_plan15_u1/…`); 6 skip E1 ở lượt đầu do chưa có video QIPEDC, hết skip sau khi tải.

### R0 sinh lại (A2a (b))
- Lệnh tại worktree sạch `b545ce7` (data symlink, không track):
  `python scripts/level1_rearm_check.py --config current=configs/level1_realtime.json --config before_a2=git:3ebc7b9:configs/level1_realtime.json --join-ms 0,300,600 --out reports/level1_realtime_2026-10-04/rearm_check_r0.json`
  → `generated_by.git_commit` b545ce7…, `code_dirty` false; `configs.before_a2.git_commit` = `3ebc7b9f0d65…` (hết chuỗi rỗng), `filled` = `tail_still_keep_ms`.
- So với JSON cũ (1acb4a5) bằng code: `current` KHÔNG đổi số nào. Chỉ `before_a2` L join 600 đổi: `one_rate` 0.4819 → 0.4870, `miss_rate` 0.4922 → 0.4870,
  `garbage_per_clip` 0.0104 → 0.0052 (một chuỗi: one 0.3214 → 0.3571, garbage 0.0357 → 0.0). Nguyên nhân (suy luận, chưa trace từng khung): lần cũ chạy
  ở a3970a6 với mã bộ tách TRƯỚC A2a (tail = hold vẫn cắt khung cuối), lần mới dùng luật A2a (tail ≥ hold ⇒ không lọc).
- Kết luận R0 không đổi: `current` L join 0/300 `one_rate` 0.3109 / 0.3731 < 0.90 ⇒ giả thuyết đứng. detect-changes: chỉ JSON, không symbol nào.

### R2 chạy trên dữ liệu — DỪNG theo luật P2
- Lệnh tại commit sạch `a66ea13`: `python scripts/level1_segment_report.py --pose-evidence --out reports/level1_realtime_2026-10-05/pose_evidence.json`
  → mã thoát 2; JSON `generated_by.code_dirty` false.
- P1 (đọc từ JSON): 516 clip chữ cái, 514 có đoạn đứng yên (thiếu: `hauuto_c_tai_B_001`, `hauuto_m_tai_B_001`); `jitter_clip` p50 0.0627, p90 0.2785,
  p95 0.3459 ⇒ `rearm_pose_dist` = 2.0 × 0.3459 = **0.6919**.
- P2: 3193 cặp, 1985 cặp có khoảng cách < ngưỡng ⇒ `coverage` **0.3783 < 0.80** ⇒ `stop_rule.triggered` true. Khoảng cách giữa hai chữ
  (`between`) p50 0.5802, p10 0.3107 — tức trung vị khoảng cách giữa hai chữ khác nhau còn nhỏ hơn ngưỡng. 300 cặp nhãn dưới ngưỡng, nhiều cặp
  dưới ngưỡng ở cả 8 phiên (vd. â–ê, ô–ơ, ă–ư, a–b).
- Theo prompt §2 bước 4: DỪNG. KHÔNG chạy `--write-pose-config` (script cũng từ chối khi P2 kích hoạt), `rearm_pose_dist` trong config giữ giá trị
  giữ chỗ 1.0, `pose_change_rules` vẫn false; KHÔNG chạy R3, không có số G1–G6. CẦN PLANNER.
- Quan sát cho planner (không phải đề xuất đổi gate): phân bố jitter lệch đuôi dài (p95 / p50 ≈ 5.5), nên ngưỡng 2 × p95 vượt trung vị khoảng
  cách giữa hai chữ; hình dạng tay `pose_distance` (N chuẩn hóa) có thể không đủ tách các chữ chỉ khác dấu phụ/hướng.

## Lần sửa 4 — coder (phiên cloud 2026-10-05, lượt 3; nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc nhận `5c62d13`)
- Môi trường: Kaggle CLI dùng `KAGGLE_API_TOKEN`; cài `seaborn` vào `.venv`. Dữ liệu khôi phục lại (gitignored, KHÔNG commit), cùng cách phiên
  trước: kernel `phmvnsm33/vsl-extract-alphabet` → 686 npz + manifest; `archive_private_kaggle.py restore` 2 manifest (provenance + step4,
  18 file ghi mới ở step4); sha256 `checkpoints/alphabet_best.pt` = `a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2` (khớp);
  640 mp4 hauuto; 46 video QIPEDC chữ cái (theo manifest, tải từng file `-f Dataset/Videos/<id>.mp4`).
- **GitNexus KHÔNG dùng được ở phiên này:** `npx -y gitnexus@latest analyze` bị chặn (tải mã ngoài bị từ chối). Thay bằng text search
  (`grep -rn <symbol>`) cho impact và `git diff --stat` cho detect-changes, ghi ở từng bước.
- Không có pytest trong `.venv` ⇒ lệnh chung §5 chạy bằng `python -m unittest` cùng danh sách module.

### K1 — phím `n` "chữ kế" (15-lan-sua-4 §3.1, AC-K1…K4)
- Mã: `Level1SignSegmenter.force_rearm(ts)` (armed = True, bộ đệm chỉ giữ khung ts ≥ lúc bấm, đồng hồ hold đang chạy đặt lại về ts, xóa
  neo/`_pose_since`/`hold_ref`; không có tay ⇒ không làm gì; ts không hữu hạn ⇒ ValueError; không phát sự kiện). `level1_demo.py`:
  `KEY_ACTIONS[ord("n")] = "next"` → `Level1App._next_key()` gọi `segmenter.force_rearm(last_ts)` và ghi `{"event": "key", "key": "next",
  "source": "key", "t_ms"}`; không tạo token; dòng hướng dẫn HUD + docstring thêm `n chữ kế`. Nhánh `rearm_mode == "classifier"`
  (`decoder.force_next`) thêm ở D2 khi có decoder (K3 mở rộng lúc đó).
- Impact (text search, thay GitNexus): `Level1App._key` chỉ được gọi trong `level1_demo.py` (`_process`, `run`) và test; `KEY_ACTIONS`
  chỉ trong `level1_demo.py`; `force_rearm` mới. detect-changes thay bằng `git diff --stat`: 4 file (level1_demo.py, level1_segmenter.py,
  2 test).
- Test viết TRƯỚC (`tests/test_level1_segmenter.py` K1/K2/K4, `tests/test_level1_demo.py` K3): ĐỎ trên mã `5c62d13`
  `Ran 9 — FAILED (failures=2, errors=5)` (`_work/_plan15/K1_red.log`; K4 xanh sẵn vì là khóa "không đổi").
  K4 so bộ tách HEAD với bộ tách `git show 5c62d13` (array_equal) trên các chuỗi AC-S1…S6, S16 (2 lưới) × 3 bộ tham số (gồm luật tư thế bật)
  + mọi clip hauuto × 2 config AC-S18.
- XANH: 10 module Level 1 (segmenter, rearm, rearm_check, rearm_gates, segment_report, pose_evidence, core, demo, guard, textbox)
  `Ran 161 — OK (skipped=1)` (`_work/_plan15/K1_green_l1.log`; skip = `test_u1_summary`, file U1 chỉ có ở local).
  AC1-ngắn còn lại + `test_level1_equivalence`: `Ran 176 — FAILED (failures=1)` = `test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs`
  (chập chờn đã biết); chạy riêng 3 lần: FAILED / OK / OK (`_work/_plan15/K1_reset_{1,2,3}.log`). Guard chính `known=9 allowed=36`.

### D1 — `WindowBuffer`, `Level1LabelDecoder`, `VARIANT_BASE`, khóa config, `Level1Speller.on_label` (15-lan-sua-4 §3.2–§3.3, AC-D1…D9)
- Mã (`src/inference/level1_segmenter.py`, thuần numpy): `VARIANT_BASE` (7 cặp ă, â→a; ê→e; ô, ơ→o; ư→u; đ→d), `LabelEmit`, `WindowBuffer`
  (khung của `cls_window_ms` gần nhất, `segment(t)` = bản sao các khung có ts ≥ t − cls_window_ms + 1e-6 — đúng dung sai của
  `window_probs` trong `15-lan-sua-4-do/analyze2.py` — gồm cả khung không tay trong cửa sổ, close_reason `"window"`; < `min_detected_frames`
  ⇒ None; đổi kích thước khung ⇒ cửa sổ bắt đầu lại), `Level1LabelDecoder` (luật 1–5 §3.2, đúng `decode_r` của `analyze5.py`).
  Chốt diễn giải (ghi rõ vì §3.2 luật 1 viết "None ⇒ chạy mới"): khung có tay mà `result` None (cửa sổ chưa đủ khung / việc bị worker bỏ)
  là "không có kết quả", KHÔNG cắt chuỗi chạy — giống `analyze5.py` (hàng NaN bị bỏ qua); kết quả có `status` ≠ ok hoặc conf < `cls_conf`
  là nhãn None ⇒ chạy mới.
- `src/inference/level1_core.py`: kind `"enum"` (`ENUMS["rearm_mode"] = REARM_MODES = ("motion_pose", "classifier")`), 4 khóa trong
  `CONFIG_SPEC` (`rearm_mode` enum, `cls_window_ms` > 0, `cls_conf` ∈ (0, 1], `cls_stable_ms` > 0); `Level1Speller.on_label(seq, emit)`
  (nhận như `on_result`: conf ≥ `accept_confidence`; `replace` chỉ thay khi token cuối đúng là chữ gốc, ngược lại thêm; nhật ký
  `action "replace"`, `source "model"`, `replaced`).
- `configs/level1_realtime.json`: thêm sau `pose_over_jitter_ratio` 4 khóa source `design`: `rearm_mode` "motion_pose", `cls_window_ms` 1000,
  `cls_conf` 0.9, `cls_stable_ms` 300; reason ghi "chosen after the planner's exploratory measure on concatenated train clips … not an
  independent calibration". Mọi khóa khác giữ từng byte (ghi bằng `json.dumps(indent=2)`, đã kiểm file gốc đúng định dạng đó).
- `scripts/level1_rearm_check.py`: `FILL_RULES`/`_fill_missing` điền 4 khóa cho config đọc từ commit cũ (`rearm_mode` = "motion_pose";
  `cls_*` = giá trị trên đĩa, không được đọc khi motion_pose) — cần ngay ở D1 vì `validate_level1_config` đòi khóa mới.
- **Ngoại lệ test cũ (§4, cùng kiểu R1):** `tests/test_level1_rearm_check.py` `test_git_spec_records_full_commit_sha_and_fill` — dict khóa
  điền mong đợi thêm 4 khóa D1 (`R1_KEYS + D1_KEYS`), như R1 đã thêm `R1_KEYS` vào đúng dòng này (4c8c210). Không assertion nào khác đổi.
  LỆCH cần reviewer xem (đây là dict mong đợi của một assertion, không phải config dựng tay). Không test cũ nào khác cần sửa (các test dựng
  config đều đọc config trên đĩa).
- Impact (text search, thay GitNexus): `CONFIG_SPEC`/`_check_value`/`validate_level1_config` dùng trong level1_core, level1_rearm_check
  (`apply_overrides`, `resolve_config_spec`), level1_segment_report (write_config) và test; `_fill_missing` chỉ trong level1_rearm_check;
  `Level1Speller` thêm phương thức mới, không đổi `on_result`. detect-changes thay bằng `git diff --stat`: 4 file mã/config + 1 test cũ +
  test mới `tests/test_level1_decoder.py`.
- Test viết TRƯỚC `tests/test_level1_decoder.py` (22 test): ĐỎ `ImportError: cannot import name 'VARIANT_BASE'` (`_work/_plan15/D1_red.log`).
  Sửa 1 lỗi dữ liệu trong chính test mới (chưa commit): chuỗi D2 "status invalid" 12 khung quá ngắn để chạy mới đủ 300 ms → 20 khung.
  Lần chạy đầu sau mã: guard Level 1 G2 bắt hằng số `WINDOW_EDGE_MS = 1e-6` (luật D-binding) → bỏ hằng, dùng `_horizon()`.
- XANH: 12 module (10 module K1 + decoder + equivalence) `Ran 192 — OK (skipped=1)` (`_work/_plan15/D1_green_l1.log`, skip = `test_u1_summary`);
  AC1-ngắn còn lại `Ran 167 — OK`, guard chính `known=9 allowed=36` (`_work/_plan15/D1_ac1.log`).

### D2 — nối bộ giải mã vào `level1_demo.py` (15-lan-sua-4 §3.4, AC-A1…A5)
- Mã: `rearm_mode == "classifier"`: mỗi khung (không tạm dừng) → `WindowBuffer.push`; khung có tay và cửa sổ đủ khung → phân loại cửa sổ
  (headless: đồng bộ, tất định; GUI/paced: `LatestWindowWorker` "chỉ giữ việc mới nhất" — việc chưa chạy bị thay thì bỏ, đếm
  `window_dropped`, khung đó nhận kết quả None). "Timeline" theo ts (khung / word gap / phím n / tạm dừng) chỉ được áp từ đầu khi đầu đã có kết
  quả ⇒ decoder nhận đúng thứ tự ts; `LabelEmit` → `Level1Speller.on_label`; nhật ký `{"event": "label"}`. Bộ tách vẫn chạy (HUD, hand_lost,
  WordGap); segment của nó KHÔNG phân loại, KHÔNG vào speller, đếm `segments_not_classified`. Phím n ở chế độ classifier: mục "next" trong
  timeline → `decoder.force_next(ts)` (không gọi `force_rearm`). Tạm dừng: reset bộ tách + cửa sổ + decoder (theo thứ tự timeline).
  JSON: `rearm_mode` (mọi chế độ), `labels` (mọi chế độ; rỗng ở motion_pose), chặng `window_classify` (CHỈ ở classifier — test AC-L cũ khóa
  `tuple(stages) == STAGES` ở motion_pose), `counts` thêm `window_jobs`, `window_results`, `window_dropped`, `label_emits`, `label_replace`,
  `segments_not_classified` (chỉ classifier). Thời gian cửa sổ không tính vào chặng `segmenter` (đo riêng). `emit_to_token` chưa đo cho nhãn
  (chỉ segment) — ghi để planner biết.
- Impact (text search): `Level1App._process`/`run`/`report`/`_on_events`/`_key` chỉ trong `level1_demo.py` + test; `ClassifyWorker` không đổi.
  detect-changes thay bằng `git diff --stat`: `level1_demo.py`, `tests/test_level1_demo.py`.
- Test viết trước (`tests/test_level1_demo.py`: A1 headless classifier ×2 lần CLI + trong tiến trình; A2 motion_pose == `level1_demo.py` của
  `git show 12bd961` (tokens/segments/text); A3 `LatestWindowWorker` 40 việc + app paced với classifier chậm định nghĩa trong test; K3 nhánh
  classifier). ĐỎ trên `level1_demo.py` của 12bd961 (mã D2 cất tạm bằng `git stash`): `Ran 6 — FAILED (errors=6)` (`_work/_plan15/D2_red.log`).
  LỆCH quy trình: mã D2 viết trước test trong phiên; đỏ ghi bằng cách cất mã rồi chạy test mới.
  A4 = `tests.test_level1_equivalence` (AC-E3) xanh trong lệnh dưới; A5 = guard Level 1 + guard chính xanh.
- XANH: 12 module `Ran 198 — OK (skipped=1)` (`_work/_plan15/D2_green_l1.log`); AC1-ngắn còn lại `OK`, `known=9 allowed=36` (`_work/_plan15/D2_ac1.log`).
- Kiểm tay (không phải số liệu): `a_hau_A_001.mp4` headless classifier → tokens `['a']`, 1 nhãn, 73 cửa sổ phân loại.

### D3 — `scripts/level1_rearm_check.py --decoder` (15-lan-sua-4 §4 #4, §5 D3, §5.1; AC-C1…C5)
- Mã: `decode_chain` (WindowBuffer + Level1LabelDecoder đúng như app headless classifier: 1 lần `classify` cho mỗi khung có tay đủ cửa sổ;
  `replace` dời phát cuối tới khung/nhãn mới như `decode_r` của analyze5; đếm `append` sau một quãng mất tay ≥ hand_lost_ms = "hand_lost"),
  `strict_chain_metrics` (rác CHẶT C2: phát ở khung join HOẶC nhãn ≠ nhãn trọn clip của clip chứa khung phát; one/miss/multi theo phát
  không rác; order_ok; khoảng cách Levenshtein với nhãn mong đợi đã gộp lặp liên tiếp), `_sum_strict`, `evaluate_decoder_gates` (G1–G6 §5.1,
  ngưỡng hằng `GATE_THRESHOLDS` cũ 0.90/0.05/0.05/0.02; G1 = one_rate đầy đủ; G3 = mọi chuỗi L/T/O; thiếu join ⇒ trượt; ghi `failed`,
  `only_g6_tone_failed`, `stop_point` theo §7 mục 1/2), `single_clip_rates_decoder` (G6: decoder mới mỗi clip chưa cắt; rate = đúng 1 phát,
  không kiểm nhãn như rate của bộ tách; `one_and_label_rate` chỉ báo cáo), `load_qipedc_clips` + `qipedc_report` (G7 chỉ báo cáo: tỉ lệ clip
  phát nhãn trọn clip / phát đúng ký hiệu, cho mọi config), `write_mode_config` (+ CLI `--write-mode-config CONFIG --rearm-json JSON`: chỉ
  đổi `rearm_mode` → "classifier" khi JSON `mode == "decoder"`, `gates.all_pass`, `code_dirty` false, config gate là classifier, JSON đã commit
  sạch qua `committed_evidence_ref`; ngược lại RuntimeError, config giữ từng byte). `run_rearm_check(decoder=True)`: config classifier →
  nhánh decoder (label_agrees None, kèm lý do); config motion_pose → như cũ + khối `strict` (cùng định nghĩa §5.1, phát = khung t_emit, chỉ
  báo cáo); JSON thêm `mode`, `rearm_modes`, `definitions`, `exploratory_params_note`, `decoder_params`, `qipedc_g7`. Thiếu checkpoint với
  `--decoder` ⇒ ValueError/FileNotFoundError có chữ "checkpoint"; CLI thoát mã 2 kèm thông báo. Tham số `classifier=` chỉ cho test.
- Impact (text search): `run_rearm_check`/`main` chỉ được gọi bởi CLI và test (`tests/test_level1_rearm_check.py`, `tests/test_level1_rearm_gates.py`,
  `docs/plans/15-lan-sua-4-do/*.py` chỉ dùng hàm ghép chuỗi); không đổi hành vi khi không có `--decoder`. detect-changes thay bằng
  `git diff --stat`: `scripts/level1_rearm_check.py`, `tests/test_level1_rearm_check.py`.
- Test viết (C1–C5 trong `tests/test_level1_rearm_check.py`, 11 test, chuỗi/manifest/classifier giả lập định nghĩa trong test). LỆCH quy trình
  như D2: mã viết trước test; đỏ ghi bằng cách cất mã (`git stash`): `Ran 25 — FAILED (errors=13)` (`_work/_plan15/D3_red.log`).
- XANH: 12 module `Ran 208 — OK (skipped=1)` (`_work/_plan15/D3_green_l1.log`); AC1-ngắn còn lại `OK`, `known=9 allowed=36` (`_work/_plan15/D3_ac1.log`).

### D4 — gate G1–G7 tại commit sạch (15-lan-sua-4 §5.1) — **DỪNG theo §7 mục 2 (chỉ G6 nhóm dấu thanh trượt) — CẦN NGƯỜI DÙNG**
- Lệnh tại `1ab5d7b` (`git status --porcelain -- scripts src configs level1_demo.py` rỗng):
  `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_rearm_check.py --decoder --config off=configs/level1_realtime.json --config on=configs/level1_realtime.json --set 'on:rearm_mode="classifier"' --gates on:off --join-ms 0,300,600 --out reports/level1_realtime_2026-10-05/rearm_check_d4.json`
  → mã thoát 3, `gates G1-G6: FAILED G6`, `stop: lần sửa 4 §7 item 2` (`_work/_plan15/D4_run.log`). JSON: `generated_by.git_commit` 1ab5d7b…,
  `code_dirty` false; commit JSON `a58df71`. Tên cờ chốt: `--decoder`, `--set on:rearm_mode="classifier"`, `--gates on:off`,
  `--write-mode-config CONFIG --rearm-json JSON` (KHÔNG chạy). Chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác.
- Số (đọc bằng code từ JSON; `on` = classifier 1000/0.9/300, `off` = config hiện hành motion_pose):
  | Gate | Giá trị | Ngưỡng | Kết quả |
  |---|---|---|---|
  | G1 L one_rate join 0 / 300 | 0.9793 / 0.9689 | ≥ 0.90 | ĐẠT |
  | G2 L multi_rate 0 / 300 / 600 | 0.0 / 0.0 / 0.0 | ≤ 0.05 | ĐẠT |
  | G3 phát cần mất tay, L/T/O × 3 join | 0 (cả 9) | = 0 | ĐẠT |
  | G4 L order_ok | true ×3 | true | ĐẠT |
  | G5 L garbage_per_clip 300 / 600 | 0.0363 / 0.0311 | ≤ 0.05 | ĐẠT |
  | G6 chữ cái (516 clip) on / off | 0.9593 / 0.8798 | on ≥ off − 0.02 | ĐẠT |
  | **G6 dấu thanh (120 clip) on / off** | **0.8000 / 0.8500** | on ≥ 0.83 | **TRƯỢT** |
- Báo cáo (không gate): L join 0/300/600 `on` one 0.9793/0.9689/0.9793, token_error_rate 0.0415/0.0570/0.0466, n_replace 6/10/10 (193 clip);
  `off` (khối strict cùng định nghĩa) one 0.2332/0.2591/0.2280, rác 0.1192/0.1554/0.1451. T (70 clip) `on` one 0.9714 ×3, rác 0.1143/0.1429/0.1429;
  `off` one 0.7143/0.7286/0.6857. O (25 cặp chữ lặp) one 0.64 cho cả on/off (chữ lặp liên tiếp không tách được nếu không rút tay / phím n — đúng
  Giới hạn §6). Clip đơn `on`: chữ cái 495 đúng-1 / 7 không phát / 14 ≥ 2; dấu 96 / 9 / 15. G7 QIPEDC (46 clip, 0 clip thiếu khung): tỉ lệ clip phát
  nhãn trọn clip `on` 0.5435 (25/46, 34 lần phát) vs `off` 0.7391 (34/46, 60 lần phát); phát đúng ký hiệu `on` 0.5435 vs `off` 0.5652 (trọn clip
  đúng ký hiệu 28/46).
- Theo §7 mục 2: DỪNG. `rearm_mode` giữ "motion_pose", KHÔNG chạy `--write-mode-config`, KHÔNG thử tham số khác, KHÔNG nới gate. Người dùng chọn
  (a) bật classifier cho buổi báo cáo, Giới hạn ghi "dấu thanh liên tiếp kém hơn chế độ cũ; dùng phím 1–5" (G6 dấu vẫn ghi là trượt), hoặc
  (b) giữ motion_pose + phím n. Khuyến nghị của planner (§7): (a).
- **Người dùng chọn (a) "Classifier"** trên thẻ quyết định (2026-10-05 04:30 UTC). Thử bật bằng cách đổi TẠM `rearm_mode` = "classifier" trong
  `configs/level1_realtime.json` (không commit, đã khôi phục từng byte) rồi chạy 12 module Level 1: `FAILED (failures=9, skipped=1)`
  (`_work/_plan15/A_flip_try.log`). Trong đó 5 test CŨ đỏ vì chúng chạy app với config mặc định và khóa hành vi motion_pose:
  `TestHeadlessD2.test_d2_exit_and_keys`, `test_d2_prediction_equals_classify_again` (classify n == số segment), `TestLatencyAcL.test_l1_headless_d2_json`,
  `test_l1_l2_paced_json`, `test_l1_window_mode_measures_every_stage` (`tuple(stages) == STAGES`, classify n == số segment); 4 test mới của lượt
  này (D8, C4, A2, K3 motion_pose) cũng giả định config mặc định là motion_pose. Ngoài ra `--write-mode-config` từ chối vì `gates.all_pass` false.
  ⇒ **Điểm dừng §7 mục 3 (test cũ đỏ) — CẦN PLANNER**: cách bật (a) mà không sửa test cũ (ví dụ test cũ ghim config motion_pose, hoặc chế độ
  chọn bằng cờ/config riêng cho demo) và cách ghi config khi G6 dấu trượt có chủ ý của người dùng. Config giữ "motion_pose".
  Tạm thời cho demo (không đổi repo): chạy app với bản sao config đặt `rearm_mode` = "classifier" qua `--config` (đường này đã kiểm ở AC-A1).

## Lần sửa 5 — coder (phiên cloud 2026-10-05, lượt 4; nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc nhận `3d1690a`)
- Môi trường: cùng container lượt 3 (`CLAUDE_CODE_REMOTE=true`, `KAGGLE_API_TOKEN` có, `seaborn` có trong `.venv`); dữ liệu Level 1 còn
  nguyên, kiểm lại: 686 npz `alphabet_hands`, 642 file hauuto (640 mp4), 46 video QIPEDC, sha256 checkpoint `a6311820…5b708a2` khớp.
- GitNexus vẫn không dùng được (tải mã ngoài bị chặn) ⇒ impact = text search, detect-changes = `git diff --stat`, như lượt 3.

### S1 — `--write-demo-config` (15-lan-sua-5 §3.1, AC-W1/W2)
- Mã (`scripts/level1_rearm_check.py`): hằng `DEMO_DECISION` (quyết định (a) 2026-10-05, nơi ghi, kế hoạch) + `write_demo_config(out, json)`:
  từ chối (RuntimeError, không ghi OUT, config gốc nguyên byte) khi `mode != "decoder"`, `code_dirty` khác false, `all_pass` true (⇒ dùng
  `--write-mode-config`), không đúng §7 mục 2 (`failed != ["G6"]`, `only_g6_tone_failed` khác true, G6 chữ cái không đạt hoặc G6 dấu không
  trượt, thiếu số G6), config gate không phải classifier, `overrides` khác đúng `{"rearm_mode": "classifier"}`, OUT là config gốc, JSON hoặc
  config gốc chưa commit/có thay đổi (`committed_evidence_ref`), sha256 config gốc ≠ `configs[gate].sha256` của JSON. Ghi OUT = config gốc,
  `_about` mới (nguồn, sha256, commit, JSON@commit, "do not edit by hand"), `_user_decision` (số G6 đọc từ JSON), `rearm_mode` = classifier
  (source "design", reason ghi rõ G6 dấu thanh TRƯỢT, "not a gate pass", phím 1–5); `validate_level1_config` trước khi ghi. CLI
  `--write-demo-config OUT --rearm-json JSON` in sha256 file ra.
- Impact (text search): `main` chỉ được gọi bởi CLI và `tests/test_level1_rearm_check.py` (`rc.main`); nhánh mới chỉ chạy khi có
  `--write-demo-config`, các nhánh cũ không đổi. Symbol mới: `DEMO_DECISION`, `write_demo_config`. detect-changes (`git diff --stat`):
  `scripts/level1_rearm_check.py | 92 +`, `tests/test_level1_rearm_check.py | 167 +` (0 dòng xóa).
- Test viết TRƯỚC: lớp `TestWriteDemoConfigW1W2` (7 test, 11 trường hợp con từ chối; JSON D4 tổng hợp với số G6 0.7123/0.8456 khác số thật).
  ĐỎ: `Ran 7 — FAILED (errors=17)` (`AttributeError: … no attribute 'write_demo_config'`, `_work/_plan15/S1_red.log`). XANH: `Ran 7 — OK`.
- Chạy thử (không commit, file vào `_work/`) trên JSON D4 thật: chấp nhận, base `configs/level1_realtime.json` sha256 `cc178955…eb54b`
  commit `12bd961` = config `on` của `rearm_check_d4.json@a58df71`.
- XANH: 12 module Level 1 `Ran 215 — OK (skipped=1)` (skip = `test_u1_summary`, thiếu file U1 của người dùng; `_work/_plan15/S1_green_l1.log`);
  AC1-ngắn phần còn lại 11 module `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/S1_ac1.log`); sha256 checkpoint không đổi.

### S2 — sinh `configs/level1_demo_classifier.json` (15-lan-sua-5 §4 #2, AC-W3…W5)
- Test viết TRƯỚC: `TestDemoConfigFileW3` (`tests/test_level1_rearm_check.py`: file được git theo dõi, qua `load_level1_config`, `rearm_mode`
  classifier, config mặc định vẫn motion_pose, mọi khóa khác bằng config mặc định, `_user_decision.evidence` = JSON đã commit có
  `failed == ["G6"]`, `only_g6_tone_failed`, `configs.on.sha256` == sha256 config mặc định, số G6 khớp JSON) và `TestDemoConfigW4`
  (`tests/test_level1_demo.py`: lệnh demo headless với `--config configs/level1_demo_classifier.json` trên clip D2, thoát 0, `rearm_mode`
  classifier, `config.path`/`sha256` đúng file demo, có chặng `window_classify`). ĐỎ: `Ran 2 — FAILED (failures=2)` (file chưa có;
  `_work/_plan15/S2_red.log`).
- Lệnh tại `6fed928` (`git status --porcelain -- scripts src configs level1_demo.py` rỗng):
  `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_rearm_check.py --write-demo-config configs/level1_demo_classifier.json --rearm-json reports/level1_realtime_2026-10-05/rearm_check_d4.json`
  → thoát 0 (`_work/_plan15/S2_run.log`). sha256 `configs/level1_demo_classifier.json` =
  `568f97d8b26a72a075067b2f7fdec7772409d8e3e0a3487c2b4824b206c397e2`; config mặc định giữ sha256 `cc178955…eb54b`, không đổi.
  Script không từ chối ⇒ không kích hoạt điểm dừng §7 mục 1.
- XANH: W3, W4 `Ran 2 — OK`; 12 module Level 1 `Ran 217 — OK (skipped=1)` (skip `test_u1_summary`; `_work/_plan15/S2_green_l1.log`).
- AC-W5: `git diff 281ece1 --numstat -- tests/` → `tests/test_level1_demo.py 38 +/0 -`, `tests/test_level1_rearm_check.py 221 +/0 -`
  (0 dòng test cũ đổi/xóa); `git diff 281ece1 -- configs/level1_realtime.json level1_demo.py src/` rỗng.
- Impact: không sửa symbol có sẵn (chỉ thêm lớp test + file config). detect-changes (`git diff --stat`): `configs/level1_demo_classifier.json`
  (mới, 166 dòng), 2 file test (chỉ thêm), `docs/plans/15-progress.md`.
- Giới hạn (cho C1): `generated_by.code_dirty` của app không phủ file demo (`CODE_PATHS` bị test L3 ghim); báo cáo app ghi `config.path` +
  `config.sha256` để đối chiếu.

## A3 — coder (phiên cloud 2026-10-05, lượt 5; nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc nhận `5e9bd42`) — **DỪNG theo §3.A.4 / §7 mục 2 (quy tắc giữ config KHÔNG đạt, AC-R1 trượt) — CẦN PLANNER**
- Môi trường: container MỚI. `.venv` → `/opt/vslt-venv` (+ `seaborn`), `KAGGLE_API_TOKEN` dùng được. Khôi phục lại theo prompt cloud §1:
  686 npz `alphabet_hands` (kernel `vsl-extract-alphabet`), 640 mp4 hauuto (+2 file khác), 46 video QIPEDC chữ cái (`-f Dataset/Videos/<id>.mp4`),
  `scripts/archive_private_kaggle.py restore` 13 file; sha256 `checkpoints/alphabet_best.pt` = `a6311820…5b708a2` (khớp). GitNexus không dùng
  (như các lượt trước) ⇒ impact = text search, detect-changes = `git diff --stat`.
- Mốc tại `5e9bd42`: 12 module Level 1 `Ran 217 — OK (skipped=1)` (`_work/_plan15/A3_base_l1.log`, skip = `test_u1_summary`).
- Mã (`scripts/level1_segment_report.py`, commit `b314d5a`): `segment_check_config` (PATH hoặc `git:REV:PATH` qua `resolve_config_spec` của
  `level1_rearm_check.py` — khóa thiếu được điền theo `FILL_RULES`, ghi trong `config.filled`; từ chối config khác `motion_pose` hoặc bật luật tư
  thế), `clip_segment_check` (bộ tách mới mỗi clip, push mọi khung, flush ts cuối + 1 ms như AC-S18/G6; nhãn segment và nhãn trọn clip bằng
  `Level1Classifier.classify`), `segment_check_groups` (chữ cái / dấu thanh / từng dấu), `segment_check_report`, `keep_rule` (quy tắc giữ §3.A.4
  + AC-R1, kiểm cùng tập clip), CLI `--segment-check --config … --label … [--manifest …] --out …` và `--keep-rule BEFORE AFTER` (mã thoát 5 = dừng).
  Tập clip = MỌI dòng hauuto của manifest (640, không loại clip nào; 4 clip dưới `min_detected_frames` được giữ và đánh dấu — bộ tách không
  phát được cho chúng).
- Impact (text search): `main` của script chỉ được gọi bởi CLI và test; `level1_rearm_check.py` import module này (`seg_report`), các hàm cũ
  không đổi (chỉ thêm). detect-changes (`git diff --stat`): `scripts/level1_segment_report.py | 194 +`, `tests/test_level1_segment_report.py | 193 +`
  (0 dòng xóa).
- Test viết TRƯỚC: lớp `TestSegmentCheckA3` (7 test: config TRƯỚC 3ebc7b9 điền tail = hold, config SAU b0620a9, từ chối config classifier, đếm
  segment khớp bộ tách + luật đồng thuận với classifier giả lập trong test, gộp nhóm, quy tắc giữ + AC-R1 + khác tập clip, CLI trên 3 clip).
  ĐỎ: `Ran 7 — FAILED (errors=7)` (`_work/_plan15/A3_red.log`). XANH: 12 module `Ran 224 — OK (skipped=1)` (`_work/_plan15/A3_green_l1.log`);
  AC1-ngắn phần còn lại 11 module `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/A3_ac1.log`).
- Lệnh tại `b314d5a` sạch (`git status --porcelain -- scripts src configs level1_demo.py` rỗng; JSON ghi `code_dirty` false):
  `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_segment_report.py --segment-check --config git:3ebc7b9:configs/level1_realtime.json --label before --out reports/level1_realtime_2026-10-05/segment_check_before.json`
  và tương tự `--config git:b0620a9:configs/level1_realtime.json --label after --out …/segment_check_after.json`.
  LỆCH kế hoạch (theo lời người dùng): SAU = config tại `b0620a9` (người dùng ghi rõ); lần sửa 2 §5 ghi "commit config của A2b" (`4b5d736`) —
  value/source 5 khóa bằng hệt nhau (AC-W3), chỉ `reason` khác ⇒ hành vi bộ tách giống hệt. Cả hai config đều thiếu khóa luật tư thế/`rearm_mode`
  ⇒ điền `pose_change_rules = false`, `rearm_mode = "motion_pose"` (ghi trong `config.filled`).
- Số (đọc bằng code từ JSON; 520 clip chữ cái, 120 clip dấu thanh; dữ liệu train của checkpoint — window agreement KHÔNG phải độ chính xác):
  | Nhóm | single_segment_rate TRƯỚC → SAU | window_agreement_rate TRƯỚC → SAU | Quy tắc |
  |---|---|---|---|
  | Dấu thanh | 0.6417 → 0.8500 | **0.6083 → 0.5583** | SAU ≥ TRƯỚC: single đạt, **agreement TRƯỢT** |
  | Chữ cái | 0.8096 → 0.8731 | **0.7558 → 0.6962** | SAU ≥ TRƯỚC − 0.02: single đạt, **agreement TRƯỢT** |
  AC-R1 (single với SAU ≥ 0.9): chữ cái 0.8731, dấu thanh 0.8500 ⇒ **TRƯỢT cả hai**.
  `--keep-rule` → `keep: false`, `ac_r1.pass: false`, `stop: true`, mã thoát 5 (`_work/_plan15/A3_keep_rule.log`).
  Ghi chú §5 lần sửa 2: vì tail = hold trong SAU, mọi khác biệt TRƯỚC/SAU đến từ still_speed/move_speed/max_segment_ms, không từ cắt đuôi.
  Đối chiếu: single SAU khớp G6 `off` của D4 (chữ cái 454 clip đúng-1 = 0.8798 × 516 clip D4; dấu 102/120 = 0.85) — 4 clip thêm ở đây là
  4 clip dưới `min_detected_frames`.
  Theo dấu (single / agreement, TRƯỚC → SAU): sắc 0.500/0.417 → 0.875/0.375; huyền 0.500/0.500 → 0.792/0.583; hỏi 0.875/0.833 → 0.917/0.833;
  ngã 0.458/0.417 → 0.792/0.167; nặng 0.875/0.875 → 0.875/0.833.
- Theo §3.A.4 + §7 mục 2 (lần sửa 1): DỪNG, báo planner. KHÔNG thử giá trị thứ ba, KHÔNG đổi dung sai, KHÔNG đổi config. `configs/level1_realtime.json`
  giữ nguyên (vẫn là config hiệu chỉnh A2 + A2b). C1 CHƯA làm (phụ thuộc A3 và kết luận này). Chế độ demo `configs/level1_demo_classifier.json`
  (re-arm bằng bộ giải mã nhãn) không thuộc phép kiểm này.

## C1 — coder (cùng phiên, sau quyết định của người dùng)
- **Người dùng chọn "Làm C1 luôn"** trên thẻ quyết định (2026-10-05 07:35 UTC) sau khi A3 trượt: giữ config hiện tại, ghi A3 trượt vào mục Giới
  hạn của `docs/level1_desktop.md` và SUMMARY. Không đổi config, không chạy giá trị khác.
- Mã (`scripts/level1_segment_report.py`, commit `28c0d7d`): `build_summary` + CLI `--summary --out reports/level1_realtime_<D>/SUMMARY.md`:
  bảng sinh bằng code từ `tone_evidence.json` (`--evidence-json`), `segment_check_{before,after}.json` (kèm kết quả `keep_rule`),
  `rearm_check_*.json` chế độ decoder (G1–G7), config demo (`_user_decision`) và `webcam_*.json` trong cùng thư mục; mỗi mục ghi đường dẫn @ commit
  của file + sha256; không ghi giờ hay commit HEAD ⇒ tất định. `docs/level1_desktop.md`: lệnh demo đặt đầu (`--config configs/level1_demo_classifier.json`),
  bảng phím (`1`–`5`, `n`, Backspace, Space, `r`, `a`, `c`, `p`, `q`), khung text, Giới hạn 1–13 (§6.3 gốc, §6.2 lần sửa 1, lần sửa 3/4/5, A3 trượt),
  nguồn số liệu; không có chuỗi khớp `\d+(\.\d+)?\s*(ms|%|fps)`.
- Impact (text search): chỉ thêm hàm + nhánh CLI; `main` chỉ gọi bởi CLI/test. detect-changes (`git diff --stat`): script `160 +`, test `68 +`, doc mới.
- Test viết TRƯỚC: lớp `TestSummaryC1` (3 test: bảng + tất định trên JSON tổng hợp + CLI, SUMMARY đã commit sinh lại bằng hệt byte, tài liệu).
  ĐỎ: `Ran 3 — FAILED (failures=1, errors=2)` (`_work/_plan15/C1_red.log`). Test "sinh lại bằng hệt" thêm ở commit SUMMARY (cần file đã commit).
- Lệnh tại `28c0d7d` sạch: `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_segment_report.py --summary --out reports/level1_realtime_2026-10-05/SUMMARY.md`
  chạy 2 lần → `cmp` bằng hệt.
- XANH (cuối): 12 module Level 1 `Ran 227 — OK (skipped=1)` (skip `test_u1_summary`; `_work/_plan15/C1_final_l1.log`); AC1-ngắn phần còn lại 11 module
  `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/C1_final_ac1.log`); sha256 checkpoint không đổi. `git diff 5e9bd42 --numstat -- tests/`
  → `tests/test_level1_segment_report.py 269 +/0 -` (0 dòng test cũ đổi); `configs/level1_realtime.json`, `backend/main.py`, `realtime_demo.py`,
  `src/data/alphabet_preprocessing.py` không đổi. AC1-đủ (31 module) KHÔNG chạy trên cloud (thiếu dữ liệu/checkpoint ngoài Level 1) — còn cho local.

## Lần sửa 6 — vòng 1 (coder cloud, W0–W3, `docs/plans/15-lan-sua-6.md` @ `92b256b`)
- Đầu phiên: `git pull` nhánh `cloud/2026-10-04-level1-rearm` (HEAD `92b256b`); `.venv` → `/opt/vslt-venv`; cài `seaborn` vào `.venv`;
  khôi phục `checkpoints/alphabet_best.pt` bằng `scripts/archive_private_kaggle.py restore` (sha256 `a6311820…5b708a2` khớp manifest),
  landmark `alphabet_hands` (output kernel `phmvnsm33/vsl-extract-alphabet`) và video hauuto (dataset `hauuto/vietnamese-sign-language-alphabet`)
  — chỉ dùng nội bộ, không commit. GitNexus: không dùng (npx bị chặn trên cloud như các phiên trước) ⇒ impact = text search + `git diff`.

### W0 — `.gitattributes` ép LF
- Thêm 4 luật `text eol=lf`: `configs/*.json`, `reports/**/*.json`, `reports/**/*.md`, `docs/**/*.md`. Không file nào phải chuẩn hóa lại:
  `git ls-files --eol` của 227 file tracked khớp đều `i/lf w/lf` (chỉ cột `attr/` đổi thành `text eol=lf`) ⇒ không đổi nội dung file nào.
- Impact: không sửa symbol mã nào (chỉ file thuộc tính git). detect-changes (`git diff --stat`): `.gitattributes` 5 +, test mới.
- Test viết TRƯỚC `tests/test_level1_gitattributes.py` (4 test): luật có mặt; `git check-attr text eol` = set/lf cho MỌI file tracked khớp 4 mẫu
  (gồm 5 file bị kiểm sha256: 2 config, `SUMMARY.md`, `segment_check_{before,after}.json`); `git ls-files --eol` không có `w/crlf`/`i/crlf`;
  mô phỏng Windows: checkout `HEAD` với `core.autocrlf=true` vào work tree + index TẠM (không đụng index/work tree của repo) ⇒ 5 file chỉ có LF,
  bằng hệt blob. ĐỎ trước khi sửa: `Ran 4 — FAILED (failures=4)` — mô phỏng tái hiện đúng E9 (`configs/level1_realtime.json` bị ghi CRLF)
  (`_work/_plan15/W0_red.log`); XANH: `Ran 4 — OK` (`_work/_plan15/W0_green.log`).

### W1 — cờ `--trace-windows` (mặc định TẮT)
- Mã (`level1_demo.py`): hằng `TRACE_KEYS`, `TRACE_MAX_ENTRIES = 20000`; `Level1App._window_entry` (kết quả cửa sổ + trạng thái bộ giải mã
  NGAY SAU khi bộ giải mã áp kết quả đó: `top1/conf/top2/conf2` lấy từ `candidates` bất kể `cls_conf`; `run_label`, `run_ms` = ts − đầu chuỗi;
  `last` = nhãn đã phát gần nhất sau cửa sổ này; `emitted` = `seq` của nhãn phát tại cửa sổ này hoặc `null`); `_trace_window` gọi trong
  `_drain_timeline` sau `decoder.push`, chỉ khi cờ bật. Bộ giải mã chỉ được ĐỌC (`_run_label`, `_run_since`, `last_label`), không sửa
  `src/inference/level1_segmenter.py`. Khi bật, JSON thêm khóa `window_trace = {max_entries, n_windows, truncated, fields, entries}`
  (`n_windows` đếm mọi cửa sổ; quá `max_entries` thì giữ các mục đầu, `truncated: true`). Không ghi landmark/khung hình.
  Lựa chọn của coder (plan không nói rõ): `window_trace` là dict chứa `entries` để `truncated` nằm cùng chỗ; `motion_pose` + cờ ⇒ `entries` rỗng.
- Impact (text search, không có GitNexus): symbol sửa `Level1App.__init__`, `Level1App._drain_timeline`, `Level1App.report`, `build_parser`;
  gọi từ `level1_demo.py` (nội bộ), `tests/test_level1_demo.py`, `tests/test_level1_equivalence.py` (`SpyApp`, `build_parser`) — chạy lại cả hai: 
  `Ran 51 — OK` (`_work/_plan15/W1_green_demo_eq.log`). detect-changes (`git diff --numstat`): `level1_demo.py` 37 + / 1 −, test 150 + / 0 −.
- Test viết TRƯỚC `TestTraceWindowsW1` (7 test, AC-6b/AC-6c): tắt cờ ⇒ tập khóa (2 tầng) + `tokens/text/labels/segments/counts` bằng hệt
  `level1_demo.py` tại `4f913a2` (nạp bằng `git show`) ở CẢ HAI chế độ; bật cờ (CLI, trong tiến trình, `--pace realtime`) ⇒ số mục ==
  `counts.window_results`, đủ 10 khóa đúng thứ tự, `emitted` khớp `labels` (`seq`, `ts_ms`, nhãn, `run_ms` = `ts_ms − run_since_ms`), token không
  đổi; giới hạn kích thước (vá `TRACE_MAX_ENTRIES = 5` ⇒ 5 mục đầu, `truncated`). ĐỎ: argparse từ chối `--trace-windows` (SystemExit 2 trong
  setUpClass, `_work/_plan15/W1_red.log`); XANH `Ran 7 — OK` (`_work/_plan15/W1_green.log`).
- Ví dụ (clip D2 `a_hau_A_001`, config demo): 73 cửa sổ, 73 mục, nhãn phát `a` tại mục có `run_ms` 339.
- Điểm dừng `frame_total` (§3): `_work/_plan15/W1_measure.sh` — 6 clip hauuto (2 chữ, 2 dấu, `a`, `o`) × tắt/bật × 3 lần, headless, config
  demo; `_work/_plan15/W1_measure_summary.py` đọc p50 `frame_total` từ JSON (và kiểm token/nhãn bật = tắt): trung vị p50 mọi lần chạy
  tắt 16.31 / bật 16.16 (tỉ lệ 0.9909), trung vị tỉ lệ theo clip 0.9953 ⇒ KHÔNG tăng > 5%, không dừng. Theo clip tỉ lệ 0.970–1.083
  (`o_vy_A_001` 1.083, `b_hau_A_001` 0.970): nhiễu đo một clip trên cloud cỡ ±8%, ghi để reviewer đo lại trên Windows.

### W2 — HUD chế độ `classifier`
- Mã (`level1_demo.py`): `Level1App.last_window` (mục cửa sổ mới nhất, tính bằng `_window_entry` ở MỌI cửa sổ, kể cả khi tắt trace — chỉ đọc
  bộ giải mã); `_decoder_line()` = `[classifier] cửa sổ: <top1> <conf> | giữ <run_ms>/<cls_stable_ms> | cuối: <last>` (`—` khi chưa có cửa sổ /
  chưa phát; `giữ 0` khi cửa sổ dưới `cls_conf`; khi tạm dừng thêm ` | tạm dừng (p)` — lựa chọn của coder để không mất báo tạm dừng mà
  dòng "Trạng thái" cũ có). `_hud_lines`: ở `classifier` dòng này thay dòng "Trạng thái" (cùng vị trí, cùng số dòng panel) và `hold_progress`
  trả 0 (không vẽ thanh tiến độ bộ tách); `motion_pose` đi đúng nhánh cũ. Nhãn chế độ: `[classifier]` là nhãn chế độ ở `classifier`; KHÔNG
  thêm nhãn cho `motion_pose` vì mọi chữ thêm vào đều đổi ảnh HUD, trái AC-6d (ảnh `motion_pose` bằng hệt) — số dòng panel không đổi nên
  không phải điểm dừng.
- Impact (text search): sửa `Level1App._hud_lines` (gọi từ `_process`; test `TestNextKeyK3.test_k3_hud_help_line_lists_n`), `_drain_timeline`,
  `_trace_window` (chỉ nội bộ). Chạy lại `tests.test_level1_demo`: `Ran 47 — OK` (`_work/_plan15/W2_green_demo.log`).
  detect-changes (`git diff --stat`): `level1_demo.py` 23 + / 6 −, test 135 + / 0 −.
- Test viết TRƯỚC `TestHudClassifierW2` (5 test, AC-6d): dòng giải mã sau một lần chạy thật (khớp mục trace cuối và nhãn phát cuối); dòng
  theo từng cửa sổ tổng hợp đẩy qua `_drain_timeline` (264 ms chưa phát → 330 ms phát `b` → `dấu hỏi` 0.60 dưới ngưỡng ⇒ `giữ 0`); không có
  thanh xanh (vá `segmenter.status` hold 0.7 ⇒ classifier 0.0, motion_pose vẫn 0.7), cùng số dòng panel với motion_pose; tạm dừng; ảnh HUD
  `motion_pose` (4 trạng thái: mới, sau chạy, tạm dừng, đang giữ) bằng hệt `Hud`/`_hud_lines` của `4f913a2`. ĐỎ: `Ran 5 — FAILED (failures=4)`
  (test ảnh motion_pose xanh từ đầu, đúng mong đợi; `_work/_plan15/W2_red.log`); XANH: W1+W2 `Ran 12 — OK` (`_work/_plan15/W2_green.log`).
- Chi phí: dòng giải mã đổi theo từng cửa sổ ⇒ panel PIL dựng lại mỗi khung. Đo vi mô `Hud.compose` 640×480 (không phải JSON của app):
  p50 0.04 ms khi chữ không đổi, 2.91 ms khi chữ đổi mỗi khung (`_work/_plan15/W2_hud_bench.py`). Ảnh kiểm mắt: `_work/_plan15/W2_hud_classifier.png`.

### W3 — `scripts/level1_trace_report.py`
- Script mới (chỉ đọc JSON của app: `rearm_mode`, `config.values`, `labels`, `window_trace`; không model, không video, không giờ ⇒ tất định):
  `--trace <json> [--expected "<ký hiệu1>,<ký hiệu2>,…"] [--hold-ms 2000] [--out-json <file>]`. In bảng theo từng đoạn chuyển ký hiệu
  (cũ, mới, kết thúc, số cửa sổ/ms theo lớp) và bảng tổng (số cửa sổ, ms, tỉ lệ thời gian M1–M4/stable), dòng "Nguyên nhân chính" theo
  quy tắc §5 (một mã > 50% thời gian chuyển). Định nghĩa ghi ở docstring đầu file, đặt TRƯỚC khi có trace U3 — đây là các lựa chọn của coder
  vì plan chỉ cho dấu hiệu (§2), cần reviewer/planner xác nhận:
  M0 = `rearm_mode` ≠ classifier (không phân tích cửa sổ); đoạn chuyển = các cửa sổ sau một lần phát `old` tới lần phát kế (hoặc tới reset
  `last = null` = rút tay/`n`/`p`, hoặc hết trace); `new` = mục kế sau `old` trong `--expected` (căn trái→phải), không có thì nhãn phát kết thúc
  đoạn; thời gian cửa sổ = tới mục kế, chặn ở `hand_lost_ms`; lớp (khớp đầu tiên): `hold` (ts < đầu chuỗi của `old` + `--hold-ms`, ngoài tỉ lệ —
  giao thức U3 giữ khoảng 2 s), M4 (`new` đã biết, {top1, top2} = {old, new}, conf < cls_conf), M1 (conf < cls_conf), M2 (top1 = old),
  `stable` (thuộc chuỗi mà lần phát kết thúc đoạn hoàn tất = chờ `cls_stable_ms` bình thường), M3 (chuỗi tự tin bị đứt trước `cls_stable_ms`).
  Giới hạn đã biết: ký hiệu cũ giữ lâu hơn `--hold-ms` bị tính là M2 (script in dòng lưu ý). Ví dụ: trace một clip train dấu nặng
  (`tone_j_khoi_A_001`, không có chuyển ký hiệu) cho M2 100% chỉ vì clip dài hơn 2 s sau đầu chuỗi.
- `docs/level1_desktop.md` thêm mục 6 (dòng HUD, `--trace-windows`, lệnh U3, lệnh đọc trace; không có số đo — `TestSummaryC1` vẫn OK).
- Impact: chỉ thêm file mới (script, test) và một mục tài liệu; không sửa symbol có sẵn. detect-changes (`git diff --numstat`): script 250 +, test 211 +, `docs/level1_desktop.md` 15 +.
- Test viết TRƯỚC `tests/test_level1_trace_report.py` (9 test, AC-6e): trace tổng hợp dựng như app (kết quả cửa sổ tổng hợp → `Level1LabelDecoder`
  thật → `Level1App._window_entry` của app) cho từng M1/M2/M3/M4 ⇒ đúng mã chính và đúng số cửa sổ từng lớp; M4 không cần `--expected`
  (lấy nhãn phát), cặp khác ⇒ không M4; M0; reset (rút tay) + onset; căn `--expected` khi phát lại sau reset; `--hold-ms`; chặn thời gian;
  cờ `truncated`, thiếu `window_trace` ⇒ mã thoát 2; CLI chạy 2 lần ra cùng byte (stdout và `--out-json`). ĐỎ: `ImportError` (script chưa có,
  `_work/_plan15/W3_red.log`); XANH: `Ran 9 — OK` (`_work/_plan15/W3_green.log`).

### Kết thúc vòng 1 (lần sửa 6) — hồi quy AC-6a/AC-6f
- Commit: `c3be3b1` W0, `c6df559` W1, `b027ac8` W2, `e848d57` W3 (+ commit tiến độ này).
- AC-6a: `git diff 4f913a2..HEAD --numstat -- tests/` → `test_level1_demo.py 285/0`, `test_level1_gitattributes.py 105/0`,
  `test_level1_trace_report.py 211/0` (cột xóa = 0); `git diff 4f913a2..HEAD -- configs src` rỗng; `backend/main.py`, `realtime_demo.py`,
  `README.md`, `src/data/alphabet_preprocessing.py` không đổi. File đổi đều trong §6 (+ `docs/plans/15-lan-sua-6.md` của planner).
- Nền trước khi sửa (tại `c3be3b1`): 12 module Level 1 + gitattributes `Ran 231 — OK (skipped=1)` (`_work/_plan15/rev6_baseline_l1.log`).
- AC-6f (cuối, cùng code với HEAD): 12 module Level 1 (gồm AC-E1 `tests.test_level1_equivalence`) `Ran 239 — OK (skipped=1)`, skip duy nhất
  `test_u1_summary` (thiếu file U1, `_work/_plan15/rev6_final_l1.log`); 2 module mới `tests.test_level1_gitattributes tests.test_level1_trace_report`
  `Ran 13 — OK` (`_work/_plan15/rev6_final_new.log`); guard `known=9 allowed=36`, `Ran 28 — OK` (`_work/_plan15/rev6_guard.log`); AC1-ngắn phần
  còn lại 11 module `Ran 167 — OK`, 0 skip (`_work/_plan15/rev6_ac1.log`); sha256 checkpoint `a6311820…5b708a2` không đổi.
  AC1-đủ (31 module) không chạy trên cloud (thiếu dữ liệu/checkpoint ngoài Level 1) — còn cho reviewer.
- Không có điểm dừng nào của §3 xảy ra. Việc tiếp theo: người dùng chạy U3 (§4) với `--trace-windows`, reviewer đọc 2 JSON bằng
  `scripts/level1_trace_report.py` và tự tính lại, rồi chọn hướng vòng 2 theo §5. Cần reviewer/planner xác nhận các định nghĩa M1–M4 của W3
  (đặc biệt `hold` theo `--hold-ms` và M4 = xác suất chia giữa cặp cũ/mới khi dưới `cls_conf`).

## Lần sửa 7 — coder (phiên cloud 2026-10-05, `docs/plans/15-lan-sua-7.md` @ `5e08fbd`) — **mã T1–T4 XONG; giá trị config demo CHƯA ghi — CẦN PLANNER**
- Đầu phiên (container mới): `git checkout -B cloud/2026-10-04-level1-rearm origin/…` (HEAD `5e08fbd`); `.venv` → `/opt/vslt-venv`, cài
  `seaborn`; khôi phục `scripts/archive_private_kaggle.py restore` (13 file, sha256 `checkpoints/alphabet_best.pt` = `a6311820…5b708a2` khớp),
  686 npz `alphabet_hands` (output kernel `phmvnsm33/vsl-extract-alphabet`), 640 mp4 hauuto (+2 file khác), 46 video QIPEDC chữ cái
  (`-f Dataset/Videos/<id>.mp4`, id lấy từ manifest) — chỉ dùng nội bộ, không commit. GitNexus không dùng (như các phiên trước) ⇒
  impact = text search, detect-changes = `git diff --numstat`.
- Mốc tại `5e08fbd`: 12 module Level 1 `Ran 239 — OK (skipped=7)` (6 skip AC-E1 vì chưa có video QIPEDC lúc chạy + `test_u1_summary`;
  `_work/_plan15/rev7_baseline_l1.log`); sau khi khôi phục QIPEDC: `tests.test_level1_equivalence` `Ran 9 — OK`, AC1-ngắn 11 module
  `Ran 167 — OK`, 0 skip (`_work/_plan15/rev7_baseline_eq.log`, `rev7_baseline_ac1.log`); 2 module mới `Ran 13 — OK`; guard `known=9 allowed=36`.

### Điểm dừng — giá trị §2 không ghi được vào `configs/level1_demo_classifier.json`
- Plan T1/T2/T3 yêu cầu ghi vào file demo `cls_conf_tone`, `cls_stable_ms_tone` (khóa mới), `cls_window_ms` và `word_gap_ms` (đổi giá trị).
  Test CŨ `TestDemoConfigFileW3.test_w3_demo_config_is_the_measured_d4_config` (lần sửa 5 S2, `tests/test_level1_rearm_check.py`) ghim file
  demo = config mặc định + `rearm_mode` (cùng danh sách khóa, cùng `{value, source, reason}` từng khóa); `_about` của file ghi "generated by
  scripts/level1_rearm_check.py --write-demo-config … do not edit by hand". Thử (không commit, file khôi phục nguyên byte):
  ghi đủ 4 giá trị ⇒ `Ran 5 — FAILED (failures=2)`: W3 (danh sách khóa khác) và `TestSummaryC1.test_c1_committed_summary_regenerates_byte_identical`
  (SUMMARY ghi commit + sha256 của file demo) (`_work/_plan15/rev7_config_conflict.log`); chỉ đổi `cls_window_ms` ⇒ W3 vẫn đỏ ở khóa
  `cls_window_ms` (`rev7_config_conflict_window_only.log`). Sửa test cũ bị cấm (§1 plan, AC-7a, prompt cloud §3) ⇒ KHÔNG ghi giá trị, KHÔNG
  sinh lại SUMMARY; mã đọc các khóa này đã xong để planner chọn cách ghi (ví dụ: file config demo mới sinh bằng script, hoặc ngoại lệ test).
- Hệ quả: lệnh demo hiện tại chạy giá trị cũ; `--cls-window-ms` và `--no-auto-space` dùng được ngay; ngưỡng dấu thanh và debounce chỉ bật
  được bằng một bản config chép ra `_work/` (ghi ở `docs/level1_desktop.md` mục 7).

### T1 — ngưỡng riêng cho 5 dấu thanh (`42a01a6`)
- Mã: `Level1LabelDecoder` nhận khóa tùy chọn `cls_conf_tone`, `cls_stable_ms_tone` (`DECODER_TONE_KEYS`; thiếu ⇒ giá trị của
  `cls_conf`/`cls_stable_ms`), `thresholds(label)` / `is_tone(label)` (5 lớp `TONE_MARKS` của `fingerspelling_compose`); quy tắc 1–2 dùng ngưỡng
  theo nhãn dự đoán; `self.p` giữ đúng 4 khóa cũ. `level1_core.OPTIONAL_CONFIG_SPEC` (khóa tùy chọn, kiểm như `CONFIG_SPEC` khi có, trả sau
  các khóa bắt buộc; `CONFIG_SPEC` không đổi ⇒ config mặc định nạp như cũ), `_entry_value` tách từ `validate_level1_config` (cùng kiểm tra).
- Impact (text search): `Level1LabelDecoder` gọi bởi `level1_demo.py` (`Level1App`) và `scripts/level1_rearm_check.py` (`--decoder`);
  `validate_level1_config`/`load_level1_config` gọi bởi `level1_demo.py`, `scripts/level1_rearm_check.py` (gồm `apply_overrides`,
  `write_demo_config`), `scripts/level1_segment_report.py` — không file nào có khóa mới ⇒ hành vi không đổi.
  detect-changes: `level1_core.py 28+/14−`, `level1_segmenter.py 26+/2−`, test `test_level1_decoder.py 152+/0−`, `test_level1_core.py 71+/0−`.
- Test viết TRƯỚC: `TestToneThresholdsT1` (9 test: AC-7b dấu 0.80 phát sau đúng 200 ms ở cả 5 dấu, chữ 0.80 bị từ chối, chữ 0.92 phát sau
  300 ms, dấu dưới ngưỡng / quá ngắn, chuỗi trộn, một khóa không có khóa kia, kiểm tham số; AC-7d: không khóa mới ⇒ phát nhãn + trạng thái
  `_run_label/_run_since/last` bằng hệt bộ giải mã `5e08fbd` (nạp bằng `git show`) trên 30 luồng ngẫu nhiên có phím `n`; khóa có giá trị
  = giá trị chữ ⇒ bằng hệt; luồng không có dấu ⇒ bằng hệt) + `TestOptionalToneKeysT1` (4 test config). ĐỎ: `Ran 13 — FAILED (failures=15,
  errors=4)` (`_work/_plan15/T1_red.log`; 2 test AC-7d xanh từ đầu, đúng mong đợi). XANH: 12 module L1 `Ran 252 — OK (skipped=1)`,
  2 module mới `Ran 13 — OK`, AC1-ngắn `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/T1_full_*.log`).

### T2 — debounce dropout 1 khung + `--cls-window-ms` (`b2cddde`)
- Mã (quy tắc 6 trong docstring bộ giải mã): khóa tùy chọn `dropout_tolerance_ms` (thiếu ⇒ tắt, `dropout_tolerance_ms = 0.0`). Một khung
  tay có kết quả mà nhãn = None (dưới ngưỡng / status khác ok) khi đang có chuỗi ⇒ chưa cắt chuỗi; khung tay có kết quả KẾ TIẾP quyết định:
  cùng nhãn chuỗi và cách khung rớt ≤ `dropout_tolerance_ms` ⇒ chuỗi giữ nguyên điểm bắt đầu; ngược lại chuỗi bắt đầu lại tại khung rớt
  đúng như cũ. Khung không tay (chưa tới `hand_lost_ms`) và khung tay không kết quả ở giữa không quyết định; mất tay / `reset()` xóa khung
  chờ; không phát nhãn tại khung rớt. Lựa chọn của coder (plan chỉ ghi "1 khung hình (60ms)"): dung sai đo từ khung rớt tới khung quay lại,
  và tên khóa lấy đúng chữ của plan. `level1_demo.py`: `--cls-window-ms N` (`positive_ms`: số hữu hạn > 0) thay `cls_window_ms` cho lần chạy
  (cửa sổ + bộ giải mã), chỉ với config `classifier` (khác ⇒ `SourceError`, mã thoát 2), JSON thêm `config.overrides` CHỈ khi có cờ.
- Impact (text search): `Level1LabelDecoder.__init__/reset/push` (gọi như T1), `Level1App.__init__`, `Level1App.report`, `build_parser`
  (gọi bởi `main`, `tests/test_level1_demo.py`, `tests/test_level1_equivalence.py`) — chạy lại cả hai trong 12 module.
  detect-changes: `level1_demo.py 27+/0−`, `level1_segmenter.py 19+/0−`, `level1_core.py 2+/1−`, test `143+ / 23+ / 92+`, 0 dòng xóa.
- Test viết TRƯỚC: `TestDropoutDebounceT2` (12 test: một khung thấp / status lỗi giữ chuỗi, dấu thanh dưới ngưỡng riêng một khung, hai khung
  ⇒ như cũ, dung sai đúng 60 giữ / 61 cắt, nhãn khác ⇒ như cũ, khung trung tính, mất tay, reset, không phát tại khung rớt; so với bộ tham chiếu
  viết riêng trong test — khung rớt được dung thứ đổi thành "không kết quả" rồi giải mã bằng bộ giải mã cũ — trên 50 luồng ngẫu nhiên,
  hai bộ tham số), `TestOptionalDropoutKeyT2` (2), `TestClsWindowArgT2` (1), `TestClsWindowFlagT2` (3: cờ = config có `cls_window_ms` đó,
  `config.overrides`, `config.values` là file nguyên vẹn, cần chế độ classifier). ĐỎ: argparse từ chối `--cls-window-ms` (SystemExit 2 trong
  setUpClass) + `Ran 15 — FAILED (failures=15, errors=1)` (`_work/_plan15/T2_red.log`). XANH: 12 module L1 `Ran 270 — OK (skipped=1)`,
  2 module mới `Ran 13 — OK`, AC1-ngắn `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/T2_full_*.log`).

### T3 — `--no-auto-space` (`83463f7`)
- Mã (`level1_demo.py`): `Level1App.auto_space`; với cờ, `WordGap` vẫn đếm (`counts.word_gaps`) và ghi sự kiện `word_gap` có
  `auto_space: false` nhưng không gọi `speller.word_gap` (cả `motion_pose` lẫn `classifier`); gốc JSON thêm `auto_space: false` CHỈ khi có cờ;
  phím Space không đổi.
- Impact (text search): `Level1App.__init__`, `_on_events` (gọi từ `_process`, `run`), `report`, `build_parser`. detect-changes:
  `level1_demo.py 11+/0−` (gồm 2 dòng docstring cách chạy với hai cờ mới), test `113+/0−`.
- Test viết TRƯỚC (AC-7c): `TestNoAutoSpaceArgT3` (1) + `TestNoAutoSpaceT3` (5): clip D2 qua MediaPipe thật, từ khung 41 báo không có tay
  (`_HandAwaySession`, tay rời khung lâu hơn `word_gap_ms`) ở cả hai chế độ: không cờ ⇒ `tokens` `['a', ' ']`; có cờ ⇒ `['a']`, cùng
  `word_gaps`, `labels`, `segments`, không sự kiện token " "; phím Space vẫn thêm " "; `WordGap` đẩy thẳng vào app. ĐỎ: argparse từ chối
  `--no-auto-space` (SystemExit 2 trong setUpClass) + `Ran 1 — FAILED (failures=1)` (`_work/_plan15/T3_red.log`). XANH: 12 module L1
  `Ran 276 — OK (skipped=1)`, 2 module mới `Ran 13 — OK`, AC1-ngắn `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/T3_full_*.log`).

### T4 — HUD `(tone)` + tài liệu (`2b7ae5a`)
- Mã (`Level1App._decoder_line`): khi chuỗi đang giữ (`run_label` của mục cửa sổ mới nhất) là dấu thanh ⇒
  `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<thời gian ổn định của dấu> (tone) | cuối: <last>`; chuỗi chữ cái hoặc không có chuỗi ⇒
  dòng của lần sửa 6 (regex `HUD_DECODER_RE` cũ vẫn khớp). Lựa chọn của coder: `(tone)` hiện cả khi config không có khóa dấu (thời gian =
  `cls_stable_ms`). `docs/level1_desktop.md`: dòng Space (bảng phím) + mục 7 (2 cờ, 3 khóa tùy chọn, HUD, ghi rõ giá trị lần sửa 7 CHƯA vào
  file demo và lý do, cách thử bằng bản chép trong `_work/`, giới hạn của `level1_trace_report.py` với ngưỡng dấu riêng); không số đo.
- Impact (text search): `_decoder_line` chỉ gọi từ `_hud_lines` (test W2/T4). detect-changes: `level1_demo.py 6+/3−`, `docs/level1_desktop.md 26+/1−`,
  test `81+/0−`.
- Test viết TRƯỚC: `TestHudToneT4` (4: dòng `(tone)` với config có khóa dấu — phát ở 231 ms, chuyển sang chữ thì về dòng cũ; dấu dưới ngưỡng ⇒
  dòng cũ; config demo không khóa dấu ⇒ `/300 (tone)`; tạm dừng) + `TestDesktopDocT4` (1). ĐỎ: `Ran 5 — FAILED (failures=4)`
  (`_work/_plan15/T4_red.log`; test "dưới ngưỡng" xanh từ đầu, đúng mong đợi).

### Kết thúc lần sửa 7 — AC-7a…AC-7e
- Commit: `42a01a6` T1, `b2cddde` T2, `83463f7` T3, `2b7ae5a` T4 (+ commit tiến độ này).
- AC-7a: `git diff 4f913a2..HEAD --numstat -- tests/` → `test_level1_core.py 94/0`, `test_level1_decoder.py 295/0`,
  `test_level1_demo.py 571/0`, `test_level1_gitattributes.py 105/0`, `test_level1_trace_report.py 211/0` (cột xóa = 0).
  `git diff 5e08fbd..HEAD` chỉ gồm file trong §3 của plan; `configs/` (cả `level1_realtime.json` lẫn `level1_demo_classifier.json`),
  `backend/main.py`, `realtime_demo.py`, `src/data/alphabet_preprocessing.py`, `README.md` không đổi; sha256 checkpoint `a6311820…5b708a2`
  không đổi; không train.
- AC-7b: đạt ở mức bộ giải mã với tham số test `cls_conf_tone 0.78`, `cls_stable_ms_tone 200` (`TestToneThresholdsT1`); CHƯA đạt ở app
  với config demo vì giá trị chưa ghi được (điểm dừng ở trên). AC-7c: đạt (`TestNoAutoSpaceT3`). AC-7d: đạt (`test_7d_*`, cả T2:
  không `dropout_tolerance_ms` ⇒ bằng hệt `5e08fbd`).
- AC-7e (cuối, cùng code với HEAD): 12 module Level 1 `Ran 281 — OK (skipped=1)`, skip duy nhất `test_u1_summary` (thiếu file U1 của người
  dùng; `_work/_plan15/rev7_final_l1.log`); 2 module mới `Ran 13 — OK`; guard `known=9 allowed=36`, `Ran 28 — OK`; AC1-ngắn phần còn lại
  11 module `Ran 167 — OK`, 0 skip (`_work/_plan15/rev7_final_*.log`). AC1-đủ (31 module) không chạy trên cloud — còn cho reviewer.
- CHƯA làm (cần planner): ghi `cls_conf_tone`, `cls_stable_ms_tone`, `cls_window_ms`, `word_gap_ms` (và nếu muốn `dropout_tolerance_ms` —
  plan không ghi khóa này vào config) cho lệnh demo. Hướng coder thấy khả thi, để planner chọn: (1) file config demo MỚI sinh bằng script từ
  file demo hiện tại + các giá trị lần sửa 7 (ghi nguồn), đổi lệnh ở `docs/level1_desktop.md` — file cũ và test cũ giữ nguyên; (2) cho phép
  ngoại lệ sửa test W3 + sinh lại SUMMARY — trái quy tắc hiện hành; (3) chỉ dùng cờ dòng lệnh (thêm cờ cho ngưỡng dấu / debounce).
  Kỳ vọng "độ trễ đổi tay dưới 1 s" của §2 T2 chưa đo — cần phiên webcam (reviewer checklist §5 mục 3).

### Lần sửa 7 — quyết định của người dùng "File config mới" (2026-10-05) — **XONG**
- Quyết định (thẻ quyết định trong thread, người dùng chọn "File config mới"): sinh một file config demo MỚI bằng script, từ file demo hiện
  tại + giá trị lần sửa 7; `configs/level1_demo_classifier.json` và test cũ (AC-W3, SUMMARY) giữ nguyên; lệnh demo đổi sang file mới.
- `1b6eb94` — `scripts/level1_rearm_check.py --write-rev7-config OUT [--base]`: `write_rev7_config` đọc file demo lần sửa 5 (phải được git
  theo dõi, không có thay đổi chưa commit, `rearm_mode` = `classifier`; OUT ≠ file gốc — sai ⇒ RuntimeError, không ghi gì), thay
  `cls_window_ms`, `word_gap_ms` tại chỗ, chèn `cls_conf_tone`, `cls_stable_ms_tone`, `dropout_tolerance_ms` sau `cls_stable_ms`, thêm
  `_about` (sha256 + commit của file gốc, "do not edit by hand") và `_rev7_decision`; giá trị + lý do nằm trong `REV7_VALUES`, mỗi lý do ghi
  "lần sửa 7"; không đồng hồ ⇒ cùng gốc cùng byte, LF. Impact (text search, GitNexus không có trên cloud): hàm mới, gọi từ nhánh CLI mới
  của `main` và test; `scripts/level1_*.py` không nằm trong closure của `level1_demo.py` (guard G2). detect-changes:
  `scripts/level1_rearm_check.py 86+/0−`, `tests/test_level1_rearm_check.py 84+/0−`. Test viết TRƯỚC `TestWriteRev7Config` (4). ĐỎ:
  `Ran 4 — FAILED (errors=6)` (thiếu `write_rev7_config` / `REV7_VALUES`; `_work/_plan15/R7a_red.log`); XANH `Ran 4 — OK`, cả module
  `Ran 37 — OK` (`R7a_green.log`, `R7a_rearm_module.log`).
- Lựa chọn của coder (báo người dùng trong thread): file mới có `dropout_tolerance_ms` = 60 (§2 T2 của plan nói debounce 1 khung ~60 ms
  nhưng không ghi khóa nào vào config; khóa thiếu ⇒ debounce tắt) để debounce chạy trong lệnh demo.
- `acd8bed` — sinh file tại `1b6eb94` (`git status --porcelain -- scripts src configs level1_demo.py` rỗng):
  `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_rearm_check.py --write-rev7-config configs/level1_demo_classifier_rev7.json`
  → in `cls_window_ms 1000 -> 700.0, cls_conf_tone - -> 0.78, cls_stable_ms_tone - -> 200.0, dropout_tolerance_ms - -> 60.0,
  word_gap_ms 1000 -> 2500.0; base configs/level1_demo_classifier.json (sha256 568f97d8…c397e2, commit 2baa7aa) unchanged`
  (`_work/_plan15/R7b_write.log`); sha256 file mới `a2aea62e…ce4a7d`. `docs/level1_desktop.md`: lệnh mục 1 dùng
  `--config configs/level1_demo_classifier_rev7.json` (vẫn nêu file lần sửa 5), mục 7 thay đoạn "CHƯA được ghi" bằng mô tả file mới và
  lệnh sinh; không số đo. Impact (text search): `configs/` không bị quét theo glob ở test nào ngoài `test_level1_gitattributes` (LF —
  file mới LF); file chỉ được đọc qua `--config`. detect-changes: `configs/level1_demo_classifier_rev7.json 188+/0−`,
  `docs/level1_desktop.md 13+/9−`, `tests/test_level1_demo.py 125+/0−`, `tests/test_level1_rearm_check.py 42+/0−`.
- Test viết TRƯỚC: `TestRev7ConfigFile` (3: file được theo dõi và sạch; ghi lại ra file tạm = đúng từng byte file đã commit; giá trị = §2,
  `rearm_mode` classifier, `_about` chứa sha256 file gốc, file lần sửa 5 không có khóa mới, config mặc định vẫn `motion_pose`),
  `TestRev7DemoConfig` (5, clip D2 — kiểm đường code, không phải độ chính xác: lệnh demo headless với file mới thoát 0, `rearm_mode`
  classifier, `config.path`/`sha256` đúng, không `overrides`; app đọc cửa sổ 700, `thresholds("dấu huyền") = (0.78, 200)`, chữ cái giữ
  `cls_conf`/`cls_stable_ms`, `dropout_tolerance_ms` 60, `word_gap_ms` 2500; dấu thanh 0.80 phát ở 231 ms với HUD `/200 (tone)`, chữ 0.80
  không phát; một cửa sổ rớt giữa chuỗi: file mới phát ở 1330 với `run_since_ms` 1000, file lần sửa 5 không phát; tay rời khung từ khung
  41 tới hết clip (ngắn hơn `word_gap_ms` mới, dài hơn cũ): file lần sửa 5 ⇒ 1 word gap + " ", file mới ⇒ 0 word gap, không " "),
  `TestRev7DesktopDoc` (1). ĐỎ: `Ran 4 — FAILED (failures=1, errors=4)` (file chưa có, tài liệu chưa có lệnh; `R7b_red.log`). Lần chạy
  xanh đầu `R7b_green.log`: ngoài test "đã commit" (đỏ đúng mong đợi trước commit) còn `test_r7_word_gap` đỏ do CHÍNH TEST đo sai mốc
  "khung cuối có tay" (lấy `t_end_ms` lớn nhất của segment — ở chế độ `classifier` segment đóng sớm hơn khung cuối có tay); sửa test
  (chưa commit) sang `segmenter._last_hand_ts`, thêm kiểm mốc word gap của file lần sửa 5; không đổi mã ⇒ `Ran 6 — OK` (`R7b_green2.log`).
- Hồi quy cuối tại `acd8bed` (`_work/_plan15/rev7b_final_*.log`): 12 module Level 1 `Ran 294 — OK (skipped=1)` (skip duy nhất
  `test_u1_summary`, thiếu file U1 của người dùng); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`; guard
  `[DoD7-guard] known=9 allowed=36`, `Ran 28 — OK`.
- AC-7a: `git diff 5e08fbd..HEAD --numstat -- tests/` → `test_level1_core.py 94/0`, `test_level1_decoder.py 295/0`,
  `test_level1_demo.py 411/0`, `test_level1_rearm_check.py 126/0` (cột xóa = 0; từ `4f913a2` cũng 0). `configs/level1_realtime.json`
  (`cc178955…eb54b`), `configs/level1_demo_classifier.json` (`568f97d8…c397e2`) không đổi; sha256 checkpoint `a6311820…5b708a2` không đổi;
  không train. AC-7b giờ đạt cả ở app với lệnh demo (`TestRev7DemoConfig`).
- Còn cho reviewer / người dùng: phiên webcam với lệnh mục 1 (kỳ vọng "độ trễ đổi tay dưới 1 s" của §2 T2 chưa đo); AC1-đủ (31 module)
  không chạy trên cloud.

## Lần sửa 8 — coder (phiên cloud 2026-10-05, `docs/plans/15-lan-sua-8.md` @ `1af1926`; Tầng 1, chỉ app demo) — **M1–M3 XONG**
- Quyết định của người dùng (thread dự án): "Chỉ Tầng 1 trên app demo (cờ --min-detection-conf, CLAHE khi thiếu sáng, giữ dshow, không
  train lại)". Nhánh: commit trên `claude/level1-rearm-rev8-0h67t5` (tạo từ `origin/cloud/2026-10-04-level1-rearm` @ `1af1926`), push lên
  cả nhánh đó và `cloud/2026-10-04-level1-rearm` sau mỗi mục.
- Đầu phiên (container mới): `.venv` → `/opt/vslt-venv`, cài `seaborn`; khôi phục (không commit): kernel `phmvnsm33/vsl-extract-alphabet`
  → 686 npz `alphabet_hands` + manifest; `archive_private_kaggle.py restore` 2 manifest (provenance 13 file, step4 18 file; thư mục tải
  phải nằm ngoài repo) — sha256 `checkpoints/alphabet_best.pt` = `a6311820…5b708a2` khớp; 640 mp4 hauuto; 46 video QIPEDC chữ cái theo
  manifest (`-f Dataset/Videos/<id>.mp4`). GitNexus không dùng ⇒ impact = text search, detect-changes = `git diff --numstat`.
- Mốc tại `1af1926` (`_work/_plan15/rev8_baseline_*.log`): 12 module Level 1 `Ran 294 — OK (skipped=1)` (skip duy nhất `test_u1_summary`,
  thiếu file U1 của người dùng); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip; guard `known=9 allowed=36`,
  `Ran 28 — OK`.

### M1 — `HandLandmarkSession(**overrides)` (`0f0af4f`)
- Mã (`src/inference/hand_live.py`): từ khóa của `LEVEL1_HANDS_KWARGS` truyền cho phiên thay giá trị đó cho mọi graph của phiên (cả
  `reset()`); `self.kwargs` = bản sao `{**LEVEL1_HANDS_KWARGS, **overrides}`; giá trị `None` ⇒ giữ mặc định; từ khóa lạ ⇒ `TypeError`, không
  dựng graph (lựa chọn của coder: plan cho phép `Optional[float] = None` hoặc `**kwargs`). `LEVEL1_HANDS_KWARGS`, `extractor_info()` không đổi.
- Impact (text search): `HandLandmarkSession` gọi bởi `backend/main.py` (WS, không đối số), `level1_demo.py` (`session_factory` mặc định),
  test (`RecordingSession` của AC-E và `_HandAwaySession` gọi `super().__init__()` không đối số; `tests/test_cors_origin_bind.py` thay bằng
  đối tượng của test). detect-changes: `hand_live.py 15+/3−`, `tests/test_level1_demo.py 132+/0−`.
- Test viết TRƯỚC (`tests/test_level1_demo.py`): `TestHandSessionKwargsM1` (5: mặc định = `LEVEL1_HANDS_KWARGS` với spy `Hands`, 0.35 cho
  cả graph sau `reset()` và hằng số không đổi, `None` = mặc định, từ khóa lạ, lớp con không đối số) + `TestHandSessionClipM1` (1, clip D2:
  phiên `min_detection_confidence=0.5` tường minh trả đúng từng khung như phiên mặc định — landmark `array_equal`, handedness, score; phiên 0.35
  chạy hết clip). ĐỎ: `Ran 6 — FAILED (errors=4, skipped=1)` (`_work/_plan15/M1_red.log`; test từ khóa lạ xanh từ đầu vì hàm cũ không nhận
  đối số nào; skip = clip chưa khôi phục lúc đó). XANH: `Ran 6 — OK` có clip (`M1_green.log`); 12 module L1 `Ran 300 — OK (skipped=1)`,
  2 module mới `Ran 13 — OK`, AC1-ngắn `Ran 167 — OK` 0 skip (gồm AC5 `test_hand_live_equivalence`, AC4-a `test_hand_landmarks_ws`), guard
  `known=9 allowed=36`, `tests.test_cors_origin_bind` `Ran 21 — OK` (`_work/_plan15/M1_full_*.log`, mã M2 cất bằng `git stash` lúc chạy).

### M2 — `enhance_low_light` (`24cfc5f`)
- Mã (`src/inference/level1_core.py`, thêm `import cv2`): `enhance_low_light(frame_bgr, threshold=LOW_LIGHT_THRESHOLD, clip_limit=
  CLAHE_CLIP_LIMIT) -> (frame, enhanced)` đúng §2 M2 (trung bình ảnh xám < ngưỡng ⇒ LAB, CLAHE trên L với `CLAHE_TILE_GRID` 8x8, về BGR,
  mảng mới, `True`; ngược lại chính đối tượng khung, `False`); khung vào không bị sửa; chỉ nhận uint8 HxWx3 (`ValueError`, lựa chọn của coder).
  Giá trị 80 / 2.0 / 8x8 là giá trị thiết kế của plan, đặt thành hằng.
- Impact (text search): hàm và hằng mới; `level1_core` được import bởi `level1_demo.py`, `scripts/level1_rearm_check.py`,
  `scripts/level1_segment_report.py` (không gọi hàm mới) — thêm `cv2` (đã có trong `.venv`). detect-changes: `level1_core.py 27+/1−`,
  `tests/test_level1_core.py 85+/0−`.
- Test viết TRƯỚC `TestEnhanceLowLightM2` (5: khung toàn 30 ⇒ `True`, mảng mới, sáng hơn, bằng bộ tham chiếu viết trong test; ramp tối ⇒
  độ lệch chuẩn ảnh xám tăng, `clip_limit` được dùng; khung toàn 150 ⇒ đúng đối tượng, `False`; ranh giới 79/80 và tham số `threshold`;
  khung sai kiểu). ĐỎ: `Ran 5 — FAILED (errors=5)` (ImportError; `_work/_plan15/M2_red.log`). Lần xanh đầu (`M2_green.log`) đỏ 1 test do
  CHÍNH TEST: ramp 48x64 quá nhỏ cho lưới 8x8 nên `clip_limit` 2 và 4 cho cùng ảnh; sửa test (chưa commit) sang ramp 640x480 và so "khác
  nhau" thay vì "độ lệch chuẩn lớn hơn"; không đổi mã ⇒ `Ran 5 — OK` (`M2_green2.log`). Hồi quy: 12 module L1 `Ran 305 — OK (skipped=1)`,
  2 module mới `Ran 13 — OK`, AC1-ngắn `Ran 167 — OK`, guard `known=9 allowed=36` (`_work/_plan15/M2_full_*.log`).

### M3 — cờ CLI, HUD, JSON, tài liệu (`7d32aea`)
- Mã (`level1_demo.py`): `--min-detection-conf` (`detection_conf`: số hữu hạn trong (0, 1]; mặc định `DEFAULT_MIN_DETECTION_CONF` =
  `LEVEL1_HANDS_KWARGS["min_detection_confidence"]`), `--auto-enhance`. `session_factory` mặc định thành
  `functools.partial(HandLandmarkSession, min_detection_confidence=…)` (graph warm-up và graph luồng); factory do test truyền vào dùng
  nguyên (lựa chọn của coder). `_process`: với `--auto-enhance`, `enhance_low_light(frame)` đưa vào `session.process`, `frame` gốc vẫn được
  vẽ landmark và hiển thị; thời gian CLAHE ở stage mới `low_light_enhance` (chỉ có khi bật cờ; không cộng vào `mediapipe`). HUD: dòng
  `[MP: conf=<x.xx> | CLAHE: on|off]` ngay dưới dòng trạng thái / `[classifier]`, chỉ khi khác mặc định. JSON: khóa gốc `hand_detection`
  (`min_detection_confidence`, `auto_enhance`; với `--auto-enhance` thêm `frames_enhanced`, `low_light_threshold`, `clahe_clip_limit`,
  `clahe_tile_grid`) chỉ khi khác mặc định — plan không nêu JSON, coder thêm để biết một lần chạy đã dùng ngưỡng / tăng sáng nào.
  `docs/level1_desktop.md`: mục 1 trỏ tới mục 8; mục 8 (lệnh của plan, hai cờ, HUD, JSON, dshow, giới hạn; không số đo). Config không đổi.
- Impact (text search): `Level1App.__init__`, `_hud_lines`, `_process`, `report`, `build_parser` (gọi bởi `main`, `tests/test_level1_demo.py`,
  `tests/test_level1_equivalence.py`); `Level1App` chỉ được tạo trong `main` và test. detect-changes: `level1_demo.py 58+/6−`,
  `docs/level1_desktop.md 26+/0−`, `tests/test_level1_demo.py 374+/0−`.
- Test viết TRƯỚC (`tests/test_level1_demo.py`, 17): `TestDetectionArgsM3` (4), `TestMinDetectionConfM3` (3: spy `Hands` — 0.35 ở cả 2
  graph, JSON `hand_detection`, config không đổi; không cờ và `--min-detection-conf 0.5` ⇒ mọi graph = `LEVEL1_HANDS_KWARGS`, JSON cùng cây
  khóa, tokens/labels/segments/counts bằng app tại `1af1926`), `TestAutoEnhanceM3` (5: clip D2 tối ở mọi khung ⇒ mỗi khung vào MediaPipe
  = `enhance_low_light(khung đọc)` và không phải đối tượng đọc, `frames_enhanced` = số khung xử lý; clip `khoi/a_khoi_A_001.mp4` sáng ở mọi
  khung ⇒ đúng đối tượng đọc, `frames_enhanced` 0; không cờ ⇒ như cũ; chế độ cửa sổ (lệnh cửa sổ ghi lại) ⇒ landmark vẽ lên khung đọc),
  `TestRev8CommandM3` (1: lệnh của plan qua `main`, `--source` clip D2 headless), `TestDetectionHudM3` (1: dòng HUD đúng định dạng ở 2
  config, không cờ ⇒ các dòng HUD bằng app `1af1926`), `TestCameraDshowM3` (2: 3 config giữ `dshow`; `CameraReader` mở bằng
  `cv2.CAP_DSHOW` với kích thước / buffer của config — `VideoCapture` thay bằng lớp ghi lại trong test, không mở camera), `TestDesktopDocM3`
  (1). ĐỎ (`_work/_plan15/M3_red_by_class.log`, chạy từng lớp vì argparse thoát trong setUpClass): Args `FAILED (failures=1, errors=2)`,
  MinDetectionConf / AutoEnhance thoát 2 (argparse từ chối cờ), Rev8Command `FAILED (failures=1)`, Hud `FAILED (errors=2)`, Doc
  `FAILED (failures=1)`; xanh từ đầu đúng mong đợi: `TestCameraDshowM3` (giữ hành vi có sẵn) và test từ chối giá trị ngoài (0, 1] (cờ chưa
  có cũng bị từ chối). XANH: `Ran 17 — OK` (`M3_green.log`).

### Kết thúc lần sửa 8 — AC-8a…AC-8e
- Commit: `0f0af4f` M1, `24cfc5f` M2, `7d32aea` M3 (+ commit tiến độ này).
- Hồi quy tại `7d32aea` (`_work/_plan15/M3_full_*.log`): 12 module Level 1 `Ran 322 — OK (skipped=1)` (= 294 cũ + 28 mới; skip duy nhất
  `test_u1_summary`); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip; guard `[DoD7-guard] known=9 allowed=36`,
  `Ran 28 — OK`; `tests.test_cors_origin_bind` `Ran 21 — OK`.
- AC-8a: `git diff 1af1926..HEAD --numstat -- tests/` → `test_level1_core.py 85/0`, `test_level1_demo.py 506/0` (cột xóa = 0).
  `git diff 1af1926..HEAD` chỉ gồm file trong §3 của plan; `configs/` (sha256 `level1_realtime.json` `cc178955…eb54b`,
  `level1_demo_classifier.json` `568f97d8…c397e2`, `level1_demo_classifier_rev7.json` `a2aea62e…ce4a7d`), `backend/main.py`,
  `realtime_demo.py`, `src/data/alphabet_preprocessing.py`, `README.md` không đổi; sha256 checkpoint không đổi; không train.
- AC-8b: đạt (không cờ ⇒ graph = `LEVEL1_HANDS_KWARGS`, JSON/HUD như `1af1926`, AC5 + AC4-a + 12 module L1 xanh). AC-8c: đạt
  (`TestMinDetectionConfM3`). AC-8d: đạt trên clip (`TestAutoEnhanceM3`, `TestRev8CommandM3`). AC-8e: phần kiểm được trên cloud đạt
  (`TestCameraDshowM3`); "ổn định trên webcam laptop" cần phiên webcam của người dùng trên Windows.
- Ghi chú: clip D2 (người ký hau) tối dưới ngưỡng ở mọi khung (`test_m3_clips_are_dark_and_bright`) ⇒ dữ liệu train có khung tối không tăng
  sáng; `--auto-enhance` làm khung vào MediaPipe khác lúc trích landmark train (ghi ở giới hạn mục 8 của `docs/level1_desktop.md`).
- Còn cho reviewer / người dùng: hồi quy trên Windows và phiên webcam theo checklist §5 của plan
  (`python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance`);
  tác dụng lên tỉ lệ thấy tay / độ chính xác chưa đo. AC1-đủ (31 module) không chạy trên cloud.

## Lần sửa 9 — coder (phiên cloud 2026-10-05, `docs/plans/15-lan-sua-9.md` @ `03d17b8`; cử chỉ Xòe 5 ngón = dấu cách) — **S1–S3 XONG**
- Nhánh: commit trên `claude/level1-rearm-rev9-o1gc4j` (tạo từ `origin/cloud/2026-10-04-level1-rearm` @ `03d17b8`), push lên cả nhánh đó và
  `cloud/2026-10-04-level1-rearm` sau mỗi mục.
- Đầu phiên (container mới): `.venv` → `/opt/vslt-venv`, cài `seaborn`; khôi phục (không commit): kernel `phmvnsm33/vsl-extract-alphabet`
  → 686 npz + manifest; `archive_private_kaggle.py restore` 2 manifest (provenance 13 file, step4 18 file) — sha256
  `checkpoints/alphabet_best.pt` = `a6311820…5b708a2` khớp; 640 mp4 hauuto; 46 video QIPEDC chữ cái theo manifest.
  GitNexus 1.6.12 dùng được (`npx -y gitnexus@latest analyze` + `impact` + `detect-changes --scope all --repo .`).
- Mốc tại `03d17b8` (worktree sạch, dữ liệu symlink; `_work/_plan15/rev9_baseline_*.log`): 12 module Level 1 `Ran 322 — OK (skipped=1)`
  (skip duy nhất `test_u1_summary`, thiếu file U1 của người dùng); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip;
  guard `known=9 allowed=36`, `Ran 28 — OK`.

### S1 — `is_open_palm_space` (`9e29dc1`)
- Mã (`src/inference/level1_core.py`): đúng 3 tiêu chí §2 S1 trên khoảng cách 3D (hoặc 2D) giữa các điểm của cùng bàn tay; `None`, shape khác
  [21, 2|3], giá trị không hữu hạn, cổ tay trùng MCP giữa ⇒ `False`. Hằng: `LONG_FINGERS`, `THUMB_SPREAD_RATIO` = 1.1 (giá trị của plan),
  `FINGER_SPREAD_MIN` = 1.2 (lựa chọn của coder — plan chỉ ghi "không quá nhỏ"): đầu ngón kề nhau phải cách xa hơn 1.2 lần khoảng MCP tương
  ứng; ngón khép sát giữ tỉ lệ quanh 1 (cao hơn một chút khi hai ngón dài khác nhau), ngón xòe thì loe ra. Giá trị chọn bằng lập luận hình học
  trên bàn tay sơ đồ TRƯỚC khi chạy trên dữ liệu thật, không chỉnh sau đó. App đưa vào `aspect_points(landmarks, w, h)` (x, z nhân rộng/cao,
  như bộ tách) để khoảng cách cùng thang trên mọi trục.
- Impact: hàm và hằng mới, không symbol cũ nào đổi. detect-changes: `level1_core.py 48+/0−`, `tests/test_level1_core.py 147+/0−`, risk low.
- Test viết TRƯỚC `TestOpenPalmSpaceS1` (6; bàn tay sơ đồ `SchematicHand` dựng từ góc khớp trong test — không phải dữ liệu): xòe ⇒ True;
  b, a, c, d, h ⇒ False; từng tiêu chí cần thiết (ngón cái gập + ngón xòe, ngón cái dang + ngón khép, ngón áp út / út gập, đầu ngón cái quặp
  về cổ tay); ngưỡng 1.1 (dời đầu ngón cái tới 1.02 / 0.98 lần ngưỡng); bất biến vị trí / tỉ lệ / xoay / nghiêng / lật; đầu vào hỏng.
  ĐỎ: `Ran 6 — FAILED (errors=6)` (`_work/_plan15/S1_red.log`); XANH: `Ran 6 — OK` (`S1_green.log`); `tests.test_level1_core` +
  `tests.test_level1_guard` `Ran 43 — OK`.
- Thăm dò trên dữ liệu thật (script `_work/_plan15/S1_real_scan.py`, KHÔNG commit, log `S1_real_scan.log`; kiểm logic, không phải độ chính
  xác): hàm trên mọi khung có tay của 686 clip train (`aspect_points`, kích thước của manifest). 8 clip có chuỗi khung xòe dài từ 250 ms trở
  lên, cả 8 là take `A_001` của người ký `khoi` (h, p, s, l, b, g, v, t) và chuỗi nằm ở các khung có tay đầu tiên; xem ảnh khung (không
  commit) của cả 8: người ký giơ bàn tay xòe 5 ngón thật trước khi làm chữ, khung chữ giữ yên ở cuối clip không bị nhận. Không clip nào
  có chuỗi xòe dài như vậy trong lúc giữ chữ; các khung lẻ còn lại đều ngắn hơn ngưỡng giữ. Đây là bằng chứng hàm nhận được bàn tay xòe thật
  (ngưỡng 1.1 đạt được trên tay thật), không phải số đo độ chính xác; webcam chưa thử.

### S2 — `SpaceGestureTracker` + nối vào app (`69f88ce`)
- Mã (`level1_demo.py`): `SpaceGestureTracker(hold_ms=GESTURE_SPACE_HOLD, rearm_ms=GESTURE_SPACE_REARM)`; `update(ts, is_space, has_hand=True)`
  đúng §2 S2 (giữ xòe ≥ hold_ms khi armed ⇒ True một lần, disarmed; tư thế khác giữ > rearm_ms hoặc mất tay ⇒ armed; khung khác giữa chuỗi
  xòe ⇒ đếm giữ lại từ đầu); `held_ms`, `reset()` (gọi khi nhấn `p`); `hold_ms`/`rearm_ms`/ts không hữu hạn hoặc ≤ 0 ⇒ ValueError.
  Thêm `has_hand` (từ khóa có mặc định) vì plan yêu cầu "mất tay ⇒ rearm" mà chữ ký `update(ts, is_space)` không phân biệt được.
  `_process`: khung có tay ⇒ `is_open_palm_space(aspect_points(...))` (thời gian tính trong stage `segmenter` — thêm stage sẽ đổi khóa `stages`
  mà test AC-L cũ khóa); `_gesture_step` → `speller.key("space", t_ms)` + sự kiện `{"event": "gesture_space", "t_ms", "added"}`.
  Lựa chọn của coder: ở chế độ `classifier` dấu cách đi qua timeline (mục `"space"`, như word gap / phím `n`) để đứng sau nhãn của các khung
  trước khi kết quả cửa sổ đến muộn (worker); headless thì áp ngay như plan. Mục "có thể bỏ qua nạp khung xòe vào `window.push`": khung xòe
  được đưa vào cửa sổ như khung KHÔNG có tay (cửa sổ không phân loại tại đó; bộ giải mã thấy không tay ⇒ luật 4 `hand_lost_ms` vẫn áp, nên
  chữ cuối có thể lặp lại sau dấu cách nếu xòe đủ lâu). `motion_pose`: bộ tách vẫn nhận khung xòe như cũ (plan chỉ nói tới cửa sổ) — ghi ở
  giới hạn mục 9 của `docs/level1_desktop.md`. HUD: `[Cử chỉ: Dấu cách <giữ>/<hold>]` khi đang giữ (armed), `[Ký hiệu: Dấu cách (Space)]`
  trong `GESTURE_SPACE_FLASH` (600, giá trị của coder) thời gian luồng sau dấu cách; không có cử chỉ ⇒ không dòng nào (HUD như cũ).
- Guard: G2 coi mọi binding tên có `ms` gán số gõ tay là số hiệu năng (`hold_ms: float = 250.0` của plan sẽ bị bắt) ⇒ giá trị thiết kế đặt
  trong hằng `GESTURE_SPACE_HOLD` / `GESTURE_SPACE_REARM` / `GESTURE_SPACE_FLASH` (đơn vị ghi ở chú thích, nêu rõ là giá trị thiết kế, không
  phải số đo). Cần reviewer xác nhận cách đặt tên này.
- Impact (GitNexus): `_process` LOW, `_hud_lines` LOW, `_key` LOW, `_drain_timeline` MEDIUM (5 caller trực tiếp, đều trong `Level1App`);
  detect-changes: `level1_demo.py 122+/3−`, `tests/test_level1_demo.py 295+/0−`, risk high (8 process của `Level1App`/`main`).
- Test viết TRƯỚC (`tests/test_level1_demo.py`): `TestSpaceGestureTrackerS2` (9: 4 trường hợp của plan + nháy < 150 ms, mất tay, giữ bị ngắt,
  `hold_ms`/`held_ms`, `reset`), `TestGestureSpaceAppS2` (6, clip thật `khoi/b_khoi_A_001.mp4`: xòe 5 ngón rồi chữ b — đúng 1 dấu cách tại
  khung mà luật cho (tính lại trong test từ landmark ghi được), chữ b giữ yên không kích hoạt, có token trước ⇒ thêm `' '`, không cửa sổ nào ở
  khung xòe, segment/token `motion_pose` bằng app `03d17b8`; clip D2 không xòe ⇒ báo cáo bằng app `03d17b8` ở 2 chế độ),
  `TestGestureSpaceHudS2` (3: dòng tiến độ / flash, thứ tự timeline, tạm dừng). ĐỎ (`_work/_plan15/S2_red.log`): tracker `FAILED (errors=9)`,
  app `FAILED (failures=5)` (5 subtest trong 3 test), HUD `FAILED (errors=4)`; 3 test app xanh từ đầu đúng mong đợi (dữ kiện của clip, segment
  `motion_pose` và báo cáo clip D2 "không đổi"). XANH: 18 OK
  (`S2_green.log`); `tests.test_level1_demo` + `core` + `guard` `Ran 152 — OK`.
- Kiểm tay (không phải số liệu, `_work/_plan15/S2_palm_clips_explore.log`): 8 clip khoi `A_001` ở cả 2 chế độ ⇒ 1 cử chỉ mỗi clip, token bằng
  app `03d17b8` (lúc xòe text còn rỗng nên không thêm gì).

### S3 — cờ CLI, JSON, tài liệu (`ab0cd3f`)
- Mã: `--gesture-space` / `--no-gesture-space` (`argparse.BooleanOptionalAction`, mặc định bật), `--space-hold-ms` (`positive_ms`, mặc định
  `GESTURE_SPACE_HOLD`). JSON: khóa gốc `gesture_space` = `enabled, hold_ms, rearm_ms, flash_ms, palm_frames, emits, spaces_added`, CHỈ khi
  đã thấy ít nhất một khung xòe hoặc `--space-hold-ms` khác mặc định (lựa chọn của coder: plan bật mặc định, mà test cũ AC-6b / M3 khóa danh
  sách khóa của báo cáo khi không cờ ⇒ ghi luôn sẽ phải sửa test cũ). `--no-gesture-space` ⇒ không kiểm hình tay, báo cáo/HUD như `03d17b8`.
  Docstring + `docs/level1_desktop.md` mục 1 (lệnh gợi ý của plan với `--no-auto-space`), mục 2 (dòng cử chỉ), mục 9 (mới; không số đo).
- Impact (GitNexus): `build_parser` LOW (2), `Level1App.report` LOW (3). detect-changes: `docs/level1_desktop.md 34+/0−`,
  `level1_demo.py 21+/0−`, `tests/test_level1_demo.py 157+/0−`, risk low.
- Test viết TRƯỚC: `TestGestureSpaceArgsS3` (2), `TestGestureSpaceFlagsS3` (4, clip thật: `--no-gesture-space` bằng app `03d17b8` ở 2 chế độ —
  khóa, token, nhãn, segment, sự kiện, counts, dòng HUD; khối JSON khi bật; `--space-hold-ms 400` (1 dấu cách, muộn hơn) / `500` (chuỗi xòe
  của clip ngắn hơn ⇒ 0); clip D2 với hold 400 ⇒ khối ghi 0 khung xòe, token như cũ), `TestRev9CommandS3` (1, lệnh gợi ý qua `main` headless
  trên clip xòe), `TestDesktopDocS3` (1). ĐỎ (`_work/_plan15/S3_red.log`): Args `FAILED (failures=1)`, Flags thoát 2 (argparse từ chối cờ),
  Command `FAILED (errors=1)`, Doc `FAILED (failures=1)`; test giá trị sai xanh từ đầu (cờ chưa có cũng bị từ chối). XANH: 8 OK
  (`S3_green.log`; lần đầu Doc đỏ vì tài liệu chỉ ghi `--no-gesture-space`, đã thêm `--gesture-space` vào tài liệu, không đổi test).

### Kết thúc lần sửa 9 — AC-9a…AC-9e
- Commit: `9e29dc1` S1, `69f88ce` S2, `ab0cd3f` S3 (+ commit tiến độ này).
- Hồi quy tại `ab0cd3f` (`_work/_plan15/rev9_final_*.log`): 12 module Level 1 `Ran 354 — OK (skipped=1)` (= 322 cũ + 32 mới; skip duy nhất
  `test_u1_summary`); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip; guard `[DoD7-guard] known=9 allowed=36`,
  `Ran 28 — OK`.
- AC-9a: `git diff 03d17b8..HEAD --numstat -- tests/` → `test_level1_core.py 147/0`, `test_level1_demo.py 452/0` (cột xóa = 0). File đổi
  chỉ trong §3 của plan; `configs/` (sha256 `level1_realtime.json` `cc178955…`, `level1_demo_classifier.json` `568f97d8…`,
  `level1_demo_classifier_rev7.json` `a2aea62e…`), `src/data/alphabet_preprocessing.py`, `backend/main.py`, `realtime_demo.py` không đổi;
  checkpoint `a6311820…5b708a2` không đổi; không train.
- AC-9b: đạt trên bàn tay sơ đồ (b, a, c, d, h ⇒ False; xòe ⇒ True); trên clip train chỉ các bàn tay xòe thật kích hoạt (thăm dò S1, không
  phải số đo). AC-9c: đạt (`TestSpaceGestureTrackerS2`, clip thật S2/S3). AC-9d: đạt (`test_9d_no_gesture_space_same_as_before`).
  AC-9e: đạt (số ở trên).
- Còn cho reviewer / người dùng: hồi quy trên Windows và phiên webcam theo checklist §5 của plan (lệnh ở mục 9 của `docs/level1_desktop.md`).
  Ngưỡng 1.1 / 1.2 và thời gian giữ chưa thử trên webcam; nếu khó kích hoạt thì xem dòng HUD `[Cử chỉ: ...]` có hiện không (không hiện ⇒ hình
  tay chưa qua tiêu chí, thường là ngón cái chưa dang đủ hoặc các ngón chưa tách).

## Lần sửa 10 — coder (phiên cloud 2026-10-05, `docs/plans/15-lan-sua-10.md` @ `8e6d6fb`; khóa tay thuận, làm mượt landmark, nhắc góc tay) — **P1–P3 XONG**
- Nhánh: commit trên `claude/level1-rearm-rev10-83s46p` (tạo từ `origin/cloud/2026-10-04-level1-rearm` @ `8e6d6fb`), push lên cả nhánh đó và
  `cloud/2026-10-04-level1-rearm` sau mỗi mục. Thứ tự làm: P2 → P3 → P1 (P1 chờ quyết định của người dùng, xem dưới).
- Đầu phiên (container mới): `.venv` → `/opt/vslt-venv`, cài `seaborn`; khôi phục (không commit): kernel `phmvnsm33/vsl-extract-alphabet`
  → 688 file (686 npz + manifest + tasks); `archive_private_kaggle.py restore` 2 manifest (provenance 13 file, step4 18 file) — sha256
  `checkpoints/alphabet_best.pt` = `a6311820…5b708a2` khớp; 640 mp4 hauuto; 46 video QIPEDC chữ cái theo manifest.
  GitNexus KHÔNG dùng được trong phiên này (`npx -y gitnexus@latest` bị chặn quyền chạy mã tải về) ⇒ impact bằng text search + `git diff`.
- Mốc tại `8e6d6fb` (worktree sạch `_work/base10`, dữ liệu symlink; `_work/_plan15/rev10_baseline_*.log`): 12 module Level 1 `Ran 354 — OK
  (skipped=1)` (skip duy nhất `test_u1_summary`); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip; guard
  `known=9 allowed=36`, `Ran 28 — OK`. (Lượt mốc đầu thiếu symlink tới file khôi phục trong `reports/` và video QIPEDC ⇒ 2 lỗi + 5 skip
  không liên quan code; chạy lại sau khi nối đủ.)

### P2 — `LandmarkSmoother` + `--smooth-landmarks` (`f4f4223`)
- Mã: `level1_core.LandmarkSmoother(alpha_static=0.6, alpha_dynamic=0.9, speed_threshold=0.15)` (giá trị của plan); `filter(ts_ms, lm)` =
  EMA với trọng số khung mới `alpha_static` khi tốc độ < ngưỡng, `alpha_dynamic` khi ngược lại hoặc bước thời gian ≤ 0; `None` / `reset()`
  xóa trạng thái, khung đầu giữ nguyên; trả `float32[21, 3]`, không sửa mảng vào; tham số / landmark sai ⇒ `ValueError`.
  Lựa chọn của coder: tốc độ = khoảng cách x, y giữa tâm bàn tay (trung bình 21 điểm) của khung mới và của đầu ra trước, chia bước thời gian
  (đơn vị ảnh MediaPipe / giây) — không dùng z vì z là trục nhiễu, tâm bàn tay trung bình hóa rung của từng điểm.
  `level1_demo`: `--smooth-landmarks` / `--no-smooth-landmarks`; landmark mỗi khung qua bộ lọc ngay sau MediaPipe (trước bộ tách, cửa sổ,
  cử chỉ, hình vẽ); stage `landmark_smooth` và khóa JSON `landmark_smoothing` (`enabled, alpha_static, alpha_dynamic, speed_threshold,
  frames_static, frames_dynamic`) chỉ khi bật.
- **Lệch plan — mặc định TẮT** (plan ghi `default=True`): §1 và AC-10d yêu cầu chạy không cờ mới giữ nguyên hành vi cũ. Bằng chứng: bật
  mặc định ⇒ `tests.test_level1_demo` `Ran 117 — FAILED (failures=17)` (`_work/_plan15/P2_default_on_evidence.log`): segment / độ tin cậy
  khác app ở commit trước trong `test_a2_motion_pose_identical_to_before_d2`, `test_s2_motion_pose_segmenter_unchanged`,
  `test_s2_no_open_palm_same_report_as_before`, `test_m3_default_run_equals_rev7_app`, `test_9d_…`, `test_9c_…`, `test_6b_…`, AC-L, M3.
  Theo quy tắc không sửa test cũ ⇒ để tắt; lệnh gợi ý ở mục 10 của `docs/level1_desktop.md` bật bằng `--smooth-landmarks`.
- Impact (text search): `Level1App` chỉ dùng trong `level1_demo.py` + `tests/test_level1_demo.py`; `build_parser` còn dùng ở
  `scripts/level1_trace_report.py`, `tests/test_level1_equivalence.py` (cờ mới có mặc định, không đổi gì với họ). diff: `level1_demo.py 31+/3−`,
  `level1_core.py 54+/0−`, `tests/test_level1_core.py 110+/0−`, `tests/test_level1_demo.py 154+/0−`.
- Test viết TRƯỚC: `TestLandmarkSmootherP2` (8: giá trị mặc định; tay tĩnh + nhiễu Gauss trục z (σ 0.02, seed cố định, trên bàn tay sơ đồ)
  ⇒ phương sai z ≤ 50 % ở MỌI khớp, trung bình giữ trong 0.2σ, x/y không đổi; bước nhảy lớn ⇒ khung đầu đã đi 90 %, sau 3 khung sai < 1 %;
  trọng số đúng; None/reset; không sửa đầu vào; tham số/landmark sai), `TestSmoothLandmarksArgsP2` (1), `TestSmoothLandmarksAppP2` (4, clip
  D2: đầu vào bộ tách và cửa sổ = bộ lọc tính lại từ landmark ghi được, rung z giữa khung kề nhau thấp hơn raw, khối JSON + stage, không cờ ⇒
  landmark raw và báo cáo bằng app `8e6d6fb` ở 2 chế độ). ĐỎ: core `FAILED (errors=13)` (`P2_red_core.log`), app thoát vì argparse không biết
  `--smooth-landmarks` (`P2_red.log`, chạy trên mã `8e6d6fb`). XANH: 13 OK; `test_level1_demo` + `core` + `guard` `Ran 173 — OK` (`P2_green.log`).

### P3 — `foreshortening_ratio` + nhắc góc tay + tài liệu mục 10 (`72b5c64`)
- Mã: `level1_core.foreshortening_ratio(lm)` = `dist_2d(8, 5) / dist_3d(8, 5)` ∈ [0, 1] (None / shape khác [21, 3] / không hữu hạn / đầu ngón
  trùng MCP ⇒ 1.0). App: `_angle_step` mỗi khung trên `aspect_points` (tính trong stage `segmenter`, không thêm stage), đếm khung có tay
  liên tiếp với tỉ lệ < `FORESHORTEN_RATIO_MIN` 0.3; > `FORESHORTEN_FRAMES` 3 ⇒ dòng HUD `[Góc tay: Hơi nghiêng tay 20°]` màu vàng
  (`Hud.HINT_RGB` cho dòng nhỏ bắt đầu `[Góc tay:`). Luôn bật, chỉ HUD (JSON/token/segment không đổi ⇒ AC-10d giữ). Docs mục 10.
- Thăm dò (script `_work/fs_scan.py`, `_work/fs_clips.py`, không commit; landmark trích trên Kaggle của 640 clip hauuto; kiểm logic, không
  phải độ chính xác): 31 / 640 clip có chuỗi > 3 khung tỉ lệ < 0.3, nhiều nhất `â` (9 clip), rồi `ê`, `ô`, `p`, `ư`, dấu thanh; clip `a` không có.
- Test: `TestForeshorteningRatioP3` (3), `TestAngleHintP3` (3: hằng của plan; 3 khung chưa hiện, khung thứ 4 hiện đúng 1 dòng, tay nghiêng
  hoặc mất tay ⇒ tắt, ở 2 chế độ; dòng vẽ màu vàng), `TestAngleHintClipP3` (2, clip thật `hau/aa_hau_A_001.mp4`: trạng thái dòng sau mỗi khung =
  luật tính lại từ landmark ghi được và có bật; clip D2 không bật; báo cáo D2 bằng app `8e6d6fb`), `TestDesktopDocP3` (1). ĐỎ (`P3_red.log`):
  `FAILED (failures=1, errors=8)`; `test_p3_report_unchanged` xanh từ đầu đúng mong đợi. Sửa test trước khi commit: bàn tay sơ đồ ban đầu có
  ngón trỏ xòe 14° nên tỉ lệ không bằng cos góc nghiêng ⇒ dùng ngón trỏ thẳng đứng (lỗi của test mới, không phải test cũ). Test tài liệu
  viết sau đoạn tài liệu (không có log đỏ). XANH: 8 OK (`P3_green.log`); `test_level1_demo` + `core` + `guard` `Ran 182 — OK` (`P3_full.log`).
- Impact: `Hud._build` chỉ gọi từ `Hud.compose`; `_hud_lines` / `_process` chỉ trong `Level1App`. diff: docs `28+`, `level1_demo.py 28+/2−`,
  `level1_core.py 20+`, tests `54+` / `152+`.

### P1 — `--dominant-hand` (`badb44d`)
- **Lỗi trong plan, đã hỏi người dùng (thẻ quyết định trong thread):** MediaPipe giả định ảnh đã lật gương; app không bao giờ lật khung khi
  xử lý, nên tay phải mang nhãn `Left` và `canonicalize_hand_sequence` lật x khi đa số `Left` (docstring của hàm). Dữ liệu train: chỉ 3 / 640
  clip hauuto đa số `Right`. Thử trên 44 clip train hau/tai (`_work/force_label.py`, không commit; kiểm đường code, không phải độ chính xác):
  không khóa 42/44 clip có segment dài nhất đúng chữ, khóa `Left` 42/44, khóa `Right` như chữ AC-10b 11/44 ⇒ lệnh checklist §5
  `--dominant-hand Right` sẽ lật gương tay phải so với dữ liệu train. Làm theo lựa chọn khuyến nghị "Theo tay người ký" (đúng help text của
  plan "Signer dominant hand"): `DOMINANT_HAND_LABELS = {"Right": "Left", "Left": "Right"}`; AC-10b hiểu là mọi khung có tay nhận MỘT nhãn cố
  định (nhãn của tay được chọn). Nếu người dùng chọn "Đúng chữ kế hoạch" thì chỉ đổi bảng này (và test mới tương ứng).
- Ghi chú: canonicalize lật theo ĐA SỐ nhãn trong segment / cửa sổ, không theo từng khung như §0 của plan viết; nhãn đổi qua lại chỉ gây lật
  khi đa số trong cửa sổ đổi. Trong landmark Kaggle: 67 / 640 clip có ít nhất một lần đổi nhãn, 38 trong đó là `â`, `ă`, `ô`, `ê`, `p`.
- Mã: `--dominant-hand {Right, Left, auto}` (mặc định `auto`); khóa nhãn ngay sau MediaPipe cho khung có tay (landmark không đổi) ⇒ bộ tách,
  cửa sổ và mọi bước sau; JSON `dominant_hand = {mode, label}` và HUD `[Tay: Phải]` / `[Tay: Trái]` chỉ khi khóa. Docs mục 10 (lệnh §5 của
  plan, cách chọn tay, lưu ý driver tự lật gương).
- Test viết TRƯỚC: `TestDominantHandArgsP1` (2), `TestDominantHandP1` (5, clip thật `khoi/aa_khoi_A_001.mp4` có nhãn Left/Right đổi qua lại:
  khóa ⇒ mọi khung có tay ở bộ tách / cửa sổ một nhãn, landmark nguyên vẹn, mọi segment canonicalize cùng một chiều (Right ⇒ lật, Left ⇒ không);
  JSON + HUD; `auto` ⇒ nhãn từng khung và báo cáo bằng app `8e6d6fb` ở 2 chế độ), `TestDesktopDocP1` (1). ĐỎ: args `FAILED (failures=1)`
  (`P1_red_args.log`), app thoát vì argparse (`P1_red.log`), doc `FAILED (failures=1)` (`P1_red_doc.log`). XANH: 7 OK (`P1_green.log`) + doc OK.
- Impact: `_process`, `_hud_lines`, `report`, `build_parser` chỉ trong `level1_demo.py` (+ 2 nơi dùng `build_parser` như P2). diff: docs
  `15+/3−`, `level1_demo.py 24+`, `tests/test_level1_demo.py 138+`.

### Kết thúc lần sửa 10 — AC-10a…AC-10d
- Commit: `f4f4223` P2, `72b5c64` P3, `badb44d` P1 (+ commit tiến độ này).
- Hồi quy tại `badb44d` (`_work/_plan15/rev10_final_*.log`): 12 module Level 1 `Ran 384 — OK (skipped=1)` (= 354 cũ + 30 mới; skip duy nhất
  `test_u1_summary`); 2 module mới `Ran 13 — OK`; AC1-ngắn 11 module `Ran 167 — OK`, 0 skip (gồm AC5 `test_hand_live_equivalence`, AC4-a
  `test_hand_landmarks_ws`); guard `[DoD7-guard] known=9 allowed=36`, `Ran 28 — OK`.
- AC-10a: `git diff 8e6d6fb..badb44d --numstat -- tests/` → `test_level1_core.py 164/0`, `test_level1_demo.py 444/0` (cột xóa = 0). File đổi
  chỉ trong §3 của plan; `configs/` (sha256 `level1_realtime.json` `cc178955…`, `level1_demo_classifier.json` `568f97d8…`,
  `level1_demo_classifier_rev7.json` `a2aea62e…`), `src/data/alphabet_preprocessing.py`, `backend/main.py`, `realtime_demo.py` không đổi;
  checkpoint `a6311820…5b708a2` không đổi; không train.
- AC-10b: đạt theo cách hiểu đã ghi ở P1 (một nhãn cố định trên mọi khung có tay; mọi segment canonicalize một chiều). AC-10c: đạt trên nhiễu
  sơ đồ (phương sai z ≤ 50 %, bám bước nhảy) và trên clip D2 (rung z thấp hơn raw). AC-10d: đạt (không cờ ⇒ báo cáo bằng app `8e6d6fb`; số ở trên),
  nhờ `--smooth-landmarks` mặc định tắt (lệch plan, ghi ở P2).
- Còn cho reviewer / người dùng: xác nhận cách hiểu `--dominant-hand` (thẻ quyết định) và mặc định tắt của `--smooth-landmarks`; hồi quy trên
  Windows và phiên webcam theo checklist §5 (lệnh ở mục 10 của `docs/level1_desktop.md`); tác dụng lên độ chính xác chưa đo.

## Lần sửa 13 — M0 (2026-10-08, mốc cad8cdc)
- Kế hoạch: `docs/plans/15-lan-sua-13.md`. Nhánh `cloud/2026-10-04-level1-rearm`, mốc HEAD `cad8cdc`.
- `sha256(checkpoints/alphabet_best.pt)` = `160e0c6825e365ba3d5481e2fd4d18423cf501c655aec618a453c524d8a17899` (v6 theo Q3 STATE 10:05).
- `git status` lưu tại `_work/_plan15_l13/m0_status.txt` (`modified: README.md`, 3 deleted CSV của người dùng, untracked files). Không sửa mã ở M0.
- AC-1 đo trên 28 module hiện có (lệnh 16 module gốc + 10 module test_level1_* hiện có + test_private_artifacts + test_frontend_contract) → log `_work/_plan15_l13/m0_ac1.log`:
  `Ran 670 tests in 853.938s` — `FAILED (failures=5, errors=2, skipped=1)`.
  - ERROR (2):
    1. `test_real_clips_match_training_evaluation (tests.test_fingerspelling_api.TestRealClipEquivalence)`: `KeyError: 'hauuto_aa_tai_B_001_tail_â'` do `train_alphabet_real.py:69` `load(..., slice_compound=True)` thêm mẫu cắt lát (review A1 #3).
    2. `setUpClass (tests.test_fingerspelling_deployed.TestDeployedCheckpointEquivalence)`: `KeyError: 'selected'` do checkpoint v6 sinh bởi `train_alphabet_real.py`, không phải run nested (review A1 #4).
  - FAIL (5):
    1. `test_b_bodies_and_responses_identical (tests.test_hand_live_equivalence.TestHandLiveEquivalence)`: `AssertionError: '160e0c68...' != 'a6311820...'` so sha checkpoint triển khai với `PROVENANCE_JSON` 2026-09-27 (review A1 #1).
    2. `test_deployed_checkpoint (tests.test_status_privacy.TestStatusDeployed)`: `AssertionError: '160e0c68...' != 'a6311820...'` so sha checkpoint triển khai với hằng PROVENANCE 2026-09-27 (review A1 #2).
    3. `test_js_body_equals_python_offline_body (tests.test_frontend_contract.TestCrossLanguageBody)`: `AssertionError: '160e0c68...' != 'a6311820...'` so sha checkpoint triển khai với `H.deployed_sha256()`.
    4. `test_g_gitignore (tests.test_private_artifacts.TestPrivateArtifacts)`: `AssertionError: 82 != 1` khóa .gitignore diff b337aee HEAD có 82 dòng thêm (do commit fd5ceea viết lại CRLF và thêm 2 dòng phủ định).
    5. `test_reset_segments_and_graphs (tests.test_hand_landmarks_ws.TestReset)`: `AssertionError: [1, 1, 1, 0] != [1, 1, 1, 1]` — test chập chờn đã biết (STATE). Chạy riêng 3 lần (`_work/_plan15_l13/m0_flaky_reset_{1,2,3}.log`): FAIL (0.832s), FAIL (0.813s), OK (0.803s). Không sửa/skip.
  - Skip (1):
    1. `test_u1_summary (tests.test_level1_segment_report.TestVariantsAndU1)`: skipped 'U1 file ... not found' (có sẵn).
  - [Sửa ghi chép ở U1] KHÔNG khớp hoàn toàn mốc của cầu nối: cầu nối đo tại `9bec0ad` (`_work/_bridge_verify/l13_m0/ac1_9bec0ad.log`,
    28 module) `Ran 670` — `FAILED (failures=4, errors=2, skipped=1)`; lần đo M0 này (agy, cad8cdc) failures=5. Chênh lệch = đúng 1 test:
    `test_reset_segments_and_graphs` (chập chờn đã biết) đỏ 3/4 lần chạy ở M0 (lần AC-1 + 2/3 lần chạy riêng), xanh ở lần đo của cầu nối.
    6 test đỏ còn lại (2 ERROR + 4 FAIL) trùng tên với mốc 9bec0ad. Tên lớp ở mục ERROR 1 và FAIL 1 đã sửa (bản 5a32cff ghi
    `TestFingerspellingApi`, `TestLiveEquivalence` — không tồn tại). Khối "Trạng thái → Xong:" bị bản 5a32cff thay hẳn (mất B0…A2b) —
    đã khôi phục từ `git show cad8cdc:docs/plans/15-progress.md`.

## Lần sửa 13 — U1 (2026-10-08, vslt-coder-claude; hoàn thiện WIP agy 7ae0040)
- Phạm vi: `src/inference/level1_display.py` (viết lại), `level1_demo.py` (CHỈ lớp `Hud` + 2 dòng import), `tests/test_level1_display.py`
  (viết lại theo hợp đồng AC-U1–U3), `tests/test_level1_guard.py` (+1 dòng, ngoại lệ E3: thêm `src/inference/level1_display.py` vào
  `PLAN15_FILES`), file này. Không đổi: khung đưa vào MediaPipe, `draw_landmarks`, `display_view`, thứ tự xử lý, logic nhận dạng, app chưa
  gọi `render_to_window` (nối app = U2). `checkpoints/alphabet_best.pt` sha `160e0c68…a8d17899` không đổi.
- Thiết kế (một nguồn): `level1_display.py` = `DisplayLayout` (dataclass frozen, `==` so đủ 9 trường gồm win_w/win_h; lặp ra 7 trường của chữ
  ký trong kế hoạch), `fit_layout`, giao thức DUY NHẤT `PanelBuilder(width, height, scale, n_stats) -> (panel BGR đúng height×width, bước dòng
  thống kê)`, `draw_panel_overlays` (thanh hold + dòng thống kê, hằng có tên = giá trị Hud.compose luôn dùng), `render_to_window`. Panel do
  `level1_demo.Hud` dựng: `Hud` nhận `scale` (mặc định 1.0), font cache theo số px (`_fonts_at`), hằng hình học có tên (`PAD_X`, `PAD_TOP`, …),
  `panel_height(...)`, `panel_builder(text, small)` (cache theo width, height, scale, font px, nội dung, n_stats); `Hud.compose` gọi
  `draw_panel_overlays` (scale 1.0). Không còn `ScalableHud`/`PanelBuilder` lớp chép.
- Sửa lỗi review `docs/reviews/15-l13-u1-bridge.md`:
  1. (CAO) `fit_layout`: tỉ lệ giữ dạng phân số nguyên (w/cam_w hoặc h/(cam_h+panel_h), chọn bằng so sánh số nguyên); làm tròn MỘT lần cho
     content_w và cho TỔNG content_h; cao camera = làm tròn xuống, panel = phần còn lại ⇒ camera + panel == content_h ≤ cửa sổ, x0, y0 ≥ 0.
     Ca `fit_layout(640,480,96,394,333)` nay y0 = 0; `render_to_window` không còn ValueError broadcast (ValueError chỉ khi builder sai giao thức).
  2. (TB) Panel dựng ĐÚNG kích thước ô layout (`height` = `panel_rect[3]`), bước dòng = bước tự nhiên × scale làm tròn xuống ⇒ các dòng chữ
     nằm trong ô (test lưới 200..4000); thanh hold + dòng thống kê vẽ trên ảnh con vùng nội dung ⇒ không pixel nào ra dải đen; dòng thống kê
     đặt theo đáy ô.
  3. (TB) AC-U3 dùng đúng "±2 px mỗi dòng" (`abs(h2 − 2·h1) ≤ 2·số dòng`), không còn `2*n+8`.
  4. (TB) AC-U2 kiểm MỌI pixel ngoài nội dung == 0 (mặt nạ + 4 phía riêng), panel đúng ô và không cắt dòng; AC-U1 lưới kiểm x0,y0 ≥ 0,
     x0+cw ≤ w, y0+ch ≤ h, camera+panel xếp đúng; lưới rộng của probe (3 cỡ camera × panel 40..400 bước 7 × cửa sổ 150..4000 bước 61);
     "cửa sổ = tự nhiên" == `Hud.compose` trên 5 view (list, dict, preview, preview rỗng active_if, rỗng) × 3 small (0, gợi ý góc tay, 4 dòng)
     × 0–3 dòng thống kê × hold 0/0.3/1 × 4 cách cho cửa sổ (None, rect tự nhiên (0,0,…), rect lệch (37,52,…), (w,h)) = 720 so sánh; Hud mới
     == Hud của cad8cdc (git show) trên 180 tổ hợp compose + `_build` 15 ca.
  5. (TB) Không chép Hud: xem "Thiết kế".
  6. (THẤP–TB) Một giao thức `PanelBuilder` (bỏ `inspect.signature`, bỏ nhận ndarray); bỏ font dự phòng 18 và `fit_layout(..., 200, None)`
     (`layout` bắt buộc; cao panel tự nhiên lấy từ `Hud.panel_height`).
  7. (THẤP) `DisplayLayout ==` so đủ trường; test tuple 4 phần tử (x,y,w,h) và 2 phần tử; bỏ import thừa (`Union`, `List`, `inspect`, `re`).
  8. Quy trình: log đỏ, mục này, impact/detect-changes (dưới), level1_display.py vào `PLAN15_FILES`.
- ĐỎ (test cuối của bước chạy trên worktree tạm tại 7ae0040, code agy không sửa) → `_work/_plan15_l13/u1_red.log`:
  `Ran 25 tests` — `FAILED (failures=3, errors=104)` (đếm cả subTest): `test_u1_wide_grid_inside_window` (y0 = −1), `test_u1_layout_equality_
  compares_every_field`, `test_g2_closure_contains_plan15_files_and_shared_modules` (level1_display chưa nằm trong closure); 40 subTest
  `ValueError: could not broadcast ... into shape (0,370,3)` ở `test_u2_never_raises_on_rounding_edge_windows`; còn lại AttributeError
  (`Hud.panel_height` chưa có).
- XANH (code này): `python -m unittest tests.test_level1_display tests.test_level1_demo tests.test_level1_guard tests.test_backend_source_guard`
  → `_work/_plan15_l13/u1_green_main.log`: `Ran 199 tests` — `OK`; `[DoD7-guard] known=9 allowed=36`.
  Toàn bộ 16 module `tests.test_level1_*` + `tests.test_backend_source_guard` → `_work/_plan15_l13/u1_green_level1_all.log`: `Ran 480 tests` —
  `FAILED (failures=1, skipped=1)`; skip = `test_u1_summary` (có sẵn); FAIL = `tests.test_level1_equivalence.TestEquivalenceE3Static.
  test_e3_no_hands_resize_flip_outside_display [src/inference/level1_display.py]`: `[('cv2.resize', 'resize', 'render_to_window')] != []`.
- CẦN PLANNER (không tự sửa): test E3 tĩnh cấm MỌI lời gọi tên `resize` trong `level1_demo.py` + `src/inference/level1_*.py`, nên
  `level1_display.py` (tên do kế hoạch đặt, §10) với `cv2.resize` (bắt buộc ở §2.2 và AC-U2 "vùng camera == cv2.resize(view, …)") làm đỏ E3,
  trong khi AC-U6 đòi E3 xanh KHÔNG sửa và §5.4 không có ngoại lệ cho file này. Đã đỏ từ WIP 7ae0040 (kiểm worktree: E3 tĩnh đỏ ở db5eb0c, xanh
  ở cad8cdc) — U1 không làm tệ hơn. Không lách (alias/đổi tên file/warpAffine). Gợi ý cho planner: ngoại lệ E4 cho phép đúng 1 lời gọi
  `cv2.resize` trong hàm `render_to_window` của `src/inference/level1_display.py` (như `cv2.flip` chỉ trong `display_view`), giữ cấm mọi nơi
  khác; khung MediaPipe vẫn được E3 động (spy) khóa.
- Impact (GitNexus CLI, chỉ mục chậm 2 commit) → `_work/_plan15_l13/u1_impact.log`, `u1_impact_file.log`: `Hud` risk UNKNOWN (0 caller giải
  được, 1 call site bị bỏ); `Hud.compose`, `Hud._build`, `Hud._view_cache_key` (file level1_demo.py) risk CRITICAL, 62 direct; `_fit_committed`
  CRITICAL 136 — CẢNH BÁO: phần lớn là trùng tên (scripts/*, `fingerspelling_compose.compose`, …). Xác nhận bằng grep: caller thật của `Hud` =
  `Level1App.__init__` (`Hud(...)`) và `Level1App._process` (`self.hud.compose`) + test (`tests/test_level1_demo.py` dùng `compose`, `_build(640, v,
  [], 0)`, `_fit_committed(c, a, w)`, `font`, `line_h`, `small_h`, `_panel`, `HINT_*`). Giảm rủi ro: chữ ký cũ giữ nguyên (tham số mới có mặc
  định), test so Hud mới == Hud cad8cdc bit-exact, `tests.test_level1_demo` xanh.
- detect-changes (`node .gitnexus/run.cjs detect-changes --scope all --repo .`) → `_work/_plan15_l13/u1_detect_changes*.log`: risk critical, chủ
  yếu do `README.md` (thay đổi CHƯA commit của người dùng, không thuộc commit này); symbol của U1: `Hud` (level1_demo.py), `DisplayLayout`,
  lớp test của `tests/test_level1_display.py`; `SpaceGestureTracker` chỉ dời dòng.
- Giả định: (a) cao camera làm tròn xuống, panel nhận phần dư (kế hoạch không chốt cách chia); (b) bước dòng scaled = bước tự nhiên × scale làm
  tròn xuống (không `int(round(font×scale)×1.35)`) để panel vừa ô; font = round(font_size × scale) đúng AC-U3; (c) độ dày nét dòng thống kê
  = max(1, round(scale)) (kế hoạch chỉ nói cỡ 0.45 × scale); (d) builder sai kích thước ⇒ ValueError (lỗi lập trình, không cắt/đệm âm thầm).
- 2026-10-08 planner: CẦN PLANNER (E3 resize) đã xử lý — docs/plans/15-lan-sua-13a.md: ngoại lệ E4 (đúng 1 cv2.resize ảnh hiển thị trong render_to_window) + siết bí danh/động; kế tiếp U1a (vslt-coder-claude) → review gộp U1+U1a → U2 (+AC-U6b).

## Lần sửa 13a — U1a (2026-10-09, vslt-coder-claude; `docs/plans/15-lan-sua-13a.md`, ngoại lệ E4)
- Phạm vi: `tests/test_level1_equivalence.py` (xóa đúng 2 dòng: docstring `:16` và `:273` của `ea9c645`; còn lại THÊM), `tests/test_level1_display.py`
  (chỉ thêm), file này. KHÔNG sửa `src/`, `level1_demo.py`, `backend/`, `configs/`. `_calls` không đổi.
- Nội dung: hằng mức module `E4_FILE`, `E4_FUNC`, `E4_RESIZE_CALLS = [("cv2.resize", "resize", "render_to_window")]` (chú thích "ngoại lệ E4 —
  15-lan-sua-13a"); `:273` thành nhánh `resizes == (E4_RESIZE_CALLS if rel == E4_FILE else [])`; hàm thuần `_e4_violations(rel, source)`
  (§3.2 mục 1–4: resize theo `_calls`; `render_to_window` đúng 1 lần ở mức module, không lồng ở mọi file; lời gọi E4 trong khoảng dòng của hàm,
  đúng 2 đối số vị trí, đối số 1 = `Name` tham số thứ nhất, keyword ⊆ {interpolation}; cấm `from cv2 import`, `import cv2 as`, `getattr(cv2, …)`,
  tham chiếu trần `cv2.{resize,flip,warpAffine,warpPerspective,remap,pyrDown,pyrUp}`, gọi `cv2.{warpAffine,warpPerspective,remap,pyrDown,pyrUp}`;
  `level1_display.py`: import gốc ⊆ {__future__, dataclasses, typing, math, cv2, numpy}, không `.process(...)`, không Name/Attribute
  `HandLandmarkSession`/`mediapipe`/`Hands`); lớp mới `TestEquivalenceE4Display` (4 test); lớp mới
  `tests/test_level1_display.py::TestRenderToWindowInputUnchanged` (§3.2 mục 5: nhánh chép — layout tự nhiên `None` và `(640, 480+panel)` —
  và nhánh resize 1920×1080, builder Hud thật + panel đặc; `array_equal(view, bản chép)`, `not np.shares_memory(out, view)`, vùng camera ==
  view / `cv2.resize(view)`, thêm lần chạy với view chỉ-đọc `writeable=False`).
- Impact (GitNexus CLI, chỉ mục làm mới `analyze --index-only` lúc bắt đầu; FTS lỗi, đồ thị OK) → `_work/_plan15_l13/u1a_impact.log`:
  `test_e3_no_hands_resize_flip_outside_display` CRITICAL (70 direct), `render_to_window` CRITICAL (197 direct), `_calls` CRITICAL (1 direct =
  `test_e3_no_hands_resize_flip_outside_display`), `TestEquivalenceE3Static` UNKNOWN. Hai CRITICAL đầu: đích không giải được (type rỗng) ⇒ ghép
  trùng tên với `scripts/*`, `clone/*` (dương tính giả). Xác nhận bằng grep: test do unittest gọi, không mã nào gọi; `_calls` chỉ 2 test E3 dùng
  (không đổi); `render_to_window` không sửa (U1a không đụng `src/`).
- ĐỎ (AC-E4f; lớp test mới viết TRƯỚC, chưa có `_e4_violations`, `:273` chưa sửa) → `_work/_plan15_l13/u1a_red.log`:
  `python -m unittest tests.test_level1_equivalence.TestEquivalenceE3Static tests.test_level1_equivalence.TestEquivalenceE4Display
  tests.test_level1_display.TestRenderToWindowInputUnchanged -v` → `Ran 8 tests` — `FAILED (failures=1, errors=28)`: 27 × `NameError: name
  '_e4_violations' is not defined` (20 ca xấu + 6 file thật + 1 nguồn hợp lệ, đếm subTest), 1 × `NameError: name 'E4_FILE' is not defined`,
  FAIL `test_e3_no_hands_resize_flip_outside_display [src/inference/level1_display.py]` (`[('cv2.resize', 'resize', 'render_to_window')] != []`).
  `TestRenderToWindowInputUnchanged` đã `ok` ở log đỏ (mã U1 vốn không sửa đầu vào — test khóa tính chất, không phải sửa lỗi). Mốc đỏ trước:
  `_work/_plan15_l13/u1_green_level1_all.log` (`Ran 480`, `FAILED (failures=1, skipped=1)`).
- AC-E4c: `test_e4_bad_sources_flagged` — 20 subTest, mỗi ca KHÁC rỗng: 13 ca của hợp đồng (1 resize trong `fit_layout`; 2 hai resize trong
  `render_to_window`; 3 nguồn hợp lệ nhưng `rel = level1_core.py`; 4 `from cv2 import resize as r`; 5 `import cv2 as c`; 6 `f = cv2.resize`;
  7 `getattr(cv2, "resize")`; 8 `render_to_window` lồng trong hàm khác; 9 đối số 1 = `frame`; 10 `dst=`; 11 `cv2.warpAffine`; 12 `import
  mediapipe`; 13 `session.process(x)`) + 7 ca thêm (8b method `render_to_window` trong lớp, cạnh hàm mức module; 9b gán lại `view_bgr` trước
  resize; 10b `**{...}`; 10c 3 đối số vị trí; 11b `warpAffine` ở `level1_core.py`; 11c `pyrDown` ở `level1_demo.py`; 12b `from
  src.inference.hand_live import HandLandmarkSession`). `test_e4_valid_source_passes`: nguồn mô phỏng `render_to_window` hiện tại ⇒ `[]`.
  `test_e4_real_files`: 6 file của `E3_FILES` ⇒ `[]`.
- AC-E4a → `_work/_plan15_l13/u1a_green_equiv_display.log`: `python -m unittest tests.test_level1_equivalence tests.test_level1_display -v` →
  `Ran 35 tests in 180.063s` — `OK` (0 skip); `TestEquivalenceE3Static` 3/3 ok, `TestEquivalenceE4Display` 4/4 ok, `TestEquivalenceE3Spy`
  2/2 ok, E1 chạy đủ.
- AC-E4b → `_work/_plan15_l13/u1a_green_level1_all.log`: `python -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##')
  tests.test_backend_source_guard` → `Ran 485 tests in 1105.600s` — `OK (skipped=1)` (485 = 480 + 5 test mới); `[DoD7-guard] known=9
  allowed=36`; skip = `test_u1_summary` (tên lấy từ log -v của AC-1 dưới; lệnh AC-E4b không -v).
  Lần chạy 1 (giữ log: `_work/_plan15_l13/u1a_green_level1_all_run1_crlf.log`): `Ran 485 tests in 1130.608s` — `FAILED (failures=1,
  skipped=1)`, FAIL `tests.test_level1_gitattributes.TestGitattributesW0.test_w0_ls_files_eol_no_crlf`: bản làm việc của `docs/STATE.md`,
  `docs/plans/15-lan-sua-13.md`, `docs/plans/15-progress.md` là CRLF (`i/lf w/crlf`; ghi lúc 23:01 ngày 08/10 cùng commit planner/orchestrator
  `232c17d`/`99fd058`), nội dung git sạch. Xử lý: đổi CRLF→LF ở cây làm việc rồi `git checkout -- <3 file>` (byte trùng `HEAD`, `git diff`
  rỗng trước và sau; không đổi nội dung theo dõi). Không do U1a. Lưu ý orchestrator: công cụ ghi file trên Windows có thể ghi CRLF cho
  `docs/**/*.md` ⇒ test W0 đỏ; cần ghi LF.
- AC-1 (29 module = 28 module M0 + `tests.test_level1_display`; danh sách `_work/_plan15_l13/u1a_ac1_modules.txt`) →
  `_work/_plan15_l13/u1a_ac1.log`: `Ran 696 tests in 1298.156s` — `FAILED (failures=5, errors=2, skipped=1)`; tập đỏ TRÙNG M0, không đỏ mới:
  ERROR `test_fingerspelling_api.TestRealClipEquivalence.test_real_clips_match_training_evaluation` (`KeyError: 'hauuto_aa_tai_B_001_tail_â'`),
  ERROR `setUpClass (test_fingerspelling_deployed.TestDeployedCheckpointEquivalence)` (`KeyError: 'selected'`), FAIL
  `test_hand_live_equivalence…test_b_bodies_and_responses_identical`, `test_status_privacy…test_deployed_checkpoint`,
  `test_frontend_contract…test_js_body_equals_python_offline_body` (3 × sha `160e0c68…` != `a6311820…`), `test_private_artifacts…test_g_gitignore`
  (`82 != 1`), `test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs` (`[1, 1, 1, 0] != [1, 1, 1, 1]`, chập chờn đã biết). Skip =
  `test_u1_summary`. Luật 3 lần (`_work/_plan15_l13/u1a_flaky_reset_{1,2,3}.log`): FAIL (0.820s), FAIL (0.836s), FAIL (0.875s) — module này không
  import file U1a sửa; không sửa/skip.
- AC-E4d (worktree tạm `_work/_plan15_l13/wt_u1a`: `git worktree add --detach` tại `99fd058` + chép 2 file test của U1a (sha bên dưới), đã xóa
  bằng `git worktree remove` + `prune`; script `_work/_plan15_l13/u1a_mutate.py`; lệnh mỗi đột biến `python -m unittest
  tests.test_level1_equivalence.TestEquivalenceE3Static tests.test_level1_equivalence.TestEquivalenceE4Display -v`; mỗi log mở đầu bằng
  `git diff -- src/` của đột biến):
  - base `u1a_mut_base.log`: `Ran 7 tests` — `OK`.
  - m1 (`cv2.resize` trong `fit_layout`) `u1a_mut_m1.log`: `Ran 7` — `FAILED (failures=2)`: E3 static + `test_e4_real_files` [level1_display.py].
  - m2 (hàm có `cv2.resize` cuối `level1_core.py`) `u1a_mut_m2.log`: `Ran 7` — `FAILED (failures=2)`: E3 static + `test_e4_real_files` [level1_core.py].
  - m3 (resize thứ hai trong `render_to_window`) `u1a_mut_m3.log`: `Ran 7` — `FAILED (failures=2)`: E3 static + `test_e4_real_files` [level1_display.py].
  - m4 (`import mediapipe` trong `level1_display.py`) `u1a_mut_m4.log`: `Ran 7` — `FAILED (failures=1)`: `test_e4_real_files` [level1_display.py].
  - sha256 file test dùng trong worktree (= file của commit U1a): `tests/test_level1_equivalence.py`
    `d398fc95a5bb8714c6459e7361877e84b375b948f2fe5a1c577242eec25d8b61`, `tests/test_level1_display.py`
    `3e28b1528ffebc706efa029ec8a1ea9d6eb11329852754ad87568b4b2eb0504a`.
- AC-E4e: `git diff --stat ea9c645..HEAD -- src/ level1_demo.py backend/ configs/` rỗng (và rỗng ở cây làm việc); `sha256(checkpoints/alphabet_best.pt)`
  = `160e0c6825e365ba3d5481e2fd4d18423cf501c655aec618a453c524d8a17899`.
- AC-0 (bản sửa 13a): `git diff --numstat ea9c645 -- tests/test_level1_equivalence.py` (trước commit) = `211 2`; dòng `-` chỉ ở `:16` (docstring)
  và `:273`. `tests/test_level1_display.py` `44 0`.
- detect-changes (`node .gitnexus/run.cjs detect-changes --scope all --repo .`) → `_work/_plan15_l13/u1a_detect_changes.log`: risk critical, do
  `README.md` (thay đổi CHƯA commit của người dùng, không thuộc commit này); symbol của U1a: `TestEquivalenceE3Static`, `TestEquivalenceE3Spy`
  (chỉ dời dòng) trong `tests/test_level1_equivalence.py`; không symbol `src/`.
- Giả định: (a) "worktree tại commit U1a" làm bằng worktree tại `99fd058` + chép 2 file test (sha trùng file commit), vì kế hoạch đòi 1 commit
  gồm cả mục này; (b) siết thêm ngoài danh sách tối thiểu (không nới): tham số thứ nhất của `render_to_window` không được gán lại; cấm
  `__import__(...)` trong `level1_display.py`; import tương đối trong `level1_display.py` bị coi là ngoài danh sách; (c) `render_to_window`
  mức module ở file KHÁC không bị cấm (kế hoạch chỉ cấm lồng) — resize ở đó vẫn bị cấm.
- Sau khi ghi mục này: 2 module test đọc file này `python -m unittest tests.test_level1_demo tests.test_level1_rearm_check` →
  `_work/_plan15_l13/u1a_progress_check.log`: `Ran 186 tests in 660.087s` — `OK`; `tests.test_level1_gitattributes` → `OK`.

## U2a — test TB-1 (AC-U7) + đột biến m9–m12 (AC-U7m) (2026-10-09)
- Mục tiêu: Khóa lỗ hổng TB-1 bằng test thanh hold và dòng thống kê ở scale ≠ 1 (AC-U7), xác minh bằng 4 đột biến m9–m12 phải đỏ trong worktree tạm (AC-U7m). Không sửa `src/`, không sửa `level1_demo.py`.
- File sửa: `tests/test_level1_display.py` (thêm lớp `TestU2OverlaysScaled` gồm 8 test H1–H4, S1–S4; numstat `117 0`, 0 xóa), `docs/plans/15-progress.md`.
- AC-U7:
  - Lệnh: `python -m unittest tests.test_level1_display -v` → `_work/_plan15_l13/u2a_green_display.log`: `Ran 30 tests in 21.533s` — `OK` (22 test có sẵn + 8 test mới).
  - Chi tiết 8 test của `TestU2OverlaysScaled` (cam 640×480, panel 200, view (90,90,90), panel builder trả nền BG (40,40,40), cửa sổ (1920, 1080) s ≈ 1.588 và (1280, 1360) s = 2.0):
    - H1 (`test_u7_h1_hold_full_scaled`): hold 1.0, stats=[]: mọi pixel `canvas[py : py + scaled_px(3, s), px : px + cw] == HOLD_BAR_BGR`.
    - H2 (`test_u7_h2_hold_half_scaled`): hold 0.5: mọi pixel `canvas[py : py + scaled_px(3, s), px : px + int(cw * 0.5)] == HOLD_BAR_BGR`; hàng `py`, cột `[px + int(cw * 0.5) + 2, px + cw)` không có pixel `HOLD_BAR_BGR`.
    - H3 (`test_u7_h3_hold_height_exact_scaled`): hold 1.0: hàng `py + scaled_px(3, s) + 1` không có pixel `HOLD_BAR_BGR` (chiều cao thanh co giãn đúng, không dày hơn).
    - H4 (`test_u7_h4_hold_zero_no_bar`): hold 0: không pixel nào của `canvas == HOLD_BAR_BGR`.
    - S1 (`test_u7_s1_stats_bottom_half_and_color`): hold 0, stats=["fps 30.0 | hud 1.2ms"]: tập D khác BG có |D| > 0 (1680 pixel ở 1080p, 2542 ở 1280×1360); mọi hàng của D ≥ `py + ph // 2`; có pixel của D với khoảng cách kênh tới `STATS_BGR` ≤ 8.
    - S2 (`test_u7_s2_stats_empty_no_diff`): hold 0, stats=[]: |D| == 0.
    - S3 (`test_u7_s3_stats_font_height_scaled`): chiều cao chữ: span(1280×1360, s = 2) = 29, span(tự nhiên, s = 1) = 15; ratio = 1.9333 ∈ [1.6, 2.4].
    - S4 (`test_u7_s4_outside_pixels_zero`): hold 1.0 + stats S1: mọi pixel ngoài vùng nội dung == 0.
- AC-U7m (đột biến trên worktree tạm `_work/_plan15_l13/wt_u2a` tại commit 95598eb + chép `tests/test_level1_display.py` sha256 `a7f9922f912dc737d9c211c5979fa94e1a10af748d043b0620bfaaeb902d1144`; chạy qua `_work/_plan15_l13/u2a_mutate.py`; đã xóa worktree bằng `git worktree remove` + `prune`):
  - base (`u2a_mut_base.log`): `Ran 30 tests in 21.454s` — `OK`.
  - m9 (`:163` chỉ gọi `draw_panel_overlays` khi `layout.scale == 1.0`) `u2a_mut_m9.log`: `Ran 30 tests in 21.666s` — `FAILED (failures=6, errors=1)`.
  - m10 (chiều cao thanh hold dùng `HOLD_BAR_HEIGHT` thay `scaled_px(HOLD_BAR_HEIGHT, scale)`) `u2a_mut_m10.log`: `Ran 30 tests in 21.653s` — `FAILED (failures=2)`.
  - m11 (cỡ chữ thống kê `STATS_FONT_SCALE` thay `STATS_FONT_SCALE * scale`) `u2a_mut_m11.log`: `Ran 30 tests in 21.599s` — `FAILED (failures=1)`.
  - m12 (`:163` truyền `1.0` thay `layout.scale`) `u2a_mut_m12.log`: `Ran 30 tests in 21.600s` — `FAILED (failures=3)`.
  - Toàn bộ 4 đột biến đều ĐỎ đúng yêu cầu, base XANH. Bằng chứng bắt lỗi hoàn tất.
- AC-U2P (toàn bộ suite Level 1):
  - Lệnh: `python -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard` → `_work/_plan15_l13/u2a_green_level1_all.log`: `Ran 493 tests in 493.358s` — `OK (skipped=1)` (493 = 485 của U1a + 8 test mới của AC-U7); `[DoD7-guard] known=9 allowed=36`; `[scope] serving=45 main=61`.
- AC-U9:
  - `git diff d1a8308..HEAD -- level1_demo.py scripts/level1_display_cost.py src/` = rỗng.
  - `git diff --stat d1a8308..HEAD -- src/` = rỗng.
  - `sha256(checkpoints/alphabet_best.pt)` = `160e0c6825e365ba3d5481e2fd4d18423cf501c655aec618a453c524d8a17899`.
- numstat: `git diff --numstat d1a8308..HEAD` đối với `tests/test_level1_display.py` là `117 0` (0 dòng xóa).

> LẦN SỬA 13b (2026-10-09): xem docs/plans/15-lan-sua-13b.md — U2 chia U2a (agy, test TB-1) → U2b (Claude, nối cửa sổ + AC-U6b) → U2c (agy, phím f/cờ/LRU) → U2d (agy, đo DC1); X1 chẩn đoán test_reset trước V1.

## U2b — nối cửa sổ co giãn vào app (AC-U4, AC-U4b, AC-U6b) (2026-10-09, vslt-coder-claude)
- Kế hoạch: `docs/plans/15-lan-sua-13b.md` §4 hàng U2b, §5. Mốc HEAD `db402c1`. Không sửa `src/` (AC-U9).
- File sửa: `level1_demo.py` (numstat `29 3`), `tests/test_level1_demo.py` (`185 0`), `tests/test_level1_equivalence.py` (`89 0` từ
  `db402c1`; `300 2` từ `ea9c645` — 2 dòng `-` vẫn là `:16`/`:273` của U1a), `docs/plans/15-progress.md`.
- Mã (`level1_demo.py`, chỉ phần hiển thị): `namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)` (thay `WINDOW_AUTOSIZE`); hàm mới
  `Level1App._window_image` thay lời gọi `self.hud.compose(...)` trong `_process` (cùng chặng `hud`): khung hiển thị đầu tiên gọi
  `cv2.resizeWindow(WINDOW_NAME, w, h + panel_h)` một lần (bọc `try/except (cv2.error, AttributeError)`; kích thước khởi đầu = tự nhiên theo §2.2
  gốc — cửa sổ WINDOW_NORMAL thật mở ở 304×281, đo bằng probe cv2 5.0.0 local); mỗi khung `cv2.getWindowImageRect` bọc `try/except (cv2.error,
  AttributeError)` → `fit_layout(w, h, panel_h, rect)`; layout == `fit_layout(w, h, panel_h)` (rect lỗi/không hợp lệ HOẶC đúng kích thước tự nhiên)
  ⇒ `Hud.compose` (ảnh cũ); ngược lại ⇒ `render_to_window(view, hud.panel_builder(...), stats, progress, layout)`. `panel_h =
  Hud.panel_height(text, small, len(stats))` (= chiều cao panel của `Hud.compose`). Thuộc tính mới `self.window_sized` trong `__init__`. Không đổi
  `frame`/`frame_mp`/`process`/`draw_landmarks`/`display_view`/thứ tự xử lý/tập chặng.
- Test mới (THÊM, không sửa test cũ):
  - `tests/test_level1_demo.py::TestScaledWindowU2b` (4 test, clip D2, recorder `_ScaledWindowRecorder` kế thừa `_WindowRecorder` + ghi
    `namedWindow`/`resizeWindow`, `getWindowImageRect` vá): `test_u4_window_1920x1080_every_image_scaled` (AC-U4: `--pace realtime`, rect
    `(0, 0, 1920, 1080)` ⇒ mọi ảnh `imshow` (1080, 1920, 3), số ảnh = số khung xử lý, `render_to_window` gọi mỗi khung, mọi chặng khung đủ n);
    `test_u4b_window_created_resizable` (AC-U4b: cờ `namedWindow` chứa `WINDOW_NORMAL` — vì `cv2.WINDOW_NORMAL == 0`, kiểm `flags & WINDOW_NORMAL ==
    WINDOW_NORMAL` VÀ bit `WINDOW_AUTOSIZE` (=1) tắt; cả 4 lần chạy); `test_u4b_fallback_is_natural_hud_compose` (AC-U4b (a) rect ném `cv2.error`,
    (b) `del cv2.getWindowImageRect` rồi khôi phục trong `finally` (AttributeError), (c) `(-1, -1, -1, -1)`: chạy hết clip không ngoại lệ, mỗi ảnh
    `imshow` shape tự nhiên và `array_equal` ảnh Hud.compose CÙNG khung, `render_to_window` 0 lần); `test_u2b_window_starts_at_natural_size`
    (`resizeWindow` đúng 1 lần với kích thước tự nhiên của khung đầu).
  - Cách so AC-U4b: recorder TÁCH được đầu vào — bọc `app.hud.compose` để chép (view.copy(), deepcopy text, small, hold, stats) của từng khung; ở
    `imshow`, một `Hud` riêng (cùng font_path/font_size) compose lại từ bản chép và so `array_equal` với ảnh hiển thị (không so với lần chạy (a)).
  - `tests/test_level1_equivalence.py::TestEquivalenceU6bWindow` (AC-U6b, 2 test, cùng clip/`_MISSING`/`SKIP_REASON` của E3 spy, `RecordingSession` +
    `SpyReader` qua `run_app`, recorder `_WindowCallsU6b` rect `(0, 0, 1920, 1080)`): `test_u6b_window_frame_is_object_read` (chế độ cửa sổ replay
    `gui`: số khung vào `process` == số khung đọc, mọi khung `is` đối tượng reader) và `test_u6b_window_paced_frame_is_object_read` (`--pace realtime`:
    luật thứ tự như `test_e3_paced_frame_is_object_read`); cả hai: số ảnh `imshow` = số khung xử lý, có và chỉ có ảnh (1080, 1920, 3).
- Log đỏ trước (AC-U2P, cây làm việc chính, test mới trên mã chưa sửa): `_work/_plan15_l13/u2b_red.log` (mtime 09:35:54) `python -m unittest
  tests.test_level1_demo.TestScaledWindowU2b tests.test_level1_equivalence.TestEquivalenceU6bWindow -v` → `Ran 6 tests in 31.267s` — `FAILED
  (failures=11)` (u4: shape (643, 640, 3) != (1080, 1920, 3); u4b cờ: `1 != 0` ×4; resizeWindow: `[]` ×4; u6b: không có ảnh (1080, 1920, 3) ×2;
  `test_u4b_fallback_is_natural_hud_compose` xanh ngay vì mã cũ chính là Hud.compose).
- Log xanh (mtime đều sau log đỏ):
  - `u2b_green_new.log` (09:37:44) cùng lệnh → `Ran 6 tests in 31.004s` — `OK`.
  - `u2b_green_equiv_display.log` (09:41:21) `python -m unittest tests.test_level1_display tests.test_level1_equivalence -v` → `Ran 45 tests in
    192.175s` — `OK`; `TestEquivalenceE3Static` 3, `TestEquivalenceE4Display` 4, `TestEquivalenceE3Spy` 2, `TestEquivalenceU6bWindow` 2, E1 4 —
    không skip.
  - `u2b_green_level1_all.log` `python -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard` →
    `Ran 499 tests in 898.734s` — `OK (skipped=1)` (499 = 493 của U2a + 6 mới); `[DoD7-guard] known=9 allowed=36`. `TestLatencyAcL` và
    `test_m3_window_shows_camera_frame` (recorder cũ, không vá `getWindowImageRect`/`resizeWindow` ⇒ cv2 thật ném `cv2.error` "NULL window" ⇒ dự phòng
    Hud.compose) xanh không sửa (AC-U4).
  - AC-1 (29 module, `_work/_plan15_l13/u1a_ac1_modules.txt`) → `u2b_ac1.log`: `Ran 710 tests in 1357.230s` — `FAILED (failures=5, errors=2,
    skipped=1)`; tập đỏ TRÙNG M0/U1a: 2 ERROR (`test_fingerspelling_api…test_real_clips_match_training_evaluation`, `setUpClass
    (test_fingerspelling_deployed.TestDeployedCheckpointEquivalence)`), 4 FAIL review A1/gitignore (`test_hand_live_equivalence…test_b_…`,
    `test_status_privacy…test_deployed_checkpoint`, `test_frontend_contract…test_js_body_equals_python_offline_body`, `test_private_artifacts…test_g_gitignore`)
    + `test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs` (chập chờn đã biết, X1 xử lý trước V1). Skip = `test_u1_summary`.
- AC-U9: `git diff d1a8308 -- level1_demo.py scripts/level1_display_cost.py src/ | grep -E '^\+' | grep -cE 'vars\(|__dict__|cv2\.dnn|getRectSubPix|__import__|importlib|warp|remap|pyr(Up|Down)'`
  → `0`; `git diff --stat d1a8308 -- src/` rỗng. `sha256(checkpoints/alphabet_best.pt)` = `160e0c6825e365ba3d5481e2fd4d18423cf501c655aec618a453c524d8a17899`.
- GitNexus: `analyze --index-only` (log `u2b_gitnexus_analyze.log`). `impact _process` → CRITICAL 120 symbol nhưng là DƯƠNG TÍNH GIẢ do trùng tên
  (`_process` của `scripts/level1_segment_report.py`, `simulate_cslr_streaming.py`, …); `impact run` → ambiguous 17 ứng viên (UNKNOWN); lọc
  `--file level1_demo.py`/`--uid` không tìm thấy method. Xác nhận bằng text: `Level1App._process` chỉ được gọi ở `Level1App.run` (2 chỗ);
  `Level1App(` chỉ ở `level1_demo.py` (`main`) và `tests/test_level1_demo.py` (+ lớp con `SpyApp` của `tests/test_level1_equivalence.py`).
  `_window_image` mới (UNKNOWN). Log `u2b_impact_*.log`. detect-changes (`u2b_detect_changes.log`): risk critical do `README.md` (thay đổi CHƯA
  commit của người dùng, không thuộc commit này); symbol của U2b: `Level1App` (`level1_demo.py`), không flow nào bị đánh dấu do `Level1App`.
- Giả định: (a) `resizeWindow` lần đầu là phần "kích thước khởi đầu = tự nhiên" của §2.2 gốc (không AC riêng; có test riêng). Ghi cho U2c: nếu
  `--fullscreen` đặt `setWindowProperty` lúc mở, `resizeWindow` ở khung đầu có thể tác động cửa sổ toàn màn hình — U2c cần kiểm thứ tự (sửa trong
  `_window_image`, không chạm dòng khung; AC-U9b). (b) Rect đúng bằng kích thước tự nhiên cũng đi `Hud.compose` (ảnh bằng hệt `render_to_window` ở
  layout tự nhiên theo AC-U2, rẻ hơn). (c) Panel đổi chiều cao (số dòng nhỏ thay đổi) khi cửa sổ giữ nguyên ⇒ `fit_layout` co nội dung (dải đen
  một cặp cạnh), không tự đổi kích thước cửa sổ như WINDOW_AUTOSIZE cũ. (d) Chế độ cửa sổ của AC-U6b: chạy cả `gui` (đếm khung bằng nhau) lẫn
  `--pace realtime` (luật thứ tự).

## Lần sửa 13b — U2c (2026-10-09)
- Mục tiêu: Phím `f` toàn màn hình (sự kiện `fullscreen`), cờ `--fullscreen`, `--display-mirror` (`BooleanOptionalAction`), cache font LRU (AC-U8), gợi ý phím (A); giữ nguyên đường khung MediaPipe và kiểm E3/E4.
- AC-U6:
  - Phím `f`: `KEY_FULLSCREEN = ord("f")`, bật/tắt toàn màn hình qua `cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, ...)`. Bọc `try/except (cv2.error, AttributeError)` không làm app dừng; ghi sự kiện `{"event": "fullscreen", "on": bool}` vào `self.events` (như pause/resume).
  - `--fullscreen`: cờ `store_true`, mặc định False, mở ở chế độ toàn màn hình, gọi `setWindowProperty` đúng 1 lần lúc mở cửa sổ trong `Level1App.run` (ngay sau `namedWindow`, khi `self.display`). KHÔNG đưa vào `DEFAULT_DEMO_ARGV` (preset).
  - `--display-mirror`: chuyển sang `argparse.BooleanOptionalAction`, mặc định parser False, preset giữ `--display-mirror`. `[*DEFAULT_DEMO_ARGV]` parse ra `display_mirror=True`, `fullscreen=False`; `[*DEFAULT_DEMO_ARGV, "--no-display-mirror"]` parse ra `display_mirror=False`.
  - Thứ tự resizeWindow (U2b) với `--fullscreen`: khi `self.fullscreen` đang bật, `_window_image` bỏ qua `resizeWindow` và giữ `window_sized = False`; khi thoát toàn màn hình, khung tiếp theo mới gọi `resizeWindow` một lần về kích thước tự nhiên.
- AC-U8 (LRU font cache):
  - Tên hàm dựng font mà Hud dùng: `ImageFont.truetype` (được gọi trong `Hud._fonts_at`, `level1_demo.py`).
  - `Hud._fonts` chuyển thành `collections.OrderedDict`, khởi tạo với cỡ mặc định. Khi truy vấn trong `Hud._fonts_at`: nếu trúng cache thì gọi `move_to_end`; nếu chưa có thì dựng qua `ImageFont.truetype`, lưu vào dict và `popitem(last=False)` khi kích thước vượt quá 8.
  - Test `TestHudFontLruU2c.test_lru_cache_eviction_and_retention`: gọi 20 cỡ font px khác nhau liên tiếp; gọi lại cỡ thứ 20 (vừa dùng) không dựng font mới; gọi lại cỡ thứ 1 (đã bị đẩy ra bởi LRU) thì dựng lại; số cỡ trong cache luôn <= 8 tại mọi thời điểm.
- Gợi ý phím (A):
  - Ban đầu thử nghiệm chèn `' | f toàn màn hình'` vào dòng phím trong `Level1App._hud_lines` (`small.append(...)`). Khi chạy test, 5 test hồi quy so sánh tương đương với các commit tham chiếu lịch sử (`app_module_at(...)`) bị FAIL: `TestDetectionHudM3.test_m3_hud_line_only_when_not_default` (2 subtests), `TestGestureSpaceFlagsS3.test_9d_no_gesture_space_same_as_before` (2 subtests mode motion_pose & classifier), và `TestHudClassifierW2.test_6d_motion_pose_hud_image_identical_to_before` do các test này ghim cứng dòng `small` khớp tuyệt đối với mã nguồn commit cũ.
  - Theo luật thiết kế §2.2 gốc và hướng dẫn kế hoạch: "Nếu sau khi chạy test thật sự có test ghim dòng đó, hoàn tác (A) và ghi lý do vào progress (khi đó tiêu đề cửa sổ chấp nhận được)".
  - Hoàn tác thêm gợi ý vào `small.append`, đặt gợi ý vào tiêu đề cửa sổ: `WINDOW_NAME = "VSLT Level 1 (f: toàn màn hình)"`. Cập nhật `test_key_hint_and_docstring` kiểm tra docstring có `'f fullscreen'` và `WINDOW_NAME` có `'f: toàn màn hình'`.
- Kiểm thử và log thực tế (AC-U2P):
  - Log đỏ viết trước: `_work/_plan15_l13/u2c_red.log` (mtime 11:21:04, cũ hơn các log green): `python -m unittest tests.test_level1_demo.TestFullscreenU2c tests.test_level1_demo.TestHudFontLruU2c tests.test_level1_demo.TestParserU2c -v` → `Ran 8 tests in 0.082s` — `FAILED (failures=3, errors=5)`.
  - Log xanh ca mới: `_work/_plan15_l13/u2c_green_new.log` (mtime 12:58:56) → `Ran 8 tests in 21.356s` — `OK`.
  - Log xanh tương đương & hiển thị: `_work/_plan15_l13/u2c_green_equiv_display.log` (mtime 13:03:04) `python -m unittest tests.test_level1_display tests.test_level1_equivalence -v` → `Ran 45 tests in 205.915s` — `OK`.
  - Log xanh toàn bộ level 1: `_work/_plan15_l13/u2c_green_level1_all.log` (mtime 12:10) `python -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard` → `Ran 507 tests in 873.494s` — `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`.
- Bất biến diff (AC-U9, AC-U9b):
  - `git diff b0cbcf1 -- level1_demo.py | grep -E '^[-+]' | grep -cE 'process\(|frame_mp|draw_landmarks|display_view|HandLandmarkSession|\.read\('` = 0.
  - `git diff d1a8308 -- level1_demo.py scripts/level1_display_cost.py src/ | grep -E '^\+' | grep -cE 'vars\(|__dict__|cv2\.dnn|getRectSubPix|__import__|importlib|warp|remap|pyr(Up|Down)'` = 0.
  - `git diff --stat d1a8308 -- src/` rỗng (src/ hoàn toàn không thay đổi).

  - Orchestrator chạy lại toàn bộ level 1 SAU lần sửa code cuối (12:56): `_work/_plan15_l13/u2c_orch_level1_all.log` → `Ran 507` — `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` (log 12:10 ở trên có trước lần sửa cuối). agy lần 2 hết giờ 40' (không có STATUS); agy-guard BLOCK 15-progress.md là báo nhầm (file đã là WIP U2c của agy lần 1, ghi ở STATE 5fd07ae); orchestrator commit hộ.
- Sửa vòng 1 (TB-1, review `docs/reviews/15-l13-u2c-review.md`; quyết định người dùng 2026-10-09 14:07): `WINDOW_NAME = "VSLT Level 1 (f: toan man hinh)"` (ASCII, cv2 backend WIN32 hiện sai mã chữ có dấu). Test MỚI `test_key_hint_and_docstring` kiểm `'f: toan man hinh'` + `WINDOW_NAME.isascii()`; không sửa test cũ.
  - Đỏ (test đổi, mã chưa đổi): `_work/_plan15_l13/u2c_fix_red.log` `.venv/Scripts/python -m unittest tests.test_level1_demo.TestFullscreenU2c tests.test_level1_demo.TestHudFontLruU2c tests.test_level1_demo.TestParserU2c` → `Ran 8` — `FAILED (failures=1)`. Xanh cùng lệnh: `u2c_fix_green.log` → `Ran 8` — `OK`.
  - `u2c_fix_green_extra.log`: `tests.test_level1_display tests.test_level1_equivalence tests.test_level1_demo.TestScaledWindowU2b tests.test_level1_demo.TestLatencyAcL` → `Ran 53` — `OK`. `grep -rn "WINDOW_NAME\|VSLT Level 1" --include=*.py level1_demo.py tests/ scripts/`: mọi chỗ dùng hằng `WINDOW_NAME`, không test nào ghim chuỗi cũ.
  - Tiêu đề thật (Win32 `GetWindowTextW`, `_work/_plan15_l13/u2c_fix_title_probe.log`): `'VSLT Level 1 (f: toan man hinh)'`, khớp. AC-U9 = 0, AC-U9b = 0 (lệnh như trên).

## Lần sửa 13b — U2d (2026-10-09)
- Mục tiêu: `scripts/level1_display_cost.py` + `tests/test_level1_display_cost.py` đo chi phí hiển thị Level 1 và kiểm tra cổng DC1 (AC-U5); commit code sạch để cầu nối chạy lệnh đo độc lập và commit JSON riêng.
- Thiết kế script `scripts/level1_display_cost.py`:
  - Hàm thuần:
    - `percentile(values, q)`: phân vị nội suy tuyến tính numpy.
    - `summarize_frame_total(values)`: trả `{"n", "p50", "p90"}`.
    - `compute_ratio(p50_natural, p50_1080)`: `p50_1080 / p50_natural`.
    - `dc1_gate(ratio, threshold=1.25)`: trả `{"name": "DC1", "threshold": 1.25, "pass": ratio <= threshold}` (biên: 1.25 => pass, 1.2501 => fail).
    - `build_report(command, commit, clip, natural, p1080, py_version, cv2_version, code_dirty)`: tạo dictionary báo cáo đủ 11 khóa, gồm `natural` (`n_frames`, `p50_ms`, `p90_ms`, `path`), `window_1080p`, `ratio_p50`, `gate`, `note` ("imshow vá, không cửa sổ thật; lần \"natural\" đo đường Hud.compose cũ vì rect bằng kích thước tự nhiên; không đo chi phí vẽ cửa sổ HĐH"), `python`, `cv2`.
  - Bộ ghi `_DisplayCostRecorder` (tự định nghĩa trong script, không import từ tests/):
    - `imshow`: ghi shape vào danh sách và cập nhật `last_shape`.
    - `waitKey`: trả `-1`.
    - `getWindowProperty`: trả `1.0`.
    - `resizeWindow`: lưu `natural_size = (w, h)` khi app gọi ở khung đầu.
    - `getWindowImageRect`:
      - Lần 1 'natural': trả kích thước tự nhiên `(0, 0, w, h)` (lấy từ `last_shape` nếu đã có imshow, hoặc `natural_size` từ `resizeWindow` khung đầu; mặc định `(0, 0, 640, 643)` cho clip D2) để app đi đúng đường `Hud.compose` cũ (không qua `render_to_window`).
      - Lần 2: trả `(0, 0, 1920, 1080)` để app đi đường `render_to_window`.
  - Hàm đo `measure(rect)`: chạy app cùng tiến trình trên clip D2 `--pace realtime`, vá `imshow`, `waitKey`, `getWindowProperty`, `namedWindow`, `destroyAllWindows`, `resizeWindow`, `getWindowImageRect` bằng `mock.patch.multiple`, chdir về gốc repo, chạy `app.run()`, thu thập chuỗi thời gian `app.times.values('frame_total')`.
  - CLI: đối số `--out PATH` (bắt buộc), tạo thư mục cha; in dòng `DC1 pass=... ratio=...`; mã thoát luôn là 0 (kết quả pass/fail lưu trong JSON).
  - Không chạy đo thật và không tạo file `reports/level1_realtime_2026-10-08/display_cost.json` ở bước coder (cầu nối sẽ chạy lệnh đo tại commit sạch theo quy trình).
- Test `tests/test_level1_display_cost.py`:
  - Hoàn toàn dùng chuỗi tổng hợp có kiểm soát ("chuỗi tạo có kiểm soát để kiểm logic"), không cần video thật, chạy nhanh (< 1s).
  - Kiểm thử đầy đủ: `percentile`, `summarize_frame_total`, `compute_ratio`, `dc1_gate` với biên 1.25 / 1.2501, `build_report` đủ khóa và đúng nội dung note, logic `_DisplayCostRecorder`, CLI tạo file JSON và in đúng stdout khi vá hàm `measure`.
- Nhật ký kiểm thử thực tế (AC-U2P):
  - Log đỏ viết trước (TDD): `_work/_plan15_l13/u2d_red.log` (mtime 14:39:38, khi chưa có script) `python -m unittest tests.test_level1_display_cost` → `Ran 1 test in 0.000s` — `FAILED (errors=1)` (`ImportError: cannot import name 'level1_display_cost' from 'scripts'`).
  - Log xanh sau khi viết script (mtime lớn hơn red):
    - `_work/_plan15_l13/u2d_green_cost.log` (mtime 14:40:42) `python -m unittest tests.test_level1_display_cost` → `Ran 8 tests in 0.236s` — `OK`.
    - `_work/_plan15_l13/u2d_green_display.log` (mtime 14:41:34) `python -m unittest tests.test_level1_display_cost tests.test_level1_display` → `Ran 38 tests in 22.801s` — `OK`.
- Bất biến phạm vi và an toàn (AC-U9, AC-U9b):
  - `git diff d1a8308..HEAD -- level1_demo.py scripts/level1_display_cost.py src/ | grep -E '^\+' | grep -cE 'vars\(|__dict__|cv2\.dnn|getRectSubPix|__import__|importlib|warp|remap|pyr(Up|Down)'` = 0.
  - `git diff --stat d1a8308..HEAD -- src/` rỗng (src/ hoàn toàn không bị sửa).
  - `level1_demo.py`, các file test có sẵn, file người dùng (`README.md`, 3 file ` D`) hoàn toàn không bị chạm.

> LẦN SỬA 13c (2026-10-09): xem docs/plans/15-lan-sua-13c.md — C1 (Claude: DC1 fail-closed, path_counts, mã thoát, đường dẫn tương đối) → C2 (cầu nối: đo 3 lần, commit lần 1) → review U2d v2 → XW (cầu nối: X1 + thăm dò cửa sổ thật) → T1 (agy: test overlay chính xác) → T2 (agy: test _window_image/f/LRU) → G1; VU người dùng không chặn; câu Giới hạn R2 ở §8.

## Lần sửa 13c — C1 (2026-10-09, vslt-coder-claude; `docs/plans/15-lan-sua-13c.md` §3.1, §4 hàng C1, AC-C1)
- Sửa `scripts/level1_display_cost.py` (gate DC1 giữ nguyên: ngưỡng 1.25, ratio p50 `frame_total` 1080p / tự nhiên):
  - TB-1 (fail-closed): `compute_ratio` ném `ValueError` khi p50 không hữu hạn hoặc ≤ 0; `dc1_gate(None|nan)` ⇒ `pass false` + `reason`. `build_report` kiểm hợp lệ TRƯỚC gate (`validate_run`): `n_frames ≥ MIN_FRAMES = 10`, p50 hữu hạn > 0, tổng `path_counts` = `n_imshow` = `n_frames`; vi phạm ⇒ `gate.pass false`, `gate.reason` ghi lý do; `ratio_p50 null` khi p50 không hợp lệ. JSON có `min_frames`.
  - TB-2: bỏ khóa `path` hard-code. `measure(rect, clip, app_module=None)` trả `frame_total`/`hud`/`mediapipe` (từ `app.times.values`), `n_imshow`, `path_counts`; đếm bằng `mock.patch.object(app_module.Hud, "compose", …)` và `mock.patch.object(app_module, "render_to_window", …)` bọc hàm gốc (giá trị trả về đi tiếp tới `imshow`). Hàm mới `summarize_run`; JSON mỗi lần đo có `n_imshow`, `path_counts`, `stage_p50_ms {hud, mediapipe}`; `info {hud_p50_delta_ms, in_gate: false}`. Note bỏ câu "natural đo đường Hud.compose", thêm "path_counts".
  - THẤP-4: `--clip` mặc định `None` (⇒ `ROOT/CLIP`), tương đối thì `abspath` theo cwd người gọi trước mọi `chdir`; clip không tồn tại ⇒ mã 2, không ghi JSON, không gọi `measure`.
  - THẤP-5: mã thoát 0 hợp lệ + pass, 1 hợp lệ + trượt, 2 đối số sai / thiếu clip, 3 dữ liệu không hợp lệ (vẫn ghi JSON); ghi ở docstring module.
  - THẤP-6: `build_command`: trình thông dịch trong ROOT ⇒ relpath posix, ngoài ⇒ basename; đối số đường dẫn tuyệt đối trong ROOT ⇒ relpath posix. `clip` trong JSON qua `display_path` (trong ROOT ⇒ relpath posix, ngoài ⇒ abspath).
  - `_DisplayCostRecorder` không đổi (test THẤP-7 khóa hành vi rect cố định).
- Test `tests/test_level1_display_cost.py` (8 → 30 test): dòng xóa chỉ ở các vị trí E-13c cho phép (`:53`; input `:77-78`, `:156-164`; `:110`, `:117`; `:192-219` đổi thành `test_cli_exit_one_when_gate_fails`). Thêm: `TestBuildReportValidityC1` (n=0 natural/1080p/cả hai, n=9, tổng path_counts ≠ n_imshow, n_imshow ≠ n_frames, thiếu counts, p50 nan/inf, hợp lệ n=10 ratio 1.2 pass, ratio 1.3 fail reason None, summarize_run), recorder đổi cao panel (THẤP-7, dùng `fit_layout` thật), `TestMeasureCountsC1` (module app giả: compose 3 + render_to_window 2, `is` ảnh gốc, list thời gian, gỡ vá, cwd), CLI mã 1/3/2, `--clip` tương đối theo cwd tạm, clip trong ROOT ⇒ `"scripts/level1_display_cost.py"` + JSON/command không chứa ROOT, `build_command`. Thêm `setUp` cho `TestDisplayCostCli`: vá `CLIP` thành file có sẵn của repo (measure bị vá nên clip không được đọc; test không cần dữ liệu D2).
- Log (`_work/_plan15_l13/`, mtime chép bằng `stat -c '%y'`):
  - Đỏ (test mới, mã cũ) `l13c_c1_red.log` (2026-10-09 15:35:05.624557000 +0700): `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_display_cost -v` → `Ran 30` — `FAILED (failures=13, errors=18)`.
  - Xanh cùng lệnh `l13c_c1_green_cost.log` (15:37:32.589824500): `Ran 30` — `OK`.
  - `l13c_c1_green_display.log` (15:39:06.509543200): `-m unittest tests.test_level1_display_cost tests.test_level1_display` → `Ran 60` — `OK`.
  - `l13c_c1_green_level1_all.log` (15:56:25.182151500): LALL → `Ran 537` — `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` (U2d 515 + 22 test mới).
  - Chạy thử (không phải số liệu, không commit) `PY scripts/level1_display_cost.py --out _work/_plan15_l13/l13c_c1_smoke.json` (code dirty) → exit 0; mỗi lần `n_imshow == n_frames`, tổng `path_counts` khớp, 1080p toàn `render_to_window`; `grep -ciE 'users[\/]+'` = 0. KHÔNG ghi `reports/…/display_cost.json` (việc C2).
- Kiểm tĩnh (`l13c_c1_static.log`, trên cây làm việc trước commit; chạy lại sau commit): AC-U9 = 0; `git diff --stat d1a8308 -- src/` rỗng; `git diff --stat 93abb08 -- level1_demo.py src/` rỗng; AC-U9b (base `b0cbcf1`) = 0; `skip` mới = 0; `sha256sum checkpoints/alphabet_best.pt` = `160e0c68…`. cv2 `5.0.0`.
- Impact (`l13c_c1_impact.log`): `compute_ratio`, `dc1_gate`, `summarize_frame_total`, `measure`, `build_report`/`main`/`_DisplayCostRecorder` (`--file scripts/level1_display_cost.py`) đều LOW, chỉ script + test của nó gọi.
- Giả định: (1) `compute_ratio` cũng ném `ValueError` khi p50 1080p không hữu hạn hoặc ≤ 0 (chặt hơn AC); (2) `ratio_p50` vẫn được tính khi p50 hai lần hợp lệ nhưng điều kiện khác vi phạm (vd n=9), gate vẫn `pass false` + reason; (3) argparse lỗi giữ `SystemExit(2)`; (4) commit theo regex AC-P `^15: L13-U2d `.
- Lệnh C2 (cầu nối): `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/level1_display_cost.py --out reports/level1_realtime_2026-10-08/display_cost.json > _work/_plan15_l13/l13c_c2_run1.log 2>&1; echo $?` rồi `--out _work/_plan15_l13/l13c_c2_run2.json` / `run3.json` (AC-C2).

## Lần sửa 13c — C2 (2026-10-09, orchestrator chạy lệnh; tại ea93fa1, scripts/ level1_demo.py src/ sạch)
- Lệnh (nối tiếp, không việc nặng khác): `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/level1_display_cost.py --out <out> > _work/_plan15_l13/l13c_c2_runN.log 2>&1; echo $?` với out lần 1 = `reports/level1_realtime_2026-10-08/display_cost.json`, lần 2/3 = `_work/_plan15_l13/l13c_c2_run{2,3}.json`. Commit DUY NHẤT JSON lần 1 (quy tắc đặt trước).
- lần 1 (commit): exit 0, gate.pass True, ratio_p50 1.1129; natural n_frames 72 path_counts {'Hud.compose': 70, 'render_to_window': 2} stage_p50_ms {'hud': 2.4, 'mediapipe': 28.184}; 1080p n_frames 74 path_counts {'Hud.compose': 0, 'render_to_window': 74} stage_p50_ms {'hud': 6.19, 'mediapipe': 27.974}; info.hud_p50_delta_ms 3.790; commit ea93fa1 code_dirty False.
- lần 2: exit 0, gate.pass True, ratio_p50 1.1329; natural n_frames 72 path_counts {'Hud.compose': 70, 'render_to_window': 2} stage_p50_ms {'hud': 2.569, 'mediapipe': 28.043}; 1080p n_frames 74 path_counts {'Hud.compose': 0, 'render_to_window': 74} stage_p50_ms {'hud': 6.263, 'mediapipe': 28.372}; info.hud_p50_delta_ms 3.694; commit ea93fa1 code_dirty False.
- lần 3: exit 0, gate.pass True, ratio_p50 1.0981; natural n_frames 72 path_counts {'Hud.compose': 70, 'render_to_window': 2} stage_p50_ms {'hud': 2.569, 'mediapipe': 28.781}; 1080p n_frames 74 path_counts {'Hud.compose': 0, 'render_to_window': 74} stage_p50_ms {'hud': 6.268, 'mediapipe': 28.275}; info.hud_p50_delta_ms 3.699; commit ea93fa1 code_dirty False.
- AC-C2: 3/3 exit 0 + pass; 1080p render_to_window == n_imshow (74/74) cả 3 lần; JSON lần 1 code_dirty false, commit ea93fa1 (= C1); grep 'users[\/]+' = 0. Natural có 2/72 khung đi render_to_window (khớp ghi nhận review U2d TB-2; nay được đếm trong path_counts).
  - Bổ sung (THẤP-B review U2d v2): mã thoát 3 lần C2 ghi ở `_work/_plan15_l13/l13c_c2_exitcodes.log` (run1/2/3 exit=0, bản sao output lệnh nền của orchestrator). Số hud dùng cho R2 lấy từ JSON: info.hud_p50_delta_ms 3.790 (lần 1).

## Lần sửa 13c — XW (2026-10-09, vslt-coder-claude chạy lệnh; tại 79b73b2; `docs/plans/15-lan-sua-13c.md` §4 hàng XW, AC-X1, AC-W1)

Chạy nối tiếp X1 rồi W1, không trùng lần đo DC1 nào (không có tiến trình python khác lúc chạy). Không sửa `src/`, `level1_demo.py`, `tests/`.

**X1 (AC-X1 = `15-lan-sua-13b.md:116-119`)** — `PY = .venv/Scripts/python`.
- (i) 5 lần `PY -m unittest tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs -v` → `_work/_plan15_l13/x1_iso_{1..5}.log`: 1 OK / 4 FAIL (iso_2 OK; iso_1, 3, 4, 5 `FAILED (failures=1)`).
- (ii) 3 lần `PY -m unittest tests.test_hand_landmarks_ws -v` → `x1_mod_{1..3}.log`: 3 OK / 0 FAIL (`Ran 9 tests`, `OK` cả 3).
- Tổng 4/8 OK ⇒ theo luật AC-X1 giữ nhãn "chập chờn"; tần suất: chạy riêng 1/5 OK, cả module 3/3 OK. Không DỪNG.
- 5 dòng cuối traceback đầu tiên (`x1_iso_1.log`):
  ```
  File "...\tests\test_hand_landmarks_ws.py", line 185, in test_reset_segments_and_graphs
    self.assertEqual([g["closes"] for g in spy.graphs], [1, 1, 1, 1])   # last graph closed with the session
  AssertionError: Lists differ: [1, 1, 1, 0] != [1, 1, 1, 1]
  First differing element 3:
  0
  ```
  iso_3/4/5 cùng `AssertionError: Lists differ: [1, 1, 1, 0] != [1, 1, 1, 1]` (graph cuối chưa được đóng khi kiểm).

**W1 (AC-W1, thông tin, không phải gate)** — script tạm `_work/_plan15_l13/w1_probe.py` (KHÔNG commit). Lệnh:
`PYTHONIOENCODING=utf-8 .venv/Scripts/python _work/_plan15_l13/w1_probe.py > _work/_plan15_l13/w1_probe.log 2>&1` → exit 0.
Cửa sổ THẬT (không vá `imshow`/`namedWindow`/`resizeWindow`/`waitKey`); chỉ bọc `cv2.getWindowImageRect` (ghi rect), đếm `Hud.compose`/`render_to_window`
(bọc hàm gốc như C1), và bọc pass-through `app._window_image` để ghi cỡ tự nhiên `(w, h + panel_h)`, cỡ ảnh trả về và `cam_rect` của
`fit_layout(w, h, panel_h, rect)` mỗi khung. Clip D2 `data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4`, `--pace realtime`; cv2 5.0.0, backend WIN32, python 3.11.9.
- Cỡ tự nhiên khung 1: `(640, 643)`.
- Rect khung 1, 2, 5: đều `(41, 57, 640, 643)` (khung 2 rect w,h == cỡ tự nhiên khung 1: True ⇒ không lệch viền/DPI trên máy này; câu
  "ở cỡ mặc định mọi khung đi `render_to_window`" KHÔNG áp dụng).
- Tập rect khác nhau: 1 giá trị `(41, 57, 640, 643)` × 69 khung (69 lần gọi getWindowImageRect / 69 khung).
- `path_counts`: `{'Hud.compose': 67, 'render_to_window': 2}` (khớp số khung mỗi đường ghi theo khung).
- Số khung cỡ tự nhiên khác khung trước (panel đổi cao): 2 (khung 6 và 8); tập cỡ tự nhiên `(640, 643)` × 67, `(640, 667)` × 2 (khung 6–7).
- Tiêu đề thật (`FindWindowW` theo tên + `GetWindowTextW`): `'VSLT Level 1 (f: toan man hinh)'`, khớp `WINDOW_NAME`.
- Nhận xét (U2b THẤP-3): khi panel cao thêm 24 px (643 → 667) mà cửa sổ giữ 640×643 (app chỉ `resizeWindow` một lần ở khung đầu), 2 khung đó đi
  `render_to_window`: `cam_rect` đổi từ `(0, 0, 640, 480)` sang `(11, 0, 617, 462)` (scale 0.964), tức ảnh camera CO lại và DỊCH ngang 11 px rồi
  trở lại ở khung 8. Cỡ ảnh đưa vào `imshow` giữ `(640, 643)` cả 69 khung. Tần suất trên clip D2: 2/69 khung (2 lần đổi đường). Đây là số đo một
  lượt, phụ thuộc nội dung panel; chuyển R2 §8 câu 2 + VU.
