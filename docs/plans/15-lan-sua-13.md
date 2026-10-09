# Kế hoạch 15 — LẦN SỬA 13: hoàn thiện Cấp 1 cho buổi DEMO, sửa review phần A theo quyết định người dùng 2026-10-08

> LẦN SỬA 13a (2026-10-08): xem docs/plans/15-lan-sua-13a.md — ngoại lệ E4 (đúng 1 cv2.resize ảnh hiển thị trong render_to_window), sửa AC-U6/AC-0/AC-V4, thêm AC-U6b.
> LẦN SỬA 13b (2026-10-09): xem docs/plans/15-lan-sua-13b.md — thay hàng U2 bằng U2a–U2d, thêm AC-U4b/U7/U8/U9 + script đo AC-U5, THẤP-2 ghi Giới hạn R2, bước X1 trước V1.
> LẦN SỬA 13c (2026-10-09): xem docs/plans/15-lan-sua-13c.md — sửa U2d (gate DC1 fail-closed, giữ ngưỡng 1.25), thêm T1/T2 (chỉ test, khóa đột biến sống U2a–U2c), XW (X1 + thăm dò cửa sổ thật) trước V1, câu Giới hạn R2.
> LẦN SỬA 13d (2026-10-09): xem docs/plans/15-lan-sua-13d.md — chốt P1 (giữ: mất tay hủy giữ space), P2 (đổi: khung trong cooldown không đệm vẫy), NaN = không tay; hàng G2 thay bằng G2a/G2b/G2c (vslt-coder-claude) với AC-D1…D9 (khóa đột biến R2/R4, THẤP-1/4).
> LẦN SỬA 13e (2026-10-09): xem docs/plans/15-lan-sua-13e.md — G2b chọn (a): shim nhập tạm "GESTURE_BACKSPACE_FLASH" CHỈ THÊM dòng trong _hud_module_at (tests/test_level1_display.py) + test AC-E2; AC-G5 giữ đủ 5 tên; đột biến M9/M10 trên worktree.

> CẦN NGƯỜI DÙNG (KHÔNG chặn các bước khác): (1) quay 24 clip cử chỉ thật sau bước G2 (§3.4, ~10 phút) — chỉ bước G5 chờ việc này;
> (2) THÔNG BÁO: gỡ khỏi git KHÔNG xóa 84 npz user1 khỏi lịch sử đã push lên GitHub công khai — xóa hẳn cần viết lại lịch sử + force
> push (không hoàn tác), kế hoạch này KHÔNG làm, người dùng quyết riêng nếu muốn; (3) THÔNG BÁO: `README.md` đang có thay đổi CHƯA commit
> của người dùng ⇒ kế hoạch không sửa README; giới hạn ghi ở `docs/level1_desktop.md`.

Người lập: vslt-planner (local, 2026-10-08). Nhánh làm việc `cloud/2026-10-04-level1-rearm`, mốc HEAD `bcda407`.
Phụ lục này CÓ HIỆU LỰC như nằm trong `docs/plans/15-level1-realtime-desktop.md`; phần nào mâu thuẫn lần sửa 1–12 thì theo lần sửa 13.
Đầu vào: `docs/reviews/15-review.md` phần A (CAO 1–4, TB 5–9, THẤP 10–12), `docs/STATE.md` "Quyết định của người dùng" mục
2026-10-08 (~10:00 và "CODE DO agy + GEMINI VIẾT"), `reports/alphabet_retrain_2026-10-07/REPORT.md`.

Độ khó: XL (toàn lần sửa; từng bước ghi riêng ở §8); vùng nhạy cảm: CÓ (landmark/tiền xử lý realtime, model mặc định, đánh giá, dữ liệu người dùng).

## 0. Quyết định người dùng áp dụng (không hỏi lại)

| # | Quyết định (STATE 2026-10-08) | Hệ quả cho kế hoạch này |
|---|---|---|
| Q1 | GIỮ preset mặc định (`DEFAULT_DEMO_ARGV`, `level1_demo.py:1485-1495`: rev9, làm mượt, conf 0.55, cử chỉ space/backspace, unikey) | Không gỡ cờ nào khỏi preset. ĐO đồng thuận (hạng mục 6) và ghi Giới hạn; không gate nào đổi preset. |
| Q2 | Giữ `DIACRITIC_FUSION` nhưng đúng Unikey/Telex, ghi nguồn + dự đoán gốc | Hạng mục 2. |
| Q3 | Model chữ cái mặc định = v6 `160e0c68…` (đã đặt vào `checkpoints/alphabet_best.pt` 10:05) — thay GATE | Hạng mục 3: test ghim checkpoint cập nhật theo NGOẠI LỆ §5.4; lưu trữ private; ghi giới hạn. |
| Q4 | Gỡ 84 npz + manifest user1 khỏi git (đã chép Drive + SHA256SUMS OK) | Hạng mục 4. |
| Q5 | Cử chỉ CHỈ khi cố ý: xòe 5 ngón = space, vẫy tay trái/phải = backspace | Hạng mục 1: thiết kế lại + gate kích hoạt nhầm đặt trước + độ nhạy trên clip cử chỉ thật. |
| Q6 | Code agy/Gemini: mỗi bước cầu nối xác minh + vslt-reviewer kiểm riêng bước đó TRƯỚC bước kế; logic phức tạp ưu tiên Opus | §8: mỗi bước 1 commit, cột "model gợi ý"; không gộp bước. |

## 1. Mục tiêu và DoD

Mục tiêu: `python level1_demo.py` (preset) chạy ổn định cho buổi demo/báo cáo: cửa sổ phóng to/toàn màn hình không vùng đen, cử chỉ
space/backspace không tự kích hoạt khi ký chữ, gõ dấu kiểu Unikey không phá từ đúng ("thuở", "quơ"), model v6 có hồ sơ truy vết + test
xanh, dữ liệu cá nhân user1 ra khỏi git, mọi lệch còn lại ghi Giới hạn bằng số từ JSON.

DoD phục vụ: DoD 6 (truy vết: token có nguồn + dự đoán gốc), DoD 7 (guard số gõ tay: bỏ hằng cử chỉ khỏi `src/`, không vi phạm mới,
`known=9 allowed=36`), quy tắc số liệu (số trong tài liệu chỉ từ JSON có lệnh + commit), tương đương train↔realtime (đo đồng thuận
preset), quy tắc dữ liệu (không commit landmark người dùng; lưu trữ private + manifest sha256).

## 2. Hạng mục 5 — GIAO DIỆN demo (ưu tiên 1)

### 2.1 Hiện trạng
- `level1_demo.py:1270` `cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)` ⇒ cửa sổ cố định theo ảnh; phóng to/toàn màn hình bằng hệ
  điều hành cho ảnh nhỏ ở góc + vùng đen (WINDOW_AUTOSIZE không co giãn ảnh).
- `level1_demo.py:1213-1221`: `draw_landmarks(frame)` → `display_view(frame, mirror)` → `Hud.compose(view, …)` (`:579-596`: panel PIL
  dưới ảnh, rộng = rộng ảnh camera; font cố định `Hud(font_path, font_size)` `:472-477`; dòng thống kê `cv2.putText` cỡ 0.45 `:595`)
  → `cv2.imshow`. Vẽ chạy trong `_process`, CÙNG luồng xử lý khung (`:1159-1231`) ⇒ chi phí vẽ cộng vào thời gian mỗi khung (chặng
  `hud`, `display`, `frame_total`).
- Khung vào MediaPipe: `frame_mp = frame` (`:1166`, `:1172`); test E3 (`tests/test_level1_equivalence.py`, B4) khóa "khung đưa vào
  process là đúng đối tượng reader trả về", không resize trước MediaPipe.
- `--display-mirror` là `store_true` (`:1444`) ⇒ preset bật mà không tắt được (review THẤP 12).
- Phím đang dùng (`KEY_ACTIONS` `:117-129`, `KEY_QUIT` `:138`, `KEY_PAUSE` `:139`): Backspace, Space, a, r, c, 1–5, n, q/Esc, p. `f` trống.
- Test cửa sổ `_WindowRecorder` (`tests/test_level1_demo.py:365-421`) chỉ patch `imshow, waitKey, getWindowProperty, namedWindow,
  destroyAllWindows`, ghi `image.shape` ⇒ mọi hàm cv2 cửa sổ MỚI phải chịu được việc không có cửa sổ thật.

### 2.2 Thiết kế
- Module mới thuần tính toán `src/inference/level1_display.py`:
  - `fit_layout(cam_w, cam_h, panel_h, win_w, win_h) -> DisplayLayout(scale, content_w, content_h, x0, y0, cam_rect, panel_rect)`:
    nội dung = ảnh camera (cam_w × cam_h) + panel (cam_w × panel_h) xếp dọc; `scale = min(win_w / cam_w, win_h / (cam_h + panel_h))`;
    nội dung co giãn đặt GIỮA cửa sổ (dải đen chỉ ở MỘT cặp cạnh đối nhau). Cửa sổ không hợp lệ (None, ≤ 0, `(-1,-1,-1,-1)`) ⇒
    `scale = 1`, kích thước tự nhiên (= hành vi cũ).
  - `render_to_window(view_bgr, panel_builder, stats_lines, hold_progress, layout) -> ảnh win_h × win_w × 3`: `cv2.resize` (INTER_LINEAR)
    ảnh HIỂN THỊ (đã vẽ landmark + lật gương; KHÔNG phải khung MediaPipe); panel dựng ở chiều rộng `round(cam_w × scale)` với cỡ chữ
    `round(font_size × scale)` (chữ nét ở mọi cỡ, không phóng ảnh panel); thanh hold + dòng thống kê `putText` cỡ `0.45 × scale`.
    Hud theo cỡ chữ cache theo số px (không dựng font mỗi khung); panel cache theo `(width, font_px, nội dung)` như `Hud._key`.
