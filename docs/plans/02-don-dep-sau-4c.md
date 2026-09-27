# Kế hoạch 02 — Dọn dẹp sau điểm dừng 4c (quyết định mục 5 và 6 của người dùng)

> **CẦN NGƯỜI DÙNG — chỉ cho MỘT mục con (A3), KHÔNG chặn việc bắt đầu code.**
> `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` **đang được git track** (review 02 xác nhận: thêm ở
> `429b289`, đã có trên `origin/fix/audit-round2`). Quyết định 5 của người dùng ("thêm reports/**/*.pt vào .gitignore") không nói
> gì về file đã track. `git rm --cached` không xóa file trên đĩa, nhưng GỠ file khỏi repo (clone sạch mất checkpoint Cấp 1 thật)
> và không xóa được nó khỏi lịch sử đã push. Vì đây là "xóa file" khỏi repo (autopilot §5), A3 chỉ làm SAU khi người dùng trả lời
> (§7). Lần sửa 1 và Lần sửa 2 KHÔNG thêm điểm dừng, KHÔNG mở rộng lưu trữ, KHÔNG chạy lệnh Kaggle ghi, KHÔNG làm A3.
>
> Điểm dừng có điều kiện của phần B (đã qua): kiểm tra private thất bại → DỪNG; slug đã tồn tại → hỏi; tổng > 2 GB → hỏi.
> **Lần sửa 2 là vòng CODE↔REVIEW 3/3 (cuối).** Nếu review vòng 3 còn FAIL thì orchestrator DỪNG và báo người dùng (§7).

Nhánh `feat/vslt-complete`. Lập kế hoạch lần đầu tại HEAD `09d4057` (gọi là `P`); Lần sửa 1 tại `12ef791`; Lần sửa 2 tại `72bc1b1`.
Ngày 2026-09-27.

---

## 0b. Lần sửa 2 (sau review `docs/reviews/02-review.md` vòng 2, CHANGES_REQUESTED mức thấp, vòng CODE↔REVIEW 2/3)

