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

## Đang làm
- B1 — checker chỉ đọc + spec (TDD).

## Còn lại
- B2, B3 (lượt này); B4–B9 (lượt sau).

## Nhật ký detect-changes (`node .gitnexus/run.cjs detect-changes --scope staged --repo .`, nguyên văn)
- 79a7eb1 (tạo file): "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
- B0 commit: "Diff touched 1 file(s) but no indexed symbols overlap those hunks — not a clean tree." (chỉ file .md)
