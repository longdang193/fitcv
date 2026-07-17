param([Parameter(Mandatory)][string]$BundlePath)

$ErrorActionPreference = "Stop"
$bundle = (Resolve-Path $BundlePath).Path
$exe = Join-Path $bundle "fitcv-local.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "fitcv-local.exe missing" }
$requiredPromptAssets = @(
    "enrich_extraction_v1.md",
    "ranking_ai_score_v2.md",
    "cv_generation_structured_write_v1.md",
    "synonym_triage_recommendation_v1.md"
)
$trayIconPath = Join-Path $bundle "_internal\fitcv.ico"
if (-not (Test-Path -LiteralPath $trayIconPath)) { throw "fitcv.ico missing" }
foreach ($promptAsset in $requiredPromptAssets) {
    $promptPath = Join-Path $bundle "_internal\fitcv\prompts\templates\$promptAsset"
    if (-not (Test-Path -LiteralPath $promptPath)) { throw "$promptAsset missing" }
}
$size = (Get-ChildItem -LiteralPath $bundle -Recurse -File | Measure-Object Length -Sum).Sum
if ($size -gt 600MB) { throw "Bundle exceeds 600MB" }

$started = Get-Date
$env:FITCV_NO_BROWSER = "1"
$process = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
try {
    $runtime = $null
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        $bootstrapPath = Join-Path $env:APPDATA "FitCV\bootstrap.json"
        if (Test-Path -LiteralPath $bootstrapPath) {
            $bootstrap = Get-Content -LiteralPath $bootstrapPath -Raw | ConvertFrom-Json
            $runtimePath = Join-Path $bootstrap.data_root ".fitcv-local-runtime.json"
            if (Test-Path -LiteralPath $runtimePath) {
                $candidate = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
                if ([int]$candidate.pid -eq $process.Id) { $runtime = $candidate; break }
            }
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $runtime) { throw "Runtime metadata not created" }
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $healthStarted = Get-Date
    $health = Invoke-WebRequest -Uri ($runtime.url + "healthz") -WebSession $session -UseBasicParsing
    if ($health.StatusCode -ne 200 -or ((Get-Date) - $healthStarted).TotalSeconds -gt 8) { throw "/healthz failed budget" }
    $page = Invoke-WebRequest -Uri ($runtime.url + "local/onboarding") -WebSession $session -UseBasicParsing
    if ($page.StatusCode -ne 200 -or ((Get-Date) - $started).TotalSeconds -gt 10) { throw "/local/onboarding failed budget" }
    if (-not ($session.Cookies.GetCookies($runtime.url)["fitcv_csrf"])) { throw "fitcv_csrf cookie missing" }
    if ($process.WorkingSet64 -gt 250MB) { throw "Idle RSS exceeds 250MB" }

    # second instance must reuse running app and exit.
    $second = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    if (-not $second.WaitForExit(5000)) { throw "second instance did not exit" }

    $origin = ([Uri]$runtime.url).GetLeftPart([System.UriPartial]::Authority)
    $shutdown = Invoke-WebRequest -Uri ($runtime.url + "local/system/shutdown") -Method Post -Headers @{ Origin = $origin } -WebSession $session -UseBasicParsing
    if ($shutdown.StatusCode -ne 200) { throw "/local/system/shutdown failed" }
    if (-not $process.WaitForExit(10000)) { throw "FitCV Local did not stop" }
}
finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
