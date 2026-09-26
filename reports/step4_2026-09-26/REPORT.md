# Báo cáo Bước 4a–4c (sinh bởi scripts/report_step4.py)

- Lệnh: `python scripts/report_step4.py --baseline reports/unified_run_2026-09-25/run --runs H-keepz=reports/step4_2026-09-26/runs/run_keepz H-dropz=reports/step4_2026-09-26/runs/run_dropz --run-360 H-keepz-360=reports/step4_2026-09-26/runs/run_keepz_360 --aux-runs H-keepz-seed43=reports/step4_2026-09-26/runs/run_keepz_seed43 H-keepz-notrim=reports/step4_2026-09-26/runs/run_keepz_notrim baseline-seed43=reports/unified_run_2026-09-25/run_seed43 --dict-run reports/step4_2026-09-26/runs/dict_keepz --dict-run-360 reports/step4_2026-09-26/runs/dict_keepz_360 --shortcut-4a reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json --shortcut-4b reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json --shortcut-legacy-compare reports/step4_2026-09-26/4a/shortcut_85.json=reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps.json=reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_dropz_qipedc_kps.json=reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json --kernel-logs reports/step4_2026-09-26/runs/vsl-train-harmonized.log reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log reports/unified_run_2026-09-25/vsl-train-unified.log --out reports/step4_2026-09-26/REPORT.md --json-out reports/step4_2026-09-26/step4_results.json`
- HEAD: `f4729ff`; code_dirty (scripts/, src/, tests/): false
- Luật chọn đăng ký trước: `reports/step4_2026-09-26/PREREGISTRATION.md`. Chọn chỉ bằng VAL; TEST chỉ đọc lại `test_logits.npz` đã sinh một lần trong kernel; không TTA.
- Mọi số trong báo cáo này có trong `step4_results.json` (cùng dict) hoặc trong JSON đầu vào.

## 1. Provenance

### 1.1 Run

| Run | Vai trò | Thư mục | Log kernel | Repo commit (log) | Nhánh | Seed (log / ckpt) | Exit | Kết quả commit (metrics.json) | Sau lần sửa PREREG cuối |
|---|---|---|---|---|---|---|---|---|---|
| baseline | baseline | `reports/unified_run_2026-09-25/run` | reports/unified_run_2026-09-25/vsl-train-unified.log | b4916b9 | fix/audit-round2 | 42 / 42 | 0 | b3f98fd 2026-09-26 10:02:09 +0700 | KHÔNG |
| H-keepz | ứng viên (gốc) | `reports/step4_2026-09-26/runs/run_keepz` | reports/step4_2026-09-26/runs/vsl-train-harmonized.log | c8a7bdf | fix/audit-round2 | 42 / 42 | 0 | c9296bf 2026-09-26 12:12:25 +0700 | KHÔNG |
| H-dropz | ứng viên (gốc) | `reports/step4_2026-09-26/runs/run_dropz` | reports/step4_2026-09-26/runs/vsl-train-harmonized.log | c8a7bdf | fix/audit-round2 | 42 / 42 | 0 | c9296bf 2026-09-26 12:12:25 +0700 | KHÔNG |
| H-keepz-360 | ứng viên (360 px) | `reports/step4_2026-09-26/runs/run_keepz_360` | reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log | c65032a | fix/audit-round2 | 42 / 42 | 0 | 27233f6 2026-09-26 19:33:43 +0700 | CÓ |
| H-keepz-seed43 | phụ (không phải ứng viên) | `reports/step4_2026-09-26/runs/run_keepz_seed43` | reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log | c9296bf | fix/audit-round2 | 43 / 43 | 0 | a414b0d 2026-09-26 13:37:01 +0700 | CÓ |
| H-keepz-notrim | phụ (không phải ứng viên) | `reports/step4_2026-09-26/runs/run_keepz_notrim` | reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log | c65032a | fix/audit-round2 | 42 / 42 | 0 | 27233f6 2026-09-26 19:33:43 +0700 | CÓ |
| baseline-seed43 | phụ (không phải ứng viên) | `reports/unified_run_2026-09-25/run_seed43` | reports/unified_run_2026-09-25/vsl-train-unified.log | b4916b9 | fix/audit-round2 | 43 / 43 | 0 | b3f98fd 2026-09-26 10:02:09 +0700 | KHÔNG |
| dict_keepz | từ điển (4c) | `reports/step4_2026-09-26/runs/dict_keepz` | reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log | c9296bf | fix/audit-round2 | 42 / 42 | 0 | a414b0d 2026-09-26 13:37:01 +0700 | CÓ |
| dict_keepz_360 | từ điển (4c) | `reports/step4_2026-09-26/runs/dict_keepz_360` | reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log | c65032a | fix/audit-round2 | 42 / 42 | 0 | 27233f6 2026-09-26 19:33:43 +0700 | CÓ |

