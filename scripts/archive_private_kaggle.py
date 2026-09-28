"""
Archive the Level 1 provenance evidence and the untracked inputs of the step-4 REPORT in ONE new private Kaggle dataset
(docs/plans/05-thuc-thi-quyet-dinh-0928.md, §3.3), and restore them into a working tree.

Sub-commands (stage -> upload -> verify, then restore on any machine):
  python scripts/archive_private_kaggle.py stage --results reports/step4_2026-09-26/step4_results.json \
         --provenance reports/alphabet_deploy_2026-09-27/provenance.json \
         --staging ../_kaggle_staging/vslt-provenance-artifacts --dataset phmvnsm33/vslt-provenance-artifacts
  python scripts/archive_private_kaggle.py upload --staging ../_kaggle_staging/vslt-provenance-artifacts \
         --dataset phmvnsm33/vslt-provenance-artifacts
  python scripts/archive_private_kaggle.py verify --staging ../_kaggle_staging/vslt-provenance-artifacts \
         --dataset phmvnsm33/vslt-provenance-artifacts --download-dir ../_kaggle_staging/verify_provenance \
         --manifest-out reports/private_archive_<YYYY-MM-DD>/kaggle_archive_manifest.json \
         --results reports/step4_2026-09-26/step4_results.json --provenance reports/alphabet_deploy_2026-09-27/provenance.json
  python scripts/archive_private_kaggle.py restore --manifest reports/private_archive_<YYYY-MM-DD>/kaggle_archive_manifest.json \
         --download-dir ../_kaggle_staging/restore_dl [--root DIR] [--only LOCAL_PATH ...]

The file list comes from committed JSON (never typed by hand):
  group "step4_untracked_input": step4_results.json limitations_data.untracked_unarchived_inputs.files (path, sha256, role);
  group "alphabet_provenance"  : provenance.json checkpoints.* (path, exists, sha256) + NESTED_PREDICTIONS of
                                 scripts/alphabet_ckpt_provenance.py (no sha256 recorded anywhere: hashed at stage time).
Upload reuses archive_step4_kaggle.upload unchanged (one create call, private flag constant there); this script never
updates, versions or deletes a dataset. Text sources are scanned for credential-like strings before staging; a match
stops everything and only the path + pattern name are printed. The scan is pattern based: it cannot prove absence.

Exit codes (as archive_step4_kaggle): 0 ok; 2 missing input / bad argument / temporary path inside the repo / metadata
without isPrivate: true / credential-like string found / total size over MAX_TOTAL_BYTES (ask the user); 3 sha256, file
set or size mismatch, or restore target present with another sha256; 4 the dataset could NOT be verified as private
(STOP); 5 the slug already exists; 6 Kaggle not ready / API or network error.
No credential is read, printed or written here (the Kaggle client authenticates itself in kaggle_api()).
"""
import argparse
import ast
import datetime as dt
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_step4_kaggle as A  # noqa: E402
from archive_step4_kaggle import (ArchiveError, check_dataset_ref, check_staging, git_head, kaggle_api,  # noqa: E402,F401
                                  parse_sums, pkg_version, private_from_list, private_from_metadata, read_metadata,
                                  remote_files, require_outside_repo, sha256_file, sums_text, upload, wait_ready)

ROOT = A.ROOT
SUMS, META = A.SUMS, A.META
SCRIPT = "scripts/archive_private_kaggle.py"
TITLE = "VSLT provenance evidence and untracked inputs"
LICENSE = "unknown"
DESCRIPTION = ("Private archive of the VSLT project (Vietnamese Sign Language Translator): (1) provenance evidence of "
               "the Level 1 alphabet checkpoints (deployed + known checkpoints + nested predictions), trained on "
               "hauuto/vietnamese-sign-language-alphabet; (2) untracked inputs of the step-4 report (kernel logs, "
               "history, checkpoints, VSL-GH segments), derived from QIPEDC and VSL-GH. File list and sha256 in "
               "SHA256SUMS. Licence of the source data unknown / redistribution not stated; internal use only, do "
               "not redistribute.")
