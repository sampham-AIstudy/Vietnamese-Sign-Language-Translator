# STATE — nguồn sự thật để tiếp tục (docs/STATE.md)
> Orchestrator PHẢI đối chiếu file này với `git log` và `docs/progress_log.md` mỗi khi khôi phục, sửa chỗ sai,
> ghi 1 dòng vào "Nhật ký khôi phục", rồi mới làm tiếp.

- Lịch sử (trạng thái phiên cũ 2/10–8/10, nhật ký khôi phục cũ): `docs/STATE_archive.md` — chỉ đọc khi cần truy vết, KHÔNG đọc khi khôi phục thường.
- Cập nhật lần cuối: 2026-10-06 (phiên cloud, nhánh `cloud/2026-10-04-level1-rearm`)
- KERNEL v6 (cloud, 2026-10-07): vsl-train-alphabet v6 (clone 8c53795, 78 clip user1 gồm p/q) → 160e0c68 (output Kaggle mới nhất). Chưa người dùng chọn v5 hay v6; `reports/alphabet_retrain_2026-10-07/REPORT.md`. Test guard G2/G3 đỏ do `GESTURE_BACKSPACE_WINDOW_MS` (7a267c7), chưa sửa.
- CHECKPOINT CẤP 1 MỚI (quyết định người dùng 2026-10-06): kernel vsl-train-alphabet v5 (36e6dc0, không cắt lát đ/ư) → 9c9e8960; lấy bằng `kaggle kernels output phmvnsm33/vsl-train-alphabet` (output v5 là output mới nhất) rồi đặt vào checkpoints/alphabet_best.pt ở local. KHÔNG qua gate G1–G6 (G1 0.896/0.902, G5 0.124); REPORT.md §5. Checkpoint cũ 756eaf3f: bản ở local người dùng.
- TRAIN LẠI CẤP 1 (cloud, 2026-10-06): kernel vsl-train-alphabet v4 (clone d3a79a2, 66 clip user1) → checkpoint 9e4a99c8 (chỉ trong output Kaggle v4 + checkpoints/ của container cloud; local vẫn checkpoint cũ 756eaf3f). Báo cáo `reports/alphabet_retrain_2026-10-06/REPORT.md`: KHÔNG thay mặc định (G1 trượt, decoder mất đ). Việc kế: người dùng quyết thí nghiệm không cắt lát đ / phiên webcam so 2 checkpoint.
- LẦN SỬA 12 (cloud, 2026-10-06, theo phản hồi webcam của người dùng): `docs/plans/15-lan-sua-12.md`. Mã: ddd7904 (G1 cổng chuyển động decoder, H1 HandednessLock, config rev9), 13759a6 (script dominant_hand_check), 85a6a91 (app: tắt tự cách mặc định, --dominant-hand lock, nối cổng), 551e1b2 (G1b: không cắt chữ biến thể của chữ vừa phát). Bằng chứng: reports/level1_realtime_2026-10-06/{dominant_hand_check,rearm_check_gate,rearm_check_gate_v2}.json. CHƯA review (vslt-reviewer local). Còn: phiên webcam người dùng so rev8 và rev9.
- HEAD: ba9e107 (+ commit state này) | Nhánh: cloud/2026-10-04-level1-rearm
- Tắt máy: CHỈ khi người dùng yêu cầu rõ trong hội thoại (quyết định 2026-10-04 01:15). Lần gần nhất: 9/10 02:12 tắt theo yêu cầu "khi nào xong thì tắt máy giúp tôi lần này" (hết hiệu lực sau phiên đó).
- Trạng thái phiên: 10:47 9/10 (5h dùng 24%). U2b XONG b0cbcf1 (vslt-coder-claude; orchestrator chạy lại tests.test_level1_demo Ran 150 OK; coder: level1 all Ran 499 OK skip 1). ĐANG GIAO vslt-reviewer U2b. VIỆC KẾ: APPROVE → U2c (agy; giả định coder U2b: resizeWindow 1 lần ở khung đầu — U2c xem thứ tự với --fullscreen; THẤP-2 review U2a điểm mù rA/rB) → U2d → X1 trước V1.

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

