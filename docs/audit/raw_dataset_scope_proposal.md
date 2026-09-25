# ĐỀ XUẤT PHẠM VI DATASET MỚI TỪ RAW VIDEOS
**Vietnamese Sign Language Recognition (VSLR)**  
**Status:** PROPOSAL AWAITING USER CONFIRMATION  
**Date:** 2026-09-12  
**Author:** Senior Computer Vision + Deep Learning Engineer  

---

## 1. Kết Quả Kiểm Kê Thực Tế Bộ Video Gốc (Empirical Inventory)

Từ kết quả chạy thực nghiệm tự động bằng OpenCV trên toàn bộ dữ liệu tại `data (2)/Dataset/Videos/`:
* **Tổng số video thực tế trên đĩa:** **4.362 video** (100% hợp lệ, có thể mở và đọc frame, 0 file hỏng, 0 file thiếu).
* **Tổng số từ vựng (glosses):** **3.314 từ vựng** (chuẩn hoá chữ thường, NFC).
* **Phân phối video trên mỗi gloss:**
  - Gloss có đúng 1 video: **2.763 glosses** (chiếm 83.4%).
  - Gloss có đúng 2 video: **62 glosses** (chiếm 1.9%).
  - Gloss có $\ge 3$ video: **489 glosses** (chiếm 14.8%).
  - Gloss có $\ge 4$ video: **6 glosses**.
  - Gloss có $\ge 5$ video: **1 gloss** (`thương yêu`: 6 videos).
  - Gloss có $\ge 10$ video: **0 gloss**.

### Nhận Định Khoa Học Cốt Lõi:
1. **Tuyệt đối KHÔNG THỂ train closed-set 3.314 classes**: 83.4% các từ vựng chỉ có duy nhất **1 video**. Nếu đưa 1 video vào Train thì Val và Test không có dữ liệu; nếu cắt video đó thành nhiều đoạn để chia cho cả 3 tập thì phạm vào **Data Leakage** nghiêm trọng (lỗi của bộ `Processed` cũ).
2. **Nguồn gốc thực sự của "472/489 classes"**: Có đúng **489 glosses** có đủ 3 video (đại diện cho bộ 3 phương ngữ: `B` - Bắc, `T` - Trung, `N` - Nam). Đây chính là tập từ vựng chuẩn hóa có đủ điều kiện để phân bổ: **1 video Train, 1 video Val, 1 video Test** hoàn toàn disjoint theo nguồn video.

---

## 2. Các Phương Án Lựa Chọn Phạm Vi (Scope Options)

### PHƯƠNG ÁN A (Khuyến nghị Nghiên cứu Học thuật Toàn diện) — 489 Glosses Triplet
* **Tiêu chí:** Chọn toàn bộ các gloss có $\ge 3$ video (đáp ứng bộ 3 phương ngữ Bắc - Trung - Nam).
* **Quy mô:** **489 classes** / **1.474 videos**.
* **Phân bổ Split (Strict Video-Disjoint):**
  - Train: 489 videos (ví dụ: Miền Bắc + augment sau split)
  - Val: 489 videos (ví dụ: Miền Trung, clean)
  - Test: 489 videos (ví dụ: Miền Nam, clean)
* **Ưu điểm:**
  - Quy mô lớn (~489 từ vựng, rất gần với con số 472 glosses kỳ vọng ban đầu).
  - Khảo sát được tính đa dạng phương ngữ (cross-dialect generalization).
  - Chuẩn mực khoa học cao, không bị rò rỉ dữ liệu.
* **Nhược điểm:**
  - Mỗi class chỉ có 1 sample thực tế trong train, đòi hỏi augmentation mạnh mẽ (post-split) hoặc pre-training để đạt độ chính xác cao.

---

### PHƯƠNG ÁN B (Khuyến nghị Tối ưu Kỹ thuật & Triển khai Realtime) — Top 50 hoặc Top 100 Glosses Phổ Biến
* **Tiêu chí:** Chọn top 50 hoặc top 100 từ vựng cốt lõi (chào hỏi, số đếm, gia đình, đại từ, giao tiếp thường ngày) từ nhóm 489 glosses có $\ge 3$ video.
* **Quy mô:** **50 classes** (150 videos) hoặc **100 classes** (300 videos).
* **Ưu điểm:**
  - Tốc độ huấn luyện rất nhanh trên GPU RTX 3050 4GB (vài phút mỗi epoch).
  - Độ chính xác (Accuracy / Macro F1) tập trung cao, ít bị phân tán xác suất.
  - Phù hợp hoàn hảo để xây dựng demo realtime webcam có độ tin cậy thực tế cao, tránh nhầm lẫn giữa hàng nghìn từ vựng.
  - Dễ dàng so sánh ablation study (BiGRU vs. ST-GCN vs. Transformer).
* **Nhược điểm:**
  - Phạm vi từ vựng hẹp hơn Phương án A.

---

### PHƯƠNG ÁN C — Hệ Thống Mở: Metric Learning / Retrieval / Few-Shot
* **Tiêu chí:** Sử dụng mạng trích xuất đặc trưng (Metric Learning / Triplet Loss / ArcFace) để sinh vector embedding không gian ký hiệu.
* **Quy mô:** Sử dụng toàn bộ 4.362 video của 3.314 classes để học không gian đặc trưng; phân loại từ vựng dựa trên Nearest Neighbor / Cosine Prototype Search.
* **Ưu điểm:**
  - Hỗ trợ cả các từ vựng chỉ có 1 video (1-shot learning).
  - Có khả năng mở rộng thêm từ mới mà không cần re-train toàn bộ mạng.
* **Nhược điểm:**
  - Kiến trúc và pipeline huấn luyện phức tạp hơn nhiều so với Cross-Entropy closed-set tiêu chuẩn của đồ án CV/DL.
  - Cần thời gian tinh chỉnh margin và hard-mining.

---

### PHƯƠNG ÁN D — Thu Thập Thêm Dữ Liệu
* **Mô tả:** Quay thêm video cho các từ vựng còn thiếu để đạt tối thiểu 10–20 video/class.
* **Đánh giá:** Không khả thi trong giới hạn thời gian đồ án học kỳ hiện tại.

---

## 3. Khuyến Nghị Cuối Cùng Của Kỹ Sư (Recommendation)

Để đảm bảo tính khả thi trên GPU RTX 3050 4GB, độ trung thực học thuật và khả năng demo ấn tượng:

> **LỘ TRÌNH ĐỀ XUẤT 2 TẦNG (TWO-TIER BENCHMARK):**
> 1. **Core Benchmark (50 Classes)**: Đóng băng tập 50 từ vựng giao tiếp cốt lõi (từ tập 489 glosses có đủ B-T-N). Dùng tập này để chạy toàn bộ các thử nghiệm mô hình ở Phase 5 (Baseline BiGRU), Phase 6 (ST-GCN), Phase 7 (Transformer), đo độ trễ và tối ưu realtime camera.
> 2. **Extended Benchmark (489 Classes)**: Mở rộng đánh giá trên toàn bộ 489 classes có đủ 3 miền để báo cáo năng lực nhận diện quy mô lớn trong bài báo cáo tổng kết (Phase 9 & 14).

*Chờ người dùng xác nhận lựa chọn trước khi tiến hành tạo file split.*
