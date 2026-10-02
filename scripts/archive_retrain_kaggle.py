"""
Archive the plan-13 retrain artifacts (and inputs) in NEW private Kaggle datasets, verify them, restore them
(docs/plans/13-train-lai-checkpoint-thieu.md §3.4c). Equivalent of scripts/archive_private_kaggle.py, but every
temporary path lives under <repo>/_work/ (user decision 2026-09-30 23:45: temporary files only in _work/).

Sub-commands (stage -> upload -> verify; restore on any machine):
  python scripts/archive_retrain_kaggle.py stage --src _work/_plan13_tmp/src_inputs_tier1 \
         --staging _work/_plan13_tmp/staging_inputs_tier1 --dataset phmvnsm33/vslt-retrain-inputs-tier1 \
         --title "VSLT retrain inputs Tier 1" --licence-note "QIPEDC: educational / research use, redistribution not stated"
  python scripts/archive_retrain_kaggle.py upload --staging _work/_plan13_tmp/staging_inputs_tier1 \
         --dataset phmvnsm33/vslt-retrain-inputs-tier1
  python scripts/archive_retrain_kaggle.py verify --staging _work/_plan13_tmp/staging_inputs_tier1 \
         --dataset phmvnsm33/vslt-retrain-inputs-tier1 --download-dir _work/_plan13_tmp/verify_inputs_tier1 \
         --manifest-out reports/retrain_<D>/inputs_tier1_manifest.json
  python scripts/archive_retrain_kaggle.py restore --manifest reports/retrain_<D>/inputs_tier1_manifest.json \
         --download-dir _work/_plan13_tmp/restore_inputs_tier1 --dest <directory>

stage copies EVERY regular file below --src (recursive). It refuses: symlinks, junctions and any other reparse point
(file or directory), empty directories (including an empty --src), a relative path with a component containing "__"
(archive_name = relative path with "/" -> "__" must stay invertible), a name colliding with SHA256SUMS or
dataset-metadata.json, credential-like strings in text files (SECRET_PATTERNS of archive_private_kaggle; only the path
and the pattern name are printed), a total over MAX_TOTAL_BYTES (3 GiB), an existing staging directory. Files are
written with exclusive create ('xb') into "<staging>.partial-*" and the directory is renamed to <staging> only when
everything is copied and re-hashed; on failure the partial directory is LEFT in _work/ (this script never deletes a
directory) and its path is printed.
upload calls ONLY api.dataset_create_new(folder, public=False, dir_mode="skip") — never version / update / delete;
an existing slug -> exit 5 (nothing created).
verify: ready, private from 2 sources (dataset_list(mine) + dataset_metadata), remote file list + sizes == staging,
download into a new directory under --download-dir, sha256 of every file == SHA256SUMS, then writes the manifest
(refuses to overwrite). --manifest-out inside the repo must be reports/retrain_<YYYY-MM-DD>/<name>_manifest.json, or
under _work/; anywhere else -> exit 2.
restore: every manifest entry is checked (generator, archive_name == rel_path with "/" -> "__", safe relative path),
the dataset is downloaded under --download-dir, every sha256 checked, every target checked (absent, or present with
the same sha256 -> skipped; present with another sha256 -> exit 3 and NOTHING is written), then files are written with
exclusive create (never overwrite).

Reused unchanged from scripts/archive_step4_kaggle.py: sha256_file, check_dataset_ref, read_metadata, check_staging,
wait_ready, private_from_list, private_from_metadata, remote_files, sums_text, parse_sums, git_head, pkg_version,
kaggle_api (+ is_not_found, listed_mine, inside); from scripts/archive_private_kaggle.py: SECRET_PATTERNS,
TEXT_SUFFIXES, check_local_path, code_status. Neither old script is modified.

Exit codes (as archive_step4_kaggle): 0 ok; 2 missing input / bad argument / path not under _work/ / link or reparse
point / empty directory / metadata without isPrivate: true / credential-like string / total too large / manifest
target present or misplaced / unsupported manifest; 3 sha256, file set or size mismatch, restore target present with
another sha256; 4 the dataset could NOT be verified as private (STOP); 5 the slug already exists; 6 Kaggle not ready /
API or network error.
No credential is read, printed or written here (the Kaggle client authenticates itself in kaggle_api()).
"""
import argparse
import datetime as dt
import json
import os
import re
import shlex
import stat
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_step4_kaggle as A  # noqa: E402
import archive_private_kaggle as P  # noqa: E402
from archive_step4_kaggle import (ArchiveError, check_dataset_ref, check_staging, git_head, kaggle_api,  # noqa: E402,F401
                                  parse_sums, pkg_version, private_from_list, private_from_metadata, read_metadata,
                                  remote_files, sha256_file, sums_text, wait_ready)

