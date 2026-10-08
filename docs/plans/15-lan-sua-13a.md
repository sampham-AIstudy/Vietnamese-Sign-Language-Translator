# Kế hoạch 15 — LẦN SỬA 13a (bổ sung nhỏ cho `docs/plans/15-lan-sua-13.md`): ngoại lệ E4 — `cv2.resize` ảnh HIỂN THỊ trong `render_to_window`

Không có điểm dừng CẦN NGƯỜI DÙNG (xem §7).

Ngày lập: 2026-10-08. Nhánh `cloud/2026-10-04-level1-rearm`, HEAD lúc lập `e66d20b` (U1 ở `ea9c645`).
Hiệu lực: THAY phần mâu thuẫn của `15-lan-sua-13.md` ở §5.4 (thêm ngoại lệ E4), AC-0/AC-V4 (numstat) và AC-U6 (câu "E3 xanh không sửa").
Mọi phần khác của lần sửa 13 giữ nguyên.

Tên gọi: "E1/E2/E3" trong §5.4 của lần sửa 13 là danh sách NGOẠI LỆ SỬA TEST; "E3" trong `tests/test_level1_equivalence.py` là TEST TƯƠNG ĐƯƠNG
(AC-E3 của kế hoạch 15 gốc, B4). Ngoại lệ mới trong tài liệu này là ngoại lệ sửa test thứ tư ⇒ gọi là **E4**; nó sửa test tương đương E3.

## 1. Mục tiêu và DoD

Gỡ mâu thuẫn trong kế hoạch: §2.2 + AC-U2 bắt `render_to_window` (`src/inference/level1_display.py`) dùng `cv2.resize`, còn test tĩnh
`TestEquivalenceE3Static.test_e3_no_hands_resize_flip_outside_display` cấm MỌI `resize` trong `src/inference/level1_*.py`, và AC-U6 đòi E3 xanh
không sửa. Cho phép đúng một lời gọi `cv2.resize` trên ảnh HIỂN THỊ, đồng thời siết thêm phần kiểm để bất biến của E3 vẫn đứng.
Phục vụ: DoD hạng mục 5 (giao diện demo co giãn, `15-lan-sua-13.md` §2) và AC-1 (hồi quy xanh), không nới bất biến train ↔ realtime (AC-E3 gốc).

## 2. Hiện trạng (HEAD `e66d20b`)

- `tests/test_level1_equivalence.py`
  - `:16-18` docstring E3: "never call Hands(...) or cv2.resize, and cv2.flip only inside display_view".
  - `:235-252` `_calls(tree)` → `(tên gọi đầy đủ, tên thuộc tính/tên hàm, hàm bao gần nhất)`; chỉ nhận `cv2.x(...)` (Attribute trên Name) và `x(...)`.
  - `:255-257` `E3_FILES` = `level1_demo.py` + glob `src/inference/level1_*.py` ⇒ đã gồm `level1_display.py`.
  - `:266-277` test tĩnh: `:272` cấm `Hands`; **`:273` cấm mọi `resize`**; `:274-277` `cv2.flip` chỉ trong `display_view`, đúng 1 ở `level1_demo.py`
    (mẫu ngoại lệ có sẵn).
  - `:279-286` tự kiểm `_calls`.
  - `:289-313` `TestEquivalenceE3Spy` (động): khung đưa vào `HandLandmarkSession.process` LÀ đúng đối tượng reader trả về (`is`), chế độ
    `--headless` và `--pace realtime` — đều KHÔNG có cửa sổ, nên chưa chạy qua đường `render_to_window`.
  - Điểm yếu sẵn có (không do U1): `from cv2 import resize as r`, `import cv2 as c`, `f = cv2.resize; f(...)`, `getattr(cv2, "resize")` lọt
    qua `_calls`. Grep tại HEAD: `level1_demo.py` + `src/inference/level1_*.py` KHÔNG có `from cv2`, `import cv2 as`, `getattr(cv2`,
    `warpAffine`, `warpPerspective`, `remap(`, `pyrDown`, `pyrUp` ⇒ siết các điểm này không làm đỏ mã hiện có.
