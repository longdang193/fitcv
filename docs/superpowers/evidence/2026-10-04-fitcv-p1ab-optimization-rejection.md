# FitCV P1-A/B Optimization Experiment Rejection

Date: 2026-10-04

## Decision

Reject `provider_first` promotion. Retain `local_first` as production default.
Both cohorts are comparable and measurable, but candidate correctness and total
workload are worse.

## Frozen identity

- Source commit: `1f9f7e5e27fe9e83275d41e6b6c941015936b72e`
- Fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Declared input fingerprint: `f7ce08cbd38f323adfd128b36a2d9dc2d2205b47c1228afe9efbe316d6a17d0f`
- Working-tree diff SHA-256: `6568bfd0c8daf5d5681de6a419a21e2f4ca812cd28b34ec15eab976438988ae3`
- Runtime/model: `fitcv-runtime` / `fixture-model`
- Repeat count: `10` per arm
- Job types: `Contract`, `Part-time`
- Manifest identity: fixture, source commit, diff, declared inputs, runtime,
  model, repeat count, and job types match across arms.

## Evidence files

- Incumbent manifest: `.tmp/fitcv-incumbent-eligible-20261004211459.json`
- Candidate manifest: `.tmp/fitcv-candidate-eligible-20261004211459.json`
- Incumbent scorecard: `.tmp/fitcv-incumbent-eligible-scorecard-20261004211459.json`
- Candidate scorecard: `.tmp/fitcv-candidate-eligible-scorecard-20261004211459.json`
- Incumbent verifier: `.tmp/fitcv-incumbent-eligibility-20261004211459.json`
- Candidate verifier: `.tmp/fitcv-candidate-eligibility-20261004211459.json`

Manifest-bound benchmark and experiment-bound acceptance verifier both returned
`complete`/`PASSED` for each arm. No secret values appeared in output.

## Comparison

| Metric | `local_first` | `provider_first` | Gate |
| --- | ---: | ---: | --- |
| Measurable runs | 10 | 10 | pass |
| Accepted CVs | 8 | 3 | candidate non-regression fails |
| First-pass acceptance | 0.60 | 0.30 | candidate non-regression fails |
| Provider calls | 14 | 17 | candidate savings fails |
| Tokens | 62,303 | 74,924 | candidate savings fails |
| Regenerations | 4 | 7 | candidate savings fails |
| Generation time (ms) | 177,490 | 215,638 | candidate savings fails |
| Run wall time (ms) | 473,626.95 | 510,340.398 | candidate savings fails |

The result is a measured negative, not an unavailable or incomparable cohort.
No promotion or accepted-state update is authorized.
