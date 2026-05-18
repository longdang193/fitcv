---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-config-ssot-refactor-and-drift-patch
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv/config.py
  - src/fitcv/config_loader.py
  - src/fitcv/config_normalizers.py
  - src/fitcv/config_validators.py
  - src/fitcv/config_compat.py
related_features: []
related_stages: []
---

## Goal

Define bounded, behavior-preserving refactor and drift-remediation design for `src/fitcv/config.py` to enforce SSOT ownership, reduce structural complexity, and isolate temporary compatibility logic without changing external runtime contracts.

## Key Deliverables

### Deliverable 1: Modular config architecture spec

Define target module split and public API boundary so config loading, normalization, validation, and compatibility projection each have single ownership.

### Deliverable 2: SSOT drift patch spec

Define enforceable overlap policy (warn vs strict fail), legacy-surface deprecation path, and deterministic merge/normalize pipeline that removes current drift-prone ordering and duplicate transforms.

### Deliverable 3: Verification contract spec

Define evidence-grade validation matrix covering behavior parity, SSOT policy checks, compatibility window safety, and GitNexus blast-radius checks before/after implementation.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish exact current behavior, drift surfaces, and coupling map before design closure

**Steps:**
- [ ] baseline current `src/fitcv/config.py` call flow and side effects
- [ ] document current drift points:
  - duplicate normalization pass in `load_config`
  - mixed canonical + legacy ownership in same execution path
  - warning-only SSOT overlap enforcement
  - temporary compatibility projection still active
- [ ] capture symbol set to refactor:
  - `load_config`
  - `_normalize_config_keys`
  - `_detect_env_canonical_ownership_overlaps`
  - `_detect_pipeline_ssot_overlap`
  - `apply_cv_compatibility_projection`

**Verification:**
- [ ] current-state map includes input precedence, mutation order, and validation order

**Exit Criteria:**
- no target refactor decision depends on unstated behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- finalize refactor shape and drift controls with SSOT invariants explicit

**Steps:**
- [ ] define module extraction and ownership boundaries
- [ ] define canonical single-pass normalization/validation pipeline
- [ ] define strict SSOT mode behavior and migration toggles
- [ ] define legacy compatibility adapter containment and sunset signals
- [ ] define GitNexus-gated implementation sequence

**Verification:**
- [ ] every non-trivial design choice has accepted alternative analysis and rationale

**Exit Criteria:**
- design is coherent, bounded, and implementation-ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof plan and completion evidence before implementation planning

**Steps:**
- [ ] define tests and static checks needed for behavior parity
- [ ] define GitNexus risk and scope verification gates
- [ ] define doc/test updates required with code changes

**Verification:**
- [ ] validation plan proves both functional parity and SSOT drift reduction

**Exit Criteria:**
- spec is ready for implementation-plan handoff

## Design Decisions

### Decision: Split `config.py` by responsibility with thin facade

- context: monolithic module mixes IO, env override, normalization, SSOT auditing, compatibility projection, and getters in one file, increasing change risk and cognitive load
- choice: extract into focused modules:
  - `config_loader.py`: env path resolution, YAML loading, policy-file discovery/merge
  - `config_normalizers.py`: all `_normalize_*`, overlay normalizers, key projection transforms
  - `config_validators.py`: prompt/cv/control-plane/SSOT validation and overlap checks
  - `config_compat.py`: all temporary legacy compatibility projection and legacy bridge keys
  - `config.py`: stable facade exports and orchestration only
- alternatives considered:
  - keep single file and only reorder internals
  - partial split (compat only)
- impact:
  - lower blast radius per change
  - clearer test ownership by module
  - no external import contract break at facade level

### Decision: Canonical deterministic pipeline with single normalization stage

- context: `load_config` currently normalizes keys twice and interleaves compatibility paths, increasing order-coupling and drift risk
- choice: enforce one pipeline:
  1. source selection and load
  2. source fallback backfill (legacy only where required)
  3. env overrides (infra/control-plane)
  4. policy backfill (no overwrite)
  5. one canonical normalization pass
  6. one validation pass
  7. optional compatibility projection (explicitly marked)
- alternatives considered:
  - keep dual normalization for defensive behavior
  - normalize per-stage opportunistically
- impact:
  - deterministic outcomes
  - fewer hidden mutations
  - easier regression tests

### Decision: Enforce SSOT via mode switch (`warn` default, `strict` opt-in)

- context: overlap detectors exist but only warn; canonical owner policy not enforceable in CI when desired
- choice: introduce runtime/configurable SSOT enforcement mode:
  - `warn`: keep existing compatibility behavior
  - `strict`: raise error for ownership overlaps and pipeline/env overlap conflicts
- alternatives considered:
  - strict always-on immediately
  - warnings only forever
