# FitCV Local LLM Settings Discoverability Audit

## Metadata

- Audit ID: `20260717-1601-fitcv-local-llm-settings-discoverability`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-17T16:01:30+02:00`
- Updated At: `2026-07-17T16:01:30+02:00`
- Related Thread/Plan: `none`

## Scope

- Environment: Windows 10, Python 3.13.5, PyInstaller 6.21.0, Inno Setup 6.7.3
- Commit/Branch: `d7ea38fd` / `codex/phase-6-inverse-optimization`
- Affected Surface: FitCV Local navigation and completed onboarding presentation

## Findings

### Finding F1: Completed users cannot discover LLM and API settings

- Classification: `spec-mismatch`
- Impact: users can configure provider credentials during onboarding but cannot find a post-onboarding path to edit provider, API root, models, retry, or prompt guidance.
- Expected Behavior: completed users have a visible settings entry that reuses the canonical local controller editor.
- Actual Behavior: `/local/onboarding` remains functional, but navigation exposes only pipeline Settings, Data & Backup, and System.

## Evidence

- Reproduction and verification record: `evidence/results/verification.txt`
- Deterministic steps: `repro/repro_steps.md`

## Reproduction

- Preconditions and commands: `repro/repro_steps.md`

## Root Cause And Boundary

- Failure boundary: `src/fitcv_cp/templates/base.html` local navigation and `src/fitcv_cp/templates/local_onboarding.html` completed-state labels.
- Root cause summary: provider editing already used the canonical controller overlay and Windows credential store, but onboarding was treated as a one-time setup page and no post-setup navigation pointed back to it.

## Fix And Verification

- Fix summary: add one local-only **LLM & API** navigation link to the existing controller form; present completed onboarding as **FitCV Local Settings** with **Back to Runs** instead of **Finish setup**.
- Verification commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_local_routes.py -q
.\scripts\build_fitcv_local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
```

- Verification evidence: `evidence/results/verification.txt`

## Risk And Disposition

- Residual risk: none; persistence, credential storage, routes, and validation remain unchanged.
- Disposition decision: `resolved`
- Follow-ups: keep completed-user navigation regression and user-facing usage documentation.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
