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

### B2a [LS1] — split câu v1 + guard G1. Log: `_work/_plan13_tmp/B2a_*`
- Lượt 2 (sau Lần sửa 1 `4f714c6`), mốc HEAD `1425863`. Phạm vi: B2a → B2b → B2c rồi dừng.
- Impact: chỉ THÊM file mới (`git diff --cached --diff-filter=M` → 0 file sửa), không sửa symbol có sẵn. GitNexus `analyze --index-only`
  chạy trước (`gitnexus_analyze_B2a.txt`; FTS vẫn "degraded", graph OK).
- Test viết trước: `B2a_test_red.log` — `ImportError: cannot import name 'sentence_split' from 'src.data'` (FAILED errors=1).
- `src/data/sentence_split.py` (mô-đun dùng chung §0.3): `make_split_dict` (kiểm bố cục canonical: người ký ↔ `split` = S01–S04 train,
  S05 val, S06 test, đúng SENT001..SENT300; V = `sorted(random.Random(seed).sample(sorted(SENT001..SENT270), 30))`, T = SENT271..SENT300),
  `validate_split_dict`/`load_sentence_split` (rời nhau, phủ đủ, 240/30/30, T == SENT271..300, V ⊂ SENT001..270, không trùng, `signer_split`
  đúng, `version`), `select_vslgh_samples` (người ký × câu, giữ thứ tự; mẫu lệch người ký ↔ `split` → ValueError, không lọc im lặng),
  `collect_glosses`, `heldout_texts` (mọi người ký, mọi lần lặp), `match_heldout` (L1 → L2 → near_dup, nguồn trước đích; Jaccard so bằng số
  nguyên 5·∩ ≥ 4·∪; L1 = `src/translation/text_normalizer.py`, không viết lại; L2 = chữ thường + BỎ `.,!?;:"'()[]{}…` + gộp khoảng trắng).
- **Giả định (ghi để reviewer kiểm):** định danh file split `sha256` = sha256 của nội dung sau CRLF→LF (`split_file_sha256`). Lý do: git ở máy này
  `core.autocrlf=true` (`C:/Program Files/Git/etc/gitconfig`), không có `.gitattributes` (không được thêm — ngoài AC0) ⇒ checkout Windows có thể biến
  file thành CRLF; blob git và bản trên Kaggle là LF. File sinh ra chỉ có LF nên giá trị này == sha256 byte của file vừa sinh (kiểm dưới).
- `scripts/make_vslgh_sentence_split.py --canonical … --seed N --out …` (từ chối ghi đè → 2, canonical thiếu → 2, bố cục sai → 3; ghi LF, `xb`).
- Test `tests/test_sentence_split_guard.py` (G1, dữ liệu giả trong `_work/_test_tmp/`): `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest
  tests.test_sentence_split_guard -v` → `Ran 26 tests` `OK`, 0 skip (`B2a_test_green.log`).
- File split thật: `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/make_vslgh_sentence_split.py --canonical data/external/vsl_gh/dataset_canonical.json
  --seed 42 --out configs/vslgh_sentence_split_v1.json` (Python 3.11.9 `.venv`, code tại HEAD 1425863 + file B2a chưa commit) → exit 0, JSON
  `_work/_plan13_tmp/B2a_make_split.json`: `sha256` `289b2ac158419d6a5e7487a256bdb9a6bf8fbac9bc76fb167fbfa9a86d8421a4`, 240/30/30, seed 42,
  `canonical_lf_sha256` `d53ab701…a881` (== B2). Tái sinh vào `_work/_plan13_tmp/split_regen/` → `cmp` IDENTICAL; chạy lại vào đích đã có → exit 2.
  `sha256sum` file == `load_sentence_split(...).sha256` (cùng giá trị trên, file 0 byte CR). Danh sách V nằm trong file (nguồn sự thật).
- detect-changes `--scope staged` (4 file mới): "Changes: 4 files, 86 symbols / Affected processes: 241 / Risk level: critical" (`dc_B2a.txt`).
  Đối chiếu: `git diff --cached --name-status` → 4 dòng `A`, 0 `M`; luồng bị liệt kê đều qua `main` (nối nhầm `main` của script mới vào mọi `main`
  — đã biết từ 12-progress B5/B8); `git grep sentence_split HEAD -- src scripts backend tests` → 0 (chưa caller nào) ⇒ không rủi ro thực.

### B2b [LS1] — tùy chọn split câu ở 3 dataset (commit WIP `9146f6f`). Log: `_work/_plan13_tmp/B2b_*`
- Impact TRƯỚC khi sửa (`B2b_impact.txt`, sau `analyze --index-only`): `VSLGHContinuousDataset`, `VSLGHTextDataset`, `Clean10kDataset` →
  `"impactedCount": 0`, `"risk": "UNKNOWN"` (riskNote "No callers resolved…"); `_filter_samples` → `impactedCount 1`, `"risk": "LOW"` (gọi từ
  `__init__`); `impact "__init__" --file src/translation/dataset.py` → `"risk": "CRITICAL"`, 53 — NHƯNG `target.id` =
  `Class:src/models/transformer_model.py:MaskedTemporalAttention` (index nhận nhầm symbol, `B2b_impact_init_translation.json`);
  `--file src/data/vsl_gh_dataset.py` → UNKNOWN. Đối chiếu bằng grep (`B2b_grep_callers.txt`, `git grep -n -E "VSLGHContinuousDataset\(|VSLGHTextDataset\(|Clean10kDataset\(" -- src scripts backend tests kaggle`):
  caller thật = `train_cslr.py:226,234,359,367,375`, `scripts/evaluate_cslr_s06.py:39`, `scripts/extract_cslr_predictions.py:31`,
  `train_translation_stage1.py:60-61`, `train_translation_stage2.py:71-72`, `tests/data/test_vsl_gh_dataset.py` — không ai truyền tham số mới ⇒
  hành vi mặc định của mọi caller không đổi (chứng minh dưới) ⇒ không chạm §7.2-8.
- Test viết trước, đỏ trên mã HEAD (sửa mã đã được cất vào `_work/_plan13_tmp/b2b_edited/`, file trả về nội dung HEAD bằng `git show`, chạy test,
  rồi chép lại): `B2b_test_red.log` — `FAILED (errors=9, skipped=1)`: `TypeError … unexpected keyword argument 'sentence_split'` ×6,
  `'exclude_heldout'` ×1, `AttributeError … 'excluded'` / `'sentence_split'` ×2.