| Run | Lệnh train (từ log kernel) | run_config (metrics.json) | sha256 test_logits.npz | sha256 stgcn_unified_best.pt |
|---|---|---|---|---|
| baseline | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/data_root --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --out-dir /kaggle/working/run` | KHÔNG CÓ | `cded2935ed711382b759cfb377de4dade06856d797b7a98838968f5a7d5dacf3` | `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb` |
| H-keepz | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_native --out-dir /kaggle/working/run_keepz --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z keep` | `{"features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": null}` | `f66f20fef3875b7225d44f879c521f781557c810b8de8c51e0f68ce1d32b57ed` | `db1909493312bccb2bf7271ce375f01ff09c6b1cbb5b7ac442dc6246f357a92d` |
| H-dropz | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_native --out-dir /kaggle/working/run_dropz --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z drop` | `{"features": "harmonized", "hand_z": "drop", "sources": "all", "process_height": null}` | `4936a0cb33ec842d229f052c2bae967feaf591fc16f4a50cd124d3d93f8c8d0f` | `1dd35425dbc9a6f704ffc88fc9644bb753637b1749126ad3b47a28d5744b3924` |
| H-keepz-360 | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_360 --out-dir /kaggle/working/run_keepz_360 --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z keep --process-height 360` | `{"features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": 360, "trim": true}` | `0a560a6d3810f0578384d0fb110ebd728004881dd087ea2fe101f2ac4ea88bfe` | `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e` |
| H-keepz-seed43 | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_native --out-dir /kaggle/working/run_keepz_seed43 --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 43 --features harmonized --hand-z keep` | `{"features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": null}` | `bb2bf6b7f495c9a6d95daa952e794e6bc376095257e63371ae18748259f8dab1` | `f8f28f05170551a65b700b947e54fa5b96d348565aeaf4fabc41a35772acbd98` |
| H-keepz-notrim | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_native --out-dir /kaggle/working/run_keepz_notrim --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z keep --no-trim` | `{"features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": null, "trim": false}` | `a04cadca374457e787f4b9b2e056ae02577ad9ca7409cca0251a49fab1405eb9` | `92e603e19300e228ac220da8f1a07dae94e18a72bd105859f53de0c4b82e2df9` |
| baseline-seed43 | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/data_root --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 43 --out-dir /kaggle/working/run_seed43` | KHÔNG CÓ | `b4d5acf5118fada4d65673acca706d7c8c42ee76a1204d942f43f63528cc0cdd` | `a8f0dc6f7df597fe9bacfedadd846e8eabeada164e3a279bcc82c6b242279871` |
| dict_keepz | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_native --out-dir /kaggle/working/dict_keepz --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z keep --sources qipedc` | `{"features": "harmonized", "hand_z": "keep", "sources": "qipedc", "process_height": null}` | `1c8213657b42a4eb6f08e8e54b59ebbbf590fefa820f703a8502f29268aef397` | `62cb7f2006b22f99d64ddac1bef6164a7592e072cf470fc1b482ad6429435cc0` |
| dict_keepz_360 | `/usr/bin/python3 scripts/train_unified.py --data-root /tmp/root_360 --out-dir /kaggle/working/dict_keepz_360 --epochs 120 --batch-size 64 --num-workers 2 --patience 20 --seed 42 --features harmonized --hand-z keep --sources qipedc --process-height 360` | `{"features": "harmonized", "hand_z": "keep", "sources": "qipedc", "process_height": 360, "trim": true}` | `013c15075763ec118cff134b1e681ac81b686027af77df0f355f694328b6ba9f` | `1fc9031d127701146efe3a852f410d4bdefbf49264193a899659c6c3d52f54a7` |

Ghi chú cấu hình: run_config thiếu khóa trim (run trước commit 9b0ade1) được hiểu là trim=True (thêm cờ `--no-trim` với mặc định giữ cắt nghỉ; xem diff mã bên dưới).

### 1.2 Kernel

| Log | Repo commit | Ngày commit | Nhánh clone | Tổ tiên của HEAD | Run | Thời lượng (s, trường time cuối) | Tổng tự báo (phút) |
|---|---|---|---|---|---|---|---|
| `reports/step4_2026-09-26/runs/vsl-train-harmonized.log` | c8a7bdf | 2026-09-26 10:58:44 +0700 | fix/audit-round2 | CÓ | run_dropz, run_keepz | 4229.1 | 70.4 |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log` | c9296bf | 2026-09-26 12:12:25 +0700 | fix/audit-round2 | CÓ | dict_keepz, run_keepz_seed43 | 4126.4 | 68.7 |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log` | c65032a | 2026-09-26 12:28:57 +0700 | fix/audit-round2 | CÓ | dict_keepz_360, run_keepz_360, run_keepz_notrim | 6573.6 | 109.4 |
| `reports/unified_run_2026-09-25/vsl-train-unified.log` | b4916b9 | 2026-09-25 16:07:58 +0700 | fix/audit-round2 | CÓ | run, run_seed43 | 6558.0 | 109.2 |

Tổng thời lượng các kernel: 21487.2 s (5.97 giờ).

Diff mã giữa các commit kernel (`git diff --numstat`, src/data/harmonized.py, scripts/train_unified.py, scripts/shortcut_85.py, scripts/source_diagnostics.py):

- b4916b9 → c8a7bdf: `117	0	scripts/shortcut_85.py`; `163	0	scripts/source_diagnostics.py`; `49	6	scripts/train_unified.py`; `183	0	src/data/harmonized.py`
- c8a7bdf → c9296bf: `23	2	scripts/shortcut_85.py`
- c9296bf → c65032a: `5	3	scripts/train_unified.py`; `2	1	src/data/harmonized.py`
- c65032a → HEAD (f4729ff): `4	1	scripts/shortcut_85.py`

### 1.3 JSON bộ phân loại nguồn

