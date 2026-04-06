---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Remove candidate chunk embedding generation from the active pipeline until a real stage-level consumer exists."
invariants:
  - "`shortlist` must continue to embed or reuse only the candidate query vector it actually uses for retrieval."
  - "`cv_analysis` remains the sole owner of evidence retrieval and must continue to work from the candidate profile and selected evidence contract."
  - "No stage should generate candidate chunk embeddings during normal runtime unless that stage directly consumes them."
  - "Future semantic retrieval or validation work may reintroduce candidate chunk embeddings, but only behind an explicit stage-owned contract."
---

# Remove Candidate Chunk Embeddings From The Active Pipeline

## Why

The active pipeline still generates candidate chunk embeddings even though no stage currently consumes them.

Today:

- `shortlist` calls `embed_and_store_candidate(profile, config)`
- that writes chunk rows into `candidate_embeddings`
- `shortlist` retrieval does not query `candidate_embeddings`
- `cv_analysis` evidence selection does not query `candidate_embeddings`
- `cv_generation` validation does not query `candidate_embeddings`

So the current behavior adds:

- avoidable embedding cost
- avoidable runtime latency
- avoidable storage churn
- operator confusion about whether candidate chunk embeddings are part of the live decision path

This spec removes that dead work from the active pipeline and makes the stage contracts clearer.

## Feature and Stage Alignment

Feature type: `MODIFY`

Summary:

- remove unused candidate chunk embedding generation from the active runtime, keep shortlist focused on job embeddings plus the candidate query embedding actually used for retrieval, and leave future semantic candidate-chunk use as an explicit later-stage enhancement

Reasoning:

- this changes existing `cv_system` behavior rather than adding a new feature family
- the work is stage-heavy because it changes the `shortlist -> cv_analysis` contract boundary and removes a misleading active-runtime step

Affected stages:

- `shortlist`
- `cv_analysis`

Affected features:

- `cv_system`
- `inspection_debugging`

Primary lens:

- `mixed`

Affected docs:

- feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
- feature_docs: none
- cross_cutting_docs:
  - [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)
- readme: none
- generated:
  - [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_overview.md)
  - [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/features_index.yaml)
  - [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_capabilities_index.yaml)
  - [shortlist.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/shortlist.yaml)
  - [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)

Generated refresh required:

- yes

Spec needed:

- yes

Plan needed:

- yes

Risk level:

- low

Migration needed:

- no

## Current Problem

The pipeline currently blurs three different candidate-side concepts:

1. candidate query embedding used by `shortlist`
2. candidate chunk embeddings written to `candidate_embeddings`
3. selected evidence used by `cv_analysis`

Only the first and third concepts matter in the current runtime.

The second concept exists in storage but is not part of the actual decision path.

That leads to a misleading mental model:

- operators may think `cv_analysis` is already using candidate chunk embeddings
- shortlist appears more semantically sophisticated than it really is
- debugging reuse becomes harder because the pipeline writes candidate embedding data that is not later referenced

## Goals

This slice should:

- remove candidate chunk embedding generation from the active runtime
- keep `shortlist` focused on the candidate query embedding it actually uses
- keep `cv_analysis` evidence retrieval unchanged for now
- make artifacts and docs clearer about what candidate-side embedding work is and is not active
- preserve a clean path for future reintroduction if semantic chunk consumers are added later

## Non-Goals

This slice does not:

- redesign `cv_analysis` evidence retrieval
- add semantic evidence retrieval
- add candidate query embedding reuse by itself
- delete or migrate historical `candidate_embeddings` data
- remove the possibility of future candidate chunk embeddings

## Proposed Design

### 1. Remove Candidate Chunk Embedding From `shortlist`

The active `shortlist` runtime should no longer call candidate chunk embedding persistence.

Specifically:

- remove the `embed_and_store_candidate(profile, config)` step from `shortlist`
- keep `embed_and_store_jobs(passed_jobs, config)` because job embeddings are used by retrieval
- keep candidate query text construction plus the single candidate query embedding used by `VECTOR_SEARCH`

After this change, the active `shortlist` path should mean:

- build candidate query text
- embed or reuse the query vector actually used for retrieval
- query reusable job embeddings

Not:

- build candidate chunks
- store candidate chunk embeddings that no later stage reads

### 2. Keep `cv_analysis` Profile-Based Retrieval As-Is

`cv_analysis` should continue to retrieve evidence from the normalized candidate profile and selected evidence contract.

This stage already uses:

- role-family hints
- domain tags
- responsibility themes
- evidence text/bullets/highlights

It does not currently require `candidate_embeddings`, and this spec keeps that contract explicit.

### 3. Clarify Candidate Embedding Ownership

The runtime should treat candidate embeddings as stage-owned, not globally assumed.

Rule:

- a stage may generate candidate embeddings only when that stage directly consumes them

Examples:

- `shortlist`
  - should not generate candidate chunk embeddings
- `cv_analysis`
  - may generate or reuse candidate chunk embeddings in the future if semantic responsibility alignment or semantic evidence reranking is added
- `cv_generation`
  - may consume stage-prepared semantic evidence support in the future, but should not silently trigger its own evidence embedding pipeline

### 4. Preserve A Future Reintroduction Path

This spec does not declare candidate chunk embeddings useless forever.

It only declares them inactive until a real consumer exists.

If later work adds:

- semantic responsibility alignment in `cv_analysis`
- embedding-based evidence reranking
- embedding-based soft-claim validation support

then candidate chunk embeddings may be reintroduced under a new explicit stage contract with:

- clear ownership
- clear reuse rules
- clear artifact/debug visibility

## Concrete Examples

### Example 1: Current Wasteful Runtime

Today a shortlist run may do all of the following:

1. build candidate query text
2. generate one query embedding for `VECTOR_SEARCH`
3. generate many candidate chunk embeddings for experiences/projects/achievements
4. never read those candidate chunk embeddings again

That means the stage pays for:

- one useful embedding path
- one unused embedding path

### Example 2: After This Change

After this change, the same shortlist run should do:

1. build candidate query text
2. generate or reuse the one query embedding used by retrieval
3. query reusable job embeddings

And stop there.

`cv_analysis` then continues to use:

- the candidate profile
- selected evidence bundle logic
- gap analysis

without any dependency on `candidate_embeddings`.

## Artifact and Debugging Changes

Artifacts and debug surfaces should no longer imply that candidate chunk embeddings are part of the active shortlist flow.

Expected clarifications:

- shortlist debug should continue to expose:
  - candidate query text
  - candidate query components
  - job embedding reuse/fresh counts
- shortlist debug should not imply candidate chunk embedding reuse/fresh status unless a real candidate-embedding consumer exists

This change should make operator reasoning simpler:

- shortlist uses job embeddings plus one candidate query vector
- `cv_analysis` uses the selected evidence retrieval contract
- candidate chunk embeddings are not part of the active path

## Compatibility

This work should remain operationally compatible because:

- no current stage depends on `candidate_embeddings`
- removing this runtime step does not invalidate the existing `cv_analysis` contract
- historical `candidate_embeddings` rows may remain in storage without affecting behavior

## Rollout Strategy

Recommended rollout:

1. remove candidate chunk embedding from `shortlist`
2. update docs and debug wording
3. verify end-to-end shortlist and `cv_analysis` runs remain unchanged in output behavior
4. only later consider candidate chunk embedding reintroduction as part of a separate semantic evidence feature

## Risks

- some operators may have assumed `candidate_embeddings` were already active in `cv_analysis`
- removing the write path can reveal implicit expectations in tests or debug tooling

Mitigations:

- make docs explicit
- keep the stage contracts narrow and clear
- verify no code path reads `candidate_embeddings` before removing the write call

## Acceptance Criteria

This work is successful when:

- the active `shortlist` runtime no longer generates candidate chunk embeddings
- `shortlist` still performs retrieval correctly using the candidate query embedding and job embeddings
- `cv_analysis` behavior remains unchanged
- docs and artifacts no longer suggest that candidate chunk embeddings are part of the live pipeline
- future semantic candidate chunk embedding work can still be added later under a separate explicit spec
