# Outcome-Fact Live-Run Contract Drift Audit

## Metadata

- Audit ID: `20260717-2332-outcome-fact-live-run-contract-drift`
- Status: `resolved`
- Severity: `medium`
- Owner: `FitCV maintainers`
- Created At: `2026-07-17`
- Updated At: `2026-07-17`
- Related Plan: `docs/superpowers/plans/2026-07-17-21-14-fitcv-outcome-fact-ssot-and-debug-traceability-plan.md`

## Scope

- Environment: Windows, source-mode local control plane, new SQLite database
- Commit/Branch: working tree on `codex/phase-6-inverse-optimization`
- Affected Surface: outcome-event persistence, run-detail UI, review-required terminal messaging
- Failing Evidence Root: `artifacts/live_run_sample_data_engineer_newdb_20260717-224857`
- Resolution Evidence Root: `artifacts/live_run_outcome_fix_20260717`
- Clock Note: Raw resolution artifacts contain future July 18, 2026 local timestamps because host process clock differed from governing task date. Audit date remains Friday, July 17, 2026; raw timestamps remain unchanged.

## Findings

### Finding F1: Required `Why?` inspection was absent

- Classification: `spec-mismatch`
- Impact: Users could not inspect bounded reason facts and exact evidence reference from normal run detail.
- Expected Behavior: Default job inspection shows outcome, stage, derived reason, `Why?`, and debug-bundle action.
- Actual Behavior: Run detail showed generic manual-review text and timeline messages, with no `Why?` control.

### Finding F2: Fingerprint leaked into default timeline

- Classification: `spec-mismatch`
- Impact: Technical detail remained visible in default UI and increased user-facing noise.
- Expected Behavior: Fingerprints stay behind explicit `Why?` inspection or debug bundle.
- Actual Behavior: Formatted CV-generation timeline messages included shortened evidence fingerprints.

### Finding F3: Outcome event payload exceeded minimal contract

- Classification: `spec-mismatch`
- Impact: Outcome chronology duplicated unrelated telemetry envelope state and violated six-key event symmetry.
- Expected Behavior: Payload contains only `job_key`, `stage`, `outcome`, `reason_code`, `outcome_fingerprint`, and `evidence_ref`.
- Actual Behavior: Every tested outcome event also contained four observability fields.

### Finding F4: Terminal event wording contradicted terminal run state

- Classification: `spec-mismatch`
- Impact: Operators saw `succeeded` and `Run paused` for the same terminal run.
- Expected Behavior: Held job outcomes remain pending review without implying the completed pipeline process is paused.
- Actual Behavior: Worker terminal review event used stale `Run paused` wording.

### Finding F5: Run-detail formatter reintroduced stale wording

- Classification: `projection-drift`
- Impact: First post-fix live run persisted the corrected `Review required:` event but rendered it as `Run paused` in the UI.
- Expected Behavior: Persistence and every user-facing projection preserve the same terminal meaning.
- Actual Behavior: `_timeline_stage_summary_message()` rebuilt the event message from payload using an independent stale label.

## Evidence

- Pre-fix:
  - `evidence/results/live-run-verification.json`
  - `evidence/results/contract-findings.txt`
- Post-fix:
  - `evidence/results/resolution-live-run-verification.json`
  - `evidence/results/resolution-checksums.txt`
  - `evidence/results/post-fix-verification.txt`
- Reproduction:
  - `repro/repro_steps.md`

## Reproduction

- Preconditions and original commands: `repro/repro_steps.md`
- Determinism: Fixed 13-row input and structural contract checks; provider output can alter outcome distribution but not required fact/event/UI shape.
- Resolution run:
  1. Start source control plane with a fresh SQLite database.
  2. Submit `data/sample_data_engineer_jobs.json` with both synonym-promotion toggles disabled.
  3. Wait for terminal state and download run, events, HTML, enriched fragment, review queue, export, and debug bundle.
  4. Validate facts, exact event keys, evidence references, bundle hashes, secret/prompt redaction, UI wording, database counts, and tracked SSOT hashes.
  5. Stop server and confirm listening port is released.

