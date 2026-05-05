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
  - start_web.ps1
  - start_worker.ps1
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
  - docs/fitcv-control-plane-setup.md
related_features:
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# 2026-05-04 Local Langfuse Ingestion And Link Validity Spec

## Work Classification
- Classification: `change`
- Rationale: This is a bounded runtime behavior and observability integration change in product code and startup/runtime config surfaces, not a pure operating-system or intent-only governance update.

## Goal
Ensure Langfuse trace-link observability is ingestion-truthful in local and configured environments so operator surfaces do not present misleading trace availability.

## Problem
Current Langfuse behavior can present a trace URL that looks valid while no trace is actually ingested into Langfuse. The existing link can be constructed from base URL + trace id without guaranteeing backend ingestion, which creates a misleading operator experience (`Trace not found`).

## Desired Outcome
- Langfuse trace links shown in run observability surfaces correspond to real ingested traces.
- Local development defaults are explicit and predictable (`localhost`) unless overridden.
- Operator surfaces distinguish clearly between:
  - link-only capability
  - ingestion-confirmed behavior
  - disabled/degraded states

## Affected Area
- Telemetry helpers and Langfuse status contract
- Reporter event payload emission for per-event observability metadata
- Run-detail health aggregation and presentation
- Local startup/runtime defaults and docs for effective env precedence

## Constraints
- Keep changes bounded to Langfuse observability flow and related startup/env surfaces.
- Do not alter deterministic stage decisions, acceptance policies, or stage-result authority.
- Do not introduce secret material persistence in logs, run artifacts, or config exports.
- Preserve non-Langfuse observability behavior (OTel and event delivery surfaces).

## What Should Stay True (Invariants)
- Stage artifacts remain the source of truth for runtime decisions.
- Pipeline execution must not fail due to Langfuse unavailability.
- `disabled` / `degraded` states remain explicit and machine-readable.
- Existing run lifecycle/state transitions remain unchanged.

## Invariants
- Stage artifacts remain the source of truth for runtime decisions.
- Pipeline execution must not fail due to Langfuse unavailability.
- `disabled` / `degraded` states remain explicit and machine-readable.
- Existing run lifecycle/state transitions remain unchanged.

## Key Deliverables
- Runtime ingestion contract for Langfuse status that distinguishes link construction from ingestion viability.
- Reporter payload contract updates that remain backward-compatible and bounded.
- Run-detail health semantics aligned with ingestion reality (no false confidence from synthetic URLs).
- Local startup defaults and docs aligned to local-first Langfuse usage.
- Regression tests that prove:
  - no false-positive linked state when ingestion is not possible
  - local-first behavior in startup surfaces
  - no execution-path regressions when Langfuse is disabled/degraded

## Design Decisions
- Keep Langfuse as observability augmentation only; never as authority for stage outcomes.
- Preserve current environment-driven configuration model.
- Treat URL construction as insufficient proof of ingestion.
- Prefer explicit status vocabulary over ambiguous “linked” semantics.

## Upstream Intent Linkage
- Parent thread: `workstream-agentic-observability.agentic-observability-provider-provenance`
- This follows existing observability provenance intent by tightening runtime truthfulness of trace-link signals.

## Downstream Impact Linkage
- Implementation impact:
  - telemetry helper status contract
  - reporter payload schema shape
  - run-detail health aggregation/display behavior
- Observability impact:
  - less operator confusion (`Trace not found` despite “linked”)
  - clearer disabled/degraded/ingestion states
- Execution/validation impact:
  - targeted telemetry and run-detail tests
  - live-run verification against local Langfuse instance

## Validation Plan
- Unit/integration tests:
  - `python -m pytest tests/test_fitcv/test_telemetry.py -q`
  - `python -m pytest tests/test_fitcv_cp/test_app.py -q -k "langfuse or telemetry"`
- Local live-run verification:
  - start local Langfuse on `http://localhost:3000`
  - run FitCV with local Langfuse env
  - verify run-detail status and trace URL behavior match ingestion reality
- Governance checks:
  - `python scripts/validate_template_required_sections.py`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria
1. Langfuse status semantics are ingestion-truthful and test-backed.
2. Run-detail no longer implies trace availability when trace is absent.
3. Local-first startup and env-precedence docs are aligned.
4. No regression in stage-result or deterministic acceptance contracts.

## Next Artifact
- Next artifact should be an **implementation execution map** (not another detailed spec), because the design boundary is now explicit and execution-ready with clear targets and validation commands.
