"""
Source-harmonised Level 2 input (step 4b of the source investigation, reports/source_diagnostics_2026-09-26).

The same function is meant for every source (VSL-GH segments, QIPEDC/HCMUE dictionary clips) and for the live
camera path, so none of the cues that identified the source reaches the model:
- joints: arms (MediaPipe pose 11-16: shoulders, elbows, wrists) + both hands (25-66). Face (0-10), the pose
  hand points 17-22 (incl. thumbs 21/22, which came from different models per source; the hand-model thumb is
  kept as part of the hand) and hips (23-24) are masked out. The 67-joint layout is kept so the ST-GCN graph and
  checkpoints stay compatible; dropped joints have mask 0 and coordinates 0.
- coordinates: aspect-corrected, centred on the mid-shoulder of each frame, scaled by the clip's median shoulder
  width. Pose z is dropped (set to 0); hand z is kept or dropped by config.
- time: the rest before/after the sign is trimmed with one motion/position rule, then the active span is
  resampled uniformly IN TIME (from fps or timestamps) to a fixed number of frames. Short hand gaps are bridged
  by linear interpolation; longer gaps stay masked.
Augmentation (training only): scale, rotation, speed warp 0.7-1.3, random temporal crop.
"""
from typing import Any, Dict, Optional, Tuple

import numpy as np

ARM_JOINTS = [11, 12, 13, 14, 15, 16]
HAND_SLICES = (slice(25, 46), slice(46, 67))
WRISTS = (25, 46)
KEEP = np.zeros(67, bool)
KEEP[ARM_JOINTS] = True
KEEP[25:67] = True

HARMONIZED_DEFAULT: Dict[str, Any] = {
    "features": "harmonized_v1",
    "target_len": 32,
    "hand_z": True,            # False -> hand z set to 0
    "trim": True,              # False -> keep the whole clip (ablation of the rest trimming)
    "rest_y": 1.2,             # wrist below this (shoulder widths under the shoulder line) counts as resting...
    "active_speed": 1.0,       # ...unless it moves faster than this (shoulder widths / second)
    "pad_s": 0.1,              # context kept around the active span
    "max_gap_s": 0.25,         # hand gaps up to this are interpolated
    "mask_resting_hand": True, # a hand below rest_y and slower than active_speed counts as absent (VSL-GH tracks
                               # the resting hand at the hip, dictionary clips mostly lose it: a source cue)
    "process_height": None,    # frame height given to MediaPipe (None = native); must match the live path
    "joints": "arms(11-16)+hands(25-66); face, pose hand points 17-22 (thumbs 21/22), hips masked",
    "pose_z": False,
}


def _normalise(kps: np.ndarray, vis: np.ndarray, aspect: Optional[float]) -> Tuple[np.ndarray, np.ndarray]:
    k = np.array(kps, dtype=np.float32, copy=True)
    v = (np.asarray(vis) > 0.5) & np.isfinite(k).all(-1) & KEEP[None]
    if aspect:
        k[..., 0] *= aspect
        k[..., 2] *= aspect
    sh_ok = v[:, 11] & v[:, 12]
    mid = (k[:, 11, :2] + k[:, 12, :2]) / 2
    width = np.linalg.norm(k[:, 11, :2] - k[:, 12, :2], axis=-1)
    if sh_ok.any():
        fallback = np.median(mid[sh_ok], 0)
        sw = float(np.median(width[sh_ok]))
    else:  # no shoulders at all: centre on the image, scale by a nominal width
        fallback, sw = np.array([0.5 * (aspect or 1.0), 0.5], np.float32), 0.25
    mid = np.where(sh_ok[:, None], mid, fallback)
    out = np.zeros_like(k)
    out[..., :2] = (k[..., :2] - mid[:, None]) / max(sw, 1e-6)
    out[..., 2] = k[..., 2] / max(sw, 1e-6)
    out[:, :25, 2] = 0.0  # pose z dropped
    out[~v] = 0.0
    return out, v


def hand_activity(k: np.ndarray, v: np.ndarray, fps: float, cfg: Dict[str, Any]):
    """Per hand (left, right): frames where the hand is present and raised above rest_y or moving fast."""
    T, out = len(k), []
    for w in WRISTS:
        present = v[:, w]
        speed = np.zeros(T)
        both = present[1:] & present[:-1]
        speed[1:][both] = np.linalg.norm(np.diff(k[:, w, :2], axis=0)[both], axis=-1) * fps
        out.append(present & ((k[:, w, 1] < cfg["rest_y"]) | (speed > cfg["active_speed"])))
    return out


def active_span(k: np.ndarray, v: np.ndarray, fps: float, cfg: Dict[str, Any]) -> Tuple[int, int]:
    """First..last frame where a hand is raised above rest_y or moving faster than active_speed, +- pad_s."""
    T = len(k)
    left, right = hand_activity(k, v, fps, cfg)
    idx = np.flatnonzero(left | right)
    if len(idx) < 2:
        return 0, T
    pad = int(round(cfg["pad_s"] * fps))
    return max(0, idx[0] - pad), min(T, idx[-1] + pad + 1)


