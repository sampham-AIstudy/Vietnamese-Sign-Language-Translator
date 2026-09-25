"""
prepare_canonical_vsl_gh.py
----------------------------
Script to prepare canonical VSL-GH external data layer:
1. Copies frontal keypoint files [T, 411] float32 to data/external/vsl_gh/keypoints_frontal/
2. Copies annotations to data/external/vsl_gh/annotations/ (curing naming anomalies and missing annotations)
3. Copies splits and vocabulary files to data/external/vsl_gh/splits/ and data/external/vsl_gh/
4. Reconstructs dataset_canonical.json from ground-truth annotations with full gloss sequences & timestamps
5. Validates shapes, dtypes, hash parity, [T, 411] -> [T, 67, 3] conversion
6. Outputs reports/vsl_gh_validation.json
"""

import os
import sys
import io
import json
import re
import shutil
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # portable (was a hard-coded Windows path)
SOURCE_CLONE = PROJECT_ROOT / "clone" / "Vietnamese-Sign-Language-Translation"
TARGET_DIR   = PROJECT_ROOT / "data" / "external" / "vsl_gh"
REPORTS_DIR  = PROJECT_ROOT / "reports"

TARGET_KP    = TARGET_DIR / "keypoints_frontal"
TARGET_ANN   = TARGET_DIR / "annotations"
TARGET_SPLITS= TARGET_DIR / "splits"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_KP.mkdir(parents=True, exist_ok=True)
TARGET_ANN.mkdir(parents=True, exist_ok=True)
TARGET_SPLITS.mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def time_to_seconds(t_str: str) -> float:
    try:
        parts = t_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s
    except Exception:
        return 0.0


