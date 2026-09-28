# Kế hoạch 05 — Thực thi quyết định người dùng 2026-09-28 (backlog 1a, 1b, 1c, 1e, 1f)

> **Không cần người dùng trước khi code.** Mọi việc trong kế hoạch đã có quyết định của người dùng (docs/STATE.md, mục "Quyết
> định", các dòng 2026-09-28). Kế hoạch có **điểm dừng có điều kiện** ở bước kiểm tra ban đầu (B0) và bước lưu trữ Kaggle (B6),
> xem §7. Nếu một điểm dừng kích hoạt, coder dừng tại đó và báo; các bước không phụ thuộc vẫn làm được.

Nhánh `feat/vslt-complete`. Lập kế hoạch tại HEAD `b337aee` (gọi là `P5`). Ngày 2026-09-28. Không push. Không viết lại lịch sử
(không amend, rebase, reset, force).

---

## 1. Mục tiêu và DoD

**Mục tiêu.**
(a) Gỡ `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` khỏi git index (`git rm --cached`), giữ file trên
đĩa, không viết lại lịch sử. Làm SAU khi file đã nằm trong một dataset Kaggle private đã được xác minh.
(b) `/api/fingerspelling/status` chỉ trả nguồn dữ liệu và số người ký, không trả tên người ký.
(c) Lưu vào MỘT dataset Kaggle PRIVATE mới: bằng chứng nguồn gốc Cấp 1 và các đầu vào không track của REPORT bước 4 (§7.2).
Slug và sha256 do script sinh.
(e) Kiểm và ghi bằng chứng: `REPORT_partial.md` nằm ở `../_backup_step4/` và không có trong git; `.gitignore` có
`reports/**/*.pt` và `reports/**/*.npz`.
(f) Bốn việc nhỏ còn lại từ review 04.

**DoD phục vụ.**
- DoD 6 và 7: test mới cho status, `/api/classes`, checkpoint không phục vụ được, `dropped_frames`, AC5 không PASS rỗng.
- DoD 1 (clone sạch): có lệnh khôi phục artifact từ dataset private; test hiện có vẫn chạy hoặc skip có lý do như trước.
- DoD 9 (Giới hạn trung thực): biết rõ artifact nằm ở đâu và file nào có giấy phép chưa rõ.
- Quy tắc cứng autopilot §4: không commit dữ liệu hay checkpoint có giấy phép chưa rõ; không nới test. GPU: 0 giờ.

**Không thuộc phạm vi.** frontend; CORS và giới hạn WS (Việc 5); đổi model mặc định; `scripts/smoke_test_phase12.py` (Việc 5);
chính sách phát lặp và tốc độ segmenter (review 04 mục 8–9); sinh lại `reports/step4_2026-09-26/REPORT.md` (xem §6, việc theo sau);
xóa tên người ký khỏi tài liệu và JSON đã commit (xem §6, rủi ro còn lại); sửa `scripts/archive_step4_kaggle.py` hay manifest bước 4.

---

## 2. Hiện trạng (tại `P5`, đọc mã; coder xác nhận lại ở bước B0)

### 2.1 (a) `alphabet_real_best.pt`
- Đang được git track (thêm ở `429b289`, có trên `origin/fix/audit-round2`; review 02 xác nhận). Train trên hauuto, giấy phép chưa rõ
  (`docs/data_registry.md:43–44`). sha256 đã ghi: `reports/alphabet_deploy_2026-09-27/provenance.json` khóa
  `checkpoints["known.real_run"].sha256` (`afc00521…`).
- `.gitignore:78` `reports/**/*.pt` ĐÃ khớp đường dẫn này. Sau `git rm --cached`, file tự thành file bị ignore. `.gitignore` không
  cần quy tắc mới; chỉ thêm một dòng chú thích để truy vết.
- Chỗ tham chiếu:
  - `tests/test_fingerspelling_api.py:34` (`REAL_CKPT`) và `:190–191`: `TestRealClipEquivalence` đã có
    `skipUnless(manifest hauuto tồn tại AND REAL_CKPT tồn tại)`. Trên máy này file vẫn còn trên đĩa, nên test vẫn chạy. Trên clone
    sạch, dữ liệu hauuto (`data/external/…`, gitignore) vốn đã không có, nên test vốn đã skip. **Vì vậy không cần sửa test cũ, và
    không có gì để hỏi người dùng ở điểm này.**
  - `scripts/alphabet_ckpt_provenance.py:52` (`KNOWN["real_run"]`): thiếu file thì `exists: false` và chạy tiếp (`:88–90`).
    `real_run` không tính vào V1. Không đổi.
  - README không trỏ trực tiếp tới file này. README dòng 51 trỏ tới thư mục `reports/alphabet_real_run_2026-09-25/`.
    `docs/data_registry.md:44` ghi "already committed and pushed", câu này phải cập nhật.
- Trên máy khác đã clone nhánh này, `git pull` qua commit `git rm --cached` sẽ XÓA file khỏi thư mục làm việc của máy đó (git coi
  là file bị xóa khỏi repo). Vì vậy (c) phải xong và được xác minh TRƯỚC (a), và phải có lệnh khôi phục (§3.3).

### 2.2 (b) `/api/fingerspelling/status`
- `backend/main.py:708–735` `get_fingerspelling_status`. Hàm này trả nguyên `meta["trained_on"]` (`:724`), gồm `signers` (tên) và
  `clips`. `meta` lấy từ `get_or_load_alphabet_model` (`:590–592`). `alphabet_data_provenance` (`:602–607`) chỉ đọc `source`.
- Checkpoint triển khai `checkpoints/alphabet_best.pt` có `trained_on = {"source": "hauuto", "signers": [4 tên], "clips": 636}`
  (`reports/alphabet_deploy_2026-09-27/provenance.json:47–56`).
- Test cũ ràng buộc hình dạng (KHÔNG được sửa), `tests/test_fingerspelling_limits.py`:
  - `:348–352`: không có `trained_on` → `body["trained_on"] is None`, `data_provenance == {"status": "unknown"}`;
  - `:354–359`: fixture `{"source": "hauuto", "signers": ["s1"], "clips": 1}` → `body["trained_on"]["source"] == "hauuto"`;
  - `:361–365`: fixture `{"source": "somewhere_else"}` → `body["trained_on"] == {"source": "somewhere_else"}` (so sánh bằng
    TOÀN BỘ dict, nên không được thêm khóa khi checkpoint không có `signers`);
  - `:373–378`: giữ các khóa cũ.
- Frontend không đọc `trained_on` hay `signers` (grep `frontend/src`: 0 kết quả).

### 2.3 (c) Lưu trữ private
- Mẫu đã APPROVE: `scripts/archive_step4_kaggle.py` (stage/upload/verify; `public=False` là hằng; kiểm private từ 2 nguồn
  `private_from_list` + `private_from_metadata`; exit 0/2/3/4/5/6; manifest). Dataset `phmvnsm33/vslt-step4-artifacts` version 1, 18
  file (manifest `reports/step4_2026-09-26/archive/kaggle_archive_manifest.json`). Manifest này được `scripts/report_step4.py`
  (`--archive-manifest`) và test ca 27/32 của `tests/test_report_step4.py` đọc. Test guard `test_13_forbidden_calls_absent`
  (`tests/test_archive_step4_kaggle.py:372–378`) cấm `dataset_create_version`, `dataset_metadata_update`, `dataset_delete`,
  `public=True` trong script đó.
- File cần lưu (danh sách lấy từ JSON đã commit, không gõ tay):
  - **Nhóm S (đầu vào không track của REPORT bước 4, §7.2):** `reports/step4_2026-09-26/step4_results.json` →
    `limitations_data.untracked_unarchived_inputs.files` (8 phần tử, có `path` + `sha256` + `role`, dòng 3120–3175): 4 log kernel,
    `reports/unified_run_2026-09-25/run_seed43/history.json`, `checkpoints/stgcn_unified_best.pt`,
    `checkpoints/stgcn_tier2_indomain.pt` (model mặc định Cấp 2 của backend), `data/processed/vslgh_segments/segments.csv`.
    Ghi chú: sha256 của `checkpoints/stgcn_unified_best.pt` trong JSON (`930633…`) trùng file baseline đã lưu
    `unified_run_2026-09-25__run__stgcn_unified_best.pt`. Vẫn lưu, vì manifest khớp theo đường dẫn; coder ghi sự trùng này.
  - **Nhóm A (bằng chứng nguồn gốc Cấp 1):** `reports/alphabet_deploy_2026-09-27/provenance.json` → `checkpoints` gồm các khóa
    `deployed` (`checkpoints/alphabet_best.pt`), `known.nested_primary`, `known.nested_variants`, `known.real_run`
    (= `alphabet_real_best.pt`), mỗi khóa có `path`, `exists`, `sha256`. Thêm `NESTED_PREDICTIONS` (hằng trong
    `scripts/alphabet_ckpt_provenance.py:56`), file này KHÔNG có sha256 đã ghi ở đâu cả.
  - **Bổ sung của planner (có lý do):** `checkpoints/alphabet_best.pt` (khóa `deployed`). Người dùng liệt kê "2 .pt nested +
    nested_predictions.csv + alphabet_real_best.pt". Planner thêm file triển khai, vì V2/V4/V5 của verdict đọc chính file này: thiếu
    nó thì máy khác không tính lại được verdict dù có đủ bằng chứng còn lại. File này cùng lớp giấy phép (hauuto) và cùng chế độ
    private, nên nằm trong phạm vi quyết định "lưu private". Orchestrator có thể bỏ file này nếu không đồng ý; khi đó AC9-2/AC10-b
    đổi theo và planner phải ghi lý do.
- Kaggle CLI trong `.venv`: `kaggle 2.2.4`, `kagglesdk 0.1.37` (kế hoạch 02 §2.4). `dataset_create_new(public=False)` → private;
  `dataset_metadata_update` đặt `isPrivate` bằng `False` nếu thiếu khóa, nên CẤM gọi.

### 2.4 (e)
- `.gitignore:78–79` có `reports/**/*.pt`, `reports/**/*.npz` (và `:35` `*.npz`). Kế hoạch 02 §2.2 ghi `REPORT_partial.md` đã được
  người dùng chuyển ra `../_backup_step4/`. Chưa có lệnh nào được ghi lại làm bằng chứng cho việc này.

### 2.5 (f) Việc nhỏ từ review 04 (`docs/reviews/04-review.md:129–137`)
- **f1 AC5:** `tests/test_live_harmonized_equivalence.py:231–292` so `ws_events` với `local_events`. Nếu cả hai rỗng thì test vẫn PASS.
- **f2 checkpoint không phục vụ được:** `get_or_load_predictor` (`backend/main.py:151–176`) ném `ModelUnavailable` khi
  `live_pipeline_for` ném `ValueError`. Điều này xảy ra khi `features` lạ, `mediapipe_version` lệch, … (`src/inference/harmonized_live.py:34–61`).
  Khi đó không cache gì. `/api/health`, `/model/info` và WS xử lý đúng (503 / `error{model_unavailable}` + 1011), nhưng mới chỉ có
  test cho sha lệch (`tests/test_ws_live_contract.py:217–240`), chưa có test cho `features` lạ hay `mediapipe_version` lệch.
- **f3 `dropped_frames`:** `_process_frame_worker_harmonized` gọi `session.process(…, seq=item["received_seq"])` (`backend/main.py:1171`).
  `received_seq` = `counters["received"]` tăng với MỌI message không rỗng (`:1362`), kể cả message lỗi và control. Trong
  `src/inference/harmonized_live.py:139`, `dropped = seqs[-1] - seqs[0] + 1 - n`. Vì vậy message lỗi/control nằm giữa một ký hiệu bị
  đếm là frame rơi. `stats["frame_seq"]` (`backend/main.py:1174`) chỉ tăng khi `session.process` thành công. `frame_result.dropped_frames`
  (`:1192`) = `counters["dropped"]` = số lần ghi đè slot cộng dồn (`:1390–1391`); giá trị này đúng nghĩa và giữ nguyên.
- **f4 `/api/classes`:** `backend/main.py:491–498` gọi thẳng `get_or_load_predictor()`. `ModelUnavailable` (hoặc lỗi nạp khác) không
  được bắt → 500. Không có caller nào trong `frontend/src`, `scripts/`, `tests/`.

---

## 3. Thiết kế

### 3.1 Luồng dữ liệu
```
step4_results.json  limitations_data.untracked_unarchived_inputs.files  (nhóm S) ─┐
provenance.json     checkpoints.{deployed, known.*}                     (nhóm A) ─┼─► archive_private_kaggle.plan_files
alphabet_ckpt_provenance.NESTED_PREDICTIONS                             (nhóm A) ─┘
   ─► stage   (thư mục NGOÀI repo; sha256 khớp JSON; quét chuỗi bí mật; ≤ 2 GiB)
   ─► upload  (dùng lại archive_step4_kaggle.upload: slug chưa có → dataset_create_new(public=False), đúng một lần)
   ─► verify  (ready; private từ 2 nguồn; danh sách + kích thước; tải về, băm lại) ─► manifest JSON (commit)
   ─► restore (tải về NGOÀI repo; sha256 theo manifest; chép vào local_path chỉ khi chưa có; không ghi đè)
manifest đã verify + commit ─► git rm --cached alphabet_real_best.pt (commit riêng) ─► README / data_registry
```
Không chạy model, không đọc TEST, không sinh số liệu ML mới. Không đụng module tiền xử lý chung (`src/data/*`), trừ việc f3 truyền
một số thứ tự khác vào `HarmonizedLiveSession.process` (không đổi `harmonize` hay segmenter).

### 3.2 (b) Status: hàm `public_trained_on`
Thêm hàm thuần ở `backend/main.py`, cạnh `alphabet_data_provenance`:
```
public_trained_on(trained_on: Any) -> Optional[Dict[str, Any]]
  - trained_on không phải dict                       -> None
  - out = {}
  - trained_on["source"] là str                      -> out["source"] = source
  - trained_on["signers"] là list/tuple, mọi phần tử là str
                                                     -> out["n_signers"] = len(set(signers))
  - out rỗng                                         -> None
  - không bao giờ chép khóa nào khác (clips, signers, …)
```
- Status (`available: true`): `"trained_on": public_trained_on(meta["trained_on"])`. `data_provenance` vẫn tính từ
  `meta["trained_on"]` gốc như cũ. `_alphabet_meta` giữ nguyên (không trả ra ngoài). Nhánh `available: false` không đổi.
- Kiểm với test cũ: không có `trained_on` → `None` ✓; `{"source": "hauuto", "signers": ["s1"], "clips": 1}` →
  `{"source": "hauuto", "n_signers": 1}` ✓; `{"source": "somewhere_else"}` → `{"source": "somewhere_else"}` ✓.
- Hợp đồng mới: `trained_on` là `null` hoặc object chỉ có các khóa trong `{"source", "n_signers"}`; không trả tên người ký.
  Cập nhật docstring của module (dòng 10) và của route (dòng 710–711).

### 3.3 (c) Script mới `scripts/archive_private_kaggle.py`

**Chọn dataset private MỚI, không tạo version mới của `phmvnsm33/vslt-step4-artifacts`.** Lý do:
1. Script bước 4 và test guard của nó cấm `dataset_create_version`. Nếu tạo version mới, file trên Kaggle sẽ khác manifest đã
   APPROVE mà `report_step4.py` và test ca 27/32 đọc. Chạy lại `verify` của bước 4 sẽ ra exit 3 (danh sách file khác staging).
2. Đường `dataset_create_version` chưa được đọc mã hay kiểm về chế độ private (kế hoạch 02 chỉ đọc `create_new` và `metadata_update`).
   Đường `dataset_create_new(public=False)` đã được chạy thật và kiểm private từ 2 nguồn.
3. Hai nhóm file khác nguồn dữ liệu (hauuto so với QIPEDC/VSL-GH), nên cần mô tả giấy phép khác nhau.
4. Version cũ không xóa được riêng lẻ; một dataset riêng thì người dùng có thể xóa cả dataset nếu cần.
Cái giá: có 2 slug; câu Giới hạn của REPORT bước 4 không tự ngắn lại (việc theo sau, §6).

**Slug:** `phmvnsm33/vslt-provenance-artifacts` (tham số `--dataset`, bắt buộc; không có giá trị mặc định trong mã).
Title: "VSLT provenance evidence and untracked inputs". License metadata: `unknown`. `isPrivate: true`.

**Dùng lại, KHÔNG sửa `scripts/archive_step4_kaggle.py`:** import `ArchiveError`, `sha256_file`, `require_outside_repo`,
`check_dataset_ref`, `parse_sums`, `sums_text`, `read_metadata`, `check_staging`, `upload`, `wait_ready`, `private_from_list`,
`private_from_metadata`, `remote_files`, `git_head`, `pkg_version`, `kaggle_api`. Mã thoát giống hệt: 0 ok; 2 thiếu input / tham số
sai / đường dẫn tạm trong repo / metadata không có `isPrivate: true` / **có chuỗi bí mật** / **tổng > 2 GiB**; 3 sha256, tập file,
kích thước lệch hoặc restore gặp file khác sha; 4 không xác minh được private (DỪNG); 5 slug đã có; 6 Kaggle/API/mạng.

**`plan_files(results_path, provenance_path, src_root=ROOT)`** → danh sách sắp theo `archive_name`, mỗi phần tử:
`{group, role, local_path, source, archive_name, expected_sha256, expected_sha256_source, licence_status, licence_note}`.
- Nhóm S: mỗi phần tử của `limitations_data.untracked_unarchived_inputs.files`: `group="step4_untracked_input"`, `role` = `role` trong
  JSON, `expected_sha256` = `sha256` trong JSON, `expected_sha256_source =
  "reports/step4_2026-09-26/step4_results.json#limitations_data.untracked_unarchived_inputs"`. Khóa thiếu hoặc danh sách rỗng → exit 2.
- Nhóm A: mỗi khóa của `checkpoints` trong provenance.json (sắp tên khóa): `group="alphabet_provenance"`, `role` = tên khóa,
  `expected_sha256` = `sha256`, `expected_sha256_source = "reports/alphabet_deploy_2026-09-27/provenance.json#checkpoints.<khóa>"`.
  Khóa có `exists` khác `true` hoặc thiếu `sha256` → exit 2.
- Cộng `NESTED_PREDICTIONS` (đọc hằng từ `scripts/alphabet_ckpt_provenance.py`; cách đọc do coder chọn, vd. import hoặc `ast`):
  `group="alphabet_provenance"`, `role="nested_predictions (V6)"`, `expected_sha256=None`, `expected_sha256_source=None`.
- Giấy phép (hằng trong script, nội dung lấy từ `docs/data_registry.md`, không phải số liệu):
  - nhóm A: `licence_status="unknown"`, `licence_note` = "hauuto/vietnamese-sign-language-alphabet: licence unknown
    (docs/data_registry.md §1b); private, internal use only".
  - nhóm S: `licence_status="redistribution_not_stated"`, `licence_note` = "derived from QIPEDC and/or VSL-GH: QIPEDC educational /
    academic research use, redistribution not stated (docs/data_registry.md §1); VSL-GH MIT per docs/data_registry.md §2 (not
    re-verified); private".
- `local_path` phải là đường dẫn tương đối, không có `..`, không có ký tự ổ đĩa. `archive_name = local_path.replace("/", "__")`.
  Tên trùng → exit 2. Cùng `local_path` xuất hiện ở cả 2 nhóm → exit 2.

**`stage --results R --provenance V --staging S --dataset D`:** như `archive_step4_kaggle.stage`: S ngoài repo và chưa tồn tại; mọi
nguồn phải có (thiếu → 2); sha256 nguồn = `expected_sha256` khi khác `None` (lệch → 3); quét bí mật (dưới đây); tổng byte ≤
`MAX_TOTAL_BYTES = 2 * 1024**3` (vượt → 2, thông báo "hỏi người dùng"); chép vào thư mục tạm cạnh S, băm lại bản sao, ghi
`SHA256SUMS` + `dataset-metadata.json` (`isPrivate: true`, `id` = D, title, licenses `[{"name": "unknown"}]`, description nêu nội dung,
nguồn dữ liệu, "licence of the source data unknown / redistribution not stated; internal use only, do not redistribute"), rồi
`os.replace`. Lỗi bất kỳ → không để lại thư mục staging.

**Quét bí mật (trong `stage`, trước khi chép):** mọi nguồn có đuôi `.log`, `.json`, `.csv`, `.txt`, `.md` được đọc dạng byte và
khớp các mẫu (tên mẫu → regex): `kaggle_token` `KGAT_[A-Za-z0-9]`, `json_key` `"key"\s*:\s*"`, `kaggle_key_env` `KAGGLE_KEY`,
`api_key` `(?i)api[_-]?key\s*[:=]`, `token_assign` `(?i)(access|auth)[_-]?token\s*[:=]`, `github_token` `ghp_[A-Za-z0-9]{20}`,
`hf_token` `hf_[A-Za-z0-9]{20}`. Có khớp → exit 2, thông báo chỉ gồm đường dẫn + tên mẫu, KHÔNG in đoạn khớp.

**`upload --staging S --dataset D`:** gọi thẳng `archive_step4_kaggle.upload(S, D, api)`.

**`verify --staging S --dataset D --download-dir X --manifest-out M --results R --provenance V`:** giống
`archive_step4_kaggle.verify`, chỉ khác danh sách lấy từ `plan_files(R, V)`; phần tử có `expected_sha256` khác `None` phải bằng
`SHA256SUMS`. Manifest có đúng 5 khóa đầu như bước 4: `generated_by`, `dataset` (có `is_private: true` và
`is_private_sources: {"dataset_list_mine": true, "dataset_metadata": true}`), `files`, `sha256sums_file`, `verified`. Mỗi phần tử
`files` có đúng các khóa `group, role, local_path, archive_name, size_bytes, sha256, sha256_after_download, expected_sha256_source,
licence_status, licence_note`. Đường dẫn manifest: `reports/private_archive_<YYYY-MM-DD>/kaggle_archive_manifest.json` (ngày chạy
`verify`, theo giờ Việt Nam). Lỗi bất kỳ → không ghi manifest.

**`restore --manifest M --download-dir X [--root DIR] [--only LOCAL_PATH ...]`:** đọc manifest; X ngoài repo; `--root` mặc định là
gốc repo, nếu khác thì phải nằm NGOÀI repo (để thử khôi phục mà không đụng repo). Tải dataset (`dataset_download_files`, `unzip=True`)
vào thư mục tạm trong X; băm mọi file được chọn và so với `manifest.files[*].sha256` (lệch → 3, không ghi gì). Rồi kiểm TOÀN BỘ trước
khi ghi: `<root>/<local_path>` đã có với sha256 bằng manifest → bỏ qua (in "đã có"); đã có với sha256 khác → 3, không ghi file nào;
chưa có → chép sang tên tạm cạnh đích rồi `os.replace`. Không bao giờ ghi đè, không ghi ra ngoài các `local_path` trong manifest.
`--only` là đường dẫn không có trong manifest → 2.

CẤM trong `scripts/archive_private_kaggle.py`: `public=True`, `"--public"`, `dataset_metadata_update`, `metadata --update`,
`dataset_delete`, `dataset_create_version`. Script không đọc, in hay ghi credential.

### 3.4 (a) Gỡ khỏi index (sau khi (c) đã verify và manifest đã commit)
- `git rm --cached -- reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`. Không xóa file trên đĩa.
- `.gitignore`: chỉ THÊM một dòng chú thích ngay sau dòng `reports/**/*.npz`, ví dụ:
  `# A3 (2026-09-28): alphabet_real_best.pt gỡ khỏi index (lịch sử đã push vẫn còn), lưu ở dataset private — xem reports/private_archive_*/`.
  Không xóa hay sửa dòng nào khác.
- README: THÊM mục ngắn "Artifact không nằm trong git" (≤ 15 dòng): hai dataset private (ref lấy từ hai manifest), đường dẫn hai
  manifest, lệnh `restore`, câu "Dataset private theo Kaggle API; chỉ tài khoản chủ và người được chia sẻ tải được (danh sách chia sẻ
  không được kiểm)". Không đưa số liệu nào vào README.
