# Kế hoạch 13 — Train lại checkpoint thiếu trên Kaggle (stgcn_best, CSLR + vocab, ViT5) + gỡ Modal

> **CẦN NGƯỜI DÙNG (KHÔNG chặn việc nào; có mặc định an toàn — chi tiết §7.1):**
> - Q1. CSLR train lại theo (i) công thức cũ chia theo NGƯỜI KÝ (S06 đã "thấy" mọi câu qua người ký khác — ghi giới hạn) hay
>   (ii) chia theo CÂU (sạch hơn, khác model cũ, tốn thêm GPU)? **Mặc định: (i)** cho checkpoint ở đường dẫn mặc định; (ii) để backlog.
> - Q2 (chỉ hỏi nếu xảy ra): upload ViT5 (kích thước đo ở B10) từ máy local quá chậm (ETA > 3 giờ) → chọn cách lưu trữ. Mặc định khi chưa
>   trả lời: vẫn đặt ViT5 vào máy để chạy test; lưu trữ ViT5 = "đang chờ", kế hoạch chưa đóng.
> - Q3 (xác nhận): đặt checkpoint MỚI vào đúng đường dẫn mặc định (`checkpoints/stgcn_best.pt`, `cslr_best.pt`, `vit5_stage*/`) được hiểu
>   là thuộc quyết định 2026-10-02 09:20 ("không có thì train lại"), KHÔNG phải GATE đổi model mặc định (không model nào đang có bị thay;
>   model mặc định Cấp 2 `stgcn_tier2_indomain.pt` không đổi). **Mặc định: được phép.** Nếu người dùng phủ nhận → dừng trước B11.
>
> Trạng thái: XONG (planner, 2026-10-02). Tệp tạm: `_work/_plan13_tmp/`. Tiến độ coder: `docs/plans/13-progress.md`.

## 1. Mục tiêu & DoD
Tái tạo, dưới dạng ARTIFACT MỚI, các thứ bị mất trong sự cố 30/9 mà không có bản lưu trữ: `checkpoints/stgcn_best.pt` (a4),
`checkpoints/vit5_stage{1,2}/best_model/` (a5), `checkpoints/cslr_best.pt` (a6) + `data/external/vsl_gh/gloss_vocab_canonical.txt`,
bằng kernel Kaggle PRIVATE, đăng ký trước tiêu chí, lưu ngay lên dataset Kaggle PRIVATE kèm manifest sha256. Gỡ Modal khỏi repo.
- DoD 7 (kiểm thử): AC2 của kế hoạch 06 (31 module) về lại `Ran 526` `OK`, 0 skip (hiện 518 / 1 ERROR / 1 skip — 12-progress B9).
- DoD 4 (Ký câu): mở khóa CSLR → gloss → ViT5 cho kế hoạch 07 (07 bị chặn tới khi có a5/a6 — kế hoạch 12 §8.1 (A)).
- DoD 9 (tài liệu trung thực): đánh dấu số liệu cũ không áp cho artifact mới.
- Quyết định người dùng 2026-10-02 09:20 (`docs/STATE.md:153-154`): không có bản sao thì train lại trên Kaggle; bỏ Modal.
- a7 (`baseline_bigru.pt`, `transformer_best.pt`, `*.onnx`) NGOÀI phạm vi (như kế hoạch 12).

## 2. Hiện trạng (đã đọc mã; số dòng tại HEAD 44887b3)

### 2.1 Ai dùng từng artifact
| # | Artifact | Nơi dùng | Test cần |
|---|---|---|---|
| a4 | `checkpoints/stgcn_best.pt` (Tier 1, 50 lớp) | backbone CSLR `src/training/train_cslr.py:10,738` (nạp ở `:428-434`; thiếu thì "Training from scratch"); fallback của `VSLPredictor` chỉ khi thiếu a2 (`src/inference/predictor.py:66-70`); `src/inference/ensemble.py:90,255,424`, `src/export/export_onnx.py:33`, `scripts/benchmark_onnx.py:38` | `tests/test_vsl_system.py:116-130` — **chỉ dùng a4 làm cổng tồn tại** (`:118-119`); `VSLPredictor(model_type="stgcn")` thật ra nạp a2 `stgcn_tier2_indomain.pt` (có sẵn). ⇒ test không kiểm nội dung a4 (§6 R9) |
| a5 | `checkpoints/vit5_stage2/best_model/` (fallback stage1) | `src/translation/translator.py:29-30,61-68`; `VSLEndToEndTranslator` `src/translation/end_to_end.py:54`; backend `get_or_load_translator` `backend/main.py:214-219` → `POST /api/translate` (`:869`), WS live-stream khi câu CONFIRMED (`:1122-1123`) | `tests/test_translation_core.py:22-29` setUpClass (ERROR nếu thiếu) |
| a6 + vocab | `checkpoints/cslr_best.pt`, `data/external/vsl_gh/gloss_vocab_canonical.txt` | `src/translation/cslr_recognizer.py:26-27,53-56` (thiếu một trong hai → FileNotFoundError); `end_to_end.py:58-66` (bắt lỗi, chạy tiếp không CSLR) | cùng setUpClass (`test_translation_core.py:28` gọi `CSLRRecognizer` trực tiếp ⇒ có ViT5 mà thiếu a6/vocab vẫn ERROR) |

⇒ Để đạt 526/0 skip cần CẢ BA: a5, a6 + vocab, a4. Test KHÔNG assert số liệu của model cũ: chỉ kiểm khóa/shape/không rỗng
(`test_translation_core.py:44-101`, `test_vsl_system.py:116-130`); grep `tests/` cho `cslr_test_results|vit5_stage|benchmark_results|PHASE4B|cslr_best` → 0.
Ràng buộc duy nhất phụ thuộc chất lượng model: 4 test ViT5/E2E đòi bản dịch KHÔNG RỖNG (`:47,60,70,84`) — đó là kiểm hành vi, giữ nguyên.
⇒ Không cần quyết định nào về test: không test nào khóa số của model cũ.

### 2.2 Công thức train gốc (mã còn nguyên trong repo)
- **a4 stgcn_best (Tier 1):** `train.py` + `configs/experiments/stgcn.yaml` (STGCNModel [64,64,128], 100 epoch, patience 10, lr 1e-3,
  bs 16, AMP; checkpoint `checkpoints/stgcn_best.pt`, history `experiments/stgcn/history.json`). Chọn epoch theo VAL top-1 (hòa → val loss)
  `src/training/trainer.py:196-215`; định dạng `{epoch, model_state_dict, optimizer_state_dict, val_top1, val_loss, val_top5, val_macro_f1}`
  (không có label_map). Test một lần: `evaluate_test.py --config … --checkpoint … --output-dir …` (`:332-357`; ghi `benchmark_results.json` `:316`).
  Dữ liệu: `get_vsl_dataloaders(tier="tier1")` mặc định HIỆN TẠI = `data/splits/folds/tier1_grouped_{train,val,test}.csv` + guard
  (`src/data/vsl_dataset.py:406-429`), npz phẳng `data/extracted_keypoints/<video_id>.npz` (`:314-315`). Cả hai **untracked, còn trên
  đĩa** (12-progress B0). **`train.py` không đặt seed** (`train.py:72-187`).
  Nguồn gốc a4 cũ: `docs/phase6_stgcn.md:221-247` ghi best epoch 49; `experiments/stgcn/benchmark_results.json:4,16` ghi best epoch 26 — hai
  lần chạy khác nhau, đều TRƯỚC split theo bản quay (`reports/audit_round3/PROVENANCE.md:73`). ⇒ KHÔNG tái tạo split cũ (rò rỉ bản quay; guard chặn).
