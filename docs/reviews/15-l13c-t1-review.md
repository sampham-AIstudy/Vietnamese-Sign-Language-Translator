# Review — lần sửa 13c, bước T1 (commit 235be2b, agy Gemini)

Reviewer độc lập, 2026-10-09. Hợp đồng: `docs/plans/15-lan-sua-13c.md` §4 hàng T1 (:94), AC-T1 (:204–217), AC-T1m (:219–225),
AC-P (:264–277), §5b (:279–296). Nguồn điểm mù: `docs/reviews/15-l13-u2a-review.md` THẤP-1/THẤP-2.
Mốc: `cb3ecad` → `235be2b`. HEAD lúc review: `c33b776` (sau T1 chỉ có commit state/ledger của orchestrator).

## Kết luận: CHANGES_REQUESTED (chỉ sửa tài liệu; phần test đạt)

Test mới đúng AC-T1, oracle độc lập, đột biến AC-T1m đều đỏ (đã chạy lại tại 235be2b). Lý do duy nhất không APPROVE:
`docs/plans/15-progress.md:13` (do commit T1 viết) trích hai commit hash KHÔNG tồn tại trong repo.

### TB-1 (phải sửa) — hash commit bịa trong progress
`docs/plans/15-progress.md:13`: `U2c (\`4f5da6b\`)` và `U2d (... + \`b7f7396\` C2)`.
`git log -1 4f5da6b` / `git log -1 b7f7396` ⇒ `fatal: ambiguous argument ... unknown revision`.
Hash thật: U2c = `00d320c` (+ sửa `6144970`); U2d = `fddba5a`, `abdcf39` (bản đầu), 13c C1 = `ea93fa1`, C2 = `44a9d69`.
Sửa: thay đúng hai hash này ở dòng 13 (tài liệu, không đụng test). Không cần chạy lại test hay đột biến; review lại chỉ dòng đó.

### THẤP-1 — đột biến không chạy đúng "tại commit T1"
`_work/_plan15_l13/t1_mutate.py` tạo worktree tại `HEAD` lúc 16:52 (= `cb3ecad`, `t1_base_head.txt`) rồi CHÉP file test từ cây làm việc;
commit T1 lúc 17:01. AC-T1m (:219) yêu cầu "tại commit T1"; progress không nêu sai lệch này. Đã khắc phục bằng chạy lại của reviewer
tại `235be2b` (bên dưới) — kết quả trùng. Ghi nhận cho T2: tạo worktree từ commit của bước.

### THẤP-2 — lưu ý thiết kế (không phải lỗi)
- S5 ca tự nhiên (s = 1.0) không phân biệt rA/rB (theo định nghĩa); khả năng bắt rA/rB dựa hoàn toàn vào 2 ca co giãn — đủ, vì cả 2 ca đều đỏ.
- `assertTrue(np.array_equal(...))` (tests/test_level1_display.py:642) cho thông báo lỗi nghèo (không có số pixel lệch); không ảnh hưởng tính đúng.
- Log `_work/agy_logs/20261009-164154-15-lan-sua-13c.log` chỉ 2 dòng (lần khởi chạy bị bỏ, 0 BLOCK); lần chạy thật là `20261009-164215-*`.