Commit đã có và GIỮ NGUYÊN: 8 commit ở §0 và `514ad47` (A5), `ae82625` (B'), `208fc5f` (C1), `72bc1b1` (C2). Không viết lại lịch
sử; mọi sửa đổi là commit MỚI trên `72bc1b1`. `docs/reviews/02-review.md` hiện có vòng 2 chưa commit: không sửa nội dung file đó.

### 0b.1 Nguyên nhân gốc
**FAIL mục 13 (mức thấp), REPORT dòng 408.** Chữ cố định mà Lần sửa 1 chốt ở §3.3 viết "Thiếu một đầu vào thì
scripts/report_step4.py dừng với mã 2". Đây là khẳng định phổ quát, và nó sai với 3/8 file trong danh sách. Reviewer đã kiểm bằng
thực nghiệm (`--segments <không tồn tại>` → exit 0, REPORT khác 5 dòng):
- `data/processed/vslgh_segments/segments.csv`: chỉ đọc khi `os.path.isfile` (`scripts/report_step4.py:1065–1066`); thiếu → giá
  trị liên quan thành `None`, REPORT in "KHÔNG CÓ (thiếu segments.csv)".
- `checkpoints/stgcn_tier2_indomain.pt`: chỉ thêm khi file có (`:1055–1058`); thiếu → `sha256`/`same_as_4a_model` thành `None`.
- `reports/unified_run_2026-09-25/run_seed43/history.json`: history của run không phải run được chọn hay run từ điển dùng → `null`
  (`:724–732`).
Chỉ 5/8 file thật sự làm script dừng với mã 2: 4 log kernel (`inputs.add` không điều kiện) và `checkpoints/stgcn_unified_best.pt`
(`inputs.add(cur_ckpt)` không điều kiện).
Lỗi thuộc KẾ HOẠCH, cùng loại với Lần sửa 1: planner chốt một câu mô tả hành vi của mã nhưng không đối chiếu với mã. `Inputs` cũng
không ghi lại file nào là bắt buộc, file nào là tùy chọn, nên không câu sinh tự động nào có thể nói đúng. Test ca 23 kiểm có cụm
"mã 2" nhưng không kiểm cụm đó đúng cho những file nào.

**Nhận xét không chặn.** `git_tracked` truyền đường dẫn cho `git ls-files` dưới dạng pathspec: `*`, `?`, `[` bị hiểu là glob.
Hiện không có đầu vào nào như vậy. Sửa bằng `--literal-pathspecs`.

### 0b.2 Thiết kế sửa (thay phần tương ứng của §3.3; phần còn lại của §3.3 giữ nguyên)
1. **Phân loại sinh từ mã, không gõ tay.** `Inputs.add(path, role, required=True)`: thêm tham số `required` (mặc định `True`, giữ
   nguyên hành vi của mọi lời gọi cũ). `Inputs` lưu cờ này theo đường dẫn; cùng một đường dẫn được thêm nhiều lần thì
   `required = OR` các lần. Chỉ những chỗ gọi mà mã ĐÃ kiểm sự tồn tại và bỏ qua khi thiếu mới truyền `required=False`. Tại
   `72bc1b1` đó là: `segments` (`:1066`), checkpoint mặc định của backend (`:1056`), và `history.json` của run không thuộc
   `(chosen, used_dict)` (`:728`, qua `load_json`; `load_json` thêm tham số `required` và truyền tiếp). Không đổi logic kiểm tồn tại
   nào; không đổi mã thoát nào.
2. `Inputs.as_list()` KHÔNG đổi (giữ ba khóa `path`, `sha256`, `role`), để JSON `inputs` giữ nguyên như ở P. Thêm phương thức mới
   `Inputs.required_paths() -> set[str]`.
3. `untracked_unarchived_inputs(inputs, tracked, archived, required)`: thêm tham số `required` (tập đường dẫn bắt buộc). Mỗi phần tử
   trả về có thêm khóa `required` (bool). Khóa JSON `limitations_data.untracked_unarchived_inputs` thêm `n_required`, `n_optional`
   (khóa này đã được bỏ khi so với P, nên không đổi AC5).
4. `git_tracked`: gọi `git --literal-pathspecs ls-files -z -- <paths…>`. Mọi hành vi khác của hàm giữ nguyên.
5. **Câu Giới hạn khi có manifest, nhánh `n > 0` (chữ cố định chốt nguyên văn; chỉ `{}` là dữ liệu; một dòng):**
   "- Checkpoint và logits TEST của mọi run được lưu ở Kaggle dataset private `{ref}` (sha256 ở mục 1.5); lưu trữ không gồm log
   kernel hay đầu vào nào khác. {n}/{n_inputs} đầu vào của báo cáo này vừa không được git track vừa không nằm trong lưu trữ;
   bằng chứng thay thế cho các file này là sha256 ở mục 1.4. Bắt buộc ({n_required}; thiếu thì scripts/report_step4.py dừng với
   mã 2): {DS_BẮT_BUỘC}. Tùy chọn ({n_optional}; thiếu thì script vẫn chạy nhưng bỏ phần dùng file đó hoặc ghi null, nên báo cáo
   khác đi mà không báo lỗi): {DS_TÙY_CHỌN}. Vì vậy kể cả khi có quyền truy cập dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo."
   `{DS_…}` là các đường dẫn trong backtick, sắp theo `path`, nối bằng ", "; nhóm rỗng thì in đúng chữ "không có".
   Nhánh `n == 0` và nhánh không có manifest: giữ nguyên như Lần sửa 1 (§3.3).
   Câu mới vẫn thỏa mọi test cũ: ca 14 (một dòng có `ref`, có "private", "log kernel", không có chuỗi cấm), ca 23 (có
   `"{n}/{n_inputs} đầu vào"`, mọi path, "bằng chứng thay thế cho các file này là sha256 ở mục 1.4", "kể cả khi có quyền truy cập
   dataset", "vẫn KHÔNG tái tạo được báo cáo", "mã 2"; không có "không có quyền truy cập dataset thì"), ca 27. Nếu coder thấy câu
   này làm một test cũ FAIL thì báo planner, KHÔNG sửa test.
6. Chữ cũ "Thiếu một đầu vào thì scripts/report_step4.py dừng với mã 2, nên …" bị BỎ.

### 0b.3 Thay đổi ở §4 và §5
- §4: thêm bước T0–T5 (thay R3–R5 của Lần sửa 1 cho vòng này).
- §5: THÊM AC1 ca 28–32. AC2: ngưỡng số test mới. AC5b (mới): so sánh với `72bc1b1`. AC8: cập nhật dòng progress_log sẵn có (không
  thêm dòng). AC9': so sánh hai lần sinh của vòng này. Không bỏ, không nới tiêu chí nào; test cũ không được sửa.

---

## 0. Lần sửa 1 (sau review `docs/reviews/02-review.md` vòng 1, CHANGES_REQUESTED, vòng CODE↔REVIEW 1/3)

Commit của coder đã có và GIỮ NGUYÊN: `2c8379c`, `9517456`, `3b89a92`, `5ead317`, `e6e6b38`, `2b3ca94`, `bee12af`, `12ef791`.
Không viết lại lịch sử (không amend, rebase, reset, force). Mọi sửa đổi là commit MỚI trên `12ef791`.

### 0.1 Nguyên nhân gốc

**FAIL mục 13 (kết luận vượt bằng chứng), REPORT dòng 407, sinh ở `scripts/report_step4.py:1494–1498`.** Câu Giới hạn mới viết
"…log kernel và `train.log` vẫn bị gitignore và không nằm trong lưu trữ; clone sạch không có quyền truy cập dataset thì vẫn
không tái tạo được báo cáo". Câu này ngụ ý rằng có quyền truy cập dataset thì tái tạo được báo cáo. Điều đó sai: theo reviewer,
8/57 đầu vào vừa không được git track vừa không nằm trong lưu trữ (4 log kernel, `data/processed/vslgh_segments/segments.csv`,
`checkpoints/stgcn_tier2_indomain.pt`, `checkpoints/stgcn_unified_best.pt`, `reports/unified_run_2026-09-25/run_seed43/history.json`).
Lỗi nằm ở KẾ HOẠCH, coder chỉ làm theo:
1. §3.3 (bản trước) đưa ra câu mẫu gõ sẵn, chỉ nêu "log kernel và `train.log`". Nó mâu thuẫn với §6, nơi viết rằng log kernel,
   `train.log`, `data/processed/`, `checkpoints/` không nằm trong lưu trữ và "REPORT phải nói đúng như vậy".
2. Câu mẫu là một danh sách GÕ TAY các loại file bị thiếu, không sinh từ dữ liệu.
3. Câu mẫu bỏ ý "sha256 ở mục 1.4 là bằng chứng thay thế" của câu cũ.
4. AC1 ca 14 chỉ kiểm câu có chứa "private" và "log kernel", không kiểm phạm vi tái tạo.

**Nhận xét không chặn, §1.5 REPORT dòng 163.** "Chỉ chủ dự án truy cập được" mạnh hơn bằng chứng (không kiểm danh sách chia sẻ).

### 0.2 Lệch kế hoạch được planner CHẤP NHẬN (ghi lại, không phải lỗi)
- `3b89a92`: trong `upload`, nếu `dataset_status` trả 403/404 thì kiểm lại bằng `dataset_list(mine=True)` trước khi coi là slug
  chưa có. Mã khác 403/404 → 6; có trong danh sách → 5. Test 05b/05c/05d kiểm. Hướng lỗi an toàn.
- `stage`/`upload` chạy khi `scripts/report_step4.py` còn WIP chưa commit (message `5ead317`). Planner chấp nhận: kết quả không phụ
  thuộc `report_step4.py`, và `verify` (ở `2b3ca94`) băm lại toàn bộ, khớp hash. Ghi UNVERIFIED có giải thích vào progress_log.

### 0.3 Thay đổi so với bản trước (Lần sửa 1)
- §3.3: câu Giới hạn sinh từ `inputs` (`untracked_unarchived_inputs`, `git_tracked`); câu §1.5 "private … không truy cập ẩn danh được".
- §4: bước R0–R5. §5: AC1 ca 21–27; AC2, AC5, AC8, AC9 cập nhật (chỉ thêm khóa/số mới vào danh sách được bỏ, có lý do).
- §6: rủi ro "danh sách phụ thuộc trạng thái git lúc sinh".

---

## 1. Mục tiêu và DoD

**Mục tiêu.** (A) Chặn việc commit nhầm checkpoint/logits trong `reports/` bằng `.gitignore`. (B) Lưu checkpoint + logits
TEST của 9 run mà REPORT bước 4 dùng vào MỘT Kaggle dataset PRIVATE; slug + sha256 từng file do script sinh và được
`report_step4.py` đọc lại để in vào REPORT.md. (C) Sửa ba góp ý G1, G2, G3 của review 01 vòng 2 mà không nới test cũ.
(D) Sinh lại REPORT/JSON bằng script và cho vslt-reviewer review cả A–C. Lần sửa 1–2: REPORT nói ĐÚNG phạm vi tái tạo và ĐÚNG hành vi
của script khi thiếu từng loại đầu vào.

**DoD phục vụ.**
- DoD 9 (Tài liệu, "Giới hạn" trung thực): REPORT nói đúng checkpoint/logits nằm ở đâu, đầu vào nào chỉ có trên máy local, và
  thiếu chúng thì điều gì xảy ra; kiểm được bằng sha256 và test.
- DoD 7 (Kiểm thử): test mới cho G1/G2/G3, cho script lưu trữ, cho câu Giới hạn và việc phân loại; test cũ giữ nguyên.
- DoD 10 (một phần): review cho các thay đổi của việc này.
- Quy tắc cứng autopilot §4. Việc này dùng 0 giờ GPU.

Không thuộc phạm vi: Việc 4 trở đi; fine-tune (ii); đổi model mặc định; mọi thay đổi `backend/`, `src/`, `configs/`,
`frontend/`; mở rộng lưu trữ (câu hỏi §7.2); A3.

---

## 2. Hiện trạng

### 2.0 Tại HEAD `72bc1b1` (theo review 02 vòng 2)
- Đã có: `.gitignore` (3 dòng thêm); `scripts/archive_step4_kaggle.py`; dataset private `phmvnsm33/vslt-step4-artifacts`
  (version 1, 19 file); manifest `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`; `report_step4.py` có
  `--archive-manifest`, nhiều `--review-file`, `git_tracked`, `untracked_unarchived_inputs`, `archive_limit_line`; REPORT/JSON sinh
  với `--review-file docs/reviews/02-review.md docs/reviews/01-review.md` tại `208fc5f`; progress_log dòng 47–54 có dòng kế hoạch 02.
- Test (reviewer đo): `tests.test_archive_step4_kaggle` 24, `tests.test_report_step4` 99, AC2 53.
- Còn sai: vế "Thiếu một đầu vào thì … dừng với mã 2" (REPORT dòng 408), xem §0b.1.
- `docs/reviews/02-review.md`: đã commit ở `208fc5f` (vòng 1), nay có thêm vòng 2 chưa commit. sha256 của nó trong REPORT §1.4 đã cũ.
- Ràng buộc từ test đã có, KHÔNG được sửa: ca 14 (`tests/test_report_step4.py:839–862`), ca 19 (`OLD_LIMIT`), ca 23–27
  (`TestLimitationUntrackedInputs`, `TestRealReportUntrackedInputs`).

### 2.1 `.gitignore` (tại P)
- Dòng 35: `*.npz` đã bị bỏ qua ở MỌI nơi. Dòng 73, 75: quy tắc `.pt` hẹp. Dòng 58–61: `kaggle.json`, `.kaggle/`, `access_token`.

### 2.2 File `.pt`/`.npz` trong `reports/`
- 7 run bước 4 + 2 run baseline (`reports/unified_run_2026-09-25/{run, run_seed43}/`), mỗi run 2 file → 18 file.
- `reports/alphabet_nested_2026-09-25/{primary,variants}/alphabet_nested_final.pt` (ignore); `alphabet_real_best.pt` (track, A3).
- `REPORT_partial.md` đã được người dùng chuyển ra `../_backup_step4/`.

### 2.3 `scripts/report_step4.py` (tại `72bc1b1`)
- `Inputs` 519–533 (`add` thiếu file → `ReportError(2)`, kiểm bằng `os.path.isfile`); `load_json`; `git()` 498–500.
- Chỗ gọi có điều kiện tồn tại (đều kiểm bằng `os.path.isfile`): `history.json` 724–732; checkpoint mặc định backend 1055–1058
  (đường dẫn đọc từ `backend/main.py`, tức file trong repo `checkpoints/`); `segments` 1065–1066 (mặc định
  `data/processed/vslgh_segments/segments.csv`, trong repo).
- Câu Giới hạn có manifest: hàm `archive_limit_line` (reviewer vòng 2).

### 2.4 Kaggle CLI trong `.venv` (đọc mã, không chạy)
- `kaggle 2.2.4`, `kagglesdk 0.1.37`. `dataset_create_new(public=False)` → `is_private = not public` (`kaggle_api_extended.py:5605,
  5630`). **Bẫy:** `dataset_metadata_update` đặt `is_private = metadata.get("isPrivate") or False` (4760): CẤM gọi.
- Kiểm private: `dataset_list(mine=True)` → `ApiDataset.is_private`; `dataset_metadata` → `DatasetInfo.isPrivate`.

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu
```
step4_results.json ─► archive_step4_kaggle.py stage/upload/verify ─► Kaggle dataset PRIVATE + manifest (đã xong)
report_step4.py --archive-manifest <manifest>
   ─► archive_summary ─► provenance.archive ─► REPORT §1.5
   ─► Inputs(path, role, required) × git --literal-pathspecs ls-files × manifest.local_path
        ─► limitations_data.untracked_unarchived_inputs {n, n_inputs, n_required, n_optional, files[+required]}
        ─► câu Giới hạn (nhóm bắt buộc / tùy chọn)                                        [Lần sửa 2]
```
Không chạy model, không đọc TEST theo cách mới, không có số liệu ML mới.

### 3.2 Script `scripts/archive_step4_kaggle.py` (đã cài; không đổi trong Lần sửa 1–2)
Lệnh con `stage` → `upload` → `verify`; mã thoát 0/2/3/4/5/6 như bản đầu. CẤM: `public=True`, `--public`, `-u`,
`dataset_metadata_update`, `metadata --update`, `dataset_delete`, `dataset_create_version`. Manifest có đúng các khóa:
```
{"generated_by": {"script", "command", "git_commit", "kaggle_version", "kagglesdk_version", "verified_at_utc"},
 "dataset": {"ref", "url", "title", "license", "is_private": true,
             "is_private_sources": {"dataset_list_mine": true, "dataset_metadata": true}, "status": "ready", "total_bytes"},
 "files": [{"run", "run_dir", "kind", "local_path", "archive_name", "size_bytes", "sha256", "sha256_after_download"}],
 "sha256sums_file": {"archive_name": "SHA256SUMS", "sha256"},
 "verified": {"file_list_matches": true, "downloaded_sha256_all_match": true, "n_files": 18}}
```

### 3.3 `scripts/report_step4.py` (chỉ THÊM; giữ mọi tham số, mã thoát, khóa JSON cũ)
Đã cài, giữ nguyên hành vi:
- `--archive-manifest PATH` (thiếu → 2; `archive_summary` lỗi → 3); JSON `provenance.archive`; `### 1.5` sau §1.4, trước `## 2.`.
- Không có manifest: `provenance.archive = None`, không có §1.5, câu Giới hạn cũ NGUYÊN VĂN.
- `--review-file` một hoặc nhiều file (`join_reviews`).
- Câu §1.5 (Lần sửa 1): "Dataset private theo Kaggle API (không truy cập ẩn danh được; chỉ tài khoản chủ và người được chia sẻ truy
  cập được; danh sách chia sẻ không được kiểm); tải: `kaggle datasets download <ref>`; kiểm: `sha256sum -c SHA256SUMS`."
- `git_tracked(paths)`: đường dẫn ngoài repo → không track, không gọi git cho nó; trong repo → MỘT lời gọi git; `git()` trả `None`
  → `ReportError(2)`. **Lần sửa 2:** lời gọi là `git --literal-pathspecs ls-files -z -- <paths…>`.
- `untracked_unarchived_inputs` và khóa `limitations_data.untracked_unarchived_inputs` luôn tính, dùng `inputs` cuối cùng của
  `build`. **Lần sửa 2:** thêm tham số/khóa `required`, `n_required`, `n_optional` (§0b.2 mục 1–3).
- Câu Giới hạn khi có manifest:
  - nhánh `n > 0`: **thay bằng câu ở §0b.2 mục 5 (Lần sửa 2).**
  - nhánh `n == 0` (giữ từ Lần sửa 1): "- Checkpoint và logits TEST của mọi run được lưu ở Kaggle dataset private `{ref}` (sha256
    ở mục 1.5); lưu trữ không gồm log kernel hay đầu vào nào khác. Mọi đầu vào của báo cáo này đều được git track hoặc nằm trong
    lưu trữ."