| JSON | command | git_commit |
|---|---|---|
| `reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json` | `python scripts/shortcut_85.py --out reports/step4_2026-09-26/provenance_rerun/4a` | 27233f6 |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | `python scripts/shortcut_85.py --skip-eval --features harmonized --hand-z keep --qipedc-kps-dir qipedc_kps --out reports/step4_2026-09-26/provenance_rerun/4b` | 27233f6 |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | `python scripts/shortcut_85.py --skip-eval --features harmonized --hand-z drop --qipedc-kps-dir qipedc_kps --out reports/step4_2026-09-26/provenance_rerun/4b` | 27233f6 |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json` | `python scripts/shortcut_85.py --skip-eval --features harmonized --hand-z keep --qipedc-kps-dir qipedc_kps360 --out reports/step4_2026-09-26/4b` | 4bb3811 |

So khớp JSON cũ (không provenance) với bản chạy lại:

| JSON cũ | commit thêm file | command / git_commit bản cũ | Bản chạy lại | chạy lại trùng | Trường khác | Trường chỉ có ở bản chạy lại |
|---|---|---|---|---|---|---|
| `reports/step4_2026-09-26/4a/shortcut_85.json` | c8a7bdf 2026-09-26 10:58:44 +0700 | KHÔNG CÓ / KHÔNG CÓ | `reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json` (27233f6) | CÓ | — | command, features, git_commit, hand_z, qipedc_kps_dir |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | 5c1d080 2026-09-26 11:00:52 +0700 | KHÔNG CÓ / KHÔNG CÓ | `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` (27233f6) | CÓ | — | command, git_commit |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | 5c1d080 2026-09-26 11:00:52 +0700 | KHÔNG CÓ / KHÔNG CÓ | `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` (27233f6) | CÓ | — | command, git_commit |

Bản cũ không ghi `--ckpt`/`--seed`; bản chạy lại dùng mặc định của scripts/shortcut_85.py (`--ckpt checkpoints/stgcn_unified_best.pt`, `--seed 0`) — giả định là bản cũ cũng vậy.

### 1.4 File đầu vào (sha256)

| File | Vai trò | sha256 |
|---|---|---|
| `checkpoints/stgcn_tier2_indomain.pt` | checkpoint mặc định của backend (chỉ sha256) | `53c34cba43854c3e9820495bba3f93ffe18b5e1cb87ef44278a188ccafe2c826` |
| `checkpoints/stgcn_unified_best.pt` | model hiện tại của 4a (chỉ sha256) | `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb` |
| `data/processed/vslgh_segments/segments.csv` | VSL-GH segments (chồng lấn câu S06) | `bc4606cc06bdfb69ed2d40d88c7f5e13c43ad9284555a13b2d5378fabd445f15` |
| `data/splits/unified/test.csv` | manifest test | `96844753b167ec2b94278ab945e051365e0a67e2ea6aba33702f42ffe4768b8a` |
| `data/splits/unified/train.csv` | manifest train | `23b5de7a66bc6686f7efa45433b66ec186426e3780b44f26977938811f373007` |
| `data/splits/unified/val.csv` | manifest val | `22ea2db2644c7dfc57a6eb4deb1986f6c757ce3b870bf6e9ad81949fda84f156` |
| `reports/step4_2026-09-26/4a/shortcut_85.json` | JSON cũ (không provenance) | `288913a6e3658ae67cef6d75069a51b4074fed81de0377cea3093920cb56babe` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | JSON cũ (không provenance) | `333dd8f1f75e72e24c4d1b1a5f402ff5c3e9a60084fab17578188c3c6b5c5983` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | JSON cũ (không provenance) | `37e25c05f5546d11cd155e90716f2859f3810b44d65166046a701d94be526931` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json` | 4b source classifier | `334b1fa82bd1ca7f62a1159f10a1493be871de3d8e5ccaf06e9d4a82fde78d0c` |
| `reports/step4_2026-09-26/PREREGISTRATION.md` | preregistration | `2da6e8e5f172dde63090b1004b973e5041a18adb7397aacc93b65fc45172b793` |
| `reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json` | 4a source classifier + cross-source (provenance); JSON chạy lại | `76a12be4393c08feaf6ec2ce4474188fc75210418078515d7f1b2971179720e0` |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | 4b source classifier; JSON chạy lại | `31aa8caf4de0f65a1af466d9e009f427340a8edc08b686db293146fcd0414393` |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | 4b source classifier; JSON chạy lại | `4f3fcf51210dafdeffaa8b8047950b1c2bce5e120508521465610b539ecdc7cd` |
| `reports/step4_2026-09-26/runs/dict_keepz/metrics.json` | metrics.json dict_keepz | `d6f0c01f7de8aaa69e115da0d046e12f213b3fd262eedd8e3fe764f8c8631b2c` |
| `reports/step4_2026-09-26/runs/dict_keepz/stgcn_unified_best.pt` | stgcn_unified_best.pt dict_keepz | `62cb7f2006b22f99d64ddac1bef6164a7592e072cf470fc1b482ad6429435cc0` |
| `reports/step4_2026-09-26/runs/dict_keepz/test_logits.npz` | test_logits.npz dict_keepz | `1c8213657b42a4eb6f08e8e54b59ebbbf590fefa820f703a8502f29268aef397` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/metrics.json` | metrics.json dict_keepz_360 | `21f9c9d1ff23c1f17464669097f7e28eb49c912c162e3c52325a7c773b2da82d` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/stgcn_unified_best.pt` | stgcn_unified_best.pt dict_keepz_360 | `1fc9031d127701146efe3a852f410d4bdefbf49264193a899659c6c3d52f54a7` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/test_logits.npz` | test_logits.npz dict_keepz_360 | `013c15075763ec118cff134b1e681ac81b686027af77df0f355f694328b6ba9f` |
| `reports/step4_2026-09-26/runs/run_dropz/metrics.json` | metrics.json H-dropz | `b9199034227a316cf05cc53098c832565ca27c223c9671750b4603695570e903` |
| `reports/step4_2026-09-26/runs/run_dropz/stgcn_unified_best.pt` | stgcn_unified_best.pt H-dropz | `1dd35425dbc9a6f704ffc88fc9644bb753637b1749126ad3b47a28d5744b3924` |
| `reports/step4_2026-09-26/runs/run_dropz/test_logits.npz` | test_logits.npz H-dropz | `4936a0cb33ec842d229f052c2bae967feaf591fc16f4a50cd124d3d93f8c8d0f` |
| `reports/step4_2026-09-26/runs/run_keepz/metrics.json` | metrics.json H-keepz | `fa175406149af0489c36c4ea4ef41d13abba683bbaff4571ef3cb79123aaaa57` |
| `reports/step4_2026-09-26/runs/run_keepz/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz | `db1909493312bccb2bf7271ce375f01ff09c6b1cbb5b7ac442dc6246f357a92d` |
| `reports/step4_2026-09-26/runs/run_keepz/test_logits.npz` | test_logits.npz H-keepz | `f66f20fef3875b7225d44f879c521f781557c810b8de8c51e0f68ce1d32b57ed` |
| `reports/step4_2026-09-26/runs/run_keepz_360/metrics.json` | metrics.json H-keepz-360 | `a573daa651ad28d2c6f561276c322415a30cc91a2320e568825161650cd98de1` |
| `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-360 | `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e` |
| `reports/step4_2026-09-26/runs/run_keepz_360/test_logits.npz` | test_logits.npz H-keepz-360 | `0a560a6d3810f0578384d0fb110ebd728004881dd087ea2fe101f2ac4ea88bfe` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/metrics.json` | metrics.json H-keepz-notrim | `12e63883049126fa46d2fc56374f6068e6dd0958cb30d6588a019409d5a78590` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-notrim | `92e603e19300e228ac220da8f1a07dae94e18a72bd105859f53de0c4b82e2df9` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/test_logits.npz` | test_logits.npz H-keepz-notrim | `a04cadca374457e787f4b9b2e056ae02577ad9ca7409cca0251a49fab1405eb9` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/metrics.json` | metrics.json H-keepz-seed43 | `2bd99e0bd0af07c49f41f937914d7c4fd9ab22a7e323796a262d2fc46760a50b` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-seed43 | `f8f28f05170551a65b700b947e54fa5b96d348565aeaf4fabc41a35772acbd98` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/test_logits.npz` | test_logits.npz H-keepz-seed43 | `bb2bf6b7f495c9a6d95daa952e794e6bc376095257e63371ae18748259f8dab1` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized.log` | kernel log | `cc9a75afdc0f60802c2065acd7fb6fae281f8651c4240d56e66bf5cb0eb25b85` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log` | kernel log | `f0dc938d16da2e4fa63ae768511b66cdb9ded491735278a92ca06f1aaf7359a0` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log` | kernel log | `d8b011c40f6dde10435f0d7c244cb35aba63c1e3d4655f967498f5dabb06cad8` |
| `reports/unified_run_2026-09-25/run/metrics.json` | metrics.json baseline | `2fa2daadc5ba0558323e401b374fe083741f9c81cecf1c11d1203438cd62cd16` |
| `reports/unified_run_2026-09-25/run/stgcn_unified_best.pt` | stgcn_unified_best.pt baseline | `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb` |
| `reports/unified_run_2026-09-25/run/test_logits.npz` | test_logits.npz baseline | `cded2935ed711382b759cfb377de4dade06856d797b7a98838968f5a7d5dacf3` |
| `reports/unified_run_2026-09-25/run_seed43/metrics.json` | metrics.json baseline-seed43 | `9c203a0df80fd13bf49190c254ffe59cda51fbcd41f45eb2c9e3e044d39e78c2` |
| `reports/unified_run_2026-09-25/run_seed43/stgcn_unified_best.pt` | stgcn_unified_best.pt baseline-seed43 | `a8f0dc6f7df597fe9bacfedadd846e8eabeada164e3a279bcc82c6b242279871` |
| `reports/unified_run_2026-09-25/run_seed43/test_logits.npz` | test_logits.npz baseline-seed43 | `b4d5acf5118fada4d65673acca706d7c8c42ee76a1204d942f43f63528cc0cdd` |
| `reports/unified_run_2026-09-25/vsl-train-unified.log` | kernel log | `14c1b59af71cd8dcbd9f5d9157d1a1c729ac38f44029e9d427f27d33d39a3422` |

