"""
Live "harmonized_v1" path of the "Ký từ" mode (plan 04 §3.2, §3.5).

Uses the training code itself, unmodified:
- landmarks: src.data.landmark_extractor.CleanHolisticExtractor(process_height=ckpt.preprocessing.process_height),
  fed `cv2.cvtColor(bgr, COLOR_BGR2RGB)` exactly like CleanHolisticExtractor.extract_from_video (the extractor
  itself resizes to process_height with INTER_AREA before MediaPipe);
- model input: src.data.harmonized.harmonize(kps, vis, aspect=W/H of the ORIGINAL frame, fps, cfg=the checkpoint's
  preprocessing dict, timestamps_s) with rng=None (no augmentation), so the rest trimming of training is kept.
A SignSegmenter (src/inference/sign_segmenter.py) collects one whole sign before anything is predicted.

Which path a checkpoint needs is decided by the checkpoint itself: live_pipeline_for(preprocessing).
"""
import time
from typing import Any, Dict, Mapping, Optional

import cv2
import numpy as np

from src.data.harmonized import harmonize
from src.inference.sign_segmenter import SEGMENTER_DEFAULT, Discard, Emit, SignSegmenter

perf_counter = time.perf_counter   # module attribute so tests can substitute a known sequence (plan AC2-f)

HARMONIZED_REQUIRED_KEYS = ("trim", "hand_z", "rest_y", "active_speed", "pad_s", "max_gap_s", "mask_resting_hand")
PIPELINE_LEGACY = "legacy"
PIPELINE_HARMONIZED = "harmonized_v1"


def _is_int(v) -> bool:
    return isinstance(v, (int, np.integer)) and not isinstance(v, bool)


def live_pipeline_for(preprocessing: Optional[Mapping[str, Any]]) -> str:
    """"legacy" for checkpoints without preprocessing.features (old checkpoints, the baseline PREPROCESSING of
    scripts/train_unified.py); "harmonized_v1" for a valid harmonized checkpoint; ValueError otherwise
    (the model must then be treated as unusable, never silently run through the other path)."""
    if not preprocessing:
        return PIPELINE_LEGACY
    if not isinstance(preprocessing, Mapping):
        raise ValueError("preprocessing must be a mapping")
    if "features" not in preprocessing:
        return PIPELINE_LEGACY
    features = preprocessing["features"]
    if features != PIPELINE_HARMONIZED:
        raise ValueError(f"unsupported preprocessing.features {features!r}")
    import mediapipe
    if preprocessing.get("extractor") != "CleanHolisticExtractor":
        raise ValueError(f"harmonized_v1 needs extractor 'CleanHolisticExtractor', got {preprocessing.get('extractor')!r}")
    if preprocessing.get("mediapipe_version") != mediapipe.__version__:
        raise ValueError(f"checkpoint mediapipe_version {preprocessing.get('mediapipe_version')!r} != installed "
                         f"{mediapipe.__version__!r}")
    ph = preprocessing.get("process_height", "missing")
    if not (ph is None or (_is_int(ph) and 1 <= ph <= 2160)):
        raise ValueError(f"process_height must be None or an int in 1..2160, got {ph!r}")
    tl = preprocessing.get("target_len")
    if not (_is_int(tl) and tl >= 2):
        raise ValueError(f"target_len must be an int >= 2, got {tl!r}")
    missing = [k for k in HARMONIZED_REQUIRED_KEYS if k not in preprocessing]
    if missing:
        raise ValueError(f"harmonized_v1 preprocessing is missing {missing}")
    return PIPELINE_HARMONIZED


def _pairs(block: np.ndarray):
    return [[round(float(x), 4), round(float(y), 4)] for x, y in block[:, :2]]


def overlay_landmarks(coords, vis) -> Dict[str, list]:
    """Skeleton overlay in the legacy message format, rebuilt from the 67-joint coords: pose = 25 [x, y] pairs
    (or [] when MediaPipe found no pose), each hand = 21 pairs or [] when missing. Values rounded to 4 digits;
    never NaN."""
    c = np.asarray(coords, dtype=np.float64)
    v = np.asarray(vis)
    pose = c[0:25]
    out = {"pose": _pairs(pose) if np.isfinite(pose[:, :2]).all() else []}
    for name, sl in (("left_hand", slice(25, 46)), ("right_hand", slice(46, 67))):
        block = c[sl]
        ok = bool((v[sl] > 0.5).all()) and bool(np.isfinite(block[:, :2]).all())
        out[name] = _pairs(block) if ok else []
    return out