- `docs/data_registry.md:44`: thay vế "is already committed and pushed in the public repo; whether to keep it there is the owner's
  call" bằng câu nói đúng hiện trạng: đã commit ở `429b289` và đã push lên `origin/fix/audit-round2`; gỡ khỏi index ở commit B7 (lịch
  sử không viết lại, nên file vẫn còn trong lịch sử đã push); bản lưu ở dataset private `<ref>`. Không đổi câu nào khác.

### 3.5 (e) Chỉ kiểm, không sửa
Lệnh (ghi output vào progress_log):
`ls -l ../_backup_step4/REPORT_partial.md`; `sha256sum ../_backup_step4/REPORT_partial.md`;
`git ls-files -- '*REPORT_partial.md'` (kỳ vọng rỗng); `git log --all --oneline -- '*REPORT_partial.md'` (ghi nguyên output, dù rỗng hay
không); `git check-ignore -v reports/_probe/x.pt reports/_probe/x.npz` (đường dẫn giả, không tạo file); `grep -n` hai dòng trong
`.gitignore`. Nếu `REPORT_partial.md` không có ở `../_backup_step4/`, hoặc đang được track → điểm dừng §7 (không tự di chuyển, không tự
xóa).

### 3.6 (f) Việc nhỏ
- **f1:** THÊM lớp test mới vào CUỐI `tests/test_live_harmonized_equivalence.py` (không sửa lớp cũ). Lớp này dựng lại cùng môi trường
  như `TestWebSocketEndToEnd` (cùng `VSL_MODEL_TYPE=stgcn_h360`, reload, khôi phục env trong `tearDownClass`), stream đúng 2 clip đầu
  của `select_train_clips(8, 0)` theo cùng cách (`_stream`), và assert mỗi clip có `len(ws_events) >= 1`. Được phép gọi lại
  hàm/`_stream` của lớp cũ; không được sửa lớp cũ; không kế thừa lớp cũ (tránh chạy lại test cũ). Cùng điều kiện
  `skipUnless(AVAILABLE, REASON)`.
