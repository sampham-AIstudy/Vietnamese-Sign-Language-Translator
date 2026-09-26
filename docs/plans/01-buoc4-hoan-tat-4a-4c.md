# Kế hoạch 01 — Hoàn tất Bước 4a → 4b → 4c (đến ĐIỂM DỪNG sau 4c)

> **CẦN NGƯỜI DÙNG — ở CUỐI việc, không phải lúc bắt đầu.** Việc này kết thúc tại ĐIỂM DỪNG BẮT BUỘC "sau bước 4c"
> (autopilot.md §5). Sản phẩm cuối: `reports/step4_2026-09-26/REPORT.md` + `PROPOSAL_4c.md` gửi người dùng.
> Người dùng quyết định A/B. KHÔNG đổi model mặc định của backend, KHÔNG train thêm, KHÔNG sửa preprocessing.
> Trước điểm dừng thì không cần người dùng: không cần dữ liệu mới, không đụng thay đổi chưa commit của người dùng,
> không có hành động không hoàn tác. Lần sửa 1 (dưới đây) KHÔNG thêm điểm dừng nào trước khi code; nó thêm câu hỏi
> cho người dùng vào điểm dừng cuối (§7).

Nhánh `feat/vslt-complete`. Lập kế hoạch lần đầu tại HEAD `27233f6`; lập lại (Lần sửa 1) tại HEAD `8c08845`.
Ngày 2026-09-26.

---

## 0. Lần sửa 1 (sau review `docs/reviews/01-review.md`, CHANGES_REQUESTED, vòng CODE↔REVIEW 1/3)

Commit của coder đã có và GIỮ NGUYÊN: `72abc13`, `f4729ff`, `8c08845`. Không viết lại lịch sử (không amend, rebase,
reset, force); mọi sửa đổi là commit MỚI trên `8c08845`.

### 0.1 Nguyên nhân gốc

**M1 — FAIL mục 13 (kết luận vượt bằng chứng).** Lỗi nằm ở kế hoạch trước, coder chỉ làm theo:
1. §3.4 mục 5 (nội dung 4c) chỉ yêu cầu số KẾT QUẢ (Top-k, McNemar, cỡ mẫu). Nó không yêu cầu chẩn đoán xem hai
   model so sánh có được tối ưu ngang nhau không: số epoch đã chạy, số bước tối ưu, train top-1, lr cuối.
   Dữ liệu cho việc này có sẵn trong `runs/*/history.json` (đã commit), nhưng kế hoạch không đưa nó vào đầu vào.
   Theo review, model từ điển dừng ở epoch 48 với train top-1 (trainer ghi) 34.21% và lr 1.5625e-05. Model gộp đạt
   95.47%, và số bước tối ưu của nó lớn hơn nhiều bậc. Các số này phải được script sinh lại, không lấy từ review.
2. §6 (Rủi ro) chỉ nêu hai yếu tố gây nhiễu cho 4c: không gian nhãn và lượng dữ liệu. Nó bỏ sót quỹ tối ưu / mức
   khớp train. Cả hai model dùng CÙNG lệnh train (epochs 120, patience 20, batch 64, ReduceLROnPlateau theo VAL loss).
   Model từ điển có ít clip train nên có ít bước mỗi epoch. VAL của nó chỉ gồm 105 clip QIPEDC, nên lr giảm và
   dừng sớm theo một tín hiệu VAL rất nhiễu.
3. Bước 6 (PROPOSAL) không bắt buộc nêu PHẠM VI của thứ 4c đã đo. 4c chỉ đo một cách tách: train từ đầu, chỉ dùng
   QIPEDC, cùng công thức với model gộp. `scripts/train_unified.py` không có tùy chọn khởi tạo từ trọng số. Vì không có
   ràng buộc này, PROPOSAL khái quát thành "Tách ra thì 'Ký từ' mất toàn bộ dữ liệu VSL-GH". Câu đó chỉ đúng cho cách
   tách train-từ-đầu. AC5 cũng chỉ kiểm con số, không kiểm phạm vi của khẳng định.

**M2 — REPORT nói "cắt đoạn nghỉ KHÔNG được công nhận" nhưng không nói hệ quả.** PREREG (dòng 20–21) chỉ quy định
khi nào cắt nghỉ được "công nhận". Nó không nói phải làm gì khi cắt nghỉ không được công nhận. Kế hoạch §3.4 mục 4
(e) chỉ yêu cầu (i)(ii)(iii), không yêu cầu nêu cấu hình trim của run được chọn. Mọi run ứng viên (H-keepz, H-dropz,
H-keepz-360) đều train với `trim=true`, vì trim nằm trong `HARMONIZED_DEFAULT`. Do đó run được chọn VẪN cắt nghỉ, và
đường live muốn khớp với nó thì phải cắt nghỉ. Người đọc câu "không được công nhận" dễ hiểu nhầm là bước cắt nghỉ đã
bị bỏ.

**M3 — thăm dò (b) trộn tỷ lệ "rơi vào lớp chỉ-VSL-GH" với độ chính xác.** Kế hoạch §3.4 mục 5 (b) định nghĩa tỷ lệ
trên MỌI dự đoán. Nhưng dự đoán đúng thì tất nhiên rơi vào lớp của nguồn đúng, nên tỷ lệ này lẫn độ chính xác vào.
Kế hoạch trước không yêu cầu cột "chỉ tính dự đoán sai" và không yêu cầu tỷ lệ nền (tỷ lệ lớp chỉ-VSL-GH trong không
gian nhãn).

**M4 — quy trình.** Bước 7–8 chưa làm: chưa sinh lại với `--review-file`, chưa có dòng progress_log. Cả ba commit
đều chạy `detect-changes --scope staged`, trong khi CLAUDE.md và AC8 yêu cầu `--scope all`.

**Lỗi của kế hoạch trong AC3.** AC3 yêu cầu chạy lại ra thư mục tạm rồi dùng `cmp` để thấy byte-giống. Điều này
không thể đạt được, vì chuỗi lệnh ghi trong header và trong `generated_by.command` chứa đường dẫn `--out`. Coder đã
so hai lần chạy tại chỗ. Xem AC3 đã sửa: cách kiểm mới vẫn chặt như ý định ban đầu, không nới.

### 0.2 Thay đổi so với kế hoạch trước (tóm tắt; chi tiết ở §3–§7)
- §2: sửa ghi chú sai về `REPORT_partial.md`. File này untracked, không có bản git, và "@3698e91" là sai. Thêm hiện
  trạng về `history.json`, trainer, và file `.pt` chưa bị gitignore.
- §3.2: thêm các hàm thuần `training_fit`, `steps_per_epoch`, `train_cmd_diff`, `pred_origin` (thêm cột chỉ-sai
  và tỷ lệ nền), `trim_consequence`, `prereg_header_times`.
