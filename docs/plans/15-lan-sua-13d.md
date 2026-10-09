# Kế hoạch 15 — LẦN SỬA 13d: chốt P1/P2 của review G1, hợp đồng G2 (chia G2a/G2b/G2c)

Không có điểm dừng CẦN NGƯỜI DÙNG (P1/P2 chốt theo §0 Q5 "chỉ khi cố ý"; người dùng có thể đổi trước G3 nếu muốn, không chặn).

Người lập: vslt-planner, 2026-10-09. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `9552b2d`. Phụ lục của `docs/plans/15-lan-sua-13.md` (CÓ HIỆU LỰC như nằm
trong đó; mâu thuẫn thì theo 13d). Đầu vào: `docs/reviews/15-l13-g1-review.md` (APPROVE: TB-1, THẤP-1…4, P1, P2), 15-lan-sua-13 §0, §3.2, §3.3, §8 #5–#6,
§9 AC-G4…G7, §10; `docs/plans/15-progress.md:1793-1804` (G1, 6 giả định).

Độ khó: L (cả G2; từng phần ghi ở §4); vùng nhạy cảm: CÓ (landmark/tiền xử lý realtime: `aspect_points`, `level1_core`, `level1_demo.py`; ngữ nghĩa cử chỉ trước gate GF).

## 1. Mục tiêu và DoD

Chốt ngữ nghĩa cử chỉ còn mở (P1, P2, khung NaN) TRƯỚC G3 (ngữ nghĩa không được đổi sau khi đo GF), khóa bằng test các giả định G1 đang sống dưới đột biến
(R2, R4), rồi làm G2 theo 15-lan-sua-13 §3.2 mục 3–4 thành 3 commit nhỏ. DoD phục vụ: DoD 7 (guard: bỏ hằng/số trần cử chỉ khỏi `src/`, `known=9 allowed=36`),
tương đương train↔realtime (app và script G3 đi cùng `GestureEngine`), §0 Q5 (ít kích hoạt nhầm).

## 2. Hiện trạng (đã đọc)

- `src/inference/level1_gestures.py`: `DeliberateSpaceGesture.update` `:197-224` (mất tay `:200-202` hủy giữ + re-arm ngay; khung lỗi `:214-219`; rearm
  `ts - other_since > rearm_ms` `:222`); `WaveBackspaceGesture.update` `:296-328` (khung trong cooldown được đệm nếu đã nhả `:305-311`; `span = self.buffer[start:]` `:317`);
  `GestureEngine.step` `:350-364` (NaN: space nhận `has_hand=True, is_palm=False` `:362`, wave nhận `None` qua `_hand_points` `:149-158`; không kiểm `width/height`).
- `src/inference/level1_core.py`: hằng `GESTURE_BACKSPACE_COOLDOWN/WINDOW/MIN_DX/MIN_SPEED/FLASH` `:548-552`; `is_flat_hand_backspace(…, thumb_min_ratio=0.5,
  thumb_max_spread=1.05)` `:556-557`; `BackspaceGestureTracker.__init__` mặc định từ hằng `:604-607`; số trần `0.35`, `1.1`, `0.04` trong `update` `:653, 661-663`.
- `level1_demo.py`: import `GESTURE_BACKSPACE_FLASH` `:92-93`; tracker cũ `:893-900`; `_gesture_step`/`_gesture_backspace_step`/`_gesture_line` `:1110-1170`;
  khung: `is_space`/`is_flat` `:1277-1282`, `segmenter.push` `:1286`, cửa sổ classifier `:1291`, bước cử chỉ `:1294-1298`; JSON `:1516-1531`; parser `:1589-1596`;
  `DEFAULT_DEMO_ARGV` `:1612-1622`. Hằng riêng của app `GESTURE_SPACE_*` `:151-153, 176` (đường cũ; test cũ dùng — GIỮ).
- Test: `tests/test_level1_gestures.py` (47 test; `DT = 25.0` `:55`, `PALM = 0.2` `:88`; helper `stroke_path`, `frames_from`, `transform`, `run_wave`; lớp
  `TestDeliberateSpaceAcG2` `:286`, `TestWaveBackspaceAcG3` `:388` có `both_ways`, `TestGestureEngine` `:549`; AST `:269-276` cho phép {0,1,2,3,5,9,13,17,21}).
  `tests/test_level1_guard.py` `PLAN15_FILES` `:26-33`. Không test nào import `GESTURE_BACKSPACE_*` (grep `tests/`: 0 dòng) ⇒ xóa hằng không làm đỏ test cũ.