- `src/inference/level1_display.py`
  - `:12-16` import: `dataclasses`, `typing`, `cv2`, `numpy` (không mediapipe, không `src.*`).
  - `:140-164` `render_to_window(view_bgr, panel_builder, stats_lines, hold_progress, layout)`: `:149` tạo `canvas` mới; `:154-157` nếu cỡ
    view đã đúng ô camera thì chép, ngược lại `cv2.resize(view_bgr, (width, cam_h), interpolation=cv2.INTER_LINEAR)` — lời gọi `resize`
    DUY NHẤT của file.
- Log đỏ: `_work/_plan15_l13/u1_green_level1_all.log` — `Ran 480`, `FAILED (failures=1, skipped=1)`; FAIL duy nhất
  `test_e3_no_hands_resize_flip_outside_display [src/inference/level1_display.py]`: `[('cv2.resize', 'resize', 'render_to_window')] != []`.
  Đỏ từ WIP agy `7ae0040`; xanh ở `cad8cdc` (M0) — theo ghi chép U1 trong `docs/plans/15-progress.md`.
- Review cầu nối U1: `docs/reviews/15-l13-u1-bridge.md` (8 điểm về fit_layout/panel/test yếu/chép Hud) — không nói tới E3; vslt-reviewer chưa
  review U1.
- App CHƯA gọi `render_to_window` (nối app = U2).

## 3. Thiết kế — quyết định của planner

### 3.1 Quyết định: ĐỒNG Ý ngoại lệ E4 (có siết thêm)
Bất biến E3 cần giữ: **khung đưa vào MediaPipe (đường trích landmark) là đúng khung reader trả về, không resize/lật/sửa** — để đầu vào live giống
hệt trích xuất offline lúc train. `render_to_window` làm việc trên ảnh HIỂN THỊ đã vẽ landmark + lật gương (sau `display_view`), sau khi
MediaPipe đã xử lý khung; nó không thuộc đường suy luận. Vì vậy cho phép resize ở đó không chạm bất biến, NẾU kiểm chứng được 3 điều:
(a) đúng một lời gọi, đúng chỗ, trên đúng tham số ảnh hiển thị; (b) module hiển thị không có đường tới MediaPipe/landmark; (c) khi app chạy ở
chế độ CỬA SỔ (đường có resize), khung vào `process` vẫn là đúng đối tượng reader trả về.

Phương án bị loại:
- Chuyển resize sang file ngoài glob `level1_*.py` (vd. `src/inference/display_render.py`): là lách bộ quét bằng đổi tên file — làm yếu guard
  (file mới không bị quét gì), trái §10 lần sửa 13 (tên file đã chốt). Loại.
- Thay `cv2.resize` bằng `warpAffine`/nội suy numpy: lách tên hàm, cùng tác dụng. Loại (và nay bị cấm tường minh, §3.2).
- Nới `:273` thành "cho phép resize trong mọi hàm hiển thị": quá rộng. Loại.

### 3.2 Hợp đồng ngoại lệ E4 (đóng — không mở rộng cho hàm/file/lời gọi khác)
Thay đổi tiêu chí này do PLANNER quyết TRƯỚC khi có kết quả xanh của E3 (E3 hiện ĐỎ ở `ea9c645`); lý do: mâu thuẫn nội bộ của kế hoạch
(§2.2/AC-U2 vs AC-U6), không phải để test dễ qua.

E4 cho phép DUY NHẤT: trong `src/inference/level1_display.py`, danh sách lời gọi tên `resize` (theo `_calls`) ==
`[("cv2.resize", "resize", "render_to_window")]` — đúng 1 phần tử. Mọi file khác trong `E3_FILES`: vẫn `[]`. Không đổi: cấm `Hands`,
luật `cv2.flip` chỉ trong `display_view` (đúng 1 ở `level1_demo.py`), `TestEquivalenceE3Spy`, `TestEquivalenceE1`.

