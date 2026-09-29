# Kế hoạch 07 — Việc 6: Bộ chọn chế độ (Đánh vần / Ký từ / Ký câu) + chế độ Ký câu (CSLR → gloss → ViT5)

**ĐANG LÀM** (planner đang viết; chưa dùng được)

- Nhánh lập kế hoạch: `cloud/2026-09-29-viec-a-d` (cloud). Ngày: 2026-09-29.
- Backlog: `docs/STATE.md` "Backlog còn lại" mục 3; `docs/prompts/autopilot.md` §2 mục 4.
- Nối tiếp kế hoạch 06 (`docs/plans/06-viec5-frontend.md`, đang làm dở ở local: còn B6–B9).

## 1. Mục tiêu và DoD phục vụ

**Mục tiêu.** (a) Giao diện có MỘT bộ chọn chế độ bằng nút — "Đánh vần (Cấp 1)", "Ký từ (Cấp 2)", "Ký câu (Cấp 3)" — thay
cho cách chọn tab hiện tại, mỗi chế độ chỉ hiện kết quả thật từ server. (b) Thêm chế độ "Ký câu": clip/bộ đệm landmark →
CSLR (ST-GCN+BiGRU, CTC) → gloss → ViT5 → câu tiếng Việt; khi có gloss ngoài từ vựng ViT5 hoặc độ tin cậy thấp thì hiện
gloss thô kèm cảnh báo; nếu không chạy realtime thì giao diện ghi rõ "chế độ offline". (c) TRƯỚC khi đo bất kỳ số nào trên
S06, kiểm và công bố ViT5 đã học những câu/cặp gloss nào của S06 (chồng lấn train ViT5 ↔ S06), với tiêu chí đăng ký trước.

**DoD phục vụ.**
- DoD 4 (Ký câu) — phần chính của việc này.
- DoD 6 (người dùng chọn chế độ bằng nút; không kết quả giả ở mọi chế độ) — phần còn lại sau kế hoạch 06.
- DoD 3 (Ký từ) — CHỈ phần tích hợp đường live WS v2 (đã làm ở kế hoạch 04/06) vào bộ chọn chế độ. Model mặc định KHÔNG
  đổi; đổi model là GATE riêng (backlog 5).
- DoD 7 (một phần): contract test cho endpoint Ký câu, test tương đương train↔suy luận cho đầu vào CSLR, e2e Ký câu trên
  clip mẫu thật (ở local), guard frontend mở rộng cho component mới.
- DoD 9 (một phần): mục "Giới hạn" cho Cấp 3 (rò rỉ câu ViT5, S06 là 1 người ký, dữ liệu VSL-GH là keypoint không có video
  cục bộ, số liệu nào KHÔNG được dùng) — sinh từ JSON.

## 2. Hiện trạng (đọc ở HEAD của nhánh cloud, tách từ feat/vslt-complete sau 34a527d)

### 2.1 S06 là gì (trích nguồn)
- S06 = tập TEST của VSL-GH, chia theo NGƯỜI KÝ: train S01–S04 × 3 lần lặp = 3.600 mẫu, val S05 × 1 = 300, test S06 × 1 =
  300 (`docs/vsl_gh_dataset.md:121-125`; `docs/data_registry.md:70-71`). Mỗi người ký ký CÙNG 300 câu SENT001–SENT300
  (`docs/data_registry.md:58`: "300 unique sentences × 14 repetitions across 6 signers").
- Dataset lọc theo trường `split` trong `dataset_canonical.json` (`src/data/vsl_gh_dataset.py:399-420`); CSLR train/val/test
  = split `train`/`val`/`test`, `conversion_mode="semantic"`, `normalize=True` (`src/training/train_cslr.py:359-384`).
- Bằng chứng S06 có 300 mẫu: `reports/cslr_s06_predictions.json` có 300 khóa `sample_id` (đếm bằng Grep), dạng
  `SENT###_S06_R01_F`; file này KHÔNG có `generated_by`/commit (script `scripts/extract_cslr_predictions.py:102-104` ghi
  thẳng, không ghi lệnh/commit).
- Nguồn: repo GitHub `nguyentheanh822/Vietnamese-Sign-Language-Translation` commit `6c351e6…`, MIT
  (`docs/vsl_gh_dataset.md:9-12`). Chỉ có keypoint `.npy` [T, 411] (137 điểm MediaPipe Holistic), KHÔNG có video gốc
  (`docs/audit/PHASE4_AUDIT.md:98-112`: tác giả gitignore `data/videos/`). Trích trên Linux, Holistic `model_complexity=1,
  smooth_landmarks=True, 0.5/0.5` (`docs/audit/PHASE4_AUDIT.md:115-117`), phiên bản MediaPipe và độ phân giải: không ghi.

