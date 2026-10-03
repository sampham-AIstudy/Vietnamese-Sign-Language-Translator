# Kế hoạch 13 — §0C Lần sửa 3 (2026-10-03, nhỏ) — phụ lục

> **XONG (planner, 2026-10-03, HEAD 3f6b1dc).** File này là **§0C** của `docs/plans/13-train-lai-checkpoint-thieu.md`, có hiệu lực như nằm ngay sau §0B.
> Tách file vì lượt planner này KHÔNG có công cụ sửa-tại-chỗ; viết lại toàn bộ 937 dòng hợp đồng đã duyệt bằng tay có rủi ro làm sai lệch nội dung.
> **Orchestrator cần chèn 1 dòng con trỏ** vào đầu file 13 (văn bản đề xuất ở §0C.6) và, nếu muốn, dấu **[LS3]** ở các dòng liệt kê ở §0C.6.
> §0C ghi đè mọi chỗ mâu thuẫn ở §3.9, §4 (B12, B13), §5 (AC0, AC9, AC12), §6 R1. Không có CẦN NGƯỜI DÙNG mới.
>
> **KHÔNG đổi:** B9a–B9f, §0B.1–§0B.4, §0B.6–§0B.12, preregistration, amendment, giao thức §3.12, mọi tiêu chí khác. Coder 13 đang ở B9b làm tiếp bình thường;
> Lần sửa 3 chỉ có hiệu lực từ B12 (và một kiểm bổ sung ở B11b, §0C.3).

## 0C.1 Lý do

- Kế hoạch 14 (`docs/plans/14-dinh-chinh-cslr-unseen.md`, quyết định người dùng 2026-10-03 02:40 — `docs/STATE.md` mục "Quyết định của người dùng") nhận
  toàn bộ việc đính chính "CSLR / Mode B đo trên câu chưa thấy": README + EVALUATION sửa TRỰC TIẾP bằng khối sinh từ JSON; 6 báo cáo lịch sử thêm khối
  ĐÍNH CHÍNH ở đầu; guard `tests/test_cslr_claim_guard.py` (14 §3.4) đỏ khi có dòng khẳng định không trỏ tới JSON bằng chứng P1/P2.
  14 §2.3 (`:103-109`) yêu cầu planner 13 sửa §3.9/B12 và §0B.5 AC0(a) TRƯỚC khi coder 13 tới B12.
- Bốn xung đột cụ thể nếu giữ §3.9 / B12 như cũ (đọc từ 14, không suy đoán):
  1. Câu đính chính của 13 §3.9 (`:627-628`, bản [LS1] `:631-634`) chứa "không phải chưa thấy câu" + neo "CSLR"/"S06"/"30 câu" ⇒ khớp CLAIM + ANCHOR của 14 §3.4
     mà không có ref P1/P2 ⇒ guard L1 (file sống) / L2 (file lịch sử) ĐỎ.
  2. 14 sửa `README.md:56-60` và `EVALUATION.md:346, :384-389` bằng khối giữa marker `cslr-claims:begin/end` (L3: nội dung == render). Các vị trí "sau dòng 56",
     "sau `EVALUATION.md:387/390`" của 13 nằm TRONG vùng đó.
  3. Khối `historical_*` của 14 liệt kê SỐ DÒNG các dòng khẳng định của file (14 §3.3 `{danh_sách_dòng}`); 13 chèn 1 dòng vào `reports/PHASE4B_REPORT.md` (sau `:112`)
     hoặc `reports/audit_round2/VERIFY.md` làm lệch số dòng ⇒ L3 ĐỎ.
  4. 14 ACB3 lặp lại AC5-c ("không số mới ngoài khối" trên `git diff 714d9c9 HEAD -- README.md EVALUATION.md …`, tính cả commit không phải của 14). Dòng
     "[Kế hoạch 13 — artifact mới]" chứa chữ số (ngày, `retrain_2026-10-02`) ⇒ nếu 13 thêm vào README/EVALUATION trước khi 14 đóng phần B, AC5-c của 14 ĐỎ giả.
- Sau khi 14 phần B (B7) chèn số mới từ `test_eval.json` vào các khối `readme_cap3`, `evaluation_12`, `evaluation_13_2`, câu đánh dấu cố định của 13
  ("Số liệu ở mục này đo trên checkpoint CŨ …") ở đầu Cấp 3 README / đầu §12 EVALUATION sẽ SAI (mục đó khi ấy có cả số mới) ⇒ bỏ hai vị trí đó.

## 0C.2 §0B.5 AC0(a) — kế hoạch chạy song song [LS3]

Thay câu "phải nằm trong danh sách file của kế hoạch đang chạy song song (`docs/plans/11-progress.md` / AC0 của 11)" (`:140-141`; và cột "Mới" của dòng AC0
ở §0B.10 `:193`; và AC0 [LS2] `:755-756`) bằng:

- Dòng `git status --porcelain` mới (so mốc B0 của 13) không thuộc danh sách AC0 của 13 thì phải thuộc danh sách file của MỘT kế hoạch đang chạy song song
  trên cùng nhánh:
  - **Kế hoạch 11:** tập ở `docs/plans/11-sua-vi-pham-guard-dod7.md` §5 AC1 (`:289-296`) + `docs/plans/11-progress.md`;
  - **Kế hoạch 14:** tập ở `docs/plans/14-dinh-chinh-cslr-unseen.md` §5 AC0 (`:249-254`) + `docs/plans/14-progress.md`.
- Script AC0 in TỪNG dòng như vậy kèm: kế hoạch sở hữu (11 | 14) + mục AC dẫn chứng. Dòng không khớp kế hoạch nào → FAIL (không đổi).
- File của 11 / 14 KHÔNG tính là vi phạm của 13. Ngược lại, file của 13 vẫn KHÔNG được xuất hiện trong commit nào ngoài tập 13 (kiểm ngược §0B.5 giữ nguyên);
  14 cam kết không chạm file của 13 (14 §2.2(c) `:94`).
- Không nới gì khác: AC0(b)(e) vẫn đo trên tập file của commit `^(WIP )?13:`.

## 0C.3 §3.9 / B12 — không chồng lấn kế hoạch 14 [LS3]

### Bỏ khỏi kế hoạch 13 (chuyển cho 14)
- MỌI "dòng đính chính rò rỉ" của §3.9: câu gốc (`:625-628`) và câu [LS1] (`:631-634`), ở mọi vị trí (`README.md:56`, `reports/PHASE4B_REPORT.md:112`,
  `EVALUATION.md:387`, `:390`, `reports/audit_round2/VERIFY.md:14`, `:46`). Nội dung đó do 14 phần A (đính chính, số "câu S06 đã thấy ở train" từ
  `reports/cslr_claims_<D>/old_cslr_sentence_coverage.json`) và 14 phần B (số mới từ `test_eval.json`) đảm nhận.
- Dòng "[Kế hoạch 13 — artifact mới]" ở: đầu khối Cấp 3 của README (trước `:56`), đầu §12 EVALUATION (`:342`), sau `reports/PHASE4B_REPORT.md:112` (lý do §0C.1).
- 13 KHÔNG sửa bất kỳ file nào trong 7 file lịch sử của 14 §2.2(b): `reports/PHASE4B_REPORT.md`, `reports/audit_round2/VERIFY.md`,
  `reports/audit_round2/AUDIT_ROUND2.md`, `reports/audit_round3/PROVENANCE.md`, `reports/audit_20260924/AUDIT_REPORT.md`, `docs/audit/PHASE4_AUDIT.md`,
  `reports/unified_run_2026-09-25/REPORT.md`.
- 13 KHÔNG thêm/xóa/sửa dòng nào nằm giữa hoặc chứa marker `cslr-claims:` (khối sinh của 14).

### Giữ lại (định vị theo TIÊU ĐỀ / chuỗi neo, không theo số dòng — 14 làm lệch số dòng)
Văn bản dòng đánh dấu giữ nguyên như §3.9 `:622-623` (không chứa từ khẳng định của 14 §3.4 ⇒ không vướng guard).
- **B12a** (sau B11b, không phụ thuộc 14):
  - `docs/phase6_stgcn.md`: ngay sau tiêu đề mục 8 và tiêu đề mục 9 (vị trí `:219`, `:233` lúc lập 13) — 2 dòng.
  - `docs/cloud_training.md`: 2 kernel mới vào bảng + 1 dòng Modal (như §3.9 `:628-629`, §3.10 `:642`).
- **B12b** (README.md + EVALUATION.md; CHỈ SAU khi commit `14: B8` có trong `git log` của nhánh — tức 14 phần B đã đóng; lý do §0C.1 ý 4):
  - `README.md`: 1 dòng đánh dấu cạnh dòng chứa `stgcn_best.onnx` (vị trí `:112-113` lúc lập 13); mục "Artifact không nằm trong git": 3 dòng (slug dataset +
    đường dẫn manifest) + dataset K3 nếu B14 chạy — như §3.9.
  - `EVALUATION.md`: 1 dòng đánh dấu ngay sau dòng tiêu đề `### 13.4 Mô Phỏng Offline vs Streaming CSLR` (`:407` lúc lập 13), NGOÀI mọi marker `cslr-claims:`.
  - Nếu tới B12b mà 14 chưa có commit `14: B8`: coder 13 ghi "B12b chờ 14 B8" vào 13-progress, làm tiếp những gì không phụ thuộc (B12a), báo orchestrator.
    Nếu orchestrator ghi 14 bị hủy/hoãn vô thời hạn → **CẦN PLANNER 13** (không tự quyết vị trí trong README/EVALUATION).
