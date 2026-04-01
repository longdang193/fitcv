---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Tighten the shortlist stage so retrieval, ranking, and inspection surfaces all reflect one job-level shortlist contract."
invariants:
  - "The shortlist stage must remain a single-chunk `job_summary` retrieval design for jobs."
  - "The scoring shortlist must be derived from `passed_jobs`; raw vector hits alone are not sufficient to enter scoring."
  - "Job-level shortlist outputs must not be distorted by duplicate embedding rows for the same canonical job URL."
  - "Stage artifacts and export/debug surfaces must distinguish observed shortlist facts from inferred miss reasons."
---

# Shortlist Contract Cleanup Design

## Affected Feature Contracts

- [docs/features/cv_system/cv_system.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/shortlist.yaml](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/shortlist.yaml)

## Triage

Feature type: MODIFY  
Summary: Tighten shortlist semantics so the stage behaves as a job-level transform from `passed_jobs` to a scoring shortlist and explains misses without overclaiming causes.  
Reasoning: The shortlist stage already exists and mostly works, but code inspection and real run logs show drift between the documented stage contract, the storage model behind retrieval, and the meanings exposed in artifacts and debug exports. This is a cleanup and clarification of an existing capability, not a new feature.  
Invariants:
- The shortlist stage remains single-chunk job retrieval using `chunk_type = 'job_summary'`.
- `passed_jobs` stays the source-of-truth input set for the scoring shortlist.
- Raw retrieval rows may be diagnostic inputs, but they must not redefine shortlist membership on their own.
- Job-level ranks and counts exposed after shortlist must correspond to unique jobs, not duplicate embedding rows.
- Debug and artifact outputs must clearly separate what was observed from what is inferred.
Dependencies:
- `cv_system`
- `inspection_debugging`
- shortlist-stage runtime in `src/fitcv/pipeline.py`
- vector retrieval/storage logic in `src/fitcv/vector_search.py` and `src/fitcv/embeddings.py`
Affected stages:
- shortlist
Affected features:
- cv_system
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - `docs/generated/*`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Rollback trigger: shortlist counts, ranks, or export/debug status meanings become less trustworthy after cleanup  
Rollback method: restore the prior shortlist merge and artifact semantics while keeping new diagnostics disabled  
Migration needed: yes  
Risk level: medium

## Why This Spec Exists

The current shortlist stage has two concrete drifts and one softer semantic mismatch:

- `job_embeddings` can accumulate multiple rows for the same `job_url`, but retrieval still presents shortlist outputs as if the system ranked one unique row per job.
- `_materialize_scoring_shortlist(...)` can admit a raw vector hit even if the job is absent from `passed_jobs`, which makes the stage boundary looser than the stage contract.
- stage artifacts currently report that a job was "not returned by vector search", but that status is only an observed absence from raw hits, not a fully diagnosed cause.

This is visible in real logs such as [fitcv-run-3051f55f-6e55-483f-ba36-d2056eef8c80-shortlist.json](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-3051f55f-6e55-483f-ba36-d2056eef8c80-shortlist.json), where three shortlisted jobs carry sparse ranks `1`, `33`, and `46`. Those ranks are consistent with duplicate embedding rows participating in row-level ranking before dedupe, even though the stage presents the result as a job-level shortlist.

The result is not necessarily a retrieval failure, but it is a contract problem:

- the storage model is row-level
- the retrieval query ranks rows
- the shortlist output is interpreted as job-level

This spec resolves that mismatch without changing the single-chunk `job_summary` retrieval strategy.

## Problem Statement

The shortlist stage currently mixes three different levels of truth:

1. embedding-row truth in `job_embeddings`
2. raw retrieval-hit truth in `raw_shortlist`
3. job-level scoring shortlist truth in `shortlist`

That mixing causes three practical problems:

- job-level ranks can be misleading when duplicate embedding rows crowd retrieval
- shortlist membership can become slightly more permissive than the documented `passed_jobs` boundary
- debug and artifact fields can sound more causal than the runtime actually proves

The cleanup goal is to make shortlist a strict, explainable job-level stage again while preserving the current v1 retrieval strategy.

## Current Drift Details

### 1. Duplicate embeddings distort job-level rank semantics

