"""
Packages landmark data, splits, and training scripts into a lightweight zip
ready for Google Colab / Kaggle (P0-3).
Archive excludes all raw videos.
Refuses any data directory containing DO_NOT_TRAIN_SYNTHETIC.md (e.g. data/vsl_alphabet_pilot).
Usage:
  python scripts/package_alphabet_cloud_data.py [--data-dir data/vsl_alphabet_real]
Output:
  data/vsl_alphabet_cloud_data.zip
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path

SYNTHETIC_MARKER = "DO_NOT_TRAIN_SYNTHETIC.md"


def package_alphabet_data(data_dir: str = "data/vsl_alphabet_real"):
    project_root = Path(__file__).resolve().parent.parent
    output_zip = project_root / "data" / "vsl_alphabet_cloud_data.zip"
    data_root = project_root / data_dir
    if (data_root / SYNTHETIC_MARKER).exists():
        sys.exit(f"[REFUSED] {data_dir} is synthetic data (see {SYNTHETIC_MARKER}).")
    if not (data_root / "splits" / "train.csv").exists():
        sys.exit(f"[ERROR] {data_dir}/splits/train.csv not found — run collect_alphabet_real.py --make-splits first.")

    files_to_pack = []

    # 1. Landmarks
    landmarks_dir = data_root / "landmarks"
    if landmarks_dir.exists():
        for p in landmarks_dir.rglob("*.npz"):
            arcname = p.relative_to(project_root)
            files_to_pack.append((p, arcname))

    # 2. Splits
    splits_dir = data_root / "splits"
    if splits_dir.exists():
        for p in splits_dir.glob("*.*"):
            arcname = p.relative_to(project_root)
            files_to_pack.append((p, arcname))

    # 3. Manifest
    manifest = data_root / "manifest.json"
    if manifest.exists():
        files_to_pack.append((manifest, manifest.relative_to(project_root)))

    # 4. Training config + source modules (imported by vsl_alphabet_cloud_training.ipynb)
    src_files = [
        project_root / "configs" / "alphabet_level1.yaml",
        project_root / "src" / "__init__.py",
        project_root / "src" / "data" / "__init__.py",
        project_root / "src" / "models" / "__init__.py",
        project_root / "src" / "data" / "alphabet_preprocessing.py",
        project_root / "src" / "data" / "alphabet_dataset.py",
        project_root / "src" / "models" / "alphabet_mlp.py",
        project_root / "src" / "models" / "alphabet_temporal.py",
    ]
    for sf in src_files:
        if sf.exists():
            files_to_pack.append((sf, sf.relative_to(project_root)))

    print(f"Packaging {len(files_to_pack)} files into {output_zip}...")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, arcname in files_to_pack:
            zf.write(file_path, arcname)

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Packaged {len(files_to_pack)} files into {output_zip} ({size_mb:.2f} MB)")
    return output_zip


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/vsl_alphabet_real")
    package_alphabet_data(parser.parse_args().data_dir)
