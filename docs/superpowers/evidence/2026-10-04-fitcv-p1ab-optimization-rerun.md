# FitCV P1-A/B Optimization Rerun

Date: 2026-10-04

## Decision

Fresh source-bound cohorts resolved Task 7 eligibility. `provider_first` beat
`local_first` on this identical ten-repeat workload, with no acceptance or
page-fit regression. Do not change production default until independent final
review accepts this evidence and the resulting default change.

## Frozen identity

- Source commit: `bfb384fe7b60b968b62f6dc357386387cec5401b`
- Fixture SHA-256: `56d06d363a0d393e19b1fc01c24db88136776bd18211bafdcbb5e04e8f8168b5`
- Declared input fingerprint: `0db5c519f498cf90ebd582ec9f58e70c91af655fdcac9177ba908a59ef252bff`
- Working-tree diff SHA-256: `cea53ab973f474e29226707a0061133b3e861b010b8b839d7b7b7a6abf6da3e1`
- Runtime/model: `fitcv-runtime` / `fixture-model`
- Repeat count: `10` per arm
- Job types: `Contract`, `Part-time`
- Both manifests match on fixture, source, diff, declared input, runtime, model,
  repeat count, and job types. Arm selectors differ only as declared.

## Evidence files

- Incumbent manifest: `.tmp/fitcv-review-202610042220/incumbent-manifest.json`
- Candidate manifest: `.tmp/fitcv-review-202610042220/candidate-manifest.json`
- Incumbent scorecard: `.tmp/fitcv-review-202610042220/incumbent-report.json`
- Candidate scorecard: `.tmp/fitcv-review-202610042220/candidate-report.json`
- Incumbent verifier: `.tmp/fitcv-review-202610042220/incumbent-acceptance.json`
- Candidate verifier: `.tmp/fitcv-review-202610042220/candidate-acceptance.json`

Both benchmark reports returned `complete`. Both experiment-bound acceptance
verifiers returned `PASSED`. Provider credentials loaded from `.env`; no secret
value appears in evidence.

## Comparison

| Metric | `local_first` | `provider_first` | Result |
| --- | ---: | ---: | --- |
| Measurable runs | 10 | 10 | pass |
| Accepted CVs | 7 | 8 | candidate improves |
| First-pass acceptance | 0.40 | 0.70 | candidate improves |
| Provider calls | 16 | 13 | candidate improves |
| Tokens | 73,246 | 59,567 | candidate improves |
| Regenerations | 4 | 1 | candidate improves |
| Generation time (ms) | 195,619 | 149,574 | candidate improves |
| Run wall time (ms) | 447,843.781 | 430,759.423 | candidate improves |
| Accepted final one-page | 7/7 | 8/8 | pass |
| Attribution/coverage | complete | complete | pass |

Candidate reduced provider calls by 7.14%, tokens by 18.68%, generation time
by 23.54%, and run wall time by 3.81% in this rerun. The previous rejection
file remains immutable historical evidence for its older source fingerprint;
this rerun is current-source evidence, not a rewrite of that decision.