- **f2:** file test mới `tests/test_backend_model_unavailable.py` (xem AC6).
- **f3:** đổi số thứ tự truyền vào segmenter, không đổi `src/`:
  trong `_process_frame_worker_harmonized`, ngay trước `session.process`, tính
  `push_seq = item["dropped_frames"] + stats["frame_seq"] + 1` và gọi `session.process(frame_bgr, item["t_s"], seq=push_seq)`.
  (`item["dropped_frames"]` = `counters["dropped"]` lúc worker lấy frame, đã gán ở `:1423`; `stats["frame_seq"]` = số frame đã đưa
  vào segmenter thành công.) Với các frame đẩy vào segmenter `p_1 … p_n` của một đoạn, `seq_n − seq_1 + 1 − n = d_n − d_1` = số frame
  bị ghi đè trong slot giữa lúc lấy `p_1` và lúc lấy `p_n`.
  **Hợp đồng mới của `sign_result.segment.dropped_frames`:** số frame hợp lệ bị bỏ vì worker bận (ghi đè slot), nằm giữa frame đầu và
  frame cuối của đoạn. KHÔNG đếm: message lỗi (ở receive hay ở worker, vd. `bad_message`, `bad_config`, `bad_timestamp`,
  `decode_failed`, `unsupported_format`, `frame_too_small`, `frame_too_large`), message control, message rỗng. `received_seq` trong
  message và `frame_result.dropped_frames` giữ nguyên nghĩa cũ. Ghi hợp đồng này vào docstring của `websocket_live_stream`.
  Nếu `session.process` ném lỗi thì `stats["frame_seq"]` không tăng (đúng như hiện tại), nên số thứ tự không nhảy.
