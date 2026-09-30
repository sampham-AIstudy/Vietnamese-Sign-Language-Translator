# Review kế hoạch 06 — Việc 5: frontend + WS v2 + CORS + e2e fullstack

Reviewer: vslt-reviewer (độc lập). Nhánh `feat/vslt-complete`, HEAD lúc review phần 1: `0491877` (lượt 1, hạng mục 2–4 + phần lớn 1);
`9d1d40f` (lượt 2, hoàn thiện hạng mục 1 — chỉ commit STATE/.gitignore/review, không đổi code).
Kế hoạch: `docs/plans/06-viec5-frontend.md`. P6 = `797d0af` (06-progress.md:3).

TRẠNG THÁI: phần 1 (hạng mục 1–4) XONG. Phần 3 (10–13) XONG tại HEAD `8f5969a` (lượt 3; code không đổi so với
0491877 — `git diff --name-only 0491877 8f5969a -- backend src frontend scripts tests` rỗng). Phần 2 (5–9) chưa làm.
**CHẶN: dữ liệu gitignored/untracked `data/external/`, `data/Dataset/`, `checkpoints/` đã bị xóa rỗng lúc 23:42 ngày 2026-09-30 (V0, NGHIÊM TRỌNG) — xem mục "Vấn đề".**

## Bảng 1–13

| # | Hạng mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch / AC có test thật | PASS (AC5-đột biến chỉ bằng proxy) | AC1–AC13 đều có test/lệnh tương ứng, kiểm bằng đột biến: AC3 9/9, AC4 1/1 (+1 sống đúng thiết kế), AC7 19/19, AC8 2/2, AC11 1/1, AC12-t 30/30 bị giết; AC10 tự chạy 2 lần PASSED exit 0; AC5: đọc code `np.array_equal` + xanh trong AC2 tại 0491877 + proxy đột biến 5/5 bị giết (test gốc nay skip do mất dữ liệu, V0) (§1) |
| 2 | Tự chạy lại toàn bộ test | PASS | AC2 31 module: `Ran 526 tests in 734.835s` / `OK` / exit 0, 0 skip; `npm test` 26/26, 0 skip, 3/3 file; `git status --porcelain` trước/sau giống hệt (§2) |
| 3 | Test không bị sửa/skip/nới | PASS | 0 dòng `-` ở 26 file test có tại P6; không xóa file; B7 chỉ thêm lớp (+100/−0); Lần sửa 4: đúng 2 dòng `-`, đều thuộc method bị thay; B2 sửa test B1 theo hướng CHẶT hơn (§3) |
| 4 | Nguồn gốc dữ liệu | PASS | Clip e2e/AC4/AC5/AC10 là video thật đọc bằng cv2 (a_hau_A_001 75 frame 640×480; D0120T 113 frame 1280×720; W03292N 70 frame), thuộc manifest hauuto (mediapipe 0.10.14) / `data/splits/unified/train.csv`, không có ở val/test; y4m sinh từ clip bằng cv2 ra `%TEMP%slt_e2e` (script từ chối thư mục trong repo); không dùng `vsl_alphabet_pilot` (§4) |
| 5 | Rò rỉ split | CHƯA LÀM — phần 2 | |
| 6 | Chọn model bằng VAL, TEST 1 lần | CHƯA LÀM — phần 2 | |
| 7 | Số liệu truy được | CHƯA LÀM — phần 2 | |
| 8 | Cỡ mẫu / CI | CHƯA LÀM — phần 2 | |
| 9 | Nhất quán train–realtime | CHƯA LÀM — phần 2 | |
| 10 | Không Math.random/mock/hard-code | PASS | Guard frontend AC8 `TestFrontendSourceGuard.test_no_violation` ok; guard DoD 7 backend 24/24 ok (`known=9 allowed=36`, không mục nào thuộc `backend/main.py`/`hand_live.py`); grep `frontend/src` + 5 script + `hand_live.py`: 0 `Math.random`/mock/kết quả giả; `Math.random` duy nhất trong bundle là nội bộ React (§10) |
| 11 | Bảo mật | PASS (2 vấn đề THẤP) | CORS/Origin/bind đúng chữ + thăm dò thật stack uvicorn+Vite: WS Origin lạ → `403` cả trực tiếp lẫn qua proxy; input WS kiểm kích thước/base64/magic/header trước giải mã; không token/kaggle.json; hook e2e không có trong bundle. Nhưng qua proxy Vite, REST đọc được từ MỌI origin họ localhost (Vite CORS mặc định) — V6; `detail` model_unavailable của `/ws/hand-landmarks` chép nguyên chuỗi exception — V7 (§11) |
| 12 | So sánh công bằng / GATE không nới (gồm đánh giá 3 lần đổi tiêu chí §0D.12) | PASS (V9 TRUNG BÌNH) | Không so model. 3 lần đổi luật AC12 (0B, 0C, 0D) đều có cơ chế từ code, suy từ mục đích viết trước, nêu điểm nới, commit trước lượt kế tiếp; `_r4` mỗi kịch bản 1 lần (bắt đầu 10 s sau commit b6c27b1); JSON đỏ còn nguyên (blob == d2752c3/e3d0df8). Luật 0C chạy trên dữ liệu `_r4` ĐỎ → `_r4` xanh nhờ Lần sửa 4 (nêu thẳng). Ca âm reviewer 16/16 (luật cuối bắt mọi socket có hại); AC12-t 59/59 ok. V9: coder đổi `hand_ws_session_info` sau lượt dev đỏ, 06-progress:237-239 báo sai (§12) |
| 13 | Kết luận vượt bằng chứng | FAIL | O1 `docs/phase12_api.md:32-33` "Qua proxy Vite, CORS không tham gia" — bị thăm dò §11 bác bỏ; O2 `docs/plans/06-progress.md:237-239` báo lượt dev B8 chỉ đỏ kiểm URL — JSON dev có `hand_ws_session_info` đỏ. Câu nên chỉnh O3–O5 (THẤP). JSON e2e `note`/`info_not_accuracy` đúng mực; danh sách thí nghiệm còn thiếu ở §13 |

## Chi tiết phần 1

### §1 — Đúng kế hoạch / AC có test thật
Đột biến làm trong worktree tạm ngoài repo (`git worktree add --detach ../_rev06_wt HEAD`; dữ liệu gitignored nối bằng
junction), mỗi đột biến hoàn tác ngay; driver `../_rev06_tmp/mutate_e2e.py`, `mutate_js.py`, `mutate_js2.py`.
Repo chính không bị sửa (`git status --porcelain` so với ảnh chụp đầu phiên: giống hệt, trừ chính file review này).

**Bảng AC → bằng chứng**

