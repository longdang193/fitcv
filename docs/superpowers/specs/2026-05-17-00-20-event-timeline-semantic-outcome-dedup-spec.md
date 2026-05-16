---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: Event Timeline Semantic Outcome and Deterministic Dedup
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv/pipeline.py
related_features:
  - inspection_debugging
related_stages:
  - cv_generation
---

## Goal

Define canonical timeline semantics that make expected policy outcomes explicitly non-bug, classify unexpected states as investigate/failure, and collapse repeated equivalent informational events deterministically without losing raw audit events.

## Key Deliverables

### Canonical semantic outcome projection contract

Specify run-event to semantic-outcome mapping that is stable across stage aliases and payload source variations.

### Deterministic dedup projection for timeline view

Specify equivalence fingerprint and dedup rules that remove repeated informational noise while preserving audit truth in source events.

### Symmetric severity and rendering policy

Specify severity and label behavior so equivalent outcomes render equivalently across timeline, with explicit expected-vs-unexpected qualification.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current event emission behavior and timeline rendering boundaries before finalizing contract decisions

**Steps:**
- [ ] inspect event emission points for `synonym_proposal_triage_completed`, `layer4_cv_generation_result`, and `layer4_cv_validation_failed`
- [ ] inspect timeline rendering path for stage label, severity, summary message, and artifact links
- [ ] record current mismatch between policy rejection semantics and bug-like visual interpretation

**Verification:**
- [ ] current-state behavior is explicit for repeated triage events and validation-failed events

**Exit Criteria:**
- no core decision depends on unstated assumptions about event source or timeline projection

### Wave 2: Decision closure

**Purpose:**
- resolve canonical semantic contract, equivalence mapping, and deterministic dedup policy

**Steps:**
- [ ] define semantic-outcome taxonomy for timeline projection
- [ ] define canonical stage-equivalence mapping rules
- [ ] define dedup fingerprint and collapse conditions for informational repeats
- [ ] define symmetric severity and qualifier rendering rules

**Verification:**
- [ ] all non-obvious decisions include rationale and bounded alternatives

**Exit Criteria:**
- design is coherent, bounded, and implementation-plannable

### Wave 3: Validation and approval readiness

**Purpose:**
- prepare proof expectations for policy clarity, invariance, and equivalence

**Steps:**
- [ ] define acceptance checks for expected-vs-unexpected labeling
- [ ] define replay and alias-equivalence checks
- [ ] define audit-preservation checks for deduped timeline view

**Verification:**
- [ ] validation plan proves behavioral correctness and contract preservation

**Exit Criteria:**
- spec is ready for approval and implementation planning

## Design Decisions

### Decision: Introduce semantic-outcome projection layer

- context: raw stage/message alone does not reliably communicate expected policy rejection vs unexpected failure
- choice: project each timeline event into canonical semantic outcomes: `expected_rejection`, `unexpected_failure`, `requires_review`, `normal_progress`, `summary`
- alternatives considered:
  - retain raw-stage-only rendering with local message patches
- impact:
  - timeline meaning becomes policy-aware and stable across emitter wording changes
  - rendering logic moves from ad-hoc stage strings to canonical semantic contract

### Decision: Canonical equivalence mapping across event aliases

- context: equivalent outcomes can surface under different stage keys over time
- choice: define canonical event keys and map alias stages into one semantic bucket before rendering
- alternatives considered:
  - treat each stage key independently
- impact:
  - equivalent outcomes render symmetrically
  - refactors in emitter naming do not change operator interpretation

### Decision: Deterministic dedup as projection, not source suppression

- context: repeated `synonym_proposal_triage_completed` events are emitted during snapshot cycles and create timeline noise
- choice: keep raw events intact; collapse repeated equivalent informational rows in timeline projection using deterministic fingerprint and adjacency/state rules
- alternatives considered:
  - suppress repeated emission at source
  - no dedup
- impact:
  - preserves audit trail while improving timeline signal-to-noise
  - keeps event-source responsibilities separate from UI projection responsibilities

### Decision: Symmetric severity policy from semantic outcome

- context: warning-level visuals can imply bugs even for expected policy rejections
- choice: derive timeline qualifier and severity from semantic outcome + reason class (`policy`, `system`, `data`, `operator`) with explicit expected/unexpected label
- alternatives considered:
  - keep stage-specific severity heuristics
- impact:
  - policy rejection and system failures are distinguishable by contract, not interpretation

### Decision: Explainability payload minima for rejection outcomes

- context: root-cause clarity depends on consistent payload fields
- choice: require projection to consume normalized fields: `reason_code`, `reason_class`, `explain_short` where available; degrade gracefully when absent and mark as investigate
- alternatives considered:
  - free-form message-only explanation
- impact:
  - clearer operator diagnosis and stable downstream automation hooks

## Invariants

- equivalent semantic outcomes must render with equivalent labels/severity regardless of raw stage alias.
- identical run events under replay must project to identical timeline semantics.
- dedup must never mutate or drop raw persisted events; it only affects timeline projection view.
- expected policy rejections must never be presented as unexpected bugs.
- projection contract must remain deterministic for same event payload and run context.

## Acceptance Criteria

1. For `layer4_cv_validation_failed` with `deterministic_outcome=rejected` and `stage_owned_subreason=validation_failed`, timeline label explicitly indicates expected policy rejection.
2. For validation-failed events missing required classification signals, timeline indicates unexpected/investigate.
3. Consecutive repeated `synonym_proposal_triage_completed` rows with equivalent fingerprint collapse into one timeline row with repeat count indicator.
4. Raw event history/export remains unchanged after dedup projection is enabled.
5. Alias stage keys mapped to same canonical semantic key produce identical timeline qualifier and severity.

## Non-Goals

- redesign full run-detail page layout.
- change upstream business policy that triggers validation failure.
- remove or rewrite historical raw events in storage.
- define implementation plan tasks or code-level rollout sequencing.

## Risks and Mitigations

- risk: over-collapsing may hide materially different events.
  - mitigation: dedup fingerprint includes outcome-driving payload fields and only collapses equivalent informational rows under explicit conditions.
- risk: missing payload fields could misclassify outcomes.
  - mitigation: fallback classification to `unexpected_failure`/`investigate` and explicit unresolved marker.
- risk: contract drift between emitters and projection layer.
  - mitigation: add projection contract tests for known stage/payload fixtures and alias cases.

## Validation Plan

- proof target: expected policy rejection is visibly distinct from unexpected failures
  - method: inspection + fixture-driven timeline rendering tests
  - evidence: test cases and rendered timeline output showing expected qualifier for policy rejection

- proof target: semantic invariance under replay
  - method: comparison run of identical event fixture sequence rendered twice
  - evidence: identical projected rows and qualifiers across both renders

- proof target: equivalence across aliases
  - method: tests with multiple stage aliases mapped to same canonical semantic key
  - evidence: identical projected severity/qualifier outputs

- proof target: dedup reduces noise without data loss
  - method: comparison between raw event count and projected timeline count for repeated triage fixtures
  - evidence: projected count reduced with repeat indicator; raw export count unchanged

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
