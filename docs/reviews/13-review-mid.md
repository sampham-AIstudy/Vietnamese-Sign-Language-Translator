# Review giữa chừng kế hoạch 13 (B0–B4d, trước B5)

- Reviewer: vslt-reviewer (độc lập), 2026-10-02, nhánh `feat/vslt-complete`, HEAD `1a4d6bf`.
- Phạm vi: mã đã viết ở B0–B4d (commit `39e96bf`, `19b7159`, `0373a90`, `0a18183`, `9146f6f`, `059a780`, `b2be827`, `3deee22`,
  `459f282`, `7ecaa25`, `a272df6`, `f7aacc1`, `13f897a`; `modal_runner.py` bị xóa trong `84c90e4`). KHÔNG phải review cuối (không chấm bảng 1–13).
- Đối chiếu: kế hoạch `docs/plans/13-train-lai-checkpoint-thieu.md` (§0 LS1, §3.3, §3.4f, §3.11, §3.12, AC11–AC12) và quyết định Q1=(ii)
  nguyên văn `docs/STATE.md:177-185`.
- File tạm của reviewer: `_work/_rev13_tmp/` (log test, bản sao đột biến, runner đột biến). Không sửa file nào của repo ngoài file này.

## Kết luận: **GO cho B5, CÓ ĐIỀU KIỆN**

Không thấy đường rò rỉ nào làm hỏng train/eval: câu T (SENT271–300) không vào train/val CSLR ở bất kỳ người ký nào, không vào train/val ViT5 s2,
và bị lọc khỏi 10k của s1 theo luật §0.3; vocab chỉ lấy từ train; tập test không được dựng trong tiến trình train. Hành vi mặc định không đổi.
Test 115 OK / 1 skip đúng như kỳ vọng. Có 3 lỗ hổng ở cổng eval (E1–E3) và 1 guard G2 tự quy chiếu (1.A) — không làm hỏng việc train,
nhưng phải sửa trước B11b. Điều kiện bắt buộc của B5: preregistration phải chứa đúng các khóa ở mục 6 (sau B5 không sửa được nữa).

## 1. Rò rỉ (split câu, chọn mẫu, vocab, 10k, backbone, bộ chuẩn hóa)

| Đường | Kết quả | Bằng chứng |
|---|---|---|
| File split | Đúng Q1: T = SENT271–300 cố định, V = `sorted(Random(42).sample(SENT001..270, 30))`, Tr = 240; signer_split S01–S04/S05/S06 | Tự tính lại V bằng Python của `.venv` → True, khớp `configs/vslgh_sentence_split_v1.json`; `git log --format=%h` của file = 1 dòng `0a18183`; `validate_split_dict` (src/data/sentence_split.py) từ chối chồng lấn / thiếu / sai cỡ / T ≠ SENT271..300 / V ngoài pool / signer_split khác |
| CSLR chọn mẫu | train = S01–S04 × Tr, val = S05 × V; mẫu có signer_id↔split lệch → ValueError (không lọt im lặng) | `select_vslgh_samples`, dùng ở `VSLGHContinuousDataset.__init__` (vsl_gh_dataset.py:400-404) |
| CSLR test trong train | Không dựng test dataset/loader khi có `--sentence-split`; in đúng 1 dòng TEST DEFERRED; return trước khối PRIMARY TEST EVALUATION | train_cslr.py:426-433, 475-482, 730-763; test `test_cslr_sentence_split_defers_test_and_records_ids` (0 dòng PRIMARY, 1 dòng DEFERRED, LEAK CHECK trước "CSLR TRAINING STARTED") |
| CSLR leak check runtime | Kiểm T/V/người ký + vocab == gloss train TRƯỚC smoke test; dataset thật dùng phải == ID đã kiểm | train_cslr.py:384-396, 441-444; `cslr_leak_check` (:92-111) |
| Smoke test | Lọc theo split khi có tùy chọn | `run_smoke_test(..., sentence_split=)` :247, 266, 275; test `test_cslr_smoke_test_filters_by_split` |
| Vocab | Train-only (S01–S04 × Tr). Leak check FAIL nếu dùng vocab đầy đủ 372 | `build_tokens_train_only` (scripts/build_gloss_vocab_canonical.py); test `test_cslr_sentence_split_refuses_full_vocab` |
| ViT5 s2 | train = Tr, val = V (từ file split); leak check + vit5_stage2_used_ids.json; KHÔNG fallback base model khi có tùy chọn | diff scripts/train_translation_stage2.py; src/translation/dataset.py:116-118 |
| ViT5 s1 (10k) | Chia 90/10 cũ rồi loại cặp khớp T ∪ V (L1/L2/near-dup, nguồn HOẶC đích, mọi người ký/lần lặp); kiểm lại bằng `text_leak_report` trên đúng mẫu sắp dùng | dataset.py:46-60; diff train_translation_stage1.py; B3: loại 3 train + 1 val (đều câu V, 0 câu T) theo `_work/_plan13_tmp/B3_result.json` |
| Backbone a4 | Tier 1 QIPEDC từ đơn (không chứa clip/câu VSL-GH) → không phải rò rỉ câu. Có thể trùng TỪ với gloss của T (tri thức từ điển, người ký khác) — hợp lệ, nên ghi trong limitations | §0.5 kế hoạch; train_cslr.py:497-504 |
| Bộ chuẩn hóa | Keypoint: chuẩn hóa vai THEO TỪNG MẪU (không thống kê toàn tập); văn bản: luật cố định | vsl_gh_dataset.py:464-474; text_normalizer.py:25-50 |
| ViT5 base | VietAI/vit5-base tiền huấn luyện công khai — không kiểm soát được; không phải rò rỉ từ dự án (ghi giới hạn) | — |

