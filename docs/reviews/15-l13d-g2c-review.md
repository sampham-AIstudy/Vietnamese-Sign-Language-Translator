# Review 15 — lần sửa 13d, phần G2c (app nối GestureEngine qua --gesture-config)

- Reviewer độc lập, 2026-10-10. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD `ddcfb11`.
- Phạm vi review: commit mã `415f5fa` (`15: L13-G2c …`, cha `59e146e`) + commit tiến độ `df0bbc5`. Coder: vslt-coder-claude (không phải agy ⇒ các kiểm agy không áp dụng).
- Hợp đồng: `docs/plans/15-lan-sua-13d.md` §4 hàng 5c + "Chi tiết thiết kế G2c", §5 G2c (AC-G6, AC-D9, AC-G5 phần guard, lệnh cuối), §5b, §7; gốc `docs/plans/15-lan-sua-13.md` §3.2 mục 4, §9 AC-G5/G6, §10.
- Ghi chú từ review trước đã kiểm: G2b #1 (flash lấy từ config nạp theo cờ) — đã làm (`level1_demo.py:1221-1226`, test `tests/test_level1_demo.py:4069`); G2a (engine nhận w/h thật kể cả khung không tay) — đã làm (`level1_demo.py:1381-1383`, test `:3976`).

## Kết luận: APPROVE

Không có FAIL. Các ghi chú dưới đây là THẤP / ghi chú cho bước sau, không chặn.

## Bằng chứng tự chạy (reviewer)

| Lệnh | Log | Kết quả |
|---|---|---|
| `PY -m unittest tests.test_level1_demo.TestGestureConfigArgsG6 tests.test_level1_demo.TestGestureEngineAppD9 tests.test_level1_guard tests.test_level1_gestures` | `_work/_plan15_l13/review_g2c_targeted.log` | `Ran 90 tests in 6.232s` — `OK` (không skip ⇒ AC-G4 chạy ở cây chính) |
| Lệnh cuối G2c (`tests.test_level1_*` + `tests.test_backend_source_guard`) | `_work/_plan15_l13/review_g2c_full.log` | `Ran 630 tests in 520.625s` — `OK (skipped=1)`; `[DoD7-guard] known=9 allowed=36` — khớp coder (630 OK skip 1; skip có sẵn từ G1, cùng số với G2b 615 + 15 mới) |
| Smoke headless (lệnh orchestrator giao) | `_work/_plan15_l13/review_g2c_smoke.log`, `review_g2c_smoke.json` | exit 0; `code_dirty false`, `git_commit ddcfb11`; `gestures.config_sha256 = 442b6d6c…` == `sha256sum configs/level1_gestures.json`; `overrides {}`; không khóa `gesture_space`/`gesture_backspace`; checkpoint sha `160e0c6825e365ba…` (không đổi); 0 sự kiện cử chỉ trên clip `a` (kiểm khói đường mã, không phải số đo) |
| Hồi quy đường cũ trên clip thật: cùng clip, `--checkpoint` thật, rev9; (a) không cờ cử chỉ, (b) `--gesture-space --gesture-backspace` không `--gesture-config`; chạy ở worktree `59e146e` và `415f5fa` | `_work/_plan15_l13/review_g2c_old_rv_wt_g2{b,c}_{plain,gest}.json` | Bỏ `generated_by`/`stages`/`warmup`/fps: thứ tự khóa bằng nhau, 0 khóa khác, text `a`, 3 sự kiện ở cả hai ⇒ đường cũ y hệt |
| Đột biến của reviewer (worktree tạm `_work/_plan15_l13/rv_wt_g2c` từ `415f5fa`, script `_work/_plan15_l13/review_g2c_mutate.py`; worktree đã gỡ) | `_work/_plan15_l13/review_g2c_mutate.log` | base `Ran 15` `OK`; 3/3 ĐỎ: A flash đọc `gesture_defaults()` (đường mặc định) thay config theo cờ ⇒ `test_d9b_flash_from_the_loaded_config` FAIL; B `still` lấy trạng thái segmenter TRƯỚC `push` (khung trước) ⇒ `test_d9a_still_of_the_same_frame…` FAIL ×2 mode; C engine bỏ qua khung không tay ⇒ `test_d9a_still…` FAIL ×2. File khôi phục bằng hệt (`restored identical: True`) |
| Đột biến của coder | `_work/_plan15_l13/g2c_mutate.log` | `red 10/10`, `restored byte-identical: True` — khớp `15-progress.md` |

Ghi chú: đột biến "engine nhận w/h = 0 khi không tay" không dùng vì `GestureEngine.step` ném `ValueError` với w/h ≤ 0 (`src/inference/level1_gestures.py:362-365`) ⇒ đỏ tầm thường; thay bằng C (không gọi engine khi không tay); coder M9 (w/h giả) phủ biến thể còn lại.

