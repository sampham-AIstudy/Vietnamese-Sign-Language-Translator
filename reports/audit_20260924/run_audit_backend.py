import os
import sys
import io
import json
import glob
import time
import math
import hashlib
import collections
from pathlib import Path

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=== STARTING COMPREHENSIVE VSL AUDIT CHECKS ===")
audit_results = {}

# -------------------------------------------------------------
# 1. SECTION B: DATA INVENTORY
# -------------------------------------------------------------
print("\n--- [AUDIT B] DATA INVENTORY BY TIER ---")

# Level 1
l1_vids = glob.glob('data/vsl_alphabet_pilot/videos/*/*.mp4')
l1_npz = glob.glob('data/vsl_alphabet_pilot/landmarks/*/*.npz')
l1_meta = glob.glob('data/vsl_alphabet_pilot/metadata/*/*.json')
l1_signers = set()
l1_classes = set()
for f in l1_vids:
    parts = Path(f).stem.split('_')
    # Format: VSL_ALPHA_S01_A_REP01
    if len(parts) >= 5:
        l1_signers.add(parts[2])
        l1_classes.add(parts[3])

audit_results["level_1"] = {
    "source": "data/vsl_alphabet_pilot",
    "video_count": len(l1_vids),
    "landmarks_npz_count": len(l1_npz),
    "metadata_json_count": len(l1_meta),
    "num_signers": len(l1_signers),
    "signers": sorted(list(l1_signers)),
    "num_classes": len(l1_classes),
    "classes": sorted(list(l1_classes)),
    "has_trained_checkpoint": os.path.exists("experiments/alphabet_model.pth") or os.path.exists("checkpoints/alphabet_best.pt"),
    "is_real_vsl": True,
    "old_asl_deleted": not os.path.exists("data/asl_alphabet_train"),
}

# Level 2
import pandas as pd
df_label = pd.read_csv('data/Dataset/Labels/label.csv')
l2_vids = glob.glob('data/Dataset/Videos/*.mp4')
hcmue_vids = glob.glob('data/raw_tudienngonngukyhieu/videos/*.mp4')
l2_kps = glob.glob('data/extracted_keypoints/*.npz')

def get_region(fname):
    base = os.path.splitext(str(fname))[0].upper()
    if base.endswith('B'): return 'Bắc (B)'
    if base.endswith('T'): return 'Trung (T)'
    if base.endswith('N'): return 'Nam (N)'
    return 'Other'

df_label['region'] = df_label['VIDEO'].apply(get_region)
region_counts = df_label['region'].value_counts().to_dict()

# Class distribution in Level 2
gloss_counts = df_label['LABEL'].value_counts()
classes_lt_3 = int((gloss_counts < 3).sum())
avg_samples_per_class = float(gloss_counts.mean())

# Check Tier 1 & Tier 2 splits
tier1_classes = [l.strip() for l in open('configs/tier1_classes.txt', encoding='utf-8') if l.strip()]
tier2_classes = [l.strip() for l in open('configs/tier2_classes.txt', encoding='utf-8') if l.strip()]
df_t2_all = pd.read_csv('data/splits/tier2_489_all.csv')
t2_all_classes = df_t2_all['gloss_normalized'].unique().tolist() if 'gloss_normalized' in df_t2_all.columns else df_t2_all['LABEL'].unique().tolist()

audit_results["level_2"] = {
    "total_videos_disk": len(l2_vids),
    "total_labels_csv": len(df_label),
    "hcmue_videos_disk": len(hcmue_vids),
    "extracted_keypoints_disk": len(l2_kps),
    "unique_glosses_raw": int(df_label['LABEL'].nunique()),
    "region_counts": region_counts,
    "classes_with_less_than_3_samples": classes_lt_3,
    "avg_samples_per_class": round(avg_samples_per_class, 2),
    "tier1_classes_count": len(tier1_classes),
    "tier2_classes_config_count": len(tier2_classes),
    "tier2_all_csv_classes_count": len(t2_all_classes),
    "tier2_classes_discrepancy": list(set(t2_all_classes) - set(tier2_classes)),
    "tier2_checkpoint_exists": os.path.exists("checkpoints/stgcn_tier2_indomain.pt"),
}

# Level 3
cslr_kps = glob.glob('data/external/vsl_gh/keypoints_frontal/*.npy')
with open('data/external/vsl_gh/dataset_canonical.json', 'r', encoding='utf-8') as f:
    vsl_gh_canon = json.load(f)

vsl_gh_signers = set()
vsl_gh_sentences = set()
for item in vsl_gh_canon:
    vsl_gh_signers.add(item.get("signer", ""))
    vsl_gh_sentences.add(item.get("sentence_id", item.get("text", "")))

# Parallel text
raw_10k_lines = [json.loads(line) for line in open('data/external/parallel_text/vie_vsl_10k.jsonl', encoding='utf-8') if line.strip()]
clean_10k_lines = [json.loads(line) for line in open('data/external/parallel_text/vie_vsl_10k_cleaned.jsonl', encoding='utf-8') if line.strip()]

audit_results["level_3"] = {
    "cslr_keypoints_count": len(cslr_kps),
    "cslr_canonical_entries": len(vsl_gh_canon),
    "cslr_signers_count": len(vsl_gh_signers),
    "cslr_signers": sorted(list(vsl_gh_signers)),
    "cslr_unique_sentences": len(vsl_gh_sentences),
    "raw_10k_pairs": len(raw_10k_lines),
    "clean_10k_pairs": len(clean_10k_lines),
    "cslr_checkpoint_exists": os.path.exists("checkpoints/cslr_best.pt"),
    "vit5_stage1_exists": os.path.exists("checkpoints/vit5_stage1/best_model/model.safetensors"),
    "vit5_stage2_exists": os.path.exists("checkpoints/vit5_stage2/best_model/model.safetensors"),
}

print(json.dumps(audit_results, indent=2, ensure_ascii=False))

with open('reports/audit_20260924/inventory_summary.json', 'w', encoding='utf-8') as f:
    json.dump(audit_results, f, indent=2, ensure_ascii=False)

print("\nAudit B finished and saved to inventory_summary.json.")