- **a6 CSLR:** `python src/training/train_cslr.py` (mặc định bs 8, 40 epoch, stage1 10 epoch backbone đóng băng lr 1e-3, stage2 lr 1e-4/5e-4,
  patience 10, seed 42 — `:718-752`; smoke test chạy trước khi train). Dữ liệu `data/external/vsl_gh/{dataset_canonical.json, keypoints_frontal/}`
  (khôi phục ở kế hoạch 12 B8), `normalize=True`, `semantic`; split theo NGƯỜI KÝ: train S01–S04 (cả 300 câu), val S05, test S06 (`:359-384`);
  chọn theo val WER S05 (`:625-631`); test S06 MỘT lần cuối hàm (`:661-679`). Checkpoint chứa `gloss_vocab_hash` = 16 hex đầu sha256(vocab)
  (`:64-67,345,613`). **Ghi đè file tracked** `reports/cslr_training_history.{json,csv}`, `reports/cslr_test_results.json` (`:647-711`).
- **vocab:** không script nào ghi `gloss_vocab_canonical.txt` (grep: chỉ nơi đọc — `train_cslr.py:737`, `cslr_recognizer.py:27`,
  `modal_runner.py:201-202`). Cơ chế có sẵn: `VSLGlossVocabulary.from_canonical_dataset(json)` (`src/data/vsl_gh_dataset.py:277-287`):
  `<blank>`, `<unk>`, rồi gloss duy nhất đã sắp xếp (`:225-232`). `.save()` mở file chế độ văn bản không `newline=` (`:289-293`) ⇒ Windows ghi
  CRLF, Linux ghi LF ⇒ sha256 khác giữa hai máy (§6 R3). Số token tham chiếu 372 (`docs/vsl_gh_dataset.md:19`; `reports/cslr_dry_run_results.json:6`).
  Planner không có shell ⇒ B0 tra `git log --all -S`.
- **a5 ViT5:** stage1 `scripts/train_translation_stage1.py` (base `VietAI/vit5-base` tải từ HF, 3 epoch, bs 8 × accum 2, lr 5e-5, seed 42;
  `Clean10kDataset` = `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl` chia 90/10 bằng `random.Random(42)` — `src/translation/dataset.py:24-43`;
  chọn theo val loss; lưu `checkpoints/vit5_stage1/best_model`; ghi đè tracked `reports/vit5_stage1_history.json` `:178`).
  stage2 `scripts/train_translation_stage2.py` (từ stage1, 15 epoch, bs 8, lr 2.5e-5, patience 5, seed 42; `VSLGHTextDataset` train SENT001–240,
  val SENT241–270; SENT271–300 không dùng — `dataset.py:92-101`; ghi đè tracked `reports/vit5_stage2_history.json` `:191`). Không script nào chạy TEST ViT5.
  **`vie_vsl_10k_cleaned.jsonl` CHƯA khôi phục** (kế hoạch 12 chỉ có `vie_vsl_10k.jsonl`, 9405 dòng); sinh bằng
  `scripts/clean_10k_translation_corpus.py` (đường dẫn tương đối project_root, ghi đè đích không kiểm — `:14-16,93`; chế độ văn bản ⇒ CRLF trên Windows).
  `scripts/prepare_canonical_translation.py` gắn cứng `PROJECT_ROOT = Path("C:/Users/Admin/…")` (`:23-24,33-34`) ⇒ trên Kaggle phải nạp bằng
  importlib và đặt lại biến đường dẫn (cách runner B8 kế hoạch 12), không sửa script.
  Số tham chiếu: 7140 cặp (`reports/audit_20260924/inventory_summary.json:88`), train/val 6426/714 (`reports/vit5_stage1_history.json:4-5`),
  stage2 240/30 (`reports/vit5_stage2_history.json:3-4`).
- Thời gian lịch sử (RTX 3050 laptop — cơ sở ước lượng §3.7): stgcn 2.27 phút (`docs/phase6_stgcn.md:222`); CSLR 2108.74 s / 40 epoch
  (`reports/cslr_test_results.json:5-7`); ViT5 stage1 1293.08 s (`reports/vit5_stage1_history.json:8`), stage2 145.94 s (`reports/vit5_stage2_history.json:7`).

### 2.3 Hạ tầng Kaggle có sẵn
- Mẫu kernel: `kaggle/vsl-train-harmonized/` (clone repo GitHub → chạy script; 2 GPU song song bằng thread; ghi `/kaggle/working/<out>/`;
  VSL-GH dựng lại từ upstream @6c351e6 bằng `scripts/prepare_canonical_vsl_gh.py` chạy không tham số — `train_harmonized_kernel.py:26-33,61-82`);
  metadata `is_private: true`, `enable_internet: true`. Quy trình: `.claude/skills/vsl-cloud-jobs/SKILL.md`, `docs/cloud_training.md:16-29`.
- Lưu trữ private: `scripts/archive_private_kaggle.py` gắn cứng danh sách file (`:147-184`) và, như `archive_step4_kaggle.py`, bắt
  staging/download NGOÀI repo (`archive_step4_kaggle.py:79-81,213-215,253-255`) — mâu thuẫn quyết định 2026-09-30 23:45 (tạm chỉ trong `_work/`;
  bẫy T3 kế hoạch 12). Giới hạn 2 GiB (`archive_private_kaggle.py:77`). ⇒ cần công cụ tương đương mới (§3.4c), tái dùng helper.
- Băng thông: skill ghi "Mạng local ~100 KB/s → tránh upload lớn" (`SKILL.md:22`); tải xuống đo ở kế hoạch 12 ~21 MB/s. Upload chưa đo.
- Ngân sách GPU: tự giới hạn 10 giờ/tuần (`docs/prompts/autopilot.md:65-66`); STATE "Tài nguyên": ~6 giờ đã dùng tuần này (chưa xác minh).

### 2.4 Modal
- `src/training/modal_runner.py` (262 dòng; `import modal` cấp module `:31`; app `vslt-cloud`, volume `vslt-data-volume`; hàm
  `check_cloud_environment`, `run_cslr_on_modal`, `write_file_to_volume`, `read_file_from_volume`, `list_volume_files`, `main`).
  Không module nào import nó (`src/training/__init__.py` chỉ export `VSLTrainer`); gói `modal` KHÔNG có trong `.venv`, không trong requirements.
