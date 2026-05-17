# Audit Report

## Metadata

- Audit ID: `20260517-1416-live-run-invalid-api-key`
- Status: `resolved`
- Severity: `high`
- Owner: `codex`
- Created At: `2026-05-17T14:16:00+02:00`
- Updated At: `2026-05-17T14:33:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-17-15-45-ai-plane-symmetry-invariance-equivalence-migration-plan.md`

## Scope

- Environment: `docker compose (redis/web/worker), API http://localhost:8000`
- Commit/Branch: `main (working tree)`
- Affected Surface: `cv_generation -> fitcv_langgraph_live provider path`

## Findings

### Finding F1: Live provider rejects key during CV generation

- Classification: `environment`
- Impact: live runs produce `cvs_generated=0`; deliverable "no problems" not met.
- Expected Behavior: agentic live trace `trace_status=completed` with generation attempts accepted or review-required.
- Actual Behavior: terminal run status `succeeded` but trace `degraded`; each generation attempt fails with OpenAI `401 invalid_api_key`.
- Resolution Evidence: after runtime override update, run `f8549230-ac38-4035-8ce3-c1545d2f1ce5` reached `status=succeeded`, `cvs_generated=2`, and `/agentic-live-trace.json` returned `trace_status=completed` with no error codes.

## Evidence

- `artifacts/live_run_bc813187-3a87-463b-852f-1bd25870e876/agentic-live-trace.json`
- `artifacts/live_run_edb1ea11-3c16-4481-942a-edc48050fc30/agentic-live-trace.json`
- `artifacts/live_run_f7e10bff-84d8-47a3-8c27-2658f688f847/agentic-live-trace.json`
- `artifacts/live_run_f7e10bff-84d8-47a3-8c27-2658f688f847/run.json`
- `artifacts/live_run_f8549230-ac38-4035-8ce3-c1545d2f1ce5/agentic-live-trace.json`
- `artifacts/live_run_f8549230-ac38-4035-8ce3-c1545d2f1ce5/run.json`
- `repro/repro_steps.md`

## Reproduction

- Preconditions:
  - valid docker runtime for `web` and `worker`
  - current runtime key present in env
- Steps:
  1. trigger `/runs` with sample payload
  2. wait terminal status
  3. fetch `/admin/runs/<run_id>/agentic-live-trace.json`
- Commands: see `repro/repro_steps.md`
- Determinism notes: reproduced on three run IDs same day.

## Root Cause And Boundary

- Failure boundary: `cv_generation` stage, component `fitcv_langgraph_live`, contract `provider credential acceptance`.
- Root cause summary: runtime OpenAI key invalid/revoked for live endpoint; migration logic not failing in local verification suites.

## Fix And Verification

- Fix summary: enforce openai-compatible live routing env overrides in runtime (`FITCV_LANGGRAPH_PROVIDER=9router`, `FITCV_LANGGRAPH_OPENAI_BASE_URL=http://host.docker.internal:20128/v1`, `FITCV_LANGGRAPH_WIRE_API=responses`, `FITCV_LANGGRAPH_MODEL=cx/gpt-5.2`) and restart `web/worker`.
- Verification commands:
  - trigger one new run
  - verify `/admin/runs/<run_id>/agentic-live-trace.json` has `trace_status=completed` and non-zero accepted/review-required outcomes.
- Verification evidence links:
  - `artifacts/live_run_f8549230-ac38-4035-8ce3-c1545d2f1ce5/run.json`
  - `artifacts/live_run_f8549230-ac38-4035-8ce3-c1545d2f1ce5/agentic-live-trace.json`

## Risk And Disposition

- Residual risk: review-required policy outcomes can pause runs; operator review flow needed when acceptance policy blocks.
- Disposition decision: `resolved`
- Follow-ups: none for credential boundary; optional policy-threshold tuning if fewer review pauses desired.

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
