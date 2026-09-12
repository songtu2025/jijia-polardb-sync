$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

& ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& ".\.venv\Scripts\python.exe" -m dotenv -f .env.localtest run --override -- `
    ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app `
    --host 127.0.0.1 `
    --port 8004
exit $LASTEXITCODE
