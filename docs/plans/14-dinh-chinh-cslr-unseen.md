# Kế hoạch 14 — Đính chính khẳng định CSLR "unseen / zero leakage" + guard

**TRẠNG THÁI: XONG (planner, 2026-10-03).** Không CẦN NGƯỜI DÙNG để bắt đầu; điểm dừng có điều kiện ở §7.
CẦN PLANNER việc khác (không chặn phần A, chặn 13 B12): §2.3.

> Planner, 2026-10-03, HEAD 714d9c9, nhánh feat/vslt-complete.
> Nguồn yêu cầu: `docs/STATE.md:276-281` (quyết định người dùng 2026-10-03 02:40 — không hỏi lại).
> Tệp tạm: `_work/_plan14_tmp/`. Tiến độ coder: `docs/plans/14-progress.md` (coder tạo ở B0).
> Phần A (B0–B6) làm ngay, không phụ thuộc K2. Phần B (B7–B8) chỉ sau khi kế hoạch 13 B11b commit `test_eval.json`.

## 1. Mục tiêu & DoD

**Mục tiêu.** (A) Gỡ mọi khẳng định "CSLR/Mode B đo trên câu chưa thấy / zero leakage" sai: README + EVALUATION + tài liệu sống sửa trực tiếp;
báo cáo lịch sử (`reports/**/*.md`, `docs/audit/**`) thêm khối ĐÍNH CHÍNH ở đầu, không xóa nội dung cũ; số "300/300 câu đã thấy ở train" sinh
từ một JSON mới có lệnh + commit; thêm test guard: khẳng định "chưa thấy/unseen/zero leakage" cho CSLR chỉ được phép khi dòng đó trỏ tới JSON
chứng minh split theo câu. (B) Điền WER/BLEU trên câu CSLR chưa học từ `reports/retrain_2026-10-02/eval/test_eval.json` qua cùng cơ chế sinh từ JSON.

**DoD phục vụ:** DoD 9 (`docs/prompts/autopilot.md:27-28`: README + EVALUATION sinh số liệu tự động từ JSON; Giới hạn trung thực — rò rỉ, số liệu
nào KHÔNG được dùng). Phụ: DoD 7 (thêm test guard chống tái phạm), DoD 10.

## 2. Hiện trạng

### 2.1 Sự thật về split CSLR cũ — chưa có JSON nào chứng minh "300/300"
- Mã: CSLR cũ chia theo NGƯỜI KÝ bằng trường `split` của `dataset_canonical.json`: train S01–S04 (cả 300 câu), val S05, test S06
  (`docs/plans/13-train-lai-checkpoint-thieu.md:375-378`; đường mã `VSLGHContinuousDataset._filter_samples` `src/data/vsl_gh_dataset.py:419-440`, dùng khi
  `sentence_split=None` `:400-405`). Tài liệu: `docs/vsl_gh_dataset.md:121-125` (train 3.600 mẫu = 4 người × 3 lần × 300 câu).
- Phát hiện gốc: `docs/cloud_reports/viec-A-D-2026-09-29.md:45-48`; review `docs/reviews/cloud-2026-09-29-review.md:110,162`.
- ViT5 stage 2 cũ: train SENT001–240, val SENT241–270, SENT271–300 không dùng (`src/translation/dataset.py:92-101`; 13 §2.2 `:394-395`).
  ⇒ "30 câu SENT271–300" chỉ là câu ViT5 stage 2 chưa học; CSLR cũ ĐÃ học chúng qua S01–S04 ⇒ Mode B (CSLR → ViT5) và WER CSLR không đo trên câu chưa thấy.
- Số cũ: `reports/audit_round2/v2_cslr_reliability.json` (KHÔNG có `generated_by`; script `reports/audit_round2/run_v2_cslr_bootstrap.py`, định nghĩa 30 câu
  `:29-30`): `sample_counts` `:2-8` (khóa `seen_sentences_in_train_count: 270` là số ViT5 stage 2 train+val, KHÔNG phải CSLR); Mode A 27.98 [17.6, 38.39]
  `:10-16`; Mode B 23.18 [13.62, 33.7] `:17-23`; Δ 4.8 [1.29, 9.14] `:24-31`; **WER 32.8 [29.48, 36.62] trên 300 clip S06** (`cslr_wer_bootstrap_300`
  `:33-39`) — README:60 đặt số này dưới tiêu đề "30 câu unseen" (gắn nhãn sai thứ hai).
- Không JSON nào có `generated_by` + commit chứng minh "câu S06 đều có trong train CSLR cũ": `reports/unified_run_2026-09-25/REPORT.md:19` nói tương tự
  nhưng cho model từ rời (`scripts/report_unified.py:116-120`), chỉ trong md; `reports/cslr_test_results.json`, `cslr_dry_run_results.json`,
  `cslr_training_history.json` không có số mẫu/câu train. ⇒ Phải SINH JSON mới (B1).
- Split câu MỚI (13): `reports/retrain_2026-10-02/preregistration.json` — `generated_by` `:3-12` (commit 2cb02b3, `code_dirty` false); `sentence_split`
  `:20-95` (sha256 `289b2ac1…`, test SENT271–300 `:27-58`); `leak_check.cslr` `:404-417` (`train_in_test: []`, `n_violations: 0`); `leak_check.total: 0`
  `:452`; ViT5 stage 1 `n_matching_test_sentences: 0` `:362`. Đây là JSON DUY NHẤT hiện có chứng minh split theo câu.
- Dữ liệu cục bộ `data/external/vsl_gh/dataset_canonical.json` (khôi phục kế hoạch 12; lf_sha256 đăng ký `d53ab701…`, preregistration `:97-101`). Giới hạn:
  bản khôi phục có 0 trường `annotation_source` (STATE:110-111; `tests.data.test_vsl_gh_dataset` test_19 FAIL có sẵn) ⇒ có thể khác file đã train CSLR cũ;
  đối chiếu chéo được bằng `reports/cslr_s06_predictions.json` (đầu ra model cũ, 300 bản ghi có `sentence_id`).

