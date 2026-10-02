# Kế hoạch 12 — Khôi phục dữ liệu sau sự cố 30/9 23:42

> **CẦN NGƯỜI DÙNG** (không chặn bước B0–B7; chặn việc đóng AC2 = 526/0 skip): mục 8.1 (checkpoint ViT5/CSLR/stgcn_best
> không có bản lưu trữ nào trong repo/_work/Kaggle), mục 8.2 (xác nhận label.csv). Chi tiết + hướng dẫn từng bước ở §8.
>
> Trạng thái file: XONG (planner, 2026-10-01). Nguồn dữ kiện: chỉ file trong repo và `_work/` (dẫn đường dẫn:dòng).

## 1. Mục tiêu & DoD phục vụ

Đưa 3 thư mục bị xóa nội dung (`checkpoints/`, `data/Dataset/`, `data/external/`) về trạng thái đủ để chạy lại bằng chứng
của kế hoạch 06 (AC2 31 module, AC10 ×2, AC5/AC6 tương đương) — mỗi file đặt vào chỗ phải có bằng chứng đúng nguồn
(sha256 theo manifest đã commit, hoặc số khung/kích thước/kết quả chạy lại khớp JSON đã commit). Mục nào không khôi phục
được thì ghi rõ test nào không chạy và vì sao, KHÔNG làm giả file để qua cổng `skipUnless`.

DoD phục vụ: điều kiện V0 của review 06 (docs/reviews/06-review.md, `_work/_rev06_tmp/sec_v0.md`) để reviewer chạy lại
AC2/AC5/AC10; gián tiếp DoD "không bịa số liệu" (mọi bằng chứng tương đương phải tái lập được trên dữ liệu thật).

## 2. Hiện trạng — kiểm kê cái đã mất

### 2.0 Bằng chứng mất và mốc tham chiếu
- `_work/_rev06_tmp/status_before_ac2.txt:20,22` có `?? data/Dataset/` và `?? data/external/`; `_work/_rev06_tmp/status_now.txt`
  không còn hai dòng đó. Glob hiện tại: `checkpoints/**`, `data/Dataset/**`, `data/external/**` → 0 file.
- Mốc "đủ dữ liệu": `_work/_plan06_tmp/b9b_ac2_31.log:1361-1363` (`Ran 526 tests` … `OK`, HEAD 0491877) và
  `_work/_rev06_tmp/ac2_31.log:1360-1362` (`Ran 526` `OK`, chạy 30/9 16:18 trước sự cố).
- Danh sách test phụ thuộc dữ liệu (đã từng skip khi thiếu dữ liệu, cây merge cloud): `_work/_cloud_review_tmp/merge_skips.txt`
  (31 dòng) + lỗi `setUpClass` của `tests.test_translation_core` (`docs/reviews/cloud-2026-09-29-review.md:73-75`).
- KHÔNG mất (đã kiểm bằng Glob, coder kiểm lại ở B0): `reports/**/*.pt` (12 file, gồm H-keepz-360
  `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt` mà `stgcn_h360` dùng — `backend/main.py:123`),
  `reports/alphabet_deploy_2026-09-27/provenance.json` (file TRACKED; STATE.md:12 ghi "mất provenance.json" là nhầm),
  `data/processed/` (qipedc_kps, vslgh_segments…), `data/extracted_keypoints/`, `data/splits/` (gồm `unified/`,
  `recording_groups.csv`), `data/raw_tudienngonngukyhieu/`, `clone/` (cả hai repo còn thư mục `.git`), `_work/`.

### 2.1 Nhóm (a) — checkpoints/
| # | File | Ai dùng (đường dẫn:dòng) | Test trong AC2 cần | Bản sao đã biết |
|---|---|---|---|---|
| a1 | `checkpoints/alphabet_best.pt` | `backend/main.py:587`; `scripts/hand_live_check.py:45` | test_fingerspelling_deployed, _compose, test_status_privacy, test_hand_live_equivalence, test_frontend_contract (TestCrossLanguageBody), test_hand_landmarks_ws (gián tiếp) | `_work/_kaggle_staging/restore_root/checkpoints/alphabet_best.pt`; `_work/_kaggle_staging/vslt-provenance-artifacts/checkpoints__alphabet_best.pt`; Kaggle private `phmvnsm33/vslt-provenance-artifacts` |
| a2 | `checkpoints/stgcn_tier2_indomain.pt` | `backend/main.py:121` (model mặc định); `src/inference/predictor.py:67` | test_ws_live_contract:207, smoke AC10 mặc định, test_vsl_system (nạp thật khi gate a4 qua) | `restore_root/checkpoints/`; `vslt-provenance-artifacts/checkpoints__stgcn_tier2_indomain.pt`; Kaggle private |
| a3 | `checkpoints/stgcn_unified_best.pt` | `backend/main.py:122`; `scripts/report_step4.py:43` | (không test AC2 bắt buộc; giữ cho đủ) | như a2 |
| a4 | `checkpoints/stgcn_best.pt` | `tests/test_vsl_system.py:118-119` (cổng tồn tại; khi có thì `VSLPredictor` vẫn nạp a2 — `src/inference/predictor.py:66-70`); backbone CSLR `src/training/modal_runner.py:103,197` | test_vsl_system.test_vsl_predictor_smoke | **KHÔNG có trong manifest nào, không có sha256 trong repo** (chỉ kích thước 3,88 MB ở `docs/audit/final_status.md:42`, 4,07 MB ở `docs/audit/PHASE4_AUDIT.md:265`). Có thể nằm trên Modal volume `vslt-data-volume` (`src/training/modal_runner.py:38,197-204`, task sync-data) — CHƯA kiểm |
| a5 | `checkpoints/vit5_stage2/best_model/` (+ fallback `vit5_stage1/best_model/`) | `src/translation/translator.py:29-30,61-68` | test_translation_core (setUpClass → FileNotFoundError = ERROR, không phải skip) | **Không lưu trữ ở đâu** (`docs/cloud_reports/viec-A-D-2026-09-29.md:52`: "chỉ có ở local, chưa lưu dataset private nào"); train local (`reports/vit5_stage2_history.json:2` base_model là đường dẫn C:\) |
| a6 | `checkpoints/cslr_best.pt` | `src/translation/cslr_recognizer.py:26,53-54` | test_translation_core (cslr + end_to_end) | **Không lưu trữ** (như a5); vocab hash 16 ký tự nằm TRONG checkpoint (`src/training/train_cslr.py:64-67,345`) |
| a7 | `baseline_bigru.pt`, `transformer_best.pt`, `*.onnx`, `*_smoke.pt` (Phase 6/13) | `src/inference/predictor.py:42-43`, `src/export/*` | không | Không lưu trữ; không cần cho AC2 → ngoài phạm vi (ghi vào inventory là "mất, không khôi phục") |

