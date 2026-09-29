Trạng thái: XONG (chờ orchestrator)

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
Lựa chọn: file mới (không thêm vào file cũ) để ba file test cũ giữ nguyên từng byte; lệnh AC8 thêm 1 module.
- Import fixture dưới dạng MODULE: `import tests.test_archive_private_kaggle as T0`, `import tests.test_archive_step4_kaggle as S4`,
  `import archive_private_kaggle as P`, `import archive_step4_kaggle as A` (cùng cách chèn `sys.path` như file cũ). KHÔNG
  `from ... import TestRestore`/lớp có `test_*` (loader sẽ chạy lặp). Lớp mới kế thừa `T0.Base` / `S4.Base` (không có test).
- Mọi lời gọi `P.restore`, `P.verify`, `P.main` truyền API giả (`T0.FakeApi` / `S4.FakeApi`); không gọi `kaggle_api()`; thư mục tạm
  ngoài repo (`Base.setUp` đã `assertFalse(A.inside(self.d))`).
- Danh sách test bắt buộc: §5 AC3, AC4.

## 4. Chia việc

**Quy tắc chung mọi bước**
- Trước khi sửa hàm CÓ SẴN: `npx --yes gitnexus@1.6.12 impact <symbol> --direction upstream --repo .` (B1: `restore`; B2: `verify`).
  `verify` trùng tên với `archive_step4_kaggle.verify` → ghi rõ kết quả thuộc file nào; nếu công cụ gộp hoặc trả `UNKNOWN`/0 caller →
  bổ sung text search (`grep -rn "restore(" scripts tests`, `grep -rn "verify(" scripts tests`) và ghi cả hai. HIGH/CRITICAL → ghi
  cảnh báo + giải thích. Hàm MỚI (`expected_archive_name`, `code_status`) không cần impact. Index cũ → chạy analyze theo
  `.claude/skills/gitnexus-cli/SKILL.md` trước. GitNexus không chạy được → DỪNG, báo orchestrator (§7), không sửa hàm.
- Trước MỖI commit: `npx --yes gitnexus@1.6.12 detect-changes --scope all --repo .`; `partial`/`truncated: true` → chạy lại; ghi
  risk vào message commit (HIGH/CRITICAL phải có giải thích).
- Test trước: viết test → chạy → ghi id test FAIL/ERROR vào `docs/plans/09-progress.md` và message commit → sửa mã → chạy lại OK.
- `git add` theo đường dẫn cụ thể (không `git add -A`/`git add .`). Không sửa `docs/STATE.md`, `docs/progress_log.md` (orchestrator).
- Log và file tạm: `/home/user/_plan09_tmp/` (ngoài repo).

