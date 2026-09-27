# Báo cáo Bước 4a–4c (sinh bởi scripts/report_step4.py)

- Lệnh: `python scripts/report_step4.py --baseline reports/unified_run_2026-09-25/run --runs H-keepz=reports/step4_2026-09-26/runs/run_keepz H-dropz=reports/step4_2026-09-26/runs/run_dropz --run-360 H-keepz-360=reports/step4_2026-09-26/runs/run_keepz_360 --aux-runs H-keepz-seed43=reports/step4_2026-09-26/runs/run_keepz_seed43 H-keepz-notrim=reports/step4_2026-09-26/runs/run_keepz_notrim baseline-seed43=reports/unified_run_2026-09-25/run_seed43 --dict-run reports/step4_2026-09-26/runs/dict_keepz --dict-run-360 reports/step4_2026-09-26/runs/dict_keepz_360 --shortcut-4a reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json --shortcut-4b reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json --shortcut-legacy-compare reports/step4_2026-09-26/4a/shortcut_85.json=reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps.json=reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json reports/step4_2026-09-26/4b/shortcut_85_harmonized_dropz_qipedc_kps.json=reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json --kernel-logs reports/step4_2026-09-26/runs/vsl-train-harmonized.log reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log reports/unified_run_2026-09-25/vsl-train-unified.log --out reports/step4_2026-09-26/REPORT.md --json-out reports/step4_2026-09-26/step4_results.json --review-file docs/reviews/01-review.md --archive-manifest reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`
- HEAD: `514ad47`; code_dirty (scripts/, src/, tests/): false
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
- c65032a → HEAD (commit ở header / generated_by.git_commit): `4	1	scripts/shortcut_85.py`

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
| `docs/reviews/01-review.md` | review | `39a121aba7808e9d814e3dd060b54abad0dde4e6f112973540a4a841495eff27` |
| `reports/step4_2026-09-26/4a/shortcut_85.json` | JSON cũ (không provenance) | `288913a6e3658ae67cef6d75069a51b4074fed81de0377cea3093920cb56babe` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | JSON cũ (không provenance) | `333dd8f1f75e72e24c4d1b1a5f402ff5c3e9a60084fab17578188c3c6b5c5983` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | JSON cũ (không provenance) | `37e25c05f5546d11cd155e90716f2859f3810b44d65166046a701d94be526931` |
| `reports/step4_2026-09-26/4b/shortcut_85_harmonized_keepz_qipedc_kps360.json` | 4b source classifier | `334b1fa82bd1ca7f62a1159f10a1493be871de3d8e5ccaf06e9d4a82fde78d0c` |
| `reports/step4_2026-09-26/PREREGISTRATION.md` | preregistration | `2da6e8e5f172dde63090b1004b973e5041a18adb7397aacc93b65fc45172b793` |
| `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json` | archive manifest | `12c5ceb37ee8c70e16c53ca8679b34c8f3a931553cdb69e9c38fbe0f770df91f` |
| `reports/step4_2026-09-26/provenance_rerun/4a/shortcut_85.json` | 4a source classifier + cross-source (provenance); JSON chạy lại | `76a12be4393c08feaf6ec2ce4474188fc75210418078515d7f1b2971179720e0` |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_dropz_qipedc_kps.json` | 4b source classifier; JSON chạy lại | `31aa8caf4de0f65a1af466d9e009f427340a8edc08b686db293146fcd0414393` |
| `reports/step4_2026-09-26/provenance_rerun/4b/shortcut_85_harmonized_keepz_qipedc_kps.json` | 4b source classifier; JSON chạy lại | `4f3fcf51210dafdeffaa8b8047950b1c2bce5e120508521465610b539ecdc7cd` |
| `reports/step4_2026-09-26/runs/dict_keepz/history.json` | history.json dict_keepz | `159338d4de02e956410d1b2e1ad27effa0d02d0ab337662a52bd38ae44c885dc` |
| `reports/step4_2026-09-26/runs/dict_keepz/metrics.json` | metrics.json dict_keepz | `d6f0c01f7de8aaa69e115da0d046e12f213b3fd262eedd8e3fe764f8c8631b2c` |
| `reports/step4_2026-09-26/runs/dict_keepz/stgcn_unified_best.pt` | stgcn_unified_best.pt dict_keepz | `62cb7f2006b22f99d64ddac1bef6164a7592e072cf470fc1b482ad6429435cc0` |
| `reports/step4_2026-09-26/runs/dict_keepz/test_logits.npz` | test_logits.npz dict_keepz | `1c8213657b42a4eb6f08e8e54b59ebbbf590fefa820f703a8502f29268aef397` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/history.json` | history.json dict_keepz_360 | `0bfc024f26621ae1741d85c03f5bda0df7a85e98b76baab28ad04e0e8ece00b6` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/metrics.json` | metrics.json dict_keepz_360 | `21f9c9d1ff23c1f17464669097f7e28eb49c912c162e3c52325a7c773b2da82d` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/stgcn_unified_best.pt` | stgcn_unified_best.pt dict_keepz_360 | `1fc9031d127701146efe3a852f410d4bdefbf49264193a899659c6c3d52f54a7` |
| `reports/step4_2026-09-26/runs/dict_keepz_360/test_logits.npz` | test_logits.npz dict_keepz_360 | `013c15075763ec118cff134b1e681ac81b686027af77df0f355f694328b6ba9f` |
| `reports/step4_2026-09-26/runs/run_dropz/history.json` | history.json H-dropz | `564e3eb9c9ee9124ef9fc2362339ed30fd87d06367f98f1761368f9a90b838fd` |
| `reports/step4_2026-09-26/runs/run_dropz/metrics.json` | metrics.json H-dropz | `b9199034227a316cf05cc53098c832565ca27c223c9671750b4603695570e903` |
| `reports/step4_2026-09-26/runs/run_dropz/stgcn_unified_best.pt` | stgcn_unified_best.pt H-dropz | `1dd35425dbc9a6f704ffc88fc9644bb753637b1749126ad3b47a28d5744b3924` |
| `reports/step4_2026-09-26/runs/run_dropz/test_logits.npz` | test_logits.npz H-dropz | `4936a0cb33ec842d229f052c2bae967feaf591fc16f4a50cd124d3d93f8c8d0f` |
| `reports/step4_2026-09-26/runs/run_keepz/history.json` | history.json H-keepz | `d00e23636aa4b74b0011b2cf9c78f7dafd5a4d57389b1663eb6af2dcbbe953d4` |
| `reports/step4_2026-09-26/runs/run_keepz/metrics.json` | metrics.json H-keepz | `fa175406149af0489c36c4ea4ef41d13abba683bbaff4571ef3cb79123aaaa57` |
| `reports/step4_2026-09-26/runs/run_keepz/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz | `db1909493312bccb2bf7271ce375f01ff09c6b1cbb5b7ac442dc6246f357a92d` |
| `reports/step4_2026-09-26/runs/run_keepz/test_logits.npz` | test_logits.npz H-keepz | `f66f20fef3875b7225d44f879c521f781557c810b8de8c51e0f68ce1d32b57ed` |
| `reports/step4_2026-09-26/runs/run_keepz_360/history.json` | history.json H-keepz-360 | `b2f292d369aa146b6eb9fe95179794cb686230bfd6019a396ceda0f4e69d695d` |
| `reports/step4_2026-09-26/runs/run_keepz_360/metrics.json` | metrics.json H-keepz-360 | `a573daa651ad28d2c6f561276c322415a30cc91a2320e568825161650cd98de1` |
| `reports/step4_2026-09-26/runs/run_keepz_360/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-360 | `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e` |
| `reports/step4_2026-09-26/runs/run_keepz_360/test_logits.npz` | test_logits.npz H-keepz-360 | `0a560a6d3810f0578384d0fb110ebd728004881dd087ea2fe101f2ac4ea88bfe` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/history.json` | history.json H-keepz-notrim | `1a567f2036d114649d67d3e904a4e2ed7afbe06fb92bfd9688efe30f67c73f4a` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/metrics.json` | metrics.json H-keepz-notrim | `12e63883049126fa46d2fc56374f6068e6dd0958cb30d6588a019409d5a78590` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-notrim | `92e603e19300e228ac220da8f1a07dae94e18a72bd105859f53de0c4b82e2df9` |
| `reports/step4_2026-09-26/runs/run_keepz_notrim/test_logits.npz` | test_logits.npz H-keepz-notrim | `a04cadca374457e787f4b9b2e056ae02577ad9ca7409cca0251a49fab1405eb9` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/history.json` | history.json H-keepz-seed43 | `a98d2f9f5deb2374ba9fe20b90e63d7bdf0f6d6ac6611f32b3805a8a614a07f1` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/metrics.json` | metrics.json H-keepz-seed43 | `2bd99e0bd0af07c49f41f937914d7c4fd9ab22a7e323796a262d2fc46760a50b` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/stgcn_unified_best.pt` | stgcn_unified_best.pt H-keepz-seed43 | `f8f28f05170551a65b700b947e54fa5b96d348565aeaf4fabc41a35772acbd98` |
| `reports/step4_2026-09-26/runs/run_keepz_seed43/test_logits.npz` | test_logits.npz H-keepz-seed43 | `bb2bf6b7f495c9a6d95daa952e794e6bc376095257e63371ae18748259f8dab1` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized.log` | kernel log | `cc9a75afdc0f60802c2065acd7fb6fae281f8651c4240d56e66bf5cb0eb25b85` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log` | kernel log | `f0dc938d16da2e4fa63ae768511b66cdb9ded491735278a92ca06f1aaf7359a0` |
| `reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log` | kernel log | `d8b011c40f6dde10435f0d7c244cb35aba63c1e3d4655f967498f5dabb06cad8` |
| `reports/unified_run_2026-09-25/run/history.json` | history.json baseline | `3a1d7bc924a07fc4b8d46e35d28dbe2b6df69366fcb7b783f9d3683279631dab` |
| `reports/unified_run_2026-09-25/run/metrics.json` | metrics.json baseline | `2fa2daadc5ba0558323e401b374fe083741f9c81cecf1c11d1203438cd62cd16` |
| `reports/unified_run_2026-09-25/run/stgcn_unified_best.pt` | stgcn_unified_best.pt baseline | `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb` |
| `reports/unified_run_2026-09-25/run/test_logits.npz` | test_logits.npz baseline | `cded2935ed711382b759cfb377de4dade06856d797b7a98838968f5a7d5dacf3` |
| `reports/unified_run_2026-09-25/run_seed43/history.json` | history.json baseline-seed43 | `e5c0f7cc6d7760c55bae5cf43f3adbdd9141512d94e5f3cdfe5bfacc8332f648` |
| `reports/unified_run_2026-09-25/run_seed43/metrics.json` | metrics.json baseline-seed43 | `9c203a0df80fd13bf49190c254ffe59cda51fbcd41f45eb2c9e3e044d39e78c2` |
| `reports/unified_run_2026-09-25/run_seed43/stgcn_unified_best.pt` | stgcn_unified_best.pt baseline-seed43 | `a8f0dc6f7df597fe9bacfedadd846e8eabeada164e3a279bcc82c6b242279871` |
| `reports/unified_run_2026-09-25/run_seed43/test_logits.npz` | test_logits.npz baseline-seed43 | `b4d5acf5118fada4d65673acca706d7c8c42ee76a1204d942f43f63528cc0cdd` |
| `reports/unified_run_2026-09-25/vsl-train-unified.log` | kernel log | `14c1b59af71cd8dcbd9f5d9157d1a1c729ac38f44029e9d427f27d33d39a3422` |
| `scripts/train_unified.py` | scripts/train_unified.py (chỉ đọc text: tùy chọn khởi tạo) | `276d91601a90fde92710d094b5bb5dada2b5a78790ac40fd3285b4585976705c` |

### 1.5 Lưu trữ checkpoint và logits (Kaggle dataset private)

- Dataset: `phmvnsm33/vslt-step4-artifacts` (https://www.kaggle.com/datasets/phmvnsm33/vslt-step4-artifacts); private: CÓ (kiểm bằng dataset_list(mine) và dataset_metadata lúc 2026-09-27T10:56:50Z); trạng thái: ready; tổng dung lượng: 37417786 byte (18 file + SHA256SUMS).
- Manifest: `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json` (sinh bởi `scripts/archive_step4_kaggle.py verify` ở commit 2b3ca94; sha256 của manifest ở mục 1.4).

| Run | Loại | Tên trong dataset | Kích thước (byte) | sha256 | trùng §1.4 |
|---|---|---|---|---|---|
| baseline | checkpoint | `unified_run_2026-09-25__run__stgcn_unified_best.pt` | 1958573 | `930633233ff37a5557e16e09714c11d2a1549def0450b6196880f4501de4aabb` | CÓ |
| baseline | test_logits | `unified_run_2026-09-25__run__test_logits.npz` | 2690394 | `cded2935ed711382b759cfb377de4dade06856d797b7a98838968f5a7d5dacf3` | CÓ |
| H-keepz | checkpoint | `step4_2026-09-26__runs__run_keepz__stgcn_unified_best.pt` | 1958829 | `db1909493312bccb2bf7271ce375f01ff09c6b1cbb5b7ac442dc6246f357a92d` | CÓ |
| H-keepz | test_logits | `step4_2026-09-26__runs__run_keepz__test_logits.npz` | 2662197 | `f66f20fef3875b7225d44f879c521f781557c810b8de8c51e0f68ce1d32b57ed` | CÓ |
| H-dropz | checkpoint | `step4_2026-09-26__runs__run_dropz__stgcn_unified_best.pt` | 1958829 | `1dd35425dbc9a6f704ffc88fc9644bb753637b1749126ad3b47a28d5744b3924` | CÓ |
| H-dropz | test_logits | `step4_2026-09-26__runs__run_dropz__test_logits.npz` | 2657818 | `4936a0cb33ec842d229f052c2bae967feaf591fc16f4a50cd124d3d93f8c8d0f` | CÓ |
| H-keepz-360 | checkpoint | `step4_2026-09-26__runs__run_keepz_360__stgcn_unified_best.pt` | 1958829 | `648a7825cab9d54cf8d6ce16208cf1cd8dbfbe493fb2d7de919b1f9aebc9b59e` | CÓ |
| H-keepz-360 | test_logits | `step4_2026-09-26__runs__run_keepz_360__test_logits.npz` | 2653253 | `0a560a6d3810f0578384d0fb110ebd728004881dd087ea2fe101f2ac4ea88bfe` | CÓ |
| H-keepz-seed43 | checkpoint | `step4_2026-09-26__runs__run_keepz_seed43__stgcn_unified_best.pt` | 1958829 | `f8f28f05170551a65b700b947e54fa5b96d348565aeaf4fabc41a35772acbd98` | CÓ |
| H-keepz-seed43 | test_logits | `step4_2026-09-26__runs__run_keepz_seed43__test_logits.npz` | 2648534 | `bb2bf6b7f495c9a6d95daa952e794e6bc376095257e63371ae18748259f8dab1` | CÓ |
| H-keepz-notrim | checkpoint | `step4_2026-09-26__runs__run_keepz_notrim__stgcn_unified_best.pt` | 1958829 | `92e603e19300e228ac220da8f1a07dae94e18a72bd105859f53de0c4b82e2df9` | CÓ |
| H-keepz-notrim | test_logits | `step4_2026-09-26__runs__run_keepz_notrim__test_logits.npz` | 2649741 | `a04cadca374457e787f4b9b2e056ae02577ad9ca7409cca0251a49fab1405eb9` | CÓ |
| baseline-seed43 | checkpoint | `unified_run_2026-09-25__run_seed43__stgcn_unified_best.pt` | 1958573 | `a8f0dc6f7df597fe9bacfedadd846e8eabeada164e3a279bcc82c6b242279871` | CÓ |
| baseline-seed43 | test_logits | `unified_run_2026-09-25__run_seed43__test_logits.npz` | 2683317 | `b4d5acf5118fada4d65673acca706d7c8c42ee76a1204d942f43f63528cc0cdd` | CÓ |
| dict_keepz | checkpoint | `step4_2026-09-26__runs__dict_keepz__stgcn_unified_best.pt` | 1807533 | `62cb7f2006b22f99d64ddac1bef6164a7592e072cf470fc1b482ad6429435cc0` | CÓ |
| dict_keepz | test_logits | `step4_2026-09-26__runs__dict_keepz__test_logits.npz` | 722096 | `1c8213657b42a4eb6f08e8e54b59ebbbf590fefa820f703a8502f29268aef397` | CÓ |
| dict_keepz_360 | checkpoint | `step4_2026-09-26__runs__dict_keepz_360__stgcn_unified_best.pt` | 1807597 | `1fc9031d127701146efe3a852f410d4bdefbf49264193a899659c6c3d52f54a7` | CÓ |
| dict_keepz_360 | test_logits | `step4_2026-09-26__runs__dict_keepz_360__test_logits.npz` | 721817 | `013c15075763ec118cff134b1e681ac81b686027af77df0f355f694328b6ba9f` | CÓ |

Dataset private theo Kaggle API (không truy cập ẩn danh được; chỉ tài khoản chủ và người được chia sẻ truy cập được; danh sách chia sẻ không được kiểm); tải: `kaggle datasets download phmvnsm33/vslt-step4-artifacts`; kiểm: `sha256sum -c SHA256SUMS`.

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
- Augmentation (training only): scale, rotation, speed warp 0.7-1.3, random temporal crop.
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

(iv) Hệ quả cho run được chọn (sinh từ `run_config.trim`): Run được chọn H-keepz-360 train với trim=true, tức VẪN cắt đoạn nghỉ (cắt nghỉ không được công nhận theo luật VAL). Đường live muốn khớp với model này thì harmonize() phải gồm bước cắt nghỉ với cùng tham số trong `preprocessing` của checkpoint. Giữ hay bỏ cắt nghỉ ở đường live không do luật đăng ký trước quyết định (PREREGISTRATION chỉ quy định khi nào cắt nghỉ được công nhận); bỏ thì phải train lại.

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

### Phạm vi so sánh và mức khớp train

Sinh từ `history.json` của hai run (trainer ghi mỗi epoch) và lệnh train trong log kernel; không chạy lại model.

| Model | Epoch đã chạy | Epoch tốt nhất | Train top-1 ở epoch tốt nhất | Train top-1 ở epoch cuối | lr đầu → lr cuối | Epoch giảm lr | val_loss đầu / min / cuối | Clip train | Batch (từ lệnh) | Bước/epoch | Tổng bước | Tổng `time_sec` (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| từ điển (dict_keepz_360) | 48 | 28 | 29.69% | 34.21% | 0.001 → 1.5625e-05 | 16, 22, 28, 34, 40, 46 | 6.3943 / 6.3584 / 6.4564 | 795 | 64 | 13 | 624 | 212.5 |
| gộp (H-keepz-360) | 98 | 78 | 95.15% | 95.47% | 0.001 → 1.5625e-05 | 50, 64, 74, 81, 87, 97 | 4.3396 / 2.4065 / 2.437 | 15138 | 64 | 237 | 23226 | 5738.5 |

- train top-1 = số trainer ghi trên batch augment ở chế độ train (src/training/trainer.py), không phải độ chính xác sạch trên tập train. Chi tiết: train_top1 là số src/training/trainer.py ghi trong train_epoch: đo trên batch đã augment, ở chế độ model.train() (dropout), với batch do WeightedRandomSampler lấy mẫu (scripts/train_unified.py) — không phải độ chính xác sạch trên tập train.
- Bước/epoch = ceil(clip train / batch) (WeightedRandomSampler với num_samples = số clip train, không drop_last); lr ghi trong history là lr dùng ở epoch đó (trước bước ReduceLROnPlateau theo VAL loss).
- Lệnh train hai model chỉ khác: không khác ngoài --out-dir/--data-root/--sources.
- scripts/train_unified.py không có tùy chọn khởi tạo từ trọng số → cả hai model train từ khởi tạo ngẫu nhiên.

**Phạm vi:** Kết quả chính so model tách **train từ đầu, cùng công thức với model gộp** với model gộp. Hai model có quỹ tối ưu và mức khớp train khác nhau (bảng trên). Vì vậy kết quả này KHÔNG đo phương án tách có khởi tạo từ trọng số VSL-GH / model gộp, và cũng không đo phương án tách được train tới khi khớp.

Ước lượng (không phải kết quả, không thuộc kế hoạch này): train model từ điển tới cùng tổng số bước như model gộp cần 1787 epoch × 4.43 s/epoch (trung bình `time_sec` của run từ điển) ≈ 7910 s ≈ 2.20 giờ GPU cho một run một seed, chưa gồm khởi động kernel; ước lượng, không phải kết quả; time_sec đo trong kernel có thể chạy nhiều job.

**Phân tích thăm dò — không đăng ký trước, không dùng để chọn:**

(a) Model gộp với logits giới hạn về đúng không gian nhãn của model từ điển, cùng clip:

| Model | Top-1 | Top-5 | Top-10 |
|---|---|---|---|
| gộp, giới hạn nhãn | 12.8% (92/721) [10.5, 15.4] | 26.9% (194/721) [23.8, 30.3] | 34.3% (247/721) [30.9, 37.8] |

McNemar top-1 (từ điển vs gộp giới hạn): n10 = 7, n01 = 76, p = 9.43e-16.

(b) Dự đoán top-1 của model gộp rơi vào lớp chỉ-VSL-GH (282 lớp có train VSL-GH, không có train QIPEDC) vs lớp có train QIPEDC (594 lớp). Không đăng ký trước, chỉ báo, không kiểm định. Cột "mọi dự đoán" lẫn độ chính xác vào (dự đoán đúng tất nhiên rơi vào lớp của nguồn đúng), nên có thêm các cột chỉ dự đoán sai:

| Tập clip | Mọi dự đoán: lớp chỉ-VSL-GH | Mọi dự đoán: lớp có QIPEDC | Mọi dự đoán: lớp không có train | Dự đoán đúng (top-1) | Chỉ dự đoán sai: lớp chỉ-VSL-GH | Chỉ dự đoán sai: lớp có QIPEDC | Chỉ dự đoán sai: lớp không có train |
|---|---|---|---|---|---|---|---|
| mọi clip QIPEDC TEST | 9.6% (69/722) [7.6, 11.9] | 90.4% (653/722) [88.1, 92.4] | 0.0% (0/722) [0.0, 0.5] | 88/722 | 10.9% (69/634) [8.7, 13.5] | 89.1% (565/634) [86.5, 91.3] | 0.0% (0/634) [0.0, 0.6] |
| clip chung của 4c | 9.6% (69/721) [7.6, 11.9] | 90.4% (652/721) [88.1, 92.4] | 0.0% (0/721) [0.0, 0.5] | 88/721 | 10.9% (69/633) [8.7, 13.6] | 89.1% (564/633) [86.4, 91.3] | 0.0% (0/633) [0.0, 0.6] |
| S06 (đối chứng) | 81.8% (973/1189) [79.5, 83.9] | 18.2% (216/1189) [16.1, 20.5] | 0.0% (0/1189) [0.0, 0.3] | 964/1189 | 81.3% (183/225) [75.7, 85.9] | 18.7% (42/225) [14.1, 24.3] | 0.0% (0/225) [0.0, 1.7] |

Tỷ lệ nền: lớp chỉ-VSL-GH trong không gian nhãn model gộp: 282/876 (32.2%).

Chỉ là chỉ báo cho giả thuyết "model gộp học phân biệt nguồn", không phải kiểm định. Lớp đúng của S06 thuộc VSL-GH, nên lỗi của S06 tự nhiên rơi vào lớp VSL-GH nhiều hơn.

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
- Tiêu đề phần bổ sung PREREGISTRATION ghi `2026-09-26 12:30`; commit `9b0ade1` lúc `2026-09-26 12:13:24 +0700` (tiêu đề − commit = 996 s; giờ tiêu đề đọc theo múi giờ của commit). Thứ tự so với kết quả được xét theo giờ commit.
- Mức khớp train của model từ điển (dict_keepz_360): train top-1 ở epoch cuối 34.21% so với 95.47% của model gộp (H-keepz-360); tổng bước tối ưu 624 so với 23226 (mục 4, "Phạm vi so sánh và mức khớp train"). Kết quả chính của 4c chỉ nói về model tách train từ đầu bằng công thức hiện tại.
- Nguồn gốc số train top-1: train_top1 là số src/training/trainer.py ghi trong train_epoch: đo trên batch đã augment, ở chế độ model.train() (dropout), với batch do WeightedRandomSampler lấy mẫu (scripts/train_unified.py) — không phải độ chính xác sạch trên tập train (src/training/trainer.py).
- Nguồn trong manifest: qipedc, vslgh — HCMUE không dùng để train hay đo.
- Model mặc định của backend: VSL_MODEL_TYPE mặc định `stgcn` → `checkpoints/stgcn_tier2_indomain.pt` (sha256 53c34cba43854c3e9820495bba3f93ffe18b5e1cb87ef44278a188ccafe2c826); trùng model được kiểm ở 4a: KHÔNG.
- Chọn epoch: epoch tốt nhất của mỗi run chọn theo VAL top-1 tổng (VSL-GH chiếm 1190/1295 clip VAL), còn biến thể chọn theo balanced VAL.
- `git_commit` trong JSON của scripts/shortcut_85.py chỉ là HEAD, không ghi trạng thái bẩn của mã.
- Checkpoint và logits TEST của mọi run được lưu ở Kaggle dataset private `phmvnsm33/vslt-step4-artifacts` (sha256 ở mục 1.5); lưu trữ không gồm log kernel hay đầu vào nào khác. 8/57 đầu vào của báo cáo này vừa không được git track vừa không nằm trong lưu trữ: `checkpoints/stgcn_tier2_indomain.pt`, `checkpoints/stgcn_unified_best.pt`, `data/processed/vslgh_segments/segments.csv`, `reports/step4_2026-09-26/runs/vsl-train-harmonized.log`, `reports/step4_2026-09-26/runs/vsl-train-harmonized_v2.log`, `reports/step4_2026-09-26/runs/vsl-train-harmonized_v3.log`, `reports/unified_run_2026-09-25/run_seed43/history.json`, `reports/unified_run_2026-09-25/vsl-train-unified.log`; bằng chứng thay thế cho các file này là sha256 ở mục 1.4. Thiếu một đầu vào thì scripts/report_step4.py dừng với mã 2, nên kể cả khi có quyền truy cập dataset, clone sạch vẫn KHÔNG tái tạo được báo cáo.

## 6. Review

# Vòng 2

Review 01, vòng CODE↔REVIEW 2/3. Reviewer độc lập, ngày 2026-09-26, nhánh `feat/vslt-complete`, HEAD `65a2821`.
Commit mới được review: `c54b772`, `67ff25a`, `65a2821` (nối tiếp `8c08845`). Kế hoạch: `docs/plans/01-buoc4-hoan-tat-4a-4c.md`
(§0 "Lần sửa 1", AC1–AC9). Mọi con số dưới đây do reviewer tự chạy lại qua `.venv/Scripts/python`, `PYTHONIOENCODING=utf-8`.
Không tin tóm tắt của coder; đã đọc `git diff 8c08845..HEAD`.

## Kết luận vòng 2: **APPROVE**

Không còn FAIL. M1–M4 và các góp ý nhỏ của vòng 1 đã được xử lý thật, do script sinh ra (không chỉnh tay), có test. Mục 13
nay PASS: REPORT có mục "Phạm vi so sánh và mức khớp train" sinh từ `history.json`, PROPOSAL nêu đúng phạm vi.
Việc còn lại **theo kế hoạch, không phải lỗi**: R6 — sinh lại REPORT/JSON với `--review-file docs/reviews/01-review.md`
(file này, có vòng 2), kiểm AC9, rồi DỪNG ở điểm dừng "sau 4c". Hiện §6 của REPORT vẫn chứa kết luận vòng 1
(CHANGES_REQUESTED), nên AC4 j chưa xong cho tới R6.

## Bảng 1–13 (trạng thái HEAD `65a2821`)

| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch; AC có test thật | PASS | AC1 ca 16–23 có test riêng, assert giá trị cụ thể: `TestTrainingFit` (`tests/test_report_step4.py:459–501`: hòa `val_top1` ở epoch 2/3 → chọn val_loss nhỏ hơn; đảo loss → 2; hòa cả hai → epoch sớm; `lr_drop_epochs == [3, 4]`; 795/64 → 13 bước; batch `None` → `None`; history rỗng → mã 2), ca 17 (504–511), ca 18 (514–537), ca 19 (540–561, quét text fixture có/không `--init-from`), ca 20 (564–586: dự đoán đúng "a" không vào `wrong_only`, tổng ba cột = n), ca 21 (589–609: tên run đổi theo; nhánh trim=false không có "trim=true"), ca 22 (612–642: 996 s; không tiêu đề → `[]`; không commit → `None`), ca 23 + hợp đồng CLI (645–715: exit 2 khi thiếu history của run chọn / run từ điển dùng, `null` với run khác, thứ tự mục 4c). AC5b 1–6: `TestProposal4cScope` (718–780), không skip, thiếu file thì lỗi ở `setUp`. |
| 2 | Tự chạy lại toàn bộ test | PASS | `python -m unittest tests.test_report_step4 -v` → `Ran 69 tests ... OK`, 0 skip. Bộ AC2 (10 module handoff) → `Ran 53 tests ... OK`. Khớp số coder báo (38 → 62 ở c54b772, → 69 ở 67ff25a; AC2 53 → 53). |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff 8c08845..HEAD -- tests/` → 1 file, `334 insertions(+)`, không có dòng `-` nào ngoài dòng header `--- a/…`. Không có `skip`/`expectedFailure` mới. Thay đổi `make_fixture` chỉ THÊM hằng `FIT_HISTORY` (dòng 246–253) và một dòng ghi `history.json` cho mỗi run fixture (dòng 285). Đánh giá: không nới test cũ. Mọi assert cũ giữ nguyên. `history.json` nay là đầu vào bắt buộc (exit 2 khi thiếu ở run chọn / run từ điển dùng), nên nếu không thêm dòng này thì các test end-to-end cũ sẽ fail vì lý do hợp lệ. Các test lỗi cũ (thiếu `test_logits.npz` → 2, sai thứ tự nhãn → 1, không khớp từ điển → 3) vẫn kiểm cùng mã thoát và vẫn kiểm không ghi file. |
| 4 | Nguồn gốc dữ liệu thật | PASS | Đầu vào mới chỉ là `runs/*/history.json` do trainer ghi trong kernel (7 file đã commit) và lệnh train trong log kernel. Số clip train 795 / 15138 khớp `train.log` của từng run ("classes 594, train 795, val 105, test 721"; "classes 876, train 15138"). Batch 64 khớp lệnh ở `vsl-train-harmonized_v3.log` dòng 15 và 80. Không có dữ liệu sinh. |
| 5 | Rò rỉ | PASS (giới hạn đã công bố) | Không đổi so với vòng 1: `split_integrity` PASS; QIPEDC không có signer_id và S06 dùng câu đã thấy trong train, cả hai nằm trong REPORT §5. |
| 6 | Chọn bằng VAL, TEST một lần | PASS | Chẩn đoán mức khớp chỉ đọc `history.json` (train/VAL), tính SAU khi chọn (`scripts/report_step4.py:861–884`), không đi vào `select`/`choose_*`. TEST vẫn chỉ đọc lại `test_logits.npz`. Mọi giá trị JSON cũ không đổi (mục 7). |
| 7 | Số liệu truy được | PASS | (a) Chạy lại đúng lệnh ở header, chỉ đổi `--out`/`--json-out` sang thư mục tạm: exit 0; JSON bằng (`==`) bản đã commit sau khi bỏ `generated_by`; REPORT chỉ khác 2 dòng header (đường dẫn out, HEAD `67ff25a` → `65a2821`). (b) Chạy lần 2 cùng lệnh → `cmp` byte-giống cả hai file. (c) `git diff 67ff25a HEAD -- scripts src tests` rỗng; `code_dirty=false`. (d) Duyệt đệ quy JSON `8c08845` vs HEAD: không khóa cũ nào bị xóa; giá trị cũ chỉ đổi ở `generated_by`, `inputs` (45 mục cũ là tập con của 56 mục mới; thêm 9 `history.json`, `train_unified.py`, review), `kernel_code_diffs[3].to`, `augmentation` (bỏ tiền tố lặp), `review`. (e) Kiểm độc lập mục 4c mới từ `history.json`: từ điển 48 epoch, best 28 (= `metrics.json` `val_best.epoch`), train top-1 29.69 / 34.21, lr 0.001 → 1.5625e-05, giảm lr ở 16, 22, 28, 34, 40, 46, val_loss 6.3943 / 6.3584 / 6.4564, tổng time_sec 212.5; gộp 98 epoch, best 78, 95.15 / 95.47, giảm lr ở 50, 64, 74, 81, 87, 97, val_loss 4.3396 / 2.4065 / 2.437, tổng 5738.5. Bước: ceil(795/64) = 13 → 624; ceil(15138/64) = 237 → 23226; ceil(23226/13) = 1787 epoch × 4.4267 s ≈ 7910 s ≈ 2.20 giờ. Tất cả trùng REPORT dòng 326–336. (f) Thăm dò (b): 69/634, 183/225, 282/876 trùng số reviewer tự tính ở vòng 1; 634 = 722 − 88, 225 = 1189 − 964. |
| 8 | Cỡ mẫu và CI | PASS | Cột "chỉ dự đoán sai" có k/n + Wilson CI cho cả ba bộ dòng (REPORT dòng 352–354). Không có kết luận mới rút từ n nhỏ; (b) ghi "chỉ báo, không kiểm định". |
| 9 | Nhất quán train–realtime | PASS (trong phạm vi) | REPORT §3.4 (iv) (dòng 274) sinh từ `run_config.trim`: H-keepz-360 train với trim=true; live phải cắt nghỉ cùng tham số; giữ/bỏ không do PREREG quyết định; bỏ thì train lại. Việc này không chạm `backend/`, `src/`. Vẫn **chặn** đổi model mặc định cho tới khi có test tương đương (360 px + cắt nghỉ). |
| 10 | Không random/mock/hard-code | PASS | Chuỗi cố định mới (`SCOPE_SENTENCE`, `TRAIN_TOP1_MEASUREMENT`) là mô tả, không chứa số. Câu phạm vi chỉ in khi `scope_limited` (tổng bước khác nhau hoặc không dùng cờ khởi tạo), đúng §3.4. `trim_consequence` không gõ cứng tên run (test ca 21c). Không có random/mock mới. |
| 11 | Bảo mật | PASS | Không token/khóa/`kaggle.json` trong diff. `git diff --name-only 27233f6..HEAD -- '*.pt' '*.npz' '*.log'` rỗng. Không đụng API/CORS/WS. Vẫn còn: `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` untracked và không bị gitignore (`git check-ignore` exit 1); đây là câu hỏi cho người dùng. |
| 12 | So sánh công bằng | PASS | 4c vẫn trên cùng 721 clip; ngưỡng 0.5 không đổi; không tiêu chí nào bị nới. Mục mới nói rõ hai model có cùng lệnh train (chỉ khác `--out-dir/--data-root/--sources`; reviewer đối chiếu log v3 dòng 15 và 80), nhưng quỹ tối ưu khác nhau: 624 vs 23226 bước. |
| 13 | Kết luận vượt bằng chứng | PASS | REPORT: câu phạm vi (dòng 334) và dòng Giới hạn (372) nói kết quả chính chỉ về "model tách train từ đầu bằng công thức hiện tại". PROPOSAL: "khuyến nghị có điều kiện: 4c chỉ đo một cách tách" (dòng 3); mục "Phạm vi" (9–12) có 34.21% vs 95.47% và 624 vs 23226 bước, nói rõ KHÔNG loại trừ A khi train tới khi khớp hoặc khởi tạo từ trọng số; câu cũ "mất toàn bộ dữ liệu VSL-GH" đã bỏ; (b) chỉ dùng cột dự đoán sai + tỷ lệ nền, ghi "chỉ báo, không kiểm định"; "Điều gì sẽ làm đổi khuyến nghị" có thí nghiệm mới "tốn GPU … cần người dùng duyệt". Nhận xét thêm của reviewer (ủng hộ "chưa khớp"): val_loss của model từ điển 6.3943 → min 6.3584, gần ln(594) ≈ 6.387, tức VAL loss hầu như không rời mức ngẫu nhiên. Góp ý câu chữ nhỏ ở G3, không chặn. |

