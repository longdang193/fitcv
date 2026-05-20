---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: candidate-module-ssot-symmetry-invariance-refactor
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
targets:
  - src/fitcv/candidate.py
  - tests/test_candidate.py
related_features: []
related_stages: []
---

## Goal

Define bounded, patch-ready refactor for `src/fitcv/candidate.py` that establishes SSOT normalization/validation flow, restores symmetry across equivalent profile concepts, and enforces invariance for schema/default/rule handling without changing intended external behavior.

## Key Deliverables

### Deliverable 1: SSOT candidate profile contract path

One canonical internal path (`normalize -> validate -> consume`) used consistently by loader functions and direct-consumer helpers (`infer_effective_preferences`, `prepare_profile_rows`) so all flows operate on same normalized shape.

### Deliverable 2: Symmetric section handling model

Shared section policies for list/text normalization, id-bearing sections, and evidence-reference sections, replacing ad-hoc section-specific drift.

### Deliverable 3: Explicit invariants and proof targets

Concrete invariants for skills shape, required section behavior, evidence reference semantics, and parser error consistency, each tied to testable evidence.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and drift boundaries before edits

**Steps:**
- [ ] capture baseline contracts from `src/fitcv/candidate.py`
- [ ] classify equivalent concepts:
  - profile parsing (`load_profile_yaml`, `load_profile_json_text`, `load_profile_text`)
  - normalization (`_normalize_profile_alignment_metadata`, `_normalize_text_list`, `_normalize_text`)
  - validation (`validate_profile`)
  - consumption (`flatten_skills`, `prepare_profile_rows`, `infer_effective_preferences`)
- [ ] map contradictions and duplication with line anchors

**Verification:**
- [ ] findings matrix fully mapped to code lines and existing tests

**Exit Criteria:**
- no planned refactor step depends on unstated behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- finalize contract decisions and bounded patch order

**Steps:**
- [ ] decide canonical internal entrypoint for normalized profile consumption
- [ ] decide skills shape policy (strict dict-only vs backward-compatible dual-shape)
- [ ] define shared constants for id-bearing and evidence-bearing sections
- [ ] define parser error contract unification target
- [ ] define extraction boundaries for shared normalization helpers

**Verification:**
- [ ] each design decision includes rationale, alternatives, impact

**Exit Criteria:**
- patch sequence can run incrementally with passing tests after each action

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof plan and migration/safety controls

**Steps:**
- [ ] define unit tests to lock invariants
- [ ] define compatibility/deprecation controls
- [ ] define rollback containment trigger and steps
- [ ] define completion criteria for handoff to implementation plan

**Verification:**
- [ ] every invariant has at least one proof target and evidence artifact

**Exit Criteria:**
- spec ready for implementation planning with bounded risk

## Design Decisions

### Decision: Introduce internal normalized profile boundary

- context: normalization currently loader-coupled; direct helper calls may bypass normalization.
- choice: add internal helper (`_ensure_normalized_profile`) and route core consumers through it.
- alternatives considered:
  - leave normalization only in loaders
  - duplicate normalization per consumer
- impact:
  - restores SSOT for profile shape
  - lowers drift risk across inference/row-prep paths

### Decision: Keep external API signatures stable

- context: module is used across pipeline, validator, vector search, control-plane callsites.
- choice: no public function rename or signature change in first patch set.
- alternatives considered:
  - immediate API cleanup/renames
- impact:
  - minimizes blast radius
  - enables incremental safe rollout

### Decision: Make section-role constants explicit

- context: required sections and id/evidence participants mixed implicitly.
- choice: split constants:
  - required sections
  - id-bearing sections
  - evidence-ref sections
- alternatives considered:
  - keep implicit hardcoded loops
- impact:
  - improves symmetry and readability
  - reduces contradiction risk

### Decision: Resolve skills-shape drift via compatibility-first normalization

- context: `validate_profile` rejects string skills while consumers accept strings.
- choice: phase 1 compatibility: normalize string skills into canonical dict form before validation checks that require dict-only behavior.
- alternatives considered:
  - strict reject string skills everywhere now
  - keep contradictory behavior
- impact:
  - preserves existing behavior expected by tests/callers
  - creates migration path to stricter schema later

### Decision: Unify parser error semantics

- context: JSON parse errors differ between `load_profile_json_text` and `load_profile_text(format_hint='json')`.
- choice: use shared parse helper returning consistent `ValueError` contract while preserving error category.
- alternatives considered:
  - leave split UX/messages
- impact:
  - consistent caller UX and easier testing

## Invariants

- Invariant 1: All candidate-profile consumer paths use same normalized structural assumptions.
- Invariant 2: Equivalent section concepts follow equivalent handling rules (text/list/id/evidence).
- Invariant 3: Explicit user preference values are never overwritten by inferred values.
- Invariant 4: Referential integrity validation remains enforced for evidence refs.
- Invariant 5: Public function signatures and intended output keys remain stable for first refactor wave.

## Acceptance Criteria

1. `load_profile_yaml`, `load_profile_json_text`, and `load_profile_text` yield equivalent normalized structures for equivalent payloads.
2. `infer_effective_preferences` and `prepare_profile_rows` operate safely when called with minimally normalized input.
3. skills-shape behavior is non-contradictory (single declared policy, codified in tests).
4. parser error behavior for JSON is consistent across JSON entrypoints.
5. `tests/test_candidate.py` passes with added/updated invariance tests.

## Non-Goals

- No BigQuery schema redesign.
- No pipeline-wide refactor outside direct `candidate.py` contract consumers.
- No feature/stage lifecycle metadata restructuring.
- No migration to pydantic/dataclass global schema in this patch wave.

## Risks and Mitigations

- Risk: hidden downstream reliance on contradictory skills behavior.
  - Mitigation: compatibility-first normalization + targeted regression tests.
- Risk: normalization centralization changes edge ordering/casing unexpectedly.
  - Mitigation: snapshot-like assertions for normalized outputs in tests.
- Risk: parser message changes break brittle tests.
  - Mitigation: update tests to assert error class + stable key phrase contract.
- Risk: refactor broadens change scope.
  - Mitigation: keep edits bounded to `candidate.py` and `tests/test_candidate.py` in first wave.

## Validation Plan

- proof target: loader normalization parity across yaml/json/text
  - method: unit test comparison of normalized output dicts
  - evidence: passing tests in `tests/test_candidate.py`

- proof target: invariance of explicit preference precedence
  - method: unit tests for explicit vs inferred preference resolution
  - evidence: existing + updated preference tests pass

- proof target: skills-shape contract consistency
  - method: targeted tests for string and dict skill entries under declared policy
  - evidence: no contradictory assertions between validation and row prep tests

- proof target: parser error contract symmetry
  - method: unit tests for invalid JSON through both JSON code paths
  - evidence: matching `ValueError` pattern assertions

- proof target: bounded impact
  - method: source inspection + test-module scope check
  - evidence: diff constrained to scoped files and expected test updates

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Triage Block

Layer: change  
Feature type: MODIFY  
Summary: Refactor candidate profile handling in `candidate.py` for SSOT, symmetry, invariance while preserving behavior.  
Reasoning: Bounded code-level contract cleanup; no intent/workstream/operating-system governance change.  
Invariants:
- maintain public API signatures
- maintain explicit-preference precedence
- maintain referential-integrity checks
Dependencies:
- `tests/test_candidate.py` contract updates
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
  - docs/superpowers/specs/2026-05-20-15-12-candidate-ssot-symmetry-invariance-spec.md
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


