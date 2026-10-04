# Prompt cloud — Kế hoạch 15 (Level 1): hoàn tất A2a → R1 → A2b → R2 → R3

Nhánh làm việc: `cloud/2026-10-04-level1-rearm` (tách từ `feat/vslt-complete`). CHỈ push lên nhánh này.
KHÔNG push `feat/vslt-complete`, KHÔNG push `main`. Orchestrator local sẽ kéo nhánh về, review rồi merge.

Dán nguyên văn khối dưới đây làm prompt cho phiên Claude Code on the web.

---

Bạn là CODER của dự án VSLT (Vietnamese Sign Language Translator), làm việc trên nhánh `cloud/2026-10-04-level1-rearm`.
Không có Antigravity (`agy`) trên cloud: bạn TỰ viết code + test theo kế hoạch, như vai `vslt-coder-claude` (`.claude/agents/vslt-coder-claude.md`).

## 0. Đầu phiên (bắt buộc)
1. Làm đúng mục 2 của `docs/CLOUD.md` (unshallow, `.venv` → `/opt/vslt-venv`, kiểm Kaggle credential, GitNexus qua `npx -y gitnexus@latest`).
   Python trên cloud: `.venv/bin/python` (tài liệu local ghi `.venv/Scripts/python` → đổi tương ứng).
2. `git checkout cloud/2026-10-04-level1-rearm && git log --oneline -5` — HEAD phải chứa commit có file này.
3. Đọc: `docs/STATE.md` (dòng "Trạng thái phiên"), `docs/prompts/autopilot.md` mục 4 (quy tắc cứng), rồi kế hoạch 15 THEO THỨ TỰ:
   `docs/plans/15-level1-realtime-desktop.md` → `docs/plans/15-lan-sua-1.md` (scope §3b) → `docs/plans/15-lan-sua-2.md` → `docs/plans/15-lan-sua-3.md`
   (thứ tự bước, gate G1–G6, điểm dừng). Tiến độ: `docs/plans/15-progress.md`. Skill: `.claude/skills/vsl-landmark-consistency/SKILL.md`,
   `.claude/skills/vsl-evaluation-rigor/SKILL.md`.

## 1. Khôi phục dữ liệu Level 1 (bị gitignore; giấy phép hauuto chưa rõ — chỉ dùng nội bộ, KHÔNG commit video/landmark/khung hình)
- Landmark clip train: `kaggle kernels output phmvnsm33/vsl-extract-alphabet -p /tmp/k_alphabet` rồi đặt thư mục `alphabet_hands`
  vào `data/external/alphabet_hands_kaggle/alphabet_hands/` (cách làm đã ghi ở `docs/plans/12-progress.md` mục B4; kỳ vọng 688 file;
  có thể có lỗi ghi log kernel do encoding — chỉ ảnh hưởng file log).
- Video gốc hauuto (cho test tương đương E1 và AC-S18 nếu cần): `kaggle datasets download hauuto/vietnamese-sign-language-alphabet -p /tmp/hauuto --unzip`
  rồi đặt vào `data/external/hauuto_raw/raw/raw/<hau|khoi|tai|vy>/...` đúng cấu trúc mà `scripts/build_alphabet_tasks.py`/manifest mong đợi.
- Checkpoint `checkpoints/alphabet_best.pt`: khôi phục từ dataset PRIVATE `phmvnsm33/vslt-provenance-artifacts` bằng
  `scripts/archive_private_kaggle.py restore` (README mục "Artifact không nằm trong git"); sha256 PHẢI là `a6311820…5b708a2` (đầy đủ trong manifest).
- Thiếu credential/không tải được → DỪNG, ghi rõ trong báo cáo (mục 5), KHÔNG coi skip là pass, KHÔNG bịa số.

## 2. Việc cần làm (mỗi bước 1 commit, tiền tố `15:`; bước dở dùng `WIP 15:`)
Trạng thái lúc giao (HEAD 71299ea + commit file này): R0 XONG (a3970a6, 1acb4a5 — giả thuyết đứng: config hiện tại one_rate 0.31–0.37).
A2a DỞ ở commit WIP `dddfde8` (đã có mã + test S16/S17/S18; local đã xác minh: đỏ tại 6067611 = failures 4, xanh ở HEAD).
1. **A2a — hoàn tất (KHÔNG viết lại):** đọc `git show dddfde8`; xác minh lại đỏ tại 6067611 / xanh ở HEAD trên cloud; chạy impact
   (GitNexus) cho symbol bị sửa trong `src/inference/level1_segmenter.py`; ghi đỏ/xanh + impact vào 15-progress; commit `15: A2a …`.
   Sửa luôn: (a) 15-progress (1acb4a5) chép sai — chuỗi T n_clips là 70 (ghi 35), `current` L join 600 garbage_per_clip là 0.0104 (ghi 0.0000);
   (b) `reports/level1_realtime_2026-10-04/rearm_check_r0.json` có `configs.before_a2.git_commit = ""` — phải là `3ebc7b9`: sửa script để
   ghi đúng và sinh lại JSON từ commit sạch (KHÔNG sửa tay JSON); (c) script R0 loại 4 clip vì `min_detected_frames` — ghi lý do vào 15-progress
   (đã đếm trong JSON). Nếu (b) làm đổi số liệu R0 → ghi cả số cũ/mới.
