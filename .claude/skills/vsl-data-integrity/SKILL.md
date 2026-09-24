---
name: vsl-data-integrity
description: BẮT BUỘC chạy Bước 0 (truy script tạo dữ liệu, phát hiện dữ liệu tổng hợp/nhãn bị gán) trước mọi lần train, đánh giá, hoặc chấm PASS audit dữ liệu. Kiểm tra nguồn gốc/tính phù hợp của bất kỳ bộ dữ liệu nào trước khi dùng để train/đánh giá cho dự án Vietnamese Sign Language Translator. Dùng skill này TRƯỚC KHI tích hợp, huấn luyện, hoặc báo cáo kết quả từ bất kỳ bộ dữ liệu nào (mới thêm hoặc đã có sẵn trong repo).
---

# VSL Data Integrity & Provenance Check

## Bài học nền tảng (từ chính dự án này)

Bộ dữ liệu `asl_alphabet_train/test` từng được dùng để huấn luyện bộ nhận diện "VSL Fingerspelling" — nhưng đó thực chất là bảng chữ cái Mỹ (ASL), không phải VSL. Model đạt 98.06% accuracy nhưng con số đó không có ý nghĩa gì cho bài toán VSL thật vì train/test đều trên đúng 1 ngôn ngữ sai. Bài học: **một bộ dữ liệu "trông có vẻ đúng dạng bài toán" (vd: cùng là "ảnh bảng chữ cái ký hiệu") không có nghĩa là đúng NGÔN NGỮ/MIỀN của bài toán.**

**Bài học thứ hai (24/09/2026):** `data/vsl_alphabet_pilot` (1.875 clip, "15 signers", "chuẩn Thông tư 17") được audit vòng 1 (B1) và vòng 2 (V5) chấm **PASS** vì đếm đúng file, đúng shape, 0 NaN, 0 hash trùng. Thực tế toàn bộ được **sinh bởi `scripts/record_vsl_alphabet.py`**: dáng tay viết cứng + nhiễu Gauss, không có camera, không chạy MediaPipe, "signer" chỉ là một hệ số `hand_scale`. Bài học: **đếm file, kiểm shape, kiểm NaN/hash KHÔNG chứng minh được nguồn gốc.** Script tên "record"/"collect"/"extract" cũng có thể đang sinh dữ liệu.

## BƯỚC 0 — KIỂM TRA NGUỒN GỐC (BẮT BUỘC, không được bỏ qua)

Phải hoàn thành bước này **trước mọi lần train, mọi lần đánh giá, và trước khi chấm PASS bất kỳ mục audit dữ liệu nào**. Một mục audit dữ liệu chỉ được PASS khi có bằng chứng nguồn gốc (0a–0d) ghi kèm; nếu thiếu, trạng thái tối đa là **UNVERIFIED**.

- **0a. Truy script tạo ra dữ liệu:** tìm mọi script ghi vào thư mục đó (`grep -rn "<tên thư mục>" --include=*.py`), rồi **đọc hàm ghi file** (`np.savez`, `cv2.VideoWriter`, `to_csv`, `json.dump`...). Hỏi: dữ liệu ghi ra đến từ camera/tải về/MediaPipe, hay từ hằng số, `np.random`, template, luật sinh (`generate`, `synth`, `simulate`, `canonical`, `template`, `augment`, `rng`)?
- **0b. Kiểm tra nguồn ngoài:** dữ liệu tải về phải có URL/paper/license ghi trong `docs/data_registry.md` hoặc `docs/provenance/`. Không có → UNVERIFIED.
- **0c. Soi nội dung thật:** mở 3–5 video/ảnh ngẫu nhiên (trích 1 frame xem) — có người thật không, hay hình vẽ/render? Với landmark: so thống kê giữa các lớp/signer; phương sai gần như bằng nhau tuyệt đối giữa người khác nhau là dấu hiệu sinh tổng hợp.
- **0d. Metadata signer/phương ngữ/nhãn lấy từ đâu:** trường `signer_id`, `dialect`, `region`, nhãn — được ghi lúc quay, lấy từ nguồn gốc, hay được **gán** bằng code (vòng lặp, hash, chia theo thứ tự)? Gán bằng code → mọi kết quả "theo signer/phương ngữ" phải đánh dấu UNVERIFIED.
- Nếu phát hiện dữ liệu tổng hợp: đặt file `DO_NOT_TRAIN_SYNTHETIC.md` trong thư mục đó (pipeline sẽ từ chối), ghi báo cáo, **dừng và báo người dùng**.

## Checklist bắt buộc trước khi dùng bất kỳ bộ dữ liệu nào

1. **Nguồn gốc**: bộ dữ liệu này đến từ đâu? Có tài liệu/paper/link xác nhận nó thực sự là dữ liệu Việt Nam / VSL không, hay chỉ là bộ dữ liệu ký hiệu chung chung (rất có thể là ASL, vì đó là bộ phổ biến nhất trên Kaggle/HuggingFace cho các bài toán "sign language")?
2. **Nhãn**: tên các lớp/nhãn có phải ký tự/từ vựng tiếng Việt thật không, hay là ký tự tiếng Anh/ngôn ngữ khác được gắn nhãn lại?
3. **Đối chiếu mẫu**: lấy ngẫu nhiên 3-5 mẫu, đối chiếu bằng tài liệu tham khảo (paper gốc, từ điển VSL chính thức như QIPEDC) xem cử chỉ có khớp với VSL thật không.
4. **Nếu không chắc chắn 100%**: DỪNG lại, báo cáo rõ ràng cho người dùng, không tự ý huấn luyện và báo cáo accuracy như thể đó là kết quả VSL thật.
5. **Đếm trước khi thiết kế split**: trước khi quyết định chiến lược split/sample cho bất kỳ tập dữ liệu nào, luôn đếm chính xác số mẫu theo (class, dialect/domain liên quan) trước — đừng giả định phân bố đều. (Bài học từ việc phát hiện tier1 chỉ có ~1 video/lớp/miền — nếu không đếm trước, dễ thiết kế split sai mà không biết.)

## Khi báo cáo kết quả

Luôn ghi bằng chứng của Bước 0 (script tạo dữ liệu + dòng code, nguồn ngoài, mẫu đã soi) bên cạnh mọi trạng thái PASS. Luôn ghi rõ nguồn gốc + phạm vi (ngôn ngữ, miền, số mẫu) của bộ dữ liệu đã dùng ngay trong phần đầu báo cáo/EVALUATION.md — không chỉ ghi accuracy suông.