## 2. Bước 4a — kiểm tra lối tắt trên các lớp có ở cả hai nguồn

Nguồn số: `reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json` (command: `python scripts/shortcut_85.py --out reports/step4_2026-09-26/provenance_rerun/4a`; git_commit: 27233f6).

Lớp chung: 85; tập cân bằng {"qipedc": 106, "vslgh": 106}; ngẫu nhiên 50.0%.

| Đặc trưng | Bộ phân loại nguồn (balanced acc., %) |
|---|---|
| all | **99.5** |
| chỉ time | 98.1 |
| chỉ presence | 70.3 |
| chỉ pose_xy | 99.1 |
| chỉ pose_z | 99.5 |
| chỉ hand_xy | 97.2 |
| chỉ hand_z | 82.5 |
| chỉ hand_shape | 95.3 |

Model hiện tại = `checkpoints/stgcn_unified_best.pt` (sha256 `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb`); baseline trong báo cáo = `reports/unified_run_2026-09-25/run/stgcn_unified_best.pt` (sha256 `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb`): cùng checkpoint: CÓ.

Đánh giá chéo nguồn của model hiện tại trên 81 lớp chung (loại vì ký khác: kết quả, thường xuyên, xem, yếu); k suy ra duy nhất từ % làm tròn và n trong JSON:

| Tập | n | Top-1 | Top-5 |
|---|---|---|---|
| QIPEDC TEST (clip chưa thấy) | 26 | 0.0% (0/26) [0.0, 12.9] | 19.2% (5/26) [8.5, 37.9] |
| QIPEDC VAL+TEST | 26 | 0.0% (0/26) [0.0, 12.9] | 19.2% (5/26) [8.5, 37.9] |
| S06 cùng lớp (tham chiếu cùng nguồn) | 202 | 58.4% (118/202) [51.5, 65.0] | 88.1% (178/202) [82.9, 91.9] |

Kiểm tra chéo với logits TEST của baseline (cùng checkpoint), cột chéo nguồn mục 3.3: trùng: CÓ (JSON k1/n/k5 = [0, 26, 5]; logits = [0, 26, 5]).

## 3. Bước 4b — đầu vào hài hòa, train lại

### 3.1 Cấu hình hài hòa (sinh từ mã)

Nguồn: checkpoint reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt -> preprocessing; src/data/harmonized.py (HARMONIZED_DEFAULT, docstring).

- Khớp giữ / bỏ, ngón cái 21/22: `arms(11-16)+hands(25-66); face, pose hand points 17-22 (thumbs 21/22), hips masked` — arms (MediaPipe pose 11-16: shoulders, elbows, wrists) + both hands (25-66). Face (0-10), the pose hand points 17-22 (incl. thumbs 21/22, which came from different models per source; the hand-model thumb is kept as part of the hand) and hips (23-24) are masked out. The 67-joint layout is kept so the ST-GCN graph and checkpoints stay compatible; dropped joints have mask 0 and coordinates 0.
- Tọa độ: aspect-corrected, centred on the mid-shoulder of each frame, scaled by the clip's median shoulder width. Pose z is dropped (set to 0); hand z is kept or dropped by config.
- pose z: bỏ (`pose_z=False`); hand z: giữ (`hand_z=True`)
- Cắt đoạn nghỉ: `trim=True`, `rest_y=1.2`, `active_speed=1.0`, `pad_s=0.1`, `mask_resting_hand=True`
- Resample theo thời gian: the rest before/after the sign is trimmed with one motion/position rule, then the active span is resampled uniformly IN TIME (from fps or timestamps) to a fixed number of frames. Short hand gaps are bridged by linear interpolation; longer gaps stay masked. `target_len=32`, `max_gap_s=0.25`
- Độ phân giải trích xuất: `process_height=360`; extractor `CleanHolisticExtractor` MediaPipe `0.10.14`
- Augmentation: Augmentation (training only): scale, rotation, speed warp 0.7-1.3, random temporal crop.
- TTA: không (TEST đánh giá một lần, không TTA: scripts/train_unified.py predict_all một lượt)
- Khác `HARMONIZED_DEFAULT`: `{"process_height": {"default": null, "chosen": 360}}`

