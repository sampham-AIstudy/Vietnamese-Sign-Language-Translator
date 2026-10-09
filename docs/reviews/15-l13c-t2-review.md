# Review 15 — lần sửa 13c, bước T2 (L13-U2t2)

- Reviewer: vslt-reviewer (độc lập), 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `2718b36`.
- Phạm vi review: `b5762ec` (test, code bởi agy, orchestrator commit hộ) + `3a07a8c` (kết quả đột biến AC-T2m, cầu nối) + `a32d6a4` (sổ agy, commit riêng).
- Hợp đồng: `docs/plans/15-lan-sua-13c.md` §4 hàng T2 (:95), AC-T2 (:227–252), AC-T2m (:254–264), AC-P, §5b (:283–296), §7.
- Nguồn đột biến sống: `docs/reviews/15-l13-u2b-review.md` (m5, m6), `docs/reviews/15-l13-u2c-review.md` (m4, m5, m6).

## Kết luận: APPROVE

Không có FAIL. Có 3 vấn đề THẤP (quy trình/ghi chép), không chặn.

## Bảng kiểm 1–13

| # | Mục | KQ | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | Lớp mới `tests/test_level1_demo.py:3652-3770` (`TestWindowAndFullscreenU2t2`), 4 test khớp AC-T2. W1a (:3656): `getWindowImageRect` = `_window_rect_raises`, view 480×640 bất đối xứng (gradient ngang + khối 100×100 góc trên trái), `tov, small = app._hud_lines()[:2]`, hold 0.6, stats 1 dòng; `array_equal(out, hud.compose(view.copy(), …))` và có pixel `(0,200,0)`. W1b (:3681): rect `(0,0,1920,1080)`, `ph = panel_height(tov, small, 1)`, `L = fit_layout(640,480,ph,rect)`, so vùng camera với `cv2.resize(view,(L.content_w, L.cam_rect[3]), INTER_LINEAR)` + pixel `(0,200,0)`. F1 (:3709): `run()` không `--fullscreen`, keys `[f,f]`; giá trị `[WINDOW_FULLSCREEN, WINDOW_NORMAL]`, thuộc tính `[WND_PROP_FULLSCREEN]*2`, `len(resized)==2`, sự kiện `[True, False]`. L1 (:3730): px 30..38 (font_px = px, không trùng px 20 của scale 1.0), A1..A8, A1 (không dựng mới), A9, rồi A1 (không dựng mới) và A2 (dựng mới), `len(_fonts) ≤ 8` mọi bước — chặt hơn AC (lần gọi A1 sau A9 là chỗ bắt FIFO). Oracle do test tự đặt; dùng `Hud.compose`/`fit_layout` của app đúng như AC-T2 quy định. `_ScaledWindowRecorder` (:3261), `_FullscreenRecorder` (:3446) không bị sửa (diff chỉ có dòng thêm sau :3649). |
| 2 | Tự chạy lại test | PASS | `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_demo.TestWindowAndFullscreenU2t2 tests.test_level1_display -v > _work/_plan15_l13/review_t2_green.log` ⇒ `Ran 36 tests in 24.420s` `OK`, 4 test U2t2 đều `... ok`, 0 dòng chứa "skip". Khớp coder (`l13c_t2_green.log`: Ran 4 OK; `l13c_t2_display.log`: Ran 32 OK). Toàn bộ level1: dùng log orchestrator `l13c_t2_level1_all.log` (`Ran 543 … OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`), không chạy lại (theo lời giao). |
| 3 | Test không bị sửa/skip/nới; agy guard | PASS | `git show --numstat b5762ec`: `120 0 tests/test_level1_demo.py`. Dòng thêm khớp `skip/xfail/expectedFailure`: DUY NHẤT `+@unittest.skipUnless(not _MISSING, SKIP_REASON)` (:3652). Số decorator này: 25 trước → 26 sau (cùng mẫu lớp sẵn có; AC-T2 :227 bắt buộc). `_MISSING` rỗng trên máy này (lớp chạy, Ran 4 không skip). BLOCK của agy-guard (`_work/agy_logs/20261009-194636-15-lan-sua-13c.log:20` "thêm skip/xfail") là dương tính giả do regex `SKIP_ADDED` (`scripts/agy_guard.py:34`) khớp mọi `unittest.skip`. agy KHÔNG lách bằng `--no-verify`: dừng, báo `STATUS: CẦN PLANNER` (:68) — đúng thực tế (commit bị chặn). Cuối log: `[agy-guard] các commit của agy: sạch` (:70), `working tree: sạch` (:71). Orchestrator commit hộ, ghi lý do trong thông điệp commit; hiện `.git/hooks` không có `pre-commit`, `core.hooksPath` trống. |
| 4 | Nguồn gốc dữ liệu | PASS (N/A) | Không dữ liệu mới; clip D2 `CLIP` (:31) chỉ đọc. |
| 5 | Rò rỉ | PASS (N/A) | Không train/split. |
| 6 | VAL/TEST | PASS (N/A) | Không chọn model. |
| 7 | Số liệu truy được; hash; sổ agy | PASS | Số trong progress (Ran/thời gian) có log `_work/_plan15_l13/l13c_t2_{green,display,level1_all,mut_*}.log`, khớp từng dòng. Mọi hash ở dòng thêm của b5762ec/3a07a8c (`93abb08`, `b5762ec`) và hash liên quan (`3a07a8c`, `d4e71dc` = `l13c_t2_base.txt`, `235be2b`, `6be8815`, `a32d6a4`) đều `git cat-file -t` = `commit`. Sổ agy: `docs/agy_usage_ledger.csv` dòng `2026-10-09T13:07Z,gemini,gemini-3.8-flash-high,high,…15-lan-sua-13c.md…,ok` (effort high), commit riêng `a32d6a4`. Không dùng số sổ làm kết luận. |
| 8 | Cỡ mẫu | PASS (N/A) | Không có kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS | `git diff --stat 93abb08..HEAD -- level1_demo.py src/` rỗng; `git diff 2718b36 -- tests/ level1_demo.py src/` rỗng. |
| 10 | Không mock/giả trong đường chính | PASS | Mock chỉ trong test (`mock.patch.multiple(app_mod.cv2, …)`); app không đổi. |
| 11 | Bảo mật; phạm vi; push | PASS | Không bí mật mới. Commit T2 chỉ `tests/test_level1_demo.py` + `docs/plans/15-progress.md` (⊆ scope §5b, đúng danh sách T2). Không đụng README.md, 3 file ` D`, untracked của người dùng. Không push: `origin/cloud/2026-10-04-level1-rearm` = `deada7f`, `git branch -r --contains b5762ec` rỗng. |
| 12 | So sánh công bằng / GATE | PASS (N/A) | Không đổi tiêu chí; AC-T2m chạy đủ 5 đột biến như đặt trước. |
| 13 | Kết luận vượt bằng chứng | PASS (ghi chú THẤP-1) | Câu "detect-changes Clean" trong progress/log agy không có log đi kèm. |

