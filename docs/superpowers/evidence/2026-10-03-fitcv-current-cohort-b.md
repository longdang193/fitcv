# FitCV Current Cohort B

- Evidence status: `complete`
- Date: `October 3, 2026`
- Verdict: `current_cohort_observed_no_first_pass_improvement`
- Source commit: `53f95ad0e2f13777e723911521a17e8cac197670`
- Run ID: `4acec250-ff7e-4693-bff7-6fd81b2e4c95`
- Workload: `167` jobs, `15` ranked, `5` attempted generations
- Fixture: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.tmp\current-cohort-20261003-167-fixture.json`
- Fixture SHA-256: `74843e9fd3655d3c3a8f96a60fd98da3a6a78d6144b40289c8d83dcb17c8ceb5`

## Results

| Metric | Current cohort B |
|---|---:|
| Accepted final CVs | 3 |
| First-pass acceptance | `0 / 5 = 0.0%` |
| Accepted final one-page | `3 / 3 = 100%` |
| Review-required artifacts | 1 |
| Review-required action | Rejected; verified `page_count=2` |
| Validation failures | 1 |
| Provider calls, accepted artifacts | 6 |
| Provider calls, attempted workload | 10 |
| Tokens, accepted artifacts | 29,130 |
| Tokens, attempted workload | 45,922 |

All three accepted artifacts required one repair retry. No accepted artifact was
first-pass. Accepted artifacts had native render proof with `page_count=1` and
`page_fit_status=pass`. The review-required artifact was not counted as accepted
after its native render proved `page_count=2` and `page_fit_status=fail`.

## Comparability

This cohort is not comparable to historical `169`-job evidence. It uses a
filtered `167`-job fixture after two uncached LinkedIn enrichment URLs repeatedly
timed out. Historical `5 / 5` accepted final CV evidence remains rejected for
first-pass promotion and is not reclassified by this run.

The first full current run failed before generation because
`src/fitcv/enrich.py:2101` scheduled all enrichment futures and propagated one
provider timeout through `future.result()`, aborting the batch. Current-b uses
seeded enrichment rows and excludes those two URLs. This proves an experiment
boundary failure, not a production first-pass improvement or a basis for a
production timeout-policy patch.

`FITCV_LLM_API_KEY` came from repository `.env` into process environment only;
it was never printed or persisted in evidence.

P1-C remains deferred.
