# STATE — nguồn sự thật để tiếp tục (docs/STATE.md)

> Orchestrator PHẢI đối chiếu file này với `git log` và `docs/progress_log.md` mỗi khi khôi phục, sửa chỗ sai,
> ghi 1 dòng vào "Nhật ký khôi phục", rồi mới làm tiếp.

- Cập nhật lần cuối: 2026-10-02 22:22 (giờ Việt Nam)
- HEAD: cfc5eea (+ commit state này) | Nhánh: feat/vslt-complete
- Cho phép tắt máy: KHÔNG
  (Chỉ NGƯỜI DÙNG được đổi dòng này; agent/orchestrator không tự đổi. Luật đầy đủ: "Quyết định của người dùng" 2026-10-02 20:15.)
- Trạng thái phiên: ĐANG CHỜ HẠN MỨC — 5h 80% lúc 22:19, reset 01:00 ngày 3/10 giờ VN; 7 ngày 43%. Không đơn vị nào lọt cổng
  (coder 1 bước nhỏ est 13: 80+13 = 93 > 90). Không có agent chạy. Orchestrator chỉ theo dõi trạng thái kernel K2 bằng sleep nền ≤ 25 phút.
  VIỆC KẾ TIẾP (sau reset): vslt-coder 13 hoàn tất B7 — K2 đang RUNNING (xem "Tài nguyên"): tải output vào _work/_plan13_tmp/k2_preflight/,
  đối chiếu preflight.json (rows, n_mismatch, leak_check_total) + env.json với preregistration.json, lệch → §7.2; khớp → commit JSON/log nhỏ, sổ GPU. Rồi B8 (K1 GPU).
  Song song khi chờ kernel: planner kế hoạch 11 (việc 5) — chưa có file.
  Coder 13 B7 (dd510f1, cfc5eea, chỉ 13-progress): GIẢ ĐỊNH CẦN REVIEWER XÉT: PIN_COMMIT trong file repo vẫn None (test có sẵn
  tests/test_retrain_tools.py:2170 và :2189 assertIsNone); bản đẩy Kaggle ở _work/_plan13_tmp/k2_push/ = file tại 0908ef3 chỉ thay dòng 38
  PIN_COMMIT="0908ef3e…" (sha256 kernel 001b3ec3…a376). B8/B9 làm tương tự. Rủi ro: kernel dùng Path(__file__) — nếu Kaggle không đặt
  __file__ → ERROR "K2 FAILED: NameError" (lỗi thiết kế kernel, không phải lệch dữ liệu). Mẹo: CLI Kaggle báo "Permission 'kernels.get' was denied"
  tới 30 phút sau access_token_expiration (lỗi kagglesdk) — chờ, không phải lỗi kernel.
  (Trước đó 21:15: giao coder 13 B7, cổng 69 + 13 = 82 ≤ 90.)
  Coder 13 B5+B6 XONG (86927ef, 2cb02b3, ea12b44, 0908ef3 = COMMIT GHIM, fa687ef, c8a9dc6; đã push, ls-remote = c8a9dc6): preregistration
  reports/retrain_2026-10-02/preregistration.json (leak_check 0, code_dirty false); kernel kaggle/vsl-retrain-stgcn-tier1 (K1),
  kaggle/vsl-retrain-cslr-vit5 (K2 MODE=preflight, enable_gpu false, không eval); PIN_COMMIT=None → đặt ở B7/B8; K2 train đòi
  k1_outputs.json khóa `stgcn_best_pt.sha256`. test_retrain_tools 112 OK; +guard 154 OK/2 skip. B6: dataset private
  phmvnsm33/vslt-retrain-inputs-tier1 162 file verify OK; upload ~26.3 KB/s ⇒ ViT5 ở B10 gần như chắc chạm Q2 (>3h).
  MỞ: AC8-a Ran 518 FAILED(failures=1, errors=1, skipped=1) — thêm 1 failure so với mốc: tests.test_hand_landmarks_ws
  test_reset_segments_and_graphs ([1,1,1,0] != [1,1,1,1]) FAIL 3/3 lần chạy đủ khi có 6 file B5, PASS 2/2 khi tạm dời chúng, PASS khi chạy riêng;
  không import chung. Cần điều tra (phụ thuộc thứ tự/thời gian?) trước review cuối 13 — reviewer cuối phải xét. Kế hoạch 11 CHƯA có file → cần planner.
  (Trước đó: chờ hạn mức 5h 88% lúc 16:28, reset thật 19:20 — bản cũ ghi nhầm 19:40.)
  Coder 13 sửa trước B5 XONG (1ff6037, 80802be): E1 (evaluation_output + file đánh dấu .started mở "x"), E2 (manifest theo đường tương đối;
  manifest_rel_paths k2/cslr_best.pt, vit5_stage2/best_model), E3 (canonical_json + test_keypoints_digest bắt buộc), G2 (TestG2RegisteredReference so với
  preregistration / tham chiếu B3 — đột biến reviewer giờ FAIL); 129 test OK / 2 skip. Coder thêm 9 dòng vào fixture build_inputs của test cũ
  (không đổi assertion) — reviewer cuối xem lại. Mục 5 (split="all" + sentence_split raise) KHÔNG làm: trái kế hoạch §3.4 dòng 347 và test có sẵn
  test_sentence_split_guard.py:472 — orchestrator HOÃN sang backlog thấp (không sửa test cũ). VIỆC KẾ TIẾP: coder 13 B5 (preregistration đủ khóa — danh sách
  trong docs/plans/13-progress.md + review giữa §6; kernel K2 không gọi eval; kernel assert sha stgcn_best.pt; commit ghim; push) → B6 … ;
  trong lúc chờ kernel: việc 5 (kế hoạch 11), việc 3 (kế hoạch 08), chuẩn bị việc 7.
  (0 trùng test); gói Tier 1 162 file digest 7098e007…; train.py --seed; archive_retrain_kaggle.py (24 test API giả); --sentence-split cho
  train_cslr/stage1/stage2 (LEAK CHECK OK, TEST DEFERRED); eval_sentsplit.py (12 test); 115 test OK/1 skip; AC2-06 y mốc.
  Review GIỮA 13 (docs/reviews/13-review-mid.md): GO cho B5 có điều kiện — không rò rỉ; cần sửa (TB) guard G2 10k tự quy chiếu (đột biến L1 SENT275 vẫn PASS),
  E1 cổng "chạy một lần" chỉ theo --out, E2 so manifest theo tên file gốc (stage1/stage2 lẫn), (thấp–TB) E3 kiểm đầu vào bỏ qua im lặng, (thấp) split="all" + sentence_split không raise.
  B5 bắt buộc: preregistration đủ khóa (danh sách trong review), K2 không gọi eval/test, kernel assert sha stgcn_best.pt (tránh train from scratch im lặng).
  VIỆC KẾ TIẾP: vslt-coder 13 B5 (kèm sửa E1, E2, E3, G2, mục 5 trước khi commit preregistration).
  Đã tìm Kaggle (09:25): 9 kernel của phmvnsm33 (extract/pack/train unified/harmonized/alphabet) + 2 dataset private — KHÔNG có stgcn_best.pt,
  ViT5, cslr_best.pt, gloss_vocab_canonical.txt. Colab: file nằm trên Google Drive của người dùng — orchestrator không truy cập được (chờ người dùng xem).
  Đã xóa (09:35, đã kiểm 0 link/junction trước khi xóa): _work/_plan12_tmp/{dl_hauuto, dl_qipedc, vslgh_src, vslgh_head.tar} (~21G),
  _work/_kaggle_staging/{restore_dl, restore_dl2, verify_provenance, verify_download}, %TEMP%slt_e2e (y4m), .agents/skills/modal/ (untracked),
  2 file rác 0 byte ở gốc repo. Dữ liệu đã khôi phục còn nguyên (4362 file Videos, 3 checkpoint). Ổ C trống 132G.
  Planner 13 XONG (docs/plans/13-train-lai-checkpoint-thieu.md): K1 stgcn_best (≤0.25 GPU-h, trần 0.75), K2 CSLR + ViT5 song song T4×2
  (≤1.0, trần 1.75), tổng trần 2.5 GPU-h; script vocab mới (372 token, LF); 3 dataset private mới + manifest sha256; gỡ Modal = git rm
  src/training/modal_runner.py (+ dòng "đã gỡ" ở plan 12 §8.1, docs/cloud_training.md). Coder B0–B13 (~15 h công + chờ kernel).
  Q1 (CSLR: (i) công thức cũ chia theo người ký [mặc định] / (ii) chia theo câu), Q2 (upload ViT5 >3h), Q3 (đặt checkpoint mới vào đường dẫn
  mặc định = thuộc quyết định 09:20, không phải GATE) — đều có mặc định, không chặn tới B9.
  Q1 ĐÃ TRẢ LỜI (ii) 10:05 → cần planner Lần sửa 1 kế hoạch 13 (split câu cho CSLR + ViT5, guard, tiêu chí WER/BLEU + CI) TRƯỚC B3.
  Coder 13 B0–B2 XONG (39e96bf, 19b7159, 0373a90): gỡ Modal (modal_runner.py bị cuốn vào commit state 84c90e4 của orchestrator do commit cùng lúc —
  nội dung đúng); vocab script: 372 token, sha256 dd7bc3da…1d11 (dựng từ TOÀN BỘ dataset); 15 test OK; AC2-06 hồi quy y mốc (518, 1 ERROR, 1 skip).
  Không tìm thấy cách sinh vocab gốc trong lịch sử git. 4 file tier1_grouped_* thực ra đang tracked.
  Planner 13 Lần sửa 1 XONG (4f714c6): test = SENT271–300 (nguồn 27.98/23.18: reports/audit_round2/v2_cslr_reliability.json), val 30 câu
  random.Random(42) trên SENT001–270, train 240; CSLR train S01–S04×train, val S05×val, test S06×test; ViT5 stage1 loại cặp khớp 60 câu;
  configs/vslgh_sentence_split_v1.json + src/data/sentence_split.py; vocab chỉ từ câu train (≠ 372); tiêu chí §3.12 (sacrebleu 13a, bootstrap
  1000, RandomState(42), CI 95%); eval MỘT lần local (scripts/eval_sentsplit.py); K3 công thức cũ = B14 tùy chọn. Bước tiếp từ B2a.
  Coder 13 B2a–B2c XONG (0a18183, 9146f6f, 059a780, b2be827): configs/vslgh_sentence_split_v1.json (240/30/30, seed 42, sha256 289b2ac1…);
  src/data/sentence_split.py; guard tests/test_sentence_split_guard.py 39 OK / 1 skip (Clean10k G2 chờ B3), 4 đột biến bị bắt; dataset mặc định
  == mã cũ (22 cấu hình); vocab train-only 322 token (sha256 c0af13db…, 50 gloss bị loại). Phát hiện ngoài phạm vi: (1) test_hand_landmarks_ws
  TestReset.test_reset_segments_and_graphs CHẬP CHỜN (OK/FAIL/OK) — cần điều tra; (2) tests.data.test_vsl_gh_dataset test_19 FAIL: dataset_canonical.json
  khôi phục có 0 trường annotation_source (dữ liệu, kế hoạch 12 b3).
  VIỆC KẾ TIẾP: vslt-coder 13 B3 (cleaned 10k jsonl + đóng gói Tier 1) → B4a–B4d → B5 (đăng ký trước, commit ghim, push) → … Sau đó: 13 B3–B5, ...; coder 06 B10 (tài liệu) xen khi chờ kernel.
  SỰ CỐ (lỗi của orchestrator): 30/9 23:42 `git worktree remove --force ../_rev06_wt` đi xuyên JUNCTION trong worktree tạm và xóa nội dung
  `checkpoints/`, `data/Dataset/`, `data/external/` của repo chính (thư mục còn, rỗng). Mất: alphabet_best.pt, provenance.json, checkpoint
  stgcn/stgcn_h360, video+nhãn QIPEDC, hauuto_raw, alphabet_hands_kaggle, vsl_gh, parallel_text. Còn nguyên: data/raw_tudienngonngukyhieu,
  data/splits, data/processed, clone/, _work/, code + git.
  Bản sao đã biết: _work/_kaggle_staging/restore_root/checkpoints/{alphabet_best.pt, stgcn_tier2_indomain.pt, stgcn_unified_best.pt};
  Kaggle private phmvnsm33/vslt-step4-artifacts + phmvnsm33/vslt-provenance-artifacts (manifest sha256 trong reports/.../kaggle_archive_manifest.json).
  CHƯA khôi phục gì: chờ người dùng chọn (1) phần mềm khôi phục file (winfr/Recuva — cần hạn chế ghi ổ C trước) hay (2) khôi phục checkpoint
  từ _work + Kaggle có kiểm sha256; video/landmark: người dùng có bản gốc không, hay tải lại từ nguồn + trích lại trên Kaggle.
  Review 06: phần 1 xong (docs/reviews/06-review.md: 1–4 PASS; AC5 đột biến chỉ qua proxy do thiếu dữ liệu; V0 = sự cố trên).
  Review 06 phần 3 XONG (00:22): 10 PASS, 11 PASS (V6 thấp: Vite proxy tự trả CORS cho origin loopback; V7 thấp: detail lộ exception),
  12 PASS (3 lần đổi tiêu chí AC12 hợp lý, không hạ tiêu chí; V9 trung bình: coder nới kiểm hand_ws_session_info ở 7e38118 và
  06-progress.md:237-239 báo sai lượt dev B8), 13 FAIL (O1: phase12_api.md:32-33 "qua proxy CORS không tham gia" bị thí nghiệm bác; O2 = V9).
  Review 06 phần 2 XONG (00:38): 5 FAIL (V11/O5: 2 clip qipedc_D0489, qipedc_D0490B trong AC5/AC6 là TEST ngoài Cấp 1, D0490B còn trong
  unified/test.csv — trái §6 kế hoạch; câu "10 clip TRAIN" sai ở phase12_api.md:173-174, progress_log:112, kế hoạch §0.4/§6/AC11; gốc: kế hoạch
  chọn "2 clip qipedc đầu" của manifest Cấp 1), 6 PASS, 7 PASS (V12 thấp), 8 PASS (V13 thấp), 9 PASS lịch sử tại 0491877 / UNVERIFIED hiện tại (V0).
  KẾT LUẬN SAU 3 PHẦN: CHANGES_REQUESTED (vòng 1/3). Trước APPROVE: V0 khôi phục dữ liệu + reviewer chạy lại AC2 526/0 skip, npm test,
  đột biến AC5, AC10 ×2; V11/O5, V10/O1, V9/O2 (TRUNG BÌNH — cần planner sửa kế hoạch rồi coder sửa tài liệu); sau đó dòng AC13 + reviewer kiểm lại 5, 13, V0.
  Backlog được: V6, V7, V8; nên làm luôn O3, O4, V12, V13 khi sửa phase12_api.md.
  Kế hoạch 06: XONG B0–B7 (B5 34a527d, B6 0328c1b, B7 dbd79f2). Còn: B8 e2e fullstack (LOCAL, Edge + video thật) → B9 → review 06.
  Reviewer 06 cần xác minh: CRITICAL impact ở B5/B6 (component React, GitNexus nhầm tên JS↔Python), HIGH ở B2/B3 (symbol mới),
  B7 sửa tests/test_frontend_contract.py (file do chính kế hoạch 06 tạo ở B4 — kiểm không nới), 050d337 thiếu detect-changes.
  CLOUD A–D: ĐÃ MERGE (bbfdff3, --no-ff) sau review local APPROVE (docs/reviews/cloud-2026-09-29-review.md, 6a6538c).
  Sau merge: 31 module (29 của AC2-06 + test_archive_private_kaggle_r05 + test_backend_source_guard) Ran 467 OK, 0 skip.
  TỪ NAY mọi lệnh không hồi quy phải có thêm 2 module mới. Planner phải xử lý K1+P2 trước khi code 08/11; P1,P3,P4,P5 trước khi code 07.
  Coder 06 chặng 4 (B8–B9): B8 xong (7e38118 script, e3d0df8 3 JSON e2e tại 15200d9 sạch; 19/20, 17/18, 20/21 đạt);
  B9 kiểm tra trước xong (001e020: AC2 29 module 429 OK, 31 module 467 OK, npm test 26/26, build OK, AC1 tách phần) nhưng CHƯA ĐÓNG.
  CẦN PLANNER (Lần sửa 2): AC12 mệnh đề "mọi URL WS bắt đầu bằng ws://localhost:3000/ws/" đỏ ở cả 3 kịch bản chỉ do socket HMR
  của Vite dev (ws://localhost:3000/?token=…, protocol vite-hmr); app socket đều qua proxy, không :8000. Coder đề xuất (a)/(b)/(c).
  Cần planner xét luôn 4 giả định coder tự đặt (clip Ký từ qipedc_D0120T; socket đóng trước message do StrictMode; cửa sổ 180 s gộp;
  độ dài lượt ghi) và AC1 có file từ commit cloud-handoff 8628948/296b12e/f62dd45 ngoài danh sách.
  Planner Lần sửa 2 XONG (§0B của kế hoạch 06, commit cùng lượt này): AC12 chọn (a) — loại socket HMR theo luật chặt
  (regex neo, protocol vite-hmr, chỉ type connected, ≤1/lượt; :8000 cấm mọi socket); luật socket mồ côi StrictMode; chấp nhận 4 giả định;
  AC1 chỉ áp cho commit `^(WIP )?06:`, commit khác quy về 4 nhóm; AC2 đóng việc = 31 module. PHẢI chạy lại 3 kịch bản e2e.
  Coder B8b-1/B8b-2 XONG (302072c, eb379fa: 16 test AC12-t; AC2 31 module Ran 483 OK, 0 skip). B8b-3 DỪNG §7-8 (1a4e182):
  chạy thử tại eb379fa (JSON ngoài repo ../_plan06_tmp/b8b3_trial_*.json): Ký từ 21/21, h360 24/24 xanh; Đánh vần 22/23 đỏ
  strictmode_orphan_rule — App.jsx tab mặc định 'realtime' mount Phase12Pipeline (2 socket /ws/live-stream do StrictMode),
  kịch bản chuyển tab ở 2.21 s → cả 2 socket đóng 0 message. App.jsx thuộc danh sách KHÔNG đổi.
  Planner Lần sửa 3 XONG (717aa3e, §0C; lượt planner đầu bị người dùng bấm nhầm dừng, giao lại): vai trò path là hằng theo kịch bản
  (Đánh vần dùng /ws/hand-landmarks, path bị gỡ /ws/live-stream; Ký từ dùng /ws/live-stream), kiểm mới tab_unmounted_socket_rule
  (≤2 socket, tạo trước click tab, đóng trước record_clicked, 0 message hoặc đúng 1 session_info v2, handshake null/101, vẫn kiểm :8000,/ws/).
  e2e_browser.cjs chỉ thêm created_t_s/closed_t_s/click_t_s. Chạy chính thức mỗi kịch bản ĐÚNG 1 lần; đỏ → dừng §7-10.
  VIỆC KẾ TIẾP: vslt-coder B8c-1 (test mục 10 trước) → B8c-2 (script) → B8c-3 (3 JSON chính thức) → B9b (0B.5 bước 4, AC1 nhóm (ii)
  gồm facffea, f52de6f, 717aa3e) → vslt-reviewer toàn bộ 06 (thêm điểm §0B.6, §0C.6).
- Hạn mức (10:15 ngày 2/10): xem usage_ledger; reset 5h 14:30. Sổ đo: docs/usage_ledger.csv

## Đã xong (đã APPROVE)
- Bước 4a–4c (kế hoạch 01): kết luận B. Ứng viên Cấp 2 = H-keepz-360. Báo cáo: reports/step4_2026-09-26/REPORT.md;
  review: docs/reviews/01-review.md (APPROVE vòng 2).
- Dọn dẹp sau 4c (kế hoạch 02, `docs/plans/02-don-dep-sau-4c.md`): .gitignore `reports/**/*.pt` + `reports/**/*.npz`,
  lưu trữ Kaggle dataset private `phmvnsm33/vslt-step4-artifacts` (manifest `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`),
  sửa 3 góp ý nhỏ G1–G3. Review: docs/reviews/02-review.md (APPROVE vòng 3); commit cuối 4fbc1a2.
- Việc 4 (kế hoạch 03) — endpoint chuỗi landmark Cấp 1: APPROVE vòng 2 (docs/reviews/03-review.md), commit 8bba04e, 253 test pass.
  Hợp đồng API: tọa độ chuẩn hóa MediaPipe |v| ≤ 10; khung không có tay gửi null/[]; khung 21 điểm trùng hệt → 422; endpoint ảnh cũ trả 409.
- Kế hoạch 05 — thực thi quyết định 2026-09-28: APPROVE vòng 1 (docs/reviews/05-review.md), commit cuối 4adbe41, AC2 383 OK, 0 skip.
  status chỉ {source, n_signers}; /api/classes 503; dropped_frames không đếm lỗi/control; AC5 không PASS rỗng;
  dataset PRIVATE phmvnsm33/vslt-provenance-artifacts (manifest reports/private_archive_2026-09-28/kaggle_archive_manifest.json);
  alphabet_real_best.pt gỡ khỏi index (còn trên đĩa + lịch sử đã push); README mục "Artifact không nằm trong git".
- Kế hoạch 04 — harmonize() vào đường live "Ký từ" (360px, CleanHolisticExtractor, SignSegmenter, WS v2): APPROVE vòng 1
  (docs/reviews/04-review.md), commit af6d384, 310 test pass. Model mặc định KHÔNG đổi (ứng viên: VSL_MODEL_TYPE=stgcn_h360).

## Đang chạy / dở dang
- Kế hoạch 06 = Việc 5 (frontend + WS v2 + CORS + fullstack e2e): planner XONG — docs/plans/06-viec5-frontend.md (commit cùng lượt này).
  Không CẦN NGƯỜI DÙNG trước khi code; điểm dừng có điều kiện ở §7 (AC5 không bằng hệt; e2e stgcn_h360 0 sự kiện; test cũ vỡ;
  cần cài gói / Edge không có / cần xóa file). Thiết kế chính: Cấp 1 dùng MediaPipe phía SERVER qua WS /ws/hand-landmarks (không
  MediaPipe JS); client WS v2 reducer thuần qua proxy /ws; CORS từ VSL_CORS_ORIGINS, allow_credentials=False, WS kiểm Origin (1008),
  bind 127.0.0.1; e2e_fullstack.py dùng puppeteer-core + Edge webcam giả (clip thật, y4m ngoài repo).
  Coder XONG chặng 1: 050d337/8e7b09b (B0, mốc 383 OK), 4924502 (B1 CORS/Origin 1008/bind 127.0.0.1/strictPort),
  ed5c4c9 (B2 hand_live.py + WS /ws/hand-landmarks). AC2 413 OK, 0 skip. detect-changes B2 HIGH (17 symbol đều mới) — reviewer xác minh;
  050d337 commit không chạy detect-changes trước (chỉ file tiến độ) — sai sót quy trình mức thấp.
  Coder XONG chặng 2: 2a45403, e58d025 (B3 test tương đương Cấp 1: AC5 bằng hệt 10/10 clip), 5fcf295 (JSON AC6), 026f474 (B4 lib JS
  + node --test 26 pass + guard). AC2 423, 1 failure CÓ CHỦ ĐÍCH (TestFrontendSourceGuard — chờ B5/B6 sửa component cũ).
  CẦN PLANNER: (1) `node --test tests/` lỗi trên Node 25 → coder dùng `node --test tests/*.test.mjs`; (2) AC1 vs AC8 mâu thuẫn ở
  RealtimeStream.jsx (':8000' trong câu báo lỗi dòng 203). Ghi nhận AC6: Kaggle npz vs trích cục bộ lệch detected 1 clip, max 0.230.
  Planner Lần sửa 1 (§0, commit cùng lượt này): lệnh chính thức `cd frontend && npm test` + đếm file test; AC1 cho sửa chuỗi báo lỗi
  dòng 203 (≤ 3 dòng, không xóa file); guard được đỏ ở B4–B6 (chỉ test đó, vi phạm không tăng), xanh từ B7; phase12_api.md ghi Giới hạn AC6.

## Quyết định của người dùng (không hỏi lại)
- 4c: chọn B (giữ model gộp). Chưa đổi model mặc định — đó là GATE riêng.
- Không làm phương án (i) (train model từ điển tới khi khớp). Phương án (ii) (fine-tune từ trọng số H-keepz-360) để CUỐI backlog,
  chỉ sau DoD 1–7, đăng ký trước tiêu chí (cùng 721 clip QIPEDC TEST, chọn epoch bằng VAL).
- 360px: chấp nhận theo luật; đường realtime hạ frame về chiều cao 360 trước MediaPipe, có test tương đương.
- Cắt đoạn nghỉ: giữ ở realtime, tham số lấy từ checkpoint; chế độ Ký từ gom trọn một ký hiệu rồi mới dự đoán.
- REPORT_partial.md: chuyển ra ../_backup_step4/, không commit. reports/**/*.pt và logits vào .gitignore; lưu lên Kaggle dataset PRIVATE, ghi slug + sha256.
  (Đã thực hiện ở kế hoạch 02.)
- 3 góp ý nhỏ của reviewer vòng 2 kế hoạch 01 (G1–G3): sửa ở đợt kế tiếp, cùng một vòng review. (Đã thực hiện ở kế hoạch 02.)
- (2026-09-28, qua BOOTSTRAP) Checkpoint Cấp 1 alphabet_best.pt bị đóng gói lại: chấp nhận tiêu chí V1–V6; ghi
  "người đóng gói: không rõ, trọng số đã đối chiếu".
- (2026-09-28) /api/fingerspelling/status: chỉ trả nguồn dữ liệu + số người ký, không trả tên.
- (2026-09-28) Bằng chứng nguồn gốc (2 file .pt nested + nested_predictions.csv): lưu lên Kaggle dataset PRIVATE.
- (2026-09-28) CORS: thu hẹp ở Việc 5, chỉ origin dev, không dùng "*" kèm credentials.
- (2026-09-28) A3: alphabet_real_best.pt → git rm --cached + .gitignore + lưu dataset private, KHÔNG viết lại lịch sử git.
  §7.2: mở rộng lưu trữ private (log kernel, run_seed43/history.json, các đầu vào không track).

- (2026-09-28 13:27) "mới 74% tận dụng nốt đi": cho phép giao việc nhỏ khi cổng ngân sách chưa đạt, trong cửa sổ 5h hiện tại.
  Orchestrator vẫn giao đơn vị nhỏ nhất, đọc hạn mức sau mỗi đơn vị, không cố ý chạm giới hạn.

- (2026-09-28) Mã người ký hauuto (hauuto_hau/khoi/tai/vy) trong file báo cáo, provenance.json, data_registry.md: GIỮ NGUYÊN (lựa chọn a).
  Chỉ API không trả tên (đã làm ở 22f891c). Không đổi sang S1–S4, không sửa file đã commit.

- (2026-09-29 10:55) Local vẫn là chính; chạy tới khi dùng hết hạn mức 5h (reset 14:40), cho phép vượt cổng ngân sách như 13:27 hôm qua,
  nhưng không cố ý chạm giới hạn thật: dừng khi đơn vị việc tiếp theo có thể không xong. Xong thì lưu STATE, commit, TẮT MÁY.
  Cloud (claude.ai/code) làm việc A–D ở nhánh riêng; orchestrator local kéo về, review, merge.

- (2026-09-29 11:07) Không tắt máy lúc 11:05; chờ hạn mức reset 14:40, chạy tiếp phiên sau reset, xong thì lưu + tắt máy.

- (2026-09-29 18:55) BỎ tự tắt máy: chỉ tắt máy khi người dùng yêu cầu rõ trong lượt đó. Các quyết định "xong thì tắt máy" trước đây hết hiệu lực.
  Khi hết hạn mức: lưu STATE, commit, push, rồi dừng (không shutdown).

- (2026-09-30 15:10) Tận dụng cửa sổ 5h tới ~90%, không dừng khi mới dùng nửa. Cổng ngân sách THAY usage_guard §3.2:
  bắt đầu đơn vị nếu `five_hour_used_pct + 1.0 × est ≤ 95` (thay `+ 1.5 × est ≤ 90`). Gần ngưỡng thì chia đơn vị nhỏ nhất
  (coder 1 bước, reviewer 1 nhóm hạng mục). Dừng lưu (STATE, commit, push) khi used ≥ 90 hoặc đơn vị nhỏ nhất không lọt cổng.
  Vẫn cấm cố ý chạm giới hạn thật; nếu dính 429 thì quay lại hệ số cũ và ghi limit_hit.

- (2026-09-30 23:45) File tạm/log/JSON chạy thử/staging/backup KHÔNG đặt ngoài project nữa: đặt trong `_work/<tên>/` (đã thêm `_work/` vào
  .gitignore). Đã chuyển các thư mục ../_plan05_tmp, ../_plan06_tmp, ../_cloud_review_tmp, ../_rev06_tmp, ../_kaggle_staging, ../_backup_step4,
  ../_backup_audit_round2_rerun_2026-09-24 vào `_work/` (giữ nguyên tên). Tài liệu cũ ghi `../_X/...` ⇒ nay là `_work/_X/...`.
  Đã gỡ worktree tạm ../_rev06_wt. Ngoại lệ: y4m webcam giả của e2e vẫn ở %TEMP%slt_e2e (script từ chối thư mục trong repo).
  Việc theo sau (thấp): docstring scripts/archive_*_kaggle.py còn ví dụ `../_kaggle_staging` → đổi sang `_work/_kaggle_staging` ở đợt dọn dẹp.

- (2026-10-01, rút ra từ sự cố) Luật: trước khi xóa worktree/thư mục tạm, liệt kê và GỠ mọi junction/symlink bên trong
  (`cmd //c rmdir <link>` hoặc `find -type l`/`fsutil reparsepoint query`), không dùng `git worktree remove --force`/`rm -rf` khi còn link.
  Agent không được tạo junction/symlink tới dữ liệu thật trong worktree tạm; cần dữ liệu thì chạy test ở repo chính.
  Orchestrator commit state bằng `git commit --only <file>` / `git commit -- <paths>` (không cuốn file coder đã stage).
  `_work/` được bỏ qua bằng .git/info/exclude (KHÔNG thêm vào .gitignore — test_private_artifacts.test_g_gitignore khóa .gitignore).

- (2026-10-01 19:22) Khôi phục dữ liệu: dùng Kaggle + _work — checkpoint từ _work/_kaggle_staging và 2 dataset Kaggle private, kiểm sha256
  theo manifest; video/landmark tải lại từ nguồn (người dùng hỗ trợ phần không có trên Kaggle). Không dùng phần mềm khôi phục file.
- (2026-10-01 19:22) 2 clip qipedc_D0489/D0490B (TEST ngoài) trong AC5/AC6 kế hoạch 06: GIỮ, chỉ đính chính tài liệu (8 TRAIN + 2 TEST ngoài), không chạy lại.

- (2026-10-01 19:35) Tắt máy (khi người dùng đã yêu cầu "xong thì tắt"): chỉ tắt khi (a) hết việc làm được, hoặc (b) hạn mức 5h thật sự cạn
  (used ≥ 90) — VÀ mọi thứ đã lưu (STATE, commit, push, không còn agent chạy). Không tắt chỉ vì đơn vị việc kế tiếp quá lớn so với cổng:
  phải chia nhỏ (planner viết một phần kế hoạch, coder 1 bước, reviewer 1 nhóm) hoặc làm việc khác không phụ thuộc để dùng nốt quota.
  (Các lần tắt lúc 71% ngày 29/9 và 48% ngày 1/10 là quá sớm.)

- (2026-10-01 20:00) Người dùng đi vắng: làm tiếp, dùng tối ưu quota 5h (chia nhỏ, không để thừa nhiều); khi hết việc làm được hoặc quota
  thật sự cạn (≥ 90) VÀ đã lưu STATE + commit + push, không còn agent chạy → tắt máy (`shutdown //s //t 120`).

- (2026-10-02 09:20) Checkpoint thiếu (§8.1 kế hoạch 12): tìm Colab + Kaggle; không có thì train lại trên Kaggle. Bỏ Modal (không dùng).
  Xóa file tải về/tạm không cần thiết.

- (2026-10-02 10:05) Q1 kế hoạch 13 — CHỌN (ii) cho K2: chia theo câu + giữ chia theo người ký.
  - Giữ split người ký hiện có (S06 = test). Câu test = đúng 30 câu ViT5 chưa thấy (để BLEU mới so được với 27.98 / 23.18); loại khỏi train
    CSLR ở MỌI người ký. Thêm ~30 câu val (seed cố định, ghi seed, không trùng câu test). Chọn epoch/hyperparameter bằng val; test chạy MỘT lần.
  - Cùng split câu áp cho ViT5: nếu train lại ViT5, loại 30 câu test (và 30 câu val) khỏi train/val của ViT5; thêm test guard FAIL nếu câu
    test xuất hiện trong train của CSLR hoặc ViT5.
  - Đăng ký trước tiêu chí trong kế hoạch: WER (S/D/I) + CI bootstrap trên 30 câu test; BLEU Mode A (oracle gloss) và Mode B (CSLR → ViT5),
    cùng CI. Ghi chú: 30 câu này KHÔNG chọn ngẫu nhiên.
  - (i) (công thức cũ) chỉ chạy SAU (ii), nếu cổng ngân sách cho phép, như kiểm tra tái tạo số cũ; ghi vào ledger.
  - Số liệu sinh từ JSON.

- (2026-10-02 16:10) THỨ TỰ MỚI (theo bảng 9 khối việc): 13 (train lại) → 2 (đóng kế hoạch 06) → 3 (kế hoạch 08 segmenter live) →
  5 (kế hoạch 11: sửa HẾT 9 vi phạm guard DoD 7 bằng sửa code, KHÔNG nới guard) → 7 (đo độ trễ) → 8 (README/EVALUATION từ JSON, Giới hạn,
  clone sạch) → 9 (review toàn nhánh + báo cáo). TRONG LÚC kernel Kaggle của 13 chạy: làm việc 5, việc 3 và phần chuẩn bị của việc 7 (không cần checkpoint).
  - Việc 6 (từ điển): KIỂM TRA DoD 5 còn thiếu gì ở /api/dictionary TRƯỚC khi lập kế hoạch; chỉ dựng SQLite nếu thật sự cần hoặc người dùng yêu cầu.
  - Việc 4 (Ký câu): chạy chế độ OFFLINE, giao diện ghi rõ "demo trong miền y tế". CHƯA làm tách đoạn realtime cho Cấp 3.
  - Ước lượng thời gian: dùng số đo từ docs/usage_ledger.csv (cả seven_delta), báo lại người dùng.
  (Orchestrator xếp việc 4 và 6 — người dùng chưa xếp — sau 5 và trước 8; báo người dùng.)

- (2026-10-02 16:15) `--source mock` của realtime_demo.py: CHUYỂN bộ sinh khung giả thành fixture chỉ dùng trong tests/ (ngoài phạm vi guard);
  realtime_demo.py không còn --source mock.

- (2026-10-02 20:10) "triển khai xong đến mức thì lưu lại và tắt máy" — ĐÃ BỊ THAY bởi quyết định 20:15 ngay dưới.

- (2026-10-02 20:15) LUẬT TẮT MÁY (thay mọi quyết định tắt máy trước đây: 2026-09-29 18:55, 2026-10-01 19:35, 2026-10-01 20:00, 2026-10-02 20:10):
  1. Dòng đầu file "Cho phép tắt máy: KHÔNG" là mặc định. Chỉ tắt khi dòng này là CÓ và do NGƯỜI DÙNG đổi; agent không tự đổi.
  2. Trước khi tắt (mọi điều kiện): `git status -sb` không có "ahead"; ghi slug + giờ bắt đầu + giờ dự kiến xong của mọi kernel Kaggle
     đang chạy; không còn tiến trình nền trên máy (agent, sleep, server…); ghi "Trạng thái phiên: ĐÃ TẮT MÁY CÓ CHỦ ĐÍCH lúc HH:MM".
  3. Lệnh: `shutdown /s /t 300 /c "VSLT: tat may sau khi luu STATE. Huy: shutdown /a"` (không dùng /f).
     Trong Git Bash phải chặn đổi đường dẫn: `MSYS_NO_PATHCONV=1 shutdown /s /t 300 /c "..."`.
  4. Nếu "Cho phép tắt máy" là KHÔNG: lưu xong (STATE, commit, push) thì dừng và báo người dùng, KHÔNG tắt.

## Câu hỏi chờ người dùng
- (từ review 06 phần 2) Nếu không khôi phục được dữ liệu: có chấp nhận bằng chứng lịch sử tại 0491877 kèm ghi giới hạn không?
- (từ báo cáo cloud A–D, không chặn việc) (1) CSLR được train trên cả 300 câu S06 (người ký khác) → README.md:56 và
  reports/PHASE4B_REPORT.md:112 ghi "unseen / zero leakage" là sai; mặc định: ghi nhãn đúng, không viết lại báo cáo cũ.
  Có thêm backlog train lại CSLR chia theo câu (tốn GPU Kaggle)? Có lưu checkpoint CSLR/ViT5 lên Kaggle dataset private?
  (2) Việc C: kiểm archive_name chỉ áp đúng luật cho manifest do script tự sinh (manifest bước 4 không có tiền tố reports/) — giữ hay áp nguyên văn?
  (3) KAGGLE_KEY trong môi trường cloud còn là chữ mẫu — người dùng tự điền (không đưa vào chat/repo).

## Backlog còn lại (thứ tự)
1. (xong — kế hoạch 05)
2. Việc 5: nối frontend với endpoint mới (hợp đồng WS v2, Cấp 1 gửi null/[] cho khung không có tay; tọa độ chuẩn hóa MediaPipe);
   chạy backend + frontend cùng nhau; WebSocket qua proxy /ws; thu hẹp CORS chỉ origin dev, không "*" kèm credentials
   (cùng đợt: kiểm Origin WS, bind); sửa scripts/smoke_test_phase12.py cho WS v2; ghi hợp đồng vào docs/phase12_api.md.
   Planner quyết chính sách ký hiệu phát lặp (W03251B) và tốc độ segmenter theo dt từng frame (review 04, mục 8–9).
2c. Đo lệch landmark Kaggle (Linux) ↔ trích cục bộ trên toàn bộ clip hauuto; ghi rủi ro tương tự cho Cấp 2 vào Giới hạn của GATE.
2b. Segmenter live (tách từ Việc 5 theo kế hoạch 06 §3.8): tốc độ theo dt từng frame; chính sách ký hiệu phát lặp (W03251B).
3. Việc 6: nút chọn chế độ; Ký từ; Ký câu (kiểm tra ViT5 đã học câu nào trước khi đo trên S06).
4. Từ điển 3 miền (SQLite: words, recordings, clips, signers).
5. GATE đổi model mặc định Cấp 2 (chỉ sau Việc 5 — UI mới dùng được đường h360): bảng so sánh model cũ vs H-keepz-360 trên cùng tập test sạch.
6. Bước 5: bộ test webcam (script quay + đánh giá; việc QUAY là của người dùng).
7. Đo độ trễ (DoD 8; ≥ 3 lần qua WebSocket thật, ghi cấu hình máy + tải). reports/audit_round2/v1_latency_benchmark.json: phần tách
   thành phần dựa trên tỷ lệ bịa 0.4/0.6 → đánh dấu không dùng; 90.78 ms "chưa xác minh lại" trong EVALUATION/VERIFY/AUDIT_ROUND2.
8. (từ review 06) V6: cấu hình `cors` cho Vite dev/preview + test; V7: `detail` lỗi WS dùng thông điệp cố định (backend/main.py:1645);
   V8: Reports.jsx:73-77 số gõ tay. Kế hoạch 12: checker kiểm sha file tham chiếu cục bộ (nested_predictions.csv).
   Dọn dẹp: hỏi người dùng có xóa frontend/src/components/RealtimeStream.jsx (mã chết) không; `detail` của 503 có thể lộ tên file.
   Thấp, từ review 05: restore kiểm archive_name == local_path.replace('/', '__'); manifest ghi code_dirty; README nêu
   alphabet_real_best.pt còn trong lịch sử đã push; planner đưa file <số>-progress.md vào danh sách AC1; report_step4.py đọc thêm manifest vslt-provenance-artifacts để REPORT bước 4 không còn ghi 8 đầu vào 'không lưu trữ';
   configs/alphabet_config.yaml (hỏi trước khi xóa); sửa câu chữ AC7-e kế hoạch 04; phương án (ii) (đăng ký trước tiêu chí).

## Tài nguyên
- Kaggle GPU tuần này: ~6 giờ đã dùng (ước tính của người dùng, chưa xác minh), giới hạn tự đặt 10 giờ/tuần.
- Kaggle kernel đang chạy: phmvnsm33/vsl-retrain-cslr-vit5 version 1 (K2 MODE=preflight, CPU, private) — đẩy 2026-10-02T14:15:08Z (21:15 VN);
  RUNNING lúc 15:19Z (orchestrator kiểm). Watchdog kernel 105 phút ⇒ dự kiến xong/tự dừng chậm nhất ~16:00–16:10Z (23:00–23:10 VN).
  Kiểm: `PYTHONUTF8=1 .venv/Scripts/kaggle kernels status phmvnsm33/vsl-retrain-cslr-vit5`.
- Giới hạn API: đã gặp lỗi 429 (reset 4:20 sáng, giờ Việt Nam). Xem orchestrator_resume_addendum.md mục 4 và usage_guard_addendum.md.

## Thay đổi chưa commit trong working tree (KHÔNG đụng)
- Của người dùng: xóa data/alphabet_landmarks_full.csv, data/hand_data.csv, data (2)/Dataset/Labels/label.csv
  (đã chuyển sang data/Dataset/Labels/label.csv). Không commit, không khôi phục.
- Nhiều file/thư mục untracked (data/, clone/, .agents/, .claude/skills/, data/splits/...): không add.

## Nhật ký khôi phục (thêm dòng mỗi lần khôi phục sau khi bị ngắt)
- 2026-09-28 11:05 | bootstrap (không phải ngắt) | kế hoạch 04 code xong, chưa review | Điền STATE từ git log + progress_log. Sửa so với bản mẫu:
  thêm kế hoạch 02 (APPROVE vòng 3) vào "Đã xong"; kế hoạch 04 = 6 commit B1–B6b xong, chưa review, dòng progress_log chưa commit;
  "3 góp ý nhỏ" đã làm ở kế hoạch 02 → bỏ khỏi backlog; chuyển 5 câu hỏi sang "Quyết định" và đưa việc thực thi vào backlog mục 2–3.
- 2026-09-28 11:10 | đối chiếu sau bootstrap | STATE ghi HEAD 2807a8a, progress_log 04 chưa commit, review chưa giao — thực tế HEAD af6d384 (dòng progress_log đã commit), reviewer 04 đã được giao trước khi orchestrator đọc giao thức mới | Sửa mục Đang chạy, ghi hạn mức, commit bootstrap.
- 2026-09-28 11:55 | cổng ngân sách (không phải ngắt) | planner 05 xong; coder 05 chặng 1 chưa giao: 73 + 1.5×20 = 103 > 90 | Dừng sạch theo usage_guard §5, chờ reset 14:30.
- 2026-09-28 13:30 | người dùng yêu cầu dùng nốt hạn mức | sửa giờ reset 14:30 → 15:50 (quy đổi sai trước đó) | Giao coder 05 chặng B0+B1.
- 2026-09-28 13:46 | dừng theo hạn mức (không phải ngắt) | coder 05 B0+B1 xong; số hạn mức chưa cập nhật sau lượt coder | Dừng sạch, chờ 15:50.
- 2026-09-28 16:46 | khôi phục sau chờ hạn mức (người dùng nhắn "tiếp tục") | STATE khớp git (HEAD e0e2365); dòng "Hạn mức" còn ghi "không biết" do sửa trước không áp được → sửa | Giao coder 05 chặng B2–B4.
- 2026-09-28 17:47 | tạm dừng theo yêu cầu người dùng | kế hoạch 05 xong B0–B6, còn AC10-d/e, B7, B8, review | Coder được báo dừng sau B6; STATE lưu việc kế tiếp.
- 2026-09-29 00:15 | khôi phục sau tạm dừng (người dùng nhắn "tiếp tục") | STATE khớp git (HEAD 20b0c36), bản nháp AC11 còn ở ../_plan05_tmp | Giao coder 05 chặng B7–B8.
- 2026-09-29 01:35 | dừng theo yêu cầu người dùng (đi ngủ, tắt máy) | planner 06 xong, coder 06 chưa giao | Lưu STATE, commit, tắt máy.
- 2026-09-29 09:44 | khôi phục sau tắt máy (người dùng nhắn "tiếp tục") | STATE khớp git (HEAD dbec36c), không có việc dở | Giao coder 06 chặng 1.
- 2026-09-29 10:50 | bàn giao cloud theo yêu cầu người dùng (sắp hết quota) | coder 06 dừng sau B5 (34a527d) | Thêm docs/CLOUD.md, scripts/cloud_setup.sh, CLAUDE.md bước 0; push feat/vslt-complete.
- 2026-09-29 11:05 | dừng theo ngân sách + yêu cầu tắt máy | kế hoạch 06 xong B0–B7, còn B8–B9 + review; cloud A/B chưa push được (403) | Lưu STATE, commit, push, tắt máy.
- 2026-09-29 17:20 | khôi phục sau chờ hạn mức (lệnh sleep nền bị dừng khi phiên cũ kết thúc; người dùng báo cloud xong) | STATE khớp git (HEAD 353c46d), cloud đã push nhánh cloud/2026-09-29-viec-a-d | Giao vslt-reviewer kiểm nhánh cloud trước khi merge; sau đó B8.
- 2026-09-29 18:50 | dừng theo ngân sách (không phải ngắt) | planner Lần sửa 3 xong; coder B8c chưa giao (71 + 1.5×16 = 95 > 90) | Lưu STATE, commit, push, tắt máy theo lệnh người dùng.
- 2026-09-29 18:55 | người dùng hủy tắt máy (đã chạy shutdown /a) | không có việc dở | Ghi quyết định: chỉ tắt máy khi được yêu cầu.
- 2026-09-30 14:50 | khôi phục sau chờ hạn mức (người dùng nhắn "continue") | STATE khớp git (HEAD 2773b44), không có nhánh cloud mới | Giao vslt-coder 06 B8c + B9b.
- 2026-09-30 23:50 | 429 giữa lượt reviewer 06 phần 1 (16:18, 71% + est 20) | review dở: 2–4 PASS, 1 đang làm | Ghi limit_hit, cổng chặt lại; dời thư mục tạm vào _work/; giao lại reviewer hoàn thiện hạng mục 1.
- 2026-10-01 00:20 | sự cố mất dữ liệu do orchestrator gỡ worktree có junction (30/9 23:42) | review 06 phần 1 xong | Dừng mọi việc, lưu STATE, push, tắt máy theo yêu cầu người dùng.
- 2026-10-01 00:40 | dừng theo ngân sách (không phải ngắt) | review 06 xong 3 phần: CHANGES_REQUESTED; planner Lần sửa 5 chưa giao (96 > 90) | Lưu STATE, commit, push, tắt máy theo yêu cầu người dùng.
- 2026-10-01 19:25 | khôi phục sau tắt máy (người dùng nhắn "tiếp tục công việc") | STATE khớp git (HEAD dcf9b0d), dữ liệu vẫn rỗng | Hỏi người dùng 2 câu chặn (đã trả lời), giao planner kế hoạch 12 khôi phục dữ liệu.
- 2026-10-01 21:40 | dừng theo hạn mức (84%, không phải ngắt) | kế hoạch 12 APPROVE; 06 Lần sửa 5 đã lập, coder B10 chưa giao | Lưu STATE, commit, push, tắt máy theo yêu cầu người dùng (20:00).
- 2026-10-02 09:40 | khôi phục sau tắt máy (người dùng giao việc mới) | STATE khớp git (HEAD eea8906) | Tìm Kaggle (không có), dọn file thừa, giao planner kế hoạch 13.
- 2026-10-02 11:25 | dừng theo hạn mức (81%) | 13 B2a–B2c xong | Lưu STATE, push, hẹn giờ 14:32 làm tiếp B3.
- 2026-10-02 14:22 | khôi phục sau chờ hạn mức (người dùng nhắn "tiếp tục công việc") | STATE khớp git (HEAD cc52880) | Giao coder 13 B3 + B4.
- 2026-10-02 16:22 | dừng theo hạn mức (86%) | 13 sửa trước B5 xong | Lưu STATE, push, hẹn giờ 19:42 làm tiếp B5.
- 2026-10-02 20:05 | khôi phục sau chờ hạn mức (sleep nền bị dừng khi phiên cũ kết thúc; người dùng nhắn "continue") | STATE khớp git (HEAD e03d988); sửa HEAD ghi eea8906 → e03d988, giờ reset 19:40 → 19:20 | Giao coder 13 B5.
