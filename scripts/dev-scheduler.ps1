$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

& ".\.venv\Scripts\python.exe" -m backend.app.scheduler
