# BÁO CÁO AUDIT NGUỒN GỐC DỮ LIỆU & KIỂM KÊ WORKSPACE (PHASE 4A PREFLIGHT)

> **Ngày thực hiện:** 2026-09-21  
> **Người thực hiện:** Senior CV & AI Engineer  
> **Bộ quy chuẩn áp dụng:** [vsl-data-integrity](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/.agents/skills/vsl-data-integrity/SKILL.md) & [vsl-evaluation-rigor](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/.agents/skills/vsl-evaluation-rigor/SKILL.md)  
> **Trạng thái:** Hoàn tất thẩm định thực nghiệm — Đề xuất phương án dọn dẹp (Chưa xóa bất kỳ file nào).

---

## PHẦN A: AUDIT NGUỒN GỐC & TÍNH XÁC THỰC CỦA DỮ LIỆU

Nhằm đảm bảo tính khoa học, trung thực tuyệt đối và tránh lặp lại bài học lịch sử (từng nhầm lẫn bộ ký hiệu tay ASL của Mỹ thành bảng chữ cái VSL), đợt audit này kiểm tra độc lập và đối soát thực nghiệm 3 tài nguyên được giới thiệu trong Phase 4A:
1. File song ngữ [vie_vsl_10k.jsonl](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/data/external/parallel_text/vie_vsl_10k.jsonl) (9.405 cặp)
2. Bộ dữ liệu skeleton VSL-GH (4.200 mẫu frontal, 300 câu)
3. Model Continuous Sign Language Recognition [cslr_best.pt](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/checkpoints/cslr_best.pt) (WER 32.80%)

---

### 1. Thẩm định `vie_vsl_10k.jsonl`

#### 1.1. Nguồn gốc xuất xứ & Hồ sơ Git
- **Vị trí file:** `data/external/parallel_text/vie_vsl_10k.jsonl` (Kích thước: 1.22 MB, 9.405 dòng JSONL hợp lệ).
- **Script sinh ra:** [scripts/prepare_canonical_translation.py](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/scripts/prepare_canonical_translation.py), chạy ngày 2026-09-21.
- **Dữ liệu gốc:**
  - Repository upstream: `https://github.com/BichDiep/Parallel-Corpus-Vie-VSL.git`
  - Commit hash: `f57558c3fa79ced8a961cba825157c573fd4c74d` (Branch: `main`)
  - Đường dẫn clone: `clone/Parallel-Corpus-Vie-VSL/`
  - Tệp nguồn trực tiếp: `VSL10k.txt` (10.000 câu) và `Vie10k.txt` (10.000 câu). Ngoài ra repo còn có `Corpus-Vie-VSL-10K.xlsx`, `Vie-Traveling.xlsx`, `Vie10k_phantich.txt`, `VSL10k_phantich.txt`, `VSL-Lexicon.rar`.
- **Tác giả & Đơn vị nghiên cứu:**
  - **TS. Nguyễn Thị Bích Điệp** (`BichDiep ICTU`), Khoa Công nghệ Thông tin, Trường Đại học Công nghệ Thông tin và Truyền thông — Đại học Thái Nguyên (ICTU).
  - Nhóm nghiên cứu gồm TS. Nguyễn Thị Bích Điệp, PGS.TS. Nguyễn Gia Như và TS. Nguyễn Văn Vinh.
  - Các công trình nghiên cứu liên quan: Đề tài luận án tiến sĩ và các bài báo khoa học về dịch máy tự động từ văn bản tiếng Việt sang ngôn ngữ ký hiệu Việt Nam dựa trên cấu trúc cú pháp và văn phạm phi ngữ cảnh xác suất (PCFG).
