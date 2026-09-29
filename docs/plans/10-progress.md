Trạng thái: XONG (chờ orchestrator gọi vslt-reviewer)

# Tiến độ kế hoạch 10 — Guard DoD 7 phía backend

- Kế hoạch: `docs/plans/10-guard-dod7.md`
- Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`)
- P10 (HEAD lúc bắt đầu B1, commit chứa kế hoạch): `f16d0a9` (`f16d0a9d9f717af6c50381732152a58d9ad3c953`)
- Log/file tạm: `/home/user/_plan10_tmp/` (ngoài repo; `../_plan10_tmp/` của kế hoạch)

**Bước đã xong:** B1, B2, B3
**Bước đang làm:** (không)
**Bước còn lại:** (không) — chờ review

## B1(1) — Mốc B0 (HEAD f16d0a9)

- `git status --porcelain > /home/user/_plan10_tmp/b0_status.txt` → 0 byte (cây sạch, chụp TRƯỚC khi tạo file progress này).
- Lệnh AC8 bỏ module cuối (29 module, `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_alphabet_preprocessing ... tests.test_frontend_contract -v`)
  → log `/home/user/_plan10_tmp/b0_ac8.txt`; tổng kết chép từ log:
  `Ran 414 tests in 31.092s` / `FAILED (failures=1, errors=1, skipped=30)`.
  - FAIL: `test_no_violation (tests.test_frontend_contract.TestFrontendSourceGuard.test_no_violation)` (đỏ có chủ đích, kế hoạch 06).
  - ERROR: `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu checkpoint ViT5, gitignore).
  - skipped: 30 dòng → `/home/user/_plan10_tmp/b0_skip.txt` (thiếu dữ liệu gitignore).
  - Khớp tham chiếu orchestrator tại 04ec565 (Ran 414, failures=1, errors=1, skipped=30).

## B1(2) — `tests/test_backend_source_guard.py`

- Chỉ thư viện chuẩn (`ast, re, os, glob, json, hashlib, collections, tempfile, subprocess, sys, datetime, unittest` + `shutil`
  để xóa thư mục tạm ở tearDown, `unicodedata` để chuẩn hóa NFC trước khi so regex tiếng Việt). Không import numpy/torch/cv2/
  mediapipe/fastapi/backend.main/src.* (AC7-a kiểm bằng subprocess).
- Hàm theo hợp đồng §3.0: `Finding`, `scan_source`, `serving_closure`, `main_scope`, `scan_repo`, `compare_registry`; phụ:
  `rules_for`, `format_comparison`, `registry_totals`, `build_report`/`write_report` (chế độ `--report`).
- Lớp test: `TestRuleSelfCheck` (AC2 + AC3 + các ca đếm), `TestScope` (AC4 a–e), `TestBackendSourceGuard` (AC5 a–c),
  `TestRegistryComparator` (AC6 a–d), `TestImportLight` (AC7-a), thêm `TestReportMode` (§3.7/AC7-c: chạy `--report` 2 lần ra
  thư mục tạm ngoài repo, `findings`/`summary`/thân giống hệt, không có đường dẫn tuyệt đối trong thân).

## B1(3) — Output thô đầu tiên (sổ rỗng)

Lệnh: `PYTHONIOENCODING=utf-8 .venv/bin/python -m tests.test_backend_source_guard --report /home/user/_plan10_tmp/b1_first_scan.json`
(HEAD `5b979a5`, `ALLOWED = {}`, `KNOWN_VIOLATIONS = {}`). Bảng gom theo `(path, rule, qualname)` do script sinh từ JSON đó:

