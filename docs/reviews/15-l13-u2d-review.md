# Review U2d — lần sửa 13b (đo chi phí hiển thị, AC-U5 / gate DC1)

Reviewer độc lập, 2026-10-09. HEAD lúc review `384aa9e`. Phạm vi: `fddba5a` (code, agy Gemini), `57395ff` (sổ agy),
`abdcf39` (JSON do cầu nối chạy). Hợp đồng: `docs/plans/15-lan-sua-13b.md` §4 hàng U2d, §5 (AC-U5, AC-U9, AC-U9b, AC-U2P), §5b, §6, §7;
gốc `docs/plans/15-lan-sua-13.md:409-410`.

**Kết luận: CHANGES_REQUESTED** — 0 CAO, 2 TB, 7 THẤP. Kết luận DC1 (pass) TÁI LẬP được; lỗi nằm ở chỗ harness có thể báo
pass khi không có dữ liệu, và nhãn đường vẽ trong JSON được hard-code, không khớp với lần đo.

## Lệnh reviewer đã chạy (log trong `_work/_plan15_l13/`)

| Lệnh | Kết quả |
|---|---|
| `PY -m unittest tests.test_level1_display_cost tests.test_level1_display` → `review_u2d_tests.log` | `Ran 38` — `OK` (coder khai Ran 38 OK: khớp) |
| Bộ AC-U2P (`tests/test_level1_*.py` + `tests.test_backend_source_guard`) → `review_u2d_level1_all.log` | `Ran 515` — `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` (U2c 507 + 8 test mới = 515) |
| `PY scripts/level1_display_cost.py --out _work/_plan15_l13/review_u2d_rerun.json` (tại 384aa9e, code sạch) → `review_u2d_measure.log` | `DC1 pass=True ratio=1.1162767673138354`; natural n=72 p50 31.31 ms; 1080p n=74 p50 34.95 ms |
| Probe chạy từ cwd `_work/` (đếm `Hud.compose` / `render_to_window`, lấy chặng `hud` / `mediapipe`), 2 lặp → `review_u2d_probe.log` | xem TB-2 và mục cần planner |
| `build_report(...)` với n=0, p50=0 cho cả hai lần; `dc1_gate(compute_ratio(0.0, 500.0))` | cả hai trả `pass: True` (TB-1) |
| `--clip nope.mp4` → `review_u2d_badclip.log` | `SourceError: video not found`, exit 1, không ghi JSON (đúng) |
| AC-U9 (lệnh nguyên văn §5) | `0` |
| `git diff --stat d1a8308..HEAD -- src/` | rỗng |
| AC-U9b (lệnh nguyên văn §5, mốc U2b `b0cbcf1`) | `0` |
| `git diff --numstat 4d95f73..HEAD` | chỉ thêm dòng; tests/: chỉ `tests/test_level1_display_cost.py` +219/-0; không `skip` mới |
| `sha256sum checkpoints/alphabet_best.pt` | `160e0c68…` (không đổi) |
| `git diff fddba5a 57395ff --name-only` | chỉ `docs/agy_usage_ledger.csv` ⇒ JSON ghi commit `57395ff` có code giống hệt `fddba5a`: CHẤP NHẬN |

Các lần đo DC1 hiện có (cùng lệnh, cùng code, chỉ khác tải máy):

| Lần | natural n / p50 (ms) | 1080p n / p50 (ms) | ratio_p50 | pass |
|---|---|---|---|---|
| Cầu nối, JSON đã commit `abdcf39` | 35 / 110.73 | 34 / 111.49 | 1.007 | true |
| Cầu nối, `_work/_plan15_l13/u2d_rerun.json` | 35 / 100.60 | 35 / 104.98 | 1.044 | true |
| Reviewer, `review_u2d_rerun.json` | 72 / 31.31 | 74 / 34.95 | 1.116 | true |
| Reviewer probe lặp 0 / lặp 1 | 72 / 30.94; 73 / 31.20 | 74 / 34.75; 74 / 35.10 | 1.123; 1.125 | true |

