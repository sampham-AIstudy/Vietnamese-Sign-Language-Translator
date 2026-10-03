# Kế hoạch 15 — tiến độ coder

Kế hoạch: `docs/plans/15-level1-realtime-desktop.md`. Chặng giao: MVP B0–B3. Nhánh `feat/vslt-complete`, mốc HEAD `6c4f5e0`.
Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`. Log tạm: `_work/_plan15/` (không commit).

## Trạng thái
- ĐANG LÀM: A2 (bước 1: code + test + config thiết kế)
- Xong: B0 (4e4d9e3), B1 (966ea4b), B2 (58b31ce), B3 (WIP 75e3116 + commit `15: B3`), B4 (commit `15: B4`), B5 (3ebc7b9), T1 (92fce21), A1 (commit code 72167b9 + commit báo cáo 1ca53f3), T2 (ec19b1d; code ở ad7c126).
- Còn lại: A2, A3, C1, A4, C2.

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

