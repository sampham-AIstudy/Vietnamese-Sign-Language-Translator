# 15 — LẦN SỬA 4: re-arm chữ liên tiếp theo DỰ ĐOÁN classifier trên cửa sổ trượt (thay luật tư thế đã dừng ở R2)

Có hiệu lực như nằm trong kế hoạch 15. Đè lên `docs/plans/15-lan-sua-3.md` ở đúng các chỗ nêu ở §0; mọi phần khác của 15 và các lần sửa 1–3
giữ nguyên. Người lập: vslt-planner (phiên cloud 2026-10-05), nhánh `cloud/2026-10-04-level1-rearm`, HEAD `22ab544`.

**CẦN NGƯỜI DÙNG — CÓ ĐIỀU KIỆN (§7 mục 2):** bắt đầu KHÔNG cần người dùng. Chỉ khi G6 nhóm dấu thanh trượt (đo thăm dò §2.4 cho thấy có
nguy cơ) thì coder dừng và người dùng chọn một trong hai phương án đã ghi sẵn ở §7. Không đổi model mặc định.

## 0. Chỗ thay trong 15-lan-sua-3
| Chỗ | Thay/bổ sung bằng |
|---|---|
| §3.2–§3.4 (luật tư thế, P1/P2) | ĐÓNG: luật tư thế giữ nguyên trong mã, `pose_change_rules = false`, `rearm_pose_dist` giữ chỗ 1.0. Không làm `--write-pose-config`, không chạy R3 với luật tư thế. Lý do §2.1. |
| §4 bảng, bước R2 (phần còn lại), R3 | Thay bằng K1 → D1 → D2 → D3 → D4 (§4 dưới). A3, C1, R4/A4/C2 giữ, chạy SAU D4. |
| §5 R3 (G1–G6) | §5 dưới: G1–G6 GIỮ ngưỡng và ý nghĩa, định nghĩa lại cho đường classifier (ghi rõ TRƯỚC khi đo, §5.1); thêm G7 chỉ báo cáo. |
| §6 Giới hạn | Thêm các dòng §6 dưới. |
| U1c | Giữ, chạy sau D4 (hoặc sau K1 nếu D4 dừng). |

## 1. Mục tiêu và DoD
Ký liên tiếp nhiều chữ không rút tay (b → a → c …) ra đúng từng chữ một lần, giữ yên lâu không phát lặp, không thêm chữ rác khi chuyển tay;
có đường dự phòng thủ công chắc chắn cho buổi báo cáo (6–8/10). Phục vụ DoD 2 (đánh vần → ghép từ, desktop), DoD 6 (token chỉ từ model hoặc
phím có ghi nguồn), DoD 7 (tiền xử lý phân loại KHÔNG đổi: mọi dự đoán vẫn đi qua `alphabet_clip_features` + checkpoint triển khai; E1 giữ).

## 2. Phân tích (có số)

Nguồn số: (a) JSON đã commit (`reports/level1_realtime_2026-10-05/pose_evidence.json`, `reports/level1_realtime_2026-10-04/rearm_check_r0.json`);
(b) đo THĂM DÒ của planner bằng script trong `docs/plans/15-lan-sua-4-do/` (chạy tại `22ab544`, dữ liệu khôi phục như prompt cloud §1:
686 npz kernel `phmvnsm33/vsl-extract-alphabet`, checkpoint sha256 `a6311820…5b708a2` khớp). Lệnh (từ gốc repo):
```
PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze.py    # → measure.json  (chuyển động mối ghép, tư thế, chi phí, cửa sổ trượt thô)
PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze2.py   # → measure2.json (ngưỡng chuyển động riêng, bộ giải mã, QIPEDC)
PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze3.py   # → measure3.json (kết hợp: hold cũ + re-arm theo classifier)
PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze4.py   # → measure4.json (P1 bỏ chữ có dấu phụ — hậu kiểm, không phải luật mới)
PYTHONIOENCODING=utf-8 .venv/bin/python docs/plans/15-lan-sua-4-do/analyze5.py   # → measure5.json (bộ giải mã + luật thay chữ gốc→chữ có dấu phụ)
```
Số (b) là THĂM DÒ trên clip TRAIN của checkpoint triển khai (model khớp 100% nhãn trọn clip trên 193 clip chuỗi L — `measure.json`
`whole_clip_train_agreement_with_symbol` = 1.0 ⇒ mọi số dính classifier đều LẠC QUAN), chuỗi ghép là tổng hợp; không phải độ chính xác,
không phải số báo cáo. Số chính thức do coder sinh ở D4 tại commit sạch. Chỉ số "rác" trong (b) CHẶT hơn R0: phát ra ở khung mối ghép HOẶC nhãn
≠ nhãn trọn clip của clip đang chạy.

