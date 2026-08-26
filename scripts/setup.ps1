$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-dev.txt

Push-Location -LiteralPath "frontend"
try {
    npm install
}
finally {
    Pop-Location
}

Write-Host "开发依赖安装完成"
