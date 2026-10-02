# Tiến độ kế hoạch 11 — sửa vi phạm guard DoD 7 (chặng 1 = B0 + B1)

Kế hoạch: `docs/plans/11-sua-vi-pham-guard-dod7.md`. Nhánh `feat/vslt-complete`. File tạm: `_work/_plan11_tmp/` (không commit).

- P11 (HEAD lúc bắt đầu B0): `4fe3398cdee86bdc0e3610147345f4e4957c21b5`
- Bắt đầu B0: 2026-10-02T19:12:48Z (UTC)
- Trong lúc B0 chạy, orchestrator commit `7547105` (`state: K2 train v3 ERROR ...`, chỉ `M docs/STATE.md`) — không thuộc C11,
  không chạm mã. Mọi mốc dưới đây không đổi vì commit đó (không đổi `src/ backend/ tests/ realtime_demo.py`).

## Trạng thái

- ĐANG LÀM: B1
- Đã xong: B0 (commit `WIP 11: B0 mốc`)
- Còn lại: B1 (chặng 1); B2, B3, B4, B5, B6 (chặng sau, chưa giao)

## B0 — Mốc (XONG)

1. P11 = `4fe3398cdee86bdc0e3610147345f4e4957c21b5`. `git status --porcelain` → `_work/_plan11_tmp/b0_status.txt` (62 dòng; dòng
   không phải `??`: đúng 3 dòng ` D` của người dùng: `"data (2)/Dataset/Labels/label.csv"`, `data/alphabet_landmarks_full.csv`,
   `data/hand_data.csv`). `git diff --stat HEAD -- realtime_demo.py src/data/landmark_extractor.py src/data/vsl_gh_dataset.py
   src/inference/sign_segmenter.py tests/test_backend_source_guard.py` → RỖNG.
2. Đối chiếu dòng §2.2 (grep tại P11): khớp hết — `realtime_demo.py:52` (`candidates = [`), `:266`/`:267` (mock), `:294`/`:296`
   (khung giả), `:330` (`else 30.0`), `:395` (help 'mock'); `src/data/landmark_extractor.py:121` (`or 25.0`);
   `src/data/vsl_gh_dataset.py:58` (dòng "100% identical", chuỗi bắt đầu `:31`); `src/inference/sign_segmenter.py:141` (`else 30.0`).
   Guard: `ENTRYPOINTS` `:46`, `PLAN10_APPROVED_ALLOWED` `:158`, `ALLOWED` `:174`, comment SHRINK `:210`, `KNOWN_VIOLATIONS` `:211`,
   `TestBackendSourceGuard` `:1188`, `TestRegistryComparator` `:1215`, `if __name__` `:1317`. Không lệch.
   (Ghi chú: `vsl_gh_dataset.py:416` có "100%" trong COMMENT — guard không quét comment, không phải finding.)
3. `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m tests.test_backend_source_guard --report _work/_plan11_tmp/b0_guard.json`:
   `[DoD7-guard] report _work/_plan11_tmp/b0_guard.json: by_status={"known": 9, "allowed": 36, "unregistered": 0}
   by_rule={"A-stdlib": 0, "A-numpy": 26, "A-torch": 1, "B-import": 0, "B-name": 0, "C-name": 4, "C-string": 4, "C-result": 1, "D-binding": 6, "D-string": 3}`;
   `generated_by.git_commit = 4fe3398cdee86bdc0e3610147345f4e4957c21b5`, `code_dirty = False`; `n_serving_files = 45`, `n_main_files = 56`.
   Tập khóa known (script so với sổ): `known==registry True`, `allowed==registry True`; 8 nhóm / 9 finding đúng §2.2:
   `realtime_demo.py 52 C-result RealtimeHUD._locate_vietnamese_font`; `266`, `267 C-string RealtimeDemo._open_stream`;
   `294 C-string RealtimeDemo.run`; `330 D-binding RealtimeDemo.run`; `395 C-string main`;
   `src/data/landmark_extractor.py 121 D-binding CleanHolisticExtractor.extract_from_video`;
   `src/data/vsl_gh_dataset.py 31 D-string <module>`; `src/inference/sign_segmenter.py 141 D-binding SignSegmenter._activity`.
   → §7.1 điểm 1 KHÔNG xảy ra.
4. Lệnh AC7 "31 module" (nguyên văn §5 AC7) → `_work/_plan11_tmp/b0_ac2_31.log` (19:13:29Z → 19:17:15Z):
   `Ran 518 tests in 221.707s` / `FAILED (errors=1, skipped=1)`; `[DoD7-guard] known=9 allowed=36`; `[scope] serving=45 main=56`.
   Không-ok (`b0_nonok.txt`, parse bằng `_work/_plan11_tmp/parse_unittest_log.py`):
   - `ERROR setUpClass (tests.test_translation_core.TestVSLTranslationCore)` — `FileNotFoundError: Không tìm thấy checkpoint ViT5 ...`
   - `skip tests.test_vsl_system.TestVSLSystem.test_vsl_predictor_smoke` — `skipped 'Checkpoint checkpoints/stgcn_best.pt not found'`
   Test chập chờn `tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs`: lần này `ok`.
   Đếm theo module (`b0_ac2_31_per_module.json`; `tests.test_ws_throughput` không có test nào được thu):
   alphabet_ckpt_provenance ok 16; alphabet_preprocessing ok 6; archive_private_kaggle ok 27; archive_private_kaggle_r05 ok 14;
   archive_step4_kaggle ok 24; aspect_correction ok 3; backend_model_unavailable ok 5; backend_source_guard ok 24; cors_origin_bind ok 21;
   fingerspelling_api ok 11; fingerspelling_compose ok 28; fingerspelling_deployed ok 9; fingerspelling_limits ok 48;
   frontend_contract ok 71; hand_landmarks_ws ok 9; hand_live_equivalence ok 4; harmonized ok 6; harmonized_live ok 10;
   live_harmonized_equivalence ok 9; private_artifacts ok 8; realtime ok 3; report_step4 ok 105; sign_segmenter ok 15;
   split_guards ok 6; status_privacy ok 5; translation_core ERROR 1 (setUpClass); unified_split_integrity ok 4;
   vsl_system ok 5 + skip 1; ws_dropped_frames ok 3; ws_live_contract ok 18.
   `git status --porcelain` trước/sau lần chạy: giống hệt (`b0_status_before_ac2.txt` == `b0_status_after_ac2.txt`).
   `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.data.test_vsl_gh_dataset -v` → `_work/_plan11_tmp/b0_vslgh.log`:
   `Ran 21 tests in 2.655s` / `FAILED (failures=1)`; 20 ok; FAIL có sẵn
   `tests.data.test_vsl_gh_dataset.TestVSLGHContinuousDataset.test_19_synthesized_annotations_tracking` (`AssertionError: 0 != 2`,
   `tests/data/test_vsl_gh_dataset.py:285`). Đây là MỐC (có từ trước kế hoạch 11); B4 so từng test với log này.
