# Kế hoạch 15 — LẦN SỬA 13e: gỡ mâu thuẫn hợp đồng G2b (AC-G5 xóa `GESTURE_BACKSPACE_FLASH` vs test M0 `_hud_module_at("cad8cdc")`)

Bổ sung cho `docs/plans/15-lan-sua-13d.md` (không thay). Chỉ đổi hợp đồng G2b ở đúng 1 điểm: một ngoại lệ CHỈ THÊM dòng trong `tests/test_level1_display.py`.
Mọi AC khác của 13d §5 (AC-G4, AC-D7, AC-D8, AC-G5 phần grep đủ 5 tên, chung AC-0/AC-1) giữ NGUYÊN, không nới.

## 1. Mục tiêu

Hoàn tất G2b (xóa 5 hằng cử chỉ khỏi `src/`, mặc định đọc lười từ config) mà test bất biến M0 `test_u2_hud_scale_one_identical_to_m0_hud` (Hud scale 1 giống hệt
Hud của `cad8cdc`) vẫn chạy và vẫn so đúng cái nó so. DoD phục vụ: như 13d (Level 1 realtime: cử chỉ một nguồn config, truy vết được; không hồi quy HUD).

## 2. Hiện trạng / nguyên nhân gốc

- `tests/test_level1_display.py:57-71` `_hud_module_at(commit)`: `git show <commit>:level1_demo.py` rồi `exec` vào module trong bộ nhớ. Mã cũ đó chạy câu
  `from src.inference.level1_core import … GESTURE_BACKSPACE_FLASH …` trên `level1_core` HIỆN TẠI ⇒ sau G2b: `ImportError` (log coder
  `_work/_plan15_l13/g2b_green_level1_all.log`: `Ran 614` `FAILED (errors=1, skipped=1)`, chỉ lỗi này). Test dùng ở `:324-337`.
- Nguyên nhân gốc (lỗi kế hoạch 13d §2): chỉ grep người dùng TRỰC TIẾP của 5 hằng trong `tests/`, bỏ sót người dùng gián tiếp qua `git show` của commit cũ.
  Đây là phụ thuộc NHẬP (import) của ảnh chụp lịch sử, không phải phụ thuộc hành vi: `GESTURE_BACKSPACE_FLASH` chỉ dùng trong `Level1App` (`level1_demo.py:1160`,
  `:1528` hiện tại), không dùng trong lớp `Hud` mà test so.
- Mã G2b đã viết, chưa commit: `_work/_plan15_l13/g2b_wip.patch` (`level1_core.py` +51/−25, `level1_demo.py` +3/−3, `tests/test_level1_gestures.py` +204/−0); script
  đột biến `_work/_plan15_l13/g2b_mutate.py` (8 đột biến). Config: `configs/level1_gestures.json` `gesture_flash_ms.value` = 600 (= hằng cũ `600.0`).

## 3. Quyết định: chọn (a), có rào chắn

So sánh:
- (b) giữ `GESTURE_BACKSPACE_FLASH` + bỏ `FLASH` khỏi AC-G5 = hạ tiêu chí sau khi thấy kết quả, để lại một tên hằng cử chỉ trong `src/` chỉ vì một test của
  phần khác ⇒ LOẠI. Mọi biến thể giữ tên trong `src/` (module `__getattr__`, alias, ghép chuỗi) = né AC-G5 ⇒ LOẠI.
- Đổi `HUD_BASE_COMMIT` sang commit khác / tự chép Hud cũ vào test = đổi bất biến M0 ⇒ LOẠI.
- (a) cấp tương thích NHẬP cho ảnh chụp lịch sử, đặt trong bộ nạp `_hud_module_at`, tạm thời, chỉ cho tên đã bị xóa có chủ đích ⇒ CHỌN. Không che lỗi vì: phép so
  `Hud.compose`/`Hud._build` mới vs `cad8cdc` giữ nguyên từng dòng (`:324-337` không sửa); tên được cấp không tham gia đường vẽ Hud; giá trị cấp lấy từ chính nguồn
  thay thế (`gesture_defaults()["gesture_flash_ms"]`, ép `float`), không gõ số.

