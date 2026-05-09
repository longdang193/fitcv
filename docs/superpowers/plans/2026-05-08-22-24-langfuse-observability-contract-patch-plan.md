---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-04-langfuse-rich-input-output-observability-spec.md
targets:
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/reporter.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_pipeline.py
related_features:
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# 2026-05-08 Langfuse Observability Contract Patch Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-04-langfuse-rich-input-output-observability-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `skill-executing-plans` to implement task-by-task with bounded scope.

## Goal

Patch FitCV observability so Langfuse receives useful root-trace and LLM-observation semantics from current OTel instrumentation, while preserving non-blocking telemetry behavior and avoiding a broad observability architecture rewrite.

## Key Deliverables

- Shared telemetry helpers that emit Langfuse-recognized trace and observation attributes with bounded serialization.
- Worker and pipeline root spans that carry useful Langfuse session, user, name, input, output, and filterable metadata semantics.
- Bounded observation-level Langfuse semantics for meaningful `cv_analysis` and `cv_generation` LLM boundaries.
- Focused tests and one live verification pass proving improved Langfuse usefulness without regressing disabled/degraded behavior.

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Task/Wave Breakdown

### Task 1: Scope Lock and Source-First Contract Confirmation

**Files:**
- Inspect: `src/fitcv/telemetry.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect tests: `tests/test_fitcv/test_telemetry.py`, `tests/test_fitcv_cp/test_reporter.py`, `tests/test_pipeline.py`

- [ ] Step 1: Confirm Langfuse OTel attribute contract in current docs for `langfuse.trace.name`, `langfuse.session.id`, `langfuse.user.id`, `langfuse.trace.input`, `langfuse.trace.output`, `langfuse.observation.type`, `langfuse.observation.input`, and `langfuse.observation.output`.
- [ ] Step 2: Confirm exact root span and LLM-adjacent span boundaries in current source before patching.
- [ ] Step 3: Bound duplicate-lane risk between OTel export and manual Langfuse native ingestion so patch scope is explicit.

### Task 2: Shared Telemetry Helper Patch

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify/Add tests: `tests/test_fitcv/test_telemetry.py`

- [ ] Step 1: Add bounded helper(s) to serialize Langfuse trace/observation input-output payloads into safe JSON strings.
- [ ] Step 2: Add helper(s) to assemble Langfuse trace attributes and observation attributes from run/stage context while omitting `None` values.
- [ ] Step 3: Preserve existing OTEL-disabled and exporter-degraded fallback behavior.

### Task 3: Root Trace Contract Hardening

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Modify/Add tests: `tests/test_pipeline.py` and/or focused worker/pipeline coverage if present

- [ ] Step 1: Patch `fitcv.worker_job` root span to emit stable Langfuse trace name, session ID, user ID, bounded root input, and filterable metadata.
- [ ] Step 2: Patch `fitcv.run_pipeline` root span to emit pipeline-specific Langfuse root input and bounded final output summary.
- [ ] Step 3: Ensure terminal status/output semantics are updated across key exit paths (`cancelled`, `awaiting_continue`, `succeeded`, and failure/degraded paths where present).

### Task 4: LLM Observation Semantics for `cv_analysis` and `cv_generation`

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: exact helper/module owning the selected LLM boundaries if discovered during Task 1
- Modify/Add tests: `tests/test_pipeline.py` and/or focused coverage for selected stage helpers

- [ ] Step 1: Patch the nearest truthful `cv_analysis` LLM boundary to emit observation type and bounded observation input/output payloads.
- [ ] Step 2: Patch the nearest truthful `cv_generation` LLM boundary to emit observation type and bounded observation input/output payloads.
- [ ] Step 3: Attach model/provider/status/fingerprint metadata needed for useful Langfuse debugging without leaking sensitive or oversized payloads.

### Task 5: Reporter Lane Containment

**Files:**
- Inspect/Modify if needed: `src/fitcv_cp/reporter.py`
- Modify/Add tests: `tests/test_fitcv_cp/test_reporter.py`

- [ ] Step 1: Check whether improved OTel root semantics now conflict with current manual Langfuse native ingestion behavior.
- [ ] Step 2: Keep reporter unchanged if it remains a bounded supplemental lane.
- [ ] Step 3: Apply only minimal alignment changes if verification shows obvious naming/session duplication or conflicting trace semantics.

### Task 6: Focused Verification and Residual Capture

**Files:**
- Verify against modified sources and tests above
- Update checkpoint pack for execution pass

- [ ] Step 1: Run focused pytest coverage for telemetry, reporter, and pipeline surfaces touched by the patch.
- [ ] Step 2: Run one local Langfuse verification pass and confirm session grouping, root trace usefulness, and nested LLM observation usefulness.
- [ ] Step 3: Record any remaining architecture-level lane-convergence issue as explicit follow-up rather than widening scope during this patch.

## Verification

```powershell
python -m pytest tests/test_fitcv/test_telemetry.py -q
python -m pytest tests/test_fitcv_cp/test_reporter.py -q
python -m pytest tests/test_pipeline.py -q -k "cv_analysis or cv_generation or telemetry"
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_repo_contracts.py --fast
```

Optional live verification lane:

```powershell
# start local FitCV surfaces and local Langfuse runtime
# execute one run with Langfuse enabled
# verify sessions grouped by run_id
# verify root trace shows non-empty input/output
# verify cv_analysis / cv_generation observations show useful payloads
```

## Completion Criteria

A plan item is complete when:

1. worker and pipeline root spans emit Langfuse-recognized session, user, name, input, output, and useful metadata fields,
2. at least one truthful LLM boundary in both `cv_analysis` and `cv_generation` emits bounded observation semantics,
3. focused telemetry/reporter/pipeline verification passes,
4. one live Langfuse run confirms improved sessions and trace usefulness,
5. any unresolved OTel/manual-ingestion convergence issue is explicitly logged as follow-up rather than hidden inside the patch.