- **f4:** `get_classes` dùng `_active_model()`; bắt `ModelUnavailable` → `_model_unavailable_response(e)` (503,
  `{"status": "model_unavailable", "detail": …}`, detail ≤ 200 ký tự). Khi thành công: body giữ đúng 2 khóa `total`, `classes`.
  Ghi chú (không làm ở đây): `detail` có thể chứa tên file/đường dẫn tương đối từ exception; giống `/api/health` hiện tại, để Việc 5 xử lý
  cùng bảo mật.

### 3.7 Module tiền xử lý chung
Không đổi `src/data/harmonized.py`, `src/data/alphabet_preprocessing.py`, `src/inference/harmonized_live.py`,
`src/inference/sign_segmenter.py`. f3 chỉ đổi giá trị `seq` mà backend truyền vào; test tương đương AC4/AC5 của kế hoạch 04 phải vẫn
pass (chúng truyền `seq` theo cách riêng và không có frame rơi).

---

## 4. Chia việc

Quy tắc chung (mọi bước): `impact` upstream trước khi sửa symbol có sẵn (ít nhất `get_fingerspelling_status`, `get_classes`,
`_process_frame_worker_harmonized`, `websocket_live_stream`; UNKNOWN → xác nhận bằng text search); `detect-changes --scope all` trước
MỖI commit, ghi risk vào commit message; chỉ `git add <đường dẫn cụ thể>`; không commit `*.pt`, `*.npz`, `*.log`, dữ liệu, staging,
file tải về; không đụng 3 file data bị xóa của người dùng và các file untracked của người dùng; không amend. Viết test TRƯỚC code ở mỗi
bước có code, và ghi lần chạy FAIL trước khi sửa (tên test + lỗi) vào commit message.

Chặng giao gợi ý cho coder: **[B0, B1, B2] → [B3, B4] → [B5] → [B6, B7, B8]**. Mỗi bước B1–B8 kết thúc bằng đúng một commit.

**B0 — Kiểm trạng thái, không commit (≈ 0.5 giờ).**
1. `git log --oneline -1` (ghi hash); `git status --porcelain` (lưu ra file tạm NGOÀI repo để so ở cuối).
2. Chạy lệnh AC2 với 20 module cũ (chưa có module mới) → ghi số test "trước", số skip và lý do.
3. `git ls-files -- '*.pt' '*.pth' '*.npz' '*.ckpt' '*.onnx' '*.safetensors'` → ghi nguyên danh sách. Nếu có file nào KHÁC
   `alphabet_real_best.pt` được train trên dữ liệu giấy phép chưa rõ → điểm dừng §7 (chỉ báo, không gỡ).
4. Làm (e) theo §3.5, ghi output. Điểm dừng nếu (e) sai.
5. `.venv/Scripts/kaggle --version` và `.venv/Scripts/kaggle datasets list --mine` (lệnh đọc). Không xác thực được → B6 bị chặn (§7),
   B1–B5 vẫn làm.

**B1 — (b) status chỉ trả nguồn + số người ký (≈ 1 giờ).** Test AC3 trước → code §3.2 → chạy AC3 + `tests.test_fingerspelling_limits`
+ `tests.test_fingerspelling_api` + `tests.test_fingerspelling_deployed`. Commit B1 (`backend/main.py`, `tests/test_status_privacy.py`).

**B2 — (f2, f4) `/api/classes` 503 + test checkpoint không phục vụ được (≈ 1 giờ).** Test AC6 trước (ca `/api/classes` FAIL với 500
trước khi sửa; các ca health/model_info/WS có thể PASS ngay, vì hành vi đó đã đúng) → sửa `get_classes` → chạy AC6 +
`tests.test_ws_live_contract`. Commit B2.

