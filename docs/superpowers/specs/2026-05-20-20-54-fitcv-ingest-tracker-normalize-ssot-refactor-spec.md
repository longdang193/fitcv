---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ingest-tracker-normalize-ssot-refactor
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
targets:
  - src/fitcv/ingest.py
  - src/fitcv/tracker.py
  - src/fitcv/normalize.py
  - src/fitcv/persistence.py
related_features:
  - cv_system
related_stages:
  - normalize
---

## Goal

Define SSOT/symmetry/invariance refactor boundaries for `ingest`, `tracker`, and `normalize` with backward-compatible persistence and deterministic dedupe/parser behavior.

## Key Deliverables

### Deliverable 1

Canonical contract surface for shared mapping/default semantics used by both ingest and normalize/tracker flows.

### Deliverable 2

Symmetric persistence path using shared BigQuery/sqlite helpers with invariant credential behavior.

### Deliverable 3

Deduplication/parser hardening rules that resolve contradictions and edge drift with explicit tests.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- Confirm drift/duplication/edge cases in scoped modules.

**Steps:**
- [ ] Capture equivalent concepts and divergences.
- [ ] Confirm call graph impact via GitNexus context/impact.

**Verification:**
- [ ] Findings map references concrete symbols and tests.

**Exit Criteria:**
- Scope and risks are bounded for one implementation plan.

### Wave 2: Decision closure

**Purpose:**
- Resolve RF-001..RF-005 decision points.

**Steps:**
- [ ] Approve persistence SSOT shape.
- [ ] Approve contract extraction shape.
- [ ] Approve parser/dedupe invariants and compatibility posture.

**Verification:**
- [ ] Decisions are explicit and non-overlapping.

**Exit Criteria:**
- Implementation plan can execute without unresolved design questions.

### Wave 3: Validation readiness

**Purpose:**
- Define proof for non-regression and bounded behavior change.

**Steps:**
- [ ] Define scoped tests/types/GitNexus checks.
- [ ] Define fallback/migration evidence for tracker writes.

**Verification:**
- [ ] Validation targets map to each RF item.

**Exit Criteria:**
- Plan handoff ready.

## Design Decisions

### Decision: Shared persistence and contract modules

- context: `ingest`/`tracker` drifted on credential and default contracts.
- choice: route both through shared helpers and shared constants.
- alternatives considered:
  - keep module-local implementations with documentation only
- impact:
  - reduced divergence risk and lower maintenance fan-out.

### Decision: Dedupe/parser hardening with explicit invariants

- context: hidden duplication and ambiguous parser outcomes created edge risk.
- choice: consolidate dedupe logic and codify parser behavior via tests.
- alternatives considered:
  - leave behavior permissive and undocumented
- impact:
  - predictable behavior under mixed/variant inputs.

## Invariants

- `job_url` remains stable identity key across ingest/normalize/tracker flows.
- dedupe exclusion reasons and ordering remain deterministic.
- tracker structured->legacy fallback remains backward compatible.
- sqlite mode remains credential-free.

## Validation Plan

- proof target: persistence symmetry across ingest/tracker
  - method: unit tests + source inspection
  - evidence: passing `tests/test_ingest.py` + `tests/test_tracker.py` parity checks
- proof target: dedupe/path invariance
  - method: unit and pipeline tests
  - evidence: passing `tests/test_normalize.py` + dedupe-focused pipeline tests
- proof target: bounded blast radius
  - method: graph diff inspection
  - evidence: `gitnexus detect_changes` output within scoped modules

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
