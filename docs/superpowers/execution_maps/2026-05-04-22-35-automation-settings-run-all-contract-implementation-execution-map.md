---
template_id: implementation-execution-map
document_type: implementation_execution_map
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
specs:
  - docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
---

# 2026-05-04 Automation Settings Run-All Contract Implementation Execution Map

## Goal
Orchestrate bounded implementation for automation-setting behavior so triage refresh/reuse, recommendation apply, global promotion, and run-all auto-accept semantics are explicit, safe, and testable without uncontrolled scope expansion.

## Scope
- In scope:
  - automation-setting contract completion in control-plane settings schema
  - run-level synonym automation orchestration (refresh -> apply -> promote)
  - run-all auto-accept gating for low-risk review-required CV actions
  - focused observability/accounting for automated actions
- Out of scope:
  - recommendation model-quality redesign
  - taxonomy extraction redesign
  - unrelated run-mode architecture changes

## Dependency Graph
1. Settings schema + effective-settings resolution are prerequisites for orchestration behavior.
2. Orchestration behavior is prerequisite for run-all terminalization updates.
3. Run-all terminalization and action accounting are prerequisites for final verification and contract-closeout evidence.

## Execution Waves
- wave 1:
  - complete settings contract surfaces
  - add new settings keys and defaults for:
    - `auto_apply_recommendation_enabled`
    - `auto_promote_global_enabled`
    - `auto_accept_ai_action_enabled`
  - ensure settings are present in effective snapshots and UI wiring
- wave 2:
  - implement bounded automation orchestration for synonym lane
  - enforce triage reuse/invalidation behavior with explicit reason reporting
  - execute auto-apply when enabled with applied/skipped/failed accounting
  - execute auto-promote when enabled only after validation + zero conflicts
- wave 3:
  - implement run-all auto-accept policy gate
  - allow only low-risk review-required reason codes for auto-accept
  - preserve awaiting_review behavior when high-risk items remain
- wave 4:
  - focused regression/contract verification
  - confirm manual fallback flows remain intact when automation is disabled
  - produce bounded pattern detection summary (`confirmed|likely|risk`) with scope decisions

## Parallel Lanes
- lane A (settings + config contract):
  - `src/fitcv_cp/settings_schema.py`
  - effective settings load/snapshot helpers in `src/fitcv_cp/app.py` / `src/fitcv_cp/worker_job.py`
- lane B (synonym automation orchestration):
  - synonym triage/apply/promote handlers in `src/fitcv_cp/app.py`
  - run-detail control surface updates in `src/fitcv_cp/templates/run_detail.html` (only where required)
- lane C (run-all review terminalization):
  - review-required terminalization path in `src/fitcv_cp/worker_job.py`
  - review action helpers in `src/fitcv_cp/app.py` as needed
- lane D (verification):
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`

## Shared-Surface Risks
- Safety drift risk:
  - auto-promote might bypass conflict/validation gates if orchestration order is wrong.
- Semantics drift risk:
  - run-all auto-accept could incorrectly finalize high-risk review-required records.
- Observability drift risk:
  - missing or inconsistent action accounting fields can hide partial failures.

## Recommended Plan Breakdown
1. Plan 1: settings contract completion and snapshot parity.
2. Plan 2: synonym automation orchestration (refresh/apply/promote) with safety gates.
3. Plan 3: run-all auto-accept low-risk gating + terminalization behavior.
4. Plan 4: focused regression verification + pattern report + scope decision log.

## Orchestration Notes
- Apply strict bounded scope: no taxonomy/model redesign.
- Preserve manual operator controls as fallback path.
- Treat conflict handling and risk gating as hard blockers for auto-promote/auto-accept.
- If cross-surface drift appears, route through drift-detection workflow before adding scope.

## Completion Criteria
An implementation-execution-map item is considered complete when:

1. all Key Deliverables from the parent spec are satisfiable through bounded plans,
2. all downstream plan items are terminal,
3. every child plan item is `completed` or `dropped` with rationale,
4. verification evidence confirms no regression of manual fallback behavior.

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
