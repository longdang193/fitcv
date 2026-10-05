# FitCV P1-A/B Provider-Backed Convergence — Current Source R2

- Source commit: `ef66aa04180e4dca3271e49ae346b3e7a346fbec`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture, declared executable input, model, runtime, provider provenance, and cold/frozen cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED`.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 10/10 |
| First-pass acceptance | 0.00 | 1.00 |
| Provider calls | 15 | 10 |
| Tokens | 64801 | 47367 |
| Regenerations | 5 | 0 |
| Generation ms | 172072.0 | 106077.0 |
| End-to-end wall ms | 268544.321 | 233251.089 |
| One-page accepted | 5/5 | 10/10 |
| Validation failures | 5 | 0 |

## Decision

- Paired-arm identity: pass.
- Current source binding: pass; executable-input identity remains equal after evidence-only commit.
- Provider-backed provenance: pass.
- Declared executable/input/model/runtime identity: pass.
- Cold-first-then-frozen upstream reuse policy: pass.
- Correctness non-regression: pass for this current run (`10/10` candidate vs `5/10` incumbent).
- Workload cost/latency: candidate lower on provider calls, tokens, generation time, and wall time.
- Optimization decision: pending independent review and explicit default-change approval.
- Production default: retain `local_first` until separately approved.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r4\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r4\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r4\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r4\candidate-benchmark.json`
- Incumbent verifier: `.tmp\fitcv-review-final-20261005-r4\incumbent-acceptance.json`
- Candidate verifier: `.tmp\fitcv-review-final-20261005-r4\candidate-acceptance.json`
