"""Kaggle job: MediaPipe Hands (0.10.14, backend settings) over hauuto alphabet + QIPEDC letter clips."""
import glob, os, subprocess, sys, time

def sh(cmd):
    print(f"$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True)

t0 = time.time()
raw = [p for p in glob.glob("/kaggle/input/**/raw/raw", recursive=True) if os.path.isdir(os.path.join(p, "hau"))]
labels = glob.glob("/kaggle/input/**/Dataset/Labels/label.csv", recursive=True)
assert raw and labels, (raw, labels)
videos = os.path.join(os.path.dirname(os.path.dirname(labels[0])), "Videos")
sh(f"{sys.executable} -m pip install -q uv")
sh("uv venv -q /tmp/mp311 --python 3.11")
sh("uv pip install -q --python /tmp/mp311/bin/python mediapipe==0.10.14 'numpy<2' opencv-python-headless==4.10.0.84")
sh("git clone -q --depth 1 -b fix/audit-round2 https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git /tmp/vslt")
sh("cd /tmp/vslt && git log --oneline -1")
os.environ["MPLBACKEND"] = "Agg"
sh(f"cd /tmp/vslt && /tmp/mp311/bin/python scripts/build_alphabet_tasks.py --hauuto-raw '{raw[0]}' "
   f"--qipedc-labels '{labels[0]}' --qipedc-videos '{videos}' --out /tmp/alphabet_tasks.csv")
sh(f"cd /tmp/vslt && /tmp/mp311/bin/python scripts/extract_hands_batch.py --tasks-csv /tmp/alphabet_tasks.csv "
   f"--out-dir /kaggle/working/alphabet_hands --workers {os.cpu_count()}")
sh("cp /tmp/alphabet_tasks.csv /kaggle/working/alphabet_hands/tasks.csv")
print(f"total {(time.time() - t0) / 60:.1f} min", flush=True)
