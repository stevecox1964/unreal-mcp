@echo off
title Unreal World Sim
cd /d "%~dp0"

echo ============================================================
echo  Unreal World Sim - standalone (no Claude / MCP required)
echo  1) Make sure Unreal is running in PIE first.
echo  2) Sim engine  : http://127.0.0.1:8777  (sim_runner)
echo  3) Web cockpit : http://127.0.0.1:8765/sim  (opens automatically)
echo ============================================================
echo.

echo Stopping any previous sim engine / web cockpit...
rem Kill whatever is LISTENING on the sim engine (8777) and cockpit (8765) ports.
for %%P in (8777 8765) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
    echo   killing PID %%a on port %%P
    taskkill /F /PID %%a >nul 2>&1
  )
)
rem Also close any orphaned "Sim Engine" console window from a prior run.
taskkill /F /FI "WINDOWTITLE eq Sim Engine (sim_runner)" >nul 2>&1
rem Give the OS a moment to release the ports before rebinding.
timeout /t 1 /nobreak >nul
echo.

echo Starting sim engine in a new window...
start "Sim Engine (sim_runner)" cmd /k uv run python sim_runner.py --port 8777

echo Starting web cockpit (Ctrl+C to stop)...
echo The cockpit page will open in your browser when ready.
rem Open the cockpit once it's listening: polls up to 30s, opens it once, stays silent if the
rem server never binds (the console error above is already loud in that case).
start "" /min powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){ if(Test-NetConnection 127.0.0.1 -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue){ Start-Process 'http://127.0.0.1:8765/sim'; exit } Start-Sleep 1 }"
uv run python -m uvicorn web_ui.main:app --host 127.0.0.1 --port 8765
pause