[`embed_and_store_jobs()`](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/embeddings.py#L210) inserts new embedding rows into `job_embeddings` every run and does not replace older rows for the same `job_url`.

[`run_vector_search()`](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/vector_search.py#L138) then ranks retrieval rows with:

- `RANK() OVER (ORDER BY distance ASC)` as `vector_rank`
- dedupe by `job_url` only after query results return

That means:

- retrieval competition happens at embedding-row level
- dedupe happens later at job level
- the final shortlist can expose sparse ranks that do not mean "33rd best unique job"

### 2. Raw hits can currently outrun the `passed_jobs` contract

[`_materialize_scoring_shortlist()`](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L138) merges each raw retrieval row onto `passed_jobs` using `passed_by_url.get(job_url, {})`.

If the URL is absent from `passed_jobs`, the function still emits a shortlist row containing only:

- `job_url`
- vector metadata
- `shortlist_origin`

That means the scoring shortlist is currently "raw vector hits enriched from `passed_jobs` when available" rather than "jobs from `passed_jobs` that were shortlisted."

### 3. Artifact wording overstates causal certainty

[`_build_stage_transition_artifacts()`](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L949) reports `jobs_not_returned_by_vector_search` and labels changed samples as `missed_by_vector_search`.

Those are acceptable observed-state labels, but they do not prove why the miss happened. The runtime currently cannot distinguish, from stage-local facts alone, between:

- no searchable embedding row
- URL mismatch
- filtered out by duplicate-row crowding
- outside `top_n`
- other retrieval visibility issues

So the current wording is slightly too causal for the evidence available inside the stage.

## Design Goals

1. Preserve single-chunk `job_summary` job retrieval.
2. Make the scoring shortlist a strict job-level transform over `passed_jobs`.
3. Make shortlist ranks and counts reflect unique jobs, not duplicate embedding rows.
4. Keep raw retrieval outputs available for diagnostics.
5. Expose shortlist facts and shortlist hypotheses separately.

## Non-Goals

- introduce multi-chunk job retrieval
- redesign candidate evidence chunking
- change the downstream AI-scoring or final-ranking architecture
- build a full retrieval root-cause engine for every miss in this iteration

## Proposed Contract

### Job retrieval contract remains v1

The shortlist stage will continue to use:

- one `job_summary` embedding row per active job identity
- one synthetic candidate query embedding
- one raw retrieval pass over the filtered job universe

No multi-chunk job design is introduced by this spec.

### Scoring shortlist contract becomes strict

The scoring shortlist must satisfy all of the following:

- every scoring-shortlist row corresponds to a canonical job in `passed_jobs`
- raw vector hits that do not map back to `passed_jobs` are treated as retrieval anomalies, not valid shortlist entrants
- backfill remains allowed, but only for jobs already present in `passed_jobs`
- the shortlist stage owns the distinction between:
  - returned by vector search
  - backfilled for scoring
  - absent from raw retrieval hits

### Rank semantics become job-level

After cleanup, the shortlist stage must expose a job-level rank contract:

- the rank shown in shortlist outputs and artifacts is the unique-job rank after duplicate rows have been collapsed
- if row-level rank remains useful for diagnostics, it must be stored separately as an explicitly raw retrieval field

This avoids presenting a row-level ranking artifact as a job-level decision.

### Artifact semantics become evidence-scoped

The shortlist stage should distinguish:

- observed facts
- inferred or diagnostic hypotheses

Observed facts include:

- whether the job is in `passed_jobs`
- whether a raw retrieval row with the canonical URL was returned
- whether the job advanced to the scoring shortlist
- whether the job was backfilled
- the job-level shortlist rank and similarity used downstream

Diagnostic hypotheses may include:

- embedding row missing
- URL mismatch
- duplicate-row crowding
- outside `top_n`

But hypotheses must be emitted only when the stage has explicit evidence for them, or they must be labeled as best-effort diagnostics rather than authoritative reasons.

## Proposed Runtime Changes

### 1. Enforce one active job-summary row per canonical job URL

The retrieval contract should behave as one-row-per-job at search time.

There are two acceptable implementation shapes:

1. storage cleanup model
   - replace or upsert `job_summary` embeddings by canonical `job_url`
   - ensure old active rows do not remain queryable for the same logical job
2. retrieval cleanup model
   - preserve raw storage history if needed
   - query only the latest active embedding row per canonical `job_url`

Recommendation:

- prefer retrieval cleanup first if we need a smaller runtime change
- preserve optional historical rows only if they are explicitly excluded from shortlist ranking

The invariant is more important than the storage mechanism:

- shortlist retrieval must rank one active embedding row per canonical job

### 2. Canonicalize URL identity before storage and shortlist joins

The same canonical URL policy must be applied consistently across:

- passed-job construction
- embedding storage
- raw retrieval result handling
- shortlist merges

This cleanup should normalize job identity before the shortlist stage relies on exact string matches.

### 3. Reject raw hits that are absent from `passed_jobs`

When a raw retrieval row has no canonical match in `passed_jobs`, shortlist should:

- exclude it from the scoring shortlist
- count it as a retrieval anomaly
- optionally surface it in shortlist diagnostics for inspection

This restores the documented boundary:

- shortlist transforms passed jobs into a scoring shortlist

### 4. Separate raw retrieval metrics from job-level shortlist metrics

The stage should expose both, but with clearer names.

Recommended semantics:

- `raw_vector_rows`: count of raw retrieval rows before unique-job collapse
- `raw_vector_unique_jobs`: count of unique jobs represented in raw retrieval
- `scoring_shortlist_jobs`: count of jobs entering AI scoring
- `backfilled_jobs`: count of passed jobs added without a raw hit

If backward compatibility requires keeping `raw_vector_hits`, it should be redefined or deprecated explicitly:

- either keep it as unique-job hits
- or add a new field that names raw row count separately

### 5. Tighten shortlist status vocabulary

User-facing and artifact-facing statuses should stay job-level and evidence-scoped.

Recommended shortlist statuses:

- `returned_by_vector_search`
- `backfilled_for_scoring`
- `not_returned_in_raw_hits`
- `not_applicable`

The stage should avoid implying a stronger cause unless it can prove one.

Recommended diagnostic fields:

- `raw_hit_present`
- `scoring_shortlist_present`
- `retrieval_anomaly_present`
- `diagnostic_reason_code` only when evidence exists

## Data Model and Artifact Implications

### Stage artifacts

[`stage_transition_artifacts.shortlist`](/C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/shortlist.yaml) should evolve so its fields describe unique-job shortlist behavior first and raw retrieval behavior second.

The shortlist block should expose:

- the candidate query text
- configured `vector_search_top_n`
- unique-job raw-hit counts
- scoring-shortlist counts
- backfill counts
- retrieval anomalies where raw hits could not be grounded to `passed_jobs`
- changed-state samples for:
  - absent from raw hits
  - backfilled for scoring
  - raw-hit anomaly excluded from shortlist

### Export/debug surfaces

Run export and debug views under `inspection_debugging` should reflect the same contract:

- "returned by vector search" means a canonical raw hit existed
- "backfilled for scoring" means the job advanced despite no raw hit
- "not returned in raw hits" means exactly that, no stronger claim
- if a retrieval anomaly exists, it should be visible as such rather than silently treated as a valid shortlist row

## Rollout Plan

### Phase 1: Contract and diagnostics

- update shortlist code paths to enforce the strict `passed_jobs` boundary
- expose raw-row and unique-job retrieval counts separately
- preserve current single-chunk retrieval

### Phase 2: Active-row enforcement

- ensure shortlist ranking operates on one active embedding row per canonical job
- preserve raw-history storage only if it does not affect shortlist ranking

### Phase 3: Doc and artifact synchronization

- update feature contracts and stage contract
- update history entries
- regenerate discovery docs

## Risks

### Backward-compatibility risk

Existing tests and debug expectations may rely on:

- `raw_vector_hits`
- sparse `vector_rank` values
- permissive handling of raw hits that fail to rejoin `passed_jobs`

Those surfaces must be updated deliberately, not accidentally.

### Operational risk

If duplicate embedding rows are currently compensating for inconsistent URL identity, tightening the contract could temporarily reduce shortlist counts until canonical URL handling is fixed.

## Success Criteria

This cleanup is successful when all of the following are true:

- shortlist outputs always contain jobs that can be grounded back to `passed_jobs`
- shortlist ranks correspond to unique jobs rather than duplicate embedding rows
- raw retrieval anomalies are visible but do not silently alter shortlist membership
- stage artifacts and export/debug surfaces describe observed shortlist facts without overstating causes
- run logs no longer show sparse ranks caused solely by duplicate embedding-row competition when only a few unique jobs are shortlisted

## Open Questions

1. Should historical embedding rows remain stored for audit, or should the system prefer hard replacement by canonical `job_url`?
2. Do we want to preserve a separate raw row-level rank field for deep debugging, or is unique-job rank sufficient?
3. Should retrieval anomaly reporting live only in stage artifacts, or also in run-results exports shown in the admin UI?