- (2026-10-03 02:40) Dọn dẹp: GIỮ frontend/src/components/RealtimeStream.jsx và configs/alphabet_config.yaml. Đưa vào backlog DỌN DẸP CUỐI: xóa khi grep
  không còn tham chiếu và test không đổi, MỖI FILE MỘT COMMIT riêng.
- (2026-10-03 02:40) Đính chính CSLR "unseen / zero leakage" (trả lời câu hỏi cloud A–D (1)):
  - README: sửa TRỰC TIẾP, bỏ "unseen / zero leakage" cho CSLR, thay bằng "người ký chưa từng thấy, nhưng 300/300 câu đã thấy ở train" kèm số liệu sinh từ JSON;
    số WER thật trên câu chưa thấy CHỜ kết quả K2 (kế hoạch 13).
  - reports/PHASE4B_REPORT.md: thêm khối ĐÍNH CHÍNH ở ĐẦU file (có ngày, link tới số đúng), KHÔNG xóa nội dung cũ.
  - Grep "unseen" / "zero leakage" / "không rò rỉ" toàn repo (EVALUATION, báo cáo, UI) và sửa tương tự.
  - Thêm test guard: khẳng định "unseen" / "zero leakage" cho CSLR chỉ được phép nếu trỏ tới JSON chứng minh split theo câu.

- (2026-10-03 02:55) KHÔNG tìm checkpoint gốc nữa (đã kiểm toàn bộ tài khoản Kaggle phmvnsm33 03/10: 11 notebook, 3 dataset, 0 model — không có;
  danh sách _work/_kaggle_search_1003/). Train lại TRÊN KAGGLE; KHÔNG train local (lâu, hại máy). Orchestrator áp dụng: chẩn đoán smoke CSLR B9b (§0B.3,
  chạy tới epoch 60) cũng chạy trên Kaggle (kernel CPU, 0 GPU) thay vì CPU local; chỉ việc rất nhẹ (test đơn vị, dữ liệu giả, đối chiếu JSON) chạy local.
  Eval MỘT lần B11b (suy luận 30 câu) giữ local như kế hoạch trừ khi người dùng muốn khác.