def _resample(k: np.ndarray, v: np.ndarray, t: np.ndarray, grid: np.ndarray, max_gap: float):
    """Per joint, linear interpolation at the grid times between visible frames less than max_gap apart."""
    L, J = len(grid), k.shape[1]
    out = np.zeros((L, J, 3), np.float32)
    mask = np.zeros((L, J), bool)
    groups = [[j] for j in ARM_JOINTS] + [list(range(s.start, s.stop)) for s in HAND_SLICES]
    for g in groups:
        pres = v[:, g[0]]
        idx = np.flatnonzero(pres)
        if len(idx) == 0:
            continue
        ti = t[idx]
        pos = np.searchsorted(ti, grid)
        lo, hi = np.clip(pos - 1, 0, len(idx) - 1), np.clip(pos, 0, len(idx) - 1)
        t_lo, t_hi = ti[lo], ti[hi]
        exact = np.isclose(t_lo, grid) | np.isclose(t_hi, grid)
        inside = (t_lo <= grid) & (grid <= t_hi) & ((t_hi - t_lo) <= max_gap)
        near = np.minimum(np.abs(grid - t_lo), np.abs(grid - t_hi)) <= max_gap / 2
        ok = exact | inside | near
        w = np.where(t_hi > t_lo, (grid - t_lo) / np.maximum(t_hi - t_lo, 1e-9), 0.0).clip(0, 1)
        a, b = k[idx[lo]][:, g], k[idx[hi]][:, g]
        vals = a + (b - a) * w[:, None, None]
        out[:, g] = np.where(ok[:, None, None], vals, 0.0)
        mask[:, g] = ok[:, None]
    return out, mask


def harmonize(kps: np.ndarray, vis: np.ndarray, aspect: Optional[float], fps: float,
              cfg: Optional[Dict[str, Any]] = None, timestamps_s: Optional[np.ndarray] = None,
              rng: Optional[np.random.Generator] = None):
    """
    kps [T,67,3] MediaPipe image coords (NaN where missing), vis [T,67].
    Returns sequence [L,67,3] float32, joint_mask [L,67] float32, temporal_mask [L] float32 (all ones).
    rng given -> training augmentation (random crop, speed warp, scale, rotation).
    """
    cfg = {**HARMONIZED_DEFAULT, **(cfg or {})}
    L = int(cfg["target_len"])
    k, v = _normalise(kps, vis, aspect)
    fps = float(fps) if fps and fps > 0 else 30.0
    t = np.asarray(timestamps_s, np.float64) if timestamps_s is not None else np.arange(len(k)) / fps
    a, b = active_span(k, v, fps, cfg) if cfg["trim"] else (0, len(k))
    if cfg["mask_resting_hand"]:
        for sl, active in zip(HAND_SLICES, hand_activity(k, v, fps, cfg)):
            v[~active, sl] = False
            k[~active, sl] = 0.0
    t0, t1 = t[a], t[b - 1]
    if rng is not None:  # random temporal crop: keep 80-100% of the span
        keep = rng.uniform(0.8, 1.0) * (t1 - t0)
        start = t0 + rng.uniform(0, (t1 - t0) - keep)
        t0, t1 = start, start + keep
    u = np.linspace(0.0, 1.0, L)
    if rng is not None:  # speed warp: local speed between ~0.7x and ~1.3x
        u = u ** rng.uniform(0.7, 1.3)
    grid = t0 + u * (t1 - t0)
    seq, mask = _resample(k, v, t, grid, cfg["max_gap_s"])
    if not cfg["hand_z"]:
        seq[..., 2] = 0.0
    if rng is not None:
        th = np.deg2rad(rng.uniform(-15, 15))
        rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]], np.float32)
        seq[..., :2] = (seq[..., :2] @ rot.T) * rng.uniform(0.85, 1.15)
        seq[~mask] = 0.0
    return seq.astype(np.float32), mask.astype(np.float32), np.ones(L, np.float32)


class HarmonizedDataset:
    """Unified-manifest rows (absolute npz_path, width, height) -> harmonised model input.
    Same item keys as VSLDataset, so vsl_collate_fn / VSLTrainer / train_unified work unchanged."""

    def __init__(self, csv_path: str, label_map: Dict[str, int], cfg: Optional[Dict[str, Any]] = None,
                 augment: bool = False):
        import csv
        with open(csv_path, encoding="utf-8") as f:
            self.samples = [r for r in csv.DictReader(f) if r["gloss_normalized"] in label_map]
        self.label_map, self.cfg, self.augment = label_map, {**HARMONIZED_DEFAULT, **(cfg or {})}, augment

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        import json
        import torch
        r = self.samples[idx % len(self.samples)]
        d = np.load(r["npz_path"])
        fps = 30.0
        if "metadata" in d.files:
            fps = float(json.loads(str(d["metadata"])).get("fps") or 30.0)
        rng = np.random.default_rng(int(torch.randint(0, 2**31 - 1, (1,)))) if self.augment else None
        seq, jm, tm = harmonize(d["keypoints"], d["visibility_mask"], float(r["width"]) / float(r["height"]), fps,
                                self.cfg, rng=rng)
        return {"sequence": torch.from_numpy(seq), "joint_mask": torch.from_numpy(jm),
                "temporal_mask": torch.from_numpy(tm),
                "label": torch.tensor(self.label_map[r["gloss_normalized"]], dtype=torch.long),
                "video_id": r["video_id"], "gloss": r["gloss_normalized"]}