### 2.1 Vì sao re-arm theo tư thế không tách được chữ (R2 dừng đúng luật)
- P2: `rearm_pose_dist` = 2 × p95 jitter = 0.6919; 1985/3193 cặp chữ khác nhau có khoảng cách < ngưỡng ⇒ coverage 0.3783; trung vị khoảng cách
  hai chữ 0.5802 (`pose_evidence.json` `calibration.p2`).
- Nguyên nhân 1 — jitter bị thổi phồng bởi 6 chữ có dấu phụ: trung vị `jitter_clip` của â 0.283, ê 0.261, ư 0.259, ô 0.213, ă 0.211, ơ 0.134,
  so với 0.021–0.084 ở 21/23 chữ còn lại (`measure.json` `pose.jitter_clip_median_by_symbol`). Trong VSL, chữ có dấu phụ = hình tay chữ gốc +
  một CHUYỂN ĐỘNG; "đoạn đứng yên dài nhất" (M_t ≤ still_speed 2.53) của chúng chứa chính chuyển động đó.
- Nguyên nhân 2 — về bản chất hình tay không phân biệt cặp gốc/biến thể: a–ă, o–ô, o–ơ, u–ư dưới ngưỡng ở cả 8 phiên, a–â, e–ê ở 7 phiên;
  129/300 cặp nhãn dưới ngưỡng có chữ dấu phụ (`pose_evidence.json` `pairs_below`).
- Hậu kiểm (KHÔNG phải luật mới, chỉ để biết sửa P1 có cứu được không): bỏ 6 chữ đó khỏi P1 ⇒ ngưỡng 0.4224, coverage cặp chữ gốc 0.812 nhưng
  coverage MỌI cặp chữ ở ngưỡng đó 0.754 < 0.80 (`measure4.json`). Khoảng cách tới chữ khác gần nhất (cùng phiên): trung vị 0.215; 25% chữ
  có chữ gần nhất < 2 × jitter của chính nó (`measure.json` `pose.nearest_*`). ⇒ Không có ngưỡng tư thế đơn nào vừa chống rung vừa tách chữ.
  Kết luận: ĐÓNG hướng tư thế, không nới P2.

### 2.2 Vì sao re-arm theo chuyển động không tách được chữ, kể cả với ngưỡng riêng thấp hơn (phương án 2)
- Mối ghép nội suy 300 ms giữa hai chữ (tổng hợp): trung vị M_t trong mối ghép p50 2.69 ≈ still_speed 2.53; 40.5% mối ghép KHÔNG có khung nào
  vượt still_speed, chỉ 27.6% chạm move_speed 5.06 (600 ms: 63.2% / 15.7%) (`measure.json` `join_motion`). Đúng với R0: `current` L one_rate
  0.311 (join 0) / 0.373 (join 300) (`rearm_check_r0.json`).
- Ngưỡng re-arm riêng X (chuyển động ≥ X liên tục ≥ rearm_move_ms 150) — tỉ lệ mối ghép 300 ms được re-arm và tỉ lệ clip chữ cái ĐƠN có đoạn
  ≥ X sau 400 ms đầu (= nguy cơ phát lặp khi đang giữ một chữ) (`measure2.json` `motion_rearm_lower_threshold`):

  | X | mối ghép 300 ms re-arm | mối ghép 600 ms | clip đơn có nguy cơ lặp |
  |---|---|---|---|
  | 1.0 | 0.984 | 0.778 | 0.484 |
  | 1.5 | 0.854 | 0.600 | 0.369 |
  | 2.0 | 0.708 | 0.486 | 0.265 |
  | 2.53 (= still) | 0.589 | 0.395 | 0.218 |
  | 5.06 (= move, hiện tại) | 0.276 | 0.146 | 0.098 |

  Không có X nào vừa ≥ 0.90 mối ghép vừa ≤ 0.05 nguy cơ lặp. Thêm nữa, chuyển động trong mối ghép do CHÍNH cách nội suy quyết định (tổng hợp)
  ⇒ hiệu chỉnh X từ chuỗi ghép là vòng tròn. Kết luận: BÁC phương án 2.

