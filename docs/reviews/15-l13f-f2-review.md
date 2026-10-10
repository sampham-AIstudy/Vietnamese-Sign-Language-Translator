# Review 15 — lần sửa 13f, bước F2 (`01ca9c4` + tiến độ `69a7bc6`)

Reviewer độc lập, 2026-10-11. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `80ed869`. Coder: vslt-coder-claude.
Hợp đồng: `docs/plans/15-lan-sua-13f.md` §3.3, AC-F2, AC-F2m; ĐÈ bởi `docs/plans/15-lan-sua-13f-a.md` §3.1–3.2.
Phạm vi: `git diff --numstat de0f28c..01ca9c4` = `127 12 src/inference/level1_display.py`, `316 0 tests/test_level1_display.py`
(khớp khối scope 13f-a §4). `git diff 01ca9c4..HEAD -- src tests` rỗng.

## Kết luận: APPROVE

Không có FAIL. Có 2 điểm nhỏ (mức THẤP) dưới mục "Vấn đề", không chặn F3.

## Bảng kiểm 1–13

| # | Mục | KQ | Bằng chứng |
|---|-----|----|-----------|
| 1 | Đúng kế hoạch, test thật | PASS | `TestSideLayout13f` (14 test, `tests/test_level1_display.py:717-989` tại 01ca9c4) phủ G1–G10. G3 tính `s_side` bằng `P = -(-w // 4)` literal. G4 có chống rỗng (`n_side > 0`, `n_ref_smallest > 0`) và nhánh không-side `== fit_layout(640,360,…)` (13f-a). G7 đúng 13f-a: `panel_h ∈ {200,283}`, `side_ref_h=None`, `assertIs(L.side, True)` mỗi ca, thanh hold `cv2.rectangle(E,(0,0),(int(pw·hold),scaled_px(3,ps)),(0,200,0),-1)` chỉ khi `hold > 0`, dòng thống kê literal, builder gọi đúng 1 lần `(pw,ph,L.panel_scale,n)`, pixel ngoài 2 rect = 0, chống rỗng `n_ps_differs > 0`. G8 so 3 chiều: `fit_window_layout == fit_layout`, ảnh bằng nhau, và bằng `render_to_window` của B0 `4925aaf` (nạp bằng `git show`). G10 dùng cả `10·len` và font thật `Hud._fonts_at(1.5)[1].getlength`. |
| 2 | Tự chạy lại test | PASS | `.venv/Scripts/python -m unittest tests.test_level1_display tests.test_level1_equivalence > _work/_plan15_l13/review_l13f_f2.log` ⇒ `Ran 62 tests in 88.227s` / `OK` (= 47 + 15, khớp `l13f_f2_green.log` Ran 47 OK và `l13f_f2_green_equivalence.log` Ran 15 OK). LALL không chạy lại (theo giao việc); log coder `l13f_f2_green_level1_all.log`: `Ran 702 tests` `OK (skipped=1)`. Đỏ trước: `l13f_f2_red.log` `FAILED (errors=90)`. |
| 3 | Test không bị sửa/nới | PASS | numstat tests 316/0; hunk duy nhất chèn trước `if __name__` (`@@ -672,6 +672,322 @@`). `tests/test_level1_equivalence.py` không đổi. Đột biến coder: base `Ran 47 OK`; d1 29, d2 24, d3 2, d4 2, d5 24, d6 18, d7 2, d8 1, d9 10, d10 2 failures (`l13f_f2_mut_*.log`); định nghĩa trong `l13f_f2_mutate.py:16-28` đúng mô tả AC-F2m, mỗi phép thay được assert là đã áp. Đột biến reviewer (worktree tạm từ 01ca9c4, đã gỡ): m1 panel bên TRÁI/camera bên phải ⇒ `FAILED (failures=6)` (`review_f2_mut_m1.log`); m3 resize lần 2 trên panel ⇒ lớp F2 vẫn OK (panel nền đồng màu) nhưng `TestEquivalenceE3Static.test_e3_no_hands_resize_flip_outside_display` ⇒ `FAILED` (`review_f2_mut_m3_eq.log`), tức E4 khóa đúng; m2 hòa ⇒ chọn cạnh nhau (`<=`→`<`) ⇒ `OK` (xem Vấn đề 1). |
| 4 | Nguồn gốc dữ liệu | PASS (N/A) | Chỉ hình học/vẽ hiển thị; không dữ liệu train/đánh giá. |
| 5 | Rò rỉ split | PASS (N/A) | Không chạm split. |
| 6 | VAL/TEST | PASS (N/A) | Không chọn model. |
| 7 | Số liệu truy được | PASS | Mọi số trong mục F2 của `15-progress.md` (Ran 47/15/702, failures d1–d10, errors=90) khớp log trong `_work/_plan15_l13/` (đã grep). Không có số khoa học. Coder không phải agy ⇒ các kiểm agy không áp. |
| 8 | Cỡ mẫu/CI | PASS (N/A) | Không có kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS | `level1_display.py` import chỉ `dataclasses`, `typing`, `cv2`, `numpy` (dòng 16-20), không mediapipe. Đúng 1 `cv2.resize` (`:262`, trong `render_to_window`), nhánh cạnh nhau dùng CHUNG dòng này bằng cách gán `content/width/cam_h` = ô camera (`:249-252`). Ảnh hiển thị, không chạm khung đưa vào MediaPipe. E3/E4 xanh. |
| 10 | Không mock/giả trong đường chính | PASS | Không Math.random/mock/hard-code kết quả trong `src/`. `SIDE_PANEL_REF_W = 320` là hằng thiết kế của §3.3. |
| 11 | Bảo mật | PASS (N/A) | Không API/mạng/token. Không đụng thay đổi chưa commit của người dùng (README.md, 3 file data ` D`, untracked còn nguyên). |
| 12 | So sánh công bằng/GATE | PASS (N/A) | Oracle G7 đổi ở 13f-a TRƯỚC khi có dòng mã F2 (`de0f28c` < `01ca9c4`, log đỏ 02:46 < xanh 02:49); không nới. |
| 13 | Kết luận vượt bằng chứng | PASS | Progress chỉ khẳng định điều test/log chứng minh; giả định (1)–(5) ghi rõ. "16:9 không dải đen" có G5 định lượng (1920×1080 `black == 0`, các cỡ khác ≤ 0.5%). |

