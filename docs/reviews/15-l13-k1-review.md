# Review 15 lần sửa 13 — bước K1 (Unikey `fusion_target`)

- Phạm vi: commit mã `82eebcd` ("15: L13-K1 module Unikey fusion_target + test bảng §4.3 (AC-K1 phần hàm, AC-K5)"), commit tiến độ `0607a02`
  (chỉ `docs/plans/15-progress.md`). Cha `4d32e17`. Reviewer chạy ở HEAD `13d8033` (sau `82eebcd` chỉ đổi docs/ledger nên mã giống hệt).
- Coder: vslt-coder-claude (không phải agy, không có mục kiểm agy).
- Hợp đồng: `docs/plans/15-lan-sua-13.md` §4.1–§4.3, §8 hàng 7 (K1) / 8 (K2), §9 AC-0, AC-1, AC-K1…AC-K6, §10.

## Kết luận: APPROVE

Mã `src/inference/level1_unikey.py` đúng F1–F6 trên mọi ca reviewer thử; mọi dòng §4.3 có mặt nguyên văn trong test và pass; 0 dòng xóa, không
đụng file ngoài phạm vi. Không còn FAIL. Có 3 lỗ hổng test (đột biến sống, mức TRUNG BÌNH/THẤP) và 1 assert luôn đúng — mã đúng, chỉ thiếu
test khóa, nên ĐƯA VÀO K2 bắt buộc (mục cuối), không cần bước sửa riêng.

## Bảng kiểm 1–13

| # | Mục | KQ | Bằng chứng |
|---|---|---|---|
| 1 | Đúng kế hoạch / test thật | PASS (phạm vi K1) | `git diff --numstat 4d32e17..82eebcd`: `68 0 src/inference/level1_unikey.py`, `250 0 tests/test_level1_unikey.py` — đúng §8 hàng 7. Bảng: `level1_unikey.py:29` import `DIACRITIC_FUSION` từ `level1_segmenter.py:412-418`; `test_one_table_15_pairs` (`tests/test_level1_unikey.py:141-145`) khóa `assertIs` + bằng 15 cặp. Đối chiếu §4.3 từng dòng với `tests/test_level1_unikey.py:30-64`: đủ ([b,a]+ô, [b,o]+ư, [b,e]+ô, [b,u]+ư, [d]+đ, NGOẠI LỆ [b,u]+ơ -> [b,u,ơ] "buơ", thuở, quơ, huơ, khuơ, [u]+ơ -> [ư], [u]+ơ+ơ -> "ươ", ngươ, quâ, giâ, giê, [b,a,dấu sắc]+â -> [b,â,dấu sắc] "bấ", [b,a," "]+â -> [b,a," ",â], []+â -> [â], unikey_mode=False [b,a]+â -> [b,a,â]); 15 cặp đủ ở `:30-46` + `test_every_pair_on_b_syllable_except_u_horn` `:147-156`. Dòng unikey_mode=False qua `on_result` VÀ `on_label` (`:123-135`) phân biệt được (M0 với unikey_mode=True sẽ ghép, `level1_core.py:362,391`). Ghi chú: nửa Level1Speller của AC-K1 và AC-K5 chưa có (điểm 3 dưới, hợp lệ, chuyển K2); `:242-244` là assert luôn đúng (THẤP-1). |
| 2 | Tự chạy lại test | PASS | `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_level1_unikey tests.test_level1_core` -> `_work/_plan15_l13/review_k1_unikey_core.log`: `Ran 70 tests` `OK`. Toàn bộ test_level1_* + `tests.test_backend_source_guard` (lệnh như coder) -> `_work/_plan15_l13/review_k1_full.log`: `Ran 665 tests in 409.496s` `OK (skipped=1)`, `[DoD7-guard] known=9 allowed=36` — khớp coder (`k1_green_full.log`: Ran 665 OK skipped=1). |
| 3 | Test không bị sửa/skip/nới | PASS | numstat `tests/`: chỉ file mới, cột xóa 0; file mới không có `skip`. |
| 4 | Nguồn gốc dữ liệu | PASS (không áp) | Logic thuần trên token điều khiển; không train/đánh giá, không dữ liệu. |
| 5 | Rò rỉ split | PASS (không áp) | Không có split. |
| 6 | VAL/TEST | PASS (không áp) | Không chọn model. |
| 7 | Số liệu truy được | PASS | Không có số liệu khoa học; 15-progress chỉ dẫn log `_work/` (Ran/OK) — reviewer tái tạo được. |
| 8 | Cỡ mẫu/CI | PASS (không áp) | AC-K5: 200 chuỗi seed cố định `20261008` (`:201-203`), có kiểm `n_fused > 0` và `n_kept_f3 > 0` (`:245-246`) nên không rỗng. |
| 9 | Nhất quán train–realtime | PASS (không áp ở K1) | Hàm chưa nối vào app; K2 nối cả `_apply` và `on_label` (AC-K1 nửa Speller). |
| 10 | Không random/mock/hard-code trong đường chính | PASS | `random` chỉ trong test (seed cố định). Module chỉ có hằng luật F3 `SYLLABLE_INITIAL_ONLY` (`level1_unikey.py:32`). Test guard DoD7 trên file mới = 0 phát hiện (`:190-195`). |
| 11 | Bảo mật | PASS | Không đụng API/WebSocket/CORS/credential; token lạ -> `ValueError` qua `token_kind` (`level1_unikey.py:49,63`); prediction không phải str -> None (`:44-45`). |
| 12 | So sánh công bằng / GATE | PASS (không áp) | Không có GATE ở K1. |
| 13 | Kết luận vượt bằng chứng | PASS (có ghi chú) | 15-progress khai đúng thực tế; docstring test (`:7`) nói AC-K5 "text == compose" nhưng phép so text ở `:242-244` là đồng nhất thức (THẤP-1) — coder đã ghi giả định (2) rằng bản qua Speller thuộc K2. |

AC-0: tiêu đề `^15: L13-` đạt; 2 file trong §10 đạt; `git diff --stat 4d32e17..13d8033 -- backend/main.py realtime_demo.py configs/ src/data src/inference/fingerspelling_compose.py README.md src/inference/level1_core.py src/inference/level1_segmenter.py level1_demo.py` rỗng; `sha256sum checkpoints/alphabet_best.pt` = `160e0c6825e365ba...`; file LF (0 CR trong diff). Thay đổi chưa commit của người dùng (`README.md`, 3 file bị xóa, untracked) không bị đụng.

## Soi theo điểm được giao

1. Diff: đúng 2 file mới (+68, +250); không sửa `level1_core`/`level1_segmenter`/`level1_demo`; bảng là đúng đối tượng ở `level1_segmenter.py`
   (test `assertIs`), 15 cặp, không thêm/bớt. Bảng trùng ở `level1_core.py:256-262` vẫn còn (xóa là việc K2, AC-K4).
2. `fusion_target` (`level1_unikey.py:39-68`):
   - F1 `:47-56`: dò ngược, bỏ qua dấu thanh, dừng ở chữ cái đầu tiên gặp hoặc SPACE: gốc = chữ cái cuối âm tiết, sau nó chỉ có dấu thanh. Đạt.
   - Chữ cuối không là khóa / dự đoán không thuộc bảng -> None `:57-60`. Đạt.
   - F3 `:61-67`: (u,ơ) chỉ ghép khi không có chữ cái nào trước `u` trong cùng âm tiết (dừng ở SPACE); `q` là chữ cái nên "quơ" giữ. (u,ư) không
     thuộc `SYLLABLE_INITIAL_ONLY` nên luôn ghép. Đạt.
   - F4/F5: suy ra từ F1–F3 (ư, i không là khóa) — test `:55-58`. Đạt.
   - F6: hàm trả (index, target, rule), không sửa `tokens`; người gọi thay 1 phần tử nên số token và token dấu thanh giữ nguyên; K5 kiểm `:234-237`. Đạt.
3. Dời nửa Speller của AC-K1 + AC-K5 sang K2: §8 hàng 7 giao "AC-K1, K5" cho K1, nhưng phần qua `Level1Speller` CHỈ đạt được sau khi nối (K2);
   viết sẵn ở K1 sẽ đỏ ở commit K1 và vi phạm AC-1 ("test mới OK"). Dời là bắt buộc về logic: CHẤP NHẬN, với điều kiện K2 làm đủ (mục cuối).
   Chưa thêm `level1_unikey.py` vào `PLAN15_FILES` (`tests/test_level1_guard.py:26`): chấp nhận — §5.4 E3 / AC-G5 yêu cầu 3 file nhưng không gán
   bước; K1 bù bằng test quét guard trực tiếp (`:190-195`). K2 phải thêm (chỉ THÊM dòng).
