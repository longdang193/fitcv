---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-local-packaging-datas-manifest-fix
targets:
  - packaging/windows/fitcv-local.spec
  - tests/test_fitcv_local_packaging.py
  - docs/superpowers/plans/2026-08-23-fitcv-local-packaging-datas-manifest-fix-plan.md
---

# FitCV Local Packaging Datas Manifest Fix

## Goal

Repair stale PyInstaller data-source ownership without changing FitCV runtime
or pipeline behavior, then create a fresh package baseline for Windows clean-VM
acceptance.

## Root Cause

`packaging/windows/fitcv-local.spec` declared the absent root `configs/`
directory. Current runtime configuration is owned by `config/`, so PyInstaller
failed before producing a bundle.

## Implementation Outcomes

- PyInstaller data manifest contains only existing canonical source paths.
- Regression test rejects future missing data-source paths.
- Fresh Technical Preview bundle, installer, and packaged smoke pass.

## Task Breakdown

### Task 1: Packaging manifest and closure proof

- Inspect canonical configuration ownership and preserve unrelated changes.
- Prove the missing-source regression before the manifest fix.
- Remove only the stale `configs/` data entry.
- Run focused tests, governance validators, real build, smoke, and independent
  validation.
- Commit and push one narrow checkpoint.

## Scope

- Remove the stale `ROOT / "configs"` data entry.
- Add a generic regression requiring every ROOT-relative PyInstaller data source
  to exist.
- Verify package build, installer creation, packaged smoke, and independent
  read-only validation.
- Do not reopen Scan + Run, source-mode P0, runtime, pipeline, or unrelated
  user changes.

## Coordination State

- Coordination owner: `single lead controller`
- Workspace: `C:\tmp\fitcv-packaged-preview-20260823`
- Branch: `codex/fitcv-local-packaging-fix`
- Base commit: `f4c8715d36bcf41fdcdb1b56295cf2e307108fd7`
- Active task: `none`
- Next action: packaged Windows clean-VM acceptance from new checkpoint
- Blockers: `none`

| Task | State | Required Proof |
| --- | --- | --- |
| Task 1 | `completed` | red regression, focused tests, repo validators, fresh PyInstaller/Inno build, packaged smoke, independent validator, narrow Git diff |

## Verification Evidence

Fresh closure evidence: packaging tests `5 passed`; repo contracts `10 passed`;
planning and template validators passed; PyInstaller 6.21.0 and Inno Setup
6.7.3 passed; bundle `48,569,251` bytes; build ID
`f4c8715d36bcf41fdcdb1b56295cf2e307108fd7`; installer
`FitCV-Local-0.1.0-Technical-Preview-Setup.exe` SHA-256
`c3d6a077396af6174ee5dac76ea214e0706b88bc29ed916bdac25332c47799c7`;
packaged smoke PASS; independent validator PASS.

## Verification

- `py -m pytest tests/test_fitcv_local_packaging.py -q`
- `py -m pytest tests/test_validate_repo_contracts.py -q`
- `py scripts/validate_planning_lifecycle.py`
- `py scripts/validate_template_required_sections.py`
- `git diff --check`
- `powershell -ExecutionPolicy Bypass -File scripts/build_fitcv_local.ps1`
- `scripts/smoke_fitcv_local.ps1`
- independent read-only validator returns `PASS`

## Completion Criteria

- `config/` remains canonical and no runtime asset is lost.
- Generic data-source regression passes.
- Fresh bundle and installer build successfully within existing limits.
- Packaged smoke passes.
- Independent validator returns `PASS`.
- Only declared packaging, test, and this plan change.
- Plan status changes to `completed` only after all proof is accepted.
