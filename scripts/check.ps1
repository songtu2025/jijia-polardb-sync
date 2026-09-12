$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = ".\.venv\Scripts\python.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked { & $python -m ruff format --check backend } "Ruff format"
Invoke-Checked { & $python -m ruff check backend } "Ruff check"
Invoke-Checked { & $python -m mypy backend\app } "Mypy"
Invoke-Checked { & $python -m pytest tests\test_e2e_app.py -q } "E2E isolation pytest"
Invoke-Checked { & $python -m pytest backend\tests --cov=backend.app --cov-report=term-missing } "Pytest"
Invoke-Checked { & $python -m unittest discover -s tests -p "test_*.py" } "Unittest"
Invoke-Checked { & $python -m compileall -q app backend tests } "Compileall"
Invoke-Checked { & $python -m pip check } "Pip check"

Push-Location -LiteralPath "frontend"
try {
    Invoke-Checked { npm run format:check } "Frontend format"
    Invoke-Checked { npm run lint:eslint } "Frontend ESLint"
    Invoke-Checked { npm run typecheck } "Frontend TypeScript"
    Invoke-Checked { npm run test -- --run --maxWorkers=1 } "Frontend test"
    Invoke-Checked { npm run build } "Frontend build"
}
finally {
    Pop-Location
}

Invoke-Checked { npm run check:duplicates } "Duplicate code"
Invoke-Checked { npm run check:unused } "Frontend dead code"
Invoke-Checked { & $python -m vulture backend\app --min-confidence 100 } "Backend dead code"
Invoke-Checked { & $python scripts\check_sensitive_literals.py } "Sensitive literal scan"
Invoke-Checked { git diff --check } "Git diff check"
Write-Host "Local project checks completed; external MySQL/PolarDB and migration approval are not included."
