# 15 — LẦN SỬA 6: đổi ký hiệu liên tiếp (vd dấu nặng → dấu hỏi) vẫn phải rút tay mới nhận

Người lập: Antigravity (planner lượt này). Coder: cloud. Reviewer: Antigravity (kéo nhánh về, chạy lại test trên Windows).
Có hiệu lực như nằm trong kế hoạch 15 (sau `15-lan-sua-5.md`). Mọi thứ không nêu ở đây giữ nguyên.

## 0. Triệu chứng và ranh giới

- Triệu chứng (người dùng, 5/10 16:12): ký một ký hiệu xong, đổi sang ký hiệu khác (ví dụ dấu nặng → dấu hỏi) mà không rút tay thì app
  không nhận ký hiệu mới; rút tay ra rồi đưa vào mới nhận. Đây chính là lỗi U1b (4/10) mà chế độ `classifier` được làm ra để sửa.
- Ranh giới (giữ nguyên các quyết định đã chốt): KHÔNG train lại, KHÔNG đổi checkpoint/tiền xử lý, KHÔNG đổi `configs/level1_realtime.json`,
  KHÔNG sửa dòng test cũ (chỉ thêm), E1 bằng hệt giữ nguyên. Tham số quyết định chỉ chọn theo quy tắc đặt trước ở §5, không chọn sau khi xem số.

## 1. Bằng chứng đã kiểm (đọc từ mã và JSON thật, không phải suy đoán)

| # | Sự kiện | Nguồn |
|---|---|---|
| E1 | HUD KHÔNG hiện chế độ đang chạy và KHÔNG hiện nhãn/độ tin cậy của cửa sổ. Dòng "Trạng thái" và thanh tiến độ lấy từ `self.segmenter.status()` vô điều kiện, kể cả khi `rearm_mode = classifier` (lúc đó bộ tách cũ vẫn chạy nhưng kết quả của nó bị bỏ: `segments_not_classified` = 6 trong `_work/u1c.json`). Người dùng không thể thấy vì sao "khựng", và thanh tiến độ trên màn hình không liên quan tới quyết định phát ký tự. | `level1_demo.py:798-822` |
| E2 | Bộ giải mã chỉ phát khi: độ tin cậy cửa sổ ≥ `cls_conf` (0,9), cùng một nhãn liên tục ≥ `cls_stable_ms` (300 ms), và nhãn ≠ nhãn đã phát gần nhất. Nhãn đã phát chỉ bị xóa khi mất tay ≥ `hand_lost_ms` (300 ms) hoặc bấm `n`. ⇒ Khi mô hình vẫn đoán nhãn cũ, hoặc độ tin cậy < 0,9 suốt lúc đổi ký hiệu, KHÔNG có phát và cách duy nhất để thoát là rút tay. | `level1_segmenter.py:539-573` |
| E3 | Cửa sổ trượt 1 s. Mô hình được train trên CẢ clip đã cắt (2–4 s). Lúc đang đổi ký hiệu, cửa sổ chứa nửa ký hiệu cũ + chuyển động + nửa ký hiệu mới ⇒ độ tin cậy thấp. Chữ cái tĩnh hồi phục khi giữ yên đủ ~1 s; dấu thanh là cử chỉ động nên cửa sổ hầu như không bao giờ "sạch". | thiết kế D1/D2 + `rearm_check_d4.json` |
| E4 | Dấu thanh là điểm yếu đã đo: out-of-fold top-1 = 40,83% (n = 120): sắc 41,67, huyền 8,33, hỏi 33,33, ngã 45,83, nặng 75,00. Biến thể có quỹ đạo cổ tay đã thử và không tốt hơn (36,67 / 40,00). Checkpoint hiện tại không thấy quỹ đạo tay. | `SUMMARY.md` §1 |
| E5 | G6 dấu thanh trượt ở D4: classifier 0,80 so với 0,85 của chế độ cũ (clip train, lạc quan). Trên QIPEDC (người ký ngoài train, 46 clip) classifier phát đúng nhãn trọn clip 0,5435, kém chế độ cũ 0,7391. Người dùng webcam cũng là người ký ngoài train. | `rearm_check_d4.json`, `SUMMARY.md` §3 |
| E6 | Chuỗi dấu thanh ghép từ clip TRAIN: `one_rate` 0,9714, rác 0,11–0,14 mỗi clip, token error 0,1286. Nhãn "đúng" ở đây là nhãn của CHÍNH mô hình trên clip, nên đây là kiểm logic bộ giải mã, không nói gì về người ký mới. ⇒ logic bộ giải mã không hỏng trên dữ liệu train; vấn đề (nếu ở chế độ classifier) nằm ở khoảng cách train → webcam. | `rearm_check_d4.json` |
| E7 | `_work/u1c.json` (13:58) chạy đúng `rearm_mode = classifier`, 6 nhãn đều `append`, 0 `replace`, KHÔNG có lần đổi dấu → dấu thanh nào. Không tái hiện được lỗi, và JSON không ghi nhãn/độ tin cậy của từng cửa sổ nên không thể chẩn đoán từ nó. | `_work/u1c.json` |
| E8 | Chế độ `motion_pose` (lệnh KHÔNG có `--config`, đúng dòng "demo lv1" trong README chưa commit của người dùng): re-arm cần chuyển động cổ tay ≥ `move_speed` 5,06 chiều dài bàn tay/giây trong ≥ 150 ms. 69/120 clip dấu thanh KHÔNG có khung nào đạt ngưỡng này ⇒ đổi dấu chậm không re-arm ⇒ đúng triệu chứng. | `STATE.md`, `15-lan-sua-3.md` |
| E9 | Trên Windows (Git mặc định `core.autocrlf=true`), 2 test của C1/S2 đỏ vì CRLF đổi sha256 (`level1_realtime.json`, `SUMMARY.md`, `segment_check_*.json`), không vì logic. Reviewer đã phải đặt `core.autocrlf=false` cho repo này để chạy. | log reviewer 5/10 |