### 2.2 Kiểm kê toàn repo
Planner grep tay `unseen|zero.?leakage|leak-free|không rò rỉ|chưa (từng )?thấy|chưa từng|held.?out|30 câu|SENT27x` trên README, EVALUATION*.md, docs/,
reports/**/*.md, frontend/src/**, scripts/, src/, backend/, tests/ (68 file có từ khóa). Đây là DỰ KIẾN; danh sách chính thức = đầu ra detector §3.4 ở B3.

**(a) PHẢI SỬA — tài liệu sống, sửa TRỰC TIẾP (5 file):**

| File:dòng | Nội dung hiện tại (rút gọn) | Vì sao sai | Cách sửa |
|---|---|---|---|
| `README.md:56` | "Cấp 3 (Dịch câu liên tục S06 - 30 câu unseen)" | CSLR/Mode B đã học 30 câu này | thay khối `:56-60` bằng khối sinh `readme_cap3` (§3.3) |
| `README.md:57-59` | Mode A/B/Δ dưới tiêu đề trên | nhãn tập sai cho Mode B | trong khối sinh, nhãn đúng |
| `README.md:60` | "CSLR WER = 32.80% [..]" dưới "30 câu" | WER đo trên 300 clip | trong khối sinh: "300 clip S06, câu đã thấy ở train" |
| `EVALUATION.md:346` | "30 câu hoàn toàn chưa từng học … Zero Leakage cả về Signer lẫn Sentence" | sai cho CSLR/Mode B | thay bằng khối sinh `evaluation_12` |
| `EVALUATION.md:348` | tiêu đề "Tập Unseen Sentences S06 (30 mẫu)" | bảng có Mode B | sửa chữ tiêu đề |
| `EVALUATION.md:384-385, 389` | "270 câu seen … 30 câu unseen"; "CI trên 30 câu unseen"; WER không nhãn | CSLR đã thấy cả 300; WER trên 300 clip | thay `:384-389` bằng khối sinh `evaluation_13_2` |
| `EVALUATION.md:390` | "… chỉ sử dụng tập 30 câu unseen" | áp cho CSLR là sai | sửa chữ: chỉ đúng cho ViT5 stage 2 |
| `EVALUATION.md:408` | streaming CSLR "trên 30 câu unseen S06" | CSLR đã học | sửa chữ |
| `docs/cslr_streaming_design.md:7, 23, 117` | "30 câu unseen", "hoàn toàn chưa từng thấy (Unseen Sentences …)" | CSLR đã học | sửa chữ |
| `scripts/evaluate_translation_phase4b.py:12` | docstring "Held-Out Unseen Sentences … 100% leak-free" | Mode B có CSLR đã học | sửa docstring |
| `scripts/simulate_cslr_streaming.py:3, 89` | docstring/chú thích "unseen sentences of S06" | CSLR đã học | sửa docstring + chú thích; KHÔNG đổi tên biến, KHÔNG đổi chuỗi `print` |

**(b) PHẢI SỬA — báo cáo lịch sử: khối ĐÍNH CHÍNH ở đầu, KHÔNG xóa/sửa dòng cũ (6 file có khối + 1 file chỉ ghi sổ):**

| File | Dòng khẳng định (dự kiến) | Ghi chú |
|---|---|---|
| `reports/PHASE4B_REPORT.md` | `:97, :112, :114, :142, :148, :168` | yêu cầu nguyên văn của người dùng; khối ngay sau tiêu đề `:1` |
| `reports/audit_round2/VERIFY.md` | `:14, :42` | khối nêu thêm `:43` ("270 câu đã xuất hiện trong tập train S01-S04" — sai cho CSLR; detector không bắt vì không có từ khẳng định) |
| `reports/audit_round2/AUDIT_ROUND2.md` | `:34, :35, :96` | khối nêu thêm `:100` (WER 300 clip dưới tiêu đề 30 câu) |
| `reports/audit_round3/PROVENANCE.md` | `:48` | "chỉ 30 câu unseen là thước đo hợp lệ" — đúng cho ViT5, sai cho CSLR |
| `reports/audit_20260924/AUDIT_REPORT.md` | `:19, :39, :54, :96` | `:19,54,96` nói ViT5 Mode A (đúng cho ViT5 stage 2) nhưng neo S06 — khối làm rõ; `:39` vốn đúng ("chỉ held-out signer, không held-out sentence") |
| `docs/audit/PHASE4_AUDIT.md` | `:180` | "300 câu do S06 … chưa từng xuất hiện trong tập train" — đúng cho clip/người ký, sai cho câu |
| `reports/unified_run_2026-09-25/REPORT.md` | `:19` | câu ĐÚNG (phủ định "not unseen sentences") nhưng detector bắt ⇒ chỉ ghi sổ `block: None` + lý do, KHÔNG sửa file |

**(c) KHÔNG SỬA — lý do:**
- Cấp 2 / Tier 1 (phương ngữ, clip — không phải CSLR): `README.md:18, :30, :135`; `EVALUATION.md:88-92, :160, :170-176, :247`;
  `docs/final_report_outline.md:15,33,36,47,64`; `docs/audit/final_status.md:13,16,24,29,47`; `docs/audit/final_health_check.md:46`; `docs/phase5_baseline.md:185`,
  `docs/phase6_stgcn.md:235,283`, `docs/phase7_transformer.md:21,134,168`, `docs/phase8_ensemble.md:22,55`, `docs/phase2_preprocessing_dataloader.md:12`;
  `frontend/src/components/Reports.jsx:76` ("8.07% Top-1 trên clip chưa thấy" — Cấp 2 clip sạch, nguồn `PROVENANCE.md`).
  **Ghi nhận cho orchestrator (backlog, ngoài phạm vi 14):** "Zero-Leakage" ở `README.md:18`, `docs/audit/final_status.md:13,24` mâu thuẫn với
  `reports/audit_round3/PROVENANCE.md:74` (mọi họ split cũ, kể cả tier1 và 3 fold cross-dialect, bị guard bản quay trùng chặn) và `README.md:55`
  (cross-dialect INVALID) ⇒ cần một kế hoạch đính chính Cấp 2 riêng.
- Đúng (người ký / bản quay): `docs/vsl_gh_dataset.md:123-124` ("unseen signer"); `reports/step4_2026-09-26/REPORT.md` ("S06 (người ký chưa thấy)",
  "QIPEDC TEST (clip chưa thấy)"); `reports/unified_run_2026-09-25/REPORT.md:8-9,23`; `reports/source_diagnostics_2026-09-26/REPORT.md:76`;
  `docs/audit/PHASE4_AUDIT.md:169` ("S06 Held-Out Signer"); `reports/alphabet_*`, `docs/alphabet_collection_protocol*.md`, `docs/data_collection_protocol.md` (Cấp 1).
- ViT5 Mode A không neo CSLR/S06: `reports/audit_20260924/AUDIT_REPORT.md:97`.
- JSON lịch sử (không sửa báo cáo cũ; khối md giải thích): khóa `bleu_bootstrap_30_unseen`, `seen_sentences_in_train_count` (`v2_cslr_reliability.json`),
  `held_out_unseen_sentences_30` (`reports/translation_phase4b_benchmark.json`), `reports/step4_2026-09-26/step4_results.json`, `reports/unified_run_2026-09-25/REPORT.json`.
- Mã, không phải khẳng định: tên biến/chuỗi in `unseen_*` (`scripts/simulate_cslr_streaming.py:93-152`; `scripts/evaluate_translation_phase4b.py:84-93` —
  tên khóa đầu ra, đổi sẽ đổi định dạng JSON); `src/data/vsl_dataset.py:192-198` (lớp chưa thấy); `scripts/report_*.py`, `build_unified_manifest.py:10`,
  `train_unified.py:9`, `cross_source_dtw.py:9`, `compare_isolated_models.py:6`, `train_alphabet_real.py:9-12` (người ký/bản quay — đúng);
  `scripts/record_vsl_alphabet.py:983,1085` (Cấp 1 tổng hợp — ngoài phạm vi).
- File của kế hoạch 13 (KHÔNG đụng): `scripts/eval_sentsplit.py` (đã ghi đúng `:464-471`), `tests/test_retrain_tools.py:1227-1246`, `reports/retrain_2026-10-02/**`.
- Tài liệu quy trình (trích khẳng định để bàn về nó — loại khỏi guard): `docs/plans/**`, `docs/reviews/**`, `docs/cloud_reports/**`, `docs/prompts/**`,
  `docs/STATE.md`, `docs/progress_log.md`, `.claude/**`, `.agents/**`, `CLAUDE.md`, `AGENTS.md` ("a zero means unseen" — GitNexus).
- UI: `frontend/src/**` không có chuỗi nào về CSLR/S06/BLEU/WER/rò rỉ (grep `S06|BLEU|WER|leak|rò rỉ|held.?out|SENT27|30 câu` → 0) ⇒ KHÔNG sửa UI.

**Tổng PHẢI SỬA:** sống 5 file (README 1 khối thay 5 dòng; EVALUATION 2 khối + 3 dòng chữ; `docs/cslr_streaming_design.md` 3 dòng; 2 script 3 dòng chữ);
lịch sử 6 file thêm khối (+ 1 file chỉ ghi sổ guard).

### 2.3 Chồng lấn với kế hoạch khác (không sửa file của họ — orchestrator chuyển planner tương ứng)
- **Kế hoạch 13 §3.9 / B12** (`docs/plans/13-train-lai-checkpoint-thieu.md:621-634, :730`) định THÊM "dòng đính chính rò rỉ" sau `README.md:56`,
  `PHASE4B_REPORT.md:112`, `EVALUATION.md:387,390`, `VERIFY.md:14,46`, luật "chỉ THÊM dòng". Quyết định người dùng 02:40 (sau 13) bắt README sửa
  TRỰC TIẾP và PHASE4B khối ở ĐẦU ⇒ phần "đính chính rò rỉ" của 13 B12 do 14 A/B đảm nhận; 13 B12 chỉ còn dòng "[Kế hoạch 13 — artifact mới]" (không chứa
  từ khẳng định ⇒ không vướng guard) + `docs/cloud_training.md`; định vị theo tiêu đề mục (14 làm lệch số dòng). Nếu 13 B12 vẫn thêm câu §3.9 [LS1]
  ("… không phải chưa thấy câu …") vào file lịch sử, guard 14 ĐỎ ⇒ **CẦN PLANNER 13** sửa §3.9 trước khi coder 13 tới B12.
- **Kế hoạch 13 §0B.5 AC0(a)** chỉ chấp nhận dòng `git status` mới thuộc kế hoạch 11 ⇒ coder 14 KHÔNG để file dở/untracked ngoài `_work/` khi kết thúc mỗi
  bước. **CẦN PLANNER 13** thêm 14 vào danh sách kế hoạch song song (sửa nhỏ).
- **Kế hoạch 13 B11b** (`scripts/eval_sentsplit.py`: `code_dirty` → exit 2): coder 14 không để cây bẩn khi 13 chạy eval (orchestrator không cho hai
  coder chạy cùng lúc B11b của 13 và bước dở của 14).
- **Kế hoạch 07** (chưa code; `docs/plans/07-viec6-che-do.md:370, :409, :625`): "không sửa báo cáo lịch sử", README chỉ thêm dòng ⇒ phần đính chính đã
  thuộc 14; dòng README mới của 07 phải qua guard 14 — ghi chú cho planner 07 khi tới lượt.
- **Kế hoạch 11**: không chạm file nào của 11 (`src/data/vsl_gh_dataset.py` chỉ được IMPORT ở B1). Kế hoạch 13: chỉ IMPORT `src/data/sentence_split.py`.

## 3. Thiết kế

### 3.1 Luồng dữ liệu
```
data/external/vsl_gh/dataset_canonical.json ─┐
reports/cslr_s06_predictions.json ───────────┼─► scripts/audit_cslr_sentence_coverage.py ─► reports/cslr_claims_<D>/old_cslr_sentence_coverage.json  (B1)
configs/vslgh_sentence_split_v1.json ────────┤
reports/retrain_2026-10-02/preregistration.json
old_cslr_sentence_coverage.json ┐
v2_cslr_reliability.json ───────┼─► scripts/render_cslr_claims.py (--write | --check) ─► khối sinh giữa marker: README, EVALUATION, 6 báo cáo lịch sử
preregistration.json ───────────┤        (dùng scripts/cslr_claim_rules.py: detector + kiểm JSON bằng chứng)
test_eval.json (phần B) ────────┘
tests/test_cslr_claim_guard.py: quét repo bằng cslr_claim_rules + sổ báo cáo lịch sử + khối sinh == render(JSON) + hồi quy trên git BASE
```
Không thay đổi tiền xử lý/model/dữ liệu ML. Lọc mẫu dùng ĐÚNG mã có sẵn (không viết lại): split cũ = `VSLGHContinuousDataset(split=…)` với
`sentence_split=None` (`src/data/vsl_gh_dataset.py`); split mới = `src.data.sentence_split.load_sentence_split` + `select_vslgh_samples`. Chỉ import.

### 3.2 `scripts/audit_cslr_sentence_coverage.py` (mới, B1)
- CLI: `--canonical data/external/vsl_gh/dataset_canonical.json --keypoints-dir data/external/vsl_gh/keypoints_frontal --predictions reports/cslr_s06_predictions.json
  --sentence-split configs/vslgh_sentence_split_v1.json --prereg reports/retrain_2026-10-02/preregistration.json --out reports/cslr_claims_<D>/old_cslr_sentence_coverage.json`
  (`<D>` = ngày sinh, YYYY-MM-DD).
- Mã thoát: 0 OK; 2 = đích đã tồn tại (không ghi đè) / cây bẩn (`git status --porcelain -- src scripts configs` có dòng không bắt đầu `??`) / thiếu đầu vào;
  3 = lf_sha256 dataset ≠ `inputs.dataset_canonical_json.lf_sha256` của preregistration (in cả hai, KHÔNG ghi JSON).
- JSON (mọi số TÍNH bằng code):
  - `generated_by{script, command, git_commit, code_dirty, generated_at_utc, python}`; `inputs{<file>: {path, sha256|lf_sha256, n_records}}`.
  - `old_recipe` (mã cũ): mỗi split ∈ {train, val, test}: `n_samples`, `signers`, `n_sentences`; `n_test_sentences_seen_in_train` = |câu(test) ∩ câu(train)|;
    `test_sentences_not_in_train` (danh sách); `heldout30` = câu(test) ∩ `test_ids` của file split: `{n_sentences, n_seen_in_train,
    min_train_samples_per_sentence, max_train_samples_per_sentence}`; `code_ref` (chuỗi mô tả đường mã + `git_commit`).
  - `old_predictions_crosscheck` (`reports/cslr_s06_predictions.json`): `n_records`, `n_unique_sentence_ids`, `n_in_old_train_sentences`.
  - `new_recipe` (split câu v1): `n_train_sentences`, `n_test_sentences`, `n_test_sentences_in_train`; `prereg_leak_check_total` (chép `leak_check.total`).
  - `limitations` (chuỗi cố định): (1) dataset là bản khôi phục kế hoạch 12, có thể khác file đã train CSLR cũ (0 `annotation_source`); (2) `old_recipe` tái
    hiện quy tắc split, không đọc được danh sách mẫu thật của lần train cũ (checkpoint/log cũ đã mất); (3) `seen_sentences_in_train_count` của
    `v2_cslr_reliability.json` là số ViT5 stage 2, không phải CSLR.
- KHÔNG assert "= 300": số nào ra ghi số đó; tài liệu chỉ dùng số trong JSON.

### 3.3 `scripts/cslr_claim_rules.py` + `scripts/render_cslr_claims.py` (mới, B2)
- `cslr_claim_rules.py` (stdlib, không import torch/numpy): hằng `SIGNER_QUALIFIED`, `CLAIM`, `ANCHOR`, `PROOF_REF` (§3.4); `find_claims(text)`;
  `is_proof(path, repo_root, tracked=…) -> (bool, lý do)`; `bare_claims(text, repo_root) -> [(lineno, line)]` (dòng khẳng định không có ref bằng chứng hợp lệ).
  Dùng chung cho renderer và guard (một chỗ, không chép logic).
- Marker (HTML comment, mỗi cái một dòng): `<!-- cslr-claims:begin <block_id> | sinh bởi scripts/render_cslr_claims.py, không sửa tay -->` …
  `<!-- cslr-claims:end <block_id> -->`.
- `BLOCKS` = `block_id → (file, template, nguồn JSON)`. Phần A: `readme_cap3` (thay `README.md:56-60`), `evaluation_12` (thay `EVALUATION.md:346`),
  `evaluation_13_2` (thay `EVALUATION.md:384-389`), `historical_phase4b`, `historical_verify`, `historical_audit_round2`, `historical_provenance`,
  `historical_audit_report`, `historical_phase4_audit` (đầu file, ngay sau dòng tiêu đề H1 đầu tiên).
- `render(block_id, repo_root) -> str` thuần; `--write` chỉ thay nội dung giữa marker (đúng 1 cặp); lần chèn đầu: `--insert <block_id> --after-line <n>` /
  `--replace-lines a-b` (chỉ B4/B5, lệnh ghi vào 14-progress); `--check` exit 1 khi khác render; exit 2: thiếu JSON nguồn, marker thiếu/lặp. Định dạng số
  cố định: BLEU/WER/tỉ lệ `f"{v:.2f}"` (Δ `f"{v:+.2f}"`), đếm `str(int)`, CI `[lo, hi]` cùng định dạng. Giữ kiểu xuống dòng của file (CRLF/LF) khi ghi.
- Nội dung bắt buộc của template (coder viết chữ; PHẢI có các ý sau; PHẢI qua guard — 0 dòng trần):
  - `readme_cap3`: (1) "Cấp 3 — ĐÍNH CHÍNH 2026-10-03: S06 là người ký chưa từng thấy, nhưng {old_recipe.n_test_sentences_seen_in_train}/{test.n_sentences}
    câu của S06 đã thấy ở train CSLR cũ ({train.signers}; {train.n_samples} mẫu, {train.n_sentences} câu) — `reports/cslr_claims_<D>/old_cslr_sentence_coverage.json`";
    (2) "30 câu SENT271–SENT300: ViT5 stage 2 cũ không dùng khi train; CSLR cũ đã học {heldout30.n_seen_in_train}/{heldout30.n_sentences} câu này";
    (3) Mode A, Mode B, Δ cũ từ `v2_cslr_reliability.json` (nguyên số), Mode B kèm "lạc quan: CSLR cũ đã học các câu này";
    (4) WER cũ "{w} [{lo}, {hi}] trên {total_test_samples} clip S06 (người ký chưa từng thấy; câu đã thấy ở train)";
    (5) phần A: "CSLR trên câu chưa học (split câu kế hoạch 13, `reports/retrain_2026-10-02/preregistration.json`): CHƯA CÓ SỐ — chờ
    `reports/retrain_2026-10-02/eval/test_eval.json` (kế hoạch 13 B11b)"; phần B: số thật (§3.6).
  - `evaluation_12`, `evaluation_13_2`: cùng ý (1)–(5) theo ngữ cảnh (§12: 30 câu là câu ViT5 stage 2 chưa học; Mode B không đo trên câu CSLR chưa học).
  - `historical_*`: "> **ĐÍNH CHÍNH CSLR (2026-10-03, kế hoạch 14)** — nội dung cũ bên dưới giữ nguyên." + "Khẳng định về tập S06 / 30 câu SENT271–SENT300
    ở các dòng {danh_sách_dòng} của file này là SAI đối với CSLR và Mode B: CSLR cũ đã thấy {seen}/{total} câu của S06 ở train ({train.signers}), gồm
    {heldout30.n_seen_in_train}/{heldout30.n_sentences} câu SENT271–SENT300 — `…/old_cslr_sentence_coverage.json`; S06 chỉ là người ký chưa từng thấy." +
    link `v2_cslr_reliability.json` (số cũ đo trên tập nào; WER trên 300 clip) + "Số đúng trên câu CSLR chưa học (split câu `reports/retrain_2026-10-02/
    preregistration.json`): chờ `reports/retrain_2026-10-02/eval/test_eval.json`" (A) / số (B) + ý riêng từng file (VERIFY `:43`, AUDIT_ROUND2 `:100`,
    AUDIT_REPORT: các dòng về ViT5 Mode A chỉ đúng cho ViT5 stage 2). `{danh_sách_dòng}` = số dòng (trong file SAU khi chèn) mà `bare_claims` trả cho
    file đó — render chạy detector trên văn bản kết quả; khối độ dài cố định ⇒ tất định.
  - Template không chứa từ CLAIM trừ cụm SIGNER_QUALIFIED hoặc trên dòng có ref P1/P2 hợp lệ. Viết dạng khẳng định dương ("đã thấy ở train", "đã học"),
    không trích lại câu sai.

### 3.4 Luật guard — HỢP ĐỒNG (hằng trong `cslr_claim_rules.py`; `tests/test_cslr_claim_guard.py` chứa bản chép nguyên văn để so; đổi = planner)
**Detector** (mỗi dòng chuẩn hóa NFC, `re.IGNORECASE`, Unicode):
1. `SIGNER_QUALIFIED` (xóa khỏi dòng trước bước 2): `unseen[\s-]+signers?`, `held[\s-]*out[\s-]+signers?`, `signer[\s-]+held[\s-]*out`,
   `người\s+ký(\s+\S+)?\s+chưa\s+(từng\s+)?(thấy|gặp)`, `chưa\s+(từng\s+)?(thấy|gặp)\s+người\s+ký`.
2. `CLAIM`: `unseen|zero[\s-]*leak(age)?|leak(age)?[\s-]*free|không\s+(hề\s+)?rò\s+rỉ|chưa\s+(từng\s+)?(thấy|học|gặp|xuất\s+hiện)|hoàn\s+toàn\s+chưa|held[\s-]*out`.
3. `ANCHOR` (trên dòng gốc): `CSLR|Mode\s*B|Cấp\s*(độ\s*)?3|Level\s*3|\bS06\b|SENT2[7-9]\d|SENT300|\b30\s+(câu|sentences?|mẫu)\b|Signer\s+lẫn\s+Sentence|dịch\s+câu|\bWER\b|end[\s-]*to[\s-]*end`.
4. Dòng khẳng định = CLAIM khớp (sau bước 1) VÀ ANCHOR khớp.

**JSON bằng chứng split theo câu** — `PROOF_REF` = `(?:reports|configs)/[^\s`'"()\[\]<>]+\.json` trong CÙNG DÒNG. Ref hợp lệ khi: file được git theo dõi
(`git ls-files --error-unmatch`), JSON đọc được, `generated_by.git_commit` 40 hex, `generated_by.code_dirty is False`, VÀ một trong:
- **P1 (đăng ký trước):** `sentence_split.sha256` == sha256(bytes `configs/vslgh_sentence_split_v1.json`, CRLF→LF — luật `sentence_split.sha256_rule` của
  preregistration) VÀ `leak_check.cslr.n_violations == 0` VÀ `leak_check.cslr.train_in_test == []` VÀ `leak_check.total == 0`.
- **P2 (đánh giá, phần B):** `inputs.sentence_split_sha256` == sha trên VÀ `per_sample` có đúng `len(test_ids)` mục, mọi `sentence_id` ∈ `test_ids`
  (đọc từ `configs/vslgh_sentence_split_v1.json`).
- JSON khác (kể cả `old_cslr_sentence_coverage.json`, `v2_cslr_reliability.json`, chính file split) KHÔNG là bằng chứng.
"Dòng trần" = dòng khẳng định không có ref hợp lệ.

**Phạm vi quét** = `git ls-files --cached --others --exclude-standard`, lọc:
- SỐNG: `README.md`, `EVALUATION*.md`, `docs/**/*.md` trừ `docs/plans/`, `docs/reviews/`, `docs/cloud_reports/`, `docs/prompts/`, `docs/audit/`, `docs/STATE.md`,
  `docs/progress_log.md`; `frontend/src/**/*.{js,jsx,ts,tsx,html,css,md}`.
- LỊCH SỬ: `reports/**/*.md`, `docs/audit/**/*.md`.
- Không quét: `.py`, `.json`, `.claude/`, `.agents/`, `CLAUDE.md`, `AGENTS.md`, `_work/`, `clone/`, `data/`, `node_modules/` (lý do §2.2c). Docstring 2 script khóa bằng AC5-d.

**Luật:**
- L1 (sống): 0 dòng trần.
- L2 (lịch sử): sổ `HISTORICAL = {path: {"claim_lines": n, "block": "<block_id>" | None, "reason": str}}` và `HISTORICAL_CEILING = {path: n}` (đóng băng ở B3,
  = số đo tại 714d9c9). Mọi file lịch sử có ≥ 1 dòng trần phải có trong sổ; số dòng trần == `claim_lines`; khóa sổ ⊆ khóa trần, `claim_lines ≤ trần`.
  `block` ≠ None ⇒ marker begin nằm trong 15 dòng đầu và nội dung == render. `block` None chỉ khi `reason` khác rỗng (dự kiến chỉ unified_run REPORT.md:19).
- L3 (khối sinh): mọi `block_id` của `BLOCKS`: file có đúng 1 cặp marker, nội dung == `render(block_id)`.
- L4 (bằng chứng guard bắt khẳng định gốc, chạy mãi mãi): `BASE = "714d9c9"`; `bare_claims(git show BASE:README.md)` chứa dòng 56;
  `git show BASE:EVALUATION.md` chứa dòng 346; `git show BASE:reports/PHASE4B_REPORT.md` vi phạm L2 (có dòng trần, không khối). Thiếu object git → FAIL
  (không skip) với thông báo "cần git fetch --unshallow".

### 3.5 Sửa trực tiếp (B4) — luật chữ
- Dòng sửa ngoài khối sinh KHÔNG thêm số mới (AC5-c). Số mới chỉ qua khối sinh. Không xóa thông tin: chỉ đổi nhãn tập đo / bỏ khẳng định sai; số cũ giữ
  giá trị + nguồn.

### 3.6 Phần B (B7, sau 13 B11b)
- Điều kiện vào: `reports/retrain_2026-10-02/eval/test_eval.json` đã commit bởi commit `^(WIP )?13:`, `generated_by.code_dirty == false`, 13-progress ghi
  `--recompute-from` khớp. Chưa có → phần B chờ; khối hiển thị dòng "CHƯA CÓ SỐ" của phần A (không lỗi).
- Coder đọc schema THẬT (`metrics`, `per_sample`, `inputs.sentence_split_sha256`, `limitations`, `comparison_to_old`), thêm nguồn thứ 4 vào `BLOCKS`. Khóa cần
  mà thiếu (WER + S/D/I + CI; BLEU A, B, Δ + CI; số mẫu) hoặc file không thỏa P2 → DỪNG, CẦN PLANNER (không suy diễn, không tính lại ngoài JSON).
- Nội dung thêm vào `readme_cap3`, `evaluation_12`, `evaluation_13_2`, mọi `historical_*`: WER (S, D, I) + CI, BLEU Mode A / Mode B / Δ + CI trên {n} câu
  SENT271–SENT300 mà CSLR + ViT5 mới không học — MỌI dòng có số này chứa đường dẫn `test_eval.json`; giới hạn chép từ `test_eval.json.limitations`
  (30 câu không ngẫu nhiên, 1 người ký, backbone K1, amendment smoke) + câu "không so trực tiếp với số cũ" (lý do 13 §0.2).

## 4. Chia việc (mỗi bước 1 commit `14: Bx …`; ghi 14-progress; detect-changes trước MỖI commit; impact trước khi sửa symbol có sẵn)

| Bước | Việc | Ước lượng | Phụ thuộc |
|---|---|---|---|
| **B0** | Mốc, chỉ đọc: `git status --porcelain` → `_work/_plan14_tmp/B0_status.txt`; 12 file đích (§2.2 a+b) KHÔNG có thay đổi chưa commit (có → DỪNG §7); `git cat-file -e 714d9c9`; lf_sha256 dataset == preregistration (khác → DỪNG §7); chạy bộ hồi quy 31 module (lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1028`) → `B0_regress.log` + đếm theo module + `B0_nonok.txt`; grep §2.2 lại → `B0_grep.txt`. Tạo `docs/plans/14-progress.md`. | 0,25 h + thời gian bộ test | — |
| **B1a** | `scripts/audit_cslr_sentence_coverage.py` + `tests/test_cslr_sentence_coverage.py` (đỏ trước: chạy test khi chưa có script, lưu log). Dữ liệu giả trong thư mục tạm (canonical nhỏ, thư mục keypoints rỗng, predictions, split, prereg giả). | 1 h | B0 |
| **B1b** | Trên cây sạch chạy lệnh §3.2 → `reports/cslr_claims_<D>/old_cslr_sentence_coverage.json` + `.log`; commit. Chép số chính vào 14-progress kèm đường dẫn:khóa. Exit 3 → DỪNG §7. | 0,25 h | B1a |
| **B2** | `scripts/cslr_claim_rules.py` + `scripts/render_cslr_claims.py` + `tests/test_render_cslr_claims.py` (đỏ trước). Chưa chèn khối vào tài liệu. | 2 h | B1b |
| **B3** | `tests/test_cslr_claim_guard.py`: AC3 (tổng hợp), L1–L4 trên repo; `HISTORICAL`/`HISTORICAL_CEILING` điền từ `bare_claims` tại HEAD (trước khi chèn khối) và đối chiếu §2.2(b) — file sống/lịch sử NGOÀI §2.2 → DỪNG §7. Chạy: AC3 + L4 xanh; L1, L2, L3 ĐỎ CÓ CHỦ ĐÍCH (lưu log, tên test đỏ, dòng vi phạm vào 14-progress). Module này ngoài mọi bộ hồi quy của 11/13. | 1,5 h | B2 |
| **B4** | Tài liệu sống: chèn `readme_cap3`, `evaluation_12`, `evaluation_13_2` bằng renderer; sửa chữ `EVALUATION.md:348,390,408`, `docs/cslr_streaming_design.md:7,23,117`, docstring `evaluate_translation_phase4b.py:12`, `simulate_cslr_streaming.py:3` + chú thích `:89` (impact upstream cho hàm chứa `:89`, ghi kết quả). L1 + L3 phần sống xanh; L2 còn đỏ. | 1,5 h | B3 |
| **B5** | Chèn 6 khối `historical_*` (sau H1). Chỉ thêm dòng. Guard xanh toàn bộ. | 1 h | B4 |
| **B6** | Đóng A: AC7 hồi quy, AC8 đột biến M1–M8, AC0, 14-progress (bảng AC), 1 dòng `docs/progress_log.md`. Báo orchestrator: gọi reviewer phần A. | 0,75 h + bộ test | B5 |
| **B7** | Phần B (§3.6): ánh xạ schema `test_eval.json`, test đỏ trước bằng JSON tổng hợp đúng schema thật, render lại mọi khối, guard xanh; đột biến M9. | 1,5 h | 13 B11b + B6 |
| **B8** | Đóng B: AC hồi quy + B-AC, 14-progress, 1 dòng progress_log; báo orchestrator gọi reviewer phần B. | 0,5 h | B7 |

