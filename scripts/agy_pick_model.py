#!/usr/bin/env python
"""Chọn model + effort cho agy từ danh sách THỰC TẾ (`agy models`), nên tự dùng bản mới nhất khi có (gemini 3.8 -> 4.0 ...).

Dùng:  agy_pick_model.py <lựa chọn> [effort]     in ra: "<model-id> <effort-flag>"
       agy_pick_model.py --list                  in bảng model mới nhất mỗi họ

<lựa chọn>:
  gemini   gemini mới nhất (xếp theo phiên bản trước, rồi pro > flash)
  opus     claude opus mới nhất           sonnet  claude sonnet mới nhất
  claude   như opus                       auto    = gemini
  <id>     id đầy đủ trong `agy models` (vd gemini-3.1-pro-high) — dùng nguyên, effort theo hậu tố của id
effort: low | medium | high | xhigh | max (mặc định high). Model chỉ có vài mức thì lấy mức gần nhất (ưu tiên cao hơn);
xhigh/max dùng mức cao nhất của model và truyền thêm --effort.
"""
import functools, re, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LEVELS = ["low", "medium", "high"]
TIER = {"flash": 0, "pro": 1}


@functools.lru_cache(maxsize=1)
def models():
    r = subprocess.run(["agy", "models"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"agy models lỗi: {r.stderr.strip()}")
    ids = [l.split("\t")[0].strip() for l in r.stdout.splitlines() if "\t" in l]
    if not ids:
        sys.exit("agy models không trả về model nào")
    return ids


def parse(mid):
    m = re.match(r"^(?P<base>.+?)(?:-(?P<eff>low|medium|high|xhigh|max))?$", mid)
    base, eff = m.group("base"), m.group("eff")
    nums = tuple(int(x) for x in re.findall(r"(?<![a-z])\d+", base))
    if base.startswith("gemini"):
        fam = "gemini"
        tier = next((t for t in TIER if t in base), "")
    elif base.startswith("claude-"):
        fam = base.split("-")[1]
        tier = ""
    else:
        fam, tier = base.split("-")[0], ""
    return {"id": mid, "base": base, "eff": eff, "fam": fam, "ver": nums, "tier": TIER.get(tier, 0)}


def best_base(ps, fam):
    c = [p for p in ps if p["fam"] == fam]
    if not c:
        sys.exit(f"không có model họ '{fam}' trong agy models")
    return max(c, key=lambda p: (p["ver"], p["tier"]))["base"]


def pick(choice, effort):
    ids = models()
    ps = [parse(i) for i in ids]
    if choice in ids:
        p = parse(choice)
        return choice, p["eff"] or ""
    fam = {"auto": "gemini", "claude": "opus"}.get(choice, choice)
    base = best_base(ps, fam)
    variants = {p["eff"]: p["id"] for p in ps if p["base"] == base}
    want = effort if effort in LEVELS else "high"
    order = LEVELS[LEVELS.index(want):] + LEVELS[:LEVELS.index(want)][::-1]
    got = next((e for e in order if e in variants), None)
    if got is None:  # model không có hậu tố effort
        return variants.get(None, next(iter(variants.values()))), effort if effort in ("xhigh", "max") else ""
    return variants[got], effort if effort in ("xhigh", "max") else got


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--list":
        ps = [parse(i) for i in models()]
        for fam in sorted({p["fam"] for p in ps}):
            b = best_base(ps, fam)
            print(f"{fam:8s} -> {b}  (mức: {', '.join(sorted(p['eff'] or '-' for p in ps if p['base'] == b))})")
        return 0
    mid, eff = pick(a[0], a[1] if len(a) > 1 else "high")
    print(mid, eff)
    return 0


if __name__ == "__main__":
    sys.exit(main())