## 2. Giả thuyết và cách phân biệt (không chọn trước)

| Mã | Giả thuyết | Dấu hiệu trong trace (W1) |
|---|---|---|
| M0 | Đang chạy `motion_pose` (quên `--config`), không phải `classifier` | JSON/HUD ghi `rearm_mode` ≠ classifier. Xử lý: không cần sửa mã (E8), chỉ đổi lệnh. |
| M1 | Cổng độ tin cậy: top-1 cửa sổ < 0,9 suốt lúc đổi | nhiều cửa sổ `conf < cls_conf`, nhãn `None` |
| M2 | Mô hình vẫn đoán nhãn CŨ với độ tin cậy cao | cửa sổ `top1 == last` kéo dài sau khi người dùng đã đổi ký hiệu |
| M3 | Nhãn chập chờn, chuỗi ổn định không đủ 300 ms | `run_ms` bị đặt lại liên tục, `top1` đổi giữa các nhãn |
| M4 | Mô hình không tách được hai dấu (cùng hình tay, khác quỹ đạo) | `top1` ≈ đồng nhất giữa hai dấu, margin top-1/top-2 nhỏ |

M2 và M4 không sửa được bằng logic bộ giải mã; M1 và M3 có thể.

## 3. Việc của coder (vòng 1 — chỉ đo và hiển thị, KHÔNG đổi hành vi nhận ký tự)

Mỗi bước một commit `15: <mã> …`, test viết TRƯỚC, impact trước khi sửa symbol có sẵn, ghi 15-progress. Test cũ chỉ được thêm.