Tổng: A = 8 bước ~8,25 h công (+ 2 lần bộ hồi quy, mỗi lần ~4–19 phút theo 13-progress); B = 2 bước ~2 h. Bị ngắt giữa bước: đọc 14-progress (bước cuối đã
commit), `git status` thấy file dở → làm lại bước dở từ đầu.

## 5. Tiêu chí chấp nhận (hợp đồng — coder không đổi; chỉ planner đổi, ghi lý do)
`$PY` = `.venv/Scripts/python` (Windows). Mọi log vào `_work/_plan14_tmp/`, tóm tắt vào 14-progress.

**AC0 — Phạm vi.** Tập commit 14: `git log --format='%H %s' 714d9c9..HEAD | grep -E '^[0-9a-f]{40} (WIP )?14:'`; hợp các
`git diff-tree --no-commit-id --name-status -r <c>` ⊆ {`docs/plans/14-progress.md`, `docs/progress_log.md`, `scripts/audit_cslr_sentence_coverage.py`,
`scripts/cslr_claim_rules.py`, `scripts/render_cslr_claims.py`, `tests/test_cslr_sentence_coverage.py`, `tests/test_render_cslr_claims.py`,
`tests/test_cslr_claim_guard.py`, `reports/cslr_claims_<D>/*`, `README.md`, `EVALUATION.md`, `docs/cslr_streaming_design.md`,
`scripts/evaluate_translation_phase4b.py`, `scripts/simulate_cslr_streaming.py`, 6 file lịch sử §2.2(b) có khối}. 0 file của 11/13 (danh sách trong prompt
orchestrator / §2.3). `git status --porcelain` cuối mỗi bước == `B0_status.txt` (bỏ qua `_work/`).