## 3. Quyết định (planner chốt; có hiệu lực từ G2a, trước G3)

**P1 — space KHÔNG chịu khung MẤT tay: GIỮ hành vi G1.** `space_dropout_frames` chỉ chịu khung CÓ tay mà sai tư thế/không yên; khung không tay hủy giữ ngay.
Lý do: §0 Q5 ưu tiên ít kích hoạt nhầm; chịu mất tay sẽ nối hai đoạn xòe tay rời nhau thành một lần giữ (tăng phát, không tăng bằng chứng cố ý). Giá phải trả
(độ nhạy khi MediaPipe chập chờn) do GT1 (§3.4, AC-G8) đo — gate đã đặt, không đổi. Việc ở G2a: sửa `reason` của `space_dropout_frames` trong
`configs/level1_gestures.json` (KHÔNG đổi `value`) để nói rõ "khung có tay mà sai tư thế/không yên; khung không tay hủy giữ", và câu tương ứng trong docstring.

**P2 — khung trong cooldown KHÔNG vào bộ đệm vẫy: ĐỔI so với G1 (chặt hơn).** Mọi khung có tay với `ts - last_emit_ts < wave_cooldown_ms` không được đệm
(bộ đệm rỗng, `strokes = 0`); nét chỉ đếm từ khung đầu tiên HẾT cooldown. Mất tay vẫn nhả `need_release` ngay (giữ G1). Lý do: cách G1 cho phép backspace thứ 2 phát
đúng lúc hết cooldown dù tay đã đứng yên (vẫy đã xong trước đó) — phát lệch thời điểm cử chỉ, người dùng thấy như tự kích hoạt; cooldown theo §3.2 là "vẫy tiếp
không tự lặp". Giá: xóa liên tiếp chậm hơn (phải vẫy lại sau cooldown 1 s) — chấp nhận cho cử chỉ phá hoại.

**THẤP-2 — khung landmark không hữu hạn = KHÔNG TAY cho cả 2 tracker (sửa ở G2a).** `GestureEngine.step`: landmark [21,3] có NaN/inf ⇒ đi đường như
`landmarks is None` (space hủy giữ/re-arm, wave xóa bộ đệm; `is_palm`/`is_flat` False). `width`, `height` phải hữu hạn > 0, ngược lại ValueError (shape sai
vẫn ValueError như cũ). Lý do: nhất quán, và chặt theo P1; G3 chạy trên npz có thể có khung NaN ⇒ phải chốt trước khi đo.

**THẤP-4 — làm ở G2a (chỉ test):** AST không phân biệt chỉ số 1/2 với giá trị 1/2 ⇒ thêm test tham số hóa (AC-D3) giết đột biến gõ cứng.

**Ghi nhận (không đổi mã):** sau khi space phát, 1 khung mất tay re-arm ngay (AC-G2 "mất tay ⇒ re-arm", test `test_losing_the_hand_rearms`) ⇒ người dùng
giữ xòe tay tiếp ≥ `space_hold_ms` sau một khung chập chờn có thể nhận dấu cách thứ 2. Không đổi (hợp đồng AC-G2 đã duyệt; HUD báo dấu cách). G3/G5: JSON thêm
số clip có ≥ 2 lần phát mỗi cử chỉ (`multi_emit`, CHỈ báo cáo, không gate); R2 ghi Giới hạn.

## 4. Chia việc G2 (thay hàng #5 G2 của 15-lan-sua-13 §8; mỗi phần 1 commit `15: L13-G2a|G2b|G2c …`, review riêng từng phần trước phần kế — Q6)

Coder: **vslt-coder-claude** cho cả 3 phần. Lý do: kế hoạch gốc "L / Opus"; vùng nhạy cảm; G2b cần lớp test có `@unittest.skipUnless(not _MISSING, SKIP_REASON)`
(AC-G4, 10 clip hauuto) mà agy-guard đang chặn nhầm (backlog 0c STATE) ⇒ agy không làm được.
Quy ước như 15-lan-sua-13 §8 (`PY = PYTHONIOENCODING=utf-8 .venv/Scripts/python`, log `_work/_plan15_l13/`, `git commit -- <đường dẫn>`, impact trước khi sửa
symbol, detect-changes trước commit, test viết TRƯỚC + log đỏ). Đột biến: script tạm `_work/_plan15_l13/g2X_mutate.py` (không commit), khôi phục file gốc, `cmp` khớp.

