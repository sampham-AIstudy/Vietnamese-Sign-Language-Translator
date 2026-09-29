# Kế hoạch 06 — tiến độ (coder; chặng 1: B0–B2)

- P6 = 797d0af (HEAD lúc coder bắt đầu B0, commit đã chứa kế hoạch 06)
- Bước đã xong: B0
- Bước đang làm: B1
- Bước còn lại: B1, B2 (chặng 1); B3–B9 (chặng sau, không làm trong phiên này)

## B0 (P6 = 797d0af, 2026-09-29)

Commit mở file tiến độ: 050d337 (chỉ `docs/plans/06-progress.md`).

1. `git status --porcelain` → `../_plan06_tmp/b0_status_porcelain.txt` (66 dòng; 3 dòng ` D` của người dùng + untracked).
2. AC2 mốc, 25 module cũ (log `../_plan06_tmp/b0_ac2.log`):
   `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m unittest <25 module của AC2, không có 4 module mới> -v`
   → `Ran 383 tests in 398.220s` / `OK`, 0 skip, 0 fail, 0 error.
   Theo module (`loadTestsFromName(...).countTestCases()`, `../_plan06_tmp/b0_counts.txt`):
   alphabet_preprocessing 6, aspect_correction 3, realtime 3, split_guards 6, translation_core 8, vsl_system 6,
   ws_throughput 0, fingerspelling_api 11, unified_split_integrity 4, report_step4 105, fingerspelling_limits 48,
   fingerspelling_compose 28, fingerspelling_deployed 9, alphabet_ckpt_provenance 16, harmonized 6, sign_segmenter 15,
   harmonized_live 10, ws_live_contract 18, live_harmonized_equivalence 9, archive_step4_kaggle 24, status_privacy 5,
   backend_model_unavailable 5, ws_dropped_frames 3, archive_private_kaggle 27, private_artifacts 8 — TỔNG 383.
   `git status --porcelain` sau khi chạy: giống hệt file trước (`diff` rỗng → in `SAME`).
3. `node --version` → `v25.9.0`. `cd frontend && npm ls --depth=0` (exit 0) → `../_plan06_tmp/b0_npm_ls.txt`
   (16 gói: @fontsource/dm-sans@5.3.0, @fontsource/epilogue@5.3.0, @types/react-dom@18.3.7, @types/react@18.3.31,
   @vitejs/plugin-react@4.7.0, autoprefixer@10.5.6, clsx@2.1.1, lucide-react@0.475.0, postcss@8.5.28,
   puppeteer-core@25.10.0, react-dom@18.3.1, react@18.3.1, tailwind-merge@3.6.0, tailwindcss@3.4.19,
   typescript@7.0.2, vite@6.4.3).
4. Edge: `ls -l "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"` → tồn tại (5001808 byte).
   → Điểm dừng §7-4 KHÔNG kích hoạt.
5. `.venv/Scripts/python -c "import mediapipe; print(mediapipe.__version__)"` → `0.10.14`.
6. GitNexus: `node .gitnexus/run.cjs analyze --index-only` (OK; cảnh báo FTS/BM25 build lỗi — chỉ ảnh hưởng tìm theo từ khóa).
   `impact <s> --direction upstream` (`../_plan06_tmp/b0_impact.txt`):
   - `websocket_live_stream`: risk UNKNOWN (0 caller resolve). Text search: route WS, gọi qua URL `/ws/live-stream` từ
     `frontend/src/components/{Phase12Pipeline,RealtimeStream}.jsx`, `scripts/smoke_test_phase12.py`, và tests
     `test_backend_model_unavailable`, `test_fingerspelling_limits`, `test_live_harmonized_equivalence`,
     `test_ws_live_contract`, `test_ws_throughput`.
   - `_parse_ws_message`: risk LOW (direct 1: `receive_loop` trong `websocket_live_stream`; 2 process).
   - `_decode_frame`: risk LOW (direct 2: `_process_frame_worker`, `_process_frame_worker_harmonized`/`run_harmonized`).
   - `health`: risk UNKNOWN (0 caller resolve). Text search `/api/health`: `frontend/src/App.jsx`,
     `tests/test_backend_model_unavailable.py`, `tests/test_ws_live_contract.py`. B0–B2 không sửa `health`.