### 2.2 Nhóm (b) — data/external/
| # | Thư mục | Nội dung mong đợi (nguồn số liệu) | Test/lệnh cần |
|---|---|---|---|
| b1 | `hauuto_raw/raw/raw/<signer>/<telex>_<signer>_<A\|B>_<n>.mp4` | 640 clip, 4 người ký, 34 lớp (`docs/data_registry.md:45`); `a_hau_A_001.mp4` + facts khung/fps/kích thước trong `reports/e2e_2026-09-30_r4/fingerspell_default.json:31-33`; n_frames 8 clip trong `reports/fingerspell_live_2026-09-29/hand_live_check.json` | test_hand_landmarks_ws:40,190; test_hand_live_equivalence; smoke AC10 bước 5 (`scripts/smoke_test_phase12.py:41`); e2e 06 |
| b2 | `alphabet_hands_kaggle/alphabet_hands/` (`manifest.csv`, npz landmark, `tasks.csv`) | output kernel PRIVATE `phmvnsm33/vsl-extract-alphabet` (`kaggle/vsl-extract-alphabet/extract_alphabet.py:22-23`); 682 dòng dự đoán = 636 hauuto + 46 qipedc (`docs/reviews/06-review.md:156-157`; `provenance.json` trained_on.clips 636, V6 k=n=46) | test_fingerspelling_api:33,190; test_fingerspelling_deployed:32; test_hand_landmarks_ws:39; hand_live_check |
| b3 | `vsl_gh/` (`keypoints_frontal/*.npy` 4.200, `annotations/` 4.206, `dataset_canonical.json`, `splits/`, `dataset_loso_s0*.json`, `gloss_vocab.txt`, `trans_vocab.txt`, `gloss_vocab_canonical.txt` 372 token) | `docs/data_registry.md:58-80`, `docs/vsl_gh_dataset.md:16-19`, `reports/vsl_gh_validation.json` | KHÔNG trong AC2, trừ `gloss_vocab_canonical.txt` (test_translation_core qua CSLR). Cần cho kế hoạch 07 (Ký câu) và `tests/data/test_vsl_gh_dataset.py` (ngoài AC2) |
| b4 | `parallel_text/vie_vsl_10k.jsonl` | 9.405 cặp (`docs/data_registry.md:93`; `reports/translation_corpus_validation.json:8-12`) | không trong AC2; cần cho train ViT5 lại (nếu có) |

### 2.3 Nhóm (c) — data/Dataset/
| # | Đường dẫn | Mong đợi | Test/lệnh cần |
|---|---|---|---|
| c1 | `data/Dataset/Videos/*.mp4` (QIPEDC) | 4.362 video (`docs/data_registry.md:21`); 4.363 file / 2.764 MB cả thư mục (`docs/audit/PHASE4_AUDIT.md:262`); `num_frames` từng video ở `data/splits/recording_groups.csv` (cột 4, đo bằng `CAP_PROP_FRAME_COUNT` — `scripts/build_recording_groups.py:36-37`); width/height ở `data/splits/unified/*.csv` | test_live_harmonized_equivalence (`scripts/live_clip_sample.py:17-32`), test_hand_live_equivalence (2 clip qipedc_D0489, qipedc_D0490B), smoke AC10 bước 4 (clip đã chọn ở mốc: `qipedc_W03292N` — `_work/_rev06_tmp/smoke_default.log:38`, `smoke_h360.log:62`), e2e word (`D0120T.mp4`, facts ở `reports/e2e_2026-09-30_r4/word_default.json:31-37`) |
| c2 | `data/Dataset/Labels/label.csv` | người dùng chuyển từ `data (2)/Dataset/Labels/label.csv` (STATE.md:172-173); bản tracked vẫn còn trong git HEAD (` D "data (2)/Dataset/Labels/label.csv"`) | `scripts/build_recording_groups.py:30`, `scripts/analyze_raw_dataset.py:3` — không test AC2 |

