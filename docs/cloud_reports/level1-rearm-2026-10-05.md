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