**AC1 — JSON phủ câu.** `$PY -m unittest tests.test_cslr_sentence_coverage -v` → OK, 0 skip; log đỏ B1a có trong 14-progress. JSON tracked;
`generated_by.git_commit` là tổ tiên HEAD và chứa script; `code_dirty` false. Chạy lại lệnh §3.2 với `--out _work/_plan14_tmp/recheck.json` → giống hệt
JSON đã commit trừ `generated_at_utc`, `command`, `git_commit` (so bằng script nhỏ, in "0 khác").

**AC2 — README.** Khối `readme_cap3` thay đúng `714d9c9:README.md:56-60` (hunk duy nhất của `git diff 714d9c9 HEAD -- README.md` bắt đầu ở dòng 56, chỉ trong
vùng đó); khối chứa chuỗi `"{seen}/{total}"` và `"{h_seen}/{h_total}"` đúng bằng giá trị JSON; `grep -n -i -E "unseen|zero.?leakage" README.md` chỉ ra 2 dòng
Cấp 2 có nội dung giống hệt `714d9c9:README.md:18` và `:30`.

**AC3 — Hợp đồng detector (văn bản tổng hợp, luôn chạy, trong `tests/test_cslr_claim_guard.py`).** Hằng regex == bản chép §3.4 (so chuỗi). Các ca:
(a) "Mode B BLEU trên 30 câu unseen" → trần; (b) "CSLR WER trên câu chưa từng học (S06)" → trần; (c) "Zero Leakage cả về Signer lẫn Sentence" → trần;
(d) "S06 là người ký chưa từng thấy" → không là khẳng định; (e) "VSL-GH words, unseen signer S06" → không; (f) "Tier 2: 8.07% Top-1 trên clip chưa thấy"
→ không (không neo); (g) (a) + `reports/retrain_2026-10-02/preregistration.json` (file thật) → hợp lệ; (h) (a) + `reports/audit_round2/v2_cslr_reliability.json` →
trần; (i) (a) + đường dẫn `old_cslr_sentence_coverage.json` thật → trần; (j) JSON P1 tổng hợp hợp lệ → hợp lệ; cùng JSON với `code_dirty: true` / sha split lệch /
`leak_check.cslr.n_violations: 1` / không tracked (tham số `tracked`) → trần (4 ca); (k) JSON P2 tổng hợp đủ 30 id đúng → hợp lệ; 29 mục / 1 id lạ → trần;
(l) file lịch sử tổng hợp: ngoài sổ → vi phạm; trần +1 → vi phạm; thiếu khối → vi phạm; khối lệch render → vi phạm; `block None` + `reason` rỗng → vi phạm;
(m) sha CRLF→LF của test == `preregistration.json` `sentence_split.sha256`.