Siết thêm (bù cho ngoại lệ, áp cho MỌI file trong `E3_FILES`), tất cả qua một hàm thuần `_e4_violations(rel, source) -> list[str]`
(rỗng = hợp lệ) đặt trong `tests/test_level1_equivalence.py`:
1. `render_to_window` trong `level1_display.py`: định nghĩa đúng 1 lần, ở MỨC MODULE (phần tử của `tree.body`), không có hàm lồng nào
   khác tên `render_to_window` ở bất kỳ file nào của `E3_FILES`; nút Call `cv2.resize` nằm trong khoảng dòng `lineno..end_lineno` của nó.
2. Lời gọi E4: đối số vị trí thứ nhất là `ast.Name` có id == tên tham số thứ nhất của `render_to_window` (hiện `view_bgr`); đúng 2 đối số
   vị trí; keyword ⊆ `{"interpolation"}` (không `dst` — chặn ghi đè vào mảng khác).
3. Không bí danh/lách tên: không `ImportFrom` có module `cv2` hoặc bắt đầu `cv2.`; mọi `import cv2` có `asname is None`; không Call
   `getattr` có đối số thứ nhất là `Name("cv2")`; mọi nút `Attribute` có `value == Name("cv2")` và `attr ∈ {"resize", "flip", "warpAffine",
   "warpPerspective", "remap", "pyrDown", "pyrUp"}` phải là `func` của một Call (không tham chiếu trần như `f = cv2.resize`); không Call nào
   tới `cv2.warpAffine`, `cv2.warpPerspective`, `cv2.remap`, `cv2.pyrDown`, `cv2.pyrUp`.
4. `level1_display.py` chỉ hiển thị: tập tên module gốc được import ⊆ `{"__future__", "dataclasses", "typing", "math", "cv2", "numpy"}`;
   không Call có thuộc tính `process`; không xuất hiện Name/Attribute `HandLandmarkSession`, `mediapipe`, `Hands`. (Nếu U2 cần import khác
   cho module này ⇒ DỪNG, báo planner — không tự nới.)

Phần động (giới hạn của kiểm tĩnh: không bắt được resize bằng phép numpy thuần như cắt bước `[::2]`/`np.repeat` — phần này do kiểm động khóa):
5. `render_to_window` không sửa đầu vào: sau lời gọi, `view_bgr` `array_equal` bản chép trước khi gọi, và `np.shares_memory(out, view_bgr)`
   False — ở layout tự nhiên (nhánh chép) và layout 1920×1080 (nhánh resize).
6. (Bước U2, bổ sung cho AC-U6) App ở chế độ CỬA SỔ, recorder vá `getWindowImageRect → (0, 0, 1920, 1080)`, chạy clip của `TestEquivalenceE3Spy`
   với `RecordingSession` + `SpyReader`: số khung vào `process` == số khung đọc (hoặc, nếu cửa sổ đi qua nhánh paced, cùng luật thứ tự như
   `test_e3_paced_frame_is_object_read`) và mọi khung vào `process` LÀ (`is`) đối tượng reader trả về; ít nhất 1 ảnh `imshow` có shape
   (1080, 1920, 3) (chứng minh đường resize đã chạy trong lần đo). Skip chỉ khi thiếu dữ liệu, cùng `_MISSING`/`SKIP_REASON` của E3 spy.

### 3.3 Sửa ở dòng có sẵn (danh sách đóng, thêm vào §5.4 của lần sửa 13 thành E4)
`tests/test_level1_equivalence.py`:
- `:273` (bắt buộc): thay bằng nhánh — `rel == "src/inference/level1_display.py"` ⇒ danh sách `resize` == `[("cv2.resize", "resize",
  "render_to_window")]`; ngược lại == `[]`. Hằng tên file/bộ ba đặt ở mức module (dòng MỚI), có chú thích "ngoại lệ E4 — 15-lan-sua-13a".
