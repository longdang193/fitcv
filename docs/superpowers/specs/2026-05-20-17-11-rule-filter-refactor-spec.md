---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: rule-filter-ssot-symmetry-invariance-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
targets:
  - src/fitcv/rule_filter.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/validator.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/cv_generator.py
  - tests/test_rule_filter.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features:
  - cv_system
related_stages:
  - rule_filter
---

## Goal

Define bounded, testable refactor specification for rule-filter subsystem that consolidates SSOT, restores structural symmetry across equivalent concepts, and enforces invariants across runtime, settings, pipeline artifacts, and downstream skill-canonicalization consumers.

## Key Deliverables

### Deliverable 1: Rule-filter signal model SSOT

Canonical signal registry defined for post-enrichment deterministic filter signals, including code, label, default blocking mode, and optional mark-details builder; all selected-filter defaults and selectable options derive from this registry.

### Deliverable 2: Symmetric predicate and mark evaluation pipeline

Equivalent rule-filter concepts (predicate check, rejection code, mark details, default behavior) aligned to single structure to eliminate duplicated condition wiring and hidden branching asymmetry.

### Deliverable 3: Public normalization/canonicalization contract

Stable public API for skill canonicalization and related synonym resolution established, replacing private underscore-import coupling across validator, gap analysis, and CV generation.

### Deliverable 4: Input-shape hardening and explicit fail-open contracts

List-like preference/config/global-setting inputs normalized through shared guards, with documented fail-open/fail-closed decisions for malformed values.

### Deliverable 5: Contract and documentation convergence

Return-shape docs, test naming, defaults, and deprecation notes aligned with actual behavior; obsolete imports and dead compatibility surfaces explicitly handled.

## Task/Wave Breakdown

### Wave 1: Source-first analysis and contract inventory

**Purpose:**
- consolidate current state for equivalent concepts, drift points, and invariants before design closure

**Steps:**
- [ ] map equivalent concepts across `rule_filter.py`, `settings_schema.py`, `pipeline.py`, and tests
- [ ] classify all findings into drifts, contradictions, obsolete/dead, hidden duplication, missing contracts, and edge risks
- [ ] record explicit compatibility obligations for pipeline stage and settings surfaces

**Verification:**
- [ ] inventory captures all RF-01..RF-05 scope boundaries and affected files

**Exit Criteria:**
- no refactor action depends on unstated assumptions about defaults, output shape, or pipeline coupling

### Wave 2: Decision closure for RF-01..RF-05

**Purpose:**
- convert findings into coherent refactor decisions with strict boundaries

**Steps:**
- [ ] define signal-registry SSOT design (RF-01)
- [ ] define duplicated must-have-skill normalization extraction (RF-02)
- [ ] define public canonicalization API migration design (RF-03)
- [ ] define input normalization guard strategy (RF-04)
- [ ] define doc/deprecation cleanup rules (RF-05)

**Verification:**
- [ ] each RF item has explicit implementation boundary, risk level, and dependency order

**Exit Criteria:**
- all major design questions resolved or explicitly deferred with rationale

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof plan that enforces invariance and prevents regression

**Steps:**
- [ ] define acceptance criteria and non-goals
- [ ] define invariant-preservation tests and schema checks
- [ ] define migration, rollback, and containment controls

**Verification:**
- [ ] validation plan includes concrete evidence artifacts and command-level proof targets

**Exit Criteria:**
- spec ready for implementation planning handoff without additional design discovery

## Design Decisions

### Decision: Centralize rule-filter signal registry (RF-01)

- context: signal code, labels, and default selected filters currently duplicated across runtime, settings schema defaults, and pipeline artifact fallback logic
- choice: create canonical registry structure in `src/fitcv/rule_filter.py` (or dedicated adjacent module) with fields:
  - `code`
  - `label`
  - `default_blocking: bool`
  - `mark_builder: callable | none`
  - `predicate: callable resolver`
- alternatives considered:
  - keep duplication with periodic parity tests only
  - move registry into settings schema and import into runtime
- impact:
  - `settings_schema` selectable options/default list generated from registry export
  - `pipeline` selected-filter fallback generated from same export
  - `KNOWN_RULE_FILTER_SIGNAL_CODES` derived, not hand-maintained

### Decision: Extract symmetric skill-set preparation helper (RF-02)

- context: must-have evaluation and missing-skill mark details duplicate canonicalization and source-field branching
- choice: create single helper for obtaining canonical job-skill set and canonical must-have set, reused by both pass/fail and details generation
- alternatives considered:
  - keep duplicated logic with comments
- impact:
  - eliminates dual maintenance
  - guarantees same canonicalization semantics for reject reason and mark details payload

### Decision: Promote public skill canonicalization API (RF-03)

- context: multiple modules import private underscore helpers from rule_filter
- choice: expose public API (`canonicalize_skill`, `get_skill_synonyms`) in dedicated normalization boundary (`rule_filter` public exports or new `skill_normalization.py`)
- alternatives considered:
  - keep underscore imports and document as accepted exception
- impact:
  - explicit contract for cross-module dependencies
  - enables future decoupling of rule filtering from skill normalization concerns

### Decision: Normalize list-like and scalar config inputs with typed guards (RF-04)

- context: prefs/settings fields can be malformed and currently may iterate string chars or throw on int conversion
- choice: introduce shared normalization helpers:
  - normalize string list inputs (`domains`, `preferred_domains`, `exclude_contract_types`, etc.)
  - safe int parsing with fallback for `global_job_filters.max_age_days` and related values
