# Kế hoạch 10 — Guard DoD 7 phía backend (không random / mock / giả lập / số hard-code trong đường chính)

Trạng thái: XONG (chờ orchestrator)

- Nhánh: cloud/2026-09-29-viec-a-d (việc D trong docs/STATE.md) | HEAD khi lập (theo orchestrator): 04ec565 | Ngày: 2026-09-29
- **Không có điểm dừng CẦN NGƯỜI DÙNG** (§7; chỉ có điểm dừng có điều kiện trong lúc làm).
- Planner chỉ đọc mã nguồn, không chạy lệnh (không có Bash). Mọi danh sách "ứng viên" ở §2 là kết quả Grep/đọc tay của
  planner, KHÔNG phải số liệu: danh sách chính thức là output của guard (§5 AC5), coder sinh ra.

## 1. Mục tiêu và DoD

**Mục tiêu.** Thêm một test guard tĩnh (AST, không import torch/mediapipe) quét mã nguồn chính phía Python: `backend/`,
`src/`, và mọi file mà đường phục vụ người dùng thực sự import. Guard FAIL khi có (a) RNG không seed trên đường phục vụ,
(b) thư viện mock, (c) dữ liệu/kết quả giả lập hoặc tổng hợp trên đường phục vụ, (d) số liệu hiệu năng gõ tay. Vi phạm có
sẵn được liệt kê bằng chính output của guard. Việc này KHÔNG sửa vi phạm nào (việc sửa là kế hoạch sau).

**DoD phục vụ.** DoD 7, vế "Có test guard FAIL nếu mã nguồn chính chứa Math.random / dữ liệu giả lập / số liệu hard-code"
— phần backend/Python. Phần frontend đã có ở kế hoạch 06 AC8 (`tests/test_frontend_contract.py`, `TestGuardSelfCheck` +
`TestFrontendSourceGuard`). DoD 6 ("không có kết quả giả ở bất kỳ chế độ nào") được hưởng lợi gián tiếp. Mục 10 của
bảng review ("Không random/mock/số giả") sau việc này có bằng chứng tự động thay cho grep tay của reviewer.

**Không thuộc việc này:** sửa vi phạm (đề xuất ở §4 "Sau kế hoạch này", thành kế hoạch sau); guard cho scripts đo/báo cáo
(đề xuất backlog, §2.4); DoD 7 các vế còn lại (e2e, tương đương train↔live).

## 2. Hiện trạng (đọc tại cây làm việc của nhánh cloud, 2026-09-29)

### 2.1 Guard đã có (frontend, kế hoạch 06) — mẫu để làm nhất quán
- `tests/test_frontend_contract.py:30-39` `GUARD_RULES` = danh sách (tên luật, regex); `:42-49` `guard_violations(text,
  name)` trả `[(name, line_no, rule)]` theo từng dòng; `:52-56` duyệt `frontend/src/**/*.{js,jsx}` bằng `glob`.
- `:59-92` `TestGuardSelfCheck`: mỗi luật có một mẫu vi phạm là CHUỖI TRONG BỘ NHỚ (`SAMPLES`), `test_each_rule_fires`
  kiểm tập tên luật trong mẫu == tập luật, rồi từng mẫu phải bị báo; `test_allowed_code`: mẫu hợp lệ → `[]`.
- `:95-105` `TestFrontendSourceGuard.test_no_violation`: quét cây thật, `assertEqual(found, [])`, thông báo lỗi dạng
  `file:dòng: luật` (đường dẫn tương đối, `/`).
- Kế hoạch 06 AC8 (`docs/plans/06-viec5-frontend.md:499-503`): không ngoại lệ theo file. §0.3 (`:35-46`): guard được đỏ
  ở mốc TRUNG GIAN B4–B6 với tập vi phạm (file + mẫu, không theo số dòng) không tăng; phải xanh khi ĐÓNG việc (từ B7).
- Guard frontend dùng regex theo dòng (JS). Với Python, regex theo dòng không phân biệt được comment/docstring,
  `self.random_scale(...)` với module `random`, hay seed đặt trước trong cùng hàm → kế hoạch này dùng AST (§3.2).

### 2.2 Đường chính (đường phục vụ người dùng) — điểm vào và phạm vi import
- `start_fullstack.ps1:13`: chỉ chạy `uvicorn backend.main:app` (+ `npm run dev`). README §5.3 (`README.md:186`) cùng
  điểm vào. README §5.4 (`README.md:199-207`): demo realtime desktop `realtime_demo.py --webcam 0` / `--video ...` — đây
  là đường phục vụ người dùng thứ hai (webcam → dự đoán → HUD).
- `backend/main.py` chỉ import mã dự án từ `src.*`: `:99-105` (predictor, realtime_pipeline, smoother, harmonized_live,
  sign_segmenter, hand_live), `:218` (lười: `src.translation.end_to_end`), `:585` (fingerspelling_compose), `:622`, `:626`
  (lười: `src.models.alphabet_mlp`, `alphabet_temporal`), `:800` (lười: `src.data.alphabet_preprocessing`). Không import
  gì từ `scripts/` (Grep "scripts" trong `backend/main.py`: chỉ một docstring ở `:359`).
- `realtime_demo.py:28-31` import predictor, realtime_extractor, realtime_pipeline, smoother; `:250` lười
  `src.translation.translator`.
- Bao đóng import tĩnh (planner tự lần theo Grep `^from src|^import src`; guard phải TỰ TÍNH, §3.1):
  `src/inference/{predictor, realtime_pipeline, realtime_extractor, smoother, harmonized_live, sign_segmenter, hand_live,
  fingerspelling_compose, ensemble}.py`; `src/models/{stgcn_model, graph, stgcn, transformer_model, baseline_bigru,
  alphabet_mlp, alphabet_temporal, cslr_stgcn_bigru}.py`; `src/data/{vsl_dataset, collate, landmark_extractor, augment,
  harmonized, alphabet_preprocessing, vsl_gh_dataset, lexicon_bank}.py` + `src/data/preprocessing/*.py`;
  `src/metrics/{metrics, cslr_metrics}.py`; `src/translation/{end_to_end, translator, text_normalizer,
  cslr_recognizer}.py`; cùng các `__init__.py` của gói. Chú ý: `src/inference/ensemble.py:39` import
  `src.data.vsl_dataset.get_vsl_dataloaders` ở đầu module → `src/data/vsl_dataset.py:26` kéo `src/data/augment.py`
  (augmentation lúc train) vào tiến trình phục vụ, dù không hàm phục vụ nào gọi tới nó.
- NGOÀI bao đóng: `src/training/*`, `src/export/*`, `src/data/{dataset, extract_landmarks, sequence_generator}.py`,
  `src/translation/{dataset, metrics}.py`.

### 2.3 Ứng viên vi phạm hiện có (Grep của planner; chỉ để dự báo — danh sách chính thức do guard sinh, §5 AC5)
Quy ước cột "Phân loại": **VI PHẠM** = đúng là vi phạm DoD 7 → vào danh sách `KNOWN_VIOLATIONS` (§3.6), sửa ở kế hoạch
sau; **DTG** = dương tính giả theo ngữ nghĩa → vào `ALLOWED` (§3.6) với lý do; **ngoài luật** = không khớp luật §3.3 theo
thiết kế (ghi để reviewer thấy planner đã xét).

