# Phụ lục orchestrator — kiểm tra hạn mức trước khi làm (docs/prompts/usage_guard_addendum.md)

Ghép cùng orchestrator_resume_addendum.md. Phụ lục này chỉ thêm việc ĐỌC hạn mức; giao thức lưu trạng thái
và khôi phục vẫn theo phụ lục kia.

## 1. Nguồn số liệu
- Bạn KHÔNG gõ được /usage và không cần: cùng số liệu nằm trong file `%USERPROFILE%\.claude\vslt_usage.json`,
  do status line của Claude Code ghi (script vslt_statusline.ps1). Đọc bằng công cụ đọc file hoặc
  `cat "$USERPROFILE/.claude/vslt_usage.json"`.
- Trường: five_hour_used_pct, five_hour_resets_at, seven_day_used_pct, seven_day_resets_at (epoch giây, UTC),
  written_at (epoch giây lúc ghi).
- Số cũ: nếu now − written_at > 1200 giây (20 phút) hoặc file không có → coi là KHÔNG BIẾT. Không được bịa số.
  Khi không biết: chỉ giao việc vừa/nhỏ, cập nhật STATE.md thường xuyên hơn, và ghi "hạn mức: không biết" vào STATE.md.
- Số liệu có thể trễ khi subagent chạy dài (status line cập nhật theo hoạt động của phiên chính).
  Vì vậy ngưỡng dưới đây cố ý thận trọng.

## 2. Khi nào đọc
- Trước MỖI lần giao subagent; sau MỖI lần subagent trả về; và trước khi bắt đầu việc mới trong backlog.

## 3. Ngưỡng (cửa sổ 5 giờ)
| Đã dùng | Hành động |
|---|---|
| < 80% | Làm bình thường. |
| 80–91% | KHÔNG giao việc lớn (planner cho kế hoạch dài, coder cho kế hoạch nhiều bước, reviewer cho kiểm toàn bộ).
  Chỉ giao việc nhỏ, hoặc chia việc lớn thành các phần nhỏ đã có điểm lưu. Cập nhật STATE.md sau mỗi phần. |
| ≥ 92% | WIND DOWN: không giao thêm việc. Chờ subagent đang chạy trả về (không giao lại nếu nó thất bại).
  Commit mọi thứ. Cập nhật STATE.md: `Trạng thái phiên: ĐANG CHỜ HẠN MỨC đến HH:MM (giờ Việt Nam, đổi từ
  five_hour_resets_at)`, việc dở, việc kế tiếp. Commit `state: wind-down theo hạn mức`. Rồi DỪNG và báo người dùng. |

## 4. Cửa sổ 7 ngày
- ≥ 90%: coi như vùng cảnh báo; chỉ làm các việc còn lại của DoD, hoãn mọi thí nghiệm phụ (phương án (ii), dọn dẹp).
- ≥ 95%: WIND DOWN như trên. seven_day_resets_at có thể cách nhiều ngày: ghi rõ thời điểm vào STATE.md,
  báo người dùng, KHÔNG chờ và KHÔNG thử lại.

## 5. Sau khi hạn mức hồi
- Phiên mới, hoặc người dùng nhắn "tiếp tục": chạy giao thức khôi phục (orchestrator_resume_addendum.md mục 3),
  đọc lại vslt_usage.json, xác nhận mức đã giảm, rồi làm tiếp từ "việc kế tiếp" trong STATE.md.
- Không bịa việc để làm khi đang chờ; không giao việc khi mức chưa giảm dưới 80%.

## 6. Lỗi 429 / "session limit" xảy ra trước khi kịp wind-down
- Xem mục 4 của orchestrator_resume_addendum.md. Việc dở của subagent bị ngắt có thể mất phần chưa ghi ra file:
  giao lại đúng agent đó với đường dẫn file đầu ra, yêu cầu hoàn thiện phần còn thiếu.
