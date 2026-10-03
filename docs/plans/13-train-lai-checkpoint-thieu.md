# Kế hoạch 13 — Train lại checkpoint thiếu trên Kaggle (stgcn_best, CSLR + vocab, ViT5) + gỡ Modal

> **Lần sửa 3 — XONG (planner, 2026-10-03, nhỏ).** §0C ở `docs/plans/13-lan-sua-3.md`: B12 tách B12a/B12b, bỏ dòng đính chính rò rỉ (chuyển kế hoạch 14), bàn giao test_eval.json cho 14 B7, AC0(a) thêm kế hoạch 14. Không đổi B9a–B9f, §0B.3, preregistration.
>
> **Lần sửa 2 — XONG (planner, 2026-10-03).** Sau K2 v3 ERROR (smoke test CSLR giải mã toàn blank; checkpoint ViT5 mất vì kernel chỉ chép output khi mọi
> job thành công). Chi tiết, bằng chứng, quy tắc quyết định đăng ký trước, thay đổi tiêu chí + lý do: **§0B**. Chỗ sửa trong thân đánh dấu **[LS2]**.
> Coder làm tiếp từ **B9a** (§0B.9); KHÔNG đẩy lại K2 trước khi B9b ra quyết định theo §0B.3.

> **Lần sửa 1 — XONG (planner, 2026-10-02).** Áp quyết định người dùng Q1 = (ii) (`docs/STATE.md:165-173`, 2026-10-02 10:05).
> Không có câu hỏi mới chặn việc. Chi tiết + lý do mọi thay đổi tiêu chí: §0. Chỗ sửa trong thân kế hoạch đánh dấu **[LS1]**.
> B0–B2 đã làm (13-progress) giữ nguyên giá trị; vocab 372 của B2 KHÔNG còn là vocab mặc định (chỉ dùng cho K3 tùy chọn — §0.4, §0.7).
> Coder làm tiếp theo thứ tự §4 bắt đầu từ B2a (mới), KHÔNG từ B3.

> **CẦN NGƯỜI DÙNG (KHÔNG chặn việc nào; có mặc định an toàn — chi tiết §7.1):**
> - Q1. **[LS1] ĐÃ TRẢ LỜI (ii)** — 2026-10-02 10:05 (`docs/STATE.md:165-173`). Áp dụng ở §0. Không hỏi lại.
> - Q2 (chỉ hỏi nếu xảy ra): upload ViT5 (kích thước đo ở B10) từ máy local quá chậm (ETA > 3 giờ) → chọn cách lưu trữ. Mặc định khi chưa
>   trả lời: vẫn đặt ViT5 vào máy để chạy test; lưu trữ ViT5 = "đang chờ", kế hoạch chưa đóng.
> - Q3 (xác nhận): đặt checkpoint MỚI vào đúng đường dẫn mặc định (`checkpoints/stgcn_best.pt`, `cslr_best.pt`, `vit5_stage*/`) được hiểu
>   là thuộc quyết định 2026-10-02 09:20 ("không có thì train lại"), KHÔNG phải GATE đổi model mặc định (không model nào đang có bị thay;
>   model mặc định Cấp 2 `stgcn_tier2_indomain.pt` không đổi). **Mặc định: được phép.** Nếu người dùng phủ nhận → dừng trước B11.
>   **[LS1]** Checkpoint đặt vào đường dẫn mặc định là bản (ii) (split câu); bản (i) (K3, tùy chọn) KHÔNG bao giờ đặt vào đường dẫn mặc định.
> - **[LS2] Q4 (thông báo, KHÔNG chặn; mặc định = §0B.3):** nếu B9b ra "đường P", K2 v4 chạy CSLR với `--skip-smoke-test` qua file bổ sung đăng ký
>   công khai (smoke gốc vẫn chạy ở CPU, kết quả ghi lại; kiểm §3.6 giữ nguyên). Người dùng phủ nhận trước B9e → dừng trước khi đẩy v4.
> - **[LS2]** B9b có thể sinh điểm dừng CẦN NGƯỜI DÙNG (R2-FAIL: pipeline không overfit được 8 mẫu) — chỉ khi xảy ra (§0B.11).
>
> Trạng thái: XONG (planner, 2026-10-02; Lần sửa 1 cùng ngày; Lần sửa 2 2026-10-03). Tệp tạm: `_work/_plan13_tmp/`. Tiến độ coder: `docs/plans/13-progress.md`.

## 0B. Lần sửa 2 (2026-10-03) — K2 v3 ERROR (smoke test CSLR), lưu output từng job, AC0 theo commit, cơ chế bản đẩy

> Chỗ sửa trong thân kế hoạch đánh dấu **[LS2]**; §0B ghi đè mọi chỗ mâu thuẫn ở §3–§7. Mọi số dưới đây CHÉP từ file có đường dẫn
> (log/JSON đã tải), không phải kỳ vọng. Coder làm tiếp từ **B9a** (§0B.9), KHÔNG đẩy lại K2 trước khi B9b ra quyết định.

### 0B.1 Sự kiện (bằng chứng: `_work/_plan13_tmp/k2_train_v3/`)
- `phmvnsm33/vsl-retrain-cslr-vit5` version 3 (MODE=train, ghim `28a126e`): `k2/env.json` `"error": "KernelError: failed jobs: ['cslr']"`, `exit` 1,
  `total_minutes` 12.14, `n_gpu` 2 (Tesla T4 ×2), torch 2.10.0+cu128. Preflight trong lần train: 44/44 MATCH, `LEAK CHECK OK (k2 kernel): total=0`
  (`vsl-retrain-cslr-vit5.log` dòng 46–91). `BACKBONE checkpoints/stgcn_best.pt sha256 2204becd… == k1_outputs.json` ở t=164.37 s, TRƯỚC lệnh
  `train_cslr.py` ở t=164.63 s (dòng 92–93).
- `jobs.cslr`: 18:52:02Z → 18:52:13Z, **0.18 phút**, exit 1. `k2/logs/cslr.log`: dòng 3 `LEAK CHECK OK (cslr): n_train_samples=2880, n_val_samples=30, …,
  n_vocab_tokens=322`; dòng 9–18 loss smoke 78.0081 → 77.8921 → 63.9242 → 30.9929 → 4.4809 → 4.3370 → 3.1192 → 2.0082 → 2.3009 → 2.3260; dòng 20 hai mẫu
  giải mã `SENT001_S02_R02_F`, `SENT001_S02_R01_F` đều `<BLANK_ONLY>`; dòng 21 `[SMOKE TEST FAILED] Loss decreased: True, Non-empty output: False`;
  dòng 27 `RuntimeError: Smoke test failed!` (`train_cslr.py:402`).
- `jobs.vit5_stage1` 8.14 phút exit 0 (`vit5_stage1.log`: best val loss ở epoch 2, lưu vào `/tmp/vslt/checkpoints/vit5_stage1/best_model`);
  `jobs.vit5_stage2` 1.28 phút exit 0 (`vit5_stage2.log:20` best epoch 3, val loss 0.6625, lưu vào `/tmp/vslt/checkpoints/vit5_stage2/best_model`).
  Output kernel chỉ có `env.json, preflight.json, SHA256SUMS, gloss_vocab_canonical.txt, translation_corpus_validation.json, logs/*` ⇒ checkpoint ViT5 MẤT.
- **Nguyên nhân mất ViT5 (mã):** `train()` của K2 chỉ chép checkpoint/history vào `/kaggle/working/k2/` SAU KHI mọi job xong và không job nào lỗi
  (`kaggle/vsl-retrain-cslr-vit5/retrain_cslr_vit5_kernel.py:630-650`; `raise KernelError(f"failed jobs: …")` ở `:631` đứng trước mọi `copy_new`).
- **Đính chính STATE** (`docs/STATE.md:17-18` ghi "smoke chạy TRƯỚC khi nạp backbone"): KHÔNG đúng. Smoke chạy trước dòng `[MODEL] Transferred` của
  `train_cslr` (`:496-502`), nhưng bản thân `run_smoke_test` nạp backbone nếu file có (`train_cslr.py:299-300`, `freeze=False`), đường dẫn =
  `cfg["pretrained_backbone"]` = `<repo>/checkpoints/stgcn_best.pt` (`:846`) = đúng chỗ kernel vừa đặt (`k2.backbone.path`). Smoke KHÔNG in gì về việc
  nạp (giá trị trả về bị bỏ) ⇒ log v3 không cho biết bao nhiêu tham số được chuyển (đo ở B9b-D4).

### 0B.2 Nguyên nhân smoke FAIL — điều đã chứng minh và điều chưa
**Sự thật (mã + log):**
- S1. Smoke = 8 mẫu đầu `split="train"` (`Subset(range(8))`, `:278`), bs 4, `shuffle=True` ⇒ 2 bước AdamW/epoch × 10 epoch = **20 bước** lr 1e-3, AMP trên
  CUDA (`:281-331`). Bản huấn luyện thật: 2880 mẫu, bs 8 ⇒ 360 bước/epoch.
- S2. Loss in ra là loss ở chế độ `train()` (dropout 0.1, BatchNorm theo thống kê lô). Giải mã ở `evaluate_cslr` → `model.eval()` (`:153`) ⇒ BatchNorm
  dùng running stats. Loss ở chế độ eval có tính (`eval_res["loss"]`) nhưng KHÔNG in (`:342-344`) ⇒ log không cho biết loss eval có giảm không.
- S3. Tiêu chí: `has_predictions = total_hyp_words > 0` trên cả 8 mẫu (`:347`) ⇒ FAIL nghĩa là ở chế độ eval, mọi khung của cả 8 mẫu đều argmax = blank.
- S4. `select_vslgh_samples` giữ thứ tự gốc (`src/data/sentence_split.py:216`); 2 mẫu giải mã là SENT001 (∈ Tr) ⇒ nhiều khả năng 8 mẫu smoke TRÙNG với
  8 mẫu của công thức cũ (không split câu). CHƯA kiểm — B9b-D0.
- S5. Không có bằng chứng trong repo rằng smoke từng PASS ở công thức cũ: grep `SMOKE TEST PASSED|Smoke Epoch|BLANK_ONLY` trong `reports/ docs/ experiments/`
  → chỉ có STATE (v3). ⇒ "smoke vốn chạy được, split câu làm hỏng" là CHƯA chứng minh.
- S6. Khác biệt duy nhất giữa smoke v3 và smoke công thức cũ (khi S4 đúng): vocab 322 vs 372 (số lớp đầu ra ⇒ khởi tạo lớp cuối và thứ tự rút RNG khác),
  backbone K1 mới (sha `2204becd…`) thay backbone cũ (đã mất), môi trường (T4, torch 2.10, AMP).

**Giả thuyết (chưa chứng minh; B9b đo, không giả thuyết nào được ghi như sự thật):**
- H1 "Bình nguyên blank" của CTC: sau 20 bước model mới học xác suất blank cao ở mọi khung (loss giảm nhanh 78 → ~2–4/token với `reduction="mean"`),
  chưa tới pha phát nhãn; tiêu chí "không rỗng sau 20 bước" nhạy với khởi tạo/backbone. Dấu hiệu phù hợp: loss tăng lại ở epoch 9–10 (S1, log dòng 16–18).
- H2 Lệch BatchNorm train/eval: running stats của `data_bn`/`blocks.*` đến từ K1 (dữ liệu QIPEDC Tier 1, phân bố khác VSL-GH) và chỉ được cập nhật 20 lần
  (momentum mặc định) ⇒ đầu ra ở `eval()` khác hẳn `train()`.
- H3 8 mẫu khác công thức cũ — nhiều khả năng SAI theo S4.
- H4 Backbone: K1 không chuyển được tham số (lệch shape ⇒ 0 tham số) hoặc K1 yếu. (Smoke `freeze=False` nên vẫn học được.)
- H5 Số học GPU (AMP fp16, CTC backward CUDA không tất định) — smoke CPU tắt autocast.
- H6 Vocab 322 vs 372 (chỉ đổi lớp cuối/RNG).

### 0B.3 Cách xử lý smoke — quy tắc quyết định ĐĂNG KÝ TRƯỚC (viết trước khi có kết quả B9b)
**Phân loại:** smoke test là **kiểm hạ tầng dừng-sớm** (fail-fast), KHÔNG phải tiêu chí chất lượng: chỉ dùng 8 mẫu TRAIN, không chạm val/test, không chọn
epoch/hyperparameter, kết quả không đi vào số liệu báo cáo nào. Nó thuộc công thức đã đăng ký ("`train_cslr.py` (đủ tham số mặc định, có smoke test)" — §3.4e;
`jobs.k2.cslr.train.argv` của preregistration không có `--skip-smoke-test`) ⇒ đổi nó = sửa đăng ký, phải làm CÔNG KHAI bằng file bổ sung (amendment), không
lặng lẽ. **Không đổi mã `run_smoke_test`** (tiêu chí gốc giữ nguyên văn và vẫn được chạy, kết quả ghi lại dù PASS hay FAIL).

**Vì sao không phải "đổi tiêu chí GATE sau khi thấy kết quả" (autopilot mục 4):** (1) không có GATE/đổi model mặc định nào ở đây; (2) kết quả đã thấy (smoke v3)
không phải số đánh giá; không số báo cáo nào phụ thuộc smoke; (3) các kiểm bảo vệ KẾT QUẢ giữ nguyên, không nới: LEAK CHECK (`train_cslr.py:384-396`, chạy cả khi
bỏ smoke), kiểm căn chỉnh CTC mỗi lô (`:600-609`, raise), kiểm hợp lý §3.6 (loss hữu hạn, best epoch ≥ 1, `best_val_wer < 100` — model chỉ ra blank cho WER 100
⇒ bị chặn, DỪNG, CẦN NGƯỜI DÙNG), luật chọn epoch theo val, đánh giá test một lần §3.12; (4) thêm một kiểm CHẶT HƠN (chuyển backbone đủ, §0B.3-R0);
(5) quy tắc dưới được viết trước khi chạy chẩn đoán, có trần cố định, chạy một lần, không lặp; FAIL → DỪNG.

**Chẩn đoán B9b (local, CPU, 0 GPU; không ghi ngoài `_work/` trước khi commit JSON):** runner `_work/_plan13_tmp/ls2/smoke_diag.py` gọi đúng
`src.training.train_cslr.run_smoke_test` (không sửa) cho D1–D3, và một bản sao có đo đạc cho D4/D5. Đầu vào (kiểm sha256 TRƯỚC khi chạy, lệch → dừng):
`data/external/vsl_gh/dataset_canonical.json` (lf_sha256 `d53ab701…` = preregistration), `keypoints_frontal` (dir_digest `59642925…`),
`_work/_plan13_tmp/vocab_train/gloss_vocab_canonical.txt` (sha256 `c0af13db…`, 322), `_work/_plan13_tmp/vocab_e02ed14/gloss_vocab_canonical.txt`
(sha256 `dd7bc3da…`, 372), `_work/_plan13_tmp/k1/k1/stgcn_best.pt` (sha256 `2204becd…bac2`), `configs/vslgh_sentence_split_v1.json`. KHÔNG đặt gì vào
`checkpoints/` hay `data/external/vsl_gh/gloss_vocab_canonical.txt` (B11 mới đặt). `device=cpu`, mỗi lần chạy timeout 30 phút tường.
- **D0** (không train): `sample_id` của `Subset(range(8))` train + mẫu val `[0]` với split câu và với `sentence_split=None`; ghi cả hai danh sách + `identical`.
- **D1** = smoke NGUYÊN BẢN: `run_smoke_test(data_root, vocab 322, K1, cpu, sentence_split=configs/vslgh_sentence_split_v1.json)` → stdout + bool.
- **D2** (giải thích): như D1 nhưng `sentence_split=None` + vocab 372 (công thức cũ, backbone K1).
- **D3** (giải thích): như D1 nhưng đường dẫn backbone không tồn tại (trong `_work/`) ⇒ không nạp backbone.
- **D4/D5** (một lần chạy, bản sao có đo đạc của vòng lặp smoke, cùng D1 setting): (i) `transfer_info` trả về từ `load_pretrained_spatial_backbone`
  (`transferred_keys_count`, `transferred_params`, danh sách skip, số khóa lệch shape) + số khóa `data_bn.*`/`blocks.*` của model CSLR;
  (ii) **kiểm trung thực:** loss epoch 1–10 làm tròn 4 số == 10 số D1 in ra (khác → D4/D5 vô hiệu, DỪNG, CẦN PLANNER);
  (iii) ở epoch 10 và epoch 60: loss CTC chế độ eval trên 8 mẫu, `total_hyp_words` chế độ eval, `total_hyp_words` khi CHỈ các lớp BatchNorm ở chế độ train
  (trên bản `deepcopy`, `torch.no_grad()` — không làm bẩn model chính), tỉ lệ khung argmax = blank, WER mã hóa vocab trên 8 mẫu (`evaluate_cslr`);
  (iv) tiếp tục cùng optimizer, cùng lr, KHÔNG đổi gì, tới **epoch 60** (= 120 bước; trần chọn theo chi phí — 6× ngân sách smoke gốc, vẫn < 4% số bước
  một epoch-1 của stage 1 thật — chọn TRƯỚC khi chạy, không đổi sau).