- (2026-10-04 00:37) Google Drive KHÔNG còn khởi động cùng máy: trước khi dùng G:, mở app bằng `C:\Users\Admin\Desktop\Google Drive.lnk` (vd `cmd //c start "" "C:\Users\Admin\Desktop\Google Drive.lnk"`),
  chờ ổ G: xuất hiện rồi mới đọc/ghi `G:\My Drive\VSLT\`. Các luật Drive khác giữ nguyên.
- (2026-10-03 03:10) Google Drive: người dùng cài Google Drive for desktop (stream, ổ G:, cache giới hạn ~20 GB, khởi động cùng máy) và tạo thư mục
  `G:\My Drive\VSLT`. Agent CHỈ đọc/ghi trong `G:\My Drive\VSLT\` (lưu trữ/tải tài liệu, bản sao checkpoint…); KHÔNG mở/liệt kê/sửa phần còn lại
  của Drive (dữ liệu cá nhân). Không đồng bộ thư mục Project lên Drive. Không cần MCP. Đã thử 03:08: ghi/đọc file 5 MB, sha256 khớp (file thử đã xóa;
  còn `VSLT\_test\write_test.txt`). Drive upload lên mây chạy nền — trước khi coi là "đã lưu trữ" phải kiểm trạng thái đồng bộ (chưa có cách kiểm qua lệnh).
  Khi người dùng PAUSE sync: G: vẫn đọc/ghi được nhưng file chỉ nằm trong cache máy (đã thử 03:14) — lần pause đó chỉ để thử; (03:20) người dùng: sync LUÔN BẬT,
  KHÔNG cần nhắc Resume/xác nhận; connector Google Drive của claude.ai (MCP mcp__claude_ai_Google_Drive__*, có từ 3/10 08:30) cũng
  CHỈ dùng trong thư mục VSLT — không search/list/đọc file ngoài VSLT; Drive chỉ là bản sao phụ, nguồn lưu trữ chính vẫn là Kaggle dataset private + manifest sha256.

- (2026-10-03 10:30) ƯU TIÊN MỚI — LEVEL 1 ĐỂ BÁO CÁO THẦY (hạn 3–5 ngày, tức khoảng 6–8/10/2026):
  - Mục tiêu: Cấp 1 (đánh vần chữ cái) chạy REALTIME, tự nhận từng chữ cái liên tục và GHÉP thành từ (không phải Ghi/Dừng từng chữ).
  - Giao diện demo: APP DESKTOP OpenCV (cửa sổ webcam, chữ hiện trên khung hình) — không phải tab web.
  - TẠM DỪNG HẾT kế hoạch 13, 11, 14 (giữ nguyên trạng thái đã lưu, làm tiếp SAU khi báo cáo xong); dồn hạn mức cho Level 1.
  - Ràng buộc vẫn giữ: đầu vào realtime phải giống lúc train (cùng extractor/tiền xử lý — skill vsl-landmark-consistency); không thêm vi phạm guard DoD 7
    (tests/test_backend_source_guard.py); quyết định 16:15 (realtime_demo.py không còn --source mock) vẫn áp; số liệu báo cáo chỉ từ JSON.
  - (10:45) Người dùng chạy tab Đánh vần trên web thấy CÓ ĐỘ TRỄ (chấm landmark chạy theo tay chậm). Nguyên nhân theo kiến trúc (chưa đo): vòng
    trình duyệt → JPEG → WS → MediaPipe server → về; chấm vẽ lên khung hiện tại bằng tọa độ của khung cũ. Yêu cầu cho kế hoạch 15: (1) LÕI Cấp 1 dùng chung
    (extract + tiền xử lý giống train + tách ký hiệu tự động + phân loại + ghép từ) để web dùng lại sau; (2) app desktop: luồng đọc webcam riêng lấy khung MỚI
    NHẤT, bỏ khung cũ; MediaPipe chế độ video/tracking (thông số khớp train hoặc có test tương đương); vẽ chấm ngay trên đúng khung đã xử lý; phân loại chỉ khi
    kết thúc ký hiệu, không chặn khung; (3) ĐO độ trễ từng chặng ra HUD + JSON (số báo cáo chỉ từ JSON). Web sau báo cáo: cân nhắc MediaPipe JS chỉ kèm test
    tương đương. README:203 `realtime_demo.py --webcam` sai (đúng: --source 0); realtime_demo.py là demo Cấp 2, KHÔNG có Cấp 1.

- (2026-10-03 15:40) "Tập trung xử lý cho hoàn thiện chạy demo tốt phần ký tự trước để trình bày": thứ tự kế hoạch 15 sau B5 = B6 (hiệu chỉnh tham số tách
  ký hiệu) + sửa theo phản hồi webcam U1/U2 của người dùng TRƯỚC; B7 (replay SUMMARY) / B8 (tài liệu) / B9 chỉ làm phần cần cho buổi trình bày; mọi việc khác chờ.

- (2026-10-03 17:20) Level 1 thành "sản phẩm" (không chỉ demo): tính năng chọn = KHUNG TEXT KIỂU BỘ GÕ (chữ đang gõ có con trỏ, dấu đổi ngay khi ký dấu mới
  á→à như Telex — compose() đã có luật "dấu sau thay dấu trước", âm tiết đang gõ tô sáng, từ trước cố định). KHÔNG chọn: copy/lưu file, TTS, bản web (để sau).
  Ưu tiên: SONG SONG — planner làm MỘT lần sửa kế hoạch 15 cho cả (1) nhận dấu thanh (phát hiện wrist_trajectory False) và (2) khung text bộ gõ; coder làm xen kẽ.

- (2026-10-02 20:10) "triển khai xong đến mức thì lưu lại và tắt máy" — ĐÃ BỊ THAY bởi quyết định 20:15 ngay dưới.

- (2026-10-08 ~10:00) SAU REVIEW 15 PHẦN A (docs/reviews/15-review.md): người dùng thử `level1_demo.py` (preset mặc định) và `--checkpoint checkpoints/alphabet_best_v6.pt`
  thấy "khá ổn" ⇒ (1) GIỮ preset mặc định hiện tại (rev9, làm mượt, conf 0.55, cử chỉ space/backspace) — vẫn phải ghi Giới hạn: lệch tiền xử lý train/realtime chưa
  đo đồng thuận, cử chỉ kích hoạt nhầm (thăm dò 24/640 backspace, 8/640 space trên clip train), rev9 trượt G5; (2) GÕ KIỂU UNIKEY: giữ DIACRITIC_FUSION (cần sửa cho đúng
  Unikey thật — "thuở"→"thử", "quơ"→"qư" là lỗi — và ghi nguồn/dự đoán gốc của model cho truy vết DoD 6); (3) MODEL CHỮ CÁI MẶC ĐỊNH = v6 (sha 160e0c68…, output kernel
  phmvnsm33/vsl-train-alphabet v6) — quyết định người dùng thay GATE; orchestrator đã chép checkpoints/alphabet_best_v6.pt → checkpoints/alphabet_best.pt lúc 10:05
  (bản trước = v5 9c9e8960, còn ở alphabet_best_v5.pt; gốc a6311820 ở alphabet_best_2026-09-27.pt). Ghi rõ trong báo cáo: v6 đã train trên user1 (kết quả người dùng
  tự thử không phải "chưa thấy"); QIPEDC 46 clip v6 top-1 23 vs v5 25, top-3 65.2 vs 73.9. (4) 84 npz landmark user1 (1.28 MB, đã commit; repo GitHub PUBLIC; 84 mp4
  KHÔNG commit): (09:50) người dùng: GỠ KHỎI GIT, lưu Drive hoặc Kaggle. Orchestrator đã chép data/collected_targeted (84 npz + 84 mp4 + manifest.csv, 169 file, 63 MB)
  vào `G:\My Drive\VSLT\collected_targeted_user1_2026-10-08\` + SHA256SUMS.txt, `sha256sum -c` OK (bản sổ: _work/user1_sha256.txt). CHƯA git rm --cached
  (kernel phmvnsm33/vsl-train-alphabet clone repo và đọc data/collected_targeted ⇒ cần dataset Kaggle PRIVATE làm đầu vào kernel + .gitignore bị test khóa ⇒ planner).
  (5) CỬ CHỈ: người dùng KHÔNG muốn space/backspace tự kích hoạt; chỉ khi cố ý: XÒE 5 NGÓN = space, VẪY TAY SANG TRÁI/PHẢI = backspace (đã có trong code) ⇒ phải
  giảm kích hoạt nhầm (review: 24/640 backspace, 8/640 space trên clip train một chữ) — cần gate tỉ lệ nhầm đặt trước + kiểm trên clip cử chỉ thật của người dùng.

- (2026-10-08 ~11:00) HẠ TẦNG agy: CHO SỬA scripts/agy_guard.py để nhận nhánh làm việc (không ghim cứng feat/vslt-complete; qua biến môi trường/danh sách nhánh,
  commit trước khi chạy) — tiếp tục trên nhánh cloud/2026-10-04-level1-rearm, merge vào feat sau review APPROVE; CHO SỬA scripts/agy_usage.py bỏ qua bucket
  {"disabled": true}. CHỌN CODER LINH HOẠT (không ghim cứng): bước phức tạp ⇒ vslt-coder-claude (Claude tự viết); bước đơn giản ⇒ vslt-coder (agy Gemini) +
  review từng bước. Đây là sự đồng ý dùng vslt-coder-claude theo luật dự phòng.

- (2026-10-08) CODE DO agy + GEMINI VIẾT: sau MỖI bước, (1) cầu nối vslt-coder xác minh độc lập (đọc diff, đối chiếu số với JSON, chạy lại test AC, scope, tests/ chỉ thêm),
  (2) vslt-reviewer kiểm riêng bước đó TRƯỚC khi giao bước kế; sửa ngay trong bước. Logic phức tạp (segmenter, decoder, hiệu chỉnh) ưu tiên Opus/Claude trong agy khi
  nhóm đó còn hạn mức. Lý do: "sửa chỗ này lỗi chỗ khác rất mất thời gian".

- (2026-10-05) CHẾ ĐỘ TÁCH CHỮ LIÊN TIẾP cho buổi báo cáo: (a) CLASSIFIER (lần sửa 4 kế hoạch 15) — điểm dừng "chỉ G6 nhóm dấu thanh trượt" đã kích hoạt trên cloud
  (dấu liên tiếp 0.80 vs 0.85 chế độ cũ; chữ cái G1 0.98). Bật chế độ classifier; dấu thanh trong demo gõ bằng phím 1–5 (token source "key", nêu trong Giới hạn
  cùng số offline dấu 40.83%); phím n vẫn có. Số chuỗi ghép = kiểm logic; U1c webcam là kiểm thật. Không hỏi lại.

- (2026-10-04 01:15) LUẬT TẮT MÁY MỚI (THAY quyết định 2026-10-02 20:15 ngay dưới): "đơn giản ko cần lưu luật tắt máy, khi nào tôi yêu cầu tắt thì lúc đó
  mới tắt thôi đừng tự suy diễn". ⇒ Chỉ tắt khi người dùng yêu cầu rõ trong hội thoại; không mang yêu cầu cũ sang phiên mới. Trước khi tắt vẫn: lưu STATE,
  commit, push, không "ahead", không agent/tiến trình nền; lệnh `MSYS_NO_PATHCONV=1 shutdown /s /t 300 /c "VSLT: tat may sau khi luu STATE. Huy: shutdown /a"` (không /f).
- [ĐÃ BỊ THAY 2026-10-04 01:15] (2026-10-02 20:15) LUẬT TẮT MÁY (thay mọi quyết định tắt máy trước đây: 2026-09-29 18:55, 2026-10-01 19:35, 2026-10-01 20:00, 2026-10-02 20:10):
  1. Dòng đầu file "Cho phép tắt máy: KHÔNG" là mặc định. Chỉ tắt khi dòng này là CÓ và do NGƯỜI DÙNG đổi; agent không tự đổi.
  2. Trước khi tắt (mọi điều kiện): `git status -sb` không có "ahead"; ghi slug + giờ bắt đầu + giờ dự kiến xong của mọi kernel Kaggle
     đang chạy; không còn tiến trình nền trên máy (agent, sleep, server…); ghi "Trạng thái phiên: ĐÃ TẮT MÁY CÓ CHỦ ĐÍCH lúc HH:MM".
  3. Lệnh: `shutdown /s /t 300 /c "VSLT: tat may sau khi luu STATE. Huy: shutdown /a"` (không dùng /f).
     Trong Git Bash phải chặn đổi đường dẫn: `MSYS_NO_PATHCONV=1 shutdown /s /t 300 /c "..."`.
  4. Nếu "Cho phép tắt máy" là KHÔNG: lưu xong (STATE, commit, push) thì dừng và báo người dùng, KHÔNG tắt.

- 2026-10-03: PHÂN VAI MỚI — Claude = Planner/Reviewer/Orchestrator; **Antigravity (agy) = Coder**. Cầu nối: `scripts/agy_code.sh` (agy -p --mode accept-edits),
  subagent `vslt-coder` là lớp mỏng gọi script + xác minh độc lập bằng git/test. `vslt-coder-claude` chỉ là DỰ PHÒNG khi agy hỏng/hết hạn mức (cần người dùng đồng ý).
  Quy tắc cho agy: `docs/prompts/agy_coder.md` + phần VSLT trong `AGENTS.md`. Log agy: `_work/agy_logs/`.
  Kiểm soát agy: git hook (`scripts/githooks/`, bật qua env, không đổi cấu hình repo) + `scripts/agy_guard.py` (scope trong kế hoạch, bảo vệ file người dùng,
  chống nới test, bắt `--no-verify`). Model: `--model gemini|opus|sonnet` tự lấy bản mới nhất, effort do vslt-coder chọn theo loại việc;
  cổng hạn mức agy `scripts/agy_usage.py` (cùng quy tắc ≤ 90% 5h / ≤ 95% tuần), sổ `docs/agy_usage_ledger.csv`.
- 2026-10-08 18:20 (người dùng): "chạy code nhớ để high nhé vì gemini code hay lỗi với cả lên plan và review kĩ" ⇒ SÀN EFFORT agy = high
  (scripts/agy_usage.py min_effort(), env AGY_MIN_EFFORT; cổng không hạ dưới high, thiếu hạn mức thì WAIT; commit ba9e107); planner/reviewer giữ Opus, review từng bước kĩ.
- 2026-10-08 18:25 (người dùng): đồng ý cả 4 cách giảm hạn mức Claude + cách khác nếu tối ưu ⇒ vslt-coder (cầu nối) chạy Sonnet; STATE gọn
  (lịch sử → docs/STATE_archive.md); chờ việc nền > 45 phút thì lưu STATE + mở phiên mới; giữ context phiên chính nhỏ; không đổi model giữa phiên.
  Chi tiết + số đo: docs/prompts/orchestrator_resume_addendum.md mục 6.

## Câu hỏi chờ người dùng
- (từ review 06 phần 2) Nếu không khôi phục được dữ liệu: có chấp nhận bằng chứng lịch sử tại 0491877 kèm ghi giới hạn không?
- (từ báo cáo cloud A–D, không chặn việc) (1) CSLR được train trên cả 300 câu S06 (người ký khác) → README.md:56 và
  reports/PHASE4B_REPORT.md:112 ghi "unseen / zero leakage" là sai; mặc định: ghi nhãn đúng, không viết lại báo cáo cũ.
  Có thêm backlog train lại CSLR chia theo câu (tốn GPU Kaggle)? Có lưu checkpoint CSLR/ViT5 lên Kaggle dataset private?
  → ĐÃ TRẢ LỜI (1): train lại chia câu = kế hoạch 13; đính chính README/báo cáo = quyết định 2026-10-03 02:40.
  (2) Việc C: kiểm archive_name chỉ áp đúng luật cho manifest do script tự sinh (manifest bước 4 không có tiền tố reports/) — giữ hay áp nguyên văn?
  (3) KAGGLE_KEY trong môi trường cloud còn là chữ mẫu — người dùng tự điền (không đưa vào chat/repo).

## Backlog còn lại (thứ tự)
0a. (2026-10-03, người dùng) Đính chính CSLR "unseen / zero leakage" + guard — xem quyết định 2026-10-03 02:40. Cần planner (kế hoạch 14).
    Phần đính chính + guard làm được ngay (không phụ thuộc K2); dòng WER câu chưa thấy điền sau 13 B11b.
0b. DỌN DẸP CUỐI: xóa RealtimeStream.jsx, configs/alphabet_config.yaml khi grep 0 tham chiếu + test không đổi; mỗi file 1 commit.
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
- Kaggle GPU tuần này: kaggle quota thật 4,18 h / 30 h (sau K1, 18:37Z 2/10; làm mới 00:00Z 3/10); giới hạn tự đặt 10 giờ/tuần (người dùng).
- Kaggle kernel đang chạy: phmvnsm33/vsl-retrain-cslr-vit5 version 1 (K2 MODE=preflight, CPU, private) — đẩy 2026-10-02T14:15:08Z (21:15 VN);
  v1 ERROR (watchdog, 16:10Z); v2 COMPLETE 18:20:57Z (2.63 phút CPU). K1 phmvnsm33/vsl-retrain-stgcn-tier1 v1 COMPLETE 18:33Z (1,58 GPU-phút). version 3 (K2 MODE=train, GPU) đẩy 2026-10-02T18:48:35Z → ERROR (CSLR smoke test), 12,14 GPU-phút. Hiện KHÔNG có kernel nào chạy (02:16 VN 3/10).
  (cũ:
  RUNNING lúc 18:51Z (orchestrator kiểm); ETA ≤ 19:49Z (§3.7, chưa xác minh), watchdog 105 phút ⇒ muộn nhất ~20:34Z (03:34 VN).
  Kiểm: `PYTHONUTF8=1 .venv/Scripts/kaggle kernels status phmvnsm33/vsl-retrain-cslr-vit5`.
- Giới hạn API: đã gặp lỗi 429 (reset 4:20 sáng, giờ Việt Nam). Xem orchestrator_resume_addendum.md mục 4 và usage_guard_addendum.md.

## Thay đổi chưa commit trong working tree (KHÔNG đụng)
- Của người dùng: xóa data/alphabet_landmarks_full.csv, data/hand_data.csv, data (2)/Dataset/Labels/label.csv
  (đã chuyển sang data/Dataset/Labels/label.csv). Không commit, không khôi phục.
- Nhiều file/thư mục untracked (data/, clone/, .agents/, .claude/skills/, data/splits/...): không add.
- (phát hiện 2026-10-03 15:30) ` M README.md` chưa commit — KHÔNG do agent kế hoạch 15 (coder báo là thay đổi của người dùng); không đụng, không commit; hỏi người dùng.

## Nhật ký khôi phục (thêm dòng mỗi lần khôi phục sau khi bị ngắt)
- 2026-10-03 23:10 | dừng theo yêu cầu người dùng (khởi động lại máy) | T2 đang chạy dở bị dừng sạch: agy Stop-Process, TaskStop subagent, savewip ad7c126 | Lưu STATE, commit, push; tiếp bằng prompt "tiếp tục" (xem Việc kế tiếp).
- 2026-10-04 00:40 | khôi phục sau khởi động lại máy (người dùng nhắn tiếp tục + dặn mở Google Drive.lnk) | STATE khớp git (HEAD d7f5a26, WIP T2 ad7c126), không agent/agy chạy | Giao vslt-coder hoàn thiện T2 từ WIP.
- 2026-10-04 15:15 | khôi phục sau tắt máy có chủ đích (người dùng báo lỗi U1b) | STATE khớp git (HEAD a78f7ba), không agent/agy chạy | Giao planner lần sửa 3 kế hoạch 15 (re-arm nhiều chữ liên tiếp).
- 2026-10-06 (cloud lần sửa 12): clone shallow → `git fetch --unshallow`; khôi phục dữ liệu gitignored để chạy test: checkpoints/alphabet_best.pt = output kernel `phmvnsm33/vsl-train-alphabet` (sha256 756eaf3f…, 34 lớp; KHÁC bản trong vslt-provenance-artifacts), video hauuto (dataset hauuto), landmark `vsl-extract-alphabet`, 3 file reports/alphabet_nested_2026-09-25 từ vslt-provenance-artifacts (sha khớp SHA256SUMS); cài seaborn vào .venv (requirements.txt).
- 2026-10-08 14:08 | khôi phục (người dùng nhắn "tiếp tục"; sleep nền bị dừng khi phiên cũ kết thúc) | STATE khớp git (HEAD 5826b2e, nhánh cloud/2026-10-04-level1-rearm), không agent chạy | Giao vslt-coder-claude sửa hạ tầng agy.
- 2026-10-08 18:15 | tối ưu hạn mức Claude theo yêu cầu người dùng (không phải ngắt) | STATE 104 KB, đọc lại mỗi lần khôi phục | Chuyển NGUYÊN VĂN lịch sử (đuôi "[Trước: …]", dòng 14–252 cũ, nhật ký khôi phục cũ) sang docs/STATE_archive.md; STATE còn 38 KB; sửa dòng HEAD; đính chính "thay đổi lạ" scripts/agy_* (đã commit 0538a01, ba9e107).
- 2026-10-08 22:58 | khôi phục (người dùng /clear + "tiếp tục") | STATE khớp git (HEAD b86547b), không agent chạy, 5h 1% | Giao planner ngoại lệ E4.
- 2026-10-09 02:12 | dừng có chủ đích: hạn mức 5h 74% (U2b không vừa cổng) + người dùng yêu cầu tắt máy | lưu STATE, commit, push | tiếp bằng "tiếp tục" → U2b.
- 2026-10-09 09:25 | khôi phục sau tắt máy có chủ đích (người dùng nhắn "tiếp tục") | STATE khớp git (HEAD e520e22, đã push), không agent chạy, 5h 0% | Giao vslt-coder-claude U2b.
