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

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/stages/shortlist.yaml`

## Triage

Feature type: MODIFY  
Summary: Tighten shortlist semantics so the stage behaves as a job-level transform from `passed_jobs` to a scoring shortlist and explains misses without overclaiming causes.  
Reasoning: The shortlist stage already exists, but code inspection and run logs showed drift between the documented boundary, duplicate embedding behavior, and the meanings exposed in artifacts and debug exports.  
Invariants:
- The shortlist stage remains single-chunk job retrieval using `chunk_type = 'job_summary'`.
- `passed_jobs` stays the source-of-truth input set for the scoring shortlist.
- Raw retrieval rows may be diagnostic inputs, but they must not redefine shortlist membership on their own.
- Job-level ranks and counts exposed after shortlist must correspond to unique jobs, not duplicate embedding rows.
- Debug and artifact outputs must clearly separate what was observed from what is inferred.
Dependencies:
- `cv_system`
- `inspection_debugging`
- shortlist runtime in `src/fitcv/pipeline.py`
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
Risk level: medium

## Design Summary

This cleanup keeps the current `job_summary` retrieval strategy but tightens the shortlist contract in four ways:

1. shortlist membership is grounded strictly in `passed_jobs`
2. duplicate embedding rows no longer distort job-level shortlist ranks
3. raw retrieval rows and job-level shortlist rows are counted separately
4. shortlist artifacts and debug payloads describe observed raw-hit facts instead of overstating root causes

## Implemented Direction

- `build_vector_search_query()` now selects the latest active `job_summary` row per `job_url`
- `_dedupe_shortlist_rows()` renumbers shortlist ranks to unique-job order
- `_materialize_scoring_shortlist()` excludes raw hits that do not rejoin `passed_jobs`
- shortlist summary and stage artifacts now distinguish raw row count from unique-job raw-hit count
- shortlist debug wording now uses `not_returned_in_raw_hits` language for observed misses
