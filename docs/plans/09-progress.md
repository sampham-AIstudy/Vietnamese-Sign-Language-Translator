Trạng thái: ĐANG LÀM

# Tiến độ kế hoạch 09 — Dọn dẹp review 05

- Kế hoạch: `docs/plans/09-don-dep-review05.md`
- Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`)
- P9 (HEAD lúc B0, commit chứa kế hoạch): `59d3509` (`git rev-parse --short HEAD` = `git log -1 --format=%h -- docs/plans/09-don-dep-review05.md` = `59d3509`)
- Log/file tạm: `/home/user/_plan09_tmp/` (ngoài repo)

**Bước đã xong:** B0, B1, B2
**Bước đang làm:** B3 (README + đột biến + AC8 + đóng việc)
**Bước còn lại:** B3

## B0 — Mốc (HEAD 59d3509)

- `git status --porcelain > /home/user/_plan09_tmp/b0_status.txt` → file rỗng (0 byte; cây sạch trước khi tạo file progress này).
- `sha256sum` hai manifest → `/home/user/_plan09_tmp/b0_sha.txt`:
  ```
  53a771ed14626f9595718b22cc48cfadbb4095eadbba0754c0d8814049ae9ad6  reports/private_archive_2026-09-28/kaggle_archive_manifest.json
  12c5ceb37ee8c70e16c53ca8679b34c8f3a931553cdb69e9c38fbe0f770df91f  reports/step4_2026-09-26/archive/kaggle_archive_manifest.json
  ```
- AC6 (3 module cũ): `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_archive_private_kaggle tests.test_archive_step4_kaggle tests.test_private_artifacts -v`
  → log `/home/user/_plan09_tmp/b0_ac6.log`; tổng kết: `Ran 59 tests in 0.517s` / `OK`; số dòng `... skipped` = 0.
- AC8 (29 module, bỏ module mới) → log `/home/user/_plan09_tmp/b0_ac8.log`; tổng kết:
  `Ran 414 tests in 31.618s` / `FAILED (failures=1, errors=1, skipped=30)`.
  - `b0_fail.txt`: `tests.test_frontend_contract.TestFrontendSourceGuard.test_no_violation` (đỏ có chủ đích).
  - `b0_error.txt`: `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu checkpoint ViT5, gitignore).
  - `b0_skip.txt`: 30 dòng (thiếu dữ liệu/checkpoint gitignore).
  - Khớp mốc orchestrator (HEAD 04ec565: Ran 414, failures=1, errors=1, skipped=30) → không chạm điểm dừng §7.1.
- GitNexus: index `.gitnexus/meta.json` `lastCommit` = `f3a7371`; `git diff --stat f3a7371 HEAD` chỉ gồm 5 file `docs/**` (không đổi mã)
  → index dùng được cho `scripts/archive_private_kaggle.py`.
- detect-changes trước commit B0: `npx --yes gitnexus@1.6.12 detect-changes --scope all --repo .` →
  `Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree.` (chỉ file progress .md; không symbol; risk: không có symbol bị ảnh hưởng).

## B1 — restore kiểm archive_name (§3.2)

- impact (AC9a): `npx --yes gitnexus@1.6.12 impact restore --direction upstream --repo .` → `status: ambiguous`, 2 ứng viên
  (`Function:scripts/archive_private_kaggle.py:restore` risk LOW; `Method:tests/test_archive_private_kaggle.py:TestRestore.restore#4`
  risk UNKNOWN, 0 caller — là helper của test, không phải hàm sửa). Chạy lại có UID:
  `npx --yes gitnexus@1.6.12 impact restore --uid "Function:scripts/archive_private_kaggle.py:restore" --direction upstream --include-tests --repo .`
  → `risk: LOW`, `impactedCount: 8`, direct 1 (`main` của `scripts/archive_private_kaggle.py`), processes_affected 1, modules
  Scripts/Tests; index sau HEAD 11 commit (chỉ docs). Output: `/home/user/_plan09_tmp/b1_impact_restore.txt`.
- Text search bổ sung (`grep -rn "restore(" scripts tests backend src`): định nghĩa `scripts/archive_private_kaggle.py:319`, gọi duy nhất
  từ `main` (`:427`); `tests/test_archive_private_kaggle.py` `TestRestore.restore` gọi `P.restore` qua `self.code`. Tài liệu dùng
  `restore`: `README.md:265` (manifest private 2026-09-28), `docs/CLOUD.md:35`, `docs/plans/08-segmenter-live.md:123,281` (dataset
  bước 4). Chỉ có 2 manifest trong repo (`git ls-files | grep kaggle_archive_manifest`) → không có script sinh thứ ba (§7.5 không chạm).
- Test trước sửa (AC9c), `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_archive_private_kaggle_r05 -v`
  → `Ran 8 tests` / `FAILED (failures=8, errors=3)` (log `/home/user/_plan09_tmp/b1_before.log`):
  - ERROR: `test_e1_rules`, `test_e2_committed_manifests`, `test_r6_step4_manifest_restores` (cả 3: `AttributeError: module
    'archive_private_kaggle' has no attribute 'STEP4_SCRIPT'`; R6 lỗi chỉ vì hằng chưa có — hành vi restore bước 4 không hồi quy).
  - FAIL: `test_r1_...` (case a, b, c: `0 != 2`), `test_r2_checked_before_only_filter` (`0 != 2`),
    `test_r3_...` (other_script, no_generated_by: `0 != 2`), `test_r4_cli_exit_2_message` (`0 != 2`),
    `test_r7_step4_manifest_with_replace_rule_name_exit_2` (`3 != 2`).
