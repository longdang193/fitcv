---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: structural-contract-consolidation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/models.py
related_features:
  - run_lifecycle_controls
  - settings_system
  - admin_control_plane_core
related_stages:
  - enrich
  - rule_filter
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define canonical shared structural contracts that remove active cross-module fragmentation in five areas: stage artifact envelope identity, proposal trace lifecycle, decision transition semantics, synonym-management policy projection defaults, and status/stage label projection.

This specification patches violations against symmetry, invariance, equivalence, repeated patterns, and shared structure without introducing behavior expansion.

Triage classification:

- Layer: change
- Feature type: MODIFY
- Summary: consolidate duplicated structural contracts and projection defaults into canonical runtime surfaces
- Reasoning: current behavior already exists but encoded in multiple modules with drift risk
- Invariants:
  - run outputs remain backward-compatible for existing persisted payload readers
  - stage/manual run controls keep same user-visible behavior
  - synonym review actions preserve allowed transition matrix
- Dependencies:
  - existing persisted run payloads using legacy schema/version tags
  - existing tests covering run detail, worker lifecycle, and settings behavior
- Affected stages:
  - enrich
  - rule_filter
  - ranking
  - cv_analysis
  - cv_generation
- Affected features:
  - run_lifecycle_controls
  - settings_system
  - admin_control_plane_core
- Primary lens: cross-cutting
- Spec needed: yes
- Plan needed: yes

## Key Deliverables

### Deliverable 1: Canonical proposal lifecycle contract module

One authoritative module exports:

- transition table for proposal actions/statuses
- trace payload builder for synonym proposal generation
- trace summary/degradation semantics

All worker/app call sites consume this module; duplicate local builders are removed.

### Deliverable 2: Canonical stage transition artifact identity contract

One authoritative constant registry defines schema/version identity for stage transition artifacts across pipeline, worker persistence payload, and app projection payload.

### Deliverable 3: Canonical synonym-management defaults resolver

One resolver builds synonym-management effective defaults from settings snapshot/runtime config. App trigger envelope, app snapshot loader, and worker automation consume same resolver.

### Deliverable 4: Canonical status/stage label projection contract

One source for run status/stage labels is used by API/template projection to avoid scattered literal status groups.

### Deliverable 5: Structural equivalence validation coverage

Tests verify equivalence between prior and consolidated payload shapes where backward compatibility is required and verify single-source transition/policy projections.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**

- lock exact current-state duplication points and define migration-safe boundaries

**Steps:**

- [x] identify duplicate proposal trace builders and transition semantics
- [x] identify fragmented stage artifact schema identity surfaces
- [x] identify repeated synonym-management defaults projections
- [x] identify status/stage label literal spread across runtime and templates

**Verification:**

- [x] cross-file evidence map exists for each of five violation classes

**Exit Criteria:**

- migration boundaries and compatibility constraints are explicit

### Wave 2: Decision closure

**Purpose:**

- resolve contract ownership and migration strategy

**Steps:**

- [x] define canonical contract owners for proposal, artifact, policy, status surfaces
- [x] select compatibility policy for persisted payloads (read old, write canonical)
- [x] define de-duplication cut lines and prohibited new duplicates

**Verification:**

- [x] each major structural contract has one owner and one consumption path

**Exit Criteria:**

- design is coherent, bounded, and plan-ready

### Wave 3: Validation and approval readiness

**Purpose:**

- define proof that consolidation removed drift vectors without regressions

**Steps:**

- [x] define test targets for symmetry/invariance/equivalence/repetition/shared-structure
- [x] define payload compatibility checks
- [x] define completion gate for no duplicate builders/default resolvers

**Verification:**

- [x] validation plan includes concrete methods and evidence paths

**Exit Criteria:**

- spec ready for implementation planning

## Design Decisions

### Decision: Centralize proposal lifecycle contracts under `fitcv_cp.synonym_proposals`

- context: proposal transition matrix and trace-building logic currently duplicated across modules
- choice: keep transition table and trace builder in `src/fitcv_cp/synonym_proposals.py`; worker/app import and use only exported functions
- alternatives considered:
  - keep duplicate shim in worker for backward tests
  - move all proposal logic into worker and make app read-only formatter
- impact:
  - removes equivalent-but-separate builders
  - reduces drift risk in degradation/status trace semantics
  - requires test updates for import paths and shared helper coverage

### Decision: Create shared schema/version contract registry for lifecycle artifacts

- context: stage transition artifacts and related payload families use inconsistent version tags across layers
- choice: define constants in one contract module (new `fitcv_cp.contracts` or existing contract surface) and reference them from pipeline/worker/app
- alternatives considered:
  - keep local literals plus linter checks only
  - convert to dynamic runtime metadata store