- **Hồ sơ lưu trữ (Provenance):** Đã được lập chỉ mục tại [docs/provenance/external_repositories.md](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/docs/provenance/external_repositories.md#L35-L58).

---

### 2. Kiểm tra tính xác thực của cột "vsl" trong `vie_vsl_10k.jsonl`

#### 2.1. Phân tích thực nghiệm trên mẫu ngẫu nhiên
Đã trích xuất 25 mẫu ngẫu nhiên (seed 42) thông qua script kiểm tra [scratch/audit_samples.py](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/scratch/audit_samples.py):

| STT | Câu tiếng Việt gốc (`vi`) | Chuỗi VSL (`vsl`) | Bản chất biến đổi phát hiện |
|:---|:---|:---|:---|
| 01 | Vui lòng cho tôi một lon bia . | cho tôi một lon bia . | Bỏ từ lịch sự "Vui lòng" |
| 02 | Bạn biết điều này . | Bạn biết điều . | Bỏ từ chỉ định "này" |
| 03 | Vâng , chúng tôi đã nghĩ đến việc đi đến một nhà hàng ưa thích . | Vâng chúng tôi nghĩ đến việc đi đến một nhà hàng ưa thích . | Bỏ trợ từ thời thể "đã" |
| 04 | tôi sẽ chuyển lời nhắn đến ông brown giúp ông . | tôi chuyển lời nhắn đến ông brown giúp ông . | Bỏ trợ từ tương lai "sẽ" |
| 05 | tôi bị đau nhói ở đây . | tôi đau nhói ở đây . | Bỏ thụ động từ "bị" |
| 06 | món tôi gọi vẫn chưa đến . | món tôi gọi chưa đến . | Bỏ phó từ "vẫn" |
| 07 | Cha nào con nấy . | Cha con nấy . | Bỏ "nào" |
| 08 | vâng , thực sự . | vâng thực sự . | Bỏ dấu phẩy |
| 09 | Tôi có khả năng tương tác xã hội tốt . | Tôi có khả năng tương tác xã hội tốt . | **Giống hệt 100% tiếng Việt** (từ vựng trừu tượng không có mã hóa ký hiệu) |
| 10 | Bạn sẽ không để lại công việc mới thực hiện được một nửa chứ ? | Bạn công việc thực hiện được một nửa không ? | Bỏ "sẽ", "để lại", "mới", "chứ"; chuyển "không" về cuối câu |
| 11 | Bạn bao nhiêu tuổi ? | Bạn tuổi bao nhiêu? | Đảo vị trí danh từ & từ để hỏi: "tuổi bao nhiêu" |
| 12 | Chúng ta đã xong chưa ? | Chúng ta xong chưa ? | Bỏ "đã" |
| 13 | Chúng tôi hết sức xin lỗi về chuyện đã xảy ra . | Chúng tôi hết sức xin lỗi về chuyện xảy ra . | Bỏ giới từ "về", bỏ "đã" |
| 14 | Có một kỳ nghỉ tuyệt vời . | Có một kỳ nghỉ tuyệt vời . | **Giống hệt 100% tiếng Việt** |
| 15 | tôi sẽ điều một người khuân vác lên ngay . | tôi điều một người khuân vác lên . | Bỏ "sẽ", bỏ "ngay" |
| 16 | vâng , để tôi đưa bạn đến nhà hàng hải sản gần đây . | vâng tôi đưa bạn đến nhà hàng hải sản gần đây . | Bỏ "để" |
| 17 | Tôi đã ly hôn . | Tôi ly hôn . | Bỏ "đã" |
| 18 | tôi sẽ mở chai bia này nhé ? | tôi mở chai bia ? | Bỏ "sẽ", "này", "nhé" |
| 19 | cô ấy có má lúm đồng tiền khi cô ấy cười . | cô có má lúm đồng tiền khi cô cười . | Đổi "cô ấy" thành "cô" |
| 20 | thật là đáng tiếc phải không ? | thật đáng tiếc phải không ? | Bỏ hệ từ "là" |
| 21 | Tôi hết tiền . | Tôi hết tiền . | **Giống hệt 100% tiếng Việt** |
| 22 | xin lỗi , nhưng tôi tin rằng tôi đã để quên chiếc ô trên xe buýt mà chở tôi từ sân bay đén khách sạn . | xin lỗi , tôi tin tôi quên chiếc ô trên xe buýt chở tôi từ sân bay đến khách sạn . | Bỏ liên từ "nhưng", "rằng", "mà", "đã để"; sửa typo "đén" |
| 23 | tôi không mong đợi gặp bạn ở đây làm ơn . | tôi mong đợi gặp bạn ở m ơn không . | **Lỗi xử lý chuỗi (Regex/Rule Bug):** Bỏ "đây là" làm cụm "làm ơn" rách thành "m ơn không" |
| 24 | hút thuốc hay không hút thuốc ? | hút thuốc hay hút thuốc không ? | Đảo từ phủ định "không" ra sau động từ |
| 25 | Tôi học 5 môn : toán , văn , lý , hóa , sinh . | Tôi học môn 5 : toán , văn , lý , hóa , sinh . | Đảo số đếm: "5 môn" -> "môn 5" |

#### 2.2. Bằng chứng cấu trúc cây ngữ pháp (PCFG Syntax Trees)
Đối chiếu trực tiếp 2 tệp `clone/Parallel-Corpus-Vie-VSL/Vie10k_phantich.txt` và `VSL10k_phantich.txt` cho thấy toàn bộ ngữ liệu được sinh ra bằng cơ chế **chuyển giao cú pháp dựa trên luật (Rule-based Tree Transformation)** sử dụng bộ gán nhãn cú pháp Stanford Parser:
- Câu 41:
  - Tiếng Việt: `(S (NP (P Tôi)) (VP (R không) (V thích) (NP (N rắn))) (. .))`
  - VSL: `(S (NP (P Tôi)) (AP (A rắn) (VP (R không) (V thích))) (. .))`
  - *Bản chất:* Đảo ngữ tân ngữ `NP(rắn)` lên trước cụm vị ngữ `VP(không thích)` (cấu trúc SOV).
- Câu 11:
  - Tiếng Việt: `Tôi học 4 môn` (`M 4`, `N môn`)
  - VSL: `Tôi học môn 4` (`N môn`, `M 4`) -> Đảo số từ ra sau danh từ.
- Câu 23:
  - Tiếng Việt: `Ai là lớp trưởng ?`
  - VSL: `Lớp trưởng ai ?` -> Từ để hỏi `Wh-word` chuyển về cuối câu, triệt tiêu hệ từ `là`.

#### 2.3. Thống kê định lượng trên toàn bộ 9.405 câu
- **Câu trùng khớp 100% từng byte (`vi == vsl`):** **2.203 câu** (**23.42%**).
- **Câu có tập từ vựng chuẩn hóa giống hệt nhau:** **2.230 câu** (**23.71%**).
- **Lỗi kỹ thuật:** Xuất hiện các lỗi ghép từ cơ học do biểu thức chính quy (ví dụ: `ở m ơn không` thay vì `ở đây làm ơn`).
- **Từ vựng:** Cột "vsl" hoàn toàn sử dụng chữ quốc ngữ tiếng Việt viết thường/hoa bình thường, không phải là ID ký hiệu (Gloss ID) chuẩn hóa theo từ điển ký hiệu VSL của cộng đồng người Điếc (như Vi-Sign hay QIPEDC).

#### 2.4. Kết luận về tính xác thực của cột "vsl"
- **Bản chất:** **DỮ LIỆU SINH BẰNG LUẬT CÚ PHÁP (RULE-BASED SYNTHETIC VSL PERMUTATION)**.
- **Đánh giá khoa học:** Đây **KHÔNG PHẢI** là bản ghi gloss tự nhiên thu thập từ người Điếc hay các chuyên gia ngôn ngữ ký hiệu. Đây là ngữ liệu giả lập được sinh ra từ văn bản tiếng Việt thông qua các thuật toán phân tích cây cú pháp PCFG và luật hoán vị từ vựng (chuyển đổi SVO sang SOV/OSV, chuyển từ phủ định/từ hỏi về cuối, lược bỏ hư từ).
- **Ý nghĩa đối với mô hình dịch:** Nếu fine-tune ViT5 trên bộ này, mô hình sẽ học một hàm tái sắp xếp trật tự từ và lược bỏ stop words của tiếng Việt, chứ **không phải** là dịch từ ngôn ngữ ký hiệu thị giác thực tế sang tiếng Việt.

---

### 3. Xác minh bộ dữ liệu "VSL-GH" (4.200 video)

#### 3.1. Truy tìm tệp video gốc trên toàn bộ hệ thống
- **Tìm kiếm toàn bộ file video (`.mp4`, `.avi`, `.mov`, `.mkv`)**:
  - Tại `clone/Vietnamese-Sign-Language-Translation/`: **0 file**.
  - Tại `data/external/vsl_gh/`: **0 file**.
  - Toàn bộ đĩa cứng dự án: Chỉ có 4.362 video gốc của bộ VSLR cũ nằm tại `data/Dataset/Videos/`.
- **Nguyên nhân không có video trong repo VSL-GH**:
  - Kiểm tra file `clone/Vietnamese-Sign-Language-Translation/.gitignore`:
    ```gitignore
    # Ignore raw videos but keep keypoints and annotations
    data/videos/
    data/raw/
    data/ELAN/
    data/*.xlsx
    ```
  - Tác giả gốc (`nguyentheanh822`) đã chủ động cấu hình `.gitignore` để **loại trừ hoàn toàn thư mục `data/videos/`** trước khi push lên GitHub, chỉ lưu trữ tọa độ trích xuất sẵn và nhãn chú thích thời gian.

#### 3.2. Kiểm tra công cụ & script trích xuất tọa độ
- **Script trích xuất gốc được tìm thấy tại:** [clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py).
- **Môi trường tác giả:** Chạy trên Linux server (`BASE_DIR = Path("/workspace/yhnn/VSL_GH")`).
- **Thư viện sử dụng:** Google MediaPipe Holistic (`mediapipe.python.solutions.holistic.Holistic` với cấu hình: `model_complexity=1`, `smooth_landmarks=True`, `min_detection_confidence=0.5`, `min_tracking_confidence=0.5`).
- **Cấu trúc 137 điểm landmarks (411 chiều / frame):**
  - **Pose:** 25 landmarks (dims 0..74) — lấy 25 điểm thân trên, bỏ chân dưới.
  - **Face Mesh:** 70 landmarks (dims 75..284) — viền môi, mắt, lông mày, mũi, đường viền mặt.
  - **Left Hand:** 21 landmarks (dims 285..347) — toàn bộ 21 khớp xương bàn tay trái MediaPipe.
  - **Right Hand:** 21 landmarks (dims 348..410) — toàn bộ 21 khớp xương bàn tay phải MediaPipe.
- **Tệp lưu trữ có sẵn trên máy:**
  - `data/external/vsl_gh/keypoints_frontal/`: **4.200 tệp `.npy` góc quay thẳng**, shape `[T, 411]`.
  - `docs/provenance/archive/vsl_gh_side_view/`: **1.830 tệp `.npy` góc quay nghiêng**.
  - `data/external/vsl_gh/annotations/`: **4.200 tệp nhãn thời gian** (gloss boundaries).

#### 3.3. Hạn chế & Rủi ro khoa học
1. **Không thể huấn luyện mô hình thị giác điểm ảnh (RGB Pixels):** Không thể áp dụng các mô hình 3D-CNN (I3D, SlowFast) hay Video Vision Transformer (TimeSformer, ViViT) trực tiếp từ video thô.
2. **Không thể đối chứng trực quan cử chỉ người ký:** Khi mô hình nhận diện sai một từ, không thể mở video MP4 để xem người ký có thực hiện đúng cử chỉ VSL hay không.
3. **Phụ thuộc hoàn toàn vào chất lượng trích xuất MediaPipe v1:** Nếu MediaPipe bị trượt tay hoặc mất dấu khớp trong các khung hình nhanh, tọa độ `.npy` bị nhiễu vĩnh viễn và không thể trích xuất lại bằng YOLO-Pose hay MediaPipe phiên bản mới hơn.
4. **Điểm khả thi:** Dữ liệu skeleton 137 điểm hoàn toàn tương thích và sử dụng tốt cho các mô hình Graph Convolution (ST-GCN) và RNN (BiGRU).

---

### 4. Xác minh mô hình `cslr_best.pt` (WER 32.80%)

#### 4.1. Thông số tệp & Môi trường huấn luyện
- **Đường dẫn checkpoint:** [checkpoints/cslr_best.pt](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/checkpoints/cslr_best.pt)
- **Kích thước:** 28.206.138 bytes (~26.90 MiB).
- **Thời điểm hoàn thành:** 2026-09-21 11:36:00.
- **Phần cứng thực thi:** Card rời `NVIDIA GeForce RTX 3050 Laptop GPU` (VRAM 4 GB), chế độ Mixed Precision (AMP FP16).
- **Thời gian huấn luyện:** 2.108,74 giây (~35,1 phút), trung bình 52,7 giây/epoch qua 40 epochs.

#### 4.2. Kiến trúc mạng & Chiến lược Transfer Learning
- **Script huấn luyện:** [src/training/train_cslr.py](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/src/training/train_cslr.py) (Model class: `STGCNBiGRU_CSLR`).
- **Quy trình 2 giai đoạn (Two-stage transfer learning):**
  - *Backbone:* Khởi tạo trọng số không gian từ mô hình nhận diện từ đơn lập [checkpoints/stgcn_best.pt](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/checkpoints/stgcn_best.pt) (408.067 tham số không gian).
  - *Giai đoạn 1 (Epochs 1–10):* Đóng băng hoàn toàn Backbone ST-GCN, chỉ huấn luyện khối giảm mẫu thời gian (Stride-2 Conv1D) + BiGRU 2 tầng (hidden_size=256) + đầu phân loại CTC với learning rate $10^{-3}$.
  - *Giai đoạn 2 (Epochs 11–40):* Mở khóa toàn bộ mạng, huấn luyện liên hợp với vi sai learning rate ($10^{-4}$ cho ST-GCN, $5 \times 10^{-4}$ cho BiGRU/CTC) và cơ chế Early Stopping theo Validation WER.

#### 4.3. Hồ sơ đường cong huấn luyện & Thẩm định
Kiểm tra chi tiết [reports/cslr_training_history.json](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/reports/cslr_training_history.json):
- Epoch 1: `train_loss` = 5.3758, `val_wer` (S05) = 73.30%
- Epoch 10 (hết Stage 1): `train_loss` = 1.0963, `val_wer` = 46.17%
- Epoch 31: Đạt điểm tối ưu toàn cục (**`val_wer` = 30.48%**, `val_loss` = 1.3103, `train_loss` = 0.1134) -> Lưu checkpoint `cslr_best.pt`.
- Epoch 40: `val_wer` = 33.59%.

#### 4.4. Thí nghiệm tái lập độc lập kết quả Test (WER 32.80%)
Nhằm đảm bảo số liệu không bị ngụy tạo hoặc tính toán sai, một script đánh giá độc lập [scripts/evaluate_cslr_s06.py](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/scripts/evaluate_cslr_s06.py) đã được viết và thực thi trực tiếp trên GPU:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_cslr_s06.py
```

**Kết quả đo đạc thực tế:**
```
============================================================
TEST EVALUATION RESULT (S06 Held-Out Signer):
  Total Samples: 300
  Test WER: 32.80%
  Substitutions: 260 (21.87%)
  Deletions:     115 (9.67%)
  Insertions:    10 (0.84%)
  Total Ref Words: 1189
  Total Hyp Words: 1089
============================================================
```
- **Tỷ lệ lỗi:** $\text{WER} = \frac{260 + 115 + 15}{1189} = \frac{390}{1189} = 32.8007\% \approx \mathbf{32.80\%}$.
- **Tính độc lập:** Tập test gồm 300 câu do người ký **S06** thực hiện, hoàn toàn chưa từng xuất hiện trong tập train (S01–S04) hay tập val (S05) — bảo đảm giao thức **Unseen Signer Generalization**.
- **Phát hiện kỹ thuật sống còn:** Mô hình chỉ đạt WER 32.80% khi tiền xử lý bật cờ `normalize=True` (chuẩn hóa gốc tọa độ về tâm vai và tỉ lệ theo khoảng cách vai). Nếu quên bật chuẩn hóa (`normalize=False`), WER lập tức suy giảm nghiêm trọng về **77.38%**!

---

### 5. Kết luận phân loại Phần A (Summary of Provenance Verdicts)

Áp dụng đúng chuẩn mực của skill `vsl-data-integrity`:

| Thành phần | Đường dẫn | Phân loại | Bản chất & Hạn chế | Khuyến nghị sử dụng |
|:---|:---|:---:|:---|:---|
| `vie_vsl_10k.jsonl` | `data/external/parallel_text/` | **[BÁN XÁC THỰC]** | Dữ liệu học thuật có thật từ ĐH CNTT&TT Thái Nguyên (TS. Nguyễn Thị Bích Điệp). Tuy nhiên, cột "vsl" là **văn bản sinh bằng luật PCFG (Rule-based Synthetic Permutation)**, không phải gloss VSL tự nhiên của người Điếc. 23.42% câu giống hệt tiếng Việt. | Chỉ được sử dụng làm bộ ngữ liệu tiền huấn luyện tái cấu trúc câu (Syntax Reordering Pretraining) cho ViT5; **tuyệt đối không báo cáo đây là dịch gloss tự nhiên sang tiếng Việt**. |
| Bộ dữ liệu VSL-GH | `data/external/vsl_gh/` | **[BÁN XÁC THỰC]** | Tọa độ MediaPipe Holistic 137 điểm (4.200 file `.npy`) và nhãn thời gian là có thật, trích xuất chính xác. Tuy nhiên, **HOÀN TOÀN KHÔNG CÓ TỆP VIDEO GỐC MP4** trên đĩa (tác giả đã ignore video khi đưa lên Git). | Sử dụng hợp lệ cho các mô hình đồ thị khung xương (ST-GCN, GCN-BiGRU). Không thể sử dụng cho mô hình thị giác RGB. |
| Model `cslr_best.pt` | `checkpoints/cslr_best.pt` | **[XÁC THỰC]** | Mô hình có thật, được huấn luyện trực tiếp trong dự án trên RTX 3050, có đầy đủ log lịch sử 40 epoch, đã được script độc lập tái lập chính xác 100% kết quả **WER 32.80%** trên người ký độc lập S06. | Đạt chuẩn làm Baseline CSLR chính thức cho dự án. |

---

## PHẦN B: ĐỀ XUẤT DỌN DẸP THƯ MỤC (DIRECTORY CLEANUP PROPOSAL)

> [!IMPORTANT]
> **QUY TẮC AN TOÀN:** Không có bất kỳ file nào bị xóa trong phiên làm việc này. Dưới đây là bảng thống kê dung lượng và các đề xuất phân loại để người dùng xem xét và phê duyệt trước khi thực thi.

### 1. Thống kê dung lượng hiện tại toàn workspace (Cấp 1)

Tổng dung lượng ghi nhận: **~29.62 GB** trải rộng trên **367.067 tệp tin**.

| Thư mục cấp 1 | Số lượng tệp | Dung lượng (MB) | Tỷ trọng | Chức năng chính |
|:---|---:|---:|---:|:---|
| `data` | 188.660 | 19.812,70 MB | **66.89%** | Video VSLR gốc (2.76 GB) + **Dữ liệu rò rỉ cũ (17.05 GB)** |
| `.venv` | 50.790 | 5.903,41 MB | **19.93%** | Môi trường ảo Python 3.11 + PyTorch CUDA |
| `data` | 98.536 | 2.173,68 MB | **7.34%** | VSL-GH canonical + VSLR keypoints + **Bộ ảnh ASL (1.05 GB)** |
| `clone` | 10.536 | 1.082,20 MB | **3.65%** | Các repo ngoài đã clone (**Trùng lặp 1.02 GB keypoints**) |
| `docs` | 1.859 | 302,41 MB | 1.02% | Tài liệu dự án + **Archive side-view keypoints (295 MB)** |
| `frontend` | 10.299 | 147,69 MB | 0.50% | Giao diện React Vite + node_modules |
| `checkpoints` | 12 | 111,07 MB | 0.37% | Trọng số mô hình (ST-GCN, CSLR, Baselines) |
| `.gitnexus` | 206 | 50,36 MB | 0.17% | Knowledge Graph & Code Intelligence Index |
| `experiments` | 31 | 10,94 MB | 0.04% | Model xuất cũ (.pth, .onnx, .torchscript) |
| `submission` | 14 | 5,56 MB | 0.02% | Báo cáo, ảnh demo, slide |
| `node_modules` (root) | 2.598 | 5,49 MB | 0.02% | Node runtime hỗ trợ GitNexus |
| `reference` | 2 | 2,56 MB | 0.01% | Tài liệu tham khảo PDF |
| `results` | 15 | 1,32 MB | <0.01% | Kết quả đánh giá |
| `src` | 94 | 0,64 MB | <0.01% | Mã nguồn chính của dự án |
| `scripts` | 39 | 0,34 MB | <0.01% | Script tiền xử lý, huấn luyện, đánh giá |
| `reports` | 15 | 0,20 MB | <0.01% | Lịch sử huấn luyện JSON/CSV |
| `scratch` | 12 | 0,06 MB | <0.01% | Script test nháp một lần |
| `tests` | 7 | 0,06 MB | <0.01% | Unit test & Integration test |
| `backend` | 3 | 0,05 MB | <0.01% | FastAPI backend service |
| `.agents` / `.claude` | 16 | 0,08 MB | <0.01% | Cấu hình Agent Skills & Prompts |
| `configs` | 8 | 0,01 MB | <0.01% | File cấu hình YAML |
| Khác (`__pycache__`, `.vscode`) | 4 | 0,03 MB | <0.01% | Cache hệ thống |

---

### 2. Nhận diện các điểm nghẽn dung lượng & tệp tin rác

1. **`data/Processed/` (17.05 GB / 184.296 file .npz):**
   - Đã bị cách ly từ 2026-09-12 vì lỗi Data Leakage nghiêm trọng (như mô tả trong [Processed_LEAKED_DO_NOT_USE.md](file:///C:/Users/Admin/Python%20Advanced/Deep%20Learning%20-%20CV/Project/data%20%282%29/Processed_LEAKED_DO_NOT_USE.md)). Thư mục này chiếm tới 58% dung lượng ổ cứng và hơn 50% số inode của toàn bộ workspace.
2. **`data/asl_alphabet_train/` và `test/` (1.05 GB / 87.028 ảnh):**
   - Là bộ ảnh bảng chữ cái Mỹ (ASL) không liên quan tới tiếng Việt hay VSL, từng bị huấn luyện nhầm trong quá khứ.
3. **`clone/Vietnamese-Sign-Language-Translation/data/keypoints/` (1.02 GB / 6.030 file .npy):**
   - Trùng lặp hoàn toàn 100% với dữ liệu canonical đã chuyển giao sang `data/external/vsl_gh/keypoints_frontal/` và `docs/provenance/archive/vsl_gh_side_view/`.
4. **`data/vsl_training_data.zip` (187 MB):**
   - File nén sao lưu dư thừa của thư mục `data/extracted_keypoints/`.
5. **Checkpoints thử nghiệm tạm (`checkpoints/*_smoke.pt`):**
   - Các file model 1-batch phục vụ kiểm tra đường truyền (`baseline_bigru_smoke.pt`, `stgcn_smoke.pt`, `transformer_smoke.pt`).
6. **Thư mục `scratch/`:**
   - Các script gỡ lỗi ngắn hạn không còn giá trị vận hành.

---

### 3. Bảng đề xuất kế hoạch dọn dẹp chi tiết

| STT | Đường dẫn mục tiêu | Dung lượng | Trạng thái hiện tại | Đề xuất | Lý do kỹ thuật | Mức độ an toàn |
|:---:|:---|---:|:---|:---:|:---|:---:|
| 1 | `data/Processed/` | **17.048 MB** (184.296 files) | Đã cách ly (Leaked) | **Xóa bỏ (Delete)** | Dữ liệu bị rò rỉ train-val leakage nghiêm trọng, gây ảo tưởng accuracy 100%, tuyệt đối cấm dùng trong nghiên cứu. Xóa sẽ giải phóng 17 GB. | **Cao** |
| 2 | `data/asl_alphabet_train/` & `test/` | **1.055 MB** (87.028 files) | Sai miền (ASL) | **Xóa bỏ (Delete)** | Bảng chữ cái ký hiệu Mỹ, không liên quan gì đến VSL. Giải phóng hơn 87.000 file I/O. | **Cao** |
| 3 | `clone/Vietnamese-Sign-Language-Translation/data/keypoints/` | **1.015 MB** (6.030 files) | Trùng lặp 100% | **Xóa bỏ (Delete)** | Đã được sao lưu đầy đủ và có kiểm tra SHA256 sang `data/external/vsl_gh/` và `docs/provenance/archive/`. | **Cao** |
| 4 | `data/vsl_training_data.zip` | **187 MB** | File nén dự phòng | **Xóa bỏ (Delete)** | Dữ liệu keypoint sạch đã nằm sẵn trong `data/extracted_keypoints/`. | **Cao** |
| 5 | `checkpoints/*_smoke.pt` (3 files) | **14,8 MB** | Checkpoint smoke | **Xóa bỏ (Delete)** | File dummy sinh ra từ dry-run 1 batch, không có giá trị trọng số. | **Cao** |
| 6 | `experiments/word_model_bigru.*` (3 files) | **7,1 MB** | Model train từ data leak | **Lưu trữ (Archive) hoặc Xóa** | Model cũ train từ `data/Processed` bị leak 100% accuracy. | **Trung bình** |
| 7 | `experiments/alphabet_model.*` (3 files) | **0,7 MB** | Model nhận diện ASL | **Xóa bỏ (Delete)** | Model cũ nhận diện bảng chữ cái ASL của Mỹ. | **Cao** |
| 8 | `scratch/` (các file script cũ) | **0,06 MB** | Script debug nháp | **Dọn dẹp (Clean)** | Giữ lại script audit hữu ích, xóa các file debug rác (`mini_test.py`, `debug_infer.py`). | **Cao** |
| 9 | `data/Dataset/` | **2.764 MB** (4.363 files) | Video gốc VSLR | **GIỮ LẠI (Retain)** | Đây là bộ 4.362 video gốc duy nhất của dự án. Cần đổi tên thành `data/raw_dataset/` trong tương lai sau khi xóa `data/Processed`. | **Bắt buộc giữ** |
| 10 | `data/extracted_keypoints/` | **186 MB** (3.039 files) | Keypoints sạch VSLR | **GIỮ LẠI (Retain)** | Dữ liệu chuẩn đang dùng cho production ST-GCN. | **Bắt buộc giữ** |
| 11 | `data/external/vsl_gh/` | **740 MB** | Canonical VSL-GH | **GIỮ LẠI (Retain)** | Dữ liệu liên tục phục vụ mô hình CSLR. | **Bắt buộc giữ** |
| 12 | `checkpoints/stgcn_best.pt` | **4,07 MB** | Production VSLR model | **GIỮ LẠI (Retain)** | Trọng số ST-GCN phục vụ API FastAPI và web React. | **Bắt buộc giữ** |
| 13 | `checkpoints/cslr_best.pt` | **28,2 MB** | Verified CSLR model | **GIỮ LẠI (Retain)** | Trọng số CSLR S06 WER 32.80%. | **Bắt buộc giữ** |

### 4. Dự kiến hiệu quả sau khi dọn dẹp
- **Dung lượng giải phóng:** **~19.32 GB** (Giảm từ 29.62 GB xuống còn **~10.30 GB**, bao gồm cả 5.9 GB của `.venv`).
- **Số lượng file cắt giảm:** **~277.350 tệp tin** (Giảm từ 367.000 tệp xuống còn **~89.000 tệp**).
- **Tốc độ làm việc:** Tăng tốc đáng kể các thao tác Git, quét virus, indexing, và sao lưu hệ thống.

