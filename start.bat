@echo off
title Seabot Launcher
echo ===================================================
echo   Starting Seabot: Offline Maritime RAG Chatbot
echo ===================================================

set ROOT_DIR=%~dp0
set PYTHON_EXE=C:\Users\Sunit Kamble\AppData\Local\Programs\Python\Python311\python.exe
set NODE_EXE=C:\Users\Sunit Kamble\.gemini\antigravity\scratch\node-v20.18.0-win-x64\node.exe
set OLLAMA_EXE=C:\Users\Sunit Kamble\AppData\Local\Programs\Ollama\ollama.exe

:: 1. Start Ollama in background if present
echo [1/3] Ensuring Ollama is running...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="1" (
    start "" "%OLLAMA_EXE%" serve
    echo Started Ollama server.
) else (
    echo Ollama server is already running.
)

:: 2. Start Backend API on port 8001
echo [2/3] Starting Seabot Backend API (Port 8001)...
cd /d "%ROOT_DIR%backend"
start "Seabot Backend" "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001

:: 3. Start Frontend UI on port 3000
echo [3/3] Starting Seabot Frontend UI (Port 3000)...
cd /d "%ROOT_DIR%frontend"
start "Seabot Frontend" "%NODE_EXE%" "node_modules/vite/bin/vite.js" --port 3000 --host 0.0.0.0

echo.
echo ===================================================
echo   Seabot is up and running!
echo   Opening http://127.0.0.1:3000 in your browser...
echo ===================================================

ping 127.0.0.1 -n 3 >nul
start http://127.0.0.1:3000