- Sửa (chỉ THÊM tham số cuối, mặc định None; 2 dòng "xóa" trong diff là 2 câu lệnh cũ được đưa nguyên văn vào nhánh `else`):
  `VSLGHContinuousDataset(…, sentence_split=None)` — có → bắt buộc `split ∈ {train,val,test}` và không LOSO (ValueError), mẫu =
  `select_vslgh_samples`; nếu không truyền `vocabulary` thì vocab mặc định dựng từ mẫu TRAIN của split (giả định của coder, theo §0.4 — kế hoạch
  không nói; `train_cslr.py` luôn truyền vocab từ file nên không ảnh hưởng đường train). `VSLGHTextDataset(…, sentence_split=None)` — train/val/test
  lấy ID từ file, `all` không đổi. `Clean10kDataset(…, exclude_heldout=None)` — sau bước chia 90/10 cũ, bỏ mục `match_heldout`, giữ
  `excluded` (`id` + `rule`/`side`/`sentence_ids`) và `excluded_ids`; None → `excluded == []`, mẫu y cũ.
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_sentence_split_guard -v` → `Ran 39 tests` `OK (skipped=1)`
  (`B2b_test_green.log`). Skip duy nhất: `test_vit5_stage1_clean10k_no_heldout_match` — "local data not present: …vie_vsl_10k_cleaned.jsonl
  (restored data; required from plan 13 B11)" (file sinh ở B3, đặt ở B11; AC8-c đòi 0 skip ở B11). G2 cần thêm (B5/B11): so `counts_after_split`
  và sha256 với preregistration.
- Hành vi mặc định trên DỮ LIỆU THẬT == mã ở `0a18183` (`_work/_plan13_tmp/b2b_default_equiv.py` nạp bản cũ từ `git show 0a18183:…`):
  `B2b_default_equiv.json` `"all_same": true` cho 22 cấu hình — `VSLGHContinuousDataset` split None/train/val/test + LOSO S01–S06 × train/test
  (mẫu + vocab), `VSLGHTextDataset` train/val/test/all, `Clean10kDataset` train/val (trên `vie_vsl_10k.jsonl` vì bản cleaned chưa có — cùng logic lớp).
- Số mẫu sau split (code, `B2b_counts.json`): CSLR train 2880 / val 30 / test 30; ViT5 s2 240 / 30 / 30.
- Đột biến guard (AC11-c, chỉ bản sao / vá lúc chạy, `_work/_plan13_tmp/mut/`): M1 bản sao split thêm SENT271 vào train
  (`VSLT_GUARD_SPLIT=…`) → `FAILED (errors=1)` "split sets overlap: … train&test=['SENT271']"; M2 đổi chỗ SENT271 ↔ 1 ID train → `FAILED`
  "test sentences must be exactly SENT271..SENT300"; M3 vá `select_vslgh_samples` bỏ lọc câu → `test_cslr_dataset_no_leak` FAIL (liệt kê
  SENT271–SENT300); M4 vá `VSLGHTextDataset` bỏ `sentence_split` → `test_vit5_stage2_dataset_no_leak` FAIL; không đột biến → `OK (skipped=1)`.
  Còn lại cho B5/B11: đột biến bản sao `*_used_ids.json` (G3) và bản sao 10k thêm cặp trùng L1 — cặp đó bị `exclude_heldout` loại nên chỉ bị bắt
  khi G2 so số mẫu/số bị loại với `counts_after_split`/`clean10k_excluded` của preregistration (B5).
- Phát hiện ngoài phạm vi (KHÔNG sửa): `tests.data.test_vsl_gh_dataset` (không thuộc AC2-06) `Ran 21` `FAILED (failures=1)` —
  `test_19_synthesized_annotations_tracking` `0 != 2`: `dataset_canonical.json` khôi phục (kế hoạch 12) có 0 trường `annotation_source`
  (`grep -c` → 0) ⇒ do dữ liệu, không do mã (mẫu mặc định == mã cũ, ở trên). Log `B2b_test_vsl_gh_dataset.log`.
- detect-changes `--scope staged` (3 file M): "Changes: 3 files, 36 symbols / Affected processes: 4 / Risk level: medium" — luồng
  `__init__ → _id_list | Split_file_sha256 | Ids | Signers` (lời gọi mới vào `sentence_split`) (`dc_B2b.txt`).
- Hồi quy AC2-06 (lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1028`, cây `9146f6f` + mã B2c chưa commit — không module nào của AC2-06
  nạp script vocab): `Ran 518 tests in 1129.152s` `FAILED (failures=1, errors=1, skipped=1)` (`B2b_ac2_31.log`); so theo module với
  `_work/_plan12_tmp/ac2_31_B9.log` (`B2b_ac2_compare.txt`): 30/31 module giống hệt mốc (gồm ERROR setUpClass `test_translation_core`, skip
  `stgcn_best.pt not found`); khác duy nhất `tests.test_hand_landmarks_ws` 9/0/0/0 → 8/0/1/0: FAIL `test_reset_segments_and_graphs`
  (`[1, 1, 1, 0] != [1, 1, 1, 1]`, đóng graph khi đóng phiên WS). Chạy lại riêng module 3 lần trên cùng cây: OK / FAIL / OK
  (`B2b_rerun_hand_landmarks_ws_{1,2,3}.log`) ⇒ chập chờn theo thời gian; module này KHÔNG nạp mã đã đổi (`import tests.test_hand_landmarks_ws`
  → 0 module `sentence_split|vsl_gh_dataset|translation.dataset|build_gloss` trong `sys.modules`, `B2b_hand_ws_imports.txt`). Không sửa test
  (ngoài phạm vi; báo orchestrator). ⇒ Mốc 518/1E/1S giữ ở mọi module chịu ảnh hưởng.

### B2c [LS1] — vocab chỉ từ câu train (commit WIP `059a780`). Log: `_work/_plan13_tmp/B2c_*`, `vocab_train/`
- Impact: `impact "main" --file scripts/build_gloss_vocab_canonical.py` → `"risk": "CRITICAL"`, 53 (danh sách là các kernel `kaggle/vsl-extract-*`,
  `train_alphabet_kernel.py` — nối nhầm `main`, đã biết); `impact "build_tokens"` → CRITICAL 53 cùng kiểu (`end_to_end.py`, `harmonized_live.py`…).
  Đối chiếu grep `git grep -n -E "build_gloss_vocab_canonical|build_tokens" -- src scripts backend tests kaggle` → chỉ chính script + `tests/test_retrain_tools.py`
  ⇒ không caller thật; `build_tokens` không bị sửa.
