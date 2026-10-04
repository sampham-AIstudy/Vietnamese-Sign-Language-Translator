# 15 — LẦN SỬA 2 (nhỏ): luật cắt đuôi `tail_still_keep_ms`, A3, 3 điểm nhỏ

> **LẦN SỬA 3 (2026-10-04):** re-arm chữ liên tiếp không rút tay (luật tư thế `pose_change_rules`/`rearm_pose_dist`), thứ tự bước mới R0 → A2a → R1 → A2b → R2 → R3 → A3 → C1, bổ sung AC-S18 và config SAU của A3 — đọc `docs/plans/15-lan-sua-3.md` trước khi làm bất kỳ bước nào còn lại của 15.

Có hiệu lực như nằm trong kế hoạch 15 (đè lên `docs/plans/15-lan-sua-1.md` ở đúng các chỗ nêu trong §3). Mọi phần khác của
15 / 15-lan-sua-1 giữ nguyên. Không có điểm dừng CẦN NGƯỜI DÙNG (xem §8).

## 1. Vấn đề và nguyên nhân gốc
- §3.A.3 của 15-lan-sua-1 (dòng 145–146) đặt hai yêu cầu không thể cùng đúng: (a) giữ khung có `ts ≤ _still_since + tail_still_keep_ms`;
  (b) `tail_still_keep_ms == hold_ms` ⇒ giống hệt hành vi cũ. Segment `hold` được phát ở khung đầu tiên có
  `held = ts − _still_since ≥ hold_ms`; với thời gian rời rạc thì thường `ts > _still_since + hold_ms`, nên luật (a) bỏ khung phát
  (và có thể hơn) dù tail == hold. Lỗi nằm ở đặc tả (planner), không phải ở coder: mã tại 6067611
  (`src/inference/level1_segmenter.py:273-274`) làm đúng câu chữ (a).
- Bằng chứng: `_work/_plan15/a2_verify/boundary_check.py` + `boundary_check.json` (so bộ tách 4a55bf0 với HEAD, config b0620a9,
  tail = hold): 633/636 clip khác segment, số segment `hold` vẫn bằng nhau. Test S14/S15 hiện có không bắt được vì khung cách đều 40 ms
  (held đúng bằng 400 ms ở khung phát).
- Hệ quả phụ cần ghi nhận (không phải lỗi): với config hiệu chỉnh hiện tại tail = hold = 400, nên sau khi sửa thì `tail_still_keep_ms`
  KHÔNG đổi segment nào trên config này. Đây là kết quả của quy tắc 5 đặt trước; KHÔNG chỉnh quy tắc 5 sau khi thấy điều này.

## 2. Quyết định (luật mới) — thay luật (a)
Khi phát lý do `hold` tại khung có timestamp `t_emit`:
```
cutoff = t_emit − (hold_ms − tail_still_keep_ms)
segment = các khung trong buffer có ts ≤ cutoff   (rồi _make_segment như cũ: bỏ khung không tay ở đầu/cuối, kiểm min_frames)
```
- tail == hold ⇒ `hold_ms − tail_still_keep_ms == 0.0` ⇒ cutoff == t_emit ⇒ giữ MỌI khung của buffer (mọi khung có ts ≤ t_emit) ⇒
  bằng hệt hành vi cũ trên mọi lưới thời gian (không phụ thuộc khoảng cách khung). Để bằng hệt không phụ thuộc làm tròn, coder viết nhánh
  rõ: `if tail_still_keep_ms >= hold_ms: buf_for_seg = self._buf` (không lọc); ngược lại lọc với `ts ≤ cutoff + 1e-6`.
- tail < hold: bỏ phần đuôi dài `hold_ms − tail` ms tính ngược từ t_emit. Vì `t_emit − _still_since ≥ hold_ms` nên cutoff ≥
  `_still_since + tail_still_keep_ms`: đuôi đứng yên giữ lại ≥ tail ms (đúng ý nghĩa "giữ khoảng tail ms đứng yên cuối", gần với
  `trailing_still_ms` đo trên clip train). Hàm liên tục theo tail, không có bước nhảy như phương án "không cắt khi tail ≥ hold, ngược lại
  cắt theo still_since".