- Sửa: `STEP4_SCRIPT`, `expected_archive_name`, `restore` đọc `generated_by.script` + kiểm trong vòng `check_local_path` (trước `--only`,
  trước `os.makedirs(download_dir)`), docstring (luật + mã thoát 2), `import posixpath`.
- AC6 sau B1 (4 module): log `/home/user/_plan09_tmp/b1_ac6.log` → `Ran 67 tests in 0.648s` / `OK`; `... skipped` = 0; FAIL/ERROR = 0.
  (59 test cũ + 8 test mới.)
- detect-changes trước commit B1: `Changes: 2 files, 2 symbols` / `Risk level: medium` / changed `Variable DESCRIPTION` (chỉ do hunk
  thêm `STEP4_SCRIPT` nằm kề, giá trị DESCRIPTION không đổi) và `Function restore`; flow `Restore → Inside`. File thứ 2 là
  `docs/plans/10-guard-dod7.md` (thay đổi của planner song song, không add). Không HIGH/CRITICAL.

## B2 — verify ghi code_dirty (§3.3)

- impact (AC9a): `npx --yes gitnexus@1.6.12 impact verify --direction upstream --repo . --summary-only` → `status: ambiguous`, 4 ứng viên:
  `Function:scripts/archive_step4_kaggle.py:verify` (risk LOW, 3 impacted — KHÔNG sửa), `Function:scripts/archive_private_kaggle.py:verify`
  (risk LOW, 2 impacted), `Method:tests/test_archive_step4_kaggle.py:Base.verify#1` và `Method:tests/test_archive_private_kaggle.py:Base.verify#1`
  (risk UNKNOWN, 0 caller — helper của test). Chạy lại có UID (hàm được sửa):
  `npx --yes gitnexus@1.6.12 impact verify --uid "Function:scripts/archive_private_kaggle.py:verify" --direction upstream --include-tests --repo .`
  → `risk: LOW`, `impactedCount: 8`, direct 1 (`main` của `scripts/archive_private_kaggle.py`), processes_affected 1, modules 2.
  Output: `/home/user/_plan09_tmp/b2_impact_verify_ambig.txt`, `/home/user/_plan09_tmp/b2_impact_verify.txt`.
- Text search bổ sung (`grep -rn "verify(" scripts tests`): `scripts/archive_private_kaggle.py:256` (định nghĩa), gọi từ `main` (`:451`);
  `scripts/archive_step4_kaggle.py:354/460` là hàm KHÁC cùng tên (không đổi); test gọi qua `Base.verify` của
  `tests/test_archive_private_kaggle.py:116` (dùng `P.verify`) và `tests/test_archive_step4_kaggle.py:144` (dùng `A.verify`).
- Test trước sửa (AC9c), `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_archive_private_kaggle_r05 -v`
  → `Ran 14 tests` / `FAILED (failures=1, errors=10)` (log `/home/user/_plan09_tmp/b2_before.log`):
  - ERROR: `test_c1_clean_and_arguments`, `test_c2_dirty_lines_kept_verbatim`, `test_c3_unknown_is_none_never_false` (4 case),
    `test_c4_real_git_consistent` (`AttributeError: module 'archive_private_kaggle' has no attribute 'code_status'`);
    `test_c5_manifest_generated_by` (3 case, `mock.patch.object`: `does not have the attribute 'code_status'`).
  - FAIL: `test_r5_manifest_without_code_dirty_restores` (`'code_dirty' not found in {...generated_by...}` — R5 assert khóa có trước khi
    `pop`, để chắc test thật sự xóa khóa verify đã ghi; phần restore của R5 vốn chạy được trước sửa).
- Sửa: `import subprocess`, `CODE_DIRS`, `code_status(run=subprocess.run, root=ROOT)`, `verify` gọi `code_status()` (tên toàn cục, ngay trước
  dựng manifest) + 2 khóa `code_dirty`/`code_dirty_files` + in 1 dòng cảnh báo khi `code_dirty` khác `False`; docstring module.
- AC6 sau B2 (4 module): log `/home/user/_plan09_tmp/b2_ac6.log` → `Ran 73 tests in 0.748s` / `OK`; `... skipped` = 0; FAIL/ERROR = 0.
  (59 test cũ + 14 test module mới; 14 dòng `test_archive_private_kaggle_r05 ... ok`.)
- detect-changes trước commit B2:
  - Lần 1 (index cũ, `lastCommit f3a7371`): `Changes: 3 files, 4 symbols` / `Risk level: high` / changed `Variable LICENSE`,
    `Function nested_predictions_path`, `Function verify`, `Function restore` (`/home/user/_plan09_tmp/b2_detect.txt`). **Giải thích HIGH:**
    index lập trên file TRƯỚC B1, còn hunk của B2 tính trên số dòng SAU B1 → lệch dòng: `git diff` (B2) chỉ đổi docstring module, import,
    `CODE_DIRS`, hàm mới `code_status` và `verify`; `LICENSE`, `nested_predictions_path`, `restore` không đổi trong B2.
  - Làm mới index: `node .gitnexus/run.cjs analyze --index-only` (`.gitnexus/` nằm trong `.git/info/exclude`, không làm bẩn git) →
    `Repository indexed successfully`, `lastCommit 90159bb`. Lần 2: `npx --yes gitnexus@1.6.12 detect-changes --scope all --repo .`
    → `Changes: 3 files, 26 symbols` / `Risk level: medium` / symbol script: `Variable CODE_DIRS`, `Function code_status`, `Function verify`;
    flows `Verify → Expected_manifest_rel/Parse_sums/Sha256_file/Inside`; phần còn lại là symbol của file test mới và các Section của
    `docs/plans/10-guard-dod7.md` (planner song song, không add) (`/home/user/_plan09_tmp/b2_detect2.txt`). Không HIGH/CRITICAL.
