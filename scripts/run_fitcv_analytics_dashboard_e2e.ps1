$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$port = 8000
$connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($connection) {
    throw "Port $port is already occupied. Stop the existing process before running dashboard E2E."
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("fitcv-analytics-dashboard-" + [guid]::NewGuid().ToString("N"))
$sourceDatabase = Join-Path $tempRoot "analytics-source.sqlite3"
$controlDatabase = Join-Path $tempRoot "control-plane.sqlite3"
$outputRoot = Join-Path $tempRoot "analytics"
$serverLog = Join-Path $tempRoot "server.log"
$serverError = Join-Path $tempRoot "server.err"
$server = $null
$previous = @{}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $sourceCommit = (git -C $repoRoot rev-parse HEAD).Trim()
    $previous["FITCV_CP_SQLITE_PATH"] = $env:FITCV_CP_SQLITE_PATH
    $previous["FITCV_ANALYTICS_OUTPUT_ROOT"] = $env:FITCV_ANALYTICS_OUTPUT_ROOT
    $previous["FITCV_ANALYTICS_SOURCE_COMMIT"] = $env:FITCV_ANALYTICS_SOURCE_COMMIT
    $previous["FITCV_CP_INLINE_EXECUTION"] = $env:FITCV_CP_INLINE_EXECUTION
    $env:FITCV_CP_SQLITE_PATH = $controlDatabase
    $env:FITCV_ANALYTICS_OUTPUT_ROOT = $outputRoot
    $env:FITCV_ANALYTICS_SOURCE_COMMIT = $sourceCommit
    $env:FITCV_CP_INLINE_EXECUTION = "1"

    $fixture = "from pathlib import Path; from tests.test_export_fitcv_analytics_source import _seed_database; from scripts.refresh_fitcv_analytics import refresh_analytics; db=Path(r'$sourceDatabase'); out=Path(r'$outputRoot'); _seed_database(db); refresh_analytics(db, out, source_commit='$sourceCommit')"
    python -c $fixture
    npm --prefix (Join-Path $repoRoot "frontend") run build

    $python = "python.exe"
    $server = Start-Process $python -ArgumentList "-m", "uvicorn", "fitcv_cp.main:app", "--host", "127.0.0.1", "--port", "$port" -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $serverLog -RedirectStandardError $serverError
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-WebRequest -Uri "http://127.0.0.1:$port/healthz" -UseBasicParsing
            if ($health.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) {
        if (Test-Path $serverError) { Get-Content $serverError }
        if (Test-Path $serverLog) { Get-Content $serverLog }
        throw "Dashboard backend did not become ready."
    }
    npm --prefix (Join-Path $repoRoot "frontend") run test:e2e -- e2e/analytics-dashboard.spec.ts
} finally {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
    foreach ($name in $previous.Keys) {
        if ($null -eq $previous[$name]) { Remove-Item -Path ("Env:" + $name) -ErrorAction SilentlyContinue }
        else { Set-Item -Path ("Env:" + $name) -Value $previous[$name] }
    }
    if (Test-Path $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