- Ghi `_work/_plan13_tmp/ls2/smoke_diag.json` (`generated_by{command, git_commit, code_dirty, torch, python, device}`, `inputs` sha256, D0–D5, `decision`)
  + log; commit bản chép ở `reports/retrain_2026-10-02/k2_ls2_smoke_diag/`.

**Quy tắc quyết định (chỉ dùng D0 [thông tin], D1, D4-i, D4-ii, D5; D2/D3/D4-iii là giải thích, KHÔNG là đầu vào quyết định):**
- **R0 (lỗi thật — chặn):** D4-i có khóa lệch shape, hoặc `transferred_params == 0`, hoặc số khóa chuyển ≠ số khóa `data_bn.*`/`blocks.*` có ở CẢ hai model
  ⇒ CSLR thật cũng sẽ train gần như từ đầu (kernel hiện chỉ kiểm có dòng `[MODEL] Transferred`, không kiểm số) ⇒ **DỪNG, CẦN PLANNER** (không tự sửa kiến trúc/K1).
- **R1 (D1 PASS trên CPU):** lỗi gắn với GPU/AMP (H5) ⇒ đi đường **P** với bằng chứng "smoke nguyên bản PASS trên CPU, cùng mã/dữ liệu/backbone/vocab".
- **R2 (D1 FAIL trên CPU):** tiêu chí gốc thất bại với công thức đăng ký, độc lập GPU. Xét D5 ở **epoch 60** (CHỈ epoch 60, không "epoch nào đó"):
  PASS nếu loss hữu hạn, loss epoch 60 < loss epoch 1, `total_hyp_words` (eval) > 0 VÀ WER 8 mẫu < 100 ⇒ đường **P** với bằng chứng "pipeline học và phát
  nhãn được trên 8 mẫu sau 120 bước; 20 bước không đủ". KHÔNG PASS, hoặc hết 30 phút trước epoch 60 ⇒ **DỪNG, CẦN NGƯỜI DÙNG** (pipeline không overfit được
  8 mẫu — không đẩy K2; lựa chọn đưa người dùng: điều tra sâu hơn / đổi công thức CSLR = kế hoạch mới).
- **Đường P (duy nhất được phép đẩy K2 v4):** commit `reports/retrain_2026-10-02/preregistration_amendment_ls2.json` (B9d) đổi ĐÚNG một khóa
  `jobs.k2.cslr.train.argv` := argv đăng ký + `["--skip-smoke-test"]`; kèm `reason_ref "docs/plans/13 §0B.3"`, `decision_rule` (R1|R2), đường dẫn + sha256 của
  `smoke_diag.json` và của `k2_train_v3/k2/logs/cslr.log`, `expected_backbone_transfer{transferred_keys_count, transferred_params}` (từ D4-i), danh sách
  "không đổi" (§3.6, luật chọn epoch, giao thức §3.12, LEAK CHECK, watchdog, trần GPU). Kernel kiểm số `[MODEL] Transferred N` == `transferred_params` (R0 ở Kaggle).
- Không có đường nào khác: không chạy lại GPU với cấu hình y hệt để "thử vận may"; không tăng số epoch smoke trong mã; không đổi seed; không đổi backbone.

### 0B.4 Lưu output từng job (sửa kernel K2)
- **Yêu cầu:** ngay khi MỖI job (`cslr`, `vit5_stage1`, `vit5_stage2`) kết thúc — exit 0, exit ≠ 0 hay watchdog — worker chép (bằng `copy_new`, không ghi đè)
  mọi file của job đó ĐANG CÓ vào `/kaggle/working/k2/` theo đúng bố cục §4 B9 hiện dùng: `cslr_best.pt`, `cslr_stage1_best.pt` (nếu có),
  `reports/{cslr_used_ids, cslr_train_summary, cslr_training_history}.json`; `vit5_stage1/best_model/*`, `reports/vit5_stage1_{history,used_ids}.json`;
  `vit5_stage2/best_model/*`, `reports/vit5_stage2_{history,used_ids}.json`. Ghi `env.json.jobs.<job>.saved` = danh sách đường dẫn tương đối đã chép,
  `missing` = danh sách dự kiến mà không có. Kiểm log + sanity của TỪNG job (`check_vit5_log`, `sanity_vit5`, `check_cslr_log`, `sanity_cslr`) chạy cho job
  đã exit 0, độc lập job khác; ghi `sanity_<job>.json` + `sanity.json` gộp. Job nào lỗi ⇒ vẫn `KernelError` cuối (exit ≠ 0) — không che lỗi.
- Không đổi: `SHA256SUMS` viết trong `finally` (đã phủ mọi file dưới `WORK`); không xóa/symlink; không chép gì ngoài `WORK`.
- **ViT5 có chạy lại không:** CÓ, trong cùng K2 v4 (GPU1 song song CSLR trên GPU0). Lý do: checkpoint v3 mất do lỗi hạ tầng (thiết kế output) ⇒ được chạy lại
  1 lần, cùng cấu hình (§3.6). Chạy song song trong cùng phiên ⇒ phiên dài bằng job dài nhất (CSLR), ViT5 gần như không thêm GPU-phút. **Không tách job:**
  tách = thêm một phiên (thêm khởi động/clone/pip/HF ~3 phút) mà không lợi gì khi đã lưu từng job. **Chống chọn lọc:** history ViT5 v3 chỉ là log lịch sử
  (commit ở B9a), không dùng làm gì; ViT5 dùng cho B10–B11b = bản ĐẦU TIÊN được lưu + kiểm (v4), bất kể kết quả các lần sau. Nếu v4 CSLR lỗi mà ViT5 v4
  lưu đủ ⇒ giữ ViT5 v4; CSLR → §0B.11 điểm dừng.
- Ghi chú lượt chạy: CSLR v4 = lần chạy lại duy nhất được phép của job CSLR (ngoại lệ trước khi xong epoch đầu, §3.6); ViT5 v4 = lần chạy lại duy nhất
  của ViT5. v5 của bất kỳ job nào ⇒ CẦN PLANNER (lỗi hạ tầng) hoặc CẦN NGƯỜI DÙNG (kiểm hợp lý §3.6).

### 0B.5 AC0 theo commit của kế hoạch 13 (kế hoạch 11 chạy song song trên cùng nhánh)
- Tập commit của 13: `git log --format='%H %s' <mốc B0 của 13>..HEAD | grep -E '^[0-9a-f]{40} (WIP )?13:'` → `_work/_plan13_tmp/ac0_commits13.txt`
  (lọc theo DÒNG TIÊU ĐỀ, không dùng `--grep` vì nó khớp cả thân commit). Tập file của 13 = hợp của
  `git diff-tree --no-commit-id --name-status -r -M <c>` với mọi `<c>` trong tập đó → `_work/_plan13_tmp/ac0_files13.txt`.
- AC0(b) và (e) áp trên tập file của 13 (thay cho `git diff <mốc B0> HEAD`). AC0(a) (`git status --porcelain` so mốc B0): dòng mới không thuộc danh sách AC0
  của 13 thì phải nằm trong danh sách file của kế hoạch đang chạy song song (`docs/plans/11-progress.md` / AC0 của 11) — in ra từng dòng + lý do; còn lại → FAIL.
- Kiểm bổ sung (chặt hơn, không nới): không commit nào NGOÀI tập 13 (trừ commit `state:` của orchestrator) sửa file chỉ thuộc 13 (`kaggle/vsl-retrain-*`,
  `reports/retrain_2026-10-02/`, `scripts/retrain_*`, `scripts/eval_sentsplit.py`, `src/data/sentence_split.py`, `configs/vslgh_sentence_split_v1.json`,
  `tests/test_retrain_tools.py`, `tests/test_sentence_split_guard.py`): `git log --format='%h %s' <mốc>..HEAD -- <các đường dẫn>` chỉ ra commit `13:`/`WIP 13:`/`state:`.

### 0B.6 Hai cơ chế coder tự đặt — XÁC NHẬN cả hai (có điều kiện ghi lại)
- (a) File repo K2 giữ `PIN_COMMIT = None`, `MODE = "preflight"`, metadata `enable_gpu: false`, `kernel_sources: []` (khóa bởi test có sẵn
  `tests/test_retrain_tools.py:2163-2164,2170-2171`); bản đẩy trong `_work/` = file ở commit ghim thay đúng 2 dòng (`MODE`, `PIN_COMMIT`) + metadata đẩy
  bật GPU + `kernel_sources` K1. **Giữ.** Mục đích của "MODE đổi bằng commit" (§3.4e) là truy vết: mã chạy được xác định hoàn toàn bởi (commit ghim, MODE),
  kernel tự kiểm phần còn lại byte-bằng (`same_as_pinned`), MODE ghi ở `env.json`/`preflight.json`. Đổi sang commit MODE vào repo sẽ làm đỏ 2 test có sẵn
  ⇒ không được. **Điều kiện [LS2]:** từ v4, bản ghi đẩy phải nằm trong repo, không chỉ trong 13-progress/`_work/`: commit
  `reports/retrain_2026-10-02/k2/push_record.json` (sinh bằng code: sha256 file đẩy + metadata đẩy, diff đúng 2 dòng so với `git show <ghim>:…`, giá trị MODE,
  `enable_gpu`, `kernel_sources`, thời điểm đẩy, version Kaggle). Chữ §3.4e được sửa cho khớp (dòng [LS2] ở §3.4e).
- (b) `same_as_pinned` của K2 bỏ qua riêng GIÁ TRỊ dòng `MODE = "<x>"  # …` khi `<x>` ∈ `MODES` = (`preflight`, `train`) (`retrain_cslr_vit5_kernel.py:47-51,93-100`).
  **Giữ:** mọi dòng khác (kể cả chú thích sau MODE) vẫn so; `repro_i` vẫn bị từ chối (test `test_k2_unknown_mode_refused`); K1 không đổi. Không cần sửa/nới
  test nào. K3 (B14) cần MODE mới ⇒ commit mã mới + test mới khi tới đó (không mở rộng `MODES` ở lần sửa này).

