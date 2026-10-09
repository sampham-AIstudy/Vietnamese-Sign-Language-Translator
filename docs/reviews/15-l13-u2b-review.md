# Review U2b — lần sửa 13b (commit `b0cbcf1` "15: L13-U2b nối cửa sổ co giãn (AC-U4/U4b/U6b)")

Ngày 2026-10-09. Reviewer độc lập. Coder: vslt-coder-claude (không phải agy, nên các mục kiểm riêng cho agy không áp dụng).
Hợp đồng: `docs/plans/15-lan-sua-13b.md` §3, §4 hàng U2b, §5 (AC-U4, AC-U4b, AC-U6b, AC-U9, AC-U2P), §5b, §7; gốc
`docs/plans/15-lan-sua-13.md` §2.2; `docs/plans/15-lan-sua-13a.md` §3.2 mục 6, §3.3. Mốc: `db402c1..b0cbcf1` (HEAD `3cbe368` chỉ thêm
`docs/STATE.md`, `docs/usage_ledger.csv`; `git diff --quiet b0cbcf1 HEAD -- level1_demo.py tests/ src/` sạch).

## Kết luận: APPROVE

0 CAO, 0 TB, 5 THẤP. Bất biến E3 giữ nguyên, các test mới chạy thật (không skip), 6/8 đột biến bị bắt; 2 đột biến còn sống nằm ở
phần nội dung ảnh HIỂN THỊ, vượt ngoài những gì AC yêu cầu (ghi THẤP-1, THẤP-2).

## Bảng kiểm 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, AC có test thật | PASS | AC-U4: `tests/test_level1_demo.py:3394` (`--pace realtime`, rect 1920×1080: mọi ảnh `imshow` (1080, 1920, 3), số ảnh = số khung xử lý, `render_to_window` được gọi ở mọi khung, đủ `n` cho mọi chặng). AC-U4b: `:3404` (cờ `namedWindow`; vì `WINDOW_NORMAL == 0` (cv2 5.0.0) nên `flags & normal == normal` luôn đúng, kiểm thật sự nằm ở `flags & WINDOW_AUTOSIZE == 0`, coder đã ghi rõ trong docstring), `:3417` (a) `cv2.error`, (b) `del cv2.getWindowImageRect` (AttributeError, khôi phục trong `finally`), (c) `(-1,-1,-1,-1)`: chạy hết clip không ngoại lệ, shape tự nhiên, `array_equal` với `Hud.compose` của một `Hud` riêng dựng lại từ BẢN CHÉP đầu vào cùng khung, `render_to_window` 0 lần. AC-U6b: `tests/test_level1_equivalence.py:561-611`, cả `gui` (số khung vào `process` == số khung đọc, mọi khung `is` đối tượng reader) lẫn `--pace realtime` (luật thứ tự giống `test_e3_paced_frame_is_object_read`), và MỌI ảnh `imshow` (1080, 1920, 3), mạnh hơn yêu cầu "≥ 1 ảnh". Thêm `:3433` (resizeWindow đúng 1 lần, kích thước tự nhiên). |
| 2 | Tự chạy lại test | PASS | `tests.test_level1_display tests.test_level1_equivalence -v` cho `Ran 45 tests in 193.414s OK`, không skip (`_work/_plan15_l13/review_u2b_equiv_display.log`), khớp số coder báo (`Ran 45 … 192.175s OK`). `tests.test_level1_demo.TestScaledWindowU2b tests.test_level1_demo.TestLatencyAcL -v` cho `Ran 8 tests in 46.880s OK` (`review_u2b_demo_new.log`). Toàn module demo (Ran 150 OK) do orchestrator chạy, reviewer không chạy lại. |
| 3 | Test không bị sửa/skip/nới | PASS | `git diff --numstat db402c1..b0cbcf1`: `tests/test_level1_demo.py 185 0`, `tests/test_level1_equivalence.py 89 0`; tính từ `ea9c645` là `300 2` (≤ 3, hai dòng `-` là của U1a). `tests/test_level1_display.py` không đổi. Skip mới chỉ có `@unittest.skipUnless(not _MISSING, SKIP_REASON)`, đúng điều kiện thiếu dữ liệu mà 13a §3.2 mục 6 cho phép; trên máy này không skip. |
| 4 | Nguồn gốc dữ liệu | PASS | Test chạy app thật trên clip người thật (`data/external/hauuto_raw/…/a_hau_A_001.mp4`, clip E3 spy) với MediaPipe thật (`RecordingSession` kế thừa `HandLandmarkSession`). Không sinh dữ liệu. |
| 5 | Rò rỉ split | N/A | Không train hay đánh giá. |
| 6 | VAL/TEST | N/A | Như trên. |
| 7 | Số liệu truy được | PASS | U2b không công bố số liệu hay báo cáo. Câu "cửa sổ WINDOW_NORMAL thật mở ở 304×281" (`15-progress.md:1544`) chỉ là ghi chú probe, không phải kết luận. cv2 5.0.0 đã xác nhận. |
| 8 | Cỡ mẫu / CI | N/A | Không có kết luận thống kê. |
| 9 | Nhất quán train và realtime (E3) | PASS | Diff không chạm `frame_mp`/`session.process`/`draw_landmarks`/`display_view` (`level1_demo.py:1243`, `:1249`, `:1290`, `:1293` giữ nguyên). Đường mới `_window_image` (`:1310-1332`) chỉ nhận `view` (ảnh hiển thị sau `display_view`), gọi `Hud.compose` (`vstack`, ra mảng mới) hoặc `render_to_window` (ra mảng mới, không sửa đầu vào, E4 mục 5). AC-U9 = `0`; `git diff --stat d1a8308..b0cbcf1 -- src/` rỗng. Đột biến m1 (chỉ ở chế độ cửa sổ thì `.copy()` khung vào `process`) qua mặt E3 spy headless/paced nhưng bị AC-U6b bắt, nên AC-U6b thật sự phủ thêm đường mới. |
| 10 | Không mock/giả/hard-code trong đường chính | PASS | Mock chỉ có trong test. Không có hằng số đo trong mã. |
| 11 | Bảo mật | PASS | Không đụng API/WS/CORS/token. Không có file dữ liệu nào bị commit. File đổi ⊆ §5b (`level1_demo.py`, 2 file test, `docs/plans/15-progress.md`). Thay đổi chưa commit của người dùng (`README.md`, 3 file ` D`) vẫn nguyên. Không có commit agy. |
| 12 | So sánh công bằng / GATE | N/A | Không có gate ở U2b. Tiêu chí không bị nới. |
| 13 | Kết luận vượt bằng chứng | PASS (kèm THẤP-3/4) | Lời khẳng định trong progress đều được test hoặc đột biến xác nhận (vd. "recorder cũ, cv2 thật ném `cv2.error` NULL window ⇒ dự phòng": bỏ `try` thì `TestLatencyAcL.setUpClass` ERROR, xem m2/m8). Hành vi trên cửa sổ THẬT (resizeWindow có cho đúng vùng ảnh hay không, DPI) chưa kiểm được bằng recorder; xem THẤP-4, cần kiểm ở V1. |

