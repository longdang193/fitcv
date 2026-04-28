---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: none
map_type: implementation_execution
threads:
  - workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
  - workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
  - workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-outcome-contract
  - workstream-agentic-observability.agentic-observability-event-contract
  - workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
  - workstream-operator-control-plane.operator-control-plane-run-detail-truth
  - workstream-agentic-synonym-management.agentic-synonym-proposal-engine
  - workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
  - workstream-operator-control-plane.operator-control-plane-agentic-review-actions
specs:
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
  - docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md
  - docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md
---

# FitCV First-Wave Implementation Execution Map

## Scope

This map assumes the first-wave detailed-spec set now exists and answers the
next question:

- what should be implemented first
- what must stay sequential
- what can move in parallel safely
- how the bounded implementation plans should be split

Detailed specs in scope:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`

Main risk:

- shared-surface coordination first, sequencing second, parallelism third

Implementation target:

- begin with the smallest buildable subset that strengthens runtime truth and
  operator trust before expanding into synonym-review product surfaces

## Dependency Graph

### Hard Execution Dependencies

- `fitcv-semantic-spine-stage-authority-contract-spec`
  - must implement before any downstream surface depends on its vocabulary
  - foundational surfaces:
    - `src/fitcv/pipeline.py`
    - `src/fitcv/agentic_cv_analysis.py`
    - stage docs and generated stage contracts

- `deterministic-truth-outcome-contract-spec`
  - depends on stage-authority implementation
  - should land before:
    - event-contract implementation
    - run-detail-truth implementation
    - any shared outcome display cleanup

- `fitcv-semantic-spine-input-mode-parity-spec`
  - depends on stage-authority implementation
  - should not begin before stage and checkpoint vocabulary is stable

- `agentic-observability-event-contract-spec`
  - depends on deterministic outcome implementation
  - should coordinate with run-detail-truth implementation on event naming and
    artifact references

- `agentic-cv-quality-analysis-grounding-spec`
  - depends on:
    - stage-authority implementation
    - deterministic-outcome implementation
  - should land before later generation-repair or calibration work

- `operator-control-plane-run-detail-truth-spec`
  - depends on:
    - stage-authority implementation
    - deterministic-outcome implementation
  - should coordinate tightly with event-contract implementation

- `agentic-synonym-proposal-engine-spec`
  - depends on stable operator-truth vocabulary
  - should follow the late-stage truth work, but does not need to wait for full
    input-mode parity implementation

- `agentic-synonym-review-queue-and-operator-actions-spec`
  - depends on:
    - proposal-engine implementation
    - operator-control-plane-run-detail-truth implementation
  - should be the last first-wave implementation slice

### Coordination Dependencies

- `agentic-observability-event-contract-spec` and
  `operator-control-plane-run-detail-truth-spec`
  share event labels, stage summaries, artifact links, and operator-facing
  outcome presentation

- `fitcv-semantic-spine-input-mode-parity-spec` and
  `operator-control-plane-run-detail-truth-spec`
  both touch checkpoint, continue, and mode-specific run-detail semantics

- `agentic-cv-quality-analysis-grounding-spec` and
  `agentic-observability-event-contract-spec`
  both touch analysis summaries, reason payloads, and bounded diagnostic
  payloads

- `agentic-synonym-proposal-engine-spec` and
  `agentic-synonym-review-queue-and-operator-actions-spec`
  share proposal identity, confidence, rationale, and overlay provenance

## Execution Waves

### Wave 1 - Semantic Runtime Core

Implement first:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`

Goal:

- align stage-owned statuses, deterministic outcomes, exports, and helper
  surfaces around one late-stage truth model

Why first:

- every later first-wave spec depends on this language staying stable in code
  and operator surfaces

### Wave 2 - Operator And Observability Truth

Implement next:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`

Goal:

- make event records and operator run-detail surfaces faithful to the Wave 1
  truth model

Why before analysis grounding:

- operator and observability truth should stop drifting before deeper quality
  tuning adds more payload complexity

### Wave 3 - Input And Analysis Quality Alignment

Implement after Wave 2:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`

Goal:

- align trigger or resume behavior and analysis-quality semantics with the now
  stable runtime-truth and operator-truth surfaces