### 2.4 Bẫy phát hiện khi kiểm kê (ảnh hưởng tiêu chí)
- T1. Thư mục rỗng ≠ thiếu: `live_clip_sample.available()` chỉ kiểm `isdir(VIDEOS_DIR)` (`scripts/live_clip_sample.py:21-22`)
  và `hand_live_check` kiểm `os.path.exists(QIPEDC_VIDEO_DIR)` (`tests/test_hand_live_equivalence.py:29-30`). Với
  `data/Dataset/Videos` rỗng nhưng tồn tại, test KHÔNG skip mà lỗi (`rng.choice(0, 8)`) hoặc chọn mẫu khác. ⇒ khôi phục
  một phần cũng nguy hiểm: mẫu được chọn phụ thuộc "file nào có trên đĩa" (`live_clip_sample.py:28-32`,
  `hand_live_check.py:82-92`). Bộ video QIPEDC và hauuto phải ĐỦ thì mẫu mới trùng mốc. Không chạy AC2 06 giữa chừng
  để "xem thử" khi bộ video chưa đủ (kết quả không có nghĩa).
- T2. `data/Dataset/` và `data/external/vsl_gh|parallel_text` KHÔNG bị gitignore (chỉ `*.mp4`, `*.npz`,
  `alphabet_hands_kaggle/`, `hauuto_raw/`, `checkpoints/` — `.gitignore:32-35,62,70-71`). Như trước sự cố chúng hiện
  `??`. Kế hoạch này KHÔNG sửa `.gitignore` (giữ baseline `git status` so được với `status_before_ac2.txt`); cấm `git add`
  bất kỳ đường dẫn nào dưới `data/`, `checkpoints/`.
- T3. `scripts/archive_private_kaggle.py restore` đòi `--download-dir` NGOÀI repo (`scripts/archive_private_kaggle.py:378`,
  `scripts/archive_step4_kaggle.py:79-81`), mâu thuẫn quyết định 2026-09-30 23:45 (file tạm chỉ trong `_work/`). ⇒ Bước
  checkpoint dùng bản ĐÃ TẢI SẴN trong `_work/_kaggle_staging/` (kiểm sha256 lại), không gọi `restore`; chỉ khi bản trong
  `_work` sai hash mới tải lại bằng `kaggle datasets download -d <slug> -p _work/_plan12_tmp/dl_<slug>` (CLI có sẵn) rồi kiểm.
- T4. `test_vsl_predictor_smoke` chỉ dùng `stgcn_best.pt` làm cổng tồn tại; tạo file giả/sao chép file khác vào tên đó để
  test chạy là GIAN LẬN — cấm.

## 3. Nguồn khôi phục & cách kiểm đúng (thiết kế)

| # | Nguồn | Cách lấy | Cách kiểm đúng (phải đạt trước khi đặt vào chỗ) | Khôi phục được? |
|---|---|---|---|---|
| a1–a3 | `_work/_kaggle_staging/restore_root/checkpoints/` (và bản phẳng trong `vslt-provenance-artifacts/`, `restore_dl*/`) | copy, không ghi đè | sha256 == `reports/private_archive_2026-09-28/kaggle_archive_manifest.json` (`:24` a6311820…b708a2, `:36` 53c34cba…fe2c826, `:48` 93063323…aabb); a1 thêm == `provenance.json:11`; a3 thêm == `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json:162` (cùng hash baseline) | CÓ (không cần mạng) |
| a4 | (1) lịch sử git (`git log --all -- checkpoints/`, `git rev-list --all --objects`); (2) Modal volume `vslt-data-volume` (CẦN NGƯỜI DÙNG); (3) bản sao riêng của người dùng | — | không có hash tham chiếu ⇒ chỉ kiểm được: tải được bằng `torch.load`, kích thước so `docs/audit/final_status.md:42`, số lớp 50 (Tier 1). Nhãn trong inventory: "nguồn: …, CHƯA xác minh bằng hash" | CHƯA BIẾT → §8.1 |
| a5, a6, vocab | như a4 (Modal volume có thể có `gloss_vocab_canonical.txt` theo `modal_runner.py:200-204`) | — | a6 ↔ vocab: 16 hex đầu sha256(vocab) == `vocab_hash` lưu trong a6; a5: không có hash ⇒ chỉ kiểm nạp được + `reports/vit5_stage2_history.json` khớp cấu hình | CHƯA BIẾT → §8.1 |
| b1 | Kaggle CÔNG KHAI `hauuto/vietnamese-sign-language-alphabet` (`docs/CLOUD.md:46`, `docs/data_registry.md:43`) | `kaggle datasets files` (ghi danh sách + tổng dung lượng + version), rồi `kaggle datasets download -d hauuto/vietnamese-sign-language-alphabet -p _work/_plan12_tmp/dl_hauuto --unzip`, rồi `mv` cây `raw/raw/` vào `data/external/hauuto_raw/raw/raw/` | đủ 640 mp4 / 4 thư mục người ký; facts của `a_hau_A_001.mp4` == JSON e2e; mạnh nhất: chạy lại hand_live_check (B7) bằng hệt JSON đã commit | CÓ (nếu dataset upstream chưa đổi) |
| b2 | output kernel PRIVATE `phmvnsm33/vsl-extract-alphabet` | `kaggle kernels output phmvnsm33/vsl-extract-alphabet -p _work/_plan12_tmp/k_alphabet`, rồi `mv alphabet_hands/` vào `data/external/alphabet_hands_kaggle/alphabet_hands/` | `manifest.csv` có đủ sample_id của 682 dòng `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv` (636 hauuto + 46 qipedc); chạy lại `alphabet_ckpt_provenance.py --out _work/...` khớp `provenance.json` (bỏ `generated_by`); hand_live_check B7 khớp cột `kaggle_npz_vs_local_offline` | CÓ (nếu output kernel còn là bản chạy cũ — kiểm bằng các so khớp trên) |
| b3 | `clone/Vietnamese-Sign-Language-Translation/.git` (repo còn `.git`; thư mục `data/keypoints/` đã bị xóa từ đợt audit — `docs/audit/PHASE4_AUDIT.md:256`) | `git -C clone/... rev-parse HEAD` phải == `6c351e63…` (`docs/data_registry.md:55`); `git -C clone/... archive HEAD data > _work/_plan12_tmp/vslgh_head.tar` (chỉ đọc repo clone) rồi giải nén vào `_work/_plan12_tmp/vslgh_src/`; nếu keypoints là con trỏ LFS hoặc thiếu object → `git clone` upstream vào `_work/_plan12_tmp/vslgh_upstream` và checkout đúng commit | chạy `prepare_canonical_vsl_gh.py` với nguồn/đầu ra báo cáo tách (B8) → báo cáo mới bằng `reports/vsl_gh_validation.json` (bỏ khóa thời gian/đường dẫn nếu có); 4.200 npy, hash_verification 4200/4200 | CÓ cho keypoints/annotations/dataset_canonical; `gloss_vocab_canonical.txt` KHÔNG có script sinh trong repo (grep chỉ thấy nơi đọc) → theo a6 |
| b4 | `clone/Parallel-Corpus-Vie-VSL/{VSL10k,Vie10k}.txt` (còn trên đĩa) | `python scripts/prepare_canonical_translation.py` (ghi `data/external/parallel_text/vie_vsl_10k.jsonl` và GHI ĐÈ `reports/translation_corpus_validation.json` tracked) | trước chạy: file report sạch trong git; sau chạy: `git diff --exit-code reports/translation_corpus_validation.json` rỗng (10000/595/9405/3764/3774). Khác → `git checkout -- reports/translation_corpus_validation.json`, xóa jsonl vừa sinh, DỪNG | CÓ (tái tạo tất định từ nguồn còn trên đĩa) |
| c1 | Kaggle CÔNG KHAI `aresusayhi/vsl-vietnamese-sign-languages` (= QIPEDC; `docs/CLOUD.md:46`; mọi kernel trích QIPEDC dùng nó — `kaggle/vsl-extract-qipedc/kernel-metadata.json:10`) | `kaggle datasets files` (danh sách, dung lượng, version) → kiểm chỗ trống đĩa → `kaggle datasets download … -p _work/_plan12_tmp/dl_qipedc --unzip` (chạy nền, log trong `_work/_plan12_tmp/`) → `mv` thư mục Videos vào `data/Dataset/Videos/` | mọi `file_name` của `recording_groups.csv` có mặt; `CAP_PROP_FRAME_COUNT` == `num_frames` cho MỌI dòng; width/height == `data/splits/unified/{train,val,test}.csv` cho mọi dòng qipedc; facts `D0120T.mp4` == JSON e2e; B7: segment_check + smoke chọn lại đúng mẫu mốc | CÓ (nếu dataset upstream chưa đổi) |
| c2 | blob git HEAD `data (2)/Dataset/Labels/label.csv` | `git show "HEAD:data (2)/Dataset/Labels/label.csv" > data/Dataset/Labels/label.csv` (chỉ khi đích chưa có); KHÔNG đụng ` D` của người dùng ở `data (2)/` | so với label.csv trong gói QIPEDC Kaggle (nếu có) — chỉ báo khác/giống | CÓ (nội dung = bản tracked; bản người dùng có sửa riêng hay không: §8.2) |

