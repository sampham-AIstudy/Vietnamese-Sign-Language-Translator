# Kế hoạch 15 — tiến độ coder

Kế hoạch: `docs/plans/15-level1-realtime-desktop.md`. Chặng giao: MVP B0–B3. Nhánh `feat/vslt-complete`, mốc HEAD `6c4f5e0`.
Lệnh `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`. Log tạm: `_work/_plan15/` (không commit).

## Trạng thái
- ĐANG LÀM: B2
- Xong: B0 (4e4d9e3), B1
- Còn lại (chặng này): B2, B3. Ngoài chặng: B4–B9.

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

## Quyết định / giả định của coder
- `load_level1_config` chốt ở `src/inference/level1_core.py` (đúng bảng §3.1); kiểm thêm khóa lạ, kiểu, `source` ∈ {design, "calibrated: …"}.
- Bộ tách import `normalize_hand_landmarks` từ `src/data/alphabet_preprocessing.py` (một nơi cho chuẩn hóa, skill mục 6); bản thân
  module không dùng cv2/torch nhưng import này kéo theo torch (alphabet_preprocessing import torch ở đầu file).
- Bộ tách: phân loại đứng yên/di chuyển chỉ cập nhật trên khung CÓ tay; khung mất tay ngắn (< hand_lost_ms) không cắt chuỗi đứng yên.
  Đổi kích thước khung giữa chừng → đóng bộ đệm như mất tay. Segment bỏ khung không tay ở đầu/cuối.
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
