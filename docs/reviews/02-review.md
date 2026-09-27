# Vòng 3

- Commit review: f2b7c5b (A6), 7643a12 (C3), eaa48e1 (B''), nối tiếp 72bc1b1. HEAD `eaa48e1`.
- Kế hoạch: `docs/plans/02-don-dep-sau-4c.md` (§0b Lần sửa 2; T0–T5; AC1 ca 28–32; AC2, AC5b, AC8, AC9', AC10).
- Reviewer: vslt-reviewer, vòng 3/3 (cuối), ngày 2026-09-27. Tôi tự chạy lại mọi lệnh. Không di chuyển hay xóa file thật: mọi thực
  nghiệm "thiếu file" dùng `unittest.mock.patch` hoặc đổi đường dẫn trong đối số sang thư mục tạm. Kaggle chỉ dùng lệnh đọc.
  Sau khi vòng này được ghi, sha256 của `docs/reviews/02-review.md` trong REPORT §1.4 sẽ cũ; bước T5 (C4, C5) sinh lại. Đó không
  phải lỗi của B''.

**Kết luận vòng 3: APPROVE.** Không còn FAIL. FAIL mục 13 của vòng 2 đã được sửa thật. Phân loại bắt buộc/tùy chọn lấy từ chính các
chỗ gọi `Inputs.add` trong mã, không gõ tay. REPORT in 5 bắt buộc / 3 tùy chọn, khớp thực nghiệm của tôi trên dữ liệu thật với cả
8/8 file. Câu Giới hạn đúng cho cả hai nhóm và không vượt bằng chứng.

## Bảng 1–13 (vòng 3, HEAD eaa48e1)

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | Ca 28 `TestInputsRequired`: phép OR theo cả hai thứ tự; `as_list` giữ 3 khóa. Ca 29 `TestRequiredOptionalBehaviour`: với MỖI file trong danh sách, giả lập thiếu bằng `mock.patch` (`os.path.isfile`/`exists`), rồi kiểm bắt buộc → `main` = 2 và không ghi file; tùy chọn → 0 và thân REPORT khác. Không động đĩa: có assert file thật trong repo vẫn còn. Ca 30: vị trí từng path theo nhóm, nhóm rỗng in "không có". Ca 31a: `--literal-pathspecs` đứng trước `ls-files`. Ca 32: file thật. Đột biến trong bộ nhớ: mọi `add` thành bắt buộc → 29 FAIL; mọi `add` thành tùy chọn → 29 FAIL; đảo nhóm trong câu → 30 FAIL; bỏ cờ literal trong `git_tracked` → 31a FAIL. Riêng 31b không phân biệt được: không có cờ literal thì kết quả vẫn rỗng, vì `git_tracked` lọc theo tên chính xác. Chỉ 31a canh cờ này (không chặn). |
| 2 | Tự chạy lại test | PASS | `unittest tests.test_archive_step4_kaggle tests.test_report_step4 -v`: `Ran 129 tests OK`, 0 skip/FAIL/ERROR (24 + 105; `test_report_step4` từ 99 lên 105, +6 ≥ +5). AC2 (10 module): `Ran 53 OK`. `git status --porcelain` trước và sau khi chạy toàn bộ test giống hệt (`cmp`). Các file thật (`checkpoints/*.pt`, `segments.csv`, `run_seed43/history.json`, log kernel) vẫn còn. |
| 3 | Test không bị sửa/nới | PASS | `git diff 72bc1b1 HEAD -- tests/` và `git diff 09d4057 HEAD -- tests/`: 0 dòng `-` ngoài header. Mọi lớp test cũ (ca 14, 19, 23–27, G1–G3) không đổi và vẫn qua. |
| 4 | Nguồn dữ liệu | PASS | Không có dữ liệu mới. `git diff 72bc1b1 HEAD -- reports/step4_2026-09-26/archive/` rỗng. |
| 5 | Rò rỉ | PASS (không áp dụng) | AC5: JSON HEAD `==` JSON tại P sau khi bỏ các khóa §5 → `True`. |
| 6 | VAL/TEST | PASS (không áp dụng) | Vẫn chọn `H-keepz-360`. |
| 7 | Số liệu truy được | PASS | Chạy lệnh ở header (HEAD 7643a12) hai lần, đổi out sang thư mục tạm: exit 0 cả hai lần. Hai lần chạy giống nhau, trừ đường dẫn out. Thân REPORT giống bản commit. JSON bằng bản commit, trừ `generated_by.command`/`git_commit`. `git diff 7643a12 HEAD -- scripts src tests` rỗng; `code_dirty=false`. sha256 của review 02 trong JSON (`34c40318…`) bằng file đã commit ở 7643a12. AC5b: JSON 72bc1b1 `==` B'' (bỏ generated_by/review/input review/`untracked_unarchived_inputs`). Tập path, `n`, `n_inputs` bằng nhau (8, 58). REPORT chỉ đổi dòng 4 (HEAD), dòng 86 (§1.4 review 02), dòng 408 (Giới hạn) và phần sau `## 6. Review`. |
| 8 | Cỡ mẫu | PASS (không áp dụng) | Không có thống kê mới. |
| 9 | Train–realtime | PASS (không áp dụng) | backend/src/configs/frontend không đổi. |
| 10 | Mock/hard-code | PASS | Mock chỉ có trong test. Cờ `required` đặt tại các chỗ gọi, và chỉ ở 3 chỗ mã đã kiểm tồn tại rồi bỏ qua khi thiếu: `history.json` của run ngoài `(chosen, used_dict)`, checkpoint mặc định của backend, `segments`. Tôi đọc mọi chỗ gọi `inputs.add`/`load_json` khác (`scripts/report_step4.py:680-716, 721, 885, 956`): đều không có điều kiện, nên bắt buộc là đúng. |
| 11 | Bảo mật | PASS | Không có lệnh Kaggle nào trong Lần sửa 2: `../_kaggle_staging/*.out` mới nhất vẫn là 17:56. Lệnh đọc của tôi: `dataset_list(mine)` → `is_private=True`, version 1, `last_updated` không đổi; gọi ẩn danh `datasets/view` → 403. Grep `KGAT_`/`"key"` trên diff 09d4057..HEAD, commit message và tên file: 0. |
| 12 | Công bằng, không nới | PASS | Planner chỉ thêm tiêu chí: ca 28–32, AC5b, "git status không đổi sau test". Khóa mới `n_required`/`n_optional` nằm trong khóa đã được bỏ khi so với P. Không nới AC cũ. |
| 13 | Kết luận vượt bằng chứng | PASS | REPORT dòng 408: "8/58 … Bắt buộc (5; thiếu thì scripts/report_step4.py dừng với mã 2): `checkpoints/stgcn_unified_best.pt`, 4 log kernel. Tùy chọn (3; thiếu thì script vẫn chạy nhưng bỏ phần dùng file đó hoặc ghi null, nên báo cáo khác đi mà không báo lỗi): `checkpoints/stgcn_tier2_indomain.pt`, `data/processed/vslgh_segments/segments.csv`, `reports/unified_run_2026-09-25/run_seed43/history.json`. Vì vậy kể cả khi có quyền truy cập dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo." Đã bỏ vế "Thiếu một đầu vào thì…". Thực nghiệm trên dữ liệu thật (AC10): (a) lệnh header, đổi `--kernel-logs …_v3.log` sang file không tồn tại trong thư mục tạm → **exit 2**, không ghi file; (b) `--segments <không tồn tại>` → **exit 0**, REPORT in "Bắt buộc (5;" / "Tùy chọn (2;"; (c) với cả 8 file, gọi `R.main(<lệnh header>)` trong `missing_patch(path)`: 5 file nhóm bắt buộc → exit 2, không ghi file; 3 file nhóm tùy chọn → exit 0, REPORT khác. **Khớp 8/8** với nhóm REPORT in, và khớp thực nghiệm vòng 2 (5/3). |

## Kiểm tra riêng vòng 3

- **Inputs / Inputs.add, impact UNKNOWN.** GitNexus: `Inputs` UNKNOWN (không resolve được caller); `add` LOW lower-bound (caller: build).
  `load_json`, `untracked_unarchived_inputs`, `git_tracked` LOW/exact (build); `archive_limit_line` LOW/exact (render). Text search:
  `Inputs()` chỉ xuất hiện ở `scripts/report_step4.py:678` (build) và `tests/test_report_step4.py:1231`. Chỉ `tests/test_report_step4.py`
  import `report_step4`. Các kết quả grep "Inputs" khác chỉ là chữ trong docstring (`kaggle/*_kernel.py:3`, `src/models/baseline_bigru.py:5`).
  `detect-changes --scope compare --base-ref 72bc1b1`: 9 file (gồm 3 file data của người dùng), MEDIUM, 2 luồng `Main → {Rel, Sha256}`
  (đổi: build, add), đều trong `scripts/report_step4.py`. Tham số mới `required` mặc định `True`, nên mọi lời gọi cũ giữ nguyên hành vi.
  `as_list()` không đổi, và khóa của JSON `inputs` vẫn là `path, role, sha256`.
- **`--literal-pathspecs`:** có ở `git_tracked`, ca 31a kiểm.
- **Phạm vi (AC7):** Lần sửa 2 chỉ đổi `scripts/report_step4.py`, `tests/test_report_step4.py`, REPORT/JSON, và commit review + kế hoạch.
  Không đổi manifest, `archive_step4_kaggle.py`, `.gitignore`, PROPOSAL, `01-review.md`, backend/src/configs/frontend/data.
  Ba file data của người dùng vẫn ở trạng thái ` D`. Review vòng 2 ở 7643a12 giống hệt bản tôi viết (sha256 `34c40318…`).
- **Chưa đến hạn (T5, không tính ở vòng này):** C4/C5, AC9', và cập nhật progress_log (AC8): cột "kết luận review" đang ghi
  "vòng 2: chờ vslt-reviewer" cần đổi thành lịch sử 3 vòng; thêm `n_required=5`/`n_optional=3`; thêm "Lần sửa 2 không chạy lệnh Kaggle nào".
- **Không chặn:** ca 31b không phân biệt được việc có hay không có `--literal-pathspecs` (chỉ 31a canh). Nếu muốn chặt hơn, thêm ca
  dùng một file tạm có tên chứa `[`, nhưng việc này ngoài phạm vi kế hoạch.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH (vòng 3)

1. **A3 (§7.1, vẫn chờ).** `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` vẫn được git track (thêm ở 429b289,
   đã có trên `origin/fix/audit-round2`). File này train trên bộ hauuto, giấy phép chưa rõ. Chọn (a) giữ; (b) lưu vào Kaggle dataset
   private (kế hoạch nhỏ riêng) rồi `git rm --cached`; (c) `git rm --cached` không lưu trữ. Không cách nào xóa được file khỏi lịch
   sử đã push.
2. **§7.2 (không chặn).** Có lưu thêm 4 log kernel (nhóm bắt buộc), `run_seed43/history.json`, và nếu được phép thì `segments.csv`
   và `checkpoints/*.pt` vào dataset private (version mới, kế hoạch riêng) không? Nếu lưu đủ 5 file bắt buộc thì người có quyền dataset
   chạy lại được script; nhưng thiếu file tùy chọn thì báo cáo vẫn khác.
3. **Không bắt buộc.** PROPOSAL_4c.md đã sửa câu chữ sau khi người dùng quyết B (dòng 6, 11, 17, 32); nội dung quyết định không đổi.

---

# Vòng 2

- Commit review: 514ad47 (A5), ae82625 (B'), 208fc5f (C1), 72bc1b1 (C2), nối tiếp 12ef791. HEAD `72bc1b1`.
- Kế hoạch: `docs/plans/02-don-dep-sau-4c.md` (Lần sửa 1, §0; AC1 ca 21–27; AC2, AC5, AC8, AC9 cập nhật).
- Reviewer: vslt-reviewer, vòng 2/3, ngày 2026-09-27. Tôi tự chạy lại mọi lệnh. Kaggle chỉ dùng lệnh đọc.
  `docs/reviews/02-review.md` sẽ được sinh lại theo R5.2 sau vòng này, vì vậy sha256 của file này trong REPORT §1.4 hiện đã cũ.
  Đó không phải lỗi của lần sinh 72bc1b1.

**Kết luận vòng 2: CHANGES_REQUESTED (mức thấp).** FAIL của vòng 1 đã được sửa thật. Câu Giới hạn giờ sinh từ inputs × git × manifest.
Danh sách 8 file khớp số tôi tự đếm. Câu vẫn giữ ý "sha256 ở §1.4 là bằng chứng thay thế" và nói rõ "kể cả khi có quyền truy cập
dataset… vẫn KHÔNG tái tạo được". Vẫn còn một FAIL nhỏ ở mục 13, lỗi gốc thuộc thiết kế: vế "Thiếu một đầu vào thì
scripts/report_step4.py dừng với mã 2" là khẳng định phổ quát, và tôi đã chứng minh bằng thực nghiệm là nó sai với 3/8 file.
Kết luận chính của câu (clone sạch không tái tạo được báo cáo) vẫn đúng. Xem mục "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH" (a/b).

## Bảng 1–13 (vòng 2, HEAD 72bc1b1)

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | Ca 21 nằm ở `TestUntrackedUnarchivedInputs`. Ca 22 ở `TestGitTracked`: 22a đếm đúng 1 lời gọi `ls-files` và không truyền đường dẫn ngoài repo; 22b/22c kiểm mã 2 và không ghi file. Ca 23–26 ở `TestLimitationUntrackedInputs`, ca 27 ở `TestRealReportUntrackedInputs` (đọc file thật, tự gọi `git ls-files -z`, không skip). Đột biến trong bộ nhớ, không sửa file: đưa lại câu cũ → 23 FAIL; bỏ một đường dẫn khỏi câu → 23 FAIL; không trừ tập archived → 23 FAIL; nhánh n==0 thêm "tái tạo được" → 24 FAIL; `git_tracked` luôn trả rỗng → 22a FAIL. Câu §1.5 khớp nguyên văn §3.3 (REPORT dòng 164). |
| 2 | Tự chạy lại test | PASS | `unittest tests.test_archive_step4_kaggle tests.test_report_step4 -v`: `Ran 123 tests OK`, 0 skip/FAIL/ERROR (24 + 99). AC2 (10 module): `Ran 53 tests OK`. `test_report_step4`: 88 → 99 (+11 ≥ +7). `test_archive_step4_kaggle` giữ 24. Khớp progress_log. |
| 3 | Test không bị sửa/nới | PASS | `git diff 12ef791 HEAD -- tests/` và `git diff 09d4057 HEAD -- tests/`: 0 dòng `-` ngoài header. Hai tham số `make_fixture(dict_runs=)` và `argv_for(dict_runs=)` đã có từ trước (12ef791:261, 320). Test cũ, gồm cả ca 14 và 19, không đổi và vẫn qua. |
| 4 | Nguồn dữ liệu | PASS | Không có dữ liệu mới, không train. Manifest không đổi (`git diff 12ef791 HEAD -- reports/step4_2026-09-26/archive/` rỗng). |
| 5 | Rò rỉ | PASS (không áp dụng) | AC5: JSON HEAD `==` JSON P sau khi bỏ các khóa §5 AC5 → `True`. |
| 6 | VAL/TEST | PASS (không áp dụng) | Vẫn chọn `H-keepz-360`, không chọn lại model. |
| 7 | Số liệu truy được | PASS | Chạy lại lệnh ở header (HEAD 208fc5f, hai `--review-file` + `--archive-manifest`) hai lần, đổi out sang thư mục tạm: exit 0 cả hai lần. Hai lần chạy giống nhau, trừ đường dẫn out. Thân REPORT (bỏ dòng 3–4) giống bản commit. JSON bằng bản commit, trừ `generated_by.command`/`git_commit`. `git diff 208fc5f HEAD -- scripts src tests` rỗng; `code_dirty=false`. AC5 12ef791 ↔ B': JSON `==` (bỏ `generated_by` + khóa mới); REPORT chỉ đổi dòng 4, 163, 407. AC9 B' ↔ C2: JSON `==` (bỏ generated_by/review/input review/`n_inputs`); REPORT chỉ đổi header, dòng §1.4 của review 02, `8/57` → `8/58` (phần còn lại của dòng Giới hạn giống hệt), và §6 (review 02 ở dòng 412, trước review 01 ở dòng 514). |
| 8 | Cỡ mẫu | PASS (không áp dụng) | Không có thống kê mới. |
| 9 | Train–realtime | PASS (không áp dụng) | backend/src/configs/frontend không đổi. |
| 10 | Mock/hard-code | PASS | Danh sách sinh từ `inputs.as_list()` × `git ls-files -z` × `manifest.files[*].local_path` (`scripts/report_step4.py` hàm `git_tracked`, `untracked_unarchived_inputs`, `archive_limit_line`). Không có đường dẫn gõ tay. |
| 11 | Bảo mật | PASS | Kiểm lại bằng lệnh đọc: `dataset_list(mine)` → `is_private=True`, `current_version_number=1`, `last_updated` 10:48:19Z (không đổi từ vòng 1); gọi ẩn danh `datasets/view` → 403. Credential: grep `KGAT_`/`"key"` trên diff 09d4057..HEAD và trên commit message: 0. Lần sửa 1 không chạy lệnh Kaggle ghi. |
| 12 | Công bằng, không nới | PASS | Planner chỉ THÊM khóa và số mới (`untracked_unarchived_inputs`, `n_inputs`) vào danh sách được bỏ ở AC5/AC9, kèm lý do. Danh sách file và `n` vẫn phải bằng nhau, nên không nới. |
| 13 | Kết luận vượt bằng chứng | **FAIL (mức thấp, thiết kế)** | Đã sửa được: REPORT dòng 408 liệt kê đúng 8/58 đầu vào vừa không track vừa không nằm trong lưu trữ. Tôi tự tính từ `inputs` × `git ls-files` × manifest và ra đúng 8 file, trùng danh sách vòng 1: 4 log kernel, `data/processed/vslgh_segments/segments.csv`, `checkpoints/stgcn_tier2_indomain.pt`, `checkpoints/stgcn_unified_best.pt`, `reports/unified_run_2026-09-25/run_seed43/history.json`. sha256 của cả 8 file khớp `inputs`. Câu có "bằng chứng thay thế cho các file này là sha256 ở mục 1.4" và "kể cả khi có quyền truy cập dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo". §1.5 dòng 164 không còn "Chỉ chủ dự án". **Còn sai:** vế "Thiếu một đầu vào thì scripts/report_step4.py dừng với mã 2" chỉ đúng với 5/8 file (4 log kernel qua `inputs.add` ở dòng 689; `checkpoints/stgcn_unified_best.pt` qua `inputs.add(cur_ckpt)` không điều kiện). Với 3 file còn lại, script vẫn chạy và sinh báo cáo KHÁC mà không báo lỗi: (i) `segments.csv` được đọc chỉ khi `os.path.isfile` (dòng 1065). Tôi chạy lại lệnh header với `--segments <không tồn tại>`: **exit 0**, REPORT ghi `7/57`, khác bản commit 5 dòng. (ii) `checkpoints/stgcn_tier2_indomain.pt` chỉ được thêm khi file có (dòng 1055). (iii) `history.json` của run phụ `baseline-seed43` → `null`, không lỗi (dòng 722–731, chỉ run được chọn và run từ điển dùng ở 4c mới bắt buộc). Kết luận "không tái tạo được" vẫn đúng. Nhưng câu này nói quá khả năng tự phát hiện thiếu file của script: thiếu 3 file kia thì báo cáo lặng lẽ khác đi. Câu này là chữ cố định do planner chốt ở §3.3, nên đây là lỗi thiết kế. |

## Kiểm tra riêng vòng 2

- **detect-changes HIGH ở 514ad47.** `detect-changes --scope compare --base-ref 12ef791`: 10 file (gồm 3 file data của người dùng),
  76 symbol (chủ yếu Section Markdown của kế hoạch/review/REPORT và test mới), 6 luồng: `Main → {Rel, Sha256, Fr, Fv, Na, Yn}`,
  đều thuộc `scripts/report_step4.py`. `impact -f scripts/report_step4.py` (upstream): `git_tracked`, `untracked_unarchived_inputs`,
  `archive_limit_line` LOW/exact (caller lần lượt build, build, render); `build` LOW/exact; `render` LOW lower-bound; `git` LOW/exact
  (caller: build, git_added, git_commit_info, git_tracked; tất cả trong cùng file). Text search `git grep` tên 3 hàm mới và
  "report_step4" trên py/js/ts/sh/yml ngoài 2 script + 2 test: rỗng. Phạm vi: chỉ trong `scripts/report_step4.py`.
- **progress_log (AC8), `docs/progress_log.md:47-54`.** Có đúng một dòng bảng cho kế hoạch 02 với đủ các hash. Lịch sử lệnh Kaggle
  khớp log ngoài repo (`../_kaggle_staging/*.out`, theo mtime): upload.out 17:40:41 (403 GetDatasetStatus, exit 6),
  upload2.out 17:44:27 (Errno 2, exit 6), upload3.out 17:48:00 (`created … (private)`, exit=0), verify.out 17:48:52
  (404 DownloadDataset, exit 6), verify2.out 17:56:50 (exit 0). Không kiểm được lần `stage` (không có file log) và các lệnh
  chỉ đọc của coder (`config view`, `datasets status` ×3), nên đánh dấu UNVERIFIED, không chặn. `current_version_number=1` khớp việc
  không có `datasets version`. A3: `alphabet_real_best.pt` được thêm ở 429b289, có trong `origin/fix/audit-round2`, tôi đã xác nhận.
  Số test trước → sau (53/53/53; 69/88/99; 24/24) khớp số tôi đo. Cột "kết luận review" đang ghi "vòng 2: chờ vslt-reviewer",
  orchestrator cần cập nhật theo kết luận này. Định dạng: có thêm một dòng tiêu đề bảng lặp lại; chấp nhận được.
- **Phạm vi (AC7).** `git diff --stat 09d4057..HEAD`: 12 file, đều thuộc danh sách AC7. Lần sửa 1 không đổi
  `scripts/archive_step4_kaggle.py`, manifest, PROPOSAL, `01-review.md`, backend/src/configs/frontend/data. Ba file data của người
  dùng vẫn ở trạng thái ` D`.
- **Nhận xét không chặn.** (1) `git_tracked` truyền đường dẫn cho `git ls-files` dưới dạng pathspec. Đường dẫn có `*`, `?` hoặc `[`
  sẽ bị hiểu là glob; hiện không có đầu vào nào như vậy, nhưng nên dùng `--literal-pathspecs`. (2) Ca 27 phụ thuộc trạng thái git
  lúc chạy test. Đó là chủ ý (§6), nhưng sau này commit/gỡ track một đầu vào sẽ làm ca 27 FAIL cho tới khi sinh lại REPORT.

## Việc phải sửa (vòng 2)

1. **[Thiết kế → triển khai, mục 13, mức thấp]** Planner sửa chữ cố định ở §3.3 cho vế cơ chế. Ví dụ: "Thiếu các đầu vào này thì
   scripts/report_step4.py dừng với mã 2 hoặc bỏ qua phần dùng chúng (giá trị thành null), nên kể cả khi có quyền truy cập
   dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo." Cũng có thể tách danh sách thành "bắt buộc (mã 2)" và "tùy chọn (báo cáo khác
   đi)", nhưng phải sinh từ dữ liệu, không gõ tay. THÊM test: câu không khẳng định mọi file thiếu đều cho mã 2, hoặc kiểm phân loại.
   Không sửa test cũ. Ca 23 hiện kiểm cụm "mã 2", nên cụm "mã 2" phải còn trong câu mới.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH (vòng 2)

1. **Mục 13 còn lại (chọn một).** (a) Làm vòng CODE↔REVIEW thứ 3 để sửa vế "dừng với mã 2" như trên. Tốn khoảng 0.5 giờ, không dùng
   GPU, không chạy lệnh Kaggle. (b) Chấp nhận câu hiện tại, ghi lỗi này vào progress_log là giới hạn đã biết. Kết luận chính của câu
   vẫn đúng: clone sạch không tái tạo được. Reviewer đề xuất (a), vì đây là mục "Giới hạn" (DoD 9).
2. **A3 (§7.1, vẫn chờ).** `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` vẫn được git track, thêm ở
   429b289 và đã có trên `origin/fix/audit-round2`, nên đã nằm trên remote. `git rm --cached` không xóa được nó khỏi lịch sử đã push.
   Chọn (a) giữ, (b) lưu trữ private rồi `git rm --cached`, hoặc (c) `git rm --cached`.
3. **§7.2 (không chặn).** Có lưu thêm 4 log kernel, `run_seed43/history.json`, và nếu được phép thì `segments.csv` và
   `checkpoints/*.pt` vào dataset private (version mới, kế hoạch riêng) không? Khi đó danh sách trong câu Giới hạn tự ngắn lại.

---

# Review 02: Dọn dẹp sau 4c (.gitignore, lưu trữ Kaggle, G1–G3)

- Kế hoạch: `docs/plans/02-don-dep-sau-4c.md` (P = `09d4057`)
- Commit review: 2c8379c, 9517456, 3b89a92, 5ead317, e6e6b38, 2b3ca94, bee12af, 12ef791 (HEAD `12ef791`)
- Reviewer: vslt-reviewer, vòng 1, ngày 2026-09-27. Mọi lệnh chạy từ gốc repo với `.venv/Scripts/python`,
  `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`. Không dựa vào tóm tắt của coder: tự đọc diff, tự chạy test và kiểm Kaggle
  bằng lệnh chỉ đọc.

**Kết luận: CHANGES_REQUESTED.** Có 1 FAIL (mục 13, câu Giới hạn mới ở REPORT dòng 407). Lỗi gốc nằm ở thiết kế: §3.3 của
kế hoạch mâu thuẫn với §6. Phần sửa thì nhỏ. Mọi mục còn lại PASS: lưu trữ Kaggle, bảo mật, test và tái lập.

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | AC1 ca 1–13: `tests/test_archive_step4_kaggle.py` (24 test, gồm 04b/05b/05c/05d/11b thêm). Ca 14–20: `TestArchiveManifestAndReviews` (`tests/test_report_step4.py:804`). G1–G3: `TestProposal4cCleanup` (`:945`). Tôi chạy đột biến trong bộ nhớ, không sửa file. Thêm vào PROPOSAL một số chỉ có trong §6 (`1.5625`) thì G1b FAIL. Số `4321.5` thì G1b FAIL. Đổi lại "clip QIPEDC" thì G3a FAIL. Bỏ cụm "không phải giả thuyết không" thì G3b FAIL. Bỏ "Lớp đúng của S06" thì G3c FAIL. Chèn NBSP thì G2 FAIL. Thêm cụm `55.5% (5/9)` thì G1a FAIL. Như vậy test bắt lỗi thật. Có một điểm lệch kế hoạch: §6 yêu cầu REPORT nói `data/processed/` và `checkpoints/` không nằm trong lưu trữ, nhưng câu sinh ra không nói. Xem mục 13. |
| 2 | Tự chạy lại test | PASS | `python -m unittest tests.test_archive_step4_kaggle tests.test_report_step4 -v`: `Ran 112 tests ... OK`, 0 skip/FAIL/ERROR (24 + 88). AC2 (10 module handoff): `Ran 53 tests ... OK`, 0 skip. Khớp số coder báo (24; 88; 53). `test_report_step4`: 69 (đếm `def test_` tại P) → 88, tức +19 ≥ +11. |
| 3 | Test không bị sửa/xóa/nới | PASS | `git diff 09d4057 HEAD -- tests/` lọc dòng bắt đầu bằng một dấu `-`: rỗng. Chỉ có 628 dòng thêm, 2 file. `TestProposal4c` và `TestProposal4cScope` giữ nguyên và vẫn qua. Trong chuỗi commit, 3b89a92 sửa `FakeApi` của file test MỚI: tổng quát lớp 404 thành mã bất kỳ, và dataset chỉ hiện trong `dataset_list` sau khi tạo. Không assert nào bị nới. 09c vẫn kiểm "không có trong danh sách → 4". Grep skip/expectedFailure trong diff chỉ ra `dir_mode == "skip"` và một docstring. |
| 4 | Nguồn gốc dữ liệu | PASS | Không có dữ liệu mới, không train. Lưu trữ gồm đúng 18 file mà REPORT đã băm tại P. Tôi băm lại từng file local: bằng `provenance.runs[*].sha256_*` tại P, bằng `sha256` và `sha256_after_download` trong manifest (0 lệch). |
| 5 | Rò rỉ split | PASS (không áp dụng) | Không đổi split, không đọc TEST theo cách mới. AC5: JSON mới `==` JSON tại P sau khi bỏ `generated_by`, `review`, `provenance.archive` và input review/manifest (`equal_to_P True`). |
| 6 | Chọn bằng VAL, TEST một lần | PASS (không áp dụng) | Không chọn lại model. Kết quả chọn vẫn `H-keepz-360` (output khi chạy lại lệnh R). |
| 7 | Số liệu truy được | PASS | Mọi số ở §1.5 (slug, kích thước, sha256, `verified_at_utc`, commit 2b3ca94) lấy từ `kaggle_archive_manifest.json`. Manifest có `generated_by.command` và `git_commit`, và sha256 của nó nằm ở §1.4 (`12c5ceb3…`, tôi đã băm lại khớp). `provenance.archive.files` bằng `manifest.files` (18/18). Tái lập: tôi chạy lệnh ở header 2 lần, đổi `--out`/`--json-out` sang thư mục tạm. Cả hai lần exit 0. Hai lần chạy giống nhau, trừ dòng 3 (đường dẫn out). Thân REPORT (bỏ dòng 3–4) giống bản commit. JSON bằng bản commit, trừ `generated_by.command` (đường dẫn out) và `git_commit` (bee12af → 12ef791). `git diff bee12af HEAD -- scripts src tests` rỗng. `code_dirty=false`. |
| 8 | Cỡ mẫu, CI | PASS | Không có thống kê mới. PROPOSAL (b) ghi k/n, mẫu số là dự đoán sai, "Chỉ báo, không kiểm định". |
| 9 | Nhất quán train–realtime | PASS (không áp dụng) | `git diff 09d4057 HEAD -- backend src configs frontend` rỗng. |
| 10 | Không mock/random/hard-code ở đường chính | PASS | API giả chỉ nằm trong test. `main` dùng `KaggleApi` thật (`scripts/archive_step4_kaggle.py:441-445`). `public=False` là hằng (`:270`). §1.5 và cột "trùng §1.4" do `render` tính từ `inputs`. Không có sha256 hay kích thước gõ tay. |
| 11 | Bảo mật | PASS | (a) Private, tôi kiểm độc lập bằng lệnh chỉ đọc: `kaggle datasets list --mine` chỉ ra `phmvnsm33/vslt-step4-artifacts`. `KaggleApi().dataset_list(mine=True, search=...)` cho `is_private= True`. `dataset_metadata(ref, <tạm ngoài repo>)` cho `isPrivate= True`, licenses = unknown. `current_version_number` = 1 (không tạo version). `kaggle datasets status` = `ready`. Gọi ẩn danh không token: `api/v1/datasets/view/<ref>` → 403, trang web → 404, download → 403. Đối chứng với dataset public `zynicide/wine-reviews` → 200/200, nên phép thử phân biệt được. (b) File: `kaggle datasets files` → 19 file (18 + SHA256SUMS). Tên và kích thước bằng manifest. Tổng 37417786 = `dataset.total_bytes`. (c) Tải 3 file + SHA256SUMS vào `/tmp` ngoài repo: checkpoint và logits của H-keepz-360, logits baseline. `sha256sum -c`: 3 OK. Hash bằng manifest, và SHA256SUMS bằng `sha256sums_file.sha256`. (d) Credential: grep `git diff 09d4057..HEAD` với các mẫu `KGAT_...`, `"key": "<32 hex>"`, `KAGGLE_KEY`, `access_token`, `.kaggle/` → rỗng. Tên file và commit message cũng không có. `git ls-files` không có `kaggle.json`/`access_token`/`.kaggle/`. Log upload/verify ngoài repo (`../_kaggle_staging/*.out`) không có token. (e) Guard mã nguồn (ca 13) qua. Script không có `metadata --update`/`delete`/`version`. (f) `.gitignore` chỉ thêm 3 dòng. `git check-ignore -q` exit 0 cho 20/20 file (18 + 2 `alphabet_nested_final.pt`). `git diff --diff-filter=AM -- *.pt *.npz *.log` rỗng. `git ls-files reports` lọc pt/npz: trước = sau (chỉ `alphabet_real_best.pt`, chờ A3). (g) Không đụng backend, nên không có thay đổi CORS/WebSocket. |
| 12 | So sánh công bằng, GATE không nới | PASS | Không có so sánh mới. Tiêu chí AC không bị đổi. G2 là định nghĩa cách đếm do planner đặt trước khi sửa: 545/545 ≤ 550. `LC_ALL=C.UTF-8 wc -w` cũng ra 545. |
| 13 | Kết luận vượt bằng chứng | **FAIL** | REPORT dòng 407 (sinh ở `scripts/report_step4.py:1494-1498`) viết: "…log kernel và `train.log` vẫn bị gitignore và không nằm trong lưu trữ; clone sạch **không có quyền truy cập dataset thì** vẫn không tái tạo được báo cáo." Câu này ngụ ý rằng có quyền truy cập dataset thì tái tạo được. Điều đó sai. Tôi đối chiếu `inputs` với `git ls-files` và manifest: **8/57 đầu vào không được track và không nằm trong lưu trữ**: 4 log kernel, `data/processed/vslgh_segments/segments.csv`, `checkpoints/stgcn_tier2_indomain.pt`, `checkpoints/stgcn_unified_best.pt`, `reports/unified_run_2026-09-25/run_seed43/history.json`. Thiếu bất kỳ file nào thì `report_step4.py` trả mã 2. Câu cũ ("clone sạch không tái tạo được báo cáo; sha256 ở mục 1.4 là bằng chứng thay thế") vô điều kiện và đúng. Câu mới còn bỏ ý "sha256 ở §1.4 là bằng chứng thay thế" cho 8 file này. Kế hoạch §6 viết: "Log kernel, train.log, data/processed/, checkpoints/ … không nằm trong lưu trữ này. REPORT phải nói đúng như vậy". Nhưng câu mẫu ở §3.3 chỉ nêu log kernel và `train.log`. Coder làm đúng §3.3, nên lỗi gốc nằm ở thiết kế. Ngoài FAIL này có một nhận xét nhỏ, không chặn: §1.5 dòng 163 "Chỉ chủ dự án truy cập được" mạnh hơn bằng chứng. Private ≠ không có collaborator, và tôi không kiểm được danh sách chia sẻ. Nên viết "dataset private (không truy cập ẩn danh được)". |

## Các kiểm tra riêng orchestrator yêu cầu

- **Kaggle private + khớp manifest:** PASS. Xem mục 11 (a)–(c). Tôi không tạo, sửa hay xóa gì trên Kaggle. Lệnh đã chạy:
  `datasets list --mine`, `datasets status`, `datasets files`, `datasets download -f` (3 file + SHA256SUMS),
  `dataset_list(mine=True)`, `dataset_metadata` (thư mục tạm `/tmp/vslt_rev02_*`), cùng `curl` ẩn danh.
- **GitNexus HIGH ở 5ead317 và e6e6b38:** xác nhận các luồng bị ảnh hưởng chỉ nằm trong hai script. Tôi chạy
  `detect-changes --scope compare --base-ref 09d4057`. Kết quả: 12 file (gồm 3 file data của người dùng), 145 symbol, 16 luồng, risk
  "critical". Mức này do số symbol (Section Markdown và test mới), không do lời gọi chéo module. Cypher `STEP_IN_PROCESS` cho 20
  process có bước trong `scripts/report_step4.py` hoặc `scripts/archive_step4_kaggle.py`. Các process này chỉ gồm
  `Main → {Flat_name, Inside, Parse_sums, Sha256_file, Check_dataset_ref, Read_metadata}`,
  `Verify → {Parse_sums, Sha256_file, Inside}`, `Private_from_metadata → Inside` (archive) và `Main → {Rel, Sha256, Fr, Fv, Na, Yn}`
  (report). Có thêm 4 process `* → Wilson` chạm `scripts/report_unified.py`. Chúng đi qua `pred_split`/`rate_of`/`label_space_base_rate`
  (hàm không đổi) tới `wilson` (callee, `report_unified.py` không đổi). `impact -f` (upstream): `upload`, `verify`, `build`,
  `parse_args`, `archive_summary`, `join_reviews` đều LOW và exact. `main` LOW. `render` LOW lower-bound, có 1 call site không resolve
  được. Text search `git grep` tìm "report_step4" hoặc "archive_step4_kaggle" trên py/js/ts/yml/sh/ipynb ngoài 2 script + 2 test: rỗng.
- **PROPOSAL dòng 6, 11, 32 (ngoài G3):** không đổi ý nghĩa, không khẳng định mạnh hơn, phù hợp quyết định người dùng.
  Dòng 6 bỏ "(REPORT mục 4)", vì dòng 3 đã ghi "Số chép từ REPORT.md". Dòng 11 rút tham chiếu tiểu mục còn "REPORT mục 4".
  Giá trị 34.21%/95.47%, 624/23226 giữ nguyên. Dòng 32 bỏ "(run được chọn train với trim=true; bỏ cắt nghỉ thì phải train lại)".
  Nhánh "bỏ cắt nghỉ" không còn cần sau quyết định 4 ngày 2026-09-27 (`docs/progress_log.md:27-29`: GIỮ cắt đoạn nghỉ, cùng tham số
  lưu trong checkpoint), và "(360 px, cắt đoạn nghỉ)" vẫn còn. Dòng 32 thuộc mục "Không làm trong việc này", không nằm trong ba mục
  được bảo vệ ở §3.5. Coder liệt kê cả ba dòng kèm lý do trong message của 2b3ca94. Khuyến nghị vẫn là B và "có điều kiện" (G3d qua).
  Nhận xét nhỏ: PROPOSAL là văn bản người dùng đã dùng để quyết. Sửa câu chữ sau khi quyết vẫn được phép theo quyết định 6 và §3.5,
  nhưng nên ghi trong progress_log rằng PROPOSAL đã đổi sau quyết định (545 từ).
- **G1, G2, G3 của review 01 vòng 2:** đã sửa thật.
  G1: test mới cắt `body` trước "## 6. Review" và dùng biên chặt `[0-9A-Za-z_.]`. Đột biến số chỉ-có-trong-§6 bị bắt.
  G2: định nghĩa đếm ở kế hoạch §3.5 có test. Đo lại: 545 = 545, không có khoảng trắng lạ.
  G3: dòng 17 ghi "69/634 dự đoán sai trên QIPEDC TEST", "183/225 dự đoán sai trên S06", có lưu ý S06 và "282/876 không phải
  giả thuyết không (null) chuẩn". Số trùng REPORT dòng 381, 383, 385.
- **Thay đổi ngoài phạm vi:** `git diff --stat 09d4057..HEAD` chỉ gồm 9 file trong danh sách AC7. `docs/reviews/01-review.md`
  không đổi (sha256 `39a121ab…` = §1.4). Ba file data bị người dùng xóa vẫn ở trạng thái xóa chưa commit. Hai `test_per_class.csv`
  untracked không bị commit.

## Theo dõi AC (chưa đến hạn, không tính FAIL ở vòng này)

- AC8 (progress_log) và AC9/AC10 thuộc S8. `docs/progress_log.md` chưa có dòng cho kế hoạch 02, `docs/plans/02-don-dep-sau-4c.md`
  còn untracked. Khi làm S8 cần ghi: 3 lần `upload` (lần 1 exit 6 vì 403 GetDatasetStatus, lần 2 exit 6 vì đường dẫn tương đối,
  lần 3 OK), 2 lần `verify` (lần 1 exit 6 do DownloadDataset 404, lần 2 exit 0), và mọi lệnh Kaggle chỉ đọc của reviewer ở trên.
- Lệch nhỏ so với §3.2, đã ghi trong message 3b89a92: nếu `dataset_status` trả 403 hoặc 404 thì kiểm lại bằng `dataset_list(mine)`
  trước khi coi slug là chưa có. Cách này an toàn: mã khác 403/404 → 6, có trong danh sách → 5, và server cũng từ chối create trùng
  slug. Test 05b/05c/05d có kiểm.
- Không kiểm được (UNVERIFIED, không chặn): lúc chạy `stage`/`upload` (sau 5ead317), `scripts/report_step4.py` đang có WIP chưa
  commit (theo message 5ead317), nên §S4 "HEAD sạch" không được đáp ứng hoàn toàn. Kết quả không bị ảnh hưởng, vì `verify` (ở 2b3ca94,
  bằng mã hiện tại) băm lại toàn bộ và file trên Kaggle khớp hash.
- Độ bền (không chặn): `archive_summary` gọi `os.path.isfile(local_path)` theo đường dẫn tương đối với CWD. Chạy ngoài gốc repo thì
  script trả 3, tức lỗi về phía an toàn.

## Việc phải sửa (xếp theo mức độ)

1. **[Thiết kế → triển khai, mục 13, chặn]** Sửa câu Giới hạn khi có `--archive-manifest` để nó không ngụ ý "có quyền truy cập
   dataset thì tái tạo được". Hướng đề xuất: planner sửa câu mẫu ở §3.3 cho khớp §6. Sau đó coder sinh câu từ `inputs`: liệt kê các
   đầu vào vừa không được git track vừa không nằm trong manifest (hiện có 8: log kernel, `data/processed/vslgh_segments/segments.csv`,
   `checkpoints/*.pt`, `run_seed43/history.json`), giữ ý "sha256 ở mục 1.4 là bằng chứng thay thế cho các file này", và nói rõ
   "kể cả khi có quyền truy cập dataset, clone sạch vẫn không tái tạo được báo cáo". THÊM test (không sửa test cũ): câu Giới hạn
   có archive chứa "kể cả" (hoặc cụm tương đương do planner chốt), và nhắc `data/processed`/`checkpoints`. Sau đó sinh lại REPORT
   theo S6/S8.
2. **[Triển khai, nhỏ, không chặn]** §1.5 dòng 163: đổi "Chỉ chủ dự án truy cập được" thành "Dataset private (không truy cập ẩn danh
   được; chỉ chủ tài khoản và người được chia sẻ)" hoặc tương đương.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **A3 (§7.1, vẫn chờ):** `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` vẫn được git track.
   `.gitignore` mới không gỡ nó. File này train trên bộ hauuto, giấy phép chưa rõ. Chọn (a) giữ, (b) lưu trữ Kaggle rồi
   `git rm --cached`, hoặc (c) `git rm --cached` không lưu trữ. Nhánh chưa có remote-tracking (`origin/feat/vslt-complete` không
   tồn tại), nhưng các nhánh khác có thể đã push file này.
2. **§7.2 (không chặn):** có lưu thêm 4 log kernel, `run_seed43/history.json`, và nếu được phép thì `segments.csv`/`checkpoints/*.pt`
   vào dataset private (tạo version mới, cần kế hoạch nhỏ riêng) không? Nếu có thì câu Giới hạn ở việc sửa 1 sẽ ngắn lại.
3. **Không bắt buộc:** PROPOSAL_4c.md đã sửa câu chữ sau khi người dùng quyết định B (dòng 6, 11, 17, 32). Nội dung quyết định
   không đổi. Người dùng xem lại nếu muốn.
