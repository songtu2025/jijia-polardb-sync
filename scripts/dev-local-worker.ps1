param(
    [string]$WorkerName = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if ([string]::IsNullOrWhiteSpace($WorkerName)) {
    $WorkerName = "local-$env:COMPUTERNAME-$PID"
}
$env:WORKER_NAME = $WorkerName

$workerMutex = [System.Threading.Mutex]::new($false, "Local\JijiaSyncLocalWorker-$WorkerName")
$workerMutexAcquired = $false

try {
    $workerMutexAcquired = $workerMutex.WaitOne(0)
    if (-not $workerMutexAcquired) {
        Write-Error "本地 Worker '$WorkerName' 已经在运行。"
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
        ".\.venv\Scripts\python.exe" -m backend.app.worker
    exit $LASTEXITCODE
}
finally {
    if ($workerMutexAcquired) {
        $workerMutex.ReleaseMutex()
    }
    $workerMutex.Dispose()
}
