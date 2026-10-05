# 15 — LẦN SỬA 10: Khóa tay thuận (`--dominant-hand`) chống lật gương và làm mượt khung xương đối diện camera

Người lập: Antigravity (planner). Coder: Claude Cloud. Reviewer: Antigravity (kéo về, chạy kiểm thử trên Windows).
Kế hoạch bổ sung tiếp nối `15-lan-sua-9.md` trên nhánh `cloud/2026-10-04-level1-rearm`.

## 0. Vấn đề thực tế từ phản hồi người dùng & phân tích dữ liệu

1. **Hiện tượng lật gương nhãn tay làm nhảy loạn ký tự (`p`, `â`, `ă`, `ô`, `ê`):**
   - Khi bàn tay hoặc ngón tay chĩa thẳng đối diện vào camera, MediaPipe không nhìn rõ mặt trước (lòng bàn tay) hay mặt sau (mu bàn tay), dẫn đến bộ phân loại handedness bị phân vân, đảo nhãn liên tục giữa `Left` và `Right` qua từng khung hình (lỗi lật nhãn).
   - Kiểm tra toàn bộ 636 clip của tập `hauuto`: **75% các clip bị lật nhãn tay tập trung đúng vào các ký tự `â`, `ă`, `ô`, `ê`, `p`** (trong đó `p` có độ rung lệch chuẩn trục $z$ lên tới $z_{std} = 1.054$, cao nhất toàn bộ dataset).
   - Trong hàm tiền xử lý `canonicalize_hand_sequence` (`src/data/alphabet_preprocessing.py`), khi nhãn tay là `"Left"`, tọa độ $x$ bị lật ngược $x \to -x$. Khi nhãn bị đảo liên tục 30 lần/giây, bàn tay bị lật gương trái $\leftrightarrow$ phải liên tục $\to$ chuỗi đặc trưng nạp vào mạng BiGRU bị giật gương liên tục $\to$ kết quả dự đoán nhảy loạn xạ ("nhảy lung tung").
2. **Dao động trục sâu $z$ do monocular depth ambiguity:**
   - Camera 2D thông thường không có cảm biến chiều sâu. Khi ngón tay chĩa thẳng vào ống kính, các khớp MCP, PIP, DIP, TIP nằm trên cùng một tia nhìn (*collinear*), khoảng cách 2D co về gần 0, khiến ước lượng $z$ bị nhiễu hạt sensor làm rung giật.

## 1. Ranh giới kỹ thuật & An toàn

- **KHÔNG train lại mô hình**, KHÔNG đổi checkpoint `checkpoints/alphabet_best.pt`.
- **KHÔNG sửa logic tiền xử lý gốc của `canonicalize_hand_sequence`**: Chỉ điều khiển nhãn tay và làm mượt landmark ở tầng ứng dụng `level1_demo.py` và `level1_core.py`.
- **Bảo toàn 100% test AC5 và AC4-a**: Khi không truyền cờ mới, hành vi mặc định hoàn toàn không đổi.
- Cột xóa trong `tests/` = 0.

## 2. Các thay đổi cụ thể cho Coder (Vòng 5 - Lần sửa 10)

Mỗi mục một commit riêng `15: <mã> ...`, viết test TRƯỚC (RED $\to$ GREEN), kiểm tra impact trước khi sửa.

### P1 — Cờ `--dominant-hand` khóa nhãn tay ký (Chống lật gương)
- File: `level1_demo.py`:
  - Thêm tham số CLI `--dominant-hand`:
    - `choices=["Right", "Left", "auto"], default="auto"`
    - `help="Signer dominant hand: 'Right' or 'Left' fixes handedness and eliminates Left/Right mirror-flipping jitter; 'auto' keeps MediaPipe per-frame classification (default: auto)"`.
  - Trong luồng xử lý `_process()`:
    - Nếu `args.dominant_hand` là `"Right"` (hoặc `"Left"`): nhãn `handedness` truyền vào `self.segmenter.push()` và `self._window_frame()` (nạp vào `self.window.push()`) được gán cố định là nhãn được chọn, bất kể MediaPipe trả về nhãn gì.
    - Nếu `args.dominant_hand` là `"auto"`: giữ nguyên nhãn gốc của MediaPipe (hành vi mặc định).
  - Khối JSON báo cáo: ghi `dominant_hand: {"mode": args.dominant_hand}` khi khác `"auto"`.
  - Dòng HUD hiển thị nhỏ: `[Tay: Phải]` hoặc `[Hand: Right]` khi được khóa cố định.
- File test: `tests/test_level1_demo.py`:
  - Viết test `TestDominantHand`:
    - Clip có nhãn MediaPipe nhảy giữa Left và Right: khi bật `--dominant-hand Right`, tất cả các khung hình trong `window` và `segmenter` đều nhận nhãn `"Right"` cố định.
    - Không cờ (mặc định): giữ nguyên nhãn gốc của clip.

