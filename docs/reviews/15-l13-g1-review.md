# Review 15 lần sửa 13 — bước G1 (commit e2ee6f8)

Reviewer độc lập, 2026-10-09. Phạm vi: CHỈ commit `e2ee6f8` ("15: L13-G1 config cử chỉ cố ý + level1_gestures (loader, 2 tracker, engine) (AC-G1–G3)"),
cha `d49c75c`, coder vslt-coder-claude (không phải agy ⇒ các mục kiểm agy không áp dụng). Hợp đồng: `docs/plans/15-lan-sua-13.md` §0, §3.1–§3.3,
§8 #4, §9 AC-G1…G3 + AC-0/AC-1, §10. Lần sửa 13a/13b/13c không đổi G1 (13c:98 chỉ xếp thứ tự).

## Kết luận: APPROVE

Không có FAIL. 1 vấn đề TB (thiếu test khóa giả định 3, không chặn — thêm test ở G2), 4 vấn đề THẤP. Mục "Cần planner chốt" có 2 điểm, không chặn G2.

## Bằng chứng đã tự chạy

| Lệnh | Log | Kết quả |
|---|---|---|
| `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_gestures tests.test_level1_core` | `_work/_plan15_l13/review_g1_unit.log` | `Ran 104 tests in 4.852s` — `OK` (khớp orchestrator) |
| `… -m unittest tests.test_level1_guard tests.test_backend_source_guard tests.test_level1_demo` | `_work/_plan15_l13/review_g1_guard_demo.log` | `Ran 194 tests in 343.497s` — `OK`; `[DoD7-guard] known=9 allowed=36` |
| `git diff --numstat d49c75c..e2ee6f8 -- tests/` | — | chỉ `617 0 tests/test_level1_gestures.py` (file mới; 0 dòng xóa ở test cũ, không skip mới) |
| `_work/_plan15_l13/g1_mutate.log` (của coder) | — | 10/10 đột biến FAILED (m1_strokes … m10_rearm) |
| Đột biến của reviewer (worktree tạm `_work/rev_g1_wt`, đã `git worktree remove`; cây chính không đổi) | — | xem bảng dưới |

Đột biến reviewer trên `src/inference/level1_gestures.py`:

