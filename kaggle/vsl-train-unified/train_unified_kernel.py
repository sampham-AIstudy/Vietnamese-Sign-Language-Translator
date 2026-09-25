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
# T4 x2: one training per GPU in parallel. Seed 42 (-> run/) is the pre-declared primary result used
# for the report and the backend gate; seed 43 (-> run_seed43/) only measures seed-to-seed variance.
import torch
n_gpu = torch.cuda.device_count()
workers = max(1, (os.cpu_count() or 2) // max(1, min(n_gpu, 2)))
cmd = (f"{sys.executable} scripts/train_unified.py --data-root {root} --epochs 120 --batch-size 64 "
       f"--num-workers {workers} --patience 20")
jobs = [("0", 42, "/kaggle/working/run")] + ([("1", 43, "/kaggle/working/run_seed43")] if n_gpu >= 2 else [])
procs = []
for gpu, seed, out in jobs:
    os.makedirs(out, exist_ok=True)
    print(f"$ [GPU {gpu}] {cmd} --seed {seed} --out-dir {out}", flush=True)
    log = open(f"{out}/train.log", "w")
    procs.append((seed, out, log, subprocess.Popen(f"{cmd} --seed {seed} --out-dir {out}", shell=True, stdout=log,
                                                   stderr=subprocess.STDOUT, env={**os.environ, "CUDA_VISIBLE_DEVICES": gpu})))
failed = []
for seed, out, log, p in procs:
    rc = p.wait(); log.close()
    print(f"--- seed {seed} exit {rc}; tail of {out}/train.log ---", flush=True)
    print("".join(open(f"{out}/train.log").readlines()[-40:]), flush=True)
    if rc != 0:
        failed.append(seed)
assert 42 not in failed, "primary run (seed 42) failed"
print(f"total {(time.time() - t0) / 60:.1f} min", flush=True)
