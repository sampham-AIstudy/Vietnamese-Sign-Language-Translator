# Vietnamese Sign Language (VSL) Translator
## Hệ Thống Nhận Diện & Dịch Ngôn Ngữ Ký Hiệu Việt Nam End-to-End

Dự án triển khai giải pháp nhận diện Ngôn ngữ Ký hiệu Việt Nam (VSL) 2 cấp độ (Bảng chữ cái ngón tay tĩnh & Từ đơn chuyển động), kế thừa phương pháp luận từ **2 báo cáo nghiên cứu học thuật** và khai thác **2 tập dữ liệu thực tế** được cung cấp.

---

### 1. Cơ Sở Lý Thuyết Từ 2 Báo Cáo Nghiên Cứu

1. **Báo cáo 1 (Review VSLR 2026)**: *“A Comprehensive Review of Vietnamese Sign Language Recognition Techniques”* (HUST, Journal of Science and Technology, 2026).
   - Tổng quan toàn diện hơn 60 công trình VSL (2015–2025).
   - Nhấn mạnh tính khả thi và hiệu năng vượt trội của pipeline dựa trên **toạ độ khung xương (Landmark-based)** thay vì 3D-CNN RGB thô.
   - Định hướng sử dụng các mô hình học chuỗi thời gian (**BiGRU / LSTM / Transformer**) để xử lý chuỗi keypoints với chi phí tính toán thấp.
   - Phân tích tính đa dạng vùng miền của VSL qua 3 phương ngữ: **Bắc (B), Trung (T), Nam (N)**.

2. **Báo cáo 2 (VSL Alphabet 2025)**: *“Vietnamese Sign Language Alphabet Recognition Using Deep Learning and Mediapipe Methods”* (HUST, 2025).
   - Phương pháp trích xuất 21 điểm đặc trưng bàn tay qua **MediaPipe Hands**.
   - Thuật toán chuẩn hoá toạ độ: trừ toạ độ điểm gốc cổ tay (wrist = index 0) và chia cho khoảng cách cực đại để đạt tính bất biến theo tỷ lệ (scale-invariance).
   - Huấn luyện mạng nơ-ron sâu đạt độ chính xác >95% trên tập dữ liệu bảng chữ cái ký hiệu.

---

### 2. Hiện Trạng 2 Bộ Dữ Liệu Thực Tế Trong Dự Án

- **Dataset 1 (`data/`)**:
  - `data/asl_alphabet_train/` & `test/`: 87.000 ảnh cử chỉ bảng chữ cái (29 lớp: A-Z, del, nothing, space).
  - `data/hand_data.csv`: Toạ độ 42 chiều (21 keypoints x, y) tiền xử lý chuẩn MediaPipe cho bảng chữ cái.
- **Dataset 2 (`data (2)/`)**:
  - `Dataset/Videos/`: **4.362 video clip thực tế** của người khiếm thính Việt Nam thực hiện các từ ký hiệu VSL chuẩn (chia theo phương ngữ B, T, N).
  - `Dataset/Labels/label.csv`: 4.364 nhãn từ vựng tương ứng (gloss).
  - `Processed/`: **184.295 chuỗi keypoints `.npz`** đã tiền trích xuất sẵn theo chuẩn $(T=60, D=201)$ phân bổ thành 3 tập `train/` (145.019 clip), `val/` (17.980 clip), `test/` (21.296 clip) qua 3.315 lớp từ vựng.

---

### 3. Tối Ưu Cho Phần Cứng (Laptop RTX 3050 4GB VRAM)

- **Tránh RGB 3D-CNN**: Các mô hình 3D-CNN thô (I3D, SlowFast, Video Swin) cần 8GB+ VRAM và dễ gây lỗi Out-Of-Memory (OOM) trên RTX 3050 4GB.
- **Landmark Pipeline**: Chuỗi $(60, 201)$ nén hàng triệu pixel thành 12.060 số thực float32 (~48 KB/clip).
- **Tốc độ thực thi**:
  - Huấn luyện 40–100 từ vựng chỉ mất vài phút.
  - Tốc độ suy luận (Inference) đạt **>150 FPS** trên laptop, hoàn toàn hỗ trợ camera thời gian thực mà không trễ.

---

### 4. Cấu Trúc Thư Mục Dự Án

