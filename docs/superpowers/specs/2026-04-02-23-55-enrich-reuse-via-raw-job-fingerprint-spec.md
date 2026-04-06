---
feature_type: modify
feature_name: pipeline_performance
status: draft
summary: "Reuse enrichment results when a normalized raw job fingerprint and enrich contract match, so repeated runs avoid unnecessary LLM extraction cost."
invariants:
  - "Enrichment reuse must be based on normalized raw-job inputs, not on later downstream interpretations."
  - "A reused enrich result must be semantically equivalent to what the current enrich contract would have produced for the same raw-job fingerprint."
  - "Run-scoped enriched outputs and inspection surfaces must still show whether a row was freshly enriched or reused."
  - "Changing the effective enrich contract must invalidate reuse automatically."
---

# Enrich Reuse Via Raw-Job Fingerprint Design

## Affected Feature Contracts

- [docs/features/pipeline_performance/pipeline_performance.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Enrich/docs/features/pipeline_performance/pipeline_performance.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Enrich/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/enrich.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Enrich/docs/stages/enrich.yaml)

## Triage

Feature type: MODIFY  
Summary: Add enrichment-result reuse keyed by a stable raw-job fingerprint plus enrich contract provenance so repeated runs can skip redundant LLM enrichment safely.  
Reasoning: The pipeline already normalizes jobs before enrichment and persists enriched rows into shared tables. The missing capability is safe reuse when the normalized raw job has not meaningfully changed. This is a performance and cost optimization of the existing enrichment stage, not a new stage or a new user-facing feature family.  
Invariants:
- Reuse must be decided before calling the enrich LLM, using normalized raw inputs only.
- Fingerprints must exclude volatile scrape/runtime fields so repeated identical jobs hash the same way.
- The enrich contract version used for reuse must include the effective prompt/model/schema contract so stale enrich rows do not survive contract changes.
- Reused rows must still flow through run-scoped persistence and inspection like freshly enriched rows.
Dependencies:
- `pipeline_performance`
- `inspection_debugging`
- enrich runtime in `src/fitcv/enrich.py`
- pipeline orchestration in `src/fitcv/pipeline.py`
- shared persistence in `structured_jobs` and `run_structured_jobs`
Affected stages:
- enrich
Affected features:
- pipeline_performance
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/pipeline_performance/pipeline_performance.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/pipeline_performance/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Rollback trigger: enrich reuse returns stale or semantically mismatched rows after prompt/schema/model changes  
Rollback method: disable reuse and fall back to always-enrich while preserving any additive fingerprint metadata fields  
Migration needed: yes  
Risk level: medium

## Why This Spec Exists

The current pipeline already pays the cost to normalize jobs before enrichment, and enrichment already produces a shared downstream contract that later stages reuse.

But when the same job appears in a later run, the pipeline currently still:

- calls the enrich prompt again
- pays the LLM cost again
- risks small LLM-driven output drift again

That is expensive and unstable for jobs that have not materially changed.

The user-approved direction is:

- add reuse efficiency at the enrich stage first
- decide reuse from stable normalized raw-job content
- only re-enrich when the raw job or enrich contract has actually changed

## Problem Statement

The current pipeline lacks a stable identity for “this normalized raw job is materially the same enrich input as before.”

Without that identity:

- repeated runs re-enrich identical jobs
- enrichment cost scales unnecessarily
- downstream outputs can drift slightly even when the source job did not change
- later reuse opportunities, like shortlist-level embedding reuse, become harder because the enrich layer itself is not stable

So the missing piece is not generic caching. It is:

- a stable pre-enrichment fingerprint
- plus a clear enrich-contract compatibility rule

## Design Goals

1. Reuse enrichment results when the normalized raw job content is unchanged.
2. Invalidate reuse automatically when the effective enrich contract changes.
3. Keep reuse logic explainable and deterministic.
4. Preserve full run-scoped visibility into whether a row was reused or freshly enriched.
5. Avoid tying reuse to brittle downstream semantic interpretation.

## Non-Goals

- reuse based on enriched output text itself
- approximate reuse based only on `job_url`
- global cache invalidation for every model change in unrelated stages
- redesigning structured_jobs persistence beyond the fields needed for safe reuse

## Chosen Design

### Reuse decision happens before enrichment

The pipeline should decide whether to reuse *before* calling the LLM for enrichment.

That decision uses:

1. a stable raw-job fingerprint
2. an enrich-contract fingerprint

Reuse is allowed only when both match a previously stored enriched row.

### Stable raw-job fingerprint is built from normalized raw fields

The fingerprint should be derived from the normalized job row, not from enriched output.

Recommended fingerprint input shape:

```json
{
  "job_url": "...",
  "title": "...",
  "company": "...",
  "location": "...",
  "description_cleaned": "...",
  "employment_type": "...",
  "experience_level": "...",
  "source": "..."
}
```

Rules:

- normalize strings with trim/lower/collapsed whitespace
- exclude volatile fields like scrape time, applicant count, run IDs, input order, and transient source metadata
- serialize deterministically with stable key ordering
- hash the result into `raw_job_fingerprint`

