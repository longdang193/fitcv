# FitCV P0/P1 Residual Closeout

Date: 2026-09-28
Plan: `docs/superpowers/plans/2026-09-28-fitcv-p0-p1-residual-completion-plan.md`
Workspace: `codex/fitcv-p0-p1-residual`, implementation commit `2bfd58ff`

## Result

Plan execution remains blocked only on P0-B broader human-reviewed boundary
coverage. P1-B lifecycle proof, P0-B benchmark provenance, multilingual adapter
implementation, and P0-A measurement are complete. Production retrieval remains
unchanged because multilingual quality did not exceed incumbent quality.

## Task status

| Task | Status | Evidence |
| --- | --- | --- |
| Task 1: P1-B lifecycle regression | completed | `826 passed` focused suite; real SQLite resolution save/load, worker refresh, candidate injection, debug identity preservation, queue closure, idempotent replay |
| Task 2: P0-B reviewed evidence | blocked | `98 passed`; production/full-pool/lexical reports and comparison generated; existing manifest still records broader reviewed-label blocker |
| Task 3: multilingual adapter | completed | optional lazy `sentence_transformers` backend; pinned CPU packages `sentence-transformers==6.1.0`, `torch==2.14.0`; model revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`; `70 passed, 2 skipped` focused suite |
| Task 4: P0-A promotion evidence | completed | incumbent, lexical, and multilingual arms measured on identical 100-row DE/EN fixture; no production promotion |
| Task 5: P1 scorecard | completed | generation-focused suite `230 passed`; offline, partial, `not_run`, and `not_applicable` states recorded here |
| Task 6: final reconciliation | blocked | full suite passes; required external evidence remains unavailable |

## P0-A

Fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`.

- Fixture SHA-256: `f80f37c407036008a7babc14e6a754cd21d9736373442f4bb2c4a81dba4af0c8`.
- Corpus: 100 reviewed rows; 80 calibration, 20 held-out; 40 DE and 40 EN calibration rows plus 10 DE and 10 EN held-out rows.
- Incumbent: held-out Recall@12 `0.15`, Precision@12 `1.0`, nDCG@12 `0.2345000467`, latency p50/p95 `24.1812/25.6758 ms`, fallback count `2`.
- Lexical: held-out Recall@12 `0.15`, Precision@12 `1.0`, nDCG@12 `0.2345000467`, latency p50/p95 `3.2722/3.6981 ms`, fallback count `0`.
- Multilingual: held-out Recall@12 `0.15`, Precision@12 `1.0`, nDCG@12 `0.2345000467`, latency p50/p95 `84.5890/93.5632 ms`, fallback count `0`; backend `sentence_transformers`, model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, dimension `384`, revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
- Decision: retain incumbent production contract. Multilingual adds no held-out quality gain and is slower; lexical and multilingual remain benchmark-only.
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

- `py -3.13 -m pytest -q` — `2873 passed, 4 skipped, 52 warnings`.
- `py -3.13 -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_agentic_cv_analysis.py tests/test_cv_generation_reason_mapping.py` — `826 passed`.
- `py -3.13 -m pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py` — `98 passed`.
- `py -3.13 -m pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_ranking_evaluation.py` — `70 passed, 2 skipped`.
- `.tmp/p0a-multilingual-venv/Scripts/python.exe` model smoke — 384-dimensional embedding generated with pinned model revision.
- `py -3.13 -m pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_cv_generation_reason_mapping.py` — `230 passed`.
- `git diff --check` — clean.
- `uv run` validation unavailable after accidental WSL `.venv` layout mutation; Windows-native `py -3.13` provided equivalent local proof. `.venv/` and `.tmp/` remain preserved as workspace artifacts.

## Blockers and rollback

- Unblock Task 2 with broader human-reviewed P0-B boundary labels and approved provenance.
- Rollback: revert benchmark metadata/test changes; retain incumbent retrieval and existing P1 runtime paths; discard only residual `.tmp/` reports after evidence retention decision.

## Deferred

P1-C, P2, GraphRAG, extra agents, vector-database infrastructure, live provider
economics, and production retrieval promotion remain deferred.