### P2 — Bộ lọc làm mượt tọa độ Landmark thích ứng (Adaptive Landmark Smoother)
- File: `src/inference/level1_core.py`:
  - Lớp `LandmarkSmoother`:
    - `__init__(self, alpha_static: float = 0.6, alpha_dynamic: float = 0.9, speed_threshold: float = 0.15)`:
      - Sử dụng bộ lọc Exponential Moving Average (EMA) thích ứng theo vận tốc chuyển động:
        - Khi tay di chuyển chậm / giữ yên (`speed < speed_threshold`): dùng `alpha_static` (làm mượt mạnh, đặc biệt triệt tiêu dao động trục $z$).
        - Khi tay di chuyển nhanh (`speed >= speed_threshold`): dùng `alpha_dynamic` (gần bằng 1.0, bám sát cử chỉ tức thời, không bị trễ).
    - `filter(self, ts_ms: float, landmarks: Optional[np.ndarray]) -> Optional[np.ndarray]`:
      - Nếu `landmarks is None`: reset trạng thái lọc, trả về `None`.
      - Ngược lại: làm mượt từng khớp trong 21 điểm (đặc biệt tọa độ $z$), trả về mảng `float32[21, 3]` đã được làm mượt.
    - `reset(self)`: xóa bộ đệm.
- File test: `tests/test_level1_core.py`:
  - Viết test `TestLandmarkSmoother`:
    - Chuỗi landmark tĩnh có cộng nhiễu Gaussian ở trục $z$: sau khi qua bộ lọc, phương sai dao động trục $z$ giảm ít nhất 50%, tọa độ trung bình được bảo toàn.
    - Bước nhảy lớn (chuyển động đột ngột): bộ lọc bám theo nhanh chóng, không bị kẹt.
- File: `level1_demo.py`:
  - Khởi tạo `self.landmark_smoother = LandmarkSmoother()` trong `Level1App`.
  - Thêm cờ CLI `--smooth-landmarks`: `action=argparse.BooleanOptionalAction, default=True, help="Enable adaptive landmark smoothing to suppress depth jitter (default: enabled)"`.
  - Trong `_process()`: nếu bật làm mượt và có landmarks, cho landmarks đi qua `self.landmark_smoother.filter(ts_ms, landmarks)` trước khi đưa vào segmenter, window và vẽ đồ họa.

### P3 — Gợi ý góc nghiêng trên HUD khi ngón tay bị che khuất collinear ($fs < 0.3$)
- File: `src/inference/level1_core.py`:
  - Hàm `foreshortening_ratio(landmarks: np.ndarray) -> float`:
    - Tính tỉ lệ giữa độ dài 2D hình chiếu của ngón trỏ `dist_2d(tip 8, mcp 5)` chia cho độ dài 3D `dist_3d(tip 8, mcp 5)`.
    - Trả về giá trị trong khoảng $[0.0, 1.0]$.
- File: `level1_demo.py`:
  - Trong `_hud_lines()`: Nếu phát hiện bàn tay có $fs < 0.3$ trong hơn 3 khung hình liên tiếp (dấu hiệu đang chĩa đâm thẳng vào mắt camera), hiển thị dòng nhắc nhở nhỏ màu vàng: `[Góc tay: Hơi nghiêng tay 20°]`.
- File: `docs/level1_desktop.md`:
  - Cập nhật mục 10: Giải thích về hiện tượng collinear projection và hướng dẫn người dùng kết hợp `--dominant-hand Right --min-detection-conf 0.35 --auto-enhance` để có độ ổn định tối đa.

## 3. Phạm vi file (Scope)

```scope
src/inference/level1_core.py
level1_demo.py
docs/level1_desktop.md
docs/plans/15-lan-sua-10.md
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

- **AC-10a**: Cột xóa trong `tests/` = 0.
- **AC-10b**: Khi bật `--dominant-hand Right`, tất cả khung hình trong window/segmenter đều nhận nhãn `"Right"`, loại bỏ 100% hiện tượng lật ngược tọa độ $x \to -x$.
- **AC-10c**: Bộ lọc `LandmarkSmoother` triệt tiêu rung lắc trục $z$ khi tay giữ yên mà không gây trễ khi tay di chuyển.
- **AC-10d**: Khi chạy với các tham số mặc định (không truyền cờ mới): Giữ nguyên 100% hành vi cũ, 354+ tests Level 1 + AC1-ngắn + Guard `known=9 allowed=36` đều xanh.

## 5. Reviewer Checklist

1. Fetch commit mới từ remote và kiểm tra `git diff`.
2. Chạy toàn bộ test trên Windows.
3. Thử nghiệm trên webcam với lệnh tổng hợp:
   ```powershell
   python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --dominant-hand Right
   ```
   Kiểm tra ký tự `p`, `â`, `ă`: xác nhận không còn hiện tượng nhảy lung tung hay lật gương.
