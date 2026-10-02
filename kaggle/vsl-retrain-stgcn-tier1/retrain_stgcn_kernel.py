"""
Kaggle job K1 of plan 13 (docs/plans/13-train-lai-checkpoint-thieu.md §3.4e): checkpoints/stgcn_best.pt (Tier 1, a4).

Clone the repository at PIN_COMMIT (asserted; the running file must equal the pinned one except the PIN_COMMIT line),
read reports/retrain_<D>/preregistration.json of the pin (committed exactly once, ancestor of the pin), restore the
Tier 1 inputs from the PRIVATE dataset phmvnsm33/vslt-retrain-inputs-tier1 (SHA256SUMS of the dataset checked, npz copied
- never linked - into data/extracted_keypoints/, the 3 CSV + classes of the clone checked with lf_sha256), measure them
with scripts/retrain_preregister.py (measure_tier1) and compare with the preregistration -> any difference: stop before
training. Then the registered commands (jobs.k1): train.py --seed 42, sanity checks (plan 13 §3.6), and evaluate_test.py
EXACTLY ONCE (only when the sanity checks pass). Sidecar stgcn_best.meta.json (label_map of get_vsl_dataloaders, sha256
of the inputs, seed, commit) - the checkpoint format is unchanged. Watchdog: jobs.k1.watchdog_minutes (wall clock).
Output: /kaggle/working/k1/ (stgcn_best.pt, stgcn_best.meta.json, stgcn_history.json, eval/, logs/, sanity.json,
preflight.json, env.json, SHA256SUMS). Nothing is deleted.
"""
import datetime
import glob
import hashlib
import json
import math
import os
import platform
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

PIN_COMMIT = None  # full 40-hex commit of the pinned code; set in the commit that pushes this kernel (B8)

REPO_URL = "https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git"
BRANCH = "feat/vslt-complete"
KERNEL_FILE_IN_REPO = "kaggle/vsl-retrain-stgcn-tier1/retrain_stgcn_kernel.py"
REPO = Path("/tmp/vslt")
WORK = Path("/kaggle/working/k1")
INPUT_ROOT = Path("/kaggle/input")
PIN_LINE_RX = re.compile(r"^PIN_COMMIT = .*$", re.M)
SUMS = "SHA256SUMS"
METADATA = "dataset-metadata.json"


class KernelError(Exception):
    pass


class Watchdog(KernelError):
    pass


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print(msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def lf_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def check_pin(pin):
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise KernelError(f"PIN_COMMIT must be a full 40-hex commit, got {pin!r} (set it in the commit that pushes "
                          "this kernel)")
    return pin


def same_as_pinned(running_text, pinned_text):
    norm = lambda t: PIN_LINE_RX.sub("PIN_COMMIT = <pin>", t.replace("\r\n", "\n"))  # noqa: E731
    if norm(running_text) != norm(pinned_text):
        raise KernelError(f"the running kernel differs from {KERNEL_FILE_IN_REPO} at the pinned commit "
                          "(other than the PIN_COMMIT line)")


def _kill(proc):
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, OSError):
        pass


def run(argv, cwd, log_path, deadline, env=None):
    remaining = deadline - time.time()
    if remaining <= 0:
        raise Watchdog(f"watchdog: no time left before {argv[:3]}")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    log(f"$ {' '.join(map(str, argv))}  (cwd={cwd}, log={log_path})")
    with open(log_path, "a", encoding="utf-8") as lf:
        kw = {"start_new_session": True} if os.name == "posix" else {}
        proc = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), stdout=lf, stderr=subprocess.STDOUT,
                                env=env, **kw)
        try:
            rc = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _kill(proc)
            proc.wait()
            raise Watchdog(f"watchdog: killed {argv[:3]} at the wall-clock limit") from None
    return rc


def run_ok(argv, cwd, log_path, deadline, env=None):
    rc = run(argv, cwd, log_path, deadline, env=env)
    if rc != 0:
        tail = "".join(Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines(True)[-40:])
        raise KernelError(f"exit {rc}: {argv[:4]}\n{tail}")


