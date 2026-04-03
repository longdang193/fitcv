---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Split the current final CV stage into sequential `cv_analysis` and `cv_generation` stages with separate stage contracts and separate runtime artifacts."
invariants:
  - "Ranking remains the sole owner of the authoritative post-filter fit label before Layer 4 begins."
  - "`cv_analysis` must not generate or persist final CV artifacts."
  - "`cv_generation` must consume `cv_analysis` outputs rather than recomputing evidence, gap, or fit-gate analysis by default."
  - "Both `cv_analysis` and `cv_generation` must emit their own bounded stage-transition artifact blocks."
  - "In staged/manual mode, `cv_analysis` and `cv_generation` become separate resumable checkpoints."
---

# CV Analysis and Generation Split Spec

## Affected Feature Contracts

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/features/trigger_run_management/trigger_run_management.yaml)

## Stage Contracts

- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/ranking.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/CV-generation/docs/stages/cv_generation.yaml)
- new: `docs/stages/cv_analysis.yaml`

## Triage

Feature type: MODIFY  
Summary: Split the current final CV stage into `cv_analysis` and `cv_generation` so evidence/gap/fit preparation is separated from actual CV writing and validation.  
Reasoning: This is a change to an existing managed feature and existing stage lifecycle, not a new standalone feature family. The work is stage-heavy because it changes the pipeline boundary model, manual checkpoints, and stage-transition artifacts.  
Invariants:
- Ranking remains the authoritative owner of post-filter fit labels and ranked job selection.
- `cv_analysis` is an analysis/preparation stage only; it must not persist accepted CV versions.
- `cv_generation` should operate from an explicit analysis payload instead of silently redoing upstream analysis.
- Manual staged runs must be able to pause after `cv_analysis` and continue into `cv_generation`.
- Stage-local debugging must improve, not regress, from the split.
Dependencies:
- `cv_system`
- `inspection_debugging`
- `trigger_run_management`
- existing stage-transition artifact system
- existing CV-generation debug snapshot system
Affected stages:
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `inspection_debugging`
- `trigger_run_management`
Primary lens: stage
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/inspection_debugging/history.md`
    - `docs/features/trigger_run_management/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
  stage_contracts:
    - `docs/stages/ranking.yaml`
    - `docs/stages/cv_analysis.yaml`
    - `docs/stages/cv_generation.yaml`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Problem

The current `cv_generation` stage owns two different responsibilities:

1. prepare the job-specific generation context
2. generate, validate, and persist the final CV artifacts

Today that single stage does all of the following in one runtime block:

- merge ranked rows with enriched job context
- retrieve candidate evidence
- compute gap analysis
- resolve the Layer 4 fit gate
- generate the CV
- validate the CV
- retry missing-section repair
- persist accepted versions
- emit debug records

That bundling causes three problems:

1. failures are harder to localize
- an operator cannot quickly tell whether a run failed in analysis or in generation

2. reruns are too coarse
- generation cannot be retried independently from evidence and fit preparation

3. stage artifacts are less clear than they should be
- the current `cv_generation` artifact mixes preparation and writing concerns into one block

## Design Goal

Split the final pipeline stage into two sequential stages:

1. `cv_analysis`
2. `cv_generation`

The split should make the lifecycle clearer:

- `ranking` decides which jobs are eligible to enter Layer 4
- `cv_analysis` decides what grounded inputs should be used for those jobs and whether each job should proceed to writing
- `cv_generation` writes, validates, repairs, and persists final CV artifacts for jobs that analysis allowed to proceed

## New Stage Order

The stage order becomes:

1. `normalize`
2. `enrich`
3. `rule_filter`
4. `shortlist`
5. `ranking`
6. `cv_analysis`
7. `cv_generation`

Manual staged mode must pause/resume at both new Layer 4 boundaries:

- pause after `cv_analysis`
- continue into `cv_generation`

`cv_generation` must execute only after `cv_analysis` completes successfully.

## Stage Responsibilities

## `cv_analysis`

`cv_analysis` becomes the preparation and gating stage for Layer 4.

It owns:

- merging ranked rows with enriched job context
- retrieving candidate evidence
- computing gap analysis
- resolving the Layer 4 fit gate for each ranked job
- building a generation-ready payload for jobs that should proceed
- recording analysis outcomes for jobs that should not proceed

It does not own:

- writing final CV markdown
- validating generated CVs
- repair retries
- persisting accepted/rejected CV versions

### `cv_analysis` inputs

- ranked jobs from `ranking`
- enriched job context
- candidate profile
- evidence retrieval settings
- gap-analysis settings
- Layer 4 fit-gate policy

### `cv_analysis` outputs

- `analysis_records`
- `generation_ready_jobs`
- `analysis_skipped_jobs`
- bounded `stage_transition_artifacts.cv_analysis`
- resumable checkpoint payload for `cv_generation`

### Recommended `analysis_record` shape

Each ranked job should produce one compact analysis record:

```json
{
  "job_url": "...",
  "ranking_fit_label": "stretch",
  "analysis_status": "ready_for_generation",
  "fit_gate_label": "stretch",
  "evidence_used": [...],
  "gap_summary": {...},
  "job_context": {...},
  "generation_input": {...}
}
```

For jobs blocked at the fit gate:

```json
{
  "job_url": "...",
  "ranking_fit_label": "skip",
  "analysis_status": "skipped_fit_gate",
  "fit_gate_label": "skip",
  "evidence_used": [...],
  "gap_summary": {...},
  "job_context": {...},
  "generation_input": null
}
```

## `cv_generation`

