# Kế hoạch 15 — LẦN SỬA 13c (bổ sung cho `15-lan-sua-13.md` + `13a` + `13b`): sửa U2d, gom THẤP của U2a–U2d, X1 + thăm dò cửa sổ thật

CẦN NGƯỜI DÙNG (KHÔNG chặn bước nào của 13c, không chặn G1): một lần nhìn cửa sổ demo thật (mục 7, việc VU). Mọi bước còn lại tự chạy được.

Ngày: 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `93abb08`. Đầu vào: `docs/reviews/15-l13-u2d-review.md` (CHANGES_REQUESTED: TB-1, TB-2,
THẤP-1..7), THẤP còn mở của `15-l13-u2a-review.md`, `15-l13-u2b-review.md`, `15-l13-u2c-review.md` (vòng 1 và vòng 2), `15-lan-sua-13b.md` §4–§7,
quyết định người dùng trong STATE (2026-10-09 14:07: tiêu đề `"VSLT Level 1 (f: toan man hinh)"`, đã làm ở `6144970`, KHÔNG đổi lại).

Hiệu lực: THAY phần "U2d" của 13b §4 bằng C1 + C2 (§4). THÊM T1, T2 (chỉ thêm test), XW (cầu nối, không commit mã). AC-X1 của 13b giữ NGUYÊN
VĂN, chỉ gộp lịch chạy vào XW. KHÔNG đổi: gate DC1 (ngưỡng 1.25, định nghĩa p50 `frame_total`(1920×1080) ≤ 1.25 × p50 `frame_total`(tự nhiên), 2 lần
cùng tiến trình, tự nhiên trước), AC-U1..U9b, AC-0/AC-1, E1–E4. Không hạ tiêu chí nào. Phần thêm vào DC1 chỉ là ĐIỀU KIỆN HỢP LỆ dữ liệu theo hướng
fail-closed (thiếu dữ liệu thì KHÔNG pass), nghĩa là chặt hơn, không lỏng hơn.

## 1. Mục tiêu và DoD

Đóng U2 của lần sửa 13 (giao diện demo, hạng mục 5): (a) harness đo DC1 không còn báo pass khi không có dữ liệu, ghi đường vẽ ĐO ĐƯỢC chứ không
hard-code; (b) khóa bằng test các lỗ đột biến sống còn lại của U2a–U2c, chỉ thêm test, không sửa app; (c) chạy chẩn đoán X1 và thăm dò cửa sổ thật
trước V1. DoD phục vụ: hạng mục 5 (giao diện demo), quy tắc số liệu (JSON có lệnh, commit và tái lập được), không lệch train ↔ realtime
(13c không chạm `level1_demo.py`, cũng không chạm `src/`).

## 2. Hiện trạng (HEAD `93abb08`)

- `scripts/level1_display_cost.py` (commit `fddba5a`):
  - `summarize_frame_total` `:39-48`: chuỗi rỗng ⇒ `n 0, p50 0.0`.
  - `compute_ratio` `:51-55`: `p50_natural <= 0` ⇒ `0.0`. `dc1_gate` `:58-64`: `ratio <= 1.25` ⇒ pass. Ghép lại thì gate pass dù không có dữ liệu (TB-1).
  - `build_report` `:67-113`: `path` hard-code `:81`, `:86`. `NOTE_TEXT` `:28-31` khẳng định lần natural đi `Hud.compose`, chưa đo (TB-2).
  - `_DisplayCostRecorder` `:116-156`: rect natural = shape `imshow` gần nhất, nên khi panel đổi cao thì khung đi `render_to_window`.
  - `measure` `:159-182`: `os.chdir(ROOT)` trước `run()`, nên `--clip` tương đối được hiểu theo gốc repo (THẤP-4).
  - `main` `:209-245`: `command` chứa `sys.executable` tuyệt đối (THẤP-6); luôn `return 0` (THẤP-5).
- `tests/test_level1_display_cost.py` (U2d, CHƯA được APPROVE): `:53` khóa `compute_ratio(0.0, 12.0) == 0.0`; `:110`, `:117` khóa chuỗi `path`;
  `:192-219` khóa mã thoát 0 khi gate trượt; recorder test `:133-150` chỉ có ca panel không đổi cao (THẤP-7).
- `reports/level1_realtime_2026-10-08/display_cost.json` (`abdcf39`): ratio 1.007, n=35/34, đo khi máy tải nặng; không đại diện cho chi phí vẽ (review U2d mục 8).
- `level1_demo.py`:
  - `_window_image` `:1328-1350`: nhánh dự phòng `:1349`, nhánh co giãn `:1350`.
  - phím f `:1102-1111`; `Hud._fonts_at` `:516-528`.
  - chặng thời gian: `mediapipe` `:1271`, `hud` `:1315`, `frame_total` `:1320`.
  - 13c KHÔNG sửa file này.
- `src/inference/level1_display.py` `draw_panel_overlays` `:122-137`: nét `max(STATS_THICKNESS, round(STATS_THICKNESS*scale))` `:133`, đáy `scaled_px(STATS_BOTTOM_MARGIN)` `:135`.
  13c KHÔNG sửa file này.