### 2.3 Classifier trên cửa sổ trượt (phương án 1) và kết hợp với hold (phương án 3)
Chi phí realtime (`measure.json` `cost_ms_this_cloud_cpu`, CPU cloud 4 luồng): forward BiGRU [1,30,63] p50 2.14 ms / p95 2.72 ms; đặc trưng
`alphabet_clip_features` 24 khung p50 0.06 ms; `push` bộ tách p50 0.07 ms. Một lượt mỗi khung có tay ở ~25 khung/s ≈ 2.2 ms trên ~40 ms ngân sách
khung (máy người dùng phải đo lại — chặng `window_classify` mới, §3.4).

Bộ giải mã đổi nhãn (D): mỗi khung có tay, cửa sổ = các khung trong `cls_window_ms` gần nhất → `alphabet_clip_features` → softmax; phát nhãn k
khi top-1 = k với xác suất ≥ `cls_conf` liên tục ≥ `cls_stable_ms` và k ≠ nhãn phát gần nhất; mất tay ≥ `hand_lost_ms` xóa "nhãn gần nhất".

| Biến thể (cửa sổ 1000 ms, conf 0.9, ổn định 300 ms trừ khi ghi) | L join0 one / rác | L join300 one / rác | L join600 one / rác | clip đơn chữ cái: đúng 1 / ≥2 | clip đơn dấu: đúng 1 / ≥2 |
|---|---|---|---|---|---|
| Bộ tách hiện tại (luật tư thế tắt), cùng thước đo | 0.233 / 0.119 | 0.259 / 0.155 | 0.228 / 0.145 | 0.884 / 0.116 | 0.872 / 0.128 |
| (1) D thuần | 0.979 / 0.052 | 0.979 / 0.078 | 0.984 / 0.078 | 0.796 / 0.190 | 0.795 / 0.128 |
| (1) D + điều kiện đứng yên (M_t ≤ still) | 0.855 / 0.047 | 0.855 / 0.073 | 0.865 / 0.078 | 0.814* / 0.118 | 0.786* / 0.103 |
| (3) hold cũ + re-arm khi nhãn cửa sổ đổi | 0.829 / 0.280 | 0.829 / 0.337 | 0.829 / 0.332 | 0.724 / 0.277 | 0.581 / 0.419 |
| **(1) D + luật thay chữ gốc→chữ dấu phụ** | **0.979 / 0.021** | **0.969 / 0.036** | **0.979 / 0.031** | **0.961 / 0.026** | 0.795 / 0.128 |

(Nguồn: dòng 1 và (3) `measure3.json`; (1) `measure2.json` `decoders`; dòng cuối `measure5.json` `w1000_c0.9_s300_replace1`.
\* = 1 − zero − multi.)
- 70% lần phát ≥ 2 ở clip đơn của D thuần là cặp gốc → biến thể trong chính clip chữ biến thể: e→ê 19, a→â 17, u→ư 15, a→ă 12, o→ơ 12, o→ô 9
  (`measure5.json` `top_multi_patterns`) — đúng cơ chế §2.1 (cửa sổ thấy hình tay chữ gốc trước khi chuyển động dấu phụ xong).
  Luật thay: nếu nhãn mới ổn định là BIẾN THỂ của nhãn vừa phát (ă/â→a, ê→e, ô/ơ→o, ư→u, đ→d) và tay chưa mất, thì THAY token vừa phát thay vì
  thêm ⇒ clip đơn chữ cái đúng-1 0.796 → 0.961, rác L giảm ~một nửa.
- (3) tệ hơn (1): segment hold được phân loại trên đoạn cắt ngắn và nhãn cửa sổ trong lúc giữ chữ dấu phụ khác nhãn segment ⇒ re-arm giả.
- Dấu thanh với D: 0.795 đúng-1, kém bộ tách hiện tại 0.872 (lỗi chính: dấu huyền→dấu nặng, dấu ngã→dấu hỏi giữa nét). Dấu thanh vốn yếu offline
  (40.83%, 15-lan-sua-1 §2.1) và đã có phím `1`–`5`.
- Người ký NGOÀI train (QIPEDC, 46 clip chữ cái một người, detection_rate ~0.5): trọn clip đúng 28/46; D thuần (1000/0.9/300) phát đúng ký hiệu ở
  25/46 clip, tổng 36 lần phát (`measure2.json` `qipedc`) — D không vượt giới hạn của model; số nhỏ, chỉ minh họa.

