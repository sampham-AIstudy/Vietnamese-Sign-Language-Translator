#!/usr/bin/env python
"""Rào chắn cơ học cho agy (Coder). Không phụ thuộc vào việc agy "ngoan".

Chế độ:
  snapshot <plan.md> <dir>   chụp trạng thái TRƯỚC khi agy chạy (file của người dùng, hash, phạm vi cho phép)
  staged   <dir>             kiểm tra thứ đang staged (gọi từ pre-commit hook)
  range    <dir>             kiểm tra mọi commit từ mốc snapshot tới HEAD (bắt cả `--no-verify`)
  worktree <dir>             kiểm tra thay đổi chưa commit: file của người dùng có bị đụng không, file ngoài phạm vi

Phạm vi cho phép = khối ```scope trong kế hoạch (mỗi dòng 1 glob; `*` khớp cả '/'; kết thúc bằng '/' = cả thư mục).
Không có khối scope → chỉ áp luật cứng (file của người dùng, test, bí mật, dữ liệu) và cảnh báo "ngoài phạm vi: không xác định".
Mã thoát: 0 sạch, 1 vi phạm (BLOCK), 0 + in WARN nếu chỉ cảnh báo.
"""
import fnmatch, hashlib, json, os, re, subprocess, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

BRANCH = "feat/vslt-complete"
ALWAYS_OK = ["docs/plans/*-progress.md", "docs/agy_usage_ledger.csv"]
SECRET_FILES = re.compile(r"(^|/)(kaggle\.json|\.env[^/]*|id_rsa[^/]*|[^/]*\.pem)$")
BIG_BINARY = re.compile(r"\.(pt|pth|ckpt|mp4|avi|mov|webm|mkv)$", re.I)
NEVER_DELETE = ("data/", "reports/", "checkpoints/", "results/")
TEST_PATH = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*\.(test|spec)\.[jt]sx?$)")
SKIP_ADDED = re.compile(r"@pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|unittest\.skip|\b(xit|xdescribe|xtest)\(|\.skip\(")
TEST_DEF = re.compile(r"^\s*(def test_|(async\s+)?(it|test)\(|(it|test)\.each)")
ASSERT = re.compile(r"\bassert\b|\bexpect\(|\.assert[A-Z_]")
SECRET_ADDED = re.compile(r"(kaggle_key|api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.I)
FAKE_ADDED = re.compile(r"Math\.random\(")
SOURCE_PATH = re.compile(r"^(src|backend|frontend/(src|app|components))/")


def git(*args, check=True):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"[agy-guard] git {' '.join(args)} lỗi: {r.stderr.strip()}")
    return r.stdout


def porcelain():
    out = git("status", "--porcelain", "-z")
    ents, parts = {}, out.split("\0")
    i = 0
    while i < len(parts):
        e = parts[i]
        i += 1
        if len(e) < 4:
            continue
        st, path = e[:2], e[3:]
        if st[0] in "RC":
            i += 1  # bỏ qua tên cũ
        ents[path] = st
    return ents


def hash_path(p):
    if not os.path.exists(p):
        return "MISSING"
    h = hashlib.sha1()
    if os.path.isdir(p):
        for root, dirs, files in os.walk(p):
            dirs.sort()
            for f in sorted(files):
                fp = os.path.join(root, f)
                try:
                    s = os.stat(fp)
                    h.update(f"{os.path.relpath(fp, p)}|{s.st_size}|{s.st_mtime_ns}\n".encode())
                except OSError:
                    pass
        return "dir:" + h.hexdigest()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_scope(plan):
    try:
        txt = open(plan, encoding="utf-8").read()
    except OSError:
        return []
    m = re.search(r"```scope\s*\n(.*?)```", txt, re.S)
    if not m:
        return []
    return [l.strip() for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]


def match(path, pats):
    for p in pats:
        if p.endswith("/") and (path.startswith(p) or path + "/" == p):
            return True
        if fnmatch.fnmatch(path, p) or path == p:
            return True
    return False


def in_protected(path, protected):
    path = path.rstrip("/")
    for p in protected:
        q = p.rstrip("/")
        if path == q or path.startswith(q + "/") or q.startswith(path + "/"):
            return True
    return False


INTEGRITY = ["scripts/agy_guard.py", "scripts/agy_code.sh", "scripts/agy_usage.py", "scripts/agy_pick_model.py", "scripts/githooks"]


def integrity_hashes():
    h = {p: hash_path(p) for p in INTEGRITY}
    h["git-config:core.hooksPath"] = git("config", "--local", "--get", "core.hooksPath", check=False).strip()
    return h


def load(d):
    L = lambda n: [l for l in open(os.path.join(d, n), encoding="utf-8").read().split("\n") if l]
    return {
        "protected": L("protected.txt"), "scope": L("scope.txt"),
        "base": open(os.path.join(d, "base"), encoding="utf-8").read().strip(),
        "hashes": json.load(open(os.path.join(d, "hashes.json"), encoding="utf-8")),
        "porcelain": json.load(open(os.path.join(d, "porcelain.json"), encoding="utf-8")),
    }


def diff_files(diff_args):
    out = git("diff", "--name-status", "-z", "--no-renames", *diff_args)
    parts = [x for x in out.split("\0") if x]
    return [(parts[i], parts[i + 1]) for i in range(0, len(parts) - 1, 2)]


