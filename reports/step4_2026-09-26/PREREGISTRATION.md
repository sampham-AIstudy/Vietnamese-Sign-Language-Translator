# Step 4b/4c — decisions fixed before any result (2026-09-26)

Written before the harmonised models are trained; results must not change these rules.

- 4b variants (unified 876 classes, `--features harmonized`, seed 42 only, no seed selection):
  H-keepz (hand z kept), H-dropz (hand z = 0), both on native-resolution QIPEDC keypoints; then the chosen z
  variant on QIPEDC keypoints extracted at 360 px height (`--process-height 360`).
- Choice between variants: balanced VAL top-1 = mean(VAL top-1 on VSL-GH S05, VAL top-1 on the 105 QIPEDC VAL clips),
  from `metrics.json -> val_by_source`. Difference < 0.5 point → the simpler one (drop hand z; native resolution).
  The TEST set is not used for this choice.
- 360 px: adopted only if it wins by the rule above; then the live path must use the same process height
  (RealtimeLandmarkExtractor) with an equivalence test.
- Main results without test-time augmentation.
- 4c: dictionary-word model (`--sources qipedc`) with the chosen harmonisation; compared with the chosen 4b model on
  the SAME QIPEDC TEST clips (rows whose class is in both label spaces): Top-1/5/10, Wilson 95% CI, exact McNemar.
- Cross-source check: QIPEDC TEST clips of the shared classes minus xem, kết quả, yếu, thường xuyên.
- Trimming conclusion: compare the chosen 4b model (trimmed, retrained) with the old unified model on the same groups.
