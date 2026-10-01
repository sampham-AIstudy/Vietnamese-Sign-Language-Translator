# Kế hoạch 06 — §0E. Lần sửa 5 (sau review 06 CHANGES_REQUESTED; chỉ sửa tài liệu)

- Trạng thái: XONG (planner). Ngày 2026-10-01, HEAD 33c7c41. Nguồn: `docs/reviews/06-review.md` mục "Kết luận (sau 3 phần)",
  V9–V13, O1–O5; quyết định người dùng `docs/STATE.md` 2026-10-01 19:22 (GIỮ 2 clip qipedc, chỉ đính chính).
- Vị trí: đây là §0E của `docs/plans/06-viec5-frontend.md`, để ở file riêng vì phiên planner không có công cụ Edit (không
  viết lại file 1400 dòng). Orchestrator thêm 1 dòng trỏ vào đầu kế hoạch 06 (sau dòng 10): "- Lần sửa 5: 2026-10-01, sau
  review 06 — `docs/plans/06-viec5-frontend-sua5.md` (§0E), ưu tiên hơn mọi câu trái ngược trong file này."
- Không có điểm dừng CẦN NGƯỜI DÙNG mới. Không đổi code, không đổi test, không đổi model mặc định, không chạy lại e2e/AC5/AC6.
- Câu "KHÔNG có Lần sửa 5 cho luật e2e" (đầu kế hoạch 06) vẫn đúng: lần sửa này KHÔNG chạm luật e2e/AC12.

## 0E.1 Mục tiêu, DoD
Sửa các câu tài liệu sai/vượt bằng chứng mà review 06 bắt (FAIL hạng mục 5 và 13) để kế hoạch 06 đủ điều kiện APPROVE.
Phục vụ DoD về tài liệu API Phase 12 trung thực (AC11) và quy tắc "không bịa số liệu / không gọi TEST là TRAIN".

## 0E.2 Nguyên nhân gốc (planner nhận lỗi)
1. V11/O5: AC5 của kế hoạch chọn "2 clip qipedc đầu tiên" từ `manifest.csv` Cấp 1, mà phần qipedc của manifest là TEST ngoài
   (`docs/data_registry.md:46`). Kế hoạch §0.4 (dòng 64), §6 (dòng 1316, 1332) và AC11 (dòng 1157) viết "10 clip TRAIN" → coder
   chép theo. Lỗi ở kế hoạch, không ở coder.
2. V10/O1: câu gốc "qua proxy Vite → CORS không tham gia" nằm ở kế hoạch §3.5 (dòng 880-882); đó là giả định chưa thăm dò. Review
   §11 đo thật: Vite dev server (`server.cors` mặc định) tự trả CORS cho mọi origin họ loopback.
3. V9/O2: 06-progress ghi kết quả lượt dev B8 không khớp JSON.

## 0E.3 Quyết định
1. **V11/O5 — GIỮ 2 clip (quyết định người dùng), đính chính.** Mọi chỗ "10 clip TRAIN" thay bằng "10 clip: 8 clip hauuto TRAIN + 2
   clip qipedc (`qipedc_D0489`, `qipedc_D0490B`) thuộc TEST ngoài Cấp 1; `qipedc_D0490B` còn thuộc `data/splits/unified/test.csv`
   (TEST Cấp 2)". Kèm: không chạy lại; 2 clip không dùng để chọn/chỉnh gì; phép so bit AC5-a không phụ thuộc nhãn.
   - Sửa kế hoạch (planner, tại đây): §0.4 dòng 64, §3.7/§6 dòng 1316 và 1332, AC11 dòng 1157 — đọc "10 clip TRAIN" thành câu trên.
     AC11 (ii) nay BẮT câu: "top-1 trùng trên 10 clip (8 TRAIN + 2 TEST ngoài), không chứng minh bền vững". Lý do đổi tiêu chí:
     câu cũ sai sự thật (V11); tiêu chí không bị nới (vẫn bắt chữ "không chứng minh bền vững", số vẫn phải từ JSON).
   - **Luật mới cho mọi kế hoạch sau:** KHÔNG chọn clip từ phần qipedc của manifest Cấp 1 (TEST ngoài). Clip gọi là "TRAIN" phải
     được kiểm thuộc split train bằng lệnh tra file split (ghi lệnh + kết quả vào progress); không kiểm được thì không gọi là TRAIN.
