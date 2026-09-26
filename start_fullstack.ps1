# ==============================================================================
# VSL Translator - Fullstack Launch Script (FastAPI + React 18 HUD)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🤟 VSL TRANSLATOR - FULLSTACK SYSTEM STARTER           " -ForegroundColor Cyan
Write-Host "  - Python AI Engine (FastAPI & WebSockets) : Port 8000  " -ForegroundColor Green
Write-Host "  - React 18 Modern Frontend (Vite)         : Port 3000  " -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Python FastAPI AI Backend
Write-Host "`n[1/2] Starting Python AI Backend (:8000)..." -ForegroundColor Green
Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "backend.main:app --host 0.0.0.0 --port 8000 --reload" -NoNewWindow

Start-Sleep -Seconds 2

# 2. Start React Frontend (Vite)
Write-Host "[2/2] Starting React Frontend (:3000)..." -ForegroundColor Magenta
Set-Location -Path "frontend"
npm run dev
