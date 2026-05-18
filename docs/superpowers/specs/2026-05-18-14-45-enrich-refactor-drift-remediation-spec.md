---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: enrich-refactor-drift-remediation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
targets:
  - src/fitcv/enrich.py
  - tests/test_enrich.py
related_features: []
related_stages: []
---

## Goal

Define bounded refactor and patch design for `src/fitcv/enrich.py` to remove identified contract drifts, enforce SSOT and structural symmetry, and preserve external behavior.

## Key Deliverables

### Deliverable 1: Canonical enrichment row contract

Single authoritative row projection contract used by both structured and run-scoped persistence paths, including full mapping suggestion payload persistence.

### Deliverable 2: Canonical enrichment normalization contract

Single policy-backed normalization surface for synonyms, enum validation, alias mapping, and canonical value transforms used across parsing and structured output normalization.

### Deliverable 3: Persistence symmetry and reuse fidelity

Storage and reuse paths behave consistently across SQLite and BigQuery modes with explicit documented differences only where operationally required.

### Deliverable 4: Validation proof package

Executable proof set (tests, type checks, targeted inspection) demonstrating drift fixes without behavioral regression.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current contracts and drift points before edits

**Steps:**
- [ ] map current schema projection surfaces in `enrich.py`
- [ ] inventory in-memory payload fields vs persisted fields
- [ ] inventory SQLite vs BigQuery behavior differences
- [ ] baseline tests for `tests/test_enrich.py`

**Verification:**
- [ ] explicit drift inventory with source locations

**Exit Criteria:**
- no patch decision depends on implicit contract assumptions

### Wave 2: Decision closure

**Purpose:**
- close design decisions for symmetry and SSOT without behavior break

**Steps:**
- [ ] define canonical row projector abstraction
- [ ] define canonical normalization policy abstraction
- [ ] define persistence/reuse adapter boundaries
- [ ] define retry/rate-limit policy extraction boundary

**Verification:**
- [ ] each drift has explicit patch strategy and ownership

**Exit Criteria:**
- design complete enough for implementation planning

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof targets and evidence for safe handoff

**Steps:**
- [ ] map each acceptance criterion to concrete test/inspection evidence
- [ ] define regression guard tests for schema roundtrip
- [ ] define post-change static checks and contract checks

**Verification:**
- [ ] validation plan proves contract parity and no data loss

**Exit Criteria:**
- spec ready for implementation plan handoff

## Design Decisions

### Decision: Introduce `RowProjectionContract` as SSOT for persistence field mapping

- context: mapping currently split across `_map_to_structured_jobs_row` and `_map_to_run_structured_jobs_row`, with JSON-list field handling duplicated and incomplete
- choice: create shared projection helper (`project_enriched_row`) parameterized by target schema keys and injected extras (`run_id`), used by both structured and run-scoped loaders
- alternatives considered:
  - keep duplicate mappers and patch per-path
  - create separate dataclasses per storage target without shared projector
- impact:
  - removes duplicate projection logic
  - eliminates partial field drift between storage targets
  - centralizes JSON field serialization behavior

### Decision: Persist all mapping suggestion variants explicitly

- context: `domain_mapping_suggestions` and `role_family_mapping_suggestions` are produced in-memory but not explicitly persisted in BigQuery schema projection lists, while readback path expects corresponding JSON fields
- choice: add explicit JSON columns contract entries for `domain_mapping_suggestions_json` and `role_family_mapping_suggestions_json` to structured and run schema projection lists and merge columns
- alternatives considered:
  - drop domain/role mapping suggestions from runtime contract
  - encode both variants into `mapping_suggestions_json` only
- impact:
  - fixes silent non-roundtrip payload loss
  - keeps semantic separation of skill mapping vs domain/role-family mapping

### Decision: Introduce `NormalizationPolicy` parameter object

- context: repeated config reads and normalization transforms across parser and structured-normalization paths create drift risk
- choice: precompute normalization policy once per operation scope (synonyms, valid enums, alias maps, role taxonomy hints), pass policy object into coercion/builders
- alternatives considered:
  - keep per-function config lookup
  - central cache globals without explicit dependency flow
- impact:
  - reduces repeated logic and hidden divergence
  - improves testability of normalization behavior

### Decision: Introduce persistence adapter protocol for storage symmetry

- context: SQLite and BigQuery branches diverge in setup pragmas, projection fidelity, and update semantics
- choice: define protocol-level operations: `lookup_reusable`, `upsert_structured`, `append_run_structured`; implement SQLite and BigQuery adapters with shared contract functions and explicit documented operational differences
- alternatives considered:
  - keep monolithic branching in each load/lookup function
  - only normalize SQLite behavior without adapter split
- impact:
  - isolates backend-specific IO from contract logic
  - enables focused backend tests

### Decision: Normalize SQLite operational defaults across write paths

- context: `load_structured_jobs` sets WAL/synchronous/busy_timeout; `load_run_structured_jobs` does not
- choice: centralize SQLite connection setup helper and use in both paths
- alternatives considered:
  - keep asymmetry and document as incidental
- impact:
  - removes avoidable lock/perf behavior drift
  - makes local behavior predictable

### Decision: Strengthen parse error signaling contract

