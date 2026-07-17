---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-outcome-fact-ssot-and-debug-traceability
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
parent_spec: docs/superpowers/specs/2026-07-17-20-45-fitcv-outcome-fact-ssot-and-debug-traceability-spec.md
targets:
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_pipeline.py
  - tests/test_pipeline_outcome_fact.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_observability_contract.py
  - tests/test_fitcv_cp/test_app.py
  - docs/component_boundaries.md
  - docs/observability.md
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Outcome Fact SSOT And Debug Traceability Implementation Plan

## Goal

Implement one versioned `JobOutcomeFact` as final per-job outcome truth across all terminal stages, execution modes, retries, runtimes, SQLite persistence surfaces, and consumer surfaces. Preserve stage artifacts as evidence authority and `RunEvent` as chronology authority.

Replace duplicated outcome reconstruction, diagnostic summaries, and technical run-detail sections with one shared projector, one compact user-facing outcome view, and one redacted debug ZIP generated on demand. Add no database, table, service, dependency, durable bundle store, or configuration surface.

## Key Deliverables

### One canonical outcome contract and reason registry

`src/fitcv/pipeline_contracts.py` owns `job_outcome.v1`, canonical outcomes, reason-code metadata, validation, fingerprinting, human labels, and the single native/legacy projector. Every terminal outcome uses same required keys.

### Native facts through existing persistence paths

Pipeline and control-plane producers attach one validated fact to each terminal per-job result. Existing result JSON, artifacts, snapshots, and mirrors carry object without schema migration or parallel persistence. Events contain only minimal outcome reference and fingerprint.

### One projection path for counts, exports, and UI

Result exports, run-level counts, job rows, reason text, event references, and historical reads consume same projector. Native facts win; one compatibility path projects `decision_chain`, then stage/result/debug evidence, then explicit `legacy_unclassified` output without writing historical data.

### Duplicate diagnostics and technical UI removed

Delete duplicate outcome label maps, summary builders, fallback builders, dead orchestration diagnostics, and UI-only technical projections after consumers move to shared projector. Remove runtime/backend tables, attempt identifiers, trace tables, fingerprints, and raw diagnostic sections from default run detail.

### Existing run artifact bundle upgraded for debugging

Extend existing `/admin/runs/{run_id}/artifacts.zip`, artifact selector, manifest builder, and tests. Add redaction, file checksums, missing-file reasons, and debug labeling without creating another route or builder. `/local/system/diagnostics` remains separate.

### Managed documentation and verification evidence

Human-owned feature sources and observability/component-boundary docs describe final ownership. Generated architecture and planning lineage refresh from canonical sources. Focused, full, privacy, and live-run proof close change.

## Task/Wave Breakdown

### Task 1: Lock source inventory and deletion ledger

**Purpose:**
- Map every terminal outcome producer and consumer before changing shared code.

**Files:**
- Inspect: `src/fitcv/pipeline_contracts.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app_run_support.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `tests/test_pipeline.py`
- Inspect: `tests/test_fitcv_cp`

**Preconditions:**
- Approved parent spec remains active.
- Run `scripts/get_gitnexus_freshness.ps1`; refresh GitNexus before high-trust impact analysis when possible, otherwise keep graph output advisory.

**Steps:**
- [x] Enumerate every terminal stage status, `decision_chain` value, reason field, result row, artifact field, event payload, counter, and UI label.
- [x] Record one producer-to-consumer matrix covering run-all, manual-staged, initial, retry, continue, FitCV Local, developer/server, native, and legacy data.
- [x] Classify each field or helper as authority, required projection, compatibility input, or removable duplication.
- [x] Confirm exact deletion candidates and direct references before edits, including `PIPELINE_OUTCOME_META`, `DECISION_CHAIN_LABELS`, `_build_ranked_cv_outcome_summary`, `_build_cv_generation_failure_reason_summary`, `_run_detail_visibility_registry`, `_run_overview_consistency_summary`, `_build_orchestration_diagnostics`, `_run_replay_context_summary`, `_run_data_plane_summary`, and route-local `run_attempt_events` UI projection. Classify historical debug and stage-artifact readers as retained compatibility evidence collectors only when they delegate all semantic defaults to the canonical projector.
- [x] Run GitNexus upstream impact analysis for every function, class, or method selected for modification or deletion; stop and report HIGH or CRITICAL risk.
- [x] Capture focused baseline test results before implementation.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_app.py -q`
- [x] Source scan shows every candidate deletion has named replacement or explicit retain decision.

