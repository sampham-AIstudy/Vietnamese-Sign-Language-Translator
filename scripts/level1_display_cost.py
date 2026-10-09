#!/usr/bin/env python
"""
Plan 15 Lần sửa 13b — Bước U2d: Đo chi phí hiển thị Level 1 (AC-U5, gate DC1); sửa ở lần sửa 13c — C1.

Chạy app cùng tiến trình trên clip D2 với --pace realtime và recorder vá các lệnh OpenCV
(không mở cửa sổ thật, không đo chi phí vẽ cửa sổ HĐH).
- Lần 1 'natural': getWindowImageRect trả rect bằng ảnh imshow gần nhất (sau lần resize đầu: cỡ tự nhiên).
- Lần 2 'window_1080p': getWindowImageRect trả (0, 0, 1920, 1080).
- Đường vẽ của mỗi lần KHÔNG suy ra từ rect: đếm số lần gọi Hud.compose / render_to_window (path_counts), bọc hàm gốc.
- Gate DC1: ratio p50(1080p) / p50(tự nhiên) <= 1.25 (frame_total), chỉ xét khi dữ liệu hợp lệ (fail-closed): mỗi lần
  n_frames >= MIN_FRAMES, p50 hữu hạn > 0, tổng path_counts == n_imshow == n_frames. Không hợp lệ => pass false + reason.

Mã thoát:
  0 = dữ liệu hợp lệ và DC1 pass;
  1 = dữ liệu hợp lệ nhưng DC1 trượt (JSON vẫn ghi);
  2 = đối số sai (argparse) hoặc clip không tồn tại (KHÔNG ghi JSON, không đo);
  3 = dữ liệu không hợp lệ (JSON vẫn ghi, gate.reason nói lý do).
"""
import argparse
import json
import math
import os
import platform
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple
from unittest import mock

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CLIP = "data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4"  # tương đối theo ROOT (mặc định của --clip)
SCRIPT_REL = "scripts/level1_display_cost.py"
MIN_FRAMES = 10  # đặt trước lần đo C2 (13c §3.1): p50 trên dưới 10 giá trị không mang nghĩa
DC1_THRESHOLD = 1.25
PATHS = ("Hud.compose", "render_to_window")
INFO_STAGES = ("hud", "mediapipe")
NOTE_TEXT = (
    "imshow vá, không cửa sổ thật, không đo chi phí vẽ cửa sổ HĐH; đường vẽ mỗi lần là số đếm path_counts "
    "(số khung đi Hud.compose / render_to_window, bọc hàm gốc), không suy ra từ rect; stage_p50_ms và info là số "
    "thông tin, không vào gate DC1"
)


def percentile(values: Sequence[float], q: float) -> float:
    """Tính phân vị q (0..100) theo phương pháp nội suy tuyến tính (numpy)."""
    return float(np.percentile(values, q))


def summarize_frame_total(values: Sequence[float]) -> Dict[str, Any]:
    """Tổng hợp chuỗi thời gian frame_total (ms) thành {n, p50, p90}. Chuỗi rỗng => n 0, p50 0.0 (build_report coi
    là không hợp lệ, không pass)."""
    vals = list(values)
    if not vals:
        return {"n": 0, "p50": 0.0, "p90": 0.0}
    return {
        "n": len(vals),
        "p50": float(percentile(vals, 50)),
        "p90": float(percentile(vals, 90)),
    }


