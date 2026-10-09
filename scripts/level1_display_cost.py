#!/usr/bin/env python
"""
Plan 15 Lần sửa 13b — Bước U2d: Đo chi phí hiển thị Level 1 (AC-U5, gate DC1).

Chạy app cùng tiến trình trên clip D2 với --pace realtime và recorder vá các lệnh OpenCV
(không mở cửa sổ thật, không đo chi phí vẽ cửa sổ HĐH).
- Lần 1 'natural': getWindowImageRect trả kích thước tự nhiên => app đi đường Hud.compose cũ.
- Lần 2 'window_1080p': getWindowImageRect trả (0, 0, 1920, 1080) => app đi đường render_to_window.
- Gate DC1: ratio p50(1080p) / p50(tự nhiên) <= 1.25.
"""
import argparse
import json
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

CLIP = "data/external/hauuto_raw/raw/raw/hau/a_hau_A_001.mp4"
NOTE_TEXT = (
    'imshow vá, không cửa sổ thật; lần "natural" đo đường Hud.compose cũ vì rect bằng '
    'kích thước tự nhiên; không đo chi phí vẽ cửa sổ HĐH'
)


def percentile(values: Sequence[float], q: float) -> float:
    """Tính phân vị q (0..100) theo phương pháp nội suy tuyến tính (numpy)."""
    return float(np.percentile(values, q))


def summarize_frame_total(values: Sequence[float]) -> Dict[str, Any]:
    """Tổng hợp chuỗi thời gian frame_total (ms) thành {n, p50, p90}."""
    vals = list(values)
    if not vals:
        return {"n": 0, "p50": 0.0, "p90": 0.0}
    return {
        "n": len(vals),
        "p50": float(percentile(vals, 50)),
        "p90": float(percentile(vals, 90)),
    }


def compute_ratio(p50_natural: float, p50_1080: float) -> float:
    """Tỷ lệ p50_1080 / p50_natural."""
    if p50_natural <= 0:
        return 0.0
    return float(p50_1080 / p50_natural)


def dc1_gate(ratio: float, threshold: float = 1.25) -> Dict[str, Any]:
    """Cổng DC1 kiểm tra ratio <= threshold (biên 1.25 => pass, 1.2501 => fail)."""
    return {
        "name": "DC1",
        "threshold": float(threshold),
        "pass": bool(ratio <= threshold),
    }


def build_report(
    command: Any,
    commit: str,
    clip: str,
    natural: Dict[str, Any],
    p1080: Dict[str, Any],
    py_version: str,
    cv2_version: str,
    code_dirty: Optional[bool] = False,
) -> Dict[str, Any]:
    """Tạo từ điển báo cáo JSON đủ cấu trúc và khóa theo tiêu chí AC-U5."""
    n_nat = int(natural.get("n_frames", natural.get("n", 0)))
    p50_nat = float(natural.get("p50_ms", natural.get("p50", 0.0)))
    p90_nat = float(natural.get("p90_ms", natural.get("p90", 0.0)))
    path_nat = natural.get("path", "Hud.compose (đường cũ, không qua render_to_window)")

    n_1080 = int(p1080.get("n_frames", p1080.get("n", 0)))
    p50_1080 = float(p1080.get("p50_ms", p1080.get("p50", 0.0)))
    p90_1080 = float(p1080.get("p90_ms", p1080.get("p90", 0.0)))
    path_1080 = p1080.get("path", "render_to_window")

    ratio = compute_ratio(p50_nat, p50_1080)
    gate = dc1_gate(ratio)

    return {
        "command": command,
        "commit": commit,
        "code_dirty": bool(code_dirty),
        "clip": clip,
        "natural": {
            "n_frames": n_nat,
            "p50_ms": p50_nat,
            "p90_ms": p90_nat,
            "path": path_nat,
        },
        "window_1080p": {
            "n_frames": n_1080,
            "p50_ms": p50_1080,
            "p90_ms": p90_1080,
            "path": path_1080,
        },
        "ratio_p50": ratio,
        "gate": gate,
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


def measure(rect: Any, clip: str = CLIP) -> List[float]:
    """Chạy app cùng tiến trình trên clip và đo chuỗi thời gian frame_total (ms)."""
    import level1_demo as app_mod

    app = app_mod.Level1App(app_mod.build_parser().parse_args(["--source", clip, "--pace", "realtime"]))
    rec = _DisplayCostRecorder(rect)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        with mock.patch.multiple(
            app_mod.cv2,
            imshow=rec.imshow,
            waitKey=rec.waitKey,
            getWindowProperty=rec.getWindowProperty,
            namedWindow=rec.namedWindow,
            destroyAllWindows=rec.destroyAllWindows,
            resizeWindow=rec.resizeWindow,
            getWindowImageRect=rec.getWindowImageRect,
        ):
            app.run()
    finally:
        os.chdir(cwd)

    return list(app.times.values("frame_total"))


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Đo chi phí hiển thị Level 1 (AC-U5, gate DC1)")
    parser.add_argument("--out", required=True, help="Đường dẫn file JSON đầu ra")
    parser.add_argument("--clip", default=CLIP, help="Đường dẫn clip đo")
    args = parser.parse_args(argv)

    raw_command = " ".join(
        [sys.executable or "python", "scripts/level1_display_cost.py", *(sys.argv[1:] if argv is None else argv)]
    )
    head_commit = git_commit()
    dirty = git_code_dirty()

    times_nat = measure("natural", clip=args.clip)
    times_1080 = measure((0, 0, 1920, 1080), clip=args.clip)

    sum_nat = summarize_frame_total(times_nat)
    sum_1080 = summarize_frame_total(times_1080)

    report = build_report(
        command=raw_command,
        commit=head_commit,
        clip=args.clip,
        natural=sum_nat,
        p1080=sum_1080,
        py_version=platform.python_version(),
        cv2_version=cv2.__version__,
        code_dirty=dirty,
    )

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"DC1 pass={report['gate']['pass']} ratio={report['ratio_p50']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