### 2.2 ViT5 đã học gì (theo mã; SỐ chồng lấn phải sinh bằng lệnh ở C1)
- **Stage 2** (mô hình mặc định `checkpoints/vit5_stage2/best_model`, `src/translation/translator.py:29-30,59-64`) fine-tune
  trên cặp (gloss_sequence → translation) của VSL-GH chia theo `sentence_id`: train SENT001–SENT240, val SENT241–SENT270
  (chọn epoch theo val loss), "test" SENT271–SENT300 (`src/translation/dataset.py:63-116`, đặc biệt `:94-101`;
  `scripts/train_translation_stage2.py:71-72,167-173`). Cặp của mỗi câu lấy từ mẫu ĐẦU TIÊN gặp trong json
  (`src/translation/dataset.py:82-90`) — chưa kiểm các lần lặp của cùng câu có cùng gloss/translation không.
  → Mặc định 240/300 câu của S06 (cả gloss lẫn câu đích) nằm trong train ViT5 và 30 câu nữa nằm trong val (dùng để chọn
  epoch). Chỉ SENT271–SENT300 không vào stage 2.
- **Stage 1**: `Clean10kDataset` trên `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl`, chia 90/10 bằng
  `random.Random(42).shuffle` (`src/translation/dataset.py:18-49`; `scripts/train_translation_stage1.py:60-61`;
  `reports/vit5_stage1_history.json`: train 6426, val 714). Cột `vsl` của bộ 10k là văn bản sinh bằng luật cú pháp
  (PCFG), không phải gloss tự nhiên (`docs/audit/PHASE4_AUDIT.md:83-92`).
- **Bằng chứng chồng lấn đã có (không đủ):** `reports/vslgh_translation_overlap.json` so 300 câu VSL-GH với **9.405 cặp**
  (bộ CHƯA làm sạch `vie_vsl_10k.jsonl`, không phải file train 7.140 cặp, không tách train/val của stage 1): khớp sau chuẩn
  hóa 5 nguồn / 9 đích / 5 cặp; danh sách mẫu gồm SENT036, 089, 101, 103, 112, 113, 141, 147, 150. JSON không có
  `generated_by`, không có lệnh/commit, không tìm được script sinh ra nó (Grep tên file trong `*.py` không có kết quả) →
  KHÔNG dùng làm số liệu chính thức; C1 sinh lại.
- **CSLR** (`checkpoints/cslr_best.pt`) train trên S01–S04 cho CẢ 300 câu → mọi câu của S06 (kể cả SENT271–300) đã được CSLR
  thấy (qua người ký khác); S06 chỉ "chưa thấy người ký", không "chưa thấy câu".
- **Khẳng định cũ vượt bằng chứng:** `scripts/evaluate_translation_phase4b.py:12` ghi SENT271–SENT300 là "100% leak-free",
  README `:56-60` ghi "30 câu unseen" — cả hai bỏ qua stage 1 và CSLR. S06 đã được chạy nhiều lần trong lịch sử
  (`reports/cslr_test_results.json`, `cslr_s06_predictions.json`, `translation_phase4b_benchmark.json`,
  `audit_round2/run_v2_cslr_bootstrap.py`, `audit_round2/cslr_streaming_simulation.json`) → quy tắc "TEST chỉ chạy một
  lần" đã bị vi phạm TRƯỚC kế hoạch này; mọi số S06 mới chỉ là đo lại, không được dùng để chọn gì.
- Cấu hình giải mã lệch: benchmark `scripts/evaluate_translation_phase4b.py:58-64` KHÔNG có `no_repeat_ngram_size`, còn
  đường sản phẩm `src/translation/translator.py:135-143` có `no_repeat_ngram_size=2`. Số README đo bằng cấu hình khác cấu
  hình người dùng thấy.