| Bước | Nội dung | Phụ thuộc | Ước lượng |
|---|---|---|---|
| **B0** | Mốc. `P9=$(git rev-parse --short HEAD)`; kiểm P9 là commit chứa kế hoạch này (`git log -1 --format=%h -- docs/plans/09-don-dep-review05.md`). `mkdir -p /home/user/_plan09_tmp`; `git status --porcelain > /home/user/_plan09_tmp/b0_status.txt`; `sha256sum reports/private_archive_2026-09-28/kaggle_archive_manifest.json reports/step4_2026-09-26/archive/kaggle_archive_manifest.json > /home/user/_plan09_tmp/b0_sha.txt`. Chạy lệnh AC6 với 3 module CŨ (bỏ module mới) → `b0_ac6.log` (phải OK, 0 skip). Chạy lệnh AC8 với 29 module (bỏ module mới) → `b0_ac8.log`; trích danh sách id FAIL / ERROR / skipped (sort) → `b0_fail.txt`, `b0_error.txt`, `b0_skip.txt`. Tạo `docs/plans/09-progress.md` (P9, dòng tổng kết của 2 log, đường dẫn log). detect-changes. Commit `09 B0: mốc`. | — | 0.25 giờ |
| **B1** | Restore kiểm `archive_name` (§3.2). impact `restore`. Viết test E1, E2, R1, R2, R3, R4, R6, R7 (§5 AC3) → chạy → ghi FAIL/ERROR trước sửa (R6 được phép PASS trước sửa: đó là test không hồi quy). Sửa `restore` + thêm `STEP4_SCRIPT`, `expected_archive_name`, docstring mã thoát. Chạy lệnh AC6 (4 module) → OK, 0 skip. detect-changes. Commit `09 B1: restore kiểm archive_name theo script sinh manifest`. | B0 | 0.75 giờ |
| **B2** | `code_dirty` (§3.3). impact `verify`. Viết test C1–C5, R5 (§5 AC4) → FAIL trước sửa → thêm `CODE_DIRS`, `code_status`, 2 khóa trong `verify`, docstring. Lệnh AC6 → OK, 0 skip. detect-changes. Commit `09 B2: verify ghi code_dirty vào manifest`. | B1 (cùng file) | 0.5 giờ |
| **B3** | README 1 dòng (§3.4, AC5). Đột biến AC7 (script ngoài repo). Lệnh AC8 đầy đủ (30 module) → so với B0. `git status --porcelain` so `b0_status.txt`; sha256 hai manifest so `b0_sha.txt`. Cập nhật `09-progress.md`: bảng AC1–AC9 (PASS/FAIL + bằng chứng: lệnh + dòng output). detect-changes. Commit `09 B3: README + đóng việc`. Orchestrator gọi vslt-reviewer. | B2 | 0.5 giờ |

Tổng ước lượng ≈ 2 giờ; GPU 0; không Kaggle; không cài gói; mạng chỉ cho `npx gitnexus` (theo CLAUDE.md).

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG được đổi; chỉ planner đổi, có ghi lý do)

Ký hiệu: `P9` = HEAD lúc B0 (commit chứa kế hoạch này). `ROOT` = gốc repo. Mọi lệnh chạy từ `ROOT` trên cloud.

**AC1 — Phạm vi file.**
- `git diff --name-status P9 HEAD` đúng bằng tập (không thừa, không thiếu):
  ```
  M	README.md
  A	docs/plans/09-progress.md
  M	scripts/archive_private_kaggle.py
  A	tests/test_archive_private_kaggle_r05.py
  ```
- `git diff --numstat P9 HEAD -- README.md` → `1	1	README.md`.
- `git diff --stat P9 HEAD -- scripts/archive_step4_kaggle.py tests/test_archive_private_kaggle.py tests/test_archive_step4_kaggle.py
  tests/test_private_artifacts.py reports/ docs/data_registry.md backend/ frontend/ src/ docs/STATE.md docs/progress_log.md
  docs/phase12_api.md scripts/smoke_test_phase12.py docs/plans/` → chỉ có `docs/plans/09-progress.md` (không file nào khác).
- `git diff P9 HEAD -- tests/ | grep '^-' | grep -v '^---' | wc -l` → `0`.

**AC2 — Hai manifest đã commit không đổi.** `sha256sum` hai file ở B3 == `b0_sha.txt` (`diff` rỗng); cả hai không xuất hiện trong
`git diff --name-only P9 HEAD`.

**AC3 — Test mới cho (1) `restore`** (trong `tests/test_archive_private_kaggle_r05.py`; mỗi mục ≥ 1 method, biến thể dùng `subTest`):
- **E1** `P.expected_archive_name`: `(P.SCRIPT, "a/b/c.pt")` → `"a__b__c.pt"`;
  `(P.STEP4_SCRIPT, "reports/step4_x/runs/run_a/stgcn_unified_best.pt")` → `"step4_x__runs__run_a__stgcn_unified_best.pt"`;
  `(P.STEP4_SCRIPT, "checkpoints/x.pt")` → `"checkpoints__x.pt"`; generator `"scripts/other.py"`, `None`, `123` → `ArchiveError`
  với `code == 2`. `P.SCRIPT == "scripts/archive_private_kaggle.py"`, `P.STEP4_SCRIPT == "scripts/archive_step4_kaggle.py"`.
