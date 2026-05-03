[CmdletBinding()]
param(
    [ValidateSet('exploration', 'debugging', 'high-risk')]
    [string]$TaskTier = 'exploration',

    [string]$MetaPath = '.gitnexus/meta.json',

    [string]$HeadCommit,

    [switch]$RequireFresh,

    [switch]$Json
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    (git rev-parse --show-toplevel).Trim()
}

function Get-ShortCommit {
    param([string]$Commit)

    if ([string]::IsNullOrWhiteSpace($Commit)) {
        return $null
    }

    if ($Commit.Length -le 12) {
        return $Commit
    }

    return $Commit.Substring(0, 12)
}

function Get-Recommendation {
    param(
        [string]$Status,
        [string]$TaskTier
    )

    switch ($Status) {
        'fresh' {
            switch ($TaskTier) {
                'exploration' {
                    return @{
                        recommendedAction = 'use-normal'
                        recommendation = 'GitNexus is fresh; use it normally for exploration and architecture lookup.'
                    }
                }
                'debugging' {
                    return @{
                        recommendedAction = 'use-normal'
                        recommendation = 'GitNexus is fresh; use it normally for debugging and execution tracing.'
                    }
                }
                'high-risk' {
                    return @{
                        recommendedAction = 'use-high-trust'
                        recommendation = 'GitNexus is fresh; it is acceptable as a high-trust aid for impact analysis, refactoring, and pre-commit scope checks.'
                    }
                }
            }
        }
        'stale' {
            switch ($TaskTier) {
                'exploration' {
                    return @{
                        recommendedAction = 'advisory-only'
                        recommendation = 'GitNexus is stale; it is still acceptable as an advisory lookup layer for exploration.'
                    }
                }
                'debugging' {
                    return @{
                        recommendedAction = 'advisory-only'
                        recommendation = 'GitNexus is stale; use it only as advisory for debugging and label conclusions accordingly.'
                    }
                }
                'high-risk' {
                    return @{
                        recommendedAction = 'refresh-expected'
                        recommendation = 'GitNexus is stale; refresh before high-trust impact or refactor use. If refresh fails, continue source-first and treat GitNexus as advisory only.'
                    }
                }
            }
        }
        default {
            return @{
                recommendedAction = 'source-first'
                recommendation = 'GitNexus is unavailable; continue source-first with code, tests, and active docs, and refresh later only if useful.'
            }
        }
    }
}

$repoRoot = Get-RepoRoot
$resolvedMetaPath = if ([System.IO.Path]::IsPathRooted($MetaPath)) {
    $MetaPath
}
else {
    Join-Path $repoRoot $MetaPath
}

if (-not $HeadCommit) {
    $HeadCommit = (git rev-parse HEAD).Trim()
}

$status = 'unavailable'
$indexedCommit = $null
$indexedAt = $null
$details = 'GitNexus meta file not found.'

if (Test-Path -LiteralPath $resolvedMetaPath) {
    try {
        $meta = Get-Content -Raw -LiteralPath $resolvedMetaPath | ConvertFrom-Json
        $indexedCommit = [string]$meta.lastCommit
        $indexedAt = [string]$meta.indexedAt

        if (-not [string]::IsNullOrWhiteSpace($indexedCommit)) {
            if ($indexedCommit -eq $HeadCommit) {
                $status = 'fresh'
                $details = 'Indexed commit matches HEAD.'
            }
            else {
                $status = 'stale'
                $details = 'Indexed commit does not match HEAD.'
            }
        }
        else {
            $details = 'GitNexus meta file is present but missing lastCommit.'
        }
    }
    catch {
        $details = "GitNexus meta file could not be parsed: $($_.Exception.Message)"
    }
}

$recommendation = Get-Recommendation -Status $status -TaskTier $TaskTier
$requireFreshSatisfied = (-not $RequireFresh) -or ($status -eq 'fresh')

$result = [ordered]@{
    status = $status
    taskTier = $TaskTier
    headCommit = $HeadCommit
    headShort = Get-ShortCommit -Commit $HeadCommit
    indexedCommit = $indexedCommit
    indexedShort = Get-ShortCommit -Commit $indexedCommit
    indexedAt = $indexedAt
    metaPath = $resolvedMetaPath
    requireFresh = [bool]$RequireFresh
    requireFreshSatisfied = $requireFreshSatisfied
    recommendedAction = $recommendation.recommendedAction
    recommendation = $recommendation.recommendation
    details = $details
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
}
else {
    Write-Host "GitNexus status: $($result.status)"
    Write-Host "Task tier: $($result.taskTier)"
    Write-Host "HEAD: $($result.headShort)"
    if ($result.indexedShort) {
        Write-Host "Indexed commit: $($result.indexedShort)"
    }
    if ($result.indexedAt) {
        Write-Host "Indexed at: $($result.indexedAt)"
    }
    Write-Host "Recommended action: $($result.recommendedAction)"
    Write-Host "Recommendation: $($result.recommendation)"
    Write-Host "Details: $($result.details)"
}

if (-not $requireFreshSatisfied) {
    exit 2
}
