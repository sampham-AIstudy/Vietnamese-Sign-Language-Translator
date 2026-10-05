# 15 — LẦN SỬA 5: bật chế độ classifier (quyết định (a) của người dùng) bằng config demo riêng, KHÔNG sửa test cũ

Có hiệu lực như nằm trong kế hoạch 15. Đè lên `docs/plans/15-lan-sua-4.md` ở đúng các chỗ nêu ở §0; mọi phần khác của 15 và các lần sửa 1–4
giữ nguyên. Người lập: vslt-planner (phiên cloud 2026-10-05), nhánh `cloud/2026-10-04-level1-rearm`, HEAD `281ece1`.

**CẦN NGƯỜI DÙNG: KHÔNG.** Người dùng đã chọn (a) "Classifier" (2026-10-05, ghi ở `docs/plans/15-progress.md` mục D4). Không đổi model mặc
định, không train, không đổi tiền xử lý.

## 0. Chỗ thay trong 15-lan-sua-4
| Chỗ | Thay/bổ sung bằng |
|---|---|
| §7 mục 2, nhánh (a) | Thực hiện bằng config demo riêng `configs/level1_demo_classifier.json` sinh bằng script (§3, bước S1–S2). `configs/level1_realtime.json` GIỮ `rearm_mode = "motion_pose"`; `--write-mode-config` vẫn chỉ dùng khi G1–G6 đạt hết (không đổi). |
| §4 dòng U1c | Lệnh thêm `--config configs/level1_demo_classifier.json` (thử "oo" bằng `n`). |
| §4 A3 | Giữ nguyên: A3 so TRƯỚC/SAU của A2 trên config mặc định (vẫn `motion_pose`). |
| §6 Giới hạn | Thêm các dòng §6 dưới (C1 ghi vào `docs/level1_desktop.md`, kèm lệnh demo). |

## 1. Mục tiêu và DoD
Buổi báo cáo chạy được chế độ classifier (chữ liên tiếp không rút tay) bằng MỘT lệnh có ghi nguồn, trong khi mọi test cũ giữ nguyên từng dòng
và vẫn xanh. Config demo phải tự nói nó là quyết định của người dùng khi G6 dấu thanh trượt, không phải gate đạt. Phục vụ DoD 2 (desktop),
DoD 6 (nguồn của hành vi ghi rõ), DoD 7 (`alphabet_clip_features` + checkpoint `a6311820…5b708a2` không đổi; E1 giữ).

## 2. Hiện trạng (đã kiểm tại `281ece1`)
- `configs/level1_realtime.json:58-62` `rearm_mode` = "motion_pose"; reason ghi "chỉ đổi bằng `--write-mode-config`" khi D4 đạt.
  sha256 hiện tại `cc178955…eb54b` = đúng config `on`/`off` mà D4 đã đo (`reports/level1_realtime_2026-10-05/rearm_check_d4.json`
  `configs.on.sha256`, `overrides = {"rearm_mode": "classifier"}`, commit JSON `a58df71`).
- D4: `gates.failed = ["G6"]`, `only_g6_tone_failed = true`; G6 dấu thanh on 0.8000 / off 0.8500 (cần ≥ 0.83), G6 chữ cái 0.9593 / 0.8798 đạt.
- `scripts/level1_rearm_check.py:849` `write_mode_config` từ chối khi `gates.all_pass` không true (đúng thiết kế lần sửa 4, giữ).
- Test cũ khóa config mặc định: `tests/test_level1_demo.py:67` (D2 chạy `level1_demo.py --source CLIP --headless` KHÔNG `--config`),
  `:98` (`config.path == "configs/level1_realtime.json"`), `:393` (AC-L chạy cùng lệnh), `:488` (`CODE_PATHS` ghim
  `configs/level1_realtime.json`, khớp `level1_demo.py:62`). Đổi tạm mặc định → 5 test cũ + 4 test mới (D8, C4, A2, K3 motion_pose) đỏ
  (`_work/_plan15/A_flip_try.log`, 15-progress D4).
- `src/inference/level1_core.py:94-99` `validate_level1_config` bỏ qua khóa bắt đầu bằng `_` (khóa chú thích) ⇒ config demo thêm được
  khóa đánh dấu mà không sửa `src/`.
