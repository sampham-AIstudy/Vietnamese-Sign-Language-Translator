# 15 — LẦN SỬA 8: Tối ưu hóa phát hiện cử chỉ tay ngang & hỗ trợ thiếu sáng (Tầng 1 - Demo App)

Người lập: Antigravity (planner). Coder: Claude Cloud. Reviewer: Antigravity (kéo về, chạy kiểm thử trên Windows).
Kế hoạch bổ sung tiếp nối `15-lan-sua-7.md` trên nhánh `cloud/2026-10-04-level1-rearm`.

## 0. Vấn đề thực tế từ phản hồi người dùng & khảo sát phần cứng

1. **Tay để ngang (Edge-on / Lateral pose) không quét được:** Khi làm ký tự `â`, `ă` (dấu mũ) hoặc cử chỉ bàn tay để ngang, diện tích lòng bàn tay chiếu lên camera bị co hẹp tối đa, các khớp gốc ngón tay tự che khuất (*self-occlusion*). MediaPipe BlazePalm SSD không đạt ngưỡng tin cậy mặc định `0.5` $\to$ bỏ qua khung hình, không có landmark nào được sinh ra.
2. **Thiếu sáng (Low-light condition) gây mất dấu & motion blur:** Trong phòng ánh sáng yếu, webcam laptop SunplusIT tự động hạ tốc độ màn trập (shutter speed $\sim 50-60\text{ms}$) để bù sáng, khiến FPS tụt xuống mức **16.7 FPS**. Khi tay cử động nhanh, ảnh bị nhòe (motion blur) và nhiễu hạt sensor, làm độ tin cậy của BlazePalm tụt xuống mức 0.20–0.35 (dưới ngưỡng 0.5).
3. **Phần cứng camera:** Thử nghiệm trực tiếp cho thấy `camera_api: "msmf"` bị lỗi `0xC00D36C4 (MF_E_INVALIDSTREAMNUMBER / SourceReader async failure)` trên driver UVC của SunplusIT. Vì vậy **bắt buộc giữ `camera_api: "dshow"`**.

## 1. Ranh giới kỹ thuật & An toàn

- **KHÔNG train lại mô hình**, KHÔNG đổi checkpoint `checkpoints/alphabet_best.pt`.
- **KHÔNG sửa `LEVEL1_HANDS_KWARGS` mặc định** trong `src/inference/hand_live.py`: mặc định vẫn giữ nguyên `min_detection_confidence: 0.5` để bảo toàn 100% tính tương đương bit-for-bit của test hồi quy offline AC5 (`tests/test_hand_live_equivalence.py`) và test websocket AC4-a (`tests/test_hand_landmarks_ws.py`).
- **KHÔNG sửa `configs/level1_realtime.json`** và `configs/level1_demo_classifier.json`.
- Cải tiến tập trung vào:
  - Cho phép `HandLandmarkSession` nhận tham số ghi đè tùy chọn `min_detection_confidence: Optional[float] = None` (hoặc `**kwargs`).
  - Hỗ trợ cờ CLI `--min-detection-conf` (mặc định 0.5, cho phép đặt 0.3 - 0.35) trong `level1_demo.py`.
  - Hỗ trợ cơ chế tự động cân bằng sáng thích ứng (`enhance_low_light`) bằng CLAHE trên kênh sáng L khi độ rọi trung bình khung hình $< 80$, kích hoạt qua cờ `--auto-enhance`.
  - Cập nhật HUD hiển thị trạng thái `[MP: conf=0.35 | CLAHE: on]` khi có tùy biến.
- Cột xóa trong `tests/` = 0.

## 2. Các thay đổi cụ thể cho Coder (Vòng 3 - Lần sửa 8)

Mỗi mục một commit riêng `15: <mã> ...`, viết test TRƯỚC (RED $\to$ GREEN), kiểm tra impact trước khi sửa.

### M1 — Cho phép `HandLandmarkSession` tùy biến `min_detection_confidence`
- File: `src/inference/hand_live.py`
  - `HandLandmarkSession.__init__(self, **kwargs)`: Cho phép nhận các tham số ghi đè `LEVEL1_HANDS_KWARGS`.
  - Lưu cấu hình hiệu lực vào `self.kwargs`. Khi gọi `reset()`, truyền `self.kwargs` vào `mp.solutions.hands.Hands(**self.kwargs)`.
  - Nếu không truyền tham số nào, dùng đúng 100% `LEVEL1_HANDS_KWARGS` hiện tại.
