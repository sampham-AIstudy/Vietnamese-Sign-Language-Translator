# Handoff — GATE 0 follow-ups, Level 1 nested, sequence endpoint (2026-09-25, updated ~17:15)

## DECISION GATE Việc 3 (owner, 2026-09-26): (a) keep the old model as default
Reason: the gate rule (new > old on the clean test AND on HCMUE) was fixed before the results; HCMUE is 0 vs 0,
so relaxing it now because S06 looks good is the mistake we set out to avoid. The key result is 0/31: the model
recognises the video SOURCE, not the sign — a user's webcam is a new source too, so live accuracy will be near the
4–10% seen on QIPEDC/HCMUE for either model.
- Default stays `stgcn` (tier2, 487 classes). New model registered as `VSL_MODEL_TYPE=stgcn_unified`
  (`checkpoints/stgcn_unified_best.pt`, local copy of reports/unified_run_2026-09-25/run) — Việc 6 experiments only.
- Now doing (c): why does the model separate sources. Steps 1–3 then STOP for owner:
  1 source classifier on model-input features (grouped by recording), then per feature group;
  2 per-source statistics + trace VSL-GH 411→67 conversion vs QIPEDC MediaPipe path;
  3 side-by-side landmark videos for 10 of the 0/31 words, list true variant differences.
  After approval: 4 harmonise data + retrain (report 3 groups + 31 cross-source + source classifier), 5 webcam test set.
- Report caveats for 70.6% (Level 2): S06 sentences all seen in train; no generalisation to other sources (0/31).
- Việc 6: check ViT5 training data first; report end-to-end only on sentences ViT5 has not seen.

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
