# Level 1 Kaggle run — STOPPED at data-integrity check (2026-09-24)

No Kaggle dataset was created and no kernel was pushed (verified with `kaggle datasets list --mine` / `kaggle kernels list --mine`).
No model was trained on GPU and no accuracy is reported.

## Finding: `data/vsl_alphabet_pilot` is fully synthetic

`scripts/record_vsl_alphabet.py::record_single_sample` does not record a camera. For every clip it:

1. Takes a hand-authored 21-point pose per symbol from `get_canonical_hand_pose(symbol)` (hard-coded
   coordinates + a `set_finger(curl_ratio)` helper), multiplied by a per-"signer" `hand_scale`.
2. Adds Gaussian noise: `rep_jitter ~ N(0, 0.002)` per repetition and `micro_tremor ~ N(0, 0.001)` per frame,
   seeded by `hash((signer_id, symbol, repetition, ...))`.
3. Moves that pose along a fixed smoothstep path rest→center→rest (frames 15–30 / hold 30–90 / 90–105).
4. Writes these points directly to `raw_landmarks` in the `.npz` — MediaPipe is never run.
5. Renders a stick-figure hand on a grey background into the `.mp4` (`videos/`, 1.1 GB).

"Signers" S01–S15 are rows of `SIGNER_PROFILES` (gender label, `hand_scale`, skin colour for the drawing).

## Consequences

| Claim in notebook / docs | Reality |
|---|---|
| 15 signers, signer-disjoint split | Signers differ only by `hand_scale`, which palm-scale normalization removes exactly. Train/val/test are the same 25 templates + noise. |
| Tests generalization to unseen signers | Not measurable with this data. Expected test accuracy ≈ 100% and meaningless. |
| MediaPipe landmarks | Synthetic points; real MediaPipe output from a webcam (backend `/api/fingerspelling`) is a different distribution. |
| Dynamic vs static classes | All 25 classes are static by construction; motion stats per class are identical (see `class_motion_train.json`: hold shape deviation 0.0089–0.0094, wrist path ≈0.88 for every class). |

## Prepared and still valid (reusable once real data exists)

- `scripts/generate_alphabet_notebook.py` → `vsl_alphabet_cloud_training.ipynb`: VAL-only selection written to
  `selection.json` before a single TEST pass; seed 42 + deterministic; checkpoint carries config, ordered classes,
  preprocessing params; outputs per-class F1, confusion matrix, per-signer accuracy, epoch logs. Smoke-tested locally.
- `configs/alphabet_level1.yaml`, `scripts/package_alphabet_cloud_data.py` (now packs config + package inits).
- `kaggle/vsl-alphabet-cloud-data/dataset-metadata.json`, `kaggle/vsl-alphabet-level1-training/kernel-metadata.json`
  (private, GPU T4 via `--accelerator NvidiaTeslaT4`, internet off).
- Kaggle CLI 2.2.4 note: `kaggle datasets create -p kaggle/<dir>` fails with a relative multi-segment path
  (resume-cache filename contains `/`) while exiting 0 — run from inside the folder with `-p .`.
