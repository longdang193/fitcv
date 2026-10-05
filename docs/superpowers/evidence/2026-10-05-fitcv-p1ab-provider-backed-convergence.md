# FitCV P1-A/B Provider-Backed Convergence

- Source commit: `800e349ba7c073765e7579b85e5f7c6a90d9fdff`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture, declared executable input, model, runtime, provider provenance, and cold/frozen cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED`.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 10 | 5 |
| First-pass acceptance | 0.90 | 0.50 |
| Provider calls | 11 | 15 |
| Tokens | 51640 | 64643 |
| Regenerations | 1 | 5 |
| Generation ms | 147749.0 | 174371.0 |
| End-to-end wall ms | 264915.4 | 280744.8 |
| One-page accepted | 10/10 | 5/5 |
| Validation failures | 0 | 5 |

## Decision

- Paired-arm identity: pass.
- Current source binding: pass.
- Provider-backed provenance: pass.
- Declared executable/input/model/runtime identity: pass.
- Cold-first-then-frozen upstream reuse policy: pass.
- Correctness non-regression: fail (`5/10` accepted candidate vs `10/10` incumbent).
- Optimization promotion: rejected.
- Production default: retain `local_first`.
- Downstream analysis identity: informational only; provider output is stochastic and is not an eligibility requirement.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261004-r3\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261004-r3\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261004-r3\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261004-r3\candidate-benchmark.json`
- Incumbent verifier: `.tmp\fitcv-review-final-20261004-r3\incumbent-acceptance.json`
- Candidate verifier: `.tmp\fitcv-review-final-20261004-r3\candidate-acceptance.json`