**Trạng thái git lúc sinh.** Danh sách phụ thuộc git index lúc chạy. Mọi file đầu vào mà việc này tạo hoặc sửa (file review 02,
manifest) phải được COMMIT TRƯỚC mỗi lần sinh REPORT được commit.

### 3.4 `.gitignore` (đã làm)
Chú thích + `reports/**/*.pt` + `reports/**/*.npz`. Không xóa dòng nào.

### 3.5 PROPOSAL_4c.md (G3) và cách đếm từ (G2) (đã làm; không đổi trong Lần sửa 1–2)
Cách đếm từ: `len(re.findall(r"[^ \t\n\r\f\v]+", text))` trên UTF-8, bằng `len(text.split())` và ≤ 550.

### 3.6 Module tiền xử lý chung
Không đổi. Không chạm `src/`, `backend/`, `configs/`, `frontend/`.

---

## 4. Chia việc

Quy tắc chung: `impact` (upstream) trước khi sửa symbol có sẵn (ít nhất `Inputs.add`, `load_json`, `build`, `git_tracked`,
`untracked_unarchived_inputs`, `archive_limit_line`; UNKNOWN → xác nhận bằng text search); `detect-changes --scope all` trước MỖI
commit; chỉ `git add <đường dẫn cụ thể>`; không commit `*.pt`/`*.npz`/`*.log`/dữ liệu/staging; không viết lại lịch sử; không đụng
thay đổi chưa commit của người dùng. Không lệnh Kaggle ghi. Không đụng A3.

