@echo off
echo ============================================================
echo   Starting Vietnamese Sign Language Recognition (VSLR)
echo   FastAPI Production Backend (Clean Logging Mode)
echo ============================================================
echo.

:: Suppress TensorFlow / MediaPipe C++ log spam
set TF_CPP_MIN_LOG_LEVEL=3
set GLOG_minloglevel=3
set GLOG_logtostderr=0

:: Check virtual environment
if exist ".\.venv\Scripts\python.exe" (
    set PYTHON_EXEC=.\.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

%PYTHON_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
