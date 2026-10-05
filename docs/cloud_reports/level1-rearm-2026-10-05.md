# Báo cáo phiên cloud 2026-10-05 — kế hoạch 15: chạy R0/R2/R3 trên dữ liệu thật

**Trạng thái chung: DỪNG Ở R2 theo luật P2 (coverage 0.3783 < 0.80) — CẦN PLANNER.** R3 không chạy, `pose_change_rules` vẫn false.

| Bước | STATUS | Commit | Ghi chú |
|---|---|---|---|
| Khôi phục dữ liệu | DONE | — (không commit dữ liệu) | 686 npz + manifest; checkpoint sha256 `a6311820…5b708a2` khớp; 640 video hauuto; 46 video QIPEDC chữ cái |
| Kiểm A2a/R1 trên dữ liệu | DONE | — | 11 module `Ran 161 — OK (skipped=7)`; AC-S18, S18b, E1 xanh; guard chính `known=9 allowed=36` OK |
| R0 sinh lại | DONE | `a66ea13` | `current` không đổi; `before_a2` L join 600 đổi nhẹ (do luật A2a); kết luận R0 giữ nguyên |
| R2 | DỪNG (P2) | commit chứa `reports/level1_realtime_2026-10-05/pose_evidence.json` | `rearm_pose_dist` = 0.6919; coverage 0.3783 (3193 cặp) |
| R3 | KHÔNG CHẠY | — | dừng sau R2 theo prompt |

Chi tiết số liệu + lệnh: `docs/plans/15-progress.md` mục "Phiên cloud 2026-10-05".
Skip còn lại: `test_u1_summary` (file U1 chỉ có ở máy local). Landmark trích trên Linux, so hai đường trên cùng máy.
Không sửa test, gate, model mặc định; không train.

## Lượt 3 — coder lần sửa 4 (K1 → D1 → D2 → D3 → D4), 2026-10-05

**Trạng thái: DỪNG ở D4 theo 15-lan-sua-4 §7 mục 2 — chỉ G6 nhóm dấu thanh trượt — CẦN NGƯỜI DÙNG chọn (a) hoặc (b).** `rearm_mode` vẫn
"motion_pose"; phím `n` "chữ kế" dùng được ngay khi demo.

| Bước | STATUS | Commit | Ghi chú |
|---|---|---|---|
| Khôi phục dữ liệu | DONE | — (không commit dữ liệu) | 686 npz + manifest; sha256 checkpoint `a6311820…5b708a2` khớp; 640 mp4 hauuto; 46 video QIPEDC |
| K1 phím n | DONE | `9462f95` | `force_rearm` + `KEY_ACTIONS[n]` + HUD + nhật ký; AC-K1…K4 |
| D1 bộ giải mã | DONE | `12bd961` | `WindowBuffer`, `Level1LabelDecoder`, `VARIANT_BASE`, 4 khóa config (`rearm_mode` motion_pose), `Speller.on_label`; AC-D1…D9 |
| D2 app | DONE | `c8a2744` | chế độ classifier trong `level1_demo.py` (headless đồng bộ, worker việc mới nhất, chặng `window_classify`); AC-A1…A3 + K3 |
| D3 script | DONE | `1ab5d7b` | `level1_rearm_check.py --decoder`, gate §5.1, G7, `--write-mode-config`; AC-C1…C5 |
| D4 gate | DỪNG (§7 mục 2) | `a58df71` (JSON) | G1–G5 + G6 chữ cái ĐẠT; G6 dấu thanh 0.80 < 0.85 − 0.02 |

Số G1–G7 (đọc từ `reports/level1_realtime_2026-10-05/rearm_check_d4.json`, sinh tại `1ab5d7b`, `code_dirty` false; chuỗi ghép từ clip train —
kiểm logic, không phải độ chính xác; tham số decoder chọn sau thăm dò planner trên cùng chuỗi L):
- G1 L one_rate join 0 / 300: 0.9793 / 0.9689 (≥ 0.90) ĐẠT. G2 L multi_rate: 0.0 ở cả 3 join ĐẠT. G3: 0 lần phát cần mất tay (L/T/O × 3) ĐẠT.
  G4 order_ok ĐẠT. G5 L rác join 300 / 600: 0.0363 / 0.0311 (≤ 0.05) ĐẠT.
- G6 clip đơn, đúng 1 phát: chữ cái on 0.9593 vs off 0.8798 ĐẠT; **dấu thanh on 0.8000 vs off 0.8500 TRƯỢT** (cần ≥ 0.83).
- G7 QIPEDC (chỉ báo cáo, 46 clip một người ký ngoài train): phát nhãn trọn clip on 0.5435 vs off 0.7391; phát đúng ký hiệu on 0.5435 vs off 0.5652.
- Đối chiếu (báo cáo): L one_rate của config hiện hành cùng thước đo chặt 0.2332 / 0.2591 / 0.2280.

Test thật (unittest, không có pytest trong `.venv`): 12 module Level 1 (segmenter, rearm, decoder, rearm_check, rearm_gates, segment_report,
pose_evidence, core, demo, guard, textbox, equivalence) `Ran 208 — OK (skipped=1)` tại `1ab5d7b` (skip = `test_u1_summary`, file U1 chỉ ở local);
AC1-ngắn còn lại `Ran 167 — OK`; guard chính `known=9 allowed=36`. `test_hand_landmarks_ws.TestReset` chập chờn đã biết: 1 lần FAILED ở lượt K1,
chạy riêng 3 lần FAILED / OK / OK; các lượt sau OK. AC-S18/S18b, AC-E1/E3, K4, A2 (bằng hệt) xanh. Landmark trích trên Linux, so trên cùng máy.

Lệch kế hoạch / giả định (chi tiết ở `docs/plans/15-progress.md` mục "Lần sửa 4 — coder"):
- GitNexus không chạy được (tải `npx gitnexus` bị chặn) ⇒ impact bằng text search, detect-changes bằng `git diff --stat`.
- Ngoại lệ test cũ: `test_git_spec_records_full_commit_sha_and_fill` thêm 4 khóa D1 vào dict khóa điền mong đợi (cùng kiểu R1) — reviewer xem.
- D2 và D3: mã viết trước test trong phiên; log đỏ ghi bằng cách cất mã (`git stash`) rồi chạy test mới.
- Diễn giải luật 1 decoder: khung có tay mà chưa có kết quả cửa sổ (thiếu khung / bị worker bỏ) không cắt chuỗi chạy (giống analyze5.py).
- Chặng `window_classify` chỉ có trong JSON ở chế độ classifier (test AC-L cũ khóa danh sách chặng ở motion_pose); `emit_to_token` chưa đo cho nhãn.
- Chưa làm: `--write-mode-config` (chờ người dùng chọn), U1c, A3, C1 (cần webcam / người dùng, làm ở local).

**Cập nhật sau quyết định:** người dùng chọn (a) Classifier. Bật thử trên config mặc định làm 5 test CŨ đỏ (AC-D2 ×2, AC-L ×3 khóa hành vi
motion_pose của config mặc định) ⇒ điểm dừng §7 mục 3, CẦN PLANNER chốt cách bật (a). Config giữ "motion_pose"; demo tạm dùng `--config` với bản
sao đặt `rearm_mode` = "classifier". Chi tiết: 15-progress mục D4.
