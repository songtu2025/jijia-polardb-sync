$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $projectRoot "frontend")

$webHost = if ([string]::IsNullOrWhiteSpace($env:DEV_WEB_HOST)) {
    "127.0.0.1"
}
else {
    $env:DEV_WEB_HOST
}

$env:DEV_PROXY_TARGET = "http://127.0.0.1:8004"
npm run dev -- --host $webHost --port 5183 --strictPort
exit $LASTEXITCODE