2. **V10/O1 — chọn SỬA TÀI LIỆU** (không sửa `vite.config.js`; cấu hình `server.cors`/`preview.cors` chuyển backlog V6). Câu đúng
   phải nêu: qua proxy Vite dev `:3000`, Vite tự trả CORS (preflight 204, `Access-Control-Allow-Origin` phản chiếu) cho origin họ
   loopback (`localhost`, `*.localhost`, `127.0.0.1`, `[::1]`, cổng bất kỳ) → REST `/api/*` qua `:3000` đọc được từ các origin đó
   dù `VSL_CORS_ORIGINS` không cho; `VSL_CORS_ORIGINS` chỉ có hiệu lực khi gọi thẳng cổng 8000; WS qua proxy vẫn bị kiểm Origin
   (403). Nguồn: `docs/reviews/06-review.md` §11. Thêm 1 dòng vào "## 7. Giới hạn". Kế hoạch §3.5 dòng 880-882: câu "CORS không
   tham gia" hết hiệu lực, thay bằng câu trên.
3. **V9/O2 — ghi chú đính chính** dưới `docs/plans/06-progress.md:237-239` (không xóa dòng cũ).
4. **Làm luôn (THẤP):** O3, O4, V12, V13. **Backlog** (orchestrator ghi vào STATE "Backlog còn lại"): V6 (`cors` cho Vite
   `server`/`preview` + test văn bản kiểu AC3-g), V7 (`detail` cố định cho `model_unavailable` của `/ws/hand-landmarks`,
   `backend/main.py:1645`), V8 (số gõ tay `frontend/src/components/Reports.jsx:73-77`); thông tin: V1/V2, V3–V5, `/api/health`
   `model_type`.

## 0E.4 Việc coder — B10 (chỉ sửa tài liệu; ≤ 1 giờ)
B10-1 `docs/phase12_api.md`:
- dòng 32-33 (O1): thay theo 0E.3 mục 2; thêm 1 dòng Giới hạn (§7) cùng nội dung ngắn.
- dòng 111-114 (O4): thêm "(cùng máy, ảnh PNG)" ở câu "Tương đương … bit-by-bit"; nêu với npz train Kaggle/Linux thì không bằng hệt (trỏ mục AC6).
- dòng 153-154 (O3): "do trình duyệt nén" giữ, nhưng "ảnh hưởng đo được ở mục dưới" → "ảnh hưởng của bộ nén trình duyệt CHƯA đo;
  mục dưới chỉ đo đại diện gần đúng bằng JPEG q90 của cv2".
- dòng 164 (V11): "mẫu 10 clip (8 hauuto TRAIN + 2 qipedc thuộc TEST ngoài Cấp 1; `qipedc_D0490B` còn thuộc `data/splits/unified/test.csv`)".
- dòng 170 (V13): "cỡ cả bàn tay" giữ; phần "ở vài frame tracker bắt/nhả tay khác nhau" ghi là "giả thuyết, chưa phân tích theo frame".
- dòng 173-174 (V11): theo 0E.3 mục 1; giữ nguyên chữ "không chứng minh bền vững" và "không phải độ chính xác"; ghi 2 clip TEST được
  giữ theo quyết định người dùng 2026-10-01.