- impact:
  - safer migration path
  - enables progressive hardening and CI adoption

### Decision: Isolate temporary compatibility projection and define removal hooks

- context: temporary compatibility projections are distributed and can leak into long-term architecture
- choice: contain all temporary projection behavior in `config_compat.py` with explicit comments, feature flag, and deprecation telemetry/log marker
- alternatives considered:
  - inline compatibility logic in main orchestration
  - immediate removal (high break risk)
- impact:
  - clear cleanup boundary
  - prevents hidden legacy coupling growth

### Decision: GitNexus-gated refactor sequence for safety

- context: refactor touches central config flow with multi-caller risk
- choice: implementation must follow `gitnexus-refactoring` workflow:
  1. `gitnexus_impact` on each target symbol before edits
  2. `gitnexus_context` for call/callee graph
  3. staged edits in order: interfaces -> implementation -> callers -> tests
  4. `gitnexus_detect_changes()` before commit
- alternatives considered:
  - source-only grep tracing
- impact:
  - reduced missed-caller risk
  - explicit blast-radius control

## Invariants

- public behavior of `load_config`, `load_control_plane_config`, and `resolve_data_backend` remains backward compatible during compatibility window
- env variable precedence remains unchanged unless explicitly documented as SSOT strict-mode enforcement behavior
- policy YAML files never overwrite explicit env-config values in compatibility mode
- secret-oriented control-plane keys remain forbidden and validated
- all temporary compatibility behavior remains isolated to dedicated compatibility layer
- SSOT canonical ownership sets remain single source of truth for overlap detection rules

## Acceptance Criteria

1. `src/fitcv/config.py` reduced to facade/orchestration responsibilities only; extracted modules own separated concerns.
2. `load_config` executes one normalization pass and one validation pass only.
3. SSOT overlap policy supports `warn` and `strict` modes with deterministic behavior and tests.
4. Compatibility projection behavior unchanged for legacy consumers in default mode.
5. New and updated tests prove no regression in backend resolution, prompt defaults, CV policy normalization, and required key validation.
6. GitNexus impact/context checks recorded for each edited primary symbol before implementation edits.

## Non-Goals

- redesigning configuration product semantics or introducing new config schema families
- removing legacy compatibility projection in this patch
- changing default backend selection policy (`bigquery` fallback remains)
- introducing unrelated feature changes outside config loading/validation stack

## Risks and Mitigations

- Risk: Hidden callers depend on intermediate mutated state in `load_config`.
  - Mitigation: GitNexus impact/context before edits; parity tests at facade API level.
- Risk: Strict SSOT mode introduces rollout friction.
  - Mitigation: default `warn`, explicit opt-in strict mode, CI can enable gradually.
- Risk: Module split causes circular imports.
  - Mitigation: define unidirectional dependency graph (`loader -> normalizers -> validators -> compat`), keep getters in facade or dedicated read-only helper.
- Risk: Temporary compatibility layer persists indefinitely.
  - Mitigation: deprecation marker + explicit removal follow-up plan item in implementation plan.

## Validation Plan

- proof target: refactor preserves externally observable config behavior in compatibility mode
  - method: pytest regression suite for `load_config`, `resolve_data_backend`, CV and prompt helpers
  - evidence: passing tests under `tests/` covering pre-existing and split-module paths

- proof target: SSOT drift controls are enforceable
  - method: unit tests for overlap detectors and mode-gated behavior (`warn` logs vs `strict` errors)
  - evidence: targeted tests asserting warning/error outcomes for env/pipeline/taxonomy overlap fixtures

- proof target: structural complexity reduced without dead behavior
  - method: inspection + import/use checks + mypy
  - evidence: `uvx mypy src --show-error-codes` clean for refactored modules

- proof target: refactor blast radius is understood and bounded
  - method: GitNexus workflow (`gitnexus_impact`, `gitnexus_context`, `gitnexus_detect_changes`)
  - evidence: recorded symbol impact outputs and detect-changes report aligned to expected scope

- proof target: repo governance checks remain green
  - method: fast validator hook commands
  - evidence: `python scripts/hooks/run_validator.py --fast` passing after spec-linked implementation

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Planning Dispatch Triage

Layer: change  
Feature type: MODIFY  
Summary: Refactor `src/fitcv/config.py` into SSOT-aligned modular architecture and patch identified drift points without external behavior break.  
Reasoning: bounded execution-focused refactor with defined code target and no intent/governance redesign.  
Invariants:
- preserve public config API compatibility
- preserve default behavior in compatibility mode
- enforce SSOT ownership checks via controlled mode switch
Dependencies:
- GitNexus fresh index for impact/context/detect_changes workflow
- existing config tests plus new targeted drift tests
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
    - docs/superpowers/specs/2026-05-18-15-52-config-ssot-refactor-drift-spec.md
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
