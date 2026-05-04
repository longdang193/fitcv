---
template_id: implementation-execution-map
document_type: implementation_execution_map
layer: change
artifact_type: execution_map
status: completed
parent_workstream: workstream-operator-control-plane
map_type: implementation_execution
threads:
  - workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
specs:
  - docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
---

# 2026-05-04 Provider Storage Agnostic Parity Implementation Execution Map

## Goal
Orchestrate bounded implementation that makes runtime behavior fully provider/storage-agnostic with no feature drift between sqlite and bigquery, while preserving existing Phase 2 deterministic truth and observability contracts.

## Key Deliverables
- Provider-agnostic late-stage runtime adapter enforcement (`LLMClient` / `EmbeddingClient`) across enrichment, reranker, and CV generation flows.
- Storage-agnostic run/pipeline persistence interfaces (`RunStore` / `PipelineStore`) with sqlite and bigquery backends behind shared contracts.
- Fail-fast routing policy that blocks silent fallback to Google paths when control-plane routing targets OpenAI-compatible providers.
- Parity validation evidence showing sqlite and bigquery produce equivalent contract surfaces and operator artifacts for the same fixture runs.

## Execution Waves
- wave 1:
  - finalize config-driven provider routing in all non-agentic and late-stage callsites, including CV generation.
  - centralize model/base_url resolution through control-plane routing contract and keep secrets env-only.
  - add fail-fast guardrails for missing provider base_url/model/api key inputs.
- wave 2:
  - introduce storage interfaces for run/event/checkpoint/artifact persistence and stage-owned row persistence.
  - migrate direct BigQuery stage callsites behind interface implementations without changing outward behavior.
  - preserve sqlite restart durability and UI parity on run detail and artifacts surfaces.
- wave 3:
  - add dual-backend parity tests and fixture-driven contract comparisons for results export, stage artifacts, events, and enriched tab surfaces.
  - run live sqlite and bigquery e2e validation passes and capture checkpoint evidence pack.
  - close remaining Phase 2 portability/no-drift gaps in closeout docs based on evidence.

## Execution Evidence
- wave 1 provider-routing hardening: completed and covered by existing provider/runtime test surfaces in this branch.
- wave 2 storage-boundary migration: completed via `RunStore`/`PipelineStore` adapter routing and focused store/pipeline tests.
- wave 3 parity verification:
  - contract parity tests: `tests/test_fitcv_cp/test_storage_backend_parity.py`
  - live parity checkpoint: `docs/intent/workstreams/checkpoints/workstream-operator-control-plane/operator-control-plane-phase-2-degraded-mode-and-portability-surface/20260504-1119-dual-backend-live-parity-evidence.md`
  - parity artifact bundle:
    - `logs/parity-evidence-20260504/sqlite-run-summary.json`
    - `logs/parity-evidence-20260504/bigquery-run-summary.json`
    - `logs/parity-evidence-20260504/parity-comparison.json`

## Dependencies And Risks
- dependencies:
  - `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`
  - runtime config contracts:
    - `config/runtime/control_plane.yaml`
    - `config/runtime/pipeline.yaml`
  - active control-plane persistence and run-detail surfaces in `src/fitcv_cp/*`
- shared-surface risks:
  - adapter migration can introduce subtle runtime drift if stage-owned contracts are changed instead of wrapped.
  - storage abstraction can break run-detail visibility if artifact/event surfaces are not parity-tested.
  - provider fail-fast behavior can regress existing local flows if env assumptions are undocumented.

## Completion Criteria
An implementation-execution-map item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
