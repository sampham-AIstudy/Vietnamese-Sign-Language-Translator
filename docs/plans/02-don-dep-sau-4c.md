# Kế hoạch 02 — Dọn dẹp sau điểm dừng 4c (quyết định mục 5 và 6 của người dùng)

> **CẦN NGƯỜI DÙNG — chỉ cho MỘT mục con (A3), KHÔNG chặn việc bắt đầu code.**
> Planner thấy trong `.git/index` rằng `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` **đang được
> git track** (review 02 vòng 1 đã xác nhận). Quyết định 5 của người dùng ("thêm reports/**/*.pt vào .gitignore") không nói gì
> về file đã track. `git rm --cached` không xóa file trên đĩa và hoàn tác được, nhưng nó GỠ file khỏi repo, tức clone sạch
> sẽ không còn checkpoint Cấp 1 thật (README dòng 51, `tests/test_fingerspelling_api.py:34`, handoff 2026-09-25 đều trỏ tới).
> Ngoài ra checkpoint này train trên bộ hauuto "license unknown, internal use only" (`.gitignore:69`) và có thể đã được push.
> Vì đây là "xóa file" khỏi repo (autopilot §5), A3 chỉ làm SAU khi người dùng trả lời (§7). Mọi bước khác làm ngay.
> Lần sửa 1 KHÔNG thêm điểm dừng nào và KHÔNG mở rộng lưu trữ (A3 và câu hỏi §7.2 vẫn chờ người dùng).
>
> Điểm dừng có điều kiện trong khi làm (xem §7): kiểm tra private thất bại → DỪNG ngay; slug Kaggle đã tồn tại → hỏi
> orchestrator; tổng dung lượng tải lên > 2 GB → hỏi orchestrator.

Nhánh `feat/vslt-complete`. Lập kế hoạch lần đầu tại HEAD `09d4057` (gọi là `P`, commit gốc của việc này); lập lại (Lần sửa 1)
tại HEAD `12ef791`. Ngày 2026-09-27.

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
Thiếu bất kỳ file nào trong số đó thì `Inputs.add` báo mã 2. Lỗi nằm ở KẾ HOẠCH, coder chỉ làm theo:
1. §3.3 (bản trước) đưa ra câu mẫu gõ sẵn, chỉ nêu "log kernel và `train.log`". Nó mâu thuẫn với §6, nơi viết rằng log kernel,
   `train.log`, `data/processed/`, `checkpoints/` không nằm trong lưu trữ và "REPORT phải nói đúng như vậy".
2. Câu mẫu là một danh sách GÕ TAY các loại file bị thiếu, không sinh từ dữ liệu. Vì vậy nó lệch với tập đầu vào thật.
   Đúng ra danh sách phải tính từ `inputs` (đã có sha256), so với git và với manifest.
3. Câu mẫu bỏ ý "sha256 ở mục 1.4 là bằng chứng thay thế" của câu cũ, nên 8 file trên không còn được nói là chỉ có sha256.
4. AC1 ca 14 chỉ kiểm câu có chứa "private" và "log kernel". Nó không kiểm câu có nói đúng phạm vi tái tạo hay không.

**Nhận xét không chặn, §1.5 REPORT dòng 163 (`scripts/report_step4.py:1202`).** "Chỉ chủ dự án truy cập được" mạnh hơn bằng
chứng. Script chỉ xác minh `is_private` (hai nguồn), không kiểm danh sách người được chia sẻ. Lỗi này cũng từ kế hoạch: §3.3 bản
trước gõ sẵn câu đó.

### 0.2 Lệch kế hoạch được planner CHẤP NHẬN (ghi lại, không phải lỗi)
- `3b89a92`: trong `upload`, nếu `dataset_status` trả 403/404 thì kiểm lại bằng `dataset_list(mine=True)` trước khi coi là slug
  chưa có. Mã khác 403/404 → 6; có trong danh sách → 5; server cũng từ chối tạo trùng slug. Test 05b/05c/05d kiểm. Hướng lỗi vẫn
  an toàn, nên §3.2 được hiểu là gồm bước kiểm lại này.
- `stage`/`upload` chạy khi `scripts/report_step4.py` còn WIP chưa commit (message `5ead317`), nên yêu cầu "HEAD sạch" của S4
  không đạt trọn vẹn. Planner chấp nhận: kết quả không phụ thuộc `report_step4.py`, và `verify` (ở `2b3ca94`) băm lại toàn bộ,
  file trên Kaggle khớp hash. Ghi vào progress_log là UNVERIFIED đã có giải thích.

### 0.3 Thay đổi so với bản trước
- §3.3: thay câu Giới hạn gõ sẵn bằng câu SINH TỪ `inputs` (hàm mới `untracked_unarchived_inputs`, `git_tracked`), có mẫu câu
  chốt nguyên văn. Sửa câu §1.5 thành "private … không truy cập ẩn danh được".
- §4: thêm bước R0–R5 (các bước S0–S7 cũ đã làm; S8 thay bằng R5, gồm ghi đủ lịch sử lệnh Kaggle).
- §5: THÊM AC1 ca 21–27. AC2 thêm ngưỡng số test. AC5 và AC9: thêm khóa JSON mới vào danh sách khóa được bỏ khi so với P, và
  cho phép số `n_inputs` trong dòng Giới hạn tăng đúng bằng số file review thêm vào (lý do: khóa/số mới do chính lần sửa này tạo;
  mọi giá trị cũ vẫn phải bằng nhau, danh sách file không track vẫn phải bằng nhau, nên không nới). AC8 ghi rõ lịch sử lệnh Kaggle.
  Không bỏ, không nới tiêu chí nào. Test cũ (kể cả `TestArchiveManifestAndReviews` ca 14–20) KHÔNG được sửa.