### 0B.7 Ngân sách GPU (cập nhật §3.7) — số từ `env.json`; ước lượng ghi rõ "chưa xác minh"
| Job | Phiên (phút) | Nguồn |
|---|---|---|
| K1 v1 | 1.58 | `reports/retrain_2026-10-02/k1/env.json` |
| K2 v3 (ERROR) | 12.14 | `_work/_plan13_tmp/k2_train_v3/k2/env.json` |
| **Đã dùng kế hoạch 13** | **13.72 (≈ 0.23 h)** | trần tổng 2.5 h |
| K2 v4 (kế tiếp) | ước lượng ≤ 1,0 h (chưa xác minh: CSLR 2880 mẫu ∥ ViT5 ~9.4 phút đo ở v3 + khởi động ~2.7 phút đo ở v3) | trần 1.75 h (watchdog 105') |
- Tổng nếu v4 chạm trần: 0.23 + 1.75 = 1.98 ≤ 2.5 → lọt trần kế hoạch. K3 tùy chọn: 1.98 + 1.75 = 3.73 ≤ 4.25.
- Cổng tuần (trước MỖI job GPU, thay số ở §3.7): `max(GPU tuần trong STATE "Tài nguyên", "GPU used" của kaggle quota đọc NGAY trước khi đẩy) + đã dùng kế hoạch
  13 (sổ GPU) + trần job` ≤ 10 → lọt; không → DỪNG, CẦN NGƯỜI DÙNG (§7.2-1). Số đã biết: kaggle quota 4.18 h lúc 18:42Z 2/10 (trước v3; làm mới
  2026-10-03T00:00Z) — số sau v3 phải ĐỌC lại bằng `kaggle quota`, không cộng tay.

### 0B.8 K1 sanity val top-1 23.08 — ảnh hưởng tới CSLR
- 23.08 = 3/13: val Tier 1 có 13 dòng (`preregistration.json` `tier1_grouped_val_csv.n_rows` 13, 12 lớp) ⇒ số này gần như không mang thông tin về chất
  lượng backbone (một mẫu đổi = ±7.7 điểm). Kiểm §3.6 cho K1 (> mức ngẫu nhiên 2.0) đã đạt; KHÔNG thêm ngưỡng chất lượng mới, KHÔNG train lại K1, KHÔNG
  bỏ backbone (backbone K1 là công thức đăng ký; preregistration `backbone.rule`).
- Ảnh hưởng có thể (ghi giới hạn, không hành động): stage 1 CSLR đóng băng backbone 10 epoch ⇒ đặc trưng từ backbone yếu có thể làm CSLR kém hơn công thức
  cũ; số CSLR mới chỉ đúng "với backbone K1 này". D3 (không backbone) ở B9b là giải thích, KHÔNG dùng để chọn có/không dùng backbone.
- Ghi vào `limitations` của `test_eval.json` (B11b) và 13-progress: "backbone K1 val top-1 đo trên 13 clip — không đủ để đánh giá backbone".

### 0B.9 Bước mới (thay B9 cũ; mỗi bước 1 commit `13: B9x …`, detect-changes trước commit, impact trước khi sửa symbol có sẵn)
| Bước | Việc | Ước lượng | Phụ thuộc |
|---|---|---|---|
| **B9a** | Ghi nhận v3: chép `_work/_plan13_tmp/k2_train_v3/` (env.json, preflight.json, SHA256SUMS, translation_corpus_validation.json, logs/*, log stdout kernel) vào `reports/retrain_2026-10-02/k2_train_v3/` (`copy_new`, kiểm SHA256SUMS; `git add -f` cho *.log; KHÔNG chép `gloss_vocab_canonical.txt` — sha256 đã trong SHA256SUMS); sổ GPU +12.14 phút; 13-progress mục "B9 phần 2 (v3 ERROR)". Không sửa mã. | 0,5 h | — |
| **B9b** | Chẩn đoán smoke local CPU theo §0B.3 (D0–D5), quyết định theo R0/R1/R2, commit `reports/retrain_2026-10-02/k2_ls2_smoke_diag/{smoke_diag.json, smoke_diag.log}`. Nếu R0 hoặc R2-FAIL → DỪNG (ghi 13-progress, báo orchestrator), KHÔNG làm B9c–B9f. | 1,5 h (CPU ≤ 4 × 30 phút) | B9a |
| **B9c** | Kernel K2: (1) lưu từng job §0B.4; (2) đọc amendment (§0B.3 đường P): file `reports/retrain_<D>/preregistration_amendment_ls2.json` nếu có thì phải đúng 1 commit, commit preregistration là tổ tiên của nó và nó là tổ tiên ghim; chỉ chấp nhận khóa trong danh sách trắng `{"jobs.k2.cslr.train.argv": thêm đúng ["--skip-smoke-test"]}`, khác → `KernelError`; in `AMENDMENT ls2 <commit> applied: …`; không có file → hành vi cũ; (3) `check_backbone_transfer(text, expected)` — mới, đúng 1 dòng `[MODEL] Transferred N` với N == `expected_backbone_transfer.transferred_params`; (4) ghi `push_record` khóa vào env (MODE, metadata). Test MỚI (đỏ trước): lưu ViT5 khi CSLR lỗi (run giả), amendment hợp lệ/khóa lạ/argv lạ/≠1 commit, transfer N lệch/thiếu. Test có sẵn GIỮ NGUYÊN (`git diff <HEAD trước B9c> -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0); test có sẵn xung đột thiết kế → DỪNG, CẦN PLANNER. impact: `train`, `main`, `check_cslr_log` (nếu chạm), `worker` (hàm lồng — đối chiếu grep). | 2 h | B9a (song song B9b được) |
| **B9d** | `scripts/retrain_amendment.py` (mới): sinh amendment từ `smoke_diag.json` + preregistration (từ chối ghi đè → 2; `code_dirty` → 2; quyết định trong diag ≠ R1/R2-PASS → 3; ghi `generated_by`); test (đỏ trước); sinh + commit amendment. Chỉ chạy khi B9b ra đường P. | 1 h | B9b, B9c |
| **B9e** | Commit ghim v4 (mã B9c + amendment là tổ tiên), push, `git ls-remote` == ghim; cổng ngân sách §0B.7 (đọc `kaggle quota` thật); bản đẩy `_work/_plan13_tmp/k2_push_train_v4/` theo §0B.6(a) (2 dòng; `same_as_pinned` + `check_pin` local OK); `kernels push`; theo dõi `kaggle kernels status` thật (≥ 5 phút/lần). Commit `push_record.json`. | 0,5 h + chờ | B9d |
| **B9f** | COMPLETE/ERROR thật → `kaggle kernels output … -p _work/_plan13_tmp/k2` → kiểm như §4 B9 [LS1] + [LS2]: SHA256SUMS; `env.mode` "train", `commit` == ghim v4; log có `AMENDMENT ls2`; argv CSLR trong log == argv amendment; 0 dòng `Smoke Epoch` (đã bỏ smoke theo amendment); `[MODEL] Transferred N` == amendment; LEAK CHECK OK trước epoch đầu; 0 `PRIMARY TEST EVALUATION`; 1 `TEST DEFERRED`; §3.6 từng job; vocab == B2c; HF sha preflight == train; `jobs.*.saved` đủ. Commit `reports/retrain_2026-10-02/k2/` (JSON + log, không .pt/model) + 3 `*_used_ids.json`; sổ GPU. CSLR lỗi mà ViT5 đủ → giữ ViT5 (§0B.4), DỪNG phần CSLR, báo. | 0,75 h + chờ | B9e |

B10 trở đi giữ nguyên (phụ thuộc B9f).

### 0B.10 Thay đổi tiêu chí chấp nhận (planner đổi, lý do)
| Tiêu chí | Cũ | Mới | Lý do |
|---|---|---|---|
| AC0 (a)(b)(e) | so `git diff`/porcelain từ mốc B0 | trên tập commit tiêu đề `^(WIP )?13:` (§0B.5) + kiểm ngược "không commit lạ sửa file của 13"; danh sách thêm: `reports/retrain_2026-10-02/{k2_train_v3, k2_ls2_smoke_diag}/`, `preregistration_amendment_ls2.json`, `k2/push_record.json`, `scripts/retrain_amendment.py`, kernel K2 (đã có) | kế hoạch 11 chạy song song cùng nhánh; không nới: thêm kiểm ngược |
| AC4 | preregistration 1 commit, tổ tiên ghim | + amendment đúng 1 commit; preregistration ⊂ amendment ⊂ ghim v4 (`merge-base --is-ancestor`); amendment chỉ đổi khóa danh sách trắng; `smoke_diag.json` commit TRƯỚC amendment | sửa đăng ký phải công khai, có thứ tự |
| AC5 | K2-train bản cuối COMPLETE; log … | bản cuối = v4; v3 ERROR ghi nhận (B9a); log v4 có `AMENDMENT ls2`, 0 `Smoke Epoch`, `[MODEL] Transferred N` == amendment; GPU K1 + v3 + v4 ≤ 2,5 h | §0B.3, §0B.7 |
| **AC14 (mới)** | — | (a) `smoke_diag.json` có D0, D1 (stdout + bool), D4-i, kiểm trung thực D4-ii = true, D5 epoch 10/60, `decision` ∈ {R0, R1, R2-PASS, R2-FAIL} khớp quy tắc §0B.3 khi reviewer tính lại từ chính JSON; (b) đường P chỉ khi decision ∈ {R1, R2-PASS}; (c) test lưu-từng-job, amendment, transfer xanh; (d) output v4 có `vit5_stage{1,2}/best_model/*` và `env.jobs.*.saved` đầy đủ | §0B.3–0B.4 |
| §3.4e "MODE đổi bằng commit" | — | MODE file repo = preflight (khóa test); MODE lần chạy = giá trị bản đẩy ∈ MODES, ghi `env.json` + `push_record.json` | §0B.6 |
| §3.6 chạy lại | tối đa 1 lần/job | v4 = lần chạy lại duy nhất của CSLR và ViT5; v5 → CẦN PLANNER / CẦN NGƯỜI DÙNG | §0B.4 |

Không tiêu chí nào bị hạ: tiêu chí smoke gốc không bị sửa (vẫn chạy ở CPU, kết quả ghi lại); mọi kiểm bảo vệ kết quả giữ nguyên; thêm R0/transfer N, AC14, kiểm ngược AC0.

### 0B.11 Điểm dừng mới
- B9b R0 → CẦN PLANNER; B9b R2-FAIL hoặc hết giờ → CẦN NGƯỜI DÙNG (không đẩy K2).
- Test có sẵn mâu thuẫn thiết kế B9c → CẦN PLANNER (không sửa test).
- v4: CSLR lỗi hạ tầng → CẦN PLANNER (không v5 tự động); CSLR §3.6 không đạt → CẦN NGƯỜI DÙNG; transfer N lệch → CẦN PLANNER.
- Q4 (thông báo, KHÔNG chặn; mặc định = §0B.3): đường P bỏ smoke trên GPU dựa trên bằng chứng CPU (R1) hoặc kiểm overfit 60 epoch (R2). Người dùng
  phủ nhận trước B9e → dừng trước khi đẩy v4.

### 0B.12 Reviewer cần kiểm thêm
1. Tính lại `decision` từ `smoke_diag.json` theo đúng R0/R1/R2 (không theo lời coder); kiểm trung thực D4-ii; D1 gọi đúng `run_smoke_test` không sửa
   (`git diff <mốc> HEAD -- src/training/train_cslr.py` rỗng ở B9a–B9f).
2. Thứ tự commit: kế hoạch Lần sửa 2 ⊂ `smoke_diag.json` ⊂ amendment ⊂ ghim v4; amendment 1 dòng `git log`, chỉ khóa danh sách trắng.
3. Kernel: test lưu-từng-job thật sự mô phỏng CSLR lỗi + ViT5 thành công; `KernelError` vẫn nổ; không đường nào ghi đè/xóa.
4. Không có số mới trong md (số trong §0B là chép từ log/JSON có đường dẫn).

## 0. Lần sửa 1 (2026-10-02) — split câu theo quyết định Q1 = (ii)

### 0.1 Quyết định áp dụng (STATE `docs/STATE.md:165-173`) → chỗ thực hiện
| Ý của người dùng (nguyên văn rút gọn) | Thực hiện |
|---|---|
| Giữ split người ký hiện có (S06 = test) | §0.3: train S01–S04, val S05, test S06 (trường `split` của `dataset_canonical.json`, như `train_cslr.py:359-384`) |
| Câu test = đúng 30 câu ViT5 chưa thấy (để BLEU so được với 27.98 / 23.18) | §0.2: SENT271–SENT300, nguồn có file:dòng |
| Loại 30 câu test khỏi train CSLR ở MỌI người ký | §0.3: CSLR train/val không chứa câu test ở S01–S06 |
| Thêm ~30 câu val (seed cố định, ghi seed, không trùng câu test) | §0.3: đúng 30 câu, `random.Random(42)` trên SENT001–SENT270 |
| Chọn epoch/hyperparameter bằng val; test chạy MỘT lần | §0.3, §3.12: chọn epoch theo val (luật có sẵn); không dò hyperparameter (giữ mặc định); test = 1 lần `scripts/eval_sentsplit.py` |
| Cùng split câu cho ViT5; loại câu test (và val) khỏi train/val của ViT5 | §0.3: stage 2 dùng đúng split; stage 1 (10k) loại cặp khớp câu test ∪ val |
| Test guard FAIL nếu câu test xuất hiện trong train của CSLR hoặc ViT5 | §3.11 `tests/test_sentence_split_guard.py` (local, không GPU) + kiểm sau train từ ID thực dùng (G3) + kernel assert |
| Đăng ký trước: WER (S/D/I) + CI bootstrap trên 30 câu test; BLEU Mode A / Mode B + CI | §3.12 (giao thức đầy đủ: số lần bootstrap, seed, mức tin cậy, BLEU/tokenize cố định) |
| 30 câu KHÔNG chọn ngẫu nhiên | ghi ở §0.2, §3.12, R13 và trong file split |
| (i) chỉ chạy SAU (ii), nếu cổng ngân sách cho phép, như kiểm tra tái tạo số cũ; ghi vào ledger | §0.7: K3 tùy chọn (B14), sổ GPU 13-progress + dòng `docs/usage_ledger.csv` |
| Số liệu sinh từ JSON | §3.12: JSON có lệnh + commit + sha256 checkpoint; md không chứa số mới (§3.9) |

### 0.2 Nguồn 27.98 / 23.18 và định nghĩa 30 câu (đã tìm thấy — không cần hỏi)
- Số: `reports/audit_round2/v2_cslr_reliability.json:9-31` (`bleu_bootstrap_30_unseen`: Mode A `point_estimate` 27.98 CI [17.6, 38.39]
  `:10-16`; Mode B 23.18 CI [13.62, 33.7] `:17-23`; delta `:24-31`); đếm `:3-6` (300 mẫu S06, 30 "unseen", 270 "seen"); WER S06 300 mẫu
  `:33-39`. Trích lại ở `README.md:57-58`, `EVALUATION.md:386-387`, `reports/audit_round2/VERIFY.md:14,45-46`, `reports/audit_round2/AUDIT_ROUND2.md:97-98`.
- Script sinh: `reports/audit_round2/run_v2_cslr_bootstrap.py` (ghi JSON ở `:162-163`).
  - **Định nghĩa 30 câu:** mẫu S06 trong `reports/cslr_s06_predictions.json` có `sentence_id >= "SENT271"` (`:29-30`) ⇒ S06 × SENT271–SENT300
    (S06 có 1 mẫu/câu ⇒ 30 clip). Trùng tập `test` "strictly held out" của ViT5 stage 2: `src/translation/dataset.py:69,98-99`
    (`all_sids[270:]` sau khi sắp xếp). `reports/cslr_s06_predictions.json` sinh bởi `scripts/extract_cslr_predictions.py:31-38,81-100`
    (`ref_gloss_list` = `gloss_sequence` THÔ của mẫu, `translation` của chính mẫu S06).
  - Giao thức cũ: nguồn `normalize_vsl_source(ref_gloss_list | pred_gloss_list)`, đích `normalize_vietnamese_target(translation)` (`:43-45`);
    sinh `tokenizer(max_length=128, padding=True, truncation=True)`, `generate(num_beams=4, max_length=64)`, cả 30 câu một lô, giải mã
    `skip_special_tokens=True` rồi `normalize_vietnamese_target` (`:47-53`); điểm = `compute_translation_metrics` → `sacrebleu.corpus_bleu(hyps, [refs])`
    mặc định (`src/translation/metrics.py:41`); bootstrap `np.random.seed(42)`, `N_BOOTSTRAP = 1000`, `np.random.choice(n, n, replace=True)`, cùng chỉ
    số cho A, B, delta, CI = phân vị 2.5/97.5 (`:66-87`); WER 300 mẫu bằng Levenshtein số sửa (không tách S/D/I) tiếp cùng luồng RNG (`:97-133`).
- **30 câu KHÔNG chọn ngẫu nhiên:** là 30 `sentence_id` cuối theo thứ tự sắp xếp. Có thể khác hệ thống so với 270 câu còn lại (chủ đề, độ dài)
  ⇒ số trên 30 câu này KHÔNG đại diện cho "câu mới bất kỳ" (R13).
- **"So được với 27.98 / 23.18" — giới hạn phải ghi cùng số mới:** cùng 30 câu + cùng giao thức sinh/BLEU ⇒ so được về PHÉP ĐO. Nhưng model cũ
  có rò rỉ mà model mới không có: CSLR cũ đã học cả 300 câu qua S01–S04 (`docs/cloud_reports/viec-A-D-2026-09-29.md:45-48`) ⇒ 23.18 (Mode B)
  lạc quan; ViT5 stage 1 cũ có thể chứa các câu này (chưa đo — kế hoạch 07 C1) ⇒ 27.98 có thể lạc quan. Số mới thấp hơn KHÔNG có nghĩa model mới tệ hơn.

### 0.3 Split câu v1 (file `configs/vslgh_sentence_split_v1.json`, tracked, sinh bằng code — không gõ tay)
- Tập câu: **T (test)** = SENT271–SENT300 (30, cố định, §0.2). **V (val)** = `sorted(random.Random(42).sample(sorted(SENT001..SENT270), 30))`
  — seed **42** (quy ước seed của dự án, chọn trước khi có kết quả nào; ghi trong file cùng phiên bản Python 3.11.9 của `.venv`). **Tr (train)** =
  300 − T − V = 240 câu. Danh sách ID nằm trong file (file là nguồn sự thật; seed chỉ để truy nguồn gốc).
- Người ký giữ nguyên: `split=="train"` (S01–S04), `"val"` (S05), `"test"` (S06) — script sinh split KIỂM bằng code ánh xạ người ký ↔ `split`
  trong `dataset_canonical.json` đúng như vậy và đủ 300 `sentence_id` SENT001–SENT300; sai → exit ≠ 0.
- **CSLR:** train = S01–S04 × Tr (mọi lần lặp); val = S05 × V; test = S06 × T (30 clip). Không dùng ở đâu cả: S01–S04 × (V ∪ T), S05 × (Tr ∪ T),
  S06 × (Tr ∪ V). ⇒ câu T không có trong train/val CSLR ở BẤT KỲ người ký nào; câu V không có trong train. Số mẫu thực tính bằng code, ghi
  preregistration (§3.3); test phải đúng 30 (`v2_cslr_reliability.json:4`), khác → DỪNG (§7.2).
- **ViT5 stage 2:** train = Tr (240), val = V (30); T không dùng khi train. (Khác split cũ SENT241–270 làm val — chủ ý, theo "seed cố định".)
- **ViT5 stage 1 (10k):** giữ cách chia 90/10 cũ (`Clean10kDataset`, `random.Random(42)`, `src/translation/dataset.py:33-43`), SAU ĐÓ loại khỏi CẢ
  train và val mọi cặp "khớp" một câu thuộc T ∪ V. "Khớp" (đăng ký trước, lấy nguyên định nghĩa của kế hoạch 07 `docs/plans/07-viec6-che-do.md:181-184`
  để hai kế hoạch dùng cùng luật): so nguồn với nguồn, đích với đích, với MỌI cặp (mọi người ký, mọi lần lặp) của câu đó trong `dataset_canonical.json`;
  L1 = bằng nhau sau `normalize_vsl_source` / `normalize_vietnamese_target`; L2 = L1 + chữ thường + bỏ `.,!?;:"'()[]{}…` + gộp khoảng trắng;
  gần trùng = Jaccard tập từ (sau L2) ≥ 0.8 VÀ chênh số từ ≤ 1. Khớp L1 hoặc L2 hoặc gần trùng ở nguồn HOẶC đích → loại. Số bị loại (train/val) và
  ID bị loại tính bằng code, ghi preregistration; KHÔNG chép văn bản 10k vào repo (chỉ ID `PAR_10K_…`).
- Chọn epoch: CSLR theo val WER S05 × V (luật có sẵn `train_cslr.py:625-631`, hòa giữ epoch trước); ViT5 s1 theo val loss 10k (sau loại); ViT5 s2 theo
  val loss trên V (luật có sẵn của 2 script). **Không dò hyperparameter**: giữ đúng mặc định §2.2 (ngân sách; tránh chọn quá khớp trên val 30 mẫu).
- Mô-đun dùng chung (một chỗ, cho CSLR + ViT5 + vocab + guard + đánh giá): `src/data/sentence_split.py` — `load_sentence_split(path)` (kiểm rời nhau,
  phủ đủ, cỡ 240/30/30, T == SENT271..SENT300), `select_vslgh_samples(samples, split_name, sentence_split)`, `heldout_texts(canonical_samples, ids)`,
  `match_heldout(src, tgt, heldout) -> (bool, lý do)`. Chuẩn hóa dùng `src/translation/text_normalizer.py` (module tiền xử lý văn bản chung, không viết lại).

### 0.4 Vocab gloss: CHỈ từ câu train (thay quyết định ở B2)
- **Chọn:** vocab = gloss duy nhất của đúng các mẫu CSLR train (S01–S04 × Tr), dựng bằng `select_vslgh_samples(…, "train", split)` + cùng thứ tự
  `<blank>`, `<unk>`, gloss đã sắp xếp (`vsl_gh_dataset.py:225-232`), ghi LF.
- **Lý do (theo mục đích "không rò rỉ nhãn test vào huấn luyện"):** vocab quyết định `num_classes` và các lớp đầu ra CTC của model ⇒ dựng từ toàn bộ
  dataset là đưa thông tin từ nhãn test/val (tập gloss chỉ có ở T/V) vào kiến trúc model. Lớp chỉ có ở T/V không bao giờ có gradient dương nên lợi
  ích thực của việc giữ chúng gần như không có, còn rủi ro diễn giải là có ⇒ chọn bản sạch. Không gây "<unk> được tính đúng": WER test chính thức
  so với chuỗi gloss THÔ (§3.12), gloss ngoài vocab luôn tính là lỗi dưới cả hai lựa chọn; `<unk>` dự đoán không bao giờ khớp tham chiếu.
- **Ảnh hưởng tới 372:** số token mới = N_train (tính bằng code ở B2c, ≤ 372), ghi preregistration kèm danh sách `glosses_only_in_val`,
  `glosses_only_in_test` (= vocab đầy đủ − vocab train) và tỉ lệ token tham chiếu test ngoài vocab. 372 chỉ còn là tham chiếu cho vocab ĐẦY ĐỦ
  (bản B2, sha256 `dd7bc3da…1d11`, 13-progress:71-75) — dùng cho K3 (i), KHÔNG đặt vào `data/external/vsl_gh/`.
- **Ảnh hưởng tới test:** không test nào khóa 372 (grep `tests/` cho `372|gloss_vocab` chỉ thấy `test_retrain_tools.py` dùng dữ liệu giả, không số 372).
  15 test B2 giữ nguyên, không sửa: hành vi mặc định (không `--sentence-split`) của script vocab phải giữ hệt (thêm test chứng minh). AC2-06
  (`test_translation_core`) chỉ kiểm khóa/không rỗng ⇒ không phụ thuộc số token. `tests/test_retrained_artifacts.py` kiểm `num_classes == số dòng vocab`
  — đúng với bất kỳ N. Tiêu chí kế hoạch "khác 372 → DỪNG" (AC2, §7.2-2) được planner đổi (§0.8).
- Hệ quả chức năng (ghi R14): model mặc định không nhận được gloss chỉ có ở 60 câu T ∪ V. Một model "đủ dữ liệu cho phục vụ" (train cả 300 câu) là
  việc khác, cần GATE riêng — không nằm trong kế hoạch này.

### 0.5 Phần không đổi / xác nhận
- **K1 `stgcn_best` (a4) không đổi:** dữ liệu Tier 1 QIPEDC từ đơn (`tier1_grouped_*`), không chứa câu/clip VSL-GH ⇒ split câu không liên quan.
  (Đính chính hiện trạng theo 13-progress B0: 4 file `data/splits/folds/tier1_grouped_*` đang TRACKED, không phải untracked như §2.2/R2 ghi; vẫn đóng gói ở B3/B6.)
- **CSLR backbone = a4 MỚI** (output K1, sha256 kiểm như §3.4e). Serving/test AC2-06: checkpoint (ii) đặt vào đường dẫn mặc định (Q3 mặc định "được").
- Ngân sách: K1 và K2 giữ trần (§3.7). K3 (i) thêm, tùy chọn.

### 0.6 Đăng ký trước đánh giá — xem §3.12 (mới). Phải nằm trong commit TRƯỚC khi đẩy kernel nào (kế hoạch này do orchestrator commit;
`preregistration.json` B5 chép giao thức bằng code, `scripts/eval_sentsplit.py` ĐỌC tham số từ `preregistration.json`, không hằng gõ tay).

### 0.7 (i) công thức cũ — K3 tùy chọn, chỉ SAU (ii)
- Điều kiện chạy: B13 xong (kể cả eval một lần của (ii)) VÀ cổng ngân sách §3.7 cho trần K3 (1,75 GPU-giờ) VÀ cổng hạn mức 5h của orchestrator.
  Không đạt → ghi "K3 hoãn — lý do" vào 13-progress + `docs/usage_ledger.csv` (orchestrator), không chạy.
- Nội dung: CSLR công thức cũ (không `--sentence-split`, vocab ĐẦY ĐỦ bản B2) ∥ ViT5 s1 (không loại) → s2 (split cũ SENT001–240 / 241–270), cùng a4 mới,
  cùng kernel K2 với `MODE="repro_i"`. Đánh giá MỘT lần bằng `scripts/eval_sentsplit.py --protocol repro_v2` = tái hiện nguyên giao thức
  `run_v2_cslr_bootstrap.py` (§0.2). Tiêu chí mô tả (đăng ký trước): với mỗi số cũ (27.98, 23.18, 32.80) ghi "nằm trong CI 95% mới" hay không; KHÔNG
  phải ngưỡng đạt/không đạt, không hành động nào dựa trên kết quả.
- Artifact (i) chỉ ở `_work/_plan13_tmp/k3/` + dataset private `phmvnsm33/vslt-retrain-repro-i` (manifest); KHÔNG bao giờ vào `checkpoints/`.
- Ghi: sổ GPU 13-progress (phút phiên từ `env.json`) + 1 dòng `docs/usage_ledger.csv` (orchestrator ghi; "ledger" theo quyết định).
- **[LS2]** K3 cũng sẽ gặp smoke test CSLR (công thức cũ, không `--sentence-split`) — trước B14 phải có quyết định riêng dựa trên D2 của B9b (§0B.3); không
  tự áp amendment `ls2` cho K3 (amendment chỉ đổi `jobs.k2.cslr.train.argv`).

### 0.8 Thay đổi tiêu chí chấp nhận (planner đổi, lý do)
| Tiêu chí | Cũ | Mới | Lý do |
|---|---|---|---|
| AC0 | danh sách file được sửa | thêm file của §0.3/§3.11/§3.12 và các tùy chọn mới trong mã train/dataset | quyết định (ii) bắt buộc sửa mã chọn mẫu; mọi tùy chọn mặc định giữ hành vi cũ |
| AC2 | vocab 372, khác → DỪNG | vocab train-only == giá trị tính bằng code trong preregistration; ≤ 372; hiệu tập == danh sách đăng ký | §0.4 (không rò rỉ nhãn test). KHÔNG nới: so khớp chính xác với số đăng ký trước, vẫn byte-bằng-hệt K2 |
| AC3 | Clean10k 6426/714, CSLR 3600/300/300 | giữ các số tham chiếu cho dữ liệu GỐC + thêm số sau lọc == preregistration, test CSLR == 30 | dữ liệu dùng để train đổi theo split |
| AC5 | đúng 1 dòng `PRIMARY TEST EVALUATION` trong log K2 | 0 dòng đó; đúng 1 dòng `TEST DEFERRED`; test chạy 1 lần ở AC12 | test không được chạm trong tiến trình train; đánh giá phải đủ S/D/I + CI + BLEU A/B |
| AC11, AC12, AC13 | — | mới (split & guard; đánh giá đăng ký trước; K3) | quyết định (ii) |
| §3.1-2 "ViT5: KHÔNG chạy test" | — | ViT5 chạy trên T đúng 1 lần trong eval | người dùng yêu cầu BLEU Mode A/B |
| §3.1-5 "không sửa mã train ngoài train.py" | — | cho phép tùy chọn mới, mặc định giữ nguyên | như trên |
Không tiêu chí nào bị hạ: mọi số "sau lọc" phải bằng giá trị code tính và commit TRƯỚC kernel.

### 0.9 Reviewer cần kiểm thêm (ngoài §5)
1. Thứ tự commit: commit Lần sửa 1 (kế hoạch) ⊂ tổ tiên commit `preregistration.json` ⊂ tổ tiên commit ghim K2 ⊂ tổ tiên commit chạy eval
   (`git merge-base --is-ancestor`); `preregistration.json` và `configs/vslgh_sentence_split_v1.json` không bị sửa sau commit tạo (mỗi file 1 dòng `git log`).
2. Guard rò rỉ: chạy `tests.test_sentence_split_guard` + G3 trong `test_retrained_artifacts`; tự đột biến (thêm 1 ID test vào bản sao `used_ids`/split
   trong `_work/`) → test phải FAIL (không sửa file thật).
3. Kernel log: assert không rò rỉ in "LEAK CHECK OK" trước khi train; 0 dòng `PRIMARY TEST EVALUATION`; S06 không được nạp ở tiến trình train.
4. Eval: đúng 1 lần chạy (log + `git log` 1 dòng cho JSON); `--recompute-from` tính lại từ dự đoán đã lưu ra đúng số (không chạy lại model);
   tham số trong JSON == §3.12 == preregistration.
5. Hành vi mặc định không đổi: test cũ (AC2-06, 15 test B2) xanh y mốc; diff các hàm có sẵn chỉ THÊM nhánh khi tùy chọn mới được truyền.
6. Không có số mới trong md; số so sánh với 27.98/23.18 luôn kèm giới hạn §0.2.

## 1. Mục tiêu & DoD
Tái tạo, dưới dạng ARTIFACT MỚI, các thứ bị mất trong sự cố 30/9 mà không có bản lưu trữ: `checkpoints/stgcn_best.pt` (a4),
`checkpoints/vit5_stage{1,2}/best_model/` (a5), `checkpoints/cslr_best.pt` (a6) + `data/external/vsl_gh/gloss_vocab_canonical.txt`,
bằng kernel Kaggle PRIVATE, đăng ký trước tiêu chí, lưu ngay lên dataset Kaggle PRIVATE kèm manifest sha256. Gỡ Modal khỏi repo.
**[LS1]** CSLR (a6) và ViT5 (a5) train theo split câu v1 (§0.3); đo một lần WER (S/D/I) + BLEU Mode A/B kèm CI trên 30 câu test (§3.12).
- DoD 7 (kiểm thử): AC2 của kế hoạch 06 (31 module) về lại `Ran 526` `OK`, 0 skip (hiện 518 / 1 ERROR / 1 skip — 12-progress B9).
- DoD 4 (Ký câu): mở khóa CSLR → gloss → ViT5 cho kế hoạch 07 (07 bị chặn tới khi có a5/a6 — kế hoạch 12 §8.1 (A)).
- DoD 9 (tài liệu trung thực): đánh dấu số liệu cũ không áp cho artifact mới.
- Quyết định người dùng 2026-10-02 09:20 (`docs/STATE.md:153-154`): không có bản sao thì train lại trên Kaggle; bỏ Modal.
- **[LS1]** Quyết định người dùng 2026-10-02 10:05 (`docs/STATE.md:165-173`): Q1 = (ii).
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
**[LS1]** Đầu vào của `test_translation_core` là gloss gõ tay (`:45,52-56,69,83`) và keypoint ngẫu nhiên (`:74,90`) — không dùng dữ liệu S06/T ⇒ chạy test
này không phải "chạy test set".

### 2.2 Công thức train gốc (mã còn nguyên trong repo)
- **a4 stgcn_best (Tier 1):** `train.py` + `configs/experiments/stgcn.yaml` (STGCNModel [64,64,128], 100 epoch, patience 10, lr 1e-3,
  bs 16, AMP; checkpoint `checkpoints/stgcn_best.pt`, history `experiments/stgcn/history.json`). Chọn epoch theo VAL top-1 (hòa → val loss)
  `src/training/trainer.py:196-215`; định dạng `{epoch, model_state_dict, optimizer_state_dict, val_top1, val_loss, val_top5, val_macro_f1}`
  (không có label_map). Test một lần: `evaluate_test.py --config … --checkpoint … --output-dir …` (`:332-357`; ghi `benchmark_results.json` `:316`).
  Dữ liệu: `get_vsl_dataloaders(tier="tier1")` mặc định HIỆN TẠI = `data/splits/folds/tier1_grouped_{train,val,test}.csv` + guard
  (`src/data/vsl_dataset.py:406-429`), npz phẳng `data/extracted_keypoints/<video_id>.npz` (`:314-315`). Cả hai **untracked, còn trên
  đĩa** (12-progress B0). **`train.py` không đặt seed** (`train.py:72-187`).
  **[LS1] Đính chính (13-progress B0):** 4 file `tier1_grouped_*` đang TRACKED; npz untracked.
  Nguồn gốc a4 cũ: `docs/phase6_stgcn.md:221-247` ghi best epoch 49; `experiments/stgcn/benchmark_results.json:4,16` ghi best epoch 26 — hai
  lần chạy khác nhau, đều TRƯỚC split theo bản quay (`reports/audit_round3/PROVENANCE.md:73`). ⇒ KHÔNG tái tạo split cũ (rò rỉ bản quay; guard chặn).
- **a6 CSLR:** `python src/training/train_cslr.py` (mặc định bs 8, 40 epoch, stage1 10 epoch backbone đóng băng lr 1e-3, stage2 lr 1e-4/5e-4,
  patience 10, seed 42 — `:718-752`; smoke test chạy trước khi train). Dữ liệu `data/external/vsl_gh/{dataset_canonical.json, keypoints_frontal/}`
  (khôi phục ở kế hoạch 12 B8), `normalize=True`, `semantic`; split theo NGƯỜI KÝ: train S01–S04 (cả 300 câu), val S05, test S06 (`:359-384`);
  chọn theo val WER S05 (`:625-631`); test S06 MỘT lần cuối hàm (`:661-679`). Checkpoint chứa `gloss_vocab_hash` = 16 hex đầu sha256(vocab)
  (`:64-67,345,613`). **Ghi đè file tracked** `reports/cslr_training_history.{json,csv}`, `reports/cslr_test_results.json` (`:647-711`).
  **[LS1]** Smoke test (`:210-244`) lấy 8 mẫu đầu `split="train"` + 1 mẫu `split="val"` — ở chế độ split câu phải lọc cùng luật (§3.4f).
  WER trong `evaluate_cslr` (`:108-170`) so trên ID đã mã hóa bằng vocab (gloss ngoài vocab → `<unk>`); hàm `compute_wer`
  (`src/metrics/cslr_metrics.py:169-230`) trả S/D/I, tie-break "ưu tiên substitution" (`:162-163`).
  **[LS2]** Số dòng tại HEAD 70f86b6: `run_smoke_test` `:242-355` (nạp backbone `:299-300`, tiêu chí `:346-348`), `train_cslr` `:358-819`
  (smoke `:398-402`, nạp backbone `:496-504`), CLI `:822-875` (`--skip-smoke-test` `:836`).
- **vocab:** không script nào ghi `gloss_vocab_canonical.txt` (grep: chỉ nơi đọc — `train_cslr.py:737`, `cslr_recognizer.py:27`,
  `modal_runner.py:201-202`). Cơ chế có sẵn: `VSLGlossVocabulary.from_canonical_dataset(json)` (`src/data/vsl_gh_dataset.py:277-287`):
  `<blank>`, `<unk>`, rồi gloss duy nhất đã sắp xếp (`:225-232`). `.save()` mở file chế độ văn bản không `newline=` (`:289-293`) ⇒ Windows ghi
  CRLF, Linux ghi LF ⇒ sha256 khác giữa hai máy (§6 R3). Số token tham chiếu 372 (`docs/vsl_gh_dataset.md:19`; `reports/cslr_dry_run_results.json:6`).
  Planner không có shell ⇒ B0 tra `git log --all -S`.
  **[LS1]** B2 đã làm: `scripts/build_gloss_vocab_canonical.py` (vocab đầy đủ 372, sha256 `dd7bc3da…1d11`); không tìm thấy cách sinh gốc trong git.
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
  **[LS1]** Dataset tạo ở stage1 `:60-61`, stage2 `:71-72`; tham số dòng lệnh stage1 `:189-191`, stage2 `:202-206`.
  `VSLGHTextDataset` lấy cặp của mẫu ĐẦU TIÊN gặp cho mỗi `sentence_id` (`dataset.py:82-90`).
- Thời gian lịch sử (RTX 3050 laptop — cơ sở ước lượng §3.7): stgcn 2.27 phút (`docs/phase6_stgcn.md:222`); CSLR 2108.74 s / 40 epoch
  (`reports/cslr_test_results.json:5-7`); ViT5 stage1 1293.08 s (`reports/vit5_stage1_history.json:8`), stage2 145.94 s (`reports/vit5_stage2_history.json:7`).
- **[LS1] Đánh giá cũ trên 30 câu:** `reports/audit_round2/run_v2_cslr_bootstrap.py` → `v2_cslr_reliability.json` (§0.2).

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
- **[LS1]** Đã gỡ ở B1 (nằm trong commit `84c90e4` — 13-progress B1).

## 3. Thiết kế

### 3.1 Nguyên tắc
1. Mỗi checkpoint train lại là ARTIFACT MỚI: số liệu cũ (README, EVALUATION, `reports/PHASE4B_REPORT.md`, `reports/cslr_*`, `reports/vit5_*`,
   `experiments/stgcn/*`, `docs/phase6_stgcn.md`) KHÔNG áp dụng; không ghi đè file cũ nào; số liệu mới chỉ nằm trong JSON mới dưới
   `reports/retrain_<D>/` (`<D>` = ngày coder làm B5, cố định cho cả kế hoạch) kèm lệnh + commit.
2. Đăng ký trước (§3.3) được commit TRƯỚC khi đẩy kernel nào. Chọn epoch bằng VAL theo luật có sẵn trong mã; TEST chạy đúng một lần
   (stgcn: Tier 1 test; CSLR: S06 cuối `train_cslr`); ViT5: KHÔNG chạy test nào ở kế hoạch này (để kế hoạch 07 đo có đăng ký trước).
   **[LS1] thay phần CSLR/ViT5:** CSLR + ViT5 (ii): TEST = S06 × T, chạy đúng MỘT lần bằng `scripts/eval_sentsplit.py` ở máy local sau B11 (§3.12);
   tiến trình train trên Kaggle KHÔNG nạp mẫu test. ViT5 chỉ chạy trên T trong lần eval đó (Mode A/B). Kế hoạch 07 phải lập lại phần ViT5/S06 (R11).
   Không thử seed khác, không chạy lại vì kết quả kém; chạy lại chỉ khi lỗi hạ tầng (§3.6).
3. Kernel PRIVATE, clone repo ở commit GHIM (assert `git rev-parse HEAD`), mọi đầu vào kiểm digest so với giá trị tính ở máy local
   và ghi trong đăng ký trước — lệch → kernel dừng TRƯỚC khi train.
4. Mọi checkpoint mới lên dataset Kaggle PRIVATE + manifest sha256 commit trong repo trước khi coi là xong. Không commit `.pt`/model/dữ liệu.
5. Không sửa mã train/model/tiền xử lý ngoài: `train.py` thêm `--seed` (mặc định giữ hành vi cũ). Mọi ghi đè file tracked của script train
   chỉ xảy ra TRONG bản clone trên Kaggle (`/tmp/vslt`), không bao giờ chép ngược đè lên repo local.
   **[LS1] bổ sung:** được THÊM tùy chọn `sentence_split`/`--sentence-split` (và `exclude_heldout` cho `Clean10kDataset`) ở §3.4f; không truyền →
   hành vi y hệt cũ (test chứng minh). Không đổi model, không đổi tiền xử lý keypoint/văn bản.
   **[LS2]** Lần sửa 2 KHÔNG sửa `src/training/train_cslr.py` (kể cả `run_smoke_test`); chỉ dùng cờ có sẵn `--skip-smoke-test` qua amendment (§0B.3).

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
**[LS1]** `configs/vslgh_sentence_split_v1.json` (tracked) đi theo bản clone; K2 `train` truyền `--sentence-split` cho cả 3 job, vocab train-only,
xuất `*_used_ids.json`. Sau B11: `scripts/eval_sentsplit.py` (local, CPU, MỘT lần) → `reports/retrain_<D>/eval/test_eval.json`.
K3 (i) tùy chọn dùng lại K2 với `MODE="repro_i"` (§0.7).
**[LS2]** Trước K2 v4: chẩn đoán smoke local CPU (B9b) → `reports/retrain_<D>/k2_ls2_smoke_diag/` → amendment `preregistration_amendment_ls2.json` (nếu
đường P) → kernel đọc amendment; mỗi job xong là chép ngay output của nó vào `/kaggle/working/k2/` (§0B.4).

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
- **[LS1] thêm (đều tính bằng code từ file split + dữ liệu local):**
  - `sentence_split{path, sha256, version, seed, python, test_ids, val_ids, n_train_sentences}`.
  - `counts_after_split`: `VSLGHContinuousDataset` train/val/test với split (test phải 30), `VSLGHTextDataset` train/val (240/30),
    `Clean10kDataset` train/val sau loại + `clean10k_excluded{rule_ref: "§0.3", n_train, n_val, by_reason{L1,L2,near_dup}, ids}`.
  - `leak_check`: giao của câu T (và V với train) với mọi tập train/val ở trên = 0 (đếm bằng chính hàm của §0.3); khác 0 → script exit ≠ 0, không ghi file.
  - `vocab{mode: "train_only", n_tokens, sha256, glosses_only_in_val, glosses_only_in_test, test_ref_tokens_total, test_ref_tokens_oov}` +
    `vocab_full_reference{n_tokens: 372, sha256: dd7bc3da…(đủ 64 hex), dùng cho: K3}`.
  - `evaluation_protocol`: toàn bộ tham số §3.12 (máy đọc được); `evaluation_protocol_repro_v2` cho K3.
  - `jobs`: ViT5 không còn "không test" — ghi "test = eval_sentsplit một lần, local, sau B11"; thêm K3 (tùy chọn, điều kiện §0.7).
  - `libs_local` thêm `sacrebleu`, `numpy`, `rouge_score` (phiên bản trong `.venv`).
Kernel đọc file này TỪ bản clone ở commit ghim (không hằng số gõ tay trong script kernel). Giá trị phụ thuộc K1 (sha256 `stgcn_best.pt`)
nằm ở `reports/retrain_<D>/k1_outputs.json`, commit SAU K1, TRƯỚC K2-train.
**[LS2]** `preregistration.json` KHÔNG sửa. Thay đổi công thức sau v3 nằm ở file bổ sung `reports/retrain_<D>/preregistration_amendment_ls2.json`
(1 commit, sinh bằng `scripts/retrain_amendment.py`, chỉ khóa danh sách trắng `jobs.k2.cslr.train.argv` — §0B.3, §0B.9 B9c/B9d).

### 3.4 Công cụ mới
**(a) `scripts/build_gloss_vocab_canonical.py`** — `--canonical <dataset_canonical.json> --out <file>`; dùng
`VSLGlossVocabulary.from_canonical_dataset` để lấy thứ tự token, nhưng tự ghi bytes UTF-8, mỗi token + `"\n"` (LF trên mọi OS); đích đã có → exit 2,
không ghi; in số token + sha256. Nếu B0 tìm thấy cách sinh gốc trong lịch sử git → dùng đúng logic đó (ghi commit vào 13-progress), giữ LF.
**[LS1]** thêm `--sentence-split <json> --split train`: chỉ lấy gloss của `select_vslgh_samples(samples, "train", split)`; cùng thứ tự/định dạng;
in thêm `glosses_excluded` (gloss chỉ có ngoài tập chọn). Không có `--sentence-split` → byte y hệt bản B2 (test).
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
  **[LS1] K2 thay đổi:** preflight và train dùng `build_gloss_vocab_canonical.py --sentence-split configs/vslgh_sentence_split_v1.json --split train`
  (vocab train-only; byte == bản B2c local); preflight thêm `counts_after_split`, `clean10k_excluded`, `leak_check` so với preregistration.
  `train`: TRƯỚC khi train in "LEAK CHECK OK" (kiểm lại bằng hàm §0.3 trên chính dataset sắp dùng; ≠ 0 → exit ≠ 0);
  GPU0 `train_cslr.py --sentence-split configs/vslgh_sentence_split_v1.json` (tham số khác mặc định); GPU1 `train_translation_stage1.py --sentence-split …`
  → `train_translation_stage2.py --sentence-split … --stage1-path checkpoints/vit5_stage1/best_model`. Xuất thêm `cslr_used_ids.json`,
  `vit5_stage1_used_ids.json`, `vit5_stage2_used_ids.json`. `MODE="repro_i"` (chỉ K3): như `train` nhưng KHÔNG `--sentence-split`, vocab đầy đủ
  (byte == bản B2), CSLR chạy test S06 cuối hàm như cũ; đầu ra vào `/kaggle/working/k3/`.
  **[LS2] K2 thay đổi:** (1) "MODE đổi bằng commit" được hiểu và thực hiện như §0B.6(a): file repo giữ `MODE = "preflight"`, `PIN_COMMIT = None`, metadata CPU
  (khóa bởi test có sẵn); MODE của lần chạy = giá trị trong bản đẩy (∈ `MODES`), kernel tự kiểm phần còn lại == file ở ghim (§0B.6(b)); bản ghi đẩy commit
  ở `reports/retrain_<D>/k2/push_record.json`. (2) "có smoke test" của CSLR: theo amendment `ls2` nếu B9b ra đường P (§0B.3). (3) Lưu output từng job
  ngay khi job kết thúc (§0B.4). (4) Kiểm số tham số backbone chuyển `[MODEL] Transferred N` == amendment.
**[LS1] (f) Tùy chọn split câu trong mã có sẵn** (impact upstream trước khi sửa từng symbol; HIGH/CRITICAL đối chiếu grep, ghi 13-progress):
- `src/data/sentence_split.py` (mới, §0.3).
- `VSLGHContinuousDataset.__init__(…, sentence_split=None)` (`vsl_gh_dataset.py:354-420`): có → yêu cầu `split ∈ {train,val,test}` và
  `loso_*` là None (ngược lại `ValueError`), lọc bằng `select_vslgh_samples`. None → y hệt cũ.
- `VSLGHTextDataset.__init__(…, sentence_split=None)` (`dataset.py:72-103`): có → `train|val|test` lấy danh sách từ file; `all` không đổi.
- `Clean10kDataset.__init__(…, exclude_heldout=None)` (`dataset.py:22-49`): có → sau bước chia cũ, bỏ mục `match_heldout` đúng; giữ `excluded_ids`
  + lý do. None → y hệt cũ.
- `src/training/train_cslr.py`: `--sentence-split PATH` → 3 dataset + smoke test (`:210-244`) lọc theo split; KHÔNG dựng test dataset, KHÔNG chạy
  khối test cuối (`:660-711`), in đúng một dòng `TEST DEFERRED (sentence split v1): run scripts/eval_sentsplit.py once`; ghi `cslr_used_ids.json`
  (sample_id + sentence_id của train/val) vào `reports_dir`; `config` thêm `sentence_split_path`, `sentence_split_sha256`.
- `scripts/train_translation_stage1.py --sentence-split PATH [--canonical-json PATH]` → `exclude_heldout = heldout_texts(T ∪ V)`; ghi used/excluded IDs.
- `scripts/train_translation_stage2.py --sentence-split PATH` → `VSLGHTextDataset(split=…, sentence_split=…)`; ghi used IDs.
- `scripts/make_vslgh_sentence_split.py --canonical … --seed 42 --out configs/vslgh_sentence_split_v1.json` (từ chối ghi đè, kiểm §0.3).
- `scripts/eval_sentsplit.py` (§3.12).
**[LS2] (g)** `scripts/retrain_amendment.py` (mới, B9d) + chẩn đoán `_work/_plan13_tmp/ls2/smoke_diag.py` (B9b, không commit vào `scripts/`).

### 3.5 Đặt vào chỗ (B11)
`cp -n` từ bản ĐÃ verify (staging) vào đích; trước đó kiểm đích chưa tồn tại; sau đó sha256 đích == manifest. Đích:
`checkpoints/stgcn_best.pt`, `checkpoints/cslr_best.pt`, `checkpoints/vit5_stage1/best_model/*`, `checkpoints/vit5_stage2/best_model/*`,
`data/external/vsl_gh/gloss_vocab_canonical.txt` (bản sinh ở local B2 — phải bằng hệt bản K2 dùng), `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl`
(B3). Không đặt `cslr_stage1_best.pt`/`cslr_latest.pt` (chỉ lưu trữ nếu muốn). Không tạo link/junction.
**[LS1]** Vocab đặt vào chỗ = bản train-only sinh ở B2c (phải byte-bằng-hệt bản K2 dùng); bản đầy đủ B2 (372) KHÔNG đặt. Artifact K3 không đặt.

### 3.6 Kiểm hợp lý (đăng ký trước; KHÔNG phải ngưỡng chất lượng)
- Mọi loss trong history hữu hạn (không NaN/Inf); có best epoch ≥ 1.
- stgcn: val top-1 ở best epoch > 100 / số_lớp (mức ngẫu nhiên, số lớp đọc từ label_map).
- CSLR: `best_val_wer` < 100.
- ViT5: stage2 sinh câu không rỗng cho đầu vào của `test_translation_core` (kiểm ở B11 bằng chính test đó).
Không đạt → DỪNG, CẦN NGƯỜI DÙNG (không chạy lại với seed/cấu hình khác). Chạy lại chỉ được phép khi lỗi hạ tầng (ngoại lệ trước khi xong
epoch đầu, Kaggle lỗi/hết phiên, lỗi mạng khi clone/pip/HF) — tối đa 1 lần/job, cùng cấu hình, ghi vào 13-progress.
**[LS1]** Số đo trên T (§3.12) KHÔNG có ngưỡng đạt/không đạt và không dẫn tới chạy lại nào.
**[LS2]** Không đổi các kiểm trên. K2 v4 = lần chạy lại duy nhất của CSLR (smoke raise trước epoch đầu) và của ViT5 (checkpoint v3 mất do thiết kế output);
"cùng cấu hình" với CSLR = cấu hình đăng ký + amendment `ls2` (chỉ `--skip-smoke-test`, §0B.3). Kiểm hợp lý chạy theo TỪNG job (§0B.4). v5 → §0B.11.

### 3.7 Thứ tự, ước lượng GPU-giờ, trần
| Job | Mở khóa | Cơ sở ước lượng (thời gian lịch sử trên RTX 3050) | Ước lượng (chưa xác minh) | Trần cứng |
|---|---|---|---|---|
| K2-preflight (CPU) | phát hiện lệch dữ liệu/thư viện sớm | — | 0 GPU-giờ | — |
| K1 stgcn Tier 1 (GPU T4) | `test_vsl_predictor_smoke` (cổng a4); backbone cho CSLR | 2.27 phút train + khởi động/clone | ≤ 0,25 | 0,75 (watchdog 45') |
| K2-train (GPU T4×2 song song) | `test_translation_core` (cần cả ViT5 + CSLR + vocab) | CSLR 2108.74 s ∥ ViT5 1293.08 + 145.94 s + tải HF/pip | ≤ 1,0 | 1,75 (watchdog 105') |
| **Tổng kế hoạch 13** | | | **≤ 1,25** | **2,5** |
| **[LS1]** K3 repro_i (GPU T4×2, TÙY CHỌN, sau B13) | kiểm tra tái tạo số cũ (§0.7) | như K2-train | ≤ 1,0 | 1,75 (watchdog 105') |
| **[LS1] Tổng nếu chạy K3** | | | **≤ 2,25** | **4,25** |

Thời gian thật = thời gian phiên đọc từ `env.json`/log kernel (ghi vào sổ GPU trong 13-progress). Trước MỖI job GPU: nếu
`GPU tuần đã dùng (STATE) + GPU đã dùng ở kế hoạch 13 + trần job` > 10 → DỪNG, CẦN NGƯỜI DÙNG. Với số STATE hiện tại (~6) cả hai job lọt.
Song song GPU0/GPU1 trong một phiên tính quota một lần (cách của `vsl-train-harmonized`). K1 phải xong trước K2-train (backbone).
Không mở khóa test nào riêng lẻ: `test_translation_core` cần đủ ViT5 + CSLR + vocab ⇒ AC2-06 chỉ kiểm được sau K2-train.
**[LS1]** (ii) train trên tập con của dữ liệu cũ (S01–S04 × 240 câu; val 30 clip) ⇒ ước lượng K2 không tăng; giữ trần. K3: cổng trên vượt 10 → KHÔNG
dừng-hỏi, chỉ ghi "K3 hoãn" (K3 tùy chọn theo quyết định người dùng "nếu cổng ngân sách cho phép"). Với số STATE ~6 + trần K1/K2 2,5 = 8,5,
K3 (1,75) chỉ lọt nếu GPU thật đã dùng thấp hơn trần — tính lại bằng số thật trước B14.
**[LS2]** Đã dùng: K1 1.58 + K2 v3 12.14 = 13.72 GPU-phút (≈ 0.23 h). K2 v4 giữ trần 1,75 h ⇒ tổng ≤ 1.98 ≤ 2,5. Cổng tuần dùng
`max(STATE, kaggle quota đọc ngay trước khi đẩy)` (§0B.7).

### 3.8 CSLR: (i) hay (ii) — khuyến nghị (i)
**[LS1] ĐÃ QUYẾT: (ii)** (người dùng, 2026-10-02 10:05). Phần dưới giữ làm lịch sử lập luận; thiết kế áp dụng ở §0.3. Khác với mô tả (ii) cũ dưới
đây: val = 30 câu chọn bằng seed 42 (không phải SENT241–270); split người ký giữ nguyên; stage 1 (10k) loại cặp khớp T ∪ V; sửa mã chỉ bằng tùy chọn
mặc định None; artifact (ii) đặt vào đường dẫn MẶC ĐỊNH (Q3), không phải `cslr_sentsplit_best.pt`.
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
**[LS1]** Câu đính chính rò rỉ đổi thành: "CSLR CŨ train trên S01–S04 cho CẢ 300 câu ⇒ S06 chỉ chưa thấy NGƯỜI KÝ, không phải chưa thấy câu.
CSLR + ViT5 mới (kế hoạch 13, split câu `configs/vslgh_sentence_split_v1.json`) không thấy 30 câu SENT271–SENT300 khi train ở bất kỳ người ký nào;
số đo mới ở `reports/retrain_<D>/eval/test_eval.json` (30 câu KHÔNG chọn ngẫu nhiên; so với 27.98/23.18 xem giới hạn trong JSON)." Thêm 1 dòng
cùng nội dung sau `reports/audit_round2/VERIFY.md:46` và `EVALUATION.md:387`. README "Artifact không nằm trong git": thêm dataset K3 nếu B14 chạy.

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
  **[LS1] thêm:** vocab `--sentence-split` trên dữ liệu giả (gloss chỉ có ở câu val/test KHÔNG vào vocab; không tùy chọn → byte y hệt bản không lọc);
  `eval_sentsplit` trên dự đoán giả (S/D/I khớp tính tay cho 3 cặp nhỏ; bootstrap tất định với seed; đọc tham số từ preregistration giả; từ chối ghi đè → 2;
  `code_dirty` → 2; `--recompute-from` ra số bằng hệt; protocol `repro_v2` tái hiện thuật toán `run_v2_cslr_bootstrap.py` trên dữ liệu giả).
  **[LS2] thêm (chỉ THÊM, không sửa test có sẵn):** K2 lưu-từng-job (run giả: CSLR exit 1 + ViT5 exit 0 có file giả → file ViT5 có trong `WORK`,
  `env.jobs.*.saved/missing` đúng, `KernelError` vẫn nổ); amendment (không file → argv preregistration; hợp lệ → argv + `--skip-smoke-test`; khóa lạ / argv
  lạ / ≠ 1 commit / không là tổ tiên → `KernelError`); `check_backbone_transfer` (N đúng → OK; lệch/thiếu/2 dòng → `KernelError`); `retrain_amendment.py`
  (từ chối ghi đè → 2, `code_dirty` → 2, decision không phải R1/R2-PASS → 3).
- **[LS1] `tests/test_sentence_split_guard.py`** (local, không GPU, không mạng; FAIL — không skip — khi vi phạm):
  - G1 (dữ liệu giả, luôn chạy): `load_sentence_split` từ chối split chồng lấn/thiếu/sai cỡ/T ≠ SENT271..SENT300; `select_vslgh_samples` không trả mẫu
    ngoài danh sách/ngoài người ký; `match_heldout` bắt L1, L2, gần trùng ở nguồn và đích; 3 dataset với `sentence_split=None` trả đúng như cũ.
  - G2 (dữ liệu thật local: `configs/vslgh_sentence_split_v1.json`, `data/external/vsl_gh/dataset_canonical.json`, `data/external/parallel_text/
    vie_vsl_10k_cleaned.jsonl` — có sau B11): file split tái sinh được bằng seed 42 (Python của `.venv`) và khớp sha256 trong preregistration; mọi
    `sentence_id` của `VSLGHContinuousDataset(split="train"|"val", sentence_split=…)` ∉ T, train ∉ V; người ký train ⊆ {S01..S04}, val = {S05},
    test = {S06} × T đúng 30; `VSLGHTextDataset` train ∩ (T ∪ V) = ∅, val == V; `Clean10kDataset(exclude_heldout=…)` train ∪ val không mục nào
    `match_heldout` với T ∪ V; số mẫu == `counts_after_split` của preregistration.
- `tests/test_retrained_artifacts.py` (dùng artifact thật; thiếu → skip có lý do — nhưng AC đòi 0 skip): sha256 các artifact == manifest đã
  commit; `STGCNModel(num_classes=len(label_map))` nạp `stgcn_best.pt` strict, label_map từ `stgcn_best.meta.json` == thứ tự `tier1_grouped_classes.txt`;
  `VSLPredictor(model_type="stgcn", stgcn_ckpt="checkpoints/stgcn_best.pt", classes_path=<tier1 classes>, device="cpu")` dự đoán được (test THẬT của
  a4 — bù cho cổng chỉ-tồn-tại, §6 R9); `cslr_best.pt["gloss_vocab_hash"]` == 16 hex đầu sha256(vocab local); `CSLRRecognizer` nạp được,
  `num_classes` == số dòng vocab; ViT5 stage2 nạp bằng `VSLTranslator(model_path=…)`.
  **[LS1] thêm G3 (sau train, từ ID THỰC DÙNG):** `reports/retrain_<D>/k2/{cslr,vit5_stage1,vit5_stage2}_used_ids.json` (commit ở B9): mọi
  `sentence_id` train/val CSLR và ViT5 s2 ∉ T, train ∉ V; ID 10k train/val của s1 ∩ `clean10k_excluded.ids` = ∅ và == tập tính lại local;
  `cslr_best.pt["config"]["sentence_split_sha256"]` == sha256 file split; vocab đã đặt không chứa gloss nào trong `glosses_only_in_test`.

### 3.12 [LS1] Đăng ký trước đánh giá trên 30 câu test (giao thức `sentsplit_v1`)
- **Tập:** S06 × T (30 clip; `select_vslgh_samples(…, "test", split)`); mỗi clip: `gloss_sequence` thô (strip, bỏ rỗng) và `translation` của CHÍNH mẫu.
  Không thêm/bớt mẫu; thiếu keypoint → DỪNG (không bỏ mẫu).
- **Model:** `checkpoints/cslr_best.pt` + vocab đã đặt; `checkpoints/vit5_stage2/best_model` (KHÔNG fallback stage1 — thiếu → exit ≠ 0). sha256 từng file
  ghi JSON và phải == manifest B10.
- **CSLR (Mode B nguồn):** `VSLGHContinuousDataset(split="test", sentence_split=…, conversion_mode="semantic", normalize=True)`, `STGCNBiGRU_CSLR` tham số
  từ `config` trong checkpoint, `ctc_greedy_decode` + `tokens_to_words` như `scripts/extract_cslr_predictions.py:48-84`; CPU; bs 8; không autocast.
- **WER (chính):** `compute_wer(hyps, refs)` (`src/metrics/cslr_metrics.py:169`), hyps = chuỗi gloss dự đoán, refs = gloss THÔ (không mã hóa vocab ⇒ gloss
  ngoài vocab luôn là lỗi; `<unk>` dự đoán không khớp gì). Báo `wer`, S, D, I, `sub_rate/del_rate/ins_rate`, N_ref, N_hyp. Phụ: `wer_vocab_encoded`
  (cách của `evaluate_cslr`, chỉ để đối chiếu với val), `oov{n_ref_tokens_not_in_vocab, ratio}`.
- **BLEU Mode A (oracle gloss → ViT5) / Mode B (CSLR → ViT5):** nguồn = `normalize_vsl_source(gloss thô | gloss dự đoán)`; tham chiếu =
  `normalize_vietnamese_target(translation)`; sinh y hệt `run_v2_cslr_bootstrap.py:47-53` (`max_length=128, padding=True, truncation=True`; `num_beams=4,
  max_length=64`, không sampling; cả 30 một lô; `skip_special_tokens=True`; rồi `normalize_vietnamese_target`); CPU, `model.eval()`, `torch.no_grad()`.
  Điểm = `sacrebleu.corpus_bleu(hyps, [refs])` với `BLEU()` mặc định — tokenize `13a`, smooth `exp`, `lowercase=False` — ghi `signature` của sacrebleu
  và phiên bản `.venv`; phiên bản khác bản trong preregistration → exit ≠ 0.
- **CI:** bootstrap theo câu, **ghép cặp**: `rng = numpy.random.RandomState(42)`; **B = 1000** lần; mỗi lần `idx = rng.choice(30, 30, replace=True)` dùng
  CHUNG cho WER (∑(S+D+I)[idx] / ∑N_ref[idx] × 100, và 3 tỉ lệ S/D/I), BLEU A, BLEU B, delta A − B; **CI 95%** = `numpy.percentile(·, [2.5, 97.5])`
  (nội suy mặc định `linear`). Điểm chính tính trên đủ 30 câu. Báo thêm "CI delta có chứa 0" (mô tả, không tuyên bố kiểm định).
- **So với số cũ (mô tả, không ngưỡng):** chép 27.98 [17.6, 38.39], 23.18 [13.62, 33.7] kèm nguồn `v2_cslr_reliability.json:10-23`; ghi
  "số cũ nằm trong CI mới" có/không; ghi nguyên văn giới hạn §0.2 (rò rỉ của model cũ; 30 câu không ngẫu nhiên; 1 người ký; khác bootstrap: cũ không
  ghép cặp WER và WER cũ đo trên 300 clip). Không kết luận "tốt hơn/kém hơn".
- **Một lần:** `scripts/eval_sentsplit.py --prereg reports/retrain_<D>/preregistration.json --protocol sentsplit_v1 --out reports/retrain_<D>/eval/test_eval.json`
  — đọc mọi tham số trên từ preregistration; đích đã có → exit 2; `code_dirty` → exit 2; commit preregistration không phải tổ tiên HEAD → exit 2.
  JSON: `generated_by{command, git_commit, code_dirty, generated_at_utc, python, torch, transformers, sacrebleu, numpy, device}`, `inputs{sha256 …,
  preregistration_sha256, sentence_split_sha256}`, `protocol` (chép), `per_sample[30]` (sample_id, sentence_id, ref/pred gloss, S/D/I, nguồn/đầu ra
  Mode A/B, tham chiếu), `metrics`, `comparison_to_old`, `limitations`. `--recompute-from <json>` tính lại `metrics` từ `per_sample` (không chạy model).
- **K3 (`--protocol repro_v2`):** tái hiện y nguyên thuật toán `run_v2_cslr_bootstrap.py:29-133` (gồm `np.random.seed(42)` toàn cục, thứ tự rút) trên
  dự đoán của model (i), đầu ra `reports/retrain_<D>/k3_repro/test_eval_repro.json`; MỘT lần; cùng luật exit.
- **[LS2]** `limitations` thêm: "backbone K1 val top-1 đo trên 13 clip — không đủ để đánh giá backbone" và "CSLR v4 train với `--skip-smoke-test` theo
  amendment `ls2` (lý do + bằng chứng: `reports/retrain_<D>/k2_ls2_smoke_diag/`)" (§0B.8, §0B.3). Giao thức đo KHÔNG đổi.

## 4. Chia việc (mỗi bước commit riêng; ghi 13-progress; impact trước khi sửa symbol có sẵn; detect-changes trước commit)

| Bước | Việc | Ước lượng | Phụ thuộc |
|---|---|---|---|
| B0 | Kiểm kê CHỈ ĐỌC → `_work/_plan13_tmp/B0_*.txt`: `git status --porcelain` (mốc), 3 dòng ` D` của người dùng; `git log --all --oneline -S gloss_vocab_canonical`, `-S from_canonical_dataset`, `-S vie_vsl_10k_cleaned`; `.venv` `pip show torch transformers tokenizers sentencepiece safetensors`; đếm dòng 3 CSV `tier1_grouped_*`, mọi `video_id` có npz trong `data/extracted_keypoints/`, tổng dung lượng các npz đó; `git ls-files` cho `data/splits/folds/tier1_grouped_*`, `experiments/stgcn/`; `keypoints_frontal` đủ 4200; đích a4/a5/a6/vocab/cleaned CHƯA tồn tại; nhánh đã push tới HEAD trên GitHub. Tạo `docs/plans/13-progress.md` (sổ GPU, nhật ký detect-changes). **[LS1] ĐÃ XONG.** | 0,75 h | — |
| B1 | Phần B — gỡ Modal (§3.10). **[LS1] ĐÃ XONG** (84c90e4 + 19b7159). | 1 h | B0 |
| B2 | `scripts/retrain_digest.py` + `scripts/build_gloss_vocab_canonical.py` + test (đỏ trước) trong `tests/test_retrain_tools.py`; sinh vocab vào `_work/_plan13_tmp/vocab/` → đếm, sha256 (đặt vào chỗ ở B11). **[LS1] ĐÃ XONG** (0373a90); vocab đầy đủ 372 = tham chiếu cho K3, không đặt vào chỗ. | 1,5 h | B0 |
| **B2a [LS1]** | `src/data/sentence_split.py` + `scripts/make_vslgh_sentence_split.py` + G1 trong `tests/test_sentence_split_guard.py` (đỏ trước); sinh `configs/vslgh_sentence_split_v1.json` (seed 42) → commit. | 1,5 h | B2 |
| **B2b [LS1]** | Tùy chọn `sentence_split`/`exclude_heldout` ở 3 dataset (§3.4f) + test hành vi mặc định không đổi + phần G2 chạy được bằng dữ liệu hiện có (CSLR, ViT5 s2). impact: `VSLGHContinuousDataset`, `VSLGHTextDataset`, `Clean10kDataset`, `_filter_samples`. Hồi quy AC2-06 = mốc 518/1E/1S. | 2 h | B2a |
| **B2c [LS1]** | `build_gloss_vocab_canonical.py --sentence-split/--split` + test; sinh vocab train-only vào `_work/_plan13_tmp/vocab_train/` (lệnh + commit + n_tokens + sha256 + danh sách gloss bị loại vào 13-progress). | 1 h | B2a |
| B3 | Sinh `vie_vsl_10k_cleaned.jsonl` vào `_work/_plan13_tmp/cleaned/` bằng runner trong `_work/` (importlib, đổi biến đích, không sửa script) → đếm dòng, `Clean10kDataset(jsonl_path=…)` train/val, `lf_sha256`. Đóng gói đầu vào Tier 1 vào `_work/_plan13_tmp/src_inputs_tier1/` (3 CSV + classes + đúng các npz cần, không link). **[LS1]** + đếm `Clean10kDataset(exclude_heldout=…)` trên bản `_work`, ghi số bị loại theo lý do. | 1 h | B0, **B2b** |
| B4a | `train.py --seed` + test. impact `main`, `parse_args` (`train.py`). | 0,5 h | B0 |
| B4b | `scripts/archive_retrain_kaggle.py` + test (API giả). | 2 h | B2 (digest) |
| **B4c [LS1]** | `train_cslr.py --sentence-split` (lọc + smoke test lọc + TEST DEFERRED + used_ids), `train_translation_stage{1,2}.py --sentence-split` + test (parse; chạy hàm chọn dữ liệu trên dữ liệu giả, không train; mặc định không đổi). impact `train_cslr` (hàm chính), `run_smoke_test`, `main` của 2 script stage. | 2 h | B2b |
| **B4d [LS1]** | `scripts/eval_sentsplit.py` (§3.12, cả `repro_v2`) + test trên dữ liệu giả. Không chạy trên dữ liệu thật ở bước này. | 2 h | B2a |
| B5 | `scripts/retrain_preregister.py` + test; 2 thư mục kernel (§3.4e, K2 `MODE="preflight"`); sinh + commit `reports/retrain_<D>/preregistration.json`; chạy AC8-a; commit; `git push` nhánh; commit này = commit ghim. **[LS1]** + các khối §3.3 [LS1]; preregister dừng nếu `leak_check` ≠ 0; kiểm commit Lần sửa 1 của kế hoạch là tổ tiên. | 2 h | B2c, B3, B4a, **B4c, B4d** |
| B6 | Lưu trữ đầu vào Tier 1: `archive_retrain_kaggle stage/upload/verify` → dataset `phmvnsm33/vslt-retrain-inputs-tier1`, manifest `reports/retrain_<D>/inputs_tier1_manifest.json`; ĐO tốc độ upload (byte/thời gian) ghi 13-progress. | 0,5 h + chờ | B4b, B5 |
| B7 | Đẩy K2 ở `MODE=preflight` (CPU, không accelerator); theo dõi bằng `kaggle kernels status` thật; tải output; mọi dòng digest/đếm khớp. Lệch → DỪNG (§7.2). | 0,5 h + chờ | B5 |
| B8 | Kiểm ngân sách (§3.7) → đẩy K1 (GPU) → theo dõi → `kaggle kernels output` vào `_work/_plan13_tmp/k1/` (`PYTHONUTF8=1`) → kiểm SHA256SUMS, kiểm hợp lý, đúng 1 lần evaluate_test trong log → commit `reports/retrain_<D>/k1/` (JSON + log, không `.pt`) + `k1_outputs.json`. Ghi sổ GPU. | 0,5 h + chờ | B6, B7 |
| B9 | Đổi K2 sang `MODE="train"` + GPU T4×2 (commit, push, cập nhật commit ghim) → kiểm ngân sách → đẩy → theo dõi → tải output vào `_work/_plan13_tmp/k2/` → kiểm SHA256SUMS, kiểm hợp lý, vocab K2 == vocab B2 (bằng hệt byte), HF snapshot sha preflight == train (khác → chỉ ghi), đúng 1 dòng "PRIMARY TEST EVALUATION" → commit `reports/retrain_<D>/k2/` (JSON + log). Ghi sổ GPU. **[LS1] sửa:** vocab K2 == vocab **B2c** (train-only); log có "LEAK CHECK OK", **0** dòng "PRIMARY TEST EVALUATION", đúng 1 dòng "TEST DEFERRED"; commit thêm 3 `*_used_ids.json`. **[LS2]** Phần 1 đã làm (v3 ERROR, 13-progress B9 phần 1); phần còn lại THAY bằng **B9a–B9f** (§0B.9). | 0,75 h + chờ | B8 |
| **B9a–B9f [LS2]** | Xem bảng §0B.9: B9a ghi nhận v3 → B9b chẩn đoán smoke CPU + quyết định R0/R1/R2 → B9c kernel lưu-từng-job + amendment + kiểm transfer → B9d amendment → B9e ghim + đẩy v4 → B9f tải, kiểm, commit. | 6,25 h + chờ | B9 phần 1 |
| B10 | Lưu trữ đầu ra: dataset `phmvnsm33/vslt-retrain-artifacts` (stgcn_best.pt + meta, cslr_best.pt, cslr_stage1_best.pt, vocab, cleaned jsonl, JSON/log) và `phmvnsm33/vslt-retrain-vit5` (vit5_stage2/best_model, vit5_stage1/best_model) → verify → 2 manifest commit. Trước ViT5: ETA = kích thước / tốc độ đo ở B6; ETA > 3 h → Q2 (§7.1), tiếp B11 với ViT5 từ output đã kiểm. **[LS1]** + file split, `*_used_ids.json`, vocab train-only vào dataset artifacts. **[LS2]** phụ thuộc B9f; + amendment, `smoke_diag.json`, `push_record.json` vào dataset artifacts. | 1 h + chờ upload | B9 **(LS2: B9f)** |
| B11 | Đặt vào chỗ (§3.5) + `tests/test_retrained_artifacts.py` + AC8-b..e. **[LS1]** + G2 đầy đủ, G3. | 2 h | B10 (hoặc B9 + Q2) |
| **B11b [LS1]** | Eval MỘT lần (§3.12) trên cây sạch → commit `reports/retrain_<D>/eval/test_eval.json` + log; chạy `--recompute-from` vào `_work/` và so bằng hệt. | 1 h | B11 |
| B12 | Đánh dấu tài liệu (§3.9). | 1,5 h | B11 **(LS1: B11b)** |
| B13 | Đóng: `docs/progress_log.md` 1 dòng; 13-progress bảng cuối (artifact → job/commit → sha256 → manifest → test); AC0 kiểm cuối. | 0,5 h | B12 |
| **B14 [LS1, TÙY CHỌN]** | K3 (i) theo §0.7: kiểm cổng (GPU + hạn mức) → không lọt: ghi "K3 hoãn" (13-progress + báo orchestrator ghi `docs/usage_ledger.csv`), DỪNG bước. Lọt: commit `MODE="repro_i"` → đẩy → tải → lưu trữ `phmvnsm33/vslt-retrain-repro-i` + manifest → eval `repro_v2` MỘT lần → commit JSON. Ghi sổ GPU. **[LS2]** trước khi lập K3: planner quyết định smoke cho công thức cũ (§0.7 [LS2]). | 1,5 h + chờ | B13 |

B1 độc lập, làm sớm để giảm nhiễu GitNexus. B2/B3/B4a song song được. Job Kaggle chạy nền; coder đợi bằng vòng lặp thưa (≥ 5 phút/lần),
chỉ báo "xong" khi `kaggle kernels status` trả COMPLETE (hoặc ERROR) thật. Theo dõi trạng thái thật sau mỗi lần khôi phục phiên.
**[LS1]** B2b/B2c/B4d song song được sau B2a; B4c sau B2b. Công thêm ~9,5 h (B2a–B2c, B4c, B4d, B11b) + B14 tùy chọn.
**[LS2]** B9c song song được với B9b (mã kernel không phụ thuộc kết quả chẩn đoán; amendment B9d thì phụ thuộc). Công thêm ~6,25 h + chờ kernel.

## 5. Tiêu chí chấp nhận (hợp đồng — coder không đổi; chỉ planner đổi, ghi lý do)
**[LS1]** Lý do mọi thay đổi: §0.8. **[LS2]** Lý do mọi thay đổi: §0B.10.

**AC0 — An toàn cây làm việc.** (a) `git status --porcelain` cuối so mốc B0: chỉ thêm file trong danh sách §3.4/§3.9/§3.11, `reports/retrain_<D>/`,
`docs/plans/13-progress.md`, `kaggle/vsl-retrain-*`; xóa đúng 1 file `src/training/modal_runner.py`; 3 dòng ` D` của người dùng còn nguyên.
(b) `git diff --name-only <mốc B0> HEAD | grep -E '\.(pt|pth|bin|safetensors|npz|npy|jsonl|mp4|onnx)$'` → 0 dòng; không `git add` gì dưới
`data/`, `checkpoints/`, `_work/`. (c) `find checkpoints data/external -type l` → 0; `fsutil reparsepoint query` cho `checkpoints`,
`checkpoints/vit5_stage1`, `checkpoints/vit5_stage2` → "not a reparse point". (d) Không ghi đè file nào: mọi đích kiểm "chưa có" trước khi ghi
(log trong `_work/_plan13_tmp/`). (e) Không file tracked cũ nào bị sửa trừ: `train.py`, các file đánh dấu §3.9 (`git diff --numstat` cột xóa = 0
cho các file md này), `docs/plans/12-khoi-phuc-du-lieu.md` (+1 dòng, 0 xóa).
**[LS1] bổ sung:** (a) danh sách thêm: `src/data/sentence_split.py`, `configs/vslgh_sentence_split_v1.json`, `scripts/make_vslgh_sentence_split.py`,
`scripts/eval_sentsplit.py`, `tests/test_sentence_split_guard.py`. (e) được sửa thêm (chỉ THÊM tham số/nhánh có mặc định None, đã impact):
`src/data/vsl_gh_dataset.py`, `src/translation/dataset.py`, `src/training/train_cslr.py`, `scripts/train_translation_stage1.py`,
`scripts/train_translation_stage2.py`, `scripts/build_gloss_vocab_canonical.py`, `tests/test_retrain_tools.py` (chỉ THÊM test — 15 test B2 giữ
nguyên văn: `git diff` của file này với 0373a90 không xóa dòng nào trong các test cũ). md thêm theo §3.9 [LS1] (`VERIFY.md`, `EVALUATION.md` — cột xóa 0).
**[LS2] sửa cách đo (§0B.5):** (b) và (e) đo trên TẬP FILE của các commit có tiêu đề `^(WIP )?13:` từ mốc B0 tới HEAD (`ac0_commits13.txt`,
`ac0_files13.txt`), không trên `git diff <mốc B0> HEAD` (kế hoạch 11 chạy song song cùng nhánh). (a) dòng porcelain mới ngoài danh sách 13 phải thuộc danh
sách file của kế hoạch song song (in từng dòng + lý do), còn lại → FAIL. Thêm kiểm ngược: mọi commit sửa file chỉ thuộc 13 (danh sách §0B.5) có tiêu đề
`13:`/`WIP 13:`/`state:`. Danh sách thêm (a): `reports/retrain_<D>/{k2_train_v3, k2_ls2_smoke_diag}/`, `reports/retrain_<D>/preregistration_amendment_ls2.json`,
`reports/retrain_<D>/k2/push_record.json`, `scripts/retrain_amendment.py`. `src/training/train_cslr.py` KHÔNG được sửa trong các commit B9a–B9f.

**AC1 — Modal gỡ sạch.** `git grep -n -i -E "modal_runner|run_cslr_on_modal|vslt-data-volume|import modal|from modal|modal\.(App|Volume|Image)" -- src scripts backend tests kaggle configs`
→ 0 dòng; `git grep -n -i modal -- frontend/src` → đúng các dòng có ở mốc B0 (Dictionary.jsx), `git diff <mốc> HEAD -- frontend/` rỗng;
`git ls-files src/training/modal_runner.py` → rỗng; `python -c "import src.training"` exit 0; `tests.test_backend_source_guard` OK.

**AC2 — Vocab.** **[LS1] thay toàn bộ** (bản cũ: "số token so với 372 — khác 372 → DỪNG" — nay chỉ áp cho vocab đầy đủ của K3).
`tests.test_retrain_tools` OK, 0 skip (gồm 15 test B2 không đổi). Vocab đặt vào chỗ = bản train-only B2c: dòng 1 `<blank>`, dòng 2 `<unk>`, LF, 0 byte CR;
`n_tokens` == `preregistration.vocab.n_tokens` (tính bằng code TRƯỚC kernel) và ≤ 372; tập token == {gloss của `select_vslgh_samples(…,"train",split)`}
∪ specials (kiểm lại bằng code ở B11); (vocab đầy đủ B2 − vocab) == `glosses_only_in_val` ∪ `glosses_only_in_test` của preregistration;
sha256 bản B2c == bản K2 dùng (bằng hệt byte); `cslr_best.pt["gloss_vocab_hash"]` == 16 hex đầu sha256(file đã đặt).
K3 (nếu chạy): vocab K3 byte == bản B2 (372, `dd7bc3da…1d11`).

**AC3 — Đầu vào tái lập được.** Bảng preflight K2 (B7) và train K2 (B9): mọi digest/đếm == `preregistration.json`; đếm so tham chiếu:
cleaned 7140, Clean10k 6426/714, VSLGHText 240/30, CSLR 3600/300/300 — **khác tham chiếu → DỪNG (§7.2)** (không chạy GPU). K1: 3 CSV + npz trên
Kaggle == manifest inputs (sha256), mọi `video_id` có npz, guard split của `get_vsl_dataloaders` chạy (không tắt `validate_guards`).
**[LS1] bổ sung:** các số tham chiếu trên áp cho dữ liệu GỐC (trước lọc: Clean10k không `exclude_heldout`, CSLR không `sentence_split`). Sau lọc:
CSLR train/val/test, VSLGHText train/val (== 240/30), Clean10k train/val + số bị loại theo lý do == `counts_after_split`/`clean10k_excluded`;
CSLR test == 30, val == 30 (S05 × V; khác → DỪNG). `leak_check` = 0 ở preregistration, preflight, train.

**AC4 — Đăng ký trước.** Commit chứa `preregistration.json` là tổ tiên của commit ghim mà log K1 và K2 in ra (`git merge-base --is-ancestor`);
log kernel in đúng commit ghim; file không bị sửa sau commit đó (`git log --format=%h -- reports/retrain_<D>/preregistration.json` = 1 dòng).
**[LS1] bổ sung:** commit đưa §0/§3.12 (Lần sửa 1) vào kế hoạch là tổ tiên của commit `preregistration.json`; `configs/vslgh_sentence_split_v1.json`
có đúng 1 dòng `git log` và là tổ tiên commit ghim; `preregistration.evaluation_protocol` == §3.12 (reviewer so từng tham số: B=1000, seed 42,
RandomState, CI 95% phân vị 2.5/97.5 linear, ghép cặp, sacrebleu `13a`/`exp`/không lowercase, beams 4, max_length 64/128, CPU); commit của
`test_eval.json` có preregistration là tổ tiên và `generated_by.git_commit` sạch (`code_dirty` false).
**[LS2] bổ sung:** commit đưa §0B (Lần sửa 2) vào kế hoạch ⊂ commit `smoke_diag.json` ⊂ commit `preregistration_amendment_ls2.json` ⊂ ghim v4
(`git merge-base --is-ancestor`); amendment đúng 1 dòng `git log`; chỉ chứa khóa danh sách trắng `jobs.k2.cslr.train.argv` với giá trị == argv đăng ký +
`["--skip-smoke-test"]`; `decision_rule` trong amendment == `decision` của `smoke_diag.json` và ∈ {R1, R2-PASS}; `preregistration.json` vẫn 1 dòng `git log`.

**AC5 — Kernel & một lần TEST.** `kaggle kernels status` (thật) = COMPLETE cho K1, K2-preflight, K2-train (bản cuối); log K1 có đúng 1 lần chạy
`evaluate_test.py`; log K2 có đúng 1 dòng `PRIMARY TEST EVALUATION`; không lệnh nào chạy ViT5 trên SENT271–300/S06; kiểm hợp lý §3.6 đạt;
sổ GPU: tổng thời gian phiên K1 + K2-train (từ `env.json`) ≤ 2,5 giờ và "STATE + kế hoạch 13" ≤ 10 (nếu không → đã DỪNG đúng §7.2, không vượt).
**[LS1] sửa phần K2:** log K2-train có **0** dòng `PRIMARY TEST EVALUATION`, đúng 1 dòng `TEST DEFERRED (sentence split v1)`, có `LEAK CHECK OK` trước
dòng epoch đầu của CSLR và của ViT5; không tiến trình nào trên Kaggle nạp mẫu S06 × T hoặc chạy ViT5 trên T (grep log + `*_used_ids.json`).
**[LS2] sửa:** "K2-train bản cuối" = v4; v3 ERROR có trong `reports/retrain_<D>/k2_train_v3/` (B9a). Log v4: dòng `AMENDMENT ls2 <commit> applied`; argv CSLR
in ra == argv amendment; 0 dòng `Smoke Epoch`; đúng 1 dòng `[MODEL] Transferred N` với N == `expected_backbone_transfer.transferred_params`; `env.json` `mode`
"train", `commit` == ghim v4, `jobs.<job>.saved` đủ cho job exit 0. Tổng phiên K1 + K2 v3 + K2 v4 (từ `env.json`) ≤ 2,5 giờ; cổng tuần theo §0B.7.

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
  **[LS1]** + `tests.test_sentence_split_guard` (G1 + G2) → OK, 0 skip, 0 failure.
- (d) `scripts/check_restored_data.py --spec docs/recovery/expected_local_data.json --out _work/_plan13_tmp/inventory_after13.json` → exit 0,
  `required_failed` [], các mục a4, a5 ×2, a6, `b3_gloss_vocab_canonical` KHÔNG còn `missing`.
- (e) `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py` → exit 0, PASSED, clip `qipedc_W03292N`.
- Test hỏng sau khi đặt (vd. bản dịch rỗng) → DỪNG; cấm sửa/nới/skip test, cấm thay checkpoint bằng file khác cho test qua (T4 kế hoạch 12).

**AC9 — Tài liệu.** Đủ các dòng `[Kế hoạch 13 — artifact mới]` + dòng đính chính rò rỉ ở đúng các file §3.9 (grep đếm theo file, ghi 13-progress);
`git diff --numstat` cột xóa = 0 cho các file đó; không số liệu mới trong md (mọi số mới chỉ trong `reports/retrain_<D>/*.json`); README liệt kê 3
dataset + 3 manifest.

**AC10 — Quy trình.** Mỗi bước 1 commit (`13: B<n> …`); trước commit có detect-changes (lưu `_work/_plan13_tmp/dc_<bước>.txt`, ghi tóm tắt
13-progress); impact trước khi sửa `train.py` (`main`, `parse_args`); HIGH/CRITICAL được đối chiếu bằng grep và ghi lại.
**[LS1]** impact thêm cho mọi symbol ở §3.4f trước khi sửa.
**[LS2]** impact thêm trước khi sửa `train`, `main` của K2 (và mọi symbol có sẵn khác chạm ở B9c); `tests/test_retrain_tools.py` chỉ THÊM
(`git diff <HEAD trước B9c> -- tests/test_retrain_tools.py | grep -c "^-[^-]"` → 0).

**[LS1] AC11 — Split câu & guard rò rỉ.** (a) `configs/vslgh_sentence_split_v1.json`: T == SENT271..SENT300; |V| = 30, V ⊂ SENT001..SENT270; |Tr| = 240;
rời nhau, phủ 300; tái sinh bằng `scripts/make_vslgh_sentence_split.py --seed 42` vào `_work/` → byte bằng hệt. (b)
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_sentence_split_guard -v` → OK, 0 skip. (c) Đột biến (reviewer/coder, chỉ bản sao
trong `_work/`): thêm 1 ID của T vào danh sách train của bản sao split / vào bản sao `cslr_used_ids.json` / `vit5_stage2_used_ids.json`, thêm 1 cặp
trùng L1 một câu T vào bản sao 10k → test tương ứng FAIL (4 lần, log). (d) G3 trong `test_retrained_artifacts` OK.

**[LS1] AC12 — Đánh giá đăng ký trước, một lần.** `reports/retrain_<D>/eval/test_eval.json` tồn tại, `git log --format=%h -- <file>` = 1 dòng; log
`_work/_plan13_tmp/B11b_eval.log` cho thấy đúng 1 lần gọi; JSON có: `generated_by` (lệnh, commit, `code_dirty` false), sha256 `cslr_best.pt`, vocab,
từng file `vit5_stage2/best_model` (== manifest B10), split, preregistration; `per_sample` đúng 30 mục, đúng 30 `sentence_id` của T, mọi `signer_id` S06;
`metrics.wer` có S, D, I, N_ref và CI 95%; `metrics.bleu_mode_a`, `bleu_mode_b`, `delta` có điểm + CI + `signature`; `protocol` == preregistration;
`comparison_to_old` có nguồn file:dòng và giới hạn §0.2; `.venv/Scripts/python scripts/eval_sentsplit.py --recompute-from <file> --out _work/…` →
`metrics` bằng hệt. Chạy lần 2 vào cùng đích → exit 2.

**[LS1] AC13 — K3 (i) (tùy chọn).** Hoặc (a) 13-progress có "K3 hoãn" kèm số cổng (GPU tuần thật + trần, hạn mức 5h) và orchestrator đã ghi
`docs/usage_ledger.csv`; hoặc (b) K3 COMPLETE, vocab byte == B2, không file nào của K3 trong `checkpoints/` (sha256 `checkpoints/*` không đổi trước/sau B14),
manifest `reports/retrain_<D>/repro_i_manifest.json` đạt như AC6, `k3_repro/test_eval_repro.json` một lần như AC12 (protocol `repro_v2`), sổ GPU ghi
K3 và tổng "STATE + kế hoạch 13" ≤ 10.

**[LS2] AC14 — Smoke test, amendment, lưu từng job.**
(a) `reports/retrain_<D>/k2_ls2_smoke_diag/smoke_diag.json` (1 dòng `git log`, `code_dirty` false) có: `inputs` sha256 == §0B.3; D0 (2 danh sách + `identical`);
D1 (stdout nguyên văn + bool, gọi `run_smoke_test` không sửa); D4-i (`transferred_keys_count`, `transferred_params`, khóa lệch shape); D4-ii `fidelity_ok` true;
D5 số đo epoch 10 và 60; `decision` ∈ {R0, R1, R2-PASS, R2-FAIL} — reviewer tính lại từ chính các trường JSON theo §0B.3 và ra cùng kết quả.
(b) K2 v4 chỉ được đẩy khi `decision` ∈ {R1, R2-PASS}; R0/R2-FAIL → 13-progress ghi DỪNG + lý do, không có commit ghim v4.
(c) `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools tests.test_sentence_split_guard` → OK (skip chỉ là 2 skip có sẵn
"10k cleaned chưa đặt" trước B11), gồm các test [LS2] của §3.11 (đỏ trước có log `_work/_plan13_tmp/B9c_test_red.log`, `B9d_test_red.log`).
(d) Output v4 đã tải: có `vit5_stage1/best_model/*`, `vit5_stage2/best_model/*`, `cslr_best.pt` (nếu CSLR exit 0), mọi file trong `env.jobs.*.saved`
có trong `SHA256SUMS` và sha256 khớp; `jobs.*.missing` rỗng cho job exit 0.
(e) `reports/retrain_<D>/k2/push_record.json`: sha256 file đẩy == sha256 tính lại từ `git show <ghim v4>:…` thay đúng 2 dòng (`MODE`, `PIN_COMMIT`);
metadata đẩy chỉ khác metadata repo ở `enable_gpu`, `kernel_sources`.

## 6. Rủi ro dữ liệu/ML
- R1 **Rò rỉ CSLR (đã biết):** (i) học mọi câu S06 qua người ký khác → số S06 chỉ là "người ký chưa thấy". Ghi ở §3.9; (ii) là backlog.
  **[LS1]** (ii) nay là mặc định; rò rỉ này chỉ còn ở số CŨ và ở K3.
- R2 **Tier 1 split mới:** a4 mới dùng `tier1_grouped_*` (theo bản quay) — khác split của a4 cũ ⇒ số Tier 1 mới không so được với
  `docs/phase6_stgcn.md`/`benchmark_results.json`. Test Tier 1 nhỏ (đếm ở B0) ⇒ không diễn giải mạnh. CSV untracked ⇒ lưu trong dataset inputs (B6).
  **[LS1]** CSV thực ra tracked (B0); vẫn lưu trong dataset inputs để kernel kiểm sha256.
  **[LS2]** Val Tier 1 = 13 clip ⇒ val top-1 của K1 (sanity) gần như không mang thông tin về chất lượng backbone (§0B.8).
- R3 **Lệch byte Windows ↔ Linux:** `.save()`, script clean và có thể `prepare_canonical_*` ghi chế độ văn bản ⇒ CRLF/LF; so file văn bản
  bằng `lf_sha256`, vocab ghi LF cố định. Nếu `dataset_canonical.json` khác CẢ sau chuẩn hóa (vd. `\r` lọt vào chuỗi khi đọc annotation CRLF ở
  Windows) → preflight bắt, DỪNG, CẦN PLANNER (không tự chọn bản nào).
- R4 **Phiên bản thư viện:** model ViT5 lưu bằng `transformers` mới hơn có thể không nạp ở `.venv` → K2 cài đúng phiên bản local; pip thất bại
  ở preflight → DỪNG (CẦN PLANNER), không nâng cấp `.venv` khi chưa hỏi.
- R5 **Base model trôi:** `VietAI/vit5-base` trên HF có thể đổi revision → ghi snapshot sha ở preflight và train; khác → ghi giới hạn.
- R6 **Không tất định trên GPU:** dù seed 42, cuDNN/AMP làm kết quả khác lần chạy — artifact định danh bằng sha256, không bằng "tái lập bit".
  **[LS2]** Hệ quả: smoke CPU (B9b) và smoke GPU có thể ra kết quả khác nhau với cùng mã/seed; ViT5 v4 ≠ ViT5 v3 — chỉ dùng v4 (bản đầu tiên được lưu, §0B.4).
- R7 **Cỡ mẫu:** S06 = 300 mẫu của 1 người ký; ViT5 val 30 câu; Tier 1 test nhỏ ⇒ không kết luận chất lượng từ một lần đo.
  **[LS1]** Test chính thức nay chỉ 30 clip / 1 người ký ⇒ CI rất rộng (CI cũ trên cùng 30 câu rộng ~20 điểm BLEU — `v2_cslr_reliability.json:12-21`);
  val CSLR chỉ 30 clip S05 ⇒ chọn epoch nhiễu (chấp nhận; không dò hyperparameter để tránh quá khớp val).
- R8 **Nguồn gốc/giấy phép:** QIPEDC (giáo dục/nghiên cứu, không nêu quyền phân phối), VSL-GH (MIT theo `docs/data_registry.md:56`, chưa xác minh lại),
  Parallel-Corpus ("open access for research") ⇒ chỉ dataset PRIVATE; không commit npz/jsonl/model.
  **[LS1]** File split chỉ chứa `sentence_id` VSL-GH; preregistration/used_ids chỉ chứa ID 10k, không chép văn bản 10k.
- R9 **Test cổng sai đối tượng:** `test_vsl_predictor_smoke` chỉ kiểm a4 tồn tại rồi nạp a2 — kế hoạch KHÔNG sửa test đó; bù bằng test mới thật sự nạp
  a4 (§3.11). Backlog: cân nhắc làm rõ test cũ (việc của planner sau, cần lý do, không phải để pass).
- R10 **Lệch train–realtime CSLR (đã biết, ngoài phạm vi):** train `normalize=True`, `CSLRRecognizer.predict` không chuẩn hóa vai
  (`docs/plans/07-viec6-che-do.md:83-86`) — không đổi ở đây; kế hoạch 07 xử lý. **[LS1]** Eval §3.12 dùng đường dataset (`normalize=True`) như train ⇒
  số đo là của đường offline, KHÔNG phải realtime.
- R11 **Kế hoạch 07 phụ thuộc artifact:** mọi số/giả định của 07 §2.2 về ViT5/CSLR phải kiểm lại trên artifact mới (cùng công thức (i) nên cấu trúc
  không đổi). Orchestrator báo planner 07 sau khi 13 xong.
  **[LS1]** Công thức đã là (ii) ⇒ cấu trúc ĐỔI: tập con C1 của 07 (`S06_vit5_train/val/heldout`, `cslr_train_occurrences`) dựa trên split cũ
  SENT001–240/241–270 ⇒ 07 phải lập lại phần ViT5/S06 theo `configs/vslgh_sentence_split_v1.json`; S06 × T đã dùng một lần ở B11b — 07 không được
  coi T là "chưa đo" nữa.
- R12 **Repo GitHub không clone được** (riêng tư/nhánh chưa push) → kernel lỗi ngay ở clone (rẻ) → kiểm push ở B0/B5.
- **[LS1] R13 Test không ngẫu nhiên:** T = 30 ID cuối theo thứ tự; có thể lệch chủ đề/độ dài so với Tr/V ⇒ số trên T không khái quát cho "câu mới bất kỳ";
  ghi trong `limitations` của JSON. Giữ T theo quyết định người dùng (để so với số cũ).
- **[LS1] R14 Vocab thu hẹp ở serving:** model mặc định không có lớp cho gloss chỉ xuất hiện ở T ∪ V (danh sách trong preregistration) ⇒ người dùng ký các
  gloss đó sẽ không được nhận. Model "đủ dữ liệu" cho phục vụ = GATE riêng, ngoài kế hoạch.
- **[LS1] R15 Luật khớp 10k chưa hoàn hảo:** L1/L2/gần trùng có thể bỏ sót diễn đạt khác của cùng câu (paraphrase) ⇒ "ViT5 chưa thấy câu T" là "chưa
  thấy theo luật §0.3", ghi đúng như vậy; ngược lại có thể loại thừa cặp 10k ngắn — số bị loại theo lý do ghi trong preregistration.
- **[LS1] R16 Lệch val ViT5 s2 so với cũ:** V khác SENT241–270 ⇒ history s2 mới không so được với `reports/vit5_stage2_history.json`.
- **[LS2] R17 Bỏ smoke trên GPU:** nếu pipeline GPU hỏng theo cách smoke đáng lẽ bắt được, chi phí là tối đa trần K2 (1,75 h) thay vì ~0,2 phút; kết quả vẫn
  được chặn bởi §3.6 (`best_val_wer < 100`, loss hữu hạn) + kiểm CTC mỗi lô + kiểm transfer N. Không có số báo cáo nào phụ thuộc smoke.
- **[LS2] R18 Chẩn đoán CPU khác GPU:** D1–D5 chạy CPU không autocast ⇒ chỉ chứng minh pipeline (dữ liệu → nhãn → CTC → giải mã) học được trên 8 mẫu, không
  chứng minh hành vi số học fp16 trên T4.

## 7. Điểm dừng

### 7.1 CẦN NGƯỜI DÙNG (không chặn; mặc định an toàn)
- **Q1** (§3.8): CSLR (i) hay (ii)? Mặc định (i). Trả lời (ii) → planner lập kế hoạch bổ sung; không đổi các bước đã làm.
  **[LS1] ĐÃ TRẢ LỜI (ii)** (2026-10-02 10:05) — áp dụng ở §0; B0–B2 giữ nguyên.
- **Q2** (chỉ khi B10 đo ETA upload ViT5 > 3 giờ): (a) để upload chạy nền qua đêm; (b) chỉ lưu stage2 (stage1 bỏ khỏi lưu trữ);
  (c) người dùng tự tạo dataset private từ output kernel qua giao diện Kaggle ("New Dataset → Notebook output") rồi coder kiểm bằng `verify`.
  Mặc định khi chưa trả lời: B11–B12 vẫn làm; AC6-vit5 "chờ"; kế hoạch không đóng.
- **Q3** (xác nhận): đặt artifact mới vào đường dẫn mặc định = thuộc quyết định 09:20, không phải GATE. Mặc định: được phép.
- **[LS1]** Không câu hỏi mới. (Nguồn 27.98/23.18 và định nghĩa 30 câu đã tìm thấy — §0.2.)
- **[LS2] Q4** (thông báo, không chặn): đường P (§0B.3) chạy CSLR v4 với `--skip-smoke-test` qua amendment công khai. Mặc định: được phép. Người dùng phủ
  nhận trước B9e → dừng trước khi đẩy v4.

### 7.2 Dừng có điều kiện (coder dừng, ghi 13-progress, báo orchestrator)
1. Ngân sách GPU: `STATE + đã dùng + trần job kế tiếp > 10` giờ, hoặc watchdog cắt job → CẦN NGƯỜI DÙNG. **[LS1]** Riêng K3: không hỏi, ghi "K3 hoãn" (§0.7).
2. Lệch dữ liệu: vocab ≠ 372; cleaned ≠ 7140 hoặc 6426/714; VSLGHText ≠ 240/30; CSLR ≠ 3600/300/300; digest preflight lệch → CẦN PLANNER.
   **[LS1] sửa:** "vocab ≠ 372" chỉ áp cho vocab đầy đủ (K3); vocab train-only ≠ preregistration hoặc > 372 → CẦN PLANNER. Thêm: CSLR test S06 × T ≠ 30
   hoặc val S05 × V ≠ 30; `leak_check` ≠ 0 ở bất kỳ đâu; file split không tái sinh được bằng seed 42; Clean10k loại ≥ 1 mục ở train mà không ghi lý do.
3. Kiểm hợp lý §3.6 không đạt → CẦN NGƯỜI DÙNG (không thử lại seed/cấu hình khác).
4. Test hỏng sau khi đặt artifact (AC8-b) → DỪNG; không sửa test.
5. Cần sửa file ngoài danh sách AC0, cần xóa thêm file/thư mục, slug Kaggle đã tồn tại (exit 5), dataset không xác minh được private (exit 4) → DỪNG.
6. Pip/transformers không cài được đúng phiên bản trên Kaggle (R4) → CẦN PLANNER.
7. **[LS1]** Eval B11b lỗi giữa chừng SAU khi đã sinh dự đoán trên T (vd. hết bộ nhớ ở BLEU) → DỪNG, CẦN PLANNER (không tự chạy lại; ghi log). Lỗi TRƯỚC
   khi nạp mẫu test (thiếu file, code_dirty) → sửa nguyên nhân rồi chạy (chưa tính là "đã chạy test").
8. **[LS1]** Impact HIGH/CRITICAL ở §3.4f mà grep xác nhận có caller thật bị đổi hành vi mặc định → DỪNG, CẦN PLANNER.
9. **[LS2]** B9b: đầu vào lệch sha256, kiểm trung thực D4-ii sai, hoặc `decision` = R0 → CẦN PLANNER; `decision` = R2-FAIL (hoặc hết 30 phút trước epoch 60)
   → CẦN NGƯỜI DÙNG. Không đẩy K2 v4 trong các trường hợp này.
10. **[LS2]** B9c: test có sẵn mâu thuẫn thiết kế (cần sửa test cũ để xanh) → CẦN PLANNER.
11. **[LS2]** K2 v4: CSLR lỗi hạ tầng hoặc transfer N lệch → CẦN PLANNER (không v5 tự động); ViT5 lỗi → CẦN PLANNER; §3.6 không đạt → CẦN NGƯỜI DÙNG (như mục 3).
    CSLR lỗi mà ViT5 đủ → giữ ViT5 v4 (§0B.4), commit phần ViT5, dừng phần CSLR.

### 7.3 Không chạm điểm dừng bắt buộc khác
Không đổi model mặc định Cấp 2 (a2 giữ nguyên; a4 chỉ là fallback khi thiếu a2); không cần dữ liệu người dùng; không đụng thay đổi chưa commit
của người dùng; xóa duy nhất `src/training/modal_runner.py` (tracked, hoàn tác bằng git, theo quyết định 09:20); không xóa dữ liệu/checkpoint/báo cáo cũ.
**[LS1]** CSLR/ViT5 (ii) đặt vào đường dẫn mặc định đang TRỐNG (không thay model nào đang có) — theo Q3 (mặc định "được"); artifact K3 không bao giờ
vào đường dẫn mặc định. Không câu hỏi mới cho người dùng.
**[LS2]** Lần sửa 2 không thêm hành động không hoàn tác: K2 v4 là phiên Kaggle private mới (version mới của cùng slug), không xóa version cũ; amendment là
file mới, preregistration không sửa; không sửa mã train/model.
