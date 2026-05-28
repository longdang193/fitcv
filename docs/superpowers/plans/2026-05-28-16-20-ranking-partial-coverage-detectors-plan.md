---
artifact_type: plan
status: proposed
layer: change
template_id: implementation-plan
name: ranking-partial-coverage-detectors-and-preference-weight-contract
parent_workstream: none
targets:
  - src/fitcv/ranking_contract.py
  - src/fitcv/ranking.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - tests/test_ranking_contract.py
  - tests/test_ranking.py
  - tests/test_pipeline_stage_artifacts.py
related_features:
  - cv_system
  - inspection_debugging
related_stages:
  - ranking
---

## Goal

Close ranking-stage partial coverage gaps by adding runtime detectors for missing-feature fallback usage and taxonomy drift, plus strict validation for `preference_fit_weights`, with source-backed tests and stage artifacts.

## Key Deliverables

### Runtime detector coverage for failure modes 2 and 3

Implement stage-owned runtime counters and diagnostics that make missing-value fallback usage and taxonomy drift visible in ranking artifacts and exports, so silent behavior shifts become detectable in normal run telemetry.

### Contract guard for failure mode 4

Implement and enforce `preference_fit_weights` validation (range + sum invariant) so preference weighting cannot accidentally overpower core fit due to bad configuration.

### Regression-proof test coverage

Add/extend focused unit tests for contract validation and ranking diagnostics payloads, including negative-path tests for invalid preference weights and detector metric shape/value assertions.

## Task/Wave Breakdown

### Task 1: Root-cause instrumentation baseline (Systematic Debugging Phase 1)

**Purpose:**
- Establish exact boundaries where detection is currently absent and define minimal instrumentation points before code edits.

**Files:**
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `docs/stages/ranking.source.yaml`

**Preconditions:**
- Existing evidence from ranking audit notes confirms partial coverage for failure modes `2,3,4`.
- GitNexus is stale; use source-first, advisory-only lookup.

**Steps:**
- [ ] Trace ranking data flow from feature assembly to `compute_final_score`, `compute_preference_fit_details`, and stage artifact construction.
- [ ] Identify exact points where fallback defaults are applied and where canonicalization/match typing already exists.
- [ ] Define bounded detector schema additions under ranking `decision_summary.quality_metrics` (or dedicated ranking diagnostics block) without breaking existing consumers.

**Verification:**
- [ ] Written mapping exists from each failure mode (`2,3,4`) to specific code insertion points.
- [ ] Detector schema draft includes field names, type contracts, and zero/default behavior.

**Exit Criteria:**
- Instrumentation plan is specific enough to implement without guessing.

### Task 2: Add `preference_fit_weights` contract validation

**Purpose:**
- Prevent misconfigured preference weights from violating policy intent.

**Files:**
- Modify: `src/fitcv/ranking_contract.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `tests/test_ranking_contract.py`
- Modify: `tests/test_ranking.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Add `validate_preference_fit_weights_contract` in `ranking_contract` with constraints:
- [ ] keys exactly `domain`, `role_family`, `location_type` (or strict required-key set with controlled optional handling)
- [ ] each value in `[0.0, 1.0]`
- [ ] total sum equals `1.0` within epsilon
- [ ] Call validator from `get_preference_fit_weights` after resolution/merge.
- [ ] Add tests for valid config, invalid sum, invalid range, missing key behavior.

**Verification:**
- [ ] `pytest -q tests/test_ranking_contract.py tests/test_ranking.py`
- [ ] New negative-path tests fail before fix and pass after fix.

**Exit Criteria:**
- Invalid `preference_fit_weights` cannot enter runtime scoring silently.

### Task 3: Add missing-feature fallback runtime detector (Failure mode 2)

**Purpose:**
- Detect silent bias from missing feature defaults by counting fallback usage and rate.

**Files:**
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_pipeline_stage_artifacts.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Add bounded helper in ranking module to compute fallback-usage metadata per feature during score/contribution computation (counts and rates).
- [ ] Surface per-run aggregate detector in ranking stage artifacts, e.g.:
- [ ] `missing_feature_fallbacks.total_applied`
- [ ] `missing_feature_fallbacks.by_feature.<feature>_count`
- [ ] `missing_feature_fallbacks.by_feature.<feature>_rate`
- [ ] Ensure metrics distinguish explicit `None`/missing from provided values.
- [ ] Keep payload bounded and backward-compatible (new optional fields only).

**Verification:**
- [ ] Unit tests for mixed present/missing feature rows assert expected counts/rates.
- [ ] Stage artifact test asserts detector appears under ranking block with deterministic shape.

**Exit Criteria:**
- Runs expose when defaults materially drive ranking outcomes.

### Task 4: Add taxonomy drift runtime detector (Failure mode 3)

**Purpose:**
- Detect canonicalization/taxonomy mismatch patterns that degrade preference alignment.

**Files:**
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_pipeline_stage_artifacts.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Reuse `compute_preference_fit_details` diagnostics (`match_details`, `canonical_values`) to derive drift indicators.
- [ ] Add stage-level drift metrics, e.g.:
- [ ] `taxonomy_drift.domain_unmatched_count`
- [ ] `taxonomy_drift.role_family_unmatched_count`
- [ ] `taxonomy_drift.neighbor_match_count`
- [ ] `taxonomy_drift.unmatched_rate`
- [ ] Add anomaly flag thresholds (configurable, conservative defaults) for warning-only signaling.
- [ ] Ensure detector treats empty preference dimensions as neutral, not drift.

**Verification:**
- [ ] Unit tests validate exact/neighbor/none paths map to expected drift counters.
- [ ] Artifact tests validate stable JSON shape and rate math.

**Exit Criteria:**
- Runs can alert on taxonomy drift trend before ranking quality regresses.

### Task 5: Integration, docs alignment, and evidence closeout

**Purpose:**
- Complete validation and ensure new detectors align with stage contract expectations.

**Files:**
- Modify: `docs/stages/ranking.source.yaml`
- Regenerate/verify: `docs/stages/ranking.yaml` (if managed sync path requires)
- Verify: `scripts/validate_repo_contracts.py`

**Preconditions:**
- Tasks 2–4 complete.

**Steps:**
- [ ] Update stage doc outputs/invariants to mention new detector metrics.
- [ ] Run repo validators and targeted tests.
- [ ] If schema/output consumers exist, verify non-breaking optional-field addition behavior.
- [ ] Record before/after evidence (sample artifact snippets + test output) in plan closeout notes.

**Verification:**
- [ ] `pytest -q tests/test_ranking_contract.py tests/test_ranking.py tests/test_pipeline_stage_artifacts.py`
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- Partial coverage items `2,3,4` move to implemented with runtime detect+prevent controls and passing tests.

## Verification

- `pytest -q tests/test_ranking_contract.py tests/test_ranking.py tests/test_pipeline_stage_artifacts.py`
- `python scripts/hooks/run_validator.py --fast`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
