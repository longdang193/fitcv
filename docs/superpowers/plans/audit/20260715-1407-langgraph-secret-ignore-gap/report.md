# Audit Report With Evidence

## Metadata

- Audit ID: `20260715-1407-langgraph-secret-ignore-gap`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-07-15T14:07:02.8013303+02:00`
- Updated At: `2026-07-15T14:07:02.8013303+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-15-12-18-fitcv-runtime-env-ssot-cleanup-plan.md`

## Scope

- Environment: `Windows + PowerShell; JOB-PROJECT and fitcv-langgraph workspaces`
- Commit/Branch: `30c593206a766dfa8e0507edb2133b1e5bd69635 on main`
- Affected Surface: `C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph\.gitignore`

## Findings

### Finding `F1`: credential-shaped local JSON was not ignored in LangGraph repo

- Classification: `security`
- Impact: accidental staging or commit could expose local credential material.
- Expected Behavior: credential-shaped local file stays untracked and ignored in both FitCV workspaces.
- Actual Behavior: JOB-PROJECT ignored exact filename, while fitcv-langgraph reported it as untracked.

## Evidence

- Logs/Text: `evidence/results/containment.txt`
- Reproduction: `repro/repro_steps.md`
- Capture timestamp, command output, and checksums are recorded in `manifest.yaml`.

## Reproduction

- Preconditions:
  - local file exists at fitcv-langgraph repo root
  - do not open or print file content
- Steps:
  1. Run filename-scoped `git status`.
  2. Run filename-scoped `git check-ignore`.
- Commands:

```powershell
git -C "C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph" status --short -- "fitcv-491123-51c030d71e07.json"
git -C "C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph" check-ignore -v -- "fitcv-491123-51c030d71e07.json"
```

- Determinism notes: filename-only Git metadata check; no secret content access.

## Root Cause And Boundary

- Failure boundary: `fitcv-langgraph local secret containment contract`
- Root cause summary: JOB-PROJECT had exact ignore rule, fitcv-langgraph did not; cross-repo security vocabulary/containment drift.

## Fix And Verification

- Fix summary: add same exact filename ignore rule to fitcv-langgraph `.gitignore`; do not read or delete local file.
- Verification commands:

```powershell
git -C "C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph" check-ignore -v -- "fitcv-491123-51c030d71e07.json"
git -C "C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph" status --short -- "fitcv-491123-51c030d71e07.json" ".gitignore"
```

- Verification evidence links:
  - `evidence/results/containment.txt`

## Risk And Disposition

- Residual risk: local file still exists by user choice; ignore rule prevents normal Git staging but does not protect against explicit forced add.
- Disposition decision: `resolved`
- Follow-ups: rotate/delete credential outside this task if file is obsolete; never stage with `git add -f`.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
