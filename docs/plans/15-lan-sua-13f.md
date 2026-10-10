# Kế hoạch 15 — LẦN SỬA 13f: giao diện demo Cấp 1 theo phản hồi cửa sổ thật (VU 2026-10-10 14:50)

> LẦN SỬA 13f-a (docs/plans/15-lan-sua-13f-a.md, 2026-10-11): G7 oracle thanh hold = cv2.rectangle cả mép (khớp draw_panel_overlays/H1/U7, khóa M0 cad8cdc), chỉ khi hold>0; G4/G7 panel_h ∈ {200,283}, G7 side_ref_h=None + chống rỗng; nhánh dọc render_to_window giữ nguyên B0. Đè lên AC-F2 và §3.3.

CẦN NGƯỜI DÙNG (KHÔNG chặn bước code F1–F4): một lần nhìn cửa sổ thật sau F4 (việc VU2, §7). Mọi bước code và đo tự chạy được.

Ngày: 2026-10-10. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc lập `4925aaf` (gọi là B0). Mốc test gần nhất: K2 `3a78019`, LALL `Ran 681`,
`OK (skipped=1)` (`docs/plans/15-progress.md:1883`). Đầu vào: STATE "Quyết định của người dùng" 2026-10-10 14:50 (4 ý, không hỏi lại),
`15-lan-sua-13.md` §2 và §9, `13a` (E4), `13b` §5 (AC-U4/U4b/U6b/U7/U9/U9b), `13c` (DC1 fail-closed, T1/T2, W1 tại `15-progress.md:1711-1726`).

Hiệu lực: THÊM các bước F1–F4 và VU2. THAY câu 2 của Giới hạn R2 ở `13c` §8 bằng câu ở §8 tài liệu này. Mọi tiêu chí cũ giữ nguyên, gồm DC1 (ngưỡng
1.25, fail-closed), E1–E4, AC-U1…U9b, AC-T1/T2. Có ĐÚNG MỘT ngoại lệ sửa test mới là **E5** (§5.0), danh sách đóng.

## 1. Mục tiêu và DoD

Sửa giao diện app desktop Cấp 1 (`level1_demo.py`) theo 4 ý của người dùng:
- (1) ảnh camera không còn co hoặc dịch khi nội dung panel đổi;
- (2) ở cửa sổ rộng hoặc toàn màn hình 16:9: camera bên TRÁI, panel bên PHẢI, không còn dải đen lớn;
- (3) giữ tiêu đề ASCII đọc được;
- (4) dòng cử chỉ luôn hiện, khi không có gì thì ghi `none`.

Chỉ đổi phần HIỂN THỊ. Đường khung vào MediaPipe, model, checkpoint và mọi JSON kết quả giữ nguyên.

DoD phục vụ: hạng mục 5 (giao diện demo, ưu tiên 1 theo quyết định 2026-10-10 02:12 "hoàn thiện Cấp 1 để DEMO bằng app desktop") và bất biến
train ↔ realtime (E3/E4/AC-U6b không đổi).

## 2. Hiện trạng (B0 = `4925aaf`)

- `level1_demo.py`
  - `:113` `WINDOW_NAME = "VSLT Level 1 (f: toan man hinh)"`, ASCII, đã khóa bằng `tests/test_level1_demo.py:3644-3649`. Ý (3) đã đạt.
    W1 đọc tiêu đề thật khớp (`15-progress.md:1722`).
  - `:466-688` `Hud`:
    - `panel_height` `:543` tính theo SỐ DÒNG `small` (`len(small) + n_stats`);
    - `_build` `:569`, `compose` `:660` (vstack camera + panel), `panel_builder` `:674`.
    - Hằng số: `LINE_RATIO 1.35`, `SMALL_LINE_RATIO 0.95`, `PAD_X 8`.
    - Font cấu hình `hud_font_size 26` (`configs/level1_realtime.json:128-131`) ⇒ bước dòng 35 / 24 px.
  - `:1301-1337` `_hud_lines()`: `small` có số dòng THAY ĐỔI theo trạng thái:
    - dòng cử chỉ chỉ có khi `_gesture_line()` khác None (`:1319-1322`);
    - góc tay `:1323`, đổi dấu `:1325-1330`;
    - mỗi cảnh báo 1 dòng, không giới hạn số dòng (`:1331-1332`).
    Đây là NGUYÊN NHÂN GỐC của ý (1): panel đổi cao thì cỡ tự nhiên đổi. Sau lần `resizeWindow` đầu, rect cửa sổ giữ nguyên, nên khung đó đi
    `render_to_window` với `fit_layout` dọc và camera co 0.964, dịch 11 px (W1: 2/69 khung, `15-progress.md:1721-1725`).
  - `:1239-1254` `_gesture_line()` trả None khi không có gì (ý 4). `:1221-1237` `_gesture_engine_line()` cũng vậy.
  - `:1402-1407` trong `_process`: `display_view` → `_hud_lines()` → `_window_image` → `imshow`.
  - `:1419-1441` `_window_image`:
    - `resizeWindow` một lần về cỡ tự nhiên;
    - đọc `getWindowImageRect`, rồi `fit_layout(w, h, panel_h, rect)`;
    - bằng cỡ tự nhiên thì `Hud.compose`, khác thì `render_to_window`.
  - `:1134-1143` phím f.
- `src/inference/level1_display.py`
  - `fit_layout` `:94-119`: CHỈ xếp dọc. Ở 1920×1080, nội dung có tỉ lệ khoảng 640:(480+panel) nên hai bên có dải đen rộng (ý 2).
  - `DisplayLayout` `:41-58`: 9 trường; `__iter__` trả 7 trường.
  - `render_to_window` `:140-164`: camera = `content[:cam_h]`, panel = `content[cam_h:]` (giả định xếp dọc). Có DUY NHẤT 1 lời gọi
    `cv2.resize(view_bgr, …)` (ngoại lệ E4).
  - `draw_panel_overlays` `:122-137`.