## Soi mã (điểm 1 của giao việc)
- E4: `grep cv2.resize` ⇒ 1 dòng (`:262`). Không import mediapipe.
- Nhánh dọc (`:253-256`, `:274-279`): so với B0 chỉ thụt 4 dòng vào `else:` và `if panel_h > 0` → `elif panel_h > 0`; không biểu thức nào đổi (diff đã đọc). `fit_layout` 0 dòng đổi. G8 khóa bằng so với B0 `4925aaf`.
- `fit_window_layout` (`:135-167`): khớp §3.3 từng bước — `avail = w - (w+3)//4`, `num/den` cạnh nhau, so phân số số nguyên với tỉ lệ đúng của `fit_layout` (`b_num, b_den` cùng biểu thức `fit_layout:121`), hòa giữ dọc (`<=` ⇒ `below`); `cam_rect = (0,(h-ch)//2,cw,ch)` (camera trái, căn dọc), `panel_rect = (cw,0,w-cw,h)` (phải, toàn cao, `w-cw ≥ ⌈w/4⌉`); `panel_scale = min(scale,(w-cw)/320[,h/side_ref_h khi > 0])`. Tự kiểm ca hòa (1024,816), panel_h 200: cả hai scale 1.2 ⇒ `side False` (đúng).
- `render_to_window` nhánh cạnh nhau (`:263-273`): theo đúng 4 bước 13f-a §3.1, `draw_panel_overlays(panel_view, 0, …, ps)`, builder gọi với `ps = panel_scale`, kiểm sai cỡ ⇒ `ValueError` (G9b). Không thêm hàm vẽ, không sửa `draw_panel_overlays`.
- `wrap_rows` (`:170-215`): thuần, không PIL; khớp §3.3. Giả định (3) (ký tự đơn rộng hơn `max_w` bị bỏ + `…`) là thêm ngoài hợp đồng nhưng hợp lý và vẫn giữ mọi bất biến của §3.3.

## Vấn đề (theo mức)
1. THẤP — thiếu test cho luật hòa "hòa giữ dọc". Đột biến m2 (`num * b_den < b_num * den`) không đỏ ở lớp F2: lưới G3 (bước 175) và các cửa sổ G2/G4–G9 không có ca hòa chính xác. Mã hiện tại ĐÚNG (đã tự kiểm (1024,816)). Không phải AC bắt buộc của AC-F2 (G3 dùng `> … + 1e-12`, ca hòa nằm ngoài lưới). Gợi ý: F3 hoặc một lần sửa sau THÊM 1 khẳng định `fit_window_layout(640,480,200,1024,816).side is False`.
2. THẤP — G8 (`_display_module_at`, `tests/test_level1_display.py:687`) gọi `git show 4925aaf:…` lúc chạy; trong môi trường không có lịch sử git (clone nông, gói nén, Kaggle) test sẽ ERROR thay vì skip. Hiện tại xanh ở máy local. Ghi nhận cho CLOUD.md/clone nông; không chặn.

## Ghi chú cho F3
- `_window_image` phải gọi `fit_window_layout(..., side_ref_h=hud.side_panel_height(...))`; nhớ `side_ref_h ≤ 0`/None bị bỏ (G4b).
- Builder của nhánh cạnh nhau nhận `(pw, ph, panel_scale, n_stats)` với `pw = w - cw` (có thể > ⌈w/4⌉); `Hud.side_panel_builder` phải trả đúng `(ph, pw, 3)` nếu không `render_to_window` ném `ValueError`.
- Oracle H1 nên dùng chính `draw_panel_overlays` (thanh hold cả mép), như 13f-a đã chốt; `wrap_rows` có thể thêm `…` ở dòng cuối khi bỏ ký tự đơn quá rộng.
- E4: không thêm `cv2.resize` nào khác (static test E3 bắt được, đã kiểm bằng m3).

## Lệnh reviewer đã chạy
- `git diff de0f28c..01ca9c4 -- src/inference/level1_display.py tests/test_level1_display.py`; `git diff --numstat de0f28c..01ca9c4`.
- `.venv/Scripts/python -m unittest tests.test_level1_display tests.test_level1_equivalence` ⇒ `_work/_plan15_l13/review_l13f_f2.log` (Ran 62, OK).
- Worktree tạm `_work/_plan15_l13/wt_review_f2` @01ca9c4 (đã `git worktree remove --force`): m1/m2/m3 ⇒ `review_f2_mut_{m1,m2,m3,m3_full,m3_eq}.log`.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có.
