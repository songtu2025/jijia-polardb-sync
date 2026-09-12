$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$schedulerMutex = [System.Threading.Mutex]::new($false, "Local\JijiaSyncLocalScheduler")
$schedulerMutexAcquired = $false

try {
    $schedulerMutexAcquired = $schedulerMutex.WaitOne(0)
    if (-not $schedulerMutexAcquired) {
        Write-Error "本地常驻 Scheduler 已经在运行。"
        exit 2
    }

    & ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime ensure-jijia-target
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & ".\.venv\Scripts\python.exe" -m scripts.local_test_runtime check
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & ".\.venv\Scripts\python.exe" -m dotenv -f .env.localtest run --override -- `
        ".\.venv\Scripts\python.exe" -m backend.app.scheduler
    exit $LASTEXITCODE
}
finally {
    if ($schedulerMutexAcquired) {
        $schedulerMutex.ReleaseMutex()
    }
    $schedulerMutex.Dispose()
}