- Dữ liệu "tổng hợp/tái dựng" (skill `vsl-data-integrity`): `reports/vsl_gh_synthesized_annotations.json` — 2 mẫu có nhãn
  do dự án tự viết (`SENT236_S01_R03_F`, `SENT285_S04_R03_F`, `annotation_source: reconstructed`), đều thuộc split train
  CSLR (`docs/data_registry.md:75`), không thuộc S06. SENT236 ≤ 240 (nằm trong train stage 2 nếu mẫu tái dựng là mẫu "đầu
  tiên" của câu đó — C1 phải kiểm). Bộ 10k: cột `vsl` sinh bằng luật (ở trên). Không phát hiện dữ liệu tổng hợp MỚI.

### 2.3 Đường suy luận Cấp 3 hiện có (lệch với train)
- `src/translation/cslr_recognizer.py:80-144` `CSLRRecognizer.predict`: nhận [T,67,3], KHÔNG chuẩn hóa vai (train dùng
  `normalize=True`, `src/data/vsl_gh_dataset.py:447-458`), dựng model không truyền `channel_dims/temporal_downsample`
  (mặc định trùng train: `src/models/cslr_stgcn_bigru.py:54-55,67-68`), greedy CTC, KHÔNG trả độ tin cậy.
  `docs/audit/PHASE4_AUDIT.md:181` ghi (văn bản, không có JSON) WER S06 đổi từ 32.80% sang 77.38% khi `normalize=False` —
  chỉ là chỉ dấu; C2 phải kiểm bằng test.
- `src/translation/end_to_end.py:126-172` `translate_keypoints`: đổi 137→67 nếu [T,411], rồi gọi `predict` (không chuẩn
  hóa). `translate_video` (`:174-206`) dùng `CleanHolisticExtractor` (bố cục QIPEDC: khớp 9/10 = miệng của Pose, 21/22 =
  ngón cái của Pose; NaN khi thiếu, `src/data/landmark_extractor.py:72-98`) — KHÁC bố cục semantic của VSL-GH (9/10 =
  FaceMesh 61/291, 21/22 = đầu ngón cái của bàn tay, `docs/vsl_gh_dataset.md:43-57`) và đưa NaN vào model
  (`src/models/cslr_stgcn_bigru.py:156-157` nhân mask, NaN·0 = NaN). Không có test nào cho hai đường này ngoài
  `tests/test_translation_core.py:72-95` (keypoint ngẫu nhiên, chỉ kiểm giao diện — không được sửa).
- `scripts/simulate_cslr_streaming.py:116-121` gọi `recognizer.predict` trên keypoint không chuẩn hóa, không mask → số
  "Full-clip WER 81.28%" trong `reports/audit_round2/cslr_streaming_simulation.json` và README `:61` đo trên đường lệch train.
- Backend: `GET /` (`backend/main.py:462-475`), `POST /api/translate` (`:864-888`: gloss → ViT5, lỗi → 500 kèm `str(e)`),
  `get_or_load_translator()` (`:212-222`: nạp CSLR + ViT5 + LexiconBank cùng lúc). CHƯA có endpoint nhận clip/keypoint
  cho Ký câu. Đường legacy Ký từ gọi ViT5 trên chuỗi từ QIPEDC khi CONFIRMED và kiểm OOV bằng
  `translator.gloss_vocab` (`:1114-1133`) — `VSLEndToEndTranslator` không có thuộc tính này, nên `oov_warning` không bao
  giờ được tạo. Khóa `translated_text`, `oov_warning` là một phần hợp đồng legacy (`tests/test_ws_live_contract.py:37`) →
  giữ nguyên, chỉ không hiển thị.

### 2.4 Frontend (sau kế hoạch 06 B5; B6 đang làm ở local)
- `frontend/src/App.jsx:9,53-56`: `activeTab` mặc định `'realtime'` → `Phase12Pipeline` (Ký từ); `'alphabet'` →
  `Fingerspelling`; `'dictionary'`, `'reports'`. `frontend/src/components/Navbar.jsx:8-13`: 4 tab. Không có chế độ Ký câu,
  không có nút chọn chế độ đúng nghĩa DoD 6 (kế hoạch 06 §3.9 để cho Việc 6).
- Kế hoạch 06 đã/đang làm: `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` + `frontend/tests/*.test.mjs`
  (`npm test`), `Phase12Pipeline.jsx` WS v2 (B5, xong), `Fingerspelling.jsx` (B6, chưa commit), guard
  `tests/test_frontend_contract.py` (AC8 kế hoạch 06), e2e `scripts/e2e_{browser.cjs,fullstack.py}` (B8, chưa có).
- `RealtimeStream.jsx` là mã chết (kế hoạch 06 §3.4) và là nơi duy nhất đọc `translated_text`/`oov_warning`.

### 2.5 Dữ liệu/checkpoint cần cho việc này (đều KHÔNG có trên cloud)
| Thứ cần | Đường dẫn | Có trong git? | Lấy ở đâu |
|---|---|---|---|
| Metadata VSL-GH | `data/external/vsl_gh/dataset_canonical.json`, `gloss_vocab_canonical.txt` | Không | Máy local (sinh bằng `scripts/prepare_canonical_vsl_gh.py` từ bản clone upstream) |
| Keypoint VSL-GH | `data/external/vsl_gh/keypoints_frontal/*.npy` (4.200) | Không | Máy local |
| Ngữ liệu 10k | `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl` (+ `vie_vsl_10k.jsonl`) | Không | Máy local |
| CSLR | `checkpoints/cslr_best.pt` | Không (`.gitignore:62`) | CHỈ máy local — không có trong 2 dataset private (Grep 2 manifest: 0 kết quả) |
| ViT5 | `checkpoints/vit5_stage{1,2}/best_model/` | Không | CHỈ máy local — như trên |
| Video webcam giả | clip QIPEDC/hauuto (đã có ở local, kế hoạch 06 §3.7) | Không | Máy local |
→ Mọi bước chạy mô hình/dữ liệu (C1–C6, C10) làm ở LOCAL. Cloud chỉ làm được bước thuần mã không cần dữ liệu (viết test
logic với fixture, JS lib) — xem §4.

## 3. Thiết kế
(đang viết)

## 4. Chia việc
(đang viết)

## 5. Tiêu chí chấp nhận (hợp đồng)
(đang viết)

## 6. Rủi ro dữ liệu/ML
(đang viết)

## 7. Điểm dừng
(đang viết)
