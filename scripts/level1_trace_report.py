#!/usr/bin/env python
"""
Plan 15 lần sửa 6 W3: diagnosis of a `level1_demo.py --trace-windows` run (session U3, §4) by the hypotheses M0-M4 of
§2. Reads only the run JSON (`rearm_mode`, `config.values`, `labels`, `window_trace`): no model, no video, no clock.
The same JSON always gives the same bytes (stdout and --out-json).

Definitions (fixed in W3, before any U3 trace exists; parameters come from the run's own config):
- M0: rearm_mode of the run is not 'classifier' (the label decoder did not run): the whole run is M0, no window table.
- transition segment: the windows after an emitted label `old` up to (not including) the next emitted label, or up to
  a decoder reset (an entry with last = None and nothing emitted: hand withdrawn >= hand_lost_ms, key n or pause), or
  up to the end of the trace. Windows before the first emission or after a reset are onset, in no segment.
  `new` (the sign the signer moved to): with --expected, the item that follows `old` in the expected list (aligned
  left to right, from the sign aligned last, so a sign emitted again after a reset keeps its place; None after the
  last item); when there is no --expected or `old` is not found in the rest of it: the label emitted at the end of the
  segment (None when the segment ends otherwise).
- window time: time to the next trace entry, capped at hand_lost_ms; the last entry gets the median interval.
- class of a segment window, first match wins:
    hold   ts < start of the run of `old` + --hold-ms (the signer still holds `old`, §4 asks ~2 s per sign): not a
           transition, left out of the shares;
    M4     `new` known, {top1, top2} == {old, new} and conf < cls_conf: the probability is split between the two signs
           of the pair (the model does not separate them);
    M1     conf < cls_conf (or status not 'ok'): confidence gate;
    M2     top1 == old with conf >= cls_conf: the model still gives the old sign;
    stable top1 != old, conf >= cls_conf, inside the run completed by the emission that closes the segment (the normal
           cls_stable_ms wait before an emission);
    M3     top1 != old, conf >= cls_conf, in a run broken before cls_stable_ms (label flicker).
- shares: time of each class / transition time (every segment window except hold). Main cause (rule of §5) = the M
  code with more than half of the transition time; none otherwise.
"""
import argparse
import json
import os
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Sequence

TRACE_CLASSES = ("M1", "M2", "M3", "M4", "stable")  # transition classes (shares); 'hold' is reported apart
M_CODES = ("M1", "M2", "M3", "M4")
DEFAULT_HOLD_MS = 2000.0  # plan 15 lần sửa 6 §4: each sign is held about 2 s before the next one
NOTE_VI = ("Chẩn đoán từ window_trace của một phiên (vài lượt, một người ký): chỉ để chọn hướng sửa theo §5, "
           "không phải độ chính xác.")


def _nfc(s: Optional[str]) -> Optional[str]:
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


def config_value(report: Dict[str, Any], key: str) -> Any:
    v = report["config"]["values"][key]
    return v["value"] if isinstance(v, dict) and "value" in v else v


def parse_expected(text: Optional[str]) -> Optional[List[str]]:
    if text is None:
        return None
    items = [_nfc(x.strip()) for x in text.split(",")]
    return [x for x in items if x]


def window_times(entries: Sequence[Dict[str, Any]], cap_ms: float) -> List[float]:
    ts = [float(e["ts_ms"]) for e in entries]
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    if gaps:
        s = sorted(gaps)
        n = len(s)
        median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
    else:
        median = 0.0
    return [min(g, cap_ms) for g in gaps] + ([min(median, cap_ms)] if ts else [])