- §6: thêm rủi ro "danh sách đầu vào thiếu phụ thuộc trạng thái git lúc sinh".

---

## 1. Mục tiêu và DoD

**Mục tiêu.** (A) Chặn việc commit nhầm checkpoint/logits trong `reports/` bằng `.gitignore`. (B) Lưu checkpoint + logits
TEST của 9 run mà REPORT bước 4 dùng vào MỘT Kaggle dataset PRIVATE; slug + sha256 từng file do script sinh và được
`report_step4.py` đọc lại để in vào REPORT.md. (C) Sửa ba góp ý G1, G2, G3 của review 01 vòng 2 mà không nới test cũ.
(D) Sinh lại REPORT/JSON bằng script và cho vslt-reviewer review cả A–C. Lần sửa 1: REPORT nói ĐÚNG phạm vi tái tạo được sau
khi có lưu trữ.

**DoD phục vụ.**
- DoD 9 (Tài liệu, "Giới hạn" trung thực): REPORT nói đúng checkpoint/logits nằm ở đâu và đầu vào nào KHÔNG có ở đâu cả ngoài
  máy local, kiểm được bằng sha256.
- DoD 7 (Kiểm thử): test mới cho G1/G2/G3, cho script lưu trữ, và cho câu Giới hạn; test cũ giữ nguyên.
- DoD 10 (một phần): review cho các thay đổi của việc này.
- Quy tắc cứng autopilot §4: "Không commit ... token", "Không xóa dữ liệu, checkpoint", "Train nặng chỉ trên Kaggle (private
  dataset ...)". Việc này dùng 0 giờ GPU.

Không thuộc phạm vi: Việc 4 trở đi; fine-tune (ii); đổi model mặc định; mọi thay đổi `backend/`, `src/`, `configs/`,
`frontend/`; mở rộng lưu trữ (log kernel, `segments.csv`, `checkpoints/*.pt`, `run_seed43/history.json`: câu hỏi §7.2).

---

## 2. Hiện trạng

### 2.0 Sau các commit của coder (HEAD `12ef791`, theo review 02 vòng 1)
- Đã có: `.gitignore` (3 dòng thêm); `scripts/archive_step4_kaggle.py`; dataset private `phmvnsm33/vslt-step4-artifacts`
  (version 1, 19 file, reviewer kiểm độc lập); `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`;
  `report_step4.py` có `--archive-manifest` (`archive_summary` 563–598) và nhiều `--review-file` (`join_reviews` 549–556);
  REPORT/JSON/PROPOSAL sinh lại; test: `tests.test_archive_step4_kaggle` 24, `tests.test_report_step4` 88, AC2 53 (reviewer).
- Còn sai: câu Giới hạn khi có lưu trữ (`scripts/report_step4.py:1494–1498`, REPORT dòng 407); câu §1.5
  (`scripts/report_step4.py:1202`, REPORT dòng 163).
- Ràng buộc từ test đã có, KHÔNG được sửa: `TestArchiveManifestAndReviews.test_14_valid_manifest_section_1_5_and_limit`
  (`tests/test_report_step4.py:839–862`) đòi: trong mục Giới hạn có ĐÚNG MỘT dòng chứa `ref`; dòng đó chứa "private" và
  "log kernel"; toàn REPORT KHÔNG chứa chuỗi con "sha256 ở mục 1.4 là bằng chứng thay thế". Test 19 (`OLD_LIMIT`, dòng 806–807)
  đòi câu cũ nguyên văn khi KHÔNG có manifest. Câu mới ở §3.3 được chốt để thỏa cả hai.
- `docs/reviews/02-review.md` và `docs/plans/02-don-dep-sau-4c.md` chưa commit.

### 2.1 `.gitignore` (tại P)
- Dòng 35: `*.npz` đã bị bỏ qua ở MỌI nơi. Dòng 73: `reports/alphabet_nested_*/**/*.pt`. Dòng 75: `reports/step4_*/runs/**/*.pt`.
- KHÔNG có quy tắc cho `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` (review 01 mục 11) và
  `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`.
- Dòng 58–61 đã có `kaggle.json`, `.kaggle/`, `access_token`.

### 2.2 File `.pt`/`.npz` trong `reports/` trên đĩa (Glob tại P)
- 7 run bước 4, mỗi run có `stgcn_unified_best.pt` + `test_logits.npz`:
  `reports/step4_2026-09-26/runs/{run_keepz, run_dropz, run_keepz_seed43, dict_keepz, run_keepz_360, run_keepz_notrim,
  dict_keepz_360}/`.
- 2 run baseline mà REPORT dùng (vai trò `baseline` và `baseline-seed43`, REPORT §1.1 dòng 14 và 20; sha256 ở §1.4 dòng
  125–132): `reports/unified_run_2026-09-25/{run, run_seed43}/`.
- Khác: `reports/alphabet_nested_2026-09-25/{primary,variants}/alphabet_nested_final.pt` (đã bị ignore bởi dòng 73),
  `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` (đang track, A3).
- `REPORT_partial.md`: không còn trong `reports/step4_2026-09-26/`. Người dùng đã chuyển ra `../_backup_step4/`.

### 2.3 `scripts/report_step4.py` (tại P; số dòng đã lệch sau các commit của coder)
- `sha256` 476–485; `Inputs` 519–533 (thiếu file → `ReportError(2)`); `git()` 498–500 (trả `None` khi git lỗi).
- `build`: `review` ở dòng 629; `prov_runs[name]` có `dir`, `sha256_test_logits`, `sha256_ckpt` (914–922); dict kết quả 1023–1042.
- `render`: §1.4 ở 1129–1130; câu Giới hạn cuối ở 1421; §6 ở 1423–1424. `parse_args` 1440–1461; `main` 1464–1483.