- `level1_demo.py --config` đã có (`level1_demo.py:1011`); chế độ classifier qua `--config` đã kiểm ở AC-A1. Báo cáo JSON của app ghi
  `config.path`, `config.sha256`, `rearm_mode`.

## 3. Thiết kế — chọn (1): config demo riêng, sinh bằng script

**(1) Config demo riêng — CHỌN.** `configs/level1_demo_classifier.json` = bản sao `configs/level1_realtime.json` chỉ khác `rearm_mode` và hai
khóa chú thích, sinh bằng code từ JSON D4 đã commit. Lý do: (i) không chạm dòng nào của test cũ, `level1_demo.py`, `src/`, config mặc định;
(ii) đúng phạm vi quyết định (a) — "bật cho buổi báo cáo", không phải đổi mặc định của dự án; (iii) nguồn chặt: script chỉ ghi khi config gốc
có sha256 đúng bằng config `on` mà D4 đã đo ⇒ config demo CHÍNH LÀ cấu hình đã đo, không phải bản sao sửa tay.

**(2) Đổi mặc định + test cũ ghim motion_pose — BÁC. Đây LÀ sửa test cũ**, theo cả hai cách làm:
- đổi giá trị trong `configs/level1_realtime.json` rồi cho 5 test cũ `--config <file motion_pose khác>` ⇒ phải đổi assertion
  `tests/test_level1_demo.py:98` (đường dẫn config) — sửa assertion, bị cấm;
- đổi `DEFAULT_CONFIG` sang file classifier mới, 5 test cũ thêm `--config configs/level1_realtime.json` ⇒ assertion `:98` còn đúng, nhưng đầu
  vào của test đổi: AC-D2/AC-L đang khóa "lệnh mặc định của người dùng", sau đó khóa "lệnh có config tường minh" — nghĩa test bị thu hẹp,
  nằm ngoài ngoại lệ duy nhất của lần sửa 4 §4 (chỉ thêm khóa vào dict config dựng tay); thêm nữa `CODE_PATHS` (khóa ở `:488`) không còn
  phủ config mặc định mới. Ngoài ra (2) đổi config mặc định trên một gate TRƯỢT, trái reason của chính khóa `rearm_mode` và test D8.

**(3) Cờ `--rearm-mode` trong `level1_demo.py` — BÁC.** Sửa app (vùng D2) cho một việc config làm được; `config.sha256` trong báo cáo không còn
phản ánh hành vi; không có chỗ ghi quyết định người dùng cạnh tham số.

### 3.1 Lệnh mới của `scripts/level1_rearm_check.py`
`--write-demo-config OUT --rearm-json JSON` (cùng kiểu `--write-mode-config`). Hàm `write_demo_config(out_path, rearm_json)`:
1. Đọc JSON; TỪ CHỐI (RuntimeError, không ghi `OUT`, config gốc nguyên từng byte) khi: JSON chưa commit hoặc có thay đổi
   (`seg_report.committed_evidence_ref`); `mode != "decoder"`; `generated_by.code_dirty` khác false; `gates.all_pass` true (khi đó dùng
   `--write-mode-config`, đổi mặc định theo lần sửa 4); `gates.failed != ["G6"]` hoặc `only_g6_tone_failed` khác true hoặc G6 chữ cái
   `pass` khác true; `rearm_modes[gate_config] != "classifier"` hoặc `configs[gate_config].overrides != {"rearm_mode": "classifier"}`;
   config gốc (`configs[gate_config].path`) có thay đổi chưa commit hoặc sha256 hiện tại ≠ `configs[gate_config].sha256`; `OUT` trỏ tới
   chính config gốc.
2. Ghi `OUT` = config gốc, chỉ thay:
   - `_about`: "Demo config (plan 15 lần sửa 5): generated by scripts/level1_rearm_check.py --write-demo-config from <path> (sha256 …,
     commit …) = config '<gate_config>' measured in <json>@<commit>; only rearm_mode differs; do not edit by hand; the default config
     stays motion_pose".
   - `_user_decision` (khóa chú thích): `choice` "(a) classifier", `decided` "2026-10-05", `recorded_in` "docs/plans/15-progress.md (D4)",
     `plans` "docs/plans/15-lan-sua-4.md §7 item 2; docs/plans/15-lan-sua-5.md", `gate_failed` "G6 tone", `g6_tone` {on, off, rule} và
     `g6_letter` {on, off} ĐỌC bằng code từ JSON, `evidence` "<json>@<commit>", `note` "not a gate pass; tones: keys 1-5".
   - `rearm_mode`: value "classifier", source "design", reason "user decision (a) 2026-10-05 after step D4: classifier re-arm enabled for
     the demo although gate G6 tones FAILED (on X vs off Y, rule on >= off - 0.02) in <json>@<commit>; not a gate pass; tones: keys 1-5"
     (X, Y từ JSON). Hằng chữ của quyết định nằm trong script, khóa bằng test.