**AC4 — Guard trên repo.** `$PY -m unittest tests.test_cslr_claim_guard tests.test_render_cslr_claims -v` → OK, 0 skip ở B5 và B6. Ở B3: log đỏ chứa test L1,
L2, L3 FAIL và liệt kê ít nhất `README.md:56`, `EVALUATION.md:346`, `docs/cslr_streaming_design.md:23`, `reports/PHASE4B_REPORT.md` (thiếu khối); L4 + AC3 xanh.
`HISTORICAL_CEILING` không đổi sau commit B3 (`git log -p` của file test sau B3: 0 dòng `+`/`-` trong khối hằng này).
`$PY scripts/render_cslr_claims.py --check` → exit 0.

**AC5 — Tài liệu sống.** (a) Mỗi dòng §2.2(a) đã sửa: `$PY -c` gọi `bare_claims` cho 3 file md → []; (b) `--check` exit 0; (c) không số mới ngoài khối: script
`_work/_plan14_tmp/numcheck.py` duyệt `git diff 714d9c9 HEAD -- README.md EVALUATION.md docs/cslr_streaming_design.md scripts/evaluate_translation_phase4b.py
scripts/simulate_cslr_streaming.py`, bỏ dòng trong marker; mọi dãy chữ số trên dòng `+` phải có trên dòng `-` cùng hunk → in "0 vi phạm" (script + output vào
14-progress); (d) `git diff 714d9c9 HEAD -- scripts/evaluate_translation_phase4b.py scripts/simulate_cslr_streaming.py` chỉ chạm docstring/chú thích (`:12`; `:3`, `:89`),
`grep -n -i "leak-free" scripts/evaluate_translation_phase4b.py` → 0; `$PY -m py_compile` 2 file OK.