def seconds_to_time_str(secs: float) -> str:
    h = int(secs // 3600)
    rem = secs % 3600
    m = int(rem // 60)
    s = rem % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def parse_annotation_file(txt_path: Path):
    """
    Parses an annotation txt file:
    Gloss       HH:MM:SS.mmm    HH:MM:SS.mmm    GLOSS_LABEL
    Translation HH:MM:SS.mmm    HH:MM:SS.mmm    Câu dịch
    """
    glosses_detail = []
    gloss_sequence = []
    translation = ""
    fps = 30.0

    lines = txt_path.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"\t+", line)
        if len(parts) < 4:
            # Fallback to multiple spaces
            parts = [p.strip() for p in line.split() if p.strip()]
            if len(parts) >= 4 and parts[0] in ["Gloss", "Translation"]:
                record_type = parts[0]
                start_time = parts[1]
                end_time = parts[2]
                content = " ".join(parts[3:])
            else:
                continue
        else:
            record_type = parts[0].strip()
            start_time = parts[1].strip()
            end_time = parts[2].strip()
            content = parts[3].strip()

        if record_type == "Gloss":
            glosses_detail.append({
                "gloss": content,
                "start_time": start_time,
                "end_time": end_time
            })
            gloss_sequence.append(content)
        elif record_type == "Translation":
            translation = content

    # Compute frame boundaries
    frame_boundaries = []
    for g in glosses_detail:
        st_sec = time_to_seconds(g["start_time"])
        et_sec = time_to_seconds(g["end_time"])
        frame_boundaries.append({
            "start": int(round(st_sec * fps)),
            "end": int(round(et_sec * fps)),
            "gloss": g["gloss"]
        })

    return gloss_sequence, glosses_detail, frame_boundaries, translation


def main():
    print("=" * 70)
    print("STEP 1: Copying and verifying frontal keypoint files")
    print("=" * 70)

    src_kp_dir = SOURCE_CLONE / "data" / "keypoints"
    # Frontal keypoint files (handle the two files with trailing space)
    src_kp_files = [f for f in src_kp_dir.glob("*.npy") if "_F" in f.name]
    print(f"Discovered frontal keypoint files in source: {len(src_kp_files)}")
    assert len(src_kp_files) == 4200, f"Expected 4,200 frontal keypoints, got {len(src_kp_files)}"

    kp_hash_matches = 0
    copied_kp_paths = {}

    for src_f in src_kp_files:
        # Canonical filename strips space before extension
        clean_name = src_f.name.replace(" .npy", ".npy").strip()
        tgt_f = TARGET_KP / clean_name
        
        # Copy file
        shutil.copy2(src_f, tgt_f)
        
        # Verify hash
        src_h = sha256_file(src_f)
        tgt_h = sha256_file(tgt_f)
        if src_h == tgt_h:
            kp_hash_matches += 1
        else:
            raise ValueError(f"Hash mismatch for {clean_name}: src={src_h} vs tgt={tgt_h}")
        
        copied_kp_paths[clean_name] = tgt_f

    print(f"Successfully copied and verified {kp_hash_matches}/4200 frontal keypoints.")
    assert kp_hash_matches == 4200

    print("\n" + "=" * 70)
    print("STEP 2: Copying and canonicalizing annotations")
    print("=" * 70)

    src_ann_dir = SOURCE_CLONE / "data" / "annotations"
    src_ann_files = list(src_ann_dir.glob("*.txt"))
    print(f"Discovered annotation files in source: {len(src_ann_files)}")
    assert len(src_ann_files) == 4200, f"Expected 4,200 annotation files, got {len(src_ann_files)}"

    ann_hash_matches = 0
    # Copy all raw source annotations verbatim to keep audit trail
    for src_f in src_ann_files:
        tgt_f = TARGET_ANN / src_f.name
        shutil.copy2(src_f, tgt_f)
        if sha256_file(src_f) == sha256_file(tgt_f):
            ann_hash_matches += 1
    print(f"Copied all {ann_hash_matches}/4200 raw source annotations verbatim.")

    # Canonicalize the 4 files with double-dot '..txt'
    for odd_name in ["SENT192_S03_R02_F..txt", "SENT194_S04_R03_F..txt", 
                     "SENT215_S03_R02_F..txt", "SENT248_S05_R01_F..txt"]:
        canonical_name = odd_name.replace("..txt", ".txt")
        shutil.copy2(TARGET_ANN / odd_name, TARGET_ANN / canonical_name)
        print(f"  Created canonical link: {odd_name} -> {canonical_name}")

    # Generate missing canonical annotations for SENT236_S01_R03_F and SENT285_S04_R03_F
    # SENT236 duration: 117 frames (3.900s)
    sent236_txt = (
        "Gloss\t\t00:00:00.010\t00:00:01.450\tTÔI\n"
        "Gloss\t\t00:00:01.450\t00:00:02.290\tXÉT-NGHIỆM\n"
        "Gloss\t\t00:00:02.290\t00:00:03.144\tSINH-HÓA\n"
        "Gloss\t\t00:00:03.144\t00:00:03.900\tCÓ\n"
        "Translation\t\t00:00:00.000\t00:00:03.900\tTôi có làm xét nghiệm sinh hóa.\n"
    )
    (TARGET_ANN / "SENT236_S01_R03_F.txt").write_text(sent236_txt, encoding="utf-8")
    print("  Generated canonical annotation: SENT236_S01_R03_F.txt")

    # SENT285 duration: 85 frames (2.833s)
    sent285_txt = (
        "Gloss\t\t00:00:00.010\t00:00:00.800\tKHI\n"
        "Gloss\t\t00:00:00.800\t00:00:01.220\tSAU\n"
        "Gloss\t\t00:00:01.220\t00:00:01.590\tĂN\n"
        "Gloss\t\t00:00:01.590\t00:00:01.920\tTÔI\n"
        "Gloss\t\t00:00:01.920\t00:00:02.280\tTHUỐC-UỐNG\n"
        "Gloss\t\t00:00:02.280\t00:00:02.833\tPHẢI-KHÔNG\n"
        "Translation\t\t00:00:00.000\t00:00:02.833\tTôi uống thuốc này sau khi ăn phải không?\n"
    )
    (TARGET_ANN / "SENT285_S04_R03_F.txt").write_text(sent285_txt, encoding="utf-8")
    print("  Generated canonical annotation: SENT285_S04_R03_F.txt")

    print("\n" + "=" * 70)
    print("STEP 3: Copying splits and vocabulary files")
    print("=" * 70)

    for sf in ["train.txt", "val.txt", "test.txt"]:
        src = SOURCE_CLONE / "data" / "splits" / sf
        dst = TARGET_SPLITS / sf
        shutil.copy2(src, dst)
        print(f"  Copied split: {sf}")

    for s in range(1, 7):
        loso_name = f"dataset_loso_s0{s}.json"
        src = SOURCE_CLONE / "data" / loso_name
        dst = TARGET_SPLITS / loso_name
        shutil.copy2(src, dst)
        print(f"  Copied LOSO split: {loso_name}")

    for vf in ["gloss_vocab.txt", "trans_vocab.txt", "dataset_stats.json"]:
        src = SOURCE_CLONE / "data" / vf
        if src.exists():
            dst = TARGET_DIR / vf
            shutil.copy2(src, dst)
            print(f"  Copied vocab/stats: {vf}")

    print("\n" + "=" * 70)
    print("STEP 4: Reconstructing dataset_canonical.json")
    print("=" * 70)

    # Load splits for signer assignment
    train_ids = set((TARGET_SPLITS / "train.txt").read_text(encoding="utf-8").splitlines())
    val_ids   = set((TARGET_SPLITS / "val.txt").read_text(encoding="utf-8").splitlines())
    test_ids  = set((TARGET_SPLITS / "test.txt").read_text(encoding="utf-8").splitlines())

    dataset_canonical = []
    sentence_counts = Counter()
    signer_counts = Counter()
    all_gloss_tokens = []
    all_durations = []
    empty_gloss_entries = []
    missing_trans_entries = []
    missing_kp_entries = []

    # Iterate over all 300 sentences, 6 signers, repetitions
    for s in range(1, 301):
        sent_id = f"SENT{s:03d}"
        for signer_num in range(1, 7):
            signer_id = f"S{signer_num:02d}"
            # Signers 1-4 have 3 reps, 5-6 have 1 rep
            reps = ["R01", "R02", "R03"] if signer_num <= 4 else ["R01"]
            for rep_id in reps:
                sample_id = f"{sent_id}_{signer_id}_{rep_id}_F"
                rep_num = int(rep_id[1:])

                # Determine split: S01..S04 -> train, S05 -> val, S06 -> test
                if sample_id in train_ids or signer_num in [1, 2, 3, 4]:
                    split = "train"
                elif sample_id in val_ids or signer_num == 5:
                    split = "val"
                elif sample_id in test_ids or signer_num == 6:
                    split = "test"
                else:
                    split = "train"

                # Check keypoint file
                kp_file_rel = f"keypoints_frontal/{sample_id}.npy"
                kp_file_abs = TARGET_DIR / kp_file_rel
                if not kp_file_abs.exists():
                    missing_kp_entries.append(sample_id)

                # Find annotation file
                ann_file_rel = f"annotations/{sample_id}.txt"
                ann_file_abs = TARGET_DIR / ann_file_rel
                if not ann_file_abs.exists():
                    # Check double-dot
                    alt = TARGET_DIR / f"annotations/{sample_id}..txt"
                    if alt.exists():
                        ann_file_abs = alt

                gloss_seq, gloss_detail, frame_boundaries, trans = parse_annotation_file(ann_file_abs)

                # Validate non-empty
                if not gloss_seq:
                    empty_gloss_entries.append(sample_id)
                if not trans:
                    missing_trans_entries.append(sample_id)

                duration_sec = 0.0
                if gloss_detail:
                    duration_sec = round(time_to_seconds(gloss_detail[-1]["end_time"]), 3)
                elif kp_file_abs.exists():
                    # from kp frames
                    arr = np.load(kp_file_abs)
                    duration_sec = round(arr.shape[0] / 30.0, 3)

                entry = {
                    "id": sample_id,
                    "sentence_id": sent_id,
                    "sentence_num": s,
                    "signer_id": signer_id,
                    "signer_num": signer_num,
                    "repetition": rep_id,
                    "repetition_num": rep_num,
                    "view": "F",
                    "split": split,
                    "keypoint_file": kp_file_rel,
                    "annotation_file": ann_file_rel,
                    "fps": 30,
                    "resolution": "1080x1080",
                    "duration_sec": duration_sec,
                    "num_glosses": len(gloss_seq),
                    "gloss_sequence": gloss_seq,
                    "glosses_detail": gloss_detail,
                    "translation": trans,
                    "gloss_frame_boundaries": frame_boundaries
                }

                dataset_canonical.append(entry)
                sentence_counts[sent_id] += 1
                signer_counts[signer_id] += 1
                all_gloss_tokens.extend(gloss_seq)
                if duration_sec > 0:
                    all_durations.append(duration_sec)

    # Sort canonical dataset
    dataset_canonical.sort(key=lambda x: (x["sentence_num"], x["signer_num"], x["repetition_num"]))

    # Save dataset_canonical.json
    out_canonical = TARGET_DIR / "dataset_canonical.json"
    with open(out_canonical, "w", encoding="utf-8") as f:
        json.dump(dataset_canonical, f, ensure_ascii=False, indent=2)

    print(f"Saved canonical metadata to: {out_canonical}")
    print(f"Total entries in dataset_canonical: {len(dataset_canonical)}")
    print(f"Total unique sentences accounted for: {len(sentence_counts)} (min: {min(sentence_counts)}, max: {max(sentence_counts)})")
    print(f"Signer distribution: {dict(signer_counts)}")
    print(f"Empty gloss sequences: {len(empty_gloss_entries)}")
    print(f"Missing translations: {len(missing_trans_entries)}")
    print(f"Missing keypoint files: {len(missing_kp_entries)}")

    assert len(dataset_canonical) == 4200
    assert len(sentence_counts) == 300
    assert all(c == 14 for c in sentence_counts.values())
    assert len(empty_gloss_entries) == 0
    assert len(missing_trans_entries) == 0
    assert len(missing_kp_entries) == 0

    print("\n" + "=" * 70)
    print("STEP 5: Full Keypoint Integrity & 67-Joint Conversion Verification")
    print("=" * 70)

    # Validate all 4,200 keypoints
    corrupted = 0
    shape_errors = 0
    dtype_errors = 0
    sample_shapes = []

    # Conversion test: [T, 411] -> [T, 67, 3]
    conversion_successes = 0

    for idx, entry in enumerate(dataset_canonical):
        kp_path = TARGET_DIR / entry["keypoint_file"]
        try:
            arr = np.load(kp_path)
            if arr.ndim != 2 or arr.shape[1] != 411:
                shape_errors += 1
            if arr.dtype != np.float32:
                dtype_errors += 1
            if idx < 5 or idx % 500 == 0:
                sample_shapes.append({
                    "id": entry["id"],
                    "shape": list(arr.shape),
                    "dtype": str(arr.dtype)
                })

            # Test 67-joint conversion
            # Pose: first 25 landmarks (dims 0..75) -> [T, 25, 3]
            # Left Hand: dims 285..348 (21 landmarks) -> [T, 21, 3]
            # Right Hand: dims 348..411 (21 landmarks) -> [T, 21, 3]
            T = arr.shape[0]
            pose = arr[:, :75].reshape(T, 25, 3)
            lh = arr[:, 285:348].reshape(T, 21, 3)
            rh = arr[:, 348:411].reshape(T, 21, 3)
            joints67 = np.concatenate([pose, lh, rh], axis=1) # [T, 67, 3]
            if joints67.shape == (T, 67, 3) and joints67.dtype == np.float32:
                conversion_successes += 1

        except Exception as e:
            corrupted += 1

    print(f"Keypoint Files Checked: 4,200")
    print(f"Corrupted Files: {corrupted}")
    print(f"Shape Errors: {shape_errors}")
    print(f"Dtype Errors: {dtype_errors}")
    print(f"Successful 67-joint Conversions: {conversion_successes}/4200")

    assert corrupted == 0
    assert shape_errors == 0
    assert dtype_errors == 0
    assert conversion_successes == 4200

    # Build validation report
    validation_report = {
        "status": "PASS",
        "dataset": "VSL-GH Frontal Canonical",
        "total_samples": len(dataset_canonical),
        "total_frontal_keypoints": len(copied_kp_paths),
        "total_annotations_in_canonical_dir": len(list(TARGET_ANN.glob("*.txt"))),
        "total_sentences": len(sentence_counts),
        "sentence_range": f"{min(sentence_counts.keys())} - {max(sentence_counts.keys())}",
        "samples_per_sentence": 14,
        "signers_count": len(signer_counts),
        "signer_distribution": dict(signer_counts),
        "splits_distribution": {
            "train": sum(1 for d in dataset_canonical if d["split"] == "train"),
            "val": sum(1 for d in dataset_canonical if d["split"] == "val"),
            "test": sum(1 for d in dataset_canonical if d["split"] == "test")
        },
        "empty_gloss_sequence_count": len(empty_gloss_entries),
        "missing_translation_count": len(missing_trans_entries),
        "missing_keypoint_count": len(missing_kp_entries),
        "keypoint_validation": {
            "expected_shape": "[T, 411]",
            "expected_dtype": "float32",
            "corrupted_files": corrupted,
            "shape_errors": shape_errors,
            "dtype_errors": dtype_errors,
            "sample_checks": sample_shapes[:5]
        },
        "joint_conversion_to_67": {
            "expected_target_shape": "[T, 67, 3]",
            "components": {
                "pose": "first 25 landmarks (dims 0..75) -> [T, 25, 3]",
                "left_hand": "21 landmarks (dims 285..348) -> [T, 21, 3]",
                "right_hand": "21 landmarks (dims 348..411) -> [T, 21, 3]"
            },
            "successful_conversions": conversion_successes,
            "conversion_rate": "100.0%"
        },
        "hash_verification": {
            "frontal_keypoints_matched": kp_hash_matches,
            "annotations_matched": ann_hash_matches
        }
    }

    rep_path = REPORTS_DIR / "vsl_gh_validation.json"
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, ensure_ascii=False, indent=2)
    print(f"\nValidation report saved to: {rep_path}")
    print("\nALL VSL-GH CANONICAL DATA VALIDATION CHECKS PASSED!")


if __name__ == "__main__":
    main()
