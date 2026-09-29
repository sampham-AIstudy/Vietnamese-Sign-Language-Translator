# Kế hoạch 06 — Việc 5: nối frontend với backend (Đánh vần Cấp 1 + Ký từ WS v2)

- Nhánh: feat/vslt-complete | HEAD khi lập: 19d02bf | Ngày: 2026-09-29
- Lần sửa 1: 2026-09-29, sau chặng 2 (B0–B4 xong, commit tới 026f474), coder trả "CẦN PLANNER" (§0).
- Lần sửa 2: 2026-09-29, sau B8/B9 (HEAD e801209), coder trả "CẦN PLANNER" (AC12 socket HMR Vite, 4 giả định, AC1 sau
  merge cloud) — §0B.
- Lần sửa 3: 2026-09-29, sau B8b-3 (HEAD 94c51ed), coder dừng §7-8 (`strictmode_orphan_rule` đỏ ở Đánh vần do socket
  `/ws/live-stream` của tab mặc định bị gỡ khi chuyển tab) — §0C.
- Backlog: docs/STATE.md "Backlog còn lại" mục 2; autopilot.md backlog gốc mục 3.
- **Không có điểm dừng CẦN NGƯỜI DÙNG trước khi code** (xem §7; chỉ có điểm dừng có điều kiện trong lúc làm). Lần sửa 1,
  Lần sửa 2 và Lần sửa 3 cũng không tạo điểm dừng CẦN NGƯỜI DÙNG mới.

## 0. Lần sửa 1 (sau chặng 2; nguồn: `docs/plans/06-progress.md` mục B3, B4)

Các commit đã có giữ nguyên, không viết lại lịch sử. Không tiêu chí nào bị nới về bản chất; các chỗ đổi được đánh dấu
"(Lần sửa 1)" ngay tại mục tương ứng.

### 0.1 Lệnh `node --test tests/` không chạy trên Node v25.9.0
- **Nguyên nhân gốc (lỗi kế hoạch):** tôi viết lệnh dạng thư mục mà không kiểm với bản Node trên máy. Từ Node 22, đối số
  của `node --test` là đường dẫn file/glob, không duyệt thư mục → `MODULE_NOT_FOUND` (06-progress B4). B0 đã ghi
  `node --version` nhưng kế hoạch không yêu cầu đối chiếu cú pháp lệnh với phiên bản đó.
- **Sửa:** lệnh chính thức là `cd frontend && npm test`, với `frontend/package.json` `"test": "node --test tests/*.test.mjs"`
  (đúng như coder đã làm). Để lệnh không lặng lẽ bỏ sót file test, AC2 thêm yêu cầu: số file test Node báo đã chạy ==
  số file `frontend/tests/*.test.mjs` trong git (đếm bằng `git ls-files frontend/tests/*.test.mjs`), 0 fail, và ghi
  `node --version` cạnh kết quả. Áp dụng ở bảng B4, AC2, AC7.
- Không nới: cùng bộ test, cùng yêu cầu 0 fail; chỉ đổi cú pháp gọi.

### 0.2 Mâu thuẫn AC1 ↔ AC8 ở `RealtimeStream.jsx`
- **Nguyên nhân gốc (lỗi kế hoạch):** khi lập §2.2 tôi chỉ ghi `:8000` ở dòng URL (`:143`), không grep hết file; dòng `:203`
  còn `:8000` trong chuỗi báo lỗi tiếng Việt. AC1 lại khóa file này ở mức "dòng URL + 1 dòng import" → không thể vừa đạt
  AC1 vừa đạt AC8.
- **Sửa (AC1):** được sửa thêm CHỈ phần chữ trong chuỗi báo lỗi có `:8000` (hiện ở `:203`) — bỏ số cổng, ví dụ
  "…FastAPI backend (/ws/live-stream)…"; không đổi logic, không đổi dòng nào khác. Reviewer kiểm bằng
  `git diff P6 HEAD -- frontend/src/components/RealtimeStream.jsx`: tối đa 3 dòng bị đổi (URL, chuỗi báo lỗi, import), mọi
  dòng khác nguyên vẹn.
- AC8 giữ nguyên toàn bộ (guard áp cho MỌI file trong `frontend/src`, không có ngoại lệ cho `RealtimeStream.jsx`).
- KHÔNG xóa `RealtimeStream.jsx` (xóa file là điểm dừng hỏi người dùng; đã có trong đề xuất backlog ở B9).

### 0.3 Test guard đỏ có chủ đích ở B4
- Hợp lệ: đây là "viết test trước" (autopilot vòng lặp bước 2), guard không bị nới hay skip. Nhưng kế hoạch cũ không nói
  AC2 áp ở mốc nào → **Nguyên nhân gốc:** AC2 chỉ được viết cho trạng thái đóng việc, không có quy định cho mốc trung gian.
- **Sửa (AC2):** AC2 đầy đủ (0 failure) là tiêu chí ĐÓNG VIỆC, bắt buộc từ B7 trở đi (B7, B8 chạy trên HEAD mà AC2 đã xanh;
  B9 chạy lại). Ở mốc trung gian B4–B6, AC2 được phép có failure DUY NHẤT là
  `TestFrontendSourceGuard.test_no_violation`, với điều kiện:
  - 0 error, 0 skip, mọi test khác OK;
  - tập vi phạm (so theo cặp file + mẫu, không theo số dòng) là tập con của 14 vi phạm ghi ở 06-progress B4, và không
    tăng qua các mốc;
  - sau B5: chỉ còn vi phạm trong `Fingerspelling.jsx`; sau B6: 0 vi phạm (guard xanh);
  - commit có test đỏ ghi rõ trong message "guard đỏ có chủ đích, còn N vi phạm" và danh sách ở 06-progress.
- Nếu sau B6 guard vẫn đỏ → coder sửa code (không sửa guard); không sửa được → báo planner.

### 0.4 Kết quả AC6: lệch nguồn Kaggle/Linux và JPEG (ghi nhận, không chặn)
- Nguồn: `reports/fingerspell_live_2026-09-29/hand_live_check.json` (`generated_by.git_commit` e58d025, `code_dirty: false`;
  coder chạy lại lần 2 ra phần thân giống hệt). Theo 06-progress B3: live PNG == offline cục bộ 10/10 (max diff 0.0);
  JPEG q90 vs PNG: cờ detected lệch ở 2/10 clip, max diff lớn nhất 0.2403; npz Kaggle vs trích lại cục bộ: detected lệch ở
  1/10 clip (`hauuto_aw_khoi_A_003`, 88/90), max diff lớn nhất 0.2298; top-1 `/sequence` trùng nhau ở cả 10 clip.
- **Đánh giá:** không làm hỏng AC5 (tương đương code trên cùng máy vẫn bằng hệt), nhưng bác bỏ giả định ngầm "landmark train
  (Kaggle/Linux) = landmark live (Windows)". Chênh 0.23 đơn vị ảnh chuẩn hóa là cỡ cả bàn tay, tức ở vài frame tracker
  bắt/nhả tay khác nhau, không phải sai số làm tròn. Top-1 trùng 10/10 là trên 10 clip TRAIN — KHÔNG chứng minh bền vững.
- **Có đưa vào Giới hạn/rủi ro: CÓ.** §6 thêm mục; AC11 thêm yêu cầu `docs/phase12_api.md` mục "Giới hạn" nêu hai lệch này,
  trích số từ JSON kèm đường dẫn + commit (không gõ số khác). Không phải điểm dừng "vấn đề dữ liệu mới": kế hoạch 04 §6 đã
  nêu rủi ro Linux↔cục bộ; lần này chỉ là đo được, không đổi hướng kế hoạch.
- Đề xuất backlog (không làm ở đây): đo lệch Kaggle↔cục bộ trên TOÀN BỘ clip hauuto (không chỉ 10) trước khi báo cáo độ
  chính xác Cấp 1 trên webcam, để biết tỉ lệ frame bị lệch cờ detected.

### 0.5 Thay đổi so với bản gốc
- §4 bảng: dòng B4 (lệnh test); B5/B6 (mốc guard). §5: AC1 (RealtimeStream), AC2 (lệnh + mốc trung gian), AC7 (lệnh),
  AC11 (Giới hạn thêm lệch AC6). §6: thêm mục lệch nguồn đo được. Không bỏ hay nới tiêu chí nào.

## 0B. Lần sửa 2 (sau B8/B9; nguồn: `docs/plans/06-progress.md` mục B8, B9; 3 JSON `reports/e2e_2026-09-29/*.json` — commit e3d0df8, chạy tại 15200d9; `docs/reviews/cloud-2026-09-29-review.md`)

Các commit đã có giữ nguyên, không viết lại lịch sử. Chỗ đổi đánh dấu "(Lần sửa 2)" tại mục tương ứng. Một mệnh đề của AC12
được định nghĩa lại (0B.1); lý do dựa trên MỤC ĐÍCH gốc của mệnh đề, không dựa trên việc cho pass; phần cấm `:8000` giữ
nguyên không ngoại lệ, và thêm kiểm âm (test) để phần loại trừ không thành lỗ hổng.

### 0B.1 AC12 — socket HMR của Vite dev: chọn phương án (a), định nghĩa chặt, PHẢI chạy lại 3 kịch bản
- **Hiện tượng (từ 3 JSON e3d0df8):** mỗi lượt có đúng 1 socket `ws://localhost:3000/?token=<12 ký tự>`, protocol
  `vite-hmr`, bắt tay 101, nhận đúng 1 message `type == "connected"`. Mọi socket còn lại có URL
  `ws://localhost:3000/ws/live-stream` hoặc `ws://localhost:3000/ws/hand-landmarks`; 0 URL chứa `:8000`. Kiểm
  `ws_urls_all_via_proxy_no_8000` đỏ ở cả 3 lượt chỉ vì socket HMR; các kiểm khác đều đạt (19/20, 17/18, 20/21).
- **Nguyên nhân gốc (lỗi kế hoạch):** tôi viết "Mọi URL WS" với ý "mọi WS do app mở" (§3.4: mọi WS trong `frontend/src`
  dùng `wsUrl`; AC8 là guard tĩnh cho `frontend/src`) nhưng không tính tới socket do client Vite dev (`/@vite/client`,
  được Vite chèn vào trang khi chạy `npm run dev`; không nằm trong `frontend/src`, không có trong bản build) tự mở — dù §3.7
  đã biết e2e chạy qua `start_fullstack.ps1` (dev server). Không phải lỗi coder; coder dừng đúng quy tắc.
- **Mục đích gốc của mệnh đề** (bằng chứng runtime bổ sung cho AC8 và §3.5): (1) trình duyệt KHÔNG nối thẳng backend `:8000`
  (Origin check + bind 127.0.0.1 + proxy chỉ có nghĩa khi app đi qua proxy); (2) mọi WS của APP đi qua đường `/ws/` của
  proxy Vite. Socket HMR cùng origin `:3000`, không tới backend, không mang dữ liệu app → không vi phạm (1) hay (2).
- **Chọn (a).** Loại (b) tắt HMR: là sửa hệ thống được kiểm cho vừa phép kiểm; đổi `frontend/vite.config.js` ngoài thiết kế
  §3.5 và đổi trải nghiệm dev; không làm bằng chứng cho (1)(2) mạnh hơn. Loại (c) `vite preview`: DoD 1 và §3.7 kiểm đúng
  đường người dùng chạy (`start_fullstack.ps1` → dev server + proxy); preview là cấu hình khác (cần build trước, khối
  `preview` riêng) → e2e mất giá trị bằng chứng cho DoD 1.
- **Định nghĩa chặt (Lần sửa 2, thay mệnh đề URL WS của AC12).** Một socket là "socket HMR của Vite" CHỈ KHI thỏa đồng thời:
  1. URL khớp TOÀN BỘ regex `^ws://localhost:3000/\?token=[A-Za-z0-9_-]+$` (host đúng `localhost:3000` như trang, path
     đúng `/`, đúng một tham số `token`);
  2. header `Sec-WebSocket-Protocol` của bắt tay (CDP `Network.webSocketWillSendHandshakeRequest`) bằng đúng `vite-hmr`;
  3. mọi message nhận là JSON có `type == "connected"` (đúng như 3 JSON e3d0df8); có message khác (vd. reload, lỗi) → KHÔNG
     được xếp HMR.
  Ba kiểm mới thay cho `ws_urls_all_via_proxy_no_8000`:
  - `ws_no_8000_any_socket`: KHÔNG socket nào — kể cả socket HMR và socket mồ côi StrictMode (0B.2) — có URL chứa `:8000`.
    Không ngoại lệ.
  - `ws_app_urls_via_proxy`: có ≥ 1 socket không phải HMR; MỌI socket không phải HMR có URL bắt đầu bằng
    `ws://localhost:3000/ws/`.
  - `vite_hmr_socket_rule`: số socket HMR ≤ 1 mỗi lượt; mọi socket có protocol `vite-hmr` phải thỏa đủ 1–3 (không thỏa →
    đỏ, liệt kê).
  JSON ghi riêng danh sách socket HMR đã loại (`url`, `protocol`, `count_by_type`) để reviewer thấy chính xác cái gì bị loại.
  Việc phân loại nằm trong MỘT hàm thuần của `scripts/e2e_fullstack.py` (không mở trình duyệt/server), có test âm AC12-t.
- **Có phải chạy lại: CÓ.** Logic kiểm của `scripts/e2e_fullstack.py` đổi → 3 JSON e3d0df8 không còn là đầu ra của script
  cuối. Phải chạy lại CẢ 3 kịch bản tại HEAD sạch chứa script mới, ghi 3 JSON mới. KHÔNG tính lại kiểm từ JSON cũ bằng tay
  hay bằng script (bằng chứng phải có lệnh + commit).