def _finite_positive(value: Any) -> bool:
    """True khi value là số hữu hạn > 0 (None, nan, inf, <= 0 => False)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0


def compute_ratio(p50_natural: float, p50_1080: float) -> float:
    """Tỷ lệ p50_1080 / p50_natural. Fail-closed (13c TB-1): p50 nào không hữu hạn hoặc <= 0 => ValueError
    (không trả 0.0, vì 0.0 sẽ làm gate pass khi không có dữ liệu)."""
    if not _finite_positive(p50_natural):
        raise ValueError(f"p50_natural phải hữu hạn và > 0, nhận {p50_natural!r}")
    if not _finite_positive(p50_1080):
        raise ValueError(f"p50_1080 phải hữu hạn và > 0, nhận {p50_1080!r}")
    return float(p50_1080) / float(p50_natural)


def dc1_gate(ratio: Optional[float], threshold: float = DC1_THRESHOLD) -> Dict[str, Any]:
    """Cổng DC1 kiểm tra ratio <= threshold (biên 1.25 => pass, 1.2501 => fail).
    ratio None / không hữu hạn => pass false, có reason (fail-closed)."""
    gate: Dict[str, Any] = {"name": "DC1", "threshold": float(threshold), "pass": False, "reason": None}
    if ratio is None or not math.isfinite(float(ratio)):
        gate["reason"] = f"ratio_p50 không hợp lệ ({ratio!r})"
        return gate
    gate["pass"] = bool(float(ratio) <= threshold)
    return gate


def _p50_or_none(values: Sequence[float]) -> Optional[float]:
    vals = list(values)
    return float(percentile(vals, 50)) if vals else None


def summarize_run(measured: Dict[str, Any]) -> Dict[str, Any]:
    """Tóm tắt kết quả measure() của một lần đo thành mục JSON: n_frames, p50/p90 frame_total, n_imshow, path_counts,
    stage_p50_ms (hud, mediapipe; None khi không có giá trị)."""
    s = summarize_frame_total(measured.get("frame_total", []))
    counts = measured.get("path_counts") or {}
    return {
        "n_frames": int(s["n"]),
        "p50_ms": float(s["p50"]),
        "p90_ms": float(s["p90"]),
        "n_imshow": int(measured["n_imshow"]) if measured.get("n_imshow") is not None else None,
        "path_counts": {k: int(counts.get(k, 0)) for k in PATHS},
        "stage_p50_ms": {st: _p50_or_none(measured.get(st, [])) for st in INFO_STAGES},
    }


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _opt_float(value: Any) -> Optional[float]:
    v = _as_float(value)
    return v if math.isfinite(v) else None


def _run_entry(run: Dict[str, Any]) -> Dict[str, Any]:
    """Chép một lần đo vào lược đồ JSON (không suy diễn, không điền số mặc định cho đường vẽ)."""
    n = run.get("n_frames", run.get("n", 0))
    n_imshow = run.get("n_imshow")
    counts = run.get("path_counts")
    stages = run.get("stage_p50_ms") or {}
    return {
        "n_frames": int(n),
        "p50_ms": _as_float(run.get("p50_ms", run.get("p50"))),
        "p90_ms": _as_float(run.get("p90_ms", run.get("p90"))),
        "n_imshow": int(n_imshow) if n_imshow is not None else None,
        "path_counts": {k: int(counts[k]) for k in PATHS if k in counts} if isinstance(counts, dict) else None,
        "stage_p50_ms": {st: _opt_float(stages.get(st)) for st in INFO_STAGES},
    }


def validate_run(name: str, entry: Dict[str, Any], min_frames: int = MIN_FRAMES) -> List[str]:
    """Điều kiện hợp lệ của một lần đo (áp TRƯỚC gate). Trả danh sách lỗi; rỗng = hợp lệ."""
    errors: List[str] = []
    n = entry["n_frames"]
    if n < min_frames:
        errors.append(f"{name}: n_frames {n} < min_frames {min_frames}")
    if not _finite_positive(entry["p50_ms"]):
        errors.append(f"{name}: p50_ms {entry['p50_ms']!r} không hữu hạn hoặc <= 0")
    counts = entry["path_counts"]
    if counts is None or set(counts) != set(PATHS):
        errors.append(f"{name}: thiếu path_counts {list(PATHS)}")
    n_imshow = entry["n_imshow"]
    if n_imshow is None:
        errors.append(f"{name}: thiếu n_imshow")
    if counts is not None and n_imshow is not None and sum(counts.values()) != n_imshow:
        errors.append(f"{name}: tổng path_counts {sum(counts.values())} != n_imshow {n_imshow}")
    if n_imshow is not None and n_imshow != n:
        errors.append(f"{name}: n_imshow {n_imshow} != n_frames {n}")
    return errors


def build_report(
    command: Any,
    commit: str,
    clip: str,
    natural: Dict[str, Any],
    p1080: Dict[str, Any],
    py_version: str,
    cv2_version: str,
    code_dirty: Optional[bool] = False,
    min_frames: int = MIN_FRAMES,
) -> Dict[str, Any]:
    """Tạo từ điển báo cáo JSON theo AC-U5 + AC-C1 (13c). Điều kiện hợp lệ áp TRƯỚC gate (fail-closed): lần đo nào
    vi phạm => gate.pass false, gate.reason ghi lý do. ratio_p50 None khi p50 của một lần đo không hợp lệ.
    stage_p50_ms / info là số thông tin, không vào gate."""
    nat = _run_entry(natural)
    w1080 = _run_entry(p1080)

    errors = validate_run("natural", nat, min_frames) + validate_run("window_1080p", w1080, min_frames)
    ratio: Optional[float] = None
    if _finite_positive(nat["p50_ms"]) and _finite_positive(w1080["p50_ms"]):
        ratio = compute_ratio(nat["p50_ms"], w1080["p50_ms"])
    if errors:
        gate = {"name": "DC1", "threshold": float(DC1_THRESHOLD), "pass": False, "reason": "; ".join(errors)}
    else:
        gate = dc1_gate(ratio)

    hud_nat = nat["stage_p50_ms"]["hud"]
    hud_1080 = w1080["stage_p50_ms"]["hud"]
    hud_delta = float(hud_1080 - hud_nat) if hud_nat is not None and hud_1080 is not None else None

    return {
        "command": command,
        "commit": commit,
        "code_dirty": bool(code_dirty),
        "clip": clip,
        "min_frames": int(min_frames),
        "natural": nat,
        "window_1080p": w1080,
        "ratio_p50": ratio,
        "gate": gate,
        "info": {"hud_p50_delta_ms": hud_delta, "in_gate": False},
        "note": NOTE_TEXT,
        "python": py_version,
        "cv2": cv2_version,
    }


class _DisplayCostRecorder:
    """Bộ ghi các lệnh OpenCV cho kiểm tra chi phí hiển thị Level 1 (không mở cửa sổ thật)."""

    def __init__(self, rect: Any):
        self.rect = rect
        self.shown: List[Tuple[int, ...]] = []
        self.last_shape: Optional[Tuple[int, ...]] = None
        self.natural_size: Optional[Tuple[int, int]] = None

    def imshow(self, name: str, image: np.ndarray) -> None:
        shape = image.shape
        self.shown.append(shape)
        self.last_shape = shape

    @staticmethod
    def waitKey(delay: int = 1) -> int:
        return -1

    @staticmethod
    def getWindowProperty(name: str, prop: int) -> float:
        return 1.0

    @staticmethod
    def namedWindow(*a: Any, **k: Any) -> None:
        return None

    @staticmethod
    def destroyAllWindows() -> None:
        return None

    def resizeWindow(self, name: str, w: int, h: int) -> None:
        self.natural_size = (w, h)

    def getWindowImageRect(self, name: str) -> Any:
        if self.rect == "natural" or self.rect is None:
            if self.last_shape is not None:
                return (0, 0, self.last_shape[1], self.last_shape[0])
            if self.natural_size is not None:
                return (0, 0, self.natural_size[0], self.natural_size[1])
            return (0, 0, 640, 643)
        return self.rect


def measure(rect: Any, clip: str = CLIP, app_module: Any = None) -> Dict[str, Any]:
    """Chạy app cùng tiến trình trên clip (nên là đường dẫn tuyệt đối: main đã abspath theo cwd người gọi).
    Trả {"frame_total", "hud", "mediapipe"} (list ms từ app.times.values), "n_imshow" (số lần imshow) và
    "path_counts" (số lần gọi Hud.compose / render_to_window, đếm bằng cách bọc hàm gốc; hàm gốc vẫn chạy và giá trị
    trả về đi tiếp tới imshow). app_module=None => level1_demo."""
    if app_module is None:
        import level1_demo as app_module

    app = app_module.Level1App(app_module.build_parser().parse_args(["--source", clip, "--pace", "realtime"]))
    rec = _DisplayCostRecorder(rect)
    counts = {k: 0 for k in PATHS}
    orig_compose = app_module.Hud.compose
    orig_render_to_window = app_module.render_to_window

    def counted_compose(hud_self: Any, *args: Any, **kwargs: Any) -> Any:
        counts["Hud.compose"] += 1
        return orig_compose(hud_self, *args, **kwargs)

    def counted_render_to_window(*args: Any, **kwargs: Any) -> Any:
        counts["render_to_window"] += 1
        return orig_render_to_window(*args, **kwargs)

    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        with mock.patch.multiple(
            app_module.cv2,
            imshow=rec.imshow,
            waitKey=rec.waitKey,
            getWindowProperty=rec.getWindowProperty,
            namedWindow=rec.namedWindow,
            destroyAllWindows=rec.destroyAllWindows,
            resizeWindow=rec.resizeWindow,
            getWindowImageRect=rec.getWindowImageRect,
        ), mock.patch.object(app_module.Hud, "compose", counted_compose), \
                mock.patch.object(app_module, "render_to_window", counted_render_to_window):
            app.run()
    finally:
        os.chdir(cwd)

    result: Dict[str, Any] = {st: list(app.times.values(st)) for st in ("frame_total",) + INFO_STAGES}
    result["n_imshow"] = len(rec.shown)
    result["path_counts"] = dict(counts)
    return result


def git_commit() -> str:
    """Lấy commit SHA hiện tại qua git rev-parse HEAD."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_code_dirty() -> bool:
    """Kiểm tra thay đổi chưa commit trên các file mã nguồn liên quan."""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--", "scripts/level1_display_cost.py", "level1_demo.py", "src"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(r.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return False


