# Kế hoạch 08 — Segmenter live (backlog 2b)

**ĐANG LÀM** (planner đang viết; các mục chưa điền coi như chưa có)

- Nhánh lập kế hoạch: `cloud/2026-09-29-viec-a-d` (cloud). Ngày: 2026-09-29.
- Nguồn: `docs/STATE.md` "Backlog còn lại" mục 2b; `docs/reviews/04-review.md` mục S3.5, S4, "Thiết kế (planner)" 8–9;
  `docs/plans/06-viec5-frontend.md` §3.8 (vì sao tách khỏi Việc 5).
- Quyết định người dùng liên quan (không hỏi lại): "Cắt đoạn nghỉ: giữ ở realtime, tham số lấy từ checkpoint; chế độ Ký từ
  gom trọn một ký hiệu rồi mới dự đoán." Model mặc định KHÔNG đổi (GATE riêng).

## 1. Mục tiêu và DoD

**Mục tiêu.**
1. (Review 04 mục 8) Trong `SignSegmenter`, tốc độ cổ tay của frame mới nhất được tính theo khoảng thời gian THẬT giữa
   frame đó và frame liền trước (`dt` từng frame), thay vì `fps` trung bình của cửa sổ `activity_window_s`. Khi frame cách
   đều, kết quả (hoạt động từng frame + sự kiện) phải GIỐNG HỆT cách cũ.
2. (Review 04 mục 9) Có chính sách được đăng ký trước cho ký hiệu có nhịp nghỉ giữa chừng (loại `qipedc_W03251B`: một ký
   hiệu bị cắt thành 2 đoạn và phát 2 `sign_result` cùng gloss), với ngưỡng chọn trên TRAIN, kiểm trên VAL, không chạm
   TEST; hoặc — nếu bằng chứng TRAIN/VAL không ủng hộ đổi hành vi — ghi Giới hạn trung thực.

**DoD phục vụ.**
- DoD 3 (Ký từ qua `/ws/live-stream`, đường `harmonized_v1` ứng viên) và DoD 6 (không có kết quả giả: không phát trùng
  gloss do lỗi cắt đoạn mà người dùng tưởng là hai từ).
- DoD 7 (test tương đương train↔realtime: mọi thay đổi ở bước tiền xử lý live phải có test tương đương — ở đây là
  tương đương với luật `hand_activity` lúc train và với segmenter cũ khi fps đều).
- DoD 9 (mục "Giới hạn" trung thực: ghi rõ phần chính sách còn lại chưa giải được).
- Gián tiếp: GATE đổi model mặc định Cấp 2 (backlog 5) sẽ dùng đường này; việc này KHÔNG đổi model mặc định.

## 2. Hiện trạng
(đang viết)

## 3. Thiết kế
(chưa điền)

## 4. Chia việc
(chưa điền)

## 5. Tiêu chí chấp nhận (hợp đồng)
(chưa điền)

## 6. Rủi ro dữ liệu/ML
(chưa điền)

## 7. Điểm dừng
(chưa điền)
