# Review 15 lần sửa 13d — phần G2a (commit 70b9055 + tiến độ f64966a)

Reviewer độc lập, 2026-10-09. Phạm vi: CHỈ commit mã `70b9055` ("15: L13-G2a P2 cooldown không đệm vẫy, NaN = không tay + kiểm w/h, reason P1;
test AC-D1–D6", cha `d7b530a`) và commit tiến độ `f64966a`. Coder vslt-coder-claude (không phải agy, các mục kiểm agy không áp dụng).
Hợp đồng: `docs/plans/15-lan-sua-13d.md` §3 (P1, P2, THẤP-2, THẤP-4), §4 hàng 5a, §5 AC-D1…D6 + "Chung", §5b, §7. Nguồn: `docs/reviews/15-l13-g1-review.md`.

## Kết luận: APPROVE

Không có FAIL. 0 vấn đề CAO/TB, 2 vấn đề THẤP (ghi nhận, không chặn G2b), 1 ghi chú cho G2c.

## Bằng chứng đã tự chạy

| Lệnh | Log | Kết quả |
|---|---|---|
| `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_gestures tests.test_level1_core` | `_work/_plan15_l13/review_g2a_gestures_core.log` | `Ran 117 tests in 5.036s` — `OK` (khớp `g2a_green_gestures_core.log` của coder: `Ran 117` `OK`) |
| `… -m unittest tests.test_level1_core tests.test_level1_guard` | `_work/_plan15_l13/review_g2a_core_guard.log` | `Ran 61 tests in 4.459s` — `OK` |
| `git diff --numstat d7b530a..70b9055 -- tests` | — | `267 0 tests/test_level1_gestures.py` (0 dòng xóa, không `skip` mới: grep diff `skip` = 0) |
| `git diff 9552b2d..70b9055 -- configs` | — | `configs/level1_gestures.json` 1+/1−: CHỈ chuỗi `reason` của `space_dropout_frames`; `"value": 1` giữ |
| `git grep level1_gestures 70b9055 -- *.py` | — | ngoài module và test của nó chỉ có docstring `level1_core.py:566-567` (không mã nào khác gọi; app chưa nối, G2c) |
| Log coder (grep `Ran`/`OK`/`FAILED`) | `g2a_green_level1_all.log`, `g2a_red.log`, `g2a_mut_*.log` | all `Ran 603` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`; đỏ trước `Ran 60` `FAILED (failures=3)`; đột biến base OK + 8/8 `FAILED` |

Đột biến của reviewer (worktree tạm `_work/_plan15_l13/wt_review_g2a` từ `70b9055`; mỗi đột biến khôi phục từ bản gốc, `cmp` khớp, `git status` trống;
worktree đã `git worktree remove` + `prune`, cây chính không đổi). Lệnh: `… -m unittest tests.test_level1_gestures`, log `_work/_plan15_l13/review_g2a_mut_<tên>.log`.

| Tên | Đột biến trên `src/inference/level1_gestures.py` | Kết quả |
|---|---|---|
| base | không đổi | `Ran 60` `OK` |
| R2 | `span = self.buffer[start:]` thành `span = self.buffer` | ĐỎ 2: `test_d1a_…`, `test_d1b_…` (ở G1: SỐNG), TB-1 của G1 đã khóa |
| R4 | rearm `>` thành `>=` | ĐỎ 1: `test_d2_other_pose_for_exactly_rearm_does_not_rearm` (ở G1: SỐNG), THẤP-3 của G1 đã khóa |
| nan | nhánh `raw = None` khi có NaN/inf thành `pass` | ĐỎ 1: `test_d5_non_finite_frame_while_holding_the_open_palm_is_a_lost_hand` |
| p2g1 | khối cooldown P2 thành `if False:` (bỏ khối, giữ cổng mới) | ĐỎ 2: `test_d4_…`, `test_cooldown_blocks_even_after_the_hand_left` |
| p2g1exact | hành vi G1 nguyên vẹn (bỏ khối + trả `or in_cooldown` vào cổng phát) | ĐỎ 1: `test_d4_strokes_inside_the_cooldown_never_fire` |

Thăm dò giả định 2 (sửa TEST trong worktree tạm, không phải đột biến mã): AC-D1b với `still_before=0` (bỏ khung chuyển ở y của nét) trên mã ĐÚNG cho
`test_d1b_…` FAIL `unexpectedly None` (`_work/_plan15_l13/review_g2a_probe_d1b.log`) — xem THẤP-1.

## Đối chiếu điểm soi

1. **P2** (`level1_gestures.py` `WaveBackspaceGesture.update`, khối `if in_cooldown:` sau nhánh `need_release`): mọi khung có tay với
   `ts - last_emit_ts < cooldown_ms` xóa bộ đệm, `strokes = 0`, trả False; mất tay vẫn xóa bộ đệm + nhả `need_release` (không đổi); cổng `or in_cooldown`
   thừa nên bỏ — đúng vì khối mới đã chặn mọi khung trong cooldown trước khi tới cổng. **THẤP-2/NaN** (`GestureEngine.step`): kiểm w/h (loại `bool`,
   không phải `numbers.Real`, không hữu hạn, <= 0) cho ValueError; shape khác (21,3) cho ValueError (kiểm TRƯỚC NaN, nên `nan_r[:, :2]` vẫn ValueError — test có);
   NaN/inf cho `raw = None`, tức CẢ space (`has_hand=False`: hủy giữ/re-arm) và wave (`None`: xóa bộ đệm), `is_palm`/`is_flat` False. **Config**: chỉ `reason`.
   Docstring module, `DeliberateSpaceGesture`, `WaveBackspaceGesture`, `GestureEngine` cập nhật khớp. Không đổi `level1_core.py`/`level1_demo.py`.
2. **Test D1–D6 giữ hành vi**: R2, R4, NaN, P2 (cả 2 dạng) đều ĐỎ (bảng trên). AC-D1 có assert tiền điều kiện trên CẢ bộ đệm (tỉ lệ phẳng < 0,9;
   dọc > 0,5 x ngang) và kiểm mọi khung nằm trong `wave_window_ms`; D1c đối chứng 10 khung không phẳng xen trong nét cho 0 (assert đếm = `N_PRE`).
   AC-D2 timestamp tính chính xác (`t1 + rearm` và `t1 + rearm + DT`, không cộng dồn). AC-D3 đỏ với 2 đột biến gõ cứng (log coder `g2a_mut_strokes2`,
   `g2a_mut_dropout1`: `FAILED (failures=2)`). AC-D4 assert `strokes == 0` ở MỌI khung trong cooldown + `n_emits == 1` tới `t_emit + cooldown + 300`,
   đối chứng sau cooldown đúng 1. AC-D5 có kiểm sanity (mất tay khác khung có tay lỗi) nên phép so "giống hệt `None`" có nghĩa; w/h thuộc {0, -1, nan, inf} x {landmark, None}.
   47 test G1 không sửa (numstat cột xóa = 0); `test_cooldown_blocks_even_after_the_hand_left`, `test_rearm_needs_end_of_flat_hand_after_cooldown`,
   `test_spec_is_the_design_table`, `test_committed_file_loads` nằm trong 117 test OK.
   **4 giả định của coder**: (1) kiểm w/h cả khi landmark `None` — khớp chữ §3 THẤP-2 (không đặt điều kiện), hợp 13d; (2) AC-D1b khung chuyển — hợp lệ nhưng
   xem THẤP-1; (3) AC-D3 `config + 1` (= 3 và 2 với bảng thiết kế) — khớp số của AC và luật "không số gõ tay" §5; (4) `MARGIN_MS = 300` — số của AC-D4, không
   phải tham số thiết kế, hợp lệ.
   **Quy ước commit**: `git log` có đúng 1 commit khớp `^15: L13-G2a` (`70b9055`); `f64966a` ("15: tiến độ lần sửa 13d G2a …") chỉ sửa
   `docs/plans/15-progress.md` (thuộc phạm vi G2a §5b), không khớp mẫu, nên không vi phạm chữ "đúng 1 commit `^15: L13-G2a`"; có tiền lệ tách commit báo cáo
   (U2t2 `b5762ec` + `3a07a8c`), và cần tách để ghi được hash `70b9055`. Ghi nhận THẤP-2.
3. Tự chạy: khớp số coder báo cho các lệnh đã chạy lại; bộ 603 test không chạy lại (khoảng 515 s) vì chỉ `tests/test_level1_gestures.py` import module đổi — chấp nhận
   log coder.
4. Không đụng thay đổi chưa commit của người dùng: `70b9055` chỉ 3 file trong scope G2a, `f64966a` chỉ `15-progress.md`; `git status -- src tests configs level1_demo.py` trống.

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, AC có test thật | PASS | AC-D1a/b/c, D2 (2 test), D3 (2), D4, D5 (5) trong `tests/test_level1_gestures.py` (13 test, diff `@@ -613,5 +621,264 @@`); AC-D6 bằng diff config + test G1 xanh; đột biến bảng trên đều ĐỎ |
| 2 | Tự chạy lại test | PASS | `review_g2a_gestures_core.log` `Ran 117` `OK`; `review_g2a_core_guard.log` `Ran 61` `OK` — khớp coder |
| 3 | Test không bị sửa/skip/nới | PASS | numstat `267 0`; không `skip` mới; không có dòng xóa trong diff tests (agy: không áp dụng) |
| 4 | Nguồn gốc dữ liệu | PASS (không đo) | chỉ chuỗi tổng hợp kiểm logic, có docstring "chuỗi tạo có kiểm soát để kiểm logic" (docstring đầu file, `TestWaveSpanAcD1`); không số báo cáo |
| 5 | Rò rỉ split | Không áp dụng | không train/đánh giá |
| 6 | Chọn model bằng VAL | Không áp dụng | không model |
| 7 | Số liệu truy được | PASS | mọi số trong `15-progress.md` mục G2a là số test có log (`g2a_*.log`) và hash `70b9055`; không số khoa học (agy: không áp dụng) |
| 8 | Cỡ mẫu / CI | Không áp dụng | không kết luận thống kê |
| 9 | Nhất quán train–realtime | PASS | NaN/inf = không tay chốt TRƯỚC G3 (13d §6); `aspect_points` giữ nguyên; app chưa nối (G2c) |
| 10 | Không Math.random/mock/giả | PASS | diff không thêm random/mock vào `src/`; tham số chỉ từ config |
| 11 | Bảo mật / kiểm input | PASS | `step` kiểm shape, NaN/inf, w/h hữu hạn > 0 (loại `bool`); không token/dữ liệu commit (agy: không áp dụng) |
| 12 | So sánh công bằng / GATE không nới | PASS | `values` config không đổi (AC-D6); P2/NaN chặt hơn, chốt trước khi có `gesture_false_trigger.json` |
| 13 | Kết luận vượt bằng chứng | PASS | tiến độ khai "8/8 đỏ", "603 OK" khớp log; pha đỏ khai AC-D1/D2/D3 xanh ngay trên G1 — đúng bản chất (khóa hành vi có sẵn, R2/R4 do reviewer xác nhận đỏ) |

## Vấn đề (theo mức)

- **THẤP-1 (giả định 2, AC-D1b):** "khoảng từ đầu nét 1" bắt đầu ở khung CỰC TRỊ x cuối cùng trước khi rời (`lo_i`/`hi_i` trong `_count_strokes`), nên khung nghỉ
  ngay trước nét — nếu cùng x — thuộc khoảng tính. Thăm dò: bỏ khung chuyển ở y của nét thì D1b không phát (`review_g2a_probe_d1b.log`). Test hiện đúng chữ AC
  (10 khung lệch y đứng trước nét) và đúng hành vi mã; hệ quả thực tế: tay nghỉ ở chỗ khác rồi vẫy ngay mà khung nghỉ cuối trùng x cực trị có thể bị chặn bởi tỉ lệ
  dọc/ngang (1 khung không phẳng như D1a chỉ chiếm khoảng 1/23, còn dưới ngưỡng 0,1). Theo hướng ít phát — hợp §0 Q5; GT1 đo độ nhạy. Không sửa; planner có thể
  ghi vào Giới hạn R2.
- **THẤP-2 (quy ước commit):** tiến độ tách thành `f64966a` thay vì nằm trong commit `15: L13-G2a` (§5b liệt kê `15-progress.md` trong phần G2a). Chữ "đúng 1 commit
  `^15: L13-G2a`" vẫn đạt; có tiền lệ. Planner có thể ghi rõ cho G2b/G2c "commit tiến độ riêng được phép, không mang tiền tố `L13-G2x`".
- **Ghi chú cho G2c:** `GestureEngine.step` nay ValueError khi w/h không hợp lệ kể cả khung không tay, nên app phải luôn truyền kích thước khung thật (kể cả khi
  MediaPipe không thấy tay); test AC-D9 nên có 1 khung `None` đi qua đường app.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có.
