---
feature_type: modify
feature_name: pipeline_performance
status: draft
summary: "Reuse shortlist job embeddings safely by hashing a stable structured embedding-input signature instead of re-embedding unchanged jobs every run."
invariants:
  - "Shortlist must keep latest-only retrieval semantics at the job_url level."
  - "Embedding reuse must never rely on job_url alone."
  - "Reuse remains valid only when the structured embedding signature and embedding model contract both match."
  - "Shortlist artifacts must make reused-versus-fresh embedding behavior visible without hiding retrieval facts."
---

# Shortlist Embedding Reuse Via Structured Signature Design

## Affected Feature Contracts

- [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/pipeline_performance/pipeline_performance.yaml)
- [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/features/inspection_debugging/inspection_debugging.yaml)
- [shortlist.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/stages/shortlist.yaml)

## Triage

Feature type: MODIFY  
Summary: Add a shortlist-stage embedding reuse contract that skips re-embedding unchanged passed jobs by comparing a stable structured embedding-input signature plus embedding-model contract metadata.  
Reasoning: The shortlist stage already embeds current-run passed jobs and already enforces latest-only retrieval per `job_url`, but it still re-embeds the same unchanged jobs across runs. This is a performance and cost optimization of existing shortlist behavior, not a new stage or a retrieval redesign.  
Invariants:
- Latest-only retrieval per canonical `job_url` remains the retrieval contract.
- Reuse must compare a stable structured signature, not just rendered prompt text and not just `job_url`.
- Reuse must also compare embedding model/version metadata so model drift invalidates old vectors automatically.
- Inspection/debugging surfaces must be able to show whether shortlist embeddings were reused or freshly generated.
Dependencies:
- `pipeline_performance`
- `cv_system`
- `inspection_debugging`
- shortlist runtime in `src/fitcv/embeddings.py`, `src/fitcv/pipeline.py`, and `src/fitcv/vector_search.py`
- persistent embedding storage in `job_embeddings`
Affected stages:
- shortlist
Affected features:
- pipeline_performance
- cv_system
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/pipeline_performance/pipeline_performance.yaml`
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/pipeline_performance/history.md`
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
Spec needed: yes  
Plan needed: yes  
Rollback trigger: shortlist reuse serves stale vectors after summary-relevant job changes, or reuse visibility is too weak to trust retrieval behavior.  
Rollback method: disable shortlist embedding reuse and fall back to the current always-embed shortlist path while keeping additive signature fields inert.  
Migration needed: yes  
Risk level: medium

## Why This Spec Exists

The shortlist stage already improved correctness by:

- embedding current-run `passed_jobs`
- retrieving only one latest active embedding row per `job_url`
- keeping backfill as a safety net

That solved stale-row competition during retrieval, but it did not solve repeated embedding work across runs.

Today the system can still do this:

1. Run A sees `job-A`
2. shortlist embeds `job-A`
3. Run B sees the same unchanged `job-A`
4. shortlist embeds `job-A` again

That is safe, but wasteful.

The initial idea was to fingerprint the rendered `job_summary` text directly. That is workable, but it is not the best optimization boundary because harmless formatting or ordering changes can invalidate reuse unnecessarily.

The chosen direction is better:

- define a stable structured embedding-input signature
- reuse only when that signature and the embedding contract both match

## Problem Statement

Shortlist currently optimizes retrieval correctness better than embedding efficiency.

The current latest-only retrieval contract ensures:

- at most one active row per canonical `job_url` participates in vector search
- retrieval anomalies are reduced

But the stage still lacks a safe reuse test for embedding generation itself.

Without that reuse check:

- unchanged jobs can be re-embedded every run
- embedding cost and latency scale with repeated job visibility rather than actual content change
- the system does not benefit from the stable shared enrich contract already produced upstream

## Design Goals

1. Avoid re-embedding unchanged shortlist jobs across runs.
2. Keep latest-only retrieval semantics unchanged.
3. Base reuse on a stable structured input signature rather than a raw rendered-text blob.
4. Invalidate reuse automatically when embedding model/version changes.
5. Keep shortlist inspection clear about reused versus freshly generated embeddings.

## Non-Goals

- redesign shortlist into a fully run-scoped ephemeral embedding store
- remove latest-only retrieval
- reuse vectors across different `job_url` values
- introduce approximate semantic reuse
- redesign AI scoring or ranking contracts

## Chosen Design

### Reuse by structured embedding-input signature

Before generating a shortlist job embedding, the stage will build a stable structured payload from shortlist-relevant job fields.

That payload is the source of truth for reuse checks.

The stage will then:

1. normalize the payload into a deterministic representation
2. hash it into an `embedding_input_signature`
3. compare that signature against the latest stored embedding row for the same canonical `job_url`
4. reuse the existing vector only when:
   - `job_url` matches
   - `embedding_input_signature` matches
   - embedding model/version matches

If any of those differ, shortlist generates a fresh embedding.

### Why not reuse by job URL alone

`job_url` alone is too weak because:

- the job content may have changed under the same URL
- the enrich output may have changed in shortlist-relevant ways

Blind URL-only reuse would keep stale vectors alive.

### Why not hash only the rendered `job_summary` text

