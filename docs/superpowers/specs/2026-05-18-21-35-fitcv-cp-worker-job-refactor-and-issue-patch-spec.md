---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-cp-worker-job-refactor-and-issue-patch
parent_workstream: none
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/bq_store.py
related_features:
  - none
related_stages:
  - none
---

## Goal

Define bounded, low-regression refactor and issue-patch specification for `src/fitcv_cp/worker_job.py` with SSOT, symmetry, invariance as primary design constraints.

## Key Deliverables

### Deliverable 1: Artifact persistence SSOT contract

Single normalized contract for run artifact payload projection and persistence lifecycle (`build -> persist -> degrade/event`) across:
- results export
- stage transition artifacts
- settings used
- mapping suggestions
- synonym proposals

### Deliverable 2: Synonym policy symmetry contract

Single source for synonym-management mode defaults, recommendation lifecycle, and status-transition constraints shared between runtime orchestration and payload builder.

### Deliverable 3: Risk patches for identified defects

Design-approved patches for:
- non-atomic global synonym-map writes
- unsafe YAML scalar serialization in overlay writer
- dead or contradictory compatibility shim behavior

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and drift points before extraction or consolidation

**Steps:**
- [ ] map all snapshot builders and persist call-sites in `worker_job.py`
- [ ] map synonym mode/default readers across `worker_job.py` and `synonym_proposals.py`
- [ ] map status/rule literals that duplicate or bypass shared contracts
- [ ] record GitNexus blast radius for edited symbols before each edit (`impact`, `context`)

**Verification:**
- [ ] equivalence map exists for payload builders, policy resolution, and status literals
- [ ] drift/duplication inventory linked to exact file locations

**Exit Criteria:**
- no refactor action starts without identified ownership boundary and caller map

### Wave 2: Decision closure

**Purpose:**
- finalize consolidation boundaries and keep behavioral invariants explicit

**Steps:**
- [ ] define SSOT module boundary for payload projection helpers
- [ ] define SSOT boundary for synonym policy defaults and transitions
- [ ] decide compatibility handling for existing shim helpers
- [ ] define patch boundary for YAML atomicity and serialization safety

**Verification:**
- [ ] every duplicated concern has selected owner surface
- [ ] each extracted helper has explicit interface and caller migration path

**Exit Criteria:**
- interface shape, migration order, and rollback path are all explicit

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof and safety controls executable before code rollout

**Steps:**
- [ ] define test matrix for behavioral parity and invariants
- [ ] define schema/integration checks for artifact payloads
- [ ] define GitNexus post-change scope validation gate
- [ ] define rollback containment for partial deployments

**Verification:**
- [ ] validation plan proves no behavioral drift for existing successful paths
- [ ] high-risk write-path changes have containment and recovery checks

**Exit Criteria:**
- spec is implementable in bounded incremental patches

## Design Decisions

### Decision: Centralize artifact snapshot construction

- context: `worker_job.py` repeats projection logic for run mode, replay context, and payload shape across multiple builders.
- choice: introduce shared artifact contract helpers in dedicated module (recommended `src/fitcv_cp/run_artifact_contracts.py`) and route existing builders through that layer.
- alternatives considered:
  - keep current inline helpers with comment-only cleanup
  - extract only run-mode normalization
- impact:
  - reduces hidden duplication
  - standardizes schema fields and defaults
  - limits future drift across artifact surfaces

### Decision: Centralize synonym-management policy resolution

- context: synonym mode/default fields are resolved in `synonym_proposals.py` but manually restated in `worker_job.py`.
- choice: make `resolve_synonym_management_mode()` authoritative and remove mirrored fallback map assembly in `worker_job.py`.
- alternatives considered:
  - leave duplicated mapping for “defensive clarity”
  - move all policy to `worker_job.py`
- impact:
  - SSOT for defaults and policy flags
  - symmetric policy behavior across proposal generation and automation

### Decision: Harden global synonym-map writes

- context: current write path for `config/taxonomy/skill_synonyms.yaml` is direct overwrite and raw string interpolation.
- choice: patch with atomic write (`tmp -> fsync -> replace`) and safe YAML emission path.
- alternatives considered:
  - retain direct write but add retry
  - enforce lock only, keep same serializer
- impact:
  - prevents partial-file corruption
  - prevents malformed YAML for reserved scalar characters

### Decision: Preserve behavior-first extraction strategy

- context: `execute_pipeline_run` is large and high-risk orchestration surface.
- choice: split by extraction seams (normalization/persistence/policy) first, no control-flow rewrite in initial passes.
- alternatives considered:
  - immediate phase decomposition of full function