| # | Đột biến | Kết quả |
|---|---|---|
| R1 | `GestureEngine.step`: `points = raw` (bỏ `aspect_points`) | ĐỎ (4 FAIL: TestGestureEngine) |
| R2 | `WaveBackspaceGesture.update`: `span = self.buffer` (tỉ lệ phẳng + dọc/ngang trên CẢ bộ đệm thay vì từ đầu nét 1) | SỐNG (`Ran 47 … OK`) ⇒ TB-1 |
| R3 | `DeliberateSpaceGesture.update`: `misses >= dropout_frames` (lệch 1) | ĐỎ (`test_one_bad_frame_in_the_middle_still_fires`) |
| R4 | rearm `>` → `>=` (biên đúng bằng `space_rearm_ms`) | SỐNG ⇒ THẤP-3 (biên độ rộng bằng 0, không AC nào đòi) |

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch / AC có test thật | PASS | AC-G1: `tests/test_level1_gestures.py:194-267` (thiếu/thừa khóa, thiếu value/source/reason, source ≠ design kể cả "Design"/None/"calibrated…", ≤0, NaN/inf, bool, chuỗi, tỉ lệ >1, strokes <1 và không nguyên, file commit nạp được và == bảng §3.2). AC-G2: `:312-384` (hold−1 khung ⇒ 0, = hold ⇒ 1, giữ tiếp vẫn 1, lỗi 1 khung vẫn phát đúng chỉ số, lỗi 2 khung đếm lại đúng chỉ số, still=False ⇒ 0, tư thế khác > rearm ⇒ lần 2, ngắn hơn ⇒ không, mất tay ⇒ re-arm + hủy giữ). AC-G3: `:410-545` (1 nét 3A ⇒ 0 / tracker cũ ⇒ 1; 2 nét 1.1A ⇒ 1; 0.9A ⇒ 0 kể cả 8 nét; trải > window ⇒ 0 và nhanh ⇒ phát; dọc/ngang 0.6 và 1.0 ⇒ 0, 0.4 ⇒ phát; phẳng 0.85 ⇒ 0, 0.95 ⇒ phát; vẫy 20 nét ⇒ 1; nhả + cooldown; mất tay giữa chừng ⇒ 0, không mất ⇒ 1; mọi ca qua `both_ways` = ×0.5 và lật x). Mẫu tay kiểm bằng vị từ thật của `level1_core` (`:145-167`). Mỗi ca âm có đối chứng dương ⇒ không assert luôn đúng. Thiếu: R2 (TB-1). |
| 2 | Tự chạy lại test | PASS | 104 OK; 194 OK + guard known=9 allowed=36 (bảng trên). Không chạy lại toàn bộ 590 test level1 (coder `g1_green_level1_all.log`: `Ran 590 … OK (skipped=1)`); các module bị ảnh hưởng (`level1_core`, `level1_demo`, guard) đã tự chạy. |
| 3 | Test không bị sửa/skip/nới | PASS | numstat tests/: chỉ file mới, 0 xóa. Lần xanh 1 đỏ ở test tự kiểm literal ⇒ coder sửa mã (NamedTuple), không sửa test (`15-progress.md` mục G1). |
| 4 | Nguồn gốc dữ liệu | PASS (không train/đo) | G1 không train/đo; dữ liệu test là chuỗi tổng hợp có docstring "chuỗi tạo có kiểm soát để kiểm logic" đúng §9 (`tests/test_level1_gestures.py:15-17`), không dùng làm số báo cáo. |
| 5 | Rò rỉ split | không áp dụng | — |
| 6 | VAL/TEST | không áp dụng | — |
| 7 | Số liệu truy được | PASS | 19 giá trị config == bảng §3.2 (`configs/level1_gestures.json:3-97`, test `:201`). 7 giá trị `legacy_flick_*` == hằng hiện tại `level1_core.py:548-551` + số trần `0.35`, `1.1`, `0.04` của tracker cũ; `git log -S` xác nhận có từ `7a267c7` (reason ghi đúng commit). `flat_*` 0.5/1.05 == số trần cũ (cũng từ `7a267c7`). Không có số đo trong tài liệu G1. |
| 8 | Cỡ mẫu / CI | không áp dụng | Không có kết luận thống kê ở G1. |
| 9 | Nhất quán train–realtime | PASS | `GestureEngine.step` nhận landmark MediaPipe thô [21,3] và gọi `aspect_points(raw, w, h)` (`level1_gestures.py:356-359`) — cùng hiệu chỉnh app đang dùng cho `is_open_palm_space`/`is_flat_hand_backspace` (`level1_demo.py:1280-1282, 1297`); R1 đỏ ⇒ có test khóa. Vẫy dựa trên biên độ x đối xứng ⇒ lật gương không đổi kết quả (test `both_ways` flip). |
| 10 | Không mock/random/hard-code trong đường chính | PASS | Không `random`, không đồng hồ; mọi ngưỡng từ `values` (`_need`, `level1_gestures.py:122-126`); test AST `:269-276` chỉ cho phép {0,1,2,3,5,9,13,17,21} (chỉ số điểm + miền). Ngoại lệ tạm: mặc định `0.5`, `1.05` trong chữ ký `is_flat_hand_backspace` (`level1_core.py:556-557`) — THẤP-1, G2 phải chuyển về config. |
| 11 | Bảo mật | PASS | Loader kiểm kiểu/miền/khóa/UTF-8 JSON (`level1_gestures.py:69-119`); engine kiểm shape [21,3] (`:357-358`); tracker kiểm timestamp hữu hạn. Không token/dữ liệu cá nhân trong diff. Không có API/WS/CORS ở bước này. |
| 12 | So sánh công bằng / gate không nới | PASS | Ngưỡng là giá trị THIẾT KẾ §3.2, `source: "design"`, đặt trước G3; GF1/GF2 (§3.3) chưa đo, không bị chạm. Khác biệt mới/cũ ghi bằng test trên CÙNG chuỗi (`:410-417`). |
| 13 | Kết luận vượt bằng chứng | PASS | Progress G1 chỉ khai kiểm logic trên chuỗi tổng hợp; không khẳng định tỉ lệ kích hoạt nhầm/độ nhạy (thuộc G3/G5). |