## Kiểm theo AC (vòng 2)

| AC | Kết quả | Ghi chú |
|---|---|---|
| AC1 | PASS | 69 OK, 0 skip; ca 1–15 cũ nguyên vẹn; ca 16–23 có test (mục 1). |
| AC2 | PASS | 53 → 53 OK; `test_report_step4` 38 → 69 (≥ 38 + 8); diff test chỉ có dòng thêm. Số trước/sau có trong `docs/progress_log.md`. |
| AC3 | PASS | Mục 7 (a)–(c). Đã kiểm ≥ 10 số, trong đó > 3 số ở mục 4c mới truy về `history.json`. |
| AC4 a–i | PASS | Không đổi so với vòng 1 (giá trị JSON cũ không đổi). |
| AC4 j | CHƯA XONG (theo kế hoạch) | §6 hiện là review vòng 1. Làm ở R6 với file này. |
| AC4 k | PASS | REPORT dòng 320–336: bảng đủ 13 cột, dòng về cách trainer đo, `train_cmd_diff`, `init_options`, câu phạm vi, ước lượng GPU có nhãn "ước lượng". Đã đối chiếu > 2 giá trị mỗi model với `history.json`. |
| AC4 l | PASS | §3.4 (iv) dòng 274; JSON `4b.trimming.consequence`. |
| AC4 m | PASS | Dòng 348–358; số trùng review vòng 1 (69/634, 183/225, 282/876). |
| AC4 n | PASS | Dòng 371 (12:30 vs 12:13:24, 996 s), dòng 372–373. |
| AC4 o | PASS | Dòng 177: đúng một dòng "- Augmentation (training only): …"; không còn "Augmentation: Augmentation". |
| AC5 | PASS (sát ngưỡng) | 546 từ theo `str.split()` (cách test đếm) và theo `LC_ALL=C.UTF-8 wc -w`; một khuyến nghị (B); có "người dùng quyết định"; `TestProposal4c` không bị sửa. Xem G2 về cách đếm `wc -w`. |
| AC5b | PASS | 1–6 có test và đều qua. Reviewer kiểm thêm: 8 cụm `% (k/n)` và 45 số của PROPOSAL đều có trong REPORT §1–5 (không tính §6 Review). |
| AC6 | PASS | `git diff --stat 27233f6..HEAD`: chỉ file được phép. Code chỉ đổi `scripts/report_step4.py`. Không đổi `.gitignore`, PREREG, `history.json`, `metrics.json`, JSON 4a/4b cũ, `data/`. `REPORT_partial.md` không có trong git và vẫn trên đĩa. 3 file data người dùng xóa vẫn chưa commit. |
| AC7 | PASS (vòng này) | Không FAIL cho các commit Lần sửa 1 và cho 348843f, 4bb3811, 9e3be95, a414b0d, 27233f6, 4f4e349 (không đổi từ vòng 1). |
| AC8 | PASS | Cả 3 commit mới ghi `impact` + `detect-changes --scope all` (không partial/truncated) trong commit message. `docs/progress_log.md` có đúng 1 dòng kế hoạch 01, số test, và ghi chú `--scope staged` của 3 commit cũ. Dòng này cần cập nhật ở R6 (kết luận review cuối, số vòng, commit C). |
| AC9 | PASS (cơ chế) / làm lại ở R6 | `git diff 67ff25a 65a2821 -- REPORT.md`: 3 hunk = header (2 dòng), dòng inputs của file review, §6. JSON bằng nhau sau khi bỏ `generated_by`, `review`, input vai trò "review". Cần kiểm lại với commit R6. |

