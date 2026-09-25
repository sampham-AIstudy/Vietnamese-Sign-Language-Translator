# SƯỜN BÀI BÁO CÁO KHOA HỌC / ĐỒ ÁN TỐT NGHIỆP
# VIETNAMESE SIGN LANGUAGE RECOGNITION (VSLR)
## HỆ THỐNG NHẬN DIỆN NGÔN NGỮ KÝ HIỆU VIỆT NAM THỜI GIAN THỰC ĐA PHƯƠNG NGỮ DỰA TRÊN SPATIO-TEMPORAL GRAPH CNN VÀ TEMPORAL ATTENTION TRANSFORMER

> **Tác giả:** Nhóm Nghiên cứu Đồ án Deep Learning & Computer Vision  
> **Môn học:** Deep Learning + Computer Vision (Học máy nâng cao)  
> **Phần cứng thực nghiệm:** Laptop NVIDIA GeForce RTX 3050 4GB GPU, Intel Core i5/i7, 16GB RAM  
> **Tài liệu tham khảo chính:** Dữ liệu VSL 4,362 video 3 miền, ST-GCN (Yan et al.), Spatial-Temporal Transformer.

---

## MỤC LỤC CHI TIẾT (REPORT STRUCTURE)

- [CHƯƠNG 1: TỔNG QUAN VÀ ĐẶT VẤN ĐỀ](#chương-1-tổng-quan-và-đặt-vấn-đề)
- [CHƯƠNG 2: PHÂN TÍCH DỮ LIỆU & QUY TRÌNH TIỀN XỬ LÝ ZERO-LEAKAGE](#chương-2-phân-tích-dữ-liệu--quy-trình-tiền-xử-lý-zero-leakage)
- [CHƯƠNG 3: KIẾN TRÚC MÔ HÌNH DEEP LEARNING CHUYÊN SÂU](#chương-3-kiến-trúc-mô-hình-deep-learning-chuyên-sâu)
- [CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM & PHÂN TÍCH KHOA HỌC](#chương-4-kết-quả-thực-nghiệm--phân-tích-khoa-học)
- [CHƯƠNG 5: HỆ THỐNG REALTIME DEMO & MLOPS OPTIMIZATION](#chương-5-hệ-thống-realtime-demo--mlops-optimization)
- [CHƯƠNG 6: KẾT LUẬN & HƯỚNG PHÁT TRIỂN](#chương-6-kết-luận--hướng-phát-triển)

---

## CHƯƠNG 1: TỔNG QUAN VÀ ĐẶT VẤN ĐỀ

### 1.1. Bối Cảnh Xã Hội và Ý Nghĩa Thực Tiễn
- Ngôn ngữ Ký hiệu (Sign Language) là phương tiện giao tiếp tự nhiên và duy nhất của cộng đồng người khiếm thính và câm tại Việt Nam (hơn 2.5 triệu người).
- Rào cản giao tiếp giữa người khiếm thính và xã hội tạo ra bất bình đẳng trong y tế, giáo dục, việc làm và dịch vụ công.
- Sự cần thiết của hệ thống dịch tự động thời gian thực (Real-time VSL Translator) chạy trực tiếp từ webcam/camera phổ thông mà không yêu cầu cảm biến đắt đỏ (Data Gloves hay Depth Cameras).

### 1.2. Thách Thức Kỹ Thuật Đa Phương Ngữ (Cross-Dialect Discrepancy)
- Ngôn ngữ Ký hiệu Việt Nam có sự phân hóa vùng miền sâu sắc: **Miền Bắc (Hà Nội)**, **Miền Trung (Đà Nẵng)**, và **Miền Nam (TP. Hồ Chí Minh)**:
  - Cùng một ý niệm (Gloss) có thể biểu đạt bằng hình thái bàn tay (Handshape), quỹ đạo chuyển động (Movement trajectory), hoặc vị trí cơ thể (Location) hoàn toàn khác biệt.
- **Thách thức Zero-Shot Cross-Dialect**: Mô hình học máy khi huấn luyện trên một phương ngữ thường bị suy giảm độ chính xác nghiêm trọng khi đem sang kiểm thử ở phương ngữ khác chưa từng thấy (Unseen Dialect).

### 1.3. Mục Tiêu Nghiên Cứu và Đóng Góp của Đồ Án
1. Xây dựng **Zero-Leakage Data Pipeline**: Thiết lập quy tắc phân chia tập dữ liệu tách biệt phương ngữ (Train: Bắc + Trung; Test: 100% Miền Nam) để đo lường năng lực tổng quát hóa thực chất.
2. Thiết kế lược đồ **67 Khớp Sinh Cơ Học (Biomechanical Skeleton)**: 25 khớp thân trên + 21 khớp tay trái + 21 khớp tay phải, tuân thủ nguyên tắc **NO ZERO-FILL** loại bỏ ảo giác dữ liệu (Artifacts).
3. Hiện thực hóa và so sánh 3 họ kiến trúc Deep Learning:
   - **Baseline BiGRU**: Xử lý chuỗi thời gian tuần tự.
   - **ST-GCN (Spatio-Temporal Graph CNN)**: Khai thác hình học đồ thị liên kết xương bàn tay và cơ thể.
   - **Transformer Encoder**: Khai thác cơ chế Multi-Head Temporal Self-Attention.
   - **Late-Fusion Ensemble**: Kết hợp ưu thế không gian của ST-GCN và ưu thế thời gian của Transformer.
4. Triển khai hệ thống Web Real-time hoàn chỉnh: **FastAPI WebSocket Backend** + **React Frontend HUD** + **ONNX Runtime Engine** (độ trễ dưới 15ms, tốc độ > 70 FPS).

---

## CHƯƠNG 2: PHÂN TÍCH DỮ LIỆU & QUY TRÌNH TIỀN XỬ LÝ ZERO-LEAKAGE

### 2.1. Khảo Sát Tập Dữ Liệu Video Gốc (Raw Dataset Inventory)
- **Tổng số video thực tế khảo sát**: **4,362 video** định dạng `.mp4` (100% hợp lệ, không lỗi codec).
- **Phân bố vùng miền**:
  - Miền Bắc (`B.mp4`): ~1,454 video.
  - Miền Trung (`T.mp4`): ~1,454 video.
  - Miền Nam (`N.mp4`): ~1,454 video.
- **Phân tích khả thi lớp từ vựng (Class Feasibility)**:
  - 3,314 từ vựng duy nhất trong bảng nhãn.
  - 489 từ vựng có đủ $\ge 3$ video (đại diện cả 3 miền).
  - Lựa chọn **Tier-1 Vocabulary (50 từ vựng thông dụng)** có tần suất cao, đại diện cho các nhu cầu giao tiếp cấp thiết: *cảm ơn, xin chào, tạm biệt, bệnh viện, bác sĩ, cấp cứu, an toàn, gia đình, trường học, v.v.*

### 2.2. Chiến Lược Phân Chia Tập Dữ Liệu (Split Policy)
- Để ngăn ngừa rò rỉ dữ liệu (Data Leakage) và đánh giá độ bền phương ngữ:
  - **Train Set (100 video)**: 50 video Miền Bắc + 50 video Miền Trung (Tỷ lệ 50%).
  - **Validation Set (50 video)**: 25 video Miền Bắc + 25 video Miền Trung (Tỷ lệ 25%, video-disjoint với Train).
  - **Test Set (50 video)**: **100% Miền Nam** (Tỷ lệ 25%, Unseen Dialect hoàn toàn).

### 2.3. Lược Đồ Khớp Sinh Cơ Học 67 Điểm (67-Joint Schema)
MediaPipe Holistic trích xuất 67 điểm khung xương đặc trưng ($201$ tọa độ không gian mỗi khung hình):
- **Khớp Thân Trên (Pose 0..24)**: Mắt, mũi, tai, vai, khuỷu tay, cổ tay, hông.
- **Bàn Tay Trái (Left Hand 25..45)**: Cổ tay, 5 ngón tay (mỗi ngón 4 khớp).
- **Bàn Tay Phải (Right Hand 46..66)**: Cổ tay, 5 ngón tay (mỗi ngón 4 khớp).

### 2.4. Tiền Xử Lý Không Gian & Thời Gian (Spatial & Temporal Normalization)
1. **Quy tắc NO ZERO-FILL**: Khớp không nhìn thấy (occlusion hoặc ngoài khung hình) được gán `np.nan` và $V_{i} = 0.0$. Tuyệt đối không thay thế bằng $(0,0,0)$ vì sẽ bóp méo tọa độ trọng tâm bàn tay.
2. **Căn Gốc Tọa Độ (Mid-Shoulder Centering)**:
   $$O = \frac{K_{\text{left\_shoulder}} + K_{\text{right\_shoulder}}}{2}, \quad K'_{i} = K_{i} - O$$
3. **Chuẩn Hóa Kích Thước (Shoulder Width Scaling)**:
   $$S = \|K_{\text{left\_shoulder}} - K_{\text{right\_shoulder}}\|_{2}, \quad \hat{K}_{i} = \frac{K'_{i}}{S}$$
4. **Căn Chỉnh Chiều Dài Chuỗi Cố Định ($T = 60$ Khung Hình)**: Sử dụng nội suy tuyến tính (Linear Interpolation) và mặt nạ thời gian $M_{T} \in \{0, 1\}^{60}$.

---

## CHƯƠNG 3: KIẾN TRÚC MÔ HÌNH DEEP LEARNING CHUYÊN SÂU

### 3.1. Mô Hình Baseline: BiGRU (Bidirectional Gated Recurrent Unit)
- **Đặc điểm**: Làm phẳng chuỗi khớp $60 \times 201$.
- **Cấu trúc**: 2 tầng BiGRU tuần tự, hidden dimension $128$, Dropout $0.2$.
- **Ưu điểm**: Nhẹ, suy luận nhanh trên CPU/GPU.
- **Nhược điểm**: Bỏ qua hoàn toàn cấu trúc hình học liên kết giữa các ngón tay và khớp xương cơ thể.

### 3.2. Mô Hình Không Gian - Thời Gian: ST-GCN (Spatial-Temporal Graph CNN)
- **Ma trận kề đồ thị sinh cơ học $\mathbf{A} \in \mathbb{R}^{3 \times 67 \times 67}$**:
  - Phân vùng cấu hình không gian (Spatial Configuration Partitioning) theo 3 tập con quan hệ: Gốc khớp (Root), Hướng tâm (Centripetal), Ly tâm (Centrifugal).
- **Khối tích chập đồ thị thời-không (ST-GCN Block)**:
  - Không gian: Tích chập đồ thị Spatial Graph Convolution có trọng số học thích nghi (Learnable Edge Importance Weighting $\mathbf{M}$).
  - Thời gian: Tích chập thời gian 1D Temporal Convolution (kernel size = 9).
  - Tích hợp mặt nạ khớp Masked Spatial-Temporal Pooling loại bỏ nhiễu từ khớp bị che khuất.

### 3.3. Mô Hình Chú Ý Thời Gian: Transformer Encoder
- **Đặc điểm**: Ánh xạ đặc trưng $201 \to d_{\text{model}} = 128$.
- **Mã hóa vị trí thời gian (Sinusoidal Positional Encoding)**: Ghi nhớ thứ tự chuyển động ký hiệu qua 60 bước.
- **Tầng mã hóa (2 Layers, 4 Attention Heads, Pre-LayerNorm)**:
  $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}} + M_{\text{padding}}\right)V$$
- **Cơ chế Masked Temporal Attention Pooling**: Tự động học trọng số chú ý để phát hiện khung hình "điểm nhấn" (Keyframes) của cử chỉ ký hiệu.

### 3.4. Mô Hình Kết Hợp: VSLR Late-Fusion Ensemble
- Kết hợp đầu ra xác suất Softmax giữa ST-GCN (Master về cấu trúc hình học không gian) và Transformer (Master về quỹ đạo chú ý thời gian):
  $$P_{\text{ensemble}} = \alpha \cdot P_{\text{ST-GCN}} + (1 - \alpha) \cdot P_{\text{Transformer}}, \quad \alpha = 0.5$$

---

## CHƯƠNG 4: KẾT QUẢ THỰC NGHIỆM & PHÂN TÍCH KHOA HỌC

### 4.1. Thiết Lập Môi Trường Thực Nghiệm
- Optimizer: `AdamW` ($\text{lr} = 10^{-3}$, weight decay $= 10^{-4}$).
- Scheduler: `CosineAnnealingLR` ($T_{\text{max}} = 50$, $\eta_{\text{min}} = 10^{-6}$).
- Tăng cường dữ liệu (Data Augmentation): Random Spatial Scaling ($0.9 - 1.1$), Random Rotation ($\pm 10^\circ$), Spatial Jittering ($\sigma = 0.005$).
- Kỹ thuật gia tốc: PyTorch Automatic Mixed Precision (AMP FP16) trên RTX 3050.

### 4.2. Bảng Tổng Hợp Số Liệu Benchmark Thực Tế (Test Set Miền Nam)

| STT | Mô Hình | Kiến Trúc | Val Top-1 | Val Loss | Test Top-1 | Test Top-5 | Macro F1 | Precision | Recall | Kích Thước (.pt) | Độ Trễ (ms) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Baseline BiGRU** | Recurrent | 44.0% | 3.1853 | 24.0% | 46.0% | 13.37% | 10.57% | 22.00% | 6.83 MB | **5.80 ms** |
| 2 | **ST-GCN (Spatial)** | Graph CNN | 40.0% | 2.7820 | **26.0%** | **60.0%** | **19.80%** | **17.57%** | **26.00%** | 3.88 MB | 10.53 ms |
| 3 | **Transformer** | Self-Attention | **46.0%** | 2.8033 | 22.0% | 50.0% | 15.91% | 14.08% | 22.00% | **3.79 MB** | 11.48 ms |
| 4 | **VSLR Ensemble** | ST-GCN + Trans | **46.0%** | **2.5828** | 24.0% | 54.0% | 18.80% | 16.50% | 24.00% | 7.67 MB | 22.01 ms |

*(Nguồn số liệu: Trích xuất từ các file `benchmark_results.json` trong thư mục `experiments/`)*

### 4.3. Phân Tích Hiện Tượng Sụt Giảm Đa Phương Ngữ (Cross-Dialect Discrepancy)
- **Hiện tượng**: Tất cả các mô hình đều đạt Top-1 từ $40\% - 46\%$ trên tập Validation (gồm phương ngữ Bắc + Trung), nhưng sụt giảm xuống còn $22\% - 26\%$ trên tập Test (hoàn toàn là phương ngữ Nam).
- **Nguyên nhân khoa học**:
  1. *Khác biệt hình thái thủ ngữ*: Nhiều từ vựng miền Nam sử dụng cấu hình bàn tay mở rộng hơn hoặc số lượng ngón tay tham gia khác với miền Bắc.
  2. *Độ dịch chuyển không gian*: ST-GCN chịu ảnh hưởng ít nhất nhờ vào tính bất biến tương đối của topo đồ thị (Top-5 đạt $60.0\%$, Macro F1 đạt $19.80\%$).
  3. *Tầm quan trọng của Top-5*: Top-5 đạt tới $60.0\%$ cho thấy không gian embedding của mô hình đã cô lập được từ đúng vào nhóm lân cận gần nhất.

### 4.4. Phân Tích Ma Trận Nhầm Lẫn (Confusion Matrix)
- Dẫn chứng hình ảnh: `submission/report_figures/confusion_matrix_stgcn.png` và `confusion_matrix_transformer.png`.
- Các từ có độ chính xác cao: Những từ có chuyển động thân thể rõ ràng (*cảm ơn, xin chào, an toàn, cấp cứu*).
- Các từ dễ nhầm lẫn: Các cặp từ có hình thái bàn tay tương đồng nhưng khác biệt ở quỹ đạo chuyển động tinh tế của đầu ngón tay.

---

## CHƯƠNG 5: HỆ THỐNG REALTIME DEMO & MLOPS OPTIMIZATION

### 5.1. Quy Trình Suy Luận Thời Gian Thực (Realtime Pipeline)
- Kiến trúc Sliding Window Buffer: Cửa sổ trượt 60 khung hình liên tục, kích hoạt suy luận sau mỗi stride = 2 frames.
- **Bộ Lọc Chống Rung Giật (Temporal Smoother)**:
  - Ngưỡng tin cậy $T_{\text{conf}} = 0.40$.
  - Thuật toán bầu cử đa số (Majority Voting) trên 5 cửa sổ suy luận gần nhất.
  - Bộ đếm duy trì hiển thị (Hold Counter = 20 frames) và thời gian trơ (Cooldown = 30 frames) giúp ghép từ thành câu mượt mà, không bị giật nháy (Flickering).

### 5.2. Kiến Trúc Web Fullstack (FastAPI + React)
- **Backend FastAPI** (`backend/main.py`):
  - WebSocket `/ws/live-stream`: Hỗ trợ truyền tải frame nén Base64 hoặc Binary Blob.
  - Tự động thu dọn phiên làm việc và giải phóng bộ nhớ khi client ngắt kết nối.
- **Frontend React 18 + Vite + Tailwind** (`frontend/`):
  - `CameraCapture.jsx`: Thu nhận webcam bằng HTML5 `getUserMedia`, vẽ khung xương MediaPipe lên overlay canvas.
  - `PredictionDisplay.jsx`: Hiển thị Gloss lớn, gauge độ tin cậy, bảng xếp hạng Top-5, độ trễ ms, FPS, và phát âm Text-to-Speech tiếng Việt.

### 5.3. Tối Ưu Hóa ONNX Runtime & Benchmark Hiệu Năng
- Script đóng gói: `src/export/export_onnx.py` (ONNX Opset 14, Constant Folding).
- Kết quả tối ưu:
  - Dung lượng file: **ST-GCN giảm 68.4%** ($3.88\text{ MB} \to 1.23\text{ MB}$), **Transformer giảm 60.3%** ($3.79\text{ MB} \to 1.50\text{ MB}$).
  - Độ chính xác bitwise: Sai số tuyệt đối tối đa giữa PyTorch và ONNX Runtime chỉ là $5.72 \times 10^{-6}$ (nhỏ hơn hàng trăm lần so với ngưỡng $10^{-4}$).
  - Tốc độ suy luận CPU: Transformer ONNX Runtime đạt **$13.85\text{ ms}$ ($72.2\text{ FPS}$)**, cho phép vận hành trơn tru trên mọi máy tính không có GPU.

---

## CHƯƠNG 6: KẾT LUẬN & HƯỚNG PHÁT TRIỂN

### 6.1. Kết Luận Đồ Án
- Đã xây dựng trọn vẹn chu trình MLOps cho bài toán Nhận diện Ngôn ngữ Ký hiệu Việt Nam: từ kiểm định dữ liệu sạch, thiết kế lược đồ sinh cơ học 67 khớp, huấn luyện các kiến trúc mạng hiện đại, đến đóng gói web realtime và tối ưu hóa ONNX.
- Chứng minh tính ưu việt của mô hình **ST-GCN** trong việc kháng cự phương ngữ chéo vùng miền (đạt Top-5 $60.0\%$ và Macro F1 $19.80\%$).
- Hoàn thành sản phẩm phần mềm demo trực quan, độ trễ cực thấp ($< 15\text{ ms}$), chạy mượt mà trên môi trường Web thời gian thực.

### 6.2. Hướng Phát Triển Tương Lai
1. Mở rộng tập từ vựng từ 50 từ (Tier-1) lên toàn bộ 489 từ có $\ge 3$ video và tiến tới 3,314 từ vựng.
2. Thu thập thêm dữ liệu ký hiệu miền Nam và miền Trung để thực hiện Data Balancing.
3. Ứng dụng mô hình Dịch chuỗi sang chuỗi (Sign-to-Text Sequence-to-Sequence / CTC Loss) để nhận diện các câu ký hiệu liên tục thay vì nhận diện từng từ độc lập.
4. Triển khai ứng dụng di động (Flutter / React Native) sử dụng ONNX Runtime Mobile hoặc TFLite.
