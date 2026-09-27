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

## Quyết định của người dùng tại điểm dừng 4c (2026-09-27) — bắt buộc tuân theo

1. 4c: chọn **B**. Ứng viên Cấp 2 = **H-keepz-360** (reports/step4_2026-09-26/runs/run_keepz_360). CHƯA đổi model
   mặc định — đó là GATE riêng.
2. Không làm (i) (train model từ điển tới khi khớp). Thêm (ii) — fine-tune model từ điển khởi tạo từ trọng số
   H-keepz-360 — vào CUỐI backlog, chỉ sau khi DoD 1–7 xong; planner phải đăng ký trước tiêu chí so sánh
   (cùng 721 clip QIPEDC TEST, chọn epoch bằng VAL) TRƯỚC khi chạy.
3. 360 px: chấp nhận theo luật, không chạy thêm seed. Đường realtime hạ frame về chiều cao 360 TRƯỚC MediaPipe,
   kèm test tương đương train–realtime.
4. Cắt đoạn nghỉ: GIỮ ở đường realtime, cùng tham số preprocessing lưu trong checkpoint. Chế độ "Ký từ" gom trọn
   một ký hiệu (bắt đầu chuyển động → tay nghỉ) rồi mới dự đoán; planner thiết kế luồng này (bộ đệm, timeout,
   trạng thái "đang ghi ký hiệu" trên giao diện).
5. REPORT_partial.md: chuyển ra ../_backup_step4/, không commit. Thêm reports/**/*.pt (và logits *.npz) vào
   .gitignore; tải checkpoint + logits các run bước 4 lên một Kaggle dataset PRIVATE làm lưu trữ, ghi slug + sha256
   vào REPORT.md.
6. 3 góp ý nhỏ của reviewer vòng 2 (G1 test AC5 chỉ so §1–5; G2 cách đếm từ PROPOSAL; G3 PROPOSAL dòng 17 mẫu số
   634 + lưu ý S06): sửa trong đợt kế tiếp, cùng một vòng review.

Thứ tự tiếp theo: (việc dọn dẹp mục 5–6) → Việc 4 (endpoint chuỗi landmark Cấp 1) → nối harmonize() vào đường live
(360 px + cắt nghỉ + luồng gom ký hiệu, test tương đương) → Việc 5 (nối frontend) → Việc 6 (nút chế độ, Ký từ,
Ký câu) → DỪNG ở GATE đổi model mặc định Cấp 2 với bảng so sánh model cũ vs H-keepz-360 trên cùng tập test sạch.

## Nhật ký

ngày | việc | kế hoạch | commit | kết luận review | việc tiếp theo
--- | --- | --- | --- | --- | ---
2026-09-26 | Bước 4a–4c: REPORT + PROPOSAL 4c | `docs/plans/01-buoc4-hoan-tat-4a-4c.md` | 72abc13, f4729ff, 8c08845, c54b772, 67ff25a, 65a2821 + commit R6 (commit ghi dòng này: REPORT/JSON sinh lại với `--review-file docs/reviews/01-review.md` có vòng 2, kèm file review và kế hoạch) | APPROVE — vòng 2/3 (docs/reviews/01-review.md); vòng 1 CHANGES_REQUESTED (FAIL mục 13 = M1), đã sửa ở Lần sửa 1 | ĐIỂM DỪNG sau 4c — chờ người dùng quyết định (5 câu hỏi trong review vòng 2)

Test (dòng trên): AC2 (10 module handoff) 53 → 53 OK; `tests.test_report_step4` 38 → 69 OK, 0 skip (+24 ở c54b772: AC1 ca 16–23 + hợp đồng history.json; +7 ở 67ff25a: AC5b); `git diff 8c08845 HEAD -- tests/test_report_step4.py` chỉ có dòng thêm. GitNexus: 72abc13/f4729ff/8c08845 đã chạy `detect-changes --scope staged` (không viết lại lịch sử); từ Lần sửa 1 chạy `--scope all`: c54b772 HIGH (do lệch dòng khi chèn hàm mới; `git diff -U0` chỉ đổi build, render + hàm mới; 7 luồng đều trong scripts/report_step4.py), 67ff25a LOW, 65a2821 LOW, commit R6: xem commit message. `impact` (upstream): build, render, _hist_summary, parse_args đều LOW (render lower-bound, text search: chỉ main() và test gọi). Không có lệnh Kaggle push/run. R6 (HEAD 65a2821 khi sinh): lệnh header + `--review-file` chạy hai lần → `cmp` trùng khít; AC9 so với 67ff25a: REPORT chỉ khác dòng Lệnh/HEAD, dòng inputs của review, mục 6; JSON `==` sau khi bỏ generated_by/review/input review; test_report_step4 69 OK, AC2 53 OK.
