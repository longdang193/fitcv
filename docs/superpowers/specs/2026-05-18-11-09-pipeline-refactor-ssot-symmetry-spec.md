---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: pipeline-refactor-ssot-symmetry-spec
author: codex

parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_observability.py
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

Define behavior-preserving refactor of `src/fitcv/pipeline.py` to enforce SSOT and structural symmetry, reduce orchestration complexity, and remove contract drift surfaces (especially stage-boundary and artifact-shape duplication).

## Key Deliverables

### Deliverable 1: Stage orchestration SSOT

Define single stage orchestration surface where stage order, stage entry/exit, pause/checkpoint, and progress callback behavior come from one canonical dispatcher path.

### Deliverable 2: Artifact/decision contract symmetry

Define canonical builders for stage artifacts, event payloads, and status transitions so equivalent logic is not duplicated across stage branches.

### Deliverable 3: Safe refactor execution boundaries

Define extraction boundaries and update sequence for module split, plus GitNexus safety checks required before and after edits.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- map current behavior and duplication without changing outputs

**Steps:**
- [ ] baseline `run_pipeline` stage flow and branch points
- [ ] catalog repeated logic families: stage boundary, status normalization, event payload, profile resolution, late-stage reuse
- [ ] identify externally consumed contracts: run return payload, stage transition artifacts, event payload schemas

**Verification:**
- [ ] callable/contract map exists for each planned extraction target

**Exit Criteria:**
- no extraction step relies on unstated behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- lock target architecture and refactor sequence

**Steps:**
- [ ] define target module boundaries
- [ ] define canonical status registry and transition map
- [ ] define stage boundary handler contract
- [ ] define artifact builder ownership split

**Verification:**
- [ ] each current duplicate path has one canonical owner in target design

**Exit Criteria:**
- design is bounded and behavior-preserving strategy is explicit

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations explicit before coding

**Steps:**
- [ ] define parity test matrix
- [ ] define GitNexus impact/check protocol per extraction step
- [ ] define acceptance metrics and rollback conditions

**Verification:**
- [ ] validation plan proves no external contract regressions

**Exit Criteria:**
- spec ready for implementation plan handoff

## Design Decisions

### Decision: Stage dispatcher extraction

- context: `run_pipeline` mixes orchestration + per-stage business logic in one large function
- choice: split into stage-specific runner functions invoked by one dispatcher keyed by canonical stage sequence
- alternatives considered:
  - keep monolith and only add comments
  - partial split for late stages only
- impact:
  - improved checkpoint/progress symmetry
  - lower branching depth in top-level function
  - predictable stage-entry behavior for all stages

### Decision: Canonical stage boundary API

- context: repeated `stage_progress_callback` and `stop_after_stage` handling causes drift risk
- choice: introduce single `handle_stage_boundary(...)` utility to emit progress + checkpoint summary + pause decision
- alternatives considered:
  - inline helper per stage
  - callback wrappers only
- impact:
  - one SSOT for pause semantics
  - fewer stage-specific divergence bugs

### Decision: Pipeline context object

- context: data clumps and long parameter trains across helpers
- choice: introduce `PipelineContext` dataclass for immutable run/config/store/runtime handles and `PipelineState` for mutable per-run accumulators
- alternatives considered:
  - keep dict-based shared state
  - pass expanded param lists
- impact:
  - easier function contracts
  - better test fixture reuse

### Decision: Status transition registry

- context: status strings repeated across cv_analysis/cv_generation/event/export logic
- choice: define canonical status constants + transition classification map consumed by event, debug, and artifact builders
- alternatives considered:
  - continue string comparisons
  - enums only without transition table
- impact:
  - deterministic mapping across outputs
  - easier policy extensions without branch explosion

### Decision: Stage artifact builder decomposition

- context: `_build_stage_transition_artifacts` owns too many responsibilities
- choice: split into per-stage summarizers + shared assembler; keep output schema unchanged
- alternatives considered:
  - keep current function and add internal sections
- impact:
  - easier schema evolution
  - reduced regression blast radius per stage

### Decision: Observability sidecar module

- context: orchestration interleaves telemetry rendering/event payload construction
- choice: move event payload/render helpers to `pipeline_observability.py` while preserving payload schema
- alternatives considered:
  - keep in file and group by region
- impact:
  - clearer core flow
  - dedicated observability tests

## Invariants

- Stage execution order remains exactly: `normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`.
- Resume behavior from checkpoint remains deterministic and backward compatible.
- `run_pipeline` return payload shape remains backward compatible for existing control-plane consumers.
- Stage transition artifact schema version and key topology remain unchanged unless explicitly version-bumped in separate spec.
- Event payload keys and deterministic-truth fields remain backward compatible.
- Existing accepted/review-required/validation-failed/generation-failed/persistence-failed semantics remain unchanged.
- Refactor must not increase external side effects (extra writes/events) for same inputs.

## Acceptance Criteria

- Monolithic `run_pipeline` orchestration reduced to dispatcher + stage calls; stage-specific logic moved to extracted functions/modules.
- All stage boundary behavior uses one canonical helper.
- All status-to-decision mappings resolve through one registry function/table.
- All stage artifact blocks generated via shared assembler + per-stage summarizers.
- No API/contract diffs in run output payload, stage artifact payload, and event payload for golden fixtures.
- Test + mypy gates pass.

## Non-Goals

- No business-rule changes to enrichment, filtering, ranking, analysis, or generation algorithms.
- No prompt/content/model-routing policy changes.
- No schema redesign for stage artifacts or run export payloads.
- No migration of persistence backends.
- No performance micro-optimization unrelated to structural refactor.

## Risks and Mitigations

- Risk: hidden coupling in stage-local mutations.
  - mitigation: extract with golden snapshot tests before/after; migrate one stage at a time.
- Risk: checkpoint/resume regression.
  - mitigation: targeted tests for each `stop_after_stage` boundary and resume start-stage canonicalization.
- Risk: status mapping drift after centralization.
  - mitigation: table-driven tests over all terminal/intermediate statuses.
- Risk: cross-file caller breakage from extraction/rename.
  - mitigation: GitNexus impact/context checks before each extraction batch; detect_changes before commit.

## Validation Plan

- proof target: stage-order and pause/resume semantics unchanged
  - method: tests + golden comparison
  - evidence: `tests/test_pipeline_stage_resume_parity.py` and snapshot diffs under `tests/golden/pipeline_refactor/`

- proof target: stage transition artifact payload parity
  - method: comparison
  - evidence: before/after JSON fixture diff equals empty for same seed inputs

- proof target: event payload parity for key lifecycle events
  - method: comparison
  - evidence: golden event stream fixture for checkpointed and full runs

- proof target: status transition semantics unchanged
  - method: table-driven unit tests
  - evidence: `tests/test_pipeline_status_registry.py`

- proof target: extraction blast radius controlled
  - method: GitNexus graph checks
  - evidence:
    - pre-edit: `gitnexus_impact({target, direction:"upstream"})`
    - pre-edit: `gitnexus_context({name: target})`
    - post-edit: `gitnexus_detect_changes({scope:"all"})`

- proof target: static/runtime safety
  - method: run
  - evidence:
    - `uvx pytest tests/`
    - `uvx mypy src --show-error-codes`

## Completion Criteria

1. all Key Deliverables satisfied with approved implementation plan mapped to this spec
2. downstream implementation artifacts reach terminal status
3. validation evidence captured and linked in plan closeout notes

Canonical source-of-truth:
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
