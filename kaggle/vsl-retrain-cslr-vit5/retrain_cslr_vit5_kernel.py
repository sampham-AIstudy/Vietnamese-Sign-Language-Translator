"""
Kaggle job K2 of plan 13 (docs/plans/13-train-lai-checkpoint-thieu.md §3.4e + [LS1]): CSLR + gloss vocab + ViT5 s1 -> s2.

MODE (a constant, changed only by a commit):
  "preflight"  CPU, no accelerator. Clone the repository at PIN_COMMIT (asserted), the two upstream sources at the commits
               of the preregistration, install the pinned libraries, rebuild the data (VSL-GH canonical, 10k parallel
               text, cleaned 10k, train-only vocab), download VietAI/vit5-base (snapshot sha recorded), then measure
               everything with scripts/retrain_preregister.py (measure_k2 — the same code that wrote the
               preregistration) and compare with reports/retrain_<D>/preregistration.json. Any difference -> exit != 0.
               No training and no evaluation of any kind.
  "train"      preflight again (still stops on a difference), backbone checkpoints/stgcn_best.pt from the K1 output with
               sha256 == reports/retrain_<D>/k1_outputs.json (missing / different -> stop: train_cslr.py would otherwise
               train from scratch silently), kernel LEAK CHECK, then GPU0: CSLR | GPU1: ViT5 stage 1 -> stage 2, with the
               commands written in the preregistration (jobs.k2), all with --sentence-split. The test set is never
               touched here: the CSLR log must contain exactly one "TEST DEFERRED (sentence split v1)" line and no
               "PRIMARY TEST EVALUATION" line; the one evaluation runs later, locally (plan 13 §3.12).
Every command, commit, version, cap and expected digest is READ from the preregistration of the pinned commit; nothing
is typed in this file except the repository URL / branch, MODE and PIN_COMMIT. Watchdog: wall clock from the
preregistration (jobs.k2.watchdog_minutes); on expiry every child process is killed and the kernel exits != 0.
Output: /kaggle/working/k2/ (preflight.json, env.json, logs/, rebuilt vocab, [train: checkpoints, used ids, histories],
SHA256SUMS). Nothing outside /kaggle/working is kept; nothing is deleted.
"""
import datetime
import glob
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

MODE = "preflight"  # "preflight" | "train"   (plan 13 §3.4e: changed only by a commit)
PIN_COMMIT = None   # full 40-hex commit of the pinned code; set in the commit that pushes this kernel (B7 / B9)

REPO_URL = "https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git"
BRANCH = "feat/vslt-complete"
KERNEL_FILE_IN_REPO = "kaggle/vsl-retrain-cslr-vit5/retrain_cslr_vit5_kernel.py"
REPO = Path("/tmp/vslt")
WORK = Path("/kaggle/working/k2")
SCRATCH = Path("/tmp/k2_scratch")
MODES = ("preflight", "train")
PIN_LINE_RX = re.compile(r"^PIN_COMMIT = .*$", re.M)
TEST_DEFERRED = "TEST DEFERRED (sentence split v1)"
PRIMARY_TEST = "PRIMARY TEST EVALUATION"
# first line of any training loop: smoke test / CSLR start / epoch lines of train_cslr.py and the two ViT5 scripts
CSLR_TRAIN_LINE = re.compile(r"Smoke Epoch|CSLR TRAINING STARTED|\bEpoch\s+0*\d+/")
VIT5_TRAIN_LINE = re.compile(r"\bEpoch\s+0*\d+/")


class KernelError(Exception):
    pass


class Watchdog(KernelError):
    pass


# ---------------------------------------------------------------------------------------------------------------------
# small helpers (no third-party import before the pinned libraries are installed)
# ---------------------------------------------------------------------------------------------------------------------
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


def check_pin(pin):
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise KernelError(f"PIN_COMMIT must be a full 40-hex commit, got {pin!r} (set it in the commit that pushes "
                          "this kernel)")
    return pin


def same_as_pinned(running_text, pinned_text):
    """The running kernel must be the pinned file except for the PIN_COMMIT line (the pin cannot contain itself)."""
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
    """Run a child process, output to `log_path`; the wall-clock `deadline` (time.time()) kills it -> Watchdog."""
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
    """Copy bytes to a NEW file (never overwrite), check sha256."""
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
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {p.relative_to(work).as_posix()}\n")
    with open(Path(work) / "SHA256SUMS", "x", encoding="utf-8", newline="\n") as f:
        f.write("".join(lines))