**B3 — (f3) `dropped_frames` (≈ 1.5 giờ).** Test AC7 trước (AC7-a và AC7-b FAIL trước khi sửa) → sửa §3.6 f3 + docstring → chạy AC7 +
`tests.test_ws_live_contract` + `tests.test_harmonized_live` + `tests.test_live_harmonized_equivalence`. Commit B3.

**B4 — (f1) AC5 không PASS rỗng (≈ 0.5 giờ).** Thêm lớp test mới (AC8) → chạy module. Ghi thời gian chạy của module trước/sau.
Commit B4.

**B5 — (c) Script lưu trữ + test với API giả (≈ 2 giờ).** Test AC9 trước → viết `scripts/archive_private_kaggle.py` → chạy AC9 +
`tests.test_archive_step4_kaggle` (không đổi). Commit B5. Không chạy lệnh Kaggle ghi nào trong bước này.

**B6 — (c) Chạy thật (≈ 1 giờ + thời gian Kaggle xử lý).** Phụ thuộc: B5; B0 mục 5 xác thực được. Tại HEAD sạch
(`git status --porcelain -- scripts src tests backend` rỗng):
```
.venv/Scripts/python scripts/archive_private_kaggle.py stage --results reports/step4_2026-09-26/step4_results.json \
   --provenance reports/alphabet_deploy_2026-09-27/provenance.json \
   --staging ../_kaggle_staging/vslt-provenance-artifacts --dataset phmvnsm33/vslt-provenance-artifacts
.venv/Scripts/python scripts/archive_private_kaggle.py upload --staging ../_kaggle_staging/vslt-provenance-artifacts \
   --dataset phmvnsm33/vslt-provenance-artifacts
.venv/Scripts/python scripts/archive_private_kaggle.py verify --staging ../_kaggle_staging/vslt-provenance-artifacts \
   --dataset phmvnsm33/vslt-provenance-artifacts --download-dir ../_kaggle_staging/verify_provenance \
   --manifest-out reports/private_archive_<YYYY-MM-DD>/kaggle_archive_manifest.json \
   --results reports/step4_2026-09-26/step4_results.json --provenance reports/alphabet_deploy_2026-09-27/provenance.json
```
Lưu stdout/stderr + exit code mỗi lệnh vào `../_kaggle_staging/*.out` (ngoài repo). `verify` exit 6 vì Kaggle chưa ready → chạy lại
`verify` (không chạy lại `upload`). Exit 4 → DỪNG. Exit 5 → DỪNG, hỏi. Exit 2 do bí mật hoặc > 2 GiB → DỪNG, hỏi. Exit 3 → DỪNG
(vấn đề dữ liệu mới). Thành công → commit B6 (chỉ manifest).
Sau commit, kiểm khôi phục (AC10-e): (1) `restore --manifest <manifest> --download-dir ../_kaggle_staging/restore_dl
--root ../_kaggle_staging/restore_root` (root tạm ngoài repo) → mọi file được ghi, sha256 đúng; (2) `restore` với root mặc định →
mọi file "đã có", không file nào bị ghi. Rồi chạy lại `scripts/alphabet_ckpt_provenance.py --out <thư mục tạm>/provenance.json`
và so với JSON đã commit (AC10-d).

**B7 — (a) `git rm --cached` + .gitignore + README + data_registry (≈ 0.5 giờ).** Phụ thuộc: B6 đã commit và AC10 PASS. Test AC11
trước (FAIL vì file còn track) → thực hiện §3.4 → chạy AC11 + `tests.test_fingerspelling_api` (TestRealClipEquivalence vẫn CHẠY,
không skip, vì file còn trên đĩa). Commit B7 gồm: xóa khỏi index file .pt, `.gitignore`, `README.md`, `docs/data_registry.md`,
`tests/test_private_artifacts.py`. Kiểm `git show --name-status HEAD` có `D	reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`
và file vẫn còn trên đĩa (`sha256sum` bằng manifest).

**B8 — Đóng việc (≈ 0.5 giờ).** Chạy AC2 đầy đủ (25 module). So `git status --porcelain` với file lưu ở B0: giống hệt (mọi thay đổi
của kế hoạch đã commit; file .pt vừa gỡ không xuất hiện vì đã bị ignore). THÊM 1 dòng progress_log (AC13). Commit B8. Orchestrator
gọi vslt-reviewer.

Ước lượng GPU: **0 giờ**. Lệnh Kaggle ghi: đúng 1 `dataset_create_new` (bên trong `upload`).

---

## 5. TIÊU CHÍ CHẤP NHẬN (hợp đồng — coder không được đổi; chỉ planner đổi và phải ghi lý do)

Mọi lệnh Python chạy qua `.venv/Scripts/python` với `PYTHONIOENCODING=utf-8`, từ thư mục gốc repo. "Mới" = file/lớp test do kế
hoạch này thêm. Test mới không cần mạng, không ghi file trong repo (chỉ thư mục tạm), không skip trên máy này.

**AC1 — Phạm vi thay đổi.** `git diff --name-status P5 HEAD` chỉ chứa:
`backend/main.py` (M); `scripts/archive_private_kaggle.py` (A); `tests/test_status_privacy.py`, `tests/test_backend_model_unavailable.py`,
`tests/test_ws_dropped_frames.py`, `tests/test_archive_private_kaggle.py`, `tests/test_private_artifacts.py` (A);
`tests/test_live_harmonized_equivalence.py` (M, chỉ thêm dòng); `reports/private_archive_<date>/kaggle_archive_manifest.json` (A);
`reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` (D, chỉ khỏi index); `.gitignore` (M, chỉ thêm 1 dòng chú
thích); `README.md` (M); `docs/data_registry.md` (M); `docs/progress_log.md` (M, chỉ thêm); `docs/plans/05-thuc-thi-quyet-dinh-0928.md`
(chỉ planner). KHÔNG đổi: `src/`, `configs/`, `frontend/`, `data/`, `checkpoints/`, `scripts/archive_step4_kaggle.py`,
`scripts/report_step4.py`, `scripts/alphabet_ckpt_provenance.py`, `reports/step4_2026-09-26/**`,
`reports/alphabet_deploy_2026-09-27/**`, `docs/reviews/*`, mọi test cũ khác. 3 file data bị xóa của người dùng vẫn ở trạng thái ` D`
chưa staged. Không file `.pt/.npz/.log/.csv` nào được THÊM vào git.

**AC2 — Không hồi quy.** Lệnh:
`PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity tests.test_report_step4 tests.test_fingerspelling_limits tests.test_fingerspelling_compose tests.test_fingerspelling_deployed tests.test_alphabet_ckpt_provenance tests.test_harmonized tests.test_sign_segmenter tests.test_harmonized_live tests.test_ws_live_contract tests.test_live_harmonized_equivalence tests.test_archive_step4_kaggle tests.test_status_privacy tests.test_backend_model_unavailable tests.test_ws_dropped_frames tests.test_archive_private_kaggle tests.test_private_artifacts -v`
- 0 failure, 0 error, 0 skip trên máy này (mọi skip đều là FAIL tiêu chí; ghi lý do nếu có).
- Số test sau = số test B0 (20 module cũ) + số test mới; báo theo module, trước → sau.
- `git diff P5 HEAD -- tests/` với mọi file test ĐÃ CÓ ở `P5`: 0 dòng bắt đầu bằng `-` (ngoài header diff).
- `git status --porcelain` trước và sau khi chạy lệnh trên giống hệt (test không thay đổi file nào trong repo).

**AC3 — (b) Status không lộ tên người ký (`tests/test_status_privacy.py`).**
- a. Bảng `public_trained_on` (hàm thuần): `None`→`None`; `"x"`→`None`; `{}`→`None`; `{"clips": 5}`→`None`;
  `{"source": "hauuto"}`→`{"source": "hauuto"}`; `{"source": "hauuto", "signers": ["a", "b", "a"], "clips": 7}`→
  `{"source": "hauuto", "n_signers": 2}`; `{"signers": ["a"]}`→`{"n_signers": 1}`; `{"source": 3, "signers": "ab"}`→`None`;
  `{"source": "x", "signers": ["a", 1]}`→`{"source": "x"}`; `{"source": "x", "signers": []}`→`{"source": "x", "n_signers": 0}`.
