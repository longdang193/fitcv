# Shortlist Contract Cleanup Implementation Plan

**Feature:** `docs/features/cv_system/cv_system.yaml`  
**Related Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Stage:** `docs/stages/shortlist.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-01-11-30-shortlist-contract-cleanup-spec.md`  
**Type:** modify  
**Status:** in_progress  

**Goal:** Tighten the shortlist stage so it remains a single-chunk `job_summary` retrieval design while restoring a strict job-level contract from `passed_jobs` to scoring shortlist rows, eliminating duplicate-row rank drift, and making stage artifacts and export/debug surfaces distinguish observed shortlist facts from retrieval diagnostics.

## Doc Update Matrix

- Feature contract:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- Stage contracts:
  - `docs/stages/shortlist.yaml`
- Feature history:
  - `docs/features/cv_system/history.md`
  - `docs/features/inspection_debugging/history.md`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-04-01-11-30-shortlist-contract-cleanup-spec.md`
- Generated discovery:
  - `docs/generated/*`

## Task Status

- [x] Task 1: Lock the shortlist contract in tests
- [x] Task 2: Canonicalize shortlist identity enough to enforce the passed-jobs boundary at runtime
- [x] Task 3: Make retrieval ranking operate on one active row per job URL by querying only the latest `job_summary` row
- [x] Task 4: Separate raw retrieval facts from unique-job shortlist facts
- [x] Task 5: Tighten shortlist status and diagnostic vocabulary in exports
- [x] Task 6: Upgrade the shortlist stage artifact contract
- [x] Task 7: Sync feature contracts, stage contract, spec, plan, and histories
- [ ] Task 8: Refresh generated discovery docs

## Verification Status

- [x] `tests/test_vector_search.py`
- [x] `tests/test_pipeline.py -k "shortlist or vector_search or stage_transition_artifacts"`
- [x] `tests/test_fitcv_cp/test_worker_job.py`
- [ ] `tests/test_fitcv_cp/test_app.py`

`tests/test_fitcv_cp/test_app.py` still has one unrelated failure in `test_run_detail_enriched_shows_summary_counts`, which does not exercise shortlist behavior directly.