- Tham chiếu khác (grep `-i modal`, trừ `_work/ data/ clone/ node_modules/ .venv/`): `docs/plans/12-khoi-phuc-du-lieu.md:39,81,82,239-243`
  (hướng dẫn tra Modal volume); `.claude/handoffs/2026-09-25-after-cleanup.md:34` (lịch sử); `reports/guard_dod7_2026-09-29/guard_findings.json:107`
  (báo cáo lịch sử); `docs/STATE.md` (của orchestrator).
- KHÔNG phải Modal cloud (giữ nguyên): `frontend/src/components/Dictionary.jsx:143` (`{/* Video Player Modal */}` — hộp thoại UI);
  `docs/translation_corpus_profile.md:29,73`, `reports/PHASE4B_REPORT.md:45` ("modal verb" — ngữ pháp).
- `tests/test_backend_source_guard.py`: grep `modal` trong `tests/` → 0 ⇒ registry không có mục của `modal_runner.py`.

## 3. Thiết kế

### 3.1 Nguyên tắc
1. Mỗi checkpoint train lại là ARTIFACT MỚI: số liệu cũ (README, EVALUATION, `reports/PHASE4B_REPORT.md`, `reports/cslr_*`, `reports/vit5_*`,
   `experiments/stgcn/*`, `docs/phase6_stgcn.md`) KHÔNG áp dụng; không ghi đè file cũ nào; số liệu mới chỉ nằm trong JSON mới dưới
   `reports/retrain_<D>/` (`<D>` = ngày coder làm B5, cố định cho cả kế hoạch) kèm lệnh + commit.
2. Đăng ký trước (§3.3) được commit TRƯỚC khi đẩy kernel nào. Chọn epoch bằng VAL theo luật có sẵn trong mã; TEST chạy đúng một lần
   (stgcn: Tier 1 test; CSLR: S06 cuối `train_cslr`); ViT5: KHÔNG chạy test nào ở kế hoạch này (để kế hoạch 07 đo có đăng ký trước).
   Không thử seed khác, không chạy lại vì kết quả kém; chạy lại chỉ khi lỗi hạ tầng (§3.6).
3. Kernel PRIVATE, clone repo ở commit GHIM (assert `git rev-parse HEAD`), mọi đầu vào kiểm digest so với giá trị tính ở máy local
   và ghi trong đăng ký trước — lệch → kernel dừng TRƯỚC khi train.
4. Mọi checkpoint mới lên dataset Kaggle PRIVATE + manifest sha256 commit trong repo trước khi coi là xong. Không commit `.pt`/model/dữ liệu.
5. Không sửa mã train/model/tiền xử lý ngoài: `train.py` thêm `--seed` (mặc định giữ hành vi cũ). Mọi ghi đè file tracked của script train
   chỉ xảy ra TRONG bản clone trên Kaggle (`/tmp/vslt`), không bao giờ chép ngược đè lên repo local.

### 3.2 Luồng dữ liệu
```
LOCAL (Windows)                                   KAGGLE (private)
data/extracted_keypoints + tier1_grouped_*.csv ─► dataset vslt-retrain-inputs-tier1 ─► K1 vsl-retrain-stgcn-tier1 (GPU)
                                                                                        train.py --seed 42 → evaluate_test.py ×1
                                                                                        → stgcn_best.pt + meta + eval JSON
VSL-GH upstream @6c351e6 (GitHub) ─────────────────────────────────────────────► K2 vsl-retrain-cslr-vit5
Parallel-Corpus @f57558c3 (GitHub), VietAI/vit5-base (HF) ─────────────────────►   MODE=preflight (CPU): dựng dữ liệu, so digest
output K1 (kernel_sources) ────────────────────────────────────────────────────►   MODE=train (GPU T4×2): GPU0 CSLR | GPU1 ViT5 s1→s2
                                                                                        → cslr_best.pt, vocab, vit5_stage{1,2}/best_model
kaggle kernels output → _work/_plan13_tmp/k_* → kiểm SHA256SUMS → archive_retrain_kaggle stage/upload/verify → dataset PRIVATE
                                                                   → cp -n vào checkpoints/ + data/external/ → test
```
Base model `VietAI/vit5-base` chỉ tải trên Kaggle (không tải về máy local); máy local chỉ nhận model ĐÃ fine-tune.

### 3.3 Đăng ký trước — `reports/retrain_<D>/preregistration.json` (commit ở B5, trước mọi kernel)
Sinh bằng script `scripts/retrain_preregister.py` (mới, chỉ đọc + ghi đúng file này, từ chối ghi đè) — KHÔNG gõ tay giá trị:
- `generated_by{command, git_commit, code_dirty, generated_at_utc}`.
- `inputs`: với mỗi đầu vào — đường dẫn, `sha256` (file nhị phân) hoặc `lf_sha256` (= sha256 sau khi thay `\r\n`→`\n`, cho file văn bản),
  số dòng/số mẫu đo bằng code: `vie_vsl_10k.jsonl`, `vie_vsl_10k_cleaned.jsonl`, `dataset_canonical.json`, `gloss_vocab_canonical.txt`,
  digest gộp `keypoints_frontal` (sha256 của chuỗi `"<tên> <sha256>\n"` sắp theo tên, 4200 dòng), 3 CSV `tier1_grouped_*` + `tier1_grouped_classes.txt`,
  digest gộp các npz Tier 1 cần dùng; số mẫu: `Clean10kDataset` train/val, `VSLGHTextDataset` train/val, `VSLGHContinuousDataset` train/val/test,
  số dòng 3 CSV Tier 1, số lớp.
- `reference_counts` (chỉ để so, kèm nguồn file:dòng): 372 token, 7140 / 6426 / 714, 240 / 30, 3600 / 300 / 300 (`docs/data_registry.md:71`).
- `jobs`: K1, K2-CSLR, K2-ViT5s1, K2-ViT5s2 — lệnh nguyên văn, seed 42, luật chọn epoch (trích file:dòng §2.2), split dùng để chọn, split TEST
  và "chạy một lần" (ViT5: "không test"), kiểm hợp lý (§3.6), trần GPU (§3.7).
- `libs_local`: phiên bản `torch`, `transformers`, `tokenizers`, `sentencepiece`, `safetensors` trong `.venv` (B0) — K2 cài đúng
  `transformers/tokenizers/sentencepiece/safetensors` này để model lưu ra nạp được ở local (§6 R4).
- `artifacts_planned`: đường dẫn đích local + slug dataset lưu trữ.
Kernel đọc file này TỪ bản clone ở commit ghim (không hằng số gõ tay trong script kernel). Giá trị phụ thuộc K1 (sha256 `stgcn_best.pt`)
nằm ở `reports/retrain_<D>/k1_outputs.json`, commit SAU K1, TRƯỚC K2-train.

