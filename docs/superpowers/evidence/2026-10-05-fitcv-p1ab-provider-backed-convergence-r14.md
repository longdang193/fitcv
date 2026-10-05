# FitCV P1-A/B Provider-Backed Convergence — Pre-Fix Current Head R14

- Source commit: `d35a9368f02d297ab2f58df31c68bf1cab60d005`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture hash, declared input fingerprint, model, runtime, provider provenance, analysis input identity, and cohort setup match.
- Both experiment-bound acceptance verifiers passed.
- This receipt is historical after later review fixes changed declared inputs; it
  does not close the post-fix current-head gate.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 5/10 |
| First-pass acceptance | 0.50 | 0.50 |
| Provider calls | 15 | 15 |
| Tokens | 68,394 | 68,418 |
| Regenerations | 5 | 5 |
| Generation ms | 194,388.0 | 188,270.0 |
| End-to-end wall ms | 262,235.118 | 257,714.159 |
| One-page accepted | 5/5 | 5/5 |
| Validation failures | 5 | 5 |

## Decision

- Paired-arm identity: pass.
- Common seeded cohort setup equality: pass.
- Current source and executable-input binding: pass at `d35a9368f02d297ab2f58df31c68bf1cab60d005`.
- Provider-backed provenance: pass.
- Correctness non-regression: pass; both arms accept 5/10 with identical first-pass and page-fit outcomes.
- Workload cost/latency: candidate lowers generation time by 6,118.0 ms and wall time by 4,520.959 ms, but increases tokens by 24; calls and regenerations tie.
- Optimization promotion: rejected because total-workload cost gate requires no token increase.
- Production default: retain `local_first`.

## Root-Cause Correction

Cold isolated arms were not comparable: analysis-stage selection produced different evidence identities even with equal declared fixture inputs. A seeded provider-only rerun matched analysis identity, proving upstream state was the cause. Final R14 uses one common seed database for both arms, frozen upstream reuse, and separate output databases/manifests; both paired gates pass.

## Evidence

- Incumbent and candidate manifest/scorecard hashes are recorded in companion JSON.
- Scratch artifacts remain under `.tmp/task7-current-20261005/` and are not staged.
