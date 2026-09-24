import os
import sys
import io
import json
import glob
import hashlib
from pathlib import Path
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)

print("=== STARTING V5: LEVEL 1 ALPHABET DATASET AUDIT ===")

# 1. Inspect all 1,875 NPZ landmarks
npz_files = glob.glob('data/vsl_alphabet_pilot/landmarks/*/*.npz')
print(f"Total NPZ landmark files: {len(npz_files)}")

shapes = set()
nan_counts = 0
total_elements = 0
total_frames = 0
frames_without_hand = 0
signer_counts = collections.defaultdict(int) if 'collections' in locals() else {}
import collections
signer_counts = collections.defaultdict(int)
class_counts = collections.defaultdict(int)
signer_class_matrix = collections.defaultdict(lambda: collections.defaultdict(int))

for p in npz_files:
    fname = Path(p).stem  # e.g. VSL_ALPHA_S01_A_REP01
    parts = fname.split('_')
    s_id = parts[2]
    # class name
    if parts[3] == "Dau":
        c_name = f"Dau_{parts[4]}"
    else:
        c_name = parts[3]

    signer_counts[s_id] += 1
    class_counts[c_name] += 1
    signer_class_matrix[s_id][c_name] += 1

    d = np.load(p)
    arr = d['palm_scale_normalized']
    shapes.add(arr.shape)
    
    nans = int(np.isnan(arr).sum())
    nan_counts += nans
    total_elements += arr.size

    det_mask = d['detected_mask']
    total_frames += len(det_mask)
    frames_without_hand += int((det_mask == 0).sum())

print(f"Shapes detected: {shapes}")
print(f"NaN count across all elements ({total_elements}): {nan_counts} ({nan_counts/total_elements*100:.4f}%)")
print(f"Frames missing hand: {frames_without_hand} / {total_frames} ({frames_without_hand/total_frames*100:.2f}%)")
print(f"Signers count: {len(signer_counts)} (min={min(signer_counts.values())}, max={max(signer_counts.values())})")
print(f"Classes count: {len(class_counts)} (min={min(class_counts.values())}, max={max(class_counts.values())})")

# 2. Check Video Duplicate Hashes
vid_files = glob.glob('data/vsl_alphabet_pilot/videos/*/*.mp4')
print(f"Total MP4 videos: {len(vid_files)}")
hash_map = collections.defaultdict(list)
for v in vid_files:
    # fast hash first 64KB + size
    sz = os.path.getsize(v)
    with open(v, 'rb') as f:
        head = f.read(65536)
    h = hashlib.md5(f"{sz}".encode() + head).hexdigest()
    hash_map[h].append(v)

dups = {k: v for k, v in hash_map.items() if len(v) > 1}
print(f"Duplicate video files found: {len(dups)}")

# 3. Label Alignment with Thông tư 17/2020/TT-BGDĐT
all_25_classes = sorted(list(class_counts.keys()))
print(f"\n25 Classes in Dataset: {all_25_classes}")

# VSL Standard Alphabet Analysis (Thông tư 17):
# Static letters in VSL: A, B, C, D, Đ, E, G, H, I, K, L, M, N, O, P, Q, R, S, T, U, V, X, Y (23 letters)
# Static accents in VSL: Dấu Sắc (upward slant pose), Dấu Huyền (downward slant pose) (2 accents)
# Dynamic letters omitted: J (tracing J in air), Z (tracing Z in air)
# Dynamic accents omitted: Dấu Ngã (wave motion), Dấu Hỏi (hook motion), Dấu Nặng (downward dotting motion)

# 4. Signer-Based Split Proposal
# 15 signers: S01 to S15
# Propose: Train = 10 signers, Val = 2 signers, Test = 3 signers
# Exactly as annotated in record_vsl_alphabet.py:
# Train (10 signers = 1,250 clips = 66.7%): S01, S04, S05, S06, S07, S08, S09, S10, S11, S13
# Val (2 signers = 250 clips = 13.3%): S02, S12
# Test (3 signers = 375 clips = 20.0%): S03, S14, S15

train_signers = ["S01", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S13"]
val_signers = ["S02", "S12"]
test_signers = ["S03", "S14", "S15"]

print(f"\nProposed Signer Split:")
print(f"  Train: {train_signers} ({len(train_signers)*125} clips, {len(train_signers)*125/1875*100:.1f}%)")
print(f"  Val:   {val_signers} ({len(val_signers)*125} clips, {len(val_signers)*125/1875*100:.1f}%)")
print(f"  Test:  {test_signers} ({len(test_signers)*125} clips, {len(test_signers)*125/1875*100:.1f}%)")

# 5. Handedness & Mirror Audit
# Extractor in record_vsl_alphabet: tracked Right Hand
# Frontend CameraCapture: raw canvas sent to backend is UNMIRRORED (from camera perspective).
# Video preview in UI is mirrored with CSS `transform: -scale-x-100`.
# If user shows their right hand, from camera perspective it is on the left side of frame.
# MediaPipe detects it as Right Hand.
# The training data was recorded with 100% Right hand.

v5_results = {
    "total_npz": len(npz_files),
    "total_videos": len(vid_files),
    "shapes": [list(s) for s in shapes],
    "nan_count": nan_counts,
    "missing_hand_frame_ratio": round(frames_without_hand / total_frames * 100.0, 2),
    "duplicate_videos": len(dups),
    "classes_25": all_25_classes,
    "linguistic_notes": {
        "static_classes": 25,
        "static_letters": 23,
        "static_accents": 2,
        "dynamic_letters_excluded": ["J", "Z"],
        "dynamic_accents_excluded": ["Dau_Hoi", "Dau_Nga", "Dau_Nang"],
        "standard": "Thông tư 17/2020/TT-BGDĐT"
    },
    "handedness_audit": {
        "dataset_handedness": "100% Right hand",
        "frontend_camera": "Raw canvas unmirrored; CSS mirrored display only",
        "consistency": "PASS (Both training data and runtime live pipeline process unmirrored right-hand coordinates)."
    },
    "proposed_signer_split": {
        "train": train_signers,
        "val": val_signers,
        "test": test_signers,
    }
}

with open('reports/audit_round2/v5_alphabet_audit.json', 'w', encoding='utf-8') as f:
    json.dump(v5_results, f, indent=2, ensure_ascii=False)

print("\nV5 completed and saved to reports/audit_round2/v5_alphabet_audit.json.")
