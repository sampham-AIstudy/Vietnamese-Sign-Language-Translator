# Kế hoạch 05 — tiến độ (coder, phạm vi phiên: B0 + B1)

- Bước đã xong: B0 (không điểm dừng nào kích hoạt), B1 (commit "05: B1 — ...", xem git log)
- Bước đang làm: (không; phiên dừng sau B1 theo lệnh orchestrator)
- Bước còn lại: B2–B8 (phiên sau)

## B0 (HEAD 2477257, 2026-09-28, không commit)

1. `git log --oneline -1` → `2477257 state: giao vslt-coder cho kế hoạch 05 (B0+B1, theo lệnh người dùng dùng nốt hạn mức)`.
   `git status --porcelain` lưu ngoài repo: `../_plan05_tmp/b0_status_porcelain.txt` (67 dòng).
2. AC2 baseline 20 module (log `../_plan05_tmp/b0_ac2.log`): `Ran 334 tests in 670.905s` / `OK`, 0 skip, 0 fail.
   Theo module: alphabet_ckpt_provenance 16, alphabet_preprocessing 6, archive_step4_kaggle 24, aspect_correction 3,
   fingerspelling_api 11, fingerspelling_compose 28, fingerspelling_deployed 9, fingerspelling_limits 48, harmonized 6,
   harmonized_live 10, live_harmonized_equivalence 8, realtime 3, report_step4 105, sign_segmenter 15, split_guards 6,
   translation_core 8, unified_split_integrity 4, vsl_system 6, ws_live_contract 18, ws_throughput 0 (file không có test).
   `git status --porcelain` sau khi chạy: giống file B0 (chỉ thêm `?? tests/test_status_privacy.py` do coder tạo cho B1).
3. `git ls-files -- '*.pt' '*.pth' '*.npz' '*.ckpt' '*.onnx' '*.safetensors'` → đúng 1 file:
   `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`. → Điểm dừng §7-1 KHÔNG kích hoạt.
4. (e), output nguyên văn:
   - `ls -l ../_backup_step4/REPORT_partial.md` → `-rw-r--r-- 1 Sam Pham 197121 2350 Sep 26 12:11 ../_backup_step4/REPORT_partial.md`
   - `sha256sum ../_backup_step4/REPORT_partial.md` → `d456d1cece190b11a089fd91fadea29071f61b4a3e8cfe36f59364023e6a434f`
   - `git ls-files -- '*REPORT_partial.md'` → (rỗng)
   - `git log --all --oneline -- '*REPORT_partial.md'` → (rỗng)
   - `git check-ignore -v reports/_probe/x.pt reports/_probe/x.npz` →
     `.gitignore:78:reports/**/*.pt	reports/_probe/x.pt` / `.gitignore:79:reports/**/*.npz	reports/_probe/x.npz`
   - `grep -n` → `78:reports/**/*.pt`, `79:reports/**/*.npz`
   → Điểm dừng §7-2 KHÔNG kích hoạt.
5. `.venv/Scripts/kaggle --version` → `Kaggle CLI 2.2.4`; `kaggle datasets list --mine` exit 0, liệt kê
   `phmvnsm33/vslt-step4-artifacts` (xác thực được). → §7-3 KHÔNG kích hoạt.

## B1 — status chỉ trả {source, n_signers}

- impact upstream `get_fingerspelling_status`: risk UNKNOWN (0 caller resolve); text search: chỉ gọi qua HTTP route (tests),
  `frontend/src` không đọc `trained_on`/`signers`. `public_trained_on` là hàm mới.
- Test viết trước, chạy trước khi sửa: `tests.test_status_privacy` FAIL/ERROR — TestPublicTrainedOn (3 test) ERROR
  `AttributeError: module 'backend.main' has no attribute 'public_trained_on'`; TestStatusFixture.test_status_only_source_and_count
  FAIL; TestStatusDeployed.test_deployed_checkpoint FAIL.
- Sau khi sửa: `python -m unittest tests.test_status_privacy tests.test_fingerspelling_limits tests.test_fingerspelling_api
  tests.test_fingerspelling_deployed -v` → `Ran 73 tests` `OK`, 0 skip (status_privacy 5 mới; limits 48, api 11, deployed 9 = như B0).
- detect-changes --scope all (sau `analyze --index-only`, index trước đó chậm 6 commit và báo sai "high" do lệch dòng):
  risk low, 3 symbol (public_trained_on, out, get_fingerspelling_status), 0 process.
