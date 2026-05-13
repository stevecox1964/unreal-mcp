@echo off
title NPC Builder
cd /d "%~dp0"

echo Stopping any existing NPC Builder on port 8765...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo  NPC Builder starting at http://127.0.0.1:8765
echo  Press Ctrl+C to stop.
echo.
uv run uvicorn web_ui.main:app --host 127.0.0.1 --port 8765
pause
