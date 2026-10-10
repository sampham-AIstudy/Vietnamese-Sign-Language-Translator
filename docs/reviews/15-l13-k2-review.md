# Review 15 — L13-K2 (nối `fusion_target` vào `Level1Speller`)

- Bước: K2 (`docs/plans/15-lan-sua-13.md` §4.1–§4.3, §8 hàng 8, §9 AC-K1…AC-K6, §10) + mục "Bắt buộc ở K2" của `docs/reviews/15-l13-k1-review.md`.
- Commit xét: `3a78019` (mã + test + docs), `5d7fe43` (chỉ `docs/plans/15-progress.md`). Cha `44d2b23`. HEAD khi review `8a9fb0a`. Coder: vslt-coder-claude (không phải agy ⇒ phần kiểm agy không áp dụng).
- Reviewer: vslt-reviewer, 2026-10-10. Không sửa mã; log tạm `_work/_plan15_l13/review_k2_*`.

## Kết luận: APPROVE

Không có FAIL. Có 4 điểm THẤP và 1 ghi chú, không chặn bước sau.

## Bảng 1–13

| # | Mục | KQ | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch, test kiểm thật | PASS | `git diff 44d2b23..3a78019 -- src/inference/level1_core.py`: `_fuse` (core `:399-414` tại 3a78019) được gọi ở `_apply` (`elif not self._fuse(...)`, sau luật thay dấu thanh, đúng thứ tự cũ) VÀ `on_label` (sau nhánh `VARIANT_BASE`, trả `action "replace"`); bỏ hẳn hai nhánh `tokens[-1]` cũ; sự kiện `_log("replace", target, "fusion", t_ms, seq, prediction=<nhãn gốc>, confidence, replaced, index, rule)` + `event/t_ms/tokens_after` của `_log` = đủ khóa F7; nhánh `VARIANT_BASE` giữ `source "model"` (token == nhãn). `unikey_mode=False`: `_fuse` trả False ngay ⇒ `_apply`/`on_label` y M0. 7 mục bắt buộc của review K1 có test: (1) `TestSpellerOracleK2` — MỌI dòng `ORACLE_15_PAIRS` + `ORACLE_SPELLING` (oracle nguyên văn K1) × 3 đường (on_result / on_label append / on_label theo action decoder), so tokens + text; (2) `TestSpellerRandomK5` seed 20261010, 200 chuỗi, so `text == compose(tokens)` VÀ tokens == oracle viết từ spec sau MỖI thao tác, giữ số token dấu thanh; assert luôn đúng cũ đã xóa; (3) `TestMutationLocksK2` R1/R3/R4; (4) `TestOneTableK4`; (5) `TestFusionEventsK3` (bộ khóa == đúng tập F7, phát lại sự kiện ra tokens cuối) + `TestClipEventsK3`; (6) `TestUnikeyOffK6` + AC-K2 (dưới); (7) `tests/test_level1_guard.py` +1/0 thêm `level1_unikey.py`. `_decoder_action` của test khớp decoder thật (`level1_segmenter.py:656`: replace ⇔ `VARIANT_BASE[label] == last`). |
| 2 | Tự chạy lại test | PASS | `PY -m unittest tests.test_level1_unikey tests.test_level1_core tests.test_level1_lan_sua_12 tests.test_level1_guard` → `review_k2_quick.log`: `Ran 107` `OK` (coder: 107 OK). Toàn bộ `tests/test_level1_*.py` + `tests.test_backend_source_guard` → `review_k2_full.log`: `Ran 681 tests in 471.574s`, `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36`, `EXIT 0` (coder: 681 OK skip 1). Đột biến của reviewer (worktree tạm `_work/_plan15_l13/wt_k2rev` từ `3a78019`, đã gỡ; `review_k2_mut.log`; base `OK (skipped=5)`): RA ghép chỉ ở `on_label` (bỏ ở `_apply`) ĐỎ f=40 e=1; RB sự kiện ghép `source "model"` ĐỎ f=50; RC `_fuse` đặt TRƯỚC nhánh VARIANT_BASE ĐỎ f=1; RD `index` = phần tử cuối ĐỎ f=5; RE `on_label` trả `add` khi ghép ĐỎ f=5; khôi phục byte-identical. Log coder `k2_mut_run.log`: base OK, 24/24 RED (M1–M10, R1–R5, K1–K9), R1/R3/R4 nay đỏ — khớp. Smoke: `PY level1_demo.py --source …/a_hau_A_001.mp4 --headless --config configs/level1_demo_classifier_rev9.json --out-json _work/_plan15_l13/review_k2_smoke.json` exit 0, `git_commit 8a9fb0a…`, `code_dirty false`, `rearm_mode classifier`, text "a", 1 nhãn / 1 sự kiện `model`, 0 lệch token≠dự đoán. |
| 3 | Test không bị nới | PASS | `git diff --numstat 44d2b23..3a78019`: `tests/test_level1_unikey.py` 365/5, `tests/test_level1_guard.py` 1/0; `tests/test_level1_core.py`, `tests/test_level1_lan_sua_12.py` không đổi (cũng không đổi từ M0 `5a32cff`). 5 dòng xóa ở `test_level1_unikey.py` (file mới của plan, `5a32cff..3a78019` 610/0): 1 dòng docstring; 1 điều kiện F3 của `TestFusionRandomK5` thay bằng `_u_after_initial_consonant` — tập ca bị assert `None` là TẬP CHA của điều kiện cũ (cũ: `before[-1]=="u"` và `before[-2]` là chữ ⇒ cùng âm tiết ⇒ thỏa điều kiện mới) ⇒ chặt hơn; 3 dòng assert luôn đúng `:242-244` xóa theo mục bắt buộc 2 (phép so thật ở `TestSpellerRandomK5`). Không `skip` mới ngoài `TestClipEventsK3` (skip chỉ khi thiếu clip/checkpoint, có tên file — đúng AC-1). Không áp dụng mục agy. |
| 4 | Nguồn gốc dữ liệu | PASS (không áp dụng) | Bước logic; dữ liệu test là chuỗi tạo có kiểm soát (docstring ghi rõ); clip D2 là clip hauuto thật chỉ dùng chạy app. |
| 5 | Rò rỉ | PASS (không áp dụng) | Không train/đánh giá. |
| 6 | VAL/TEST | PASS (không áp dụng) | Không chọn model. |
| 7 | Số liệu truy được | PASS | `docs/level1_desktop.md` +4/0 (mục Giới hạn 14) không có số đo; "15 cặp" là kích thước bảng F2. Số trong `15-progress.md` (Ran 681, 24/24) khớp log tự chạy/đọc. Không áp dụng mục agy. |
| 8 | Cỡ mẫu | PASS (không áp dụng) | Không có kết luận thống kê; smoke ghi rõ "kiểm khói, không phải số đo". |
| 9 | Nhất quán train–realtime | PASS | Đường khung MediaPipe/tiền xử lý không đổi (`git diff --stat 44d2b23..3a78019 -- src/data src/inference/level1_segmenter.py level1_demo.py src/inference/fingerspelling_compose.py` rỗng). `is_variant_of`, `compose`, decoder không đổi. |
| 10 | Không random/mock/hard-code trong đường chính | PASS | `level1_core.py` không thêm hằng số; bảng duy nhất ở `level1_segmenter.py:412` (`git grep -c "DIACRITIC_FUSION = {" 3a78019 -- src/` ⇒ 1 dòng, 1 file). |
| 11 | Bảo mật | PASS | Không đụng API/WebSocket/CORS/credential. File trong §10 scope. `README.md` + 3 file ` D` của người dùng vẫn chưa commit (`git status`). `sha256sum checkpoints/alphabet_best.pt` bắt đầu `160e0c6825e365ba` (= v6). Không áp dụng mục agy. |
| 12 | So sánh công bằng / GATE | PASS (không áp dụng) | Không có gate trong K2; AC không đổi. |
| 13 | Kết luận vượt bằng chứng | PASS | Mục Giới hạn 14 đúng §4.2 F1/F3/F5 (vd "b,a,dấu sắc"+"â" → "bấ" khớp §4.3; "Không có luật uow → ươ" khớp F5; `--unikey-mode` mặc định bật khớp `level1_demo.py:1727`). Progress ghi rõ clip chỉ chữ "a", 0 sự kiện ghép. |

