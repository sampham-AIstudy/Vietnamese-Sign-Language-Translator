# Kế hoạch 15 — tiến độ coder

Kế hoạch: `docs/plans/15-level1-realtime-desktop.md`. Chặng giao: MVP B0–B3. Nhánh `feat/vslt-complete`, mốc HEAD `6c4f5e0`.
Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`. Log tạm: `_work/_plan15/` (không commit).

## Trạng thái
- ĐANG LÀM: phiên cloud 2026-10-04 (nhánh `cloud/2026-10-04-level1-rearm`) DỪNG sau R3 — mã A2a/R1/A2b/R2/R3 xong; CHẠY R2/R3 + kiểm S18/E1 BỊ CHẶN vì cloud thiếu dữ liệu (KAGGLE_KEY giữ chỗ). Báo cáo + thứ tự việc cho local: `docs/cloud_reports/level1-rearm-2026-10-04.md` §8.
- Xong: B0 (4e4d9e3), B1 (966ea4b), B2 (58b31ce), B3 (WIP 75e3116 + commit `15: B3`), B4 (commit `15: B4`), B5 (3ebc7b9), T1 (92fce21), A1 (commit code 72167b9 + commit báo cáo 1ca53f3), T2 (ec19b1d; code ở ad7c126), A2 (6067611 + config commit `15: A2 config hiệu chỉnh`), R0 (code `a3970a6` + báo cáo `reports/level1_realtime_2026-10-04/rearm_check_r0.json`). A2a (code ở WIP `dddfde8` + commit `15: A2a` trên nhánh cloud; CHỜ LOCAL: AC-S18 trên clip thật + sinh lại rearm_check_r0.json bằng lệnh ở mục A2a). R1 (commit `15: R1` trên nhánh cloud; CHỜ LOCAL: AC-S18 + S18b trên clip thật). A2b (`71fc664` mã + `4b5d736` config; AC-W3 đạt).
- Còn lại: R2 (chạy + commit JSON + commit config), R3 (chạy + commit JSON + commit config), U1c, A3, C1, (R4, A4, C2).

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
  `Ran 51 — OK` (`_work/_plan15/W1_green_demo_eq.log`). detect-changes (`git diff --stat`): `level1_demo.py` 38 + / 1 −, test 150 + / 0 −.
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
- Impact: chỉ thêm file mới (script, test) và một mục tài liệu; không sửa symbol có sẵn. detect-changes (`git diff --stat`): xem commit.
- Test viết TRƯỚC `tests/test_level1_trace_report.py` (9 test, AC-6e): trace tổng hợp dựng như app (kết quả cửa sổ tổng hợp → `Level1LabelDecoder`
  thật → `Level1App._window_entry` của app) cho từng M1/M2/M3/M4 ⇒ đúng mã chính và đúng số cửa sổ từng lớp; M4 không cần `--expected`
  (lấy nhãn phát), cặp khác ⇒ không M4; M0; reset (rút tay) + onset; căn `--expected` khi phát lại sau reset; `--hold-ms`; chặn thời gian;
  cờ `truncated`, thiếu `window_trace` ⇒ mã thoát 2; CLI chạy 2 lần ra cùng byte (stdout và `--out-json`). ĐỎ: `ImportError` (script chưa có,
  `_work/_plan15/W3_red.log`); XANH: `Ran 9 — OK` (`_work/_plan15/W3_green.log`).
