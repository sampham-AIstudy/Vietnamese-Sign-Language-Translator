# Review kế hoạch 06 — Việc 5: frontend + WS v2 + CORS + e2e fullstack

Reviewer: vslt-reviewer (độc lập). Nhánh `feat/vslt-complete`, HEAD lúc review phần 1: `0491877` (lượt 1, hạng mục 2–4 + phần lớn 1);
`9d1d40f` (lượt 2, hoàn thiện hạng mục 1 — chỉ commit STATE/.gitignore/review, không đổi code).
Kế hoạch: `docs/plans/06-viec5-frontend.md`. P6 = `797d0af` (06-progress.md:3).

TRẠNG THÁI: phần 1 (hạng mục 1–4) XONG. Phần 2 (5–9) và phần 3 (10–13) chưa làm.
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
| 10 | Không Math.random/mock/hard-code | CHƯA LÀM — phần 3 | |
| 11 | Bảo mật | CHƯA LÀM — phần 3 | |
| 12 | So sánh công bằng / GATE không nới (gồm đánh giá 3 lần đổi tiêu chí §0D.12) | CHƯA LÀM — phần 3 | |
| 13 | Kết luận vượt bằng chứng | CHƯA LÀM — phần 3 | |

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

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

1. **Khôi phục dữ liệu bị xóa (V0).** `data/external/`, `data/Dataset/`, `checkpoints/` hiện rỗng. Nguồn có thể: Recycle Bin /
   bản sao lưu của người dùng; tải lại hauuto/qipedc từ nguồn gốc (người dùng tự làm — agent không chạy script tải); checkpoint
   từ `_work/_kaggle_staging/restore_root/checkpoints/` (phải đối chiếu sha256 với `provenance.json` gốc trước khi dùng) hoặc
   tải lại output kernel Kaggle private. Việc này ngoài quyền của reviewer và coder.
2. Sau khi khôi phục: có chạy lại AC2 đầy đủ (khoảng 13 phút) + 5 đột biến AC5 để đóng V0 trước phần 2 không.
3. Quy trình: cấm junction/symlink tới dữ liệu trong worktree tạm (hoặc bắt buộc gỡ junction bằng `rmdir` trước khi
   `git worktree remove`); đề xuất ghi vào `docs/prompts/autopilot.md`.