S0–S7 (bản đầu) và R0–R5 (Lần sửa 1) đã làm. Lần sửa 2 gồm T0–T5.

**T0 — Kiểm trạng thái (≈ 0.25 giờ).** `git log --oneline -1` → `72bc1b1`. `git status --porcelain -- scripts src tests` → rỗng.
`git status --porcelain docs/reviews/02-review.md` → ` M` (vòng 2 chưa commit). Chạy AC2 + hai module test → ghi số "trước"
(reviewer: 53; 24 + 99).

**T1 — Test trước (≈ 1 giờ).** THÊM AC1 ca 28–32 vào `tests/test_report_step4.py` (không sửa dòng cũ). Ca 32 đọc file thật, sẽ FAIL
tới T3.

**T2 — Cài đặt (≈ 1 giờ).** §0b.2 mục 1–6. Chạy toàn bộ test (trừ ca 32) + AC2. Commit mã + test (commit A6). Nếu ca 29 cho thấy
một file có cờ `required=True` mà thiếu thì KHÔNG ra mã 2 (vd. crash, mã 1/3), đó là phát hiện: ghi lại, báo planner; không nới test,
không đổi mã thoát trong lần sửa này.

**T3 — Commit review vòng 2 rồi sinh lại (≈ 0.5 giờ).** Phụ thuộc: A6.
1. Commit C3: chỉ `docs/reviews/02-review.md` (vòng 2, nguyên nội dung reviewer viết) + `docs/plans/02-don-dep-sau-4c.md`.
2. Tại HEAD = C3 (sạch): chạy lệnh ở header REPORT hiện tại, không đổi đối số (`--review-file docs/reviews/02-review.md
   docs/reviews/01-review.md` + `--archive-manifest …`). Chạy hai lần, `cmp`. Kiểm AC5b. Chạy toàn bộ test (gồm ca 32).