- `:16` (tùy chọn, chỉ docstring): thêm "except the single E4 display resize (plan 15-lan-sua-13a)"; `:17-18` có thể dàn lại dòng nếu cần.
Tổng dòng xóa của file này ≤ 3 (`:273` + tối đa `:16-17`... trong khối docstring `:16-18`). Mọi thay đổi khác là THÊM. Không đổi loại
assertion của test khác, không skip mới, không đổi `_calls` (chỉ được thêm hàm mới).

## 4. Chia việc

| # | Mã | Nội dung | Phụ thuộc | Giờ | Độ khó / model |
|---|---|---|---|---|---|
| 1 | U1a | (a) Viết TRƯỚC: lớp mới `TestEquivalenceE4Display` trong `tests/test_level1_equivalence.py` gồm `_e4_violations` + tự kiểm (§5 AC-E4c) + kiểm file thật; test không sửa đầu vào trong `tests/test_level1_display.py` (§3.2 mục 5). Chạy ⇒ log đỏ/xanh từng phần (`_e4_violations` chưa có ⇒ đỏ). (b) Sửa `:273` (+ docstring tùy chọn). (c) Thử đột biến (AC-E4d) trong worktree tạm. (d) Chạy AC-E4a/b + AC-1. (e) Ghi mục "Lần sửa 13a — U1a" trong `docs/plans/15-progress.md`. 1 commit `15: L13-U1a ngoại lệ E4 resize hiển thị`. | U1 (`ea9c645`) | 1,5 | S / **vslt-coder-claude** |
| 2 | — | Cầu nối xác minh độc lập U1a (chạy lại lệnh AC-E4a/b, xem diff `:273`, numstat). | 1 | — | — |
| 3 | — | **vslt-reviewer review U1 + U1a CÙNG LÚC** (`ea9c645` + commit U1a): 8 điểm của `docs/reviews/15-l13-u1-bridge.md` đã sửa đúng chưa + AC-U1–U3 + AC-E4. U1 riêng lẻ không thể đạt AC-1 nếu không có E4, nên review gộp. | 2 | — | — |
| 4 | U2 | Như `15-lan-sua-13.md` §8 #3, CỘNG thêm AC-U6b (§3.2 mục 6). AC-U6 đọc theo bản sửa ở §5 dưới đây. | 3 APPROVE | 1,5 | M (như cũ) |

Quy ước chung giữ §8 lần sửa 13: `python` = `PYTHONIOENCODING=utf-8 .venv/Scripts/python`; log `_work/_plan15_l13/`; `git commit -- <đường dẫn cụ thể>`
(KHÔNG stage `README.md`, 3 file ` D` của người dùng); impact trước khi sửa symbol có sẵn (`test_e3_no_hands_resize_flip_outside_display` là
test, ghi impact/ghi chú vào progress nếu GitNexus không giải được); `detect-changes --scope all` trước commit.

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder KHÔNG đổi; chỉ planner đổi kèm lý do)

Bản sửa tiêu chí của lần sửa 13 (lý do: §3.2):
- **AC-U6 (sửa)**: "E3 (`tests.test_level1_equivalence`) xanh; dòng có sẵn của file chỉ được đổi theo ngoại lệ E4 (§3.3 tài liệu này)" thay cho
  "xanh không sửa". Phần còn lại của AC-U6 giữ nguyên.
- **AC-U6b (mới, ở bước U2)**: §3.2 mục 6 — test mới (THÊM, ví dụ lớp mới trong `tests/test_level1_equivalence.py` hoặc `tests/test_level1_demo.py`)
  xanh, không skip trên máy có dữ liệu.
