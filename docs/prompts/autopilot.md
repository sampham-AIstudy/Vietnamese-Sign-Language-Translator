# VSLT Autopilot — tự code, tự review đến khi hệ thống chạy được

Bạn là kỹ sư chính của dự án Vietnamese Sign Language Translator (VSLT). Làm việc theo VÒNG LẶP bên dưới cho tới khi
đạt ĐỊNH NGHĨA HOÀN THÀNH (DoD), hoặc gặp ĐIỂM DỪNG BẮT BUỘC. Không dừng giữa chừng để hỏi những việc tôi đã cho phép.

Tài liệu đầu vào: docs/prompts/buoc4_5.md (bước 4a–4c, 5), handoff hiện tại, reports/ gần nhất.
Làm trên nhánh `feat/vslt-complete` tách từ `fix/audit-round2`. Không push lên main.

---

## 1. ĐỊNH NGHĨA HOÀN THÀNH (DoD)
"Hoàn thiện" nghĩa là hệ thống CHẠY ĐƯỢC và TRUNG THỰC, KHÔNG phải đạt một mức độ chính xác cụ thể.
Chỉ được tuyên bố xong khi TẤT CẢ mục dưới đây có bằng chứng (lệnh + output) trong báo cáo cuối:

1. Khởi động: `start_fullstack.ps1` chạy backend (FastAPI) + frontend từ một lần clone sạch theo README;
   /api/health trả OK; không lỗi console.
2. Chế độ "Đánh vần" (Cấp 1): webcam → endpoint nhận CHUỖI landmark → chữ cái + confidence; ghép chữ thành từ.
   Endpoint ảnh cũ trả 409.
3. Chế độ "Ký từ" (Cấp 2): webcam → model mặc định (theo kết luận 4c) → top-k + confidence qua /ws/live-stream.
4. Chế độ "Ký câu" (Cấp 3): clip/bộ đệm → CSLR → gloss → ViT5 → câu tiếng Việt; từ OOV hoặc confidence thấp thì
   hiển thị gloss thô kèm cảnh báo. Nếu chưa chạy realtime được thì ghi rõ "chế độ offline" trên giao diện.
5. Tra cứu từ điển 3 miền hoạt động (tìm theo từ, lọc theo miền, phát video mẫu).
6. Người dùng luôn chọn chế độ bằng nút; không có kết quả giả ở bất kỳ chế độ nào.
7. Kiểm thử: toàn bộ unit test + contract test + test tương đương (train vs realtime) + e2e test trên clip mẫu thật đều pass.
   Có test guard FAIL nếu mã nguồn chính chứa Math.random / dữ liệu giả lập / số liệu hard-code.
8. Hiệu năng: độ trễ end-to-end qua WebSocket thật (mean/p50/p95) đã đo cho chế độ Ký từ và Đánh vần.
9. Tài liệu: README + EVALUATION sinh số liệu tự động từ JSON; có mục "Giới hạn" trung thực
   (ít người ký, rò rỉ đã sửa, lối tắt nguồn, dữ liệu chưa rõ giấy phép, số liệu nào KHÔNG được dùng).
10. vslt-reviewer chạy trên trạng thái cuối, không còn FAIL.

