# Kế hoạch 12 — tiến độ (coder)

Kế hoạch: `docs/plans/12-khoi-phuc-du-lieu.md`. Nhánh `feat/vslt-complete`, HEAD lúc bắt đầu `0aa7a44`
(B0 chạy trên `79a7eb1` = 0aa7a44 + commit tạo file này).
Phạm vi lượt này: B0–B3 (B4 trở đi giao lượt sau).

## Bước đã xong

### B0 — kiểm kê ban đầu (chỉ đọc). Log: `_work/_plan12_tmp/B0_inventory_{1..7}.txt`, `B0_status_{before,after}.txt`
- `git status --porcelain`: 65 dòng; ` D` của người dùng còn đủ 3 dòng (`data (2)/Dataset/Labels/label.csv`,
  `data/alphabet_landmarks_full.csv`, `data/hand_data.csv`). before == after (B0 không đổi gì trong cây làm việc).
- 3 thư mục bị mất nội dung: `checkpoints/`, `data/Dataset/`, `data/external/` — đều TỒN TẠI, 0 file, 0 link.
- Ổ đĩa (`df -h .`): C: 376G, dùng 240G, trống 137G (64%).
- `kaggle --version` (.venv): Kaggle CLI 2.2.4. Credential: có (file `credentials.json` trong `~/.kaggle/`, không đọc nội dung);
  `kaggle datasets list --mine` exit 0, thấy 2 dataset private `phmvnsm33/vslt-provenance-artifacts`, `phmvnsm33/vslt-step4-artifacts`.
- Lịch sử git: `git log --all -- checkpoints/ "*.pt"` → 3 commit, chỉ chạm `experiments/*.torchscript.pt` và
  `reports/alphabet_real_run_2026-09-25/.../alphabet_real_best.pt`; `git rev-list --all --objects | grep " checkpoints/"` → 0.
  ⇒ a4 (`stgcn_best.pt`), a5 (ViT5), a6 (`cslr_best.pt`) KHÔNG có trong lịch sử git (xác nhận §8.1).
- `clone/Vietnamese-Sign-Language-Translation`: `.git` có; HEAD `6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a` (== data_registry);
  `status --porcelain` 6030 dòng ` D data/keypoints/*.npy` (đã xóa trên đĩa từ đợt audit); `ls-files data/keypoints` 6030;
  git-lfs 3.7.1 có, `lfs ls-files` 0 ⇒ không phải con trỏ LFS; blob mẫu `SENT001_S01_R01_F.npy` đọc được từ object DB
  (235220 byte, header NUMPY). Số file `_F.npy` trong HEAD: 4198 (ghi để B8 đối chiếu với 4200 trong `reports/vsl_gh_validation.json`).
- `clone/Parallel-Corpus-Vie-VSL`: `.git` có; HEAD `f57558c3fa79ced8a961cba825157c573fd4c74d` (== data_registry);
  status 1 dòng ` D "Parallel Corpus Vie-VSL.rar"`; `VSL10k.txt`, `Vie10k.txt` còn trên đĩa.
- 12 `reports/**/*.pt`: sha256 khớp 12/12 với 2 manifest, 0 đường dẫn manifest thiếu trên đĩa
  (`_work/_plan12_tmp/B0_reports_pt_sha.json`, lệnh `.venv/Scripts/python _work/_plan12_tmp/b0_reports_pt_sha.py <out>`).
- Không mất (kiểm lại): `reports/alphabet_deploy_2026-09-27/provenance.json` tracked; `data/processed` 26909 file,
  `data/extracted_keypoints` 3039, `data/splits` 48 (có `unified/`, `recording_groups.csv`), `data/raw_tudienngonngukyhieu` 437,
  `clone` 4422, `_work/_kaggle_staging` 157 file (0 link), có `restore_root/checkpoints/` 3 file .pt.

### B1 — checker chỉ đọc + spec (TDD)
- Mới: `scripts/check_restored_data.py` (chỉ ghi `--out`; `--out` chỉ trong `_work/` hoặc `reports/data_recovery_2026-10-01/`;
  `--dir-override <id>=<dir>` chỉ trong `_work/`; `--only`; thêm `--root` (mặc định = repo) để test dùng cây giả trong temp dir;
  loại mục `sha256 | count | video_frames | csv_ids | exists_only`; mã thoát 0/3/2; mục `private_names` không ghi tên clip vào
  `--out` ngoài `_work/`), `tests/test_check_restored_data.py`, `docs/recovery/expected_local_data.json` (31 mục: a1–a3,
  12 `rpt_*` = `reports/**/*.pt`, a4–a7 exists_only required=false, b1 ×2, b2, b3 ×4 + b4 required=false, c1, c2).
  Spec sinh bằng `_work/_plan12_tmp/gen_spec.py` (không commit): `expect_source` = file:dòng tìm bằng quét file; giá trị
  mong đợi đọc từ file tham chiếu lúc chạy (manifest/JSON/git blob), literal duy nhất: 640 / 4 người ký
  (`docs/data_registry.md:45`), 682 dòng (`docs/reviews/06-review.md:156`). c2 so blob `0aa7a44:data (2)/Dataset/Labels/label.csv`
  (ghim commit thay vì `HEAD` để không gãy nếu người dùng commit thao tác ` D`).