- Test viết trước: `B2c_test_red.log` — `Ran 20` `FAILED (failures=2, errors=1)` (`build_tokens_train_only` chưa có; tùy chọn chưa có).
- `--sentence-split <json> --split train` (phải đi cùng nhau, `--split` chỉ nhận `train`; file split sai/thiếu → exit 2, không ghi): token =
  `VSLGlossVocabulary(tokens=collect_glosses(select_vslgh_samples(…, "train", split)))` (cùng thứ tự `<blank>`, `<unk>`, sắp xếp; cùng hàm dataset
  B2b dùng); JSON thêm `split, sentence_split, sentence_split_sha256, n_samples_selected, glosses_excluded`. Không tùy chọn → nhánh cũ nguyên văn.
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools -v` → `Ran 20 tests` `OK`, 0 skip (`B2c_test_green.log`);
  `git diff 0373a90 -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0 (15 test B2 nguyên văn, chỉ thêm 5 test).
- Không tùy chọn trên dữ liệu thật (ở `059a780`): sinh vào `_work/_plan13_tmp/vocab_full_059a780/` → `cmp` với `vocab_e02ed14/` BẰNG HỆT byte; JSON (bỏ `out`) giống hệt.
- **Vocab train-only (sinh ở commit `059a780`, mã sạch):** `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/build_gloss_vocab_canonical.py
  --canonical data/external/vsl_gh/dataset_canonical.json --out _work/_plan13_tmp/vocab_train/gloss_vocab_canonical.txt
  --sentence-split configs/vslgh_sentence_split_v1.json --split train` → exit 0, JSON `_work/_plan13_tmp/vocab_train/build_output.json`:
  `n_tokens` **322** (≤ 372), `sha256` `c0af13dbdf20e7d5a4dd6644f9c8217d8cfb937e48b7f25c8bf4e021c06213d0`, `vocab_hash16` `c0af13dbdf20e7d5`,
  `n_samples_selected` 2880, `sentence_split_sha256` `289b2ac1…21a4`, `canonical_lf_sha256` `d53ab701…a881`; `glosses_excluded` 50 gloss (danh sách
  trong JSON) == vocab đầy đủ B2 − vocab train (kiểm bằng code). Phân loại mô tả (`vocab_train/excluded_breakdown.json`): 27 chỉ ở câu T, 22 chỉ ở câu V,
  1 ở cả T và V, 0 từ câu train của người ký ngoài train. File: 322 dòng, 0 byte CR, `<blank>`/`<unk>` đầu, byte cuối LF; `VSLGlossVocabulary.from_file`
  → 322, blank 0, unk 1. Chạy lại vào đích đã có → exit 2, sha256 không đổi. Chưa đặt vào `data/external/vsl_gh/` (B11).
  (`glosses_only_in_val` / `glosses_only_in_test` và tỉ lệ OOV token tham chiếu test do `retrain_preregister.py` tính ở B5.)

### B3 — cleaned 10k + gói đầu vào Tier 1 (lượt 3, mốc HEAD `34117fd`). Log: `_work/_plan13_tmp/B3_*`
- Không sửa mã tracked nào (chỉ runner trong `_work/`) ⇒ không cần impact.
- Lệnh: `PYTHONIOENCODING=utf-8 .venv/Scripts/python _work/_plan13_tmp/b3_runner.py` (HEAD `34117fd`, `code_dirty` false cho
  `src scripts configs train.py`) → exit 0; kết quả máy đọc `_work/_plan13_tmp/B3_result.json`, stdout `B3_runner.log`.
- Cách chạy script clean KHÔNG sửa: runner `compile` nguyên văn `scripts/clean_10k_translation_corpus.py` rồi `exec` với `__file__` giả
  = `_work/_plan13_tmp/cleaned/scripts/…` (script suy mọi đường dẫn từ `__file__` ở cấp module, `:14-16`) ⇒ `project_root` = `_work/_plan13_tmp/cleaned/`;
  đầu vào = bản chép byte (`xb`, kiểm sha256) của `data/external/parallel_text/vie_vsl_10k.jsonl`; runner assert `raw_path`/`clean_path` của script
  trỏ đúng vào `_work`. (Biến thể của "importlib + đổi biến đích" §2.2: script không có `main()`, chạy ngay khi nạp nên không đặt lại biến sau nạp được.)
- **cleaned:** `_work/_plan13_tmp/cleaned/data/external/parallel_text/vie_vsl_10k_cleaned.jsonl` — đầu vào 9405 dòng; script in
  identical 2259 / misaligned 6 / fixed 3 / retained **7140** (== tham chiếu `inventory_summary.json:88`); 7140 dòng, 7140 id duy nhất;
  ghi chế độ văn bản Windows ⇒ 7140 CRLF; `sha256` `012e7f555f7fb8c93a4958fa1331f981cfb1b6628e70f78eccf53458ac26d6d0`,
  **`lf_sha256` `f141f64a04d919fc8c9887cc76b2c6cf027c8f996eba3c6df168732d766c1778`** (giá trị so ở preflight — R3).
  Đầu vào: `sha256` `f55df87a…5748`, `lf_sha256` `c1dcceff…40e6`.
- `Clean10kDataset(jsonl_path=…)` không loại: train **6426** / val **714** (== tham chiếu `vit5_stage1_history.json:4-5`).
- `Clean10kDataset(…, exclude_heldout=heldout_texts(canonical, T ∪ V))` (split `289b2ac1…21a4`, canonical `lf_sha256` `d53ab701…a881`):
  train 6426 → **6423** (loại 3: L1/source 1 `PAR_10K_02347`→SENT112; near_dup/source 1 `PAR_10K_03112`→SENT223; near_dup/target 1
  `PAR_10K_05270`→SENT144); val 714 → **713** (loại 1: L1/source `PAR_10K_02536`→SENT141). Tổng loại **4**, cả 4 khớp câu V, **0** khớp câu T.
  Danh sách đầy đủ (id + rule/side/sentence_ids) trong `B3_result.json` → `clean10k_exclude_heldout`. Số này sẽ do `retrain_preregister.py` tính
  lại bằng code ở B5 (preregistration là nguồn chính thức).
