@echo off
title GeoSentinel-AI Launcher
echo ===================================================
echo   Starting GeoSentinel-AI Automated Dev Environment
echo ===================================================

:: 1. Check & Setup Python Virtual Environment
if not exist "backend\venv" (
    echo [*] Creating virtual environment and installing backend dependencies...
    python -m venv backend\venv
    call backend\venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
) else (
    echo [*] Python virtual environment ready.
)

:: 2. Check & Setup Frontend Packages
if not exist "frontend\node_modules" (
    echo [*] Installing frontend npm dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo [*] Frontend dependencies ready.
)

:: 3. Launch Backend and Frontend in Parallel Windows
echo [*] Launching FastAPI Backend on http://localhost:8000...
start "GeoSentinel Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] Launching Vite Frontend on http://localhost:5173...
start "GeoSentinel Frontend" cmd /k "cd frontend && npm run dev"

echo ===================================================
echo   System running! Open http://localhost:5173
echo ===================================================