- `level1_demo.py` (CHỈ phần hiển thị):
  - `cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)`; kích thước khởi đầu = tự nhiên.
  - Mỗi khung có cửa sổ: `cv2.getWindowImageRect(WINDOW_NAME)` bọc `try/except (cv2.error, AttributeError)`; lỗi/không hợp lệ ⇒ đường
    cũ `Hud.compose` (ảnh BẰNG HỆT cũ). Hợp lệ ⇒ `render_to_window`.
  - Phím `f`: bật/tắt toàn màn hình `cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN | cv2.WINDOW_NORMAL)`
    (bọc try/except; sự kiện `{"event": "fullscreen", "on": bool}`); cờ `--fullscreen` (mở ở toàn màn hình; KHÔNG thêm vào preset).
    Gợi ý " | f toàn màn hình" thêm vào dòng phím (`:1153`) CHỈ khi grep `tests/` không thấy test ghim nguyên văn dòng đó; nếu có ⇒ đặt
    vào tiêu đề cửa sổ.
  - `--display-mirror` → `argparse.BooleanOptionalAction` (thêm `--no-display-mirror`; mặc định parser vẫn False, preset vẫn bật).
  - Tùy chọn (THẤP 12): panel chỉ HIỂN THỊ 2 cảnh báo cuối (JSON không đổi) — chỉ làm nếu không test cũ nào ghim số dòng cảnh báo; không
    làm được thì ghi progress.
  - KHÔNG đổi: thứ tự xử lý, `frame`/`frame_mp`, `draw_landmarks`, `display_view`, `Hud.compose` (giữ cho test cũ), tập chặng thời gian
    (resize + panel tính vào chặng `hud`).

## 3. Hạng mục 1 — CỬ CHỈ chỉ khi CỐ Ý (ưu tiên 2; ưu tiên Opus)

### 3.1 Hiện trạng
- Space: `is_open_palm_space` (`src/inference/level1_core.py:510-544`, lần sửa 9; `THUMB_SPREAD_RATIO 1.1`, `FINGER_SPREAD_MIN 1.2`) +
  `SpaceGestureTracker` (`level1_demo.py:672-724`): giữ xòe tay `GESTURE_SPACE_HOLD = 250.0` (`:147`) là phát; KHÔNG đòi tay đứng yên.
  Test cũ ghim mặc định 250 (`tests/test_level1_demo.py:2532-2533`) và hành vi tracker (`:2177-2250`).
- Backspace: `is_flat_hand_backspace` (`level1_core.py:556-587`, số trần `0.5 * palm` `:581`, `1.05 * palm` `:583`) +
  `BackspaceGestureTracker.update` (`:626-665`): MỘT khung "tay phẳng" trong cửa sổ 250 ms + `dx >= 0.05` hoặc `dx/palm >= 0.35`,
  `vx >= 0.30`, `dx > 1.1 dy`, `dt >= 0.04` (số trần `:649, 657-659`). Một cú phẩy đơn là đủ.
- Review A3.2 (thăm dò inline, KHÔNG có JSON ⇒ không phải số báo cáo): backspace 24/640 clip hauuto một chữ, space 8/640.
- Guard: `c7bad20` đổi tên `GESTURE_BACKSPACE_WINDOW_MS` → `GESTURE_BACKSPACE_WINDOW` để luật D-binding im (`level1_core.py:548-553`; TB 5).
- App: khung xòe tay vào cửa sổ classifier như khung không tay (`level1_demo.py:1194-1197`); khung "tay phẳng" VẪN vào cửa sổ (tay phẳng
  tĩnh có thể thành chữ, vd giống `b`). Backspace gọi `decoder.reset()` (`:1056-1057`).
- `scripts/collect_targeted_signs.py` nhận ký hiệu bất kỳ (`SYMBOL_MAP.get(s, s)` `:76`), ghi 60 khung (~2 s, `:51`) npz + mp4 + `manifest.csv`
  vào `--out-dir`; MediaPipe `min_detection_confidence=0.35` (`:119`) ≠ 0.5 của train (rủi ro §11).

### 3.2 Thiết kế
Nguyên tắc: KHÔNG có cờ mới ⇒ hành vi cũ y nguyên (test cũ không đổi). Hành vi MỚI bật bằng `--gesture-config <file>`; preset thêm
`--gesture-config configs/level1_gestures.json` (`test_default_webcam_preset` dùng `assertIn` ⇒ thêm cờ không làm đỏ).

1. Config `configs/level1_gestures.json`: mỗi khóa `{"value", "source": "design", "reason"}` (kiểu `level1_realtime.json`). Loader
   `load_gesture_config(path)` (module mới `src/inference/level1_gestures.py`): thiếu/thừa khóa, thiếu source/reason, source ≠ "design",
   giá trị ngoài miền ⇒ ValueError; trả `{"values", "raw", "sha256", "path"}`. Không giá trị mặc định trong mã. Giá trị THIẾT KẾ (không
   chỉnh sau khi đo; lý do ghi vào `reason`):

   | Khóa | Giá trị | Lý do |
   |---|---|---|
   | `space_hold_ms` | 600 | gấp đôi `cls_stable_ms` 300 của rev9, hơn 2 lần mức 250 đã kích hoạt nhầm; tư thế cố ý giữ ~0.5 s+ |
   | `space_dropout_frames` | 1 | chịu 1 khung MediaPipe chập chờn khi giữ, như debounce 1 khung của decoder (lần sửa 7 T2) |
   | `space_rearm_ms` | 300 | phải đổi tư thế/hạ tay đủ lâu mới có dấu cách kế (cũ 150) |
   | `wave_window_ms` | 1500 | 2 nét vẫy (đi + về) ở nhịp ~2–3 nét/s nằm gọn trong 1.5 s |
   | `wave_min_amplitude` | 0.6 | mỗi nét dịch tâm lòng bàn tay ≥ 0.6 × độ dài lòng bàn tay `|p9 − p0|`: vẫy cố ý, không phải rung/trôi |
   | `wave_min_strokes` | 2 | "vẫy" = ít nhất một lần đi và về; một cú phẩy đơn (kiểu cũ) không đủ |
   | `wave_max_vertical_ratio` | 0.5 | biên độ dọc ≤ 0.5 biên độ ngang: loại nét dấu thanh đi chéo/xuống |
   | `wave_min_flat_fraction` | 0.9 | ≥ 90% khung có tay trong các nét là tay phẳng (cũ: 1 khung là đủ) |
   | `wave_cooldown_ms` | 1000 | sau một backspace phải hạ tay/đổi tư thế; vẫy tiếp không tự lặp |
   | `flat_thumb_min_ratio` | 0.5 | số trần `0.5 * palm` (`level1_core.py:581`) đưa vào config, giá trị giữ nguyên |
   | `flat_thumb_max_spread` | 1.05 | số trần `1.05 * palm` (`:583`) đưa vào config, giá trị giữ nguyên |
   | `gesture_flash_ms` | 600 | thời gian hiện dòng HUD sau cử chỉ (như cũ) |
   | `legacy_flick_cooldown_ms`, `_window_ms`, `_min_dx`, `_min_speed`, `_palm_ratio`, `_dx_over_dy`, `_min_dt_s` | 400, 250, 0.05, 0.30, 0.35, 1.1, 0.04 | giá trị của `7a267c7` (người dùng, ngoài kế hoạch) cho `BackspaceGestureTracker` cũ — giữ CHỈ để đường cũ/test cũ bằng hệt; reason ghi nguồn commit |

2. `src/inference/level1_gestures.py` (mới, thuần tính toán, không đồng hồ):
   - `palm_centre(points)` = trung bình điểm 0, 5, 9, 13, 17 (tọa độ `aspect_points`); `palm_len(points) = |p9 − p0|`.
   - `DeliberateSpaceGesture.update(ts_ms, is_palm, has_hand, still) -> bool`: phát đúng 1 lần khi xòe tay VÀ đứng yên liên tục
     ≥ `space_hold_ms` (chịu ≤ `space_dropout_frames` khung lỗi liên tiếp). `still` = `Level1SignSegmenter.state != "moving"` của CÙNG
     khung (dùng lại ngưỡng chuyển động đã hiệu chỉnh của config preset — không thêm ngưỡng tốc độ mới). Mất tay ⇒ hủy giữ. Sau khi phát:
     re-arm khi không tay, hoặc tư thế khác / không yên > `space_rearm_ms`.
   - `WaveBackspaceGesture.update(ts_ms, points_or_None, is_flat) -> bool`: bộ đệm khung có tay trong `wave_window_ms` gần nhất; mất tay
     ⇒ xóa bộ đệm. Nét vẫy theo trễ trên x của `palm_centre`: một nét mới khi x đi ngược khỏi cực trị hiện tại ≥ `wave_min_amplitude ×
     median(palm_len)`. Phát khi số nét ≥ `wave_min_strokes` VÀ tỉ lệ khung phẳng ≥ `wave_min_flat_fraction` VÀ biên độ dọc ≤
     `wave_max_vertical_ratio ×` biên độ ngang (trên khung của các nét đã đếm) VÀ ngoài cooldown. Sau khi phát: xóa bộ đệm, cooldown, chỉ
     re-arm khi hết tay phẳng (không tay, hoặc ≥ 1 khung không phẳng sau cooldown).
   - `GestureEngine(values)`: gom 2 tracker; `step(ts_ms, landmarks_or_None, w, h, still) -> {"space", "backspace", "is_palm", "is_flat"}`;
     gọi `is_open_palm_space` và `is_flat_hand_backspace(points, thumb_min, thumb_spread)`. Đây là đường DUY NHẤT app và script đo cùng gọi.
