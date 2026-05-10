---
template_id: implementation-plan
document_type: implementation_plan
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
parent_execution_map: none
---

# 2026-05-10 Provider-Agnostic Persistence Patch Plan

## Goal
Deliver full provider-agnostic runtime persistence for FitCV by removing remaining BigQuery-only write paths, centralizing backend-mode resolution, and enabling end-to-end sqlite execution without mandatory GCP credentials.

## Key Deliverables
- Central backend resolver utility replaces duplicated `_sqlite_mode_enabled` checks across persistence modules.
- `gap_analysis.py`, `evidence.py`, and `ai_score.py` support sqlite persistence with schema-compatible payload storage.
- `ingest.py` and run-scoped enrichment persistence stop using sqlite no-op bypasses and perform real sqlite writes.
- Backend-aware config gating requires GCP-only settings only when backend is `bigquery`.
- Verification evidence proves sqlite pipeline runs without `GOOGLE_APPLICATION_CREDENTIALS` and without BigQuery client creation on sqlite paths.

## Task Breakdown
- task 1: baseline and scope lock
  - acknowledge existing red baseline in this worktree (3 known failing tests unrelated to patch scope).
  - define strict touched-file scope for patch lane:
    - `src/fitcv/config.py` (or `src/fitcv/db.py` if backend utility belongs there)
    - `src/fitcv/gap_analysis.py`
    - `src/fitcv/evidence.py`
    - `src/fitcv/ai_score.py`
    - `src/fitcv/ingest.py`
    - `src/fitcv/enrich.py` (only run-scoped sqlite persistence branch)
    - `tests/test_gap_analysis.py`
    - `tests/test_evidence.py`
    - `tests/test_ai_score.py`
    - `tests/test_ingest.py`
    - `tests/test_enrich.py`

- task 2: central backend resolver
  - introduce single source-of-truth backend helper:
    - `resolve_data_backend(config) -> Literal["sqlite", "bigquery"]`
    - `sqlite_mode_enabled(config) -> bool`
    - optional `require_bigquery_mode(config, surface_name)` for fail-fast branch safety.
  - replace per-file env checks with helper usage.
  - ensure helper reads existing canonical setting (`FITCV_CP_DATA_BACKEND`) and preserves current default behavior.

- task 3: sqlite persistence for gap analysis
  - add sqlite table bootstrap for gap-analysis records if missing.
  - implement sqlite insert path in `store_gap_analysis` preserving existing record shape (JSON/text for nested fields).
  - lazy-import BigQuery client and execute BigQuery write only inside explicit bigquery branch.

- task 4: sqlite persistence for evidence selection
  - add sqlite table bootstrap for evidence-selection rows if missing.
  - implement sqlite insert/upsert path in `store_evidence_selection` with stable run/job/evidence identifiers.
  - keep BigQuery path unchanged except branch isolation and lazy-import hardening.

- task 5: sqlite persistence for AI scoring
  - add sqlite table bootstrap for ai-score rows if missing.
  - implement sqlite write path in `store_ai_scores` maintaining score payload fidelity.
  - preserve BigQuery behavior on bigquery branch.

- task 6: ingest/enrich sqlite no-op removal
  - in `ingest.py`, replace sqlite early-return no-op with concrete writes to sqlite raw-jobs table.
  - in `enrich.py`, persist run-scoped enriched/structured job records in sqlite where current path bypasses persistence.
  - retain operational parity for downstream readers relying on these datasets.

- task 7: backend-aware config validation
  - update config validation so GCP credential requirements apply only to bigquery backend.
  - keep explicit, actionable error messages when bigquery mode is selected but credentials/settings missing.
  - confirm sqlite mode does not require `GOOGLE_APPLICATION_CREDENTIALS` or service-account fields.

- task 8: tests and non-regression coverage
  - add/adjust module tests to assert sqlite writes occur for:
    - gap analysis
    - evidence selection
    - ai scoring
    - ingest raw jobs
    - enrich run-scoped records
  - add branch tests ensuring bigquery code path is not invoked in sqlite mode (mock-based assertion).
  - keep existing unrelated failing baseline tests out-of-scope; do not mask them.

- task 9: e2e sqlite validation evidence
  - run targeted test set for touched modules.
  - run focused pipeline path in sqlite mode with GCP env vars unset.
  - confirm expected sqlite tables populated and no BigQuery credential failure occurs.

## Verification
- `& "c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe" -m pytest tests/test_gap_analysis.py tests/test_evidence.py tests/test_ai_score.py tests/test_ingest.py tests/test_enrich.py`
- `& "c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe" -m pytest tests/test_pipeline.py -k "sqlite or backend or ingest or evidence or gap or score"`
- `& "c:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe" scripts/validate_repo_contracts.py --fast`
- optional sqlite smoke (no GCP creds): run one bounded pipeline command/entrypoint with `FITCV_CP_DATA_BACKEND=sqlite` and verify no credential exception.

## Completion Criteria
A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