| # | Mã | Nội dung | Phụ thuộc | Giờ | Độ khó |
|---|---|---|---|---|---|
| 5a | G2a | `level1_gestures.py`: P2 (cooldown không đệm), THẤP-2 (NaN = không tay; kiểm w/h) + docstring; config: CHỈ `reason` của `space_dropout_frames` (P1); test AC-D1…D6. Impact: `WaveBackspaceGesture.update`, `GestureEngine.step`. | G1 | 1,5 | M |
| 5b | G2b | `level1_core.py`: xóa 5 hằng + mọi số trần cử chỉ (`0.5`, `1.05` chữ ký — THẤP-1; `0.35`, `1.1`, `0.04` trong `BackspaceGestureTracker.update`) ⇒ mặc định đọc LƯỜI từ config; `level1_demo.py` CHỈ đổi import `GESTURE_BACKSPACE_FLASH` + 2 chỗ dùng (`:1160`, `:1528`); test AC-G4, AC-D7, AC-D8, AC-G5 (phần grep). Impact: `is_flat_hand_backspace`, `BackspaceGestureTracker`. | G2a | 1,5 | L |
| 5c | G2c | `level1_demo.py` §3.2 mục 4: `--gesture-config`, `GestureEngine`, `still`, preset, JSON `gestures`, HUD, `--space-hold-ms` ghi đè; guard thêm `src/inference/level1_gestures.py` vào `PLAN15_FILES`; test AC-G6, AC-D9, AC-G5 (phần guard). Impact: `Level1App.__init__`, `_gesture_step`, `_gesture_backspace_step`, `_gesture_line`, phương thức xử lý khung, `report`, `build_parser`. | G2b | 2 | L |

Chi tiết thiết kế G2b: một hàm `gesture_defaults()` trong `level1_core.py` có `functools.lru_cache(maxsize=1)`, import CỤC BỘ trong thân hàm
`from src.inference.level1_gestures import load_gesture_config` (tránh vòng import: `level1_gestures` import `level1_core` ở đầu file), đường dẫn tuyệt đối từ
`__file__` tới `configs/level1_gestures.json` (không phụ thuộc CWD), trả `values`. Tham số mặc định = `None` ⇒ lấy từ `gesture_defaults()`; giá trị ép `float` như
hằng cũ (JSON `flash_ms`, `cooldown_ms`, `window_ms` cùng kiểu cũ). `BackspaceGestureTracker` thêm thuộc tính `palm_ratio`, `dx_over_dy`, `min_dt_s` (tham số
tùy chọn, mặc định từ `legacy_flick_*`). Config thiếu/hỏng ⇒ lỗi khi gọi (fail-closed), không đọc file lúc import. Không đổi tên né guard; không thêm ALLOWED/KNOWN.

Chi tiết thiết kế G2c (giữ thứ tự khung hiện tại): `is_palm` cho cửa sổ classifier tính TRƯỚC `segmenter.push` như `:1280` (cùng `is_open_palm_space` trên cùng
`aspect_points`); `engine.step(ts, landmarks, w, h, still=self.segmenter.state != "moving")` gọi ở vị trí `:1294-1298` (SAU `segmenter.push` ⇒ `still` của CÙNG
khung). Chỉ áp kết quả của cử chỉ đang bật (`--gesture-space`, `--gesture-backspace`); tạm dừng ⇒ không gọi (như cũ). Có `--gesture-config`: KHÔNG ghi khóa cũ
`gesture_space`/`gesture_backspace` (tracker cũ không chạy) mà ghi `gestures` theo §3.2 mục 4; sự kiện cử chỉ thêm `source: "gesture"` CHỈ ở đường mới. Flash HUD
dùng `gesture_flash_ms`. HUD: `[Cử chỉ: Dấu cách n/600]` (n = `engine.space.held_ms`), `[Cử chỉ: vẫy k/2]` (k = `engine.wave.strokes`, mẫu số = `wave_min_strokes`).
`--space-hold-ms` có MẶT trong argv ⇒ ghi đè `space_hold_ms` (ghi `overrides`); không có ⇒ `overrides == {}`.

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; coder KHÔNG đổi; bổ sung AC-G4…G6 của 15-lan-sua-13 §9, không thay)

