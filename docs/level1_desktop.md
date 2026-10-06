# Cấp 1 (Đánh vần) — ứng dụng desktop realtime

Ứng dụng `level1_demo.py` đọc webcam (hoặc một file video), tách từng ký hiệu chữ cái / dấu thanh và ghép thành chữ tiếng Việt
trong khung text kiểu bộ gõ. Model là checkpoint Cấp 1 đang triển khai (`checkpoints/alphabet_best.pt`, không đổi trong kế hoạch 15).
Mọi số đo nằm trong các JSON và `reports/level1_realtime_2026-10-05/SUMMARY.md` (sinh tự động); tài liệu này không chép số.

## 1. Chạy demo (lệnh dùng cho buổi báo cáo)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev9.json --min-detection-conf 0.35 --auto-enhance --dominant-hand lock
```

- Lệnh trên (kế hoạch 15 lần sửa 12, mục 11): đánh vần nhiều chữ liên tiếp không cần hạ tay, chữ chỉ được nhận khi tay đã đứng yên
  (cổng chuyển động `cls_motion_gate`), nhãn tay khóa theo đa số nhãn của chính MediaPipe, không tự chèn dấu cách (dấu cách bằng phím
  Space). KHÔNG dùng `--dominant-hand Right` như lần sửa 10: cờ đó từng ép nhãn `Left` và lật gương bàn tay (nay là bí danh của `lock`).
- Lệnh của lần sửa 7: `python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json`.

- Windows: `.venv\Scripts\python level1_demo.py ...`; cloud/Linux: `.venv/bin/python level1_demo.py ...`.
- `--config configs/level1_demo_classifier_rev7.json` bật chế độ re-arm `classifier` (chữ liên tiếp không cần rút tay) với các giá trị
  của lần sửa 7 (mục 7). Config demo trước đó, `--config configs/level1_demo_classifier.json` (lần sửa 5, cùng chế độ, chưa có giá trị lần
  sửa 7), vẫn chạy được. Thiếu `--config` app chạy config mặc định `configs/level1_realtime.json` (chế độ `motion_pose`, phải nảy tay hoặc
  hạ tay giữa hai chữ). Báo cáo JSON của app ghi `rearm_mode`, `config.path` và `config.sha256` để biết đã chạy chế độ nào.
- Ghi lại phiên (tùy chọn): thêm `--expected "<từ>" --out-json reports/level1_realtime_<ngày>/webcam_<từ>_<lần>.json`. App chỉ ghi token,
  sự kiện, thời gian và thống kê; không ghi video, khung hình hay landmark.
- Chạy trên file video, không cửa sổ: `python level1_demo.py --source <video.mp4> --headless --out-json <file>.json`
  (`--pace realtime` để đọc theo nhịp của file và bỏ khung như webcam).
- Tay để ngang (`â`, `ă`) hoặc phòng thiếu sáng: thêm `--min-detection-conf 0.35 --auto-enhance` (mục 8).
- Dấu cách tự động (hạ tay đủ lâu: `--auto-space`; cử chỉ Xòe 5 ngón: `--gesture-space`, mục 9) TẮT mặc định từ lần sửa 12 (mục 11);
  `--no-auto-space` vẫn nhận (là mặc định), ví dụ:
  `python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --no-auto-space`
- Các cờ khác: `python level1_demo.py --help`.

## 2. Phím

| Phím | Tác dụng |
|---|---|
| `1` … `5` | Gõ dấu cho âm tiết đang gõ: `1` sắc, `2` huyền, `3` hỏi, `4` ngã, `5` nặng (đổi dấu ngay nếu đã có dấu) |
| `n` | Chữ kế: nhận lại ký hiệu đang giữ như một chữ mới (chữ lặp như "oo", "ee") |
| Backspace | Xóa token cuối (chữ hoặc dấu) |
| Space | Thêm dấu cách (kết thúc từ); hạ tay đủ lâu chỉ thêm dấu cách khi chạy với `--auto-space` (mặc định tắt, mục 11) |
| Cử chỉ Xòe 5 ngón | Chỉ với `--gesture-space` (mặc định tắt): giữ bàn tay xòe cả 5 ngón trước camera trong `--space-hold-ms` (mục 9) |
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

## 8. Tay để ngang và thiếu sáng (kế hoạch 15 lần sửa 8, Tầng 1 — chỉ app demo)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance
```

