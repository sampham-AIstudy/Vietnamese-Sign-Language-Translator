# Review 15 — lần sửa 13f, bước F1 (vslt-reviewer, 2026-10-10)

- Kế hoạch: `docs/plans/15-lan-sua-13f.md` §3.2, §3.4 (phần `_process`), §5 AC-F1/AC-F1m. Quyết định người dùng 2026-10-10 14:50 (`docs/STATE.md`).
- Commit: `40aa56c` (mã + test, cha `ab33094`), `7f9673c` (tiến độ). Coder: vslt-coder-claude (không phải agy, nên không áp mục kiểm agy).
- Diff của `ab33094..40aa56c`: `level1_demo.py` +27/-1, `tests/test_level1_demo.py` +247/-0. `7f9673c` chỉ sửa `docs/plans/15-progress.md`.
- Không có `README.md` hay 3 file ` D` của người dùng trong commit nào. Code của `4925aaf` (B0) và `ab33094` trùng nhau (`ab33094` chỉ sửa docs).

## Kết luận: APPROVE

Không có FAIL. Có 2 lỗ hổng test mức THẤP, xem ở "Vấn đề". Hai lỗ này không chặn F1, nên ghi lại để F3 xử lý.

## Bảng 1–13

| # | Mục | KQ | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | Hằng `GESTURE_NONE_LINE` ở `level1_demo.py:163-165`; `_panel_lines` ở `:1342-1363`, đúng thứ tự ô và ưu tiên của §3.2 (góc tay > cảnh báo CUỐI > đổi dấu > `""`). `_process` `:1429` là dòng `-` DUY NHẤT của diff. Không đổi `_hud_lines`, `_gesture_line`, `_gesture_engine_line`, `_decoder_line`, `_hand_line`, `Hud.*`, `_window_image`, `WINDOW_NAME`; `level1_display.py` không có trong diff. Số ô là `5 + MP + hand`, không phụ thuộc nội dung. `Hud.panel_height` (`:546-552`) chỉ phụ thuộc `len(small)`, nên cao panel cố định. `_gesture_line` thuần (đã đọc `:1224-1257`; `is_ready` ở `level1_core.py:655` chỉ đọc), nên gọi lại trong `_panel_lines` không có tác dụng phụ. Test `TestFixedPanel13f` (`tests/test_level1_demo.py:4189-4401`) phủ AC-F1 mục 1–7: mục 1 `:4262`; mục 2 `:4265`; mục 3 oracle viết trong test, ghép từ `s=_hud_lines()[1]` (`:4276-4307`), có (h)=góc tay và (f)=cảnh báo thứ 3; mục 4 gồm `len(slots)`, `panel_height` và app 7 ô `--dominant-hand lock --auto-enhance` (`:4309-4320`); mục 5 `:4322`; mục 6 chạy app trên clip D2 trong chế độ cửa sổ, recorder kế thừa và theo `resizeWindow`, ném `cv2.error` trước lần resize đầu (`:4169-4177`, `:4336-4380`); mục 7 đo pixel ở 2 chế độ rect (`:4382-4401`). |
| 2 | Tự chạy lại test | PASS | `PY -m unittest tests.test_level1_demo.TestFixedPanel13f tests.test_level1_display tests.test_level1_equivalence -v` → `_work/_plan15_l13/review_l13f_f1_run.log`: `Ran 55 tests in 88.623s`, `OK`, 0 skip (7 + 48). Kết quả khớp với coder (`l13f_f1_green.log` Ran 7 OK; `l13f_f1_green_display_equiv.log` Ran 48 OK). LALL Ran 688 `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` thì tôi chỉ đọc lại từ log của coder (`l13f_f1_green_level1_all.log`), KHÔNG tự chạy lại, vì việc được giao giới hạn ở 3 module. Log đỏ trên B0: `Ran 0`, `FAILED (errors=1)`, `AttributeError … '_panel_lines'`. mtime đỏ 15:18:06.62 < xanh 15:18:30.45 (`stat -c '%y'`). |
| 3 | Test không bị sửa/skip/nới | PASS | `git diff --numstat ab33094..40aa56c -- tests/` → `247 0`; số dòng `-` = 0. Không dùng E5 (W1b không đổi). Chỉ có 1 `skipUnless(not _MISSING, …)` mới, đúng theo hợp đồng. |
| 4 | Nguồn gốc dữ liệu | PASS | Không có dữ liệu train/đánh giá mới. Cảnh báo và đổi dấu trong (f)/(g)/(h) là chuỗi stub chỉ để hiển thị, có ghi rõ ở `:4157-4165`. Clip D2 là clip thật và chỉ được đọc. |
| 5 | Rò rỉ split | PASS (N/A) | F1 chỉ chạm phần hiển thị. |
| 6 | VAL/TEST | PASS (N/A) | Không chọn model. |
| 7 | Số liệu truy được | PASS | Progress chỉ ghi số test và log (`_work/…`). Không có số khoa học. Lần chạy khói headless được ghi là "không phải số đo". |
| 8 | Cỡ mẫu/CI | PASS (N/A) | — |
| 9 | Nhất quán train–realtime | PASS | §3.5: không chạm tiền xử lý, segmenter, decoder. `_process` chỉ đổi nguồn ô panel. JSON nhận dạng không đổi (`_hud_lines` giữ nguyên, sự kiện không đổi). |
| 10 | Không mock/giả trong đường chính | PASS | Mã chính không có random/mock; stub chỉ nằm trong test. |
| 11 | Bảo mật | PASS (N/A) | Không chạm API, WS hay cấu hình. |
| 12 | So sánh công bằng/GATE | PASS | Không đổi tiêu chí. State "fg" được THÊM ngoài (a)–(i): chỉ là thêm ca và dùng cùng oracle, không nới gì. Đột biến f4 cần ca này mới đỏ được (ở (h) góc tay luôn thắng). |
| 13 | Kết luận vượt bằng chứng | PASS | Progress không khẳng định gì về UX. Cửa sổ thật là việc của F4/VU2. |