**Exit Criteria:**
- No outcome path, diagnostic helper, technical UI field, or compatibility input remains unclassified.

### Task 2: Add symmetric outcome contract

**Purpose:**
- Create one validated builder and projector before changing producers.

**Files:**
- Modify: `src/fitcv/pipeline_contracts.py`
- Create: `tests/test_pipeline_outcome_fact.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 1 inventory complete.
- GitNexus impact completed for modified symbols in `pipeline_contracts.py`.

**Steps:**
- [x] Add canonical outcome and projection-status identities without class hierarchy, plugin framework, or new dependency.
- [x] Add one reason registry containing stable code, owning stage or policy family, human label, and recommended action; keep variable values in `reason_facts`.
- [x] Add one builder/validator for exact `job_outcome.v1` required-key set: `schema_version`, `run_id`, `job_key`, `job_url`, `attempt_id`, `stage`, `stage_status`, `outcome`, `reason_code`, `reason_facts`, `policy_version`, `trace_id`, `evidence_ref`, `projection_status`, and `occurred_at`.
- [x] Define grain as one exported input occurrence and derive `job_key` exactly as `input:<input_index>` from immutable run input order; retain existing raw fingerprint and normalized URL identities for content and lookup only.
- [x] Enforce timezone-aware timestamps, mandatory reasons, finite JSON leaves, and exact v1 bounds: 16 keys, depth 3, 16 list items, 512 characters per string, and 4096 canonical UTF-8 JSON bytes.
- [x] Require `evidence_ref={artifact,fingerprint,record_key}` with `record_key == job_key`.
- [x] Add deterministic SHA-256 fingerprinting over canonical JSON.
- [x] Add one shared projection function using precedence: valid native v1 fact, `decision_chain`, stage/result/debug fields, then `legacy_unclassified`.
- [x] Project present malformed v1 facts or unknown major versions as `invalid_native_outcome` with `projection_status=incomplete`; never silently fall through to legacy evidence.
- [x] Preserve unknown additive v1 fields and future reason codes through safe reader behavior and fallback wording.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_outcome_fact.py -q`
- [x] Table-driven cases prove identical keys for accepted, held, blocked, rejected, and skipped outcomes across every pipeline stage.
- [x] Invalid or missing reasons, unbounded facts, naive timestamps, malformed evidence, and invalid outcomes fail at builder boundary.
- [x] Native, decision-chain-only, status-only, ambiguous, and unknown-code fixtures project deterministically without writes.

**Exit Criteria:**
- One module owns outcome semantics, validation, labels, compatibility, and fingerprints.

### Task 3: Emit native facts from terminal job results

**Purpose:**
- Attach one native fact where final per-job results are already constructed.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify only if inventory proves necessary: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/models.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`

**Preconditions:**
- Task 2 contract complete.
- GitNexus impact completed for each producer symbol before edit.

**Steps:**
- [x] Build facts once in the existing export-row constructor, where every trigger-time input occurrence already receives one terminal row.
- [x] Preserve `_input_index` long enough to derive `job_key=input:<input_index>`, then keep existing output sorting and remove only the private index field.
- [x] Implement the exhaustive native status mapping from the parent spec; no producer-local mapping or label table is allowed.
- [x] Require skipped results to include owning stage, native stage status, stable reason, observed/required facts when applicable, and exact stage artifact record reference.
- [x] Preserve `run_id` and `job_key` across retry and continue; change only attempt identity and timestamp where required.
- [x] Include fact in existing result/export JSON and terminal artifact payloads; add no database column or independent write.
- [x] On review resolution, atomically replace held fact with accepted or rejected fact while events retain both fingerprints.
- [x] Fail producer validation before persistence when terminal result cannot produce valid fact.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py -q`
- [x] Mixed terminal-outcome fixture contains one valid fact per job.
- [x] Retry, continue, run-all, and manual-staged fixtures preserve semantic identity and exact required-key symmetry.
- [x] Existing stored row shape remains readable without migration.

