param(
    [string]$HostRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\codex-harness-host')
)

$ErrorActionPreference = 'Stop'

$hostPath = (Resolve-Path -LiteralPath $HostRoot).Path

& harness-core-launcher upgrade --host-root $hostPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& harness-core-launcher doctor
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& harness-core-launcher preflight
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