## Bảng kiểm 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|-----|---------|------------|
| 1 | Đúng kế hoạch, test kiểm thật | PASS | Lớp mới `TestU2OverlaysExactT1` tests/test_level1_display.py:568. 3 ca `subTest` (1920×1080, 1280×1360, tự nhiên `fit_layout(640,480,200)`) :575–579, view 90 / BG (40,40,40) :572,:582. P1 :587–616: `abs(s − min(W/640, H/680)) ≤ 0.01`, tự nhiên `s == 1.0`, `scaled_px(3,s) ≥ 1`, `cw>0`, `ph>0`, lát cắt H1 (`bar`) và H2 (`bar`, `rest`) trùng đúng lát cắt của `test_u7_h1/h2` (:475, :485, :487), `size>0`. S5 :618–642: `E = np.full((ph,cw,3), BG)`, `putText(E, line, (int(8*s), ph − int(10*s)), SIMPLEX, 0.45*s, (160,255,160), max(1,int(round(s))), LINE_AA)` — literal, không import hằng module (chỉ dùng `disp.fit_layout`, `disp.render_to_window`, `disp.scaled_px` cho lát cắt/bước dòng); so `np.array_equal` bit-identical, dung sai 0 đúng AC. Oracle không rỗng (E có chữ; canvas thiếu chữ ⇒ đỏ, xem m9). Không assertion luôn đúng. |
| 2 | Tự chạy lại test | PASS | `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_display -v` ⇒ `_work/_plan15_l13/review_t1_main.log`: `Ran 32 tests` `OK`, 2 test T1 `ok`. Khớp coder (`l13c_t1_green.log:41,43` Ran 32 OK). Level1 toàn bộ của orchestrator `t1_orch_level1_all.log:482,484` Ran 539 `OK (skipped=1)`, DoD7 `known=9 allowed=36`. |
| 3 | Test không bị sửa/skip/nới | PASS | `git diff cb3ecad..235be2b -- tests/`: 1 hunk @@ -564,6 +564,83 @@, +77/−0; 0 dòng `-`, 0 `skip`. File chỉ có LF (0 `\r`). agy: `_work/agy_logs/20261009-164215-15-lan-sua-13c.log:64-65` `[agy-guard] các commit của agy: sạch`, `working tree: sạch`; 0 `BLOCK` (cả `.agy.log`). Commit message khớp `^15: L13-U2t1 `. |
| 4 | Nguồn gốc dữ liệu | PASS (N/A) | Test tổng hợp ảnh pixel (view hằng 90, panel hằng 40) để kiểm hiển thị; không train/đánh giá model. |
| 5 | Rò rỉ split | PASS (N/A) | Không chạm dữ liệu/split. |
| 6 | Chọn model bằng VAL | PASS (N/A) | Không chọn model. |
| 7 | Số liệu truy được | FAIL | Số Ran/FAILED trong progress khớp log (`l13c_t1_mut_*.log`, grep `^(Ran|OK|FAILED)`). NHƯNG `docs/plans/15-progress.md:13` trích `4f5da6b`, `b7f7396` không tồn tại (TB-1). agy: sổ `docs/agy_usage_ledger.csv` có dòng `2026-10-09T10:02Z,gemini,gemini-3.8-flash-high,high,…15-lan-sua-13c.md,…,ok`, commit RIÊNG bởi orchestrator (`675f57b`), đúng THẤP-4 U2c; model/effort thật `t1_agy_run.log:4` `model=gemini-3.8-flash-high effort=high`. |
| 8 | Cỡ mẫu / CI | PASS (N/A) | Không có kết luận thống kê. |
| 9 | Nhất quán train–realtime | PASS (N/A) | Không đổi đường khung; `git diff --stat 93abb08..HEAD -- level1_demo.py src/` rỗng. |
| 10 | Không mock/giả trong đường chính | PASS | Chỉ thêm test; panel builder giả nằm trong test, đúng AC-U7. |
| 11 | Bảo mật / phạm vi | PASS | File commit T1 = {`tests/test_level1_display.py`, `docs/plans/15-progress.md`} ⊆ khối scope §5b và danh sách T1 (:293). Không đụng README.md, 3 file ` D`, untracked (git status sau review không đổi). Không push: `git merge-base --is-ancestor 235be2b origin/cloud/2026-10-04-level1-rearm` ⇒ không (origin = `e520e22`). Không có dấu hiệu `--no-verify` (log hook `pre-commit: sạch` dòng 44). |
| 12 | So sánh công bằng / GATE | PASS | Dung sai 0 (bit-identical) đúng AC-T1, không nới. Đột biến đúng định nghĩa: `t1_mutate.py` rA = `thickness = STATS_THICKNESS` (src :133), rB = `content.shape[0] - STATS_BOTTOM_MARGIN - …` (:135), m9–m12 khớp `15-lan-sua-13b.md:81-82`; mỗi thay thế `assert count == 1`. Log coder: base OK; rA, rB FAILED(2) chỉ ở S5 ca 1080p + 1280×1360; m9 FAILED(8, errors=1); m10 FAILED(2); m11 FAILED(3); m12 FAILED(5). Reviewer chạy lại trong worktree tạm `_work/_plan15_l13/wt_review_t1` tại `235be2b` (đã xóa + prune): base `OK`; rA `FAILED (failures=2)`; rB `FAILED (failures=2)`; m11 `FAILED (failures=3)` — log `_work/_plan15_l13/review_t1_mut_{base,rA,rB,m11}.log`; FAIL của rA/rB đúng `test_t1_s5_stats_exact_oracle` 2 ca co giãn. |
| 13 | Kết luận vượt bằng chứng | PASS | Progress khai "6 đột biến đều ĐỎ, base XANH" — đúng theo log; "chạy trong worktree … qua t1_mutate.py" đúng, nhưng không nêu worktree ở `cb3ecad` + test chép (THẤP-1). agy `STATUS: DONE` (log :62) khớp thực tế git/test; không báo "đã push". |

Mục 4 yêu cầu của orchestrator: 2 dòng `-` trong progress (`git diff cb3ecad..235be2b -- docs/plans/15-progress.md`) đều thuộc mục `## Trạng thái`
(dòng "Xong…Lần sửa 13" và "Còn lại…") — chỉ cập nhật trạng thái, đúng; nhưng dòng thay thế chứa TB-1.

## Việc phải sửa (theo mức)
1. TB-1: sửa `docs/plans/15-progress.md:13` — `4f5da6b` → `00d320c` (+`6144970`), `b7f7396` → `44a9d69`. Commit riêng (vd. `15: L13-U2t1 sửa hash progress`)
   hoặc orchestrator sửa trong commit state; không đụng file khác.
2. (THẤP-1, cho T2) worktree đột biến phải tạo từ commit của bước, không chép file từ cây làm việc.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH
Không có.

## Vòng 2 (commit d27e507): APPROVE

- `git show d27e507 --stat`: `docs/plans/15-progress.md` 1/1 (+1/−1), `docs/reviews/15-l13c-t1-review.md` +55/−0 (bản review vòng 1, giống hệt file trên đĩa).
- Diff dòng 13: chỉ đổi `4f5da6b` → `00d320c` + `6144970` (U2c), `b7f7396` → `44a9d69` (C2), thêm `T1 (\`235be2b\`)`; phần còn lại của dòng giữ nguyên.
- Mọi hash ở dòng 13 đều tồn tại (`git cat-file -t` ⇒ `commit`): 5a32cff, acdcf63, cf5e2cc, b0cbcf1, 00d320c, 6144970, ea93fa1, 44a9d69, 6be8815, 235be2b.
- Không đụng test hay mã; README.md, 3 file ` D` và các file untracked không bị chạm. TB-1 đã đóng; THẤP-1 vẫn là ghi chú cho T2. Không còn FAIL ⇒ mục 7 PASS.