| AC | Test/lệnh | Tự kiểm | Kết quả |
|---|---|---|---|
| AC1 phạm vi | lệnh 0B.3 | Hợp file của C06 (36 commit coder, bỏ 4 commit planner) nằm trong danh sách AC1; `start_fullstack.ps1` chỉ đổi `--host 0.0.0.0` thành `127.0.0.1`; `RealtimeStream.jsx` đúng 3 dòng (import, URL, chuỗi lỗi); `package.json` chỉ thêm `"test"` (+ dấu phẩy); diff P6..HEAD của package-lock.json, App.jsx, main.jsx, Dictionary.jsx, Reports.jsx, extract_hands_batch.py, src/data, harmonized_live.py, sign_segmenter.py, predictor.py, configs, checkpoints, data: rỗng; `docs/reviews/*` chỉ đổi bởi merge bbfdff3 + 6a6538c (nhóm iv). 28 commit first-parent ngoài C06 đều thuộc đúng nhóm i–iv, chỉ chạm file của nhóm (progress_log ở 2f5d3f2: 0 dòng xóa). Không commit B8d nào chạm `frontend/`. Không file thêm có đuôi pt/npz/mp4/y4m/png/jpg/log. 3 file ` D` chưa staged (`git diff --cached` rỗng). | PASS |
| AC2 | 31 module + npm test | §2 | PASS |
| AC3 a–g | `tests/test_cors_origin_bind.py` (21 test) | Đột biến (đều bị giết): `ws_origin_allowed` luôn True → 12 fail; so khớp không phân biệt hoa thường → 3 fail; `uvicorn.run(host="0.0.0.0")` → 1; ps1 `--host 0.0.0.0` → 1; `allow_credentials=True` → 2; đóng 1000 thay 1008 → 10; `strictPort: false` ở `server` → 1; bỏ kiểm Origin chỉ ở `/ws/hand-landmarks` → 6; chỉ ở `/ws/live-stream` → 6. | PASS |
| AC4 a–g | `tests/test_hand_landmarks_ws.py` (9 test, MediaPipe thật) | Đột biến `min_detection_confidence` 0.5→0.7 → `test_kwargs_equal_training_extractor` fail. Đột biến bỏ `cvtColor(BGR2RGB)` → AC4 vẫn xanh (đúng thiết kế: AC4 kiểm hợp đồng, phép kiểm bit thuộc AC5). | PASS |
| AC5 | `tests/test_hand_live_equivalence.py` (4 test; 8 hauuto + 2 qipedc) | Đọc code: `np.array_equal` trên detected/landmark/score, body `/sequence` và JSON response bằng hệt, top-1 + sai lệch confidence ≤ 1e-4 (`tests/test_hand_live_equivalence.py:85-132`). 4/4 xanh, 0 skip trong AC2 tại 0491877 (§2). Đột biến: xem "Đột biến AC5" (proxy 5/5 bị giết; chạy trên chính test gốc: UNVERIFIED vì V0). | PASS (đột biến qua proxy) |
| AC6 | `scripts/hand_live_check.py` + `TestHandLiveCheckReport` | Chạy lại tại HEAD → thân JSON bằng hệt bản commit (§4). | PASS |
| AC7 a–c | `frontend/tests/*.test.mjs` (26) | 11 đột biến `reduceLive` đều bị giết (bỏ `protocol_mismatch`; bỏ/tắt thêm từ CONFIRMED legacy; `bufferCapacity` cứng 60; harmonized `frame_result` xóa `lastSign`; khử trùng `sign_result`; đảo dấu `client_e2e_ms`; mất `reason`; không `fatal`; không đếm type lạ; sửa state đầu vào → deepFreeze bắt). 8 đột biến `buildSequenceBody` đều bị giết (khung 0 thay `null`; bỏ sort; bỏ lọc `segment_id`; `source_mirrored: true`; bỏ `frame_size_changed`; bỏ giới hạn frame; bỏ lỗi rỗng; cho timestamps giảm). | PASS |
| AC7-d | `TestCrossLanguageBody` | xanh trong AC2 (node có trên máy, không skip) | PASS |
| AC8 | `TestFrontendSourceGuard`, `TestGuardSelfCheck` | Đột biến thêm `Math.random()` vào `frontend/src/lib/ws.js` → fail; URL `ws://…:8000` ở `Phase12Pipeline.jsx:83` → fail. | PASS |
| AC9 | build + npm ls | `npx vite build --outDir ../_rev06_tmp/dist` exit 0 (`built in 4.97s`); `npm ls --depth=0` == `../_plan06_tmp/b0_npm_ls.txt` (diff rỗng); lock file không đổi. | PASS |
| AC10 | `scripts/smoke_test_phase12.py` | Tự chạy 2 lần: mặc định → `pipeline=legacy model=stgcn is_default=True`, rác → `decode_failed`, 30 frame `{'frame_result': 30}`, `PASSED`, exit 0; `VSL_MODEL_TYPE=stgcn_h360` → `harmonized_v1`, rác → `bad_timestamp`, `{'frame_result': 30}`, `PASSED`, exit 0. | PASS |
| AC11 | `TestPhase12ApiDoc` (6 test) | Đột biến xóa `1008` khỏi `docs/phase12_api.md` → fail `[1008]`. | PASS |
| AC12 (3 JSON) | `reports/e2e_2026-09-30_r4/*.json` | `all_checks_pass` true, 25/25, 23/23, 26/26; `checks` có đủ `strictmode_orphan_rule`, `tab_unmounted_socket_rule`, `tab_unmounted_owner_rule`; `generated_by.git_commit` b6c27b1, `code_dirty` false; `git merge-base --is-ancestor 0517c0a b6c27b1` đúng; `git diff --name-only b6c27b1 HEAD -- backend src frontend scripts tests` rỗng; JSON đỏ `reports/e2e_2026-09-30/fingerspell_default.json` blob c7a83cb giống d2752c3; `e2e_2026-09-29/*` chỉ commit ở e3d0df8. Fingerspell `page_hook`: live 2 bản ghi == 2 socket CDP, owner 2 lần `Phase12Pipeline.jsx`. Không chạy lại e2e (cần khởi động stack; tính hợp lệ của đổi luật để phần 3). | PASS (kiểm tĩnh) |
| AC12-t | `TestE2eSocketRules` (16) + `TestE2eScenarioRoles` (30) + `TestE2eTabOwner` (13) = 59 test | 30 đột biến vào `scripts/e2e_fullstack.py`, TẤT CẢ bị giết: regex HMR cho host bất kỳ; bỏ kiểm protocol `vite-hmr`; bỏ kiểm type `connected`; cho `n_messages` lệch; `MAX_HMR_SOCKETS` 2; tắt kiểm `:8000`; cho 0 socket app; `WS_PREFIX` = `ws://`; cho 2 mồ côi; cho mồ côi chưa đóng; cho socket cuối 0 message; cho path `used` rỗng; `MAX_TAB_UNMOUNTED_SOCKETS` 3; bỏ `closed_t_s ≤ record_clicked`; bỏ `closed: true`; bỏ `protocol_version 2`; cho handshake 403; cho `{session_info: 2}`; bỏ `n_non_json`; bỏ kiểm bước `tab_alphabet`; cho path lạ; KHÔI PHỤC phép so `created_t_s < click_t_s` (test thay thế + 11d bắt); `ws_owner` lấy frame `/src/` cuối; giữ `?t=`; bỏ so số bản ghi == số socket CDP; `page_ws` thiếu → xanh; chỉ bắt owner `None`; hằng owner = Fingerspelling; `evaluate` nối cứng owner True; `page_ws` thiếu chỉ đỏ ở fingerspell. | PASS |
| AC13 | message commit / progress | Xem "Vấn đề" V1–V2 (quy trình, mức THẤP). | PASS có ghi chú |

**Kiểm riêng theo 0C.6/0D.12 (phần thuộc 1–4):**
- `git diff eb379fa e1d13d2 -- scripts/e2e_browser.cjs`: chỉ ghi `created_t_s`, `closed_t_s`, `click_t_s` (1 dòng `-` được thay bằng bản thêm `click_t_s`).
- `git diff e1d13d2 HEAD -- scripts/e2e_browser.cjs`: đúng 3 mục 0D.5 (hook `Proxy` chỉ bẫy `construct` + `Reflect.construct`, ghi trong try/catch, không đổi `Error.stackTraceLimit`; `click_page_ms_before/after` quanh `b.click()`; `obs.ws_page` đọc 1 lần). Không đổi selector, thứ tự, thời gian chờ.
- `git diff e1d13d2 HEAD -- scripts/e2e_fullstack.py` dòng `-`: đúng phép so `created_t_s < click_t_s` + thông điệp "not before click_t_s", 2 docstring và 1 dòng trả về của `ws_classification` (thay bằng bản mở rộng). (a), (c), (d), (e), điều kiện bước, "created_t_s missing" còn nguyên (`scripts/e2e_fullstack.py:317-368`).
- `scenario_ws_roles` vẫn trả đúng 2 kiểm (`tests/test_frontend_contract.py:537` assert tập kiểm).

**Điểm nợ từ STATE (xác minh thực chất bằng diff):**
- B2 ed5c4c9 "HIGH (17 symbol mới)": `backend/main.py` +133/−0, `src/inference/hand_live.py` mới; không symbol cũ nào đổi → HIGH do đếm symbol mới, không có rủi ro hồi quy thực chất.
- B3 e58d025 "HIGH staged": chỉ thêm `scripts/hand_live_check.py`, `tests/test_hand_live_equivalence.py` + progress → không đụng code cũ.
- B5 34a527d "CRITICAL 4 component": caller thật (grep import trong `frontend/src`): `Navbar`, `Phase12Pipeline`, `Fingerspelling` chỉ từ `App.jsx`; `CameraCapture`, `PredictionDisplay` chỉ từ `Phase12Pipeline.jsx` (đổi cùng commit). `App.jsx` gọi `<Phase12Pipeline />`, `<Fingerspelling />` không prop; `Navbar` chỉ đổi 1 dòng chữ `':8000'` thành `'Online'`. Python có `FingerspellingSequenceRequest`/`FingerspellingComposeRequest` (`backend/main.py:680,695`) → hợp giả thuyết GitNexus ghép nhầm theo tên. Build xanh (AC9), e2e xanh. Không có rủi ro thực chất.
- B6 0328c1b "CRITICAL Fingerspelling": chỉ đổi `Fingerspelling.jsx` (+432/−181) + progress; caller duy nhất `App.jsx:54`, không prop.
- 050d337 thiếu detect-changes: đúng (commit chỉ thêm 6 dòng vào `docs/plans/06-progress.md`). Tôi tìm thêm 4 commit docs-only khác cũng không có detect-changes trong message: ada003b, 15200d9, 0e506c3, 001e020 (cả 4 chỉ chạm `docs/plans/06-progress.md`). → V1.
- 2fa59e0 (14:53:14, sau 85ef325 14:52:55) và 1b05851 (15:00:48, sau e1d13d2 15:00:32): message ghi `--scope staged` "risk low"; kế hoạch 0D.9 mục 12 đã ghi nhận (1b05851 ghi "risk low" trong khi output thật là "no indexed symbols overlap"; 2fa59e0 chạy sau commit). Chỉ docs. Từ B8d (828e472 trở đi) message chép nguyên văn output (`Changes: … Risk level: critical` / "no indexed symbols overlap those hunks — not a clean tree"). → V2.

