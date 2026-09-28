# STATE — nguồn sự thật để tiếp tục (docs/STATE.md)

> Orchestrator PHẢI đối chiếu file này với `git log` và `docs/progress_log.md` mỗi khi khôi phục, sửa chỗ sai,
> ghi 1 dòng vào "Nhật ký khôi phục", rồi mới làm tiếp.

- Cập nhật lần cuối: 2026-09-29 00:15 (giờ Việt Nam)
- HEAD: 20b0c36 | Nhánh: feat/vslt-complete
- Trạng thái phiên: ĐANG LÀM — vslt-coder kế hoạch 05 chặng [B7, B8] (giao 00:15, HEAD 20b0c36, 5h 0%, cổng 30 ≤ 90).
  Sau đó: vslt-reviewer toàn bộ kế hoạch 05 (xác minh HIGH ở B3, CRITICAL ở B4; AC10-c).
- Hạn mức (00:13): 5 giờ 0% (reset 05:50 giờ VN), 7 ngày 17% (reset 1790820000). Sổ đo: docs/usage_ledger.csv

## Đã xong (đã APPROVE)
- Bước 4a–4c (kế hoạch 01): kết luận B. Ứng viên Cấp 2 = H-keepz-360. Báo cáo: reports/step4_2026-09-26/REPORT.md;
  review: docs/reviews/01-review.md (APPROVE vòng 2).
- Dọn dẹp sau 4c (kế hoạch 02, `docs/plans/02-don-dep-sau-4c.md`): .gitignore `reports/**/*.pt` + `reports/**/*.npz`,
  lưu trữ Kaggle dataset private `phmvnsm33/vslt-step4-artifacts` (manifest `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`),
  sửa 3 góp ý nhỏ G1–G3. Review: docs/reviews/02-review.md (APPROVE vòng 3); commit cuối 4fbc1a2.
- Việc 4 (kế hoạch 03) — endpoint chuỗi landmark Cấp 1: APPROVE vòng 2 (docs/reviews/03-review.md), commit 8bba04e, 253 test pass.
  Hợp đồng API: tọa độ chuẩn hóa MediaPipe |v| ≤ 10; khung không có tay gửi null/[]; khung 21 điểm trùng hệt → 422; endpoint ảnh cũ trả 409.
- Kế hoạch 04 — harmonize() vào đường live "Ký từ" (360px, CleanHolisticExtractor, SignSegmenter, WS v2): APPROVE vòng 1
  (docs/reviews/04-review.md), commit af6d384, 310 test pass. Model mặc định KHÔNG đổi (ứng viên: VSL_MODEL_TYPE=stgcn_h360).

## Đang chạy / dở dang
- Kế hoạch 05 (thực thi quyết định 2026-09-28): planner XONG — docs/plans/05-thuc-thi-quyet-dinh-0928.md (commit cùng lượt này).
  Không có CẦN NGƯỜI DÙNG trước khi code; 6 điểm dừng có điều kiện ở §7. Lưu trữ: dataset private MỚI phmvnsm33/vslt-provenance-artifacts
  (script mới scripts/archive_private_kaggle.py); planner thêm checkpoints/alphabet_best.pt vào lưu trữ — orchestrator CHẤP NHẬN.
  Chặng coder: [B0,B1,B2] → [B3,B4] → [B5] → [B6,B7,B8].
  - Coder XONG B0 + B1 (commit 22f891c; tiến độ docs/plans/05-progress.md). B0: không điểm dừng nào kích hoạt; Kaggle xác thực được;
    (e) xác nhận; file nhị phân track duy nhất = alphabet_real_best.pt. B1: status chỉ {source, n_signers}; 73 test OK (4 module).
    Mốc B0: 20 module cũ 334 OK, 0 skip. Còn: B2–B8. Ghi chú cho reviewer: 05-progress.md nằm trong commit B1 (ngoài danh sách AC1).
  - Coder XONG B2 (77f4da3, /api/classes 503), B3 (0e1d737, dropped_frames; detect-changes HIGH — 11 luồng /ws/live-stream, thay đổi 1 biểu thức + docstring),
    B4 (9e2c64a, AC5 không PASS rỗng; CRITICAL trên đồ thị do gộp symbol trùng tên trong test, 0 dòng production). Reviewer phải xác minh HIGH/CRITICAL.
  - Coder XONG B5 (46674ab): scripts/archive_private_kaggle.py + 27 test API giả; 13 file, 8.36 MB; chưa chạy lệnh Kaggle nào.
  - Coder XONG B6 (8a73e9d): dataset PRIVATE phmvnsm33/vslt-provenance-artifacts đã upload + verify, manifest đã commit.
    Chi tiết lệnh Kaggle + exit code: docs/plans/05-progress.md mục B6. Dừng trước B7 theo yêu cầu người dùng.
    Verify: private từ 2 nguồn (dataset_list_mine + dataset_metadata), 13 file, 8363141 byte, sha256 sau tải khớp 13/13.
    AC10-d (V1–V6 True, JSON khớp) và AC10-e (restore root tạm 13/13 khớp; root mặc định không ghi đè) PASS. AC10-c để reviewer.
    f4d38f0: progress — tạm dừng sau B6. Bản nháp test AC11 (B7) để NGOÀI repo:
    ../_plan05_tmp/test_private_artifacts.py.draft (chưa chạy; ca AC11-g chỉ pass sau commit B7).
  - Còn lại: B7 (git rm --cached alphabet_real_best.pt, KHÔNG viết lại lịch sử),
    B8 (AC2 25 module + progress_log), rồi review kế hoạch 05.
    Nếu bị ngắt: giao lại coder với kế hoạch + 05-progress.md, tiếp tục từ bước dở.

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

