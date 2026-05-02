@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Python\restart_unreal_mcp_stdio.ps1"

echo.
echo If Codex still shows the MCP transport as closed, reload/reconnect the unrealMCP server in Codex.
pause
