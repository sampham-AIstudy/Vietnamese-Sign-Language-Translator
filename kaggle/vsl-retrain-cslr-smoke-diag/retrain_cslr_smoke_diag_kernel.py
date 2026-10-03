"""
Kaggle CPU kernel of plan 13 Lan sua 2, step B9b (docs/plans/13-train-lai-checkpoint-thieu.md §0B.3): diagnosis of the CSLR
smoke test that failed in K2 train v3. Runs on Kaggle CPU (no accelerator) instead of the local CPU of §0B.3 because of the
user decision of 2026-10-03 02:55 (no training on the local machine); every diagnosis and every decision rule of §0B.3 is
unchanged.

Inputs (the same as K2): the repository at PIN_COMMIT (asserted), the VSL-GH upstream at the commit of the preregistration,
the pinned libraries, the VSL-GH canonical data rebuilt with the registered command, the train-only vocab (322) built with
the registered command, the full vocab (372) built with the same script without --sentence-split, and stgcn_best.pt from
the K1 output (kernel source). Every expected digest is READ from the preregistration / k1_outputs.json of the pinned
commit and cross-checked against the prefixes written in §0B.3; any difference -> stop before any run (CAN PLANNER).

Parts (each one a child process with a 30-minute wall clock, device cpu):
  D0  sample ids of Subset(range(8)) train + val[0], with the sentence split and with sentence_split=None (no training)
  D1  src.training.train_cslr.run_smoke_test UNCHANGED (vocab 322, K1 backbone, sentence split v1): stdout + bool
  D4  an instrumented copy of the run_smoke_test loop (same setting as D1): (i) transfer_info of the real
      load_pretrained_spatial_backbone + key analysis, (ii) losses of epochs 1-10 (4 decimals) compared with D1,
      (iii) at epochs 10 and 60: eval-mode CTC loss, total_hyp_words, BatchNorm-only-train total_hyp_words (deepcopy,
      no_grad), blank-frame fraction, WER; (iv) same optimizer / lr / everything up to epoch 60 (D5). Measurements save and
      restore every RNG state, so they never change the training trajectory.
  D2  run_smoke_test with sentence_split=None + vocab 372 (explanation only)
  D3  run_smoke_test with a backbone path that does not exist (explanation only)
Decision (decide(), unit-tested): R0 / R1 / R2-PASS / R2-FAIL exactly as written in §0B.3 before any result.
Output: /kaggle/working/diag/ (smoke_diag.json, env.json, parts/, logs/, SHA256SUMS). No checkpoint is written; nothing
is deleted; no test / val evaluation of any model.
"""
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import time
from pathlib import Path

PIN_COMMIT = None   # full 40-hex commit of the pinned code; set only in the pushed copy (plan 13 §0B.6(a) mechanism)

SLUG = "phmvnsm33/vsl-retrain-cslr-smoke-diag"
REPO_URL = "https://github.com/sampham-AIstudy/Vietnamese-Sign-Language-Translator.git"
BRANCH = "feat/vslt-complete"
KERNEL_FILE_IN_REPO = "kaggle/vsl-retrain-cslr-smoke-diag/retrain_cslr_smoke_diag_kernel.py"
K2_FILE_IN_REPO = "kaggle/vsl-retrain-cslr-vit5/retrain_cslr_vit5_kernel.py"
REPO = Path("/tmp/vslt")
WORK = Path("/kaggle/working/diag")
SCRATCH = Path("/tmp/diag_scratch")
PIN_LINE_RX = re.compile(r"^PIN_COMMIT = .*$", re.M)
PLAN_REF = "docs/plans/13-train-lai-checkpoint-thieu.md §0B.3"

PART_TIMEOUT_S = 30 * 60      # §0B.3: each run 30 minutes wall clock
KERNEL_WATCHDOG_MIN = 200     # setup + 5 parts (< Kaggle CPU session limit)
SMOKE_EPOCHS = 10             # run_smoke_test (unchanged)
DIAG_EPOCHS = 60              # §0B.3 (iv): fixed before the run (120 steps)
MEASURE_EPOCHS = (10, 60)     # §0B.3 (iii)
PARTS = ("D0", "D1", "D4", "D2", "D3")   # decision inputs first; D2/D3 are explanations only
CODE_PATHS = ("src", "scripts", "configs", "train.py", "evaluate_test.py", "kaggle")
# prefixes / suffixes written in §0B.3 (cross-check of the values read from the preregistration and k1_outputs.json)
PLAN_PREFIXES = {
    "dataset_canonical_json": ("d53ab701", None),
    "keypoints_frontal": ("59642925", None),
    "vocab_train_322": ("c0af13db", None),
    "vocab_full_372": ("dd7bc3da", None),
    "k1_stgcn_best_pt": ("2204becd", "bac2"),
}
SMOKE_LOSS_RX = re.compile(r"Smoke Epoch (\d+)/10: Train CTC Loss = (\S+)")


