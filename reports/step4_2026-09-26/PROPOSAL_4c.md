# Đề xuất 4c — cấu trúc Cấp 2

**Khuyến nghị: B — giữ model gộp cho "Ký từ"**; khuyến nghị có điều kiện: 4c chỉ đo một cách tách. Không có luật A/B đăng ký trước — người dùng quyết định. Số chép từ `REPORT.md`.

## Bằng chứng ủng hộ B
- Kết quả chính, đã đăng ký (REPORT mục 4), cùng 721 clip QIPEDC TEST: model gộp H-keepz-360 top-1 12.2% (88/721) [10.0, 14.8], model từ điển dict_keepz_360 3.2% (23/721) [2.1, 4.7]; top-10 32.0% (231/721) so với 13.3% (96/721); McNemar p = 1.06e-14.
- Thăm dò (a): giới hạn model gộp về 594 nhãn của model từ điển vẫn đạt 12.8% (92/721).

## Phạm vi
- Model từ điển được train từ đầu, cùng công thức với model gộp; `scripts/train_unified.py` không có tùy chọn khởi tạo từ trọng số.
- Nó chưa khớp tập train: train top-1 ở epoch cuối 34.21% so với 95.47% (model gộp); 624 so với 23226 bước tối ưu (REPORT mục 4 "Phạm vi so sánh và mức khớp train"; trainer đo trên batch augment).
- Vậy 4c chỉ cho thấy tách train-từ-đầu bằng công thức hiện tại kém hơn gộp; KHÔNG loại trừ A với model từ điển train tới khi khớp hoặc khởi tạo từ trọng số VSL-GH / model gộp rồi fine-tune. Cách tách có khởi tạo vẫn dùng được dữ liệu VSL-GH.

## Bằng chứng chống B (ủng hộ A)
- Độ chính xác tuyệt đối vẫn thấp; chéo nguồn 15.4% (4/26) [6.1, 33.5].
- Bộ phân loại nguồn trên đầu vào hài hòa 360 px vẫn đạt 94.8 (4a: 99.5).
- Thăm dò (b), chỉ dự đoán sai: lỗi của model gộp rơi vào lớp chỉ-VSL-GH ở 10.9% (69/634) clip QIPEDC, 81.3% (183/225) clip S06; tỷ lệ nền 282/876. Chỉ báo, không kiểm định.

## Giới hạn
- Ít mẫu mỗi lớp (593/594 lớp của model từ điển có ≤ 2 clip train); QIPEDC không có nhãn người ký.
- Một seed cho model từ điển và cho run 360 px; chênh seed của H-keepz (+1.61) gần bằng mức 360 px thắng (+1.72).
- CI rộng; Wilson giả định clip độc lập.
- "Ký câu = VSL-GH qua CSLR (Cấp 3)" của A KHÔNG được đánh giá trong Bước 4.
- Bộ phân loại nguồn đo trên đầu vào hài hòa, không trên biểu diễn trong model.
- Đường live chưa dùng `harmonize()`; realtime phải giảm về 360 px, có test tương đương.

## Điều gì sẽ làm đổi khuyến nghị
- Model từ điển train tới khi khớp, hoặc khởi tạo từ trọng số VSL-GH, mà ngang hay hơn model gộp trên 721 clip. Thí nghiệm mới, tốn GPU (ước lượng 2.20 giờ mỗi run mỗi seed), cần người dùng duyệt.
- Bộ test webcam Bước 5, hoặc thêm dữ liệu/seed, đảo ngược kết quả chính.

## Không làm trong việc này; việc SAU khi người dùng duyệt
Không đổi model mặc định của backend. Nếu duyệt B: (1) nối `harmonize()` vào đường live, gồm 360 px và cắt đoạn nghỉ (run được chọn train với trim=true; bỏ cắt nghỉ thì phải train lại), kèm test tương đương; (2) điểm dừng riêng trước khi đổi model mặc định; (3) đo trên bộ webcam Bước 5.
