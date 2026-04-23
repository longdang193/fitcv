---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-04-22T15:37:00+02:00
change_id: 2026-04-22-phase-11-control-plane-evidence-completion
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 11 control-plane evidence work.
parent_workstream: none
targets:
  - docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml
  - docs/features/run_lifecycle_controls/lineage.generated.yaml
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

# Phase 11 Control Plane Evidence Completion Implementation Plan

**Feature Source:** `docs/features/run_lifecycle_controls/feature.source.yaml`, `docs/features/admin_control_plane_core/feature.source.yaml`  
**Feature Contract:** `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`, `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-15-20-phase-11-control-plane-evidence-completion-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task. Keep control-plane ownership sparse and avoid blanket tagging shared files.

**Goal:** Complete the bounded Mode B evidence pass for `run_lifecycle_controls` and `admin_control_plane_core` by attaching direct code and test evidence to the control-plane runtime, persistence, queue, and reporting surfaces that already implement these behaviors.

**Architecture:** The control plane is concentrated in `src/fitcv_cp/`, with endpoint/UI behavior in `app.py`, persistence in `bq_store.py`, queue/RQ integration in `queue.py`, event reporting in `reporter.py`, worker-side checkpoint cancellation in `worker_job.py`, and state contracts in `models.py`. Most proving tests already exist, so this phase is primarily a precise evidence-hydration pass rather than a behavior-adding phase.

**Key Invariants:**
- Do not edit generated feature contracts or lineage files manually.
- Only tag a capability on the file that materially owns it.
- Only add `@proves` markers to tests that directly assert the named capability.
- Extend `repo_config/adoption-mode.yaml` only for capabilities completed in this phase.

**Rollout / Revert:**  
- rollback_trigger: weak or indirect evidence mapping, or adoption-shape validation failure  
- rollback_method: remove Phase 11 metadata/proof markers/enforcement entries, rerun architecture sync, and return to the Phase 10 baseline

## Doc Update Matrix

- Feature source: `docs/features/run_lifecycle_controls/feature.source.yaml`, `docs/features/admin_control_plane_core/feature.source.yaml` unchanged unless audit reveals semantic drift
- Feature contract: `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`, `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- Feature lineage: `docs/features/run_lifecycle_controls/lineage.generated.yaml`, `docs/features/admin_control_plane_core/lineage.generated.yaml`
- Stage source: none
- Stage contracts: none
- Feature history: `docs/features/run_lifecycle_controls/history.md`, `docs/features/admin_control_plane_core/history.md` unchanged unless narrative clarification becomes necessary
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: `docs/operating_system/feature-lifecycle.md`
- README: none
- Generated discovery: `docs/generated/*`

## Selected Mapping Audit

### Run Lifecycle Controls