- §3.4: thêm mục 4c "Phạm vi so sánh và mức khớp train", câu hệ quả cắt nghỉ sinh từ `run_config`, thêm cột chỉ-sai
  cho thăm dò (b), câu về giờ ghi ở tiêu đề PREREG so với giờ commit, và sửa chữ "Augmentation" bị lặp.
- §4: thêm các bước R0–R6 (các bước 1–8 cũ đã xong, trừ phần 7–8).
- §5: thêm AC1 ca 16–23, AC4 k–o, AC5b (test chặt hơn, THÊM test mới, không sửa test cũ), AC9 (lần sinh cuối chỉ
  khác ở mục Review). Sửa AC3 (lý do ở trên), AC6 (`REPORT_partial.md`, file review), AC8 (`--scope all`). Không bỏ
  và không nới tiêu chí nào.
- §6: thêm rủi ro về quỹ tối ưu / mức khớp train, và việc train top-1 do trainer ghi không phải độ chính xác sạch.
- §7: thêm các câu hỏi cho người dùng tại điểm dừng cuối (train lại model từ điển, seed 360 px, cắt nghỉ ở live,
  `REPORT_partial.md`, gitignore `.pt`). Không thêm điểm dừng trước khi code.

---

## 1. Mục tiêu và DoD

**Mục tiêu.** Sinh báo cáo cuối của Bước 4 (4a, 4b, 4c) hoàn toàn bằng script, từ các file kết quả đã có. Không train
thêm. Báo cáo phải áp đúng luật đã đăng ký trước trong `PREREGISTRATION.md`, bổ sung các mục `buoc4_5.md` yêu cầu mà
script còn thiếu, và truy nguồn được mọi con số (lệnh + commit). Sau đó viết đề xuất 4c (A tách / B gộp, ≤ 1 trang).
Đề xuất phải dựa trên bằng chứng và **nói đúng phạm vi của thứ đã đo**. Rồi DỪNG.

**DoD phục vụ.**
- DoD 3 (tiền đề): kết luận 4c là căn cứ để người dùng chọn cấu trúc/model mặc định cho Cấp 2. Việc đổi model mặc định
  là việc sau, chỉ làm khi người dùng đã duyệt.
- DoD 9 (tiền đề): số liệu cho mục "Giới hạn" (lối tắt nguồn, cỡ mẫu, rò rỉ, mức khớp train) nằm trong JSON máy đọc
  được (`step4_results.json`), để README/EVALUATION sinh tự động về sau.
- DoD 10 (một phần): vslt-reviewer chạy trên thay đổi của việc này VÀ trên các commit trước quy trình 3 agent.

---

## 2. Hiện trạng

### 2.1 File kết quả có trên đĩa
- `reports/step4_2026-09-26/runs/{run_keepz, run_dropz, run_keepz_seed43, dict_keepz, run_keepz_360,
  run_keepz_notrim, dict_keepz_360}/`: mỗi thư mục có `metrics.json` (có `val_by_source`, `run_config`,
  `train_samples_per_class_hist`, `split_integrity`), `history.json` (**đã commit**; mỗi epoch có `epoch`,
  `train_loss`, `train_top1`, `val_loss`, `val_top1`, `lr`, `time_sec`), `test_logits.npz`, `stgcn_unified_best.pt`,
  `test_predictions.csv`, `train.log`. `*.npz`, `*.pt`, `*.log` bị gitignore.
- Log kernel v1/v2/v3 và `reports/unified_run_2026-09-25/vsl-train-unified.log`: chứa lệnh train đầy đủ, trong đó có
  `--batch-size`, `--epochs`, `--patience`, `--seed` (xem REPORT §1.1).
- `REPORT_partial.md`: **untracked**, không có bản nào trong git. Ghi chú "@3698e91" ở kế hoạch trước là SAI, vì
  3698e91 chỉ sửa handoff. Việc này không sửa, không xóa, không `git add` file này (chưa rõ ai tạo, nên hỏi người
  dùng ở §7).
- `PREREGISTRATION.md`: KHÔNG được sửa. Tiêu đề phần bổ sung ghi "12:30", nhưng commit `9b0ade1` có giờ 12:13:24
  (theo review). Chỉ được nêu điểm lệch này trong REPORT, và câu đó phải sinh bằng script.
- `reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt`: untracked và KHÔNG bị gitignore (`.gitignore:75` chỉ
  phủ `step4_*`). Việc này chỉ ghi nhận. Không sửa `.gitignore`, trừ khi có `.pt` đang bị staged hoặc đã commit (R0).

### 2.2 Mã liên quan (tại `8c08845`)
- `scripts/report_step4.py`:
  - `_hist_summary` (422–426): số clip train và hist lấy từ `metrics.json`.
  - `build` (438–834). Khối 4c ở 649–703; thăm dò (b) là `pred_split` lồng trong `build` (675–680), chỉ tính trên
    MỌI dự đoán. Khối cấu hình hài hòa ở 600–614: `aug` lấy cả dòng "Augmentation (training only): …" từ docstring.
    Giới hạn ở 770–812. PREREG chỉ có danh sách commit (760–764).
  - `render` (864–): dòng 961 in `f"- Augmentation: {…}"`, nên ra chữ lặp "Augmentation: Augmentation (training only)".
  - Chưa đọc `history.json`.
- `scripts/train_unified.py`: DataLoader train dùng `WeightedRandomSampler(num_samples=len(train_ds))` (192–196),
  không `drop_last`, nên số bước/epoch = ceil(n_train / batch). Argparse (125–142) KHÔNG có tùy chọn khởi tạo từ trọng
  số hay resume, nên mọi run đều train từ khởi tạo ngẫu nhiên.
- `src/training/trainer.py`: `ReduceLROnPlateau(mode="min", factor=0.5, patience=5, min_lr=1e-6)` bước theo
  `val_metrics["loss"]` (57–63, 177–178). Dừng sớm theo `val_top1` với `patience` (197–236). `train_top1` được đo
  trên batch đã augment, ở chế độ `model.train()` (87–126), nên **không** phải độ chính xác sạch trên tập train.
  `lr` ghi trong history là lr TRƯỚC khi scheduler bước ở epoch đó (174).
- `tests/test_report_step4.py`: 38 test. AC5 ở dòng 411–446. `test_every_number_is_in_report` so số không theo ngữ
  cảnh, nên một số nguyên có thể khớp nhầm vào chuỗi sha256.
- Các phần khác của §2.2 cũ (`harmonized.py`, `report_unified.py`, `shortcut_85.py`, `landmark_extractor.py`) không
  đổi và vẫn ngoài phạm vi sửa.

