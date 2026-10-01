"""Read-only checker of restored local data (plan 12, docs/plans/12-khoi-phuc-du-lieu.md §3.1).

Checks the local files listed in a spec (docs/recovery/expected_local_data.json) against references that are already in
the repo (committed manifests / JSON reports / CSV splits / git blobs). Writes ONE file: the JSON given by --out.
Never writes, moves or deletes data; no network; does not import backend/ or src/.

Item types (spec "items"[].type):
  sha256       file under <dir>; sha256 == every expected_from source (manifest local_path / json key / git blob / value)
  count        number of files matching <glob> under <dir> (or non-empty lines of <dir>/<file> if count_mode=lines)
               == expect (compare "eq" | "ge"); optional expect_groups = number of distinct parent dirs
  video_frames videos <glob> under <dir>: every file_name of the reference CSVs present; CAP_PROP_FRAME_COUNT == frames
               column; width/height == columns (cv2, same measure as scripts/build_recording_groups.py:36-37); optional
               single-file facts {frames,fps,width,height} from a JSON key
  csv_ids      every id of a reference CSV column is present in <dir>/<file> column id_col; reference row count == expect
  exists_only  <dir>/<file> exists (file, or non-empty dir); no reference hash -> status "unverifiable"
Status per item: ok | missing | mismatch | unverifiable.
Exit code: 0 = no missing/mismatch among required items; 3 = at least one; 2 = argument/spec/reference error (no output).

--out must be inside <root>/_work/ or <root>/reports/data_recovery_2026-10-01/; --dir-override <id>=<dir> only inside
<root>/_work/ (to check an extracted copy BEFORE moving it into place). Items with "private_names": true never list
file/clip names in an --out outside _work/ (counts only).

Usage:
  python scripts/check_restored_data.py --spec docs/recovery/expected_local_data.json --out _work/_plan12_tmp/inv.json
      [--only <id> ...] [--dir-override <id>=_work/...]
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TYPES = {"sha256", "count", "video_frames", "csv_ids", "exists_only"}
OUT_DIRS = ("_work", os.path.join("reports", "data_recovery_2026-10-01"))
OVERRIDE_DIR = "_work"
MAX_EXAMPLES = 20


class SpecError(Exception):
    pass


# ---------------------------------------------------------------- spec + references

def validate_spec(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("items"), list) or not spec["items"]:
        raise SpecError("spec must be an object with a non-empty 'items' list")
    seen = set()
    for it in spec["items"]:
        if not isinstance(it, dict):
            raise SpecError("item must be an object")
        for k in ("id", "group", "type", "dir", "expect_source"):
            if not isinstance(it.get(k), str) or not it[k]:
                raise SpecError(f"item {it.get('id')!r}: missing string field {k!r}")
        if not isinstance(it.get("required"), bool):
            raise SpecError(f"item {it['id']}: 'required' must be true/false")
        if it["id"] in seen:
            raise SpecError(f"duplicate item id {it['id']}")
        seen.add(it["id"])
        t = it["type"]
        if t not in TYPES:
            raise SpecError(f"item {it['id']}: unknown type {t!r}")
        need = {"sha256": ("file", "expected_from"), "count": ("expect",), "video_frames": (),
                "csv_ids": ("file", "id_col", "ref"), "exists_only": ("file",)}[t]
        for k in need:
            if k not in it:
                raise SpecError(f"item {it['id']}: type {t} needs {k!r}")
        if t == "sha256" and (not isinstance(it["expected_from"], list) or not it["expected_from"]):
            raise SpecError(f"item {it['id']}: expected_from must be a non-empty list")
        if t == "count" and it.get("count_mode", "glob") == "glob" and "glob" not in it:
            raise SpecError(f"item {it['id']}: count needs 'glob'")
        if t == "count" and it.get("count_mode") == "lines" and "file" not in it:
            raise SpecError(f"item {it['id']}: count_mode=lines needs 'file'")
        if t == "count" and it.get("compare", "eq") not in ("eq", "ge"):
            raise SpecError(f"item {it['id']}: compare must be eq|ge")
        if t == "video_frames":
            if not isinstance(it.get("refs", []), list) or not isinstance(it.get("facts", []), list):
                raise SpecError(f"item {it['id']}: refs/facts must be lists")
            if not it.get("refs") and not it.get("facts"):
                raise SpecError(f"item {it['id']}: video_frames needs refs and/or facts")
            for r in it.get("refs", []):
                if "csv" not in r or "file_col" not in r:
                    raise SpecError(f"item {it['id']}: each ref needs csv + file_col")
        if t == "csv_ids" and not ("csv" in it["ref"] and "id_col" in it["ref"]):
            raise SpecError(f"item {it['id']}: ref needs csv + id_col")
    return spec["items"]


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _load_json(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        raise SpecError(f"reference file not found: {rel}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def resolve_source(root, src):
    """One expectation source -> value. Raises SpecError if the reference cannot be read."""
    if not isinstance(src, dict):
        raise SpecError(f"bad source {src!r}")
    if "value" in src:
        if not src.get("source"):
            raise SpecError(f"literal value {src['value']!r} without 'source' (file:line)")
        return src["value"]
    if "json" in src:
        cur = _load_json(root, src["json"])
        for k in src["key"].split("."):
            if not isinstance(cur, dict) or k not in cur:
                raise SpecError(f"key {src['key']!r} not in {src['json']}")
            cur = cur[k]
        return cur
    if "manifest" in src:
        for f in _load_json(root, src["manifest"]).get("files", []):
            if f.get("local_path") == src["local_path"]:
                return f["sha256"]
        raise SpecError(f"local_path {src['local_path']!r} not in {src['manifest']}")
    if "git_blob" in src:
        p = subprocess.run(["git", "-C", root, "cat-file", "blob", src["git_blob"]], capture_output=True)
        if p.returncode != 0:
            raise SpecError(f"git blob {src['git_blob']!r} not readable")
        return hashlib.sha256(p.stdout).hexdigest()
    raise SpecError(f"unknown source kind {sorted(src)}")


def resolve_expectations(root, it):
    """All expectations of an item, resolved before any check (reference error -> SpecError -> exit 2)."""
    r = {}
    t = it["type"]
    if t == "sha256":
        r["expected_sha256"] = [resolve_source(root, s) for s in it["expected_from"]]
    if t == "count":
        r["expect"] = resolve_source(root, it["expect"])
        if "expect_groups" in it:
            r["expect_groups"] = resolve_source(root, it["expect_groups"])
    if t == "video_frames":
        for ref in it.get("refs", []):
            if not os.path.isfile(os.path.join(root, ref["csv"])):
                raise SpecError(f"reference csv not found: {ref['csv']}")
        if it.get("min_files_from_ref") and not os.path.isfile(os.path.join(root, it["min_files_from_ref"])):
            raise SpecError(f"reference csv not found: {it['min_files_from_ref']}")
        r["facts"] = [resolve_source(root, f["expect"]) for f in it.get("facts", [])]
    if t == "csv_ids":
        if not os.path.isfile(os.path.join(root, it["ref"]["csv"])):
            raise SpecError(f"reference csv not found: {it['ref']['csv']}")
        if "expect_ref_rows" in it:
            r["expect_ref_rows"] = resolve_source(root, it["expect_ref_rows"])
    return r


# ---------------------------------------------------------------- checks

def _read_csv(path, flt=None):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if flt:
        rows = [r for r in rows if all(r.get(k) == v for k, v in flt.items())]
    return rows


def video_props(path):
    import cv2
    cap = cv2.VideoCapture(path)
    try:
        return {"frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), "fps": float(cap.get(cv2.CAP_PROP_FPS)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    finally:
        cap.release()


def _files(base, pattern):
    return sorted(os.path.relpath(p, base).replace(os.sep, "/")
                  for p in glob.glob(os.path.join(base, pattern), recursive=True) if os.path.isfile(p))


def check_sha256(base, it, exp):
    path = os.path.join(base, it["file"])
    vals = exp["expected_sha256"]
    res = {"expected_sha256": vals[0], "reference_disagreement": len(set(vals)) > 1}
    if not os.path.isfile(path):
        return {**res, "status": "missing"}
    s = _sha256_file(path)
    ok = (not res["reference_disagreement"]) and s == vals[0]
    return {**res, "sha256": s, "size_bytes": os.path.getsize(path), "status": "ok" if ok else "mismatch"}


def check_count(base, it, exp):
    res = {"expected": exp["expect"], "compare": it.get("compare", "eq")}
    if it.get("count_mode") == "lines":
        p = os.path.join(base, it["file"])
        if not os.path.isfile(p):
            return {**res, "status": "missing", "count": 0}
        with open(p, encoding="utf-8") as f:
            n = sum(1 for line in f if line.strip())
        groups = None
    else:
        if not os.path.isdir(base):
            return {**res, "status": "missing", "count": 0}
        files = _files(base, it["glob"])
        n = len(files)
        groups = len({os.path.dirname(f) for f in files})
    ok = n == exp["expect"] if res["compare"] == "eq" else n >= exp["expect"]
    res["count"] = n
    if "expect_groups" in exp:
        res["groups"], res["expected_groups"] = groups, exp["expect_groups"]
        ok = ok and groups == exp["expect_groups"]
    return {**res, "status": "ok" if ok else "mismatch"}


def check_video_frames(base, it, exp, root, show_names):
    res = {}
    if not os.path.isdir(base):
        return {"status": "missing", "n_files": 0}
    on_disk = set(_files(base, it.get("glob", "*.mp4")))
    res["n_files"] = len(on_disk)
    ref_files, frames_ref, size_ref = [], {}, {}
    for ref in it.get("refs", []):
        for row in _read_csv(os.path.join(root, ref["csv"]), ref.get("filter")):
            name = row[ref["file_col"]]
            if name not in frames_ref and name not in size_ref:
                ref_files.append(name)
            if ref.get("frames_col"):
                frames_ref[name] = int(row[ref["frames_col"]])
            if ref.get("width_col"):
                size_ref[name] = (int(row[ref["width_col"]]), int(row[ref["height_col"]]))
    ref_files = list(dict.fromkeys(ref_files))
    missing = [f for f in ref_files if f not in on_disk]
    props = {}

    def prop(name):
        if name not in props:
            props[name] = video_props(os.path.join(base, name))
        return props[name]

    frame_mm, size_mm, n_size = [], [], 0
    for name in ref_files:
        if name not in on_disk:
            continue
        if name in frames_ref and prop(name)["frames"] != frames_ref[name]:
            frame_mm.append({"file": name, "expected": frames_ref[name], "actual": prop(name)["frames"]})
        if name in size_ref:
            n_size += 1
            got = (prop(name)["width"], prop(name)["height"])
            if got != size_ref[name]:
                size_mm.append({"file": name, "expected": list(size_ref[name]), "actual": list(got)})
    res.update({"n_ref_files": len(ref_files), "n_missing_files": len(missing), "n_frame_checked":
                sum(1 for f in ref_files if f in frames_ref and f in on_disk), "n_frame_mismatch": len(frame_mm),
                "n_size_checked": n_size, "n_size_mismatch": len(size_mm)})
    ge_ok = True
    if it.get("min_files_from_ref"):
        n_rows = len(_read_csv(os.path.join(root, it["min_files_from_ref"])))
        ge_ok = len(on_disk) >= n_rows
        res.update({"min_files_ref_rows": n_rows, "n_files_ge_ref_rows": ge_ok})
    facts, facts_mm, facts_missing = [], False, False
    for f, want in zip(it.get("facts", []), exp["facts"]):
        if f["file"] not in on_disk:
            facts.append({"file": f["file"] if show_names else None, "status": "missing", "expected": want})
            facts_missing = True
            continue
        got = {k: prop(f["file"])[k] for k in want}
        st = "ok" if got == want else "mismatch"
        facts_mm |= st == "mismatch"
        facts.append({"file": f["file"] if show_names else None, "status": st, "expected": want, "actual": got})
    res["facts"] = facts
    if show_names:
        res.update({"missing_file_examples": missing[:MAX_EXAMPLES], "frame_mismatch_examples": frame_mm[:MAX_EXAMPLES],
                    "size_mismatch_examples": size_mm[:MAX_EXAMPLES]})
    else:
        res["examples_redacted"] = True
    if frame_mm or size_mm or facts_mm:
        res["status"] = "mismatch"
    elif missing or facts_missing or not ge_ok:
        res["status"] = "missing"
    else:
        res["status"] = "ok"
    return res


def check_csv_ids(base, it, exp, root, show_names):
    ref_rows = _read_csv(os.path.join(root, it["ref"]["csv"]))
    ref_ids = list(dict.fromkeys(r[it["ref"]["id_col"]] for r in ref_rows))
    res = {"n_ref_rows": len(ref_rows), "n_ref_ids": len(ref_ids)}
    rows_ok = True
    if "expect_ref_rows" in exp:
        res["expected_ref_rows"] = exp["expect_ref_rows"]
        rows_ok = len(ref_rows) == exp["expect_ref_rows"]
    p = os.path.join(base, it["file"])
    if not os.path.isfile(p):
        return {**res, "status": "missing", "target_exists": False}
    have = {r[it["id_col"]] for r in _read_csv(p)}
    missing = [i for i in ref_ids if i not in have]
    res.update({"target_exists": True, "n_target_rows": len(have), "n_missing_ids": len(missing)})
    if show_names:
        res["missing_id_examples"] = missing[:MAX_EXAMPLES]
    else:
        res["examples_redacted"] = True
    res["status"] = "mismatch" if not rows_ok else ("missing" if missing else "ok")
    return res


def check_exists_only(base, it):
    p = os.path.join(base, it["file"])
    if os.path.isfile(p):
        return {"status": "unverifiable", "verified": "no_reference_hash", "size_bytes": os.path.getsize(p)}
    if os.path.isdir(p) and os.listdir(p):
        n = sum(len(fs) for _, _, fs in os.walk(p))
        return {"status": "unverifiable", "verified": "no_reference_hash", "n_files": n}
    return {"status": "missing", "verified": "no_reference_hash"}


# ---------------------------------------------------------------- CLI

def _inside(path, parent):
    path = os.path.normcase(os.path.realpath(path))
    parent = os.path.normcase(os.path.realpath(parent))
    try:
        return os.path.commonpath([path, parent]) == parent
    except ValueError:  # different drives
        return False


def _git(args):
    try:
        p = subprocess.run(["git", "--no-optional-locks", "-C", REPO] + args, capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else None
    except OSError:
        return None


def _rel(p, root):
    try:
        r = os.path.relpath(os.path.abspath(p), root)
    except ValueError:
        return p
    return p if r.startswith("..") else r.replace(os.sep, "/")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="+", action="extend", default=[])
    ap.add_argument("--dir-override", action="append", default=[])
    ap.add_argument("--root", default=REPO, help="project root (default: this repo); paths in the spec are relative to it")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    def fail(msg):
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    spec_path = args.spec if os.path.isabs(args.spec) else os.path.join(root, args.spec)
    try:
        with open(spec_path, encoding="utf-8") as f:
            items = validate_spec(json.load(f))
    except (OSError, ValueError, SpecError) as e:
        return fail(f"spec: {e}")
    out = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    if not any(_inside(out, os.path.join(root, d)) for d in OUT_DIRS) or os.path.isdir(out):
        return fail(f"--out must be a file inside {' or '.join(d + '/' for d in OUT_DIRS)} of {root}")
    ids = {i["id"] for i in items}
    unknown = [i for i in args.only if i not in ids]
    if unknown:
        return fail(f"--only: unknown item(s) {unknown}")
    overrides = {}
    for ov in args.dir_override:
        if "=" not in ov:
            return fail(f"--dir-override must be <id>=<dir>: {ov!r}")
        k, v = ov.split("=", 1)
        if k not in ids:
            return fail(f"--dir-override: unknown item {k!r}")
        vabs = v if os.path.isabs(v) else os.path.join(root, v)
        if not _inside(vabs, os.path.join(root, OVERRIDE_DIR)):
            return fail(f"--dir-override: {v!r} is not inside {OVERRIDE_DIR}/")
        overrides[k] = vabs
    selected = [i for i in items if not args.only or i["id"] in args.only]
    try:
        expectations = {it["id"]: resolve_expectations(root, it) for it in selected}
    except SpecError as e:
        return fail(f"reference: {e}")

    show_names = _inside(out, os.path.join(root, "_work"))
    results = []
    for it in selected:
        base = overrides.get(it["id"], os.path.join(root, it["dir"]))
        exp = expectations[it["id"]]
        names = show_names or not it.get("private_names", False)
        t = it["type"]
        if t == "sha256":
            r = check_sha256(base, it, exp)
        elif t == "count":
            r = check_count(base, it, exp)
        elif t == "video_frames":
            r = check_video_frames(base, it, exp, root, names)
        elif t == "csv_ids":
            r = check_csv_ids(base, it, exp, root, names)
        else:
            r = check_exists_only(base, it)
        row = {"id": it["id"], "group": it["group"], "type": t, "required": it["required"],
               "expect_source": it["expect_source"], "dir": _rel(base, root), "dir_overridden": it["id"] in overrides}
        row.update(r)
        results.append(row)
        print(f"{it['id']:<40} {row['status']:<13} required={it['required']}")

    failed = [r["id"] for r in results if r["required"] and r["status"] in ("missing", "mismatch")]
    rel_spec = _rel(spec_path, REPO)
    dirty = _git(["status", "--porcelain", "--", "scripts/check_restored_data.py", rel_spec])
    cmd = ["python", "scripts/check_restored_data.py"] + [
        _rel(a, root) if os.path.isabs(a) else a for a in (argv if argv is not None else sys.argv[1:])]
    report = {
        "generated_by": {"command": " ".join(cmd), "git_commit": _git(["rev-parse", "HEAD"]),
                         "code_dirty": None if dirty is None else bool(dirty)},
        "spec": rel_spec, "only": args.only or None,
        "summary": {s: sum(1 for r in results if r["status"] == s) for s in ("ok", "missing", "mismatch", "unverifiable")},
        "required_failed": failed, "exit_code": 3 if failed else 0, "items": results,
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"summary {report['summary']} required_failed={failed} -> {_rel(out, root)}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