- `tests/test_level1_demo.py`: `_ScaledWindowRecorder` `:3261`, `_FullscreenRecorder` `:3446` (có `keys`, `set_props`, `resized`), `TestFullscreenU2c` `:3486`,
  `TestHudFontLruU2c` `:3581`. Các lớp này dùng lại được, không cần sửa.
- Đột biến còn sống:
  - U2a: rA (nét chữ thống kê không co giãn), rB (lề đáy không co giãn).
  - U2b: m5 (nhánh dự phòng mất thanh hold), m6 (ảnh lật vào `render_to_window`).
  - U2c: m4 (FIFO thay LRU), m5 (tắt toàn màn hình vẫn gửi `WINDOW_FULLSCREEN`), m6 (bỏ `window_sized = False`).

## 3. Quyết định của planner

### 3.1 Review U2d
| Mục | Quyết định |
|---|---|
| TB-1 | **Sửa (C1), theo hướng fail-closed.** `compute_ratio` ném `ValueError` khi `p50_natural` ≤ 0 hoặc không hữu hạn. Thêm điều kiện hợp lệ ở mỗi lần đo, áp TRƯỚC gate: `n_frames ≥ MIN_FRAMES = 10`; `p50` hữu hạn và > 0; `path_counts` tổng = `n_imshow` = `n_frames`. Vi phạm bất kỳ điều kiện nào thì `gate.pass = false`, ghi `gate.reason`, mã thoát 3. Ngưỡng 1.25 và công thức ratio giữ nguyên. Lý do chọn `MIN_FRAMES = 10`: p50 trên dưới 10 giá trị không mang nghĩa. Ngưỡng này đặt trước khi đo; các lần đo cũ có n = 34–74 nên không phải đặt theo kết quả. |
| TB-2 | **Sửa (C1).** Bỏ khóa `path` hard-code. Mỗi lần đo ghi `path_counts {"Hud.compose", "render_to_window"}`, đếm bằng `mock.patch.object` bọc hàm gốc (hàm gốc vẫn chạy), cùng với `n_imshow`. Thêm số THÔNG TIN, không vào gate: `stage_p50_ms {"hud", "mediapipe"}` mỗi lần đo, và `info.hud_p50_delta_ms`. Note bỏ câu khẳng định "natural = Hud.compose". |
| Đo lại | **Có (C2).** Cầu nối chạy 3 lần (3 tiến trình nối tiếp nhau, không chạy song song việc nặng khác) tại commit code sạch của C1. Commit JSON của LẦN 1, quy tắc đặt trước (không chọn lần đẹp). Lần 2 và 3 chỉ ghi vào progress. Ba lần phải cùng kết luận pass và cùng mã thoát 0. Việc này xử lý THẤP-3 (1 lượt, không lặp) mà không đổi định nghĩa DC1. |
| Câu hỏi "số hud là thông tin hay Giới hạn R2" | **Cả hai.** p50 `hud` vào JSON làm số thông tin. R2 thêm câu Giới hạn (§8), số lấy từ JSON C2 kèm đường khóa. KHÔNG trích "ratio 1.007" như chi phí hiển thị. |
| THẤP-1 (thiếu log AC-U2P) | C1 bắt buộc có `l13c_c1_green_level1_all.log` và ghi số AC-U9b vào progress. |
| THẤP-2 (mtime ghi sai) | Ghi nhận. Từ nay progress chép mtime bằng `stat -c '%y'`, không gõ tay. |
| THẤP-3 | Xử lý bằng 3 lần đo của C2 và câu Giới hạn R2. |
| THẤP-4 | **Sửa (C1).** `--clip` tương đối được hiểu theo cwd của người gọi (`abspath` trước mọi `chdir`). Clip không tồn tại ⇒ mã thoát 2, không ghi JSON, không gọi `measure`. |
| THẤP-5 | **Sửa (C1).** Mã thoát: 0 = hợp lệ và pass; 1 = hợp lệ nhưng DC1 trượt; 2 = đối số sai hoặc thiếu clip (không ghi JSON); 3 = dữ liệu không hợp lệ (vẫn ghi JSON, có `reason`). Ghi trong docstring. |
| THẤP-6 | **Sửa (C1).** `command` không chứa đường dẫn tuyệt đối. Trình thông dịch nằm trong ROOT thì ghi `relpath` dạng posix (vd. `.venv/Scripts/python.exe`), nằm ngoài ROOT thì ghi `basename`. `clip` nằm trong ROOT thì ghi `relpath` posix, nằm ngoài thì ghi `abspath`. |
| THẤP-7 | **Sửa (C1).** Thêm test `measure()` với module app giả: đếm đúng đường vẽ, gồm ca đổi đường giữa chừng. |

