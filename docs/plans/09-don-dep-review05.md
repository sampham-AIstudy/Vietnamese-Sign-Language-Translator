ĐANG LÀM

# Kế hoạch 09 — Dọn dẹp 3 góp ý mức thấp từ review 05

Nguồn: `docs/reviews/05-review.md` dòng 54 (khuyến nghị triển khai (1)(2)(3)); bảng mục 7 (dòng 19, `code_dirty`),
mục 11 (dòng 23, `archive_name`), mục 13 (dòng 25, README). Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`).
Backlog: `docs/STATE.md` mục "Backlog còn lại" 8 (dòng "Thấp, từ review 05").

Không CẦN NGƯỜI DÙNG (xem §7). Có MỘT quyết định thiết kế lệch chữ so với yêu cầu gốc, có lý do (§3.2, "Quyết định D1").

## 1. Mục tiêu và DoD

**Mục tiêu.** (1) `restore` của `scripts/archive_private_kaggle.py` không tin `archive_name` trong manifest: kiểm, cho MỌI phần
tử, rằng `archive_name` đúng bằng tên suy ra từ `local_path` theo quy tắc của script đã sinh manifest, trước khi tạo thư mục,
tải hay ghi bất cứ gì; sai → exit 2, không ghi gì. (2) `verify` ghi `code_dirty` + `code_dirty_files` vào `generated_by` của
manifest (trạng thái `git status --porcelain -- scripts src tests backend` lúc verify; `null` khi git không chạy được — không
bao giờ ghi `false` khi không biết). (3) README mục "Artifact không nằm trong git" nói rõ `alphabet_real_best.pt` vẫn còn trong
lịch sử git đã push (trỏ `docs/data_registry.md` §1b).

**DoD phục vụ** (`docs/prompts/autopilot.md` §1):
- DoD 9 (tài liệu trung thực, mục Giới hạn): câu README hiện có thể đọc thành "chưa từng commit" (review 05 mục 13).
- DoD 7 (kiểm thử): test mới cho hai hành vi của script lưu trữ, có kiểm đột biến.
- Quy tắc cứng §4 "mọi số liệu từ JSON có lệnh + commit hash": manifest tự ghi mã có sạch hay không (review 05 mục 7: khẳng định
  "git status rỗng lúc verify" hiện chỉ nằm ngoài repo).
- An toàn khôi phục dữ liệu (DoD 1 clone sạch → khôi phục artifact theo README / `docs/CLOUD.md` §3).

## 2. Hiện trạng

### 2.1 `scripts/archive_private_kaggle.py` (435 dòng, tạo ở kế hoạch 05)
- Import dùng chung từ script anh em (`:45-48`): `import archive_step4_kaggle as A` và `ArchiveError, check_dataset_ref,
  check_staging, git_head, kaggle_api, parse_sums, pkg_version, private_from_list, private_from_metadata, read_metadata,
  remote_files, require_outside_repo, sha256_file, sums_text, upload, wait_ready`. Chưa import `subprocess`.
- Quy ước mã thoát (docstring `:26-29`): 0 ok; **2** thiếu input / tham số sai / đường dẫn tạm trong repo / ...; **3** sha256,
  tập file, kích thước lệch hoặc đích restore có sha khác; 4 không xác minh được private; 5 slug đã có; 6 Kaggle/API/mạng.
- `check_local_path` (`:103-111`): `local_path` tương đối, `/`, không `..`, không ổ đĩa, không `\` → sai thì `ArchiveError(2)`.
- `_entry` (`:121-127`): khi lưu trữ, `archive_name = local_path.replace("/", "__")`.
- `verify` (`:248-313`): `generated_by` (`:291-295`) = `{script, command, git_commit, kaggle_version, kagglesdk_version,
  verified_at_utc}`. **Thiếu:** không ghi mã có bẩn không. Manifest ghi qua `.tmp` + `os.replace` (`:307-311`).
- `restore` (`:319-379`): đọc manifest; lấy `dataset.ref` và `files[*].{local_path, archive_name, sha256}` (`:321-326`, thiếu
  khóa → 2); `check_dataset_ref`; `--download-dir` ngoài repo; `--root` khác ROOT phải ngoài repo; `check_local_path` cho mọi
  phần tử (`:331-332`); lọc `--only` (`:333-338`); TẠO `download_dir` + tải (`:340-345`); đọc
  `os.path.join(dl, e["archive_name"])` và so sha (`:346-351`); kiểm toàn bộ đích rồi mới ghi (`:353-377`).
  **Thiếu:** `archive_name` không được kiểm. Vì `os.path.join(dl, archive_name)` nhận cả đường dẫn tuyệt đối và `..`, một
  manifest sai có thể khiến restore đọc file NGOÀI thư mục tải và chép nó vào `local_path` nếu sha trùng (review 05 dòng 23).
- Guard nguồn (`tests/test_archive_private_kaggle.py:483-488`, AC9-12 kế hoạch 05): trong file script CẤM các chuỗi
  `public=True`, `"--public"`, `dataset_metadata_update`, `dataset_delete`, `dataset_create_version`, `metadata --update`
  (kể cả trong chú thích/docstring).

### 2.2 Script anh em `scripts/archive_step4_kaggle.py` — KHÔNG được sửa
- `tests/test_archive_private_kaggle.py:490-495` (`test_13_step4_script_unchanged`) FAIL nếu
  `git diff --name-only b337aee -- scripts/archive_step4_kaggle.py` khác rỗng. Mọi hàm mới phải nằm trong
  `archive_private_kaggle.py`.
- `flat_name(run_dir, filename)` (`:84-91`): tên phẳng của bước 4 = thư mục run BỎ tiền tố `reports/`, `/`→`__`, + `__<file>`.
  `plan_files` (`:94-115`): `local_path = dir + "/" + fname`, `archive_name = flat_name(dir, fname)`.
- `verify` của bước 4 (`:354-416`) ghi `generated_by.script = "scripts/archive_step4_kaggle.py"`; test
  `tests/test_archive_step4_kaggle.py:340-346` (test_12) khóa CHÍNH XÁC tập khóa `generated_by` của manifest bước 4 → kế hoạch này
  không đổi manifest bước 4 (không sửa script đó nên tự nhiên thỏa).

### 2.3 Hai manifest đã commit (bằng chứng lịch sử, KHÔNG sửa)
- `reports/private_archive_2026-09-28/kaggle_archive_manifest.json`: `generated_by.script = scripts/archive_private_kaggle.py`,
  `git_commit f7ad8d2`; 13 phần tử, `archive_name == local_path.replace('/', '__')` (vd. `:17`/`:22`, `:101`/`:106`).
  Không có `code_dirty`.
- `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`: sinh bởi `scripts/archive_step4_kaggle.py`;
  `archive_name` theo `flat_name`, vd. `:17` `step4_2026-09-26__runs__dict_keepz_360__stgcn_unified_best.pt` với `:19`
  `local_path` `reports/step4_2026-09-26/runs/dict_keepz_360/stgcn_unified_best.pt` → **KHÁC** `local_path.replace('/', '__')`
  (= `reports__step4_2026-09-26__...`). Không có `code_dirty`.
- **Manifest bước 4 đang được khôi phục bằng `archive_private_kaggle.py restore`:** `docs/CLOUD.md:33-35` (khôi phục cả hai dataset
  bằng lệnh `restore`), `docs/plans/08-segmenter-live.md:123` (checkpoint H-keepz-360 từ `phmvnsm33/vslt-step4-artifacts` qua
  `scripts/archive_private_kaggle.py restore`). Với mã hiện tại, luồng này chạy được (đủ khóa `local_path/archive_name/sha256`,
  tên file trên Kaggle = `archive_name`). → Áp NGUYÊN VĂN quy tắc `local_path.replace('/', '__')` cho mọi manifest sẽ làm
  restore bước 4 trả exit 2: hồi quy. Xem Quyết định D1 (§3.2).

### 2.4 Test hiện có (không sửa)
- `tests/test_archive_private_kaggle.py` (27 test theo review 05 mục 2): `Base` (`:66-129`, thư mục tạm NGOÀI repo, fixture byte
  nhỏ, helper `code/plan/stage/verify/created_api`), `FakeApi` (`:39-54`, kế thừa FakeApi bước 4), `TestRestore` (`:411-478`:
  setUp chạy stage + verify với API giả; `restore()` helper; `snapshot()`), `TestSourceGuard` (`:482-495`). `test_09`
  (`:351-374`) chỉ kiểm `generated_by.script` và `command` → thêm khóa vào `generated_by` không làm test cũ đổi kết quả.
- `tests/test_archive_step4_kaggle.py`: `FakeApi` (`:37-99`, `dataset_download_files` chép mọi file trong staging trừ
  `dataset-metadata.json`, có `download_tamper`), `Base` (`:102-151`, RUNS `reports/step4_x/runs/run_a`, `reports/unified_y/run`
  → `archive_name` bỏ `reports/`), 24 test.
- `tests/test_private_artifacts.py` (8 test): đọc manifest private mới nhất + repo thật; không phụ thuộc `generated_by`.
- `tests/` không có `__init__.py` (namespace package); các test đã import chéo `from tests.test_archive_step4_kaggle import ...`
  khi chạy `python -m unittest` từ gốc repo.

### 2.5 README và data_registry
- `README.md:256-267` mục "### Artifact không nằm trong git"; dòng `:258` nguyên văn:
  `Checkpoint, logit và log có dữ liệu giấy phép chưa rõ không được commit; chúng nằm trong 2 dataset Kaggle private:`
- `docs/data_registry.md:41-44` §1b: đã nói rõ file được commit ở `429b289`, push lên `origin/fix/audit-round2`, gỡ khỏi index ở
  B7, "history not rewritten, so the file is still in the pushed history". Không sửa file này.

### 2.6 Quy ước `code_dirty` đã có trong repo (để nhất quán)
- `scripts/report_step4.py:1119-1124`: `"code_dirty": bool(dirty), "code_dirty_files": dirty.splitlines() if dirty else []`
  (pathspec `scripts src tests`).
- `scripts/hand_live_check.py:326`, `scripts/live_segment_check.py:150`: `code_dirty` bool.

## 3. Thiết kế

### 3.1 Luồng dữ liệu (chỉ phần đổi, đánh dấu ★)
```
restore --manifest M --download-dir X [--root R] [--only ...]
  đọc M: dataset.ref, ★generated_by.script, files[*].{local_path, archive_name, sha256}   (thiếu khóa → 2)
  ─► check_dataset_ref; X ngoài repo; R ≠ ROOT thì R ngoài repo
  ─► với MỌI phần tử của M (trước --only):
        check_local_path(local_path)                                                    (sai → 2)
        ★archive_name == expected_archive_name(generated_by.script, local_path)          (sai/không hỗ trợ → 2)
  ─► lọc --only ─► tạo X + tải ─► so sha ─► kiểm toàn bộ đích ─► ghi       (KHÔNG đổi)

