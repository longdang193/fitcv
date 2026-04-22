---
layer: change
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/run_lifecycle_controls/feature.source.yaml
  - docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml
  - docs/features/run_lifecycle_controls/lineage.generated.yaml
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/admin_control_plane_core/admin_control_plane_core.yaml
  - docs/features/admin_control_plane_core/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_models.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_fitcv_cp/test_worker_job.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - run_lifecycle_controls
  - admin_control_plane_core
related_stages: []
---

# Phase 11 Control Plane Evidence Completion Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Complete the next bounded Mode B evidence pass by backfilling direct
code and test evidence for `run_lifecycle_controls` and
`admin_control_plane_core`.  
Reasoning: After Phase 10, the remaining drift is concentrated in the control
plane. These two features are tightly coupled, share the same runtime and
persistence surfaces, and can be audited together without scattering into
broader UI or CV-system domains.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated feature contracts and lineage files remain generator-owned.
- File metadata must stay sparse and only name capabilities materially owned by
  the file.
- `@proves` markers must only be attached to tests that directly assert the
  named capability.
- Adoption enforcement must only expand for capabilities that have both direct
  code and direct test evidence.
- This phase must not relabel or restate feature semantics just to fit easier
  metadata mapping.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-14-43-phase-10-settings-performance-residual-evidence-audit-spec.md`
- `docs/superpowers/plans/2026-04-22-14-48-phase-10-settings-performance-residual-evidence-audit-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- current metadata and `@proves` parsing behavior

Affected stages:

- none

Affected features:

- `run_lifecycle_controls`
- `admin_control_plane_core`

Primary lens: `feature`

Affected docs:

- feature_source:
  - `docs/features/run_lifecycle_controls/feature.source.yaml`
  - `docs/features/admin_control_plane_core/feature.source.yaml`
- feature_yaml:
  - `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
  - `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- feature_lineage:
  - `docs/features/run_lifecycle_controls/lineage.generated.yaml`
  - `docs/features/admin_control_plane_core/lineage.generated.yaml`
- feature_history:
  - `docs/features/run_lifecycle_controls/history.md`
  - `docs/features/admin_control_plane_core/history.md`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none unless audit finds stale feature-specific prose`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
- readme: `none`
- generated:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`

Generated refresh required: `yes`  
Capability IDs:

- `run_lifecycle_controls.*`
- `admin_control_plane_core.*`

Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Current Gap Snapshot

As of the post-Phase-10 checkpoint:

| Feature | Missing code | Missing tests |
| --- | ---: | ---: |
| `run_lifecycle_controls` | 9 | 9 |
| `admin_control_plane_core` | 7 | 7 |
| Combined Phase 11 target | 16 | 16 |
| Repo-wide total | 86 | 86 |

Every capability in both features is currently doc-backed but still lacks direct
code and test evidence.

### `run_lifecycle_controls` Residual Capabilities

- `run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq`
- `run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs`
- `run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue`
- `run_lifecycle_controls.stale-cancellation-repair-endpoint`
- `run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs`
- `run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time`
- `run_lifecycle_controls.archive-and-unarchive-terminal-runs`
- `run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries`
- `run_lifecycle_controls.full-audit-trail-in-pipeline-run-events`

Likely implementation surfaces:

- lifecycle endpoints and timeout guard logic in `src/fitcv_cp/app.py`
- queue cancellation helpers in `src/fitcv_cp/queue.py`
- status transitions and audit persistence in `src/fitcv_cp/bq_store.py`
- checkpoint-aware cancellation behavior in `src/fitcv_cp/worker_job.py`
- run-state structures in `src/fitcv_cp/models.py`

Likely proof surfaces:

- endpoint and UI behavior tests in `tests/test_fitcv_cp/test_app.py`
- queue behavior tests in `tests/test_fitcv_cp/test_queue.py`
- persistence and event logging tests in `tests/test_fitcv_cp/test_bq_store.py`
- cooperative worker cancellation tests in `tests/test_fitcv_cp/test_worker_job.py`
- state/model tests in `tests/test_fitcv_cp/test_models.py`

### `admin_control_plane_core` Residual Capabilities

- `admin_control_plane_core.fastapi-web-server`
- `admin_control_plane_core.rq-background-worker-integration`
- `admin_control_plane_core.jinja2-admin-pages`
- `admin_control_plane_core.pipelinereporter-integration`
- `admin_control_plane_core.pipeline-runs-bigquery-table`
- `admin_control_plane_core.pipeline-run-events-bigquery-table`
- `admin_control_plane_core.insert-before-enqueue-invariant`

Likely implementation surfaces:

- FastAPI routes and rendered pages in `src/fitcv_cp/app.py`
- run enqueue/cancel integration in `src/fitcv_cp/queue.py`
- reporter plumbing in `src/fitcv_cp/reporter.py`
- persistence contracts in `src/fitcv_cp/bq_store.py`
- run models and worker orchestration in `src/fitcv_cp/models.py` and
  `src/fitcv_cp/worker_job.py`

Likely proof surfaces:

- HTTP and template tests in `tests/test_fitcv_cp/test_app.py`
- queue integration tests in `tests/test_fitcv_cp/test_queue.py`
- reporter tests in `tests/test_fitcv_cp/test_reporter.py`
- BigQuery table/persistence tests in `tests/test_fitcv_cp/test_bq_store.py`
- model/invariant tests in `tests/test_fitcv_cp/test_models.py`

## Goal

Create a Phase 11 implementation plan that:

1. maps each control-plane capability to concrete owning code and proof tests
2. defers any capability whose direct owner or test remains too broad
3. adds sparse metadata to real control-plane implementation files
4. adds truthful `@proves` markers to endpoint, persistence, queue, reporter,
   model, and worker tests
5. extends pilot enforcement only for completed control-plane capabilities
6. regenerates contracts, lineage, and generated discovery
7. records before/after gap counts for both features and repo-wide totals

## Non-Goals

This phase does not:

- eliminate every remaining repo-wide evidence gap
- refactor the control-plane architecture
- rename long capability IDs
- expand into `ui_consistency_theming`, `multi_file_job_input`, `cv_system`, or
  `inspection_debugging`
- add metadata to passive helpers that do not materially own a capability
- force completion of a capability if its proof surface is only indirect

## Proposed Shape

### 1. Joint Control-Plane Mapping Audit

The implementation plan should start with a concrete mapping table containing:

- capability ID
- candidate owning file(s)
- candidate proving test(s)
- confidence: `complete_candidate` or `defer`
- rationale

Because these two features share files, the plan should explicitly prevent
blanket tagging of `src/fitcv_cp/app.py` or `src/fitcv_cp/bq_store.py` for
every control-plane statement.

### 2. Runtime And Persistence Metadata Backfill

Add metadata only where the capability is actually implemented:

- endpoint and UI lifecycle behavior in `src/fitcv_cp/app.py`
- queue and RQ integration in `src/fitcv_cp/queue.py`
- persistence tables and status/event mutations in `src/fitcv_cp/bq_store.py`
- reporter integration in `src/fitcv_cp/reporter.py`
- worker checkpoint cancellation in `src/fitcv_cp/worker_job.py`
- model/state definitions only where they materially own an invariant

### 3. Truthful Endpoint And Store Proof Markers

Use `@proves <capability_id>` only where tests directly assert:

- queue cancellation outcomes
- awaiting-continue cancellation behavior
- timeout messages and status transitions
- archive and unarchive endpoints
- bulk action processed/skipped summaries
- persisted pipeline run rows and run-event rows
- insert-before-enqueue sequencing
- reporter handoff behavior

### 4. Enforcement Extension

Extend `repo_config/adoption-mode.yaml` only for the completed Phase 11
capabilities.

### 5. Regeneration And Measurement

Run:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `run_lifecycle_controls` gap counts
- updated `admin_control_plane_core` gap counts
- updated repo-wide totals
- which Phase 11 capabilities reached `completeness_status: complete`
- which capabilities, if any, were intentionally deferred

## Acceptance Criteria

Phase 11 is ready for implementation when:

1. an implementation plan exists with exact capability-to-file and
   capability-to-test mappings
2. weak or indirect mappings are explicitly deferred
3. selected capabilities have direct code evidence
4. selected capabilities have direct test evidence
5. pilot enforcement covers only completed mappings
6. generated feature contracts and lineage are refreshed
7. generated discovery outputs are refreshed
8. focused control-plane tests for touched files pass
9. `scripts/sync_architecture_docs.py --check` passes
10. `scripts/validate_adoption_shape.py` passes
11. `git diff --check` has no whitespace errors
12. post-phase gap counts are recorded in both the plan and the completed spec

## Risks And Guardrails

- Risk: `admin_control_plane_core.fastapi-web-server` gets proven by broad smoke
  tests instead of route behavior. Guardrail: only mark tests that assert actual
  server-owned endpoint or page behavior.
- Risk: queue behavior and lifecycle behavior get collapsed into one metadata
  owner. Guardrail: keep `queue.py`, `app.py`, `worker_job.py`, and `bq_store.py`
  responsibilities distinct.
- Risk: `pipeline_run_events` gets tagged broadly because many actions emit
  events. Guardrail: use event-persistence tests that verify concrete inserted
  event records.
- Risk: insert-before-enqueue evidence becomes anecdotal. Guardrail: require a
  direct test that proves run persistence precedes queue job id persistence or
  enqueue side effects.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 11 over-attributes evidence or makes enforcement stricter than the
actual proof surface:

1. remove the Phase 11 metadata/proof markers
2. remove the Phase 11 adoption-mode entries
3. restore any touched semantic source if the audit changed it
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the post-Phase-10 baseline

## Execution Notes

Status: `completed`

Implemented by:
`docs/superpowers/plans/2026-04-22-15-37-phase-11-control-plane-evidence-completion-plan.md`

Outcome:

- `run_lifecycle_controls` residual gaps moved from `9/9` missing code/test
  evidence to `0/0`.
- `admin_control_plane_core` residual gaps moved from `7/7` missing code/test
  evidence to `0/0`.
- Repo-wide missing direct evidence moved from `86/86` to `70/70`.
- No Phase 11 selected capabilities were deferred.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
  passed with `317 passed`.
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
  passed.
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
