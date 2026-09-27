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
