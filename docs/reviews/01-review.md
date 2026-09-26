# Vòng 2

Review 01, vòng CODE↔REVIEW 2/3. Reviewer độc lập, ngày 2026-09-26, nhánh `feat/vslt-complete`, HEAD `65a2821`.
Commit mới được review: `c54b772`, `67ff25a`, `65a2821` (nối tiếp `8c08845`). Kế hoạch: `docs/plans/01-buoc4-hoan-tat-4a-4c.md`
(§0 "Lần sửa 1", AC1–AC9). Mọi con số dưới đây do reviewer tự chạy lại qua `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`.
Không tin tóm tắt của coder; đã đọc `git diff 8c08845..HEAD`.

## Kết luận vòng 2: **APPROVE**

Không còn FAIL. M1–M4 và các góp ý nhỏ của vòng 1 đã được xử lý thật, do script sinh ra (không chỉnh tay), có test. Mục 13
nay PASS: REPORT có mục "Phạm vi so sánh và mức khớp train" sinh từ `history.json`, PROPOSAL nêu đúng phạm vi.
Việc còn lại **theo kế hoạch, không phải lỗi**: R6 — sinh lại REPORT/JSON với `--review-file docs/reviews/01-review.md`
(file này, có vòng 2), kiểm AC9, rồi DỪNG ở điểm dừng "sau 4c". Hiện §6 của REPORT vẫn chứa kết luận vòng 1
(CHANGES_REQUESTED), nên AC4 j chưa xong cho tới R6.

## Bảng 1–13 (trạng thái HEAD `65a2821`)

| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch; AC có test thật | PASS | AC1 ca 16–23 có test riêng, assert giá trị cụ thể: `TestTrainingFit` (`tests/test_report_step4.py:459–501`: hòa `val_top1` ở epoch 2/3 → chọn val_loss nhỏ hơn; đảo loss → 2; hòa cả hai → epoch sớm; `lr_drop_epochs == [3, 4]`; 795/64 → 13 bước; batch `None` → `None`; history rỗng → mã 2), ca 17 (504–511), ca 18 (514–537), ca 19 (540–561, quét text fixture có/không `--init-from`), ca 20 (564–586: dự đoán đúng "a" không vào `wrong_only`, tổng ba cột = n), ca 21 (589–609: tên run đổi theo; nhánh trim=false không có "trim=true"), ca 22 (612–642: 996 s; không tiêu đề → `[]`; không commit → `None`), ca 23 + hợp đồng CLI (645–715: exit 2 khi thiếu history của run chọn / run từ điển dùng, `null` với run khác, thứ tự mục 4c). AC5b 1–6: `TestProposal4cScope` (718–780), không skip, thiếu file thì lỗi ở `setUp`. |
| 2 | Tự chạy lại toàn bộ test | PASS | `python -m unittest tests.test_report_step4 -v` → `Ran 69 tests ... OK`, 0 skip. Bộ AC2 (10 module handoff) → `Ran 53 tests ... OK`. Khớp số coder báo (38 → 62 ở c54b772, → 69 ở 67ff25a; AC2 53 → 53). |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff 8c08845..HEAD -- tests/` → 1 file, `334 insertions(+)`, không có dòng `-` nào ngoài dòng header `--- a/…`. Không có `skip`/`expectedFailure` mới. Thay đổi `make_fixture` chỉ THÊM hằng `FIT_HISTORY` (dòng 246–253) và một dòng ghi `history.json` cho mỗi run fixture (dòng 285). Đánh giá: không nới test cũ. Mọi assert cũ giữ nguyên. `history.json` nay là đầu vào bắt buộc (exit 2 khi thiếu ở run chọn / run từ điển dùng), nên nếu không thêm dòng này thì các test end-to-end cũ sẽ fail vì lý do hợp lệ. Các test lỗi cũ (thiếu `test_logits.npz` → 2, sai thứ tự nhãn → 1, không khớp từ điển → 3) vẫn kiểm cùng mã thoát và vẫn kiểm không ghi file. |
| 4 | Nguồn gốc dữ liệu thật | PASS | Đầu vào mới chỉ là `runs/*/history.json` do trainer ghi trong kernel (7 file đã commit) và lệnh train trong log kernel. Số clip train 795 / 15138 khớp `train.log` của từng run ("classes 594, train 795, val 105, test 721"; "classes 876, train 15138"). Batch 64 khớp lệnh ở `vsl-train-harmonized_v3.log` dòng 15 và 80. Không có dữ liệu sinh. |
| 5 | Rò rỉ | PASS (giới hạn đã công bố) | Không đổi so với vòng 1: `split_integrity` PASS; QIPEDC không có signer_id và S06 dùng câu đã thấy trong train, cả hai nằm trong REPORT §5. |
| 6 | Chọn bằng VAL, TEST một lần | PASS | Chẩn đoán mức khớp chỉ đọc `history.json` (train/VAL), tính SAU khi chọn (`scripts/report_step4.py:861–884`), không đi vào `select`/`choose_*`. TEST vẫn chỉ đọc lại `test_logits.npz`. Mọi giá trị JSON cũ không đổi (mục 7). |
| 7 | Số liệu truy được | PASS | (a) Chạy lại đúng lệnh ở header, chỉ đổi `--out`/`--json-out` sang thư mục tạm: exit 0; JSON bằng (`==`) bản đã commit sau khi bỏ `generated_by`; REPORT chỉ khác 2 dòng header (đường dẫn out, HEAD `67ff25a` → `65a2821`). (b) Chạy lần 2 cùng lệnh → `cmp` byte-giống cả hai file. (c) `git diff 67ff25a HEAD -- scripts src tests` rỗng; `code_dirty=false`. (d) Duyệt đệ quy JSON `8c08845` vs HEAD: không khóa cũ nào bị xóa; giá trị cũ chỉ đổi ở `generated_by`, `inputs` (45 mục cũ là tập con của 56 mục mới; thêm 9 `history.json`, `train_unified.py`, review), `kernel_code_diffs[3].to`, `augmentation` (bỏ tiền tố lặp), `review`. (e) Kiểm độc lập mục 4c mới từ `history.json`: từ điển 48 epoch, best 28 (= `metrics.json` `val_best.epoch`), train top-1 29.69 / 34.21, lr 0.001 → 1.5625e-05, giảm lr ở 16, 22, 28, 34, 40, 46, val_loss 6.3943 / 6.3584 / 6.4564, tổng time_sec 212.5; gộp 98 epoch, best 78, 95.15 / 95.47, giảm lr ở 50, 64, 74, 81, 87, 97, val_loss 4.3396 / 2.4065 / 2.437, tổng 5738.5. Bước: ceil(795/64) = 13 → 624; ceil(15138/64) = 237 → 23226; ceil(23226/13) = 1787 epoch × 4.4267 s ≈ 7910 s ≈ 2.20 giờ. Tất cả trùng REPORT dòng 326–336. (f) Thăm dò (b): 69/634, 183/225, 282/876 trùng số reviewer tự tính ở vòng 1; 634 = 722 − 88, 225 = 1189 − 964. |
| 8 | Cỡ mẫu và CI | PASS | Cột "chỉ dự đoán sai" có k/n + Wilson CI cho cả ba bộ dòng (REPORT dòng 352–354). Không có kết luận mới rút từ n nhỏ; (b) ghi "chỉ báo, không kiểm định". |
| 9 | Nhất quán train–realtime | PASS (trong phạm vi) | REPORT §3.4 (iv) (dòng 274) sinh từ `run_config.trim`: H-keepz-360 train với trim=true; live phải cắt nghỉ cùng tham số; giữ/bỏ không do PREREG quyết định; bỏ thì train lại. Việc này không chạm `backend/`, `src/`. Vẫn **chặn** đổi model mặc định cho tới khi có test tương đương (360 px + cắt nghỉ). |
| 10 | Không random/mock/hard-code | PASS | Chuỗi cố định mới (`SCOPE_SENTENCE`, `TRAIN_TOP1_MEASUREMENT`) là mô tả, không chứa số. Câu phạm vi chỉ in khi `scope_limited` (tổng bước khác nhau hoặc không dùng cờ khởi tạo), đúng §3.4. `trim_consequence` không gõ cứng tên run (test ca 21c). Không có random/mock mới. |
| 11 | Bảo mật | PASS | Không token/khóa/`kaggle.json` trong diff. `git diff --name-only 27233f6..HEAD -- '*.pt' '*.npz' '*.log'` rỗng. Không đụng API/CORS/WS. Vẫn còn: `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` untracked và không bị gitignore (`git check-ignore` exit 1); đây là câu hỏi cho người dùng. |
| 12 | So sánh công bằng | PASS | 4c vẫn trên cùng 721 clip; ngưỡng 0.5 không đổi; không tiêu chí nào bị nới. Mục mới nói rõ hai model có cùng lệnh train (chỉ khác `--out-dir/--data-root/--sources`; reviewer đối chiếu log v3 dòng 15 và 80), nhưng quỹ tối ưu khác nhau: 624 vs 23226 bước. |
| 13 | Kết luận vượt bằng chứng | PASS | REPORT: câu phạm vi (dòng 334) và dòng Giới hạn (372) nói kết quả chính chỉ về "model tách train từ đầu bằng công thức hiện tại". PROPOSAL: "khuyến nghị có điều kiện: 4c chỉ đo một cách tách" (dòng 3); mục "Phạm vi" (9–12) có 34.21% vs 95.47% và 624 vs 23226 bước, nói rõ KHÔNG loại trừ A khi train tới khi khớp hoặc khởi tạo từ trọng số; câu cũ "mất toàn bộ dữ liệu VSL-GH" đã bỏ; (b) chỉ dùng cột dự đoán sai + tỷ lệ nền, ghi "chỉ báo, không kiểm định"; "Điều gì sẽ làm đổi khuyến nghị" có thí nghiệm mới "tốn GPU … cần người dùng duyệt". Nhận xét thêm của reviewer (ủng hộ "chưa khớp"): val_loss của model từ điển 6.3943 → min 6.3584, gần ln(594) ≈ 6.387, tức VAL loss hầu như không rời mức ngẫu nhiên. Góp ý câu chữ nhỏ ở G3, không chặn. |

## Kiểm theo AC (vòng 2)

| AC | Kết quả | Ghi chú |
|---|---|---|
| AC1 | PASS | 69 OK, 0 skip; ca 1–15 cũ nguyên vẹn; ca 16–23 có test (mục 1). |
| AC2 | PASS | 53 → 53 OK; `test_report_step4` 38 → 69 (≥ 38 + 8); diff test chỉ có dòng thêm. Số trước/sau có trong `docs/progress_log.md`. |
| AC3 | PASS | Mục 7 (a)–(c). Đã kiểm ≥ 10 số, trong đó > 3 số ở mục 4c mới truy về `history.json`. |
| AC4 a–i | PASS | Không đổi so với vòng 1 (giá trị JSON cũ không đổi). |
| AC4 j | CHƯA XONG (theo kế hoạch) | §6 hiện là review vòng 1. Làm ở R6 với file này. |
| AC4 k | PASS | REPORT dòng 320–336: bảng đủ 13 cột, dòng về cách trainer đo, `train_cmd_diff`, `init_options`, câu phạm vi, ước lượng GPU có nhãn "ước lượng". Đã đối chiếu > 2 giá trị mỗi model với `history.json`. |
| AC4 l | PASS | §3.4 (iv) dòng 274; JSON `4b.trimming.consequence`. |
| AC4 m | PASS | Dòng 348–358; số trùng review vòng 1 (69/634, 183/225, 282/876). |
| AC4 n | PASS | Dòng 371 (12:30 vs 12:13:24, 996 s), dòng 372–373. |
| AC4 o | PASS | Dòng 177: đúng một dòng "- Augmentation (training only): …"; không còn "Augmentation: Augmentation". |
| AC5 | PASS (sát ngưỡng) | 546 từ theo `str.split()` (cách test đếm) và theo `LC_ALL=C.UTF-8 wc -w`; một khuyến nghị (B); có "người dùng quyết định"; `TestProposal4c` không bị sửa. Xem G2 về cách đếm `wc -w`. |
| AC5b | PASS | 1–6 có test và đều qua. Reviewer kiểm thêm: 8 cụm `% (k/n)` và 45 số của PROPOSAL đều có trong REPORT §1–5 (không tính §6 Review). |
| AC6 | PASS | `git diff --stat 27233f6..HEAD`: chỉ file được phép. Code chỉ đổi `scripts/report_step4.py`. Không đổi `.gitignore`, PREREG, `history.json`, `metrics.json`, JSON 4a/4b cũ, `data/`. `REPORT_partial.md` không có trong git và vẫn trên đĩa. 3 file data người dùng xóa vẫn chưa commit. |
| AC7 | PASS (vòng này) | Không FAIL cho các commit Lần sửa 1 và cho 348843f, 4bb3811, 9e3be95, a414b0d, 27233f6, 4f4e349 (không đổi từ vòng 1). |
| AC8 | PASS | Cả 3 commit mới ghi `impact` + `detect-changes --scope all` (không partial/truncated) trong commit message. `docs/progress_log.md` có đúng 1 dòng kế hoạch 01, số test, và ghi chú `--scope staged` của 3 commit cũ. Dòng này cần cập nhật ở R6 (kết luận review cuối, số vòng, commit C). |
| AC9 | PASS (cơ chế) / làm lại ở R6 | `git diff 67ff25a 65a2821 -- REPORT.md`: 3 hunk = header (2 dòng), dòng inputs của file review, §6. JSON bằng nhau sau khi bỏ `generated_by`, `review`, input vai trò "review". Cần kiểm lại với commit R6. |

## Xác minh M1–M4 và góp ý nhỏ vòng 1

| Việc | Đã xử lý? | Bằng chứng |
|---|---|---|
| M1 (mức khớp / phạm vi 4c) | CÓ | Hàm `steps_per_epoch`, `training_fit`, `batch_size_from_command`, `train_cmd_diff`, `init_options` (`scripts/report_step4.py:318–396`); `4c.fit_and_scope` (861–884); render (1304–1349). PROPOSAL viết lại có phạm vi; có test AC5b. |
| M2 (hệ quả cắt nghỉ) | CÓ | `trim_consequence` (434–452), JSON `4b.trimming.consequence`, REPORT (iv). |
| M3 ((b) chỉ-sai + tỷ lệ nền) | CÓ | `pred_origin`, `label_space_base_rate` (413–431); `pred_split` dùng chúng (851–862) và giữ khóa cũ. |
| M4 (quy trình) | CÓ, trừ R6 | REPORT đã sinh với `--review-file` (65a2821); progress_log có dòng; `--scope all` ở cả 3 commit. Còn R6 cuối. |
| Góp ý: test AC5 theo ngữ cảnh | CÓ | AC5b.1 (so cụm `% (k/n)` nguyên văn + biên không phải `[0-9A-Za-z]`). Còn điểm yếu nhỏ, xem G1. |
| Góp ý: `REPORT_partial.md` | CÓ | Kế hoạch §2.1 đã sửa; file untracked, không bị đụng; câu hỏi ở §7. |
| Góp ý: giờ tiêu đề PREREG | CÓ | `prereg_header_times` (458–478), REPORT dòng 371, sinh từ `git show <commit>:PREREGISTRATION.md`. |
| Góp ý: "Augmentation" lặp | CÓ | REPORT dòng 177; test ca 23. |
| Góp ý: `.gitignore` cho `.pt` | Chuyển cho người dùng | Đúng kế hoạch (§7 câu 5); `.gitignore` chưa bị sửa. |

## Xác minh risk HIGH của `detect-changes` ở c54b772

- Reviewer chạy `node .gitnexus/run.cjs detect-changes --scope compare --base-ref 8c08845 --repo .` → `risk high`, 8 luồng bị
  ảnh hưởng: `Pred_split → Wilson`, `Main → Rel`, `Main → Sha256`, `Main → Fr`, `Main → Fv`, `Main → Na`, `Main → Yn`,
  `Label_space_base_rate → Wilson`. Cả 8 luồng nằm trong `scripts/report_step4.py`. Coder ghi 7 luồng; luồng thêm là
  `Label_space_base_rate`, do index được làm mới ở commit sau. Không đổi kết luận.
- `git diff -U0 8c08845..HEAD -- scripts/report_step4.py`: các hunk chỉ nằm ở khối hàm mới chèn sau `compare_legacy`, trong
  `build`, ở hàm mới `raw` (chèn sau `na`), và trong `render`. Không hàm có sẵn nào khác bị sửa. HIGH đến từ số symbol/luồng
  bị ảnh hưởng và việc lệch dòng, không phải từ caller ngoài script.
- `impact build --file scripts/report_step4.py --direction upstream`: LOW, `epistemic: exact`, caller duy nhất `main`
  (+ module Tests). `impact render …`: LOW nhưng `epistemic: lower-bound` (1 call site không xác định được kiểu receiver).
  Text search bù: chuỗi `report_step4` chỉ xuất hiện trong `scripts/report_step4.py`, `tests/test_report_step4.py` và
  `step4_results.json` (chuỗi lệnh). Trong script, `build(`/`render(` chỉ được gọi ở `main` (dòng 1469–1470). Call site không
  xác định là `R.render(...)` trong test. Kết luận: không có caller nào ngoài `main()` và test.

## Góp ý nhỏ (không chặn)

- **G1 (triển khai, test).** `TestProposal4c.test_every_number_is_in_report` và AC5b.1 so với TOÀN BỘ REPORT.md, kể cả §6
  Review. Văn bản review lại chứa đúng các số đó (34.21%, 69/634, …), nên test có thể qua nhờ văn bản review chứ không nhờ
  phần do script sinh. Reviewer đã kiểm tay: mọi số của PROPOSAL có trong §1–5. Đề xuất (việc sau, THÊM test mới): cắt REPORT
  trước `## 6. Review` khi so. Ngoài ra, biên `(?<![0-9A-Za-z.])` coi `_` là biên, nên "360" có thể khớp vào `run_keepz_360`.
- **G2 (kế hoạch, cách đo AC5).** `wc -w` phụ thuộc locale. Trong Git Bash mặc định ra **555** (> 550), vì chế độ byte tách từ
  tại byte 0xA0 của chữ "à". `LC_ALL=C.UTF-8 wc -w` và `str.split()` ra **546**. Con số "508" của vòng 1 cũng là số đếm ở chế
  độ byte (UTF-8: 498). Số đúng là 546 ≤ 550, nhưng chỉ dư 4 từ. Planner nên ghi rõ cách đếm (UTF-8 / `str.split()` như test).
- **G3 (triển khai, câu chữ PROPOSAL dòng 17).** "…rơi vào lớp chỉ-VSL-GH ở 10.9% (69/634) clip QIPEDC": mẫu số là 634 dự đoán
  SAI, không phải mọi clip QIPEDC. PROPOSAL cũng thiếu lưu ý đã có trong REPORT: lớp đúng của S06 thuộc VSL-GH nên lỗi S06 tự
  nhiên rơi vào lớp VSL-GH; và tỷ lệ nền của không gian nhãn không phải một giả thuyết không (null) chuẩn. Dòng đã ghi "chỉ
  báo, không kiểm định", nên không chặn.
- **G4 (quy trình).** `docs/plans/` đang untracked: hợp đồng AC mà REPORT, review và progress_log trỏ tới không có trong git.
  AC6 cho phép commit `docs/plans/`; orchestrator nên commit kế hoạch ở R6.
- **G5 (truy nguồn).** `reports/unified_run_2026-09-25/run_seed43/history.json` untracked nhưng được đọc làm đầu vào (sha256 ở
  REPORT §1.4). Không số nào trong REPORT phụ thuộc file này (chỉ run chọn và run từ điển được dùng `history.json`).
- **G6 (đọc ước lượng cho đúng).** `step_matched_estimate` giả định cùng thời gian/epoch và bỏ qua dừng sớm/giảm lr. Với công
  thức hiện tại, model từ điển sẽ lại dừng sớm. REPORT đã ghi "ước lượng, không phải kết quả". Thí nghiệm "train tới khi khớp"
  cần đổi công thức (không giảm lr / không dừng theo VAL 105 clip), tức là kế hoạch mới.

## Việc phải làm tiếp (không phải FAIL)

1. R6: chạy lại lệnh R3 + `--review-file docs/reviews/01-review.md` (file này) ở HEAD sạch; kiểm AC3 (`cmp` hai lần chạy) và
   AC9 (so với `67ff25a`: chỉ header, dòng inputs của review, §6); chạy lại `tests.test_report_step4`.
2. Cập nhật dòng progress_log: kết luận "APPROVE, vòng 2/3", thêm commit R6.
3. (Tùy chọn) commit `docs/plans/01-buoc4-hoan-tat-4a-4c.md` (G4).

Phân loại: không còn lỗi triển khai hay thiết kế ở mức FAIL. G1, G3 là lỗi triển khai nhỏ; G2, G4 thuộc kế hoạch/quy trình.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **A/B cho 4c.** Coder khuyến nghị B, có điều kiện. Kết quả chính (top-1 12.2% vs 3.2% trên 721 clip, p = 1.06e-14) là
   thật và đúng luật đăng ký, nhưng chỉ nói về model tách train từ đầu và chưa khớp (train top-1 34.21% vs 95.47%, 624 vs
   23226 bước). Nên đọc REPORT mục 4 "Phạm vi so sánh và mức khớp train" trước khi chọn.
2. **Có làm thí nghiệm MỚI trước khi chọn không** (chưa đăng ký trước, tốn GPU): (i) model từ điển train tới khi khớp: ước lượng
   thô ≈ 2.20 giờ GPU mỗi run mỗi seed, cần đổi công thức; (ii) khởi tạo từ trọng số VSL-GH / model gộp rồi fine-tune: cần thêm
   tùy chọn vào `scripts/train_unified.py` và phần đăng ký trước mới. Cần duyệt ngân sách GPU (hạn 10 giờ/tuần).
3. **360 px chỉ có một seed** (+1.72 điểm, trong khi chênh giữa hai seed H-keepz là +1.61): thêm seed trước khi đổi đường
   realtime sang 360 px, hay chấp nhận kết quả theo luật?
4. **Cắt đoạn nghỉ ở đường live:** model được chọn train với trim=true. Giữ bước cắt (khớp model) hay bỏ (phải train lại)?
5. **Việc nhỏ:** `REPORT_partial.md` (untracked): commit, giữ, hay xóa? Thêm `reports/unified_run_*/**/*.pt` vào `.gitignore`?
   Có commit file kế hoạch trong `docs/plans/` không (G4)?

---

# Review 01: Bước 4a → 4c (kế hoạch `docs/plans/01-buoc4-hoan-tat-4a-4c.md`)

Reviewer độc lập, ngày 2026-09-26, nhánh `feat/vslt-complete`, HEAD `8c08845`.
Commit được review:
- Của coder (kế hoạch 01): `72abc13`, `f4729ff`, `8c08845`.
- Trước quy trình 3 agent: `348843f`, `9e3be95`, `a414b0d`, `4bb3811`, `4f4e349`, `27233f6`.

Toàn bộ số liệu dưới đây do reviewer tự chạy lại. Lệnh chạy qua `.venv/Scripts/python`, có `PYTHONIOENCODING=utf-8`.

## Kết luận: **CHANGES_REQUESTED**

Mã, test, luật chọn, truy nguồn và khả năng tái lập đều đạt. Có đúng một FAIL, ở mục 13 (kết luận vượt bằng chứng):
`PROPOSAL_4c.md` khuyến nghị B dựa trên kết quả chính của 4c. Nhưng đề xuất không nói rằng model từ điển **chưa khớp được
chính tập train của nó**, và cũng không nói rằng phương án "A" đã đo chỉ là một cách tách: train từ đầu, chỉ dùng QIPEDC.
Phần sửa không cần GPU.

---

## Bảng 1–13

| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch; mỗi AC có test thật | PASS | `tests/test_report_step4.py`: 38 test, mỗi ca AC1 1–15 có test riêng với assert cụ thể. Ca 8 (`test_selection_does_not_depend_on_test_logits`, dòng 337–351) đảo dấu logits TEST, kiểm test_groups ĐÃ đổi còn selection/trimming KHÔNG đổi, nên không phải test rỗng. Ca 2 (dòng 52–58) đặt tên ngược với `run_config`. Ca 15: exit 1/2/3, kiểm cả hai file không tồn tại (dòng 381–408). AC5: dòng 411–446. Điểm yếu nhỏ: test AC5 chỉ kiểm con số có mặt *ở đâu đó* trong REPORT.md (xem "Góp ý nhỏ"). Reviewer đã kiểm tay: mọi số trong PROPOSAL đều khớp đúng ngữ cảnh. |
| 2 | Tự chạy lại toàn bộ test | PASS | `python -m unittest tests.test_report_step4 -v` → `Ran 38 tests ... OK`, 0 skip. Bộ hồi quy AC2 (10 module) → `Ran 53 tests ... OK`. Commit message 72abc13 ghi 35 test; 8c08845 thêm 3 test AC5, tổng 38, khớp. |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff --stat e62fce3..HEAD -- tests/` → chỉ `tests/test_report_step4.py` (+450, file mới). Các commit trước quy trình không chạm `tests/`. `grep -i skip` chỉ ra tên test và docstring, không có `skipIf`/`skip`. |
| 4 | Nguồn gốc dữ liệu thật | PASS | Log kernel v1/v2/v3: VSL-GH do `prepare_canonical_vsl_gh.py` sinh từ repo gốc (checkout `6c351e6`). QIPEDC là npz MediaPipe trích từ video thật (kernel `vsl-extract-qipedc`, `vsl-extract-qipedc360-s0..s2`, cả 4 COMPLETE theo `kaggle kernels status`). Manifest có 1622 dòng QIPEDC, đủ 1622/1622 file trong cả `data/processed/qipedc_kps` và `qipedc_kps360` (4362 npz mỗi thư mục). Không có dữ liệu sinh. Fixture trong test là fixture unit test, được ghi rõ ở docstring. |
| 5 | Rò rỉ | PASS (có giới hạn đã công bố) | `split_integrity` trong metrics.json: `status PASS`, S01–S04 train, S05 val, S06 test, 1227 recording group QIPEDC. Reviewer tự đếm: 0 video_id và 0 recording_group chung giữa train/val/test. QIPEDC không có signer_id (0/1622) và 100% (1189/1189) đoạn S06 đến từ câu đã thấy trong train. Cả hai đã ghi ở REPORT §5. |
| 6 | Chọn bằng VAL, TEST một lần | PASS | `select()` (report_step4.py:429–435) chỉ nhận `bal` từ `val_by_source`. `choose_z` nhận biến thể đơn giản theo `run_config.hand_z` (dòng 121). Ngưỡng dùng `>=` trên số chưa làm tròn (dòng 131, 147, 166). TEST chỉ đọc lại `test_logits.npz`. Đối chiếu PREREG: dòng 8–10 khớp `balanced_val`+`choose_z`; dòng 11 và 22 khớp `choose_resolution` (so với run z đã chọn, không so với dropz như trước 348843f); dòng 14–15 và 23 khớp `pick_dict_run` (không fallback); dòng 20–21 khớp `trimming_verdict`; dòng 24 khớp: seed43 là aux, có test ca 4. Kết quả: H-keepz − H-dropz = +2.31 → H-keepz; H-keepz-360 − H-keepz = +1.72 → 360; trim −0.28 → không công nhận (`step4_results.json → 4b.selection`, `4b.trimming.val`). |
| 7 | Số liệu truy được | PASS | Chạy lại lệnh ở header REPORT.md, `--out` trỏ vào thư mục tạm, hai lần: exit 0 cả hai lần. Hai lần chạy chỉ khác nhau ở đường dẫn `--out` nằm trong chuỗi lệnh. So với file đã commit, chỉ khác thêm HEAD (`f4729ff` → `8c08845`, vì `git diff f4729ff HEAD -- scripts/ src/` rỗng). Mọi số và sha256 khác đều trùng. Có `code_dirty=false`. Đã kiểm ngẫu nhiên hơn 10 số (xem "Kiểm số độc lập"), tất cả khớp. |
| 8 | Cỡ mẫu và CI | PASS | Mỗi ô có % (k/n) [Wilson 95%], top-1 và top-5. Chéo nguồn n=26 được gắn "CI rất rộng". Giá trị 1 clip QIPEDC VAL là 0.476 điểm, in cạnh ngưỡng. Chênh seed +1.61 in cạnh các chênh dùng để chọn. Không có kết luận nào rút riêng từ nhóm n=26. |
| 9 | Nhất quán train–realtime | PASS (trong phạm vi) | Việc này không chạm đường live. REPORT §5 ghi rằng không file nào trong backend/ hoặc src/inference/ gọi `harmonize()`, và rằng nếu dùng 360 px thì live phải giảm cùng mức và có test tương đương. **Chặn** mọi việc đổi model mặc định sang H-keepz-360 cho tới khi có test tương đương. |
| 10 | Không random/mock/hard-code | PASS | Mã chỉ hard-code hằng số lấy từ PREREG: `THRESHOLD=0.5`, `DIFFERENT_SIGN`. `LEGACY_CONFIG_DEFAULTS={"trim":True}` có lý do kèm diff mã (reviewer kiểm `git diff c8a7bdf c65032a` thấy chỉ THÊM cờ `--no-trim`, mặc định giữ nguyên). `np.random` duy nhất nằm ở `shortcut_85.py:39` (lấy mẫu cân bằng có seed). Chuỗi "không TTA": reviewer kiểm `predict_all` (train_unified.py:102), chỉ một lượt. |
| 11 | Bảo mật | PASS | Không có token, khóa hay `kaggle.json` trong diff. `kernel-metadata.json` có `is_private: true`. Không commit `*.pt`/`*.npz`/`*.log`. Không đụng API, CORS hay WS. Góp ý: `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` đang untracked nhưng KHÔNG bị gitignore (quy tắc `.gitignore:75` chỉ phủ `step4_*`), nên dễ bị commit nhầm. |
| 12 | So sánh công bằng | PASS | Mọi run được đo trên cùng manifest TEST 1911 clip. 4c dùng cùng 721 clip, reviewer tự tính lại. Ngưỡng 0.5 không bị nới. Addendum PREREG (`9b0ade1`, 12:13:24) được commit TRƯỚC mọi kết quả 360/notrim/4c (`a414b0d` 13:37, `4f4e349` 15:14, `27233f6` 19:33) và SAU kết quả v1 (`c9296bf` 12:12:25). REPORT đã ghi điều này. Về quỹ huấn luyện không cân bằng của model từ điển: xem mục 13. |
| 13 | Kết luận vượt bằng chứng | **FAIL** | Xem "Việc phải sửa" M1. `runs/dict_keepz_360/history.json` (đã commit) cho thấy model từ điển dừng ở epoch 48, train top-1 **34.21%**, lr đã giảm còn 1.5625e-05, VAL QIPEDC tốt nhất 3.81%. Model gộp `run_keepz_360` đạt train top-1 95.47%. Model từ điển chỉ có khoảng 795/64 ≈ 13 bước/epoch, tức khoảng 600 bước; model gộp có khoảng 237 bước/epoch × 98 epoch. Vậy 4c đo "model tách, train từ đầu bằng công thức của model gộp và chưa khớp tập train" so với model gộp; 4c chưa đo "tách vs gộp" nói chung. PROPOSAL không nói điều này và viết "Tách ra thì 'Ký từ' mất toàn bộ dữ liệu VSL-GH". Câu đó chỉ đúng với cách tách train-từ-đầu. |

---

## Kiểm theo AC của kế hoạch

| AC | Kết quả | Ghi chú |
|---|---|---|
| AC1 | PASS | 38/38 OK, đủ 15 ca. |
| AC2 | PASS (số) / CHƯA XONG (ghi log) | 53 test OK, cùng 10 module handoff. `docs/progress_log.md` chưa có dòng của kế hoạch 01 và chưa ghi số trước/sau (Bước 8 còn lại). |
| AC3 | PASS | Tái lập như mục 7. Lưu ý thiết kế: `--out` nằm trong chuỗi lệnh được ghi lại, nên chạy ra thư mục tạm thì không bao giờ `cmp` byte-giống được. Coder đã so hai lần chạy tại chỗ. Reviewer so ra thư mục tạm: chỉ khác đường dẫn và HEAD. |
| AC4 a–i | PASS | a: 9 run đều có commit, lệnh, seed (baseline lấy từ `vsl-train-unified.log`, b4916b9), có sha256 và thời lượng kernel. b: 3 JSON cũ "chạy lại trùng: CÓ". c: 2.31 / 1.72 / 0.476 / +1.61. d: 4 nhóm × top-1/top-5 với k/n và CI, loại 0 clip. e: (i)(ii)(iii). f: seed cho H-keepz và baseline. g: khối cấu hình sinh từ ckpt và `HARMONIZED_DEFAULT`. h: một so sánh chính, dict_keepz chỉ nêu tên. i: đủ ý §3.4 mục 6. |
| AC4 j | CHƯA XONG | §6 Review hiện ghi "Chưa có kết quả". Cần sinh lại với `--review-file` sau khi sửa M1. |
| AC5 | PASS (test) / FAIL (nội dung, M1) | 508 từ; một khuyến nghị; có "người dùng quyết định"; đủ ý giới hạn; mọi số đều có trong REPORT. |
| AC6 | PASS | `git diff --stat 27233f6..HEAD` chỉ gồm các file được phép. Không đổi backend/, src/, configs/, frontend/, PREREG, JSON 4a/4b cũ, data/. 3 file data bị xóa của người dùng vẫn chưa commit. |
| AC7 | Chờ | Phụ thuộc M1. |
| AC8 | PASS có lưu ý | 72abc13 có kết quả `impact`. Nhưng cả 3 commit ghi `detect-changes --scope staged`, trong khi kế hoạch và CLAUDE.md yêu cầu `--scope all`. Không có lệnh Kaggle push. |

## Commit trước quy trình 3 agent

| Commit | Kết quả | Bằng chứng |
|---|---|---|
| 348843f | PASS (đã được thay thế) | Sửa đúng lỗi so 360 với dropz; aux không được chọn; 4c theo độ phân giải. Điểm yếu còn lại: nhận biến thể theo **tên** (`"dropz" in k`, `"notrim" in k`), trim ghép theo tên. 72abc13 đã chuyển sang `run_config` và có test ca 2 và ca 6. REPORT hiện tại sinh bằng mã mới, nên không có số nào đến từ logic cũ. |
| 4bb3811 | PASS | Ghi `command` và `git_commit` (HEAD `--short`). Giới hạn "không ghi trạng thái bẩn" có trong REPORT §5. |
| 9e3be95 | PASS | JOBS v3 khớp log v3 (entry 13, 14, 79): so với v1 chỉ khác `--no-trim` hoặc `--process-height 360` + `--data-root /tmp/root_360`; seed 42. `root_360` chỉ thay npz QIPEDC (log: 4362 npz từ 3 shard), `vslgh_segments` dùng chung. `dict_keepz_360` = `--sources qipedc --process-height 360`, khớp `run_config`. |
| a414b0d / 27233f6 | PASS | Log kernel chỉ in 30 dòng cuối metrics.json. Reviewer so 30 dòng đó với file trên đĩa cho cả 7 run: trùng 7/7. Không kiểm được `val_by_source` từ log vì log không in khóa này. Thay vào đó reviewer kiểm tính nội tại: VAL tổng tại epoch tốt nhất trong `history.json` = (k_vslgh + k_qipedc)/1295 cho mọi run, ví dụ 360: (899+21)/1295 = 71.04 = `val_best.top1`. `test_overall.top1` = độ chính xác tính từ `test_predictions.csv` (7/7). `video_id` của npz = của predictions (7/7). |
| 4f4e349 | PASS | JSON 360 có `command` và `git_commit 4bb3811` (commit 1 giây trước). `qipedc_kps360` có đủ 1622/1622 file của manifest. |

## Kiểm số độc lập (không qua report_step4.py)

Tính từ file đã commit (`metrics.json`, `history.json`, `test_predictions.csv`, fp32 của kernel):
- Balanced VAL: H-keepz (74.958+17.143)/2 = 46.05; H-dropz 43.74; H-keepz-360 47.77; seed43 47.66; notrim 46.33. Khớp REPORT §3.2.
- 4c trên 721 clip chung (`test_predictions.csv`): từ điển top-1 23, top-5 70; gộp top-1 88, top-5 185; n10=7, n01=72, `binomtest` p = 1.059e-14. Khớp REPORT §4.
- S06 top-1: H-keepz 936, notrim 940. Khớp §3.4(ii).
- Thời lượng kernel v3: 6573.6 s và "total 109.4 min". Khớp log.
- 1 clip QIPEDC VAL = 100/210 = 0.476. Khớp.

---

## Việc phải sửa (xếp theo mức độ)

**M1 (CAO, FAIL mục 13). Loại: thiết kế/tiêu chí (kế hoạch §3.4 không yêu cầu chẩn đoán độ khớp train) cộng triển khai (câu chữ PROPOSAL).**
1. `scripts/report_step4.py`: thêm vào mục 4c (và `step4_results.json`), lấy từ `history.json` của cả hai model: số epoch đã chạy, epoch tốt nhất, train top-1 ở epoch cuối, lr cuối, và số bước tối ưu ước lượng (clip train / batch × epoch). Sinh từ file, không gõ tay. Thêm test cho hàm này.
2. `PROPOSAL_4c.md`:
   - Nêu trong "Bằng chứng chống B / Giới hạn" rằng model từ điển chưa khớp tập train (số lấy từ REPORT mới). Vì vậy 4c chỉ cho thấy model tách train-từ-đầu bằng công thức hiện tại kém hơn; 4c không loại trừ phương án A.
   - Sửa câu "Tách ra thì 'Ký từ' mất toàn bộ dữ liệu VSL-GH" thành câu có phạm vi, vì A vẫn có thể khởi tạo từ trọng số VSL-GH hoặc model gộp rồi fine-tune trên QIPEDC.
   - Thêm vào "Điều gì sẽ làm đổi khuyến nghị": một model từ điển train tới khi khớp (cùng số bước, hoặc không giảm lr theo VAL 105 clip), hoặc khởi tạo từ trọng số VSL-GH, mà đạt ngang hay hơn model gộp trên 721 clip. Thí nghiệm này tốn GPU nên phải là kế hoạch mới.
   - Test AC5 phải vẫn qua.

**M2 (TRUNG BÌNH). Loại: thiết kế (PREREG không nói hệ quả).** REPORT §3.4 kết luận "cắt đoạn nghỉ KHÔNG được công nhận" nhưng không nói rằng run được chọn (`H-keepz-360`, `trim=true`) vẫn cắt nghỉ, và đường live sẽ phải cài `harmonize()` gồm cả bước cắt. Cần một câu sinh từ `chosen_run_config`. Có quyết định kèm theo, xem "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH".

**M3 (THẤP). Loại: triển khai.** Thăm dò (b): tỷ lệ "rơi vào lớp chỉ-VSL-GH" bị trộn với độ chính xác, vì dự đoán đúng thì tự nhiên rơi vào lớp của nguồn đó. Nên thêm cột "chỉ tính dự đoán sai". Reviewer tính từ `run_keepz_360/test_predictions.csv`: QIPEDC sai → lớp chỉ-VSL-GH 69/634 (10.9%); S06 sai → lớp chỉ-VSL-GH 183/225 (81.3%); tỷ lệ lớp chỉ-VSL-GH trong không gian nhãn 282/876. Kết quả này *ủng hộ* giả thuyết mạnh hơn bảng hiện tại, nhưng phải do script sinh ra thì REPORT mới được dùng.

**M4 (THẤP, quy trình).** Hoàn tất Bước 7–8: sinh lại REPORT với `--review-file`, ghi progress_log gồm số test trước/sau (53 → 53; test_report_step4 thêm 38), và chạy `detect-changes --scope all` thay cho `--scope staged`.

### Góp ý nhỏ (không chặn)
- Test AC5 (`test_every_number_is_in_report`) chỉ kiểm con số có mặt ở đâu đó trong REPORT. Số nguyên như "12" có thể khớp nhầm vào sha256 hex. Nên so theo ngữ cảnh, ví dụ cả cụm "% (k/n)".
- `REPORT_partial.md` đang **untracked**. Kế hoạch ghi "@3698e91" là sai (3698e91 chỉ sửa handoff). File này không có bản git để bảo đảm "giữ nguyên".
- Tiêu đề phần bổ sung trong PREREG ghi "12:30" nhưng commit `9b0ade1` lúc 12:13:24. Không sửa PREREG được. REPORT §5 đã in ngày commit; nên thêm một câu nêu điểm lệch này.
- Khối "Augmentation" trong REPORT §3.1 lặp chữ ("Augmentation: Augmentation (training only)").
- Nên thêm `reports/unified_run_*/**/*.pt` vào `.gitignore` (mục 11).

---

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **A/B cho 4c** (điểm dừng bắt buộc). Nên quyết sau khi PROPOSAL được sửa theo M1. Lý do: kết quả chính (12.2% vs 3.2%, p = 1.06e-14) là thật và theo đúng luật đăng ký, nhưng model từ điển dùng trong so sánh chưa khớp tập train. Có muốn một kế hoạch mới (tốn GPU) train model từ điển tới khi khớp hoặc khởi tạo từ VSL-GH trước khi chọn không?
2. **360 px**: theo luật thì được chọn (+1.72 điểm balanced VAL). Nhưng chênh giữa hai seed của cùng cấu hình H-keepz là +1.61 điểm, và run 360 chỉ có một seed. Chọn 360 kéo theo phải đổi đường realtime (giảm độ phân giải trước MediaPipe cộng test tương đương). Luật đã đăng ký được áp đúng; người dùng cần biết mức chắc chắn thấp trước khi duyệt thay đổi realtime.
3. **Cắt đoạn nghỉ** (M2): luật VAL không công nhận cắt nghỉ (−0.28), nhưng mọi run ứng viên đều cắt. Khi nối `harmonize()` vào đường live, giữ bước cắt (đúng với model đã train) hay bỏ (phải train lại)? PREREG không quy định.
