[CmdletBinding()]
param(
    [string]$ExportRoot = (Join-Path $env:TEMP "fitcv-public-export"),
    [string]$PublicRemote = "public",
    [string]$PublicBranch = "main",
    [string]$CommitMessage = "Publish curated public mirror",
    [switch]$Push
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $root = git rev-parse --show-toplevel
    if (-not $root) {
        throw "Unable to resolve repo root."
    }

    return $root.Trim()
}

function Ensure-CleanDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Ensure-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Copy-PublicPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $source = Join-Path $SourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        return
    }

    $destination = Join-Path $DestinationRoot $RelativePath
    Ensure-ParentDirectory -Path $destination
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

function Assert-ForbiddenPathAbsent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $path = Join-Path $DestinationRoot $RelativePath
    if (Test-Path -LiteralPath $path) {
        throw "Forbidden path present in public export: $RelativePath"
    }
}

function Assert-RequiredPathPresent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $path = Join-Path $DestinationRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required public path missing from export: $RelativePath"
    }
}

function Assert-NoPrivateReferences {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    $patterns = @(
        'AGENTS\.md',
        '\.agents/',
        '\.cursor/',
        'agent-core/',
        'codex/rules/',
        'docs/operating_system/',
        'docs/superpowers/',
        '/[A-Za-z]:/',
        '\([A-Za-z]:/',
        'file://'
    )

    $files = Get-ChildItem -LiteralPath $DestinationRoot -Recurse -File -Include *.md,*.yaml,*.yml,*.txt
    foreach ($file in $files) {
        $content = Get-Content -Raw -LiteralPath $file.FullName
        foreach ($pattern in $patterns) {
            if ($content -match $pattern) {
                throw "Private-only reference found in public export: $($file.FullName)"
            }
        }
    }
}

function Assert-NoLocalAbsoluteLinks {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    $patterns = @(
        '/[A-Za-z]:/',
        '\([A-Za-z]:/',
        'file://'
    )

    $files = Get-ChildItem -LiteralPath $DestinationRoot -Recurse -File -Include *.md,*.yaml,*.yml,*.txt
    foreach ($file in $files) {
        $content = Get-Content -Raw -LiteralPath $file.FullName
        foreach ($pattern in $patterns) {
            if ($content -match $pattern) {
                throw "Local absolute link found in public export: $($file.FullName)"
            }
        }
    }
}

function Remove-UnlistedGeneratedDocs {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [Parameter(Mandatory = $true)]
        [string[]]$AllowedGeneratedPaths
    )

    $generatedRoot = Join-Path $DestinationRoot 'docs/generated'
    if (-not (Test-Path -LiteralPath $generatedRoot)) {
        return
    }

    $allowed = @{}
    foreach ($path in $AllowedGeneratedPaths) {
        $allowed[$path.Replace('\', '/').ToLowerInvariant()] = $true
    }

    $generatedFiles = Get-ChildItem -LiteralPath $generatedRoot -Recurse -File
    foreach ($file in $generatedFiles) {
        $relative = [System.IO.Path]::GetRelativePath($DestinationRoot, $file.FullName).Replace('\', '/').ToLowerInvariant()
        if (-not $allowed.ContainsKey($relative)) {
            Remove-Item -LiteralPath $file.FullName -Force
        }
    }
}

function Remove-PrivateAdapterFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot
    )

    $agentFiles = Get-ChildItem -LiteralPath $DestinationRoot -Recurse -File -Filter 'AGENTS.md' -ErrorAction SilentlyContinue
    foreach ($file in $agentFiles) {
        Remove-Item -LiteralPath $file.FullName -Force
    }
}

function Remove-PrivateReferenceLines {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $patterns = @(
        'AGENTS\.md',
        'docs/superpowers/',
        'docs/operating_system/',
        'agent-core/',
        'codex/rules/',
        '\.agents/',
        '\.cursor/'
    )

    $targetRoot = Join-Path $DestinationRoot $RelativePath
    if (-not (Test-Path -LiteralPath $targetRoot)) {
        return
    }

    $files = Get-ChildItem -LiteralPath $targetRoot -Recurse -File -Include *.md,*.yaml,*.yml
    foreach ($file in $files) {
        $lines = Get-Content -LiteralPath $file.FullName
        $filtered = foreach ($line in $lines) {
            $skip = $false
            foreach ($pattern in $patterns) {
                if ($line -match $pattern) {
                    $skip = $true
                    break
                }
            }

            if (-not $skip) {
                $line
            }
        }

        Set-Content -LiteralPath $file.FullName -Value $filtered
    }
}

