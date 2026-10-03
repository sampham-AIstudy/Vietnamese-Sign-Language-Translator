"""
Level 1 desktop app: per-stage timing statistics (plan 15 §3.5). Pure python + numpy.

Every value is a duration measured by the caller with time.perf_counter (milliseconds); nothing is estimated here.
Statistics: n, mean, p50, p95 with numpy.percentile (linear interpolation); n = 0 -> mean / p50 / p95 = None.
"""
from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

FRAME_STAGES = ("capture_age", "mediapipe", "segmenter", "draw_landmarks", "hud", "display", "frame_total")
SIGN_STAGES = ("classify", "emit_to_token")
PERCENTILES = (50, 95)  # reported as "p<q>"


def summarize(values: Sequence[float]) -> Dict[str, Optional[float]]:
    """{n, mean, p50, p95} of `values` (None for an empty sequence)."""
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return {"n": 0, "mean": None, "p50": None, "p95": None}
    out = {"n": int(arr.size), "mean": float(arr.mean())}
    for q in PERCENTILES:
        out[f"p{q}"] = float(np.percentile(arr, q))
    return out


def rate_from_timestamps(timestamps_s: Sequence[float]) -> float:
    """Frames per second from processing timestamps (seconds): (n - 1) / (last - first); 0.0 when fewer than two
    timestamps or no elapsed time (nothing measured yet)."""
    ts = list(timestamps_s)
    if len(ts) < 2 or not ts[-1] > ts[0]:
        return 0.0
    return (len(ts) - 1) / (ts[-1] - ts[0])


class StageTimes:
    """Collects durations (ms) per stage; keeps every value for the final JSON and the last `rolling` values for a
    rolling p50 on the HUD."""

    def __init__(self, stages: Iterable[str], rolling: int):
        if int(rolling) < 1:
            raise ValueError("rolling must be >= 1")
        self.stages = tuple(stages)
        self._all: Dict[str, List[float]] = {s: [] for s in self.stages}
        self._recent: Dict[str, deque] = {s: deque(maxlen=int(rolling)) for s in self.stages}

    def add(self, stage: str, value: float) -> None:
        if stage not in self._all:
            raise KeyError(f"unknown stage {stage!r}")
        v = float(value)
        self._all[stage].append(v)
        self._recent[stage].append(v)

    def values(self, stage: str) -> List[float]:
        return list(self._all[stage])

    def rolling_p50(self, stage: str) -> Optional[float]:
        return summarize(self._recent[stage])["p50"]

    def stats(self) -> Dict[str, Dict[str, Optional[float]]]:
        return {s: summarize(self._all[s]) for s in self.stages}