- Test khóa hành vi hiện có (KHÔNG được sửa, trừ E5):
  - `tests/test_level1_display.py`: `TestFitLayoutAcU1`, `TestRenderToWindowAcU2` (gồm `test_u2_natural_equals_hud_compose` và test M0
    `test_u2_hud_scale_one_identical_to_m0_hud` so `Hud` với `cad8cdc`), `TestScaledPanelAcU3`, `TestRenderToWindowInputUnchanged`,
    `TestU2OverlaysScaled`, `TestU2OverlaysExactT1`.
  - `tests/test_level1_demo.py`:
    - `TestLatencyAcL.test_l1_window_mode_measures_every_stage` `:494` (ảnh cao hơn khung camera, tức panel ở DƯỚI ở cỡ tự nhiên);
    - `TestScaledWindowU2b` `:3301-3443`:
      - 1080p: mọi ảnh (1080, 1920, 3) và `render_calls == frames`;
      - dự phòng: ảnh bằng `Hud.compose` của chính đầu vào app truyền;
      - `resizeWindow` 1 lần;
    - `TestFullscreenU2c`;
    - `TestWindowAndFullscreenU2t2`: W1a `:3656`, **W1b `:3681-3707`** (khóa bố cục DỌC ở 1080p), F1, L1;
    - các test nội dung `_hud_lines()` (S2 `:2465-2487`, P3 `:2865-2888`, D9 `:4091-4120`…).
  - `tests/test_level1_equivalence.py`:
    - E3 tĩnh và E4: `level1_display.py` chỉ được import ⊆ {`__future__`, `dataclasses`, `typing`, `math`, `cv2`, `numpy`}; đúng 1 resize;
    - AC-U6b.
- `scripts/level1_display_cost.py` (DC1):
  - bọc `app_module.render_to_window` và `Hud.compose` để đếm `path_counts`;
  - rect "tự nhiên" = cỡ ảnh `imshow` gần nhất.

Thiếu: panel có số dòng cố định; bố cục cạnh nhau; dòng cử chỉ luôn có; tách cỡ chữ panel khỏi cỡ camera ở bố cục cạnh nhau; xuống dòng cho panel hẹp.

## 3. Thiết kế

### 3.1 Lựa chọn của planner (và lý do)
- **Panel cố định = số "ô" (slot) cố định.** App không truyền `small` có số dòng thay đổi nữa. App truyền danh sách ô `slots` có độ dài
  KHÔNG đổi trong cả lượt chạy; ô trống là `""` để giữ chỗ.
  - Hệ quả: cỡ tự nhiên là hằng số, rect luôn bằng cỡ tự nhiên, nên mọi khung đi `Hud.compose` và camera không co, không dịch.
  - Ở bố cục co giãn, `panel_h` cũng là hằng số, nên `cam_rect` chỉ phụ thuộc cỡ cửa sổ.
- **Giữ đường tự nhiên DỌC và giữ nguyên `Hud.compose`/`_build`** (không sửa 1 dòng nào của `Hud.compose`, `_build`, `panel_height`,
  `panel_builder`, `_fit_committed`, `_fonts_at`).
  - Test M0 (`cad8cdc`) vẫn xanh, không cần ngoại lệ. Lý do: test M0 so HÀM vẽ trên cùng đầu vào, còn thứ đổi là ĐẦU VÀO app truyền vào
    (thêm ô giữ chỗ, dòng `none`).
  - Ảnh tự nhiên của APP đổi đúng theo ý (1) và (4). Đây là thay đổi có chủ đích, không phải nới test.
  - Các test dự phòng U4b, W1a, `TestLatencyAcL` (panel dưới camera) vẫn đúng nguyên văn.
  - Phương án bị loại: tự nhiên = cạnh nhau. Phương án này làm đỏ `TestLatencyAcL :494`, U4b, U2b, W1a, nên phải có ngoại lệ rộng. Thêm vào
    đó, cửa sổ tự nhiên rộng 960 px trên màn nhỏ không có lợi rõ ràng.
- **Bố cục cạnh nhau khi cửa sổ rộng.** Hàm mới `fit_window_layout` tính cả hai bố cục rồi chọn bố cục có cỡ camera LỚN HƠN:
  - bố cục DỌC = `fit_layout`, giữ nguyên;
  - bố cục CẠNH NHAU = camera sát trái, panel phải phủ hết chiều cao.
  - Hòa thì chọn dọc.
  - Ở cửa sổ tự nhiên thì luôn chọn dọc (cạnh nhau cho tỉ lệ 0.75 < 1).
  - Với cửa sổ 16:9 bất kỳ: panel tối thiểu = ⌈W/4⌉, phần còn lại 3W/4 = 4H/3, vừa khít ảnh 4:3 cao H, nên dải đen bằng 0 (sai số làm tròn).
  - Phương án bị loại: bố cục cạnh nhau với panel cùng cỡ chữ của camera. Ở 1080p chữ ×2.25 trong panel 480 px thì gần như mọi dòng bị cắt.
- **Đi qua `render_to_window` (tổng quát hóa theo rect)**, không thêm hàm vẽ mới. Lý do:
  - E4 vẫn đúng 1 `cv2.resize` trong đúng hàm đó;
  - DC1 (`path_counts`) và AC-U4 (`render_calls == frames`) vẫn đo đúng đường;
  - với bố cục dọc, ảnh phải BẰNG HỆT trước (các test U2/U7/T1/E4 khóa).
- **Panel cạnh nhau có cỡ chữ riêng `panel_scale`** và **xuống dòng theo hạn mức cố định**. Mỗi ô được tối đa 2 dòng, riêng ô cuối (dòng phím)
  được 3 dòng. Phần tràn bị cắt, kết thúc bằng `…`.
  - Số dòng panel cạnh nhau = 2·(n−1)+3, cố định, nên vị trí dòng không phụ thuộc nội dung.
  - Hằng thiết kế `SIDE_PANEL_REF_W = 320` (đặt TRƯỚC mọi lần đo): panel rộng 320 px ứng với cỡ chữ tự nhiên. Ở 1920×1080 panel rộng 480 px,
    nên cỡ chữ ×1.5, tức chữ chính 39 px.
  - Không chỉnh hằng này theo kết quả DC1/VU2. Muốn đổi thì planner lập lần sửa mới.

### 3.2 Ô của panel (`Level1App._panel_lines`, MỚI)
`_panel_lines() -> (tb_view, slots, progress, stats)`. `tb_view`, `progress`, `stats` giống hệt `_hud_lines()` tại cùng trạng thái.

`slots` theo thứ tự:
1. `small[0]` của `_hud_lines()`: ký hiệu cuối.
2. `small[1]`: dòng decoder hoặc trạng thái.
3. (CHỈ khi `self.detection_custom`) dòng `[MP: …]`, giống hệt `_hud_lines`.
4. (CHỈ khi `self.hand_lock is not None`) `self._hand_line()`.
5. **ô cử chỉ, LUÔN có**:
   - lấy `_gesture_line()` khi có cử chỉ được bật và hàm trả khác None;
   - ngược lại (gồm cả khi tắt cử chỉ) là hằng mới `GESTURE_NONE_LINE = "[Cử chỉ: none]"`.
6. **ô cảnh báo (1 dòng)**, theo thứ tự ưu tiên:
   - `ANGLE_HINT_LINE` nếu `foreshortened_run > FORESHORTEN_FRAMES`;
   - nếu không thì `"Cảnh báo: " + code` của cảnh báo CUỐI CÙNG;
   - nếu không thì dòng `"đổi dấu: x → y"` (chuỗi giống `_hud_lines`);
   - nếu không thì `""`.