ROOT = A.ROOT
WORK_ROOT = os.path.join(ROOT, "_work")
SUMS, META = A.SUMS, A.META
SCRIPT = "scripts/archive_retrain_kaggle.py"
LICENSE = "unknown"
DESCRIPTION_PREFIX = ("Private archive of the VSLT project (Vietnamese Sign Language Translator), plan 13 (retrain of "
                      "missing checkpoints). File list and sha256 in SHA256SUMS. Internal use only, do not "
                      "redistribute. Licence note: ")
MAX_TOTAL_BYTES = 3 * 1024 ** 3
TEXT_SUFFIXES = tuple(P.TEXT_SUFFIXES) + (".jsonl", ".yaml", ".yml", ".py", ".sh", ".cfg", ".ini", ".toml")
SECRET_PATTERNS = P.SECRET_PATTERNS
MANIFEST_IN_REPO_RX = re.compile(r"^reports/retrain_\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+_manifest\.json$")
CHUNK = 1 << 20


# ---------------------------------------------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------------------------------------------
def require_under_work(path, what, work_root=None):
    """`path` must be strictly below <repo>/_work/ (plan 13 §3.4c)."""
    work = os.path.abspath(work_root or WORK_ROOT)
    p = os.path.abspath(path)
    if not A.inside(p, work) or os.path.normcase(p) == os.path.normcase(work):
        raise ArchiveError(2, f"{what} phải nằm DƯỚI {work}: {path}")
    return p


