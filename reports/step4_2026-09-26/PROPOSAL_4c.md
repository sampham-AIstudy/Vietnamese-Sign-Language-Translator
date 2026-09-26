# Đề xuất 4c — cấu trúc Cấp 2

**Khuyến nghị: B — giữ model gộp cho chế độ "Ký từ".** Đây là đề xuất; không có luật A/B đăng ký trước — người dùng quyết định. Mọi số chép từ `REPORT.md` cùng thư mục.

## Bằng chứng ủng hộ B
- Kết quả chính, đã đăng ký (REPORT mục 4): trên cùng 721 clip QIPEDC TEST, model gộp H-keepz-360 đạt top-1 12.2% (88/721) [10.0, 14.8], model từ điển dict_keepz_360 đạt 3.2% (23/721) [2.1, 4.7]; top-10: 32.0% (231/721) so với 13.3% (96/721). McNemar chính xác: n10 = 7, n01 = 72, p = 1.06e-14.
- Thăm dò (a), không đăng ký trước: giới hạn model gộp về đúng 594 nhãn của model từ điển vẫn đạt 12.8% (92/721), nên lợi thế không đến từ không gian nhãn.
- Model từ điển chỉ có 795 clip train, 593/594 lớp có ≤ 2 clip (REPORT mục 4, mục 5). Tách ra thì "Ký từ" mất toàn bộ dữ liệu VSL-GH.

## Bằng chứng chống B (ủng hộ A)
- Độ chính xác tuyệt đối trên QIPEDC vẫn thấp: 12.2% (88/721); chéo nguồn 15.4% (4/26) [6.1, 33.5] (REPORT mục 3.3).
- Lối tắt nguồn còn: bộ phân loại nguồn trên đầu vào hài hòa 360 px vẫn đạt 94.8 (REPORT mục 3.6; ở 4a là 99.5).
- Thăm dò (b): top-1 của model gộp rơi vào lớp chỉ-VSL-GH ở 9.6% (69/722) clip QIPEDC nhưng 81.8% (973/1189) clip S06 — khớp giả thuyết model phân biệt nguồn (chỉ báo, không kiểm định).

## Giới hạn
- Ít mẫu mỗi lớp (hist ở REPORT mục 4); QIPEDC không có nhãn người ký nên không đo được người ký mới trên từ đơn lẻ.
- Một seed cho model từ điển và cho run 360 px; chênh balanced VAL giữa seed 42 và 43 của H-keepz (+1.61) gần bằng mức 360 px thắng (+1.72) (REPORT mục 3.2).
- CI rộng; Wilson giả định các clip độc lập.
- Phần "Ký câu = VSL-GH qua CSLR (Cấp 3)" của phương án A KHÔNG được đánh giá trong Bước 4.
- Bộ phân loại nguồn đo trên đầu vào hài hòa, không phải trên biểu diễn bên trong model.
- Đường live chưa dùng `harmonize()`; run được chọn dùng 360 px nên realtime (webcam 640×480) phải giảm về cùng mức và có test tương đương.

## Điều gì sẽ làm đổi khuyến nghị
- Bộ test webcam Bước 5: nếu model từ điển tốt hơn model gộp trên từ đơn lẻ quay thật thì cân nhắc A.
- Thêm dữ liệu từ đơn lẻ hoặc thêm seed mà đảo ngược kết quả chính.

## Không làm trong việc này; việc SAU khi người dùng duyệt
Không đổi model mặc định của backend. Nếu duyệt B: (1) nối `harmonize()` và 360 px vào đường live, kèm test tương đương train–realtime; (2) điểm dừng riêng trước khi đổi model mặc định; (3) đo trên bộ webcam Bước 5.
