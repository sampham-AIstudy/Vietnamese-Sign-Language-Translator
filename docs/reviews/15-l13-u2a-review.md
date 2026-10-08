# Review U2a (lần sửa 13b) — commit `cf5e2cc` "15: L13-U2a test TB-1 overlay co giãn (AC-U7/U7m)"

Reviewer độc lập, 2026-10-09, HEAD `6c8d6cc`. Coder: agy (gemini-3.8-flash-high, effort high). Hợp đồng: `docs/plans/15-lan-sua-13b.md` §3 (TB-1), §4 hàng U2a,
§5 AC-U7, AC-U7m, AC-U2P/AC-U9, §5b. Nguồn TB-1: `docs/reviews/15-l13-u1-review.md` dòng 20 (m9 xanh).

## Kết luận: APPROVE

0 CAO, 0 TB, 4 THẤP. Test mới bám đúng đặc tả pixel H1–H4, S1–S4 ở hai cửa sổ, oracle độc lập với mã (hằng/ngưỡng lấy từ hợp đồng), đột biến m9–m12 đỏ
(reviewer tự chạy lại m10, m11 tại `cf5e2cc`; cầu nối đã chạy m9, m12). Hai điểm mù ngoài hợp đồng (độ dày nét chữ, lề đáy) ghi THẤP cho planner cân nhắc.

## Test reviewer tự chạy (`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest …`)