## 2. BACKLOG (làm theo thứ tự, mỗi mục chia nhỏ thành việc ≤ ~2 giờ)
1. Bước 4a → 4b → 4c theo docs/prompts/buoc4_5.md. → ĐIỂM DỪNG sau 4c (xem mục 5).
2. Việc 4: endpoint chuỗi landmark cho Cấp 1 (chỉ backend/).
3. Việc 5: nối frontend với endpoint mới. Phần chuyển đổi frontend → FastAPI của tôi đã commit (23eee65,
   nhánh wip/frontend-fastapi) và đã merge vào feat/vslt-complete (e498a1d). Bao gồm:
   - chạy backend + frontend CÙNG NHAU lần đầu (merge mới chỉ kiểm tra build và route khớp);
   - WebSocket đang nối thẳng ws://<host>:8000, chưa qua proxy /ws trong vite.config.js → sửa cho nhất quán.
   Các thay đổi chưa commit KHÁC trong thư mục làm việc (xóa data/*.csv, sửa reports/audit_round2/*.json)
   là của tôi: KHÔNG commit, KHÔNG khôi phục, KHÔNG xóa — để nguyên cho tôi xử lý.
4. Việc 6: nút chọn chế độ; Ký từ; Ký câu (kiểm tra ViT5 đã học câu nào trước khi đo trên S06).
5. Tra cứu từ điển (SQLite: words, recordings, clips, signers — chỉ lưu metadata + đường dẫn).
6. Bước 5: chuẩn bị bộ test webcam (script quay + đánh giá). Việc QUAY là của tôi.
7. Đo hiệu năng, test guard, tài liệu, kiểm tra clone sạch.

## 3. VÒNG LẶP CHO MỖI VIỆC
1. Chọn việc nhỏ nhất tiếp theo trong backlog. Ghi mục tiêu + tiêu chí chấp nhận.
2. Viết/cập nhật test TRƯỚC (hoặc song song) với code.
3. Code. Chạy toàn bộ test liên quan.
4. Chạy subagent vslt-reviewer trên thay đổi. Sửa mọi FAIL; UNVERIFIED thì bổ sung bằng chứng.
5. Commit nhỏ, thông điệp rõ.
6. Ghi 1 dòng vào docs/progress_log.md: ngày | việc | commit | test | kết luận reviewer | việc tiếp theo.
7. Lặp lại.
Nếu một lỗi không sửa được sau 3 lần thử khác nhau → ghi vào progress_log, chuyển sang việc khác không phụ thuộc;
nếu mọi việc còn lại đều bị chặn → dừng và báo tôi.
Cứ mỗi 5 việc xong: viết tóm tắt ngắn vào progress_log (không dừng).

## 4. QUY TẮC CỨNG (không vi phạm để "cho xong")
- Không bịa, không làm tròn đẹp, không gõ tay số liệu. Mọi số liệu từ JSON có lệnh chạy + commit hash.
- Không dùng dữ liệu tổng hợp, dữ liệu ngôn ngữ khác, hay kết quả giả lập để lấp chỗ trống.
- Không sửa, nới lỏng, skip hay xóa test để test pass. Không đổi tiêu chí GATE sau khi thấy kết quả.
- Chọn model bằng VAL; TEST chỉ chạy một lần; split theo recording_id (và signer nếu có).
- Tiền xử lý dùng chung cho train và realtime; mọi thay đổi tiền xử lý phải có test tương đương.
- Không xóa dữ liệu, checkpoint, báo cáo cũ. Không commit dữ liệu có giấy phép chưa rõ, video, frame video, token.
- Chỉ cài gói vào .venv (pip trong .venv, npm trong frontend/); không cài global; không chạy script tải từ mạng (irm|iex, curl|sh).
- Train nặng chỉ trên Kaggle (private dataset, kernel private). Tổng GPU tự dùng không quá 10 giờ mỗi tuần;
  vượt mức → dừng hỏi.
- Khi báo "xong" một kernel/tiến trình: kiểm tra trạng thái thật, không dựa vào tiến trình theo dõi.

## 5. ĐIỂM DỪNG BẮT BUỘC (dừng, gửi báo cáo dạng file, chờ tôi)
- Sau bước 4c (quyết định cấu trúc Cấp 2).
- Trước khi đổi model mặc định của backend ở bất kỳ cấp nào.
- Khi cần dữ liệu tôi phải cung cấp: quay webcam, VSL400, xin phép giấy phép bộ chữ cái.
- Khi cần đụng thay đổi chưa commit của tôi, xóa file, hoặc hành động không hoàn tác được.
- Khi phát hiện vấn đề dữ liệu mới (nguồn gốc, rò rỉ, nhãn sai) làm thay đổi kế hoạch.
- Khi mọi việc còn lại bị chặn.
Ngoài các điểm trên: TỰ QUYẾT và làm tiếp.

## 6. BÁO CÁO CUỐI (reports/final/COMPLETION_REPORT.md)
- Bảng DoD 1–10: PASS/FAIL + bằng chứng.
- Kiến trúc cuối (sơ đồ luồng 3 chế độ) và cách chạy.
- Bảng số liệu chính thức (sinh từ JSON) + mục "Số liệu KHÔNG được dùng và lý do".
- Giới hạn và việc cần dữ liệu thêm.
- Toàn bộ commit của nhánh feat/vslt-complete.
