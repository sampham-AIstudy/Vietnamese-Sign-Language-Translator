# BÁO CÁO KIỂM ĐỊNH TOÀN DIỆN HỆ THỐNG VÀ DỮ LIỆU (ML & QA AUDIT REPORT)
**Dự án:** Vietnamese-Sign-Language-Translator  
**Thời điểm kiểm định:** 24/09/2026  
**Chế độ thực thi:** READ-ONLY AUDIT (Không ghi đè code, không can thiệp checkpoint/dữ liệu gốc)  
> [!CAUTION]
> **ĐÍNH CHÍNH 24/09/2026:** Mục **B1** chấm PASS chỉ dựa trên đếm file/shape, không kiểm tra nguồn gốc. Thực tế bộ `data/vsl_alphabet_pilot` (1.875 clip, "15 signers") là **dữ liệu tổng hợp**: sinh bởi `scripts/record_vsl_alphabet.py` từ dáng tay viết cứng + nhiễu Gauss, không có người quay, không chạy MediaPipe; "signer" chỉ khác `hand_scale`. B1 đổi thành **FAIL**; mọi đề xuất "chỉ cần train trên 1.875 clip" trong báo cáo này không còn giá trị. Chi tiết: `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.

**Quy chuẩn áp dụng:** [vsl-data-integrity](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/.agents/skills/vsl-data-integrity/SKILL.md) & [vsl-evaluation-rigor](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/.agents/skills/vsl-evaluation-rigor/SKILL.md)

---

## 1. TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

1. **Trạng thái luồng thực thi:** Luồng Cấp 2 (Từ rời 487 lớp qua ST-GCN + Motion Gating) và REST Dịch thuật (ViT5) hoạt động ổn định trên Backend (`latency` p95 = 12.81ms < 150ms).
2. **Khoảng trống Cấp 1 (Fingerspelling):** ~~Dữ liệu VSL chuẩn (1.875 clip pilot, 15 signers) đã thu thập và trích xuất landmarks xong~~ *(đính chính: dữ liệu tổng hợp, xem B1)* — **CHƯA CÓ DỮ LIỆU THẬT, CHƯA CÓ MODEL**. Backend chưa có endpoint; Frontend hiện đang dùng hàm giả lập `Math.random()`.
3. **Khoảng trống Cấp 3 (CSLR):** Mô hình CSLR ST-GCN+BiGRU và ViT5 hoạt động chính xác ở chế độ offline/batch, nhưng **CHƯA ĐƯỢC NỐI VÀO WEBSOCKET REALTIME** (luồng live-stream hiện chỉ chạy Cấp 2).
4. **Tính toàn vẹn dữ liệu Cấp 2:** Checkpoint `stgcn_tier2_indomain.pt` (487 lớp) tái lập chính xác 100% số liệu (Top-1: 46.41%, Top-5: 60.78%). Tuy nhiên, file `configs/vsl_config.yaml` và `data/splits/tier2_*.csv` gốc bị **lệch dồn miền** (Train 100% Bắc, Val 100% Trung, Test 100% Nam) và ghi 489 lớp; trong khi mô hình thực tế đã được train trên `data/splits/folds/tier2_indomain_*.csv` (487 lớp).
5. **Độ phủ dữ liệu Cấp 2:** 2.740 từ vựng trong kho chỉ có đúng $N=1$ video clip, chỉ phù hợp làm Ngân hàng Truy vấn (One-Shot Retrieval / Lexicon Bank), không thể train mạng phân loại đóng.
6. **Thổi phồng chỉ số Cấp 3:** BLEU 58.09 của ViT5 trên full test set S06 bị **thổi phồng do 90% câu đã xuất hiện trong tập Train**; trên 30 câu thực sự chưa từng thấy (unseen sentences), BLEU thực tế là **27.87**.
7. **Kết luận chung:** Hệ thống **CHƯA ĐỦ ĐỂ CHẠY TOÀN DIỆN NHƯ MÔ TẢ**, nhưng nền tảng thuật toán lõi (Core Engine) Cấp 2, CSLR và ViT5 đều có checkpoint thật, độ trễ đạt chuẩn thời gian thực.

---

## 2. BẢNG KẾT QUẢ KIỂM ĐỊNH CHI TIẾT (PHẦN A – E)

| Mã | Hạng mục kiểm tra | Kết quả | Bằng chứng kiểm định thực tế (Evidence) |
| :--- | :--- | :---: | :--- |
| **A1** | Cấu trúc thư mục & Entry Points | **PASS** | `backend/main.py`, `frontend/vite.config.js`, `realtime_demo.py`, `run_core.py` tồn tại, cấu trúc phân lớp rõ ràng. |
| **A2** | Nạp Checkpoint mặc định & Config | **PASS** | `backend/main.py` nạp `checkpoints/stgcn_tier2_indomain.pt` (487 lớp), hỗ trợ biến môi trường `VSL_MODEL_TYPE`, `VSL_STGCN_CKPT`. |
| **A3** | Tích hợp luồng Cấp 1 (Chữ cái) | **FAIL** | Frontend [`Fingerspelling.jsx`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/frontend/src/components/Fingerspelling.jsx#L32-L43) dùng `Math.random()`; Backend không có endpoint Cấp 1; Checkpoint không tồn tại. |
| **A4** | Tích hợp luồng Cấp 2 (Từ rời) | **PASS** | Nối hoàn chỉnh: Camera $\to$ MediaPipe $\to$ Preprocessor $\to$ ST-GCN Tier 2 $\to$ Smoother + Motion Gating $\to$ HUD/WebSocket. |
| **A5** | Tích hợp luồng Cấp 3 vào Realtime | **FAIL** | WebSocket `/ws/live-stream` **chỉ chạy Cấp 2**. CSLR Cấp 3 chỉ chạy offline/batch qua `VSLEndToEndTranslator` hoặc script. |
| **A6** | Tích hợp Dịch thuật Gloss $\to$ Text | **PASS** | ViT5 được nạp qua REST `POST /api/translate` và tự động kích hoạt trong `realtime_demo.py` khi chốt từ. |
| **B1** | Dữ liệu Cấp 1 (VSL vs ASL) | **FAIL** *(đính chính 24/09)* | Dữ liệu ASL cũ đã bị xóa sạch (0 file). Nhưng `data/vsl_alphabet_pilot/` (1.875 clip, "15 signers") **không phải dữ liệu quay thật**: sinh bởi `scripts/record_vsl_alphabet.py` từ dáng tay viết cứng + nhiễu, MediaPipe không chạy, video là hình que. Lần chấm PASS trước chỉ đếm file/shape, không kiểm tra nguồn gốc. Xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`. |
| **B2** | Dữ liệu Cấp 2 (Từ rời) | **PASS** | 4.362 video `.mp4` trong `data/Dataset/Videos/`, khớp 1-1 với `label.csv`, 0 file hỏng; 435 video HCMUE tại `data/raw_tudienngonngukyhieu/videos/`. |
| **B3** | Kiểm kê lớp ít mẫu Cấp 2 | **PASS** | 2.826 / 3.315 lớp có $< 3$ mẫu (2.740 lớp có đúng 1 mẫu). Số mẫu trung bình: 1.32 mẫu/lớp. 487 lớp có $\ge 3$ mẫu đủ 3 miền được train vào Tier 2. |
| **B4** | Dữ liệu Cấp 3 (CSLR & Parallel) | **PASS** | CSLR: 4.200 file keypoints `.npy` (VSL-GH, 300 câu y tế thật, 6 signers). Parallel text: 10K là **dữ liệu tổng hợp (PCFG rule-based)** (9.405 câu thô, 7.140 câu đã làm sạch). |
| **C1** | Rò rỉ video Cấp 2 (Leakage) | **PASS** | `tier2_train.csv`, `val.csv`, `test.csv` có 0 video trùng lặp (100% video-disjoint). |
| **C2** | Phân bổ Signer & Câu Cấp 3 | **PASS** | CSLR S06 là held-out signer thật sự (train: S01-S04, val: S05, test: S06). Tuy nhiên, 300 câu lặp lại 100% giữa train/val/test (chỉ held-out signer, không held-out sentence). |
| **C3** | Nhiễu phương ngữ (Dialect Confound) | **FAIL** | File gốc `data/splits/tier2_train.csv` (488 Bắc), `val.csv` (488 Trung), `test.csv` (488 Nam) bị **lệch dồn 100% theo vùng miền**. Tuy nhiên mô hình đã train trên `data/splits/folds/tier2_indomain_*.csv` cân bằng 1:1:1. |
| **C4** | Nhất quán nhãn (Label Integrity) | **PASS** | 0 video mồ côi (100% khớp video trên đĩa và nhãn), 0 dòng trùng lặp, 3.314 nhãn chuẩn hóa không lỗi khoảng trắng/dấu câu. |
| **C5** | Sức khỏe Keypoint (NaN/Zeros) | **PASS** | Keypoints Cấp 2 lưu dưới dạng strict NaN (không zero-fill bừa bãi); độ dài chuỗi phân bố hợp lý: min=79, median=117, max=255 frames. |
| **C6** | Nhất quán Không gian đặc trưng | **PASS** | ST-GCN nhận 67 joints; Realtime extractor xuất đúng `(67, 3)`; VSL-GH chuyển đổi thành công từ 411 dims sang `(T, 67, 3)`. |
| **C7** | Ngữ liệu dịch thuật (No-op & Lệch miền) | **PASS** | Tập `vie_vsl_10k_cleaned.jsonl` có 0% no-op (đã lọc sạch 2.204 câu trùng lặp). Phát hiện lệch miền: 6.76% từ vựng VSL-GH hoàn toàn vắng mặt trong 10K. |
| **D1** | Smoke Test: Video $\to$ Keypoint | **PASS** | `CleanHolisticExtractor` trích xuất video `0001B.mp4` $\to$ shape `(130, 67, 3)`, `0001N.mp4` $\to$ `(133, 67, 3)`. |
| **D2** | Smoke Test: Keypoint $\to$ Cấp 2 Predictor | **PASS** | Keypoint qua `VSLPreprocessingPipeline` $\to$ `VSLPredictor`: ra nhãn hợp lệ (`địa chỉ`, conf: 0.515), độ trễ 6.5ms – 20.7ms. |
| **D3** | Smoke Test: Keypoint câu $\to$ CSLR | **PASS** | VSL-GH chuyển sang 67 joints $\to$ `CSLRRecognizer`: xuất chuỗi gloss (độ trễ 48.7ms). |
| **D4** | Smoke Test: Gloss $\to$ ViT5 Translation | **PASS** | `VSLTranslator`: Oracle `TÔI ĐĂNG-KÝ KHÁM SỨC-KHỎE MUỐN` $\to$ *"Tôi muốn đăng ký khám sức khỏe."* (1.150ms lần đầu, ~480ms sau warmup). |
| **D5** | Smoke Test: Backend REST & WebSocket | **PASS** | TestClient: `/health` (200 OK), `/api/classes` (487 lớp), `/api/dictionary` (4.797 mục), `/api/translate` (200 OK), `/ws/live-stream` (Handshake + nhận `frame_result` thành công). |
| **D6** | Frontend $\leftrightarrow$ Backend Proxy | **PASS** | `frontend/vite.config.js` proxy `/api` và `/ws` chính xác về port 8000; CORS middleware cho phép `*`. |
| **D7** | Đo độ trễ E2E & Benchmark (< 150ms) | **PASS** | Benchmark ST-GCN (50 runs): Mean = 8.76ms, p50 = 8.15ms, p95 = 12.81ms $\ll 150\text{ms}$ mục tiêu. |
| **E1** | Tái lập chỉ số Cấp 2 (Held-out Test) | **PASS** | Chạy lại trên 487 mẫu `tier2_indomain_test.csv`: **Top-1 = 46.41%**, **Top-5 = 60.78%** (Khớp chính xác 100% với số liệu đã công bố). |
| **E2** | Rà soát phân bổ phương ngữ Cấp 2 | **PASS** | Miền Trung đạt 61.73%, Miền Nam đạt 56.17%, Miền Bắc chỉ đạt 21.47% (do tập train indomain chứa nhiều dữ liệu Trung/Nam hơn). |
| **E3** | Đánh giá thổi phồng BLEU Cấp 3 | **PASS** | Xác nhận hiện tượng thổi phồng: BLEU 58.09 đo trên tập S06 bị ghi nhớ câu (seen sentences); BLEU đo trên 30 câu chưa từng xuất hiện (unseen sentences) là **27.87**. |
| **E4** | Xác thực Checkpoint thực tế | **PASS** | Toàn bộ checkpoint đang nạp (`stgcn_tier2_indomain.pt`, `cslr_best.pt`, `vit5_stage2`) là bản hội tụ hoàn chỉnh, không phải dummy hay epoch đầu. |

