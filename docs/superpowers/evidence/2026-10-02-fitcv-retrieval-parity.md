# FitCV Retrieval Parity Evidence

Date: 2026-10-02

## Decision

No one-pass channel-scoring rewrite retained. Existing retrieval policy remains production default.

## Proof

- `python -m pytest tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py -q` passed.
- `python scripts/compare_requirement_support.py --help` passed.
- Current production benchmark keeps requirement recall and evidence-pair recall at `1.0` on the frozen fixture.
- No paired implementation benchmark proved a material runtime win without changing the scoring path.

One-pass scoring remains deferred. Do not change retrieval policy, global pool limits, or channel weights without exact candidate, ordering, support, and disambiguation parity plus measured benefit.