### 3.2 THẤP U2a–U2c
| Nguồn | Mục | Quyết định |
|---|---|---|
| U2a THẤP-1 | lát cắt có thể rỗng; chưa khẳng định `L.scale` | **T1**: thêm test điều kiện tiền đề (chỉ thêm). |
| U2a THẤP-2 | rA, rB sống | **T1**: oracle chính xác của dòng thống kê lấy từ tham số hợp đồng (13b §2); rA, rB phải ĐỎ. |
| U2a THẤP-3 | `rows.max()` gặp `ValueError` | Ghi nhận, không sửa: vẫn đỏ, chỉ thông điệp kém. Sửa thì phải xóa dòng của test đã APPROVE. |
| U2a THẤP-4 | quy trình, dòng progress lỗi thời | Orchestrator dọn dòng "ĐANG LÀM" trong progress khi ghi 13c. |
| U2b THẤP-1/2 | m5, m6 sống | **T2**: test gọi thẳng `_window_image` với đầu vào do test tự đặt; m5, m6 phải ĐỎ. |
| U2b THẤP-3 | ảnh camera đổi cỡ hoặc dịch khi panel đổi cao | KHÔNG sửa app trong 13c: mọi cách sửa đều đổi UX (giữ chỗ panel cố định thì đổi ảnh so với `Hud.compose` của AC-U2; còn `resizeWindow` lại thì cả cửa sổ giật như AUTOSIZE cũ). XW đo tần suất khung đổi đường. **VU** (người dùng) nhìn và quyết. Ghi Giới hạn R2. |
| U2b THẤP-4 | chưa kiểm cửa sổ thật | **XW** (cầu nối thăm dò cửa sổ thật, tự động). VU chỉ nhìn bằng mắt. |
| U2b THẤP-5 | natural đi `Hud.compose` | Đã chấp nhận ở U2b; nay được ĐO bằng `path_counts` (C1). |
| U2c THẤP-1 | m5 sống (giá trị thuộc tính) | **T2**. |
| U2c THẤP-2 | m4 (FIFO), m6 sống | **T2**. |
| U2c THẤP-3 | `setWindowProperty` lỗi vẫn ghi `on: true`; `--fullscreen` lỗi thì cửa sổ giữ cỡ mặc định | Ghi Giới hạn R2. Không sửa app: AC-U6 chỉ đòi "không dừng". Muốn sửa thì làm bước riêng sau VU. |
| U2c THẤP-4 | sổ agy nằm trong commit mã | Quy tắc cho 13c: `docs/agy_usage_ledger.csv` do orchestrator commit RIÊNG, không gộp vào commit C1/T1/T2. |
| U2c THẤP-5 | thiếu log impact, trích sai nguồn | Quy tắc cho 13c: mỗi bước có `_work/_plan15_l13/l13c_<bước>_impact.log` và `..._detect.log`. Progress chỉ trích kế hoạch bằng `file:dòng`, lời giao của cầu nối thì ghi là "lời giao". |
| U2c THẤP-6 | thoát toàn màn hình thì về cỡ tự nhiên | Ghi Giới hạn R2; VU nhìn. |
| U2c vòng 2 | chú thích `tests/test_level1_demo.py:3646` | Không sửa: sửa là thêm dòng xóa vào file test có sẵn, vi phạm AC-0. Ghi nhận. |

### 3.3 X1
Giữ AC-X1 của 13b nguyên văn (luật 8 lần chạy, 0/8 OK ⇒ DỪNG). Gộp lịch chạy với thăm dò cửa sổ thật thành một bước cầu nối XW, không có commit
mã. Phải chạy sau C2, KHÔNG chạy song song với bất kỳ lần đo DC1 nào vì sẽ làm nhiễu thời gian.

## 4. Chia việc (mỗi bước có mã là 1 commit; sau MỖI bước: cầu nối xác minh rồi vslt-reviewer, sau đó mới giao bước kế)

| Bước | Nội dung | Phụ thuộc | Giờ | Coder | Lý do |
|---|---|---|---|---|---|
| C1 | Sửa `scripts/level1_display_cost.py` + `tests/test_level1_display_cost.py` (AC-C1). Commit `15: L13-U2d sửa TB-1/TB-2 …`. | — | 1,5 | `vslt-coder-claude` | Harness đánh giá có gate. Lần trước agy làm ra fail-open và nhãn hard-code; việc nhỏ nhưng cần chắc. Không chạm app. |
| C2 | Cầu nối chạy đo 3 lần (AC-C2), commit JSON lần 1: `15: L13-U2d báo cáo display_cost.json (đo lại 13c)`. Sau đó vslt-reviewer review U2d vòng 2 (C1 + C2 cùng lúc). | C1 | 0,5 | cầu nối/orchestrator | Chỉ chạy lệnh. |
| XW | X1 (AC-X1 13b) + thăm dò cửa sổ thật W1 (AC-W1). Ghi vào progress, commit docs `15: L13-XW …` (chỉ `docs/plans/15-progress.md`). | C2 xong (không chạy song song lần đo) | 0,5 | cầu nối/orchestrator | Chỉ chạy lệnh; script thăm dò nằm ở `_work/`, không commit. |
| T1 | CHỈ THÊM test vào `tests/test_level1_display.py` (AC-T1). Cầu nối chạy đột biến (AC-T1m). Commit `15: L13-U2t1 …`. | review U2d vòng 2 APPROVE | 0,75 | `vslt-coder` (agy Gemini, effort ≥ high) | Thuần test pixel, đặc tả đầy đủ, nhỏ. Nếu agy hết giờ 2 lần thì giao `vslt-coder-claude`, giữ nguyên AC. |
| T2 | CHỈ THÊM test vào `tests/test_level1_demo.py` (AC-T2). Cầu nối chạy đột biến (AC-T2m). Commit `15: L13-U2t2 …`. | T1 APPROVE | 1,0 | `vslt-coder` (agy Gemini, effort ≥ high) | Thuần test, dùng lại recorder có sẵn. Lùi về Claude như T1. |
| VU | Người dùng nhìn cửa sổ demo thật (mục 7). | — (không chặn) | — | NGƯỜI DÙNG | Quyết định UX. |

