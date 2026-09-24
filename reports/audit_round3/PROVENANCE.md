# Audit vòng 3 — Nguồn gốc dữ liệu (PROVENANCE) — 24/09/2026

Thực hiện theo skill `vsl-data-integrity` (Bước 0: truy script tạo dữ liệu → nguồn ngoài → soi nội dung → nguồn của nhãn).
Bằng chứng tái lập: `run_r3_tier2_leakage.py`, `r3_tier2_leakage.json`, `r3_tier2_leakage_per_sample.csv`.

## Tóm tắt

| Bộ dữ liệu | Dùng cho | Người thật? | Nguồn | Nhãn đến từ | Kết luận |
|---|---|---|---|---|---|
| `data/vsl_alphabet_pilot` | Cấp 1 | **Không** — sinh tổng hợp | `scripts/record_vsl_alphabet.py` | code | **FAIL** (đã cách ly, xem `reports/alphabet_run_2026-09-24/`) |
| `data/Dataset/Videos` + `Labels/label.csv` (QIPEDC) | Cấp 2 | **Có** | Từ điển QIPEDC (logo + chữ "Kí hiệu Miền …" in trong video) | Nguồn (tên file + chữ trong video) | **Dữ liệu thật — nhưng ~54% split test là bản quay trùng với train → số liệu Cấp 2 KHÔNG hợp lệ** |
| `data/extracted_keypoints` | Cấp 2 (đầu vào model) | Suy ra từ video thật | `preextract_tier2_parallel.py` → MediaPipe Holistic | — | PASS (trích lại 1 video: cùng 75 frame, lệch TB 0.006) |
| `data/external/vsl_gh` (VSL-GH) | Cấp 3 CSLR | Có dấu hiệu thật (không có video để soi) | GitHub `nguyentheanh822/Vietnamese-Sign-Language-Translation` @ `6c351e6`, MIT | Nguồn | **PASS có lưu ý** |
| `data/external/parallel_text` (10K) | Dịch gloss→câu | N/A (văn bản) | GitHub `BichDiep/Parallel-Corpus-Vie-VSL` @ `f57558c` | Nguồn | Nguồn khớp; **phương pháp biên soạn UNVERIFIED** |
| `data/raw_tudienngonngukyhieu` (HCMUE) | Chỉ hiển thị (lexicon), không train | **Có** | Crawl `tudienngonngukyhieu.com` | Tiêu đề trang nguồn | PASS; license chưa rõ; chỉ tải được 435/12.101 URL |

Không phát hiện thêm bộ dữ liệu **tổng hợp** nào ngoài pilot chữ cái. Phát hiện mới nghiêm trọng là **rò rỉ bản quay trùng lặp** ở Cấp 2 và **số liệu trong tài liệu không có artifact chứng minh**.

---

## 1. Cấp 2 — QIPEDC (`data/Dataset/`)

**Nguồn / người thật.** 4.362 video 1280×720 (24–30 fps, 2–9 s), khớp 1-1 với `label.csv`. `label.csv` giống hệt bản commit gốc `406db45` (12/09, chỉ khác BOM/CRLF); không script nào ghi đè nó. Soi 36 frame ngẫu nhiên: người thật, studio nền xanh, logo QIPEDC; video có dòng chữ "Kí hiệu Miền Bắc/Trung/Nam" do nguồn in sẵn → **nhãn phương ngữ là thật, không bị gán**.

**Người ký (signer).** ~8–10 người, và **cùng một người xuất hiện ở cả ba biến thể B/T/N**. Nhãn B/T/N là *biến thể ký hiệu vùng miền*, không phải vùng của người ký. `possible_signer_id = unknown` cho 100% video → không thể chia split độc lập người ký. Câu "Native deaf signers recorded across 3 geographic dialect regions" trong `docs/data_registry.md` là **nói quá, chưa kiểm chứng**.

**Rò rỉ bản quay trùng lặp (phát hiện chính).** Nguồn QIPEDC dùng lại *cùng một clip* cho nhiều vùng khi ký hiệu giống nhau (chỉ đổi chữ chú thích). Trên 120 từ có đủ B/T/N: cặp T–N gần như trùng hệt ở 68/120 (lệch pixel trung vị 0.3/255, cùng số frame ở 65/120); B–T 33/120; B–N 0/120. Split `data/splits/folds/tier2_indomain_*` xếp các biến thể của cùng từ vào train/val/test khác nhau, nên:

| Test in-domain (checkpoint `stgcn_tier2_indomain.pt`, n=487) | n | Top-1 [95% CI] | Top-5 |
|---|---:|---|---|
| Toàn bộ (tái lập đúng JSON vòng 2) | 487 | 46.41 [42.09, 50.93] | 60.78 |
| **Có bản quay trùng trong train** | 264 (54.2%) | **78.79** [73.48, 83.71] | 97.73 |
| **Sạch (không trùng)** | 223 | **8.07** [4.93, 11.66] | 17.04 |
| Bắc sạch / Trung sạch / Nam sạch | 125 / 32 / 66 | 1.6 / 12.5 / 18.2 | |