- **Gói Tier 1** `_work/_plan13_tmp/src_inputs_tier1/` (bố cục đường dẫn tương đối repo, chép `xb`, sha256 nguồn == đích, 0 link):
  **162 file** = 3 CSV `data/splits/folds/tier1_grouped_{train,val,test}.csv` + `tier1_grouped_classes.txt` + 158 npz
  `data/extracted_keypoints/<video_id>.npz` (đúng 158 `video_id` duy nhất của 3 CSV); tổng 9991844 byte (npz 9951449 == B0).
  `npz` `dir_digest` (158) `88f15ac819942f7acc51093a61e68a6065c50f52f80c6e9a2702cde77359ae88`; digest gói (dòng `"<rel_path> <sha256>\n"` sắp theo
  đường dẫn) `7098e007687a08f5eee7affe7250d6a2437c56cd127dfcbfdb130c2bdb9e33b7`. sha256 từng file trong `B3_result.json` → `tier1_inputs.files`.
  Ghi nhận cho B5/B6: 4 file văn bản Tier 1 tracked với `i/lf w/crlf` (`git ls-files --eol`) ⇒ bản chép là CRLF; `lf_sha256` của từng file ==
  sha256 blob git tại HEAD (train `8d2f6878…`, val `6b663e16…`, test `85e57199…`, classes `29f1a69e…`) ⇒ kernel K1 so `lf_sha256`, không so sha256 thô.
- Chưa đặt cleaned vào `data/external/parallel_text/` (B11, §3.5). Guard G2 `test_vit5_stage1_clean10k_no_heldout_match` vẫn skip tới B11
  (test đọc đường dẫn thật `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl`).

### B4a — `train.py --seed` (lượt 3). Log: `_work/_plan13_tmp/B4a_*`
- Impact TRƯỚC khi sửa (`B4a_impact.txt`, sau `analyze --index-only` — `gitnexus_analyze_B4a.txt`): `impact "main" --file train.py` →
  `"status": "ambiguous"` (2 ứng viên: `train.py:72` và `clone/Vietnamese-Sign-Language-Translation/source/train.py:165`), mỗi ứng viên
  `"risk": "CRITICAL"`, 58; `impact "parse_args" --file train.py` → `"risk": "CRITICAL"`, 58 (luồng `Run_harmonized → …`, `translate_video`… —
  nối nhầm tên `parse_args`/`main` giữa các script, như 12-progress B5/B8). Đối chiếu grep (`B4a_grep_callers.txt`):
  `git grep -n -E "from train import|^\s*import train|train\.main\(|train\.parse_args|[^_a-z]train\.py" -- src scripts backend tests kaggle configs …`
  và `git grep -E "['\"/ ]train\.py"` (trừ docs/reports/md) → chỉ 2 dòng docstring của chính `train.py` ⇒ không caller mã thật; hành vi mặc định
  giữ nguyên (test dưới) ⇒ không chạm §7.2-8.
- Test viết trước (`tests/test_retrain_tools.py`, lớp mới `TestTrainSeed`, 6 test; `main()` dừng bằng stub `get_vsl_dataloaders`, không train):
  `B4a_test_red.log` — `Ran 6` `FAILED (failures=1, errors=5)` (`Namespace` không có `seed`; `train` không có `set_seed`).
- Sửa `train.py` (+21/−0, `git diff --numstat`): `--seed` (int, mặc định None); hàm mới `set_seed(n)` = `random.seed`, `np.random.seed`,
  `torch.manual_seed`, `torch.cuda.manual_seed_all`; trong `main()` gọi TRƯỚC `get_vsl_dataloaders` chỉ khi `args.seed is not None` (in `Seed: N`).
  Không đụng `VSLTrainer`. Test khóa: tùy chọn cũ y nguyên + `seed None`; không `--seed` → không gọi `set_seed`; `--seed 42` → `set_seed(42)` rồi
  mới tới DataLoader; `set_seed` tất định (42 hai lần bằng nhau, 43 khác; trạng thái RNG trả lại sau test).
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools -v` → `Ran 26 tests` `OK`, 0 skip (`B4a_test_green.log`);
  `git diff 0373a90 -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0.

### B4b — `scripts/archive_retrain_kaggle.py` + test API giả (lượt 3). Log: `_work/_plan13_tmp/B4b_*`
- Chỉ THÊM file mới; 2 script archive cũ không sửa (chỉ import helper) ⇒ không cần impact sửa.
- Test viết trước (`TestArchiveRetrainKaggle`, 24 test, scratch dưới `_work/_test_tmp/`, API Kaggle giả — mọi hàm `dataset_*` khác 6 hàm
  được phép đều ghi lại và FAIL): `B4b_test_red.log` — `ModuleNotFoundError: No module named 'archive_retrain_kaggle'` (FAILED errors=1);
  mã được cất ở `_work/_plan13_tmp/b4b_edited/` trong lúc chạy đỏ rồi chuyển lại.