# ---------------------------------------------------------------------------------------------------------------------
# checks on logs / histories (pure functions, unit-tested locally)
# ---------------------------------------------------------------------------------------------------------------------
def check_cslr_log(text):
    """AC5 [LS1]: no PRIMARY_TEST line, exactly one TEST_DEFERRED line, LEAK CHECK OK (cslr) before the first training
    line, backbone transferred (never 'Training from scratch')."""
    lines = text.splitlines()
    problems = []
    n_primary = sum(PRIMARY_TEST in ln for ln in lines)
    n_deferred = sum(TEST_DEFERRED in ln for ln in lines)
    if n_primary:
        problems.append(f"{n_primary} '{PRIMARY_TEST}' line(s)")
    if n_deferred != 1:
        problems.append(f"{n_deferred} '{TEST_DEFERRED}' line(s) (expected 1)")
    leak = next((i for i, ln in enumerate(lines) if "LEAK CHECK OK (cslr)" in ln), None)
    epoch = next((i for i, ln in enumerate(lines) if CSLR_TRAIN_LINE.search(ln)), None)
    if leak is None:
        problems.append("no 'LEAK CHECK OK (cslr)' line")
    elif epoch is not None and epoch < leak:
        problems.append("first epoch line before 'LEAK CHECK OK (cslr)'")
    if any("LEAK CHECK FAILED" in ln for ln in lines):
        problems.append("LEAK CHECK FAILED")
    if any("Training from scratch" in ln for ln in lines) or not any("[MODEL] Transferred" in ln for ln in lines):
        problems.append("backbone not transferred (stgcn_best.pt missing?)")
    if problems:
        raise KernelError("CSLR log check failed: " + "; ".join(problems))


def check_vit5_log(text, job):
    lines = text.splitlines()
    tag = f"LEAK CHECK OK ({job})"
    leak = next((i for i, ln in enumerate(lines) if tag in ln), None)
    epoch = next((i for i, ln in enumerate(lines) if VIT5_TRAIN_LINE.search(ln)), None)
    problems = []
    if leak is None:
        problems.append(f"no '{tag}' line")
    elif epoch is not None and epoch < leak:
        problems.append(f"first epoch line before '{tag}'")
    if any(PRIMARY_TEST in ln or "LEAK CHECK FAILED" in ln for ln in lines):
        problems.append("test evaluation or failed leak check in the log")
    if problems:
        raise KernelError(f"{job} log check failed: " + "; ".join(problems))


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x not in (float("inf"), float("-inf"))


def sanity_cslr(history, summary):
    """Plan 13 §3.6: every loss finite, best epoch >= 1, best_val_wer < 100."""
    bad = [h.get("epoch") for h in history for k in ("train_loss", "val_loss") if not _finite(h.get(k))]
    best_epoch = (summary.get("training_time") or {}).get("best_epoch")
    best_wer = (summary.get("validation_s05") or {}).get("best_val_wer")
    out = {"n_epochs": len(history), "non_finite_loss_epochs": bad, "best_epoch": best_epoch, "best_val_wer": best_wer,
           "test_deferred": summary.get("test_deferred"), "test_s06": summary.get("test_s06")}
    out["ok"] = (bool(history) and not bad and isinstance(best_epoch, int) and best_epoch >= 1 and _finite(best_wer)
                 and best_wer < 100 and summary.get("test_deferred") is True and summary.get("test_s06") is None)
    return out


def sanity_vit5(summary, need_best_epoch):
    hist = summary.get("history") or []
    bad = [h.get("epoch") for h in hist for k in ("train_loss", "val_loss") if not _finite(h.get(k))]
    out = {"n_epochs": len(hist), "non_finite_loss_epochs": bad, "best_val_loss": summary.get("best_val_loss"),
           "best_epoch": summary.get("best_epoch")}
    ok = bool(hist) and not bad and _finite(summary.get("best_val_loss"))
    if need_best_epoch:
        ok = ok and isinstance(summary.get("best_epoch"), int) and summary["best_epoch"] >= 1
    out["ok"] = ok
    return out


def place_backbone(src, dst, expected_sha256):
    """Copy the K1 checkpoint to checkpoints/stgcn_best.pt only if its sha256 is the registered one."""
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise KernelError(f"no registered sha256 for stgcn_best.pt: {expected_sha256!r}")
    if src is None or not Path(src).is_file():
        raise KernelError(f"backbone stgcn_best.pt not found in the K1 output ({src}); refusing to train from scratch")
    got = sha256_file(src)
    if got != expected_sha256:
        raise KernelError(f"backbone sha256 {got} != k1_outputs.json {expected_sha256}")
    if Path(dst).exists():
        raise KernelError(f"{dst} already exists")
    copy_new(src, dst)
    if sha256_file(dst) != expected_sha256:
        raise KernelError("backbone sha256 changed after copy")
    return got


