# Bước 4a–4c và 5 — bản đầy đủ (thay thế mọi bản trước)

Bối cảnh: reports/source_diagnostics_2026-09-26/REPORT.md (commit f920ebf, 8d78658).
Quy tắc chung giữ nguyên: không xóa dữ liệu/checkpoint, train nặng trên Kaggle (private, T4), mọi số liệu sinh
tự động từ JSON có lệnh chạy + commit hash, chọn model bằng VAL, TEST chạy một lần.
Chạy subagent vslt-reviewer (nếu đã cài) trước mỗi điểm dừng và dán kết quả vào báo cáo.

**Thứ tự: 4a → 4b → 4c → DỪNG báo tôi → 5.**

## Quyết định đã chốt (không cần hỏi lại)
- HCMUE: KHÔNG dùng để train và KHÔNG dùng làm thước đo (chỉ 23 clip đạt ngưỡng thuộc bộ nhãn). Giữ làm video tham khảo.
- Realtime hiện dùng webcam 640×480, JPEG 0.75, lật gương chỉ ở CSS. Mọi thay đổi độ phân giải trong 4b phải áp dụng
  cho cả đường realtime, kèm test tương đương (cùng 1 video qua đường train và đường realtime → tensor giống nhau).

## 4a. Kiểm tra lối tắt trên 85 lớp chung
Mục đích: 100% "đoán nguồn" là do lối tắt (khung hình, độ dài) hay chỉ do hai nguồn có bộ từ khác nhau.
1. Lấy 85 lớp có ở cả VSL-GH và QIPEDC. Cân bằng số mẫu mỗi lớp giữa hai nguồn (lấy mẫu xuống).
2. Chạy lại bộ phân loại nguồn (VSL-GH vs QIPEDC) trên tập cân bằng này, GroupKFold theo recording_id,
   đủ các nhóm đặc trưng như bảng bước 1 (all, pose x/y, pose z, độ dài clip, hình dạng tay, hand x/y, hand z, joint presence).
3. Kết luận: vẫn gần 100% → lối tắt có thật. Giảm mạnh → phần lớn do khác bộ từ.
4. Đánh giá chéo nguồn của model hiện tại trên 85 lớp này, LOẠI 4 từ ký khác nhau (xem, kết quả, yếu, thường xuyên).

## 4b. Hài hòa dữ liệu + train lại (THÍ NGHIỆM)
Áp dụng GIỐNG NHAU cho mọi nguồn và cho đường realtime:
- Chỉ giữ tay + cánh tay; chuẩn hóa theo vai (tâm giữa hai vai, scale theo độ rộng vai). Bỏ mặt, hông
  (loại luôn vấn đề khóe miệng 9/10).
- BỎ trục z của pose. Với z của bàn tay: chạy 2 biến thể (giữ / bỏ), báo cả hai.
- Khớp ngón cái 21/22: lấy từ hand model cho mọi nguồn, hoặc bỏ; ghi rõ lựa chọn.
- Cắt đoạn nghỉ bằng ngưỡng chuyển động (cùng ngưỡng cho mọi nguồn và realtime), resample theo THỜI GIAN về độ dài cố định.
- Độ phân giải: thử QIPEDC ở ~360px cho khớp VSL-GH. Nếu chọn phương án này, realtime cũng phải giảm về cùng mức.
- Augmentation khi train: scale, xoay, tốc độ 0.7–1.3, cắt ngẫu nhiên theo thời gian.
  Kết quả chính KHÔNG dùng test-time augmentation; TTA (nếu có) chỉ báo như kết quả phụ.

Báo cáo:
- 3 nhóm như cũ (S06, QIPEDC-only ≥2 bản quay, tổng), Top-1/Top-5 + CI.
- Đánh giá chéo nguồn trên 85 lớp chung (đã loại 4 từ).
- Bộ phân loại nguồn chạy lại trên đặc trưng đã hài hòa (dùng tập cân bằng của 4a).
- Kết luận về cắt đoạn nghỉ (lần này đã train lại).

## 4c. Thí nghiệm tách Cấp 2 theo chế độ
Giả thuyết: "từ cắt ra từ câu" (VSL-GH) và "từ đơn lẻ kiểu từ điển" (QIPEDC) là hai loại dữ liệu khác bản chất,
gộp vào một bộ phân loại 876 lớp thì model sẽ học cách phân biệt chúng.
1. Train bộ phân loại "Ký từ" CHỈ trên dữ liệu từ đơn lẻ (QIPEDC), split theo recording_id, dùng cách hài hòa tốt nhất từ 4b.
2. So sánh với model gộp (của 4b) trên CÙNG test QIPEDC sạch. Top-1/Top-5/Top-10 + CI, McNemar.
3. Viết đề xuất ngắn (≤ 1 trang): Cấp 2 nên
   - (A) tách: chế độ "Ký từ" = model từ đơn lẻ; chế độ "Ký câu" = VSL-GH qua CSLR (Cấp 3), hay
   - (B) giữ model gộp.
   Nêu rõ bằng chứng cho lựa chọn và giới hạn còn lại (ít mẫu mỗi lớp, không có nhãn người ký).

**DỪNG sau 4c, gửi tôi REPORT (dạng file).**

## 5. Bộ test webcam (CHUẨN BỊ, chưa quay)
1. Danh sách (a): 20–30 từ đơn lẻ có video QIPEDC rõ ràng, ưu tiên từ thông dụng. Kèm đường dẫn video mẫu để tôi xem và ký theo.
2. Danh sách (b): 10 câu ngắn trong VSL-GH. Kiểm tra có dựng được hoạt ảnh skeleton từ keypoint VSL-GH đủ rõ
   để học cách ký không. Nếu không → báo tôi và bỏ phần (b).
3. Script quay đi qua ĐÚNG đường realtime (webcam 640×480 → extractor backend), lưu landmark + metadata
   (signer_id ẩn danh, tay thuận, ánh sáng, nền, ngày quay). Không lưu video nếu tôi không bật tùy chọn.
4. Script đánh giá: chạy model mặc định, model gộp và model từ đơn lẻ (nếu có) trên bộ webcam; báo Top-1/Top-5 theo từ.