Dữ liệu test: chuỗi tổng hợp có docstring "chuỗi tạo có kiểm soát để kiểm logic". Test mới không dùng số gõ tay cho tham số thiết kế: lấy từ `load_values()`.
Mọi đột biến dưới đây phải ĐỎ (≥ 1 FAIL) và được ghi vào `15-progress.md` (log `_work/_plan15_l13/g2X_mutate.log`).

G2a (`tests/test_level1_gestures.py`, chỉ THÊM):
- **AC-D1 (TB-1)** (a) chuỗi: ≥ 10 khung tay KHÔNG phẳng đứng yên ngay trước 2 nét phẳng 1.2·A, tất cả trong `wave_window_ms`; test assert TIỀN ĐIỀU KIỆN: tỉ lệ
  phẳng trên mọi khung của bộ đệm lúc phát < `wave_min_flat_fraction`; `both_ways` ⇒ đúng 1 lần phát. (b) như (a) nhưng khung trước nét phẳng, lệch y ≥ 2·A (yên),
  tiền điều kiện: biên độ dọc/ngang trên cả bộ đệm > `wave_max_vertical_ratio`; `both_ways` ⇒ 1. (c) đối chứng: cùng số khung không phẳng nằm XEN TRONG các nét ⇒ 0.
  Đột biến R2 `span = self.buffer` ⇒ ĐỎ.
- **AC-D2 (THẤP-3)** sau khi space phát: khung tư thế khác với `ts - other_since == space_rearm_ms` ĐÚNG BẰNG (timestamp chọn chính xác, không cộng dồn DT)
  rồi xòe+yên đủ lâu ⇒ KHÔNG phát lần 2; cùng chuỗi với khung tư thế khác cuối ở `space_rearm_ms + DT` ⇒ phát lần 2. Đột biến R4 `>` → `>=` ⇒ ĐỎ.
- **AC-D3 (THẤP-4)** `from_values` với bản sao `values` đổi `wave_min_strokes = 3`: 2 nét ⇒ 0, 3 nét ⇒ 1; `space_dropout_frames = 2`: 2 khung lỗi liên tiếp vẫn phát,
  3 khung ⇒ đếm lại. Đột biến gõ cứng `self.min_strokes = 2`, `self.dropout_frames = 1` (trong `__init__`) ⇒ ĐỎ.
- **AC-D4 (P2)** phát; khung không tay ngay sau; tay trở lại và hoàn tất 2 nét 1.2·A HOÀN TOÀN trong cooldown; sau đó tay phẳng đứng yên tới
  `t_emit + wave_cooldown_ms + 300 ms` ⇒ KHÔNG phát lần 2 và `strokes == 0` ở mọi khung trong cooldown; đối chứng: 2 nét bắt đầu sau cooldown ⇒ đúng 1.
  `test_cooldown_blocks_even_after_the_hand_left` và `test_rearm_needs_end_of_flat_hand_after_cooldown` xanh KHÔNG sửa. Đột biến khôi phục hành vi G1 (đệm khung
  trong cooldown) ⇒ ĐỎ.
- **AC-D5 (THẤP-2)** `GestureEngine.step` với [21,3] có NaN: trả `is_palm False, is_flat False`; giữa lúc giữ xòe tay ⇒ chỉ số phát GIỐNG HỆT chuỗi thay khung đó
  bằng `None`; giữa nét vẫy ⇒ `engine.wave.strokes == 0` sau khung đó. `width` hoặc `height` ∈ {0, −1, nan} ⇒ ValueError; shape sai vẫn ValueError. Đột biến
  bỏ nhánh NaN ⇒ ĐỎ.
- **AC-D6 (P1)** `values` của config không đổi (`test_spec_is_the_design_table`, `test_committed_file_loads` xanh); `git diff 9552b2d..<G2a> -- configs/level1_gestures.json`
  chỉ đổi chuỗi `reason` của `space_dropout_frames`. 47 test G1 xanh không sửa.
