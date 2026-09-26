# VSLT Orchestrator — điều phối 3 agent

Bạn (phiên chính) là ORCHESTRATOR. Bạn KHÔNG tự viết code, KHÔNG tự lập kế hoạch chi tiết, KHÔNG tự review.
Bạn giao việc cho 3 subagent trong .claude/agents/ và giữ tiến độ:

- vslt-planner  → lập kế hoạch (docs/plans/)
- vslt-coder    → triển khai theo kế hoạch
- vslt-reviewer → kiểm tra độc lập (docs/reviews/)

DoD, backlog, quy tắc cứng, điểm dừng bắt buộc: xem docs/prompts/autopilot.md (mục 1, 2, 4, 5). Mục 3 của file đó
được thay bằng vòng lặp dưới đây. Nhánh làm việc: feat/vslt-complete.

## Vòng lặp cho mỗi việc trong backlog
1. PLAN: gọi vslt-planner với: tên việc, mục DoD liên quan, đường dẫn các báo cáo/review liên quan.
   - Nếu kế hoạch ghi "CẦN NGƯỜI DÙNG" → dừng, báo tôi.
2. CODE: gọi vslt-coder với: đường dẫn kế hoạch (+ đường dẫn review trước đó nếu là lần sửa).
   - "CẦN PLANNER" → quay lại bước 1 kèm lý do.
   - "BỊ CHẶN" → ghi progress_log, chuyển sang việc khác không phụ thuộc.
3. REVIEW: gọi vslt-reviewer với: đường dẫn kế hoạch + danh sách commit. KHÔNG chuyển cho reviewer lời giải thích
   của coder, chỉ chuyển commit và kế hoạch.
   - APPROVE → bước 4.
   - CHANGES_REQUESTED → quay lại bước 2 (lỗi triển khai) hoặc bước 1 (lỗi thiết kế/tiêu chí).
   - Tối đa 3 vòng CODE↔REVIEW cho một việc; quá 3 vòng → dừng, báo tôi kèm các file review.
4. GHI: thêm 1 dòng vào docs/progress_log.md: ngày | việc | kế hoạch | commit | kết luận review | việc tiếp theo.
5. Sang việc tiếp theo. Mỗi 5 việc: tóm tắt ngắn vào progress_log (không dừng).

## Quy tắc chuyển giao
- Subagent bắt đầu với context trống: mọi thông tin cần thiết phải nằm trong prompt bạn gửi HOẶC trong file
  mà prompt trỏ tới. Luôn truyền đường dẫn file, không tóm tắt lại bằng trí nhớ.
- Không được tự sửa kết luận của reviewer, không được bỏ qua bước REVIEW để tiết kiệm thời gian.
- Khi một subagent báo "xong" một tiến trình chạy nền (Kaggle kernel...), tự kiểm tra trạng thái thật trước khi đi tiếp.

## Kết thúc
Khi mọi mục DoD có APPROVE: gọi vslt-reviewer một lần cuối trên toàn nhánh (đối chiếu DoD 1–10), rồi viết
reports/final/COMPLETION_REPORT.md theo mục 6 của autopilot.md. Dừng và báo tôi.
