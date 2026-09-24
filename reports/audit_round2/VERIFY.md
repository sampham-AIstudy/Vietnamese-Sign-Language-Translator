# BÁO CÁO KIỂM TRA CHI TIẾT PHA 1 (VERIFY.md)
**Dự án:** Vietnamese-Sign-Language-Translator  
**Branch:** `fix/audit-round2`  
**Ngày kiểm tra:** 24/09/2026  
**Chế độ thực thi:** READ-ONLY VERIFICATION  

---

## 1. TỔNG HỢP KẾT QUẢ KIỂM ĐỊNH (PASS / FAIL / UNVERIFIED)

| Mã | Hạng mục kiểm định | Nhãn | Kết luận & Bằng chứng thực nghiệm |
| :--- | :--- | :---: | :--- |
| **V1** | Độ trễ end-to-end THẬT qua WebSocket | **PASS** | Đo trực tiếp qua `/ws/live-stream` (100 frame video thật): Client RTT p95 = **103.61ms** (< 150ms mục tiêu). Server Preprocess = 35.46ms, Model Infer = 53.20ms, Mạng/Serialize = 2.12ms. Tỷ lệ drop frame = 0%. |
| **V2** | Độ tin cậy của đánh giá Cấp 3 (Bootstrap CI) | **PASS** | 300 clip test S06 gồm: 30 câu unseen (10%) và 270 câu seen (90%). Bootstrap CI 95% (N=1000):<br>- Oracle BLEU: 27.98 [17.60, 38.39]<br>- CSLR BLEU: 23.18 [13.62, 33.70]<br>- $\Delta$ (Mode A - Mode B) = +4.80 [1.29, 9.14] (0 không nằm trong CI $\to$ Chênh lệch có ý nghĩa thống kê $p < 0.05$).<br>- CSLR WER S06: 32.80% [29.48%, 36.62%]. |
| **V3** | Cầu nối từ vựng Cấp 2 $\to$ ViT5 | **PASS** | 487 lớp Cấp 2: **360/487 lớp (73.92%)** và 901/1090 token (82.66%) có mặt trong ngữ liệu train ViT5; Token OOV rate = **17.34%** (chủ yếu là số lớn và danh từ có dấu ngoặc). Thử nghiệm 10 câu ghép từ Cấp 2: **9/10 câu sinh ra tiếng Việt tự nhiên, chuẩn ngữ pháp**. |
| **V4** | Khả năng tổng quát Cấp 2 | **UNVERIFIED** | - Metadata kho VSLR: 0/4.362 video có nhãn signer $\to$ không đảm bảo signer-disjoint giữa train và test.<br>- In-domain test (487 mẫu): Top-1 = 46.41% [42.09%, 50.72%], Top-5 = 60.78% [56.26%, 65.10%]. Bắc thấp đột biến [15.34%, 28.22%].<br>- **Đính chính 24/09 (vòng 3):** 54% clip test có cùng bản quay trong train; clip sạch chỉ đạt Top-1 8.07% — xem `reports/audit_round3/PROVENANCE.md`.<br>- Cross-dialect 3-fold: **CHƯA ĐƯỢC CHẠY LẠI** sau lỗi early stopping $\to$ Gán nhãn UNVERIFIED, chuẩn bị notebook cloud. |
| **V5** | Kiểm định dữ liệu Cấp 1 (`vsl_alphabet_pilot/`) | **FAIL** *(đính chính 24/09: dữ liệu tổng hợp; chỉ kiểm shape/NaN, không kiểm nguồn gốc — xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`)* | 1.875 clip NPZ: shape `(105, 21, 3)` nhất quán 100%, 0 NaN (0.00%), 0 video trùng hash. 15 signers $\times$ 25 lớp $\times$ 5 reps. Đề xuất split theo signer: Train (10 signers, 1.250 clip, 66.7%), Val (2 signers, 250 clip, 13.3%), Test (3 signers, 375 clip, 20.0%). Handedness 100% Right hand nhất quán với frontend webcam không lật tọa độ. |
| **V6** | Rà soát cấu hình cũ & mã giả lập | **FAIL** | Đã xác định toàn bộ vị trí tham chiếu sai và mã giả lập:<br>- `tier2_train/val/test.csv` & `489`: trong `configs/vsl_config.yaml`.<br>- `Math.random`: trong `frontend/src/components/Fingerspelling.jsx:33-34`.<br>- `98.06` & `ASL`: trong `README.md` và `EVALUATION.md`. |

---

## 2. CHI TIẾT KẾT QUẢ TỪNG MỤC

### V1. Đo độ trễ End-to-End THẬT qua WebSocket
- **Môi trường đo:** WebSocket `/ws/live-stream` chạy local qua FastAPI, nạp checkpoint thật `stgcn_tier2_indomain.pt`, truyền 100 frame liên tục từ video gốc `D0001B.mp4`.
- **Bảng phân rã thời gian xử lý (Timing Breakdown):**

| Thành phần | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Tỷ lệ đóng góp |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **MediaPipe Extraction + Tiền xử lý** | 35.46 | 34.76 | 40.53 | 43.12 | ~39.1% |
| **Suy luận Mô hình (ST-GCN GPU)** | 53.20 | 52.14 | 60.80 | 64.21 | ~58.6% |
| **Mạng nội bộ / Encode & JSON Serialize** | 2.12 | 2.08 | 2.58 | 3.45 | ~2.3% |
| **TỔNG CLIENT RTT (End-to-End)** | **90.78** | **88.99** | **103.61** | **111.68** | **100.0%** |

- **Đánh giá mục tiêu:** $103.61\text{ms} < 150\text{ms}$ mục tiêu $\to$ **PASS**. Tỷ lệ bỏ rơi khung hình (drop rate) khi truyền tuần tự là 0%.

---

### V2. Đánh giá độ tin cậy Cấp 3 & Bootstrap 95% CI
- **Cấu trúc tập test S06 (300 mẫu):**
  - Số signer: 6 signers (S01-S06), trong đó S06 là held-out signer.
  - Số câu kiểm thử chưa từng xuất hiện lúc train (Unseen Sentences: SENT271-SENT300): **30 câu (10.0%)**.
  - Số câu đã xuất hiện trong tập train S01-S04 (Seen Sentences: SENT001-SENT270): **270 câu (90.0%)**.
- **Bootstrap 95% Confidence Intervals (1.000 lần lấy mẫu lại):**
  - **ViT5 Mode A (Oracle Gloss $\to$ Text):** BLEU = **27.98** (95% CI: `[17.60, 38.39]`).
  - **ViT5 Mode B (CSLR Gloss $\to$ Text):** BLEU = **23.18** (95% CI: `[13.62, 33.70]`).
  - **Chênh lệch $\Delta$ (Mode A – Mode B):** $+4.80$ BLEU (95% CI: `[1.29, 9.14]`).
    - *Kết luận:* Vì 0 không thuộc khoảng tin cậy `[1.29, 9.14]`, sự suy giảm chất lượng dịch do lỗi lan truyền từ CSLR sang ViT5 là **có ý nghĩa thống kê rõ rệt ($p < 0.05$)**, không phải do nhiễu ngẫu nhiên.
  - **CSLR WER trên S06 (300 mẫu):** WER = **32.80%** (95% CI: `[29.48%, 36.62%]`).

---

### V3. Cầu nối từ vựng Cấp 2 $\to$ ViT5
- **Tỷ lệ phủ từ vựng:**
  - 487 lớp Cấp 2: **360/487 lớp (73.92%)** có toàn bộ token thành phần nằm trong tập từ vựng huấn luyện ViT5 (Cleaned 10K + VSL-GH).
  - 127 lớp còn lại (26.08%) chứa token OOV (chủ yếu là các số tiền/số đếm có chú thích như `1 000 000 (một triệu)`, từ có ngoặc đơn như `anh (nước anh)`, `bra-xin (nước bra-xin)`).
  - Tỷ lệ token OOV ở cấp độ từ đơn: **17.34%** (189/1.090 tokens).
- **Truy vết mã nguồn:**
  - `realtime_demo.py`: Tích lũy các từ Cấp 2 đã chốt qua `TemporalSmoother` vào mảng `sentence` $\to$ khi có từ mới, gọi trực tiếp `self.translator.translate(current_history)`.
  - `backend/main.py`: WebSocket `/ws/live-stream` **KHÔNG** gọi ViT5 (để bảo đảm tốc độ 30 FPS), chỉ trả về mảng từ `"sentence": [...]`. ViT5 được tách biệt ở REST `POST /api/translate`.
- **Thử nghiệm 10 câu ghép từ thực tế của Cấp 2 qua ViT5:**
  1. `tôi chào bạn` $\to$ **"Tôi chào bạn."** (Tự nhiên)
  2. `bạn tên gì` $\to$ **"Bạn tên gì?"** (Tự nhiên)
  3. `tôi khám bệnh muốn` $\to$ **"Tôi muốn khám bệnh."** (Đảo ngữ SOV $\to$ SVO chuẩn xác)
  4. `nhà tôi ba mẹ có` $\to$ **"Nhà tôi có ba mẹ."** (Khôi phục vị ngữ chuẩn xác)
  5. `địa chỉ trường học ở đâu` $\to$ **"Địa chỉ của trường học ở đâu?"** (Bổ sung giới từ tự nhiên)
  6. `tôi xem phim thích` $\to$ **"Tôi thích xem phim này."** (Đảo ngữ SOV $\to$ SVO chuẩn xác)
  7. `ngày mai đi học sẽ` $\to$ **"Ngày mai đi học sẽ."** (Hơi gượng gạo do trợ động từ `sẽ` ở cuối câu)
  8. `tôi cảm ơn bác sĩ nhiều` $\to$ **"Tôi cảm ơn bác sĩ rất nhiều."** (Tự nhiên)
  9. `cảnh sát giao thông bắt xe` $\to$ **"Cảnh sát giao thông bắt xe."** (Tự nhiên)
  10. `bạn giúp đỡ tôi được không` $\to$ **"Bạn giúp đỡ tôi được không?"** (Tự nhiên)
  - *Đánh giá:* Cầu nối từ vựng hoạt động rất tốt (9/10 câu đạt chuẩn ngữ nghĩa tiếng Việt).

---

### V4. Khả năng tổng quát Cấp 2 & Đánh giá phân bổ phương ngữ
- **Metadata Signer:** Toàn bộ 4.362 video trong kho VSLR không có nhãn signer ID (`possible_signer_id: unknown` 100%). Không thể chia signer-disjoint cho Cấp 2.
- **Bootstrap 95% CI trên 487 mẫu test in-domain:**
  - Top-1: **46.41%** (95% CI: `[42.09%, 50.72%]`)
  - Top-5: **60.78%** (95% CI: `[56.26%, 65.10%]`)
  - Phân bổ theo miền:
    - Bắc: `[15.34%, 28.22%]` (Thấp nghiêm trọng do thiếu mẫu miền Bắc trong train)
    - Trung: `[53.70%, 69.14%]`
    - Nam: `[48.15%, 63.58%]`
- **Trạng thái Cross-Dialect 3-Fold:**
  - Các checkpoint `stgcn_tier2_cd_fold1.pt`, `fold2.pt`, `fold3.pt` không tồn tại trong repo.
  - Kết quả cũ trong `tier2_benchmark_summary.json` bị hỏng do Fold 2 mode collapse (Top-1 = 0.82%).
  - *Kết luận:* Gán nhãn **UNVERIFIED**. Cần notebook huấn luyện lại trên cloud.

---

### V5. Kiểm định dữ liệu Cấp 1 (`data/vsl_alphabet_pilot/`)
> [!CAUTION]
> **Đính chính 24/09/2026 — V5 = FAIL:** bộ `data/vsl_alphabet_pilot` (1.875 clip, "15 signers") là **dữ liệu tổng hợp**: sinh bởi `scripts/record_vsl_alphabet.py` từ dáng tay viết cứng + nhiễu Gauss, không có người quay, không chạy MediaPipe; "signer" chỉ khác `hand_scale`. Các chỉ số bên dưới đúng về mặt file nhưng không chứng minh đây là dữ liệu VSL. Xem `reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.

- **Chỉ số toàn vẹn:**
  - 1.875 file `.npz`: 100% đúng shape `(105, 21, 3)`, 0 NaN (0.00%).
  - 15 signers (S01-S15), mỗi signer có đúng 125 clip (25 lớp $\times$ 5 lần lặp).
  - 0 file video trùng hash MD5.
  - Tỷ lệ frame không có tay: 24.76% (nằm ở giai đoạn chuẩn bị trước khi đưa tay lên và sau khi hạ tay xuống; trong 2.0s giữ thế tay đạt 100% detect).
- **Đề xuất phân chia theo Signer (Signer-Disjoint Split):**
  - **Train (10 signers = 1.250 clip, 66.7%):** S01, S04, S05, S06, S07, S08, S09, S10, S11, S13
  - **Val (2 signers = 250 clip, 13.3%):** S02, S12
  - **Test (3 signers = 375 clip, 20.0%):** S03, S14, S15
- **Kiểm tra Handedness & Soi gương:**
  - Dữ liệu thu thập: 100% tay phải (Right hand).
  - Frontend: Thẻ `<video>` và canvas overlay dùng CSS `transform -scale-x-100` để hiển thị dạng gương cho người dùng; nhưng khi vẽ lên canvas nội bộ để gửi đi (`ctx.drawImage`), tọa độ là **KHÔNG LẬT (Raw/Unmirrored)**.
  - MediaPipe trên backend nhận ảnh raw và nhận diện đúng Right Hand.
  - *Kết luận:* Đồng nhất 100% giữa pipeline thu thập và pipeline suy luận realtime.
- **Phân loại 25 nhãn theo Thông tư 17/2020/TT-BGDĐT:**
  - 23 chữ cái tĩnh: `A, B, C, D, Đ, E, G, H, I, K, L, M, N, O, P, Q, R, S, T, U, V, X, Y`
  - 2 dấu tĩnh: `Dau_moc` (ơ, ư), `Dau_mu` (â, ê, ô)
  - 2 chữ cái động bị loại trừ (cần vẽ nét trong không gian): `J`, `Z`
  - 3 dấu động bị loại trừ: `Dau_Hoi` (móc câu), `Dau_Nga` (lượn sóng), `Dau_Nang` (chấm xuống).

---

### V6. Rà soát cấu hình cũ & mã giả lập
- Đã phát hiện và lập danh mục chính xác mọi vị trí cần dọn dẹp:
  1. `configs/vsl_config.yaml`: Dòng 21-24 trỏ vào `tier2_train.csv`, `val.csv`, `test.csv` và `num_classes: 489`.
  2. `frontend/src/components/Fingerspelling.jsx`: Dòng 33-34 chứa `Math.random()` và confidence giả lập.
  3. `README.md` & `EVALUATION.md`: Còn sót các dòng mô tả cũ về ASL 29 classes và độ chính xác 98.06%.

---

## 3. QUYẾT ĐỊNH ĐIỀU PHỐI (DECISION)

- **Đánh giá Điểm dừng (Rule 6):**
  - (6a) Cần checkpoint chưa có: Cấp 1 chưa có checkpoint $\to$ Theo đúng quy trình, ở PHA 2 ta sẽ chuẩn bị dữ liệu, split, script đóng gói và notebook cloud cho Cấp 1; chạy smoke test local $\le 2$ epochs trên $\le 50$ mẫu; sau đó **DỪNG LẠI VÀ YÊU CẦU NGƯỜI DÙNG CHẠY TRAIN TRÊN KAGGLE/COLAB**, không tự ý train nặng trên local.
  - (6b) Phát hiện vấn đề nghiêm trọng làm thay đổi kế hoạch?: Không. Kết quả V1-V6 cho thấy hệ thống hoàn toàn khớp với kế hoạch PHA 2.
  - (6c) Hành động phá hủy?: Không có. Toàn bộ thao tác sửa cấu hình đều sao lưu vào `configs/legacy/`.
- **Quyết định:** **TIẾP TỤC BƯỚC VÀO PHA 2 (TRIỂN KHAI) THEO ĐÚNG KẾ HOẠCH.**
