"""
Script to analyze and audit raw VSL video dataset:
- Inspects data/Dataset/Videos/ and data/Dataset/Labels/label.csv
- Checks file integrity, OpenCV video header, resolution, FPS, frame counts
- Generates:
  1. results/raw_dataset_inventory.csv
  2. results/class_feasibility.csv
  3. results/class_feasibility_summary.json
"""

import os
import sys
import json
import hashlib
import unicodedata
import cv2
import pandas as pd
import numpy as np

# Ensure stdout handles utf-8 properly on Windows
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIDEO_DIR = os.path.join(PROJECT_ROOT, "data", "Dataset", "Videos")
LABEL_CSV = os.path.join(PROJECT_ROOT, "data", "Dataset", "Labels", "label.csv")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def compute_fast_md5(file_path: str, chunk_size: int = 65536, max_chunks: int = 32) -> str:
    """Computes MD5 hash from start, middle, and end chunks for fast integrity verification."""
    hasher = hashlib.md5()
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            if file_size <= chunk_size * max_chunks:
                # Read full file
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            else:
                # Sample head, middle, tail
                hasher.update(f.read(chunk_size * 10))
                f.seek(file_size // 2)
                hasher.update(f.read(chunk_size * 10))
                f.seek(max(0, file_size - chunk_size * 10))
                hasher.update(f.read(chunk_size * 10))
                hasher.update(str(file_size).encode())
        return hasher.hexdigest()
    except Exception:
        return "error_reading_hash"


def normalize_gloss(text: str) -> str:
    """Normalizes Vietnamese text (NFC, strip whitespace, lowercase)."""
    if not isinstance(text, str):
        return ""
    norm = unicodedata.normalize("NFC", text).strip().lower()
    return norm


def parse_dialect_from_filename(filename: str) -> str:
    """
    Extracts dialect code from filename suffix.
    E.g. D0001B.mp4 -> B (Bắc), D0001T.mp4 -> T (Trung), D0001N.mp4 -> N (Nam)
    """
    base = os.path.splitext(filename)[0].strip()
    if not base:
        return "Unknown"
    last_char = base[-1].upper()
    if last_char == "B":
        return "B (Miền Bắc / North)"
    elif last_char == "T":
        return "T (Miền Trung / Central)"
    elif last_char == "N":
        return "N (Miền Nam / South)"
    else:
        return "Neutral / Unspecified"


def analyze_videos():
    print(f"[1/4] Loading label CSV: {LABEL_CSV}")
    if not os.path.exists(LABEL_CSV):
        raise FileNotFoundError(f"Label CSV not found: {LABEL_CSV}")

    df_labels = pd.read_csv(LABEL_CSV)
    print(f"Loaded {len(df_labels)} rows from label.csv. Columns: {list(df_labels.columns)}")

    # Check videos in video directory
    all_disk_files = set(os.listdir(VIDEO_DIR)) if os.path.exists(VIDEO_DIR) else set()
    print(f"Total video files on disk: {len(all_disk_files)}")

    inventory_records = []
    print(f"[2/4] Auditing all video files and extracting metadata via OpenCV...")

    for idx, row in df_labels.iterrows():
        video_id = row.get("ID", idx + 1)
        video_name = str(row.get("VIDEO", "")).strip()
        raw_gloss = str(row.get("LABEL", "")).strip()
        norm_gloss = normalize_gloss(raw_gloss)

        file_path = os.path.join(VIDEO_DIR, video_name)
        dialect = parse_dialect_from_filename(video_name)
        # Signer ID: no explicit signer metadata exists in current dataset files
        signer_id = "unknown"

        if not os.path.exists(file_path):
            record = {
                "video_id": video_id,
                "file_name": video_name,
                "file_path": file_path,
                "file_size_mb": 0.0,
                "gloss_raw": raw_gloss,
                "gloss_normalized": norm_gloss,
                "possible_region_or_dialect": dialect,
                "possible_signer_id": signer_id,
                "num_frames": 0,
                "fps": 0.0,
                "width": 0,
                "height": 0,
                "fast_md5": "missing",
                "status": "MISSING_FILE",
            }
        else:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                record = {
                    "video_id": video_id,
                    "file_name": video_name,
                    "file_path": file_path,
                    "file_size_mb": round(size_mb, 3),
                    "gloss_raw": raw_gloss,
                    "gloss_normalized": norm_gloss,
                    "possible_region_or_dialect": dialect,
                    "possible_signer_id": signer_id,
                    "num_frames": 0,
                    "fps": 0.0,
                    "width": 0,
                    "height": 0,
                    "fast_md5": compute_fast_md5(file_path),
                    "status": "CORRUPT_CANNOT_OPEN",
                }
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)
                num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                # test read first frame
                ret, _ = cap.read()
                cap.release()

                status = "VALID" if (ret and num_frames > 0) else "UNREADABLE_FRAMES"
                record = {
                    "video_id": video_id,
                    "file_name": video_name,
                    "file_path": file_path,
                    "file_size_mb": round(size_mb, 3),
                    "gloss_raw": raw_gloss,
                    "gloss_normalized": norm_gloss,
                    "possible_region_or_dialect": dialect,
                    "possible_signer_id": signer_id,
                    "num_frames": num_frames,
                    "fps": round(fps, 2),
                    "width": width,
                    "height": height,
                    "fast_md5": compute_fast_md5(file_path),
                    "status": status,
                }

        inventory_records.append(record)

        if (idx + 1) % 500 == 0 or (idx + 1) == len(df_labels):
            print(f"  Processed {idx + 1}/{len(df_labels)} videos...")

    df_inventory = pd.DataFrame(inventory_records)
    inv_csv_path = os.path.join(RESULTS_DIR, "raw_dataset_inventory.csv")
    df_inventory.to_csv(inv_csv_path, index=False, encoding="utf-8-sig")
    print(f"[Done] Saved inventory to {inv_csv_path}")

    # Check disk videos that are not in label.csv
    csv_videos = set(df_inventory["file_name"].unique())
    unlabeled_videos = all_disk_files - csv_videos
    if unlabeled_videos:
        print(f"[Warning] Found {len(unlabeled_videos)} video files on disk not listed in label.csv!")
    else:
        print("[Info] All video files on disk match label.csv entries.")

    print(f"\n[3/4] Performing Class Feasibility Analysis...")
    # Group by normalized gloss
    valid_inv = df_inventory[df_inventory["status"] == "VALID"]
    gloss_groups = valid_inv.groupby("gloss_normalized")

    feasibility_rows = []
    for gloss, group in gloss_groups:
        v_count = len(group)
        sample_vids = ";".join(group["file_name"].tolist()[:5])
        dialects = ";".join(sorted(group["possible_region_or_dialect"].unique()))
        avg_frames = group["num_frames"].mean()
        avg_fps = group["fps"].mean()
        feasibility_rows.append({
            "gloss": gloss,
            "video_count": v_count,
            "sample_videos": sample_vids,
            "dialects_represented": dialects,
            "avg_frames": round(avg_frames, 1),
            "avg_fps": round(avg_fps, 1),
        })

    df_feasibility = pd.DataFrame(feasibility_rows)
    df_feasibility = df_feasibility.sort_values(by="video_count", ascending=False).reset_index(drop=True)
    feas_csv_path = os.path.join(RESULTS_DIR, "class_feasibility.csv")
    df_feasibility.to_csv(feas_csv_path, index=False, encoding="utf-8-sig")
    print(f"[Done] Saved class feasibility to {feas_csv_path}")

    # Summary statistics
    total_videos = len(valid_inv)
    total_glosses = len(df_feasibility)
    counts = df_feasibility["video_count"].values

    ge_2 = int(np.sum(counts >= 2))
    ge_3 = int(np.sum(counts >= 3))
    ge_5 = int(np.sum(counts >= 5))
    ge_10 = int(np.sum(counts >= 10))
    ge_20 = int(np.sum(counts >= 20))

    avg_v = float(np.mean(counts))
    med_v = float(np.median(counts))
    min_v = int(np.min(counts)) if len(counts) > 0 else 0
    max_v = int(np.max(counts)) if len(counts) > 0 else 0

    # Determine recommendation
    if ge_5 < 50:
        rec = (
            "Extremely high class imbalance and sparsity. A closed-set classification across all "
            f"{total_glosses} glosses is mathematically invalid because the vast majority of glosses "
            "have <= 2 samples (insufficient for train/val/test split). "
            f"Recommendation: Select glosses with >= 3 samples (num_glosses={ge_3}) or top 40-50 classes for closed-set benchmark."
        )
    else:
        rec = (
            f"Filter to glosses with at least 3 samples (n={ge_3}) or 5 samples (n={ge_5}) to allow "
            "strictly disjoint 1-train, 1-val, 1-test video assignment without artificial oversampling."
        )

    summary = {
        "total_valid_videos": total_videos,
        "total_glosses": total_glosses,
        "avg_videos_per_gloss": round(avg_v, 2),
        "median_videos_per_gloss": med_v,
        "min_videos_per_gloss": min_v,
        "max_videos_per_gloss": max_v,
        "num_glosses_with_ge_2": ge_2,
        "num_glosses_with_ge_3": ge_3,
        "num_glosses_with_ge_5": ge_5,
        "num_glosses_with_ge_10": ge_10,
        "num_glosses_with_ge_20": ge_20,
        "top_10_glosses": df_feasibility.head(10)[["gloss", "video_count"]].to_dict(orient="records"),
        "bottom_10_glosses": df_feasibility.tail(10)[["gloss", "video_count"]].to_dict(orient="records"),
        "recommendation": rec
    }

    sum_json_path = os.path.join(RESULTS_DIR, "class_feasibility_summary.json")
    with open(sum_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[Done] Saved class feasibility summary to {sum_json_path}")

    print("\n[4/4] Feasibility Overview:")
    print(f"  Total valid videos: {total_videos}")
    print(f"  Total unique glosses: {total_glosses}")
    print(f"  Glosses with >= 2 videos: {ge_2} ({ge_2/total_glosses*100:.1f}%)")
    print(f"  Glosses with >= 3 videos: {ge_3} ({ge_3/total_glosses*100:.1f}%)")
    print(f"  Glosses with >= 5 videos: {ge_5} ({ge_5/total_glosses*100:.1f}%)")
    print(f"  Glosses with >= 10 videos: {ge_10} ({ge_10/total_glosses*100:.1f}%)")
    print(f"  Top 5 glosses: {df_feasibility.head(5)[['gloss', 'video_count']].to_dict(orient='records')}")


if __name__ == "__main__":
    analyze_videos()