### 2.4 Test (tại P)
- `tests/test_report_step4.py`: 69 test. `TestProposal4c` 420–455, `TestProposal4cScope` 718–780. G1/G2/G3 như review 01 vòng 2.

### 2.5 Kaggle CLI trong `.venv` (đọc mã, không chạy)
- `kaggle 2.2.4`, `kagglesdk 0.1.37`. OAuth, user `phmvnsm33`. Không đọc, không in `~/.kaggle/*`.
- `dataset_create_new(folder, public=False, ...)`: `request.is_private = not public` (`kaggle_api_extended.py:5605, 5630`).
  Slug đã tồn tại → trả `status="error"` (5586–5595). Slug/title 6–50 ký tự (5570–5573). `dir_mode="skip"` bỏ thư mục con.
- **Bẫy:** `dataset_metadata_update` đặt `is_private = metadata.get("isPrivate") or False` (4760). CẤM gọi.
- Kiểm private: `dataset_list(mine=True)` → `ApiDataset.is_private` (`kagglesdk/datasets/types/dataset_api_service.py:658, 836`);
  `dataset_metadata` → `DatasetInfo.isPrivate` (`kagglesdk/datasets/types/dataset_types.py:62, 246`). Bool mặc định False, nên
  lỗi thiên về phía "không private" (an toàn).

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu
```
step4_results.json (provenance.runs[*].dir, sha256_ckpt, sha256_test_logits)
   └─► archive_step4_kaggle.py stage   ─► ../_kaggle_staging/vslt-step4-artifacts/ (NGOÀI repo)
   └─► archive_step4_kaggle.py upload  ─► Kaggle dataset PRIVATE phmvnsm33/vslt-step4-artifacts (public=False)
   └─► archive_step4_kaggle.py verify  ─► reports/step4_2026-09-26/archive/kaggle_archive_manifest.json
report_step4.py --archive-manifest <manifest>
   ─► archive_summary (băm lại, so manifest/§1.4) ─► provenance.archive ─► REPORT §1.5
   ─► inputs × git ls-files × manifest.local_path ─► limitations_data.untracked_unarchived_inputs   [MỚI, Lần sửa 1]
                                                   ─► câu Giới hạn (mục 5)                           [SỬA, Lần sửa 1]
```
Không chạy model, không đọc TEST theo cách mới, không có số liệu ML mới. Mọi sha256/slug/kích thước/danh sách file do script sinh.

### 3.2 Script `scripts/archive_step4_kaggle.py` (đã cài; giữ nguyên hợp đồng)
CLI ba lệnh con `stage` → `upload` → `verify`:
```
python scripts/archive_step4_kaggle.py stage  --results reports/step4_2026-09-26/step4_results.json \
       --staging ../_kaggle_staging/vslt-step4-artifacts --dataset phmvnsm33/vslt-step4-artifacts
python scripts/archive_step4_kaggle.py upload --staging ../_kaggle_staging/vslt-step4-artifacts \
       --dataset phmvnsm33/vslt-step4-artifacts
python scripts/archive_step4_kaggle.py verify --staging ../_kaggle_staging/vslt-step4-artifacts \
       --dataset phmvnsm33/vslt-step4-artifacts --download-dir ../_kaggle_staging/verify_download \
       --manifest-out reports/step4_2026-09-26/archive/kaggle_archive_manifest.json
```
Mã thoát: 0 xong; 2 thiếu đầu vào / tham số sai / đường dẫn tạm trong repo / metadata không có `isPrivate: true`; 3 sha256 /
tập file / kích thước không khớp; 4 KHÔNG xác minh được private → DỪNG; 5 slug đã tồn tại; 6 Kaggle chưa `ready` / lỗi mạng.

`stage`: danh sách file từ `provenance.runs` (9 run × 2 = 18); sha256 nguồn phải bằng `sha256_ckpt`/`sha256_test_logits`; tên
phẳng `rel(dir)` bỏ `reports/`, `/`→`__`, rồi `__<tên file>`; `SHA256SUMS`; `dataset-metadata.json` có `"isPrivate": true`,
license `unknown`; staging phải ở NGOÀI repo.
`upload`: băm lại staging so `SHA256SUMS`; metadata `isPrivate is True`, `id == --dataset`; slug đã có → 5 (gồm bước kiểm lại
bằng `dataset_list(mine)` khi `dataset_status` trả 403/404, §0.2); một lần `dataset_create_new(..., public=False, dir_mode="skip")`.
CẤM: `public=True`, `--public`, `-u`, `dataset_metadata_update`, `metadata --update`, `dataset_delete`, `dataset_create_version`.
`verify`: chờ `ready` (≥ 60 s/lần, ≤ 60 phút); private từ hai nguồn đều `True`; `dataset_list_files` (có phân trang) khớp tên +
kích thước; tải về ngoài repo, băm lại; ghi manifest với đúng các khóa:
```
{"generated_by": {"script", "command", "git_commit", "kaggle_version", "kagglesdk_version", "verified_at_utc"},
 "dataset": {"ref", "url", "title", "license", "is_private": true,
             "is_private_sources": {"dataset_list_mine": true, "dataset_metadata": true}, "status": "ready", "total_bytes"},
 "files": [{"run", "run_dir", "kind", "local_path", "archive_name", "size_bytes", "sha256", "sha256_after_download"}],
 "sha256sums_file": {"archive_name": "SHA256SUMS", "sha256"},
 "verified": {"file_list_matches": true, "downloaded_sha256_all_match": true, "n_files": 18}}
```

