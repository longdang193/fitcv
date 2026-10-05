# FitCV P1-A/B Provider-Backed Convergence — Current Head R15

- Source commit: `71cb62ac0928eff89c27515d5cd2ec9c00089754`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Fixture hash, declared executable-input fingerprint, model, runtime, provider provenance, analysis input identity, and seeded cohort setup match.
- Both experiment-bound acceptance verifiers returned `PASSED` using disposable digest-bound verification state; tracked acceptance state was not changed.

## Results

| Metric | `local_first` | `provider_first` |
| --- | ---: | ---: |
| Accepted CVs | 5/10 | 5/10 |
| First-pass acceptance | 0.50 | 0.50 |
| Provider calls | 15 | 15 |
| Tokens | 68675 | 68935 |
| Regenerations | 5 | 5 |
| Generation ms | 341529.0 | 359163.0 |
| End-to-end wall ms | 406194.901 | 420625.831 |
| One-page accepted | 5/5 | 5/5 |
| Validation failures | 5 | 5 |

## Decision

- Paired-arm identity: pass.
- Current committed-head source binding: pass.
- Provider-backed provenance: pass.
- Correctness non-regression: pass; both arms accept 5/10 with identical first-pass and page-fit outcomes.
- Workload cost/latency: provider calls, accepted count, regenerations, validation failures, and page fit tie; candidate changes token and timing totals.
- Optimization promotion: rejected because total-workload improvement is not proven under no-token-increase gate.
- Production default: retain `local_first`.

## Root-Cause Closure

R14 became historical after review fixes changed declared executable inputs. R15 reran after commit `71cb62ac` from one common seeded database with frozen upstream reuse and separate output databases. Analysis identities and cohort setup match; both experiment-bound verifiers pass.

## Evidence

- Manifest and scorecard hashes are recorded in companion JSON.
- Scratch artifacts remain under `.tmp/task7-current-20261005-head-71cb62ac/` and are not staged.
