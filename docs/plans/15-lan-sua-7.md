# 15 — LẦN SỬA 7: Tối ưu hóa chuyển ký hiệu liên tục (multi-turn), độ nhạy dấu thanh và cơ chế tự động cách

Người lập: Antigravity (planner). Coder: Claude Cloud. Reviewer: Antigravity (kéo về, chạy kiểm thử trên Windows).
Kế hoạch bổ sung tiếp nối `15-lan-sua-6.md` trên nhánh `cloud/2026-10-04-level1-rearm`.

## 0. Vấn đề thực tế từ phiên chạy U3 (webcam)

Từ phản hồi người dùng (5/10 17:25) và số liệu đo thực tế từ `_work/u3_letters.json`:
1. **Dấu thanh nhận chậm (15–17 giây)**: Cửa sổ trượt mang tính cử chỉ động (có chuyển động nét vẽ trong không gian), độ tin cậy thực tế dao động 0.75–0.88 (chỉ 7% cửa sổ đạt >= 0.90). Ngưỡng ép cứng `cls_conf = 0.90` khiến 100 cửa sổ dấu huyền liên tiếp bị từ chối dù mô hình đã đoán đúng.
2. **Đổi cử chỉ tay không quét ngay (multi-turn bị lì)**: Cửa sổ trượt `cls_window_ms = 1000 ms` lưu vết ký hiệu cũ quá lâu. Khi đổi sang ký hiệu mới, phải giữ yên ký hiệu mới > 1.0s để đẩy ký hiệu cũ ra khỏi cửa sổ, cộng thêm 300 ms giữ yên, và bất kỳ 1 khung hình rớt conf nào cũng reset bộ đếm về 0.
3. **Cơ chế tự Space (`word_gap`) gây phiền**: `word_gap_ms = 1000 ms` quá ngắn. Chỉ cần hạ tay hoặc mất dấu tay 1 giây là hệ thống tự động chèn `' '` làm đứt đoạn từ đang gõ dở.

## 1. Ranh giới kỹ thuật

- KHÔNG train lại mô hình, KHÔNG đổi checkpoint `checkpoints/alphabet_best.pt`.
- KHÔNG sửa cấu hình mặc định `configs/level1_realtime.json` (chế độ motion_pose gốc giữ nguyên).
- Cải tiến tập trung vào: bộ giải mã `Level1LabelDecoder` (hỗ trợ tham số chuyên biệt), `WindowBuffer` / `level1_demo.py` và cấu hình demo `configs/level1_demo_classifier.json`.
- KHÔNG xóa/sửa test cũ (chỉ thêm test mới, cột xóa trong `tests/` luôn = 0).

## 2. Các thay đổi cụ thể cho Coder (Vòng 2)

Mỗi mục một commit riêng `15: <mã> ...`, viết test TRƯỚC, kiểm tra impact trước khi sửa.

### T1 — Ngưỡng riêng cho dấu thanh trong `Level1LabelDecoder`
- Trong `src/inference/level1_segmenter.py`:
  - `Level1LabelDecoder` hỗ trợ thêm 2 tham số tùy chọn:
    - `cls_conf_tone`: ngưỡng tin cậy cho 5 dấu thanh (`dấu sắc`, `dấu huyền`, `dấu hỏi`, `dấu ngã`, `dấu nặng`). Mặc định bằng `cls_conf` nếu không cung cấp.
    - `cls_stable_ms_tone`: thời gian ổn định yêu cầu cho dấu thanh. Mặc định bằng `cls_stable_ms` nếu không cung cấp.
  - Khi phân loại cửa sổ: nếu nhãn là dấu thanh, dùng `cls_conf_tone` và `cls_stable_ms_tone`. Chữ cái tĩnh (29 chữ) dùng `cls_conf` và `cls_stable_ms`.
- Trong `configs/level1_demo_classifier.json`:
  - Đặt `cls_conf_tone = 0.78` (phân vị an toàn theo đo U3 thực tế).
  - Đặt `cls_stable_ms_tone = 200.0` (ms).