## Xác minh M1–M4 và góp ý nhỏ vòng 1

| Việc | Đã xử lý? | Bằng chứng |
|---|---|---|
| M1 (mức khớp / phạm vi 4c) | CÓ | Hàm `steps_per_epoch`, `training_fit`, `batch_size_from_command`, `train_cmd_diff`, `init_options` (`scripts/report_step4.py:318–396`); `4c.fit_and_scope` (861–884); render (1304–1349). PROPOSAL viết lại có phạm vi; có test AC5b. |
| M2 (hệ quả cắt nghỉ) | CÓ | `trim_consequence` (434–452), JSON `4b.trimming.consequence`, REPORT (iv). |
| M3 ((b) chỉ-sai + tỷ lệ nền) | CÓ | `pred_origin`, `label_space_base_rate` (413–431); `pred_split` dùng chúng (851–862) và giữ khóa cũ. |
| M4 (quy trình) | CÓ, trừ R6 | REPORT đã sinh với `--review-file` (65a2821); progress_log có dòng; `--scope all` ở cả 3 commit. Còn R6 cuối. |
| Góp ý: test AC5 theo ngữ cảnh | CÓ | AC5b.1 (so cụm `% (k/n)` nguyên văn + biên không phải `[0-9A-Za-z]`). Còn điểm yếu nhỏ, xem G1. |
| Góp ý: `REPORT_partial.md` | CÓ | Kế hoạch §2.1 đã sửa; file untracked, không bị đụng; câu hỏi ở §7. |
| Góp ý: giờ tiêu đề PREREG | CÓ | `prereg_header_times` (458–478), REPORT dòng 371, sinh từ `git show <commit>:PREREGISTRATION.md`. |
| Góp ý: "Augmentation" lặp | CÓ | REPORT dòng 177; test ca 23. |
| Góp ý: `.gitignore` cho `.pt` | Chuyển cho người dùng | Đúng kế hoạch (§7 câu 5); `.gitignore` chưa bị sửa. |

