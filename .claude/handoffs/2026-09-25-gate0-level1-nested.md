# Handoff — GATE 0 follow-ups, Level 1 nested, sequence endpoint (2026-09-25, updated ~17:15)

## NOW (2026-09-26): waiting for owner at GATE Việc 3
Level 2 trained (seed 42 primary, seed 43), report `reports/unified_run_2026-09-25/REPORT.md` (b3f98fd).
Gate: new > old on QIPEDC-fair only as a trend (8.3 vs 4.2, p=0.34), clearly on S06 (50.9 vs 0), NOT on HCMUE (0 vs 0)
→ owner's rule "better on clean test AND HCMUE" is not met; backend default NOT swapped. Checkpoints are in
`reports/unified_run_2026-09-25/run*/stgcn_unified_best.pt` (gitignored? no — untracked; do not commit without asking).
Local data: `data/processed/qipedc_kps` (624/4362, all 96 gate clips), `data/processed/hcmue_kps` (47).
Next after owner decision: Việc 5 needs frontend WIP moved to its own branch first; Việc 6 note: all S06 sentences
are also signed in train → ViT5 end-to-end on S06 measures unseen signer, not unseen sentence (check ViT5 training data).

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
