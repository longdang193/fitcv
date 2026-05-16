## Metadata

- Audit ID: `20260516-2200-live-run-candidate-yaml-422`
- Status: `resolved`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-05-16T22:00:00+02:00`
- Updated At: `2026-05-16T22:12:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-16-21-07-input-data-contract-symmetry-option-c-plan.md`

## Scope

- Environment: `Windows, localhost:8000 control-plane`
- Commit/Branch: `27ffbe6` + `codex/input-data-contract-symmetry-option-c`
- Affected Surface: `src/fitcv_cp/app.py`, candidate upload/paste trigger path

## Findings

### Finding `F1`: YAML candidate payload rejected in live trigger

- Classification: `environment`
- Impact: `live trigger path cannot accept YAML candidate payload in upload/paste modes`
- Expected Behavior: `YAML candidate payload accepted equivalently to JSON for upload/paste modes`
- Actual Behavior: `POST /admin/upload-trigger` with YAML candidate payload returns 422 `Invalid JSON in candidate profile`.

## Evidence

- Result JSON: `evidence/results/paste_yaml_422.json`
- Result JSON: `evidence/results/baseline_run_summary.json`

## Reproduction

- Preconditions:
  - control-plane reachable at `http://localhost:8000`
- Steps:
  1. Trigger baseline `/runs` API run.
  2. Trigger `/admin/upload-trigger` with `candidate_profile_mode=paste` and YAML text.
- Commands:

```powershell
# see repro/repro_steps.md
```

- Determinism notes: `Same YAML file (`data/candidate_profile.yaml`) reproduces 422 on paste path.`

## Root Cause And Boundary

- Failure boundary: `control-plane live process candidate parse contract in upload/paste trigger path`
- Root cause summary: `Live process behavior still enforces JSON-only parse on candidate upload/paste path, inconsistent with intended Option C contract.`

## Fix And Verification

- Fix summary: `Control-plane restarted/redeployed from current worktree branch; YAML upload and YAML paste trigger probes rerun successfully (run creation accepted, candidate loaded).`
- Verification commands:

```powershell
# rerun baseline and YAML-trigger probes after deploy/restart
```

- Verification evidence links:
  - `evidence/results/paste_yaml_422.json`

## Risk And Disposition

- Residual risk: `low; trigger acceptance for YAML candidate input now validated, but runs still depend on normal HITL review flow.`
- Disposition decision: `resolved`
- Follow-ups: `restart/deploy service from updated branch and rerun workflow-live-run-execution + verification`

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

