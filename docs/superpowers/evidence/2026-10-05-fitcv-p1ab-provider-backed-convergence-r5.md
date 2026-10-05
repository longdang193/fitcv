# FitCV P1-A/B Provider-Backed Convergence — Current Source R5

- Source commit: `72d8f57902b9faaa924c78e2d1229c970136f0bd`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture, declared executable input, model, runtime, provider provenance, and cold/frozen cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED` after expanded runtime, artifact-contract, and prompt-package input binding.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 10/10 |
| First-pass acceptance | 0.00 | 0.50 |
| Provider calls | 20 | 15 |
| Tokens | 92653 | 69911 |
| Regenerations | 10 | 5 |
| Generation ms | 270472.0 | 191211.0 |
| End-to-end wall ms | 377004.992 | 334256.013 |
| One-page accepted | 5/5 | 10/10 |
| Validation failures | 5 | 0 |

## Decision

- Paired-arm identity: pass.
- Current source binding: pass; declared inputs were recomputed from current files.
- Provider-backed provenance: pass.
- Declared executable/input/model/runtime identity: pass.
- Cold-first-then-frozen upstream reuse policy: pass.
- Correctness non-regression: pass; candidate accepts 10/10 versus incumbent 5/10.
- Workload cost/latency: candidate uses fewer calls, tokens, and wall time in this rerun.
- Optimization promotion: rejected.
- Production default: retain `local_first`.

## Evidence

- Incumbent manifest: `.tmp\fitcv-review-final-20261005-r8\incumbent-manifest.json`
- Candidate manifest: `.tmp\fitcv-review-final-20261005-r7\candidate-manifest.json`
- Incumbent scorecard: `.tmp\fitcv-review-final-20261005-r8\incumbent-benchmark.json`
- Candidate scorecard: `.tmp\fitcv-review-final-20261005-r7\candidate-benchmark.json`
- Incumbent verifier: `.tmp\fitcv-review-final-20261005-r8\incumbent-acceptance.json`
- Candidate verifier: `.tmp\fitcv-review-final-20261005-r8\candidate-acceptance.json`