| Capability | Code owner(s) | Proof test(s) | Confidence | Rationale |
| --- | --- | --- | --- | --- |
| `run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq` | `src/fitcv_cp/app.py`, `src/fitcv_cp/queue.py` | `test_admin_stop_queued_run_returns_json`, `test_cancel_queued_run_returns_true_when_cancelable`, `test_cancel_queued_run_returns_false_when_not_found` | complete_candidate | App owns the stop endpoint behavior; queue owns the RQ cancellation helper. |
| `run_lifecycle_controls.cooperative-cancellation-at-safe-checkpoints-for-running-jobs` | `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/app.py` | `test_worker_marks_cancelled_when_cancel_already_requested`, `test_worker_cancellation_event_appended_on_early_exit`, `test_worker_pipeline_cancelled_exception_marks_cancelled`, `test_admin_stop_claimed_run_falls_back_to_cancelling` | complete_candidate | Worker owns checkpoint-aware cooperative cancellation; app owns the operator-facing transition into cancelling. |
| `run_lifecycle_controls.direct-cancellation-of-paused-manual-runs-in-awaiting-continue` | `src/fitcv_cp/app.py` | `test_admin_stop_awaiting_continue_run_returns_cancelled`, `test_admin_bulk_cancel_awaiting_continue_run_directly_cancels` | complete_candidate | Awaiting-continue cancellation is directly implemented by app endpoints. |
| `run_lifecycle_controls.stale-cancellation-repair-endpoint` | `src/fitcv_cp/app.py` | `test_admin_repair_cancellation_stale_run_returns_cancelled`, `test_admin_repair_cancellation_started_stale_run_returns_cancelled`, `test_admin_repair_cancellation_running_run_returns_409`, `test_run_detail_stale_cancelling_shows_repair_status`, `test_run_detail_started_stale_cancelling_shows_repair_status` | complete_candidate | App owns both the repair endpoint and its run-detail affordance. |
| `run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs` | `src/fitcv_cp/app.py` | `test_admin_runs_timeouts_running_runs_to_failed`, `test_admin_runs_timeouts_awaiting_continue_runs_to_cancelled` | complete_candidate | Timeout guard logic and status branching live in app. |
| `run_lifecycle_controls.timeout-copy-now-distinguishes-queue-wait-active-runtime-and-stage-by-stage-manual-wait-time` | `src/fitcv_cp/app.py` | `test_admin_runs_timeouts_running_runs_to_failed`, `test_admin_runs_timeouts_awaiting_continue_runs_to_cancelled` | complete_candidate | The distinct operator-facing timeout messages are emitted in app. |
| `run_lifecycle_controls.archive-and-unarchive-terminal-runs` | `src/fitcv_cp/app.py`, `src/fitcv_cp/bq_store.py` | `test_admin_archive_succeeded_run_returns_json`, `test_admin_unarchive_archived_run_returns_json`, `test_archive_run_uses_parameterized_query`, `test_unarchive_run_uses_parameterized_query` | complete_candidate | App owns eligibility and endpoints; bq_store owns persistence. |
| `run_lifecycle_controls.batch-cancel-archive-and-unarchive-endpoints-with-explicit-processed-skipped-summaries` | `src/fitcv_cp/app.py` | `test_admin_bulk_cancel_mixed_eligibility_returns_processed_and_skipped_summary`, `test_admin_bulk_archive_terminal_runs_only`, `test_admin_bulk_unarchive_archived_runs_only`, `test_admin_bulk_lifecycle_rejects_empty_run_ids`, `test_admin_bulk_lifecycle_rejects_unknown_run_ids` | complete_candidate | Bulk lifecycle summaries are endpoint-owned behavior in app. |
| `run_lifecycle_controls.full-audit-trail-in-pipeline-run-events` | `src/fitcv_cp/bq_store.py`, `src/fitcv_cp/reporter.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/worker_job.py` | `test_append_event_calls_bq`, `test_reporter_emits_event`, `test_worker_cancellation_event_appended_on_early_exit`, lifecycle endpoint tests that assert event appends indirectly only where explicit mocks exist | complete_candidate | Event persistence is owned by bq_store; reporter, app, and worker are direct event-emitting surfaces. |

### Admin Control Plane Core

| Capability | Code owner(s) | Proof test(s) | Confidence | Rationale |
| --- | --- | --- | --- | --- |
| `admin_control_plane_core.fastapi-web-server` | `src/fitcv_cp/app.py` | `test_admin_stop_queued_run_returns_json`, `test_admin_archive_succeeded_run_returns_json`, `test_runs_list_shows_active_all_archived_filter_tabs` | complete_candidate | FastAPI route and HTML response behavior is directly exercised through app tests. |
| `admin_control_plane_core.rq-background-worker-integration` | `src/fitcv_cp/queue.py`, `src/fitcv_cp/app.py` | `test_enqueue_run_returns_uuid`, `test_enqueue_run_with_job_id_returns_tuple`, `test_cancel_queued_run_returns_true_when_cancelable`, `test_post_runs_inserts_before_enqueue` | complete_candidate | Queue owns RQ integration; app owns the insert-then-enqueue control-plane orchestration. |
| `admin_control_plane_core.jinja2-admin-pages` | `src/fitcv_cp/app.py` | `test_runs_list_shows_active_all_archived_filter_tabs`, `test_runs_list_renders_bulk_action_bar_hooks`, `test_run_detail_awaiting_continue_shows_run_next_stage_and_stop_run`, `test_run_detail_archived_shows_unarchive_and_badge` | complete_candidate | Template rendering lives in app and is directly asserted by HTML tests. |
| `admin_control_plane_core.pipelinereporter-integration` | `src/fitcv_cp/reporter.py`, `src/fitcv_cp/worker_job.py` | `test_reporter_emits_event`, `test_reporter_noop_without_bq`, `test_reporter_payload_serialized` | complete_candidate | Reporter owns the control-plane event adapter; worker injects it but does not need all ownership. |
| `admin_control_plane_core.pipeline-runs-bigquery-table` | `src/fitcv_cp/bq_store.py`, `src/fitcv_cp/models.py` | `test_insert_run_calls_bq`, `test_row_to_run_maps_lifecycle_fields`, `test_list_runs_returns_list`, `test_list_runs_active_filters_archived`, `test_list_runs_archived_only`, `test_list_runs_include_all` | complete_candidate | bq_store owns row persistence and filtering; models own the run shape contract. |
| `admin_control_plane_core.pipeline-run-events-bigquery-table` | `src/fitcv_cp/bq_store.py`, `src/fitcv_cp/models.py` | `test_append_event_calls_bq`, `test_run_event_fields` | complete_candidate | bq_store owns event table writes; models own the event contract. |
| `admin_control_plane_core.insert-before-enqueue-invariant` | `src/fitcv_cp/app.py` | `test_post_runs_inserts_before_enqueue` | complete_candidate | The invariant is directly owned and asserted in the app trigger flow. |