Không cần trích lại landmark (data/processed còn nguyên; b2 là output kernel đã có) ⇒ **0 GPU-giờ Kaggle** cho kế hoạch này.
Train lại ViT5/CSLR/stgcn_best (nếu người dùng chọn ở §8.1) là KẾ HOẠCH RIÊNG, không nằm ở đây.

### 3.1 Công cụ kiểm: `scripts/check_restored_data.py` (mới, CHỈ ĐỌC)
- Input: `--spec docs/recovery/expected_local_data.json` (coder viết từ bảng §2–§3, mỗi mục ghi `expect_source` = file:dòng
  trong repo, không gõ số không nguồn), `--out <json>` (chỉ cho phép trong `_work/` hoặc `reports/data_recovery_2026-10-01/`),
  `--only <mục…>` và `--dir-override <mục>=<thư mục>` (để kiểm bản giải nén trong `_work/` TRƯỚC khi chuyển vào chỗ; override
  chỉ nhận thư mục trong `_work/`).
- Mỗi mục spec thuộc một loại: `sha256` (file, hash mong đợi), `count` (glob, số mong đợi), `video_frames` (csv tham chiếu,
  cột tên file/số khung/width/height, thư mục video), `csv_ids` (file csv + cột id phải có trong manifest), `exists_only`
  (không hash — dùng cho a4–a6, ghi `verified: "no_reference_hash"`), có cờ `required`.
- Output JSON: `generated_by{command, git_commit, code_dirty}`, theo mục: `status ∈ {ok, missing, mismatch, unverifiable}`,
  số đếm, danh sách tối đa 20 phần tử lệch (KHÔNG ghi tên clip hauuto theo người ký vào file commit — chỉ đếm; danh sách đầy
  đủ chỉ vào `_work/`). Mã thoát: 0 nếu không có `missing|mismatch` ở mục `required: true`; 3 nếu có; 2 nếu lỗi tham số.
- Không ghi/sửa/xóa file dữ liệu nào; không mạng; không import `backend`; không đụng `src/data/*` (không phải module tiền
  xử lý; không có luồng train/realtime nào đi qua nó). Đếm khung bằng `cv2.VideoCapture(...).get(CAP_PROP_FRAME_COUNT)`
  đúng như `scripts/build_recording_groups.py:36-37` (cùng cách đo với số tham chiếu).

