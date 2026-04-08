# Shortlist Contract Cleanup Implementation Plan

**Feature:** `docs/features/cv_system/cv_system.yaml`  
**Related Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Stage:** `docs/stages/shortlist.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-01-11-30-shortlist-contract-cleanup-spec.md`  
**Type:** modify  
**Status:** draft  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Tighten the shortlist stage so it remains a single-chunk `job_summary` retrieval design while restoring a strict job-level contract from `passed_jobs` to scoring shortlist rows, eliminating duplicate-row rank drift, and making stage artifacts and export/debug surfaces distinguish observed shortlist facts from retrieval diagnostics.

**Architecture:** This rollout keeps the current candidate-summary-to-`job_summary` retrieval flow but hardens the boundaries around it. The shortlist stage will continue to produce a raw retrieval surface and a scoring shortlist surface, but the scoring shortlist becomes strictly grounded in canonical `passed_jobs`. Retrieval cleanup ensures that shortlist ranking is based on one active `job_summary` embedding row per canonical job identity rather than arbitrary historical duplicates. Artifact and export surfaces are updated so job-level shortlist states remain authoritative while raw retrieval anomalies are visible as diagnostics instead of silently affecting scoring membership.

**Key Invariants:**
- The shortlist stage remains single-chunk job retrieval using `chunk_type = 'job_summary'`.
- The scoring shortlist must only contain canonical jobs from `passed_jobs`.
- Duplicate embedding rows must not distort job-level shortlist counts, ranks, or downstream scoring membership.
- Raw retrieval facts and retrieval hypotheses must remain distinct in artifacts and export/debug payloads.
- Backfill remains allowed only for jobs already present in `passed_jobs`.
- Historical runs do not need to be rewritten.

**Rollout / Revert:**  
- rollback_trigger: shortlist counts, ranks, or export/debug meanings become less trustworthy after cleanup, or the stricter contract unexpectedly drops valid jobs from AI scoring  
- rollback_method: revert the shortlist merge, retrieval filtering, artifact schema updates, and associated tests together so runtime and debug surfaces return to the previous contract

---

## Doc Update Matrix

- Feature contract:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- Stage contracts:
  - `docs/stages/shortlist.yaml`
- Feature history:
  - `docs/features/cv_system/history.md`
  - `docs/features/inspection_debugging/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-04-01-11-30-shortlist-contract-cleanup-spec.md`
- README: `none`
- Generated discovery:
  - `docs/generated/*`

## Stage and Feature Scope

- Affected stages:
  - `shortlist`
- Affected features:
  - `cv_system`
  - `inspection_debugging`
- Primary lens: mixed

## File Structure First

- Modify:
  - `src/fitcv/embeddings.py`
  - `src/fitcv/vector_search.py`
  - `src/fitcv/pipeline.py`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/cv_system/history.md`
  - `docs/features/inspection_debugging/history.md`
  - `docs/stages/shortlist.yaml`
- Test:
  - `tests/test_embeddings.py`
  - `tests/test_vector_search.py`
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`

---

## Task 1: Lock the Shortlist Contract in Tests

**Files:**
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_embeddings.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Add failing shortlist tests that define the strict contract that scoring-shortlist rows must always map back to canonical `passed_jobs`.
- [ ] Step 2: Add failing tests that prove a raw retrieval row without a canonical `passed_jobs` match is excluded from the scoring shortlist and surfaced only as a retrieval anomaly.
- [ ] Step 3: Add failing tests that prove duplicate retrieval rows for the same canonical job URL do not produce misleading job-level shortlist ranks.
- [ ] Step 4: Add failing tests around raw retrieval metrics versus unique-job shortlist metrics so the expected artifact meanings are explicit before implementation.
- [ ] Step 5: Run the failing targeted tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_vector_search.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "shortlist or vector_search"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_embeddings.py`
- [ ] Step 6: Commit if requested.

## Task 2: Canonicalize Shortlist Identity and Enforce the Passed-Jobs Boundary

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_vector_search.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Identify or add one canonical job-URL normalization path used consistently by shortlist joins and retrieval outputs.
- [ ] Step 2: Update `_materialize_scoring_shortlist()` so raw hits that do not rejoin `passed_jobs` are excluded from scoring membership rather than emitted as partial shortlist rows.
- [ ] Step 3: Preserve anomaly visibility by capturing excluded raw-hit URLs in a dedicated retrieval-anomaly diagnostic path.
- [ ] Step 4: Ensure backfill continues to work only for canonical jobs already present in `passed_jobs`.
- [ ] Step 5: Re-run the targeted shortlist merge tests and confirm the stage boundary is now strict.
- [ ] Step 6: Commit if requested.

## Task 3: Make Retrieval Ranking Operate on One Active Row Per Canonical Job

**Files:**
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `tests/test_embeddings.py`
- Modify: `tests/test_vector_search.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Choose the cleanup shape from the spec:
  - retrieval cleanup that queries only one active `job_summary` row per canonical job URL
  - or storage cleanup that replaces prior active rows for the same canonical identity