- impact:
  - enforces invariance for artifact identity
  - simplifies compatibility checks
  - requires staged migration path for existing persisted payload readers

### Decision: Introduce one synonym-management default resolver

- context: defaults repeated in app trigger, app snapshot loader, and worker mode extraction
- choice: define `resolve_synonym_management_effective_config(...)` and consume everywhere
- alternatives considered:
  - keep duplicated `setdefault` blocks with snapshot tests
  - move defaults into settings schema only and trust downstream callers
- impact:
  - restores symmetry for policy projection
  - removes repeated default literals
  - easier to assert policy behavior equivalence across run paths

### Decision: Bind status/stage display groupings to model-level contract

- context: run status/stage groupings are partly enum-backed, partly literal checks in templates/runtime
- choice: expose canonical status groups/labels in app projection layer derived from `RunStatus` and stage contract constants; templates consume projection fields instead of literal tuples
- alternatives considered:
  - keep literal tuples in templates
  - push all formatting logic into templates with macro indirection
- impact:
  - improves shared-structure consistency between API and UI
  - reduces coupling between template literals and lifecycle semantics

### Decision: Backward-compatible read policy with canonical write policy

- context: existing persisted payloads contain legacy schema/version tags
- choice: maintain reader compatibility for legacy tags, write only canonical tags post-migration
- alternatives considered:
  - immediate hard-cut migration requiring data rewrite
  - dual-write forever
- impact:
  - lower rollout risk
  - bounded deprecation path required and documented

## Invariants

- Proposal action/status transitions must remain identical to current allowed matrix.
- Proposal trace payload meaning must remain equivalent for downstream UI/audit consumers.
- Stage transition artifacts must keep semantic field compatibility for existing run detail views.
- Synonym-management effective flags must evaluate identically for same input settings snapshot.
- Run status lifecycle semantics (`queued`, `running`, `awaiting_continue`, `cancelling`, `cancelled`, `succeeded`, `failed`) must not change.
- No new duplicated builders/resolvers for these contracts may be introduced.

## Acceptance Criteria

- Exactly one implementation of synonym proposal trace builder exists in runtime code.
- Exactly one implementation of synonym proposal transition matrix exists in runtime code.
- Stage transition artifact schema/version constants are sourced from one contract registry.
- Synonym-management defaults are computed by one shared resolver and used by app + worker paths.
- UI status grouping logic consumes projected canonical groups instead of ad-hoc literal status tuples.
- Regression tests pass for run detail artifacts, synonym proposal review actions, and worker automation behavior.

## Non-Goals

- No redesign of product workflow stages or run lifecycle semantics.
- No addition of new synonym-management features or policies.
- No large storage migration rewriting historical run payloads.
- No broad frontend redesign.
- No changes to unrelated planning lineage issues currently failing pre-existing validators.

## Risks and Mitigations

- Risk: compatibility regression for older persisted payloads.
  - Mitigation: keep legacy read adapters; add fixture tests for old payload tags.
- Risk: hidden callers depend on duplicate helper location.
  - Mitigation: temporary compatibility exports with deprecation comments; grep-based enforcement test.
- Risk: template/runtime mismatch during status projection swap.
  - Mitigation: add integration tests on run list/detail rendering for all RunStatus values.
- Risk: partial consolidation leaves mixed constants.
  - Mitigation: add static assertion test that disallows local schema/version literals for targeted families.

## Validation Plan

- proof target: proposal lifecycle equivalence preserved under consolidation
  - method: unit tests comparing transition outcomes and trace outputs for representative proposal sets
  - evidence: `tests/test_fitcv_cp/test_synonym_proposals.py` updates plus new equivalence fixtures

- proof target: stage artifact identity invariance across pipeline/worker/app
  - method: unit tests asserting all targeted producers reference shared constants and emit expected canonical tags
  - evidence: new/updated tests in `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_pipeline.py`

- proof target: synonym-management defaults symmetry across app and worker
  - method: unit tests for shared resolver consumed by trigger envelope, snapshot loader, and worker mode extraction
  - evidence: tests in `tests/test_fitcv_cp/test_app.py` and `tests/test_fitcv_cp/test_worker_job.py`

- proof target: status/stage projection shared-structure conformance
  - method: integration-style template projection tests for run list/detail and status groups
  - evidence: `tests/test_fitcv_cp/test_run_detail_output_availability.py` and/or new template projection tests

- proof target: duplicate pattern elimination
  - method: structural grep check in test or lint helper for forbidden duplicate function definitions/literals
  - evidence: test artifact output showing single-owner surfaces

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
