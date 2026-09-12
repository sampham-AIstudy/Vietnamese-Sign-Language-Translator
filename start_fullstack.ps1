# ==============================================================================
# VSL Translator - Fullstack Launch Script (ReactJS + Node.js + FastAPI)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🤟 VSL TRANSLATOR - FULLSTACK SYSTEM STARTER           " -ForegroundColor Cyan
Write-Host "  - Python AI Engine (FastAPI & WebSockets) : Port 8000  " -ForegroundColor Green
Write-Host "  - Node.js Backend Gateway & Dictionary    : Port 5000  " -ForegroundColor Yellow
Write-Host "  - ReactJS Modern Frontend (Vite)          : Port 3000  " -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Python FastAPI AI Backend
Write-Host "`n[1/3] Starting Python AI Backend (:8000)..." -ForegroundColor Green
Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "app.api.main:app --host 0.0.0.0 --port 8000 --reload" -NoNewWindow

Start-Sleep -Seconds 2

# 2. Start Node.js Backend
Write-Host "[2/3] Starting Node.js Backend Gateway (:5000)..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "backend/server.js" -NoNewWindow

Start-Sleep -Seconds 1

# 3. Start React Frontend (Vite)
Write-Host "[3/3] Starting React Frontend (:3000)..." -ForegroundColor Magenta
Set-Location -Path "frontend"
npm run dev