- Script (§3.4c): `stage --src --staging --dataset --title --licence-note` (chép đệ quy, `archive_name` = đường dẫn tương đối `/`→`__`;
  từ chối symlink/junction/reparse point (`os.lstat` + `FILE_ATTRIBUTE_REPARSE_POINT`, không theo link), thư mục rỗng, thành phần tên chứa `__`
  (để `archive_name` đảo được), tên trùng `SHA256SUMS`/`dataset-metadata.json`, chuỗi giống credential (`SECRET_PATTERNS` của
  `archive_private_kaggle`; đuôi văn bản + `.jsonl .yaml .yml .py .sh .cfg .ini .toml`), tổng > 3 GiB, staging đã có, `--src`/`--staging` không
  nằm DƯỚI `_work/` → exit 2; chép `xb` vào `<staging>.partial-*` rồi `os.rename`; lỗi → thư mục dở dang ĐỂ LẠI trong `_work/` (script không
  bao giờ xóa thư mục — quy tắc sau sự cố 30/9; khác script cũ dùng `rmtree`)); `upload` (chỉ `dataset_create_new(folder, public=False,
  dir_mode="skip")`, slug đã có → 5; viết lại thân `upload` vì `archive_step4_kaggle.upload` bắt staging NGOÀI repo — mâu thuẫn §3.4c; dùng lại
  `is_not_found`, `listed_mine`); `verify` (ready, private 2 nguồn, danh sách + kích thước, tải về thư mục mới dưới `--download-dir`, sha256;
  manifest `generated_by{script, command, git_commit, code_dirty, code_dirty_files, kaggle_version, kagglesdk_version, verified_at_utc}`,
  `dataset{ref, url, title, license, description, is_private, is_private_sources, status, total_bytes}`, `files[{rel_path, archive_name,
  size_bytes, sha256, sha256_after_download}]`, `verified{n_files}`; `--manifest-out` trong repo chỉ `reports/retrain_<YYYY-MM-DD>/<tên>_manifest.json`
  hoặc dưới `_work/`, ngoài repo → 2, đích đã có → 2 (mở `x`, không ghi đè)); `restore --manifest --download-dir --dest` (kiểm mọi mục: generator
  == script này, `archive_name` == `rel_path` `/`→`__`, đường dẫn tương đối an toàn; tải, kiểm sha256; kiểm mọi đích trước khi ghi — khác hash → 3,
  KHÔNG ghi file nào; cùng hash → bỏ qua; ghi `xb`). Mã thoát 0/2/3/4/5/6 như `archive_step4_kaggle`.
  Guard nguồn (test): không chứa `public=True`, `dataset_delete`, `dataset_create_version`, `dataset_metadata_update`, `rmtree`, `os.remove(`,
  `os.unlink(`, `os.symlink`, `shutil.copy`. Test không bao giờ tạo symlink/junction thật (phát hiện link được kiểm bằng vá `lstat`).
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools tests.test_archive_step4_kaggle tests.test_archive_private_kaggle`
  → `Ran 101 tests` `OK` (`B4b_test_green.log`; `test_retrain_tools` = 50: 15 B2 + 5 B2c + 6 B4a + 24 B4b), 0 skip;
  `git diff 0373a90 -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0.

### B4c [LS1] — `--sentence-split` cho CSLR + ViT5 s1/s2 (lượt 3). Log: `_work/_plan13_tmp/B4c_*`
- Impact TRƯỚC khi sửa (`B4c_impact.txt`, index tại `7ecaa25`): `impact "train_cslr" --file src/training/train_cslr.py` → `"risk": "CRITICAL"`,
  `impactedCount` 61, `direct` 1; `run_smoke_test` → CRITICAL, 61, `direct` 2; `train_stage1` (`scripts/train_translation_stage1.py`) → CRITICAL, 62,
  `direct` 1; `train_stage2` → CRITICAL, 62, `direct` 1 (luồng liệt kê `Run_harmonized → …`, `translate_video`, `Ws_classification → …` — nối nhầm
  `main`/tên trùng như B4a). Đối chiếu grep (`B4c_grep_callers.txt`, `git grep -n -E "train_cslr\(|run_smoke_test\(|train_stage1\(|train_stage2\(|
  from src.training.train_cslr|import train_cslr|train_translation_stage[12]" -- src scripts backend tests kaggle configs …` + `-- kaggle backend tests
  *.ps1 *.yaml`): caller thật = chỉ nội bộ (`train_cslr.py:351,756,764`, `__main__` của 2 script stage); `scripts/evaluate_cslr_s06.py:21` chỉ import
  `evaluate_cslr` (không sửa); 3 dòng trong test là chú thích ⇒ không caller nào bị đổi hành vi mặc định (test dưới) ⇒ không chạm §7.2-8.
- Test viết trước (`TestB4cSentenceSplitTraining`, 14 test, fixture tổng hợp nhỏ dưới `_work/_test_tmp/`; KHÔNG train: `train_cslr` chạy với
  `total_epochs=0` (không epoch nào); ViT5 dừng ở `DataLoader` đầu tiên, tokenizer/model giả, không tải mạng): `B4c_test_red.log` — `Ran 14`
  `FAILED (failures=2, errors=9)`; 3 test "mặc định không đổi" (`test_cslr_default_unchanged`, `test_stage1_default_unchanged`,
  `test_stage2_default_unchanged`) XANH ngay trên mã cũ (chứng minh chúng mô tả đúng hành vi cũ). Sửa fixture 2 test ViT5 của chính lượt này
  (mini canonical thiếu câu → `heldout_texts`/`VSLGHTextDataset` báo thiếu; đổi sang fixture 300 câu) — `B4c_test_green1.log` → `green2.log`.
- `src/data/sentence_split.py` (+69/−0, chỉ THÊM hàm): `sample_leak_report` (câu train ∈ T/V/ngoài Tr, câu val ∈ T/ngoài V, người ký ngoài split),
  `text_leak_report` (cặp 10k còn `match_heldout`), `vocab_leak_report` (token ≠ gloss train + specials), `assert_no_leak` → dòng
  `LEAK CHECK OK (<job>): …` hoặc `RuntimeError("LEAK CHECK FAILED …")`.
- `src/training/train_cslr.py` (+115/−4; 4 dòng "xóa" = 2 dòng `)` thêm `if … else None`, 1 lời gọi `run_smoke_test` thêm kwarg, 1 `print` cũ đưa
  nguyên văn vào nhánh `if sentence_split is None`): hàm mới `sentence_split_config(path)` (kiểm file, trả `sentence_split_path`, `sentence_split_sha256`),
  `cslr_leak_check` (chọn mẫu train/val bằng `select_vslgh_samples` + kiểm vocab == gloss train + specials; chạy TRƯỚC smoke test và trước
  "CSLR TRAINING STARTED"); `run_smoke_test(…, sentence_split=None)`; `train_cslr`: chỉ khi `config["sentence_split_path"]` có — sha256 khớp config,
  in `LEAK CHECK OK (cslr)`, dataset train/val lọc theo split, KHÔNG dựng test dataset/loader, dataset == tập đã kiểm, ghi `cslr_used_ids.json`
  (`sample_id`, `sentence_id`, `signer_id` train/val; mở `x`), sau history in đúng 1 dòng `TEST DEFERRED (sentence split v1): run scripts/eval_sentsplit.py once`,
  ghi `cslr_train_summary.json` (`test_s06: null`, `test_deferred: true`, mở `x`) và trả về TRƯỚC khối "PRIMARY TEST EVALUATION"; CLI `--sentence-split PATH`
  (thêm 2 khóa config; `--smoke-test-only` truyền split). Không tùy chọn → config không thêm khóa, mọi dòng cũ chạy y nguyên.
