#!/bin/bash
echo "============================================================"
echo "  Starting Vietnamese Sign Language Recognition (VSLR)"
echo "  FastAPI Production Backend (Clean Logging Mode)"
echo "============================================================"
echo

# Suppress TensorFlow / MediaPipe C++ log spam
export TF_CPP_MIN_LOG_LEVEL=3
export GLOG_minloglevel=3
export GLOG_logtostderr=0

# Detect python executable in virtualenv
if [ -f "./.venv/bin/python" ]; then
    PYTHON_EXEC="./.venv/bin/python"
elif [ -f "./.venv/Scripts/python.exe" ]; then
    PYTHON_EXEC="./.venv/Scripts/python.exe"
else
    PYTHON_EXEC="python"
fi

$PYTHON_EXEC -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
