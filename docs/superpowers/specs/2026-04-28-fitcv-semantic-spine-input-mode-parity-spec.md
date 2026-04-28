---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
targets:
  - docs/intent/workstreams/threads/workstream-fitcv-semantic-spine/01-semantic-spine-input-mode-parity.md
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - docs/stages/shortlist.source.yaml
  - docs/stages/shortlist.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
related_features:
  - trigger_run_management
  - cv_system
  - inspection_debugging
related_stages:
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Semantic Spine Input Mode Parity

## Summary

Define the parity contract that all supported run-trigger input modes must obey
so they feed the same downstream stage meanings, artifact expectations, and
decision semantics once a run enters the pipeline.

This spec follows the stage-authority and deterministic-outcome contracts. It
keeps input-mode variety at the trigger boundary instead of letting it leak into
stage meaning.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is the third bounded detailed spec in the approved first-wave sequence
- the work is cross-stage but still part of the semantic-spine thread set
- it is downstream of stage authority because parity only makes sense once stage
  ownership is fixed

Invariants:

- input-mode differences are allowed at ingestion and trigger preparation only
- once jobs reach stage-owned runtime surfaces, downstream semantics must match
- no input mode may silently bypass ranking, fit, analysis, or generation truth
- operator surfaces should explain mode-specific provenance without redefining
  pipeline meaning

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/intent/workstreams/threads/workstream-fitcv-semantic-spine/01-semantic-spine-input-mode-parity.md`
- `src/fitcv_cp/app.py`
- `src/fitcv/pipeline.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives spec linkage from frontmatter.

Plan needed: `no` until the downstream first-wave specs are authored and
approved.

## Problem

The control plane supports multiple operator input paths and mode decisions:

- different job input sources
- different candidate-profile input sources
- execution-mode selection such as run-all versus manual staged flow
- persisted run snapshots and continue flow

That flexibility is useful, but it creates risk. If each mode carries slightly
different assumptions into the runtime, then downstream stages can begin to
mean different things depending on how the run was started.

This thread exists to prevent that drift.

## Goals

- Define what must be identical across input modes once a run starts.
- Separate trigger-time mode variance from downstream semantic truth.
- Preserve mode provenance for debugging without turning provenance into a new
  stage contract.
- Clarify how manual staged runs still obey the same semantic spine as run-all
  runs.

## Non-Goals

- No redesign of upload UX or trigger-form layout here.
- No implementation of new input modes.
- No checkpoint-payload schema redesign beyond parity requirements.

## Input Modes In Scope

This spec treats an input mode as any run-entry variation that may change how
the pipeline is started or resumed, including:

- job-input source mode
- candidate-profile source mode
- execution mode (`run_all` versus `manual_staged`)
- resume-from-checkpoint flow

The specific UI controls may evolve. The parity rules below are the stable
contract.

## Proposed Contract

## 1. Trigger-Boundary Variance Only

Input modes may differ in how the run is assembled, validated, and persisted at
trigger time.

Allowed mode-specific variance:

- file upload versus stored path selection
- how input payloads are validated before enqueue
- whether the operator chooses continuous execution or manual stage-by-stage
  continuation
- whether a run begins fresh or resumes from a checkpoint payload

Not allowed:

- changing what stage ids mean
- changing ranking fit semantics
- changing analysis readiness semantics
- changing deterministic outcome mapping
- changing the meaning of exported artifacts

## 2. Canonical Post-Trigger Normalization

Before stage execution begins, every input mode must normalize into the same
runtime envelope:

- one run id
- one persisted jobs snapshot
- one persisted effective settings snapshot
- one canonical candidate profile payload
- one declared run mode
- one canonical next-stage pointer for manual continuation when applicable

This envelope is the parity boundary. After it exists, stage behavior should
not care how the run was originally triggered.

## 3. Stage-Semantic Parity Rules

### `shortlist`

Must stay true across all input modes:

- raw retrieval and scoring-shortlist semantics are identical
- shortlist backfill still means the same thing
- mode choice does not alter shortlist transition reasons

### `ranking`

Must stay true across all input modes:

- fit labels `strong`, `stretch`, `skip` mean the same thing
- ranking outputs can be resumed into `cv_analysis` without alternate semantics
- manual staging does not create a second ranking truth

### `cv_analysis`

Must stay true across all input modes:

- `blocked_by_reranker_fit`, `ready_for_generation`, `skipped_fit_gate`, and
  `analysis_failed` mean the same thing
- resuming from checkpoint does not allow a mode-specific reinterpretation of
  ranking fit or evidence-selection meaning

### `cv_generation`

Must stay true across all input modes:

- accepted versus validation or generation or persistence failure meanings are
  identical
- a manual continue action only changes timing, not outcome semantics

## 4. Manual-Staged Parity

`manual_staged` is an execution pacing mode, not a semantic mode.

Rules:

- each checkpoint pauses after a stage-owned truth has already been created
- continue actions resume from the canonical next stage only
- operator intervention between checkpoints may change whether execution
  continues, but must not rewrite completed stage meanings
- run detail should expose that a run is staged without implying different
  outcome rules

## 5. Provenance Without Semantic Drift

Mode provenance is still valuable and should remain inspectable.

Later implementation work should preserve fields such as:

- jobs input source
- candidate profile source
- run mode
- checkpoint status
- whether a run was resumed

But those fields are secondary provenance. They must never be required to
interpret:

- fit label meaning
- stage outcome meaning
- deterministic job outcome meaning

## 6. Validation Requirements

Future implementation should reject or repair mode flows that would violate
parity, including:

- bypassing canonical run insertion before enqueue
- allowing manual continue to jump into a non-canonical stage
- accepting incomplete checkpoint payloads that cannot restore upstream truth
- letting one input path omit settings or candidate-profile state that another
  path always preserves

## 7. Operator-Surface Expectations

The control plane should make mode differences visible where useful:

- trigger summary
- run mode label
- checkpoint status
- continue actions

But operator surfaces should not encode different copies of stage truth just
because the run arrived through a different mode.

## Acceptance Criteria

- A run started through any supported input path reaches the same downstream
  semantic contracts.
- `manual_staged` and `run_all` differ in pacing only, not in stage meaning.
- Resume behavior is defined as state continuation, not semantic reconstruction.
- Provenance remains inspectable without becoming required to interpret stage
  outcomes.

## Risks

- If mode provenance and stage truth get mixed together in run detail, operator
  surfaces will become harder to reason about.
- If checkpoint payloads are allowed to be underspecified, parity will fail only
  on resumed runs.
- If one trigger path skips validation or canonical snapshot creation, later
  stage artifacts will become incomparable across runs.

## Next Artifact

After these first three specs, the next approved detailed-spec wave is:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`
