---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement latest-only persistent shortlist retrieval per canonical job URL and expand shortlist diagnostics so backfill and anomalies are easier to inspect."
invariants:
  - "The shortlist stage must continue to derive scoring-shortlist membership from `passed_jobs`."
  - "Vector search may rank at most one active `job_summary` embedding row per canonical `job_url`."
  - "Backfill remains additive safety-net behavior; it does not replace retrieval as the primary shortlist source."
  - "Shortlist diagnostics must distinguish observed retrieval facts from inferred causes."
---

# Shortlist Latest-Only Persistent Embeddings Plan

## Triage

Feature type: MODIFY
Summary: Make shortlist retrieval latest-only per canonical `job_url` while improving shortlist diagnostics and preserving current persistent embedding writes plus backfill behavior.
Reasoning: The shortlist stage already exists and already writes persistent embeddings for current-run `passed_jobs`. The remaining problem is retrieval contract drift caused by stale/duplicate rows in `job_embeddings`, plus debug surfaces that do not make shortlist anomalies explicit enough. This is a behavior cleanup of an existing stage, not a new stage or new feature family.
Invariants:
- `passed_jobs` remains the job-level shortlist boundary.
- Vector retrieval continues to use persistent embeddings rather than a dedicated run-scoped embedding table.
- At search time, at most one active `job_summary` row may compete per canonical `job_url`.
- Backfill remains allowed only for jobs already present in `passed_jobs`.
- Stage artifacts and run inspection must expose shortlist facts clearly enough to debug retrieval misses.
Dependencies:
- `cv_system`
- `inspection_debugging`
- `trigger_run_management`
- shortlist runtime in `src/fitcv/pipeline.py`
- retrieval query builder in `src/fitcv/vector_search.py`
- embedding persistence in `src/fitcv/embeddings.py`
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
Spec needed: no
Plan needed: yes
Rollback trigger: shortlist output loses expected jobs or diagnostics become less trustworthy after latest-only retrieval is introduced
Rollback method: restore the prior retrieval query and artifact semantics while disabling the latest-only query path
Migration needed: no
Risk level: medium

## Scope

This plan implements [2026-04-02-23-10-shortlist-latest-only-persistent-embeddings-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/superpowers/specs/2026-04-02-23-10-shortlist-latest-only-persistent-embeddings-spec.md).

In scope:

- latest-only retrieval selection for `job_summary` embeddings per canonical `job_url`
- stable canonical URL handling across shortlist embedding and retrieval joins
- shortlist artifact and export diagnostics for raw rows, unique jobs, anomalies, and backfill
- preserving current persistent embedding writes and shortlist backfill behavior

Out of scope:

- replacing persistent embeddings with a fully run-scoped embedding store
- removing backfill
- introducing multi-chunk job retrieval
- pruning historical embedding rows from storage in this slice

## Implementation Tasks

### Task 1: Tighten canonical `job_url` handling at shortlist boundaries

Make sure the shortlist stage uses one consistent canonical `job_url` identity across:

- `passed_jobs`
- embedding writes
- vector-search filtering
- raw-hit joins
- shortlist anomaly detection

Requirements:

- centralize or reuse one canonical URL extraction path for shortlist code
- prevent empty or malformed job URLs from entering retrieval joins silently
- add tests that cover matching the same logical job across embedding, retrieval, and shortlist materialization

Likely touchpoints:

- `src/fitcv/pipeline.py`
- `src/fitcv/vector_search.py`
- possibly shared helper code already used by shortlist/ranking exports

### Task 2: Make shortlist latest-only per canonical `job_url`

Update shortlist so ranking operates on at most one active `job_summary` row per canonical `job_url`.

Requirements:

- preserve the existing rule-filter universe restriction (`job_url IN passed_job_urls`)
- preserve `chunk_type = 'job_summary'`
- prefer a temporary latest-row table if BigQuery `VECTOR_SEARCH` rejects richer base-table query shapes
- keep the final `VECTOR_SEARCH` call within supported base-table constraints
- keep the behavior readable and testable

Deliverables:

- updated retrieval contract implementation
- tests proving duplicate historical rows for one `job_url` do not compete as active shortlist candidates

### Task 3: Keep shortlist-level dedupe as a defensive guard

Retain `_dedupe_shortlist_rows(...)` and shortlist materialization dedupe even after latest-only retrieval lands.

Requirements:

- keep the existing safety guard behavior
- make sure the dedupe is treated as defense-in-depth, not the primary contract
- add regression coverage that duplicate raw rows still cannot create duplicate shortlist jobs

### Task 4: Preserve backfill but make it more explicit in runtime data

