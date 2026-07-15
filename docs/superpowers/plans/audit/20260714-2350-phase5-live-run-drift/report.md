# Audit Report With Evidence

## Metadata

- Audit ID: `20260714-2350-phase5-live-run-drift`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-14T23:46:05+02:00`
- Updated At: `2026-07-15T00:43:13+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-14-20-54-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-plan.md`

## Scope

- Environment: `Windows, PowerShell, Python 3.13, inline TestClient, isolated SQLite`
- Branch: `codex/fitcv-llm-runtime-spine-phase1`
- Input: `data/sample_data_engineer_jobs.json` (13 jobs)
- Initial run: `5773ef48-9ef6-40c9-960c-ef52e138110e`
- Full post-fix run: `b26e96bd-f8fb-4b12-9c94-fd5eb3e9976d`
- CV-heartbeat verification run: `6c0977d5-623d-4cfb-984f-99d9e0c78f25`
- Affected surface: CV-generation trace symmetry, reuse diagnostics, stage liveness events, mutation-safe verification

## Findings

### Finding `F1`: direct adapter lost CV-generation trace records

- Classification: `contract-invariant-drift`
- Root cause: `_generate_fresh_from_analysis` created stage trace only when LangGraph-live provenance was available.
- Fix: stage-owned trace now wraps direct and LangGraph adapter calls through one canonical attempt skeleton.
- Proof: both post-fix runs report `records_total=3`, `present_records=3`, `trace_status=completed`; canonical and historical alias exports are semantically equal.

### Finding `F2`: fresh isolated run emitted misleading reuse anomaly

- Classification: `observability-drift`
- Root cause: reuse guard treated current processed-row total as prior overlap even when `reused=0`.
- Fix: anomaly evaluation skips stages with zero reused rows; low nonzero reuse remains warning-eligible.
- Proof: isolated full run and forced-fresh CV run both emit zero `reuse_anomaly` events.

### Finding `F3`: verification run mutated tracked synonym SSOT

- Classification: `configured-side-effect`
- Root cause: live verification inherited mutation-enabled synonym promotion settings.
- Fix: live-run execution workflow now requires mutation-safe per-run overrides unless SSOT mutation is scenario scope.
- Proof: both post-fix runs kept `config/taxonomy/skill_synonyms.yaml` SHA-256 unchanged.

### Finding `F4`: long provider work lacked periodic stage events

- Classification: `observability-drift`
- Root cause: enrichment heartbeat callback was disabled by an undocumented env switch, while concurrent CV-generation waits blocked on `as_completed` without timeout events.
- Fix: reporter callback now activates enrichment heartbeat directly; concurrent CV generation uses timed `wait(..., FIRST_COMPLETED)` and emits `cv_generation_heartbeat` every 15 seconds while futures remain pending.
- Proof: full isolated run emitted 71 enrichment heartbeats with `FITCV_ENRICH_HEARTBEAT_EVENTS` unset; reuse-assisted run emitted 7 CV-generation heartbeats before results.

## Evidence

- `evidence/results/postfix-full-live-run-report.json`
- `evidence/results/postfix-full-events.json`
- `evidence/results/postfix-cv-heartbeat-live-run-report.json`
- `evidence/results/postfix-cv-heartbeat-events.json`
- `evidence/results/postfix-cv-generation-trace.json`
- `evidence/results/postfix-cv-debug-summary.json`
- `evidence/results/postfix-focused-regression.log`
- Original failure evidence remains in this bundle for before/after comparison.

## Reproduction

- Original reproduction: `repro/repro_steps.md`.
- Post-fix full run used isolated SQLite, inline execution, same 13-job input, and mutation-safe synonym overrides.
- Post-fix heartbeat run reused prior stage snapshots, disabled only `reuse.cv_generation.enabled`, and forced three fresh provider calls.
- Expected: periodic stage liveness, complete stage-neutral trace records, no false fresh-run reuse warning, no tracked taxonomy mutation, endpoint/mirror semantic parity.
- Actual after fix: all expected checks passed.

## Root Cause And Boundary

- Business semantics were not changed.
- LangGraph remains runtime adapter/orchestrator only.
- Trace ownership, status meaning, validation, repair, and evidence projection remain repo-native.
- Heartbeats expose operational liveness only; they do not create extra LLM calls or alter outputs.

## Fix And Verification

- Regression tests cover direct trace parity, zero-reuse suppression, low-nonzero warning retention, enrichment heartbeat without env enablement, CV-generation heartbeat, deterministic order, and resume parity.
- Affected pipeline suites pass.
- Phase 5 combined regression passes.
- Full isolated live run succeeded with complete artifacts and 71 enrichment heartbeats.
- Reuse-assisted live run succeeded with 7 CV-generation heartbeats and 3/3 canonical trace records.
- Endpoint JSON and filesystem mirrors are semantically equal for export, debug, settings, CV-analysis trace, and CV-generation trace.
- Audit validator passes after manifest refresh.

## Risk And Disposition

- Residual risk: provider latency remains external and variable, but both single-item and concurrent batches now share one bounded heartbeat executor path.
- Disposition decision: `resolved`
- Follow-up: none required for current stage-event contract.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] fix applied
- [x] verification evidence confirms resolution
- [x] final status recorded
