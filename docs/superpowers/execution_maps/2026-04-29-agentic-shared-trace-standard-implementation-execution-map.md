---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: none
map_type: implementation_execution
threads:
  - workstream-agentic-observability.agentic-observability-shared-trace-standard
  - workstream-agentic-observability.agentic-observability-provider-provenance
  - workstream-agentic-observability.agentic-observability-synonym-proposal-trace
  - workstream-agentic-observability.agentic-observability-operator-surface
  - workstream-agentic-observability.agentic-observability-event-contract
specs:
  - docs/superpowers/specs/2026-04-29-agentic-shared-trace-standard-spec.md
  - docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md
---
# Agentic Shared Trace Standard Implementation Execution Map

## Scope

This map assumes the shared trace standard spec now exists and answers the next
question:

- how should adoption be sequenced
- what must stay sequential
- what can move in parallel safely
- how should bounded implementation plans be split

Implementation scope:

- normalize the existing `cv_generation` trace into the shared standard where
  needed
- add an agentic `cv_analysis` trace surface
- add a synonym or proposal-generation trace surface
- align bundle-manifest, export, and observability docs across those trace
  families

Main risk:

- shared artifact vocabulary is easy to drift if multiple trace families change
  independently

Implementation target:

- use the current `agentic-live-trace.json` work as the first reference slice,
  then extend the shared contract outward without reopening settled runtime
  truth unnecessarily

## Dependency Graph

### Hard Execution Dependencies

- `2026-04-29-agentic-shared-trace-standard-spec`
  - defines the cross-step contract vocabulary
  - must guide every downstream implementation wave

- `2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec`
  - already establishes the first persisted trace surface
  - should be normalized before new trace families copy any older naming drift

- `2026-04-28-agentic-observability-event-contract-spec`
  - should remain the upstream source for bounded event semantics
  - must stay aligned with trace status, scope, and stage-owned outcome wording

- `2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec`
  - already defines run-level artifact applicability and degraded-state
    vocabulary
  - should guide synonym trace adoption and manifest state language

### Coordination Dependencies

- `cv_generation` trace normalization and `cv_analysis` trace introduction
  share:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`

- `cv_analysis` trace and synonym trace adoption both depend on stable:
  - trace top-level vocabulary
  - manifest artifact-state rules
  - run export presentation

- synonym trace adoption and observability doc refresh share:
  - artifact naming
  - operator debugging guidance
  - degraded versus not-applicable explanations

## Execution Waves

### Wave 1 - Shared Standard Alignment For Existing Trace

Implement first:

- align the existing `cv_generation` trace payload and manifest semantics with
  the shared standard where they still differ

Goal:

- establish one clean reference implementation before more trace families are
  added

Why first:

- every later wave will copy this shape in some form
- it is cheaper to normalize one trace now than to reconcile three later

Primary surfaces:

- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `tests/test_pipeline_agentic_late_stage.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_app.py`

### Wave 2 - Agentic CV Analysis Trace

Implement next:

- add a persisted agentic `cv_analysis` trace surface that follows the shared
  standard

Goal:

- make the analysis step observable with the same provenance, attempt,
  validation, and degradation vocabulary already used in generation

Why second:

- `cv_analysis` is the next highest-value agentic debugging surface
- it shares runtime and stage-owned truth closely with generation, so it
  benefits from the reference implementation being settled first

Primary surfaces:

- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `docs/observability.md`

### Wave 3 - Synonym Or Proposal Trace

Implement after Wave 2:

- add a synonym or proposal-generation trace surface that follows the shared
  standard

Goal:

- bring proposal-generation observability into the same persisted artifact
  family instead of relying on partial persistence hints or bundle-only
  inference

Why here:

- this wave depends more on stable manifest applicability semantics than on the
  specific generation runtime shape
- it should not race ahead before the shared operator vocabulary is stable

Primary surfaces:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py` when durable persistence coordination is needed
- proposal-related tests and run-artifact tests

