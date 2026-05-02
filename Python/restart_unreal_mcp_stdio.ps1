$ErrorActionPreference = "Stop"

$pythonDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $pythonDir
$server = Join-Path $pythonDir "unreal_mcp_server.py"

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -like "*$server*" -and
    ($_.Name -eq "python.exe" -or $_.Name -eq "uv.exe")
}

foreach ($target in $targets) {
    Stop-Process -Id $target.ProcessId -Force
}

Write-Output "Stopped $($targets.Count) Unreal MCP stdio process(es) for $repoRoot"
Write-Output "Reconnect or reload the MCP server from the client so it can spawn a fresh stdio child."
