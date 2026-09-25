# GATE 0 — Level 1 data integrity (vsl-data-integrity, 2026-09-25)

Dataset: hauuto `vietnamese-sign-language-alphabet` (Kaggle) + QIPEDC single-letter dictionary clips.
Result under review: BiGRU LOSO 75.1% (`alphabet_run/alphabet_report.json`).

## Step 0
| Check | Evidence | Status |
|---|---|---|
| 0a Script that wrote the data | `scripts/extract_hands_batch.py::_extract_one`: `cv2.VideoCapture(mp4)` → `mp.solutions.hands.Hands(...).process(frame)` → `np.savez_compressed`. No rng/template/constants. Run on Kaggle `phmvnsm33/vsl-extract-alphabet` (commit 55e3476). Manifest: 686/686 `mediapipe_version=0.10.14`, `extractor=mp.solutions.hands` | PASS |
| 0b External source | https://www.kaggle.com/datasets/hauuto/vietnamese-sign-language-alphabet — created 2026-09-18, **license "unknown"**, no description, no paper | URL OK, **license UNVERIFIED** |
| 0c Content | 4 raw mp4 viewed (one per signer, 3 frames each): 4 different real people, different rooms/webcams, 640×480, variable fps (12–30, webcam-like). Landmark stats differ per signer (hand size 0.205/0.251/0.323/0.265; motion std 0.015–0.048). 0 duplicate landmark arrays | PASS |
| 0d Signer / label metadata | `signer_id` and label come from the source path `raw/raw/<signer>/<telex>_<signer>_<A|B>_<n>.mp4` (`build_alphabet_tasks.py`), not assigned by code. Telex→Vietnamese map fixed (29 letters + 5 tones) | PASS |
| Sign form vs VSL standard | Letters seen (b, đ, ơ) look plausible. Tone-mark handshapes NOT checked against an official reference. Signers look like students recording by webcam; Deaf status unknown | PARTIAL |

## Split / counts
| Signer | Clips | Classes | Reps/class | MediaPipe detection |
|---|---|---|---|---|
| hauuto_hau | 160 | 34 | 4–6 | 0.99 |
| hauuto_khoi | 160 | 34 | 4–6 | 0.92 |
| hauuto_tai | 156 (4 dropped, <3 detected frames) | 34 | 4–6 | 0.95 |
| hauuto_vy | 160 | 34 | 4–6 | 0.99 |
| QIPEDC letters (external) | 46 clips = **40 distinct recordings**, signer IDs unknown | 29 letters, 0 tones | 1–3 | 0.50 |

LOSO: each fold trains on 3 people and tests on 1 (≈160 clips). No validation set, fixed 80 epochs, so no early stopping on test.
BiGRU vs MLP was chosen on the same LOSO test folds (2 candidates, small optimistic bias).

## Results per unseen signer (BiGRU)
| Test signer | Overall | Letters (n≈130) | Tone marks (n=30) |
|---|---|---|---|
| hau | 76.2 | 85.4 | 36.7 |
| khoi | 78.8 | 86.2 | 46.7 |
| tai | 60.9 | 73.8 | 6.7 |
| vy | 84.4 | 92.3 | 50.0 |
| **Mean (95% t-CI, n=4 folds)** | **75.1 [59.1, 91.0]** | **84.4 [72.1, 96.7]** | **35.0 [3.6, 66.4]** |

External QIPEDC letters: 60.9% on 46 clips; **60.0% (24/40), Wilson 95% CI [44.6, 73.7]** after removing duplicate recordings.

## Verdict
Real data (real people, real MediaPipe, signer IDs from the source): **PASS**. The data can be used for training and the backend.
Numbers usable in the report: letters 84.4% [72.1, 96.7] on unseen signers (4 signers); QIPEDC external 60.0% [44.6, 73.7] (40 recordings).
Tone marks are not usable as a result (CI 3.6–66.4). Open item: the dataset license is unknown, so ask the uploader before publishing.
