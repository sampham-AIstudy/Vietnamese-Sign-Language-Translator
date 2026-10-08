# Review độc lập — Kế hoạch 15 lần sửa 13, bước U1 (`ea9c645`) + lần sửa 13a, bước U1a (`acdcf63`)

Reviewer: vslt-reviewer, 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `9943ff7`.
Hợp đồng: `docs/plans/15-lan-sua-13.md` §2.2, §5.4, §8 (U1), §9 (AC-0, AC-1, AC-U1..U3, AC-U6), §10; `docs/plans/15-lan-sua-13a.md` (toàn bộ:
E4, AC-E4a..f, AC-0/AC-V4 sửa); `docs/reviews/15-l13-u1-bridge.md` (8 điểm). Mốc: M0 `5a32cff` (đường cơ sở mã `cad8cdc`).
Coder: U1 = vslt-coder-claude hoàn thiện WIP agy `7ae0040`; U1a = vslt-coder-claude.

## Kết luận: APPROVE

Không còn FAIL. 0 vấn đề CAO, 1 TB (lỗ hổng test, sửa ở U2), 5 THẤP. Giao U2 khi orchestrator đưa TB-1 vào hợp đồng U2.

## Test reviewer tự chạy (máy local, `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest`)

| Lệnh | Log | Kết quả | Coder khai |
|---|---|---|---|
| `tests.test_level1_equivalence tests.test_level1_display -v` (AC-E4a) | `_work/_plan15_l13/review_equiv_display.log` | `Ran 35 tests in 178.601s` — `OK`, 0 skip; E3Static 3/3, E4Display 4/4, E3Spy 2/2, E1 ok | `Ran 35` `OK` (`u1a_green_equiv_display.log`) — khớp |
| 16 module `tests.test_level1_*` + `tests.test_backend_source_guard -v` (AC-E4b) | `_work/_plan15_l13/review_level1_all.log` | `Ran 485 tests in 1267.756s` — `OK (skipped=1)`; skip duy nhất `test_u1_summary` (thiếu `_work/_plan15_u1/u1_2026-10-03_1650.json`); `[DoD7-guard] known=9 allowed=36` | `Ran 485` `OK (skipped=1)` (`u1a_green_level1_all.log`) — khớp |
| Đột biến AC-E4d, worktree tạm `_work/_plan15_l13/wt_review` tại `acdcf63` (đã `git worktree remove` + `prune`); lệnh `TestEquivalenceE3Static TestEquivalenceE4Display` | `review_mut_{base,m1,m5_bare_ref_core,m6_warp_demo,m7_dst}.log` | base `Ran 7` `OK`; m1 (`cv2.resize` trong `fit_layout`) `FAILED (failures=2)`; m5 (`_RESIZE = cv2.resize` cuối `level1_core.py`) `FAILED (failures=1)`; m6 (`cv2.warpAffine` trong `level1_demo.py`) `FAILED (failures=1)`; m7 (`dst=` trong lời gọi E4) `FAILED (failures=1)` | m1–m4 FAILED, base OK — khớp (m1 lặp lại được) |
| Đột biến động m8 (`view_bgr[0, 0] = 0` trong `render_to_window`); `TestRenderToWindowInputUnchanged TestEquivalenceE4Display` | `review_mut_m8_write_input.log` | `Ran 5` — `FAILED (failures=18)` (tĩnh không bắt — đúng thiết kế; test động bắt cả nhánh chép lẫn nhánh resize) | — |
| Đột biến m9 (chỉ gọi `draw_panel_overlays` khi `layout.scale == 1.0`); `tests.test_level1_display` | `review_mut_m9_no_overlay_scaled.log` | `Ran 22 tests` — **`OK`** ⇒ vấn đề TB-1 | — |

AC-1 đầy đủ (29 module) reviewer KHÔNG chạy lại; log coder `_work/_plan15_l13/u1a_ac1.log` (`Ran 696`, `FAILED (failures=5, errors=2, skipped=1)`)
và `m0_ac1.log` (`Ran 670`, `FAILED (failures=5, errors=2, skipped=1)`) đọc được; tập đỏ trùng tên với M0 (15-progress dòng 1473–1480).