## Đột biến

- **Của coder** (AC-F1m, đọc lại log `_work/_plan15_l13/l13f_f1_mut_*.log`):
  - base: `Ran 7 OK`.
  - f1 failures=1, f2 failures=25, f3 failures=21, f4 failures=2, f5 failures=4, f6 failures=16, tức 6/6 đỏ.
  - Script `l13f_f1_mutate.py`: mỗi phép thay thế được assert xuất hiện đúng 1 lần, nên không có đột biến rỗng.
- **Của reviewer**: worktree tạm `_work/_plan15_l13/wt_rev_13f_f1` dựng từ `40aa56c`, có chép clip D2 và `checkpoints/alphabet_best.pt`. Worktree đã gỡ và đã `prune`. Base `Ran 7 OK`, 0 skip. Log ở `review_l13f_f1_mut_*.log`.

| Đột biến | KQ | Test đỏ |
|---|---|---|
| r1: bỏ ô cảnh báo giữ chỗ khi `alert == ""` | ĐỎ (failures=15) | f1_3, f1_4, f1_7 (pixel/shape camera) |
| r2: ẩn ô cử chỉ khi cử chỉ tắt (`gesture_hud` False) | ĐỎ (failures=7) | f1_3, f1_4, f1_5 |
| r5: ô góc tay thành `""` | ĐỎ (failures=4) | f1_3 |
| r3: dòng đổi dấu lấy `small[n_head]` (bỏ bù dòng cử chỉ) | **SỐNG** | — |
| r4: `_panel_lines` trả `progress = 0.0` | **SỐNG** | — |

## Vấn đề (theo mức)

**THẤP-1, lỗ phủ ca r3.** Không có state nào có đồng thời dòng cử chỉ khác None, đổi dấu, không cảnh báo và không góc tay.
- Vì vậy chỉ số `small[n_head + int(gesture is not None)]` (`level1_demo.py:1358`) chưa bị khóa.
- Mã hiện tại đúng: tôi đã đối chiếu với `_hud_lines` `:1322-1333`, dòng đổi dấu đứng ngay sau dòng cử chỉ khi không có góc tay.
- Ca lỗi tiềm năng: người dùng đang giữ lòng bàn tay sau một lần đổi dấu. Khi đó ô cảnh báo sẽ lặp lại dòng cử chỉ.
- Đề nghị: F3 (hoặc một lần THÊM test sau) thêm state "bg" = (b) + (g), không góc tay, không cảnh báo.

**THẤP-2, lỗ phủ r4.** AC-F1 mục 2 so `[2]` (progress), nhưng ở mọi state progress đều là 0.0 (app mặc định `motion_pose`, segmenter mới dựng). Vì vậy phép so này rỗng về nội dung.
- Rủi ro thấp vì `_panel_lines` chỉ trả lại nguyên biến đã unpack.
- Đề nghị: test F3 hoặc H3 nên có một khung có `hold_progress > 0`.

**THÔNG TIN.**
- AC-F1 mục 6 ghi "đọc mọi khung". Test chạy `--pace` mặc định `all` nhưng không assert `frames_processed` bằng số khung của clip. Chấp nhận được, vì giá trị mặc định đã là đọc mọi khung.
- `_gesture_line()` được gọi 2 lần mỗi khung (một trong `_hud_lines`, một trong `_panel_lines`). Hàm thuần nên chi phí không đáng kể; F4/DC1 sẽ đo lại.

## Ghi chú cho F2/F3

- F3 phải giữ được `test_f1_6` (`render_calls == 0`, `len(rec.resized) == 1`) ở cửa sổ tự nhiên. Khi `_window_image` đổi sang `fit_window_layout`, nếu tại rect tự nhiên nó không trả về đúng `fit_layout`, test này sẽ đỏ. Đây là cái khóa đúng ý §3.4.
- E5 chỉ dùng ở F3, đúng `:3699-3703` của B0, tối đa 5 dòng `-`.
- Nên thêm ca "bg" (THẤP-1) và một khung có hold progress > 0 (THẤP-2), chỉ THÊM, không sửa test cũ.
- `side_ref_h = hud.side_panel_height(len(small), …)`: với F1, `len(small)` đã là hằng số, nên `panel_scale` cố định trong một lượt chạy.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có.
