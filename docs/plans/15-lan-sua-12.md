# 15 — LẦN SỬA 12: Đánh vần nhiều chữ liên tiếp, chặn chữ rác lúc chuyển tay, bỏ tự cách, sửa lật gương tay thuận

> LẦN SỬA 13 (2026-10-08): xem docs/plans/15-lan-sua-13.md — giao diện co giãn/toàn màn hình, cử chỉ cố ý (gate kích hoạt nhầm), Unikey đúng chính tả + nguồn "fusion", model v6 + ngoại lệ test E1–E3, gỡ dữ liệu user1 khỏi git, đo đồng thuận preset; có hiệu lực thay phần mâu thuẫn của lần sửa này.

Người lập + coder: Claude Code (cloud, nhánh `cloud/2026-10-04-level1-rearm`). Reviewer: vslt-reviewer (local, khi kéo nhánh về).
Yêu cầu gốc: phản hồi webcam của người dùng ngày 2026-10-06 (5 vấn đề, 4 tiêu chí nghiệm thu).

## 0. Chẩn đoán (đối chiếu mã và dữ liệu, không đoán)

| # | Vấn đề | Nguyên nhân trong mã | Bằng chứng |
|---|---|---|---|
| 1 | `motion_pose` không quét nhiều chữ | sau mỗi chữ bộ tách `disarmed`, chỉ re-arm khi `M_t >= move_speed` liên tục `rearm_move_ms`; đổi ngón nhẹ không đủ | đường re-arm theo hình dạng tay (`pose_change_rules`) đã DỪNG ở R2 theo luật P2: độ phủ cặp chữ 0.378 < 0.80 (`reports/level1_realtime_2026-10-05/pose_evidence.json`, `calibration.p2.coverage`) ⇒ không thể bật bằng dữ liệu hiện có |
| 2 | `classifier` (rev8) bắn chữ rác | decoder nhận nhãn của cửa sổ ở MỌI khung có tay, kể cả khung tay đang chuyển giữa hai chữ; với `cls_conf` 0.78 / tone 0.70, `cls_stable_ms` 300 / tone 200 một tư thế trung gian đủ để thành chữ | `Level1LabelDecoder.push` không có thông tin chuyển động (mã trước `ddd7904`) |
| 3 | Tự chèn dấu cách | `--no-auto-space` mặc định tắt ⇒ `word_gap_ms` (1000 ở config mặc định) chèn dấu cách khi mất tay; `--gesture-space` mặc định bật ⇒ bàn tay thả lỏng dễ thành cử chỉ Xòe 5 ngón | `level1_demo.py` trước lần sửa 12 |
| 4 | `--dominant-hand Right` lật gương | `DOMINANT_HAND_LABELS = {"Right": "Left"}` giả định camera không lật gương; trên camera của người dùng MediaPipe gán `Right` cho tay ký (35/36 clip), nên nhãn ép `Left` làm `canonicalize_hand_sequence` lật x mọi khung | `reports/level1_realtime_2026-10-06/dominant_hand_check.json` @ `13759a6`: auto 36/36, ép `Left` 7/36, ép `Right` 35/36, lock 36/36 (clip train — kiểm logic, không phải độ chính xác) |
| 5 | Unikey cần luồng ổn định | hệ quả của 2–4 | — |

Ghi chú số liệu người dùng: 7/36 khi ép `Left` trùng khớp với JSON; 32/36 ở chế độ auto của người dùng khác 36/36 ở đây (ở đây phân
loại nguyên clip từ landmark đã ghi; người dùng có thể đã chạy qua video/MediaPipe lại). Không dùng số 32/36 trong tài liệu.

## 1. Ranh giới

- Không train lại, không đổi checkpoint, không đổi `canonicalize_hand_sequence`, không đổi `configs/level1_realtime.json`.
- Khóa config mới là TÙY CHỌN (`cls_motion_gate`); vắng khóa ⇒ decoder như cũ (mọi config/JSON cũ cho kết quả y hệt).
- Đổi mặc định CLI (S1) là thay đổi hành vi có chủ đích theo yêu cầu người dùng; các test cũ ghim mặc định cũ được giữ nguyên khẳng
  định, chỉ chạy với cờ tường minh `LEGACY_DEFAULTS = ("--auto-space", "--gesture-space")`. Không xóa test nào.

## 2. Thay đổi