7. dòng phím, giống hệt dòng cuối của `_hud_lines`.

Số ô = 5 + [detection_custom] + [hand_lock]. Số này là hằng trong một lượt chạy (chỉ phụ thuộc cờ và cấu hình).

`_hud_lines`, `_gesture_line`, `_gesture_engine_line`, `_decoder_line`, `_hand_line` KHÔNG sửa (0 dòng `-`). Các test nội dung cũ vẫn kiểm đúng các
chuỗi mà panel dùng. JSON và sự kiện không đổi. Panel chỉ HIỂN THỊ 1 cảnh báo; JSON vẫn đủ.

### 3.3 Hợp đồng `src/inference/level1_display.py`
- `DisplayLayout` có thêm 2 trường cuối, có mặc định: `side: bool = False`, `panel_scale: Optional[float] = None`.
  - `__iter__` giữ 7 phần tử.
  - Gọi bằng 9 đối số vị trí như cũ thì vẫn bằng (`test_u1_*` không đổi).
  - `fit_layout` KHÔNG đổi một dòng nào.
- `SIDE_PANEL_REF_W = 320`.
- `fit_window_layout(cam_w, cam_h, panel_h, win_w=None, win_h=None, side_ref_h=None) -> DisplayLayout`:
  - Cửa sổ không hợp lệ (luật `_window_size`) ⇒ `fit_layout(cam_w, cam_h, panel_h)` (tự nhiên).
  - `below = fit_layout(cam_w, cam_h, panel_h, w, h)`.
  - Bố cục cạnh nhau, chỉ dùng số nguyên và tỉ lệ đúng như `fit_layout`:
    - `P = (w + 3) // 4`, `avail = w − P`. Nếu `avail < 1` ⇒ trả `below`.
    - `num, den = (h, cam_h) if h * cam_w <= avail * cam_h else (avail, cam_w)`; `scale = num / den`.
    - `cw = min(avail, max(1, _round_ratio(cam_w, num, den)))`, `ch = min(h, max(1, _round_ratio(cam_h, num, den)))`.
    - `cam_rect = (0, (h − ch) // 2, cw, ch)`, `panel_rect = (cw, 0, w − cw, h)`.
    - `panel_scale = min(scale, (w − cw) / SIDE_PANEL_REF_W, h / side_ref_h)`. Bỏ vế cuối khi `side_ref_h` là None hoặc ≤ 0.
    - `x0 = y0 = 0`, `content_w = w`, `content_h = h`, `side = True`.
  - Chọn bố cục cạnh nhau ⇔ `scale_side > below.scale` (so phân số bằng số nguyên). Ngược lại trả ĐÚNG đối tượng-giá trị `below`
    (`side False`, `panel_scale None`).
- `render_to_window` giữ chữ ký:
  - ảnh hiển thị vào `cam_rect`: chép nếu đúng cỡ, ngược lại dùng ĐÚNG 1 `cv2.resize(view_bgr, (cw, ch), interpolation=cv2.INTER_LINEAR)`;
  - panel dựng bằng `panel_builder(pw, ph, ps, n_stats)` với `ps = layout.panel_scale if not None else layout.scale`, đặt vào `panel_rect`;
  - thanh hold và dòng thống kê vẽ trên VÙNG PANEL theo `ps` (thanh ở mép trên panel; thống kê ở các dòng đáy panel);
  - pixel ngoài `cam_rect ∪ panel_rect` = 0;
  - với bố cục dọc, ảnh bằng hệt bản B0 (test cũ khóa).
  - `ValueError` khi builder trả sai cỡ (như cũ).
- `wrap_rows(text, measure, max_w, budget) -> List[str]` (thuần, `measure` là callable độ rộng px, không import PIL):
  - trả ĐÚNG `budget` phần tử; ngắt tham lam theo khoảng trắng; từ dài hơn `max_w` thì cắt theo ký tự;
  - mỗi dòng khác rỗng có `measure ≤ max_w`;
  - khi tràn, dòng cuối kết thúc bằng `"…"` và vẫn ≤ `max_w`;
  - `text` rỗng ⇒ `[""] * budget`;
  - `budget < 1` ⇒ `ValueError`;
  - `measure("…") > max_w` ⇒ `[""] * budget`.
- Import của module vẫn ⊆ tập E4. `math` được phép.

### 3.4 Hợp đồng `level1_demo.py` (chỉ hiển thị)
- `GESTURE_NONE_LINE`, `_panel_lines` (§3.2). Trong `_process`, dòng `self._hud_lines()` ở `:1403` đổi thành `self._panel_lines()`. Đó là dòng duy nhất
  được sửa trong `_process`.
- `Hud` THÊM (không sửa method cũ):
  - `SIDE_ROWS_PER_SLOT = 2`, `SIDE_ROWS_LAST_SLOT = 3`;
  - `side_rows(slots, scale, width) -> List[str]`: nối `wrap_rows(slot_i, small_font(scale).getlength, width − 2·scaled_px(PAD_X, scale), budget_i)`,
    trong đó `small_font(scale) = self._fonts_at(scale)[1]`;
  - `side_panel_height(n_slots, n_stats, scale=1.0)` = `panel_height` của một view dict với `2·(n_slots−1)+3` dòng nhỏ;
  - `side_panel_builder(text_or_view, slots) -> PanelBuilder`: `build(w, h, s, n)` = `self._build(w, text_or_view, self.side_rows(slots, s, w), n, s, h)`,
    cache theo `(w, h, s, font_px, view_key, tuple(slots), n)`; trả `(panel, line_steps(s)[1])`.
- `_window_image(view, text_or_view, small, hold, stats)`:
  - giữ chữ ký; `small` được hiểu là danh sách ô;
  - `panel_h = hud.panel_height(...)` và `resizeWindow` một lần như cũ;
  - `layout = fit_window_layout(w, h, panel_h, rect, side_ref_h=hud.side_panel_height(len(small), len(stats)))`;
  - `layout == fit_layout(w, h, panel_h)` ⇒ `Hud.compose`. `layout.side` ⇒ `render_to_window(view, hud.side_panel_builder(...), …)`. Ngược lại ⇒
    `render_to_window(view, hud.panel_builder(...), …)` như cũ.
- `WINDOW_NAME`, phím f, `--fullscreen`, `--display-mirror`, `frame`/`frame_mp`/`draw_landmarks`/`display_view`, `_key`: KHÔNG đổi.

### 3.5 Luồng dữ liệu (không đổi phần suy luận)
reader → `frame` → `session.process(frame_mp)` → segmenter/decoder/speller (không đổi) → `draw_landmarks(frame)` → `display_view` →
`_panel_lines()` (MỚI, thay `_hud_lines()`) → `_window_image` → `fit_window_layout` → `Hud.compose` | `render_to_window` → `imshow`.
Module tiền xử lý chung (`src/data/alphabet_preprocessing.py`, `level1_core`, `level1_segmenter`) không bị chạm.