---

## 3. DANH SÁCH LỖI VÀ RỦI RO KỸ THUẬT (SEVERITY-RANKED RISKS)

### 🔴 Mức độ CRITICAL (Nghiêm trọng nhất - Cần xử lý trước khi demo người dùng)

#### Lỗi 1: Giao diện Cấp 1 (Fingerspelling) dùng mã giả lập ngẫu nhiên (`Math.random()`)
- **Mô tả:** Trong component frontend [`frontend/src/components/Fingerspelling.jsx`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/frontend/src/components/Fingerspelling.jsx#L33-L42), hàm nhận diện ảnh bảng chữ cái `predictStaticImage` không hề gọi API backend mà tự sinh ngẫu nhiên một ký tự từ mảng `sampleLetters` kèm confidence giả từ 0.92 đến 0.99. Backend cũng chưa có endpoint `/api/fingerspelling`.
- **Bằng chứng:**
  ```javascript
  const randomChar = sampleLetters[Math.floor(Math.random() * sampleLetters.length)];
  const conf = (0.92 + Math.random() * 0.07).toFixed(3);
  setPrediction(randomChar);
  ```
- **Hậu quả:** Người dùng tưởng hệ thống nhận diện được bảng chữ cái, nhưng thực chất là quay số ngẫu nhiên; đồng thời giải thích vì sao khi giơ chữ "C" trên camera realtime (đang chạy ST-GCN Cấp 2) lại bị ép sang từ "hành quân".
- **Cách sửa đề xuất (Không tự sửa):** Huấn luyện một mạng MLP/Lightweight CNN đơn giản trên ~~1.875 clip `.npz` đã có sẵn tại `data/vsl_alphabet_pilot/landmarks/`~~ dữ liệu quay thật (bộ pilot là tổng hợp — xem B1), tạo endpoint `POST /api/fingerspelling` trên FastAPI và kết nối giao diện vào API này.

---

### 🟠 Mức độ HIGH (Ảnh hưởng kiến trúc & Cấu hình)

#### Lỗi 2: CSLR Cấp 3 chưa được nối vào luồng Streaming Realtime
- **Mô tả:** WebSocket endpoint `/ws/live-stream` tại [`backend/main.py`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/backend/main.py#L394-L440) chỉ gọi `RealtimePipeline` (chạy ST-GCN từ rời trên cửa sổ trượt 60 frame). Mô hình CSLR (`cslr_best.pt`) chỉ được tích hợp dạng hàm offline trong `VSLEndToEndTranslator.translate_keypoints()`.
- **Bằng chứng:** Hàm worker `_process_frame_worker()` trong `backend/main.py` chỉ cập nhật buffer cho `VSLPredictor`, không có cơ chế CTC sliding decoding của CSLR.
- **Cách sửa đề xuất:** Thiết kế luồng Streaming CSLR 2 chế độ (Mode Toggle): Chế độ 1 (Từ rời: ST-GCN + Smoother), Chế độ 2 (Câu liên tục: CSLR CTC streaming buffer theo chunk 60-120 frame).

#### Lỗi 3: Lệch file phân chia dữ liệu gốc (`configs/vsl_config.yaml` trỏ vào split dồn miền 489 lớp)
- **Mô tả:** File cấu hình chính [`configs/vsl_config.yaml`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/configs/vsl_config.yaml#L21-L24) đang trỏ vào `data/splits/tier2_train.csv` (chứa 488 mẫu miền Bắc), `val.csv` (chứa 488 mẫu miền Trung) và `test.csv` (chứa 488 mẫu miền Nam) với nhãn `num_classes: 489` (có 2 lớp thừa `'chiếu'`, `'bắt đền'`). Trong khi đó, checkpoint thực tế `stgcn_tier2_indomain.pt` (487 lớp) được train trên `data/splits/folds/tier2_indomain_*.csv`.
- **Bằng chứng:** Đã kiểm tra đối soát mã nguồn và dữ liệu:
  - `data/splits/tier2_train.csv`: 488/497 mẫu là miền Bắc.
  - `data/splits/folds/tier2_indomain_train.csv`: 326 Trung, 325 Bắc, 163 Nam.
- **Cách sửa đề xuất:** Cập nhật `configs/vsl_config.yaml` trỏ đường dẫn split sang `data/splits/folds/tier2_indomain_*.csv` và cập nhật `num_classes: 487` để tránh người sau chạy lại training bị rơi vào bẫy dồn miền cũ.

---

### 🟡 Mức độ MEDIUM (Hạn chế về dữ liệu & Đánh giá)

#### Lỗi 4: Thổi phồng chỉ số dịch thuật ViT5 do trùng lặp câu giữa Train và Test
- **Mô tả:** Tập kiểm thử VSL-GH gồm 300 câu được quay bởi signer S06. Tuy nhiên, 270 câu trong số này đã xuất hiện trong tập Train (do signers S01-S04 thể hiện). Điểm số BLEU 58.09 báo cáo trên toàn bộ S06 phản ánh năng lực ghi nhớ mẫu câu hơn là năng lực dịch thuật khái quát.
- **Bằng chứng:** Trên 30 câu thực sự độc lập (unseen sentences), BLEU giảm từ 58.09 xuống **27.87**.
- **Cách sửa đề xuất:** Trong tài liệu báo cáo khoa học, luôn phân tách rõ hai chỉ số: BLEU trên tập câu đã thấy (Signer-Heldout: 58.09) và BLEU trên tập câu chưa từng thấy (Sentence+Signer-Heldout: 27.87).

#### Lỗi 5: 2.740 từ vựng Cấp 2 chỉ có đúng 1 mẫu ($N=1$)
- **Mô tả:** Trong tổng số 3.315 từ vựng của kho `data/Dataset/`, có tới 2.740 từ chỉ có 1 video duy nhất. Không thể đưa các từ này vào huấn luyện mạng nơ-ron phân loại có giám sát (Supervised Learning) vì vi phạm nguyên lý chia tập Train/Val/Test.
- **Cách sửa đề xuất:** Giữ nguyên chiến lược hiện tại: 487 từ đa miền dùng cho ST-GCN Closed-Set; 2.740 từ còn lại dùng cho Ngân hàng Tra cứu (Lexicon Retrieval Bank / Cosine Matching).

---

## 4. BẢNG PHÂN TÍCH KHOẢNG TRỐNG DỮ LIỆU (PHẦN F)

| Phân hệ | Tình trạng dữ liệu hiện có | Định lượng khoảng trống còn thiếu | Nguồn công khai khả thi / Phương án bù đắp | Mức ưu tiên | Tác động kỳ vọng |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Cấp 1: Chữ cái (Fingerspelling)** | **THIẾU MODEL**<br>(~~Đã có 1.875 clip VSL thật~~ — đính chính: dữ liệu tổng hợp; **chưa có dữ liệu thật**) | Thiếu model weights và API; thiếu 2 chữ cái động (J, Z) theo Thông tư 17. | ~~Đã có sẵn 1.875 file `.npz`... Chỉ cần train.~~ Phải thu dữ liệu thật (`scripts/collect_alphabet_real.py`) hoặc xin bộ dữ liệu của nhóm HUST. | **P0** | Cho phép nhận diện chữ cái tĩnh chính xác khi giơ tay đơn lẻ (giải quyết triệt để lỗi chữ C ra hành quân). |
| **Cấp 2: Từ rời (Isolated Words)** | **ĐỦ MỘT PHẦN**<br>(487 từ đa miền đủ 3 miền; 2.740 từ chỉ có 1 mẫu) | Thiếu $\approx 5.500$ – $8.000$ clip (cần tối thiểu thêm 2-3 clip/từ cho 2.740 từ $N=1$). | Thu thập bổ sung từ từ điển ký hiệu trực tuyến (HCMUE - `tudienngonngukyhieu.com`) hoặc cộng đồng người Điếc. | **P2** | Mở rộng từ điển nhận diện trực tiếp từ 487 từ lên hàng nghìn từ vựng. |
| **Cấp 3: Câu liên tục (CSLR)** | **THIẾU MỘT PHẦN**<br>(4.200 keypoint files, nhưng chỉ gồm 300 câu y tế studio) | Thiếu các miền ngữ cảnh đời thường, giao tiếp, trường học; thiếu dữ liệu ngoại cảnh thực tế. | VSL-GH là bộ CSLR công khai duy nhất hiện nay của VSL. Bổ sung cần quay thực tế cùng người Điếc ($\ge 500$ câu mới). | **P1** | Nâng cao khả năng nhận diện câu ngoài ngữ cảnh bệnh viện. |
| **Dịch thuật (Gloss $\to$ Text)** | **ĐỦ CHO MIỀN Y TẾ**<br>(10K cleaned synthetic + 300 câu VSL-GH) | Thiếu câu song song thực tế do người Điếc dịch (ngữ liệu 10K là sinh bằng luật ngữ pháp). | Khai thác thêm dữ liệu văn bản từ sách dạy ngôn ngữ ký hiệu hoặc từ điển mở. | **P1** | Tăng độ tự nhiên và ngữ pháp tiếng Việt khi dịch các câu phức tạp. |

---

## 5. KẾ HOẠCH HÀNH ĐỘNG TIẾP THEO (NEXT ACTIONS BY PRIORITY)

1. **[P0] Huấn luyện Model Bảng chữ cái VSL Cấp 1 (Milestone A2 Training):**
   - ~~Viết script huấn luyện mạng MLP nhẹ trên 1.875 file landmark `.npz` có sẵn trong `data/vsl_alphabet_pilot/landmarks/`.~~ *(Đính chính: bộ này là tổng hợp — phải thu dữ liệu thật trước.)*
   - Lưu checkpoint chính thức vào `checkpoints/alphabet_vsl_best.pt`.
   - Bổ sung endpoint `POST /api/fingerspelling` trên `backend/main.py`.
   - Thay thế mã `Math.random()` trong `frontend/src/components/Fingerspelling.jsx` bằng API thật.

2. **[P0] Chuẩn hóa đồng bộ Cấu hình Huấn luyện Cấp 2:**
   - Cập nhật [`configs/vsl_config.yaml`](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/configs/vsl_config.yaml) để trỏ train/val/test vào `data/splits/folds/tier2_indomain_*.csv` (487 lớp).
   - Đánh dấu file `data/splits/tier2_train.csv`, `val.csv`, `test.csv` cũ là `tier2_confounded_DO_NOT_USE.csv` để bảo vệ tính toàn vẹn dữ liệu.

3. **[P1] Tích hợp CSLR Cấp 3 vào Streaming WebSocket Realtime:**
   - Bổ sung chế độ nhận diện chuỗi câu liên tục (CSLR Mode) trên giao diện webcam: gom cửa sổ 60–90 frame $\to$ đưa qua `CSLRRecognizer` CTC greedy decode $\to$ gọi ViT5 dịch câu tiếng Việt tự nhiên hoàn chỉnh.

4. **[P2] Khai thác triệt để 2.740 video $N=1$ qua Cơ chế One-Shot Retrieval:**
   - Trích xuất embedding đặc trưng không gian-thời gian cho 2.740 video nhóm "Other" đưa vào `VSLLexiconBank` để phục vụ tra cứu từ điển và so khớp One-Shot khi người dùng thực hiện cử chỉ lạ ngoài 487 lớp.
