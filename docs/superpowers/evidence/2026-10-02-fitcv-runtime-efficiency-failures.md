# FitCV Runtime Failure And Regeneration Evidence

Date: 2026-10-02

## Workload

Command:

```text
python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-fresh-workload/fitcv.sqlite3 --run-id 5558b199-f6f0-4b85-86a5-fdf71d5deddc --output-json .tmp/task5-baseline.json --output-markdown .tmp/task5-baseline.md
```

Fresh persisted run: `5558b199-f6f0-4b85-86a5-fdf71d5deddc`.

- Attempted generation jobs: `3`
- Provider calls: `5`
- Regenerations: `2`
- Validation failures: `1`
- Accepted CVs: `2`
- Accepted-CV aggregate: `3` provider calls, `16668` tokens, `50235 ms`
- Attribution: complete; unmatched traces `0`; unattributed accepted artifacts `0`

## Root-cause classification

- Both retries use `retry_reason=missing_or_shallow_sections`; no provider timeout, transport, persistence, or cancellation retry occurred.
- One retry produced an accepted CV; one retry still failed grounding validation. Retry work therefore belongs to the acceptance/quality path, not avoidable infrastructure retry waste.
- One failed job had zero approved evidence items. Its content plan correctly excluded unsupported requirements; skipping generation or retry would bypass required section and grounding gates.
- Deterministic profile backfill runs after provider repair. Moving it before repair would change CV content selection for shallow sections and lacks quality-parity evidence.

## Decision

No production retry or regeneration change retained. Existing gates remain unchanged. Revisit only with a paired quality and same-workload benchmark proving deterministic backfill or repair suppression preserves grounding, support, render, and artifact lineage.

The benchmark reader also required a non-runtime fix: fresh SQLite snapshots store debug payloads under `compatibility_json`; the reader now falls back to that canonical snapshot. Regression: `tests/test_benchmark_cv_efficiency.py::test_baseline_reads_debug_payload_from_compatibility_snapshot`.
