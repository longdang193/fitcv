---
template_id: implementation-plan
document_type: implementation_plan
layer: change
artifact_type: plan
status: completed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
parent_execution_map: docs/superpowers/execution_maps/2026-05-04-provider-storage-agnostic-parity-implementation-execution-map.md
---

# 2026-05-04 Provider Storage Agnostic Parity Implementation Plan

## Goal
Deliver fully provider/storage-agnostic runtime behavior with no drift between sqlite and bigquery by enforcing adapter boundaries, config-routed provider resolution, and parity-validated operator artifacts.

## Key Deliverables
- All late-stage LLM calls resolve through config-routed provider adapters with env-only secrets and explicit fail-fast rules.
- Run/event/checkpoint/artifact persistence and stage persistence paths are served through storage interfaces, not direct stage-level BigQuery calls.
- SQLite and bigquery e2e runs produce equivalent contract outputs for run status, events, stage artifacts, and enriched job visibility.
- Evidence pack and closeout updates demonstrate no-drift acceptance for Phase 2 portability deliverables.

## Task Breakdown
- task 1: provider-adapter completion
  - migrate remaining Google-only late-stage callsites (especially CV generation) to provider-agnostic runtime client boundary.
  - replace local routing logic with `control_plane` model-routing resolver for provider/model/base_url.
  - enforce fail-fast errors when routed provider config is incomplete instead of silent Google fallback.
- task 2: storage-boundary completion
  - define `RunStore` and `PipelineStore` runtime interfaces and backend implementations for sqlite and bigquery.
  - route control-plane run/event/checkpoint/artifact writes and reads through store interfaces.
  - route stage persistence/query helpers through store interfaces while preserving output schemas.
- task 3: parity verification + evidence
  - add targeted parity tests for enriched-tab rows, results export, stage artifacts, and run events across sqlite/bigquery.
  - run live sqlite e2e and bigquery e2e fixture executions with identical job input/config snapshots.
  - capture evidence and update closeout matrix/docs only after verification passes.

## Execution Evidence
- adapter-boundary completion evidence:
  - `tests/test_fitcv_cp/test_store.py`
  - `tests/test_pipeline_store.py`
- parity test evidence:
  - `tests/test_fitcv_cp/test_storage_backend_parity.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
- live dual-backend parity evidence:
  - checkpoint: `docs/intent/workstreams/checkpoints/workstream-operator-control-plane/operator-control-plane-phase-2-degraded-mode-and-portability-surface/20260504-1119-dual-backend-live-parity-evidence.md`
  - summary artifacts:
    - `logs/parity-evidence-20260504/sqlite-run-summary.json`
    - `logs/parity-evidence-20260504/bigquery-run-summary.json`
    - `logs/parity-evidence-20260504/parity-comparison.json`

## Verification
- `python -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py`
- `python -m pytest tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_worker_job.py`
- `python -m pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- `python scripts/validate_template_required_sections.py`
- `python scripts/validate_planning_lifecycle.py --strict`

## Completion Criteria
A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
