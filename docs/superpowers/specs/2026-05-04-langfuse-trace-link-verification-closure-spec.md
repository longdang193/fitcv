---
template_id: detailed-specification
document_type: detailed_specification
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
targets:
  - src/fitcv/telemetry.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/data_plane.py
  - tests/test_fitcv_cp/test_observability_contract.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
  - docs/superpowers/plans/2026-05-03-phase-2-completion-gate-resolution.md
  - docs/superpowers/plans/2026-05-03-phase-2-master-closeout-matrix.md
related_features:
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# 2026-05-04 Langfuse Trace-Link Verification Closure Spec

## Goal
Close the Phase 2 Langfuse observability gap by adding a bounded Langfuse trace-link integration surface and verifiable end-to-end evidence that run-scoped traces can be linked from FitCV telemetry outputs without changing stage-decision authority.

## Key Deliverables
- Runtime Langfuse trace-link emission contract (enabled/disabled/degraded) integrated with existing telemetry runtime helpers.
- Run-event and run-detail observability surface that exposes Langfuse linkage status and identifiers when available.
- Deterministic fallback behavior when Langfuse is not configured or unreachable.
- Test coverage proving linkage emission and degraded-path visibility.
- Checkpoint evidence + closeout status updates that allow Langfuse row promotion from `partial` to `done`.

## Design Decisions
- Keep Langfuse as an observability sink layered on top of the existing OTel-compatible trace context, not a replacement for stage artifacts.
- Emit bounded linkage metadata only (for example trace id/link status), never raw secret material and never chain-of-thought content.
- Route integration through existing telemetry/reporter boundaries (`fitcv.telemetry` and `fitcv_cp.reporter`) to avoid product-semantic drift.
- Use environment-driven configuration toggles to preserve backward compatibility in environments without Langfuse.
- Preserve current run lifecycle and deterministic acceptance behavior; Langfuse only augments observability metadata.

## Invariants
- Stage artifacts remain the authoritative evidence source of truth.
- Deterministic acceptance and policy outcomes remain unchanged by Langfuse integration.
- Telemetry failure or missing Langfuse configuration must not block pipeline execution.
- No secrets or secret-key names are persisted in YAML config surfaces.
- Existing OTel export behavior remains supported and non-regressive.

## Validation Plan
- Runtime/test verification:
  - `python -m pytest tests/test_fitcv_cp/test_observability_contract.py -q`
  - `python -m pytest tests/test_fitcv_cp/test_app.py -q -k "telemetry or degraded or trace"`
- Planning/governance verification:
  - `python scripts/validate_template_required_sections.py`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_repo_contracts.py --fast`
- Evidence publication:
  - checkpoint result pack under
    `docs/intent/workstreams/checkpoints/workstream-agentic-observability/agentic-observability-provider-provenance/`
  - closeout artifact updates in:
    - `docs/superpowers/plans/2026-05-03-phase-2-completion-gate-resolution.md`
    - `docs/superpowers/plans/2026-05-03-phase-2-master-closeout-matrix.md`

## Completion Criteria
A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