## Vấn đề (không chặn)

- THẤP-1 — AC-K3 phần chạy app (`tests/test_level1_unikey.py`, `TestClipEventsK3`) bỏ dấu cách `reason "word_gap"` khỏi phép quét "không sự kiện `model` nào có token ≠ dự đoán" (giả định 1 của coder). Hợp lý (dấu cách do khoảng nghỉ không có dự đoán, nguồn của nó không thuộc phạm vi K2), nhưng là diễn giải AC — planner xác nhận hoặc ghi vào plan.
- THẤP-2 — Clip D2 (`a_hau_A_001.mp4`) chỉ cho 1 nhãn "a" ⇒ lần chạy app của AC-K3 không có sự kiện `fusion`; ghép trên đường app thật (decoder → `on_label` → `_fuse`) chỉ được kiểm bằng chuỗi tạo có kiểm soát (`run_speller(..., "decoder")`). AC-K3 chỉ đòi "một lần chạy app trên clip D2" nên đạt; nếu muốn chứng cứ trên clip thật có ghép, cần clip ký "a" rồi "â"/"ô" (việc sau, không thuộc K2).
- THẤP-3 — Docstring đầu `tests/test_level1_unikey.py:4-6` còn câu của K1 "only the `unikey_mode=False` row is checked through Level1Speller here", mâu thuẫn với khối K2 ngay dưới. Mỹ thuật; sửa khi chạm file lần tới (R2).
- THẤP-4 (từ review K1, còn mở) — `["đ","i"]` + "đ" ⇒ nối thêm (`ORACLE_15_PAIRS` dòng cuối) là diễn giải "`[đ,i]` không áp" của §4.3; planner chưa xác nhận.
- Ghi chú — `_fuse` gọi `fusion_target`, hàm này ném `ValueError` khi danh sách tokens có token lạ (`token_kind`). `compose` (thuộc tính `text`) đã ném y hệt với cùng tokens, và nhãn model ⊂ 34 lớp của `compose` (`TestSpellerRandomK5` assert `len(vocab) == 34`), nên không có chế độ lỗi mới trong thực tế.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có. (THẤP-1 và THẤP-4 là việc planner xác nhận diễn giải.)