→ Con số 46.41% chủ yếu đo **khả năng nhận lại clip đã thấy**. Năng lực thật trên clip chưa thấy ≈ **8% Top-1**. Chênh lệch "Bắc thấp – Trung cao" giải thích bởi tỉ lệ trùng (B 23%, T 80%, N 59%), không phải bởi đặc điểm phương ngữ.

Split Tier 1 (`tier1_*`: B=train, T=val, N=test) chịu cùng lỗi theo chiều khác: **val và test chứa cùng bản quay** ở phần lớn từ (ví dụ `W00013T`/`W00013N` cùng 120 frame, cùng tỉ lệ phát hiện tay 0.483) → chọn model bằng val ≈ chọn bằng test.

**Số liệu trong tài liệu không có bằng chứng.** `EVALUATION.md` §13.3 và `AUDIT_ROUND2.md` §4.2 ghi Top-5 **75.77%**, Trung **81.60%** [75.46, 87.12], Nam **36.20%** [28.83, 43.56]. Artifact duy nhất (`reports/audit_round2/v4_generalization.json`, commit `536c7c5`) và lần chạy lại hôm nay đều cho Top-5 **60.78%**, Trung **61.73%**, Nam **56.17%**. Các con số trong tài liệu (đưa vào ở `08733ee`, `1a266c6`) **không truy được về bất kỳ lần chạy nào**.

## 2. Cấp 3 — VSL-GH (`data/external/vsl_gh/`)

- 4.198/4.200 file `keypoints_frontal/*.npy` khớp **từng byte** (git blob SHA-1) với upstream @ `6c351e6`; 2 file còn lại (`SENT151_S04_R01/R02_F`) là file upstream có dấu cách thừa trong tên, cũng khớp hash sau khi đổi tên.
- Upstream README: 6 signer, MediaPipe Holistic, nền xanh; repo không kèm video → không soi được hình.
- Thống kê landmark nhất quán với quay thật: độ rộng vai khác nhau giữa signer (0.31–0.475), rung tự nhiên, các lần lặp cùng câu dài khác nhau (185/175/167 frame) và không trùng.
- **Lưu ý:** `scripts/prepare_canonical_vsl_gh.py` **tự viết tay** 2 annotation (`SENT236_S01_R03_F`, `SENT285_S04_R03_F`, mốc thời gian ước lượng) — thuộc tập train, ảnh hưởng nhỏ nhưng phải ghi rõ đây là nhãn do dự án tạo, không phải của upstream.
- Đã biết từ trước: test S06 có 270/300 câu đã xuất hiện trong train; chỉ 30 câu unseen là thước đo hợp lệ (EVALUATION §13.2 đã ghi).

## 3. Corpus dịch 10K (`data/external/parallel_text/`)

- 9.404/9.405 cặp trong `vie_vsl_10k.jsonl` có nguyên văn trong upstream `VSL10k.txt`/`Vie10k.txt` @ `f57558c` (bản dự án đã loại trùng).
- Vế "VSL" là gloss dạng chữ Việt (bỏ hư từ, đổi trật tự), ví dụ `Anh mất năm năm trước .` ↔ `Anh ấy đã mất năm năm trước .`
- `reports/audit_20260924/AUDIT_REPORT.md` mục B4/§4 ghi corpus là "tổng hợp (PCFG rule-based)" — **không tìm thấy căn cứ nào** (không script, không tài liệu upstream nói vậy). Upstream nói được "biên soạn cẩn thận" nhưng không công bố phương pháp. Trạng thái đúng: **nguồn đã xác minh, phương pháp biên soạn UNVERIFIED** — không nên gọi là "tổng hợp", cũng không nên gọi là "do người Điếc dịch".

## 4. HCMUE crawl (`data/raw_tudienngonngukyhieu/`)

`scripts/crawl_tudienngonngukyhieu.py` chỉ tải (requests, Vimeo). 435 video người thật (nhiều người, nhiều phông), vùng miền lấy từ tiêu đề trang. **Không nằm trong split nào** — chỉ dùng cho `src/data/lexicon_bank.py`/backend để hiển thị video tham khảo. License nội dung web chưa rõ.

## 5. Việc cần làm (chưa làm — chờ quyết định)

1. **Cấp 2:** coi mọi số liệu Tier 1/Tier 2 hiện có là **không hợp lệ**. Làm lại split theo **bản quay** (gom các video trùng hình thành một nhóm, cả nhóm nằm cùng một split), rồi train lại. Báo cáo số liệu "clean" (≈8% hiện tại là mốc thật).
2. Gỡ các số 75.77 / 81.60 / 36.20 khỏi `EVALUATION.md`, `AUDIT_ROUND2.md`, `README.md`; thay bằng bảng ở mục 1.
3. `docs/data_registry.md`: sửa mô tả signer QIPEDC; sửa nhận định "PCFG synthetic" ở AUDIT_REPORT B4; ghi 2 annotation VSL-GH do dự án tự viết.
4. Thêm guard `DuplicateRecordingLeakageError` vào `src/data/vsl_dataset.py` cạnh `VideoLeakageError` hiện có (guard hiện tại chỉ so `video_id`/tên file — `src/data/vsl_dataset.py:86-101` — nên không bắt được cùng một bản quay mang hai tên file khác nhau).