# ---------------------------------------------------------------------------------------------------------------------
# steps
# ---------------------------------------------------------------------------------------------------------------------
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


def pip_pinned(prereg, deadline):
    pins = prereg["k2_pip_pinned"]
    argv = [sys.executable, "-m", "pip", "install", "-q", *[f"{n}=={v}" for n, v in sorted(pins.items())]]
    run_ok(argv, "/tmp", WORK / "logs" / "pip.log", deadline)
    from importlib.metadata import version
    got = {n: version(n) for n in pins}
    if got != pins:
        raise KernelError(f"installed {got} != preregistration k2_pip_pinned {pins} (plan 13 R4: CAN PLANNER)")
    return got


def clone_upstreams(prereg, deadline):
    out = {}
    for name, src in sorted(prereg["upstream_sources"].items()):
        dst = REPO / src["clone_dir"]
        run_ok(["git", "clone", "-q", src["url"], str(dst)], "/tmp", WORK / "logs" / "clone.log", deadline)
        run_ok(["git", "-C", str(dst), "checkout", "-q", src["commit"]], "/tmp", WORK / "logs" / "clone.log", deadline)
        head = git("rev-parse", "HEAD", cwd=dst)
        if head != src["commit"]:
            raise KernelError(f"{name}: HEAD {head} != {src['commit']}")
        out[name] = head
        log(f"UPSTREAM {name} {head}")
    return out


TRANSLATION_RUNNER = '''
import importlib.util, sys
from pathlib import Path
repo, report = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("prepare_canonical_translation",
                                              repo / "scripts" / "prepare_canonical_translation.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)  # module level: stdout wrapper + mkdir of the hard-coded Windows paths (relative -> scratch)
m.PROJECT_ROOT = repo
m.CORPUS_DIR = repo / "clone" / "Parallel-Corpus-Vie-VSL"
m.VSL_SRC = m.CORPUS_DIR / "VSL10k.txt"
m.VIE_SRC = m.CORPUS_DIR / "Vie10k.txt"
m.OUTPUT_DIR = repo / "data" / "external" / "parallel_text"
m.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
m.OUTPUT_JSONL = m.OUTPUT_DIR / "vie_vsl_10k.jsonl"
m.REPORTS_DIR = report.parent
m.REPORT_JSON = report
m.main()
'''


def build_data(prereg, deadline):
    jobs = prereg["jobs"]["k2"]["data_prep"]
    py = sys.executable
    run_ok([py, *jobs["vsl_gh"]["argv"]], REPO, WORK / "logs" / "prepare_vsl_gh.log", deadline)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    runner = SCRATCH / "run_prepare_translation.py"
    runner.write_text(TRANSLATION_RUNNER, encoding="utf-8")
    run_ok([py, str(runner), str(REPO), str(WORK / "translation_corpus_validation.json")], SCRATCH,
           WORK / "logs" / "prepare_translation.log", deadline)
    run_ok([py, *jobs["clean_10k"]["argv"]], REPO, WORK / "logs" / "clean_10k.log", deadline)
    run_ok([py, *jobs["vocab"]["argv"]], REPO, WORK / "logs" / "vocab.log", deadline)


HF_PROBE = '''
import json, sys
from pathlib import Path
from huggingface_hub import snapshot_download
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
name = sys.argv[1]
path = snapshot_download(name)
tok = AutoTokenizer.from_pretrained(name)
model = AutoModelForSeq2SeqLM.from_pretrained(name)
print("HF_SNAPSHOT " + json.dumps({"name": name, "snapshot_sha": Path(path).name,
                                    "n_params": sum(p.numel() for p in model.parameters()),
                                    "tokenizer": type(tok).__name__}))
'''


def hf_snapshot(prereg, deadline, tag):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    probe = SCRATCH / "hf_probe.py"
    if not probe.exists():
        probe.write_text(HF_PROBE, encoding="utf-8")
    logp = WORK / "logs" / f"hf_{tag}.log"
    run_ok([sys.executable, str(probe), prereg["hf_base_model"]["name"]], SCRATCH, logp, deadline)
    line = [ln for ln in logp.read_text(encoding="utf-8").splitlines() if ln.startswith("HF_SNAPSHOT ")][-1]
    return json.loads(line[len("HF_SNAPSHOT "):])


