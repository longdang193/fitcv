[CmdletBinding()]
param()

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

function Write-GeneratedFile {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string]$CommentPrefix = "#"
    )

    Ensure-ParentDirectory -Path $DestinationPath

    $sourceContent = Get-Content -Raw -LiteralPath $SourcePath
    $header = @(
        "$CommentPrefix GENERATED FILE - do not edit directly."
        "$CommentPrefix Source: ``$SourcePath``"
        ""
    ) -join [Environment]::NewLine

    Set-Content -LiteralPath $DestinationPath -Value ($header + $sourceContent)
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

foreach ($mapping in $mappings) {
    Write-GeneratedFile -SourcePath $mapping.Source -DestinationPath $mapping.Destination -CommentPrefix $mapping.Prefix
}

Write-Host "Agent adapters synchronized."
