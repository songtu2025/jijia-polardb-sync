$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

& ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime setup `
    --confirm-local-isolated
exit $LASTEXITCODE