## 4. Quy tắc an toàn (bắt buộc mọi bước)
1. Chỉ GHI vào: `checkpoints/`, `data/Dataset/`, `data/external/` (đang rỗng), `_work/_plan12_tmp/`, và các file tài liệu/
   script/test liệt kê ở §5. Không ghi vào `clone/`, `data (2)/`, `data/processed/`, `data/splits/`, `reports/` (ngoại trừ
   thư mục mới `reports/data_recovery_2026-10-01/` và trường hợp b4 có kiểm diff).
2. Không ghi đè: trước mỗi lần đặt file kiểm đích chưa tồn tại (`[ -e target ] && dừng`); dùng `cp -n`/`mv -n` và kiểm lại
   sha256 sau khi đặt. Đích đã có mà khác hash → DỪNG, không xóa.
3. Kiểm sha256/số khung TRƯỚC khi đặt vào chỗ (trên bản trong `_work/`), và kiểm lại SAU khi đặt (B7 checker).
4. Không commit dữ liệu: cấm `git add` dưới `data/`, `checkpoints/`, mọi `.pt/.npz/.npy/.mp4/.jsonl`. Không sửa `.gitignore`.
   Trước mỗi commit: `git diff --cached --name-only` chỉ chứa file §5 cho phép.
5. Không tạo junction/symlink/hardlink/worktree; không `rm -rf`, không `git worktree`, không `git clean`. Xóa file tạm trong
   `_work/_plan12_tmp/` chỉ sau khi `find _work/_plan12_tmp -type l` rỗng và `fsutil reparsepoint query` không báo link
   (luật 2026-10-01, STATE.md:130-132). Dọn `_work/_plan12_tmp/dl_*` (bản zip/giải nén đã chuyển) là tùy chọn, làm cuối.
6. Mạng: chỉ `kaggle` CLI trong `.venv` (đã dùng trước đây, `kaggle==2.2.4`) và `git clone` upstream VSL-GH khi B8 cần.
   Không chạy script tải từ mạng khác; không phần mềm khôi phục file (quyết định 2026-10-01 19:22). Không in KAGGLE_KEY.
7. Không đổi model mặc định, không sửa test cũ, không sửa `backend/`, `src/`, `frontend/`.
8. Chạy nặng duy nhất là tải (nền). Không train. Không kernel Kaggle nào phải chạy.
9. Thay đổi chưa commit của người dùng (` D` 3 file, mọi `??`) giữ nguyên; `git status --porcelain` trước/sau từng bước
   lưu vào `_work/_plan12_tmp/B<n>_status_{before,after}.txt`.

## 5. Chia việc (coder)

File được thêm/sửa trong git: `docs/plans/12-progress.md` (A/M), `docs/recovery/expected_local_data.json` (A),
`scripts/check_restored_data.py` (A), `tests/test_check_restored_data.py` (A), `reports/data_recovery_2026-10-01/*.json` (A),
`scripts/prepare_canonical_vsl_gh.py` (M, chỉ B8, chỉ thêm tham số), `docs/progress_log.md` (M, chỉ thêm). Không file nào khác.

