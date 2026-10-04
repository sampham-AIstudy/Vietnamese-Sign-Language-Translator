# 15 — LẦN SỬA 3: nhận nhiều chữ liên tiếp không cần rút tay (re-arm theo thay đổi hình dạng tay)

Có hiệu lực như nằm trong kế hoạch 15. Đè lên `docs/plans/15-lan-sua-1.md` và `docs/plans/15-lan-sua-2.md` đúng ở các chỗ nêu ở §0;
mọi phần khác giữ nguyên. KHÔNG có điểm dừng CẦN NGƯỜI DÙNG (§7). Planner không chạy được lệnh trong lượt này (chỉ đọc file): mọi số dưới
đây đọc từ JSON đã commit / file trong `_work/`, kèm dòng; số nào cần tính thêm thì chỉ định lệnh sinh ra nó (R0).

## 0. Chỗ thay trong 15-lan-sua-1 / 15-lan-sua-2
| Chỗ | Thay/bổ sung bằng |
|---|---|
| 15-lan-sua-1 §4 bảng (dòng 224–233) + 15-lan-sua-2 §7 (dòng 91–98) | Thứ tự mới §4 dưới: R0 → A2a → R1 → A2b → R2 → R3 → (U1c) → A3 → C1 → (R4, A4, C2). Nội dung A2a/A2b/A3/C1 giữ, trừ các điểm ghi ở đây. |
| 15-lan-sua-2 §4 AC-S18 (dòng 59–63) | Bổ sung: khi `SEGMENTER_KEYS` có khóa của R1, AC-S18 chạy với `pose_change_rules = false` (config (a) và (b)); thêm khẳng định "hai giá trị `rearm_pose_dist` khác nhau cho kết quả bằng hệt" (khóa không được dùng khi tắt). Điền khóa vào bộ dựng config của AC-S18 ở R1 thuộc ngoại lệ §4 (không đổi assertion). |
| 15-lan-sua-2 §5 "Config SAU" (dòng 78) | SAU = config tại commit config của A2b (khi đó `pose_change_rules = false`) — vẫn cô lập tác động hiệu chỉnh A2. Tác động của luật tư thế kiểm riêng ở R3 (G6), không gộp vào quy tắc giữ của A3. |
| 15-lan-sua-1 §3b scope | Thêm `scripts/level1_rearm_check.py`, `docs/plans/15-progress.md` (§5b). |
| 15-lan-sua-1 §6.2 Giới hạn | Thêm các dòng ở §6 dưới (cặp chữ cùng hình dạng, chữ lặp cần nảy tay/`r`, nguồn kiểm là train ghép). |
| 15-lan-sua-1 §6.3 việc người dùng | Thêm U1c (§4). |

## 1. Mục tiêu và DoD
Người dùng ký liên tiếp nhiều chữ (b → a → …) mà không phải đưa tay ra khỏi khung; giữ yên lâu KHÔNG phát lặp; chữ lặp thật (oo, ee) vẫn có
cách (nảy tay rõ hoặc phím `r`); không phát chữ rác khi chuyển tay. Phục vụ DoD Level 1 desktop realtime (kế hoạch 15 §1: đánh vần liên tục
dùng được, tham số có nguồn, không đổi model mặc định, không thêm vi phạm guard DoD 7).

## 2. Hiện trạng và kiểm giả thuyết

### 2.1 Mã
- `src/inference/level1_segmenter.py:261-265`: re-arm CHỈ khi `M_t ≥ move_speed` liên tục `≥ rearm_move_ms` (buffer cắt về `_move_since`),
  hoặc mất tay (`_tracking` false → dòng 232-235 armed = True). `M_t` = trung vị cửa sổ của `m_t = max(tốc độ cổ tay, tốc độ hình dạng)`
  (`frame_motion` dòng 89-96; dòng 95 = tốc độ hình dạng trên `normalize_hand_landmarks`: tâm cổ tay, chia độ dài bàn tay).
- Phân loại still/moving dòng 248-259 (vùng trễ ở giữa giữ cả hai đồng hồ; `M_t ≤ still_speed` xóa `_move_since`). Phát `hold` dòng 268-280;
  sau phát `_armed = False`.
- Khóa: `SEGMENTER_KEYS` dòng 37-38; `CONFIG_SPEC`/`validate_level1_config` ở `src/inference/level1_core.py:25-47, 77-106` (bắt buộc đủ khóa,
  không có giá trị mặc định). Phím `r` = lặp token chữ cuối (`level1_core.py:327-332`, `level1_demo.py:72`) — đã có, không phải re-arm.
