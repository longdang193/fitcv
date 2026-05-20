---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: embedding-cache-query-ssot-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
targets:
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - tests/test_embeddings.py
related_features: []
related_stages: []
---

## Goal

Define bounded, implementation-ready refactor spec for embedding cache/query surfaces in `src/fitcv/embeddings.py`, prioritizing SSOT, structural symmetry, and invariance while reducing immediate risk in cache metadata lookup.

### Triage Block

Layer: change  
Feature type: MODIFY  
Summary: Refactor shortlist embedding cache-query and contract surfaces for safety and symmetry, with immediate patch on parameterized metadata lookup.  
Reasoning: Design known, scope bounded to shortlist embedding module and nearest equivalent vector-query surface; no product-intent change.  
Invariants:
- shortlist reuse decision remains exact match on signature + contract fingerprint
- sqlite deterministic embedding behavior unchanged
- persisted row schema fields used downstream remain stable
- existing status labels remain stable (`fresh_embedding`, `reused_cached_embedding`)
Dependencies:
- `src/fitcv/shortlist_runtime.py`
- BigQuery parameterized query behavior
- existing tests in `tests/test_embeddings.py`
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
  - docs/operating_system/planning/planning-dispatch.md
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

## Key Deliverables

### Deliverable 1: Query Safety SSOT Decision

Resolve canonical approach for loading latest job embedding metadata so equivalent cache lookups use equivalent parameterization/safety model across job and candidate-query flows.

### Deliverable 2: Refactor Action Boundary

Define exact first patch scope (RA-01) and explicit non-goals, plus dependency order for follow-on RA-02..RA-05 refactors.

### Deliverable 3: Invariant and Proof Contract

Define acceptance criteria and validation evidence proving no behavioral regression in reuse logic, persistence shape, and pipeline-facing metadata.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current behavior and divergence points in embedding cache lookup and contract fingerprint paths

**Steps:**
- [ ] analyze current `_load_latest_job_embedding_metadata` SQL construction and input shaping
- [ ] compare equivalent cache lookup path in `vector_search.py`
- [ ] enumerate downstream fields consumed by pipeline artifacts/tests

**Verification:**
- [ ] current state captures query safety risks, symmetry drifts, and downstream dependencies

**Exit Criteria:**
- all RA-01 behavioral invariants defined with no unstated assumptions

### Wave 2: Decision closure

**Purpose:**
- close design choices for bounded patch and refactor ordering

**Steps:**
- [ ] decide canonical parameterized query design for job URL list lookup
- [ ] decide allowable mutation/side-effect boundaries for job dict enrichment fields
- [ ] lock out-of-scope list for first patch

**Verification:**
- [ ] decision record includes alternatives and rejection reasons

**Exit Criteria:**
- patch scope and expected behavior explicit, testable, and bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof-ready checks for regression safety and invariance preservation

**Steps:**
- [ ] define unit tests for URL escaping and empty list behavior
- [ ] define contract checks for unchanged status and metadata keys
- [ ] define blast-radius verification expectations for high-impact symbols

**Verification:**
- [ ] validation plan includes explicit evidence outputs

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Parameterize job metadata lookup query

- context: Current job metadata lookup uses interpolated URL string list; equivalent candidate query cache lookup already parameterized.
- choice: Use BigQuery query parameters for `job_urls` and avoid direct string interpolation in `_load_latest_job_embedding_metadata`.
- alternatives considered:
  - keep interpolation with manual quote escaping
  - move to generic reusable query builder immediately
- impact:
  - immediate SQL safety improvement
  - improves symmetry with candidate-query lookup pattern
  - no expected output schema change

### Decision: Keep first patch bounded to RA-01

- context: `generate_embedding` has GitNexus HIGH upstream impact; broad refactor risks cross-flow regression.
- choice: patch only metadata lookup safety + parity tests now; defer higher-impact policy/abstraction work.
- alternatives considered:
  - combine RA-01 and RA-02 extraction in one patch
  - include `generate_embedding` policy refactor in same cycle
- impact:
  - faster safe delivery
  - clearer rollback path
  - preserves behavior while reducing near-term risk

### Decision: Preserve runtime mutation contract for jobs in this phase

- context: current pipeline relies on fields injected into each job (`embedding_input_signature`, `embedding_contract_fingerprint`, `embedding_reuse_status`).
- choice: preserve mutation behavior unchanged for RA-01; document as explicit compatibility invariant.
- alternatives considered:
  - make functions pure and return enriched copy
- impact:
  - avoids pipeline integration breakage
  - postpones semantic API change to future spec/plan

## Invariants

- Reuse decision logic remains: reuse only when both `embedding_input_signature` and `embedding_contract_fingerprint` match latest stored metadata.
- `embed_and_store_jobs` return value remains number of newly inserted rows.
- Job dict enrichment fields and status strings remain unchanged.
- SQLite path behavior remains unchanged.
- BigQuery inserted row keys remain unchanged, including `embedding_input_signature_payload_json`.
- No change to `SHORTLIST_SUMMARY_SCHEMA_VERSION` or fingerprint payload schema in RA-01.

## Acceptance Criteria

1. `_load_latest_job_embedding_metadata` no longer builds SQL via direct job URL interpolation.
2. Behavior parity holds for:
   - empty `job_urls` input
   - mixed reused/fresh jobs
   - unchanged inserted row payload shape
3. Unit test proves URL containing single quote does not break lookup execution path.
4. Existing reuse-status assertions in `tests/test_embeddings.py` continue passing without modification of semantics.
5. No caller-facing signature changes for `embed_and_store_jobs`.

## Non-Goals

- No change to embedding provider selection or fallback policy in `generate_embedding`.
- No extraction of shared sqlite/BigQuery backend abstraction in this patch.
- No schema migration for job/candidate embedding tables.
- No renaming of statuses or contract fields.
- No changes outside scoped targets unless test harness updates are strictly required.

## Risks and Mitigations

- Risk: BigQuery parameterization with array semantics may not match existing SQL shape.
  - Mitigation: add focused unit test with mock query parameter assertion and regression test against current returned mapping.
- Risk: hidden dependency on interpolated SQL text in tests/mocks.
  - Mitigation: update tests to assert behavior and parameter usage, not exact raw SQL formatting.
- Risk: future refactors touch high-impact `generate_embedding` path without explicit policy decision.
  - Mitigation: require separate spec/plan and GitNexus impact checkpoint before RA-04.

## Validation Plan

- proof target: Job metadata lookup is parameterized and interpolation removed
  - method: inspection + unit test
  - evidence: diff in `src/fitcv/embeddings.py` and new/updated assertion in `tests/test_embeddings.py`

- proof target: Reuse/fresh behavior remains unchanged
  - method: existing unit suite + focused regression tests
  - evidence: passing `tests/test_embeddings.py` cases that assert reuse status and inserted row count

- proof target: downstream metadata contract remains stable
  - method: inspection + test comparison
  - evidence: unchanged keys for job mutation fields and inserted rows in test expectations

- proof target: scoped patch avoids high-risk embedding policy churn
  - method: change-scope inspection (and GitNexus detect-changes during implementation phase)
  - evidence: changed files limited to scoped targets

## Completion Criteria

1. all Key Deliverables satisfied
2. downstream implementation plan authored from this spec
3. implementation patch verified with required tests and invariants
4. no unresolved decision remains for RA-01 scope