- impact:
  - lower regression probability
  - clearer incremental review and rollback

## Invariants

- run terminal statuses and transitions remain semantically unchanged (`running`, `awaiting_continue`, `succeeded`, `failed`, `cancelled`)
- existing artifact schema version fields remain present and valid
- manual-staged checkpoint semantics remain unchanged
- run-all progress snapshot cadence remains unchanged
- synonym proposal status transitions remain legal under existing transition graph
- degraded snapshot persistence still emits warning signal without hard-failing run completion
- replay context defaults remain deterministic for missing fields

## Acceptance Criteria

- all artifact payload builders use shared SSOT helpers for run-mode label and replay-context projection
- no duplicated synonym default map remains outside authoritative policy resolver
- global synonym map persistence uses atomic write and passes YAML roundtrip tests for reserved characters
- compatibility shim behavior is either removed with migration update or explicitly retained with deprecation marker and tests
- no user-visible behavior regression in success, checkpoint pause, cancel, and failure flows

## Non-Goals

- no full architectural rewrite of worker runtime or pipeline orchestration engine
- no change to business scoring logic, ranking logic, or CV generation semantics
- no public API redesign for control-plane web routes in this change
- no schema-version bump unless current fields cannot express required invariant

## Risks and Mitigations

- risk: regression in run-finalization branch behavior
  - mitigation: golden-path integration tests for terminal states and artifact persistence
- risk: cross-module import cycles after helper extraction
  - mitigation: extract pure helpers with no runtime side effects; keep orchestration import boundary stable
- risk: synonym promotion write contention
  - mitigation: atomic replace and deterministic merge rules; event logs on contention-retry failure
- risk: hidden callers for moved helpers
  - mitigation: GitNexus `context` + `impact` pre-change and `detect-changes` pre-commit

## Validation Plan

- proof target: artifact payload parity preserved after SSOT extraction
  - method: snapshot/golden comparison tests for payload JSON outputs
  - evidence: test artifacts under `tests/` showing identical key/value behavior for baseline fixtures

- proof target: run-mode and replay-context symmetry enforced
  - method: table-driven unit tests over valid/invalid run modes and replay payload defaults
  - evidence: passing tests with explicit cases for unknown run mode fallback

- proof target: synonym policy defaults remain invariant across modules
  - method: shared contract tests asserting policy resolution outputs
  - evidence: tests proving same dict shape and default values for all policy flags

- proof target: global synonyms write-path safe under edge data
  - method: roundtrip serialization tests + failure-injection around atomic replace
  - evidence: no malformed YAML, no partial-file state after simulated write failure

- proof target: blast radius remains bounded for each patch
  - method: run `npx gitnexus impact <symbol> --direction upstream --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` before each symbol edit; run `npx gitnexus detect-changes` before commit
  - evidence: recorded impact outputs and detect-changes summary showing expected scope only

- proof target: refactor does not change runtime outcomes
  - method: run regression suite (`uvx pytest tests/`) and static checks (`uvx mypy src --show-error-codes`)
  - evidence: green test and type-check logs

## Migration and Safety Controls

### Backward compatibility needs

- preserve existing payload key names and schema-version fields
- preserve existing event stage names used by downstream UI/reporting
- preserve synonym proposal status names and transition actions

### Deprecation/removal path

- mark compatibility shim helpers as deprecated in first patch
- migrate direct callers to new SSOT helpers in same or next bounded patch
- remove shim only after tests and call-graph show zero production callers

### Rollback/containment strategy

- incremental patch sequence with one consolidation axis per patch
- rollback by reverting latest bounded patch only; keep prior validated patches
- if write-path hardening fails in production-like test, disable promotion write branch and keep run-scoped overlay behavior only

## Triage Block

Layer: change  
Feature type: MODIFY  
Summary: Refactor and patch `fitcv_cp` worker orchestration and artifact persistence contracts for SSOT/symmetry/invariance.  
Reasoning: Bounded runtime refactor with no product-intent change; design/contract cleanup with safety patches.  
Invariants:
  - terminal status semantics preserved
  - artifact schema continuity preserved
  - synonym transition legality preserved
Dependencies:
  - GitNexus fresh index
  - existing tests + new contract tests
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
    - docs/superpowers/specs/2026-05-18-21-35-fitcv-cp-worker-job-refactor-and-issue-patch-spec.md
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

## Completion Criteria

1. all Key Deliverables satisfied with approved design boundaries
2. acceptance criteria and invariants mapped to executable validation checks
3. deprecation and rollback controls documented for each risky patch axis
4. spec ready for handoff to implementation planning without unresolved architecture ambiguity