### 2.4 Kết luận phân tích
Chỉ classifier tách được chữ liên tiếp trên dữ liệu này (one_rate ~0.97–0.98 so với 0.23–0.37), nhờ dùng đúng thông tin model đã học (85.6%
chữ cái offline) thay vì hình học tay. Rủi ro còn lại: (i) số trên train lạc quan; (ii) clip đơn dấu thanh kém hơn hiện tại (nguy cơ trượt G6
nhóm dấu); (iii) tham số D do planner chọn SAU khi thăm dò trên chính chuỗi L ⇒ G1–G6 trên chuỗi L là kiểm LOGIC, không độc lập (ghi rõ; người
dùng thử U1c là kiểm thật).

## 3. Thiết kế (chọn: phương án 1 + luật thay biến thể, kèm phương án 4 phím "chữ kế"; phương án 2 bác; 3 bác; tư thế đóng)

### 3.1 Phím "chữ kế" `n` (phương án 4 — làm TRƯỚC, độc lập gate, đảm bảo demo)
- `Level1SignSegmenter.force_rearm(ts_ms)` (public, mới): `armed = True`, bộ đệm = [] (chỉ giữ khung từ ts trở đi), nếu đồng hồ hold đang chạy thì
  `_still_since = ts` (hold đếm lại từ lúc bấm, segment chỉ chứa khung sau phím), xóa neo/`_pose_since`. Đã armed ⇒ chỉ đặt lại bộ đệm/hold.
- Ở chế độ classifier (§3.2): phím `n` gọi `decoder.force_next(ts)` = xóa "nhãn gần nhất" ⇒ cho phép phát lại CÙNG chữ (chữ lặp oo, ee).
- `level1_demo.py`: `ord("n")` → hành động `next`; nhật ký sự kiện `{"event": "key", "key": "next", "source": "key"}`; dòng hướng dẫn HUD thêm `n: chữ kế`.
  Không tạo token (token vẫn chỉ từ model hoặc phím token có sẵn) ⇒ DoD 6 giữ.

### 3.2 Bộ giải mã nhãn `Level1LabelDecoder` (thuần numpy, trong `src/inference/level1_segmenter.py`)
- Vào mỗi khung: `push(ts_ms, has_hand, result)` với `result` = None (không tay / chưa đủ khung / chưa có kết quả) hoặc dict của
  `Level1Classifier.classify` (`status`, `prediction`, `confidence`). Ra: None hoặc `LabelEmit{seq, ts_ms, prediction, confidence, action ∈
  {"append","replace"}, run_since_ms, result}`.
- Luật (đặt trước, giống hệt bộ giải mã đã đo ở `measure5.json` trừ ghi chú):
  1. Nhãn khung = `prediction` nếu `status == "ok"` và `confidence ≥ cls_conf`, ngược lại None. Nhãn khác nhãn chạy hoặc None ⇒ chạy mới từ ts.
  2. Phát khi nhãn ≠ None, `ts − run_since ≥ cls_stable_ms`, nhãn ≠ `last`. Sau phát `last = nhãn`.
  3. Thay: nếu `VARIANT_BASE[nhãn] == last` (bảng hằng: ă, â→a; ê→e; ô, ơ→o; ư→u; đ→d — sự kiện ngôn ngữ, khóa bằng test) và đã có lần phát
     trước ⇒ `action = "replace"`.
  4. Không tay liên tục ≥ `hand_lost_ms` ⇒ `last = None`, chạy = None (rút tay rồi ký lại = cho phép lặp). `force_next(ts)` ⇒ `last = None`.
  5. Timestamp tăng ngặt (như bộ tách; vi phạm → ValueError).
- `WindowBuffer` (cùng file, thuần): giữ khung (raw, detected, handedness, ts, W, H) của `cls_window_ms` gần nhất; `segment(ts)` → `SignSegment`
  bản sao (close_reason `"window"`), None nếu < `min_detected_frames` khung có tay. Đầu vào `Level1Classifier.classify` KHÔNG đổi ⇒ tiền xử lý
  dùng chung, không công thức mới.
- Bộ tách cũ vẫn chạy song song cho trạng thái HUD, `hand_lost`, `WordGap`; ở chế độ classifier các `SignSegment` của nó KHÔNG được phân loại/nhận
  token (ghi số lượng vào JSON để đối chiếu).