class KernelError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------------------
# pure helpers (unit-tested locally, tests/test_retrain_tools.py)
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
        raise KernelError(f"PIN_COMMIT must be a full 40-hex commit, got {pin!r}")
    return pin


def same_as_pinned(running_text, pinned_text):
    """The running kernel must be the pinned file except for the PIN_COMMIT line."""
    norm = lambda t: PIN_LINE_RX.sub("PIN_COMMIT = <pin>", t.replace("\r\n", "\n"))  # noqa: E731
    if norm(running_text) != norm(pinned_text):
        raise KernelError(f"the running kernel differs from {KERNEL_FILE_IN_REPO} at the pinned commit "
                          "(other than the PIN_COMMIT line)")


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def parse_smoke_losses(text):
    """The 4-decimal strings of 'Smoke Epoch NN/10: Train CTC Loss = X' in epoch order (run_smoke_test stdout)."""
    out = [(int(m.group(1)), m.group(2)) for m in SMOKE_LOSS_RX.finditer(text)]
    if [e for e, _ in out] != list(range(1, len(out) + 1)):
        raise KernelError(f"smoke epochs out of order: {[e for e, _ in out]}")
    return [v for _, v in out]


def fidelity(d1_losses, d4_losses_4dp):
    """§0B.3 D4-ii: losses of epochs 1-10 of the instrumented copy, rounded to 4 decimals, == the 10 printed by D1."""
    a, b = list(d1_losses or []), list(d4_losses_4dp or [])[:SMOKE_EPOCHS]
    mism = [{"epoch": i + 1, "d1": x, "d4": y} for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ok = len(a) == SMOKE_EPOCHS and len(b) == SMOKE_EPOCHS and not mism
    return {"fidelity_ok": ok, "n_d1": len(a), "n_d4": len(b), "mismatches": mism}


def transfer_analysis(ckpt_shapes, model_shapes):
    """Independent re-count of load_pretrained_spatial_backbone (same key rule): shapes are lists of ints."""
    pref = lambda k: k.startswith("data_bn.") or k.startswith("blocks.")  # noqa: E731
    transferred, mismatch, skipped = [], [], []
    for k, s in ckpt_shapes.items():
        if pref(k) and k in model_shapes:
            if list(model_shapes[k]) == list(s):
                transferred.append(k)
            else:
                mismatch.append(f"{k} (shape mismatch: {list(model_shapes[k])} vs {list(s)})")
        else:
            skipped.append(k)
    model_pref = sorted(k for k in model_shapes if pref(k))
    ckpt_pref = sorted(k for k in ckpt_shapes if pref(k))
    both = sorted(set(model_pref) & set(ckpt_pref))
    return {"n_transferred_keys": len(transferred), "n_shape_mismatch_keys": len(mismatch),
            "shape_mismatch_keys": mismatch, "skipped_keys": skipped + mismatch,
            "n_prefix_keys_model": len(model_pref), "n_prefix_keys_ckpt": len(ckpt_pref),
            "n_prefix_keys_in_both": len(both),
            "prefix_keys_only_in_model": sorted(set(model_pref) - set(ckpt_pref)),
            "prefix_keys_only_in_ckpt": sorted(set(ckpt_pref) - set(model_pref))}


def decide(diag):
    """§0B.3 decision rule (written before any result). Inputs: inputs_ok, D1.passed, D4.transfer_info / key analysis
    (D4-i), fidelity (D4-ii), D4 epoch-60 measures (D5). D0/D2/D3/D4-iii are never decision inputs.
    Returns {"decision": R0|R1|R2-PASS|R2-FAIL|None, "stop": None|"CAN_PLANNER"|"CAN_NGUOI_DUNG", "reasons": [...]}"""
    def out(decision, stop, *reasons):
        return {"decision": decision, "stop": stop, "reasons": list(reasons)}

    if not diag.get("inputs_ok"):
        return out(None, "CAN_PLANNER", "input sha256 differs from the preregistration / §0B.3 (§7.2-9)")
    d1 = diag.get("D1") or {}
    if not isinstance(d1.get("passed"), bool):
        return out(None, "CAN_PLANNER", f"D1 did not complete (status {d1.get('status')!r}); no rule of §0B.3 applies")
    d4 = diag.get("D4") or {}
    ti, ka = d4.get("transfer_info"), d4.get("key_analysis")
    if not isinstance(ti, dict) or not isinstance(ka, dict):
        return out(None, "CAN_PLANNER", f"D4-i missing (status {d4.get('status')!r})")
    r0 = []
    if ka.get("n_shape_mismatch_keys", 0) > 0:
        r0.append(f"{ka['n_shape_mismatch_keys']} key(s) with shape mismatch")
    if ti.get("transferred_params") == 0:
        r0.append("transferred_params == 0")
    if ti.get("transferred_keys_count") != ka.get("n_prefix_keys_in_both"):
        r0.append(f"transferred_keys_count {ti.get('transferred_keys_count')} != data_bn.*/blocks.* keys in both "
                  f"models {ka.get('n_prefix_keys_in_both')}")
    if r0:
        return out("R0", "CAN_PLANNER", *r0)
    fid = diag.get("fidelity") or {}
    if fid.get("fidelity_ok") is not True:
        return out(None, "CAN_PLANNER", f"D4-ii fidelity check false ({fid}): D4/D5 invalid")
    if d1["passed"]:
        return out("R1", None, "D1 (original smoke test) PASS on CPU")
    m60 = (d4.get("measures") or {}).get(str(DIAG_EPOCHS))
    losses = d4.get("train_losses") or []
    if not isinstance(m60, dict) or len(losses) < DIAG_EPOCHS:
        return out("R2-FAIL", "CAN_NGUOI_DUNG", f"D1 FAIL and D5 did not reach epoch {DIAG_EPOCHS} "
                                                f"(epochs done {len(losses)}, status {d4.get('status')!r})")
    ev = m60.get("eval") or {}
    fails = []
    if not (all(finite(x) for x in losses[:DIAG_EPOCHS]) and finite(ev.get("loss"))):
        fails.append("non-finite loss")
    if not (finite(losses[DIAG_EPOCHS - 1]) and finite(losses[0]) and losses[DIAG_EPOCHS - 1] < losses[0]):
        fails.append(f"loss epoch {DIAG_EPOCHS} {losses[DIAG_EPOCHS - 1]} not < loss epoch 1 {losses[0]}")
    if not (isinstance(ev.get("total_hyp_words"), int) and ev["total_hyp_words"] > 0):
        fails.append(f"eval total_hyp_words {ev.get('total_hyp_words')} not > 0")
    if not (finite(ev.get("wer")) and ev["wer"] < 100):
        fails.append(f"WER 8 samples {ev.get('wer')} not < 100")
    if fails:
        return out("R2-FAIL", "CAN_NGUOI_DUNG", "D1 FAIL on CPU", *fails)
    return out("R2-PASS", None, "D1 FAIL on CPU", f"D5 epoch {DIAG_EPOCHS}: losses finite, loss decreased, "
                                                    f"total_hyp_words {ev['total_hyp_words']} > 0, WER {ev['wer']} < 100")


# ---------------------------------------------------------------------------------------------------------------------
# parts (child processes; torch imported only here)
# ---------------------------------------------------------------------------------------------------------------------
class _Tee(io.StringIO):
    def __init__(self, stream):
        super().__init__()
        self._stream = stream

    def write(self, s):
        self._stream.write(s)
        self._stream.flush()
        return super().write(s)


def _import_train_cslr(repo):
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from src.training import train_cslr as T
    return T


def part_d0(cfg, T):
    v322 = T.VSLGlossVocabulary.from_file(cfg["vocab_322"])
    v372 = T.VSLGlossVocabulary.from_file(cfg["vocab_372"])
    root = Path(cfg["data_root"])
    res = {}
    for label, split, vocab in (("sentence_split_v1", cfg["split_path"], v322), ("sentence_split_none", None, v372)):
        ds = {s: T.VSLGHContinuousDataset(canonical_json=root / "dataset_canonical.json",
                                          keypoints_dir=root / "keypoints_frontal", split=s, vocabulary=vocab,
                                          conversion_mode="semantic", normalize=True, sentence_split=split)
              for s in ("train", "val")}
        res[label] = {"train_subset_range8": [ds["train"].samples[i]["id"] for i in range(8)],
                      "val_index0": ds["val"].samples[0]["id"],
                      "n_train": len(ds["train"]), "n_val": len(ds["val"])}
    a, b = res["sentence_split_v1"], res["sentence_split_none"]
    res["identical_train8"] = a["train_subset_range8"] == b["train_subset_range8"]
    res["identical_val0"] = a["val_index0"] == b["val_index0"]
    res["identical"] = res["identical_train8"] and res["identical_val0"]
    return res


def part_smoke(cfg, T, vocab_key, split, backbone):
    import torch
    tee = _Tee(sys.stdout)
    t = time.time()
    with contextlib.redirect_stdout(tee):
        passed = T.run_smoke_test(Path(cfg["data_root"]), Path(cfg[vocab_key]), Path(backbone), torch.device("cpu"),
                                  sentence_split=split)
    text = tee.getvalue()
    return {"args": {"data_root": cfg["data_root"], "vocab_path": cfg[vocab_key], "checkpoint_path": str(backbone),
                     "checkpoint_exists": Path(backbone).is_file(), "device": "cpu", "sentence_split": split},
            "passed": bool(passed), "stdout": text, "smoke_losses": parse_smoke_losses(text),
            "seconds": round(time.time() - t, 2)}


def _decode_pass(T, model, loader, ctc_loss_fn, vocab, device):
    import torch
    tot, n, hyps, refs, blank, frames, ids = 0.0, 0, [], [], 0, 0, []
    with torch.no_grad():
        for batch in loader:
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            gloss_targets = batch["gloss_targets"].to(device)
            gloss_lengths = batch["gloss_lengths"].to(device)
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lengths = model(features, joint_masks=joint_masks, sequence_lengths=lengths)
                loss = ctc_loss_fn(log_probs, gloss_targets, out_lengths, gloss_lengths)
            tot += float(loss.item()) * len(lengths)
            n += len(lengths)
            hyps.extend(T.ctc_greedy_decode(log_probs, sequence_lengths=out_lengths, blank_id=vocab.blank_id))
            ptr = 0
            for g in gloss_lengths.tolist():
                refs.append(gloss_targets[ptr:ptr + g].cpu().tolist())
                ptr += g
            am = log_probs.argmax(dim=-1)  # [T_out, B] (model output is [T_out, B, C])
            for i, L in enumerate(out_lengths.tolist()):
                blank += int((am[:L, i] == vocab.blank_id).sum().item())
                frames += int(L)
            ids.extend(batch["sample_ids"])
    w = T.compute_wer(hyps, refs)
    return {"loss": tot / n if n else None, "total_hyp_words": int(w["total_hyp_words"]), "wer": w["wer"],
            "total_ref_words": int(w["total_ref_words"]), "substitutions": w["substitutions"],
            "deletions": w["deletions"], "insertions": w["insertions"], "blank_frame_fraction": blank / frames if frames else None,
            "n_frames": frames, "hyp_lengths": [len(h) for h in hyps], "sample_ids": ids}


def _measure(T, model, train_loader, fixed_loader, ctc_loss_fn, vocab, device):
    """§0B.3 (iii). Every RNG state is saved and restored: the training trajectory is the same as without measuring."""
    import numpy as np
    import torch
    state = (torch.get_rng_state(), random.getstate(), np.random.get_state())
    try:
        ev = T.evaluate_cslr(model, train_loader, ctc_loss_fn, vocab, device, max_examples=8)  # same call as D1
        model.eval()
        ev_fixed = _decode_pass(T, model, fixed_loader, ctc_loss_fn, vocab, device)
        m2 = copy.deepcopy(model)
        m2.eval()
        bn = [m for m in m2.modules() if isinstance(m, torch.nn.modules.batchnorm._BatchNorm)]
        for m in bn:
            m.train()
        bn_train = _decode_pass(T, m2, fixed_loader, ctc_loss_fn, vocab, device)
        del m2
    finally:
        torch.set_rng_state(state[0])
        random.setstate(state[1])
        np.random.set_state(state[2])
        model.train()
    return {"eval": {k: ev[k] for k in ("loss", "total_samples", "wer", "substitutions", "deletions", "insertions",
                                        "total_ref_words", "total_hyp_words", "qualitative_examples")},
            "eval_fixed_order": ev_fixed, "bn_train_only": {**bn_train, "n_batchnorm_modules": len(bn)}}


def instrumented_smoke(T, cfg, epochs=DIAG_EPOCHS, measure_at=MEASURE_EPOCHS, on_record=None):
    """Copy of the run_smoke_test loop (src/training/train_cslr.py), D1 setting, extended with measurements and epochs.
    Lines kept in the same order so that the RNG stream is identical up to epoch 10."""
    import torch
    import torch.nn as nn
    rec = {"status": "running", "train_losses": [], "train_losses_4dp": [], "epochs": [], "measures": {}}
    emit = on_record or (lambda kind, obj: None)
    data_root, vocab_path = Path(cfg["data_root"]), Path(cfg["vocab_322"])
    checkpoint_path, device, sentence_split = Path(cfg["backbone"]), torch.device("cpu"), cfg["split_path"]

    T.set_seed(42)
    vocab = T.VSLGlossVocabulary.from_file(str(vocab_path))
    full_train = T.VSLGHContinuousDataset(canonical_json=data_root / "dataset_canonical.json",
                                          keypoints_dir=data_root / "keypoints_frontal", split="train",
                                          vocabulary=vocab, conversion_mode="semantic", normalize=True,
                                          sentence_split=sentence_split)
    val_dataset = T.VSLGHContinuousDataset(canonical_json=data_root / "dataset_canonical.json",
                                           keypoints_dir=data_root / "keypoints_frontal", split="val",
                                           vocabulary=vocab, conversion_mode="semantic", normalize=True,
                                           sentence_split=sentence_split)
    smoke_train_subset = T.Subset(full_train, indices=list(range(8)))
    smoke_val_subset = T.Subset(val_dataset, indices=[0])
    train_loader = T.DataLoader(smoke_train_subset, batch_size=4, shuffle=True, collate_fn=T.vslgh_collate_fn)
    val_loader = T.DataLoader(smoke_val_subset, batch_size=1, shuffle=False, collate_fn=T.vslgh_collate_fn)  # noqa: F841
    fixed_loader = T.DataLoader(smoke_train_subset, batch_size=4, shuffle=False, collate_fn=T.vslgh_collate_fn)
    model = T.STGCNBiGRU_CSLR(num_joints=67, in_channels=3, num_classes=len(vocab), channel_dims=[64, 64, 128],
                              temporal_downsample=2, hidden_size=256, num_gru_layers=2, dropout=0.1).to(device)
    rec["transfer_info"] = None
    if checkpoint_path.is_file():
        rec["transfer_info"] = model.load_pretrained_spatial_backbone(str(checkpoint_path), freeze=False)
        ck = torch.load(str(checkpoint_path), map_location="cpu")  # same call as the function (no RNG use)
        sd = ck.get("model_state_dict", ck)
        rec["key_analysis"] = transfer_analysis({k: list(v.shape) for k, v in sd.items()},
                                                {k: list(v.shape) for k, v in model.state_dict().items()})
    rec["n_vocab"] = len(vocab)
    emit("transfer", {"transfer_info": rec["transfer_info"], "key_analysis": rec.get("key_analysis")})
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))
    ctc_loss_fn = nn.CTCLoss(blank=vocab.blank_id, zero_infinity=True, reduction="mean")

    for epoch in range(1, epochs + 1):
        t = time.time()
        model.train()
        epoch_loss = 0.0
        batch_ids = []
        for batch in train_loader:
            features = batch["features"].to(device)
            joint_masks = batch["joint_masks"].to(device)
            lengths = batch["lengths"].to(device)
            gloss_targets = batch["gloss_targets"].to(device)
            gloss_lengths = batch["gloss_lengths"].to(device)

            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                log_probs, out_lengths = model(features, joint_masks=joint_masks, sequence_lengths=lengths)
                loss = ctc_loss_fn(log_probs, gloss_targets, out_lengths, gloss_lengths)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()

            epoch_loss += loss.item() * len(lengths)
            batch_ids.append(list(batch["sample_ids"]))

        epoch_loss /= len(smoke_train_subset)
        rec["train_losses"].append(epoch_loss)
        rec["train_losses_4dp"].append(f"{epoch_loss:.4f}")
        e = {"epoch": epoch, "train_loss": epoch_loss, "train_loss_4dp": f"{epoch_loss:.4f}", "batch_ids": batch_ids,
             "seconds": round(time.time() - t, 2)}
        rec["epochs"].append(e)
        emit("epoch", e)
        if epoch in measure_at:
            m = _measure(T, model, train_loader, fixed_loader, ctc_loss_fn, vocab, device)
            rec["measures"][str(epoch)] = m
            emit("measure", {"epoch": epoch, **m})
    rec["status"] = "complete"
    return rec