- `scripts/train_translation_stage1.py` (+62/−2): `train_stage1(…, sentence_split=None, canonical_json=DEFAULT)`; có split → `exclude_heldout =
  heldout_texts(canonical, T ∪ V)` (hàm `stage1_heldout`), in `LEAK CHECK OK (vit5_stage1)` (kiểm lại chính các cặp sắp dùng), ghi `vit5_stage1_used_ids.json`
  (chỉ ID: `train_ids`, `val_ids`, `excluded` kèm rule/side/sentence_ids/split, `heldout_sentence_ids`, `lf_sha256` của jsonl + canonical), thêm khối
  `sentence_split` vào history; CLI `--sentence-split`, `--canonical-json` (không có `--sentence-split` → `parser.error`). 2 dòng "xóa" = 2 lời gọi
  `Clean10kDataset` thêm `exclude_heldout=heldout` (None khi không tùy chọn = hành vi cũ, B2b).
- `scripts/train_translation_stage2.py` (+25/−2): `train_stage2(…, sentence_split=None)` → `VSLGHTextDataset(split, sentence_split=…)`, `LEAK CHECK OK
  (vit5_stage2)`, `vit5_stage2_used_ids.json`; CLI `--sentence-split`. **Giả định của coder (ngoài chữ kế hoạch, chỉ ở chế độ split):** thiếu stage 1 →
  `FileNotFoundError` thay vì lặng lẽ dùng `VietAI/vit5-base` (công thức đăng ký là s1 → s2); không tùy chọn → fallback cũ giữ nguyên.
- Kiểm trên dữ liệu THẬT (chỉ chọn mẫu, không train, không nạp mẫu test; `.venv/Scripts/python _work/_plan13_tmp/b4c_real_check.py` →
  `B4c_real_check.json`): `LEAK CHECK OK (cslr): n_train_samples=2880, n_val_samples=30, n_train_sentences=240, n_val_sentences=30, n_vocab_tokens=322`
  (vocab train-only B2c); vocab đầy đủ 372 → `LEAK CHECK FAILED (cslr): 50 violation(s)` (đúng 50 gloss B2c loại); `LEAK CHECK OK (vit5_stage1):
  n_items=7136` (train 6423 / val 713, loại 4 ID == B3) trên bản cleaned trong `_work`; `LEAK CHECK OK (vit5_stage2): 240 / 30`.
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools` → `Ran 64 tests` `OK`, 0 skip (`B4c_test_green.log`);
  `tests.test_sentence_split_guard tests.test_backend_source_guard` → `Ran 63` `OK (skipped=1)` (skip = G2 clean10k chờ B11; `B4c_guard_tests.log`);
  `git diff 0373a90 -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0.

### B4d [LS1] — `scripts/eval_sentsplit.py` (§3.12 + `repro_v2`) — chỉ dữ liệu giả, KHÔNG chạy trên dữ liệu thật (lượt 3). Log: `_work/_plan13_tmp/B4d_*`
- Chỉ THÊM file mới (không sửa symbol có sẵn; chỉ gọi `compute_wer`, `levenshtein_distance`, `ctc_greedy_decode`, `tokens_to_words`,
  `select_vslgh_samples`, `VSLGHContinuousDataset`) ⇒ không cần impact sửa.
- Test viết trước (`TestEvalSentsplit`): `B4d_test_red.log` — `ModuleNotFoundError: No module named 'eval_sentsplit'` (FAILED errors=1); mã cất ở
  `_work/_plan13_tmp/b4d_edited/` lúc chạy đỏ. Sửa test của chính lượt này: 1 khẳng định yếu (`assertNotEqual` CI seed 42 vs 7 trùng nhau với 3 dòng × 40
  lần rút) thay bằng tái dựng độc lập luồng `RandomState` cho cả seed 42 và 7 (WER, BLEU A, delta) — `B4d_test_green1.log` → `green2.log`.
- Script: `protocol_template("sentsplit_v1"|"repro_v2")` = dạng code của §3.12/§0.7 (B5 chép vào preregistration); khi chạy, MỌI tham số đọc từ
  `preregistration.evaluation_protocol[_repro_v2]`, `check_protocol` từ chối trường thuật toán không cài đặt (rng, interpolation, paired, lớp BLEU, CPU,
  fallback stage1). Hợp đồng khóa preregistration mà B5 phải ghi: `evaluation_protocol`, `evaluation_protocol_repro_v2`, `sentence_split{path, sha256}`,
  `libs_local{sacrebleu, numpy}`, `vocab{sha256}`, `vocab_full_reference{sha256}`, tùy chọn `inputs{…: {path, sha256|lf_sha256}}`.
  Chạy một lần: đích có → 2; `git status --porcelain -- src scripts configs train.py <prereg>` bẩn → 2; commit thêm preregistration không phải tổ tiên HEAD
  hoặc file có > 1 commit → 2; phiên bản `sacrebleu`/`numpy` ≠ preregistration → 2; thiếu đầu vào → 2; sha256 split/vocab ≠ preregistration, sha256
  `cslr_best.pt` + từng file ViT5 không có trong `--manifest` (JSON manifest hoặc SHA256SUMS, khớp theo tên gốc), `gloss_vocab_hash` checkpoint ≠ vocab,
  `config.sentence_split_sha256` ≠ split, số clip ≠ `expected_n`, người ký ≠ S06, câu ≠ T, thiếu keypoint (không bỏ clip) → 3 — TẤT CẢ trước khi nạp
  clip test; in đúng 1 dòng `EVAL RUN …`; in `PER_SAMPLE …` (dự đoán) TRƯỚC khi tính số (lỗi sau đó không mất dự đoán — §7.2-7). WER chính =
  `compute_wer(pred, gloss THÔ)` + S/D/I/tỉ lệ/N_ref/N_hyp; phụ `wer_vocab_encoded`, `oov`; BLEU = `sacrebleu.metrics.BLEU(tokenize, smooth_method,
  lowercase)` + `signature`; CI = bootstrap GHÉP CẶP một `RandomState(seed)`, cùng `idx` cho WER/S/D/I/BLEU A/BLEU B/delta, `numpy.percentile` (linear);
  `ci_contains_zero` (mô tả). `comparison_to_old` đọc số cũ TỪ `reports/audit_round2/v2_cslr_reliability.json` (kèm sha256 + `file:dòng`), không gõ tay
  (test quét nguồn không chứa 27.98/23.18/32.8/…); `limitations` theo §0.2/R7/R10/R13/R15. `--recompute-from` tính lại `metrics` từ `per_sample`
  (không chạy model) → `identical` + exit 0, khác → 3. `repro_v2` = thuật toán `run_v2_cslr_bootstrap.py:29-133` (RNG toàn cục, thứ tự rút, DP edit).
