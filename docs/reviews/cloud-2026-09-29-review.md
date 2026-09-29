# Review độc lập nhánh cloud `origin/cloud/2026-09-29-viec-a-d` (ab40a82) trước merge vào feat/vslt-complete (be0aac0)

TRẠNG THÁI: XONG — **KẾT LUẬN: APPROVE (cho việc MERGE), kèm điều kiện ở mục 7**

- merge-base: f3a7371. Reviewer: vslt-reviewer (độc lập, local Windows), 2026-09-29.
- Không tin báo cáo cloud / review 09, 10 của cloud: mọi kết luận dưới đây từ lệnh tự chạy.
- Thư mục tạm (ngoài repo): `../_cloud_review_tmp/` (log, script đột biến), worktree `../_cloud_merge_check` (đã gỡ).
- Python: `.venv/Scripts/python.exe` của repo chính; Node v25.9.0.

## 0. Phạm vi thay đổi (điểm 4)
- `git diff --stat f3a7371 origin/cloud/2026-09-29-viec-a-d` → đúng 14 file, 5109+/4−:
  README.md (1 dòng), docs/cloud_reports/viec-A-D-2026-09-29.md, docs/plans/{07,08,09,09-progress,10,10-progress}.md,
  docs/reviews/{09,10}-review.md, reports/guard_dod7_2026-09-29/guard_findings.json, scripts/archive_private_kaggle.py,
  tests/test_archive_private_kaggle_r05.py (MỚI), tests/test_backend_source_guard.py (MỚI).
- KHÔNG đụng docs/STATE.md, docs/progress_log.md, backend/, src/, frontend/, realtime_demo.py, docs/phase12_api.md,
  docs/plans/06-*, scripts/smoke_test_phase12.py. Không file dữ liệu/nhị phân.
- Phía local từ f3a7371 tới be0aac0 (`git diff --stat f3a7371 be0aac0`): 9 file (CLOUD.md, STATE.md, phase12_api.md,
  06-progress.md, usage_ledger.csv, Fingerspelling.jsx, cloud_setup.sh, smoke_test_phase12.py, test_frontend_contract.py)
  → giao với 14 file của cloud = rỗng. Merge thử `git merge --no-ff --no-commit` trong worktree tạm: "Automatic merge went well".
- Kế hoạch 06 so với merge-base: mọi thay đổi backend/src của 06 (4924502 B1 CORS/Origin, ed5c4c9 B2
  `src/inference/hand_live.py` + `/ws/hand-landmarks`) nằm TRƯỚC f3a7371; sau merge-base, 06 chỉ đổi frontend, script smoke,
  docs, test_frontend_contract (`git log --oneline f3a7371..be0aac0 -- backend src tests` → chỉ dbd79f2, chỉ sửa
  tests/test_frontend_contract.py). `git diff --stat f3a7371 be0aac0 -- backend src realtime_demo.py start_fullstack.ps1 run_core.py`
  → rỗng. Tức là guard 10 được lập sổ trên CHÍNH mã backend/src mà feat/vslt-complete đang có.

## 1. Kế hoạch 09 (restore kiểm archive_name, code_dirty, README)
- AC1: `git diff --name-status 59d3509 f4d868a` = M README.md, A docs/plans/09-progress.md, M scripts/archive_private_kaggle.py,
  A tests/test_archive_private_kaggle_r05.py; numstat README `1 1`. Khớp đúng tập của kế hoạch.
- Mã khớp §3.2/§3.3: `expected_archive_name` (SCRIPT → thay '/' bằng '__'; STEP4_SCRIPT → `A.flat_name(dirname, basename)`;
  khác hoặc không phải str → ArchiveError 2); kiểm MỌI phần tử trước lọc `--only` và trước makedirs/download
  (vòng `for e in entries:` sau `require_outside_repo`); thiếu `generated_by` → nhánh KeyError sẵn có → 2. `code_status`
  đúng hợp đồng (đối số dạng list, không shell, timeout 60, trả (None, None) khi không biết). README: dòng mới trùng nguyên văn §3.4.
- Test (14) kiểm thật: R1 a/b/c dựng sẵn file độc để nếu bỏ kiểm thì restore thành công và ghi file; E2 đọc 2 manifest thật
  đã commit; R6 chứng minh restore manifest bước 4 vẫn chạy (quyết định D1).
