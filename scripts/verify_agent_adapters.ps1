# @meta
# repo: private

[CmdletBinding()]
param(
    [string]$ConfigPath = 'repo_config/agent-adapter-mappings.json'
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    (git rev-parse --show-toplevel).Trim()
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

$driftFound = $false
foreach ($mapping in $mappings) {
    $sourcePath = Join-Path $repoRoot $mapping.source
    $destinationPath = Join-Path $repoRoot $mapping.destination
    $prefix = if ($mapping.prefix) { [string]$mapping.prefix } else { '#' }

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