- **AC-0 / AC-V4 (sửa)**: thêm `tests/test_level1_equivalence.py` vào danh sách được xóa dòng: `git diff --numstat ea9c645..HEAD --
  tests/test_level1_equivalence.py` cột xóa ≤ 3, và `git diff ea9c645..HEAD -- tests/test_level1_equivalence.py` chỉ có dòng `-` nằm ở
  `:273` hoặc khối docstring `:16-18` của bản `ea9c645`. Mọi file test có sẵn khác: như cũ.

AC của U1a:
- **AC-E4a** `PY -m unittest tests.test_level1_equivalence tests.test_level1_display -v` → `OK`; `TestEquivalenceE3Static` (3 test),
  `TestEquivalenceE4Display` (mọi test), `TestEquivalenceE3Spy` (2 test) đều chạy, KHÔNG skip trên máy local có dữ liệu (E1 có thể chạy lâu; ghi `Ran`).
  Log `_work/_plan15_l13/u1a_green_equiv_display.log`.
- **AC-E4b** Toàn bộ module Level 1 + guard backend:
  `PY -m unittest $(ls tests/test_level1_*.py | sed 's#/#.#; s#\.py$##') tests.test_backend_source_guard`
  → `OK (skipped=1)`, skip duy nhất `test_u1_summary`; `Ran` = 480 + số test mới (ghi số thật); `[DoD7-guard] known=9 allowed=36`.
  Log `_work/_plan15_l13/u1a_green_level1_all.log`. AC-1 (28 module, lệnh M0): đỏ chỉ là tập đỏ của M0 (2 ERROR + 4 FAIL review A1/gitignore
  + `test_reset_segments_and_graphs` chập chờn theo luật 3 lần) — không đỏ mới.
- **AC-E4c** Tự kiểm `_e4_violations` trên nguồn tổng hợp (chuỗi trong test), mỗi ca một `subTest`, trả KHÁC rỗng với:
  (1) `cv2.resize` trong `fit_layout` của `level1_display.py`; (2) hai `cv2.resize` trong `render_to_window`; (3) `render_to_window` + `cv2.resize`
  hợp lệ nhưng `rel = "src/inference/level1_core.py"`; (4) `from cv2 import resize as r`; (5) `import cv2 as c`; (6) `f = cv2.resize`;
  (7) `getattr(cv2, "resize")`; (8) `render_to_window` lồng trong hàm khác; (9) resize đối số thứ nhất không phải tham số thứ nhất
  (vd. `frame`); (10) keyword `dst=`; (11) `cv2.warpAffine(...)` ở bất kỳ file nào; (12) `import mediapipe` trong `level1_display.py`;
  (13) `session.process(x)` trong `level1_display.py`. Trả RỖNG với nguồn hợp lệ mô phỏng `render_to_window` hiện tại. Kiểm file thật: mọi
  file của `E3_FILES` ⇒ `[]`.
- **AC-E4d** Đột biến thật (worktree tạm `_work/_plan15_l13/wt_u1a` tại commit U1a, xóa sau khi xong; KHÔNG sửa cây làm việc chính), mỗi đột
  biến chạy `PY -m unittest tests.test_level1_equivalence.TestEquivalenceE3Static tests.test_level1_equivalence.TestEquivalenceE4Display` ⇒
  `FAILED`: (m1) thêm `cv2.resize` vào `fit_layout`; (m2) thêm `cv2.resize` vào `src/inference/level1_core.py`; (m3) thêm lời gọi
  `cv2.resize` thứ hai trong `render_to_window`; (m4) thêm `import mediapipe` vào `level1_display.py`. Bản không đột biến ⇒ `OK`.
  Log `_work/_plan15_l13/u1a_mut_{m1,m2,m3,m4,base}.log`; ghi dòng `Ran`/`FAILED` từng log vào progress.
