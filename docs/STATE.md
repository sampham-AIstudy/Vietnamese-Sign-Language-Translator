# STATE — nguồn sự thật để tiếp tục (docs/STATE.md)

> Orchestrator PHẢI đối chiếu file này với `git log` và `docs/progress_log.md` mỗi khi khôi phục, sửa chỗ sai,
> ghi 1 dòng vào "Nhật ký khôi phục", rồi mới làm tiếp.

- Cập nhật lần cuối: 2026-09-28 11:10 (giờ Việt Nam)
- HEAD: af6d384 (+ commit bootstrap "chore: resume protocol + usage guard + STATE") | Nhánh: feat/vslt-complete
- Trạng thái phiên: ĐANG LÀM — orchestrator đang chạy, chờ vslt-reviewer kế hoạch 04
- Hạn mức: không biết (chưa có `%USERPROFILE%\.claude\vslt_usage.json` thật)

## Đã xong (đã APPROVE)
- Bước 4a–4c (kế hoạch 01): kết luận B. Ứng viên Cấp 2 = H-keepz-360. Báo cáo: reports/step4_2026-09-26/REPORT.md;
  review: docs/reviews/01-review.md (APPROVE vòng 2).
- Dọn dẹp sau 4c (kế hoạch 02, `docs/plans/02-don-dep-sau-4c.md`): .gitignore `reports/**/*.pt` + `reports/**/*.npz`,
  lưu trữ Kaggle dataset private `phmvnsm33/vslt-step4-artifacts` (manifest `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`),
  sửa 3 góp ý nhỏ G1–G3. Review: docs/reviews/02-review.md (APPROVE vòng 3); commit cuối 4fbc1a2.
- Việc 4 (kế hoạch 03) — endpoint chuỗi landmark Cấp 1: APPROVE vòng 2 (docs/reviews/03-review.md), commit 8bba04e, 253 test pass.
  Hợp đồng API: tọa độ chuẩn hóa MediaPipe |v| ≤ 10; khung không có tay gửi null/[]; khung 21 điểm trùng hệt → 422; endpoint ảnh cũ trả 409.

## Đang chạy / dở dang
- Kế hoạch 04 — nối harmonize() vào đường realtime "Ký từ" (`docs/plans/04-harmonize-duong-live.md`).
  - Coder: XONG B1–B7, 7 commit `04:` (0f07585, 9c894da, 4c9e24c, 5627010, b1d447a, 2807a8a, af6d384 = dòng progress_log, đã commit).
    AC8 19 module 310 OK, 0 skip (coder báo). Coder đã amend cục bộ b1d447a và af6d384 (chưa push) — reviewer đánh giá.
    detect-changes CRITICAL ở 4c9e24c (viết lại /ws/live-stream), b1d447a, 2807a8a.
  - Review: vslt-reviewer ĐÃ GIAO (~11:00, HEAD af6d384), đầu ra `docs/reviews/04-review.md` (chưa có file lúc 11:10).
    Nếu bị ngắt: giao lại reviewer với đường dẫn file, hoàn thiện phần còn thiếu.
  - Lưu ý: protocol WS v2 gửi `session_info` trước → frontend hiện tại (RealtimeStream.jsx, Phase12Pipeline.jsx) và
    scripts/smoke_test_phase12.py có thể hỏng cho tới Việc 5.
  - Model mặc định KHÔNG đổi (ứng viên chỉ bật bằng `VSL_MODEL_TYPE=stgcn_h360`).

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

## Câu hỏi chờ người dùng
- (không có)

## Backlog còn lại (thứ tự)
1. Review kế hoạch 04 (vslt-reviewer) → nếu APPROVE: chuyển sang "Đã xong", commit cùng dòng progress_log của coder.
2. Thực thi quyết định người dùng 2026-09-28 (đi qua planner → coder → reviewer, một kế hoạch nhỏ):
   a) bỏ alphabet_real_best.pt khỏi git (git rm --cached, .gitignore), KHÔNG viết lại lịch sử;
   b) /api/fingerspelling/status chỉ trả nguồn dữ liệu + số người ký;
   c) lưu bằng chứng nguồn gốc (2 .pt nested + nested_predictions.csv) + checkpoint (alphabet_real_best.pt) lên Kaggle dataset PRIVATE,
      kèm mở rộng §7.2 (log kernel, run_seed43/history.json, đầu vào không track); ghi slug + sha256;
   e) kiểm tra REPORT_partial.md và .gitignore cho *.pt đã làm chưa (quyết định 4c mục 5). Ghi nhận lúc bootstrap (chỉ đọc):
      ../_backup_step4/REPORT_partial.md tồn tại, reports/step4_2026-09-26/ không còn file này; .gitignore có `reports/**/*.pt`,
      `reports/**/*.npz` — reviewer xác nhận lại.
   (d — thu hẹp CORS — nằm trong Việc 5.)
3. Việc 5: nối frontend với endpoint mới (hợp đồng WS v2, Cấp 1 gửi null/[] cho khung không có tay); chạy backend + frontend cùng nhau;
   WebSocket qua proxy /ws; d) thu hẹp CORS chỉ origin dev, không "*" kèm credentials.
4. Việc 6: nút chọn chế độ; Ký từ; Ký câu (kiểm tra ViT5 đã học câu nào trước khi đo trên S06).
5. Từ điển 3 miền (SQLite: words, recordings, clips, signers).
6. GATE đổi model mặc định Cấp 2: bảng so sánh model cũ vs H-keepz-360 trên cùng tập test sạch.
7. Bước 5: bộ test webcam (script quay + đánh giá; việc QUAY là của người dùng).
8. Đo độ trễ (DoD 8; 90.78 ms cũ vs 492 ms chạy lại mâu thuẫn — đo lại ≥ 3 lần qua WebSocket thật).
9. Dọn dẹp: configs/alphabet_config.yaml (hỏi trước khi xóa); phương án (ii) (đăng ký trước tiêu chí).

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
