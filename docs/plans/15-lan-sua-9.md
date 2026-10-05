# 15 — LẦN SỬA 9: Cử chỉ tay xòe 5 ngón cho phím cách (Gesture-based Space)

Người lập: Antigravity (planner). Coder: Claude Cloud. Reviewer: Antigravity (kéo về, chạy kiểm thử trên Windows).
Kế hoạch bổ sung tiếp nối `15-lan-sua-8.md` trên nhánh `cloud/2026-10-04-level1-rearm`.

## 0. Vấn đề thực tế từ trải nghiệm người dùng (UX)

Khi thực hiện đánh vần liên tục trước webcam:
1. **Tự động cách (`word_gap_ms`):** Người dùng bị động — phải chờ 2.5 giây khi hạ tay để tự cách từ; nếu dừng tay suy nghĩ thì dễ vô tình bị chèn dấu cách.
2. **Gõ phím `Space` vật lý:** Người dùng phải hạ tay xuống bàn phím để bấm, làm đứt mạch cử chỉ và tốn thời gian đưa tay định vị lại trước camera.
3. **Giải pháp:** Cung cấp cử chỉ tay chuyên biệt cho dấu cách: **Xòe cả 5 ngón tay hướng về phía camera (Open Palm / "High Five")** trong thời gian ngắn (~250–300 ms). Khi người dùng muốn ngắt từ, chỉ cần xòe bàn tay mở rộng 5 ngón một nhịp ngắn $\to$ hệ thống tự động phát sinh một dấu cách (`' '`) ngay lập tức mà không cần chạm vào bàn phím hay chờ đợi auto-space.

## 1. Ranh giới kỹ thuật & An toàn

- **KHÔNG train lại mô hình**, KHÔNG đổi checkpoint `checkpoints/alphabet_best.pt`.
- Nhận diện cử chỉ hoàn toàn bằng **hình học 21 landmark MediaPipe** ($O(1)$ CPU, cực nhanh, không phụ thuộc mạng nơ-ron).
- **Phân biệt tuyệt đối với chữ cái VSL:**
  - Chữ `b`: 4 ngón duỗi nhưng ngón cái gập ngang vào lòng bàn tay $\to$ ngón cái không mở.
  - Chữ `a`, `s`: Nắm đấm $\to$ 4 ngón không duỗi.
  - Chữ `c`, `o`: Các ngón cong hình cung.
  - Chữ `d`, `h`, `v`, `k`: Chỉ có 1 hoặc 2 ngón duỗi.
  - $\to$ Chỉ duy nhất cử chỉ xòe mở cả 5 ngón mới kích hoạt dấu cách.
- **Chống lặp liên thanh (Anti-repeating debounce):** Sau khi phát sinh 1 dấu cách, cử chỉ Space rơi vào trạng thái *disarmed*; người dùng phải thu tay hoặc chuyển sang cử chỉ khác trước khi có thể phát tiếp dấu cách thứ hai.
- Cột xóa trong `tests/` = 0.

## 2. Các thay đổi cụ thể cho Coder (Vòng 4 - Lần sửa 9)

Mỗi mục một commit riêng `15: <mã> ...`, viết test TRƯỚC (RED $\to$ GREEN), kiểm tra impact trước khi sửa.

### S1 — Hàm kiểm tra hình học `is_open_palm_space`
- File: `src/inference/level1_core.py`:
  - Hàm `is_open_palm_space(landmarks: np.ndarray) -> bool`:
    - Đầu vào: `landmarks` dạng `float32[21, 3]` (tọa độ gốc hoặc chuẩn hóa). Trả về `False` nếu `landmarks is None` hoặc không đủ 21 điểm.
    - **Tiêu chí 1: 4 ngón dài (trỏ, giữa, áp út, út) đều duỗi thẳng:**
      - Ngón trỏ: `dist(tip 8, wrist 0) > dist(pip 6, wrist 0)` và `dist(tip 8, mcp 5) > dist(pip 6, mcp 5)`.
      - Ngón giữa: `dist(tip 12, wrist 0) > dist(pip 10, wrist 0)` và `dist(tip 12, mcp 9) > dist(pip 10, mcp 9)`.
      - Ngón áp út: `dist(tip 16, wrist 0) > dist(pip 14, wrist 0)` và `dist(tip 16, mcp 13) > dist(pip 14, mcp 13)`.
      - Ngón út: `dist(tip 20, wrist 0) > dist(pip 18, wrist 0)` và `dist(tip 20, mcp 17) > dist(pip 18, mcp 17)`.
    - **Tiêu chí 2: Ngón cái mở rộng ra ngoài (Thumb Abduction - khác với chữ `b`):**
      - `dist(thumb_tip 4, pinky_mcp 17) > dist(middle_mcp 9, wrist 0) * 1.1` (hoặc góc dang ngón cái đủ lớn so với bàn tay).
      - Ngón cái duỗi: `dist(thumb_tip 4, wrist 0) > dist(thumb_ip 3, wrist 0)`.
    - **Tiêu chí 3: Độ mở giữa các ngón (Finger Separation):**
      - Khoảng cách giữa các đầu ngón tay lân cận (`dist(8, 12)`, `dist(12, 16)`, `dist(16, 20)`) không quá nhỏ (tránh 4 ngón khép sát như chữ `b`).
    - Nếu thỏa mãn cả 3 tiêu chí: trả về `True`; ngược lại `False`.
