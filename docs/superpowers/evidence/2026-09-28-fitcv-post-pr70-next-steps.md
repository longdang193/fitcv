# FitCV Post-PR #70 Evidence

Date: 2026-09-28
Base commit: `ad4a9e11`
Workspace: `main`, uncommitted working tree

## Task 1: Cache Identity

- Embedding and candidate-query cache rows now persist actual producer backend contracts.
- Deterministic fallback identity cannot occupy `sentence_transformers` identity.
- Recovery skips fallback rows and regenerates multilingual vectors.
- Proof: `py -3.13 -m pytest -q tests/test_embeddings.py tests/test_vector_search.py` → `60 passed, 2 skipped`.

## Task 2: Uncertainty Lifecycle

- Resolution endpoint now writes through `sqlite_store_module.save_requirement_resolution`; the previous `client` value was always `None` in `create_app`.
- Worker loader rejects stale profile identity, unknown actions, missing identity, and non-object payload rows.
- Permanent coverage includes `RESOLVE_WITH_ANSWER`, `CONFIRM_OMIT`, `OVERRIDE_BLOCK`, contradiction, malformed rows, duplicate action, refresh failure, fresh analysis/generation, debug replacement, and queue closure.
- Proof: focused lifecycle suite → `832 passed`.
- Refresh failure keeps `review_required`; terminal resolution follows successful fresh validation only.

## P0-A Retrieval Benchmark

Fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`
Fixture SHA-256: `f80f37c407036008a7babc14e6a754cd21d9736373442f4bb2c4a81dba4af0c8`
Workload: 5 warmups, 50 measured iterations, 100 reviewed rows, 80 calibration, 20 held-out.

| Arm | Backend | Held-out Recall@12 | Precision@12 | nDCG@12 | p50 ms | p95 ms | Fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| incumbent | `structured_jobs_lexical` | 0.15 | 1.00 | 0.2345 | 24.52 | 46.00 | 2 |
| lexical | `structured_jobs_lexical` | 0.15 | 1.00 | 0.2345 | 3.80 | 5.75 | 0 |
| multilingual | `sentence_transformers` | 0.15 | 1.00 | 0.2345 | 76.48 | 82.78 | 0 |

Multilingual retrieval does not improve measured held-out quality and is slower than incumbent. Production default remains unchanged. Reports:

- `.tmp/post-pr70-p0a-incumbent.json`
- `.tmp/post-pr70-p0a-lexical.json`
- `.tmp/post-pr70-p0a-multilingual.json`

## P0-B Requirement Support

All three 50-run arms completed with zero validation failures:

- `production`: 17/17 validation cases passed; median total time 2.17 ms.
- `full_pool_diagnostic`: 17/17 validation cases passed; median total time 2.43 ms.
- `lexical_only`: 17/17 validation cases passed; median total time 1.81 ms.
- Benchmark script SHA-256: `de9035f73c19dc40d87376d9068c5be858ae34a3020309e366fe5e5a77d1159b`.

Promotion remains blocked. Manifest records 8 reviewed requirement-evidence pairs, but only three approved relevance seed pairs and insufficient boundary coverage. No model-generated labels were added.

Reports:

- `.tmp/post-pr70-p0b-production.json`
- `.tmp/post-pr70-p0b-full-pool.json`
- `.tmp/post-pr70-p0b-lexical-only.json`
- `.tmp/post-pr70-p0b-comparison.json`

## Deferrals and Rollback

- Accepted-CV economics: unavailable; no authorized live provider/operator workload, accepted-CV denominator, token/cost trace, or manual-review workload was used.
- P1-C, P2, GraphRAG, extra agents, and vector database work: deferred.
- Rollback: disable multilingual strategy, retain incumbent retrieval, preserve P0-C/P1-A/P1-B paths.
- Unrelated `.tmp/` and `.venv/` content remains untouched.

## Final Verification

- Focused lifecycle suite: `832 passed`.
- Benchmark regression suite: `44 passed`.
- Full suite: `2882 passed, 4 skipped, 52 warnings`.
- `git diff --check`: passed.