## Bảng kiểm 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, AC có test thật | PASS | AC-G6: `TestGestureConfigArgsG6` (cờ + mặc định None, preset, argv `main([])`, `--space-hold-ms` có mặt kể cả dạng viết tắt / `=`, `app_mod.GestureEngine is level1_gestures.GestureEngine`). AC-D9 (a) `test_d9a_still…` assert `set(stills) == {True, False}` và `still == (states[ts] != "moving")` cho MỌI lần gọi + w/h == 640×480 mọi lần, có khung None (đột biến `still=True`, khung trước, bỏ khung không tay đều đỏ); `test_d9a_old_trackers_not_called` (update cũ patch ném lỗi, `n_emits` 0); `test_d9a_engine_palm_frames_reach_the_window_without_hand` (+ đối chứng `--no-gesture-space`). (b) sha == sha256 file, `overrides {}` / `{"space_hold_ms": X}` (X = nửa giá trị config và X = 250 mặc định parser ⇒ khóa ngữ nghĩa "có mặt"), không khóa cũ, `source == "gesture"`, thời điểm sự kiện == thời điểm engine phát. (c) HUD 2 mẫu dòng + dòng nằm trong `_hud_lines()[1]`. (d) `test_d9d_no_flag_no_gestures_block` + hồi quy clip thật ở trên. AC-G5 guard: `tests/test_level1_guard.py:33` 1 dòng thêm, 0 xóa; guard xanh. Thiết kế: `is_space` cho cửa sổ vẫn tính trước `segmenter.push` (`level1_demo.py:1365`), `engine.step` sau `push` (`:1381-1383`), cùng `aspect_points` float64 (`src/inference/level1_segmenter.py:99`) ⇒ `is_palm` của engine và `is_space` của app trùng nhau. |
| 2 | Tự chạy lại test | PASS | Bảng trên: 90 OK; 630 OK skip 1, `[DoD7-guard] known=9 allowed=36` — khớp coder. |
| 3 | Test không bị sửa/skip/nới | PASS | `git diff --numstat 59e146e..415f5fa`: `tests/test_level1_demo.py 385 0`, `tests/test_level1_guard.py 1 0`; không `skip`/`expectedFailure` mới (grep dòng `+`); `pass` duy nhất là `_ScriptedSession.close`. |
| 4 | Nguồn gốc dữ liệu | PASS | Test dùng chuỗi tạo có kiểm soát (mẫu tay của `tests/test_level1_gestures.py`), docstring ghi rõ không phải dữ liệu / số đo; tham số từ `load_gesture_config`. Không sinh số báo cáo. |
| 5 | Rò rỉ split | N/A | Không train/đánh giá. |
| 6 | Chọn model bằng VAL / TEST 1 lần | N/A | Không đổi model; `DEFAULT_DEMO_ARGV` chỉ thêm 1 dòng `--gesture-config` (`level1_demo.py:1743`); checkpoint sha `160e0c68…` không đổi. |
| 7 | Số liệu truy được | PASS | Số trong `15-progress.md` mục G2c là số test/đột biến, đều có log; reviewer xác nhận `Ran 630 … OK (skipped=1)`, `red 10/10`, sha config/checkpoint. Smoke JSON có `generated_by` (lệnh + commit + `code_dirty false`). |
| 8 | Cỡ mẫu / CI | N/A | Không có kết luận đo lường. |
| 9 | Nhất quán train–realtime / E3 | PASS | Khung vào MediaPipe vẫn `session.process(frame_mp)` với `frame_mp = frame` (không đổi trong diff, không resize/flip). Engine nhận CÙNG `landmarks` (sau smoother nếu `--smooth-landmarks`) như segmenter và cửa sổ, w/h thật của khung kể cả khung không tay; `still` = trạng thái segmenter của cùng khung (khóa bởi đột biến B). |
| 10 | Không mock/giả trong đường chính | PASS | `_NoLabelClassifier`, `_ScriptedSession`, checkpoint stub chỉ trong test. Không số trần cử chỉ mới trong `level1_demo.py` (flash/hold/strokes đọc từ `gesture_values` / engine). |
| 11 | Bảo mật / đầu vào / phạm vi | PASS | `--gesture-config` thiếu file ⇒ `SourceError`; hỏng ⇒ `ValueError` của loader đổi thành `SourceError` (`level1_demo.py:920-926`) ⇒ `main` trả `EXIT_INPUT_ERROR = 2`; test `test_d9_bad_gesture_config_is_an_input_error`. Không token / dữ liệu commit. Phạm vi: `git diff --name-only 59e146e..HEAD` = 3 file mã/test G2c + `15-progress.md` (coder) + `STATE.md`, `usage_ledger.csv` (orchestrator, `ddcfb11`) — trong khối scope. Không push (origin `72037f3`). Không đụng README / 3 file bị xóa / untracked của người dùng. |
| 12 | So sánh công bằng / GATE | N/A | Không đo GF/GT ở G2c; tiêu chí GATE §3.3 không đổi. |
| 13 | Kết luận vượt bằng chứng | PASS | `15-progress.md` ghi smoke là "kiểm khói đường mã, không phải số đo"; không có khẳng định về độ nhạy / kích hoạt nhầm. |

