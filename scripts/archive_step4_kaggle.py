"""
Archive the step-4 checkpoints and TEST logits in ONE private Kaggle dataset (docs/plans/02-don-dep-sau-4c.md, §3.2).

Three sub-commands, run in this order:
  python scripts/archive_step4_kaggle.py stage  --results reports/step4_2026-09-26/step4_results.json \
         --staging ../_kaggle_staging/vslt-step4-artifacts --dataset phmvnsm33/vslt-step4-artifacts
  python scripts/archive_step4_kaggle.py upload --staging ../_kaggle_staging/vslt-step4-artifacts \
         --dataset phmvnsm33/vslt-step4-artifacts
  python scripts/archive_step4_kaggle.py verify --staging ../_kaggle_staging/vslt-step4-artifacts \
         --dataset phmvnsm33/vslt-step4-artifacts --download-dir ../_kaggle_staging/verify_download \
         --manifest-out reports/step4_2026-09-26/archive/kaggle_archive_manifest.json \
         [--results reports/step4_2026-09-26/step4_results.json]

The file list comes from provenance.runs of step4_results.json (never typed by hand): for each run
<dir>/stgcn_unified_best.pt (kind "checkpoint") and <dir>/test_logits.npz (kind "test_logits"); each source file must
hash to the sha256 recorded in the results JSON. The dataset is created exactly once, always private (the privacy flag
passed to the Kaggle API is a constant in this file), and never updated, versioned or deleted by this script.

Exit codes: 0 ok; 2 missing input / bad argument / temporary path inside the repo / metadata without isPrivate: true;
3 sha256, file set or size mismatch; 4 the dataset could NOT be verified as private (STOP); 5 the slug already exists
(nothing is created); 6 Kaggle not ready before the timeout / API or network error (can be retried).
When the exit code is not 0, `verify` writes no manifest and `stage` leaves no staging directory behind.

The Kaggle client is imported only in main() for real runs; the functions below take an `api` object so the tests use a
fake API (no network, no credentials). No credential is read, printed or written here.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUMS = "SHA256SUMS"
META = "dataset-metadata.json"
TITLE = "VSLT step 4 checkpoints and test logits"
LICENSE = "unknown"
DESCRIPTION = ("Private archive of the VSLT project (Vietnamese Sign Language Translator): checkpoints and TEST logits "
               "of the step-4 runs (file list and sha256 in SHA256SUMS). Trained on QIPEDC + VSL-GH; the licence of the "
               "source data is unknown. Internal use only, do not redistribute.")
KINDS = (("checkpoint", "stgcn_unified_best.pt", "sha256_ckpt"),
         ("test_logits", "test_logits.npz", "sha256_test_logits"))
POLL_S = 60
TIMEOUT_S = 3600


class ArchiveError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inside(path, root=ROOT):
    """True when `path` is `root` or below it (different drives -> False)."""
    a, r = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath([a, r]) == r
    except ValueError:
        return False


def require_outside_repo(path, what):
    if inside(path):
        raise ArchiveError(2, f"{what} phải nằm NGOÀI repo: {path}")


def flat_name(run_dir, filename):
    """Deterministic flat archive name: run dir (repo-relative) without 'reports/', '/' -> '__', then '__<file>'."""
    d = run_dir.replace("\\", "/").strip("/")
    if os.path.isabs(run_dir) or ":" in d or d.startswith("..") or "/../" in f"/{d}/":
        raise ArchiveError(2, f"dir của run phải là đường dẫn tương đối trong repo: {run_dir}")
    if d.startswith("reports/"):
        d = d[len("reports/"):]
    return d.replace("/", "__") + "__" + filename


def plan_files(results_path, src_root=ROOT):
    """[{run, run_dir, kind, local_path, source, archive_name, expected_sha256}] from provenance.runs (sorted)."""
    if not os.path.isfile(results_path):
        raise ArchiveError(2, f"thiếu file results: {results_path}")
    with open(results_path, encoding="utf-8") as f:
        res = json.load(f)
    runs = ((res.get("provenance") or {}).get("runs")) or {}
    if not runs:
        raise ArchiveError(2, f"{results_path}: không có provenance.runs")
    out = []
    for run, r in runs.items():
        for kind, fname, key in KINDS:
            if not r.get("dir") or not r.get(key):
                raise ArchiveError(2, f"{run}: thiếu dir hoặc {key} trong results")
            local = r["dir"].replace("\\", "/").rstrip("/") + "/" + fname
            out.append({"run": run, "run_dir": r["dir"], "kind": kind, "local_path": local,
                        "source": os.path.join(src_root, *local.split("/")),
                        "archive_name": flat_name(r["dir"], fname), "expected_sha256": r[key]})
    names = [f["archive_name"] for f in out]
    if len(set(names)) != len(names):
        raise ArchiveError(2, f"tên phẳng trùng nhau: {sorted(n for n in names if names.count(n) > 1)}")
    return sorted(out, key=lambda f: f["archive_name"])


def sums_text(entries):
    """sha256sum format: '<hex>  <name>' per line, sorted by name."""
    return "".join(f"{h}  {n}\n" for n, h in sorted(entries.items()))


def parse_sums(path):
    if not os.path.isfile(path):
        raise ArchiveError(2, f"thiếu {SUMS}: {path}")
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f.read().splitlines():
            if not line.strip():
                continue
            h, sep, n = line.partition("  ")
            if not sep or len(h) != 64 or not n or n in out:
                raise ArchiveError(3, f"{SUMS}: dòng không hợp lệ: {line!r}")
            out[n] = h
    if not out:
        raise ArchiveError(3, f"{SUMS} rỗng")
    return out


def metadata(dataset):
    return {"title": TITLE, "id": dataset, "licenses": [{"name": LICENSE}], "isPrivate": True,
            "description": DESCRIPTION}


def check_dataset_ref(dataset):
    parts = dataset.split("/")
    if len(parts) != 2 or not all(parts) or not (6 <= len(parts[1]) <= 50):
        raise ArchiveError(2, f"--dataset phải có dạng owner/slug (slug 6-50 ký tự): {dataset}")
    return parts


def read_metadata(staging, dataset):
    p = os.path.join(staging, META)
    if not os.path.isfile(p):
        raise ArchiveError(2, f"thiếu {META} trong staging")
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    if m.get("isPrivate") is not True:
        raise ArchiveError(2, f"{META}: isPrivate phải là true (bool), nhận {m.get('isPrivate')!r}")
    if m.get("id") != dataset:
        raise ArchiveError(2, f"{META}: id {m.get('id')!r} khác --dataset {dataset!r}")
    return m


def check_staging(staging):
    """Re-hash the staging directory against SHA256SUMS; the data file set must equal the SHA256SUMS set exactly."""
    if not os.path.isdir(staging):
        raise ArchiveError(2, f"không có thư mục staging: {staging}")
    sums = parse_sums(os.path.join(staging, SUMS))
    present = {n for n in os.listdir(staging) if n not in (SUMS, META)}
    if present != set(sums):
        raise ArchiveError(3, f"tập file staging khác {SUMS}: thừa {sorted(present - set(sums))}, "
                              f"thiếu {sorted(set(sums) - present)}")
    for n, h in sorted(sums.items()):
        p = os.path.join(staging, n)
        if not os.path.isfile(p) or sha256_file(p) != h:
            raise ArchiveError(3, f"sha256 của {n} trong staging khác {SUMS}")
    return sums


def is_not_found(exc):
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) == 404


def git_head():
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip() if r.returncode == 0 else None


def pkg_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------------
# stage
# ---------------------------------------------------------------------------------------------------------------
def stage(results_path, staging, dataset, src_root=ROOT):
    check_dataset_ref(dataset)
    require_outside_repo(staging, "--staging")
    if os.path.exists(staging):
        raise ArchiveError(2, f"staging đã tồn tại (không ghi đè): {staging}")
    files = plan_files(results_path, src_root)
    for f in files:
        if not os.path.isfile(f["source"]):
            raise ArchiveError(2, f"thiếu file nguồn: {f['local_path']} ({f['run']})")
    for f in files:
        if sha256_file(f["source"]) != f["expected_sha256"]:
            raise ArchiveError(3, f"sha256 của {f['local_path']} khác giá trị trong results ({f['run']}, {f['kind']})")
    parent = os.path.dirname(os.path.abspath(staging))
    os.makedirs(parent, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=os.path.basename(os.path.abspath(staging)) + ".partial-", dir=parent)
    try:
        entries = {}
        for f in files:
            dst = os.path.join(tmp, f["archive_name"])
            shutil.copy2(f["source"], dst)
            h = sha256_file(dst)
            if h != f["expected_sha256"]:
                raise ArchiveError(3, f"bản sao {f['archive_name']} có sha256 khác nguồn")
            entries[f["archive_name"]] = h
        with open(os.path.join(tmp, SUMS), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(sums_text(entries))
        with open(os.path.join(tmp, META), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(metadata(dataset), ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, staging)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    total = sum(os.path.getsize(os.path.join(staging, n)) for n in os.listdir(staging))
    print(f"staged {len(files)} files + {SUMS} + {META} in {staging} ({total} bytes)")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# upload (exactly one create call, always private)
# ---------------------------------------------------------------------------------------------------------------
def upload(staging, dataset, api):
    check_dataset_ref(dataset)
    require_outside_repo(staging, "--staging")
    check_staging(staging)                       # (1) sha256 + exact file set -> 3
    read_metadata(staging, dataset)              # (2) isPrivate is True, id == dataset -> 2
    try:                                         # (3) the slug must not exist yet -> 5
        st = api.dataset_status(dataset)
    except Exception as e:  # noqa: BLE001 - HTTP 404 means "does not exist"; anything else is an API/network error
        if not is_not_found(e):
            raise ArchiveError(6, f"dataset_status lỗi: {e}")
    else:
        raise ArchiveError(5, f"dataset {dataset} đã tồn tại (status {st!r}); không tạo, không ghi đè")
    try:
        result = api.dataset_create_new(folder=staging, public=False, quiet=False, dir_mode="skip")
    except Exception as e:  # noqa: BLE001
        raise ArchiveError(6, f"dataset_create_new lỗi: {e}")
    err, status = getattr(result, "error", None), getattr(result, "status", None)
    if err or status == "error":
        raise ArchiveError(6, f"dataset_create_new trả lỗi: status={status!r} error={err!r}")
    print(f"created {dataset} (private); status={status!r} ref={getattr(result, 'ref', None)!r} "
          f"url={getattr(result, 'url', None)!r}")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------------------------------------------
def wait_ready(api, dataset, poll_s, timeout_s, sleep, clock):
    start = clock()
    while True:
        try:
            st = api.dataset_status(dataset)
        except Exception as e:  # noqa: BLE001 - transient until the timeout
            st = f"lỗi: {e}"
        if st == "ready":
            return st
        if clock() - start >= timeout_s:
            raise ArchiveError(6, f"dataset {dataset} chưa ready sau {timeout_s} s (lần cuối: {st!r}); chạy lại verify")
        print(f"status {st!r}; hỏi lại sau {poll_s} s")
        sleep(poll_s)


def private_from_list(api, dataset):
    slug = dataset.split("/")[1]
    try:
        items = api.dataset_list(mine=True, search=slug) or []
    except Exception as e:  # noqa: BLE001
        raise ArchiveError(4, f"DỪNG: không xác minh được dataset là private (dataset_list lỗi: {e})")
    hits = [d for d in items if d is not None and str(getattr(d, "ref", "")).lower() == dataset.lower()]
    if len(hits) != 1:
        raise ArchiveError(4, f"DỪNG: không xác minh được dataset là private ({dataset} không có trong dataset_list(mine))")
    v = getattr(hits[0], "is_private", None)
    if v is not True:
        raise ArchiveError(4, f"DỪNG: không xác minh được dataset là private (dataset_list: is_private={v!r})")
    return True


def private_from_metadata(api, dataset):
    tmp = tempfile.mkdtemp(prefix="vslt-archive-meta-")
    try:
        require_outside_repo(tmp, "thư mục tạm metadata")
        try:
            p = api.dataset_metadata(dataset, path=tmp)
            with open(p, encoding="utf-8") as f:
                j = json.load(f)
        except Exception as e:  # noqa: BLE001
            raise ArchiveError(4, f"DỪNG: không xác minh được dataset là private (dataset_metadata lỗi: {e})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    info = j.get("info", j) if isinstance(j, dict) else None
    v = info.get("isPrivate") if isinstance(info, dict) else None
    if v is not True:
        raise ArchiveError(4, f"DỪNG: không xác minh được dataset là private (dataset_metadata: isPrivate={v!r})")
    return True


def remote_files(api, dataset, page_size=100):
    out, token, seen = {}, None, set()
    while True:
        try:
            resp = api.dataset_list_files(dataset, page_token=token, page_size=page_size)
        except Exception as e:  # noqa: BLE001
            raise ArchiveError(6, f"dataset_list_files lỗi: {e}")
        if resp is None:
            raise ArchiveError(6, "dataset_list_files không trả gì")
        if getattr(resp, "error_message", None):
            raise ArchiveError(6, f"dataset_list_files: {resp.error_message}")
        for f in getattr(resp, "files", None) or []:
            out[f.name] = int(f.total_bytes)
        token = getattr(resp, "next_page_token", None)
        if not token:
            return out
        if token in seen:
            raise ArchiveError(6, "dataset_list_files: page_token lặp lại")
        seen.add(token)


def verify(staging, dataset, download_dir, manifest_out, api, argv, results_path, src_root=ROOT,
           poll_s=POLL_S, timeout_s=TIMEOUT_S, sleep=time.sleep, clock=time.monotonic):
    check_dataset_ref(dataset)
    require_outside_repo(staging, "--staging")
    require_outside_repo(download_dir, "--download-dir")
    sums = check_staging(staging)
    meta = read_metadata(staging, dataset)
    files = plan_files(results_path, src_root)
    if {f["archive_name"] for f in files} != set(sums):
        raise ArchiveError(3, f"tập file của results khác {SUMS} trong staging")
    for f in files:
        if sums[f["archive_name"]] != f["expected_sha256"]:
            raise ArchiveError(3, f"{SUMS}: sha256 của {f['archive_name']} khác results")
    local_sizes = {n: os.path.getsize(os.path.join(staging, n)) for n in list(sums) + [SUMS]}
    sums_sha = sha256_file(os.path.join(staging, SUMS))

    status = wait_ready(api, dataset, poll_s, timeout_s, sleep, clock)
    src = {"dataset_list_mine": private_from_list(api, dataset),
           "dataset_metadata": private_from_metadata(api, dataset)}

    remote = remote_files(api, dataset)
    if remote != local_sizes:
        raise ArchiveError(3, f"danh sách file trên Kaggle khác staging: chỉ Kaggle {sorted(set(remote) - set(local_sizes))}, "
                              f"chỉ staging {sorted(set(local_sizes) - set(remote))}, kích thước khác "
                              f"{sorted(n for n in set(remote) & set(local_sizes) if remote[n] != local_sizes[n])}")

    os.makedirs(download_dir, exist_ok=True)
    dl = tempfile.mkdtemp(prefix="verify-", dir=download_dir)
    try:
        api.dataset_download_files(dataset, path=dl, unzip=True)
    except Exception as e:  # noqa: BLE001
        raise ArchiveError(6, f"dataset_download_files lỗi: {e}")
    got = {n for n in os.listdir(dl)}
    if got != set(local_sizes):
        raise ArchiveError(3, f"file tải về khác staging: thừa {sorted(got - set(local_sizes))}, "
                              f"thiếu {sorted(set(local_sizes) - got)}")
    after = {n: sha256_file(os.path.join(dl, n)) for n in sums}
    bad = sorted(n for n in sums if after[n] != sums[n])
    if bad or sha256_file(os.path.join(dl, SUMS)) != sums_sha:
        raise ArchiveError(3, f"sha256 file tải về khác {SUMS}: {bad or [SUMS]}")

    manifest = {
        "generated_by": {"script": "scripts/archive_step4_kaggle.py",
                         "command": "python scripts/archive_step4_kaggle.py " + " ".join(shlex.quote(a) for a in argv),
                         "git_commit": git_head(), "kaggle_version": pkg_version("kaggle"),
                         "kagglesdk_version": pkg_version("kagglesdk"),
                         "verified_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "dataset": {"ref": dataset, "url": f"https://www.kaggle.com/datasets/{dataset}", "title": meta.get("title"),
                    "license": (meta.get("licenses") or [{}])[0].get("name"), "is_private": True,
                    "is_private_sources": src, "status": status, "total_bytes": sum(remote.values())},
        "files": [{"run": f["run"], "run_dir": f["run_dir"], "kind": f["kind"], "local_path": f["local_path"],
                   "archive_name": f["archive_name"], "size_bytes": local_sizes[f["archive_name"]],
                   "sha256": sums[f["archive_name"]], "sha256_after_download": after[f["archive_name"]]}
                  for f in files],
        "sha256sums_file": {"archive_name": SUMS, "sha256": sums_sha},
        "verified": {"file_list_matches": True, "downloaded_sha256_all_match": True, "n_files": len(files)}}
    os.makedirs(os.path.dirname(os.path.abspath(manifest_out)), exist_ok=True)
    tmp = manifest_out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, manifest_out)
    print(f"verified {dataset}: private (2 sources), ready, {len(files)} files + {SUMS}; manifest {manifest_out}")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------------------
def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--results", required=True)
    s.add_argument("--staging", required=True)
    s.add_argument("--dataset", required=True)
    u = sub.add_parser("upload")
    u.add_argument("--staging", required=True)
    u.add_argument("--dataset", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--staging", required=True)
    v.add_argument("--dataset", required=True)
    v.add_argument("--download-dir", required=True)
    v.add_argument("--manifest-out", required=True)
    v.add_argument("--results", default="reports/step4_2026-09-26/step4_results.json")
    return ap.parse_args(argv)


def kaggle_api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api


def main(argv=None, api=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        if args.cmd == "stage":
            return stage(os.path.abspath(args.results), args.staging, args.dataset)
        api = api if api is not None else kaggle_api()
        if args.cmd == "upload":
            return upload(args.staging, args.dataset, api)
        return verify(args.staging, args.dataset, args.download_dir, args.manifest_out, api, argv,
                      os.path.abspath(args.results))
    except ArchiveError as e:
        print(f"archive_step4_kaggle: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