Hashing the final text blob is better than URL-only reuse, but it is still more fragile than necessary.

Rendered text can change for reasons that are not semantically important to retrieval:

- field ordering
- list ordering
- harmless formatting changes
- punctuation or label changes

A structured signature is more stable, easier to test, and easier to explain.

## Proposed Signature Contract

### Signature input

The shortlist embedding signature should be built from the smallest stable set of fields that meaningfully determine shortlist retrieval semantics.

Recommended initial fields:

- `title`
- `location_type`
- `seniority`
- `job_family`
- sorted `required_skills_canonical`
- sorted `preferred_skills_canonical`

Optional follow-up fields only if proven stable enough:

- reduced normalized `responsibilities`
- reduced normalized domain information

### Signature rules

- normalize strings consistently
- sort list fields when order is not semantically meaningful
- omit fields that are missing rather than inventing volatile placeholders
- serialize deterministically
- hash the canonical payload

The signature should represent:

- "Would this job produce the same shortlist embedding input?"

not:

- "Did any incidental formatting difference happen upstream?"

### Separate signature from rendered embedding text

Important distinction:

- the embedding text used for the actual model call may remain rich and labeled
- the reuse decision should use the smaller stable structured signature

So there are two contracts:

1. `embedding_input_signature_payload`
   - stable
   - minimal
   - used for reuse checks

2. rendered `job_summary`
   - richer text for the embedding model
   - may be regenerated from the same stable payload

## Embedding Contract Fingerprint

Reuse must also check the embedding contract itself.

Minimum contract inputs:

- embedding model name
- embedding model version or contract version if tracked
- shortlist summary schema version

This prevents reuse when:

- the embedding model changes
- the shortlist summary builder changes in meaningfully retrieval-relevant ways

## Runtime Flow

### Current shortlist flow

1. `rule_filter` produces `passed_jobs`
2. shortlist embeds those jobs
3. shortlist embeds candidate query context
4. vector search runs latest-only per `job_url`
5. shortlist materializes scoring rows

### New shortlist flow

1. `rule_filter` produces `passed_jobs`
2. shortlist builds structured embedding signatures for those jobs
3. shortlist loads latest embedding metadata for the same canonical `job_url`s
4. shortlist reuses vectors for exact signature + contract matches
5. shortlist embeds only the misses
6. vector search runs latest-only per `job_url`
7. shortlist materializes scoring rows

This keeps retrieval semantics intact while reducing repeated embedding calls.

## Persistence Implications

The persistent shortlist embedding rows should carry enough metadata to support reuse checks:

- `job_url`
- `chunk_type = job_summary`
- `created_at`
- `embedding_input_signature`
- `embedding_contract_fingerprint`
- optional serialized `embedding_input_signature_payload` for debugging

The vector itself remains unchanged.

This does not require cross-URL reuse or approximate matching.

## Inspection and Debugging Implications

The shortlist stage should expose reuse behavior explicitly.

Useful decision-summary fields:

- `embedding_reused_jobs`
- `embedding_fresh_jobs`
- `embedding_total_jobs`

Useful changed-state or output sample fields:

- `embedding_reuse_status`
  - `reused_cached_embedding`
  - `fresh_embedding`
- `embedding_input_signature`
- `embedding_contract_fingerprint`

Inspection must still keep retrieval facts distinct from embedding reuse facts.

Example:

```json
{
  "job_url": "...",
  "embedding_reuse_status": "reused_cached_embedding",
  "raw_hit_present": true,
  "shortlist_origin": "vector_search",
  "vector_similarity": 0.84
}
```

This makes it clear that:

- the embedding was reused
- retrieval still genuinely returned the job

## Rollout Plan

### Phase 1: signature and contract metadata

- define shortlist structured signature helper
- define shortlist embedding contract fingerprint
- persist metadata on new `job_summary` rows

### Phase 2: reuse lookup before embedding

- fetch latest embedding metadata for current `passed_jobs`
- reuse exact matches
- embed only misses

### Phase 3: artifact and inspection updates

- expose reuse counts and row-level reuse status in shortlist artifacts
- keep retrieval facts and reuse facts separate

## Risks

### Under-specified signature risk

If the signature excludes fields that materially affect retrieval, reuse could keep stale vectors.

### Over-sensitive signature risk

If the signature includes noisy or weakly relevant fields, reuse hit rate will be poor and the optimization will not pay off.

### Debuggability risk

If signature/contract metadata is not visible in artifacts, it will be hard to trust reuse decisions during shortlist debugging.

## Success Criteria

This design is successful when:

- unchanged shortlist jobs are not re-embedded across runs
- latest-only retrieval semantics remain intact
- reuse invalidates automatically on embedding model or summary-contract change
- shortlist artifacts clearly report reused versus freshly generated embeddings
- embedding cost per run decreases without making retrieval behavior less trustworthy

## Open Questions

1. Should the initial signature use only canonical skill fields plus coarse labels, or should it also include a reduced responsibilities summary from day one?
2. Do we want to persist the full signature payload for debugging, or only the hash plus a schema version in phase 1?
3. Should candidate-query embedding reuse be part of the same optimization later, or stay separate from shortlist job embedding reuse?