### 3.2 Chọn trên VAL (balanced VAL = trung bình VAL top-1 VSL-GH S05 và QIPEDC)

| Run | Vai trò | VAL VSL-GH top-1 | VAL QIPEDC top-1 | Balanced VAL | Epoch tốt nhất (VAL tổng) |
|---|---|---|---|---|---|
| baseline | baseline | n/a | n/a | n/a (không có val_by_source) | 46 |
| H-keepz | ứng viên (gốc) | 75.0% (892/1190) [72.4, 77.3] | 17.1% (18/105) [11.1, 25.5] | **46.05** | 61 |
| H-dropz | ứng viên (gốc) | 73.2% (871/1190) [70.6, 75.6] | 14.3% (15/105) [8.9, 22.2] | **43.74** | 58 |
| H-keepz-360 | ứng viên (360 px) | 75.5% (899/1190) [73.0, 77.9] | 20.0% (21/105) [13.5, 28.6] | **47.77** | 78 |
| H-keepz-seed43 | phụ (không phải ứng viên) | 77.2% (919/1190) [74.8, 79.5] | 18.1% (19/105) [11.9, 26.5] | **47.66** | 103 |
| H-keepz-notrim | phụ (không phải ứng viên) | 76.5% (910/1190) [74.0, 78.8] | 16.2% (17/105) [10.4, 24.4] | **46.33** | 90 |
| baseline-seed43 | phụ (không phải ứng viên) | n/a | n/a | n/a (không có val_by_source) | 51 |
| dict_keepz_360 | từ điển (4c) | n/a | 3.8% (4/105) [1.5, 9.4] | n/a (không có val_by_source) | 28 |

Giá trị balanced VAL của 1 clip QIPEDC VAL = 100/(2·105) = 0.476 điểm; ngưỡng 0.5 điểm. Cờ "sát ngưỡng" khi |chênh − 0.5| < giá trị đó.

- Chọn z (độ phân giải gốc): H-keepz − H-dropz = +2.31 điểm → **H-keepz**.
- 360 px: H-keepz-360 − H-keepz = +1.72 điểm → chọn 360 px.
- Tham khảo, KHÔNG dùng để chọn: chênh balanced VAL seed 42 → 43 (H-keepz → H-keepz-seed43) = +1.61 điểm.

**Run được chọn theo luật: H-keepz-360** (`{"trim": true, "features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": 360, "seed": 42}`).

### 3.3 TEST — 4 nhóm (top-1 và top-5: % (k/n) [Wilson 95%])

| Run | Nhóm | Top-1 | Top-5 |
|---|---|---|---|
| baseline | S06 (người ký chưa thấy) | 70.6% (839/1189) [67.9, 73.1] | 90.9% (1081/1189) [89.1, 92.4] |
| baseline | QIPEDC-only (≥ 2 bản quay) | 9.8% (68/691) [7.8, 12.3] | 21.7% (150/691) [18.8, 24.9] |
| baseline | Tổng | 47.5% (907/1911) [45.2, 49.7] | 64.7% (1236/1911) [62.5, 66.8] |
| baseline | Chéo nguồn (lớp chung − 4 từ) | 0.0% (0/26) [0.0, 12.9] | 19.2% (5/26) [8.5, 37.9] |
| H-keepz | S06 (người ký chưa thấy) | 78.7% (936/1189) [76.3, 81.0] | 94.7% (1126/1189) [93.3, 95.8] |
| H-keepz | QIPEDC-only (≥ 2 bản quay) | 13.0% (90/691) [10.7, 15.7] | 25.2% (174/691) [22.1, 28.5] |
| H-keepz | Tổng | 53.9% (1030/1911) [51.7, 56.1] | 68.6% (1311/1911) [66.5, 70.6] |
| H-keepz | Chéo nguồn (lớp chung − 4 từ) | 11.5% (3/26) [4.0, 29.0] | 38.5% (10/26) [22.4, 57.5] |
| H-dropz | S06 (người ký chưa thấy) | 76.0% (904/1189) [73.5, 78.4] | 93.2% (1108/1189) [91.6, 94.5] |
| H-dropz | QIPEDC-only (≥ 2 bản quay) | 11.6% (80/691) [9.4, 14.2] | 23.3% (161/691) [20.3, 26.6] |
| H-dropz | Tổng | 51.6% (987/1911) [49.4, 53.9] | 66.8% (1277/1911) [64.7, 68.9] |
| H-dropz | Chéo nguồn (lớp chung − 4 từ) | 11.5% (3/26) [4.0, 29.0] | 26.9% (7/26) [13.7, 46.1] |
| H-keepz-360 | S06 (người ký chưa thấy) | 81.1% (964/1189) [78.8, 83.2] | 95.8% (1139/1189) [94.5, 96.8] |
| H-keepz-360 | QIPEDC-only (≥ 2 bản quay) | 12.0% (83/691) [9.8, 14.6] | 25.3% (175/691) [22.2, 28.7] |
| H-keepz-360 | Tổng | 55.0% (1052/1911) [52.8, 57.3] | 69.3% (1324/1911) [67.2, 71.3] |
| H-keepz-360 | Chéo nguồn (lớp chung − 4 từ) | 15.4% (4/26) [6.1, 33.5] | 34.6% (9/26) [19.4, 53.8] |
| H-keepz-seed43 (không phải ứng viên) | S06 (người ký chưa thấy) | 80.7% (959/1189) [78.3, 82.8] | 95.5% (1135/1189) [94.1, 96.5] |
| H-keepz-seed43 (không phải ứng viên) | QIPEDC-only (≥ 2 bản quay) | 12.6% (87/691) [10.3, 15.3] | 26.0% (180/691) [22.9, 29.4] |
| H-keepz-seed43 (không phải ứng viên) | Tổng | 55.0% (1051/1911) [52.8, 57.2] | 69.2% (1322/1911) [67.1, 71.2] |
| H-keepz-seed43 (không phải ứng viên) | Chéo nguồn (lớp chung − 4 từ) | 15.4% (4/26) [6.1, 33.5] | 23.1% (6/26) [11.0, 42.1] |
| H-keepz-notrim (không phải ứng viên) | S06 (người ký chưa thấy) | 79.1% (940/1189) [76.7, 81.3] | 95.6% (1137/1189) [94.3, 96.6] |
| H-keepz-notrim (không phải ứng viên) | QIPEDC-only (≥ 2 bản quay) | 11.6% (80/691) [9.4, 14.2] | 24.5% (169/691) [21.4, 27.8] |
| H-keepz-notrim (không phải ứng viên) | Tổng | 53.4% (1021/1911) [51.2, 55.7] | 68.5% (1309/1911) [66.4, 70.5] |
| H-keepz-notrim (không phải ứng viên) | Chéo nguồn (lớp chung − 4 từ) | 0.0% (0/26) [0.0, 12.9] | 7.7% (2/26) [2.1, 24.1] |
| baseline-seed43 (không phải ứng viên) | S06 (người ký chưa thấy) | 71.7% (853/1189) [69.1, 74.2] | 90.7% (1079/1189) [89.0, 92.3] |
| baseline-seed43 (không phải ứng viên) | QIPEDC-only (≥ 2 bản quay) | 10.0% (69/691) [8.0, 12.4] | 20.8% (144/691) [18.0, 24.0] |
| baseline-seed43 (không phải ứng viên) | Tổng | 48.4% (925/1911) [46.2, 50.6] | 64.4% (1230/1911) [62.2, 66.5] |
| baseline-seed43 (không phải ứng viên) | Chéo nguồn (lớp chung − 4 từ) | 11.5% (3/26) [4.0, 29.0] | 26.9% (7/26) [13.7, 46.1] |