3. `validate_level1_config` trên kết quả trước khi ghi; trả `{"out", "rearm_mode": {old, new}, "base": {path, sha256, commit}}`.

## 4. Chia việc (mỗi bước 1 commit `15: <mã> …`; test viết TRƯỚC, ghi đỏ/xanh vào 15-progress; impact trước khi sửa symbol có sẵn,
detect-changes trước commit — GitNexus bị chặn trên cloud thì grep + `git diff --stat` và ghi lại như các bước trước)

| # | Bước | Nội dung | Giờ |
|---|---|---|---|
| 1 | **S1** | §3.1: `write_demo_config` + nhánh CLI `--write-demo-config` trong `scripts/level1_rearm_check.py`; test AC-W1, AC-W2 (lớp mới trong `tests/test_level1_rearm_check.py`, JSON tổng hợp, cơ chế commit giống lớp C5). | 1,0 |
| 2 | **S2** | Tại commit sạch: `PYTHONIOENCODING=utf-8 .venv/bin/python scripts/level1_rearm_check.py --write-demo-config configs/level1_demo_classifier.json --rearm-json reports/level1_realtime_2026-10-05/rearm_check_d4.json` → test AC-W3, AC-W4 → commit config + test + 15-progress. | 0,5 |
| — | U1c, C1, A3 | Như lần sửa 4 §4, với §0 trên. Lệnh demo cho C1/U1c: `level1_demo.py --source 0 --display-mirror --config configs/level1_demo_classifier.json`. | như cũ |

**Test cũ:** chỉ THÊM lớp/hàm mới. Không đổi, xóa hay dời dòng nào của test hiện có (kể cả 4 test của lần sửa 4). Không có ngoại lệ.

## 5. Tiêu chí chấp nhận (hợp đồng; coder không đổi)
- **AC-W1** (từ chối): mỗi trường hợp từ chối ở §3.1 bước 1 có một test: RuntimeError, `OUT` không được tạo (hoặc nguyên byte nếu có
  sẵn), config gốc nguyên byte. Bắt buộc có: JSON chưa commit; `all_pass` true; gate khác G6 trượt; G6 chữ cái trượt; `code_dirty` true;
  sha256 config gốc khác JSON; `OUT` = config gốc.
- **AC-W2** (thành công, JSON tổng hợp hợp lệ): `load_level1_config(OUT)` qua; mọi khóa trừ `rearm_mode`, `_about`, `_user_decision` bằng
  config gốc (`json.dumps(..., sort_keys=True)`); `rearm_mode.value == "classifier"`; reason chứa "user decision (a)", "G6", đường dẫn JSON
  @commit và hai số dấu thanh đúng như JSON; `_user_decision.gate_failed == "G6 tone"`; config gốc nguyên byte.
- **AC-W3** (file thật, sau S2): `configs/level1_demo_classifier.json` đã commit, qua `load_level1_config`, `rearm_mode` "classifier"; mọi khóa
  trừ ba khóa trên bằng `configs/level1_realtime.json`; `_user_decision.evidence` trỏ JSON đã commit có `gates.only_g6_tone_failed` true và
  `configs.on.sha256` == sha256 hiện tại của `configs/level1_realtime.json`; config mặc định vẫn `motion_pose`.
- **AC-W4** (lệnh demo, bỏ qua khi thiếu dữ liệu như D2): `level1_demo.py --source CLIP --headless --config configs/level1_demo_classifier.json
  --out-json …` mã thoát 0, báo cáo `rearm_mode` "classifier", `config.path` "configs/level1_demo_classifier.json", có chặng `window_classify`.
- **AC-W5** (không sửa test cũ): `git diff 281ece1..HEAD --numstat -- tests/` cột xóa = 0 cho mọi file; `git diff 281ece1..HEAD --
  configs/level1_realtime.json level1_demo.py src/` rỗng.
