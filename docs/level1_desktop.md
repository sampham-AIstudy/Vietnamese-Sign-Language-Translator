# Cấp 1 (Đánh vần) — ứng dụng desktop realtime

Ứng dụng `level1_demo.py` đọc webcam (hoặc một file video), tách từng ký hiệu chữ cái / dấu thanh và ghép thành chữ tiếng Việt
trong khung text kiểu bộ gõ. Model là checkpoint Cấp 1 đang triển khai (`checkpoints/alphabet_best.pt`, không đổi trong kế hoạch 15).
Mọi số đo nằm trong các JSON và `reports/level1_realtime_2026-10-05/SUMMARY.md` (sinh tự động); tài liệu này không chép số.

## 1. Chạy demo (lệnh dùng cho buổi báo cáo)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier.json
```

- Windows: `.venv\Scripts\python level1_demo.py ...`; cloud/Linux: `.venv/bin/python level1_demo.py ...`.
- `--config configs/level1_demo_classifier.json` bật chế độ re-arm `classifier` (chữ liên tiếp không cần rút tay). Thiếu cờ này app chạy
  config mặc định `configs/level1_realtime.json` (chế độ `motion_pose`, phải nảy tay hoặc hạ tay giữa hai chữ). Báo cáo JSON của app ghi
  `rearm_mode`, `config.path` và `config.sha256` để biết đã chạy chế độ nào.
- Ghi lại phiên (tùy chọn): thêm `--expected "<từ>" --out-json reports/level1_realtime_<ngày>/webcam_<từ>_<lần>.json`. App chỉ ghi token,
  sự kiện, thời gian và thống kê; không ghi video, khung hình hay landmark.
- Chạy trên file video, không cửa sổ: `python level1_demo.py --source <video.mp4> --headless --out-json <file>.json`
  (`--pace realtime` để đọc theo nhịp của file và bỏ khung như webcam).
- Các cờ khác: `python level1_demo.py --help`.

## 2. Phím

| Phím | Tác dụng |
|---|---|
| `1` … `5` | Gõ dấu cho âm tiết đang gõ: `1` sắc, `2` huyền, `3` hỏi, `4` ngã, `5` nặng (đổi dấu ngay nếu đã có dấu) |
| `n` | Chữ kế: nhận lại ký hiệu đang giữ như một chữ mới (chữ lặp như "oo", "ee") |
| Backspace | Xóa token cuối (chữ hoặc dấu) |
| Space | Thêm dấu cách (kết thúc từ); hạ tay đủ lâu cũng thêm dấu cách |
| `r` | Lặp lại chữ cuối |
| `a` | Nhận ứng viên bị từ chối gần nhất (chữ mờ) |
| `c` | Xóa hết |
| `p` | Tạm dừng / chạy tiếp |
| `q` hoặc Esc | Thoát (ghi JSON nếu có `--out-json`) |

Token tạo bằng phím có `source: "key"` trong JSON — không tính là nhận dạng.

## 3. Khung text

Dòng chữ dưới ảnh camera: phần đã cố định (trước dấu cách cuối) và âm tiết đang gõ (tô sáng), con trỏ luôn ở cuối. Ứng viên có độ tin
cậy thấp hiện mờ bên phải con trỏ (nhấn `a` để nhận). Khi đổi dấu trong âm tiết đang gõ, khung ghi thông tin "đổi dấu". Khung text
không che vùng tay của ảnh camera.

## 4. Giới hạn (trung thực, cho báo cáo)

1. Model Cấp 1 train trên 4 người ký (bộ hauuto), một bộ dữ liệu, giấy phép chưa rõ — chỉ dùng nội bộ, không phát hành clip/landmark.
2. Số LOSO là đánh giá OFFLINE trên clip đã cắt sẵn; checkpoint triển khai = chạy nested `primary`, số lấy từ
   `reports/alphabet_nested_2026-09-25/primary/nested_report.json`. Số ở README thuộc lần chạy khác (real_run), không dùng cho checkpoint
   này. Dấu thanh yếu hơn chữ cái rất nhiều (theo lớp và theo người ký: `reports/level1_realtime_2026-10-03/tone_evidence.json`, bảng ở SUMMARY).
3. Độ chính xác trên webcam CHƯA được đánh giá. Phiên `--expected` (nếu có) là thử nghiệm vài từ, một người — không phải đánh giá.
4. Tham số tách ký hiệu: thiết kế + hiệu chỉnh trên clip TRAIN (quy tắc đặt trước); mọi phép kiểm trên clip train là kiểm logic, không
   phải độ chính xác. Chưa đo tracker liên tục qua nhiều ký hiệu.
5. Độ trễ đo trong app (từ lúc nhận khung tới lúc hiển thị) trên MỘT máy; không gồm trễ camera/màn hình; không thay số độ trễ WebSocket
   của web. Độ trễ chữ hiện ra gồm thời gian giữ yên / cửa sổ ổn định của chế độ đang chạy.
6. Phím (`1`–`5`, `n`, `a`, `r`, Backspace, Space) được ghi nguồn "key" trong JSON.
7. Dấu thanh: biến thể có quỹ đạo cổ tay đã thử cùng giao thức và không tốt hơn
   (`reports/alphabet_nested_2026-09-25/variants/nested_report.json`). Khi model nhận sai dấu, người trình bày gõ dấu bằng phím `1`–`5`.
8. **Kiểm A3 TRƯỢT (quyết định của người dùng: vẫn giữ config hiệu chỉnh).** So config trước hiệu chỉnh (3ebc7b9) với config hiệu chỉnh
   (b0620a9) trên mọi clip train: tỉ lệ đúng một segment tăng ở cả chữ cái và dấu thanh, nhưng tỉ lệ nhãn segment khớp nhãn trọn clip
   giảm ở cả hai nhóm ⇒ quy tắc giữ config đặt trước KHÔNG đạt; tiêu chí "đúng một segment" của kế hoạch (AC-R1) cũng không đạt. Config
   không bị đổi lại; số ở `reports/level1_realtime_2026-10-05/segment_check_before.json`, `segment_check_after.json` và mục 2 của SUMMARY.
   Phép kiểm này đo đường `motion_pose` (config mặc định), không đo chế độ demo.
9. Chế độ demo = `classifier` theo quyết định (a) của người dùng, KHÔNG phải gate đạt: gate G6 nhóm dấu thanh TRƯỢT (dấu thanh liên tiếp
   kém hơn chế độ cũ) ⇒ dấu thanh dùng phím `1`–`5`. Số ở `reports/level1_realtime_2026-10-05/rearm_check_d4.json` (mục 3 của SUMMARY);
   quyết định ghi trong `_user_decision` của `configs/level1_demo_classifier.json`.
10. Chữ liên tiếp được tách bằng dự đoán của model trên cửa sổ trượt ngắn; kiểm trên chuỗi ghép từ clip train — kiểm logic, không phải độ
    chính xác, không phải phiên webcam. Trên clip QIPEDC (ngoài train, một người ký, chỉ báo cáo) chế độ `classifier` phát nhãn trọn clip
    ít hơn chế độ cũ (G7 trong `rearm_check_d4.json`).
11. Chữ lặp (oo, ee) và chữ gốc ngay trước biến thể của nó (vd "aă" liền nhau) cần phím `n` hoặc rút tay giữa hai chữ.
12. Luật re-arm theo tư thế tay (lần sửa 3) đã đo và bác: hình tay không phân biệt chữ gốc / chữ có dấu phụ
    (`reports/level1_realtime_2026-10-05/pose_evidence.json`).
13. Tham số của bộ giải mã nhãn được chọn sau thăm dò trên chính chuỗi ghép dùng để kiểm (ghi trong `rearm_check_d4.json`); không chỉnh
    tiếp theo kết quả kiểm hay phiên webcam.

## 5. Nguồn số liệu

- `reports/level1_realtime_2026-10-05/SUMMARY.md` — bảng tổng hợp, sinh bằng
  `python scripts/level1_segment_report.py --summary --out reports/level1_realtime_2026-10-05/SUMMARY.md` (chạy lại ra đúng từng byte).
- `reports/level1_realtime_2026-10-03/tone_evidence.json` — dấu thanh out-of-fold, hồ sơ chuyển động clip train, quy tắc hiệu chỉnh.
- `reports/level1_realtime_2026-10-05/segment_check_before.json`, `segment_check_after.json` — kiểm A3.
- `reports/level1_realtime_2026-10-05/rearm_check_d4.json` — gate G1–G7 của chế độ `classifier`.
- `reports/level1_realtime_2026-10-05/pose_evidence.json` — luật tư thế (đã bác).
- Tiến độ và lệnh đã chạy: `docs/plans/15-progress.md`.