def _inside_root(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    r = os.path.normcase(ROOT)
    try:
        return os.path.commonpath([p, r]) == r
    except ValueError:  # khác ổ đĩa
        return False


def display_path(path: str) -> str:
    """Đường dẫn ghi vào JSON: trong ROOT => relpath dạng posix; ngoài ROOT => abspath."""
    p = os.path.abspath(path)
    if _inside_root(p):
        return os.path.relpath(p, ROOT).replace(os.sep, "/")
    return p


def _portable_arg(arg: str) -> str:
    """Đối số là đường dẫn tuyệt đối trong ROOT (kể cả dạng --opt=...) => relpath posix; còn lại giữ nguyên."""
    prefix, value = "", arg
    if arg.startswith("--") and "=" in arg:
        prefix, value = arg.split("=", 1)
        prefix += "="
    if os.path.isabs(value) and _inside_root(value):
        return prefix + display_path(value)
    return arg


def build_command(argv: Sequence[str]) -> str:
    """Lệnh tái lập không chứa ROOT tuyệt đối (13c THẤP-6): trình thông dịch trong ROOT => relpath posix, ngoài ROOT =>
    basename; script ghi tương đối; đối số đường dẫn tuyệt đối trong ROOT => relpath posix."""
    exe = sys.executable or "python"
    exe_label = display_path(exe) if _inside_root(exe) else os.path.basename(exe)
    return " ".join([exe_label, SCRIPT_REL, *(_portable_arg(str(a)) for a in argv)])


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI; mã thoát xem docstring của module (0 pass, 1 DC1 trượt, 2 đối số sai / thiếu clip, 3 dữ liệu không hợp lệ)."""
    parser = argparse.ArgumentParser(description="Đo chi phí hiển thị Level 1 (AC-U5, gate DC1)")
    parser.add_argument("--out", required=True, help="Đường dẫn file JSON đầu ra")
    parser.add_argument("--clip", default=None,
                        help=f"Đường dẫn clip đo; tương đối thì theo cwd của người gọi (mặc định: {CLIP} trong repo)")
    args = parser.parse_args(argv)

    # abspath TRƯỚC mọi chdir (measure chdir về ROOT khi chạy app)
    clip_abs = os.path.abspath(args.clip) if args.clip is not None else os.path.abspath(os.path.join(ROOT, CLIP))
    if not os.path.isfile(clip_abs):
        print(f"Lỗi: không thấy clip {clip_abs}", file=sys.stderr)
        return 2

    command = build_command(sys.argv[1:] if argv is None else list(argv))
    head_commit = git_commit()
    dirty = git_code_dirty()

    measured_nat = measure("natural", clip=clip_abs)
    measured_1080 = measure((0, 0, 1920, 1080), clip=clip_abs)

    report = build_report(
        command=command,
        commit=head_commit,
        clip=display_path(clip_abs),
        natural=summarize_run(measured_nat),
        p1080=summarize_run(measured_1080),
        py_version=platform.python_version(),
        cv2_version=cv2.__version__,
        code_dirty=dirty,
    )

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    gate = report["gate"]
    print(f"DC1 pass={gate['pass']} ratio={report['ratio_p50']} reason={gate['reason']}")
    if gate["reason"] is not None:
        return 3
    return 0 if gate["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
