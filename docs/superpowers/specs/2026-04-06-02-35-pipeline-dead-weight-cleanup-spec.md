---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Remove pipeline computations, exports, and event emissions that no longer meaningfully affect runtime behavior or operator-facing diagnostics."
invariants:
  - "The pipeline must preserve current ranking, cv_analysis, cv_generation, and persistence behavior."
  - "Any removed field or computation must have no active production owner, or must be replaced by a clearer bounded owner."
  - "Run detail and exported diagnostics must stay sufficient for debugging completed and paused runs."
---

# Pipeline Dead-Weight Cleanup

## Triage

Feature type: MODIFY  
Summary: Remove dead-weight pipeline work that is still computed, persisted, or emitted even though the current runtime and admin surfaces no longer meaningfully use it.  
Reasoning: This is not a new feature. It is a contract and performance cleanup across existing diagnostics and pipeline summary paths.  
Invariants:
- Ranking, CV analysis, and CV generation outputs must remain behaviorally identical.
- Reuse logic must keep working for `enrich`, shortlist embeddings, ranking AI scores, and `cv_analysis`.
- Operator-facing diagnostics must remain readable and sufficiently explanatory after cleanup.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- `pipeline_performance`
Affected stages:
- enrich
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- `inspection_debugging`
- `trigger_run_management`
- `pipeline_performance`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/pipeline_performance/history.md`
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The current pipeline still performs or carries forward several pieces of work that no longer have a meaningful active owner in runtime behavior or operator-facing diagnostics.

This dead weight now falls into four buckets:

1. summary-level metrics that are recomputed even though the UI now reads them from stage artifacts
2. per-job job-ledger fields that are not consumed by any production surface
3. enrich-stage raw duplicate fields that inflate persisted rows and exports without active downstream use
4. per-job and compatibility-era metadata that survives mostly as historical baggage

The cleanup goal is not to minimize every byte mechanically. The goal is to make each computed or persisted unit answer a clear question:

- runtime behavior owner
- operator-facing diagnostic owner
- compatibility owner with explicit expiration

If a unit has none of those, it should stop being produced.

## Current Dead-Weight Candidates

### 1. Top-level summary metrics duplicated after the stage-artifact migration

The pipeline still computes:

- `stage_quality_metrics`
- `late_stage_reuse_metrics`
- top-level `shortlist_debug`

inside the run summary object even though the current control plane rebuilds run health directly from `stage_transition_artifacts`.

Current state:

- computed in `fitcv/pipeline.py`
- not exported in the job-ledger `results.json`
- not needed by run detail because run detail derives health from `stage_transition_artifacts_json`

This is summary-level duplicate work.

### 2. Per-row `shortlist_debug` inside `results.json`

Each row in the job-ledger export still carries `shortlist_debug`, but the current run-detail enriched-jobs tab uses:

- `pipeline_status`
- `reject_reasons`
- `rule_filter_marks`
- `decision_chain`

and does not read row-level `shortlist_debug`.

This makes `results.json` heavier without changing the current UI behavior.

### 3. Raw duplicate enrich fields that do not appear to drive runtime or UI

The enrich payload currently persists and re-exports fields such as:

- `description_cleaned`
- `location_type_raw`
- `seniority_raw`
- `domain_raw`
- `job_family_raw`

`description_cleaned` is still meaningful for enrich fingerprinting, but that does not require it to remain part of the run-scoped structured payload or operator-facing exports after enrich has completed.

The raw duplicate classification fields may still have historical debugging value, but they do not currently appear to drive:

- rule filtering
- shortlist
- ranking
- cv_analysis
- cv_generation
- default run-detail UI

This suggests storage/export dead weight, even if some raw values remain useful in narrowly scoped debug contexts.

### 4. Compatibility-era `cv_prompt_version`

The active CV generation prompt contract is now registry-owned and identified by prompt/runtime metadata such as:

- prompt id
- template path

Yet `cv_prompt_version` is still threaded through:

- CV generation artifacts
- CV version records
- some result/debug payloads

This is likely compatibility metadata rather than meaningful runtime control. It may still deserve a bounded compatibility owner, but not unlimited propagation.

### 5. Per-job late-stage event spam on large runs

The current pipeline still emits per-job events in Layer 4 for cases like:

- `layer4_cv_analysis_skip`
- `layer4_cv_error`
- `layer4_cv_validation_failed`

For runs with `500` to `1000` jobs, this can create high event volume and timeline noise while the run detail now already prefers aggregate stage-summary messaging and stage-owned artifact links.

This is not necessarily fully dead work, but it is a strong dead-weight candidate because:

- the operator-facing timeline has moved toward aggregate rows
- per-job links are no longer the preferred ownership model
- event volume scales with row count

## Design Goal

Make the pipeline produce only the units that still have a meaningful owner:

- **runtime owner**: affects ranking, filtering, CV writing, or persistence
- **diagnostic owner**: shown in run detail or exported diagnostics with a clear role
- **compatibility owner**: retained temporarily with explicit bounded purpose

Everything else should be removed, bounded, or demoted.

## Proposed Contract Split

### A. Pipeline summary object returned by `run_pipeline()`

Keep only what the worker or runtime still needs immediately:

- top-line counts
- `cv_generation_debug_records`
- `mapping_suggestions`
- `stage_transition_artifacts`
- `late_stage_reuse_snapshots`
- `export_results`

Remove from the top-level summary:

- `stage_quality_metrics`
- `late_stage_reuse_metrics`
- top-level `shortlist_debug`

Reasoning:

- run detail already derives health from `stage_transition_artifacts`
- job-ledger export intentionally no longer owns stage-level aggregates

### B. Job-ledger `results.json`

Keep `results.json` focused on:

- per-job final status
- compact score facts
- compact decision chain
- CV output metadata when produced

Remove from per-row payload unless a production owner is re-established:

- `shortlist_debug`

Keep only if explicitly justified later:

- row-level reuse status fields already used for operator-visible diagnosis

### C. Stage diagnostics

Keep stage-level diagnostics in:

- `stage_transition_artifacts`
- stage-local artifact downloads

If shortlist retrieval debugging is still important, its home should be:

- shortlist stage artifact decision summary
- shortlist stage samples

not duplicated into the top-level summary or every job-ledger row.

### D. Enrich payload slimming

Treat enrich payload fields in three classes:

1. canonical runtime fields  
Examples:
- `location_type`
- `seniority`
- `required_skills_canonical`
- `preferred_skills_canonical`
- `domain`
- `job_family`

2. runtime-support-only fields  
Examples:
- inputs needed for enrich fingerprinting or internal reuse

3. operator/debug-only fields  
Examples:
- raw duplicate values if they are still needed anywhere

Proposed default:

- stop exporting raw duplicate classification fields in run-scoped job-ledger surfaces
- consider stopping persistence of `description_cleaned` in structured job rows if fingerprinting can rely on raw source text or a narrower internal-only representation
- preserve raw values only in places with a proven debug owner

### E. `cv_prompt_version`

Reclassify `cv_prompt_version` explicitly:

- either compatibility-only metadata with a bounded owner
- or remove it from current artifacts/records where prompt id and template path already provide the active contract

Recommended direction:

- do not use `cv_prompt_version` as a primary live provenance field
- keep it only where historical compatibility with stored CV version rows still needs it
- avoid propagating it to new operator-facing payloads when prompt id/template already exist

### F. Timeline event volume

Adopt an aggregate-first event model for large runs.

Keep aggregate stage rows such as:

- normalize complete
- enrich complete
- rule filter complete
- shortlist complete
- ranking complete
- cv_analysis complete
- cv_generation complete

Demote or remove row-scaled per-job event emission where the same information is already recoverable from:

- aggregate stage rows
- stage artifact downloads
- job-ledger results

Priority candidates:

- per-job `layer4_cv_analysis_skip`
- per-job `layer4_cv_error`
- per-job `layer4_cv_validation_failed`

## What Must Remain

The cleanup must not remove work that still materially affects runtime or diagnostics.

Keep:

- enrich reuse fingerprints and reuse lookups
- shortlist embedding reuse and candidate query reuse
- ranking AI-score reuse
- `cv_analysis` exact-match reuse
- stage-owned prompt/model provenance
- stage-owned ranking contribution visibility if still used in stage artifacts
- job-ledger decision chain and final per-job outcome

## Acceptance Criteria

### Summary cleanup

- `run_pipeline()` no longer computes or returns top-level `stage_quality_metrics`
- `run_pipeline()` no longer computes or returns top-level `late_stage_reuse_metrics`
- `run_pipeline()` no longer computes or returns top-level `shortlist_debug`

### Job-ledger slimming

- `results.json` rows no longer include `shortlist_debug`
- current run-detail enriched-jobs rendering remains behaviorally unchanged

### Enrich payload cleanup

- raw duplicate classification fields are removed from operator-facing run-scoped exports unless a concrete debug owner remains
- `description_cleaned` is not persisted or exported beyond the scope required for fingerprinting, if a safe internal replacement is available

### Prompt metadata cleanup

- `cv_prompt_version` is no longer treated as a meaningful live prompt selector in operator-facing exports
- if retained, its compatibility purpose is explicit and bounded

### Event cleanup

- timeline event count for large runs is meaningfully reduced
- aggregate stage messaging remains sufficient for operators
- stage artifact downloads still provide detailed diagnosis when needed

## Risks

### Losing useful forensic detail

Some apparently unused fields may still help ad hoc debugging through raw JSON inspection.

Mitigation:

- remove only fields with no current production consumer and no clear stage-owned diagnostic role
- prefer moving diagnostics to stage artifacts over deleting them outright

### Over-pruning compatibility fields

Some historical data flows may still expect `cv_prompt_version`.

Mitigation:

- keep compatibility boundaries explicit
- update tests around tracker / BigQuery row shapes before removing storage-level fields

### Breaking large-run investigations

Reducing event volume too aggressively could hide useful row-level failure patterns.

Mitigation:

- preserve aggregate failure counts in stage summary rows
- preserve per-row failure detail in stage artifacts or debug exports

## Recommended Execution Order

1. Remove top-level summary duplicate metrics.
2. Remove row-level `shortlist_debug` from job-ledger exports.
3. Audit and slim raw duplicate enrich fields.
4. Reclassify `cv_prompt_version` propagation.
5. Reduce row-scaled Layer 4 event emission in favor of aggregate stage summaries.

## Source-of-Truth Alignment

Primary feature contract:

- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/inspection_debugging.yaml)

Secondary affected feature contracts:

- [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/pipeline_performance/pipeline_performance.yaml)
- [trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/trigger_run_management/trigger_run_management.yaml)

Expected follow-up docs:

- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/inspection_debugging/history.md)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/pipeline_performance/history.md)
