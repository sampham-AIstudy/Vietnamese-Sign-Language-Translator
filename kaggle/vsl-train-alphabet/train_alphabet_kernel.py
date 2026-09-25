"""Kaggle job: Level 1 LOSO training/eval on extracted hand landmarks (CPU is enough)."""
import glob, os, subprocess, sys, time

def sh(cmd):
    print(f"$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True)

t0 = time.time()
data = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/alphabet_hands/manifest.csv", recursive=True)]
assert data, "attach kernel output phmvnsm33/vsl-extract-alphabet"
sh("git clone -q --depth 1 -b fix/audit-round2 https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git /tmp/vslt")
sh("cd /tmp/vslt && git log --oneline -1")
sh(f"cd /tmp/vslt && {sys.executable} scripts/train_alphabet_real.py --data-dir '{data[0]}' --out-dir /kaggle/working/alphabet_run --epochs 80")
print(f"total {(time.time() - t0) / 60:.1f} min", flush=True)
