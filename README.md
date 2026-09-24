# Vietnamese Sign Language Recognition (VSLR)
## Hệ Thống Nhận Diện Ngôn Ngữ Ký Hiệu Việt Nam Thời Gian Thực Đa Phương Ngữ
### Đồ Án Môn Học: Deep Learning + Computer Vision (Học Máy Nâng Cao)

[![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0%2Bcu124-EE4C2C.svg?style=flat&logo=pytorch)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB.svg?style=flat&logo=react)](https://react.dev/)
[![ONNX](https://img.shields.io/badge/ONNX_Opset-14-005CED.svg?style=flat&logo=onnx)](https://onnx.ai/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)

---

## 1. Tóm Tắt Đồ Án (Abstract)

Nhận diện Ngôn ngữ Ký hiệu Việt Nam (**Vietnamese Sign Language Recognition - VSLR**) đóng vai trò quyết định trong việc xóa bỏ rào cản giao tiếp cho hơn 2.5 triệu người khiếm thính và câm tại Việt Nam. Thách thức lớn nhất trong thực tiễn là **Sự Phân Hóa Đa Phương Ngữ (Cross-Dialect Discrepancy)** giữa ba miền Bắc, Trung, Nam: cùng một ý niệm (Gloss) có thể có cấu hình bàn tay (Handshape), vị trí (Location) và quỹ đạo chuyển động (Movement) hoàn toàn khác biệt.

Đồ án này nghiên cứu và phát triển hệ thống VSLR hoàn chỉnh với các đóng góp cốt lõi:
1. **Zero-Leakage & No Zero-Fill Data Pipeline**: Phân chia tập dữ liệu tách biệt phương ngữ (Huấn luyện trên miền Bắc + Trung; Kiểm thử 100% trên miền Nam - *Unseen Dialect*) để đánh giá năng lực tổng quát hóa thực chất, loại bỏ triệt để rò rỉ dữ liệu.
2. **Lược đồ Khung xương Sinh cơ học 67 Khớp**: Kết hợp 25 khớp thân trên, 21 khớp bàn tay trái và 21 khớp bàn tay phải từ MediaPipe Holistic ($D = 201$ đặc trưng/frame), chuẩn hóa không gian theo chiều rộng vai.
3. **Mô hình Hóa Đồ thị Thời - Không & Cơ chế Chú ý**:
   - **ST-GCN (Spatial-Temporal Graph CNN)**: Khai thác hình học liên kết bàn tay qua ma trận kề $3 \times 67 \times 67$ phân vùng cấu hình không gian.
   - **Transformer Encoder**: Khai thác cơ chế Multi-Head Temporal Self-Attention và Masked Attention Pooling.
   - **Late-Fusion Ensemble**: Kết hợp dự đoán xác suất giữa ST-GCN và Transformer.
4. **Hệ thống Demo Real-time & MLOps Optimization**:
   - Web application hiện đại: Backend **FastAPI WebSocket** kết hợp Frontend **React 18 (Vite + Tailwind CSS)**.
   - Tối ưu hóa **ONNX Runtime (Opset 14)**: Nén dung lượng file hơn **68%**, sai số số học $\le 5.72 \times 10^{-6} \ll 10^{-4}$, đạt tốc độ **95 FPS** trên GPU và **72 FPS** trên CPU.

---

## 2. Bảng Kết Quả Thực Nghiệm (Test Set Miền Nam - Unseen Dialect)

Toàn bộ mô hình được đánh giá trên tập **Test Set (50 mẫu độc lập 100% miền Nam)**:

| Mô Hình | Kiến Trúc Cốt Lõi | Val Top-1 (%) | Test Top-1 (%) | Test Top-5 (%) | Macro F1 (%) | File Size (.pt) | File Size (.onnx) | Latency (ms) | Throughput (FPS) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline BiGRU** | Recurrent (2-layer BiGRU) | 44.0% | 24.0% | 46.0% | 13.37% | 6.83 MB | N/A | **5.80 ms** | 172.4 |
| **ST-GCN (Spatial Master)** | Spatial Graph CNN (67 joints) | 44.0% | **30.0%** | **52.0%** | **21.37%** | 3.88 MB | **1.23 MB** | 10.53 ms | 95.0 |
| **Transformer (Temporal Master)** | Multi-Head Self-Attention | 44.0% | 26.0% | 46.0% | 19.33% | 3.79 MB | 1.50 MB | 11.48 ms | 87.1 |
| **VSLR Ensemble** | Late-Fusion (ST-GCN + Trans) | 42.0% | 26.0% | 50.0% | 19.33% | 7.67 MB | 2.73 MB | 22.01 ms | 45.4 |

> **Nhận xét khoa học:** Sau khi tích hợp Data Augmentation (Jitter, Spatial Scale, 2D Rotation, Temporal Warp) và Label Smoothing (0.1), mô hình **ST-GCN** tăng độ chính xác Test Top-1 từ **26.0% lên 30.0%** và Macro F1 từ **19.80% lên 21.37%**; **Transformer** tăng Test Top-1 từ **22.0% lên 26.0%** và Macro F1 từ **15.91% lên 19.33%**.

---

## 2.1. Báo Cáo Kiểm Toán & Độ Tin Cậy Dữ Liệu (Audit Round 2 Update)

> [!CAUTION]
> **CẤP ĐỘ 1 (FINGERSPELLING) — CHƯA CÓ DỮ LIỆU THẬT, CHƯA CÓ MÔ HÌNH** (đính chính 24/09/2026):
> - **Loại bỏ ASL:** Đã xóa bỏ hoàn toàn bộ dữ liệu ASL 29 ký tự tiếng Mỹ và loại bỏ chỉ số PoC cũ (98.06% ASL) khỏi toàn bộ tài liệu chính thức.
> - **Đính chính:** Phiên bản trước ghi đây là "dữ liệu VSL thật của 15 người" — **SAI**. Thực tế bộ `data/vsl_alphabet_pilot` (1.875 clip, "15 signers") là **dữ liệu tổng hợp**: sinh bởi `scripts/record_vsl_alphabet.py` từ dáng tay viết cứng + nhiễu Gauss, không có người quay, không chạy MediaPipe; "signer" chỉ khác `hand_scale`. Không được dùng để train/đánh giá (có chốt chặn `DO_NOT_TRAIN_SYNTHETIC.md`). Chi tiết: `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.
> - **Pipeline (dùng lại khi có dữ liệu thật):** Đã kiểm thử module chuẩn hóa lòng bàn tay (`tests/test_alphabet_preprocessing.py` PASS), 2 kiến trúc baseline (Static MLP 63 dims và Temporal BiGRU 30 frames), script đóng gói cloud và notebook `vsl_alphabet_cloud_training.ipynb`.

> [!NOTE]
> **CẤP ĐỘ 2 (TỪ RỜI - 487 LỚP) & CẤP ĐỘ 3 (DỊCH CÂU) — THỐNG KÊ BOOTSTRAP 95% CI**:
> - **Cấp 2 (In-Domain 487 lớp):** Top-1 = **46.41% [42.09%, 50.72%]**, Top-5 = **75.77% [71.87%, 79.47%]**. Thử nghiệm Cross-Dialect 3-Fold: **UNVERIFIED** (cần chạy lại trên Cloud sau khi sửa lỗi early stopping).
> - **Cấp 3 (Dịch câu liên tục S06 - 30 câu unseen):**
>   - Mode A (Oracle Gloss $\to$ ViT5): BLEU = **27.98 [17.60, 38.39]**
>   - Mode B (CSLR $\to$ ViT5): BLEU = **23.18 [13.62, 33.70]**
>   - Khoảng chênh lệch: $\Delta = \mathbf{+4.80\ [1.29, 9.14]}$ ($p < 0.05$, có ý nghĩa thống kê thực chất).
>   - CSLR WER = **32.80% [29.48%, 36.62%]**.
> - **Mô phỏng Streaming CSLR:** Full-clip WER = **81.28%** (độ trễ 118.6ms) vs Streaming Chunk=60 frames WER = **158.78%** (TTFT 32.0ms, suy giảm +95.35% do BiGRU mất ngữ cảnh tương lai). Đã công bố tài liệu thiết kế tại [`docs/cslr_streaming_design.md`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/docs/cslr_streaming_design.md).

---

## 3. Kiến Trúc Kỹ Thuật (Architecture)

```
[Webcam / Video Clip]
          │
          ▼
[MediaPipe Holistic Realtime Extractor]  ───►  67 Joints (25 Pose + 21 LH + 21 RH = 201 dims)
          │                                     * Strict NO ZERO-FILL (NaN/Visibility Mask)
          ▼
[Spatial & Temporal Preprocessing]       ───►  Mid-Shoulder Centered, Shoulder-Width Scaled
          │                                     Temporal Buffer Deque (T = 60 frames)
          ▼
[Deep Neural Network Engines]
    ├── ST-GCN (Spatial Graph CNN)       ───►  Biomechanical Topology Adjacency A (3, 67, 67)
    ├── Transformer Encoder              ───►  Multi-Head Temporal Self-Attention
    └── VSLR Late-Fusion Ensemble        ───►  50:50 Softmax Probabilities Average
          │
          ▼
[TemporalSmoother (Anti-Flicker)]        ───►  Confidence Gating (0.40), Majority Voting, 20-frame Hold
          │
          ▼
[FastAPI WebSocket (:8000)]              ───►  JSON Stream: {gloss, confidence, top5, latency, fps, status}
          │
          ▼
[React 18 Frontend HUD (:3000)]          ───►  Live Video Preview, Skeleton Overlay, Speech Synthesis (TTS)
```

---

## 4. Cấu Trúc Thư Mục Dự Án (Repository Structure)

```
Project/
├── backend/                            # FastAPI Production Backend (Phase 12)
│   ├── main.py                         # FastAPI REST + WebSocket Server (:8000)
│   └── requirements.txt                # Python Backend dependencies
├── frontend/                           # React 18 + Vite + Tailwind Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── CameraCapture.jsx       # Component thu nhận webcam & canvas streaming
│   │   │   ├── PredictionDisplay.jsx   # Component hiển thị kết quả HUD, Top-5, FPS
│   │   │   └── Phase12Pipeline.jsx     # Điều phối WebSocket & ghép giao diện
│   │   ├── App.jsx                     # Ứng dụng chính & bộ chuyển tab
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js                  # Vite development server (:3000)
├── checkpoints/                        # Model weights (.pt) và ONNX models (.onnx)
│   ├── stgcn_best.pt                   # Best PyTorch ST-GCN weights
│   ├── stgcn_best.onnx                 # Optimized ONNX model (1.23 MB)
│   ├── transformer_best.pt             # Best PyTorch Transformer weights
│   └── transformer_best.onnx           # Optimized ONNX model (1.50 MB)
├── configs/                            # Configuration files & Class labels
│   ├── tier1_classes.txt               # 50 Tier-1 Vietnamese Sign Glosses
│   └── vsl_config.yaml                 # Hyperparameters configuration
├── data/Dataset/Videos/            # 4,362 raw VSL videos (North, Central, South)
├── docs/                               # Comprehensive Documentation
│   ├── audit/phase_state.json          # Trajectory audit tracker (Phases 0 -> 14)
│   ├── audit/final_status.md           # Endgame packaging validation checklist
│   ├── phase12_api.md                  # WebSocket & REST API documentation
│   ├── phase13_optimization.md         # ONNX vs PyTorch benchmark report
│   └── final_report_outline.md         # Sườn bài báo cáo khoa học Word/LaTeX
├── experiments/                        # Experiment metrics, plots, and logs
│   ├── baseline/                       # BiGRU training curve, confusion matrix, report
│   ├── stgcn/                          # ST-GCN training curve, confusion matrix, report
│   ├── transformer/                    # Transformer training curve, confusion matrix, report
│   └── ensemble/                       # Ensemble confusion matrix, benchmark JSON
├── scripts/                            # Verification & benchmark scripts
│   ├── smoke_test_phase10.py           # Phase 10 Realtime pipeline test
│   ├── smoke_test_phase12.py           # Phase 12 FastAPI WebSocket test
│   ├── benchmark_onnx.py               # Phase 13 ONNX benchmark script
│   └── generate_slide_images.py        # Phase 14 Slide snapshot generator
├── src/                                # Core Deep Learning Source Code
│   ├── data/                           # Data loaders, Landmark extractor, Preprocessing
│   ├── models/                         # ST-GCN, Transformer, BiGRU, Graph topology
│   ├── inference/                      # VSLPredictor, RealtimePipeline, TemporalSmoother
│   └── export/                         # ONNX export script and OnnxPredictor
├── submission/                         # Endgame Submission Artifacts
│   ├── report_figures/                 # All 7 confusion matrices & training curves
│   ├── slide_images/                   # Demo HUD slides for presentation
│   └── benchmark_tables.csv            # Summary benchmark spreadsheet
├── realtime_demo.py                    # Standalone Desktop Realtime Demo with Pillow HUD
├── train.py                            # Model training script with AMP & Early Stopping
└── evaluate_test.py                    # Independent Test Set evaluation script
```

---

## 5. Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### 5.1. Yêu Cầu Hệ Thống
- Hệ điều hành: Windows 10/11, Ubuntu 20.04/22.04.
- Python: 3.10 hoặc 3.11.
- Node.js: $\ge 18.0.0$, npm $\ge 9.0.0$.
- GPU (Khuyến nghị): NVIDIA GeForce RTX 3050 (hoặc tương đương) với CUDA 12.x.

### 5.2. Cài Đặt Môi Trường
1. **Thiết lập Virtualenv & Thư viện Python**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   ```
2. **Cài đặt Frontend React**:
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

---

### 5.3. Khởi Chạy Ứng Dụng Web Real-time (Khuyến Nghị)

#### Cách 1: Chạy song song 2 terminal
**Terminal 1 (FastAPI Backend)**:
```powershell
.\.venv\Scripts\uvicorn.exe backend.main:app --host 0.0.0.0 --port 8000 --reload
```
*API Docs Swagger UI mở tại: `http://localhost:8000/docs`*

**Terminal 2 (React Frontend)**:
```powershell
cd frontend
npm run dev
```
*Truy cập trình duyệt tại: `http://localhost:3000`. Cấp quyền Camera và trải nghiệm nhận diện thời gian thực.*

---

### 5.4. Chạy Bản Demo Desktop OpenCV (Tùy chọn)
Để chạy bản demo trực tiếp qua cửa sổ OpenCV với HUD tiếng Việt sắc nét:
```powershell
# Chạy với Webcam mặc định (Camera 0)
.\.venv\Scripts\python.exe realtime_demo.py --webcam 0

# Chạy kiểm thử trên file video mẫu
.\.venv\Scripts\python.exe realtime_demo.py --video "data\Dataset\Videos\W00009N.mp4"
```

---

### 5.5. Huấn Luyện & Đánh Giá Mô Hình
```powershell
# Huấn luyện mô hình ST-GCN với PyTorch AMP
.\.venv\Scripts\python.exe train.py --model stgcn --epochs 50 --batch-size 16

# Huấn luyện mô hình Transformer
.\.venv\Scripts\python.exe train.py --model transformer --epochs 50 --batch-size 16

# Đánh giá độc lập trên tập Test Set Miền Nam
.\.venv\Scripts\python.exe evaluate_test.py --model ensemble
```

---

### 5.6. Xuất & Benchmark Mô Hình ONNX
```powershell
# Xuất mô hình sang định dạng ONNX Opset 14
.\.venv\Scripts\python.exe src/export/export_onnx.py --model all

# Chạy kịch bản đo kiểm hiệu năng PyTorch vs ONNX Runtime
.\.venv\Scripts\python.exe scripts/benchmark_onnx.py
```

---

### 5.7. Chạy Kiểm Thử Tích Hợp (Smoke Tests)
```powershell
# Kiểm thử toàn bộ Phase 12 (REST API + WebSocket Stream)
.\.venv\Scripts\python.exe scripts/smoke_test_phase12.py
```

---

### 5.8. Huấn Luyện Tăng Tốc Trên Cloud GPU (Google Colab / Kaggle)
Để tận dụng GPU miễn phí (Tesla T4 / P100) trên Cloud và giữ máy cá nhân cho các tác vụ nhẹ (trích xuất MediaPipe, webcam demo, fullstack app):

1. **Đóng gói dữ liệu đã trích xuất tại máy cá nhân** (~187 MB, không chứa video thô):
```powershell
.\.venv\Scripts\python.exe scripts/package_cloud_data.py
```
2. **Mở notebook huấn luyện:**
   - Sử dụng file [`vsl_cloud_training.ipynb`](./vsl_cloud_training.ipynb) trên **Google Colab** (chọn T4 GPU) hoặc **Kaggle** (chọn GPU T4 x2 / P100).
   - Chi tiết hướng dẫn tải dữ liệu, chạy huấn luyện, xuất ONNX và tải checkpoint về máy: xem tài liệu [docs/cloud_training.md](./docs/cloud_training.md).

---

## 6. Trích Dẫn & Bản Quyền

Dự án được phát triển phục vụ mục đích nghiên cứu học thuật trong khuôn khổ môn học **Deep Learning + Computer Vision**. Mọi mã nguồn phát hành dưới giấy phép MIT License.