Clip QIPEDC-only bị loại vì lớp có < 2 bản quay: 0.

Kiểm tra hòa điểm: `test_logits.npz` lưu float16 nên lớp đúng có thể hòa điểm với lớp khác. Báo cáo dùng sắp xếp ổn định (hòa → lớp có chỉ số nhỏ hơn đứng trước). Số clip đúng trên toàn TEST của mỗi run: k dùng [bi quan – lạc quan] / n, và k từ `metrics.json → test_overall` (tính trong kernel trên logits float32):

| Run | Top-1: dùng [bi quan – lạc quan] | Top-1 metrics.json | Top-5: dùng [bi quan – lạc quan] | Top-5 metrics.json | Top-10: dùng [bi quan – lạc quan] |
|---|---|---|---|---|---|
| baseline | 907 [907 – 907] / 1911 | 907 | 1236 [1236 – 1236] / 1911 | 1236 | 1327 [1327 – 1327] / 1911 |
| H-keepz | 1030 [1030 – 1030] / 1911 | 1030 | 1311 [1310 – 1311] / 1911 | 1311 | 1377 [1377 – 1377] / 1911 |
| H-dropz | 987 [986 – 988] / 1911 | 987 | 1277 [1277 – 1278] / 1911 | 1277 | 1364 [1363 – 1364] / 1911 |
| H-keepz-360 | 1052 [1052 – 1052] / 1911 | 1052 | 1324 [1323 – 1324] / 1911 | 1324 | 1386 [1385 – 1387] / 1911 |
| H-keepz-seed43 | 1051 [1051 – 1051] / 1911 | 1051 | 1322 [1321 – 1322] / 1911 | 1321 | 1394 [1394 – 1394] / 1911 |
| H-keepz-notrim | 1021 [1021 – 1021] / 1911 | 1021 | 1309 [1309 – 1309] / 1911 | 1309 | 1376 [1376 – 1376] / 1911 |
| baseline-seed43 | 925 [925 – 925] / 1911 | 925 | 1230 [1230 – 1230] / 1911 | 1230 | 1325 [1325 – 1325] / 1911 |
| dict_keepz_360 | 23 [23 – 23] / 721 | 23 | 70 [70 – 70] / 721 | 70 | 96 [96 – 96] / 721 |

### 3.4 Kết luận cắt đoạn nghỉ

(i) Luật VAL (PREREGISTRATION phần bổ sung): H-keepz (cắt) − H-keepz-notrim (không cắt) = -0.28 điểm balanced VAL → cắt đoạn nghỉ KHÔNG được công nhận (ngưỡng 0.5).

(ii) TEST cả hai run (H-keepz cắt vs H-keepz-notrim không cắt; McNemar chính xác top-1 chỉ để mô tả, không đăng ký trước):

| Nhóm | Cắt: top-1 | Không cắt: top-1 | Chênh (điểm / clip) | McNemar n10 / n01 / p |
|---|---|---|---|---|
| S06 (người ký chưa thấy) | 78.7% (936/1189) [76.3, 81.0] | 79.1% (940/1189) [76.7, 81.3] | -0.3 / -4 | 71 / 75 / 0.804 |
| QIPEDC-only (≥ 2 bản quay) | 13.0% (90/691) [10.7, 15.7] | 11.6% (80/691) [9.4, 14.2] | +1.4 / +10 | 34 / 24 / 0.237 |
| Tổng | 53.9% (1030/1911) [51.7, 56.1] | 53.4% (1021/1911) [51.2, 55.7] | +0.5 / +9 | 108 / 99 / 0.578 |
| Chéo nguồn (lớp chung − 4 từ) | 11.5% (3/26) [4.0, 29.0] | 0.0% (0/26) [0.0, 12.9] | +11.5 / +3 | 3 / 0 / 0.25 |

(iii) Run được chọn (H-keepz-360, process_height=360) vs baseline cũ (đầu vào cũ, không cắt nghỉ) trên cùng nhóm — khác nhau đồng thời ở hài hòa, cắt nghỉ và độ phân giải, nên chênh lệch KHÔNG quy riêng cho cắt nghỉ:

