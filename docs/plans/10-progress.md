Trạng thái: ĐANG LÀM

# Tiến độ kế hoạch 10 — Guard DoD 7 phía backend

- Kế hoạch: `docs/plans/10-guard-dod7.md`
- Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`)
- P10 (HEAD lúc bắt đầu B1, commit chứa kế hoạch): `f16d0a9` (`f16d0a9d9f717af6c50381732152a58d9ad3c953`)
- Log/file tạm: `/home/user/_plan10_tmp/` (ngoài repo; `../_plan10_tmp/` của kế hoạch)

**Bước đã xong:** B1
**Bước đang làm:** B2 (báo cáo JSON + AC8)
**Bước còn lại:** B2, B3

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
