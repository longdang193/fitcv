---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Replace unused candidate-chunk embedding work in shortlist with deterministic reuse of the single shortlist query embedding."
invariants:
  - shortlist remains a single-query retrieval stage in phase 1
  - shortlist continues to reuse job embeddings by structured signature
  - shortlist retrieval must not depend on candidate chunk embeddings
  - candidate-query embedding reuse must be deterministic and contract-aware
---

# Shortlist Query Embedding Reuse Spec

## Summary

Optimize `shortlist` by stopping eager candidate-chunk embedding work that the stage does not consume, and instead add explicit reuse for the single shortlist query embedding derived from `candidate_query_text`.

This keeps the current retrieval model:

- one deterministic candidate query text
- one candidate query embedding
- `VECTOR_SEARCH` over reusable job embeddings

but removes wasted candidate-chunk embedding cost from `shortlist`.

## Problem

`shortlist` currently performs two different candidate-side embedding actions:

1. it embeds the deterministic `candidate_query_text` and uses that vector for `VECTOR_SEARCH`
2. it also calls `embed_and_store_candidate(profile, config)` and writes candidate chunks into `candidate_embeddings`

Only the first action is actually used by shortlist retrieval.

Today:

- shortlist retrieval in [`run_vector_search()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/vector_search.py) uses one fresh embedding of `candidate_query_text`
- shortlist does not query `candidate_embeddings`
- `cv_analysis` evidence retrieval also does not query `candidate_embeddings` today

So the current stage does unnecessary work:

- candidate chunk embeddings are generated
- candidate chunk embeddings are stored
- but those stored vectors do not affect shortlist ranking

This creates three problems:

- unnecessary embedding cost per run
- confusing pipeline behavior because stored candidate embeddings look important but are unused here
- missing reuse at the actual shortlist retrieval boundary, which is the single candidate query embedding

## Goals

- Remove wasted candidate-chunk embedding work from `shortlist`
- Keep shortlist retrieval centered on one deterministic candidate query text
- Add explicit reuse for the single candidate query embedding actually used by `VECTOR_SEARCH`
- Make shortlist artifacts/debug surfaces clearly show whether the candidate query embedding was reused or freshly created
- Preserve current job-embedding reuse behavior unchanged

## Non-Goals

- Switching shortlist to multi-query candidate retrieval
- Making shortlist use candidate chunk embeddings directly
- Replacing `cv_analysis` evidence retrieval in this change
- Reworking job embedding reuse semantics
- Introducing LLM-based query generation

## Current State

In the current shortlist flow:

1. [`pipeline.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/pipeline.py) calls:
   - `embed_and_store_jobs(passed_jobs, config)`
   - `embed_and_store_candidate(profile, config)`