MAX_TOTAL_BYTES = 2 * 1024 ** 3
PROVENANCE_SCRIPT = os.path.join(ROOT, "scripts", "alphabet_ckpt_provenance.py")
GROUP_S, GROUP_A = "step4_untracked_input", "alphabet_provenance"
S_SHA_SOURCE = "reports/step4_2026-09-26/step4_results.json#limitations_data.untracked_unarchived_inputs"
A_SHA_SOURCE = "reports/alphabet_deploy_2026-09-27/provenance.json#checkpoints."
LICENCE_NOTE_A = ("hauuto/vietnamese-sign-language-alphabet: licence unknown (docs/data_registry.md §1b); private, "
                  "internal use only")
LICENCE_NOTE_S = ("derived from QIPEDC and/or VSL-GH: QIPEDC educational / academic research use, redistribution not "
                  "stated (docs/data_registry.md §1); VSL-GH MIT per docs/data_registry.md §2 (not re-verified); private")
LICENCE = {GROUP_A: ("unknown", LICENCE_NOTE_A), GROUP_S: ("redistribution_not_stated", LICENCE_NOTE_S)}
TEXT_SUFFIXES = (".log", ".json", ".csv", ".txt", ".md")
SECRET_PATTERNS = {
    "kaggle_token": re.compile(rb"KGAT_[A-Za-z0-9]"),
    "json_key": re.compile(rb'"key"\s*:\s*"'),
    "kaggle_key_env": re.compile(rb"KAGGLE_KEY"),
    "api_key": re.compile(rb"(?i)api[_-]?key\s*[:=]"),
    "token_assign": re.compile(rb"(?i)(access|auth)[_-]?token\s*[:=]"),
    "github_token": re.compile(rb"ghp_[A-Za-z0-9]{20}"),
    "hf_token": re.compile(rb"hf_[A-Za-z0-9]{20}"),
}
MANIFEST_NAME = "kaggle_archive_manifest.json"
VN_TZ = dt.timezone(dt.timedelta(hours=7))