### 3.3 Config (khóa mới; không giá trị mặc định trong mã; `validate_level1_config` kiểm)
| Khóa | Giá trị | source | reason (tóm tắt) |
|---|---|---|---|
| `rearm_mode` | `"motion_pose"` (đến khi D4 đạt) → `"classifier"` | design | enum {"motion_pose","classifier"}; đổi sang classifier chỉ bằng `--write-mode-config` khi G1–G6 đạt (reason ghi `<json>@<commit>`) |
| `cls_window_ms` | 1000 | design | chọn sau thăm dò planner trên chuỗi train ghép (15-lan-sua-4 §2.3); 1500 tương tự, 600 nhiều rác |
| `cls_conf` | 0.9 | design | như trên; 0.8 rác gấp ~2 |
| `cls_stable_ms` | 300 | design | như trên; bằng thứ tự với hold_ms 400 |
Reason ghi rõ "chọn sau thăm dò trên dữ liệu train, không phải hiệu chỉnh độc lập". `rearm_mode` cần kind mới `"enum"` trong `_check_value`.

### 3.4 App (`level1_demo.py`)
- `rearm_mode == "classifier"`: mỗi khung có tay → `WindowBuffer.push` → `segment(ts)`:
  - headless: phân loại đồng bộ (tất định, như hiện tại).
  - GUI/paced: gửi vào worker "chỉ giữ việc mới nhất" (việc cũ chưa chạy bị bỏ, đếm `window_dropped`); kết quả mang ts của khung → đưa vào
    decoder theo đúng thứ tự ts (kết quả bị bỏ = None cho khung đó). Không gọi model trên luồng chính (giữ ý AC-D5).
  - `LabelEmit` → `Level1Speller.on_label(seq, emit)`: `append` = như `on_result` (ngưỡng `accept_confidence` giữ nguyên); `replace` = thay token
    model cuối nếu đó đúng là chữ gốc (ngược lại append); nhật ký `{"event": "token", "action": "replace", "source": "model"}`.
- Chặng đo mới `window_classify` (n, mean, p50, p95), đếm `window_dropped`; JSON ghi `rearm_mode`.
- `rearm_mode == "motion_pose"`: hành vi bằng hệt hiện tại (test khóa).

## 4. Chia việc (mỗi bước 1 commit `15: <mã> …`; test viết trước, ghi đỏ/xanh vào 15-progress; impact trước khi sửa symbol có sẵn,
detect-changes trước commit; JSON sinh tại commit mã sạch, commit riêng; quy ước §4 của 15-lan-sua-1/-3 giữ)

| # | Bước | Nội dung | Phụ thuộc | Giờ |
|---|---|---|---|---|
| 1 | **K1** | §3.1: `force_rearm` + phím `n` (cả `KEY_ACTIONS`/HUD/nhật ký) + test AC-K1…K4. Sau K1 orchestrator báo người dùng có thể dùng `n` khi demo. | — | 0,75 |
| 2 | **D1** | `WindowBuffer`, `Level1LabelDecoder`, `VARIANT_BASE` + khóa config §3.3 (giá trị như bảng, `rearm_mode = "motion_pose"`) + kind "enum" + `Level1Speller.on_label` + test AC-D1…D9. | K1 | 1,5 |
| 3 | **D2** | Nối vào app §3.4 (headless đồng bộ, worker mới nhất, chặng `window_classify`) + test AC-A1…A5. | D1 | 1,5 |
| 4 | **D3** | `scripts/level1_rearm_check.py --decoder`: chạy D trên chuỗi L/T/O (join 0/300/600) + clip đơn + QIPEDC (báo cáo); chỉ số §5.1; gate G1–G6; `--write-mode-config`; test AC-C1…C5 (dữ liệu tổng hợp). | D1 | 1,5 |
| 5 | **D4** | Tại commit sạch: `python scripts/level1_rearm_check.py --decoder --config off=configs/level1_realtime.json --config on=configs/level1_realtime.json --set on:rearm_mode='"classifier"' --gates on:off --join-ms 0,300,600 --out reports/level1_realtime_<D>/rearm_check_d4.json` → commit JSON. Đạt hết ⇒ `--write-mode-config configs/level1_realtime.json --rearm-json <json>` → chạy lại test Level 1 + AC-E1 → commit `15: D4 config`. Trượt ⇒ DỪNG (§7). Tên cờ chính xác coder chốt, ghi 15-progress. | D2, D3 | 0,5 |
| — | U1c | Người dùng (không chặn): `level1_demo.py --source 0 --display-mirror --out-json _work/u1c.json`, ký "b a c" không rút tay, giữ chữ cuối ~3 s, thử "oo" bằng `n` (chế độ classifier) hoặc nảy tay (motion_pose). | D4 hoặc K1 | — |
| 6+ | A3, C1, (R4, A4, C2) | Như 15-lan-sua-3 §4; C1 thêm Giới hạn §6 dưới. A3 so TRƯỚC/SAU của A2 với `rearm_mode = "motion_pose"` (cô lập A2, như cũ). | D4 | như cũ |

