# Phụ lục orchestrator — chống mất việc khi bị ngắt (docs/prompts/orchestrator_resume_addendum.md)

Ghép vào docs/prompts/orchestrator.md. Nếu mâu thuẫn, phụ lục này thắng.

## 1. Ghi STATE.md TRƯỚC khi giao việc, và SAU khi việc xong
- Trước khi gọi bất kỳ subagent nào: cập nhật mục "Đang chạy / dở dang" trong docs/STATE.md
  (tên agent, số kế hoạch, mục tiêu, thời điểm, HEAD hiện tại), rồi commit `state: giao <agent> cho kế hoạch <số>`.
- Ngay khi một việc được APPROVE: chuyển nó sang "Đã xong" (kèm commit, số test), cập nhật "Backlog còn lại"
  và progress_log.md trong CÙNG một commit.
- Khi người dùng đưa ra quyết định hoặc trả lời câu hỏi: ghi vào "Quyết định của người dùng" ngay lượt đó và commit.
- Không bao giờ để trạng thái quan trọng chỉ nằm trong hội thoại.

## 2. Subagent phải để lại dấu vết sớm (áp dụng khi giao việc)
Thêm câu này vào MỌI prompt giao cho subagent:
> Trong 5 phút đầu, tạo file đầu ra của bạn (docs/plans/..., docs/reviews/...) với khung mục và ghi "ĐANG LÀM".
> Cập nhật file sau mỗi phần hoàn thành. Bạn có thể bị ngắt bất cứ lúc nào; việc chưa ghi ra file coi như mất.
- Planner/Reviewer: ghi từng mục (hiện trạng, thiết kế, bảng 1–13...) ngay khi xong mục đó, không gom đến cuối.
- Coder: commit sau MỖI bước nhỏ của kế hoạch, thông điệp bắt đầu bằng `WIP 04:` cho bước dở,
  `04:` cho bước hoàn chỉnh. Ghi trong docs/plans/<số>-progress.md dòng "bước đã xong / bước đang làm / bước còn lại".

## 3. Giao thức khôi phục (khi phiên mới, khi "tiếp tục", hoặc sau lỗi/ngắt)
1. Đọc STATE.md → đối chiếu git (`git status`, `git log --oneline -15`, ls docs/plans docs/reviews).
2. Với mỗi việc trong "Đang chạy":
   - Có file kế hoạch/review ở trạng thái "ĐANG LÀM" hoặc thiếu mục → giao lại CHÍNH agent đó, kèm đường dẫn file,
     yêu cầu "hoàn thiện phần còn thiếu, không viết lại phần đã có".
   - Coder có commit `WIP` → giao lại coder với đường dẫn kế hoạch + progress file, yêu cầu tiếp tục từ bước dở.
   - Không có dấu vết nào → chạy lại từ đầu.
   - Đã có review APPROVE → chuyển sang "Đã xong", không làm lại.
3. Ghi 1 dòng vào "Nhật ký khôi phục" (nguyên nhân ngắt, việc dở, cách xử lý), commit, rồi làm tiếp.
4. Báo người dùng 3 dòng: đã khôi phục từ đâu, việc gì phải làm lại, việc gì đang chờ quyết định của họ.

## 4. Giới hạn API / rate limit
- Gặp lỗi 429 hoặc "session limit": KHÔNG gọi lại liên tục. Ghi vào STATE.md
  `Trạng thái phiên: ĐANG CHỜ GIỚI HẠN đến HH:MM (giờ Việt Nam)`, ghi việc dở, commit, rồi dừng gọn.
- Không chạy quá 2 subagent nặng cùng lúc; không để 2 agent cùng ghi một file.
  Coder chạy một mình khi có kế hoạch cần sửa backend/main.py. Ưu tiên chạy tuần tự khi gần hết hạn mức.
- Nếu phiên tự tiếp tục sau khi hết giới hạn: chạy đúng giao thức mục 3, không giả định agent nền còn sống.

## 5. Cuối mỗi lượt làm việc dài
Trước khi dừng hoặc khi ước lượng đã làm > 45 phút: cập nhật STATE.md (trạng thái, HEAD, việc kế tiếp) và commit.