**AC6 — Báo cáo lịch sử.** Với 6 file có khối: `git diff 714d9c9 HEAD -- <file> | grep -c '^-[^-]'` == 0; marker begin ở dòng ≤ 15; `{danh_sách_dòng}` trong khối
== `bare_claims` (guard L3 kiểm). `git diff 714d9c9 HEAD -- reports/unified_run_2026-09-25/REPORT.md` rỗng.

**AC7 — Hồi quy = mốc.** Lệnh B0 (31 module) + `tests.test_cslr_sentence_coverage tests.test_render_cslr_claims tests.test_cslr_claim_guard`. 31 module cũ:
đếm ok/FAIL/ERROR/skip theo module giống hệt B0; tập id không-ok ⊆ `B0_nonok.txt`; test chập chờn có sẵn `test_reset_segments_and_graphs` theo đúng luật
`docs/plans/11-sua-vi-pham-guard-dod7.md` AC7 (chạy riêng 3 lần, phải OK cả 3). Nếu `checkpoints/` khác lúc B0 (13 B11 đặt checkpoint): test trước ERROR/skip
nay phải ok, FAIL → DỪNG báo. 3 module mới: ok, 0 skip. Không file frontend nào đổi (AC0) ⇒ không bắt buộc `npm test`.

**AC8 — Đột biến (mỗi cái trên cây sạch, hoàn tác bằng `git checkout -- <file>` hoặc xóa file tạm; ghi lệnh + test FAIL vào 14-progress; sau cùng `git status`
== trước).** M1 README: thêm " (30 câu unseen)" vào dòng Mode B trong khối → L1 + L3 FAIL. M2 README: thêm dòng ngoài khối "> CSLR đạt WER thấp trên 30 câu
chưa từng thấy." → L1 FAIL. M3 EVALUATION: đặt lại dòng 346 gốc (thay khối) → L1 + L3 FAIL. M4 PHASE4B: xóa khối → L2 FAIL. M5 VERIFY.md: thêm dòng
"- CSLR: 30 câu unseen S06" → L2 FAIL (đếm). M6 `frontend/src/components/Reports.jsx`: thêm chữ "CSLR … 30 câu chưa thấy" trong JSX → L1 FAIL.
M7 file mới chưa track `docs/_m7.md` có "Mode B trên 30 câu unseen" → L1 FAIL. M8 sửa tạm một số trong `old_cslr_sentence_coverage.json` → L3 FAIL.

