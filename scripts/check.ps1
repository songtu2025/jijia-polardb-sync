$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = ".\.venv\Scripts\python.exe"

& $python -m ruff format --check backend
& $python -m ruff check backend
& $python -m mypy backend\app
& $python -m pytest backend\tests --cov=backend.app --cov-report=term-missing
& $python -m unittest discover -s tests -p "test_*.py"
& $python -m compileall -q app backend tests
& $python -m pip check

Push-Location -LiteralPath "frontend"
try {
    npm run lint
    npm run test -- --run
    npm run build
}
finally {
    Pop-Location
}

git diff --check
Write-Host "阶段 0 + M1 检查完成"