| # | Bước | Nội dung | Giờ |
|---|---|---|---|
| 1 | **W0** | `.gitattributes`: ép `eol=lf` cho `configs/*.json`, `reports/**/*.json`, `reports/**/*.md`, `docs/**/*.md` để test sha256 chạy đúng trên Windows mặc định. Test mới: `git ls-files --eol` của các file trên không có `w/crlf`. | 0,25 |
| 2 | **W1** | Cờ `--trace-windows` (mặc định TẮT) cho `level1_demo.py`. Khi bật, JSON có thêm khóa `window_trace`: mỗi cửa sổ phân loại một mục `{ts_ms, status, top1, conf, top2, conf2, run_label, run_ms, last, emitted}`. Khi tắt: JSON bằng hệt hiện tại (test so khóa). Giới hạn kích thước: tối đa 20 000 mục, quá thì ghi `truncated: true`. Không ghi landmark/khung hình. | 1,0 |
| 3 | **W2** | HUD chỉ ở chế độ `classifier`: thay dòng "Trạng thái" bằng dòng bộ giải mã `[classifier] cửa sổ: <top1> <conf> | giữ <ms>/<cls_stable_ms> | cuối: <last>` và ẩn thanh tiến độ của bộ tách cũ. Chế độ `motion_pose` bằng hệt (mọi test HUD cũ giữ nguyên). Thêm nhãn chế độ vào HUD ở cả hai chế độ nếu làm được mà không đổi số dòng panel của test cũ; nếu đổi số dòng ⇒ DỪNG, báo planner. | 0,75 |
| 4 | **W3** | `scripts/level1_trace_report.py --trace <json> [--expected "<ký hiệu1>,<ký hiệu2>,…"]`: phân loại từng đoạn chuyển ký hiệu theo M1–M4 và in bảng (đếm cửa sổ và tỉ lệ thời gian theo từng loại), đọc hoàn toàn từ `window_trace`. Tất định, test bằng trace tổng hợp. | 1,0 |

Tổng ≈ 3 giờ. Điểm dừng của coder (ghi 15-progress, báo planner): test cũ đỏ; cần sửa file ngoài §6; W2 buộc đổi số dòng panel của chế độ cũ; trace làm `frame_total` p50 tăng quá 5% so với không trace (đo bằng chính JSON, ghi số).

## 4. Việc của người dùng (U3, ~5 phút, sau W2 + W1)

Chạy từng lệnh, KHÔNG rút tay giữa các ký hiệu. Mỗi ký hiệu giữ ~2 s rồi đổi:
```
.venv\Scripts\python level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier.json --trace-windows --out-json _work/u3_tones.json
```
Phiên 1 (dấu): nặng → hỏi → ngã → sắc → huyền. Phiên 2 (chữ): b → a → c → o. Mỗi phiên một file JSON (`_work/u3_tones.json`, `_work/u3_letters.json`). JSON ở `_work/`, không commit, không chứa video.
Nhìn HUD trong lúc ký: dòng `[classifier] cửa sổ: … | cuối: …` là chẩn đoán trực tiếp. Gửi 2 file JSON cho reviewer (Antigravity đọc cục bộ, không cần cloud).

## 5. Bảng quyết định đặt trước cho VÒNG 2 (chưa làm; chọn SAU khi có trace, ghi vào 15-lan-sua-7)

Quy tắc chọn đặt trước: dùng đúng một mã chiếm > 50% thời gian cửa sổ trong các đoạn chuyển ký hiệu của phiên U3 làm nguyên nhân chính.

| Nguyên nhân chính | Hướng sửa được phép | Cổng (đặt trước) |
|---|---|---|
| M0 | Không sửa mã. Ghi lệnh `--config …` lên đầu README/`docs/level1_desktop.md` (README là file chưa commit của người dùng: chỉ ĐỀ XUẤT dòng, không sửa). | — |
| M1 | Ngưỡng độ tin cậy RIÊNG cho dấu thanh (`cls_conf_tone`, khóa mới, `source: design`, lý do ghi rõ), chọn theo quy tắc: phân vị 25 của `conf` các cửa sổ có `top1` đúng dấu trong phiên hiệu chỉnh U3a; kiểm trên phiên RIÊNG U3b (không dùng để chỉnh). | chuỗi D4 G1–G5 và G6 chữ cái không tụt; clip đơn dấu thanh không tụt quá 0,02 so với `off` 0,85; U3b: tỉ lệ đổi dấu đúng phải cao hơn lần đo U3 trước. Khóa mới bị khóa test như D1 (ngoại lệ thêm khóa vào dict test cũ). |
| M3 | Giảm đòi hỏi ổn định cho nhãn dấu thanh (`cls_stable_ms_tone`) hoặc nâng cửa sổ dấu lên theo độ dài cử chỉ trung vị của clip train (tính bằng code từ manifest). | như M1. |
| M2 hoặc M4 | KHÔNG sửa bộ giải mã (không phải lỗi logic). Ghi vào Giới hạn: "đổi dấu liên tiếp dùng phím 1–5 hoặc `n`"; HUD hiện gợi ý khi cửa sổ đứng yên một nhãn > 2 s trong khi tay đang chuyển động. Mọi thay đổi mô hình = kế hoạch riêng có GATE, CẦN NGƯỜI DÙNG. | — |