AC-U2P: đúng 1 commit `^15: L13-U2b ` (`b0cbcf1`); log đỏ `u2b_red.log` (mtime 09:35:54, đường dẫn cây chính, `Ran 6`, `FAILED (failures=11)`, lý do đỏ đúng
kỳ vọng) có mtime nhỏ hơn `u2b_green_new.log` (09:37:44, `OK`); `u2b_green_level1_all.log` cho `Ran 499 … OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`.
File LF (không có ký tự CR trong 4 file của commit). sha `checkpoints/alphabet_best.pt` vẫn là `160e0c68…`.

## Đột biến (worktree tạm `_work/_plan15_l13/wt_u2b_review` tại `b0cbcf1`, dữ liệu nối bằng junction/hardlink; đã gỡ link rồi `git worktree remove`; dữ liệu gốc còn nguyên)

Bộ test của mỗi đột biến: `TestScaledWindowU2b`, `TestLatencyAcL`, `TestEquivalenceE3Static`, `TestEquivalenceE3Spy`, `TestEquivalenceU6bWindow`
(m7, m8 bỏ `TestScaledWindowU2b`). Bản gốc trong worktree: `Ran 8 OK`, không skip (`review_u2b_mut_base.log`).
Script: `_work/_plan15_l13/review_u2b_mutate.py`, `review_u2b_mutate2.py`; log `_work/_plan15_l13/review_u2b_mut_<tên>.log`.

| Đột biến | Kết quả | Test bắt được |
|---|---|---|
| m1 `process(frame_mp.copy() if self.display else frame_mp)` | ĐỎ (failures=2) | 2 test U6b (E3 spy headless KHÔNG bắt được, đúng như mong đợi) |
| m7 `process(cv2.resize(frame_mp, …) if self.display else frame_mp)` | ĐỎ (failures=3) | E3 static `[level1_demo.py]` + 2 test U6b |
| m2 bỏ `try/except` quanh `getWindowImageRect` | ĐỎ (failures=4, errors=1) | U4b (a)(b), U2b start (a)(b), `TestLatencyAcL.setUpClass` |
| m8 bỏ `try/except` quanh `resizeWindow` | ĐỎ (errors=1) | `TestLatencyAcL.setUpClass` |
| m3 luôn gọi `render_to_window` (bỏ nhánh compose) | ĐỎ (failures=3, errors=3) | U4b fallback (a)(b)(c), U2b start |
| m4 `WINDOW_AUTOSIZE` | ĐỎ (failures=4) | U4b cờ ×4 |
| m5 nhánh dự phòng gọi `compose(…, 0.0, …)` (mất thanh hold) | XANH | không test nào (THẤP-1) |
| m6 `render_to_window(view[:, ::-1], …)` (ảnh co giãn bị lật) | XANH | không test nào (THẤP-2) |