### 3.3 `scripts/report_step4.py` (chỉ THÊM; giữ mọi tham số, mã thoát, khóa JSON cũ)
Đã cài (giữ nguyên hành vi):
- `--archive-manifest PATH`: `inputs.add(PATH, "archive manifest")` (thiếu → 2); `archive_summary` kiểm private, verified, tập run,
  2 file/run, sha256 (local = sau tải về = provenance) → lỗi là 3; JSON `provenance.archive`; mục `### 1.5` sau §1.4, trước `## 2.`.
- Không có manifest: `provenance.archive = None`, không có §1.5, câu Giới hạn cũ NGUYÊN VĂN.
- `--review-file` nhận một hoặc nhiều file (`join_reviews`).

**[SỬA, Lần sửa 1] Câu §1.5 về quyền truy cập.** Thay "Chỉ chủ dự án truy cập được; tải: …" bằng câu chốt nguyên văn:
"Dataset private theo Kaggle API (không truy cập ẩn danh được; chỉ tài khoản chủ và người được chia sẻ truy cập được; danh sách
chia sẻ không được kiểm); tải: `kaggle datasets download <ref>`; kiểm: `sha256sum -c SHA256SUMS`."

**[MỚI, Lần sửa 1] Hàm thuần.**
- `git_tracked(paths) -> set[str]`: nhận các đường dẫn đã `rel()`. Đường dẫn nằm NGOÀI repo (tuyệt đối sau `rel`) thì coi là
  không track, không gọi git cho nó. Với các đường dẫn trong repo: MỘT lời gọi `git ls-files -z -- <paths…>`; trả tập đường dẫn
  được track (so sau khi chuẩn hóa `/`). `git()` trả `None` (git lỗi) → `ReportError(2, "không xác định được file nào được git
  track")`. Không dùng `--others`/`--ignored`. Không cache giữa các lần gọi `build`.
- `untracked_unarchived_inputs(inputs, tracked, archived) -> list[dict]`: `inputs` là `inputs.as_list()`; `archived` là tập
  `rel(files[*].local_path)` của manifest (rỗng nếu không có manifest). Trả các phần tử `{"path", "sha256", "role"}` có
  `path ∉ tracked` và `path ∉ archived`, sắp theo `path`. Không lọc theo vai trò.

**[MỚI, Lần sửa 1] Khóa JSON** `limitations_data.untracked_unarchived_inputs = {"n": <số phần tử>, "n_inputs": len(inputs),
"files": [...]}`. Luôn tính (có hoặc không có manifest), dùng `inputs` cuối cùng của `build` (sau khi mọi `inputs.add` đã xong,
kể cả file review và manifest).

**[SỬA, Lần sửa 1] Câu Giới hạn khi có manifest** (đúng MỘT gạch đầu dòng, một dòng). Hai nhánh, chữ cố định chốt nguyên văn,
chỉ phần trong `{}` là dữ liệu:
- `n > 0`:
  "- Checkpoint và logits TEST của mọi run được lưu ở Kaggle dataset private `{ref}` (sha256 ở mục 1.5); lưu trữ không gồm log
  kernel hay đầu vào nào khác. {n}/{n_inputs} đầu vào của báo cáo này vừa không được git track vừa không nằm trong lưu trữ:
  `{path_1}`, `{path_2}`, …; bằng chứng thay thế cho các file này là sha256 ở mục 1.4. Thiếu một đầu vào thì
  scripts/report_step4.py dừng với mã 2, nên kể cả khi có quyền truy cập dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo."
- `n == 0`:
  "- Checkpoint và logits TEST của mọi run được lưu ở Kaggle dataset private `{ref}` (sha256 ở mục 1.5); lưu trữ không gồm log
  kernel hay đầu vào nào khác. Mọi đầu vào của báo cáo này đều được git track hoặc nằm trong lưu trữ."
  (Nhánh này không khẳng định "tái tạo được": việc đó còn phụ thuộc môi trường, không được kiểm ở đây.)
- Hai câu trên thỏa test 14 cũ: một dòng có `ref`, có "private" và "log kernel", KHÔNG chứa chuỗi con
  "sha256 ở mục 1.4 là bằng chứng thay thế" (cụm mới là "bằng chứng thay thế cho các file này là sha256 ở mục 1.4").
  Coder không được đổi chữ cố định; nếu thấy mâu thuẫn với test cũ thì báo planner, không sửa test.
- Không có manifest: câu cũ nguyên văn (test 19), không in danh sách.

**Trạng thái git lúc sinh.** Danh sách phụ thuộc git index lúc chạy. Vì vậy mọi file đầu vào mà việc này tạo ra (file review
`docs/reviews/02-review.md`, manifest) phải được COMMIT TRƯỚC lần sinh cuối (R5), để REPORT đã commit khớp với git.

### 3.4 `.gitignore` (đã làm)
Khối ở cuối file: chú thích + `reports/**/*.pt` + `reports/**/*.npz`. Không xóa dòng nào. `alphabet_real_best.pt` vẫn track (A3).

### 3.5 PROPOSAL_4c.md (G3) và cách đếm từ (G2) (đã làm; giữ nguyên hợp đồng)
- (b) nói mẫu số là DỰ ĐOÁN SAI; có lưu ý S06; có "tỷ lệ nền … không phải giả thuyết không (null) chuẩn"; "Chỉ báo, không kiểm định".
- Cách đếm từ: `len(re.findall(r"[^ \t\n\r\f\v]+", text))` trên văn bản UTF-8, phải bằng `len(text.split())` và ≤ 550.
  `wc -w` ở locale mặc định của Git Bash KHÔNG phải cách đo.
- Lần sửa 1 KHÔNG sửa PROPOSAL.