5. Đếm video thiếu fps: `PYTHONIOENCODING=utf-8 .venv/Scripts/python _work/_plan11_tmp/count_fps_metadata.py` →
   `_work/_plan11_tmp/b0_fps_metadata.json` (`generated_by.git_commit = 7547105519badfb4d000878141bcc8e9517b8020`,
   `generated_at_utc = 2026-10-02T19:14:38Z`, cv2 5.0.0). Kết quả (chép từ JSON):
   `totals {"n_videos": 7312, "n_fps_missing": 0, "n_open_failed": 0}`;
   `data/Dataset/Videos` 4362/0/0; `data/external/hauuto_raw` 640/0/0; `data/raw_tudienngonngukyhieu/videos` 435/0/0;
   `data/vsl_alphabet_pilot/videos` 1875/0/0 (n_videos/n_fps_missing/n_open_failed). Không có thư mục nào thiếu (`missing_dirs: []`).
   → §7.1 điểm 2 KHÔNG xảy ra; B3 được phép làm (chặng sau).
6. `sha256sum` mọi file trong `checkpoints/` → `_work/_plan11_tmp/b0_ckpt.txt` (3 file: `alphabet_best.pt`, `stgcn_tier2_indomain.pt`,
   `stgcn_unified_best.pt`; không có `stgcn_best.pt`, không có `vit5_stage*/`).
7. GitNexus: `.gitnexus/meta.json` lastCommit trước = `ab0d740`; `git diff --stat ab0d740 HEAD -- src backend realtime_demo.py tests` rỗng.
   Vẫn chạy `node .gitnexus/run.cjs analyze --index-only` (exit 0, 19 s; cảnh báo FTS/BM25 "search index build failed" — không ảnh
   hưởng impact/detect-changes) → lastCommit `7547105`. Log `_work/_plan11_tmp/b0_analyze.log`.

## B1 — K1 TestRegistryBaseline

(đang làm)

## Nhật ký impact (GitNexus)

- B1 (đã chạy trước khi sửa file; symbol CHỈ ĐỌC, B1 không sửa chúng):
  `node .gitnexus/run.cjs impact "compare_registry" --direction upstream --repo .` → `risk: CRITICAL`, `riskSharedAxes: MEDIUM`,
  impactedCount 47, direct 1 (`test_a_tree_matches_registry`, filePath rỗng), depth 2: 39 nút = các FILE `kaggle/*`, `scripts/*`,
  `train.py`, `src/data/sentence_split.py`, `src/inference/ensemble.py`, `src/training/train_cslr.py`… (log
  `_work/_plan11_tmp/b1_impact_compare_registry.txt`).
  `impact "registry_totals"` → `risk: CRITICAL`, cùng hình (direct 1 = `test_c_summary_line`, filePath rỗng; depth 2 cùng 39 file).
  **CẢNH BÁO (CRITICAL theo chỉ số GitNexus) — đánh giá: KHÔNG THẬT.** Xác nhận bằng `git grep -n -E
  "compare_registry|registry_totals|test_a_tree_matches_registry"`: caller thật DUY NHẤT ở `tests/test_backend_source_guard.py`
  (`:1193`, `:1211`, `:1249`, `:1259`, `:1265`, `:1269`); ngoài ra chỉ tài liệu `docs/plans/10-*`, `11-*`, `docs/reviews/*`. Không file
  kaggle/scripts/src nào gọi hàm test hay hàm của guard (nút depth-1 không có filePath → index gán nhầm "caller của phương thức test"
  thành mọi file có lời gọi trùng tên). B1 KHÔNG sửa hai symbol này (chỉ thêm hàm/lớp mới cuối file) → §7.1 điểm 6 ("CRITICAL cho
  symbol sắp sửa") không áp dụng.

## Nhật ký detect-changes (trước mỗi commit)
- B0 commit (`WIP 11: B0 mốc`): `node .gitnexus/run.cjs analyze --index-only` (exit 0) rồi
  `node .gitnexus/run.cjs detect-changes --scope all --repo .` → `Diff touched 3 file(s) but no indexed symbols overlap those hunks —
  not a clean tree.` (3 file = `git diff HEAD --name-only`: đúng 3 dòng ` D` của người dùng; `11-progress.md` mới chưa track). risk = không
  có symbol bị chạm (không có partial/truncated).