**AC9 — Quy trình.** Mỗi bước 1 commit `14: Bx …`; detect-changes trước mỗi commit (log); impact cho symbol có sẵn bị chạm (B4 `:89`) ghi kết quả + risk;
HIGH/CRITICAL → ghi lý do, reviewer xét. Không `git add -A`; không đụng 3 dòng ` D` của người dùng.

**AC10 — Ghi sổ.** 1 dòng `docs/progress_log.md` ở B6 (và B8): ngày | việc | commit | test | reviewer | việc tiếp theo.

**Phần B (B7–B8):**
- **ACB1** `test_eval.json` thật thỏa P2 (test mới trong guard, thêm ở B7 — không skip); thiếu khóa → DỪNG (không tạo test để pass).
- **ACB2** `--check` exit 0; mọi dòng chứa số mới có đường dẫn `test_eval.json`; số == JSON theo định dạng §3.3; guard OK 0 skip.
- **ACB3** AC5-c lặp lại (không số mới ngoài khối); AC6 lặp lại (file lịch sử chỉ thêm dòng); AC7 lặp lại.
- **ACB4** Đột biến M9: sửa một chữ số WER trong khối README → L3 FAIL; JSON P2 tổng hợp `code_dirty: true` → không là bằng chứng (ca AC3 mới).