3. `src/inference/level1_core.py`: xóa hằng `GESTURE_BACKSPACE_COOLDOWN/WINDOW/MIN_DX/MIN_SPEED/FLASH` và số trần trong thân
   `is_flat_hand_backspace`/`BackspaceGestureTracker` (`:548-552, 581, 583, 649, 657-659`); giá trị mặc định lấy từ khóa `legacy_flick_*`
   và `flat_*` của `configs/level1_gestures.json` (đọc LƯỜI một lần, cache; không đọc file lúc import) ⇒ chữ ký + hành vi cũ BẰNG HỆT.
   Không đổi tên né guard; không thêm ALLOWED/KNOWN vào guard chính. `GESTURE_BACKSPACE_DEFAULT = False` (bool) giữ.
4. `level1_demo.py`: `--gesture-config PATH` (mặc định None ⇒ đường cũ). Có cờ ⇒ `GestureEngine` thay `SpaceGestureTracker`/
   `BackspaceGestureTracker` cho cử chỉ đang bật (`--gesture-space`, `--gesture-backspace`); `still = self.segmenter.state != "moving"`;
   khung xòe tay vẫn vào cửa sổ như khung không tay (giữ `:1196`). `--space-hold-ms` có MẶT trong argv ⇒ ghi đè `space_hold_ms` (ghi JSON).
   JSON thêm khóa `gestures` `{config_path, config_sha256, values, overrides, counts: {palm_frames, flat_frames, spaces_added,
   backspaces_added, emits}}` CHỈ khi có `--gesture-config`. Preset thêm `"--gesture-config", "configs/level1_gestures.json"`. Sự kiện
   cử chỉ có `source: "gesture"`. HUD: dòng giữ xòe tay `[Cử chỉ: Dấu cách n/600]`, dòng vẫy `[Cử chỉ: vẫy k/2]`.
5. `scripts/level1_gesture_check.py` (mới): mỗi clip landmark một ký hiệu → timestamps từ fps của manifest (như `level1_rearm_check.py`);
   chạy song song `Level1SignSegmenter` (giá trị config rev9 = config preset) để có `still`; đường `smoothed` (qua `LandmarkSmoother`, như
   preset) và `raw`; cử chỉ `deliberate` (`GestureEngine`) và `legacy` (tracker cũ, chỉ để so). Đếm clip có ≥ 1 lần phát. JSON:
   `generated_by` (lệnh, commit, `code_dirty`), sha config cử chỉ + config rev9, `per_source`, `per_class`, `rates`, `gates` (ngưỡng là hằng
   của script ghi "đặt trước ở 15-lan-sua-13 §3.3"), `pass`. Chế độ `--positives <manifest>` cho §3.4 (thêm số chữ decoder phát trong clip
   cử chỉ khi có `--checkpoint`, chạy `Level1LabelDecoder` rev9 như `level1_rearm_check.py`).

### 3.3 Gate kích hoạt nhầm (đặt TRƯỚC khi đo; coder không đổi)
- Tập âm tính = MỌI clip một ký hiệu có trên máy: hauuto + QIPEDC chữ (`data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv`),
  user1 (`data/collected_targeted/manifest.csv`, vẫn trên đĩa sau hạng mục 4). Thiếu nguồn ⇒ script FAIL (không bỏ qua lặng lẽ). Số clip
  từng nguồn chỉ lấy từ JSON.
- GF1 (backspace): tỉ lệ clip có ≥ 1 backspace, GỘP mọi nguồn, ≤ 0.005 trên CẢ đường `raw` và `smoothed`.
- GF2 (space): tỉ lệ clip có ≥ 1 space, gộp, ≤ 0.010 trên cả hai đường.
- Lý do: backspace xóa chữ (phá hoại) ⇒ chặt gấp đôi; ≤ 1 lần nhầm / 200 ký hiệu (backspace), / 100 ký hiệu (space) ⇒ câu demo ~20 ký hiệu
  có kỳ vọng nhầm ≤ 0.1 backspace, ≤ 0.2 space. Theo nguồn/lớp chỉ BÁO CÁO (QIPEDC quá ít clip cho ngưỡng riêng). Đường `legacy` chỉ báo
  cáo (so với thăm dò 24/640, 8/640; lệch ⇒ ghi chú).
- Luật dừng: GF1 hoặc GF2 trượt ⇒ DỪNG, KHÔNG chỉnh tham số (chỉnh sau khi thấy kết quả biến các clip này thành dữ liệu chỉnh ⇒ cần tập kiểm
  mới); báo planner. Số này là kiểm logic trên ký hiệu thật đã thu (4 người hauuto + QIPEDC + user1), KHÔNG phải tỉ lệ webcam.

### 3.4 Độ nhạy trên clip cử chỉ THẬT — VIỆC NGƯỜI DÙNG (sau bước G2)
Chưa có clip cử chỉ nào (JSON webcam của app không chứa landmark ⇒ không dùng được). Người dùng quay 24 clip (~10 phút):
```
.venv\Scripts\python scripts/collect_targeted_signs.py --signer user1 --symbols gesture_space,gesture_backspace --reps-per-angle 4 --out-dir data/collected_gestures
```
(2 cử chỉ × 3 góc × 4 lần; mỗi clip ~2 s sau đếm ngược; bấm SPACE để ghi.)
- `gesture_space`: xòe đủ 5 ngón (ngón cái dang ra), giữ YÊN ~1 giây trong lúc ghi.
- `gesture_backspace`: bàn tay phẳng (4 ngón duỗi khép, ngón cái duỗi sát ngón trỏ), vẫy ngang trái → phải → trái (≥ 2 nét, mỗi nét ~một bàn
  tay) trong ~1 giây; không vẫy chéo/lên xuống.