| Nhóm | Được chọn: top-1 | Baseline: top-1 | Chênh (điểm / clip) | McNemar n10 / n01 / p |
|---|---|---|---|---|
| S06 (người ký chưa thấy) | 81.1% (964/1189) [78.8, 83.2] | 70.6% (839/1189) [67.9, 73.1] | +10.5 / +125 | 183 / 58 / 2.83e-16 |
| QIPEDC-only (≥ 2 bản quay) | 12.0% (83/691) [9.8, 14.6] | 9.8% (68/691) [7.8, 12.3] | +2.2 / +15 | 46 / 31 / 0.11 |
| Tổng | 55.0% (1052/1911) [52.8, 57.3] | 47.5% (907/1911) [45.2, 49.7] | +7.6 / +145 | 234 / 89 / 3.54e-16 |
| Chéo nguồn (lớp chung − 4 từ) | 15.4% (4/26) [6.1, 33.5] | 0.0% (0/26) [0.0, 12.9] | +15.4 / +4 | 4 / 0 / 0.125 |

**Kết luận:** ablation cắt nghỉ chạy ở độ phân giải gốc. Theo luật VAL đăng ký trước, cắt đoạn nghỉ KHÔNG được công nhận là có ích; bảng (ii) chỉ để mô tả. So sánh (iii) với baseline cũ đo tác động gộp của cả gói hài hòa, không riêng cắt nghỉ.

### 3.5 Dao động seed

Chênh = seed sau − seed trước; theo điểm % và theo số clip đúng (k). Không dùng để chọn.

| Cặp | Nhóm | Top-1: seed trước → sau | Chênh top-1 (điểm / clip) | Top-5: seed trước → sau | Chênh top-5 (điểm / clip) |
|---|---|---|---|---|---|
| baseline (seed 42) → baseline-seed43 (seed 43) | S06 (người ký chưa thấy) | 70.6% (839/1189) [67.9, 73.1] → 71.7% (853/1189) [69.1, 74.2] | +1.2 / +14 | 90.9% (1081/1189) [89.1, 92.4] → 90.7% (1079/1189) [89.0, 92.3] | -0.2 / -2 |
| baseline (seed 42) → baseline-seed43 (seed 43) | QIPEDC-only (≥ 2 bản quay) | 9.8% (68/691) [7.8, 12.3] → 10.0% (69/691) [8.0, 12.4] | +0.1 / +1 | 21.7% (150/691) [18.8, 24.9] → 20.8% (144/691) [18.0, 24.0] | -0.9 / -6 |
| baseline (seed 42) → baseline-seed43 (seed 43) | Tổng | 47.5% (907/1911) [45.2, 49.7] → 48.4% (925/1911) [46.2, 50.6] | +0.9 / +18 | 64.7% (1236/1911) [62.5, 66.8] → 64.4% (1230/1911) [62.2, 66.5] | -0.3 / -6 |
| baseline (seed 42) → baseline-seed43 (seed 43) | Chéo nguồn (lớp chung − 4 từ) | 0.0% (0/26) [0.0, 12.9] → 11.5% (3/26) [4.0, 29.0] | +11.5 / +3 | 19.2% (5/26) [8.5, 37.9] → 26.9% (7/26) [13.7, 46.1] | +7.7 / +2 |
| H-keepz (seed 42) → H-keepz-seed43 (seed 43) | S06 (người ký chưa thấy) | 78.7% (936/1189) [76.3, 81.0] → 80.7% (959/1189) [78.3, 82.8] | +1.9 / +23 | 94.7% (1126/1189) [93.3, 95.8] → 95.5% (1135/1189) [94.1, 96.5] | +0.8 / +9 |
| H-keepz (seed 42) → H-keepz-seed43 (seed 43) | QIPEDC-only (≥ 2 bản quay) | 13.0% (90/691) [10.7, 15.7] → 12.6% (87/691) [10.3, 15.3] | -0.4 / -3 | 25.2% (174/691) [22.1, 28.5] → 26.0% (180/691) [22.9, 29.4] | +0.9 / +6 |
| H-keepz (seed 42) → H-keepz-seed43 (seed 43) | Tổng | 53.9% (1030/1911) [51.7, 56.1] → 55.0% (1051/1911) [52.8, 57.2] | +1.1 / +21 | 68.6% (1311/1911) [66.5, 70.6] → 69.2% (1322/1911) [67.1, 71.2] | +0.6 / +11 |
| H-keepz (seed 42) → H-keepz-seed43 (seed 43) | Chéo nguồn (lớp chung − 4 từ) | 11.5% (3/26) [4.0, 29.0] → 15.4% (4/26) [6.1, 33.5] | +3.8 / +1 | 38.5% (10/26) [22.4, 57.5] → 23.1% (6/26) [11.0, 42.1] | -15.4 / -4 |

### 3.6 Bộ phân loại nguồn trên đầu vào hài hòa (tập cân bằng của 4a)

