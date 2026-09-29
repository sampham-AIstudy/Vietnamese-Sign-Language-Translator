# Kế hoạch 07 — Việc 6: Bộ chọn chế độ (Đánh vần / Ký từ / Ký câu) + chế độ Ký câu (CSLR → gloss → ViT5)

**Trạng thái: XONG (chờ orchestrator)**

- **Điểm dừng bắt buộc trước khi code: KHÔNG.** Có 2 câu hỏi cho người dùng KHÔNG chặn bước nào (§7.2, đã có mặc định) và
  các điểm dừng có điều kiện trong lúc làm (§7.3; mục 1 và 6 có thể cần người dùng).
- Nhánh lập kế hoạch: `cloud/2026-09-29-viec-a-d` (cloud). Ngày: 2026-09-29.
- Backlog: `docs/STATE.md` "Backlog còn lại" mục 3; `docs/prompts/autopilot.md` §2 mục 4.
- Nối tiếp kế hoạch 06 (`docs/plans/06-viec5-frontend.md`, đang làm dở ở local: còn B6–B9). MỌI bước của kế hoạch này chỉ
  bắt đầu SAU KHI kế hoạch 06 được APPROVE (§4).

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
  Script trích gốc: `clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py` (chỉ có ở máy local, `clone/`
  không track).

### 2.2 ViT5 đã học gì (theo mã; SỐ chồng lấn phải sinh bằng lệnh ở C1)
- **Stage 2** (mô hình mặc định `checkpoints/vit5_stage2/best_model`, `src/translation/translator.py:29-30,59-64`) fine-tune
  trên cặp (gloss_sequence → translation) của VSL-GH chia theo `sentence_id`: train SENT001–SENT240, val SENT241–SENT270
  (chọn epoch theo val loss), "test" SENT271–SENT300 (`src/translation/dataset.py:63-116`, đặc biệt `:94-101`;
  `scripts/train_translation_stage2.py:71-72,167-173`). Cặp của mỗi câu lấy từ mẫu ĐẦU TIÊN gặp trong json
  (`src/translation/dataset.py:82-90`) — chưa kiểm các lần lặp của cùng câu có cùng gloss/translation không.
  → Theo mã, 240/300 câu của S06 (cả gloss lẫn câu đích) nằm trong train ViT5 và 30 câu nữa nằm trong val (dùng để chọn
  epoch). Chỉ SENT271–SENT300 không vào stage 2. `VSLTranslator` tự LẶNG LẼ lùi về stage 1 nếu thiếu stage 2
  (`src/translation/translator.py:59-64`).
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
- **Khẳng định cũ vượt bằng chứng:** `scripts/evaluate_translation_phase4b.py:12` ghi SENT271–SENT300 là "100% leak-free";
  `reports/PHASE4B_REPORT.md:112` ghi "Zero Leakage cả về Signer lẫn Sentence"; README `:56-60` và
  `reports/audit_round2/VERIFY.md:14,42` ghi "30 câu unseen" — tất cả bỏ qua stage 1 và việc CSLR đã học mọi câu.
  S06 đã được chạy nhiều lần trong lịch sử (`reports/cslr_test_results.json`, `cslr_s06_predictions.json`,
  `translation_phase4b_benchmark.json`, `audit_round2/run_v2_cslr_bootstrap.py`, `audit_round2/cslr_streaming_simulation.json`)
  → quy tắc "TEST chỉ chạy một lần" đã bị vi phạm TRƯỚC kế hoạch này; mọi số S06 mới chỉ là đo lại, không được dùng để chọn gì.
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
  chỉ là chỉ dấu; C2/C4 kiểm bằng test.
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
- Helper WS dùng lại được (kế hoạch 04/06): `_short` (`backend/main.py:149`), `_ws_check_origin` (`:1337`),
  `_parse_ws_message`, `_decode_frame`, `_ws_error`, `THREAD_POOL`; mẫu endpoint tuần tự `/ws/hand-landmarks` (`:1576+`).
- Kế hoạch 06 AC11 (`docs/plans/06-viec5-frontend.md:513-518`) có test buộc `docs/phase12_api.md` chứa MỌI mã lỗi mà
  `backend/main.py` phát ra (trích bằng regex) và mọi `type` message của các WS → thêm mã/type mới ở backend mà không cập
  nhật `docs/phase12_api.md` sẽ làm vỡ test có sẵn đó.

### 2.4 Frontend (sau kế hoạch 06 B5; B6 đang làm ở local)
- `frontend/src/App.jsx:9,53-56`: `activeTab` mặc định `'realtime'` → `Phase12Pipeline` (Ký từ); `'alphabet'` →
  `Fingerspelling`; `'dictionary'`, `'reports'`. `frontend/src/components/Navbar.jsx:8-13`: 4 tab. Không có chế độ Ký câu,
  không có nút chọn chế độ đúng nghĩa DoD 6 (kế hoạch 06 §3.9 để cho Việc 6).
- Kế hoạch 06 đã/đang làm: `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` + `frontend/tests/*.test.mjs`
  (`npm test`), `Phase12Pipeline.jsx` WS v2 (B5, xong), `Fingerspelling.jsx` (B6, chưa commit), guard
  `tests/test_frontend_contract.py` (AC8 kế hoạch 06), e2e `scripts/e2e_{browser.cjs,fullstack.py}` (B8, chưa có).
- `RealtimeStream.jsx` là mã chết (kế hoạch 06 §3.4) và là nơi duy nhất đọc `translated_text`/`oov_warning` (Grep
  `frontend/src` ở HEAD cloud).

### 2.5 Dữ liệu/checkpoint cần cho việc này (đều KHÔNG có trên cloud)
| Thứ cần | Đường dẫn | Có trong git? | Lấy ở đâu |
|---|---|---|---|
| Metadata VSL-GH | `data/external/vsl_gh/dataset_canonical.json`, `gloss_vocab_canonical.txt` | Không | Máy local (sinh bằng `scripts/prepare_canonical_vsl_gh.py` từ bản clone upstream) |
| Keypoint VSL-GH | `data/external/vsl_gh/keypoints_frontal/*.npy` (4.200) | Không | Máy local |
| Ngữ liệu 10k | `data/external/parallel_text/vie_vsl_10k_cleaned.jsonl` (+ `vie_vsl_10k.jsonl`) | Không | Máy local |
| CSLR | `checkpoints/cslr_best.pt` | Không (`.gitignore:62`) | CHỈ máy local — không có trong 2 dataset private (Grep 2 manifest: 0 kết quả) |
| ViT5 | `checkpoints/vit5_stage{1,2}/best_model/` | Không | CHỈ máy local — như trên |
| Script trích gốc VSL-GH | `clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py` | Không | Máy local |
| Video webcam giả | clip QIPEDC TRAIN (đã có ở local, kế hoạch 06 §3.7) | Không | Máy local |

→ Mọi bước cần dữ liệu/checkpoint (C0–C2, phần thật của C3, C4–C8, C11, C12) làm ở LOCAL. Làm được trên cloud: phần
fixture của C3, C9, C10 (build) — xem §4. CLOUD.md §3 không có nguồn nào cho dữ liệu Cấp 3 trên cloud.

## 3. Thiết kế

### 3.0 Quyết định chính
- **D1 — Ký câu là chế độ OFFLINE.** CSLR là BiGRU hai chiều + CTC, train trên trọn câu; chưa có bằng chứng chạy cuốn chiếu
  được (mô phỏng cũ đo trên đường lệch train, §2.3). Người dùng ghi TRỌN câu (Ghi → Dừng) hoặc chọn clip mẫu; server chạy
  một lần trên cả clip. Giao diện luôn hiện nhãn "Chế độ offline" khi ở Ký câu. Không làm streaming CSLR trong việc này.
- **D2 — Hai nguồn vào, MỘT lõi.** (i) "Clip mẫu": keypoint thật của VSL-GH S06 đọc từ đĩa server (đúng miền dữ liệu model
  đã học, có nhãn để đối chiếu); (ii) "Webcam — thử nghiệm": frame → server trích landmark theo bố cục 137 điểm của VSL-GH
  → bộ đệm phía server → hết câu thì chạy lõi. Cả hai đi qua CÙNG hàm `SentencePipeline.run_137`.
- **D3 — Tiền xử lý dùng chung, bằng hệt train.** Hàm mới `preprocess_vslgh_137` tái hiện đúng bước 2–4 của
  `VSLGHContinuousDataset.__getitem__` (`src/data/vsl_gh_dataset.py:441-458`), chứng minh bằng test `np.array_equal` trên
  `.npy` thật. KHÔNG sửa `src/data/**`, `src/training/**`, `src/models/**` (checkpoint đã train bằng mã hiện tại). KHÔNG sửa
  `CSLRRecognizer`/`VSLEndToEndTranslator` (đường cũ lệch train, không được endpoint mới dùng; ghi vào Giới hạn + backlog dọn).
- **D4 — Không có mô hình/ngưỡng thay thế lặng lẽ.** Lõi truyền ĐÍCH DANH `checkpoints/vit5_stage2/best_model` (không dùng
  lùi về stage 1); thiếu CSLR/ViT5/dữ liệu/ngưỡng → báo "không sẵn sàng" với mã lỗi, không có giá trị mặc định. Model mặc
  định mọi cấp không đổi (CSLR/ViT5 là đúng các đường mặc định đang có trong mã).
- **D5 — Ngưỡng độ tin cậy chọn bằng VAL (S05), OOV theo kho gloss ViT5 thật sự đã học.** Cả hai được cố định trong JSON
  đã commit TRƯỚC khi chạy S06.
- **D6 — Bộ chọn chế độ:** chế độ ban đầu = CHƯA chọn (không mở camera, không mở WS cho tới khi người dùng bấm một nút).
  Đổi chế độ = tháo component cũ (đóng WS, dừng camera) rồi mới gắn component mới.
- **D7 — Ký từ không đổi backend:** chế độ Ký từ gắn `Phase12Pipeline` (kế hoạch 06) nguyên trạng; model mặc định giữ
  nguyên; `VSL_MODEL_TYPE=stgcn_h360` chỉ dùng trong e2e như kế hoạch 06.

