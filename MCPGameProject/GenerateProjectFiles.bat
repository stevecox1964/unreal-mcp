@echo off
echo Generating Visual Studio project files...
"C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles\GenerateProjectFiles.bat" "%~dp0MCPGameProject.uproject" -Game
echo.
echo Done. Press any key to close.
pause
