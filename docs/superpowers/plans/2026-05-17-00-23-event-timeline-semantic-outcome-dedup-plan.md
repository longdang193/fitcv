---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: Event Timeline Semantic Outcome and Deterministic Dedup Implementation Plan
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-17-00-20-event-timeline-semantic-outcome-dedup-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_fitcv_cp/test_app.py
  - docs/generated/planning_lineage.yaml
related_features:
  - inspection_debugging
related_stages:
  - cv_generation
---

## Goal

Implement canonical semantic outcome projection and deterministic timeline dedup so operators can reliably distinguish expected policy rejections from unexpected failures while reducing repeated synonym-triage noise without altering raw event history.

## Key Deliverables

### Canonical semantic outcome projection in timeline rendering

Timeline rows render from a normalized semantic contract, including explicit expected-vs-unexpected qualifier for validation-failed outcomes.

### Deterministic dedup projection with repeat visibility

Timeline collapses repeated equivalent informational events (especially synonym triage refresh) using stable fingerprints and displays repeat count in projected view.

### Verification coverage for symmetry, invariance, and equivalence behavior

Tests prove alias-equivalent outcomes render identically, replay-equivalent payloads project identically, and dedup does not alter raw event persistence surfaces.

## Task/Wave Breakdown

### Task 1: Add semantic projection contract for timeline outcomes

**Purpose:**
- establish one canonical event-to-outcome mapping layer for timeline interpretation

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Parent spec approved for implementation.
- Existing timeline message helpers identified (`_timeline_stage_summary_message` and related functions).

**Steps:**
- [x] Step 1: Introduce semantic outcome resolver using existing payload fields (`deterministic_outcome`, `stage_owned_subreason`, stage id).
- [x] Step 2: Define qualifier policy for `expected_rejection` vs `unexpected_failure` and integrate into timeline row message/metadata.
- [x] Step 3: Keep fallback behavior deterministic when fields are missing (mark investigate path).

**Verification:**
- [x] Add/adjust tests for validation-failed rows to assert expected-policy qualifier when contract fields match.
- [x] Add test for missing/partial classification fields to assert unexpected/investigate qualifier.

**Exit Criteria:**
- Timeline outcome qualifiers no longer depend on ad-hoc raw message text.

### Task 2: Implement deterministic dedup projection with repeat counts

**Purpose:**
- collapse repeated equivalent informational rows in timeline view while retaining raw events

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.
- Semantic outcome and canonical key strategy available for fingerprint input.

**Steps:**
- [x] Step 1: Define canonical fingerprint payload for dedup-eligible informational events (`synonym_proposal_triage_completed` first).
- [x] Step 2: Implement projection-time collapse rules for equivalent consecutive rows and track repeat count.
- [x] Step 3: Expose repeat count in timeline row context so template can display compactly.

**Verification:**
- [x] Add test fixture with repeated equivalent triage events and assert one projected row plus repeat count.
- [x] Add test fixture with materially changed triage payload and assert no collapse.

**Exit Criteria:**
- Timeline noise reduced deterministically without suppressing underlying stored events.

### Task 3: Ensure equivalence and audit-preservation invariants

**Purpose:**
- prove canonical equivalence and raw-event preservation guarantees

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1 and 2 complete.

**Steps:**
- [x] Step 1: Add alias-equivalence tests (different raw stage aliases mapped to same canonical semantic outcome).
- [x] Step 2: Add replay-invariance test (same payload sequence projects identically across runs).
- [x] Step 3: Add assertion that raw events source remains unmodified by projection/dedup helpers.

**Verification:**
- [x] Run focused test module for timeline behavior.
- [x] Inspect event export/read path to confirm dedup is view-only.

**Exit Criteria:**
- Symmetry, invariance, and equivalence acceptance criteria are executable and passing.

### Task 4: Finalize docs lineage and run contract validation

**Purpose:**
- keep planning artifacts and repo validators in sync after plan-linked implementation updates

**Files:**
- Inspect: `docs/generated/planning_lineage.yaml`
- Modify: `docs/generated/planning_lineage.yaml` (if needed by validator)
- Verify: `scripts/hooks/run_validator.py`

**Preconditions:**
- Implementation changes and tests complete.

**Steps:**
- [x] Step 1: Regenerate planning lineage if spec/plan graph changed.
- [x] Step 2: Run fast validator hook and required targeted tests.
- [x] Step 3: Capture final evidence references in PR/closeout notes.

**Verification:**
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `pytest tests/test_fitcv_cp/test_app.py -k timeline`

**Exit Criteria:**
- Validation gates pass with no lifecycle or template contract drift.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest tests/test_fitcv_cp/test_app.py -k timeline`
- `pytest tests/test_fitcv_cp/test_app.py -k "validation_failed or synonym"`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

