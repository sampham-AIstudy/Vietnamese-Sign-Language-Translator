# Handoff — GATE 0 follow-ups, Level 1 nested, sequence endpoint (2026-09-25, updated ~17:15)

## NOW (2026-09-26 11:00): step 4a–4c in progress — brief: docs/prompts/buoc4_5.md (replaces all earlier)
Rules fixed in advance: reports/step4_2026-09-26/PREREGISTRATION.md. STOP after 4c and send owner the REPORT file.
- 4a DONE (c8a7bdf): shared 85 classes, balanced 106/106 → source classifier 99.5% (shortcut real); current model
  cross-source 0/26 (seed 43 of the same legacy model gets 3/26 → metric is noisy).
- 4b: harmonised input `src/data/harmonized.py`; classifier on harmonised features 92.0/94.3% (length, pose z → 50%).
  Kaggle `vsl-train-harmonized` v1 RUNNING (GPU0 run_keepz, GPU1 run_dropz). 360 px shards
  `vsl-extract-qipedc360-s{0,1,2}` RUNNING (CPU).
  Next: download outputs to reports/step4_2026-09-26/runs/, run `scripts/report_step4.py`, pick z variant by the
  pre-registered VAL rule, then kernel v2: GPU0 chosen-z @360 (add the 3 shard kernels to kernel_sources, kps=360),
  GPU1 `--sources qipedc` (4c) chosen-z native. If 360 wins on VAL → v3 dictionary model @360.
  Also rerun `shortcut_85.py --features harmonized --qipedc-kps-dir qipedc_kps360` (download 360 output first).
- Local data: data/processed/qipedc_kps = all 4362 (tar from `vsl-pack-qipedc`), old subset kept as qipedc_kps_partial623.
- No `vslt-reviewer` subagent installed → say so in the report.

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
- (c) steps 1–3 DONE (26322dc, `reports/source_diagnostics_2026-09-26/REPORT.md`): source = body geometry + clip length
  (100%), no gross extraction bug, VSL-GH ran MediaPipe at 360x360, xem/kết quả/yếu/thường xuyên signed differently.
  WAITING for owner approval of steps 4–5. Rerun with all 435 HCMUE → `.../final/` (background; commit when done).
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
