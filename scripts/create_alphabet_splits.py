"""
Generate signer-disjoint splits for VSL Alphabet Pilot Dataset (P0-3).
Signers:
  Train (10): S01, S04, S05, S06, S07, S08, S09, S10, S11, S13 (1,250 clips)
  Val   (2) : S02, S12 (250 clips)
  Test  (3) : S03, S14, S15 (375 clips)
Outputs:
  data/vsl_alphabet_pilot/splits/train.csv
  data/vsl_alphabet_pilot/splits/val.csv
  data/vsl_alphabet_pilot/splits/test.csv
  data/vsl_alphabet_pilot/splits/classes.txt
"""

import os
import json
import csv

MANIFEST_PATH = "data/vsl_alphabet_pilot/manifest.json"
OUTPUT_DIR = "data/vsl_alphabet_pilot/splits"

TRAIN_SIGNERS = {"S01", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S13"}
VAL_SIGNERS = {"S02", "S12"}
TEST_SIGNERS = {"S03", "S14", "S15"}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"]
    print(f"Total samples in manifest: {len(samples)}")

    train_rows, val_rows, test_rows = [], [], []
    classes = set()

    for s in samples:
        signer = s["signer_id"]
        symbol = s["symbol"]
        classes.add(symbol)

        row = {
            "sample_id": s["sample_id"],
            "signer_id": signer,
            "symbol": symbol,
            "symbol_type": s.get("symbol_type", "letter"),
            "handedness": s.get("handedness", "Right"),
            "repetition": s.get("repetition", 1),
            "hold_start_frame": s.get("hold_start_frame", 30),
            "hold_end_frame": s.get("hold_end_frame", 90),
            "landmark_path": s.get("landmark_path", ""),
            "source_video": s.get("source_video", ""),
            "split": "train" if signer in TRAIN_SIGNERS else ("val" if signer in VAL_SIGNERS else "test"),
        }

        if signer in TRAIN_SIGNERS:
            train_rows.append(row)
        elif signer in VAL_SIGNERS:
            val_rows.append(row)
        elif signer in TEST_SIGNERS:
            test_rows.append(row)
        else:
            raise ValueError(f"Unknown signer {signer}")

    fieldnames = [
        "sample_id",
        "signer_id",
        "symbol",
        "symbol_type",
        "handedness",
        "repetition",
        "hold_start_frame",
        "hold_end_frame",
        "landmark_path",
        "source_video",
        "split",
    ]

    def save_csv(path: str, rows: list):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} rows to {path}")

    save_csv(os.path.join(OUTPUT_DIR, "train.csv"), train_rows)
    save_csv(os.path.join(OUTPUT_DIR, "val.csv"), val_rows)
    save_csv(os.path.join(OUTPUT_DIR, "test.csv"), test_rows)

    sorted_classes = sorted(list(classes))
    with open(os.path.join(OUTPUT_DIR, "classes.txt"), "w", encoding="utf-8") as f:
        for c in sorted_classes:
            f.write(f"{c}\n")

    print(f"Saved {len(sorted_classes)} classes to {os.path.join(OUTPUT_DIR, 'classes.txt')}")
    print("Signer sets:")
    print(f"  Train: {sorted(list(TRAIN_SIGNERS))} -> {len(train_rows)} samples")
    print(f"  Val  : {sorted(list(VAL_SIGNERS))} -> {len(val_rows)} samples")
    print(f"  Test : {sorted(list(TEST_SIGNERS))} -> {len(test_rows)} samples")
    print("Done!")


if __name__ == "__main__":
    main()