## 4. Chia việc

Mỗi bước có mã là 1 commit, rồi cầu nối xác minh, rồi vslt-reviewer, rồi mới giao bước kế.

| Bước | Nội dung | Phụ thuộc | Giờ | Coder | Lý do chọn |
|---|---|---|---|---|---|
| F1 | Panel cố định + dòng cử chỉ `none` (§3.2): `GESTURE_NONE_LINE`, `_panel_lines`, `_process` dùng nó. Test THÊM lớp mới cuối `tests/test_level1_demo.py` (AC-F1), viết trước, có log đỏ. Commit `15: L13f-F1 …`. | — | 1,25 | `vslt-coder-claude` | Chạm `_process` (vòng lặp chính, cạnh đường khung); test mới cần `@unittest.skipUnless(not _MISSING, SKIP_REASON)` mà agy-guard chặn nhầm (backlog 0c); agy từng bịa hash. |
| F2 | `src/inference/level1_display.py` (§3.3) + test THÊM cuối `tests/test_level1_display.py` (AC-F2). Không chạm app. Commit `15: L13f-F2 …`. | F1 APPROVE | 1,5 | `vslt-coder-claude` | Vùng nhạy cảm E4: sửa `render_to_window` (hàm có ngoại lệ resize). |
| F3 | Nối app (§3.4): `Hud.side_rows/side_panel_height/side_panel_builder`, `_window_image` dùng `fit_window_layout`. Test THÊM (AC-F3) + ngoại lệ E5 (W1b). Commit `15: L13f-F3 …`. | F2 APPROVE | 1,5 | `vslt-coder-claude` | Vùng nhạy cảm: hiển thị + E4 + chế độ cửa sổ của AC-U6b. |
| F4 | Cầu nối: (a) DC1 đo lại 3 lần, commit JSON lần 1 `15: L13f-F4 báo cáo display_cost.json`; (b) thăm dò cửa sổ thật W2 (script ở `_work/`, không commit); ghi progress (commit docs `15: L13f-F4 W2 …`). | F3 APPROVE | 0,5 | cầu nối/orchestrator | Chỉ chạy lệnh. |
| VU2 | Người dùng nhìn cửa sổ thật (§7). | F4 | — | NGƯỜI DÙNG | Nghiệm thu UX. |

Tổng thời gian coder khoảng 4,25 giờ (Claude). Vẫn giữ quy ước của `15-lan-sua-13.md` §8 và `13c` §4:
- chạy impact (GitNexus) TRƯỚC khi sửa `render_to_window`, `DisplayLayout`, `draw_panel_overlays` (F2), `_process`, `_window_image`, `Hud` (F1/F3);
- log `_work/_plan15_l13/l13f_<bước>_impact.log` và `..._detect.log`; risk HIGH/CRITICAL thì ghi vào progress kèm danh sách caller;
- `detect-changes --scope all` trước commit;
- commit bằng `git commit -- <đường dẫn>`; KHÔNG stage `README.md` và 3 file ` D`;
- không push; sổ hạn mức do orchestrator commit riêng.

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

Ký hiệu:
- `PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python`; log ở `_work/_plan15_l13/`.
- `LALL = PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard`.
- B0 = `4925aaf`.
- "state (x)" là các trạng thái app do test tự đặt bằng gán thuộc tính hoặc stub, không cần dữ liệu thật. Danh sách:
  - (a) mới dựng;
  - (b) `--gesture-space`, đang giữ lòng bàn tay (`_gesture_line()` ra `[Cử chỉ: Dấu cách …]`);
  - (c) vừa phát space (flash);
  - (d) không bật cử chỉ nào;
  - (e) `foreshortened_run = FORESHORTEN_FRAMES + 1`;
  - (f) `speller` được thay bằng stub có `view` chứa 3 cảnh báo;
  - (g) stub `view` có `tone_changes` khác rỗng;
  - (h) gộp (c) + (e) + (f) + (g) và một cảnh báo dài hơn 300 ký tự;
  - (i) `paused = True`.

### 5.0 Ngoại lệ sửa test E5 (đóng)
`tests/test_level1_demo.py`, `test_w1b_window_image_scaled_layout`. Chỉ được xóa các dòng `:3699-3703` của bản B0 (`ph = …`, `L = …fit_layout…`,
`cam_h = …`, `cam_region = …`, `expected_cam = …`), tối đa 5 dòng `-`.

Dòng thay thế giữ ĐÚNG ý cũ: vùng camera của `out_b` == `cv2.resize(view, (cw, ch), interpolation=cv2.INTER_LINEAR)` tại `L.cam_rect` của
`fit_window_layout(640, 480, ph, (0, 0, 1920, 1080), side_ref_h=app.hud.side_panel_height(len(small), 1))`, trong đó `ph = app.hud.panel_height(tov, small, 1)`.
Thêm `assertTrue(L.side)`. `:3704-3705` (assert camera, pixel hold `(0,200,0)`) giữ nguyên.

Lý do: W1b khóa bố cục DỌC ở 1080p, mà người dùng đã bác bố cục này (ý 2). Đây không phải nới test: phép kiểm pixel vẫn chính xác như trước.

Mọi dòng có sẵn khác của MỌI file test: 0 dòng xóa. `tests/test_level1_equivalence.py` vẫn ≤ 3 dòng xóa tính từ `ea9c645` (E4), và 13f không sửa file này.

### AC-F1 (F1 — lớp mới `TestFixedPanel13f`, `@unittest.skipUnless(not _MISSING, SKIP_REASON)`)
1. `app_mod.GESTURE_NONE_LINE == "[Cử chỉ: none]"` (literal trong test).
2. Ở mọi state (a)–(i): `_panel_lines()[0] is`/`==` `_hud_lines()[0]` (so `==`), `[2]` bằng, `[3]` bằng.
3. Oracle ô, mỗi state 1 `subTest`. Đặt `s = _hud_lines()[1]`. Kỳ vọng VIẾT TRONG TEST, ghép từ `s` theo luật §3.2:
   - `[s[0], s[1]] + [MP?] + [hand?] + [G] + [A] + [s[-1]]`;
   - `G` = chuỗi bắt đầu `"[Cử chỉ:"` hoặc `"[Ký hiệu:"` trong `s` nếu có, ngược lại `GESTURE_NONE_LINE`;
   - `A` = `ANGLE_HINT_LINE` nếu có trong `s`; nếu không, phần tử CUỐI bắt đầu `"Cảnh báo: "`; nếu không, phần tử bắt đầu `"đổi dấu: "`;
     nếu không, `""`.
   - Kỳ vọng `slots == expected`.
   - State (h) phải cho `A == ANGLE_HINT_LINE`. Riêng (f) cho `A ==` cảnh báo thứ 3.