- Viết test kiểm chứng: Dấu thanh đạt 0.80 được phát bình thường; chữ cái tĩnh 0.80 bị từ chối; tính tương thích ngược khi không truyền 2 khóa này.

### T2 — Giảm độ trễ cửa sổ trượt khi chuyển cử chỉ (multi-turn)
- Trong `src/inference/level1_segmenter.py` (`Level1LabelDecoder`):
  - Bổ sung **Debounce dung sai dropout 1 khung hình** (`dropout_tolerance_ms = 60 ms`): Nếu một nhãn đang tích lũy thời gian ổn định mà gặp 1 khung hình đơn lẻ bị rớt conf hoặc None do nhiễu MediaPipe, không reset ngay `_run_since` nếu khung hình kế tiếp ngay sau đó quay lại đúng nhãn đó.
- Trong `configs/level1_demo_classifier.json`:
  - Điều chỉnh `cls_window_ms = 700.0` (ms) thay vì 1000.0 ms. Giúp đẩy cử chỉ cũ ra khỏi buffer nhanh hơn ~30%, giảm độ trễ phản hồi khi đổi tay từ ~1.8s xuống dưới 1.0s.
- Hỗ trợ CLI cờ `--cls-window-ms` trong `level1_demo.py` để người dùng có thể linh hoạt thử nghiệm các độ dài cửa sổ khác nhau (ví dụ: 600, 700, 800).

### T3 — Tinh chỉnh cơ chế tự động Space (`word_gap`)
- Trong `configs/level1_demo_classifier.json`:
  - Nâng `word_gap_ms = 2500.0` (ms) thay vì 1000.0 ms. Chỉ tự cách khi người dùng hạ tay nghỉ rõ ràng ít nhất 2.5 giây.
- Trong `level1_demo.py`:
  - Bổ sung cờ CLI `--no-auto-space`: Khi bật cờ này, demo không kích hoạt `speller.word_gap` từ sự kiện nhận diện, để người dùng hoàn toàn chủ động bấm phím `Space` thủ công trên bàn phím.

### T4 — Cập nhật HUD & tài liệu
- HUD dòng `[classifier]`:
  - Hiển thị rõ ngưỡng đang áp dụng: nếu đang giữ dấu thanh, hiển thị `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<stable_tone> (tone) | cuối: <last>`.
  - Cập nhật hướng dẫn phím và cờ mới trong `docs/level1_desktop.md`.

## 3. Phạm vi file (Scope)

```scope
src/inference/level1_segmenter.py
src/inference/level1_core.py
configs/level1_demo_classifier.json
level1_demo.py
tests/test_level1_decoder.py
tests/test_level1_demo.py
tests/test_level1_core.py
docs/level1_desktop.md
docs/plans/15-progress.md
```

KHÔNG đụng: `configs/level1_realtime.json`, `src/data/alphabet_preprocessing.py`, `backend/main.py`, `realtime_demo.py`, checkpoint `alphabet_best.pt`.

## 4. Tiêu chí chấp nhận (Acceptance Criteria)

- **AC-7a**: `git diff 4f913a2..HEAD --numstat -- tests/` cột xóa = 0.
- **AC-7b**: Dấu thanh với conf 0.80 phát thành công trong 200 ms; chữ cái với conf 0.80 bị từ chối; chữ cái conf 0.92 phát sau 300 ms.
- **AC-7c**: Bật `--no-auto-space`: dù mất tay > word_gap_ms, không có ký tự space nào tự sinh vào text.
- **AC-7d**: Khi không truyền các khóa mới trong config, decoder giữ nguyên 100% hành vi cũ của D4 (backward compatibility).
- **AC-7e**: Toàn bộ 12 module Level 1 + guard (`known=9 allowed=36`) + AC1-ngắn đều xanh (Ran 250+ OK, 0 fail, 0 error).

## 5. Reviewer Checklist

1. Fetch nhánh và kiểm tra git diff, không có file cấm bị sửa.
2. Chạy lại toàn bộ test Level 1 + guard + AC1-ngắn trên Windows.
3. Người dùng chạy lại webcam với cấu hình mới: kiểm tra độ nhạy dấu thanh, chuyển thế tay mượt mà và kiểm tra phím Space / auto-space.
