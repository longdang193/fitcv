# FitCV P1-A/B Provider-Backed Convergence

- Source commit: `4730f9f776f58b1532e3906c87cf867beb976fa0`
- Repeat count: `10` per arm
- Arms: `local_first` incumbent, `provider_first` candidate
- Identical fixture/input/model fingerprints: yes
- Identical analysis input identity: yes

## Results

| Metric | Incumbent | Candidate |
|---|---:|---:|
| Accepted CVs | 10 | 10 |
| First-pass acceptance | 1.00 | 1.00 |
| Provider calls | 10 | 10 |
| Tokens | 44999 | 45043 |
| Regenerations | 0 | 0 |
| Generation ms | 119467.0 | 112335.0 |
| End-to-end wall ms | 247344.1 | 195964.6 |

Both arms: 10/10 accepted, 10/10 first-pass, 10/10 one-page, zero validation failures. Candidate matches provider-call count, uses 44 more tokens, and lowers end-to-end wall time. Production default remains unchanged pending independent review.

## Root Cause

Seeded cohort stabilization incremented `configuration_revision` even when temperatures were already `0.0`. That changed `enrich_contract_fingerprint`, invalidated seeded enrichment, and let fresh upstream LLM output diverge. Stabilization now updates SQLite only when values change.
