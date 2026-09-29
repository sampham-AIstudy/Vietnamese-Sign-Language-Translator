Trạng thái: ĐANG LÀM

# Tiến độ kế hoạch 10 — Guard DoD 7 phía backend

- Kế hoạch: `docs/plans/10-guard-dod7.md`
- Nhánh: `cloud/2026-09-29-viec-a-d` (cloud, `.venv/bin/python`)
- P10 (HEAD lúc bắt đầu B1, commit chứa kế hoạch): `f16d0a9` (`f16d0a9d9f717af6c50381732152a58d9ad3c953`)
- Log/file tạm: `/home/user/_plan10_tmp/` (ngoài repo; `../_plan10_tmp/` của kế hoạch)

**Bước đã xong:** B1(1) mốc B0
**Bước đang làm:** B1(2) viết `tests/test_backend_source_guard.py`
**Bước còn lại:** B1(2)–(6), B2, B3

## B1(1) — Mốc B0 (HEAD f16d0a9)

- `git status --porcelain > /home/user/_plan10_tmp/b0_status.txt` → 0 byte (cây sạch, chụp TRƯỚC khi tạo file progress này).
- Lệnh AC8 bỏ module cuối (29 module, `PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest tests.test_alphabet_preprocessing ... tests.test_frontend_contract -v`)
  → log `/home/user/_plan10_tmp/b0_ac8.txt`; tổng kết chép từ log:
  `Ran 414 tests in 31.092s` / `FAILED (failures=1, errors=1, skipped=30)`.
  - FAIL: `test_no_violation (tests.test_frontend_contract.TestFrontendSourceGuard.test_no_violation)` (đỏ có chủ đích, kế hoạch 06).
  - ERROR: `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu checkpoint ViT5, gitignore).
  - skipped: 30 dòng → `/home/user/_plan10_tmp/b0_skip.txt` (thiếu dữ liệu gitignore).
  - Khớp tham chiếu orchestrator tại 04ec565 (Ran 414, failures=1, errors=1, skipped=30).
