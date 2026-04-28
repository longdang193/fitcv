---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: none
map_type: spec_authoring
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
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md
  - docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md
  - docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md
---

# FitCV First-Wave Spec-Authoring Map

## Scope

This map assumes the complete spec set is already known from:

- `docs/superpowers/specs/2026-04-28-fitcv-product-thread-set-complete-spec-set-spec.md`

and answers the next question:

- which detailed specs should be authored first
- which spec-authoring tasks depend on others
- what can be authored in parallel safely
- where shared-surface design risks make parallel authoring unsafe

Workstream or branch in scope:

- cross-workstream first-wave FitCV product spine

Threads in scope:

- `workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract`
- `workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity`
- `workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-outcome-contract`
- `workstream-agentic-observability.agentic-observability-event-contract`
- `workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding`
- `workstream-operator-control-plane.operator-control-plane-run-detail-truth`
- `workstream-agentic-synonym-management.agentic-synonym-proposal-engine`
- `workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval`
- `workstream-operator-control-plane.operator-control-plane-agentic-review-actions`

Main risk:

- shared-surface design conflicts first, authoring sequencing second,
  authoring parallelism third

## Dependency Graph

### Hard Authoring Dependencies

- `fitcv-semantic-spine-stage-authority-contract-spec`
  - no in-scope detailed-spec prerequisite
  - this is the root semantic glossary for the authoring wave

- `deterministic-truth-outcome-contract-spec`
  - depends on `fitcv-semantic-spine-stage-authority-contract-spec`

- `fitcv-semantic-spine-input-mode-parity-spec`
  - depends on stage-authority terminology being stable enough to reuse

- `agentic-observability-event-contract-spec`
  - depends on `deterministic-truth-outcome-contract-spec`

- `agentic-cv-quality-analysis-grounding-spec`
  - depends on:
    - `fitcv-semantic-spine-stage-authority-contract-spec`
    - `deterministic-truth-outcome-contract-spec`

- `operator-control-plane-run-detail-truth-spec`
  - depends on:
    - `fitcv-semantic-spine-stage-authority-contract-spec`
    - `deterministic-truth-outcome-contract-spec`

- `agentic-synonym-proposal-engine-spec`
  - no first-wave detailed-spec prerequisite
  - but should be authored after the core semantic and outcome vocabulary are
    stable enough to avoid proposal-state naming drift

- `agentic-synonym-review-queue-and-operator-actions-spec`
  - depends on:
    - `agentic-synonym-proposal-engine-spec`
    - stable operator truth vocabulary from
      `operator-control-plane-run-detail-truth-spec`

### Coordination Dependencies

- `agentic-observability-event-contract-spec`,
  `agentic-cv-quality-analysis-grounding-spec`, and
  `operator-control-plane-run-detail-truth-spec`
  all consume the same stage-owned outcome vocabulary and should not author
  conflicting names for outcomes, artifacts, or fallback states

- `fitcv-semantic-spine-input-mode-parity-spec` and
  `fitcv-semantic-spine-stage-authority-contract-spec`
  both touch pipeline meaning and should share one semantic glossary checkpoint

- `agentic-synonym-proposal-engine-spec` and
  `agentic-synonym-review-queue-and-operator-actions-spec`
  must share one proposal-object vocabulary instead of inventing separate
  schemas

## Authoring Waves

### Wave 1 — Semantic Foundation

Author first:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`

Goal:

- freeze stage-owned meaning, handoff language, and reranker-fit authority
  before any dependent detailed spec authors around it

### Wave 2 — Core Contract Pair

Author next:

- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`

Goal:

- lock the accepted/held/blocked/rejected vocabulary
- align trigger/input semantics to the now-stable stage model

### Wave 3 — Parallel Downstream Detailed Specs

Author in parallel once Wave 2 is stable:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`

Goal:

- let observability, late-stage analysis quality, and operator truth advance
  together while consuming the same upstream terminology

### Wave 4 — Synonym Proposal Primitive

Author after Wave 3:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`

Goal:

- define the proposal object, confidence, rationale, and review-ready payload
  before any queue or approval surface is authored around it

### Wave 5 — Shared Review Surface

Author after Wave 4:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`

Goal:

- define one bounded operator review surface on top of a stable proposal object

## Safe Parallel Authoring Lanes

### Lane A — Semantic Core

- `fitcv-semantic-spine-stage-authority-contract-spec`
- then `fitcv-semantic-spine-input-mode-parity-spec`

Why safe:

- same semantic family
- lowest ambiguity when one author or tightly coordinated pair owns the shared
  glossary

### Lane B — Outcome Contract

- `deterministic-truth-outcome-contract-spec`

Why safe:

- narrow contract surface
- clean dependency bridge for later detailed-spec authors

### Lane C — Event Contract

- `agentic-observability-event-contract-spec`

Why safe:

- can move independently after the outcome contract if it treats stage and
  outcome terminology as fixed upstream inputs

### Lane D — Analysis Grounding

- `agentic-cv-quality-analysis-grounding-spec`

Why safe:

- can move after semantic and outcome contracts if it avoids redefining final
  gate meaning

### Lane E — Operator Truth Surface

- `operator-control-plane-run-detail-truth-spec`

Why safe:

- can move after stage and outcome freeze
- should coordinate with Lane C on surfaced event and artifact naming

### Lane F — Synonym Design Surface

- `agentic-synonym-proposal-engine-spec`
- then `agentic-synonym-review-queue-and-operator-actions-spec`

Why sequential inside the lane:

- the review surface depends on the proposal object

## Shared-Surface Design Risks

### `src/fitcv/pipeline.py` And `docs/stages/*`

Touched by:

- stage authority
- input-mode parity
- analysis grounding

Risk:

- three detailed specs may encode slightly different stage boundary language

Coordination rule:

- freeze the stage glossary in Wave 1 and quote it consistently in later specs

### Results Artifacts, Status Labels, And Run Detail Surfaces

Touched by:

- deterministic outcome contract
- observability event contract
- operator run-detail truth

Risk:

- event names, UI labels, and results-ledger terms diverge before any code
  changes even begin

Coordination rule:

- treat the deterministic outcome spec as the single upstream naming source

### Late-Stage Analysis Artifacts

Touched by:

- analysis grounding
- event contract

Risk:

- event snapshots and analysis artifacts duplicate or contradict each other in
  design

Coordination rule:

- event contract should point at analysis artifacts rather than redefining the
  same payload

### Synonym Proposal Objects And Review Actions

Touched by:

- proposal engine
- shared review queue and operator actions

Risk:

- review actions get designed against a placeholder or unstable proposal object

Coordination rule:

- no shared review detailed spec until the proposal-engine detailed spec is
  complete enough to anchor the object schema

## Recommended Next Detailed-Spec Sequence

Author next in this exact sequence:

1. `2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
2. `2026-04-28-deterministic-truth-outcome-contract-spec.md`
3. `2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
4. parallel:
   - `2026-04-28-agentic-observability-event-contract-spec.md`
   - `2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
   - `2026-04-28-operator-control-plane-run-detail-truth-spec.md`
5. `2026-04-28-agentic-synonym-proposal-engine-spec.md`
6. `2026-04-28-agentic-synonym-review-queue-and-operator-actions-spec.md`

## Orchestration Notes

- this is a spec-authoring map, not yet an implementation execution map
- do not write bounded implementation plans for later-wave work before the
  detailed specs above exist and are approved
- after the detailed specs in this map are approved, the next orchestration
  artifact should be an implementation execution map for the subset that is
  ready to implement