- Test (12): giao thức == §3.12 (B=1000, seed 42, RandomState, [2.5, 97.5] linear, ghép cặp, 13a/exp/không lowercase, beams 4, max_length 64/128, CPU,
  bs 8, n=30); từ chối giao thức không cài đặt; S/D/I tính tay 3 cặp (S1, D1, I1, N_ref 8 → WER 37.5); BLEU điểm == `sacrebleu.corpus_bleu` mặc định;
  bootstrap tất định + đọc seed/B từ giao thức + tái dựng độc lập luồng ghép cặp; `repro_v2` so với CHÍNH mã gốc `run_v2_cslr_bootstrap.py` (đoạn
  "# 2. Bootstrap…" → trước `v2_results`, đọc từ file, `exec` trên dữ liệu giả) → CI A/B/delta, WER, CI WER bằng hệt; chạy đầy đủ với CSLR/ViT5 giả
  (30 clip S06 × T, JSON đủ khóa AC12, chạy lần 2 → 2 và 0 lời gọi model, `--recompute-from` bằng hệt và 0 lời gọi model, `per_sample` bị sửa → 3);
  từ chối trước mọi lời gọi model (bẩn, không tổ tiên, chưa commit, > 1 commit, lệch phiên bản, lệch vocab, ngoài manifest, thiếu keypoint);
  luật tham số CLI; bước nặng thật (`cslr_predict`, `vit5_generate`) chạy trên model NGẪU NHIÊN TÍ HON dựng trong test (không tải, không train) để bắt
  lỗi nối dây trước lần chạy thật; `git_state` trên file split đã commit (1 commit, tổ tiên HEAD).
- Test: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools tests.test_sentence_split_guard` → `Ran 115 tests` `OK (skipped=1)`
  (`B4d_test_green.log`; `test_retrain_tools` 76 test, 0 skip; skip duy nhất = G2 clean10k chờ B11); `git diff 0373a90 -- tests/test_retrain_tools.py |
  grep -c "^-[^-]"` → 0.

### Hồi quy sau B4c (lượt 3)
- AC2-06 (lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1028`) trên cây `a272df6` (B4c đã commit; B4d chỉ thêm file không thuộc 31 module):
  `Ran 518 tests in 698.018s` `FAILED (errors=1, skipped=1)` (`_work/_plan13_tmp/B4_ac2_31.log`); so theo module với `_work/_plan12_tmp/ac2_31_B9.log`
  (`B4_ac2_compare.txt`): 31/31 module GIỐNG HỆT mốc; non-ok y mốc (ERROR setUpClass `test_translation_core` — thiếu ViT5; skip `stgcn_best.pt not found`).
  `test_hand_landmarks_ws` 9/0/0/0 lần này (chập chờn đã ghi ở B2b, không gặp lại). Dòng `[scope] serving=45 main=56` == B2b.
- Guard: `tests.test_sentence_split_guard` 39 test, `OK (skipped=1)` — G2 `test_vit5_stage1_clean10k_no_heldout_match` VẪN skip (file cleaned chưa đặt vào
  `data/external/parallel_text/`, đặt ở B11). Chạy cùng guard với `VSLT_GUARD_CLEAN10K=<bản cleaned trong _work>` → `Ran 39` `OK`, 0 skip (`B3_guard_with_work_cleaned.log`).
- Ngoài phạm vi, không gặp lại / không sửa: `tests.data.test_vsl_gh_dataset` test_19 (dữ liệu khôi phục thiếu `annotation_source`) — không chạy lại ở lượt này.

### Sửa sau review giữa (`docs/reviews/13-review-mid.md`, lượt 4, mốc HEAD `a22b3d9`). Log: `_work/_plan13_tmp/E_*`, `G2ref_*`
- G2 (vấn đề 1.A): THÊM `TestG2RegisteredReference` vào `tests/test_sentence_split_guard.py` (0 dòng cũ bị xóa/sửa; `git diff --numstat` → `98 0`).
  So với giá trị ĐĂNG KÝ TRƯỚC, không tính lại bằng `match_heldout`: preregistration (`reports/retrain_*/preregistration.json`, đúng 1 file, hoặc
  `VSLT_GUARD_PREREG`) → `sentence_split.sha256`, `counts_after_split.{clean10k{train,val}, cslr{train,val,test}, vslgh_text{train,val,test}}`,
  `clean10k_excluded{n_train, n_val, ids}`; CHƯA có preregistration → số B3/B2b do code tính và ghi trong `_work/_plan13_tmp/B3_result.json`
  (`b3_runner.py`, commit `34117fd`, code_dirty false: train 6423 / val 713, loại 3 + 1, 4 ID) + `B2b_counts.json` (cslr 2880/30/30, vit5_s2 240/30/30).
  Có dữ liệu mà không có tham chiếu → FAIL; thiếu dữ liệu → skip (như G2).
  Kết quả: mặc định `Ran 3` `OK (skipped=1)` (10k chưa đặt) (`G2ref_default.log`); với bản cleaned B3 `Ran 3` `OK` (`G2ref_clean.log`);
  với ĐỘT BIẾN D2 của reviewer `VSLT_GUARD_CLEAN10K=_work/_rev13_tmp/m2_10k.jsonl` → test mới **FAIL** `AssertionError: 4 != 3 : ('train',
  [..., 'PAR_10K_MUT01', ...])`, còn test cũ `test_vit5_stage1_clean10k_no_heldout_match` vẫn ok (đúng như reviewer báo) (`G2ref_D2.log`).

## Đang làm
- Lượt 4: sửa E1–E3 / G2 / mục 5 theo review giữa; dừng trước B5.