def measure_and_compare(prereg):
    sys.path[:0] = [str(REPO), str(REPO / "scripts")]
    import retrain_preregister as P
    m = P.measure_k2(REPO, REPO / P.CLEAN10K_REL, vocab_file=REPO / P.VOCAB_REL)
    rows = P.compare(prereg, m, P.K2_COMPARE)
    bad = [r for r in rows if not r["ok"]]
    for r in rows:
        log(f"{'MATCH   ' if r['ok'] else 'MISMATCH'} {r['key']}: expected={json.dumps(r['expected'], ensure_ascii=False)[:120]}"
            f" measured={json.dumps(r['measured'], ensure_ascii=False)[:120]}")
    return m, rows, bad


def find_k1_backbone():
    hits = sorted(glob.glob("/kaggle/input/**/stgcn_best.pt", recursive=True))
    return hits[0] if len(hits) == 1 else None


def train(prereg, deadline, env_rec):
    k2 = prereg["jobs"]["k2"]
    date = prereg["date"]
    k1_out = REPO / "reports" / f"retrain_{date}" / "k1_outputs.json"
    if not k1_out.is_file():
        raise KernelError(f"{k1_out.relative_to(REPO)} missing at the pin (commit it after K1, before K2-train)")
    key1, key2 = k2["backbone"]["k1_outputs_key"].split(".")
    expected = json.loads(k1_out.read_text(encoding="utf-8"))[key1][key2]
    (REPO / "checkpoints").mkdir(exist_ok=True)
    env_rec["backbone_sha256"] = place_backbone(find_k1_backbone(), REPO / k2["backbone"]["path"], expected)
    log(f"BACKBONE {k2['backbone']['path']} sha256 {env_rec['backbone_sha256']} == k1_outputs.json")

    import torch
    n_gpu = torch.cuda.device_count()
    env_rec["n_gpu"] = n_gpu
    env_rec["gpus"] = [torch.cuda.get_device_name(i) for i in range(n_gpu)]
    py = sys.executable
    queues = {"0": [("cslr", k2["cslr"])], "1": [("vit5_stage1", k2["vit5_stage1"]), ("vit5_stage2", k2["vit5_stage2"])]}
    if n_gpu < 2:
        queues = {"0": queues["0"] + queues["1"]}
    failed, timings = [], {}

    def worker(gpu, jobs):
        for name, job in jobs:
            t = time.time()
            timings[name] = {"start_utc": utc(), "gpu": gpu}
            try:
                rc = run([py, *job["train"]["argv"]], REPO, WORK / "logs" / f"{name}.log", deadline,
                         env={**os.environ, "CUDA_VISIBLE_DEVICES": gpu, "PYTHONUNBUFFERED": "1"})
            except Watchdog as e:
                rc = f"watchdog: {e}"
            timings[name].update({"end_utc": utc(), "minutes": round((time.time() - t) / 60, 2), "exit": rc})
            if rc != 0:
                failed.append(name)
                return  # stage 2 needs stage 1

    threads = [threading.Thread(target=worker, args=(g, j)) for g, j in queues.items()]
    [t.start() for t in threads]
    [t.join() for t in threads]
    env_rec["jobs"] = timings
    if failed:
        raise KernelError(f"failed jobs: {failed}")

    check_cslr_log((WORK / "logs" / "cslr.log").read_text(encoding="utf-8", errors="replace"))
    check_vit5_log((WORK / "logs" / "vit5_stage1.log").read_text(encoding="utf-8", errors="replace"), "vit5_stage1")
    check_vit5_log((WORK / "logs" / "vit5_stage2.log").read_text(encoding="utf-8", errors="replace"), "vit5_stage2")
    rep = REPO / "reports"
    sanity = {"cslr": sanity_cslr(json.loads((rep / "cslr_training_history.json").read_text(encoding="utf-8")),
                                  json.loads((rep / "cslr_train_summary.json").read_text(encoding="utf-8"))),
              "vit5_stage1": sanity_vit5(json.loads((rep / "vit5_stage1_history.json").read_text(encoding="utf-8")),
                                         need_best_epoch=False),
              "vit5_stage2": sanity_vit5(json.loads((rep / "vit5_stage2_history.json").read_text(encoding="utf-8")),
                                         need_best_epoch=True)}
    write_json_new(WORK / "sanity.json", sanity)
    for f in ("cslr_best.pt", "cslr_stage1_best.pt"):
        copy_new(REPO / "checkpoints" / f, WORK / f)
    copy_tree_new(REPO / "checkpoints" / "vit5_stage1" / "best_model", WORK / "vit5_stage1" / "best_model")
    copy_tree_new(REPO / "checkpoints" / "vit5_stage2" / "best_model", WORK / "vit5_stage2" / "best_model")
    for f in ("cslr_used_ids.json", "cslr_train_summary.json", "cslr_training_history.json", "vit5_stage1_used_ids.json",
              "vit5_stage1_history.json", "vit5_stage2_used_ids.json", "vit5_stage2_history.json"):
        copy_new(rep / f, WORK / "reports" / f)
    if not all(v["ok"] for v in sanity.values()):
        raise KernelError(f"sanity checks (plan 13 §3.6) failed: {sanity} -> CAN NGUOI DUNG, no rerun")


