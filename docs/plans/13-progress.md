# Kế hoạch 13 — tiến độ (coder)

Kế hoạch: `docs/plans/13-train-lai-checkpoint-thieu.md`. Nhánh `feat/vslt-complete`, mốc B0 (HEAD lúc bắt đầu) `3bdd72f`.
Phạm vi lượt 1: B0–B2 (dừng sau B2, báo orchestrator). Q1–Q3 chưa trả lời → dùng mặc định §7.1 (không ảnh hưởng B0–B2).
Tệp tạm: `_work/_plan13_tmp/`.

## Bước đã xong

### B0 — kiểm kê CHỈ ĐỌC (log `_work/_plan13_tmp/B0_*.txt`)
- Mốc: `git status --porcelain` 62 dòng (`B0_git_status_porcelain.txt`), HEAD lúc chụp `3bdd72f`; 3 dòng ` D` của người dùng
  còn nguyên (`data (2)/Dataset/Labels/label.csv`, `data/alphabet_landmarks_full.csv`, `data/hand_data.csv`).
- Cách sinh vocab gốc (`B0_git_history.txt`): `git log --all -S gloss_vocab_canonical` → 17 commit, `-S from_canonical_dataset` → 2,
  `-S vie_vsl_10k_cleaned` → 7; xem diff 3 commit mã (429b289, 6f50af1, 536c7c5): mọi dòng chỉ là NƠI ĐỌC; 0 dòng bị xóa chứa tên file;
  `git log --all -G 'vocab\.save\(|vocabulary\.save\(|\.save\(.*vocab'` → 0; `git grep` writer hiện tại → 0.
  ⇒ KHÔNG tìm thấy cách sinh gốc trong lịch sử git → B2 dùng `VSLGlossVocabulary.from_canonical_dataset` theo §3.4(a), ghi LF.
- Thư viện `.venv` (`B0_libs.txt`): Python 3.11.9; torch 2.6.0+cu124; transformers 4.57.6; tokenizers 0.22.2; sentencepiece 0.2.2;
  safetensors 0.8.0.
- Tier 1 (`B0_tier1_inputs.txt`, lệnh `.venv/Scripts/python _work/_plan13_tmp/b0_tier1_inventory.py`): train 74 dòng (50 lớp),
  val 13 (12 lớp), test 71 (50 lớp); 158 `video_id` duy nhất, 50 lớp hợp; npz phẳng có đủ 158/158, thiếu 0; tổng 9951449 byte;
  `tier1_grouped_classes.txt` 50 dòng.
  **Lệch so với kế hoạch §2.2/R2:** 4 file `data/splits/folds/tier1_grouped_*` ĐANG ĐƯỢC TRACK trong git (`git ls-files` trả đủ 4),
  không phải untracked. Không ảnh hưởng B0–B2; B3/B6 vẫn đóng gói như kế hoạch (bản clone trên Kaggle cũng có sẵn 4 file này).
  `experiments/stgcn/` tracked 6 file (benchmark_results.json, classification_report.csv, confusion_matrix.png, history.json,
  smoke_history.json, training_curve.png) — `train.py`/`evaluate_test.py` sẽ ghi đè các file này, chỉ được xảy ra trong bản clone Kaggle (§3.1.5).
- `data/external/vsl_gh/keypoints_frontal/*.npy`: 4200. `dataset_canonical.json` có (6443220 byte).
- Đích CHƯA tồn tại (`B0_targets.txt`): `checkpoints/stgcn_best.pt`, `cslr_best.pt`, `vit5_stage1`, `vit5_stage2`,
  `data/external/vsl_gh/gloss_vocab_canonical.txt`, `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl` — đều absent.
  `checkpoints/` hiện có 3 file (alphabet_best.pt, stgcn_tier2_indomain.pt, stgcn_unified_best.pt); link dưới checkpoints + data/external: 0.