def copy_new(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as fi, open(dst, "xb") as fo:
        for block in iter(lambda: fi.read(1 << 20), b""):
            fo.write(block)
    if sha256_file(src) != sha256_file(dst):
        raise KernelError(f"sha256 changed while copying {src} -> {dst}")
    return dst


def copy_tree_new(src, dst):
    for p in sorted(Path(src).rglob("*")):
        if p.is_file():
            copy_new(p, Path(dst) / p.relative_to(src))


def write_json_new(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def write_sums(work):
    lines = []
    for p in sorted(Path(work).rglob("*")):
        if p.is_file() and p.name != SUMS:
            lines.append(f"{sha256_file(p)}  {p.relative_to(work).as_posix()}\n")
    with open(Path(work) / SUMS, "x", encoding="utf-8", newline="\n") as f:
        f.write("".join(lines))


# ---------------------------------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------------------------------
def parse_sums(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        h, sep, name = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", h) or not name or name in out:
            raise KernelError(f"{SUMS}: invalid line {line!r}")
        out[name] = h
    if not out:
        raise KernelError(f"{SUMS} is empty")
    return out


def find_input_dir(prereg, input_root=INPUT_ROOT):
    """The one mounted dataset directory whose SHA256SUMS lists the Tier 1 train CSV archive name."""
    want = prereg["inputs"]["tier1_grouped_train_csv"]["path"].replace("/", "__")
    hits = [p.parent for p in Path(input_root).rglob(SUMS) if (p.parent / want).is_file()]
    if len(hits) != 1:
        raise KernelError(f"expected exactly one input dataset with {want} under {input_root}, found {hits}")
    return hits[0]


def restore_tier1(input_dir, repo, prereg):
    """Check the dataset against its SHA256SUMS, copy the npz (new files only, no link), check the CSV/classes of the
    clone (tracked) and of the dataset with lf_sha256 against the preregistration. Returns a record."""
    sums = parse_sums(Path(input_dir) / SUMS)
    present = sorted(p.name for p in Path(input_dir).iterdir() if p.is_file() and p.name not in (SUMS, METADATA))
    if sorted(sums) != present:
        raise KernelError(f"dataset files != {SUMS}: extra={sorted(set(present) - set(sums))} "
                          f"missing={sorted(set(sums) - set(present))}")
    for name, h in sums.items():
        got = sha256_file(Path(input_dir) / name)
        if got != h:
            raise KernelError(f"{name}: sha256 {got} != {SUMS} {h}")
    text_entries = {k: v for k, v in prereg["inputs"].items()
                    if k.startswith("tier1_grouped_") and isinstance(v, dict) and "lf_sha256" in v}
    checked = {}
    for key, e in sorted(text_entries.items()):
        arch = e["path"].replace("/", "__")
        if arch not in sums:
            raise KernelError(f"{arch} not in the input dataset")
        for where, p in (("dataset", Path(input_dir) / arch), ("clone", Path(repo) / e["path"])):
            if not p.is_file():
                raise KernelError(f"{key}: {where} file missing: {p}")
            if lf_sha256(p) != e["lf_sha256"]:
                raise KernelError(f"{key}: lf_sha256 of the {where} file != preregistration")
        checked[key] = e["lf_sha256"]
    npz_dir_rel = prereg["inputs"]["tier1_npz"]["path"]
    n_npz = 0
    for name in sorted(sums):
        rel = name.replace("__", "/")
        if rel.startswith(npz_dir_rel + "/") and rel.endswith(".npz"):
            dst = Path(repo) / rel
            if dst.exists():
                if sha256_file(dst) != sums[name]:
                    raise KernelError(f"{dst} exists with another sha256")
            else:
                copy_new(Path(input_dir) / name, dst)
            n_npz += 1
    return {"input_dir": str(input_dir), "n_files": len(sums), "n_npz_restored": n_npz, "text_lf_sha256": checked}


# ---------------------------------------------------------------------------------------------------------------------
# sanity (plan 13 §3.6) — pure, unit-tested locally
# ---------------------------------------------------------------------------------------------------------------------
def sanity_k1(history, checkpoint_meta, n_classes):
    """Every loss finite; best epoch >= 1; val top-1 at the best epoch > 100 / n_classes."""
    bad = [h.get("epoch") for h in history for k in ("train_loss", "val_loss")
           if not isinstance(h.get(k), (int, float)) or not math.isfinite(h[k])]
    best_epoch = checkpoint_meta.get("epoch")
    top1 = checkpoint_meta.get("val_top1")
    chance = 100.0 / n_classes if n_classes else None
    ok = (bool(history) and not bad and isinstance(best_epoch, int) and best_epoch >= 1 and chance is not None
          and isinstance(top1, (int, float)) and math.isfinite(top1) and top1 > chance)
    return {"n_epochs": len(history), "non_finite_loss_epochs": bad, "best_epoch": best_epoch,
            "val_top1_best": top1, "chance_top1": chance, "n_classes": n_classes, "ok": ok}


def git(*args, cwd=REPO):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise KernelError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def clone_pinned(pin, deadline):
    run_ok(["git", "clone", "-q", "-b", BRANCH, REPO_URL, str(REPO)], "/tmp", WORK / "logs" / "clone.log", deadline)
    run_ok(["git", "-C", str(REPO), "checkout", "-q", pin], "/tmp", WORK / "logs" / "clone.log", deadline)
    head = git("rev-parse", "HEAD")
    if head != pin:
        raise KernelError(f"HEAD {head} != PIN_COMMIT {pin}")
    log(f"PINNED COMMIT {head}")
    same_as_pinned(Path(__file__).read_text(encoding="utf-8"), (REPO / KERNEL_FILE_IN_REPO).read_text(encoding="utf-8"))
    return head


def load_prereg():
    found = sorted(glob.glob(str(REPO / "reports" / "retrain_*" / "preregistration.json")))
    if len(found) != 1:
        raise KernelError(f"expected exactly one reports/retrain_*/preregistration.json at the pin, found {found}")
    rel = Path(found[0]).relative_to(REPO).as_posix()
    commits = [c for c in git("log", "--format=%H", "--", rel).splitlines() if c]
    if len(commits) != 1:
        raise KernelError(f"{rel} has {len(commits)} commits (must be exactly 1, never changed)")
    subprocess.run(["git", "merge-base", "--is-ancestor", commits[0], "HEAD"], cwd=str(REPO), check=True)
    with open(found[0], encoding="utf-8") as f:
        prereg = json.load(f)
    log(f"PREREGISTRATION {rel} commit {commits[0]} (ancestor of the pin)")
    return rel, commits[0], prereg


def main():
    t0 = time.time()
    env_rec = {"job": "k1", "start_utc": utc(), "python": platform.python_version(), "platform": platform.platform()}
    rc = 1
    WORK.mkdir(parents=True, exist_ok=True)
    n_test_runs = 0
    try:
        pin = check_pin(PIN_COMMIT)
        deadline = t0 + 3600
        env_rec["commit"] = clone_pinned(pin, deadline)
        prereg_rel, prereg_commit, prereg = load_prereg()
        env_rec.update({"preregistration": prereg_rel, "preregistration_commit": prereg_commit})
        k1 = prereg["jobs"]["k1"]
        deadline = t0 + 60 * k1["watchdog_minutes"]
        env_rec["watchdog_minutes"] = k1["watchdog_minutes"]
        env_rec["inputs"] = restore_tier1(find_input_dir(prereg), REPO, prereg)

        sys.path[:0] = [str(REPO), str(REPO / "scripts")]
        os.chdir(REPO)
        import retrain_preregister as P
        rows = P.compare(prereg, {"inputs": P.measure_tier1(REPO)}, P.K1_COMPARE)
        bad = [r for r in rows if not r["ok"]]
        for r in rows:
            log(f"{'MATCH   ' if r['ok'] else 'MISMATCH'} {r['key']}: expected={r['expected']} measured={r['measured']}")
        write_json_new(WORK / "preflight.json", {"rows": rows, "n_rows": len(rows), "n_mismatch": len(bad)})
        if bad:
            raise KernelError(f"INPUT MISMATCH: {len(bad)} of {len(rows)} values differ from the preregistration")
        log(f"INPUTS OK: {len(rows)} values == preregistration")

        import torch
        env_rec.update({"torch": torch.__version__, "cuda": torch.version.cuda,
                        "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]})
        py = sys.executable
        t = time.time()
        env_rec["train_start_utc"] = utc()
        run_ok([py, *k1["train"]["argv"]], REPO, WORK / "logs" / "train.log", deadline,
               env={**os.environ, "PYTHONUNBUFFERED": "1"})
        env_rec.update({"train_end_utc": utc(), "train_minutes": round((time.time() - t) / 60, 2)})

        from src.data.vsl_dataset import get_vsl_dataloaders
        _, _, _, label_map = get_vsl_dataloaders(tier="tier1", batch_size=1, num_workers=0)
        ckpt_path = REPO / k1["checkpoint"]
        meta = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
        history = json.loads((REPO / k1["history_file"]).read_text(encoding="utf-8"))
        sanity = sanity_k1(history, {k: meta.get(k) for k in ("epoch", "val_top1", "val_loss")}, len(label_map))
        write_json_new(WORK / "sanity.json", sanity)
        copy_new(ckpt_path, WORK / "stgcn_best.pt")
        copy_new(REPO / k1["history_file"], WORK / "stgcn_history.json")
        write_json_new(WORK / "stgcn_best.meta.json", {
            "checkpoint": "stgcn_best.pt", "checkpoint_sha256": sha256_file(WORK / "stgcn_best.pt"),
            "label_map": label_map, "n_classes": len(label_map), "seed": prereg["jobs"]["seed"],
            "commit": env_rec["commit"], "preregistration_commit": prereg_commit,
            "inputs_lf_sha256": env_rec["inputs"]["text_lf_sha256"],
            "note": "sidecar of plan 13 §3.4e; the checkpoint format is unchanged (no label_map inside)"})
        if not sanity["ok"]:
            raise KernelError(f"sanity checks (plan 13 §3.6) failed: {sanity} -> test NOT run; CAN NGUOI DUNG")
        n_test_runs += 1  # the one test run of K1
        env_rec["test_start_utc"] = utc()
        run_ok([py, *k1["test"]["argv"]], REPO, WORK / "logs" / "evaluate_test.log", deadline,
               env={**os.environ, "PYTHONUNBUFFERED": "1"})
        env_rec["test_end_utc"] = utc()
        rc = 0
    except Exception as e:  # noqa: BLE001 - recorded, then exit != 0
        env_rec["error"] = f"{type(e).__name__}: {e}"
        log(f"K1 FAILED: {env_rec['error']}")
    finally:
        env_rec.update({"end_utc": utc(), "total_minutes": round((time.time() - t0) / 60, 2), "exit": rc,
                        "n_test_runs": n_test_runs})
        write_json_new(WORK / "env.json", env_rec)
        write_sums(WORK)
    return rc


if __name__ == "__main__":
    sys.exit(main())
