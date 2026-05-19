---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: vector-search-refactor-and-issue-patch-implementation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-19-16-19-vector-search-refactor-spec.md
targets:
  - src/fitcv/vector_search.py
  - src/fitcv/embeddings.py
  - src/fitcv/config.py
  - tests/test_vector_search.py
  - tests/test_embeddings.py
related_features: []
related_stages: []
---

# Vector Search Refactor and Issue Patch Plan

## Goal

Implement spec-defined SSOT/symmetry/invariance refactor for shortlist vector-search and embedding runtime surfaces, plus bounded safety hardening, without changing externally observable retrieval behavior.

## Key Deliverables

### Deliverable 1: Shared shortlist runtime SSOT

One shared helper surface owns sqlite runtime policy and common shortlist runtime primitives currently duplicated across `vector_search.py` and `embeddings.py`.

### Deliverable 2: Deterministic contract symmetry

One shared deterministic normalization/hash contract powers shortlist signature/fingerprint generation paths with backward-compatible behavior.

### Deliverable 3: Typed shortlist cache/result contracts

Candidate-query cache/result and status payloads use explicit typed contracts, reducing drift and unsafe implicit dict-key coupling.

### Deliverable 4: Query hardening + backend invariance proof

Vector-search universe input handling is hardened and backend parity tests prove sqlite-mode and BigQuery-mode logic stay semantically aligned.

### Deliverable 5: Verified bounded rollout

All changes pass targeted tests, mypy, repo validator checks, and GitNexus scope verification with rollback containment notes.

## Task/Wave Breakdown

### Task 1: Establish shared shortlist runtime helper boundary

**Purpose:**
- remove duplicated runtime helpers and enforce one source of truth for shortlist runtime policies.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/shortlist_runtime.py` (new)
- Verify: `tests/test_vector_search.py`
- Verify: `tests/test_embeddings.py`

**Preconditions:**
- Spec approved: `docs/superpowers/specs/2026-05-19-16-19-vector-search-refactor-spec.md`.
- Run GitNexus impact before editing each target symbol cluster:
  - `_sqlite_path`
  - sqlite connection setup helpers
  - sqlite retry branches

**Steps:**
- [x] Run `gitnexus_impact` for runtime helper symbols to map callers and risk.
- [x] Create `shortlist_runtime.py` with:
  - sqlite path resolver
  - sqlite connection pragma configurator
  - transient sqlite write retry wrapper (bounded retry)
- [x] Replace duplicated helper internals in `vector_search.py` and `embeddings.py` with shared imports.
- [x] Keep existing function behavior and exceptions unchanged.

**Verification:**
- [x] `uvx pytest tests/test_vector_search.py tests/test_embeddings.py -k "sqlite or shortlist or embedding"`
- [x] Focused inspection confirms no duplicated sqlite helper implementations remain.

**Exit Criteria:**
- shortlist runtime helper duplication is removed and test behavior unchanged.

### Task 2: Extract deterministic normalization/hash SSOT helpers

**Purpose:**
- enforce symmetry for equivalent hashing/normalization logic across shortlist flows.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/shortlist_runtime.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_embeddings.py`

**Preconditions:**
- Task 1 complete.
- Run GitNexus impact before editing signature/fingerprint-building symbols.

**Steps:**
- [x] Run `gitnexus_impact` for signature/fingerprint builder symbols.
- [x] Add shared deterministic helpers for scalar normalization + canonical hash payload serialization.
- [x] Refactor candidate-query and job-summary signature code to use shared helpers.
- [x] Add/adjust golden stability tests for equivalent reordered inputs.

**Verification:**
- [x] `uvx pytest tests/test_vector_search.py tests/test_embeddings.py -k "signature or fingerprint or deterministic"`
- [x] Existing fingerprint-change-with-model tests remain green.

**Exit Criteria:**
- one deterministic contract implementation drives both shortlist signature families.

### Task 3: Introduce typed shortlist cache/result contracts

**Purpose:**
- formalize cache/result/status payload contracts and reduce hidden dict-key coupling.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `tests/test_vector_search.py`

**Preconditions:**
- Task 2 complete.
- GitNexus impact run for `resolve_candidate_query_embedding` and adjacent callers.

**Steps:**
- [x] Define `TypedDict`/dataclass contracts for shortlist cache row/result/status payloads.
- [x] Refactor return payload builders and internal access sites to use typed contracts.
- [x] Keep existing key names and status literal values backward compatible.
- [x] Add tests/assertions for required keys and statuses.

**Verification:**
- [x] `uvx mypy src --show-error-codes` (known pre-existing baseline debt outside Task 3 scope)
- [x] `uvx pytest tests/test_vector_search.py -k "resolve_candidate_query_embedding or reuse_status"`

**Exit Criteria:**
- typed contract coverage exists for shortlist cache/result/status surfaces with zero behavior regression.

### Task 4: Harden BigQuery vector-search universe input handling

**Purpose:**
- remove interpolation risk and keep shortlist query semantics invariant.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `tests/test_vector_search.py`

**Preconditions:**
- Task 3 complete.
- GitNexus impact run for `build_vector_search_query` and `run_vector_search`.

**Steps:**
- [x] Refactor universe-filter query path to parameterized handling for `passed_job_urls`.
- [x] Keep same effective filtering semantics and top-k behavior.
- [x] Extend tests with special-character URL cases and query-shape invariants.

**Verification:**
- [x] `uvx pytest tests/test_vector_search.py -k "build_vector_search_query or run_vector_search"`
- [x] Assertions confirm no unsafe raw URL interpolation contract remains.

**Exit Criteria:**
- vector-search query handling hardened with preserved shortlist behavior.

### Task 5: Add backend parity coverage and finalize bounded rollout

**Purpose:**
- prove invariance across backend modes and complete closeout gates.

**Files:**
- Inspect: `tests/test_vector_search.py`
- Inspect: `tests/test_embeddings.py`
- Modify: `tests/test_vector_search.py`
- Modify: `tests/test_embeddings.py`

**Preconditions:**
- Tasks 1-4 complete.

**Steps:**
- [x] Add parity tests comparing sqlite-mode vs mocked BigQuery-mode shortlist semantics on deterministic fixtures.
- [x] Run full targeted verification suite.
- [x] Run `gitnexus_detect_changes()` evidence capture completed (output remains HIGH risk, but post-isolation changed set is restricted to planned code/docs scope for this workstream).
- [x] Record rollback containment:
  - rollback Task 4 separately if query hardening regression appears
  - rollback Task 3 separately if type-contract migration causes caller breakage
  - keep Tasks 1-2 as structural baseline if validated

**Verification:**
- [x] `uvx pytest tests/test_vector_search.py tests/test_embeddings.py`
- [x] `uvx mypy src --show-error-codes` (known pre-existing baseline debt outside this workstream)
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `gitnexus_detect_changes()`

**Exit Criteria:**
- all deliverables proven with tests/type/validator/GitNexus evidence.

## Verification

- `uvx pytest tests/test_vector_search.py tests/test_embeddings.py`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- `gitnexus_detect_changes()`
- Targeted GitNexus impact checks before each symbol-family refactor slice:
  - `gitnexus_impact({target: "_sqlite_path", direction: "upstream"})`
  - `gitnexus_impact({target: "resolve_candidate_query_embedding", direction: "upstream"})`
  - `gitnexus_impact({target: "build_vector_search_query", direction: "upstream"})`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`


