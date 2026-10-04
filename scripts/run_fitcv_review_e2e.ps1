$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$e2eRoot = Join-Path $env:TEMP ("fitcv-p1ab-e2e-" + [guid]::NewGuid().ToString("N"))
$manifest = Join-Path $e2eRoot "manifest.json"
$database = Join-Path $e2eRoot "control-plane.sqlite3"
$stdout = Join-Path $e2eRoot "server.stdout.log"
$stderr = Join-Path $e2eRoot "server.stderr.log"
$server = $null
try {
    if (Test-Path -LiteralPath $e2eRoot) { throw "e2e_root_exists" }
    New-Item -ItemType Directory -Path $e2eRoot | Out-Null
    if (Test-Path -LiteralPath $database) { throw "database_exists_before_seed" }

    npm --prefix (Join-Path $repo "frontend") run build
    if ($LASTEXITCODE -ne 0) { throw "frontend_build_failed:$LASTEXITCODE" }
    $env:FITCV_LOCAL_MODE = "0"
    $env:FITCV_CP_INLINE_EXECUTION = "1"
    $env:FITCV_REVIEW_E2E = "1"
    $env:FITCV_CP_SQLITE_PATH = $database
    python (Join-Path $repo "scripts/seed_fitcv_review_e2e.py") --database $database --manifest $manifest
    if ($LASTEXITCODE -ne 0) { throw "seed_failed:$LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $manifest)) { throw "seed_manifest_missing" }
    $serverScript = Join-Path $repo "scripts/serve_fitcv_review_e2e.py"
    $server = Start-Process -FilePath python -ArgumentList @(
        "-u", ('"' + $serverScript + '"'),
        "--manifest", $manifest,
        "--port", "8000"
    ) -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 250
        try {
            $health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing
            $diag = Invoke-RestMethod -Uri "http://127.0.0.1:8000/__e2e/diagnostics"
            if ($health.StatusCode -eq 200 -and $diag.database -eq [IO.Path]::GetFullPath($database) -and $diag.fitcv_local_mode -eq "0" -and $diag.inline_execution -eq "1") {
                $ready = $true
                break
            }
        } catch { }
    }
    if (-not $ready) { throw "owned_server_not_ready" }
    $env:FITCV_E2E_MANIFEST = $manifest
    npm --prefix (Join-Path $repo "frontend") run test:e2e -- integration-flows.spec.ts -g "real review flow"
    if ($LASTEXITCODE -ne 0) { throw "browser_e2e_failed:$LASTEXITCODE" }
    exit 0
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
        Wait-Process -Id $server.Id -Timeout 10 -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $e2eRoot) {
        Remove-Item -LiteralPath $e2eRoot -Recurse -Force
    }
}