- `--min-detection-conf <x>`: ngưỡng `min_detection_confidence` của MediaPipe Hands cho lần chạy này (số trong (0, 1]; mặc định 0.5 =
  giá trị lúc trích landmark train và của đường WebSocket). Ngưỡng thấp hơn để MediaPipe nhận bàn tay để ngang hoặc ảnh nhòe mà ở 0.5 bị
  bỏ qua; đổi lại dễ bắt nhầm vật khác thành tay hơn. Cả phiên MediaPipe khởi động (warm-up) lẫn phiên chạy luồng dùng giá trị này.
  `LEVEL1_HANDS_KWARGS` trong `src/inference/hand_live.py` không đổi (test AC5, AC4-a vẫn so bit-for-bit với 0.5).
- `--auto-enhance`: khung có độ sáng trung bình (ảnh xám) dưới `LOW_LIGHT_THRESHOLD` (80, `src/inference/level1_core.py`) được tăng tương
  phản cục bộ bằng CLAHE trên kênh L của LAB (`clipLimit` 2.0, lưới 8 x 8) TRƯỚC khi vào MediaPipe; khung đủ sáng vào MediaPipe nguyên vẹn
  (không chép). Cửa sổ vẫn hiện ảnh thật của camera: landmark vẽ lên khung gốc. Thời gian CLAHE đo riêng ở stage `low_light_enhance`
  (không cộng vào `mediapipe`).
- HUD (chỉ khi khác mặc định): một dòng ngay dưới dòng trạng thái / `[classifier]`, ví dụ `[MP: conf=0.35 | CLAHE: on]` (`CLAHE: off`
  khi không có `--auto-enhance`).
- JSON (chỉ khi khác mặc định): gốc JSON có `hand_detection` = `min_detection_confidence`, `auto_enhance` và, với `--auto-enhance`,
  `frames_enhanced` (số khung đã tăng sáng), `low_light_threshold`, `clahe_clip_limit`, `clahe_tile_grid`. Không cờ (hoặc
  `--min-detection-conf 0.5`) ⇒ JSON, HUD và mọi khung đưa vào MediaPipe như lần sửa 7.
- Camera: mọi config giữ `camera_api` = `dshow` (webcam SunplusIT của laptop lỗi khi đọc với `msmf`); kích thước khung và buffer lấy từ
  config như trước.
- Giới hạn: hai cờ chỉ là ngưỡng / tiền xử lý của app demo — KHÔNG train lại, checkpoint không đổi. Model Cấp 1 học từ landmark trích ở
  ngưỡng 0.5 trên ảnh không tăng sáng, nên khung CLAHE và landmark ở ngưỡng thấp có thể lệch phân phối train. Tác dụng lên tỉ lệ thấy tay
  và độ chính xác CHƯA được đo: cần phiên webcam của người dùng (checklist §5 của kế hoạch); mục này không chép số đo nào.