Đột biến guard (bản sao trong `_work/_rev13_tmp/`, không sửa repo):

| # | Đột biến | Kỳ vọng | Thực tế |
|---|---|---|---|
| D0 | G2 với bản cleaned 10k của B3 (env VSLT_GUARD_CLEAN10K trỏ `_work/_plan13_tmp/cleaned/...`) | OK | Ran 4 tests, OK |
| D1 | Bản sao split thêm SENT271 vào train_ids (env VSLT_GUARD_SPLIT) | FAIL | FAILED (errors=1), setUpClass ValueError — đạt |
| D2 | Bản sao 10k + 1 cặp L1 của câu T (PAR_10K_MUT01 = gloss/translation của SENT275) | FAIL (AC11-c) | **Ran 1 test, OK — KHÔNG FAIL**; cặp bị lọc im lặng (excluded: L1 source SENT275) |
| D3 | In-process: `select_vslgh_samples` lén thêm 1 clip S01×SENT271 vào train (`_work/_rev13_tmp/m3_runner.py m3`) | FAIL | G2 CSLR FAIL (SENT271); train_cslr LEAK CHECK FAILED (cslr) — đạt |
| D4 | In-process: `Clean10kDataset` bỏ qua exclude_heldout (`m3_runner.py m4`) | FAIL | stage1 LEAK CHECK FAILED (vit5_stage1); G1 `test_clean10k_exclude_heldout` FAIL — đạt |

**Vấn đề 1.A (TRUNG BÌNH) — G2 10k tự quy chiếu.** tests/test_sentence_split_guard.py:599-610 lọc bằng `match_heldout` rồi kiểm lại bằng chính
`match_heldout` → dữ liệu 10k bị chèn cặp của câu T vẫn PASS (D2). AC11-c đòi FAIL. Cách sửa (sau khi có preregistration): G2 so số mẫu train/val
và tập excluded_ids (+ lý do) với `counts_after_split` / `clean10k_excluded.ids` đã đăng ký → chèn/bớt cặp sẽ FAIL. Điều kiện: B5 PHẢI ghi
ID loại + số đếm (mục 6). Tương tự, G2 nên so sha256 file split với `preregistration.sentence_split.sha256` (§3.11 G2 yêu cầu, hiện chưa có).

**Vấn đề 1.B (THẤP).** `VSLGHTextDataset(split="all", sentence_split=...)` trả cả 300 câu không báo lỗi (dataset.py:116-126), khác với
`VSLGHContinuousDataset` (raise). Không script nào gọi như vậy; nên raise để chặn lỗi sử dụng trong kernel.

## 2. Hành vi mặc định khi không truyền tùy chọn mới — PASS

Diff chỉ thêm nhánh có điều kiện `is not None`:
- `VSLGHContinuousDataset`: không sentence_split → `_filter_samples` + vocab từ toàn bộ canonical như cũ (vsl_gh_dataset.py:400-418);
  test `test_continuous_default_unchanged` (cả LOSO).