### 0B.2 Bốn giả định coder tự đặt ở B8 — quyết định
1. **Clip Ký từ `qipedc_D0120T`: CHẤP NHẬN.** §3.7 viết mơ hồ ("clip đầu tiên (thứ tự của hàm)" không nói tham số `n`).
   Mục đích: 1 clip TRAIN chọn tất định bằng hàm có sẵn, KHÁC W03251B (ca phát lặp đã biết, tách sang kế hoạch "segmenter
   live" — để số sự kiện không bị nhiễu bởi lỗi đó). D0120T thỏa: `scripts/e2e_fullstack.py` (`clip_identity`) từ chối clip
   VAL/TEST của `data/splits/unified`, JSON ghi `split: "train"`. §3.7 nay ghi đích danh (Lần sửa 2). Lượt chạy lại dùng ĐÚNG
   clip này (không đổi clip sau khi đã thấy kết quả). Ghi nhận: smoke B7 dùng `select_train_clips(1, 0)` → W03292N; AC10
   không quy định clip → không mâu thuẫn, không sửa.
2. **Socket app đóng trước khi có message do React.StrictMode: CHẤP NHẬN CÓ ĐIỀU KIỆN.** Căn cứ: `frontend/src/main.jsx:7`
   bọc `<React.StrictMode>`; ở dev React chạy effect mount → unmount → mount nên component mở socket, đóng, mở lại; JSON:
   socket đầu của mỗi path có `handshake_status: null`, `closed: true`, 0 message. Điều kiện để một socket được coi là "mồ côi
   StrictMode" (không phải kiểm `session_info` đầu tiên) — cũng nằm trong hàm thuần, có test AC12-t:
   - nhận 0 message; đã đóng trong lượt chạy (`closed: true`);
   - KHÔNG phải socket cuối cùng của path đó (socket cuối phải là socket được dùng, nhận `session_info` đầu tiên);
   - tối đa 1 socket mồ côi cho mỗi path trong một lượt (mỗi component chỉ mount 1 lần trong kịch bản).
   Vi phạm bất kỳ điều kiện → kiểm `strictmode_orphan_rule` đỏ. Socket mồ côi VẪN chịu `ws_no_8000_any_socket` và
   `ws_app_urls_via_proxy`; message `error` trên MỌI socket của path vẫn được tính. JSON ghi số socket mồ côi theo path.
   (Lần sửa 3: luật này nay CHỈ áp cho path mà kịch bản dùng; path của component bị gỡ khi chuyển tab theo luật riêng 0C.2.)
3. **Cửa sổ 180 s gộp: CHẤP NHẬN.** Đo "health 200 và trang 3000 200" trong CÙNG 180 s tính từ lúc khởi chạy
   `start_fullstack.ps1` chặt hơn hoặc bằng cách đo riêng từng cái. AC12 nay ghi rõ (Lần sửa 2).
4. **Độ dài lượt ghi: CHẤP NHẬN.** Đánh vần: bấm `fs-record`, chờ đúng 1 vòng clip (thời lượng y4m), bấm `fs-stop` — 1 clip
   hauuto là 1 ký hiệu, dưới giới hạn 300 frame. Ký từ: chạy ≥ 1 vòng clip, dừng sớm khi đủ điều kiện kịch bản (legacy
   ≥ 30 `frame_result`; harmonized ≥ 1 `sign_result`/`sign_discarded`), tối đa 3 vòng (khớp "tối đa 3 vòng lặp clip").
   Ghi nhận: webcam giả lặp clip từ lúc mở trang nên lượt ghi Đánh vần bắt đầu ở pha clip không kiểm soát → `prediction`
   chỉ là `info_not_accuracy`; không thêm tiêu chí nào về nhãn. JSON phải ghi số `hand_frame` của lượt ghi và `ran_loops`
   (đang có).

### 0B.3 AC1 khi `P6..HEAD` chứa commit không thuộc kế hoạch 06
- **Nguyên nhân (lỗi kế hoạch, không phải coder):** AC1 viết khi nhánh chỉ có commit của 06; sau đó nhánh nhận thêm commit
  của orchestrator (`state:`), bàn giao cloud (8628948 "chore: cloud handoff", 296b12e, f62dd45 "cloud: …" — CLAUDE.md,
  docs/CLOUD.md, scripts/cloud_setup.sh), merge cloud bbfdff3 (14 file, đã review ở `docs/reviews/cloud-2026-09-29-review.md`)
  và commit ghi review đó (6a6538c, nếu nằm trên first-parent của P6..HEAD). `git diff --name-status P6 HEAD` gộp tất cả →
  không dùng nguyên văn được.
- **Cách đánh giá (Lần sửa 2; KHÔNG nới phạm vi của coder 06):**
  - `C06` = commit trong `git log --first-parent --no-merges -E --grep='^(WIP )?06:' --format='%h %s' P6..HEAD` (commit của
    coder 06). File của từng commit: `git show --name-status --format= <c>`.
  - **AC1-a:** hợp file của `C06` ⊆ danh sách AC1, với đúng các điều kiện từng file như cũ (start_fullstack.ps1 chỉ `--host`;
    RealtimeStream.jsx ≤ 3 dòng; `frontend/package.json` chỉ thêm khóa `scripts.test` — dòng khóa đứng trước chỉ đổi vì thêm
    dấu phẩy được tính là một phần của việc thêm khóa, không dòng nào khác đổi). Không commit nào trong `C06` chạm danh sách
    "KHÔNG đổi".
  - **AC1-b:** MỌI commit first-parent khác trong `P6..HEAD` được liệt kê (hash + subject + file) trong 06-progress và thuộc
    đúng một nhóm, chỉ chạm tập file của nhóm đó:
    (i) orchestrator `state:` — docs/STATE.md, docs/usage_ledger.csv, docs/progress_log.md (chỉ thêm dòng: numstat cột xóa = 0);
    (ii) planner kế hoạch 06 (facffea = Lần sửa 1; commit chứa Lần sửa 2 này; (Lần sửa 3) commit chứa Lần sửa 3) —
         docs/plans/06-viec5-frontend.md (+ docs/STATE.md, docs/usage_ledger.csv);
    (iii) bàn giao cloud 8628948, 296b12e, f62dd45 — CLAUDE.md, docs/CLOUD.md, scripts/cloud_setup.sh
         (+ docs/STATE.md, docs/usage_ledger.csv);
    (iv) merge bbfdff3 — đúng tập `git diff --name-status bbfdff3^1 bbfdff3`; commit review cloud 6a6538c — chỉ
         docs/reviews/cloud-2026-09-29-review.md (+ docs/STATE.md, docs/usage_ledger.csv).
    Commit không thuộc nhóm nào, hoặc chạm file ngoài tập của nhóm → DỪNG, báo planner (§7-9).
  - **AC1-c:** không commit ngoài `C06` chạm file "của 06" (các file code/test/report/tài liệu trong danh sách AC1), trừ
    docs/progress_log.md (nhóm i, chỉ thêm) và docs/plans/06-viec5-frontend.md (nhóm ii). Lệnh:
    `git log --first-parent --format='%h %s' P6..HEAD -- <các file của 06>` chỉ được ra commit `C06` (+ các ngoại lệ vừa nêu).
  - **AC1-d:** mỗi dòng của `git diff --name-status P6 HEAD` được quy về commit nguồn (bảng trong 06-progress); dòng không
    quy được → FAIL.
  - Giữ nguyên: `git diff P6 HEAD -- tests/` 0 dòng `-` với mọi test có ở P6; `git diff --diff-filter=D --name-only P6 HEAD`
    rỗng; 3 file ` D` của người dùng chưa staged; không thêm file `.pt/.npz/.mp4/.y4m/.png/.jpg/.log`.
- Coder đã làm phần lớn ở 06-progress B9 (tại 0e506c3); phải làm lại tại HEAD cuối (sau commit Lần sửa 2 và commit B8 lần 2)
  theo đúng các lệnh trên.

### 0B.4 AC2 đóng việc: dùng lệnh 31 module
- **Có.** `docs/reviews/cloud-2026-09-29-review.md` (mục cuối) quy định từ sau merge bbfdff3 mọi lệnh không hồi quy (gồm 06
  B8/B9 và review 06) thêm `tests.test_archive_private_kaggle_r05 tests.test_backend_source_guard`. Lý do theo mục đích của
  AC2: đo không hồi quy trên đúng cây sẽ được review; cây đó có 2 module này; `tests.test_backend_source_guard` quét mã
  backend mà kế hoạch 06 sửa (`backend/main.py`) nên là bằng chứng liên quan trực tiếp.
- Lệnh đóng việc = lệnh 29 module cũ + 2 module (AC2, Lần sửa 2). Lệnh 29 module là tập con, không bắt chạy riêng.
- Số test báo theo module, so với mốc có nguồn: 25 module cũ = B0 (06-progress B0); 4 module của 06 = B7 cộng số test
  AC12-t thêm ở Lần sửa 2; 2 module merge = số đo trên cây merge (review cloud: 2 module mới `Ran 38` OK). Chênh ở module
  nào phải giải thích bằng commit.

### 0B.5 Việc coder làm tiếp (đóng B8/B9) và điều reviewer kiểm
Coder (chặng 4, tiếp):
1. **B8b-1 (test trước).** Thêm vào `tests/test_frontend_contract.py` lớp test AC12-t (§5) cho hàm thuần phân loại socket
   và luật mồ côi StrictMode trong `scripts/e2e_fullstack.py` (nạp module theo đường dẫn, không mở trình duyệt/server).
   Chạy → đỏ (hàm chưa có) là đúng.
2. **B8b-2.** `impact evaluate --direction upstream` (và symbol mới nếu có); sửa `scripts/e2e_fullstack.py`: hàm thuần
   (gợi ý `classify_ws(ws_list)` + `strictmode_orphans(sockets_of_path)`), thay kiểm `ws_urls_all_via_proxy_no_8000` bằng
   `ws_no_8000_any_socket`, `ws_app_urls_via_proxy`, `vite_hmr_socket_rule`, thêm `strictmode_orphan_rule`; dùng luật mồ côi
   cho `hand_ws_session_info` và `live_ws_first_message_session_info_v2`. `scripts/e2e_browser.cjs` chỉ sửa nếu thiếu dữ liệu
   quan sát (đang có `protocol`, `count_by_type`, `closed`, `n_messages`). Chạy AC12-t → xanh; chạy lệnh AC2 31 module → 0
   failure/error/skip. `detect-changes --scope all`; commit (message có impact/detect-changes).
3. **B8b-3.** Tại HEAD đó, `git status --porcelain -- backend src frontend scripts tests` rỗng; chạy đúng 3 lệnh (như
   `generated_by.command` của 3 JSON cũ, clip giữ nguyên):
   - `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/e2e_fullstack.py --scenario fingerspell --video data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4 --out reports/e2e_<YYYY-MM-DD>/fingerspell_default.json`
   - `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/e2e_fullstack.py --scenario word --video data/Dataset/Videos/D0120T.mp4 --out reports/e2e_<YYYY-MM-DD>/word_default.json`
   - `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/e2e_fullstack.py --scenario word --model-type stgcn_h360 --video data/Dataset/Videos/D0120T.mp4 --out reports/e2e_<YYYY-MM-DD>/word_stgcn_h360.json`
   `<YYYY-MM-DD>` = ngày chạy. Nếu vẫn là 2026-09-29 → ghi đè 3 file cũ (M). Nếu khác ngày → thư mục mới; thư mục cũ GIỮ
   NGUYÊN (không xóa file), 06-progress ghi 3 JSON cũ là "bản chạy trước Lần sửa 2, bị thay thế". Mỗi lệnh exit 0,
   `all_checks_pass: true`. Có kiểm nào đỏ (kể cả luật HMR/mồ côi gặp trường hợp khác 3 JSON cũ) → DỪNG, báo planner, KHÔNG
   sửa luật (§7-8). Commit CHỈ 3 JSON (+ 06-progress).
4. **B9b.** Tại HEAD cuối: lệnh AC2 31 module (log `../_plan06_tmp/b9b_ac2_31.log`), `cd frontend && npm test` (+ đếm file),
   `npm run build`, `npm ls --depth=0` so với B0; `git status --porcelain` so với B0; AC1-a..d theo 0B.3 (bảng quy nguồn
   trong 06-progress); `git diff --name-only <git_commit của 3 JSON mới> HEAD -- backend src frontend scripts tests` rỗng.
   THÊM 1 dòng `docs/progress_log.md` (AC13; nêu cả Lần sửa 2 và commit của 3 JSON mới). Ghi backlog đề xuất như B9 cũ.
   Commit. Orchestrator gọi vslt-reviewer.
(Lần sửa 3: bước 3 đã chạy và dừng đúng §7-8; phần còn lại làm theo 0C.5 — B8c thay cho phần chạy chính thức của B8b-3.)

Reviewer kiểm (ngoài các AC khác):
- Quyết định (a) và định nghĩa ở 0B.1 được cài ĐÚNG như chữ: regex neo đầu–cuối, host `localhost:3000`, protocol đúng
  `vite-hmr`, types chỉ `connected`, ≤ 1 socket HMR; `:8000` cấm ở mọi socket; test AC12-t có đủ ca âm và không skip.
- 3 JSON mới: `all_checks_pass: true`; `generated_by.git_commit` là commit chứa script mới (`git merge-base --is-ancestor
  <commit script B8b-2> <git_commit>`), `code_dirty: false`; không đổi code sau lượt chạy (lệnh ở bước 4); danh sách socket
  HMR bị loại đúng 0 hoặc 1 phần tử/lượt; clip Ký từ là `qipedc_D0120T`.
- Luật mồ côi StrictMode: ≤ 1 mỗi path, 0 message, đã đóng, không phải socket cuối.
- AC1 theo 0B.3 (tự chạy lại lệnh, không tin bảng của coder); AC2 31 module theo 0B.4.
- Các mục reviewer còn nợ từ STATE (impact CRITICAL/HIGH ở B2/B3/B5/B6/B8, 050d337 thiếu detect-changes, B7 sửa
  `tests/test_frontend_contract.py` không nới) vẫn giữ.

### 0B.6 Thay đổi so với bản trước
- §3.7: clip Ký từ ghi đích danh; luật socket HMR + mồ côi. §4 bảng: B8, B9 (thêm B8b/B9b). §5: AC1 (cách đánh giá 0B.3),
  AC2 (31 module), AC12 (mệnh đề URL WS thay bằng 3 kiểm + luật mồ côi + cửa sổ 180 s gộp + độ dài lượt ghi + code không đổi
  sau lượt chạy; thêm AC12-t). §7: thêm điểm dừng 8, 9. Không bỏ tiêu chí nào; cấm `:8000` giữ nguyên không ngoại lệ.

## 0C. Lần sửa 3 (sau B8b-3; nguồn: `docs/plans/06-progress.md` mục B8b-1..B8b-3; chạy thử ngoài repo tại eb379fa: `../_plan06_tmp/b8b3_trial_fingerspell.json`, `b8b3_trial_word_default.json`, `b8b3_trial_word_stgcn_h360.json`; code `scripts/e2e_fullstack.py`, `scripts/e2e_browser.cjs`, `frontend/src/App.jsx`, `frontend/src/main.jsx`)

Các commit đã có giữ nguyên (302072c, eb379fa, 1a4e182). Chỗ đổi đánh dấu "(Lần sửa 3)" tại mục tương ứng. Phạm vi hẹp:
chỉ luật socket app theo path của AC12 và việc chạy lại 3 kịch bản; mọi kiểm URL/HMR/`:8000` của 0B.1 giữ nguyên chữ.

### 0C.1 Vấn đề và nguyên nhân gốc
- **Hiện tượng (coder, chạy thử tại eb379fa, JSON ngoài repo — không phải bằng chứng chính thức):** Đánh vần exit 1, đỏ
  duy nhất `strictmode_orphan_rule` với `/ws/live-stream: violations ["socket 1: 0 messages and it is the last socket of the
  path"]`; path đó có đúng 2 socket, cả hai `handshake_status: null`, `closed: true`, 0 message. `/ws/hand-landmarks` (path
  kịch bản dùng) đúng luật cũ: mồ côi [0], socket 1 nhận `session_info` → `reset_done` → `hand_frame`. Hai kịch bản Ký từ
  xanh. Mọi kiểm URL/HMR/`:8000` xanh ở cả 3.
- **Cơ chế (đọc code):** `frontend/src/App.jsx:9` `useState('realtime')` + `:53` → tab mặc định mount `Phase12Pipeline`;
  `frontend/src/main.jsx:7` `<React.StrictMode>` → mount → unmount → mount = 2 socket `/ws/live-stream`; kịch bản Đánh vần
  (`scripts/e2e_browser.cjs:380-388`) bấm tab "Bảng Chữ Cái" ngay sau `goto` → `Phase12Pipeline` bị gỡ, socket thứ hai đóng
  trước khi bắt tay xong. Đây là hành vi đúng của app (component bị gỡ thì đóng socket), không phải socket hỏng.
- **Nguyên nhân gốc (lỗi kế hoạch, không phải coder):** ở Lần sửa 2 tôi viết luật mồ côi với giả định "mỗi component chỉ
  mount 1 lần trong kịch bản" và "socket cuối của path là socket được dùng", cho MỌI path app. Tôi không đối chiếu giả định đó
  với `App.jsx` (tab mặc định) và không đọc từng socket của JSON Đánh vần e3d0df8 — JSON đó ĐÃ có đúng 2 socket
  `/ws/live-stream` 0 message; tôi tóm tắt sai thành "socket đầu của mỗi path … 0 message". Coder cài đúng chữ và dừng đúng
  §7-8.

### 0C.2 Quyết định: luật theo VAI TRÒ của path trong kịch bản (chọn (b) của coder, siết thêm)
**Mục đích gốc của luật mồ côi** (Lần sửa 2): phát hiện socket app hỏng hoặc không phục vụ kịch bản (bị từ chối, lỗi, không
bao giờ nhận `session_info`) mà vẫn không báo đỏ vì hiệu ứng StrictMode; phần "không vượt proxy, không `:8000`" do 3 kiểm URL
của 0B.1 lo và giữ nguyên. Luật mới giữ nguyên mục đích đó, chỉ bỏ giả định sai "mỗi path đều là path được dùng".

Mỗi path app (socket không phải HMR, gom theo path như `app_ws_by_path`) có đúng MỘT vai trò, xác định TĨNH theo kịch bản
(hằng trong `scripts/e2e_fullstack.py`, không suy từ dữ liệu quan sát):

| Kịch bản | Path được dùng (`used`) | Path của tab mặc định bị gỡ (`tab_unmounted`) | Path khác |
|---|---|---|---|
| `fingerspell` | `/ws/hand-landmarks` | `/ws/live-stream` (sự kiện chuyển tab: bước `tab_alphabet`; mốc thao tác đầu: bước `record_clicked`) | đỏ |
| `word` (cả 2) | `/ws/live-stream` | KHÔNG có (kịch bản không chuyển tab) | đỏ |

1. **Path `used` — luật cũ, KHÔNG đổi chữ (0B.2 mục 2):** phải có ≥ 1 socket; mồ côi = 0 message + `closed: true` + không
   phải socket cuối; ≤ 1 mồ côi; socket cuối nhận message; mọi socket không phải mồ côi có message đầu `session_info`
   (qua `hand_ws_session_info` / `live_ws_first_message_session_info_v2`). Path `used` không có socket nào → đỏ (chặt hơn cài
   đặt hiện tại, vốn chỉ duyệt path có mặt).
2. **Path `tab_unmounted` — luật mới, chỉ ở `fingerspell`, chỉ `/ws/live-stream`.** Được phép 0 socket. Nếu có socket, TẤT CẢ
   phải thỏa đồng thời:
   - a. số socket ≤ 2 (đúng một cặp StrictMode mount → unmount → mount);
   - b. mỗi socket được TẠO trước lúc bấm tab: `created_t_s < click_t_s` của bước `tab_alphabet` (mốc lấy NGAY TRƯỚC lệnh
     click, xem 0C.4); bước `tab_alphabet` phải có và `clicked: true`, nếu không → đỏ;
   - c. mỗi socket đã ĐÓNG trong lượt (`closed: true`) và `closed_t_s` không null, `closed_t_s ≤ t_s` của bước
     `record_clicked` (đóng trước khi kịch bản bắt đầu thao tác dữ liệu); không có bước `record_clicked` → đỏ;
   - d. message: `n_non_json == 0`; `count_by_type` rỗng, HOẶC đúng `{session_info: 1}` với `first_type == "session_info"` và
     `session_info.protocol_version == 2`. Bất kỳ `error`, `frame_result`, `sign_result`, type khác, hay > 1 message → đỏ;
   - e. `handshake_status` ∈ {null, 101} (bắt tay bị từ chối, vd. 403 của kiểm Origin, → đỏ).
   Vẫn chịu nguyên `ws_no_8000_any_socket` và `ws_app_urls_via_proxy` (0B.1), không ngoại lệ.
3. **Path khác** (mọi path app không phải `used` và không phải `tab_unmounted` của kịch bản, vd. `/ws/hand-landmarks` trong
   `word`, hay một path lạ dưới `/ws/`) → đỏ, liệt kê.

**Kiểm (tên cố định):** `strictmode_orphan_rule` nay CHỈ áp cho path `used` (chữ luật như cũ). Thêm kiểm mới
`tab_unmounted_socket_rule` gộp mục 2 và 3: xanh khi mọi path không phải `used` là `tab_unmounted` hợp lệ; có mặt trong
`checks` của CẢ 3 kịch bản (ở `word` chỉ xanh khi không có path app nào khác `/ws/live-stream`). JSON
`ws_classification` thêm `tab_unmounted_by_path` (số socket theo path) và `role_by_path`.

**Mức chặt so với các lựa chọn.**
- Chặt hơn (b) của coder ở: vai trò path cố định theo kịch bản (không phải "bất kỳ path nào không được dùng"); ràng buộc thời
  điểm tạo/đóng theo mốc bước (bắt được socket sai path mở SAU khi chuyển tab, vd. `Fingerspelling` lỡ mở `/ws/live-stream`);
  kiểm `handshake_status`; path lạ → đỏ; path `used` vắng → đỏ.
- Nới hơn (b) của coder ĐÚNG một điểm: cho phép một message `session_info` hợp lệ (d). Lý do (quyết định TRƯỚC lượt chạy chính
  thức, không dựa trên kết quả): đây là cuộc đua thời gian, không phải tính chất của app — ở lượt thử Ký từ mặc định,
  `/ws/live-stream` sẵn sàng (bước `ready`) khoảng 1.5 s sau `goto`, còn ở lượt thử Đánh vần kịch bản bấm tab khoảng 1.1 s sau
  `goto` (hai số lấy từ `steps` của 2 JSON thử nêu trên; chỉ để minh họa độ sát, không phải số đo có kiểm soát). Nếu backend
  trả `session_info` sớm hơn, socket tab mặc định sẽ có 1 message hợp lệ; socket nhận `session_info` đúng giao thức là socket
  KHỎE, nên theo mục đích gốc không có lý do báo đỏ. Mọi message khác (nhất là `error`) vẫn đỏ.
- Loại (a) của coder (chỉ áp luật cho path có kiểm `session_info`, path còn lại "luật riêng" không nêu): không định nghĩa được
  path còn lại → lỗ hổng. Loại (c) (giữ chữ): AC12 Đánh vần không bao giờ đạt được với `App.jsx` bị khóa — luật đo sai hiện
  tượng, không đo app.
- Loại thêm (d') "sửa luồng trình duyệt: chờ `/ws/live-stream` kết nối xong rồi mới bấm tab" để luật cũ tự xanh: KHÔNG chọn —
  cùng lý do đã loại tắt HMR ở 0B.1 (sửa đối tượng được kiểm cho vừa phép kiểm), đổi kịch bản người dùng (người dùng bấm tab
  ngay là hợp lệ) và buộc kịch bản Đánh vần phụ thuộc model Ký từ. Luồng thao tác của `e2e_browser.cjs` KHÔNG đổi.
- Đổi `App.jsx` (tab mặc định) hay bỏ `StrictMode` ở `main.jsx`: KHÔNG (AC1 khóa `App.jsx`; `main.jsx` không thuộc danh sách
  được sửa; cả hai là sửa app cho vừa phép kiểm).

### 0C.3 Ba giả định coder tự đặt ở B8b (06-progress B8b-2/B8b-3 không đánh số; planner tách ra) — quyết định
1. **`strictmode_orphan_rule` áp cho MỌI path socket app (đọc đúng chữ "với mỗi path app" của AC12): đọc chữ ĐÚNG, nhưng
   chữ sai → THAY bằng 0C.2** (luật cũ chỉ cho path `used`; path còn lại theo `tab_unmounted_socket_rule`). Không phải lỗi coder.
2. **Mọi socket không phải mồ côi của path được dùng phải có message đầu `session_info`, và phải có ≥ 1 socket như vậy
   (`hand_ws_session_info`, `live_ws_first_message_session_info_v2`): CHẤP NHẬN.** Chặt hơn chữ "message WS đầu là
   `session_info`" và đúng mục đích (không socket được dùng nào bỏ qua kiểm giao thức). Giữ nguyên.
3. **Điều kiện (3) của socket HMR cài bằng `count_by_type ⊆ {connected}` VÀ `n_messages == tổng count_by_type` (message không
   phải JSON làm socket mất tư cách HMR), `fullmatch` cho regex URL: CHẤP NHẬN.** Đúng chữ "mọi message nhận là JSON có
   `type == "connected"`" của 0B.1; `fullmatch` chặt hơn `$` (chặn xuống dòng cuối). Giữ nguyên.
- Ghi nhận thêm (thực hành, không phải giả định về luật): coder chạy THỬ 3 kịch bản ra thư mục ngoài repo trước lượt chính
  thức. CHẤP NHẬN như bước dò lỗi; JSON thử KHÔNG phải bằng chứng AC12, không commit, không trích số như kết quả. Lượt chính
  thức (B8c) chạy đủ 3 kịch bản lại từ đầu, không chọn lọc lượt.

### 0C.4 Dữ liệu quan sát cần thêm (`scripts/e2e_browser.cjs`, chỉ phần ghi nhận)
- Mỗi socket thêm `created_t_s` (trong handler `Network.webSocketCreated`) và `closed_t_s` (trong handler
  `Network.webSocketClosed`; null nếu chưa đóng), cùng đồng hồ và cùng cách làm tròn với `steps[].t_s` (`now()/1000`, 3 chữ số).
- Bước `tab_alphabet` thêm `click_t_s` = `now()/1000` lấy NGAY TRƯỚC `page.evaluate(...)` bấm tab (giữ `t_s` và `clicked`
  như cũ). Lý do: `t_s` hiện ghi SAU khi click trả về, lúc đó component mới có thể đã mở socket → mốc `created_t_s < t_s` sẽ
  lọt socket mở sau khi chuyển tab.
- KHÔNG đổi thứ tự thao tác, không thêm chờ, không đổi selector, không đổi cách chọn clip. Diff của file này ở B8c chỉ gồm
  các dòng ghi 3 trường trên (reviewer kiểm bằng `git diff eb379fa HEAD -- scripts/e2e_browser.cjs`).

### 0C.5 Việc coder làm tiếp (B8c thay phần chạy chính thức của B8b-3, rồi B9b)
1. **B8c-1 (test trước).** Thêm vào `tests/test_frontend_contract.py` các ca AC12-t mục 10 (§5) cho hàm thuần mới (gợi ý
   `scenario_ws_roles(ws_by_path, scenario, steps) -> dict` gồm vai trò từng path, kết quả `strictmode_orphan_rule` cho path
   `used` và `tab_unmounted_socket_rule`). 16 test hiện có của `TestE2eSocketRules` KHÔNG được sửa hay xóa:
   `git diff eb379fa HEAD -- tests/test_frontend_contract.py` 0 dòng `-`. Nếu một test cũ không thể giữ nguyên vì mâu thuẫn
   với 0C.2 → DỪNG, báo planner (§7-10). Chạy → ca mới đỏ vì hàm chưa có là đúng; commit `WIP 06: B8c-1 …`.
2. **B8c-2.** `impact` upstream cho `evaluate`, `strictmode_orphans`, `app_ws_by_path`, `ws_classification` (và symbol JS nếu
   index thấy); `risk: UNKNOWN`/đồ thị nhầm tên → xác nhận bằng text search, ghi vào 06-progress. Sửa
   `scripts/e2e_browser.cjs` theo 0C.4; sửa `scripts/e2e_fullstack.py`: bảng vai trò 0C.2 thành hằng; `strictmode_orphan_rule`
   chỉ cho path `used` (vắng → đỏ); thêm `tab_unmounted_socket_rule`; `ws_classification` thêm `role_by_path`,
   `tab_unmounted_by_path`. `strictmode_orphans(sockets_of_path)` giữ nguyên hành vi (test cũ gọi nó). Chạy AC12-t → xanh;
   `cd frontend && npm test` không liên quan nhưng không được đỏ; chạy lệnh AC2 31 module → 0 failure/error/skip, số test
   theo module = mốc B8b-2 + số ca AC12-t mới (chỉ `tests.test_frontend_contract` đổi). `detect-changes --scope all`; commit
   `06: B8c-2 …` (message có impact/detect-changes).
3. **B8c-3 (chạy chính thức).** Tại HEAD của B8c-2, `git status --porcelain -- backend src frontend scripts tests` rỗng; chạy
   ĐÚNG 3 lệnh ở 0B.5 bước 3 (clip, tham số, tên file giữ nguyên), theo thứ tự fingerspell → word → word stgcn_h360, mỗi
   lệnh đúng 1 lần, đầu ra vào `reports/e2e_<YYYY-MM-DD>/`. Cùng ngày 2026-09-29 → ghi đè (M); khác ngày → thư mục mới, thư
   mục cũ giữ nguyên, 06-progress ghi 3 JSON e3d0df8 là "bản chạy trước Lần sửa 2/3, bị thay thế". Mỗi lệnh exit 0,
   `all_checks_pass: true`, `checks` có cả `strictmode_orphan_rule` và `tab_unmounted_socket_rule`. Có kiểm nào đỏ → DỪNG, báo
   planner, KHÔNG sửa luật, KHÔNG chạy lại để lấy lượt xanh (§7-8, §7-10). Commit CHỈ 3 JSON (+ 06-progress):
   `06: B8c-3 …`.
4. **B9b** như 0B.5 bước 4, tại HEAD cuối sau B8c-3; progress_log (AC13) nêu thêm Lần sửa 3 (luật path tab mặc định bị gỡ)
   và commit của 3 JSON mới. AC1-b nhóm (ii) gồm cả commit chứa Lần sửa 3.

### 0C.6 Reviewer kiểm (thêm vào 0B.5)
- `tab_unmounted_socket_rule` cài đúng 0C.2: vai trò path là hằng theo kịch bản (không suy từ dữ liệu); `tab_unmounted` chỉ
  `/ws/live-stream` ở `fingerspell`; đủ a–e; `session_info` được phép tối đa 1 và phải `protocol_version == 2`; path lạ và
  path `used` vắng đều đỏ; `strictmode_orphan_rule` chỉ áp cho path `used` và chữ luật cũ không đổi.
- AC12-t mục 10 có đủ ca dương/âm, không skip; 16 test cũ không bị sửa (lệnh ở 0C.5 bước 1).
- `scripts/e2e_browser.cjs`: diff chỉ ghi `created_t_s`, `closed_t_s`, `click_t_s`; luồng thao tác không đổi.
- 3 JSON mới: `generated_by.git_commit` là con cháu của commit B8c-2 (`git merge-base --is-ancestor`), `code_dirty: false`;
  JSON Đánh vần có `role_by_path` đúng bảng 0C.2 và số socket `tab_unmounted` ≤ 2; 3 JSON thử ngoài repo KHÔNG được trích như
  bằng chứng.
- Không file nào trong danh sách "KHÔNG đổi" của AC1 (nhất là `frontend/src/App.jsx`) bị chạm; `frontend/src/main.jsx` không đổi.

### 0C.7 Thay đổi so với bản trước
- Đầu file (dòng Lần sửa 3). §0B.2 mục 2, §0B.3 AC1-b (ii), §0B.5 (ghi chú trỏ sang 0C). §3.7: luật theo vai trò path + trường
  thời gian. §4 bảng: thêm B8c, B8b/B9 ghi chú. §5: AC12 (luật mồ côi chỉ cho path `used`; thêm `tab_unmounted_socket_rule`;
  3 JSON của B8c), AC12-t (thêm mục 10), AC13 (nêu Lần sửa 3). §7: thêm điểm dừng 10. Không bỏ tiêu chí nào; kiểm URL/HMR/
  `:8000` giữ nguyên chữ; điểm nới duy nhất (một `session_info` hợp lệ trên socket tab mặc định bị gỡ) nêu lý do ở 0C.2 và
  được quyết trước lượt chạy chính thức.

## 1. Mục tiêu và DoD

**Mục tiêu.** Frontend React dùng được hai hợp đồng backend đã APPROVE: (a) chế độ "Đánh vần" gửi CHUỖI landmark bàn tay
tới `/api/fingerspelling/sequence` và ghép chữ bằng `/compose`; (b) chế độ "Ký từ" nói giao thức WS v2 của
`/ws/live-stream` qua proxy `/ws` của Vite. Đồng thời siết CORS/Origin/bind theo quyết định 2026-09-28, sửa smoke test
Phase 12, ghi hợp đồng vào `docs/phase12_api.md`, và lần đầu chạy backend + frontend cùng nhau có kiểm tự động (trình
duyệt thật, webcam giả nạp clip thật).

**DoD phục vụ.**
- DoD 1 (một phần): `start_fullstack.ps1` chạy cả hai, `/api/health` OK, không lỗi console — kiểm bằng script tự động.
  Phần "clone sạch theo README" KHÔNG thuộc việc này (backlog 7 gốc).
- DoD 2: webcam → chuỗi landmark → chữ + confidence → ghép từ; endpoint ảnh cũ 409 (frontend không gọi nữa).
- DoD 3: webcam → model mặc định (KHÔNG đổi) → top-k + confidence qua `/ws/live-stream`, cả đường `legacy` (mặc định) lẫn
  `harmonized_v1` (khi bật `VSL_MODEL_TYPE=stgcn_h360`, để GATE về sau dùng được UI — review 04 mục 12).
- DoD 6 (một phần): không có kết quả giả; bỏ nút "Test Frame" gửi ảnh 1×1. Nút chọn chế độ là Việc 6.
- DoD 7: contract test cho endpoint mới + test tương đương train↔live cho Cấp 1 + e2e trên clip thật + guard cơ bản
  cho `frontend/src` (Math.random, URL cứng).
- DoD 8: chỉ đảm bảo ĐO ĐƯỢC (có mốc thời gian client/server trong message), KHÔNG đo trong việc này.

## 2. Hiện trạng (HEAD 19d02bf)

### 2.1 Backend
- `backend/main.py:327-334`: `CORSMiddleware(allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
  allow_headers=["*"])` — đúng cái quyết định 2026-09-28 cấm.
- `backend/main.py:1297-1314`: `websocket_live_stream` gọi `websocket.accept()` ngay, KHÔNG kiểm header `Origin`.
- `backend/main.py:1519`: `uvicorn.run(..., host="0.0.0.0", ...)`; `start_fullstack.ps1:13`: `--host 0.0.0.0 --reload`.
- Cấp 1 (APPROVE ở kế hoạch 03): `GET /api/fingerspelling/status` (`:729`), `POST /api/fingerspelling/sequence` (`:760`),
  `POST /api/fingerspelling/compose` (`:800`), `POST /api/fingerspelling` → 409 (`:811`). Hợp đồng §3.2 kế hoạch 03:
  `landmarks` 1..`ALPHABET_MAX_FRAMES`(=300, `:551`) phần tử, mỗi phần tử `null`/`[]` hoặc 21×[x,y,z] hữu hạn |v| ≤ 10,
  không trùng hệt; `handedness`, `timestamps_ms?`, `frame_width/height`, `source_mirrored`, `top_k`; 413 (> 1 MiB),
  422 hai dạng body (`{"detail": str}` hoặc `{"detail": [{loc,msg,type}]}`), 503.
- Checkpoint Cấp 1 triển khai (`reports/alphabet_deploy_2026-09-27/provenance.json:27-45`): `bigru`, `target_frames` 30,
  `resample: "frame_index"`, `min_detected_frames` 3.
- Extractor lúc train Cấp 1: `scripts/extract_hands_batch.py:37-50` — `mp.solutions.hands.Hands(static_image_mode=False,
  max_num_hands=1, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)`, tracker MỚI cho mỗi
  clip, frame gốc (không resize), BGR→RGB, không lật; mediapipe 0.10.14. Không có tay → ghi 0 + `detected=False`.
  Dữ liệu train: `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` (hauuto 640×480 ≈ 23.6 fps, ≈ 75
  frame/clip; qipedc 1280×720) — trích trên Kaggle (Linux). Video gốc hauuto có cục bộ:
  `data/external/hauuto_raw/raw/raw/<signer>/<tên>.mp4`; video qipedc: `data/Dataset/Videos/D*.mp4`.
- **Backend CHƯA có đường nào trích landmark bàn tay Cấp 1 từ frame webcam.** `src/data/extract_landmarks.py:122`
  (`HandLandmarkExtractor`) dùng `min_detection_confidence=0.7`, không đặt `model_complexity`, trả đặc trưng 42 chiều đã
  chuẩn hóa — KHÁC extractor train, KHÔNG được dùng.
- WS v2 (kế hoạch 04 §3.6, `backend/main.py:1297+`): `session_info` → `frame_result` (legacy: có `gloss/prediction/
  confidence/top5/status IDLE|DETECTING|CONFIRMED/is_confirmed/buffer_fill/buffer_capacity`, `:1114-1143`; harmonized:
  không bao giờ mang dự đoán) → `sign_result` / `sign_discarded` (chỉ harmonized) → `error{code, detail, received_seq}`;
  1 MiB → 1009; `model_unavailable` → 1011. Helper dùng lại được: `_parse_ws_message` (`:890`, ném `bad_message`,
  `bad_config`, `bad_timestamp`, `message_too_large`), `_image_header` (`:945`), `_decode_frame(raw, min_height=None)`
  (`:965`), `_ws_error` (`:875`), `THREAD_POOL` (`:89`).
- `sign_result.segment.dropped_frames` theo hợp đồng mới của kế hoạch 05 (chỉ đếm frame hợp lệ bị ghi đè slot; docstring
  `:1308-1312`) và các thay đổi hợp đồng legacy (review 04 mục 11: message đầu là `session_info`, lỗi frame thành
  `error{code}`, bỏ khóa `frame`/`data`) CHƯA có trong `docs/phase12_api.md` (tài liệu còn `ws://localhost:8000`,
  `--host 0.0.0.0`, không có `session_info`).
- `scripts/smoke_test_phase12.py:74-102`: đọc `resp['gloss']` ở message đầu (nay là `session_info`) → `KeyError`;
  bước [4/5] chờ `status == "ERROR"` (nay là `error{code}`); dùng ảnh đen 640×480 và `data\Dataset\Videos\W00009N.mp4`.

### 2.2 Frontend
- `frontend/vite.config.js:5-14`: proxy `/api` → `http://127.0.0.1:8000` (changeOrigin) và `/ws` → `ws://127.0.0.1:8000`
  (`ws: true`); port 3000 cho `dev` và `preview`, KHÔNG `strictPort` (cổng bận thì Vite nhảy sang 3001 → Origin đổi).
  Proxy không đổi `Origin` của trình duyệt (`changeOrigin` chỉ đổi Host).
- `frontend/src/App.jsx:53-56`: tab `realtime` → `Phase12Pipeline`, `alphabet` → `Fingerspelling`, `dictionary`, `reports`.
  (Nút chọn chế độ đúng nghĩa DoD 6 là Việc 6; ở đây giữ các tab.)
- `frontend/src/components/Phase12Pipeline.jsx:51-52`: `ws://${host}:8000/ws/live-stream` CỨNG (bỏ qua proxy);
  `onmessage` (`:65-93`) không xét `type`: bỏ qua `session_info`/`error`, ghi đè `gloss=null` mỗi `frame_result`
  harmonized, bỏ qua `sign_result`/`sign_discarded`; nút "Test Frame" (`:121-131,160-168`) gửi JPEG 1×1 — dữ liệu giả lập
  trong mã chính; `bufferCapacity={60}` cứng (`:201`).
- `frontend/src/components/CameraCapture.jsx`: webcam 640×480 lý tưởng, `toDataURL('image/jpeg', 0.75)` hoặc binary;
  frame KHÔNG lật (chỉ CSS `-scale-x-100` khi hiển thị, `:252,260`) — khớp train, giữ nguyên. `timestamp: Date.now()`
  (`:146`) — đồng hồ tường, có thể lùi khi hệ thống chỉnh giờ → `bad_timestamp`. Nhận `ws` qua prop `wsRef.current`.
- `frontend/src/components/PredictionDisplay.jsx:81` và `Navbar.jsx:71`: chữ cứng ":8000".
- `frontend/src/components/RealtimeStream.jsx`: KHÔNG được import ở đâu (mã chết); nối cứng `ws://…:8000` (`:143`) và
  (Lần sửa 1) còn `:8000` trong chuỗi báo lỗi (`:203`).
- `frontend/src/components/Fingerspelling.jsx:58-88`: tải MỘT ảnh lên `POST /api/fingerspelling` (nay 409 → `alert`);
  không có webcam, không gửi chuỗi; ghép chữ bằng cộng chuỗi thô (`:207`) thay vì `/compose`; "25 lớp" cứng (`:130`).
- Không có framework test frontend. Có `puppeteer-core` trong `devDependencies` (`frontend/package.json:26`, đã có trong
  `frontend/node_modules`) và tiền lệ `scripts/take_screenshots.cjs` chạy Edge
  (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) với `--use-fake-device-for-media-stream`.
  → Unit test JS dùng `node --test` (có sẵn trong Node), e2e dùng puppeteer-core: KHÔNG cần cài gói mới.
- (Lần sửa 2) `frontend/src/main.jsx:7` bọc app trong `<React.StrictMode>` → ở dev mỗi component mở WS hai lần (lần đầu
  đóng ngay). `start_fullstack.ps1` chạy `npm run dev` → trang có thêm socket HMR của Vite (`/?token=…`, `vite-hmr`).
- (Lần sửa 3) `frontend/src/App.jsx:9` tab mặc định `'realtime'` → khi mở trang, `Phase12Pipeline` luôn mount (2 socket
  `/ws/live-stream` do StrictMode) kể cả ở kịch bản Đánh vần; chuyển tab thì component bị gỡ và socket đóng.

### 2.3 Còn thiếu (việc này làm)
1. Đường trích landmark bàn tay Cấp 1 từ webcam, nhất quán với extractor train.
2. `Fingerspelling.jsx` viết lại: webcam → ghi một ký hiệu → `/sequence` → top-k → chấp nhận token → `/compose`.
3. Client WS v2 cho "Ký từ" (xử lý theo `type`, cả hai pipeline), URL qua proxy `/ws`.
4. CORS danh sách origin dev, WS kiểm Origin, bind 127.0.0.1.
5. `smoke_test_phase12.py` cho WS v2; `docs/phase12_api.md` cập nhật.
6. Script e2e fullstack (Edge + webcam giả nạp clip thật) + kiểm console.
7. Quyết định review 04 mục 8–9 (§3.8).

## 3. Thiết kế

### 3.1 Quyết định: MediaPipe cho Cấp 1 chạy ở SERVER (Python), không ở trình duyệt
- Bất biến 1 của skill `vsl-landmark-consistency`: cùng extractor + cùng phiên bản ở train và live. Train Cấp 1 dùng
  `mp.solutions.hands` 0.10.14 (Python). MediaPipe JS (`@mediapipe/tasks-vision`, HandLandmarker) là model/phiên bản
  khác, cần tải model `.task` + WASM từ mạng (trái quy tắc "không tải từ mạng" nếu không có bản cục bộ), và KHÔNG thể có
  test tương đương bit-by-bit với landmark train.
- Chạy ở server: dùng đúng `mp.solutions.hands` với đúng tham số của `scripts/extract_hands_batch.py`, tracker mới cho mỗi
  ký hiệu (như "tracker mới cho mỗi clip" lúc trích). Tương đương kiểm được bằng test Python: cùng video → đường live ↔
  `_extract_one` phải ra landmark GIỐNG HỆT (AC5).
- Giá phải trả: frame đi qua WS (như chế độ Ký từ); có thêm độ trễ mạng/giải mã — ghi được vào metrics, không đo ở đây.
- Hợp đồng `/api/fingerspelling/sequence` (kế hoạch 03) GIỮ NGUYÊN: server trả landmark thô về client, client ghép chuỗi
  và gọi `/sequence`. Không thêm đường phân loại thứ hai.

### 3.2 Luồng dữ liệu chế độ "Đánh vần"
```
Fingerspelling.jsx
  GET /api/fingerspelling/status → available, classes, num_classes, preprocessing   (không available → khóa nút ghi, hiện message)
  WS  /ws/hand-landmarks (URL từ window.location qua proxy /ws) → session_info
  [Ghi]   → gửi {"type":"control","action":"reset"} → chờ reset_done(segment_id)
          → vòng chụp (FS_TARGET_FPS, canvas KHÔNG lật, JPEG chất lượng FS_JPEG_QUALITY) gửi {image, timestamp=nowMs()}
            tối đa FS_MAX_IN_FLIGHT frame chưa có hand_frame; vượt → bỏ chụp frame đó, đếm client_skipped
          → mỗi hand_frame(segment_id hiện tại) → lưu {landmarks|null, handedness, client_timestamp, frame_width, frame_height}
  [Dừng] hoặc đủ limits.max_frames_per_segment frame (lấy từ session_info, không cứng)
          → chờ hết frame đang bay (timeout 2 s; frame không về thì không có trong chuỗi, đếm vào client_skipped)
          → body = buildSequenceBody(frames, {topK: 5})   (hàm thuần, frontend/src/lib/fingerspelling.js)
          → POST /api/fingerspelling/sequence
              200 → hiện prediction, confidence, candidates (class, confidence, kind), frames, detected_frames
              413/422/503 → hiện detail (cả 2 dạng body), KHÔNG hiện kết quả nào
  Bộ ghép: tokens[] trong state. [Thêm] = thêm candidate người dùng chọn (mặc định top-1); [Dấu cách] = " ";
          [Xóa lùi], [Xóa hết]. Mỗi lần tokens đổi → POST /api/fingerspelling/compose {tokens}
          → hiện text + warnings. Chữ hiển thị CHỈ lấy từ `text` của server (không tự ghép trong JS).
```
`buildSequenceBody` (hợp đồng, test ở AC7):
- `landmarks[i]` = mảng 21×[x,y,z] đúng như server trả, hoặc `null` khi `hand_frame.landmarks == null`.
  KHÔNG bao giờ gửi khung toàn 0.
- `handedness[i]` = `hand_frame.handedness` ("" khi không có tay); `timestamps_ms[i]` = `client_timestamp` (ms, đồng hồ
  đơn điệu `performance.timeOrigin + performance.now()`, không giảm).
- `frame_width`/`frame_height` = của hand_frame; nếu kích thước đổi giữa chừng → không gửi, hiện lỗi "kích thước camera
  đổi" (không đoán).
- `source_mirrored: false` (frame không lật); `top_k`.
- Thứ tự theo `frame_seq`; chỉ lấy hand_frame có `segment_id` của lượt ghi hiện tại.

Hằng mới (ghi ở `frontend/src/lib/fingerspelling.js`, có chú thích "giá trị thiết kế, chưa đo"): `FS_TARGET_FPS = 24`
(gần fps hauuto trong manifest), `FS_JPEG_QUALITY = 0.9`, `FS_MAX_IN_FLIGHT = 2`. Không có tham số cắt ký hiệu tự động:
người dùng bấm Ghi/Dừng (tránh thêm luật cắt chưa có dữ liệu; §6).

UI hiển thị kèm kết quả: độ phân giải frame, số frame, số frame có tay, `client_skipped`, fps hiệu dụng của lượt ghi
(tính từ `client_timestamp`) — để người dùng thấy khi đầu vào lệch điều kiện train. `confidence` ghi là "độ tin cậy của
model", không ghi là "độ chính xác".

### 3.3 Hợp đồng `WS /ws/hand-landmarks` (mới, `protocol_version` 1)
Module thuần mới `src/inference/hand_live.py` (không import torch/fastapi):
- `LEVEL1_HANDS_KWARGS = {"static_image_mode": False, "max_num_hands": 1, "model_complexity": 1,
  "min_detection_confidence": 0.5, "min_tracking_confidence": 0.5}` — phải BẰNG các keyword trong lời gọi
  `Hands(...)` của `scripts/extract_hands_batch.py` (AC4-a đọc bằng `ast`, KHÔNG sửa file train).
- `class HandLandmarkSession`: `reset()` (đóng graph cũ, tạo `mp.solutions.hands.Hands(**LEVEL1_HANDS_KWARGS)` mới),
  `process(frame_bgr) -> (landmarks float32[21,3] | None, label: str, score: float | None)` — đúng chuyển đổi của
  `_extract_one`: `cv2.cvtColor(BGR2RGB)`, frame gốc không resize, `multi_hand_landmarks[0]`,
  `multi_handedness[0].classification[0]`; `close()`.

Endpoint `websocket_hand_landmarks` trong `backend/main.py`: kiểm Origin (§3.5) → accept → tạo session (lỗi →
`error{model_unavailable}` + 1011) → vòng nhận TUẦN TỰ (mỗi message xử lý xong mới nhận message sau; không có slot
"frame mới nhất", không bỏ frame ở server). Dùng lại `_parse_ws_message`, `_decode_frame(raw, min_height=None)`,
`_ws_error`, `THREAD_POOL`; không viết lại logic giải mã/kiểm kích thước.

Client → server: giống `/ws/live-stream` (text JSON `{"image", "timestamp"?}`, binary JPEG/PNG,
`{"type":"control","action":"reset"}`). `config` hợp lệ bị bỏ qua; `config` sai → `bad_config` (do parser dùng chung).

Server → client:
1. `session_info` (đầu tiên): `{"type":"session_info","endpoint":"hand-landmarks","protocol_version":1,
   "extractor":{"name":"mp.solutions.hands","mediapipe_version", ...LEVEL1_HANDS_KWARGS},
   "limits":{"max_message_bytes":WS_MAX_MESSAGE_BYTES,"max_frame_side":WS_MAX_FRAME_SIDE,
   "max_frames_per_segment":ALPHABET_MAX_FRAMES}}`.
2. `reset_done`: `{"type":"reset_done","segment_id":int}` — gửi SAU khi graph mới đã tạo; `segment_id` tăng 1 mỗi reset
   (bắt đầu 0 lúc mở phiên, graph ban đầu cũng mới).
3. `hand_frame`: `{"type":"hand_frame","segment_id","frame_seq"(0-based trong segment),"received_seq",
   "client_timestamp":number|null,"frame_width","frame_height","landmarks":[[x,y,z]×21]|null,
   "handedness":"Left"|"Right"|"","handedness_score":number|null,
   "metrics":{"decode_ms","extract_ms","server_total_ms"}}` (thời gian đo bằng `time.perf_counter`).
   `landmarks` là float32 của MediaPipe đổi sang float Python (không làm tròn), để JSON đi-về giữ nguyên giá trị.
4. `error`: `_ws_error` với mã ∈ {`message_too_large` (đóng 1009), `bad_message`, `bad_config`, `bad_timestamp`,
   `decode_failed`, `unsupported_format`, `frame_too_large`, `model_unavailable` (đóng 1011)}; lỗi một message không đóng
   phiên; frame lỗi KHÔNG tăng `frame_seq` và không đưa vào tracker.

### 3.4 Chế độ "Ký từ": client WS v2
- `frontend/src/lib/ws.js`: `wsUrl(location, path)` → `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`.
  Mọi WS trong `frontend/src` dùng hàm này; không còn chuỗi `:8000` nào trong `frontend/src`.
- `frontend/src/lib/liveProtocol.js`: reducer THUẦN `reduceLive(state, msg, nowMs)` (không React, test bằng `node --test`):
  - `session_info`: lưu `pipeline`, `protocol_version` (≠ 2 → `state.fatal = "protocol_mismatch"`), `model`
    (`model_type`, `is_default`), `segmenter.max_sign_s` (harmonized), `limits`.
  - `frame_result` legacy: cập nhật `gloss/confidence/top5/status/buffer_fill/buffer_capacity` (lấy từ message, bỏ số 60
    cứng), `landmarks`, `metrics`; thêm từ vào `words` khi `status` chuyển sang `CONFIRMED` với gloss mới (giữ hành vi cũ
    của `Phase12Pipeline.jsx:81-89`).
  - `frame_result` harmonized: chỉ cập nhật trạng thái ghi (`status` IDLE/RECORDING/WAIT_REST, `segment.recording_s`,
    `hand_detected`, `hand_active`), `landmarks`, `metrics`; KHÔNG động tới kết quả dự đoán đang hiện.
  - `sign_result`: `lastSign = {gloss, confidence, top5, segment, segment_id}`; thêm `gloss` vào `words` (KHÔNG khử trùng,
    §3.8); `lastSign.client_e2e_ms = nowMs - metrics.trigger_client_timestamp` khi trigger là số (để DoD 8 đo được).
  - `sign_discarded`: `lastDiscard = {reason, segment}`; UI đổi `reason` sang câu tiếng Việt.
  - `error`: `lastError = {code, detail}`; `message_too_large`/`model_unavailable` → `state.fatal = code`.
  - `type` lạ: tăng `state.unknownMessages`, không ném lỗi.
- `Phase12Pipeline.jsx`: dùng `wsUrl(window.location, '/ws/live-stream')` + `reduceLive`; hiện huy hiệu pipeline/model,
  "Đang ghi ký hiệu" + thanh `recording_s / max_sign_s` (harmonized), lý do bỏ đoạn, lỗi theo `code`; top-5 + confidence
  của `sign_result` (harmonized) hoặc `frame_result` (legacy); nút "Xóa từ cuối". Xóa nút "Test Frame" và chuỗi base64 1×1.
- `CameraCapture.jsx`: `timestamp = nowMs()` (`performance.timeOrigin + performance.now()`, đơn điệu, dùng chung với
  reducer); lấy socket qua ref/getter thay vì giá trị `wsRef.current` lúc render (tránh socket cũ sau khi nối lại).
- `PredictionDisplay.jsx`, `Navbar.jsx`: bỏ ":8000".
- `RealtimeStream.jsx` (mã chết): CHỈ thay dòng URL bằng `wsUrl(...)` và (Lần sửa 1) bỏ `:8000` khỏi chuỗi báo lỗi.
  KHÔNG xóa file (xóa file là điểm dừng); ghi vào backlog "hỏi người dùng trước khi xóa RealtimeStream.jsx".

### 3.5 CORS, Origin của WS, bind
- `backend/main.py`: `DEFAULT_DEV_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")`;
  hàm thuần `parse_cors_origins(value: Optional[str]) -> Tuple[str, ...]`: `None`/rỗng → mặc định; tách theo dấu phẩy,
  bỏ khoảng trắng; phần tử `*`, rỗng, hoặc không bắt đầu bằng `http://`/`https://`, hoặc có dấu `/` ở cuối → `ValueError`.
  `ALLOWED_ORIGINS = parse_cors_origins(os.environ.get("VSL_CORS_ORIGINS"))` lúc import (sai → không khởi động được).
- `CORSMiddleware(allow_origins=list(ALLOWED_ORIGINS), allow_credentials=False, allow_methods=["GET", "POST"],
  allow_headers=["Content-Type"])`. Frontend không dùng cookie/credentials. Giữ thứ tự middleware (CORS ngoài cùng,
  `backend/main.py:324`).
- `ws_origin_allowed(origin: Optional[str]) -> bool`: không có header `Origin` → True (client không phải trình duyệt: smoke
  test, script đo; trình duyệt luôn gửi Origin); có → khớp CHÍNH XÁC một phần tử `ALLOWED_ORIGINS` (`"null"` bị từ chối).
  Cả `/ws/live-stream` và `/ws/hand-landmarks` gọi TRƯỚC `accept()`; bị từ chối → `await websocket.close(code=1008)`
  (bắt tay trả 403), log cảnh báo với origin cắt ngắn bằng `_short`, KHÔNG gửi `session_info`, KHÔNG nạp model.
- Bind: `start_fullstack.ps1` `--host 127.0.0.1`; `uvicorn.run(host="127.0.0.1", ...)` trong `backend/main.py`;
  `frontend/vite.config.js` thêm `strictPort: true` cho `server` và `preview`, KHÔNG đặt `host: true`/`0.0.0.0`.
- Qua proxy Vite, trình duyệt thấy `/api` và `/ws` là cùng origin → CORS không tham gia; backend vẫn thấy
  `Origin: http://localhost:3000` ở bắt tay WS nên Origin check vẫn có hiệu lực. CORS chỉ còn ý nghĩa khi một trang
  origin khác gọi thẳng :8000.
- (Lần sửa 2) KHÔNG tắt HMR / không đổi `server.hmr`/`server.ws` của Vite (xem 0B.1).

### 3.6 Smoke test Phase 12 và tài liệu
- `scripts/smoke_test_phase12.py` (sửa, vẫn là script thủ công dùng `TestClient`): message đầu phải là `session_info`
  (`protocol_version == 2`, `pipeline` ∈ {legacy, harmonized_v1}); các bước sau phân nhánh theo `pipeline`
  (legacy: `frame_result` đủ khóa cũ; harmonized: `frame_result` có `prediction is None`); text rác → một message
  `type == "error"` với `code` thuộc bảng mã §3.6 kế hoạch 04 (in ra mã thật); video thật 30 frame: đếm message theo
  `type`, 0 `error`; thêm bước `/ws/hand-landmarks` (session_info → reset_done → hand_frame trên 1 frame video hauuto
  thật); thêm bước Origin lạ bị từ chối. In "PASSED" chỉ khi mọi assert qua.
- `docs/phase12_api.md` (viết lại phần giao thức): cách chạy (127.0.0.1, proxy `/api` `/ws`, `strictPort`), chính sách
  CORS/Origin/`VSL_CORS_ORIGINS`; REST (health 200/503, fingerspelling status/sequence/compose/409, 413/422/503); WS
  `/ws/live-stream` v2 đầy đủ (chép bảng §3.6 kế hoạch 04 + nghĩa `dropped_frames` của kế hoạch 05 + thay đổi legacy ở
  review 04 mục 11); WS `/ws/hand-landmarks` (§3.3); các trường để đo DoD 8 (Ký từ: `trigger_client_timestamp`; Đánh vần:
  mốc client từ lúc bấm Dừng tới khi có phản hồi `/sequence` + `metrics` của hand_frame). Không ghi số đo độ trễ nào.

### 3.7 Kiểm tự động fullstack + e2e trên clip thật
- `scripts/make_fake_webcam_y4m.py --video <mp4> --out <y4m> [--max-frames N]`: đọc video bằng cv2, ghi Y4M 4:2:0 cùng
  kích thước (cắt 1 px nếu lẻ) và cùng fps (`F<num>:<den>`). File ra ở thư mục tạm NGOÀI repo (vd. `%TEMP%\vslt_e2e\`);
  không commit video/frame.
- `scripts/e2e_browser.cjs` (puppeteer-core + Edge; đường dẫn trình duyệt từ `VSL_E2E_BROWSER`, mặc định đường Edge của
  `take_screenshots.cjs`): cờ `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream
  --use-file-for-fake-video-capture=<y4m>`; mở `http://localhost:3000/`; ghi lại: console `error`, `pageerror`,
  `requestfailed`, HTTP ≥ 400, URL WS (CDP `Network.webSocketCreated`), `type` của mọi message WS nhận (CDP
  `Network.webSocketFrameReceived`), body + status của mọi `POST /api/fingerspelling/sequence|compose`.
  Chọn phần tử bằng `data-testid` (thêm vào component; danh sách ở B5/B6). In JSON ra file `--out`.
- `scripts/e2e_fullstack.py --scenario fingerspell|word [--model-type stgcn_h360] --video <mp4> --out <json>`:
  1. chạy `powershell -NoProfile -ExecutionPolicy Bypass -File start_fullstack.ps1` (env thêm `VSL_MODEL_TYPE` nếu có;
     `-ExecutionPolicy Bypass` chỉ cho tiến trình này, KHÔNG đổi policy hệ thống);
  2. chờ `GET http://127.0.0.1:8000/api/health` 200 và `http://localhost:3000/` 200 (timeout 180 s, ghi thời gian chờ);
  3. tạo y4m, chạy `node scripts/e2e_browser.cjs`;
  4. dừng cây tiến trình (`taskkill /T /F /PID`), kiểm cổng 8000/3000 đã rảnh;
  5. ghi JSON: `generated_by{command, git_commit, code_dirty}`, phiên bản node/Edge/mediapipe, clip id (không đường dẫn
     tuyệt đối, không landmark), kết quả kịch bản, danh sách lỗi console (nguyên văn, cắt 300 ký tự).
- (Lần sửa 2) Phân loại socket trong một hàm thuần của `scripts/e2e_fullstack.py`: socket HMR của Vite theo định nghĩa
  0B.1 (loại khỏi kiểm "qua `/ws/`", KHÔNG loại khỏi kiểm `:8000`); socket mồ côi StrictMode theo 0B.2.
- (Lần sửa 3) Mỗi path app có vai trò cố định theo kịch bản (bảng 0C.2): `used` theo luật mồ côi 0B.2; `tab_unmounted`
  (chỉ `/ws/live-stream` ở Đánh vần) theo `tab_unmounted_socket_rule`; path khác → đỏ. `e2e_browser.cjs` ghi thêm
  `created_t_s`/`closed_t_s` mỗi socket và `click_t_s` ở bước `tab_alphabet` (0C.4); luồng thao tác không đổi.
- Clip: Đánh vần — `data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4` (640×480, cỡ webcam; clip TRAIN của model Cấp
  1 → chỉ kiểm chạy được, KHÔNG phải độ chính xác). Ký từ — (Lần sửa 2, ghi đích danh) `qipedc_D0120T`
  (`data/Dataset/Videos/D0120T.mp4`) = phần tử đầu tiên KHÁC `qipedc_W03251B` của `scripts/live_clip_sample.py`
  `select_train_clips()` với tham số mặc định (n=8, seed=0, split TRAIN). KHÔNG dùng clip TEST/VAL nào.

### 3.8 Quyết định review 04 mục 8–9: TÁCH khỏi Việc 5
- **Mục 8 (tốc độ theo dt từng frame) và mục 9 (ký hiệu có nhịp nghỉ bị phát lặp, W03251B): KHÔNG làm trong kế hoạch này.**
  Tách thành kế hoạch riêng "segmenter live", đặt ngay sau Việc 5 trong backlog; phần chỉnh tham số chờ dữ liệu webcam
  của Bước 5.
- Lý do:
  1. Cả hai đổi hành vi cắt đoạn của đường harmonized (đoạn nào được dự đoán), tức đổi đầu vào model; cần test tương đương
     và bằng chứng riêng. Gộp vào việc nối UI sẽ trộn hai loại rủi ro trong một review.
  2. Chính sách cho mục 9 (gộp đoạn gần nhau / khử trùng gloss liên tiếp / đổi `rest_hold_s`) hiện chỉ có 1 clip bằng chứng
     (W03251B, n = 1). Kế hoạch 04 §3.4 cấm chỉnh tham số trên TEST; dữ liệu hợp lệ là clip TRAIN (nhiều clip) và webcam
     người dùng (Bước 5). Khử trùng gloss ở UI sẽ nuốt mất từ lặp thật mà người ký chủ ý.
  3. Mục 8 cần fixture tay nghỉ có nhiễu + mô phỏng rơi frame thật; với WebSocket thật (việc này bật được) mới đo được
     mẫu rơi frame thực tế — nên làm SAU khi UI chạy.
  4. Đường mặc định (legacy) không dùng `SignSegmenter`; UI của việc này vẫn đúng hợp đồng khi segmenter đổi về sau.
- Trong Việc 5: UI hiện TỪNG `sign_result` như server gửi (không khử trùng, không gộp), có nút "Xóa từ cuối"; `sign_discarded`
  hiện lý do. Như vậy hiện tượng lặp nhìn thấy được, không bị che. Ghi giới hạn này vào `docs/phase12_api.md`.

### 3.9 Ngoài phạm vi (ghi rõ để reviewer không tính là thiếu)
- Nút chọn chế độ, Ký câu (Việc 6); từ điển SQLite; proxy `/videos` `/raw_videos` cho tab Từ điển; đổi model mặc định
  (GATE); đo độ trễ DoD 8; clone sạch; số liệu cứng trong `Reports.jsx` (DoD 9).
- `detail` 503 có thể chứa tên file (review 04 mục 6 / review 05): KHÔNG sửa ở đây — sửa sẽ đổi body mà test cũ đang
  kiểm, và sau khi bind 127.0.0.1 phạm vi lộ chỉ còn máy cục bộ. Đưa vào backlog 8.
- (Lần sửa 1) Đo lệch Kaggle↔cục bộ trên toàn bộ clip hauuto: đề xuất backlog (§0.4), không làm ở đây.
- (Lần sửa 2) Tắt HMR / chạy e2e trên `vite preview`: không làm (0B.1).
- (Lần sửa 3) Đổi tab mặc định trong `App.jsx`, bỏ `StrictMode`, hay thêm bước chờ trong kịch bản trình duyệt để luật cũ tự
  xanh: không làm (0C.2).

## 4. Chia việc

Quy ước chung cho mọi bước:
- `P6` = HEAD lúc coder bắt đầu B0 (commit đã chứa kế hoạch này; ghi hash vào `docs/plans/06-progress.md`).
- Trước khi sửa một symbol: GitNexus `impact <symbol> --direction upstream`; `risk: UNKNOWN` → xác nhận bằng text search.
  Trước MỖI commit: `detect-changes --scope all`; ghi risk thật vào commit message. KHÔNG `git commit --amend`, không
  `git add -A`/`git add .` (3 file ` D` của người dùng + nhiều file untracked).
- Viết test trước (hoặc cùng lúc) với code. Mỗi bước kết thúc bằng 1 commit và 1 đoạn trong `docs/plans/06-progress.md`
  (lệnh đã chạy + output thật rút gọn + hash).
- Thư mục tạm ngoài repo: `../_plan06_tmp/`.
- (Lần sửa 1) AC2 ở mốc trung gian B4–B6 theo §0.3; từ B7 trở đi AC2 phải xanh hoàn toàn.
- (Lần sửa 2) Từ B8b trở đi, lệnh AC2 là bản 31 module (0B.4).

| Bước | Nội dung | Phụ thuộc | Ước lượng |
|---|---|---|---|
| **B0** | Mốc: chạy lệnh AC2 (chỉ 25 module cũ) tại `P6`, lưu output + `git status --porcelain` vào `../_plan06_tmp/b0_*.txt`; ghi `node --version`, `npm ls --depth=0` (lưu file), Edge có tồn tại ở đường mặc định không, `mediapipe.__version__`; `impact` cho `websocket_live_stream`, `_parse_ws_message`, `_decode_frame`, `health`. Tạo `docs/plans/06-progress.md`. Commit. | — | 0.5 giờ |
| **B1** | CORS/Origin/bind (§3.5): test `tests/test_cors_origin_bind.py` (AC3) trước → sửa `backend/main.py`, `start_fullstack.ps1`, `frontend/vite.config.js`. Chạy AC3 + `tests.test_ws_live_contract tests.test_fingerspelling_limits tests.test_fingerspelling_api tests.test_ws_dropped_frames`. Commit. | B0 | 1.5 giờ |
| **B2** | `src/inference/hand_live.py` + endpoint `/ws/hand-landmarks` (§3.3): test `tests/test_hand_landmarks_ws.py` (AC4) trước. Commit. | B1 (dùng `ws_origin_allowed`) | 2 giờ |
| **B3** | Tương đương Cấp 1 train↔live: `tests/test_hand_live_equivalence.py` (AC5) + `scripts/hand_live_check.py` và JSON (AC6). Nếu AC5-a không bằng hệt → DỪNG, báo planner (§7). Commit. | B2 | 2 giờ |
| **B4** | Thư viện JS thuần `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` + `frontend/tests/*.test.mjs` + `frontend/tests/build_body_cli.mjs`; thêm script `"test": "node --test tests/*.test.mjs"` vào `frontend/package.json` (Lần sửa 1; lệnh chạy chính thức: `cd frontend && npm test`); Python `tests/test_frontend_contract.py` (AC7-d, AC8; guard được phép đỏ theo §0.3). Commit. | B2 (định dạng hand_frame) | 2 giờ |
| **B5** | UI "Ký từ" (§3.4): `Phase12Pipeline.jsx`, `CameraCapture.jsx`, `PredictionDisplay.jsx`, `Navbar.jsx`, dòng URL + chuỗi báo lỗi của `RealtimeStream.jsx`; `data-testid`: `live-connection`, `live-pipeline`, `live-model`, `live-status`, `live-recording`, `live-gloss`, `live-confidence`, `live-top5`, `live-discard`, `live-error`, `live-words`, `live-undo`, `camera-start`, `camera-stop`. `npm run build` (AC9). Sau B5 guard chỉ còn vi phạm trong `Fingerspelling.jsx` (§0.3). Commit. | B4 | 2 giờ |
| **B6** | UI "Đánh vần" (§3.2): viết lại `Fingerspelling.jsx`; `data-testid`: `fs-status`, `fs-ws`, `fs-record`, `fs-stop`, `fs-frames`, `fs-prediction`, `fs-confidence`, `fs-candidates`, `fs-error`, `fs-add`, `fs-space`, `fs-backspace`, `fs-clear`, `fs-composed`, `fs-warnings`. `npm run build`. Sau B6 guard xanh (0 vi phạm). Commit. | B4 | 2 giờ |
| **B7** | `scripts/smoke_test_phase12.py` (AC10) chạy với model mặc định VÀ `VSL_MODEL_TYPE=stgcn_h360`; viết lại `docs/phase12_api.md` (AC11, test thêm vào `tests/test_frontend_contract.py`). AC2 phải xanh hoàn toàn. Commit. | B2, B5, B6 | 1.5 giờ |
| **B8** | E2E: `scripts/make_fake_webcam_y4m.py`, `scripts/e2e_browser.cjs`, `scripts/e2e_fullstack.py`; chạy 3 kịch bản AC12 (Đánh vần mặc định, Ký từ mặc định, Ký từ `stgcn_h360`) tại HEAD sạch; commit script + 3 JSON. (Đã làm: 7e38118, e3d0df8 — bị thay thế bởi B8b theo Lần sửa 2.) | B5, B6, B7 | 2 giờ |
| **B8b** | (Lần sửa 2, 0B.5 bước 1–3) Test AC12-t trước trong `tests/test_frontend_contract.py` → hàm thuần phân loại socket HMR/mồ côi + 4 kiểm mới trong `scripts/e2e_fullstack.py` → AC2 31 module xanh → commit; tại HEAD sạch đó chạy lại 3 kịch bản (clip giữ nguyên) → 3 JSON `all_checks_pass: true` → commit 3 JSON. Kiểm nào đỏ → DỪNG (§7-8). (Lần sửa 3: B8b-1, B8b-2 xong — 302072c, eb379fa; B8b-3 dừng §7-8 ở 1a4e182; phần chạy chính thức chuyển sang B8c.) | B8 | 1.5 giờ |
| **B8c** | (Lần sửa 3, 0C.5 bước 1–3) Test AC12-t mục 10 trước (16 test cũ không sửa) → `e2e_browser.cjs` ghi `created_t_s`/`closed_t_s`/`click_t_s` + `e2e_fullstack.py` vai trò path + `tab_unmounted_socket_rule` → AC12-t xanh, AC2 31 module xanh → commit; tại HEAD sạch đó chạy chính thức 3 kịch bản, mỗi kịch bản 1 lần → 3 JSON `all_checks_pass: true` → commit 3 JSON. Kiểm nào đỏ → DỪNG (§7-8, §7-10). | B8b-2 | 2 giờ |
| **B9** | Đóng: chạy AC2 đầy đủ + `npm test` + build; so `git status --porcelain` với B0; THÊM 1 dòng progress_log (AC13), ghi backlog đề xuất (kế hoạch "segmenter live"; hỏi người dùng trước khi xóa `RealtimeStream.jsx`; `detail` 503; đo lệch Kaggle↔cục bộ toàn bộ hauuto). Commit. Orchestrator gọi vslt-reviewer. (Lần sửa 2: làm theo 0B.5 bước 4 — AC2 31 module, AC1 theo 0B.3, code không đổi sau lượt e2e — tại HEAD cuối sau B8b. Lần sửa 3: tại HEAD cuối sau B8c, 0C.5 bước 4.) | B0–B8c | 0.5 giờ |

Tổng ước lượng ≈ 16 giờ (+ 1.5 giờ B8b, + 2 giờ B8c), GPU 0 giờ, không Kaggle, không cài gói.

**Chặng giao gợi ý:** chặng 1 = B0–B2 (xong); chặng 2 = B3–B4 (xong); chặng 3 = B5–B7 (xong); chặng 4 = B8–B9 (B8 xong;
B8b-1/B8b-2 xong; còn B8c + B9b theo Lần sửa 3).

## 5. Tiêu chí chấp nhận (hợp đồng — coder KHÔNG được đổi; chỉ planner đổi và phải ghi lý do)

Mọi lệnh Python chạy qua `.venv/Scripts/python` với `PYTHONIOENCODING=utf-8`, từ thư mục gốc repo. "Mới" = file/lớp test do kế
hoạch này thêm. Test mới không cần mạng, không ghi file trong repo (chỉ thư mục tạm), và KHÔNG skip trên máy này (được
`skipUnless` cho clone sạch, lý do nêu rõ file thiếu).

**AC1 — Phạm vi thay đổi.** (Lần sửa 2: đánh giá theo 0B.3 — danh sách dưới áp cho hợp file của các commit `C06` của coder;
commit không thuộc 06 được quy nhóm theo AC1-b..d.) `git diff --name-status P6 HEAD` (phần thuộc `C06`) chỉ chứa:
- `backend/main.py` (M); `src/inference/hand_live.py` (A); `start_fullstack.ps1` (M, chỉ tham số `--host`);
- `frontend/vite.config.js` (M); `frontend/package.json` (M, CHỈ thêm khóa `scripts.test`); `frontend/index.html` (M, chỉ
  nếu cần để hết lỗi console ở AC12, ghi lý do);
- `frontend/src/components/{Phase12Pipeline,CameraCapture,PredictionDisplay,Navbar,Fingerspelling}.jsx` (M);
  `frontend/src/components/RealtimeStream.jsx` (M, chỉ: dòng URL, 1 dòng import, và (Lần sửa 1) phần chữ của chuỗi báo lỗi
  có `:8000`; `git diff P6 HEAD -- frontend/src/components/RealtimeStream.jsx` đổi tối đa 3 dòng, không đổi logic);
  `frontend/src/lib/{ws,liveProtocol,fingerspelling}.js` (A); `frontend/tests/*.mjs` (A);
- `scripts/smoke_test_phase12.py` (M); `scripts/{hand_live_check,make_fake_webcam_y4m,e2e_fullstack}.py`,
  `scripts/e2e_browser.cjs` (A);
- `tests/{test_cors_origin_bind,test_hand_landmarks_ws,test_hand_live_equivalence,test_frontend_contract}.py` (A);
- `reports/fingerspell_live_<YYYY-MM-DD>/hand_live_check.json`, `reports/e2e_<YYYY-MM-DD>/*.json` (A; (Lần sửa 2) M nếu
  ghi đè cùng ngày);
- `docs/phase12_api.md` (M); `docs/progress_log.md` (M, chỉ thêm); `docs/plans/06-progress.md` (A/M);
  `docs/plans/06-viec5-frontend.md` (chỉ planner).

KHÔNG đổi: `frontend/package-lock.json`, `frontend/src/App.jsx`, `Dictionary.jsx`, `Reports.jsx`, `scripts/extract_hands_batch.py`,
`src/data/**`, `src/inference/{harmonized_live,sign_segmenter,predictor}.py`, `configs/`, `checkpoints/`, `data/`, mọi test
đã có, `docs/reviews/*`. Không xóa file nào. 3 file data của người dùng vẫn ` D` chưa staged. Không file `.pt/.npz/.mp4/.y4m/
.png/.jpg/.log` nào được thêm vào git; `frontend/dist` và `node_modules` không vào git. ((Lần sửa 3) `frontend/src/main.jsx`
không nằm trong danh sách được sửa ở trên nên cũng KHÔNG đổi.)

**AC2 — Không hồi quy.** (Lần sửa 2) Lệnh đóng việc — 31 module (25 của kế hoạch 05 + 4 module mới của 06 + 2 module từ merge
cloud bbfdff3, xem 0B.4):
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts tests.test_cors_origin_bind tests.test_hand_landmarks_ws tests.test_hand_live_equivalence tests.test_frontend_contract tests.test_archive_private_kaggle_r05 tests.test_backend_source_guard -v`
(Lệnh 29 module trước Lần sửa 2 là tập con; áp cho B7/B8 đã làm.)
- **Đóng việc (B7, B8, B8b, B8c, B9):** 0 failure, 0 error, 0 skip. Số test báo theo module, trước → sau: 25 module cũ = B0;
  4 module của 06 = B7 + số test AC12-t (Lần sửa 2 và (Lần sửa 3) mục 10); 2 module merge = số trên cây merge (review cloud).
  Chênh phải giải thích.
- **(Lần sửa 1) Mốc trung gian B4–B6:** như trên, ngoại trừ failure DUY NHẤT được phép là
  `TestFrontendSourceGuard.test_no_violation`, với tập vi phạm (cặp file + mẫu) là tập con của 14 vi phạm ghi ở
  06-progress B4, không tăng qua các mốc; sau B5 chỉ còn trong `Fingerspelling.jsx`; sau B6 = 0. Commit có guard đỏ ghi
  "guard đỏ có chủ đích, còn N vi phạm" trong message.
- `git diff P6 HEAD -- tests/` với mọi file test đã có ở `P6`: 0 dòng `-`.
- `git status --porcelain` trước và sau khi chạy giống hệt.
- **(Lần sửa 1) Test JS:** `cd frontend && npm test` (script `"test": "node --test tests/*.test.mjs"`) → 0 fail; số file
  test Node báo đã chạy == số dòng của `git ls-files "frontend/tests/*.test.mjs"`; báo số test và `node --version`.

**AC3 — CORS / Origin / bind (`tests/test_cors_origin_bind.py`).**
- a. `parse_cors_origins`: `None`→`DEFAULT_DEV_ORIGINS`; `""`→`DEFAULT_DEV_ORIGINS`; `" http://a:1 , https://b "`→
  `("http://a:1", "https://b")`; mỗi giá trị sau → `ValueError`: `"*"`, `"http://a,*"`, `"http://a,"`, `"ftp://x"`,
  `"http://a/"`, `"null"`.
- b. `api.DEFAULT_DEV_ORIGINS == ("http://localhost:3000", "http://127.0.0.1:3000")`; khi test chạy không có
  `VSL_CORS_ORIGINS` thì `api.ALLOWED_ORIGINS == api.DEFAULT_DEV_ORIGINS`. Trong `api.app.user_middleware` có đúng một
  `CORSMiddleware` với `allow_origins == list(DEFAULT_DEV_ORIGINS)`, `allow_credentials is False`, và `"*"` không nằm trong
  `allow_origins`, `allow_methods`, `allow_headers`.
- c. HTTP (`POST /api/fingerspelling/compose {"tokens": ["a"]}`, không cần model):
  - `Origin: http://localhost:3000` → 200, `access-control-allow-origin == "http://localhost:3000"`, KHÔNG có header
    `access-control-allow-credentials`;
  - `Origin: http://evil.example` → không có header `access-control-allow-origin`;
  - preflight `OPTIONS` với `Origin: http://evil.example` + `Access-Control-Request-Method: POST` → không có
    `access-control-allow-origin` và mã khác 2xx; với `Origin: http://127.0.0.1:3000` → 200 và ACAO bằng origin đó;
  - không response nào trong test có ACAO `*`.
- d. WS: với mỗi path ∈ {`/ws/live-stream`, `/ws/hand-landmarks`} và mỗi origin ∈ {`http://evil.example`, `null`,
  `http://localhost:3001`, `http://localhost:3000.evil.example`, `HTTP://LOCALHOST:3000`}: `websocket_connect(path,
  headers={"origin": ...})` ném `WebSocketDisconnect` với `code == 1008`; `backend.main._active_model` và
  `HandLandmarkSession` (vá bằng `MagicMock`) KHÔNG được gọi.
- e. Origin hợp lệ vẫn qua: `/ws/hand-landmarks` với `Origin: http://localhost:3000` → message đầu `type == "session_info"`;
  `/ws/live-stream` với `Origin: http://localhost:3000` và `_active_model` vá để ném `ModelUnavailable` → nhận
  `error{code: "model_unavailable"}` rồi đóng 1011 (chứng minh đã qua kiểm Origin mà không nạp model thật); không có header
  Origin → như Origin hợp lệ.
- f. `ws_origin_allowed`: `None`→True; `"http://localhost:3000"`→True; `"http://127.0.0.1:3000"`→True; `""`→False; `"null"`→False.
- g. Bind (kiểm văn bản): `start_fullstack.ps1` chứa `--host 127.0.0.1` và không chứa `0.0.0.0`; `backend/main.py` không chứa
  `0.0.0.0` và lời gọi `uvicorn.run(` có `host="127.0.0.1"`; `frontend/vite.config.js` có `strictPort: true` trong cả
  `server` và `preview`, không có khóa `host`.

**AC4 — Hợp đồng `/ws/hand-landmarks` (`tests/test_hand_landmarks_ws.py`, MediaPipe thật, CPU).**
- a. `LEVEL1_HANDS_KWARGS` bằng hệt dict keyword của lời gọi `Hands(...)` DUY NHẤT trong `scripts/extract_hands_batch.py`
  (đọc bằng `ast.literal_eval` từng keyword). Subprocess `import src.inference.hand_live, sys; print('torch' in
  sys.modules, 'fastapi' in sys.modules)` in `False False`.
- b. `session_info` là message đầu, đủ khóa §3.3; `extractor.mediapipe_version == mediapipe.__version__` và bằng giá trị
  DUY NHẤT của cột `mediapipe_version` trong `manifest.csv` (đọc từ file, không gõ tay);
  `limits.max_frames_per_segment == api.ALPHABET_MAX_FRAMES`.
- c. Reset: `segment_id` ban đầu 0; mỗi `control/reset` → `reset_done` với `segment_id` +1; `frame_seq` bắt đầu lại từ 0.
  Spy constructor `mp.solutions.hands.Hands`: số lần gọi = 1 + số reset; graph cũ được `close()` đúng 1 lần mỗi reset.
- d. Frame thật: frame của `a_hau_A_001.mp4` có tay (chỉ số lấy từ kết quả `_extract_one` trong test, không gõ tay) →
  `landmarks` 21×3 số, |v| ≤ 10, `handedness` ∈ {Left, Right}, `0 < handedness_score ≤ 1`; frame đen 640×480 →
  `landmarks is None`, `handedness == ""`, `handedness_score is None`.
- e. Lỗi (phiên KHÔNG đóng, frame hợp lệ tiếp theo vẫn nhận `hand_frame` và lỗi không làm tăng `frame_seq`):
  text rác → `type == "error"`, `code` ∈ {bad_message, decode_failed, unsupported_format}; PNG header khai 4000×10 →
  `frame_too_large` và `cv2.imdecode` KHÔNG được gọi (spy); `timestamp: "x"` → `bad_timestamp`. Message > 1 MiB →
  `message_too_large` rồi đóng 1009. `detail` ≤ 200 ký tự và không chứa chuỗi base64 đã gửi.
- f. Tuần tự, không bỏ frame: gửi liên tiếp 5 frame rồi mới đọc → đúng 5 `hand_frame`, `frame_seq` 0..4, `received_seq`
  tăng ngặt, `client_timestamp` bằng hệt timestamp đã gửi; frame binary → `client_timestamp is None`.
- g. `Hands(...)` ném lỗi khi khởi tạo (vá) → `error{model_unavailable}` + đóng 1011.

**AC5 — Tương đương train↔live Cấp 1 (`tests/test_hand_live_equivalence.py`).**
- Mẫu: `np.random.default_rng(0)` chọn 8 clip hauuto trong `manifest.csv` có video cục bộ (hàm ánh xạ `sample_id` →
  `data/external/hauuto_raw/raw/raw/<signer>/<tên>.mp4` dùng chung với `scripts/hand_live_check.py`; test assert tìm thấy
  ≥ 8) + 2 clip qipedc đầu tiên (theo `sample_id`) có `data/Dataset/Videos/<id>.mp4`.
- Offline = `_extract_one` của `scripts/extract_hands_batch.py` (import, không sửa) chạy vào thư mục tạm, CÙNG máy.
  Live = đọc cùng video bằng `cv2.VideoCapture` → PNG → WS text data-URL, `timestamp = i * 1000 / fps` → một `reset` đầu
  clip → dãy `hand_frame`.
- a. Mỗi clip: số frame bằng nhau; `detected` `array_equal`; landmark các frame có tay `np.array_equal` sau khi ép float32;
  nhãn handedness bằng nhau; score bằng nhau (float32).
- b. Body `/sequence` dựng từ live (theo §3.2) == body dựng từ npz offline (theo cách của
  `tests/test_fingerspelling_deployed.body`, thêm `timestamps_ms` như nhau) — so dict JSON bằng hệt. POST cả hai với
  checkpoint triển khai (`checkpoints/alphabet_best.pt`, sha256 phải bằng `provenance.json`) → JSON response bằng hệt.
- c. Model offline dựng từ checkpoint (như `TestDeployedCheckpointEquivalence`) trên `alphabet_clip_features` của npz
  offline → top-1 bằng `prediction` của live, `|Δconfidence| ≤ 1e-4`.
- d. Test in mỗi clip: `sample_id`, số frame, số frame có tay (từ output, không gõ tay). Không có câu nào về độ chính xác.
- Nếu (a) KHÔNG bằng hệt: DỪNG, báo planner (không nới sang dung sai).

**AC6 — Báo cáo lệch nguồn (`scripts/hand_live_check.py`).** Lệnh:
`.venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0 --out reports/fingerspell_live_<YYYY-MM-DD>/hand_live_check.json`
(cùng mẫu AC5). JSON có `generated_by{command, git_commit, code_dirty: false}`, `note` ("report only; hauuto clips are
training data of the deployed Level 1 model; not accuracy"), và mỗi clip: `sample_id`, `source`, `n_frames`;
`live_png_vs_local_offline{detected_equal, max_abs_diff}`; `live_jpeg90_vs_live_png{detected_agree, max_abs_diff_both}`;
`kaggle_npz_vs_local_offline{n_frames_equal, detected_agree, max_abs_diff_both}`;
`sequence_top1{live_png, live_jpeg90, kaggle_npz}`. KHÔNG có mảng landmark trong JSON (test trong
`tests/test_frontend_contract.py` cấm các khóa `landmarks`/`raw_landmarks`/`coords`). Không có ngưỡng pass cho hai so sánh
JPEG và Kaggle — chỉ ghi nhận. Reviewer chạy lại → phần thân giống hệt, trừ `generated_by`/thời gian.

**AC7 — Thư viện JS (`frontend/tests/*.test.mjs`; chạy bằng `cd frontend && npm test` — Lần sửa 1).**
- a. `wsUrl({protocol: 'http:', host: 'localhost:3000'}, '/ws/live-stream') === 'ws://localhost:3000/ws/live-stream'`;
  `https:` → `wss://`; giữ nguyên port của host.
- b. `reduceLive` với message mẫu viết theo lược đồ §3.6 kế hoạch 04 (mẫu giao thức, không phải dữ liệu):
  session_info v2 legacy và harmonized; `protocol_version: 3` → `fatal === 'protocol_mismatch'`; legacy CONFIRMED
  chuyển trạng thái thêm 1 từ, CONFIRMED lặp cùng gloss không thêm; `buffer_capacity` lấy từ message; `frame_result`
  harmonized KHÔNG đổi `lastSign`; hai `sign_result` liên tiếp cùng gloss → `words` có CẢ HAI; `client_e2e_ms ===
  nowMs - trigger_client_timestamp`; `sign_discarded` lưu `reason`; `error message_too_large` → `fatal`; type lạ →
  `unknownMessages` +1; state đầu vào được `deepFreeze` và không bị sửa.
- c. `buildSequenceBody`: frame không tay → `null` (không bao giờ khung toàn 0); sắp theo `frame_seq` khi đầu vào lộn
  xộn; bỏ frame khác `segment_id`; kích thước đổi → lỗi `frame_size_changed`; quá `max_frames_per_segment` → lỗi; rỗng →
  lỗi; `source_mirrored === false`; `timestamps_ms` không giảm.
- d. (Python, `tests/test_frontend_contract.py`) Chéo ngôn ngữ: lấy dãy `hand_frame` live của 1 clip hauuto (tạo trong
  test như AC5) → ghi JSON tạm → `node frontend/tests/build_body_cli.mjs <in> <out>` → body bằng hệt body Python dựng
  từ npz offline (AC5-b), rồi POST → 200. `skipUnless(shutil.which("node"))`; trên máy này không skip.

**AC8 — Guard mã nguồn frontend (`tests/test_frontend_contract.py`).** Duyệt mọi file `frontend/src/**/*.{js,jsx}`
(không ngoại lệ, kể cả `RealtimeStream.jsx`): không chứa `Math.random`; không chứa `:8000`; không có literal
`ws://`/`wss://`; không có `data:image/jpeg;base64,/9j/`; không có chuỗi `'/api/fingerspelling'` đứng riêng (endpoint
ảnh cũ; regex khớp dấu nháy đóng ngay sau `fingerspelling`); không có `bufferCapacity={60}` và `25 lớp`. Test tự kiểm:
đưa từng mẫu vi phạm (chuỗi trong bộ nhớ) vào hàm guard → hàm báo lỗi. Mốc được phép đỏ: xem AC2 (Lần sửa 1).

**AC9 — Build, không thêm gói.** `cd frontend && npm run build` exit 0 (build vào `frontend/dist`, đã bị ignore);
`npm ls --depth=0` giống hệt file B0; `git diff P6 HEAD -- frontend/package-lock.json` rỗng; diff `frontend/package.json`
chỉ thêm `"test"` ((Lần sửa 2) dòng khóa đứng trước chỉ đổi vì thêm dấu phẩy được chấp nhận; không dòng nào khác đổi).

**AC10 — Smoke test Phase 12.** `.venv/Scripts/python scripts/smoke_test_phase12.py` exit 0 và in dòng PASSED, chạy 2
lần: model mặc định và `VSL_MODEL_TYPE=stgcn_h360`. Output (cả mã lỗi thật của bước text rác và số message theo `type`)
chép vào `06-progress.md`.

**AC11 — `docs/phase12_api.md` (`tests/test_frontend_contract.py`).**
- Không chứa `0.0.0.0` và `ws://localhost:8000`.
- Chứa MỌI mã lỗi mà `backend/main.py` phát ra (test tự trích bằng regex từ `_ws_error("…"`/`WsError("…"`, không gõ tay),
  mọi `reason` của `sign_discarded` (trích từ `src/inference/sign_segmenter.py`/`backend/main.py`), mọi `type` message của
  cả hai WS (`session_info`, `frame_result`, `sign_result`, `sign_discarded`, `error`, `reset_done`, `hand_frame`),
  `VSL_CORS_ORIGINS`, `1008`, `1009`, `1011`, `dropped_frames`, `trigger_client_timestamp`, `/ws/hand-landmarks`.
- Có mục "Giới hạn" nêu: ký hiệu có nhịp nghỉ có thể bị phát 2 lần (W03251B), segmenter chưa chỉnh tham số, landmark
  Cấp 1 live dùng JPEG (ảnh hưởng ghi ở AC6), Origin check không chặn client không phải trình duyệt.
- (Lần sửa 1) Mục "Giới hạn" còn phải nêu hai lệch đo được ở AC6, trích từ
  `reports/fingerspell_live_2026-09-29/hand_live_check.json` (ghi đường dẫn + `generated_by.git_commit`): (i) landmark
  train (Kaggle/Linux) và landmark trích lại trên máy này KHÔNG bằng hệt — số clip có cờ detected lệch và max diff lớn nhất;
  (ii) JPEG q90 so với PNG — số clip lệch cờ detected và max diff lớn nhất; kèm câu "top-1 trùng trên 10 clip TRAIN, không
  chứng minh bền vững". Test kiểm: tài liệu chứa đường dẫn JSON và giá trị `git_commit` của nó, và mọi số thập phân trong
  đoạn này có mặt trong JSON (đọc từ file, không gõ tay trong test).

**AC12 — E2E fullstack trên clip thật (`scripts/e2e_fullstack.py`).** 3 lần chạy tại HEAD sạch
(`git status --porcelain -- backend src frontend scripts tests` rỗng), mỗi lần 1 JSON trong `reports/e2e_<YYYY-MM-DD>/`:
`fingerspell_default.json`, `word_default.json`, `word_stgcn_h360.json`. (Lần sửa 2) Mỗi lệnh exit 0 và JSON có
`all_checks_pass: true`; 3 JSON là của lượt chạy B8b (script chứa luật 0B.1/0B.2), không phải e3d0df8. ((Lần sửa 3) Thay
"lượt chạy B8b" bằng "lượt chạy chính thức B8c" — script chứa luật 0B.1/0B.2 và 0C.2; mỗi kịch bản chạy đúng 1 lần; JSON thử
ngoài repo của B8b-3 không phải bằng chứng.) Chung cho cả 3:
- `/api/health` 200 (`status == "ok"`) và trang 3000 200, (Lần sửa 2) cả hai trong CÙNG cửa sổ 180 s tính từ lúc khởi chạy
  `start_fullstack.ps1`; ghi thời gian chờ từng cái; ghi `model_type`, `is_default` từ health.
- 0 console `error`, 0 `pageerror`, 0 `requestfailed`, 0 HTTP ≥ 400 (lỗi nguyên văn được liệt kê nếu có).
- (Lần sửa 2, thay mệnh đề "Mọi URL WS bắt đầu bằng `ws://localhost:3000/ws/`…"; lý do 0B.1):
  - `ws_no_8000_any_socket`: KHÔNG socket nào (kể cả socket HMR, kể cả socket mồ côi) có URL chứa `:8000`.
  - `ws_app_urls_via_proxy`: có ≥ 1 socket không phải HMR; mọi socket không phải HMR có URL bắt đầu bằng
    `ws://localhost:3000/ws/`.
  - `vite_hmr_socket_rule`: tối đa 1 socket HMR mỗi lượt; socket HMR = thỏa đồng thời (1) URL khớp toàn bộ
    `^ws://localhost:3000/\?token=[A-Za-z0-9_-]+$`, (2) `Sec-WebSocket-Protocol` bắt tay == `vite-hmr`, (3) mọi message nhận
    có `type == "connected"`; mọi socket có protocol `vite-hmr` mà không thỏa (1) hoặc (3) → đỏ. JSON liệt kê riêng socket
    HMR đã loại.
  - `strictmode_orphan_rule`: ((Lần sửa 3) CHỈ cho path `used` của kịch bản theo bảng 0C.2 — Đánh vần `/ws/hand-landmarks`,
    Ký từ `/ws/live-stream`; path `used` không có socket → đỏ) socket "mồ côi" (không phải kiểm message đầu `session_info`)
    chỉ khi: 0 message, `closed: true`, không phải socket cuối của path; tối đa 1 mồ côi mỗi path. Message `error` trên mọi
    socket của path vẫn tính.
  - **(Lần sửa 3) `tab_unmounted_socket_rule`** (có trong `checks` của cả 3 JSON): mọi path app KHÁC path `used` phải là
    path `tab_unmounted` của kịch bản (chỉ `/ws/live-stream` ở Đánh vần; Ký từ không có) và thỏa đủ 0C.2 mục 2: ≤ 2 socket;
    mỗi socket `created_t_s < click_t_s` của bước `tab_alphabet` (bước có mặt, `clicked: true`); `closed: true`,
    `closed_t_s` không null và `≤ t_s` của bước `record_clicked`; `n_non_json == 0` và `count_by_type` rỗng hoặc đúng
    `{session_info: 1}` với `first_type == "session_info"`, `protocol_version == 2`; `handshake_status` ∈ {null, 101}.
    Path khác → đỏ. JSON `ws_classification` có `role_by_path` và `tab_unmounted_by_path`.
  - Không request nào tới `POST /api/fingerspelling` (endpoint ảnh cũ).
- Sau khi dừng: cổng 8000 và 3000 rảnh; không còn tiến trình con.
- **Đánh vần** (`a_hau_A_001.mp4`): status `available: true`; WS hand-landmarks nhận `session_info`; ≥ 1
  `POST /sequence` 200; MỌI body gửi đi: `len(landmarks) == len(handedness) == len(timestamps_ms) ≤ 300`, ≥ 3 khung
  không null, không khung nào có 21 điểm trùng hệt, mọi |v| ≤ 10, `timestamps_ms` không giảm, `source_mirrored == false`;
  text `fs-prediction` == `prediction` của response cuối; `fs-confidence` hiển thị đúng `confidence` đó; bấm `fs-add` →
  `POST /compose` 200 và `fs-composed` == `text` của response. Ghi `prediction` và nhãn clip vào JSON dưới khóa
  `info_not_accuracy`. (Lần sửa 2) Lượt ghi: bấm `fs-record`, chờ 1 vòng clip, bấm `fs-stop`; JSON ghi số `hand_frame`.
- **Ký từ mặc định (legacy)** (Lần sửa 2: clip `qipedc_D0120T`): message WS đầu là `session_info` với
  `protocol_version == 2`, `pipeline == "legacy"`; ≥ 30 `frame_result`; 0 message `error`; `live-pipeline` hiện "legacy";
  sau `camera-stop`, danh sách `live-top5` == `top5` của `frame_result` cuối cùng nhận được.
- **Ký từ `VSL_MODEL_TYPE=stgcn_h360`** (Lần sửa 2: clip `qipedc_D0120T`): `pipeline == "harmonized_v1"`; mọi
  `frame_result.prediction is null`; thấy ≥ 1 `frame_result.status == "RECORDING"` và `live-recording` hiện ra ít nhất một
  lần; ≥ 1 `sign_result` hoặc `sign_discarded` trong tối đa 3 vòng lặp clip; nếu có `sign_result`: `live-gloss` == `gloss`
  và `live-top5` == `top5` của nó; 0 message `error`. Nếu 0 sự kiện: DỪNG, báo planner (KHÔNG chỉnh segmenter hay tham số).
- (Lần sửa 2) Độ dài chạy Ký từ: ≥ 1 vòng clip, dừng sớm khi đủ điều kiện kịch bản, tối đa 3 vòng; JSON ghi `ran_loops`.
- JSON có `generated_by{command, git_commit, code_dirty: false}`; không chứa đường dẫn tuyệt đối, landmark, hay ảnh.
- (Lần sửa 2) Lúc đóng việc: `git diff --name-only <generated_by.git_commit> HEAD -- backend src frontend scripts tests`
  rỗng (không đổi code sau lượt e2e).
- **(Lần sửa 2) AC12-t — test luật phân loại socket** (lớp mới trong `tests/test_frontend_contract.py`, gọi hàm thuần của
  `scripts/e2e_fullstack.py`, không mở trình duyệt/server, không skip). Đầu vào là danh sách socket dạng quan sát của
  `e2e_browser.cjs` (`url`, `protocol`, `count_by_type`, `n_messages`, `closed`, `first_type`). Phải có đủ các ca:
  1. `ws://localhost:3000/?token=AAsU3M2Axbsn` + `vite-hmr` + `{connected: 1}` + 1 socket app `/ws/live-stream` → HMR bị
     loại, cả 3 kiểm URL xanh;
  2. cùng URL nhưng protocol `null` → không phải HMR → `ws_app_urls_via_proxy` đỏ;
  3. `vite-hmr` với URL `ws://localhost:3000/?token=x&a=1`, `ws://localhost:3000/foo?token=x`, `ws://127.0.0.1:3000/?token=x`
     → mỗi ca đỏ;
  4. `ws://localhost:8000/?token=x` + `vite-hmr` → `ws_no_8000_any_socket` đỏ; `ws://localhost:8000/ws/live-stream` → đỏ;
  5. socket HMR có thêm message type khác `connected` (vd. `full-reload`) → đỏ;
  6. 2 socket HMR hợp lệ → `vite_hmr_socket_rule` đỏ;
  7. chỉ có socket HMR, không có socket app → `ws_app_urls_via_proxy` đỏ;
  8. socket app `ws://localhost:3000/api/x` → đỏ;
  9. path có [mồ côi (0 message, closed), socket dùng (first_type `session_info`)] → xanh; 2 mồ côi cùng path → đỏ;
     socket 0 message là socket cuối/duy nhất của path → đỏ; socket 0 message chưa đóng (không phải cuối) → đỏ.
  10. **(Lần sửa 3) Vai trò path + `tab_unmounted_socket_rule`** (đầu vào thêm `scenario`, `steps` dạng `e2e_browser.cjs`, và
      trường `created_t_s`, `closed_t_s`, `handshake_status`, `n_non_json`, `session_info` của socket). Mốc chung cho các ca
      Đánh vần: bước `tab_alphabet` `{clicked: true, click_t_s: T}`, bước `record_clicked` `{t_s: R}`, R > T. Mỗi ca âm chỉ
      đổi MỘT yếu tố so với ca dương 10a và assert đúng kiểm bị đỏ (`tab_unmounted_socket_rule` hoặc `strictmode_orphan_rule`
      như ghi), các kiểm khác của ca đó vẫn xanh:
      - 10a (dương, dạng đúng như lượt thử Đánh vần): `fingerspell`; `/ws/live-stream` 2 socket 0 message, `closed`,
        `handshake_status: null`, tạo trước T, đóng trong (T, R]; `/ws/hand-landmarks` [mồ côi, socket dùng `session_info`]
        → `strictmode_orphan_rule` và `tab_unmounted_socket_rule` đều xanh; `role_by_path` đúng bảng 0C.2.
      - 10b (dương): như 10a nhưng socket thứ hai của `/ws/live-stream` có `{session_info: 1}`, `first_type session_info`,
        `protocol_version 2`, `handshake_status 101` → xanh.
      - 10c (dương): `fingerspell`, không có socket `/ws/live-stream` nào → `tab_unmounted_socket_rule` xanh.
      - Âm, `tab_unmounted_socket_rule` đỏ, mỗi ca một ý: 3 socket `/ws/live-stream`; một socket `closed: false`; một socket
        `closed_t_s` null; `closed_t_s > R`; `created_t_s ≥ T` (socket mở sau khi bấm tab); thiếu bước `tab_alphabet`;
        `clicked: false`; thiếu bước `record_clicked`; `{error: 1}`; `{session_info: 1, frame_result: 1}`;
        `{session_info: 2}`; `{frame_result: 1}`; `n_non_json: 1`; `session_info.protocol_version: 3`;
        `handshake_status: 403`; một path app lạ `ws://localhost:3000/ws/other` ở `fingerspell`; `word` có thêm socket
        `/ws/hand-landmarks` (0 message, closed, đúng thời điểm như 10a).
      - Âm, `strictmode_orphan_rule` đỏ (luật cũ không bị luật mới nuốt): `word` với `/ws/live-stream` gồm 2 socket 0 message
        đã đóng (dạng 10a, tức path `used` không có socket nhận message); `fingerspell` với `/ws/hand-landmarks` gồm 2 socket
        0 message đã đóng; `fingerspell` không có socket `/ws/hand-landmarks` nào (path `used` vắng).
      - Âm, kiểm URL vẫn áp cho path `tab_unmounted`: socket `ws://localhost:8000/ws/live-stream` dạng 10a →
        `ws_no_8000_any_socket` đỏ; `ws://127.0.0.1:3000/ws/live-stream` dạng 10a → `ws_app_urls_via_proxy` đỏ.
      - Hai kịch bản `word` dạng lượt thử (HMR + [mồ côi, socket dùng] trên `/ws/live-stream`, không có path khác) →
        `tab_unmounted_socket_rule` xanh, có mặt trong `checks`.
  Test cũ của lớp (ca 1–9 và các ca âm thêm ở B8b-1) giữ nguyên: `git diff eb379fa HEAD -- tests/test_frontend_contract.py`
  không có dòng `-` (Lần sửa 3).

**AC13 — Quy trình.** Mỗi commit có output `impact`/`detect-changes` (risk thật) trong message; không amend; 3 file ` D`
của người dùng vẫn chưa staged; `docs/plans/06-progress.md` có output thật cho từng bước; `docs/progress_log.md` THÊM 1
dòng (không sửa dòng cũ) nêu: commit, số test trước → sau, 3 JSON e2e ((Lần sửa 2) của B8b, kèm commit; (Lần sửa 3) của
B8c), quyết định §3.8, lệch nguồn AC6 (§0.4), Lần sửa 2 (loại socket HMR theo 0B.1), (Lần sửa 3) luật socket của tab mặc
định bị gỡ (0C.2), các việc theo sau đề xuất. Kết luận vslt-reviewer = APPROVE.

## 6. Rủi ro dữ liệu/ML

**Lệch train–realtime, Cấp 1 (quan trọng nhất).**
- Cùng extractor + tham số + tracker mới mỗi lượt ghi được chứng minh bằng AC4-a/AC5 (PNG, cùng máy). Những gì AC5 KHÔNG
  chứng minh (chỉ ghi nhận ở AC6 hoặc chưa đo):
  - **Nén JPEG** (client gửi JPEG `FS_JPEG_QUALITY`) so với frame giải mã từ mp4 lúc train: AC6 ghi `live_jpeg90_vs_live_png`.
  - **Nền tảng:** landmark train trích trên Kaggle (Linux), live chạy Windows: AC6 ghi `kaggle_npz_vs_local_offline`.
  - **(Lần sửa 1) Đã đo, ghi nhận:** theo JSON AC6 (commit e58d025), cả hai lệch trên đều KHÁC 0: lệch nền tảng làm đổi cờ
    detected ở 1/10 clip và max diff lớn nhất 0.2298; JPEG q90 so với PNG đổi cờ detected ở 2/10 clip, max diff lớn nhất
    0.2403. Cỡ lệch này là tracker bắt/nhả tay khác nhau ở vài frame, không phải sai số làm tròn. Top-1 trùng 10/10 chỉ
    trên 10 clip TRAIN (n nhỏ, dữ liệu model đã học) → không kết luận được về độ bền. Hệ quả: tương đương "train = live"
    chỉ đúng khi cùng nền tảng và cùng định dạng ảnh; mọi số độ chính xác Cấp 1 trên webcam về sau phải nêu điều này.
  - **Tốc độ khung:** train hauuto ≈ 23.6 fps, mọi frame; live phụ thuộc webcam và `FS_MAX_IN_FLIGHT`. Với
    `resample: "frame_index"`, ít frame hơn → lấy mẫu thời gian khác. UI hiện fps hiệu dụng và `client_skipped`; chưa đo
    ảnh hưởng lên nhãn.
  - **Cắt ký hiệu thủ công:** người dùng bấm Ghi/Dừng nên đầu/cuối có thể chứa đoạn đưa tay lên/hạ tay, khác cách cắt clip
    train (chưa kiểm chứng clip hauuto được cắt thế nào). Không thêm luật cắt tự động khi chưa có dữ liệu webcam (Bước 5).
  - **Độ phân giải:** webcam có thể trả khác 640×480; tỉ lệ khung được bù qua `frame_width/height` (kế hoạch 03), nhưng
    độ nhạy MediaPipe theo độ phân giải chưa đo. UI hiện độ phân giải.
- Lật gương: frame không lật ở cả hai phía, `source_mirrored: false`; giữ đúng bất biến 4 của skill.

**Lệch train–realtime, Cấp 2.** Không đổi gì ở đường live (kế hoạch 04 giữ nguyên). Các thí nghiệm còn thiếu của review 04
mục 13 (JPEG q0.75, rơi frame thật, nhiều ký hiệu một phiên, webcam người dùng) vẫn thiếu; e2e của việc này KHÔNG phải
đánh giá chất lượng và không được trích như vậy. (Lần sửa 1) Kết quả AC6 cho Cấp 1 gợi ý lệch Linux↔Windows cũng có thể
có ở Cấp 2 (plan 04 chưa so) — ghi vào Giới hạn của GATE.

**Rò rỉ / TEST.** Không train, không chọn model. E2E và AC5 chỉ dùng clip TRAIN (hauuto là dữ liệu train của model Cấp 1;
clip Ký từ lấy từ split TRAIN); KHÔNG chạm clip TEST/VAL (TEST chỉ chạy một lần, để dành cho GATE). (Lần sửa 2) Clip Ký từ
cố định là `qipedc_D0120T` trước khi chạy lại; không đổi clip theo kết quả. (Lần sửa 3) Lần sửa này đổi luật SAU khi đã thấy
một lượt thử đỏ; để không thành "chỉnh tiêu chí theo kết quả": luật mới dựa trên cơ chế đọc từ code (`App.jsx:9`,
`main.jsx:7`, `e2e_browser.cjs:380-388`), siết thêm ở mọi chỗ khác (thời điểm, handshake, path lạ, path `used` vắng), có ca âm
cho từng điều kiện, quyết định trước lượt chính thức, và lượt chính thức chạy mỗi kịch bản đúng 1 lần (không chọn lượt).

**Cỡ mẫu.** AC5 10 clip là kiểm tương đương CODE (tất định), không phải tỉ lệ. AC6 10 clip chỉ là ghi nhận, không suy ra
tỉ lệ lệch cho toàn bộ dữ liệu. E2E 1 clip/kịch bản chỉ chứng minh "chạy được". `prediction` trong JSON e2e ghi dưới khóa
`info_not_accuracy`; không suy ra độ chính xác từ đó. (Lần sửa 2) Webcam giả là Y4M chuyển từ mp4 (không bằng hệt frame cv2)
và lặp từ lúc mở trang (pha ghi không kiểm soát) — thêm lý do không đọc `prediction` như độ chính xác. (Lần sửa 3) Kiểm thời
điểm socket dựa trên 1 lượt/kịch bản và phụ thuộc tốc độ máy; khoảng cách giữa bấm tab và `record_clicked` chưa đo có kiểm
soát — nếu đỏ vì thời điểm thì dừng báo planner, không nới mốc.

**Nguồn gốc / giấy phép.** hauuto: giấy phép unknown, chỉ dùng nội bộ (`docs/data_registry.md` 1b); mã người ký trong id
clip giữ nguyên theo quyết định (a) 2026-09-28; y4m/video/frame KHÔNG vào git; JSON không chứa landmark. QIPEDC video
chỉ đọc.

**Bảo mật.** Origin check chỉ chặn trang web khác origin trong trình duyệt, không chặn client tự viết; bảo vệ chính là bind
127.0.0.1. Endpoint mới mở thêm bề mặt: mỗi kết nối giữ 1 graph MediaPipe và xử lý tuần tự; chưa có giới hạn số kết nối
(giống `/ws/live-stream` hiện tại) — chấp nhận vì chỉ nghe cục bộ; ghi vào `docs/phase12_api.md` mục Giới hạn nếu coder
thấy cần. `VSL_CORS_ORIGINS` sai → backend không khởi động (fail-fast, không lặng lẽ mở rộng). (Lần sửa 2) Socket HMR của
Vite dev chỉ tồn tại khi chạy dev server (bind localhost, `strictPort`); không có trong bản build. (Lần sửa 3) Ghi nhận cho
backlog (không làm ở đây): mở trang ở tab mặc định luôn mở một phiên `/ws/live-stream` (nạp model Ký từ phía server) kể cả khi
người dùng chỉ định dùng Đánh vần — thuộc Việc 6 (nút chọn chế độ).

**Trung thực UI (DoD 6).** Mọi chữ/từ/câu hiển thị lấy từ response server; khi model không sẵn sàng thì khóa chức năng và
nói rõ; không còn frame giả lập; `confidence` ghi là độ tin cậy của model.

## 7. Điểm dừng

**Không có điểm dừng CẦN NGƯỜI DÙNG trước khi code** (Lần sửa 1, Lần sửa 2 và Lần sửa 3 không đổi điều này: không đổi
model mặc định, không cần dữ liệu người dùng, không xóa file, không đụng thay đổi chưa commit, không có hành động không
hoàn tác; Lần sửa 3 không chạm `App.jsx`/`main.jsx`). Lý do:
- CORS/Origin/bind đã có quyết định (2026-09-28): chỉ origin dev, không `*` kèm credentials.
- Model mặc định KHÔNG đổi; `VSL_MODEL_TYPE=stgcn_h360` chỉ đặt trong môi trường của tiến trình e2e/smoke.
- Không cần dữ liệu mới từ người dùng (dùng video cục bộ đã có; webcam thật là Bước 5).
- Không đụng thay đổi chưa commit của người dùng; không xóa file (`RealtimeStream.jsx` giữ lại, hỏi sau); không có hành
  động không hoàn tác được; không cài gói; không Kaggle.

**Điểm dừng có điều kiện trong lúc làm (coder DỪNG, báo planner/orchestrator; KHÔNG tự nới tiêu chí):**
1. AC5-a không bằng hệt (landmark live ≠ `_extract_one` trên cùng máy) → báo planner. (B3: không kích hoạt.)
2. AC12 kịch bản `stgcn_h360` có 0 `sign_result`/`sign_discarded` → báo planner (không chỉnh segmenter/tham số).
3. Một test đã có bị vỡ do CORS/Origin/bind hoặc endpoint mới → báo planner (không sửa test cũ).
4. Cần cài gói npm/pip, cần tải trình duyệt/model từ mạng, hoặc Edge không có ở máy → báo orchestrator (hỏi người dùng).
5. Cần xóa file, hoặc đổi policy hệ thống (ExecutionPolicy toàn máy) để chạy `start_fullstack.ps1` → hỏi người dùng.
6. Phát hiện vấn đề dữ liệu mới (ví dụ `manifest.csv` có nhiều `mediapipe_version`, video hauuto không khớp npz) → báo
   planner (điểm dừng "vấn đề dữ liệu mới" của autopilot mục 5). (Lần sửa 1: lệch Kaggle↔cục bộ ở §0.4 đã được đánh giá,
   KHÔNG kích hoạt điểm này.)
7. (Lần sửa 1) Sau B6 guard AC8 vẫn đỏ mà không sửa được bằng code → báo planner (không sửa guard).
8. (Lần sửa 2) Ở B8b, bất kỳ kiểm AC12 nào đỏ ở lượt chạy lại — gồm luật HMR gặp message type khác `connected` hoặc > 1
   socket HMR, hay luật mồ côi gặp > 1 mồ côi/path — → báo planner; KHÔNG sửa luật, KHÔNG tắt HMR, KHÔNG đổi clip.
   (Lần sửa 3: đã kích hoạt ở B8b-3 → xử lý ở 0C; áp tiếp cho B8c.)
9. (Lần sửa 2) Khi đánh giá AC1 theo 0B.3, có commit first-parent trong `P6..HEAD` không thuộc `C06` và không thuộc nhóm
   (i)–(iv), hoặc thuộc nhóm nhưng chạm file ngoài tập của nhóm → báo planner.
10. (Lần sửa 3) Ở B8c: (a) một test cũ của `TestE2eSocketRules` không giữ nguyên được; (b) cần đổi luồng thao tác của
    `e2e_browser.cjs` (ngoài ghi 3 trường thời gian) hoặc chạm `App.jsx`/`main.jsx`; (c) bất kỳ kiểm AC12 nào đỏ ở lượt
    chính thức — kể cả `tab_unmounted_socket_rule` đỏ vì thời điểm (`closed_t_s > record_clicked`), số socket > 2, message
    khác `session_info`, hay path lạ → báo planner; KHÔNG sửa luật, KHÔNG nới mốc thời gian, KHÔNG chạy lại để lấy lượt xanh.