### 3.6 Module tiền xử lý chung
Không đổi. Không chạm `src/`, `backend/`, `configs/`, `frontend/`.

---

## 4. Chia việc

Quy tắc chung: `impact` (upstream) trước khi sửa symbol có sẵn (ít nhất `render`, `build`); `detect-changes --scope all` trước MỖI
commit (partial/truncated → chạy lại); chỉ `git add <đường dẫn cụ thể>`; không commit `*.pt`/`*.npz`/`*.log`/dữ liệu/staging;
không viết lại lịch sử; không đụng thay đổi chưa commit của người dùng.

S0–S7 của bản trước đã làm (commit ở §0). Lần sửa 1 gồm R0–R5. S8 cũ thay bằng R5.

**R0 — Kiểm trạng thái (≈ 0.25 giờ, không sửa gì).** Phụ thuộc: không.
- `git log --oneline -1` → `12ef791`. `git status --porcelain -- scripts src tests` → rỗng. `git diff --cached --name-only` → rỗng.
- Chạy `tests.test_archive_step4_kaggle tests.test_report_step4` và AC2 → ghi số "trước" (review: 24 + 88; 53).
- Không có lệnh Kaggle nào (ghi hay đọc) trong Lần sửa 1, trừ lệnh chỉ đọc nếu reviewer cần.

**R1 — Test trước (≈ 1 giờ).** Phụ thuộc: R0.
THÊM vào `tests/test_report_step4.py` (không sửa dòng cũ nào) AC1 ca 21–27. Ca 27 đọc file thật, sẽ FAIL tới R3.

**R2 — Cài đặt (≈ 1 giờ).** Phụ thuộc: R1.
Thêm `git_tracked`, `untracked_unarchived_inputs`, khóa JSON, câu Giới hạn mới, câu §1.5 mới (§3.3). Chạy ca 21–26 + toàn bộ test
cũ + AC2. Commit mã + test (commit A5).

**R3 — Sinh lại REPORT/JSON (≈ 0.5 giờ).** Phụ thuộc: R2 đã commit (`code_dirty=false`).
Lệnh R: lệnh ở header REPORT.md hiện tại, không đổi đối số (`--review-file docs/reviews/01-review.md` + `--archive-manifest …`).
Chạy hai lần, `cmp` (AC5). Chạy toàn bộ test (gồm ca 27). Commit REPORT/JSON (commit B').

**R4 — Review vòng 2 (orchestrator gọi vslt-reviewer).** Phụ thuộc: R3. Reviewer thêm vòng 2 vào `docs/reviews/02-review.md`.
Còn FAIL → quay lại R1–R3 (tối đa 3 vòng). Chỉ planner đổi tiêu chí.

**R5 — Bản cuối + đóng việc (≈ 0.5 giờ).** Phụ thuộc: R4 không còn FAIL.
1. Commit C1: `docs/reviews/02-review.md` + `docs/plans/02-don-dep-sau-4c.md` (không file nào khác).
2. Tại HEAD = C1 (sạch): lệnh R nhưng `--review-file docs/reviews/02-review.md docs/reviews/01-review.md`. Chạy hai lần, `cmp`.
   Kiểm AC5, AC9. Chạy toàn bộ test.
3. Thêm 1 dòng progress_log (AC8, gồm lịch sử lệnh Kaggle đầy đủ). `detect-changes --scope all`. Commit C2
   (REPORT/JSON + progress_log).
4. Nếu người dùng đã trả lời §7.1: A3 thành commit riêng theo câu trả lời, có dòng progress_log riêng.

Ước lượng GPU: **0 giờ**. Không có `kaggle kernels push`. Lần sửa 1 không tải gì lên Kaggle.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder không được đổi; chỉ planner đổi và phải ghi lý do)

Mọi lệnh Python chạy qua `.venv/Scripts/python` với `PYTHONIOENCODING=utf-8`, từ thư mục gốc repo.

**AC1 — Test, mỗi ca một test riêng, không skip, không cần mạng.**
`.venv/Scripts/python -m unittest tests.test_archive_step4_kaggle tests.test_report_step4 -v` → `OK`, 0 skip.

Ca 1–13 (`tests/test_archive_step4_kaggle.py`) và ca 14–20 (`TestArchiveManifestAndReviews`) giữ nguyên như bản trước:
1. `stage` thành công, tên phẳng xác định, `SHA256SUMS` đúng, metadata `isPrivate is True`, `id`, license `unknown`.
2. `stage`: sha256 nguồn khác results → 3, không có staging. 3. staging trong ROOT → 2; thiếu file nguồn → 2.
4. `upload` gọi create đúng 1 lần, `public is False`, `dir_mode == "skip"`. 5. slug đã có → 5, không gọi create.
6. metadata thiếu/sai `isPrivate` → 2. 7. staging bị sửa / file thừa → 3. 8. create trả `status="error"` → 6.
9. `verify`: private False ở bất kỳ nguồn nào / không có trong danh sách → 4, không có manifest.
10. danh sách file thiếu / kích thước khác → 3; phân trang gộp đúng. 11. hash tải về khác → 3.
12. manifest đúng tập khóa ở mọi cấp; `n_files` = 2 × số run. 13. guard mã nguồn (không `public=True`, `"--public"`,
    `dataset_metadata_update`, `dataset_delete`, `dataset_create_version`, `metadata --update`).
14. manifest hợp lệ → `provenance.archive`, §1.5 đúng vị trí, sha256, một dòng Giới hạn có `ref`/"private"/"log kernel", không
    chứa "sha256 ở mục 1.4 là bằng chứng thay thế". 15. sha256 lệch → 3. 16. không private / nguồn false / download false → 3.
