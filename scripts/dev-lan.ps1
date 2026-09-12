[CmdletBinding()]
param(
    [string]$ListenAddress = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ListenAddress)) {
    $network = Get-NetIPConfiguration |
        Where-Object {
            $_.NetAdapter.Status -eq "Up" -and
            $_.NetAdapter.HardwareInterface -and
            $_.IPv4DefaultGateway -ne $null -and
            $_.IPv4Address -ne $null
        } |
        Sort-Object { $_.NetAdapter.InterfaceMetric } |
        Select-Object -First 1

    if ($null -eq $network) {
        Write-Error "No active physical LAN adapter was found. Use -ListenAddress to select a local IPv4 address."
        exit 2
    }
    $ListenAddress = ($network.IPv4Address | Select-Object -First 1).IPAddress
}

$localAddress = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $ListenAddress `
    -ErrorAction SilentlyContinue
if ($null -eq $localAddress) {
    Write-Error "Address $ListenAddress is not assigned to a local IPv4 adapter."
    exit 2
}

$env:DEV_WEB_HOST = $ListenAddress
$env:LAN_PUBLIC_WEB_URL = "http://${ListenAddress}:5183"

Write-Host "LAN URL: $env:LAN_PUBLIC_WEB_URL"
Write-Host "API and Worker remain local-only."

& (Join-Path $PSScriptRoot "dev-local.ps1")
exit $LASTEXITCODE