| Bước | Việc | Phụ thuộc | Ước lượng | Commit |
|---|---|---|---|---|
| B0 | Ảnh chụp ban đầu (chỉ đọc): `git status --porcelain`, `git rev-parse HEAD`, liệt kê 3 thư mục (0 file), chỗ trống ổ đĩa (`df -h .`), `kaggle --version`, `kaggle datasets list --mine` (chỉ kiểm credential), `git log --all --oneline -- checkpoints/ "*.pt"` và `git rev-list --all --objects \| grep -E " checkpoints/"` (a4–a6 có trong lịch sử không), `git -C clone/Vietnamese-Sign-Language-Translation rev-parse HEAD` + `status --porcelain \| head` + `ls-files data/keypoints \| wc -l` + `lfs ls-files` (nếu có lfs), tương tự cho Parallel-Corpus (so commit `f57558c3…`, `docs/data_registry.md:89`). sha256 của 12 `reports/**/*.pt` so 2 manifest (chỉ đọc). Ghi kết quả vào `12-progress.md` | — | 0,5 h | `12: B0 kiểm kê ban đầu` |
| B1 | TDD: `tests/test_check_restored_data.py` (fixture tạm: file + sha, glob đếm, csv id, video nhỏ sinh bằng `cv2.VideoWriter` trong temp dir — chỉ để kiểm hàm đếm khung, không phải dữ liệu) → đỏ; viết `scripts/check_restored_data.py` → xanh; viết `docs/recovery/expected_local_data.json` từ §2–§3 (mỗi mục `expect_source`). `impact`/`detect-changes` theo CLAUDE.md. Chạy checker → `_work/_plan12_tmp/inventory_before.json` (mong đợi: mọi mục `required` = missing) | B0 | 1,5–2 h | `12: B1 checker chỉ đọc + spec` |
| B2 | Checkpoint a1–a3 từ `_work/_kaggle_staging/restore_root/checkpoints/`: sha256 3 file == manifest → `cp -n` vào `checkpoints/` → sha256 lại. Nếu bản `_work` sai: thử bản phẳng `vslt-provenance-artifacts/checkpoints__*.pt`; vẫn sai → `kaggle datasets download -d phmvnsm33/vslt-provenance-artifacts -p _work/_plan12_tmp/dl_prov --unzip`. Chạy nhanh: `-m unittest tests.test_status_privacy tests.test_fingerspelling_compose -v` (ghi số skip còn lại) | B1 | 0,5 h | chỉ `12-progress.md` |
| B3 | c2: `git show "HEAD:data (2)/Dataset/Labels/label.csv"` → `data/Dataset/Labels/label.csv` (đích chưa có); sha256 ghi vào progress | B1 | 0,25 h | progress |
| B4 | b2: `kaggle kernels output phmvnsm33/vsl-extract-alphabet -p _work/_plan12_tmp/k_alphabet` (ghi log kernel + danh sách file); kiểm sample_id ↔ nested_predictions.csv (682); `mv -n` vào chỗ; chạy `scripts/alphabet_ckpt_provenance.py --out _work/_plan12_tmp/provenance_rerun.json` và so dict (bỏ `generated_by`) với `reports/alphabet_deploy_2026-09-27/provenance.json` | B2 | 1 h | progress |
| B5 | b1: `kaggle datasets files hauuto/vietnamese-sign-language-alphabet` (ghi version, tổng dung lượng) → tải nền vào `_work/_plan12_tmp/dl_hauuto` → kiểm 640 mp4/4 người ký + facts `a_hau_A_001.mp4` (checker `--dir-override`) → `mv -n` | B1 | 0,5 h làm + thời gian tải | progress |
| B6 | c1: `kaggle datasets files aresusayhi/vsl-vietnamese-sign-languages` (version, dung lượng, cấu trúc) → so chỗ trống ổ (cần ≥ 2 × dung lượng zip + 1 GB; không đủ → DỪNG báo) → tải nền, đo tốc độ 5 phút đầu, ghi ETA vào progress → giải nén trong `_work` → checker mục c1 với `--dir-override` PHẢI ok → `mv -n` thư mục Videos → so label.csv của gói với c2 (chỉ báo) | B1 | 1–2 h làm + thời gian tải | progress |
| B7 | Kiểm tổng (§6 AC3–AC4): checker → `reports/data_recovery_2026-10-01/inventory_after.json`; hand_live_check, live_segment_check chạy lại vào `_work`; smoke ×2; AC2 31 module; `npm test`. Ghi bảng test còn skip/lỗi + lý do | B2–B6 | 1,5 h | `12: B7 inventory sau khôi phục + kết quả kiểm` |
| B8 | (không chặn AC2) b4 theo §3 (diff report phải rỗng). b3: thêm `--source-clone` và `--report-out` vào `scripts/prepare_canonical_vsl_gh.py` (mặc định giữ nguyên hành vi; impact trước khi sửa; test nhỏ cho parse tham số), chạy với nguồn `_work/_plan12_tmp/vslgh_src` và report vào `_work`, so với `reports/vsl_gh_validation.json` | B7 | 1,5 h | `12: B8 tái tạo vsl_gh/parallel_text` |
| B9 | Cập nhật `12-progress.md` (bảng cuối: mục → nguồn → trạng thái), 1 dòng `docs/progress_log.md`; báo orchestrator mục §8 còn mở | B7 (B8 nếu làm) | 0,25 h | `12: B9 đóng` |

Thời gian tải: KHÔNG ước lượng ở đây (không có số đo tốc độ đáng tin trong repo; skill vsl-cloud-jobs chỉ ghi "~100 KB/s"
cho upload). Coder đo ở B5/B6 và ghi ETA thật; nếu ETA > 3 h báo orchestrator để xếp lịch (không phải điểm dừng người dùng).
B5 và B6 có thể chạy tải song song (nền); B7 chỉ bắt đầu khi B2–B6 xong.

## 6. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder không được đổi)

**AC0 — An toàn.** Mọi `B<n>_status_after.txt` khác `before` CHỈ ở các dòng `?? data/Dataset/`, `?? data/external/`,
`?? docs/recovery/…`/file §5 chưa commit; ` D` của người dùng còn nguyên 3 dòng. `git log` của kế hoạch 12 không chứa đường
dẫn dưới `data/`, `checkpoints/`, không file `.pt/.npz/.npy/.mp4/.jsonl` (`git diff --name-only <B0> HEAD | grep -E
'^(data|checkpoints)/|\.(pt|npz|npy|mp4|jsonl)$'` rỗng). `find checkpoints data/Dataset data/external -type l` rỗng và
`fsutil reparsepoint query` trên 3 thư mục gốc báo không phải reparse point.

**AC1 — Checker (B1).** `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_check_restored_data -v` → OK,
0 skip; có test cho: sha khớp/khác, file thiếu, đếm glob, khung video khớp/khác, csv id thiếu, mục `unverifiable`, mã thoát
0/3/2, từ chối `--out`/`--dir-override` ngoài phạm vi cho phép, không ghi file nào ngoài `--out` (so listing temp dir
trước/sau).

**AC2 — Checkpoint (B2).** sha256 sau khi đặt:
- `checkpoints/alphabet_best.pt` = `a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2`
- `checkpoints/stgcn_tier2_indomain.pt` = `53c34cba43854c3e9820495bba3f93ffe18b5e1cb87ef44278a188ccafe2c826`
- `checkpoints/stgcn_unified_best.pt` = `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb`
- 12 `reports/**/*.pt` = sha256 trong 2 manifest (không file nào bị ghi).
(nguồn: `reports/private_archive_2026-09-28/kaggle_archive_manifest.json:24,36,48`; `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`)

**AC3 — Dữ liệu (B4–B6), checker `reports/data_recovery_2026-10-01/inventory_after.json` exit 0, trong đó:**
- c1: số mp4 trong `data/Dataset/Videos` ≥ số dòng `recording_groups.csv`; 0 `file_name` thiếu; 0 lệch `num_frames`; 0 lệch
  width/height với `data/splits/unified/*.csv`. `D0120T.mp4`: frames 113, fps 29.97002997002997, 1280×720
  (`reports/e2e_2026-09-30_r4/word_default.json:33-36`).