- b. API với checkpoint fixture (trọng số seed, như `tests/test_fingerspelling_limits.save_fixture`), `trained_on =
  {"source": "hauuto", "signers": ["signer_alpha", "signer_beta"], "clips": 636}`: `body["trained_on"] == {"source": "hauuto",
  "n_signers": 2}`; `response.text` không chứa `signer_alpha`, `signer_beta`, `"clips"`; duyệt đệ quy mọi khóa và mọi giá trị chuỗi
  của body: không chuỗi nào chứa hai tên đó; `body["data_provenance"] == {"licence": "unknown", "usage": "internal only",
  "registry": "docs/data_registry.md#1b"}`.
- c. Checkpoint triển khai `checkpoints/alphabet_best.pt` (sha256 phải bằng `provenance.json` `checkpoints.deployed.sha256`, nếu
  không thì FAIL): giá trị mong đợi tính từ chính checkpoint (`torch.load(...)["trained_on"]`): `{"source": <source>,
  "n_signers": len(set(signers))}`; `response.text` không chứa tên nào trong `signers`. Không gõ tay số người ký hay tên. Được
  `skipUnless(file tồn tại)` cho clone sạch, nhưng trên máy này KHÔNG được skip.
- d. `tests/test_fingerspelling_limits.py:348–378` vẫn pass, không sửa.

**AC4 — (e) Bằng chứng.** Dòng progress_log (AC13) chứa nguyên output các lệnh ở §3.5: file `../_backup_step4/REPORT_partial.md`
có tồn tại + sha256; `git ls-files -- '*REPORT_partial.md'` rỗng; output `git log --all --oneline -- '*REPORT_partial.md'` (nguyên văn);
`git check-ignore -v` in một quy tắc của `.gitignore` cho cả `.pt` và `.npz`; hai dòng `reports/**/*.pt`, `reports/**/*.npz` có trong
`.gitignore` (số dòng). Không lệnh nào của (e) sửa hay di chuyển file.

**AC5 — (a) chạy test cũ trên máy này.** Sau B7, `tests.test_fingerspelling_api` chạy `TestRealClipEquivalence` (không skip) và pass;
`git diff P5 HEAD -- tests/test_fingerspelling_api.py` rỗng.

**AC6 — (f2, f4) Checkpoint không phục vụ được (`tests/test_backend_model_unavailable.py`).** Hai ca preprocessing, đều dựng từ
`tests.test_harmonized_live.PRE`: (i) `features` = `"harmonized_v9"`; (ii) `mediapipe_version` = `"0.0.0-test"`. Mỗi ca: patch
`api.GLOBAL_PREDICTOR=None`, `api.STGCN_CKPT_SHA256=None`, `api.VSLPredictor` = `MagicMock` trả về `FakePredictor` có preprocessing đó;
`TestClient(api.app, raise_server_exceptions=False)` không chạy lifespan. Rồi:
- a. `GET /api/health` → 503, `status == "model_unavailable"`, `len(detail) <= 200`.
- b. `GET /model/info` → 503.
- c. `GET /api/classes` → 503, `status == "model_unavailable"`, `len(detail) <= 200` (ở `P5` ca này ra 500: ghi lại khi chạy trước B2).
- d. WS `/ws/live-stream`: message đầu `{"type": "error", "code": "model_unavailable"}`, sau đó `websocket.close` code 1011.
- e. Sau a–d: `api.GLOBAL_PREDICTOR is None`; `VSLPredictor.call_count == 4` (mỗi request nạp lại một lần, không cache).
- f. Thêm ca: `VSLPredictor` ném `FileNotFoundError` → `/api/classes` 503 (không phải 500).
- g. Ca thành công: `FakePredictor` với `PRE` hợp lệ, và với preprocessing `{}` (legacy) → `/api/classes` 200,
  `set(body) == {"total", "classes"}`, `total == num_classes`, `classes == class_names`.

**AC7 — (f3) `dropped_frames` (`tests/test_ws_dropped_frames.py`).**
- a. WS, fixture của `tests.test_ws_live_contract._WsCase` (harmonized, `LoopExtractor`, `FakePredictor`): gửi các frame của ký hiệu.
  Khi `frame_result.segment.state == "recording"` (và trước `sign_result`), chèn lần lượt, mỗi cái kèm `expect_error` đúng mã:
  `'{"image": "abc", '` → `bad_message`; `{"type": "control", "action": "explode"}` → `bad_message`; frame có `timestamp` bằng
  timestamp hợp lệ trước đó → `bad_timestamp`; frame `data:image/png;base64,@@@not-base64@@@` với timestamp mới → `decode_failed`;
  frame PNG 320×240 với timestamp mới → `frame_too_small`. Gửi tiếp frame tới khi có `sign_result`. Assert: đúng 1 `sign_result`;
  `sign_result.segment.dropped_frames == 0`; mọi `frame_result.dropped_frames == 0`. (Ở `P5` giá trị là 5; ghi lại khi chạy trước B3.)
- b. Gọi thẳng `api._process_frame_worker_harmonized(item, session, stats)` với `HarmonizedLiveSession(FakePredictor(), PRE,
  extractor=LoopExtractor(...))` và `stats` như backend dựng (`{"frame_seq": 0, "last_done": None, "rates": deque(maxlen=30)}`).
  Mỗi item có `image` = PNG 640×480, `t_s` tăng 1/30 s, `received_seq = 1000 * i` (cố ý không liên quan), `client_ts`,
  `timestamp_source`, và `dropped_frames` là dãy cộng dồn do test đặt: tăng +2 ở một frame và +1 ở một frame khác, cả hai nằm giữa
  vùng `recording` của `sign_profile(x, 1.0, 2.5)`; có thêm một item ảnh hỏng ở giữa vùng `recording` (trả `[error]`, không vào
  segmenter). Bọc `session.process` bằng spy ghi `seq`. Assert: `sign_result.segment.dropped_frames == 3`; dãy `seq` được truyền
  tăng chặt và `seq[k+1] − seq[k] − 1 == d[k+1] − d[k]` với mọi k; item ảnh hỏng không làm `stats["frame_seq"]` tăng.
  Biến thể: đặt hai lần tăng ở vùng `idle` trước khi ký → `dropped_frames == 0`.
- c. `tests.test_ws_live_contract`, `tests.test_harmonized_live`, `tests.test_live_harmonized_equivalence` (AC4/AC5 cũ, có
  `dropped_frames == 0`) vẫn pass, không sửa.
- d. Docstring `websocket_live_stream` có câu định nghĩa `sign_result.segment.dropped_frames` như §3.6 f3.

**AC8 — (f1) AC5 không PASS rỗng.** `tests/test_live_harmonized_equivalence.py` có lớp MỚI ở cuối file, chạy (không skip) trên máy
này, và assert `len(ws_events) >= 1` cho TỪNG clip trong 2 clip đầu của `select_train_clips(8, 0)`; in danh sách
`(type, reason, gloss)` của từng clip. `git diff P5 HEAD -- tests/test_live_harmonized_equivalence.py`: 0 dòng `-`. Lớp mới không
kế thừa `TestWebSocketEndToEnd`. Sau khi chạy module, env `VSL_MODEL_TYPE`/`VSL_STGCN_CKPT` và `backend.main` trở về như trước
(module test khác chạy sau vẫn thấy model mặc định: AC2 pass khi chạy cả 25 module trong một tiến trình).

**AC9 — (c) Script lưu trữ, test với API giả (`tests/test_archive_private_kaggle.py`).** Mỗi ca một test; dùng thư mục tạm NGOÀI
repo; có thể dùng lại `FakeApi` của `tests/test_archive_step4_kaggle.py`.
1. `plan_files` trên fixture (2 file nhóm S; provenance có `deployed` + 3 khóa `known.*`; một `nested_predictions.csv`) → 7 phần tử,
   đúng `group`, `role`, `expected_sha256`, `expected_sha256_source`, `licence_status`, `licence_note` theo §3.3; sắp theo
   `archive_name`; `archive_name == local_path.replace("/", "__")`.