4. Cố định: trong cùng một app, `len(slots)` và `app.hud.panel_height(tb, slots, len(stats))` bằng nhau ở mọi state (a)–(i).
   - `len(slots) == 5 + int(app.detection_custom) + int(app.hand_lock is not None)`.
   - Chạy thêm một app có `--dominant-hand lock` và cờ làm `detection_custom` True (coder ghi cờ vào progress); ở app đó `len(slots) == 7`.
5. Ô cử chỉ nằm ở chỉ số cố định `2 + int(detection_custom) + int(hand_lock is not None)`. Ô này == `GESTURE_NONE_LINE` ở (a), (d), (i); ==
   `_gesture_line()` ở (b), (c).
6. Nối app: chạy app trên clip D2 ở chế độ cửa sổ (không `--pace`, đọc mọi khung) với recorder kế thừa `_ScaledWindowRecorder` (KHÔNG sửa lớp cũ).
   Recorder có `getWindowImageRect` trả `(0, 0, w, h)` của lần `resizeWindow` gần nhất, mô phỏng cửa sổ thật W1; trước lần resize đầu thì ném
   `cv2.error`. Bọc `app._panel_lines` để ghi kết quả, bọc `Hud.compose` để ghi `small` được truyền. Kỳ vọng:
   - với mọi khung, `small` truyền vào `compose` == `slots` mà `_panel_lines` trả ở khung đó;
   - tập shape ảnh `imshow` có đúng 1 phần tử;
   - số lần gọi `render_to_window` == 0;
   - `len(rec.resized) == 1`.
7. Pixel. `ref` = ảnh của `_window_image(view, tb_a, slots_a, 0.0, stats)`, rect `(0, 0, 640, 480 + ph)`. `alt` = ảnh của
   `_window_image(view, tb_h, slots_h, 0.6, stats)`, cùng rect. Kỳ vọng `ref.shape == alt.shape` và `array_equal(ref[:480], alt[:480])`.
   Lặp lại khi `getWindowImageRect` ném `cv2.error`.
- Lệnh:
  - `PY -m unittest tests.test_level1_demo.TestFixedPanel13f -v > l13f_f1_red.log 2>&1` trên mã B0 (test viết trước) ⇒ `FAILED`/`ERROR`;
  - sau khi sửa ⇒ `l13f_f1_green.log` `OK`, không skip;
  - mtime log đỏ < log xanh, chép bằng `stat -c '%y'`.
- `LALL > l13f_f1_green_level1_all.log 2>&1` ⇒ `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`, `Ran` = 681 + số test mới (ghi số thật).
- `PY -m unittest tests.test_level1_equivalence -v` ⇒ `OK` (E3 spy, E4, AC-U6b chạy, không skip).
- **AC-F1m** (đột biến; cầu nối chạy trong worktree `_work/_plan15_l13/wt_13f_f1` tại commit F1, xóa sau; chỉ chạy lớp mới). Mọi đột biến phải `FAILED`:
  - f1: `_process` gọi lại `_hud_lines()`;
  - f2: bỏ ô cử chỉ khi `_gesture_line()` là None;
  - f3: `GESTURE_NONE_LINE = ""`;
  - f4: ưu tiên ô cảnh báo đổi thành đổi dấu > cảnh báo;
  - f5: lấy cảnh báo ĐẦU thay cho cuối;
  - f6: luôn thêm ô MP.

  Base ⇒ `OK`. Log `l13f_f1_mut_{f1..f6,base}.log`.

### AC-F2 (F2 — lớp mới cuối `tests/test_level1_display.py`; không cần dữ liệu)
Ký hiệu: cam 640×480 (thêm 640×360 ở G4).
1. G1: mọi cửa sổ không hợp lệ của `test_u1_invalid_windows` cho `fit_window_layout(640, 480, 200, *inv) == fit_layout(640, 480, 200)`.
2. G2 (tự nhiên là dọc): với `panel_h ∈ {150, 200, 283, 400}`, cửa sổ `(640, 480 + panel_h)` cho `== fit_layout(...)` và `side is False`.
3. G3 (luật chọn): lưới w, h ∈ range(200, 4001, 175), `panel_h ∈ {200, 283}`. Test tính `s_side` bằng công thức literal: `P = -(-w // 4)`,
   `min(h / 480, (w − P) / 640)`. Kỳ vọng `L.side == (s_side > fit_layout(...).scale + 1e-12)`. Nếu `not L.side` thì `L == fit_layout(640, 480, panel_h, w, h)`.
4. G4 (hình học cạnh nhau). Áp cho mọi ca `side` của G3, cộng cam 640×360 với `side_ref_h ∈ {None, 300, 451, 600}` ở các cửa sổ
   `(1920, 1080), (2400, 800), (3000, 700), (1024, 768)`. Kỳ vọng:
   - `cam_rect[0] == 0`; `cam_rect[1] == (h − ch) // 2`;
   - `panel_rect == (cw, 0, w − cw, h)`; `w − cw ≥ -(-w // 4)`;
   - `|L.scale − s_side| ≤ 1e-9`; `|cw/ch / (cam_w/cam_h) − 1| ≤ 0.01`;
   - `|ch − h| ≤ 1` hoặc `|cw − (w − P)| ≤ 1`;
   - `L.panel_scale == min(L.scale, (w − cw)/320, h/side_ref_h nếu có)` (±1e-9);
   - có ít nhất 1 ca mà vế `h/side_ref_h` là vế nhỏ nhất.
5. G5 (dải đen 16:9, ĐỊNH LƯỢNG). Cửa sổ ∈ {(1280,720), (1366,768), (1600,900), (1920,1080), (2560,1440), (3840,2160)}, `panel_h ∈ {200, 283, 400}`.
   - `side is True`;
   - `black = w·h − cw·ch − pw·ph` ≤ `0.005·w·h`;
   - riêng 1920×1080: `cam_rect == (0, 0, 1440, 1080)`, `panel_rect == (1440, 0, 480, 1080)`, `black == 0`.
   - Đối chứng hàm cũ không đổi: `fit_layout(640, 480, 200, 1920, 1080)` có `1 − cw·ch_total/(w·h) > 0.3`.