- b1: 640 mp4 trong 4 thư mục người ký (`docs/data_registry.md:45`); facts `a_hau_A_001.mp4` == `reports/e2e_2026-09-30_r4/fingerspell_default.json:32+`.
- b2: mọi sample_id của `nested_predictions.csv` (682) có trong `manifest.csv`; `provenance_rerun.json` == `provenance.json`
  (so dict, bỏ `generated_by`), đặc biệt `verdict` và V6 k=n=46. Khác ở bất kỳ khóa nào → DỪNG, CẦN PLANNER.
- c2: `data/Dataset/Labels/label.csv` sha256 == sha256 của blob `HEAD:data (2)/Dataset/Labels/label.csv`.

**AC4 — Tái lập bằng chứng (B7), mỗi lệnh 1 lần, output vào `_work/_plan12_tmp/`:**
- `git diff --name-only 0491877 HEAD -- backend src scripts` phải rỗng hoặc chỉ `scripts/check_restored_data.py`
  (và `scripts/prepare_canonical_vsl_gh.py` nếu B8 đã làm — vì vậy chạy AC4 TRƯỚC B8).
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0 --out _work/_plan12_tmp/hand_live_check_rerun.json`
  → thân JSON (bỏ `generated_by`) BẰNG HỆT `reports/fingerspell_live_2026-09-29/hand_live_check.json` (như review 06
  `docs/reviews/06-review.md:146-148`). Khác → DỪNG (§7), không "giải thích" cho qua.
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/live_segment_check.py --n-clips 8 --seed 0 --out _work/_plan12_tmp/segment_check_rerun.json`
  → cùng 8 `video_id` đúng thứ tự như `reports/live_word_2026-09-28/segment_check.json:30-292`; các trường số so bằng hệt
  (bỏ `generated_by`). Nếu khác chỉ ở trường số mà code đã đổi từ 2026-09-28 (`git log` của file liên quan) → ghi cụ thể,
  CẦN PLANNER. Khác `video_id` → DỪNG (bộ video chưa đủ/khác).
- AC10 của 06: `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py` và
  `VSL_MODEL_TYPE=stgcn_h360 PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/smoke_test_phase12.py` → mỗi lệnh exit 0 và
  in `PHASE 12 SMOKE TEST PASSED`; cả hai lượt chọn clip `qipedc_W03292N` (như `_work/_rev06_tmp/smoke_default.log:38`,
  `_work/_rev06_tmp/smoke_h360.log:62`).
- AC2 của 06 (lệnh nguyên văn `docs/plans/06-viec5-frontend.md:1027`), log `_work/_plan12_tmp/ac2_31.log`:
  - **Nếu §8.1 đã có a4, a5, a6 + vocab hợp lệ:** `Ran 526 tests` … `OK`, 0 failure, 0 error, 0 skip.
  - **Nếu §8.1 chưa giải quyết (mặc định):** chỉ được phép đúng 2 sai khác so với mốc `_work/_plan06_tmp/b9b_ac2_31.log`:
    (i) 8 test của `tests.test_translation_core` không chạy, thay bằng đúng 1 `ERROR: setUpClass
    (tests.test_translation_core.TestVSLTranslationCore)` với FileNotFoundError ViT5 (`src/translation/translator.py:66-68`);
    (ii) `tests.test_vsl_system.TestVSLSystem.test_vsl_predictor_smoke` SKIP với lý do `Checkpoint checkpoints/stgcn_best.pt
    not found`. Mọi test khác của 31 module: `ok`; 0 failure; 0 skip khác; 0 error khác. Coder đếm dòng `... ok` theo module
    ở cả hai log và liệt kê chênh (chênh ngoài (i)(ii) → DỪNG). Số "Ran" in ra được ghi nguyên văn, không suy diễn.
    Đây KHÔNG phải "đạt AC2 của 06": là trạng thái báo lên reviewer/người dùng; đóng AC2 của 06 vẫn đòi 526/0 skip hoặc
    quyết định người dùng (STATE.md:139, câu hỏi đang chờ).
  - Nếu chỉ có một phần của a5/a6/vocab: vẫn là setUpClass ERROR; ghi rõ file nào thiếu.
- `cd frontend && npm test` → 0 fail (không phụ thuộc dữ liệu; chạy để đủ bộ V0).

**AC5 — Báo cáo.** `12-progress.md` có bảng cuối: mỗi mục a1–a7, b1–b4, c1–c2 → nguồn (slug + version Kaggle/commit) →
trạng thái (ok / mất / unverifiable) → lệnh kiểm + kết quả; mọi số trong bảng trích từ JSON/log có lệnh + commit.

**AC6 — B8 (nếu làm).** b4: `git diff --exit-code reports/translation_corpus_validation.json` rỗng sau khi chạy; jsonl có
9.405 dòng. b3: report chạy lại vào `_work` có `total_frontal_keypoints` 4200, `hash_verification` 4200/4200 và mọi khóa đếm
bằng `reports/vsl_gh_validation.json`; `reports/vsl_gh_validation.json` không đổi (`git diff --exit-code`); test tham số mới OK;
AC2 31 module chạy lại sau B8 cho kết quả giống hệt AC4.

## 7. Rủi ro dữ liệu/ML và điểm dừng có điều kiện (coder dừng, báo orchestrator)
1. **Nguồn upstream đổi version** (hauuto, QIPEDC Kaggle): biểu hiện = lệch `num_frames`/facts/hand_live_check. Không "chấp nhận
   gần đúng": dữ liệu khác thì mọi bằng chứng tương đương cũ không còn áp dụng. → DỪNG, CẦN NGƯỜI DÙNG (bản gốc).
