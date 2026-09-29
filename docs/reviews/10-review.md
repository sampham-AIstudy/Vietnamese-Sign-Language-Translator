# Review kế hoạch 10 — guard DoD 7 phía backend

**Trạng thái: XONG — APPROVE** (reviewer độc lập, 2026-09-29)

- Kế hoạch: `docs/plans/10-guard-dod7.md` (commit kế hoạch f16d0a9)
- Nhánh: `cloud/2026-09-29-viec-a-d`
- Commit coder: 5b979a5, 319ddcd, 0b19f8a, cf23cef
- Phạm vi: `git diff f16d0a9 cf23cef` (HEAD lúc review: 45a324b = cf23cef + d0839c9 docs/cloud_reports + 45a324b khung review; `git diff --stat cf23cef HEAD` chỉ 2 file docs, không mã)

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|-----|---------|------------|
| 1 | Đúng kế hoạch / tiêu chí chấp nhận có test thật | PASS | Xem §1 dưới: AC1–AC10 đối chiếu từng gạch; mọi mẫu AC2 (10 mã, 59 mẫu — đếm bằng `sum(len(v) for v in TestRuleSelfCheck.POSITIVE.values())`) và AC3 (36 mẫu âm — `len(NEGATIVE)`) có trong `POSITIVE`/`NEGATIVE` (`tests/test_backend_source_guard.py:949-1068`); assert thật (assertIn mã luật / assertEqual `[]`, đếm chính xác ở `:1084-1128`). |
| 2 | Tự chạy lại toàn bộ test | PASS | Module mới: `Ran 24 tests in 2.852s` / `OK`, 0 skip. AC8 + r05: `Ran 452 tests in 36.791s` / `FAILED (failures=1, errors=1, skipped=30)` = 414 (B0) + 24 + 14; tập FAIL/ERROR/skip == B0. |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff --name-status f16d0a9 cf23cef` = 3 file `A`; `git diff f16d0a9 cf23cef -- tests/ \| grep -c '^-[^-]'` = 0; file test chỉ có 1 commit (319ddcd). |
| 4 | Nguồn gốc dữ liệu | PASS (N/A dữ liệu ML) | Kế hoạch không train/đánh giá; guard chỉ đọc mã; JSON `note` ghi rõ "counts are code findings, not model metrics". Không có file dữ liệu/nhị phân trong diff. |
| 5 | Rò rỉ split | PASS (N/A) | Không split/train/đánh giá; diff không đụng `src/data/*`, `scripts/create_grouped_splits.py`. |
| 6 | Chọn model bằng VAL; TEST một lần | PASS (N/A) | Không chọn model, không chạy TEST; không đổi model mặc định. |
| 7 | Số liệu truy được | PASS | Mọi số vi phạm (known=9, allowed=36, 24 nhóm, 45 finding, by_rule, serving=44, main=56) trỏ tới `reports/guard_dod7_2026-09-29/guard_findings.json` có `generated_by.command` + `git_commit=319ddcd…` + `code_dirty:false`; reviewer sinh lại ở HEAD 45a324b ra thư mục ngoài repo → thân GIỐNG HỆT. Số test (414/438/24, thời gian) chép từ log `/home/user/_plan10_tmp/*.txt` (đã đọc, khớp) và được reviewer tái lập (§2). |
| 8 | Cỡ mẫu / CI | PASS (N/A) | Không có số liệu ML; JSON `note` nói rõ số đếm là điểm mã, không phải metric. |
| 9 | Nhất quán train–realtime | PASS (N/A) | Không sửa tiền xử lý/mã chạy; `git diff f16d0a9 cf23cef -- src backend realtime_demo.py` rỗng. Test tương đương có sẵn (harmonized_live_equivalence, hand_live_equivalence) vẫn chạy như B0 (§2). |
| 10 | Không Math.random/mock/kết quả giả/hard-code | PASS (với thay đổi của KH10) — DoD 7 backend CHƯA ĐẠT | Diff chỉ thêm file test/docs/JSON, không thêm gì vào đường chính. Guard hoạt động: reviewer tự đột biến trong bộ nhớ 21 mẫu × 5 file SERVING (`backend/main.py`, `src/inference/harmonized_live.py`, `src/inference/predictor.py`, `src/translation/end_to_end.py`, `src/data/harmonized.py`) → cả 21 đều làm guard đỏ đúng mã (§5). 6 mẫu hợp lệ → im lặng. Còn 9 vi phạm có sẵn (danh sách cuối) — đúng thiết kế phương án (ii), sửa ở kế hoạch 11. |
| 11 | Bảo mật | PASS | Không token/kaggle.json/dữ liệu/nhị phân trong diff; JSON không có đường dẫn tuyệt đối (grep `/home`, `/root`, `C:/` → 0 trong JSON; `TestReportMode` assert). subprocess của test dùng danh sách đối số cố định, không `shell=True`, có `timeout`; thư mục tạm ngoài repo, xóa ở tearDown/finally. Không đổi API/CORS/WS (backend không đổi). |
| 12 | So sánh công bằng / GATE không nới | PASS | `set(ALLOWED) == PLAN10_APPROVED_ALLOWED` == đúng 16 khóa bảng §3.6 kế hoạch (`docs/plans/10-guard-dod7.md:283-291`), không khóa ngoài kế hoạch. 4 nhóm ngoài dự báo vào KNOWN (không tự vào ALLOWED). Tập hằng luật (STDLIB_DRAWS 21, NUMPY_NON_GLOBAL 11, TORCH_DRAWS 12, TORCH_INPLACE 8, MOCK_NAMES 8, FAKE_TOKENS 14, RESULT_KEYS 10, METRIC_TOKENS 22, SENTINELS, UNIT_FACTORS, 2 regex C-string, 3 regex D-string) khớp nguyên văn §3.3; các giả định của coder (10-progress:232-244) đều CHẶT hơn hoặc trung tính, không nới. |
| 13 | Kết luận vượt bằng chứng | PASS (có khuyến nghị) | 10-progress:190 và docstring test `:20` ghi rõ DoD 7 backend CHƯA ĐẠT (known=9). Các khẳng định "13/13 dự báo xảy ra, đúng mã, đúng dòng", "backend/main.py 0 finding", "30.0 chỉ khi n < 2" (đúng: `validate_time` bắt timestamp tăng ngặt, `src/inference/sign_segmenter.py:174-180,185,208`) đều kiểm được. Giới hạn âm tính giả cần giữ khi trích dẫn guard: xem §6. |

## §1 — Đối chiếu tiêu chí chấp nhận (mục 1)

| AC | Test / cách kiểm | Kết quả reviewer |
|---|---|---|
| AC1 phạm vi | `git diff --name-status f16d0a9 cf23cef` | `A docs/plans/10-progress.md`, `A reports/guard_dod7_2026-09-29/guard_findings.json`, `A tests/test_backend_source_guard.py`. Không đụng backend/, src/, scripts/, frontend/, realtime_demo.py, run_core.py, start_fullstack.ps1, README.md, docs/STATE.md, docs/progress_log.md, docs/plans/06-*, docs/phase12_api.md, docs/plans/10-guard-dod7.md, docs/reviews/*. 0 dòng `-` trong tests/. |
| AC2 tự kiểm dương | `TestRuleSelfCheck.test_each_rule_fires` (`:1070-1077`) + ca đếm `:1084-1128` | Đối chiếu từng gạch AC2 với `POSITIVE` (`:949-1029`): đủ A-stdlib 5, A-numpy 6, A-torch 5, B-import 4, B-name 3, C-name 7, C-string 5, C-result 6, D-binding 11, D-string 7; `assertEqual(set(POSITIVE), set(RULES))`. A-torch-trong-đối-số-seed kiểm KHÔNG có A-numpy (`:1089-1093`); dict 2 cặp → đúng 2 C-result (`:1095-1097`); 2 chuỗi "mock" → đúng 2 C-string (`:1099-1101`); f-string liền 3 dòng → 1 finding dòng 2 (`:1103-1106`); dòng đúng trong mẫu nhiều dòng (`:1108-1112`). |
| AC3 tự kiểm âm | `test_valid_code_is_silent` (`:1079-1082`) | 36 mẫu `NEGATIVE` (`:1031-1068`) phủ đủ danh sách AC3 (kể cả `"%d%%"`, docstring module/hàm thường, sentinel dict, `WS_MAX_MESSAGE_BYTES`, `ALPHABET_MAX_ABS_COORD`); assert `== []`. |
| AC4 phạm vi | `TestScope` (`:1131-1185`) | a: repo tạm ngoài repo (assert không nằm dưới PROJECT_ROOT), đúng tập 6 file, loại `pkg/unused.py`; b: MIN_SERVING ⊆ SERVING, NOT_SERVING ∩ SERVING = ∅, SERVING ⊆ MAIN, backend/src ⊆ MAIN; c: parse mọi file MAIN; d: `backend.main:app` trong ps1, scripts_realtime == ∅; e: in `[scope] serving=44 main=56`. |
| AC5 cây thật khớp sổ | `TestBackendSourceGuard` (`:1188-1212`) | a: cả 3 danh sách rỗng; b: `len(PLAN10_APPROVED_ALLOWED)==16`, ALLOWED ⊆ đó, giao KNOWN = ∅, count ≥ 1, text khác rỗng; c: in `[DoD7-guard] known=9 allowed=36`. d (reviewer tự kiểm): JSON `git_commit=319ddcd…` là tổ tiên HEAD, `git diff 319ddcd HEAD -- tests/test_backend_source_guard.py backend src realtime_demo.py start_fullstack.ps1 scripts` rỗng, `code_dirty: false`, `unregistered: 0`, known/allowed 9/36 == dòng in; chạy lại lệnh ra thư mục ngoài repo → thân (bỏ `generated_by`) GIỐNG HỆT. e: 9 finding `known` (danh sách ở cuối). |
| AC6 đột biến sổ thật | `TestRegistryComparator` (`:1215-1271`) | 5 đột biến đúng nguyên văn AC6-a nối vào `backend/main.py` trong bộ nhớ, thay finding của file trong F, assert `unregistered` chứa đúng mã + path; sha256 trước/sau bằng nhau. b: nhân đôi khóa KNOWN → `changed` chứa `(key, n, n+1)`; c: bỏ khóa → `stale`; d: nguyên vẹn → rỗng. |
| AC7 nhẹ/nhanh/tất định | `TestImportLight` (`:1274-1283`), `TestReportMode` (`:1286-1314`) | a: subprocess → `[]` (reviewer kiểm thêm trong tiến trình: sau import guard, không có torch/numpy/cv2/mediapipe/fastapi/backend.main/src trong `sys.modules`); b: `Ran 24 tests in 2.852s` OK 0 skip (< 10 s); c: 2 lần `--report` → thân giống hệt, không đường dẫn tuyệt đối. |
| AC8 không hồi quy | lệnh AC8 | Xem mục 2. |
| AC9 quy trình | `git show --format=%B` 4 commit | Mọi commit có dòng `detect-changes` (risk: không có symbol bị ảnh hưởng); 319ddcd có `[DoD7-guard] known=9 allowed=36`; lịch sử tuyến tính; 10-progress:84-98 có tóm tắt `context` cho mọi khóa ALLOWED (+ Grep khi không có caller), file output ở `/home/user/_plan10_tmp/context/*.json` (15 file, ngoài repo). |
| AC10 tài liệu | `docs/plans/10-progress.md` | Có P10, B0, bảng output thô đầu tiên (24 nhóm), phân loại + bằng chứng, đối chiếu dự báo #1–#13, danh sách vi phạm có sẵn (JSON + commit), đề xuất KH11, đề xuất DTG. |

## §2 — Chạy lại test (mục 2)

- `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_backend_source_guard -v` → `Ran 24 tests in 2.852s` / `OK`; không có dòng `skipped`. Coder báo 2.572 s / 2.688 s (log `/home/user/_plan10_tmp/b1_run{1,2}.txt`, đã đọc, khớp).
- Lệnh AC8 (30 module) + `tests.test_archive_private_kaggle_r05` → `Ran 452 tests in 36.791s` / `FAILED (failures=1, errors=1, skipped=30)`.
  - FAIL: `tests.test_frontend_contract.TestFrontendSourceGuard.test_no_violation` (đỏ có chủ đích, kế hoạch 06) — trùng B0.
  - ERROR: `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu checkpoint ViT5) — trùng B0.
  - Tập 30 id skip == tập skip của B0 (`diff` với `/home/user/_plan10_tmp/b0_ac8.txt` rỗng) — skip do thiếu dữ liệu gitignore, KHÔNG coi là pass.
  - 452 = 414 (B0, khớp mốc orchestrator) + 24 (module mới, 24/24 ok) + 14 (r05 của kế hoạch 09, 14/14 ok). Coder báo 438 = 414 + 24 (không chạy r05, đúng lệnh AC8) — nhất quán.
- `git status --porcelain` trước/sau: chỉ `docs/reviews/10-review.md` (file của reviewer); sha256 `backend/main.py`, `realtime_demo.py` không đổi.

## §3 — Test không bị nới (mục 3)
- Không test có sẵn nào bị sửa (0 dòng `-`). Guard không có `skip`/`expectedFailure`. Sổ `KNOWN_VIOLATIONS`/`ALLOWED` lập một lần ở commit B1 319ddcd (`git log --follow -- tests/test_backend_source_guard.py` chỉ 1 commit) và khớp ĐÚNG output thô đầu tiên: reviewer so `/home/user/_plan10_tmp/b1_first_scan.json` (HEAD 5b979a5, 45 finding, cả 45 `unregistered`) với sổ → 24 nhóm, count trùng từng khóa (16 ALLOWED + 8 KNOWN); danh sách finding của bản quét đầu == bản reviewer sinh lại (bỏ status/text).

## §4 — Nhóm 5–9 (ghi chú)
- Mục 7: các số trong `docs/plans/10-progress.md` B1(3) (bảng 24 nhóm) lấy từ `/home/user/_plan10_tmp/b1_first_scan.json` — file NGOÀI repo, không commit (đúng kế hoạch §4 B1(3)). Reviewer đã đọc file đó: `git_commit=5b979a5`, `code_dirty=true` (file test chưa track), 45 finding đều `unregistered`; danh sách finding (bỏ status/text) == bản sinh lại tại HEAD → số tái lập được. Không có số nào không truy được.
- Mục 9 (quan sát, không thuộc phạm vi): fps mặc định khi thiếu metadata là `25.0` ở `src/data/landmark_extractor.py:121` nhưng `30.0` ở `src/data/harmonized.py:129,175`. Nếu một đường (train hoặc live) rơi vào nhánh mặc định thì hai giả định fps khác nhau. Đề nghị planner xét khi quyết "đề xuất DTG" #2 (không phải lỗi của kế hoạch 10).

## §5 — Kiểm riêng (a)–(g)

**(a) Guard FAIL khi có vi phạm.** Script ngoài repo `scratchpad/mutate.py` import guard (chỉ thư viện chuẩn), đọc file từ đĩa, NỐI mẫu trong bộ nhớ, quét lại file đó bằng `scan_source` với bộ luật của nó, thay finding của file trong F, gọi `compare_registry` với sổ thật. sha256 mọi file đích trước/sau bằng nhau (assert trong script); `git status --porcelain` không đổi.
- Trên 5 file SERVING, cả 21 mẫu đều đỏ đúng mã: `random.random()` → A-stdlib; `np.random.rand(3)` (cấp module và trong hàm), `import numpy.random as npr; npr.normal()`, `np.random.random()`, `np.random.default_rng()` → A-numpy; `torch.randn(3)` → A-torch; `from unittest.mock import MagicMock` → B-import; `MagicMock()` → B-name; `@mock.patch` → B-import + B-name; `def predict_sign(x): return {'gloss': 'xin chào', 'confidence': 0.95}` → C-result; route `@app.post('/api/fake')` trả dict cố định → C-result + C-string; `fake_landmarks = np.zeros(...)` → C-name; `'using simulated predictions'` → C-string; `accuracy = 0.87`, `latency_ms = 90.78`, `self.latency_ms = 90.78`, `{'accuracy': 0.87, 'latency_ms': 90.78}`, `_server_ms = latency_ms * 0.4` → D-binding; `'Top-1 91%'`, `f'Top-1 91.2% on {n} clips'` → D-string.
- File ngoài SERVING (`src/training/trainer.py`): chỉ B/D bắt (A/C im lặng) — đúng §3.1 kế hoạch.
- Mẫu hợp lệ trên `backend/main.py` → im lặng: `np.random.default_rng(seed)`, `default_rng(0)` + `rng.normal()`, comment `# accuracy 0.87, Top-1 91%, latency 90.78 ms`, `MAX_FRAMES = 64` / `WINDOW_SIZE = 30` / `CONF_THRESHOLD = 0.45`, `latency_ms = (perf_counter() - t0) * 1000.0`, `torch.Generator().manual_seed(0)` + `generator=`.
- Trên file thật (bộ nhớ): thêm 1 `np.random.rand` vào `KeypointAugmenter.add_jitter` (khóa ALLOWED) → `CHANGED … đăng ký 1, hiện 2`; bỏ chuỗi "mock" khỏi `realtime_demo.py` (mô phỏng sửa) → `STALE` 3 khóa; thêm 1 chuỗi "fake" vào nhánh mock → `CHANGED`.

**(b) Sổ.** `ALLOWED` 16 khóa == `PLAN10_APPROVED_ALLOWED` == bảng §3.6 (đối chiếu từng khóa). Không khóa nào che vi phạm thật trên đường phục vụ:
- augment.py (8 khóa): `KeypointAugmenter` chỉ tạo khi `augment=True` (`src/data/vsl_dataset.py:256`, `src/data/dataset.py:45,113`); module vào bao đóng vì `src/inference/predictor.py:30` → `src/inference/ensemble.py:39` → `vsl_dataset`; `get_vsl_dataloaders` chỉ gọi trong `run_ensemble_benchmark` (`ensemble.py:272`, CLI). Grep `augment|KeypointAugmenter|HarmonizedDataset|VSLDataset|get_vsl_dataloaders` trong backend/main.py, realtime_demo.py, các file phục vụ của src/inference, src/translation: 0 lời gọi (chỉ 1 dòng docstring).
- harmonized.py A-torch/D-binding `HarmonizedDataset.__getitem__` (`:175,178`): Dataset train, không tạo trên đường phục vụ; live gọi `harmonize(..., timestamps_s=ts)` không truyền rng (`src/inference/harmonized_live.py:115`). D-binding `harmonize` (`:129`) là fps ĐẦU VÀO mặc định dùng chung train/live.
- `compute_wer` (`src/metrics/cslr_metrics.py:216`), `validate_split_guards`, `run_ensemble_benchmark`: không gọi từ đường phục vụ. `VSLPredictor.warmup` (`predictor.py:185-191`, `_ = self.model(...)`), `RealtimeLandmarkExtractor.__init__` (`realtime_extractor.py:66-67`): warmup, đầu ra bỏ.
- 4 nhóm ngoài dự báo (`realtime_demo.py:52`, `src/data/landmark_extractor.py:121`, `src/data/vsl_gh_dataset.py:31`, `src/inference/sign_segmenter.py:141`) vào KNOWN với "đề xuất DTG (planner xét)" — đúng quy tắc §3.6, coder không tự vào ALLOWED.
- `KNOWN_VIOLATIONS` 8 nhóm / 9 finding, count trùng output thô đầu tiên.

**(c) Phương án (ii) không thành "nới test".** Sổ lập một lần từ output thô (khớp), test đỏ khi có nhóm mới / đổi số / biến mất (đã chứng minh ở (a) và `TestRegistryComparator` b/c). Tài liệu ghi rõ CHƯA ĐẠT (10-progress:190; docstring test :17-20; báo cáo cloud d0839c9). Giới hạn: quy tắc "chỉ co" hiện do reviewer kiểm (`git log -p`), máy chưa kiểm — khuyến nghị K1.

**(d) Tập SERVING.** 44 file (JSON `scope.serving_files`), gồm mọi import lười của `backend/main.py` (end_to_end, alphabet_mlp, alphabet_temporal, alphabet_preprocessing) và `realtime_demo.py` (translator). Reviewer kiểm chéo bằng resolver regex độc lập: không import nào từ file SERVING trỏ tới file repo ngoài SERVING. Không có `importlib`/`__import__` trên đường phục vụ ngoài `src/inference/__init__.py:22` (bảng `_LAZY` trỏ tới 4 module đã có trong bao đóng). `sys.path.insert` chỉ thêm PROJECT_ROOT. Ngoài SERVING (12 file MAIN): `src/training/*`, `src/export/*`, `src/data/{dataset,extract_landmarks,sequence_generator}.py`, `src/translation/{dataset,metrics}.py` — không file phục vụ nào import chúng. `scripts/`: backend không import, không subprocess; `start_fullstack.ps1`, `start_clean.sh`, `start_clean.bat` chỉ chạy `uvicorn backend.main:app`. `run_core.py` (CLI gốc, ngoài phạm vi theo kế hoạch §2.4) chỉ import `src.translation.end_to_end` + `realtime_demo` (đều trong SERVING) và tự nó 0 finding khi reviewer quét thử.

**(e) Nhẹ/nhanh/0 skip.** Import guard trong tiến trình: không có torch/numpy/cv2/mediapipe/fastapi/backend.main/src trong `sys.modules`; `TestImportLight` OK; `Ran 24 tests in 2.852s`, 0 skip.

**(f) Phạm vi file.** Đúng 3 file `A`; 0 dòng `-` trong tests/; không đụng file cấm nào (backend/main.py, frontend/src/**, scripts/smoke_test_phase12.py, docs/phase12_api.md, docs/plans/06-*, docs/STATE.md, docs/progress_log.md, docs/plans/10-guard-dod7.md); không sửa mã nguồn chính. GitNexus `node .gitnexus/run.cjs detect-changes --scope compare --base-ref f16d0a9 --repo .` → "Diff touched 5 file(s) but no indexed symbols overlap those hunks" (3 file KH10 + báo cáo cloud + file review; không symbol có sẵn nào bị ảnh hưởng).

**(g) Số liệu.** Xem mục 7.

## §6 — Giới hạn âm tính giả (không FAIL; thuộc thiết kế kế hoạch §6, nêu để không trích dẫn quá mức)
Reviewer thử trên `backend/main.py` (bộ nhớ), các mẫu sau KHÔNG bị báo: `{'label': 'A', 'score': 0.93}` (backend thật có khóa `"label"` ở `backend/main.py:418,451`), `{'text': 'xin chào'}`, `def get_sign(x): return 'xin chào'` (tên hàm không có token predict/translate/…), `from random import *` + `random()`, `getattr(random, 'random')()`, `rng = default_rng(0); confidence = rng.uniform()`, `confidence = time.time() % 1`, `frame = np.zeros((720,1280,3))` (khung tổng hợp không có chữ fake/mock), `elapsed = 90.78`. Vì vậy "guard xanh và known=0" là điều kiện CẦN của vế guard DoD 7 backend, không phải bằng chứng "không có kết quả giả".

## Kết luận

**APPROVE** — 13/13 PASS (mục 4–6, 8–9 là N/A cho kế hoạch chỉ-guard), không còn FAIL.

Khuyến nghị (không chặn; xếp theo mức độ):
1. **K1 (trung bình-thấp, cần PLANNER):** máy hóa quy tắc "sổ chỉ co": thêm hằng trần (ví dụ `PLAN10_B1_COUNTS` = count các khóa lúc B1) và assert `set(KNOWN_VIOLATIONS) ⊆ trần`, `count ≤ trần` (và tương tự trần count cho ALLOWED). Hiện một coder tương lai (ví dụ kế hoạch 08 sửa `SignSegmenter._activity`) có thể tăng count/thêm mục mà test vẫn xanh; chỉ reviewer `git log -p` bắt được.
2. **K2 (thấp):** `TestRegistryComparator._registered_key` (`tests/test_backend_source_guard.py:1235-1238`) FAIL khi cả hai sổ rỗng — tức trạng thái lý tưởng sau khi sửa hết sẽ làm test b/c đỏ. Nên dùng sổ tổng hợp trong bộ nhớ cho AC6-b/c khi cả hai rỗng (cần planner vì là sửa test).
3. **K3 (thấp, planner xét ở lần sửa sau):** mở rộng luật cho các âm tính giả ở §6 (khóa `label`/`score`/`text`, `from random import *`, `np.random.SeedSequence()` không entropy) và thêm `start_clean.sh`/`start_clean.bat` vào tiêu chí R2 (hiện không đổi kết quả vì chỉ chạy `backend.main:app`).
4. **K4 (quan sát, planner xét cùng "đề xuất DTG" #2):** fps mặc định 25.0 (`src/data/landmark_extractor.py:121`) ≠ 30.0 (`src/data/harmonized.py:129,175`).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có cho kế hoạch 10. (Việc bỏ chế độ `--source mock` của `realtime_demo.py` ở kế hoạch 11 có thể cần hỏi người dùng LÚC ĐÓ theo §7.6; 4 "đề xuất DTG" là việc của planner, không phải người dùng.)

## Danh sách vi phạm có sẵn reviewer xác nhận (file:dòng:luật [qualname]) — từ JSON 319ddcd, tái lập tại HEAD 45a324b
1. `realtime_demo.py:52:C-result [RealtimeHUD._locate_vietnamese_font]` — `candidates = [` (danh sách đường dẫn font; đề xuất DTG)
2. `realtime_demo.py:266:C-string [RealtimeDemo._open_stream]` — `elif self.source == "mock":`
3. `realtime_demo.py:267:C-string [RealtimeDemo._open_stream]` — `print("Using Synthetic Mock Video Stream for Smoke Test...")`
4. `realtime_demo.py:294:C-string [RealtimeDemo.run]` — `if self.source == "mock":` (khung tổng hợp `np.zeros` + `cv2.circle`, `:295-297`)
5. `realtime_demo.py:330:D-binding [RealtimeDemo.run]` — `avg_fps = ... if fps_tracker else 30.0`
6. `realtime_demo.py:395:C-string [main]` — help `--source ... or 'mock'`
7. `src/data/landmark_extractor.py:121:D-binding [CleanHolisticExtractor.extract_from_video]` — `fps = cap.get(cv2.CAP_PROP_FPS) or 25.0` (đề xuất DTG)
8. `src/data/vsl_gh_dataset.py:31:D-string [<module>]` — chuỗi ghi chú cấp module "100% identical" (dòng 58) (đề xuất DTG)
9. `src/inference/sign_segmenter.py:141:D-binding [SignSegmenter._activity]` — `... else 30.0` (chỉ khi n < 2; đề xuất DTG)

Tổng: 9 finding / 8 nhóm (known=9, allowed=36, unregistered=0). DoD 7 phần backend: **guard có, CHƯA ĐẠT**.
