# ⚠ SYNTHETIC DATA — DO NOT USE FOR TRAINING OR EVALUATION

Everything in this directory (`landmarks/`, `videos/`, `metadata/`, `manifest.json`, `splits/`) was **generated**
by `scripts/record_vsl_alphabet.py`, not recorded from people:

- Landmarks = hard-coded pose per symbol (`get_canonical_hand_pose`) × per-"signer" `hand_scale`
  + Gaussian noise (σ 0.002 / 0.001). MediaPipe was never run.
- Videos = stick-figure hands rendered on a grey background.
- "Signers" S01–S15 = rows of `SIGNER_PROFILES`; they differ only by `hand_scale`, which the
  palm-scale normalization removes. Any "signer-disjoint" accuracy on this data is meaningless (~100%).
- "Thông tư 17 standard" / "15 signers" claims made about this data are false.

Kept (not deleted) only as evidence for the audit trail:
`reports/alphabet_run_2026-09-24/DATA_INTEGRITY_STOP.md`.

This file is also a **guard**: `vsl_alphabet_cloud_training.ipynb` and
`scripts/package_alphabet_cloud_data.py` refuse to run on any data directory that contains it.
Real Level 1 data goes to `data/vsl_alphabet_real/` via `scripts/collect_alphabet_real.py`.