### 3.4 Công cụ mới
**(a) `scripts/build_gloss_vocab_canonical.py`** — `--canonical <dataset_canonical.json> --out <file>`; dùng
`VSLGlossVocabulary.from_canonical_dataset` để lấy thứ tự token, nhưng tự ghi bytes UTF-8, mỗi token + `"\n"` (LF trên mọi OS); đích đã có → exit 2,
không ghi; in số token + sha256. Nếu B0 tìm thấy cách sinh gốc trong lịch sử git → dùng đúng logic đó (ghi commit vào 13-progress), giữ LF.
**(b) `train.py --seed N`** — tùy chọn; có thì đặt seed `random`, `numpy`, `torch`, `torch.cuda` trước khi tạo DataLoader; KHÔNG có
(mặc định) thì hành vi y như cũ. Không đụng `VSLTrainer`.
**(c) `scripts/archive_retrain_kaggle.py`** — tương đương `archive_private_kaggle.py` cho artifact train lại:
- `stage --src <thư mục trong _work/> --staging _work/_plan13_tmp/staging_<tên> --dataset phmvnsm33/<slug> --title … --licence-note …`:
  chép đệ quy mọi file (từ chối symlink/junction/reparse point, từ chối thư mục rỗng), `archive_name` = đường dẫn tương đối, `/`→`__`;
  ghi `SHA256SUMS` + `dataset-metadata.json` (`isPrivate: true`); quét chuỗi giống credential cho file văn bản (tái dùng `SECRET_PATTERNS`
  của `archive_private_kaggle`); tổng > 3 GiB → exit 2; staging đã có → exit 2.
- `upload`: chỉ `api.dataset_create_new(folder, public=False, dir_mode="skip")` — không bao giờ version/update/delete (như ràng buộc ở
  `tests/test_archive_step4_kaggle.py:372-378`); slug đã tồn tại → exit 5.
- `verify --download-dir _work/_plan13_tmp/verify_<tên> --manifest-out reports/retrain_<D>/<tên>_manifest.json`: chờ ready, private theo 2 nguồn
  (`private_from_list`, `private_from_metadata`), danh sách + kích thước trên Kaggle == staging, tải về, sha256 từng file == SHA256SUMS; manifest
  có `generated_by{script, command, git_commit, code_dirty, verified_at_utc}`, `dataset{ref, is_private, …}`, `files[{rel_path, archive_name,
  size_bytes, sha256, sha256_after_download}]`.
- `restore --manifest … --download-dir _work/… --dest <thư mục>`: kiểm hết rồi mới ghi, không ghi đè file khác hash.
- Ràng buộc đường dẫn: `--src/--staging/--download-dir` phải nằm dưới `<repo>/_work/` (thay cho "ngoài repo" của script cũ — quyết định
  2026-09-30 23:45); `--manifest-out` trong repo chỉ được là `reports/retrain_<D>/*_manifest.json`. Mã thoát giống `archive_step4_kaggle` (0/2/3/4/5/6).
- Tái dùng không sửa: `sha256_file, check_dataset_ref, read_metadata, check_staging, wait_ready, private_from_list, private_from_metadata,
  remote_files, sums_text, parse_sums, git_head, pkg_version, kaggle_api` của `archive_step4_kaggle`. KHÔNG sửa 2 script archive cũ.
  (`private_from_metadata` tạo thư mục tạm hệ thống cho 1 file metadata nhỏ và xóa ngay — `archive_step4_kaggle.py:314-325`; chấp nhận, không đổi.)
**(d) `scripts/retrain_preregister.py`** (§3.3) và `scripts/retrain_digest.py` (hàm `lf_sha256`, `dir_digest`) — dùng chung cho local và kernel.
**(e) Kernel** `kaggle/vsl-retrain-stgcn-tier1/{kernel-metadata.json, retrain_stgcn_kernel.py}` và
`kaggle/vsl-retrain-cslr-vit5/{kernel-metadata.json, retrain_cslr_vit5_kernel.py}` — `is_private: true`, `enable_internet: true`,
GPU theo bước; clone `https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git` (URL như kernel cũ) nhánh `feat/vslt-complete`
rồi `git checkout <commit ghim>` + assert; mọi đầu ra vào `/kaggle/working/<job>/`: checkpoint, history/test JSON (đổi tên khi chép), log từng
job, `env.json` (commit, phiên bản Python/torch/transformers/CUDA, tên GPU, số GPU, HF snapshot sha của `VietAI/vit5-base`, thời điểm bắt
đầu/kết thúc từng job, tổng phút), `SHA256SUMS`. Watchdog thời gian tường: K1 45 phút, K2 105 phút (vượt → kill tiến trình con, exit ≠ 0).
K1: đặt 3 CSV vào `data/splits/folds/`, npz vào `data/extracted_keypoints/` trong bản clone, kiểm sha256 so manifest inputs; `train.py --config
configs/experiments/stgcn.yaml --seed 42`; `evaluate_test.py --config … --checkpoint checkpoints/stgcn_best.pt --output-dir /kaggle/working/k1/eval`
đúng 1 lần; thêm `stgcn_best.meta.json`: `label_map` (từ `get_vsl_dataloaders`), sha256 3 CSV, seed, commit (sidecar — không đổi định dạng checkpoint).
- K2 `MODE` là hằng trong script, đổi bằng commit: `preflight` (CPU, không GPU quota): clone 3 nguồn (repo ghim; VSL-GH @6c351e6 vào
  `clone/Vietnamese-Sign-Language-Translation`; Parallel-Corpus @f57558c3 vào `clone/Parallel-Corpus-Vie-VSL`), chạy `prepare_canonical_vsl_gh.py`
  (không tham số, như kernel harmonized), `prepare_canonical_translation.py` qua importlib với `CORPUS_DIR`/`OUTPUT_DIR`/`OUTPUT_JSONL`/`REPORT_JSON`
  đặt lại vào bản clone (§2.2), `clean_10k_translation_corpus.py`, `build_gloss_vocab_canonical.py`; cài phiên bản thư viện ở `libs_local`; tải
  tokenizer+model `VietAI/vit5-base`; đếm mẫu 3 dataset; so mọi digest/đếm với `preregistration.json` → in bảng khớp/lệch, exit ≠ 0 nếu lệch.
  `train`: làm lại toàn bộ preflight (vẫn exit nếu lệch), chép `stgcn_best.pt` từ output K1 vào `checkpoints/` và assert sha256 ==
  `k1_outputs.json`, rồi thread GPU0: `train_cslr.py` (đủ tham số mặc định, có smoke test); thread GPU1: stage1 → stage2 (`--stage1-path
  checkpoints/vit5_stage1/best_model`). Chỉ 1 GPU → chạy tuần tự CSLR rồi ViT5 (watchdog vẫn áp).

### 3.5 Đặt vào chỗ (B11)
`cp -n` từ bản ĐÃ verify (staging) vào đích; trước đó kiểm đích chưa tồn tại; sau đó sha256 đích == manifest. Đích:
`checkpoints/stgcn_best.pt`, `checkpoints/cslr_best.pt`, `checkpoints/vit5_stage1/best_model/*`, `checkpoints/vit5_stage2/best_model/*`,
`data/external/vsl_gh/gloss_vocab_canonical.txt` (bản sinh ở local B2 — phải bằng hệt bản K2 dùng), `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl`
(B3). Không đặt `cslr_stage1_best.pt`/`cslr_latest.pt` (chỉ lưu trữ nếu muốn). Không tạo link/junction.