`data/collected_gestures/` bị gitignore (bước D2 thêm `.gitignore` riêng; npz/mp4 vốn bị `*.npz`/`*.mp4` gốc chặn) — KHÔNG commit; orchestrator
chép Drive `G:\My Drive\VSLT\` + SHA256SUMS như user1. Gate (đặt trước, đường `smoothed` = preset; `raw` báo cáo):
GT1 ≥ 10/12 clip `gesture_space` có ≥ 1 space và 0 backspace; GT2 ≥ 10/12 clip `gesture_backspace` có ≥ 1 backspace và 0 space.
Trượt ⇒ DỪNG, báo planner + người dùng (không tự chỉnh ngưỡng). n = 12/cử chỉ là kiểm khói, khoảng tin cậy rộng — ghi rõ.
Tùy chọn (không gate): người dùng chạy preset với `--out-json _work/u_demo.json`, đánh vần một câu và dùng cử chỉ; JSON chỉ để xem sự kiện.

## 4. Hạng mục 2 — GÕ KIỂU UNIKEY (ưu tiên 3; ưu tiên Opus)

### 4.1 Hiện trạng
- `DIACRITIC_FUSION` khai báo HAI lần: `src/inference/level1_segmenter.py:412-419` và `src/inference/level1_core.py:252-259` (bản sau che bản
  import ở `level1_core.py:32`). 15 cặp: a{â,ô,ê→â; ă→ă}, o{â,ô,ê→ô; ơ,ư→ơ}, e{â,ô,ê→ê}, u{ơ,ư→ư}, d{đ→đ}.
- Áp ở `Level1Speller._apply` (`level1_core.py:358-362`) và `on_label` (`:387-392`): chỉ nhìn `tokens[-1]`, ghi `_log("replace", target,
  "model", …, replaced=old)` — nguồn "model" dù token do luật sinh, KHÔNG có dự đoán gốc (CAO 3).
- Lỗi (review): `[t,h,u]`+ơ+dấu hỏi ⇒ "thử" (đúng "thuở"); `[q,u]`+ơ ⇒ "qư" (đúng "quơ").
- `is_variant_of` (`level1_segmenter.py:422-430`) dùng bảng để miễn cổng chuyển động (luật 7, `3510c3a`); docstring luật 7 cũ (`:553-555`).
- Test cũ phải giữ xanh: `tests/test_level1_core.py:917-954` (`["a"]+ô→["â"]`, `["b","o"]+â→["b","ô"]`, `["b","a"]+ă→["b","ă"]`,
  `["u"]+ơ→["ư"]`), `tests/test_level1_lan_sua_12.py:92-131` (e+â→"ê", o+â→"ô", u+ơ→"ư"; đều KHÔNG phụ âm đầu).
- `compose()` (`src/inference/fingerspelling_compose.py:7-25`): dấu thanh áp cả âm tiết dù đứng đâu. KHÔNG sửa compose.

### 4.2 Thiết kế (luật thay chữ đặt trước; không có luật dấu thanh mới)
Module mới `src/inference/level1_unikey.py`: `fusion_target(tokens, prediction) -> Optional[(index, target, rule)]` thuần;
`level1_core.py` xóa bảng trùng (bản DUY NHẤT ở `level1_segmenter.py`) và gọi hàm này ở CẢ `_apply` và `on_label`.
- F1 Vị trí gốc: chữ cái CUỐI của âm tiết đang gõ (sau SPACE cuối); sau nó chỉ được có token dấu thanh (Telex "asa" → "ấ"). Âm tiết không chữ
  cái, chữ cuối không là khóa bảng, hoặc dự đoán không thuộc bảng của chữ đó ⇒ không ghép (thêm token như cũ).
- F2 Bảng = 15 cặp hiện có, KHÔNG thêm/bớt. Tương ứng Telex: a+{â,ô,ê} ≙ "aa"→â; a+ă ≙ "aw"→ă; o+{â,ô,ê} ≙ "oo"→ô; o+{ơ,ư} ≙ "ow"→ơ;
  e+{â,ô,ê} ≙ "ee"→ê; u+{ơ,ư} ≙ "uw"→ư; d+đ ≙ "dd"→đ.
- F3 Ngoại lệ "uơ" (chính tả: thuở, quơ, huơ, khuơ): (u, ơ) CHỈ ghép khi `u` là chữ cái ĐẦU âm tiết (không phụ âm đầu, kể cả `q`); có phụ âm đầu
  ⇒ giữ đúng dự đoán "ơ" (DoD 6: không thay dự đoán khi chuỗi gốc hợp lệ). (u, ư) luôn ghép. (u, ơ) là cặp DUY NHẤT của bảng mà chuỗi gốc có
  thể hợp lệ (aâ, aô, aê, aă, oâ, oô, oê, oơ, oư, eâ, eô, eê, uư, dđ không có trong âm tiết tiếng Việt).
- F4 qu/gi: `[q,u]`+â ⇒ "quâ"; `[q,u]`+ơ ⇒ "quơ" (F3); `[g,i,a]`+â ⇒ "giâ"; `[g,i]`+ê ⇒ "giê".
- F5 ươ: `[…,ư]`+ơ ⇒ "ươ"; `[u]`+ơ ⇒ "ư" (F3) rồi +ơ ⇒ "ươ". KHÔNG cài luật Telex "uow→ươ" (đổi hai token một lúc = đoán chữ model không đưa
  ra); ghi Giới hạn: "uơ" sau phụ âm đầu không tự thành "ươ" — ký thẳng chữ "ư".
- F6 Ghép không tạo/xóa/dời token dấu thanh; text luôn = `compose(tokens)["text"]`.
- F7 Truy vết: sự kiện `{"event": "token", "action": "replace", "token": target, "source": "fusion", "prediction": <nhãn model>,
  "confidence", "replaced": <chữ gốc>, "index", "rule": "<gốc>+<nhãn>", "seq", "t_ms", "tokens_after"}`; `on_label` trả `action: "replace"`.
  Nhánh `VARIANT_BASE` của decoder (token = đúng dự đoán) giữ `source: "model"`.
- `is_variant_of` KHÔNG đổi (không có ngữ cảnh âm tiết; đổi = đổi decoder đã đo ở `reports/alphabet_retrain_2026-10-07/rearm_check_gate_v6.json`).

### 4.3 Bảng tham chiếu cho test (oracle viết NGUYÊN VĂN trong test, độc lập với mã)
Dòng: tokens trước + dự đoán → tokens sau → text (phím Telex tương ứng).
- 15 cặp F2 trên âm tiết `[b, <gốc>]`, vd `[b,a]`+ô → `[b,â]` "bâ" ("baa"); `[b,o]`+ư → `[b,ơ]` "bơ" ("bow"); `[b,e]`+ô → `[b,ê]` "bê" ("bee");
  `[b,u]`+ư → `[b,ư]` "bư" ("buw"); `[đ,i]` không áp; `[d]`+đ → `[đ]` "đ" ("dd"); NGOẠI LỆ `[b,u]`+ơ → `[b,u,ơ]` "buơ" (F3, có phụ âm đầu).
- Ca chính tả: `[t,h,u]`+ơ+dấu hỏi → "thuở"; `[q,u]`+ơ → "quơ"; `[h,u]`+ơ → "huơ"; `[k,h,u]`+ơ → "khuơ"; `[u]`+ơ → `[ư]` "ư"; `[u]`+ơ+ơ →
  "ươ"; `[n,g,ư]`+ơ → "ngươ"; `[q,u]`+â → "quâ"; `[g,i,a]`+â → "giâ"; `[g,i]`+ê → "giê"; `[b,a,dấu sắc]`+â → `[b,â,dấu sắc]` "bấ" (F1);
  `[b,a," "]`+â → `[b,a," ",â]` (không qua dấu cách); `[]`+â → `[â]`; `unikey_mode=False`: `[b,a]`+â → `[b,a,â]`.
- `[b,u]`+ơ cố ý KHÁC hành vi cũ ("bư"); không test cũ nào ghim ca có phụ âm đầu (đã kiểm hai đoạn test ở §4.1).

## 5. Hạng mục 3 — MODEL MẶC ĐỊNH v6 + test ghim (ưu tiên 4)

### 5.1 Hiện trạng
- `checkpoints/alphabet_best.pt` = v6 `160e0c68…` (STATE 10:05; v5 ở `alphabet_best_v5.pt`, gốc a6311820 ở `alphabet_best_2026-09-27.pt`);
  `checkpoints/` gitignore (`.gitignore:64`). `backend/main.py` đọc `checkpoints/alphabet_best.pt` — KHÔNG sửa.
- 4 test đỏ (review A1) — nguyên nhân đọc từ mã:
  1. `tests/test_hand_live_equivalence.py:100` so `H.deployed_sha256()` = `scripts/hand_live_check.py:251-253` đọc
     `PROVENANCE_JSON` (`:46`, provenance 2026-09-27). Cũng dùng ở `tests/test_frontend_contract.py:278`.
  2. `tests/test_status_privacy.py:142` đọc hằng riêng `PROVENANCE` (`:29`, provenance 2026-09-27).
  3. `tests/test_fingerspelling_api.py:209` KeyError `'hauuto_aa_tai_B_001_tail_â'`: KHÔNG do checkpoint — `scripts/train_alphabet_real.py:69`
     `load(data_dir, slice_compound=True, …)` mặc định nay thêm mẫu cắt lát có `sample_id` không có trong manifest; test gọi `load(REAL_DATA)`
     (`:202`) với checkpoint `reports/alphabet_real_run_2026-09-25/…` (`:34`).
  4. `tests/test_fingerspelling_deployed.py:61` KeyError `'selected'`: module dựng cho checkpoint NESTED a6311820 (đường offline
     `train_alphabet_nested.load`, provenance V1–V6 chỉ áp cho run nested — `scripts/alphabet_ckpt_provenance.py:8-22`); v6 do
     `train_alphabet_real.py` (kernel) sinh, không có `selected`.
- v6 `trained_on` = `{"source": "hauuto", "signers", "clips"}` ghi cứng ở `train_alphabet_real.py:270` dù kernel dùng thêm
  `--extra-data-dir data/collected_targeted` (`kaggle/vsl-train-alphabet/train_alphabet_kernel.py:13`) ⇒ endpoint status báo nguồn "hauuto"
  (thiếu user1). Không sửa checkpoint (đổi sha); ghi vào hồ sơ + Giới hạn.
- Số v5/v6: `reports/alphabet_retrain_2026-10-07/{retrain_summary_v5.json, retrain_summary_v6.json, ckpt_compare.json, rearm_check_gate_v6.json}`
  (REPORT.md §1–3: QIPEDC top-1 v6 23/46 vs v5 25/46, top-3 65.2 vs 73.9; G1, G5 trượt) — tài liệu phải đọc số từ JSON, không chép REPORT.md.

### 5.2 Thiết kế
- `scripts/alphabet_deploy_record.py` (mới) → `reports/alphabet_deploy_2026-10-08/deployment.json`, sinh tại commit sạch. Đầu vào:
  checkpoint đang đặt, các JSON ở `reports/alphabet_retrain_2026-10-07/`, slug kernel `phmvnsm33/vsl-train-alphabet` v6, clone `8c53795`.
  Lược đồ: `checkpoints.deployed {path, sha256 (tính từ file), kernel, kernel_version, clone_commit}` (CÙNG đường khóa
  `checkpoints.deployed.sha256` như provenance cũ), `checkpoints.previous` [v5 (sha tính từ `alphabet_best_v5.pt` nếu có, không thì null +
  ghi chú), 2026-09-27 (sha đọc từ `reports/alphabet_deploy_2026-09-27/provenance.json`)], `decision {by: "user", date, ref: "docs/STATE.md
  Quyết định 2026-10-08 ~10:00 (3)", gate: "không có — G1, G5 trượt (rearm_check_gate_v6.json)"}`, `trained_on` (nguyên văn từ checkpoint)
  + `trained_on_note` (dữ liệu thật: hauuto + user1 collected_targeted), `preprocessing`, `evaluation` (số SAO CHÉP BẰNG MÃ theo đường khóa từ
  các JSON nguồn, mỗi số kèm `{json, key}`; khóa thiếu ⇒ lỗi, không gõ tay), `limitations` (v6 đã train trên user1; QIPEDC là tập duy nhất
  chưa thấy, ~1–3 clip/lớp), `generated_by {command, git_commit, code_dirty}`. Sha khác tiền tố `160e0c68` ⇒ exit lỗi (không ghi).
- `scripts/hand_live_check.py:46` `PROVENANCE_JSON` → `reports/alphabet_deploy_2026-10-08/deployment.json` (`deployed_sha256` giữ nguyên
  thân hàm). Không sửa test 1 và `test_frontend_contract`.
- `scripts/train_alphabet_real.py`: `load(data_dir, slice_compound=False, apply_overrides=True)` (mặc định về như trước cắt lát); `main()`
  truyền TƯỜNG MINH `slice_compound=True` ở cả hai lời gọi (`:232`, `:234`) ⇒ lệnh train (kernel) bằng hệt v6. Không sửa test 3.
- Test 2 và 4: NGOẠI LỆ §5.4.
- Test mới `tests/test_alphabet_deployed_v6.py` (cùng sức mạnh với module 4 nhưng cho v6, đường offline = mã train của v6): sha
  `checkpoints/alphabet_best.pt` == `deployment.json`; `ckpt["preprocessing"] == train_alphabet_real.PREPROCESSING`; backend `POST
  /api/fingerspelling/sequence` == offline (`train_alphabet_real.load(…, slice_compound=False)` + `build` + forward CPU) trên CÙNG mẫu như
  module 4 (15 clip/người hauuto, rng 0, + mọi QIPEDC): prediction ==, |Δconfidence| ≤ 1e-4, top-3 ==; nguồn lật gương cho cùng kết quả (5 clip
  đầu); `/api/fingerspelling/status` `trained_on` khớp checkpoint; `deployment.json` evaluation == giá trị JSON nguồn (tính lại bằng mã).
  Thiếu file ⇒ skip có tên file (như module cũ).
- Lưu trữ: v6 (bắt buộc) + v5 (nếu có trên đĩa) lên dataset Kaggle PRIVATE mới `phmvnsm33/vslt-alphabet-ckpt-2026-10-08` bằng công cụ D1;
  manifest `reports/alphabet_deploy_2026-10-08/kaggle_checkpoint_manifest.json`. KHÔNG dùng `scripts/archive_private_kaggle.py` (chỉ ghi
  `reports/private_archive_<ngày>/…` (`:252-262`), mà `tests/test_private_artifacts.py:32-34` đọc manifest MỚI NHẤT của mẫu đó ⇒ sẽ đỏ).
- Tài liệu: `docs/level1_desktop.md` dòng 4 ("không đổi trong kế hoạch 15") + mục mới "Model v6 và giới hạn" (số trích từ `deployment.json`
  kèm đường khóa). README KHÔNG sửa (đang có thay đổi chưa commit của người dùng).

### 5.3 Không làm
Không đổi `backend/main.py`, không sửa `reports/alphabet_deploy_2026-09-27/provenance.json`, không chạy lại `alphabet_ckpt_provenance.py`
cho v6 (V1–V6 chỉ áp cho run nested — đặt verdict giả là sai), không train lại, không đẩy kernel.

### 5.4 NGOẠI LỆ sửa test cũ (do ĐỔI MODEL theo Q3) — danh sách đóng
Chỉ được đổi đúng các dòng sau; mọi file test có sẵn khác: 0 dòng xóa.
- E1 `tests/test_status_privacy.py:29`: đường dẫn `PROVENANCE` → `reports/alphabet_deploy_2026-10-08/deployment.json` (đường khóa không đổi).
- E2 `tests/test_fingerspelling_deployed.py`: `:31` `DEPLOYED_CKPT` → `checkpoints/alphabet_best_2026-09-27.pt` (module này từ nay kiểm checkpoint
  a6311820 — checkpoint mà provenance 2026-09-27 ghim — tại đường lưu trữ; v6 do module mới kiểm); `:155` và `:174` chuỗi `"alphabet_best.pt"` →
  `os.path.basename(DEPLOYED_CKPT)`; docstring dòng 2 ghi lại phạm vi. (Coder đọc `backend/main.py` — KHÔNG sửa — xác nhận `_alphabet_meta["checkpoint"]`
  là basename của `ALPHABET_CKPT`; nếu không ⇒ DỪNG, báo planner.)
- E3 `tests/test_level1_guard.py`: chỉ THÊM 3 file mới (`level1_display.py`, `level1_gestures.py`, `level1_unikey.py`) vào danh sách file quét
  (nếu danh sách viết trên một dòng thì dòng đó được thay, giữ mọi phần tử cũ) — thắt chặt, không nới.
KHÔNG được: đổi loại assertion, dung sai, cỡ mẫu, thêm skip, xóa test, sửa `test_hand_live_equivalence`, `test_frontend_contract`,
`test_fingerspelling_api`, `test_alphabet_ckpt_provenance`, `test_private_artifacts`, `test_backend_source_guard`, hay bất kỳ test Level 1 nào khác.
Nếu sau V1 còn test cũ đỏ vì ghim nhãn/số của checkpoint cũ ⇒ DỪNG, báo planner (không tự thêm ngoại lệ).

> LẦN SỬA 13a (2026-10-08): xem docs/plans/15-lan-sua-13a.md — ngoại lệ E4 (đúng 1 cv2.resize ảnh hiển thị trong render_to_window), sửa AC-U6/AC-0/AC-V4, thêm AC-U6b.

## 6. Hạng mục 4 — GỠ dữ liệu user1 khỏi git (ưu tiên 5)

### 6.1 Hiện trạng
- `.gitignore:43-44` `!data/collected_targeted/manifest.csv`, `!data/collected_targeted/**/*.npz` (thêm ở `fd5ceea`, cùng lúc viết lại toàn file —
  đổi kết thúc dòng, review A6). Gốc đã có `*.npz` (`:35`), `*.mp4` (`:32`).
- `tests/test_private_artifacts.py:82-93` (test_g) khóa `.gitignore`: `git diff b337aee HEAD -- .gitignore` chỉ được có ĐÚNG 1 dòng thêm bắt đầu
  `+#` và 0 dòng xóa ⇒ nhiều khả năng ĐANG ĐỎ từ `fd5ceea` (review không chạy module này; M0 đo).
- Kernel `kaggle/vsl-train-alphabet/train_alphabet_kernel.py:11-13`: clone nhánh rồi `--extra-data-dir data/collected_targeted`.
- Bản sao: `G:\My Drive\VSLT\collected_targeted_user1_2026-10-08\` + SHA256SUMS (sổ local `_work/user1_sha256.txt`).

### 6.2 Thiết kế
- D1 công cụ `scripts/private_files_kaggle.py` (mới; dùng lại NGUYÊN các hàm của `scripts/archive_step4_kaggle.py`: `upload`, `wait_ready`,
  `private_from_list`, `private_from_metadata`, `remote_files`, `sha256_file`, `require_outside_repo`, `check_dataset_ref`, mã thoát cùng quy ước):
  - `stage --files-from <danh sách đường dẫn tương đối repo> --staging <ngoài repo> --dataset <slug> --title … --license other`: chép phẳng
    (`/` → `__`), `SHA256SUMS`, `dataset-metadata.json` `isPrivate: true`; quét chuỗi giống credential (như script cũ).
  - `upload`, `verify --manifest-out <path>`: hai nguồn private đều True (không ⇒ exit 4, DỪNG), danh sách + kích thước khớp, tải về ngoài repo,
    sha256 khớp; manifest `{generated_by{script, command, git_commit, code_dirty}, dataset{slug, is_private, is_private_sources}, files[{local_path,
    archive_name, sha256, bytes}]}`. `--manifest-out` khớp `reports/private_archive_*` ⇒ exit 2 (bảo vệ test_private_artifacts).
  - `materialize --manifest M --from <thư mục dataset> --to <đích>`: dựng lại cây theo `local_path`, kiểm sha256 từng file; thiếu/thừa/sai ⇒ exit 3.
- D2 user1: danh sách file = `git ls-files data/collected_targeted` tại commit TRƯỚC khi gỡ (85 mục kỳ vọng: 84 npz + manifest.csv — số thật lấy từ
  lệnh); mp4 KHÔNG tải (kernel không cần; Drive giữ). Đối chiếu sha từng file với `_work/user1_sha256.txt` (không có ⇒ mở Drive theo quy tắc STATE
  2026-10-04 và dùng SHA256SUMS.txt) — lệch ⇒ DỪNG. Dataset PRIVATE `phmvnsm33/vslt-user1-targeted-2026-10-08`; manifest
  `reports/private_data_2026-10-08/user1_targeted_manifest.json`. Rồi: `git rm -r --cached data/collected_targeted` (file vẫn trên đĩa; KHÔNG viết
  lại lịch sử); thêm `data/collected_targeted/.gitignore` và `data/collected_gestures/.gitignore` nội dung `*` + `!.gitignore` (luật gitignore cấp
  thư mục con thắng luật phủ định ở gốc); `.gitignore` gốc: nếu M0 cho test_g ĐỎ và `git diff --ignore-cr-at-eol fd5ceea^ HEAD -- .gitignore` chỉ
  gồm đúng 2 dòng phủ định trên ⇒ khôi phục BYTE-EXACT `git show fd5ceea^:.gitignore` (gỡ phủ định + kết thúc dòng cũ); khác ⇒ DỪNG, báo planner.
  Không thêm dòng nào vào `.gitignore` gốc (test_g không nới; khóa của nó giữ nguyên ý nghĩa).
- `docs/data_registry.md` mục mới `## 1c. user1 — dữ liệu tự quay của người dùng (Level 1)`: nguồn (người dùng tự quay bằng
  `scripts/collect_targeted_signs.py`, webcam, MediaPipe 0.10.14 `min_detection_confidence` 0.35), đồng ý (chính chủ, dùng nội bộ dự án — STATE
  2026-10-08), lưu trữ (Drive + Kaggle private + manifest), KHÔNG commit, dùng trong train v4–v6 (fold LOSO user1), lịch sử git công khai vẫn chứa
  bản commit từ `fd5ceea` (xóa hẳn = viết lại lịch sử, người dùng quyết); `data/collected_gestures/` (clip cử chỉ) cùng quy tắc.