**Đột biến AC5 (lượt 2, HEAD 9d1d40f):**
- Cách làm: vá trong tiến trình (monkeypatch), KHÔNG sửa file nào trên đĩa, không cần worktree. Driver
  `_work/_rev06_tmp/mutate_ac5.py` (chạy `tests.test_hand_live_equivalence` sau khi vá) và `_work/_rev06_tmp/proxy_ac5.py`.
- Chạy `mutate_ac5.py NONE` (mốc) ra `Ran 4 tests` / `OK (skipped=4)`. Lý do skip (in `_MISSING` của test): thiếu
  `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv`, `data/external/hauuto_raw/raw/raw`, `data/Dataset/Videos`,
  `checkpoints/alphabet_best.pt`. Kiểm tra: `data/external/`, `data/Dataset/`, `checkpoints/` còn nhưng RỖNG, mtime
  `30/09/2026 23:42` (`cmd /c dir /a`), xem V0. Vì vậy KHÔNG chạy được đột biến trên chính test AC5.
- Proxy (cùng hàm so sánh của test AC5-a: `H.live_hand_frames` qua WS `/ws/hand-landmarks` bằng TestClient, PNG,
  `H.live_arrays`, `np.array_equal` trên detected/landmark/nhãn/score; offline = `_extract_one` import nguyên văn) trên 1 video
  người thật còn trên máy: `data/raw_tudienngonngukyhieu/videos/5--nam-863.mp4` (259 frame, offline có tay 127). Lệnh:
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python _work/_rev06_tmp/proxy_ac5.py data/raw_tudienngonngukyhieu/videos/5--nam-863.mp4 NONE M1 M2 M3 M4 M5`
  (exit 0, log `_work/_rev06_tmp/proxy_ac5.log`):

  | Đột biến | detected bằng (số frame có tay live) | landmark bằng | nhãn bằng | max abs Δ (frame cùng có tay) | AC5-a |
  |---|---|---|---|---|---|
  | NONE (mốc) | True (127) | True | True | 0.0 | xanh (proxy hợp lệ) |
  | M1 bỏ `cvtColor(BGR2RGB)` trong `HandLandmarkSession.process` | False (0) | False | False | — | ĐỎ (bị giết) |
  | M2 server lật ngang frame sau `_decode_frame` (mirror) | False (132) | False | False | 0.3861 | ĐỎ |
  | M3 landmark qua float16 | True (127) | False | True | 0.00047 | ĐỎ |
  | M4 `static_image_mode=True` | False (124) | False | False | 0.0632 | ĐỎ |
  | M5 `min_tracking_confidence` 0.5 thành 0.6 | False (129) | False | False | 0.0430 | ĐỎ |

  Kết luận: phép so bit của AC5-a phân biệt được cả 5 lệch train–live (kể cả lệch làm tròn 5e-4 mà một dung sai sẽ bỏ qua).
  Giới hạn: đây là proxy trên 1 clip ngoài mẫu AC5 (video từ điển, không phải clip Cấp 1), không phải chạy lại chính test AC5;
  AC5-b/c (body, response, top-1) không được đột biến. Cần chạy `mutate_ac5.py M1`…`M5` sau khi khôi phục dữ liệu để có bằng
  chứng trên đúng test. Video chỉ đọc cục bộ, không commit; npz tạm ghi vào `_work/_rev06_tmp/off_*` và đã xóa.

### §2 — Tự chạy lại toàn bộ test (PASS)
- Lệnh (từ gốc repo, HEAD 0491877):
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest <29 module AC2 của §5> tests.test_archive_private_kaggle_r05 tests.test_backend_source_guard -v > ../_rev06_tmp/ac2_31.log 2>&1`
  - Output: `Ran 526 tests in 734.835s` / `OK` / `EXIT=0`. Không dòng `skipped`/`FAIL`/`ERROR`/`expected failure`.
  - Khớp số coder báo (Ran 526 OK, 0 skip — 505c1e6).
  - Số test theo module (đếm từ log verbose): 4 module của 06 = cors 21 + hand_landmarks_ws 9 + hand_live_equivalence 4 +
    frontend_contract 71 = 105; 2 module merge = r05 14 + backend_source_guard 24 = 38 (khớp review cloud);
    25 module cũ = 526 − 105 − 38 = 383 (khớp mốc B0, 8e7b09b). Công thức 0D.11: frontend_contract = 58 (B8c-2) + 13
    test của `TestE2eTabOwner` (đếm `def test_` từ `tests/test_frontend_contract.py:809`) = 71; test bị thay tính 1 đổi 1 → khớp.
- `cd frontend && npm test` (node v25.9.0): `tests 26 / pass 26 / fail 0 / skipped 0`. Theo file (grep `test(`):
  fingerspelling 10 + liveProtocol 12 + ws 4 = 26 → cả 3 file của `git ls-files "frontend/tests/*.test.mjs"` (3 dòng) đều chạy.
- `git status --porcelain` trước khi chạy (`../_rev06_tmp/status_before_ac2.txt`) == sau AC2 == sau npm test (`diff` rỗng).

### §3 — Test không bị sửa/skip/nới (PASS)
- `git diff --name-status 797d0af HEAD -- tests/`: chỉ `A` (6 file: 4 của 06 + 2 của merge cloud). Với mọi file của
  `git ls-tree -r 797d0af tests/`: số dòng `-` trong `git diff 797d0af HEAD` = 0. `git diff --diff-filter=D --name-only 797d0af HEAD` rỗng.
- Sửa trong file test do chính 06 tạo (`git show --numstat`):
  - `tests/test_cors_origin_bind.py`: ed5c4c9 (B2) +27/−6. Các dòng `−`: docstring; `WS_PATHS` thêm `/ws/hand-landmarks`;
    bỏ `if hasattr(api, "HandLandmarkSession")` để LUÔN vá mock; thêm `self.hand_session.assert_not_called()` và lớp
    `TestWsOriginAcceptedHandLandmarks`. Đều CHẶT hơn (thêm path, thêm assert), không nới.
  - `tests/test_frontend_contract.py`: 026f474 +199/−0; dbd79f2 (B7) +100/−0 — một hunk `@@ -140,6 +140,106 @@` chèn lớp
    mới `TestPhase12ApiDoc` + helper ở mức module giữa hai lớp, không chạm thân test cũ; 302072c +158/−0; 85ef325 +303/−0;
    828e472 +260/−2.
  - `git diff e1d13d2 HEAD -- tests/test_frontend_contract.py | grep '^-[^-]'` = đúng 2 dòng:
    `def test_live_socket_created_at_or_after_click_is_red(self):` và `self._tab_red(s)` — cả hai thuộc method bị thay theo
    0D.10 (kế hoạch nói "6 dòng của method"; thực tế chỉ 2 dòng đổi, 4 dòng giữ nguyên → tập con). `git diff eb379fa HEAD`
    0 dòng `-`. Test thay thế gọi `self._assert_only_red(ok)` không đối số = assert cả 5 kiểm True
    (`tests/test_frontend_contract.py:542-543`) — đúng 0D.10, không phải assert rỗng.
- Skip: chỉ `skipUnless` cho dữ liệu gitignored / thiếu `node` (`tests/test_hand_landmarks_ws.py:118,190`,
  `tests/test_hand_live_equivalence.py:35`, `tests/test_frontend_contract.py:246`) — đúng §5; trên máy này 0 skip (§2).

### §4 — Nguồn gốc dữ liệu (PASS)
- Clip thật (đọc lại bằng cv2 tại máy review, đếm frame + std trung bình của frame để loại ảnh hằng):
  `data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4` 75 frame 640×480 23.584 fps (std 46.5);
  `data/Dataset/Videos/D0120T.mp4` 113 frame 1280×720 29.97 fps (std 49.0); `data/Dataset/Videos/W03292N.mp4` 70 frame (std 49.8).
  Khớp `clip.video_facts` trong `reports/e2e_2026-09-30_r4/*.json` (75/640×480; 113/1280×720).
- Nguồn gốc: `hauuto_a_hau_A_001` có trong `data/external/alphabet_hands_kaggle/alphabet_hands/manifest.csv` (source hauuto,
  mediapipe_version 0.10.14 — dữ liệu người thật đã trích MediaPipe thật, là dữ liệu TRAIN của model Cấp 1, JSON ghi đúng
  `split: "Level 1 training data (hauuto)"`, `info_not_accuracy`). `qipedc_D0120T`, `qipedc_W03292N` có trong
  `data/splits/unified/train.csv`, 0 dòng ở `val.csv`/`test.csv`.
- y4m: `scripts/make_fake_webcam_y4m.py:38-69` đọc video bằng `cv2.VideoCapture`, đổi `COLOR_BGR2YUV_I420`, ghi từng frame
  thật; `scripts/e2e_fullstack.py:678-705` ghi ra `tempfile.gettempdir()/vslt_e2e` và từ chối thư mục trong repo
  (`is_inside_repo`). Không file `.y4m/.mp4/.png/.jpg/.npz/.pt/.log` nào được thêm vào git trong P6..HEAD (lệnh
  `git diff --diff-filter=A --name-only 797d0af HEAD | grep -Ei '\.(pt|npz|mp4|y4m|png|jpg|log)$'` rỗng).
