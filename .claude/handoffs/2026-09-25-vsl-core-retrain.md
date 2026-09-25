# Handoff — VSL core retrain on real data (2026-09-25)

Branch `fix/audit-round2` (pushed to origin; never touch `main`). Owner: SamPhamVjp. Reply in Vietnamese.

## Goal (owner's words, condensed)
Nationwide VSL translator from webcam: recognise the sign the user makes **exactly** (letters → words → sentences).
Dialect-agnostic (merge Bắc/Trung/Nam variants). Prefer existing public data over self-recording.
Heavy work on cloud (Kaggle/Colab), never lag the local PC. Install only inside `.venv`.

## State at handoff
| Item | Status |
|---|---|
| Kaggle kernel `phmvnsm33/vsl-extract-qipedc` | RUNNING (CPU, 4362 QIPEDC videos → `qipedc_kps/*.npz`, ~1.5–2 h from ~09:55) |
| Kaggle kernel `phmvnsm33/vsl-extract-alphabet` | RUNNING (Hands on 640 hauuto + 46 QIPEDC letter clips → `alphabet_hands/`) |
| `kaggle/vsl-train-unified/` | ready, push after qipedc extraction: `cd kaggle/vsl-train-unified && kaggle kernels push -p . --accelerator NvidiaTeslaT4` |
| `kaggle/vsl-train-alphabet/` | ready (CPU), push after alphabet extraction: `cd kaggle/vsl-train-alphabet && kaggle kernels push -p .` |
| Colab MCP | works: call `open_colab_browser_connection` first; runtime must be T4 (owner switches it) |
| VSL400 (Zenodo, 26 signers, 400 words) | owner emailed for access, not approved yet — biggest future accuracy gain |

## Next steps (in order)
1. When extraction kernels finish: `kaggle kernels output phmvnsm33/<kernel> -p <tmp>` is NOT needed for training (train kernels take `kernel_sources`). Just check logs: counts ≈ 4362 / 686 npz, few errors, detection rates.
2. Push both train kernels; poll `kaggle kernels status`; then `kaggle kernels output ... -p reports/<run_dir>`.
3. Report Level 2 split by group: `vslgh_class` (unseen signer S06) vs `qipedc_only_class` (unseen recording, 1–2 train samples → expect low). Level 1: LOSO mean (letters vs tones) + external QIPEDC letters.
4. Before swapping backend models: load new ckpt with `VSLPredictor(stgcn_ckpt=...)` — it reads `label_map` + `preprocessing.aspect_correct` from the checkpoint; RealtimePipeline follows it. Level 1 new model is BiGRU/sequence (34 classes) → backend needs a sequence endpoint (owner pre-approved: new landmark-sequence endpoint, image endpoint returns 409, contract + equivalence tests).
5. Optional: add HCMUE (435 videos, `data/raw_tudienngonngukyhieu`, not on cloud) as extra QIPEDC-like units.

## Key numbers (verified)
- Legacy Tier 2 "46.41%" was leakage: 54% test clips had the same recording in train; clean Top-1 = **8.07%** (`reports/audit_round3/`).
- QIPEDC: 4362 videos = 3946 distinct recordings; 101 glosses with ≥3 recordings.
- Unified manifest (`data/splits/unified/`): **876 measurable classes** (510 QIPEDC-only with 1–2 train samples; 366 with VSL-GH 12–70+), train/val/test 15138/1295/1911.
- Label inventory (`data/splits/label_inventory*.{csv,json}`): 3861 labels, 986 with ≥2 independent units.

## Commits this session (newest first)
4d0600b alphabet features+LOSO · 22211f0 alphabet extraction · c6df431 unified manifest+train script ·
6c28da9 batch extraction + VSL-GH segments · 6f50af1 commit untracked src/ · 84cc277 aspect hook + inventory ·
d3e32a1 source vetting · 98c2e8b grouped splits + DuplicateRecordingLeakageError · 68c0f0a provenance ·
3316503 collector + skill · f080ef4 retract alphabet claims · 0b7a43a synthetic guard · 5e309de alphabet pipeline

## Decisions already made (don't re-ask)
- Data: pilot alphabet is synthetic (guarded); VOYA_VSL + v2 `online_sourced` rejected (QIPEDC repack / byte-dup files); Multi-VSL full set not public.
- Level 1 source = Kaggle `hauuto/vietnamese-sign-language-alphabet` (4 signers, license Unknown → cite, ask author).
- GPU: Kaggle T4 for batch (background), Colab T4 for interactive; TPU not used; HF dropped (5 min/day).
- Owner allowed: pushing `fix/audit-round2`, committing `src/`. Not allowed without asking: pushing `main`, public datasets, installs outside `.venv`.

## Open caveats
- `frontend/src/components/Reports.jsx` edited (numbers corrected) but NOT committed — owner has other uncommitted edits there.
- Owner's uncommitted edits elsewhere (e.g. `reports/audit_round2/v1_*.json`, frontend files) — never stage them.
- GitNexus index goes stale after each commit: run `node .gitnexus/run.cjs analyze --index-only` before `detect-changes`.

Skills to load: `vsl-cloud-jobs`, `vsl-landmark-consistency`, `vsl-data-integrity`, `vsl-evaluation-rigor`.
