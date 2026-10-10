# Lần sửa 13f-a — gỡ mâu thuẫn oracle G7/H1 và chốt 2 điểm trống của F2

Ngày: 2026-10-11. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc lập `f50c50b`. Sửa kế hoạch gốc `docs/plans/15-lan-sua-13f.md`
(§3.3 và AC-F2). Không cần người dùng: không đổi model mặc định, không cần dữ liệu, không có hành động không hoàn tác.

## 1. Mục tiêu
Cho coder F2 code được mà không phải tự đặt luật: (a) sửa oracle thanh hold của G7 cho khớp `draw_panel_overlays` đã có và đã bị khóa;
(b) chốt `panel_h`/`side_ref_h` cho G4 và G7; (c) chốt cách giữ nhánh dọc của `render_to_window`. Phục vụ cùng mục DoD như 13f (hiển thị Level 1).

## 2. Nguyên nhân gốc
- `draw_panel_overlays` (`src/inference/level1_display.py:122-137`) vẽ thanh hold bằng `cv2.rectangle(..., -1)`. Hàm này tô CẢ hai mép,
  nên thanh chiếm hàng `[top, top + scaled_px(3, s)]` và cột `[0, int(w·hold)]` (đóng hai đầu). Hàm chỉ vẽ khi `hold_progress > 0`.
- Hành vi này đã bị khóa: test U7 h2 (`+2`), `Hud.compose` (M0 `cad8cdc`), và AC-F3 H1 lấy oracle là chính `draw_panel_overlays`.
- AC-F2 G7 ghi thanh dạng nửa mở (`[0, scaled_px(3, ps))`, `[0, int(pw·hold))`). Đây là lỗi ghi của planner. Với `hold > 0`, G7 và H1
  không thể cùng đúng.
- Nếu đổi `draw_panel_overlays` sang nửa mở thì vỡ U7/`Hud.compose`, và trái §3.3 "bố cục dọc ảnh bằng hệt B0".

Đây là SỬA ORACLE cho khớp hành vi vẽ có sẵn, không phải nới tiêu chí:
- F2 chưa có dòng mã nào, chưa có log red/green, nên không sửa sau khi thấy kết quả;
- G7 vẫn so `array_equal` toàn vùng panel, theo từng pixel;
- đột biến d6 (overlay theo `layout.scale`) vẫn phải `FAILED`. Mục 3.2 thêm khẳng định chống rỗng để chắc điều này.

## 3. Thay đổi hợp đồng (ĐÈ lên `15-lan-sua-13f.md`; phần không nhắc ở đây giữ nguyên)

### 3.1 §3.3 `render_to_window`, bổ sung
- Nhánh `not layout.side` giữ NGUYÊN các phép tính của B0 (`level1_display.py:148-163`), gồm `panel_builder(width, panel_h, layout.scale, …)`
  và `draw_panel_overlays(content, cam_h, …, layout.scale)`. Chỉ được thụt lề hoặc bọc vào nhánh `if`, không đổi biểu thức nào.
  Bị khóa bởi G8 và U1/U2/U3/E4/U7/T1.
- Nhánh `layout.side` làm theo 4 bước:
  1. đặt camera vào `cam_rect`;
  2. lấy `panel_view = canvas[py:py+ph, px:px+pw]` theo `panel_rect`;
  3. `panel_view[:] = panel` (builder gọi với `ps = layout.panel_scale`);
  4. `draw_panel_overlays(panel_view, 0, hold, stats, step, ps)`.

  Như vậy nét vẽ bị cắt trong panel, không tràn sang camera. KHÔNG thêm hàm vẽ mới, KHÔNG sửa `draw_panel_overlays`.

### 3.2 AC-F2, thay thế
- G4: các ca thêm cho cam 640×360 dùng `panel_h ∈ {200, 283}` × `side_ref_h ∈ {None, 300, 451, 600}` × 4 cửa sổ đã liệt kê.
  - Kỳ vọng hình học chỉ áp cho ca có `L.side`. Ca không `side` phải `== fit_layout(640, 360, panel_h, w, h)`.
  - Thêm khẳng định chống rỗng: cam 640×360 có ít nhất 1 ca `side`.
- G7: `panel_h ∈ {200, 283}`, `side_ref_h=None`, view ngẫu nhiên 480×640 (không có pixel 0). Mỗi ca khẳng định trước `L.side is True`.
  Dòng thanh hold đổi thành:
  - vùng panel == E. E = nền BG; nếu `hold > 0` thì `cv2.rectangle(E, (0, 0), (int(pw·hold), scaled_px(3, ps)), (0, 200, 0), -1)`
    (tô cả hai mép, như `draw_panel_overlays` với `panel_top = 0`); `hold == 0.0` thì không vẽ gì.
  - Số viết literal; `scaled_px` được import (đã dùng ở bản gốc). Dòng thống kê giữ nguyên như bản gốc.
  - Thêm khẳng định chống rỗng: có ít nhất 1 cửa sổ G7 mà `L.panel_scale != L.scale` (để d5/d6 bắt được).
    Test tự kiểm, không ghi số kỳ vọng.

Lệnh, log, đột biến d1–d10, numstat và AC-F3 giữ nguyên như `15-lan-sua-13f.md`.

## 4. Phạm vi file (không đổi so với F2 gốc)
```scope
src/inference/level1_display.py
tests/test_level1_display.py
```
Độ khó: M; vùng nhạy cảm: có (`render_to_window`, hiển thị; không chạm landmark, tiền xử lý, split, đánh giá).

## 5. Rủi ro
- Không có rủi ro dữ liệu/ML: chỉ chạm hiển thị, không chạm đường khung → landmark.
- Rủi ro duy nhất là lệch dọc so với B0. G8 và các test cũ khóa rủi ro này (0 dòng xóa trong tests ngoài phạm vi đã cho).

## 6. Điểm dừng
Không có.

`> LẦN SỬA 13f-a (docs/plans/15-lan-sua-13f-a.md, 2026-10-11): G7 oracle thanh hold = cv2.rectangle cả mép (khớp draw_panel_overlays/H1/U7, khóa M0 cad8cdc), chỉ khi hold>0; G4/G7 panel_h ∈ {200,283}, G7 side_ref_h=None + chống rỗng; nhánh dọc render_to_window giữ nguyên B0. Đè lên AC-F2 và §3.3.`
