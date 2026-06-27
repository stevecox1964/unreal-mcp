@echo off
title Unreal World Sim
cd /d "%~dp0"

echo ============================================================
echo  Unreal World Sim - standalone (no Claude / MCP required)
echo  1) Make sure Unreal is running in PIE first.
echo  2) Sim engine  : http://127.0.0.1:8777  (sim_runner)
echo  3) Web cockpit : http://127.0.0.1:8765/sim
echo ============================================================
echo.

echo Starting sim engine in a new window...
start "Sim Engine (sim_runner)" cmd /k uv run python sim_runner.py --port 8777

echo Starting web cockpit (Ctrl+C to stop)...
echo Open http://127.0.0.1:8765/sim
uv run python -m uvicorn web_ui.main:app --host 127.0.0.1 --port 8765
pause
