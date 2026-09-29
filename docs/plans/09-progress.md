Trạng thái: ĐANG LÀM

# Tiến độ kế hoạch 09 — Dọn dẹp review 05

- Kế hoạch: `docs/plans/09-don-dep-review05.md`
- Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`)
- P9 (HEAD lúc B0, commit chứa kế hoạch): `59d3509` (`git rev-parse --short HEAD` = `git log -1 --format=%h -- docs/plans/09-don-dep-review05.md` = `59d3509`)
- Log/file tạm: `/home/user/_plan09_tmp/` (ngoài repo)

**Bước đã xong:** B0
**Bước đang làm:** B1 (restore kiểm archive_name)
**Bước còn lại:** B1, B2, B3

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
