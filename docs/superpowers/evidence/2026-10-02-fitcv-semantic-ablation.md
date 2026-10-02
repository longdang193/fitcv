# FitCV Semantic Ablation Evidence

Date: 2026-10-02

Fixture: `tests/fixtures/requirement_support_benchmark.json`, `3` measured runs, `1` warmup.

| Arm | Total median ms | Retrieval median ms | Selected requirement recall | Selected evidence-pair recall | Validation |
| --- | ---: | ---: | ---: | ---: | ---: |
| `production` | `1.8132` | `0.4753` | `1.0` | `1.0` | `17/17` |
| `current-hash` | `2.1510` | `0.5895` | `1.0` | `1.0` | `17/17` |
| `lexical_only` | `1.5235` | `0.1189` | `1.0` | `0.9375` | `17/17` |

## Copy profile

Representative frozen fixture run measured `64` `deepcopy` calls, `24981` copied payload bytes, and `14.388 ms` total execution across `16` scenarios: `4` calls and `1561.3` bytes per scenario on average.

## Decision

- Keep incumbent production/hybrid behavior.
- Reject lexical-only production substitution: faster, but loses one evidence pair (`0.9375` recall).
- Defer deep-copy refactor: measured cost is small and no parity-preserving win was proven.