## 9. Cử chỉ Xòe 5 ngón = dấu cách (kế hoạch 15 lần sửa 9)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --no-auto-space
```

- Cách làm: kết thúc một từ bằng cách xòe cả bàn tay về phía camera — 4 ngón dài duỗi thẳng và tách nhau, ngón cái dang ra ngoài (khác
  chữ `b`: 4 ngón khép, ngón cái gập ngang lòng bàn tay) — rồi giữ yên trong `--space-hold-ms` (mặc định 250). App thêm đúng một dấu
  cách (như phím Space: không thêm khi text rỗng hoặc ký tự cuối đã là dấu cách). Giữ tiếp không thêm dấu cách thứ hai; muốn cách tiếp thì
  đổi sang tư thế khác (giữ hơn 150 mili giây) hoặc rút tay khỏi khung hình rồi xòe lại.
- Nhận diện bằng hình học 21 landmark của MediaPipe, không qua model (`is_open_palm_space` trong `src/inference/level1_core.py`):
  4 ngón dài duỗi (đầu ngón xa cổ tay và xa MCP hơn khớp PIP), ngón cái dang (khoảng đầu ngón cái tới MCP ngón út lớn hơn
  `THUMB_SPREAD_RATIO` = 1.1 lần khoảng cổ tay tới MCP ngón giữa) và duỗi, các đầu ngón kề nhau cách xa hơn `FINGER_SPREAD_MIN` = 1.2 lần
  khoảng MCP tương ứng. Landmark được nhân x, z với rộng / cao khung (như bộ tách) trước khi so khoảng cách.
- Chế độ `classifier` (config demo): khung xòe tay được đưa vào cửa sổ phân loại như khung không có tay, nên không bao giờ thành một chữ;
  dấu cách đi qua cùng hàng đợi thời gian với nhãn và word gap (đứng sau chữ của các khung trước nó). Chế độ `motion_pose` (config mặc
  định): bộ tách vẫn nhận khung xòe như cũ, nên bàn tay xòe giữ yên đủ lâu vẫn có thể bị tách thành một ký hiệu chữ.
- HUD: khi đang giữ xòe tay hiện `[Cử chỉ: Dấu cách <đã giữ>/<cần giữ>]` ngay dưới dòng trạng thái / `[classifier]` (dưới dòng `[MP: ...]`
  nếu có); ngay sau khi thêm dấu cách hiện `[Ký hiệu: Dấu cách (Space)]` trong `GESTURE_SPACE_FLASH` của `level1_demo.py` (thời gian của
  luồng khung). Không có cử chỉ ⇒ HUD như lần sửa 8.
- JSON: mỗi lần cử chỉ kích hoạt có sự kiện `{"event": "gesture_space", "t_ms", "added"}` (`added` = text có đổi), dấu cách tương ứng
  ghi như phím Space (`source: "key"`, `key: "space"`) cùng `t_ms`. Khóa gốc `gesture_space` = `enabled`, `hold_ms`, `rearm_ms`,
  `flash_ms`, `palm_frames` (số khung xòe tay), `emits` (số lần cử chỉ kích hoạt), `spaces_added` — chỉ có khi đã thấy ít nhất một khung xòe
  tay hoặc `--space-hold-ms` khác mặc định; lần chạy không có khung xòe tay với mặc định giữ đúng các khóa như lần sửa 8.
- Bật / tắt: `--gesture-space` (mặc định) / `--no-gesture-space` ⇒ app như lần sửa 8 (không kiểm hình tay, JSON và HUD như cũ). Thời
  gian kiểm hình tay tính trong stage `segmenter`.
- Giới hạn: giá trị giữ / re-arm là giá trị thiết kế của kế hoạch, ngưỡng 1.1 của kế hoạch, ngưỡng tách ngón 1.2 do coder đặt — chưa chỉnh
  theo phiên webcam. Trên clip train (chỉ kiểm logic) bàn tay xòe thật ở đầu một số clip của người ký `khoi` được nhận; chữ giữ yên không
  kích hoạt. Tỉ lệ nhận / bỏ sót trên webcam CHƯA được đo: cần phiên webcam của người dùng (checklist §5 của kế hoạch); mục này không chép
  số đo nào.

## 10. Ngón tay chĩa vào camera: khóa tay thuận, làm mượt landmark và nhắc góc tay (kế hoạch 15 lần sửa 10)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --dominant-hand Right
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev7.json --min-detection-conf 0.35 --auto-enhance --smooth-landmarks
```

- Hiện tượng (collinear projection): webcam thường chỉ cho ảnh 2D, không có cảm biến độ sâu. Khi ngón tay chĩa thẳng vào ống kính, các
  khớp MCP, PIP, DIP, TIP nằm gần trên cùng một tia nhìn: khoảng cách 2D giữa chúng co về gần 0, MediaPipe phải đoán độ sâu `z` từ rất ít
  thông tin nên `z` rung theo nhiễu ảnh và bàn tay dễ bị đọc sai (hay gặp ở `â`, `ă`, `ô`, `ê`, `p` — ngón cái và đầu ngón hướng về camera).