- D3 kernel: bỏ `--extra-data-dir data/collected_targeted` (đọc từ clone); thêm bước `python scripts/private_files_kaggle.py materialize --manifest
  reports/private_data_2026-10-08/user1_targeted_manifest.json --from <thư mục dataset gắn vào /kaggle/input> --to /tmp/extra` rồi
  `--extra-data-dir /tmp/extra/data/collected_targeted`; `kernel-metadata.json` `dataset_sources` thêm slug. KHÔNG đẩy kernel (đẩy = version mới,
  đổi "output mới nhất" mà STATE dùng để tải checkpoint; chỉ đẩy khi có đợt train mới — ghi rủi ro "chưa chạy thật trên Kaggle").

## 7. Hạng mục 6 — các vấn đề còn lại của review phần A (ưu tiên 6)

### 7.1 Đồng thuận preset (CAO 1; Q1 giữ preset)
- Hiện trạng: preset làm mượt EMA `LandmarkSmoother` trước bộ tách + cửa sổ classifier (`level1_demo.py:1177-1181, 1191, 1196`), conf 0.55 vs
  0.5 của train (`DEFAULT_MIN_DETECTION_CONF` `:136`); không test nào đo.
- Thiết kế `scripts/level1_preset_agreement.py` (mới; dùng `Level1Classifier`, `LandmarkSmoother`, `HandLandmarkSession` CÓ SẴN — không chép
  tiền xử lý) → `reports/level1_realtime_2026-10-08/preset_agreement.json`:
  - A (làm mượt, mọi clip landmark: hauuto, QIPEDC, user1): A1 top-1 của `classify` cả clip thô vs làm mượt (timestamps từ fps); A2 chuỗi nhãn
    decoder rev9 trên clip đơn (như G6 của `level1_rearm_check.py`) thô vs làm mượt — tỉ lệ BẰNG NHAU.
  - B (conf, mẫu CỐ ĐỊNH 15 clip/người hauuto rng 0 + mọi QIPEDC, chạy MediaPipe lại trên VIDEO): conf 0.5 vs 0.55: tỉ lệ khung thấy tay, top-1 đồng
    thuận; tổ hợp preset (0.55 + làm mượt) vs đường train (0.5 thô).
  - Checkpoint = v6 (sha ghi vào JSON). Ghi rõ: hauuto + user1 đã có trong train v6 ⇒ đây là độ nhạy với tiền xử lý, KHÔNG phải độ chính xác.