- [ ] Step 2: Implement the chosen approach so shortlist ranking no longer depends on historical duplicate embedding rows being present.
- [ ] Step 3: Preserve any needed audit/history behavior only if historical rows are excluded from active shortlist ranking.
- [ ] Step 4: Update or add tests that prove repeated embedding writes for the same logical job do not cause sparse job-level ranks in shortlist outputs.
- [ ] Step 5: Re-run targeted retrieval and embedding tests and confirm pass.
- [ ] Step 6: Commit if requested.

## Task 4: Separate Raw Retrieval Facts from Job-Level Shortlist Facts

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Replace or clarify shortlist-stage count fields so raw retrieval row counts and unique-job shortlist counts are not conflated.
- [ ] Step 2: Ensure job-level `vector_rank` exposed after shortlist reflects unique-job ranking, not raw row-order artifacts.
- [ ] Step 3: If raw row-level ranking remains useful, add a clearly named diagnostic-only field rather than reusing the job-level rank field.
- [ ] Step 4: Update tests that assert shortlist JSON blocks now report the new count semantics and rank semantics explicitly.
- [ ] Step 5: Re-run targeted pipeline and worker-job tests that cover shortlist debug payloads and stage artifacts.
- [ ] Step 6: Commit if requested.

## Task 5: Tighten Shortlist Status and Diagnostic Vocabulary in Exports

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update shortlist status helpers so job-facing statuses reflect observed facts such as `returned_by_vector_search`, `backfilled_for_scoring`, and `not_returned_in_raw_hits`.
- [ ] Step 2: Remove or rename fields whose current wording implies stronger causality than the stage can prove.
- [ ] Step 3: Add bounded diagnostic fields for retrieval anomalies and reason codes only where evidence exists.
- [ ] Step 4: Update app and worker tests so admin-facing shortlist debug payloads and run exports match the stricter vocabulary.
- [ ] Step 5: Re-run targeted app, worker, and pipeline tests and confirm pass.
- [ ] Step 6: Commit if requested.

## Task 6: Upgrade the Shortlist Stage Artifact Contract

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `docs/stages/shortlist.yaml`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update the shortlist stage block to report unique-job raw-hit counts, scoring-shortlist counts, backfill counts, and retrieval anomalies with unambiguous names.
- [ ] Step 2: Update `dropped_or_changed_sample` so it distinguishes:
  - absent from raw hits
  - backfilled for scoring
  - raw-hit anomaly excluded from shortlist
- [ ] Step 3: Ensure decision-summary fields describe observed shortlist facts and do not overclaim root causes.
- [ ] Step 4: Update tests that validate shortlist stage artifacts and sample rows against the new contract.
- [ ] Step 5: Re-run targeted pipeline tests that cover stage-transition artifact generation.
- [ ] Step 6: Commit if requested.

## Task 7: Sync Feature Contracts and Histories

**Files:**
- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/inspection_debugging/history.md`
- Modify: `docs/stages/shortlist.yaml`
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Update `cv_system.yaml` so the shortlist capability text reflects the strict job-level shortlist contract and single-chunk `job_summary` retrieval strategy.
- [ ] Step 2: Update `inspection_debugging.yaml` so shortlist artifacts and export surfaces are described using the new facts-versus-diagnostics vocabulary.
- [ ] Step 3: Update `docs/stages/shortlist.yaml` to reflect the tightened stage inputs, outputs, and anomaly semantics.
- [ ] Step 4: Add history entries in both feature histories summarizing the shortlist contract cleanup and any artifact-schema meaning changes.
- [ ] Step 5: Refresh any generated discovery docs required by the repo’s doc workflow.
- [ ] Step 6: Commit if requested.

## Task 8: Run End-to-End Verification and Spot-Check Real Run Semantics

**Files:**
- Modify: `none`
- Verify:
  - `tests/test_embeddings.py`
  - `tests/test_vector_search.py`
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - shortlist-related run JSON expectations in `logs/` when appropriate
- Docs: exact entries from the Doc Update Matrix

- [ ] Step 1: Run the full targeted shortlist verification suite:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_embeddings.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_vector_search.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "shortlist or vector_search or stage_transition_artifacts"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp/test_app.py -k "shortlist or pipeline_status"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp/test_worker_job.py -k "shortlist or artifact"`
- [ ] Step 2: Confirm the new contract removes sparse job-level shortlist ranks caused only by duplicate embedding-row competition.
- [ ] Step 3: Confirm a raw retrieval anomaly is visible diagnostically but cannot silently enter the scoring shortlist.
- [ ] Step 4: Confirm artifact and export/debug status wording now reflects observed facts rather than overclaimed causes.
- [ ] Step 5: Commit if requested.

## Expected Outcome

After this rollout:

- shortlist remains a simple single-chunk job retrieval stage
- the scoring shortlist is strictly grounded in `passed_jobs`
- duplicate embedding rows no longer distort job-level shortlist ranks
- raw retrieval anomalies remain inspectable without silently changing scoring membership
- stage artifacts and admin-facing shortlist debug surfaces clearly separate observed shortlist facts from retrieval diagnostics