- Sau mỗi commit B12a/B12b, nếu `tests/test_cslr_claim_guard.py` có ở HEAD:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_cslr_claim_guard tests.test_render_cslr_claims -v` → OK, 0 skip, và
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/render_cslr_claims.py --check` → exit 0. Đỏ → DỪNG, CẦN PLANNER (không sửa test/khối của 14,
  không chạy `--write`).
- Không số liệu mới trong md (giữ luật §3.9). 13 không chép số nào từ `test_eval.json` vào md — việc đó là của 14 B7 qua khối sinh.

### Bàn giao số liệu cho 14 phần B (B11b → 14 B7)
Đường dẫn CỐ ĐỊNH (14 trỏ cứng): `reports/retrain_2026-10-02/eval/test_eval.json`. Điều kiện vào của 14 B7 (14 §3.6 `:219-221`, luật P2 14 §3.4 `:194-195`)
trùng với đầu ra của B11b; Lần sửa 3 biến chúng thành kiểm BẮT BUỘC của 13 (chặt hơn, xem AC12 [LS3]):
1. Commit có tiêu đề `13: B11b …`, chứa `test_eval.json` (+ log); `git log --format=%h -- <file>` = 1 dòng; `generated_by.code_dirty == false`.
2. `inputs.sentence_split_sha256` (ghi bởi `scripts/eval_sentsplit.py:723`) == `split_file_sha256(bytes của configs/vslgh_sentence_split_v1.json)`
   (luật CRLF→LF, `src/data/sentence_split.py:131-134`) == `sentence_split.sha256` của `reports/retrain_2026-10-02/preregistration.json`.
3. `per_sample` đúng `len(test_ids)` mục (30), mọi `sentence_id` ∈ `test_ids` của file split (đã có ở AC12).
4. `--recompute-from` ra `metrics` bằng hệt (đã có ở AC12) — kết quả + đường log ghi ở 13-progress.
5. 13-progress có mục **"Bàn giao cho kế hoạch 14 phần B"**: đường dẫn, hash commit B11b, sha256 của `test_eval.json`, đường log recompute, và danh sách khóa
   cấp 1 + khóa của `metrics` IN RA bằng lệnh (`.venv/Scripts/python -c "import json; d=json.load(open('reports/retrain_2026-10-02/eval/test_eval.json', encoding='utf-8')); print(sorted(d)); print(sorted(d['metrics']))"`),
   chép nguyên output (không gõ tay). Coder 13 báo orchestrator "14 B7 có thể bắt đầu".
6. Thiếu khóa mà 14 §3.6 cần (WER + S/D/I + CI; BLEU A, B, Δ + CI; số mẫu) là việc của 14 phát hiện (14 B7 → CẦN PLANNER); 13 KHÔNG thêm khóa/sửa
   `eval_sentsplit.py` sau B11b, KHÔNG chạy eval lần hai.

## 0C.4 Thay đổi bảng §4 [LS3]

| Bước | Cũ | Mới |
|---|---|---|
| B12 (`:730`) | Đánh dấu tài liệu (§3.9), 1,5 h, phụ thuộc B11b | **B12a** (§0C.3: `docs/phase6_stgcn.md`, `docs/cloud_training.md`, 0,5 h, phụ thuộc B11b). **B12b** (§0C.3: README.md, EVALUATION.md, 0,5 h, phụ thuộc B12a VÀ commit `14: B8`). Mỗi bước 1 commit `13: B12a …` / `13: B12b …`. |
| B13 (`:731`) | phụ thuộc B12 | phụ thuộc B12a + B12b |

Thứ tự toàn cục (orchestrator xếp): 13 B11b → (14 B7 → 14 B8) → 13 B12b → 13 B13. Không vòng phụ thuộc (14 B7 chỉ cần 13 B11b).

## 0C.5 Thay đổi tiêu chí chấp nhận (planner đổi, lý do)