The strongest field is expected to be the cleaned description text, but other stable contextual fields should also participate.

### Enrich-contract compatibility must be explicit

Reuse must not depend only on raw-job sameness. It must also depend on whether the enrich contract is meaningfully the same.

The enrich contract fingerprint should include the effective enrich-stage contract inputs, such as:

- effective enrich prompt ID / version
- effective enrich model
- response schema version or parsing contract version
- any canonical-skill post-processing contract version

This ensures that:

- changing the prompt
- changing the model
- changing the expected enrich output contract

automatically invalidates reuse.

### Structured storage becomes the reuse source of truth

The shared `structured_jobs` table should become the primary reuse lookup surface.

For a given normalized raw job:

- if there is a stored enriched row with matching `job_url`
- matching `raw_job_fingerprint`
- matching `enrich_contract_fingerprint`

then the pipeline can reuse that enriched result instead of calling the LLM.

The run still writes a fresh row to `run_structured_jobs`, but the row should indicate that the enrich payload came from reuse.

## Proposed Runtime Changes

### 1. Add normalized raw-job fingerprint generation

Introduce one code-owned function that:

- projects a normalized raw job into a stable reuse payload
- serializes it deterministically
- returns a fingerprint string

This function should be treated as part of the enrich contract and versioned when its input shape changes.

### 2. Add enrich-contract fingerprint generation

Introduce one code-owned function that computes an enrich-contract fingerprint from:

- prompt provenance
- model
- schema contract
- relevant enrich post-processing contract version

This allows reuse invalidation without manually clearing old rows.

### 3. Lookup before enrich, enrich only on miss

The enrich pipeline path should become:

1. normalize jobs
2. compute `raw_job_fingerprint`
3. compute `enrich_contract_fingerprint`
4. lookup matching structured row
5. reuse on match
6. call LLM enrich only on miss

This means the LLM call becomes conditional, not universal.

### 4. Persist reuse provenance

Each enriched row should expose enough provenance to answer:

- was this row reused or freshly enriched?
- which raw fingerprint was used?
- which enrich contract fingerprint was used?

Recommended fields:

- `raw_job_fingerprint`
- `enrich_contract_fingerprint`
- `enrich_reuse_status` with values like:
  - `fresh_enrichment`
  - `reused_cached_enrichment`

Optional:

- `reused_from_job_url`
- `reused_from_enriched_at`

### 5. Inspection surfaces must show reuse explicitly

The enrich stage artifact and run-detail inspection should show:

- reused row counts
- fresh row counts
- sample rows with reuse provenance

This matters because reuse is a semantic shortcut; it should never be invisible in debugging.

## Data Model Implications

### `structured_jobs`

`structured_jobs` should gain the fields needed to support reuse lookup and provenance:

- `raw_job_fingerprint`
- `enrich_contract_fingerprint`
- optional `enrich_reuse_status` or equivalent provenance fields if storing them at shared-table level is useful

The shared table remains keyed by `job_url`, but the fingerprint fields define whether the current stored row is reusable under the active contract.

### `run_structured_jobs`

`run_structured_jobs` should also carry reuse provenance so each run can explain:

- which rows were reused
- which rows were freshly enriched

This is especially useful for manual staged debugging and cost analysis.

## Rollout Plan

### Phase 1: fingerprint contract

- define stable raw-job fingerprint input shape
- define enrich-contract fingerprint shape
- add tests proving deterministic fingerprinting behavior

### Phase 2: reuse lookup and persistence

- lookup matching rows in `structured_jobs`
- skip LLM enrichment on exact fingerprint + contract match
- persist reuse provenance into shared and run-scoped enriched rows

### Phase 3: inspection surfaces

- enrich stage artifacts and run detail expose reuse/fresh counts and sample provenance
- settings-used and prompt provenance remain consistent with the reuse decision path

## Risks

### Under-hashing risk

If the raw-job fingerprint excludes a meaningful raw field, the system may wrongly reuse stale enrich output.

### Over-hashing risk

If the raw-job fingerprint includes noisy or volatile fields, reuse rates will be poor and the optimization becomes ineffective.

### Contract-drift risk

If enrich-contract fingerprinting is incomplete, prompt/model/schema changes may incorrectly reuse stale enrich results.

## Success Criteria

This design is successful when:

- identical normalized jobs are no longer re-enriched unnecessarily
- prompt/model/schema changes invalidate reuse automatically
- enrich-stage artifacts show clear reuse versus fresh-enrichment behavior
- downstream stages receive the same enrich contract shape regardless of whether a row was reused or freshly enriched

## Open Questions

1. Which normalized raw fields are stable enough to include in the initial fingerprint without making reuse too brittle?
2. Should `description_cleaned` be sufficient as the dominant raw-text field, or do we want a separate normalized title/company/location bundle in the fingerprint too?
3. Should reuse lookup be `job_url`-scoped only, or should later iterations allow cross-URL reuse when the raw fingerprint matches exactly?