- Test: `tests/test_level1_segmenter.py` PARAMS dòng 26-28; S3 (re-arm bằng chuyển động, dòng 107-115), S4 (chuyển động ngắn không re-arm,
  dòng 117-122). Mọi chuỗi test dùng MỘT hình dạng cố định (`TEMPLATE`, chỉ cổ tay dịch) ⇒ khoảng cách tư thế đã chuẩn hóa luôn 0.

### 2.2 Số liệu (đọc từ file; không phải độ chính xác)
- Config hiện hành (`configs/level1_realtime.json:8-22`, A2 b0620a9): still_speed 2.5306, move_speed 5.0612 (= 2 × p90 qua 516 clip chữ cái
  của trung vị M_t từng clip, `tone_evidence.json:1032-1040`). Trước A2: 1.0 / 2.0 (`tone_evidence.json:1018-1022`). rearm_move_ms 150 (design).
- Clip TRAIN (`reports/level1_realtime_2026-10-03/tone_evidence.json`, sinh tại 72167b9, code_dirty false), với ngưỡng mới: 322/516 clip chữ
  cái (dòng 585) và 69/120 clip DẤU THANH (dòng 646; `rule6` dòng 1061-1062) KHÔNG có khung nào đạt `M_t ≥ move_speed`. p95 trung vị M_t
  của clip chữ cái = 3.79 (dòng 641) < 5.06; p90 trung vị M_t của clip dấu = 1.78 (dòng 701) < still_speed 2.53. Tức là ngay cả chuyển động
  CỐ Ý của dấu thanh trong train phần lớn không đạt ngưỡng re-arm hiện tại.
- Phiên U1 (`_work/_plan15_u1/u1_2026-10-03_1650.json`, commit 2cf1f34, config cũ still 1.0 / move 2.0 — dòng 25-38): 105 segment (dòng 217),
  close_reason hold 89 / hand_lost 15 / end_of_stream 1 (`tone_evidence.json:1100-1104`), 33 sự kiện word_gap (dòng 218; đếm `"event": "word_gap"`
  = 33). Có ÍT NHẤT 33 cặp sự kiện `hold` liền nhau không có word_gap xen giữa (grep multiline không chồng lấp = cận dưới). Phù hợp với việc
  ngưỡng cũ re-arm được giữa hai chữ mà không rút tay, nhưng KHÔNG chứng minh (mất tay 300–1000 ms khi chưa armed không để lại sự kiện).
  Ghi chú phụ (ngoài việc này): `tone_evidence.json:1144` ghi `word_gaps: 24`, khác 33 của U1 JSON — báo orchestrator.
- U1b (sau A2, ngưỡng mới) KHÔNG có JSON.
- **Kết luận giả thuyết:** CÓ CƠ SỞ MẠNH, CHƯA CHỨNG MINH TRỰC TIẾP (chưa có dữ liệu chuyển tiếp chữ→chữ). Ngưỡng re-arm 5.06 hiệu chỉnh từ
  clip MỘT ký hiệu. Nguyên nhân thứ hai planner thấy khi đọc mã: still_speed 2.53 cao ⇒ chuyển tay chậm bị coi là "đứng yên" ⇒ (a)
  `_move_since` bị xóa liên tục (dòng 251-254), không bao giờ đủ 150 ms; (b) nếu chỉ hạ ngưỡng re-arm, đồng hồ hold có thể đã chạy suốt lúc
  chuyển tay chậm và phát ngay một tư thế lưng chừng (chữ rác). Thiết kế §3 xử lý cả hai.
