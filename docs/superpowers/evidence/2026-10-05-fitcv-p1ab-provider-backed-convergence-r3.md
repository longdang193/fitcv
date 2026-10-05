# FitCV P1-A/B Provider-Backed Convergence — Current Source R3

- Source commit: `7f351da9250d62ccc750d4dfceb4c7729d5bbee1`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture, declared executable input, model, runtime, provider provenance, and cold/frozen cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED`.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 5/10 |
| First-pass acceptance | 0.00 | 0.00 |
| Provider calls | 20 | 20 |
| Tokens | 82475 | 92827 |
| Regenerations | 10 | 10 |
| Generation ms | 209400.0 | 260831.0 |
| End-to-end wall ms | 312401.973 | 369055.862 |
| One-page accepted | 5/5 | 5/5 |
| Validation failures | 5 | 5 |

## Decision

- Paired-arm identity: pass.
- Current source binding: pass; declared inputs were recomputed from current files.
- Provider-backed provenance: pass.
- Declared executable/input/model/runtime identity: pass.
- Cold-first-then-frozen upstream reuse policy: pass.
- Correctness non-regression: pass; both arms accept 5/10.
- Workload cost/latency: candidate is not lower; calls tie, tokens and wall time increase.
- Optimization promotion: rejected.
- Production default: retain `local_first`.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r5\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r5\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r5\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r5\candidate-benchmark.json`
- Incumbent verifier: `.tmp\fitcv-review-final-20261005-r5\incumbent-acceptance.json`
- Candidate verifier: `.tmp\fitcv-review-final-20261005-r5\candidate-acceptance.json`