- File test: `tests/test_hand_live_equivalence.py` hoặc `tests/test_level1_demo.py`:
  - Viết test: `HandLandmarkSession()` mặc định dùng `min_detection_confidence = 0.5`.
  - `HandLandmarkSession(min_detection_confidence=0.35)` khởi tạo đúng MediaPipe Hands với 0.35.
  - Test AC5 và AC4-a vẫn chạy xanh nguyên vẹn.

### M2 — Bổ sung tiền xử lý thích ứng CLAHE cho khung hình thiếu sáng
- File: `src/inference/level1_core.py` (hoặc module tiện ích phù hợp):
  - Hàm `enhance_low_light(frame_bgr: np.ndarray, threshold: float = 80.0, clip_limit: float = 2.0) -> Tuple[np.ndarray, bool]`:
    - Tính độ sáng trung bình kênh xám: `np.mean(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY))`.
    - Nếu `< threshold`: chuyển sang không gian màu LAB, áp dụng CLAHE lên kênh L (`clipLimit=clip_limit`, `tileGridSize=(8, 8)`), ghép lại và chuyển về BGR. Trả về `(enhanced_frame, True)`.
    - Nếu $\ge threshold$: trả về `(frame_bgr, False)`.
- File test: `tests/test_level1_core.py`:
  - Khung hình tối (toàn 30) $\to$ được nâng độ tương phản, cờ `enhanced=True`.
  - Khung hình sáng (toàn 150) $\to$ giữ nguyên không đổi (`enhanced=False`).

### M3 — Tích hợp cờ CLI trong `level1_demo.py` & HUD
- File: `level1_demo.py`:
  - Thêm cờ `--min-detection-conf`: `type=float, default=0.5, help="MediaPipe min_detection_confidence (default 0.5; try 0.35 for edge-on hands)"`.
  - Thêm cờ `--auto-enhance`: `action="store_true", default=False, help="Enable adaptive CLAHE enhancement for low-light frames before hand detection"`.
  - Khởi tạo session: truyền `min_detection_confidence=args.min_detection_conf` vào `session_factory` (ví dụ: `lambda: HandLandmarkSession(min_detection_confidence=self.args.min_detection_conf)`).
  - Trong luồng xử lý `_process()`: nếu bật `--auto-enhance`, chạy `enhance_low_light(frame)` trước khi đưa vào `session.process()`. Khung hình vẽ lên màn hình (display) giữ nguyên ảnh thật của camera.
  - Dòng HUD hiển thị thông tin nếu khác mặc định: `[MP: conf=0.35 | CLAHE: on]`.
  - Đảm bảo `camera_api` trong config vẫn là `"dshow"`.
- Cập nhật tài liệu `docs/level1_desktop.md` với lệnh chạy mẫu mới:
  ```powershell
  python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance
  ```

## 3. Phạm vi file (Scope)

```scope
src/inference/hand_live.py
src/inference/level1_core.py
level1_demo.py
docs/level1_desktop.md
docs/plans/15-lan-sua-8.md
docs/plans/15-progress.md
tests/test_level1_demo.py
tests/test_level1_core.py
```

CẤM ĐỤNG:
- `configs/level1_realtime.json`
- `configs/level1_demo_classifier.json`
- `src/data/alphabet_preprocessing.py`
- `backend/main.py`
- `realtime_demo.py`
- Checkpoint `checkpoints/alphabet_best.pt`

## 4. Tiêu chí chấp nhận (Acceptance Criteria)

- **AC-8a**: Cột xóa trong `tests/` = 0.
- **AC-8b**: Chạy không cờ (`--min-detection-conf 0.5` mặc định): Giữ nguyên 100% hành vi cũ, 294 tests Level 1 + AC1-ngắn + Guard `known=9 allowed=36` đều xanh.
- **AC-8c**: Bật `--min-detection-conf 0.35`: MediaPipe Hands được khởi tạo với `min_detection_confidence = 0.35`.
- **AC-8d**: Bật `--auto-enhance`: Khung hình có độ rọi thấp được tăng cường CLAHE trước khi trích xuất landmark.
- **AC-8e**: Giữ `camera_api: "dshow"` hoạt động ổn định trên webcam laptop, không gây crash hoặc lỗi stream.

## 5. Reviewer Checklist

1. Fetch commit mới và kiểm tra `git diff`, đảm bảo không đụng các file cấm.
2. Chạy hồi quy 12 module Level 1 (294 test), Guard và AC1-ngắn trên Windows.
3. Người dùng test thực tế trên webcam:
   ```powershell
   python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance
   ```
   Kiểm tra cử chỉ tay để ngang (dấu mũ `â`, `ă`) và độ nhạy trong môi trường thiếu sáng.
