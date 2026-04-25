@echo off
echo Building MCPGameProject (Editor)...
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\Build.bat" MCPGameProjectEditor Win64 Development "%~dp0MCPGameProject.uproject" -WaitMutex
echo.
if %ERRORLEVEL% == 0 (
    echo BUILD SUCCEEDED
) else (
    echo BUILD FAILED - error code %ERRORLEVEL%
)
echo.
cmd /k