Why here:

- parity and grounding both benefit from the earlier truth cleanup
- they can then reuse the stabilized event and run-detail language

### Wave 4 - Synonym Proposal Primitive

Implement next:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`

Goal:

- create one stable review-ready proposal object on top of existing mapping
  suggestions and run-scoped overlay seams

Why standalone:

- this is the clean boundary before queue and approval UI or workflow work

### Wave 5 - Shared Review Surface

Implement last:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`

Goal:

- build the bounded operator review queue and review actions on top of the
  stable proposal object

## Parallel Lanes

### Lane A - Semantic And Outcome Core

- stage-authority contract
- then deterministic outcome contract

Why sequential:

- same shared runtime vocabulary
- least safe place for competing patches

### Lane B - Event And Operator Truth

- observability event contract
- run-detail truth

Why parallel with coordination:

- separate primary modules exist
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/app.py`
- but the naming and artifact-link surfaces must be reviewed together

### Lane C - Input And Analysis Refinement

- input-mode parity
- analysis grounding

Why parallel after Wave 2:

- both reuse stabilized truth contracts
- write surfaces are more separable than in earlier waves

### Lane D - Synonym Review Surface

- proposal engine
- then shared review queue and operator actions

Why sequential:

- review actions depend on stable proposal identity and proposal-state fields

## First Buildable Subset

The first buildable subset should be:

- `fitcv-semantic-spine-stage-authority-contract-spec`
- `deterministic-truth-outcome-contract-spec`
- `agentic-observability-event-contract-spec`
- `operator-control-plane-run-detail-truth-spec`

Why this subset first:

- it creates the strongest trust foundation with the smallest conceptual blast
  radius
- it improves runtime truth, event truth, and operator truth before broader
  feature expansion
- it reduces the risk that later synonym or analysis work will build on drifting
  status language

This subset should be the first target for bounded implementation plans.

## Shared-Surface Risks

### `src/fitcv/pipeline.py`

Touched by:

- stage authority
- deterministic outcome mapping
- event contract
- analysis grounding
- proposal-engine evidence sourcing

Risk:

- too many simultaneous edits to status helpers, exports, stage artifacts, and
  late-stage summaries

Coordination rule:

- isolate Wave 1 runtime truth cleanup first
- do not mix synonym proposal persistence into the same implementation plan as
  semantic or outcome cleanup

### `src/fitcv_cp/app.py`

Touched by:

- run-detail truth
- input-mode parity
- proposal engine inspection surfaces
- review queue and operator actions

Risk:

- control-plane truth and new review UX can blur together and become one large
  patch

Coordination rule:

- finish truth cleanup before adding new queue or approval UI behavior

### Run-Scoped Overlay And Mapping Suggestion Surfaces

Touched by:

- proposal engine
- shared review queue

Risk:

- raw mapping-suggestion payloads get treated as final review objects

Coordination rule:

- implement proposal-object persistence before queue actions

## Recommended Plan Breakdown

Create bounded implementation plans in this order:

1. one combined plan for:
   - `fitcv-semantic-spine-stage-authority-contract-spec`
   - `deterministic-truth-outcome-contract-spec`

2. one combined plan for:
   - `agentic-observability-event-contract-spec`
   - `operator-control-plane-run-detail-truth-spec`

3. one combined plan for:
   - `fitcv-semantic-spine-input-mode-parity-spec`
   - `agentic-cv-quality-analysis-grounding-spec`

4. one plan for:
   - `agentic-synonym-proposal-engine-spec`

5. one plan for:
   - `agentic-synonym-review-queue-and-operator-actions-spec`

Reasoning:

- Waves 1 and 2 each share enough surfaces that splitting them into separate
  micro-plans would mostly add coordination overhead
- Wave 3 is coherent as one follow-on stabilization lane
- Waves 4 and 5 should stay separate so the review queue never outruns the
  proposal object

## Orchestration Notes

- this is an implementation execution map, not yet an implementation plan
- do not start the synonym review queue before the proposal object exists in
  code
- do not let input-mode parity work reopen settled stage-authority vocabulary
- the immediate next artifact should be the first bounded implementation plan
  for the first buildable subset