- (ĐÃ THAY bằng mục 11 — lần sửa 12: `Right` / `Left` nay là bí danh của `--dominant-hand lock`; JSON và HUD như mục 11. Đoạn dưới
  giữ lại để đọc lịch sử.) `--dominant-hand Right | Left | auto` (mặc định `auto`): khi ngón tay chĩa vào camera, MediaPipe không phân biệt được lòng bàn tay
  với mu bàn tay nên nhãn tay trái / phải của nó đổi qua lại giữa các khung. `canonicalize_hand_sequence` lật gương x khi đa số khung trong
  một segment / cửa sổ mang nhãn `Left`, nên nhãn đổi qua lại làm cửa sổ lúc lật lúc không. Với `Right` (người ký thuận tay phải) hoặc
  `Left`, mọi khung có tay nhận MỘT nhãn cố định, bất kể MediaPipe trả về gì. Nhãn đó là nhãn MediaPipe gán cho bàn tay ấy trên khung KHÔNG
  lật gương (app không bao giờ lật khung khi xử lý; `--display-mirror` chỉ lật hình hiển thị): MediaPipe giả định ảnh đã lật như camera
  selfie, nên tay phải mang nhãn `Left` (giống clip train của người ký thuận tay phải: x được lật) và tay trái mang nhãn `Right`. Người
  thuận tay trái dùng `--dominant-hand Left`. HUD có dòng `[Tay: Phải]` / `[Tay: Trái]`; JSON có khóa gốc
  `dominant_hand` = `{"mode": "Right", "label": "Left"}` (hoặc `Left` / `Right`). `auto` ⇒ nhãn từng khung của MediaPipe, JSON và HUD
  như lần sửa 9. Lưu ý: nếu driver webcam tự lật gương khung hình trước khi app nhận, nhãn của tay sẽ ngược lại; khi đó chạy thử
  `auto` và xem nhãn nào chiếm đa số trước khi khóa.
- `--smooth-landmarks` (mặc định TẮT): 21 điểm của mỗi khung đi qua `LandmarkSmoother` (`src/inference/level1_core.py`) trước bộ tách,
  cửa sổ phân loại, cử chỉ Xòe 5 ngón và hình vẽ khung xương. Đây là trung bình trượt mũ thích ứng: khi tâm bàn tay (trung bình 21 điểm,
  trục x, y) di chuyển chậm hơn `speed_threshold` = 0.15 đơn vị ảnh mỗi giây thì khung mới chỉ chiếm `alpha_static` = 0.6 (làm mượt mạnh,
  dập rung `z`); nhanh hơn thì chiếm `alpha_dynamic` = 0.9 (bám tay, gần như không trễ). Mất tay ⇒ bộ lọc xóa trạng thái, khung có tay
  đầu tiên sau đó giữ nguyên. Ba giá trị là giá trị thiết kế của kế hoạch; cách đo tốc độ (tâm bàn tay, chỉ x, y) do coder chọn.
  JSON có khóa gốc `landmark_smoothing` = `enabled`, `alpha_static`, `alpha_dynamic`, `speed_threshold`, `frames_static`,
  `frames_dynamic` (số khung lọc với mỗi trọng số) và stage `landmark_smooth`; không cờ ⇒ JSON, stage và kết quả như lần sửa 9.
  Kế hoạch ghi mặc định BẬT, nhưng tiêu chí AC-10d yêu cầu chạy không cờ mới giữ nguyên hành vi cũ: bật mặc định làm đổi landmark của
  mọi khung, nên các test cũ so từng segment với app ở commit trước bị đỏ. Vì vậy cờ mặc định tắt; bật bằng `--smooth-landmarks`.
- Nhắc góc tay (luôn bật, chỉ trên HUD): `foreshortening_ratio` = độ dài 2D / độ dài 3D của ngón trỏ (đầu ngón 8 tới MCP 5, landmark đã
  nhân x, z với rộng / cao khung), bằng 1 khi ngón trỏ nằm trong mặt phẳng ảnh và gần 0 khi chĩa thẳng vào camera. Khi tỉ lệ dưới
  `FORESHORTEN_RATIO_MIN` = 0.3 trên hơn `FORESHORTEN_FRAMES` = 3 khung có tay liên tiếp, HUD hiện dòng màu vàng
  `[Góc tay: Hơi nghiêng tay 20°]`: nghiêng bàn tay một chút để camera thấy ngón tay từ bên cạnh. Khung có tỉ lệ từ 0.3 trở lên hoặc mất
  tay ⇒ dòng biến mất. Không đổi JSON, token hay segment.
- Hai lệnh gợi ý ở trên kết hợp cấu hình classifier lần sửa 7, ngưỡng phát hiện tay 0.35 và CLAHE (mục 8) với khóa tay thuận
  (lệnh của checklist §5 kế hoạch) hoặc với làm mượt landmark; có thể dùng cả hai cờ cùng lúc.
- Giới hạn: tác dụng của khóa tay thuận, của làm mượt và của lời nhắc lên độ chính xác / tỉ lệ thấy tay trên webcam CHƯA được đo; trên clip train (chỉ kiểm logic) dòng
  nhắc xuất hiện ở một số clip (nhiều nhất là `â`) và không xuất hiện ở clip `a` của bộ test D2. Cần phiên webcam của người
  dùng (checklist §5 của kế hoạch); mục này không chép số đo nào.