## Bảng 1–13

| # | Mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch | PASS (kèm THẤP-1) | Script chạy app cùng tiến trình trên clip D2 `--pace realtime`, recorder tự cài (không import tests/), 2 lần natural rồi 1920×1080 (`scripts/level1_display_cost.py:159-182`, `:221-222`); JSON đủ khóa AC-U5 (command, commit, clip, n_frames, p50/p90, ratio_p50, gate DC1/1.25/pass, note, python, cv2, thêm code_dirty). Test kiểm thật: biên 1.25 pass / 1.2501 fail (`tests/test_level1_display_cost.py:55-71`), CLI ghi JSON khi vá `measure`, docstring "chuỗi tạo có kiểm soát để kiểm logic" (`:3`). Thiếu artefact AC-U2P `u2d_green_level1_all.log` và số AC-U9b trong progress — reviewer chạy bù, xanh. |
| 2 | Tự chạy lại test | PASS | Ran 38 OK; Ran 515 OK (skipped=1), DoD7 known=9 allowed=36. |
| 3 | Test không bị sửa/skip/nới | PASS | numstat tests/: chỉ file mới, 0 dòng xóa; 0 `skip` mới. agy: `[agy-guard] các commit của agy: sạch`, `working tree: sạch` (`_work/agy_logs/20261009-143022-15-lan-sua-13b.log:451-452`; `_work/_plan15_l13/u2d_agy_run.log:7-8`, `:47-48`); không có `BLOCK`. Không cài hook pre-commit (`.git/hooks` chỉ có mẫu) nên kiểm `--no-verify` không áp dụng. Log đỏ `u2d_red.log` (14:39:38, ImportError do chưa có script) có mtime nhỏ hơn log xanh `u2d_green_cost.log` (14:40:42), cùng cây chính. |
| 4 | Nguồn gốc dữ liệu | PASS | Đo trên video thật `data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4` + MediaPipe thật; chuỗi tổng hợp chỉ có trong test và được ghi rõ. Không có dữ liệu mới. |
| 5 | Rò rỉ split | N/A | Không train/đánh giá model. |
| 6 | VAL/TEST | N/A | Không chọn model. |
| 7 | Số liệu truy được | PASS | JSON `abdcf39` có `command`, `commit` 57395ff (code = fddba5a), `code_dirty: false`; reviewer chạy lại cùng lệnh ra cùng kết luận. Sổ agy: dòng mới `2026-10-09T07:46Z,gemini,gemini-3.8-flash-high,high,...,stale` (`57395ff`) — không dùng làm số khoa học. |
| 8 | Cỡ mẫu / khoảng tin cậy | PASS (kèm TB-2, THẤP-3) | Mỗi lần đo 1 lượt, n=34–74 khung, không có CI; ratio dao động 1.007–1.125 qua 5 lần theo tải máy. Kết luận pass vững (mọi lần ≤ 1.125 < 1.25), nhưng con số 1.007 trong commit `abdcf39`/STATE không đại diện cho chi phí hiển thị (đo khi MediaPipe ~100–110 ms/khung; n=35 vì chế độ paced bỏ khung khi chậm). |
| 9 | Nhất quán train–realtime | PASS | Script không chạm đường khung vào MediaPipe; AC-U9b = 0; `src/` không đổi; `level1_demo.py` không đổi trong U2d. |
| 10 | Không kết quả giả / hard-code | **FAIL** | TB-1: gate pass khi không có dữ liệu (`scripts/level1_display_cost.py:53-55` trả `0.0` nên `dc1_gate` pass; `:42-43` n=0 cho p50 0.0); test khóa hành vi này (`tests/test_level1_display_cost.py:53`). TB-2: `path` mỗi lần là chuỗi hard-code (`scripts/level1_display_cost.py:81`, `:86`), không đo; probe cho thấy lần natural có 2/72 khung đi `render_to_window`. |
| 11 | Bảo mật / phạm vi / agy | PASS (kèm THẤP-6) | File đổi nằm trong khối scope §5b (cộng docs/STATE.md, các sổ, review là việc orchestrator); không token/kaggle.json; clip không bị commit. Không push: `origin/cloud/2026-10-04-level1-rearm` = `e520e22`, `git branch -r --contains fddba5a` rỗng. agy báo `STATUS: DONE`, khớp git (đúng 1 commit `15: L13-U2d ...`, test xanh); agy không tuyên bố đã đo hay đã push. |
| 12 | So sánh công bằng / GATE | PASS (kèm THẤP-3) | Ngưỡng 1.25 và định nghĩa trên `frame_total` đúng `docs/plans/15-lan-sua-13.md:409-410` và `docs/plans/15-lan-sua-13b.md:102-106`, đặt trước khi đo; hai lần cùng clip, cùng tiến trình; thứ tự cố định theo kế hoạch. |
| 13 | Kết luận vượt bằng chứng | PASS (kèm TB-2, mục cần planner) | Note JSON "lần natural đo đường Hud.compose cũ" đúng cho ~97% khung, không phải mọi khung; "ratio 1.007" chỉ là một lần đo khi máy tải nặng. DC1 chỉ cho biết chi phí hiển thị nhỏ so với tổng khung, không phải chi phí vẽ riêng. |

