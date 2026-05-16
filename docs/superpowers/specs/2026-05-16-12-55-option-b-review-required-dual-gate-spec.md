---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: option-b-review-required-dual-gate
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-agentic-gate-integration
targets:
  - config/env.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - tests/
  - docs/configuration.md
related_features: []
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Define Option B acceptance-policy design so weak-match `stretch` jobs are not auto-accepted, while preserving runtime stability, central config SSOT direction, and artifact contract compatibility.

## Key Deliverables

### Central acceptance policy contract

Define canonical config-owned policy fields for required-match acceptance boundaries by fit class, with one policy source and deterministic interpretation.

### Dual-gate decision contract

Define how `cv_analysis` and `cv_generation` share required-match metrics and produce policy-consistent outcomes (`accepted` vs `review_required`) without ambiguous stage ownership.

### Artifact and event transparency contract

Define additive diagnostics and reason-code outputs so policy-driven downgrades are inspectable in run artifacts/events without breaking existing consumer contract expectations.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current acceptance flow, stage ownership, and artifact fields against live-run evidence

**Steps:**
- [ ] inspect current status transition logic across `cv_analysis` and `cv_generation`
- [ ] inspect current config policy surfaces that influence fit and acceptance outcomes
- [ ] map current artifact fields used by run detail and tests for acceptance/review/failure breakdown

**Verification:**
- [ ] current boundary between quality-policy decisions and hard failures is explicit

**Exit Criteria:**
- no design choice depends on unstated assumptions about status ownership or artifact schema

### Wave 2: Decision closure

**Purpose:**
- close non-obvious policy and stage-ownership decisions for Option B

**Steps:**
- [ ] define central policy matrix fields and meaning for `strong` and `stretch`
- [ ] define normalized required-match metrics computed once and consumed consistently downstream
- [ ] define deterministic `review_required` reason-code set for policy failures
- [ ] define contract-safe additive artifact/event fields for policy diagnostics

**Verification:**
- [ ] each acceptance-policy branch has explicit owner and outcome mapping

**Exit Criteria:**
- design is internally coherent and bounded to policy strictness scope

### Wave 3: Validation and approval readiness

**Purpose:**
- specify proof that Option B fixes permissive acceptance without runtime regressions

**Steps:**
- [ ] define targeted tests for acceptance downgrade behavior under `stretch` deficits
- [ ] define compatibility checks for existing stage-artifact consumers and run-detail views
- [ ] define live-run verification evidence to compare accepted/review split before vs after

**Verification:**
- [ ] validation plan proves policy strictness change and preserves operational success path

**Exit Criteria:**
- spec is ready for implementation planning handoff

## Design Decisions

### Decision: Central config policy matrix as SSOT for acceptance strictness

- context: second-pass audit for run `c62dc5a3-6f80-4a43-94f6-ab0025f6633f` showed `3/4` accepted jobs with missing required items, max missing required `7`
- choice: store acceptance strictness boundaries in central config (`config/env.yaml`) with fit-class-aware thresholds and missing-required controls
- alternatives considered:
  - hard gate only at `cv_analysis`
  - prompt-only tightening without deterministic policy fields
- impact:
  - policy ownership centralized
  - deterministic policy updates without scattering rule logic

### Decision: Dual-gate model with shared normalized metrics

- context: acceptance quality needs stronger control while preserving staged architecture
- choice: compute required-match metrics in `cv_analysis`; apply final policy gate in `cv_generation` before final `accepted` status
- alternatives considered:
  - single-stage hard block in `cv_analysis`
- impact:
  - stronger symmetry and invariance across stages
  - clear separation between policy downgrade and hard generation/validation failures

### Decision: `review_required` as policy downgrade outcome

- context: rows can be structurally valid yet fail acceptance strictness policy
- choice: route policy-failing rows to `review_required` with deterministic reason code rather than mark as hard failure
- alternatives considered:
  - converting policy failures into `validation_failed`
  - allowing current permissive `accepted` behavior
- impact:
  - preserves HITL review path
  - keeps failure statuses reserved for true runtime/validation/persistence faults

### Decision: Additive artifact diagnostics only

- context: existing run and stage consumers already parse current artifacts
- choice: add policy diagnostics as additive fields/reason codes; avoid removing or renaming existing keys
- alternatives considered:
  - schema reshaping with breaking changes
- impact:
  - lower downstream break risk
  - easier verification and rollout

## Invariants

- `config/env.yaml` remains canonical policy source for acceptance strictness in this slice.
- Same required-match inputs and fit class must produce same acceptance outcome across equivalent execution paths.
- `review_required` remains non-fatal HITL path; hard-failure statuses remain reserved for real generation/validation/persistence failures.
- Stage artifacts/events remain backward compatible by additive extension only.
- Existing successful runtime path (`succeeded` run with completed stages) must remain operationally intact after policy tightening.

## Validation Plan

- proof target: policy-failing `stretch` rows no longer auto-accept
  - method: targeted unit/integration tests with controlled required-match deficits
  - evidence: test outputs showing `review_required` with deterministic reason code where policy fails

- proof target: valid rows still accept under configured policy
  - method: targeted tests with policy-passing required-match metrics
  - evidence: test outputs showing unchanged `accepted` outcomes for passing cases

- proof target: artifact compatibility is preserved
  - method: schema/consumer inspection + existing run-detail-related tests
  - evidence: passing tests and inspection confirming existing keys retained, new keys additive

- proof target: live-run behavior reflects stricter acceptance split without runtime breakdown
  - method: post-change live run and artifact retrieval using same inspection workflow used in this thread
  - evidence: run status remains successful and accepted/review-required distribution reflects policy boundaries

- proof target: policy source-of-truth remains centralized
  - method: config load-path inspection and tests for policy field resolution
  - evidence: assertions that policy projections come from canonical config surface

## Acceptance Criteria

- Option B dual-gate policy contract is explicitly documented with stage ownership and outcome mapping.
- `review_required` downgrade semantics are explicitly bounded as HITL non-fatal path.
- Deterministic reason-code taxonomy for policy downgrades is documented.
- Validation plan includes direct proof for:
  - downgrade of weak-match `stretch` cases
  - preservation of passing-case acceptance
  - artifact compatibility
  - successful post-change live-run verification
- Non-goals and risks are explicit enough to prevent scope creep.

## Non-Goals

- Redesigning ranking, reranker, or fit-label generation algorithms.
- Enabling/overhauling telemetry or Langfuse in this change.
- Enabling/overhauling semantic-alignment subsystem in this change.
- Broad refactor of unrelated config domains outside acceptance policy fields.
- Public-mirror governance/publication changes.

## Risks and Mitigations

- Risk: threshold values overtighten and reduce useful outputs too sharply
  - mitigation: fit-class-specific policy fields and targeted regression fixtures before rollout

- Risk: inconsistent enforcement between `cv_analysis` and `cv_generation`
  - mitigation: shared normalized metrics contract and deterministic outcome mapping tests

- Risk: downstream consumers break on artifact changes
  - mitigation: additive-only schema extension and compatibility-focused tests

- Risk: GitNexus unavailable during drafting reduced graph-assisted cross-file trace
  - mitigation: source-first inspection and test/validator-backed proof requirements in validation plan

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