## Bảng 13 mục

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS (kèm TB-1) | AC-U1: `tests/test_level1_display.py:112-200` (scale 2 → 2.0; 1920×1080 content_h 1080, x0 căn giữa, y0 0; 600×2000 content_w 600; (-1,-1,-1,-1)/(0,0)/None + 14 dạng hỏng ⇒ layout tự nhiên; lưới 200..4000 bước 175: trong cửa sổ, chạm cặp cạnh, tỉ lệ ≤ 1%; lưới rộng của cầu nối). Probe reviewer (trong bộ nhớ): 5 cỡ camera × panel {0,1,50,200,999} × cửa sổ 1..4000 bước 97: 0 ca ra ngoài/không chạm cạnh. AC-U2: `:214-344` (shape; mọi pixel ngoài nội dung == 0 bằng mặt nạ + 4 phía; vùng camera `array_equal` `cv2.resize`; 720 so sánh bằng hệt `Hud.compose`, assert số ca `:322`; Hud mới == Hud `cad8cdc` qua `git show`, 180 tổ hợp + 15 `_build`). AC-U3: `:355-404` (font == round(font_size×2), cỡ font PIL thật; ±2 px mỗi dòng `abs(h2−2h1) ≤ 2·n_lines`, đã bỏ `+8`; đếm `_build`: chỉ đổi stats/hold ⇒ 1, đổi chữ ⇒ 2, đổi cửa sổ ⇒ 3; `truetype` đúng 2 lần mỗi cỡ px). AC-E4c: 13 ca hợp đồng + 7 ca thêm (`tests/test_level1_equivalence.py:403-495`), nguồn hợp lệ ⇒ `[]`, file thật ⇒ `[]`. AC-E4 mục 5: `tests/test_level1_display.py:408-448` (bắt đột biến m8). AC-E4d lặp lại được. Lỗ hổng: thanh hold + dòng thống kê ở scale ≠ 1 không có test (m9 xanh) — TB-1. |
| 2 | Tự chạy lại test | PASS | 35 OK; 485 OK (skipped=1), khớp coder. Log đỏ coder `u1_red.log` (`Ran 25`, `FAILED (failures=3, errors=104)`), `u1a_red.log` (`Ran 8`, `FAILED (failures=1, errors=28)`) khớp 15-progress. |
| 3 | Test không bị sửa/skip/nới | PASS | `git diff --numstat cad8cdc..acdcf63 -- tests/`: `test_level1_display.py 452 0` (file mới L13), `test_level1_equivalence.py 211 2`, `test_level1_guard.py 1 0`, `test_agy_infra.py 130 0` (commit hạ tầng orchestrator, ngoài U1/U1a). Dòng `-` của `test_level1_equivalence.py` (`git diff ea9c645..acdcf63`): đúng 2 — `:16` (docstring) và `:273` của `ea9c645` (đã `git show` đối chiếu) — trong danh sách đóng 13a §3.3, ≤ 3. `:273` thành `E4_RESIZE_CALLS if rel == E4_FILE else []` (so cả bộ ba tên/hàm bao — chặt). `_calls` không đổi. `test_level1_guard.py`: chỉ THÊM `level1_display.py` vào `PLAN15_FILES` (E3 §5.4). Không `skip` mới (`skipUnless` duy nhất trong diff là dòng ngữ cảnh). agy-guard WIP `7ae0040` (`_work/agy_logs/20261008-141721-15-lan-sua-13.log` dòng 19-21): `các commit của agy: sạch`, `working tree: sạch`, không BLOCK. |
| 4 | Nguồn gốc dữ liệu | PASS (không áp dụng) | Không dữ liệu train/đánh giá mới. Ảnh test là ngẫu nhiên seed cố định (`_view`) chỉ để kiểm hình học hiển thị; E1/E3 spy dùng clip hauuto thật có sẵn. |
| 5 | Rò rỉ split | PASS (không áp dụng) | Không train, không split. |
| 6 | Chọn model bằng VAL | PASS (không áp dụng) | Không chọn model. `checkpoints/alphabet_best.pt` sha256 `160e0c68…a8d17899` (reviewer tự tính) = v6 M0. |
| 7 | Số liệu truy được | PASS | Không số liệu khoa học/JSON mới. `Ran/FAILED` trong 15-progress (dòng 1399-1505) khớp log `_work/_plan15_l13/*.log` (grep). Sổ agy: dòng `2026-10-08T07:57Z … 15-lan-sua-13.md … timeout` cho lần chạy tạo `7ae0040`; không dùng làm kết luận. |
| 8 | Cỡ mẫu / CI | PASS (không áp dụng) | Không kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS | `git diff 5a32cff..ea9c645 -- level1_demo.py`: chỉ lớp `Hud` + import; không đổi `_process`, `frame`/`frame_mp`, `draw_landmarks`, `display_view`. App CHƯA gọi `render_to_window` (U2). E3 spy xanh ở headless + paced (log reviewer). E4 tĩnh: đúng 1 `cv2.resize` trên tham số thứ nhất của `render_to_window`; module hiển thị chỉ import {dataclasses, typing, cv2, numpy}, không `.process`/MediaPipe. `render_to_window` không sửa đầu vào, không chung bộ nhớ (test + m8). Đường cửa sổ còn chờ AC-U6b (U2, đúng kế hoạch). |
| 10 | Không Math.random/mock/kết quả giả | PASS | Không có trong đường chính; `mock.patch.object(..., wraps=...)` chỉ trong test để đếm. Hằng có tên (`HOLD_BAR_*`, `STATS_*`, `Hud.PAD_*`…); `[DoD7-guard] known=9 allowed=36` xanh với `level1_display.py` trong `PLAN15_FILES`. |
| 11 | Bảo mật | PASS (không áp dụng) | Không API/WebSocket/CORS. `git diff --stat 5a32cff..acdcf63 --` các đường CẤM (`backend/main.py`, `realtime_demo.py`, `configs/`, `src/data/`, `fingerspelling_compose.py`, `hand_live.py`, `README.md`, kế hoạch 11/13/14, `reports/`, `tests/test_backend_source_guard.py`, `checkpoints/`): rỗng. File `ea9c645` ⊆ §10; file `acdcf63` ⊆ scope 13a. agy không push (origin ở `0570c2b`, commit state của orchestrator); không thấy `--no-verify`. |
| 12 | So sánh công bằng / GATE | PASS | Không GATE số. Ngoại lệ E4 do PLANNER quyết TRƯỚC khi E3 xanh (`232c17d`, 13a §3.2), kèm siết bù; coder không tự nới (U1 dừng, báo CẦN PLANNER — 15-progress dòng 1409-1413). |
| 13 | Kết luận vượt bằng chứng | PASS (kèm THẤP) | "Không pixel nào ra dải đen" có test thật. "Thanh hold + dòng thống kê cỡ 0.45 × scale" (§2.2) đúng ở mã (probe reviewer 1920×1080, 1280×1360, 800×2000: thanh hold đủ 100% bề rộng, có pixel dòng thống kê) nhưng chưa có test (TB-1). Giới hạn kiểm tĩnh: THẤP-2. |

## Đối chiếu 8 điểm review cầu nối

| # | Điểm cầu nối | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | CAO `fit_layout` làm tròn riêng ⇒ y0 = −1, ValueError | ĐÃ SỬA | `src/inference/level1_display.py:94-119`: tỉ lệ phân số nguyên, làm tròn 1 lần cho content_w và TỔNG content_h, `min(...)` theo cửa sổ, camera làm tròn xuống, panel phần dư. `test_u1_wide_grid_inside_window`, `test_u2_never_raises_on_rounding_edge_windows`. |
| 2 | TB panel khác ô, tràn dải đen | ĐÃ SỬA | Panel dựng đúng `panel_rect[3]` (`:159-162`, ValueError nếu builder sai giao thức); overlay vẽ trên ảnh con `content` (`:150`, `:163`); `test_u2_shape_and_every_outside_pixel_zero` (dòng thống kê rất dài, 10 cửa sổ). |
| 3 | TB AC-U3 `2n+8` | ĐÃ SỬA | `tests/test_level1_display.py:372-373` `≤ 2 * n_lines`. |
| 4 | TB test yếu | ĐÃ SỬA | `:97-110`, `:224-229`, `:304-322` (4 cách cho cửa sổ tự nhiên). |
| 5 | TB `ScalableHud` chép Hud | ĐÃ SỬA | Không còn lớp HUD trong `level1_display.py`; `Hud` nhận `scale` + `panel_builder`; test bằng hệt Hud `cad8cdc`. |
| 6 | THẤP–TB `inspect.signature`, số gõ tay | ĐÃ SỬA | Một giao thức `PanelBuilder` (`:20-23`); không `inspect`; không font dự phòng 18; `layout` bắt buộc. |
| 7 | THẤP `__eq__`, tuple 4, import thừa | ĐÃ SỬA | dataclass frozen so 9 trường; `test_u1_rect_four_tuple_is_x_y_w_h`; import `:12-16` đều dùng. |
| 8 | Quy trình | ĐÃ SỬA (kèm THẤP-4) | `u1_red.log`, mục U1 15-progress, `u1_impact*.log`, `u1_detect_changes*.log`, `tests/test_level1_guard.py:32`. |

## Vấn đề

### CAO
(không có)

### TRUNG BÌNH
- **TB-1 Thanh hold + dòng thống kê ở cửa sổ co giãn không có test khóa.** `src/inference/level1_display.py:163`. Không test nào trong
  `tests/test_level1_display.py` kiểm ở scale ≠ 1 rằng thanh hold có mặt (cao `scaled_px(3, s)`, rộng `int(content_w × hold)`) và dòng thống kê có mặt ở
  hàng đáy ô panel với cỡ `0.45 × scale` (§2.2). Cách kiểm: đột biến m9 (chỉ gọi `draw_panel_overlays` khi `layout.scale == 1.0`) ⇒ `tests.test_level1_display`
  `Ran 22` **OK** (`_work/_plan15_l13/review_mut_m9_no_overlay_scaled.log`). Ở scale 1.0 có khóa (720 so sánh với `Hud.compose`). Mã hiện tại ĐÚNG (probe
  reviewer) và AC-U1..U3 không ghi điều này thành tiêu chí, nên không chặn APPROVE. Yêu cầu: THÊM test ở U2, trước khi đo AC-U5 — vd. 1920×1080 và 1280×1360,
  hold 1.0: mọi pixel hàng `panel_rect[1] .. +scaled_px(3, s)` trong `[x0, x0 + int(content_w × hold))` == (0,200,0); hold 0 ⇒ không có; có pixel màu
  `STATS_BGR` ở hàng đáy ô khi có stats, không có khi `stats=[]`; chiều cao nét chữ thống kê ở scale 2 ≈ 2× scale 1 (dung sai planner chốt).

### THẤP
- **THẤP-2 Kiểm tĩnh E4 còn lối vòng ngoài danh sách đóng.** `_e4_violations` (`tests/test_level1_equivalence.py:280-363`) trả `[]` khi thêm vào
  `src/inference/level1_core.py`: `vars(cv2)["resize"](frame, (2, 2))`, `cv2.__dict__["resize"](...)`, `cv2.dnn.blobFromImage(frame, 1.0, (2, 2))` (có
  resize), `cv2.getRectSubPix(...)` (probe trong bộ nhớ, không ghi file). Không phải lỗi coder (13a §3.2 là danh sách đóng; 13a §6 đã nêu giới hạn kiểm tĩnh).
  Lưới đỡ: E3 spy (`is` đối tượng reader) bắt mọi biến đổi tạo mảng mới ở headless/paced; AC-U6b sẽ phủ đường cửa sổ. Đề nghị planner ghi vào Giới hạn ở R2.
- **THẤP-3 Bước U1 có 2 commit**; `7ae0040` mang tiêu đề `WIP 15: agy bị ngắt (timeout)…` (không khớp `^15: L13-` của AC-0), do cầu nối agy `savewip` khi hết
  giờ, không do coder Claude. Ghi nhận, không sửa lịch sử.
- **THẤP-4 Log đỏ U1 tạo SAU code xanh.** `u1_red.log` mtime 15:59:26 > `u1_green_main.log` 15:58:11; coder ghi rõ là chạy test cuối trên worktree tại
  `7ae0040` (15-progress dòng 1398-1402). Bằng chứng hợp lệ rằng test bắt lỗi cũ, nhưng không phải "test viết trước". U1a đúng thứ tự (`u1a_red.log` 23:08:20
  < `u1a_green_equiv_display.log` 23:13:32).
- **THẤP-5 Cache font không giới hạn.** `level1_demo.py` `Hud._fonts_at`: mỗi cỡ px mới giữ 2 `FreeTypeFont` mãi; khi U2 đọc `getWindowImageRect` mỗi khung,
  kéo giãn cửa sổ sinh nhiều cỡ. Bộ nhớ nhỏ; U2 cân nhắc giới hạn (giữ N cỡ gần nhất) — không bắt buộc.
- **THẤP-6 `test_reset_segments_and_graphs` đỏ 3/3** trong luật 3 lần của U1a (`u1a_flaky_reset_{1,2,3}.log`), M0 đỏ 3/4. Không do U1/U1a (module không
  import file bị sửa), "cùng trạng thái M0" nên đạt AC-1 bước này; nhưng gọi "chập chờn" khi đỏ liên tục là đáng ngờ — AC-1 sau V1 đòi 0 FAIL trừ chập chờn
  theo luật 3 lần ⇒ planner cần xem trước V1/R2.

## Ghi chú agy (dòng 3, 7, 11)
- Chỉ `7ae0040` do agy (gemini-3.8-flash-high, high; sổ `docs/agy_usage_ledger.csv` dòng `2026-10-08T07:57Z … timeout`). Guard sạch, không BLOCK. Mã agy đã được
  coder Claude viết lại ở `ea9c645` và review ở đây.
- Commit `7f08e0e` (agy savewip, chỉ `docs/agy_usage_ledger.csv`, log `_work/agy_logs/20261008-162318-15-lan-sua-13.log`) KHÔNG nằm trên nhánh nào (commit
  treo); dòng sổ của lần chạy đó không có trong HEAD — thông tin cho orchestrator.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có.

## Việc cho orchestrator
1. Commit file này.
2. Giao U2 kèm AC-U6 (sửa) + AC-U6b (13a), CỘNG test TB-1 (chỉ thêm, `tests/test_level1_display.py`); cân nhắc THẤP-5.
3. Chuyển THẤP-2, THẤP-6 cho planner (Giới hạn R2 / xem trước V1).