## Vấn đề

### CAO
Không có.

### TB
- **TB-1 — Gate DC1 "fail-open" khi không có dữ liệu.** `scripts/level1_display_cost.py:42-43` trả `p50 = 0.0` khi chuỗi rỗng;
  `:53-55` trả `ratio = 0.0` khi `p50_natural <= 0`; `dc1_gate(0.0)` cho `pass: true`. Đã chạy: `build_report` với n=0, p50=0 cho cả hai lần
  cho `gate.pass = True`; `dc1_gate(compute_ratio(0.0, 500.0))` cho `pass = True`. `tests/test_level1_display_cost.py:53` khóa `compute_ratio(0.0, 12.0) == 0.0`.
  Sửa: n=0 ở lần nào hoặc `p50_natural <= 0` thì `pass: false` (hoặc thoát mã khác 0, không ghi JSON) kèm lý do; đổi kiểm ở `:53` theo hành vi mới
  và thêm ca n=0 không pass (file test mới của chính U2d, không phải test cũ).
- **TB-2 — Nhãn đường vẽ hard-code, không khớp đo thật; JSON không đủ để diễn giải DC1.** `path` (`:81`, `:86`) và note (`:28-31`) khẳng định
  lần natural đi `Hud.compose`; recorder natural trả rect theo shape `imshow` gần nhất (`:149-155`), nên khi chiều cao panel đổi, khung đó đi
  `render_to_window` (ghi chú (c) của cầu nối là đúng). Probe reviewer (`_work/_plan15_l13/review_u2d_probe.log`): lặp 0 natural `compose 70, rtw 2`;
  lặp 1 `compose 73, rtw 0`; 1080p `rtw 74` cả hai lặp. Ảnh hưởng lên p50 nhỏ, nhưng JSON đang ghi một khẳng định chưa đo. Sửa (không đổi gate, không
  sửa app): đếm số lần gọi `Hud.compose` / `render_to_window` mỗi lần bằng `mock.patch.object` (không dùng mẫu cấm AC-U9) và ghi `path_counts` thay
  chuỗi cố định; ghi thêm (thông tin, không phải gate) p50 chặng `hud` và `mediapipe` mỗi lần từ `app.times`. Sau khi sửa: commit code
  `15: L13-U2d ...`, chạy lại lệnh đo khi máy rảnh, commit JSON riêng.

### THẤP
- **THẤP-1** AC-U2P: không có `_work/_plan15_l13/u2d_green_level1_all.log`; progress ghi "AC-U9, AC-U9b" nhưng chỉ có lệnh và số AC-U9
  (`docs/plans/15-progress.md`, mục "Lần sửa 13b — U2d", các dòng cuối). Reviewer đã chạy bù: Ran 515 OK (skipped=1), AC-U9b = 0. Prompt cầu nối gửi
  agy cũng không yêu cầu bước này.