- alternatives considered:
  - rely on upstream settings validation only
- impact:
  - runtime robustness independent of caller quality
  - explicit fail-open semantics preserved where required

### Decision: Converge contracts and deprecate stale compatibility surface (RF-05)

- context: docs and test naming drift from actual behavior; `global_settings` arg on `apply_rule_filters` retained but unused
- choice:
  - align return-contract docs with actual `passed_records` inclusion
  - rename contradictory test names to current behavior
  - remove unused imports
  - add soft deprecation note/log path for unused compatibility arg if removal not immediate
- alternatives considered:
  - no deprecation path; keep silent compatibility forever
- impact:
  - clearer public contract
  - reduced confusion in future maintenance and reviews

## Invariants

- pre-enrichment global filters (`job_too_stale`, `applications_count_exceeded`) remain exclusively in `apply_pre_enrichment_global_filters`
- post-enrichment deterministic rule checks remain exclusively in `apply_rule_filters`
- selected filters produce `reasons`; unselected failures produce `marks`
- output shape of `apply_rule_filters` remains backward compatible for existing consumers
- unknown or missing job fields keep fail-open behavior unless explicitly reclassified and approved
- pipeline stage artifacts and control-plane settings use same selected-filter source of truth
- canonicalization result for existing skill synonym cases remains unchanged

## Acceptance Criteria

1. single canonical source exists for rule-filter signal codes, labels, and default selected set; no duplicated hardcoded default list remains in runtime/settings/pipeline
2. must-have skills pass/fail logic and missing-skill mark details use same normalized canonical sets
3. no module outside rule-filter boundary imports underscore/private canonicalization helpers
4. malformed list/scalar config inputs do not crash rule-filter path; behavior follows documented fail-open/fail-closed rules
5. rule-filter docs and tests reflect actual runtime output/behavior without contradictory naming
6. all relevant existing tests pass, plus new parity/robustness contract tests

## Non-Goals

- changing business meaning of existing filter signals (seniority/location/contract/experience/must-have/domain)
- introducing new ranking, enrich, shortlist, or CV-generation policy semantics
- changing BigQuery table schema for `rule_filter_results`
- redesigning pipeline-stage sequence or control-plane workflow model
- broad repo-wide normalization refactor outside directly coupled rule-filter/canonicalization surfaces

## Risks and Mitigations

- risk: subtle behavior drift from registry centralization
  - mitigation: parity tests asserting pre/post equivalent outputs for representative job/prefs/config fixtures
- risk: cross-module breakage during canonicalization API migration
  - mitigation: staged shim exports with temporary alias support and targeted regression tests in validator/gap/cv paths
- risk: hidden dependency on duplicated default lists
  - mitigation: dedicated invariant test asserting equality among runtime selected defaults, settings default, and pipeline artifact default source
- risk: stricter input normalization changes effective filtering in edge inputs
  - mitigation: explicit malformed-input tests documenting old vs intended behavior and approval gate for any semantic changes

## Migration and Safety Controls

### Backward compatibility

- preserve `apply_rule_filters` response keys consumed by pipeline/tests (`passed`, `rejected`, `passed_records`)
- preserve existing reason codes and mark payload keys
- preserve settings key path `rule_filter.selected_filters`

### Deprecation/removal path

- phase 1: introduce public canonicalization API and migrate imports
- phase 2: keep temporary compatibility alias for underscore helpers with deprecation comment
- phase 3: remove private import dependence after all call sites migrated and tests stable
- phase 4: evaluate removal of unused `global_settings` arg on `apply_rule_filters` through explicit deprecation notice and call-site audit

### Rollback/containment

- implement RF actions in isolated commits by action id order
- keep registry introduction and behavior-preserving refactor separate from stricter normalization changes
- if regression appears, rollback latest action-scope commit without reverting earlier stabilized SSOT work

## Validation Plan

- proof target: signal registry is single SSOT for defaults/options
  - method: inspection + unit tests
  - evidence: tests assert equality between runtime-export defaults, settings schema default, and pipeline artifacts default

- proof target: no duplicated must-have canonicalization path remains
  - method: inspection + unit tests
  - evidence: helper-based shared path in source and unchanged outcomes for existing must-have test cases

- proof target: no private underscore canonicalization imports in dependent modules
  - method: static grep assertion
  - evidence: `rg "from fitcv.rule_filter import _canonical" src/fitcv` returns empty

- proof target: malformed input shapes do not crash and follow declared behavior
  - method: unit tests with malformed prefs/settings payloads
  - evidence: new tests in `tests/test_rule_filter.py` covering string/list/int/None anomalies

- proof target: contract/docs/test naming convergence
  - method: inspection + test run
  - evidence: updated docstrings/comments and renamed contradictory tests passing in CI

- proof target: no behavioral regression in rule-filter/pipeline coupling
  - method: targeted test runs
  - evidence: passing `tests/test_rule_filter.py`, rule-filter-related subsets in `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_settings_schema.py`

## Completion Criteria

1. all Key Deliverables resolved with approved design boundaries
2. RF-01..RF-05 action scopes defined with dependency order and risk controls
3. acceptance criteria fully testable with identified evidence surfaces
4. invariants explicitly preserved or approved for change
5. spec ready for plan handoff (`skill-writing-plans`) with no unresolved design blockers