B10-2 `docs/plans/06-progress.md`: thêm khối "Đính chính (Lần sửa 5, review 06 V9/O2)" ngay sau dòng 239: đọc
`_work/_plan06_tmp/b8_dev_fingerspell.json` và ghi đúng các kiểm đỏ của lượt dev (theo review: `hand_ws_session_info` đỏ, `detail`
socket đầu `first_type` null 0 message; `code_clean_at_run` đỏ — dự kiến vì code bẩn; cùng `ws_urls_all_via_proxy_no_8000`), và
việc kiểm `hand_ws_session_info` đã được đổi (commit 7e38118, bỏ qua socket 0 message) TRƯỚC lượt chính thức, sau đó được thay
bằng `strictmode_orphans` chặt hơn theo 0B.2. Chép tên kiểm/giá trị từ JSON, không chép từ review. JSON không có → dừng, báo.
B10-3 `docs/progress_log.md`: THÊM 1 dòng mới (không sửa dòng 112): đính chính "10 clip TRAIN" → 8 TRAIN + 2 TEST ngoài (quyết định
người dùng GIỮ); đường log đúng `_work/_plan06_tmp/b9b_ac2_31.log` (V12); "526 OK, 0 skip" là kết quả tại 0491877 (trước V0).
B10-4 Chạy AC-E1..E5, detect-changes trước commit, chép output vào message (AC13).

## 0E.5 Tiêu chí chấp nhận (hợp đồng)
- AC-E1: `.venv/Scripts/python -m unittest tests.test_frontend_contract -v` → `OK`, 0 failure/error; `TestPhase12ApiDoc` xanh hết.
  Đã đọc test (`tests/test_frontend_contract.py:175-240`): KHÔNG khóa câu "10 clip TRAIN" hay câu CORS → không cần đổi test. Bẫy
  phải tránh: (a) trong mục AC6 (`### Lệch nguồn landmark Cấp 1 đo được (AC6)`) MỌI số thập phân phải có trong JSON AC6 → không
  thêm số thập phân mới (vd. 0.135, phiên bản Vite) vào mục đó; (b) không viết `0.0.0.0` hay `ws://localhost:8000` ở bất kỳ đâu;
  (c) §7 Giới hạn phải còn `W03251B`, `segmenter`, `JPEG`, `Origin`, `không phải trình duyệt`. Nếu đỏ → sửa TÀI LIỆU, không sửa/skip
  test; đỏ do thiếu dữ liệu (V0) → báo nguyên văn, không skip.
- AC-E2: `git diff --name-only 33c7c41 HEAD -- backend src frontend scripts tests` rỗng; file đổi chỉ gồm `docs/phase12_api.md`,
  `docs/plans/06-progress.md`, `docs/progress_log.md` (+ STATE/plans do orchestrator).
- AC-E3: `grep -n "10 clip TRAIN\|CORS không tham gia" docs/phase12_api.md` rỗng; `grep -n "qipedc_D0490B" docs/phase12_api.md`
  có dòng chứa `unified/test.csv` hoặc dòng kề; `grep -n "cùng máy, ảnh PNG\|giả thuyết\|chưa đo" docs/phase12_api.md` có cả ba.
- AC-E4: `git diff 33c7c41 HEAD -- docs/progress_log.md docs/plans/06-progress.md | grep '^-[^-]'` rỗng (chỉ thêm dòng).
- AC-E5: trong `docs/phase12_api.md` câu CORS mới có `localhost`, `VSL_CORS_ORIGINS`, `8000`, `403` và trỏ `docs/reviews/06-review.md`.

## 0E.6 Reviewer kiểm lại
Hạng mục 5 và 13: đọc diff 3 file tài liệu + chạy AC-E1..E5; đối chiếu ghi chú 06-progress với JSON dev B8. V0: nay chỉ phụ thuộc
§8.1 kế hoạch 12 (đã APPROVE ở review 12) — không đòi thêm ở 06. Sau đó thêm dòng kết luận reviewer vào progress_log (AC13).

## 0E.7 Rủi ro dữ liệu/ML
Không train/chọn model. 2 clip TEST đã bị model Cấp 1 triển khai chạy `/sequence` (top-1 nằm trong JSON AC6) — không dùng để quyết
định gì; kết quả TEST ngoài Cấp 1 đã công bố từ 2026-09-25 không đổi. Không có số liệu mới; mọi số giữ nguyên từ JSON AC6.
