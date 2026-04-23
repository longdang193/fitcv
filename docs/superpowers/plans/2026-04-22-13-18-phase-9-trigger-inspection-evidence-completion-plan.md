---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T13:18:00+02:00
change_id: 2026-04-22-phase-9-trigger-inspection-evidence-completion
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 9 trigger and inspection evidence work.
parent_workstream: none
targets:
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/trigger_run_management/lineage.generated.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_worker_job.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - trigger_run_management
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 9 Trigger And Inspection Evidence Completion Implementation Plan

**Feature Source:** `docs/features/trigger_run_management/feature.source.yaml`, `docs/features/inspection_debugging/feature.source.yaml`  
**Feature Contract:** `docs/features/trigger_run_management/trigger_run_management.yaml`, `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-13-05-phase-9-trigger-inspection-evidence-completion-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task. Keep proof sparse and defer weak mappings.

**Goal:** Complete a second bounded direct-evidence pass for the two highest remaining lineage-gap features: `trigger_run_management` and `inspection_debugging`.

**Architecture:** This phase extends existing control-plane file metadata and representative test `@proves` markers. It also cleans human-owned feature source YAML anchors for the two target features. Generated contracts, lineage, and discovery are refreshed only through `scripts/sync_architecture_docs.py`.

**Key Invariants:**
- Do not hand-edit generated feature contracts or lineage.
- Use trigger capabilities for control/action ownership and inspection capabilities for diagnostic visibility.
- Add pilot enforcement only for selected capabilities with both code and test evidence.
- Leave `cv_analysis` and `cv_generation` diagnostic capabilities partial unless directly proven in this batch.

**Rollout / Revert:**  
- rollback_trigger: over-tagged app metadata, weak proof markers, validation blocks valid states, or YAML source cleanup changes semantics.  
- rollback_method: remove Phase 9 metadata/proofs/enforcement, restore source feature semantics, rerun sync, and return to the Phase 8 baseline.

---

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-13-05-phase-9-trigger-inspection-evidence-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-13-18-phase-9-trigger-inspection-evidence-completion-plan.md`
- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/features/inspection_debugging/feature.source.yaml`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/queue.py`
- `src/fitcv_cp/worker_job.py`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_queue.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Generated outputs to refresh**

- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/lineage.generated.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/lineage.generated.yaml`
- `docs/generated/*`
- `docs/stages/*.yaml`

## Selected Capability Mappings

### Trigger Run Management

- `src/fitcv_cp/app.py`
  - `trigger_run_management.runs-list-management`
  - `trigger_run_management.run-detail-actions`
  - `trigger_run_management.job-input-modes`
  - `trigger_run_management.candidate-profile-input-modes`
  - `trigger_run_management.synonym-overlay-at-trigger`
  - `trigger_run_management.shared-stage-progress`
  - `trigger_run_management.synonym-overlay-replacement`
  - `trigger_run_management.run-health-surface`
  - `trigger_run_management.run-owned-artifact-exports`
  - `trigger_run_management.stage-artifact-downloads`
  - `trigger_run_management.synonym-overlay-inspection`
  - `trigger_run_management.run-results-export`
  - `trigger_run_management.shortlist-debug-exports`
  - `trigger_run_management.decision-chain-outcomes`
  - `trigger_run_management.reranker-fit-authority`
- `src/fitcv_cp/bq_store.py`
  - `trigger_run_management.runs-list-management`
  - `trigger_run_management.run-detail-actions`
  - `trigger_run_management.run-results-export`
  - `trigger_run_management.run-owned-artifact-exports`
- `src/fitcv_cp/queue.py`
  - `trigger_run_management.runs-list-management`
  - `trigger_run_management.run-detail-actions`
- `src/fitcv_cp/worker_job.py`
  - `trigger_run_management.shared-stage-progress`
  - `trigger_run_management.run-results-export`
  - `trigger_run_management.run-owned-artifact-exports`
  - `trigger_run_management.reranker-fit-authority`

### Inspection Debugging

- `src/fitcv_cp/app.py`
  - `inspection_debugging.synonym-overlay-inspection`
  - `inspection_debugging.run-owned-artifact-exports`
  - `inspection_debugging.settings-used-export`
  - `inspection_debugging.results-ledger-inspection`
  - `inspection_debugging.stage-transition-diagnostics`
  - `inspection_debugging.prompt-provenance-diagnostics`
  - `inspection_debugging.ranking-diagnostics`
  - `inspection_debugging.shortlist-diagnostics`
  - `inspection_debugging.reuse-diagnostics`
  - `inspection_debugging.quality-metrics-diagnostics`
  - `inspection_debugging.enriched-job-debug-export`
  - `inspection_debugging.rule-filter-diagnostics`
- `src/fitcv_cp/bq_store.py`
  - `inspection_debugging.settings-used-export`
  - `inspection_debugging.stage-transition-diagnostics`
  - `inspection_debugging.results-ledger-inspection`
  - `inspection_debugging.enriched-job-debug-export`
- `src/fitcv_cp/worker_job.py`
  - `inspection_debugging.settings-used-export`
  - `inspection_debugging.results-ledger-inspection`
  - `inspection_debugging.stage-transition-diagnostics`
  - `inspection_debugging.prompt-provenance-diagnostics`
  - `inspection_debugging.reuse-diagnostics`
  - `inspection_debugging.quality-metrics-diagnostics`

Deferred:

- `inspection_debugging.cv-analysis-diagnostics`
- `inspection_debugging.cv-generation-diagnostics`

Reason: these need a focused CV analysis/generation diagnostic pass rather than a control-plane trigger/inspection pass.

## Tasks

### Task 1: Source YAML Anchor Cleanup

- [x] Replace `&id001` / `*id001` stage participation aliases in `trigger_run_management/feature.source.yaml` with explicit capability lists.
- [x] Replace `&id001` / `*id001` stage participation aliases in `inspection_debugging/feature.source.yaml` with explicit capability lists.
- [x] Confirm no `&id` or `*id` YAML anchors remain in those source files.

### Task 2: Code Evidence Metadata

- [x] Extend `src/fitcv_cp/app.py` capability metadata with selected trigger and inspection capabilities.
- [x] Extend `src/fitcv_cp/bq_store.py` capability metadata with selected trigger and inspection persistence capabilities.
- [x] Extend `src/fitcv_cp/queue.py` capability metadata with selected trigger queue/action capabilities.
- [x] Extend `src/fitcv_cp/worker_job.py` capability metadata with selected trigger and inspection snapshot/export capabilities.

### Task 3: Test Proof Metadata

- [x] Add `@proves` markers to representative app tests for runs list, run detail actions, inputs, overlays, artifacts, health, results, decision chains, and diagnostics.
- [x] Add `@proves` markers to representative BQ store tests for persistence-backed run and inspection surfaces.
- [x] Add `@proves` markers to representative queue tests for queued run action behavior.
- [x] Add `@proves` markers to representative worker tests for shared progress, exports, settings, diagnostics, and reranker-authority evidence.

### Task 4: Enforcement And Governance

- [x] Add selected Phase 9 capabilities to `repo_config/adoption-mode.yaml` pilot enforcement.
- [x] Update `docs/operating_system/feature-lifecycle.md` to mention Phase 9 trigger/inspection evidence extension and source YAML readability cleanup.

### Task 5: Regenerate And Measure

- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Record post-sync gap counts for `trigger_run_management`, `inspection_debugging`, and repo-wide totals.
- [x] Confirm selected capabilities now have code and test evidence in lineage.

### Task 6: Verify And Close

- [x] Run focused pytest:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Run `git diff --check`.
- [x] Mark the Phase 9 spec and plan completed with execution notes.

## Execution Notes

Status: `completed`

Completed: 2026-04-22

Results:

- `trigger_run_management` evidence gaps reduced from `30/30` to `0/0`.
- `inspection_debugging` evidence gaps reduced from `28/28` to `4/4`.
- Remaining `inspection_debugging` gaps are the intentionally deferred `cv-analysis-diagnostics` and `cv-generation-diagnostics` capabilities.
- Repo-wide evidence gaps reduced from `182/182` to `128/128`.
- Source YAML anchors were removed from both targeted human-owned feature source files.

Verification:

- `.\.venv\Scripts\python.exe -m py_compile tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py` passed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py` passed with `306 passed`.
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check` passed.
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with only LF/CRLF working-copy warnings.
