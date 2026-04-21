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

function Get-RepoRelativePath {
    param(
        [string]$RepoRoot,
        [string]$Path
    )

    return [System.IO.Path]::GetRelativePath($RepoRoot, $Path).Replace('\', '/')
}

function Get-ExpectedContent {
    param(
        [string]$RepoRoot,
        [string]$SourcePath,
        [string]$CommentPrefix = "#"
    )

    $sourceContent = Get-Content -Raw -LiteralPath $SourcePath
    $relativeSourcePath = Get-RepoRelativePath -RepoRoot $RepoRoot -Path $SourcePath
    $header = @(
        "$CommentPrefix GENERATED FILE - do not edit directly."
        "$CommentPrefix Source: ``$relativeSourcePath``"
        ""
    ) -join [Environment]::NewLine

    return $header + $sourceContent
}

function Normalize-Content {
    param([string]$Content)

    return ($Content -replace "`r`n", "`n").TrimEnd("`r", "`n")
}

$repoRoot = Get-RepoRoot
$mappings = Load-AdapterMappings -RepoRoot $repoRoot

$driftFound = $false
foreach ($mapping in $mappings) {
    if (-not $mapping.source -or -not $mapping.destination) {
        Write-Error "Each adapter mapping must define source and destination."
        $driftFound = $true
        continue
    }

    $prefix = if ($mapping.prefix) { $mapping.prefix } else { '#' }
    $sourcePath = Join-Path $repoRoot $mapping.source
    $destinationPath = Join-Path $repoRoot $mapping.destination

    if (-not (Test-Path -LiteralPath $destinationPath)) {
        Write-Error "Missing generated adapter: $destinationPath"
        $driftFound = $true
        continue
    }

    $expected = Get-ExpectedContent -RepoRoot $repoRoot -SourcePath $sourcePath -CommentPrefix $prefix
    $actual = Get-Content -Raw -LiteralPath $destinationPath
    if ((Normalize-Content -Content $expected) -ne (Normalize-Content -Content $actual)) {
        Write-Error "Generated adapter drift detected: $destinationPath"
        $driftFound = $true
    }
}

if ($driftFound) {
    throw "Agent adapter verification failed."
}

Write-Host "Agent adapters are up to date."
