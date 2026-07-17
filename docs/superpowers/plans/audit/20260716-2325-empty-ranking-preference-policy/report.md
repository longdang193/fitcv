# Audit Report With Evidence

## Metadata

- Audit ID: `20260716-2325-empty-ranking-preference-policy`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-07-16T23:25:00+02:00`
- Updated At: `2026-07-16T23:58:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-16-22-40-fitcv-local-distribution-and-onboarding-plan.md`

## Scope

- Environment: `Windows 11, PowerShell, Python 3.13.5, uv 0.10.8, SQLite, source inline runtime`
- Commit/Branch: `d210f5486988f702646950b1093fe26d01eb5f36 on codex/phase-6-inverse-optimization`
- Affected Surface: `full pipeline ranking stage, preference-policy resolution, worker/local inline execution`

## Findings

### Finding `F1`: valid zero-ranking run crashes

- Classification: `regression`
- Impact: a run where all jobs are filtered or no ranking features remain fails instead of completing with zero ranked jobs.
- Expected Behavior: pipeline records empty ranking and completes normally.
- Actual Behavior: `resolve_run_preference_policy()` raises `ValueError: ranking rows are required to resolve preference policy`.

## Evidence

- Result JSON: `evidence/results/full-pipeline-failure.json`
- Zero-ranking post-fix JSON: `evidence/results/full-pipeline-postfix.json`
- Late-stage live JSON: `evidence/results/full-pipeline-late-stage.json`
- SQLite reconciliation: `evidence/results/late-stage-db.json`
- Bounded policy scenario: `evidence/results/hard-gate.json`
- Live provider check: `evidence/results/provider-live.json`
- Packaged smoke: `evidence/results/package-smoke.txt`
- Focused regressions: `evidence/results/focused-tests.txt`
- Repo contracts: `evidence/results/repo-contracts-fast.txt`
- Package hashes: `evidence/results/package-summary.json`
- SSOT audit: `evidence/results/ssot-audit-summary.json`
- Checksums: `manifest.yaml`

## Reproduction

- Preconditions and commands: `repro/repro_steps.md`.
- Determinism notes: fixed first row from `data/sample_jobs.json`, isolated SQLite path, global synonym promotion disabled.

## Root Cause And Boundary

- Failure boundary: ranking stage calls preference-policy resolution with empty `ranking_inputs`.
- Root cause summary: `resolve_run_preference_policy()` treated empty ranking as invalid input and raised before `rank_jobs()` could return an empty terminal result. All-job rejection is valid pipeline behavior, so preference policy must degrade to typed zero residual rather than abort the run.

## Fix And Verification

- Fix summary: empty ranking now produces `zero_residual_invalid` with diagnostic `missing_ranking_rows`; provider/task contract literals now use shared SSOT constants.
- Verification evidence links: `evidence/results/full-pipeline-postfix.json`, `evidence/results/full-pipeline-late-stage.json`, `evidence/results/late-stage-db.json`, `evidence/results/focused-tests.txt`, `evidence/results/repo-contracts-fast.txt`, `evidence/results/package-smoke.txt`.

## Risk And Disposition

- Residual risk: clean Windows VM and code-signing release gates remain outside this runtime verification.
- Disposition decision: `resolved`.
- Follow-ups: retain zero-ranking regression and shared-constant SSOT regression.

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
