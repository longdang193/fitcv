[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SecretFile,
    [string]$SecretKey = "FITCV_LLM_API_KEY",
    [string]$CodexConfigPath = (Join-Path $HOME ".codex\config.toml"),
    [string]$UvPath = (Join-Path $HOME ".local\bin\uv.exe"),
    [switch]$SkipInstall,
    [switch]$ResetConfig
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $HOME ".local\share\dcode-project"
$binRoot = Join-Path $HOME ".local\bin"
$launcherSource = Join-Path $repoRoot "scripts\dcode_project.py"
$directMcpConfig = Join-Path $HOME ".deepagents\.mcp.json"

if (-not (Test-Path $launcherSource -PathType Leaf)) {
    throw "Missing launcher source: $launcherSource"
}
if (-not (Test-Path $CodexConfigPath -PathType Leaf)) {
    throw "Missing Codex config: $CodexConfigPath"
}
if (-not (Test-Path $SecretFile -PathType Leaf)) {
    throw "Missing secret file: $SecretFile"
}
if (Test-Path -LiteralPath $directMcpConfig -PathType Leaf) {
    throw "Direct DeepAgents MCP config detected: $directMcpConfig. Remove it before setup: Remove-Item -LiteralPath '$directMcpConfig' -Force"
}

if (-not $SkipInstall) {
    if (-not (Test-Path $UvPath -PathType Leaf)) {
        $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
        if ($null -eq $uvCommand) {
            throw "uv is required to install DeepAgents Code. Pass -UvPath or install uv."
        }
        $UvPath = $uvCommand.Source
    }
    & $UvPath tool install --reinstall deepagents-code
    if ($LASTEXITCODE -ne 0) {
        throw "DeepAgents Code installation failed."
    }
}

New-Item -ItemType Directory -Force -Path $runtimeRoot, $binRoot | Out-Null

$configPath = Join-Path $runtimeRoot "config.toml"
if ($ResetConfig -or -not (Test-Path $configPath -PathType Leaf)) {
    $escapeToml = {
        param([string]$Value)
        $Value.Replace("\", "\\").Replace('"', '\"')
    }
    $config = @"
[paths]
codex_config = "$( & $escapeToml $CodexConfigPath )"
secret_file = "$( & $escapeToml ((Resolve-Path $SecretFile).Path ) )"
secret_key = "$( & $escapeToml $SecretKey )"
"@
    Set-Content -NoNewline -Encoding utf8 $configPath $config
}
Remove-Item -LiteralPath (Join-Path $runtimeRoot "dcode_project.py") -Force -ErrorAction SilentlyContinue

$wrapper = @'
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DcodeArgs
)

$ErrorActionPreference = "Stop"
$repoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repoRoot) {
    Write-Error "dcode-project: run inside a Git repository."
    exit 2
}

& py -3 (Join-Path $repoRoot "scripts\dcode_project.py") @DcodeArgs
exit $LASTEXITCODE
'@
Set-Content -NoNewline -Encoding utf8 (Join-Path $binRoot "dcode-project.ps1") $wrapper

$cmd = @'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dcode-project.ps1" %*
'@
Set-Content -NoNewline -Encoding ascii (Join-Path $binRoot "dcode-project.cmd") $cmd

Write-Output "Installed dcode-project at $(Join-Path $binRoot 'dcode-project.cmd')"
Write-Output "dcode-project uses the active Codex provider binding but runs DeepAgents without MCP projection."