- Đột biến của reviewer (trong bộ nhớ, `../_cloud_review_tmp/mut09.py`, không ghi file repo): không đột biến → 14/14 OK;
  Y2 (luật step4 cho manifest private) BẮT; Y3 (generator lạ lùi về luật replace) BẮT; Y4 (dung thứ thiếu generated_by) BẮT;
  Y5 (strip dòng porcelain) BẮT; Y6 (bỏ dòng untracked) BẮT; Y7 (ghi bool(dirty): None thành False) BẮT;
  Y8 (chỉ kiểm phần tử đầu) BẮT; **Y1 (so archive_name không phân biệt hoa thường) SỐNG SÓT** — mức thấp (sha256 vẫn chặn
  nội dung sai); nên thêm 1 subTest đổi hoa/thường.
- Quyết định D1 (lệch câu chữ review 05, không lệch mục tiêu): hợp lý — áp nguyên văn sẽ làm restore manifest bước 4
  (docs/CLOUD.md §3) trả 2. Đã có trong "Câu hỏi chờ người dùng" (2) của STATE.md. Không chặn merge.

## 2. Kế hoạch 10 (guard DoD 7 backend)
- AC1: `git diff --name-status f16d0a9 cf23cef` = A docs/plans/10-progress.md, A reports/guard_dod7_2026-09-29/guard_findings.json,
  A tests/test_backend_source_guard.py. File guard có đúng 1 commit (319ddcd) trên nhánh → sổ KNOWN/ALLOWED chưa từng bị sửa
  sau khi lập.
- Sổ: ALLOWED 16 khóa, nằm trong PLAN10_APPROVED_ALLOWED (16 khóa = bảng §3.6); tổng count ALLOWED = 36, KNOWN = 9 (8 nhóm) —
  tự cộng từ tests/test_backend_source_guard.py:174-235, khớp dòng in `[DoD7-guard] known=9 allowed=36`.
- JSON: tái sinh trên CÂY ĐÃ MERGE (`python -m tests.test_backend_source_guard --report ../_cloud_review_tmp/guard_merge.json`)
  → phần thân (bỏ generated_by) **giống hệt** file đã commit; summary by_status {known 9, allowed 36, unregistered 0},
  n_serving_files 44, n_main_files 56. JSON đã commit có command + git_commit 319ddcdb... + code_dirty false. Trên cây merge,
  `git diff --stat 319ddcd -- tests/test_backend_source_guard.py backend src realtime_demo.py` → rỗng, nên AC5-d vẫn đúng sau merge.
- 9 vi phạm có sẵn (status known): realtime_demo.py:52 C-result, :266 và :267 C-string, :294 C-string, :330 D-binding,
  :395 C-string; src/data/landmark_extractor.py:121 D-binding; src/data/vsl_gh_dataset.py:31 D-string;
  src/inference/sign_segmenter.py:141 D-binding. backend/main.py: 0. → DoD 7 phần backend: guard CÓ, **CHƯA ĐẠT**
  (báo cáo cloud ghi đúng như vậy).
- Đột biến của reviewer (`../_cloud_review_tmp/mut10.py`, trong bộ nhớ): chèn A-stdlib / C-result / D-binding / A-numpy vào
  src/inference/hand_live.py (file của 06), backend/main.py, src/inference/sign_segmenter.py → 12/12 BẮT (unregistered);
  thêm 1 D-binding trong `SignSegmenter._activity` (nhóm KNOWN) → `changed` 1 → 2, BẮT; resolver bỏ import lười → thiếu 4 file
  MIN_SERVING (test_b_real_tree_serving sẽ đỏ); comparator bỏ so số lượng → test_b_duplicate_is_changed đỏ.
- Guard trên CÂY LÀM VIỆC của repo chính (có file untracked/ignored): gọi `scan_repo(<repo chính>)` + `compare_registry` (chỉ đọc)
  → unregistered 0, changed 0, stale 0; serving 44, main 56, scripts_realtime rỗng → không file untracked nào trong
  backend/src làm guard đỏ ở máy local.

## 3. Test trên cây đã merge vs mốc be0aac0 (điểm 2)
| Lần chạy | Lệnh | Kết quả |
|---|---|---|
| Mốc HEAD be0aac0 (repo chính, đủ dữ liệu) | lệnh AC2 kế hoạch 06 (29 module), log `../_cloud_review_tmp/base_ac2.log` | `Ran 429 tests in 283.485s` `OK`, 0 skip, 0 fail, 0 error (khớp mốc B7 của 06: 429 OK) |
| Cây merge (worktree tạm, KHÔNG có dữ liệu gitignored) | 29 module + tests.test_archive_private_kaggle_r05 + tests.test_backend_source_guard, log `merge_ac2.log` | `Ran 458 tests in 34.317s` `FAILED (errors=1, skipped=31)` |
| Cây merge, 2 module mới | `-m unittest tests.test_archive_private_kaggle_r05 tests.test_backend_source_guard -v` | `Ran 38 tests in 1.989s` `OK`, 0 skip |
| Cây merge, frontend | `cd frontend && npm test` | `tests 26, pass 26, fail 0` (merge không đụng frontend; chạy cho đủ) |

