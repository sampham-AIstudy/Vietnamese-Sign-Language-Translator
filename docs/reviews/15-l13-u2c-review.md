# Review độc lập — Kế hoạch 15, lần sửa 13b, phần U2c (commit `00d320c`)

- Reviewer: vslt-reviewer (Claude), 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `678717b`.
- Phạm vi: CHỈ commit `00d320c` "15: L13-U2c phím f, --fullscreen, --[no-]display-mirror, LRU font (AC-U6/U8)".
  Mốc so: `e165990` (review U2b); mốc AC-U9b: `b0cbcf1` (commit U2b); mốc AC-U9: `d1a8308`.
- Hợp đồng: `docs/plans/15-lan-sua-13b.md` §3, §4 hàng U2c, §5 (AC-U6, AC-U8, AC-U9, AC-U9b, AC-U2P), §5b, §7; gốc `docs/plans/15-lan-sua-13.md` §2.2, §9.
- Coder: agy (gemini-3.8-flash-high, effort high), 2 lần chạy (lần 1 đứt mạng, exit=3; lần 2 hết giờ 40', không có dòng STATUS); orchestrator commit hộ.

## Kết luận: CHANGES_REQUESTED (0 CAO, 1 TB, 6 THẤP)

Mã đúng hợp đồng về chức năng (phím f, `--fullscreen` không vào preset, `BooleanOptionalAction`, LRU ≤ 8, không đụng đường khung).
Một vấn đề TB: gợi ý phím đặt ở tiêu đề cửa sổ bằng chữ có dấu, và trên máy đích tiêu đề hiện sai mã (đã kiểm thực tế) nên gợi ý không đọc được.

## Lệnh reviewer đã chạy (log `_work/_plan15_l13/review_u2c_*.log`)

| Lệnh | Kết quả |
|---|---|
| `PY -m unittest tests.test_level1_demo.TestFullscreenU2c tests.test_level1_demo.TestHudFontLruU2c tests.test_level1_demo.TestParserU2c -v` → `review_u2c_new.log` | `Ran 8 tests` `OK`, 0 skip |
| `PY -m unittest tests.test_level1_display tests.test_level1_equivalence -v` → `review_u2c_equiv_display.log` | `Ran 45 tests` `OK`; `test_e3_headless/paced_frame_is_object_read`, 4 test `test_e4_*`, `test_u6b_window_frame_is_object_read`, `test_u6b_window_paced_frame_is_object_read` đều chạy, 0 skip |
| Toàn level1: không chạy lại, đọc log orchestrator `u2c_orch_level1_all.log` (mtime 13:50:20) | `Ran 507` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` |
| Đột biến trong worktree tạm `_work/_plan15_l13/wt_u2c_review` tại `00d320c` (clip/checkpoint chép vào; đã `git worktree remove`) | bảng dưới |
| Thăm dò tiêu đề thật: `cv2.namedWindow(WINDOW_NAME)` + `EnumWindows`/`GetWindowTextW` (ctypes), lệnh một dòng, không ghi file | cv2 5.0.0, `GUI: WIN32UI`, ACP 1252; tiêu đề thật `VSLT Level 1 (f: toÃ n mÃ n hÃ¬nh)` (khác `WINDOW_NAME`); `getWindowProperty(VISIBLE)` = 1.0, `getWindowImageRect` hợp lệ |
| AC-U9b: `git diff b0cbcf1..HEAD -- level1_demo.py`, lọc dòng `[-+]` theo mẫu khung | `0` |
| AC-U9: `git diff d1a8308..HEAD -- level1_demo.py scripts/level1_display_cost.py src/`, lọc dòng `+` theo mẫu lách | `0` |
| `git diff --stat d1a8308..HEAD -- src/` | rỗng |
| `sha256sum checkpoints/alphabet_best.pt` | `160e0c68…` |
| `git diff e165990..00d320c --numstat -- tests/` | `204 0 tests/test_level1_demo.py` |

### Đột biến (3 lớp mới, worktree tạm)

| Mã | Đột biến (`level1_demo.py`) | Kết quả | Log |
|---|---|---|---|
| base | không đổi | `Ran 8` `OK` (0 skip) | `review_u2c_mut_base.log` |
| m1 | bỏ giới hạn LRU (`> 8` thành `> 10**6`) | `FAILED (failures=1)` | `review_u2c_mut_m1_nolimit.log` |
| m2 | `--fullscreen` vẫn gọi `resizeWindow` (`if not self.window_sized:`) | `FAILED (failures=1)` | `review_u2c_mut_m2_fsresize.log` |
| m3 | phím f không đảo trạng thái (`self.fullscreen = True`) | `FAILED (failures=2)` | `review_u2c_mut_m3_notoggle.log` |
| m4 | bỏ `move_to_end` (FIFO thay LRU) | `OK` (SỐNG) | `review_u2c_mut_m4_fifo.log` |
| m5 | tắt toàn màn hình vẫn gửi `WINDOW_FULLSCREEN` (f không thoát được) | `OK` (SỐNG) | `review_u2c_mut_m5_offprop.log` |
| m6 | bỏ `window_sized = False` khi bật toàn màn hình | `OK` (SỐNG) | `review_u2c_mut_m6_noreset.log` |
| m7 | chèn gợi ý ` \| f toàn màn hình` vào dòng phím HUD (kiểm lời khai agy) | 3 lớp cũ `Ran 10` `FAILED (failures=5)`: `test_m3_hud_line_only_when_not_default` x2, `test_9d_no_gesture_space_same_as_before` x2, `test_6d_motion_pose_hud_image_identical_to_before` | `review_u2c_mut_m7_hintline.log` |

Ba đột biến được giao (m1–m3) đều ĐỎ. m4–m6 sống: lỗ test (THẤP-1, THẤP-2); mã hiện tại đúng ở cả ba chỗ.

## Bảng kiểm 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | FAIL (TB-1) | AC-U6: phím f hai lần cho đúng 2 sự kiện `on: True` rồi `on: False` (`tests/test_level1_demo.py:3510-3512`); `setWindowProperty` ném `cv2.error` không dừng app (`:3516-3528`); `--fullscreen` gọi đúng 1 lần sau `namedWindow`, 0 `resizeWindow` (`:3530-3555`); thoát toàn màn hình thì resize 1 lần về cỡ tự nhiên (`:3557-3574`); parser/preset (`:3612-3640`). AC-U8: 20 cỡ, cỡ 20 trúng cache, cỡ 1 dựng lại, ≤ 8 ở mọi bước (`:3581-3609`); hàm dựng font = `ImageFont.truetype` trong `Hud._fonts_at` (`level1_demo.py:516-528`). Luật gợi ý phím §2.2: thỏa về chuỗi Python (`level1_demo.py:104`) nhưng hiển thị thật hỏng mã (TB-1). Lỗ test m4/m5/m6 (THẤP-1/2). |
| 2 | Tự chạy lại test | PASS | 8/8 OK; display+equivalence 45 OK; khớp progress (`Ran 8 OK`, `Ran 45 OK`) và log orchestrator `Ran 507 OK (skipped=1)`. |
| 3 | Test không bị sửa/skip/nới | PASS | numstat `204 0`; 0 dòng `-` trong `git diff e165990..00d320c -- tests/`; không test cũ nào bị sửa cho hợp tên cửa sổ mới (test cũ dùng `app_mod.WINDOW_NAME`, không ghim chuỗi). Lớp mới dùng `skipUnless(not _MISSING)` theo mẫu có sẵn; máy này không skip. agy-guard: lần 1 `_work/agy_logs/20261009-111028-15-lan-sua-13b.log:99-100` commit agy sạch, working tree sạch; lần 2 `20261009-124935-15-lan-sua-13b.log:35-37` commit agy sạch, working tree BLOCK `docs/plans/15-progress.md` — báo nhầm (điểm 1), orchestrator đã ghi lại, không bị bỏ qua âm thầm. |
| 4 | Nguồn gốc dữ liệu | PASS (không áp dụng) | Không dữ liệu mới; test dùng clip hauuto thật có sẵn và checkpoint `160e0c68…`. |
| 5 | Rò rỉ split | PASS (không áp dụng) | Không train/đánh giá. |
| 6 | Chọn model bằng VAL | PASS (không áp dụng) | Không đổi model. |
| 7 | Số liệu truy được | PASS | Số trong progress chỉ là đếm test/grep, đã chạy lại được. agy: file của `00d320c` = `level1_demo.py`, `tests/test_level1_demo.py`, `docs/plans/15-progress.md` (trong khối scope §5b) + `docs/agy_usage_ledger.csv` (NGOÀI scope, orchestrator gộp — THẤP-4). Không commit nào của agy trong `e165990..00d320c` (chỉ `5fd07ae` state và `00d320c` do orchestrator), nên không có commit `--no-verify` của agy. Không push: `origin/cloud/2026-10-04-level1-rearm` = `e520e22`, sau HEAD. Ledger 2 dòng mới (`2026-10-09T05:13Z` stale; `06:30Z` gemini-3.8-flash-high, high, 5h +29.2, `ok timeout`). Không dùng số sổ làm kết luận. |
| 8 | Cỡ mẫu / CI | PASS (không áp dụng) | Không có kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS | AC-U9b = 0, AC-U9 = 0, `src/` không đổi; E3 spy, E4, AC-U6b xanh không skip. Thay đổi chỉ ở `_key`, nhánh resize của `_window_image`, `run` (sau `namedWindow`), parser, `Hud._fonts_at`. |
| 10 | Không mock/giả trong đường chính | PASS | Không `random`/mock trong `level1_demo.py`; mock chỉ trong test. |
| 11 | Bảo mật | PASS | Không token/khóa; không API/WS mới; không dữ liệu mới vào git. agy STATUS: lần 2 không có STATUS (hết giờ), lần 1 chết vì mạng — không có STATUS sai lệch với git/test. |
| 12 | So sánh công bằng / gate | PASS (không áp dụng) | U2c không có gate; AC không bị nới. |
| 13 | Kết luận vượt bằng chứng | FAIL (TB-1, THẤP-5) | Progress coi tiêu đề cửa sổ là chỗ đặt gợi ý chấp nhận được mà chưa kiểm tiêu đề thật trên Windows (hỏng mã). Câu trích "Nếu sau khi chạy test thật sự có test ghim dòng đó, hoàn tác (A)…" được gán cho "luật thiết kế §2.2 gốc và hướng dẫn kế hoạch", thật ra là lời giao của cầu nối (`_work/_plan15_l13/u2c_steps2.txt`). Lời khai "5 test cũ đỏ" ĐÚNG (m7). |

## Kết luận các điểm cần soi riêng

1. **BLOCK `docs/plans/15-progress.md` là báo nhầm.** `git diff e165990..00d320c -- docs/plans/15-progress.md`: đúng 3 dòng `-`, cả 3 ở mục "## Trạng thái"
   (dòng U2b "Chờ cầu nối + reviewer U2b…" thành "Reviewer U2b: APPROVE (`e165990`)" — đúng thực tế; dòng "ĐANG LÀM"; dòng "Còn lại" bỏ U2c), cộng dòng `+`
   cập nhật trạng thái và mục mới "Lần sửa 13b — U2c" ở CUỐI file. Không mất/sửa nội dung cũ của người khác. Lần 2 snapshot 66 đường dẫn bảo vệ
   (lần 1: 63), khớp việc guard coi file WIP bẩn lúc bắt đầu là "của người dùng" (WIP ghi ở STATE `5fd07ae`).
2. **Tiêu đề `WINDOW_NAME = "VSLT Level 1 (f: toàn màn hình)"`.**
   - Luật §2.2 (`15-lan-sua-13.md:71-72`) chỉ cho đặt vào tiêu đề khi có test ghim nguyên văn dòng phím. `grep` trong `tests/` không thấy test ghim nguyên văn,
     nhưng m7 xác nhận 5 test so dòng/ảnh HUD với commit tham chiếu (`app_module_at`) đỏ, nghĩa là dòng phím bị ghim GIÁN TIẾP; dùng tiêu đề đúng TINH THẦN luật
     (không sửa test cũ). Lời giao của cầu nối mâu thuẫn ("test cũ đỏ thì DỪNG báo CẦN PLANNER" rồi "hoàn tác (A)… tiêu đề chấp nhận được"); agy theo câu sau (THẤP-5).
   - **Rủi ro chữ có dấu là CÓ THẬT (TB-1)**: cv2 5.0.0 backend WIN32UI, ACP 1252; tiêu đề hiển thị `VSLT Level 1 (f: toÃ n mÃ n hÃ¬nh)`.
     Tra theo tên (`getWindowProperty`, `getWindowImageRect`) vẫn chạy, nên chỉ hỏng hiển thị — nhưng hiển thị là toàn bộ mục đích của gợi ý.
   - Không test cũ nào bị sửa cho hợp tên mới (0 dòng `-` trong `tests/`).
3. **Thứ tự cửa sổ, cờ, LRU.** `--fullscreen`: `self.fullscreen` True từ `__init__` (`level1_demo.py:932`); `setWindowProperty(..., WINDOW_FULLSCREEN)` ngay sau
   `namedWindow` (`:1389-1394`); `_window_image` bỏ `resizeWindow` khi đang toàn màn hình (`:1337`), nên không kéo cửa sổ về cỡ tự nhiên (m2 đỏ). Phím f:
   bật thì `window_sized = False` (`:1108-1109`); tắt thì khung kế `resizeWindow` 1 lần về cỡ tự nhiên (bỏ cỡ người dùng đã kéo — THẤP-6).
   `--fullscreen` không có trong `DEFAULT_DEMO_ARGV` (`:1612-1623`); `main` chỉ ghép preset + argv người dùng (`:1626-1628`). `--display-mirror` là
   `BooleanOptionalAction, default=False` (`:1568-1569`); preset vẫn chứa `--display-mirror` nên True; `--no-display-mirror` cho False — hành vi preset mặc định không đổi.
   LRU: `OrderedDict`, trúng thì `move_to_end`, thêm thì `popitem(last=False)` khi > 8 (`:516-528`) — đúng LRU (giữ cỡ vừa dùng, loại cỡ cũ nhất).
   Test LRU đỏ khi bỏ giới hạn (m1) nhưng KHÔNG phân biệt LRU với FIFO (m4 sống).
4. **E3/AC-U9/U9b**: giữ; `src/` không đổi; E3/E4/AC-U6b xanh, không skip.

## Vấn đề

### CAO
Không có.

### TB
- **TB-1 — Gợi ý phím ở tiêu đề cửa sổ hiện sai mã trên Windows** (`level1_demo.py:104`; test `tests/test_level1_demo.py:3644-3647` chỉ kiểm chuỗi Python).
  Đã kiểm thực tế: tiêu đề hiển thị `VSLT Level 1 (f: toÃ n mÃ n hÃ¬nh)`. Người dùng demo không đọc được gợi ý; yêu cầu "gợi ý phím" của §2.2 không đạt về hiệu quả.
  Đề xuất (reviewer không sửa): tiêu đề ASCII, ví dụ `"VSLT Level 1 (f: fullscreen)"` hoặc `"VSLT Level 1 (f: toan man hinh)"`; sửa test MỚI của chính
  commit này thành `assertTrue(app_mod.WINDOW_NAME.isascii())` + `assertIn("f:", app_mod.WINDOW_NAME)`. Không đụng test cũ. Chọn chữ: mục CẦN PLANNER.

### THẤP
- **THẤP-1 — Test không kiểm giá trị thuộc tính khi bật/tắt** (`tests/test_level1_demo.py:3502-3511` chỉ kiểm phần tử `[0]`, `[1]` của `set_props`):
  m5 (tắt vẫn gửi `WINDOW_FULLSCREEN`, f không thoát được toàn màn hình) sống. Nên thêm `set_props[0][2] == cv2.WINDOW_FULLSCREEN`, `set_props[1][2] == cv2.WINDOW_NORMAL`.
- **THẤP-2 — Lỗ test LRU và đường thường → f → f**: m4 (FIFO) sống vì chuỗi 20 cỡ không truy cập lại cỡ cũ trước khi bị đẩy; m6 sống vì test thoát
  toàn màn hình bắt đầu bằng `--fullscreen` (`window_sized` vốn False). Mã đúng (`level1_demo.py:519-520`, `:1108-1109`). Nên thêm: chạm lại cỡ 1 sau cỡ 7
  rồi thêm cỡ 9 thì cỡ 1 vẫn trong cache; chạy không `--fullscreen`, phím f hai lần thì `resized` có 2 lần.
- **THẤP-3 — Trạng thái khi `setWindowProperty` lỗi**: `self.fullscreen` vẫn đảo và ghi `on: true` dù cửa sổ không toàn màn hình (`level1_demo.py:1102-1111`);
  `--fullscreen` lỗi lúc mở thì không bao giờ `resizeWindow` (`:1337`), cửa sổ WINDOW_NORMAL giữ cỡ mặc định của OpenCV. Đúng AC (không dừng app); ghi giới hạn ở R2.
- **THẤP-4 — `docs/agy_usage_ledger.csv` nằm trong commit `00d320c`**, ngoài khối scope §5b (AC-U2P "file ⊆ §5b"); do orchestrator, là sổ sách, không ảnh hưởng mã.
  U2a/U2b không gộp sổ vào commit code. Lần sau tách commit sổ.
- **THẤP-5 — Quy trình/ghi chép**: (a) mục U2c trong progress không ghi impact GitNexus cho `Hud._fonts_at`, `Level1App._key`, `_window_image`, `run`,
  `build_parser` và detect-changes (quy ước `15-lan-sua-13.md` §8; `u2c_steps.txt` yêu cầu); không thấy log `u2c_impact_*` trong `_work/_plan15_l13/`.
  (b) Câu trích "hoàn tác (A)" bị gán cho kế hoạch, thật ra từ lời giao của cầu nối. (c) `u2c_steps2.txt` tự mâu thuẫn (DỪNG báo CẦN PLANNER vs tiêu đề
  chấp nhận được). (d) Dòng trạng thái "U2c xong" không có hash.
- **THẤP-6 — Thoát toàn màn hình đặt lại cửa sổ về cỡ tự nhiên**, bỏ cỡ người dùng đã kéo trước khi bấm f (thiết kế theo lời giao cầu nối). Không sai AC; ghi R2 nếu cần.

## Việc phải sửa (theo mức độ)
1. TB-1: đổi `WINDOW_NAME` sang ASCII + sửa test mới `test_key_hint_and_docstring`; kiểm lại tiêu đề thật (thăm dò `GetWindowTextW` hoặc nhìn cửa sổ).
   Sau sửa: chạy lại 3 lớp U2c + `tests.test_level1_display tests.test_level1_equivalence`; AC-U9b vẫn 0.
2. Nên làm cùng lúc (THẤP-1, THẤP-2): thêm kiểm giá trị thuộc tính bật/tắt, ca LRU truy cập lại, ca f hai lần từ chế độ thường — chỉ THÊM test.
3. THẤP-3..6: ghi giới hạn ở R2/progress; không chặn U2d.

## CẦN PLANNER (không phải người dùng)
- Chữ tiêu đề: tiếng Việt không dấu (`f: toan man hinh`) hay tiếng Anh (`f: fullscreen`). Cả hai đều ASCII; §2.2 viết gợi ý bằng tiếng Việt có dấu nên planner chốt.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có.

## Vòng 2 (2026-10-09, commit sửa `6144970`, HEAD `288feb2`): APPROVE

Phạm vi: `git show --stat 6144970` = 3 file: `level1_demo.py` (1 dòng, :104), `tests/test_level1_demo.py` (+3/-1, chỉ trong `test_key_hint_and_docstring`),
`docs/plans/15-progress.md` (+4). Các commit còn lại trong `920cb81..288feb2` (`dc054d3` ledger, `5ea94c3`/`288feb2` state) không chạm mã/test.

| Mục | Kết quả | Bằng chứng |
|---|---|---|
| TB-1 sửa đúng quyết định người dùng | PASS | `level1_demo.py:104` `WINDOW_NAME = "VSLT Level 1 (f: toan man hinh)"`, đúng chuỗi trong STATE (2026-10-09 14:07). Mọi chỗ dùng qua hằng (`:1106, :1316, :1325, :1340, :1344, :1389, :1392`); không còn chuỗi có dấu trong `level1_demo.py`, `tests/`, `scripts/` (grep). |
| Test khóa TB-1 | PASS | `tests/test_level1_demo.py:3644-3649`: `assertIn("f: toan man hinh", WINDOW_NAME)` + `assertTrue(WINDOW_NAME.isascii())`. Đột biến (worktree tạm `_work/_r2_mut`, đã gỡ): đổi lại `WINDOW_NAME` có dấu → `FAIL: test_key_hint_and_docstring` `AssertionError: 'f: toan man hinh' not found in 'VSLT Level 1 (f: toàn màn hình)'`, `Ran 3` `FAILED (failures=1)`. Có `isascii()` nên chữ có dấu chen ở chỗ khác cũng đỏ. |
| Không nới/sửa test cũ | PASS | `git diff 00d320c..6144970 --stat -- tests/` = 1 file, +3/-1; dòng bị bỏ là assert chuỗi có dấu do chính U2c thêm (TB-1 yêu cầu sửa), thay bằng assert chặt hơn. Không skip, không xóa test khác. |
| Chạy lại | PASS | `.venv/Scripts/python -m unittest tests.test_level1_demo.TestFullscreenU2c tests.test_level1_demo.TestHudFontLruU2c tests.test_level1_demo.TestParserU2c` → `_work/_plan15_l13/review_u2c_r2.log`: `Ran 8` `OK`. Khớp `u2c_fix_green.log` (`Ran 8` `OK`); `u2c_fix_red.log` `Ran 8` `FAILED (failures=1)`; `u2c_fix_green_extra.log` `Ran 53` `OK` (không chạy lại 53 test này; thay đổi chỉ là hằng chuỗi). |
| Tiêu đề thật | PASS | `_work/_plan15_l13/u2c_fix_title_probe.log`: `backend WIN32`, `title 'VSLT Level 1 (f: toan man hinh)' match True` (GetWindowTextW). Không tự mở cửa sổ lại. |
| Số liệu trong progress | PASS | 4 dòng mới chỉ là đếm test, trỏ log có thật, đã đối chiếu như trên. |

Các mục 2–13 của bảng vòng 1 không đổi (vòng này chỉ đổi một hằng chuỗi + một test). Mục 1 và 13 hết FAIL do TB-1 đã sửa và đã kiểm tiêu đề thật.

### Còn mở (THẤP, không chặn; orchestrator chuyển planner trước V1)
- THẤP-1: test bật/tắt chưa kiểm giá trị thuộc tính (`WINDOW_FULLSCREEN`/`WINDOW_NORMAL`) — chỉ THÊM test.
- THẤP-2: lỗ test LRU (chưa có ca truy cập lại cỡ cũ; FIFO sống) và ca thường → f → f.
- THẤP-3: `setWindowProperty` lỗi thì `self.fullscreen` vẫn đảo và ghi `on: true`.
- THẤP-4: `docs/agy_usage_ledger.csv` trong commit `00d320c`, ngoài khối scope §5b (sổ sách).
- THẤP-5: progress U2c thiếu impact/detect-changes GitNexus; câu trích "luật §2.2" thực ra là lời giao cầu nối.
- THẤP-6: thoát toàn màn hình đặt lại cỡ tự nhiên, bỏ cỡ người dùng đã kéo — ghi R2 nếu cần.
- Nhỏ (mới): chú thích cũ `tests/test_level1_demo.py:3646` ("hint placed in window title when tests pin small lines…") vẫn còn, đúng nhưng nên gọn khi sửa THẤP-1/2.

### CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có (tiêu đề đã được người dùng chốt 2026-10-09 14:07; mục "CẦN PLANNER" vòng 1 về chữ tiêu đề coi như đã đóng).
