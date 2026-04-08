---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Separate `results.json` into a job-centric run ledger while keeping stage diagnostics in `stage-artifacts.json` and per-stage artifacts."
---

# Results JSON Job-Ledger Separation

## Triage

Feature type: MODIFY
Summary: Redefine `results.json` as a job-ledger export and move run-level diagnostic ownership fully to stage artifacts.
Reasoning: The current export contract overlaps too heavily between `results.json`, `stage-artifacts.json`, and the per-stage JSON files, which makes each artifact harder to trust and more expensive to inspect.
Invariants:
  - `results.json` must remain the easiest operator-facing export for answering what happened to each job in a run.
  - Stage-level metrics, reuse diagnostics, prompt provenance, and sample rows must remain available in stage-owned artifacts.
  - Per-stage JSON files remain the deepest debug source and must not lose diagnostic fidelity.
Dependencies:
  - `inspection_debugging`
  - `cv_system`
  - `trigger_run_management`
Affected stages:
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
Affected features:
  - inspection_debugging
  - cv_system
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs: none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

`results.json` is currently trying to be both:

- the run's job-by-job processed results ledger
- and a secondary container for run-level diagnostics that already belong to stage artifacts

This creates three problems:

1. Contract overlap
- `results.json` repeats stage-derived blocks such as quality metrics, reuse metrics, and other run-level debug structures that are already represented elsewhere.

2. Weaker ownership boundaries
- Operators cannot easily tell whether a field is:
  - a per-job final outcome
  - a run-level summary
  - or a stage-owned diagnostic detail

3. Heavier exports with lower clarity
- The most operator-facing export contains data that is only useful for stage debugging, while stage-centric artifacts already exist for that purpose.

## Design Goal

Create a clean three-surface export model:

1. `results.json`
- job-centric
- operator-facing
- answers what happened to each job

2. `stage-artifacts.json`
- run-centric diagnostic bundle
- convenience export for all stage diagnostics together

3. per-stage `*.json`
- stage-centric
- authoritative deep debug source

## Proposed Separation

### 1. `results.json` becomes the job ledger

`results.json` should answer these questions:

- which jobs were processed?
- what was each job's final pipeline outcome?
- where did each job stop?
- why did it stop there?
- was a CV produced, and if so, what output metadata exists?

It should not try to answer:

- how shortlist behaved globally
- which stage had poor health
- how many rows were reused at a stage
- prompt provenance for every late stage
- sample rows for stage debugging

### 2. `stage-artifacts.json` remains the bundled diagnostics export

`stage-artifacts.json` should own the "download everything diagnostic" story.

It remains the home for:

- per-stage decision summaries
- per-stage counts
- reuse metrics
- quality metrics
- prompt/model provenance
- evidence diagnostics
- stage samples

This file is intentionally redundant with the individual stage exports, but only as a convenience bundle.

### 3. Per-stage JSON remains the deep source of truth

Each stage artifact keeps ownership of:

- stage-local settings refs
- stage-local prompt/model provenance
- stage-local reuse information
- stage-local samples
- stage-local decisions and diagnostics

These files remain the authoritative artifact for debugging one stage in depth.

## Required `results.json` Contract

### Top-level run summary

Keep only compact run-scoped information that supports the job ledger:

- `run_id`
- `status`
- `created_at`
- `started_at` when available
- `finished_at` when available
- `summary`

Recommended `summary` fields:

- `total_jobs`
- `passed_filter`
- `ranked`
- `cvs_generated`

This top-level summary should stay compact and operator-readable.

### `results[]` rows

Each row should remain job-centric and include:

- stable job identity
  - `job_url`
  - `title`

- compact canonical context
  - `domain`
  - `job_family`
  - `seniority`
  - `location_type`

- final job outcome
  - `pipeline_status`
  - compact decision chain

- per-job stage path facts only when needed to explain the job outcome
  - filter pass/reject
  - shortlist path
  - ranking fit
  - cv_analysis handoff status
  - cv_generation outcome

- final CV output metadata when a CV exists
  - `version_id`
  - `fit_classification`
  - other compact output identifiers only

### Explicitly remove from `results.json`

The following should no longer live at the top level of `results.json`:

- `stage_quality_metrics`
- `late_stage_reuse_metrics`
- top-level `shortlist_debug`
- any other run-level stage diagnostics already owned by stage artifacts

If a field is needed only to debug a stage globally, it belongs in:

- `stage-artifacts.json`
- or the stage-specific artifact

## Allowed Per-Job Detail in `results.json`

Some compact per-job debug is still acceptable when it helps explain the final path of one job.

Allowed:

- compact decision chain
- final pipeline-outcome explanation
- compact per-job shortlist/ranking facts if they are necessary to understand why the job was not advanced

Not allowed:

- bulky stage sample payloads
- run-level aggregate metric blocks
- stage-owned prompt provenance repeated for every row without job-specific value

Rule:

If a field primarily explains stage behavior across the run, it does not belong in `results.json`.

## Ownership Rules

### `results.json`

Primary owner:
- job-level outcome contract

Best for:
- operators
- run review
- downstream result consumption

### `stage-artifacts.json`

Primary owner:
- run-level diagnostic bundle

Best for:
- one-click run debug export
- audit or support workflows

### per-stage `*.json`

Primary owner:
- deep stage diagnostics

Best for:
- implementation debugging
- contract verification
- tuning and regression analysis

## UI Implications

Run detail should align to the same separation:

- `results.json`
  - linked and described as the run results ledger

- `stage-artifacts.json`
  - linked and described as the bundled diagnostics export

- timeline stage downloads
  - continue to point to stage-specific artifacts

The UI should not imply that `results.json` is the main stage-debug artifact.

## Migration Strategy

### Phase 1

Slim `results.json` without changing the per-job result-row meaning.

Actions:

- remove top-level stage metric and reuse blocks
- remove top-level redundant shortlist debug blocks
- keep compact `summary`
- preserve existing `results[]` row identity and main outcome fields

### Phase 2

Review per-job row payload size and trim any remaining stage-owned fields that are not needed to explain the row outcome.

### Phase 3

Update UI labels and export descriptions so operators understand:

- `Results JSON` = job ledger
- `Stage Artifacts JSON` = bundled diagnostics
- stage downloads = deep stage debug

## Invariants

- `results.json` stays the easiest export for understanding job outcomes.
- No diagnostic capability currently owned by stage artifacts may be lost.
- The separation must reduce overlap, not create missing information gaps.
- Per-stage artifact fidelity takes priority over convenience duplication in `results.json`.

## Affected Source-of-Truth Docs

- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/FitCV-pipeline.md`

## Success Criteria

- `results.json` reads like a job-by-job processed results ledger.
- Run-level diagnostic blocks are no longer duplicated there when stage artifacts already own them.
- `stage-artifacts.json` remains the convenience bundle.
- Per-stage JSON remains the authoritative deep debug surface.