2. [`run_vector_search()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/vector_search.py) builds `candidate_query_text`
3. shortlist generates a fresh embedding for that text
4. shortlist uses that single vector in `VECTOR_SEARCH`

Job embedding reuse already exists and is visible in shortlist artifacts through fields like:

- `embedding_reused_jobs`
- `embedding_fresh_jobs`
- per-row `embedding_reuse_status`

But candidate-query embedding reuse does not exist today, and candidate chunk embeddings are not surfaced as meaningful shortlist inputs because they are not actually used for retrieval.

## Proposed Design

### 1. Keep shortlist retrieval as one query embedding

`shortlist` should continue to use one deterministic candidate query string produced from:

- headline
- target role
- recent roles
- role-family hints
- flattened skills
- domain hints

That text should still be embedded once and used as the query vector for `VECTOR_SEARCH`.

This keeps phase-1 shortlist behavior simple and stable.

### 2. Remove candidate-chunk embedding from shortlist

`shortlist` should stop calling `embed_and_store_candidate(profile, config)`.

Reason:

- those candidate chunk embeddings are not used by shortlist retrieval
- they are not currently consumed by `cv_analysis` either
- they add cost without improving shortlist output

If candidate chunk embeddings are needed later for semantic evidence retrieval, they should be reintroduced at the stage that actually consumes them, not generated preemptively in shortlist.

### 3. Add explicit reuse for the candidate query embedding

The stage should add a dedicated reuse path for the one candidate query embedding that shortlist actually uses.

The reuse decision should be based on:

- `candidate_query_signature`
- `candidate_query_contract_fingerprint`

If both match the latest cached row, shortlist should reuse the cached query embedding.

If either differs, shortlist should generate a fresh query embedding and persist it for future reuse.

### 4. Define a stable candidate query signature

The signature should be derived from the deterministic shortlist query inputs, not from arbitrary runtime state.

Recommended source:

- bounded `candidate_query_components`

Conceptually:

```json
{
  "headline": "...",
  "target_role": "...",
  "recent_roles": ["..."],
  "role_family_hints": ["..."],
  "flattened_skills": ["..."],
  "domain_hints": ["..."]
}
```

This should be:

- normalized
- deduplicated
- order-stable
- hashed deterministically

So if the candidate retrieval surface is unchanged, the shortlist query embedding can be reused safely.

### 5. Define a candidate query embedding contract fingerprint

Reuse must also invalidate when shortlist embedding behavior changes.

The contract fingerprint should include at least:

- shortlist embedding model
- candidate query schema/version

This is the candidate-query equivalent of the existing job-embedding contract fingerprint.

### 6. Persist query-embedding cache separately from candidate chunks

The shortlist query embedding should not be conflated with `candidate_embeddings`.

Two acceptable designs:

- add a dedicated cache table for candidate query embeddings
- or add a clearly typed `candidate_query` record class to `candidate_embeddings`

Recommendation:

- prefer a dedicated shortlist-query cache shape, because it matches the actual retrieval contract and avoids mixing unrelated embedding purposes

The stored row should include:

- `candidate_query_signature`
- `candidate_query_contract_fingerprint`
- `candidate_query_text`
- `embedding`
- `created_at`

Optional but useful:

- `candidate_query_components_json`

### 7. Expose candidate-query reuse in shortlist debug surfaces

Shortlist artifacts and debug summaries should explicitly tell reviewers whether shortlist used a reused or fresh query embedding.

At minimum, shortlist should expose:

- `candidate_query_text`
- `candidate_query_components`
- `candidate_query_reuse_status`
- `candidate_query_signature`
- `candidate_query_contract_fingerprint`

This closes the current observability gap where reviewers can see job embedding reuse counts but cannot tell what happened on the candidate query side.

## Example

### Current behavior

Candidate profile yields:

```text
Candidate: Data Analyst
Target role: Data Analyst
Recent roles: Business Data Analyst, BI Analyst
Role families: analytics
Skills: SQL, Python, Power BI, Looker, dbt, BigQuery
Domain hints: banking, retail banking
```

Shortlist then:

1. generates a fresh embedding for that whole query text
2. stores candidate chunks in `candidate_embeddings`
3. ignores those candidate chunks during retrieval
4. runs `VECTOR_SEARCH` with the fresh query vector

So the useful candidate-side work is:

- one fresh query embedding

And the extra work is:

- all candidate chunk embeddings

### Proposed behavior

The same candidate query text produces:

- `candidate_query_signature = sig-123`
- `candidate_query_contract_fingerprint = contract-1`

#### Run 1

No cache exists yet.

Shortlist:

- generates fresh query embedding
- stores one query-cache row
- runs `VECTOR_SEARCH`

Artifact/debug could show:

```json
{
  "candidate_query_reuse_status": "fresh_query_embedding",
  "candidate_query_signature": "sig-123",
  "candidate_query_contract_fingerprint": "contract-1"
}
```

#### Run 2

Same candidate query inputs, same embedding contract.

Shortlist:

- finds cached query embedding
- reuses it
- does not call the embedding model for the candidate query again
- runs `VECTOR_SEARCH`

Artifact/debug could show:

```json
{
  "candidate_query_reuse_status": "reused_cached_query_embedding",
  "candidate_query_signature": "sig-123",
  "candidate_query_contract_fingerprint": "contract-1"
}
```

Job embedding reuse stays separate and continues to report:

- `embedding_reused_jobs`
- `embedding_fresh_jobs`

## Design Details

### Stage ownership

`shortlist` owns:

- candidate query construction
- candidate query embedding reuse/fresh generation
- job embedding reuse/fresh generation for shortlist search
- vector retrieval results and shortlist artifacts

`cv_analysis` does not become responsible for shortlist query embedding behavior.

### Data separation

The pipeline should distinguish three concepts clearly:

1. shortlist query embedding
   - one vector per candidate query text
   - used directly by shortlist retrieval

2. job summary embeddings
   - one active embedding per job summary
   - used directly by shortlist retrieval

3. candidate chunk embeddings
   - many vectors for evidence chunks
   - not used by shortlist in this design

That separation is important both for optimization and for operator understanding.

### Backward compatibility

The rollout should tolerate older shortlist runs that do not have candidate-query reuse fields.

Debug/UI behavior should be:

- show candidate query reuse details when present
- degrade cleanly when absent

## Risks

- introducing a cache without clear contract invalidation could serve stale query vectors
- mixing shortlist query embeddings into generic candidate chunk storage could create future confusion
- changing shortlist artifacts without preserving compatibility could break inspection surfaces

## Mitigations

- require deterministic signature plus explicit contract fingerprint for reuse
- keep shortlist query embedding storage logically separate from candidate chunks
- keep artifact/debug additions additive

## Acceptance Criteria

- shortlist no longer embeds/stores candidate chunks as part of shortlist execution
- shortlist can reuse a cached candidate query embedding when the query signature and contract both match
- shortlist generates a fresh candidate query embedding only when reuse is invalid
- shortlist artifacts/debug surfaces explicitly show candidate query reuse status
- job embedding reuse behavior remains unchanged

