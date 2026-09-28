# Kế hoạch 05 — tiến độ (coder; phiên 1: B0 + B1; phiên 2: B2–B4; phiên 3: B5; phiên 4: B6–B8)

- Bước đã xong: B0 (không điểm dừng nào kích hoạt), B1 (22f891c), B2 (77f4da3), B3 (0e1d737), B4 (9e2c64a), B5 (46674ab), B6 (8a73e9d)
- Bước đang làm: B7 (phiên 5, từ HEAD 76d1208)
- Bước còn lại: B7, B8 (AC10-d/e đã chạy xong, PASS; AC10-c để reviewer)

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

## B4 — (f1) AC5 không PASS rỗng

- Thêm lớp `TestWebSocketEventsNotEmpty` ở cuối `tests/test_live_harmonized_equivalence.py` (trước khối `__main__`),
  `skipUnless(AVAILABLE, REASON)`, không kế thừa `TestWebSocketEndToEnd`, gọi lại `TestWebSocketEndToEnd._stream`;
  cùng env/reload/tearDownClass như lớp cũ; assert `len(ws_events) >= 1` cho từng clip trong 2 clip đầu, in `(type, reason, gloss)`.
  `git diff` file này: 56 dòng `+`, 0 dòng `-`. Không có symbol production nào bị sửa, nên không chạy impact.
- Không có FAIL trước khi sửa: hành vi vốn đúng, lớp mới chỉ chặn trường hợp PASS rỗng. Chưa tự chạy đột biến "WS trả 0 event"
  (AC14-iv, để reviewer làm).
- Thời gian module `tests.test_live_harmonized_equivalence`: trước `Ran 8 tests in 506.958s` (real 8m28s), OK;
  sau `Ran 9 tests in 471.899s` (real 7m54s), OK, 0 skip. Log `../_plan05_tmp/b4_before.log`, `../_plan05_tmp/b4_after.log`.
- Output AC8 (nguyên văn):
  `[AC8] qipedc_W03251B: 257 frames + 21 padding frames -> WS events [('sign_result', None, 'thìa'), ('sign_result', None, 'thìa')]`
  `[AC8] qipedc_D0120T: 113 frames + 21 padding frames -> WS events [('sign_result', None, 'phải không?')]`
  (clip TRAIN, chỉ để chứng minh có event; không phải số liệu đánh giá).
- `git status --porcelain` trước/sau lần chạy: chỉ khác ` M docs/plans/05-progress.md` (coder sửa file này trong lúc test chạy);
  test không đổi file nào.
- detect-changes --scope all (sau analyze --index-only): risk CRITICAL, 52 flow. Nguyên nhân: graph gộp các symbol cùng tên
  (`setUpClass`, biến `api`) giữa nhiều file test. Symbol thực sự đổi đều nằm trong file test: TestWebSocketEventsNotEmpty,
  setUpClass của nó, `api`; 0 dòng mã production.

## B5 — (c) scripts/archive_private_kaggle.py + test với API giả (AC9)

- Không sửa hàm có sẵn nào (script và test đều mới; `scripts/archive_step4_kaggle.py` chỉ được import, `git diff b337aee`
  của file này rỗng). Không chạy lệnh Kaggle nào (kể cả lệnh đọc) trong bước này.
- Test viết trước (`tests/test_archive_private_kaggle.py`, 27 test, AC9 ca 1–13), chạy trước khi có script: `Ran 1`,
  `FAILED (errors=1)`: `ModuleNotFoundError: No module named 'archive_private_kaggle'`.
- Lần chạy đầu sau khi viết script: 26/27 pass; `test_11b_existing_same_sha_untouched` FAIL `8 != 7`, vì dòng tổng kết của
  restore cũng chứa chữ "đã có". Sửa câu tổng kết của script ("bỏ qua vì có sẵn cùng sha256"), không sửa test.
- Sau khi sửa: `tests.test_archive_private_kaggle tests.test_archive_step4_kaggle -v` → `Ran 51 tests`, `OK`, 0 skip
  (mới 27; archive_step4_kaggle 24 = như B0). Log `../_plan05_tmp/b5_tests.log`.
- Kiểm trước B6, chỉ đọc (không băm, không staging, không Kaggle): `plan_files(JSON thật)` → 13 file, 0 file thiếu trên đĩa,
  tổng 8361555 byte (≤ 2 GiB), quét bí mật trên các file text thật → 0 khớp. Quét chỉ theo mẫu, không chứng minh được là
  không có bí mật. sha256 so với JSON sẽ được kiểm ở `stage` của B6.
- Thêm ngoài §3.3 (giả định của coder): `verify` từ chối `--manifest-out` nằm trong repo nếu khác
  `reports/private_archive_<ngày hôm nay giờ VN>/kaggle_archive_manifest.json` (exit 2, trước mọi lời gọi API); ngoài repo thì
  không ràng buộc (để test ghi vào thư mục tạm). `main(..., src_root=ROOT)` là tham số chỉ dùng cho test (không có cờ CLI).
- detect-changes --scope all (sau analyze --index-only): risk low, 0 process (chỉ thấy 05-progress.md; script và test mới
  chưa được track nên không có trong graph).

## B6 — chạy thật (lịch sử lệnh Kaggle, theo thứ tự)

