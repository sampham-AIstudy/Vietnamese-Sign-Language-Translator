# Review 15 — L13d G2b (commit mã `342326e`, tiến độ `2d77deb`)

Reviewer độc lập, 2026-10-10. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `a58d372`. Coder: vslt-coder-claude (không phải agy ⇒ mục kiểm agy không áp dụng).
Hợp đồng: `docs/plans/15-lan-sua-13d.md` §4 hàng 5b, §5 G2b (AC-G4, AC-D7, AC-D8, AC-G5 grep, Chung); `docs/plans/15-lan-sua-13e.md` §3 (a), §5 AC-E1…E4, §5b;
gốc `docs/plans/15-lan-sua-13.md` §9 AC-G4…G5. Mốc so: `48b00d0`.

**Kết luận: APPROVE.** 0 FAIL, 0 vấn đề CAO/TB, 3 vấn đề THẤP (ghi nhận, không chặn G2c), 2 ghi chú cho G2c.

## Lệnh reviewer tự chạy (PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python)

| Lệnh | Log | Kết quả |
|---|---|---|
| `PY -m unittest tests.test_level1_core tests.test_level1_gestures tests.test_level1_display` | `_work/_plan15_l13/review_g2b_cgd.log` | `Ran 161 tests in 32.589s` `OK` (0 skip ⇒ AC-G4 chạy thật) |
| `PY -m unittest -v tests.test_level1_gestures.TestLegacyFlatHandOnHauutoAcG4 tests.test_level1_display.TestRenderToWindowAcU2` | (stdout) | `Ran 10`: `test_g4_default_call_equals_the_design_values` ok, `test_m0_ref_loader_compat_is_temporary` ok, `test_u2_hud_scale_one_identical_to_m0_hud` ok |
| Lệnh AC-E3 toàn bộ: mọi `tests.test_level1_*` + `tests.test_backend_source_guard` | `_work/_plan15_l13/review_g2b_level1_all.log` | `Ran 615 tests in 619.934s` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` — khớp coder (`g2b_e_green_level1_all.log`: Ran 615, OK skipped=1) |
| `PY -m unittest -v tests.test_level1_segment_report` | (stdout) | skip duy nhất = `test_u1_summary`: "U1 file .../_work/_plan15_u1/u1_2026-10-03_1650.json not found" (`tests/test_level1_segment_report.py:244-247`, có từ `4f913a2`; thiếu file `_work` gitignored; có tên file) |
| Đột biến M9 trên worktree tạm `_work/_plan15_l13/wt_review_g2b` từ `342326e`: dòng `delattr(m0_core, m0_name)` → `pass`; `PY -m unittest tests.test_level1_display` | `_work/_plan15_l13/review_g2b_M9.log` | `Ran 33` `FAILED (failures=1)`: `test_m0_ref_loader_compat_is_temporary` ⇒ ĐỎ |
| Đột biến M10 (cùng worktree): thêm `GESTURE_BACKSPACE_FLASH = 600.0` trước `GESTURE_BACKSPACE_DEFAULT`; `PY -m unittest tests.test_level1_gestures tests.test_level1_display` | `_work/_plan15_l13/review_g2b_M10.log` | `Ran 104` `FAILED (failures=2, skipped=1)`: `test_g5_no_removed_constant_left` + `test_m0_ref_loader_compat_is_temporary` ⇒ ĐỎ |
| Khôi phục + gỡ worktree | — | `git checkout --` sau mỗi đột biến ⇒ `git status --short` 0 dòng trong worktree; `git worktree remove` + `prune`; `git worktree list` chỉ còn cây chính |
| `sha256sum checkpoints/alphabet_best.pt` | — | bắt đầu `160e0c68` (không đổi) |
| Đếm khung AC-G4 (script chỉ đọc) | (stdout) | 10 clip hauuto (chữ a ×4, 6 clip chữ có dấu), 747 khung có tay; mặc định trả True ở 1 khung |

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch; test thật | PASS | AC-G4 `tests/test_level1_gestures.py:1062-1084` (10 dòng hauuto đầu theo thứ tự manifest `:913-920`; `aspect_points(raw[i], w, h)` như `level1_demo.py:1282`; so mặc định với `DESIGN_TABLE` (0.5, 1.05) và với config; `assertGreater(n_frames, 0)`). AC-D7 `:946-966` (hằng AST ⊆ {0,1,2,3,4,9,12,17,21,1000}; mặc định `None`, có `assertTrue(defaults)` chống rỗng). AC-D8 (a) `:986-1000`, (b) `:1002-1032` (patch `GESTURE_CONFIG_PATH` + `cache_clear`, khôi phục `addCleanup`; thêm nhánh file hỏng/thiếu ⇒ ValueError/OSError), (c) `:1034-1040` (tiến trình con, `currsize == 0`). AC-G5 grep `:1043-1057`. AC-E2 `tests/test_level1_display.py:356-375` đủ (i)–(v), thêm tiền điều kiện "tên đã bị xóa". 8 đột biến coder + M9/M10 đều ĐỎ (log coder `g2b_mutate.log`, `g2b_e_mutate.log`, 10 log `g2b_mut_*` đều `FAILED`, base `OK`); reviewer chạy lại M9, M10: ĐỎ. |
| 2 | Tự chạy lại test | PASS | Bảng lệnh trên; Ran 615 OK skip 1 khớp coder; core+gestures+display Ran 161 OK. |
| 3 | Test không bị sửa/skip/xóa/nới | PASS | `git diff --numstat 48b00d0..342326e -- tests/`: `31 0 tests/test_level1_display.py`, `204 0 tests/test_level1_gestures.py`. `-U0` display: đúng 4 hunk thêm `@@ -34,0 +35` (hằng), `@@ -66,0 +68,7` và `@@ -70,0 +79,2` (thân `_hud_module_at`), `@@ -345,0 +356,21` (test mới) ⇒ AC-E1 đạt. `test_u2_hud_scale_one_identical_to_m0_hud` (`:334-347`) không đổi, vẫn `np.array_equal` trên mọi tổ hợp compose + `_build` 3 độ rộng. Skip mới duy nhất = lớp AC-G4 `@unittest.skipUnless(not _MISSING, SKIP_REASON)` (`SKIP_REASON` liệt kê đường dẫn thiếu) — hợp đồng cho phép; trên máy này không skip. |
| 4 | Nguồn gốc dữ liệu | PASS | AC-G4 dùng npz MediaPipe thật (`manifest.csv`: `mp.solutions.hands`, `0.10.14`), chỉ kiểm bằng nhau, không huấn luyện/đánh giá. Chuỗi tổng hợp khác có docstring "chuỗi tạo có kiểm soát" (`:31-33`). |
| 5 | Rò rỉ split | PASS (không áp dụng) | Không đổi dữ liệu/split/model. |
| 6 | VAL/TEST | PASS (không áp dụng) | Không chọn model, không chạy TEST. |
| 7 | Số liệu truy được | PASS | Mục G2b cuối `docs/plans/15-progress.md` (2d77deb): mọi số (Ran 33/322/615, đột biến, sha) trỏ log trong `_work/_plan15_l13/`; reviewer grep đối chiếu: red `Ran 33 FAILED (errors=2)`; green display `Ran 33 OK`; 13d `Ran 322 OK`; all `Ran 615 OK (skipped=1)`, `known=9 allowed=36`. Không có số khoa học. |
| 8 | Cỡ mẫu/CI | PASS (không áp dụng) | Không có kết luận thống kê. Xem THẤP-1 về độ phân biệt của AC-G4. |
| 9 | Nhất quán train–realtime | PASS | Giá trị đọc lười = hằng cũ: config `legacy_flick_cooldown_ms 400, window_ms 250, min_dx 0.05, min_speed 0.3, palm_ratio 0.35, dx_over_dy 1.1, min_dt_s 0.04`, `flat_thumb_min_ratio 0.5, flat_thumb_max_spread 1.05`, `gesture_flash_ms 600` = hằng/số trần tại `48b00d0:src/inference/level1_core.py:548-552, 556-557, 653, 661-663`; ép `float` (`_gesture_default`, `src/inference/level1_core.py:568-570`) như hằng cũ. Biểu thức so trong `update` giữ nguyên dạng (`:679, 687-689`). `level1_demo.py` không đổi tiền xử lý (`aspect_points` `:1282`). `BackspaceGestureTracker()` dựng trong `Level1App.__init__` (`level1_demo.py:898`) ⇒ config hỏng lộ ngay lúc khởi động. Người gọi khác: chỉ `level1_gestures.py:379` truyền tham số tường minh (không đổi hành vi). |
| 10 | Không random/mock/hard-code | PASS | Không còn số trần cử chỉ trong `is_flat_hand_backspace`/`BackspaceGestureTracker` (AC-D7 xanh; đột biến bare đỏ). grep AC-G5 trên `src/ level1_demo.py` = 0 dòng; không có `__getattr__`/`globals()`/getattr theo tên động/alias/ghép chuỗi trong `level1_core.py` né AC-G5. `GESTURE_BACKSPACE_DEFAULT` còn (`:552`). `mock` chỉ trong test. |
| 11 | Bảo mật | PASS | Không token/khóa; không file dữ liệu mới được commit; không đụng `backend/`. Thay đổi chưa commit của người dùng (`README.md`, 3 file bị xóa) nguyên trạng. |
| 12 | So sánh công bằng / gate | PASS | AC-G5 giữ đủ 5 tên (không chọn (b)); `M0_CORE_COMPAT_NAMES` đúng 1 tên; `HUD_BASE_COMMIT` vẫn `cad8cdc`; không thêm ALLOWED/KNOWN (`known=9 allowed=36`). |
| 13 | Kết luận vượt bằng chứng | PASS | Mục tiến độ chỉ khẳng định điều log chứng minh; ghi rõ AC-G4 skip trong worktree đột biến. Giả định (2) "AC-E2 (v) chặt hơn AC" đúng (đệ quy vào code object lồng). |

Phạm vi: `git diff --name-only 48b00d0..a58d372` = 4 file mã/test trong khối `scope` của 13e + `docs/plans/15-progress.md`; `docs/STATE.md`, `docs/usage_ledger.csv`
thuộc commit orchestrator `a58d372`. Đúng 1 commit `^15: L13-G2b` (`342326e`); commit tiến độ `2d77deb` không mang tiền tố. `level1_demo.py` chỉ đổi import (`:92-93`)
và 2 chỗ flash (`:1160`, `:1528`) — đúng "CHỈ" của 13d.

Shim (13e §3 ràng buộc 1): sau `sys.modules[name] = mod`, trước `try:` (`tests/test_level1_display.py:68-74`); chỉ gắn khi `not hasattr` (ở HEAD trước G2b là no-op);
giá trị `float(m0_core.gesture_defaults()["gesture_flash_ms"])`; `delattr` đúng các tên đã gắn trong `finally` (`:79-80`); chú thích 1 dòng đúng văn bản yêu cầu.
Kiểm thêm: ở `cad8cdc`, `GESTURE_BACKSPACE_FLASH` chỉ dùng tại `level1_demo.py:1065, 1404` (thuộc `class Level1App` từ `:728`); lớp `Hud` nằm `:453-599` ⇒ tên được
cấp không tham gia phép so Hud.

## Vấn đề (theo mức)

**CAO / TB:** không có.

**THẤP-1 — AC-G4 gần như chỉ kiểm phía False.** Trên 747 khung có tay của 10 clip hauuto đầu, mặc định trả True ở đúng 1 khung ⇒ phép so
`is_flat_hand_backspace(p) == is_flat_hand_backspace(p, 0.5, 1.05)` ít sức phân biệt ở phía True. Đúng nguyên văn hợp đồng (10 clip hauuto ĐẦU), không chặn;
việc đọc đúng khóa `flat_thumb_*` đã được AC-D8b (`test_d8b_flat_thumb_defaults_come_from_the_file`) và đột biến `thumb_*_default` che. Không cần sửa.

**THẤP-2 — shim chạy trước `try:`.** Nếu `gesture_defaults()` ném lỗi (config thiếu/hỏng) thì `sys.modules[name]` của module tham chiếu không được gỡ
(`tests/test_level1_display.py:67-74`). Vị trí do 13e §3 quy định; khi config hỏng nhiều test khác cũng đỏ, nên chỉ là rác trong tiến trình test. Không cần sửa.

**THẤP-3 — AC-E2 (v) chỉ phủ `Hud.compose`/`Hud._build`.** Phương thức phụ khác của `Hud` (nếu có gọi) không bị kiểm `co_names`. Hiện an toàn (kiểm tay ở
`cad8cdc` như trên) và `HUD_BASE_COMMIT` cố định nên tập này không đổi. Không cần sửa.

## Ghi chú cho G2c

1. `level1_demo.py:1160, 1528` đọc flash từ `gesture_defaults()` (đường dẫn cố định `GESTURE_CONFIG_PATH`). Khi G2c thêm `--gesture-config <path>`, flash HUD và
   `report` của đường mới phải lấy `gesture_flash_ms` từ config đã nạp theo cờ (13d §4 "Flash HUD dùng `gesture_flash_ms`"), không từ đường dẫn mặc định; nên có
   test với config tạm có `gesture_flash_ms` khác để phân biệt.
2. Đột biến trên worktree làm AC-G4 skip (dữ liệu gitignored không có trong worktree). Nếu đột biến G2c nhắm lớp cần dữ liệu thật, ghi rõ skip trong log hoặc
   chạy đột biến đó theo cách khác (không để lớp dữ liệu skip âm thầm).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có.