## Root Cause And Boundary

- F1: Canonical `job_outcome_surface()` data existed but was not projected into the enriched-job inspection UI.
- F2: Timeline formatting independently exposed `validation_evidence_fingerprint` instead of keeping it behind explicit technical drill-down.
- F3: Reporter observability enrichment appended common telemetry keys to every event, including the canonical minimal `job_outcome` reference event.
- F4: Worker terminal review event retained pre-terminal pause wording after run semantics changed to terminal success with held items.
- F5: Run-detail timeline formatter duplicated semantic wording instead of preserving the corrected terminal meaning.
- SSOT drift: Producer and reporter duplicated the `job_outcome` stage literal. UI reason/evidence rendering had a separate projection path.
- Compatibility boundary: Legacy pipeline-status filter values remain an explicit adapter namespace for historical rows. They are not canonical JobOutcomeFact truth and must not be collapsed into the five canonical outcomes.

## Fix And Verification

- Fix summary:
  1. Added canonical `JOB_OUTCOME_EVENT_STAGE` in `src/fitcv/pipeline_contracts.py`; producer and reporter consume it.
  2. Preserved exact six-key `job_outcome` payload by excluding this canonical reference event from common reporter telemetry enrichment.
  3. Added closed-by-default `Why?` disclosure sourced through `job_outcome_surface()` with stage, reason, exact evidence reference, and fingerprint.
  4. Removed evidence fingerprint from default timeline formatting.
  5. Replaced stale pause wording in both worker event production and run-detail timeline formatting.
  6. Added regressions for event minimality, `Why?`, hidden default fingerprint, and terminal wording consistency.
- Live verification:
  - Run ID: `ae564960-2139-4cc4-9b0c-5919c7783590`
  - Terminal status: `succeeded`
  - 13 valid symmetric JobOutcomeFact rows and 13 exact six-key `job_outcome` events
  - Outcome counts: held 4, blocked 1, rejected 8
  - All evidence references resolved; bundle missing files 0; all declared hashes matched
  - No loaded secret value or prompt body found in bundle
  - `Why?` and exact evidence references visible; default timeline contains no `evidence fingerprint` and no `Run paused`
  - Tracked control-plane, prompt, taxonomy, and input hashes unchanged across run
  - Server stopped; port released
- Focused verification:
  - `pytest -q tests/test_fitcv_cp/test_reporter.py tests/test_pipeline_outcome_fact.py` -> 48 passed
  - `pytest -q tests/test_fitcv_cp/test_app.py -k "enriched or fingerprint or job_outcome"` -> 44 passed
  - `pytest -q tests/test_fitcv_cp/test_app.py::test_timeline_stage_summary_message_does_not_call_terminal_review_paused` -> 1 passed
  - `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "review_required_reason_totals"` -> 1 passed
  - `pytest -q tests/test_pipeline.py tests/test_pipeline_outcome_fact.py` -> 169 passed
  - `pytest -q tests/test_fitcv_cp` -> 1009 passed; known Windows pytest atexit cleanup ACL warning occurred after exit code 0
  - `python -m mypy src/fitcv/pipeline_contracts.py --follow-imports=skip` -> success
  - `python scripts/hooks/run_validator.py --fast` -> passed
  - `python scripts/validate_repo_contracts.py --fast` -> passed
- SSOT disposition: No remaining SSOT violation found in audited outcome-fact scope. Canonical fact semantics, event-stage identity, user-facing reason projection, and evidence reference now have one owner each. Legacy status strings remain bounded compatibility inputs only.
- Separate docs-only SSOT correction: Active JOB-PROJECT governance now consistently names `config/` as runtime/workflow config root. Starter-only adoption guidance remains unchanged.

## Risk And Disposition

- Residual risk: Low. Provider output distribution can vary, but structural contracts and both persistence/UI projections were live-verified.
- Disposition decision: `resolved`
- Follow-ups: Keep one source-mode 13-row structural live scenario and one packaged pipeline scenario in release verification.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] bounded fix applied
- [x] post-fix live verification attached
- [x] SSOT disposition recorded
- [x] final status recorded as `resolved`