- **E2** hai manifest THẬT đã commit (chỉ đọc file): `generated_by.script` lần lượt == `P.SCRIPT` (private 2026-09-28) và
  `P.STEP4_SCRIPT` (bước 4); `len(files) > 0`; với MỌI phần tử `P.expected_archive_name(script, f["local_path"]) == f["archive_name"]`;
  `"code_dirty" not in generated_by` (định dạng cũ). Với manifest bước 4: có ≥ 1 phần tử `archive_name != local_path.replace("/", "__")`.
- **R1** (lớp kế thừa `T0.Base`; setUp: `stage` + `verify(created_api())` như `T0.TestRestore`; `root`, `rdl` là thư mục tạm chưa
  tồn tại). 3 subTest, mỗi cái ghi manifest đã sửa ra file riêng, đổi `archive_name` của phần tử có `local_path == T0.REAL_RUN` thành:
  (a) `"evil__copy.pt"`, file này được THÊM vào staging (FakeApi tải mọi file staging) với đúng byte của REAL_RUN trong fixture;
  (b) `"../evil_rel.bin"`, tạo trước `<rdl>/evil_rel.bin` với đúng byte đó;
  (c) đường dẫn tuyệt đối `<self.d>/evil_abs.bin` với đúng byte đó.
  Mỗi subTest dùng FakeApi mới: mã trả về `2`; `api.calls == []`; `<root>` không có file nào; (a),(c): `<rdl>` không tồn tại;
  (b): `os.listdir(<rdl>) == ["evil_rel.bin"]`. (Fixture được dựng để khi BỎ kiểm thì cả 3 ca trả 0 và ghi file — AC7 M1 chứng minh.)
- **R2** `--only`: sai `archive_name` (như R1a) ở phần tử `checkpoints/alphabet_best.pt` (KHÔNG được chọn), gọi `only=[T0.REAL_RUN]`
  → `2`, `api.calls == []`, `<root>` rỗng.
- **R3** script sinh manifest: `generated_by.script = "scripts/other.py"` → `2`; xóa hẳn khóa `generated_by` → `2`; cả hai
  `api.calls == []`.
- **R4** CLI: `P.main(["restore", "--manifest", <M của R1a>, "--download-dir", <rdl>, "--root", <root>], api=<FakeApi>)` → `2`;
  stderr bắt đầu bằng `archive_private_kaggle:` và chứa `T0.REAL_RUN`.
- **R6** manifest bước 4 (lớp kế thừa `S4.Base`; setUp: `A.stage` + `A.verify` với `S4.FakeApi` đã created, như `S4.TestVerify`):
  `P.restore(<manifest bước 4>, <rdl tạm>, S4.FakeApi(staging=self.staging), root=<root tạm>)` → `0`; mọi `files[*]` có mặt dưới
  root với sha256 == manifest; assert fixture có ≥ 1 phần tử `archive_name != local_path.replace("/", "__")`.
- **R7** manifest bước 4 bị sửa: 1 phần tử đổi `archive_name` thành `local_path.replace("/", "__")` → `2`, `api.calls == []`, root rỗng.

**AC4 — Test mới cho (2) `code_dirty` + tương thích manifest cũ** (cùng file):
- **C1** `P.code_status(run=fake)`, fake trả `returncode=0, stdout=""` → `(False, [])` (`assertIs(r[0], False)`); fake ghi đối số:
  đối số vị trí đầu == `["git", "status", "--porcelain", "--", "scripts", "src", "tests", "backend"]`;
  `os.path.normcase(kwargs["cwd"]) == os.path.normcase(ROOT)`; `"timeout" in kwargs`.
