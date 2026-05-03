---
roadmap_id: fitcv-master-workstream-roadmap
status: active
registered_workstreams:
  - workstream-fitcv-semantic-spine
  - workstream-operator-control-plane
  - workstream-deterministic-acceptance-and-artifact-truth
  - workstream-bounded-agentic-cv-quality
  - workstream-agentic-observability
  - workstream-agentic-synonym-management
  - workstream-pipeline-efficiency-and-reuse
---

# Master Workstream Roadmap

## Goal

Deliver a FitCV-first platform where stage semantics and deterministic acceptance remain authoritative while portability, orchestration, and observability hardening are expanded by phase without feature drift.

## Key Deliverables

- Preserve FitCV semantic spine, deterministic acceptance, and operator control-plane truth.
- Complete Phase 2 portability/hardening outcomes with evidence-backed parity and observability.
- Keep one canonical roadmap and route details through downstream planning artifacts.

## Phase Structure

### Phase 1

### Goal
- Deliver the baseline FitCV product line with stable stage meaning, bounded agentic quality upgrades, deterministic acceptance truth, and operator-facing lifecycle control.

### Key Deliverables
- Semantic-spine stage authority from ingest through final CV outcome.
- Operator control-plane trigger, status, timeline, and run-detail truth surfaces.
- Deterministic acceptance and artifact-truth diagnostics/export surfaces.
- Bounded agentic quality seams with deterministic final gates.

### Phase 2

### Goal
- Harden architecture and portability without changing product meaning.

### Key Deliverables
- SQLite portability:
  - no feature drift vs BigQuery for equivalent behaviors.
  - behavior verification against BigQuery-backed implementation where relevant.
- Prefect orchestration:
  - implemented or verified end-to-end in this phase.
  - end-to-end verified means submit, status progression, cancellation path, and run-detail/timeline visibility are all validated.
- OpenTelemetry observability:
  - telemetry pipeline verified end-to-end.
  - trace propagation plus stage/event compatibility are validated.
- Langfuse integration:
  - implemented or verified.
  - evidence includes successful instrumented runs with trace linkage back to FitCV run/stage context.
- Universal stage contract across every deterministic and agentic stage:
  - `StageResult = { output, evidence, validation, decision, policy_version, trace_context }`
- FitCV control-plane reliability hardening:
  - preserve existing control-plane behavior.
  - persist partial artifacts for failed and cancelled runs (not only successful runs).
  - add outbox, retry, and dead-letter handling for `pipeline_run_events`.
- Standardized observability IDs:
  - include `trace_id`, `span_id`, `parent_span_id` across stage artifacts and events.
  - keep existing trace JSON surfaces while making them OpenTelemetry-compatible.
- Independent policy versioning:
  - policy versioned separately from application code.
  - every gate decision stores `policy_version`.
  - replay supports `strict` (same config + same policy) and `policy_replay` (new policy on old run).
- Data-plane split for growth:
  - operational run metadata/state on Postgres path.
  - analytical or warehouse-style storage explicitly separated.

### Phase 2 Deliverables Completed In This Branch

- SQLite portability and runtime backend resolution hardening:
  - shared backend runtime contract implemented and wired through control-plane startup/worker paths.
  - explicit env override support for backend mode (`FITCV_CP_DATA_BACKEND`) now respected by backend resolution.
  - SQLite mode startup path avoids BigQuery client requirement.
- Provider-agnostic adapter architecture:
  - `LLMClient` and `EmbeddingClient` protocol surface added under control-plane adapters.
  - routing-selection contract added to support provider scaling without stage-semantic drift.
- Observability tooling layer contract and diagnostics:
  - control-plane observability event emitter surface present and wired for orchestration/backend/model-routing diagnostics.
  - stage/result traces expose standardized trace fields and `trace_status` handling across run artifacts.
- Multi-file configuration strategy and settings-used evidence surface:
  - runtime configuration surfaces use split config ownership (`config/runtime/control_plane.yaml`, `config/runtime/pipeline.yaml`, plus env).
  - run-scoped `settings-used.json` remains the canonical execution snapshot for operator/debug evidence.
- SQLite E2E stabilization work completed for no-crash parity path:
  - run-detail/runtime paths hardened for SQLite (including null-safe BigQuery dependencies in control-plane store/read paths).
  - run execution reaches terminal success in SQLite mode with artifacts and trace exports available.
  - shortlist persistence now invoked in pipeline flow and persisted in SQLite local store.
  - non-applicable trace artifacts (`cv-analysis-trace.json`, `agentic-live-trace.json`) are exportable as explicit `trace_status=not_applicable` payloads for stable artifact surface.
- Secret-hygiene improvements in SQLite settings export:
  - `service_account_key` removed from SQLite-mode `settings-used` effective snapshot/compatibility projection exports.
  - backend data-plane metadata in settings-used now records SQLite backend in SQLite mode.

### Phase 2 Remaining/Not Yet Closed In This Branch

- Prefect orchestration is not yet fully implemented and verified end-to-end in this branch.
- OpenTelemetry collector-export pipeline is not yet fully verified end-to-end in this branch.
- Langfuse integration is not yet implemented/verified end-to-end in this branch.
- Full no-drift SQLite parity remains open for event persistence durability:
  - local run events are not yet durably persisted with SQLite parity equivalent to BigQuery-backed event history.

Current Phase 2 completion references:
- `docs/superpowers/plans/2026-05-03-phase-2-completion-gate-resolution.md`
- `docs/superpowers/plans/2026-05-03-phase-2-master-closeout-matrix.md`
- `docs/superpowers/plans/2026-05-03-14-20-phase-2-architecture-hardening-and-portability-plan.md`

## Workstream Index

- `workstream-fitcv-semantic-spine` - preserve FitCV stage-owned meaning and acceptance authority.
- `workstream-operator-control-plane` - preserve and harden trigger/run/replay/inspection operator surfaces.
- `workstream-deterministic-acceptance-and-artifact-truth` - keep decisions and evidence legible, stage-owned, and exportable.
- `workstream-bounded-agentic-cv-quality` - improve late-stage quality with bounded agentic behavior under deterministic gates.
- `workstream-agentic-observability` - make agentic behavior and deterministic gate interaction observable.
- `workstream-agentic-synonym-management` - review-first synonym assistance with deterministic runtime authority.
- `workstream-pipeline-efficiency-and-reuse` - improve throughput/reuse without semantic drift.
- `operating_system.docs-and-contract-hygiene` - maintain docs/contracts/source-of-truth hygiene.
- `operating_system.repo-governance-and-publication-boundary` - enforce private/public publication boundary.
- `operating_system.starter-shared-surface-sync` - keep shared-starter surfaces aligned without overwriting product truth.
- `operating_system.agent-workflow-reliability` - maintain validator/skill/agent reliability surfaces.

## Completion Criteria

A roadmap item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