- **AC-W6** (hồi quy): 12 module Level 1 + AC-E1 như các bước trước, `python -m unittest` OK, chỉ `test_u1_summary` bỏ qua; AC-S18/S18b,
  AC-E1, K4, A2 bằng hệt; guard nguồn `known=9 allowed=36`; sha256 checkpoint không đổi.

## 5b. Phạm vi file
```scope
scripts/level1_rearm_check.py
configs/level1_demo_classifier.json
tests/test_level1_rearm_check.py
tests/test_level1_demo.py
docs/plans/15-progress.md
docs/level1_desktop.md
```
(`tests/test_level1_demo.py` chỉ để THÊM lớp AC-W4; `docs/level1_desktop.md` thuộc C1.) Độ khó: S; vùng nhạy cảm: có, chỉ config hành vi
realtime (không đổi tiền xử lý, model, checkpoint). KHÔNG đụng: `configs/level1_realtime.json`, `level1_demo.py`, `src/`, các file cấm của
prompt cloud §3 (kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`, `tests/test_backend_source_guard.py`, `.claude/`,
`docs/prompts/`, `docs/STATE.md`). File tạm: `_work/_plan15/`. Gợi ý model coder: S1, S2 gemini/high.

## 6. Rủi ro (+ Giới hạn cho docs/level1_desktop.md ở C1)
- **Lệch config:** sau này đổi bất kỳ giá trị nào của `configs/level1_realtime.json` ⇒ AC-W3 đỏ CÓ CHỦ Ý (config demo không còn là cấu hình
  đã đo). Cách đúng: chạy lại lệnh D4 với config mới, rồi S2; không sửa tay config demo.
- **`code_dirty` của app không phủ config demo** (`CODE_PATHS` bị test L3 ghim): báo cáo app vẫn ghi `config.path` + `config.sha256`; reviewer
  đối chiếu với `git show HEAD:configs/level1_demo_classifier.json | sha256sum`.
- **Quên `--config`:** lệnh mặc định chạy `motion_pose`; báo cáo JSON ghi `rearm_mode`. C1 đặt lệnh demo lên đầu mục chạy.
- **source "design"** của `rearm_mode` trong config demo nghĩa là "quyết định", không phải đo; reason và `_user_decision` nói rõ (validator chỉ
  nhận "design"/"calibrated", không mở rộng ở lần sửa này).
- Giới hạn thêm (số từ `rearm_check_d4.json@a58df71`): "Chế độ demo = classifier theo quyết định người dùng; gate G6 dấu thanh TRƯỢT (0.80 so với
  0.85 của chế độ cũ) ⇒ dấu thanh dùng phím 1–5"; "Trên 46 clip QIPEDC (ngoài train, chỉ báo cáo) chế độ classifier phát nhãn trọn clip ở
  0.5435 so với 0.7391 của chế độ cũ"; "Chữ lặp (oo, ee) cần phím `n` hoặc rút tay"; "Kiểm trên chuỗi ghép từ clip train — kiểm logic, không
  phải độ chính xác".

## 7. Điểm dừng
Không có điểm dừng bắt buộc khi BẮT ĐẦU (quyết định đã có, không đổi model/tiền xử lý). Điểm dừng cho coder (ghi 15-progress, báo planner):
1. Script từ chối trên JSON D4 thật ở S2 (vd sha256 config gốc khác JSON) ⇒ DỪNG; không sửa tay config demo, không chạy lại D4 khi chưa có kế hoạch.
2. Bất kỳ test cũ nào đỏ, hoặc cần sửa dòng test cũ / `level1_demo.py` / `src/` / `configs/level1_realtime.json` ⇒ DỪNG.
3. Muốn classifier thành mặc định (lệnh mặc định, web) hoặc chỉnh `cls_*` ⇒ lần sửa kế hoạch mới + gate mới, không làm trong lần này.

## Dòng con trỏ (orchestrator chèn vào đầu docs/plans/15-lan-sua-4.md)
> **LẦN SỬA 5 (2026-10-05):** người dùng chọn (a); classifier được bật bằng config demo riêng `configs/level1_demo_classifier.json` (sinh bằng `--write-demo-config` từ JSON D4, ghi rõ G6 dấu thanh trượt), config mặc định giữ `motion_pose`, test cũ không đổi; bước S1 → S2 — đọc `docs/plans/15-lan-sua-5.md` trước C1/U1c.