- errors=1 = `setUpClass (tests.test_translation_core.TestVSLTranslationCore)` (thiếu checkpoints/vit5_* trong worktree);
  31 skip đều do thiếu dữ liệu/checkpoint gitignored trong worktree (alphabet_best.pt, H-keepz-360, stgcn_best.pt, video
  QIPEDC/hauuto, recording_groups.csv) + 1 skip `not a git checkout` (TestAC7aUnchangedFiles: worktree có `.git` là file).
- Đối chiếu từng module (đếm dòng kết quả theo module, mốc vs merge): khác nhau CHỈ ở (a) 2 module mới (+14, +24, đều ok),
  (b) test_translation_core 8 test → 1 dòng lỗi setUpClass, (c) các test cần dữ liệu chuyển ok → skipped. Không test nào FAIL.
- Vì sao kết quả mốc chuyển được sang cây merge: file không phải tài liệu mà merge đổi chỉ có scripts/archive_private_kaggle.py
  và README.md; test đọc chúng = test_archive_private_kaggle, test_private_artifacts, test_archive_private_kaggle_r05,
  test_backend_source_guard (grep "archive_private_kaggle" hoặc "README" trong tests/*.py) — cả 4 chạy đủ trên cây merge,
  0 skip, 0 fail. Các module bị skip trong worktree kiểm mã giống hệt be0aac0 (merge không đổi file nào của chúng) và đã OK ở mốc.
- Dự báo sau khi merge thật trên feat/vslt-complete (đủ dữ liệu): 429 + 38 = 467 test, 0 skip — orchestrator phải chạy lại
  để xác nhận (điều kiện merge 2).
- `git status --porcelain` của repo chính trước/sau khi chạy mốc: giống hệt.

## 4. Kế hoạch 07, 08 — nhất quán với kế hoạch 06 và STATE.md (điểm 3)
Chỉ là kế hoạch; cả hai tự ràng buộc "chỉ bắt đầu sau khi 06 APPROVE". Không chặn merge. Cần planner sửa TRƯỚC KHI CODE:
- P1 (07 và 08): lệnh không hồi quy (07 AC2, 08 AC-T) chưa có `tests.test_archive_private_kaggle_r05` và
  `tests.test_backend_source_guard` (có sau merge này) → thêm vào.
- P2 (07 và 08, gắn với K1): 07 AC2 và 08 AC-T đòi `git diff P -- tests/` có 0 dòng `-` cho mọi test có sẵn, trong khi kế hoạch
  10 cho phép (và buộc, khi mã được sửa) CO sổ KNOWN_VIOLATIONS trong tests/test_backend_source_guard.py. 08 sửa đúng
  `SignSegmenter._activity` (nhóm KNOWN D-binding, count 1). Thiết kế 08 giữ nhánh `n = 1: fps_last = 30.0` nên có thể giữ
  nguyên 1 finding, nhưng nếu coder viết khác thì count đổi → CHANGED/STALE → phải sửa sổ, mà AC-T lại cấm. Planner phải ghi rõ:
  được xóa mục/giảm count trong KNOWN (ngoại lệ có tên, đúng file đó), cấm tăng.
- P3 (07): mã mới C4/C7/C8 (backend/main.py, src/translation/sentence_pipeline.py, src/inference/sentence_live.py) sẽ vào phạm vi
  guard (SERVING/MAIN). Ví dụ: cảnh báo `fps_out_of_range` gợi ý hằng kiểu `FPS_MIN = 15.0` → luật D-binding báo; chuỗi/khóa kết
  quả cố định → C-result. 07 cần tiêu chí "guard 10 xanh, không thêm khóa KNOWN/ALLOWED" và quy trình khi cần ngoại lệ (ALLOWED
  chỉ đổi qua "Lần sửa" của planner với hằng PLAN10_APPROVED_ALLOWED).
- P4 (07 §2.4, §3.9): hiện trạng đã cũ — 06 B6 đã commit (0328c1b) và viết cơ chế chụp NGAY TRONG
  frontend/src/components/Fingerspelling.jsx (khoảng :105-120, FS_MAX_IN_FLIGHT) → nhánh "tách ra lib/capture.js" của C10 sẽ
  xảy ra (AC1 của 07 đã cho phép). 06 B8 (scripts/e2e_*) vẫn chưa có tại be0aac0 — C11 phụ thuộc.
- P5 (07 C10 và 08 B6): 08 B6 sửa timestamp lúc chụp chỉ ở CameraCapture.jsx:127; Fingerspelling.jsx:120 cũng gửi
  `timestamp: nowMs()` SAU `toDataURL` (cùng lỗi). Nếu 07 tách capture.js từ Fingerspelling, cần một quy ước chung
  (timestamp = lúc chụp) cho cả hai đường và thứ tự 07/08 để khỏi sửa chồng.
- Nhất quán với "Quyết định của người dùng": 08 chỉ đổi tham số live (`rest_hold_s`, thêm `speed_min_dt_s`) không thuộc
  CHECKPOINT_KEYS (src/inference/sign_segmenter.py:12-15, :34-44) → không trái "tham số cắt nghỉ lấy từ checkpoint"; không đổi
  model mặc định. 07 D7 giữ Phase12Pipeline + model mặc định; chọn ngưỡng trên VAL S05, đo S06 đúng 1 lần, kiểm chồng lấn trước
  (đúng mục 5–6). Tham chiếu dòng backend/main.py trong 07/08 vẫn đúng (backend không đổi từ merge-base).
- Phát hiện của 07 (CSLR train S01–S04 cho cả 300 câu): tự kiểm docs/vsl_gh_dataset.md:120-123 (train 4 người × 3 lần × 300 câu)
  và reports/PHASE4B_REPORT.md:112 ("Zero Leakage cả về Signer lẫn Sentence") → mâu thuẫn có thật cho phần CSLR của "Mode B";
  lỗi tài liệu CÓ SẴN (không do nhánh này), đã có trong "Câu hỏi chờ người dùng" (1).

## 5. Góp ý K1 review 10 (điểm 5)
- Xác nhận: không test nào so sổ KNOWN_VIOLATIONS với một mốc cố định; tăng count trong sổ cùng lúc thêm vi phạm → test vẫn xanh.
  Hiện chỉ có quy ước + reviewer kiểm `git log -p` (kế hoạch 10 §3.5 ý 2).
- Mức độ: **TRUNG BÌNH-THẤP, không chặn merge** (tại ab40a82 sổ chưa từng bị sửa; merge không đổi mã được quét). Thành rủi ro thật
  ngay ở kế hoạch kế tiếp chạm mã đã đăng ký (08 `_activity`, 11 sửa realtime_demo.py).
- Đề xuất cho planner (trước khi code 08/11): thêm test so KNOWN_VIOLATIONS với JSON đã commit
  reports/guard_dod7_2026-09-29/guard_findings.json (gom finding `status: known` theo (path, rule, qualname)): mọi khóa KNOWN
  phải có trong JSON và count không lớn hơn count trong JSON. Muốn nới thì phải sửa cả bằng chứng đã commit → lộ rõ khi review.
  Kèm P2 ở mục 4.
- K2 (review 10, `_registered_key` đỏ khi cả 2 sổ rỗng): thấp, đồng ý. K3 (các dạng guard bỏ sót): đồng ý — "known=0" chỉ là
  điều kiện cần của DoD 7.

## 6. Bảng 1–13
| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | §1, §2: AC1 của 09/10 khớp tập file; 7/8 đột biến 09 bị bắt (Y1 sống sót, thấp); 12/12 + 3 đột biến guard bị bắt |
| 2 | Tự chạy lại test | PASS | Mốc be0aac0 `Ran 429` OK 0 skip; cây merge `Ran 458` errors=1 skipped=31 (chỉ do thiếu dữ liệu gitignored trong worktree, §3); 2 module mới `Ran 38` OK; npm 26/26. Lời cloud "Ran 38 ... OK" khớp |
| 3 | Không sửa/skip/nới test | PASS | `git diff f3a7371 origin/cloud/... -- tests/`, lọc dòng bắt đầu bằng `-` (trừ `---`) → 0 dòng; chỉ 2 file test mới; file guard 1 commit |
| 4 | Nguồn gốc dữ liệu | N/A | Không train/đánh giá; JSON guard là finding mã nguồn (note "not model metrics") |
| 5 | Rò rỉ | N/A | Không split mới (07 lên kế hoạch kiểm chồng lấn ViT5–S06 trước khi đo) |
| 6 | VAL chọn, TEST một lần | N/A (mã) / PASS (kế hoạch) | 07: ngưỡng trên VAL S05, S06 một lần; 08: chọn trên TRAIN, VAL xác nhận, không chạm TEST (W03251N/T) |
| 7 | Số liệu truy được | PASS | guard_findings.json: command + git_commit 319ddcd + code_dirty false; thân tái sinh giống hệt trên cây merge. Số test của cloud (414/428/452) là log môi trường cloud (thiếu dữ liệu), ghi rõ là cloud |
| 8 | Cỡ mẫu / CI | N/A | Không có số liệu mô hình. 08 ghi trung thực n = 1 (W03251B) |
| 9 | Nhất quán train–realtime | N/A (mã) / PASS (kế hoạch 08) | 08 giữ `hand_activity`/`_normalise` của train, test tương đương khi fps đều |
| 10 | Không random/mock/kết quả giả | PASS (không thêm) | Guard xanh trên cây merge và cây local; 9 vi phạm CÓ SẴN được ghi sổ; DoD 7 backend CHƯA ĐẠT (ghi trung thực) |
| 11 | Bảo mật | PASS | restore chặn archive_name lệch trước mọi tải/ghi; subprocess dạng list, không shell; không token/kaggle.json trong diff (chỉ nhắc KAGGLE_KEY là chuỗi mẫu, không có giá trị); JSON không chứa đường dẫn tuyệt đối (test assert) |
| 12 | So sánh công bằng / GATE | N/A | Không đổi model mặc định, không đổi tiêu chí GATE |
| 13 | Kết luận vượt bằng chứng | PASS (có ghi chú) | Báo cáo cloud nói đúng "DoD 7 backend CHƯA ĐẠT", "D1 cần xác nhận". Ghi chú: docstring 09 nói git thiếu → null nhưng `git_head()` (scripts/archive_step4_kaggle.py:197-199) không bắt FileNotFoundError → verify dừng trước (review 09 K2, thấp) |

## 7. Kết luận
**APPROVE cho việc merge** `origin/cloud/2026-09-29-viec-a-d` vào feat/vslt-complete. Không còn FAIL.

Điều kiện kèm theo khi merge:
1. Merge bằng `git merge --no-ff` (không rebase/amend); không add 3 file ` D` và file untracked của người dùng.
2. Ngay sau merge, chạy trên feat/vslt-complete (đủ dữ liệu): lệnh AC2 của 06 + `tests.test_archive_private_kaggle_r05
   tests.test_backend_source_guard` → kỳ vọng `Ran 467`, OK, 0 skip; ghi số thật vào STATE/progress_log (cloud không ghi 2 file này).
3. Từ nay mọi lệnh không hồi quy (06 B8/B9 + review 06, 07, 08, 11) thêm 2 module mới.
4. Trước khi code 08 và 11: planner xử lý K1 + P2 (mục 4–5). Trước khi code 07: P1, P3, P4, P5.

Việc nên sửa sau (không chặn, xếp theo mức độ):
- Trung bình-thấp: K1 (sổ KNOWN "chỉ co lại" chưa được máy kiểm) — đề xuất ở §5.
- Thấp: thêm subTest archive_name đổi hoa/thường (đột biến Y1 sống sót); review 09 K1–K3; review 10 K2–K4.
- Thông tin: cloud cài transformers 5.17.0, còn scripts/cloud_setup.sh (f62dd45, local) ghim transformers==4.57.6 → hai môi
  trường khác phiên bản. Mục 6 "việc chưa làm" của báo cáo cloud (thêm seaborn/transformers vào setup) đã xong ở f62dd45.

## 8. CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
(Đều đã có trong "Câu hỏi chờ người dùng" của STATE.md hoặc kế hoạch 10 §7.6; không chặn merge.)
1. D1 (kế hoạch 09): giữ luật tên theo script sinh manifest (reviewer khuyên GIỮ: áp nguyên văn sẽ làm hỏng restore manifest
   bước 4 ở docs/CLOUD.md §3) hay áp nguyên văn luật thay '/' bằng '__' cho mọi manifest.
2. CSLR đã học mọi câu S06 qua người ký khác → README:56 / PHASE4B_REPORT.md:112 ghi "unseen / zero leakage" sai phần CSLR;
   có thêm backlog train lại CSLR chia theo câu không, và có lưu checkpoint CSLR/ViT5 lên Kaggle dataset PRIVATE không.
3. Bỏ chế độ `--source mock` của realtime_demo.py (kế hoạch 11; 5 trong 9 vi phạm) — kế hoạch 10 §7.6 dự kiến hỏi khi lập kế hoạch 11.
