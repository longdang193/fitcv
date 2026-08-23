[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SecretFile,
    [string]$SecretKey = "FITCV_LLM_API_KEY",
    [string]$CodexConfigPath = (Join-Path $HOME ".codex\config.toml"),
    [string]$UvPath = (Join-Path $HOME ".local\bin\uv.exe"),
    [string]$DeepAgentsCodeVersion = "0.1.59",
    [switch]$SkipInstall,
    [switch]$ResetConfig
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $HOME ".local\share\dcode-project"
$binRoot = Join-Path $HOME ".local\bin"
$deepAgentsToolRoot = Join-Path $runtimeRoot "deepagents-tool"
$deepAgentsBinRoot = Join-Path $runtimeRoot "bin"
$launcherSource = Join-Path $repoRoot "scripts\dcode_project.py"
$directMcpConfig = Join-Path $HOME ".deepagents\.mcp.json"
$pythonCommand = Get-Command py -ErrorAction SilentlyContinue

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
if ($null -eq $pythonCommand) {
    throw "Python launcher `py` is required. Install Python 3.12 or newer."
}
$pythonVersion = (& $pythonCommand.Source -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($LASTEXITCODE -ne 0 -or [version]$pythonVersion -lt [version]"3.12") {
    throw "DeepAgents Code requires Python 3.12 or newer; detected $pythonVersion."
}

if (-not $SkipInstall) {
    if (-not (Test-Path $UvPath -PathType Leaf)) {
        $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
        if ($null -eq $uvCommand) {
            throw "uv is required to install DeepAgents Code. Pass -UvPath or install uv."
        }
        $UvPath = $uvCommand.Source
    }
    $env:UV_TOOL_DIR = $deepAgentsToolRoot
    $env:UV_TOOL_BIN_DIR = $deepAgentsBinRoot
    & $UvPath tool install --reinstall "deepagents-code==$DeepAgentsCodeVersion"
    if ($LASTEXITCODE -ne 0) {
        throw "DeepAgents Code installation failed."
    }
}

$dcodePath = Join-Path $deepAgentsBinRoot "dcode.exe"
if (-not (Test-Path $dcodePath -PathType Leaf)) {
    $dcodeCommand = Get-Command dcode -ErrorAction SilentlyContinue
    if ($null -ne $dcodeCommand) {
        $dcodePath = $dcodeCommand.Source
    }
}
if (-not (Test-Path $dcodePath -PathType Leaf)) {
    throw "DeepAgents Code executable not found after setup."
}
$versionOutput = (& $dcodePath --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $versionOutput -notmatch "deepagents-code\s+$([regex]::Escape($DeepAgentsCodeVersion))") {
    throw "DeepAgents Code version mismatch. Expected $DeepAgentsCodeVersion; got: $versionOutput"
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

$doctorWrapper = @'
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DcodeArgs
)

$ErrorActionPreference = "Stop"
$env:DEEPAGENTS_CODE_UI_CHARSET_MODE = "ascii"
$dcodePath = Join-Path $HOME ".local\share\dcode-project\bin\dcode.exe"
if (-not (Test-Path $dcodePath -PathType Leaf)) {
    Write-Error "dcode-doctor: isolated DeepAgents Code executable not found. Run setup_deepagents_runtime.ps1."
    exit 2
}

& $dcodePath doctor @DcodeArgs
exit $LASTEXITCODE
'@
Set-Content -NoNewline -Encoding utf8 (Join-Path $binRoot "dcode-doctor.ps1") $doctorWrapper

$doctorCmd = @'
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dcode-doctor.ps1" %*
'@
Set-Content -NoNewline -Encoding ascii (Join-Path $binRoot "dcode-doctor.cmd") $doctorCmd

Write-Output "Installed dcode-project at $(Join-Path $binRoot 'dcode-project.cmd')"
Write-Output "Installed dcode-doctor at $(Join-Path $binRoot 'dcode-doctor.cmd')"
Write-Output "DeepAgents Code $DeepAgentsCodeVersion verified with Python $pythonVersion"
Write-Output "dcode-project uses the active Codex provider binding but runs DeepAgents without MCP projection."