def check_diff(diff_args, snap):
    block, warn = [], []
    scope = snap["scope"]
    br = git("branch", "--show-current").strip()
    if br != BRANCH:
        block.append(f"sai nhánh: '{br}' (phải là {BRANCH})")
    for st, f in diff_files(diff_args):
        if in_protected(f, snap["protected"]):
            block.append(f"{f}: là thay đổi chưa commit của NGƯỜI DÙNG — không được commit")
        if SECRET_FILES.search(f) or BIG_BINARY.search(f):
            block.append(f"{f}: file bí mật / video / checkpoint không được commit")
        if st == "D" and (f.startswith(NEVER_DELETE) or TEST_PATH.search(f)):
            block.append(f"{f}: xóa file dữ liệu/báo cáo/checkpoint/test bị cấm")
        if scope:
            if not match(f, scope + ALWAYS_OK):
                block.append(f"{f}: NGOÀI phạm vi kế hoạch (scope)")
        elif not match(f, ALWAYS_OK):
            warn.append(f"{f}: kế hoạch không có khối ```scope — không xác định được có đúng phạm vi không")
        if st == "D":
            continue
        patch = git("diff", "-U0", "--no-renames", *diff_args, "--", f, check=False)
        added = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
        for l in added:
            if SECRET_ADDED.search(l):
                block.append(f"{f}: dòng thêm có dạng bí mật/token: {l.strip()[:60]}")
                break
        if SOURCE_PATH.match(f) and not TEST_PATH.search(f):
            if any(FAKE_ADDED.search(l) for l in added):
                block.append(f"{f}: thêm Math.random() trong mã nguồn (cấm kết quả giả)")
        if TEST_PATH.search(f):
            if any(SKIP_ADDED.search(l) for l in added):
                block.append(f"{f}: thêm skip/xfail vào test")
            if sum(bool(TEST_DEF.match(l)) for l in removed) > sum(bool(TEST_DEF.match(l)) for l in added):
                block.append(f"{f}: số test bị giảm (xóa/đổi tên test nhiều hơn thêm)")
            if sum(bool(ASSERT.search(l)) for l in removed) > sum(bool(ASSERT.search(l)) for l in added):
                block.append(f"{f}: số assert bị giảm (nghi nới lỏng test)")
    return block, warn


def report(block, warn, title):
    for w in warn:
        print(f"[agy-guard] WARN  {w}")
    for b in block:
        print(f"[agy-guard] BLOCK {b}", file=sys.stderr)
    if block:
        print(f"[agy-guard] {title}: {len(block)} vi phạm", file=sys.stderr)
        return 1
    print(f"[agy-guard] {title}: sạch ({len(warn)} cảnh báo)")
    return 0


def main():
    mode = sys.argv[1]
    if mode == "snapshot":
        plan, d = sys.argv[2], sys.argv[3]
        os.makedirs(d, exist_ok=True)
        ents = {p: s for p, s in porcelain().items() if not p.startswith("_work/")}
        w = lambda n, s: open(os.path.join(d, n), "w", encoding="utf-8", newline="\n").write(s)
        w("protected.txt", "\n".join(ents) + "\n")
        w("scope.txt", "\n".join(read_scope(plan)) + "\n")
        w("base", git("rev-parse", "HEAD").strip())
        w("hashes.json", json.dumps({p: hash_path(p) for p in ents}))
        w("integrity.json", json.dumps(integrity_hashes()))
        w("porcelain.json", json.dumps(ents))
        print(f"[agy-guard] snapshot: {len(ents)} đường dẫn của người dùng được bảo vệ, scope={len(read_scope(plan))} mẫu")
        return 0
    snap = load(sys.argv[2])
    if mode == "staged":
        b, w = check_diff(["--cached"], snap)
        return report(b, w, "pre-commit")
    if mode == "range":
        b, w = check_diff([f"{snap['base']}..HEAD"], snap)
        return report(b, w, "các commit của agy")
    if mode == "worktree":
        block, warn = [], []
        for p, h in snap["hashes"].items():
            if hash_path(p) != h:
                block.append(f"{p}: file/thư mục CỦA NGƯỜI DÙNG đã bị agy thay đổi trong lúc chạy")
        before = json.load(open(os.path.join(sys.argv[2], "integrity.json"), encoding="utf-8"))
        for k, v in integrity_hashes().items():
            if before.get(k) != v:
                block.append(f"{k}: rào chắn/cấu hình guard bị thay đổi trong lúc agy chạy (cấm)")
        now = {p: s for p, s in porcelain().items() if not p.startswith("_work/")}
        for p, s in now.items():
            if p in snap["porcelain"] or in_protected(p, snap["protected"]):
                continue
            if snap["scope"] and not match(p, snap["scope"] + ALWAYS_OK):
                block.append(f"{p}: thay đổi chưa commit NGOÀI phạm vi ({s.strip()})")
            elif not snap["scope"]:
                warn.append(f"{p}: thay đổi mới ({s.strip()}), không có scope để đối chiếu")
        return report(block, warn, "working tree")
    sys.exit("chế độ không hợp lệ")


if __name__ == "__main__":
    sys.exit(main())