### G1 — Cổng chuyển động của decoder (vấn đề 1, 2)
- `Level1LabelDecoder` luật 7: khi `cls_motion_gate` true, khung có tay được đẩy vào với `moving=True` (trạng thái bộ tách
  `moving` của chính khung đó: `M_t >= move_speed` có trễ, hoặc chưa đo được chuyển động) cắt lượt nhãn và không phát gì. Nhãn chỉ
  được phát sau khi giữ `cls_stable_ms` trên các khung tay đứng yên. Cửa sổ không đổi (nét dấu thanh vẫn trong cửa sổ khi tay dừng).
  G1b (`551e1b2`): khung có dự đoán là chữ biến thể của nhãn vừa phát (`VARIANT_BASE[pred] == last`, ví dụ `a` → `â`) không bị cắt.
  Lưu ý: dòng `reason` của `cls_motion_gate` trong rev9 viết trước G1b ("the run restarts on every moving frame"); quy tắc đầy đủ ở
  docstring `Level1LabelDecoder` (luật 7). Không sửa file config để giữ sha256 khớp với hai JSON đo.
- `level1_demo.py`: truyền `segmenter.state == "moving"` vào timeline (phần tử thứ 6 của khung); HUD `| chờ tay yên`;
  `counts.frames_gated` chỉ khi bật cổng.
- `scripts/level1_rearm_check.py decode_chain`: khi bật cổng chạy một `Level1SignSegmenter` song song, như app.
- `configs/level1_demo_classifier_rev9.json` = rev8 + `cls_motion_gate: true` (mọi giá trị khác giữ nguyên, test khóa điều này).
- Đánh vần liên tục dùng chế độ `classifier` (không có trạng thái disarmed: nhãn đổi là chữ mới); `motion_pose` giữ nguyên vì P2.

### S1 — Dấu cách tự động tắt mặc định (vấn đề 3)
- `--auto-space / --no-auto-space` (mặc định tắt), `--gesture-space` mặc định tắt. Phím Space luôn thêm dấu cách. Word gap vẫn được
  phát hiện và ghi JSON (`auto_space: false`).

### H1 — Khóa tay theo đa số nhãn MediaPipe (vấn đề 4)
- `HandednessLock` (`src/inference/level1_core.py`): đếm `HAND_LOCK_FRAMES` (15, giá trị thiết kế, lẻ để không hòa) nhãn đầu tiên,
  rồi khóa nhãn đa số cho cả phiên. Không còn ánh xạ cố định tay → nhãn.
- `--dominant-hand {auto, lock, Right, Left}`; `Right` / `Left` là bí danh của `lock` (in cảnh báo). JSON `dominant_hand` =
  `mode, requested, label, lock_frames, votes`; HUD `[Tay: đang khóa n/N]` → `[Tay: khóa <label>]`.

## 3. Tiêu chí nghiệm thu và cách kiểm

| AC | Kiểm bằng | Kết quả |
|---|---|---|
| AC1 multi-sign không rác | test G1 (`tests/test_level1_lan_sua_12.py`, `TestDefaultsS1G1`); chuỗi ghép clip train (mục 4) | logic xanh; chuỗi ghép: rác giảm so với rev8 nhưng G5 trượt; webcam CHƯA đo |
| AC2 không tự cách | `TestDefaultsS1G1.test_s1_no_automatic_space`, `TestDefaultsArgsS1` | xanh |
| AC3 không lật gương | `dominant_hand_check.json`; `TestDominantHandP1`, `TestHandednessLockH1` | lock 36/36 vs ép `Left` 7/36 |
| AC4 test 100% | `tests.test_level1_core`, `tests.test_level1_demo` (+ segmenter, rearm_check, lần sửa 12) | mục 5 |

## 4. Bằng chứng cổng chuyển động (chuỗi ghép clip train — kiểm logic decoder, không phải phiên webcam)

Lệnh: `python scripts/level1_rearm_check.py --decoder --config off=configs/level1_demo_classifier_rev8.json --config on=configs/level1_demo_classifier_rev9.json --join-ms 0,300,600 --gates on:off --out reports/level1_realtime_2026-10-06/rearm_check_gate.json`

Hai lần đo (cùng lệnh, đổi `--out`): `rearm_check_gate.json` tại `85a6a91` (cổng G1 bản đầu) và `rearm_check_gate_v2.json` tại
`551e1b2` (G1b: không cắt chữ biến thể của chữ vừa phát), `generated_by.code_dirty = false` cả hai. `off` = rev8, `on` = rev9.
Cổng G1–G6 là cổng đăng ký trước của D4 (`scripts/level1_rearm_check.py`), KHÔNG đổi sau khi thấy kết quả.