Backfill should still protect passed jobs from disappearing, but it should be easier to inspect and reason about.

Requirements:

- keep current bounded backfill semantics
- preserve `shortlist_origin = "backfill"` and `vector_similarity = 0.0`
- expose a clearer per-row shortlist outcome in artifact/export samples
- keep anomaly URLs separate from backfilled job URLs

Recommended added row-level fields:

```json
{
  "shortlist_outcome": "returned_by_vector_search | backfilled_for_scoring",
  "raw_hit_present": true,
  "retrieval_anomaly_present": false
}
```

### Task 5: Expand shortlist stage diagnostics and export surfaces

Make shortlist inspection surfaces explain retrieval behavior directly.

Requirements:

- `stage_transition_artifacts.shortlist` should report:
  - `raw_vector_rows`
  - `raw_vector_unique_jobs`
  - `scoring_shortlist_jobs`
  - `backfilled_jobs`
  - `raw_shortlist_anomaly_urls`
  - `backfilled_job_urls`
- shortlist changed-state samples should distinguish:
  - raw-hit anomalies
  - backfilled-for-scoring jobs
  - not-returned-in-raw-hits observations
- run export / debug surfaces should stay job-level and use the same shortlist vocabulary

Likely touchpoints:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`

### Task 6: Add migration and compatibility checks if the retrieval contract needs storage support

If latest-only retrieval requires a new storage field or a stronger sort/tie-break mechanism, add the minimum migration and compatibility logic needed.

Requirements:

- prefer query-only change if possible
- only add storage schema changes if the retrieval contract cannot be implemented safely without them
- document whether existing `job_embeddings` history remains valid under the new query model

### Task 7: Sync source-of-truth docs and generated discovery

Update the relevant source docs once runtime behavior is in place.

Required updates:

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/history.md`
- `docs/stages/shortlist.yaml`
- `docs/FitCV-pipeline.md`

Generated refresh:

- regenerate `docs/generated/feature_overview.md`

## Verification Plan

### Unit and contract tests

- query-builder tests for latest-only retrieval behavior
- shortlist materialization tests for:
  - duplicate historical embedding rows collapsing to one active retrieval candidate
  - duplicate raw rows not duplicating shortlist jobs
  - backfill still adding eligible jobs that raw retrieval missed
  - anomaly URLs remaining separate from valid shortlist entrants
- artifact/export tests for the new shortlist decision-summary fields and changed-state samples

### Regression checks

- current shortlist still operates only within `passed_jobs`
- current persistent embedding writes still happen before retrieval
- backfill still works when raw retrieval misses a passed job
- ranked/debug surfaces remain consistent with the shortlist contract after diagnostics are expanded

## Execution Order

1. Tighten canonical URL handling used by shortlist boundaries.
2. Update shortlist latest-only enforcement per canonical `job_url`.
3. Preserve defensive dedupe and add regression coverage.
4. Expand shortlist runtime diagnostics and changed-state samples.
5. Update run export and inspection surfaces if needed.
6. Add any required migration/compatibility support.
7. Sync docs and regenerate discovery outputs.

## Risks and Notes

- The biggest technical risk is enforcing latest-only behavior in a way that leaves no active row behind if embedding replacement fails midway.
- The biggest semantic risk is conflating "not returned in raw hits" with "storage failure"; artifacts must stay evidence-scoped.
- If canonical URL handling is inconsistent, latest-only retrieval can hide valid rows rather than clarifying retrieval behavior.

## Task Status

- [x] Task 1: Tighten canonical `job_url` handling at shortlist boundaries
- [x] Task 2: Make shortlist latest-only per canonical `job_url`
- [x] Task 3: Keep shortlist-level dedupe as a defensive guard
- [x] Task 4: Preserve backfill but make it more explicit in runtime data
- [x] Task 5: Expand shortlist stage diagnostics and export surfaces
- [x] Task 6: Add migration and compatibility checks if the retrieval contract needs storage support
- [x] Task 7: Sync source-of-truth docs and generated discovery

## Verification Status

- [x] Focused shortlist verification passed:
  - `tests/test_vector_search.py`
  - targeted shortlist slices in `tests/test_pipeline.py`
- [x] `python -m py_compile` passed for touched shortlist/runtime test modules

## Post-Implementation Notes

- This rollout did not require a schema migration because latest-only behavior is enforced by materializing a temporary latest-row shortlist table before `VECTOR_SEARCH`, keeping the final search call in a supported shape.
- The older `raw_vector_hits` field remains present as the unique-job hit count for compatibility, while `raw_vector_unique_jobs` and `raw_vector_unique_jobs_total` now make that meaning explicit.
