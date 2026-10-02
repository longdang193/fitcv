# FitCV Runtime Efficiency Convergence

Date: 2026-10-02

## Historical baseline

Command:

```text
python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-live-workload/control_plane.sqlite3
```

Result: `incomplete`.

- Four succeeded ordinary persisted runs selected; one failed run excluded.
- Eleven accepted generation outcomes exist in debug records.
- Zero accepted-artifact events exist in selected persisted snapshots.
- Workload totals remain visible: 34 attempted jobs, 64 provider calls, 293762 tokens, 30 regenerations, 12 validation failures.
- Per-accepted-CV cost is `null`; attribution is not trustworthy.
- No historical or synthetic total promoted as a complete baseline.

## Fresh post-contract evidence

Command:

```text
python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-fresh-workload/fitcv.sqlite3 --run-id 5558b199-f6f0-4b85-86a5-fdf71d5deddc --output-json docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-fresh.json --output-markdown docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-fresh.md
```

Result: `complete`.

- One fresh succeeded ordinary persisted run selected: `5558b199-f6f0-4b85-86a5-fdf71d5deddc`.
- Fifteen CV-generation records: 2 accepted, 12 blocked by reranker fit, 1 validation failure.
- Two accepted-artifact events persisted; both match accepted records by exact `trace_id` and non-null `run_job_id`.
- Attribution counters: `unmatched_trace_count=0`, `unattributed_accepted_artifact_count=0`.
- Workload totals: 3 attempted generation jobs, 5 provider calls, 23485 tokens, 2 regenerations, 1 validation failure, 0 render retries.
- Accepted-CV aggregate: 3 provider calls, 16668 tokens, 50235 ms.
- Per accepted CV: 1.5 provider calls, 8334 tokens, 25117.5 ms.
- Fresh evidence JSON: `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-fresh.json`.

## Final closure verification

Workspace: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT`
Branch: `codex/fitcv-p0-p1-closure-contract`
HEAD: `a26ed2b83b34dcf154b8bb983d49c4703795f5fe`
Base: `6a27b93aa8bed25c6d295d8e08eba06360efe5ea`

- Broad suite: `1648 passed, 1 skipped`.
- Render/compiler acceptance: `4 passed`.
- Acceptance verifier: `p0_b`, `p0_c`, and `p1_b` passed.
- Direct SQLite proof: `2` accepted debug records, `2` accepted artifacts, and `2` `cv_versions` rows; all have non-null `run_job_id` and `trace_id` attribution.
- Benchmark CLI help passed; persisted fresh benchmark remains `complete`.
- Plan target paths exist, merge-marker scan is clean, and `git diff --check` passes.

Verification result: `verified`.

Approved residuals: historical attribution remains incomplete; P1-C and P2 remain deferred; rejected runtime optimizations stay documented. No push, merge, commit, or cleanup performed.

## Post-baseline lineage fix

- Root cause: `merge_scraped_and_enriched()` rebuilt fresh and cache-reused rows without copying `run_job_id`; accepted debug and artifact projections then received `null` despite correct `cv_versions` rows.
- Patch: preserve `run_job_id` at shared enrichment merge owner; both callers use this path.
- Regression proof: `tests/test_enrich.py::test_merge_scraped_and_enriched_preserves_run_job_id`.
- Verification: `25` enrichment tests, `52` late-stage and artifact-contract tests passed; `git diff --check` passed for changed files.
- Fresh persisted workload rerun passed: accepted debug records, accepted artifact events, and `cv_versions` rows carry matching non-null `run_job_id` and `trace_id` values.

## Runtime decisions

- Task 5 failure/regeneration optimization: rejected for now. Fresh evidence shows validation-driven retries, not avoidable transport waste; see `2026-10-02-fitcv-runtime-efficiency-failures.md`.
- Task 6 content-plan reuse: existing fingerprinted reuse retained; `83` generation/reuse tests pass. No new cache or cross-run reuse added.
- Task 7 lazy diagnostics/support: retained. Requirement-support annotation changed from two passes to one; `233` worker/evidence/benchmark tests pass.
- Task 8 one-pass channel scoring: rejected for now. No material parity-preserving win proven; incumbent retrieval remains unchanged.
- Task 9 copy/semantic ablation: lexical-only rejected for evidence-pair loss; deep-copy refactor deferred. See `2026-10-02-fitcv-semantic-ablation.md`.

Only measured support-pass reduction retained. P1-C and P2 stay deferred. Plan closure verified.

## Canonical lineage fix

- Root cause: `_build_cv_generation_trace_summary()` copied embedded trace payloads without restoring run and artifact lineage from the owning debug record.
- Patch: preserve `run_id`, `run_job_id`, `cv_version_id`, `trace_id`, and render fields before projection or benchmark matching.
- Regression: `tests/test_pipeline.py::test_cv_generation_trace_summary_preserves_run_and_artifact_lineage`.
- Fresh workload: run `4f5a73bc-52b7-4221-9aca-0c18642e6005`; 6 accepted artifacts, 0 unmatched traces, 0 unattributed artifacts, 3 canonical job types.
- Canonical evidence pair regenerated at `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.json` and `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.md`.
- Measurement promoted to `measured`: 2 ordinary runs, 3 canonical job types, complete attribution/cost/timing/page-fit/review/human-action/reuse coverage.
- Combined workload: 18 attempted generation jobs, 11 accepted artifacts, 0 unmatched traces, 0 unattributed artifacts.
- P1-C and P2 remain deferred.

## Verification already available

- Relevant suite: `1644 passed, 1 skipped`.
- `python scripts/verify_fitcv_acceptance.py` passed `p0_b`, `p0_c`, and `p1_b`.
- `python -m pytest tests/test_benchmark_cv_efficiency.py` passed `3` tests.
- `python -m pytest -q tests/test_cv_render_acceptance.py` passed `4` tests.
- `python scripts/benchmark_cv_efficiency.py --help` passed.
- `git diff --check` passed before fresh evidence update.