def part_main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=PARTS)
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.cfg).read_text(encoding="utf-8"))
    T = _import_train_cslr(cfg["repo"])
    import torch
    t0 = time.time()
    if a.part == "D0":
        res = part_d0(cfg, T)
    elif a.part == "D1":
        res = part_smoke(cfg, T, "vocab_322", cfg["split_path"], cfg["backbone"])
    elif a.part == "D2":
        res = part_smoke(cfg, T, "vocab_372", None, cfg["backbone"])
    elif a.part == "D3":
        if Path(cfg["missing_backbone"]).exists():
            raise KernelError("D3 backbone path exists")
        res = part_smoke(cfg, T, "vocab_322", cfg["split_path"], cfg["missing_backbone"])
    else:
        progress = Path(a.out).with_name("D4_progress.jsonl")

        def emit(kind, obj):
            with open(progress, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({"kind": kind, **obj}, ensure_ascii=False) + "\n")
        res = instrumented_smoke(T, cfg, on_record=emit)
    res.update({"part": a.part, "torch": torch.__version__, "torch_num_threads": torch.get_num_threads(),
                "part_seconds": round(time.time() - t0, 2)})
    with open(a.out, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    return 0


def d4_from_progress(path):
    """D4 record rebuilt from the append-only progress file (used when the D4 child timed out)."""
    rec = {"status": "partial", "train_losses": [], "train_losses_4dp": [], "epochs": [], "measures": {}}
    if not Path(path).is_file():
        return rec
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        o = json.loads(ln)
        kind = o.pop("kind")
        if kind == "transfer":
            rec.update(o)
        elif kind == "epoch":
            rec["epochs"].append(o)
            rec["train_losses"].append(o["train_loss"])
            rec["train_losses_4dp"].append(o["train_loss_4dp"])
        elif kind == "measure":
            rec["measures"][str(o.pop("epoch"))] = o
    return rec


# ---------------------------------------------------------------------------------------------------------------------
# kernel
# ---------------------------------------------------------------------------------------------------------------------
def _git(*args, cwd=REPO):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise KernelError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _load_k2():
    spec = importlib.util.spec_from_file_location("k2_kernel_at_pin", REPO / K2_FILE_IN_REPO)
    k2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(k2)  # module level only defines constants / functions
    k2.WORK = WORK  # its run / run_ok / clone_upstreams / pip_pinned write their logs under WORK/logs
    return k2


def _check_input(name, measured, expected, extra=None):
    pre, suf = PLAN_PREFIXES[name]
    ok_prereg = isinstance(expected, str) and measured == expected
    ok_plan = isinstance(measured, str) and measured.startswith(pre) and (suf is None or measured.endswith(suf))
    return {"name": name, "measured": measured, "expected": expected, "plan_prefix": pre, "plan_suffix": suf,
            "ok": bool(ok_prereg and ok_plan), **(extra or {})}


def check_inputs(prereg, k1_outputs, paths):
    sys.path[:0] = [str(REPO), str(REPO / "scripts")]
    import retrain_digest as D
    from src.data.sentence_split import split_file_sha256
    inp = prereg["inputs"]
    digest, n = D.dir_digest(str(paths["keypoints"]), pattern=inp["keypoints_frontal"]["pattern"])
    key1, key2 = prereg["jobs"]["k2"]["backbone"]["k1_outputs_key"].split(".")
    v322 = Path(paths["vocab_322"]).read_bytes()
    v372 = Path(paths["vocab_372"]).read_bytes()
    rows = [
        _check_input("dataset_canonical_json", D.lf_sha256(str(paths["canonical"])),
                     inp["dataset_canonical_json"]["lf_sha256"], {"rule": "lf_sha256", "path": str(paths["canonical"])}),
        _check_input("keypoints_frontal", digest, inp["keypoints_frontal"]["dir_digest"],
                     {"rule": "dir_digest", "n_files": n, "n_files_expected": inp["keypoints_frontal"]["n_files"],
                      "path": str(paths["keypoints"])}),
        _check_input("vocab_train_322", hashlib.sha256(v322).hexdigest(), prereg["vocab"]["sha256"],
                     {"rule": "sha256", "n_tokens": len(v322.decode("utf-8").splitlines()),
                      "n_tokens_expected": prereg["vocab"]["n_tokens"], "path": str(paths["vocab_322"])}),
        _check_input("vocab_full_372", hashlib.sha256(v372).hexdigest(), prereg["vocab_full_reference"]["sha256"],
                     {"rule": "sha256", "n_tokens": len(v372.decode("utf-8").splitlines()),
                      "n_tokens_expected": prereg["vocab_full_reference"]["n_tokens"], "path": str(paths["vocab_372"])}),
        _check_input("k1_stgcn_best_pt", sha256_file(paths["backbone"]), k1_outputs[key1][key2],
                     {"rule": "sha256", "path": str(paths["backbone"])}),
    ]
    rows[1]["ok"] = rows[1]["ok"] and rows[1]["n_files"] == rows[1]["n_files_expected"]
    rows[2]["ok"] = rows[2]["ok"] and rows[2]["n_tokens"] == rows[2]["n_tokens_expected"]
    rows[3]["ok"] = rows[3]["ok"] and rows[3]["n_tokens"] == rows[3]["n_tokens_expected"]
    s = split_file_sha256(Path(paths["split"]).read_bytes())
    rows.append({"name": "sentence_split_v1", "measured": s, "expected": prereg["sentence_split"]["sha256"],
                 "rule": "split_file_sha256 (LF)", "path": str(paths["split"]),
                 "ok": s == prereg["sentence_split"]["sha256"]})
    return rows


def run_part(k2, part, cfg_path, deadline):
    out = WORK / "parts" / f"{part}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    part_deadline = min(t + PART_TIMEOUT_S, deadline)
    argv = [sys.executable, str(REPO / KERNEL_FILE_IN_REPO), "--part", part, "--cfg", str(cfg_path), "--out", str(out)]
    try:
        rc = k2.run(argv, REPO, WORK / "logs" / f"{part}.log", part_deadline,
                    env={**os.environ, "PYTHONUNBUFFERED": "1", "CUDA_VISIBLE_DEVICES": ""})
        status = "complete" if rc == 0 and out.is_file() else f"exit {rc}"
    except k2.Watchdog as e:
        status = f"timeout: {e}"
    minutes = round((time.time() - t) / 60, 2)
    res = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    res.update({"status": status, "wall_minutes": minutes, "timeout_minutes": PART_TIMEOUT_S / 60})
    log(f"PART {part}: {status} ({minutes} min)")
    return res


def main():
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    env = {"slug": SLUG, "start_utc": utc(), "python": platform.python_version(), "platform": platform.platform(),
           "accelerator": "none (CPU)"}
    diag = {"plan_ref": PLAN_REF, "inputs_ok": False,
            "location": "Kaggle CPU kernel (user decision 2026-10-03 02:55: no training on the local machine); "
                        "§0B.3 local CPU otherwise unchanged",
            "constants": {"part_timeout_minutes": PART_TIMEOUT_S / 60, "smoke_epochs": SMOKE_EPOCHS,
                          "diag_epochs": DIAG_EPOCHS, "measure_epochs": list(MEASURE_EPOCHS), "parts_order": list(PARTS)}}
    rc = 1
    try:
        pin = check_pin(PIN_COMMIT)
        deadline = t0 + 60 * KERNEL_WATCHDOG_MIN
        (WORK / "logs").mkdir(parents=True, exist_ok=True)
        with open(WORK / "logs" / "clone.log", "a", encoding="utf-8") as lf:
            for argv in (["git", "clone", "-q", "-b", BRANCH, REPO_URL, str(REPO)],
                         ["git", "-C", str(REPO), "checkout", "-q", pin]):
                subprocess.run(argv, check=True, stdout=lf, stderr=subprocess.STDOUT, timeout=1200)
        head = _git("rev-parse", "HEAD")
        if head != pin:
            raise KernelError(f"HEAD {head} != PIN_COMMIT {pin}")
        log(f"PINNED COMMIT {head}")
        same_as_pinned(Path(__file__).read_text(encoding="utf-8"),
                       (REPO / KERNEL_FILE_IN_REPO).read_text(encoding="utf-8"))
        env["commit"] = head
        k2 = _load_k2()
        prereg_rel, prereg_commit, prereg = k2.load_prereg()
        env.update({"preregistration": prereg_rel, "preregistration_commit": prereg_commit})
        env["pip"] = k2.pip_pinned(prereg, deadline)
        env["upstream"] = k2.clone_upstreams({"upstream_sources": {"vsl_gh": prereg["upstream_sources"]["vsl_gh"]}},
                                             deadline)
        prep = prereg["jobs"]["k2"]["data_prep"]
        py = sys.executable
        k2.run_ok([py, *prep["vsl_gh"]["argv"]], REPO, WORK / "logs" / "prepare_vsl_gh.log", deadline)
        k2.run_ok([py, *prep["vocab"]["argv"]], REPO, WORK / "logs" / "vocab.log", deadline)
        va = list(prep["vocab"]["argv"])
        i = va.index("--sentence-split")
        full_argv = va[:i] + va[i + 4:]  # registered argv without "--sentence-split <file> --split train"
        if va[i + 2] != "--split" or "--sentence-split" in full_argv or "--split" in full_argv:
            raise KernelError(f"unexpected registered vocab argv {va}")
        vocab372 = SCRATCH / "vocab_full" / "gloss_vocab_canonical.txt"
        full_argv[full_argv.index("--out") + 1] = str(vocab372)
        k2.run_ok([py, *full_argv], REPO, WORK / "logs" / "vocab_full.log", deadline)
        env["vocab_full_argv"] = full_argv

        k1_out = json.loads((REPO / "reports" / f"retrain_{prereg['date']}" / "k1_outputs.json").read_text(encoding="utf-8"))
        backbone = k2.find_k1_backbone()
        if backbone is None:
            raise KernelError("stgcn_best.pt of K1 not found (exactly one expected under /kaggle/input)")
        data_root = REPO / Path(prereg["inputs"]["dataset_canonical_json"]["path"]).parent
        paths = {"canonical": REPO / prereg["inputs"]["dataset_canonical_json"]["path"],
                 "keypoints": REPO / prereg["inputs"]["keypoints_frontal"]["path"],
                 "vocab_322": REPO / prereg["vocab"]["path"], "vocab_372": vocab372, "backbone": Path(backbone),
                 "split": REPO / prereg["sentence_split"]["path"]}
        rows = check_inputs(prereg, k1_out, paths)
        diag["inputs"] = rows
        diag["inputs_ok"] = all(r["ok"] for r in rows)
        for r in rows:
            log(f"{'MATCH   ' if r['ok'] else 'MISMATCH'} input {r['name']}: {r['measured']}")
        if not diag["inputs_ok"]:
            raise KernelError("input sha256 mismatch (plan 13 §7.2-9: stop, CAN PLANNER)")

        missing = SCRATCH / "no_backbone" / "stgcn_best.pt"
        cfg = {"repo": str(REPO), "data_root": str(data_root), "vocab_322": str(paths["vocab_322"]),
               "vocab_372": str(vocab372), "backbone": str(backbone), "split_path": prereg["sentence_split"]["path"],
               "missing_backbone": str(missing)}
        cfg_path = SCRATCH / "cfg.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "x", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1)
        diag["cfg"] = cfg
        dirty = _git("status", "--porcelain", "--", *CODE_PATHS)
        import torch
        diag["generated_by"] = {
            "command": f"Kaggle kernel {SLUG} (pushed copy of {KERNEL_FILE_IN_REPO} at the pin, PIN_COMMIT line only); "
                       f"parts: python {KERNEL_FILE_IN_REPO} --part <P> --cfg <cfg.json> --out parts/<P>.json",
            "git_commit": head, "code_dirty": bool(dirty.strip()), "code_dirty_files": dirty.splitlines(),
            "torch": torch.__version__, "torch_num_threads": torch.get_num_threads(), "python": platform.python_version(),
            "device": "cpu", "cuda_available": torch.cuda.is_available()}

        for part in PARTS:
            diag[part] = run_part(k2, part, cfg_path, deadline)
            if part == "D1":
                log(diag["D1"].get("stdout", "")[-3000:])
        if diag["D4"]["status"] != "complete":
            partial = d4_from_progress(WORK / "parts" / "D4_progress.jsonl")
            diag["D4"] = {**partial, "status": diag["D4"]["status"], "wall_minutes": diag["D4"]["wall_minutes"]}
        diag["fidelity"] = fidelity(diag["D1"].get("smoke_losses"), diag["D4"].get("train_losses_4dp"))
        ev10 = (diag["D4"].get("measures") or {}).get(str(SMOKE_EPOCHS), {}).get("eval", {})
        d1_dec = re.search(r"Smoke Test Decoded Samples: (.*)", diag["D1"].get("stdout", ""))
        diag["d4_epoch10_reproduces_d1_decoded_samples"] = (
            d1_dec is not None and d1_dec.group(1) == str(ev10.get("qualitative_examples", [])[:2]))
        rc = 0
    except Exception as e:  # noqa: BLE001 - recorded, then exit != 0
        env["error"] = f"{type(e).__name__}: {e}"
        log(f"DIAG FAILED: {env['error']}")
    finally:
        diag["decision_rule"] = decide(diag)
        diag["decision"] = diag["decision_rule"]["decision"]
        log(f"DECISION {json.dumps(diag['decision_rule'], ensure_ascii=False)}")
        env.update({"end_utc": utc(), "total_minutes": round((time.time() - t0) / 60, 2), "exit": rc})
        for path, obj in ((WORK / "smoke_diag.json", diag), (WORK / "env.json", env)):
            with open(path, "x", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
        lines = [f"{sha256_file(p)}  {p.relative_to(WORK).as_posix()}\n" for p in sorted(WORK.rglob("*"))
                 if p.is_file() and p.name != "SHA256SUMS"]
        with open(WORK / "SHA256SUMS", "x", encoding="utf-8", newline="\n") as f:
            f.write("".join(lines))
    return rc


if __name__ == "__main__":
    if "--part" in sys.argv:
        sys.exit(part_main(sys.argv[1:]))
    sys.exit(main())