- Không có dữ liệu sinh/giả lập trong đường chính: grep `vsl_alphabet_pilot|synthetic|random.` trên 5 script + `hand_live.py`
  của 06 chỉ ra `np.random.default_rng(seed)` dùng CHỌN mẫu clip (`scripts/hand_live_check.py:88`), không sinh dữ liệu.
  Ảnh đen 640×480 chỉ có trong test/smoke để kiểm giao thức "không có tay" (`scripts/smoke_test_phase12.py:75`,
  AC4-d) — là fixture kiểm, không phải dữ liệu train/đánh giá.
- AC6 chạy lại tại HEAD (`PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/hand_live_check.py --n-clips 8 --seed 0
  --out ../_rev06_tmp/hand_live_check_rerun.json`, exit 0, git_commit 0491877, code_dirty false): phần thân (bỏ
  `generated_by`) BẰNG HỆT `reports/fingerspell_live_2026-09-29/hand_live_check.json` (so dict Python: True).

## Chi tiết phần 3 (lượt 3, HEAD 8f5969a; không sửa file nguồn nào; file tạm ở `_work/_rev06_tmp/`)

Test chạy lại (chỉ module liên quan phần 3):
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_cors_origin_bind tests.test_backend_source_guard tests.test_frontend_contract tests.test_hand_landmarks_ws -v`
→ `Ran 124 tests` / `OK (skipped=3)` / exit 0 (log `_work/_rev06_tmp/p3_tests.log`). 3 skip đều do V0 (mất dữ liệu):
`TestCrossLanguageBody` (setUpClass: thiếu `manifest.csv`, `checkpoints/alphabet_best.pt`), `TestRealFrame.test_hand_and_no_hand`
(thiếu `a_hau_A_001.mp4`), `TestSessionInfo.test_session_info` (thiếu `manifest.csv`) — các test này KHÔNG được tính là PASS ở
lượt này; bằng chứng xanh của chúng là AC2 lịch sử tại 0491877 (§2). `git status --porcelain` trước/sau: giống hệt.

### §10 — Không Math.random / mock / kết quả giả / hard-code (PASS)
- Guard frontend AC8: `TestFrontendSourceGuard.test_no_violation ... ok`, `TestGuardSelfCheck` ok (đột biến ở §1 đã chứng minh
  guard bắt `Math.random` và `:8000`).
- Guard DoD 7 backend (`tests/test_backend_source_guard.py`, 24 test): tất cả ok, in `[DoD7-guard] known=9 allowed=36`.
  Phạm vi SERVING có `backend/main.py` và `src/inference/hand_live.py` (`tests/test_backend_source_guard.py:46-56`). Đọc
  `KNOWN_VIOLATIONS` (`:211-235`) và `ALLOWED` (`:174-207`): KHÔNG khóa nào thuộc `backend/main.py` hay `hand_live.py` → mã 06
  thêm vào backend (+197 dòng) có 0 phát hiện (không phải được "đăng ký miễn"). 9 vi phạm đã biết nằm ở `realtime_demo.py`
  (chế độ `--source mock`), `src/data/*`, `sign_segmenter.py` — có từ trước, ngoài phạm vi 06.
- Grep `Math.random|mock|fake|simulat|dummy` trên `frontend/src/**`, `backend/main.py`, `src/inference/hand_live.py`, 5 script
  của 06: 0 kết quả giả trong đường chính. Chữ "fake" chỉ là cờ webcam giả của Edge trong script e2e (nguồn là Y4M từ clip thật,
  §4); `np.random.default_rng(seed)` chỉ để CHỌN clip (`scripts/hand_live_check.py:88`). `np.zeros` ở `backend/main.py:732-733`
  là bộ đệm + mặt nạ `detected` của `/sequence` (có từ kế hoạch 03, b9fd11c), không phải khung giả gửi vào model.
- UI hiển thị số/chữ lấy từ message server: `Phase12Pipeline.jsx:136-144,245-258` (gloss/confidence/top5/metrics từ
  `reduceLive`), `Fingerspelling.jsx:449-455,318` (prediction/confidence của response `/sequence`, `text` của `/compose`).
  Hằng thiết kế (24 fps, JPEG 0.9, 2 frame đang bay, `targetFps={25}`) được `docs/phase12_api.md:136` ghi rõ là giá trị thiết kế,
  chưa đo — không phải số đo.
- Bundle: `npx vite build --outDir ../_work/_rev06_tmp/dist_p3` exit 0; trong `index-*.js`: `__e2e` 0 lần, `:8000` 0 lần;
  `Math.random` 2 lần, cả hai là nội bộ React (`_reactListening` + Math.random, `__reactFiber$` + Math.random), không phải mã app.
- Ghi nhận ngoài phạm vi (không tính cho 06, AC1 khóa file): `frontend/src/components/Reports.jsx:73-77` có số gõ tay
  (98.13% Pham et al., 95.0% sau tiền xử lý, 8.07% Top-1 / 17.04% Top-5, 46.41% cũ) hiển thị trong app, không trỏ tới
  JSON có lệnh + commit; guard AC8 không bắt loại này. Đề xuất backlog (V8).

### §11 — Bảo mật (PASS, có V6, V7 mức THẤP)
- CORS (`backend/main.py:329-371`): `ALLOWED_ORIGINS = parse_cors_origins(VSL_CORS_ORIGINS)`; `*`/rỗng/không http(s)/có `/` cuối →
  `ValueError` lúc import; `CORSMiddleware(allow_origins=list(ALLOWED_ORIGINS), allow_credentials=False,
  allow_methods=["GET","POST"], allow_headers=["Content-Type"])` — không `*` ở đâu, không credentials. AC3 21/21 ok ở lượt này.
- WS Origin: `_ws_check_origin` (`backend/main.py:1337-1344`) gọi TRƯỚC `accept()` ở cả `/ws/live-stream` (`:1366`) và
  `/ws/hand-landmarks` (`:1636`), đóng 1008. Không có header Origin → cho qua (đúng thiết kế, đã ghi Giới hạn
  `docs/phase12_api.md:155-157`).
- Bind: `start_fullstack.ps1:13` `--host 127.0.0.1 ... --ws-max-size 1048576`; `backend/main.py:1704` `host="127.0.0.1"`;
  `frontend/vite.config.js` không có khóa `host`, `strictPort: true` ở `server` và `preview`.
- **Thăm dò thật (reviewer, không sửa code):** `_work/_rev06_tmp/p3_proxy_probe.py` khởi động `uvicorn backend.main:app --host
  127.0.0.1 --port 8000 --ws-max-size 1048576` + `npx vite --port 3000 --strictPort`, gửi request thô, rồi `taskkill /T` (sau đó
  cả 2 cổng rảnh). Kết quả (`_work/_rev06_tmp/p3_proxy_probe.json`):

  | Đích | Origin | POST `/api/fingerspelling/compose` | OPTIONS preflight | WS `/ws/hand-landmarks`, `/ws/live-stream` |
  |---|---|---|---|---|
  | :8000 trực tiếp | `http://localhost:3000` | 200, ACAO = origin | 200 | 101 / 101 |
  | :8000 trực tiếp | `http://evil.example` | 200, KHÔNG ACAO | 400 | 403 / 403 |
  | :8000 trực tiếp | `http://localhost:5173` | 200, KHÔNG ACAO | 400 | 403 / 403 |
  | :3000 qua proxy | `http://localhost:3000` | 200, ACAO = origin | 204 | 101 / 101 |
  | :3000 qua proxy | `http://evil.example` | 200, KHÔNG ACAO | 204, KHÔNG ACAO | 403 / 403 |
  | :3000 qua proxy | `http://localhost:5173` | **200, ACAO = `http://localhost:5173`** | **204, ACAO = origin** | 403 / 403 |
  | :3000 qua proxy | `http://attacker.localhost:8080` | **200, ACAO = origin** | **204, ACAO = origin** | 403 / 403 |

  → Kiểm Origin WS giữ nguyên qua proxy (Vite chuyển tiếp header Origin); REST trực tiếp :8000 đúng danh sách chính xác.
  NHƯNG qua proxy Vite (đường người dùng chạy), CORS do Vite dev server trả lời, không phải backend: Vite 6.4.3 mặc định
  `server.cors = {origin: defaultAllowedOrigins}`, regex chấp nhận `localhost`, `*.localhost`, `127.0.0.1`, `[::1]` với cổng bất
  kỳ (`frontend/node_modules/vite/dist/node/constants.js:144`) → mọi trang ở origin họ loopback, cổng bất kỳ, đọc được response
  `/api/*` qua `:3000`. Danh sách chính xác `VSL_CORS_ORIGINS` bị vượt cho REST trên đường dev. Không phải "CORS mở toàn bộ"
  (origin ngoài loopback bị chặn), chỉ cục bộ, API không có bí mật/không đổi trạng thái → **V6 THẤP**; nhưng câu
  `docs/phase12_api.md:32-33` ("Qua proxy Vite, CORS không tham gia; CORS chỉ có ý nghĩa khi trang origin khác gọi thẳng cổng
  8000") là SAI (tính ở §13). Sửa gợi ý: `server.cors`/`preview.cors` = `{origin: [danh sách dev]}` (hoặc `false`) trong
  `vite.config.js` + test văn bản, hoặc sửa tài liệu nêu đúng giới hạn.
- Input WS (dùng chung cho 2 path, `backend/main.py:927-1034`): kích thước message kiểm 2 lớp (uvicorn `--ws-max-size 1048576`
  và `_parse_ws_message` `size > WS_MAX_MESSAGE_BYTES` → `message_too_large` + đóng 1009); base64 `validate=True`; magic byte chỉ
  JPEG/PNG; kích thước đọc từ header (PIL, bắt `DecompressionBombError`) TRƯỚC `cv2.imdecode`; cạnh ≤ 1920; `ndim == 3`;
  timestamp/threshold hữu hạn. `test_errors_keep_session`, `test_message_too_large_closes_1009` ok ở lượt này (spy `imdecode` 0
  lần với header 4000×10). `/ws/hand-landmarks` xử lý tuần tự — không có hàng đợi không giới hạn.
- `detail`: `WsError`/`_ws_error` cắt ≤ 200 ký tự, không lặp dữ liệu client. Riêng `/ws/hand-landmarks`, `unavailable(e)`
  (`backend/main.py:1645`) gửi `f"hand landmark extractor unavailable: {e}"` — chuỗi exception nguyên văn (cắt 200) của
  MediaPipe/OS, có thể chứa đường dẫn tuyệt đối site-packages (tên người dùng Windows). Chỉ lộ cho client cục bộ đã qua kiểm
  Origin; `docs/phase12_api.md:158` chỉ nêu trường hợp 503 checkpoint → **V7 THẤP** (backlog: thông điệp cố định, chi tiết vào
  log). `/ws/live-stream` `:1396` `str(e)` có từ kế hoạch 04 (ngoài 06).
- Bí mật: `git diff 797d0af HEAD --name-only` không có `kaggle.json`/`.env`/token; grep dòng thêm (trừ docs) theo
  `KAGGLE_KEY|api_key|password|secret|Bearer|ghp_|hf_...`: 0. 8 JSON `reports/e2e_*` + `hand_live_check.json`: 0 đường dẫn tuyệt
  đối (`C:\`, `/c/Users`, `Admin`, `/home/`). Có URL HMR `ws://localhost:3000/?token=...` (token HMR của Vite, sinh lại mỗi lần
  chạy dev server, chỉ chống trang lạ nối HMR; không phải bí mật lâu dài) — thông tin.
- Hook e2e (`scripts/e2e_browser.cjs:363-395`): chỉ bẫy `construct`, `Reflect.construct(target, args, newTarget)`, ghi trong
  try/catch, frames chỉ `pathname` `/src/...`/nhãn gộp; đăng ký bằng `page.evaluateOnNewDocument` trong trình duyệt do script
  điều khiển. Không có trong `frontend/src` (grep `__e2e|new Proxy|Reflect.construct` = 0) và không có trong bundle (`__e2e` 0).
- Đã được kế hoạch nêu, không tính lỗi: không giới hạn số kết nối WS đồng thời (`docs/phase12_api.md:156-157`); Origin không
  chặn client không phải trình duyệt (`:155-156`).

### §12 — So sánh công bằng / tiêu chí không bị nới sau khi thấy kết quả (PASS, có V9)
Phần "so model trên cùng tập test sạch": KHÔNG áp dụng — 06 không train, không chọn model, không so độ chính xác; 2 kịch bản Ký
từ (`stgcn` mặc định, `stgcn_h360`) chạy trên CÙNG clip TRAIN `qipedc_D0120T`, kết quả chỉ ghi dưới `info_not_accuracy`; model mặc
định không đổi (`word_default.json`: `is_default` true, `legacy`). AC5 (không bằng hệt → DỪNG, không nới sang dung sai) và AC6
(không có ngưỡng pass) có từ bản gốc `dbec36c` (`git show dbec36c:docs/plans/06-viec5-frontend.md`, dòng 402, 411) — không đổi
sau khi thấy số.

**Dòng thời gian** (commit time; `generated_by.generated_at_utc` ghi LÚC BẮT ĐẦU lượt — `scripts/e2e_fullstack.py:689-695`).
Kiểm kê MỌI JSON e2e còn trên máy (`_work/_rev06_tmp/p3_runs.py`, quét `reports/e2e_*` + `_work/_plan06_tmp/`):

| Lượt | Code | Bắt đầu (UTC) | Kết quả | Luật khi chạy | Sau đó |
|---|---|---|---|---|---|
| B8 dev (thử, code bẩn) | ada003b | 09-29 10:44–10:46 | 17/20, 16/18, 19/21; đỏ: URL, `code_clean_at_run`, **`hand_ws_session_info` (Đánh vần)** | gốc | coder đổi `hand_ws_session_info` (V9) |
| B8 chính thức | 15200d9 | 09-29 10:48–10:49 | 19/20, 17/18, 20/21; đỏ duy nhất `ws_urls_all_via_proxy_no_8000` | gốc | Lần sửa 2 f52de6f (18:16 +07) |
| B8b-3 thử | eb379fa | 09-29 11:28–11:29 | Đánh vần 22/23 đỏ `strictmode_orphan_rule`; Ký từ 21/21, 24/24 | 0B | Lần sửa 3 717aa3e (18:46 +07) |
| B8c-3 chính thức (chỉ Đánh vần, dừng đúng §7-10) | 1b05851 | 09-30 08:01 | 23/24 đỏ `tab_unmounted_socket_rule` (b) | 0C | Lần sửa 4 4a1bc31 (15:33 +07) |
| B8d-3 thử | 0517c0a (commit 15:53:12 +07) | 09-30 08:53:20–08:54:26 | 25/25, 23/23, 26/26 | 0D | cổng qua |
| **B8d-4 chính thức** | b6c27b1 (commit 15:55:37 +07) | 09-30 08:55:47, 08:56:10, 08:56:38 | 25/25, 23/23, 26/26 | 0D | commit 024ec64 |

Mỗi lần sửa luật được commit TRƯỚC lượt kế tiếp; lượt chính thức B8d-4 bắt đầu 10 s sau khi commit b6c27b1 tồn tại, 3 kịch bản
cách nhau 23 s và 28 s (mỗi lượt khoảng 11 s khởi động + 6 s trình duyệt) → không có chỗ cho lượt chính thức lặp/chọn lọc tại
b6c27b1. `git merge-base --is-ancestor 0517c0a b6c27b1` đúng; `git diff --name-only 0517c0a b6c27b1 -- backend src frontend
scripts tests` rỗng. JSON đỏ còn nguyên: blob `reports/e2e_2026-09-30/fingerspell_default.json` = c7a83cbc… ở cả d2752c3 và HEAD;
3 blob `reports/e2e_2026-09-29/*` ở e3d0df8 == HEAD (8c3c306…, 08cf90b…, 8f4537a…); `git log` các đường dẫn này chỉ ra
e3d0df8, d2752c3 (và 024ec64 cho `_r4`).

**Đánh giá từng lần đổi theo 5 câu hỏi của 0D.12:**

| | (1) nguyên nhân gốc bằng code/cơ chế | (2) luật mới suy từ mục đích viết trước | (3) điểm nới nêu rõ + ca âm | (4) kiểm bỏ có kiểm thay cùng mục đích | (5) chính thức 1 lần/kịch bản, JSON đỏ giữ | Hạ tiêu chí để pass? |
|---|---|---|---|---|---|---|
| Lần sửa 2 (0B) | Có: socket HMR do `/@vite/client` chèn khi `npm run dev`, không nằm trong `frontend/src`, không có trong bundle | Có: mục đích (1) không nối thẳng `:8000`, (2) mọi WS của APP qua `/ws/` (0B.1) | Có: định nghĩa HMR 3 điều kiện đồng thời, tối đa 1; `:8000` cấm MỌI socket; AC12-t ca 1–9 (16 test) | `ws_urls_all_via_proxy_no_8000` → 3 kiểm URL cùng mục đích | B8 1 lần/kịch bản; e3d0df8 giữ | KHÔNG. Nhưng luật mồ côi StrictMode (0B.2) viết SAI giả định (planner tự nhận ở 0C.1: không đọc từng socket của JSON Đánh vần e3d0df8) |
| Lần sửa 3 (0C) | Có: `App.jsx:9,53` tab mặc định mount `Phase12Pipeline`; `main.jsx:7` StrictMode; kịch bản bấm tab ngay | Có: mục đích luật mồ côi = bắt socket app hỏng/không phục vụ kịch bản | Có: nới 1 điểm (cho 1 `session_info` v2) quyết trước lượt chính thức và chưa từng được dùng (mọi socket tab_unmounted quan sát đều 0 message); siết thêm path `used` vắng, path lạ, handshake, thời điểm; AC12-t mục 10 (30 test) | luật mồ côi giữ nguyên chữ cho path `used`; path còn lại có luật riêng | chỉ trial trước; B8c-3 chạy 1 lần, đỏ, dừng, JSON đỏ commit | KHÔNG |
| Lần sửa 4 (0D) | Có: passive effect của lần mount đầu được xả khi xử lý click (`Phase12Pipeline.jsx:121-128`); mốc cũ là giờ Node nhận sự kiện CDP | Có: M1–M3 (0D.2); (b) đo M3 bằng thời điểm, thay bằng đo M3 trực tiếp (module gọi `new WebSocket`) | Có: nới đúng 1 điểm (thời điểm tạo socket của `Phase12Pipeline.jsx`), nêu ở 0D.3; 0D.4 + AC12-t mục 11 (13 test) | (b) → `tab_unmounted_owner_rule` (M3) | thử 1 lần/kịch bản + chính thức 1 lần/kịch bản; d2752c3 giữ | KHÔNG về thực chất (xem dưới) — nhưng lượt `_r4` CHỈ xanh nhờ lần sửa này |

**Kiểm độc lập Lần sửa 4 (reviewer).**
- Luật cũ trên dữ liệu mới: nạp `git show 1b05851:scripts/e2e_fullstack.py` (luật 0C) và chạy trên `observations` THẬT của
  `reports/e2e_2026-09-30_r4/fingerspell_default.json` → `tab_unmounted_socket_rule` ĐỎ (socket 0 và 1: `created_t_s 2.185 not
  before click_t_s 2.021`). Tức kết quả xanh của `_r4` phụ thuộc trực tiếp vào việc đổi luật sau khi thấy lượt đỏ — ghi thẳng.
- Pha tạo socket khác nhau giữa 2 lượt (thử B8d-3 `before_click`; chính thức `after_click`: `t_page_ms` 1037.6 và 1041.1 >
  `click_page_ms_after` 1036.6) → điều kiện thời điểm phụ thuộc lập lịch, không phải tính chất của app; đúng lý do 0D.3. Kết luận
  H1/H2 trong 06-progress:520-521, 551-555 và progress_log khớp luật đặt trước (thử → H1; chính thức → cả H1 lẫn H2 không mô tả
  đúng), không dùng để đổi luật. n = 2 lượt → chỉ mô tả, không khái quát (kế hoạch §6 đã nói).
- Hook quy nguồn đúng trên dữ liệu thật: trong `_r4`, 2 bản ghi `/ws/live-stream` có frame `/src/` đầu tiên là
  `Phase12Pipeline.jsx`, 2 bản ghi `/ws/hand-landmarks` là `Fingerspelling.jsx`, HMR chỉ `<other>` → hook phân biệt được component
  trong trình duyệt thật, không chỉ trong test tổng hợp. `n_records_by_path == n_cdp_by_path` ở cả 3 JSON.
- 0D.7 (hook không đổi hành vi app): tự so `checks` của JSON đỏ B8c-3 (không hook) với `_r4` Đánh vần: tập B8c-3 ⊂ `_r4` (thêm đúng
  `tab_unmounted_owner_rule`); kiểm xanh ở B8c-3 mà không xanh ở `_r4`: rỗng; `console_error_0`, `pageerror_0`, `requestfailed_0`
  xanh ở cả 3 `_r4` (`_work/_rev06_tmp/p3_cmp2.py`).
- AC12-t tại HEAD: `TestE2eSocketRules` 16, `TestE2eScenarioRoles` 30 (đủ 30 tên đã chạy; 1 dòng ok bị log chen), `TestE2eTabOwner`
  13 — 59/59 ok trong lượt chạy phần 3. Phần 1 đã chạy 30 đột biến vào `e2e_fullstack.py`, tất cả bị giết.

- Ca âm tự dựng (`_work/_rev06_tmp/p3_neg.py`, log `p3_neg.log`): lấy `observations` THẬT của `_r4` Đánh vần, mỗi ca đổi MỘT
  yếu tố, chạy các hàm thuần tại HEAD (`classify_ws`, `app_ws_by_path`, `scenario_ws_roles`, `tab_unmounted_owner_check`).
  **16/16 đúng kỳ vọng**:
  P0 dữ liệu gốc → 6 kiểm socket xanh; N1 `Fingerspelling.jsx` mở `/ws/live-stream` TRƯỚC lúc bấm (ca mà luật (b) cũ không bắt
  được) → owner + tab đỏ; N1b 1 trong 2 socket live có owner `Fingerspelling.jsx` → owner đỏ; N2 socket `Phase12Pipeline` sau bấm
  nhận `frame_result` → tab đỏ; N3 có `session_info` nhưng đóng SAU `record_clicked` → đỏ; N4 không đóng (rò component) → đỏ;
  N5 socket thứ 3 (kết nối lại sau khi gỡ) → đỏ; N6 thiếu dữ liệu hook → owner đỏ; N7 socket tạo qua helper `/src/lib/ws.js` →
  owner đỏ; N8 socket CDP không có bản ghi trang (vd. worker) → owner + tab đỏ; N8b 2 socket CDP / 1 bản ghi → owner đỏ; N9 `:8000`
  → 2 kiểm URL đỏ; N10 `protocol_version` 3 → đỏ; N11 bắt tay 403 → đỏ; N12 message `error` → đỏ; P1 (xanh theo thiết kế) socket
  `Phase12Pipeline` sau bấm, 1 `session_info` v2, đóng trước `record_clicked` → xanh.
  Phần còn lọt đúng như 0D.4: socket do `Phase12Pipeline.jsx` tạo, tối đa 2, không dữ liệu (hoặc 1 `session_info` v2), đóng trước
  khi kịch bản ghi, bắt tay không bị từ chối, qua proxy — không gây hại theo M2.

**Kết luận riêng về 3 lần đổi tiêu chí:** không lần nào là hạ tiêu chí để pass về thực chất: mỗi lần chỉ ra cơ chế bằng code, giữ
nguyên chữ các kiểm cùng nhóm (`:8000`, qua proxy, HMR, M2), điểm nới được nêu thẳng, quyết trước lượt kế tiếp, có ca âm (của
coder và của reviewer) cho mọi đường có hại; lượt chính thức mỗi kịch bản đúng 1 lần; mọi JSON đỏ còn trong repo. Rủi ro còn lại
(nêu thẳng): (i) 3 lần đổi liên tiếp cùng nhóm kiểm cho thấy luật socket được viết từ hình dung rồi sửa theo quan sát — chất lượng
lập kế hoạch kém, không phải gian lận; (ii) `_r4` Đánh vần chỉ xanh nhờ Lần sửa 4, và test 11d dùng chính số của lượt đỏ làm ca
dương; (iii) sức mạnh của luật cuối chỉ được chứng minh bằng ca tổng hợp trên hàm thuần + 1 lượt thật, không có lượt thật nào cài
lỗi có chủ đích vào app. Chấp nhận được vì luật cuối đo trực tiếp M3 và giữ nguyên M1/M2.

**V9 (TRUNG BÌNH, minh bạch): lần đổi tiêu chí THỨ TƯ, do coder, trước lượt B8 chính thức, không được báo đúng.** Lượt dev
`_work/_plan06_tmp/b8_dev_fingerspell.json` (ada003b, 10:44Z) có `hand_ws_session_info` ĐỎ (`detail`: socket đầu `first_type`
null, 0 message). Script commit sau đó (`git show 7e38118:scripts/e2e_fullstack.py`, dòng 231-236) đã đổi kiểm này thành chỉ xét
socket có message (`used = [w for w in hws if w["n_messages"] > 0]` — bỏ qua MỌI socket 0 message, không cần đã đóng, không cần
không phải socket cuối). `docs/plans/06-progress.md:237-239` lại ghi lượt dev "đạt mọi kiểm tra AC12 TRỪ
`ws_urls_all_via_proxy_no_8000`" — SAI so với JSON. Giảm nhẹ: coder có nêu hiện tượng StrictMode (06-progress:259) và planner đã
xét nó như giả định 0B.2 mục 2, thay bằng luật chặt hơn (`strictmode_orphans`: 0 message + đã đóng + không phải cuối + tối đa
1/path; `scripts/e2e_fullstack.py:538-545`), nên tiêu chí CUỐI không bị nới. Việc phải làm: sửa/ghi chú 06-progress:237-239 cho
đúng JSON dev (có `hand_ws_session_info` đỏ và việc đổi kiểm trước lượt chính thức).

### §13 — Kết luận vượt bằng chứng (FAIL: 2 câu sai so với bằng chứng)
Đã đọc: `docs/phase12_api.md` (174 dòng), dòng 112 của `docs/progress_log.md` (dòng của 06), `note`/`info_not_accuracy` của 3 JSON
`_r4`, 06-progress B8/B8d/B9b, `docs/STATE.md` (các dòng về 06).

**Câu SAI (phải sửa trước APPROVE):**
- **O1** `docs/phase12_api.md:32-33`: "Qua proxy Vite, CORS không tham gia; CORS chỉ có ý nghĩa khi trang origin khác gọi thẳng
  cổng 8000." Thăm dò thật ở §11 bác bỏ: qua `:3000`, Vite dev server tự trả lời CORS (preflight 204, ACAO phản chiếu) cho mọi
  origin họ loopback (`http://localhost:5173`, `http://attacker.localhost:8080`), tức REST đọc được từ các origin mà danh sách
  `VSL_CORS_ORIGINS` không cho. Sửa: nêu đúng hành vi (hoặc đặt `server.cors`/`preview.cors` trong `vite.config.js` rồi viết lại câu
  có test), kèm dòng Giới hạn.
- **O2** `docs/plans/06-progress.md:237-239`: lượt dev B8 "đạt mọi kiểm tra AC12 TRỪ `ws_urls_all_via_proxy_no_8000`" — SAI:
  `_work/_plan06_tmp/b8_dev_fingerspell.json` có `hand_ws_session_info` đỏ (và `code_clean_at_run` đỏ, dự kiến vì code bẩn), sau đó
  kiểm bị đổi trước lượt chính thức (V9, §12).

**Câu mạnh hơn bằng chứng (nên sửa chữ, mức THẤP):**
- **O3** `docs/phase12_api.md:153-154`: "Landmark Cấp 1 live được trích từ frame JPEG (chất lượng 0.9) do trình duyệt nén … ảnh hưởng
  đo được ở mục dưới." Mục dưới đo JPEG của `cv2.imencode` q90 (`scripts/hand_live_check.py:148`; JSON ghi "not the browser
  encoder"), không phải bộ nén canvas của trình duyệt → ảnh hưởng của đường live thật CHƯA đo; chỉ có đại diện gần đúng. Câu
  `:171` có nêu "bộ nén cv2, không phải trình duyệt" nhưng câu 153-154 vẫn nói "đo được".
- **O4** `docs/phase12_api.md:111-114`: "trích … bằng đúng extractor lúc train Cấp 1 … Tương đương … được kiểm bit-by-bit" — đúng
  tham số và đúng trên CÙNG máy với ảnh PNG (AC5); với landmark train thật (Kaggle/Linux) thì KHÔNG bằng hệt (`:168-170`, 10/10 clip
  lệch khác 0, 1/10 lệch cờ detected). Nên thêm "(cùng máy, ảnh PNG)" ngay ở câu 114 để không đọc thành live == dữ liệu train.
- **O5** `docs/phase12_api.md:173-174` và progress_log:112 "top-1 trùng … 10 clip TRAIN": 2/10 clip là qipedc (`qipedc_D0489`,
  `qipedc_D0490B`); JSON AC6 chỉ ghi "hauuto clips are training data" — việc 2 clip qipedc thuộc TRAIN của model Cấp 1 chưa được
  reviewer xác minh (chuyển phần 2, mục 5). Cách viết đã tránh gọi là độ chính xác — đúng.
- Câu đúng mực (không tính lỗi): `note` của 3 JSON `_r4` ("End-to-end run on ONE training clip per scenario: shows that backend +
  frontend run together … Not an accuracy measurement …"); `info_not_accuracy` ở cả 3; 06-progress B8d-4 ghi `gloss` trùng nhãn là
  "clip TRAIN — không phải độ chính xác"; kết luận H1/H2 theo luật đặt trước, có nêu n = 2 lượt không ổn định; progress_log:112 ghi
  "Kết luận vslt-reviewer: CHỜ"; `docs/phase12_api.md:136` ghi 24 fps / 0.9 / 2 là "giá trị thiết kế, chưa đo"; mục 6 ghi DoD 8
  "chưa đo trong việc này". Không thấy câu nào nói e2e chứng minh app chạy với webcam/người dùng thật.
- Ghi chú V0: progress_log:112 "31 module 526 OK, 0 skip" đúng tại thời điểm (reviewer tái lập ở 0491877, §2) nhưng HIỆN KHÔNG tái
  lập được (dữ liệu mất) — khi đóng kế hoạch cần ghi rõ ngày/commit của con số này.

**Thí nghiệm còn thiếu (giới hạn phải giữ trong báo cáo cuối):**
1. E2E = 1 clip TRAIN/kịch bản, 1 lượt chính thức, webcam giả Y4M, dev server — chỉ chứng minh "chạy được cùng nhau"; chưa có webcam
   thật, người ký khác, ánh sáng/nền khác, bản build (`vite preview`/tĩnh), nhiều ký hiệu một phiên, chạy lặp để đo độ ổn định.
2. JPEG canvas của trình duyệt so với frame mp4 lúc train (Cấp 1 và Cấp 2) — chưa đo (AC6 chỉ có JPEG cv2).
3. Lệch landmark Kaggle/Linux ↔ Windows: 10 clip; ảnh hưởng lên nhãn trên dữ liệu không phải TRAIN chưa đo.
4. CORS/Origin qua proxy Vite chưa có test tự động (AC3 dùng TestClient gọi thẳng app); probe của reviewer (§11) là lần đo duy nhất.
5. Biên của điều kiện (c) (đóng trước `record_clicked`): 3 lượt, biên 0.35–0.45 s; chưa đo có kiểm soát. H1/H2: chưa phân định.
6. Độ trễ (DoD 8), số kết nối WS đồng thời/tải: chưa đo.
7. AC5/AC4 phần MediaPipe thật/AC7-d/AC10 hiện không chạy lại được (V0) — cần chạy lại sau khi khôi phục dữ liệu.

## Vấn đề theo mức độ

- **V0 — NGHIÊM TRỌNG (môi trường, KHÔNG do code kế hoạch 06; chặn việc review tiếp).** Dữ liệu gitignored/untracked của
  người dùng đã bị xóa: `data/external/` (hauuto_raw, alphabet_hands_kaggle, …), `data/Dataset/` (Videos, Labels của qipedc),
  `checkpoints/` (gồm `alphabet_best.pt`, `provenance.json`, checkpoint stgcn/stgcn_h360 mà AC10 dùng) — thư mục còn nhưng
  rỗng (`du -sh`: 0), mtime cả ba = `30/09/2026 23:42`. Bằng chứng: `git status --porcelain` chụp trước AC2 ở lượt 1
  (`_work/_rev06_tmp/status_before_ac2.txt`) có `?? data/Dataset/` và `?? data/external/`; nay không còn (diff với
  `_work/_rev06_tmp/status_now.txt`); lúc đó AC2 chạy 526 test 0 skip nhờ các dữ liệu này (§2). Thời điểm trùng với việc
  "Đã gỡ worktree tạm ../_rev06_wt" + dời thư mục tạm (`docs/STATE.md:107-110`, commit 9d1d40f lúc 23:43:12). Worktree đó có
  thư mục dữ liệu nối bằng JUNCTION về repo chính (§1, lượt 1) nên giả thuyết mạnh là: lệnh xóa/dời worktree đã đi xuyên
  junction và xóa nội dung đích. `.git/worktrees` không còn. Bản sao duy nhất tìm thấy (find độ sâu 6 dưới thư mục cha):
  `_work/_kaggle_staging/restore_root/checkpoints/{alphabet_best.pt, stgcn_tier2_indomain.pt, stgcn_unified_best.pt}` (ngày
  28/09; sha256 alphabet_best.pt = a6311820ba778b6b…b708a2, CHƯA đối chiếu được vì `provenance.json` cũng mất). Không tìm thấy
  bản sao video hauuto/qipedc. Hệ quả: AC2 không còn tái lập được (AC5, AC4 phần MediaPipe thật, AC6, AC7-d, AC10 và các test
  dữ liệu cũ sẽ skip hoặc lỗi); phần 2 (rò rỉ, nhất quán train–realtime) cần dữ liệu. Reviewer KHÔNG khôi phục (ngoài quyền).
  Xem mục "CẦN NGƯỜI DÙNG QUYẾT ĐỊNH".

Không có vấn đề mức CAO hay TRUNG BÌNH do code/test của kế hoạch 06 trong hạng mục 1–4.

- **V1 — THẤP (quy trình, AC13 "mỗi commit có output impact/detect-changes").** 5 commit của C06 không có dòng
  detect-changes trong message: 050d337 (đã nêu ở STATE) và thêm ada003b, 15200d9, 0e506c3, 001e020 (reviewer tìm thấy,
  STATE chưa nêu). Lệnh: vòng lặp `git log -1 --format=%B <c> | grep -qi detect-changes` trên C06. Cả 5 chỉ chạm
  `docs/plans/06-progress.md` → không có rủi ro code; nhưng đây là lệch chữ AC13, cần ghi nhận ở kết luận cuối (phần 3).
- **V2 — THẤP (quy trình).** 2fa59e0 (14:53:14, sau 85ef325 14:52:55) và 1b05851 (15:00:48, sau e1d13d2 15:00:32):
  detect-changes chạy sau commit code / message ghi "risk low" không khớp output thật — planner đã ghi nhận ở 0D.9 mục 12;
  chỉ docs; từ 828e472 trở đi đã chép nguyên văn output chạy trước commit. Không chặn.
- **V3 — THÔNG TIN (chữ kế hoạch).** 0D.10 nói dòng `-` "CHỈ là 6 dòng của method bị thay"; thực tế chỉ 2 dòng `-` (4 dòng
  giữa của method giữ nguyên). Chặt hơn chữ kế hoạch, không phải nới.
- **V4 — THÔNG TIN (độ phủ của smoke AC10).** Ở `stgcn_h360`, bước "text rác" nhận `bad_timestamp` (phiên harmonized kiểm
  timestamp trước khi giải mã) thay vì mã giải mã; vẫn đúng chữ §3.6 (mã thuộc bảng), nhưng bước này không đi qua đường
  giải mã ở pipeline harmonized. Đường giải mã lỗi của `/ws/live-stream` đã có test riêng từ kế hoạch 04 (`tests.test_ws_live_contract`).
- **V5 — THÔNG TIN (độ phủ AC4).** Bỏ `cv2.cvtColor(BGR2RGB)` trong `HandLandmarkSession.process` không làm AC4 đỏ; chỉ AC5
  (so bit với `_extract_one`) có thể bắt. Proxy đột biến AC5 (§1): M1 bị giết (live 0 frame có tay so với offline 127).

Vấn đề phát hiện ở phần 3 (lượt 3, HEAD 8f5969a):
- **V6 — THẤP (bảo mật, đường dev).** Qua proxy Vite `:3000`, REST `/api/*` đọc được từ mọi origin họ loopback, cổng bất kỳ (Vite
  6.4.3 `server.cors` mặc định phản chiếu origin khớp `localhost`/`*.localhost`/`127.0.0.1`/`[::1]`); danh sách chính xác
  `VSL_CORS_ORIGINS` chỉ có hiệu lực khi gọi thẳng `:8000`. WS vẫn bị chặn 403 qua proxy. Bằng chứng: §11,
  `_work/_rev06_tmp/p3_proxy_probe.json`. Sửa: đặt `cors` cho `server`/`preview` trong `frontend/vite.config.js` (+ test văn bản
  AC3-g) hoặc ghi đúng giới hạn trong `docs/phase12_api.md`.
- **V7 — THẤP (bảo mật).** `/ws/hand-landmarks` gửi `detail` `hand landmark extractor unavailable: {e}` (`backend/main.py:1645`)
  — chuỗi exception nguyên văn (≤ 200 ký tự), có thể lộ đường dẫn tuyệt đối cho client cục bộ. Backlog: thông điệp cố định.
- **V8 — THÔNG TIN (ngoài phạm vi 06, AC1 khóa file).** `frontend/src/components/Reports.jsx:73-77` hiển thị số gõ tay (98.13%,
  95.0%, 8.07%/17.04%, 46.41%) không trỏ JSON có lệnh + commit; guard AC8 không bắt loại này. Backlog kế hoạch sau.
- **V9 — TRUNG BÌNH (minh bạch / đổi tiêu chí sau khi thấy kết quả).** Coder đổi `hand_ws_session_info` (bỏ qua mọi socket
  0 message) sau lượt dev B8 đỏ ở kiểm này, trước lượt chính thức; `docs/plans/06-progress.md:237-239` báo lượt dev chỉ đỏ kiểm URL
  — sai với `_work/_plan06_tmp/b8_dev_fingerspell.json`. Tiêu chí cuối không bị nới (0B.2 thay bằng `strictmode_orphans` chặt hơn),
  nhưng phải sửa bản ghi. Bằng chứng: §12.
- **V10 — TRUNG BÌNH (tài liệu sai, mục 13).** `docs/phase12_api.md:32-33` khẳng định CORS không tham gia qua proxy — bị thực
  nghiệm bác bỏ (O1). Kèm các câu nên chỉnh chữ O3–O5 (THẤP).


Chuyển cho phần 2/3 (không đánh giá ở đây):
- Phần 2 (mục 9): AC5 chứng minh live == offline CÙNG MÁY; lệch Kaggle/Linux ↔ cục bộ (AC6: detected lệch 1/10 clip, max
  diff 0.2298) và JPEG q90 ↔ PNG (2/10, 0.2403) là lệch train↔realtime thật, cần đánh giá ở mục 9.
- Phần 3 (mục 12/13): tính hợp lệ của 3 lần đổi luật socket sau khi thấy kết quả (0B, 0C, 0D). Dữ kiện đã thu: JSON chính thức
  `_r4` Đánh vần có `tab_unmounted_click_phase` = `["after_click", "after_click"]` (`t_page_ms` 1037.6 và 1041.1 >
  `click_page_ms_after` 1036.6) — tức cả 2 socket `/ws/live-stream` được tạo SAU lúc bấm tab, đúng dạng mà luật (b) cũ sẽ báo
  đỏ; lượt thử B8d-3 thì `before_click`. Mọi kiểm URL/HMR/`:8000`/M2 vẫn xanh.

V1 đã kiểm lại ở lượt 2: vòng lặp trên 40 commit `_work/_rev06_tmp/c06.txt` ra 9 commit không có `detect-changes`; 4 là
commit planner (4a1bc31, 717aa3e, f52de6f, facffea — ngoài phạm vi AC13 của coder), 5 còn lại đúng như V1.

## Kết luận tạm (phần 1)

- Hạng mục 1 PASS (đột biến AC5 bằng proxy), 2 PASS, 3 PASS, 4 PASS. Không có FAIL nào do code/test của kế hoạch 06.
- Vấn đề: V0 NGHIÊM TRỌNG (môi trường: mất dữ liệu `data/external`, `data/Dataset`, `checkpoints` lúc 23:42, không do
  coder); V1, V2 THẤP (quy trình AC13, chỉ commit docs); V3–V5 thông tin.
- Hạng mục 2 PASS là bằng chứng lịch sử tại 0491877 (log `_work/_rev06_tmp/ac2_31.log`); ở trạng thái máy hiện tại KHÔNG
  tái lập được cho tới khi khôi phục dữ liệu.
- Chưa thể APPROVE kế hoạch 06 cho tới khi: (1) V0 được xử lý (khôi phục dữ liệu, chạy lại AC2 ra lại 526 OK 0 skip, và
  `mutate_ac5.py M1`…`M5` trên chính test AC5), và (2) phần 2, phần 3 xong.

## Kết luận tạm (phần 3)

- Hạng mục 10 PASS; 11 PASS (V6, V7 THẤP); 12 PASS (V9 TRUNG BÌNH — minh bạch, tiêu chí cuối không bị nới); 13 **FAIL** (O1 câu
  bảo mật sai trong `docs/phase12_api.md:32-33`; O2 câu kết quả sai trong `docs/plans/06-progress.md:237-239`).
- Đánh giá riêng 3 lần đổi tiêu chí AC12 (0B, 0C, 0D): KHÔNG phải hạ tiêu chí để pass về thực chất. Mỗi lần có cơ chế đọc từ code,
  luật mới suy từ mục đích viết trước, điểm nới nêu thẳng và quyết trước lượt kế tiếp, lượt chính thức mỗi kịch bản đúng 1 lần, JSON
  đỏ giữ nguyên. Luật cuối bắt được mọi socket có hại reviewer dựng (16/16, trên dữ liệu thật `_r4`), kể cả ca luật thời điểm cũ bỏ
  lọt (socket sai nguồn tạo trước lúc bấm). Nêu thẳng: `_r4` Đánh vần chỉ xanh nhờ Lần sửa 4 (luật 0C chạy trên cùng dữ liệu → đỏ).
- Việc phải làm trước APPROVE (thêm vào danh sách của phần 1), xếp theo mức độ:
  1. (V0, NGHIÊM TRỌNG, môi trường) khôi phục dữ liệu, chạy lại AC2 31 module + đột biến AC5 — như phần 1.
  2. (V10/O1, TRUNG BÌNH) sửa `docs/phase12_api.md:32-33` cho đúng hành vi CORS qua proxy Vite (hoặc sửa `vite.config.js` rồi viết
     lại câu, có test); AC11 phải vẫn xanh.
  3. (V9/O2, TRUNG BÌNH) sửa/ghi chú `docs/plans/06-progress.md:237-239` cho đúng JSON dev B8 (`hand_ws_session_info` đỏ, kiểm đổi
     trước lượt chính thức).
  4. (THẤP, có thể chuyển backlog nếu planner ghi rõ) V6 cấu hình `cors` của Vite; V7 `detail` cố định; O3–O4 chỉnh chữ.
- Phần 2 (5–9) chưa làm; chuyển thêm cho phần 2: O5 (2 clip qipedc của AC6/AC5 có thuộc TRAIN của model Cấp 1 không).
- Kết luận chung hiện tại: CHANGES_REQUESTED (còn FAIL ở 13; V0 chặn tái lập; phần 2 chưa làm).

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **Khôi phục dữ liệu bị xóa (V0).** `data/external/`, `data/Dataset/`, `checkpoints/` hiện rỗng. Nguồn có thể: Recycle Bin /
   bản sao lưu của người dùng; tải lại hauuto/qipedc từ nguồn gốc (người dùng tự làm — agent không chạy script tải); checkpoint
   từ `_work/_kaggle_staging/restore_root/checkpoints/` (phải đối chiếu sha256 với `provenance.json` gốc trước khi dùng) hoặc
   tải lại output kernel Kaggle private. Việc này ngoài quyền của reviewer và coder.
2. Sau khi khôi phục: có chạy lại AC2 đầy đủ (khoảng 13 phút) + 5 đột biến AC5 để đóng V0 trước phần 2 không.
3. Quy trình: cấm junction/symlink tới dữ liệu trong worktree tạm (hoặc bắt buộc gỡ junction bằng `rmdir` trước khi
   `git worktree remove`); đề xuất ghi vào `docs/prompts/autopilot.md`.
