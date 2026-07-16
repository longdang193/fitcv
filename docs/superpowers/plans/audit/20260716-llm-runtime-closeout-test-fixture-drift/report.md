# Audit Report With Evidence

## Metadata

- Audit ID: `20260716-llm-runtime-closeout-test-fixture-drift`
- Status: `resolved`
- Severity: `low`
- Owner: `Codex`
- Created At: `2026-07-16T22:17:37.9818605+02:00`
- Updated At: `2026-07-16T22:17:37.9818605+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-16-21-16-fitcv-langgraph-removal-and-llm-runtime-ssot-closeout-plan.md`

## Scope

- Environment: `Windows, PowerShell, Python virtual environment, pytest`
- Commit/Branch: `0a38017a20047cc4c5a5533533f295cf0e9003e1 on codex/phase-6-inverse-optimization with uncommitted closeout changes`
- Affected Surface: `tests/test_pipeline_agentic_late_stage.py` fixtures only

## Findings

### Finding `F1`: late-stage pipeline fixtures lagged current shortlist and preference-policy contracts

- Classification: `spec-mismatch`
- Impact: five planned verification tests failed; production runtime behavior was not implicated.
- Expected Behavior: vector-search mocks return `{"production_rows": [...]}`, and shared test config includes minimum ranking/preference-policy ownership required by current pipeline.
- Actual Behavior: mocks returned a bare list, then the fixture lacked `decision_learning_policy.inverse_optimization` and `ranking_policy`.

## Evidence

- Verification sequence: `evidence/results/verification.txt`
- Reproduction steps: `repro/repro_steps.md`
- Checksums: `manifest.yaml`

## Reproduction

- Preconditions:
  - repository checkout at recorded branch and commit
  - project virtual environment available
- Steps and exact commands: `repro/repro_steps.md`
- Determinism notes: all five tests use fixed in-process fixtures and no live provider.

## Root Cause And Boundary

- Failure boundary: test fixture setup before shortlist/preference-policy execution.
- Root cause summary: unrelated pipeline contract evolution was not reflected in this focused late-stage test helper and five vector-search mocks.

## Fix And Verification

- Fix summary: wrap five vector-search mock rows under `production_rows` and add minimum current policy fields to shared `_minimal_config`.
- Verification commands: `repro/repro_steps.md`.
- Verification evidence links: `evidence/results/verification.txt`.

## Risk And Disposition

- Residual risk: none identified in production code; helper change affects fifteen tests and full focused suite passed.
- Disposition decision: `resolved`
- Follow-ups: keep shared pipeline fixtures aligned when shortlist or preference-policy input contracts change.

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