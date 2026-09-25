import os
import sys
import io
import time
import json
import numpy as np
import pandas as pd
import torch
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=== RUNNING SECTION E: EVALUATION REPRODUCTION ===")

# -------------------------------------------------------------
# 1. LEVEL 2: ST-GCN TIER 2 EVALUATION ON HELD-OUT TEST SET
# -------------------------------------------------------------
print("\n--- [E1] ST-GCN Tier 2 Evaluation ---")
from src.data.preprocessing.pipeline import VSLPreprocessingPipeline
from src.inference.predictor import VSLPredictor

# Test set: data/splits/folds/tier2_indomain_test.csv
test_csv_path = 'data/splits/folds/tier2_indomain_test.csv'
df_test = pd.read_csv(test_csv_path)
print(f"Loaded held-out test set: {len(df_test)} samples from {test_csv_path}")

classes_txt = [line.strip() for line in open('configs/tier2_classes.txt', encoding='utf-8') if line.strip()]
class_to_idx = {c: i for i, c in enumerate(classes_txt)}

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

correct_top1 = 0
correct_top5 = 0
total_evaluated = 0
dialect_stats = {"B": [0, 0, 0], "T": [0, 0, 0], "N": [0, 0, 0]}  # [top1, top5, total]

# Evaluate all test samples
t0 = time.perf_counter()
for idx, row in df_test.iterrows():
    vid_id = str(row['video_id'])
    true_label = str(row['gloss_normalized']).strip()
    fname = str(row['file_name']).strip()
    dialect = fname[-5] if len(fname) >= 5 and fname[-5] in 'BTN' else 'Other'

    kp_path = os.path.join('data', 'extracted_keypoints', f"{vid_id}.npz")
    if not os.path.exists(kp_path):
        continue

    d = np.load(kp_path)
    kps = d['keypoints']
    vis = d['visibility_mask']
    seq, jm, tm = preprocessor(kps, vis)

    pred = predictor.predict(seq, joint_mask=jm, temporal_mask=tm, top_k=5)
    pred_top1 = pred['gloss']
    pred_top5 = [x['gloss'] for x in pred['top5']]

    total_evaluated += 1
    is_top1 = (pred_top1 == true_label)
    is_top5 = (true_label in pred_top5)

    if is_top1:
        correct_top1 += 1
    if is_top5:
        correct_top5 += 1

    if dialect in dialect_stats:
        dialect_stats[dialect][2] += 1
        if is_top1: dialect_stats[dialect][0] += 1
        if is_top5: dialect_stats[dialect][1] += 1

eval_duration = time.perf_counter() - t0

top1_acc = (correct_top1 / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
top5_acc = (correct_top5 / total_evaluated * 100.0) if total_evaluated > 0 else 0.0

print(f"Evaluated {total_evaluated} samples in {eval_duration:.2f}s ({eval_duration/total_evaluated*1000:.1f}ms/sample)")
print(f"  Overall Top-1 Accuracy: {top1_acc:.2f}% (Reported in tier2_benchmark_summary: 46.41%)")
print(f"  Overall Top-5 Accuracy: {top5_acc:.2f}% (Reported in tier2_benchmark_summary: 60.78%)")
print("  By Dialect:")
for d, (c1, c5, tot) in dialect_stats.items():
    d_name = {"B": "Bắc (North)", "T": "Trung (Central)", "N": "Nam (South)"}.get(d, d)
    print(f"    {d_name}: Top-1 = {c1}/{tot} ({c1/tot*100:.2f}%), Top-5 = {c5}/{tot} ({c5/tot*100:.2f}%)")

results_e = {
    "level_2_rerun": {
        "test_csv": test_csv_path,
        "total_evaluated": total_evaluated,
        "top1_acc": round(top1_acc, 2),
        "top5_acc": round(top5_acc, 2),
        "reported_top1": 46.41,
        "reported_top5": 60.78,
        "diff_top1": round(top1_acc - 46.41, 2),
        "diff_top5": round(top5_acc - 60.78, 2),
        "dialect_breakdown": {
            d: {
                "top1": round(c1/tot*100, 2),
                "top5": round(c5/tot*100, 2),
                "count": tot
            } for d, (c1, c5, tot) in dialect_stats.items()
        }
    }
}

with open('reports/audit_20260924/eval_reproduction.json', 'w', encoding='utf-8') as f:
    json.dump(results_e, f, indent=2, ensure_ascii=False)

print("\nSection E evaluation saved to eval_reproduction.json.")