| # | Vị trí (file:dòng, hàm) | Trích đoạn | Luật §3.3 | Phân loại |
|---|---|---|---|---|
| 1 | `realtime_demo.py:266-267` `RealtimeDemo._open_stream` | `elif self.source == "mock":` / `print("Using Synthetic Mock Video Stream for Smoke Test...")` | C-string | **VI PHẠM**: chế độ nguồn giả (khung đen + hình tròn, `:294-297`) trong điểm vào phục vụ người dùng |
| 2 | `realtime_demo.py:294` `RealtimeDemo.run` | `if self.source == "mock":` | C-string | **VI PHẠM** (cùng tính năng #1) |
| 3 | `realtime_demo.py:395` `main` | help `"... or 'mock'"` | C-string | **VI PHẠM** (cùng tính năng #1) |
| 4 | `realtime_demo.py:330` `RealtimeDemo.run` | `avg_fps = ... if fps_tracker else 30.0` | D-binding (nhánh IfExp) | **VI PHẠM**: FPS 30 gõ tay hiển thị trên HUD nếu nhánh đó chạy (hiện không tới được vì vừa `append`, nhưng vẫn là số hiển thị không đo) |
| 5 | `src/data/augment.py:34..188` `KeypointAugmenter.{add_jitter, random_scale, random_rotate_2d, time_warp, keypoint_mask, augment_sequence, augment_static, augment_vsl_sequence}` | `np.random.normal/uniform/rand/choice(...)` | A-numpy | **DTG**: augmentation chỉ khi `augment=True` (`src/data/vsl_dataset.py:256`, `src/data/dataset.py:45,113`); đường phục vụ không tạo dataset; module chỉ nằm trong bao đóng do import đầu module (§2.2) |
| 6 | `src/data/harmonized.py:178` `HarmonizedDataset.__getitem__` | `np.random.default_rng(int(torch.randint(...))) if self.augment else None` | A-torch | **DTG**: nhánh augment của Dataset train; live gọi `harmonize(..., rng=None)` (`src/inference/harmonized_live.py`, kế hoạch 04 AC2) |
| 7 | `src/data/harmonized.py:175` `HarmonizedDataset.__getitem__` | `fps = 30.0` | D-binding | **DTG**: tốc độ khung hình ĐẦU VÀO mặc định khi npz thiếu metadata, không phải số đo |
| 8 | `src/data/harmonized.py:129` `harmonize` | `fps = float(fps) if fps and fps > 0 else 30.0` | D-binding (IfExp) | **DTG**: như #7 (tham số tiền xử lý dùng chung train/live) |
| 9 | `src/metrics/cslr_metrics.py:216` `compute_wer` | `wer = 100.0 if total_hyp_words > 0 else 0.0` | D-binding (IfExp) | **DTG**: quy ước công thức WER khi không có từ tham chiếu, không phải số gõ tay |
| 10 | `src/data/vsl_dataset.py:176` `validate_split_guards` | f-string `"... confounded with 100% dialect ..."` | D-string (%) | **DTG**: câu báo lỗi kiểm toàn vẹn split |
| 11 | `src/inference/ensemble.py:303` `run_ensemble_benchmark` | `print("... (50% ST-GCN + 50% Transformer) ---")` | D-string (%) | **DTG**: mô tả trọng số 0.5/0.5 của hàm đánh giá offline, không phải số đo |
| 12 | `src/inference/predictor.py:185-187` `VSLPredictor.warmup` | `dummy_seq/dummy_jm/dummy_tm = torch.zeros/ones(...)` | C-name | **DTG**: warmup, kết quả bỏ (`_ = self.model(...)`, `:191`), không tới người dùng |
| 13 | `src/inference/realtime_extractor.py:66` `RealtimeLandmarkExtractor.__init__` | `dummy = np.zeros((256,256,3))`; `self.holistic.process(dummy)` | C-name | **DTG**: warmup, kết quả bỏ; khung đen không có người → tracker không giữ landmark |
| 14 | `backend/main.py:116` | comment `# ... (0% on HCMUE, 0/31 cross-source clips)` | — | **ngoài luật**: comment (AST không thấy); số lấy từ báo cáo, ghi chú cho dev |
| 15 | `backend/main.py:531` docstring route `/api/classes` | `"(487 classes for Tier 2)"` | — | **ngoài luật**: số lớp, không phải số đo hiệu năng (không khớp D-string). Ghi nhận: docstring route hiển thị ở `/docs`; đề xuất bỏ số cứng ở kế hoạch sau (cùng tinh thần AC8 "25 lớp") |
| 16 | `backend/main.py:1083`, `:1085`, `:1092`, `:1243` | `infer_ms = 0.0`; `.get("latency_ms", 0.0)`; `... else 0.0` | — | **ngoài luật**: giá trị 0 = "không có phép đo", không phải số giả (review 04 mục 10 đã kiểm các `*_ms` đo bằng `perf_counter`) |
| 17 | `src/export/export_onnx.py:63,167` `torch.randn` + `dummy_*`; `src/export/onnx_predictor.py:74-77` `dummy_*`, `:186-187` `np.random.seed(42)` + `randn` | — | — | **ngoài luật**: ngoài bao đóng phục vụ (luật A/C chỉ áp cho bao đóng, §3.1); `:186-187` có seed trong cùng hàm |
| 18 | `src/training/train_cslr.py:54-59, 223, 330` `set_seed`; `src/translation/dataset.py:34-35` `random.Random(seed)` | — | — | **ngoài luật**: ngoài bao đóng; có seed |

Kết luận dự báo: `backend/main.py` KHÔNG có ứng viên nào khớp luật §3.3 tại cây hiện tại (máy local đang sửa file này theo
kế hoạch 06; nếu guard báo gì trong file này thì CHỈ liệt kê, không sửa — §7). Không thấy `unittest.mock`/`MagicMock` trong
`backend/` hay `src/` (Grep "mock" trong `src/`: 0 dòng; trong `backend/`: 0 dòng).

### 2.4 `scripts/` — tiêu chí phân loại và danh sách
**Tiêu chí "script phục vụ realtime" (thuộc phạm vi guard):** (R1) nằm trong bao đóng import tĩnh của một điểm vào phục vụ
(§3.1), hoặc (R2) được `start_fullstack.ps1` gọi. README §5.3–5.4 (cách chạy hệ thống) chỉ nêu `backend.main:app` và
`realtime_demo.py` (ở gốc repo, KHÔNG thuộc `scripts/`).
**Kết quả tại cây hiện tại: KHÔNG có script nào trong `scripts/` thỏa R1 hoặc R2** (backend không import `scripts/`;
`start_fullstack.ps1` không gọi script). Guard phải tự tính lại tập này mỗi lần chạy và so với hằng khai báo
`SCRIPTS_REALTIME = ()` (§3.1), để khi backend bắt đầu import một script thì phạm vi tự mở rộng và test báo.

Các nhóm ngoài phạm vi (công cụ offline; lý do: không chạy khi phục vụ người dùng):
- Kiểm thử/khói (client gọi backend hoặc chạy pipeline với đầu vào thử): `smoke_test_phase6.py`, `smoke_test_phase10.py`
  (`:53` `np.random.randn` làm đầu vào khói — công cụ test, hợp lệ ngoài đường chính), `smoke_test_phase12.py` (kế hoạch 06
  B7 đang viết lại), `audit_realtime.py`.
- Đo/báo cáo (sinh số liệu): `hand_live_check.py`, `live_segment_check.py`, `live_clip_sample.py` (seed), `report_step4.py`,
  `report_unified.py`, `report_alphabet_nested.py`, `benchmark_onnx.py`, `compare_isolated_models.py`, `evaluate_cslr_s06.py`,
  `evaluate_translation_phase4b.py`, `source_diagnostics.py`, `trim_rest_eval.py`, `cross_source_dtw.py`, `shortcut_85.py`,
  `alphabet_ckpt_provenance.py`, `analyze_alphabet_signers.py`, `analyze_raw_dataset.py`, `simulate_cslr_streaming.py`
  (mô phỏng streaming OFFLINE trên dữ liệu thật, sinh `reports/audit_round2/cslr_streaming_simulation.json`).
- Train: `train_unified.py`, `train_alphabet_real.py`, `train_alphabet_nested.py`, `train_translation_stage1.py`,
  `train_translation_stage2.py`.
- Chuẩn bị/trích dữ liệu: `extract_hands_batch.py` (phía "train" của tương đương Cấp 1; `hand_live.py` phải khớp kwargs —
  kế hoạch 06 AC4-a), `extract_keypoints_batch.py`, `extract_cslr_predictions.py`, `build_alphabet_tasks.py`,
  `build_label_inventory.py`, `build_recording_groups.py`, `build_unified_manifest.py` (`random.Random(args.seed)`),
  `create_grouped_splits.py` (`random.Random(args.seed)`), `prepare_canonical_translation.py`, `prepare_canonical_vsl_gh.py`,
  `clean_10k_translation_corpus.py`, `export_vslgh_segments.py`, `crawl_tudienngonngukyhieu.py`.
- Sinh dữ liệu tổng hợp đã bị chặn: `record_vsl_alphabet.py` (README:50; `data/vsl_alphabet_pilot/DO_NOT_TRAIN_SYNTHETIC.md`).
- Lưu trữ/hạ tầng/trình bày: `archive_step4_kaggle.py`, `archive_private_kaggle.py`, `cloud_setup.sh`,
  `generate_slide_images.py` (import `RealtimeHUD` từ `realtime_demo.py`), `render_cross_source.py`, `take_screenshots.cjs`.
- Ngoài `scripts/` cũng ngoài phạm vi: `run_core.py` (CLI ở gốc, không có trong README/`start_fullstack.ps1`), `train.py`,
  `evaluate_test.py` (train/đánh giá), `kaggle/**` (kernel train), `reports/**/*.py` (script lịch sử; lưu ý
  `reports/audit_round2/run_v1_latency.py` từng tổng hợp số bịa 0.4/0.6 — review 04 mục 10; đã có trong backlog 7 STATE).
- **Đề xuất backlog (không làm ở đây):** guard thứ hai cho nhóm "Đo/báo cáo" chỉ với luật D (số gõ tay) + kiểm JSON có
  `generated_by`, vì đó là nơi số liệu công bố được sinh ra.

### 2.5 Thiếu
- Không có guard Python nào; reviewer kiểm mục 10 bằng grep tay trên diff (review 04 mục 10, review 05 mục 10).
- Không có cơ chế ghi nhận vi phạm có sẵn để chúng không tăng mà không làm đỏ cả bộ test.
- `tests/test_backend_source_guard.py` chưa tồn tại (Glob `tests/*.py`: 29 file, không trùng tên; không có
  `tests/__init__.py` — gói namespace, `python -m unittest tests.<module>` vẫn chạy như các module khác).

## 3. Thiết kế

### 3.0 Tổng quan, luồng dữ liệu, hợp đồng
Một file mới `tests/test_backend_source_guard.py`, CHỈ dùng thư viện chuẩn (`ast`, `re`, `os`, `glob`, `json`,
`collections`, `tempfile`, `subprocess`, `sys`, `datetime`, `unittest`). Không import `numpy`, `torch`, `cv2`,
`mediapipe`, `fastapi`, không import `backend.main` hay bất kỳ module nào của `src/` (chỉ ĐỌC file dạng văn bản).

Luồng: `ENTRYPOINTS` → `serving_closure()` → tập SERVING → hợp với glob `backend/**/*.py`, `src/**/*.py` → tập MAIN →
mỗi file: đọc UTF-8, `ast.parse` → áp luật theo phạm vi (A, C nếu file ∈ SERVING; B, D cho mọi file ∈ MAIN) → danh sách
`Finding` → gom nhóm theo khóa `(path, rule, qualname)` → so với sổ đăng ký `ALLOWED` + `KNOWN_VIOLATIONS` (§3.6).

Hợp đồng hàm (tên bắt buộc để AC gọi được; coder có thể thêm hàm phụ):
- `Finding` = namedtuple `(path, line, rule, qualname, snippet)`: `path` tương đối từ gốc repo, dấu `/`; `line` ≥ 1;
  `rule` ∈ 10 mã luật §3.3; `qualname` như §3.2; `snippet` = dòng nguồn đã `strip()`, cắt ≤ 160 ký tự.
- `scan_source(text: str, path: str, rules: frozenset[str]) -> list[Finding]` — hàm THUẦN (không đọc đĩa), dùng cho tự kiểm.
  `SyntaxError` được ném ra (không nuốt).
- `serving_closure(root: str, entrypoints: tuple[str, ...]) -> list[str]` — đường dẫn tương đối, đã sắp xếp.
- `main_scope(root: str, serving: list[str]) -> list[str]`.
- `scan_repo(root: str = PROJECT_ROOT) -> tuple[list[Finding], dict]` — dict phạm vi `{entrypoints, serving_files,
  main_files, scripts_realtime}`.
- `compare_registry(findings, allowed, known) -> dict` với 3 khóa `unregistered` (list Finding không thuộc khóa nào đã
  đăng ký), `changed` (list `(key, registered_count, current_count)` với current > 0 và khác), `stale` (list `(key,
  registered_count)` với current = 0). Guard "xanh" ⇔ cả 3 rỗng.
- "Mã lỗi" = thông điệp FAIL của test: mỗi dòng `path:line: RULE [qualname] snippet` (unregistered), hoặc
  `CHANGED path RULE qualname: đăng ký N, hiện M`, hoặc `STALE path RULE qualname: đăng ký N, hiện 0`.
- `python -m tests.test_backend_source_guard --report <out.json>`: ghi báo cáo §3.7, exit 0 (chế độ báo cáo, không phải
  test); không có `--report` → `unittest.main()`.

Chỗ dùng module tiền xử lý chung: KHÔNG áp dụng (guard không đọc dữ liệu, không chạy tiền xử lý hay model).

### 3.1 Phạm vi
- `ENTRYPOINTS = ("backend/main.py", "realtime_demo.py")`. Lý do: `backend.main:app` là đích uvicorn của
  `start_fullstack.ps1:13` (test assert file này chứa đúng chuỗi `backend.main:app`); `realtime_demo.py` là cách chạy
  realtime thứ hai mà README §5.4 hướng dẫn người dùng. Không gắn test vào nội dung README (README có thể đổi ở nhánh local).
- **SERVING** = bao đóng import tĩnh của `ENTRYPOINTS`, tự tính mỗi lần chạy:
  - duyệt MỌI nút `ast.Import`/`ast.ImportFrom` trong file, kể cả trong thân hàm (import lười như `backend/main.py:218`);
  - `import a.b.c` → thử các module `a`, `a.b`, `a.b.c`; `from a.b import x` → thử `a`, `a.b`, `a.b.x` (x có thể là module
    con); import tương đối (`level ≥ 1`) giải theo gói của file hiện tại;
  - module → file: `<root>/a/b.py` hoặc `<root>/a/b/__init__.py`, thử lần lượt 2 gốc `PROJECT_ROOT` và
    `PROJECT_ROOT/scripts` (gốc thứ hai mô phỏng `sys.path.insert(scripts)`); không tìm thấy → bỏ qua (thư viện ngoài/chuẩn);
  - khi thêm `a/b/c.py` thì thêm cả `a/__init__.py`, `a/b/__init__.py` nếu tồn tại (Python chạy chúng khi import);
  - lặp tới điểm bất động; KHÔNG giải `importlib.import_module`/`__import__` động (giới hạn ghi ở §6; bảng lười của
    `src/inference/__init__.py:12-17` trỏ tới các module vốn đã nằm trong bao đóng).
- **MAIN** = `glob backend/**/*.py` ∪ `glob src/**/*.py` ∪ SERVING (bỏ `__pycache__`). Mọi file SERVING ⊂ MAIN.
- `SCRIPTS_REALTIME = ()` (hằng khai báo). Tập tính được = {file SERVING bắt đầu bằng `scripts/`} ∪ {đường dẫn khớp
  `scripts[\\/][\w.-]+\.py` trong `start_fullstack.ps1`}. Test assert tập tính được == `set(SCRIPTS_REALTIME)`; lệch →
  FAIL "phạm vi scripts đổi — CẦN PLANNER" (không tự sửa hằng).
- `MIN_SERVING` (chống pass rỗng — resolver hỏng sẽ trả tập nhỏ): SERVING phải chứa `backend/main.py`, `realtime_demo.py`,
  `src/inference/predictor.py`, `src/inference/realtime_pipeline.py`, `src/inference/harmonized_live.py`,
  `src/inference/hand_live.py`, `src/inference/sign_segmenter.py`, `src/inference/fingerspelling_compose.py`,
  `src/data/harmonized.py`, `src/data/alphabet_preprocessing.py` (import lười), `src/models/alphabet_temporal.py` (import
  lười), `src/translation/end_to_end.py` (import lười), `src/translation/translator.py`. Và SERVING KHÔNG chứa
  `src/training/trainer.py`, `src/export/export_onnx.py` (hai file không ai trên đường phục vụ import).
- Phạm vi luật: A (RNG) và C (giả lập) → SERVING; B (mock) và D (số gõ tay) → MAIN. Lý do: A/C là vấn đề khi CHẠY
  phục vụ (augment lúc train, input giả để trace ONNX ở `src/export` là hợp lệ ngoài đường phục vụ); mock và số liệu gõ
  tay thì không có chỗ hợp lệ nào trong mã nguồn chính.

### 3.2 Phân tích AST: qualname, docstring, chuỗi, cách đếm
- Mỗi file: `open(..., encoding="utf-8")` → `ast.parse(text, filename=path)`. `SyntaxError`/`UnicodeDecodeError` →
  test FAIL (không skip).
- `qualname`: ghép tên các `ClassDef`/`FunctionDef`/`AsyncFunctionDef` bao quanh bằng `.` (ví dụ
  `KeypointAugmenter.add_jitter`, `validate_split_guards.get_dialects`); mã cấp module → `<module>`; lambda thuộc hàm bao.
- Docstring = câu lệnh đầu `Expr(Constant(str))` của Module/ClassDef/FunctionDef/AsyncFunctionDef → KHÔNG xét ở C-string
  và D-string, TRỪ docstring của hàm có decorator route FastAPI (`@<obj>.get|post|put|patch|delete|websocket|api_route(...)`)
  — FastAPI hiển thị chúng ở `/docs`, tức là chữ người dùng thấy.
- Comment: AST không chứa → tự động không xét (ví dụ §2.3 #14).
- **Đơn vị chuỗi** (xét ở C-string/D-string): một `ast.Constant` kiểu `str` đứng riêng (không phải docstring như trên),
  hoặc MỘT `ast.JoinedStr` (f-string; các f-string viết liền nhau được Python gộp thành một nút) với các phần hằng nối
  lại, mỗi chỗ nội suy thay bằng `{}`. KHÔNG xét phần `format_spec` (ví dụ `.1f`) và biểu thức nội suy (là mã, luật khác
  xét). `bytes` không xét. Mỗi đơn vị khớp một luật → đúng 1 Finding (dù khớp nhiều mẫu), `line` = `lineno` của nút.
- **Cách đếm Finding:** A-*: mỗi lời gọi; B-import: mỗi câu import; B-name: mỗi lần xuất hiện tên; C-name: mỗi điểm gán;
  C-string/D-string: mỗi đơn vị chuỗi; C-result: mỗi cặp khóa–giá trị / phép gán / `return`; D-binding: mỗi đích gán /
  khóa dict / keyword / tham số mặc định.
- Tách token định danh (dùng cho C-name, C-result, D-binding): tách theo `_` và ranh giới camelCase, hạ chữ thường; ghép
  một token 1–3 chữ cái đứng NGAY trước một token toàn số thành một token (`top_1`/`top1` → `top1`, `f1`, `p95`;
  `bleu_4` → `bleu`, `4`); số nhiều: token kết thúc `s` mà bỏ `s` thì thuộc tập → coi là thuộc tập.
- Bí danh import (theo file, gom từ mọi Import/ImportFrom): `import random [as r]`, `from random import f [as g]`;
  `import numpy [as np]`, `import numpy.random [as npr]`, `from numpy import random [as npr]`,
  `from numpy.random import f [as g]`; `import torch [as t]`, `from torch import f [as g]`, `from torch import nn`,
  `import torch.nn as nn`, `from torch.nn import init`, `import torch.nn.init as init`. Hàm gọi được chuẩn hóa thành
  tên chấm đầy đủ (ví dụ `numpy.random.rand`, `torch.randn`, `random.choice`, `torch.nn.init.normal_`); gọi trên đối
  tượng không phân giải được (ví dụ `rng.normal`, `self.random_scale`) KHÔNG được coi là hàm của module RNG.

### 3.3 Luật (10 mã; mỗi Finding mang đúng một mã)
Hằng dùng chung: `SENTINELS = {0, -1}` (so bằng số, gồm 0.0/-1.0; `bool` không phải số);
`UNIT_FACTORS = {1, 100, 1000, 1_000_000, 0.01, 0.001, 1e-6, 60, 3600}`;
"số gõ tay" (H) = `Constant` số (không bool) ∉ SENTINELS; `UnaryOp(+/-)` trên hằng số (tính giá trị rồi xét như trên);
`Constant` str toàn số khớp `^\s*[-+]?\d+(?:[.,]\d+)?\s*%?\s*$`; `BinOp` mà mọi toán hạng đều là hằng số;
`IfExp` có nhánh `body` hoặc `orelse` là H (đệ quy); `BoolOp` có một giá trị là H. `Call`, `Name`, `Attribute`,
`Subscript` KHÔNG phải H (giá trị tính/đọc được).

| Mã | Phạm vi | Khớp khi | Không khớp (ví dụ hợp lệ) |
|---|---|---|---|
| **A-stdlib** | SERVING | gọi `random.<f>` (qua bí danh) với f ∈ {random, randint, randrange, choice, choices, shuffle, sample, uniform, triangular, gauss, normalvariate, lognormvariate, expovariate, vonmisesvariate, gammavariate, betavariate, paretovariate, weibullvariate, binomialvariate, getrandbits, randbytes}; `random.Random()`/`Random(None)`; `random.seed()`/`seed(None)`; `random.SystemRandom(...)` | `random.Random(42).random()`; `random.Random(seed)`; lượt rút SAU `random.seed(<khác None>)` trong CÙNG hàm (hoặc cùng mã cấp module) |
| **A-numpy** | SERVING | gọi `numpy.random.<f>` với f ∉ {default_rng, Generator, SeedSequence, RandomState, seed, BitGenerator, PCG64, PCG64DXSM, MT19937, Philox, SFC64} (hàm dùng trạng thái toàn cục); `default_rng()`/`default_rng(None)`, `RandomState()`/`(None)`, `seed()`/`seed(None)`, bit generator không đối số/None | `np.random.default_rng(0)`, `default_rng(seed)` (đối số bất kỳ khác hằng None — nhưng mọi lượt rút RNG BÊN TRONG biểu thức đối số vẫn bị luật của nó bắt, ví dụ §2.3 #6); `rng.normal()`; lượt rút sau `np.random.seed(<khác None>)` trong cùng hàm |
| **A-torch** | SERVING | gọi `torch.<f>` với f ∈ {rand, randn, randint, randperm, rand_like, randn_like, randint_like, normal, bernoulli, multinomial, poisson, seed} mà KHÔNG có keyword `generator=`; gọi phương thức `<expr>.<m>(...)` với m ∈ {uniform_, normal_, bernoulli_, random_, exponential_, geometric_, cauchy_, log_normal_} không có `generator=` và `<expr>` không phân giải thành `torch.nn.init`; `torch.Generator(...)` trừ khi nối ngay `.manual_seed(x)` hoặc cùng hàm có `<tên đã gán>.manual_seed(x)` | `torch.rand(2, generator=g)`; lượt rút sau `torch.manual_seed(<khác None>)` trong cùng hàm; `nn.init.trunc_normal_(w)` / `nn.init.normal_(w)` (khởi tạo trọng số, bị checkpoint ghi đè — rủi ro §6) |
| **B-import** | MAIN | `import unittest.mock`, `from unittest import mock`, `from unittest.mock import ...`, `import mock`, `from mock import ...`, `import pytest_mock`/`from pytest_mock ...`, `import asynctest` | `import unittest` (không có mock) |
| **B-name** | MAIN | `Name.id` hoặc `Attribute.attr` ∈ {Mock, MagicMock, AsyncMock, NonCallableMock, NonCallableMagicMock, PropertyMock, create_autospec, mock_open}; `Attribute.attr == "patch"` với giá trị là tên `mock` hoặc chuỗi thuộc tính kết thúc bằng `mock` | hàm tên `patch_image`; chuỗi `"mock"` (thuộc C-string) |
| **C-name** | SERVING | ĐIỂM GÁN TÊN có token ∈ FAKE = {fake, dummy, mock, mocked, stub, simulate, simulated, simulation, simulator, synthetic, synthesized, synthesised, placeholder, fabricated}: đích Assign/AnnAssign/AugAssign (Name, `Attribute.attr`, phần tử tuple), đích for/comprehension, `with ... as`, tên def/class, tham số hàm, bí danh `import ... as` | dùng lại tên (chỉ đếm điểm gán); `random_scale`, `sample_id`, `example` |
| **C-string** | SERVING | đơn vị chuỗi (§3.2) khớp `(?i)\b(fake|dummy|mock(?:ed)?|stub(?:bed)?|simulat(?:e|ed|ion|or)|synthe(?:tic|sized|sised)|placeholder|fabricated)\b` hoặc `(?i)giả\s+lập|dữ\s+liệu\s+giả|kết\s+quả\s+giả|số\s+liệu\s+giả` | docstring thường; comment; `"giải"` |
| **C-result** | SERVING | giá trị CỐ ĐỊNH (F) gán vào khóa/tên kết quả. F = str có ≥ 1 ký tự `\w`; số (không bool) ∉ SENTINELS; list/tuple khác rỗng mà mọi phần tử là F (dict: mọi value là F). Vị trí: (1) dict literal có khóa str ∈ RESULT_KEYS = {gloss, glosses, prediction, predictions, translation, translated_text, confidence, top5, candidates, sentence}; (2) Assign/AnnAssign vào Name/Attribute có token CUỐI ∈ {gloss, glosses, prediction, predictions, translation, confidence} hoặc tên ∈ RESULT_KEYS; (3) gán `x["<khóa ∈ RESULT_KEYS>"] = F`; (4) `return F` trong hàm có token tên ∈ {predict, translate, classify, recognize, recognise, infer} | `"gloss": "..."`, `"translation": ""`, `"confidence": 0.0`, `"prediction": None`, `"top5": []`, `"gloss": pred["gloss"]`; `confidence_threshold = 0.45`; tham số mặc định và keyword khi gọi (`min_detection_confidence=0.5`) KHÔNG xét |
| **D-binding** | MAIN | tên/khóa có token ∈ METRIC = {accuracy, acc, top1, top5, topk, precision, recall, f1, wer, cer, bleu, rouge, meteor, latency, fps, throughput, speedup, p50, p90, p95, p99, ms} nhận giá trị H, hoặc giá trị có "tỉ lệ gõ tay" (một nút `BinOp` Mult/Div bất kỳ trong biểu thức giá trị — `ast.walk` — có toán hạng là hằng số ∉ UNIT_FACTORS; dạng `latency_ms * 0.4` từng bịa, review 04 mục 10). Vị trí: đích Assign/AnnAssign/AugAssign (Name, `Attribute.attr`, `Subscript` khóa str); khóa str của dict literal; keyword khi gọi hàm; giá trị mặc định của tham số | `infer_ms = 0.0`; `best_top1 = -1.0`; `latency_ms = (t1 - t0) * 1000.0`; `fps = 1.0 / dt`; `"top1": round(top1, 2)`; `.get("latency_ms", 0.0)` (đối số vị trí của `.get` không xét) |
| **D-string** | MAIN | đơn vị chuỗi (§3.2) khớp một trong: (i) phần trăm `(?<![\w.])\d+(?:[.,]\d+)?\s*%`; (ii) số kèm đơn vị `(?i)(?<![\w.])\d+(?:[.,]\d+)?\s*(?:ms|fps)\b`; (iii) từ khóa số liệu rồi tới một số trong ≤ 20 ký tự không phải chữ số: `(?i)\b(?:accuracy|acc|top-?[15]|precision|recall|f1|wer|cer|bleu|rouge|latency|fps|throughput|độ\s+chính\s+xác|độ\s+trễ)\b[^\d\n]{0,20}(?<![\w-])\d` | `f"{fps:.1f} FPS"` (phần hằng không có số); `"%.2f"`, `"%d%%"`; `"Top-5 Dự đoán:"`; `"precision, recall, f1-score"` (số `1` dính chữ `f`) |

Ghi chú thiết kế luật:
- "Seed trước trong cùng phạm vi": một lượt rút loại K (stdlib/numpy/torch) KHÔNG bị báo nếu trong cùng hàm trong cùng
  nhất (hoặc cùng mã cấp module) có lời gọi seed cùng loại (`random.seed(x)`, `np.random.seed(x)`, `torch.manual_seed(x)`)
  với ≥ 1 đối số không phải hằng `None`, ở DÒNG NHỎ HƠN. Seed ở hàm khác KHÔNG tính (ví dụ `set_seed()` ở một hàm, rút ở
  hàm khác → vẫn báo). Chính lời gọi seed có đối số không bị báo.
- Mỗi điểm khớp là một Finding (§3.2 "Cách đếm"); một dòng có thể có nhiều Finding khác mã. Không gộp theo dòng.
- Không có cơ chế ngoại lệ tại chỗ (`# guard: allow ...`): (1) ngoại lệ tại chỗ buộc sửa mã nguồn chính (cấm trong việc
  này); (2) ngoại lệ rải rác khó đếm và dễ lạm dụng. Ngoại lệ DUY NHẤT là sổ `ALLOWED` trong file test (§3.6), đếm được,
  mỗi mục có lý do, chỉ planner thêm được.

### 3.4 So khớp với sổ đăng ký
- Khóa nhóm = `(path, rule, qualname)`; giá trị = số Finding của nhóm. Không dùng số dòng (dòng dịch chuyển khi file khác
  sửa — backend/main.py đang được sửa ở local), nhưng số lượng phải khớp đúng → thêm một vi phạm vào cùng hàm cũng FAIL.
- `compare_registry` (§3.0): nhóm hiện có mà không có trong `ALLOWED` ∪ `KNOWN_VIOLATIONS` → `unregistered` (báo từng
  Finding kèm dòng); nhóm đăng ký có số hiện tại khác → `changed`; nhóm đăng ký mà hiện tại 0 → `stale`.
- `ALLOWED` và `KNOWN_VIOLATIONS` không được chung khóa (assert). Mỗi mục có chuỗi `text` (lý do / hướng sửa) không rỗng.

### 3.5 Vi phạm có sẵn: chọn phương án (ii) — sổ `KNOWN_VIOLATIONS` đăng ký cứng, không phải (i) để test đỏ
- **(i) Test đỏ tới khi sửa** (tiền lệ 06 §0.3). Ưu: đúng nghĩa đen "guard FAIL khi có vi phạm". Nhược: ở 06 §0.3, đỏ
  chỉ được phép ở mốc TRUNG GIAN của CÙNG kế hoạch và phải xanh khi đóng việc; ở đây việc sửa cố ý nằm NGOÀI kế hoạch
  (người dùng: không tự sửa, nhất là `backend/main.py`; orchestrator: sửa là kế hoạch sau) → test đỏ kéo dài qua nhiều kế
  hoạch, mọi AC "không hồi quy" sau này phải khoét ngoại lệ, và một vi phạm MỚI trong cùng test bị che bởi chữ FAIL cũ
  (chỉ còn quy ước "tập không tăng" do người kiểm bằng mắt).
- **(ii) Sổ đăng ký cứng** (CHỌN). Test FAIL khi: có vi phạm mới (kể cả thêm 1 lần trong hàm đã đăng ký), hoặc một vi phạm
  đã đăng ký biến mất/đổi số lượng mà sổ chưa cập nhật. Ưu: bất biến "tập vi phạm không tăng" của 06 §0.3 được MÁY kiểm
  thay vì quy ước; bộ test xanh nên failure mới không bị che; danh sách vi phạm nằm ngay trong test + báo cáo JSON.
  Nhược: guard xanh trong khi còn vi phạm đã biết → phải có quy tắc để không thành "nới test".
- **Vì sao (ii) không phải "nới test để pass":**
  1. Không có test/tiêu chí cũ nào bị đổi; sổ được lập MỘT lần từ output đầu tiên của chính guard, trước khi sửa bất kỳ
     dòng mã nào, và được công bố (JSON §3.7 + 10-progress).
  2. Sổ chỉ được CO: sau commit B1, `KNOWN_VIOLATIONS` chỉ được bớt mục hoặc giảm số (vì mã đã sửa); thêm mục/tăng số =
     sửa test để pass (cấm, reviewer kiểm `git log -p -- tests/test_backend_source_guard.py`). `ALLOWED` chỉ đổi qua
     "Lần sửa" của kế hoạch này (planner ghi lý do).
  3. Mỗi luật được chứng minh FAIL với vi phạm mới bằng đột biến (AC2, AC6), kể cả khi chèn vào `backend/main.py` thật
     (đọc từ đĩa, sửa trong bộ nhớ).
  4. DoD 7 (phần backend) CHỈ được báo PASS khi `KNOWN_VIOLATIONS` rỗng. Test in `[DoD7-guard] known=<n> allowed=<m>`
     (số tính từ sổ) và JSON có `summary`; báo cáo cuối (autopilot §6) phải trích `known = 0` từ JSON có commit.
- Hệ quả: DoD 7 phần backend sau kế hoạch này = "guard có, CHƯA ĐẠT" nếu sổ KNOWN khác rỗng (dự báo: có, §2.3 #1–#4).

### 3.6 Sổ `ALLOWED` (planner duyệt trước) và `KNOWN_VIOLATIONS` (từ output guard)
Dạng: `dict[(path, rule, qualname)] -> (count, text)`; `count` chép từ output guard ở B1 (không gõ theo dự báo).
Test giữ thêm hằng `PLAN10_APPROVED_ALLOWED` = đúng tập khóa của bảng dưới (16 khóa) và assert
`set(ALLOWED) <= PLAN10_APPROVED_ALLOWED` (reviewer đối chiếu hằng này với bảng).
- **ALLOWED — chỉ những khóa sau được phép** (DTG ở §2.3), lý do phải ghi nguyên ý trong `text`:

| Khóa (path, rule, qualname) | Lý do (ghi vào `text`) |
|---|---|
| `src/data/augment.py`, A-numpy, `KeypointAugmenter.{add_jitter, random_scale, random_rotate_2d, time_warp, keypoint_mask, augment_sequence, augment_static, augment_vsl_sequence}` (8 khóa) | augmentation lúc train; chỉ tạo khi `augment=True`; module vào bao đóng phục vụ qua import đầu module `src/inference/ensemble.py` → `src/data/vsl_dataset.py`, không hàm phục vụ nào gọi |
| `src/data/harmonized.py`, A-torch, `HarmonizedDataset.__getitem__` | nhánh augment của Dataset train; live gọi `harmonize(rng=None)` |
| `src/data/harmonized.py`, D-binding, `HarmonizedDataset.__getitem__` | fps ĐẦU VÀO mặc định khi npz thiếu metadata; không phải số đo |
| `src/data/harmonized.py`, D-binding, `harmonize` | fps ĐẦU VÀO mặc định; tham số tiền xử lý dùng chung |
| `src/metrics/cslr_metrics.py`, D-binding, `compute_wer` | quy ước công thức WER khi không có từ tham chiếu |
| `src/data/vsl_dataset.py`, D-string, `validate_split_guards` | câu báo lỗi kiểm toàn vẹn split ("100% dialect") |
| `src/inference/ensemble.py`, D-string, `run_ensemble_benchmark` | mô tả trọng số 0.5/0.5 của hàm đánh giá offline |
| `src/inference/predictor.py`, C-name, `VSLPredictor.warmup` | tensor warmup, đầu ra bỏ (`_ = self.model(...)`) |
| `src/inference/realtime_extractor.py`, C-name, `RealtimeLandmarkExtractor.__init__` | khung warmup MediaPipe, đầu ra bỏ |

  - Khóa trong bảng mà guard KHÔNG báo → không thêm vào `ALLOWED` (vẫn để trong `PLAN10_APPROVED_ALLOWED`); ghi trong
    10-progress "dự báo không xảy ra" + lý do từ output.
  - Mỗi khóa ALLOWED phải kèm bằng chứng trong 10-progress: `npx --yes gitnexus@1.6.12 context <symbol>` (caller) và, nếu
    `UNKNOWN`/rỗng, text search `Grep` (ví dụ `KeypointAugmenter(`, `HarmonizedDataset(`, `augment=True`) cho thấy không
    có caller trên đường phục vụ.
- **KNOWN_VIOLATIONS** = MỌI nhóm còn lại mà guard báo ở B1, kể cả nhóm coder nghĩ là DTG nhưng không có trong bảng trên
  (khi đó ghi "đề xuất DTG" trong 10-progress để planner xét ở lần sửa sau — coder KHÔNG tự thêm vào ALLOWED).
  `text` = hướng sửa đề xuất + "kế hoạch sau". Dự báo: §2.3 #1–#4 (`realtime_demo.py`).
- Nếu guard báo nhóm nào trong `backend/main.py`: vào KNOWN, KHÔNG sửa `backend/main.py` (yêu cầu người dùng).

### 3.7 Báo cáo JSON (bằng chứng số liệu)
Lệnh: `PYTHONIOENCODING=utf-8 .venv/bin/python -m tests.test_backend_source_guard --report
reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json`. Nội dung:
`generated_by{command (nguyên văn), git_commit (40 hex, git rev-parse HEAD), code_dirty (git status --porcelain --
backend src tests realtime_demo.py start_fullstack.ps1 khác rỗng), generated_at_utc}`, `note` ("static source guard for
DoD 7; counts are code findings, not model metrics"), `scope{entrypoints, serving_files, main_files, scripts_realtime}`,
`rules{mã: mô tả}`, `findings[{path, line, rule, qualname, snippet, status ∈ {known, allowed, unregistered}, text}]`,
`summary{by_status, by_rule, n_serving_files, n_main_files}`. Không chứa dữ liệu, token hay đường dẫn tuyệt đối.
Mọi con số về vi phạm trong 10-progress/commit/báo cáo cuối đều trích từ file này (kèm đường dẫn + commit).

### 3.8 Hiệu năng và GitNexus
- Chỉ đọc ~80 file và parse AST: mục tiêu `Ran N tests in X s` với X < 10 s trên cloud (AC7). Không cần dữ liệu gitignore
  → 0 skip ở mọi máy.
- Không sửa symbol nào có sẵn → không cần `impact` trước khi sửa; vẫn chạy `npx --yes gitnexus@1.6.12 detect-changes
  --scope all --repo .` trước MỖI commit (CLAUDE.md) và ghi kết quả (risk) vào message; `context` cho các symbol của
  ALLOWED như §3.6.

## 4. Chia việc

Ký hiệu: `P10` = HEAD lúc bắt đầu B1 (ghi hash vào 10-progress). Thư mục tạm NGOÀI repo: `../_plan10_tmp/`.

| Bước | Nội dung | Phụ thuộc | Ước lượng |
|---|---|---|---|
| **B1** | (1) Mốc: tại `P10` chạy lệnh AC8 KHÔNG có module mới → `../_plan10_tmp/b0_ac8.txt`; `git status --porcelain` → `../_plan10_tmp/b0_status.txt`; tạo `docs/plans/10-progress.md`, ghi tóm tắt B0 (Ran / failures / errors / skipped + id test đỏ/lỗi, chép từ output). (2) Viết `tests/test_backend_source_guard.py` theo §3: hàm §3.0, lớp `TestRuleSelfCheck` (AC2, AC3), `TestScope` (AC4), `TestRegistryComparator` (AC6), `TestImportLight` (AC7-a), `TestBackendSourceGuard` (AC5); `ALLOWED`/`KNOWN_VIOLATIONS` ban đầu rỗng. (3) Chạy chế độ báo cáo ra `../_plan10_tmp/b1_first_scan.json` (output thô đầu tiên), chép bảng nhóm vào 10-progress. (4) Điền `ALLOWED` (chỉ khóa §3.6 mà guard báo; `count` từ output) và `KNOWN_VIOLATIONS` (mọi nhóm còn lại). Ghi bằng chứng `context`/Grep cho từng khóa ALLOWED. (5) Chạy module 2 lần → OK cả hai. (6) `detect-changes`; commit `test(guard): DoD 7 backend source guard (plan 10 B1)`, message có dòng `[DoD7-guard] known=… allowed=…` chép từ output test. | — | 2 giờ |
| **B2** | (1) Tại HEAD của B1, cây sạch với các đường của `code_dirty`: chạy lệnh báo cáo §3.7 → `reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json`; chạy lại ra `../_plan10_tmp/b2_rerun.json`, so phần thân (bỏ `generated_by`) → giống hệt. (2) Chạy lệnh AC8 đầy đủ → `../_plan10_tmp/b2_ac8.txt`; so với B0 theo AC8. (3) `git status --porcelain` trước/sau chạy test giống hệt (ngoài file báo cáo chưa commit). (4) Cập nhật 10-progress (số chép từ JSON/output, kèm lệnh + commit). (5) `detect-changes`; commit `docs(guard): DoD 7 findings report (plan 10 B2)`. | B1 | 1 giờ |
| **B3** | (1) 10-progress: đối chiếu dự báo §2.3 #1–#13 (xảy ra / không, mã luật thực tế, lý do); danh sách "vi phạm có sẵn" = mọi finding `status: known` (file:dòng, chép từ JSON B2); đề xuất sửa cho kế hoạch sau (mục dưới); danh sách "đề xuất DTG" (nếu có). (2) Kiểm AC1, AC9, AC10. (3) `detect-changes`; commit `docs(plan10): progress + proposals (plan 10 B3)`. Orchestrator gọi vslt-reviewer. KHÔNG sửa `docs/progress_log.md`/`docs/STATE.md` (orchestrator làm khi hợp nhất). | B2 | 0.5 giờ |

**Sau kế hoạch này (KHÔNG làm ở đây; đề xuất kế hoạch 11 — sửa vi phạm):**
- `realtime_demo.py`: bỏ chế độ `--source mock` (khung tổng hợp) khỏi điểm vào người dùng (hoặc chuyển thành fixture chỉ
  trong `tests/`); bỏ `else 30.0` của `avg_fps` (hiển thị "—"/0 khi chưa đo). Caller: `run_core.py:116-124` chỉ truyền
  webcam/video; `scripts/generate_slide_images.py:19` chỉ import `RealtimeHUD`. Sau khi sửa: nhóm KNOWN thành `STALE`
  → xóa khỏi sổ (sổ co lại), `known` giảm.
- (Tùy chọn, cần `impact` trên `src/inference/ensemble.py`) import lười `get_vsl_dataloaders` trong hàm đánh giá của
  `ensemble.py` để `augment.py` ra khỏi bao đóng phục vụ → 8 khóa ALLOWED thành `STALE` → xóa.
- `backend/main.py:531` docstring "(487 classes for Tier 2)" → bỏ số cứng (SAU khi nhánh local của kế hoạch 06 hợp nhất).
- Guard thứ hai cho scripts đo/báo cáo (§2.4).
- Hợp nhất nhánh: khi `feat/vslt-complete` (kế hoạch 06 B6–B9, gồm 0328c1b) hợp nhất với nhánh này, orchestrator chạy
  `tests.test_backend_source_guard` ngay sau merge; nhóm mới → KNOWN (mặc định) hoặc planner "Lần sửa" cho ALLOWED.

## 5. Tiêu chí chấp nhận (hợp đồng; coder không được đổi)

Lệnh chạy module trên cloud: `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_backend_source_guard -v`
(máy local Windows: `.venv/Scripts/python`).

**AC1 — Phạm vi thay đổi.** `git diff --name-status P10 HEAD` chỉ gồm: `A tests/test_backend_source_guard.py`,
`A docs/plans/10-progress.md`, `A reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json` (file kế hoạch này do orchestrator
commit, ngoài danh sách). `git diff P10 HEAD -- tests/` chỉ là file mới, 0 dòng `-`. KHÔNG đổi: `backend/`, `src/`,
`scripts/`, `frontend/`, `realtime_demo.py`, `run_core.py`, `start_fullstack.ps1`, `README.md`, `docs/STATE.md`,
`docs/progress_log.md`, `docs/plans/06-*`, `docs/phase12_api.md`, `docs/reviews/*`, mọi test có sẵn. Không thêm dữ liệu,
nhị phân, `.pt/.npz/.mp4/.log`.

**AC2 — Tự kiểm dương: mỗi luật bắt được (`TestRuleSelfCheck`, chuỗi trong bộ nhớ, không file).** Dict `POSITIVE`
(mã luật → danh sách mẫu mã nguồn); assert `set(POSITIVE) == set(RULES)` (đủ 10 mã). Mỗi mẫu chạy
`scan_source(mẫu, "mem/x.py", ALL_RULES)` phải cho ≥ 1 Finding đúng mã đó (subTest theo mẫu). Tối thiểu các mẫu sau (câu
chữ có thể khác, nội dung phải phủ từng gạch):
- A-stdlib: `import random` + `x = random.random()`; bí danh `import random as r` + `r.choice(xs)` trong một `def`;
  `from random import shuffle` + `shuffle(xs)`; `random.seed()`; seed ở `def a()` rồi rút ở `def b()` → vẫn báo ở `b`.
- A-numpy: `np.random.rand(3)`; `import numpy` + `numpy.random.normal(0, 1)`; `from numpy import random as npr` +
  `npr.uniform()`; `np.random.default_rng()`; `np.random.default_rng(None)`; `from numpy.random import randn` + `randn(2)`.
- A-torch: `torch.rand(3)`; `torch.randn_like(x)`; `np.random.default_rng(int(torch.randint(0, 5, (1,))))` → có A-torch
  và KHÔNG có A-numpy; `x.uniform_(0, 1)`; `g = torch.Generator()` không `manual_seed`.
- B-import: `from unittest import mock`; `import unittest.mock`; `from unittest.mock import patch`; `import mock`.
- B-name: `m = MagicMock()`; `AsyncMock()`; `from unittest import mock` + `mock.patch("a.b")` → có B-name.
- C-name: `fake_result = 1`; `def simulate_landmarks(): pass`; `class SyntheticStream: pass`;
  `def f(placeholder_gloss): pass`; `for mock_frame in frames: pass`; `mockPredictor = 1`; `dummies = []`.
- C-string: `print("Using synthetic frames")`; `if src == "mock": pass`; `f"dummy {x}"`; `msg = "dữ liệu giả lập"`;
  docstring route `@app.get("/x")` + `def h():` + `"""Returns simulated results."""`.
- C-result: `def f():` + `return {"gloss": "xin chào", "confidence": 0.9}` (đúng 2 Finding C-result);
  `self.last_gloss = "cảm ơn"`; `confidence = 0.87`; `out["translation"] = "Tôi đi học"`; `def predict(x):` +
  `return "a"`; `r = {"top5": [("a", 0.9)]}`.
- D-binding: `latency_ms = 12.5`; `ACCURACY = 0.751`; `{"top1": 75.1}`; `self.fps = 30`; `stats["latency_ms"] = 42`;
  `wer = 100.0 if x else 0.0`; `top5_acc: float = 0.9`; `server_preprocess_ms = latency_ms * 0.4`; `hud.draw(fps=30.0)`;
  `def f(latency_ms=12.0): pass`; `{"accuracy": "75.1"}`.
- D-string: `"Độ chính xác 92%"`; `f"Top-1: 75.1 ({n} clip)"`; `"latency 35 ms"`; `"~30 FPS"`; `"accuracy=0.87"`;
  `print("WER 23.4")`; docstring route `"""Mô hình đạt 87% trên tập test."""`.
- Cách đếm: `a = "mock"` + `b = "mock"` → đúng 2 Finding C-string; một f-string liền nhau trải 3 dòng khớp D-string →
  đúng 1 Finding, `line` = dòng đầu; mẫu nhiều dòng có dòng vi phạm đã biết → `line` đúng dòng đó.

**AC3 — Tự kiểm âm: mẫu hợp lệ không bị báo (`TestRuleSelfCheck`).** Mỗi mẫu sau (kèm import cần thiết để bí danh phân
giải) chạy với `ALL_RULES` → 0 Finding:
`rng = np.random.default_rng(0)` + `v = rng.normal()`; `np.random.default_rng(seed)`; `random.Random(42).random()`;
`def f():` + `np.random.seed(0)` + `return np.random.randn(2)`; `def g():` + `torch.manual_seed(0)` + `return torch.rand(2)`;
`torch.rand(2, generator=g)`; `g = torch.Generator()` + `g.manual_seed(1)`; `nn.init.trunc_normal_(w, std=0.02)`;
`from torch.nn import init` + `init.normal_(w)`; `self.random_scale(x)`; comment `# np.random.rand()`; docstring MODULE
`"""Synthetic dummy data, 87% accuracy, sub-10ms latency."""`; docstring của hàm KHÔNG phải route có chữ "dummy";
`infer_ms = 0.0`; `best_top1 = -1.0`; `latency_ms = (t1 - t0) * 1000.0`; `fps = 1.0 / dt`;
`fps = float(np.mean(t)) if t else 0.0`; `{"top1": round(top1, 2)}`; `prediction.get("latency_ms", 0.0)`;
`f"{fps:.1f} FPS | {lat:.1f}ms"`; `"%.2f"`; `"Top-5 Dự đoán:"`; `"precision, recall, f1-score"`;
`{"gloss": "...", "confidence": 0.0, "prediction": None, "top5": [], "translation": ""}`; `{"gloss": pred["gloss"]}`;
`confidence_threshold = 0.45`; `def f(min_detection_confidence: float = 0.5): pass`;
`Holistic(min_detection_confidence=0.5)`; `WS_MAX_MESSAGE_BYTES = 1_048_576`; `ALPHABET_MAX_ABS_COORD = 10.0`;
`import unittest`; `def patch_image(x): pass`; `"giải mã CTC"`; `sample_id = 3`.

**AC4 — Phạm vi (`TestScope`).**
- a. Resolver trên repo mẫu tạm (`tempfile.mkdtemp()` NGOÀI repo, xóa ở tearDown): `entry.py` có `import pkg.a` ở đầu,
  `def f(): from pkg import b` (lười), `import json`, `import tool`; `pkg/__init__.py`; `pkg/a.py` có `from .c import d`;
  `pkg/b.py`; `pkg/c.py`; `pkg/unused.py`; `scripts/tool.py`. `serving_closure(tmp, ("entry.py",))` == đúng tập
  {`entry.py`, `pkg/__init__.py`, `pkg/a.py`, `pkg/b.py`, `pkg/c.py`, `scripts/tool.py`} (không có `pkg/unused.py`).
- b. Cây thật: SERVING ⊇ `MIN_SERVING` (§3.1); SERVING ∩ {`src/training/trainer.py`, `src/export/export_onnx.py`} = ∅;
  SERVING ⊆ MAIN; MAIN ⊇ mọi `backend/**/*.py` và `src/**/*.py`.
- c. Mọi file của MAIN đọc UTF-8 và `ast.parse` được.
- d. `start_fullstack.ps1` chứa `backend.main:app`; tập scripts-realtime tính được == `set(SCRIPTS_REALTIME)` == ∅.
- e. In `[scope] serving=<n> main=<m>` (số tính được, không gõ tay).

**AC5 — Cây thật khớp sổ (`TestBackendSourceGuard`).**
- a. `compare_registry(scan_repo()[0], ALLOWED, KNOWN_VIOLATIONS)` → `unregistered`, `changed`, `stale` đều rỗng; nếu không,
  thông điệp FAIL theo §3.0.
- b. `set(ALLOWED) <= PLAN10_APPROVED_ALLOWED` (= 16 khóa §3.6); `set(ALLOWED) & set(KNOWN_VIOLATIONS) == set()`; mọi mục
  có `count ≥ 1` và `text` khác rỗng.
- c. In `[DoD7-guard] known=<tổng count KNOWN> allowed=<tổng count ALLOWED>`.
- d. File `reports/guard_dod7_<YYYY-MM-DD>/guard_findings.json` (B2): `generated_by.git_commit` là commit B1 (tổ tiên HEAD,
  và `git diff <commit> HEAD -- tests/test_backend_source_guard.py backend src realtime_demo.py` rỗng), `code_dirty: false`,
  `summary.by_status.unregistered == 0`, tổng `known`/`allowed` trong JSON == số in ở (c). Reviewer chạy lại lệnh báo cáo
  ra thư mục tạm → phần thân (bỏ `generated_by`) giống hệt.
- e. **Danh sách vi phạm có sẵn** = các finding `status: "known"` của JSON đó (file:dòng:mã:qualname). Không danh sách
  nào khác được coi là chính thức; không gõ tay số lượng.

**AC6 — Đột biến trên sổ thật (`TestRegistryComparator`).** Gọi `F = scan_repo()[0]`:
- a. Với MỖI đột biến sau: đọc `backend/main.py` từ đĩa, NỐI chuỗi vào cuối TRONG BỘ NHỚ, quét lại riêng file đó bằng
  `scan_source` với bộ luật của nó (file ∈ SERVING → đủ 10 mã), thay các Finding của file này trong `F` →
  `compare_registry` có `unregistered` chứa Finding đúng mã, `path == "backend/main.py"`:
  `import random` + `_v = random.random()` (A-stdlib); `from unittest.mock import MagicMock` (B-import);
  `_r = {"gloss": "xin chào", "confidence": 0.9}` (C-result); `_fake_latency_ms = 12.5` (C-name và D-binding);
  `def _h():` + `return "Độ chính xác 92%"` (D-string). sha256 của `backend/main.py` trước/sau test bằng nhau.
- b. Nhân đôi: thêm một bản sao của một Finding thuộc một khóa đã đăng ký (ưu tiên KNOWN; nếu KNOWN rỗng dùng ALLOWED) →
  `changed` chứa khóa đó.
- c. Xóa: bỏ mọi Finding của một khóa đã đăng ký → `stale` chứa khóa đó.
- d. `F` nguyên vẹn → cả 3 rỗng (trùng AC5-a).

**AC7 — Nhẹ, nhanh, tất định.**
- a. (`TestImportLight`) subprocess `[sys.executable, "-c", "import sys, tests.test_backend_source_guard; print(sorted(m for m
  in ('torch','numpy','cv2','mediapipe','fastapi','backend.main') if m in sys.modules))"]`, `cwd=PROJECT_ROOT` → stdout
  đúng `[]`.
- b. Lệnh module ở đầu §5 → `OK`, không có `skipped`, `Ran N tests in X s` với X < 10 trên cloud (báo N, X từ output).
- c. Hai lần chạy chế độ báo cáo liên tiếp ra 2 file tạm → `findings` và `summary` giống hệt.

**AC8 — Không hồi quy.** Lệnh (29 module của kế hoạch 06 AC2 + module mới):
`PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_backend_source_guard -v`
- Mốc B0 = cùng lệnh BỎ module cuối, chạy tại `P10`. Tham chiếu do orchestrator chạy tại 04ec565 (không phải số của
  planner): `Ran 414`, failures=1 (`TestFrontendSourceGuard.test_no_violation` — đỏ có chủ đích; local đã sửa ở 0328c1b,
  chưa hợp nhất vào nhánh này), errors=1 (`setUpClass` của `test_translation_core`: thiếu checkpoint ViT5, dữ liệu
  gitignore), skipped=30 (thiếu dữ liệu gitignore). B0 của coder là số chính thức; nếu khác tham chiếu → ghi cả hai.
- Sau B2: `Ran` = B0 + số test của module mới; tập id test FAIL == của B0; tập id test ERROR == của B0; số skipped == B0;
  module mới: mọi test OK, 0 fail, 0 error, 0 skip. `git status --porcelain` trước/sau lệnh giống hệt.

**AC9 — Quy trình.** Mỗi commit có kết quả `detect-changes` (risk) trong message; commit B1 có dòng `[DoD7-guard] ...` chép
từ output; 10-progress có output `context` cho symbol của mỗi khóa ALLOWED (+ Grep nếu `UNKNOWN`). Không amend/rebase/
force-push. Không đụng thay đổi chưa commit có sẵn (so `b0_status.txt`).

**AC10 — Tài liệu `docs/plans/10-progress.md`.** Có: `P10`; tóm tắt B0; bảng output thô đầu tiên (từ
`../_plan10_tmp/b1_first_scan.json`); phân loại từng nhóm (ALLOWED + lý do + bằng chứng; KNOWN + hướng sửa); đối chiếu dự báo
§2.3 #1–#13; danh sách vi phạm có sẵn (file:dòng, chép từ JSON B2, ghi đường dẫn + commit); đề xuất kế hoạch 11; "đề xuất
DTG" nếu có. Mọi số đều có nguồn (lệnh + commit hoặc đường dẫn JSON).

## 6. Rủi ro dữ liệu/ML
- **Không đụng dữ liệu/model:** guard chỉ đọc mã → không rò rỉ, không cỡ mẫu, không chọn model, không TEST. Con số của guard
  là số dòng mã khớp luật, KHÔNG phải số liệu ML (JSON ghi rõ trong `note`).
- **Âm tính giả (guard không thấy):** import động (`importlib`, `__import__`); RNG nằm trong thư viện ngoài (MediaPipe,
  sklearn `random_state=None`, `DataLoader(shuffle=True)`); model quên `eval()` (dropout) — được phủ bởi test tương
  đương (kế hoạch 04 AC4, kế hoạch 06 AC5), không phải guard; trọng số khởi tạo ngẫu nhiên nếu nạp checkpoint không chặt
  (`nn.init.*` bị loại khỏi luật A) — hiện `src/inference/predictor.py:144,162,177`, `src/inference/ensemble.py:112,133`,
  `src/translation/cslr_recognizer.py:76`, `backend/main.py:629` đều `load_state_dict` với `strict` mặc định (True);
  RNG CÓ seed nhưng dùng để SINH kết quả (`confidence = rng.uniform()`) — luật A cho qua, C-result chỉ bắt hằng; số liệu
  gõ tay qua biểu thức phức tạp hoặc đọc từ file cấu hình gõ tay; scripts đo/báo cáo ngoài phạm vi (đề xuất §2.4).
- **Dương tính giả:** xử lý bằng `ALLOWED` do planner duyệt; rủi ro sổ phình → chính sách §3.5 (2) và AC5-b.
- **Lý do ALLOWED phụ thuộc hành vi hiện tại:** "đường phục vụ không tạo dataset với `augment=True`" và "live gọi
  `harmonize(rng=None)`". Nếu sau này backend tạo dataset (ví dụ Ký câu offline từ clip), phải xét lại; bằng chứng caller
  được chốt trong 10-progress ở commit B1.
- **Lệch train–realtime:** guard không thay test tương đương. `fps = 30.0` mặc định trong `harmonize` là giả định DÙNG CHUNG
  train/live (cùng một hàm) nên không tự gây lệch; nhưng nếu live có lúc truyền fps ≤ 0 thì đó là giả định cần nêu ở mục
  "Giới hạn" của GATE (ghi nhận, không thuộc việc này).
- **Hợp nhất nhánh:** local đang sửa `backend/main.py`, frontend, `scripts/smoke_test_phase12.py` (kế hoạch 06). Sau merge,
  phát hiện/bao đóng có thể đổi → guard đỏ (đúng thiết kế). Khóa theo qualname nên dời dòng không gây đỏ; đổi tên hàm
  hoặc thêm chuỗi khớp luật thì đỏ → xử lý theo §3.6, không sửa sổ tùy tiện.
- **Nguồn gốc dữ liệu:** chế độ `--source mock` của `realtime_demo.py` là đầu vào tổng hợp trong một điểm vào người dùng
  (DoD 6/7) — ghi nhận, sửa ở kế hoạch sau; không phát hiện dữ liệu tổng hợp nào đi vào backend.

## 7. Điểm dừng
**Không có điểm dừng bắt buộc** → không cần người dùng trước khi code: không đổi model mặc định; không cần dữ liệu người
dùng; không đụng thay đổi chưa commit (chỉ thêm 3 file mới); không xóa file, không hành động không hoàn tác.

Điểm dừng có điều kiện trong lúc làm (coder dừng, ghi 10-progress, báo orchestrator):
1. Guard báo nhóm trong `backend/main.py` → CHỈ liệt kê vào KNOWN (yêu cầu người dùng: không sửa file này); không dừng.
2. Guard cho thấy kết quả/dữ liệu giả THẬT SỰ tới người dùng qua backend (ví dụ C-result/C-string trong một route, không
   phải `realtime_demo.py` mock đã biết) → DỪNG, báo orchestrator: "vấn đề dữ liệu mới" + DoD 6 (autopilot §5).
3. Tập scripts-realtime tính được ≠ ∅ hoặc không thỏa `MIN_SERVING` → CẦN PLANNER (quyết định phạm vi); không tự sửa hằng.
4. Muốn xanh mà phải sửa test cũ, sửa mã nguồn chính, nới luật §3.3 hay thêm ALLOWED ngoài §3.6 → CẦN PLANNER.
5. AC8 có failure/error MỚI so với B0 → dừng, không sửa test cũ; báo planner.
6. Kế hoạch sau (sửa `realtime_demo.py`): nếu cần xóa file hay bỏ tính năng người dùng có thể đang dùng → hỏi người dùng
   LÚC ĐÓ (không phải bây giờ).
