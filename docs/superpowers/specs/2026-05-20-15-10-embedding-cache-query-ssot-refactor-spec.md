---
layer: change
artifact_type: spec
status: completed
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

### Wave 4: RA-02 extraction execution wave

**Purpose:**
- execute cross-module helper extraction after RA-01 invariants lock

**Steps:**
- [x] extract shared BigQuery-client construction into `shortlist_runtime.py`
- [x] update `embeddings.py` and `vector_search.py` to consume shared helper
- [x] verify parity on embedding/vector unit tests

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`
- [x] `pytest tests/test_vector_search.py -q`

**Exit Criteria:**
- duplicated cross-module setup is reduced without contract drift

### Wave 5: RA-03 and RA-05 cleanup execution wave

**Purpose:**
- consolidate SSOT serialization/fingerprint logic and remove obsolete wrappers

**Steps:**
- [x] centralize contract fingerprint generation via shared helper
- [x] remove dead `_canonicalize_for_hash` wrappers
- [x] unify payload-json derivation to canonical `hash_payload` output

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`
- [x] `pytest tests/test_vector_search.py -q`

**Exit Criteria:**
- equivalent concepts now use symmetric implementation paths

### Wave 6: RA-04 high-impact degradation-policy wave

**Purpose:**
- encode explicit degradation policy for high-impact `generate_embedding` path

**Steps:**
- [x] add explicit failure-policy resolver and policy constants
- [x] preserve default fallback behavior; add explicit raise policy branch
- [x] add/expand tests to prove policy branch behavior

**Verification:**
- [x] `pytest tests/test_embeddings.py -q`

**Exit Criteria:**
- high-impact path has explicit policy control with default semantics preserved

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

### Decision: Explicit post-RA-01 sequencing for RA-02/03/04/05

- context: follow-on refactors differ in blast radius and risk-reduction value.
- choice:
  - RA-04 touches high-impact `generate_embedding` path (GitNexus HIGH) and requires explicit degradation-policy decision in a dedicated spec before implementation.
  - RA-02 is broad extraction across modules and executes only after query/failure invariants are locked and accepted.
  - RA-03 and RA-05 remain valid cleanup actions, but are lower risk-reduction priority than RA-01.
- alternatives considered:
  - parallelize RA-02 and RA-04 immediately after RA-01
  - run RA-03/RA-05 before RA-02/RA-04 without policy lock
- impact:
  - keeps highest-risk policy work gated by explicit decision records
  - avoids premature cross-module extraction before invariant lock
  - preserves momentum while prioritizing risk-reduction order

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

## Scope Evolution Note

- Initial scope: RA-01 only.
- Approved execution expansion: RA-02 through RA-05 executed in same lane after explicit sequencing update.
- High-impact RA-04 governance handling: implemented with explicit degradation-policy gate while preserving default runtime behavior.

## Execution Update (Scope Extension Applied)

This lane moved beyond RA-01 and executed concrete RA-02 through RA-05 follow-ons with safety gates:

- RA-02: extraction across `embeddings.py`, `vector_search.py`, and shared `shortlist_runtime.py`.
- RA-03: shared contract-fingerprint normalization helper applied.
- RA-04: explicit degradation-policy decision encoded in runtime (`embedding_failure_policy`), preserving current default fallback behavior.
- RA-05: duplicate/dead helper cleanup and payload-json derivation symmetry fixes applied.

High-impact notes:

- `generate_embedding` impact remains HIGH in GitNexus; execution preserved default behavior and added explicit policy gate rather than changing default semantics.