# ---------------------------------------------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------------------------------------------
def nested_predictions_path(script=PROVENANCE_SCRIPT):
    """NESTED_PREDICTIONS of scripts/alphabet_ckpt_provenance.py, read with ast (the module imports torch)."""
    try:
        with open(script, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        raise ArchiveError(2, f"không đọc được {script}: {e}")
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "NESTED_PREDICTIONS"
                                                for t in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise ArchiveError(2, f"{script}: không có hằng chuỗi NESTED_PREDICTIONS")


def check_local_path(path):
    """Relative repo path with '/' separators, no drive letter, no '..', no empty component."""
    if not isinstance(path, str) or not path:
        raise ArchiveError(2, f"local_path không hợp lệ: {path!r}")
    parts = path.split("/")
    if (os.path.isabs(path) or path.startswith(("/", "\\")) or ":" in path or "\\" in path
            or any(p in ("", ".", "..") for p in parts)):
        raise ArchiveError(2, f"local_path phải là đường dẫn tương đối trong repo (không '..', không ổ đĩa): {path!r}")
    return path


def _load_json(path, what):
    if not os.path.isfile(path):
        raise ArchiveError(2, f"thiếu file {what}: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _entry(group, role, local_path, src_root, expected, expected_source):
    status, note = LICENCE[group]
    check_local_path(local_path)
    return {"group": group, "role": role, "local_path": local_path,
            "source": os.path.join(src_root, *local_path.split("/")), "archive_name": local_path.replace("/", "__"),
            "expected_sha256": expected, "expected_sha256_source": expected_source,
            "licence_status": status, "licence_note": note}


def plan_files(results_path, provenance_path, src_root=ROOT):
    """Sorted by archive_name; keys group, role, local_path, source, archive_name, expected_sha256,
    expected_sha256_source, licence_status, licence_note."""
    res = _load_json(results_path, "results")
    prov = _load_json(provenance_path, "provenance")
    untracked = ((res.get("limitations_data") or {}).get("untracked_unarchived_inputs")) if isinstance(res, dict) else None
    s_files = untracked.get("files") if isinstance(untracked, dict) else None
    if not isinstance(s_files, list) or not s_files:
        raise ArchiveError(2, f"{results_path}: thiếu hoặc rỗng limitations_data.untracked_unarchived_inputs.files")
    ckpts = prov.get("checkpoints") if isinstance(prov, dict) else None
    if not isinstance(ckpts, dict) or not ckpts:
        raise ArchiveError(2, f"{provenance_path}: thiếu hoặc rỗng checkpoints")

    s_out = []
    for e in s_files:
        if not isinstance(e, dict) or not e.get("path") or not e.get("sha256"):
            raise ArchiveError(2, f"untracked_unarchived_inputs: phần tử thiếu path/sha256: {e!r}")
        s_out.append(_entry(GROUP_S, e.get("role"), e["path"], src_root, e["sha256"], S_SHA_SOURCE))
    a_out = []
    for key in sorted(ckpts):
        v = ckpts[key]
        if not isinstance(v, dict) or not v.get("path"):
            raise ArchiveError(2, f"checkpoints.{key}: thiếu path")
        if v.get("exists") is not True:
            raise ArchiveError(2, f"checkpoints.{key}: exists khác true ({v.get('exists')!r})")
        if not v.get("sha256"):
            raise ArchiveError(2, f"checkpoints.{key}: thiếu sha256")
        a_out.append(_entry(GROUP_A, key, v["path"], src_root, v["sha256"], A_SHA_SOURCE + key))
    a_out.append(_entry(GROUP_A, "nested_predictions (V6)", nested_predictions_path(), src_root, None, None))

    both = {f["local_path"] for f in s_out} & {f["local_path"] for f in a_out}
    if both:
        raise ArchiveError(2, f"local_path có ở cả 2 nhóm: {sorted(both)}")
    out = s_out + a_out
    names = [f["archive_name"] for f in out]
    if len(set(names)) != len(names):
        raise ArchiveError(2, f"tên trùng nhau: {sorted({n for n in names if names.count(n) > 1})}")
    return sorted(out, key=lambda f: f["archive_name"])


# ---------------------------------------------------------------------------------------------------------------
# stage
# ---------------------------------------------------------------------------------------------------------------
def scan_secrets(files):
    """[(local_path, pattern name)] for text sources; the matched bytes are never returned or printed."""
    hits = []
    for f in files:
        if not f["local_path"].lower().endswith(TEXT_SUFFIXES):
            continue
        with open(f["source"], "rb") as fh:
            data = fh.read()
        hits += [(f["local_path"], name) for name, rx in SECRET_PATTERNS.items() if rx.search(data)]
    return hits


def metadata(dataset):
    return {"title": TITLE, "id": dataset, "licenses": [{"name": LICENSE}], "isPrivate": True,
            "description": DESCRIPTION}


def stage(results_path, provenance_path, staging, dataset, src_root=ROOT):
    check_dataset_ref(dataset)
    require_outside_repo(staging, "--staging")
    if os.path.exists(staging):
        raise ArchiveError(2, f"staging đã tồn tại (không ghi đè): {staging}")
    files = plan_files(results_path, provenance_path, src_root)
    missing = [f["local_path"] for f in files if not os.path.isfile(f["source"])]
    if missing:
        raise ArchiveError(2, f"thiếu file nguồn: {missing}")
    hashes = {}
    for f in files:
        hashes[f["archive_name"]] = sha256_file(f["source"])
        if f["expected_sha256"] is not None and hashes[f["archive_name"]] != f["expected_sha256"]:
            raise ArchiveError(3, f"sha256 của {f['local_path']} khác giá trị trong {f['expected_sha256_source']}")
    hits = scan_secrets(files)
    if hits:
        raise ArchiveError(2, "DỪNG, hỏi người dùng: có chuỗi giống credential (chỉ nêu file + tên mẫu): "
                              + "; ".join(f"{p} [{n}]" for p, n in hits))
    total = sum(os.path.getsize(f["source"]) for f in files)
    if total > MAX_TOTAL_BYTES:
        raise ArchiveError(2, f"tổng {total} byte > MAX_TOTAL_BYTES {MAX_TOTAL_BYTES}: hỏi người dùng")
    parent = os.path.dirname(os.path.abspath(staging))
    os.makedirs(parent, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=os.path.basename(os.path.abspath(staging)) + ".partial-", dir=parent)
    try:
        for f in files:
            dst = os.path.join(tmp, f["archive_name"])
            shutil.copy2(f["source"], dst)
            if sha256_file(dst) != hashes[f["archive_name"]]:
                raise ArchiveError(3, f"bản sao {f['archive_name']} có sha256 khác nguồn")
        with open(os.path.join(tmp, SUMS), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(sums_text(hashes))
        with open(os.path.join(tmp, META), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(metadata(dataset), ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, staging)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"staged {len(files)} files + {SUMS} + {META} in {staging} ({total} bytes of data)")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------------------------------------------
def expected_manifest_rel(now=None):
    day = (now or dt.datetime.now(VN_TZ)).astimezone(VN_TZ).strftime("%Y-%m-%d")
    return f"reports/private_archive_{day}/{MANIFEST_NAME}"


def check_manifest_out(manifest_out):
    """Inside the repo the manifest must be reports/private_archive_<today, Vietnam time>/kaggle_archive_manifest.json."""
    if A.inside(manifest_out):
        rel = os.path.relpath(os.path.abspath(manifest_out), ROOT).replace("\\", "/")
        if rel != expected_manifest_rel():
            raise ArchiveError(2, f"--manifest-out trong repo phải là {expected_manifest_rel()}, nhận {rel}")


def verify(staging, dataset, download_dir, manifest_out, api, argv, results_path, provenance_path, src_root=ROOT,
           poll_s=A.POLL_S, timeout_s=A.TIMEOUT_S, sleep=time.sleep, clock=time.monotonic):
    check_dataset_ref(dataset)
    check_manifest_out(manifest_out)
    require_outside_repo(staging, "--staging")
    require_outside_repo(download_dir, "--download-dir")
    sums = check_staging(staging)
    meta = read_metadata(staging, dataset)
    files = plan_files(results_path, provenance_path, src_root)
    if {f["archive_name"] for f in files} != set(sums):
        raise ArchiveError(3, f"tập file của plan_files khác {SUMS} trong staging")
    for f in files:
        if f["expected_sha256"] is not None and sums[f["archive_name"]] != f["expected_sha256"]:
            raise ArchiveError(3, f"{SUMS}: sha256 của {f['archive_name']} khác {f['expected_sha256_source']}")
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
    dl = tempfile.mkdtemp(prefix="verify-", dir=os.path.abspath(download_dir))
    try:
        api.dataset_download_files(dataset, path=dl, unzip=True)
    except Exception as e:  # noqa: BLE001
        raise ArchiveError(6, f"dataset_download_files lỗi: {e}")
    got = set(os.listdir(dl))
    if got != set(local_sizes):
        raise ArchiveError(3, f"file tải về khác staging: thừa {sorted(got - set(local_sizes))}, "
                              f"thiếu {sorted(set(local_sizes) - got)}")
    after = {n: sha256_file(os.path.join(dl, n)) for n in sums}
    bad = sorted(n for n in sums if after[n] != sums[n])
    if bad or sha256_file(os.path.join(dl, SUMS)) != sums_sha:
        raise ArchiveError(3, f"sha256 file tải về khác {SUMS}: {bad or [SUMS]}")

    manifest = {
        "generated_by": {"script": SCRIPT,
                         "command": f"python {SCRIPT} " + " ".join(shlex.quote(a) for a in argv),
                         "git_commit": git_head(), "kaggle_version": pkg_version("kaggle"),
                         "kagglesdk_version": pkg_version("kagglesdk"),
                         "verified_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "dataset": {"ref": dataset, "url": f"https://www.kaggle.com/datasets/{dataset}", "title": meta.get("title"),
                    "license": (meta.get("licenses") or [{}])[0].get("name"), "is_private": True,
                    "is_private_sources": src, "status": status, "total_bytes": sum(remote.values())},
        "files": [{"group": f["group"], "role": f["role"], "local_path": f["local_path"],
                   "archive_name": f["archive_name"], "size_bytes": local_sizes[f["archive_name"]],
                   "sha256": sums[f["archive_name"]], "sha256_after_download": after[f["archive_name"]],
                   "expected_sha256_source": f["expected_sha256_source"], "licence_status": f["licence_status"],
                   "licence_note": f["licence_note"]}
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
# restore (never overwrites; writes only the manifest's local_path entries under root)
# ---------------------------------------------------------------------------------------------------------------
def restore(manifest_path, download_dir, api, root=ROOT, only=None):
    m = _load_json(manifest_path, "manifest")
    try:
        dataset = m["dataset"]["ref"]
        entries = [{"local_path": f["local_path"], "archive_name": f["archive_name"], "sha256": f["sha256"]}
                   for f in m["files"]]
    except (KeyError, TypeError) as e:
        raise ArchiveError(2, f"manifest thiếu khóa: {e}")
    check_dataset_ref(dataset)
    require_outside_repo(download_dir, "--download-dir")
    if os.path.normcase(os.path.abspath(root)) != os.path.normcase(ROOT):
        require_outside_repo(root, "--root (khác gốc repo)")
    for e in entries:
        check_local_path(e["local_path"])
    if only:
        known = {e["local_path"] for e in entries}
        unknown = sorted(set(only) - known)
        if unknown:
            raise ArchiveError(2, f"--only không có trong manifest: {unknown}")
        entries = [e for e in entries if e["local_path"] in set(only)]

    os.makedirs(download_dir, exist_ok=True)
    dl = tempfile.mkdtemp(prefix="restore-", dir=os.path.abspath(download_dir))
    try:
        api.dataset_download_files(dataset, path=dl, unzip=True)
    except Exception as e:  # noqa: BLE001
        raise ArchiveError(6, f"dataset_download_files lỗi: {e}")
    for e in entries:
        p = os.path.join(dl, e["archive_name"])
        if not os.path.isfile(p):
            raise ArchiveError(3, f"file tải về thiếu {e['archive_name']}")
        if sha256_file(p) != e["sha256"]:
            raise ArchiveError(3, f"sha256 file tải về {e['archive_name']} khác manifest; không ghi gì")

    todo = []
    for e in entries:                              # check EVERYTHING before writing anything
        target = os.path.join(root, *e["local_path"].split("/"))
        if os.path.lexists(target):
            if not os.path.isfile(target) or sha256_file(target) != e["sha256"]:
                raise ArchiveError(3, f"{e['local_path']} đã có với nội dung khác manifest; không ghi file nào")
            print(f"đã có: {e['local_path']}")
        else:
            todo.append((e, target))
    for e, target in todo:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=os.path.basename(target) + ".partial-", dir=os.path.dirname(target))
        os.close(fd)
        try:
            shutil.copyfile(os.path.join(dl, e["archive_name"]), tmp)
            if sha256_file(tmp) != e["sha256"]:
                raise ArchiveError(3, f"bản sao {e['local_path']} có sha256 khác manifest")
            if os.path.lexists(target):
                raise ArchiveError(3, f"{e['local_path']} vừa xuất hiện trong lúc khôi phục; không ghi đè")
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        print(f"đã ghi: {e['local_path']}")
    print(f"restore {dataset}: {len(todo)} file ghi mới, {len(entries) - len(todo)} file bỏ qua vì có sẵn cùng sha256 (root {root})")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------------------
def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--results", required=True)
    s.add_argument("--provenance", required=True)
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
    v.add_argument("--results", required=True)
    v.add_argument("--provenance", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--manifest", required=True)
    r.add_argument("--download-dir", required=True)
    r.add_argument("--root", default=ROOT)
    r.add_argument("--only", nargs="+", default=None)
    return ap.parse_args(argv)


def main(argv=None, api=None, src_root=ROOT):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        if args.cmd == "stage":
            return stage(os.path.abspath(args.results), os.path.abspath(args.provenance), args.staging, args.dataset,
                         src_root=src_root)
        api = api if api is not None else kaggle_api()
        if args.cmd == "upload":
            return A.upload(args.staging, args.dataset, api)
        if args.cmd == "verify":
            return verify(args.staging, args.dataset, args.download_dir, args.manifest_out, api, argv,
                          os.path.abspath(args.results), os.path.abspath(args.provenance), src_root=src_root)
        return restore(os.path.abspath(args.manifest), args.download_dir, api, root=args.root, only=args.only)
    except ArchiveError as e:
        print(f"archive_private_kaggle: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