### 3.1 Luồng dữ liệu
```
[Nút chế độ] ─ Đánh vần → Fingerspelling.jsx (kế hoạch 06, không đổi)
             ─ Ký từ    → Phase12Pipeline.jsx (kế hoạch 06, không đổi) → /ws/live-stream v2
             ─ Ký câu   → SentenceMode.jsx  (nhãn "Chế độ offline")
                 ├─ Clip mẫu:  GET /api/sentence/samples → chọn → POST /api/sentence/sample {sample_id}
                 │               server: đọc .npy [T,411] ─┐
                 └─ Webcam:    WS /ws/sentence-landmarks: reset → frame… (sentence_frame) → finish
                                 server: Holistic (bố cục 137 VSL-GH) → bộ đệm [T,411] ─┤
                                                                                       ▼
            SentencePipeline.run_137(raw[T,411], source)
              preprocess_vslgh_137 (semantic 137→67 + chuẩn hóa vai + mask)   ← dùng chung, = dataset train
              → STGCNBiGRU_CSLR (joint_masks, lengths) → log_probs
              → greedy CTC + độ tin cậy từng gloss (ctc_greedy_with_confidence; token = ctc_greedy_decode)
              → cờ OOV (kho gloss stage-2 train, từ JSON C1) + cờ tin cậy thấp (τ từ JSON C5)
              → VSLTranslator(stage2, cấu hình sản phẩm).translate(glosses)   (không gọi nếu 0 gloss)
              → SentenceResult {glosses[], translation, display, warnings[], …}
```

### 3.2 C1 — Kiểm "ViT5 đã học câu nào" (ĐĂNG KÝ TRƯỚC, chạy trước mọi lần suy luận trên S06)
Script mới `scripts/vit5_s06_overlap.py --out reports/vit5_s06_overlap_<YYYY-MM-DD>/overlap.json` (chỉ đọc văn bản, không
nạp model). Tập train/val lấy bằng cách IMPORT đúng lớp đã dùng để train (không viết lại logic chia):
`Clean10kDataset(split="train"|"val", val_ratio=0.1, seed=42)` và `VSLGHTextDataset(split="train"|"val"|"test")`.
- **Kiểm nhất quán với lần train (điều kiện dừng):** `len(Clean10k train/val)` phải bằng `train_samples`/`val_samples` đọc
  từ `reports/vit5_stage1_history.json`; `len(VSLGHText train/val)` phải bằng `reports/vit5_stage2_history.json`. Lệch → dữ
  liệu đã đổi sau khi train → DỪNG (§7.3-1).
- **Chuẩn hóa so khớp** (đúng hàm train dùng): nguồn `normalize_vsl_source`, đích `normalize_vietnamese_target`.
  - L1 = bằng nhau sau chuẩn hóa train.
  - L2 = L1 + chữ thường + bỏ mọi ký tự `.,!?;:"'()[]{}…` + gộp khoảng trắng.
  - Gần trùng = Jaccard tập từ (sau L2) ≥ 0.8 VÀ chênh số từ ≤ 1 (ngưỡng đăng ký trước, chỉ để LOẠI khỏi tập sạch).
- **Mỗi mẫu S06 (300)** ghi: `sample_id`, `sentence_id`, `vit5_stage2_split` ∈ {train, val, heldout};
  `stage2_pair_identical` (cặp ViT5 đã học cho `sentence_id` đó == cặp của mẫu S06 sau chuẩn hóa L1);
  `stage2_pair_source_sample` + `stage2_pair_reconstructed` (mẫu nào cung cấp cặp, có phải nhãn tái dựng);
  `stage1_{train,val}_{src,tgt,pair}_L1`, `…_L2` (bool) + `stage1_match_ids` (chỉ ID `PAR_10K_…`, không chép văn bản 10k);
  `stage1_max_jaccard_{src,tgt}` + cờ `stage1_near_duplicate`; `cslr_train_occurrences` (số mẫu train CSLR cùng
  `sentence_id`), `n_distinct_pairs_across_repetitions` (trên cả 14 lần lặp).
- **Tập con ĐĂNG KÝ TRƯỚC** (định nghĩa cố định trong script, tên cố định):
  - `S06_all` — cả 300.
  - `S06_vit5_train` — `vit5_stage2_split == train`; `S06_vit5_val` — `== val`; `S06_vit5_heldout` — `== heldout`.
  - `S06_vit5_clean` — `heldout` VÀ không khớp L1/L2 (nguồn, đích hoặc cặp) với stage 1 train ∪ val VÀ không gần trùng.
    Đây là tập DUY NHẤT được gọi là "câu ViT5 chưa học". KHÔNG tập nào được gọi là "câu hệ thống chưa thấy" (CSLR đã học
    mọi câu).
- **Kho gloss cho cờ OOV:** `vit5_stage2_train_glosses` = tập gloss thô (đúng chuỗi trong `raw_glosses`) của các cặp
  `VSLGHTextDataset(split="train")`, sắp xếp; kèm `cslr_glosses_not_in_vit5_stage2_train` (gloss CSLR có thể xuất mà ViT5
  chưa học ở stage 2 → luôn bị cờ OOV).
- `summary`: số mẫu mỗi tập con, số câu có nhiều biến thể cặp, số mẫu S06 có `stage2_pair_identical == false`.
- `generated_by{command, git_commit, code_dirty, generated_at_utc, input_sha256{dataset_canonical, vie_vsl_10k_cleaned,
  vit5_stage1_history, vit5_stage2_history}}`. JSON chỉ chứa văn bản VSL-GH (MIT) + ID của 10k; không chứa keypoint.
- File cũ `reports/vslgh_translation_overlap.json` GIỮ NGUYÊN (không xóa/sửa); `docs/sentence_mode.md` ghi nó bị thay
  thế bởi JSON C1 và vì sao.

### 3.3 C2/C3 — Tiền xử lý dùng chung, giải mã có độ tin cậy, căn chỉnh
- `src/translation/cslr_preprocess.py`: `preprocess_vslgh_137(raw: ndarray[T,411], conversion_mode="semantic",
  normalize=True) -> (kps float32[T,67,3], joint_mask float32[T,67])`. Gọi `convert_137_to_67` (import từ
  `src/data/vsl_gh_dataset.py`, không chép); mask và chuẩn hóa vai là bản sao nguyên văn `:444-458`; KHÔNG có
  velocity/subsample/truncation (train không dùng: `src/training/train_cslr.py:359-366`). File mới không tự `import torch`
  (module `vsl_gh_dataset` có thể kéo torch — chấp nhận). Kiểm đầu vào: 2 chiều, cột 411, hữu hạn, T ≥ 1 → `ValueError` có mã.
- `src/translation/sentence_scoring.py`:
  - `ctc_greedy_with_confidence(log_probs_btc, lengths, blank_id) -> List[List[(token_id, confidence)]]`. Token phải BẰNG
    `ctc_greedy_decode` (`src/metrics/cslr_metrics.py:16-75`). **Độ tin cậy (đăng ký trước):** với mỗi token phát ra, lấy
    đoạn frame liên tiếp có argmax = token đó (đoạn đã sinh ra token sau khi gộp lặp); `confidence = mean(exp(log_probs[t,
    token]))` trên đoạn đó. Độ tin cậy câu = min các token (0 token → `None`). Test kiểm `exp(log_probs).sum(-1) ≈ 1` trên
    output thật (khẳng định đầu ra là log_softmax).
  - `align_hypothesis(ref, hyp) -> List[label]`, label ∈ {correct, substitution, insertion} cho từng token hyp, truy vết
    bảng Levenshtein với CÙNG luật hòa của `levenshtein_distance` (`src/metrics/cslr_metrics.py:106-166`: `min` trên thứ tự
    sub, del, ins). Số S/I phải bằng `levenshtein_distance`.
- Không sửa `src/metrics/cslr_metrics.py` (chỉ import).

### 3.4 C4 — `src/translation/sentence_pipeline.py`
```
class SentenceUnavailable(Exception): code ∈ {model_unavailable, data_unavailable, calibration_missing}
class SentencePipeline:
    __init__(cslr_ckpt="checkpoints/cslr_best.pt", vocab="data/external/vsl_gh/gloss_vocab_canonical.txt",
             vit5="checkpoints/vit5_stage2/best_model", threshold_json=<JSON C5>, overlap_json=<JSON C1>,
             device=None, require_calibration=True)
    recognize_137(raw) -> {"tokens": [(gloss, conf)], "num_frames", "timing_ms"}      # chỉ CSLR (C5 dùng)
    run_137(raw, source: "sample"|"webcam", fps=None, extra_warnings=()) -> SentenceResult
    info() -> {"cslr_sha256", "vit5_path"(tương đối), "vit5_config", "tau", "tau_source", "oov_inventory_source", "device"}
```
- Dựng CSLR đúng như `scripts/extract_cslr_predictions.py:48-60` (in_channels 3, 67 khớp, num_classes = len(vocab),
  hidden 256, 2 tầng GRU; `eval()`), nạp `model_state_dict`; tính sha256 checkpoint lúc nạp. Forward với `joint_masks` +
  `sequence_lengths` (batch 1), không autocast trên CPU. ViT5: `VSLTranslator(model_path=<stage2 đích danh>, device=…)`, cấu
  hình mặc định của lớp (num_beams 4, max_length 64, `no_repeat_ngram_size=2` trong `translate`) — gọi `translate`, không tự
  gọi `generate`.
- Thiếu file/nạp lỗi → `SentenceUnavailable` (thông điệp cố định, không chứa đường dẫn). `require_calibration=True` mà
  thiếu JSON C5 → `calibration_missing` (không có τ mặc định). Thiếu JSON C1 → `data_unavailable` (không có kho OOV mặc định).
  Đầu vào: T < `SENTENCE_MIN_FRAMES` → `clip_too_short`; T > `SENTENCE_MAX_FRAMES` → `clip_too_long` (`ValueError` có mã).
  Hằng thiết kế (ghi chú "giá trị thiết kế, chưa đo"): `SENTENCE_MIN_FRAMES = 16`, `SENTENCE_MAX_FRAMES = 600` (20 s ở
  30 fps); test buộc [min, max] BAO TRỌN độ dài của mọi mẫu VSL-GH (đọc từ dữ liệu) — không clip thật nào bị từ chối.