Tổng ≈ 5,75 giờ (K1 0,75 + D1–D4 5). Thứ tự cắt khi thiếu ngân sách: R4 → A4 → C2 → `--summary` của C1 → A3 → D3/D4 (khi đó config giữ
`motion_pose`, demo dùng phím `n`; Giới hạn ghi "chữ liên tiếp cần phím n hoặc rút tay"). KHÔNG cắt K1.
**Test cũ:** chỉ THÊM. Ngoại lệ DUY NHẤT (cùng kiểu R1): thêm 4 khóa §3.3 vào dict tham số/config dựng tay của test hiện có (`rearm_mode`
= "motion_pose"). Không đổi assertion nào. Test cũ đỏ sau đó ⇒ DỪNG, báo planner.

## 5. Tiêu chí chấp nhận (hợp đồng; coder không đổi)
Lệnh chung: `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_level1_segmenter.py tests/test_level1_rearm.py tests/test_level1_decoder.py tests/test_level1_rearm_check.py tests/test_level1_rearm_gates.py tests/test_level1_segment_report.py tests/test_level1_pose_evidence.py tests/test_level1_core.py tests/test_level1_demo.py tests/test_level1_guard.py tests/test_level1_equivalence.py -q`
(local Windows: `.venv/Scripts/python`) → 0 failed, có dữ liệu thì 0 skip ngoài `test_u1_summary`. AC1-ngắn, AC-S18/S18b, AC-E1, AC-G
(`known=9 allowed=36`) như cũ. Chuỗi trong test đơn vị là dữ liệu TỔNG HỢP có kiểm soát (ghi docstring).

**K1:** K1 giữ A → hold → `force_rearm` → giữ A tiếp ≥ hold_ms ⇒ đúng 2 segment `hold`, segment 2 chỉ chứa khung ts ≥ lúc bấm; K2 đang armed:
`force_rearm` không tạo segment thêm; K3 `Level1App._key(ord("n"))` (dựng như test D hiện có) gọi đúng hàm theo `rearm_mode`, ghi sự kiện
`source "key"`, KHÔNG thêm token; K4 `motion_pose` không bấm `n` ⇒ sự kiện bằng hệt trước K1 trên luồng AC-S1…S18 (array_equal).

**D1:** D1 chuỗi kết quả tổng hợp A×0.5 s, B×0.5 s (conf 0.95) ⇒ phát A rồi B, ts phát = ts khung đầu + `cls_stable_ms` (≤ một khung lệch);
D2 conf dưới `cls_conf` hoặc chạy < stable ⇒ không phát; D3 A giữ 5 s ⇒ 1 lần; D4 A → mất tay ≥ hand_lost_ms → A ⇒ 2 lần; mất tay ngắn hơn ⇒ 1;
D5 `force_next` ⇒ A phát lại; D6 a → â ⇒ `replace`; â → a, a → b, a (mất tay) → â ⇒ `append`; bảng `VARIANT_BASE` đúng 7 cặp, mọi khóa/giá trị là
lớp của checkpoint (đọc `classes` nếu có checkpoint; không có ⇒ so với danh sách lớp trong `fingerspelling_compose`); D7 `WindowBuffer.segment`
== đúng các khung trong cửa sổ (array_equal), là bản sao, < min khung ⇒ None, và `classify(segment)` == `classify` của SignSegment dựng tay cùng
khung; D8 config: thiếu khóa mới / `rearm_mode` ngoài enum / số ≤ 0 / `cls_conf` ∉ (0,1] ⇒ ValueError; config thật nạp được; D9 Speller
`on_label` replace: token cuối là chữ gốc ⇒ thay, `text == compose(tokens)["text"]`, nhật ký `action "replace"`; token cuối khác ⇒ append.

