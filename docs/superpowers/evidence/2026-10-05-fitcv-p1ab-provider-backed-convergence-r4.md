# FitCV P1-A/B Provider-Backed Convergence — Current Source R4

- Source commit: `0e09ade4d17feaf2af16711779d3cf92526cdff8`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture, declared executable input, model, runtime, provider provenance, and cold/frozen cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED` after expanded runtime, artifact-contract, and prompt-package input binding.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 10/10 |
| First-pass acceptance | 0.00 | 0.00 |
| Provider calls | 15 | 15 |
| Tokens | 69674 | 66903 |
| Regenerations | 5 | 5 |
| Generation ms | 189771.0 | 205748.0 |
| End-to-end wall ms | 282307.396 | 325322.895 |
| One-page accepted | 5/5 | 10/10 |
| Validation failures | 5 | 0 |

## Decision

- Paired-arm identity: pass.
- Current source binding: pass; declared inputs were recomputed from current files.
- Provider-backed provenance: pass.
- Declared executable/input/model/runtime identity: pass.
- Cold-first-then-frozen upstream reuse policy: pass.
- Correctness non-regression: pass; candidate accepts 10/10 versus incumbent 5/10.
- Workload cost/latency: candidate calls tie, tokens decrease, and wall time increases.
- Optimization promotion: rejected.
- Production default: retain `local_first`.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r6\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r6\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r6\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r6\candidate-benchmark.json`
- Incumbent verifier: `.tmp\fitcv-review-final-20261005-r6\incumbent-acceptance.json`
- Candidate verifier: `.tmp\fitcv-review-final-20261005-r6\candidate-acceptance.json`
