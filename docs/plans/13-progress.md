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

## Đang làm
- B1 — gỡ Modal.

## Còn lại
- B2 script vocab + digest + test; B3–B13 (lượt sau).

## Sổ GPU (kế hoạch 13)
| Job | Phiên (phút, từ env.json) | Ghi chú |
|---|---|---|
| (chưa có job) | | |

## Nhật ký detect-changes
| Bước | Lệnh | Kết quả (nguyên văn risk) |
|---|---|---|
| B0-start (6048042) | `node .gitnexus/run.cjs detect-changes --scope staged --repo .` (index cũ dded0a6) | "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (`dc_B0start.txt`) |
| B0 | như trên (sau analyze) | "Changes: 1 files, 1 symbols / Affected processes: 34 / Risk level: critical" — symbol duy nhất: `Section Kế hoạch 13 — tiến độ (coder) → docs/plans/13-progress.md` (mục markdown); đối chiếu: diff chỉ là 1 file .md, không mã nào đọc file này (`git grep -n 13-progress -- src scripts backend tests` → 0) ⇒ nối nhầm của index, không có rủi ro thực (`dc_B0.txt`) |
