# Handoff — GATE 0 follow-ups, Level 1 nested, sequence endpoint (2026-09-25, updated ~17:15)

## PAUSED HERE (owner moving to home machine) — resume in this order
1. `kaggle kernels status phmvnsm33/vsl-train-unified` (pushed ~16:40 on GPU T4 x2; seed 42 → `run/` = primary,
   seed 43 → `run_seed43/` = variance only). Wait with a background loop that ignores network errors.
2. When COMPLETE: `kaggle kernels output phmvnsm33/vsl-train-unified -p reports/unified_run_2026-09-25`
   (use `--file-pattern "run(_seed43)?/(metrics\.json|test_logits\.npz|test_predictions\.csv|test_per_class\.csv|history\.json|stgcn_unified_best\.pt|train\.log)$"`).
   If it failed with "split integrity FAIL" → stop and report to owner.
3. Finish QIPEDC test keypoints: 387/722 in `data/processed/qipedc_dl/qipedc_kps` (gitignored). Remaining list:
   recompute (test.csv qipedc rows whose npz is missing) and download in chunks of 100 names with
   `--file-pattern "qipedc_kps/(A|B|...)\.npz$"` (plain `kernels output` stops after ~200–500 files).
   Data root for scripts = `data/processed/qipedc_dl` + symlink/copy `data/processed/vslgh_segments` → easiest:
   pass `--data-root data/processed` after moving `qipedc_kps` to `data/processed/qipedc_kps`.
4. `python scripts/compare_isolated_models.py --new-ckpt reports/unified_run_2026-09-25/run/stgcn_unified_best.pt --new-metrics .../run/metrics.json --data-root data/processed --out reports/unified_run_2026-09-25/compare_old_new.json`
   (sanity line must reproduce metrics.json test top-1).
5. `python scripts/report_unified.py --run reports/unified_run_2026-09-25/run --extra-runs reports/unified_run_2026-09-25/run_seed43 --compare reports/unified_run_2026-09-25/compare_old_new.json --out reports/unified_run_2026-09-25/REPORT.md`
6. STOP at GATE: send owner the Level 2 report + gate table. Do NOT swap backend default before approval
   (keep old ckpt in checkpoints/). Then Việc 5 only after owner moves frontend WIP to its own branch.
If the home machine is a different computer: gitignored local data (hauuto, hcmue_kps, qipedc_dl, checkpoints/)
is not in git — re-download (hauuto/QIPEDC from Kaggle; HCMUE videos only exist on the original machine).

Supersedes `2026-09-25-after-cleanup.md`. Branch `fix/audit-round2` @ `d1c844f`, pushed. Reply in Vietnamese.
Owner works gate by gate: stop and report at each GATE. Owner WIP — never stage/commit/stash: `frontend/*`,
`requirements.txt`, `tests/test_realtime.py`, `start_fullstack.ps1`, `reports/audit_round2/v1_*.json`, `v6_*.json`,
deleted `app/`, `backend/*.js*`, `data (2)/…`, `data/*.csv` (owner moves frontend to its own branch before Việc 5).

## State
| Item | Status | Next |
|---|---|---|
| `phmvnsm33/vsl-extract-qipedc` | RUNNING since ~09:55 (no progress visible) | when done: check npz count ≈ 4362, then push `kaggle/vsl-train-unified` (GPU) |
| Level 2 checks (a)(b)(c) | DONE: VSL-GH cut by annotated start/end times; S06 test-only; QIPEDC 0/1227 groups cross splits; `train_unified.assert_split_integrity` FAILs hard (8935120) | — |
| Level 2 report | TODO after training | groups: vslgh rows (S06), qipedc-only classes, total; Top-1/5 + Wilson from `test_logits.npz` |
| Việc 3 gate | script ready `scripts/compare_isolated_models.py` | needs qipedc_kps locally (download kernel output) + new ckpt; old model smoke: S06 0/59, HCMUE 0/26 top-1 |
| HCMUE external | 47 videos (33 labels) ∩ 876 classes extracted → `data/processed/hcmue_kps` (320×240) | no signer IDs: report by region, say so |
| Level 1 | nested LOSO done; deployed `checkpoints/alphabet_best.pt` (bigru 120 frame, local, gitignored) | — |
| Việc 4 | DONE (6dd0202): `/api/fingerspelling/sequence`, image → 409, tests pass | — |
| MCP | sequential-thinking + playwright added (local scope, `cmd /c npx`); Connected | available next session |

## Level 1 numbers (nested LOSO, `reports/alphabet_nested_2026-09-25/REPORT.md`)
Letters 85.6 [74.8, 96.4]; tones 40.8 [7.5, 74.2]; overall 77.1 [62.7, 91.6]; QIPEDC letters 62.5% (40 recordings) [47.0, 75.8].
tai: fps not the cause (PTS constant); session B clips 1.65 s vs 3.1 s; letters A 79.4 / B 77.8; tones 20 / 0.
time resample and wrist trajectory variants do not help → keep `frame`.
hauuto licence unknown → internal only; data under `data/external/{alphabet_hands_kaggle,hauuto_raw}` (gitignored).
Permission draft: `docs/provenance/hauuto_permission_request.md` (owner sends it).

## Gotchas
- Git Bash turns `cmd /c` into `cmd C:/` → use `MSYS_NO_PATHCONV=1`.
- Kaggle CLI `kernels output` stops at ~500 files: use `--file-pattern` per folder.
- Pipe output with Vietnamese → set `PYTHONIOENCODING=utf-8` (otherwise tests "fail" with UnicodeEncodeError).
- Tests: `python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput tests.test_fingerspelling_api tests.test_unified_split_integrity` (47 OK).
