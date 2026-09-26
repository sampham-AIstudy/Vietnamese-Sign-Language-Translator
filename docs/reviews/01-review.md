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