def split_segments(entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transition segments as index ranges of `entries` (see the module docstring)."""
    segments, cur = [], None
    for i, e in enumerate(entries):
        if e["emitted"] is not None:
            if cur is not None:
                cur.update(end=i, end_reason="emit", closing=i)
                segments.append(cur)
            cur = {"emit_index": i, "start": i + 1}
        elif e["last"] is None and cur is not None:
            cur.update(end=i, end_reason="reset", closing=None)
            segments.append(cur)
            cur = None
    if cur is not None:
        cur.update(end=len(entries), end_reason="end", closing=None)
        segments.append(cur)
    return segments


def classify_window(e: Dict[str, Any], old: str, new: Optional[str], cls_conf: float, hold_until: float,
                    stable_run: Optional[Dict[str, Any]]) -> str:
    if float(e["ts_ms"]) < hold_until:
        return "hold"
    conf = e["conf"]
    low = e["status"] != "ok" or conf is None or conf < cls_conf
    top1, top2 = _nfc(e["top1"]), _nfc(e["top2"])
    if new is not None and low and {top1, top2} == {old, new} and old != new:
        return "M4"
    if low:
        return "M1"
    if top1 == old:
        return "M2"
    if (stable_run is not None and _nfc(e["run_label"]) == stable_run["label"]
            and float(e["ts_ms"]) >= stable_run["since"]):
        return "stable"
    return "M3"


def analyse(report: Dict[str, Any], expected: Optional[List[str]] = None,
            hold_ms: float = DEFAULT_HOLD_MS) -> Dict[str, Any]:
    out: Dict[str, Any] = {"rearm_mode": report.get("rearm_mode"), "expected": expected, "hold_ms": float(hold_ms),
                           "note_vi": NOTE_VI}
    if report.get("rearm_mode") != "classifier":
        out.update(m0=True, main_cause="M0", segments=[], totals=None,
                   reason="rearm_mode is not 'classifier': the label decoder did not run (M0, §2)")
        return out
    if "window_trace" not in report:
        raise ValueError("the JSON has no window_trace (run level1_demo.py with --trace-windows)")
    wt = report["window_trace"]
    entries = wt["entries"]
    cls_conf = float(config_value(report, "cls_conf"))
    cls_stable_ms = float(config_value(report, "cls_stable_ms"))
    hand_lost_ms = float(config_value(report, "hand_lost_ms"))
    out.update(m0=False, cls_conf=cls_conf, cls_stable_ms=cls_stable_ms, hand_lost_ms=hand_lost_ms,
               n_entries=len(entries), n_windows=wt["n_windows"], truncated=bool(wt["truncated"]))
    times = window_times(entries, hand_lost_ms)
    pointer = 0
    segments = []
    totals = {c: {"windows": 0, "ms": 0.0} for c in TRACE_CLASSES + ("hold",)}
    for seg in split_segments(entries):
        emit = entries[seg["emit_index"]]
        old = _nfc(emit["top1"])
        closing = entries[seg["closing"]] if seg["closing"] is not None else None
        new, found = None, False
        if expected is not None:  # from the sign aligned last: the same sign emitted again keeps its place
            for q in range(max(pointer - 1, 0), len(expected)):
                if expected[q] == old:
                    new = expected[q + 1] if q + 1 < len(expected) else None
                    pointer, found = q + 1, True
                    break
        if not found and closing is not None:
            new = _nfc(closing["top1"])
        stable_run = None
        if closing is not None:
            stable_run = {"label": _nfc(closing["run_label"]),
                          "since": float(closing["ts_ms"]) - float(closing["run_ms"])}
        hold_until = float(emit["ts_ms"]) - float(emit["run_ms"]) + float(hold_ms)
        counts = {c: {"windows": 0, "ms": 0.0} for c in TRACE_CLASSES + ("hold",)}
        for i in range(seg["start"], seg["end"]):
            c = classify_window(entries[i], old, new, cls_conf, hold_until, stable_run)
            counts[c]["windows"] += 1
            counts[c]["ms"] += times[i]
        for c in counts:
            totals[c]["windows"] += counts[c]["windows"]
            totals[c]["ms"] += counts[c]["ms"]
        transition_ms = sum(counts[c]["ms"] for c in TRACE_CLASSES)
        segments.append({
            "old": old, "new": new, "start_ts_ms": float(emit["ts_ms"]),
            "end_reason": seg["end_reason"], "closing_label": _nfc(closing["top1"]) if closing is not None else None,
            "reached_new": closing is not None and new is not None and _nfc(closing["top1"]) == new,
            "transition_ms": transition_ms, "counts": counts,
        })
    transition_ms = sum(totals[c]["ms"] for c in TRACE_CLASSES)
    shares = {c: (totals[c]["ms"] / transition_ms if transition_ms > 0 else None) for c in TRACE_CLASSES}
    main = [m for m in M_CODES if shares[m] is not None and shares[m] > 0.5]
    out.update(segments=segments, totals=totals, transition_ms=transition_ms, shares=shares,
               main_cause=main[0] if main else None)
    return out


def _fmt_ms(v: float) -> str:
    return f"{v:.0f}"


def _fmt_share(v: Optional[float]) -> str:
    return "—" if v is None else f"{100.0 * v:.1f}%"


def render(res: Dict[str, Any], trace_path: str) -> str:
    lines = [f"trace: {trace_path}", f"rearm_mode: {res['rearm_mode']}"]
    if res["m0"]:
        lines += [f"Nguyên nhân chính: M0 — {res['reason']}", res["note_vi"]]
        return "\n".join(lines) + "\n"
    exp = ",".join(res["expected"]) if res["expected"] is not None else "—"
    lines.append(f"cls_conf {res['cls_conf']:g} | cls_stable_ms {res['cls_stable_ms']:g} | hand_lost_ms "
                 f"{res['hand_lost_ms']:g} | hold_ms {res['hold_ms']:g} | expected: {exp}")
    lines.append(f"cửa sổ trong trace: {res['n_entries']} / {res['n_windows']}"
                 + (" (TRACE BỊ CẮT: chỉ phân tích các cửa sổ đầu)" if res["truncated"] else ""))
    lines.append("")
    head = ["#", "cũ", "mới", "kết thúc", "chuyển (ms)"] + [f"{c} n/ms" for c in TRACE_CLASSES + ("hold",)]
    lines.append(" | ".join(head))
    for k, s in enumerate(res["segments"], 1):
        end = {"emit": f"phát {s['closing_label']}", "reset": "reset (rút tay / n / p)", "end": "hết trace"}
        row = [str(k), s["old"], s["new"] if s["new"] is not None else "—", end[s["end_reason"]],
               _fmt_ms(s["transition_ms"])]
        row += [f"{s['counts'][c]['windows']}/{_fmt_ms(s['counts'][c]['ms'])}" for c in TRACE_CLASSES + ("hold",)]
        lines.append(" | ".join(row))
    lines.append("")
    lines.append("Tổng các đoạn chuyển ký hiệu (không tính hold):")
    lines.append("loại | số cửa sổ | thời gian (ms) | tỉ lệ thời gian")
    for c in TRACE_CLASSES:
        t = res["totals"][c]
        lines.append(f"{c} | {t['windows']} | {_fmt_ms(t['ms'])} | {_fmt_share(res['shares'][c])}")
    t = res["totals"]["hold"]
    lines.append(f"hold (ngoài tỉ lệ) | {t['windows']} | {_fmt_ms(t['ms'])} | —")
    lines.append(f"thời gian chuyển: {_fmt_ms(res['transition_ms'])} ms trong {len(res['segments'])} đoạn")
    main = res["main_cause"]
    lines.append("Nguyên nhân chính (§5: một mã > 50% thời gian chuyển): " + (main if main else "không có mã nào > 50%"))
    lines.append(f"Lưu ý: ký hiệu cũ giữ lâu hơn hold_ms ({res['hold_ms']:g} ms) được tính là M2; đặt --hold-ms theo thời gian giữ thật.")
    lines.append(res["note_vi"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plan 15 lần sửa 6 W3: M0-M4 diagnosis of a level1_demo.py "
                                            "--trace-windows JSON (window_trace).")
    p.add_argument("--trace", required=True, help="JSON written by level1_demo.py --trace-windows --out-json")
    p.add_argument("--expected", default=None,
                   help='signs in the order they were signed, comma separated (e.g. "dấu nặng,dấu hỏi,dấu ngã")')
    p.add_argument("--hold-ms", type=float, default=DEFAULT_HOLD_MS,
                   help="time each sign is held before the next one (U3 protocol, default %(default)s ms)")
    p.add_argument("--out-json", default=None, help="also write the result as JSON")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    with open(args.trace, encoding="utf-8") as f:
        report = json.load(f)
    try:
        res = analyse(report, parse_expected(args.expected), args.hold_ms)
    except ValueError as e:
        print(f"level1_trace_report: {e}", file=sys.stderr)
        return 2
    trace_name = args.trace.replace("\\", "/")
    text = render(res, trace_name)
    sys.stdout.write(text)
    if args.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"trace": trace_name, **res}, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