## 6. Rủi ro dữ liệu/ML
- **R1 Nguồn gốc dữ liệu.** `dataset_canonical.json` là bản khôi phục (kế hoạch 12), có thể khác file đã train CSLR cũ (0 `annotation_source`). Số "câu S06 đã thấy ở
  train" là của QUY TẮC split áp lên bản khôi phục; checkpoint/log train cũ đã mất nên không đọc được danh sách mẫu thật. Giảm: đối chiếu `reports/cslr_s06_predictions.json`
  (đầu ra model cũ) + ghi `limitations` trong JSON và khối. Không thổi phồng thành "đã chứng minh trên checkpoint cũ".
- **R2 Detector theo từ khóa.** Bỏ sót diễn đạt khác ("không được train", "độc lập", "never seen") ⇒ guard là điều kiện cần, không đủ; reviewer đọc diff. Bắt nhầm câu
  đúng (phủ định) ⇒ sổ `HISTORICAL` có `reason` (unified_run REPORT.md:19). Ngưỡng/từ khóa là hợp đồng §3.4, không nới khi gặp vi phạm.
- **R3 "Chưa thấy" phía ViT5.** Stage 2 cũ không dùng SENT271–300 (mã); stage 1: 0 cặp khớp theo luật L1/L2/gần trùng (`preregistration.json:362`), diễn đạt khác vẫn có thể
  lọt (13 R15). Khối chỉ nói "ViT5 stage 2 không dùng khi train"; không nói stage 1 trừ khi trỏ preregistration.
- **R4 Cỡ mẫu / chọn mẫu (phần B).** 30 câu không chọn ngẫu nhiên (30 id cuối), 1 người ký ⇒ CI rộng, không đại diện "câu mới bất kỳ"; chép nguyên giới hạn từ
  `test_eval.json`. Số mới không so trực tiếp với 23.18 / 32.80 (model cũ rò rỉ câu; WER cũ trên 300 clip).
- **R5 Rò rỉ / test nhiều lần.** Kế hoạch 14 không train, không đánh giá, không chạy lại test; phần B chỉ ĐỌC kết quả eval một lần của 13. Không chọn gì dựa trên số test.
- **R6 Lệch train–realtime.** Không áp dụng (không đổi tiền xử lý, model, backend, UI).
- **R7 Song song.** Đụng thứ tự với 13 B12/B11b/AC0 và 07 (§2.3); khối sinh tự cập nhật số dòng khi file đổi (L3 bắt lệch).
- **R8 Phụ thuộc git.** L4 + kiểm tracked cần lịch sử đầy đủ; clone nông → FAIL có thông báo (không skip).
- **R9 Xuống dòng.** Renderer giữ CRLF/LF của từng file; guard so sau chuẩn hóa LF; sha split theo luật CRLF→LF như preregistration.

## 7. Điểm dừng
- **Không chạm điểm dừng bắt buộc** (`docs/prompts/autopilot.md:69-73`): không đổi model mặc định; không cần dữ liệu người dùng; không xóa file; mọi thay đổi là
  file tracked, hoàn tác được bằng git; không sửa UI hiển thị cho người dùng cuối (`frontend/src` không có khẳng định CSLR — §2.2c); không đụng thay đổi chưa commit
  (B0 kiểm). Câu chữ README/PHASE4B theo đúng quyết định 02:40 ⇒ không hỏi lại.
- **CẦN NGƯỜI DÙNG — chỉ khi xảy ra:** B0 thấy thay đổi chưa commit trên một trong 12 file đích (lưu ý `docs/prompts/autopilot.md:38`: người dùng từng có sửa đổi chưa
  commit ở `reports/audit_round2/*.json`; kế hoạch chỉ sửa `.md` của thư mục này, nhưng vẫn kiểm) → dừng, không đụng.
- **CẦN PLANNER (14) — coder dừng, ghi 14-progress:** lf_sha256 dataset lệch preregistration (B0/B1b exit 3); detector ở B3 thấy file/dòng ngoài §2.2 (thêm file sống
  hoặc lịch sử); `preregistration.json` thật không thỏa P1 (luật bằng chứng sai); template không thể qua guard mà vẫn giữ ý bắt buộc §3.3; `test_eval.json` thiếu khóa
  hoặc không thỏa P2 (B7).
- **CẦN PLANNER việc khác (không chặn phần A):** kế hoạch 13 §3.9/B12 + §0B.5 AC0(a) (§2.3) — phải sửa TRƯỚC khi coder 13 tới B12; kế hoạch 07 ghi chú khi tới lượt.
- **Thông báo người dùng (không chặn):** backlog đính chính "Zero-Leakage" Cấp 2 (`README.md:18`, `docs/audit/final_status.md:13,24`) — mâu thuẫn `PROVENANCE.md:74`.
