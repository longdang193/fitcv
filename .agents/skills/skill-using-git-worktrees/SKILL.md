---
name: skill-using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace
  or before executing implementation plans - creates isolated git worktrees with smart
  directory selection and safety verification
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads:
- docs/operating_system/governance/repo-governance.md
tags:
- skill
- skill-using-git-worktrees
required_outputs: []
distribution_tier: starter_kit
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the skill-using-git-worktrees skill to set up an isolated workspace."

## Directory Selection Process

Follow this priority order:

### 1. Check Existing Directories

```bash
# Check in priority order
ls -d .worktrees 2>/dev/null     # Preferred (hidden)
ls -d worktrees 2>/dev/null      # Alternative
```

**If found:** Use that directory. If both exist, `.worktrees` wins.

### 2. Check CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**If preference specified:** Use it without asking.

### 3. Ask User

If no directory exists and no CLAUDE.md preference:

```
No worktree directory found. Where should I create worktrees?

1. .worktrees/ (project-local, hidden)
2. ~/.config/superpowers/worktrees/<project-name>/ (global location)

Which would you prefer?
```

## Safety Verification

### For Project-Local Directories (.worktrees or worktrees)

**MUST verify directory is ignored before creating worktree:**

```bash
# Check if directory is ignored (respects local, global, and system gitignore)
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:**

Per Jesse's rule "Fix broken things immediately":
1. Add appropriate line to .gitignore
2. Commit the change
3. Proceed with worktree creation

**Why critical:** Prevents accidentally committing worktree contents to repository.

### For Global Directory (~/.config/superpowers/worktrees)

No .gitignore verification needed - outside project entirely.

## Branch Freshness Preflight (Required Before `git worktree add`)

Run these checks on the base branch before creating or reusing any worktree:

```bash
# 1) Must be clean
git status --short

# 2) Must be freshly compared with remote
git fetch origin

# 3) Ahead/behind gate
git rev-list --left-right --count origin/main...main

# 4) Record exact base for traceability
git rev-parse --short main
```

Decision gates:

- If `git status --short` is non-empty: stop and ask user to commit/stash/discard.
- If ahead count is greater than `0`: ask user whether to push now (recommended) or continue from local-only commits.
- If behind count is greater than `0`: ask user whether to pull/rebase first or continue knowingly.
- Always capture and report base branch SHA before `git worktree add`.

## Creation Steps

### 1. Detect Project Name

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Create Worktree

```bash
# Determine full path
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.config/superpowers/worktrees/*)
    path="~/.config/superpowers/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# Create worktree with new branch
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Run Project Setup

Auto-detect and run appropriate setup:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

### 4. Verify Clean Baseline

Run tests to ensure worktree starts clean:

```bash
# Examples - use project-appropriate command
npm test
cargo test
pytest
go test ./...
```

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

### 5. Report Location

```
Worktree ready at <full-path>
Base branch: <branch-name>
Base SHA: <short-sha>
Ahead/behind vs origin/main: <ahead>/<behind>
Decision record: <pushed | local-only-approved | no-divergence>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| Branch dirty before preflight | Stop and ask commit/stash/discard |
| Ahead of origin/main | Ask push now (recommended) or local-only continue |
| Behind origin/main | Ask pull/rebase first or continue knowingly |
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md → Ask user |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |
| No package.json/Cargo.toml | Skip dependency install |

## Common Mistakes

### Skipping freshness preflight

- **Problem:** Worktree created from stale or unpublished base, causing hidden drift
- **Fix:** Always run status/fetch/ahead-behind/base-SHA sequence before `git worktree add`

### Skipping ignore verification

- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always use `git check-ignore` before creating project-local worktree

### Assuming directory location

- **Problem:** Creates inconsistency, violates project conventions
- **Fix:** Follow priority: existing > CLAUDE.md > ask

### Proceeding with failing tests

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

### Hardcoding setup commands

- **Problem:** Breaks on projects using different tools
- **Fix:** Auto-detect from project files (package.json, etc.)

## Example Workflow

```
You: I'm using the skill-using-git-worktrees skill to set up an isolated workspace.

[Run git status --short - clean]
[Run git fetch origin]
[Run git rev-list --left-right --count origin/main...main - 0 0]
[Run git rev-parse --short main - 4293f96]
[Check .worktrees/ - exists]
[Verify ignored - git check-ignore confirms .worktrees/ is ignored]
[Create worktree: git worktree add .worktrees/auth -b feature/auth]
[Run npm install]
[Run npm test - 47 passing]

Worktree ready at /Users/jesse/myproject/.worktrees/auth
Base branch: main
Base SHA: 4293f96
Ahead/behind vs origin/main: 0/0
Decision record: no-divergence
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

## Red Flags

**Never:**
- Create worktree without freshness preflight (status/fetch/divergence/base-SHA)
- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
- Proceed with failing tests without asking
- Assume directory location when ambiguous
- Skip CLAUDE.md check

**Always:**
- Run branch freshness preflight before `git worktree add`
- Follow directory priority: existing > CLAUDE.md > ask
- Verify directory is ignored for project-local
- Auto-detect and run project setup
- Verify clean test baseline
- Report base SHA and divergence decision record

## Integration

**Called by:**
- **skill-brainstorming** (Phase 4) - REQUIRED when design is approved and implementation follows
- **skill-subagent-driven-development** - REQUIRED before executing any tasks
- **skill-executing-plans** - REQUIRED before executing any tasks
- Any skill needing isolated workspace

**Pairs with:**
- **skill-finishing-a-development-branch** - REQUIRED for cleanup after work complete
