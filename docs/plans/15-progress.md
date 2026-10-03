# Kế hoạch 15 — tiến độ coder

Kế hoạch: `docs/plans/15-level1-realtime-desktop.md`. Chặng giao: MVP B0–B3. Nhánh `feat/vslt-complete`, mốc HEAD `6c4f5e0`.
Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`. Log tạm: `_work/_plan15/` (không commit).

## Trạng thái
- ĐANG LÀM: — (chặng MVP B0–B3 xong; chờ orchestrator / U1 của người dùng)
- Xong: B0 (4e4d9e3), B1 (966ea4b), B2 (58b31ce), B3 (WIP 75e3116 + commit `15: B3`)
- Còn lại: B4–B9 (ngoài chặng này). B4 (AC-E1/E3) là bước kế tiếp theo kế hoạch.

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

## Việc người dùng — U1 (sau B3, ~10 phút; không chặn)
Từ gốc repo, trong .venv: `.venv\Scripts\python level1_demo.py --source 0 --display-mirror`
(thêm `--out-json _work/u1_webcam.json` nếu muốn xem JSON; không commit). Ký lần lượt vài chữ (a, b, c, o, dấu sắc) rồi 2 từ "ba", "cá"
(giữ yên mỗi chữ cho tới khi thanh xanh đầy; hạ tay ~1 giây để kết thúc từ; chữ lặp "oo" cần nảy tay hoặc nhấn `r`). Nhận xét: chấm có
bám tay không, chữ có tự tách không, có phát lặp khi giữ yên không, độ trễ cảm nhận. Nếu webcam không mở: thử `--source 1`, hoặc đổi
`camera_api` trong configs/level1_realtime.json sang "msmf"/"any" (ghi lại).

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