## Xác minh risk HIGH của `detect-changes` ở c54b772

- Reviewer chạy `node .gitnexus/run.cjs detect-changes --scope compare --base-ref 8c08845 --repo .` → `risk high`, 8 luồng bị
  ảnh hưởng: `Pred_split → Wilson`, `Main → Rel`, `Main → Sha256`, `Main → Fr`, `Main → Fv`, `Main → Na`, `Main → Yn`,
  `Label_space_base_rate → Wilson`. Cả 8 luồng nằm trong `scripts/report_step4.py`. Coder ghi 7 luồng; luồng thêm là
  `Label_space_base_rate`, do index được làm mới ở commit sau. Không đổi kết luận.
- `git diff -U0 8c08845..HEAD -- scripts/report_step4.py`: các hunk chỉ nằm ở khối hàm mới chèn sau `compare_legacy`, trong
  `build`, ở hàm mới `raw` (chèn sau `na`), và trong `render`. Không hàm có sẵn nào khác bị sửa. HIGH đến từ số symbol/luồng
  bị ảnh hưởng và việc lệch dòng, không phải từ caller ngoài script.
- `impact build --file scripts/report_step4.py --direction upstream`: LOW, `epistemic: exact`, caller duy nhất `main`
  (+ module Tests). `impact render …`: LOW nhưng `epistemic: lower-bound` (1 call site không xác định được kiểu receiver).
  Text search bù: chuỗi `report_step4` chỉ xuất hiện trong `scripts/report_step4.py`, `tests/test_report_step4.py` và
  `step4_results.json` (chuỗi lệnh). Trong script, `build(`/`render(` chỉ được gọi ở `main` (dòng 1469–1470). Call site không
  xác định là `R.render(...)` trong test. Kết luận: không có caller nào ngoài `main()` và test.