- `VSLGHTextDataset`: nhánh cũ SENT001–240/241–270/271–300 nguyên vẹn; test `test_text_default_unchanged`.
- `Clean10kDataset`: chỉ thêm thuộc tính `excluded=[]`, `excluded_ids=[]`; test so với chia 90/10 viết lại độc lập (`old_clean10k_split`).
- `train_cslr`: không khóa mới trong config (checkpoint giữ định dạng), vẫn dựng test và đúng 1 PRIMARY TEST EVALUATION (`test_cslr_default_unchanged`).
  `train.py --seed` mặc định None không gọi seed (`test_main_without_seed_never_seeds`).
- stage1/stage2: không tùy chọn → như cũ (`test_stage1_default_unchanged`, `test_stage2_default_unchanged`).
- Serving: cslr_recognizer.py, translator.py, end_to_end.py, backend/ không đổi (`git diff --numstat bf2ec8a HEAD -- src scripts train.py` chỉ gồm
  các file đã nêu + modal_runner.py bị xóa). Dòng bị xóa trong file cũ (1–4/file) đều là dòng được thay bằng nhánh có điều kiện.

## 3. scripts/eval_sentsplit.py

Đúng §3.12:
- WER: `compute_wer(pred, ref THÔ strip/bỏ rỗng)`; S/D/I từng mẫu bằng `levenshtein_distance`, kiểm tổng == compute_wer (:281-285);
  phụ wer_vocab_encoded, oov (:286-287, 324-327).
- BLEU: `sacrebleu.metrics.BLEU(tokenize, smooth_method, lowercase)` đọc từ protocol; template 13a / exp / False (:99-100, 263-266);
  test `test_bleu_points_equal_sacrebleu_defaults`: điểm == corpus_bleu mặc định, signature có tok:13a, smooth:exp.
- Bootstrap ghép cặp: một `RandomState(seed)`, `rng.choice(n, n, replace=True)`, cùng idx cho WER + S/D/I + BLEU A/B + delta,
  `np.percentile(., [2.5, 97.5])` mặc định linear (:297-313); B = 1000, seed 42 trong template; test tái tính độc lập.
- Sinh ViT5: tokenizer 128/padding/truncation, num_beams 4, max_length 64, do_sample False, một lô, skip_special_tokens, rồi
  normalize_vietnamese_target, CPU, no_grad (:482-495) == run_v2_cslr_bootstrap.py:47-53.
- repro_v2: test chạy nguyên văn đoạn mã cũ (`test_repro_v2_reproduces_old_audit_algorithm`) → khớp.
- Không có số cũ gõ tay trong mã (`test_no_hand_typed_old_numbers_in_source`); số cũ đọc từ v2_cslr_reliability.json kèm file:dòng.
- Kaggle: K2 dùng `train_cslr --sentence-split` (không dựng test), stage1/2 không có bước test → không chạy test trên Kaggle. Kernel chưa viết (B5) —
  B5 phải đảm bảo kernel KHÔNG gọi eval_sentsplit.py, không chạy test_translation_core / ViT5 trên T.

Lỗ hổng:
- **E1 (TRUNG BÌNH) — "chạy một lần" chỉ theo đường dẫn --out.** `run()` chỉ từ chối khi CHÍNH --out đã tồn tại (:540-541); chạy lần 2 vào đường khác
  (vd. _work/x.json) vẫn được khi code sạch và prereg hợp lệ. Sửa: đăng ký `evaluation_output` trong preregistration, script từ chối mọi --out khác;
  thêm file đánh dấu tạo độc quyền (mode "x") cạnh đích TRƯỚC khi đọc clip test (dòng EVAL RUN), để lần chạy hỏng giữa chừng không chạy lại được khi
  chưa có planner (§7.2-7).
- **E2 (TRUNG BÌNH) — so manifest theo TÊN FILE GỐC.** `manifest_sha_index` / `check_against_manifests` dùng basename (:248, 255). Dataset
  vslt-retrain-vit5 (B10) chứa CẢ vit5_stage1/best_model và vit5_stage2/best_model → nếu đặt nhầm stage1 vào checkpoints/vit5_stage2/best_model, mọi sha256
  vẫn có trong manifest dưới cùng basename (config.json, model.safetensors, ...) → kiểm PASS, trái với "KHÔNG fallback stage1" (§3.12).
  Sửa: so theo đường dẫn tương đối đầy đủ (vit5_stage2/best_model/<rel>); cslr_best.pt theo rel_path của artifacts manifest.
