---
layer: change
artifact_type: plan
status: proposed
parent_spec: docs/superpowers/specs/2026-05-03-pipeline-efficiency-exact-match-contract-bootstrap-spec.md
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
---

# Pipeline Efficiency Exact Match Bootstrap Plan

1. [x] Confirm exact-match eligibility fields and hash strategy.
   - confirmed shortlist reuse uses deterministic candidate-query component payloads with a SHA-256 signature plus a separate contract fingerprint
   - confirmed reranker reuse uses job URL + rendered prompt + ranking contract fingerprint
   - confirmed `cv_analysis` reuse uses normalized profile/job payloads + `cv_analysis` contract fingerprint
2. [x] Define invalidation triggers and evidence persistence requirements.
   - shortlist invalidates on signature drift or contract-fingerprint drift; latest stored matching row wins
   - reranker invalidates on prompt drift, job URL drift, or ranking-contract drift
   - `cv_analysis` invalidates on normalized profile drift, normalized job-context drift, or `cv_analysis` contract drift
   - exact-match `cv_analysis` reuse requires persisted full analysis snapshots; evidence-selection rows alone are insufficient
3. [x] Add deterministic tests for cache-hit, cache-miss, and stale-cache paths.
   - verified shortlist cache hit, stale contract, and cache miss in `tests/test_vector_search.py::test_resolve_candidate_query_embedding_reuses_or_refreshes_cache`
   - verified ranking exact-match hit, missing-snapshot fallback, and stale-fingerprint fallback in `tests/test_pipeline.py`
   - verified `cv_analysis` exact-match hit, missing-snapshot fallback, and stale-fingerprint fallback in `tests/test_pipeline.py`
   - checkpoint evidence: `docs/intent/workstreams/checkpoints/workstream-pipeline-efficiency-and-reuse/efficiency-reuse-exact-match-contract/20260508-1644.md`