## Đánh giá 6 giả định của coder

1. `effective_argv` chưa có ⇒ kiểm argv `main([])` đưa vào `Level1App` (`tests/test_level1_demo.py:3926`): CHẤP NHẬN. `effective_argv` thuộc bước R2 (15-lan-sua-13 §7.3, §8 hàng 15). Ghi chú cho R2: khi tách hàm, test phải assert `effective_argv([])` chứa `--gesture-config configs/level1_gestures.json` (không chỉ mirror).
2. `gestures.values` = giá trị FILE, ghi đè riêng ở `overrides`: CHẤP NHẬN — cùng mẫu `config.values`/`config.overrides` sẵn có; giá trị hiệu lực = `values` ghi đè bởi `overrides`. Script G3 / tài liệu phải ghi rõ cách đọc này.
3. `counts.emits {space, backspace}` chỉ đếm cử chỉ đang bật; `palm_frames`/`flat_frames` chỉ khi cử chỉ tương ứng bật: CHẤP NHẬN (giống đường cũ; §3.2 mục 4 không định cấu trúc `emits`).
4. Dòng HUD hiện cả khi chỉ bật `--gesture-backspace` (`level1_demo.py:1319`): CHẤP NHẬN — §3.2 mục 4 đòi dòng vẫy; đường cũ (engine None) giữ điều kiện cũ. Bỏ dòng gợi ý phẩy tay ở đường mới là hợp lý (đường mới không còn cú phẩy).
5. Sự kiện token của speller giữ `source "key"`, chỉ sự kiện `gesture_space`/`gesture_backspace` mang `source "gesture"`: CHẤP NHẬN — speller ngoài phạm vi G2c; AC-D9(b) nói "sự kiện cử chỉ".
6. `--gesture-config` thiếu/hỏng ⇒ `SourceError` exit 2, không rơi về đường cũ: CHẤP NHẬN (fail-closed, đúng tinh thần loader).

## Vấn đề (không chặn)

- THẤP-1 (độ phủ test): `_NoLabelClassifier` không bao giờ phát nhãn ⇒ đường mới chưa có test cử chỉ xen giữa nhãn thật ở rearm_mode classifier (thứ tự timeline space/backspace sau nhãn, `decoder.reset()` sau backspace). Rủi ro thấp vì `_apply_gesture_*` và `_drain_timeline` không đổi logic và đã có test cho đường cũ; smoke với checkpoint thật có 0 sự kiện cử chỉ nên không phủ. Đề nghị: kiểm ở G5 (clip cử chỉ thật của người dùng) hoặc thêm 1 test classifier giả phát nhãn cố định khi có dịp.
- THẤP-2: `--gesture-config` được nạp SAU khi nạp checkpoint/classifier trong `Level1App.__init__` (`level1_demo.py:917-926`, sau `:845-849`) ⇒ cờ hỏng chỉ báo lỗi sau khi nạp model (chậm hơn, không sai).
- THẤP-3: `is_space` (cửa sổ) và `is_palm` (engine) tính hai lần bằng cùng hàm trên cùng input float64 ⇒ bằng nhau hiện nay (test d9a khóa). Nếu sau này đổi định nghĩa xòe tay trong engine, phải đổi cả `level1_demo.py:1365`.
- Ghi chú: coder không cập nhật `docs/progress_log.md` (§5b cho phép, không bắt buộc) — orchestrator tự ghi.

## Ghi chú cho G3 (`scripts/level1_gesture_check.py`)

- Gọi `GestureEngine.step(ts, landmarks, w, h, still)` với `still = segmenter.state != "moving"` lấy SAU `segmenter.push` của CÙNG khung, w/h thật cả khi không tay (như app `level1_demo.py:1381-1383`); đường `smoothed` = landmark sau `LandmarkSmoother` (như preset), cùng biến đưa vào segmenter.
- Đọc `gestures.values` + `overrides` như giả định 2; ghi sha config cử chỉ như app.
- Test G3 phải kiểm script import `GestureEngine` từ `src.inference.level1_gestures` (phần AC-G6 còn lại).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có.