2. `plan_files` trên JSON THẬT đã commit (chỉ đọc 2 JSON và hằng, không băm file lớn): tập `local_path` == tập `path` của
   `limitations_data.untracked_unarchived_inputs.files` ∪ tập `path` của `provenance.json` `checkpoints.*` ∪ {`NESTED_PREDICTIONS`};
   có `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`, hai file `alphabet_nested_final.pt`,
   `reports/alphabet_nested_2026-09-25/primary/nested_predictions.csv`, `checkpoints/alphabet_best.pt`; mọi `expected_sha256` của
   nhóm S và A (trừ CSV) bằng giá trị trong JSON nguồn. Số phần tử so với độ dài danh sách trong JSON, không gõ tay.
3. Provenance có khóa `exists: false` → 2; thiếu `sha256` → 2; `local_path` trùng giữa 2 nhóm → 2; `local_path` tuyệt đối hoặc có `..`
   → 2; `untracked_unarchived_inputs` thiếu → 2.
4. `stage` thành công: staging có đúng các `archive_name` + `SHA256SUMS` + `dataset-metadata.json`; metadata `isPrivate is True`,
   `id == dataset`, licenses `[{"name": "unknown"}]`; `SHA256SUMS` khớp sha256 thật; sha256 của CSV được tính (không `None`).
5. `stage`: sha256 nguồn khác JSON → 3; thiếu nguồn → 2; staging trong repo → 2; staging đã tồn tại → 2. Mọi ca lỗi: không còn thư mục
   staging hay thư mục `.partial-*`.
6. Quét bí mật: với MỖI mẫu trong §3.3, một file `.log` fixture chứa chuỗi khớp (dựng lúc chạy test, không phải token thật) → 2,
   không có staging; stderr chứa đường dẫn và tên mẫu, KHÔNG chứa chuỗi khớp. File `.pt` chứa byte `KGAT_x` không bị quét (chỉ
   quét đuôi text).
7. Giới hạn kích thước: patch `MAX_TOTAL_BYTES` nhỏ hơn tổng → 2, không có staging.
8. `upload`: `archive_private_kaggle` dùng đúng hàm `archive_step4_kaggle.upload` (cùng đối tượng hàm, hoặc spy chứng minh được gọi);
   API giả → `dataset_create_new` được gọi đúng 1 lần với `public=False`; slug đã có → 5, không gọi create; metadata
   `isPrivate: false` → 2.
9. `verify` thành công → manifest có đúng 5 khóa đầu; mỗi phần tử `files` có đúng 10 khóa ở §3.3; `dataset.is_private is True`,
   `is_private_sources == {"dataset_list_mine": True, "dataset_metadata": True}`; `sha256_after_download == sha256` cho mọi file;
   `verified.n_files == len(plan_files(...))`.
10. `verify`: `dataset_list` báo không private / `dataset_metadata` `isPrivate` false / `dataset_list` lỗi → 4, không có manifest;
    danh sách file từ xa khác → 3; file tải về bị sửa → 3; chưa ready trước timeout → 6. Mọi ca lỗi: không có manifest.
11. `restore` vào `root` tạm: file chưa có → được ghi, sha256 đúng; file đã có cùng sha256 → không bị ghi (nội dung và mtime không
    đổi); một file đã có khác sha256 → 3 và KHÔNG file nào được ghi (kể cả file khác); file tải về bị sửa → 3, không ghi gì; `--only`
    với đường dẫn ngoài manifest → 2; `--download-dir` trong repo → 2; `--root` khác gốc repo mà nằm trong repo → 2.
12. Guard mã nguồn: `scripts/archive_private_kaggle.py` không chứa `public=True`, `"--public"`, `dataset_metadata_update`,
    `dataset_delete`, `dataset_create_version`, `metadata --update`.
13. `tests.test_archive_step4_kaggle` vẫn pass, không sửa; `git diff P5 HEAD -- scripts/archive_step4_kaggle.py` rỗng.

**AC10 — (c) Lưu trữ thật (bằng chứng ở progress_log + manifest đã commit).**
- a. Exit code: `stage` 0, `upload` 0, `verify` 0. Mọi lần chạy khác (kể cả thất bại) được liệt kê theo thứ tự, kèm exit code và lý do
  (đối chiếu `../_kaggle_staging/*.out`). Đúng MỘT lần `dataset_create_new` thành công trong toàn bộ kế hoạch.
- b. Manifest `reports/private_archive_<date>/kaggle_archive_manifest.json`: `dataset.ref == "phmvnsm33/vslt-provenance-artifacts"`,
  `is_private is true`, cả hai nguồn true, `status == "ready"`, `verified.file_list_matches` và `verified.downloaded_sha256_all_match`
  true, `verified.n_files == len(plan_files(JSON thật))`. `generated_by.git_commit` = HEAD lúc `verify`, và tại HEAD đó
  `git status --porcelain -- scripts src tests backend` rỗng.
- c. Reviewer kiểm bằng lệnh chỉ đọc: `kaggle datasets list --mine` có ref đó; truy cập ẩn danh trang dataset trả 403 hoặc 404.
- d. `scripts/alphabet_ckpt_provenance.py --out <tmp>/provenance.json` chạy sau B6: JSON bằng `reports/alphabet_deploy_2026-09-27/provenance.json`
  sau khi bỏ `generated_by` (so bằng `==` trong Python; in `True`).
- e. Khôi phục: `restore --root <tạm ngoài repo>` exit 0, mọi file của manifest có mặt dưới root tạm với sha256 bằng manifest;
  `restore` với root mặc định exit 0, in "đã có" cho mọi file, không file nào trong repo đổi (so `git status --porcelain` và sha256
  trước/sau).
- f. Không có lệnh Kaggle nào chứa `version`, `metadata --update`, `delete`, `kernels push` trong lịch sử lệnh của coder.

**AC11 — (a) Gỡ khỏi index (`tests/test_private_artifacts.py`, đọc trạng thái repo thật; thiếu manifest thì FAIL, không skip).**
Gọi `X = reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt`.
- a. `git --literal-pathspecs ls-files -z -- X` rỗng.
- b. `git check-ignore -q -- X` trả 0.
- c. Manifest mới nhất `reports/private_archive_*/kaggle_archive_manifest.json` có phần tử `local_path == X` với `sha256` bằng
  `provenance.json` `checkpoints["known.real_run"].sha256`; `dataset.is_private is True`, cả hai nguồn true.
- d. Không `local_path` nào trong manifest mới được git track (một lời gọi `git --literal-pathspecs ls-files -z -- <mọi path>` → rỗng).
  Nếu điều này sai với file nào khác X thì đó là phát hiện: coder báo planner, KHÔNG tự gỡ.
- e. Tập `local_path` của manifest == tập của `plan_files(JSON thật)`.
- f. Nếu X có trên đĩa thì sha256 của nó bằng manifest (điều kiện theo dữ liệu, không phải skip). Trên máy này X PHẢI có trên đĩa
  (ghi `sha256sum X` vào progress_log).
- g. `.gitignore` chứa đúng các dòng `reports/**/*.pt` và `reports/**/*.npz`; `git diff P5 HEAD -- .gitignore` chỉ có 1 dòng `+` bắt
  đầu bằng `#` và 0 dòng `-`.
- h. Lệnh (ghi output): `git show --name-status <B7>` có `D` cho X; `git merge-base --is-ancestor 429b289 HEAD` → 0 (lịch sử không bị
  viết lại); `git log --oneline -- X` liệt kê cả `429b289` và `<B7>`.

