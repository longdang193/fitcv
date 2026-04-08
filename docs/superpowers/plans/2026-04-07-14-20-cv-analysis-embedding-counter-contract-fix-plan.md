---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Correct `cv_analysis` embedding counter semantics so stage artifacts stop inflating fresh/reused totals."
---

# CV Analysis Embedding Counter Contract Fix Plan

## Goal

Make `cv_analysis` stage diagnostics trustworthy by removing or correcting stage-level embedding counters that are currently produced by summing cumulative per-record snapshots.

## Task 1 — Trace and lock the current counter scopes

- Audit the exact scope of:
  - per-record `evidence_selection_summary.semantic_alignment.embedding_counts`
  - stage-level `cv_analysis.decision_summary` embedding counters
- Confirm in tests and code comments that per-record counters are record-local runtime-cache snapshots, not stage totals.

## Task 2 — Choose and implement the corrected stage-level contract

- Preferred:
  - compute true per-run aggregate fresh/reused lookup counts from valid deltas or a run-scoped aggregate
- Fallback if needed:
  - remove the four stage-level embedding counters from `cv_analysis.decision_summary`
- In either case, stop summing cumulative per-record snapshots into stage-level totals.

## Task 3 — Clarify naming and semantics

- If stage-level counters remain, rename them to reflect the real counted unit and scope, for example:
  - `candidate_evidence_embedding_lookups_fresh`
  - `candidate_evidence_embedding_lookups_reused`
  - `job_context_embedding_lookups_fresh`
  - `job_context_embedding_lookups_reused`
- Keep per-record `embedding_counts` only if their record-local snapshot semantics remain useful.

## Task 4 — Align run-detail diagnostics with the corrected artifact shape

- Review any control-plane readers of `cv_analysis.decision_summary`
- Ensure run detail and derived diagnostics do not assume the old four fields still exist
- If stage-level counters are removed, keep the UI stable without inventing replacement values.

## Task 5 — Add regression coverage

- Add a focused test with multiple `cv_analysis` records that would previously inflate totals
- Assert that the corrected artifact no longer reports summed cumulative snapshot values
- Add a compatibility test for run-detail readers if the artifact shape changes.

## Task 6 — Sync feature docs and history

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [inspection_debugging history](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [cv_system history](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- Refresh generated discovery docs after source docs change.

## Task 7 — Verify before completion

- Run focused pytest coverage for:
  - `cv_analysis` stage-artifact generation
  - run-detail/control-plane artifact readers that consume `cv_analysis` diagnostics
- Run `python -m py_compile` on touched Python modules
- Re-check one real artifact snapshot to confirm the counter contract is now internally consistent.