Deferred:

- none planned for deferral at the start of execution; remove any weak mapping before enforcement if validation reveals one

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-15-20-phase-11-control-plane-evidence-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-15-37-phase-11-control-plane-evidence-completion-plan.md`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/models.py`
- `src/fitcv_cp/queue.py`
- `src/fitcv_cp/reporter.py`
- `src/fitcv_cp/worker_job.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_models.py`
- `tests/test_fitcv_cp/test_queue.py`
- `tests/test_fitcv_cp/test_reporter.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Generated outputs to refresh**

- `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
- `docs/features/run_lifecycle_controls/lineage.generated.yaml`
- `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- `docs/features/admin_control_plane_core/lineage.generated.yaml`
- `docs/generated/*`

### Task 1: Control-Plane Code Evidence

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Docs: `docs/operating_system/feature-lifecycle.md`

- [x] Step 1: Add missing control-plane capability metadata to the real owner files only.
- [x] Step 2: Keep `app.py` focused on FastAPI/Jinja lifecycle surfaces and endpoint-owned run actions.
- [x] Step 3: Keep `bq_store.py` focused on `pipeline_runs`, `pipeline_run_events`, archive/unarchive, and cancel persistence.
- [x] Step 4: Keep `queue.py` focused on RQ enqueue and queued-run cancellation.
- [x] Step 5: Keep `reporter.py` focused on reporter integration, and `worker_job.py` focused on cooperative cancellation only where it materially owns behavior.
- [x] Step 6: Add `models.py` metadata only for the shared run/event contract capabilities it directly defines.

### Task 2: Control-Plane Test Proof Evidence

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_models.py`
- Modify: `tests/test_fitcv_cp/test_queue.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: none

- [x] Step 1: Add `@proves` markers to endpoint tests covering stop, repair, archive/unarchive, bulk lifecycle summaries, timeout handling, and template rendering.
- [x] Step 2: Add `@proves` markers to BQ store tests covering `pipeline_runs`, `pipeline_run_events`, cancel fields, archive state, and archive filtering.
- [x] Step 3: Add `@proves` markers to queue, reporter, model, and worker tests for RQ integration, event reporting, state contracts, and cooperative cancellation.
- [x] Step 4: Avoid tagging broad smoke tests or tests that only happen to call a capability indirectly.

### Task 3: Enforcement And Regeneration

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Modify: `docs/operating_system/feature-lifecycle.md`
- Refresh: generated feature contracts, lineage, and `docs/generated/*`

- [x] Step 1: Add only completed Phase 11 capabilities to `repo_config/adoption-mode.yaml`.
- [x] Step 2: Update `docs/operating_system/feature-lifecycle.md` to note the Phase 11 control-plane evidence pass.
- [x] Step 3: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Step 4: Measure updated gap counts for `run_lifecycle_controls`, `admin_control_plane_core`, and repo-wide totals.

### Task 4: Verification And Closeout

**Files:**
- Modify: `docs/superpowers/archive/specs/2026-04-22-15-20-phase-11-control-plane-evidence-completion-spec.md`
- Modify: `docs/superpowers/plans/2026-04-22-15-37-phase-11-control-plane-evidence-completion-plan.md`

- [x] Step 1: Run focused pytest:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
- [x] Step 2: Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Step 3: Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Step 4: Run `git diff --check`.
- [x] Step 5: Mark the spec and plan completed with exact before/after gap counts and verification results.

## Execution Notes

Status: `completed`

Outcome:

- Completed all selected Phase 11 control-plane evidence mappings for
  `run_lifecycle_controls` and `admin_control_plane_core`.
- `run_lifecycle_controls` moved from `9/9` missing code/test evidence to
  `0/0`.
- `admin_control_plane_core` moved from `7/7` missing code/test evidence to
  `0/0`.
- Repo-wide missing direct evidence moved from `86/86` to `70/70`.
- No selected Phase 11 capability was deferred.

Verification:

- Focused pytest passed: `317 passed`.
- `scripts/sync_architecture_docs.py --check` passed.
- `scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