- **THẤP-2** Progress ghi mtime `u2d_green_display.log` 14:41:34, thực tế 14:41:45 (không ảnh hưởng thứ tự đỏ trước xanh).
- **THẤP-3** Mỗi điều kiện chỉ đo 1 lượt, thứ tự cố định (natural luôn trước; lần 1080p có thể hưởng bộ nhớ đệm ấm); không lặp xen kẽ, không CI.
  Kết luận pass vẫn vững (5/5 lần), nhưng nên chạy ≥ 3 cặp xen kẽ nếu DC1 được dẫn trong báo cáo.
- **THẤP-4** `--clip` tương đối được hiểu theo gốc repo, không theo cwd người gọi, vì `os.chdir(ROOT)` trước `app.run()` (`:165-166`). Ghi chú (b)
  của cầu nối: dựng `Level1App` trước `chdir` KHÔNG gây lỗi (config/checkpoint qua `resolve_path`, `level1_demo.py:697-702`; clip mở trong `run()` sau
  `chdir`); probe chạy từ cwd `_work/` xong bình thường.
- **THẤP-5** Mã thoát luôn 0 kể cả khi gate trượt (`:245`, khóa ở test `:192-219`) — theo prompt cầu nối, nhưng §7 đòi "trượt thì DỪNG"; người chạy phải
  đọc dòng `DC1 pass=`. Nên thoát khác 0 khi gate trượt, hoặc ghi rõ trong docstring.
- **THẤP-6** `command` trong JSON chứa đường dẫn tuyệt đối `C:\Users\Admin\...\python.exe` (lộ tên tài khoản máy, không phải bí mật); nên ghi dạng tương đối.
- **THẤP-7** Test recorder (`tests/test_level1_display_cost.py:133-150`) chỉ kiểm panel không đổi chiều cao; không kiểm ca chiều cao panel đổi (ca gây TB-2).
  Không có test chạy `measure()` thật (chấp nhận được: §5 không đòi dữ liệu thật trong test).

## Trả lời các ghi chú của cầu nối
- (a) DC1 còn ý nghĩa không: `frame_total` = MediaPipe + segmenter + hud + display; với imshow vá, `display` p50 ≈ 0.006 ms, nên
  ratio ≈ 1 + Δhud / frame_total(natural). Probe: chặng `hud` natural p50 2.42 / 2.48 ms, 1080p 5.85 / 6.16 ms (×2.42 / ×2.49, Δ ≈ 3.5 ms);
  MediaPipe p50 ≈ 27.5 ms khi máy rảnh. Lần cầu nối (p50 khung ~100–110 ms) cho ratio 1.007 / 1.044; máy rảnh cho ~1.12. DC1 vẫn đúng như kế hoạch
  định nghĩa (chi phí hiển thị so với cả khung) và vẫn pass, nhưng không đo chi phí vẽ riêng, và ratio phụ thuộc tải máy. Không được đổi gate sau khi
  thấy kết quả; xem mục dưới.
- (b) Không lỗi khi chạy từ thư mục khác (đã chạy thử); chỉ còn THẤP-4.
- (c) Đúng: 2/72 khung natural đi `render_to_window` ở một lượt (TB-2).

## CẦN NGƯỜI DÙNG / PLANNER QUYẾT ĐỊNH
- DC1 trên `frame_total` bị pha loãng bởi MediaPipe và tải máy: riêng chặng `hud` chậm ~2.4–2.5× ở 1920×1080 (Δ ≈ 3.5 ms trên máy này). Gate DC1
  KHÔNG được đổi sau khi thấy kết quả. Planner quyết định có (i) ghi p50 `hud` vào JSON như số thông tin (TB-2 đề xuất) và (ii) thêm câu Giới hạn ở R2:
  "DC1 đo chi phí hiển thị so với tổng khung với imshow vá; riêng chặng vẽ tăng ~X ms; không đo chi phí vẽ cửa sổ HĐH". Không trích "ratio 1.007" như
  chi phí hiển thị.