Ràng buộc của (a) (hợp đồng):
1. Sửa `tests/test_level1_display.py` CHỈ THÊM dòng (numstat cột xóa = 0), và chỉ ở 2 chỗ:
   - trong thân `_hud_module_at` (`:57-71`): sau `sys.modules[name] = mod` và trước `try:` — nhập `src.inference.level1_core`, với mỗi tên trong hằng mô-đun
     `M0_CORE_COMPAT_NAMES = ("GESTURE_BACKSPACE_FLASH",)` (khai báo mới, đặt cạnh `HUD_BASE_COMMIT`), CHỈ gắn nếu `level1_core` KHÔNG có thuộc tính đó, ghi lại danh
     sách đã gắn; trong `finally:` (thêm dòng sau `sys.modules.pop(...)`) `delattr` đúng các tên đã gắn. Giá trị: `float(level1_core.gesture_defaults()["gesture_flash_ms"])`.
     Docstring/ghi chú 1 dòng: "compat shim for names removed by plan 15 L13-G2b; import-only, not used by Hud".
   - 1 phương thức test MỚI trong lớp `TestRenderToWindowAcU2` (hoặc lớp mới cuối file) — xem AC-E2.
2. `M0_CORE_COMPAT_NAMES` có ĐÚNG 1 tên. Cần thêm tên nào khác ⇒ DỪNG, báo planner (không tự mở rộng).
3. Không sửa dòng nào khác của file; không thêm skip; `test_u2_hud_scale_one_identical_to_m0_hud` không sửa.
4. Không gắn khi tên đã có (ở HEAD trước G2b bộ nạp là no-op ⇒ hành vi cũ giữ nguyên).

## 4. Chia việc G2b còn lại (coder = vslt-coder-claude; quy ước `PY`, log `_work/_plan15_l13/`, `git commit -- <đường dẫn>` như 13d §4)

| # | Bước | Phụ thuộc | Giờ |
|---|---|---|---|
| 1 | Kiểm HEAD sạch với phạm vi (không đụng `README.md`, 3 file ` D`); `git apply --check` rồi `git apply _work/_plan15_l13/g2b_wip.patch`; `git diff --numstat` khớp 51/25, 3/3, 204/0. | — | 0,1 |
| 2 | Impact `_hud_module_at` (upstream; UNKNOWN ⇒ grep xác nhận chỉ `:326` dùng). Viết TRƯỚC test AC-E2 (bước 3 chưa có) ⇒ chạy `PY -m unittest tests.test_level1_display` ⇒ log đỏ `g2b_e_red.log` (mong đợi: lỗi `ImportError` của test u2 + test mới đỏ). | 1 | 0,3 |
| 3 | Thêm shim theo §3 ràng buộc 1; chạy lệnh AC-E3 ⇒ log xanh. | 2 | 0,3 |
| 4 | detect-changes; commit đúng 1 commit `15: L13-G2b …` gồm `level1_core.py`, `level1_demo.py`, `tests/test_level1_gestures.py`, `tests/test_level1_display.py`. | 3 | 0,1 |
| 5 | Đột biến trên worktree từ commit G2b: `git worktree add _work/_plan15_l13/wt_g2b <G2b>`; chạy `g2b_mutate.py` (8 đột biến cũ) + 2 đột biến AC-E4 với cwd = worktree; khôi phục, `cmp` khớp; `git worktree remove`. Log `g2b_mutate.log`. | 4 | 0,4 |
| 6 | Ghi tiến độ vào `docs/plans/15-progress.md` (mục G2b: hash, log đỏ/xanh, Ran, đột biến) — commit riêng hoặc commit tiến độ như các lần trước. | 5 | 0,1 |

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng; coder KHÔNG đổi)

Giữ nguyên toàn bộ AC G2b của 13d §5 (AC-G4, AC-D7, AC-D8, AC-G5 phần grep với đủ `COOLDOWN|WINDOW|MIN_DX|MIN_SPEED|FLASH`) và mục "Chung". Thêm:
- **AC-E1 (phạm vi sửa test cũ)** `git diff --numstat <HEAD trước G2b>..<G2b> -- tests/` cột xóa = 0 cho MỌI file; `git diff -U0 … -- tests/test_level1_display.py` chỉ có
  hunk `+` nằm trong: khối hằng đầu file (`M0_CORE_COMPAT_NAMES`), thân `_hud_module_at`, và 1 phương thức test mới. Dòng `:324-337` không đổi.
- **AC-E2 (shim đúng, sạch)** test mới (ví dụ `test_m0_ref_loader_compat_is_temporary`): (i) `M0_CORE_COMPAT_NAMES == ("GESTURE_BACKSPACE_FLASH",)`;
  (ii) gọi `_hud_module_at(HUD_BASE_COMMIT)` thành công; (iii) sau đó `hasattr(src.inference.level1_core, "GESTURE_BACKSPACE_FLASH")` là False;
  (iv) `ref_mod.GESTURE_BACKSPACE_FLASH == float(gesture_defaults()["gesture_flash_ms"])` và kiểu `float`;
  (v) tên này KHÔNG nằm trong `co_names` của `ref_mod.Hud.compose` và `ref_mod.Hud._build` (chứng minh không tham gia phép so Hud).