- File test: `tests/test_level1_core.py`:
  - Viết test `TestOpenPalmSpace`:
    - Mẫu xòe 5 ngón $\to$ `True`.
    - Mẫu chữ `b` (ngón cái gập qua lòng bàn tay) $\to$ `False`.
    - Mẫu chữ `a` (nắm đấm) $\to$ `False`.
    - Mẫu chữ `d` (chỉ ngón trỏ) $\to$ `False`.

### S2 — Bộ đếm thời gian & Kích hoạt dấu cách trong `level1_demo.py`
- File: `level1_demo.py`:
  - Lớp `SpaceGestureTracker`:
    - `__init__(self, hold_ms: float = 250.0)`: Khởi tạo với thời gian giữ yêu cầu (mặc định 250 ms).
    - `update(self, ts_ms: float, is_space: bool) -> bool`:
      - Nếu `is_space` là `True`:
        - Nếu đang armed: tích lũy thời gian giữ `run_since = run_since or ts_ms`.
        - Nếu `ts_ms - run_since >= hold_ms`: emit event Space (`True`), chuyển trạng thái sang disarmed (`armed = False`).
      - Nếu `is_space` là `False`:
        - Reset `run_since = None`.
        - Nếu cử chỉ khác duy trì $> 150\text{ms}$ hoặc mất tay: rearm lại (`armed = True`).
      - Trả về `True` đúng 1 lần khi emit Space; các khung tiếp theo khi vẫn giữ tay xòe trả về `False`.
  - Tích hợp vào `Level1App._process()`:
    - Trong mỗi khung hình có landmark: kiểm tra `is_open_palm_space(landmarks)`.
    - Đưa vào `self.space_tracker.update(ts_ms, is_space)`.
    - Nếu trả về `True`: gọi trực tiếp `self.speller.key("space", t_ms=ts_ms)` và ghi log `_log("gesture_space", t_ms=ts_ms)`.
    - Khi nhận diện cử chỉ space, có thể tạm thời bỏ qua nạp khung hình đó vào bộ đệm nhận diện chữ cái `window.push` để tránh làm nhiễu classifier.
  - Phản hồi trên HUD:
    - Khi đang giữ xòe 5 ngón: hiển thị tiến độ `[Cử chỉ: Dấu cách <giữ ms>/250]`.
    - Khi emit thành công: HUD nhấp nháy `[Ký hiệu: Dấu cách (Space)]`.
- File test: `tests/test_level1_demo.py`:
  - Viết test `TestSpaceGestureTracker`:
    - Giữ xòe 200 ms (< 250 ms) $\to$ không emit.
    - Giữ xòe 260 ms $\to$ emit đúng 1 lần.
    - Giữ tiếp xòe đến 1000 ms $\to$ KHÔNG emit lần thứ hai (không lặp liên thanh).
    - Đổi sang tư thế khác rồi xòe lại $\to$ emit lần thứ hai thành công.

### S3 — Cờ CLI và Cập nhật Tài liệu
- File: `level1_demo.py`:
  - Thêm cờ `--gesture-space`: `action=argparse.BooleanOptionalAction, default=True, help="Enable 5-finger open palm gesture for Space (default: enabled)"`.
  - Thêm cờ `--space-hold-ms`: `type=float, default=250.0, help="Required hold time in ms for open palm space gesture (default: 250)"`.
  - Ghi cấu hình `gesture_space` vào JSON run report khi kết thúc phiên.
- File: `docs/level1_desktop.md`:
  - Cập nhật mục phím tắt & cử chỉ: Thêm hướng dẫn cử chỉ **Xòe 5 ngón tay** để tạo phím cách tự nhiên.
  - Bổ sung lệnh demo gợi ý kết hợp `--no-auto-space` và cử chỉ space chủ động:
    ```powershell
    python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --no-auto-space
    ```

## 3. Phạm vi file (Scope)

```scope
src/inference/level1_core.py
level1_demo.py
docs/level1_desktop.md
docs/plans/15-lan-sua-9.md
docs/plans/15-progress.md
tests/test_level1_core.py
tests/test_level1_demo.py
```

CẤM ĐỤNG:
- `configs/level1_realtime.json`
- `configs/level1_demo_classifier.json`
- `src/data/alphabet_preprocessing.py`
- `backend/main.py`
- `realtime_demo.py`
- Checkpoint `checkpoints/alphabet_best.pt`

## 4. Tiêu chí chấp nhận (Acceptance Criteria)

- **AC-9a**: Cột xóa trong `tests/` = 0.
- **AC-9b**: Hàm `is_open_palm_space` nhận diện chính xác tư thế xòe 5 ngón, không nhận nhầm chữ `b`, `a`, `c`, `d`, `h`.
- **AC-9c**: Giữ xòe 5 ngón liên tục 250 ms kích hoạt đúng 1 ký tự `' '` vào speller; giữ tiếp không bị lặp liên thanh.
- **AC-9d**: Khi tắt cờ `--no-gesture-space`, hành vi hoàn toàn như cũ không bị ảnh hưởng.
- **AC-9e**: Toàn bộ 12 module Level 1 (322+ test), Guard `known=9 allowed=36` và AC1-ngắn đều xanh.

## 5. Reviewer Checklist

1. Fetch commit mới từ remote và kiểm tra `git diff`.
2. Chạy toàn bộ test trên Windows (bao gồm các test mới cho `is_open_palm_space` và `SpaceGestureTracker`).
3. Thử nghiệm trực tiếp trên webcam:
   - Đánh vần một từ (ví dụ "tôi").
   - Xòe 5 ngón tay trước camera trong ~0.3s $\to$ kiểm tra màn hình đã thêm khoảng trắng chưa.
   - Tiếp tục đánh vần từ tiếp theo mà không cần chạm bàn phím.