- `t_emit_ms` không đổi; khung sau cutoff vẫn tính vào hold, chỉ không vào segment; `hand_lost`/`end_of_stream` không đổi;
  kiểm `0 < tail_still_keep_ms ≤ hold_ms` giữ nguyên.
- Lý do chọn: là luật duy nhất trong các phương án nêu ra vừa (i) bằng hệt hành vi cũ khi tail == hold trên thời gian rời rạc bất kỳ,
  (ii) liên tục theo tail, (iii) không cần định nghĩa theo số khung (phụ thuộc fps — trái nguyên tắc "mọi thời lượng tính bằng ms").

## 3. Thay thế trong `docs/plans/15-lan-sua-1.md`
| Chỗ trong 15-lan-sua-1 | Thay bằng |
|---|---|
| §3.A.3 dòng 145–146 ("segment chỉ giữ các khung có ts ≤ `_still_since + tail_still_keep_ms` … giống hệt hiện tại (test khóa)") | §2 ở trên. |
| §3.A.4 dòng 150–156 (config TRƯỚC/SAU của `segment_check`) | §5 dưới. Quy tắc giữ config dòng 157–160 GIỮ NGUYÊN chữ và số. |
| §4 bảng: dòng A3 (#5) | Chèn A2a, A2b trước A3 (§7). A3 giữ nội dung, cập nhật theo §5. |
| §5 "AC-S bổ sung" dòng 268–269 (S15: "ts ≤ `_still_since + tail_still_keep_ms`") | S15 đổi điều kiện thành "khung cuối của segment `hold` có ts ≤ `t_emit − (hold_ms − tail_still_keep_ms)`, t_emit không đổi". Test S15 hiện có vẫn đúng nguyên văn (lưới 40 ms: 800 − 200 = 600 = 400 + 200), không sửa. Thêm AC-S16…S18, AC-W1…W3 (§4). |
| §3.A.3 dòng 142–143 (`--write-config`) | Bổ sung §6 (reason, commit, kiểu số). |

## 4. Tiêu chí chấp nhận bổ sung (hợp đồng; coder không đổi)
Lệnh: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_level1_segmenter.py tests/test_level1_segment_report.py tests/test_level1_core.py -q`
→ 0 failed; các test dữ liệu chỉ được skip vì thiếu file gitignored (cùng kiểu `skipUnless` như `tests/test_level1_core.py:179`); trên
máy dev (có dữ liệu) KHÔNG được skip. Cộng toàn bộ AC-S/AC-C/AC-E1/AC-G/AC1-ngắn như cũ, 0 failed.

- **AC-S16 (khoảng cách khung KHÔNG đều, tail == hold):** luồng tổng hợp chuyển động→đứng yên với dt không đều (ít nhất: dt xen kẽ
  33/47 ms, và lưới fps thật i×1000/23.584), đặt sao cho ở khung phát `held > hold_ms` thật sự (assert điều này trong test). Với
  tail == hold: segment `hold` có `t_end_ms == t_emit_ms`, `n_frames` == số khung có tay từ t_start tới t_emit, và bằng hệt (`array_equal`
  raw_landmarks/detected/handedness/timestamps_ms, cùng close_reason, t_start/t_end/t_emit) kết quả của bản tham chiếu "không lọc" — bản
  tham chiếu là bộ tách 4a55bf0 nạp bằng `git show 4a55bf0:src/inference/level1_segmenter.py` vào module tạm (thư mục tạm của test,
  không ghi vào repo). Test này phải ĐỎ tại 6067611.
- **AC-S17 (không đều, tail < hold):** cùng luồng, tail = hold/2: t_emit bằng t_emit của chạy tail == hold; segment là TIỀN TỐ của
  segment tail == hold; `t_end_ms ≤ t_emit − (hold − tail)`; khung kế tiếp trong luồng sau t_end (nếu có tay) có ts > cutoff
  (cắt tối đa, không bỏ thừa); `t_end_ms − (thời điểm bắt đầu đứng yên mà test dựng) ≥ tail − (dt lớn nhất)`.
- **AC-S18 (clip thật, bằng hệt 4a55bf0):** trên MỌI clip hauuto của manifest (dùng `load_train_clips`/`clip_timestamps` của
  `scripts/level1_segment_report.py`, flush như `boundary_check.py`), với HAI config: (a) `configs/level1_realtime.json` hiện hành;
  (b) config tại 3ebc7b9 (`git show`) điền `tail_still_keep_ms = hold_ms` — so bộ tách HEAD với bộ tách 4a55bf0: mọi clip cùng số sự
  kiện, cùng kiểu, và mỗi SignSegment bằng hệt như AC-S16. Assert số clip == số dòng hauuto của manifest (không ngầm bỏ clip). Test này
  phải ĐỎ tại 6067611 (cấu hình (a)). Đặt trong `tests/test_level1_segmenter.py` hoặc file mới `tests/test_level1_segmenter_clips.py`.
- **AC-W1:** `write_config` không còn chuỗi commit gõ tay: nếu file evidence chưa nằm trong commit nào, hoặc đang có thay đổi chưa commit
  (`git status --porcelain -- <evidence>` khác rỗng) → `RuntimeError`, config KHÔNG bị ghi (kiểm nội dung file sau lỗi không đổi). Không
  dùng `generated_by.git_commit` làm dự phòng (đó là commit mã, không phải commit chứa JSON). Grep `1ca53f3` trong `scripts/` = 0 kết quả.
- **AC-W2:** sau `write_config`, `reason` của 5 khóa hiệu chỉnh là chuỗi cố định trong script mô tả QUY TẮC (vd "calibrated by rule 5 of
  plan 15 §3.A.3: min(hold_ms, p50 trailing_still_ms over clips with motion)") — không chứa chữ số đo, không còn câu lý do thiết kế cũ;
  khóa không hiệu chỉnh giữ nguyên `value/source/reason` từng byte (so dict trước/sau).
- **AC-W3:** chạy lại `--write-config` trên config hiện hành ra `value` của 5 khóa BẰNG HỆT b0620a9 (so `git show b0620a9:configs/level1_realtime.json`);
  chỉ `reason` đổi; `source` vẫn trỏ đúng commit chứa evidence (1ca53f3, lấy bằng git, không gõ).

## 5. A3 cập nhật (thay §3.A.4 dòng 150–156)
- Mã chạy: bộ tách tại commit A2a trở đi (đã chứng minh bằng hệt 4a55bf0 khi tail == hold bởi AC-S18).
- **Config TRƯỚC** = `configs/level1_realtime.json` tại 3ebc7b9 (`git show` → `_work/_plan15/config_before.json`), điền
  `tail_still_keep_ms = hold_ms` (= hành vi trước 15 nhờ AC-S18 (b)); JSON ghi `"filled": {"tail_still_keep_ms": "= hold_ms of this config"}`
  và commit nguồn 3ebc7b9.
- **Config SAU** = `configs/level1_realtime.json` tại commit config của A2b (giá trị = b0620a9 theo AC-W3); JSON ghi commit đó.
- Mỗi JSON ghi thêm `generated_by` (lệnh, commit mã, code_dirty) như các report khác của 15. Chạy tại commit mã sạch.
- Quy tắc giữ/bỏ (dòng 157–160 của 15-lan-sua-1) GIỮ NGUYÊN, áp lên số đọc từ JSON; không chạy giá trị thứ ba; không đổi dung sai.
  Lưu ý ghi trước: vì tail = hold trong SAU, mọi khác biệt TRƯỚC/SAU đến từ still_speed/move_speed/max_segment_ms, không từ cắt đuôi;
  15-progress ghi câu này cạnh kết luận.

## 6. Ba điểm nhỏ (quyết định)
1. **reason 5 khóa hiệu chỉnh:** `write_config` ghi reason theo quy tắc (AC-W2); config được sinh lại trong A2b (không sửa tay JSON).
2. **Dự phòng "1ca53f3":** bỏ; thành lỗi (AC-W1). Bỏ luôn dự phòng `generated_by.git_commit`.
3. **hold_ms int → float (400 → 400.0):** CHẤP NHẬN float. Lý do: `CONFIG_SPEC` khai báo `("number", "positive")`
   (`src/inference/level1_core.py:31`), không chỗ nào trong `src/inference/`, `level1_demo.py`, `scripts/level1_*.py` ép int hay định dạng
   `%d` với hold_ms (đã grep); mọi phép dùng là so sánh/chia. Không thêm test riêng; AC-S/AC-C/AC-E1 đầy đủ chạy với config float là đủ.

## 7. Bước coder (agy; mỗi bước 1 commit `15: <mã> …`; quy ước §4 của 15-lan-sua-1 giữ nguyên: impact trước sửa, detect-changes trước commit, test đỏ trước)
| # | Bước | Nội dung | Phụ thuộc | Giờ |
|---|---|---|---|---|
| 4a | **A2a** | Viết AC-S16/S17/S18 trước (chạy, ghi ĐỎ tại 6067611 vào 15-progress) → sửa luật §2 trong `Level1SignSegmenter.push` + docstring mô-đun (dòng mô tả hold) → xanh. Chạy AC-S/AC-C/AC-E1/AC-G/AC1-ngắn. | A2 | 1 |
| 4b | **A2b** | `write_config`: bỏ dự phòng (AC-W1), reason theo quy tắc (AC-W2) + test trong `tests/test_level1_segment_report.py` (dùng file evidence/config tạm, không đụng config thật). Commit mã. Rồi tại commit mã sạch chạy `--write-config configs/level1_realtime.json` → kiểm AC-W3 → commit config riêng (`15: A2b config reason`). Ghi bảng reason cũ→mới vào 15-progress. | A2a | 0,75 |
| 5 | **A3** | Như bảng §4 của 15-lan-sua-1, với config TRƯỚC/SAU theo §5 trên. | A2b | 1 |
Tổng thêm so với kế hoạch: +1,75 giờ (A2a, A2b). Thứ tự cắt khi thiếu ngân sách: KHÔNG cắt A2a (sửa lỗi bộ tách đã commit, vùng nhạy cảm);
A2b được cắt cùng A3 (khi đó Giới hạn trong C1 ghi "reason trong config còn chữ thiết kế").

**Test cũ:** chỉ được THÊM test. Không sửa/xóa assertion nào của test hiện có — S14/S15 giữ nguyên văn (vẫn đúng với luật mới). Không có
ngoại lệ. Nếu một test cũ đỏ sau sửa → DỪNG, báo planner (đó là dấu hiệu luật sai, không phải test sai).

## Phạm vi file
Không đổi so với §3b của 15-lan-sua-1 (mọi file của A2a/A2b/A3 nằm trong đó; test mới khớp `tests/test_level1_*.py`; file tạm ở `_work/_plan15/` không commit):
```scope
src/inference/level1_textbox.py
src/inference/level1_core.py
src/inference/level1_segmenter.py
level1_demo.py
configs/level1_realtime.json
scripts/level1_segment_report.py
scripts/level1_replay_clips.py
tests/test_level1_*.py
docs/level1_desktop.md
docs/progress_log.md
reports/level1_realtime_*
```
Độ khó: M; vùng nhạy cảm: có (bộ tách đoạn realtime, config đã hiệu chỉnh) → A2a dùng opus/high; A2b gemini/high được.
KHÔNG đụng: kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`, `tests/test_backend_source_guard.py`, model mặc định.

## Rủi ro dữ liệu/ML
- Lệch train–realtime: luật mới chỉ khác hành vi khi tail < hold; với config hiện hành không đổi segment nào (AC-S18 khóa điều đó).
- AC-S18 dùng dữ liệu train của checkpoint — đây là kiểm tương đương hành vi, không phải độ chính xác; không báo số nào từ nó như chất lượng.
- AC-S18 phụ thuộc lịch sử git (4a55bf0, 3ebc7b9): nếu thiếu commit (clone nông) test phải FAIL rõ ràng, không skip.

## 8. Điểm dừng
Không có điểm dừng bắt buộc: không đổi model mặc định, không cần dữ liệu người dùng, không đụng thay đổi chưa commit, không hành động không
hoàn tác (config sinh lại có commit riêng, hoàn tác bằng git). Điểm dừng cho coder: test cũ đỏ (§7); AC-W3 ra value khác b0620a9 → DỪNG.

## Dòng con trỏ
> **LẦN SỬA 2 (2026-10-04):** luật cắt đuôi `tail_still_keep_ms` (§3.A.3 dòng 145–146), config TRƯỚC/SAU của A3 (§3.A.4 dòng 150–156), AC-S15 và bước A2a/A2b được thay/bổ sung bởi `docs/plans/15-lan-sua-2.md` — đọc file đó trước khi làm A2a/A2b/A3.
