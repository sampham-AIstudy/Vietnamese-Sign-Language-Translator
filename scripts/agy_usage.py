#!/usr/bin/env python
"""Cân ngân sách hạn mức của agy trước khi giao việc (giống cổng của docs/prompts/usage_guard_addendum.md bên Claude).

Nguồn số liệu: `agy -p "/usage" --output-format json` (không tốn token). Hai nhóm model, mỗi nhóm có hạn mức 5h và tuần:
  gemini = Gemini Flash/Pro      claude = Claude Opus/Sonnet + GPT-OSS

Lệnh:
  status                                  tóm tắt hạn mức (giờ VN)
  choose <họ|id> <effort> <số-bước>       chọn (model, effort) vừa ngân sách; in "MODEL=.. EFFORT=.. GROUP=.." hoặc "WAIT ..."
        [--plan NN]                       exit 0 = có phương án, 20 = KHÔNG ĐỦ ngân sách (chưa chạy gì), 21 = không đọc được usage nhưng
                                          vẫn trả phương án nhỏ nhất (UNKNOWN)
  record <số-bước> [--note ghi-chú]       sau khi chạy: đo lại usage, ghi 1 dòng vào docs/agy_usage_ledger.csv
Cổng (cùng quy tắc bên Claude): dùng_5h + 1.0 × est ≤ 90 và dùng_tuần + est_tuần ≤ 95. Không bao giờ cố tình chạm giới hạn.
est lấy từ sổ đo thật (lớn nhất trong 3 dòng `ok` gần nhất cùng nhóm + effort). Chưa có số đo thì dùng GIÁ TRỊ KHỞI ĐẦU
CHƯA ĐO bên dưới (cố ý thận trọng) và đánh dấu "unmeasured".
"""
import csv, datetime as dt, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agy_pick_model as pm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "docs", "agy_usage_ledger.csv")
BEFORE = os.path.join(ROOT, "_work", "agy_usage_before.json")
HEAD = ["time_utc", "group", "model", "effort", "plan", "steps", "five_before", "five_after", "five_delta", "week_delta", "quality"]
FIVE_LIMIT, WEEK_LIMIT = 90.0, 95.0
LADDER = ["max", "xhigh", "high", "medium", "low"]
# GIÁ TRỊ KHỞI ĐẦU CHƯA ĐO: điểm % của cửa sổ 5h cho MỘT bước kế hoạch. Thay bằng số đo thật khi sổ có dữ liệu.
# Nhóm claude (Opus/Sonnet): ĐO 3/10 — Opus/high, 1 bước A1 = +77 điểm 5h (+41 tuần) trong ~8 phút rồi chạm 100% (CẬN DƯỚI). Các mức khác suy theo tỉ lệ, chưa đo.
DEFAULT_PER_STEP_BY_GROUP = {
    "gemini": {"low": 3.0, "medium": 5.0, "high": 12.0, "xhigh": 18.0, "max": 18.0},
    "claude": {"low": 25.0, "medium": 45.0, "high": 77.0, "xhigh": 100.0, "max": 100.0},
}
DEFAULT_WEEK_RATIO = 1.0  # chưa đo: coi 1 điểm 5h = 1 điểm tuần (thận trọng)
VN = dt.timezone(dt.timedelta(hours=7))


