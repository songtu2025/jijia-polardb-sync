param(
    [string]$WorkerName = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not [string]::IsNullOrWhiteSpace($WorkerName)) {
    $env:WORKER_NAME = $WorkerName
}

& ".\.venv\Scripts\python.exe" -m backend.app.worker