`cv_generation` becomes the writing, validation, repair, and persistence stage.

It owns:

- generating the structured CV / markdown output from `generation_input`
- running validation
- retrying repair when allowed
- persisting accepted CV versions
- emitting final generation debug records

It does not own:

- evidence retrieval
- gap analysis
- initial fit-gate resolution
- re-merging ranked and enriched rows by default

### `cv_generation` inputs

- `generation_ready_jobs` from `cv_analysis`
- CV generation and validation settings

### `cv_generation` outputs

- accepted CV artifacts
- validation and repair outcomes
- final generation status records
- bounded `stage_transition_artifacts.cv_generation`
- existing run-scoped CV debug snapshot, updated to reflect the new two-stage ownership

## Sequential Execution Rule

The runtime must enforce:

- `cv_analysis` always runs before `cv_generation`
- `cv_generation` consumes `cv_analysis` outputs

In continuous `run_all` mode:

- `cv_analysis` runs immediately after `ranking`
- then `cv_generation` runs immediately after `cv_analysis`

In `manual_staged` mode:

- the run may pause after `cv_analysis`
- when resumed, `cv_generation` must use the persisted `cv_analysis` checkpoint payload instead of recomputing analysis by default

## Artifact Requirements

Both new stages must have their own artifact block.

## `cv_analysis` artifact

`stage_transition_artifacts.cv_analysis` should include:

- input count: ranked jobs
- output counts:
  - `analysis_records`
  - `ready_for_generation`
  - `skipped_fit_gate`
- decision summary:
  - fit-gate label counts
  - evidence retrieval settings summary
  - gap-analysis mode summary if useful
- inputs sample:
  - ranked rows entering analysis
- outputs sample:
  - compact ready-for-generation analysis rows
- dropped or changed sample:
  - jobs skipped at fit gate

This artifact should make it possible to answer:

- what evidence was chosen?
- what gap picture was derived?
- which jobs were allowed into CV writing?
- which jobs were stopped before writing?

## `cv_generation` artifact

`stage_transition_artifacts.cv_generation` should become generation-only.

It should include:

- input count: `generation_ready_jobs`
- output counts:
  - `accepted`
  - `validation_failed`
  - `generation_failed`
  - `persistence_failed`
- decision summary:
  - generation model
  - prompt version
  - validation/repair counts
- inputs sample:
  - generation-ready rows from `cv_analysis`
- outputs sample:
  - accepted generation records
- dropped or changed sample:
  - validation/generation/persistence failures

This artifact should not be the primary place to inspect evidence retrieval or initial fit-gate decisions anymore; those belong to `cv_analysis`.

## Checkpoint and Resume Contract

The checkpoint payload boundary changes:

- `ranking` pauses with `next_stage = cv_analysis`
- `cv_analysis` pauses with `next_stage = cv_generation`

The `cv_analysis` checkpoint payload should contain:

- `analysis_records`
- `generation_ready_jobs`
- any bounded context needed by `cv_generation`

The `cv_generation` stage should not require recomputing:

- evidence retrieval
- gap analysis
- fit-gate results

except as an explicit future fallback path, not the default path.

## Inspection and Debugging Changes

Run inspection should improve in two ways:

1. stage artifacts now separate:
- analysis failures / skips
- generation/validation failures

2. CV debug records should preserve the distinction between:
- `analysis_status`
- `generation_status`

Recommended direction:

- keep the existing run-scoped CV debug snapshot surface
- but evolve its record shape so it reflects the two-stage lifecycle

Example:

```json
{
  "job_url": "...",
  "analysis": {
    "status": "ready_for_generation",
    "fit_gate_label": "stretch",
    "evidence_used": [...],
    "gap_summary": {...}
  },
  "generation": {
    "status": "accepted",
    "validation_status": "passed"
  }
}
```

## Stage Boundary Ownership After the Split

- `ranking`
  - owns ranked selection and authoritative ranking fit labels

- `cv_analysis`
  - owns Layer 4 evidence preparation and fit-gate transition into writing

- `cv_generation`
  - owns CV writing, validation, repair, and persistence

This avoids the current ambiguity where `cv_generation` both decides what to generate from and also generates it.

## Backward Compatibility

The rollout should preserve:

- existing run results export
- existing CV debug JSON download
- existing accepted CV persistence model

Compatibility may temporarily allow the export surface to flatten both analysis and generation detail into the old row shape, but the internal stage ownership should still follow the new split.

## Acceptance Criteria

1. The pipeline stage sequence includes both `cv_analysis` and `cv_generation`.
2. `cv_analysis` always runs before `cv_generation`.
3. `cv_analysis` and `cv_generation` each emit their own bounded artifact block.
4. `cv_analysis` artifacts make evidence, gap, and fit-gate decisions inspectable before writing begins.
5. `cv_generation` artifacts focus on writing, validation, repair, and persistence outcomes only.
6. Manual staged runs can pause after `cv_analysis` and resume into `cv_generation`.
7. `cv_generation` can resume from persisted `cv_analysis` outputs without recomputing analysis by default.
8. Existing CV debug/export surfaces remain supported during rollout.

## Recommended Next Step

Draft an implementation plan that:

1. adds the new `cv_analysis` stage contract and updates the stage sequence
2. defines the persisted `analysis_record` and `generation_ready_job` shapes
3. updates manual staged checkpoints for the new boundary
4. splits the current `cv_generation` artifact/debug payload into two stage-owned surfaces
5. adds regression coverage for:
   - `ranking -> cv_analysis` pause
   - `cv_analysis -> cv_generation` resume
   - failures isolated to analysis vs generation
