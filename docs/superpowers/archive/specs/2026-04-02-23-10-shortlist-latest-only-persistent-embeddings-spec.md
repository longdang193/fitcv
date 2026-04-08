---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Make shortlist retrieval rank only the latest active persistent embedding per canonical job URL while keeping backfill as an explicit safety net with stronger diagnostics."
invariants:
  - "The shortlist stage must continue to operate on `passed_jobs` as its job-level source-of-truth input set."
  - "At shortlist retrieval time, at most one active `job_summary` embedding row may participate per canonical `job_url`."
  - "Backfill remains a safety net for retrieval misses; it must not silently redefine shortlist membership semantics."
  - "Shortlist artifacts and exports must distinguish observed retrieval facts from inferred causes."
---

# Shortlist Latest-Only Persistent Embeddings Design

## Affected Feature Contracts

- [docs/features/cv_system/cv_system.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/cv_system/cv_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/trigger_run_management/trigger_run_management.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/trigger_run_management/trigger_run_management.yaml)
- [docs/stages/shortlist.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/stages/shortlist.yaml)

## Triage

Feature type: MODIFY  
Summary: Replace duplicate-row-prone shortlist retrieval with latest-only persistent embedding selection per canonical `job_url`, while preserving backfill and making retrieval diagnostics more explicit.  
Reasoning: The shortlist stage already exists and already embeds current-run passed jobs before vector search. The problem is not the existence of the stage, but the retrieval contract over persistent embeddings: stale or duplicate `job_embeddings` rows can still compete at search time and distort job-level shortlist behavior. This is a cleanup and tightening of an existing capability.  
Invariants:
- `passed_jobs` remains the source-of-truth job universe entering shortlist.
- Retrieval continues to use persistent embeddings rather than a fully run-scoped isolated embedding store.
- Exactly one active embedding row per canonical `job_url` may participate in vector search.
- Backfill remains allowed only for jobs already present in `passed_jobs`.
- Stage artifacts and run inspection must expose retrieval facts clearly enough to debug backfill and anomalies.
Dependencies:
- `cv_system`
- `inspection_debugging`
- `trigger_run_management`
- shortlist runtime in `src/fitcv/pipeline.py`
- embedding storage logic in `src/fitcv/embeddings.py`
- retrieval logic in `src/fitcv/vector_search.py`
Affected stages:
- shortlist
Affected features:
- cv_system
- inspection_debugging
- trigger_run_management
Primary lens: mixed
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
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Rollback trigger: shortlist output loses expected jobs, or retrieval diagnostics become less trustworthy after latest-only filtering is introduced  
Rollback method: restore the prior retrieval query and shortlist diagnostics while keeping any non-breaking artifact additions disabled  
Migration needed: yes  
Risk level: medium

## Why This Spec Exists

The current shortlist stage already tries to prevent jobs from disappearing too early:

- it embeds the current run's `passed_jobs`
- it restricts vector search to `passed_job_urls`
- it dedupes raw retrieval rows by `job_url`
- it backfills passed jobs that raw retrieval missed

Those guardrails are helpful, but they still leave one important source of noise in place:

- persistent `job_embeddings` can contain multiple rows for the same canonical `job_url`
- vector search can rank those duplicate or stale rows before shortlist-level dedupe happens
- the stage then collapses them after retrieval, which means job-level ranks and shortlist explanations are reacting to row-level storage noise

The user-approved direction is:

- keep persistent embeddings
- but make shortlist retrieval latest-only per canonical `job_url`

That gives us cleaner shortlist semantics without forcing a full redesign to run-scoped embedding storage.

## Problem Statement

Today the shortlist stage can still suffer from duplicate-row competition even though earlier stages are job-level and deduped.

The problem is not that the pipeline source jobs contain duplicates. The problem is that retrieval searches `job_embeddings`, and `job_embeddings` can accumulate multiple `job_summary` rows for the same `job_url` across runs.

That causes three practical issues:

1. Raw retrieval rows can contain the same `job_url` more than once.
2. Job-level `vector_rank` and `vector_similarity` are derived from a row-level competition the stage later hides.
3. Backfill can happen for reasons that are harder to debug because retrieval and storage state are not tightly aligned.

## Design Goals

1. Keep persistent embeddings and reuse them across runs.
2. Ensure shortlist retrieval searches at most one active `job_summary` row per canonical `job_url`.
3. Preserve current run embedding writes for `passed_jobs`.
4. Keep backfill as an explicit safety net rather than an accidental membership rule.
5. Improve shortlist diagnostics so retrieval misses, backfill, and anomalies are easier to inspect.

## Non-Goals

- redesign the stage to use a fully isolated run-scoped embedding table
- remove backfill entirely
- introduce multi-chunk job retrieval
- redesign AI scoring or final ranking
- build a full retrieval root-cause engine for every missing hit in this iteration

## Chosen Design

### Persistent embeddings stay, but shortlist behavior becomes latest-only

The shortlist stage will continue to write persistent `job_summary` embeddings for current-run `passed_jobs`.

However, shortlist must no longer let all historical rows for one URL remain active at search time. The implementation can achieve this either by search-time selection or by replacing older active rows before retrieval runs.

The intended effect is:

- we keep reuse and persistence benefits
- we stop old rows from competing with current ones during retrieval
- raw retrieval rows become much closer to true job-level retrieval facts

### Current-run embedding still happens before retrieval

The stage should continue its current order:

1. `rule_filter` produces `passed_jobs`
2. shortlist embeds and stores those passed jobs
3. shortlist embeds the candidate query context
4. vector search runs over the filtered passed-job universe
5. scoring shortlist is materialized