2. **Output kernel `vsl-extract-alphabet` đã bị ghi đè** bởi lần chạy sau: kiểm bằng AC3-b2/AC4. Lệch → DỪNG; không trích lại
   trên Kaggle khi chưa có kế hoạch (trích lại = npz mới, cột `kaggle_npz_*` của JSON cũ không còn tái lập).
3. **Lệch train–realtime**: khôi phục không đổi code tiền xử lý; AC4 là kiểm trực tiếp (bằng hệt). Landmark trích trên Windows
   vs Linux lệch nhẹ là đã biết (`docs/CLOUD.md:54-55`) — chỉ so cùng máy.
4. **Rò rỉ**: không có train/chọn model; split không đổi (cấm ghi `data/splits/`). Ghi chú: 2 clip `qipedc_D0489/D0490B`
   là TEST ngoài (quyết định 2026-10-01 19:22: giữ, đính chính tài liệu — việc của 06, không làm ở đây).
5. **Giấy phép**: hauuto chưa rõ giấy phép → chỉ dùng nội bộ, không commit video/landmark/tên clip theo người ký trong file mới;
   QIPEDC giáo dục/nghiên cứu (`docs/data_registry.md:15`).
6. **Cỡ mẫu**: không đo độ chính xác; không có số liệu mới nào được báo như kết quả mô hình.
7. **Ổ đĩa**: thiếu chỗ (B6) → DỪNG trước khi tải, không xóa gì để lấy chỗ.
8. Đích đã có file khác hash; `git status` đổi ngoài dự kiến; cần sửa file ngoài §5 → DỪNG.

## 8. Điểm dừng bắt buộc — CẦN NGƯỜI DÙNG

### 8.1 Checkpoint không có bản lưu trữ: `stgcn_best.pt`, `vit5_stage{1,2}/best_model/`, `cslr_best.pt` (+ `gloss_vocab_canonical.txt`)
Không có trong 2 manifest, không có sha256 nào trong repo, không có trong `_work/`. Hậu quả nếu không có: AC2 của 06 thiếu 9
test (8 không chạy do lỗi setUpClass + 1 skip) — xem AC4. Hướng dẫn người dùng (làm theo thứ tự, dừng khi tìm thấy):
1. Tìm bản sao riêng: ổ khác/USB/OneDrive/Google Drive; tên thư mục `checkpoints` có các file `stgcn_best.pt` (~3,9–4,1 MB),
   `cslr_best.pt` (~28 MB, `docs/audit/PHASE4_AUDIT.md:266`), thư mục `vit5_stage2\best_model\` (có `config.json`,
   `model.safetensors` hoặc `pytorch_model.bin`, file tokenizer), và `data\external\vsl_gh\gloss_vocab_canonical.txt`. Nếu có:
   chép vào `_work\_plan12_restore_user\` (KHÔNG chép thẳng vào `checkpoints\`), báo orchestrator; coder sẽ kiểm (nạp được,
   vocab_hash khớp) rồi đặt vào chỗ.
2. Modal volume (dự án từng có `src/training/modal_runner.py`, volume `vslt-data-volume`, lệnh sync-data đẩy
   `checkpoints/stgcn_best.pt`, `gloss_vocab_canonical.txt`, `dataset_canonical.json` lên): trong terminal của bạn, đăng nhập Modal
   (token của bạn — không dán token vào chat/repo), chạy `modal volume ls vslt-data-volume /` và
   `modal volume ls vslt-data-volume checkpoints`. Gửi lại danh sách tên file (không cần nội dung). Nếu có, orchestrator sẽ
   đề xuất lệnh `modal volume get` vào `_work\_plan12_restore_user\`.
   > (2026-10-02, kế hoạch 13) Modal không dùng; `src/training/modal_runner.py` đã gỡ ở commit 84c90e4 — mục này không còn áp dụng.
3. Nếu không còn bản nào: chọn một trong
   (A) Chấp nhận mất: 9 test trên ghi là "không tái lập được do mất artifact chưa lưu trữ"; trả lời câu hỏi đang chờ ở STATE
       ("có chấp nhận bằng chứng lịch sử tại 0491877 kèm ghi giới hạn không?"). Chế độ Ký câu (kế hoạch 07) bị chặn tới khi có (B).
   (B) Train lại trên Kaggle (kernel PRIVATE) thành artifact MỚI: cần kế hoạch riêng (ViT5 stage1→2, CSLR với backbone mới,
       stgcn_best Tier 1), GPU-giờ do planner ước lượng từ `reports/vit5_stage*_history.json`, `reports/cslr_training_history.json`;
       số liệu cũ (BLEU/WER trong `reports/PHASE4B_REPORT.md`, `reports/cslr_test_results.json`) KHÔNG áp cho model mới.
       Nên kèm lưu ngay vào dataset private (câu hỏi Q2 đang chờ ở STATE).
   Mặc định khi chưa trả lời: (A) tạm thời cho mục đích báo cáo; không train gì.

### 8.2 `data/Dataset/Labels/label.csv`
Bạn đã chuyển file này từ `data (2)/Dataset/Labels/` (STATE "Thay đổi chưa commit"). Kế hoạch khôi phục nó bằng bản trong git
HEAD. Nếu bản bạn chuyển có sửa riêng (thêm/bớt dòng), hãy báo; nếu không trả lời, mặc định coi bản git HEAD là đúng.
Không chặn bước nào.

### 8.3 Không có điểm dừng khác
Không đổi model mặc định; không hành động không hoàn tác (chỉ thêm file vào thư mục rỗng, không xóa/ghi đè); không đụng
thay đổi chưa commit của người dùng; tải dữ liệu đã được người dùng cho phép (quyết định 2026-10-01 19:22).