Thứ tự: C1 → C2 → (review U2d v2) → XW → T1 → T2 → G1 (`15-lan-sua-13.md` §8 #4 trở đi, không đổi). XW chạy được trong lúc chờ review U2d
v2, miễn không trùng lúc reviewer đang đo DC1. Khi thiếu thời gian, T1/T2 được dời ra sau K2, nhưng PHẢI xong trước R2. C1, C2, XW không được dời.
Tổng thời gian coder ≈ 3,25 h (Claude 1,5 h; agy 1,75 h). Quy ước chung giữ `15-lan-sua-13.md` §8: chạy impact trước khi sửa symbol có sẵn
(`compute_ratio`, `build_report`, `measure`, `main`, `_DisplayCostRecorder`), chạy detect-changes trước commit, dùng `git commit -- <đường dẫn cụ thể>`,
KHÔNG stage `README.md` và 3 file ` D` của người dùng.

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

Ký hiệu: `PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python`; log ở `_work/_plan15_l13/`. Bộ hồi quy `LALL` =
`PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard`.

### AC-C1 (C1 — harness DC1)
JSON (khóa bắt buộc; có thể có thêm khóa khác):
```
command: str        # không chứa ROOT tuyệt đối; có "scripts/level1_display_cost.py" và các đối số
commit: str, code_dirty: bool, clip: str (relpath posix nếu trong ROOT), min_frames: 10
natural / window_1080p: {n_frames:int, p50_ms:float, p90_ms:float, n_imshow:int,
                          path_counts:{"Hud.compose":int, "render_to_window":int},
                          stage_p50_ms:{"hud":float|null, "mediapipe":float|null}}
ratio_p50: float|null
gate: {name:"DC1", threshold:1.25, pass:bool, reason:str|null}
info: {hud_p50_delta_ms: float|null, in_gate: false}
note: str  # có "imshow vá", "không cửa sổ thật", "không đo chi phí vẽ cửa sổ HĐH", "path_counts"; KHÔNG có câu "natural đo đường Hud.compose"
python: str, cv2: str
```
KHÔNG còn khóa `path` trong `natural` / `window_1080p`. Không có số nào trong JSON được gõ tay; mọi số đều tính từ dữ liệu đo.

`measure(rect, clip, app_module=None)`: `app_module=None` thì import `level1_demo`. Hàm trả dict có `frame_total`, `hud`, `mediapipe` (list ms lấy từ
`app.times.values`), `n_imshow`, `path_counts`. Việc đếm bọc hàm gốc bằng `mock.patch.object(app_module.Hud, "compose", …)` và
`mock.patch.object(app_module, "render_to_window", …)`, giá trị trả về của hàm gốc đi tiếp tới `imshow`. Không dùng mẫu cấm của AC-U9.

Test (thêm hoặc sửa trong `tests/test_level1_display_cost.py`; giữ docstring "chuỗi tạo có kiểm soát để kiểm logic"):
1. Biên gate: `dc1_gate(1.25)` pass; `dc1_gate(1.2501)` fail (GIỮ). `dc1_gate(float("nan"))` và `dc1_gate(None)` ⇒ `pass False`.
2. `compute_ratio(0.0, 12.0)`, `compute_ratio(-1.0, 12.0)`, `compute_ratio(float("nan"), 12.0)` ⇒ `ValueError`. `compute_ratio(10.0, 12.5) == 1.25` (GIỮ). Thay `:53`.
3. `build_report` với dữ liệu thiếu ⇒ `gate.pass False`, `reason` khác rỗng, có `ratio_p50 is None` khi p50 không hợp lệ. Các ca:
   - natural `n=0, p50=0`;
   - 1080p `n=0`;
   - cả hai `n=0`;
   - `n=9` (dưới `min_frames`);
   - `sum(path_counts) != n_imshow`;
   - `n_imshow != n_frames`.
   Ca hợp lệ `n=10`, ratio 1.2 ⇒ `pass True`, `reason None`. Ca hợp lệ ratio 1.3 ⇒ `pass False`, `reason None`.
4. `build_report`: không có khóa `path`; `path_counts`, `stage_p50_ms`, `n_imshow` được chép đúng; `info.in_gate is False`; `info.hud_p50_delta_ms` == hud(1080) − hud(natural);
   note đúng yêu cầu ở trên.
5. CLI (vá `measure`):
   - pass ⇒ `ret 0`, có JSON;
   - ratio 2.0 ⇒ `ret 1`, có JSON, `pass False`;
   - `n=0` ⇒ `ret 3`, có JSON, `pass False`, `reason`;
   - `--clip` không tồn tại ⇒ `ret 2`, KHÔNG có JSON, `measure` không được gọi.
   Bỏ `test_cli_exit_zero_even_when_gate_fails` (đổi thành ca `ret 1`).
6. `--clip` tương đối: `chdir` vào thư mục tạm có file `clips/x.mp4` ⇒ `measure` nhận `abspath` theo thư mục tạm. Ca clip nằm trong ROOT (dùng
   `scripts/level1_display_cost.py` làm file có sẵn, không cần dữ liệu) ⇒ JSON `clip == "scripts/level1_display_cost.py"`. Chuỗi JSON không chứa ROOT
   (kiểm cả dạng `\` lẫn `/`), và `command` không chứa ROOT.
7. `measure` với module app giả (`types.SimpleNamespace`/lớp giả có `Level1App`, `build_parser`, `Hud`, `render_to_window`, `cv2`): `run()` giả gọi
   `Hud.compose` 3 lần rồi `render_to_window` 2 lần (đổi đường giữa chừng), mỗi lần `imshow` ảnh do hàm gốc trả về, và ghi thời gian `frame_total`/`hud`/`mediapipe`.
   Kỳ vọng `path_counts == {"Hud.compose": 3, "render_to_window": 2}`, `n_imshow == 5`, ảnh `imshow` là ĐÚNG đối tượng hàm gốc trả về (`is`), list thời gian khớp.
8. Recorder (THẤP-7): sau `resizeWindow(640, 643)` và `imshow` (643, 640) mà panel tự nhiên đổi sang 640×663, rect vẫn là `(0, 0, 640, 643)`, nghĩa là app
   sẽ đi `render_to_window`. Test khẳng định đúng hành vi này của recorder và ghi lý do trong chú thích (giống cửa sổ thật: rect cố định sau lần resize đầu).

Ngoại lệ AC-0/AC-U2P (E-13c, đóng): ĐƯỢC xóa dòng trong `tests/test_level1_display_cost.py` vì file này của U2d, chưa APPROVE, và review đòi sửa. Chỉ
xóa ở: `:53`; `:77-78` cùng input của `:156-164` và `:194-200` (đổi schema); `:110`, `:117` (path); `:192-219` (mã thoát). Mọi kiểm khác của file
giữ nguyên hoặc chặt hơn; reviewer đối chiếu từng dòng `-`. Mọi file test khác: 0 dòng xóa.

Lệnh và kết quả:
- `PY -m unittest tests.test_level1_display_cost -v > l13c_c1_red.log 2>&1` (test mới, mã cũ) ⇒ `FAILED`. Sau đó `… > l13c_c1_green_cost.log` ⇒ `OK`.
  mtime của log đỏ < mtime log xanh, cả hai trên cây làm việc chính; chép mtime bằng `stat -c '%y'`.
- `LALL > l13c_c1_green_level1_all.log 2>&1` ⇒ `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`; ghi số `Ran` thật.
- AC-U9 (lệnh 13b, base `d1a8308`) ⇒ `0`; `git diff --stat 93abb08..HEAD -- level1_demo.py src/` rỗng; AC-U9b (lệnh 13b, base `b0cbcf1`) ⇒ `0`.
- `sha256sum checkpoints/alphabet_best.pt` ⇒ bắt đầu bằng `160e0c68`.
- Commit chỉ gồm 2 file mã/test + `docs/plans/15-progress.md`.

### AC-C2 (C2 — đo lại, cầu nối)
Tại HEAD có `git diff <C1>..HEAD -- scripts/ level1_demo.py src/` rỗng và `git status --porcelain -- scripts level1_demo.py src` rỗng:
1. `PY scripts/level1_display_cost.py --out reports/level1_realtime_2026-10-08/display_cost.json > _work/_plan15_l13/l13c_c2_run1.log 2>&1; echo $?`
2. Tương tự với `--out _work/_plan15_l13/l13c_c2_run2.json` và `--out _work/_plan15_l13/l13c_c2_run3.json`, chạy nối tiếp ngay sau lần 1.

Yêu cầu:
- Cả 3 lần có mã thoát 0 và `gate.pass true`.
- JSON lần 1: `code_dirty false`, `commit` có code giống `<C1>`.
- `window_1080p.path_counts.render_to_window == window_1080p.n_imshow` (lần 1080p đi đường co giãn ở mọi khung).
- `grep -ciE 'users[\\/]+' reports/level1_realtime_2026-10-08/display_cost.json` ⇒ `0`.
- Ghi vào progress cho cả 3 lần: `ratio_p50`, `n_frames`, `path_counts`, `stage_p50_ms`, `info.hud_p50_delta_ms`.
- Commit DUY NHẤT JSON lần 1, không chọn lần khác.

Bất kỳ lần nào có mã thoát khác 0, hoặc 3 lần không cùng kết luận, hoặc `render_to_window` < `n_imshow` ở lần 1080p ⇒ DỪNG, báo planner. Không chạy
thêm để "lấy lần đẹp".

### AC-X1 — giữ nguyên văn `15-lan-sua-13b.md:116-119`.

### AC-W1 (XW — thăm dò cửa sổ thật, cầu nối; thông tin, không phải gate)
Script tạm `_work/_plan15_l13/w1_probe.py` (KHÔNG commit). Script chạy `Level1App` trên clip D2 `--pace realtime` với cửa sổ THẬT: không vá
`imshow`/`namedWindow`/`resizeWindow`/`waitKey`; chỉ bọc `cv2.getWindowImageRect` để ghi lại, và đếm `Hud.compose`/`render_to_window` như C1.
Lệnh: `PY _work/_plan15_l13/w1_probe.py > _work/_plan15_l13/w1_probe.log 2>&1`.

Log phải có:
- kích thước tự nhiên `(w, h + panel_h)` ở khung 1;
- rect ở khung 1, 2, 5;
- tập các rect khác nhau;
- `path_counts`;
- số khung mà kích thước tự nhiên khác khung trước (panel đổi cao);
- tiêu đề thật (`GetWindowTextW`, như probe U2c).

Ghi vào progress. Nếu rect khung 2 khác kích thước tự nhiên khung 1 (viền hoặc DPI) ⇒ ghi Giới hạn R2: "ở cỡ mặc định mọi khung đi `render_to_window`,
scale ≈ 1". Không sửa app trong 13c; planner quyết sau. Máy không có màn hình hoặc phiên đang khóa ⇒ ghi "không chạy được", không chặn.
Cửa sổ chỉ mở trong vài giây, đóng khi hết clip.

### AC-T1 (T1 — chỉ THÊM lớp mới `TestU2OverlaysExactT1` trong `tests/test_level1_display.py`)
Ký hiệu như AC-U7 của 13b §5 (cam 640×480, `panel_h = 200`, panel builder trả nền `BG = (40, 40, 40)`, view `(90, 90, 90)`). Mỗi trường hợp là
một `subTest`, gồm `(W, H) ∈ {(1920, 1080), (1280, 1360)}` cộng ca tự nhiên (`fit_layout(640, 480, 200)`).
- P1 (tiền đề, U2a THẤP-1): `|L.scale − min(W/640, H/680)| ≤ 0.01`; ca tự nhiên `L.scale == 1.0`; `scaled_px(3, s) ≥ 1`, `cw > 0`, `ph > 0`; mọi lát cắt
  dùng trong H1/H2 có `size > 0`.
- S5 (oracle chính xác dòng thống kê, rA/rB). Với `hold 0`, `stats = ["fps 30.0 | hud 1.2ms"]`, dựng
  `E = np.full((ph, cw, 3), BG, uint8)`, rồi
  `cv2.putText(E, line, (int(8*s), ph − int(10*s)), cv2.FONT_HERSHEY_SIMPLEX, 0.45*s, (160, 255, 160), max(1, int(round(s))), cv2.LINE_AA)`.
  Các số 8, 10, 0.45, `(160,255,160)` và độ dày `max(1, round(s))` VIẾT LITERAL theo hợp đồng 13b §2, KHÔNG import hằng của module.
  Kỳ vọng `np.array_equal(canvas[py:py+ph, px:px+cw], E)`.
- Không sửa hay xóa dòng nào có sẵn (numstat cột xóa = 0).

Lệnh: `PY -m unittest tests.test_level1_display -v > l13c_t1_green.log 2>&1` ⇒ `OK`, ghi số `Ran`. Mã hiện tại được coi là đúng, nên test mới XANH
ngay; bằng chứng test bắt được lỗi là AC-T1m. Nếu S5 hoặc P1 đỏ trên mã hiện tại ⇒ DỪNG, báo planner (không nới dung sai, không đổi oracle).

### AC-T1m (T1 — đột biến, cầu nối chạy trong worktree tạm `_work/_plan15_l13/wt_13c_t1` tại commit T1, xóa sau; không sửa cây chính)
Mỗi đột biến sửa `src/inference/level1_display.py` trong worktree, rồi chạy `PY -m unittest tests.test_level1_display`. Kỳ vọng `FAILED` ở mọi đột biến:
- (rA) `:133` `thickness = STATS_THICKNESS`;
- (rB) `:135` dùng `STATS_BOTTOM_MARGIN` thay `scaled_px(STATS_BOTTOM_MARGIN, scale)`;
- m9–m12 của 13b (chạy lại).

Bản không đột biến ⇒ `OK`. Log `l13c_t1_mut_{rA,rB,m9,m10,m11,m12,base}.log`; ghi dòng `Ran`/`FAILED` vào progress. Một đột biến không đỏ ⇒ DỪNG, báo planner.

### AC-T2 (T2 — chỉ THÊM lớp mới trong `tests/test_level1_demo.py`, `skipUnless(not _MISSING)`; dùng lại `_ScaledWindowRecorder`, `_FullscreenRecorder` KHÔNG sửa)
- W1a (U2b m5). Dựng app `--source CLIP` trong `chdir(PROJECT_ROOT)`, chưa `run`. Đầu vào:
  - `view` 480×640 bất đối xứng do test tạo (vd. gradient ngang cộng khối đặc ở góc trên trái);
  - cặp `(text_or_view, small)` hợp lệ của app. Coder chọn cách lấy (vd. `app._hud_lines()`) và ghi cách lấy vào progress;
  - `hold = 0.6`, `stats = ["fps 30.0 | hud 1.2ms"]`.

  Vá `getWindowImageRect` cho ném `cv2.error`, `resizeWindow` không làm gì. Kỳ vọng:
  - `out = app._window_image(view.copy(), tov, small, 0.6, stats)` `array_equal` với `app.hud.compose(view.copy(), tov, small, 0.6, stats)`;
  - `out` có ≥ 1 pixel `== (0, 200, 0)`.
- W1b (U2b m6). Như W1a, nhưng rect `(0, 0, 1920, 1080)`. Đặt `ph = app.hud.panel_height(tov, small, 1)`, `L = fit_layout(640, 480, ph, (0, 0, 1920, 1080))`. Kỳ vọng:
  - vùng camera `out[L.y0 : L.y0 + cam_h, L.x0 : L.x0 + L.content_w]` == `cv2.resize(view, (L.content_w, cam_h), interpolation=cv2.INTER_LINEAR)`
    với `cam_h = L.cam_rect[3]`;
  - `out` có ≥ 1 pixel `== (0, 200, 0)`.
- F1 (U2c m5, m6). Chạy `run()` KHÔNG `--fullscreen`, `_FullscreenRecorder(keys=[ord("f"), ord("f")])`. Kỳ vọng:
  - `[p[2] for p in rec.set_props] == [cv2.WINDOW_FULLSCREEN, cv2.WINDOW_NORMAL]`, `[p[1] …] == [cv2.WND_PROP_FULLSCREEN] * 2`;
  - `len(rec.resized) == 2` (lần đầu, và sau khi thoát toàn màn hình);
  - sự kiện fullscreen `[True, False]`.
- L1 (U2c m4, LRU). Mẫu đếm `ImageFont.truetype` như `TestHudFontLruU2c`. Dùng 9 scale mới khác nhau A1..A9, KHÔNG gồm 1.0, cỡ px khác nhau
  (vd. `px/20` với px 30..38). Gọi A1..A8, rồi A1 (không dựng mới), rồi A9. Kỳ vọng:
  - gọi A1 ⇒ KHÔNG dựng mới;
  - gọi A2 ⇒ dựng mới;
  - `len(hud._fonts) ≤ 8` ở mọi bước.
- Không sửa hay xóa dòng nào có sẵn (numstat cột xóa = 0).

Lệnh: `PY -m unittest tests.test_level1_demo.<LớpMới> -v > l13c_t2_green.log 2>&1` ⇒ `OK`, không skip trên máy có dữ liệu. `LALL > l13c_t2_green_level1_all.log`
⇒ `OK (skipped=1)`, DoD7 `known=9 allowed=36`. `PY -m unittest tests.test_level1_equivalence -v` ⇒ `OK`. Test mới đỏ trên mã hiện tại ⇒ DỪNG, báo planner.

### AC-T2m (T2 — đột biến trong worktree `_work/_plan15_l13/wt_13c_t2`, sửa `level1_demo.py` của worktree)
Chạy `PY -m unittest tests.test_level1_demo.<LớpMới>`. Kỳ vọng `FAILED` ở mọi đột biến:
- (b5) `:1349` `compose(view, text_or_view, small, 0.0, stats_lines)`;
- (b6) `:1350` `render_to_window(view[:, ::-1], …)`;
- (c4) bỏ `move_to_end` trong `_fonts_at`;
- (c5) `:1104` luôn `cv2.WINDOW_FULLSCREEN`;
- (c6) bỏ `:1109-1110`.

Base ⇒ `OK`. Log `l13c_t2_mut_{b5,b6,c4,c5,c6,base}.log`. Một đột biến không đỏ ⇒ DỪNG, báo planner.

### AC-P (quy trình, mọi bước có commit)
- Đúng 1 commit cho mỗi bước:
  - C1: `^15: L13-U2d `;
  - C2: `^15: L13-U2d báo cáo`;
  - T1: `^15: L13-U2t1 `;
  - T2: `^15: L13-U2t2 `;
  - XW: `^15: L13-XW `.
- File của mỗi commit ⊆ khối scope của bước đó (§5b).
- Sổ agy commit riêng, do orchestrator.
- Có log impact và detect-changes.
- 0 `skip` mới.
- `git diff --stat 93abb08..HEAD -- level1_demo.py src/` rỗng sau mọi bước.
- sha checkpoint vẫn bắt đầu bằng `160e0c68`.
- Không push.

## 5b. Phạm vi file

```scope
scripts/level1_display_cost.py
tests/test_level1_display_cost.py
tests/test_level1_display.py
tests/test_level1_demo.py
reports/level1_realtime_2026-10-08/display_cost.json
docs/plans/15-progress.md
```
Theo bước:
- C1: `scripts/level1_display_cost.py`, `tests/test_level1_display_cost.py`, progress.
- C2: `reports/level1_realtime_2026-10-08/display_cost.json`, progress.
- XW: progress (script thăm dò nằm ở `_work/`, không commit).
- T1: `tests/test_level1_display.py`, progress.
- T2: `tests/test_level1_demo.py`, progress.

CẤM trong 13c: `level1_demo.py`, `src/`, mọi file test có sẵn khác, `README.md`, 3 file ` D`. Tập này là con của §10 lần sửa 13 + 13b §5b.

Độ khó: S–M (C1 M, T1 S, T2 S–M); vùng nhạy cảm: có ở C1 (harness đánh giá có gate DC1). Không có ở T1/T2 (chỉ thêm test, không chạm đường khung).

## 6. Rủi ro dữ liệu/ML

- Số DC1 là thời gian trên máy local với `imshow` vá, nên phụ thuộc tải máy. `stage_p50_ms.mediapipe` trong JSON cho biết tải lúc đo. Không có số kỳ vọng ở đây; mọi số lấy từ JSON C2.
- Chọn lần đẹp: đã chặn bằng quy tắc "commit lần 1" đặt trước. Ba lần không cùng kết luận ⇒ DỪNG.
- Đổi gate sau khi thấy kết quả: KHÔNG. Ngưỡng và định nghĩa giữ nguyên, chỉ thêm điều kiện hợp lệ fail-closed. `MIN_FRAMES = 10` đặt trước lần đo C2.
- Lệch train ↔ realtime: 13c không sửa `level1_demo.py`/`src/`. Đường khung vào MediaPipe giữ nguyên (AC-U9/U9b + diff rỗng).
- Oracle S5 dùng `cv2.putText` với tham số hợp đồng. Nếu cv2 đổi phiên bản thì ảnh AA có thể khác, nhưng mã và test cùng gọi một cv2 nên vẫn bằng hệt; ghi phiên bản cv2 vào progress.
- Không có dữ liệu mới, không đổi model hay checkpoint. Clip D2 chỉ đọc.

## 7. Điểm dừng

- **CẦN NGƯỜI DÙNG (không chặn) — VU.** Ở buổi chạy thử demo (`PY level1_demo.py`, preset, webcam), người dùng nhìn và trả lời 3 câu:
  1. ảnh camera có co hoặc dịch khi các dòng gợi ý dưới panel hiện hoặc ẩn không, có khó chịu không (U2b THẤP-3);
  2. phím f vào và ra toàn màn hình có đúng không; sau khi ra, cửa sổ về cỡ tự nhiên, mất cỡ đã kéo, có chấp nhận không (U2c THẤP-6);
  3. tiêu đề đọc được không.

  Trả lời "khó chịu" hoặc "không chấp nhận" ⇒ planner lập bước sửa app riêng (vùng `level1_demo.py`, Claude). Ngược lại thì giữ và ghi Giới hạn R2.
- Không đổi model mặc định; không đụng thay đổi chưa commit của người dùng; worktree tạm xóa được; không push; không có hành động không hoàn tác.
- DỪNG, báo planner (không tự nới):
  - C1 cần sửa `level1_demo.py`/`src/`;
  - AC-C2 có mã thoát ≠ 0, kết luận lệch giữa 3 lần, hoặc 1080p không đi `render_to_window` ở mọi khung;
  - test T1/T2 đỏ trên mã hiện tại;
  - một đột biến AC-T1m/T2m không đỏ;
  - AC-X1 cho 0/8 OK.

## 8. Câu Giới hạn chuyển cho R2 (`docs/level1_desktop.md`; số lấy từ JSON C2, ghi đường khóa)
1. DC1: "DC1 so p50 thời gian cả khung (MediaPipe + segmenter + vẽ + hiển thị) giữa cửa sổ 1920×1080 và cỡ tự nhiên, với `imshow` vá (không đo chi phí vẽ
   cửa sổ của HĐH), 1 lượt mỗi điều kiện, thứ tự cố định, nên ratio phụ thuộc tải máy (3 lần đo: xem progress 13c C2). Riêng chặng vẽ tăng
   `info.hud_p50_delta_ms` ms (`reports/level1_realtime_2026-10-08/display_cost.json`)." KHÔNG trích ratio của `abdcf39`.
2. Panel đổi chiều cao thì ảnh camera đổi cỡ hoặc vị trí (U2b THẤP-3; tần suất lấy từ XW).
3. Cửa sổ thật: kết quả AC-W1 (rect khung đầu có bằng cỡ tự nhiên không).
4. `setWindowProperty` lỗi thì sự kiện vẫn ghi `on: true`; `--fullscreen` lỗi lúc mở thì cửa sổ giữ cỡ mặc định OpenCV (U2c THẤP-3).
5. Thoát toàn màn hình thì cửa sổ về cỡ tự nhiên, bỏ cỡ đã kéo (U2c THẤP-6), trừ khi VU quyết sửa.
6. Câu kiểm tĩnh E3/E4 của 13b §3 (giữ).

## 9. Con trỏ cần chèn (orchestrator chèn; planner không sửa file khác)

`docs/plans/15-progress.md` (cuối file):
`> LẦN SỬA 13c (2026-10-09): xem docs/plans/15-lan-sua-13c.md — C1 (Claude: DC1 fail-closed, path_counts, mã thoát, đường dẫn tương đối) → C2 (cầu nối: đo 3 lần, commit lần 1) → review U2d v2 → XW (cầu nối: X1 + thăm dò cửa sổ thật) → T1 (agy: test overlay chính xác) → T2 (agy: test _window_image/f/LRU) → G1; VU người dùng không chặn; câu Giới hạn R2 ở §8.`

`docs/plans/15-lan-sua-13.md` (ngay dưới con trỏ 13b ở đầu file, và ngay dưới con trỏ 13b sau bảng §8):
`> LẦN SỬA 13c (2026-10-09): xem docs/plans/15-lan-sua-13c.md — sửa U2d (gate DC1 fail-closed, giữ ngưỡng 1.25), thêm T1/T2 (chỉ test, khóa đột biến sống U2a–U2c), XW (X1 + thăm dò cửa sổ thật) trước V1, câu Giới hạn R2.`
