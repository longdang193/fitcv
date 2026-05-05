---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
owning_workstream: workstream-agentic-observability
---

# 2026-05-04 Langfuse Rich Input-Output Observability Spec

## Goal

Enable meaningful Langfuse `Input` and `Output` trace visibility for FitCV live runs by adding bounded, non-authoritative rich observability payload emission while preserving deterministic pipeline behavior.

## Key Deliverables

- A bounded rich-observability emission contract that populates Langfuse `Input` and `Output` fields for selected high-value stages.
- A dual-lane observability model definition:
  - lane A: existing OTel trace continuity and stage timeline
  - lane B: Langfuse-native rich payload semantics for operator debugging
- A redaction and payload-budget policy for emitted input/output summaries.
- Feature-flagged rollout controls that keep current behavior safe by default when disabled or degraded.
- Verification criteria that prove traces exist and Input/Output fields are populated for target stages.

## Design Decisions

- Classify this as a `change` item, not a new workstream or operating-system item.
- Keep the work attached to `parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance` because the core objective is observability metadata richness and provenance visibility.
- Use bounded stage coverage first (`normalize`, `cv_analysis`, `cv_generation`) rather than all stages at once.
- Preserve current `langfuse_link.status` semantics (`unverified|disabled|degraded`) until explicit ingestion-confirmed status logic is separately defined.
- Treat Langfuse rich IO payloads as operator-debug surfaces only; they must not become runtime decision inputs.

## Invariants

- Stage artifacts and StageResult envelopes remain the source of truth for deterministic acceptance and policy outcomes.
- Pipeline execution must not fail when Langfuse emission fails, is disabled, or is partially degraded.
- No secret leakage: emitted input/output must be redacted and bounded.
- Existing run lifecycle behavior, queueing semantics, and stage transition contracts remain unchanged.
- Existing observability cards and event payload contracts remain backward-compatible for non-rich fields.

## Validation Plan

- Unit tests:
  - verify rich payload builder redacts and truncates correctly
  - verify disabled/degraded feature-flag paths do not emit rich payloads
- Integration/route tests:
  - verify run detail and event payloads still render and aggregate correctly
- Live-run validation:
  - run one targeted `run_all` execution
  - verify Langfuse trace exists and selected stage rows contain non-empty `Input` and `Output`
  - verify no stage decision or completion behavior changes
- Regression safety:
  - verify telemetry degradation states remain truthful under missing dependencies/config

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