Không phương án nào được thử "thêm" giá trị thứ hai sau khi thấy số (quy tắc chống chỉnh sau kết quả của dự án).

## 6. Phạm vi file

```scope
.gitattributes
level1_demo.py
scripts/level1_trace_report.py
tests/test_level1_demo.py
tests/test_level1_trace_report.py
tests/test_level1_gitattributes.py
docs/plans/15-progress.md
docs/level1_desktop.md
```
KHÔNG đụng: `configs/level1_realtime.json`, `configs/level1_demo_classifier.json`, `src/inference/level1_segmenter.py` (bộ giải mã), `src/data/alphabet_preprocessing.py`, `backend/main.py`, `realtime_demo.py`, `README.md`, checkpoint, các test hiện có. Vòng 1 không đổi hành vi nhận ký tự nên bộ giải mã và config giữ nguyên byte; `AC-W3` vẫn xanh.

## 7. Tiêu chí chấp nhận (vòng 1)

- **AC-6a** `git diff 4f913a2..HEAD --numstat -- tests/`: cột xóa = 0 cho mọi file; `git diff 4f913a2..HEAD -- configs src` rỗng.
- **AC-6b** Không có `--trace-windows`: JSON của app bằng hệt trước thay đổi về tập khóa, và chạy headless D2/E1 trên cùng clip cho cùng token (so từng token).
- **AC-6c** Có `--trace-windows`: số mục `window_trace` == `counts.window_results`; mỗi mục có đủ khóa §3.W1; `emitted` đúng với `labels` của JSON (cùng `seq`); token không đổi so với chạy không trace.
- **AC-6d** HUD: chế độ `classifier` có dòng bộ giải mã đúng chuỗi mẫu và KHÔNG có thanh tiến độ bộ tách; chế độ `motion_pose` ảnh HUD bằng hệt (so mảng ảnh với bản trước trên cùng trạng thái tổng hợp).
- **AC-6e** `level1_trace_report`: trên trace tổng hợp dựng sẵn cho từng M1–M4, phân loại đúng và tất định (chạy 2 lần ra cùng byte).
- **AC-6f** Hồi quy: 12 module Level 1 + AC-E1 + guard (`known=9 allowed=36`) + sha256 checkpoint không đổi; chỉ `test_u1_summary` được phép skip khi thiếu file U1.

## 8. Checklist reviewer (Antigravity, sau khi cloud push)

1. `git fetch`, kiểm commit, `git diff --numstat -- tests/` (cột xóa 0), file cấm không đổi.
2. Chạy lại trên Windows: `$env:PYTHONIOENCODING="utf-8"` + 12 module Level 1 + AC-E1 + guard + AC1-ngắn; so từng con số coder báo với log của mình.
3. Đọc diff `level1_demo.py` (impact thật, không chỉ grep), kiểm cờ trace tắt = không đổi hành vi, kiểm giới hạn kích thước trace.
4. Đọc 2 JSON của U3 và `level1_trace_report`, tự tính lại tỉ lệ M1–M4 từ `window_trace`, đối chiếu với báo cáo; không tin số của coder.
5. Ghi kết luận chọn hướng vòng 2 theo §5 vào `docs/plans/15-lan-sua-7.md` (hoặc báo "M0/M2/M4: không sửa mã").

## 9. Rủi ro

- Trace làm chậm vòng xử lý ⇒ có điểm dừng đo `frame_total` (§3).
- Phiên U3 chỉ một người ký, vài lượt ⇒ chỉ đủ để chọn hướng sửa, không phải đo độ chính xác; Giới hạn của `level1_desktop.md` giữ nguyên câu "độ chính xác trên webcam CHƯA được đánh giá".
- Có thể kết luận là M2/M4 (giới hạn của mô hình dấu thanh): khi đó câu trả lời trung thực là "đổi dấu liên tiếp cần phím 1–5/`n`", không phải thêm luật vá.