- context: `parse_extraction_response` returns `errors`, but coercion drops are largely silent unless JSON parse fails
- choice: preserve non-fatal behavior but append structured warnings for dropped/invalid fields (enum out-of-set, non-list coercions, invalid confidence) in `errors` with stable tags
- alternatives considered:
  - keep empty-error behavior except hard parse failures
  - raise hard errors for coercion issues
- impact:
  - better observability without changing output fallback semantics

### Decision: GitNexus-assisted impact gating for symbol edits

- context: refactor touches high-fan-in functions in large module
- choice: before editing each target symbol, run `gitnexus_impact({target, direction:"upstream"})`; if HIGH/CRITICAL risk returned, pause and confirm sequencing; run `gitnexus_detect_changes()` before commit
- alternatives considered:
  - source-only grep impact checks
- impact:
  - safer caller/update ordering and blast-radius visibility
  - explicit risk gate before patching shared symbols

## Invariants

- external behavior of enrichment output remains compatible for existing consumers
- no persisted field currently required by downstream loaders is removed
- mapping suggestion payloads roundtrip between in-memory and persistence layers
- parser remains non-throwing on malformed LLM output (fallback semantics preserved)
- SQLite mode and BigQuery mode produce equivalent semantic payloads for same enriched input (except backend-specific transport metadata)
- one canonical source-of-truth function owns row projection logic per target schema
- one canonical source-of-truth policy object owns normalization constants and alias maps per operation scope

## Acceptance Criteria

- `domain_mapping_suggestions` and `role_family_mapping_suggestions` persist and restore in both structured and run-scoped paths
- shared projector used by both structured and run-scoped mapping functions; no duplicate JSON-serialization branches remain
- normalization helpers consume `NormalizationPolicy` instead of repeated ad hoc config lookups
- SQLite write paths use shared connection setup helper with consistent pragmas
- `parse_extraction_response` emits tagged warning entries in `errors` for coercion drops while preserving parsed output semantics
- all existing enrich tests pass; new tests cover roundtrip and drift scenarios

## Non-Goals

- no provider/model behavior changes in Gemini/OpenAI client integration
- no redesign of enrichment prompt content
- no migration of entire module split in same patch set (module extraction deferred unless required for safe implementation)
- no changes to public dataset/table naming conventions

## Risks and Mitigations

- risk: schema migration mismatch in BigQuery environments
  - mitigation: explicit schema-field constants update with integration tests/inspection checklist
- risk: hidden downstream dependency on currently dropped fields
  - mitigation: additive field persistence first; no field removals in this change
- risk: behavior drift from normalization consolidation
  - mitigation: golden-case tests comparing pre/post normalization outputs
- risk: high blast radius on core helper edits
  - mitigation: GitNexus impact gate per edited symbol and small-step sequencing
- risk: validator baseline noise unrelated to change
  - mitigation: record pre-existing validator failure evidence and isolate patch scope

## Validation Plan

- proof target: persisted mapping suggestion fields roundtrip correctly
  - method: unit test and targeted integration-style mapper inspection
  - evidence: passing tests in `tests/test_enrich.py` for structured + run projection and cache readback

- proof target: shared row projector is SSOT for both projection paths
  - method: source inspection + unit tests hitting both call sites
  - evidence: single projector helper referenced by both structured/run mapping functions

- proof target: normalization symmetry preserved after policy extraction
  - method: regression tests for parser path and structured output path on identical fixtures
  - evidence: equal canonical outputs for skills/domain/job_family enums and aliases

- proof target: SQLite write-path operational symmetry restored
  - method: inspection + sqlite-mode tests
  - evidence: shared sqlite connection setup helper invoked in both write paths

- proof target: parse warning telemetry improved without hard-fail behavior changes
  - method: malformed/partial payload tests
  - evidence: `errors` populated with tagged warnings while function returns parsed payload and no exception

- proof target: no regressions in existing enrich behavior
  - method: test run + type check
  - evidence: `uv run pytest tests/test_enrich.py -q` and `uvx mypy src --show-error-codes` pass

- proof target: impact scope controlled before commit
  - method: GitNexus graph checks when tooling available
  - evidence: logged outputs from `gitnexus_impact` for touched symbols and `gitnexus_detect_changes()` before commit

## Completion Criteria

1. all Key Deliverables are satisfied
2. all acceptance criteria are met with recorded evidence
3. all validation-plan proof targets have concrete outputs
4. implementation handoff can proceed to planning without unresolved drift ambiguity

## Triage

Layer: change  
Feature type: MODIFY  
Summary: Refactor and patch enrichment contracts to remove schema/persistence/normalization drift while preserving behavior.  
Reasoning: scope is bounded to one module and its tests; no intent or operating-system governance change.  
Invariants:
- enrichment payload semantics preserved
- persistence roundtrip fidelity improved, not reduced
Dependencies:
- `src/fitcv/enrich.py`
- `tests/test_enrich.py`
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs:
  - none
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-18-14-45-enrich-refactor-drift-remediation-spec.md
- readme: none
- generated:
  - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes

## Implementation Sequencing Hint (for next skill)

Recommended patch order for `skill-writing-plans` / implementation phase:
1. Add schema-field constants + projector SSOT (additive only)
2. Add persistence of missing mapping suggestion JSON fields
3. Extract normalization policy object and adapt call sites
4. Unify SQLite connection setup helper usage
5. Enhance parser warning telemetry
6. Run full validation and GitNexus change-scope check


