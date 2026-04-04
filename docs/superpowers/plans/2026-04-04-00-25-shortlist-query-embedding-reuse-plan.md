---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Replace unused candidate-chunk embedding work in shortlist with deterministic reuse of the single shortlist query embedding."
invariants:
  - "Shortlist remains a single-query retrieval stage in phase 1."
  - "Shortlist continues to reuse job embeddings by structured signature."
  - "Shortlist retrieval must not depend on candidate chunk embeddings."
  - "Candidate-query embedding reuse must be deterministic and contract-aware."
---

# Shortlist Query Embedding Reuse Plan

## Triage

Feature type: MODIFY  
Summary: Remove unused candidate-chunk embedding from `shortlist` and add deterministic reuse for the single candidate query embedding actually used by shortlist vector retrieval.  
Reasoning: The shortlist stage already owns candidate query construction and vector retrieval. This change keeps the existing single-query retrieval model intact while eliminating wasted candidate-chunk embedding work and adding reuse at the real shortlist boundary. It modifies existing shortlist behavior rather than introducing a new feature family.  
Invariants:
- `shortlist` remains a single-query retrieval stage in phase 1.
- Job embedding reuse by structured signature remains in place and unchanged.
- `shortlist` must not depend on `candidate_embeddings` for vector retrieval.
- Candidate-query embedding reuse must invalidate on query or contract drift.
Dependencies:
- `cv_system`
- `inspection_debugging`
- shortlist runtime in `src/fitcv/pipeline.py`, `src/fitcv/vector_search.py`, and `src/fitcv/embeddings.py`
- BigQuery shortlist retrieval storage/query surfaces
Affected stages:
- shortlist
Affected features:
- cv_system
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: no
Plan needed: yes
Rollback trigger: shortlist retrieval starts serving stale candidate query vectors, candidate-query debug becomes less clear, or shortlist stops producing expected vector results
Rollback method: restore fresh candidate-query embedding generation and re-enable the old candidate-chunk embedding call while leaving additive debug fields inert
Migration needed: maybe
Risk level: medium

## Scope

This plan implements [2026-04-04-00-10-shortlist-query-embedding-reuse-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/superpowers/specs/2026-04-04-00-10-shortlist-query-embedding-reuse-spec.md).

In scope:

- stop generating/storing candidate chunk embeddings as part of shortlist execution
- add deterministic signature + contract fingerprint logic for the single shortlist candidate query embedding
- add a candidate-query embedding cache/read path
- reuse cached candidate query embeddings when the query signature and contract both match
- expose candidate-query reuse state in shortlist debug/artifact surfaces

Out of scope:

- multi-query shortlist retrieval
- embedding-based `cv_analysis` evidence retrieval
- redesigning job embedding reuse
- LLM-based shortlist query generation
- broad candidate-embedding cleanup outside shortlist-owned behavior

## Implementation Tasks

### Task 1: Define the candidate-query embedding contract

Add a code-owned contract for the single shortlist query embedding.

Required fields:

- `candidate_query_signature`
- `candidate_query_contract_fingerprint`
- `candidate_query_text`
- optionally bounded `candidate_query_components_json`

Requirements:

- stable deterministic hashing from bounded candidate-query components
- explicit contract invalidation when shortlist query schema/model changes
- no coupling to job embedding signatures

Likely touchpoints:

- `src/fitcv/vector_search.py`
- `src/fitcv/embeddings.py`

### Task 2: Add deterministic candidate-query signature helpers

Implement helpers that compute a stable shortlist query signature from the already-bounded candidate query components.

Requirements:

- use the existing candidate-query component contract
- normalize and dedupe before hashing
- keep the hash deterministic for the same profile/query inputs
- keep the helper small and shortlist-specific

Likely touchpoints:

- `src/fitcv/vector_search.py`
- shortlist query tests

### Task 3: Add candidate-query contract fingerprinting

Create a dedicated shortlist query embedding contract fingerprint separate from the job-summary embedding contract.

Minimum inputs:

- shortlist embedding model
- candidate query schema/version

Requirements:

- contract drift must force a fresh query embedding
- implementation should be easy to inspect in tests and debug outputs

Likely touchpoints:

- `src/fitcv/embeddings.py`
- `tests/test_embeddings.py`

### Task 4: Add a shortlist query-embedding cache path

Implement a persistence path for the single shortlist candidate query embedding so the stage can reuse it across runs.

Requirements:

- fetch the latest cached query embedding metadata/vector by signature + contract
- generate and store a fresh query embedding only when reuse is invalid
- keep the cache shape logically separate from candidate chunk embeddings
- handle empty or sparse profiles safely

Design note:

- if a new dedicated table is required, include the minimum schema/migration work
- if an existing table is reused, the record type must clearly separate shortlist query embeddings from candidate chunks

Likely touchpoints:

- `src/fitcv/embeddings.py`
- `src/fitcv/vector_search.py`
- BigQuery schema assets and possible migration scripts

### Task 5: Remove candidate-chunk embedding from shortlist execution

Delete the shortlist-stage dependency on `embed_and_store_candidate(profile, config)`.

Requirements:

- shortlist must still build the candidate query text and run vector retrieval successfully
- no stage behavior should still imply that `candidate_embeddings` affect shortlist retrieval
- tests that currently patch `embed_and_store_candidate` for shortlist execution should be updated accordingly

Likely touchpoints:

- `src/fitcv/pipeline.py`
- shortlist pipeline tests

### Task 6: Expose candidate-query reuse in shortlist debug surfaces

Add candidate-query reuse visibility into shortlist stage artifacts and run-level shortlist debug surfaces.

Required fields:

- `candidate_query_reuse_status`
- `candidate_query_signature`
- `candidate_query_contract_fingerprint`
- `candidate_query_text`
- bounded `candidate_query_components`

Requirements:

- clearly distinguish candidate-query reuse from job embedding reuse
- keep fields additive and bounded
- make it obvious in artifacts whether shortlist used a reused or fresh candidate query embedding

Likely touchpoints:

- `src/fitcv/pipeline.py`
- shortlist artifact/sample builders
- shortlist tests

### Task 7: Sync source-of-truth docs and generated discovery

Update docs after runtime behavior is in place.

Required updates:

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/stages/shortlist.yaml`
- `docs/FitCV-pipeline.md`

Generated refresh:

- `docs/generated/feature_overview.md`
- `docs/generated/features_index.yaml`
- `docs/generated/feature_capabilities_index.yaml`

## Verification Plan

### Unit and contract tests

- tests for deterministic candidate-query signature generation
- tests for candidate-query contract fingerprint invalidation
- tests that shortlist reuses cached query embeddings when signature and contract match
- tests that shortlist creates fresh query embeddings when signature or contract differ
- tests proving shortlist no longer calls `embed_and_store_candidate(...)`
- shortlist artifact/debug tests for:
  - `candidate_query_reuse_status`
  - `candidate_query_signature`
  - `candidate_query_contract_fingerprint`

### Regression checks

- shortlist still reuses unchanged job embeddings
- shortlist still runs `VECTOR_SEARCH` with one candidate query vector
- sparse profiles still produce a valid shortlist query and embedding path
- shortlist artifacts clearly distinguish:
  - candidate-query reuse
  - job embedding reuse

## Execution Order

1. Define the candidate-query embedding contract and deterministic signature helpers.
2. Add candidate-query contract fingerprinting.
3. Implement the shortlist query-embedding cache/read-write path.
4. Wire shortlist retrieval to reuse-or-create the candidate query embedding.
5. Remove `embed_and_store_candidate(...)` from shortlist execution.
6. Expose candidate-query reuse details in shortlist artifacts/debug output.
7. Update source-of-truth docs and generated discovery.

## Expected Outcome

After this plan:

- shortlist still uses one candidate query embedding for vector retrieval
- shortlist reuses that query embedding when the candidate query and embedding contract are unchanged
- shortlist no longer spends embedding cost on unused candidate chunks
- operators can tell from the artifact whether shortlist used a fresh or reused candidate query embedding
- job embedding reuse remains unchanged and separately visible