6. G6 (đọc được): ở các cửa sổ 16:9 của G5, `side_ref_h=355` ⇒ `L.panel_scale ≥ 1.0`.
7. G7 (render cạnh nhau, oracle chính xác). Cửa sổ ∈ {(1920,1080), (2560,1080), (1024,768), (1920,1200)}. Builder test ghi đối số và trả
   `np.full((h, w, 3), BG=(40,40,40))` cùng `step = scaled_px(18, ps)`. View ngẫu nhiên không có pixel 0. `hold ∈ {0.0, 0.5}`,
   `stats ∈ {[], ["fps 30.0 | hud 1.2ms"]}`. Kỳ vọng:
   - shape `(h, w, 3)`;
   - vùng camera == `cv2.resize(view, (cw, ch), interpolation=cv2.INTER_LINEAR)`;
   - builder được gọi đúng 1 lần với `(pw, ph, L.panel_scale, len(stats))`;
   - vùng panel == E. E = nền BG; thanh hold: hàng `[0, scaled_px(3, ps))`, cột `[0, int(pw·hold))` = `(0, 200, 0)`; dòng thống kê vẽ bằng
     `cv2.putText(E, line, (int(8·ps), ph − int(10·ps) − (n−1−i)·step), cv2.FONT_HERSHEY_SIMPLEX, 0.45·ps, (160,255,160), max(1, int(round(ps))), cv2.LINE_AA)`.
     Các số VIẾT LITERAL như T1, không import hằng;
   - mọi pixel ngoài `cam_rect ∪ panel_rect` == 0.
8. G8 (dọc không đổi): với 5 cửa sổ dọc (vd. (640,680), (1280,1360), (600,2000), (800,900), (700,1400)), `render_to_window` theo
   `fit_window_layout` `array_equal` `render_to_window` theo `fit_layout`. Các lớp cũ U1/U2/U3/E4-input/U7/T1 xanh, 0 dòng xóa.
9. G9 (không sửa đầu vào, nhánh cạnh nhau): `view_bgr` sau lời gọi `array_equal` bản chép trước, và `np.shares_memory(out, view_bgr)` False.
10. G10 `wrap_rows`. Dùng `measure = lambda s: 10·len(s)` và font nhỏ thật (`Hud._fonts_at(1.5)[1].getlength`). Kỳ vọng:
    - `len == budget`; mọi dòng ≤ `max_w`;
    - vừa thì `" ".join(r for r in rows if r).split() == text.split()`;
    - tràn thì dòng cuối `endswith("…")`;
    - rỗng ⇒ `[""]·budget`; một từ dài 50 ký tự với `max_w = 100` bị cắt theo ký tự;
    - `budget = 0` ⇒ `ValueError`; `max_w = 5` ⇒ `[""]·budget`.
- Lệnh:
  - `PY -m unittest tests.test_level1_display -v`: đỏ trước (`l13f_f2_red.log`), xanh sau (`l13f_f2_green.log`, ghi `Ran`);
  - `PY -m unittest tests.test_level1_equivalence -v` ⇒ `OK`, file đó không đổi;
  - `LALL > l13f_f2_green_level1_all.log` ⇒ `OK (skipped=1)`, DoD7 như trên.
- **AC-F2m** (worktree `wt_13f_f2`; sửa `level1_display.py`; chạy `tests.test_level1_display`). Mọi đột biến ⇒ `FAILED`:
  - d1: `fit_window_layout` luôn trả `below`;
  - d2: luôn chọn cạnh nhau khi hợp lệ;
  - d3: `panel_rect` cao `ch` thay cho `h`;
  - d4: camera căn giữa trong `avail`;
  - d5: builder nhận `layout.scale` thay cho `panel_scale`;
  - d6: overlay vẽ theo `layout.scale`;
  - d7: `P = w // 5`;
  - d8: bỏ vế `h/side_ref_h`;
  - d9: `wrap_rows` không thêm `…`;
  - d10: `wrap_rows` không đệm `""`.

  Base ⇒ `OK`. Log `l13f_f2_mut_{d1..d10,base}.log`.

### AC-F3 (F3 — lớp mới `TestSideLayoutApp13f` cuối `tests/test_level1_demo.py`, `skipUnless(not _MISSING)`; cộng E5)
View tổng hợp 480×640 bất đối xứng như W1b; `stats = ["fps 30.0 | hud 1.2ms"]`; `hold = 0.6`; `slots` lấy từ `_panel_lines()` ở state (a) và (h).
1. H1: rect `(0, 0, 1920, 1080)`, state (a). `ph = hud.panel_height(tb, slots, 1)`, `L = fit_window_layout(640, 480, ph, rect, side_ref_h=hud.side_panel_height(len(slots), 1))`.
   Kỳ vọng:
   - `L.side`, `out.shape == (1080, 1920, 3)`;
   - camera == `cv2.resize(view, (1440, 1080), INTER_LINEAR)`;
   - panel `out[0:1080, 1440:1920]` == E. E = `Hud(font)._build(480, tb, rows, 1, L.panel_scale, 1080)`, với `rows` ghép trong TEST từ
     `wrap_rows(slot_i, Hud(font)._fonts_at(ps)[1].getlength, 480 − 2·int(8·ps), 2 hoặc 3 cho ô cuối)`; sau đó
     `draw_panel_overlays(E, 0, 0.6, stats, hud.line_steps(ps)[1], ps)`. So `array_equal`;
   - `len(rows) == 2·(len(slots)−1) + 3`.
2. H1c: app 7 ô (cờ như AC-F1 mục 4), view 360×640, rect `(0, 0, 2400, 800)`. Như H1, và khẳng định vế `h/side_ref_h` là vế nhỏ nhất trong
   `L.panel_scale`. Mọi dòng của `rows` có đáy ≤ `ph − 1·small_step` (không đè hàng thống kê).
3. H2 (camera bất biến theo nội dung). Rect ∈ {ném `cv2.error`, `(0,0,640,480+ph)`, `(0,0,1920,1080)`, `(0,0,1280,1360)`, `(0,0,1000,700)`,
   `(0,0,2560,1080)`}. Với mỗi rect, so state (a) và (h) (hold 0.0 và 0.6):
   - cùng shape;
   - cùng `cam_rect` (bọc `render_to_window` để ghi `layout`; đường `compose` coi là `(0, 0, 640, 480)`);
   - vùng camera `array_equal`.
4. H3 (chạy app 1080p). Recorder `rect=(0, 0, 1920, 1080)`, clip D2 `--pace realtime`, bọc `render_to_window` ghi `layout`. Kỳ vọng:
   - mọi ảnh `(1080, 1920, 3)`;
   - số lần gọi `render_to_window` == `frames_processed`;
   - tập `layout.cam_rect` == `{(0, 0, 1440, 1080)}`; mọi `layout.side` True;
   - `len(rec.resized) == 1`.
5. H4 (sức chứa): với 5, 6, 7 ô và 2 dòng thống kê, `hud.side_panel_height(n, 2) ≤` chiều cao camera của clip D2. Chỉ là thông tin khẳng định;
   phần chặn tràn là vế `h/side_ref_h`.