- Lệnh: `PY -m unittest tests.test_level1_gestures` ⇒ `OK`; `PY -m unittest tests.test_level1_core tests.test_level1_guard` ⇒ `OK`.

G2b:
- **AC-G4** nguyên văn 15-lan-sua-13 §9 (lớp test 10 clip hauuto: 10 dòng hauuto ĐẦU theo thứ tự manifest `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv`,
  `@unittest.skipUnless(not _MISSING, SKIP_REASON)` khi thiếu file; so trên mọi khung có tay sau `aspect_points` như app).
- **AC-D7 (THẤP-1)** test AST trên nút hàm `is_flat_hand_backspace` và lớp `BackspaceGestureTracker` của `level1_core.py`: hằng số trong đó ⊆
  {0, 1, 2, 3, 4, 9, 12, 17, 21, 1000} (chỉ số điểm, shape 21, trung bình 3 điểm, chỉ số lịch sử/`-1`, ms→s; tập này là TRẦN — mã hợp lệ cần số khác ⇒ báo
  planner, không tự nới); mặc định tham số là `None`. Đột biến đưa lại `thumb_min_ratio: float = 0.5` hoặc số trần `0.35` ⇒ ĐỎ.
- **AC-D8** (a) `BackspaceGestureTracker()` có `cooldown_ms, window_ms, min_dx, min_speed, palm_ratio, dx_over_dy, min_dt_s` == `legacy_flick_*` của config, kiểu `float`;
  (b) trỏ `gesture_defaults` tới config tạm (patch hằng đường dẫn + `cache_clear()`, khôi phục trong `addCleanup`) có `legacy_flick_window_ms` khác ⇒ tracker mới mang
  giá trị khác (chứng minh đọc từ file); (c) tiến trình con `import src.inference.level1_core` ⇒ `gesture_defaults.cache_info().currsize == 0` (không đọc lúc import).
- **AC-G5 (phần grep)** `grep -rnE "GESTURE_BACKSPACE_(COOLDOWN|WINDOW|MIN_DX|MIN_SPEED|FLASH)" src/ level1_demo.py` = 0 dòng; `GESTURE_BACKSPACE_DEFAULT` còn.
- Lệnh: `PY -m unittest tests.test_level1_gestures tests.test_level1_core tests.test_level1_demo tests.test_level1_guard tests.test_backend_source_guard` ⇒ `OK`
  (skip chỉ do thiếu dữ liệu, có tên file); `[DoD7-guard] known=9 allowed=36`; test cũ `tests/test_level1_core.py:957+`, `tests/test_level1_demo.py:2177-2318, 2532-2536`
  xanh không sửa.

G2c:
- **AC-G6** nguyên văn 15-lan-sua-13 §9 (trừ câu "script import" — thuộc G3).
- **AC-D9** (a) có `--gesture-config`: `step` của engine nhận `still == (segmenter.state != "moving")` của CÙNG khung (patch ghi đối số trên chuỗi có cả 2 trạng thái);
  tracker cũ không được gọi (`n_emits` 0); khung được `engine` coi là xòe tay (`is_palm`) đi vào cửa sổ classifier như khung không tay khi `--gesture-space`;
  (b) JSON `gestures.config_sha256` == sha256 của file, `overrides == {}` không có `--space-hold-ms` và `{"space_hold_ms": X}` khi có; không có khóa
  `gesture_space`/`gesture_backspace`; sự kiện cử chỉ có `source == "gesture"`; (c) HUD trả đúng 2 mẫu dòng khi đang giữ/đang vẫy; (d) không cờ: report không có khóa
  `gestures` và toàn bộ test cũ `tests.test_level1_demo` xanh không sửa. Đột biến `still=True` cố định ⇒ ĐỎ.
- **AC-G5 (phần guard)** `src/inference/level1_gestures.py` thêm vào `PLAN15_FILES` (dòng mới, 0 dòng xóa); `tests.test_level1_guard` xanh.
- Lệnh cuối G2c: `PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard` ⇒ `OK` (skip chỉ do thiếu dữ liệu;
  `test_reset_segments_and_graphs` theo luật 3 lần chạy); `[DoD7-guard] known=9 allowed=36`; `sha256sum checkpoints/alphabet_best.pt` bắt đầu `160e0c68`.