- Ngưỡng THÔNG BÁO (đặt trước, không phải gate, không đổi preset): bất kỳ tỉ lệ đồng thuận nào < 0.95 ⇒ planner báo người dùng xem lại Q1 (CẦN NGƯỜI
  DÙNG, không chặn demo). Mọi tỉ lệ ghi vào Giới hạn.

### 7.2 rev8/rev9 không truy được (CAO 4, TB 7)
- Hiện trạng: `configs/level1_demo_classifier_rev8.json` viết tay, `_rev8_decision.evidence = "_work/webcam_trace.json"` (không commit), `_about`
  ghi `cls_conf_tone 0.62, cls_stable_ms_tone 140` ≠ giá trị thật 0.70 / 200; rev9 = rev8 + `cls_motion_gate` (test khóa); preset dùng rev9.
- Thiết kế: KHÔNG sửa rev8/rev9 (đổi file ⇒ đổi sha đã ghi trong các JSON đo). Nếu `_work/webcam_trace.json` còn và chỉ chứa trường trace (không
  landmark/khung): chạy `scripts/level1_trace_report.py` (lần sửa 6) → `reports/level1_realtime_2026-10-08/rev8_tuning_trace_summary.json` (thêm
  `used_for_tuning: true`; trace gốc không commit). Không còn ⇒ ghi "nguồn không còn". Cả hai trường hợp: Giới hạn ghi "cls_* của rev8/rev9 chỉnh tay
  theo phiên webcam người dùng (đã dùng để chỉnh, không độc lập); `_about` rev8 lệch giá trị thật — giá trị chạy là `values`; rev9 trượt G5; v6 trượt
  G1, G5 (`reports/alphabet_retrain_2026-10-07/rearm_check_gate_v6.json`, số đọc từ JSON)".

### 7.3 Docstring luật 7 (TB 6) và AC2 (TB 8), THẤP 10
- `src/inference/level1_segmenter.py:547-555`: docstring luật 7 ghi `VARIANT_BASE[prediction] == last` ⇒ sửa thành `is_variant_of(prediction, last)`
  (VARIANT_BASE hoặc DIACRITIC_FUSION, `3510c3a`) — CHỈ docstring. Số hiện hành của decoder trên v6 = `rearm_check_gate_v6.json` (đo trên code decoder
  của `3510c3a` = HEAD); số của lần sửa 12 §4 ghi là lịch sử.
- AC2 qua `main()`: tách `effective_argv(argv)` (thuần) từ `main()` (`level1_demo.py:1498-1501`, logic không đổi); test: `effective_argv([])` parse ra
  `auto_space False`; `main([])` với `Level1App` bị patch (không mở camera) nhận args `auto_space False`, `gesture_config` = file cử chỉ.
- THẤP 10: thêm test MỚI khẳng định `meta["filled"] == {}` cho config hiện hành (`tests/test_level1_rearm_check.py`, chỉ thêm; không sửa assertion cũ).

## 8. Chia việc (mỗi bước 1 commit `15: L13-<mã> …`; bước sinh JSON có commit báo cáo riêng tại commit code sạch)

Quy ước (giữ §4 gốc): `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`; log tạm `_work/_plan15_l13/`; `git commit -- <đường dẫn cụ thể>`
(KHÔNG stage `README.md` và 3 file ` D` của người dùng); trước sửa symbol có sẵn: `node .gitnexus/run.cjs impact "<symbol>" --direction upstream
--repo .` (ghi 15-progress; HIGH/CRITICAL ⇒ ghi + chạy đủ test liên quan); trước commit: `detect-changes --scope all`; test viết TRƯỚC, đỏ có log;
sau mỗi bước: cầu nối xác minh độc lập + vslt-reviewer kiểm riêng bước đó (Q6) rồi mới giao bước kế.

| # | Mã | Nội dung | Phụ thuộc | Giờ | Độ khó / model gợi ý |
|---|---|---|---|---|---|
| 1 | M0 | Mốc: HEAD, sha checkpoint (= v6 160e0c68…), `git status` → `_work/_plan15_l13/m0_status.txt`; chạy AC-1 (§9) → ghi Ran/FAIL/ERROR/skip từng test đỏ vào 15-progress (kỳ vọng đỏ: 4 test review A1 + có thể `test_frontend_contract` pin + `test_private_artifacts.test_g`). Không sửa mã. | — | 0,5 | S / gemini-high |
| 2 | U1 | `src/inference/level1_display.py` + `tests/test_level1_display.py` (AC-U1–U3, viết trước, đỏ). | M0 | 1,5 | M / gemini-high |
| 3 | U2 | Nối app: WINDOW_NORMAL, getWindowImageRect có dự phòng, phím `f`, `--fullscreen`, `--no-display-mirror`; test AC-U4, U6; đo AC-U5 → `reports/level1_realtime_2026-10-08/display_cost.json`. | U1 | 1,5 | M / gemini-high |
| 4 | G1 | `configs/level1_gestures.json` + `src/inference/level1_gestures.py` (loader, 2 tracker, engine) + `tests/test_level1_gestures.py` (AC-G1–G3). | M0 | 2 | L / **Opus** |
| 5 | G2 | Hằng cũ → config (`level1_core.py`), `--gesture-config`, preset, JSON `gestures`, HUD; test AC-G4–G6; guard. | G1 | 1,5 | L / **Opus** |
| 6 | G3 | `scripts/level1_gesture_check.py` + `tests/test_level1_gesture_check.py`; chạy → `reports/level1_realtime_2026-10-08/gesture_false_trigger.json` (commit riêng); GF1/GF2 (AC-G7). Trượt ⇒ DỪNG. | G2 | 1,5 + chạy | M / **Opus** |
| 7 | K1 | `src/inference/level1_unikey.py` + `tests/test_level1_unikey.py` (bảng §4.3, AC-K1, K5). | M0 | 1,5 | M / **Opus** |
| 8 | K2 | Nối `Level1Speller` (`_apply`, `on_label`), xóa bảng trùng, sự kiện `source: "fusion"`; AC-K2–K4, K6. | K1 | 1 | M / **Opus** |
| 9 | V1 | `scripts/alphabet_deploy_record.py` + chạy → `deployment.json` (commit riêng); `hand_live_check.py:46`; `train_alphabet_real.load` mặc định; ngoại lệ E1/E2; `tests/test_alphabet_deployed_v6.py`, `tests/test_train_alphabet_real_load.py`; AC-V1–V4. | M0 | 2 | L / **Opus** (vùng nhạy cảm: model mặc định, đánh giá) |
| 10 | D1 | `scripts/private_files_kaggle.py` + `tests/test_private_files_kaggle.py` (api giả, không mạng; AC-D1). | M0 | 2 | M / gemini-high |
| 11 | V2 | Lưu trữ v6 (+v5) private → `reports/alphabet_deploy_2026-10-08/kaggle_checkpoint_manifest.json`; AC-V5. | D1, V1 | 0,75 | S / gemini-high |
| 12 | D2 | Tải user1 private + manifest; `git rm -r --cached`; `.gitignore` con + khôi phục gốc; `docs/data_registry.md` §1c; `tests/test_level1_private_data.py`; AC-D2. | D1 | 1,5 | M / **Opus** (thao tác index git, dữ liệu người dùng) |
| 13 | D3 | Kernel đọc dataset private qua `materialize`; `kernel-metadata.json`; test AC-D3. | D2 | 1 | S / gemini-high |
| 14 | R1 | `scripts/level1_preset_agreement.py` + test; chạy → `preset_agreement.json` (commit riêng); AC-R1. | V1 | 2 + chạy | L / **Opus** (đánh giá, tiền xử lý) |
| 15 | R2 | Docstring luật 7; `effective_argv` + test AC2; test `filled == {}`; rev8 trace summary (nếu có); `docs/level1_desktop.md` cập nhật toàn bộ Giới hạn (§9 AC-R3); 15-progress; AC-1 cuối. | mọi bước trên | 1,5 | M / gemini-high |
| 16 | G5 | (sau khi NGƯỜI DÙNG quay §3.4) `level1_gesture_check.py --positives` → `gesture_sensitivity.json`; GT1/GT2 (AC-G8). | G3 + clip người dùng | 0,5 | S / gemini-high |
> LẦN SỬA 13b (2026-10-09): xem docs/plans/15-lan-sua-13b.md — thay hàng U2 bằng U2a–U2d, thêm AC-U4b/U7/U8/U9 + script đo AC-U5, THẤP-2 ghi Giới hạn R2, bước X1 trước V1.
> LẦN SỬA 13c (2026-10-09): xem docs/plans/15-lan-sua-13c.md — sửa U2d (gate DC1 fail-closed, giữ ngưỡng 1.25), thêm T1/T2 (chỉ test, khóa đột biến sống U2a–U2c), XW (X1 + thăm dò cửa sổ thật) trước V1, câu Giới hạn R2.
> LẦN SỬA 13d (2026-10-09): xem docs/plans/15-lan-sua-13d.md — chốt P1 (giữ: mất tay hủy giữ space), P2 (đổi: khung trong cooldown không đệm vẫy), NaN = không tay; hàng G2 thay bằng G2a/G2b/G2c (vslt-coder-claude) với AC-D1…D9 (khóa đột biến R2/R4, THẤP-1/4).
> LẦN SỬA 13e (2026-10-09): xem docs/plans/15-lan-sua-13e.md — G2b chọn (a): shim nhập tạm "GESTURE_BACKSPACE_FLASH" CHỈ THÊM dòng trong _hud_module_at (tests/test_level1_display.py) + test AC-E2; AC-G5 giữ đủ 5 tên; đột biến M9/M10 trên worktree.