AC-0 (phạm vi): 5 file đổi (`configs/level1_gestures.json`, `src/inference/level1_gestures.py`, `src/inference/level1_core.py`,
`tests/test_level1_gestures.py`, `docs/plans/15-progress.md`) — đều trong khối `scope` §10; không chạm file CẤM, `README.md` hay 3 file bị xóa của người dùng.
Một commit `^15: L13-G1`; `25f993e` chỉ là commit state.

## Điểm soi của orchestrator

1. **`level1_core.is_flat_hand_backspace` thêm 2 tham số.** Diff chỉ thay `0.5 * palm` → `thumb_min_ratio * palm` và `1.05 * palm` →
   `thumb_max_spread * palm`, mặc định 0.5 / 1.05 (cùng float) ⇒ gọi 1 đối số cho kết quả bit-giống cũ (cùng phép nhân, cùng toán hạng). Được phép ở G1:
   §3.2 mục 2 bắt `GestureEngine` gọi `is_flat_hand_backspace(points, thumb_min, thumb_spread)` ⇒ chữ ký phải có ở bước làm engine; file nằm trong §10.
   Phần thuộc G2 (§3.2 mục 3: mặc định đọc LƯỜI từ config, xóa hằng `GESTURE_BACKSPACE_*`) CHƯA làm, progress ghi rõ. Test
   `test_flat_hand_thresholds_are_parameters_with_the_old_values` (`:160-167`) chỉ trên 1 mẫu tay; AC-G4 (10 clip hauuto) là việc G2.
2. **Config**: đủ 19 khóa, mỗi mục đúng `{value, source:"design", reason}`, giá trị khớp §3.2, reason nêu lý do/nguồn commit; `_about` là chú thích.
3. **AC-G3 "1 nét lớn: mới 0, cũ 1"**: đúng ý §9 ("1 nét biên độ lớn ⇒ 0 (cùng chuỗi qua `BackspaceGestureTracker` cũ ⇒ 1 — ghi khác biệt)"): test
   assert cả hai, progress ghi khác biệt.
4. Đột biến: 10/10 của coder đỏ; của reviewer 2/4 đỏ (R1, R3), R2 và R4 sống (TB-1, THẤP-3).
5. Test: tự chạy như bảng trên.

## Đánh giá 6 giả định của coder

| # | Giả định | Đánh giá |
|---|---|---|
| 1 | Khung lỗi space = có tay mà không (xòe và yên); mất tay hủy giữ ngay; thời gian giữ vẫn chạy qua khung lỗi | Đúng §3.2 ("Mất tay ⇒ hủy giữ"; AC-G2 "mất tay ⇒ re-arm"). Lưu ý: chập chờn hay gặp của MediaPipe là MẤT tay 1 khung, mà reason của `space_dropout_frames` viết "tolerate one flickering MediaPipe frame" ⇒ dropout chỉ chịu chập chờn tư thế/`still`, không chịu mất tay. Kế hoạch viết rõ nên coder đúng; xem P1. |
| 2 | `palm_len` chỉ x, y | Hợp lý, nhất quán với tracker cũ (`palm = norm(p[9,:2] - p[0,:2])`) và dịch tâm cũng đo trên x, y; z MediaPipe nhiễu. Không cần chốt. |
| 3 | Khoảng "các nét đã đếm" = từ cực trị bắt đầu nét 1 (cùng giá trị ⇒ khung muộn nhất) tới hiện tại | Đúng chữ "(trên khung của các nét đã đếm)" §3.2. Nhưng KHÔNG có test khóa (R2 sống) ⇒ TB-1. |
| 4 | Sau phát: không tay nhả ngay (kể cả trong cooldown, phát vẫn chờ hết cooldown); khung không phẳng chỉ nhả sau cooldown; lúc chờ nhả không đệm khung | Một cách đọc hợp lệ của "(không tay, hoặc ≥ 1 khung không phẳng sau cooldown)"; AC-G3 thỏa. Hệ quả: khung trong cooldown (sau khi tay rời) được đệm ⇒ 2 nét vẫy trong cooldown có thể phát NGAY khung đầu tiên hết cooldown, kể cả khi tay đã đứng yên (còn trong window 1.5 s). Chấp nhận được cho xóa liên tiếp; xem P2. |
| 5 | Miền giá trị (count nguyên ≥1; 2 tỉ lệ trong (0,1]; còn lại >0 hữu hạn); `_` là chú thích; mỗi mục đúng 3 trường | Đúng §3.2 mục 1 và AC-G1; `_about` theo kiểu `configs/level1_realtime.json`. Không cần chốt. |
| 6 | Engine nhận landmark thô [21,3], tự gọi `aspect_points` | Đúng: chữ ký §3.2 `step(ts_ms, landmarks_or_None, w, h, still)` có w, h chỉ có nghĩa khi đầu vào là thô; khớp cách app đang gọi. Không cần chốt. |

