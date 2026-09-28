# Phụ lục orchestrator — CÂN NGÂN SÁCH hạn mức trước khi làm (docs/prompts/usage_guard_addendum.md, bản 2)

Thay bản cũ. Ghép cùng orchestrator_resume_addendum.md (lưu trạng thái, khôi phục). Mục tiêu duy nhất:
KHÔNG bắt đầu một việc mà hạn mức còn lại không đủ để làm xong, để không bao giờ bị ngắt giữa chừng.
Cố ý chạm giới hạn thật là ĐIỀU CẤM.

## 1. Nguồn số liệu
- Đọc `%USERPROFILE%\.claude\vslt_usage.json` (status line ghi): five_hour_used_pct, five_hour_resets_at,
  seven_day_used_pct, seven_day_resets_at (epoch giây UTC), written_at.
- Số cũ (now − written_at > 1200 giây) hoặc thiếu file = KHÔNG BIẾT. Không bịa số.
  Khi không biết: chỉ giao đơn vị việc nhỏ nhất, ghi STATE.md sau mỗi đơn vị, và ghi "hạn mức: không biết".
- Status line chỉ cập nhật khi phiên chính có phản hồi API. Sau khi subagent trả về, số có thể chưa mới:
  đọc lại ở lượt kế tiếp của bạn; nếu written_at vẫn cũ hơn lúc subagent xong thì đánh dấu "chưa cập nhật".

## 2. Sổ đo chi phí thật: docs/usage_ledger.csv
Tạo file nếu chưa có, dòng đầu:
`time_utc,agent,plan,unit,five_before,five_after,five_delta,seven_delta,quality`
- Sau MỖI lần subagent trả về: điền 1 dòng. five_before = số đọc ngay trước khi giao; five_after = số đọc sau khi số đã cập nhật.
- quality: `ok` khi cả hai số đều mới; `stale` khi một trong hai cũ (dòng `stale` KHÔNG dùng để ước lượng).
- Người dùng có thể đang dùng chat/Claude Code chỗ khác trong cùng cửa sổ, nên delta chỉ là ước lượng thô:
  ghi chú vào cột quality nếu nghi ngờ (`noisy`). Commit sổ này cùng progress_log.

## 3. Cổng ngân sách trước MỖI lần giao subagent
1. Ước lượng chi phí `est` của đơn vị việc (theo agent + kích cỡ):
   - Có ≥ 3 dòng `ok` cùng loại agent: est = giá trị LỚN NHẤT trong 3 dòng gần nhất (không dùng trung bình).
   - Chưa đủ 3 dòng: est = 20 (điểm phần trăm) — GIÁ TRỊ KHỞI ĐẦU CHƯA ĐO, chỉ để thận trọng; thay bằng số đo thật ngay khi có.
2. Điều kiện bắt đầu (cửa sổ 5 giờ): `five_hour_used_pct + 1.5 × est ≤ 90`.
   Cửa sổ 7 ngày: `seven_day_used_pct + 1.5 × est_7d ≤ 95` (est_7d từ seven_delta; chưa có số thì bỏ qua điều kiện này
   nhưng nếu seven_day_used_pct ≥ 90 thì chỉ làm việc thuộc DoD, hoãn mọi thí nghiệm phụ).
3. Không đạt → KHÔNG giao. Thử chia nhỏ (mục 4). Nếu đơn vị nhỏ nhất vẫn không đạt → mục 5.

## 4. Chia đơn vị nhỏ để phần mất tối đa bị chặn
- Coder: không giao cả kế hoạch một lần. Giao theo chặng 1–3 bước của kế hoạch; mỗi chặng kết thúc bằng commit
  và cập nhật `docs/plans/<số>-progress.md`. Ngân sách thấp → giao 1 bước.
- Planner: với kế hoạch dài, viết theo từng mục và ghi ra file sau mỗi mục; ngân sách thấp → lập kế hoạch một phần
  (mục 1–4) rồi để phần còn lại cho phiên sau.
- Reviewer: chia theo nhóm hạng mục 1–13 (ví dụ 1–4, 5–9, 10–13), ghi kết quả từng nhóm ra file review ngay khi xong nhóm.
- Việc nào không chia được và est vượt ngân sách → mục 5.
- Vẫn chỉ 1 subagent nặng chạy tại một thời điểm.

## 5. Không đủ ngân sách: dừng SẠCH
1. Ghi STATE.md: `Trạng thái phiên: ĐANG CHỜ HẠN MỨC — 5h dùng X%, reset lúc HH:MM giờ VN (đổi từ five_hour_resets_at)`,
   việc kế tiếp và ước lượng chi phí của nó. Commit `state: chờ hạn mức`.
2. Dừng và báo người dùng đúng 3 dòng: mức hiện tại, việc kế tiếp cần khoảng bao nhiêu %, giờ có thể tiếp tục.
3. KHÔNG tiếp tục làm "việc nhỏ cho hết quota", KHÔNG thử lại liên tục, KHÔNG cố tình chạm giới hạn.
4. Cửa sổ 7 ngày: nếu không đủ, reset có thể cách nhiều ngày: ghi rõ thời điểm vào STATE.md, báo người dùng, không chờ.

## 6. Sau khi hạn mức hồi
- Phiên mới hoặc người dùng nhắn "tiếp tục": chạy giao thức khôi phục (orchestrator_resume_addendum.md mục 3),
  đọc lại vslt_usage.json, chạy lại cổng ở mục 3 với việc kế tiếp trong STATE.md.

## 7. Nếu vẫn bị 429 giữa chừng
- Coi là sai sót của ước lượng, không phải lỗi bình thường. Xem orchestrator_resume_addendum.md mục 4 để khôi phục.
- Ghi 1 dòng vào docs/usage_ledger.csv với quality=`limit_hit` và ghi vào STATE.md "ước lượng đã sai, tăng biên an toàn":
  đổi hệ số 1.5 thành 2.0 cho các lần sau cho đến khi người dùng cho phép đổi lại.