4. Đột biến:
   - Coder `k1_mut_run.log`: BASE OK, M1–M10 đều RED (đã đọc log).
   - Reviewer (bản trích `git archive 82eebcd src tests configs` vào `_work/_plan15_l13/rv_k1_tree`, đã xóa; script `_work/_plan15_l13/rv_k1_mut.py`,
     log `_work/_plan15_l13/review_k1_mut.log`; bản gốc khôi phục `cmp` khớp, BASE sau cùng OK):
     - R2 "cho phép chữ cái đứng sau gốc" (gốc = chữ cái khóa cuối của âm tiết): RED (failures=2). Đạt.
     - R5 F3 bỏ qua mọi phụ âm trừ `t`: RED (failures=1). Đạt.
     - R1 F3 chỉ nhìn token NGAY trước `u` (không dò qua dấu thanh): SỐNG. Ca phân biệt `["t","dấu sắc","u"]`+ơ — đúng spec phải None ("tuớ"),
       đột biến ghép thành "tứ". Điều kiện K5 `:218` dùng đúng điều kiện yếu `before[-2]` nên không bắt được. -> TB-1.
     - R3 F3 coi dấu thanh trước `u` là phụ âm đầu: SỐNG. Ca `["dấu sắc","u"]`+ơ — `u` là chữ cái đầu nên phải ghép `(1,"ư","u+ơ")`. -> THẤP-2.
     - R4 bỏ chuẩn hóa NFC của dự đoán: SỐNG — giả định (5) của coder không có test (vd "ô" dạng NFD). -> THẤP-3.
5. Test: xem hàng 2.

## Vấn đề (theo mức)

- CAO: không có.
- TRUNG BÌNH
  - TB-1 `tests/test_level1_unikey.py:168-172, 218`: F3 chưa được khóa khi có token dấu thanh giữa phụ âm đầu và `u` (đột biến R1 sống). Mã đúng
    (`level1_unikey.py:62-67`), thiếu test. Sửa ở K2: thêm `fusion_target(["t","dấu sắc","u"],"ơ") is None` và cho điều kiện K5 `:218` dò mọi
    token trước `u` trong âm tiết (không chỉ `before[-2]`).
- THẤP
  - THẤP-1 `tests/test_level1_unikey.py:242-244`: `text = compose(toks)["text"]; assertEqual(text, compose(list(toks))["text"])` luôn đúng,
    không kiểm gì. Phần "text == compose(tokens)" của AC-K5 chỉ có nghĩa với text/sự kiện của `Level1Speller` -> K2.
  - THẤP-2: thiếu ca `["dấu sắc","u"]`+ơ -> `(1,"ư","u+ơ")` (R3 sống).
  - THẤP-3: thiếu ca NFD cho dự đoán/token (R4 sống).
  - THẤP-4 (diễn giải hợp đồng): "`[đ,i]` không áp" (§4.3) được coder hiểu là `[đ,i]`+đ nối thêm (`:46`) — nhất quán F1; thêm `[b,d]`+đ -> `[b,đ]`
    (`:147-156`). Planner xác nhận nếu ý khác.

## Bắt buộc ở K2

1. AC-K1 nửa Speller: MỌI dòng §4.3 (cả 15 cặp và dòng `[đ,i]`) qua `Level1Speller(accept, unikey_mode=True)` bằng CẢ `on_result` VÀ `on_label`,
   so tokens + `text` với cùng oracle nguyên văn (dùng lại `ORACLE_15_PAIRS`/`ORACLE_SPELLING`, không sinh oracle từ mã). Lưu ý `_apply` xét
   luật thay dấu thanh trước luật ghép (`level1_core.py:358-362`) — dòng "thuở" phải ra đúng.
2. AC-K5 qua Speller: 200 chuỗi seed cố định, sau MỖI thao tác `text` của Speller == `compose(speller.tokens)["text"]`, mỗi lần ghép giữ số token
   dấu thanh; thay assert luôn đúng `tests/test_level1_unikey.py:242-244` bằng phép so này (file mới của plan này).
3. Khóa đột biến R1/R3/R4 (TB-1, THẤP-2, THẤP-3); chạy lại R1–R5 + M1–M10 sau khi nối, ghi log.
4. AC-K4: xóa `DIACRITIC_FUSION` ở `level1_core.py:256-262` để `grep -rc "DIACRITIC_FUSION = {" src/` tổng = 1; `level1_core` gọi `fusion_target`
   ở CẢ `_apply` và `on_label` (không giữ nhánh `tokens[-1]` cũ).
5. AC-K3: sự kiện `source "fusion"` đủ khóa F7 (`prediction`, `confidence`, `replaced`, `index`, `rule`, ...); `on_label` trả `action "replace"`;
   quét bảng §4.3 + một lần chạy clip D2: không sự kiện `source "model"` nào có `token` khác dự đoán.
6. AC-K2/AC-K6: `tests/test_level1_core.py:917-954`, `tests/test_level1_lan_sua_12.py:92-131` xanh không sửa; `unikey_mode=False` = M0.
7. Guard: THÊM `src/inference/level1_unikey.py` vào `PLAN15_FILES` (`tests/test_level1_guard.py:26`, 0 dòng xóa; E3), guard `known=9 allowed=36`.

## CẦN NGƯỜI DÙNG QUYẾT ĐỊNH

Không có. (THẤP-4 là việc planner xác nhận diễn giải, không cần người dùng.)