def main():
    t0 = time.time()
    env_rec = {"mode": MODE, "start_utc": utc(), "python": platform.python_version(), "platform": platform.platform()}
    rc = 1
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        if MODE not in MODES:
            raise KernelError(f"MODE {MODE!r} not implemented at this commit (repro_i = plan 13 B14)")
        pin = check_pin(PIN_COMMIT)
        deadline = t0 + 3600  # until the preregistration (with the registered watchdog) is read
        env_rec["commit"] = clone_pinned(pin, deadline)
        prereg_rel, prereg_commit, prereg = load_prereg()
        env_rec.update({"preregistration": prereg_rel, "preregistration_commit": prereg_commit})
        deadline = t0 + 60 * prereg["jobs"]["k2"]["watchdog_minutes"]
        env_rec["watchdog_minutes"] = prereg["jobs"]["k2"]["watchdog_minutes"]
        env_rec["pip"] = pip_pinned(prereg, deadline)
        env_rec["upstream"] = clone_upstreams(prereg, deadline)
        build_data(prereg, deadline)
        env_rec["hf_preflight"] = hf_snapshot(prereg, deadline, "preflight")
        m, rows, bad = measure_and_compare(prereg)
        vocab_rel = prereg["inputs"]["gloss_vocab_canonical_txt"]["path"]
        copy_new(REPO / vocab_rel, WORK / "gloss_vocab_canonical.txt")
        write_json_new(WORK / "preflight.json", {"mode": MODE, "commit": env_rec["commit"], "rows": rows,
                                                 "n_rows": len(rows), "n_mismatch": len(bad),
                                                 "leak_check_total": m["leak_check"]["total"]})
        if bad:
            raise KernelError(f"PREFLIGHT MISMATCH: {len(bad)} of {len(rows)} values differ from the preregistration "
                              "(plan 13 §7.2-2: stop, CAN PLANNER)")
        log(f"PREFLIGHT OK: {len(rows)} values == preregistration")
        log(f"LEAK CHECK OK (k2 kernel): total={m['leak_check']['total']} "
            + " ".join(f"{k}={v['n_violations']}" for k, v in m["leak_check"].items() if isinstance(v, dict)))
        if MODE == "preflight":
            log("TEST DEFERRED (preflight): no training and no evaluation in this mode")
        else:
            train(prereg, deadline, env_rec)
            env_rec["hf_train"] = hf_snapshot(prereg, deadline, "train")
            env_rec["hf_snapshot_same"] = env_rec["hf_train"]["snapshot_sha"] == env_rec["hf_preflight"]["snapshot_sha"]
        rc = 0
    except Exception as e:  # noqa: BLE001 - recorded, then exit != 0
        env_rec["error"] = f"{type(e).__name__}: {e}"
        log(f"K2 FAILED: {env_rec['error']}")
    finally:
        env_rec["end_utc"] = utc()
        env_rec["total_minutes"] = round((time.time() - t0) / 60, 2)
        env_rec["exit"] = rc
        try:
            import torch
            env_rec.update({"torch": torch.__version__, "cuda": torch.version.cuda,
                            "gpus_visible": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]})
        except Exception as e:  # noqa: BLE001
            env_rec["torch"] = f"unavailable: {e}"
        try:
            from importlib.metadata import version
            env_rec["transformers"] = version("transformers")
        except Exception:  # noqa: BLE001
            pass
        write_json_new(WORK / "env.json", env_rec)
        write_sums(WORK)
    return rc


if __name__ == "__main__":
    sys.exit(main())