verify ... (không đổi đến khi dựng manifest)
  ─► ★(code_dirty, code_dirty_files) = code_status()      # git status --porcelain -- scripts src tests backend
  ─► generated_by += {code_dirty, code_dirty_files} ─► ghi manifest (.tmp + os.replace)   (phần còn lại không đổi)
```
Không chạy model, không đọc dữ liệu học, không đụng module tiền xử lý chung (`src/data/*`, `harmonize`, extractor): không áp dụng.
Không gọi Kaggle thật ở bất kỳ bước nào (test dùng API giả; coder KHÔNG chạy `stage/upload/verify/restore` thật, KHÔNG sinh manifest
mới trong `reports/`).

### 3.2 (1) Kiểm `archive_name` trong `restore`

**Quyết định D1 (planner, lệch chữ so với yêu cầu, không lệch ý):** tên mong đợi được SUY RA từ `local_path` theo quy tắc của
script đã sinh manifest (`generated_by.script`), không phải luôn luôn `local_path.replace('/', '__')`.
- Manifest của chính script này (`scripts/archive_private_kaggle.py`): đúng nguyên văn review — `local_path.replace("/", "__")`.
- Manifest bước 4 (`scripts/archive_step4_kaggle.py`): `A.flat_name(posixpath.dirname(local_path), posixpath.basename(local_path))`
  — chính hàm đã sinh tên gốc (dùng lại, không chép luật, không sửa script bước 4). Với `local_path = dir + "/" + fname` như
  `A.plan_files` tạo ra, biểu thức này trả đúng `flat_name(dir, fname)`.
- `generated_by.script` khác hai giá trị trên (hoặc không phải chuỗi) → exit 2 ("manifest sinh bởi script không được hỗ trợ").
- Lý do: (i) giữ mục tiêu an toàn của review (tên đọc trong thư mục tải luôn suy ra được, không `..`, không tuyệt đối — vì
  `check_local_path` đã chặn các dạng đó trên `local_path`); (ii) áp nguyên văn sẽ làm restore manifest bước 4 trả 2, phá luồng
  `docs/CLOUD.md` §3 và `docs/plans/08-segmenter-live.md:123` (§2.3); (iii) không cần sửa manifest đã commit.

**Hợp đồng hàm mới (trong `scripts/archive_private_kaggle.py`):**
```
STEP4_SCRIPT = "scripts/archive_step4_kaggle.py"          # hằng; SCRIPT đã có = "scripts/archive_private_kaggle.py"

expected_archive_name(generator, local_path) -> str
  generator == SCRIPT        -> local_path.replace("/", "__")
  generator == STEP4_SCRIPT  -> A.flat_name(posixpath.dirname(local_path), posixpath.basename(local_path))
  khác (kể cả None / không phải str) -> raise ArchiveError(2, "...không được hỗ trợ...")
```
(`local_path` đã qua `check_local_path` trước khi gọi; hàm được phép gọi lại `check_local_path`.)

**Sửa `restore` (chỉ các điểm sau):**
1. Trong khối `try` đọc manifest (`:321-326`): thêm `generator = m["generated_by"]["script"]` → thiếu khóa rơi vào nhánh
   `KeyError/TypeError` sẵn có → `ArchiveError(2, "manifest thiếu khóa ...")`.
2. Trong vòng lặp `for e in entries:` sẵn có (`:331-332`), ngay sau `check_local_path(e["local_path"])`: so `e["archive_name"]` với
   `expected_archive_name(generator, e["local_path"])`; khác → `ArchiveError(2, ...)`; thông báo nêu `local_path`, `archive_name`
   nhận được (repr) và tên mong đợi, kèm "không tải, không ghi gì".
3. Vị trí bắt buộc: TRƯỚC lọc `--only` (kiểm cả phần tử không được chọn) và TRƯỚC `os.makedirs(download_dir)` /
   `api.dataset_download_files`. Không đổi thứ tự hay hành vi các bước sau.
- Mã lỗi 2 (không phải 3): đây là manifest/đầu vào sai dạng, cùng loại với `check_local_path` và "manifest thiếu khóa" (quy ước
  docstring `:26-29`); 3 dành cho lệch sha/tập file/kích thước. Cập nhật docstring mã thoát: thêm "manifest có archive_name không
  khớp local_path / script sinh manifest không được hỗ trợ" vào nhóm 2.
- `restore` KHÔNG đọc `code_dirty`/`code_dirty_files` → manifest cũ (không có hai khóa) đọc được như trước.

### 3.3 (2) `code_dirty` trong manifest của `verify`

**Định dạng (quyết định của planner):** thêm đúng 2 khóa vào `generated_by`:
```
"code_dirty":       true | false | null
"code_dirty_files": ["<dòng porcelain>", ...] | [] | null
```
- Phạm vi: `git status --porcelain -- scripts src tests backend` chạy ở `cwd=ROOT` (hằng `CODE_DIRS = ("scripts", "src",
  "tests", "backend")`). Mọi dòng khác rỗng của stdout được giữ NGUYÊN VĂN, đúng thứ tự git in (không strip đầu dòng: mã trạng thái
  porcelain có thể bắt đầu bằng dấu cách, vd. `" M scripts/x.py"`). File untracked trong 4 thư mục (`?? ...`) tính là bẩn.
- `true` ⇔ có ≥ 1 dòng; `false` ⇔ git chạy thành công (returncode 0) và 0 dòng.
- `null` + `null` khi KHÔNG biết: git không có (`FileNotFoundError`/`OSError`), `subprocess.SubprocessError` (gồm
  `TimeoutExpired`), hoặc returncode ≠ 0 (vd. không phải repo git). Không bao giờ ghi `false` trong các trường hợp này; `verify` không
  thất bại vì lý do này (nhất quán với `git_head()` trả `None` khi git lỗi, `archive_step4_kaggle.py:197-199`).
- Hai khóa đi cặp, cùng tên với `scripts/report_step4.py:1123-1124` (khác: pathspec có thêm `backend`, và `null` khi không biết).
- Manifest ghi vào `reports/...` (ngoài 4 thư mục) nên việc ghi manifest không đổi cờ.

**Hợp đồng hàm mới:**
```
code_status(run=subprocess.run, root=ROOT) -> (code_dirty: bool|None, code_dirty_files: list[str]|None)
  run(["git", "status", "--porcelain", "--", "scripts", "src", "tests", "backend"],
      cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60)
  - ngoại lệ OSError / subprocess.SubprocessError      -> (None, None)
  - returncode != 0                                     -> (None, None)
  - lines = [ln for ln in stdout.splitlines() if ln.strip()]
  -> (bool(lines), lines)
```
- `verify`: gọi `code_status()` qua TÊN TOÀN CỤC của module (để test `mock.patch.object(P, "code_status", ...)` có hiệu lực), ngay
  trước khi dựng `manifest` (cùng chỗ gọi `git_head()`); thêm 2 khóa. Không đổi khóa, thứ tự kiểm hay đường lỗi nào khác.
  Được phép (không bắt buộc) in thêm 1 dòng cảnh báo ra stdout khi `code_dirty` khác `False`; `verify` không từ chối vì bẩn.
- Cập nhật docstring module: manifest `generated_by` có `code_dirty`/`code_dirty_files` (ý nghĩa của `null`).
- Chỉ sửa `scripts/archive_private_kaggle.py`; thêm `import posixpath`, `import subprocess`. Docstring/chú thích mới KHÔNG chứa chuỗi
  bị guard cấm (§2.1).

### 3.4 (3) README — thay đúng 1 dòng
Dòng `README.md:258`, cũ:
```
Checkpoint, logit và log có dữ liệu giấy phép chưa rõ không được commit; chúng nằm trong 2 dataset Kaggle private:
```
mới (nguyên văn, chỉ chèn một cụm trong ngoặc trước dấu `;`):
```
Checkpoint, logit và log có dữ liệu giấy phép chưa rõ không được commit (riêng `alphabet_real_best.pt` đã từng được commit và vẫn còn trong lịch sử git đã push, xem `docs/data_registry.md` §1b); chúng nằm trong 2 dataset Kaggle private:
```
Không đổi dòng nào khác của README. Nội dung khẳng định có bằng chứng: `docs/data_registry.md:44`, test
`tests/test_private_artifacts.py:95-103` (`test_h_history_not_rewritten`), review 05 S1/S3.

### 3.5 Test mới — file MỚI `tests/test_archive_private_kaggle_r05.py`
Lựa chọn: file mới (không thêm vào file cũ) để ba file test cũ giữ nguyên từng byte; lệnh AC2 thêm 1 module.
- Import fixture dưới dạng MODULE: `import tests.test_archive_private_kaggle as T0`, `import tests.test_archive_step4_kaggle as S4`,
  `import archive_private_kaggle as P`, `import archive_step4_kaggle as A` (cùng cách chèn `sys.path` như file cũ). KHÔNG
  `from ... import TestRestore`/lớp có `test_*` (loader sẽ chạy lặp). Lớp mới kế thừa `T0.Base` / `S4.Base` (không có test).
- Mọi lời gọi `P.restore`, `P.verify`, `P.main` truyền API giả (`T0.FakeApi` / `S4.FakeApi`); không gọi `kaggle_api()`; thư mục tạm
  ngoài repo (`Base.setUp` đã `assertFalse(A.inside(self.d))`).
- Danh sách test bắt buộc: §5 AC3, AC4.

## 4. Chia việc
(đang viết)

## 5. Tiêu chí chấp nhận
(đang viết)

## 6. Rủi ro dữ liệu/ML
(đang viết)

## 7. Điểm dừng
(đang viết)
