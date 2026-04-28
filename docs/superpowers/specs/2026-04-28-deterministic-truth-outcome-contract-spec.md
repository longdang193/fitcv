---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-outcome-contract
targets:
  - docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/01-deterministic-truth-outcome-contract.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Deterministic Truth Outcome Contract

## Summary

Define the authoritative deterministic outcome vocabulary that pipeline exports,
stage artifacts, and operator surfaces must share when describing what happened
to a job after ranking.

This spec follows the stage-authority contract and turns stage-owned meanings
into one deterministic outcome model that downstream observability and
control-plane specs can rely on.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is the second bounded detailed spec in the approved first-wave sequence
- it depends on the semantic-spine stage-authority contract
- it is stage-heavy and cross-surface because it connects runtime, exports, and
  operator views

Invariants:

- ranking fit labels remain upstream inputs, not final run outcomes
- deterministic outcomes must derive from stage-owned states, not convenience UI
  wording
- one job outcome should be reconstructable from bounded stage truth without
  hidden branching rules

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/01-deterministic-truth-outcome-contract.md`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`

Primary lens: `stage`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` should reflect the new `parent_thread`
linkage.

Plan needed: `no` until the first-wave dependent specs are drafted and approved.

## Problem

The repo already exposes several families of status:

- ranking fit labels such as `strong`, `stretch`, `skip`
- `cv_analysis` statuses such as `blocked_by_reranker_fit`,
  `ready_for_generation`, `skipped_fit_gate`, `analysis_failed`
- `cv_generation` statuses such as `accepted`, `validation_failed`,
  `generation_failed`, `persistence_failed`
- pipeline-level export labels such as `ranked_with_cv`,
  `ranked_blocked_by_reranker_fit`, `ranked_skipped_fit_gate`, and
  `ranked_no_cv`
- operator-facing display labels such as "CV created" or "Ranked, CV failed"

These are useful, but they are not yet presented as one deterministic contract.
Without that contract, later specs can treat different surfaces as if they own
the same truth.

## Goals

- Define a deterministic outcome vocabulary for job-level pipeline truth.
- Show how that outcome vocabulary derives from stage-owned statuses.
- Separate primary stage outcomes from operator-facing presentation labels.
- Make result exports, stage artifacts, and run-detail surfaces comparable.

## Non-Goals

- No change to ranking heuristics or fit thresholds.
- No redesign of event schemas yet; that belongs to the observability spec.
- No redesign of stage artifact payload shapes yet; that belongs to later
  artifact-focused specs.

## Current-State Reading

The current runtime already exposes a deterministic skeleton.

### In `src/fitcv/pipeline.py`

- ranked jobs can be exported as:
  - `ranked_with_cv`
  - `ranked_blocked_by_reranker_fit`
  - `ranked_skipped_fit_gate`
  - `ranked_no_cv`
- lower-progress outcomes also exist:
  - `not_shortlisted`
  - `shortlisted_not_scored`
  - `scored_not_ranked`
  - `rejected_after_enrichment`
  - `rejected_before_enrichment`
  - `deduplicated_before_enrichment`

### In `src/fitcv_cp/app.py`

operator-facing labels and badge classes are already derived from those export
states.

### In `src/fitcv/agentic_cv_analysis.py`

the stage-owned distinction between blocked, skipped, ready, and failed is
already explicit.

## Proposed Contract

## 1. Outcome Layers

The contract should recognize three separate but related layers.

### Layer A: stage-owned statuses

These are owned by individual stages and come from the semantic spine.

Examples:

- `skip` from ranking fit
- `blocked_by_reranker_fit` from `cv_analysis`
- `ready_for_generation` from `cv_analysis`
- `validation_failed` from `cv_generation`

### Layer B: deterministic job outcomes

These are the canonical cross-stage outcomes used to answer:

`What happened to this job in the pipeline?`

Canonical deterministic outcomes:

- `accepted`
- `held`
- `blocked`
- `rejected`
- `skipped`

### Layer C: derived presentation or export labels

These are surface-specific labels for operator reading or export grouping.

Examples:

- `ranked_with_cv`
- `ranked_blocked_by_reranker_fit`
- `CV created`

They must derive from Layer B and must not become the semantic source.

## 2. Canonical Deterministic Meanings

### `accepted`

Meaning:

- the job completed the late-stage path and produced a persisted accepted CV
  artifact

Derived from:

- `cv_generation.status == accepted`

### `held`

Meaning:

- the job remains a meaningful candidate in the workflow but is not yet a final
  accepted output because human or future-stage review is still possible

First-wave rule:

- do not overuse `held`
- reserve it for bounded future review or pause states once a later spec
  introduces them explicitly

Current practical note:

- the current runtime does not yet expose a first-class late-stage `held`
  status; the vocabulary is being reserved now so later review specs do not
  invent it inconsistently

### `blocked`

Meaning:

- upstream authority prevented the job from entering or completing the late
  writing path

Derived from examples:

- `cv_analysis.status == blocked_by_reranker_fit`
- future bounded stop states where an upstream deterministic rule prevents
  handoff

### `rejected`

Meaning:

- the job reached a stage that produced a substantive negative result rather
  than merely not continuing

Derived from examples:

- `cv_generation.status == validation_failed`
- `cv_generation.status == generation_failed`
- `cv_generation.status == persistence_failed`
- `cv_analysis.status == analysis_failed`

Rule:

- `rejected` is for terminal negative outcomes after real stage work occurred
- the subreason must still be preserved alongside the high-level outcome

### `skipped`

Meaning:

- the job did not proceed because a bounded stage decision concluded that the
  later path should not run, but this is not the same thing as an error

Derived from examples:

- `cv_analysis.status == skipped_fit_gate`
- lower-stage non-advancement states such as not shortlisted or not ranked,
  when the surface is answering a broader pipeline-progress question

## 3. Deterministic Mapping Rules

### Late-stage canonical mapping

| Stage-owned state | Deterministic outcome | Required preserved subreason |
| --- | --- | --- |
| `cv_generation.accepted` | `accepted` | `accepted` |
| `cv_generation.validation_failed` | `rejected` | `validation_failed` |
| `cv_generation.generation_failed` | `rejected` | `generation_failed` |
| `cv_generation.persistence_failed` | `rejected` | `persistence_failed` |
| `cv_analysis.blocked_by_reranker_fit` | `blocked` | `blocked_by_reranker_fit` |
| `cv_analysis.skipped_fit_gate` | `skipped` | `skipped_fit_gate` |
| `cv_analysis.analysis_failed` | `rejected` | `analysis_failed` |
| `cv_analysis.ready_for_generation` | not final by itself | `ready_for_generation` |

### Important rule

`ready_for_generation` is not a final deterministic outcome. It is a handoff
state. Surfaces may show it in stage diagnostics, but they must not treat it as
the same class of answer as accepted, blocked, rejected, or skipped.

## 4. Export And Operator-Surface Rules

### Export surfaces

Pipeline export rows may keep existing labels such as:

- `ranked_with_cv`
- `ranked_blocked_by_reranker_fit`
- `ranked_skipped_fit_gate`
- `ranked_no_cv`

But each export row should be interpretable as:

- deterministic outcome
- preserved stage-owned subreason
- optional operator label

### Operator surfaces

The control plane may continue to use human-readable labels, but:

- the label must map to one deterministic outcome
- the underlying stage-owned subreason must remain inspectable
- badge or severity styling must not hide the subreason family

## 5. Artifact Truth Requirements

The deterministic outcome contract should be visible in:

- job-level export results
- stage transition artifact summaries
- run-detail outcome badges and lists
- decision-chain explanations
- later event contracts

Required preserved fields in later implementation work:

- `deterministic_outcome`
- `stage_owned_subreason`
- `source_stage`

## Acceptance Criteria

- A reviewer can map every late-stage job result to one of:
  `accepted`, `held`, `blocked`, `rejected`, `skipped`.
- Existing runtime labels are explained as derived views rather than competing
  truths.
- `ready_for_generation` is treated as a handoff state, not a final outcome.
- Operator-facing labels remain possible without losing deterministic meaning.

## Risks

- If `held` is used prematurely without a concrete stage contract, it will
  become vague filler.
- If `ranked_no_cv` remains a catch-all with no required subreason mapping,
  observability and operator surfaces will drift.
- If analysis failures and generation failures are both flattened into generic
  "failed" language, downstream review tools will lose operational value.

## Next Artifact

After this spec, the next detailed spec in the current lane should be:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`

After that, the approved next wave is the parallel trio:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