3. Commit B'' (REPORT/JSON).

**T4 — Review vòng 3/3 (orchestrator gọi vslt-reviewer).** Reviewer thêm vòng 3 vào đầu `docs/reviews/02-review.md`. Còn FAIL →
KHÔNG còn vòng CODE↔REVIEW: orchestrator dừng và báo người dùng (§7).

**T5 — Bản cuối + đóng việc (≈ 0.5 giờ) = R5.2 của vòng này.** Phụ thuộc: T4 không FAIL.
1. Commit C4: chỉ `docs/reviews/02-review.md` (vòng 3).
2. Tại HEAD = C4 (sạch): cùng lệnh T3.2. Chạy hai lần, `cmp`. Kiểm AC9'. Chạy toàn bộ test.
3. CẬP NHẬT dòng progress_log sẵn có của kế hoạch 02 (AC8). `detect-changes --scope all`. Commit C5 (REPORT/JSON + progress_log).

Ước lượng GPU: **0 giờ**. Không có lệnh Kaggle nào trong Lần sửa 2.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder không được đổi; chỉ planner đổi và phải ghi lý do)

Mọi lệnh Python chạy qua `.venv/Scripts/python` với `PYTHONIOENCODING=utf-8`, từ thư mục gốc repo.

**AC1 — Test, mỗi ca một test riêng, không skip, không cần mạng.**
`.venv/Scripts/python -m unittest tests.test_archive_step4_kaggle tests.test_report_step4 -v` → `OK`, 0 skip.

Ca 1–13 (`tests/test_archive_step4_kaggle.py`): stage/upload/verify, mã thoát 2/3/4/5/6, `public is False`, guard mã nguồn (như bản đầu).
Ca 14–20 (`TestArchiveManifestAndReviews`): manifest, §1.5, câu Giới hạn cũ/mới, nhiều review (như bản đầu).
Ca 21–27 (Lần sửa 1): `untracked_unarchived_inputs`; `git_tracked`; câu Giới hạn `n > 0`/`n == 0`; §1.5 không còn "Chỉ chủ dự án";
không có manifest; file thật khớp `git ls-files` + manifest. Tất cả giữ nguyên, không sửa.

MỚI (Lần sửa 2), THÊM vào `tests/test_report_step4.py`:
28. `Inputs`: `add(p, r)` → `p ∈ required_paths()`; `add(q, r, required=False)` → `q ∉ required_paths()`; thêm cùng đường dẫn một
    lần `False` rồi một lần `True` (và theo thứ tự ngược lại) → bắt buộc; `as_list()` vẫn chỉ có đúng ba khóa `path`, `sha256`, `role`.
29. **Phân loại khớp hành vi thật (fixture, giả lập thiếu từng file).** Dựng fixture có manifest hợp lệ, có `--segments` trỏ tới một
    `segments.csv` nhỏ trong thư mục tạm (có cột `signer_id`, `sentence_id`), và có `history.json` của ít nhất một run không phải run
    được chọn hay run từ điển dùng. Chạy `build` một lần (đủ file), lấy `limitations_data.untracked_unarchived_inputs.files` và REPORT
    tham chiếu. Assert cả hai nhóm `required=True` và `required=False` đều khác rỗng.
    Rồi với MỖI phần tử `X` (không chọn mẫu), giả lập "thiếu X" mà KHÔNG động vào đĩa: trong `unittest.mock.patch` bọc
    `os.path.isfile` và `os.path.exists` để trả `False` cho đúng đường dẫn `X` (so sau khi chuẩn hóa bằng `R.rel`) và giữ nguyên
    hành vi với mọi đường dẫn khác; chạy `R.main` với `--out`/`--json-out` mới trong thư mục tạm:
    - `required=True` → `main` trả 2 và không ghi file nào;
    - `required=False` → `main` trả 0, và thân REPORT (bỏ dòng Lệnh/HEAD) khác thân REPORT tham chiếu.
    **Cấm** test di chuyển, đổi tên hay xóa bất kỳ file nào ngoài thư mục tạm của test (đầu vào như `checkpoints/…` là file thật của
    người dùng). Mọi `patch` phải được gỡ trong `finally`/context manager.
30. Câu Giới hạn (fixture của ca 29, đủ file): dòng duy nhất chứa `ref` chứa `f"Bắt buộc ({n_required}; thiếu thì
    scripts/report_step4.py dừng với mã 2)"` và `f"Tùy chọn ({n_optional}; thiếu thì script vẫn chạy nhưng bỏ phần dùng file đó hoặc
    ghi null, nên báo cáo khác đi mà không báo lỗi)"`. Mỗi đường dẫn `required=True` nằm giữa cụm "Bắt buộc (" và cụm "Tùy chọn (",
    mỗi đường dẫn `required=False` nằm sau cụm "Tùy chọn (". Dòng KHÔNG chứa "Thiếu một đầu vào thì". `n_required + n_optional == n`.
    Biến thể nhóm rỗng: thay `R.git_tracked` bằng hàm coi mọi đường dẫn tùy chọn là đã track (các đường dẫn khác giữ như thật) → dòng
    có "Tùy chọn (0; " và ngay sau dấu ":" của nhóm đó là đúng chữ "không có".
31. `git_tracked` dùng pathspec nguyên văn: thay `R.git` bằng hàm ghi lại tham số → lời gọi có `--literal-pathspecs` đứng trước
    `ls-files`. Không thay `R.git`: `git_tracked(["scripts/*.py"])` → tập rỗng (không có file tên đúng như vậy), và
    `git_tracked(["scripts/report_step4.py"])` → `{"scripts/report_step4.py"}`.
32. File THẬT (lớp mới, thiếu file thì FAIL, không skip): đọc `reports/step4_2026-09-26/{REPORT.md, step4_results.json}`. Mỗi phần
    tử của `limitations_data.untracked_unarchived_inputs.files` có `required` là bool; `n_required + n_optional == n`; `body` (phần
    trước `"\n## 6. Review\n"`) có dòng chứa `ref`, trong đó đường dẫn bắt buộc nằm trong nhóm "Bắt buộc (", đường dẫn tùy chọn
    nằm trong nhóm "Tùy chọn ("; dòng KHÔNG chứa "Thiếu một đầu vào thì". (Việc phân loại đúng với hành vi thật đã do ca 29 kiểm
    trên fixture và do reviewer kiểm thực nghiệm trên dữ liệu thật, AC10.)

**AC2 — Không hồi quy.** Bộ 10 module handoff → cùng số như T0 (53), `OK`. `tests.test_report_step4`: số sau ≥ số trước T0 (99) + 5
(ca 28–32). `tests.test_archive_step4_kaggle`: = số trước (24). `git diff 09d4057 HEAD -- tests/`, `git diff 12ef791 HEAD -- tests/`
và `git diff 72bc1b1 HEAD -- tests/` chỉ có dòng THÊM. Mọi lớp test cũ không đổi và vẫn qua (kể cả ca 14, 19, 23–27). Sau khi chạy
toàn bộ test, `git status --porcelain` giống hệt trước khi chạy (test không làm thay đổi file nào trong repo). Ghi trước → sau.

**AC3 — `.gitignore` (A).** Như bản đầu; Lần sửa 2 không đổi `.gitignore`.