- R0 (§4) kiểm giả thuyết bằng số trên chuỗi train ghép, có luật bác bỏ đặt trước. Lệnh đếm chính xác cặp hold→segment liền nhau của U1
  (chỉ để ghi 15-progress, không phải số báo cáo):
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "import json;e=json.load(open('_work/_plan15_u1/u1_2026-10-03_1650.json',encoding='utf-8'))['events'];print(sum(1 for a,b in zip(e,e[1:]) if a.get('close_reason')=='hold' and b['event']=='segment'))"`

## 3. Thiết kế

### 3.1 Khoảng cách tư thế (hàm public dùng chung)
`pose_distance(n_a, n_b) = mean_i ‖n_a[i] − n_b[i]‖` (chuẩn 3D trên 21 điểm; `n = normalize_hand_landmarks(aspect_points(raw))` — đúng N đang
tính ở dòng 241-242; cùng công thức với phần hình dạng dòng 95 nhưng không chia dt). Đơn vị: độ dài bàn tay. Đặt trong `level1_segmenter.py`;
script R0/R2/R3 GỌI LẠI hàm này (không viết lại công thức; test kiểm).

### 3.2 Ba luật mới trong `Level1SignSegmenter.push` (chỉ khi `pose_change_rules == true`)
Tham số mới (config, không mặc định trong mã): `pose_change_rules` (bool), `rearm_pose_dist` (số > 0, độ dài bàn tay).
1. **Neo tư thế khi phát `hold`:** `anchor` = trung bình N của các khung có tay trong `[t_emit − motion_window_ms, t_emit]` (chống một khung
   lệch). Xóa `anchor` khi re-arm (bất kỳ cách nào), `reset()`, `_close_lost`.
2. **Re-arm theo hình dạng (thêm, OR với re-arm chuyển động hiện có):** khi chưa armed và có `anchor`: `d_t = pose_distance(N_t, anchor)`;
   `_pose_since` = ts khung đầu của chuỗi khung có tay LIÊN TIẾP có `d_t ≥ rearm_pose_dist` (khung có `d_t <` ngưỡng → None). Re-arm khi
   `ts − _pose_since ≥ rearm_move_ms` (dùng lại khóa có sẵn: "cần ≥ rearm_move_ms bằng chứng liên tục mới re-arm"; reason của khóa cập nhật
   chữ). Buffer cắt về `ts ≥ _pose_since` (đối xứng với cắt về `_move_since`).
3. **Hold phải ổn định hình dạng (chống chữ rác khi chuyển tay chậm):** khi đồng hồ hold đang chạy (`_still_since` khác None), giữ
   `hold_ref` = N tại khung đặt `_still_since`; nếu `pose_distance(N_t, hold_ref) ≥ rearm_pose_dist` thì `_still_since = ts`, `hold_ref = N_t`
   (hold bắt đầu lại). Áp dụng cả lúc armed và chưa armed. Hệ quả: chuyển tay chậm (tốc độ ≤ still_speed) không phát được tư thế lưng chừng
   trừ khi tư thế đó nằm trong phạm vi < rearm_pose_dist suốt hold_ms.
- Không đổi: `m_t`/`M_t`, ngưỡng still/move, re-arm chuyển động, `hand_lost`, `word_gap`, `max_segment_ms`, luật cắt đuôi (15-lan-sua-2 §2),
  4 khóa của `status()` (được thêm khóa `rearm` ∈ {None, "motion", "pose", "hand"} = lý do re-arm gần nhất, tùy chọn, cho HUD/JSON).
- `pose_change_rules == false` ⇒ hành vi BẰNG HỆT bộ tách sau A2a trên mọi luồng (`rearm_pose_dist` không được đọc trong nhánh tính).
  Test khóa: AC-S18 (bổ sung §0) + AC-RA6.
- Kiểm khi nạp: `pose_change_rules` phải là bool thật (thêm kind "bool" vào `_check_value`); `rearm_pose_dist > 0`.

### 3.3 Chống xung đột
- Giữ yên lâu: sau phát, `d_t ≈ 0` và `M_t` thấp ⇒ không re-arm ⇒ không phát lặp (AC-RA2, G2).
- Rung tay/landmark nhiễu dưới ngưỡng: neo là trung bình cửa sổ, re-arm cần `≥ rearm_move_ms` liên tục (AC-RA3, AC-RA8).
- Chữ lặp thật (oo, ee): hình dạng giống ⇒ không re-arm theo tư thế; cách: nảy tay (re-arm chuyển động cũ), phím `r` (có sẵn), hoặc rút tay.
  Ghi vào Giới hạn + dòng hướng dẫn HUD (nếu dòng HUD đã nhắc `r` thì không đổi).
- Chữ rác khi chuyển: luật 3 + `min_sign_frames` + `accept_confidence` có sẵn (dưới ngưỡng → hiện mờ, `a` để nhận). Không thêm ngưỡng mới.
- Cặp chữ hình dạng gần nhau (khoảng cách < `rearm_pose_dist`): không re-arm theo tư thế ⇒ cần nảy tay/rút tay; R2 liệt kê các cặp này từ dữ
  liệu (vào Giới hạn), không đoán.

### 3.4 Nguồn tham số (quy tắc ĐẶT TRƯỚC; script tính, coder không gõ số)
| Khóa | Giá trị | source | Quy tắc / lý do |
|---|---|---|---|
| `pose_change_rules` | R1: `false`; R3: `true` chỉ khi G1–G6 đạt | design | công tắc; bật sau khi kiểm logic trên train ghép đạt (reason ghi tên JSON R3 + commit) |
| `rearm_pose_dist` | R1: giữ chỗ (reason: "không dùng khi pose_change_rules false; thay bằng quy tắc P1 ở R2"); R2: hiệu chỉnh | `calibrated: reports/level1_realtime_<D>/pose_evidence.json@<commit>` | P1 dưới |
| `pose_over_jitter_ratio` | 2.0 | design | cùng tinh thần `move_over_still_ratio`: ngưỡng gấp đôi biến thiên tư thế khi đang giữ một chữ (CONFIG_SPEC kiểu "above_one"; chỉ script đọc) |

- **P1:** trên MỌI clip CHỮ CÁI hauuto (`load_train_clips`), lấy đoạn đứng yên dài nhất (M_t ≤ still_speed của config hiện hành, cùng định
  nghĩa `longest_still_ms` của A1); `ref` = trung bình N của đoạn đó; `jitter_clip` = p95 qua các khung của đoạn của `pose_distance(N_t, ref)`.
  `rearm_pose_dist = pose_over_jitter_ratio × (p95 qua clip của jitter_clip)`. Clip không có khung đứng yên: đếm riêng, bỏ.
- **P2 (báo cáo + điểm dừng đặt trước):** với mỗi (người ký, phiên) và mỗi cặp lớp CHỮ CÁI khác nhau: `pose_lớp` = `ref` của clip có sample_id
  nhỏ nhất của lớp; `between = pose_distance(pose_a, pose_b)`. `coverage` = tỉ lệ cặp có `between ≥ rearm_pose_dist`. Ghi danh sách cặp dưới
  ngưỡng (gộp theo cặp nhãn, đếm số người ký). **coverage < 0,80 → DỪNG, báo planner** (không tự đổi tỉ lệ hay quy tắc).
- `pose_evidence.json` RIÊNG (không sinh lại tone_evidence.json, giữ nguồn của A2): `generated_by` (lệnh, commit, code_dirty), sha256 manifest
  + config, định nghĩa, n, p5/p10/p50/p90/p95 của jitter_clip và between, coverage, danh sách cặp dưới ngưỡng, câu "train data of the deployed
  checkpoint; not accuracy".
- `--write-pose-config` (hàm riêng, KHÔNG sửa hành vi `write_config` của A2b): chỉ ghi `rearm_pose_dist` với source trên, reason mô tả quy tắc
  (không chứa chữ số đo), commit evidence lấy bằng git theo luật AC-W1 (evidence chưa commit/bẩn → RuntimeError, config không ghi); khóa khác
  giữ nguyên từng byte. Dùng lại helper của A2b, không nhân bản.
- KHÔNG dùng dữ liệu webcam của người dùng (U1/U1b/U1c) để chọn hay báo tham số.

### 3.5 Kiểm không cần webcam: chuỗi GHÉP từ clip train (`scripts/level1_rearm_check.py`)
JSON và mọi chỗ trích ghi: "train clips concatenated to test the segmenter logic; not accuracy, not a webcam session".
- Nguồn: clip hauuto của manifest, đọc như A1 (`load_train_clips`, `clip_timestamps`). Mỗi clip bỏ khung không tay ở ĐẦU/CUỐI; clip có đoạn
  không tay bên trong ≥ `hand_lost_ms` bị loại (đếm). Chỉ ghép clip cùng (người ký, phiên) có cùng kích thước khung + fps (lệch → loại, đếm).
- Chuỗi (tất định, đặt trước):
  - **L (chữ cái, có gate):** mỗi (người ký, phiên): mọi lớp chữ cái theo `sorted()` nhãn, mỗi lớp 1 clip (sample_id nhỏ nhất).
  - **T (chữ → dấu, chỉ báo cáo):** mỗi (người ký, phiên) × mỗi dấu: [clip lớp `a`, clip dấu].
  - **O (lặp, chỉ báo cáo):** mỗi (người ký, phiên), lớp `o` và `e` nếu có ≥ 2 clip: [clip 1, clip 2].
- Mối ghép (bắt buộc truyền bằng CLI, không mặc định trong mã: `--join-ms 0,300,600`): 0 = nối thẳng; J > 0 = chèn `round(J × fps / 1000)`
  khung nội suy TUYẾN TÍNH landmark thô từ khung có tay cuối của clip trước tới khung có tay đầu của clip sau, handedness của clip trước —
  khung TỔNG HỢP, ghi rõ trong JSON. Timestamp = chỉ số khung toàn chuỗi × 1000 / fps.
- Chạy `Level1SignSegmenter` (push từng khung, flush cuối) với các config truyền bằng `--config NAME=PATH` (mỗi config ghi sha256 + nguồn commit).
- Gán segment: mỗi khung biết nguồn (clip i hoặc "join"); segment thuộc nguồn chiếm đa số khung (hòa → nguồn sớm hơn). Segment thuộc "join" = RÁC.
- Chỉ số mỗi (config, loại chuỗi, join): n_clips, số segment theo close_reason, `one_rate` (clip có đúng 1 segment), `miss_rate` (0), `multi_rate`
  (≥ 2), `garbage_per_clip` (segment rác / n_clips), `order_ok` (chỉ số clip của các segment không giảm), `hand_lost` (số segment hand_lost), và
  (tùy chọn nếu có checkpoint) `label_agrees` = nhãn segment == nhãn phân loại trọn clip (BÁO CÁO, không gate, không phải độ chính xác).
  `one_rate` của G1 tính thêm bản "covered" = chỉ các clip mà cặp (clip trước, clip này) có `between ≥ rearm_pose_dist` (clip đầu chuỗi luôn tính).
- G6 trên clip ĐƠN: chạy bộ tách trên mọi clip hauuto (như AC-S18) → `single_segment_rate` theo nhóm chữ cái / dấu thanh.
- Tùy chọn R4 (cắt được): ghép VIDEO gốc (nối thẳng, cùng (người ký, phiên)) vào `_work/_plan15/concat/*.mp4` rồi
  `level1_demo.py --source <file> --pace realtime --headless --out-json _work/_plan15/concat/<tên>.json`; tổng hợp số segment / số clip /
  processing_fps / dropped — chỉ báo cáo (ảnh hưởng bỏ khung), không gate, không chọn tham số.

### 3.6 Quan hệ với A2a/A2b/A3 và thứ tự tối ưu cho demo sớm
- R0 (script + test, không sửa bộ tách) TRƯỚC A2a: rẻ (0,5 h), có luật bác bỏ giả thuyết — nếu sai thì không làm R1. Đếm segment không phụ
  thuộc lỗi cắt đuôi (số segment hold 670/670 bằng nhau, 15-lan-sua-2 §1).
- A2a TRƯỚC R1: R1 sửa cùng hàm `push`; AC-S18 của A2a (bằng hệt 4a55bf0 trên 636 clip) là lưới an toàn chứng minh "tắt luật ⇒ không đổi".
- A2b TRƯỚC R2: `--write-pose-config` dùng lại helper lấy commit evidence bằng git của A2b (không dự phòng gõ tay).
- A3: không đổi quy tắc; SAU = config A2b (luật tư thế tắt). G6 của R3 là kiểm không-hồi-quy riêng của luật tư thế. A3 sau R3 (không chặn demo).
- Demo dùng được (chữ liên tiếp) sau R3 ≈ 5,75 h công (R0 0,5 + A2a 1 + R1 1,5 + A2b 0,75 + R2 1 + R3 1).

## 4. Chia việc (agy; mỗi bước 1 commit `15: <mã> …`; JSON sinh tại commit mã sạch, commit riêng; quy ước §4 của 15-lan-sua-1 giữ nguyên:
impact trước khi sửa symbol có sẵn, detect-changes trước commit, test đỏ trước, AC-G + AC1-ngắn trước mỗi commit)

| # | Bước | Nội dung | Phụ thuộc | Giờ | Model |
|---|---|---|---|---|---|
| 1 | **R0** | `scripts/level1_rearm_check.py` phần ghép chuỗi + gán segment + chỉ số (§3.5, chưa có G6/pose) + `tests/test_level1_rearm_check.py` (AC-RC1…RC4). Tại commit sạch chạy `--config current=configs/level1_realtime.json --config before_a2=_work/_plan15/config_before.json` (= `git show 3ebc7b9:configs/level1_realtime.json` điền `tail_still_keep_ms = hold_ms`) `--join-ms 0,300,600` → `reports/level1_realtime_<D>/rearm_check_r0.json` (commit riêng). Áp luật R0 (§5). Ghi 15-progress số đọc từ JSON + kết quả lệnh đếm U1 (§2.2). | — | 0,5 | gemini/high |
| 2 | **A2a** | Như 15-lan-sua-2 §7 (không đổi). | R0 | 1 | opus/high |
| 3 | **R1** | Test trước (AC-RA1…RA11, đỏ) → `pose_distance`, luật 1–3 §3.2, khóa mới trong `SEGMENTER_KEYS` + `CONFIG_SPEC` (+ kind "bool"); config: thêm `pose_change_rules: false`, `rearm_pose_dist` giữ chỗ, `pose_over_jitter_ratio: 2.0`, cập nhật reason `rearm_move_ms`; docstring mô-đun. Ngoại lệ test cũ: cuối §4. | A2a | 1,5 | opus/high |
| 4 | **A2b** | Như 15-lan-sua-2 §7 (không đổi; config sinh lại giữ nguyên các khóa R1 từng byte). | R1 | 0,75 | gemini/high |
| 5 | **R2** | Script thêm `--pose-evidence --out …/pose_evidence.json` (P1, P2) + `--write-pose-config` + test (AC-RP1…RP4). Tại commit sạch → commit `pose_evidence.json` → `--write-pose-config` → commit config riêng (`15: R2 config`). P2 coverage < 0,80 → DỪNG. | A2b | 1 | opus/high |
| 6 | **R3** | Thêm G6 vào script; chạy `--config off=<config R2, pose_change_rules=false> --config on=<bản sao config R2 trong _work với pose_change_rules=true> --join-ms 0,300,600` → `rearm_check_r3.json` (commit). G1–G6 đạt → đặt `pose_change_rules: true` trong config (commit riêng `15: R3 config`); không đạt → DỪNG, báo planner, config giữ false. Sau đó orchestrator báo người dùng U1c. | R2 | 1 | gemini/high |
| 7 | **A3** | Như 15-lan-sua-2 §5 (SAU = config A2b). | R3 | 1 | opus/high |
| 8 | **C1** | Như cũ + Giới hạn §6 dưới + dòng hướng dẫn chữ lặp. | A3 | 1 | gemini/high |
| 9 | R4, A4, C2 | Tùy chọn, cắt trước tiên (R4 0,5 h). | — | — | — |

Tổng thêm so với 15-lan-sua-2: +4 h bắt buộc (R0–R3). Thứ tự cắt khi thiếu ngân sách: R4 → A4 → C2 → `--summary` của C1 → A3. KHÔNG cắt
R0–R3 (demo không dùng được nếu thiếu), A2a.
**U1c (người dùng, ~5 phút, sau R3, không chặn):** `level1_demo.py --source 0 --display-mirror --out-json _work/u1c.json`, ký "b a c" không
rút tay, giữ yên chữ cuối ~3 giây, thử "oo" bằng phím `r`. JSON ở `_work/`, không commit, không dùng để chọn tham số.
**Test cũ:** chỉ THÊM. Ngoại lệ DUY NHẤT (R1, cùng kiểu A2): thêm 3 khóa mới (`pose_change_rules: False`, `rearm_pose_dist` bất kỳ > 0,
`pose_over_jitter_ratio`) vào dict tham số/config cục bộ của test hiện có (PARAMS của test_level1_segmenter, config dựng tay trong
test_level1_core/demo/segment_report, bộ dựng config của AC-S18). Không đổi assertion nào. Test cũ đỏ sau đó → DỪNG, báo planner.

## 5. Tiêu chí chấp nhận (hợp đồng; coder không đổi)
Lệnh chung: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_level1_segmenter.py tests/test_level1_rearm.py tests/test_level1_rearm_check.py tests/test_level1_segment_report.py tests/test_level1_core.py tests/test_level1_demo.py tests/test_level1_guard.py -q`
→ 0 failed; skip chỉ khi thiếu file gitignored (kiểu `skipUnless` như `tests/test_level1_core.py:179`), trên máy dev KHÔNG skip. Cộng
AC1-ngắn + AC-S/AC-C/AC-E1/AC-G như cũ, 0 failed (test chập chờn đã biết xử lý như §5 AC1 gốc). Chuỗi landmark trong test đơn vị là chuỗi
TỔNG HỢP có kiểm soát (ghi trong docstring như `tests/test_level1_segmenter.py:4-6`).

**R0 (`tests/test_level1_rearm_check.py`):**
- AC-RC1 bỏ khung không tay đầu/cuối; clip có đoạn không tay trong ≥ hand_lost_ms bị loại và đếm; kích thước/fps lệch → loại, đếm.
- AC-RC2 nội suy: join 0 ⇒ không có khung chèn; join J > 0 ⇒ đúng `round(J × fps / 1000)` khung, giá trị nội suy tuyến tính đúng (so số), nguồn "join".
- AC-RC3 gán đa số, rác, `order_ok`, các tỉ lệ (kể cả bản "covered") đúng trên ví dụ tay (chuỗi tổng hợp 3 "clip").
- AC-RC4 `generated_by`, sha256 config, câu "not accuracy" có trong JSON; thiếu `--join-ms` → lỗi argparse (không mặc định).
- **Luật R0 (đặt trước, áp lên `rearm_check_r0.json`):** config `current`, chuỗi L, join 0 VÀ 300 đều có `one_rate ≥ 0,90` ⇒ giả thuyết SAI
  trên dữ liệu ghép ⇒ DỪNG, báo planner (không làm R1). Ngược lại đi tiếp; ghi `one_rate`, `miss_rate`, `hand_lost` của cả hai config vào
  15-progress (đọc từ JSON).

**R1 (`tests/test_level1_rearm.py`; hình dạng A/B tổng hợp có `pose_distance(A, B)` biết trước; params test riêng):**
- AC-RA1 giữ A 1 s → chuyển A→B trong 200 ms, cổ tay đứng yên, tốc độ hình dạng lúc chuyển nằm DƯỚI move_speed của params test (test assert
  điều này) → giữ B 1 s, không mất tay: đúng 2 segment `hold`; segment 2 có `t_start_ms` = ts khung đầu có `d ≥ rearm_pose_dist`; 0 WordGap.
  Cùng luồng với `pose_change_rules=false`: đúng 1 segment (tái hiện lỗi U1b).
- AC-RA2 giữ A 5 s (sau phát): đúng 1 segment (không phát lặp).
- AC-RA3 A có nhiễu đặt sao cho `d < rearm_pose_dist / 2` trong 5 s, cộng một khung lệch đơn lẻ ≥ ngưỡng: đúng 1 segment.
- AC-RA4 chuyển A→B chậm trong 2 s với tốc độ hình dạng ≤ still_speed và thời gian đi hết `rearm_pose_dist` < hold_ms (test assert cả hai):
  bật luật ⇒ đúng 2 segment (không segment lưng chừng thứ 3) và khung cuối segment 2 có `pose_distance(·, B) < rearm_pose_dist`; tắt luật ⇒
  đúng 1 segment.
- AC-RA5 A giữ → nảy tay (hình dạng A, cổ tay `M ≥ move_speed` ≥ rearm_move_ms) → giữ A: 2 segment ở cả bật và tắt (re-arm chuyển động giữ).
- AC-RA6 tắt luật: trên mọi luồng của AC-RA1…RA5 và AC-S16/S17, sự kiện bằng hệt (array_equal mọi trường) giữa hai giá trị `rearm_pose_dist`.
- AC-RA7 mất tay ≥ hand_lost_ms rồi quay lại cùng A: phát lại A (hành vi cũ), neo bị xóa; `reset()` xóa neo và `_pose_since`.
- AC-RA8 neo = trung bình cửa sổ `motion_window_ms` trước t_emit: một khung lệch ngay tại t_emit không gây re-arm.
- AC-RA9 `pose_distance` bằng công thức tay trên mảng ngẫu nhiên seed cố định; script gọi đúng hàm này (kiểm bằng `is`/mock như R'1b).
- AC-RA10 config: thiếu khóa mới → ValueError; `pose_change_rules` không phải bool (kể cả 0/1) → ValueError; `rearm_pose_dist ≤ 0` → ValueError.
- AC-RA11 `status()` giữ 4 khóa cũ cùng nghĩa; AC-S18 (bổ sung §0) xanh; AC-G không có phát hiện mới trong file của 15.

**R2:**
- AC-RP1 P1/P2 trên clip tổng hợp: giá trị khớp tính tay; clip không có khung đứng yên đếm riêng.
- AC-RP2 `--write-pose-config`: evidence chưa commit / bẩn → RuntimeError, config không đổi từng byte; thành công → chỉ `rearm_pose_dist` đổi
  (value; source có commit lấy bằng git; reason không chứa chữ số); mọi khóa khác bằng hệt từng byte.
- AC-RP3 `pose_evidence.json` có `generated_by` (code_dirty false), sha256 manifest/config, coverage, danh sách cặp dưới ngưỡng, câu "not accuracy".
- AC-RP4 test của A2b (AC-W1…W3) vẫn xanh, không sửa. Luật dừng P2 như §3.4.

**R3 (gate đặt trước, áp lên `rearm_check_r3.json`, config `on`; số đọc từ JSON vào 15-progress):**
- G1 chuỗi L, join 0 và 300: `one_rate` bản "covered" ≥ 0,90 (bản đầy đủ báo cáo cạnh bên).
- G2 chuỗi L, mọi join: `multi_rate ≤ 0,05` (không phát lặp khi giữ yên — clip train có đuôi giữ yên dài).
- G3 mọi chuỗi: `hand_lost == 0` (không cần mất tay).
- G4 mọi chuỗi L: `order_ok` 100%.
- G5 chuỗi L, join 300 và 600: `garbage_per_clip ≤ 0,05`.
- G6 clip đơn: `single_segment_rate(on) ≥ single_segment_rate(off) − 0,02` cho cả nhóm chữ cái và nhóm dấu thanh.
- Chuỗi T, O, `label_agrees`, G1 ở join 600: chỉ báo cáo. Bất kỳ G nào trượt → DỪNG, báo planner; KHÔNG thử giá trị/tỉ lệ khác, không đổi gate.

## 5b. Phạm vi file
```scope
src/inference/level1_textbox.py
src/inference/level1_core.py
src/inference/level1_segmenter.py
level1_demo.py
configs/level1_realtime.json
scripts/level1_segment_report.py
scripts/level1_replay_clips.py
scripts/level1_rearm_check.py
tests/test_level1_*.py
docs/level1_desktop.md
docs/progress_log.md
docs/plans/15-progress.md
reports/level1_realtime_*
```
Độ khó: M (R1: L); vùng nhạy cảm: có (bộ tách đoạn realtime, config hiệu chỉnh, tiền xử lý dùng chung `normalize_hand_landmarks` — chỉ GỌI,
không sửa). KHÔNG đụng: kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`, `tests/test_backend_source_guard.py`,
`src/data/alphabet_preprocessing.py`, model mặc định. File tạm/video ghép: `_work/_plan15/`, không commit.

## 6. Rủi ro dữ liệu/ML (+ Giới hạn đưa vào docs/level1_desktop.md ở C1)
- Lệch train–realtime: tiền xử lý phân loại KHÔNG đổi (AC-E1 giữ). Luật mới chỉ đổi CHỖ CẮT segment; segment bắt đầu từ `_pose_since` (giữa
  lúc chuyển tay), trong khi clip train phần lớn bắt đầu khi tay đã ở tư thế (leading_still p50 275 ms, `tone_evidence.json:599`); `label_agrees`
  báo cáo ảnh hưởng, không gate.
- Ghép clip ≠ chuyển tay thật: nối thẳng là bước nhảy một khung (dễ hơn thực tế); nội suy tuyến tính là khung tổng hợp. R0/R3 là kiểm LOGIC,
  không phải độ chính xác hay trải nghiệm webcam; U1c là cảm nhận thật (không phải số báo cáo).
- Cỡ mẫu: 4 người ký hauuto; P1/P2 trên dữ liệu train của checkpoint (không rò rỉ vì không báo độ chính xác). Cặp chữ hình dạng gần nhau
  không re-arm theo tư thế — danh sách từ P2 vào Giới hạn.
- N không chuẩn hóa xoay: xoay cổ tay cũng tính là đổi tư thế (chủ ý — một số chữ khác nhau ở hướng tay); đổi tay trái/phải cũng re-arm.
- Dấu thanh sau chữ: re-arm theo tư thế chỉ khi hình dạng dấu khác chữ trước; còn lại cần chuyển động/rút tay/phím 1–5 (chuỗi T báo cáo).
- Giới hạn thêm: "chữ lặp (oo, ee): nảy tay rõ hoặc phím `r`"; "kiểm re-arm trên clip train ghép, không phải phiên webcam".

## 7. Điểm dừng
Không có điểm dừng bắt buộc CẦN NGƯỜI DÙNG: không đổi model mặc định, không cần dữ liệu người dùng (U1c tùy chọn, không chặn), không đụng
thay đổi chưa commit của người dùng, mọi config có commit riêng (hoàn tác bằng git). Điểm dừng cho coder (báo planner): luật R0 bác giả
thuyết; P2 coverage < 0,80; bất kỳ G1–G6 trượt; test cũ đỏ ngoài ngoại lệ §4; AC-S18 với luật tắt không bằng hệt.

## Dòng con trỏ (orchestrator chèn vào đầu docs/plans/15-lan-sua-2.md)
> **LẦN SỬA 3 (2026-10-04):** re-arm chữ liên tiếp không rút tay (luật tư thế `pose_change_rules`/`rearm_pose_dist`), thứ tự bước mới R0 → A2a → R1 → A2b → R2 → R3 → A3 → C1, bổ sung AC-S18 và config SAU của A3 — đọc `docs/plans/15-lan-sua-3.md` trước khi làm bất kỳ bước nào còn lại của 15.