| # | path | rule | qualname | count | dòng |
|---|---|---|---|---|---|
| 1 | `realtime_demo.py` | C-result | `RealtimeHUD._locate_vietnamese_font` | 1 | 52 |
| 2 | `realtime_demo.py` | C-string | `RealtimeDemo._open_stream` | 2 | 266, 267 |
| 3 | `realtime_demo.py` | C-string | `RealtimeDemo.run` | 1 | 294 |
| 4 | `realtime_demo.py` | C-string | `main` | 1 | 395 |
| 5 | `realtime_demo.py` | D-binding | `RealtimeDemo.run` | 1 | 330 |
| 6 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.add_jitter` | 1 | 34 |
| 7 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.augment_sequence` | 5 | 107, 109, 111, 113, 115 |
| 8 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.augment_static` | 3 | 122, 124, 126 |
| 9 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.augment_vsl_sequence` | 12 | 147, 148, 152, 153, 161, 162, 166, 167, 181, 182, 186, 188 |
| 10 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.keypoint_mask` | 2 | 95, 97 |
| 11 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.random_rotate_2d` | 1 | 49 |
| 12 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.random_scale` | 1 | 41 |
| 13 | `src/data/augment.py` | A-numpy | `KeypointAugmenter.time_warp` | 1 | 76 |
| 14 | `src/data/harmonized.py` | A-torch | `HarmonizedDataset.__getitem__` | 1 | 178 |
| 15 | `src/data/harmonized.py` | D-binding | `HarmonizedDataset.__getitem__` | 1 | 175 |
| 16 | `src/data/harmonized.py` | D-binding | `harmonize` | 1 | 129 |
| 17 | `src/data/landmark_extractor.py` | D-binding | `CleanHolisticExtractor.extract_from_video` | 1 | 121 |
| 18 | `src/data/vsl_dataset.py` | D-string | `validate_split_guards` | 1 | 176 |
| 19 | `src/data/vsl_gh_dataset.py` | D-string | `<module>` | 1 | 31 |
| 20 | `src/inference/ensemble.py` | D-string | `run_ensemble_benchmark` | 1 | 303 |
| 21 | `src/inference/predictor.py` | C-name | `VSLPredictor.warmup` | 3 | 185, 186, 187 |
| 22 | `src/inference/realtime_extractor.py` | C-name | `RealtimeLandmarkExtractor.__init__` | 1 | 66 |
| 23 | `src/inference/sign_segmenter.py` | D-binding | `SignSegmenter._activity` | 1 | 141 |
| 24 | `src/metrics/cslr_metrics.py` | D-binding | `compute_wer` | 1 | 216 |

summary (từ JSON): by_status={"known": 0, "allowed": 0, "unregistered": 45}; by_rule={"A-stdlib": 0, "A-numpy": 26, "A-torch": 1, "B-import": 0, "B-name": 0, "C-name": 4, "C-string": 4, "C-result": 1, "D-binding": 6, "D-string": 3}; n_serving_files=44; n_main_files=56; nhóm=24
generated_by: git_commit=5b979a5d03ae0ff295ba4ea7f58f70406eef1f6a, code_dirty=True (file test mới chưa track), command=`PYTHONIOENCODING=utf-8 .venv/bin/python -m tests.test_backend_source_guard --report /home/user/_plan10_tmp/b1_first_scan.json`

- Phạm vi: `scripts_realtime = []` (== `SCRIPTS_REALTIME = ()`), `MIN_SERVING` thỏa, `src/training/trainer.py` và
  `src/export/export_onnx.py` KHÔNG thuộc SERVING → không chạm điểm dừng §7.3.
- `backend/main.py`: 0 finding → không chạm §7.1. Không có C-result/C-string nào trong một route backend → không chạm §7.2
  (C-result duy nhất là danh sách đường dẫn font trong `realtime_demo.py`, xem dưới).

## B1(4) — Phân loại (sổ điền bằng script từ `b1_first_scan.json`, không gõ tay số)

### ALLOWED — 16/16 khóa của bảng §3.6 đều được guard báo (không có "dự báo không xảy ra"); tổng count = 36

Bằng chứng caller: `npx --yes gitnexus@1.6.12 context <tên> --file <file> --repo .` (output đầy đủ:
`/home/user/_plan10_tmp/context/<tên>.json`; index `.gitnexus/meta.json` lastCommit `90159bb`, `git diff --stat 90159bb HEAD --
src backend realtime_demo.py` rỗng → index khớp mã). Tóm tắt `incoming` (chép từ output):

| Khóa (qualname) | context (incoming) | Grep bổ sung |
|---|---|---|
| augment.py A-numpy `KeypointAugmenter.add_jitter` | status=found; has_method KeypointAugmenter; calls: augment_sequence, augment_static | xem dòng Grep augment dưới |
| … `random_scale`, `random_rotate_2d` | calls: augment_sequence, augment_static | nt |
| … `time_warp`, `keypoint_mask` | calls: augment_sequence | nt |
| … `augment_sequence`, `augment_static` | chỉ has_method (không caller trong index → coi như UNKNOWN) | `src/data/dataset.py:88` `self.augmenter.augment_sequence`, `:121` `augment_static` (dataset.py NGOÀI bao đóng phục vụ) |
| … `augment_vsl_sequence` | calls: tests/test_vsl_system.py:test_keypoint_augmenter | `src/data/vsl_dataset.py:369` (trong `VSLDataset`, chỉ khi `self.augmenter`) |
| lớp `KeypointAugmenter` | imports: src/data/dataset.py, src/data/vsl_dataset.py, tests/test_vsl_system.py | Grep `KeypointAugmenter\(`: `src/data/vsl_dataset.py:256` và `src/data/dataset.py:45,113` đều `KeypointAugmenter() if augment else None`; Grep `augment=True`: chỉ `scripts/train_unified.py:182,187`, `src/data/dataset.py:169`; Grep `VSLDataset(\|get_vsl_dataloaders(\|HarmonizedDataset(` trong `backend/ src/inference src/translation realtime_demo.py` (trừ `def`): chỉ `src/inference/ensemble.py:272` (trong `run_ensemble_benchmark`, gọi từ CLI `ensemble.py:430`) |
| harmonized.py A-torch / D-binding `HarmonizedDataset.__getitem__` | lớp HarmonizedDataset: imports từ scripts (train_unified, report_step4, shortcut_85, live_segment_check), src/inference/harmonized_live.py, src/inference/sign_segmenter.py, tests | Grep: `harmonized_live.py:20` chỉ import `harmonize`; `sign_segmenter.py:32` chỉ import `_normalise, hand_activity` → phục vụ KHÔNG tạo `HarmonizedDataset`; `HarmonizedDataset(..., augment=True)` chỉ ở `scripts/train_unified.py:182` |
| harmonized.py D-binding `harmonize` | calls: harmonized_live._harmonize_buffer, HarmonizedDataset.__getitem__, scripts/shortcut_85.featurize, tests | `harmonized_live.py:115` `harmonize(kps, vis, aspect, fps, cfg=..., timestamps_s=ts)` (không truyền rng → mặc định None, `harmonized.py:120`); 30.0 là fps ĐẦU VÀO mặc định dùng chung train/live |
| cslr_metrics.py D-binding `compute_wer` | calls: cslr_metrics.compute, src/training/train_cslr.evaluate_cslr, scripts/simulate_cslr_streaming.main | phục vụ chỉ import `ctc_greedy_decode, tokens_to_words` (`src/translation/cslr_recognizer.py:24`); Grep `compute_wer(` trong backend/src/inference/src/translation/realtime_demo.py: 0 |
| vsl_dataset.py D-string `validate_split_guards` | calls: vsl_dataset.get_vsl_dataloaders, scripts/train_unified.main, tests/test_split_guards (6) | câu báo lỗi kiểm toàn vẹn split |
| ensemble.py D-string `run_ensemble_benchmark` | calls: ensemble.py (module, CLI) | `ensemble.py:430` trong khối CLI; chuỗi mô tả trọng số 0.5/0.5 |
| predictor.py C-name `VSLPredictor.warmup` | calls: VSLPredictor.__init__ | `predictor.py:191` `_ = self.model(dummy_seq, dummy_jm, dummy_tm)` — đầu ra bỏ |
| realtime_extractor.py C-name `RealtimeLandmarkExtractor.__init__` | lớp: imports realtime_demo.py, src/inference/realtime_pipeline.py, scripts (audit_realtime, generate_slide_images, smoke_test_phase10), reports/audit_20260924 | `realtime_extractor.py:66-67` `dummy = np.zeros(...)`; `self.holistic.process(dummy)` — đầu ra bỏ |

### KNOWN_VIOLATIONS — 8 nhóm, tổng count = 9 (mọi nhóm còn lại; coder KHÔNG thêm vào ALLOWED)

| Khóa | count | Loại | Hướng sửa (kế hoạch sau) |
|---|---|---|---|
| `realtime_demo.py` C-string `RealtimeDemo._open_stream` | 2 | VI PHẠM (dự báo #1) | bỏ `--source mock` khỏi điểm vào người dùng (hoặc fixture chỉ trong tests/) |
| `realtime_demo.py` C-string `RealtimeDemo.run` | 1 | VI PHẠM (dự báo #2) | bỏ cùng chế độ mock |
| `realtime_demo.py` C-string `main` | 1 | VI PHẠM (dự báo #3) | bỏ cùng chế độ mock |
| `realtime_demo.py` D-binding `RealtimeDemo.run` | 1 | VI PHẠM (dự báo #4) | bỏ `else 30.0` (hiển thị "—"/0 khi chưa đo) |
| `realtime_demo.py` C-result `RealtimeHUD._locate_vietnamese_font` | 1 | **đề xuất DTG** (ngoài dự báo) | `candidates = [...]` là danh sách đường dẫn font (khóa `candidates` ∈ RESULT_KEYS); nếu planner không duyệt: đổi tên biến |
| `src/data/landmark_extractor.py` D-binding `CleanHolisticExtractor.extract_from_video` | 1 | **đề xuất DTG** (ngoài dự báo) | `fps = cap.get(cv2.CAP_PROP_FPS) or 25.0`: fps ĐẦU VÀO mặc định khi video thiếu metadata (cùng tinh thần khóa ALLOWED harmonized #7/#8) |
| `src/data/vsl_gh_dataset.py` D-string `<module>` | 1 | **đề xuất DTG** (ngoài dự báo) | chuỗi `"""..."""` dòng 31–70 là ghi chú cấp module đứng SAU import (không phải docstring module — docstring ở dòng 1) chứa "Hand landmark ordering is 100% identical" (dòng 58); không phải số đo. Nếu không duyệt: chuyển thành comment |
| `src/inference/sign_segmenter.py` D-binding `SignSegmenter._activity` | 1 | **đề xuất DTG** (ngoài dự báo) | `fps = (n - 1) / (t1 - t0) if n >= 2 and t1 > t0 else 30.0`: fps suy từ timestamp; 30.0 chỉ khi n < 2 (comment trong mã: tốc độ = 0 bất kể fps); không hiển thị. Nếu không duyệt: hằng có tên |

## B1(5) — Chạy module 2 lần

`PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_backend_source_guard -v` (log `/home/user/_plan10_tmp/b1_run1.txt`,
`b1_run2.txt`): lần 1 `Ran 24 tests in 2.572s` / `OK`; lần 2 `Ran 24 tests in 2.688s` / `OK`; 0 skip. Dòng in:
`[DoD7-guard] known=9 allowed=36`, `[scope] serving=44 main=56`.

Đột biến AC6 (in minh họa, `/home/user/_plan10_tmp/b1_mutations.txt`): mỗi đột biến nối vào `backend/main.py` TRONG BỘ NHỚ cho
`unregistered` đúng mã (A-stdlib, B-import, C-result ×2, C-name + D-binding, D-string); nhân đôi → `CHANGED realtime_demo.py
C-result RealtimeHUD._locate_vietnamese_font: đăng ký 1, hiện 2`; xóa → `STALE ...: đăng ký 1, hiện 0`; nguyên vẹn → rỗng.
`sha256sum -c` `backend/main.py` sau khi chạy: OK; `git status --porcelain` trước/sau giống hệt.

## B2 — Báo cáo JSON + không hồi quy (HEAD B1 = `319ddcd`)

- Cây sạch với các đường của `code_dirty` (`git status --porcelain -- backend src tests realtime_demo.py start_fullstack.ps1` → 0 dòng).
- Lệnh: `PYTHONIOENCODING=utf-8 .venv/bin/python -m tests.test_backend_source_guard --report reports/guard_dod7_2026-09-29/guard_findings.json` → `reports/guard_dod7_2026-09-29/guard_findings.json`:
  `generated_by.git_commit = 319ddcdb344572fa4d0878ae9922e60062f202a2` (commit B1), `code_dirty = false`,
  `generated_at_utc = 2026-09-29T05:11:18Z`.
  `summary.by_status = {"known": 9, "allowed": 36, "unregistered": 0}`; `by_rule = {"A-stdlib": 0, "A-numpy": 26, "A-torch": 1, "B-import": 0, "B-name": 0, "C-name": 4, "C-string": 4, "C-result": 1, "D-binding": 6, "D-string": 3}`;
  `n_serving_files = 44`, `n_main_files = 56`.
  Tổng `known`/`allowed` trong JSON khớp dòng in của test `[DoD7-guard] known=9 allowed=36` (AC5-c/d).
- Chạy lại ra `/home/user/_plan10_tmp/b2_rerun.json`: thân (bỏ `generated_by`) giống hệt (`findings` và `summary` giống hệt; AC7-c).
  File báo cáo không chứa đường dẫn tuyệt đối.
- AC8 (30 module, lệnh §5 AC8) → `/home/user/_plan10_tmp/b2_ac8.txt`: `Ran 438 tests in 34.411s` / `FAILED (failures=1, errors=1, skipped=30)`.
  So B0 (`Ran 414`): 438 = 414 + 24 (module mới); tập id FAIL/ERROR (`b2_failerr.txt`) == B0 (`b0_failerr.txt`):
  `TestFrontendSourceGuard.test_no_violation` (FAIL), `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (ERROR);
  tập id skip (`b2_skip.txt`, 30) == B0 (`b0_skip.txt`); module mới 24/24 `ok`, 0 fail, 0 error, 0 skip.
  Giữa B0 và B2 nhánh không nhận commit ngoài kế hoạch này (`git log f16d0a9..HEAD`: chỉ `5b979a5`, `319ddcd`).
- `git status --porcelain` trước/sau lệnh AC8 giống hệt (chỉ `?? reports/guard_dod7_2026-09-29/`); `sha256sum -c backend/main.py`: OK.

## B3 — Đối chiếu, danh sách vi phạm, đề xuất

### Đối chiếu dự báo §2.3 #1–#13 (bảng do script sinh từ `reports/guard_dod7_2026-09-29/guard_findings.json`, commit `319ddcd`)

| # §2.3 | Vị trí dự báo | Luật dự báo | Xảy ra? | Mã luật thực tế (JSON) | Dòng thực tế (JSON) | status JSON |
|---|---|---|---|---|---|---|
| 1 | `realtime_demo.py:266-267` | C-string (VI PHẠM) | có (2 finding, 1/1 nhóm) | C-string | 266, 267 | known |
| 2 | `realtime_demo.py:294` | C-string (VI PHẠM) | có (1 finding, 1/1 nhóm) | C-string | 294 | known |
| 3 | `realtime_demo.py:395` | C-string (VI PHẠM) | có (1 finding, 1/1 nhóm) | C-string | 395 | known |
| 4 | `realtime_demo.py:330` | D-binding (VI PHẠM) | có (1 finding, 1/1 nhóm) | D-binding | 330 | known |
| 5 | `src/data/augment.py:34..188` | A-numpy (DTG) | có (26 finding, 8/8 nhóm) | A-numpy | 34, 41, 49, 76, 95, 97, 107, 109, 111, 113, 115, 122, 124, 126, 147, 148, 152, 153, 161, 162, 166, 167, 181, 182, 186, 188 | allowed |
| 6 | `src/data/harmonized.py:178` | A-torch (DTG) | có (1 finding, 1/1 nhóm) | A-torch | 178 | allowed |
| 7 | `src/data/harmonized.py:175` | D-binding (DTG) | có (1 finding, 1/1 nhóm) | D-binding | 175 | allowed |
| 8 | `src/data/harmonized.py:129` | D-binding (DTG) | có (1 finding, 1/1 nhóm) | D-binding | 129 | allowed |
| 9 | `src/metrics/cslr_metrics.py:216` | D-binding (DTG) | có (1 finding, 1/1 nhóm) | D-binding | 216 | allowed |
| 10 | `src/data/vsl_dataset.py:176` | D-string (DTG) | có (1 finding, 1/1 nhóm) | D-string | 176 | allowed |
| 11 | `src/inference/ensemble.py:303` | D-string (DTG) | có (1 finding, 1/1 nhóm) | D-string | 303 | allowed |
| 12 | `src/inference/predictor.py:185-187` | C-name (DTG) | có (3 finding, 1/1 nhóm) | C-name | 185, 186, 187 | allowed |
| 13 | `src/inference/realtime_extractor.py:66` | C-name (DTG) | có (1 finding, 1/1 nhóm) | C-name | 66 | allowed |

Cả 13 dự báo đều xảy ra, đúng mã luật dự báo, đúng dòng dự báo (#5: 26 finding trải 8 nhóm, dòng 34..188).
Mục "ngoài luật" #14–#18 kiểm trong cùng JSON: `backend/main.py` 0 finding (#14 comment, #15 docstring route "(487 classes for
Tier 2)" không khớp D-string, #16 `*_ms = 0.0` là sentinel); `src/export/*`, `src/training/*`, `src/translation/dataset.py` 0 finding
và KHÔNG thuộc SERVING (#17, #18).

Ngoài dự báo (nhóm guard báo mà §2.3 không có) — cả 4 vào KNOWN kèm "đề xuất DTG" (§3.6: coder không tự thêm ALLOWED):
- `realtime_demo.py` C-result `RealtimeHUD._locate_vietnamese_font`: dòng 52, status=known
- `src/data/landmark_extractor.py` D-binding `CleanHolisticExtractor.extract_from_video`: dòng 121, status=known
- `src/data/vsl_gh_dataset.py` D-string `<module>`: dòng 31, status=known
- `src/inference/sign_segmenter.py` D-binding `SignSegmenter._activity`: dòng 141, status=known

### Danh sách vi phạm có sẵn (CHÍNH THỨC, AC5-e) — mọi finding `status: "known"` của
`reports/guard_dod7_2026-09-29/guard_findings.json` (`generated_by.git_commit = 319ddcdb344572fa4d0878ae9922e60062f202a2`); bảng do script chép từ JSON

| # | file:dòng | mã | qualname | snippet |
|---|---|---|---|---|
| 1 | `realtime_demo.py:52` | C-result | `RealtimeHUD._locate_vietnamese_font` | `candidates = [` |
| 2 | `realtime_demo.py:266` | C-string | `RealtimeDemo._open_stream` | `elif self.source == "mock":` |
| 3 | `realtime_demo.py:267` | C-string | `RealtimeDemo._open_stream` | `print("Using Synthetic Mock Video Stream for Smoke Test...")` |
| 4 | `realtime_demo.py:294` | C-string | `RealtimeDemo.run` | `if self.source == "mock":` |
| 5 | `realtime_demo.py:330` | D-binding | `RealtimeDemo.run` | `avg_fps = 1.0 / (sum(fps_tracker) / len(fps_tracker)) if fps_tracker else 30.0` |
| 6 | `realtime_demo.py:395` | C-string | `main` | `parser.add_argument("--source", type=str, default="0", help="Webcam device index ('0', '1') or video path ('path.mp4') or 'mock'")` |
| 7 | `src/data/landmark_extractor.py:121` | D-binding | `CleanHolisticExtractor.extract_from_video` | `fps = cap.get(cv2.CAP_PROP_FPS) or 25.0` |
| 8 | `src/data/vsl_gh_dataset.py:31` | D-string | `<module>` | `"""` |
| 9 | `src/inference/sign_segmenter.py:141` | D-binding | `SignSegmenter._activity` | `fps = (n - 1) / (t1 - t0) if n >= 2 and t1 > t0 else 30.0   # n == 1: speed is 0 whatever fps is` |

Số finding status=known (đếm từ JSON): 9; summary.by_status.known = 9

DoD 7 phần backend sau kế hoạch này: **guard có, CHƯA ĐẠT** (`known = 9` ≠ 0, theo JSON trên; §3.5 ý 4).

### Đề xuất DTG (planner xét ở "Lần sửa" — coder KHÔNG thêm vào ALLOWED)

1. `realtime_demo.py` C-result `RealtimeHUD._locate_vietnamese_font` (dòng 52): `candidates = [...]` là danh sách đường dẫn font
   (tên `candidates` ∈ RESULT_KEYS nên luật C-result (2) khớp), không phải kết quả nhận dạng. Phương án khác: đổi tên biến ở kế hoạch 11.
2. `src/data/landmark_extractor.py` D-binding `CleanHolisticExtractor.extract_from_video` (dòng 121): `fps = cap.get(...) or 25.0`
   — fps ĐẦU VÀO mặc định khi video thiếu metadata; cùng bản chất với khóa ALLOWED `harmonized.py` D-binding (#7, #8).
3. `src/data/vsl_gh_dataset.py` D-string `<module>` (dòng 31): chuỗi ghi chú cấp module đứng sau import (không phải docstring)
   chứa "Hand landmark ordering is 100% identical" (dòng 58) — mô tả ánh xạ landmark, không phải số đo.
4. `src/inference/sign_segmenter.py` D-binding `SignSegmenter._activity` (dòng 141): `... else 30.0` chỉ khi n < 2 (tốc độ = 0 bất
   kể fps, theo comment trong mã); tham số nội bộ bộ tách ký hiệu, không hiển thị.

### Đề xuất kế hoạch 11 (sửa vi phạm; KHÔNG làm ở đây)

- `realtime_demo.py`: bỏ chế độ `--source mock` (dòng 266–267, 294, 395; khung tổng hợp) khỏi điểm vào người dùng, hoặc chuyển
  thành fixture chỉ trong `tests/` (caller: `run_core.py:116-124` chỉ truyền webcam/video; `scripts/generate_slide_images.py:19` chỉ
  import `RealtimeHUD`); bỏ `else 30.0` của `avg_fps` (dòng 330; hiển thị "—"/0 khi chưa đo). Sau khi sửa: nhóm tương ứng thành
  `STALE` → xóa khỏi `KNOWN_VIOLATIONS` (sổ co lại). Nếu bỏ tính năng người dùng có thể đang dùng → hỏi người dùng lúc đó (§7.6).
- 4 nhóm "đề xuất DTG" ở trên: planner quyết định ALLOWED (Lần sửa) hoặc sửa mã (đổi tên / hằng có tên / comment).
- (Tùy chọn, cần `impact` trên `src/inference/ensemble.py`) import lười `get_vsl_dataloaders` trong hàm đánh giá để `augment.py`
  ra khỏi bao đóng phục vụ → 8 khóa ALLOWED augment thành `STALE` → xóa.
- `backend/main.py` docstring route `/api/classes` "(487 classes for Tier 2)" → bỏ số cứng (sau khi nhánh local kế hoạch 06 hợp nhất).
- Guard thứ hai cho scripts đo/báo cáo (luật D + kiểm `generated_by`), §2.4.
- Khi hợp nhất với `feat/vslt-complete`: chạy `tests.test_backend_source_guard` ngay sau merge; nhóm mới → KNOWN (mặc định) hoặc
  planner "Lần sửa" cho ALLOWED.

### Tự kiểm AC

- AC1: `git diff --name-status f16d0a9 HEAD` (xem mục "Kiểm cuối" dưới) chỉ gồm 3 file `A`; `git diff f16d0a9 HEAD -- tests/`
  chỉ là file mới, 0 dòng `-`; không đổi `backend/ src/ scripts/ frontend/ realtime_demo.py run_core.py start_fullstack.ps1
  README.md docs/STATE.md docs/progress_log.md docs/plans/06-* docs/phase12_api.md docs/reviews/*` hay test có sẵn; không có dữ liệu/nhị phân.
- AC2/AC3/AC4/AC6/AC7-a: các lớp test tương ứng OK (B1(5), B2 AC8). AC7-b: `Ran 24 tests in 2.572s` / `2.688s` / `OK`, 0 skip (< 10 s).
  AC7-c: B2 (2 lần chạy báo cáo, thân giống hệt) + `TestReportMode`.
- AC5: a–c OK; d: JSON `git_commit` = commit B1 `319ddcd` (tổ tiên HEAD), `code_dirty: false`, `unregistered: 0`, known/allowed =
  9/36 = dòng in; `git diff 319ddcd HEAD -- tests/test_backend_source_guard.py backend src realtime_demo.py` rỗng (mục "Kiểm cuối").
- AC8: B2 (438 = 414 + 24, tập FAIL/ERROR/skip == B0).
- AC9: mọi commit của kế hoạch có kết quả `detect-changes` trong message; commit B1 có `[DoD7-guard] known=9 allowed=36`; không
  amend/rebase/force-push; `b0_status.txt` rỗng → không có thay đổi chưa commit nào của người dùng để đụng.
- AC10: P10, B0, bảng output thô đầu tiên, phân loại + bằng chứng, đối chiếu dự báo, danh sách vi phạm có sẵn, đề xuất kế hoạch 11,
  đề xuất DTG — đều ở file này; mọi số có nguồn (lệnh + commit hoặc đường dẫn JSON/log).

### Giả định coder tự đặt (để reviewer xét)

1. qualname của phần đầu `def`/`class` (tên, tham số, giá trị mặc định) = chính hàm/lớp đó; decorator thuộc mã bao ngoài;
   phạm vi "seed trước" của giá trị mặc định = phạm vi bao ngoài (vì Python tính mặc định lúc định nghĩa).
2. Số nhiều: ngoài "bỏ `s`" của §3.2, thêm "`ies` → `y`" — cần để mẫu AC2 `dummies = []` (C-name) được báo.
3. C-name còn xét 2 dạng gán tên ngoài danh sách liệt kê: walrus (`:=`, đích là `Name` Store) và `except ... as <tên>`
   (chặt hơn, không nới; hiện 0 finding từ 2 dạng này).
4. B-import còn bắt `from asynctest import ...` (cùng thư viện với `import asynctest`).
5. `torch.seed()` luôn báo (không được miễn bởi `manual_seed` trước), giống `random.seed()`/`np.random.seed()` không đối số.
6. Chuẩn hóa NFC trước khi so regex C-string/D-string (tiếng Việt có thể ở dạng NFD); dùng thêm `shutil`, `unicodedata` (thư viện chuẩn).
7. `generated_by.command` dựng lại từ `PYTHONIOENCODING` + đường dẫn tương đối của `sys.executable` + argv (khớp nguyên văn lệnh §3.7
   khi chạy từ gốc repo bằng `.venv/bin/python`).
8. Thêm lớp `TestReportMode` (ngoài 5 lớp của B1) để máy kiểm §3.7/AC7-c; nó chạy `--report` 2 lần ra thư mục tạm ngoài repo.

### Kiểm cuối (chạy trên cây đã stage cho commit B3; commit B3 chỉ thêm file này)

```
$ git diff --cached --name-status f16d0a9
A	docs/plans/10-progress.md
A	reports/guard_dod7_2026-09-29/guard_findings.json
A	tests/test_backend_source_guard.py
$ git diff --cached f16d0a9 -- tests/ | grep -c "^-[^-]"
0
$ git diff --cached 319ddcd -- tests/test_backend_source_guard.py backend src realtime_demo.py | wc -l
0
```