**AC4 — Lưu trữ Kaggle (B).** Như bản đầu. Lần sửa 2 không đổi manifest (`git diff 72bc1b1 HEAD -- reports/step4_2026-09-26/archive/`
rỗng), không đổi `scripts/archive_step4_kaggle.py`, không chạy lệnh Kaggle nào.

**AC5 — REPORT sinh bằng script, tái lập.** Như Lần sửa 1 (so với P: JSON `==` sau khi bỏ `generated_by`, `review`,
`provenance.archive`, `limitations_data.untracked_unarchived_inputs`, và `inputs` có vai trò "review"/"archive manifest"; REPORT so
với P chỉ chạm các vùng đã liệt kê). Mọi lần sinh được commit: exit 0; header có đúng lệnh và HEAD `h`; `git diff h -- scripts/ src/
tests/` rỗng; `code_dirty = false`; chạy hai lần → `cmp` không khác.

**AC5b — So với `72bc1b1` (Lần sửa 2).** Gọi B'' là commit T3.3.
- `git diff 72bc1b1 B'' -- reports/step4_2026-09-26/REPORT.md` chỉ chạm: dòng Lệnh/HEAD; dòng §1.4 của `docs/reviews/02-review.md`
  (sha256 mới); đúng MỘT dòng Giới hạn (dòng chứa `ref`); nội dung sau `## 6. Review`.
- JSON ở `72bc1b1` và B'' bằng nhau (`==`) sau khi bỏ `generated_by`, `review`, phần tử `inputs` có vai trò "review", và
  `limitations_data.untracked_unarchived_inputs`. Riêng khóa đó: tập `path` trong `files`, `n`, `n_inputs` phải BẰNG nhau (Lần
  sửa 2 không đổi danh sách, chỉ phân loại nó).
- Ở B'': `n_required` và `n_optional` do script sinh. Reviewer đối chiếu với kết quả thực nghiệm của mình ở vòng 2 (5 bắt buộc, 3
  tùy chọn). Nếu khác thì ghi nguyên nhân; KHÔNG chỉnh tay.

**AC6 — G1, G2, G3 (`TestProposal4cCleanup`).** Như bản đầu; vẫn qua.

**AC7 — Phạm vi thay đổi.** Như Lần sửa 1. Lần sửa 2 chỉ được đổi `scripts/report_step4.py`, `tests/test_report_step4.py`,
`reports/step4_2026-09-26/{REPORT.md, step4_results.json}`, `docs/progress_log.md`, và commit `docs/reviews/02-review.md`,
`docs/plans/02-don-dep-sau-4c.md`. KHÔNG đổi: `backend/`, `src/`, `configs/`, `frontend/`, `data/`, `checkpoints/`, PREREG,
`history.json`, `metrics.json`, JSON 4a/4b, `docs/reviews/01-review.md`, `PROPOSAL_4c.md`, `scripts/archive_step4_kaggle.py`,
manifest, `.gitignore`. `git status` vẫn cho thấy 3 file data bị xóa của người dùng như trước.

**AC8 — Quy trình.** Mỗi commit mới ghi `impact` (symbol đã sửa) và `detect-changes --scope all` (không partial/truncated) trong
commit message. Progress_log có ĐÚNG MỘT dòng bảng cho kế hoạch 02 (dòng sẵn có được CẬP NHẬT, không thêm dòng): commit = mọi hash
(8 commit ở §0 + `514ad47`, `ae82625`, `208fc5f`, `72bc1b1` + A6, C3, B'', C4, C5); kết luận review = kết luận vòng 3 + lịch sử vòng
("vòng 1 CHANGES_REQUESTED: FAIL mục 13, câu tái tạo; vòng 2 CHANGES_REQUESTED mức thấp: vế 'mã 2' sai với 3/8 file; vòng 3 …");
việc tiếp theo = "Việc 4 (endpoint chuỗi landmark Cấp 1)". Các dòng ghi chú ngay dưới giữ đủ nội dung Lần sửa 1 (số test, số từ
PROPOSAL 545 + ghi chú PROPOSAL đổi sau quyết định, ref/số file/tổng byte từ manifest, lịch sử lệnh Kaggle của coder: `stage` exit 0;
`upload` ×3: exit 6 do 403 GetDatasetStatus, exit 6 do đường dẫn tương đối, exit 0; `verify` ×2: exit 6 do 404 DownloadDataset,
exit 0; lệnh chỉ đọc của reviewer; UNVERIFIED: `stage` không có file log, lệnh chỉ đọc của coder không có log, WIP lúc stage/upload),
và THÊM: số test trước → sau của Lần sửa 2; `n_required`/`n_optional` ở B''; "Lần sửa 2 không chạy lệnh Kaggle nào"; sửa cột
"kết luận review" đang ghi "vòng 2: chờ vslt-reviewer"; trạng thái A3 và §7.2 (chờ người dùng).

**AC9' — Lần sinh cuối chỉ thêm review vòng 3.** Gọi C5 là commit T5.3.
- `git diff B'' C5 -- reports/step4_2026-09-26/REPORT.md` chỉ chạm: dòng Lệnh/HEAD; dòng §1.4 của `docs/reviews/02-review.md`;
  nội dung sau `## 6. Review`. Dòng Giới hạn giống hệt (không có file đầu vào mới).
- JSON ở B'' và C5 bằng nhau (`==`) sau khi bỏ `generated_by`, `review`, và phần tử `inputs` có vai trò "review" (KHÔNG bỏ
  `untracked_unarchived_inputs`).