17. thiếu/thừa run → 3. 18. manifest không tồn tại → 2. 19. không có manifest → câu cũ nguyên văn, `archive is None`.
20. nhiều `--review-file` → thứ tự + tiêu đề; một file → như cũ.

MỚI (Lần sửa 1), THÊM vào `tests/test_report_step4.py`:
21. `untracked_unarchived_inputs`: inputs giả 5 phần tử; 2 được track, 1 trong `archived`, 1 vừa track vừa archived → trả đúng
    phần tử còn lại (1 phần tử), và thêm một ca 2 phần tử không track/không archived → trả cả hai, sắp theo `path`; mỗi phần tử có
    đúng khóa `path`, `sha256`, `role`. `inputs` rỗng → `[]`.
22. `git_tracked`: `scripts/report_step4.py` → được track; một đường dẫn trong repo không tồn tại (vd.
    `reports/__no_such_file__.txt`) → không track; một đường dẫn tuyệt đối trong thư mục tạm ngoài repo → không track, git KHÔNG
    được gọi cho nó (kiểm bằng cách thay `R.git` bằng hàm ghi lại tham số). `R.git` trả `None` → `ReportError` mã 2; qua `main`
    → trả 2 và không ghi file.
23. Fixture + manifest hợp lệ (fixture nằm ngoài repo nên mọi đầu vào đều không track): `limitations_data.untracked_unarchived_inputs.files`
    có tập `path` = tập `inputs[*].path` trừ tập `local_path` của manifest; `n` = độ dài; `n_inputs = len(inputs)`. Dòng Giới
    hạn (dòng duy nhất chứa `ref`) chứa: `f"{n}/{n_inputs} đầu vào"`, mọi `path` trong danh sách (trong dấu backtick),
    "bằng chứng thay thế cho các file này là sha256 ở mục 1.4", "kể cả khi có quyền truy cập dataset",
    "vẫn KHÔNG tái tạo được báo cáo", "mã 2". Dòng đó KHÔNG chứa "không có quyền truy cập dataset thì".
24. Nhánh `n == 0` (thay `R.git_tracked` bằng hàm trả mọi đường dẫn): dòng Giới hạn chứa "Mọi đầu vào của báo cáo này đều được
    git track hoặc nằm trong lưu trữ", KHÔNG chứa "kể cả khi" và KHÔNG chứa "tái tạo được".
25. §1.5 (fixture + manifest): chứa "không truy cập ẩn danh được" và "danh sách chia sẻ không được kiểm"; toàn REPORT KHÔNG chứa
    "Chỉ chủ dự án".
26. Không có manifest: khóa `limitations_data.untracked_unarchived_inputs` vẫn có (`n_inputs = len(inputs)`); REPORT không chứa
    "kể cả khi có quyền truy cập dataset" (câu cũ nguyên văn đã do test 19 kiểm).
27. File THẬT (lớp mới, thiếu file thì FAIL, không skip): đọc `reports/step4_2026-09-26/{REPORT.md, step4_results.json,
    archive/kaggle_archive_manifest.json}`. Test tự tính lại, KHÔNG gọi `report_step4.py`: tập đường dẫn `inputs[*].path` không có
    trong output `git ls-files -z -- <các path đó>` và không có trong `rel(files[*].local_path)` của manifest. Tập này phải bằng
    tập `path` của `limitations_data.untracked_unarchived_inputs.files` và khác rỗng. Mọi `path` đó có trong dòng Giới hạn của
    `body` (phần trước `"\n## 6. Review\n"`) chứa `ref`. Dòng đó chứa "kể cả khi có quyền truy cập dataset" và
    "bằng chứng thay thế cho các file này là sha256 ở mục 1.4". `body` chứa "không truy cập ẩn danh được" và không chứa
    "Chỉ chủ dự án".

**AC2 — Không hồi quy.** Bộ 10 module handoff → cùng số test như R0 (53), `OK`. `tests.test_report_step4`: số sau ≥ số trước R0
(88) + 7 (ca 21–27). `tests.test_archive_step4_kaggle`: số sau = số trước (24). `git diff 09d4057 HEAD -- tests/` và
`git diff 12ef791 HEAD -- tests/` chỉ có dòng THÊM (không dòng `-` nào ngoài header diff). `TestProposal4c`,
`TestProposal4cScope`, `TestProposal4cCleanup`, `TestArchiveManifestAndReviews` không đổi và vẫn qua. Ghi trước → sau vào progress_log.

**AC3 — `.gitignore` (A).** Như bản trước: diff so với P chỉ thêm dòng (`reports/**/*.pt`, `reports/**/*.npz`, chú thích);
`git check-ignore -q` exit 0 cho 18 file của `provenance.runs` và 2 `alphabet_nested_final.pt`; `git ls-files reports | grep -E
'\.(pt|npz)$'` sau = trước (trừ A3 nếu được duyệt); `git diff --name-only --diff-filter=AM 09d4057..HEAD -- '*.pt' '*.npz' '*.log'` rỗng.

**AC4 — Lưu trữ Kaggle (B).** Như bản trước (manifest do `verify` ghi; 18 file; sha256 = §1.4 tại P = sau tải về; private từ hai
nguồn; `ready`; reviewer kiểm độc lập; không lộ credential; không lệnh `metadata --update`/`version`/`delete`/`kernels push`).
Lần sửa 1 không được đổi manifest (`git diff 12ef791 HEAD -- reports/step4_2026-09-26/archive/` rỗng) và không chạy lệnh Kaggle ghi.

