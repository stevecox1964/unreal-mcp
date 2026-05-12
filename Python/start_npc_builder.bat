@echo off
title NPC Builder
cd /d "%~dp0"
echo.
echo  NPC Builder starting at http://127.0.0.1:8765
echo  Press Ctrl+C to stop.
echo.
uv run uvicorn web_ui.main:app --host 127.0.0.1 --port 8765
pause