- **SentenceResult** (dùng chung REST + WS):
```
{"type": "sentence_result", "mode": "offline", "source": "sample"|"webcam", "num_frames": int, "fps": float|null,
 "glosses": [{"gloss": str, "confidence": float (4 số lẻ), "oov": bool, "low_confidence": bool}],
 "gloss_str": str, "sentence_confidence": float|null,
 "translation": str|null,                         # null khi 0 gloss (ViT5 không được gọi)
 "display": "translation"|"raw_gloss"|"empty",
 "warnings": [{"code": "oov_gloss"|"low_confidence"|"no_gloss"|"unverified_input_domain"|"fps_out_of_range",
               "glosses": [str], "message": str (tiếng Việt)}],
 "thresholds": {"tau": float, "tau_source": str, "oov_inventory_source": str},
 "models": {"cslr_sha256": str, "vit5": "vit5_stage2/best_model", "vit5_config": {...}},
 "timing_ms": {"preprocess", "cslr", "vit5", "total"},
 "reference": {...}}                              # CHỈ khi source=sample, xem 3.7
```
- **Luật hiển thị (đăng ký trước):** `oov` ⇔ gloss == `<unk>` hoặc gloss ∉ `vit5_stage2_train_glosses`; `low_confidence`
  ⇔ confidence < τ (so trên giá trị chưa làm tròn). `display = "empty"` nếu 0 gloss (cảnh báo `no_gloss`); `"raw_gloss"`
  nếu có ≥ 1 gloss `oov` hoặc `low_confidence`; ngược lại `"translation"`. Khi `raw_gloss`, `translation` VẪN được tính và
  trả về (để đo), nhưng giao diện KHÔNG hiện nó như kết quả (3.9). Webcam luôn có cảnh báo `unverified_input_domain`;
  `fps_out_of_range` khi fps hiệu dụng ngoài [min, max] trường `fps` của các mẫu VSL-GH train (đọc từ dữ liệu lúc nạp).

### 3.5 C5 — Chọn τ trên VAL (S05), ĐĂNG KÝ TRƯỚC
`scripts/sentence_calibrate.py --split val --device cpu --out reports/sentence_calibration_<YYYY-MM-DD>/threshold.json`:
- Chạy `recognize_137` (pipeline `require_calibration=False`) trên cả 300 mẫu split `val` (script assert mọi
  `signer_id == "S05"`), gán nhãn token bằng `align_hypothesis` với `gloss_sequence`. Dương tính = token sai (substitution
  hoặc insertion).
- Lưới τ ∈ {0.00, 0.01, …, 1.00}; cờ = confidence < τ; chọn τ làm cực đại J = TPR − FPR; hòa → τ nhỏ nhất. Không lớp nào
  được rỗng (0 token đúng hoặc 0 token sai → DỪNG, §7.3-4).
- Ghi: `tau`, luật (chuỗi mô tả), toàn bộ điểm ROC `{tau, tpr, fpr, j}`, `n_tokens`, `n_incorrect`, `n_samples`,
  `split: "val"`, `sample_ids_sha256` (sha256 của danh sách `sample_id` đã sắp xếp, nối bằng `\n`), `cslr_sha256`, phân
  bố `display` trên VAL (chỉ báo cáo, dùng kho OOV của C1), `generated_by{command, git_commit, code_dirty: false}`.
- Không chạm S06. τ không được đổi sau C6 (sửa τ = kế hoạch mới, planner ghi lý do; không bao giờ dựa trên S06).

### 3.6 C6 — Đo trên S06 (ĐĂNG KÝ TRƯỚC, chạy đúng 1 lần để sinh JSON chính thức)
Điều kiện trước (script tự assert, sai → thoát mã khác 0, không ghi file): JSON C1 và C5 đã commit, không bị sửa so với
HEAD (`git status --porcelain` rỗng cho hai file), `code_dirty == false`; ghi sha256 của hai file vào output.
`scripts/evaluate_sentence_s06.py --device cpu --out reports/sentence_s06_<YYYY-MM-DD>/eval.json`:
- Chạy `run_137` (đúng lõi sản phẩm) trên 300 mẫu `split == "test"` (assert `signer_id == "S06"`). Kiểm chéo trong script:
  token của lõi == token của đường dataset (`VSLGHContinuousDataset(split="test", normalize=True)` + cùng model, batch 1)
  cho MỌI mẫu; lệch 1 mẫu → thoát lỗi, không ghi JSON (§7.3-5). Ghi `pipeline_equals_dataset_path: true`, `n_checked`.
- Cho mỗi tập con của C1 (`S06_all`, `S06_vit5_train`, `S06_vit5_val`, `S06_vit5_heldout`, `S06_vit5_clean`): `n`; CSLR
  WER (`compute_wer`, S/D/I); dịch từ gloss CSLR (mode B) và từ gloss nhãn (mode A, oracle) bằng CÙNG `VSLTranslator` cấu
  hình sản phẩm, chấm `compute_translation_metrics` (`src/translation/metrics.py:16`); phân bố `display`; mode B chỉ trên
  mẫu `display == "translation"` (kèm `n`); CI 95% bootstrap theo mẫu (1000 lần, `np.random.default_rng(0)`, percentile)
  cho WER và BLEU. `n < 10` → vẫn ghi số đếm, CI ghi `null` và `ci_note: "n<10"`.
- Mỗi mẫu: `sample_id`, gloss nhãn, gloss dự đoán + confidence, `display`, câu mode A, câu mode B, câu nhãn (văn bản VSL-GH).
- `note` (nguyên văn cố định trong script): "S06 was evaluated several times before this plan; these numbers are a
  re-measurement with the production pipeline, not a first held-out test, and were not used to choose anything. The CSLR
  model was trained on all 300 sentences (other signers). Only S06_vit5_clean may be described as sentences unseen by ViT5."
- Không ngưỡng pass/fail; không đổi gì sau khi xem số.

### 3.7 C7 — REST Ký câu (`backend/main.py`)
- Loader riêng `get_or_load_sentence_pipeline()` (singleton), KHÔNG dùng `get_or_load_translator` (không nạp LexiconBank,
  không dùng đường lùi stage 1). Chỉ cache khi nạp THÀNH CÔNG; lỗi không được cache (lần gọi sau nạp lại), để sửa file xong
  không phải khởi động lại backend.
- `GET /api/sentence/status` → 200 `{"available": bool, "reason": null|"model_unavailable"|"data_unavailable"|
  "calibration_missing", "mode": "offline", "realtime": false, "sources": {"sample": bool, "webcam": bool},
  "limits": {"min_frames", "max_frames"}, "thresholds": {...}|null, "models": {...}|null}`.
- `GET /api/sentence/samples` → 200 `{"samples": [{"sample_id", "sentence_id", "tags": {"split": "test", "signer": "S06",
  "vit5_stage2": "train"|"val"|"heldout", "vit5_clean": bool, "stage1_match": bool, "cslr_seen_sentence": bool}}]}` (thứ tự
  theo `sample_id`; tag đọc từ JSON C1, không tính lại); 503 `data_unavailable`.
- `POST /api/sentence/sample` body `{"sample_id": str (≤ 64 ký tự)}` → 200 SentenceResult (`source: "sample"`, `fps` = trường
  `fps` của mẫu) + `reference: {"sample_id", "sentence_id", "signer_id", "gloss": [...], "translation": str, "tags": {...}}`.
  404 `{"detail": {"error": "unknown_sample"}}` nếu không phải mẫu split `test` của S06 có trong `dataset_canonical.json`;
  422 body sai; 503 `{"status": "model_unavailable"|"data_unavailable"|"calibration_missing", "detail": <thông điệp cố
  định>}` — `detail` không chứa đường dẫn, tên file, `str(exception)`.
- Suy luận chạy trong `THREAD_POOL` (không chặn event loop). Thêm `"sentence": "/api/sentence/status"` vào dict `GET /`.
- KHÔNG đụng: `MODEL_TYPE`, `STGCN_VARIANTS`, `get_or_load_predictor`, `_active_model`, `get_or_load_translator`,
  `/api/translate`, `/ws/live-stream`, `/ws/hand-landmarks`, middleware, CORS, `BODY_LIMITED_PATHS`.

### 3.8 C8 — Webcam: extractor 137 điểm + `WS /ws/sentence-landmarks` (protocol_version 1)
- `src/inference/sentence_live.py` (không import torch/fastapi): `VSLGH_HOLISTIC_KWARGS`, `VSLGH_POSE_INDICES` (25),
  `VSLGH_FACE_INDICES` (70), thứ tự khối pose→face→tay trái→tay phải, quy ước thiếu = 0 — TẤT CẢ chép từ script trích gốc
  `clone/.../source/extract_keypoints.py` (MIT) và test đối chiếu bằng `ast` (AC10-a). Nếu script gốc có resize/lật/đổi màu
  thì làm y hệt; không tự thêm bước nào. `class Vslgh137Session`: `reset()` (graph Holistic mới), `process(frame_bgr) ->
  (vec float32[411], hands {"left": bool, "right": bool}, pose: bool)`, `close()`; và hàm offline
  `extract_vslgh137_from_video(path) -> ndarray[T,411]` dùng CHÍNH `Vslgh137Session`.
- Endpoint `websocket_sentence_landmarks`: `_ws_check_origin` TRƯỚC `accept` (sai → 1008, không nạp gì) → `session_info`
  `{"type":"session_info","endpoint":"sentence-landmarks","protocol_version":1,"mode":"offline","extractor":{"name":
  "mp.solutions.holistic","layout":"vslgh_137","mediapipe_version",…kwargs},"limits":{"max_message_bytes","max_frame_side",
  "min_frames","max_frames"}}` → vòng nhận TUẦN TỰ (như `/ws/hand-landmarks`; dùng lại `_parse_ws_message`,
  `_decode_frame(raw, min_height=None)`, `_ws_error`, `THREAD_POOL`).
  - control `reset` → `reset_done{clip_id}` (graph mới, bộ đệm rỗng, `clip_id` +1; phiên mở với `clip_id` 0).
  - frame → `sentence_frame{clip_id, frame_seq, received_seq, client_timestamp, hands, pose, buffer_fill, metrics{decode_ms,
    extract_ms}}` (KHÔNG gửi landmark về client). Quá `max_frames` → `error{clip_too_long}` (không đóng phiên, frame không
    vào bộ đệm).
  - control `finish` → nếu `buffer_fill < min_frames` → `error{clip_too_short}`; nếu 0 frame có tay → `error{no_hands}` và
    KHÔNG chạy model; ngược lại chạy `run_137(buffer, "webcam", fps)` trong `THREAD_POOL` → `sentence_result` (có
    `unverified_input_domain`; fps hiệu dụng tính từ `client_timestamp`, không có → `null`). Sau `finish` bộ đệm giữ nguyên
    tới `reset`.
  - Mã lỗi: `message_too_large` (1009), `bad_message`, `bad_config`, `bad_timestamp`, `decode_failed`,
    `unsupported_format`, `frame_too_large`, `clip_too_short`, `clip_too_long`, `no_hands`, `model_unavailable` (1011),
    `data_unavailable`/`calibration_missing` (1011). Lỗi một message không đóng phiên (trừ mã có số đóng). Backend định
    nghĩa tuple `SENTENCE_WS_ERROR_CODES` (dùng cho test tài liệu, AC15).
