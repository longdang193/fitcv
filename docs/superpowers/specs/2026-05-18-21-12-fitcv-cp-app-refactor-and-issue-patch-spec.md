---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-cp-app-refactor-and-issue-patch
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/app.py
related_features: []
related_stages: []
---

# Detailed Specification: fitcv_cp app.py Refactor And Issue Patch

## Goal

Define bounded, low-regression refactor and issue-patch program for `src/fitcv_cp/app.py` that enforces SSOT, symmetry, and invariance while preserving external behavior and route contracts.

### Planning Triage

Layer: change  
Feature type: MODIFY  
Summary: Normalize duplicated and divergent control-plane route/service logic in `app.py` without changing business outcomes.  
Reasoning: Change is bounded to existing runtime surface; no new product intent or workstream needed.  
Invariants:
- route paths and HTTP methods remain unchanged
- persistence semantics remain unchanged for `_CP_STORE` and BigQuery fallback
- status-driven export availability behavior remains unchanged unless explicitly documented
Dependencies:
- fresh GitNexus index for high-trust impact checks
- existing route and pipeline tests
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
- feature_docs: none
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-18-21-12-fitcv-cp-app-refactor-and-issue-patch-spec.md
- readme: none
- generated: none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### D1: Refactor boundary and sequence contract

Define phased execution order for refactor with explicit dependencies and rollback points:
- patch-first safety fixes
- service extraction for duplicated logic
- optional module split once behavior parity proven

### D2: SSOT service contracts

Define canonical contracts for:
- run retrieval and `404` handling
- settings mutation pipeline (`coerce -> validate -> save`)
- payload loading/parsing for JSON/YAML route inputs
- orchestration status access and naming

### D3: Invariance proof matrix

Define test and verification matrix that proves no behavioral regression in:
- run lifecycle actions
- export availability guards
- synonym overlay and proposal routes
- admin settings write surfaces

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and identify structural drift before edits

**Steps:**
- [ ] run `gitnexus_impact` for each target symbol before patching
- [ ] capture duplicate/divergent symbols and callsites
- [ ] baseline response behavior for representative route families

**Verification:**
- [ ] drift list covers duplication, contradiction, hidden duplication, missing contracts, risky edge cases

**Exit Criteria:**
- refactor scope bounded; no unresolved behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- decide normalization targets and abstractions

**Steps:**
- [ ] approve canonical helper/service interfaces
- [ ] approve route-level error and status invariants
- [ ] map extraction sequence: interfaces -> implementations -> callers -> tests

**Verification:**
- [ ] each target drift has single mapped corrective action

**Exit Criteria:**
- no open design ambiguity for first implementation slice

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof requirements explicit before implementation planning

**Steps:**
- [ ] define per-wave regression tests
- [ ] define GitNexus scope checks (`impact`, `detect_changes`)
- [ ] define rollback triggers and containment rules

**Verification:**
- [ ] each invariant has at least one proof target and evidence artifact

**Exit Criteria:**
- spec ready for implementation plan authoring

## Design Decisions

### Decision: Patch-first before structural extraction

- context: `app.py` includes correctness-risk drift (duplicate function definitions) and high coupling
- choice: apply smallest correctness patches first, then refactor in bounded waves
- alternatives considered:
  - immediate large module split
  - full rewrite of route services in one pass
- impact:
  - lowers first-pass regression risk
  - enables finer rollback and diff review

### Decision: Introduce SSOT helpers for repeated route patterns

- context: repeated `get_run(...)` + `404`, repeated parsing/validation, repeated settings write sequence
- choice: central helpers/services become only allowed implementation path for equivalent behavior
- alternatives considered:
  - keep inline route-local branches
  - partial dedupe only in selected routes
- impact:
  - reduced hidden duplication
  - improved symmetry and maintainability

### Decision: Treat status semantics as explicit invariants

- context: export and lifecycle behavior depends on status combinations
- choice: codify status-policy guard helpers and tests before route-level cleanup
- alternatives considered:
  - continue scattered status conditionals
- impact:
  - preserves behavior during refactor
  - prevents silent logic drift

### Decision: Use GitNexus gate for refactor slices

- context: broad call graph and many route callsites
- choice: before editing each symbol, run `gitnexus_impact`; before commit, run `gitnexus_detect_changes`
- alternatives considered:
  - source-only grep checks
- impact:
  - explicit blast-radius tracking
  - safer staged refactor

## Invariants

- public route paths, methods, and response classes remain unchanged unless explicitly approved
- `RunStatus`-driven behavior remains semantically equivalent
- `_CP_STORE` override precedence remains higher than BigQuery store fallback
- all settings writes still enforce `coerce_value` and `validate_settings` before persistence
- overlay uploads still require UTF-8 decode and schema parse validation
- all patch/refactor slices remain behavior-preserving by tests and targeted route assertions

## Acceptance Criteria

1. Duplicate `_timeline_semantic_outcome` definition reduced to single canonical implementation with parity tests.
2. All run-detail routes use one SSOT not-found helper or equivalent invariant contract.
3. Settings mutation paths share one canonical service/flow and no longer duplicate validation logic.
4. Overlay parsing and validation uses shared parser helper(s) with identical error semantics.
5. GitNexus impact report captured for each touched symbol before edit; detect-changes report captured before commit.
6. Full targeted tests and type checks pass with no externally visible route contract break.

## Non-Goals

- no route URL redesign
- no datastore migration
- no orchestration backend replacement
- no large feature addition in synonym/HITL workflows
- no public/private repo governance change

## Risks and Mitigations

- Risk: behavior drift in long `create_app` closure
  - mitigation: patch-first sequence; route-level regression tests before/after each wave
- Risk: hidden callsites missed during extraction
  - mitigation: GitNexus `impact/context/query` + ripgrep cross-checks
- Risk: inconsistent error payloads after helper centralization
  - mitigation: snapshot tests for representative error responses
- Risk: oversized PR raises review risk
  - mitigation: enforce bounded wave PRs with separate acceptance gates

## Validation Plan

- proof target: duplicate semantic-outcome bug removed without behavior loss
  - method: unit tests for timeline outcome mapping across stage aliases
  - evidence: passing tests + single function definition in `src/fitcv_cp/app.py`

- proof target: run-not-found handling symmetric across route families
  - method: route tests for JSON and HTML endpoints
  - evidence: assertions on status code and detail/message contract

- proof target: settings write invariants preserved after dedupe
  - method: table-driven tests for single-key, group, section writes
  - evidence: validation failures unchanged; persisted values unchanged

- proof target: overlay parser contract invariant
  - method: input matrix tests (empty bytes, non-UTF8, invalid YAML, bad scope)
  - evidence: stable `422/409` semantics and messages

- proof target: refactor scope stays bounded
  - method: `gitnexus_detect_changes()` before commit
  - evidence: affected symbols/processes match planned scope

- proof target: no regressions in baseline quality gates
  - method: `uvx pytest tests/` and `uvx mypy src --show-error-codes`
  - evidence: clean command outputs archived in task notes

## Completion Criteria

1. all Key Deliverables completed
2. all acceptance criteria satisfied with evidence
3. implementation plan authored from this spec with wave-level checkpoints and rollback points
4. GitNexus scope verification completed for final refactor diff
