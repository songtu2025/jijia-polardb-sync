$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

& ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime ensure-jijia-target
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime check
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

# 仅用于开发诊断：最多领取一条任务后立即退出。
& ".\.venv\Scripts\python.exe" -m dotenv -f .env.localtest run --override -- `
    ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime worker-once
exit $LASTEXITCODE