### 2.3 Còn thiếu (sau review)
1. Chẩn đoán mức khớp train và quỹ tối ưu của hai model 4c, sinh từ `history.json` + lệnh train (M1).
2. Phạm vi của kết quả chính 4c, nêu trong REPORT (sinh từ dữ liệu) và trong PROPOSAL (M1).
3. Câu hệ quả cắt nghỉ, sinh từ `run_config.trim` của run được chọn (M2).
4. Thăm dò (b): cột "chỉ tính dự đoán sai" + tỷ lệ nền của không gian nhãn (M3).
5. Giờ ghi trong tiêu đề PREREG so với giờ commit (góp ý nhỏ); chữ "Augmentation" bị lặp (góp ý nhỏ).
6. Test AC5 theo ngữ cảnh (góp ý nhỏ).
7. REPORT sinh lại với `--review-file`; dòng progress_log; `detect-changes --scope all` (M4).

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu
```
runs/*/metrics.json ──► (VAL) balanced_val ──► choose_z ──► choose_resolution ──► chosen run
                                                   └──► trimming_verdict (ghép cặp theo run_config)
                                                   └──► trim_consequence(chosen run_config)            [MỚI, M2]
runs/*/test_logits.npz + .pt(label_map) + data/splits/unified/{train,val,test}.csv
      ──► hits@1/5/10 theo nhóm (group_rows) + cross-source + seed spread
      ──► pred_origin (mọi dự đoán / chỉ dự đoán sai / tỷ lệ nền)                                  [MỚI, M3]
chosen run_config ──► pick_dict_run (khớp hand_z, process_height, trim) ──► 4c
runs/{dict_used, chosen}/history.json + lệnh train (log kernel) + metrics.json (n_train)
      ──► training_fit + steps_per_epoch + train_cmd_diff ──► 4c.fit_and_scope                     [MỚI, M1]
PREREGISTRATION.md (tiêu đề "Added … HH:MM") + git log ──► prereg_header_times                     [MỚI]
4a/4b JSON (bản chạy lại có provenance) ──► bảng bộ phân loại nguồn + so khớp với bản cũ
vsl-train-*.log ──► repo commit, lệnh, seed, thời lượng GPU mỗi kernel
                ──► step4_results.json ──► REPORT.md (render từ cùng dict)
```
Không bước nào chạy lại model, trên TEST hay trên train. Chẩn đoán mức khớp chỉ đọc `history.json` mà kernel đã ghi.

### 3.2 Hàm thuần (đã có từ lần trước: giữ nguyên hành vi; MỚI: thêm ở Lần sửa 1)
Đã có, giữ nguyên hành vi: `balanced_val`, `choose_z`, `choose_resolution`, `trimming_verdict`, `pick_dict_run`,
`topk_hits`, `align`, `mcnemar_exact`, `parse_kernel_log`, `json_provenance`, `compare_legacy`.

MỚI (coder được đặt tên khác, KHÔNG được đổi hành vi mô tả dưới đây):
- `steps_per_epoch(n_train: int, batch_size: int | None) -> int | None` = ceil(n_train / batch_size); trả `None` nếu
  thiếu batch_size.
- `training_fit(history: list[dict], n_train: int, batch_size: int | None) -> dict` trả:
  `epochs_run` (số phần tử history); `best_epoch` (theo đúng luật của trainer: `val_top1` lớn nhất, hòa thì
  `val_loss` nhỏ hơn, hòa nữa thì epoch sớm hơn); `train_top1_at_best`, `train_top1_last`, `train_loss_last`;
  `lr_first`, `lr_last`, `lr_drop_epochs` (danh sách epoch mà `lr` nhỏ hơn epoch trước); `val_loss_first`,
  `val_loss_min`, `val_loss_last`; `steps_per_epoch`, `total_steps` = steps_per_epoch × epochs_run (hoặc `None`);
  `time_sec_total`, `time_sec_mean` (tổng và trung bình `time_sec`). Số lấy nguyên văn từ history, không làm tròn khi
  lưu. history rỗng thì báo lỗi mã 2.
- `batch_size_from_command(cmd: str | None) -> int | None`: đọc `--batch-size N` bằng `shlex`; không có thì `None`
  (KHÔNG lấy mặc định của argparse; REPORT ghi "KHÔNG CÓ").
- `train_cmd_diff(cmd_a, cmd_b, ignore=("--out-dir", "--data-root", "--sources")) -> dict`: so hai lệnh train theo
  cặp cờ/giá trị. Trả `{"only_a": {...}, "only_b": {...}, "different": {flag: [a, b]}}`. Dùng để chứng minh hai model
  4c có cùng công thức train, chỉ khác nguồn dữ liệu (và độ phân giải, nếu có).
- `init_options(train_script_path) -> list[str]`: liệt kê các cờ argparse của `scripts/train_unified.py` mà tên chứa
  `init|pretrain|resume|finetune|load` (không phân biệt hoa thường). Danh sách rỗng nghĩa là mọi run train từ khởi
  tạo ngẫu nhiên. Nếu danh sách không rỗng, REPORT in danh sách đó và kiểm xem lệnh train của run từ điển có dùng cờ
  nào không.
- `pred_origin(pred_cls, true_cls, vslgh_only: set, with_qipedc: set) -> dict`: trả ba khối `all`, `wrong_only`
  (chỉ các dòng `pred != true`) và `correct_n`. Mỗi khối có `vslgh_only_class`, `class_with_qipedc_train`,
  `class_without_train_data`, mỗi giá trị dạng `rate(k, n)`. Thay `pred_split` lồng trong `build`; ba bộ dòng như cũ
  (mọi clip QIPEDC TEST, clip chung 4c, S06 đối chứng). Thêm `label_space_base_rate` = rate(|lớp chỉ-VSL-GH|,
  |không gian nhãn model gộp|).
- `trim_consequence(chosen_name, chosen_cfg, trimming_rows) -> dict`: trả `chosen_trim` (bool), `credited`
  (từ `trimming_verdict`), và câu `sentence` dựng từ hai giá trị đó. Khi `chosen_trim=True` và `credited=False`, câu
  phải nói ba ý: (1) run được chọn `<tên>` train với `trim=true`, tức VẪN cắt đoạn nghỉ; (2) đường live muốn khớp với
  model này thì `harmonize()` phải gồm bước cắt nghỉ với cùng tham số trong `preprocessing` của checkpoint; (3) giữ
  hay bỏ cắt nghỉ ở live không do luật đăng ký trước quyết định, và bỏ thì phải train lại. Khi `chosen_trim=False`,
  câu nói run được chọn không cắt nghỉ. Không có nhánh nào gõ cứng tên run.
- `prereg_header_times(prereg_text, prereg_commits) -> list[dict]`: dùng regex tìm các tiêu đề
  `Added YYYY-MM-DD HH:MM` trong PREREG. Mỗi tiêu đề trả `header_time` và `commit` (commit PREREG đầu tiên có chứa
  tiêu đề đó: dùng `git log -S "<chuỗi tiêu đề>"` hoặc tương đương, commit sớm nhất), kèm `commit_time` và
  `header_minus_commit_s`. Không tìm được commit thì các trường là `None`, không báo lỗi.