- **AC-E3 (lệnh)** `PY -m unittest tests.test_level1_display` ⇒ `OK` (gồm `test_u2_hud_scale_one_identical_to_m0_hud` không sửa);
  lệnh 13d G2b `PY -m unittest tests.test_level1_gestures tests.test_level1_core tests.test_level1_demo tests.test_level1_guard tests.test_backend_source_guard` ⇒ `OK`;
  toàn bộ `PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard` ⇒ `OK` (skip chỉ do thiếu dữ liệu, có tên file;
  `test_reset_segments_and_graphs` theo luật 3 lần chạy); `[DoD7-guard] known=9 allowed=36`; ghi số `Ran` thực tế từ log, không ước đoán.
  `grep -rnE "GESTURE_BACKSPACE_(COOLDOWN|WINDOW|MIN_DX|MIN_SPEED|FLASH)" src/ level1_demo.py` = 0 dòng.
- **AC-E4 (đột biến, trên worktree từ commit G2b)** 8 đột biến của `g2b_mutate.py` đều ĐỎ, cộng: (M9) bỏ dòng `delattr` trong `finally` ⇒ AC-E2 ĐỎ;
  (M10) đưa lại `GESTURE_BACKSPACE_FLASH = 600.0` vào `level1_core.py` ⇒ test grep AC-G5 ĐỎ. Mọi file khôi phục, `cmp` khớp bản commit.
- Đúng 1 commit mã `^15: L13-G2b`; `sha256sum checkpoints/alphabet_best.pt` bắt đầu `160e0c68` (không đổi).

## 5b. Phạm vi file

```scope
src/inference/level1_core.py
level1_demo.py
tests/test_level1_gestures.py
tests/test_level1_display.py
docs/plans/15-progress.md
```
`tests/test_level1_display.py`: chỉ theo §3 ràng buộc 1 / AC-E1. `level1_demo.py`: chỉ import + 2 chỗ dùng flash (như 13d). CẤM như 13d §5b
(`backend/main.py`, `README.md`, `configs/level1_realtime.json`, `src/data/`, `tests/test_backend_source_guard.py`, 3 file ` D` của người dùng).

Độ khó: M (mã đã viết; phần mới nhỏ); vùng nhạy cảm: có (`level1_core`, landmark/`aspect_points`, app realtime, bất biến HUD M0).

## 6. Rủi ro dữ liệu/ML

- Không đổi dữ liệu, split, model, đánh giá. Giá trị flash 600 ms giữ nguyên (config = hằng cũ) ⇒ không lệch train↔realtime.
- Rủi ro test: shim chạm module thật `level1_core` trong tiến trình test ⇒ phải gỡ trong `finally` (AC-E2 iii, đột biến M9); test chạy tuần tự nên không đua.
- Rủi ro che lỗi: nếu sau này Hud dùng tên bị xóa, shim sẽ cấp giá trị config — AC-E2 (v) chặn vì kiểm `co_names` của Hud ở `cad8cdc`.

## 7. Điểm dừng

Không có. Không đổi model mặc định, không cần dữ liệu người dùng, không đụng thay đổi chưa commit của người dùng, không hành động không hoàn tác (worktree tạm gỡ
sau bước 5). DỪNG báo planner nếu: cần thêm tên vào `M0_CORE_COMPAT_NAMES`, cần xóa/sửa dòng cũ trong `tests/`, hoặc bản vá không `apply --check` sạch trên HEAD.

## 8. Con trỏ cần chép (orchestrator chép; coder không sửa ngoài phạm vi)

- `docs/plans/15-lan-sua-13.md` (dưới dòng "LẦN SỬA 13d"):
  `> LẦN SỬA 13e (2026-10-09): xem docs/plans/15-lan-sua-13e.md — G2b chọn (a): shim nhập tạm "GESTURE_BACKSPACE_FLASH" CHỈ THÊM dòng trong _hud_module_at (tests/test_level1_display.py) + test AC-E2; AC-G5 giữ đủ 5 tên; đột biến M9/M10 trên worktree.`
- `docs/plans/15-progress.md` (cuối file):
  `> LẦN SỬA 13e (2026-10-09, planner): mâu thuẫn G2b gỡ theo (a) — shim tạm trong _hud_module_at, chỉ thêm dòng, AC-E1…E4; AC-G5 không nới; coder vslt-coder-claude áp g2b_wip.patch rồi làm 15-lan-sua-13e.md §4.`
