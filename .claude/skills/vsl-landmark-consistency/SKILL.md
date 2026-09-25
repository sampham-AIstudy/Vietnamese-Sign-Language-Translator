---
name: vsl-landmark-consistency
description: BẮT BUỘC khi trích landmark, train model mới, hoặc sửa backend/camera của dự án VSL — đảm bảo đầu vào lúc train và lúc quét webcam giống hệt nhau (cùng extractor, phiên bản MediaPipe, bù tỉ lệ khung hình, chuẩn hoá tay, nhãn lưu trong checkpoint). Lệch ở đây làm model trả sai nhãn dù test offline tốt.
---

# Train ↔ camera consistency (VSL)

Mục tiêu dự án: nhận **đúng nhãn** người dùng ký trước webcam. Mọi khác biệt giữa pipeline train và pipeline live là lỗi.

## Bất biến (kiểm tra trước khi train / đổi backend)
1. **Cùng extractor + phiên bản**: Cấp 2 = `src/data/landmark_extractor.CleanHolisticExtractor` (67 khớp: pose 0–24, LH 25–45, RH 46–66);
   Cấp 1 = `mediapipe.solutions.hands` (`max_num_hands=1, model_complexity=1`). **mediapipe 0.10.14** cả hai phía
   (cloud: env py3.11, xem skill `vsl-cloud-jobs`). Không trộn landmark từ phiên bản/extractor khác (VSL-GH đi qua
   `convert_137_to_67(mode="semantic")` — `direct` gán sai khớp).
2. **Tracker mới cho mỗi clip** khi trích offline (`static_image_mode=False` giữ trạng thái giữa các video nếu dùng lại instance).
3. **Bù tỉ lệ khung hình**: MediaPipe chia x theo width, y theo height → cùng bàn tay khác nhau giữa 16:9 (QIPEDC), 1:1 (VSL-GH),
   4:3 (webcam/hauuto). Cấp 2: `VSLPreprocessingPipeline(..., aspect_ratio=W/H)`; `VSLDataset(aspect_correct=True)` đọc `width/height`
   từ CSV. Cấp 1: `canonicalize_hand_sequence(..., aspect_ratio=W/H)`. Live: `RealtimePipeline` lấy W/H từ frame.
4. **Chuẩn hoá tay**: Cấp 1 lật tay theo nhãn handedness đa số (`canonicalize_hand_sequence`). Frontend gửi frame **không lật gương**
   (`-scale-x-100` chỉ để hiển thị) — giữ nguyên như vậy; MediaPipe gán tay phải là "Left" trên frame không lật, quy tắc đã tính.
5. **Checkpoint tự mô tả**: lưu `label_map`/`classes` + `preprocessing` (aspect_correct, target_len, extractor, mediapipe_version).
   `VSLPredictor` ưu tiên `label_map` trong checkpoint; `RealtimePipeline(aspect_correct=None)` theo `preprocessing.aspect_correct`.
   Checkpoint cũ không có `preprocessing` → chạy như cũ (không bù) — đừng bật bù cho model train không bù.
6. **Tiền xử lý dùng chung một hàm** cho train và live; không viết lại logic chuẩn hoá trong backend.

## Kiểm chứng tối thiểu khi đổi pipeline
- `python -m unittest tests.test_aspect_correction tests.test_split_guards tests.test_vsl_system tests.test_realtime`
- `python scripts/smoke_test_phase10.py` (latency lần đầu có thể > 50 ms do GPU nguội — chạy lại trước khi kết luận).
- Test tương đương: 1 clip đi qua backend phải ra cùng nhãn/độ tin như script đánh giá offline.
