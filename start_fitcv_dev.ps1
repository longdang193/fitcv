param(
    [int]$HealthTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path $PSScriptRoot).Path
$configPath = Join-Path $root "config\dev-server.json"
$frontendRoot = Join-Path $root "frontend"
$webScript = Join-Path $root "start_web.ps1"
$bootstrapPath = Join-Path $env:APPDATA "FitCV\bootstrap.json"
$backend = $null
$frontend = $null

function Test-PortAvailable([int]$Port) {
    return -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Stop-ChildProcess($Process) {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$bootstrap = if (Test-Path -LiteralPath $bootstrapPath) {
    Get-Content -LiteralPath $bootstrapPath -Raw | ConvertFrom-Json
} else {
    $null
}
if ($null -eq $bootstrap -or [string]::IsNullOrWhiteSpace([string]$bootstrap.data_root)) {
    throw "FitCV Local bootstrap missing or invalid: $bootstrapPath"
}
$env:FITCV_LOCAL_MODE = "1"
$env:FITCV_CP_INLINE_EXECUTION = "1"
$hostName = [string]$config.host
$backendPort = [int]$config.backendPort
$frontendPort = [int]$config.frontendPort
if ([string]::IsNullOrWhiteSpace($hostName) -or $backendPort -notin 1..65535 -or $frontendPort -notin 1..65535) {
    throw "Invalid FitCV dev-server config: $configPath"
}
$apiOrigin = "http://${hostName}:$backendPort"

if (-not (Test-PortAvailable $backendPort)) {
    throw "FitCV backend port $backendPort is already in use. Stop existing FitCV processes or use the existing app."
}
if (-not (Test-PortAvailable $frontendPort)) {
    throw "FitCV frontend port $frontendPort is already in use. Stop existing Vite processes or use the existing app."
}

try {
    $backend = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "`"$webScript`"",
        "-Port",
        $backendPort
    ) -WorkingDirectory $root -WindowStyle Hidden -PassThru

    $deadline = [DateTime]::UtcNow.AddSeconds($HealthTimeoutSeconds)
    $healthy = $false
    $lastError = "no response"
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($backend.HasExited) {
            throw "FitCV backend exited before /healthz. Run .\start_web.ps1 directly for startup diagnostics."
        }
        try {
            $health = Invoke-WebRequest -Uri "$apiOrigin/healthz" -UseBasicParsing -TimeoutSec 2
            if ($health.StatusCode -eq 200) {
                $healthy = $true
                break
            }
            $lastError = "HTTP $($health.StatusCode)"
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $healthy) {
        throw "FitCV backend failed /healthz within $HealthTimeoutSeconds seconds: $lastError"
    }

    $frontend = Start-Process -FilePath "npm.cmd" -ArgumentList @(
        "run",
        "dev",
        "--",
        "--host",
        $hostName,
        "--port",
        $frontendPort
    ) -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru

    Write-Host "FitCV backend: $apiOrigin"
    Write-Host "FitCV app: http://${hostName}:$frontendPort/app/#/overview"
    Write-Host "Press Ctrl+C to stop both processes."
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 1
    }
    if ($backend.HasExited) {
        throw "FitCV backend stopped unexpectedly."
    }
    throw "FitCV frontend stopped unexpectedly."
} finally {
    Stop-ChildProcess $frontend
    Stop-ChildProcess $backend
}