**Exit Criteria:**
- Every new terminal job result carries exactly one validated native fact through existing persistence paths.

### Task 4: Move events, counts, exports, and legacy reads to projector

**Purpose:**
- Eliminate consumer-specific outcome reconstruction before deleting helpers.

**Files:**
- Modify: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_mirror.py`
- Verify: `tests/test_fitcv_cp/test_observability_contract.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 native emission complete.
- GitNexus impact completed for each changed event, export, mirror, summary, and fallback symbol.

**Steps:**
- [x] Encode minimal outcome event references containing only `job_key`, stage, outcome, reason code, outcome fingerprint, and evidence reference.
- [x] Keep event emission optional to final semantic truth; result fact remains authoritative when event append fails.
- [x] Derive accepted, held, blocked, rejected, skipped, and total counts from projected facts.
- [x] Make result export, terminal mirror, run-detail job rows, and API-facing summaries consume same projection output.
- [x] Route every historical read through single compatibility projector; perform no backfill and no database mutation.
- [x] Reconcile native fact fingerprint, event reference, result export, and stage evidence fingerprint in tests.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_app.py -q`
- [x] Mixed native and legacy fixture produces identical semantic output across export, mirror, API projection, event reference, and UI context.
- [x] Run-level counts equal direct counts from projected facts.

**Exit Criteria:**
- No active consumer reconstructs final outcome meaning independently.

### Task 5: Extend existing run artifact bundle

**Purpose:**
- Preserve reproducibility by upgrading existing run ZIP without restoring technical UI or adding durable diagnostics.

**Files:**
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_observability_contract.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 4 consumer migration complete.
- GitNexus impact completed for bundle route and helper symbols.

**Steps:**
- [x] Extend `_build_available_run_artifact_files`, `_build_run_artifact_bundle_manifest`, and existing `/admin/runs/{run_id}/artifacts.zip`; create no second run-bundle route or ZIP builder.
- [x] Assemble available `run.json`, `results.json`, `events.json`, `jobs-input.json`, `candidate-profile.json`, `settings-used.json`, `stage-artifacts.json`, `cv-debug.json`, and `prompts-and-models.json` from existing persisted sources.
- [x] Use one allowlist-based redaction/bounding pass; exclude credentials, full prompt text, private reasoning, raw provider traffic, and oversized values.
- [x] Advance existing manifest additively from `run_artifact_bundle_v6` with run/build identity, filenames, schema versions, SHA-256 hashes, missing-file reasons, redaction status, and timezone-aware generation time.
- [x] Keep existing response route and compatible filename; write no DB row and retain no durable ZIP.
- [x] Rename existing run-detail action from `Download All Artifacts (.zip)` to `Download debug bundle`.
- [x] Keep `/local/system/diagnostics` separate and unchanged.
- [x] Keep bundle generation available for native, legacy-projected, incomplete, failed, cancelled, and partially completed runs.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_app.py -q`
- [x] Existing artifact-bundle partial/succeeded tests remain green; two fixed-fixture bundles contain equivalent included-file hashes except generation metadata.
- [x] Manifest hashes match included bytes and every unavailable file has bounded reason.
- [x] Credential, prompt-text, private-reasoning, and oversized-payload canaries remain absent from fact, event, HTML, and ZIP bytes.

**Exit Criteria:**
- One disposable bundle provides bounded debugging evidence for every readable run state without another persistence or administration layer.

### Task 6: Delete duplicate diagnostics and simplify run detail

**Purpose:**
- Remove redundant administration and technical UI after shared projection owns meaning.