**AC12 — Tài liệu.** README có mục "Artifact không nằm trong git" chứa đúng hai ref (lấy từ hai manifest), đường dẫn hai manifest, và
lệnh `restore`; không có số liệu đánh giá nào mới trong diff README. `docs/data_registry.md` không còn vế "is already committed and
pushed in the public repo; whether to keep it there is the owner's call", và có `429b289` + ref mới. `git diff P5 HEAD -- README.md
docs/data_registry.md` chỉ chạm các chỗ trên.

**AC13 — Quy trình và progress_log.** Mỗi commit B1–B8 ghi trong message: symbol đã `impact` + risk, `detect-changes --scope all` (không
partial/truncated) + risk, và (bước có code) tên test FAIL trước khi sửa. progress_log THÊM đúng 1 dòng bảng cho kế hoạch 05 (ngày |
việc | kế hoạch | commit B1–B8 | kết luận review "chưa review" | việc tiếp theo "vslt-reviewer cho kế hoạch 05"), kèm đoạn ghi chú:
số test trước → sau theo module; danh sách `git ls-files` file nhị phân ở B0; bằng chứng (e); lịch sử lệnh Kaggle + exit code; ref,
`verified.n_files`, `total_bytes` chép từ manifest (nêu đường dẫn manifest); danh sách file theo `licence_status` ("unknown": nhóm A;
"redistribution_not_stated": nhóm S) và ghi riêng rằng `segments.csv` chỉ từ VSL-GH (MIT theo registry, chưa kiểm lại); sự trùng
sha256 của `checkpoints/stgcn_unified_best.pt` với file baseline trong `phmvnsm33/vslt-step4-artifacts` (nếu đúng); "REPORT bước 4 chưa
sinh lại (việc theo sau)"; kết quả AC10-d/e. Không sửa dòng cũ nào của progress_log.

**AC14 — Review.** vslt-reviewer: không FAIL. Reviewer tự chạy AC2, AC10-c (lệnh chỉ đọc), AC11-h; đột biến trong bộ nhớ để kiểm test
có răng: (i) trả lại `meta["trained_on"]` nguyên vẹn → AC3 FAIL; (ii) quay lại `seq=item["received_seq"]` → AC7-a/b FAIL;
(iii) `get_classes` gọi thẳng `get_or_load_predictor` → AC6-c/f FAIL; (iv) bỏ assert `>= 1` → không còn test nào bắt WS rỗng
(kiểm bằng cách cho WS trả 0 event: lớp mới AC8 FAIL).

---

## 6. Rủi ro dữ liệu/ML

- **Không có số liệu ML mới.** Không train, không đọc TEST, không đổi model. AC10-d chỉ chứng minh verdict provenance tái lập giống
  hệt JSON đã commit; không đưa ra số liệu mới nào.
- **Lộ dữ liệu có giấy phép chưa rõ.** Mọi file lưu trữ đều là private: `public=False` là hằng trong hàm `upload` dùng lại;
  metadata `isPrivate: true`; kiểm private từ 2 nguồn trước khi ghi manifest; cấm `metadata --update` (bẫy `isPrivate` → False).
  File giấy phép chưa rõ: toàn bộ nhóm A (hauuto: `alphabet_best.pt`, 2 `alphabet_nested_final.pt`, `alphabet_real_best.pt`,
  `nested_predictions.csv`, trong đó CSV có thể chứa định danh clip/người ký lấy từ đường dẫn hauuto). Nhóm S: suy ra từ QIPEDC
  (phân phối lại không được nêu) và/hoặc VSL-GH (MIT theo registry, chưa kiểm lại). Không file nào được commit vào git.
- **Bí mật trong log kernel.** Log Kaggle có thể chứa biến môi trường hay token. Quét trước khi chép; khớp → dừng, không upload, và
  không in đoạn khớp. Đây là quét theo mẫu, không chứng minh được "không có bí mật"; progress_log phải nói đúng như vậy.
- **`git rm --cached` và máy khác.** Commit B7 làm `git pull` trên máy khác xóa file khỏi thư mục làm việc của máy đó. Giảm nhẹ: B6
  (lưu trữ đã verify) đi trước; có `restore`; README nêu cách khôi phục. Lịch sử đã push vẫn chứa file (quyết định của người dùng:
  không viết lại lịch sử); không được nói "đã gỡ khỏi repo công khai".
- **Tên người ký vẫn còn ở chỗ khác (rủi ro còn lại, ngoài phạm vi).** `reports/alphabet_deploy_2026-09-27/provenance.json:49–54` (đã
  commit) và `docs/data_registry.md:45` chứa tên/ID người ký hauuto; checkpoint `alphabet_best.pt` cũng chứa. Quyết định của người dùng
  chỉ nói về API. Kế hoạch này không sửa các chỗ đó; orchestrator nêu cho người dùng như một câu hỏi không chặn.
- **Lệch train–realtime (f3).** Chỉ đổi số thứ tự dùng để đếm frame rơi; không đổi đầu vào của `harmonize` hay model. AC7-c giữ
  test tương đương AC4/AC5 của kế hoạch 04. `dropped_frames` sẽ được dùng cho DoD 8; định nghĩa mới phải được ghi vào
  `docs/phase12_api.md` ở Việc 5.
- **REPORT bước 4 cũ đi một phần (việc theo sau).** Câu Giới hạn của `reports/step4_2026-09-26/REPORT.md` vẫn nói 8 đầu vào "không
  nằm trong lưu trữ" (so với `phmvnsm33/vslt-step4-artifacts`). Câu đó vẫn đúng về dataset nó nêu, nhưng thiếu dataset mới. Sửa cần
  `report_step4.py` đọc nhiều manifest rồi sinh lại REPORT (có tiêu chí AC5/AC9 riêng). Đưa vào backlog mục 8 (Dọn dẹp); không làm ở đây.
- **Cỡ mẫu.** Không có thống kê. AC8 dùng 2 clip TRAIN chỉ để chứng minh test không PASS rỗng.
- **Giả lập trong test.** `FakePredictor`, `LoopExtractor`, `FakeApi` chỉ có trong test. Mã nguồn chính không có dữ liệu giả.

---

## 7. Điểm dừng

**Trước khi code: KHÔNG có điểm dừng bắt buộc.** Không đổi model mặc định; không cần dữ liệu người dùng; không đụng thay đổi chưa
commit của người dùng; `git rm --cached` và lưu trữ private đã được người dùng quyết định (STATE, dòng 2026-09-28); không viết lại
lịch sử; không xóa file trên đĩa.

**Điểm dừng có điều kiện (coder dừng bước đó, ghi progress_log, báo orchestrator; bước không phụ thuộc vẫn làm):**
1. B0-3: có file nhị phân được git track KHÁC `alphabet_real_best.pt` mà train trên dữ liệu giấy phép chưa rõ → báo, không gỡ (cần
   quyết định mới của người dùng).
2. B0-4 / (e): `../_backup_step4/REPORT_partial.md` không có, hoặc `REPORT_partial.md` đang được track → báo, không di chuyển/xóa.
3. B0-5: Kaggle không xác thực được → B6, B7 bị chặn (B7 phụ thuộc B6). Cần người dùng cấu hình credential; coder không đọc hay ghi
   credential.
4. B6: exit 4 (không xác minh được private) → DỪNG ngay; không chạy lệnh Kaggle nào khác; báo người dùng (có thể cần tự chuyển dataset
   về private trên web). Exit 5 (slug đã có) → hỏi người dùng. Exit 2 do bí mật hoặc tổng > 2 GiB → hỏi người dùng. Exit 3 (sha256 nguồn
   khác JSON đã commit) → vấn đề dữ liệu mới (autopilot §5) → báo.
5. AC11-d sai với file khác X (một file trong manifest đang được track) → báo planner; không tự gỡ.
6. Test cũ FAIL mà muốn pass phải sửa test cũ → KHÔNG sửa; báo planner.

**Sau B8:** không có điểm dừng bắt buộc. Orchestrator gọi vslt-reviewer; sau APPROVE chuyển sang Việc 5. Câu hỏi không chặn cho người
dùng: có gỡ tên người ký khỏi `provenance.json` và `docs/data_registry.md` không (§6).
