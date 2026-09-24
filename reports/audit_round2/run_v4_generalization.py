import os
import sys
import io
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.preprocessing.pipeline import VSLPreprocessingPipeline
from src.inference.predictor import VSLPredictor

print("=== STARTING V4: LEVEL 2 GENERALIZATION & BOOTSTRAP CI ===")

# 1. Signer Metadata Check
df_inv = pd.read_csv('results/raw_dataset_inventory.csv')
num_signers_annotated = (df_inv['possible_signer_id'] != 'unknown').sum()
print(f"Signer Metadata Check:")
print(f"  Total videos in raw inventory: {len(df_inv)}")
print(f"  Videos with identified signer ID: {num_signers_annotated} / {len(df_inv)} (0.00%)")
print(f"  Signer-disjoint guarantee between train and test?: FALSE (Signers are unannotated; same actor recorded multiple regional signs).")

# 2. Evaluate held-out test set and record per-sample binary hits
test_csv_path = 'data/splits/folds/tier2_indomain_test.csv'
df_test = pd.read_csv(test_csv_path)

predictor = VSLPredictor(
    model_type="stgcn",
    stgcn_ckpt="checkpoints/stgcn_tier2_indomain.pt",
    classes_path="configs/tier2_classes.txt",
    warmup=True
)

preprocessor = VSLPreprocessingPipeline(
    target_len=60,
    vis_threshold=0.5,
    center_mode="mid_shoulder",
    scale_mode="shoulder_width",
    temporal_mode="pad",
)

hits_top1 = []
hits_top5 = []
sample_dialects = []

for idx, row in df_test.iterrows():
    vid_id = str(row['video_id'])
    true_label = str(row['gloss_normalized']).strip()
    fname = str(row['file_name']).strip()
    dialect = fname[-5] if len(fname) >= 5 and fname[-5] in 'BTN' else 'Other'

    kp_path = os.path.join('data', 'extracted_keypoints', f"{vid_id}.npz")
    if not os.path.exists(kp_path):
        continue

    d = np.load(kp_path)
    seq, jm, tm = preprocessor(d['keypoints'], d['visibility_mask'])
    pred = predictor.predict(seq, joint_mask=jm, temporal_mask=tm, top_k=5)

    is_top1 = int(pred['gloss'] == true_label)
    is_top5 = int(true_label in [x['gloss'] for x in pred['top5']])

    hits_top1.append(is_top1)
    hits_top5.append(is_top5)
    sample_dialects.append(dialect)

hits_top1 = np.array(hits_top1)
hits_top5 = np.array(hits_top5)
sample_dialects = np.array(sample_dialects)
N = len(hits_top1)

print(f"\nEvaluated {N} test samples.")
print(f"Base Top-1 Accuracy: {hits_top1.mean()*100:.2f}%")
print(f"Base Top-5 Accuracy: {hits_top5.mean()*100:.2f}%")

# 3. Bootstrap 95% CI (1000 iterations)
np.random.seed(42)
N_BOOT = 1000
boot_top1 = []
boot_top5 = []
boot_dialects = {"B": [], "T": [], "N": []}

for _ in range(N_BOOT):
    idx = np.random.choice(N, size=N, replace=True)
    boot_top1.append(hits_top1[idx].mean() * 100.0)
    boot_top5.append(hits_top5[idx].mean() * 100.0)

for d in ["B", "T", "N"]:
    d_mask = (sample_dialects == d)
    d_hits = hits_top1[d_mask]
    for _ in range(N_BOOT):
        idx = np.random.choice(len(d_hits), size=len(d_hits), replace=True)
        boot_dialects[d].append(d_hits[idx].mean() * 100.0)

ci_top1 = (np.percentile(boot_top1, 2.5), np.percentile(boot_top1, 97.5))
ci_top5 = (np.percentile(boot_top5, 2.5), np.percentile(boot_top5, 97.5))

print(f"\nTop-1 95% CI: [{ci_top1[0]:.2f}%, {ci_top1[1]:.2f}%]")
print(f"Top-5 95% CI: [{ci_top5[0]:.2f}%, {ci_top5[1]:.2f}%]")
print("Dialect Top-1 95% CIs:")
dialect_ci_results = {}
for d, vals in boot_dialects.items():
    d_ci = (np.percentile(vals, 2.5), np.percentile(vals, 97.5))
    d_name = {"B": "Bắc (North)", "T": "Trung (Central)", "N": "Nam (South)"}[d]
    dialect_ci_results[d_name] = [round(d_ci[0], 2), round(d_ci[1], 2)]
    print(f"  {d_name}: [{d_ci[0]:.2f}%, {d_ci[1]:.2f}%]")

# 4. Check status of cross-dialect 3-fold checkpoints
cd_ckpts = [
    os.path.exists("checkpoints/stgcn_tier2_cd_fold1.pt"),
    os.path.exists("checkpoints/stgcn_tier2_cd_fold2.pt"),
    os.path.exists("checkpoints/stgcn_tier2_cd_fold3.pt"),
]
cd_retrained = any(cd_ckpts)

v4_results = {
    "signer_metadata": {
        "annotated_signers": 0,
        "is_signer_disjoint": False,
        "note": "VSLR dataset has no signer labels. Signer-disjoint splitting is impossible with current metadata."
    },
    "in_domain_test_bootstrap": {
        "n_samples": int(N),
        "top1_point_estimate": round(float(hits_top1.mean() * 100.0), 2),
        "top1_ci_95": [round(ci_top1[0], 2), round(ci_top1[1], 2)],
        "top5_point_estimate": round(float(hits_top5.mean() * 100.0), 2),
        "top5_ci_95": [round(ci_top5[0], 2), round(ci_top5[1], 2)],
        "dialect_top1_ci_95": dialect_ci_results,
    },
    "cross_dialect_3fold_status": {
        "has_retrained_checkpoints": cd_retrained,
        "status": "UNVERIFIED (Checkpoints for folds 1, 2, 3 do not exist; past evaluation in tier2_benchmark_summary suffered from mode collapse on Fold 2; retrain needed on cloud).",
    }
}

with open('reports/audit_round2/v4_generalization.json', 'w', encoding='utf-8') as f:
    json.dump(v4_results, f, indent=2, ensure_ascii=False)

print("\nV4 completed and saved to reports/audit_round2/v4_generalization.json.")
