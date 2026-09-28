"""
Inference module for Vietnamese Sign Language (VSL) real-time translation.

The package-level names are imported lazily (PEP 562), so that the pure-numpy submodules
(e.g. src.inference.sign_segmenter) can be imported without loading torch, cv2 or mediapipe.
`from src.inference import VSLPredictor` keeps working as before.
"""
import importlib

__all__ = ["VSLREnsemble", "VSLPredictor", "RealtimePipeline", "TemporalSmoother"]

_LAZY = {
    "VSLREnsemble": "src.inference.ensemble",
    "VSLPredictor": "src.inference.predictor",
    "RealtimePipeline": "src.inference.realtime_pipeline",
    "TemporalSmoother": "src.inference.smoother",
}


def __getattr__(name):
    if name in _LAZY:
        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
