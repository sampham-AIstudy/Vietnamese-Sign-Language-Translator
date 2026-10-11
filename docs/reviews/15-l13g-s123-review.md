# Review 15 — Lần sửa 13g S1/S2/S3 (agy, người dùng tự chạy)

- Kế hoạch: `docs/plans/15-lan-sua-13g.md` (§3.2, §3.3, §4, §6, §9)
- Commit: S1 `a794d00`, S2 `01e3809`, S3 `84878b1` (mốc `2276abc`); HEAD `db9d56f`
- Reviewer: Claude (độc lập), 2026-10-11. Không sửa mã, không commit.
- Log: `_work/l13g/review_s123.log` (unittest + 1 đột biến trong bộ nhớ)

## Kết luận: CHANGES_REQUESTED

## Bảng kiểm 1–13

| # | Mục | KQ | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch / test thật | FAIL | AC-1, AC-2, AC-4, AC-5, AC-7 có test thật. AC-3 `tests/test_level1_gesture_diag.py:159-200` chỉ kiểm có phiên static True/False; `_is_enhanced` không bao giờ được gán, không assert CLAHE trước MP, mượt sau MP, segmenter nhận landmark mượt. AC-6 `:297-352`: ca G-3 (`:345-352`) bị G-0 chặn trước nên `stop_combined`/phát ngược/spell không được kiểm (assert `or`); "lấy lỏng hơn của hai biến thể" không kiểm (`clips_pfps=None` `:336`); "rules khớp bảng §3.3 từng số" không có test. AC-8 `:444-470` kiểm dict mẫu, không kiểm output `run_diag`/sha256. Đột biến bắt buộc §6:178 `>= 4` thành `>= 3` (thay 7 chỗ, trong bộ nhớ): `MUT_RESULT failures=0 errors=0` = đột biến SỐNG. JSON thiếu mục §3.2 `gestures.per_clip` (emits design/floor, số nét tối đa, phát ngược, raw vs smoothed): `frames_seq_raw` tính ở `scripts/level1_gesture_diag.py:369` nhưng không dùng. |
| 2 | Tự chạy test | PASS | `.venv/Scripts/python -m unittest tests.test_level1_gesture_diag -v`: `Ran 15 tests ... OK` (khớp agy báo 15/15). Bộ đầy đủ discover KHÔNG chạy (hạn mức): so sánh FAILED/ERROR mới UNVERIFIED (rủi ro thấp: không file nguồn cũ nào đổi). |
| 3 | Test cũ không bị sửa/skip | PASS (guard UNVERIFIED) | `git diff 2276abc..84878b1 --stat`: chỉ 4 file (script mới, test mới, JSON, progress), đều trong khối scope §7; không đụng `level1_demo.py`/`src`/`configs`/test cũ; không skip. agy: không có log `_work/agy_logs/*13g*` (log mới nhất 2026-10-09 13c), không xác minh được `[agy-guard] sạch`/`pre-commit: sạch`. |
| 4 | Nguồn dữ liệu | PASS (có giới hạn, xem M3) | 12 clip mp4 thật, sha256 khác nhau, quay 16:35–16:37 bằng `_work/l13g/collect_13g_gestures.py` (webcam dshow 640x480, khung chưa lật `:247`); MediaPipe thật. Không dữ liệu sinh. |
| 5 | Rò rỉ | PASS (n/a) | D là tập chỉnh; T chưa quay. |
| 6 | VAL/TEST | PASS (n/a) | Chưa có tập T; G-4 chưa chạy. |
| 7 | Số liệu truy được | FAIL | JSON có `generated_by.commit = 01e380927e16...` (40 ký tự, git cat-file -t = commit), `code_dirty: false`, lệnh tương đối: mối lo "thiếu commit hash" của orchestrator KHÔNG đúng. Nhưng progress S3 (`docs/plans/15-progress.md`, mục Lần sửa 13g — S3) nêu: backspace 0/5 ở design, 5/5 ở floor, g1_results backspace = false, 4 danh sách crits (vd [0.5, 0.6, 0.5, 0.6, 0.6]), 0.005–0.008 vs 0.023–0.026 làm căn cứ R-S — KHÔNG có trong JSON: `gesture_ablation` chỉ có `g0` + `decisions` vì return sớm ở `scripts/level1_gesture_diag.py:682-684`. Số không truy được: FAIL. Hash trong progress (a794d00, 01e3809) có thật. |
| 8 | Cỡ mẫu / CI | FAIL | Quyết định R-S tính trên `skeleton.moving_*` count 12 (1 khung/clip), p50 = p90 = 0.0 cả ba: suy biến (xem H2). n = 5/cử chỉ là kiểm khói theo §8 (chấp nhận), nhưng progress viết kết luận cơ chế (xóa bị nghẽn do tỉ lệ phẳng 80–85%) không có bằng chứng JSON. |
| 9 | Nhất quán train–realtime | FAIL (một phần) | Đường ống đúng thứ tự app (`level1_demo.py:1414-1451` so với script `:340-369`: CLAHE, MP, khóa tay, mượt, segmenter, still = state khác moving), dùng GestureEngine, enhance_low_light, LandmarkSmoother, HandednessLock, Level1SignSegmenter, aspect_points, palm_len thật — không cài lại logic. Lệch: `min_detected_frames=5` cứng (`:311`) thay vì giá trị checkpoint (= 3, `reports/level1_realtime_2026-10-08/gesture_false_trigger.json`) — hiện không đổi hành vi vì max(min_sign_frames 6, ...) (`src/inference/level1_segmenter.py:143`). Biến thể process-fps 15.5 trên nguồn ~16.9 fps giữ 38/76 khung (~8.4 fps hiệu dụng, không phải 15.5) — đúng luật §3.2 bước 3 nhưng không mô phỏng app. |
| 10 | Không giả/mock/hard-code | PASS | Không Math.random/mock ở đường chính; mock chỉ trong test qua session_factory/runner. |
| 11 | Bảo mật / riêng tư | PASS (agy UNVERIFIED) | grep users[\/]+ (không phân biệt hoa thường) trên JSON = 0; không khóa ảnh; overlay (có mặt) ở `_work/l13g/overlay/` không commit; mp4 không commit. agy: không có dòng ledger 13g trong `docs/agy_usage_ledger.csv` (dòng cuối 2026-10-09 13c), không log guard; nhánh đã trên origin (origin = db9d56f), không xác định được ai push. |
| 12 | So sánh công bằng / GATE | PASS | Hằng GRIDS / PRESET_RULES_13G (`:57-115`) khớp bảng §3.3 từng số (đọc tay); không nới sau kết quả. Xem M2 (G-0 dừng toàn bộ). |
| 13 | Kết luận vượt bằng chứng | FAIL | Progress S3: độ lệch thuộc giới hạn MediaPipe (dựa trên 12 khung 0.0); xóa bị nghẽn do tỉ lệ phẳng và vẫy dịch dọc (crits không có trong JSON). Thiếu thí nghiệm: R-S trên khung vẫy thực sự; chẩn đoán backspace ghi vào JSON. |