### 3.3 Hợp đồng CLI của `scripts/report_step4.py`
Giữ nguyên toàn bộ tham số và mã thoát cũ (0 / 1 / 2 / 3; khi mã ≠ 0 thì không ghi file). Thêm:
- `history.json` của mọi run được đọc tự động từ thư mục run. Nếu thiếu `history.json` ở **run từ điển được dùng
  hoặc run được chọn** thì exit 2 (thông báo nêu đường dẫn). Run khác thiếu thì ghi `null`. Mọi `history.json` đọc
  được đều được thêm vào `inputs` kèm sha256.
- `--review-file PATH` (đã có): file review được thêm vào `inputs` kèm sha256, vai trò "review".

Khóa JSON MỚI trong `step4_results.json` (chỉ thêm, không đổi khóa cũ):
- `4c.fit_and_scope`: `{dict: training_fit(...), unified: training_fit(...), batch_size_source: "lệnh train trong log
  kernel", train_cmd_diff: {...}, init_options: [...], dict_command_uses_init: bool, step_matched_estimate: {
  epochs_needed: ceil(unified.total_steps / dict.steps_per_epoch), gpu_s_estimate: epochs_needed ×
  dict.time_sec_mean, note: "ước lượng, không phải kết quả; time_sec đo trong kernel có thể chạy nhiều job"}}`.
- `4c.exploratory.b_unified_top1_class_origin`: thêm `wrong_only` vào từng bộ dòng, và thêm `label_space_base_rate`.
- `4b.trimming.consequence`: kết quả của `trim_consequence`.
- `limitations_data.preregistration_header_times`: kết quả của `prereg_header_times`.
- `limitations_data.train_top1_measurement`: chuỗi mô tả nguồn gốc (trainer đo trên batch augment ở chế độ train;
  kèm đường dẫn `src/training/trainer.py`).
- `4b.harmonisation_config.augmentation`: bỏ tiền tố "Augmentation (training only):" khỏi giá trị; giữ nhãn
  "(training only)" trong phần render.

### 3.4 Nội dung REPORT.md (giữ mọi mục cũ; phần MỚI đánh dấu)
1–3. Header, Provenance, 4a: như cũ. Bảng inputs thêm `history.json` và file review.
4. **4b**: như cũ, cộng thêm:
   - Khối cấu hình hài hòa: một dòng "Augmentation (training only): …", không lặp chữ **[MỚI]**.
   - Ngay sau câu **Run được chọn**, in cả `trim` của run được chọn (đã có trong JSON cấu hình; giữ nguyên).
   - **Kết luận cắt đoạn nghỉ**: sau (i)(ii)(iii), thêm (iv) = `trim_consequence.sentence` **[MỚI, M2]**.