## Vấn đề

CAO: không có. TB: không có.

- **THẤP-1 (oracle AC-U4b chưa độc lập với đối số).** `tests/test_level1_demo.py:3358-3375` lấy "đầu vào đúng" từ chính lời gọi
  `app.hud.compose`, nên oracle độc lập với `render_to_window`/`Hud.compose` nhưng KHÔNG độc lập với các đối số mà `_window_image` truyền vào.
  Đột biến m5 (đổi `hold_progress` thành 0.0 ở `level1_demo.py:1331`) vẫn xanh. Không vi phạm AC (AC cho phép so với "ảnh Hud.compose của cùng
  khung"). Đề xuất (U2c hoặc R2): ghi đầu vào ở lối vào `_window_image` (hoặc từ `app._hud_lines()`) rồi so với ảnh `imshow`.
- **THẤP-2 (nội dung nhánh co giãn chưa được kiểm ở mức app).** AC-U4 chỉ đòi shape, nên test `:3394` và U6b chỉ kiểm shape. m6 (truyền ảnh lật hoặc
  sai vào `render_to_window`) vẫn xanh. Đây là ảnh hiển thị (không thuộc đường suy luận), còn `render_to_window` thì đã được U1/U2a khóa riêng. Đề xuất:
  ở rect 1920×1080, so ảnh `imshow` với `render_to_window` của ảnh hiển thị đã ghi lại (cùng khung).
- **THẤP-3 (giả định (c): nội dung nhảy cỡ khi panel đổi chiều cao).** Panel có nhiều dòng điều kiện (`level1_demo.py:1213-1229`: cử chỉ, gợi ý góc,
  đổi dấu, cảnh báo). Cửa sổ chỉ được `resizeWindow` một lần theo khung đầu, nên ở kích thước mặc định:
  - khi panel cao lên, nội dung co (scale < 1, dải đen hai bên);
  - khi panel thấp xuống, nội dung ở scale 1 và lệch xuống (dải đen trên và dưới).

  Ảnh camera vì vậy đổi cỡ hoặc vị trí theo nhịp các dòng gợi ý. §2.2 không cấm ("kích thước khởi đầu = tự nhiên", còn kích thước sau do người dùng
  quyết), và WINDOW_AUTOSIZE cũ cũng giật (giật cả cửa sổ). Tuy vậy, đây là quyết định UX cho buổi demo. Gợi ý cho planner: `resizeWindow` lại khi kích
  thước tự nhiên đổi VÀ rect vẫn bằng kích thước tự nhiên trước đó (người dùng chưa kéo), hoặc giữ chỗ cố định cho panel. Cần nhìn ở V1.
- **THẤP-4 (giả định (a): chưa kiểm được trên cửa sổ thật).** Để đi nhánh `Hud.compose` ở kích thước mặc định, cần hai điều: `resizeWindow` (`:1322`) có tác
  dụng ngay trong cùng khung, và `getWindowImageRect` trả đúng `(w, h + panel_h)` (cả viền/toolbar win32 lẫn scale DPI). Recorder không kiểm được hai
  điều này. Nếu lệch vài px thì mọi khung đi `render_to_window` ở scale ≈ 1 (ảnh hơi mờ do nội suy; không ảnh hưởng suy luận). Cần kiểm ở V1 (cửa sổ
  thật: ghi rect sau khung đầu).
- **THẤP-5 (giả định (b), ghi cho U2d).** Rect đúng bằng kích thước tự nhiên thì đi `Hud.compose` thay vì `render_to_window`. Về chữ thì lệch §2.2
  ("Hợp lệ ⇒ render_to_window"), nhưng ảnh bằng hệt (AC-U2) và rẻ hơn; chấp nhận. Hệ quả cho AC-U5/DC1: lần đo "tự nhiên" thực chất đo đường
  `Hud.compose` cũ, nên `display_cost.json` (U2d) phải ghi rõ điều này trong `note`.

## Đánh giá 3 giả định của coder (15-progress.md:1590-1595)

(a) Đúng ý §2.2 ("kích thước khởi đầu = tự nhiên"; nếu không có lệnh này, WINDOW_NORMAL mở ở kích thước mặc định của HĐH). Phần còn lại xem THẤP-4.
Lưu ý cho U2c mà coder đã nêu: với `--fullscreen`, `resizeWindow` ở khung đầu có thể đè lên trạng thái toàn màn hình, nên phải kiểm thứ tự.
(b) Chấp nhận được (THẤP-5). (c) Không trái §2.2 nhưng có hệ quả UX (THẤP-3), cần planner hoặc người dùng nhìn ở V1.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không bắt buộc. THẤP-3 (cửa sổ có tự đổi cỡ theo panel hay không) là lựa chọn UX: planner có thể quyết, hoặc hỏi người dùng sau khi xem V1.
