param(
    [string]$Version = "0.1.0",
    [string]$BuildId = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dist = Join-Path $root "dist"
$build = Join-Path $root "build"
if (-not $BuildId) { $BuildId = (git -C $root rev-parse --short HEAD).Trim() }
$env:FITCV_BUILD_ID = $BuildId

foreach ($path in @($dist, $build)) {
    $full = [System.IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean path outside repository: $full"
    }
    if (Test-Path -LiteralPath $full) { Remove-Item -LiteralPath $full -Recurse -Force }
}

Push-Location $root
try {
    uv run --extra local python -c "import fitcv_cp.local_app, fitcv_cp.local_routes, keyring; print('FitCV Local import smoke passed')"
    uv run --group build PyInstaller .\packaging\windows\fitcv-local.spec --clean --noconfirm
    $bundle = Join-Path $dist "fitcv-local"
    if (-not (Test-Path -LiteralPath (Join-Path $bundle "fitcv-local.exe"))) { throw "Bundle executable missing" }
    $size = (Get-ChildItem -LiteralPath $bundle -Recurse -File | Measure-Object Length -Sum).Sum
    if ($size -gt 600MB) { throw "Bundle exceeds 600MB budget: $size bytes" }
    @{ version = $Version; build_id = $BuildId; technical_preview = $true; bundle_bytes = $size } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $bundle "build.json") -Encoding utf8
    Get-ChildItem -LiteralPath $bundle -Recurse -File | Get-FileHash -Algorithm SHA256 |
        ForEach-Object { "$($_.Hash.ToLower())  $($_.Path.Substring($bundle.Length + 1))" } |
        Set-Content -LiteralPath (Join-Path $dist "SHA256SUMS.txt") -Encoding ascii
    $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $isccPath = if ($iscc) { $iscc.Source } else {
        @(
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
        ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if ($isccPath) {
        & $isccPath .\packaging\windows\FitCV.iss
        Get-ChildItem -LiteralPath (Join-Path $dist "installer") -File | Get-FileHash -Algorithm SHA256 |
            ForEach-Object { "$($_.Hash.ToLower())  installer/$($_.Path | Split-Path -Leaf)" } |
            Add-Content -LiteralPath (Join-Path $dist "SHA256SUMS.txt") -Encoding ascii
    }
    else { Write-Warning "Inno Setup not found; bundle remains Technical Preview." }
}
finally {
    Pop-Location
}
