@echo off
setlocal
title Stop Unreal World Sim
cd /d "%~dp0"

echo ============================================================
echo  Stopping Unreal World Sim
echo  - Sim engine  : http://127.0.0.1:8777
echo  - Web cockpit : http://127.0.0.1:8765
echo ============================================================
echo.

echo Requesting a graceful simulation stop...
powershell -NoProfile -Command ^
  "try { Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8777/stop' -TimeoutSec 2 | Out-Null } catch {}"

echo Stopping listeners on the sim ports...
for %%P in (8777 8765) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
    echo   stopping PID %%A on port %%P
    taskkill /F /T /PID %%A >nul 2>&1
  )
)

echo Cleaning up orphaned project server processes...
powershell -NoProfile -Command ^
  "$patterns = @('sim_runner\.py\s+--port\s+8777', 'uvicorn\s+web_ui\.main:app.*--port\s+8765', 'Test-NetConnection\s+127\.0\.0\.1\s+-Port\s+8765');" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $cmd = $_.CommandLine; $cmd -and ($patterns | Where-Object { $cmd -match $_ }) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

rem Close command windows left behind by start_sim.bat after their child process exits.
taskkill /F /FI "WINDOWTITLE eq Sim Engine (sim_runner)" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Unreal World Sim" >nul 2>&1

timeout /t 1 /nobreak >nul

set "PORTS_BUSY="
for %%P in (8777 8765) do (
  netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING" >nul 2>&1
  if not errorlevel 1 (
    echo WARNING: port %%P is still in use.
    set "PORTS_BUSY=1"
  )
)

echo.
if defined PORTS_BUSY (
  echo Shutdown was incomplete. See the warnings above.
  echo Unreal PIE was not stopped.
  pause
  exit /b 1
)

echo Sim engine and web cockpit are stopped. Ports 8777 and 8765 are free.
echo Unreal PIE and unrelated browser windows were left alone.
echo The old cockpit tab can now be closed or reused after start_sim.bat runs again.
echo.
pause
exit /b 0
