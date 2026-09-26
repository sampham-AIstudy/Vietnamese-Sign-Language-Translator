"""
Kaggle job: extract 67-joint landmarks for QIPEDC shard 1/3 at 360 px height with the backend's extractor.
Runs under an isolated Python 3.11 + mediapipe 0.10.14 env (same version as the backend).
Output: /kaggle/working/qipedc_kps360/*.npz + manifest.csv
"""
import glob, os, subprocess, sys, time

def sh(cmd):
    print(f"$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True)

t0 = time.time()
labels = glob.glob("/kaggle/input/**/Dataset/Labels/label.csv", recursive=True)
assert labels, "QIPEDC input not attached"
videos_dir = os.path.join(os.path.dirname(os.path.dirname(labels[0])), "Videos")
print("labels:", labels[0], "| videos:", videos_dir, len(os.listdir(videos_dir)), flush=True)

sh(f"{sys.executable} -m pip install -q uv")
sh("uv venv -q /tmp/mp311 --python 3.11")
sh("uv pip install -q --python /tmp/mp311/bin/python mediapipe==0.10.14 'numpy<2' opencv-python-headless==4.10.0.84")
sh("git clone -q --depth 1 -b fix/audit-round2 https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git /tmp/vslt")
sh("cd /tmp/vslt && git log --oneline -1")
os.environ["MPLBACKEND"] = "Agg"
sh(f"cd /tmp/vslt && /tmp/mp311/bin/python scripts/extract_keypoints_batch.py "
   f"--videos-dir '{videos_dir}' --labels-csv '{labels[0]}' --source qipedc --process-height 360 --shard 1/3 "
   f"--out-dir /kaggle/working/qipedc_kps360 --workers {os.cpu_count()}")
print(f"total {(time.time() - t0) / 60:.1f} min", flush=True)