Tổng ≈ 22 giờ coder. Đường tới DEMO (thứ tự ưu tiên của orchestrator): M0 → U1 → U2 → G1 → G2 → G3 → K1 → K2 (≈ 11,5 h) — sau K2 có thể demo;
V1 nên xong trước demo (test xanh, hồ sơ model). Cắt khi thiếu thời gian (cắt từ cuối): R1 → D3 → V2 → R2 (giữ phần docs Giới hạn tối thiểu) → D2/D1.
G1 và K1 không phụ thuộc nhau (có thể xen), nhưng Q6 bắt review từng bước ⇒ vẫn giao tuần tự.

## 9. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

Lệnh test chung (`PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python`):
- AC1-ngắn (16 module, lệnh nguyên văn `docs/plans/15-level1-realtime-desktop.md:250-253`) + `$(ls tests/test_level1_*.py → tests.test_level1_*)` +
  `tests.test_private_artifacts tests.test_frontend_contract tests.test_alphabet_ckpt_provenance tests.test_train_alphabet_real_load
  tests.test_alphabet_deployed_v6 tests.test_private_files_kaggle` (module chưa có ở bước sớm thì bỏ, ghi rõ) — gọi chung là AC-1.

**AC-0 Phạm vi/quy trình.** Mỗi bước 1 commit `^15: L13-`; file nằm trong §10; `git diff --numstat <M0>..HEAD -- tests/`: cột xóa = 0 với mọi file
test có sẵn TRỪ đúng các dòng E1/E2/E3 (§5.4); không `skip` mới; `backend/main.py`, `realtime_demo.py`, `configs/level1_realtime.json`,
`configs/level1_demo_classifier*.json`, `src/data/alphabet_preprocessing.py`, `src/inference/fingerspelling_compose.py`, `README.md`, file kế hoạch
11/13/14, `reports/alphabet_deploy_2026-09-27/`, `reports/private_archive_*` KHÔNG đổi (`git diff --stat <M0>..HEAD -- <các đường dẫn>` rỗng);
`checkpoints/alphabet_best.pt` sha trước = sau = v6 (M0).
**AC-1 Hồi quy.** Mỗi bước: mọi test có ở M0 cùng trạng thái hoặc tốt hơn; test mới OK. Sau V1: 0 FAIL/ERROR trên AC-1 (ngoại lệ duy nhất: test chập chờn
đã biết `test_reset_segments_and_graphs` theo luật 3 lần chạy của §5 gốc; skip chỉ khi thiếu dữ liệu/checkpoint, có tên file). Guard chính
`[DoD7-guard] known=9 allowed=36`.

Giao diện (`tests/test_level1_display.py`, `tests/test_level1_demo.py` thêm lớp mới):
- AC-U1 `fit_layout` (cam 640×480, panel 200): cửa sổ 1280×1360 ⇒ scale 2.0; 1920×1080 ⇒ content_h == 1080 (±1), x0 == (1920 − content_w)//2 (±1),
  y0 == 0; 600×2000 ⇒ content_w == 600, căn giữa dọc; (-1,-1,-1,-1), (0,0), None ⇒ scale 1, kích thước tự nhiên. Lưới cửa sổ 200..4000 bước 175 × 2 chiều:
  nội dung nằm trong cửa sổ, chạm ≥ 1 cặp cạnh đối (±1 px), tỉ lệ khung lệch ≤ 1%.
- AC-U2 `render_to_window`: shape == (win_h, win_w, 3); điểm ngoài vùng nội dung == 0; vùng camera == `cv2.resize(view, …)` (array_equal); ở cửa sổ =
  kích thước tự nhiên: ảnh BẰNG HỆT `Hud.compose(view, …)` cùng đầu vào.
- AC-U3 scale 2: cỡ font panel == round(font_size × 2); chiều cao panel = 2× (±2 px mỗi dòng); panel không dựng lại khi chỉ dòng thống kê đổi (đếm số lần build).
- AC-U4 `TestLatencyAcL` + mọi test cửa sổ cũ xanh KHÔNG sửa (dự phòng khi `getWindowImageRect` lỗi); test mới: recorder patch thêm
  `getWindowImageRect → (0,0,1920,1080)` ⇒ mọi ảnh `imshow` có shape (1080, 1920, 3).
- AC-U5 `display_cost.json` (chạy clip D2 `--pace realtime` chế độ cửa sổ với recorder như `TestLatencyAcL`, 2 lần: cửa sổ tự nhiên và 1920×1080, cùng
  tiến trình): gate DC1 p50 `frame_total`(1080p) ≤ 1.25 × p50 `frame_total`(tự nhiên). Trượt ⇒ DỪNG, báo planner.
- AC-U6 E3 (`tests.test_level1_equivalence`) xanh không sửa; phím `f` ghi sự kiện `fullscreen` và `setWindowProperty` ném `cv2.error` không làm app dừng;
  `--no-display-mirror` ⇒ False; `effective_argv([])` vẫn bật mirror.

Cử chỉ (`tests/test_level1_gestures.py`, `tests/test_level1_gesture_check.py`; dữ liệu tổng hợp có docstring "chuỗi tạo có kiểm soát để kiểm logic"):
- AC-G1 loader: thiếu/thừa khóa, thiếu source/reason, source ≠ design, giá trị ≤ 0, tỉ lệ > 1, strokes < 1 ⇒ ValueError; file commit nạp được.
- AC-G2 space: xòe + yên đủ `hold − 1 khung` ⇒ 0; ≥ hold ⇒ đúng 1; giữ tiếp ⇒ vẫn 1; lỗi 1 khung giữa chừng ⇒ vẫn phát; lỗi 2 khung liên tiếp ⇒ đếm lại;
  xòe nhưng `still=False` ⇒ 0; tư thế khác > rearm rồi xòe lại ⇒ phát lần 2; mất tay ⇒ re-arm.
- AC-G3 vẫy: 1 nét biên độ lớn ⇒ 0 (cùng chuỗi qua `BackspaceGestureTracker` cũ ⇒ 1 — ghi khác biệt); 2 nét ≥ A trong cửa sổ ⇒ 1; 2 nét 0.9·A ⇒ 0; 2 nét
  trải > window ⇒ 0; dọc/ngang > 0.5 ⇒ 0; tỉ lệ phẳng 0.85 ⇒ 0; vẫy tiếp sau khi phát ⇒ không phát lần 2 tới khi hết tay phẳng + cooldown; mất tay giữa
  chừng ⇒ đếm lại; cùng chuỗi thu nhỏ 0.5 lần hoặc lật x ⇒ cùng kết quả.
- AC-G4 đường cũ bằng hệt: `BackspaceGestureTracker()` có thuộc tính == giá trị `legacy_flick_*`; `is_flat_hand_backspace(p) ==
  is_flat_hand_backspace(p, 0.5, 1.05)` trên mọi khung có tay của 10 clip hauuto cố định (skip nếu thiếu dữ liệu); test cũ `tests/test_level1_core.py:957+`,
  `tests/test_level1_demo.py:2177-2318, 2532-2536` xanh không sửa.
- AC-G5 guard: `tests.test_level1_guard` xanh với 3 file mới trong danh sách; `grep -rnE "GESTURE_BACKSPACE_(COOLDOWN|WINDOW|MIN_DX|MIN_SPEED|FLASH)" src/`
  = 0 dòng; guard chính known=9 allowed=36; không có tên mới chứa giá trị số gõ tay trong khối cử chỉ của `src/`.
- AC-G6 app: không `--gesture-config` ⇒ khóa JSON + sự kiện của các test cũ không đổi; có cờ ⇒ JSON `gestures` có sha config; `effective_argv([])` chứa
  `--gesture-config configs/level1_gestures.json`; app và script dùng cùng `GestureEngine` (test kiểm script import từ `src.inference.level1_gestures`).
- AC-G7 `gesture_false_trigger.json` sinh tại commit sạch (`code_dirty false`), đủ 3 nguồn; GF1 ≤ 0.005, GF2 ≤ 0.010 trên `raw` và `smoothed`; test tính lại
  tỉ lệ từ số đếm trong JSON khớp `rates`/`pass`; script trên manifest giả (tmp) đếm đúng; thiếu nguồn ⇒ lỗi.
- AC-G8 (sau việc người dùng) `gesture_sensitivity.json`: GT1 ≥ 10/12, GT2 ≥ 10/12 (đường `smoothed`).

Unikey (`tests/test_level1_unikey.py`):
- AC-K1 mọi dòng §4.3: `fusion_target` và `Level1Speller` (qua `on_result` VÀ `on_label`) cho cùng tokens + text như bảng.
- AC-K2 `tests/test_level1_core.py:917-954`, `tests/test_level1_lan_sua_12.py:92-131` xanh không sửa.
- AC-K3 mọi lần ghép ⇒ sự kiện `source "fusion"` có `prediction` (== nhãn model), `confidence`, `replaced`, `rule`, `index`; quét mọi sự kiện của bảng §4.3 +
  một lần chạy app trên clip D2: không sự kiện `source "model"` nào có `token` ≠ dự đoán của model.
- AC-K4 `grep -c "DIACRITIC_FUSION = {" src/` tổng = 1 (ở `level1_segmenter.py`).
- AC-K5 200 chuỗi dự đoán ngẫu nhiên (seed cố định, 34 lớp + dấu cách): sau mỗi thao tác `text == compose(tokens)["text"]`; một lần ghép không đổi số token dấu thanh.
- AC-K6 `unikey_mode=False` ⇒ hành vi như M0 (test cũ).

Model v6 (`tests/test_alphabet_deployed_v6.py`, `tests/test_train_alphabet_real_load.py`):
- AC-V1 `deployment.json` sinh tại commit sạch; `checkpoints.deployed.sha256` == sha file trên máy và bắt đầu `160e0c68`; `trained_on` == checkpoint; số
  `evaluation` == giá trị JSON nguồn (tính lại bằng mã).