6. E5: `test_w1b_window_image_scaled_layout` bản sửa xanh. Mọi test cũ còn lại xanh KHÔNG sửa, gồm:
   - `TestLatencyAcL`, `TestScaledWindowU2b`, `TestFullscreenU2c`;
   - W1a, F1, L1;
   - `TestEquivalenceE3Spy`, `TestEquivalenceE4Display`, AC-U6b;
   - `test_u2_hud_scale_one_identical_to_m0_hud`.
7. Bất biến mã:
   - `git diff B0..HEAD -- level1_demo.py`: không có dòng `-` nằm trong thân `Hud.compose`, `_build`, `panel_height`, `panel_builder`, `_fit_committed`,
     `_fonts_at`, `_hud_lines`, `_gesture_line`, `_gesture_engine_line`, `_decoder_line`, `_hand_line`, `_key` (reviewer đối chiếu);
   - `grep -cE '^[-+]WINDOW_NAME'` trên diff đó ⇒ `0`.
8. AC-U9 (base B0): `git diff B0..HEAD -- level1_demo.py src/ | grep -E '^\+' | grep -cE 'vars\(|__dict__|cv2\.dnn|getRectSubPix|__import__|importlib|warp|remap|pyr(Up|Down)'` ⇒ `0`.
   AC-U9b (base B0): `git diff B0..HEAD -- level1_demo.py | grep -E '^[-+]' | grep -cE 'process\(|frame_mp|draw_landmarks|display_view|HandLandmarkSession|\.read\('` ⇒ `0`.
   Câu "`git diff … -- src/` rỗng" của AC-U9 13b chỉ áp cho U2 và KHÔNG áp cho 13f, vì F2 được phép sửa `level1_display.py`.
- Lệnh:
  - lớp mới: đỏ trước `l13f_f3_red.log`, xanh sau `l13f_f3_green.log`;
  - `LALL > l13f_f3_green_level1_all.log` ⇒ `OK (skipped=1)`, DoD7 `known=9 allowed=36`;
  - `PY -m unittest tests.test_level1_equivalence -v` ⇒ `OK`.
- Numstat: `git diff --numstat B0..HEAD -- tests/`: cột xóa = 0 với mọi file, trừ `tests/test_level1_demo.py` ≤ 5 và chỉ ở `:3699-3703` của B0.
- **AC-F3m** (worktree `wt_13f_f3`; sửa `level1_demo.py`; chạy `tests.test_level1_demo.TestSideLayoutApp13f tests.test_level1_demo.TestWindowAndFullscreenU2t2`).
  Mọi đột biến ⇒ `FAILED`:
  - w1: `_window_image` dùng `fit_layout`;
  - w2: nhánh cạnh nhau dùng `hud.panel_builder`;
  - w3: ô cuối chỉ 2 dòng;
  - w4: `_window_image` không truyền `side_ref_h`;
  - w5: `max_w` của `side_rows` không trừ lề `PAD_X`.

  Base ⇒ `OK`. Log `l13f_f3_mut_{w1..w5,base}.log`.

### AC-F4 (F4 — cầu nối; tại commit F3, `git status --porcelain -- level1_demo.py src scripts` rỗng)
- (a) DC1, định nghĩa và ngưỡng giữ nguyên:
  - lần 1: `PY scripts/level1_display_cost.py --out reports/level1_realtime_2026-10-10/display_cost.json > _work/_plan15_l13/l13f_f4_run1.log 2>&1; echo $?`;
  - lần 2 và 3: `--out _work/_plan15_l13/l13f_f4_run{2,3}.json`, chạy nối tiếp, không có việc nặng song song.

  Yêu cầu:
  - cả 3 lần mã thoát 0 và `gate.pass true`;
  - `window_1080p.path_counts.render_to_window == window_1080p.n_imshow`;
  - MỚI (khóa ý 1 dưới harness): `natural.path_counts.render_to_window == 0` ở cả 3 lần;
  - JSON lần 1 có `code_dirty false`; `grep -ciE 'users[\\/]+'` ⇒ `0`;
  - progress ghi `ratio_p50`, `n_frames`, `path_counts`, `stage_p50_ms`, `info.hud_p50_delta_ms` của 3 lần;
  - CHỈ commit JSON lần 1. File cũ `reports/level1_realtime_2026-10-08/display_cost.json` giữ nguyên.

  Trượt bất kỳ yêu cầu nào ⇒ DỪNG, báo planner. Không chạy thêm để "lấy lần đẹp", không chỉnh `SIDE_PANEL_REF_W` hay luật ô.
- (b) W2, thăm dò cửa sổ THẬT. Script tạm `_work/_plan15_l13/w2_probe.py`, KHÔNG commit, cùng cách của W1 (`15-progress.md:1711-1715`): không vá
  `imshow/namedWindow/resizeWindow/waitKey`; chỉ bọc `getWindowImageRect`, `Hud.compose`, `render_to_window` (ghi `layout`) và `_window_image`.
  Hai lượt trên clip D2 `--pace realtime`: (i) cửa sổ mặc định; (ii) `--fullscreen`.

  Log phải có:
  - cỡ tự nhiên mỗi khung và tập giá trị; tập rect; `path_counts`;
  - tập `cam_rect` (đường compose thì `(0, 0, w, h)`);
  - `layout.side` của các khung có rect bằng rect cuối;
  - cỡ màn hình và `black = 1 − (cw·ch + pw·ph)/(W·H)` ở (ii);
  - tiêu đề thật (`GetWindowTextW`).

  Điều kiện đạt:
  - (i): tập cỡ tự nhiên có 1 phần tử và tập `cam_rect` có 1 phần tử;
  - (ii): trong các khung có rect bằng rect cuối, tập `cam_rect` có 1 phần tử và `side` True;
  - nếu màn hình 16:9 thì `black ≤ 0.005`, nếu không thì ghi số;
  - tiêu đề == `WINDOW_NAME`.

  Không đạt ⇒ DỪNG, báo planner. Máy không có màn hình hoặc phiên khóa ⇒ ghi "không chạy được", VU2 thay thế.

### AC-P (quy trình, mọi bước)
- Đúng 1 commit cho mỗi bước có mã, theo mẫu: `^15: L13f-F1 `, `^15: L13f-F2 `, `^15: L13f-F3 `, `^15: L13f-F4 báo cáo`, `^15: L13f-F4 W2`.
- File của mỗi commit ⊆ scope của bước đó (§5b).
- Có log impact và detect-changes; có log đỏ trước xanh.
- 0 `skip` mới.
- `sha256sum checkpoints/alphabet_best.pt` bắt đầu bằng `160e0c68`.
- `git diff --stat B0..HEAD -- backend/ configs/ src/data/ src/inference/level1_core.py src/inference/level1_segmenter.py src/inference/level1_gestures.py scripts/` rỗng.
  Ngoại lệ duy nhất: không có, vì F4 chỉ thêm `reports/…`.