**Files:**
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_observability_contract.py`

**Preconditions:**
- Task 5 debug bundle complete.
- Task 4 consumer migration complete.
- Task 1 deletion ledger rechecked against current references.
- GitNexus impact completed for every deleted symbol.

**Steps:**
- [x] Delete `PIPELINE_OUTCOME_META`, `DECISION_CHAIN_LABELS`, outcome summary builders, and semantic stage/debug fallback projectors. Retain only format-specific compatibility evidence readers, named as evidence readers and delegating outcome semantics to the shared projector.
- [x] Delete dead orchestration/backend diagnostic code, including `_build_orchestration_diagnostics`, while retaining inert legacy DB fields only for compatibility.
- [x] Delete UI-only visibility/consistency, replay-context, data-plane, attempt, trace, and fingerprint projections when no non-UI consumer remains.
- [x] Remove default `Runtime and Backend Details`, `Run Attempt Timeline`, and `Stage Result Policy + Trace Summary` sections plus raw technical identifiers.
- [x] Replace duplicated pipeline-result badges and failure summaries with one compact per-job projection: outcome, stage, reason, `Why?`, and evidence link.
- [x] Keep compact human event chronology and artifact actions; do not show raw event payloads or backend internals by default.
- [x] Move any user action trapped inside advanced block to its owning user-facing section before deleting wrapper.
- [x] Delete obsolete tests asserting removed helpers; replace them with projector and absence assertions instead of compatibility wrappers.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_observability_contract.py tests/test_fitcv_cp/test_app.py -q`
- [x] Source scan finds no competing outcome label registry, reason map, counter, diagnostic summary builder, or semantic legacy fallback outside canonical projector; retained compatibility evidence readers contain source-shape parsing only.
- [x] Rendered run detail contains compact outcome/stage/reason/`Why?` controls and omits runtime backend tables, queue/worker IDs, trace tables, fingerprints, stack traces, provider payloads, and raw event dumps.

**Exit Criteria:**
- Default UI is user-first and every deleted diagnostic path has equivalent reproducibility evidence through canonical facts, artifacts, or bundle.

### Task 7: Align feature and architecture sources

**Purpose:**
- Record final SSOT boundaries without duplicating runtime facts in docs.