def is_link_or_reparse(path):
    """True for a symlink, a junction or any other reparse point (Windows), checked without following links."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def check_manifest_out(manifest_out):
    """In the repo: reports/retrain_<YYYY-MM-DD>/<name>_manifest.json, or anywhere under _work/; otherwise exit 2.
    An existing target is never overwritten."""
    p = os.path.abspath(manifest_out)
    if A.inside(p, WORK_ROOT) and os.path.normcase(p) != os.path.normcase(os.path.abspath(WORK_ROOT)):
        pass
    elif A.inside(p, ROOT):
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if not MANIFEST_IN_REPO_RX.match(rel):
            raise ArchiveError(2, f"--manifest-out trong repo phải là reports/retrain_<YYYY-MM-DD>/<tên>_manifest.json "
                                  f"(hoặc dưới _work/), nhận {rel}")
    else:
        raise ArchiveError(2, f"--manifest-out phải nằm trong repo (reports/retrain_<D>/ hoặc _work/): {manifest_out}")
    if os.path.lexists(p):
        raise ArchiveError(2, f"--manifest-out đã tồn tại (không ghi đè): {manifest_out}")
    return p


# ---------------------------------------------------------------------------------------------------------------
# stage
# ---------------------------------------------------------------------------------------------------------------
def plan_files(src):
    """[{rel_path, archive_name, source}] for every regular file below `src` (sorted by archive_name)."""
    if not os.path.isdir(src) or is_link_or_reparse(src):
        raise ArchiveError(2, f"--src không phải thư mục thường: {src}")
    out = []
    for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
        for d in list(dirnames):
            full = os.path.join(dirpath, d)
            if is_link_or_reparse(full):
                raise ArchiveError(2, f"từ chối symlink/junction/reparse point: {full}")
        if not dirnames and not filenames:
            raise ArchiveError(2, f"từ chối thư mục rỗng: {dirpath}")
        for n in filenames:
            full = os.path.join(dirpath, n)
            if is_link_or_reparse(full):
                raise ArchiveError(2, f"từ chối symlink/junction/reparse point: {full}")
            if not os.path.isfile(full):
                raise ArchiveError(2, f"không phải file thường: {full}")
            rel = os.path.relpath(full, src).replace("\\", "/")
            P.check_local_path(rel)
            if any("__" in part for part in rel.split("/")):
                raise ArchiveError(2, f"tên có '__' (archive_name không đảo được): {rel}")
            name = rel.replace("/", "__")
            if name in (SUMS, META):
                raise ArchiveError(2, f"tên trùng file hệ thống của staging: {rel}")
            out.append({"rel_path": rel, "archive_name": name, "source": full})
    names = [f["archive_name"] for f in out]
    if len(set(n.lower() for n in names)) != len(names):
        raise ArchiveError(2, "archive_name trùng nhau (không phân biệt hoa thường)")
    return sorted(out, key=lambda f: f["archive_name"])


def scan_secrets(files):
    """[(rel_path, pattern name)] for text files; the matched bytes are never returned or printed."""
    hits = []
    for f in files:
        if not f["rel_path"].lower().endswith(TEXT_SUFFIXES):
            continue
        with open(f["source"], "rb") as fh:
            data = fh.read()
        hits += [(f["rel_path"], name) for name, rx in SECRET_PATTERNS.items() if rx.search(data)]
    return hits


def metadata(dataset, title, licence_note):
    return {"title": title, "id": dataset, "licenses": [{"name": LICENSE}], "isPrivate": True,
            "description": DESCRIPTION_PREFIX + licence_note}


def _copy_exclusive(src, dst):
    with open(src, "rb") as fi, open(dst, "xb") as fo:
        for block in iter(lambda: fi.read(CHUNK), b""):
            fo.write(block)


def stage(src, staging, dataset, title, licence_note, work_root=None):
    check_dataset_ref(dataset)
    src = require_under_work(src, "--src", work_root)
    staging = require_under_work(staging, "--staging", work_root)
    if not title or not (6 <= len(title) <= 50):
        raise ArchiveError(2, f"--title phải dài 6-50 ký tự: {title!r}")
    if not licence_note or not licence_note.strip():
        raise ArchiveError(2, "--licence-note không được rỗng")
    if os.path.lexists(staging):
        raise ArchiveError(2, f"staging đã tồn tại (không ghi đè): {staging}")
    if A.inside(staging, src) or A.inside(src, staging):
        raise ArchiveError(2, "--staging và --src không được lồng nhau")
    files = plan_files(src)
    hashes = {f["archive_name"]: sha256_file(f["source"]) for f in files}
    hits = scan_secrets(files)
    if hits:
        raise ArchiveError(2, "DỪNG, hỏi người dùng: có chuỗi giống credential (chỉ nêu file + tên mẫu): "
                              + "; ".join(f"{p} [{n}]" for p, n in hits))
    total = sum(os.path.getsize(f["source"]) for f in files)
    if total > MAX_TOTAL_BYTES:
        raise ArchiveError(2, f"tổng {total} byte > MAX_TOTAL_BYTES {MAX_TOTAL_BYTES}: hỏi người dùng")
    parent = os.path.dirname(staging)
    os.makedirs(parent, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=os.path.basename(staging) + ".partial-", dir=parent)
    try:
        for f in files:
            dst = os.path.join(tmp, f["archive_name"])
            _copy_exclusive(f["source"], dst)
            if sha256_file(dst) != hashes[f["archive_name"]]:
                raise ArchiveError(3, f"bản sao {f['archive_name']} có sha256 khác nguồn")
        with open(os.path.join(tmp, SUMS), "x", encoding="utf-8", newline="\n") as fh:
            fh.write(sums_text(hashes))
        with open(os.path.join(tmp, META), "x", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(metadata(dataset, title, licence_note), ensure_ascii=True, indent=2, sort_keys=True)
                     + "\n")
        if os.path.lexists(staging):
            raise ArchiveError(2, f"staging vừa xuất hiện trong lúc chép (không ghi đè): {staging}")
        os.rename(tmp, staging)
    except BaseException as e:
        print(f"archive_retrain_kaggle: stage thất bại; thư mục dở dang để lại (không xóa): {tmp}", file=sys.stderr)
        if isinstance(e, ArchiveError):
            raise
        if isinstance(e, OSError):
            raise ArchiveError(2, f"lỗi ghi staging: {e}")
        raise
    print(f"staged {len(files)} files + {SUMS} + {META} in {staging} ({total} bytes of data)")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# upload (exactly one create call, always private)
# ---------------------------------------------------------------------------------------------------------------
def upload(staging, dataset, api, work_root=None):
    check_dataset_ref(dataset)
    staging = require_under_work(staging, "--staging", work_root)
    check_staging(staging)                       # (1) sha256 + exact file set -> 3
    read_metadata(staging, dataset)              # (2) isPrivate is True, id == dataset -> 2
    try:                                         # (3) the slug must not exist yet -> 5
        st = api.dataset_status(dataset)
    except Exception as e:  # noqa: BLE001 - HTTP 403/404 means "maybe absent"; anything else is an API/network error
        if not A.is_not_found(e):
            raise ArchiveError(6, f"dataset_status lỗi: {e}")
        if A.listed_mine(api, dataset):
            raise ArchiveError(5, f"dataset {dataset} đã có trong dataset_list(mine); không tạo, không ghi đè")
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
def rel_from_archive_name(name):
    return name.replace("__", "/")


def verify(staging, dataset, download_dir, manifest_out, api, argv, work_root=None,
           poll_s=A.POLL_S, timeout_s=A.TIMEOUT_S, sleep=time.sleep, clock=time.monotonic):
    check_dataset_ref(dataset)
    manifest_out = check_manifest_out(manifest_out)
    staging = require_under_work(staging, "--staging", work_root)
    download_dir = require_under_work(download_dir, "--download-dir", work_root)
    sums = check_staging(staging)
    meta = read_metadata(staging, dataset)
    for n in sums:
        P.check_local_path(rel_from_archive_name(n))
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
    got = set(os.listdir(dl))
    if got != set(local_sizes):
        raise ArchiveError(3, f"file tải về khác staging: thừa {sorted(got - set(local_sizes))}, "
                              f"thiếu {sorted(set(local_sizes) - got)}")
    after = {n: sha256_file(os.path.join(dl, n)) for n in sums}
    bad = sorted(n for n in sums if after[n] != sums[n])
    if bad or sha256_file(os.path.join(dl, SUMS)) != sums_sha:
        raise ArchiveError(3, f"sha256 file tải về khác {SUMS}: {bad or [SUMS]}")

    dirty, dirty_files = P.code_status()
    if dirty is not False:
        print(f"cảnh báo: code_dirty = {dirty!r}; ghi vào manifest")
    manifest = {
        "generated_by": {"script": SCRIPT,
                         "command": f"python {SCRIPT} " + " ".join(shlex.quote(a) for a in argv),
                         "git_commit": git_head(), "code_dirty": dirty, "code_dirty_files": dirty_files,
                         "kaggle_version": pkg_version("kaggle"), "kagglesdk_version": pkg_version("kagglesdk"),
                         "verified_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "dataset": {"ref": dataset, "url": f"https://www.kaggle.com/datasets/{dataset}", "title": meta.get("title"),
                    "license": (meta.get("licenses") or [{}])[0].get("name"), "description": meta.get("description"),
                    "is_private": True, "is_private_sources": src, "status": status,
                    "total_bytes": sum(remote.values())},
        "files": [{"rel_path": rel_from_archive_name(n), "archive_name": n, "size_bytes": local_sizes[n],
                   "sha256": sums[n], "sha256_after_download": after[n]} for n in sorted(sums)],
        "sha256sums_file": {"archive_name": SUMS, "sha256": sums_sha},
        "verified": {"file_list_matches": True, "downloaded_sha256_all_match": True, "n_files": len(sums)}}
    os.makedirs(os.path.dirname(manifest_out), exist_ok=True)
    with open(manifest_out, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"verified {dataset}: private (2 sources), ready, {len(sums)} files + {SUMS}; manifest {manifest_out}")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# restore (never overwrites)
# ---------------------------------------------------------------------------------------------------------------
def _load_json(path, what):
    if not os.path.isfile(path):
        raise ArchiveError(2, f"thiếu file {what}: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def restore(manifest_path, download_dir, dest, api, work_root=None):
    m = _load_json(manifest_path, "manifest")
    try:
        dataset = m["dataset"]["ref"]
        generator = m["generated_by"]["script"]
        entries = [{"rel_path": f["rel_path"], "archive_name": f["archive_name"], "sha256": f["sha256"]}
                   for f in m["files"]]
    except (KeyError, TypeError) as e:
        raise ArchiveError(2, f"manifest thiếu khóa: {e}")
    if generator != SCRIPT:
        raise ArchiveError(2, f"manifest sinh bởi {generator!r}, chỉ nhận {SCRIPT}; không tải, không ghi gì")
    check_dataset_ref(dataset)
    download_dir = require_under_work(download_dir, "--download-dir", work_root)
    if not entries:
        raise ArchiveError(2, "manifest không có file nào")
    for e in entries:                              # EVERY entry, before any download or write
        P.check_local_path(e["rel_path"])
        if e["archive_name"] != e["rel_path"].replace("/", "__"):
            raise ArchiveError(2, f"manifest: archive_name của {e['rel_path']} là {e['archive_name']!r}, mong đợi "
                                  f"{e['rel_path'].replace('/', '__')!r}; không tải, không ghi gì")
        if not isinstance(e["sha256"], str) or len(e["sha256"]) != 64:
            raise ArchiveError(2, f"manifest: sha256 không hợp lệ cho {e['rel_path']}")
    dest = os.path.abspath(dest)
    if os.path.lexists(dest) and (not os.path.isdir(dest) or is_link_or_reparse(dest)):
        raise ArchiveError(2, f"--dest không phải thư mục thường: {dest}")

    os.makedirs(download_dir, exist_ok=True)
    dl = tempfile.mkdtemp(prefix="restore-", dir=download_dir)
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
        target = os.path.join(dest, *e["rel_path"].split("/"))
        if os.path.lexists(target):
            if is_link_or_reparse(target) or not os.path.isfile(target) or sha256_file(target) != e["sha256"]:
                raise ArchiveError(3, f"{e['rel_path']} đã có ở đích với nội dung khác manifest; không ghi file nào")
            print(f"đã có: {e['rel_path']}")
        else:
            todo.append((e, target))
    for e, target in todo:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            _copy_exclusive(os.path.join(dl, e["archive_name"]), target)
        except FileExistsError:
            raise ArchiveError(3, f"{e['rel_path']} vừa xuất hiện trong lúc khôi phục; không ghi đè")
        if sha256_file(target) != e["sha256"]:
            raise ArchiveError(3, f"bản ghi {e['rel_path']} có sha256 khác manifest (file để lại để kiểm tra)")
        print(f"đã ghi: {e['rel_path']}")
    print(f"restore {dataset}: {len(todo)} file ghi mới, {len(entries) - len(todo)} file bỏ qua vì có sẵn cùng sha256 "
          f"(dest {dest})")
    return 0


# ---------------------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------------------
def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--src", required=True)
    s.add_argument("--staging", required=True)
    s.add_argument("--dataset", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--licence-note", required=True)
    u = sub.add_parser("upload")
    u.add_argument("--staging", required=True)
    u.add_argument("--dataset", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--staging", required=True)
    v.add_argument("--dataset", required=True)
    v.add_argument("--download-dir", required=True)
    v.add_argument("--manifest-out", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--manifest", required=True)
    r.add_argument("--download-dir", required=True)
    r.add_argument("--dest", required=True)
    return ap.parse_args(argv)


def main(argv=None, api=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        if args.cmd == "stage":
            return stage(args.src, args.staging, args.dataset, args.title, args.licence_note)
        api = api if api is not None else kaggle_api()
        if args.cmd == "upload":
            return upload(args.staging, args.dataset, api)
        if args.cmd == "verify":
            return verify(args.staging, args.dataset, args.download_dir, args.manifest_out, api, argv)
        return restore(os.path.abspath(args.manifest), args.download_dir, args.dest, api)
    except ArchiveError as e:
        print(f"archive_retrain_kaggle: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
