# FitCV First-Pass Experiment

- Evidence status: `complete`
- Date: `October 3, 2026`
- Verdict: `candidate_rejected_for_first_pass_promotion`
- Fixture: `data/linkedin-2026-10-02-22-52-15.json`
- Fixture SHA-256: `4ba6f4b5459c805e2455e7912120e8cde6ffb7d274493c44613ac62ad053950d`
- Config: `.env.yaml`
- Candidate profile: `sanitized_candidate_profile`
- Model: `cx/gpt-5.6-luna`
- Workload: `169` jobs, `15` ranked, `8` attempted generations per arm

## Results

| Metric | Incumbent | Candidate |
|---|---:|---:|
| Source | `039a5ee625799f44734fe7dc3e732b7659c126c5` | merged tree `cfeed507ed28a08c35df48cefaf7c87af0a2a467` |
| Run ID | `606d0751-970f-4ac8-9b9a-76026dd1b7b6` | `940ff9ba-e86a-49e4-8107-e7ef2593892c` |
| Accepted final CVs | 5 | 5 |
| First-pass acceptance | `0 / 8 = 0.0%` | `0 / 8 = 0.0%` |
| Retry success / failure | 5 / 3 | 5 / 3 |
| Provider calls | 16 | 16 |
| Tokens | 71,854 | 76,152 |
| Regenerations | 8 | 8 |
| Terminal validation failures | 3 | 3 |
| Accepted-artifact calls per CV | 2.0 | 2.0 |
| Accepted-artifact tokens per CV | 9,672.2 | 10,331.2 |
| Total-workload calls per CV | 3.2 | 3.2 |
| Total-workload tokens per CV | 14,370.8 | 15,230.4 |
| Accepted final one-page | not recorded | `5 / 5 = 100%` |
| Trace conflicts | 0 | 0 |
| Unattributed accepted artifacts | 0 | 0 |
| Generation-format defects | 5 | 5 |

Candidate preserves final-artifact and reporting integrity gates. Candidate does
not improve first-pass acceptance over this identical workload. Candidate also
uses `5.98%` more tokens, with generation elapsed time up `12.42%`; no promotion
claim is allowed for first-pass optimization.

## Hard Gates

- Same fixture, profile, model, config, run mode: `PASS`
- Unsupported claims in accepted artifacts: `0`, `PASS`
- Accepted final page-fit success: `100%`, `PASS`
- Trace conflicts: `0`, `PASS`
- Unattributed accepted artifacts: `0`, `PASS`
- First-pass rate increased: `NO`, `FAIL`
- Promotion: `REJECTED`

## Durable Inputs

- Detailed machine-readable evidence: `docs/superpowers/evidence/2026-10-03-fitcv-first-pass-experiment.json`
- Database paths: omitted from committed evidence.

P1-C and P2 remain deferred. No production retrieval, provider, model, or retry
policy change follows from this experiment.
