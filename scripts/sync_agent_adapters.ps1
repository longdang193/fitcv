[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    (git rev-parse --show-toplevel).Trim()
}

function Load-AdapterMappings {
    param([string]$RepoRoot)

    $configPath = Join-Path $RepoRoot 'repo_config/agent-adapter-mappings.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw "Missing adapter mapping config: $configPath"
    }

    $payload = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
    if (-not $payload) {
        throw "Adapter mapping config is empty: $configPath"
    }

    return @($payload)
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

    Set-Content -LiteralPath $DestinationPath -Value ($header + $sourceContent)
}

$repoRoot = Get-RepoRoot
$mappings = Load-AdapterMappings -RepoRoot $repoRoot

foreach ($mapping in $mappings) {
    if (-not $mapping.source -or -not $mapping.destination) {
        throw "Each adapter mapping must define source and destination."
    }

    $prefix = if ($mapping.prefix) { $mapping.prefix } else { '#' }
    $sourcePath = Join-Path $repoRoot $mapping.source
    $destinationPath = Join-Path $repoRoot $mapping.destination

    Write-GeneratedFile -RepoRoot $repoRoot -SourcePath $sourcePath -DestinationPath $destinationPath -CommentPrefix $prefix
}

Write-Host "Agent adapters synchronized."
