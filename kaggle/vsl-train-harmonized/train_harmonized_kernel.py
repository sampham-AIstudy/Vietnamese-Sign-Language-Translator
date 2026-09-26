"""
Kaggle job (GPU T4 x2): step 4b/4c harmonised Level 2 runs, one job per GPU in parallel.
Inputs : QIPEDC keypoints (vsl-extract-qipedc = native resolution; vsl-extract-qipedc360-s{0,1,2} = 360 px shards)
         VSL-GH rebuilt from upstream @ 6c351e6 -> gloss segments (scripts/export_vslgh_segments.py)
JOBS   : edit the list below; each job = train_unified.py args + which QIPEDC keypoints to use.
Output : /kaggle/working/<out>/ (metrics.json incl. val_by_source, test_logits.npz, test_predictions.csv, checkpoint)
"""
import glob, os, subprocess, sys, time

# v1 (done): run_keepz / run_dropz, native resolution. v2: chosen variant = hand z kept (pre-registered VAL rule).
JOBS = [
    {"gpu": "0", "out": "dict_keepz", "kps": "native", "args": "--features harmonized --hand-z keep --sources qipedc"},
    {"gpu": "1", "out": "run_keepz_seed43", "kps": "native", "seed": 43,   # seed variance only, never selected
     "args": "--features harmonized --hand-z keep"},
]
SEED = 42  # pre-declared, no seed selection (reports/step4_2026-09-26/PREREGISTRATION.md)


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

dirs = [p for p in glob.glob("/kaggle/input/**/qipedc_kps", recursive=True) if os.path.isdir(p)]
dirs360 = [p for p in glob.glob("/kaggle/input/**/qipedc_kps360", recursive=True) if os.path.isdir(p)]
roots = {}
for name, srcs in (("native", dirs), ("360", dirs360)):
    if not srcs:
        continue
    root = f"/tmp/root_{name}"
    kps = f"{root}/qipedc_kps"
    os.makedirs(kps, exist_ok=True)
    for d in srcs:  # 360 px comes in 3 shards: merge by symlinking every npz
        for f in glob.glob(f"{d}/*.npz"):
            dst = f"{kps}/{os.path.basename(f)}"
            if not os.path.exists(dst):
                os.symlink(f, dst)
    os.symlink(f"{REPO}/data/processed/vslgh_segments", f"{root}/vslgh_segments")
    roots[name] = root
    print(name, "qipedc npz:", len(os.listdir(kps)), "from", srcs, flush=True)

import torch
n_gpu = torch.cuda.device_count()
workers = max(1, (os.cpu_count() or 2) // max(1, min(n_gpu, len(JOBS))))
procs = []
for job in JOBS:
    out = f"/kaggle/working/{job['out']}"
    os.makedirs(out, exist_ok=True)
    extra = " --process-height 360" if job["kps"] == "360" else ""
    cmd = (f"{sys.executable} scripts/train_unified.py --data-root {roots[job['kps']]} --out-dir {out} --epochs 120 "
           f"--batch-size 64 --num-workers {workers} --patience 20 --seed {job.get('seed', SEED)} {job['args']}{extra}")
    print(f"$ [GPU {job['gpu']}] {cmd}", flush=True)
    log = open(f"{out}/train.log", "w")
    procs.append((job, out, log, subprocess.Popen(cmd, shell=True, stdout=log, stderr=subprocess.STDOUT,
                                                  env={**os.environ, "CUDA_VISIBLE_DEVICES": job["gpu"]})))
failed = []
for job, out, log, p in procs:
    rc = p.wait(); log.close()
    print(f"--- {job['out']} exit {rc} ---\n" + "".join(open(f"{out}/train.log").readlines()[-30:]), flush=True)
    if rc:
        failed.append(job["out"])
print(f"total {(time.time() - t0) / 60:.1f} min; failed: {failed}", flush=True)
assert not failed, failed