| Chuỗi L (chữ cái), join | rev8 one / rác / TER | rev9 bản đầu one / rác / TER | rev9 G1b one / rác / TER |
|---|---|---|---|
| 0 ms | 0.933 / 0.109 / 0.130 | 0.896 / 0.130 / 0.161 | 0.922 / 0.104 / 0.135 |
| 300 ms | 0.933 / 0.124 / 0.140 | 0.902 / 0.124 / 0.150 | 0.922 / 0.104 / 0.130 |
| 600 ms | 0.938 / 0.135 / 0.150 | 0.902 / 0.145 / 0.150 | 0.927 / 0.119 / 0.124 |

- Dấu thanh phát ra trong chuỗi L (rác kiểu "dấu sắc" giữa hai chữ), cộng 3 join: rev8 19, rev9 14 (cả hai bản).
- Clip đơn (G6): chữ 0.957 → 0.961, dấu thanh 0.575 → 0.625 (ít phát nhiều lần hơn: multi 48 → 41).
- Chuỗi T (dấu thanh) và O: như nhau giữa rev8 và rev9.
- Gate (rev9 G1b): G1 0.922 / 0.922 ĐẠT; G2, G3, G4, G6 ĐẠT; **G5 0.104 / 0.119 TRƯỢT** (ngưỡng ≤ 0.05). rev8 trên cùng phép đo cũng
  có rác 0.124 / 0.135 (> 0.05). Bản đầu của G1 trượt cả G1 (0.896) vì cắt mất chuyển động của chữ biến thể (`â → a`, `ê → e`, `ô → o`),
  đã sửa ở G1b — thay đổi THĂM DÒ sau khi thấy lần đo 1, ghi rõ ở đây.
- Đọc kết quả: phần lớn "rác" còn lại của phép đo này là nhãn sai bên trong clip (ví dụ chữ biến thể không thành), không phải chữ bắn
  ở khung chuyển tay; join của chuỗi ghép là nội suy tuyến tính, không giống chuyển tay thật trên webcam. Phép đo này KHÔNG chứng minh
  được AC1 trên webcam; nó cho thấy cổng (G1b) không làm xấu chuỗi chữ cái so với rev8 và giảm rác dấu thanh / TER.
- Theo luật lần sửa 4 §7 mục 1 (một gate trượt ⇒ DỪNG): `configs/level1_realtime.json` giữ `motion_pose`; rev9 chỉ là config demo,
  như rev7 / rev8 (người dùng đã chọn classifier cho demo dù G6 tone của D4 trượt).

## 5. Kết quả test (cloud, 2026-10-06, sau khi khôi phục dữ liệu gitignored)

- `tests.test_level1_demo`: Ran 142, OK, 0 skip (tại `85a6a91` + test).
- Mọi module `tests/test_level1_*.py`: xem dòng cuối của `docs/progress_log.md` (số chạy cuối cùng, kể cả test lần sửa 12).
- Test đổi khẳng định (không xóa): `TestNoAutoSpaceArgT3.test_t3_help_and_default`, `TestRev7DemoConfig.test_r7_demo_command_runs_classifier_mode`
  (`auto_space: false` nay là mặc định), `TestRev9CommandS3` (thêm `--gesture-space`), khối dominant-hand (ánh xạ cố định → lock;
  `test_p1_choices_default_mapping` → `_aliases`, `test_p1_locked_label_on_every_hand_frame` → `_is_mediapipe_majority`).
  Các test hồi quy còn lại chạy với `LEGACY_DEFAULTS` (cờ tường minh của hành vi cũ), khẳng định giữ nguyên.
- GitNexus: impact trước sửa (`decode_chain` HIGH, `Level1LabelDecoder` MEDIUM, các method app LOW/MEDIUM); detect-changes trước
  commit app: risk CRITICAL (103 process — chủ yếu do helper test `args_for` dùng trong hầu hết test demo) ⇒ đã chạy lại toàn bộ test.

## 6. Còn lại cho người dùng

- Phiên webcam thật với lệnh mục 1 của `docs/level1_desktop.md` (`--out-json`) để xác nhận AC1/AC2 trên camera thật.
- Nếu dấu thanh khó ra dưới cổng chuyển động trên webcam: dừng tay ngắn ở cuối nét dấu; đây là giới hạn đã biết của G1.
