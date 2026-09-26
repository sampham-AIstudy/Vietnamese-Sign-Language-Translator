# Handoff 2026-09-26 — thiết lập orchestrator 3 agent, chưa chạy việc nào

## Trạng thái
- Nhánh: feat/vslt-complete (từ fix/audit-round2). Commit: 70a303e (agents), 23eee65 (WIP frontend, nhánh
  wip/frontend-fastapi) → merge e498a1d, b004bb5 (autopilot.md), + commit progress_log/handoff này.
- Quy trình: docs/prompts/orchestrator.md (phiên chính = orchestrator, KHÔNG tự code/plan/review),
  docs/prompts/autopilot.md (DoD, backlog, quy tắc, điểm dừng), docs/prompts/buoc4_5.md.
- Agent: .claude/agents/vslt-{planner,coder,reviewer}.md. Phiên trước KHÔNG nạp được (cần khởi động lại Claude Code).
  Người dùng chọn khởi động lại, không dùng general-purpose thay thế.
- Ghi chú người dùng (độ trễ DoD 8, alphabet_config.yaml, thay đổi chưa commit): docs/progress_log.md.
- Thay đổi chưa commit của người dùng (xóa 3 CSV trong data/, "data (2)/"): để nguyên.
- reports/audit_round2/*.json đã restore về bản commit 536c7c5; bản chạy lại lưu ở ../_backup_audit_round2_rerun_2026-09-24/.

## CẬP NHẬT 13:40 — phiên chính làm nốt 4b/4c theo yêu cầu người dùng (agent chưa nạp)
- v2 COMPLETE (68.7 min, repo c9296bf): runs/dict_keepz (QIPEDC-only 594 lớp, 795 clip train → VAL top-1 2.86%,
  giới hạn cỡ mẫu, không phải lỗi) và runs/run_keepz_seed43 (chỉ đo dao động seed). Log: runs/vsl-train-harmonized_v2.log.
- 348843f: report_step4.py áp đúng luật đăng ký trước (--run-360, --aux-runs, --dict-run-360).
- 9e3be95: kernel v3 (GPU0 run_keepz_360; GPU1 run_keepz_notrim → dict_keepz_360), PUSHED 13:36, đang chạy.
- 3 shard 360px COMPLETE; đang tải về data/processed/qipedc_kps360 (chậm) để chạy
  `scripts/shortcut_85.py --features harmonized --hand-z keep --qipedc-kps-dir qipedc_kps360 --out reports/step4_2026-09-26/4b`.
- Sau v3: tải output vào reports/step4_2026-09-26/runs/, chạy
  `PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/report_step4.py --baseline reports/unified_run_2026-09-25/run
  --runs H-keepz=<runs>/run_keepz H-dropz=<runs>/run_dropz --run-360 H-keepz-360=<runs>/run_keepz_360
  --aux-runs H-keepz-seed43=<runs>/run_keepz_seed43 H-keepz-notrim=<runs>/run_keepz_notrim
  --dict-run <runs>/dict_keepz --dict-run-360 <runs>/dict_keepz_360 --out reports/step4_2026-09-26/REPORT.md`,
  viết đề xuất 4c (A/B), vslt-reviewer, rồi DỪNG báo người dùng.
- GPU tuần này: v1 70.4 + v2 68.7 phút + v3 (~80 phút ước tính).

## Việc tiếp theo: Việc 1 backlog — Bước 4a
4a (và một phần 4b, kernel 4c) có vẻ ĐÃ làm trước quy trình 3 agent: reports/step4_2026-09-26/{4a/shortcut_85.json,
4b/*.json, runs/, PREREGISTRATION.md, REPORT_partial.md}; commit c8a7bdf, 5c1d080, c9296bf, c319928, 9b0ade1, 8cca760.
Kiểm tra trạng thái thật của kernel Kaggle 4c trước khi đi tiếp.

Prompt đã soạn cho vslt-planner (gửi nguyên văn):
> Lập kế hoạch cho VIỆC 1 của backlog: Bước 4a (kiểm tra lối tắt trên 85 lớp chung). DoD liên quan: tiền đề cho
> DoD 3 và DoD 9 (Giới hạn: lối tắt nguồn); điểm dừng là sau 4c. Đọc: docs/prompts/autopilot.md, docs/prompts/buoc4_5.md
> (mục 4a), docs/progress_log.md, .claude/handoffs/2026-09-25-gate0-level1-nested.md, .claude/handoffs/2026-09-26-orchestrator-setup.md,
> reports/source_diagnostics_2026-09-26/REPORT.md, reports/step4_2026-09-26/{PREREGISTRATION.md, REPORT_partial.md,
> 4a/shortcut_85.json, 4b/*.json, runs/}, commit c8a7bdf 5c1d080 c9296bf c319928 9b0ade1 8cca760.
> 4a có vẻ đã làm một phần/toàn bộ: đối chiếu từng yêu cầu 4a (bước 1–4) với cái đã có kèm bằng chứng; kế hoạch chỉ gồm
> phần còn thiếu/chưa đạt, hoặc là việc xác minh + hoàn thiện báo cáo 4a nếu đã đủ. Không coi số trong REPORT_partial.md
> là đúng khi chưa truy được về JSON có lệnh + commit hash. Việc nặng chỉ trên Kaggle, ghi ước lượng giờ GPU (≤ 10 giờ/tuần).
> Viết docs/plans/01-buoc4a-kiem-tra-loi-tat.md. Trả về: đường dẫn, tóm tắt ≤ 5 dòng, có/không "CẦN NGƯỜI DÙNG".
