# Review 15 — lần sửa 13f, bước F3 (cee4e4a + tiến độ d0bab0d)

Reviewer độc lập, 2026-10-11. Hợp đồng: `docs/plans/15-lan-sua-13f.md` §3.4, §5.0 (E5), AC-F3, AC-F3m; `docs/plans/15-lan-sua-13f-a.md`.
Coder: vslt-coder-claude (không phải agy, nên không áp các kiểm riêng cho agy).

## Kết luận: APPROVE

Không có FAIL. Có 2 điểm THẤP ghi chú, không chặn F4.

## Bảng kiểm

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | `level1_demo.py` (diff `fea1e62..cee4e4a`) khớp §3.4 từng ý: `SIDE_ROWS_PER_SLOT=2`/`SIDE_ROWS_LAST_SLOT=3`; `side_rows` dùng `_fonts_at(scale)[1].getlength`, `max_w = width - 2*scaled_px(PAD_X, scale)`; `side_panel_height` = `panel_height({}, [""]*(2(n-1)+3), n_stats, scale)`; `side_panel_builder` có cache riêng (`_side_key/_side_panel`), khóa `(w,h,s,font_px,view_key,tuple(slots),n)`, trả `(panel, line_steps(s)[1])`; `_window_image` dùng `fit_window_layout(..., side_ref_h=hud.side_panel_height(len(small), len(stats_lines)))`, `layout == fit_layout(w,h,panel_h)` thì đi `Hud.compose`, `layout.side` thì dùng `side_panel_builder`, còn lại dùng `panel_builder` như cũ. Lớp `TestSideLayoutApp13f` (`tests/test_level1_demo.py:4428-4637` tại cee4e4a) phủ H1 (oracle panel dựng trong test bằng Hud mới + `wrap_rows` với `480-2·int(8·ps)` + `draw_panel_overlays`, đúng 13f-a), H1c (vế `800/ref_h` nhỏ nhất NGHIÊM, `panel_scale` bằng nó, đáy mọi dòng ≤ `ph - small_step`), H2 (6 rect, có chống rỗng: `paths == {compose, side, below}`), H3 (chạy app 1080p: `len(layouts) == frames_processed`, cam_rect `{(0,0,1440,1080)}`, `resized == 1`), H4. Các mục review trước được THÊM: state "bg" (F1 THẤP-1), `hold_progress = 0.4 > 0` có kiểm thanh hold tới đúng cột `int(pw·0.4)` (F1 THẤP-2), ca hòa `(1024,816)` thì `side is False` (F2 THẤP-1). |
| 2 | Tự chạy lại test | PASS | `.venv/Scripts/python -m unittest tests.test_level1_demo.TestSideLayoutApp13f tests.test_level1_demo.TestWindowAndFullscreenU2t2 tests.test_level1_display tests.test_level1_equivalence` cho `Ran 74 tests in 118.397s` `OK`, rc=0 (`_work/_plan15_l13/review_l13f_f3.log`). Log coder: đỏ `l13f_f3_red.log` `Ran 8` `FAILED (failures=3, errors=6)`; xanh `l13f_f3_green.log` `Ran 12` `OK`; LALL `l13f_f3_green_level1_all.log` `Ran 710` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`. LALL không chạy lại, theo chỉ thị hạn mức. |
| 3 | Test không bị sửa/nới | PASS | `git diff --numstat fea1e62..cee4e4a -- tests/` ra `240 4 tests/test_level1_demo.py`. 4 dòng `-` đều ở hunk `@@ -3697,10` (W1b, B0 `:3700-3703`: `L = …fit_layout…`, `cam_h`, `cam_region`, `expected_cam`), nằm trong phạm vi E5 `:3699-3703` (≤ 5). Hai assert `:3704-3705` (camera `array_equal`, pixel hold `(0,200,0)`) giữ nguyên; có thêm `assertTrue(L.side)`. Tính từ B0 `4925aaf`: `test_level1_demo.py 487/4`, `test_level1_display.py 316/0`; `tests/test_level1_equivalence.py` không đổi. Khẳng định phụ mà coder đổi (H1 state (h): `…` thành `assertIn(ANGLE_HINT_LINE, rows)`) là dòng mới, đổi trước commit, không có trong lịch sử git. Đây không phải khẳng định AC (AC H1 chỉ yêu cầu state (a)), và theo ưu tiên §3.2 thì đổi như vậy là đúng. Đột biến coder (`l13f_f3_mutate.py`, mỗi phép thay đều assert xuất hiện đúng 1 lần): base `Ran 12 OK`; w1 failures=7, w2 3, w3 3, w4 1, w5 3. Định nghĩa w1–w5 khớp AC-F3m. Đột biến reviewer r1 (worktree tạm từ cee4e4a, chép clip D2 + checkpoint, đã gỡ): `side_panel_height` dùng `2·n_slots` thay cho `2(n-1)+3`, cho `FAILED (failures=1)` ở `test_h1c_seven_slots_height_term` (`review_l13f_f3_mut_r1.log`). |
| 4 | Nguồn gốc dữ liệu | PASS | Chỉ có view tổng hợp là mẫu thử hiển thị (`_f3_view`, ghi rõ trong test). H3/H4 dùng clip người thật D2 có sẵn. Không train, không đánh giá. |
| 5 | Rò rỉ split | PASS (không áp dụng) | Bước chỉ thuộc phần hiển thị. |
| 6 | VAL/TEST | PASS (không áp dụng) | Không chọn model. |
| 7 | Số liệu truy được | PASS | Progress d0bab0d chỉ khai số test/log (`Ran 710`, `Ran 12`, failures w1–w5), đã đối chiếu từng log và khớp. Không có số khoa học mới. |
| 8 | Cỡ mẫu/CI | PASS (không áp dụng) | Không có kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS | AC-U9 `git diff 4925aaf..cee4e4a -- level1_demo.py src/` ra 0; AC-U9b ra 0; `^[-+]WINDOW_NAME` ra 0. Các dòng `-` của `level1_demo.py` tính từ B0 gồm import (`:9`), `_process` `_hud_lines()` thành `_panel_lines()` (F1, được phép), docstring và 2 dòng của `_window_image`. Không có dòng nào trong `Hud.compose/_build/panel_height/panel_builder/_fit_committed/_fonts_at/_hud_lines/_gesture_*/_decoder_line/_hand_line/_key` (M0 giữ). Không thêm `cv2.resize`. E3/E4 (`tests.test_level1_equivalence`) xanh trong lần chạy 74 test. Cửa sổ tự nhiên vẫn đi `Hud.compose` (H2 rect `(0,0,640,480+ph)` và `"error"` cho `la is None`; W1a/test_f1_6 xanh). |
| 10 | Không random/mock trong đường chính | PASS | `mock` chỉ có trong test. Không hard-code số đo. |
| 11 | Bảo mật | PASS (không áp dụng) | Không có API/WS/token. Phạm vi file: `level1_demo.py`, `tests/test_level1_demo.py`, `docs/plans/15-progress.md`, khớp §phạm vi F3. `git status --porcelain -- level1_demo.py src tests` rỗng. README.md, 3 file data ` D` và các file untracked của người dùng không bị đụng. |
| 12 | So sánh công bằng/GATE | PASS | Không đổi tiêu chí AC. Ngưỡng DC1 để F4 đo. |
| 13 | Kết luận vượt bằng chứng | PASS | Progress chỉ nói "AC-F3 xanh, đột biến đỏ", đúng với log. Chưa có khẳng định nào về cửa sổ thật (W2) hay chi phí (DC1): đó là việc của F4/VU2. |

## Vấn đề

1. THẤP: `_window_image` gọi `hud.side_panel_height(...)` mỗi khung (`level1_demo.py:1510-1511` tại cee4e4a). Lời gọi này dựng `[""]*n_rows` rồi gọi `panel_height` trên một dict mới. Giá trị không cache, nên chi phí mỗi khung tăng thêm một chút. Có thể không đáng kể, nhưng F4 DC1 nên xác nhận (xem ghi chú dưới). Không chặn.
2. THẤP: oracle lề trong test là `int(8·ps)`, còn mã dùng `scaled_px(PAD_X, ps)`. Hiện hai cách bằng nhau (`scaled_px = int(value*scale)`, `level1_display.py:45-47`, `PAD_X = 8`). Nếu sau này `scaled_px` đổi sang làm tròn thì test sẽ đỏ đúng như ý muốn. Chỉ ghi nhận.

## Ghi chú cho F4

- Tại cee4e4a, `git status --porcelain -- level1_demo.py src scripts` rỗng, đủ điều kiện AC-F4.
- DC1 đo lại 3 lần: ở 1080p đường cạnh nhau là đường mới (`side_panel_builder` + `side_panel_height` mỗi khung). Cần ghi rõ script DC1 đang đo đường nào (compose/dọc/cạnh nhau). Nếu chỉ đo compose thì phải nói rõ đường cạnh nhau CHƯA được đo, không suy ra từ compose.
- W2 (cửa sổ thật): kiểm `getWindowImageRect` khi fullscreen 16:9 trả về rect cho `L.side` True và camera `(0,0,1440,1080)` như H3.
- THẤP-2 của review F2 (G8 gọi `git show` lúc chạy) vẫn còn, không thuộc F3.
