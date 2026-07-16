# Reproduction Steps

## Missing Packaged Config

1. Remove `packaging/windows/.env.yaml` from PyInstaller data files.
2. Build bundle.
3. Launch executable with isolated user-data directories.

```powershell
$env:APPDATA = "$PWD\tmp\fitcv-local-repro\Roaming"
$env:LOCALAPPDATA = "$PWD\tmp\fitcv-local-repro\Local"
uv run --group build PyInstaller .\packaging\windows\fitcv-local.spec --clean --noconfirm
.\dist\fitcv-local\fitcv-local.exe
```

Expected: `/healthz` returns HTTP 200.

Actual: process exits with `FileNotFoundError: Config file not found: .env.yaml`.

## Windowed Standard Streams

1. Restore packaged `.env.yaml`.
2. Remove `packaging/windows/pyi_rth_stdio.py` from `runtime_hooks`.
3. Build windowed bundle and launch with isolated user-data directories.
4. Read `.fitcv-local-runtime.json` and request `/healthz`.

```powershell
$runtime = Get-Content "$env:LOCALAPPDATA\FitCV\data\.fitcv-local-runtime.json" -Raw | ConvertFrom-Json
Invoke-WebRequest -Uri ($runtime.url + "healthz") -UseBasicParsing -TimeoutSec 8
```

Expected: request returns HTTP 200 within eight seconds.

Actual: request times out while process remains listening.

## Resolution Check

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_fitcv_local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
```
