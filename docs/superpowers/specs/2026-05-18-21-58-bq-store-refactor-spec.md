---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: bq-store-ssot-symmetry-invariance-refactor
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/bq_store.py
related_features: []
related_stages: []
---

## Goal

Define bounded, behavior-preserving refactor for `src/fitcv_cp/bq_store.py` that removes structural drift and duplication across local/sqlite, BigQuery, and legacy-fallback persistence paths while enforcing SSOT, symmetry, and invariance.

## Key Deliverables

### Refactor contract for run mutation paths

Specify single internal mutation pattern used by all `pipeline_runs` update functions, including retry behavior, local/BQ mode handling, and legacy schema degradation behavior.

### Unified persistence/degradation outcome contract

Specify one explicit result model for operations that can degrade (`append_event`, schema-fallback updates, dead-letter paths), including canonical status and reason vocabulary.

### Shared normalization contract

Specify one normalization strategy for JSON decode/default behavior and one coercion strategy for typed fields (timestamps, integers, enum/status).

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- capture current behavior and structural asymmetry before refactor decisions

**Steps:**
- [x] inspect `bq_store.py` update/read paths for equivalent concepts
- [x] record drift/contradiction/duplication/edge-case findings
- [x] check GitNexus freshness and refresh index (`npx gitnexus analyze`)
- [x] collect skill constraints from `skill-spec-drafting`, `gitnexus-refactoring`, `skill-python-refactoring-expert`

**Verification:**
- [x] findings mapped to concrete functions and contracts in scope

**Exit Criteria:**
- no core design decision depends on hidden assumptions

### Wave 2: Decision closure

**Purpose:**
- close design for safe refactor sequence and bounded patch set

**Steps:**
- [ ] define internal SSOT helpers for run mutation, JSON normalization, and degradation status
- [ ] define compatibility boundaries (public signatures, fallback behavior, return-shape handling)
- [ ] define phased migration sequence minimizing caller breakage

**Verification:**
- [ ] each design choice has selected alternative and migration implication

**Exit Criteria:**
- design internally coherent and implementation-plan ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof obligations showing behavior preserved and drift reduced

**Steps:**
- [ ] define tests for local mode, BQ mode, retry/fallback, and degraded states
- [ ] define invariants and expected evidence for each refactor phase
- [ ] define rollback and containment controls

**Verification:**
- [ ] validation plan covers all modified equivalence classes

**Exit Criteria:**
- spec approved for plan drafting and implementation

## Design Decisions

### Decision: Introduce single internal run-field mutation primitive

- context: `update_run_*` functions duplicate same shape (local `dataclasses.replace` + BQ `UPDATE` + retry/fallback branches), with drift (`update_run_effective_settings` bypasses retry, inconsistent fallback return contracts).
- choice: add internal helper (for example `_mutate_run_field(...)`) that centralizes:
  - local mode mutation/load/save
  - BQ parameterized update execution
  - retry policy via `_execute_query_with_pipeline_runs_retry`
  - optional legacy-column fallback policy
- alternatives considered:
  - keep per-function manual SQL updates (rejected: preserves drift/duplication)
  - rewrite external API into one generic public updater (deferred: larger caller migration risk)
- impact:
  - public `update_run_*` functions remain stable wrappers
  - structural symmetry improves; regressions become testable at helper layer

### Decision: Standardize persistence outcome model

- context: current success/degradation return payloads diverge (`"none"` vs `""`, dict-return on some functions and `None` elsewhere).
- choice: define canonical internal outcome model (`status`, `reason`, optional metadata) and adapt existing public functions:
  - functions currently returning dict keep dict shape but use standardized values
  - `None`-return mutators stay `None` in phase 1 (backward-compat), with optional future harmonization spec
- alternatives considered:
  - immediate external API unification across all mutators (rejected now: medium-high caller compatibility risk)
- impact:
  - logs/tests gain consistent degradation semantics
  - no immediate breaking interface change

### Decision: Consolidate JSON decode/default normalization

- context: repeated JSON parse logic has different defaults (`None`, `[]`, silent skip).
- choice: add shared internal decode helpers with explicit policy per field class:
  - object-like optional JSON -> `None` on invalid
  - list-like collection JSON -> `[]` or `None` per declared contract
  - corrupted line-based event replay -> skip record with counted warning