- `docs/phase12_api.md`: THÊM mục "WS /ws/sentence-landmarks" (các `type` mới `sentence_frame`, `sentence_result`, mã lỗi
  mới) + trỏ tới `docs/sentence_mode.md` — bắt buộc để test AC11 của kế hoạch 06 (§2.3) vẫn xanh; không sửa phần đã có.

### 3.9 C9–C10 — Frontend
- `frontend/src/lib/modes.js`: `MODES` = [{id:"fingerspell", label:"Đánh vần (Cấp 1)"}, {id:"word", label:"Ký từ (Cấp 2)"},
  {id:"sentence", label:"Ký câu (Cấp 3)"}] đúng thứ tự; `INITIAL_MODE = null`; `selectMode(current, clicked)` thuần.
- `frontend/src/lib/sentence.js`: `OFFLINE_LABEL` (chứa "Chế độ offline"); `sentenceView(result)` →
  `{headline, glossLine, showTranslation, warnings[{code, text}]}` với luật: `translation` → headline = `translation`,
  `showTranslation` true; `raw_gloss` → headline = `gloss_str`, `showTranslation` false, cảnh báo tiếng Việt cho từng mã;
  `empty` → headline "Không nhận ra gloss nào", không câu. Không bao giờ tự ghép câu tiếng Việt từ gloss. `reduceSentenceWs
  (state, msg)` thuần cho các `type` của 3.8 (type lạ → đếm `unknownMessages`). Hằng thiết kế `SENT_TARGET_FPS = 30`,
  `SENT_JPEG_QUALITY = 0.9`, `SENT_MAX_IN_FLIGHT = 2` (ghi "giá trị thiết kế, chưa đo"). Không có τ hay ngưỡng nào ở JS.
- `frontend/src/components/ModeSelector.jsx`: 3 nút `data-testid` `mode-fingerspell`, `mode-word`, `mode-sentence`,
  `aria-pressed`. `frontend/src/App.jsx`: tab `translate` ("Dịch ký hiệu") chứa ModeSelector + component của chế độ đã
  chọn (`mode == null` → chỉ có dòng hướng dẫn `data-testid="mode-none"`); bỏ 2 tab `realtime`, `alphabet`; giữ
  `dictionary`, `reports`. `Navbar.jsx`: chỉ sửa mảng `navItems` (và dòng import icon nếu cần).
- `frontend/src/components/SentenceMode.jsx`: gọi status (không sẵn sàng → khóa nút, hiện `reason` tiếng Việt); luôn hiện
  `OFFLINE_LABEL` (`sentence-offline`); khung "Clip mẫu VSL-GH (người ký S06)" (select + nút dịch; hiện tag: "ViT5 đã học
  câu này" / "ViT5 chưa học (sạch)" / "CSLR đã học câu này qua người ký khác"); khung "Webcam — thử nghiệm" (Ghi/Dừng);
  kết quả theo `sentenceView`; "Nhãn gốc" hiện TÁCH BIỆT với kết quả, có tiêu đề riêng. `data-testid`: `sentence-status`,
  `sentence-offline`, `sentence-sample-select`, `sentence-sample-run`, `sentence-tags`, `sentence-record`, `sentence-stop`,
  `sentence-frames`, `sentence-headline`, `sentence-gloss`, `sentence-translation` (chỉ render khi `showTranslation`),
  `sentence-warnings`, `sentence-reference`, `sentence-error`.
- Chụp webcam cho Ký câu: dùng lại cơ chế chụp có giới hạn frame đang bay của B6 kế hoạch 06 (§3.2 của 06: canvas không
  lật, JPEG, `nowMs()`, tối đa N frame chưa được ack). Nếu B6 viết nó bên trong `Fingerspelling.jsx`, C10 được tách ra
  `frontend/src/lib/capture.js` và sửa `Fingerspelling.jsx` CHỈ để gọi hàm đã tách (e2e `fingerspell_default` ở AC14 chạy
  lại chứng minh hành vi không đổi). Không viết bản chụp thứ hai.
- Ký từ: `Phase12Pipeline` gắn nguyên trạng; không hiện `translated_text`/`oov_warning` ở bất kỳ component nào còn dùng.

### 3.10 Ngoài phạm vi (reviewer không tính là thiếu)
- Streaming/realtime CSLR, train lại CSLR (kể cả chia theo câu), train lại ViT5; sửa/xóa `CSLRRecognizer`,
  `VSLEndToEndTranslator`, `scripts/simulate_cslr_streaming.py` (đưa vào backlog dọn dẹp); đổi model mặc định Cấp 2 (GATE);
  từ điển; đo độ trễ DoD 8 cho Ký câu (có `timing_ms` để đo sau); `Reports.jsx`/badge số cứng trong Navbar (DoD 9, backlog 7);
  sửa báo cáo lịch sử (`PHASE4B_REPORT.md`, `VERIFY.md`, `AUDIT_ROUND2.md`) — chỉ ghi chú ở README + `docs/sentence_mode.md`.

## 4. Chia việc

**Quy ước chung**
- **Phụ thuộc kế hoạch 06:** MỌI bước (kể cả C0) chỉ bắt đầu sau khi kế hoạch 06 APPROVE (review 06 = APPROVE và dòng
  progress_log của 06 đã commit). Lý do: C7/C8 sửa `backend/main.py` và `docs/phase12_api.md` (06 B7 đang viết lại file
  này); C10 sửa `App.jsx`/`Navbar.jsx` (06 AC1 cấm 06 đổi `App.jsx`, 06 B5 đã sửa `Navbar.jsx`); C10 dùng lại cách chụp
  của 06 B6; C11 sửa `scripts/e2e_*.{cjs,py}` do 06 B8 tạo; AC2 cần mốc đã xanh của 06 (guard 06 chỉ xanh từ B7). Các bước
  dữ liệu (C1–C6) không đụng file của 06 nhưng vẫn đợi, để P7/AC1/AC2 đo trên một nền cố định và không có hai coder cùng
  commit vào một nhánh. Không trùng việc với 06: 06 giữ nguyên B6–B9 (UI Đánh vần, smoke + phase12_api, e2e 3 kịch bản,
  đóng việc); 07 chỉ THÊM.
- `P7` = HEAD lúc coder bắt đầu C0 (đã có kế hoạch này + APPROVE của 06); ghi vào `docs/plans/07-progress.md`.
- Bước làm được trên cloud (phần fixture của C3, C9, C10) chỉ sau P7, trên nhánh tách từ P7; orchestrator merge bằng merge
  commit (không rebase, không amend).
- Trước khi sửa symbol có sẵn: GitNexus `impact <symbol> --direction upstream` (`risk: UNKNOWN` → text search). Trước MỖI
  commit: `detect-changes --scope all`, ghi risk thật vào commit message. Không `git add -A`/`git add .`. Không amend.
- Viết test trước hoặc cùng lúc. Mỗi bước: 1 commit + 1 đoạn trong `docs/plans/07-progress.md` (lệnh + output thật rút gọn
  + hash). Thư mục tạm ngoài repo: `../_plan07_tmp/`.
- **Không chạy mô hình trên S06 trước C6.** Test C2–C5 chỉ dùng split `train` và `val` (S05). Sau C6, S06 chỉ được dùng
  cho: test hợp đồng C7 (2 mẫu), e2e C11 (1 mẫu), demo giao diện — không sinh thêm số nào.
- Python: local `PYTHONIOENCODING=utf-8 .venv/Scripts/python`; cloud `.venv/bin/python`.

| Bước | Nội dung | Phụ thuộc | Nơi | Ước lượng |
|---|---|---|---|---|
| **C0** | Mốc: `git status --porcelain` → `../_plan07_tmp/c0_status.txt`; lệnh AC2 của kế hoạch 06 (29 module) → số test theo module; chạy thêm `tests.data.test_vsl_gh_dataset` (ghi kết quả; chỉ đưa vào AC2 nếu xanh ở P7); `cd frontend && npm test`, `node --version`, `npm ls --depth=0` → tmp; sha256 của `checkpoints/cslr_best.pt` và từng file trong `checkpoints/vit5_stage{1,2}/best_model/`; đếm `keypoints_frontal/*.npy`; có/không `clone/.../source/extract_keypoints.py`; `mediapipe.__version__`; `impact` cho `root`, `App`, `Navbar`, hàm chính của `scripts/e2e_browser.cjs`/`e2e_fullstack.py`. Tạo `07-progress.md`. Commit. | 06 APPROVE | local | 0.5 h |
| **C1** | Kiểm chồng lấn (3.2): `tests/test_vit5_s06_overlap.py` trước → `scripts/vit5_s06_overlap.py` → commit mã (sạch) → sinh JSON ở HEAD sạch → chạy lại lần 2 vào tmp (thân giống hệt) → commit JSON. Kiểm điều kiện dừng §7.3-1, -2. | C0 | local | 2 h |
| **C2** | `src/translation/cslr_preprocess.py` + `tests/test_cslr_preprocess_equivalence.py` (AC4). | C0 | local | 1.5 h |
| **C3** | `src/translation/sentence_scoring.py` + `tests/test_sentence_scoring.py` (AC5): phần fixture (cloud được) + phần dữ liệu thật trên VAL (local). | C0 (phần thật: C2) | cloud + local | 1.5 h |
| **C4a** | `SentencePipeline` phần CSLR (`recognize_137`, sha256, giới hạn T, `SentenceUnavailable`) + `tests/test_sentence_pipeline.py` AC6-a, e, g. | C2, C3 | local | 2 h |
| **C4b** | Phần ViT5 + cờ OOV/τ + `SentenceResult` + AC6-b, c, d, f, h. | C4a, C1 | local | 1.5 h |
| **C5** | `tests/test_sentence_calibration.py` (logic) trước → `scripts/sentence_calibrate.py` → commit mã → JSON ở HEAD sạch → commit (AC7). | C4b | local | 1 h |
| **C6** | `tests/test_sentence_eval_report.py` + `scripts/evaluate_sentence_s06.py` → commit mã → chạy ĐÚNG 1 lần ở HEAD sạch → commit JSON (AC8). | C1, C5 | local | 1.5 h |
| **C7** | REST (3.7) + `tests/test_sentence_api.py` (AC9); ghi RAM (và VRAM nếu CUDA) sau khi nạp pipeline vào 07-progress (chỉ ghi nhận). | C6 | local | 2 h |
| **C8a** | `src/inference/sentence_live.py` + `tests/test_sentence_live.py` AC10-a, c, d. Thiếu script gốc → DỪNG C8 (§7.3-6), làm tiếp C9–C10. | C4b | local | 1.5 h |
| **C8b** | WS `/ws/sentence-landmarks` + `tests/test_sentence_ws.py` (AC11) + AC10-b; thêm mục WS mới vào `docs/phase12_api.md`. | C7, C8a | local | 2 h |
| **C9** | `frontend/src/lib/{modes,sentence}.js` + `frontend/tests/{modes,sentence}.test.mjs` + `tests/test_frontend_modes.py` (AC12). Được đỏ có chủ đích tới C10 theo đúng luật 06 §0.3 (chỉ `tests.test_frontend_modes`, vi phạm chỉ ở `App.jsx`/`Navbar.jsx`, không tăng; message ghi "guard đỏ có chủ đích, còn N vi phạm"). | P7 | cloud được | 1.5 h |
| **C10** | `ModeSelector.jsx`, `SentenceMode.jsx`, (tùy chọn) `lib/capture.js`, sửa `App.jsx`, `navItems` của `Navbar.jsx`; `npm run build` (AC13); guard xanh. | C9 (+ C7, C8b để xem thử ở local) | cloud (build) / local | 2 h |
| **C11** | E2E: sửa `scripts/e2e_browser.cjs`, `scripts/e2e_fullstack.py` (vào chế độ bằng nút `mode-*`; thêm kịch bản) → chạy 7 kịch bản AC14 ở HEAD sạch → commit 7 JSON vào `reports/e2e_07_<ngày>/` (thư mục riêng, không ghi đè JSON e2e của 06). | C7, C8b, C10 | local (Edge) | 2 h |
| **C12** | `docs/sentence_mode.md` + ghi chú README + `tests/test_sentence_docs.py` (AC15); AC2 đầy đủ + `npm test` + build; so `git status` với C0; THÊM 1 dòng progress_log (AC16); ghi backlog đề xuất (§6 cuối). Orchestrator gọi vslt-reviewer. | C1–C11 | local | 1.5 h |

Tổng ước lượng ≈ 23.5 giờ; GPU 0 giờ (mọi lần chạy đo dùng CPU), không Kaggle, không cài gói.
**Chặng giao gợi ý:** 1 = C0–C3; 2 = C4a–C6 (dữ liệu/đo, local); 3 = C7–C8b (backend, local); 4 = C9–C10 (frontend, giao
cloud được); 5 = C11–C12 (e2e + đóng việc, local).

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG được đổi; chỉ planner đổi và phải ghi lý do)

