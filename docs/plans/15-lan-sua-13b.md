# Kế hoạch 15 — LẦN SỬA 13b (bổ sung nhỏ cho `docs/plans/15-lan-sua-13.md` + `15-lan-sua-13a.md`): hợp đồng bước U2

Ngày: 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `d1a8308` (review U1+U1a APPROVE: `docs/reviews/15-l13-u1-review.md`).
Hiệu lực: THAY hàng U2 của `15-lan-sua-13.md` §8 (#3) bằng 4 phần U2a–U2d (§4); THÊM AC-U4b, AC-U7, AC-U8, AC-U9; làm rõ cách đo AC-U5
(thêm script); THÊM bước chẩn đoán X1 trước V1. KHÔNG đổi: AC-U1–U3, AC-U4 (gốc), gate DC1 của AC-U5, AC-U6 (bản sửa 13a), AC-U6b (13a §3.2 mục 6),
AC-0/AC-1, ngoại lệ E1–E4. Không có tiêu chí nào bị hạ.

## 1. Mục tiêu và DoD

Nối `render_to_window` (U1) vào app: cửa sổ co giãn/toàn màn hình cho buổi DEMO, đồng thời khóa bằng test lỗ hổng TB-1 (thanh hold + dòng
thống kê ở scale ≠ 1) và giữ đường khung vào MediaPipe không đổi. DoD phục vụ: hạng mục 5 (giao diện demo) của lần sửa 13; không lệch
train ↔ realtime (E3/E4/AC-U6b).

## 2. Hiện trạng (HEAD `d1a8308`)

- `src/inference/level1_display.py` (KHÔNG đổi ở U2): hằng `HOLD_BAR_BGR=(0,200,0)` `:27`, `HOLD_BAR_HEIGHT=3` `:28`, `STATS_BGR=(160,255,160)` `:29`,
  `STATS_FONT_SCALE=0.45` `:30`, `STATS_X=8` `:32`, `STATS_BOTTOM_MARGIN=10` `:33`; `scaled_px` `:36`; `fit_layout` `:94`;
  `draw_panel_overlays` `:122-137` (hình chữ nhật đầy, hai đầu mút BAO GỒM của `cv2.rectangle`; `putText` `LINE_AA`, độ dày `max(1, round(scale))`);
  `render_to_window` `:140-164`, gọi overlay ở `:163` với `layout.scale`.
- TB-1: không test nào ở scale ≠ 1 khóa overlay; đột biến m9 ⇒ `tests.test_level1_display` vẫn `OK` (`_work/_plan15_l13/review_mut_m9_no_overlay_scaled.log`).
- `tests/test_level1_equivalence.py:280-363` `_e4_violations` (danh sách đóng; THẤP-2: không bắt `vars(cv2)["resize"]`, `cv2.__dict__`, `cv2.dnn.blobFromImage`,
  `cv2.getRectSubPix`).
- `level1_demo.py`: `Hud.compose`, `Hud._fonts_at` (cache font không giới hạn — THẤP-5), dòng phím `:1153` (theo §2.2 gốc; coder xác nhận lại số dòng).
- `tests/test_hand_landmarks_ws.py:160-163` `TestReset.test_reset_segments_and_graphs`: đỏ 3/3 ở U1a, 3/4 ở M0 (THẤP-6).
- Thiếu: nối app (WINDOW_NORMAL, `getWindowImageRect`, phím `f`, `--fullscreen`, `--no-display-mirror`), test AC-U4/U6/U6b, lệnh đo AC-U5 tái lập được.

## 3. Quyết định của planner về các mục review

- **TB-1 → AC-U7 (bước U2a, đầu tiên của U2, trước khi đo AC-U5).** Mã hiện tại đúng, nên test sẽ XANH ngay; bằng chứng "test bắt lỗi" là đột biến
  m9–m12 phải ĐỎ (thay cho log đỏ viết-trước, chỉ áp cho U2a).
- **THẤP-2 → GHI GIỚI HẠN (ở R2), KHÔNG siết `_e4_violations` trong U2.** Lý do: (i) danh sách đóng không bao giờ đủ (`__import__`, `importlib`,
  numpy thuần, `vars`, `__dict__`, … là vô hạn) — thêm 4 ca chỉ dời lỗ hổng; (ii) mọi lối vòng reviewer nêu đều tạo MẢNG MỚI, đã bị kiểm động khóa:
  E3 spy (`is` đối tượng reader) ở headless/paced và AC-U6b ở chế độ cửa sổ (đường mới duy nhất của U2), E1 bit-identical là lưới cuối;
  (iii) sửa `_e4_violations` là sửa dòng có sẵn của file đang bị AC-0/13a giới hạn numstat (≤ 3 dòng xóa từ `ea9c645`), mở rộng diff vùng nhạy cảm.
  Bù lại, thêm kiểm DIFF rẻ cho mọi commit U2 (AC-U9): dòng `+` không chứa mẫu lách. Câu Giới hạn cho R2 (`docs/level1_desktop.md`, nguyên văn ý):
  "Kiểm tĩnh E3/E4 là danh sách đóng; không bắt được lời gọi qua `vars(cv2)`, `cv2.__dict__`, `getattr` gián tiếp, `__import__`/`importlib`,
  `cv2.dnn.blobFromImage`, `cv2.getRectSubPix` hay thu/phóng numpy thuần. Đường suy luận được khóa bằng kiểm động: E3 spy (identity) headless/paced,
  AC-U6b cửa sổ 1920×1080, E1 landmark bit-identical 10 clip; sửa khung TẠI CHỖ trước `process` không bị identity bắt."
- **THẤP-6 → bước chẩn đoán X1 trước V1** (§4), không skip, không nới. Đỏ liên tục ⇒ ngoại lệ "chập chờn" của AC-1 sau V1 KHÔNG còn áp dụng ⇒ DỪNG, báo planner.
- THẤP-3: ghi nhận, không sửa lịch sử; nếu agy `savewip` sinh commit `WIP …` trong phần agy của U2, reviewer ghi THẤP, phần đó vẫn phải kết thúc bằng 1 commit `^15: L13-U2<x> `.
- THẤP-4: ghi nhận; U2b–U2d bắt buộc log đỏ có mtime NHỎ HƠN log xanh, cả hai chạy trên cây làm việc chính (AC-U2P).
- THẤP-5: làm trong U2c (AC-U8: cache font LRU ≤ 8 cỡ), vì chính U2 (đọc `getWindowImageRect` mỗi khung khi kéo giãn) làm cache phình.

## 4. Chia việc U2 (mỗi phần 1 commit `15: L13-U2<x> …`; sau MỖI phần: cầu nối xác minh + vslt-reviewer kiểm riêng phần đó rồi mới giao phần kế)

| Phần | Nội dung | Phụ thuộc | Giờ | Coder | Lý do chọn coder |
|---|---|---|---|---|---|
| U2a | CHỈ THÊM test TB-1 (AC-U7) vào `tests/test_level1_display.py`; chạy đột biến m9–m12 trong worktree tạm (AC-U7m). Không đổi mã nguồn. | — | 1,0 | `vslt-coder` (agy Gemini, effort ≥ high) | Thuần test hiển thị, đặc tả pixel đầy đủ ở §5; không chạm đường khung. Cầu nối chạy lại m9 độc lập. |
| U2b | `level1_demo.py`: `namedWindow(..., WINDOW_NORMAL)`, mỗi khung `getWindowImageRect` bọc `try/except (cv2.error, AttributeError)`, hợp lệ ⇒ `fit_layout` + `render_to_window`, lỗi/không hợp lệ ⇒ `Hud.compose` (bằng hệt cũ); test AC-U4, AC-U4b, AC-U6b; E3/E4 xanh. | U2a APPROVE | 1,5 | `vslt-coder-claude` | Vùng nhạy cảm: sửa vòng lặp chính cạnh `frame`/`frame_mp`/`process`; AC-U6b (identity khung ở chế độ cửa sổ). |
| U2c | Phím `f` (toàn màn hình, sự kiện `fullscreen`), `--fullscreen` (không vào preset), `--display-mirror` → `BooleanOptionalAction`, gợi ý phím theo luật §2.2 gốc, cache font LRU (AC-U8); test AC-U6 (phần còn lại), AC-U8. Tùy chọn "2 cảnh báo cuối" (THẤP 12) KHÔNG làm ở U2 (dời R2). | U2b APPROVE | 1,0 | `vslt-coder` (agy Gemini, effort ≥ high) | Cơ học (argparse, phím, cache). Rủi ro chạm đường khung được chặn bằng AC-U9b (diff không đụng dòng khung) + chạy lại E3/AC-U6b. |
| U2d | `scripts/level1_display_cost.py` + `tests/test_level1_display_cost.py` (commit code); chạy → `reports/level1_realtime_2026-10-08/display_cost.json` (commit báo cáo riêng tại commit code sạch); gate DC1. | U2c APPROVE | 1,0 + chạy | `vslt-coder` (agy Gemini, effort ≥ high) | Harness đo, không sửa app; số liệu tái lập bằng lệnh. Cầu nối chạy lại lệnh đo; kết luận DC1 khác lần coder ⇒ DỪNG, báo planner. |
| X1 | Chẩn đoán THẤP-6 (§5 AC-X1). Không sửa file mã/test. | — (trước V1; nên chạy ngay sau U2d) | 0,25 | cầu nối/orchestrator (không cần coder) | Chỉ chạy lệnh + ghi log. |

Tổng U2 ≈ 4,5 h coder (gốc 1,5 h — gốc thiếu TB-1, AC-U6b, harness đo, LRU). Claude chỉ dùng cho U2b (≈ 1,5 h). Thứ tự bắt buộc U2a → U2b → U2c → U2d.
Quy ước chung giữ `15-lan-sua-13.md` §8 (impact trước khi sửa symbol có sẵn — `Hud.compose`, `Hud._fonts_at`, hàm vòng lặp chính, parser; detect-changes
trước commit; `git commit -- <đường dẫn cụ thể>`, KHÔNG stage `README.md` và 3 file ` D` của người dùng).

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

`PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python`; log tạm `_work/_plan15_l13/`. Ký hiệu cho AC-U7: cam 640×480, `panel_h = 200`;
`L = fit_layout(640, 480, 200, W, H)`; `s = L.scale`; `px, py, cw, ph = L.panel_rect[0], L.panel_rect[1], L.content_w, L.panel_rect[3]`;
panel builder của test trả `np.full((h, w, 3), BG)` với `BG = (40, 40, 40)` và `stats_step = scaled_px(18, s)`; ảnh view đặc `(90, 90, 90)`.
Cửa sổ kiểm: `(W, H) ∈ {(1920, 1080), (1280, 1360)}`, mỗi ca 1 `subTest`.

**AC-U7 (U2a, TB-1; THÊM lớp mới `TestU2OverlaysScaled` trong `tests/test_level1_display.py`)**
- H1 hold 1.0, `stats=[]`: mọi pixel `canvas[py : py + scaled_px(3, s), px : px + cw]` == `HOLD_BAR_BGR`.
- H2 hold 0.5: mọi pixel `canvas[py : py + scaled_px(3, s), px : px + int(cw * 0.5)]` == `HOLD_BAR_BGR`; hàng `py`, cột `[px + int(cw * 0.5) + 2, px + cw)`
  không có pixel `HOLD_BAR_BGR`.
- H3 hold 1.0: hàng `py + scaled_px(3, s) + 1` (trong `[px, px + cw)`) không có pixel `HOLD_BAR_BGR` (chiều cao thanh co giãn đúng, không dày hơn).
- H4 hold 0: không pixel nào của `canvas` == `HOLD_BAR_BGR`.
- S1 hold 0, `stats=["fps 30.0 | hud 1.2ms"]`: tập `D` = pixel trong vùng panel `[py, py + ph) × [px, px + cw)` khác `BG`: `|D| > 0`; mọi hàng của `D`
  ≥ `py + ph // 2` (dòng thống kê ở nửa đáy panel); có ≥ 1 pixel của `D` với `max |pixel − STATS_BGR|` theo kênh ≤ 8.
- S2 hold 0, `stats=[]`: `|D| == 0`.
- S3 chiều cao chữ: cùng 1 dòng S1, `span = max_row(D) − min_row(D) + 1`; `span(1280×1360, s = 2) / span(fit_layout(640, 480, 200) tự nhiên, s = 1)` ∈ `[1.6, 2.4]`
  (dung sai planner chốt TRƯỚC khi chạy).
- S4 hold 1.0 + stats S1: mọi pixel ngoài vùng nội dung == 0 (không vẽ ra dải đen).
- Lệnh: `PY -m unittest tests.test_level1_display -v > _work/_plan15_l13/u2a_green_display.log 2>&1` → `OK`, `Ran` = 22 + số test mới (ghi số thật).

**AC-U7m (U2a, đột biến)** Worktree tạm `_work/_plan15_l13/wt_u2a` tại commit U2a (xóa sau; KHÔNG sửa cây làm việc chính), mỗi đột biến sửa
`src/inference/level1_display.py` trong worktree rồi chạy `PY -m unittest tests.test_level1_display` ⇒ `FAILED`; bản không đột biến ⇒ `OK`:
(m9) `:163` chỉ gọi `draw_panel_overlays` khi `layout.scale == 1.0`; (m10) chiều cao thanh hold dùng `HOLD_BAR_HEIGHT` thay `scaled_px(HOLD_BAR_HEIGHT, scale)`;
(m11) cỡ chữ thống kê `STATS_FONT_SCALE` thay `STATS_FONT_SCALE * scale`; (m12) `:163` truyền `1.0` thay `layout.scale`.
Log `_work/_plan15_l13/u2a_mut_{m9,m10,m11,m12,base}.log`; ghi dòng `Ran`/`FAILED` từng log vào 15-progress. Một đột biến không đỏ ⇒ DỪNG, báo planner (không đổi ca).

**AC-U4 (giữ nguyên, U2b)** `TestLatencyAcL` + mọi test cửa sổ cũ xanh KHÔNG sửa; test mới: recorder vá thêm `getWindowImageRect → (0, 0, 1920, 1080)`
⇒ mọi ảnh `imshow` có shape (1080, 1920, 3).
**AC-U4b (mới, U2b — làm rõ dự phòng)** Recorder ghi đối số `namedWindow`: cờ chứa `cv2.WINDOW_NORMAL`. `getWindowImageRect` (a) ném `cv2.error`,
(b) không tồn tại (`AttributeError`), (c) trả `(-1, -1, -1, -1)` ⇒ mỗi ca: app chạy hết clip không ngoại lệ, mọi ảnh `imshow` có shape tự nhiên
(cao = cam_h + panel_h, rộng = cam_w) và `array_equal` với ảnh `Hud.compose` của cùng khung (hoặc, nếu recorder không tách được đầu vào, với ảnh của
lần chạy (a) — coder ghi cách so vào progress).
**AC-U6b (13a §3.2 mục 6, U2b)** nguyên văn 13a; xanh, không skip trên máy có dữ liệu.
**AC-U6 (bản 13a; phần E3 kiểm ở U2b và U2c; phần còn lại ở U2c)** phím `f` hai lần ⇒ hai sự kiện `{"event": "fullscreen", "on": true}` rồi `false`;
`setWindowProperty` ném `cv2.error` ⇒ app không dừng; `--fullscreen` ⇒ `setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, …)` gọi 1 lần lúc mở,
`effective_argv` của preset KHÔNG chứa `--fullscreen`; `--no-display-mirror` ⇒ `display_mirror is False`; parser mặc định False; `effective_argv([])` vẫn bật mirror.
**AC-U8 (U2c, THẤP-5)** Vá hàm dựng font mà `Hud` dùng (coder ghi tên vào progress) để đếm: gọi cache với 20 cỡ px khác nhau liên tiếp ⇒ cỡ thứ 20 gọi lại
không dựng font mới; cỡ thứ 1 gọi lại ⇒ dựng mới (đã bị đẩy ra); số cỡ giữ trong cache ≤ 8 tại mọi thời điểm. Test cũ của `Hud` xanh không sửa.
**AC-U9 (mọi phần U2, THẤP-2)** `git diff d1a8308..HEAD -- level1_demo.py scripts/level1_display_cost.py src/ | grep -E '^\+' | grep -cE
'vars\(|__dict__|cv2\.dnn|getRectSubPix|__import__|importlib|warp|remap|pyr(Up|Down)'` → `0`. `git diff --stat d1a8308..HEAD -- src/` rỗng
(U2 KHÔNG sửa `src/inference/level1_display.py`; nếu cần ⇒ DỪNG, báo planner).
**AC-U9b (U2c, U2d)** `git diff <commit U2b>..HEAD -- level1_demo.py | grep -E '^[-+]' | grep -cE 'process\(|frame_mp|draw_landmarks|display_view|HandLandmarkSession|\.read\('`
→ `0` (U2c/U2d không chạm đường khung vào MediaPipe).
**AC-U5 (gate DC1 giữ nguyên; U2d làm rõ CÁCH đo)** Lệnh tái lập: `PY scripts/level1_display_cost.py --out reports/level1_realtime_2026-10-08/display_cost.json`
(đối số khác do coder chọn, ghi nguyên văn). Script: cùng tiến trình chạy app trên clip D2 `--pace realtime` chế độ cửa sổ, `imshow`/`waitKey` vá như
`TestLatencyAcL` (tự cài, KHÔNG import từ `tests/`), 2 lần: `getWindowImageRect` trả kích thước tự nhiên, rồi `(0, 0, 1920, 1080)`. JSON có: `command`,
`commit` (sha code sạch), `clip`, `n_frames` mỗi lần, `p50`/`p90` `frame_total` mỗi lần (ms), `ratio_p50`, `gate: {"name": "DC1", "threshold": 1.25, "pass": bool}`,
`note` ("imshow vá, không cửa sổ thật"), phiên bản python/cv2. Gate DC1: `p50(1080p) ≤ 1.25 × p50(tự nhiên)`; trượt ⇒ DỪNG, báo planner.
`tests/test_level1_display_cost.py`: không cần dữ liệu thật — tính p50/ratio/gate trên chuỗi thời gian tổng hợp (docstring "chuỗi tạo có kiểm soát để
kiểm logic"), JSON đủ khóa, gate biên (ratio = 1.25 ⇒ pass, 1.2501 ⇒ fail). Cầu nối chạy lại lệnh: kết luận `pass` khác lần coder ⇒ DỪNG, báo planner.
**AC-U2P (quy trình, mọi phần)** Đúng 1 commit `^15: L13-U2[a-d] ` mỗi phần (+ commit báo cáo `^15: L13-U2d ` riêng cho JSON); file ⊆ §5b; numstat cột xóa
= 0 với mọi file test có sẵn trừ ngoại lệ E1–E4 (`tests/test_level1_equivalence.py` vẫn ≤ 3 dòng xóa tính từ `ea9c645`); không `skip` mới.
U2b–U2d: `_work/_plan15_l13/u2<x>_red.log` (test mới đỏ) mtime < `u2<x>_green*.log`, cả hai trên cây làm việc chính.
Mỗi phần: `PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard > _work/_plan15_l13/u2<x>_green_level1_all.log 2>&1`
→ `OK (skipped=1)` (skip duy nhất `test_u1_summary`), `[DoD7-guard] known=9 allowed=36`; `PY -m unittest tests.test_level1_equivalence -v` (U2b, U2c) → `OK`,
`TestEquivalenceE3Spy`, `TestEquivalenceE4Display` và lớp AC-U6b chạy không skip. AC-1 (lệnh M0): đỏ chỉ là tập đỏ của M0.
`checkpoints/alphabet_best.pt` sha vẫn `160e0c68…`.
**AC-X1 (trước V1, THẤP-6)** Tại HEAD lúc chạy: (i) 5 lần `PY -m unittest tests.test_hand_landmarks_ws.TestReset.test_reset_segments_and_graphs -v`
→ `_work/_plan15_l13/x1_iso_{1..5}.log`; (ii) 3 lần `PY -m unittest tests.test_hand_landmarks_ws -v` → `x1_mod_{1..3}.log`. Ghi vào 15-progress: số lần OK/FAIL
mỗi nhóm + 5 dòng cuối traceback đầu tiên. Luật: có ≥ 1 OK ở (i) hoặc (ii) ⇒ giữ nhãn "chập chờn" (ghi tần suất); 0 OK trên cả 8 lần ⇒ KHÔNG phải chập chờn,
ngoại lệ AC-1 sau V1 không áp dụng ⇒ DỪNG, báo planner (file test và mã liên quan nằm ngoài §10; KHÔNG skip, KHÔNG nới).

## 5b. Phạm vi file

```scope
level1_demo.py
tests/test_level1_display.py
tests/test_level1_demo.py
tests/test_level1_equivalence.py
tests/test_level1_display_cost.py
scripts/level1_display_cost.py
reports/level1_realtime_2026-10-08/
docs/plans/15-progress.md
```
(Tập con của §10 lần sửa 13, CỘNG `scripts/level1_display_cost.py` — mới, lý do: AC-U5 cần lệnh tái lập có commit hash theo quy tắc số liệu.
`tests/test_level1_display_cost.py` khớp `tests/test_level1_*.py` của §10. U2a chỉ `tests/test_level1_display.py` + progress; U2b không sửa
`tests/test_level1_display.py`; `src/` CẤM ở U2.)

Độ khó: M (U2a S, U2b M, U2c S–M, U2d S–M); vùng nhạy cảm: có ở U2b (đường khung vào landmark/MediaPipe, test tương đương E3/E4/AC-U6b), không ở U2a/U2c/U2d.

## 6. Rủi ro dữ liệu/ML

- Lệch train ↔ realtime: chỉ ảnh HIỂN THỊ bị resize (E4). U2b là nơi duy nhất có thể làm lệch; khóa bằng AC-U6b (identity khung ở cửa sổ 1920×1080),
  E3 tĩnh, AC-U9/U9b. Giới hạn kiểm tĩnh (THẤP-2) ghi ở R2 (câu ở §3).
- Số liệu AC-U5 là thời gian trên máy local với `imshow` vá (không đo chi phí vẽ cửa sổ thật của HĐH) — JSON phải ghi rõ; không có số kỳ vọng ở đây.
- Không dữ liệu mới, không đổi model/checkpoint. Clip D2 chỉ đọc.

## 7. Điểm dừng

- Không CẦN NGƯỜI DÙNG: không đổi model mặc định, không cần dữ liệu người dùng, không đụng `README.md`/3 file ` D`, worktree tạm xóa được.
- DỪNG, báo planner (không tự nới): đột biến AC-U7m không đỏ; AC-U7 đỏ trên mã hiện tại (mã đúng theo probe reviewer — nếu đỏ, có thể đặc tả sai);
  cần sửa `src/`; AC-U6b không chạy được bằng recorder; DC1 trượt hoặc cầu nối ra kết luận DC1 khác; AC-X1 0/8 OK.

## 8. Con trỏ cần chèn (orchestrator chèn; planner không sửa file khác)

`docs/plans/15-progress.md` (cuối file, mục U2):
`> LẦN SỬA 13b (2026-10-09): xem docs/plans/15-lan-sua-13b.md — U2 chia U2a (agy, test TB-1) → U2b (Claude, nối cửa sổ + AC-U6b) → U2c (agy, phím f/cờ/LRU) → U2d (agy, đo DC1); X1 chẩn đoán test_reset trước V1.`

`docs/plans/15-lan-sua-13.md` (ngay dưới con trỏ 13a ở đầu file, và ngay dưới hàng U2 §8):
`> LẦN SỬA 13b (2026-10-09): xem docs/plans/15-lan-sua-13b.md — thay hàng U2 bằng U2a–U2d, thêm AC-U4b/U7/U8/U9 + script đo AC-U5, THẤP-2 ghi Giới hạn R2, bước X1 trước V1.`