## Đột biến (AC-T2m)

- Script `_work/_plan15_l13/t2_mutate.py` định nghĩa đúng 5 đột biến: b5 (`compose(…, 0.0, …)` ở nhánh fallback `_window_image`, `level1_demo.py:1349`), b6 (`render_to_window(view[:, ::-1], …)`, :1350), c4 (xóa `self._fonts.move_to_end(px)`, :520), c5 (`prop = cv2.WINDOW_FULLSCREEN`, :1104), c6 (xóa `if self.fullscreen: self.window_sized = False`, :1109-1110); mỗi chuỗi `assert count == 1`; worktree `wt_13c_t2` từ `b5762ec`, khôi phục và xóa trong `finally`.
- Log cầu nối: base `Ran 4 … OK`; b5 FAIL `test_w1a…`; b6 FAIL `test_w1b…`; c4 FAIL `test_l1…`; c5, c6 FAIL `test_f1…` — khớp progress (3a07a8c).
- Reviewer tự chạy lại trong worktree tạm `_work/_plan15_l13/wt_rev_t2` (từ `b5762ec`, junction `data/external`, `checkpoints`), log `_work/_plan15_l13/review_t2_mut_{base,c4,c6,b6}.log`:
  - base: `Ran 4 tests in 2.946s` `OK`;
  - c4: `FAILED (failures=1)` — `test_l1_font_lru_mru_retention_and_eviction`;
  - c6: `FAILED (failures=1)` — `test_f1_fullscreen_toggle_properties_and_resizes`;
  - b6: `FAILED (failures=1)` — `test_w1b_window_image_scaled_layout`.
  - Đã gỡ junction (dữ liệu gốc còn nguyên: `data/external/`, `checkpoints/alphabet_best.pt`) và `git worktree remove`; `git worktree list` chỉ còn cây chính.

## Vấn đề (theo mức)

Không có CAO/TRUNG BÌNH.

- **THẤP-1 (quy trình, AC-P / §3.2 U2c THẤP-5).** Thiếu `_work/_plan15_l13/l13c_t2_impact.log` và `l13c_t2_detect.log` (C1, T1 có). Kết quả impact/detect chỉ có trong lời kể của agy (`…194636….log:44-45`, progress) nên không kiểm được; câu "detect-changes: Clean" khó đúng khi working tree đang có thay đổi chưa commit. Tác động thấp (chỉ thêm test, không chạm symbol). Đề nghị: orchestrator chạy `detect-changes --scope compare --base-ref d4e71dc` lưu `l13c_t2_detect.log`, hoặc ghi nhận thiếu vào progress.
- **THẤP-2 (quy trình, AC-P "đúng 1 commit mỗi bước").** Có 2 commit khớp `^15: L13-U2t2 ` (`b5762ec` mã, `3a07a8c` chỉ progress của cầu nối). Nội dung hợp lệ (ghi kết quả AC-T2m), nhưng lệch chữ AC-P; T1 cũng có commit thứ hai (`d27e507`). Đề nghị: chấp nhận và ghi nhận; từ G1 dùng tiền tố khác (vd. `docs: …`) cho commit ghi kết quả của cầu nối.
- **THẤP-3 (ghi chép).** `docs/plans/15-progress.md:11` vẫn "ĐANG LÀM: T2 (13c)", dòng "Xong … Lần sửa 13/13c" chưa có T2; orchestrator cập nhật khi đóng T2 (`T2 (b5762ec + 3a07a8c)`). Regex `SKIP_ADDED` của agy-guard báo nhầm với `skipUnless(not _MISSING…)` bắt buộc — đã có trong backlog (`2718b36`), không thuộc T2.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có cho T2. (VU ở §7 kế hoạch 13c vẫn mở, không chặn.)
