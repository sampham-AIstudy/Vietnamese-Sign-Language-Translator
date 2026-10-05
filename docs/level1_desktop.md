# Cấp 1 (Đánh vần) — ứng dụng desktop realtime

Ứng dụng `level1_demo.py` đọc webcam (hoặc một file video), tách từng ký hiệu chữ cái / dấu thanh và ghép thành chữ tiếng Việt
trong khung text kiểu bộ gõ. Model là checkpoint Cấp 1 đang triển khai (`checkpoints/alphabet_best.pt`, không đổi trong kế hoạch 15).
Mọi số đo nằm trong các JSON và `reports/level1_realtime_2026-10-05/SUMMARY.md` (sinh tự động); tài liệu này không chép số.

## 1. Chạy demo (lệnh dùng cho buổi báo cáo)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json
```

- Windows: `.venv\Scripts\python level1_demo.py ...`; cloud/Linux: `.venv/bin/python level1_demo.py ...`.
- `--config configs/level1_demo_classifier_rev7.json` bật chế độ re-arm `classifier` (chữ liên tiếp không cần rút tay) với các giá trị
  của lần sửa 7 (mục 7). Config demo trước đó, `--config configs/level1_demo_classifier.json` (lần sửa 5, cùng chế độ, chưa có giá trị lần
  sửa 7), vẫn chạy được. Thiếu `--config` app chạy config mặc định `configs/level1_realtime.json` (chế độ `motion_pose`, phải nảy tay hoặc
  hạ tay giữa hai chữ). Báo cáo JSON của app ghi `rearm_mode`, `config.path` và `config.sha256` để biết đã chạy chế độ nào.
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
| Space | Thêm dấu cách (kết thúc từ); hạ tay đủ lâu cũng thêm dấu cách (tắt phần tự động bằng `--no-auto-space`, mục 7) |
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

## 6. Chẩn đoán đổi ký hiệu liên tiếp (kế hoạch 15 lần sửa 6)

- HUD ở chế độ `classifier`: dòng `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<cls_stable_ms> | cuối: <last>` thay dòng "Trạng thái".
  `cửa sổ` = nhãn top-1 và độ tin cậy của cửa sổ trượt mới nhất (kể cả khi dưới `cls_conf`); `giữ` = nhãn đó đã đứng liền bao lâu so với
  `cls_stable_ms` (về 0 khi cửa sổ dưới `cls_conf` hoặc đổi nhãn); `cuối` = nhãn đã phát gần nhất (nhãn trùng nó không được phát lại cho tới
  khi rút tay hoặc nhấn `n`). Chế độ `classifier` không có thanh tiến độ của bộ tách. Chế độ `motion_pose` giữ nguyên HUD cũ.
- Ghi trace (mặc định tắt): thêm `--trace-windows` ⇒ JSON có khóa `window_trace` (mỗi cửa sổ: `ts_ms, status, top1, conf, top2, conf2,
  run_label, run_ms, last, emitted`; tối đa 20000 mục, quá thì `truncated: true`). Không có landmark hay khung hình.
- Phiên U3 (§4 của lần sửa 6, không rút tay giữa các ký hiệu, mỗi ký hiệu giữ khoảng 2 s):
  `python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier.json --trace-windows --out-json _work/u3_tones.json`
- Đọc trace: `python scripts/level1_trace_report.py --trace _work/u3_tones.json --expected "dấu nặng,dấu hỏi,dấu ngã,dấu sắc,dấu huyền"`
  in bảng theo đoạn chuyển ký hiệu và tỉ lệ thời gian M1 (dưới ngưỡng tin cậy), M2 (vẫn đoán ký hiệu cũ), M3 (nhãn chập chờn), M4 (xác suất
  chia giữa hai ký hiệu của cặp); chạy `motion_pose` ⇒ M0. Định nghĩa đầy đủ ở đầu file script. Ký hiệu cũ giữ lâu hơn `--hold-ms`
  (mặc định theo giao thức U3) được tính là M2.

## 7. Tinh chỉnh chế độ `classifier` (kế hoạch 15 lần sửa 7)

- `--cls-window-ms <N>`: độ dài cửa sổ trượt (mili giây) cho lần chạy này, thay `cls_window_ms` của config — để thử vài độ dài khác nhau
  mà không sửa file. Chỉ dùng với config `rearm_mode` = `classifier` (config `motion_pose` ⇒ app dừng và báo lỗi). File config không đổi;
  JSON ghi giá trị đã thay ở `config.overrides` (không có cờ ⇒ không có khóa này).
- `--no-auto-space`: hạ tay lâu hơn `word_gap_ms` không tự thêm dấu cách; khoảng nghỉ vẫn được phát hiện và đếm (sự kiện `word_gap` có
  `auto_space: false`, gốc JSON có `auto_space: false`). Dấu cách chỉ đến từ phím Space.
- Khóa TÙY CHỌN của config (thiếu khóa ⇒ hành vi như trước lần sửa 7; không khóa nào ⇒ bộ giải mã bằng hệt bộ giải mã đã đo ở D4):
  - `cls_conf_tone`, `cls_stable_ms_tone`: ngưỡng tin cậy và thời gian ổn định riêng cho 5 dấu thanh; chữ cái vẫn dùng `cls_conf`,
    `cls_stable_ms`. Thiếu một khóa ⇒ dấu thanh dùng giá trị của chữ cái cho khóa đó.
  - `dropout_tolerance_ms`: một cửa sổ đơn lẻ rớt dưới ngưỡng (hoặc không hợp lệ) giữa một chuỗi không làm chuỗi bắt đầu lại nếu cửa sổ
    kế tiếp có kết quả quay lại đúng nhãn đó trong khoảng thời gian này tính từ cửa sổ rớt; ngược lại chuỗi bắt đầu lại tại cửa sổ rớt như
    cũ. Thiếu khóa ⇒ tắt.
  Mỗi khóa viết như các khóa khác: `{"value": …, "source": "design", "reason": "…"}`.
- HUD: khi chuỗi đang giữ là một dấu thanh, dòng `[classifier]` hiện thời gian ổn định của dấu thanh kèm `(tone)`:
  `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<cls_stable_ms_tone> (tone) | cuối: <last>` (chuỗi chữ cái hoặc không có chuỗi ⇒ dòng như
  mục 6).
- **Giá trị của lần sửa 7 nằm trong file config demo mới `configs/level1_demo_classifier_rev7.json`** (quyết định của người dùng
  "File config mới"): file này = `configs/level1_demo_classifier.json` với `cls_window_ms`, `word_gap_ms` đổi và `cls_conf_tone`,
  `cls_stable_ms_tone`, `dropout_tolerance_ms` thêm theo §2 của kế hoạch, sinh bằng
  `python scripts/level1_rearm_check.py --write-rev7-config configs/level1_demo_classifier_rev7.json` (`_about` ghi sha256 và commit của
  file gốc, `_rev7_decision` ghi quyết định; không sửa tay; chạy lại ra đúng từng byte). File demo của lần sửa 5 (test AC-W3 ghim nó bằng
  config mặc định + `rearm_mode`) và config mặc định không đổi. Các giá trị do planner chọn sau phiên U3 (trace không commit): không phải
  hiệu chỉnh độc lập, không phải gate. Lệnh ở mục 1 dùng file này; thử giá trị khác: `--cls-window-ms`, hoặc chép file ra `_work/`, sửa
  khóa, chạy `--config _work/<file>.json` (không commit file đó).
- `scripts/level1_trace_report.py` vẫn so `conf` với `cls_conf` cho mọi nhãn (chưa biết ngưỡng riêng của dấu thanh và debounce) ⇒ phân
  loại M1/M3 của dấu thanh trên trace chạy với các khóa mới chỉ gần đúng.