| Lệnh | Log | Kết quả | Coder khai |
|---|---|---|---|
| `tests.test_level1_display tests.test_level1_equivalence -v` (cây chính, HEAD `6c8d6cc`) | `_work/_plan15_l13/review_u2a_main.log` | `Ran 43 tests in 84.199s` — `OK`; 8 test `TestU2OverlaysScaled` ok; E3Spy, E4Display chạy | — |
| `tests.test_level1_display` | `_work/_plan15_l13/review_u2a_display.log` | `Ran 30 tests in 21.812s` — `OK` (22 cũ + 8 mới) | `Ran 30` `OK` (`u2a_green_display.log`) — khớp |
| Worktree tạm `_work/_plan15_l13/wt_rev_u2a` tại `cf5e2cc` (đã `git worktree remove --force` + `prune`), mỗi đột biến 1 dòng `src/inference/level1_display.py` | `review_u2a_mut_*.log` | base `Ran 30` `OK`; **m10** (`panel_top + HOLD_BAR_HEIGHT`) `FAILED (failures=2)` h1, h2; **m11** (`STATS_FONT_SCALE` không nhân scale) `FAILED (failures=1)` s3; rC (thanh dày thêm 1 px: `scaled_px(...) + 1`) `FAILED (failures=3)` h3 + test cũ `test_u2_hud_scale_one_identical_to_m0_hud`; **rA** (nét chữ `thickness = STATS_THICKNESS`) `OK`; **rB** (lề đáy `STATS_BOTTOM_MARGIN` không co giãn) `OK` | m10 `failures=2`, m11 `failures=1` — khớp |
| Log coder/cầu nối (đọc bằng grep) | `u2a_mut_{base,m9,m10,m11,m12}.log`, `u2a_bridge_mut_{m9,m12}.log`, `u2a_green_level1_all.log`, `u2a_bridge_level1_all.log` | base OK; m9 `FAILED (failures=6, errors=1)`; m12 `FAILED (failures=3)` (cầu nối lặp lại khớp); level1 all `Ran 493` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` (cả hai log) | khớp 15-progress |

Reviewer KHÔNG chạy lại toàn bộ 493 test Level 1 (hạn mức); dựa vào hai log độc lập coder + cầu nối khớp nhau.

## Bảng 13 mục

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test thật | PASS | `tests/test_level1_display.py:453-563`. H1 `:468` (hàng `[py, py+scaled_px(3,s))` × `[px, px+cw)` == `HOLD_BAR_BGR`); H2 `:478` (nửa trái đủ màu + hàng `py` từ `px+int(cw*0.5)+2` không có màu thanh); H3 `:491` (hàng `py+scaled_px(3,s)+1` sạch — khớp `cv2.rectangle` tô bao hai đầu, bắt rC); H4 `:502` (toàn canvas); S1 `:510` (`|D|>0`, mọi hàng ≥ `py+ph//2`, ≥1 pixel cách `STATS_BGR` ≤ 8/kênh); S2 `:526`; S3 `:536` (tỉ lệ span 1280×1360 / tự nhiên ∈ [1.6, 2.4], dung sai đúng hợp đồng, không nới); S4 `:559` (mặt nạ `_outside_mask` có sẵn). Hai cửa sổ (1920,1080) và (1280,1360) bằng `subTest` (S3 chỉ 1280×1360 theo hợp đồng). Oracle: hằng 3/18/BG/view lấy từ hợp đồng, không gọi `draw_panel_overlays`. Bốn đột biến hợp đồng đỏ. Điểm yếu nhỏ: THẤP-1, THẤP-2. |
| 2 | Tự chạy lại test | PASS | Xem bảng trên: `Ran 43 OK`, `Ran 30 OK`; m10/m11 đỏ khớp coder. |
| 3 | Test không sửa/skip/nới | PASS | `git diff --numstat 95598eb..cf5e2cc`: `tests/test_level1_display.py 117 0`, `docs/plans/15-progress.md 33 6` — chỉ 2 file, 0 dòng xóa trong test, không `skip` mới (`grep skip tests/test_level1_display.py` rỗng). agy-guard `_work/agy_logs/20261009-011321-15-lan-sua-13b.log` dòng 72–73: `các commit của agy: sạch`, `working tree: sạch`; không `BLOCK`. Log `20261009-011303-…` chỉ có snapshot + cổng hạn mức (lần khởi động hỏng/bị thay, không commit). |
| 4 | Nguồn gốc dữ liệu | PASS (không áp dụng) | Ảnh tổng hợp đặc (90/40) chỉ để kiểm hình học hiển thị; không train/đánh giá. |
| 5 | Rò rỉ split | PASS (không áp dụng) | — |
| 6 | Chọn model bằng VAL | PASS (không áp dụng) | Không đổi model; sha checkpoint `160e0c68…` coder khai, `src/` không đổi. |
| 7 | Số liệu truy được | PASS | Không số liệu khoa học. `Ran/FAILED` trong 15-progress khớp log (grep ở trên). Span 29/15 = 1.9333 là chi tiết test, không phải kết quả. Sổ `docs/agy_usage_ledger.csv` có dòng `2026-10-08T18:40Z,gemini,gemini-3.8-flash-high,high,docs/plans/15-lan-sua-13b.md,…,ok`; không dùng làm kết luận. |
| 8 | Cỡ mẫu / CI | PASS (không áp dụng) | — |
| 9 | Nhất quán train–realtime | PASS | Không đổi `src/`, `level1_demo.py`; `git diff 95598eb..cf5e2cc -- src/ level1_demo.py` rỗng; E3Spy/E4 xanh trong log reviewer. |
| 10 | Không mock/kết quả giả | PASS | Không có trong đường chính; test chỉ dựng panel builder giả theo đúng hợp đồng §5. |
| 11 | Bảo mật / phạm vi | PASS | Hai file ⊆ khối ```scope §5b và ⊆ "U2a chỉ test_level1_display + progress". Không đụng README.md / 3 file ` D` / untracked của người dùng. origin `0570c2b` là tổ tiên của `95598eb`, `git branch -r --contains cf5e2cc` rỗng ⇒ agy không push. Không thấy `--no-verify`: hook chạy qua `core.hooksPath` env của `scripts/agy_code.sh:95-98`, guard sau chạy sạch (dòng hook `pre-commit: sạch` không được lưu vào log — UNVERIFIED trực tiếp, guard bù). `STATUS: DONE` (dòng 70) khớp thực tế: 1 commit `^15: L13-U2a `, test xanh. |
| 12 | So sánh công bằng / không nới GATE | PASS | Dung sai S3 [1.6, 2.4] và ngưỡng 8/kênh y nguyên hợp đồng (planner chốt trước). |
| 13 | Kết luận vượt bằng chứng | PASS (kèm THẤP-2) | "Bằng chứng bắt lỗi hoàn tất" đúng cho m9–m12; không đúng cho mọi lỗi co giãn của dòng thống kê (rA, rB sống). |

## Vấn đề

### CAO — không có. ### TB — không có.

### THẤP
- **THẤP-1** `tests/test_level1_display.py:475,485`: `np.all(bar == …)` trên lát cắt có thể rỗng (luôn `True` nếu `scaled_px(3,s)` hay `cw` = 0); test không khẳng định `bar.size > 0` cũng không khẳng định `L.scale` mong đợi (≈1.588 / 2.0; S3 `:539,547` không kiểm `L_nat.scale == 1`, `L_2.scale == 2`). Hiện vô hại (s ≥ 1, `fit_layout` có test riêng ở AC-U1), nhưng là assertion có thể xanh rỗng nếu `fit_layout` hồi quy.
- **THẤP-2** Điểm mù ngoài hợp đồng (đột biến reviewer sống): rA — nét chữ thống kê không co giãn (`thickness = STATS_THICKNESS`) và rB — lề đáy không co giãn (`STATS_BOTTOM_MARGIN` thay `scaled_px(...)`) đều `OK`. Không phải lỗi coder (AC-U7 không đòi); planner có thể thêm ở U2c nếu muốn khóa (vd. vị trí hàng đáy của D ≈ `py+ph−scaled_px(10,s)` ± dung sai).
- **THẤP-3** `tests/test_level1_display.py:544,552`: khi không có pixel chữ, `rows.max()` ném `ValueError` (m9 cho `errors=1` thay vì failure). Vẫn đỏ, nhưng thông điệp kém; nên `assertGreater(len(rows), 0)` trước.
- **THẤP-4** Quy trình/ghi chép: AC-U7m đòi worktree "tại commit U2a"; coder chạy ở `95598eb` + chép file test (15-progress khai sha256 `a7f9922f…`, reviewer xác nhận `git show cf5e2cc:tests/test_level1_display.py | sha256sum` trùng; `src/` giống hệt) ⇒ tương đương, reviewer đã chạy lại đúng tại `cf5e2cc`. `docs/plans/15-progress.md:8` còn dòng cũ "ĐANG LÀM: U2a — hoàn tất commit và báo cáo U2a." (lỗi thời sau commit).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có.
