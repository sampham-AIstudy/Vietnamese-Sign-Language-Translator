# Kế hoạch 15 lần sửa 13 — kiểm của cầu nối sau M0 + U1 (agy gemini-3.8-flash-high, hết giờ mã 13)

Nguồn: báo cáo cầu nối vslt-coder 2026-10-08 ~15:00; script tái hiện ở `_work/_bridge_verify/l13_u1/` (probe.py, probe2.py, probe3.py).
Commit: `5a32cff` (M0, chỉ 15-progress), `7ae0040` (WIP U1: src/inference/level1_display.py +514, tests/test_level1_display.py +234).
Test tại 7ae0040: display+demo+guard+guard chính Ran 189 OK, known=9 allowed=36. Phạm vi/guard sạch; tests/ chỉ thêm.

## M0 — lỗi ghi chép trong docs/plans/15-progress.md (5a32cff)
- Tên lớp sai: `tests.test_fingerspelling_api.TestFingerspellingApi` → thật `TestRealClipEquivalence`; `tests.test_hand_live_equivalence.TestLiveEquivalence` → thật `TestHandLiveEquivalence`.
- Câu "Khớp 100% với kỳ vọng" sai: lần đo agy (`_work/_plan15_l13/m0_ac1.log`, UTF-16) failures=5 (test_reset_segments_and_graphs đỏ 3/4 lần chạy) vs mốc cầu nối 9bec0ad failures=4 — phải ghi chênh lệch.
- Khối "Trạng thái → Xong:" bị thay hẳn, mất danh sách B0…A2b — khôi phục.

## U1 — lỗi code (chưa sửa)
1. CAO — app có thể sập: `fit_layout` làm tròn chiều cao camera và panel riêng ⇒ nội dung có thể cao hơn cửa sổ 1 px, `y0 = -1`. Ví dụ `fit_layout(640,480,96,394,333)` → y0=-1, content_h=334 ⇒ `render_to_window` ValueError broadcast (probe3.py); 179 ca (panel 40..400; camera 640×480, 1280×720, 320×240) (probe.py). AC-U1 chưa được bảo đảm.
2. TRUNG BÌNH — vi phạm AC-U2: panel dựng ở scale s cao khác ô layout (+2..+6 px ở scale 1.56–3.36, −3 px ở 0.93); `render_to_window` dán nguyên, không cắt/đệm, dòng thống kê đặt theo đáy panel thật ⇒ tràn dải đen (5120 px ≠ 0 ở 1280×1360; 2000 px ở 1000×3000); 1920×1080 cắt mất 3 px đáy (probe.py, probe2.py).
3. TRUNG BÌNH — test nới hợp đồng: AC-U3 dùng delta = 2*total_lines + 8 thay vì "±2 px mỗi dòng" (= 8 với 4 dòng).
4. TRUNG BÌNH — test yếu: AC-U2 chỉ xét dải đen trái/phải khi x0 > 0 (không trên/dưới); lưới AC-U1 không kiểm x0,y0 ≥ 0, x0+cw ≤ w, y0+ch ≤ h; ca "cửa sổ = kích thước tự nhiên" chỉ thử layout None (cầu nối tự kiểm 216 tổ hợp giống hệt Hud.compose — nên đưa vào test).
5. TRUNG BÌNH — thiết kế: `ScalableHud` CHÉP nguyên `Hud._build`, `_fit_committed`, `_view_cache_key`, hằng màu từ level1_demo.py ⇒ hai bản phải đồng bộ. Phải dùng chung một nguồn (tái cấu trúc để Hud nhận scale, hoặc ScalableHud gọi/kế thừa Hud) — không chép.
6. THẤP–TB — `render_to_window` đoán chữ ký `panel_builder` bằng `inspect.signature` theo tên tham số ("font", "px"), 4 cách gọi, nhận cả ndarray ⇒ gom về MỘT giao thức. Số gõ tay: font dự phòng 18; `layout=None` ⇒ `fit_layout(..., 200, None)`.
7. THẤP — `DisplayLayout.__eq__` bỏ win_w/win_h; fit_layout nhận tuple 4 phần tử (x,y,w,h) không có test; import thừa (Union, List, DisplayLayout, PanelBuilder).
8. Quy trình — không có log đỏ U1; chưa có mục U1 trong 15-progress; chưa ghi impact/detect-changes; chưa thêm level1_display.py vào PLAN15_FILES (E3 cho phép).
