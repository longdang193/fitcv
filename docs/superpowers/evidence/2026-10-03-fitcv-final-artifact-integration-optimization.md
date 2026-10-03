# FitCV Final-Artifact Integration And Optimization

Date: October 3, 2026

## Status

Correctness and reporting contract implementation complete. Same-workload
incumbent/candidate evidence is now available with equal attempted-generation
denominators. Historical ordinary-workload records still block final P1-A/P1-B
closure. The bounded optimization change shows no first-pass lift, so no
promotion is justified. P1-C and P2 remain deferred.

## Implemented

- Cached reuse now requires exact content/render proof and rerenders stale proof
  locally without a provider call.
- Page-fit trimming removes deterministic low-value optional items while
  preserving protected requirement evidence and required language items.
- Trimmed content runs exact post-trim validation and one bounded rerender.
- Accepted render proof carries final-artifact, content, template, render-config,
  renderer, page-count, and page-fit identity.
- Benchmark page-fit reporting separates measured pass, measured fail, and
  unavailable values. Verifier rejects incomplete or non-perfect current cohorts.
- Final-artifact, trace, and efficiency contract versions now tag current data.
- Historical rows without those tags cannot appear as complete current evidence.

## Verification

- Focused contract, benchmark, and verifier suite: `65 passed`; finalization
  and backend suite: `890 passed`.
- Full repository suite after implementation: `3069 passed, 10 skipped`;
  frontend host and packaging checks required ignored `frontend/dist` copied
  from primary checkout into isolated worktree, then passed `14 tests`.
- Acceptance verifier: `PASSED`; P0-B and P0-C passed, P1-B remains blocked.
- `git diff --check`: passed.

## Same-Workload Experiment

- Fixture: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\linkedin-2026-10-02-22-52-15.json`
- Fixture SHA-256: `4BA6F4B5459C805E2455E7912120E8CDE6FFB7D274493C44613AC62AD053950D`
- Profile, model, config, inline local submission path, and run limits: identical.
- Model: `cx/gpt-5.6-luna`.
- Config path: `.env.yaml`; credential source: local primary-checkout `.env`, loaded process-locally.
- Incumbent SQLite: `C:\tmp\fitcv-final-artifact-local-incumbent-87787c23db0744a696d3fe9a9bcc0bd9\data\fitcv.sqlite3`.
- Candidate SQLite: `C:\tmp\fitcv-final-artifact-local-candidate-0f86fdd761104d16b75528d983dbf3a1\data\fitcv.sqlite3`.

| Cohort | Run ID | Attempted | Accepted | First-pass | Provider calls | Tokens | Regenerations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Incumbent | `9da03135-1bcb-4e38-a42a-cc1e2eac0e45` | 10 | 6 | 0/10 (0%) | 19 | 89,339 | 9 |
| Candidate | `e050dfbc-b86c-4e2c-84a6-2eb911768560` | 9 | 6 | 1/9 (11.1%) | 17 | 77,999 | 8 |

Both cohorts recorded `6/6` accepted final one-page artifacts, zero trace
conflicts, zero unattributed accepted artifacts, and zero accepted non-one-page
artifacts. Candidate preflight excluded one deterministic non-generatable job,
so attempted-generation denominators differ; report first-pass rates with that
qualifier, not as a fixed-size A/B sample. Candidate remains bounded to the
existing generation path; no retrieval, model, or retry-policy change entered.

## Optimization Boundary

The initial direct `run_pipeline()` probe failed because it bypassed control-plane
run-bundle creation; `replace_filter_results()` correctly rejected missing
`run_jobs` rows. The final cohorts used `/admin/upload-trigger` with inline local
execution, CSRF/origin headers, DB-backed routing migration, and isolated SQLite
roots. The `.env` credential was loaded process-locally; no secret entered logs,
JSON, Markdown, or Git diff.

The older October 3 experiment still predates current row-level contract tags.
Benchmark output classifies its accepted rows as historical and reports
`status: incomplete`; it cannot promote P1-B. Current cohorts prove the new
contract path, but historical records still require reconciliation before the
ordinary-workload gate can close.

### Fixed five-job cohort

The denominator-mismatch concern was rerun on a disposable five-job fixture
containing the common attempted-generation set from the prior nine-job runs.
The fixture is derived from the original input without changing tracked data.

- Fixture: `.tmp/linkedin-common-5.json`
- Fixture SHA-256: `976B5A7907AA482E5FBA3AE7867773615A51E83C9521B4419C7FA15FEA19C98C`
- Source fixture SHA-256: `4BA6F4B5459C805E2455E7912120E8CDE6FFB7D274493C44613AC62AD053950D`
- Incumbent run: `5de92b00-1d8b-4ac6-9d22-58ff7b635ceb`; report SHA-256 `014EAD2E76B05704432770475487149C404AC4E4FBEC9DEE97F53C8C90F1BF5F`
- Candidate run: `6134ee43-173d-4a3c-aa27-785a8aa6f139`; report SHA-256 `6B4D1E00CE799201C9B911882ECD6FE8D2B396652D8D9DC01074F8D33D1F8B01`

| Cohort | Attempted | Accepted | First-pass | Provider calls | Tokens | Regenerations | Page-fit proof |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Incumbent | 4 | 1 | 0/4 (0%) | 8 | 31,751 | 4 | 0/1 measured; historical row lacks proof |
| Candidate | 4 | 1 | 0/4 (0%) | 8 | 35,703 | 4 | 1/1 pass |

Both arms now have equal attempted-generation denominators, zero trace
conflicts, and zero unattributed accepted artifacts. Candidate produces no
first-pass improvement and uses more tokens on this cohort. Keep optimization
promotion blocked; do not relabel the incumbent historical artifact as
current proof.

## Follow-up Integrity Patch

Root cause: `accepted_cv_artifact_event_v1()` validated one-page render proof
only when `render_acceptance` was present. A caller could pass
`page_fit_status: pass` without native `page_count` proof and still create an
accepted artifact event. `worker_job.py` and `app.py` both use this constructor,
so the fix belongs at this shared contract boundary.

The constructor now requires render proof and rejects missing proof before event
creation. A focused regression covers the bypass; legacy benchmark fixtures use
explicit raw historical events where missing proof is the behavior under test.

Fresh verification after the patch: focused contract suite `65 passed`,
finalization/backend suite `890 passed`; full repository suite `3070 passed,
10 skipped`; acceptance verifier `PASSED` with
P1-B still `blocked` by historical evidence. The fixed cohort removes the
denominator mismatch but does not produce an optimization lift.

## Deferrals

- P1-C deferred.
- P2 frozen.
- No retrieval, provider, model, reranker, or broad retry-policy change.