- Push: GitHub `feat/vslt-complete` = `eea8906`; local đi trước 5 commit (44887b3…6048042), sau 0 ⇒ CHƯA push tới HEAD.
  Theo kế hoạch, push ở B5 (commit ghim) — B0 chỉ ghi nhận.
- GitNexus: `node .gitnexus/run.cjs analyze --index-only` chạy xong (incremental; FTS build lỗi — "keyword search degraded",
  graph OK) — log `_work/_plan13_tmp/gitnexus_analyze_B0.txt`.

### B1 — gỡ Modal (§3.10). Log: `_work/_plan13_tmp/B1_*.txt`, `B1_ac2_31.log`, `B1_ac2_compare.txt`
- Impact TRƯỚC khi xóa (`B1_impact.txt`, sau `analyze --index-only`): `node .gitnexus/run.cjs impact "<s>" --direction upstream --repo .`
  cho `check_cloud_environment`, `run_cslr_on_modal`, `write_file_to_volume`, `read_file_from_volume`, `list_volume_files`, và
  `impact "main" --file src/training/modal_runner.py --include-tests` → cả 6: `"impactedCount": 0`, `"risk": "UNKNOWN"`, riskNote
  "No callers resolved. Absence of edges is not evidence the symbol is unused…". Không HIGH/CRITICAL.
- Đối chiếu bằng grep (vì UNKNOWN; `B1_grep_before.txt`): `git grep -n -i -E 'modal_runner|run_cslr_on_modal|vslt-data-volume|import modal|from modal|modal\.(App|Volume|Image)' -- src scripts backend tests kaggle configs frontend/src`
  → mọi dòng nằm TRONG `src/training/modal_runner.py`; tên 4 hàm còn lại chỉ xuất hiện trong chính file đó (các lệnh `.remote()` nội bộ);
  `src/training/__init__.py` chỉ export `VSLTrainer`. Mốc AC1 frontend: `git grep -n -i modal -- frontend/src` → đúng 1 dòng
  `frontend/src/components/Dictionary.jsx:143: {/* Video Player Modal */}` (UI, giữ nguyên).
- `git rm src/training/modal_runner.py`. **Sự cố quy trình (không mất dữ liệu):** trong lúc thao tác detect-changes, orchestrator commit
  `84c90e4` ("state: quyết định người dùng Q1 …") và commit đó đã cuốn theo thay đổi ĐÃ STAGE của coder (xóa `modal_runner.py`, 261 dòng).
  ⇒ việc gỡ file nằm ở commit `84c90e4` (không có commit riêng `WIP 13: B1`). Nội dung đúng như dự định; không sửa lịch sử.
  Dòng ghi chú ở `docs/plans/12-khoi-phuc-du-lieu.md` (§8.1 mục 2) dẫn tới `84c90e4` (+1 dòng, 0 xóa — `git diff --numstat` `1 0`).
- AC1 sau khi gỡ (`B1_ac1_after.txt`): grep trên `src scripts backend tests kaggle configs` → 0 dòng; `frontend/src` → đúng dòng
  Dictionary.jsx như mốc; `git ls-files src/training/modal_runner.py` → rỗng; `.venv/Scripts/python -c "import src.training"` exit 0;
  `tests.test_backend_source_guard`: `Ran 24 tests` `OK` (trước khi gỡ cũng 24 OK; dòng thông tin `[scope] serving=44 main=56` → `main=55`).