## Vấn đề

**TB-1 — giả định 3 (khoảng tính tỉ lệ phẳng + dọc/ngang) không có test khóa.** `src/inference/level1_gestures.py:317` `span = self.buffer[start:]`;
đổi thành `self.buffer` thì mọi test vẫn xanh (R2): mọi chuỗi test có khung trước nét 1 đều phẳng và cùng y ⇒ hai cách cho cùng kết quả. Nếu hồi quy:
tay chưa phẳng/trôi dọc trong ≤ 1.5 s trước khi vẫy sẽ chặn backspace cố ý (giảm độ nhạy GT2). Việc phải làm (ở G2, chỉ THÊM test, không đổi mã):
chuỗi có ~10 khung KHÔNG phẳng (hoặc lệch y lớn) đứng yên ngay trước 2 nét phẳng trong cùng window ⇒ phát đúng 1; chuỗi đối chứng có khung không phẳng
nằm TRONG các nét ⇒ 0. Không chặn APPROVE vì AC-G3 không liệt kê ca này.

**THẤP-1 — số trần mới trong `src/`.** `src/inference/level1_core.py:556-557` mặc định `0.5`, `1.05` trong chữ ký. Guard hiện không bắt (known=9 allowed=36),
nhưng §3.2 mục 3 / AC-G5 đòi đưa mặc định về config (đọc lười) ở G2 — G2 phải xóa cả hai literal này, không chỉ các hằng `GESTURE_BACKSPACE_*`.

**THẤP-2 — khung không hữu hạn xử lý không nhất quán giữa 2 tracker.** `GestureEngine.step` với landmark [21,3] chứa NaN: space nhận `has_hand=True,
is_palm=False` (khung lỗi, `level1_gestures.py:362`), wave nhận `None` qua `_hand_points` (= mất tay: xóa bộ đệm, nhả; `:299-303`). MediaPipe thực tế không
trả NaN ⇒ không ảnh hưởng demo. Engine cũng không kiểm `width/height > 0` (`aspect_points` chia cho `height`).

**THẤP-3 — biên rearm `> space_rearm_ms` không có test khóa** (R4 sống). Khác biệt chỉ ở đúng một giá trị thời gian; không AC nào đòi. Không cần sửa.

**THẤP-4 — test AST "không mặc định trong mã" (`tests/test_level1_gestures.py:269-276`) cho phép literal 1 và 2** ⇒ không bắt việc gõ cứng
`wave_min_strokes = 2` hay `space_dropout_frames = 1`. Đột biến hành vi m1, m2 của coder bù phần này; ghi để biết giới hạn của test.

## Cần planner chốt (không chặn G2; phải chốt TRƯỚC G3 vì ngữ nghĩa không được đổi sau khi đo)

- **P1** (giả định 1): `space_dropout_frames` có nên chịu cả 1 khung MẤT tay (chập chờn phát hiện) không? §3.2 hiện viết "Mất tay ⇒ hủy giữ", coder theo
  đúng; nếu giữ nguyên thì G2 sửa câu reason trong config cho khỏi hiểu là chịu cả mất tay.
- **P2** (giả định 4): chấp nhận "không tay nhả ngay, khung trong cooldown được đệm" (cho phép backspace thứ 2 ngay khi hết cooldown 1 s nếu đã vẫy trong
  cooldown)? Nếu muốn chặt hơn ("chỉ đệm sau cooldown") phải chốt trước G3.

## Kiểm agy

Không áp dụng (coder vslt-coder-claude; không có log `_work/agy_logs` cho bước này).
