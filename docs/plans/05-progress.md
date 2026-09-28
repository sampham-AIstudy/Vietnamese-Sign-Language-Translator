# Kế hoạch 05 — tiến độ (coder; phiên 1: B0 + B1; phiên 2: B2–B4)

- Bước đã xong: B0 (không điểm dừng nào kích hoạt), B1 (22f891c), B2 (77f4da3), B3 (commit "05: B3 — ...")
- Bước đang làm: B4
- Bước còn lại: B4 (phiên 2); B5–B8 (phiên sau)

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

## B2 — (f2, f4) /api/classes 503 + test checkpoint không phục vụ được

- impact upstream `get_classes`: UNKNOWN (0 caller); text search backend/scripts/tests/frontend/src/src: không caller ngoài route.
- Test viết trước (`tests/test_backend_model_unavailable.py`, 5 test), chạy trước khi sửa: `Ran 5`, `FAILED (failures=3)`:
  test_features_unknown, test_mediapipe_version_mismatch (tại /api/classes: `AssertionError: 500 != 503`; health và
  model_info đã 503 trước đó trong cùng test), test_file_not_found_is_503 (`500 != 503`). 2 ca thành công (g) PASS ngay.
- Sửa: `get_classes` dùng `_active_model()`, bắt `ModelUnavailable` → `_model_unavailable_response`.
- Sau khi sửa: `tests.test_backend_model_unavailable tests.test_ws_live_contract -v` → `Ran 23`, `OK`, 0 skip
  (mới 5; ws_live_contract 18 = như B0). Log `../_plan05_tmp/b2_tests.log`.
- detect-changes --scope all (index vừa refresh): risk medium; symbol get_classes; 3 flow của chính get_classes
  (Get_classes → _is_int / _sha256_file / _short, qua _active_model).

## B3 — (f3) dropped_frames không đếm message lỗi/control

- impact upstream: `_process_frame_worker_harmonized` LOW (1 caller trực tiếp: run_harmonized, 1 process);
  `websocket_live_stream` UNKNOWN (0 caller; text search: chỉ là route WS, chỉ sửa docstring).
- Test viết trước (`tests/test_ws_dropped_frames.py`, 3 test), chạy trước khi sửa: `FAILED (failures=3)`:
  TestWsErrorsAreNotDroppedFrames.test_errors_during_recording `AssertionError: 5 != 0` (đúng giá trị P5 kế hoạch nêu);
  TestWorkerSeq.test_drops_inside_recording `73926 != 3`; TestWorkerSeq.test_drops_in_idle_before_sign `73926 != 0`
  (received_seq = 1000*i cố ý không liên quan).
- Sửa: `push_seq = item.get("dropped_frames", 0) + stats["frame_seq"] + 1` → `session.process(..., seq=push_seq)`;
  docstring `websocket_live_stream` thêm hợp đồng `sign_result.segment.dropped_frames`. Không đổi `src/`.
- Sau khi sửa: `tests.test_ws_dropped_frames tests.test_ws_live_contract tests.test_harmonized_live
  tests.test_live_harmonized_equivalence -v` → `Ran 39 tests in 560.066s`, `OK`, 0 skip (mới 3; ws_live_contract 18,
  harmonized_live 10, live_harmonized_equivalence 8 = như B0). Log `../_plan05_tmp/b3_tests.log`.
- detect-changes --scope all (index tại 77f4da3): risk HIGH; symbol _process_frame_worker_harmonized,
  websocket_live_stream; 11 flow (Run_harmonized → ..., Websocket_live_stream → ...). Thay đổi thực tế chỉ là giá trị
  `seq` truyền vào segmenter + docstring; AC4/AC5 tương đương của kế hoạch 04 vẫn pass.
