# FitCV P1-A/B Provider-Backed Convergence — Current Source R13

- Source commit: `2564e20ec5977668dc0740418e7f7b68ff7e362c`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Seeded database, fixture, declared executable input, model, runtime, provider provenance, and cohort setup match.
- Experiment acceptance verifier passed at current source.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 10/10 | 10/10 |
| First-pass acceptance | 0.50 | 0.50 |
| Provider calls | 15 | 15 |
| Tokens | 70,282 | 70,367 |
| Regenerations | 5 | 5 |
| Generation ms | 216,303.0 | 194,170.0 |
| End-to-end wall ms | 308,266.482 | 285,228.900 |
| One-page accepted | 10/10 | 10/10 |
| Validation failures | 5 | 5 |

## Decision

- Paired-arm identity: pass.
- Seeded cohort setup equality: pass.
- Current source and executable-input binding: pass at `2564e20`.
- Provider-backed provenance: pass.
- Correctness non-regression: pass; both arms accept 10/10.
- Workload cost/latency: candidate lowers generation time by 22,133 ms and wall time by 23,037.582 ms, but increases tokens by 85; calls and regenerations tie.
- Optimization promotion: rejected because total-workload cost gate requires no token increase.
- Production default: retain `local_first`.

## Root-cause correction

Seeded runs previously reused idempotency keys from the seed database. The API replayed old submissions and never enqueued fresh work, producing `acceptance job was not submitted`. The producer now scopes each key to a fresh cohort nonce, routes all submissions through the nonce-bound helper, and regression coverage checks both key isolation and caller binding.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r13\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r13\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r13\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r13\candidate-benchmark.json`
- Acceptance verifier: `.tmp\fitcv-review-final-20261005-r13\candidate-acceptance.json`