$repoRoot = Get-RepoRoot
$publicPaths = @(
    ".dockerignore",
    ".gitignore",
    "Dockerfile",
    "README.md",
    "assets",
    "config",
    "data",
    "docker-compose.yml",
    "docs/features",
    "docs/generated/features_index.yaml",
    "docs/generated/stages_index.yaml",
    "docs/generated/stage_overview.md",
    "docs/FitCV-pipeline.md",
    "docs/fitcv-control-plane-setup.md",
    "docs/stages",
    "pyproject.toml",
    "requirements.txt",
    "scripts/bootstrap_bigquery.py",
    "scripts/download_cvs.py",
    "src",
    "start_web.ps1",
    "start_worker.ps1",
    "stop_fitcv.ps1",
    "templates",
    "tests",
    "uv.lock"
)

$forbiddenPaths = @(
    "AGENTS.md",
    ".agents",
    ".cursor",
    "agent-core",
    "codex",
    "docs/operating_system",
    "docs/superpowers",
    "logs",
    "sample",
    ".worktrees"
)

$requiredPaths = @(
    "README.md",
    "docs/FitCV-pipeline.md",
    "docs/fitcv-control-plane-setup.md",
    "docs/features",
    "src"
)

$remoteUrl = $null
if ($Push) {
    $remoteUrl = git remote get-url $PublicRemote 2>$null
    if (-not $remoteUrl) {
        throw "Remote '$PublicRemote' is not configured."
    }
}

Ensure-CleanDirectory -Path $ExportRoot

if ($Push) {
    Remove-Item -LiteralPath $ExportRoot -Recurse -Force
    $remoteHeads = git ls-remote --heads $PublicRemote

    if ($remoteHeads) {
        git clone --branch $PublicBranch --single-branch $remoteUrl $ExportRoot | Out-Null
        Get-ChildItem -LiteralPath $ExportRoot -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
    } else {
        New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
        git -C $ExportRoot init -b $PublicBranch | Out-Null
        git -C $ExportRoot remote add origin $remoteUrl
    }
}

foreach ($relativePath in $publicPaths) {
    Copy-PublicPath -SourceRoot $repoRoot -DestinationRoot $ExportRoot -RelativePath $relativePath
}

Remove-UnlistedGeneratedDocs -DestinationRoot $ExportRoot -AllowedGeneratedPaths @(
    'docs/generated/features_index.yaml',
    'docs/generated/stages_index.yaml',
    'docs/generated/stage_overview.md'
)

Remove-PrivateAdapterFiles -DestinationRoot $ExportRoot

Remove-PrivateReferenceLines -DestinationRoot $ExportRoot -RelativePath 'docs/features'
Remove-PrivateReferenceLines -DestinationRoot $ExportRoot -RelativePath 'docs/stages'

foreach ($relativePath in $forbiddenPaths) {
    Assert-ForbiddenPathAbsent -DestinationRoot $ExportRoot -RelativePath $relativePath
}

foreach ($relativePath in $requiredPaths) {
    Assert-RequiredPathPresent -DestinationRoot $ExportRoot -RelativePath $relativePath
}

Assert-NoPrivateReferences -DestinationRoot $ExportRoot
Assert-NoLocalAbsoluteLinks -DestinationRoot $ExportRoot

Write-Host "Public export prepared at: $ExportRoot"

if ($Push) {
    git -C $ExportRoot add -A
    $status = git -C $ExportRoot status --short

    if (-not $status) {
        Write-Host "No public-repo changes to publish."
        exit 0
    }

    git -C $ExportRoot commit -m $CommitMessage | Out-Null
    git -C $ExportRoot push origin $PublicBranch
    Write-Host "Public repo updated on branch '$PublicBranch'."
}