- **C2** stdout `" M scripts/a.py\n?? tests/b.py\n\n"` → `(True, [" M scripts/a.py", "?? tests/b.py"])` (giữ dấu cách đầu dòng).
- **C3** không biết → `(None, None)` (`assertIsNone` cả hai), 4 subTest: returncode `128`; fake raise `FileNotFoundError`; raise
  `subprocess.TimeoutExpired(cmd, 60)`; raise `OSError`.
- **C4** git thật, không mock: `r = P.code_status()`; `assertIsInstance(r[0], bool)`; `r == (bool(lines), lines)` với `lines` tính
  độc lập trong test bằng `subprocess.run` cùng lệnh, `cwd=ROOT`, lọc dòng rỗng như §3.3. Không assert giá trị (repo có thể bẩn lúc chạy).
- **C5** `verify` ghi manifest (lớp kế thừa `T0.Base`, setUp: `stage`): với mỗi `v` trong `(True, [" M scripts/x.py"])`,
  `(False, [])`, `(None, None)` (subTest), `with mock.patch.object(P, "code_status", return_value=v)`: verify với `created_api()` →
  `0`; `assertIs(m["generated_by"]["code_dirty"], v[0])`; `m["generated_by"]["code_dirty_files"] == v[1]`;
  `set(m["generated_by"]) == {"script", "command", "git_commit", "kaggle_version", "kagglesdk_version", "verified_at_utc",
  "code_dirty", "code_dirty_files"}`; `set(m) == {"generated_by", "dataset", "files", "sha256sums_file", "verified"}`; với
  `(None, None)`: nội dung file manifest chứa chuỗi `"code_dirty": null`.
- **R5** tương thích: manifest do `verify` (fixture) sinh, XÓA `code_dirty` và `code_dirty_files` khỏi `generated_by` (`pop(..., None)`)
  → `P.restore` → `0`, mọi file ghi dưới root với sha256 == manifest.

**AC5 — README.** `git diff -U0 P9 HEAD -- README.md`: đúng 1 dòng `-` BẰNG dòng cũ §3.4 và đúng 1 dòng `+` BẰNG dòng mới §3.4
(so chuỗi nguyên văn). `grep -c 'xem `docs/data_registry.md` §1b' README.md` → `1`.

**AC6 — Các module lưu trữ, 0 skip.**
`PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_archive_private_kaggle tests.test_archive_private_kaggle_r05 tests.test_archive_step4_kaggle tests.test_private_artifacts -v`
→ dòng cuối `OK` (không `(skipped=`), 0 dòng `... skipped`, 0 `FAIL`/`ERROR`; `Ran` = (số test 3 module cũ ở `b0_ac6.log`) + (số test
module mới, đếm trong output). Ghi cả hai số vào progress (lấy từ output, không gõ tay ước lượng).

**AC7 — Đột biến (trong bộ nhớ, không sửa file repo).** Script ngoài repo `/home/user/_plan09_tmp/mut.py`: đọc
`scripts/archive_private_kaggle.py`, mỗi đột biến áp thay thế chuỗi (assert đoạn gốc xuất hiện đúng 1 lần), `exec` mã đã đổi vào
`P.__dict__` của module đã import, chạy các test của `tests.test_archive_private_kaggle_r05` trong tiến trình, ghi id FAIL/ERROR; nạp
lại mã gốc trước đột biến kế tiếp. Không đột biến → mọi test module mới OK. Mỗi đột biến phải làm FAIL/ERROR ít nhất các test ghi:

| # | Đột biến | Test phải bắt |
|---|---|---|
| M1 | bỏ kiểm `archive_name` trong `restore` (lệnh raise không bao giờ chạy) | R1 (cả 3 subTest a, b, c), R2, R4, R7 |
| M2 | `expected_archive_name` luôn trả `local_path.replace("/", "__")` | E1, E2, R6 |
| M3 | chuyển vòng kiểm `archive_name` ra SAU lọc `--only` | R2 |
| M4 | chuyển kiểm `archive_name` ra SAU `api.dataset_download_files` (vẫn trước khi ghi) | R1 |
| M5 | `code_status` trả `(False, [])` khi returncode ≠ 0 và khi có ngoại lệ | C3 |
| M6 | pathspec thiếu `"backend"` | C1 |
| M7 | `verify` ghi `"code_dirty": False`, `"code_dirty_files": []` cố định (không gọi `code_status`) | C5 |

Ghi `mut.py` (đường dẫn) và output từng đột biến vào progress. `git status --porcelain` trước và sau khi chạy đột biến giống hệt.

**AC8 — Không hồi quy toàn bộ** (lệnh AC2 kế hoạch 06, đổi sang `.venv/bin/python`, + module mới):
`PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_archive_private_kaggle_r05 -v`
- Mốc: `b0_ac8.log` (cùng lệnh, bỏ module cuối). Orchestrator đã đo ở HEAD 04ec565: `Ran 414`, failures=1
  (`TestFrontendSourceGuard.test_no_violation`, đỏ có chủ đích — kế hoạch 06 sửa ở nhánh local), errors=1 (`setUpClass` của
  `test_translation_core`, thiếu checkpoint ViT5 bị gitignore), skipped=30 (thiếu dữ liệu gitignore). B0 đo lại, số của B0 là mốc.
- Sau B3: `Ran` = `Ran` B0 + số test module mới; tập id FAIL == `b0_fail.txt`; tập id ERROR (kể cả dòng `ERROR: setUpClass ...`)
  == `b0_error.txt`; tập id skipped == `b0_skip.txt` (so bằng `diff` trên file đã sort; trích từ output `-v` bằng
  `grep -E '\.\.\. (FAIL|ERROR)$|^(FAIL|ERROR): '` và `grep -E '\.\.\. skipped'`). Module mới: 0 skip, 0 FAIL, 0 ERROR.

**AC9 — Quy trình.**
- a. impact trước khi sửa `restore` (B1) và `verify` (B2): lệnh, risk, caller (và text search nếu UNKNOWN) có trong progress.
- b. detect-changes trước mỗi commit B0–B3; risk có trong message; HIGH/CRITICAL có giải thích.
- c. Id test FAIL/ERROR trước khi sửa (B1, B2) có trong progress và message commit.
- d. Không lệnh Kaggle thật: progress không có lệnh `kaggle ...` hay `archive_private_kaggle.py stage|upload|verify|restore` chạy thật;
  trong file test mới, mọi lời gọi `P.main(`, `P.restore(`, `P.verify(` đều truyền API giả; không có `kaggle_api(`.
- e. `git status --porcelain` sau B3 == `b0_status.txt`.
- f. 4 commit (B0–B3), mỗi commit chỉ chứa file của bước đó; `git add` theo đường dẫn.

## 6. Rủi ro dữ liệu/ML

- **Không có phần ML.** Không train, không đánh giá, không đọc TEST, không chọn model, không đổi tiền xử lý → rò rỉ, lệch
  train–realtime, cỡ mẫu/CI: không áp dụng. Không sinh số liệu mới; mọi con số trong progress (số test, id FAIL/skip) phải trích
  từ log của lệnh đã ghi.
- **Nguồn dữ liệu trong test:** chỉ byte fixture nhỏ tự tạo trong thư mục tạm ngoài repo (không phải dữ liệu thật) và HAI manifest
  thật đã commit, chỉ ĐỌC (đường dẫn, sha256, kích thước; không landmark/per-clip). Không thêm file dữ liệu/nhị phân nào vào git.
  Không tải, không upload.
