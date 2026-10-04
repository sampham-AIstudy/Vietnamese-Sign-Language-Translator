# Báo cáo phiên cloud 2026-10-04 — kế hoạch 15 Level 1: A2a → R1 → A2b → R2 → R3

**Trạng thái chung: MÃ XONG CẢ 5 BƯỚC, NHƯNG PHẦN CHẠY TRÊN DỮ LIỆU BỊ CHẶN** — environment cloud không có Kaggle credential thật
(`KAGGLE_KEY` = chuỗi mẫu `<API key Kaggle của bạn>` của docs/CLOUD.md, 24 ký tự; lỗi `'latin-1' codec can't encode character 'ủ'` — giống
hệt phiên cloud 2026-09-29). Không khôi phục được dữ liệu Level 1 ⇒ không có `pose_evidence.json`, không có `rearm_check_r3.json`, không có
số G1–G6, `rearm_check_r0.json` chưa sinh lại, `pose_change_rules` vẫn `false`. Không bịa số nào; mọi test thiếu dữ liệu được liệt kê là
ERROR/FAIL/skip, KHÔNG coi là pass.

- Nhánh: `cloud/2026-10-04-level1-rearm` (tách từ `feat/vslt-complete`, HEAD lúc nhận việc `3e6a15e`). Chỉ push nhánh này.
- Không sửa: `docs/STATE.md`, `docs/prompts/`, `.claude/`, kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`,
  `tests/test_backend_source_guard.py`, `src/data/alphabet_preprocessing.py`. Không train, không GPU, không đổi model mặc định.
- Chi tiết từng bước (impact, detect-changes, log đỏ/xanh, bảng): `docs/plans/15-progress.md` các mục A2a, R1, A2b, R2, R3 và "Nhật ký detect-changes".

## 1. STATUS từng bước

| Bước | STATUS | Commit | Còn thiếu (cần local có dữ liệu) |
|---|---|---|---|
| A2a | DONE (phần cloud) — CHỜ LOCAL kiểm AC-S18 | `b545ce7` (mã luật cắt đuôi vẫn ở WIP `dddfde8`, không viết lại) | AC-S18 trên clip thật; sinh lại `rearm_check_r0.json` (lệnh §5) |
| R1 | DONE (mã + 16 test) — CHỜ LOCAL kiểm AC-S18/S18b | `4c8c210` | AC-S18 + S18b (luật tắt bằng hệt 4a55bf0 trên mọi clip hauuto), AC-E1 |
| A2b | DONE (đủ: mã + config sinh lại, AC-W3 ĐẠT) | `71fc664` (mã), `4b5d736` (config) | — |
| R2 | BỊ CHẶN (mã + 11 test xong; không chạy được) | `263c10d` | chạy `--pose-evidence`, commit JSON, luật dừng P2, `--write-pose-config`, commit config |
| R3 | BỊ CHẶN (mã + 13 test xong; không chạy được) | `23563bc` | chạy với `--gates on:off`, commit JSON, nếu G1–G6 đạt thì `--write-rules-config`, commit config |
| Báo cáo | DONE | commit chứa file này | — |

CẦN PLANNER/REVIEWER xem (không chặn): (1) 2 assertion của test A2a do chính phiên này viết bị sửa ở R1 (mục 6.1); (2) đỏ tạm có chủ đích của
test cũ `test_r_prime_1d_write_config` giữa 2 commit A2b (mục 6.2); (3) nguy cơ G5 ở mối ghép 600 ms (mục 6.6).

## 2. Danh sách commit (đều đã push)
```
23563bc 15: R3 — code: covered one_rate, G6 clip đơn, gate G1–G6 đặt trước, --set/--gates/--write-rules-config + test (chưa chạy: thiếu dữ liệu)
263c10d 15: R2 — code: pose evidence (P1 jitter, P2 coverage) + --write-pose-config + test AC-RP1..RP4 (chưa chạy: thiếu dữ liệu)
4b5d736 15: A2b config reason — sinh lại bằng --write-config tại 71fc664 (value/source bằng hệt b0620a9, chỉ reason đổi)
71fc664 15: A2b — write_config: commit evidence lấy bằng git (không dự phòng gõ tay), reason theo quy tắc + test AC-W1..W3
4c8c210 15: R1 — luật re-arm theo tư thế (pose_change_rules, rearm_pose_dist, pose_distance) + AC-RA1..RA11
b545ce7 15: A2a — hoàn tất luật cắt đuôi (code ở dddfde8) + R0 ghi đúng commit config + sửa bảng R0 trong 15-progress
```

## 3. File đổi (`git diff --stat 3e6a15e..23563bc`, 12 file, +2158/−56; tất cả trong scope §3b/§5b)
- `src/inference/level1_segmenter.py` (R1: `pose_distance`, luật 1–3, 2 khóa mới trong `SEGMENTER_KEYS`, kiểm kiểu, xóa trạng thái tư thế ở `reset`/`_close_lost`)
- `src/inference/level1_core.py` (R1: kind `"bool"`, 3 khóa trong `CONFIG_SPEC`)
- `configs/level1_realtime.json` (R1: `pose_change_rules` false, `rearm_pose_dist` 1.0 giữ chỗ, `pose_over_jitter_ratio` 2.0, reason `rearm_move_ms`;
  A2b: reason 5 khóa hiệu chỉnh theo quy tắc — value/source không đổi)
- `scripts/level1_rearm_check.py` (A2a: `resolve_config_spec`/`FILL_RULES`, id clip bị loại; R1: điền khóa R1 cho config git cũ; R3: covered, G6, gate, `--set`, `--gates`, `--write-rules-config`)
- `scripts/level1_segment_report.py` (A2b: `committed_evidence_ref`, `CALIBRATION_REASONS`; R2: `hand_shape`, `longest_still_run`, `clip_pose_profile`, `pose_calibration`, `pose_report`, `write_pose_config`, CLI)
- Test MỚI: `tests/test_level1_rearm.py` (16), `tests/test_level1_pose_evidence.py` (11), `tests/test_level1_rearm_gates.py` (13).
  Test THÊM vào file cũ: `tests/test_level1_rearm_check.py` (+6 `TestConfigProvenanceA2a`), `tests/test_level1_segment_report.py` (+5 `TestWriteConfigA2b`),
  `tests/test_level1_segmenter.py` (+1 `test_s18b…`). Sửa test cũ: chỉ ngoại lệ R1 (PARAMS + bộ dựng config AC-S18 thêm 3 khóa) + mục 6.1.
- `docs/plans/15-progress.md` (A2a–R3, sửa bảng R0, nhật ký detect-changes), file này.

## 4. Test chạy thật trên cloud (Linux, Python 3.11.15, mediapipe 0.10.14, torch 2.6.0+cpu; KHÔNG có dữ liệu gitignored)

Mốc so sánh = cùng lệnh tại worktree sạch `b545ce7` trên cùng máy (`_work/_cloud/ac1_base_b545ce7.log`).

| Lệnh | Kết quả tại HEAD `23563bc` |
|---|---|
| 7 module Level 1 (lệnh §4 của prompt) | `Ran 112 tests — FAILED (failures=1, errors=5, skipped=19)` — toàn bộ do thiếu dữ liệu (dưới) |
| Guard chính `tests.test_backend_source_guard -v` | `Ran 28 — OK`, `[DoD7-guard] known=9 allowed=36`, `[scope] serving=45 main=60` (không đổi) |
| AC1-ngắn (19 module: 16 của B5 + textbox, segment_report, rearm_check) + 3 module mới | `Ran 328 — FAILED (failures=1, errors=5, skipped=43)`; mốc b545ce7 (19 module): `Ran 282 — FAILED (failures=1, errors=4, skipped=43)` |
| So từng test với mốc | KHÁC duy nhất: 45 test mới đều ok (16 RA + 11 RP + 13 R3 + 5 A2b) và `test_s18b…` mới ERROR (thiếu manifest). Mọi test có ở mốc giữ nguyên trạng thái. |
| R1 riêng `tests.test_level1_rearm` | đỏ trước (mã b545ce7): `Ran 16 — FAILED (failures=14, errors=6)` (RA1/RA4 `['hold'] != ['hold', 'hold']`); sau: `Ran 16 — OK` |
| A2a đỏ/xanh `tests.test_level1_segmenter` | tại 6067611: `Ran 23 — FAILED (failures=3, errors=1)` = S16 ×2 lưới + S17 FAIL, S18 ERROR thiếu dữ liệu; tại HEAD: S16/S17 ok, S18 ERROR thiếu dữ liệu |

1 FAIL + 5 ERROR còn lại (đều do thiếu file gitignored, KHÔNG phải pass):
`test_s18_all_hauuto_clips_identical_to_reference`, `test_s18b_rearm_pose_dist_unused_when_rules_off` (thiếu manifest.csv),
`test_td7_keys_1_to_5` (thiếu checkpoint), `test_r_prime_1b_motion_series_matches_segmenter_push` (thiếu manifest),
`test_r_prime_1a_per_class_counts` (ERROR) + `test_r_prime_1a_fold_top1_and_mean_match_report` (FAIL) (thiếu `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv`).
43 skip (thiếu manifest/npz, checkpoint, video hauuto, file U1) theo module: fingerspelling_deployed 9, level1_demo 17, level1_equivalence 6,
hand_live_equivalence 4, level1_core 4, fingerspelling_compose 2, hand_landmarks_ws 2, level1_segment_report 2, status_privacy 2, fingerspelling_api 1, level1_segmenter 1.
⇒ AC-S18/S18b, AC-E1, AC-C1, AC-D, AC-R'1a/b, AC-L **CHƯA được kiểm trên cloud**. Test chập chờn `test_hand_landmarks_ws … test_reset_segments_and_graphs`: ok ở mọi lần chạy.
Ghi chú: landmark trích trên Linux có thể lệch nhẹ Windows (docs/CLOUD.md §4) — phiên này không trích landmark nào.

## 5. Số liệu
- **R0 (cũ/mới):** `rearm_check_r0.json` CHƯA sinh lại (thiếu dữ liệu) ⇒ không có số mới. Số cũ (JSON tại 1acb4a5, sinh tại a3970a6) được chép LẠI BẰNG
  CODE vào 15-progress, sửa 4 chỗ chép tay sai: chuỗi T `n_clips` 35 → **70** (6 dòng); `current` L join 600 `garbage_per_clip` 0.0000 → **0.0104**;
  `before_a2` L join 600 `garbage_per_clip` 0.0000 → **0.0104** (prompt không nêu, phát hiện khi sinh lại bảng); `before_a2` L join 0 miss "(57.00%)" →
  0.5699 = 56.99%. Luật R0 không đổi kết luận: `current` L join 0/300 `one_rate` 0.3109 / 0.3731 < 0.90 (nguồn: JSON, `results.current.L`).
- Lý do 4 clip bị loại vì `min_detected_frames` (JSON `manifest_summary.excluded.min_detected_frames = 4`; thêm 8 `internal_hand_lost`, 628/640 clip dùng):
  cùng bộ lọc A1/AC-R1; clip < `min_detected_frames` khung có tay không thể tạo segment riêng ⇒ luôn "miss" không liên quan re-arm. Script nay liệt kê id.
- **A2b (AC-W3):** value 5 khóa sau `--write-config` == `git show b0620a9:configs/level1_realtime.json` (still_speed 2.5306153884920786, move_speed
  5.061230776984157, hold_ms 400.0, max_segment_ms 3543, tail_still_keep_ms 400.0 — đọc bằng code từ hai file); source `…tone_evidence.json@1ca53f3` lấy bằng git.
- **pose_evidence.json / rearm_pose_dist / P2 coverage: KHÔNG CÓ** (chưa chạy). **G1–G6: KHÔNG CÓ** (chưa chạy).
- sha256 checkpoint: KHÔNG kiểm được (file không có trên cloud); phiên này không đụng checkpoint.

## 6. Lệch kế hoạch / giả định (để reviewer quyết)
1. **Sửa 2 assertion của test A2a (viết trong chính phiên này ở b545ce7, chưa review)** khi làm R1: config 3ebc7b9 thiếu thêm 3 khóa R1 nên
   `FILL_RULES` của script R0 điền `pose_change_rules = false` (= hành vi trước luật, AC-RA6) và `rearm_pose_dist`, `pose_over_jitter_ratio` lấy từ
   `configs/level1_realtime.json` trên đĩa (không được bộ tách đọc khi luật tắt). Assertion đổi: `filled` mong đợi thêm đúng 3 khóa R1; vòng so giá
   trị bỏ qua đúng các khóa đã điền; test HEAD: `set(filled) == các khóa CONFIG_SPEC thiếu ở HEAD` (thay `== {}`, vốn đỏ trước mỗi commit thêm khóa).
   Không khóa nào bị nới. Không chấp nhận ⇒ hoàn tác 2 assertion, CẦN PLANNER.
2. **Đỏ tạm có chủ đích** của test cũ A2 `test_r_prime_1d_write_config` ở commit mã `71fc664` (assert reason sau ghi == reason trên đĩa; AC-W2 bắt ghi
   reason quy tắc) — hệ quả của thiết kế 2 commit 15-lan-sua-2 §7; test KHÔNG sửa, xanh lại ở `4b5d736`.
3. Lệnh sinh lại R0 dùng `--config before_a2=git:3ebc7b9:configs/level1_realtime.json` (đọc thẳng từ git, ghi `git_commit` đầy đủ + `filled`) thay
   cho file `_work/_plan15/config_before.json` chưa track (nguyên nhân `git_commit = ""`). Path chưa track/bẩn nay ghi `None`, không còn chuỗi rỗng.
4. R1 — quyết định nhỏ ngoài đặc tả: neo đặt mỗi khi luật hold kích hoạt kể cả khi segment bị bỏ vì ít khung; khung không tay ngắn không xóa
   `_pose_since` (đối xứng `_move_since`); thứ tự trong khung: still/move → luật 3 → luật 2 → re-arm chuyển động → re-arm tư thế → trim → phát;
   KHÔNG thêm khóa `rearm` tùy chọn vào `status()`; cửa sổ neo đóng hai đầu; `rearm_pose_dist` giữ chỗ = 1.0 (không đọc khi tắt).
5. R3: config `on` tạo bằng `--set on:pose_change_rules=true` trên config R2 đã commit (ghi `overrides` trong JSON) thay cho bản sao trong `_work/`;
   G6 dùng clip ≥ `min_detected_frames` của checkpoint (như AC-R1) thay cho "mọi clip, min_frames = min_sign_frames" của bộ dựng AC-S18;
   `label_agrees` cài đặt (báo cáo, cần checkpoint).
6. **Nguy cơ G5 (chỉ quan sát trên dữ liệu TỔNG HỢP của test, không phải số liệu):** với mối ghép nội suy chậm 600 ms, luật 3 có thể bắt đầu đồng
   hồ hold giữa mối ghép (quãng còn lại < `rearm_pose_dist`) và segment bắt đầu ở `_pose_since` ⇒ segment đa số khung "join" ⇒ tính là rác. Đã trace:
   đúng chữ §3.2, không phải lỗi cài đặt. Nếu G5 trượt trên dữ liệu thật ⇒ điểm DỪNG của R3 (báo planner, không nới gate).
7. Môi trường: venv cloud thiếu `seaborn` (có trong requirements.txt, thiếu trong `scripts/cloud_setup.sh`) ⇒ 6 module backend lỗi import; đã cài
   `seaborn 0.13.2` vào `.venv`. GitNexus chạy qua `npx -y gitnexus@latest analyze` (đầu phiên) + `node .gitnexus/run.cjs` (impact, detect-changes);
   lệnh analyze sinh thư mục chưa track `.claude/skills/gitnexus-*`, `.agents/skills/gitnexus-*` — KHÔNG commit (thêm vào `.git/info/exclude` cục bộ).

## 7. Dữ liệu đã khôi phục
KHÔNG có. Nguồn dự kiến (prompt §1): kernel `phmvnsm33/vsl-extract-alphabet` (688 file landmark), dataset `hauuto/vietnamese-sign-language-alphabet`,
dataset PRIVATE `phmvnsm33/vslt-provenance-artifacts` (checkpoint, sha256 `a6311820…5b708a2`). `www.kaggle.com` truy cập được qua proxy (HTTP 200)
nhưng thiếu key thật. Không thử đường vòng (tự trích landmark / tải ẩn danh) vì sẽ cho dữ liệu khác nguồn kế hoạch.
**Người dùng cần:** đặt `KAGGLE_KEY` thật trong cấu hình environment cloud (không dán vào chat/repo); phiên MỚI sẽ nhận biến này.

## 8. Việc chưa làm — thứ tự cho local (hoặc phiên cloud mới có key), mỗi bước tại commit sạch, `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`
1. Kiểm A2a + R1 trên dữ liệu: `python -m unittest tests.test_level1_segmenter -v` (AC-S18, S18b) + `tests.test_level1_equivalence` (AC-E1) + 7 module
   Level 1 + `tests.test_level1_rearm tests.test_level1_pose_evidence tests.test_level1_rearm_gates` + AC1-ngắn → 0 lỗi, 0 skip. S18/S18b đỏ ⇒ DỪNG.
2. Sinh lại R0 tại `b545ce7` (trước khi R1 thêm khóa): `git worktree add <tmp> b545ce7` rồi trong đó
   `python scripts/level1_rearm_check.py --config current=configs/level1_realtime.json --config before_a2=git:3ebc7b9:configs/level1_realtime.json --join-ms 0,300,600 --out reports/level1_realtime_2026-10-04/rearm_check_r0.json`
   (sau R1 vẫn chạy được tại HEAD nhờ `FILL_RULES`, nhưng config `current` khi đó có thêm 3 khóa) → so số cũ/mới, ghi 15-progress, commit JSON.
3. R2: `python scripts/level1_segment_report.py --pose-evidence --out reports/level1_realtime_<D>/pose_evidence.json` → `code_dirty` false → commit;
   mã thoát 2 (P2 coverage < 0.80) ⇒ DỪNG. Rồi `python scripts/level1_segment_report.py --write-pose-config configs/level1_realtime.json --pose-evidence-json reports/level1_realtime_<D>/pose_evidence.json` → commit `15: R2 config`.
4. R3: `python scripts/level1_rearm_check.py --config off=configs/level1_realtime.json --config on=configs/level1_realtime.json --set on:pose_change_rules=true --gates on:off --join-ms 0,300,600 --out reports/level1_realtime_<D>/rearm_check_r3.json`
   → commit JSON; mã thoát 3 (gate trượt) ⇒ DỪNG, ghi số. Đạt: `python scripts/level1_rearm_check.py --write-rules-config configs/level1_realtime.json --rearm-json reports/level1_realtime_<D>/rearm_check_r3.json`
   → test Level 1 + AC-E1 → commit `15: R3 config` → báo người dùng U1c.
5. Sau đó (ngoài phiên này): U1c, A3, C1; review toàn bộ bởi vslt-reviewer (kế hoạch 15 + 3 phụ lục + danh sách commit ở mục 2).
