# Audit Report With Evidence

## Metadata

- Audit ID: `20260712-2358-review-synonym-artifact-truth-split`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-07-12T23:58:00+00:00`
- Updated At: `2026-07-12T19:22:31.461188+00:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-12-20-40-fitcv-review-synonym-artifact-ssot-patch-plan.md`

## Scope

- Environment: `Windows + PowerShell + local sqlite control-plane + inline/live artifact inspection`
- Commit/Branch: `d3f927f7c902781f07bcc4ca18432439e66d4dc7` on `main`
- Affected Surface: `src/fitcv_cp/app.py`, `src/fitcv_cp/run_artifact_mirror.py`, `src/fitcv_cp/worker_job.py`

## Findings

### Finding `F1`: mirror rebuilds `export.json` with partial row shape

- Classification: `data-quality`
- Impact: filesystem mirror hides HITL-enriched export truth even when live endpoint exposes it.
- Expected Behavior: `artifacts/live_run_<run_id>/export.json` should match live run export contract for same run.
- Actual Behavior: mirror export rows for run `92b4c45d-cd2a-4e74-a18a-bbb87b5cd413` dropped derived fields present in live endpoint payload, including `final_status`, `fit_label`, and `reason`.

### Finding `F2`: mirror omits deterministic review/synonym payloads returned by live endpoints

- Classification: `data-quality`
- Impact: filesystem mirror is incomplete for review/debug workflows and splits truth by access path.
- Expected Behavior: deterministic run-scoped review/synonym artifacts available via live endpoints should also exist in new-run mirror.
- Actual Behavior: live endpoint payloads existed for `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json`, but mirror folder lacked all three files.

## Evidence

- Result JSON: `evidence/results/live-export.json`
- Result JSON: `evidence/results/mirror-export.json`
- Result JSON: `evidence/results/hitl-review-audit.json`
- Result JSON: `evidence/results/synonym-proposals-trace.json`
- Result JSON: `evidence/results/synonym-suppression-diff.json`
- Logs/Text: `evidence/results/mirror-listing.txt`
- Logs/Text: `evidence/results/summary.txt`
- Logs/Text: `evidence/results/verification.txt`
- Result JSON: `evidence/results/inline-settled-comparison.json`

## Reproduction

- Preconditions:
  - repo workspace contains run `92b4c45d-cd2a-4e74-a18a-bbb87b5cd413` evidence
  - live endpoint snapshots exist under `runtime/`
- Steps:
  1. Inspect live endpoint snapshots under `runtime/`.
  2. Inspect mirror folder `artifacts/live_run_92b4c45d-cd2a-4e74-a18a-bbb87b5cd413/`.
  3. Compare available filenames and first export-row keys.
- Commands:

```powershell
Get-Content runtime/live-export.json -Raw | ConvertFrom-Json
Get-Content artifacts/live_run_92b4c45d-cd2a-4e74-a18a-bbb87b5cd413/export.json -Raw | ConvertFrom-Json
Get-ChildItem artifacts/live_run_92b4c45d-cd2a-4e74-a18a-bbb87b5cd413
```

- Determinism notes: same captured run ID and saved endpoint payload snapshots used for all comparisons.

## Root Cause And Boundary

- Failure boundary: `deterministic run-scoped artifact serialization at live endpoint versus filesystem mirror boundary`
- Root cause summary: mirror path owned a second partial serializer in `src/fitcv_cp/run_artifact_mirror.py`, while live endpoint and bundle derived richer payloads from app-owned helpers.

## Fix And Verification

- Fix summary: route endpoint, bundle, and mirror through one deterministic artifact payload owner, keep `synonym-proposals.json` raw everywhere under same filename, and stabilize suppression-diff timestamp for parity.
- Verification commands:

```powershell
py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py -k "artifact or mirror or export or hitl or synonym" -q
py -3 scripts/audit_check.py docs/superpowers/plans/audit/20260712-2358-review-synonym-artifact-truth-split
```

- Verification evidence links:
  - `evidence/results/summary.txt`
  - `evidence/results/verification.txt`
  - `evidence/results/inline-settled-comparison.json`

## Risk And Disposition

- Residual risk: local dev server on `localhost:8000` must be restarted to load patched source; current source proof is resolved.
- Disposition decision: `resolved`
- Follow-ups:
  - restart any long-lived local server process before manual browser checks
  - no backfill required for pre-patch artifacts

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
