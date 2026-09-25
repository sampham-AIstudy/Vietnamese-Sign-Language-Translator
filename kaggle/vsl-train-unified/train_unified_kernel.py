"""
Kaggle job: train the unified isolated-sign recogniser (GPU).
Inputs : QIPEDC keypoints from kernel phmvnsm33/vsl-extract-qipedc (qipedc_kps/)
         VSL-GH rebuilt from upstream @ 6c351e6 -> gloss segments (scripts/export_vslgh_segments.py)
Output : /kaggle/working/run/ (checkpoint with label_map + preprocessing, metrics.json, per-class CSVs)
"""
import glob, os, subprocess, sys, time

def sh(cmd):
    print(f"$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True)

t0 = time.time()
REPO, VSLGH = "/tmp/vslt", "/tmp/vslt/clone/Vietnamese-Sign-Language-Translation"
sh(f"git clone -q --depth 1 -b fix/audit-round2 https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git {REPO}")
sh(f"cd {REPO} && git log --oneline -1")
sh(f"git clone -q https://github.com/nguyentheanh822/Vietnamese-Sign-Language-Translation.git {VSLGH}")
sh(f"cd {VSLGH} && git checkout -q 6c351e63c0b2cf1b5e2e8056bb3bf2d6f31dc90a && git log --oneline -1")
os.chdir(REPO)
sh(f"{sys.executable} scripts/prepare_canonical_vsl_gh.py > /tmp/prepare_vslgh.log 2>&1 || (tail -40 /tmp/prepare_vslgh.log; exit 1)")
sh(f"{sys.executable} scripts/export_vslgh_segments.py")

kps = [p for p in glob.glob("/kaggle/input/**/qipedc_kps", recursive=True) if os.path.isdir(p)]
assert kps, "attach kernel output phmvnsm33/vsl-extract-qipedc"
root = "/tmp/data_root"
os.makedirs(root, exist_ok=True)
for name, target in (("qipedc_kps", kps[0]), ("vslgh_segments", f"{REPO}/data/processed/vslgh_segments")):
    if not os.path.exists(f"{root}/{name}"):
        os.symlink(target, f"{root}/{name}")
print("qipedc npz:", len(glob.glob(f"{kps[0]}/*.npz")), flush=True)

sh(f"{sys.executable} -c \"import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)\"")
sh(f"{sys.executable} scripts/train_unified.py --data-root {root} --out-dir /kaggle/working/run "
   f"--epochs 120 --batch-size 64 --num-workers {os.cpu_count()} --patience 20")
print(f"total {(time.time() - t0) / 60:.1f} min", flush=True)