**AC5 — REPORT sinh bằng script, tái lập.**
- Lệnh R3 và lệnh R5 exit 0. Header chứa đúng lệnh và HEAD `h`; `git diff h -- scripts/ src/ tests/` rỗng; `code_dirty = false`.
- Chạy lần 1, sao REPORT.md + step4_results.json ra thư mục tạm, chạy lại đúng lệnh → `cmp` hai cặp file: không khác.
- So với P: nạp JSON ở `09d4057` và bản mới, bỏ `generated_by`, `review`, `provenance.archive`,
  `limitations_data.untracked_unarchived_inputs` *(thêm ở Lần sửa 1: khóa mới do lần sửa này tạo, không có ở P)*, và mọi phần tử
  `inputs` có vai trò chứa "review" hoặc "archive manifest"; so bằng `==` → bằng nhau.
- `git diff 09d4057 HEAD -- reports/step4_2026-09-26/REPORT.md` chỉ chạm: dòng Lệnh/HEAD; dòng §1.4 của manifest và file review
  mới; §1.5 mới; đúng MỘT dòng Giới hạn (câu cũ); nội dung sau `## 6. Review`.
- So với `12ef791` (Lần sửa 1): `git diff 12ef791 B' -- REPORT.md` chỉ chạm dòng Lệnh/HEAD, câu truy cập ở §1.5, và dòng Giới
  hạn có `ref`. JSON ở `12ef791` và B' bằng nhau sau khi bỏ `generated_by` và `limitations_data.untracked_unarchived_inputs`.

**AC6 — G1, G2, G3 (`TestProposal4cCleanup`).** Như bản trước, không đổi; vẫn qua.

**AC7 — Phạm vi thay đổi.** `git diff --stat 09d4057..HEAD` chỉ gồm: `.gitignore`, `scripts/archive_step4_kaggle.py`,
`scripts/report_step4.py`, `tests/test_archive_step4_kaggle.py`, `tests/test_report_step4.py`,
`reports/step4_2026-09-26/{REPORT.md, step4_results.json, PROPOSAL_4c.md, archive/kaggle_archive_manifest.json}`,
`docs/progress_log.md`, `docs/plans/02-don-dep-sau-4c.md`, `docs/reviews/02-review.md`; và A3 nếu được duyệt. Lần sửa 1 chỉ được
đổi `scripts/report_step4.py`, `tests/test_report_step4.py`, `REPORT.md`, `step4_results.json`, `docs/progress_log.md`, và commit
`docs/plans/02-…`, `docs/reviews/02-review.md`. KHÔNG đổi: `backend/`, `src/`, `configs/`, `frontend/`, `data/`,
`PREREGISTRATION.md`, `history.json`, `metrics.json`, JSON 4a/4b, `docs/reviews/01-review.md`, `PROPOSAL_4c.md` (Lần sửa 1),
`scripts/archive_step4_kaggle.py` (Lần sửa 1). `git status` vẫn cho thấy 3 file data bị xóa của người dùng như trước.

**AC8 — Quy trình.** Mỗi commit mới ghi `impact` (symbol đã sửa) và `detect-changes --scope all` (không partial/truncated) trong
commit message. Đúng 1 dòng progress_log cho kế hoạch 02 theo định dạng bảng hiện có: việc = "Dọn dẹp sau 4c: .gitignore, lưu trữ
Kaggle, G1–G3"; kế hoạch = `docs/plans/02-don-dep-sau-4c.md`; commit = mọi hash của việc (8 commit ở §0 + A5, B', C1, C2); kết
luận review = kết luận review 02 cuối + số vòng (vòng 1 CHANGES_REQUESTED, FAIL mục 13); việc tiếp theo = "Việc 4 (endpoint chuỗi
landmark Cấp 1)". Ngay dưới dòng đó, ghi đủ:
- số test trước → sau (AC2) ở P, ở `12ef791`, và cuối;
- số từ PROPOSAL theo §3.5 (545) và ghi chú: PROPOSAL đã sửa câu chữ sau khi người dùng quyết B (dòng 6, 11, 17, 32), nội dung
  quyết định không đổi;
- ref dataset, số file, tổng byte (lấy từ manifest);
- **lịch sử lệnh Kaggle của coder, theo thứ tự, mỗi lần một dòng có mã thoát và nguyên nhân:** `stage` (exit 0); `upload` lần 1
  (exit 6: 403 ở GetDatasetStatus), `upload` lần 2 (exit 6: đường dẫn tương đối), `upload` lần 3 (exit 0); `verify` lần 1 (exit 6:
  404 ở DownloadDataset), `verify` lần 2 (exit 0). Coder đối chiếu với log `../_kaggle_staging/*.out` và commit message; nếu lệch
  với danh sách này thì ghi đúng theo log và nêu chỗ lệch;
- lệnh Kaggle chỉ đọc của reviewer (theo review 02: `datasets list --mine`, `datasets status`, `datasets files`,
  `datasets download -f`, `dataset_list(mine=True)`, `dataset_metadata`, `curl` ẩn danh);
- UNVERIFIED đã giải thích: `stage`/`upload` chạy khi `report_step4.py` có WIP chưa commit (§0.2);
- trạng thái A3 (chờ người dùng / đã làm theo câu trả lời) và câu hỏi §7.2 (chờ người dùng).

**AC9 — Lần sinh cuối chỉ thêm review.** Gọi B' là commit R3, C2 là commit R5.3.
- `git diff B' C2 -- reports/step4_2026-09-26/REPORT.md` chỉ chạm: dòng Lệnh/HEAD; dòng §1.4 của `docs/reviews/02-review.md`;
  nội dung sau `## 6. Review`; và trong dòng Giới hạn có `ref` CHỈ số `{n_inputs}` (tăng đúng bằng số file review thêm, tức +1).
  Phần còn lại của dòng đó, gồm `{n}` và danh sách đường dẫn, phải giữ nguyên, vì file review 02 đã được commit ở C1 trước khi
  sinh nên không vào danh sách đầu vào không track. *(Làm rõ ở Lần sửa 1: `n_inputs` là số mới do lần sửa này tạo.)*
