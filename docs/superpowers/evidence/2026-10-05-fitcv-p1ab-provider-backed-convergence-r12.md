# FitCV P1-A/B Provider-Backed Convergence — Current Source R12

- Source commit: `81cc412152ac6f39a9bfecc887e9665b7a6eaf09`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Seeded database, fixture, declared executable input, model, runtime, provider provenance, and cohort setup match.
- Candidate and incumbent acceptance verification passed.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 10/10 | 10/10 |
| First-pass acceptance | 0.50 | 0.50 |
| Provider calls | 15 | 15 |
| Tokens | 70,318 | 70,438 |
| Regenerations | 5 | 5 |
| Generation ms | 169,944.0 | 209,026.0 |
| End-to-end wall ms | 252,497.206 | 295,326.243 |
| One-page accepted | 10/10 | 10/10 |
| Validation failures | 5 | 5 |

## Decision

- Paired-arm identity: pass.
- Seeded cohort setup equality: pass.
- Current source and executable-input binding: pass.
- Provider-backed provenance: pass.
- Correctness non-regression: pass; both arms accept 10/10.
- Workload cost/latency: candidate is not better; calls and regenerations tie, tokens increase by 120, generation time increases by 39,082 ms, and wall time increases by 42,829.037 ms.
- Optimization promotion: rejected.
- Production default: retain `local_first`.

## Root-cause correction

Seeded runs previously reused idempotency keys from the seed database. The API replayed old submissions and never enqueued fresh work, producing `acceptance job was not submitted`. The producer now scopes each key to a fresh cohort nonce; regression coverage proves distinct cohorts cannot replay seeded actions.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r12\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r12\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r12\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r12\candidate-benchmark.json`
- Acceptance verifier: `.tmp\fitcv-review-final-20261005-r12\candidate-acceptance.json`
