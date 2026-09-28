# FitCV P0/P1 Residual Closeout

Date: 2026-09-28
Plan: `docs/superpowers/plans/2026-09-28-fitcv-p0-p1-residual-completion-plan.md`
Workspace: `main`, HEAD `f04761a0d8caa800b2a161a662f6468ed7e3830a`

## Result

Plan execution is blocked, not complete. P1-B lifecycle proof and P0-B
benchmark provenance are complete. Multilingual implementation and promotion
claims remain blocked by unavailable local model capability and missing broader
human-reviewed evidence.

## Task status

| Task | Status | Evidence |
| --- | --- | --- |
| Task 1: P1-B lifecycle regression | completed | `826 passed` focused suite; real SQLite resolution save/load, worker refresh, candidate injection, debug identity preservation, queue closure, idempotent replay |
| Task 2: P0-B reviewed evidence | blocked | `98 passed`; production/full-pool/lexical reports and comparison generated; existing manifest still records broader reviewed-label blocker |
| Task 3: multilingual adapter | blocked | `66 passed, 2 skipped`; `sentence_transformers` and `torch` unavailable; target model not cached; no provider/model download attempted |
| Task 4: P0-A promotion evidence | blocked | incumbent and lexical measured; multilingual report is `not_run` with reason `approved multilingual retrieval backend unavailable` |
| Task 5: P1 scorecard | completed | generation-focused suite `230 passed`; offline, partial, `not_run`, and `not_applicable` states recorded here |
| Task 6: final reconciliation | blocked | full suite passes; required external evidence remains unavailable |

## P0-A

Fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`.

- Fixture SHA-256: `f80f37c407036008a7babc14e6a754cd21d9736373442f4bb2c4a81dba4af0c8`.
- Corpus: 100 reviewed rows; 80 calibration, 20 held-out; 40 DE and 40 EN calibration rows plus 10 DE and 10 EN held-out rows.
- Incumbent: held-out Recall@12 `0.15`, Precision@12 `1.0`, nDCG@12 `0.2345000467`, latency p50/p95 `23.8996/47.2529 ms`, fallback count `2`.
- Lexical: held-out Recall@12 `0.15`, Precision@12 `1.0`, nDCG@12 `0.2345000467`, latency p50/p95 `3.3968/3.6887 ms`, fallback count `0`.
- Multilingual: `not_run`; reason `approved multilingual retrieval backend unavailable`.
- Decision: retain incumbent production contract. Do not promote lexical or multilingual from this evidence.
- Reports: `.tmp/p0a-incumbent-residual.json`, `.tmp/p0a-lexical-residual.json`, `.tmp/p0a-multilingual-residual.json`.

## P0-B

Fixture: `tests/fixtures/requirement_support_benchmark.json`.

- Fixture SHA-256: `58acd4396905dc6b5b1c33c50b91c5eebc27c49db1abf35fb14dd20854bc977b`.
- All three arms: selected requirement recall `1.0`, selected evidence-pair recall `1.0`, validation `17/17`, failed `0`, skipped `0`, not-applicable `0`.
- Reports include commit SHA, benchmark script SHA-256, policy hash version, fixture hash, dataset size `16`, arm, warmups `5`, measured runs `50`, and validation counts.
- Comparison: production vs full-pool diagnostic is non-decreasing for qualified requirement and evidence-pair recall; false qualified pairs `0`.
- Existing reviewed evidence manifest remains `promotion_blocked: true`: only 8 reviewed pairs, 2 source postings, and insufficient boundary coverage for promotion-grade claims.
- Reports: `.tmp/p0b-production-residual.json`, `.tmp/p0b-full-pool-residual.json`, `.tmp/p0b-lexical-only-residual.json`, `.tmp/p0b-comparison-residual.json`.

## P1 scorecard

| Metric | Status | Evidence |
| --- | --- | --- |
| Approved/full evidence counts, characters, token estimates | measured | existing generation traces and `230` focused tests |
| Full/section repair | measured | bounded section repair tests preserve unaffected sections and rerun validation |
| Resolution reuse and stale scoping | measured | profile/revision/source-fingerprint loader and lifecycle regression |
| Review actions and accepted-CV rate | not_run | no live operator/provider workload authorized |
| Provider calls and provider input/output tokens | not_run | offline-only execution |
| Local input-token estimates | partial | traces and offline benchmark payloads only |
| Questions avoided | not_run | no paired live workload |
| Accepted-CV economics | not_applicable | no live accepted-CV denominator or provider cost |

## Verification

- `py -3.13 -m pytest -q` — `2869 passed, 4 skipped, 52 warnings`.
- `py -3.13 -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py` — `826 passed`.
- `py -3.13 -m pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py` — `98 passed`.
- `py -3.13 -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_ranking_evaluation.py` — `66 passed, 2 skipped`.
- `py -3.13 -m pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_cv_generation_reason_mapping.py` — `230 passed`.
- `git diff --check` — clean.
- `uv run` validation unavailable after accidental WSL `.venv` layout mutation; Windows-native `py -3.13` provided equivalent local proof. `.venv/` and `.tmp/` remain preserved as workspace artifacts.

## Blockers and rollback

- Unblock Task 2 with broader human-reviewed P0-B boundary labels and approved provenance.
- Unblock Task 3 with approved installation/loading of `sentence-transformers` plus pinned `paraphrase-multilingual-MiniLM-L12-v2` revision.
- Unblock Task 4 by rerunning multilingual arm after Task 3 and retaining incumbent unless held-out thresholds pass.
- Rollback: revert benchmark metadata/test changes; retain incumbent retrieval and existing P1 runtime paths; discard only residual `.tmp/` reports after evidence retention decision.

## Deferred

P1-C, P2, GraphRAG, extra agents, vector-database infrastructure, live provider
economics, and production retrieval promotion remain deferred.
