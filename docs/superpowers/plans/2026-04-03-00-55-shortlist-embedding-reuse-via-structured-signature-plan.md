---
feature_type: modify
feature_name: pipeline_performance
status: completed
summary: "Implement shortlist embedding reuse by comparing a stable structured embedding-input signature and embedding contract before regenerating job_summary vectors."
invariants:
  - "Shortlist must keep latest-only retrieval semantics at the job_url level."
  - "Embedding reuse must never rely on job_url alone."
  - "Reuse remains valid only when the structured embedding signature and embedding contract both match."
  - "Shortlist artifacts must make reused-versus-fresh embedding behavior visible without hiding retrieval facts."
---

# Shortlist Embedding Reuse Via Structured Signature Plan

## Triage

Feature type: MODIFY  
Summary: Add shortlist embedding reuse so unchanged passed jobs can skip repeated `job_summary` embedding generation when both the structured signature and embedding contract still match.  
Reasoning: The shortlist stage already improved correctness with latest-only retrieval per `job_url`, but it still re-embeds unchanged jobs every run. This is a performance optimization of existing shortlist behavior, not a new stage or ranking redesign.  
Invariants:
- Latest-only retrieval per canonical `job_url` remains the retrieval contract.
- Reuse must compare a structured signature, not just rendered text and not just `job_url`.
- Embedding model/contract changes must invalidate reuse automatically.
- Shortlist inspection must keep retrieval facts separate from embedding reuse facts.
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
Spec needed: no
Plan needed: yes
Rollback trigger: shortlist embedding reuse serves stale vectors after shortlist-relevant job changes, or reuse metadata makes retrieval debugging less trustworthy
Rollback method: disable shortlist embedding reuse and fall back to the current always-embed shortlist path while leaving additive signature fields inert
Migration needed: yes
Risk level: medium

## Scope

This plan implements [2026-04-03-00-40-shortlist-embedding-reuse-via-structured-signature-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/superpowers/specs/2026-04-03-00-40-shortlist-embedding-reuse-via-structured-signature-spec.md).

In scope:

- stable structured shortlist embedding-input signature generation
- shortlist embedding contract fingerprint generation
- persistent metadata on `job_summary` embedding rows
- reuse lookup before generating shortlist job embeddings
- embedding only the shortlist misses
- shortlist-stage reuse provenance in artifacts and debug surfaces

Out of scope:

- candidate-query embedding reuse
- cross-URL embedding reuse
- approximate semantic reuse
- redesigning latest-only retrieval itself
- redesigning ranking or AI scoring

## Implementation Tasks

### Task 1: Define the shortlist embedding-input signature contract

Add a code-owned helper that builds a stable structured payload and hash from shortlist-relevant job fields.

Requirements:

- include only shortlist-relevant stable fields
- normalize strings consistently
- sort list fields where order is not semantically meaningful
- serialize deterministically
- return both:
  - `embedding_input_signature`
  - optional structured payload for debugging/tests

Initial recommended fields:

- `title`
- `location_type`
- `seniority`
- `job_family`
- sorted `required_skills_canonical`
- sorted `preferred_skills_canonical`

Deliverables:

- signature helper implementation
- deterministic unit tests

### Task 2: Define the shortlist embedding contract fingerprint

Add a helper that fingerprints the embedding contract used for shortlist job embeddings.

Requirements:

- include embedding model name
- include shortlist summary contract version
- include any relevant embedding builder versioning if needed
- change when embedding behavior changes materially

Deliverables:

- embedding contract helper
- tests proving contract changes invalidate reuse

### Task 3: Extend embedding persistence metadata

Persist enough metadata on `job_summary` rows to support reuse checks.

Required fields:

- `embedding_input_signature`
- `embedding_contract_fingerprint`
- optional `embedding_input_signature_payload_json` if phase 1 keeps payload visibility

Likely touchpoints:

