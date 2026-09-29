#!/usr/bin/env bash
# VSLT — setup script for a Claude Code on the web cloud environment (Ubuntu 24.04, runs as root, cached ~7 days).
# Paste this whole file into the environment's "Setup script" box. It must finish in ~5 min to be cached and must exit 0.
# Network access must be "Custom" with the default list PLUS: download.pytorch.org, www.kaggle.com, api.kaggle.com,
# storage.googleapis.com (see docs/CLOUD.md).
#
# It builds a Python virtualenv OUTSIDE the repo at /opt/vslt-venv with the versions used locally
# (mediapipe MUST be 0.10.14: the checkpoints record it and the backend refuses a mismatch).
# torch/torchvision are the CPU builds (no GPU in the cloud VM; heavy training stays on Kaggle).
set -euo pipefail

PY=python3.11
if ! command -v "$PY" >/dev/null 2>&1; then
  # mediapipe 0.10.14 has wheels for Python 3.9-3.12; fall back to the image's python3 if it is <= 3.12.
  PY=python3
fi
"$PY" -c 'import sys; assert sys.version_info[:2] <= (3, 12), f"mediapipe 0.10.14 needs Python <= 3.12, got {sys.version}"'

"$PY" -m venv /opt/vslt-venv
/opt/vslt-venv/bin/python -m pip install --upgrade pip wheel

/opt/vslt-venv/bin/pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.6.0 torchvision==0.21.0

/opt/vslt-venv/bin/pip install \
  mediapipe==0.10.14 \
  "numpy==2.4.6" "pandas==3.0.5" "scipy==1.17.1" "scikit-learn==1.9.1" \
  "opencv-python-headless==5.0.0.93" "pillow==12.3.0" "protobuf==4.25.9" \
  "fastapi==0.141.1" "starlette==1.6.0" "uvicorn[standard]==0.52.4" "websockets==16.1.1" \
  "pydantic==2.13.5" "python-multipart==0.0.32" "httpx==0.28.1" \
  "PyYAML==6.0.3" "matplotlib==3.11.1" "kaggle==2.2.4"

/opt/vslt-venv/bin/python -c "import mediapipe, torch, cv2, numpy; print('vslt-venv ok', mediapipe.__version__, torch.__version__, cv2.__version__, numpy.__version__)"