- Test đỏ trước: `_work/_plan12_tmp/B1_test_red.log` (ModuleNotFoundError). Xanh:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_check_restored_data -v` → `Ran 23 tests` `OK`, 0 skip
  (`_work/_plan12_tmp/B1_test_green.log`).
- `inventory_before.json` (`_work/_plan12_tmp/`): exit 3; ok 12 (12 `rpt_*`), missing 19, mismatch 0; required thất bại đúng
  8 mục mong đợi: a1, a2, a3, b1_hauuto_videos, b1_hauuto_facts, b2, c1, c2.
- impact: không sửa symbol có sẵn (chỉ file mới) ⇒ không cần impact upstream. Index GitNexus làm mới
  (`node .gitnexus/run.cjs analyze --index-only`, log `_work/_plan12_tmp/gitnexus_analyze_B1.log`; FTS build lỗi, graph OK).

### B2 — checkpoint a1–a3 (nguồn `_work/_kaggle_staging/restore_root/checkpoints/`, không cần mạng)
- Trước khi đặt: checker `--only a1 a2 a3 --dir-override <id>=_work/_kaggle_staging/restore_root/checkpoints` → 3/3 ok, exit 0
  (`_work/_plan12_tmp/B2_staging_check.json`); 0 link trong `restore_root`; `fsutil reparsepoint query checkpoints` → "not a reparse point".
- Đặt: kiểm `[ -e checkpoints/<f> ]` = không có, rồi `cp -n` 3 file (`_work/_plan12_tmp/B2_place.log`).
- sha256 SAU khi đặt (`sha256sum checkpoints/*.pt`, `_work/_plan12_tmp/B2_sha_after.txt`), khớp manifest
  `reports/private_archive_2026-09-28/kaggle_archive_manifest.json:24,36,48`:
  - `checkpoints/alphabet_best.pt` a6311820ba778b6b38a33cffffd58602b2bb840b8b35326b5bf46086e5b708a2
  - `checkpoints/stgcn_tier2_indomain.pt` 53c34cba43854c3e9820495bba3f93ffe18b5e1cb87ef44278a188ccafe2c826
  - `checkpoints/stgcn_unified_best.pt` 930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb
  Checker sau khi đặt (a1–a3 + 12 `rpt_*`): 15/15 ok, exit 0 (`_work/_plan12_tmp/B2_after_check.json`). Bản phẳng /
  tải lại Kaggle KHÔNG cần (bản `restore_root` đúng hash).
- Chạy nhanh: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_status_privacy tests.test_fingerspelling_compose -v`
  → `Ran 33 tests` `OK`, 0 skip (`_work/_plan12_tmp/B2_quicktests.log`).
- `git status --porcelain` before == after (`checkpoints/` bị gitignore, `.gitignore:62`); 0 link dưới `checkpoints/`.

### B3 — c2 `data/Dataset/Labels/label.csv` (bản git HEAD; §8.2 mặc định)
- Blob `HEAD:data (2)/Dataset/Labels/label.csv` = `0aa7a44:…` = `cdb547ea81cb9aa8c99f7d46ebc17462adbfdc2d`.
- `git show "HEAD:data (2)/Dataset/Labels/label.csv" > _work/_plan12_tmp/label_head.csv` → sha256 bằng `git cat-file blob … | sha256sum`;
  đích chưa có → `mkdir -p data/Dataset/Labels` + `cp -n` (`_work/_plan12_tmp/B3_place.log`). Không chạm `data (2)/` (thư mục
  không tồn tại trên đĩa; ` D` của người dùng giữ nguyên, không `git checkout`/`git add`).
- sha256 sau khi đặt: `b53a664e0bb4017dcce9bde9617b99f797cf535dfb7123ccc56cb44aa6630233` (== blob), 4363 dòng (`wc -l`);
  checker `--only c2_label_csv` → ok, exit 0 (`_work/_plan12_tmp/B3_after_check.json`). 0 link; `data/Dataset` không phải reparse point.
- `git status`: after khác before đúng 1 dòng `?? data/Dataset/` (AC0 cho phép); 3 dòng ` D` còn nguyên.
- So với label.csv trong gói QIPEDC Kaggle: để B6 (chỉ báo giống/khác).

### B4 — b2 `data/external/alphabet_hands_kaggle/alphabet_hands/` (output kernel PRIVATE, lượt 2 từ ae30658)
- `kaggle kernels status phmvnsm33/vsl-extract-alphabet` → `KernelWorkerStatus.COMPLETE` (`_work/_plan12_tmp/B4_kernel_status.txt`).
  `kaggle kernels files … --page-size 100`: ngày tạo file output `3:47 am, Friday 25 September 2026 UTC` (`B4_kernel_files_p1.txt`).
- Ổ đĩa trước tải: C: trống 137G. `kaggle kernels output phmvnsm33/vsl-extract-alphabet -p _work/_plan12_tmp/k_alphabet`
  19:57:58→20:06:34 (~8,5 phút, 15M); 688 file output tải đủ (`B4_kernel_output.log`: 688 dòng "Output file downloaded");
  lệnh thoát 1 vì lỗi `'charmap' codec` khi CLI ghi file log kernel (file `vsl-extract-alphabet.log` 0 byte) — chỉ ảnh hưởng
  file log. Log kernel lấy lại bằng `PYTHONUTF8=1 kaggle kernels logs …` → `B4_kernel_logs.txt` (exit 0): kernel clone
  commit `4d0600b feat(alphabet): shared camera-invariant hand features and LOSO training`, `done: 686 npz, 0 errors []`,
  `total 15.9 min`.
- Cấu trúc: `manifest.csv` + `tasks.csv` (687 dòng mỗi file = header + 686), 4 thư mục người ký hauuto × 160 npz + `qipedc/` 46 npz
  = 686 npz; 0 link.
- Kiểm TRƯỚC khi đặt: checker `--only b2_alphabet_manifest_ids --dir-override b2_alphabet_manifest_ids=_work/_plan12_tmp/k_alphabet/alphabet_hands`
  → ok, exit 0: `n_ref_rows` 682 (== `expected_ref_rows` 682), `n_target_rows` 686, `n_missing_ids` 0 (`B4_staging_check.json`).
- Đặt: `data/external/alphabet_hands_kaggle/alphabet_hands` chưa tồn tại; `data/external` không phải reparse point (fsutil
  4390), rỗng → `mkdir -p data/external/alphabet_hands_kaggle` + `mv -n` (`B4_place.log`: mv exit 0, 688 file, 0 link).
- Kiểm SAU khi đặt: checker `--only b2_alphabet_manifest_ids` → ok, exit 0 (`B4_after_check.json`).
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/alphabet_ckpt_provenance.py --out _work/_plan12_tmp/provenance_rerun.json`
  (HEAD a46a321) → `verdict=real_data_known_checkpoint`, V1–V6 True, `external_reproduction=46/46`, V6 `{"k": 46, "n": 46,
  "clips_in_csv": 46}`. So dict với `reports/alphabet_deploy_2026-09-27/provenance.json` (bỏ `generated_by`): **bằng hệt**
  (`equal_without_generated_by True`, 0 khóa lệch — `B4_provenance_compare.txt`).
- `git status --porcelain` before == after (`alphabet_hands_kaggle/` bị gitignore); 3 dòng ` D` còn nguyên.

## Đang làm
- Lượt 2 (giao: B4–B7, HEAD bắt đầu ae30658): B4 xong; **B5 ĐANG LÀM** (b1 hauuto).

## Còn lại
- B5 (b1 hauuto), B6 (c1 QIPEDC), B7 (kiểm tổng), B8 (b3/b4, tùy chọn), B9 (đóng) — lượt sau.
- Còn mở: §8.1 (a4 `stgcn_best.pt`, a5 ViT5, a6 `cslr_best.pt` + `gloss_vocab_canonical.txt`: không có trong lịch sử git — B0), §8.2 (label.csv: đang dùng mặc định bản git HEAD).

## Nhật ký detect-changes (`node .gitnexus/run.cjs detect-changes --scope staged --repo .`, nguyên văn)
- 79a7eb1 (tạo file): "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- B0 commit: "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- B1 commit: "Changes: 3 files, 65 symbols / Affected processes: 2 / Risk level: medium" — mọi symbol là mới trong
  `scripts/check_restored_data.py`; 2 luồng bị ảnh hưởng đều nằm trong script mới (Main → _load_json; Check_video_frames → Video_props).
- B2 commit: "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- B3 commit: "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- a46a321 (WIP B4): "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- B4 commit: "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