def fetch():
    try:
        r = subprocess.run(["agy", "-p", "/usage", "--output-format", "json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
        data = json.loads(r.stdout)
        out = {}
        for g in data["command"]["data"]["groups"]:
            name = "gemini" if "gemini" in g["name"].lower() else "claude"
            b = {x["window"]: x for x in g["buckets"]}
            out[name] = {
                "five_used": round(100 * (1 - b["5h"]["remaining_fraction"]), 1), "five_reset": b["5h"]["reset_time"],
                "week_used": round(100 * (1 - b["weekly"]["remaining_fraction"]), 1), "week_reset": b["weekly"]["reset_time"],
            }
        return out if out else None
    except Exception as e:  # noqa: BLE001
        print(f"[agy-usage] không đọc được /usage: {e}", file=sys.stderr)
        return None


def vn(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(VN).strftime("%H:%M %d/%m")


def read_ledger():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def estimate(group, effort, steps):
    rows = [r for r in read_ledger() if r["group"] == group and r["effort"] == effort and r["quality"].startswith("ok") and int(r["steps"]) > 0]
    rows = rows[-3:]
    if rows:
        per = max(float(r["five_delta"]) / int(r["steps"]) for r in rows)
        wk = max(float(r["week_delta"]) / int(r["steps"]) for r in rows)
        return per * steps, wk * steps, "measured"
    per = DEFAULT_PER_STEP_BY_GROUP[group][effort]
    ratio = 0.55 if group == "claude" else DEFAULT_WEEK_RATIO  # claude đo được tuần/5h ≈ 0.54
    return per * steps, per * ratio * steps, "unmeasured"


def candidates(pref, effort):
    """Danh sách (họ, effort) theo thứ tự ưu tiên: hạ effort trước, rồi đổi họ."""
    start = LADDER.index(effort) if effort in LADDER else LADDER.index("high")
    ladder = LADDER[start:]
    chain = {"gemini": ["gemini", "sonnet", "opus"], "opus": ["opus", "sonnet", "gemini"],
             "sonnet": ["sonnet", "gemini", "opus"], "claude": ["opus", "sonnet", "gemini"], "auto": ["gemini", "sonnet", "opus"]}
    fams = chain.get(pref) or [pref, "sonnet", "gemini"]
    return [(f, e) for f in fams for e in ladder]


def group_of(fam):
    return "gemini" if fam.startswith("gemini") else "claude"


def cmd_status():
    u = fetch()
    if not u:
        print("hạn mức agy: KHÔNG BIẾT")
        return 21
    for g, v in u.items():
        print(f"{g:7s} 5h dùng {v['five_used']:5.1f}% (reset {vn(v['five_reset'])}) | tuần dùng {v['week_used']:5.1f}% (reset {vn(v['week_reset'])})")
    return 0


def cmd_choose(pref, effort, steps, plan):
    u = fetch()
    os.makedirs(os.path.dirname(BEFORE), exist_ok=True)
    cands = candidates(pref, effort)
    if pref not in ("gemini", "opus", "sonnet", "claude", "auto"):  # id cụ thể: thử đúng id trước
        fam = pm.parse(pref)["fam"]
        cands = [(pref, effort)] + candidates(fam if fam in ("gemini", "opus", "sonnet") else "auto", effort)
    if u is None:  # không biết hạn mức: chỉ phương án rẻ nhất, như quy tắc "KHÔNG BIẾT" bên Claude
        fam = cands[0][0] if cands[0][0] in ("gemini", "opus", "sonnet") else "gemini"
        mid, eff = pm.pick("sonnet" if fam == "opus" else fam, "low")
        print(f"MODEL={mid} EFFORT={eff} GROUP={group_of(fam)} NOTE=hạn-mức-không-biết:chỉ-chạy-nhỏ-nhất")
        json.dump({"usage": None, "group": group_of(fam), "model": mid, "effort": "low", "plan": plan}, open(BEFORE, "w"))
        return 21
    # nhóm đã dùng tuần > 80% bị đẩy xuống cuối để dồn sang nhóm còn dư (cân bằng nhẹ)
    cands.sort(key=lambda c: u.get(group_of(c[0]), {}).get("week_used", 0) > 80)
    why, waits = [], []
    for fam, eff in cands:
        g = group_of(fam)
        if g not in u:
            continue
        mid, flag = pm.pick(fam, eff) if fam in ("gemini", "opus", "sonnet") else (fam, "")
        e5, ew, src = estimate(g, eff if eff in LADDER else "high", steps)
        ok5 = u[g]["five_used"] + e5 <= FIVE_LIMIT
        okw = u[g]["week_used"] + ew <= WEEK_LIMIT
        if ok5 and okw:
            json.dump({"usage": u, "group": g, "model": mid, "effort": eff, "plan": plan, "est": e5, "src": src}, open(BEFORE, "w"))
            print(f"MODEL={mid} EFFORT={flag or eff} GROUP={g} EST5H={e5:.1f} SRC={src} "
                  f"USED5H={u[g]['five_used']} USEDWEEK={u[g]['week_used']}")
            return 0
        why.append((g, eff, "5h" if not ok5 else "tuần"))
        waits.append(u[g]["five_reset"] if not ok5 else u[g]["week_reset"])
    soonest = min(waits) if waits else "?"
    print(f"WAIT: không phương án nào vừa ngân sách (đã thử {len(why)}); sớm nhất có thể tiếp tục lúc {vn(soonest) if waits else '?'} giờ VN")
    return 20


def cmd_record(steps, note):
    try:
        b = json.load(open(BEFORE, encoding="utf-8"))
    except OSError:
        print("[agy-usage] không có _work/agy_usage_before.json — bỏ qua ghi sổ")
        return 0
    after = fetch()
    g = b["group"]
    if not b.get("usage") or not after or g not in after:
        q, f0, f1, d5, dw = "stale (không đọc được usage trước/sau)", "", "", 0, 0
    else:
        f0, f1 = b["usage"][g]["five_used"], after[g]["five_used"]
        w0, w1 = b["usage"][g]["week_used"], after[g]["week_used"]
        d5, dw = round(f1 - f0, 1), round(w1 - w0, 1)
        q = "ok" if d5 >= 0 and dw >= 0 and b["usage"][g]["five_reset"] == after[g]["five_reset"] else "stale (cửa sổ 5h đã reset giữa chừng)"
        if note:
            q += f" {note}"
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(HEAD)
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), g, b["model"], b["effort"], b["plan"], steps, f0, f1, d5, dw, q])
    print(f"[agy-usage] sổ đo: nhóm {g}, 5h {f0}->{f1} (+{d5}), tuần +{dw}, {q}")
    return 0


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 0
    if a[0] == "status":
        return cmd_status()
    if a[0] == "choose":
        plan = a[a.index("--plan") + 1] if "--plan" in a else ""
        return cmd_choose(a[1], a[2], int(a[3]), plan)
    if a[0] == "record":
        note = a[a.index("--note") + 1] if "--note" in a else ""
        return cmd_record(int(a[1]), note)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
