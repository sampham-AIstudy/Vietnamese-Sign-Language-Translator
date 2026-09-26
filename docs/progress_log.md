# VSLT progress log

Nhánh: feat/vslt-complete (tách từ fix/audit-round2). Quy trình: docs/prompts/orchestrator.md + docs/prompts/autopilot.md.

## Ghi chú của người dùng (2026-09-26) — planner phải tính tới

1. DoD 8 (độ trễ): lần đo trước 90.78 ms (reports/audit_round2/v1_latency_benchmark.json, commit 536c7c5) và lần
   chạy lại 492 ms (p99 1994 ms; bản sao lưu ở ../_backup_audit_round2_rerun_2026-09-24/) mâu thuẫn nhau.
   Đo lại qua WebSocket thật ít nhất 3 lần, ghi cấu hình máy và tải CPU/GPU lúc đo, báo cả mean/p50/p95/p99.
   Cho tới lúc đó, đánh dấu 90.78 ms trong EVALUATION.md / reports/audit_round2/VERIFY.md /
   reports/audit_round2/AUDIT_ROUND2.md là "chưa xác minh lại".
2. configs/alphabet_config.yaml trỏ tới dữ liệu 42 chiều đã bị xóa (data/alphabet_landmarks_full.csv) và không còn
   code nào dùng: đưa vào việc dọn dẹp ở cuối backlog (đề xuất xóa hoặc chuyển vào configs/legacy/,
   HỎI NGƯỜI DÙNG trước khi xóa).
3. Thay đổi chưa commit của người dùng trong thư mục làm việc (xóa `data (2)/Dataset/Labels/label.csv`,
   `data/alphabet_landmarks_full.csv`, `data/hand_data.csv`): KHÔNG commit, KHÔNG khôi phục, KHÔNG xóa.

## Nhật ký

ngày | việc | kế hoạch | commit | kết luận review | việc tiếp theo
--- | --- | --- | --- | --- | ---