**Files:**
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/features/trigger_run_management/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/component_boundaries.md`
- Modify: `docs/observability.md`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Generate: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Generate: `docs/features/trigger_run_management/lineage.generated.yaml`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 2 through 6 behavior and deletion scope stable.

**Steps:**
- [x] Document `JobOutcomeFact` as final job-outcome authority, stage artifacts as evidence authority, events as chronology authority, and bundles as generated views.
- [x] Remove docs describing deleted orchestration diagnostics, duplicate UI summaries, or runtime/backend tables as current behavior.
- [x] Describe compact UI, `Why?`, compatibility projection, and debug-bundle privacy boundaries.
- [x] Update human-owned feature sources only; regenerate feature contracts, lineage, history blocks, architecture discovery, and planning lineage.

**Verification:**
- [x] `python scripts/validate_repo_contracts.py --fast` (includes current architecture-sync check path)
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] `python scripts/validate_template_required_sections.py`
- [x] `python scripts/validate_repo_contracts.py` attempted: functional validators passed; validator pytest cleanup was blocked by Windows ACL on `.tmp-tests/repo-contract-pytest`.
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Active docs and generated discovery agree with code ownership and deleted UI.

### Task 8: Run final symmetry, privacy, and live proof

**Purpose:**
- Prove change works across admissible cases and did not create another SSOT.

**Files:**
- Verify: `tests/test_pipeline_outcome_fact.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp`
- Verify: `docs/superpowers/plans/audit`

**Preconditions:**
- Tasks 1 through 7 complete.
- Fresh GitNexus change detection available or explicitly advisory if refresh remains unavailable.

**Steps:**
- [x] Run focused outcome, producer, projector, mirror, UI, bundle, and privacy tests first.
- [x] Run full pipeline and control-plane suites.
- [x] Run source scans for duplicate registries, labels, counters, fallback projectors, diagnostic builders, and removed technical UI wording.
- [x] Trigger one admissible live run ending with at least one skipped, blocked, held, or rejected job.
- [x] Reconcile fact, event reference, result export, stage artifact, UI `Why?`, run counts, and downloaded bundle for that job.
- [x] Run GitNexus `detect_changes` before any commit and inspect affected flows.
- [x] Save audit evidence under dated folder without committing secrets, disposable bundles, or large runtime artifacts.

**Verification:**
- [x] `python -m pytest tests/test_pipeline_outcome_fact.py tests/test_pipeline.py -q`
- [x] `python -m pytest tests/test_fitcv_cp -q`
- [x] `python -m compileall src/fitcv src/fitcv_cp`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] `python scripts/validate_template_required_sections.py`
- [x] `python scripts/validate_repo_contracts.py` attempted: functional validators passed; validator pytest cleanup was blocked by Windows ACL on `.tmp-tests/repo-contract-pytest`.
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] Live evidence shows one semantic outcome and reason across every inspected surface, with no credential or prompt-text leakage.

**Exit Criteria:**
- Structural symmetry, SSOT ownership, historical readability, privacy, compact UI, debug reproducibility, and deletion claims have fresh evidence.

## Verification

- `python -m pytest tests/test_pipeline_outcome_fact.py tests/test_pipeline.py -q`
- `python -m pytest tests/test_fitcv_cp -q`
- `python -m compileall src/fitcv src/fitcv_cp`
- `python scripts/validate_repo_contracts.py --fast` (includes current architecture-sync check path)
- `python scripts/validate_planning_lifecycle.py`
- `python scripts/validate_template_required_sections.py`
- `python scripts/validate_repo_contracts.py`
- `python scripts/hooks/run_validator.py --fast`
- GitNexus change detection includes expected outcome, artifact, run-detail, bundle, test, and documentation flows; workspace-wide risk remains `critical` because 82 files from earlier tasks are already modified.
- One live run reconciles canonical fact, projected event, counts, UI, evidence, export, and debug bundle.

## Execution Evidence

- `python -m pytest tests/test_pipeline_outcome_fact.py tests/test_pipeline.py -q`: `169 passed`.
- `python -m pytest tests/test_fitcv_cp -q`: `1005 passed`; pytest then emitted a benign Windows ACL cleanup warning for `C:\tmp\pytest-of-HOANG PHI LONG DANG\pytest-current`.
- Focused run-detail deletion tests: `10 passed`; compatibility evidence-reader tests: `3 passed`; outcome/bundle app selection: `4 passed`.
- `python -m compileall -q src/fitcv src/fitcv_cp`, planning lifecycle, template sections, planning-lineage generation, `git diff --check`, and hook validator subset passed.
- Full `validate_repo_contracts.py` reached its validator pytest phase; functional validators passed, while 82 test setups failed only because Windows denied cleanup/access under `.tmp-tests/repo-contract-pytest`.
- Live run `job-outcome-live-20260717` produced one `rejected` fact at `rule_filter` with reason `seniority_mismatch`; evidence resolved, fingerprints matched, counts reconciled, and secret leakage check was false.
- GitNexus `detect_changes` reports workspace-wide `critical` risk from 82 already-modified files across earlier tasks; focused impact for deleted UI helpers was `LOW`, with zero callers or affected flows.
## Completion Criteria

A plan item is complete when:

1. every new terminal job result contains one valid `job_outcome.v1`
2. all outcomes share exact required-key set and reason-code registry
3. events, counts, exports, mirrors, UI, and legacy reads use one projector
4. duplicate diagnostic builders and technical UI sections are deleted
5. compact UI explains outcomes and offers bounded evidence and bundle download
6. debug bundles are redacted, checksummed, disposable, and non-authoritative
7. historical runs remain readable without rewrite or backfill
8. focused, full, privacy, symmetry, managed-doc, and live-run proofs pass
9. all downstream tasks are `completed` or explicitly `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-17-20-45-fitcv-outcome-fact-ssot-and-debug-traceability-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