- `src/fitcv/embeddings.py`
- BigQuery DDL for `job_embeddings`
- migration script(s)

### Task 4: Implement reuse lookup before shortlist job embedding

Change shortlist embedding flow so it can reuse an existing latest embedding row when the signature and contract still match.

Requirements:

- fetch latest embedding metadata for current `passed_jobs`
- compare:
  - canonical `job_url`
  - `embedding_input_signature`
  - `embedding_contract_fingerprint`
- skip embedding generation for exact matches
- generate fresh embeddings only for misses

Important constraint:

- latest-only retrieval semantics must remain unchanged after this task

### Task 5: Preserve latest-only retrieval with reused and fresh rows

Make sure shortlist retrieval still operates on one latest active row per canonical `job_url`.

Requirements:

- reused rows and fresh rows must both be compatible with the current latest-only retrieval contract
- shortlist should not regress into duplicate-row competition during vector search
- shortlist-level dedupe should remain as a defensive guard only

Likely touchpoints:

- `src/fitcv/embeddings.py`
- `src/fitcv/vector_search.py`
- `src/fitcv/pipeline.py`

### Task 6: Expose shortlist embedding reuse provenance in diagnostics

Add explicit reuse visibility to shortlist artifacts and debug/export surfaces.

Requirements:

- shortlist decision summary should report:
  - `embedding_reused_jobs`
  - `embedding_fresh_jobs`
  - `embedding_total_jobs`
- row-level shortlist samples should include `embedding_reuse_status` where present
- retrieval facts and reuse facts must stay separate

Likely touchpoints:

- `src/fitcv/pipeline.py`
- shortlist stage artifact builders
- run-scoped inspection/export readers if needed

### Task 7: Sync source-of-truth docs and generated discovery

Update docs once the runtime behavior is in place.

Required updates:

- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/pipeline_performance/history.md`
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

- shortlist signature determinism tests
- embedding contract invalidation tests
- reuse lookup tests:
  - exact signature + contract match -> reuse
  - signature mismatch -> fresh embedding
  - contract mismatch -> fresh embedding
- persistence mapping tests for new embedding metadata fields
- shortlist artifact tests for reuse/fresh counts and row-level reuse visibility

### Regression checks

- latest-only retrieval semantics remain intact
- shortlist still returns one job-level row per canonical `job_url`
- backfill behavior still works when retrieval misses occur
- ranking input shape remains unchanged apart from additive shortlist debug metadata

## Execution Order

1. Define shortlist signature contract and tests.
2. Define shortlist embedding contract fingerprint and tests.
3. Extend embedding persistence metadata.
4. Add reuse lookup before shortlist embedding generation.
5. Confirm latest-only retrieval still behaves correctly.
6. Add shortlist reuse diagnostics and inspection visibility.
7. Sync docs and generated discovery.

## Risks and Notes

- The biggest correctness risk is a signature that omits shortlist-relevant fields and reuses stale vectors.
- The biggest efficiency risk is a signature that is too noisy and rarely matches.
- The main inspection risk is mixing embedding reuse facts with retrieval facts in a way that obscures shortlist debugging.

## Task Status

- [x] Task 1: Define the shortlist embedding-input signature contract
- [x] Task 2: Define the shortlist embedding contract fingerprint
- [x] Task 3: Extend embedding persistence metadata
- [x] Task 4: Implement reuse lookup before shortlist job embedding
- [x] Task 5: Preserve latest-only retrieval with reused and fresh rows
- [x] Task 6: Expose shortlist embedding reuse provenance in diagnostics
- [x] Task 7: Sync source-of-truth docs and generated discovery

## Verification Status

- [x] `pytest -q .worktrees\Shortlist\tests\test_embeddings.py .worktrees\Shortlist\tests\test_pipeline.py` (via Azure CLI Python + `PYTHONPATH` workaround) -> `78 passed, 2 skipped`
- [x] `python -m py_compile` on touched shortlist runtime, migration, and test files
