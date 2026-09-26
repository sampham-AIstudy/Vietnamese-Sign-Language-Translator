"""Kaggle job: pack the vsl-extract-qipedc output (qipedc_kps/*.npz + manifest) into one tar for a fast download."""
import glob, os, tarfile
src = [p for p in glob.glob("/kaggle/input/**/qipedc_kps", recursive=True) if os.path.isdir(p)][0]
with tarfile.open("/kaggle/working/qipedc_kps.tar", "w") as t:
    t.add(src, arcname="qipedc_kps")
print("packed", len(os.listdir(src)), "files", os.path.getsize("/kaggle/working/qipedc_kps.tar") // 2**20, "MB")