**D2 (app):** A1 headless video `a_hau_A_001.mp4` với `rearm_mode` classifier ⇒ exit 0, JSON có `rearm_mode`, chặng `window_classify` (n =
số khung có kết quả), token chạy 2 lần giống hệt; A2 `motion_pose` ⇒ `tokens`/`segments` giống hệt trước D2 trên cùng video; A3 worker "mới nhất"
(classifier chậm định nghĩa trong test): không bao giờ trả kết quả cũ hơn kết quả đã trả, `window_dropped` đếm đúng, luồng chính vẫn xử lý > 1
khung trong thời gian đó; A4 AC-E3 giữ (không `Hands(`/`cv2.resize`, flip chỉ ở hiển thị); A5 guard: file mới/sửa 0 phát hiện mới.

**D3 (script):** C1 trên chuỗi tổng hợp 3 "clip" với kết quả classifier giả lập bằng hàm định nghĩa TRONG test: one/multi/miss/rác/order đúng
tính tay; C2 rác = phát ở khung "join" HOẶC nhãn ≠ nhãn trọn clip của clip chứa khung phát; C3 `--decoder` thiếu checkpoint ⇒ lỗi rõ (không
skip ngầm); C4 JSON có `generated_by` (code_dirty), sha256 config, `note` "train clips concatenated…; not accuracy", `note_vi`, `definitions`,
`exploratory_params_note` ("tham số D chọn sau thăm dò planner trên cùng chuỗi L — gate là kiểm logic"); C5 `--write-mode-config` chỉ đổi
`rearm_mode` khi JSON đã commit, sạch, `gates.all_pass`; ngược lại RuntimeError, config giữ từng byte (dùng helper `committed_evidence_ref`).

### 5.1 Gate D4 (ĐẶT TRƯỚC khi coder đo; ngưỡng G1–G6 giữ nguyên số; config `on` = `rearm_mode "classifier"`, `off` = config hiện hành)
Định nghĩa cho đường classifier (thay đổi so với 15-lan-sua-3 §5 nêu lý do TRƯỚC khi đo): "segment" của `on` = lần phát `append` (lần `replace`
không tính là segment mới; được đếm riêng); gán clip = nguồn của khung phát; "covered" của G1 bỏ (định nghĩa cũ dựa trên khoảng cách tư thế, không
còn nghĩa) — G1 dùng one_rate ĐẦY ĐỦ (chặt hơn bản covered); rác theo định nghĩa CHẶT C2 (chặt hơn R0, vốn chỉ đếm đa số khung mối ghép).
- G1 chuỗi L, join 0 và 300: `one_rate ≥ 0.90`.
- G2 chuỗi L, mọi join: `multi_rate ≤ 0.05`.
- G3 mọi chuỗi: lần phát cần mất tay = 0 (mọi `append` trong chuỗi L xảy ra khi tay liên tục).
- G4 mọi chuỗi L: `order_ok` 100%.
- G5 chuỗi L, join 300 và 600: `garbage_per_clip ≤ 0.05`.
- G6 clip đơn (mọi clip hauuto ≥ `min_detected_frames`, như R3): `one_rate(on) ≥ one_rate(off) − 0.02` cho nhóm chữ cái VÀ nhóm dấu thanh.
- G7 (CHỈ BÁO CÁO, không gate): 46 clip QIPEDC — tỉ lệ clip mà `on` phát nhãn trọn-clip của model và tỉ lệ tương ứng của `off`; lý do không
  gate: 1 người ký, detection_rate ~0.5, planner đã xem một nửa số này (D thuần) ở §2.3.
- Chuỗi T, O, `label_agrees`, `token_error_rate`: báo cáo. KHÔNG thử giá trị tham số khác, không đổi gate sau khi thấy số.