| JSON | hand z | keypoint QIPEDC | git_commit | all | time | presence | pose_xy | pose_z | hand_xy | hand_z | hand_shape |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | keep | qipedc_kps | 27233f6 | 92.0 | 50.0 | 70.8 | 94.8 | 50.0 | 94.8 | 79.2 | 86.8 |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | drop | qipedc_kps | 27233f6 | 94.3 | 50.0 | 70.8 | 94.8 | 50.0 | 94.8 | 50.0 | 85.8 |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json` | keep | qipedc_kps360 | 4bb3811 | 94.8 | 50.0 | 70.3 | 95.3 | 50.0 | 95.3 | 77.4 | 85.8 |

## 4. Bước 4c — model từ điển (chỉ QIPEDC) vs model gộp được chọn, cùng clip QIPEDC TEST

- Run từ điển dùng: **dict_keepz_360** (`{"trim": true, "features": "harmonized", "hand_z": "keep", "sources": "qipedc", "process_height": 360, "seed": 42}`); model gộp: **H-keepz-360** (`{"trim": true, "features": "harmonized", "hand_z": "keep", "sources": "all", "process_height": 360, "seed": 42}`). Cấu hình trùng mọi khóa trừ `sources`.
- Run từ điển còn lại: dict_keepz — không khớp cách hài hòa đã chọn; không báo theo PREREGISTRATION.md dòng 23 (không in số).

| Model | Số lớp | Lớp có dữ liệu train | Clip train | Lớp có ≤ 2 clip train | Hist (clip/lớp: số lớp) |
|---|---|---|---|---|---|
| từ điển | 594 | 594 | 795 | 593 | `{"1": 394, "2": 199, "3": 1}` |
| gộp | 876 | 876 | 15138 | 509 | `{"1": 319, "2": 190, "3": 1, "11": 5, "12": 179, "13": 32, "14": 3, "22": 1, "23": 2, "24": 33, "25": 18, "26": 3, "27": 1, "34": 1, "36": 16, "37": 11, "38": 2, "48": 10, "49": 3, "56": 1, "59": 1, "60": 6, "61": 2, "71": 1, "72": 6, "84": 4, "85": 1, "95": 1, "96": 2, "97": 1, "107": 1, "109": 1, "121": 1, "122": 1, "131": 1, "132": 1, "133": 1, "134": 1, "144": 1, "156": 1, "168": 1, "180": 1, "195": 1, "203": 1, "224": 1, "239": 1, "300": 1, "301": 1, "312": 1, "3324": 1}` |

Clip chung (QIPEDC TEST có lớp thuộc cả hai không gian nhãn): 721 (dòng TEST của model từ điển 721; dòng QIPEDC TEST của model gộp 722).

**Kết quả chính (đã đăng ký trước)** — % (k/n) [Wilson 95%]:

| Model | Top-1 | Top-5 | Top-10 |
|---|---|---|---|
| từ điển (dict_keepz_360) | 3.2% (23/721) [2.1, 4.7] | 9.7% (70/721) [7.8, 12.1] | 13.3% (96/721) [11.0, 16.0] |
| gộp (H-keepz-360) | 12.2% (88/721) [10.0, 14.8] | 25.7% (185/721) [22.6, 29.0] | 32.0% (231/721) [28.7, 35.5] |

McNemar chính xác top-1: từ điển đúng & gộp sai n10 = 7, ngược lại n01 = 72, p = 1.06e-14.

**Phân tích thăm dò — không đăng ký trước, không dùng để chọn:**

(a) Model gộp với logits giới hạn về đúng không gian nhãn của model từ điển, cùng clip:

| Model | Top-1 | Top-5 | Top-10 |
|---|---|---|---|
| gộp, giới hạn nhãn | 12.8% (92/721) [10.5, 15.4] | 26.9% (194/721) [23.8, 30.3] | 34.3% (247/721) [30.9, 37.8] |

McNemar top-1 (từ điển vs gộp giới hạn): n10 = 7, n01 = 76, p = 9.43e-16.

(b) Dự đoán top-1 của model gộp rơi vào lớp chỉ-VSL-GH (282 lớp có train VSL-GH, không có train QIPEDC) vs lớp có train QIPEDC (594 lớp):

| Tập clip | Lớp chỉ-VSL-GH | Lớp có QIPEDC | Lớp không có train |
|---|---|---|---|
| mọi clip QIPEDC TEST | 9.6% (69/722) [7.6, 11.9] | 90.4% (653/722) [88.1, 92.4] | 0.0% (0/722) [0.0, 0.5] |
| clip chung của 4c | 9.6% (69/721) [7.6, 11.9] | 90.4% (652/721) [88.1, 92.4] | 0.0% (0/721) [0.0, 0.5] |
| S06 (đối chứng) | 81.8% (973/1189) [79.5, 83.9] | 18.2% (216/1189) [16.1, 20.5] | 0.0% (0/1189) [0.0, 0.3] |

Chỉ là chỉ báo cho giả thuyết "model gộp học phân biệt nguồn", không phải kiểm định.

## 5. Giới hạn

- Cỡ mẫu TEST của run được chọn: S06 (người ký chưa thấy) n=1189; QIPEDC-only (≥ 2 bản quay) n=691; Tổng n=1911; Chéo nguồn (lớp chung − 4 từ) n=26. Chéo nguồn: 15.4% (4/26) [6.1, 33.5] — CI rất rộng. Clip QIPEDC-only bị loại vì < 2 bản quay: 0.
- Wilson CI giả định các clip độc lập; clip cùng lớp / cùng bản quay / cùng người ký tương quan nên CI thật rộng hơn.
- Ít mẫu mỗi lớp: model gộp 509 lớp có ≤ 2 clip train; model từ điển 593/594 lớp có ≤ 2 clip train (795 clip train).
- Số seed cùng cấu hình: H-keepz-360: 1; dict_keepz_360: 1 (1 = một seed duy nhất; so sánh 360 px và 4c dựa trên một seed).
- QIPEDC không có nhãn người ký: dòng QIPEDC có signer_id 0.0% (0/1622) [0.0, 0.2]; không split được theo người ký.
- S06 đo người ký mới, không đo câu mới: đoạn S06 đến từ câu mà người ký train cũng ký: 100.0% (1189/1189) [99.7, 100.0].
- Đường live chưa dùng `harmonize()`: file trong backend/ và src/inference/ gọi harmonize: không có.
- Độ phân giải của run được chọn: process_height=360. Nếu giữ lựa chọn này, đường realtime (webcam 640×480) phải giảm về cùng chiều cao trước MediaPipe và có test tương đương train–realtime — việc SAU khi người dùng duyệt (PREREGISTRATION dòng 11–12).
- Phần bổ sung của PREREGISTRATION viết sau khi đã biết kết quả chọn z; commit của PREREGISTRATION: 9b0ade1 2026-09-26 12:13:24 +0700; c8a7bdf 2026-09-26 10:58:44 +0700 (so với cột "Sau lần sửa PREREG cuối" ở mục 1.1).
- Nguồn trong manifest: qipedc, vslgh — HCMUE không dùng để train hay đo.
- Model mặc định của backend: VSL_MODEL_TYPE mặc định `stgcn` → `checkpoints/stgcn_tier2_indomain.pt` (sha256 53c34cba43854c3e9820495bba3f93ffe18b5e1cb87ef44278a188ccafe2c826); trùng model được kiểm ở 4a: KHÔNG.
- Chọn epoch: epoch tốt nhất của mỗi run chọn theo VAL top-1 tổng (VSL-GH chiếm 1190/1295 clip VAL), còn biến thể chọn theo balanced VAL.
- `git_commit` trong JSON của scripts/shortcut_85.py chỉ là HEAD, không ghi trạng thái bẩn của mã.
- Logits, checkpoint và log kernel bị gitignore: clone sạch không tái tạo được báo cáo; sha256 ở mục 1.4 là bằng chứng thay thế.

## 6. Review

Chưa có kết quả vslt-reviewer (sinh lại với `--review-file`).