- alternatives considered:
  - leave local inline parsing (rejected: hidden duplication, inconsistent behavior)
- impact:
  - invariance of parse behavior across surfaces
  - easier edge-case testing

### Decision: Explicit legacy schema capability gating

- context: unrecognized-column fallbacks implemented ad hoc for some columns/functions.
- choice: centralize legacy-missing-column handling behind shared helper and declared capability map for `pipeline_runs`/other table columns.
- alternatives considered:
  - catch-and-ignore errors inline per function (rejected: contradiction risk)
- impact:
  - stable downgrade behavior during staggered migrations
  - clearer operational visibility

### Decision: Refactor sequencing follows GitNexus refactoring workflow

- context: safe refactor needs caller-aware updates and bounded blast radius.
- choice: for implementation phase, enforce sequence:
  - impact/context check before editing each targeted symbol
  - interfaces/helpers first, then wrappers, then tests
  - `gitnexus_detect_changes()` before commit
- alternatives considered:
  - opportunistic edits without graph checks (rejected: hidden dependency risk)
- impact:
  - lower cross-file regression risk

## Invariants

- External behavior remains unchanged for successful paths.
- Public function names and signatures in `bq_store.py` remain stable in phase 1.
- Local mode (`bq is None`) remains supported for runs, events, and CV rows.
- BigQuery write paths remain parameterized SQL/insert APIs (no string interpolation for values).
- Retry semantics for `pipeline_runs` updates remain active and become consistent.
- Legacy-schema fallback behavior is preserved where already implemented.
- Event ordering/read semantics remain deterministic (`created_at` ascending for events, descending for runs).
- Archive visibility semantics in `list_runs` remain unchanged.

## Acceptance Criteria

1. Equivalent mutators for run fields use single internal mutation primitive.
2. `update_run_effective_settings` uses same retry policy as peer mutators.
3. Degradation reason vocabulary is canonicalized and documented.
4. JSON parsing behavior for repeated field classes is centralized and test-covered.
5. Existing public callers require no signature-level changes.
6. Legacy fallback paths are explicit and regression-tested.

## Non-Goals

- No redesign of domain models (`PipelineRun`, `RunEvent`, `RunStatus`).
- No migration of storage backend architecture beyond scoped refactor.
- No broad cross-module API unification beyond `bq_store.py` scope.
- No feature-level behavior changes in job filtering/ranking/CV generation logic.

## Risks and Mitigations

- Risk: hidden caller reliance on current ad-hoc return payloads.
  - Mitigation: phase 1 preserves public return shapes; add tests for caller-visible payloads.
- Risk: fallback-policy consolidation alters legacy behavior.
  - Mitigation: golden tests for current fallback cases (missing columns, dead-letter behavior).
- Risk: helper extraction introduces subtle local/BQ parity bugs.
  - Mitigation: backend-matrix tests (`bq=None`, BQ success, BQ transient failure, BQ missing-column).
- Risk: stale graph assumptions in refactor ordering.
  - Mitigation: refresh GitNexus index before implementation wave and run impact/context checks per targeted symbol.

## Validation Plan

- proof target: run mutation logic is symmetric across `update_run_*` wrappers
  - method: unit tests comparing wrapper behavior before/after for representative fields
  - evidence: passing tests under `tests/` for field update matrix

- proof target: retry behavior invariant preserved and normalized
  - method: mocked BQ failure/retry tests
  - evidence: assertions that retry helper invoked for all `pipeline_runs` updates

- proof target: degradation outcomes standardized without caller breakage
  - method: contract tests for returned status/reason payloads
  - evidence: snapshots/assertions for `append_event` and `update_run_synonym_proposals`

- proof target: legacy fallback semantics preserved
  - method: simulated `Unrecognized name:` error tests on affected columns
  - evidence: expected fallback query path or degradation status observed

- proof target: parse invariance for JSON/text fields
  - method: invalid/empty/valid JSON fixture tests
  - evidence: deterministic defaults (`None`/`[]`) by declared field contract

- proof target: no unintended blast radius
  - method: `gitnexus_detect_changes()` during implementation phase
  - evidence: changed symbols/files match planned scope

- proof target: overall regression safety
  - method: `uvx pytest tests/` and `uvx mypy src --show-error-codes`
  - evidence: green test/type runs

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