Chung (mọi phần): AC-0/AC-1 của 15-lan-sua-13 §9; numstat `tests/` cột xóa = 0; không `skip` mới ngoài lớp AC-G4; mỗi phần đúng 1 commit `^15: L13-G2[abc]`.

## 5b. Phạm vi file

```scope
src/inference/level1_gestures.py
src/inference/level1_core.py
level1_demo.py
configs/level1_gestures.json
tests/test_level1_gestures.py
tests/test_level1_core.py
tests/test_level1_demo.py
tests/test_level1_guard.py
docs/plans/15-progress.md
docs/progress_log.md
```
Theo phần: G2a = `level1_gestures.py`, `configs/level1_gestures.json` (CHỈ `reason` của `space_dropout_frames`), `tests/test_level1_gestures.py`, `15-progress.md`.
G2b = `level1_core.py`, `level1_demo.py` (CHỈ import + 2 chỗ dùng flash), `tests/test_level1_gestures.py` hoặc `tests/test_level1_core.py` (chỉ THÊM), `15-progress.md`.
G2c = `level1_demo.py`, `tests/test_level1_demo.py`, `tests/test_level1_guard.py` (chỉ thêm 1 dòng), `15-progress.md`, `progress_log.md`.
CẤM giữ nguyên 15-lan-sua-13 §10 (`backend/main.py`, `README.md`, `configs/level1_realtime.json`, `src/data/`, `tests/test_backend_source_guard.py`, …).

Độ khó: L (G2a M, G2b L, G2c L); vùng nhạy cảm: có (landmark/tiền xử lý chung qua `aspect_points`, `level1_core`, app realtime; ngữ nghĩa trước gate đánh giá GF).

## 6. Rủi ro dữ liệu/ML

- Ngữ nghĩa cử chỉ (P1, P2, NaN) chốt TRƯỚC G3; sau khi có `gesture_false_trigger.json` không đổi nữa (luật dừng §3.3). Cả 3 thay đổi đều theo hướng ít phát hơn
  ⇒ GF dễ đạt hơn, độ nhạy GT có thể giảm — GT1/GT2 (đặt trước) là chỗ kiểm; không suy đoán số trước khi đo.
- Train↔realtime: app (G2c) và script G3 phải cùng gọi `GestureEngine.step` với landmark thô + `aspect_points`; `still` lấy từ segmenter config preset. Lệch thứ tự
  khung (`is_palm` trước/sau `segmenter.push`) được AC-D9(a) khóa.
- Lazy config ở `level1_core`: đổi `configs/level1_gestures.json` đổi cả đường CŨ (legacy) — chấp nhận vì cùng một nguồn truy vết; sha config ghi trong JSON đường mới.
- Dữ liệu test G2a là chuỗi tổng hợp (kiểm logic), không phải số báo cáo. AC-G4 đọc 10 clip hauuto (dữ liệu train) chỉ để kiểm bằng hệt, không đo.

## 7. Điểm dừng

Không có. Không đổi model mặc định, không cần dữ liệu người dùng cho G2 (clip §3.4 vẫn chỉ chặn G5), không đụng `README.md`/3 file ` D` của người dùng, không
hành động không hoàn tác. Nếu một test cũ đỏ do preset thêm `--gesture-config` (G2c) ⇒ DỪNG, báo planner (không sửa test).

## 8. Con trỏ cần chép (orchestrator chép; coder không sửa ngoài phạm vi)

- `docs/plans/15-lan-sua-13.md` (dưới dòng "LẦN SỬA 13c" ở đầu file và dưới bảng §8):
  `> LẦN SỬA 13d (2026-10-09): xem docs/plans/15-lan-sua-13d.md — chốt P1 (giữ: mất tay hủy giữ space), P2 (đổi: khung trong cooldown không đệm vẫy), NaN = không tay; hàng G2 thay bằng G2a/G2b/G2c (vslt-coder-claude) với AC-D1…D9 (khóa đột biến R2/R4, THẤP-1/4).`
- `docs/plans/15-progress.md` (cuối file):
  `## Lần sửa 13d — planner (2026-10-09): P1 giữ, P2 đổi, NaN = không tay; G2 = G2a → G2b → G2c, mỗi phần 1 commit + review; xem docs/plans/15-lan-sua-13d.md.`