Lệnh Python chạy từ gốc repo với `PYTHONIOENCODING=utf-8 .venv/Scripts/python` (local). "Mới" = file/lớp test do kế hoạch
này thêm. Test mới không cần mạng, không ghi file trong repo (chỉ thư mục tạm), và KHÔNG skip trên máy local (được
`skipUnless` cho clone sạch/cloud, lý do nêu rõ file thiếu). Mọi số trong các tiêu chí dưới đây được test ĐỌC từ dữ liệu
hoặc JSON, không gõ tay.

**AC1 — Phạm vi thay đổi.** `git diff --name-status P7 HEAD` chỉ chứa:
- Mới (A): `src/translation/{cslr_preprocess,sentence_scoring,sentence_pipeline}.py`, `src/inference/sentence_live.py`;
  `scripts/{vit5_s06_overlap,sentence_calibrate,evaluate_sentence_s06}.py`;
  `tests/{test_vit5_s06_overlap,test_cslr_preprocess_equivalence,test_sentence_scoring,test_sentence_pipeline,
  test_sentence_calibration,test_sentence_eval_report,test_sentence_api,test_sentence_live,test_sentence_ws,
  test_frontend_modes,test_sentence_docs}.py`;
  `frontend/src/lib/{modes,sentence}.js`, (tùy chọn) `frontend/src/lib/capture.js`, `frontend/tests/{modes,sentence}.test.mjs`,
  `frontend/src/components/{ModeSelector,SentenceMode}.jsx`;
  `reports/vit5_s06_overlap_<ngày>/overlap.json`, `reports/sentence_calibration_<ngày>/threshold.json`,
  `reports/sentence_s06_<ngày>/eval.json`, `reports/e2e_07_<ngày>/{mode_initial,fingerspell_default,word_default,
  word_stgcn_h360,sentence_sample,sentence_webcam,mode_switch}.json`; `docs/sentence_mode.md`, `docs/plans/07-progress.md`.
- Sửa (M): `backend/main.py`; `frontend/src/App.jsx`; `frontend/src/components/Navbar.jsx` (chỉ `navItems` + dòng import
  icon); `frontend/src/components/Fingerspelling.jsx` (CHỈ khi tách hàm chụp sang `lib/capture.js`, diff chỉ là thay khối
  chụp bằng lời gọi); `frontend/src/components/{Phase12Pipeline,Fingerspelling}.jsx` thêm tối đa 10 dòng trong hàm dọn dẹp
  `useEffect` CHỈ khi e2e `mode_switch` chứng minh WS/camera không được giải phóng (ghi lý do + output e2e trước/sau);
  `scripts/e2e_browser.cjs`, `scripts/e2e_fullstack.py` (thêm điều hướng bằng nút và kịch bản mới; mọi assert cũ giữ nguyên);
  `docs/phase12_api.md`, `README.md`, `docs/progress_log.md` (cả ba CHỈ thêm dòng); `docs/plans/07-viec6-che-do.md` (chỉ planner).
- KHÔNG đổi: `src/data/**`, `src/training/**`, `src/models/**`, `src/metrics/**`,
  `src/translation/{__init__,translator,cslr_recognizer,end_to_end,dataset,text_normalizer,metrics}.py`, các file có sẵn
  trong `src/inference/`, `scripts/{train_*,prepare_*,evaluate_cslr_s06,extract_cslr_predictions,evaluate_translation_phase4b,
  simulate_cslr_streaming,smoke_test_phase12}.py`, `frontend/package.json`, `frontend/package-lock.json`,
  `frontend/src/components/{PredictionDisplay,CameraCapture,RealtimeStream,Dictionary,Reports}.jsx`, `frontend/src/lib/{ws,
  liveProtocol,fingerspelling}.js`, mọi test đã có ở P7, mọi file `reports/` đã có (kể cả JSON e2e của 06), `docs/reviews/*`,
  `configs/`, `checkpoints/`, `data/`, `clone/`. Không xóa file. 3 file ` D` của người dùng vẫn chưa staged. Không file
  `.pt/.npz/.npy/.mp4/.y4m/.png/.jpg/.log` nào vào git.