## Còn lại
- B5–B14 (lượt sau). Ghi chú cho B5: `retrain_preregister.py` phải ghi đúng các khóa mà `eval_sentsplit.py` đọc (mục B4d); `protocol_template()` là nguồn
  của `evaluation_protocol`; số Clean10k sau loại (6423/713, loại 4) và CSLR/ViT5 (2880/30, 240/30) phải được TÍNH LẠI bằng code ở B5 (B3/B4c chỉ là số
  kiểm tra trước); file Tier 1 văn bản so `lf_sha256` (B3).

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
| B2a (0a18183) | `detect-changes --scope staged` (4 file mới; rồi + progress) | "Changes: 4 files, 86 symbols / Affected processes: 241 / Risk level: critical" (`dc_B2a.txt`); + progress: "Changes: 5 files, 86 symbols / Risk level: critical" (`dc_B2a_full.txt`). Chỉ file `A`, 0 `M`; luồng qua `main` của script mới (nối nhầm `main`); 0 caller có sẵn |
| B2b (WIP 9146f6f) | `detect-changes --scope staged` (3 file M) | "Changes: 3 files, 36 symbols / Affected processes: 4 / Risk level: medium" — `__init__ → _id_list | Split_file_sha256 | Ids | Signers` (`dc_B2b.txt`) |
| B2c (WIP 059a780) | `detect-changes --scope staged` (2 file M) | "Changes: 2 files, 13 symbols / Affected processes: 6 / Risk level: high" — luồng `Main → _id_list | Split_file_sha256 | Ids | Signers | From_canonical_dataset | Collect_glosses` (đều là `main` của chính script vocab gọi hàm dùng chung); grep: không caller ngoài script + test (`dc_B2c_wip.txt`) |
| B2b+B2c (progress) | `detect-changes --scope staged` | "Changes: 1 files, 1 symbols / Risk level: critical" — `Section Kế hoạch 13 — tiến độ (coder) → docs/plans/13-progress.md` (markdown; nối nhầm như B0/B2) (`dc_B2c.txt`) |
| B3 (progress) | `detect-changes --scope staged` (chỉ `M docs/plans/13-progress.md`) | "Changes: 1 files, 1 symbols / Affected processes: 226 / Risk level: critical" — symbol duy nhất `Section Kế hoạch 13 — tiến độ (coder)` (markdown; nối nhầm như B0/B2) (`dc_B3.txt`) |
| B4a | `detect-changes --scope staged` (`train.py`, `tests/test_retrain_tools.py`; rồi + progress) | "Changes: 2 files, 1 symbols / Affected processes: 226 / Risk level: critical" — symbol `Function parse_args → train.py`; luồng liệt kê (`Run_harmonized → …`, `Main → …`) là nối nhầm tên `parse_args` (grep: 0 caller mã của `train.py`) (`dc_B4a.txt`); + progress: "Changes: 3 files, 1 symbols / Risk level: critical" (`dc_B4a_full.txt`) |
| B4b | `detect-changes --scope staged` (`A scripts/archive_retrain_kaggle.py`, `M tests/test_retrain_tools.py`), sau `analyze --index-only` | "Diff touched 2 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_B4b.txt`) — index chưa có symbol của file mới / phần test thêm ⇒ KHÔNG phải kết quả sạch; đối chiếu: `git diff --cached --name-status` → `A` + `M` (test chỉ thêm dòng, 0 dòng xóa); file mới chỉ import `archive_step4_kaggle`/`archive_private_kaggle` (không sửa); `git grep archive_retrain_kaggle -- src backend scripts kaggle` → chỉ chính file ⇒ không caller có sẵn. Sau commit: `detect-changes --scope compare` (ghi ở dòng kế) |
| B4b (sau commit 7ecaa25) | `analyze --index-only` rồi `detect-changes --scope compare --base-ref HEAD~1` | "Changes: 6 files, 79 symbols / Affected processes: 202 / Risk level: critical" — symbol đổi = các hằng/hàm của `scripts/archive_retrain_kaggle.py` (mới) + `Section … 13-progress`; luồng liệt kê (`Run_harmonized → …`, `Main → …`) là nối nhầm qua mục markdown/`main` như B0/B2; "6 files" gồm cả thay đổi chưa commit của cây làm việc (3 ` D` người dùng) (`dc_B4b_compare.txt`) |
| B4c | `detect-changes --scope staged` (5 file M, sau `analyze --index-only`) | "Changes: 5 files, 25 symbols / Affected processes: 16 / Risk level: critical" — symbol: hàm/hằng mới + `train_stage1`, `train_stage2`, `run_smoke_test`, `train_cslr`…; luồng: `Train_stage1 → _words | _normalizers | L2_text | Heldout_ids | _id_list | Split_file_sha256`, `Cslr_leak_check → Ids`, `Train_stage2 → Signers | _id_list`, `Run_smoke_test → Levenshtein_distance` … — đều trong chính 3 script train gọi mô-đun split dùng chung; không luồng serving/backend; hành vi mặc định khóa bằng 3 test xanh trên cả mã cũ và mới (`dc_B4c.txt`) |
| B4d | `detect-changes --scope staged` (`A scripts/eval_sentsplit.py`, `M tests/test_retrain_tools.py`), sau `analyze --index-only` | "Diff touched 2 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_B4d.txt`) — như B4b: index chưa có symbol của file mới ⇒ KHÔNG phải kết quả sạch; đối chiếu: test chỉ thêm dòng (0 dòng xóa), file mới không được mã nào import (`git grep eval_sentsplit -- src backend kaggle` → 2 dòng, đều là chuỗi/chú thích trong `src/training/train_cslr.py:82,731` — dòng `TEST DEFERRED`, không import). Sau commit: `detect-changes --scope compare` (dòng kế) |
| B4d (sau commit f7aacc1) | `analyze --index-only` rồi `detect-changes --scope compare --base-ref HEAD~1` | "Changes: 6 files, 44 symbols / Affected processes: 213 / Risk level: critical" — symbol đổi = hàm/hằng của `scripts/eval_sentsplit.py` (mới) + `Section … 13-progress`; luồng liệt kê là nối nhầm qua mục markdown/`main` như B0/B2/B4b; "6 files" gồm thay đổi chưa commit của cây (3 ` D` người dùng) (`dc_B4d_compare.txt`) |
| Sửa-review G2 | `detect-changes --scope staged` (`M tests/test_sentence_split_guard.py`, chỉ thêm dòng), sau `analyze --index-only` | "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_G2.txt`) — index chưa có symbol của lớp test mới ⇒ KHÔNG phải kết quả sạch; đối chiếu: `git diff --cached --numstat` → `98 0` (0 dòng xóa), file test không được mã nào import |