- **R1 — Quyết định D1 lệch chữ yêu cầu.** Reviewer có thể coi là lệch phạm vi. Giảm thiểu: bằng chứng §2.3 (manifest bước 4 dùng
  `flat_name`; `docs/CLOUD.md` §3 và kế hoạch 08 dựa vào restore bước 4), test E2/R6 chạy trên manifest bước 4 thật và fixture bước 4,
  M2 chứng minh cách áp nguyên văn làm hỏng luồng đó. Với manifest của chính script này, quy tắc đúng nguyên văn review.
- **R2 — Script sinh manifest thứ ba trong tương lai** sẽ bị restore từ chối (exit 2) cho tới khi thêm quy tắc đặt tên. Chủ đích
  (không đoán tên); ghi trong docstring.
- **R3 — Phạm vi `code_dirty` hẹp:** chỉ 4 thư mục (không `configs/`, `docs/`, `frontend/`) và chỉ tại thời điểm `verify` (không lúc
  `stage`/`upload`). `false` không chứng minh staging được tạo từ mã sạch; tính đúng của nội dung lưu trữ vẫn dựa vào sha256 so với
  JSON đã commit. Ghi rõ trong docstring.
- **R4 — Manifest cũ không có `code_dirty`:** không bổ sung hồi tố (không sửa bằng chứng lịch sử). Với manifest 2026-09-28, bằng chứng
  mã sạch vẫn là review 05 mục 7 (`git diff --stat 46674ab HEAD -- scripts src backend` rỗng tại lúc review).
- **R5 — C4 dùng git thật:** chỉ kiểm nhất quán với một lời gọi git độc lập, không kiểm giá trị → không phụ thuộc repo sạch/bẩn.
  Git thiếu trên máy chạy test → C4 sẽ FAIL (không skip); trên cloud và local git có sẵn (các test cũ đã gọi git).
- **R6 — Câu README là khẳng định về lịch sử git:** có bằng chứng (`docs/data_registry.md:44`, `test_h_history_not_rewritten`,
  review 05 S1/S3); không nói "đã gỡ khỏi repo công khai" hay "đã xóa".
- **R7 — Guard chuỗi cấm** (`TestSourceGuard.test_12`): docstring/chú thích mới trong script không được chứa chuỗi cấm; AC6 bắt.
- **R8 — Cloud thiếu dữ liệu gitignore** → 30 skip + 1 error ở module khác (mốc); không liên quan phạm vi, không được coi là pass
  cho module của kế hoạch này (AC6 yêu cầu 0 skip cho 4 module lưu trữ).

## 7. Điểm dừng

**Không chạm điểm dừng bắt buộc** (`docs/prompts/autopilot.md` §5): không đổi model mặc định; không cần dữ liệu người dùng; không
đụng thay đổi chưa commit của người dùng (`git add` theo đường dẫn; các xóa file dữ liệu ghi trong STATE là của máy local); không
hành động không hoàn tác (không gọi Kaggle, không xóa file, không viết lại lịch sử, không push lên main); không phát hiện vấn đề dữ
liệu mới. → KHÔNG cần người dùng trước khi code.

**Điểm dừng có điều kiện** (coder dừng, ghi vào `09-progress.md`, báo orchestrator — "CẦN PLANNER"; không tự đổi tiêu chí):
1. B0: lệnh AC6 (3 module cũ) không OK hoặc có skip; hoặc tập FAIL/ERROR của `b0_ac8.log` khác mô tả mốc của orchestrator (§5 AC8).
2. GitNexus `impact`/`detect-changes` không chạy được (CLAUDE.md cấm sửa hàm khi chưa có impact).
3. Muốn đạt AC mà phải sửa test cũ, `scripts/archive_step4_kaggle.py`, hay manifest đã commit.
4. Một đột biến AC7 không bị bắt: không nới test; bổ sung test đúng AC; nếu AC có lỗ thì báo planner.
5. Phát hiện tài liệu/luồng nào khác dựa vào `restore` với manifest sinh bởi script ngoài hai script ở §3.2.
