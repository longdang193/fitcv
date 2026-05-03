[CmdletBinding()]
param(
    [string]$ConfigPath = 'repo_config/agent-adapter-mappings.json'
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    (git rev-parse --show-toplevel).Trim()
}

function Ensure-ParentDirectory {
    param([string]$Path)

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Get-RepoRelativePath {
    param(
        [string]$RepoRoot,
        [string]$Path
    )

    return [System.IO.Path]::GetRelativePath($RepoRoot, $Path).Replace('\', '/')
}

function Write-GeneratedFile {
    param(
        [string]$RepoRoot,
        [string]$SourcePath,
        [string]$DestinationPath,
        [string]$CommentPrefix = "#"
    )

    Ensure-ParentDirectory -Path $DestinationPath

    $sourceContent = Get-Content -Raw -LiteralPath $SourcePath
    $relativeSourcePath = Get-RepoRelativePath -RepoRoot $RepoRoot -Path $SourcePath
    $header = @(
        "$CommentPrefix GENERATED FILE - do not edit directly."
        "$CommentPrefix Source: ``$relativeSourcePath``"
        ""
    ) -join [Environment]::NewLine

    Set-Content -LiteralPath $DestinationPath -Value ($header + $sourceContent) -NoNewline
}

function Get-AdapterMappings {
    param(
        [string]$RepoRoot,
        [string]$ConfigPath
    )

    $configFullPath = Join-Path $RepoRoot $ConfigPath
    if (-not (Test-Path -LiteralPath $configFullPath)) {
        throw "Adapter config not found: $configFullPath"
    }

    $mappings = Get-Content -Raw -LiteralPath $configFullPath | ConvertFrom-Json
    if (-not $mappings) {
        throw "Adapter config is empty: $configFullPath"
    }

    return @($mappings)
}

$repoRoot = Get-RepoRoot
$mappings = Get-AdapterMappings -RepoRoot $repoRoot -ConfigPath $ConfigPath

foreach ($mapping in $mappings) {
    $sourcePath = Join-Path $repoRoot $mapping.source
    $destinationPath = Join-Path $repoRoot $mapping.destination
    $prefix = if ($mapping.prefix) { [string]$mapping.prefix } else { '#' }
    Write-GeneratedFile -RepoRoot $repoRoot -SourcePath $sourcePath -DestinationPath $destinationPath -CommentPrefix $prefix
}

Write-Host "Agent adapters synchronized."