## 11. Đánh vần nhiều chữ liên tiếp, không tự cách, khóa tay đúng chiều (kế hoạch 15 lần sửa 12)

```bash
python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier_rev9.json --min-detection-conf 0.35 --auto-enhance --dominant-hand lock
```

- Cổng chuyển động (`cls_motion_gate`, config `configs/level1_demo_classifier_rev9.json` = rev8 + khóa này): ở chế độ `classifier`, cửa
  sổ trượt vẫn được phân loại ở mọi khung có tay, nhưng nhãn chỉ được tính vào thời gian giữ `cls_stable_ms` trên các khung mà bộ tách
  thấy tay ĐỨNG YÊN (trạng thái khác `moving`: `M_t` chưa vượt `move_speed`, có trễ như mục `motion_pose`). Khung tay đang di chuyển
  hoặc đang đổi hình dạng (chuyển giữa hai chữ) cắt ngang lượt nhãn, nên tư thế trung gian không bao giờ đủ thời gian giữ để thành chữ
  rác. Ngoại lệ: chữ có dấu (`â`, `ă`, `ê`, `ô`, `ơ`, `ư`, `đ`) ngay sau chữ gốc của nó (trường hợp thay thế `a` → `â`) không bị cổng
  cắt, vì chuyển động đó là một phần của ký hiệu. Dấu thanh: nét vẽ vẫn nằm trong cửa sổ sau khi tay dừng, nên dấu được nhận khi tay
  dừng lại cuối nét. Không có khóa ⇒ decoder như cũ. HUD dòng `[classifier]` thêm `| chờ tay yên` khi cổng đang chặn; JSON `counts.frames_gated` (chỉ khi bật cổng).
- Vì sao không sửa re-arm của `motion_pose`: đường re-arm theo hình dạng tay (`pose_change_rules`) đã dừng ở bước R2 theo luật P2
  (hình dạng tay của nhiều cặp chữ khác nhau quá gần so với độ rung, `reports/level1_realtime_2026-10-05/pose_evidence.json`). Đánh vần
  liên tục dùng chế độ `classifier` + cổng chuyển động; `configs/level1_realtime.json` (mặc định, `motion_pose`) không đổi.
- Dấu cách tự động TẮT mặc định: hạ tay / mất tay quá `word_gap_ms` chỉ được ghi là sự kiện `word_gap` (JSON `auto_space: false`),
  bật lại bằng `--auto-space`; cử chỉ Xòe 5 ngón bật bằng `--gesture-space` (bàn tay thả lỏng dễ bị nhận nhầm là cử chỉ). Phím Space
  luôn thêm dấu cách.
- `--dominant-hand lock`: `HandednessLock` (`src/inference/level1_core.py`) đếm nhãn MediaPipe của các khung có tay đầu tiên
  (`HAND_LOCK_FRAMES`) rồi khóa nhãn đa số cho cả phiên. Không giả định tay phải mang nhãn nào: nếu driver webcam lật gương khung hình,
  MediaPipe gán nhãn `Right` cho tay phải, và cách gán cứng `Right -> Left` của lần sửa 10 làm `canonicalize_hand_sequence` lật x của
  mọi khung (ngón cái thành ngón út: `â` thành `ê`, `d` thành `i`). Bằng chứng trên clip `data/collected_targeted/` (clip train — kiểm
  logic, không phải độ chính xác): `reports/level1_realtime_2026-10-06/dominant_hand_check.json`. HUD `[Tay: đang khóa n/N]` rồi
  `[Tay: khóa Right]` (hoặc `Left`); JSON khóa gốc `dominant_hand` = `mode`, `requested`, `label`, `lock_frames`, `votes`. `Right` /
  `Left` chạy như `lock` và in cảnh báo.
- Bằng chứng cổng chuyển động trên chuỗi ghép clip train (kiểm logic decoder, không phải phiên webcam):
  `reports/level1_realtime_2026-10-06/rearm_check_gate.json` (bản đầu) và `rearm_check_gate_v2.json` (có ngoại lệ chữ biến thể; gate G5
  vẫn trượt, như rev8); kế hoạch và số liệu: `docs/plans/15-lan-sua-12.md`.
- Giới hạn: tác dụng trên webcam của người dùng CHƯA được đo; cần phiên webcam (`--out-json`) để xác nhận.
