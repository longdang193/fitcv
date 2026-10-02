# FitCV P0/P1 Contract Closure Evidence

Date: 2026-10-02
Base HEAD: `6a27b93aa8bed25c6d295d8e08eba06360efe5ea`
Workspace: current worktree, intentionally uncommitted under approved no-commit execution
Plan: `docs/superpowers/plans/2026-10-02-fitcv-p0-p1-closure-contract-plan.md`

## Scope

Closed three narrow contract defects without changing architecture:

- P0-B now classifies full requirement/evidence pairs. Known requirements with unknown evidence remain unexpected assignments.
- P0-C no longer treats generic `science` token overlap as proof that Political Science is related to Computer Science.
- P1-B normalizes trace identity before deduplication, carries `run_job_id`, and prevents same-run job collisions.
- Acceptance Verifier runs bounded contract checks, prints failure summaries, and CI uploads reports with `if: always()`.

P0-A remains rejected. P1-A remains maintenance-only. P1-C and P2 remain deferred.

## Proof

Focused contract tests:

```text
python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_acceptance_verifier.py
```

Task-specific results:

- P0-C: `122 passed` in `tests/test_evidence.py tests/test_agentic_cv_analysis.py`.
- P0-B: `22 passed, 4 skipped`; frozen runtime evaluator eligible with assignment precision `1.0`, zero unexpected assignments, and zero unsupported assignments.
- P1-B: `815 passed` across run artifact, worker, app, and SQLite contract tests.
- Acceptance Verifier: exit `0`; P0-B, P0-C, and P1-B passed; stdout includes current commit and priority status.
- Render Acceptance: `4 passed`.
- Full Suite: `3015 passed, 8 skipped, 4 deselected`.
- `git diff --check`: passed.

## P1-B Measurement

Existing sanitized live workload remains authoritative for effort totals:

- `accepted_cv_effort_v1` denominator: `11` accepted CVs.
- Attempted jobs: `17`; validation failures: `6`.
- Provider calls: `20`; tokens: `101808`; regenerations: `9`.
- Review questions: `34`; human actions: `not_applicable` for automatic acceptances.
- Total CV elapsed time: `291659 ms`; page fit: `11 / 11` one-page renders.

Contract regressions additionally prove duplicate top-level/embedded traces count once and two `run_job_id` values in one `run_id` remain distinct.

## CI Retention

`.github/workflows/repo-hooks.yml` uploads these paths after the verifier with
`if: always()`:

- `.tmp/fitcv-acceptance-report.json`
- `.tmp/p0b-runtime-acceptance-verifier.json`

No performance improvement claim is made. Optimization remains follow-up work
after larger protected normal-use measurement.