## Vấn đề theo mức

### CAO
- H1 — Số trong progress S3 không truy được. Toàn bộ số G-1/G-2 (0/5, 5/5, 4 danh sách crits, giá trị lưới 0.6/0.80) không có trong `reports/level1_realtime_2026-10-11/gesture_diag_D.json`; script dừng ở G-0 (`scripts/level1_gesture_diag.py:682-684`) nên lần chạy này không thể sinh ra chúng. Hoặc từ lần chạy khác không lưu, hoặc bịa. Phải gỡ khỏi progress hoặc sinh lại JSON có các khóa đó (lần chạy mới, commit sạch).
- H2 — Quyết định R-S suy biến (điểm planner 13h hỏi). Mã gộp KHÔNG sai: extend các danh sách moving (`:877-879`) và compute_percentiles (`:921-929`) đúng định nghĩa khung moving. Nguyên nhân thật: still trên khung có tay = 75/76 ở mọi clip (cả 5 clip vẫy), tức state moving chỉ ở khung có tay ĐẦU TIÊN (khi motion là None, `src/inference/level1_segmenter.py:312-314`); tay có mặt từ khung 0 (hand_rate.app_video = 1.0 cả 12 clip). Ở khung đó: bộ làm mượt trả nguyên landmark thô nên smooth = 0; phiên video khung đầu = phát hiện đầy đủ như static nên track = 0; enh = 0 ở MỌI khung vì enhance_low_light không kích hoạt khi khung đủ sáng (`src/inference/level1_core.py:502-503`). Vì vậy mediapipe_limit true là hệ quả của 12 khung 0.0, không phải bằng chứng; fix_draw_raw false chưa được kiểm. Script cần chặn cỡ mẫu (vd số khung moving dưới ngưỡng đặt trước thì rs_insufficient, không quyết định) — đổi luật thuộc planner. Quan sát (không thay luật): p90 trên MỌI khung từng clip có smooth < track (space_01 0.0053 vs 0.0258, backspace_01 0.0297 vs 0.0369).
- H3 — Test không đạt hợp đồng §6. Đột biến >= 4 thành >= 3 sống; G-3, lỏng hơn hai biến thể, rules khớp §3.3 không được kiểm; AC-3 không kiểm thứ tự đường ống (chi tiết dòng 1 bảng). Đột biến bỏ kẹp sàn chưa chạy (giới hạn 1 đột biến).

