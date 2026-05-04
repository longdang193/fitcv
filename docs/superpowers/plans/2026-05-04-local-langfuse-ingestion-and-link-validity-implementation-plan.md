---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-04-local-langfuse-ingestion-and-link-validity-spec.md
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

# 2026-05-04 Local Langfuse Ingestion And Link Validity Implementation Plan

**Goal:** Ensure Langfuse run-detail/link signals reflect real ingestion availability while preserving deterministic pipeline authority and non-blocking observability behavior.

## Scope

- refine Langfuse status semantics so link generation is not treated as ingestion proof
- align reporter payload and run-detail health aggregation with updated semantics
- keep local-first startup defaults explicit and override-safe
- add regression tests for event payload contract and run-detail status behavior
- validate end-to-end on local Langfuse runtime

## Non-Goals

- changing stage acceptance/policy decisions
- replacing stage artifacts with Langfuse as evidence authority
- introducing cloud-first defaults
- broad observability architecture refactor

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Langfuse Runtime Status Contract
- [ ] update Langfuse runtime helper semantics in `src/fitcv/telemetry.py` to distinguish URL capability from ingestion-confirmed availability
- [ ] keep disabled/degraded behavior explicit and backward-compatible for consumers

## Task 2: Reporter And Run-Detail Alignment
- [ ] align `src/fitcv_cp/reporter.py` payload emission to updated Langfuse semantics
- [ ] align `src/fitcv_cp/app.py` run-detail health aggregation and card status mapping to avoid false-positive confidence

## Task 3: Local-First Defaults + Docs
- [ ] verify startup scripts remain local-first and env override-safe (`start_web.ps1`, `start_worker.ps1`)
- [ ] update docs guidance in `docs/observability.md` and `docs/fitcv-control-plane-setup.md` for effective env precedence and expected local behavior

## Task 4: Tests And Live Verification
- [ ] add/adjust tests in `tests/test_fitcv/test_telemetry.py` and `tests/test_fitcv_cp/test_app.py` for updated status semantics
- [ ] run local live verification with Langfuse on `localhost:3000` and confirm run-detail behavior matches ingestion reality

## Verification

```powershell
python -m pytest tests/test_fitcv/test_telemetry.py -q
python -m pytest tests/test_fitcv_cp/test_app.py -q -k "langfuse or telemetry or events"
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_repo_contracts.py --fast
```

## Exit Criteria

1. Langfuse status surfaces are ingestion-truthful and test-backed.
2. Run-detail no longer implies trace availability solely from constructed URLs.
3. Local-first startup behavior is explicit and documented.
4. Deterministic stage-result authority remains unchanged.