## Câu hỏi chờ người dùng
- (không có)

## Backlog còn lại (thứ tự)
1. Thực thi quyết định người dùng 2026-09-28 (planner → coder → reviewer, một kế hoạch nhỏ, số 05):
   a) bỏ alphabet_real_best.pt khỏi git (git rm --cached, .gitignore), KHÔNG viết lại lịch sử;
   b) /api/fingerspelling/status chỉ trả nguồn dữ liệu + số người ký;
   c) lưu bằng chứng nguồn gốc (2 .pt nested + nested_predictions.csv) + alphabet_real_best.pt lên Kaggle dataset PRIVATE,
      kèm mở rộng §7.2 (log kernel, run_seed43/history.json, đầu vào không track); ghi slug + sha256;
   e) xác nhận REPORT_partial.md đã ra ../_backup_step4/ và .gitignore có reports/**/*.pt, reports/**/*.npz.
   f) việc nhỏ từ review 04 (triển khai, thấp): AC5 assert ≥ 1 event; test backend checkpoint `features` lạ → 503/1011;
      `dropped_frames` không đếm message lỗi/control; /api/classes trả 503 thay vì 500 khi model không dùng được.
2. Việc 5: nối frontend với endpoint mới (hợp đồng WS v2, Cấp 1 gửi null/[] cho khung không có tay; tọa độ chuẩn hóa MediaPipe);
   chạy backend + frontend cùng nhau; WebSocket qua proxy /ws; thu hẹp CORS chỉ origin dev, không "*" kèm credentials
   (cùng đợt: kiểm Origin WS, bind); sửa scripts/smoke_test_phase12.py cho WS v2; ghi hợp đồng vào docs/phase12_api.md.
   Planner quyết chính sách ký hiệu phát lặp (W03251B) và tốc độ segmenter theo dt từng frame (review 04, mục 8–9).
3. Việc 6: nút chọn chế độ; Ký từ; Ký câu (kiểm tra ViT5 đã học câu nào trước khi đo trên S06).
4. Từ điển 3 miền (SQLite: words, recordings, clips, signers).
5. GATE đổi model mặc định Cấp 2 (chỉ sau Việc 5 — UI mới dùng được đường h360): bảng so sánh model cũ vs H-keepz-360 trên cùng tập test sạch.
6. Bước 5: bộ test webcam (script quay + đánh giá; việc QUAY là của người dùng).
7. Đo độ trễ (DoD 8; ≥ 3 lần qua WebSocket thật, ghi cấu hình máy + tải). reports/audit_round2/v1_latency_benchmark.json: phần tách
   thành phần dựa trên tỷ lệ bịa 0.4/0.6 → đánh dấu không dùng; 90.78 ms "chưa xác minh lại" trong EVALUATION/VERIFY/AUDIT_ROUND2.
8. Dọn dẹp: report_step4.py đọc thêm manifest vslt-provenance-artifacts để REPORT bước 4 không còn ghi 8 đầu vào 'không lưu trữ';
   configs/alphabet_config.yaml (hỏi trước khi xóa); sửa câu chữ AC7-e kế hoạch 04; phương án (ii) (đăng ký trước tiêu chí).

## Tài nguyên
- Kaggle GPU tuần này: ~6 giờ đã dùng (ước tính của người dùng, chưa xác minh), giới hạn tự đặt 10 giờ/tuần.
- Kaggle kernel đang chạy: không có ghi nhận nào.
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
