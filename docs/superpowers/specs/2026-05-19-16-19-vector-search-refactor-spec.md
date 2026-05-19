---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: vector-search-ssot-symmetry-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract

targets:
  - src/fitcv/vector_search.py
  - src/fitcv/embeddings.py
  - src/fitcv/config.py
  - tests/test_vector_search.py
  - tests/test_embeddings.py
related_features: []
related_stages: []
---

## Goal

Define bounded refactor + patch specification for vector-search and shortlist-embedding surfaces, enforcing SSOT, structural symmetry, and invariance without external behavior change.

## Key Deliverables

### Deliverable 1: Shared runtime contract for shortlist embedding/cache paths

Establish single reusable contract layer for sqlite connection policy, deterministic normalization/hash behavior, cache record shape, and status semantics used by both candidate-query and job-summary embedding flows.

### Deliverable 2: Safe query/path hardening and parity guarantees

Remove divergent backend behavior risks (sqlite vs BigQuery), harden SQL construction, and define parity proof so shortlist ranking/reuse semantics remain consistent.

### Deliverable 3: Execution-ready migration sequence

Provide ordered, low-blast-radius execution waves with explicit dependencies, risk level, required tests, rollback controls, and GitNexus checkpoints.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and drift boundaries before refactor

**Steps:**
- [x] inspect `src/fitcv/vector_search.py` and equivalent shortlist embedding surfaces
- [x] map equivalent concepts across `vector_search.py`, `embeddings.py`, and `config.py`
- [x] identify drift/duplication/contract gaps and backend edge-case risks
- [x] refresh GitNexus index (`npx gitnexus analyze`) for high-trust graph usage

**Verification:**
- [x] current-state matrix exists with line-level evidence and risk categories

**Exit Criteria:**
- all proposed changes map to explicit source drifts, not stylistic preference

### Wave 2: Decision closure

**Purpose:**
- close architectural decisions for SSOT/symmetry/invariance target

**Steps:**
- [ ] define shared shortlist runtime helper module boundary
- [ ] define shared normalization/hash contract boundary
- [ ] define typed cache/status contract boundary
- [ ] define query hardening approach for `passed_job_urls`
- [ ] define backend parity constraints and required tests

**Verification:**
- [ ] each decision has rationale, alternatives, and impact

**Exit Criteria:**
- design is bounded, internally coherent, and patch-ordered

### Wave 3: Validation and approval readiness

**Purpose:**
- prepare implementation handoff with proof expectations and containment controls

**Steps:**
- [ ] define unit/parity/regression test matrix
- [ ] define mypy and targeted pytest command set
- [ ] define rollback strategy by action slice
- [ ] define GitNexus refactor checkpoints (`impact` before edits, `detect_changes` before commit)

**Verification:**
- [ ] every invariant has matching proof target and evidence path

**Exit Criteria:**
- spec can hand off directly to implementation planning/execution

## Design Decisions

### Decision: Introduce shared shortlist runtime helper layer

- context: sqlite path/config/retry behavior duplicated across modules, causing drift risk
- choice: extract shared helper surface (e.g., `fitcv/shortlist_runtime.py`) for:
  - sqlite path resolution
  - sqlite connection pragmas
  - bounded retry wrapper for transient sqlite operational errors
  - optional shared BigQuery client bootstrap helper
- alternatives considered:
  - keep duplicated helpers and add comments only
  - partial extraction of sqlite path only
- impact:
  - touches `vector_search.py` and `embeddings.py` internals only
  - no API change expected

### Decision: Introduce shared deterministic payload contract helpers

- context: equivalent hashing/normalization logic duplicated across modules
- choice: extract SSOT helper set for scalar normalization and canonical hash serialization used by both candidate-query and job-summary signatures
- alternatives considered:
  - keep separate functions and enforce via tests only
- impact:
  - possible cache key sensitivity; requires golden stability tests

### Decision: Standardize typed shortlist cache/status contracts

- context: string-keyed dict payloads and status literals repeated across flows
- choice: define `TypedDict`/dataclass contracts for:
  - cache row metadata
  - candidate query embedding resolution result
  - status enum-like literals (`reused_*`, `fresh_*`)
- alternatives considered:
  - leave untyped dicts and rely on caller conventions
- impact:
  - safer refactors, stronger invariance guarantees, lower regression risk

### Decision: Parameterize BigQuery vector-search universe inputs

- context: `build_vector_search_query` interpolates URL strings into SQL
- choice: migrate to parameterized universe handling to remove string interpolation risk
- alternatives considered:
  - keep interpolation and rely on upstream URL sanitation
- impact:
  - query builder + tests update; behavior should remain identical for valid inputs

### Decision: Enforce backend parity invariants explicitly in tests

- context: sqlite path computes similarity/rank locally while BigQuery path delegates semantics
- choice: add parity tests for ranking/dedupe/reuse behavior against deterministic fixtures
- alternatives considered:
  - rely on existing unit tests only