## 5b. Phạm vi file
Như §3b của 15-lan-sua-1 (+ 2 dòng đã thêm ở 15-lan-sua-3 §5b); không thêm file nguồn mới ngoài test:
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
Độ khó: M (D2: L); vùng nhạy cảm: có (bộ tách/giải mã realtime, config, đường phân loại dùng chung — chỉ GỌI `alphabet_clip_features`/`classify`,
không sửa). KHÔNG đụng: kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`, `tests/test_backend_source_guard.py`,
`src/data/alphabet_preprocessing.py`, `src/inference/fingerspelling_compose.py`, checkpoint/model mặc định. File tạm: `_work/_plan15/`.
Gợi ý model coder: K1, D3 gemini/high; D1, D2 opus/high.

## 6. Rủi ro dữ liệu/ML (+ Giới hạn cho docs/level1_desktop.md ở C1)
- **Lạc quan vì dữ liệu train:** model khớp 100% nhãn trọn clip trên clip dùng để ghép; gate D4 là kiểm LOGIC. Cửa sổ 1 s ngắn hơn clip train
  (~2–4 s) ⇒ lệch phân bố đầu vào (cùng hàm đặc trưng, khác độ dài trước khi lấy mẫu lại 30 khung); QIPEDC (G7) và U1c là tín hiệu ngoài train.
- **Chọn tham số sau khi thấy số:** `cls_*` chọn sau thăm dò trên chính chuỗi L; ghi trong reason config, JSON D4 và Giới hạn. Không được chỉnh
  tiếp theo kết quả D4 hay U1c (muốn chỉnh ⇒ lần sửa kế hoạch, dữ liệu mới, ghi "đã dùng để chỉnh").
- **Chữ lặp:** đổi nhãn không phát lại cùng chữ ⇒ oo/ee cần phím `n` hoặc rút tay (Giới hạn).
- **Chữ gốc ngay trước biến thể của nó** (vd "aă" liền nhau — hiếm trong tiếng Việt) bị gộp thành biến thể ⇒ cần `n` hoặc rút tay giữa hai chữ.
- **Dấu thanh** có thể kém hơn bộ tách cũ (§2.3); phím `1`–`5` giữ; G6 nhóm dấu là điểm quyết định (§7).
- **Chi phí:** +1 forward/khung có tay; máy yếu ⇒ worker bỏ việc cũ (đếm `window_dropped`), ổn định tính theo ms nên không đổi luật; đo ở U1c/U2.
- **Không đổi tiền xử lý phân loại** ⇒ E1 (train ↔ realtime bằng hệt trên trọn clip) giữ; tracker liên tục vẫn chưa đo (Giới hạn cũ).
- Giới hạn thêm: "Chữ liên tiếp được tách bằng dự đoán của model trên cửa sổ ~1 s; kiểm trên clip train ghép, không phải phiên webcam";
  "Luật tư thế (lần sửa 3) đã đo và bác: hình tay không phân biệt chữ gốc/chữ có dấu phụ (pose_evidence.json)"; "Phím `n` = chữ kế (dự phòng)".

## 7. Điểm dừng
Không có điểm dừng bắt buộc khi BẮT ĐẦU: không đổi model mặc định, không train, không cần dữ liệu người dùng, mọi đổi config có commit riêng.
Điểm dừng cho coder (ghi 15-progress, báo orchestrator → planner):
1. G1, G2, G3, G4, G5 hoặc G6 nhóm CHỮ CÁI trượt ⇒ DỪNG, config giữ `motion_pose`, demo dùng phím `n` (K1). Không thử tham số khác.
2. **Chỉ G6 nhóm DẤU THANH trượt (mọi gate khác đạt) ⇒ DỪNG, CẦN NGƯỜI DÙNG chọn** (ghi số từ JSON vào câu hỏi):
   (a) bật `classifier` cho buổi báo cáo, Giới hạn ghi "dấu thanh liên tiếp kém hơn chế độ cũ; dùng phím 1–5" (người dùng chấp nhận đánh đổi —
   KHÔNG phải nới gate, ghi rõ G6 dấu trượt); hoặc (b) giữ `motion_pose` + phím `n`. Khuyến nghị planner: (a), vì chữ cái liên tiếp là mục tiêu
   chính và dấu đã có phím; nhưng đây là thay đổi hành vi người dùng thấy ⇒ người dùng quyết.
3. Test cũ đỏ ngoài ngoại lệ §4; AC-S18/S18b, AC-E1, K4 hoặc A2 không còn bằng hệt.
4. Cần sửa file ngoài §5b, hoặc chặng `window_classify` làm app không chạy được trên máy người dùng (U1c báo) ⇒ planner lập lần sửa.

## Dòng con trỏ (orchestrator chèn vào đầu docs/plans/15-lan-sua-3.md)
> **LẦN SỬA 4 (2026-10-05):** luật tư thế đóng (R2 dừng đúng luật P2); re-arm chữ liên tiếp chuyển sang bộ giải mã đổi nhãn classifier trên cửa sổ trượt + phím `n` "chữ kế"; bước K1 → D1 → D2 → D3 → D4 thay R2 (phần còn lại)/R3; gate G1–G6 định nghĩa lại cho đường classifier — đọc `docs/plans/15-lan-sua-4.md` trước khi làm bất kỳ bước nào còn lại của 15.