### 3.6 Kiểm hợp lý (đăng ký trước; KHÔNG phải ngưỡng chất lượng)
- Mọi loss trong history hữu hạn (không NaN/Inf); có best epoch ≥ 1.
- stgcn: val top-1 ở best epoch > 100 / số_lớp (mức ngẫu nhiên, số lớp đọc từ label_map).
- CSLR: `best_val_wer` < 100.
- ViT5: stage2 sinh câu không rỗng cho đầu vào của `test_translation_core` (kiểm ở B11 bằng chính test đó).
Không đạt → DỪNG, CẦN NGƯỜI DÙNG (không chạy lại với seed/cấu hình khác). Chạy lại chỉ được phép khi lỗi hạ tầng (ngoại lệ trước khi xong
epoch đầu, Kaggle lỗi/hết phiên, lỗi mạng khi clone/pip/HF) — tối đa 1 lần/job, cùng cấu hình, ghi vào 13-progress.

### 3.7 Thứ tự, ước lượng GPU-giờ, trần
| Job | Mở khóa | Cơ sở ước lượng (thời gian lịch sử trên RTX 3050) | Ước lượng (chưa xác minh) | Trần cứng |
|---|---|---|---|---|
| K2-preflight (CPU) | phát hiện lệch dữ liệu/thư viện sớm | — | 0 GPU-giờ | — |
| K1 stgcn Tier 1 (GPU T4) | `test_vsl_predictor_smoke` (cổng a4); backbone cho CSLR | 2.27 phút train + khởi động/clone | ≤ 0,25 | 0,75 (watchdog 45') |
| K2-train (GPU T4×2 song song) | `test_translation_core` (cần cả ViT5 + CSLR + vocab) | CSLR 2108.74 s ∥ ViT5 1293.08 + 145.94 s + tải HF/pip | ≤ 1,0 | 1,75 (watchdog 105') |
| **Tổng kế hoạch 13** | | | **≤ 1,25** | **2,5** |

Thời gian thật = thời gian phiên đọc từ `env.json`/log kernel (ghi vào sổ GPU trong 13-progress). Trước MỖI job GPU: nếu
`GPU tuần đã dùng (STATE) + GPU đã dùng ở kế hoạch 13 + trần job` > 10 → DỪNG, CẦN NGƯỜI DÙNG. Với số STATE hiện tại (~6) cả hai job lọt.
Song song GPU0/GPU1 trong một phiên tính quota một lần (cách của `vsl-train-harmonized`). K1 phải xong trước K2-train (backbone).
Không mở khóa test nào riêng lẻ: `test_translation_core` cần đủ ViT5 + CSLR + vocab ⇒ AC2-06 chỉ kiểm được sau K2-train.

### 3.8 CSLR: (i) hay (ii) — khuyến nghị (i)
- (i) Công thức cũ, chia theo người ký: tái tạo đúng hợp đồng mà test, backend và kế hoạch 07 (C1 tập con `S06_vit5_clean`,
  `cslr_train_occurrences`) giả định; giới hạn rò rỉ đã biết và chỉ ảnh hưởng LỜI DIỄN GIẢI số S06 (CSLR đã thấy mọi câu S06 qua người
  ký khác — `docs/cloud_reports/viec-A-D-2026-09-29.md:45-48`), không ảnh hưởng chức năng ⇒ ghi giới hạn (§3.9).
- (ii) Chia theo câu (train S01–S04 × SENT001–240, val S05 × SENT241–270, test S06 × SENT271–300, đồng bộ split ViT5 stage2; vocab chỉ từ
  câu train): cần sửa `VSLGHContinuousDataset`/`train_cslr.py` (tùy chọn mới, mặc định giữ nguyên) + test; ~+0,6 GPU-giờ (ước lượng);
  TEST chỉ 30 mẫu một người ký → khoảng tin cậy rất rộng; ViT5 stage1 (10k) có thể đã chứa các câu đó (C1 của 07 mới đo) ⇒ "chưa thấy câu"
  vẫn chưa chắc. Model khác ⇒ kế hoạch 07 phải lập lại một phần.
- Khuyến nghị: (i) cho checkpoint ở đường dẫn mặc định (mặc định nếu chưa trả lời). (ii) = mục backlog sau DoD 1–7, artifact riêng
  `checkpoints/cslr_sentsplit_best.pt` (không thay mặc định — nếu muốn thay là GATE riêng), lập kế hoạch riêng khi người dùng chọn.

### 3.9 Đánh dấu tài liệu (chỉ THÊM dòng, không xóa/sửa câu cũ)
Dòng đánh dấu bắt đầu bằng `> **[Kế hoạch 13 — artifact mới]**`: "Số liệu ở mục này đo trên checkpoint CŨ (mất 30/9/2026, không còn tái lập).
Checkpoint hiện tại train lại ngày <D> trên Kaggle (kế hoạch 13) — số liệu của nó chỉ ở `reports/retrain_<D>/`; hai bộ số KHÔNG so sánh trực tiếp."
Vị trí: `README.md` trước dòng 56 (khối Cấp 3) và cạnh dòng 112-113 (`stgcn_best.onnx` — a7, không còn); `EVALUATION.md` đầu §12 (`:342`) và
§13.4 (`:407`); `docs/phase6_stgcn.md` đầu §8 (`:219`) và §9 (`:233`); `reports/PHASE4B_REPORT.md` sau dòng 112. Thêm dòng đính chính rò rỉ
(nguồn: `docs/cloud_reports/viec-A-D-2026-09-29.md:45-48`) ngay sau `README.md:56`, `reports/PHASE4B_REPORT.md:112`, `EVALUATION.md:390`,
`reports/audit_round2/VERIFY.md:14`: "CSLR (cũ và (i) mới) train trên S01–S04 cho CẢ 300 câu ⇒ S06 chỉ chưa thấy NGƯỜI KÝ, không phải chưa
thấy câu." README mục "Artifact không nằm trong git": thêm 3 dòng (slug dataset + đường dẫn manifest). `docs/cloud_training.md`: thêm 2 kernel
mới vào bảng và 1 dòng "Modal: không dùng — `src/training/modal_runner.py` đã gỡ ngày <D> (kế hoạch 13)". KHÔNG gõ số liệu mới vào md.
Không sửa JSON báo cáo cũ (`reports/cslr_*`, `reports/vit5_*`, `experiments/stgcn/*`).

### 3.10 Gỡ Modal (Phần B)
- `git rm src/training/modal_runner.py` (file tracked ⇒ hoàn tác được bằng git; được phép bởi quyết định 09:20 "bỏ Modal"). Trước đó:
  GitNexus `impact` upstream cho 6 hàm ở §2.4 + `Grep` `modal_runner|run_cslr_on_modal|vslt-data-volume|import modal|from modal` trên
  `src scripts backend tests kaggle configs frontend/src` (index từng nối nhầm `main` vào mọi luồng — 12-progress B5/B8 — nên HIGH/CRITICAL do `main`
  phải đối chiếu bằng grep, ghi cả hai vào 13-progress).
- Tài liệu: thêm 1 dòng dưới §8.1 mục 2 của `docs/plans/12-khoi-phuc-du-lieu.md`: "> (2026-10-02, kế hoạch 13) Modal không dùng; `src/training/modal_runner.py`
  đã gỡ ở commit <hash> — mục này không còn áp dụng." + dòng ở `docs/cloud_training.md` (§3.9). KHÔNG sửa `.claude/handoffs/*`,
  `reports/guard_dod7_2026-09-29/guard_findings.json` (lịch sử), `docs/STATE.md` (orchestrator). KHÔNG đụng `Dictionary.jsx` (modal UI).
- Không có gì để gỡ trong requirements/.venv. Sau xóa: `node .gitnexus/run.cjs analyze --index-only`.

### 3.11 Test mới
- `tests/test_retrain_tools.py` (không mạng, không GPU): vocab script (thứ tự `<blank>`,`<unk>`, sắp xếp; LF; từ chối ghi đè; tất định), `lf_sha256`/`dir_digest`,
  `train.py --seed` (parse; mặc định None không gọi seed), `archive_retrain_kaggle` với API giả (private cố định, không gọi version/update/delete,
  staging ngoài `_work/` → 2, symlink → 2, trùng staging → 2, sha lệch → 3, slug tồn tại → 5, manifest-out sai chỗ → 2, restore không ghi đè),
  `retrain_preregister.py` từ chối ghi đè.
- `tests/test_retrained_artifacts.py` (dùng artifact thật; thiếu → skip có lý do — nhưng AC đòi 0 skip): sha256 các artifact == manifest đã
  commit; `STGCNModel(num_classes=len(label_map))` nạp `stgcn_best.pt` strict, label_map từ `stgcn_best.meta.json` == thứ tự `tier1_grouped_classes.txt`;
  `VSLPredictor(model_type="stgcn", stgcn_ckpt="checkpoints/stgcn_best.pt", classes_path=<tier1 classes>, device="cpu")` dự đoán được (test THẬT của
  a4 — bù cho cổng chỉ-tồn-tại, §6 R9); `cslr_best.pt["gloss_vocab_hash"]` == 16 hex đầu sha256(vocab local); `CSLRRecognizer` nạp được,
  `num_classes` == số dòng vocab; ViT5 stage2 nạp bằng `VSLTranslator(model_path=…)`.

## 4. Chia việc (mỗi bước commit riêng; ghi 13-progress; impact trước khi sửa symbol có sẵn; detect-changes trước commit)

| Bước | Việc | Ước lượng | Phụ thuộc |
|---|---|---|---|
| B0 | Kiểm kê CHỈ ĐỌC → `_work/_plan13_tmp/B0_*.txt`: `git status --porcelain` (mốc), 3 dòng ` D` của người dùng; `git log --all --oneline -S gloss_vocab_canonical`, `-S from_canonical_dataset`, `-S vie_vsl_10k_cleaned`; `.venv` `pip show torch transformers tokenizers sentencepiece safetensors`; đếm dòng 3 CSV `tier1_grouped_*`, mọi `video_id` có npz trong `data/extracted_keypoints/`, tổng dung lượng các npz đó; `git ls-files` cho `data/splits/folds/tier1_grouped_*`, `experiments/stgcn/`; `keypoints_frontal` đủ 4200; đích a4/a5/a6/vocab/cleaned CHƯA tồn tại; nhánh đã push tới HEAD trên GitHub. Tạo `docs/plans/13-progress.md` (sổ GPU, nhật ký detect-changes). | 0,75 h | — |
| B1 | Phần B — gỡ Modal (§3.10). | 1 h | B0 |
| B2 | `scripts/retrain_digest.py` + `scripts/build_gloss_vocab_canonical.py` + test (đỏ trước) trong `tests/test_retrain_tools.py`; sinh vocab vào `_work/_plan13_tmp/vocab/` → đếm, sha256 (đặt vào chỗ ở B11). | 1,5 h | B0 |
| B3 | Sinh `vie_vsl_10k_cleaned.jsonl` vào `_work/_plan13_tmp/cleaned/` bằng runner trong `_work/` (importlib, đổi biến đích, không sửa script) → đếm dòng, `Clean10kDataset(jsonl_path=…)` train/val, `lf_sha256`. Đóng gói đầu vào Tier 1 vào `_work/_plan13_tmp/src_inputs_tier1/` (3 CSV + classes + đúng các npz cần, không link). | 1 h | B0 |
| B4a | `train.py --seed` + test. impact `main`, `parse_args` (`train.py`). | 0,5 h | B0 |
| B4b | `scripts/archive_retrain_kaggle.py` + test (API giả). | 2 h | B2 (digest) |
| B5 | `scripts/retrain_preregister.py` + test; 2 thư mục kernel (§3.4e, K2 `MODE="preflight"`); sinh + commit `reports/retrain_<D>/preregistration.json`; chạy AC8-a; commit; `git push` nhánh; commit này = commit ghim. | 2 h | B2, B3, B4a |
| B6 | Lưu trữ đầu vào Tier 1: `archive_retrain_kaggle stage/upload/verify` → dataset `phmvnsm33/vslt-retrain-inputs-tier1`, manifest `reports/retrain_<D>/inputs_tier1_manifest.json`; ĐO tốc độ upload (byte/thời gian) ghi 13-progress. | 0,5 h + chờ | B4b, B5 |
| B7 | Đẩy K2 ở `MODE=preflight` (CPU, không accelerator); theo dõi bằng `kaggle kernels status` thật; tải output; mọi dòng digest/đếm khớp. Lệch → DỪNG (§7.2). | 0,5 h + chờ | B5 |
| B8 | Kiểm ngân sách (§3.7) → đẩy K1 (GPU) → theo dõi → `kaggle kernels output` vào `_work/_plan13_tmp/k1/` (`PYTHONUTF8=1`) → kiểm SHA256SUMS, kiểm hợp lý, đúng 1 lần evaluate_test trong log → commit `reports/retrain_<D>/k1/` (JSON + log, không `.pt`) + `k1_outputs.json`. Ghi sổ GPU. | 0,5 h + chờ | B6, B7 |
| B9 | Đổi K2 sang `MODE="train"` + GPU T4×2 (commit, push, cập nhật commit ghim) → kiểm ngân sách → đẩy → theo dõi → tải output vào `_work/_plan13_tmp/k2/` → kiểm SHA256SUMS, kiểm hợp lý, vocab K2 == vocab B2 (bằng hệt byte), HF snapshot sha preflight == train (khác → chỉ ghi), đúng 1 dòng "PRIMARY TEST EVALUATION" → commit `reports/retrain_<D>/k2/` (JSON + log). Ghi sổ GPU. | 0,75 h + chờ | B8 |
| B10 | Lưu trữ đầu ra: dataset `phmvnsm33/vslt-retrain-artifacts` (stgcn_best.pt + meta, cslr_best.pt, cslr_stage1_best.pt, vocab, cleaned jsonl, JSON/log) và `phmvnsm33/vslt-retrain-vit5` (vit5_stage2/best_model, vit5_stage1/best_model) → verify → 2 manifest commit. Trước ViT5: ETA = kích thước / tốc độ đo ở B6; ETA > 3 h → Q2 (§7.1), tiếp B11 với ViT5 từ output đã kiểm. | 1 h + chờ upload | B9 |
| B11 | Đặt vào chỗ (§3.5) + `tests/test_retrained_artifacts.py` + AC8-b..e. | 2 h | B10 (hoặc B9 + Q2) |
| B12 | Đánh dấu tài liệu (§3.9). | 1,5 h | B11 |
| B13 | Đóng: `docs/progress_log.md` 1 dòng; 13-progress bảng cuối (artifact → job/commit → sha256 → manifest → test); AC0 kiểm cuối. | 0,5 h | B12 |

B1 độc lập, làm sớm để giảm nhiễu GitNexus. B2/B3/B4a song song được. Job Kaggle chạy nền; coder đợi bằng vòng lặp thưa (≥ 5 phút/lần),
chỉ báo "xong" khi `kaggle kernels status` trả COMPLETE (hoặc ERROR) thật. Theo dõi trạng thái thật sau mỗi lần khôi phục phiên.

## 5. Tiêu chí chấp nhận (hợp đồng — coder không đổi; chỉ planner đổi, ghi lý do)

**AC0 — An toàn cây làm việc.** (a) `git status --porcelain` cuối so mốc B0: chỉ thêm file trong danh sách §3.4/§3.9/§3.11, `reports/retrain_<D>/`,
`docs/plans/13-progress.md`, `kaggle/vsl-retrain-*`; xóa đúng 1 file `src/training/modal_runner.py`; 3 dòng ` D` của người dùng còn nguyên.
(b) `git diff --name-only <mốc B0> HEAD | grep -E '\.(pt|pth|bin|safetensors|npz|npy|jsonl|mp4|onnx)$'` → 0 dòng; không `git add` gì dưới
`data/`, `checkpoints/`, `_work/`. (c) `find checkpoints data/external -type l` → 0; `fsutil reparsepoint query` cho `checkpoints`,
`checkpoints/vit5_stage1`, `checkpoints/vit5_stage2` → "not a reparse point". (d) Không ghi đè file nào: mọi đích kiểm "chưa có" trước khi ghi
(log trong `_work/_plan13_tmp/`). (e) Không file tracked cũ nào bị sửa trừ: `train.py`, các file đánh dấu §3.9 (`git diff --numstat` cột xóa = 0
cho các file md này), `docs/plans/12-khoi-phuc-du-lieu.md` (+1 dòng, 0 xóa).

**AC1 — Modal gỡ sạch.** `git grep -n -i -E "modal_runner|run_cslr_on_modal|vslt-data-volume|import modal|from modal|modal\.(App|Volume|Image)" -- src scripts backend tests kaggle configs`
→ 0 dòng; `git grep -n -i modal -- frontend/src` → đúng các dòng có ở mốc B0 (Dictionary.jsx), `git diff <mốc> HEAD -- frontend/` rỗng;
`git ls-files src/training/modal_runner.py` → rỗng; `python -c "import src.training"` exit 0; `tests.test_backend_source_guard` OK.

**AC2 — Vocab.** `tests.test_retrain_tools` OK, 0 skip. File sinh: dòng 1 `<blank>`, dòng 2 `<unk>`, kết thúc dòng LF, số token so với 372
(`docs/vsl_gh_dataset.md:19`) — **khác 372 → DỪNG (§7.2), không tự chỉnh**; sha256 bản B2 == bản K2 dùng (bằng hệt byte);
`cslr_best.pt["gloss_vocab_hash"]` == 16 hex đầu sha256(file đã đặt).

**AC3 — Đầu vào tái lập được.** Bảng preflight K2 (B7) và train K2 (B9): mọi digest/đếm == `preregistration.json`; đếm so tham chiếu:
cleaned 7140, Clean10k 6426/714, VSLGHText 240/30, CSLR 3600/300/300 — **khác tham chiếu → DỪNG (§7.2)** (không chạy GPU). K1: 3 CSV + npz trên
Kaggle == manifest inputs (sha256), mọi `video_id` có npz, guard split của `get_vsl_dataloaders` chạy (không tắt `validate_guards`).

**AC4 — Đăng ký trước.** Commit chứa `preregistration.json` là tổ tiên của commit ghim mà log K1 và K2 in ra (`git merge-base --is-ancestor`);
log kernel in đúng commit ghim; file không bị sửa sau commit đó (`git log --format=%h -- reports/retrain_<D>/preregistration.json` = 1 dòng).

**AC5 — Kernel & một lần TEST.** `kaggle kernels status` (thật) = COMPLETE cho K1, K2-preflight, K2-train (bản cuối); log K1 có đúng 1 lần chạy
`evaluate_test.py`; log K2 có đúng 1 dòng `PRIMARY TEST EVALUATION`; không lệnh nào chạy ViT5 trên SENT271–300/S06; kiểm hợp lý §3.6 đạt;
sổ GPU: tổng thời gian phiên K1 + K2-train (từ `env.json`) ≤ 2,5 giờ và "STATE + kế hoạch 13" ≤ 10 (nếu không → đã DỪNG đúng §7.2, không vượt).

**AC6 — Lưu trữ private.** 3 manifest commit: `reports/retrain_<D>/{inputs_tier1,artifacts,vit5}_manifest.json`, mỗi manifest: `is_private`
true từ 2 nguồn, mọi `sha256 == sha256_after_download`, `n_files` == số file staging. (Nếu Q2 xảy ra và người dùng chưa trả lời: manifest vit5 được
phép thiếu; kế hoạch ở trạng thái "chưa đóng — chờ Q2", mọi AC khác vẫn phải đạt.)

**AC7 — Đặt đúng.** Mỗi đích §3.5: không tồn tại trước khi đặt (log), sha256 sau khi đặt == manifest (hoặc == SHA256SUMS kernel đã kiểm nếu Q2).

**AC8 — Hồi quy & test.** Log trong `_work/_plan13_tmp/`:
- (a) Sau B5 (trước khi có artifact): lệnh AC2-06 nguyên văn (`docs/plans/06-viec5-frontend.md:1028`) cho đúng trạng thái 12-progress B9:
  `Ran 518`, chỉ 1 ERROR setUpClass ViT5 + 1 skip `stgcn_best.pt not found`; 29 module còn lại giống hệt mốc theo module.
- (b) Sau B11: lệnh AC2-06 nguyên văn → `Ran 526 tests` … `OK`, 0 failure, 0 error, 0 skip; so theo module với `_work/_plan06_tmp/b9b_ac2_31.log`
  → 31/31 module cùng số ok (script so sánh trong `_work/_plan13_tmp/`, như `_work/_plan12_tmp/ac2_compare.py`).
- (c) Bộ mở rộng: lệnh AC2-06 + `tests.test_retrain_tools tests.test_retrained_artifacts tests.test_check_restored_data` → OK, 0 skip.
- (d) `scripts/check_restored_data.py --spec docs/recovery/expected_local_data.json --out _work/_plan13_tmp/inventory_after13.json` → exit 0,
  `required_failed` [], các mục a4, a5 ×2, a6, `b3_gloss_vocab_canonical` KHÔNG còn `missing`.
- (e) `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py` → exit 0, PASSED, clip `qipedc_W03292N`.
- Test hỏng sau khi đặt (vd. bản dịch rỗng) → DỪNG; cấm sửa/nới/skip test, cấm thay checkpoint bằng file khác cho test qua (T4 kế hoạch 12).

**AC9 — Tài liệu.** Đủ các dòng `[Kế hoạch 13 — artifact mới]` + dòng đính chính rò rỉ ở đúng các file §3.9 (grep đếm theo file, ghi 13-progress);
`git diff --numstat` cột xóa = 0 cho các file đó; không số liệu mới trong md (mọi số mới chỉ trong `reports/retrain_<D>/*.json`); README liệt kê 3
dataset + 3 manifest.

**AC10 — Quy trình.** Mỗi bước 1 commit (`13: B<n> …`); trước commit có detect-changes (lưu `_work/_plan13_tmp/dc_<bước>.txt`, ghi tóm tắt
13-progress); impact trước khi sửa `train.py` (`main`, `parse_args`); HIGH/CRITICAL được đối chiếu bằng grep và ghi lại.

## 6. Rủi ro dữ liệu/ML
- R1 **Rò rỉ CSLR (đã biết):** (i) học mọi câu S06 qua người ký khác → số S06 chỉ là "người ký chưa thấy". Ghi ở §3.9; (ii) là backlog.
- R2 **Tier 1 split mới:** a4 mới dùng `tier1_grouped_*` (theo bản quay) — khác split của a4 cũ ⇒ số Tier 1 mới không so được với
  `docs/phase6_stgcn.md`/`benchmark_results.json`. Test Tier 1 nhỏ (đếm ở B0) ⇒ không diễn giải mạnh. CSV untracked ⇒ lưu trong dataset inputs (B6).
- R3 **Lệch byte Windows ↔ Linux:** `.save()`, script clean và có thể `prepare_canonical_*` ghi chế độ văn bản ⇒ CRLF/LF; so file văn bản
  bằng `lf_sha256`, vocab ghi LF cố định. Nếu `dataset_canonical.json` khác CẢ sau chuẩn hóa (vd. `\r` lọt vào chuỗi khi đọc annotation CRLF ở
  Windows) → preflight bắt, DỪNG, CẦN PLANNER (không tự chọn bản nào).
- R4 **Phiên bản thư viện:** model ViT5 lưu bằng `transformers` mới hơn có thể không nạp ở `.venv` → K2 cài đúng phiên bản local; pip thất bại
  ở preflight → DỪNG (CẦN PLANNER), không nâng cấp `.venv` khi chưa hỏi.
- R5 **Base model trôi:** `VietAI/vit5-base` trên HF có thể đổi revision → ghi snapshot sha ở preflight và train; khác → ghi giới hạn.
- R6 **Không tất định trên GPU:** dù seed 42, cuDNN/AMP làm kết quả khác lần chạy — artifact định danh bằng sha256, không bằng "tái lập bit".
- R7 **Cỡ mẫu:** S06 = 300 mẫu của 1 người ký; ViT5 val 30 câu; Tier 1 test nhỏ ⇒ không kết luận chất lượng từ một lần đo.
- R8 **Nguồn gốc/giấy phép:** QIPEDC (giáo dục/nghiên cứu, không nêu quyền phân phối), VSL-GH (MIT theo `docs/data_registry.md:56`, chưa xác minh lại),
  Parallel-Corpus ("open access for research") ⇒ chỉ dataset PRIVATE; không commit npz/jsonl/model.
- R9 **Test cổng sai đối tượng:** `test_vsl_predictor_smoke` chỉ kiểm a4 tồn tại rồi nạp a2 — kế hoạch KHÔNG sửa test đó; bù bằng test mới thật sự nạp
  a4 (§3.11). Backlog: cân nhắc làm rõ test cũ (việc của planner sau, cần lý do, không phải để pass).
- R10 **Lệch train–realtime CSLR (đã biết, ngoài phạm vi):** train `normalize=True`, `CSLRRecognizer.predict` không chuẩn hóa vai
  (`docs/plans/07-viec6-che-do.md:83-86`) — không đổi ở đây; kế hoạch 07 xử lý.
- R11 **Kế hoạch 07 phụ thuộc artifact:** mọi số/giả định của 07 §2.2 về ViT5/CSLR phải kiểm lại trên artifact mới (cùng công thức (i) nên cấu trúc
  không đổi). Orchestrator báo planner 07 sau khi 13 xong.
- R12 **Repo GitHub không clone được** (riêng tư/nhánh chưa push) → kernel lỗi ngay ở clone (rẻ) → kiểm push ở B0/B5.

## 7. Điểm dừng

### 7.1 CẦN NGƯỜI DÙNG (không chặn; mặc định an toàn)
- **Q1** (§3.8): CSLR (i) hay (ii)? Mặc định (i). Trả lời (ii) → planner lập kế hoạch bổ sung; không đổi các bước đã làm.
- **Q2** (chỉ khi B10 đo ETA upload ViT5 > 3 giờ): (a) để upload chạy nền qua đêm; (b) chỉ lưu stage2 (stage1 bỏ khỏi lưu trữ);
  (c) người dùng tự tạo dataset private từ output kernel qua giao diện Kaggle ("New Dataset → Notebook output") rồi coder kiểm bằng `verify`.
  Mặc định khi chưa trả lời: B11–B12 vẫn làm; AC6-vit5 "chờ"; kế hoạch không đóng.
- **Q3** (xác nhận): đặt artifact mới vào đường dẫn mặc định = thuộc quyết định 09:20, không phải GATE. Mặc định: được phép.

### 7.2 Dừng có điều kiện (coder dừng, ghi 13-progress, báo orchestrator)
1. Ngân sách GPU: `STATE + đã dùng + trần job kế tiếp > 10` giờ, hoặc watchdog cắt job → CẦN NGƯỜI DÙNG.
2. Lệch dữ liệu: vocab ≠ 372; cleaned ≠ 7140 hoặc 6426/714; VSLGHText ≠ 240/30; CSLR ≠ 3600/300/300; digest preflight lệch → CẦN PLANNER.
3. Kiểm hợp lý §3.6 không đạt → CẦN NGƯỜI DÙNG (không thử lại seed/cấu hình khác).
4. Test hỏng sau khi đặt artifact (AC8-b) → DỪNG; không sửa test.
5. Cần sửa file ngoài danh sách AC0, cần xóa thêm file/thư mục, slug Kaggle đã tồn tại (exit 5), dataset không xác minh được private (exit 4) → DỪNG.
6. Pip/transformers không cài được đúng phiên bản trên Kaggle (R4) → CẦN PLANNER.

### 7.3 Không chạm điểm dừng bắt buộc khác
Không đổi model mặc định Cấp 2 (a2 giữ nguyên; a4 chỉ là fallback khi thiếu a2); không cần dữ liệu người dùng; không đụng thay đổi chưa commit
của người dùng; xóa duy nhất `src/training/modal_runner.py` (tracked, hoàn tác bằng git, theo quyết định 09:20); không xóa dữ liệu/checkpoint/báo cáo cũ.