- **AC-E4e** Không đổi file nguồn: `git diff --stat ea9c645..HEAD -- src/ level1_demo.py backend/ configs/` rỗng (U1a chỉ sửa test + progress).
  `checkpoints/alphabet_best.pt` sha vẫn `160e0c68…`.
- **AC-E4f** Log đỏ có trước: `_work/_plan15_l13/u1a_red.log` = chạy lớp test mới TRƯỚC khi có `_e4_violations`/trước khi sửa `:273`
  (ERROR/FAIL ghi vào progress), cùng log đỏ sẵn `u1_green_level1_all.log` làm mốc.

## 5b. Phạm vi file

```scope
tests/test_level1_equivalence.py
tests/test_level1_display.py
docs/plans/15-progress.md
```
(Đều nằm trong phạm vi §10 lần sửa 13. U1a KHÔNG sửa `src/`; nếu thấy cần ⇒ DỪNG, báo planner. Bước U2 dùng phạm vi §10 lần sửa 13.)

Độ khó: S; vùng nhạy cảm: có (test tương đương landmark train ↔ realtime, đánh giá).

## 6. Rủi ro dữ liệu/ML

- Lệch train ↔ realtime: ngoại lệ chỉ cho ảnh HIỂN THỊ. Đường suy luận được khóa bằng (i) E3 tĩnh còn cấm resize ở mọi nơi khác + siết bí danh/
  hàm nội suy khác, (ii) E3 spy (identity) ở headless/paced, (iii) AC-U6b ở chế độ cửa sổ — đường duy nhất có resize.
- Giới hạn còn lại: kiểm tĩnh không thấy phép thu/phóng bằng numpy thuần; nếu ai đó làm thế trên khung TRƯỚC `process` mà vẫn truyền đúng đối tượng
  (sửa tại chỗ), identity không bắt được. Đã có từ trước (không do E4); E1 (landmark bit-identical với trích xuất offline, 10 clip) là lưới đỡ
  cuối cho đường headless. Ghi vào Giới hạn ở R2 nếu reviewer thấy cần.
- Không dữ liệu mới, không số liệu mới; không đổi model, không đổi checkpoint.

## 7. Điểm dừng

- Không CẦN NGƯỜI DÙNG: không đổi model mặc định, không cần dữ liệu người dùng, không đụng `README.md`/3 file ` D`, không hành động không hoàn tác
  (worktree tạm xóa được).
- DỪNG, báo planner (không tự nới): bất kỳ AC-E4c ca nào không bắt được mà phải đổi ý nghĩa ca; mã hiện tại vi phạm mục 1–4 §3.2 (cần sửa `src/`);
  U2 cần thêm import/lời gọi `resize` thứ hai/hàm resize ở chỗ khác; AC-U6b không chạy được ở chế độ cửa sổ bằng recorder.

## 8. Chỉ dẫn cho orchestrator

1. Giao U1a cho vslt-coder-claude với tài liệu này + `15-lan-sua-13.md` §5.4, §8 (quy ước), §9 (AC-0/AC-1).
2. Sau U1a: cầu nối xác minh (chạy lại AC-E4a/b, kiểm numstat AC-0 sửa) → vslt-reviewer review GỘP U1 (`ea9c645`) + U1a theo
   `docs/reviews/15-l13-u1-bridge.md` + AC-U1–U3 + AC-E4a–f.
3. APPROVE ⇒ giao U2 (`15-lan-sua-13.md` §8 #3) kèm AC-U6 sửa + AC-U6b của tài liệu này.
4. Chèn con trỏ vào `15-lan-sua-13.md` (ngay dưới tiêu đề, và cuối §5.4):
   `> LẦN SỬA 13a (2026-10-08): xem docs/plans/15-lan-sua-13a.md — ngoại lệ E4 (đúng 1 cv2.resize ảnh hiển thị trong render_to_window), sửa AC-U6/AC-0/AC-V4, thêm AC-U6b.`
