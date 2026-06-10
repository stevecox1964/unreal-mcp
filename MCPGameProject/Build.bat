@echo off
set RESULTS=%~dp0build_results.txt
echo Building MCPGameProject (Editor)... output in "%RESULTS%"
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\Build.bat" MCPGameProjectEditor Win64 Development "%~dp0MCPGameProject.uproject" -WaitMutex > "%RESULTS%" 2>&1
echo.
if %ERRORLEVEL% == 0 (
    echo BUILD SUCCEEDED
    echo BUILD SUCCEEDED >> "%RESULTS%"
) else (
    echo BUILD FAILED - error code %ERRORLEVEL%
    echo BUILD FAILED - error code %ERRORLEVEL% >> "%RESULTS%"
)
echo.
cmd /k