- Hồi quy AC2-06 (lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1028`, chạy trên cây có B1): `Ran 518 tests in 1141.450s`,
  `FAILED (errors=1, skipped=1)`; so theo module với `_work/_plan12_tmp/ac2_31_B9.log` bằng `_work/_plan13_tmp/ac2_compare.py`
  (bản sao của script kế hoạch 12) → mọi module GIỐNG HỆT mốc 12-B9; non-ok y như mốc: ERROR setUpClass `test_translation_core` (thiếu ViT5),
  skip `test_vsl_predictor_smoke` (`stgcn_best.pt not found`).
- Chưa làm (cố ý, để B12): dòng "Modal: không dùng — … đã gỡ ngày <D> (kế hoạch 13)" ở `docs/cloud_training.md` — §3.9 định nghĩa `<D>` = ngày
  coder làm B5, chưa cố định; làm cùng các dòng §3.9 khác ở B12.
- Sau xóa: `node .gitnexus/run.cjs analyze --index-only` (log `_work/_plan13_tmp/gitnexus_analyze_B1.txt`).

### B2 — `scripts/retrain_digest.py` + `scripts/build_gloss_vocab_canonical.py` + `tests/test_retrain_tools.py`. Log: `_work/_plan13_tmp/B2_*`
- Impact: chỉ THÊM file mới, không sửa symbol có sẵn (`VSLGlossVocabulary` chỉ được gọi, không đổi) ⇒ không cần impact sửa.
- Test viết trước: `B2_test_red.log` — `ModuleNotFoundError: No module named 'build_gloss_vocab_canonical'` (FAILED errors=1).
- `retrain_digest.py`: `sha256_file`, `lf_sha256` (chỉ thay cặp CRLF→LF, giữ CR lẻ), `digest_entries`, `dir_digest(directory, pattern, names)`
  (file thường ngay trong thư mục, không đệ quy; `names` = đúng danh sách, thiếu → FileNotFoundError, tên có đường dẫn/trùng → ValueError),
  CLI `sha256 | lf-sha256 | dir` in 1 JSON; chỉ đọc.
- `build_gloss_vocab_canonical.py --canonical … --out …`: thứ tự token lấy từ `VSLGlossVocabulary.from_canonical_dataset` (B0: không có
  cách sinh gốc trong git); ghi bytes UTF-8, mỗi token + LF; `--out` đã có → exit 2 (mở `xb`, không ghi đè kể cả khi đua); canonical thiếu → 2;
  token chứa CR/LF → exit 3, không tạo file; in JSON `out, n_tokens, sha256, vocab_hash16, canonical_lf_sha256`.
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools -v` → `Ran 15 tests` `OK`, 0 skip
  (`B2_test_green.log`; chạy lại ở commit e02ed14 cũng `Ran 15` `OK` — `B2_vocab_e02ed14.txt`). Thư mục tạm của test nằm dưới
  `_work/_test_tmp/` (tự dọn; không dùng thư mục tạm hệ thống). Phần còn lại của `test_retrain_tools` (train.py --seed, archive, preregister)
  thuộc B4a/B4b/B5.
- Vocab thật (sinh ở commit e02ed14, code sạch): `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/build_gloss_vocab_canonical.py
  --canonical data/external/vsl_gh/dataset_canonical.json --out _work/_plan13_tmp/vocab_e02ed14/gloss_vocab_canonical.txt` → exit 0, JSON
  `_work/_plan13_tmp/vocab_e02ed14/build_output.json`: `n_tokens` 372 (== tham chiếu `docs/vsl_gh_dataset.md:19` ⇒ KHÔNG chạm §7.2),
  `sha256` `dd7bc3da8f83e1e3400a85a0bfc4a7d8e882224647a23279a63b8f31d3601d11`, `vocab_hash16` `dd7bc3da8f83e1e3`,
  `canonical_lf_sha256` `d53ab70100e2b2cd70ed32ec6893aa0bcdffab0c4389f27b7d3b8838f6c9a881`.
  Kiểm: 372 dòng, 0 byte CR, dòng 1 `<blank>`, dòng 2 `<unk>`, byte cuối `0a`; bằng hệt byte (`cmp`) bản sinh trước commit
  (`_work/_plan13_tmp/vocab/`); `VSLGlossVocabulary.from_file` đọc lại: 372, ánh xạ == `from_canonical_dataset`, blank 0, unk 1.
  Chạy lại vào đích đã có → exit 2, sha256 đích không đổi (`B2_vocab_real.txt`).
- Ghi nhận cho B5/R3: `dataset_canonical.json` local có 285051 byte CR (ghi chế độ văn bản trên Windows) — sha256 thô
  `8470076fe737aa29cb59702f9b1265419b9c7f1041648dcbe97bf7e214a9d1ea` ≠ `lf_sha256` ở trên ⇒ preflight phải so `lf_sha256`.
- Chưa đặt vocab vào `data/external/vsl_gh/` (đặt ở B11 theo §3.5).
- Lưu ý cho planner (Q1 = (ii), STATE 10:05): §3.8(ii) ghi "vocab chỉ từ câu train". Vocab B2 dựng từ TOÀN BỘ `dataset_canonical.json`
  (đúng AC2 hiện hành, 372). Nếu Lần sửa 1 đổi nguồn vocab, script nhận `--canonical` bất kỳ; có thể cần thêm tùy chọn lọc câu — chưa làm.

## Đang làm
- (không) — lượt 1 (B0–B2) xong; dừng, báo orchestrator.

## Còn lại
- B3–B13 (lượt sau). Lưu ý: Q1 đã trả lời (ii) (STATE 10:05) → cần planner Lần sửa 1 trước B3.

## Sổ GPU (kế hoạch 13)
| Job | Phiên (phút, từ env.json) | Ghi chú |
|---|---|---|
| (chưa có job) | | |

## Nhật ký detect-changes
| Bước | Lệnh | Kết quả (nguyên văn risk) |
|---|---|---|
| B0-start (6048042) | `node .gitnexus/run.cjs detect-changes --scope staged --repo .` (index cũ dded0a6) | "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_B0start.txt`) |
| B0 | như trên (sau analyze) | "Changes: 1 files, 1 symbols / Affected processes: 34 / Risk level: critical" — symbol duy nhất: `Section Kế hoạch 13 — tiến độ (coder) → docs/plans/13-progress.md` (mục markdown); đối chiếu: diff chỉ là 1 file .md, không mã nào đọc file này (`git grep -n 13-progress -- src scripts backend tests` → 0) ⇒ nối nhầm của index, không có rủi ro thực (`dc_B0.txt`) |
| B1 (xóa file, đã lọt vào 84c90e4) | `detect-changes --scope staged` khi chỉ stage `D src/training/modal_runner.py` | "No changes detected." (`dc_B1a.txt`); `--scope all` cùng lúc: "Diff touched 3 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_B1a_all.txt`) ⇒ công cụ không thấy symbol của file bị xóa; đã đối chiếu bằng impact (6× UNKNOWN, 0 caller) + grep (0 tham chiếu ngoài file) |
| B1 (docs) | `detect-changes --scope staged` (sau analyze) | "Changes: 2 files, 1 symbols / Affected processes: 33 / Risk level: critical" — symbol duy nhất: `Section Kế hoạch 12 — Khôi phục dữ liệu sau sự cố 30/9 23:42 → docs/plans/12-khoi-phuc-du-lieu.md` (mục markdown, +1 dòng); không mã nào ĐỌC file kế hoạch (`git grep -n 12-khoi-phuc -- src scripts backend tests` → 1 dòng: docstring `scripts/check_restored_data.py:1`, chỉ là chú thích — đính chính ở commit B2, bản ghi trước ghi nhầm "→ 0") ⇒ nối nhầm của index (`dc_B1.txt`) |
| B2 (WIP e02ed14) | `detect-changes --scope staged` (3 file mới) | "Changes: 3 files, 41 symbols / Affected processes: 4 / Risk level: medium" — luồng: `Main → From_canonical_dataset`, `Main → _check_names`, `Main → Digest_entries`, `Main → Sha256_file` (đều là `main` của 2 script mới gọi hàm của chính nó; không symbol có sẵn nào bị sửa) (`dc_B2wip.txt`) |
| B2 (progress) | `detect-changes --scope staged` | "Changes: 1 files, 1 symbols / Risk level: critical" — symbol duy nhất `Section Kế hoạch 13 — tiến độ (coder) → docs/plans/13-progress.md` (markdown; như B0 — nối nhầm của index) (`dc_B2.txt`) |