| Tiêu chí | Cũ | Mới [LS3] | Lý do |
|---|---|---|---|
| AC0 (a) | dòng porcelain ngoài 13 phải thuộc 11 | thuộc 11 HOẶC 14 (§0C.2), in từng dòng + kế hoạch sở hữu | 14 chạy song song cùng nhánh (14 §2.3) |
| AC0 (e) | trừ "các file đánh dấu §3.9" (gồm `PHASE4B_REPORT.md`, `VERIFY.md` [LS1]) | file md 13 được sửa = đúng {`README.md`, `EVALUATION.md`, `docs/phase6_stgcn.md`, `docs/cloud_training.md`, `docs/plans/12-khoi-phuc-du-lieu.md`} (+ `docs/progress_log.md`, `docs/plans/13-progress.md`); tập file của commit `^(WIP )?13:` ∩ 7 file lịch sử §0C.3 = ∅ | §0C.1 ý 3 |
| AC9 | đủ dòng đánh dấu + dòng đính chính rò rỉ ở các file §3.9 | (a) đếm `[Kế hoạch 13 — artifact mới]` theo file, trong diff của commit 13: `README.md` 1, `EVALUATION.md` 1, `docs/phase6_stgcn.md` 2, file khác 0; (b) 0 dòng `+` trong file md của commit 13 khớp CLAIM của 14 §3.4 (kiểm bằng `scripts/cslr_claim_rules.find_claims` nếu có ở HEAD; nếu chưa có thì bằng regex CLAIM chép nguyên văn 14 §3.4 ý 2, sau khi xóa SIGNER_QUALIFIED ý 1); (c) 0 dòng `+`/`-` của commit 13 chứa `cslr-claims:`; (d) `git diff --numstat` cột xóa = 0 cho các md đó (giữ); không số liệu mới trong md (giữ); README liệt kê 3 dataset + 3 manifest (giữ); (e) guard 14 + `--check` như §0C.3 (nếu có ở HEAD) | phần đính chính chuyển sang 14 với kiểm máy chặt hơn (guard + khối sinh); 13 kiểm KHÔNG can thiệp |
| AC12 | như `:831-836` | + `inputs.sentence_split_sha256` == `split_file_sha256(configs/vslgh_sentence_split_v1.json)` == `preregistration.sentence_split.sha256`; + mục "Bàn giao cho kế hoạch 14 phần B" ở 13-progress (§0C.3) | chặt hơn; khớp luật P2 của 14 |
| §6 R1 | "Ghi ở §3.9" | "Ghi ở kế hoạch 14 (khối README/EVALUATION + 6 báo cáo lịch sử)" | §0C.3 |

Không tiêu chí nào bị hạ: nghĩa vụ "ghi rò rỉ CSLR cũ vào tài liệu" vẫn tồn tại, chuyển sang 14 với guard máy kiểm (L1–L4) + số sinh từ JSON có lệnh/commit,
chặt hơn câu chữ gõ tay của §3.9. 13 có thêm kiểm "không can thiệp" (AC9 b, c) và kiểm sha split ở AC12.

## 0C.6 Chỗ đánh dấu [LS3] trong thân `13-train-lai-checkpoint-thieu.md` (cho orchestrator / lần sửa sau có công cụ sửa)

Dòng con trỏ đề xuất, chèn ngay trước dòng 3 (trước khối "Lần sửa 2"):
`> **Lần sửa 3 — XONG (planner, 2026-10-03, nhỏ).** §0C ở `docs/plans/13-lan-sua-3.md`: B12 tách B12a/B12b, bỏ dòng đính chính rò rỉ (chuyển kế hoạch 14), bàn giao test_eval.json cho 14 B7, AC0(a) thêm kế hoạch 14. Không đổi B9a–B9f, §0B.3, preregistration.`

| Dòng (tại 3f6b1dc) | Mục | Ghi chú [LS3] |
|---|---|---|
| `:136`, `:140-141` | §0B.5 AC0(a) | thêm kế hoạch 14 — §0C.2 |
| `:193` | §0B.10 dòng AC0 | §0C.2 |
| `:621-634` | §3.9 | bỏ dòng đính chính rò rỉ + 3 vị trí đánh dấu; B12a/B12b — §0C.3 |
| `:730-731` | §4 B12, B13 | §0C.4 |
| `:742-748`, `:753`, `:755-756` | AC0 (a)(e), [LS1] câu "md thêm theo §3.9 [LS1] (`VERIFY.md`, `EVALUATION.md`)", [LS2] (a) | §0C.5 |
| `:815-817` | AC9 | §0C.5 |
| `:831-836` | AC12 | §0C.5 (bổ sung) |
| `:856` | §6 R1 | §0C.5 |

## 0C.7 Rủi ro / điểm dừng do Lần sửa 3

- Rủi ro: 13 đóng muộn hơn vì B12b chờ 14 B8 (14 B7–B8 ước lượng ~2 h công theo 14 §4; con số là ước lượng của 14, chưa xác minh). Không ảnh hưởng
  checkpoint, đánh giá, ngân sách GPU.
- Điểm dừng mới: (1) guard 14 / `--check` đỏ sau B12a/B12b → CẦN PLANNER (không sửa test/khối của 14); (2) 14 bị hủy/hoãn khi 13 tới B12b → CẦN PLANNER 13.
- Không CẦN NGƯỜI DÙNG; không đổi model mặc định; không hành động không hoàn tác; không đụng thay đổi chưa commit.
