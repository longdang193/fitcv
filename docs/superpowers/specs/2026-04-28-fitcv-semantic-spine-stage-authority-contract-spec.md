---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
targets:
  - docs/intent/workstreams/threads/workstream-fitcv-semantic-spine/02-semantic-spine-stage-authority-contract.md
  - docs/stages/shortlist.source.yaml
  - docs/stages/shortlist.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Semantic Spine Stage Authority Contract

## Summary

Define the stage-owned meanings that downstream specs must treat as fixed:
which stage is authoritative for shortlist transitions, ranking fit labels,
analysis readiness, fit-gate decisions, generation outcomes, and resume-ready
checkpoint payloads.

This spec is the semantic root for the first detailed-spec wave. It does not
change runtime behavior yet. It freezes vocabulary, ownership, and handoff
boundaries so later specs do not restate the same meanings differently.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- the upstream thread set, complete spec set, and spec-authoring map already
  exist
- this artifact is one bounded detailed spec inside that approved authoring
  sequence
- the work is stage-heavy because it governs stage authority and handoff truth

Invariants:

- stage meaning stays sourced from `docs/stages/*.source.yaml`
- generated stage contracts remain derived views, not the semantic source
- ranking owns authoritative post-filter fit labels
- `cv_analysis` owns readiness versus blocked or skipped analysis outcomes
- `cv_generation` owns accepted, validation-failed, generation-failed, and
  persistence-failed final writing outcomes

Dependencies:

- `docs/intent/workstreams/threads/workstream-fitcv-semantic-spine/02-semantic-spine-stage-authority-contract.md`
- `docs/stages/shortlist.source.yaml`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/stages/cv_generation.source.yaml`
- `src/fitcv/pipeline.py`

Primary lens: `stage`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec linkage from
`parent_thread`.

Plan needed: `no` until the dependent first-wave specs are drafted and approved.

## Problem

The current runtime already contains the raw ingredients of a stage-owned
contract:

- `shortlist` owns raw-hit versus backfill transitions
- `ranking` owns the final post-filter fit label
- `cv_analysis` can block on reranker fit, skip after the fit gate, fail
  analysis, or mark a job ready for generation
- `cv_generation` can accept, fail validation, fail generation, or fail
  persistence

But those meanings are still spread across stage docs, pipeline exports,
decision-chain helpers, status constants, and control-plane labels. That makes
later design work fragile. A downstream spec can easily treat "fit", "skip",
"blocked", "ready", "accepted", or "failed" as if they were interchangeable
surface labels instead of stage-owned decisions.

## Goals

- Freeze which stage owns which decision and label family.
- Define the canonical handoff contract from one stage to the next.
- Establish the vocabulary later specs must reuse verbatim.
- Make checkpoint and continue semantics subordinate to stage authority rather
  than a parallel lifecycle language.

## Non-Goals

- No runtime implementation change in this spec.
- No redesign of ranking heuristics, evidence retrieval, or generation logic.
- No UI copy rewrite beyond what is necessary to respect stage-owned truth in
  later specs.

## Current-State Reading

### `shortlist`

`docs/stages/shortlist.source.yaml` and `src/fitcv/pipeline.py` already treat
`shortlist` as the owner of:

- raw retrieval output
- the scoring shortlist
- shortlist transition reasons such as returned-by-vector-search versus
  backfilled-for-scoring
- shortlist backfill-rate quality metrics

### `ranking`

`docs/stages/ranking.source.yaml` and `src/fitcv/pipeline.py` already treat
`ranking` as the owner of:

- final scored ranking inputs
- authoritative post-filter fit labels: `strong`, `stretch`, `skip`
- ranking quality metrics and reuse metrics
- ranked jobs that may proceed to `cv_analysis`
- checkpoint payloads that can resume from ranked jobs

### `cv_analysis`

`docs/stages/cv_analysis.source.yaml`, `src/fitcv/pipeline.py`, and
`src/fitcv/agentic_cv_analysis.py` already expose four materially different
analysis outcomes:

- `blocked_by_reranker_fit`
- `ready_for_generation`
- `skipped_fit_gate`
- `analysis_failed`

Those outcomes are not just logging detail. They are stage-owned truth about
whether `cv_generation` should run at all.

### `cv_generation`

`docs/stages/cv_generation.source.yaml` and `src/fitcv/pipeline.py` already
treat `cv_generation` as the owner of:

- accepted CV outputs
- validation failures
- generation failures
- persistence failures
- final persisted CV artifacts

## Proposed Contract

## 1. Stage-Owned Semantic Authority

The semantic spine should adopt these ownership rules.

### `shortlist` owns retrieval transition truth

Canonical questions answered here:

- was the job returned by raw vector retrieval?
- was it backfilled into the scoring shortlist?
- did it enter scoring through retrieval or through bounded backfill repair?

Downstream stages may consume shortlist transition facts, but must not
reclassify them.

### `ranking` owns post-filter fit truth

Canonical questions answered here:

- what is the authoritative final fit label for the ranked job?
- was the label derived from an explicit reranker label or threshold fallback?
- did the job reach the ranked set or only the scored set?

Downstream stages may consume ranking fit, but must not replace it with a new
primary fit source.

### `cv_analysis` owns generation-readiness truth

Canonical questions answered here:

- is the ranked job blocked before analysis because reranker fit is `skip`?
- did analysis complete and mark the job `ready_for_generation`?
- did the fit gate skip the job after analysis work?
- did analysis fail before a valid handoff to generation?

This stage owns the final answer to "should generation run?".

### `cv_generation` owns final writing truth

Canonical questions answered here:

- was a CV accepted?
- did validation reject it?
- did generation fail before a candidate output existed?
- did persistence fail after a candidate output existed?

No earlier stage may claim accepted or rejected CV truth.

## 2. Canonical Handoff Boundaries

The semantic spine should use the following stage handoff model.

### `shortlist -> ranking`

Handoff object:

- shortlist membership
- shortlist origin and transition reasons
- retrieval provenance needed for scoring explanation

Must stay true:

- ranking receives retrieval-aware scoring candidates
- ranking does not reinterpret raw retrieval itself

### `ranking -> cv_analysis`

Handoff object:

- ranked job row
- authoritative fit label
- fit-label provenance
- ranking explanations and bounded ranking artifacts
- checkpoint-resumable ranked-job state

Must stay true:

- `cv_analysis` treats ranking fit as upstream authority
- `cv_analysis` may block or skip later, but does not back-edit ranking truth

### `cv_analysis -> cv_generation`

Handoff object:

- only records marked `ready_for_generation`
- selected evidence payload
- evidence selection summary
- gap summary
- analysis input fingerprint and reuse status

Must stay true:

- generation-ready records are the only valid input class for `cv_generation`
- skipped or failed analysis records never become generation inputs by naming
  convention alone

## 3. Canonical Vocabulary

These names should be treated as contract terms, not informal copy.

### Ranking fit labels

- `strong`
- `stretch`
- `skip`

Owner: `ranking`

### Analysis stage statuses

- `blocked_by_reranker_fit`
- `ready_for_generation`
- `skipped_fit_gate`
- `analysis_failed`

Owner: `cv_analysis`

### Generation stage statuses

- `accepted`
- `validation_failed`
- `generation_failed`
- `persistence_failed`

Owner: `cv_generation`

### Pipeline-facing aggregate outcomes

Pipeline surfaces may present aggregate labels such as:

- `ranked_with_cv`
- `ranked_blocked_by_reranker_fit`
- `ranked_skipped_fit_gate`
- `ranked_no_cv`

But those are derived views. They must be traceable back to one stage-owned
decision family above.

## 4. Checkpoint And Continue Semantics

Checkpoint and continue is not a parallel execution model with its own truth.
It is a transport mechanism for stage-owned state.

Rules:

- checkpoint payloads may only preserve already-owned upstream stage outputs
- resume targets must be stage ids from the canonical pipeline stage sequence
- no checkpoint may reclassify a stage outcome while carrying it forward
- resumed `cv_analysis` must start from ranked-job truth, not from a
  reconstructed pseudo-stage

## 5. Documentation And Artifact Alignment

The following surfaces should converge on the same stage-owned language in later
implementation work:

- `docs/stages/*.source.yaml`
- generated `docs/stages/*.yaml`
- `src/fitcv/pipeline.py`
- `src/fitcv/agentic_cv_analysis.py`
- control-plane run detail and export surfaces
- stage transition artifact summaries
- decision-chain explanations

## Acceptance Criteria

- A reviewer can answer which stage owns each late-stage decision without
  reading code.
- The distinction between ranking fit, analysis readiness, and generation
  outcome is explicit and non-overlapping.
- Checkpoint and continue semantics are defined as stage-state transport rather
  than a separate meaning system.
- Later detailed specs can quote this vocabulary without redefining it.

## Risks

- If later specs reword these statuses casually, the semantic spine will drift
  before implementation begins.
- If UI-facing labels become the primary contract, stage ownership will blur
  again.
- If checkpoint payloads start carrying reinterpreted or partially recomputed
  state, manual resume behavior will stop matching the stage model.

## Next Artifact

After this spec, the next detailed spec should be:

- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`

Then:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
