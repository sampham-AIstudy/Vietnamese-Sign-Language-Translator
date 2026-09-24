"""
Packages landmark data, splits, and training scripts into a lightweight zip
ready for Google Colab / Kaggle (P0-3).
Archive excludes all raw videos to keep upload size ~10-15 MB.
Output:
  data/vsl_alphabet_cloud_data.zip
"""

import os
import zipfile
from pathlib import Path


def package_alphabet_data():
    project_root = Path(__file__).resolve().parent.parent
    output_zip = project_root / "data" / "vsl_alphabet_cloud_data.zip"

    files_to_pack = []

    # 1. Landmarks
    landmarks_dir = project_root / "data" / "vsl_alphabet_pilot" / "landmarks"
    if landmarks_dir.exists():
        for p in landmarks_dir.rglob("*.npz"):
            arcname = p.relative_to(project_root)
            files_to_pack.append((p, arcname))

    # 2. Splits
    splits_dir = project_root / "data" / "vsl_alphabet_pilot" / "splits"
    if splits_dir.exists():
        for p in splits_dir.glob("*.*"):
            arcname = p.relative_to(project_root)
            files_to_pack.append((p, arcname))

    # 3. Manifest
    manifest = project_root / "data" / "vsl_alphabet_pilot" / "manifest.json"
    if manifest.exists():
        files_to_pack.append((manifest, manifest.relative_to(project_root)))

    # 4. Source modules
    src_files = [
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
    package_alphabet_data()