5. **4c**: như cũ, cộng thêm:
   - **[MỚI, M1] mục "Phạm vi so sánh và mức khớp train"**, đặt NGAY SAU bảng kết quả chính và TRƯỚC phần thăm dò:
     - Bảng hai dòng (từ điển / gộp): epoch đã chạy, epoch tốt nhất, train top-1 ở epoch tốt nhất và ở epoch cuối,
       lr đầu → lr cuối, các epoch giảm lr, val_loss đầu / min / cuối, clip train, batch (từ lệnh), bước/epoch, tổng
       bước, tổng giây `time_sec`.
     - Dòng ghi rõ: "train top-1 = số trainer ghi trên batch augment ở chế độ train (src/training/trainer.py), không
       phải độ chính xác sạch trên tập train".
     - `train_cmd_diff`: "Lệnh train hai model chỉ khác: …" (liệt kê khác biệt; nếu rỗng thì ghi "không khác ngoài
       --out-dir/--data-root/--sources").
     - `init_options`: "scripts/train_unified.py không có tùy chọn khởi tạo từ trọng số → cả hai model train từ khởi
       tạo ngẫu nhiên" (hoặc danh sách cờ nếu có).
     - Câu phạm vi. Câu này là chuỗi cố định, kèm điều kiện sinh từ dữ liệu: nếu `dict.total_steps !=
       unified.total_steps` HOẶC `dict_command_uses_init` là False, thì in: "Kết quả chính so model tách
       **train từ đầu, cùng công thức với model gộp** với model gộp. Hai model có quỹ tối ưu và mức khớp train khác
       nhau (bảng trên). Vì vậy kết quả này KHÔNG đo phương án tách có khởi tạo từ trọng số VSL-GH / model gộp, và
       cũng không đo phương án tách được train tới khi khớp."
     - Ước lượng giờ GPU cho một lần train model từ điển với cùng số bước như model gộp (`step_matched_estimate`),
       ghi rõ "ước lượng, không phải kết quả, không thuộc kế hoạch này".
   - Thăm dò (b) **[MỚI, M3]**: bảng thêm các cột "chỉ dự đoán sai" (k/n + CI) cho từng bộ dòng; thêm dòng tỷ lệ nền
     "lớp chỉ-VSL-GH trong không gian nhãn model gộp: k/n". Vẫn có nhãn "không đăng ký trước, chỉ báo, không kiểm định".
6. **Giới hạn**: như cũ, cộng thêm **[MỚI]**:
   - Câu về giờ PREREG: "Tiêu đề phần bổ sung PREREGISTRATION ghi `<header_time>`; commit `<hash>` lúc
     `<commit_time>`. Thứ tự so với kết quả được xét theo giờ commit." Không sửa PREREG.
   - Câu về mức khớp của model từ điển (trỏ về mục 4c mới), và về nguồn gốc của số train top-1.
7. **Review**: nội dung `--review-file` (review cuối cùng, xem R6).

### 3.5 Module tiền xử lý chung
Không đổi. Việc này KHÔNG thay đổi tiền xử lý, không chạm `src/`, `backend/`, `configs/`, `frontend/`.
`src/data/harmonized.py` chỉ được IMPORT để đọc `HARMONIZED_DEFAULT` và docstring.
`scripts/train_unified.py` chỉ được ĐỌC dưới dạng text (cho `init_options`), không import và không sửa.

---

## 4. Chia việc

Bước 1–6 của kế hoạch trước đã xong trong `72abc13`, `f4729ff`, `8c08845` (review xác nhận AC1–AC6 PASS, trừ các
điểm nêu ở §0). Lần sửa 1 gồm R0–R6 dưới đây. Bước 7–8 cũ được thay bằng R5–R6.

Quy tắc chung (không đổi, chỉ làm chặt hơn):
- Trước khi sửa symbol nào, chạy `node .gitnexus/run.cjs impact "<symbol>" --direction upstream --repo .`. Ít nhất
  chạy cho `build`, `render`, `_hist_summary` (nếu sửa) và mọi hàm có sẵn bị đổi. Nếu kết quả là HIGH/CRITICAL/UNKNOWN
  thì ghi vào commit message + progress_log. Với UNKNOWN, xác nhận thêm bằng text search.
- Trước MỖI commit, chạy `node .gitnexus/run.cjs detect-changes --scope all --repo .` (**`--scope all`**, không phải
  `staged`). Không chấp nhận `partial: true`/`truncated: true`; gặp thì chạy lại. Output sẽ liệt kê cả thay đổi chưa
  commit của người dùng: ghi rõ trong commit message rằng các mục đó không thuộc việc này.
- Chỉ `git add <đường dẫn cụ thể>`. Không dùng `git add -A`/`.`/`-u`. Không commit `*.pt`, `*.npz`, `*.log`, video,
  `REPORT_partial.md`, `data/`.

**R0 — Kiểm trạng thái (≈ 0.25 giờ, không sửa gì).** Phụ thuộc: không.
- `git log --oneline -3` → `8c08845`, `f4729ff`, `72abc13`. `git status --porcelain -- scripts src tests` → rỗng.
- `git diff --cached --name-only` → rỗng. `git ls-files -- "*.pt" "*.npz" "*.log"` → ghi lại danh sách.
  `git diff --name-only 27233f6..HEAD -- "*.pt" "*.npz" "*.log"` → phải rỗng. Nếu có `.pt` của
  `reports/unified_run_2026-09-25/` đang staged thì `git restore --staged <file>` (hoàn tác được) và ghi progress_log.
  Nếu có `.pt` đã nằm trong commit của việc này thì DỪNG, báo orchestrator (không viết lại lịch sử).
- Chạy AC2 và `tests.test_report_step4` → ghi số test "trước" (review ghi 53 và 38; phải tự đo lại).

**R1 — Test trước cho hàm mới (≈ 1.5 giờ).** Phụ thuộc: R0.
Thêm vào `tests/test_report_step4.py` các ca AC1 16–23 (§5), dùng fixture nhỏ dựng trong test (history vài epoch,
lệnh train, dự đoán vài dòng, PREREG text 3 dòng). Không sửa, không xóa test cũ.

**R2 — Cài đặt (≈ 2 giờ).** Phụ thuộc: R1.
Thêm các hàm §3.2 MỚI vào `scripts/report_step4.py`. Nối chúng vào `build` (4c `fit_and_scope`, (b) `pred_origin`,
`trimming.consequence`, `preregistration_header_times`, inputs history/review) và vào `render` (§3.4). Sửa chữ
"Augmentation" bị lặp. Chạy `python -m unittest tests.test_report_step4 -v` và bộ AC2. Commit mã + test (commit A).

**R3 — Sinh lại REPORT + JSON (≈ 0.5 giờ).** Phụ thuộc: R2 đã commit (`code_dirty=false`).
Lệnh chuẩn: lệnh ở header REPORT.md hiện tại, không đổi đối số, CHƯA có `--review-file`. Chạy xong, lưu bản sao
REPORT.md + step4_results.json ra thư mục tạm. Chạy lại đúng lệnh đó, tại chỗ. So `cmp` với bản sao (AC3).

**R4 — Sửa PROPOSAL_4c.md + test AC5b (≈ 1 giờ).** Phụ thuộc: R3.
- Viết lại theo AC5 + AC5b. Mọi số chép từ REPORT.md mới.
- Bắt buộc: nêu phạm vi (tách train-từ-đầu, cùng công thức); nêu số mức khớp train của hai model; sửa câu "mất toàn
  bộ dữ liệu VSL-GH" thành câu có phạm vi; (b) nếu được nhắc thì phải kèm cột chỉ-sai và tỷ lệ nền; bước cắt nghỉ ở
  việc sau; "Điều gì sẽ làm đổi khuyến nghị" có model từ điển train tới khi khớp / khởi tạo từ VSL-GH (ghi "thí
  nghiệm mới, tốn GPU, cần người dùng duyệt").
- Khuyến nghị vẫn là đúng MỘT trong A/B. Coder chọn theo bằng chứng. Nếu bằng chứng chưa đủ để phân định, phải nói
  rõ "khuyến nghị có điều kiện" trong cùng câu, nhưng vẫn chỉ nêu một chữ cái.
- Thêm test AC5b (THÊM test mới, không sửa test AC5 cũ). Commit REPORT/JSON/PROPOSAL/test (commit B).
  `detect-changes --scope all` trước commit.

**R5 — Review vòng 2 (orchestrator gọi vslt-reviewer).** Phụ thuộc: R4.
Reviewer kiểm M1–M4, các góp ý nhỏ, AC mới. Nếu còn FAIL thì quay lại R1–R4 (vòng CODE↔REVIEW tối đa 3).

**R6 — Sinh bản cuối với review + đóng việc (≈ 0.5 giờ).** Phụ thuộc: R5 kết luận không còn FAIL.
- Chạy lại lệnh R3 + `--review-file <file review cuối, trong docs/reviews/>` (file do orchestrator cung cấp). Kiểm
  AC9. Chạy lại test AC5/AC5b.
- Thêm 1 dòng vào `docs/progress_log.md` (§5 AC8). `detect-changes --scope all`. Commit C (REPORT/JSON + progress_log).
- Orchestrator gửi người dùng đường dẫn REPORT.md + PROPOSAL_4c.md + các câu hỏi §7. DỪNG.

Ước lượng GPU cho kế hoạch này: **0 giờ**. Không có lệnh `kaggle kernels push`/run nào.

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder không được đổi; chỉ planner đổi và phải ghi lý do)

**AC1 — Test logic chọn và hàm thuần.**
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_report_step4 -v` → `OK`, 0 skip. Có ít nhất các
ca sau, mỗi ca một test riêng. Ca 1–15 giữ nguyên như kế hoạch trước; test hiện có của chúng không được sửa, skip
hay xóa.
1. z: keepz hơn dropz ≥ 0.5 → keepz; hơn < 0.5 (vd. 0.49) → dropz; dropz tốt hơn → dropz; chênh đúng 0.5 → keepz.
2. z nhận diện theo `run_config.hand_z`, không theo tên.
3. 360: chênh ≥ 0.5 → 360; < 0.5 → native; khác hand_z → mã 3.
4. Aux run có balanced VAL cao nhất vẫn không được chọn.
5. Run thiếu `val_by_source` không phải ứng viên, không lỗi.
6. Trimming ghép theo `run_config`; ≥ 0.5 → credited; < 0.5 → not; không ghép được → mã 3.
7. `pick_dict_run`: không khớp → mã 3, không fallback.
8. Chọn không phụ thuộc TEST.
9. `mcnemar_exact`: (0,0) → p = 1.0; 5/0 khớp `scipy.stats.binomtest`; đối xứng.
10. Căn theo `video_id`; sai thứ tự nhãn → assert.
11. Wilson: k = 0 và k = n cho cận trong [0, 100].
12. `parse_kernel_log` trên fixture.
13. JSON thiếu command/git_commit → "KHÔNG CÓ"; so khớp cũ/mới báo đúng trường khác.
14. Render xác định.
15. Mã thoát ≠ 0 → không ghi file.

MỚI (Lần sửa 1):

16. `training_fit`: fixture history 4 epoch. (a) `best_epoch` theo đúng luật trainer: `val_top1` lớn nhất; nếu hòa
    `val_top1` thì chọn `val_loss` nhỏ hơn; fixture phải có một cặp hòa `val_top1`. (b) `lr_drop_epochs` đúng.
    (c) `train_top1_at_best`/`_last` đúng giá trị history. (d) `total_steps` = ceil(n/b) × epochs, có ca n chia
    không hết cho b (vd. n=795, b=64 → 13 bước/epoch). (e) `batch_size=None` → `steps_per_epoch`/`total_steps` là
    `None`, không lỗi. (f) history rỗng → mã 2.
17. `batch_size_from_command`: có `--batch-size 64` → 64; không có cờ → `None`; `None` → `None`.
18. `train_cmd_diff`: hai lệnh chỉ khác `--out-dir`/`--sources` → không có khác biệt. Thêm `--process-height 360`
    vào một lệnh → báo trong `only_a`/`only_b`. Đổi `--epochs` → báo trong `different`.
19. `init_options`: trên text argparse fixture không có cờ khởi tạo → `[]`; fixture có `--init-from` → `["--init-from"]`.
20. `pred_origin`: fixture với dự đoán đúng và sai. `wrong_only.n` = số dòng `pred != true`. Một dự đoán đúng rơi
    vào lớp có QIPEDC KHÔNG được tính trong `wrong_only`. Tổng ba cột của mỗi khối = n.
    `label_space_base_rate` = |chỉ-VSL-GH| / |nhãn|.
21. `trim_consequence`: (a) `chosen_trim=True`, `credited=False` → câu chứa tên run, "trim=true", "harmonize()",
    và cụm nói việc giữ/bỏ không do luật đăng ký trước quyết định. (b) `chosen_trim=False` → câu nói run được chọn
    không cắt nghỉ, và KHÔNG chứa "trim=true". (c) Đổi tên run trong fixture thì câu đổi theo (không gõ cứng tên).
22. `prereg_header_times`: text fixture có tiêu đề "Added 2026-09-26 12:30" và commit giả lập lúc 12:13:24 cùng múi
    giờ → `header_minus_commit_s` = 996 (12:30:00 − 12:13:24). Không có tiêu đề → `[]`. Không tìm được commit → các
    trường `None`, không lỗi.
23. Render: chuỗi REPORT không chứa "Augmentation: Augmentation"; chứa đúng một dòng bắt đầu bằng
    "- Augmentation (training only):".

**AC2 — Không hồi quy.** Bộ test trong handoff
(`tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards
tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api
tests.test_unified_split_integrity tests.test_harmonized`, qua `.venv`, `PYTHONIOENCODING=utf-8`) chạy ở R0 và sau R2
→ cùng số test, `OK`, không test nào bị sửa/skip/xóa. `tests.test_report_step4`: số test sau ≥ số test trước + 8
(ca 16–23), và `git diff 8c08845 HEAD -- tests/test_report_step4.py` chỉ gồm dòng THÊM (không dòng `-` nào ngoài
header diff). Ghi cả hai con số (trước → sau) vào progress_log.

**AC3 — REPORT sinh bằng script, tái lập.** *(Sửa ở Lần sửa 1. Lý do: bản cũ đòi `cmp` giữa hai lần chạy khác
`--out`, điều này không thể đạt vì `--out` nằm trong chuỗi lệnh được ghi. Kiểm tra mới vẫn chặt như cũ: cùng lệnh,
cùng đầu vào thì ra cùng byte.)*
- Lệnh R3 (và lệnh R6, có `--review-file`) exit 0. Header REPORT.md chứa đúng lệnh đó và HEAD `h`.
  `git diff h -- scripts/ src/ tests/` rỗng. `code_dirty = false` trong `step4_results.json`.
- Chạy lệnh lần 1, sao REPORT.md + step4_results.json ra thư mục tạm, chạy đúng lệnh đó lần 2 → `cmp` hai cặp file:
  không khác.
- Chạy cùng lệnh, chỉ đổi `--out`/`--json-out` sang thư mục tạm → so JSON bằng
  `python -c` (nạp hai JSON, xóa khóa `generated_by.command` ở cả hai, so bằng `==`) → bằng nhau.
- Mọi số trong REPORT.md có mặt trong step4_results.json hoặc JSON đầu vào. Reviewer kiểm ngẫu nhiên ≥ 10 số, trong
  đó ≥ 3 số ở mục 4c "Phạm vi so sánh và mức khớp train", truy về `history.json`.

**AC4 — Nội dung REPORT.md** (reviewer đánh dấu từng mục). Mục a–j giữ nguyên như kế hoạch trước:
a. Bảng provenance đủ (không ô trống; "KHÔNG CÓ" rõ ràng), sha256 mọi đầu vào, thời lượng kernel.
b. Số bộ phân loại nguồn từ JSON có `command` + `git_commit`; so khớp bản cũ CÓ/KHÔNG.
c. 4b: balanced VAL, câu chọn z/360 (2 chữ số thập phân), giá trị 1 clip QIPEDC VAL, cờ sát ngưỡng, chênh seed.
d. Bảng TEST 4 nhóm, top-1 và top-5 có k/n + Wilson CI; số clip bị loại.
e. Kết luận cắt đoạn nghỉ (i)(ii)(iii).
f. Dao động seed cho H-keepz và baseline cũ.
g. Khối cấu hình hài hòa sinh từ mã.
h. 4c: đúng MỘT so sánh chính, run từ điển khớp cấu hình, cỡ mẫu, Top-1/5/10 + k/n + CI, McNemar, thăm dò có nhãn.
i. Mục Giới hạn đủ ý.
j. Mục Review chứa kết luận vslt-reviewer (bản cuối, R6).

MỚI:
k. **(M1)** Mục 4c "Phạm vi so sánh và mức khớp train", đặt trước phần thăm dò, gồm: bảng hai model với mọi trường
   §3.4 mục 5; dòng về cách trainer đo train top-1; `train_cmd_diff`; `init_options`; câu phạm vi; ước lượng GPU có
   nhãn "ước lượng". Các giá trị train top-1 / epoch / lr trùng `history.json`. Reviewer mở file và đối chiếu ≥ 2
   giá trị cho mỗi model.
l. **(M2)** Mục 3.4 có (iv): câu sinh từ `run_config.trim` của run được chọn, nêu rõ run được chọn dùng
   `trim=true` (với dữ liệu hiện tại) và hệ quả cho `harmonize()` ở đường live. JSON có `4b.trimming.consequence`.
m. **(M3)** Thăm dò (b) có cột "chỉ dự đoán sai" (k/n + CI) cho cả ba bộ dòng, và dòng tỷ lệ nền của không gian nhãn.
   Tất cả do script sinh ra. Reviewer đối chiếu với số tự tính trong review (QIPEDC sai → chỉ-VSL-GH; S06 sai →
   chỉ-VSL-GH; 282/876). Nếu không trùng thì ghi nguyên nhân, không chỉnh tay.
n. Giới hạn có câu về giờ ở tiêu đề PREREG so với giờ commit (sinh bằng `prereg_header_times`), và câu về mức khớp của
   model từ điển.
o. Không còn chuỗi "Augmentation: Augmentation".

**AC5 — PROPOSAL_4c.md** (giữ nguyên): `wc -w` ≤ 550; đúng một khuyến nghị (A hoặc B); có câu "người dùng quyết
định"; có mục Giới hạn gồm các ý của Bước 6 cũ. Test hiện có trong `TestProposal4c` phải vẫn qua, không bị sửa.

**AC5b — PROPOSAL, ràng buộc phạm vi (MỚI; THÊM test, không sửa test cũ).** Thêm test không skip; thiếu file thì FAIL.
1. So theo ngữ cảnh: mọi cụm dạng `<số>% (<k>/<n>)` trong PROPOSAL xuất hiện nguyên văn trong REPORT.md. Mọi số
   (thập phân, %, k/n, nguyên ≥ 10) trong PROPOSAL khớp trong REPORT.md ở vị trí mà ký tự liền trước và liền sau
   KHÔNG phải `[0-9A-Za-z]` (tránh khớp nhầm vào sha256/hex), trừ dấu chấm thập phân như test cũ.
2. PROPOSAL chứa: "train từ đầu", "khởi tạo từ trọng số", và cả hai giá trị train top-1 ở epoch cuối (của model từ
   điển và model gộp), chép nguyên văn từ mục 4c mới của REPORT.
3. PROPOSAL KHÔNG chứa câu cũ `mất toàn bộ dữ liệu VSL-GH` (so chuỗi con).
4. Nếu PROPOSAL chứa "chỉ-VSL-GH" thì cũng phải chứa "dự đoán sai".
5. Mục "Điều gì sẽ làm đổi khuyến nghị" chứa "khi khớp" hoặc "khởi tạo", VÀ chứa "tốn GPU".
6. Mục việc sau (sau khi người dùng duyệt) chứa "cắt đoạn nghỉ" hoặc "cắt nghỉ".

**AC6 — Phạm vi thay đổi.** `git diff --stat 27233f6..HEAD` chỉ gồm: `scripts/report_step4.py`,
`tests/test_report_step4.py`, `reports/step4_2026-09-26/{REPORT.md, step4_results.json, PROPOSAL_4c.md,
REVIEW_step4.md (tùy chọn), provenance_rerun/**}`, `docs/progress_log.md`, `docs/plans/`, `docs/reviews/` (nếu
orchestrator commit file review). KHÔNG đổi: `backend/`, `src/`, `configs/`, `frontend/`, `.gitignore`,
`PREREGISTRATION.md`, các JSON 4a/4b cũ, `data/`, `runs/*/history.json`, `runs/*/metrics.json`. `REPORT_partial.md`
không bị sửa, xóa hay thêm vào git (`git ls-files reports/step4_2026-09-26/REPORT_partial.md` → rỗng; file vẫn còn
trên đĩa). `git status` vẫn cho thấy các thay đổi chưa commit của người dùng y như trước (3 file data bị xóa). Không
commit `*.npz`, `*.pt`, `*.log`, video (`git diff --name-only 27233f6..HEAD -- "*.pt" "*.npz" "*.log"` → rỗng).
*(Sửa ở Lần sửa 1: thêm `docs/reviews/` vì `--review-file` trỏ vào review do reviewer viết ở đó; thêm các file cấm
sửa `.gitignore`, `history.json`, `metrics.json`; thay "không đổi REPORT_partial.md" bằng kiểm tra cụ thể, vì file
này untracked. Không nới tiêu chí nào.)*

**AC7 — Review.** vslt-reviewer: không FAIL cho thay đổi của việc này (gồm các commit của Lần sửa 1) và cho 348843f,
4bb3811, 9e3be95, a414b0d, 27233f6, 4f4e349. Mục 13 (kết luận vượt bằng chứng) phải PASS. Mọi UNVERIFIED có bằng
chứng bổ sung hoặc có mặt trong mục Giới hạn của REPORT.

**AC8 — Quy trình.** Output `impact` cho symbol đã sửa và `detect-changes --scope all` (không partial/truncated)
được nêu trong commit message của MỖI commit mới hoặc trong progress_log. *(Sửa: nêu rõ `--scope all`. Ba commit cũ
đã dùng `staged` và không viết lại; progress_log ghi điều này và ghi kết quả `--scope all` chạy ở R6.)* Đúng 1 dòng
progress_log cho kế hoạch 01, theo định dạng bảng hiện có
`ngày | việc | kế hoạch | commit | kết luận review | việc tiếp theo`, trong đó:
việc = "Bước 4a–4c: REPORT + PROPOSAL 4c"; kế hoạch = `docs/plans/01-buoc4-hoan-tat-4a-4c.md`; commit = danh sách
hash của việc (72abc13, f4729ff, 8c08845 + các commit mới); kết luận review = kết luận của review cuối + số vòng;
việc tiếp theo = "DỪNG — chờ người dùng quyết định 4c (+ câu hỏi §7)". Trong cùng dòng hoặc ngay dưới nó, ghi số test
AC2 trước → sau và `test_report_step4` trước → sau. Không có lệnh Kaggle push/run nào.

**AC9 — Lần sinh cuối chỉ thêm Review (MỚI).** Gọi commit B là commit ở R4 và commit C là commit ở R6.
- `git diff B C -- reports/step4_2026-09-26/REPORT.md` chỉ chạm dòng lệnh/HEAD trong header, bảng inputs (dòng file
  review), và mục `## 6. Review`.
- `python -c` nạp `step4_results.json` ở B và C (`git show`), bỏ các khóa `generated_by`, `review` và phần tử
  `inputs` có vai trò "review", rồi so bằng `==` → bằng nhau.
- Mục Review chứa kết luận của review cuối (không phải "Chưa có kết quả").

---

## 6. Rủi ro dữ liệu / ML

- **Rò rỉ chọn model.** Luật chọn chỉ dùng VAL (AC1 ca 8). TEST chỉ được đọc lại từ logits đã sinh một lần. Chẩn đoán
  mức khớp (Lần sửa 1) chỉ đọc `history.json` (train/VAL), không chạm TEST và không dùng để chọn.
- **[MỚI] Quỹ tối ưu / mức khớp train không ngang nhau ở 4c.** Hai model dùng cùng lệnh train, nhưng khác nhau về số
  clip train, số bước mỗi epoch, và tín hiệu VAL (model từ điển có VAL 105 clip QIPEDC, là tín hiệu điều khiển cả
  ReduceLROnPlateau lẫn dừng sớm). Kết quả chính (đã đăng ký) vẫn đúng như đã đo. Nhưng chỉ được diễn giải là "model
  tách train-từ-đầu bằng công thức hiện tại kém hơn model gộp", không phải "tách kém hơn gộp" nói chung. REPORT phải
  in câu phạm vi (AC4 k) và PROPOSAL phải nêu nó (AC5b).
- **[MỚI] `train_top1` không phải độ chính xác sạch trên tập train.** Nó được đo trên batch augment, ở chế độ train
  (dropout), với WeightedRandomSampler. Số này chỉ dùng để so tương đối giữa hai model cùng công thức, và phải có
  dòng ghi chú. Không chạy lại model trên tập train trong việc này.
- **[MỚI] Thăm dò (b) lẫn độ chính xác vào.** Dùng cột chỉ-sai và tỷ lệ nền. Vẫn chỉ là chỉ báo, không phải kiểm định.
  S06 đối chứng có lớp đúng thuộc VSL-GH, nên lỗi dự đoán của nó tự nhiên rơi vào lớp VSL-GH nhiều hơn. Không kết
  luận "model học phân biệt nguồn" chỉ từ bảng này.
- **[MỚI] Cắt nghỉ: "không được công nhận" không có nghĩa là "đã bỏ".** Run được chọn train với trim=true. Nếu đường
  live bỏ bước cắt thì sẽ lệch train–realtime. Việc giữ hay bỏ ở live là quyết định của người dùng (§7).
- **Luật đăng ký trước viết một phần sau khi thấy kết quả chọn z.** Không sửa PREREG. Thêm câu về giờ ở tiêu đề so với
  giờ commit (sinh bằng script).
- **Ngưỡng 0.5 so với độ nhiễu.** 1 clip QIPEDC VAL tương đương 0.476 điểm. Chênh giữa seed 42 và 43 của H-keepz gần
  bằng mức 360 px thắng, và run 360 chỉ có 1 seed (REPORT đã in). Không đổi luật. Nêu thành câu hỏi cho người dùng.
- **Cỡ mẫu.** Đánh giá chéo nguồn có n rất nhỏ; model từ điển có 593/594 lớp chỉ có ≤ 2 clip train; Wilson giả định
  các clip độc lập.
- **So sánh 4c còn bị nhiễu bởi không gian nhãn và lượng dữ liệu.** Thăm dò (a) chỉ để hiểu, không thay kết quả chính.
- **Lệch train–realtime.** Đường live chưa dùng `harmonize()`. Nếu dùng 360 px thì live phải giảm về cùng mức và có
  test tương đương. Nếu giữ trim thì live phải cắt nghỉ bằng cùng tham số. Tất cả là việc SAU khi người dùng duyệt.
- **Tính so sánh giữa kernel; checkpoint "model hiện tại" của 4a; nguồn gốc/tái lập; S06 gồm câu đã thấy trong train.**
  Như kế hoạch trước; REPORT đã có.
- **[MỚI] `.pt` chưa bị gitignore** trong `reports/unified_run_2026-09-25/run*/`: có nguy cơ commit nhầm. R0 kiểm;
  AC6 cấm. Việc sửa `.gitignore` để cho người dùng quyết định (§7).

---

## 7. Điểm dừng

- **Trước khi code: KHÔNG có điểm dừng.** Lần sửa 1 không cần dữ liệu người dùng, không đổi model mặc định, không đụng
  thay đổi chưa commit của người dùng, không có hành động không hoàn tác. Nó không viết lại lịch sử, chỉ thêm commit
  mới. Trường hợp ngoại lệ duy nhất: nếu R0 thấy `.pt`/`.npz` đã nằm trong commit, thì DỪNG và báo (xử lý file đó đòi
  viết lại lịch sử).
- **Có: ĐIỂM DỪNG BẮT BUỘC "sau bước 4c"** ở cuối (R6). Gửi REPORT.md + PROPOSAL_4c.md. → **CẦN NGƯỜI DÙNG**.
  Orchestrator gửi kèm các câu hỏi sau (chỉ là câu hỏi; KHÔNG thuộc kế hoạch này, KHÔNG tự làm):
  1. **A/B cho 4c.** Nên quyết định sau khi đọc mục 4c mới "Phạm vi so sánh và mức khớp train".
  2. **Có muốn một thí nghiệm MỚI trước khi chọn A/B không?** Thí nghiệm này chưa đăng ký trước và tốn GPU. Phương án:
     (i) train model từ điển tới khi khớp: cùng số bước với model gộp, hoặc không giảm lr / dừng sớm theo VAL 105 clip;
     (ii) khởi tạo từ trọng số VSL-GH hoặc model gộp rồi fine-tune trên QIPEDC. Phương án này cần thêm tùy chọn khởi
     tạo vào `scripts/train_unified.py`, cần phần đăng ký trước mới, và cần thêm seed. Ước lượng GPU: REPORT mục 4c
     in `step_matched_estimate` sinh từ `history.json`. Ước lượng thô của planner cho (i), chưa kiểm chứng: tổng
     `time_sec` của `dict_keepz_360/history.json` ≈ 212 s cho 48 epoch (≈ 4.4 s/epoch); theo review, model gộp
     ≈ 237 bước/epoch × 98 epoch, model từ điển 13 bước/epoch, nên cần ≈ 1 790 epoch ≈ 2.2 giờ GPU cho mỗi run
     mỗi seed, chưa tính thời gian khởi động kernel và chuẩn bị dữ liệu. (ii) có thể ngắn hơn, nhưng cần sửa mã và
     có thể cần một run chỉ-VSL-GH để lấy trọng số khởi tạo. Hạn mức 10 giờ GPU/tuần: REPORT §1.2 ghi 5.97 giờ cho 4
     kernel train (chưa gồm các kernel trích xuất 360 px), nên người dùng cần duyệt ngân sách. Nếu người dùng chọn
     làm thì planner lập kế hoạch MỚI (02-…), có đăng ký trước.
  3. **360 px chỉ có một seed.** Theo luật, 360 px được chọn (+1.72). Nhưng chênh giữa hai seed của H-keepz là +1.61.
     Có muốn thêm seed cho H-keepz-360 (cũng là thí nghiệm mới, tốn GPU) trước khi đổi đường realtime sang 360 px
     không? Hay chấp nhận kết quả theo luật?
  4. **Cắt đoạn nghỉ ở đường live.** Model được chọn train với trim=true. Khi nối `harmonize()` vào live, giữ bước cắt
     (khớp model hiện có) hay bỏ (phải train lại)? PREREG không quy định.
  5. **Việc nhỏ:** `REPORT_partial.md` đang untracked: commit, giữ nguyên hay xóa? Có thêm
     `reports/unified_run_*/**/*.pt` vào `.gitignore` không?
- Đổi model mặc định: KHÔNG (điểm dừng riêng, sau khi người dùng duyệt).
- Cần dữ liệu người dùng: không.
- Thay đổi chưa commit của người dùng: không đụng.
- Hành động không hoàn tác: không.