- JSON ở B' và C2 bằng nhau (`==`) sau khi bỏ `generated_by`, `review`, phần tử `inputs` có vai trò "review", và trong
  `limitations_data.untracked_unarchived_inputs` chỉ bỏ trường `n_inputs` (danh sách `files` và `n` phải bằng nhau).
- §6 chứa kết luận review 02 (đứng trước) và review 01.

**AC10 — Review.** vslt-reviewer (`docs/reviews/02-review.md`, vòng ≥ 2): không FAIL cho các commit của việc này; mục 13 PASS
(câu Giới hạn đúng phạm vi tái tạo, danh sách khớp số reviewer tự đếm từ `inputs`, `git ls-files`, manifest); mục 11 PASS với
bằng chứng AC4; mục 3 PASS với bằng chứng AC2.

---

## 6. Rủi ro dữ liệu / ML

- **Lộ dữ liệu có giấy phép chưa rõ.** Checkpoint/logits train từ QIPEDC + VSL-GH, giấy phép chưa rõ; chỉ ở dạng PRIVATE.
  Biện pháp: `public=False` là hằng; test guard; metadata `isPrivate: true`; kiểm private hai nguồn; exit 4 thì DỪNG. Không bao
  giờ gọi `datasets metadata --update` (`kaggle_api_extended.py:4760` đặt False khi thiếu `isPrivate`). Slug có trong REPORT.
- **Khẳng định quá mức về quyền truy cập (Lần sửa 1).** Script chỉ biết dataset private, không biết danh sách chia sẻ. REPORT chỉ
  được nói điều đã kiểm.
- **Khẳng định quá mức về khả năng tái tạo (Lần sửa 1).** Lưu trữ chỉ có 18 file. Các đầu vào khác không track (log kernel,
  `data/processed/…`, `checkpoints/*.pt`, `run_seed43/history.json` — theo reviewer) chỉ có sha256. REPORT phải liệt kê chúng từ
  dữ liệu và nói rõ kể cả có quyền dataset vẫn không tái tạo được.
- **Danh sách phụ thuộc trạng thái git lúc sinh (Lần sửa 1).** Nếu sinh khi một đầu vào chưa commit (vd. file review mới), REPORT
  sẽ liệt kê nó, rồi thành sai sau commit. Biện pháp: R5 commit review + kế hoạch TRƯỚC khi sinh; ca 27 kiểm REPORT đã commit
  khớp `git ls-files` hiện tại, nên nếu trạng thái git đổi về sau thì test báo REPORT đã cũ.
- **Truy nguồn lưu trữ.** sha256 băm ở nguồn, staging, bản tải về, và lại khi sinh REPORT. Không sha256 nào gõ tay.
- **Không có số liệu ML mới.** AC5 chứng minh mọi giá trị JSON cũ không đổi. Không có rủi ro rò rỉ, lệch train–realtime, cỡ mẫu mới.
- **G1/G2/G3.** Như bản trước; đã sửa, có test, không nới test cũ.
- **File `alphabet_real_best.pt` đang track.** `.gitignore` không gỡ nó; quyết định thuộc người dùng (§7.1).

---

## 7. Điểm dừng

- **Trước khi code Lần sửa 1: KHÔNG có điểm dừng.** Không đổi model mặc định, không cần dữ liệu người dùng, không đụng thay đổi chưa
  commit của người dùng, không có hành động không hoàn tác, không lệnh Kaggle ghi, không viết lại lịch sử.
- Điểm dừng có điều kiện của phần B (đã qua, giữ để tham chiếu): `verify` exit 4 → DỪNG, CẦN NGƯỜI DÙNG; slug đã tồn tại → hỏi;
  tổng > 2 GB → hỏi.
- **§7.1 — CẦN NGƯỜI DÙNG (A3, không chặn phần còn lại).** Orchestrator gửi câu hỏi, kèm output S0 và ghi chú của reviewer (nhánh
  hiện tại chưa có remote-tracking; các nhánh khác có thể đã push file):
  > `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` (checkpoint Cấp 1 thật, train trên bộ hauuto
  > giấy phép chưa rõ) đang được git track. `.gitignore` mới không gỡ được nó. Chọn một:
  > (a) giữ track như hiện nay; (b) lưu vào dataset Kaggle private (kế hoạch nhỏ riêng) rồi `git rm --cached` (file còn trên
  > đĩa; clone sạch không có nó; lịch sử git cũ vẫn chứa nó); (c) `git rm --cached` không lưu trữ.
  Chưa có câu trả lời thì không làm gì với file này. (b) cần tạo version dataset, là thao tác bị cấm trong kế hoạch này, nên planner
  phải lập kế hoạch nhỏ riêng trước.
- **§7.2 — Câu hỏi không chặn:** có lưu thêm 4 log kernel, `reports/unified_run_2026-09-25/run_seed43/history.json`, và (nếu được
  phép) `data/processed/vslgh_segments/segments.csv`, `checkpoints/*.pt` vào dataset private (version mới, kế hoạch nhỏ riêng)
  không? Nếu có, danh sách trong câu Giới hạn sẽ tự ngắn lại khi sinh lại REPORT với manifest mới.
- **Không bắt buộc:** PROPOSAL_4c.md đã sửa câu chữ sau khi người dùng quyết B (dòng 6, 11, 17, 32); nội dung quyết định không đổi.
  Người dùng xem lại nếu muốn.
- Sau R5: KHÔNG có điểm dừng bắt buộc. Orchestrator chuyển sang Việc 4.