### TRUNG BÌNH
- M1 — JSON thiếu mục báo cáo §3.2 (gestures.per_clip: emits design/floor theo clip, số nét tối đa, phát ngược, raw vs smoothed). Vì G-0 trả sớm, backspace — đúng lỗi người dùng gặp (U2 `_work/l13g/u2_app.json`: space 5, backspace 0) — không có chẩn đoán nào trong JSON.
- M2 — Ngữ nghĩa G-0. Script dừng cả R-G khi BẤT KỲ cử chỉ nào đạt G-0 (`:682`). Space đạt cả offline và app (U2 phát 5 space), nên tiền đề G-0 (offline đạt mà app không) sai cho space. Kế hoạch ghi R-G từng cử chỉ g — cần planner chốt G-0 theo từng cử chỉ.
- M3 — Tính hợp lệ tập D. Collector `_work/l13g/collect_13g_gestures.py` (không tracked, .git/info/exclude) thay Windows Camera §5: (+) dshow 640x480 như app, khung chưa lật; (-) tự dừng ở max_duration 4.5 s nên mọi clip cử chỉ đúng 76 khung (~16.9 fps vì vòng xem trước chạy MediaPipe); ghi mp4 fps hằng (`:117-130`) nên POS_MSEC đều, mất jitter thật (đúng lỗi §3.5 nêu ở collector cũ); tay có trong 100% khung ở cả 12 clip, trái hướng dẫn bắt đầu khi tay hạ ngoài khung, nên segmenter/GestureEngine không thấy pha tay đi vào như trong app. Cần ghi Giới hạn; trước T (U3) nên chốt công cụ quay.
- M4 — min_detected_frames=5 cứng (`scripts/level1_gesture_diag.py:311`); phải lấy như min_detected_frames_of (`scripts/level1_gesture_check.py:378`).

### THẤP
- L1: is_git_dirty fail-open (`:504-505`) và không xét configs/.
- L2: Progress ghi S3 do agy/cầu nối; kế hoạch §4 giao S3 cho cầu nối. Không có log agy/dòng ledger cho 13g.

## CẦN NGƯỜI DÙNG / PLANNER QUYẾT ĐỊNH
1. G-0 theo từng cử chỉ (M2) và luật cỡ mẫu tối thiểu cho R-S (H2): đổi luật sau khi đã thấy dữ liệu D phải ghi rõ là lần sửa luật; D không còn là tập đặt trước sạch cho luật mới.
2. Quay lại D đúng §5 (tay vào/ra khung, thời lượng tự do) hay chấp nhận D hiện có kèm Giới hạn (M3).
3. Số progress S3 (H1): gỡ hay sinh lại bằng lần chạy có lưu G-1/G-2.