### Wave 4 - Shared Operator Surface And Docs Polish

Implement last:

- unify docs and operator wording across all trace families
- make sure run exports and bundle manifest presentation remain consistent

Goal:

- ensure the operator experience feels like one coherent observability system
  rather than three separate debugging features

Why last:

- final wording and navigation are easiest to settle after the trace families
  exist

Primary surfaces:

- `docs/observability.md`
- `docs/api.md` if endpoint inventory needs trace downloads added
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html` only if export naming or grouping
  needs refinement

## Parallel Lanes

### Lane A - Runtime Trace Capture

- Wave 1 alignment
- Wave 2 `cv_analysis` capture

Why partially sequential:

- shared runtime helpers and payload builders should stabilize in one place
  before they are reused

### Lane B - Control-Plane Persistence And Export

- worker snapshot persistence
- app download routes
- bundle manifest state handling

Why parallel with coordination:

- app and worker files are separable enough for bounded parallel work
- but manifest semantics must be reviewed together

### Lane C - Proposal Trace Adoption

- synonym or proposal trace capture
- degraded persistence coordination

Why later and mostly standalone:

- this lane has the least overlap with `cv_analysis` internals
- it mainly shares artifact contract and operator vocabulary

### Lane D - Docs And Operator Guidance

- observability docs
- endpoint docs
- export naming polish

Why last:

- documentation should describe the final adopted trace family set, not a
  moving target

## First Buildable Subset

The first buildable subset should be:

- Wave 1 shared-standard alignment for the existing `cv_generation` trace

Why this subset first:

- it turns current working code into the reference contract
- it reduces naming and shape drift before adding more implementations
- it keeps the first follow-up plan small and easy to verify

This subset should be the first target for a bounded implementation plan.

## Shared-Surface Risks

### `src/fitcv/pipeline.py`

Touched by:

- existing generation trace summary
- future analysis trace summary
- proposal trace summary
- run-level artifact aggregation

Risk:

- too many trace families can turn pipeline summary assembly into a generic but
  fragile abstraction too early

Coordination rule:

- prefer one small shared helper per trace contract family over a giant
  universal builder in the first adoption waves

### `src/fitcv_cp/app.py`

Touched by:

- new download endpoints
- export list construction
- manifest artifact states
- operator run-detail presentation

Risk:

- artifact-state logic can fork by trace family if each route is added ad hoc

Coordination rule:

- centralize applicability and artifact-state handling where possible before
  adding the third trace family

### `docs/observability.md`

Touched by:

- current live trace docs
- future analysis trace docs
- future synonym trace docs

Risk:

- doc guidance can become a patchwork of one-off debugging instructions

Coordination rule:

- keep one shared "agentic traces" section with per-trace specifics nested
  under the same operator workflow

## Recommended Plan Breakdown

Create bounded implementation plans in this order:

1. one plan for:
   - Wave 1 shared-standard alignment for `cv_generation`

2. one plan for:
   - Wave 2 `cv_analysis` trace adoption

3. one plan for:
   - Wave 3 synonym or proposal trace adoption

4. one plan for:
   - Wave 4 operator-surface and docs polish

Reasoning:

- Wave 1 is the reference-contract cleanup and should stay narrowly scoped
- Wave 2 has enough shared runtime and control-plane surfaces to be coherent as
  one plan
- Wave 3 should stay separate because proposal persistence and degraded storage
  semantics are their own risk lane
- Wave 4 is lightweight polish and should not bloat earlier runtime plans

## Orchestration Notes

- this is an implementation execution map, not yet an implementation plan
- do not expand the shared standard into a universal abstraction before two
  trace families are actually implemented
- keep artifact naming consistent even if filenames remain step-specific
- treat the current `agentic-live-trace.json` as the reference slice, not a
  permanent exception
- the immediate next artifact should be the bounded Wave 1 implementation plan