- Không push.

## 5b. Phạm vi file

```scope
level1_demo.py
src/inference/level1_display.py
tests/test_level1_demo.py
tests/test_level1_display.py
reports/level1_realtime_2026-10-10/
docs/plans/15-progress.md
```

Phạm vi theo bước:
- F1: `level1_demo.py`, `tests/test_level1_demo.py`, progress.
- F2: `src/inference/level1_display.py`, `tests/test_level1_display.py`, progress.
- F3: `level1_demo.py`, `tests/test_level1_demo.py`, progress.
- F4: `reports/level1_realtime_2026-10-10/display_cost.json`, progress.

CẤM: `tests/test_level1_equivalence.py`, `scripts/level1_display_cost.py`, `docs/level1_desktop.md` (để R2), `README.md`, 3 file ` D`, `configs/`, `checkpoints/`.

Độ khó: M (F1 S–M, F2 M, F3 M, F4 S); vùng nhạy cảm: có (`level1_demo.py` vòng lặp chính cạnh đường khung vào landmark; `render_to_window` có ngoại lệ E4;
harness đánh giá DC1).

## 6. Rủi ro dữ liệu/ML

- Lệch train ↔ realtime: không đổi `frame`/`frame_mp`/`process`. Khóa bằng:
  - E3 tĩnh/E4 (file test không đổi);
  - E3 spy, AC-U6b ở chế độ cửa sổ 1920×1080 (nay là bố cục cạnh nhau: vẫn đúng 1 resize ảnh HIỂN THỊ);
  - AC-U9/U9b base B0.
- Kết quả nhận dạng/JSON: `_hud_lines` và mọi logic segmenter/decoder/speller không đổi. Panel chỉ hiện 1 cảnh báo, JSON vẫn đủ (Giới hạn R2).
- Số liệu: không có số kỳ vọng nào trong tài liệu này ngoài hình học tất định (rect, tỉ lệ đen). Chi phí hiển thị chỉ lấy từ JSON F4 có lệnh và commit.
  Panel tự nhiên cao hơn (thêm ô giữ chỗ) và panel cạnh nhau có chữ lớn hơn, nên chặng `hud` có thể tăng; DC1 (ngưỡng 1.25, đặt trước) quyết.
- Đo phụ thuộc tải máy (như 13c): dùng 3 lần đo, commit lần 1, quy tắc đặt trước.
- Hằng thiết kế (`SIDE_PANEL_REF_W = 320`, ⌈W/4⌉, hạn mức 2/3 dòng, ưu tiên cảnh báo) đặt TRƯỚC khi đo, không chỉnh theo DC1/W2/VU2. Muốn chỉnh
  thì phải có lần sửa mới của planner.
- Màn hình không 16:9 (4:3, 16:10) ở bố cục cạnh nhau còn dải đen trên/dưới ảnh camera; G5 chỉ hứa cho 16:9. Cửa sổ tự nhiên cao hơn trước
  (thêm ô giữ chỗ), nên màn hình cao 768 px có thể không chứa hết. Khi đó HĐH thu cửa sổ, app đi `render_to_window` dọc ở scale cố định
  (vẫn không co hoặc dịch theo nội dung).
- Không có dữ liệu mới, không đổi model hay checkpoint. Clip D2 chỉ đọc.

## 7. Điểm dừng

- **CẦN NGƯỜI DÙNG (không chặn F1–F4) — VU2**, sau F4. Người dùng chạy demo (`PY level1_demo.py`, preset, webcam) rồi trả lời:
  1. camera còn co hoặc dịch khi chữ dưới hay bên phải thay đổi không;
  2. phím f hoặc `--fullscreen`: camera trái, panel phải, còn dải đen không; chữ trong panel đọc được không;
  3. dòng cử chỉ luôn hiện, ghi `[Cử chỉ: none]` khi không ký;
  4. tiêu đề vẫn đọc được.

  Trả lời "không đạt" ⇒ planner lập lần sửa mới; không tự chỉnh hằng.
- Không đổi model mặc định; không đụng thay đổi chưa commit của người dùng; worktree tạm xóa được; không có hành động không hoàn tác; không push.
- DỪNG, báo planner (không tự nới):
  - test cũ nào ngoài E5 đỏ, hoặc cần sửa dòng có sẵn;
  - E3/E4 cần đổi, hoặc `level1_display.py` cần import ngoài tập E4 hoặc thêm `resize`;
  - cần sửa `Hud.compose`/`_build`/`_hud_lines`;
  - một đột biến F1m/F2m/F3m không đỏ;
  - test mới đỏ trên mã đã sửa mà phải đổi oracle;
  - AC-F4(a) hoặc (b) không đạt.

## 8. Giới hạn chuyển cho R2 (`docs/level1_desktop.md`; số lấy từ JSON F4, ghi đường khóa)

- THAY câu 2 của `13c` §8 bằng: "Panel có số ô cố định (5, thêm ô MP và ô khóa tay khi bật), nên ảnh camera không đổi cỡ hay vị trí theo nội dung.
  Ảnh chỉ đổi khi cửa sổ đổi cỡ, hoặc khi chuyển giữa bố cục dọc và bố cục cạnh nhau (chọn bố cục cho camera lớn hơn)."
- Thêm các câu:
  - "Panel hiện 1 dòng cảnh báo (ưu tiên góc tay > cảnh báo cuối > đổi dấu); JSON giữ đủ cảnh báo."
  - "Màn hình không 16:9 ở bố cục cạnh nhau còn dải đen trên/dưới ảnh camera; dòng thống kê (cv2) có thể bị cắt phải ở panel hẹp."
  - "Cửa sổ tự nhiên cao hơn trước vì có ô giữ chỗ."
- DC1: trích JSON `reports/level1_realtime_2026-10-10/display_cost.json` (F4), KHÔNG trích số của các JSON cũ như chi phí của bố cục mới.

## 9. Con trỏ cần chèn (orchestrator chèn; planner không sửa file khác)

`docs/plans/15-progress.md` (cuối file) và `docs/plans/15-lan-sua-13.md` (ngay dưới con trỏ 13e ở đầu file, và ngay dưới con trỏ 13e sau bảng §8):

`> LẦN SỬA 13f (2026-10-10): xem docs/plans/15-lan-sua-13f.md — giao diện theo VU: panel số ô cố định (camera không co/dịch), dòng cử chỉ luôn hiện "[Cử chỉ: none]", bố cục cạnh nhau (camera trái, panel phải) khi cửa sổ rộng/fullscreen 16:9 không dải đen; F1→F2→F3 (vslt-coder-claude) → F4 (cầu nối: DC1 đo lại + thăm dò cửa sổ thật W2) → VU2 người dùng; ngoại lệ test E5 (W1b, ≤ 5 dòng).`