```
Project/
├── data/                               # Dữ liệu Bảng chữ cái ngón tay (Level 1)
│   ├── asl_alphabet_train/             # Ảnh gốc train bảng chữ cái
│   ├── asl_alphabet_test/              # Ảnh gốc test bảng chữ cái
│   └── hand_data.csv                   # 42 toạ độ đặc trưng chuẩn hoá
├── data (2)/                           # Dữ liệu Từ đơn VSL (Level 2)
│   ├── Dataset/
│   │   ├── Videos/                     # 4.362 video VSL gốc (.mp4)
│   │   └── Labels/label.csv            # Bảng ánh xạ video -> nhãn từ vựng
│   └── Processed/                      # 184.295 chuỗi (60, 201) keypoints
│       ├── label_map.json              # 3.315 từ vựng ánh xạ sang ID
│       ├── train/                      # 145.019 files .npz
│       ├── val/                        # 17.980 files .npz
│       └── test/                       # 21.296 files .npz
├── src/
│   ├── data/
│   │   ├── extract_landmarks.py        # MediaPipe Holistic (201-dim) & Hands (42-dim)
│   │   ├── dataset.py                  # PyTorch Dataset/DataLoader (Sequence & Alphabet)
│   │   └── augment.py                  # Tăng cường dữ liệu keypoint (jitter, rotate, time warp)
│   ├── models/
│   │   ├── alphabet_classifier.py      # MLP nhận diện bảng chữ cái (Paper 2)
│   │   ├── gru_classifier.py           # BiGRU + Temporal Attention (Paper 1)
│   │   ├── transformer_classifier.py   # Spatio-temporal Transformer Encoder
│   │   └── stgcn.py                    # Skeleton Graph Convolutional Network
│   ├── train_alphabet.py               # Huấn luyện model Level 1
│   ├── train_word.py                   # Huấn luyện model Level 2
│   ├── evaluate.py                     # Đánh giá Top-1, Top-5 & vẽ Confusion Matrix
│   └── export.py                       # Xuất mô hình ONNX & TorchScript
├── app/
│   ├── api/
│   │   └── main.py                     # FastAPI backend (REST endpoints)
│   └── ui/
│       └── app.py                      # Streamlit Web UI tương tác thời gian thực
├── configs/
│   ├── alphabet_config.yaml            # Cấu hình huấn luyện Level 1
│   └── word_config.yaml                # Cấu hình huấn luyện Level 2
├── experiments/                        # Lưu checkpoints (.pth), đồ thị và ONNX models
├── requirements.txt
└── README.md
```

---

### 5. Hướng Dẫn Cài Đặt & Chạy Hệ Thống

#### Bước 1: Kích hoạt Môi trường Ảo
Sử dụng trực tiếp Python trong virtualenv:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

#### Bước 2: Huấn luyện Mô hình Cấp độ 1 (Bảng chữ cái)
```powershell
.\.venv\Scripts\python.exe src/train_alphabet.py
```
*Kết quả:* Mô hình `AlphabetMLP` đạt độ chính xác >95%, lưu tại `experiments/alphabet_model.pth`.

#### Bước 3: Huấn luyện Mô hình Cấp độ 2 (Từ đơn VSL)
Huấn luyện mô hình BiGRU trên tập 40–50 từ vựng VSL phổ biến nhất:
```powershell
.\.venv\Scripts\python.exe src/train_word.py --model bigru --top_k 40 --epochs 25
```
*(Tùy chọn) Huấn luyện mô hình Transformer:*
```powershell
.\.venv\Scripts\python.exe src/train_word.py --model transformer --top_k 40 --epochs 25
```

#### Bước 4: Đánh giá & Phân tích Ma trận Nhầm lẫn
```powershell
.\.venv\Scripts\python.exe src/evaluate.py --checkpoint experiments/word_model_bigru.pth
```
Đồ thị ma trận nhầm lẫn sẽ được xuất ra `experiments/confusion_matrix_word.png` kèm danh sách các cặp từ dễ nhầm lẫn nhất.

#### Bước 5: Xuất Mô hình Phục vụ Triển khai (ONNX / TorchScript)
```powershell
.\.venv\Scripts\python.exe src/export.py
```

#### Bước 6: Khởi chạy Hệ Thống Web Fullstack Hiện Đại (ReactJS + Node.js + FastAPI)
Hệ thống hỗ trợ truyền luồng video trực tiếp từ webcam qua WebSockets và đo lường độ trễ mili-giây (RTT, AI Infer, MediaPipe):
```powershell
.\start_fullstack.ps1
```
Hoặc khởi chạy độc lập từng tầng:
- **Python AI Engine (FastAPI & WebSockets)**:
  ```powershell
  .\.venv\Scripts\uvicorn.exe app.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Node.js Gateway & Dictionary API**:
  ```powershell
  node backend/server.js
  ```
- **ReactJS Modern Frontend**:
  ```powershell
  cd frontend; npm run dev
  ```
Mở trình duyệt: `http://localhost:3000` (React Web) hoặc `http://localhost:8000/docs` (Swagger API).

#### Bước 7: (Tùy chọn) Khởi chạy Giao diện Thử nghiệm Nhanh (Streamlit UI)
```powershell
.\.venv\Scripts\streamlit.exe run app/ui/app.py
```
Giao diện Streamlit mở tại: `http://localhost:8501`.