2. **R1** — luật re-arm theo tư thế (`pose_change_rules`, `rearm_pose_dist`, `pose_distance`, tư thế neo, chống trôi khi hold) đúng §lần sửa 3;
   test AC-RA1…RA11 viết TRƯỚC (ghi log đỏ); luật tắt ⇒ bằng hệt cũ (AC-S18). Ngoại lệ test cũ DUY NHẤT: thêm 3 khóa mới vào dict tham số/config test.
3. **A2b** — `write_config`: bỏ dự phòng gõ tay "1ca53f3" và dự phòng `generated_by` (evidence chưa commit ⇒ RuntimeError, không ghi config);
   reason 5 khóa hiệu chỉnh mô tả quy tắc, không chứa số; chạy lại `--write-config` phải ra value BẰNG HỆT b0620a9 (chỉ reason đổi) — lệch ⇒ DỪNG.
   1 commit code + 1 commit config sinh lại.
4. **R2** — hiệu chỉnh `rearm_pose_dist` = 2 × p95 biến thiên tư thế khi giữ yên (clip train chữ cái, quy tắc P1) → `pose_evidence.json`
   (commit sạch, `git_commit` + `code_dirty false`); P2 độ phủ cặp chữ < 0.80 ⇒ DỪNG.
5. **R3** — chạy `scripts/level1_rearm_check.py` với luật bật; gate đặt trước G1 ≥ 0.90, G2 ≤ 0.05, G3 0 hand_lost, G4 đúng thứ tự,
   G5 rác ≤ 0.05, G6 clip đơn tụt ≤ 0.02 — KHÔNG đổi gate sau khi thấy số; đạt hết thì bật luật trong `configs/level1_realtime.json`; JSON báo cáo commit sạch.
   Bất kỳ G nào trượt ⇒ DỪNG, ghi số, KHÔNG nới gate.
DỪNG sau R3 (A3, C1, U1c cần webcam/người dùng → làm ở local).

## 3. Quy tắc cứng
- Không bịa số; số chỉ từ JSON có lệnh + commit + `code_dirty false`. JSON chuỗi ghép phải ghi "chuỗi ghép từ clip train — kiểm logic, không phải độ chính xác".
- Không sửa/skip/nới test cũ (ngoài ngoại lệ ở R1). Không đổi tiêu chí/gate sau khi thấy kết quả.
- Không đổi model mặc định (sha `checkpoints/alphabet_best.pt` giữ nguyên). Không train, không GPU.
- Scope file theo §3b của `15-lan-sua-1.md` (+ `scripts/level1_rearm_check.py`, `docs/plans/15-progress.md`, `reports/level1_realtime_2026-10-0*/`).
  KHÔNG sửa: file kế hoạch 11/13/14, `backend/main.py`, `realtime_demo.py`, `README.md`, `tests/test_backend_source_guard.py`, `.claude/`, `docs/prompts/`, `docs/STATE.md`.
- Không thêm vi phạm guard DoD 7: `.venv/bin/python -m tests.test_backend_source_guard` phải `known=9 allowed=36` như cũ.
- Commit bằng đường dẫn cụ thể (`git commit -- <paths>`), không `git add -A`. File tạm chỉ dưới `_work/` (gitignore qua .git/info/exclude — trên cloud
  có thể phải tự thêm `_work/` vào `.git/info/exclude`). Không commit dữ liệu hauuto/landmark/checkpoint.
- Trước MỖI commit: impact cho symbol có sẵn bị sửa + `detect-changes`; ghi vào 15-progress (thiếu GitNexus ⇒ text search + `git diff`, ghi rõ).
- Push sau mỗi bước hoàn chỉnh: `git push origin cloud/2026-10-04-level1-rearm`.

## 4. Test phải tự chạy (dán số thật)
- 7 module Level 1: `.venv/bin/python -m unittest tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_segmenter tests.test_level1_core tests.test_level1_demo tests.test_level1_guard tests.test_level1_rearm_check -v`
- Guard chính: `.venv/bin/python -m unittest tests.test_backend_source_guard`
- AC1-ngắn: lệnh ở `docs/plans/15-level1-realtime-desktop.md` (khoảng dòng 250–253) + `tests.test_level1_textbox tests.test_level1_segment_report tests.test_level1_rearm_check`.
  Test chập chờn đã biết: `tests.test_hand_landmarks_ws` TestReset — chạy riêng để xác nhận. Test skip vì thiếu dữ liệu: liệt kê, không coi là pass.
- Ghi rõ: landmark trích trên Linux có thể lệch nhẹ Windows (docs/CLOUD.md §4) — test tương đương so hai đường TRÊN CÙNG máy vẫn phải bằng hệt.

## 5. Kết thúc
Viết `docs/cloud_reports/level1-rearm-2026-10-04.md`: STATUS từng bước (DONE / CẦN PLANNER / BỊ CHẶN), danh sách commit, file đổi,
lệnh + kết quả test thật, số R0 (cũ/mới nếu đổi), `pose_evidence.json` + kết quả G1–G6 (số từ JSON + đường dẫn), mọi lệch kế hoạch/giả định,
dữ liệu đã khôi phục (nguồn + số file + sha checkpoint), phần chưa làm. Commit + push báo cáo lên nhánh cloud rồi dừng.