This means the design is not "go back to a shared historical store only." It is:

- write current-run embeddings
- retrieve from the persistent store using latest-only semantics

### Backfill remains intentional

Backfill continues to exist because vector search can still miss eligible jobs for reasons other than duplicate-row competition:

- write visibility lag
- top-N cutoff
- query/ranking behavior
- missing or failed writes

So the design keeps backfill, but with clearer semantics:

- a job can be `returned_by_vector_search`
- a job can be `backfilled_for_scoring`
- a job can be absent from raw hits
- a raw-hit anomaly can exist separately if retrieval returns a row that cannot be grounded to `passed_jobs`

## Proposed Runtime Changes

### 1. Canonical job identity must be consistent at embedding and retrieval boundaries

The same canonical `job_url` policy must be used across:

- `passed_jobs`
- embedding storage
- retrieval filtering
- shortlist joins

This keeps "latest row per job" meaningful and prevents identity drift from creating fake misses.

### 2. At most one active row per canonical `job_url` may participate in retrieval

The shortlist stage must no longer let every matching historical `job_embeddings` row participate for `passed_job_urls`.

Implementation shape is open, but the behavior is not:

- only `chunk_type = 'job_summary'`
- only canonical URLs in the current `passed_job_urls`
- only one active row per canonical `job_url` may participate in retrieval

Initial implementation note:

- because BigQuery `VECTOR_SEARCH` rejects richer base-table subquery shapes, shortlist may materialize a temporary latest-row table first and run `VECTOR_SEARCH` over that table

The most likely latest selector remains:

- latest `created_at` per canonical `job_url`

### 3. Raw retrieval dedupe remains as a defensive guard

Even after latest-only retrieval is introduced, shortlist should still keep a lightweight dedupe by `job_url`:

- it becomes a safety guard instead of the main contract enforcement
- it protects against unexpected query drift or malformed rows

### 4. Backfill remains bounded and explicit

`_materialize_scoring_shortlist(...)` should continue to:

- include genuine retrieval hits first
- add missing `passed_jobs` only while shortlist capacity remains
- mark these rows with:
  - `shortlist_origin: "backfill"`
  - `vector_similarity: 0.0`

But the stage must also make the reason surface clearer:

- backfill is evidence of a retrieval miss
- it is not itself evidence of a storage failure

### 5. Retrieval diagnostics should become more explicit

The shortlist stage artifact should make these distinct:

- `raw_vector_rows`
- `raw_vector_unique_jobs`
- `scoring_shortlist_jobs`
- `backfilled_jobs`
- `raw_shortlist_anomaly_urls`
- `backfilled_job_urls`

Recommended changed-state sample rows should expose:

```json
{
  "job_url": "...",
  "job_title": "...",
  "shortlist_outcome": "backfilled_for_scoring",
  "raw_hit_present": false,
  "vector_similarity": 0.0,
  "vector_rank": 12,
  "shortlist_origin": "backfill"
}
```

This makes the stage easier to debug without overstating causal certainty.

## Data Model Implications

### `job_embeddings`

The persistent `job_embeddings` table may continue to store history, but shortlist retrieval must behave as though only one row is active per canonical `job_url`.

This means one of two implementation patterns:

1. physical replacement / cleanup
   - old rows are replaced or deactivated
2. logical latest-only selection
   - history remains stored
   - retrieval query selects only the latest active row

This spec prefers logical latest-only selection first because it is less invasive while still fixing shortlist behavior.

### Stage artifacts and exports

`stage_transition_artifacts.shortlist` should make the latest-only model visible through decision-summary fields and samples, not just count totals.

Run-detail exports should remain job-level and reflect:

- whether the job was returned by retrieval
- whether it was backfilled
- whether a raw-hit anomaly was observed

## Rollout Plan

### Phase 1: latest-only retrieval contract

- update retrieval query to operate on latest active embedding rows per canonical `job_url`
- preserve current persistent storage writes
- keep shortlist-level dedupe as a safety check

### Phase 2: stronger diagnostics

- expand shortlist artifacts and run export/debug surfaces
- explicitly report raw-row counts, unique-job counts, anomalies, and backfill

### Phase 3: optional storage cleanup follow-up

- if needed later, add a cleanup/upsert policy so the storage layer itself also trends toward one active row per canonical `job_url`

## Risks

### Query complexity risk

Latest-only selection makes the vector-search SQL more complex and may affect query performance or debugging simplicity if implemented carelessly.

### Canonical URL drift risk

If different parts of the pipeline canonicalize `job_url` differently, latest-only retrieval can accidentally hide valid rows or create apparent misses.

### Overconfidence risk

Even after latest-only retrieval, not every backfill means a storage problem. Artifacts must keep observed facts separate from inferred explanations.

## Success Criteria

This design is successful when:

- raw vector hits almost never contain duplicate `job_url` values
- shortlist ranks correspond to one active embedding row per canonical job
- backfill becomes rarer and easier to interpret
- shortlist artifacts clearly explain which jobs were retrieved, backfilled, or anomalous
- retrieval behavior stays consistent with the `passed_jobs` boundary

## Open Questions

1. Should canonical `job_url` cleanup be handled in shortlist code only, or should earlier normalization guarantee the exact retrieval identity format?
2. Should latest-only selection use `created_at` only, or also require a future explicit `is_active` field?
3. Do we want a future maintenance job to prune or archive stale embedding rows once the latest-only contract is in place?