**AC2 — Không hồi quy.** Lệnh (29 module AC2 của kế hoạch 06 + module mới; thêm `tests.data.test_vsl_gh_dataset` nếu xanh ở C0):
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_vit5_s06_overlap tests.test_cslr_preprocess_equivalence tests.test_sentence_scoring tests.test_sentence_pipeline tests.test_sentence_calibration tests.test_sentence_eval_report tests.test_sentence_api tests.test_sentence_live tests.test_sentence_ws tests.test_frontend_modes tests.test_sentence_docs -v`
- Đóng việc (C11, C12): 0 failure, 0 error, 0 skip. Số test = số C0 + số test mới; báo theo module, trước → sau.
- Mốc trung gian: mỗi bước chạy các module đã tồn tại tới bước đó, 0 failure; ngoại lệ DUY NHẤT là guard của C9 theo luật
  ở bảng §4 (hết ở C10).
- `git diff P7 HEAD -- tests/` với mọi file test đã có ở P7: 0 dòng `-`.
- `git status --porcelain` trước và sau khi chạy giống hệt.
- `cd frontend && npm test` → 0 fail; số file test Node báo đã chạy == số dòng của `git ls-files "frontend/tests/*.test.mjs"`;
  ghi `node --version`.

**AC3 — Kiểm chồng lấn ViT5 ↔ S06 (C1).** Lệnh:
`.venv/Scripts/python scripts/vit5_s06_overlap.py --out reports/vit5_s06_overlap_<YYYY-MM-DD>/overlap.json`.
`tests/test_vit5_s06_overlap.py`:
- a. Logic (fixture trong thư mục tạm, docstring ghi rõ là fixture): cặp bằng nhau sau chuẩn hóa train → L1; chỉ khác hoa/
  thường/dấu câu → L1 false, L2 true; Jaccard ≥ 0.8 và chênh 1 từ → gần trùng; chênh 2 từ → không; `heldout` có bất kỳ
  khớp stage 1 nào → không vào `S06_vit5_clean`; mẫu `train`/`val` không bao giờ vào `clean`.
- b. `ast` của script: import `Clean10kDataset` và `VSLGHTextDataset` từ `src.translation.dataset`; KHÔNG có tên `random`,
  `shuffle`, `SENT240`/`SENT270` (không tự chia lại).
- c. Dữ liệu thật: gọi hàm chính của script vào thư mục tạm → JSON bỏ `generated_by` == JSON đã commit bỏ `generated_by`;
  độ dài train/val stage 1/2 == history JSON (đọc file); `summary.S06_all` == số mẫu `split == "test"` trong
  `dataset_canonical.json` và mỗi mẫu đó xuất hiện đúng 1 lần; `S06_vit5_train`/`val`/`heldout` rời nhau và hợp lại bằng
  `S06_all`; `S06_vit5_clean ⊆ S06_vit5_heldout`; mọi `sample_id` chứa `_S06_`.
- d. JSON không có khóa `keypoints`, `landmarks`, `coords`, `vsl`, `vi`; mọi phần tử `stage1_match_ids` khớp `^PAR_10K_\d{5}$`.
- e. `generated_by.code_dirty == false`; `input_sha256.dataset_canonical` == sha256 file cục bộ; reviewer kiểm
  `git_commit` là tổ tiên HEAD.

**AC4 — Tiền xử lý dùng chung == train (`tests/test_cslr_preprocess_equivalence.py`).**
- a. `ast` của `src/translation/cslr_preprocess.py`: không có `import torch`/`from torch`.
- b. Với MỌI mẫu split `val` và mọi mẫu split `train` có chỉ số (thứ tự của dataset) chia hết cho 10:
  `preprocess_vslgh_137(np.load(npy))` so với `VSLGHContinuousDataset(split=…, conversion_mode="semantic", normalize=True,
  vocabulary=VSLGlossVocabulary.from_file(vocab))[i]` → `np.array_equal` cho keypoints VÀ joint_mask. Test in số mẫu đã so
  và assert bằng số tính từ dataset.
- c. Danh sách mẫu của test không có id chứa `_S06_` (assert).
- d. Đầu vào sai (cột 410, có NaN, T = 0) → `ValueError` có mã.
- e. (07-progress, không phải test) Đột biến trong bộ nhớ `normalize=False` → test b FAIL (chứng minh test nhạy).

**AC5 — Giải mã có độ tin cậy + căn chỉnh (`tests/test_sentence_scoring.py`).**
- a. Fixture log_probs (dựng tay, docstring ghi rõ): toàn blank → `[]`; A A blank A → [A, A]; A B B → [A, B]; T = 1;
  `lengths` < T bỏ phần đuôi. Token == `ctc_greedy_decode`; confidence == trung bình tính tay (|Δ| ≤ 1e-7).
- b. Dữ liệu thật: 20 mẫu VAL đầu tiên (sắp theo `sample_id`), log_probs qua đường dataset: token ==
  `ctc_greedy_decode`; mọi confidence ∈ [0, 1]; |exp(log_probs).sum(-1) − 1| ≤ 1e-4 trên frame hợp lệ.
- c. `align_hypothesis`: trên fixture và trên cả 300 cặp (ref, hyp) VAL: số `substitution` == S, số `insertion` == I của
  `levenshtein_distance`; `len(labels) == len(hyp)`.

**AC6 — `SentencePipeline` (`tests/test_sentence_pipeline.py`).**
- a. Mọi mẫu VAL + mẫu train chỉ số chia hết cho 10: token của `recognize_137(np.load(npy))` == token đường dataset (cùng
  checkpoint, CPU, batch 1); max|Δlog_probs| ≤ 1e-5 trên bước hợp lệ. Không mẫu S06.
- b. `VSLTranslator` được dựng đúng 1 lần với `model_path` trỏ `checkpoints/vit5_stage2/best_model` (spy); vá cho thư mục
  stage 2 "không tồn tại" → `SentenceUnavailable("model_unavailable")` và không lời gọi `from_pretrained` nào có đường dẫn
  chứa `vit5_stage1` (spy).
- c. Luật (vá `recognize_137`): 0 token → `display == "empty"`, `translation is None`, `translate` không được gọi, có cảnh báo
  `no_gloss`; `<unk>` → `oov`; gloss ngoài kho → `oov`; confidence < τ → `low_confidence`; confidence == τ → không; mọi
  gloss ổn → `"translation"`; `raw_gloss` → `translation` là chuỗi và `translate` được gọi đúng 1 lần; `source="webcam"` →
  có `unverified_input_domain`; fps ngoài khoảng → `fps_out_of_range`, trong khoảng → không.
- d. Thiếu JSON C5 (`require_calibration=True`) → `calibration_missing`; thiếu JSON C1 → `data_unavailable`; cả hai ca
  không nạp ViT5.
- e. [`SENTENCE_MIN_FRAMES`, `SENTENCE_MAX_FRAMES`] chứa T của MỌI file `.npy` (đọc shape bằng `mmap_mode="r"`; số file ==
  số mẫu trong `dataset_canonical.json`); T ngoài khoảng → `ValueError` mã `clip_too_short`/`clip_too_long`.
- f. Tập khóa của kết quả đúng §3.4 (không có `reference`); `models.cslr_sha256` == sha256 file; không `message` nào chứa
  `/`, `\`, `checkpoints`.
- g. Subprocess `import src.translation.sentence_pipeline` → `'fastapi' in sys.modules` là False.
- h. (Chỉ ghi nhận) Nếu có CUDA: số mẫu VAL có token khác nhau giữa CPU và CUDA — in ra, ghi 07-progress, không ngưỡng.

**AC7 — Chọn τ trên VAL (C5).** Lệnh:
`.venv/Scripts/python scripts/sentence_calibrate.py --split val --device cpu --out reports/sentence_calibration_<YYYY-MM-DD>/threshold.json`.
`tests/test_sentence_calibration.py`:
- a. Hàm luật trên ROC fixture: chọn cực đại J; hòa → τ nhỏ nhất; lớp rỗng → lỗi.
- b. JSON: `tau` thuộc lưới (`round(tau*100)` nguyên, 0..100); `tau` == luật áp lên các điểm ROC đã lưu (test tính lại);
  `0 < n_incorrect < n_tokens`; `split == "val"`; `sample_ids_sha256` == sha256 danh sách id VAL đọc từ dữ liệu, mọi id chứa
  `_S05_`; chuỗi `_S06_` không xuất hiện ở đâu trong JSON; `cslr_sha256` == sha256 file; `code_dirty == false`.
- c. Reviewer chạy lại lệnh vào thư mục tạm → thân JSON (bỏ `generated_by`) giống hệt.

**AC8 — Đo S06 một lần (C6).** Lệnh (chạy 1 lần cho JSON chính thức):
`.venv/Scripts/python scripts/evaluate_sentence_s06.py --device cpu --out reports/sentence_s06_<YYYY-MM-DD>/eval.json`.
- a. (Reviewer, git) Đúng 1 commit thêm `reports/sentence_s06_*/eval.json` và file không bị sửa sau đó
  (`git log --format=%H -- <file>` có 1 dòng); commit thêm JSON C1 và commit thêm JSON C5 là tổ tiên của nó
  (`git merge-base --is-ancestor`); commit của script C6 có trước commit JSON.
- b. JSON: `inputs.overlap_sha256`/`inputs.threshold_sha256` == sha256 hai file đã commit; `note` đúng nguyên văn §3.6;
  `pipeline_equals_dataset_path is True` và `n_checked` == số mẫu `split == "test"` (đọc từ dữ liệu); `n` từng tập con ==
  `summary` của JSON C1; mọi `sample_id` chứa `_S06_`.
- c. `tests/test_sentence_eval_report.py` (không nạp model): tính lại WER từng tập con từ ref/hyp đã lưu bằng `compute_wer`
  == giá trị lưu (bằng hệt dict S/D/I/wer); tính lại `compute_translation_metrics` từ chuỗi đã lưu == giá trị lưu
  (|Δ| ≤ 1e-9); tổng phân bố `display` == `n`; không khóa nào chứa "accuracy"; CI là `null` ⇔ `n < 10`.
- d. Reviewer chạy lại (CPU) vào thư mục tạm → thân JSON giống hệt (bỏ `generated_by`, thời gian). Không giống → FAIL, báo planner.

**AC9 — REST Ký câu (`tests/test_sentence_api.py`).**
- a. Pipeline giả (vá loader): `/api/sentence/status` đủ khóa §3.7; `/samples` đúng thứ tự, tag == JSON C1 (test đọc);
  `/sample` → 200 đủ khóa + `reference`; id `SENT001_S05_R01_F`, `nope`, `../x` → 404 `unknown_sample`; id 65 ký tự hoặc
  thiếu `sample_id` → 422.
- b. Loader ném lỗi có thông điệp chứa `C:\x\checkpoints\cslr_best.pt` → 503, `status` ∈ {model_unavailable,
  data_unavailable, calibration_missing}, `detail` không chứa `\`, `/`, `.pt`, `.json`, `checkpoints` hay thông điệp gốc;
  `/status` → 200, `available: false`, `reason` đúng mã.
- c. Spy: `get_or_load_translator` và `get_or_load_predictor` KHÔNG được gọi bởi request `/api/sentence/*` nào.
- d. Lỗi nạp không bị cache: lần 1 lỗi (vá), bỏ vá → lần 2 thành công.
- e. Thật (local): mẫu đầu tiên (sắp xếp) của `S06_vit5_heldout` và của `S06_vit5_train` → 200; `glosses`, `translation`,
  `display` == `SentencePipeline.run_137` trên cùng `.npy` trong cùng tiến trình; `reference` == `dataset_canonical.json`;
  `tags` == JSON C1.
- f. `GET /` có `"sentence": "/api/sentence/status"`. Reviewer: `git diff P7 HEAD -- backend/main.py` không có dòng `-` nào
  chứa `MODEL_TYPE`, `STGCN_VARIANTS`, `ALPHABET_CKPT`, `def get_or_load_predictor`, `def get_or_load_translator`,
  `BODY_LIMITED_PATHS`, `allow_origins`.

**AC10 — Extractor 137 điểm (`tests/test_sentence_live.py`, MediaPipe thật).**
- a. `ast` của `clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py` → kwargs Holistic, danh sách chỉ số
  pose, danh sách chỉ số face, thứ tự khối == hằng trong `sentence_live.py`. Subprocess import `sentence_live` → không có
  `torch`, `fastapi` trong `sys.modules`. (Trên local PHẢI chạy; C0 đã ghi file có.)
- b. 2 clip đầu của `scripts/live_clip_sample.py` (seed 0, split TRAIN): `run_137(extract_vslgh137_from_video(v), "webcam",
  fps)` == `sentence_result` nhận qua WS (frame PNG, `reset` đầu clip, `finish` cuối) — bằng hệt `glosses` (gloss và
  confidence), `translation`, `display`, `num_frames`; cờ `hands`/`pose` từng frame bằng cờ của phiên offline.
- c. Frame đen 640×480 → vector toàn 0, `hands` cả hai false, `pose` false; output float32, shape (411,), hữu hạn.
- d. `preprocess_vslgh_137(extract(video))` cho joint_mask đúng luật `(|x|+|y|+|z|) > 1e-6` của dataset.

**AC11 — `WS /ws/sentence-landmarks` (`tests/test_sentence_ws.py`; MediaPipe thật; pipeline giả trừ khi ghi khác).**
- a. Origin ∈ {`http://evil.example`, `null`, `http://localhost:3001`, `http://localhost:3000.evil.example`,
  `HTTP://LOCALHOST:3000`} → `WebSocketDisconnect` mã 1008; `Vslgh137Session` và loader không được gọi.
- b. Message đầu `session_info` đủ khóa §3.8; `extractor.mediapipe_version == mediapipe.__version__`; `limits` == hằng.
- c. `reset` → `reset_done` với `clip_id` 1, 2, …; `frame_seq` về 0; spy constructor Holistic: số lần = 1 + số reset;
  graph cũ `close()` đúng 1 lần mỗi reset.
- d. Gửi liền 5 frame rồi mới đọc → đúng 5 `sentence_frame`, `frame_seq` 0..4, `received_seq` tăng ngặt, `client_timestamp`
  bằng hệt; không message nào có khóa `landmarks`/`keypoints`.
- e. `finish` với `min_frames − 1` frame → `clip_too_short`; `min_frames` frame đen → `no_hands`; hai ca pipeline không
  được gọi. Vá `max_frames` nhỏ (ví dụ 20) rồi gửi 21 frame → frame thứ 21 nhận `clip_too_long`, `buffer_fill` == 20.
- f. Text rác → `code` ∈ {bad_message, decode_failed, unsupported_format}; PNG khai 4000×10 → `frame_too_large` và
  `cv2.imdecode` không được gọi; `timestamp: "x"` → `bad_timestamp`; message > 1 MiB → `message_too_large` + đóng 1009;
  loader ném lỗi ở `finish` → `model_unavailable` + đóng 1011; lỗi không làm tăng `frame_seq`; lỗi không fatal không đóng phiên.
- g. Spy: `get_or_load_predictor`, `get_or_load_translator` không được gọi.
- h. `SENTENCE_WS_ERROR_CODES` ⊇ mọi chuỗi mã truyền vào `_ws_error(`/`WsError(` trong `websocket_sentence_landmarks` và
  hàm phụ của nó (trích bằng `inspect`/`ast`).

**AC12 — Thư viện JS + guard.**
- `frontend/tests/modes.test.mjs`: `MODES` đúng id/nhãn/thứ tự §3.9; `INITIAL_MODE === null`; `selectMode` thuần (deepFreeze).
- `frontend/tests/sentence.test.mjs`: `sentenceView` cho 3 giá trị `display`; `raw_gloss` kèm `translation` khác rỗng →
  `showTranslation === false` và `headline === gloss_str`; mọi mã cảnh báo ở §3.4 có câu tiếng Việt khác rỗng; mã lạ → câu
  chung (không bị bỏ); `OFFLINE_LABEL` chứa "Chế độ offline"; `reduceSentenceWs` cho `session_info`, `reset_done`,
  `sentence_frame`, `sentence_result`, `error`, type lạ (`unknownMessages` +1); state đầu vào deepFreeze không bị sửa.
- Guard của kế hoạch 06 (`TestFrontendSourceGuard` trong `tests/test_frontend_contract.py`, chạy trong AC2, không sửa) phải
  xanh với mọi file mới/sửa trong `frontend/src`.
- `tests/test_frontend_modes.py`: (i) `translated_text`, `oov_warning` không xuất hiện trong `frontend/src/**` trừ
  `components/RealtimeStream.jsx`; (ii) `App.jsx` không còn id tab `'realtime'`/`'alphabet'` và có import `ModeSelector`;
  (iii) `lib/sentence.js`, `components/SentenceMode.jsx` không khớp regex `/\b(tau|threshold)\w*\s*[:=]\s*[0-9.]/i`;
  (iv) tự kiểm: đưa chuỗi vi phạm mẫu vào từng luật (i)–(iii) → bị bắt.

**AC13 — Build, không thêm gói.** `cd frontend && npm run build` exit 0; `npm ls --depth=0` giống hệt file C0;
`git diff P7 HEAD -- frontend/package.json frontend/package-lock.json` rỗng.

**AC14 — E2E fullstack (local, Edge; C11).** Chạy ở HEAD sạch (`git status --porcelain -- backend src frontend scripts
tests` rỗng), 7 JSON trong `reports/e2e_07_<YYYY-MM-DD>/`. Chung cho cả 7: như phần "Chung" của AC12 kế hoạch 06 (health
200 trong 180 s; 0 console `error`/`pageerror`/`requestfailed`/HTTP ≥ 400; mọi URL WS bắt đầu `ws://localhost:3000/ws/`,
không `:8000`; không `POST /api/fingerspelling`; cổng 8000/3000 rảnh sau khi dừng; `generated_by` sạch; không đường dẫn
tuyệt đối, landmark, ảnh).
- `mode_initial`: tải trang, chờ 5 s không thao tác → 0 WS được tạo; 0 phần tử `<video>`; thấy `mode-fingerspell`,
  `mode-word`, `mode-sentence`, `mode-none`.
- `fingerspell_default`, `word_default`, `word_stgcn_h360`: vào chế độ bằng `mode-fingerspell`/`mode-word`; MỌI assert
  của kịch bản tương ứng ở AC12 kế hoạch 06 giữ nguyên và đạt.
- `sentence_sample`: bấm `mode-sentence`; `sentence-offline` hiện và chứa "Chế độ offline"; số mẫu trong select ==
  `summary.S06_all` của JSON C1; chọn id đầu tiên (sắp xếp) của `S06_vit5_heldout` (script đọc JSON C1); `POST
  /api/sentence/sample` 200; `sentence-headline` == `translation` (nếu `display == translation`) / == `gloss_str` (nếu
  `raw_gloss`) / == câu "Không nhận ra gloss nào" (nếu `empty`); `sentence-translation` tồn tại ⇔ `display == translation`;
  số mục trong `sentence-warnings` == `len(warnings)`; `sentence-reference` chứa câu nhãn; `sentence-tags` hiện. Response
  ghi dưới khóa `info_not_accuracy`.
- `sentence_webcam`: webcam giả = clip Ký từ của kế hoạch 06 §3.7 (QIPEDC TRAIN); bấm `mode-sentence` → `sentence-record`
  → chờ hết độ dài clip (đọc từ video) → `sentence-stop`; WS nhận `session_info`, `reset_done`, ≥ `min_frames`
  `sentence_frame`, rồi đúng 1 `sentence_result`, 0 `error`; `warnings` có `unverified_input_domain` và `sentence-warnings`
  hiện câu tương ứng. Kết quả ghi dưới `info_not_accuracy`. Không đạt → DỪNG, báo planner (§7.3-7), không chỉnh tham số.
- `mode_switch`: Ký từ (chờ `session_info`) → Ký câu → Đánh vần → Ký câu: khi rời Ký từ, socket `/ws/live-stream` đóng
  trong 2 s (CDP `Network.webSocketClosed`); ở mọi thời điểm ≤ 1 WS đang mở (tính từ sự kiện created/closed) và ≤ 1 `<video>`.

**AC15 — Tài liệu (`tests/test_sentence_docs.py`).**
- `docs/sentence_mode.md` chứa: mọi mã trong `SENTENCE_WS_ERROR_CODES`; `unknown_sample`, `model_unavailable`,
  `data_unavailable`, `calibration_missing`; mọi mã cảnh báo §3.4; các `type` `session_info`, `reset_done`,
  `sentence_frame`, `sentence_result`; đường dẫn 3 JSON (C1, C5, C6) kèm `generated_by.git_commit` của từng file; chữ
  "offline"; mục "Giới hạn" có đủ 9 ý (test kiểm bằng từ khóa cố định cho từng ý): (1) S06 là 1 người ký; (2) CSLR đã học
  cả 300 câu qua người ký khác; (3) chỉ `S06_vit5_clean` là "câu ViT5 chưa học"; (4) S06 đã được đo nhiều lần trước kế
  hoạch này; (5) τ chọn trên 1 người ký (S05); (6) đường webcam chưa kiểm chứng tương đương với dữ liệu train (không có
  video VSL-GH; extractor gốc chạy Linux, phiên bản không rõ); (7) ngữ liệu stage 1 sinh bằng luật; (8) số Cấp 3 cũ trong
  README / `PHASE4B_REPORT.md` / `cslr_streaming_simulation.json` đo bằng cấu hình giải mã khác hoặc đường không chuẩn hóa
  → không dùng; (9) `reports/vslgh_translation_overlap.json` được thay bằng JSON C1.
- Mọi số thập phân trong mục "Kết quả" và "Giới hạn" của `docs/sentence_mode.md` có mặt trong một trong 3 JSON (test đọc file).
- `git diff P7 HEAD -- docs/phase12_api.md README.md` có 0 dòng `-`; dòng thêm ở README không chứa chữ số nào ngoài bên
  trong đường dẫn `docs/…`/`reports/…`, và có nhắc `docs/sentence_mode.md`. Test AC11 của kế hoạch 06 vẫn xanh (trong AC2).

**AC16 — Quy trình.** Mỗi commit có output `impact`/`detect-changes` (risk thật) trong message; không amend; 3 file ` D` của
người dùng vẫn chưa staged; `docs/plans/07-progress.md` có output thật cho từng bước; `docs/progress_log.md` THÊM 1 dòng (không
sửa dòng cũ) nêu commit, số test trước → sau, 3 JSON C1/C5/C6 + 7 JSON e2e, câu trả lời của người dùng cho §7.2 (nếu có),
backlog đề xuất. Model mặc định không đổi: Cấp 2 (`test_a_default_is_unchanged` trong AC2 + AC9-f), Cấp 1 (AC9-f), Cấp 3
phục vụ đúng đường mặc định có sẵn (AC6-b). Kết luận vslt-reviewer = APPROVE.

## 6. Rủi ro dữ liệu/ML

**Rò rỉ / nhiễm test (quan trọng nhất cho số liệu Cấp 3).**
- ViT5 stage 2 học cặp của 240 câu S06 (gloss + câu đích) và chọn epoch trên 30 câu khác → mode A (oracle) trên các câu đó
  đo khả năng NHỚ, không phải dịch. Chỉ `S06_vit5_clean` được gọi "câu ViT5 chưa học"; cỡ tập này chưa biết (C1 sinh), theo
  mã tối đa là số câu heldout → CI rộng hoặc `null`.
- CSLR đã học MỌI câu S06 qua 4 người ký khác (3 lần lặp/người): BiGRU + CTC có thể học thứ tự gloss của câu → WER S06 là
  "người ký mới, câu đã biết", lạc quan so với câu mới thật. VSL-GH không có tập nào đo được "câu mới" cho CSLR (mọi người ký
  ký cùng 300 câu) → Giới hạn + câu hỏi Q1 (§7.2).
- Stage 1 (10k, sinh bằng luật): chồng lấn với S06 CHƯA được đo trên đúng file/split train (JSON cũ đo trên 9.405 cặp chưa
  làm sạch, không nguồn) → C1 đo lại, kể cả gần trùng.
- S06 đã bị đo nhiều lần trước đây; τ và luật OOV cố định trước C6 (VAL/JSON C1); C6 chạy 1 lần; không chọn gì theo S06.
- Mẫu S06 hiện trong UI (clip mẫu) chỉ để minh họa; tag trên UI nói rõ ViT5/CSLR đã học câu nào; không dùng UI để chỉnh gì.

**Lệch train–suy luận.**
- Đường clip mẫu: cùng `.npy` + tiền xử lý chứng minh bằng hệt (AC4) + cùng model/forward (AC6-a, kiểm chéo trong C6) →
  không lệch trong mã. CPU vs GPU fp16 (backend có thể chạy CUDA): chỉ ghi nhận (AC6-h); số chính thức đo trên CPU.
- **Đường webcam — lệch lớn và KHÔNG đo được:** VSL-GH quay phông xanh, camera/độ phân giải/fps không rõ, extractor chạy
  Linux, phiên bản MediaPipe không ghi; ta chạy mediapipe (bản trong `.venv`, ghi ở C0) trên Windows. Kế hoạch 06 đã đo lệch
  Linux↔Windows ở Cấp 1 là KHÁC 0 (`reports/fingerspell_live_2026-09-29/hand_live_check.json`, commit e58d025, trích ở 06 §0.4).
  Không có video VSL-GH → không thể kiểm extractor 137 điểm của ta so với `.npy` gốc; AC10-b chỉ chứng minh nhất quán NỘI BỘ
  (live == offline của chính ta). Người dùng tự cắt câu (Ghi/Dừng) nên đầu/cuối có thể dài hơn clip train; fps khác.
  → Luôn có cảnh báo `unverified_input_domain`; không báo độ chính xác webcam; e2e webcam dùng clip QIPEDC (một TỪ, không
  phải câu VSL-GH) chỉ chứng minh "chạy được".
- Bố cục: mẫu semantic chỉ dùng 2 điểm FaceMesh (61/291) cho khớp 9/10, nhưng extractor vẫn phải xuất đủ [T,411] đúng thứ
  tự gốc để `convert_137_to_67` chọn đúng điểm.
- Đường cũ `CSLRRecognizer`/`translate_keypoints`/`translate_video`/`simulate_cslr_streaming.py` lệch train (không chuẩn
  hóa; bố cục QIPEDC + NaN) — không dùng; ghi Giới hạn + backlog; số của chúng không được trích.

**Ngưỡng và OOV.**
- τ chọn trên S05 = 1 người ký, 300 câu, và S05 cũng là tập đã dùng chọn epoch CSLR → τ có thể lạc quan và không chuyển
  được sang người khác. Độ tin cậy CTC (trung bình softmax trên đoạn argmax) không phải xác suất đã hiệu chuẩn; chỉ dùng xếp hạng.
- Kho OOV = gloss của stage-2 train → gloss chỉ có ở SENT241–300 luôn bị cờ; trên `S06_vit5_heldout` nhiều câu sẽ ở
  `raw_gloss`. Đó là hành vi mong muốn (trung thực), không được nới luật sau khi thấy tỉ lệ.

**Cỡ mẫu.**
- S06: 300 mẫu, 1 người ký, mỗi câu 1 lần; bootstrap theo mẫu = theo câu; CI chỉ phản ánh biến thiên theo câu, không theo
  người ký (n người ký = 1). `S06_vit5_clean` có thể < 10 → CI `null`. E2E 1 clip/kịch bản chỉ chứng minh "chạy được".
- AC4/AC6-a (≈ 660 mẫu train+VAL) là kiểm tương đương CODE (tất định), không phải tỉ lệ.

**Nguồn gốc / giấy phép.**
- VSL-GH: MIT theo `docs/data_registry.md:56`; JSON C1/C6 chứa văn bản câu/gloss VSL-GH (được phép, ghi nguồn trong
  `docs/sentence_mode.md`); không commit keypoint.
- Bộ 10k: "Open access for research and educational purposes" (`docs/data_registry.md:90`), cột `vsl` sinh bằng luật; JSON
  chỉ chứa ID.
- 2 nhãn tái dựng (train CSLR): C1 ghi nếu một trong hai là nguồn cặp của ViT5.
- Checkpoint CSLR/ViT5 chỉ có trên đĩa local, không có bản lưu trữ → mất máy = không tái lập (Q2). sha256 ghi ở C0 và trong
  mọi JSON.

**Tài nguyên.** Backend có thể giữ 2 bản ViT5 (translator legacy của Ký từ + lõi Ký câu) → RAM/VRAM máy laptop; C7 ghi
nhận, không tối ưu ở đây. C6 chạy ViT5 beam 4 trên CPU cho 600 lần dịch (mode A + B) — thời gian chưa đo, chấp nhận.

**Trung thực UI (DoD 6).** Nhãn gốc tách biệt khỏi kết quả; câu dịch không hiện khi `raw_gloss`; "Chế độ offline" luôn
hiện; webcam gắn nhãn "thử nghiệm" + cảnh báo; mọi chữ kết quả lấy từ response server.

**Backlog đề xuất (C12 ghi vào progress_log, KHÔNG làm ở đây).**
1. Dọn đường Cấp 3 cũ lệch train (`CSLRRecognizer.predict`, `VSLEndToEndTranslator.translate_keypoints/translate_video`,
   `scripts/simulate_cslr_streaming.py`) — hỏi người dùng trước khi xóa.
2. `oov_warning` của đường legacy không bao giờ được tạo (`backend/main.py:1127`) — sửa hoặc bỏ cùng đổi hợp đồng legacy
   (cần planner, vì `tests/test_ws_live_contract.py:37` khóa tập khóa).
3. Lưu trữ private checkpoint Cấp 3 (nếu Q2 = có).
4. Train lại CSLR với tập chia theo câu (nếu Q1 = có) để có số "câu mới" thật.
5. Streaming CSLR chỉ sau khi có model nhân quả (`docs/cslr_streaming_design.md` §4); đo lại mô phỏng trên đường đã chuẩn hóa.
6. Đo độ trễ Ký câu (mở rộng DoD 8) từ `timing_ms`.

## 7. Điểm dừng

### 7.1 Trước khi code: KHÔNG có điểm dừng bắt buộc
- Đổi model mặc định: KHÔNG. Cấp 2 giữ nguyên (AC9-f, AC16); Cấp 1 không đụng; Cấp 3 dùng đúng đường mặc định đang có trong mã
  (`checkpoints/cslr_best.pt`, `checkpoints/vit5_stage2/best_model`) và BỎ đường lùi lặng lẽ sang stage 1 (D4).
- Cần dữ liệu người dùng cung cấp: KHÔNG (VSL-GH, bộ 10k, checkpoint, video QIPEDC, script trích gốc đều ở máy local).
  Ngoại lệ có điều kiện: §7.3-6.
- Đụng thay đổi chưa commit của người dùng / xóa file / hành động không hoàn tác: KHÔNG.
- GPU/Kaggle: 0.
- Vấn đề dữ liệu mới: phát hiện khi lập kế hoạch — (a) CSLR đã học mọi câu S06 trong khi README/`PHASE4B_REPORT.md`/`VERIFY.md`
  ghi "30 câu unseen / zero leakage"; (b) JSON chồng lấn cũ không có nguồn và đo trên bộ chưa làm sạch; (c) đường suy luận
  Cấp 3 cũ không chuẩn hóa. Đánh giá: KHÔNG đổi hướng kế hoạch — việc này vốn được giao để kiểm rò rỉ trước khi đo; (a) chỉ
  đổi cách GỌI TÊN số liệu (đã khóa vào AC8-b, AC15), (b) và (c) được thay/né bằng C1 và lõi mới. Vì vậy không kích hoạt
  điểm dừng bắt buộc; nhưng người dùng cần biết vì các số Cấp 3 đang có trong README bị nói quá → Q1.

### 7.2 Câu hỏi cho người dùng (KHÔNG chặn bước nào; kế hoạch chạy theo mặc định nếu chưa có trả lời)
- **Q1.** CSLR đã học cả 300 câu của S06 qua người ký khác, nên hiện KHÔNG có số Cấp 3 nào đo "câu mới" cho cả hệ thống;
  README (`:56-60`) và `reports/PHASE4B_REPORT.md:112` đang ghi "30 câu unseen / zero leakage". **Mặc định:** giữ CSLR hiện
  tại, gọi đúng tên ("người ký chưa gặp, câu CSLR đã học"), thêm ghi chú ở README trỏ `docs/sentence_mode.md` (không sửa báo
  cáo lịch sử). Người dùng có muốn thêm vào backlog việc train lại CSLR với tập chia theo câu (GPU Kaggle, sau DoD 1–7) không?
- **Q2.** `checkpoints/cslr_best.pt` và `checkpoints/vit5_stage{1,2}/best_model/` chỉ có trên máy local, chưa có trong dataset
  private nào. **Mặc định:** chỉ ghi sha256 (C0 + các JSON), không tải lên. Có muốn lưu trữ vào một dataset Kaggle PRIVATE
  như kế hoạch 02/05 (việc riêng, sau kế hoạch này) không?

### 7.3 Điểm dừng có điều kiện trong lúc làm (coder DỪNG, báo; KHÔNG tự nới tiêu chí)
1. C1: độ dài `Clean10kDataset`/`VSLGHTextDataset` ≠ history JSON (dữ liệu đã đổi sau khi train) → DỪNG, CẦN NGƯỜI DÙNG
   (vấn đề dữ liệu mới).
2. C1: có câu mà các lần lặp mang > 1 biến thể cặp (gloss/translation), hoặc cặp ViT5 học cho một câu ≠ cặp của mẫu S06, hoặc
   câu heldout khớp L1/L2 với stage 1, hoặc `S06_vit5_clean` rỗng → báo planner (planner đánh giá có phải "vấn đề dữ liệu
   mới"; coder không tự đổi định nghĩa tập con hay ngưỡng).
3. C2 (AC4-b) hoặc C4a (AC6-a) không bằng hệt → báo planner (không nới sang dung sai).
4. C5: một lớp rỗng (0 token đúng hoặc 0 token sai trên VAL) → báo planner.
5. C6: kiểm chéo lõi ≠ đường dataset trên S06 → không ghi JSON, báo planner. Muốn chạy lại C6 lần 2 vì bất kỳ lý do gì →
   planner quyết và ghi lý do (không tự chạy lại để lấy số khác).
6. C8a: không có `clone/.../source/extract_keypoints.py` ở local, hoặc script gốc có bước không tái hiện được (tham số
   không đọc được bằng `ast`, tiền xử lý ảnh không rõ) → dừng C8, CẦN NGƯỜI DÙNG (cung cấp script gốc, hoặc đồng ý Ký câu
   chỉ có nguồn "clip mẫu" trong đợt này); các bước khác làm tiếp; AC10, AC11, `sentence_webcam` khi đó ghi BLOCKED, không
   tính là PASS.
7. C11: `sentence_webcam` không ra đúng 1 `sentence_result`, hoặc `mode_switch` cho thấy WS/camera không được giải phóng mà
   sửa ≤ 10 dòng dọn dẹp không đủ → báo planner.
8. Một test đã có bị vỡ → báo planner (không sửa test cũ). Riêng test AC11 của kế hoạch 06 (`docs/phase12_api.md`) xử lý
   bằng cách THÊM tài liệu (§3.8), không sửa test.
9. Cần cài gói npm/pip, tải model/trình duyệt từ mạng, cần GPU/Kaggle, cần xóa file, hoặc cần đổi model mặc định → báo
   orchestrator (hỏi người dùng).
10. Trên cloud: bước cần dữ liệu/checkpoint không chạy được → ghi "cần local", không thay bằng dữ liệu khác, không coi skip là pass.
