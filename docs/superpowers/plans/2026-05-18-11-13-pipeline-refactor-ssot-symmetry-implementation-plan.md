---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: pipeline-refactor-ssot-symmetry-implementation-plan
author: codex
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-18-11-09-pipeline-refactor-ssot-symmetry-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_observability.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_status_registry.py
  - tests/golden/pipeline_refactor/
related_features:
  - run_lifecycle_controls
  - bounded_parallel_enrichment
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Execute behavior-preserving refactor of `src/fitcv/pipeline.py` into SSOT-aligned orchestration and shared abstractions, while proving no contract drift in checkpointing, events, stage artifacts, and terminal statuses.

## Key Deliverables

### Deliverable 1: Stage-orchestration decomposition with preserved behavior

`run_pipeline` reduced to canonical dispatcher + stage execution calls, with unchanged stage order, pause/resume semantics, and run result payload shape.

### Deliverable 2: Canonical status/event/artifact contract surfaces

Introduce shared status transition registry, shared stage-boundary handler, and decomposed stage-artifact builders with output parity for existing consumers.

### Deliverable 3: Verified refactor safety with GitNexus and parity tests

Every extraction/rename step guarded by GitNexus impact/context checks and final detect-changes verification, plus pytest/mypy and golden diff evidence.

## Task/Wave Breakdown

### Task 1: Baseline contracts and safety harness

**Purpose:**
- freeze behavior expectations before structural edits

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/golden/pipeline_refactor/` (new fixtures)
- Verify: `docs/superpowers/specs/2026-05-18-11-09-pipeline-refactor-ssot-symmetry-spec.md`

**Preconditions:**
- parent spec approved for execution
- GitNexus freshness confirms index matches HEAD

**Steps:**
- [x] Step 1: capture baseline fixtures for full run and checkpointed run outputs (run result, stage artifacts, event stream)
- [x] Step 2: add parity tests asserting unchanged stage order, resume behavior, and output payload key contracts
- [x] Step 3: add table-driven baseline for status transition expectations across cv_analysis/cv_generation terminals

**Verification:**
- [x] `uvx pytest tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_status_registry.py -q`

**Exit Criteria:**
- baseline parity harness exists and fails on contract drift

### Task 2: Extract pipeline context and boundary helpers

**Purpose:**
- remove data clumps and duplicate stage-boundary logic without changing stage outcomes

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_context.py` (new)
- Verify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Task 1 complete
- GitNexus safety checks executed for extraction targets

**Steps:**
- [x] Step 1: run `gitnexus_context({name: "run_pipeline"})` and `gitnexus_impact({target:"run_pipeline", direction:"upstream"})`
- [ ] Step 2: introduce `PipelineContext` and `PipelineState` dataclasses; migrate repeated state dictionaries to typed access
- [ ] Step 3: introduce canonical stage-boundary helper handling progress callback + `stop_after_stage` + checkpoint summary
- [ ] Step 4: rewire existing stage blocks to use boundary helper while preserving existing return/pause outputs

**Verification:**
- [ ] `uvx pytest tests/test_pipeline_stage_resume_parity.py -q`
- [ ] parity fixture diff unchanged

**Exit Criteria:**
- single canonical boundary path used by all stage pauses

### Task 3: Stage dispatcher and runner module extraction

**Purpose:**
- split monolithic flow into stage-scoped execution units with one dispatcher SSOT

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py` (new)
- Verify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Task 2 complete
- GitNexus checks for each extracted stage function

**Steps:**
- [ ] Step 1: define dispatcher map keyed by canonical stage sequence
- [ ] Step 2: extract stage functions (`normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, `cv_generation`) into runner module in small batches
- [ ] Step 3: keep orchestration loop in `run_pipeline` minimal: resolve start/stop, dispatch stage, process boundary result
- [ ] Step 4: preserve cancellation checks and checkpoint payload serialization semantics

**Verification:**
- [ ] `uvx pytest tests/test_pipeline_stage_resume_parity.py -q`
- [ ] checkpointed and full-run golden payloads unchanged

**Exit Criteria:**
- `run_pipeline` is dispatcher-centric and stage logic is extracted

### Task 4: Status registry and observability extraction

**Purpose:**
- centralize status semantics and decouple observability payload assembly from orchestration

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_observability.py` (new)
- Verify: `tests/test_pipeline_status_registry.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: introduce canonical status transition registry used by deterministic-truth, validation-status mapping, and review reason normalization
- [ ] Step 2: move event payload builders and observation render helpers into observability sidecar module
- [ ] Step 3: ensure exported event payload keys and deterministic fields remain unchanged

**Verification:**
- [ ] `uvx pytest tests/test_pipeline_status_registry.py -q`
- [ ] event stream golden comparison unchanged for key lifecycle events

**Exit Criteria:**
- no duplicated status-string conditionals across cv_analysis/cv_generation summary paths

### Task 5: Stage artifact builder decomposition

**Purpose:**
- decompose stage artifact construction into per-stage summarizers + shared assembler with schema parity

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py` (new)
- Verify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Task 4 complete

**Steps:**
- [ ] Step 1: extract shared truncation/sampling utilities and stage-block assembler
- [ ] Step 2: extract per-stage summarizer builders for `normalize` through `cv_generation`
- [ ] Step 3: preserve `STAGE_TRANSITION_ARTIFACTS_PIPELINE_SCHEMA_VERSION` output shape and keys
- [ ] Step 4: retain backward-compatible artifact references used by control-plane consumers

**Verification:**
- [ ] stage artifact JSON golden diff unchanged
- [ ] `uvx pytest tests/test_pipeline_stage_resume_parity.py -q`

**Exit Criteria:**
- stage artifact output parity proven with no schema/key drift

### Task 6: GitNexus scope validation and final quality gates

**Purpose:**
- prove bounded blast radius and repository health before completion

**Files:**
- Inspect: affected files from Tasks 2-5
- Verify: `docs/generated/planning_lineage.yaml` (if touched indirectly)

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: run `gitnexus_detect_changes({scope:"all"})` and confirm changed symbols/processes match plan scope
- [ ] Step 2: run full tests relevant to pipeline and control-plane integration paths
- [ ] Step 3: run type checks and repo fast validator
- [ ] Step 4: capture evidence links/outputs in closeout note

**Verification:**
- [ ] `uvx pytest tests/`
- [ ] `uvx mypy src --show-error-codes`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- all checks pass and detected change scope remains expected

## Verification

- `uvx pytest tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_status_registry.py -q`
- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- GitNexus evidence:
  - `gitnexus_impact` + `gitnexus_context` per major extraction target
  - `gitnexus_detect_changes({scope:"all"})` pre-commit scope proof

## Completion Criteria

1. all Key Deliverables are satisfied with parity evidence attached
2. all downstream implementation tasks are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`