- AC-V2 4 test đỏ của review A1 + `test_frontend_contract` xanh (test 1, 3 và `test_frontend_contract` KHÔNG sửa).
- AC-V3 backend == offline v6 trên mẫu §5.2 (prediction ==, |Δconf| ≤ 1e-4, top-3 ==; lật gương bằng nhau); `load(dir)` mặc định chỉ trả `sample_id` có trong
  manifest; `main()` gọi `load(..., slice_compound=True)` cả 2 lần (patch `load` ghi kwargs).
- AC-V4 numstat: `tests/test_status_privacy.py` −1/+1 (dòng 29), `tests/test_fingerspelling_deployed.py` xóa ≤ 4 dòng (2, 31, 155, 174), `tests/test_level1_guard.py`
  theo E3; mọi file test có sẵn khác 0 dòng xóa.
- AC-V5 `kaggle_checkpoint_manifest.json`: `is_private true`, hai nguồn true, sha v6 == `deployment.json`, bước verify đã tải về và khớp.

Dữ liệu (`tests/test_private_files_kaggle.py`, `tests/test_level1_private_data.py`):
- AC-D1 api giả: staging trong repo ⇒ exit 2; `--manifest-out` dưới `reports/private_archive_*` ⇒ exit 2; metadata `isPrivate true`; một nguồn private không True ⇒ exit 4;
  sha lệch ⇒ exit 3; `materialize` dựng đúng cây, thiếu/thừa/sai ⇒ exit 3; không in credential.
- AC-D2 manifest user1: số file == số mục `git ls-files data/collected_targeted` tại commit trước khi gỡ (từ lệnh), sha từng file == sổ sha đã chép Drive; hai nguồn
  private true; `git ls-files data/collected_targeted data/collected_gestures` == đúng 2 file `.gitignore`; `git check-ignore -q` = 0 cho
  `data/collected_targeted/manifest.csv`, `…/user1/x.npz`, `data/collected_gestures/manifest.csv`, `…/x.npz`, `…/x.mp4`; file user1 trên đĩa còn nguyên sha;
  `fd5ceea` là tổ tiên của HEAD (không viết lại lịch sử); `tests.test_private_artifacts` 8/8 xanh KHÔNG sửa.
- AC-D3 kernel: không còn `--extra-data-dir data/collected_targeted`; có lời gọi `materialize` với manifest đã commit; `kernel-metadata.json` có slug; không đẩy kernel.

Còn lại:
- AC-R1 `preset_agreement.json` sinh tại commit sạch, có sha checkpoint v6, đủ phần A/B, cờ `notify_user` = (bất kỳ tỉ lệ < 0.95); test logic trên dữ liệu giả + tính lại cờ từ JSON.
- AC-R2 docstring luật 7 nhắc `is_variant_of`; test AC2 qua `main()` (Level1App patch) xanh; test `filled == {}` xanh.
- AC-R3 `docs/level1_desktop.md` có mục Giới hạn gồm: v6 đã train trên user1 (thử của người dùng không phải "chưa thấy"); QIPEDC top-1/top-3 v6 vs v5 (đọc từ
  `deployment.json`/`retrain_summary_*.json`, ghi đường khóa); gate G1/G5 trượt; số đồng thuận preset; GF/GT; giới hạn Unikey F3/F5; rev8/rev9 chỉnh theo phiên webcam;
  `trained_on.source` "hauuto" thiếu user1; README chưa cập nhật. Mọi số có đường JSON; reviewer đối chiếu từng số.

## 10. Phạm vi file

```scope
src/inference/level1_display.py
src/inference/level1_gestures.py
src/inference/level1_unikey.py
src/inference/level1_core.py
src/inference/level1_segmenter.py
level1_demo.py
configs/level1_gestures.json
scripts/level1_gesture_check.py
scripts/level1_preset_agreement.py
scripts/alphabet_deploy_record.py
scripts/private_files_kaggle.py
scripts/hand_live_check.py
scripts/train_alphabet_real.py
kaggle/vsl-train-alphabet/train_alphabet_kernel.py
kaggle/vsl-train-alphabet/kernel-metadata.json
tests/test_level1_*.py
tests/test_alphabet_deployed_v6.py
tests/test_train_alphabet_real_load.py
tests/test_private_files_kaggle.py
tests/test_status_privacy.py
tests/test_fingerspelling_deployed.py
reports/level1_realtime_2026-10-08/
reports/alphabet_deploy_2026-10-08/
reports/private_data_2026-10-08/
data/collected_targeted/
data/collected_gestures/.gitignore
.gitignore
docs/level1_desktop.md
docs/data_registry.md
docs/plans/15-progress.md
docs/plans/15-lan-sua-13.md
docs/progress_log.md
```
`src/inference/level1_segmenter.py`: CHỈ docstring luật 7. `.gitignore`: CHỈ khôi phục byte-exact bản `fd5ceea^` (§6.2). `data/collected_targeted/`: CHỈ
`git rm --cached` + file `.gitignore` con. `tests/test_status_privacy.py`, `tests/test_fingerspelling_deployed.py`: CHỈ dòng E1/E2.
CẤM: `backend/main.py`, `realtime_demo.py`, `README.md`, `configs/level1_realtime.json`, `configs/level1_demo_classifier*.json`, `src/data/`,
`src/inference/fingerspelling_compose.py`, `src/inference/hand_live.py`, `tests/test_backend_source_guard.py`, `scripts/archive_private_kaggle.py`,
`scripts/archive_step4_kaggle.py`, `reports/private_archive_*`, `reports/alphabet_deploy_2026-09-27/`, `docs/plans/11-*`, `docs/plans/13-*`, `docs/plans/14-*`,
`checkpoints/` (không commit; chỉ đọc).

## 11. Rủi ro dữ liệu/ML

- Lệch train↔realtime GIỮ theo Q1: làm mượt + conf 0.55 đổi đầu vào model so với train (0.5, thô) — R1 đo, chưa có số; cử chỉ trong preset chạy trên
  landmark làm mượt ⇒ gate GF đo cả `raw` và `smoothed`.
- `scripts/collect_targeted_signs.py` trích landmark với conf 0.35 (`:119`) ≠ 0.5 của train hauuto ≠ 0.55 của preset: dữ liệu user1 dùng train v4–v6 lệch nhẹ
  tiền xử lý (thuộc phần B review; ghi Giới hạn, không sửa ở đây). Clip cử chỉ quay bằng cùng script ⇒ cùng lệch với đường app.
- Rò rỉ/“chưa thấy”: v6 train trên user1 + hauuto ⇒ mọi thử webcam của người dùng và R1 trên hauuto/user1 KHÔNG là dữ liệu chưa thấy; QIPEDC (46 clip, ~1–3/lớp)
  là tập duy nhất chưa thấy ⇒ khoảng tin cậy rộng.
- Tham số cử chỉ là giá trị thiết kế, đặt trước khi đo; tập âm tính là clip train (không dùng để chỉnh). Nếu GF trượt và planner chỉnh lại ⇒ các clip này thành
  dữ liệu chỉnh, phải ghi "đã dùng để chỉnh" và cần tập kiểm mới (clip người dùng mới).
- Cỡ mẫu: GT n = 12/cử chỉ (một người, một máy) — kiểm khói, không phải tỉ lệ thật.
- `trained_on.source = "hauuto"` trong checkpoint v6 thiếu user1 (endpoint status báo thiếu) — ghi hồ sơ + Giới hạn; sửa = train lại (ngoài phạm vi).
- Kernel đổi đường dữ liệu chưa chạy thật trên Kaggle (không đẩy) — lần train tới phải kiểm `materialize` ở log kernel.
- Lịch sử git công khai vẫn chứa 84 npz user1 (từ `fd5ceea`).
- `.gitignore` gốc: nếu `fd5ceea` có thay đổi ngữ nghĩa khác 2 dòng phủ định ⇒ DỪNG (không đoán).
- cv2 GUI trên máy không màn hình (cloud) có thể thiếu `getWindowImageRect` ⇒ dự phòng về đường cũ (AC-U4).

## 12. Điểm dừng

- CẦN NGƯỜI DÙNG (không chặn): quay 24 clip cử chỉ (§3.4) trước G5; xem lại Q1 nếu R1 bật `notify_user`; quyết định riêng nếu muốn xóa user1 khỏi lịch sử git
  (không hoàn tác, ngoài kế hoạch); README (người dùng commit/stash thay đổi của mình trước nếu muốn cập nhật README).
- Không đổi model mặc định ngoài Q3 (v6 đã đặt); không đụng thay đổi chưa commit của người dùng (`README.md`, 3 file ` D`); không viết lại lịch sử; không đẩy kernel.
- Dataset Kaggle mới (2 cái) đều PRIVATE, kiểm 2 nguồn; một nguồn không xác nhận private ⇒ exit 4, DỪNG, báo người dùng.
- Luật DỪNG khác (báo planner, không tự sửa tiêu chí): GF1/GF2/GT1/GT2/DC1 trượt; test cũ đỏ ngoài danh sách ngoại lệ; `_alphabet_meta["checkpoint"]` không phải
  basename; diff `.gitignore` không như §6.2; sha user1 lệch sổ Drive; sha checkpoint không bắt đầu `160e0c68`.

---
CON TRỎ (orchestrator chèn vào ĐẦU `docs/plans/15-lan-sua-12.md`):
`> LẦN SỬA 13 (2026-10-08): xem docs/plans/15-lan-sua-13.md — giao diện co giãn/toàn màn hình, cử chỉ cố ý (gate kích hoạt nhầm), Unikey đúng chính tả + nguồn "fusion", model v6 + ngoại lệ test E1–E3, gỡ dữ liệu user1 khỏi git, đo đồng thuận preset; có hiệu lực thay phần mâu thuẫn của lần sửa này.`
