# Handoff — after cleanup + Level 1 results (2026-09-25, ~11:35)

Supersedes `2026-09-25-vsl-core-retrain.md` (still valid for background/decisions). Branch `fix/audit-round2` @ `429b289`, pushed.
Reply in Vietnamese. Skills: `vsl-handoff`, `vsl-cloud-jobs`, `vsl-landmark-consistency`, `vsl-data-integrity`, `vsl-evaluation-rigor`.

## State
| Item | Status | Next command |
|---|---|---|
| `phmvnsm33/vsl-extract-qipedc` | RUNNING since ~09:55 (4362 videos) | wait → check log counts |
| `kaggle/vsl-train-unified` | ready | `cd kaggle/vsl-train-unified && ..\..\.venv\Scripts\kaggle kernels push -p . --accelerator NvidiaTeslaT4` |
| `phmvnsm33/vsl-train-alphabet` | COMPLETE | results in `reports/alphabet_real_run_2026-09-25/` |
| Cleanup | DONE (`429b289`) | — |

## Level 1 results (real data, verified)
BiGRU chosen on LOSO (4 hauuto signers, 636 clips, 34 classes):
unseen signer **75.1% ± 8.7** (letters 84.4 ± 6.7, tone marks 35.0 ± 17.1); MLP 68.8 ± 5.6.
External QIPEDC letters (46 clips, other signers/camera): **60.9%** top-1, 76.1% top-3.
Checkpoint `reports/alphabet_real_run_2026-09-25/alphabet_run/alphabet_real_best.pt` (classes + preprocessing inside).
Weak spot: tone marks (6 reps/signer). Integration pending: backend image endpoint is single-frame MLP → needs
a landmark-sequence endpoint for the BiGRU (owner pre-approved; image endpoint → 409; contract + equivalence tests).

## Next steps
1. QIPEDC extraction done → push `vsl-train-unified` (GPU) → poll → `kaggle kernels output ... -p reports/unified_run_<date>`.
2. Report Level 2 by group (`vslgh_class` unseen signer vs `qipedc_only_class` unseen recording).
3. Verify new STGCN ckpt loads via `VSLPredictor(stgcn_ckpt=...)` (label_map + preprocessing.aspect_correct) before swapping backend default.
4. Level 1 sequence endpoint + frontend wiring (skill `vsl-landmark-consistency`).

## Cleanup done (what is gone — don't look for it)
ASL/pilot modules (`src/train_word.py`, `src/train_alphabet.py`, `src/evaluate.py`, `src/export.py`, old classifiers,
`src/evaluation/`, `src/data/alphabet_dataset.py`), pilot notebooks/packagers/collector/`configs/alphabet_level1.yaml`,
legacy split/extract scripts (`create_video_splits`, `check_data_leakage`, `preextract_*`, `dry_run_*`), `scratch/`,
`docs/provenance/archive` (307 MB), `clone/Multi-VSL_WACV_2025`, `data/dry_run_extracted`, `configs/word_config.yaml`.
Root reports now in `docs/audit/`. Kept on purpose: `run_core.py`, `data/vsl_alphabet_pilot` (evidence), `scripts/record_vsl_alphabet.py`,
audit scripts in `reports/audit_*`, `src/training/modal_runner.py`.

## Checks that pass now
`python -m unittest tests.test_alphabet_preprocessing tests.test_aspect_correction tests.test_realtime tests.test_split_guards tests.test_translation_core tests.test_vsl_system tests.test_ws_throughput` (32 OK; no tests/__init__.py → discover fails, list modules explicitly);
`scripts/smoke_test_phase6.py`, `phase10` (first run may exceed 50 ms latency — rerun), `phase12` (487 classes).

## Owner WIP — never stage
`frontend/*` (incl. edited `Reports.jsx`), `requirements.txt`, `tests/test_realtime.py`, `reports/audit_round2/v1_*.json`, `v6_*.json`.