## Góp ý nhỏ (không chặn)

- **G1 (triển khai, test).** `TestProposal4c.test_every_number_is_in_report` và AC5b.1 so với TOÀN BỘ REPORT.md, kể cả §6
  Review. Văn bản review lại chứa đúng các số đó (34.21%, 69/634, …), nên test có thể qua nhờ văn bản review chứ không nhờ
  phần do script sinh. Reviewer đã kiểm tay: mọi số của PROPOSAL có trong §1–5. Đề xuất (việc sau, THÊM test mới): cắt REPORT
  trước `## 6. Review` khi so. Ngoài ra, biên `(?<![0-9A-Za-z.])` coi `_` là biên, nên "360" có thể khớp vào `run_keepz_360`.
- **G2 (kế hoạch, cách đo AC5).** `wc -w` phụ thuộc locale. Trong Git Bash mặc định ra **555** (> 550), vì chế độ byte tách từ
  tại byte 0xA0 của chữ "à". `LC_ALL=C.UTF-8 wc -w` và `str.split()` ra **546**. Con số "508" của vòng 1 cũng là số đếm ở chế
  độ byte (UTF-8: 498). Số đúng là 546 ≤ 550, nhưng chỉ dư 4 từ. Planner nên ghi rõ cách đếm (UTF-8 / `str.split()` như test).