- **E3 (THẤP–TRUNG BÌNH) — kiểm đầu vào phụ thuộc chuỗi path.** `check_prereg_inputs` chỉ kiểm mục inputs có path trùng CHÍNH XÁC chuỗi tương đối của
  protocol, bỏ qua im lặng nếu không trùng / không tồn tại (:517-533); thư mục keypoints không bao giờ được kiểm (chỉ file). canonical_json vì vậy có thể
  không được kiểm mà không báo. Sửa: bắt buộc canonical_json nằm trong danh sách đã kiểm (thiếu → exit 3); so test_keypoints_digest (đã tính ở :611-612)
  với giá trị đăng ký trước.
- THẤP: `check_protocol` chỉ khóa các trường thuật toán; seed/B/percentiles/BLEU options đọc từ prereg — chấp nhận vì prereg bị khóa, nhưng B5 cần test
  `preregistration.evaluation_protocol` (trừ inputs) == `protocol_template("sentsplit_v1")`.
- THẤP: `metrics.wer.wer` làm tròn 2 chữ số (từ compute_wer) còn CI không làm tròn; đã có wer_exact — ghi rõ khi báo cáo.

## 4. scripts/archive_retrain_kaggle.py — PASS

Chỉ `api.dataset_create_new(folder, public=False, dir_mode="skip")` (:248); slug tồn tại (status hoặc listed_mine) → 5 (:239-246);
metadata isPrivate True (:171), verify private từ 2 nguồn. Không rmtree/remove/unlink/symlink (grep); staging dở dang để lại, không xóa (:220).
Mọi --src/--staging/--download-dir phải dưới _work/ (`require_under_work` :85-91); từ chối symlink/junction/reparse point (:94-103, 128-141);
ghi bằng open "xb" (`_copy_exclusive` :175-178), manifest mode "x" (:322); manifest trong repo chỉ reports/retrain_<YYYY-MM-DD>/*_manifest.json
(:78, 105-120); restore kiểm hết rồi mới ghi, không ghi đè file khác hash (:377-393). 24 test API giả, gồm `test_source_has_no_forbidden_calls`.
Ghi chú: `private_from_metadata` tái dùng tạo thư mục tạm hệ thống rồi xóa — kế hoạch đã chấp nhận (§3.4c).

## 5. Test — PASS

- `git diff --numstat bf2ec8a HEAD -- tests/` → `1491 0 tests/test_retrain_tools.py`, `614 0 tests/test_sentence_split_guard.py` (chỉ thêm).
  `git diff 0373a90 HEAD -- tests/test_retrain_tools.py` không có dòng xóa nào (đếm dòng bắt đầu bằng "-" = 0) → 15 test B2 giữ nguyên văn.
- Chạy lại: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_retrain_tools tests.test_sentence_split_guard -v`
  → `Ran 115 tests in 74.576s`, `OK (skipped=1)` (log `_work/_rev13_tmp/tests_run1.log`). Skip duy nhất: `test_vit5_stage1_clean10k_no_heldout_match`
  vì data/external/parallel_text/vie_vsl_10k_cleaned.jsonl chưa đặt (đúng kế hoạch: có sau B11; AC8-c đòi 0 skip lúc đó). Khớp kỳ vọng 115 / 1 skip.
- Test có thực chất (không assert luôn đúng), trừ G2-10k (vấn đề 1.A). `test_git_state_on_a_tracked_file` phụ thuộc lịch sử git của file split (1 commit) —
  chấp nhận, trùng với AC4.
- Không chạy lại AC2 31 module (theo yêu cầu).

## 6. B5 phải ghi gì vào preregistration (khóa mà eval_sentsplit.py / kernel / guard đọc)

Bắt buộc (thiếu hoặc sai dạng → eval exit 2/3, hoặc guard không bắt được rò rỉ):
1. `evaluation_protocol` = `protocol_template("sentsplit_v1")` sinh bằng code (không gõ tay); `evaluation_protocol_repro_v2` = template repro_v2.
   Review cuối sẽ so từng tham số với §3.12 (B=1000, seed 42, RandomState, ghép cặp, [2.5, 97.5] linear, 13a/exp/False, beams 4, 64/128, CPU, bs 8).
2. `sentence_split{path: "configs/vslgh_sentence_split_v1.json", sha256, version, seed, python, test_ids, val_ids, n_train_sentences}` với sha256 =
   `load_sentence_split(...).sha256` (sha256 SAU khi đổi CRLF→LF; eval so khóa này ở eval_sentsplit.py:560-563).
3. `libs_local{sacrebleu, numpy}` = đúng chuỗi `importlib.metadata.version` trong .venv (eval so bằng ==, :509-514), cùng torch/transformers/tokenizers/
   sentencepiece/safetensors/rouge_score như §3.3.
4. `vocab{sha256}` = sha256 BYTE THÔ (không phải lf_sha256) của vocab train-only B2c (eval dùng sha256_file, :565-567; gloss_vocab_hash = 16 hex đầu),
   kèm mode, n_tokens, glosses_only_in_val, glosses_only_in_test, test_ref_tokens_total, test_ref_tokens_oov;
   `vocab_full_reference{n_tokens: 372, sha256: đủ 64 hex dd7bc3da…}` cho K3.
5. `inputs` với path đúng chuỗi tương đối dấu "/" như protocol: "data/external/vsl_gh/dataset_canonical.json" + lf_sha256 (không trùng chuỗi → eval bỏ
   qua im lặng, E3); digest gộp keypoints_frontal (4200); vie_vsl_10k(_cleaned).jsonl lf_sha256; Tier 1 CSV/npz.
6. `counts_after_split` (CSLR train/val/test, test == 30, val == 30; VSLGHText 240/30; Clean10k train/val sau loại) và
   `clean10k_excluded{rule_ref, n_train, n_val, by_reason, ids}` — cần cho G2/G3 so khớp (sửa 1.A) và kernel so.
7. `leak_check` = 0 (script dừng nếu ≠ 0) cho CSLR, ViT5 s1, s2, vocab.
8. Đề xuất (để đóng E1/E3): `evaluation_output: "reports/retrain_<D>/eval/test_eval.json"` (eval chỉ nhận đúng đường này) và `test_keypoints_digest`
   (công thức như eval_sentsplit.py:611-612; chỉ hash file, không đưa nội dung vào model — không phải "chạy test").
9. Đề xuất: ghim revision HF của VietAI/vit5-base, hoặc ghi rõ "snapshot sha ghi ở preflight; khác ở train → ghi giới hạn" (R5).
10. `jobs`: lệnh K2 nguyên văn có `--sentence-split configs/vslgh_sentence_split_v1.json` cho CSLR, s1, s2; ghi "TEST DEFERRED"; eval một lần ở local sau B11.

Thứ tự commit (AC4): 4f714c6 (Lần sửa 1) phải là tổ tiên commit preregistration (hiện là tổ tiên HEAD).

## Việc phải làm (xếp theo mức độ)

Trước/trong B5 (bắt buộc, vì preregistration bị khóa sau B5):
1. Preregistration chứa đủ các khóa mục 6 điểm 1–7, đúng dạng (sha split = LF-normalized; vocab = sha byte thô; inputs.path đúng chuỗi tương đối).
2. Kernel K2 (viết ở B5) không gọi eval/test trên T; in "LEAK CHECK OK" trước epoch đầu CSLR/ViT5; assert sha stgcn_best.pt trước CSLR (nếu thiếu backbone,
   train_cslr âm thầm train from scratch — train_cslr.py:497-504).

Trước B11b (khuyến nghị làm ngay trong B5 để commit ghim chứa mã eval cuối cùng):
3. E1: khóa --out theo preregistration + file đánh dấu độc quyền trước khi đọc clip test.
4. E2: so manifest theo đường dẫn tương đối đầy đủ, không theo basename.
5. E3: bắt buộc kiểm canonical_json (+ test_keypoints_digest), không bỏ qua im lặng.
6. 1.A: G2 so số đếm + ID loại 10k + sha split với preregistration để đột biến D2 FAIL (AC11-c).
7. 1.B (thấp): VSLGHTextDataset raise khi split="all" kèm sentence_split.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có. Mọi điểm trên là cài đặt/quy trình trong phạm vi kế hoạch; không đổi tiêu chí GATE.