HEAD lúc chạy: f7ad8d2; `git status --porcelain -- scripts src tests backend` rỗng. Output: `../_kaggle_staging/prov_*.out`.
- `stage` (không gọi Kaggle) → exit 0: "staged 13 files + SHA256SUMS + dataset-metadata.json ... (8361555 bytes of data)"; sha256 13 file khớp JSON (các file có sha256 ghi sẵn).
- `upload` (1 lần `dataset_create_new`, public=False trong archive_step4_kaggle.upload) → exit 0: "created phmvnsm33/vslt-provenance-artifacts (private); status='Ok'".
- `verify` lần 1 → exit 6: "dataset_download_files lỗi: 404 Client Error: Not Found for url: https://api.kaggle.com/v1/datasets.DatasetApiService/DownloadDataset" (ready, private 2 nguồn và danh sách file đã qua; lỗi ở bước tải về, chưa ghi manifest). Theo kế hoạch: chạy lại verify, không chạy lại upload.
- `verify` lần 2 (sau ~4 phút) → exit 0: "verified phmvnsm33/vslt-provenance-artifacts: private (2 sources), ready, 13 files +
  SHA256SUMS; manifest reports/private_archive_2026-09-28/kaggle_archive_manifest.json".
- Tổng: đúng 1 `dataset_create_new` (trong upload). Không lệnh nào chứa version / metadata --update / delete / kernels push.

Manifest `reports/private_archive_2026-09-28/kaggle_archive_manifest.json` (chép từ file): ref `phmvnsm33/vslt-provenance-artifacts`,
is_private true, is_private_sources {dataset_list_mine: true, dataset_metadata: true}, status ready, total_bytes 8363141,
verified {file_list_matches: true, downloaded_sha256_all_match: true, n_files: 13}, git_commit f7ad8d2,
verified_at_utc 2026-09-28T10:42:46Z (17:42 giờ VN, trùng ngày trong đường dẫn).
- licence_status "unknown" (nhóm A, hauuto, 5 file): checkpoints/alphabet_best.pt, 2 × alphabet_nested_final.pt,
  nested_predictions.csv, alphabet_real_best.pt.
- licence_status "redistribution_not_stated" (nhóm S, 8 file): 2 checkpoint Cấp 2, 4 log kernel, history.json, segments.csv.
  `data/processed/vslgh_segments/segments.csv` chỉ từ VSL-GH (MIT theo docs/data_registry.md §2, chưa kiểm lại).
- sha256 của `checkpoints/stgcn_unified_best.pt` (930633233ff3…) trùng file `unified_run_2026-09-25__run__stgcn_unified_best.pt`
  trong `phmvnsm33/vslt-step4-artifacts` (so bằng hai manifest).
- Quét bí mật theo mẫu: 0 khớp. Đây là quét theo mẫu, không chứng minh được là không có bí mật.

### AC10 sau commit B6 (8a73e9d)
- AC10-e(1) `restore --manifest reports/private_archive_2026-09-28/kaggle_archive_manifest.json --download-dir
  ../_kaggle_staging/restore_dl --root ../_kaggle_staging/restore_root` → exit 0, "13 file ghi mới"; sha256 cả 13 file dưới
  root tạm = manifest (True).
- AC10-e(2) `restore` với root mặc định (`--download-dir ../_kaggle_staging/restore_dl2`) → exit 0, 13 dòng "đã có: …",
  "0 file ghi mới"; sha256 + mtime của 13 file trong repo trước/sau giống hệt; `git status --porcelain` trước/sau giống hệt.
- AC10-d `scripts/alphabet_ckpt_provenance.py --out ../_plan05_tmp/ac10d/provenance.json` → exit 0,
  verdict=real_data_known_checkpoint, V1–V6 True; so với JSON đã commit sau khi bỏ generated_by: `True`.
- AC10-c (kaggle datasets list --mine + truy cập ẩn danh) để reviewer tự chạy.

### Tạm dừng sau B6
- Chưa bắt đầu B7 trong repo: chưa `git rm --cached`, chưa sửa .gitignore/README/data_registry. Bản nháp test AC11
  (`tests/test_private_artifacts.py`, chưa chạy) được chuyển ra ngoài repo: `../_plan05_tmp/test_private_artifacts.py.draft`
  (phiên sau có thể chép lại vào tests/ khi làm B7).

## B7 — (a) gỡ alphabet_real_best.pt khỏi index

- Bản nháp AC11 chép lại vào `tests/test_private_artifacts.py`, không sửa. Chạy TRƯỚC khi sửa: a, b, d, g, h FAIL (a/d: X còn
  track — `git ls-files` chỉ ra đúng X, không file nào khác của manifest bị track, nên AC11-d không có phát hiện mới;
  b: check-ignore 1; g: .gitignore chưa có dòng chú thích; h: chưa có commit xóa X khỏi index); c, e, f pass.
- `git rm --cached -- reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`; file vẫn trên đĩa:
  `sha256sum` → `afc00521d56bccb2eddf9570eff8905c89aa33c67df0d4781fafec4936a15fa9` (= manifest = provenance.json known.real_run), 541077 byte.
- `.gitignore`: thêm đúng 1 dòng chú thích sau `reports/**/*.npz`. README: thêm mục "Artifact không nằm trong git" (13 dòng,
  2 ref, 2 manifest, lệnh restore). `docs/data_registry.md:44`: thay vế "already committed and pushed…owner's call" bằng
  429b289 / origin/fix/audit-round2 / gỡ ở B7 / ref private mới.
- Trước commit: AC11 a–f pass, g/h FAIL (cần commit). `tests.test_fingerspelling_api` → Ran 11, OK, 0 skip;
  TestRealClipEquivalence CHẠY (nạp alphabet_real_best.pt từ đĩa) và ok.
- detect-changes --scope all (sau analyze --index-only): risk low, 0 process (chỉ các mục tài liệu).
