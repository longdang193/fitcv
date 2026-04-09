[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    (git rev-parse --show-toplevel).Trim()
}

function Get-ExpectedContent {
    param(
        [string]$SourcePath,
        [string]$CommentPrefix = "#"
    )

    $sourceContent = Get-Content -Raw -LiteralPath $SourcePath
    $header = @(
        "$CommentPrefix GENERATED FILE - do not edit directly."
        "$CommentPrefix Source: ``$SourcePath``"
        ""
    ) -join [Environment]::NewLine

    return $header + $sourceContent
}

function Normalize-Content {
    param([string]$Content)

    return ($Content -replace "`r`n", "`n").TrimEnd("`r", "`n")
}

$repoRoot = Get-RepoRoot

$mappings = @(
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/root-AGENTS.template.md'
        Destination = Join-Path $repoRoot 'AGENTS.md'
        Prefix = '#'
    }
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/docs-AGENTS.template.md'
        Destination = Join-Path $repoRoot 'docs/AGENTS.md'
        Prefix = '#'
    }
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/src-fitcv-AGENTS.template.md'
        Destination = Join-Path $repoRoot 'src/fitcv/AGENTS.md'
        Prefix = '#'
    }
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/src-fitcv_cp-AGENTS.template.md'
        Destination = Join-Path $repoRoot 'src/fitcv_cp/AGENTS.md'
        Prefix = '#'
    }
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/rules/command-execution.rules'
        Destination = Join-Path $repoRoot 'codex/rules/command-execution.rules'
        Prefix = '#'
    }
    @{
        Source = Join-Path $repoRoot 'agent-core/adapters/codex/rules/publication-boundary.rules'
        Destination = Join-Path $repoRoot 'codex/rules/publication-boundary.rules'
        Prefix = '#'
    }
)

$driftFound = $false
foreach ($mapping in $mappings) {
    if (-not (Test-Path -LiteralPath $mapping.Destination)) {
        Write-Error "Missing generated adapter: $($mapping.Destination)"
        $driftFound = $true
        continue
    }

    $expected = Get-ExpectedContent -SourcePath $mapping.Source -CommentPrefix $mapping.Prefix
    $actual = Get-Content -Raw -LiteralPath $mapping.Destination
    if ((Normalize-Content -Content $expected) -ne (Normalize-Content -Content $actual)) {
        Write-Error "Generated adapter drift detected: $($mapping.Destination)"
        $driftFound = $true
    }
}

if ($driftFound) {
    throw "Agent adapter verification failed."
}

Write-Host "Agent adapters are up to date."