class HarmonizedLiveSession:
    """One client session of the harmonized_v1 path: frame -> landmarks -> segmenter -> (harmonize -> predict)."""

    def __init__(self, predictor, preprocessing: Mapping[str, Any], segmenter_cfg: Mapping[str, Any] = SEGMENTER_DEFAULT,
                 extractor=None, record_clip: bool = False, top_k: int = 5):
        if live_pipeline_for(preprocessing) != PIPELINE_HARMONIZED:
            raise ValueError("HarmonizedLiveSession needs a harmonized_v1 checkpoint preprocessing")
        self.predictor = predictor
        self.preprocessing = preprocessing          # the checkpoint's dict itself: passed as cfg to harmonize()
        self.top_k = top_k
        self.segmenter = SignSegmenter(preprocessing, segmenter_cfg)
        if extractor is None:
            from src.data.landmark_extractor import CleanHolisticExtractor
            extractor = CleanHolisticExtractor(process_height=preprocessing["process_height"])
        self.extractor = extractor
        self.extractor._get_holistic()              # build the graph now; no dummy frame (tracker state)
        self._record = record_clip
        self._clip_kps, self._clip_vis, self._clip_t, self._clip_wh = [], [], [], set()

    @property
    def process_height(self) -> Optional[int]:
        return self.preprocessing["process_height"]

    # ------------------------------------------------------------------ core
    def _harmonize_buffer(self, kps, vis, t, frame_wh):
        """The one place live frames become model input (used by the segment path AND finalize_clip)."""
        t = np.asarray(t, dtype=np.float64)
        ts = t - t[0]
        n = len(ts)
        fps = (n - 1) / ts[-1] if n >= 2 and ts[-1] > 0 else 0.0
        aspect = frame_wh[0] / frame_wh[1]
        return harmonize(kps, vis, aspect, fps, cfg=self.preprocessing, timestamps_s=ts)

    def _event(self, ev) -> Dict[str, Any]:
        """Segmenter event -> sign_result / sign_discarded dict (+ finalize timings)."""
        if isinstance(ev, Discard):
            return {"type": "sign_discarded", "segment_id": ev.segment_id, "reason": ev.reason,
                    "segment": {"duration_s": ev.duration_s, "frames": ev.frames},
                    "metrics": {"harmonize_ms": None, "infer_ms": None, "finalize_ms": None}}
        assert isinstance(ev, Emit)
        q0 = perf_counter()
        seq, jm, tm = self._harmonize_buffer(ev.kps, ev.vis, ev.t, ev.frame_wh)
        q1 = perf_counter()
        pred = None
        if jm[:, 25:67].sum() > 0:
            pred = self.predictor.predict(seq, jm, tm, top_k=self.top_k)
        q2 = perf_counter()
        n = len(ev.t)
        duration = float(ev.t[-1] - ev.t[0])
        metrics = {"harmonize_ms": (q1 - q0) * 1000.0, "infer_ms": (q2 - q1) * 1000.0 if pred is not None else None,
                   "finalize_ms": (q2 - q0) * 1000.0}
        if pred is None:
            return {"type": "sign_discarded", "segment_id": ev.segment_id, "reason": "no_hand_frames",
                    "segment": {"duration_s": duration, "frames": n}, "metrics": metrics}
        top = [{"gloss": str(p["gloss"]), "confidence": float(p["confidence"])} for p in pred["top5"]]
        dropped = None if ev.seqs is None else int(ev.seqs[-1] - ev.seqs[0] + 1 - n)
        return {"type": "sign_result", "segment_id": ev.segment_id,
                "prediction": top[0]["gloss"], "gloss": top[0]["gloss"], "confidence": top[0]["confidence"],
                "top5": top, "end_reason": "rest",
                "segment": {"start_s": float(ev.t[0]), "end_s": float(ev.t[-1]), "duration_s": duration,
                            "frames": n, "effective_fps": (n - 1) / duration if duration > 0 else None,
                            "dropped_frames": dropped,
                            "active_start_s": ev.active_start_s, "active_end_s": ev.active_end_s},
                "metrics": {**metrics, "rest_hold_s": self.segmenter.params["rest_hold_s"]}}

    def process(self, frame_bgr: np.ndarray, t_s: float, seq: Optional[int] = None) -> Dict[str, Any]:
        """One BGR frame at time t_s (seconds, strictly increasing) -> landmarks, segmenter state, optional event.
        Timings (*_ms) come from time.perf_counter."""
        self.segmenter.validate_time(t_s)          # before MediaPipe: a rejected frame must not move the tracker
        p0 = perf_counter()
        coords, vis = self.extractor.extract_frame(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        p1 = perf_counter()
        h, w = frame_bgr.shape[:2]
        ev = self.segmenter.push(coords, vis, t_s, (w, h), seq=seq)
        p2 = perf_counter()
        if self._record:
            self._clip_kps.append(coords)
            self._clip_vis.append(vis)
            self._clip_t.append(float(t_s))
            self._clip_wh.add((w, h))
        event = self._event(ev) if ev is not None else None
        fin = (event or {}).get("metrics", {})
        return {"coords": coords, "vis": vis, "landmarks": overlay_landmarks(coords, vis),
                "hand_detected": bool(np.any(np.asarray(vis)[25:67] > 0.5)),
                "hand_active": bool(self.segmenter.hand_active),
                "event": event, "state": self.segmenter.state, "segment_id": self.segmenter.segment_id,
                "recording_s": self.segmenter.recording_s, "n_frames": self.segmenter.n_frames,
                "extract_ms": (p1 - p0) * 1000.0, "segment_ms": (p2 - p1) * 1000.0,
                "harmonize_ms": fin.get("harmonize_ms"), "infer_ms": fin.get("infer_ms"),
                "finalize_ms": fin.get("finalize_ms")}

    def reset(self) -> Optional[Dict[str, Any]]:
        ev = self.segmenter.reset()
        return self._event(ev) if ev is not None else None

    def finalize_clip(self) -> Dict[str, Any]:
        """TEST/REPORT ONLY (record_clip=True): harmonize every frame received so far, bypassing the segmenter,
        through the same _harmonize_buffer as the segment path."""
        if not self._record:
            raise RuntimeError("finalize_clip needs record_clip=True")
        if not self._clip_t:
            raise RuntimeError("no frame recorded")
        if len(self._clip_wh) != 1:
            raise ValueError(f"frame size changed within the clip: {sorted(self._clip_wh)}")
        kps, vis = np.stack(self._clip_kps), np.stack(self._clip_vis)
        t = np.asarray(self._clip_t, dtype=np.float64)
        seq, jm, tm = self._harmonize_buffer(kps, vis, t, next(iter(self._clip_wh)))
        return {"sequence": seq, "joint_mask": jm, "temporal_mask": tm, "keypoints": kps, "visibility_mask": vis,
                "timestamps_s": t}

    def close(self):
        self.extractor.close()