- impact:
  - stronger confidence for future refactors

## Invariants

- external call signatures and return shapes for `run_vector_search`, `resolve_candidate_query_embedding`, and `store_shortlist` remain backward compatible unless explicitly versioned
- shortlist ordering invariant remains: descending similarity, deterministic rank assignment, dedupe by first best-ranked `job_url`
- cache validity invariant remains: reuse only when signature and contract fingerprint match
- config precedence invariant remains: `pipeline.vector_search_top_n` takes precedence over legacy `vector_top_n`
- sqlite mode remains offline-safe deterministic path
- no refactor step may bypass GitNexus impact check before symbol edits in scoped files

## Validation Plan

- proof target: shared helper extraction preserves behavior
  - method: run targeted unit tests + compare pre/post result fixtures
  - evidence: passing `tests/test_vector_search.py` and `tests/test_embeddings.py`

- proof target: signature/fingerprint invariance preserved
  - method: add/execute golden tests for candidate-query and job-summary hash records
  - evidence: deterministic snapshots stable across reordered equivalent inputs

- proof target: SQL hardening does not regress shortlist output
  - method: unit tests for query generation + injected special-character input tests
  - evidence: tests pass and generated query uses parameters for universe scope

- proof target: backend parity maintained
  - method: parity tests for sqlite-mode vs mocked-BigQuery-mode ranking/reuse semantics
  - evidence: identical shortlist rows/ranks for shared deterministic fixture

- proof target: type/contract soundness
  - method: `uvx mypy src --show-error-codes`
  - evidence: no new type errors in touched files

- proof target: refactor blast radius bounded
  - method: `gitnexus_detect_changes()` before commit
  - evidence: changed symbols/files match planned scope

## Acceptance Criteria

- all duplicated shortlist runtime primitives in scope are centralized or intentionally documented as justified divergence
- no raw SQL interpolation remains for `passed_job_urls` in BigQuery vector-search flow
- typed contract layer exists for shortlist cache/result/status payloads
- parity tests added and passing for backend-equivalent behavior claims
- no regression in existing vector-search and embedding tests

## Non-Goals

- changing ranking algorithm, similarity math model, or business scoring logic
- redesigning pipeline orchestration outside shortlist/vector-search scope
- introducing new retrieval strategy versions in this refactor
- broad cross-module style rewrites not tied to explicit drift findings

## Risks and Mitigations

- risk: cache-key drift accidentally invalidates reuse unexpectedly
  - mitigation: golden signature/fingerprint tests before/after extraction

- risk: query parameterization changes BigQuery execution plan subtly
  - mitigation: keep SQL shape equivalent; add focused integration/contract tests

- risk: helper extraction increases coupling
  - mitigation: keep helper module narrow, shortlist-specific, no generic framework abstraction

- risk: hidden caller assumptions on dict keys
  - mitigation: typed contracts + transitional compatibility tests

## Migration and Safety Controls

- backward compatibility needs:
  - preserve current public function names/signatures and returned key names
  - preserve status literal values consumed by pipeline diagnostics

- deprecation/removal path:
  - phase 1: introduce shared helpers + adapters while retaining existing call sites
  - phase 2: migrate internals in small slices
  - phase 3: remove obsolete duplicated private helpers after full test pass

- rollback/containment strategy:
  - isolate each action in separate commit-ready slice
  - if regression appears, rollback latest slice only; keep prior validated slices
  - keep temporary compatibility shim functions during transition when needed

## Dependency Ordering

1. shared runtime helper extraction (low-medium risk)
2. normalization/hash SSOT extraction (medium risk)
3. typed contracts for cache/status payloads (low-medium risk)
4. query parameterization/hardening (medium risk)
5. backend parity test suite expansion (low risk, but required gate)
6. optional cleanup/removal of obsolete helpers (post-proof)

## Completion Criteria

1. all Key Deliverables are satisfied
2. every planned action slice has passing tests + type check evidence
3. GitNexus blast-radius check confirms expected scope before commit
4. no open invariant violations remain

## Triage Block

Layer: change  
Feature type: MODIFY  
Summary: Refactor shortlist vector-search/embedding internals for SSOT + symmetry + invariance with bounded hardening patches.  
Reasoning: Bounded internal change; no new product capability; resolves structural drift and reliability risk in existing implementation.  
Invariants:
  - shortlist ranking/reuse behavior must remain equivalent
  - API and status payload compatibility must remain stable
Dependencies:
  - refreshed GitNexus index
  - existing vector-search and embeddings unit tests
Affected stages:
  - none
Affected features:
  - none
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs:
    - none
  cross_cutting_docs:
    - docs/superpowers/specs/2026-05-19-16-19-vector-search-refactor-spec.md
  readme: none
  generated:
    - none
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes
