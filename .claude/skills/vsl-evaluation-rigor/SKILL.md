---
name: vsl-evaluation-rigor
description: Quy tắc đánh giá nghiêm ngặt cho các model VSL trong dự án này. Dùng skill này TRƯỚC KHI chạy bất kỳ đánh giá/benchmark nào, hoặc trước khi ghi kết luận số liệu vào EVALUATION.md.
---

# VSL Model Evaluation Rigor

## Các quy tắc rút ra từ chính dự án này (đọc kỹ trước khi lặp lại quy trình cũ)

1. **Video-disjoint không đủ, phải kiểm tra confound**: chia theo video không rò rỉ là điều kiện CẦN nhưng chưa ĐỦ — luôn kiểm tra xem cách chia có vô tình dồn hết 1 biến khác (miền, người quay, thiết bị quay...) vào riêng 1 tập hay không. Từng xảy ra: train/val/test bị chia đúng 3 miền riêng biệt (100% Bắc / 100% Trung / 100% Nam) dù "không rò rỉ video" — vẫn là confound nghiêm trọng khiến accuracy đo được bị đánh giá thấp hơn thực tế rất nhiều.
2. **Luôn đếm N trước khi tin số liệu**: nếu test set có N gần bằng số lớp (~1 mẫu/lớp), coi mọi so sánh %-accuracy giữa các cấu hình là chưa đủ tin cậy thống kê, trừ khi chênh lệch rất lớn hoặc đã cross-validate.
3. **Luôn nghi ngờ mode collapse trước khi kết luận "khó về bản chất bài toán"**: khi 1 model cho kết quả gần-ngẫu nhiên hoặc cực thấp, kiểm tra phân phối nhãn dự đoán trước khi kết luận đó là do bài toán khó/khác biệt miền/model kém — rất có thể là suy biến do early stopping/optimization. (Từng xảy ra: fold cross-dialect tưởng là "khác biệt ngôn ngữ học vùng miền" hóa ra là early-stopping phục hồi checkpoint epoch 1 chưa hội tụ, chỉ dự đoán vào 9/487 nhãn.)
4. **Benchmark latency qua đúng luồng thật, không chỉ test harness cô lập**: số đo qua script test riêng và qua đúng WebSocket/API thật có thể lệch nhau — luôn đo lại qua luồng thật trước khi chốt số liệu latency cuối cùng.
5. **So sánh ensemble với từng model đơn lẻ trước khi mặc định ensemble tốt hơn**: ensemble tốn thêm compute nhưng không tự động tốt hơn — luôn có bảng so sánh model đơn lẻ vs ensemble trước khi quyết định giữ/bỏ.
6. **Khi mở rộng số lớp/vocab, luôn so sánh cạnh kết quả tier trước đó** (không ghi đè) — để thấy rõ xu hướng accuracy giữ được/giảm theo quy mô, và để phát hiện lại confound nếu tái diễn ở quy mô mới.

## Trước khi ghi bất kỳ kết luận "khoa học" nào vào EVALUATION.md

Tự hỏi: kết luận này có kiểm chứng được bằng cách khác rẻ hơn để loại trừ nguyên nhân đơn giản hơn không (data quá ít, mode collapse, bug pipeline, confound trong split) trước khi quy về nguyên nhân phức tạp hơn (khác biệt ngôn ngữ học, giới hạn kiến trúc)? Ưu tiên giải thích đơn giản nhất được kiểm chứng bằng số liệu, không phải giải thích nghe hợp lý nhất.