- §6 chứa review 02 (vòng 3 ở đầu) rồi review 01.

**AC10 — Review.** vslt-reviewer vòng 3 (`docs/reviews/02-review.md`): không FAIL cho các commit của việc này. Mục 13 PASS: reviewer
lặp lại thực nghiệm vòng 2 trên dữ liệu thật, ÍT NHẤT một file bắt buộc (vd. một log kernel, qua đổi đường dẫn trong đối số
`--kernel-logs` sang file không tồn tại) → exit 2, và `--segments <không tồn tại>` → exit 0, rồi đối chiếu với nhóm mà REPORT in.
Không di chuyển hay xóa file thật khi làm thực nghiệm. Mục 11 PASS (không lệnh Kaggle ghi mới); mục 3 PASS (AC2).

---

## 6. Rủi ro dữ liệu / ML

- **Lộ dữ liệu có giấy phép chưa rõ.** Dataset chỉ PRIVATE; `public=False` là hằng; test guard; metadata `isPrivate: true`; kiểm
  private hai nguồn. Không bao giờ gọi `datasets metadata --update`.
- **Khẳng định quá mức (Lần sửa 1–2).** REPORT chỉ được nói điều script đã kiểm: private (không nói ai được chia sẻ); danh sách
  đầu vào không track sinh từ `inputs` × git × manifest; hành vi khi thiếu file lấy từ cờ `required` do chính chỗ gọi `Inputs.add`
  đặt, và ca 29 kiểm cờ đó khớp hành vi thật (giả lập thiếu từng file). Hai lần FAIL trước đều do planner gõ sẵn câu mô tả hành vi
  mã mà không đối chiếu; từ nay câu mô tả hành vi phải có test chạy hành vi đó.
- **Giả lập bằng `patch` có giới hạn.** Ca 29 chỉ đúng nếu mọi chỗ kiểm tồn tại dùng `os.path.isfile`/`os.path.exists` (đúng tại
  `72bc1b1`, §2.3). Nếu sau này có chỗ đọc file không qua hai hàm đó, ca 29 có thể bỏ sót; reviewer kiểm thực nghiệm trên dữ liệu
  thật (AC10) để bù. Không dùng cách xóa file thật, vì đầu vào gồm file của người dùng (`checkpoints/`, `data/processed/`).
- **Báo cáo khác đi mà không báo lỗi.** Thiếu đầu vào tùy chọn làm REPORT lặng lẽ khác (vd. "KHÔNG CÓ (thiếu segments.csv)"). Lần
  sửa 2 chỉ NÓI RA điều này; không đổi hành vi (đổi thành bắt buộc là thay đổi hợp đồng CLI, không thuộc phạm vi).
- **Danh sách phụ thuộc trạng thái git lúc sinh.** Commit mọi đầu vào mới/sửa (file review) TRƯỚC khi sinh; ca 27 và 32 báo khi
  REPORT đã cũ so với git.
- **Pathspec.** `--literal-pathspecs` tránh việc tên file có `*`, `?`, `[` bị hiểu là glob.
- **Không có số liệu ML mới.** AC5/AC5b/AC9' chứng minh mọi giá trị JSON cũ không đổi.
- **File `alphabet_real_best.pt` đang track.** Quyết định thuộc người dùng (§7.1).

---

## 7. Điểm dừng

- **Trước khi code Lần sửa 2: KHÔNG có điểm dừng.** Không đổi model mặc định, không cần dữ liệu người dùng, không đụng thay đổi chưa
  commit của người dùng, không có hành động không hoàn tác, không lệnh Kaggle, không viết lại lịch sử, không A3.
- **Sau T4:** đây là vòng CODE↔REVIEW cuối (3/3). Nếu vòng 3 còn FAIL → orchestrator DỪNG, ghi progress_log, báo người dùng kèm
  đề xuất của reviewer (a/b ở review vòng 2 mục "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH"). Không tự mở vòng 4.
- **§7.1 — CẦN NGƯỜI DÙNG (A3, không chặn phần còn lại).**
  > `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` (checkpoint Cấp 1 thật, train trên bộ hauuto giấy
  > phép chưa rõ) đang được git track (thêm ở `429b289`, đã có trên `origin/fix/audit-round2`). `.gitignore` mới không gỡ được nó;
  > `git rm --cached` cũng không xóa được nó khỏi lịch sử đã push. Chọn một: (a) giữ track; (b) lưu vào dataset Kaggle private (kế
  > hoạch nhỏ riêng, cần tạo version) rồi `git rm --cached`; (c) `git rm --cached` không lưu trữ.
  Chưa có câu trả lời thì không làm gì với file này.
- **§7.2 — Câu hỏi không chặn:** có lưu thêm 4 log kernel, `reports/unified_run_2026-09-25/run_seed43/history.json`, và (nếu được
  phép) `data/processed/vslgh_segments/segments.csv`, `checkpoints/*.pt` vào dataset private (version mới, kế hoạch nhỏ riêng)
  không? Nếu có, danh sách trong câu Giới hạn tự ngắn lại khi sinh lại REPORT với manifest mới.
- **Không bắt buộc:** PROPOSAL_4c.md đã sửa câu chữ sau khi người dùng quyết B (dòng 6, 11, 17, 32); nội dung quyết định không đổi.
- Sau T5: KHÔNG có điểm dừng bắt buộc. Orchestrator chuyển sang Việc 4.
