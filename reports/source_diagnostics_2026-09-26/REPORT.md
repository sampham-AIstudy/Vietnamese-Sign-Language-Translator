# Why the Level 2 model separates video sources — steps 1–3 (2026-09-26)

Model: unified ST-GCN, seed 42 (`reports/unified_run_2026-09-25/run`). Key symptom: 0/31 QIPEDC test clips of words
with hundreds of VSL-GH training samples. Numbers below come from the JSON files in this folder.

## Step 1 — source classifier on the model input (`prelim_hcmue47/source_diagnostics.json`)
Logistic regression on clip summaries of the preprocessed input (aspect-corrected, shoulder-centred, 60 frames +
masks), GroupKFold(5) by recording. n = VSL-GH 1500, QIPEDC 623, HCMUE 47 (full 435 rerun → `final/`).

| Features | 3 sources, balanced acc. (chance 33.3) | VSL-GH vs QIPEDC |
|---|---|---|
| all | 93.9 | **100.0** |
| pose x/y only | 95.3 | **100.0** |
| pose z only | 91.1 | **100.0** |
| clip length only (valid-frame share, 1 number) | 66.2 | **98.2** |
| hand shape only (wrist-centred, size-scaled) | 85.2 | 94.7 |
| hand x/y only | 81.9 | 97.8 |
| hand z only | 77.5 | 90.9 |
| joint presence only | 48.2 | 60.8 |

Leaving any one group out keeps ≥ 88.8% → the source is encoded redundantly, mostly by body geometry and clip length.

## Step 2 — per-source statistics and extraction paths
| | VSL-GH | QIPEDC | HCMUE (47) |
|---|---|---|---|
| Frames per clip (median) | 27 (sign cut from a sentence) | 115 (rest → sign → rest) | 273 |
| Frames with left / right hand | 0.97 / 0.97 | 0.53 / 0.68 | see JSON |
| Frames with no hand | 0.4% | 29.4% | |
| Pose z (median) | −0.51 | −0.40 | |
| Stored dtype | float16 | float32 | float32 |
| Missing stored as NaN | yes | yes | yes |

Anatomical ratios (should not depend on the sign) are close across sources: index finger/palm 1.00 / 0.99 / 0.96,
thumb/palm 1.07 / 1.02 / 1.04, hand depth/palm 0.52 / 0.46 / 0.43, torso/shoulder width 1.38 / 1.48 / 1.46,
eye distance/shoulder width 0.215 / 0.199 / 0.223. → **no gross extraction bug** (no axis swap, scale or joint-map error).
Mirroring checked and rejected: in all sources the left shoulder is on the image right, the left-hand slot sits at
the pose left wrist, and the right hand moves most.

Extraction paths (upstream `clone/Vietnamese-Sign-Language-Translation/source/extract_keypoints.py` vs
`src/data/landmark_extractor.py`): both MediaPipe Holistic, `model_complexity=1`, tracking mode,
`smooth_landmarks=True`, zeros/NaN for missing. Differences:
1. **VSL-GH frames are resized 1080×1080 → 360×360 before MediaPipe**; QIPEDC runs at 1280×720.
2. MediaPipe version of the upstream run is unknown (ours 0.10.14).
3. Mapping 137 → 67 checked index by index against the upstream landmark lists: correct, except two small points —
   mouth corners 9/10 come from FaceMesh 61/291 (possibly left/right swapped vs MediaPipe Pose 9/10), and thumb
   joints 21/22 come from the hand model (VSL-GH) vs the pose model (QIPEDC).
4. VSL-GH segments are float16 (precision ~1e-3).

Trimming the rest at the start/end of QIPEDC/HCMUE clips (`trim_rest_eval_hcmue47.json`, no retraining) does not
fix it: cross-source 0.0 → 4.3% top-1 (1/23), QIPEDC test 11.3 → 3.7%, HCMUE 4.3 → 0.0%; S06 control 67.2 → 67.0%.

## Step 3 — are the words signed the same way?
Side-by-side renders (VSL-GH segment of S01 | QIPEDC test clip | QIPEDC video): `cross_source/<word>.png|.mp4`
(local only, not committed: they contain QIPEDC video frames).
Hands-only DTW nearest neighbour (`cross_source_dtw.json`; no body joints, clip trimmed, 32 frames), pool = VSL-GH
segments of S01–S04 (≈365 words):

| Queries | n | correct word 1st | in top 5 | median rank |
|---|---|---|---|---|
| S06 segments (same source, unseen signer) — reference | 29 | 55.2% | 79.3% | 1 |
| QIPEDC clips of the same words | 23 | 0.0% | 17.4% | 29 |

| Word | DTW rank | Visual | Verdict |
|---|---|---|---|
| bình thường | 2 | right hand raised open palm in both | same form |
| giấy | 4 | two flat hands stacked at the chest in both | same form |
| xem | 332 (nearest VSL-GH words include "nhìn") | QIPEDC one hand from the eyes outward; VSL-GH two hands at chest/shoulders | **different sign** |
| kết quả | 199–202 | QIPEDC left palm up flat + right thumb on top; VSL-GH left hand upright, right hand high | **different sign** |
| yếu | 211 | not rendered | likely different |
| thường xuyên | 222 | not rendered | likely different |
| hồi hộp, không hiểu | 11–14 | — | unclear |
| hỏi, hiểu, mỗi ngày, lâu, điện, hẹn, đợi | 29–61 | same location (face/chin/head), đợi: VSL-GH adds the left hand | unclear / partly different |
| muốn, mới, thông tin, trước, ngồi, thận | — | keypoints not downloaded | not checked |

Candidates to exclude from any cross-source evaluation (different variant): **xem, kết quả, yếu, thường xuyên**.
Caveat: VSL-GH segments are cut from continuous signing (co-articulated, no hold), so a poor rank can also come
from the cut, not only from a different sign.

## Reading
- The model can tell the source from body geometry and clip length alone (100%), and the two vocabularies barely
  overlap (85 of 876 classes), so "which source" is a cheap proxy for "which word" during training.
- Not a single extraction bug: the extractors agree; the sources differ as studios (camera, framing, people,
  360-px processing for VSL-GH), as tasks (sign cut from a sentence vs citation form with rest), and partly as
  vocabularies (some words signed differently).
- Even with hands only and no learned model, QIPEDC clips land near the correct VSL-GH word far less often than S06
  does (median rank 29 vs 1) → part of the gap is real sign/segmentation difference, not only a shortcut.