- **G3 (triển khai, câu chữ PROPOSAL dòng 17).** "…rơi vào lớp chỉ-VSL-GH ở 10.9% (69/634) clip QIPEDC": mẫu số là 634 dự đoán
  SAI, không phải mọi clip QIPEDC. PROPOSAL cũng thiếu lưu ý đã có trong REPORT: lớp đúng của S06 thuộc VSL-GH nên lỗi S06 tự
  nhiên rơi vào lớp VSL-GH; và tỷ lệ nền của không gian nhãn không phải một giả thuyết không (null) chuẩn. Dòng đã ghi "chỉ
  báo, không kiểm định", nên không chặn.
- **G4 (quy trình).** `docs/plans/` đang untracked: hợp đồng AC mà REPORT, review và progress_log trỏ tới không có trong git.
  AC6 cho phép commit `docs/plans/`; orchestrator nên commit kế hoạch ở R6.
- **G5 (truy nguồn).** `reports/unified_run_2026-09-25/run_seed43/history.json` untracked nhưng được đọc làm đầu vào (sha256 ở
  REPORT §1.4). Không số nào trong REPORT phụ thuộc file này (chỉ run chọn và run từ điển được dùng `history.json`).
- **G6 (đọc ước lượng cho đúng).** `step_matched_estimate` giả định cùng thời gian/epoch và bỏ qua dừng sớm/giảm lr. Với công
  thức hiện tại, model từ điển sẽ lại dừng sớm. REPORT đã ghi "ước lượng, không phải kết quả". Thí nghiệm "train tới khi khớp"
  cần đổi công thức (không giảm lr / không dừng theo VAL 105 clip), tức là kế hoạch mới.

## Việc phải làm tiếp (không phải FAIL)

1. R6: chạy lại lệnh R3 + `--review-file docs/reviews/01-review.md` (file này) ở HEAD sạch; kiểm AC3 (`cmp` hai lần chạy) và
   AC9 (so với `67ff25a`: chỉ header, dòng inputs của review, §6); chạy lại `tests.test_report_step4`.
2. Cập nhật dòng progress_log: kết luận "APPROVE, vòng 2/3", thêm commit R6.
3. (Tùy chọn) commit `docs/plans/01-buoc4-hoan-tat-4a-4c.md` (G4).

Phân loại: không còn lỗi triển khai hay thiết kế ở mức FAIL. G1, G3 là lỗi triển khai nhỏ; G2, G4 thuộc kế hoạch/quy trình.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **A/B cho 4c.** Coder khuyến nghị B, có điều kiện. Kết quả chính (top-1 12.2% vs 3.2% trên 721 clip, p = 1.06e-14) là
   thật và đúng luật đăng ký, nhưng chỉ nói về model tách train từ đầu và chưa khớp (train top-1 34.21% vs 95.47%, 624 vs
   23226 bước). Nên đọc REPORT mục 4 "Phạm vi so sánh và mức khớp train" trước khi chọn.
2. **Có làm thí nghiệm MỚI trước khi chọn không** (chưa đăng ký trước, tốn GPU): (i) model từ điển train tới khi khớp: ước lượng
   thô ≈ 2.20 giờ GPU mỗi run mỗi seed, cần đổi công thức; (ii) khởi tạo từ trọng số VSL-GH / model gộp rồi fine-tune: cần thêm
   tùy chọn vào `scripts/train_unified.py` và phần đăng ký trước mới. Cần duyệt ngân sách GPU (hạn 10 giờ/tuần).
3. **360 px chỉ có một seed** (+1.72 điểm, trong khi chênh giữa hai seed H-keepz là +1.61): thêm seed trước khi đổi đường
   realtime sang 360 px, hay chấp nhận kết quả theo luật?
4. **Cắt đoạn nghỉ ở đường live:** model được chọn train với trim=true. Giữ bước cắt (khớp model) hay bỏ (phải train lại)?
5. **Việc nhỏ:** `REPORT_partial.md` (untracked): commit, giữ, hay xóa? Thêm `reports/unified_run_*/**/*.pt` vào `.gitignore`?
   Có commit file kế hoạch trong `docs/plans/` không (G4)?

---

# Review 01: Bước 4a → 4c (kế hoạch `docs/plans/01-buoc4-hoan-tat-4a-4c.md`)

Reviewer độc lập, ngày 2026-09-26, nhánh `feat/vslt-complete`, HEAD `8c08845`.
Commit được review:
- Của coder (kế hoạch 01): `72abc13`, `f4729ff`, `8c08845`.
- Trước quy trình 3 agent: `348843f`, `9e3be95`, `a414b0d`, `4bb3811`, `4f4e349`, `27233f6`.

Toàn bộ số liệu dưới đây do reviewer tự chạy lại. Lệnh chạy qua `.venv/Scripts/python`, có `PYTHONIOENCODING=utf-8`.

## Kết luận: **CHANGES_REQUESTED**

Mã, test, luật chọn, truy nguồn và khả năng tái lập đều đạt. Có đúng một FAIL, ở mục 13 (kết luận vượt bằng chứng):
`PROPOSAL_4c.md` khuyến nghị B dựa trên kết quả chính của 4c. Nhưng đề xuất không nói rằng model từ điển **chưa khớp được
chính tập train của nó**, và cũng không nói rằng phương án "A" đã đo chỉ là một cách tách: train từ đầu, chỉ dùng QIPEDC.
Phần sửa không cần GPU.

---

## Bảng 1–13

| # | Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch; mỗi AC có test thật | PASS | `tests/test_report_step4.py`: 38 test, mỗi ca AC1 1–15 có test riêng với assert cụ thể. Ca 8 (`test_selection_does_not_depend_on_test_logits`, dòng 337–351) đảo dấu logits TEST, kiểm test_groups ĐÃ đổi còn selection/trimming KHÔNG đổi, nên không phải test rỗng. Ca 2 (dòng 52–58) đặt tên ngược với `run_config`. Ca 15: exit 1/2/3, kiểm cả hai file không tồn tại (dòng 381–408). AC5: dòng 411–446. Điểm yếu nhỏ: test AC5 chỉ kiểm con số có mặt *ở đâu đó* trong REPORT.md (xem "Góp ý nhỏ"). Reviewer đã kiểm tay: mọi số trong PROPOSAL đều khớp đúng ngữ cảnh. |
| 2 | Tự chạy lại toàn bộ test | PASS | `python -m unittest tests.test_report_step4 -v` → `Ran 38 tests ... OK`, 0 skip. Bộ hồi quy AC2 (10 module) → `Ran 53 tests ... OK`. Commit message 72abc13 ghi 35 test; 8c08845 thêm 3 test AC5, tổng 38, khớp. |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff --stat e62fce3..HEAD -- tests/` → chỉ `tests/test_report_step4.py` (+450, file mới). Các commit trước quy trình không chạm `tests/`. `grep -i skip` chỉ ra tên test và docstring, không có `skipIf`/`skip`. |
| 4 | Nguồn gốc dữ liệu thật | PASS | Log kernel v1/v2/v3: VSL-GH do `prepare_canonical_vsl_gh.py` sinh từ repo gốc (checkout `6c351e6`). QIPEDC là npz MediaPipe trích từ video thật (kernel `vsl-extract-qipedc`, `vsl-extract-qipedc360-s0..s2`, cả 4 COMPLETE theo `kaggle kernels status`). Manifest có 1622 dòng QIPEDC, đủ 1622/1622 file trong cả `data/processed/qipedc_kps` và `qipedc_kps360` (4362 npz mỗi thư mục). Không có dữ liệu sinh. Fixture trong test là fixture unit test, được ghi rõ ở docstring. |
| 5 | Rò rỉ | PASS (có giới hạn đã công bố) | `split_integrity` trong metrics.json: `status PASS`, S01–S04 train, S05 val, S06 test, 1227 recording group QIPEDC. Reviewer tự đếm: 0 video_id và 0 recording_group chung giữa train/val/test. QIPEDC không có signer_id (0/1622) và 100% (1189/1189) đoạn S06 đến từ câu đã thấy trong train. Cả hai đã ghi ở REPORT §5. |
| 6 | Chọn bằng VAL, TEST một lần | PASS | `select()` (report_step4.py:429–435) chỉ nhận `bal` từ `val_by_source`. `choose_z` nhận biến thể đơn giản theo `run_config.hand_z` (dòng 121). Ngưỡng dùng `>=` trên số chưa làm tròn (dòng 131, 147, 166). TEST chỉ đọc lại `test_logits.npz`. Đối chiếu PREREG: dòng 8–10 khớp `balanced_val`+`choose_z`; dòng 11 và 22 khớp `choose_resolution` (so với run z đã chọn, không so với dropz như trước 348843f); dòng 14–15 và 23 khớp `pick_dict_run` (không fallback); dòng 20–21 khớp `trimming_verdict`; dòng 24 khớp: seed43 là aux, có test ca 4. Kết quả: H-keepz − H-dropz = +2.31 → H-keepz; H-keepz-360 − H-keepz = +1.72 → 360; trim −0.28 → không công nhận (`step4_results.json → 4b.selection`, `4b.trimming.val`). |
| 7 | Số liệu truy được | PASS | Chạy lại lệnh ở header REPORT.md, `--out` trỏ vào thư mục tạm, hai lần: exit 0 cả hai lần. Hai lần chạy chỉ khác nhau ở đường dẫn `--out` nằm trong chuỗi lệnh. So với file đã commit, chỉ khác thêm HEAD (`f4729ff` → `8c08845`, vì `git diff f4729ff HEAD -- scripts/ src/` rỗng). Mọi số và sha256 khác đều trùng. Có `code_dirty=false`. Đã kiểm ngẫu nhiên hơn 10 số (xem "Kiểm số độc lập"), tất cả khớp. |
| 8 | Cỡ mẫu và CI | PASS | Mỗi ô có % (k/n) [Wilson 95%], top-1 và top-5. Chéo nguồn n=26 được gắn "CI rất rộng". Giá trị 1 clip QIPEDC VAL là 0.476 điểm, in cạnh ngưỡng. Chênh seed +1.61 in cạnh các chênh dùng để chọn. Không có kết luận nào rút riêng từ nhóm n=26. |
| 9 | Nhất quán train–realtime | PASS (trong phạm vi) | Việc này không chạm đường live. REPORT §5 ghi rằng không file nào trong backend/ hoặc src/inference/ gọi `harmonize()`, và rằng nếu dùng 360 px thì live phải giảm cùng mức và có test tương đương. **Chặn** mọi việc đổi model mặc định sang H-keepz-360 cho tới khi có test tương đương. |
| 10 | Không random/mock/hard-code | PASS | Mã chỉ hard-code hằng số lấy từ PREREG: `THRESHOLD=0.5`, `DIFFERENT_SIGN`. `LEGACY_CONFIG_DEFAULTS={"trim":True}` có lý do kèm diff mã (reviewer kiểm `git diff c8a7bdf c65032a` thấy chỉ THÊM cờ `--no-trim`, mặc định giữ nguyên). `np.random` duy nhất nằm ở `shortcut_85.py:39` (lấy mẫu cân bằng có seed). Chuỗi "không TTA": reviewer kiểm `predict_all` (train_unified.py:102), chỉ một lượt. |
| 11 | Bảo mật | PASS | Không có token, khóa hay `kaggle.json` trong diff. `kernel-metadata.json` có `is_private: true`. Không commit `*.pt`/`*.npz`/`*.log`. Không đụng API, CORS hay WS. Góp ý: `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` đang untracked nhưng KHÔNG bị gitignore (quy tắc `.gitignore:75` chỉ phủ `step4_*`), nên dễ bị commit nhầm. |
| 12 | So sánh công bằng | PASS | Mọi run được đo trên cùng manifest TEST 1911 clip. 4c dùng cùng 721 clip, reviewer tự tính lại. Ngưỡng 0.5 không bị nới. Addendum PREREG (`9b0ade1`, 12:13:24) được commit TRƯỚC mọi kết quả 360/notrim/4c (`a414b0d` 13:37, `4f4e349` 15:14, `27233f6` 19:33) và SAU kết quả v1 (`c9296bf` 12:12:25). REPORT đã ghi điều này. Về quỹ huấn luyện không cân bằng của model từ điển: xem mục 13. |
| 13 | Kết luận vượt bằng chứng | **FAIL** | Xem "Việc phải sửa" M1. `runs/dict_keepz_360/history.json` (đã commit) cho thấy model từ điển dừng ở epoch 48, train top-1 **34.21%**, lr đã giảm còn 1.5625e-05, VAL QIPEDC tốt nhất 3.81%. Model gộp `run_keepz_360` đạt train top-1 95.47%. Model từ điển chỉ có khoảng 795/64 ≈ 13 bước/epoch, tức khoảng 600 bước; model gộp có khoảng 237 bước/epoch × 98 epoch. Vậy 4c đo "model tách, train từ đầu bằng công thức của model gộp và chưa khớp tập train" so với model gộp; 4c chưa đo "tách vs gộp" nói chung. PROPOSAL không nói điều này và viết "Tách ra thì 'Ký từ' mất toàn bộ dữ liệu VSL-GH". Câu đó chỉ đúng với cách tách train-từ-đầu. |

---

## Kiểm theo AC của kế hoạch

| AC | Kết quả | Ghi chú |
|---|---|---|
| AC1 | PASS | 38/38 OK, đủ 15 ca. |
| AC2 | PASS (số) / CHƯA XONG (ghi log) | 53 test OK, cùng 10 module handoff. `docs/progress_log.md` chưa có dòng của kế hoạch 01 và chưa ghi số trước/sau (Bước 8 còn lại). |
| AC3 | PASS | Tái lập như mục 7. Lưu ý thiết kế: `--out` nằm trong chuỗi lệnh được ghi lại, nên chạy ra thư mục tạm thì không bao giờ `cmp` byte-giống được. Coder đã so hai lần chạy tại chỗ. Reviewer so ra thư mục tạm: chỉ khác đường dẫn và HEAD. |
| AC4 a–i | PASS | a: 9 run đều có commit, lệnh, seed (baseline lấy từ `vsl-train-unified.log`, b4916b9), có sha256 và thời lượng kernel. b: 3 JSON cũ "chạy lại trùng: CÓ". c: 2.31 / 1.72 / 0.476 / +1.61. d: 4 nhóm × top-1/top-5 với k/n và CI, loại 0 clip. e: (i)(ii)(iii). f: seed cho H-keepz và baseline. g: khối cấu hình sinh từ ckpt và `HARMONIZED_DEFAULT`. h: một so sánh chính, dict_keepz chỉ nêu tên. i: đủ ý §3.4 mục 6. |
| AC4 j | CHƯA XONG | §6 Review hiện ghi "Chưa có kết quả". Cần sinh lại với `--review-file` sau khi sửa M1. |
| AC5 | PASS (test) / FAIL (nội dung, M1) | 508 từ; một khuyến nghị; có "người dùng quyết định"; đủ ý giới hạn; mọi số đều có trong REPORT. |
| AC6 | PASS | `git diff --stat 27233f6..HEAD` chỉ gồm các file được phép. Không đổi backend/, src/, configs/, frontend/, PREREG, JSON 4a/4b cũ, data/. 3 file data bị xóa của người dùng vẫn chưa commit. |
| AC7 | Chờ | Phụ thuộc M1. |
| AC8 | PASS có lưu ý | 72abc13 có kết quả `impact`. Nhưng cả 3 commit ghi `detect-changes --scope staged`, trong khi kế hoạch và CLAUDE.md yêu cầu `--scope all`. Không có lệnh Kaggle push. |

## Commit trước quy trình 3 agent

| Commit | Kết quả | Bằng chứng |
|---|---|---|
| 348843f | PASS (đã được thay thế) | Sửa đúng lỗi so 360 với dropz; aux không được chọn; 4c theo độ phân giải. Điểm yếu còn lại: nhận biến thể theo **tên** (`"dropz" in k`, `"notrim" in k`), trim ghép theo tên. 72abc13 đã chuyển sang `run_config` và có test ca 2 và ca 6. REPORT hiện tại sinh bằng mã mới, nên không có số nào đến từ logic cũ. |
| 4bb3811 | PASS | Ghi `command` và `git_commit` (HEAD `--short`). Giới hạn "không ghi trạng thái bẩn" có trong REPORT §5. |
| 9e3be95 | PASS | JOBS v3 khớp log v3 (entry 13, 14, 79): so với v1 chỉ khác `--no-trim` hoặc `--process-height 360` + `--data-root /tmp/root_360`; seed 42. `root_360` chỉ thay npz QIPEDC (log: 4362 npz từ 3 shard), `vslgh_segments` dùng chung. `dict_keepz_360` = `--sources qipedc --process-height 360`, khớp `run_config`. |
| a414b0d / 27233f6 | PASS | Log kernel chỉ in 30 dòng cuối metrics.json. Reviewer so 30 dòng đó với file trên đĩa cho cả 7 run: trùng 7/7. Không kiểm được `val_by_source` từ log vì log không in khóa này. Thay vào đó reviewer kiểm tính nội tại: VAL tổng tại epoch tốt nhất trong `history.json` = (k_vslgh + k_qipedc)/1295 cho mọi run, ví dụ 360: (899+21)/1295 = 71.04 = `val_best.top1`. `test_overall.top1` = độ chính xác tính từ `test_predictions.csv` (7/7). `video_id` của npz = của predictions (7/7). |
| 4f4e349 | PASS | JSON 360 có `command` và `git_commit 4bb3811` (commit 1 giây trước). `qipedc_kps360` có đủ 1622/1622 file của manifest. |

## Kiểm số độc lập (không qua report_step4.py)

Tính từ file đã commit (`metrics.json`, `history.json`, `test_predictions.csv`, fp32 của kernel):
- Balanced VAL: H-keepz (74.958+17.143)/2 = 46.05; H-dropz 43.74; H-keepz-360 47.77; seed43 47.66; notrim 46.33. Khớp REPORT §3.2.
- 4c trên 721 clip chung (`test_predictions.csv`): từ điển top-1 23, top-5 70; gộp top-1 88, top-5 185; n10=7, n01=72, `binomtest` p = 1.059e-14. Khớp REPORT §4.
- S06 top-1: H-keepz 936, notrim 940. Khớp §3.4(ii).
- Thời lượng kernel v3: 6573.6 s và "total 109.4 min". Khớp log.
- 1 clip QIPEDC VAL = 100/210 = 0.476. Khớp.

---

## Việc phải sửa (xếp theo mức độ)

**M1 (CAO, FAIL mục 13). Loại: thiết kế/tiêu chí (kế hoạch §3.4 không yêu cầu chẩn đoán độ khớp train) cộng triển khai (câu chữ PROPOSAL).**
1. `scripts/report_step4.py`: thêm vào mục 4c (và `step4_results.json`), lấy từ `history.json` của cả hai model: số epoch đã chạy, epoch tốt nhất, train top-1 ở epoch cuối, lr cuối, và số bước tối ưu ước lượng (clip train / batch × epoch). Sinh từ file, không gõ tay. Thêm test cho hàm này.
2. `PROPOSAL_4c.md`:
   - Nêu trong "Bằng chứng chống B / Giới hạn" rằng model từ điển chưa khớp tập train (số lấy từ REPORT mới). Vì vậy 4c chỉ cho thấy model tách train-từ-đầu bằng công thức hiện tại kém hơn; 4c không loại trừ phương án A.
   - Sửa câu "Tách ra thì 'Ký từ' mất toàn bộ dữ liệu VSL-GH" thành câu có phạm vi, vì A vẫn có thể khởi tạo từ trọng số VSL-GH hoặc model gộp rồi fine-tune trên QIPEDC.
   - Thêm vào "Điều gì sẽ làm đổi khuyến nghị": một model từ điển train tới khi khớp (cùng số bước, hoặc không giảm lr theo VAL 105 clip), hoặc khởi tạo từ trọng số VSL-GH, mà đạt ngang hay hơn model gộp trên 721 clip. Thí nghiệm này tốn GPU nên phải là kế hoạch mới.
   - Test AC5 phải vẫn qua.

**M2 (TRUNG BÌNH). Loại: thiết kế (PREREG không nói hệ quả).** REPORT §3.4 kết luận "cắt đoạn nghỉ KHÔNG được công nhận" nhưng không nói rằng run được chọn (`H-keepz-360`, `trim=true`) vẫn cắt nghỉ, và đường live sẽ phải cài `harmonize()` gồm cả bước cắt. Cần một câu sinh từ `chosen_run_config`. Có quyết định kèm theo, xem "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH".

**M3 (THẤP). Loại: triển khai.** Thăm dò (b): tỷ lệ "rơi vào lớp chỉ-VSL-GH" bị trộn với độ chính xác, vì dự đoán đúng thì tự nhiên rơi vào lớp của nguồn đó. Nên thêm cột "chỉ tính dự đoán sai". Reviewer tính từ `run_keepz_360/test_predictions.csv`: QIPEDC sai → lớp chỉ-VSL-GH 69/634 (10.9%); S06 sai → lớp chỉ-VSL-GH 183/225 (81.3%); tỷ lệ lớp chỉ-VSL-GH trong không gian nhãn 282/876. Kết quả này *ủng hộ* giả thuyết mạnh hơn bảng hiện tại, nhưng phải do script sinh ra thì REPORT mới được dùng.

**M4 (THẤP, quy trình).** Hoàn tất Bước 7–8: sinh lại REPORT với `--review-file`, ghi progress_log gồm số test trước/sau (53 → 53; test_report_step4 thêm 38), và chạy `detect-changes --scope all` thay cho `--scope staged`.

### Góp ý nhỏ (không chặn)
- Test AC5 (`test_every_number_is_in_report`) chỉ kiểm con số có mặt ở đâu đó trong REPORT. Số nguyên như "12" có thể khớp nhầm vào sha256 hex. Nên so theo ngữ cảnh, ví dụ cả cụm "% (k/n)".
- `REPORT_partial.md` đang **untracked**. Kế hoạch ghi "@3698e91" là sai (3698e91 chỉ sửa handoff). File này không có bản git để bảo đảm "giữ nguyên".
- Tiêu đề phần bổ sung trong PREREG ghi "12:30" nhưng commit `9b0ade1` lúc 12:13:24. Không sửa PREREG được. REPORT §5 đã in ngày commit; nên thêm một câu nêu điểm lệch này.
- Khối "Augmentation" trong REPORT §3.1 lặp chữ ("Augmentation: Augmentation (training only)").
- Nên thêm `reports/unified_run_*/**/*.pt` vào `.gitignore` (mục 11).

---

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **A/B cho 4c** (điểm dừng bắt buộc). Nên quyết sau khi PROPOSAL được sửa theo M1. Lý do: kết quả chính (12.2% vs 3.2%, p = 1.06e-14) là thật và theo đúng luật đăng ký, nhưng model từ điển dùng trong so sánh chưa khớp tập train. Có muốn một kế hoạch mới (tốn GPU) train model từ điển tới khi khớp hoặc khởi tạo từ VSL-GH trước khi chọn không?
2. **360 px**: theo luật thì được chọn (+1.72 điểm balanced VAL). Nhưng chênh giữa hai seed của cùng cấu hình H-keepz là +1.61 điểm, và run 360 chỉ có một seed. Chọn 360 kéo theo phải đổi đường realtime (giảm độ phân giải trước MediaPipe cộng test tương đương). Luật đã đăng ký được áp đúng; người dùng cần biết mức chắc chắn thấp trước khi duyệt thay đổi realtime.
3. **Cắt đoạn nghỉ** (M2): luật VAL không công nhận cắt nghỉ (−0.28), nhưng mọi run ứng viên đều cắt. Khi nối `harmonize()` vào đường live, giữ bước cắt (đúng với model đã train) hay bỏ (phải train lại)? PREREG không quy định.
